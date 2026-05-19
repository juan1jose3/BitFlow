from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta
import subprocess
import tempfile
import uuid
import os


def _run_ffmpeg_thumbnail(video_path, output_path):
    """Extract a frame at 1s with ffmpeg. Returns True on success."""
    result = subprocess.run(
        [
            'ffmpeg', '-y',
            '-ss', '00:00:01',
            '-i', video_path,
            '-vframes', '1',
            '-q:v', '2',
            output_path,
        ],
        capture_output=True,
        timeout=30,
    )
    return (
        result.returncode == 0
        and os.path.exists(output_path)
        and os.path.getsize(output_path) > 0
    )


class Category(models.Model):
    """Genre / category for videos."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Video(models.Model):
    """A single streamable video."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='videos',
    )
    video_file = models.FileField(upload_to='videos/')
    thumbnail = models.ImageField(upload_to='thumbnails/', blank=True, null=True)
    duration = models.DurationField(blank=True, null=True, help_text='Auto-filled on upload')
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def duration_display(self):
        if not self.duration:
            return ''
        total = int(self.duration.total_seconds())
        hours, remainder = divmod(total, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f'{hours}:{minutes:02d}:{seconds:02d}'
        return f'{minutes}:{seconds:02d}'

    @property
    def file_size_mb(self):
        try:
            return round(self.video_file.size / (1024 * 1024), 1)
        except (FileNotFoundError, ValueError):
            return 0

    @property
    def like_count(self):
        return self.likes.count()

    @property
    def dislike_count(self):
        return self.dislikes.count()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        video_path = self.video_file.path if self.video_file else None
        if not video_path or not os.path.exists(video_path):
            return

        # ── Auto-detect duration via ffprobe ──
        if not self.duration:
            try:
                result = subprocess.run(
                    [
                        'ffprobe', '-v', 'error',
                        '-show_entries', 'format=duration',
                        '-of', 'default=noprint_wrappers=1:nokey=1',
                        video_path,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0 and result.stdout.strip():
                    seconds = float(result.stdout.strip())
                    Video.objects.filter(pk=self.pk).update(
                        duration=timedelta(seconds=seconds)
                    )
            except Exception:
                pass

        # ── Auto-generate thumbnail via ffmpeg ──
        if not self.thumbnail:
            self.generate_thumbnail()

    def generate_thumbnail(self):
        """Extract a frame at 1s and attach it as the thumbnail. Safe to call manually."""
        from django.core.files import File

        video_path = self.video_file.path if self.video_file else None
        if not video_path or not os.path.exists(video_path):
            return False

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                tmp_path = tmp.name

            if _run_ffmpeg_thumbnail(video_path, tmp_path):
                thumb_name = f'thumbnails/auto_{self.pk}.jpg'
                with open(tmp_path, 'rb') as f:
                    # Use update() to avoid triggering save() recursion
                    from django.core.files.base import ContentFile
                    content = f.read()

                from django.core.files.storage import default_storage
                saved_path = default_storage.save(thumb_name, ContentFile(content))
                Video.objects.filter(pk=self.pk).update(thumbnail=saved_path)
                self.thumbnail = saved_path
                return True

        except Exception:
            pass
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        return False


class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'video')

    def __str__(self):
        return f'{self.user.username} likes {self.video.title}'


class Dislike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dislikes')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='dislikes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'video')

    def __str__(self):
        return f'{self.user.username} dislikes {self.video.title}'


class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='comments')
    body = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} on {self.video.title}'
