"""Symmetric encryption for secrets stored at rest (e.g. AI API keys).

Uses Fernet with a key derived from ``AUTH_SECRET``. The plaintext secret is
never returned to clients or written to logs — only an encrypted blob and the
last 4 characters (for display) are persisted.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.auth_secret.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(token: str) -> str | None:
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError):
        return None


def last4(secret: str) -> str:
    return secret[-4:] if secret and len(secret) >= 4 else "****"
