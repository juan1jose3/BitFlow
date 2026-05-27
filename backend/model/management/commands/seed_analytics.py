"""
Seed command — populates the analytics, recommendation, and subscription
tables with realistic dummy data for demonstration purposes.

Usage:
    python manage.py seed_analytics
    python manage.py seed_analytics --clear   # wipe existing data first
"""
import random
from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from backend.model.models import Video
from backend.model.analytics_models import (
    WatchEvent, RetentionPoint, VideoRecommendation,
    SubscriptionPlan, UserSubscription, CdnDeliveryLog,
)

COUNTRIES = ['US', 'MX', 'BR', 'GB', 'DE', 'FR', 'JP', 'IN', 'CA', 'AU', 'ES', 'KR']
CITIES = ['New York', 'Mexico City', 'São Paulo', 'London', 'Berlin', 'Paris',
          'Tokyo', 'Mumbai', 'Toronto', 'Sydney', 'Madrid', 'Seoul']
DEVICES = ['desktop', 'mobile', 'tablet', 'tv']
DEVICE_WEIGHTS = [0.52, 0.33, 0.10, 0.05]
QUALITIES = ['360p', '480p', '720p', '1080p', 'auto']
EDGE_LOCATIONS = ['MIA', 'LAX', 'ORD', 'AMS', 'SIN', 'NRT', 'GRU', 'SYD', 'LHR', 'CDG']
CACHE_STATUSES = ['HIT', 'HIT', 'HIT', 'MISS', 'EXPIRED', 'BYPASS']  # weighted towards HIT


class Command(BaseCommand):
    help = 'Seed the DB with realistic dummy analytics, recommendations, and subscription data.'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Clear existing data before seeding')

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            CdnDeliveryLog.objects.all().delete()
            WatchEvent.objects.all().delete()
            RetentionPoint.objects.all().delete()
            VideoRecommendation.objects.all().delete()
            UserSubscription.objects.all().delete()
            SubscriptionPlan.objects.all().delete()

        videos = list(Video.objects.all())
        users = list(User.objects.all())

        if not videos:
            self.stdout.write(self.style.WARNING('No videos found — upload some first.'))
            return

        # ── Subscription Plans ──────────────────────────────────────────────
        self.stdout.write('Creating subscription plans...')
        plans_data = [
            dict(name='Free', slug='free', price_usd=Decimal('0.00'),
                 max_upload_mb=500, max_quality='720p', analytics_enabled=False,
                 description='Basic streaming, up to 720p, 500 MB uploads.'),
            dict(name='Creator', slug='creator', price_usd=Decimal('9.99'),
                 max_upload_mb=5000, max_quality='1080p', analytics_enabled=True,
                 description='Full analytics, 1080p streaming, 5 GB uploads.'),
            dict(name='Pro', slug='pro', price_usd=Decimal('24.99'),
                 max_upload_mb=50000, max_quality='4K', analytics_enabled=True,
                 description='Unlimited uploads, 4K, priority CDN, API access.'),
        ]
        plans = []
        for pd in plans_data:
            plan, _ = SubscriptionPlan.objects.get_or_create(slug=pd['slug'], defaults=pd)
            plans.append(plan)
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(plans)} plans'))

        # ── User Subscriptions ──────────────────────────────────────────────
        if users:
            self.stdout.write('Assigning subscriptions to users...')
            count = 0
            for user in users:
                if not UserSubscription.objects.filter(user=user).exists():
                    plan = random.choice(plans)
                    now = timezone.now()
                    UserSubscription.objects.create(
                        user=user,
                        plan=plan,
                        status=random.choice(['active', 'active', 'active', 'trialing']),
                        stripe_subscription_id=f'sub_fake_{user.pk}',
                        current_period_start=now - timedelta(days=random.randint(0, 28)),
                        current_period_end=now + timedelta(days=random.randint(1, 30)),
                    )
                    count += 1
            self.stdout.write(self.style.SUCCESS(f'  ✓ {count} subscriptions'))

        # ── Watch Events ────────────────────────────────────────────────────
        self.stdout.write('Generating watch events...')
        events_created = 0
        for video in videos:
            n_events = random.randint(40, 200)
            for _ in range(n_events):
                completion = random.betavariate(2, 1.5)  # realistic drop-off curve
                duration_s = int((video.duration.total_seconds() if video.duration else 300) * completion)
                country = random.choice(COUNTRIES)
                city = CITIES[COUNTRIES.index(country)]
                WatchEvent.objects.create(
                    user=random.choice(users) if users and random.random() > 0.3 else None,
                    video=video,
                    watch_duration_s=duration_s,
                    completion_pct=round(completion, 4),
                    device_type=random.choices(DEVICES, weights=DEVICE_WEIGHTS)[0],
                    country_code=country,
                    city=city,
                    quality_watched=random.choice(QUALITIES),
                    buffering_events=random.choices([0, 1, 2, 3], weights=[0.7, 0.2, 0.07, 0.03])[0],
                    created_at=timezone.now() - timedelta(
                        days=random.randint(0, 90),
                        hours=random.randint(0, 23),
                    ),
                )
                events_created += 1
        self.stdout.write(self.style.SUCCESS(f'  ✓ {events_created} watch events'))

        # ── Retention Curves ────────────────────────────────────────────────
        self.stdout.write('Building retention curves...')
        rp_created = 0
        for video in videos:
            RetentionPoint.objects.filter(video=video).delete()
            retention = 1.0
            for pos in range(0, 101, 2):
                if pos > 0:
                    drop = random.uniform(0.005, 0.025)
                    if pos in range(25, 35):    # mid-video dip
                        drop *= 1.8
                    if pos in range(85, 95):    # end-of-video drop
                        drop *= 2.2
                    retention = max(0.05, retention - drop)
                RetentionPoint.objects.create(
                    video=video,
                    position_pct=pos,
                    viewer_pct=round(retention, 4),
                )
                rp_created += 1
        self.stdout.write(self.style.SUCCESS(f'  ✓ {rp_created} retention points'))

        # ── Video Recommendations ───────────────────────────────────────────
        if len(videos) > 1:
            self.stdout.write('Computing recommendation scores...')
            rec_created = 0
            for video in videos:
                candidates = [v for v in videos if v.pk != video.pk]
                for target in random.sample(candidates, min(len(candidates), 6)):
                    score = round(random.uniform(0.3, 0.97), 4)
                    reason = random.choice(['collaborative', 'content_based', 'same_category', 'trending'])
                    VideoRecommendation.objects.get_or_create(
                        source_video=video,
                        target_video=target,
                        defaults={'score': score, 'reason': reason},
                    )
                    rec_created += 1
            self.stdout.write(self.style.SUCCESS(f'  ✓ {rec_created} recommendation pairs'))

        # ── CDN Delivery Logs ───────────────────────────────────────────────
        self.stdout.write('Simulating CDN delivery logs...')
        cdn_created = 0
        for video in videos:
            for _ in range(random.randint(80, 300)):
                CdnDeliveryLog.objects.create(
                    video=video,
                    edge_location=random.choice(EDGE_LOCATIONS),
                    bytes_served=random.randint(512_000, 8_000_000),
                    cache_status=random.choice(CACHE_STATUSES),
                    status_code=random.choices([206, 200, 304], weights=[0.85, 0.10, 0.05])[0],
                    response_time_ms=random.randint(8, 180),
                    timestamp=timezone.now() - timedelta(
                        days=random.randint(0, 30),
                        hours=random.randint(0, 23),
                    ),
                )
                cdn_created += 1
        self.stdout.write(self.style.SUCCESS(f'  ✓ {cdn_created} CDN log entries'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✅  Seed complete!'))
