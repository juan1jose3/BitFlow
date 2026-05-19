# CDN storage layer — Cloudflare R2 / S3-compatible backend
from backend.cdn.storage import get_storage_backend, cdn_url, purge_cache

__all__ = ['get_storage_backend', 'cdn_url', 'purge_cache']
