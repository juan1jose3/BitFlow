
import logging
import os

logger = logging.getLogger(__name__)

# Feature flag — set USE_CDN=True in .env to enable
_CDN_ENABLED = os.environ.get('USE_CDN', 'False').lower() == 'true'


def get_storage_backend():

    if not _CDN_ENABLED:
        logger.debug('[cdn] CDN disabled — using local FileSystemStorage')
        from django.core.files.storage import FileSystemStorage
        return FileSystemStorage()

    try:
        import boto3  # noqa: F401
        from storages.backends.s3boto3 import S3Boto3Storage

        class R2Storage(S3Boto3Storage):
            bucket_name = os.environ.get('CDN_BUCKET_NAME', 'bitflow-media')
            endpoint_url = os.environ.get('CDN_ENDPOINT_URL', '')
            access_key = os.environ.get('CDN_ACCESS_KEY_ID', '')
            secret_key = os.environ.get('CDN_SECRET_ACCESS_KEY', '')
            custom_domain = os.environ.get('CDN_PUBLIC_BASE_URL', '')
            file_overwrite = False
            default_acl = 'public-read'

        logger.info('[cdn] Using Cloudflare R2 storage backend')
        return R2Storage()

    except ImportError:
        logger.warning(
            '[cdn] USE_CDN=True but boto3/django-storages not installed. '
            'Falling back to local storage. Run: pip install boto3 django-storages'
        )
        from django.core.files.storage import FileSystemStorage
        return FileSystemStorage()


def cdn_url(path):

    if not _CDN_ENABLED or not path:
        from django.conf import settings
        return f'{settings.MEDIA_URL}{path}'

    base = os.environ.get('CDN_PUBLIC_BASE_URL', '').rstrip('/')
    return f'{base}/{path}'


def purge_cache(path):
   
    import requests
    requests.post(
        f'https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/purge_cache',
        headers={'Authorization': f'Bearer {CF_TOKEN}'},
        json={'files': [cdn_url(path)]},
    )
    
    if _CDN_ENABLED:
        logger.info(f'[cdn] Cache purge requested for: {path} (not yet implemented)')
