"""
Extended analytics, recommendation, and subscription models.

These tables power the recommendation engine, creator analytics dashboard,
and the subscription/monetisation layer of BitFlow.
"""
import uuid
from django.db import models
from django.contrib.auth.models import User
from backend.model.models import Video


class WatchEvent(models.Model):
    """
    Granular watch session tracking.
    One row per play session — records how much of the video was watched,
    what device was used, and from which country.
    Used by the recommendation engine and creator analytics.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='watch_events')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='watch_events')
    session_key = models.CharField(max_length=64, blank=True)       # anonymous sessions
    watch_duration_s = models.PositiveIntegerField(default=0)       # seconds actually watched
    completion_pct = models.FloatField(default=0.0)                 # 0.0–1.0
    device_type = models.CharField(max_length=20, choices=[
        ('desktop', 'Desktop'),
        ('mobile', 'Mobile'),
        ('tablet', 'Tablet'),
        ('tv', 'Smart TV'),
    ], default='desktop')
    country_code = models.CharField(max_length=2, blank=True)       # ISO 3166-1 alpha-2
    city = models.CharField(max_length=100, blank=True)
    quality_watched = models.CharField(max_length=10, default='auto')  # 360p / 720p / 1080p
    buffering_events = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['video', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f'WatchEvent({self.video_id}, {self.completion_pct:.0%})'


class RetentionPoint(models.Model):
    """
    Per-video retention curve data points (0–100% of video timeline).
    Aggregated nightly by the analytics worker from WatchEvent records.
    Used to render the retention graph in the creator dashboard.
    """
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='retention_points')
    position_pct = models.PositiveSmallIntegerField()   # 0–100
    viewer_pct = models.FloatField()                    # fraction of viewers still watching

    class Meta:
        unique_together = ('video', 'position_pct')
        ordering = ['position_pct']

    def __str__(self):
        return f'{self.video_id} @ {self.position_pct}%: {self.viewer_pct:.2f}'


class VideoRecommendation(models.Model):
    """
    Precomputed video-to-video recommendation scores.
    Generated nightly by the collaborative filtering pipeline
    (matrix factorization on the WatchEvent interaction matrix).
    Higher score = stronger recommendation.
    """
    source_video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='recommendations_from')
    target_video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='recommendations_to')
    score = models.FloatField(default=0.0)              # 0.0–1.0 cosine similarity
    reason = models.CharField(max_length=50, choices=[
        ('collaborative', 'Collaborative Filtering'),
        ('content_based', 'Content-Based'),
        ('trending', 'Trending'),
        ('same_category', 'Same Category'),
    ], default='collaborative')
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('source_video', 'target_video')
        ordering = ['-score']

    def __str__(self):
        return f'{self.source_video_id} → {self.target_video_id} ({self.score:.3f})'


class SubscriptionPlan(models.Model):
    """
    Subscription tiers available on the platform.
    Controls upload limits, max video quality, and analytics access.
    """
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    price_usd = models.DecimalField(max_digits=6, decimal_places=2)
    max_upload_mb = models.PositiveIntegerField()
    max_quality = models.CharField(max_length=10, default='1080p')
    analytics_enabled = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.name} (${self.price_usd}/mo)'


class UserSubscription(models.Model):
    """
    A user's active subscription to a plan.
    Billing is handled externally (Stripe webhook updates this record).
    """
    STATUS = [
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('past_due', 'Past Due'),
        ('trialing', 'Trialing'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS, default='active')
    stripe_subscription_id = models.CharField(max_length=100, blank=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} — {self.plan.name} ({self.status})'


class CdnDeliveryLog(models.Model):
    """
    CDN edge delivery log.
    Populated by the Cloudflare R2 webhook on each video segment served.
    Used for bandwidth billing and geographic performance monitoring.
    """
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='cdn_logs')
    edge_location = models.CharField(max_length=10)     # e.g. 'MIA', 'AMS', 'SIN'
    bytes_served = models.PositiveBigIntegerField(default=0)
    cache_status = models.CharField(max_length=10, choices=[
        ('HIT', 'Cache Hit'),
        ('MISS', 'Cache Miss'),
        ('BYPASS', 'Bypass'),
        ('EXPIRED', 'Expired'),
    ], default='HIT')
    status_code = models.PositiveSmallIntegerField(default=206)
    response_time_ms = models.PositiveSmallIntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'CDN {self.edge_location} {self.cache_status} {self.bytes_served}B'
