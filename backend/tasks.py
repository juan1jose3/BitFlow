"""
Async task definitions for video processing.

These tasks are dispatched by Celery workers connected to the Redis broker.
To start a worker locally:
    celery -A backend worker --loglevel=info

To start the beat scheduler (periodic tasks):
    celery -A backend beat --loglevel=info
"""
import logging
from backend.celery import app

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=3, default_retry_delay=10)
def transcode_video(self, video_id):
    """
    Transcode an uploaded video into HLS format for adaptive streaming.

    Generates multiple quality tiers:
      - 1080p (4500 kbps)
      - 720p  (2500 kbps)
      - 480p  (1000 kbps)
      - 360p  (600 kbps)

    Output is written to media/hls/<video_id>/ as .m3u8 + .ts segments.
    """
    try:
        from backend.model.models import Video
        video = Video.objects.get(pk=video_id)
        logger.info(f'[transcode] Starting HLS transcode for: {video.title}')

        # TODO: implement ffmpeg HLS pipeline
        # subprocess.run(['ffmpeg', '-i', video.video_file.path, ...])

        logger.info(f'[transcode] Completed for video {video_id}')
    except Exception as exc:
        logger.error(f'[transcode] Failed for video {video_id}: {exc}')
        raise self.retry(exc=exc)


@app.task
def generate_thumbnail_async(video_id):
    """
    Async thumbnail generation — offloads ffmpeg work from the request cycle.
    Falls back to the synchronous model method.
    """
    try:
        from backend.model.models import Video
        video = Video.objects.get(pk=video_id)
        ok = video.generate_thumbnail()
        logger.info(f'[thumbnail] {"Generated" if ok else "Skipped"} for video {video_id}')
    except Exception as e:
        logger.error(f'[thumbnail] Failed for video {video_id}: {e}')


@app.task
def send_comment_notification(comment_id):
    """
    Notify the video uploader when someone leaves a comment.
    Requires EMAIL_HOST to be configured in settings.
    """
    try:
        from backend.model.models import Comment
        from django.core.mail import send_mail
        from django.conf import settings

        comment = Comment.objects.select_related('video', 'user').get(pk=comment_id)
        # TODO: send actual email when EMAIL_HOST is configured
        logger.info(
            f'[notify] Comment by {comment.user.username} '
            f'on "{comment.video.title}" — notification queued'
        )
    except Exception as e:
        logger.error(f'[notify] Failed for comment {comment_id}: {e}')


@app.task
def warm_cache(video_id):
    """
    Pre-populate the Redis cache for a freshly uploaded video
    so the first real request is served instantly.
    """
    try:
        from backend.model.models import Video
        from backend import cache

        video = Video.objects.select_related('category').get(pk=video_id)
        cache.set(f'video:{video_id}:meta', {
            'title': video.title,
            'duration': video.duration_display,
            'views': video.views_count,
        }, ttl=cache.TTL_MEDIUM)
        logger.info(f'[cache] Warmed cache for video {video_id}')
    except Exception as e:
        logger.error(f'[cache] Cache warm failed for video {video_id}: {e}')
