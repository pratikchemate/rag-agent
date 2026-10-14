"""Storage service for persisting original source documents."""

import re
from pathlib import Path
from typing import Optional
from uuid import UUID

import httpx

from app.core.config import get_settings
from app.core.errors import ServiceUnavailableError
from app.core.logging import get_logger

logger = get_logger(__name__)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal or invalid characters."""
    clean = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", filename)
    return clean[:128]


class StorageService:
    """Handles object storage for source documents via Supabase Storage or local fallback."""

    def __init__(self):
        self.settings = get_settings()
        self.bucket = self.settings.SUPABASE_STORAGE_BUCKET
        self.use_supabase = bool(
            self.settings.SUPABASE_URL
            and (self.settings.get_supabase_secret_key() or self.settings.SUPABASE_PUBLISHABLE_KEY)
        )
        self.local_cache_dir = Path(self.settings.STORAGE_LOCAL_FALLBACK_DIR)
        if not self.use_supabase:
            self.local_cache_dir.mkdir(parents=True, exist_ok=True)

    def generate_storage_path(self, owner_id: UUID, document_id: UUID, filename: str) -> str:
        """Create structured object path: {owner_id}/{document_id}/{safe_filename}."""
        safe_name = sanitize_filename(filename)
        return f"{owner_id}/{document_id}/{safe_name}"

    def upload_file(self, storage_path: str, content: bytes, content_type: str) -> str:
        """Upload file to storage and return storage path."""
        if self.use_supabase:
            api_key = (
                self.settings.get_supabase_secret_key() or self.settings.SUPABASE_PUBLISHABLE_KEY
            )
            url = f"{self.settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/{self.bucket}/{storage_path}"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "apikey": api_key,
                "Content-Type": content_type,
            }
            try:
                response = httpx.post(url, content=content, headers=headers, timeout=30.0)
                if response.status_code in (200, 201):
                    return storage_path
                # Check conflict
                if response.status_code == 400 and "Duplicate" in response.text:
                    return storage_path

                logger.warning(
                    f"Supabase storage upload returned {response.status_code}: {response.text}"
                )
                if self.settings.ENVIRONMENT == "production":
                    raise ServiceUnavailableError(
                        f"Object storage upload failed with status {response.status_code}"
                    )
            except Exception as e:
                logger.error(f"Error uploading to Supabase storage: {str(e)}")
                if self.settings.ENVIRONMENT == "production":
                    raise ServiceUnavailableError("Object storage service is unavailable.")
                # Fall back to local storage only in non-production environments
                pass

        # Local storage fallback (non-production only)
        dest_path = self.local_cache_dir / storage_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(content)
        return storage_path

    def delete_file(self, storage_path: str) -> bool:
        """Remove file from storage."""
        supabase_success = True
        if self.use_supabase:
            api_key = (
                self.settings.get_supabase_secret_key() or self.settings.SUPABASE_PUBLISHABLE_KEY
            )
            url = f"{self.settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/{self.bucket}/{storage_path}"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "apikey": api_key,
            }
            try:
                resp = httpx.delete(url, headers=headers, timeout=15.0)
                supabase_success = resp.status_code in (200, 204, 404)
            except Exception as e:
                logger.warning(f"Failed to delete from Supabase storage: {str(e)}")
                supabase_success = False

        dest_path = self.local_cache_dir / storage_path
        local_deleted = True
        if dest_path.exists():
            try:
                dest_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete local fallback file: {str(e)}")
                local_deleted = False

        return supabase_success and local_deleted


_default_storage: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Return default storage service."""
    global _default_storage
    if _default_storage is None:
        _default_storage = StorageService()
    return _default_storage
