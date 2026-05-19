
import logging
import functools

logger = logging.getLogger(__name__)

# TTL defaults (seconds)
TTL_SHORT = 60       # 1 minute  — hot data (view counts)
TTL_MEDIUM = 300     # 5 minutes — video metadata
TTL_LONG = 3600      # 1 hour    — category lists


def _get_client():
    """
    Return the Redis client.
    Falls back gracefully to None if Redis is not configured,
    allowing the application to run without caching.
    """
    try:
        from django.core.cache import cache
        return cache
    except Exception:
        return None


def get(key, default=None):
    """Retrieve a value from the cache."""
    client = _get_client()
    if client is None:
        return default
    try:
        value = client.get(key)
        return value if value is not None else default
    except Exception as e:
        logger.warning(f'[cache] GET failed for key={key}: {e}')
        return default


def set(key, value, ttl=TTL_MEDIUM):
    """Store a value in the cache with an optional TTL."""
    client = _get_client()
    if client is None:
        return False
    try:
        client.set(key, value, timeout=ttl)
        return True
    except Exception as e:
        logger.warning(f'[cache] SET failed for key={key}: {e}')
        return False


def delete(key):
    """Invalidate a single cache key."""
    client = _get_client()
    if client is None:
        return
    try:
        client.delete(key)
    except Exception as e:
        logger.warning(f'[cache] DELETE failed for key={key}: {e}')


def invalidate_video(video_id):
    """Invalidate all cache entries related to a specific video."""
    keys = [
        f'video:{video_id}:meta',
        f'video:{video_id}:likes',
        f'video:{video_id}:comments',
        f'video:{video_id}:views',
    ]
    for key in keys:
        delete(key)
    logger.debug(f'[cache] Invalidated {len(keys)} keys for video {video_id}')


def cached(key_fn, ttl=TTL_MEDIUM):

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = key_fn(*args, **kwargs)
            cached_value = get(cache_key)
            if cached_value is not None:
                logger.debug(f'[cache] HIT {cache_key}')
                return cached_value
            result = func(*args, **kwargs)
            set(cache_key, result, ttl=ttl)
            logger.debug(f'[cache] MISS {cache_key} — stored with ttl={ttl}s')
            return result
        return wrapper
    return decorator
