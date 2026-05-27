"""
View layer — renders templates with context data.
"""
import os
import mimetypes
import subprocess
import tempfile
from django.shortcuts import render, get_object_or_404, redirect
from django.http import StreamingHttpResponse, Http404, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, F
from django.core.files import File
from backend.model.models import Video, Category, Like, Dislike, Comment


# ─── 404 ─────────────────────────────────────────────────────────────────────

def custom_404(request, exception=None):
    return render(request, '404.html', status=404)


# ─── Upload ──────────────────────────────────────────────────────────────────

ALLOWED_VIDEO_TYPES = {'video/mp4', 'video/webm', 'video/ogg', 'video/quicktime', 'video/x-matroska'}
MAX_VIDEO_MB = 500


@login_required
def upload_video(request):
    """Upload a new video from the frontend."""
    categories = Category.objects.all()

    if request.method != 'POST':
        return render(request, 'upload.html', {'categories': categories})

    title = request.POST.get('title', '').strip()
    description = request.POST.get('description', '').strip()
    category_id = request.POST.get('category', '').strip()
    video_file = request.FILES.get('video_file')
    thumbnail_file = request.FILES.get('thumbnail')

    # ── Validation ──
    errors = []
    if not title:
        errors.append('Title is required.')
    if not video_file:
        errors.append('Please select a video file.')
    else:
        if video_file.content_type not in ALLOWED_VIDEO_TYPES:
            errors.append(f'Unsupported format: {video_file.content_type}. Use MP4, WebM, OGG or MKV.')
        if video_file.size > MAX_VIDEO_MB * 1024 * 1024:
            errors.append(f'File too large. Maximum size is {MAX_VIDEO_MB} MB.')

    if errors:
        for e in errors:
            messages.error(request, e)
        return render(request, 'upload.html', {'categories': categories})

    # ── Save video ──
    category = None
    if category_id:
        try:
            category = Category.objects.get(pk=category_id)
        except Category.DoesNotExist:
            pass

    video = Video(
        title=title,
        description=description,
        category=category,
        video_file=video_file,
        uploaded_by=request.user,
    )

    if thumbnail_file:
        video.thumbnail = thumbnail_file

    video.save()  # triggers duration detection + auto-thumbnail via model

    messages.success(request, f'"{title}" uploaded successfully!')
    return redirect('streaming:watch', video_id=video.pk)


# ─── Home / Browse ────────────────────────────────────────────────────────────

def home(request):
    """Landing page — shows all videos, optionally filtered by category or search."""
    category_slug = request.GET.get('category')
    search_query = request.GET.get('q', '').strip()
    videos = Video.objects.select_related('category').all()
    categories = Category.objects.all()

    if category_slug:
        videos = videos.filter(category__name__iexact=category_slug)
    if search_query:
        videos = videos.filter(
            Q(title__icontains=search_query) | Q(description__icontains=search_query)
        )

    return render(request, 'home.html', {
        'videos': videos,
        'categories': categories,
        'selected_category': category_slug,
        'search_query': search_query,
    })


# ─── Watch ────────────────────────────────────────────────────────────────────

def watch(request, video_id):
    """Player page — streams a single video."""
    video = get_object_or_404(Video.objects.select_related('category'), pk=video_id)
    Video.objects.filter(pk=video.pk).update(views_count=F('views_count') + 1)
    video.refresh_from_db()

    # Related videos — same category first
    related = Video.objects.exclude(pk=video.pk).select_related('category')
    if video.category:
        from django.db.models import Case, When, Value, IntegerField
        related = related.annotate(
            same_cat=Case(
                When(category=video.category, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        ).order_by('same_cat', '-created_at')[:6]
    else:
        related = related.order_by('-created_at')[:6]

    comments = video.comments.select_related('user').all()

    # What did the current user do?
    user_liked = user_disliked = False
    if request.user.is_authenticated:
        user_liked = Like.objects.filter(user=request.user, video=video).exists()
        user_disliked = Dislike.objects.filter(user=request.user, video=video).exists()

    return render(request, 'watch.html', {
        'video': video,
        'related': related,
        'comments': comments,
        'user_liked': user_liked,
        'user_disliked': user_disliked,
    })


# ─── Like / Dislike ───────────────────────────────────────────────────────────

@login_required
def toggle_like(request, video_id):
    """Toggle like — removes dislike if present."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    video = get_object_or_404(Video, pk=video_id)
    liked = False

    existing_like = Like.objects.filter(user=request.user, video=video).first()
    if existing_like:
        existing_like.delete()
    else:
        Like.objects.create(user=request.user, video=video)
        Dislike.objects.filter(user=request.user, video=video).delete()
        liked = True

    return JsonResponse({
        'liked': liked,
        'like_count': video.like_count,
        'dislike_count': video.dislike_count,
    })


@login_required
def toggle_dislike(request, video_id):
    """Toggle dislike — removes like if present."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    video = get_object_or_404(Video, pk=video_id)
    disliked = False

    existing_dislike = Dislike.objects.filter(user=request.user, video=video).first()
    if existing_dislike:
        existing_dislike.delete()
    else:
        Dislike.objects.create(user=request.user, video=video)
        Like.objects.filter(user=request.user, video=video).delete()
        disliked = True

    return JsonResponse({
        'disliked': disliked,
        'like_count': video.like_count,
        'dislike_count': video.dislike_count,
    })


# ─── Comments ─────────────────────────────────────────────────────────────────

@login_required
def add_comment(request, video_id):
    """Post a comment on a video."""
    if request.method != 'POST':
        return redirect('streaming:watch', video_id=video_id)

    video = get_object_or_404(Video, pk=video_id)
    body = request.POST.get('body', '').strip()

    if body:
        Comment.objects.create(user=request.user, video=video, body=body)
    else:
        messages.error(request, 'Comment cannot be empty.')

    return redirect('streaming:watch', video_id=video_id)


@login_required
def delete_comment(request, comment_id):
    """Delete a comment — only the author can do this."""
    comment = get_object_or_404(Comment, pk=comment_id, user=request.user)
    video_id = comment.video.pk
    comment.delete()
    return redirect('streaming:watch', video_id=video_id)


# ─── Auth ─────────────────────────────────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect('streaming:home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')

        if not username or not password:
            messages.error(request, 'Username and password are required.')
        elif password != password2:
            messages.error(request, 'Passwords do not match.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            messages.success(request, f'Welcome, {username}!')
            return redirect('streaming:home')

    return render(request, 'auth/register.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('streaming:home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            next_url = request.GET.get('next', '')
            return redirect(next_url if next_url else 'streaming:home')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'auth/login.html')


def logout_view(request):
    logout(request)
    return redirect('streaming:home')


# ─── Streaming ────────────────────────────────────────────────────────────────

def stream_video(request, video_id):
    """Stream a video file with HTTP Range support for proper seeking."""
    video = get_object_or_404(Video, pk=video_id)
    file_path = video.video_file.path

    if not os.path.exists(file_path):
        raise Http404("Video file not found.")

    file_size = os.path.getsize(file_path)
    content_type, _ = mimetypes.guess_type(file_path)
    content_type = content_type or 'application/octet-stream'

    range_header = request.META.get('HTTP_RANGE', '').strip()
    range_start = 0
    range_end = file_size - 1
    chunk_size = 1024 * 1024 * 2

    if range_header.startswith('bytes='):
        ranges = range_header[6:].split('-')
        range_start = int(ranges[0]) if ranges[0] else 0
        range_end = int(ranges[1]) if ranges[1] else min(range_start + chunk_size, file_size) - 1

    range_end = min(range_end, file_size - 1)
    content_length = range_end - range_start + 1

    def file_iterator():
        with open(file_path, 'rb') as f:
            f.seek(range_start)
            remaining = content_length
            while remaining > 0:
                read_size = min(8192, remaining)
                data = f.read(read_size)
                if not data:
                    break
                remaining -= len(data)
                yield data

    response = StreamingHttpResponse(file_iterator(), status=206, content_type=content_type)
    response['Content-Length'] = content_length
    response['Content-Range'] = f'bytes {range_start}-{range_end}/{file_size}'
    response['Accept-Ranges'] = 'bytes'
    return response
