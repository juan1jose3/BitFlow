"""
Management command to generate missing thumbnails for all videos.

Usage:
    python manage.py generate_thumbnails           # all videos without thumbnail
    python manage.py generate_thumbnails --all     # regenerate even existing thumbnails
"""
from django.core.management.base import BaseCommand
from backend.model.models import Video


class Command(BaseCommand):
    help = 'Auto-generate thumbnails for videos that are missing one.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            dest='regenerate_all',
            help='Regenerate thumbnails even for videos that already have one.',
        )

    def handle(self, *args, **options):
        regenerate_all = options['regenerate_all']

        if regenerate_all:
            videos = Video.objects.all()
            self.stdout.write(f'Regenerating thumbnails for all {videos.count()} videos...')
        else:
            videos = Video.objects.filter(thumbnail='')
            self.stdout.write(f'Found {videos.count()} video(s) without a thumbnail.')

        success = 0
        failed = 0

        for video in videos:
            self.stdout.write(f'  → {video.title[:60]}...', ending=' ')
            ok = video.generate_thumbnail()
            if ok:
                self.stdout.write(self.style.SUCCESS('✓'))
                success += 1
            else:
                self.stdout.write(self.style.WARNING('✗ skipped (file missing or ffmpeg error)'))
                failed += 1

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Done: {success} generated, {failed} skipped.'))
