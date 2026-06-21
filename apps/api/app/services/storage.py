"""Object-storage abstraction: local filesystem (dev), MinIO/GCS (prod).

For the local driver, upload/download flow through internal API endpoints so the
"signed URL" pattern is preserved end-to-end without external services.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from pathlib import Path

from app.core.config import settings


class StorageService:
    def create_upload_url(self, storage_key: str, *, content_type: str | None = None) -> dict:
        raise NotImplementedError

    def download_url(self, storage_key: str, filename: str, *, expires_in: int = 300) -> str:
        raise NotImplementedError

    def save(self, storage_key: str, data: bytes) -> None:
        raise NotImplementedError

    def read(self, storage_key: str) -> bytes:
        raise NotImplementedError

    def exists(self, storage_key: str) -> bool:
        raise NotImplementedError


class LocalStorage(StorageService):
    def __init__(self, root: str, api_base: str):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.api_base = api_base.rstrip("/")

    def _path(self, storage_key: str) -> Path:
        safe = storage_key.lstrip("/")
        p = (self.root / safe).resolve()
        if not str(p).startswith(str(self.root)):
            raise ValueError("Invalid storage key")
        return p

    def _token(self, storage_key: str) -> str:
        b = base64.urlsafe_b64encode(storage_key.encode()).decode()
        return b

    def create_upload_url(self, storage_key, *, content_type=None):
        return {
            "upload_url": f"{self.api_base}{settings.api_v1_prefix}/documents/_storage/{self._token(storage_key)}",
            "method": "PUT",
            "fields": {},
        }

    def download_url(self, storage_key, filename, *, expires_in=300):
        token = self._token(storage_key)
        exp = int(time.time()) + expires_in
        sig = _sign(f"{token}:{exp}")
        return (
            f"{self.api_base}{settings.api_v1_prefix}/documents/_storage/"
            f"{token}?filename={filename}&exp={exp}&sig={sig}"
        )

    def save(self, storage_key, data):
        p = self._path(storage_key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def read(self, storage_key):
        return self._path(storage_key).read_bytes()

    def exists(self, storage_key):
        return self._path(storage_key).exists()

    @staticmethod
    def decode_token(token: str) -> str:
        return base64.urlsafe_b64decode(token.encode()).decode()

    @staticmethod
    def verify_download_sig(token: str, exp: int, sig: str) -> bool:
        if exp < int(time.time()):
            return False
        return hmac.compare_digest(_sign(f"{token}:{exp}"), sig)


class MinioOrGCSStorage(StorageService):  # pragma: no cover - requires external service
    """Placeholder presigned-URL driver for MinIO/GCS.

    Production wiring uses the storage client to mint real signed PUT/GET URLs.
    Falls back to local behaviour shape so callers stay identical.
    """

    def __init__(self, driver: str):
        self.driver = driver

    def create_upload_url(self, storage_key, *, content_type=None):
        # Real implementation: generate a V4 signed PUT URL.
        raise NotImplementedError(
            f"{self.driver} signed upload not configured in this build; use STORAGE_DRIVER=local"
        )

    def download_url(self, storage_key, filename, *, expires_in=300):
        raise NotImplementedError


_instance: StorageService | None = None


def get_storage() -> StorageService:
    global _instance
    if _instance is None:
        driver = settings.storage_driver.lower()
        if driver in {"minio", "gcs"}:
            _instance = MinioOrGCSStorage(driver)
        else:
            _instance = LocalStorage(settings.storage_local_path, settings.api_base_url)
    return _instance


def _sign(payload: str) -> str:
    return hmac.new(settings.auth_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()[
        :32
    ]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_storage_key(
    org_id, entity_type: str | None, entity_id, document_id, version_no: int, filename: str
) -> str:
    safe = (
        "".join(c for c in filename if c.isalnum() or c in "._- ").strip().replace(" ", "_")
        or "file"
    )
    parts = ["organizations", str(org_id)]
    if entity_type and entity_id:
        parts += [f"{entity_type}s", str(entity_id)]
    parts += ["documents", str(document_id), f"v{version_no}", safe]
    return "/".join(parts)
