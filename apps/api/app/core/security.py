"""Password hashing and JWT token utilities."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import settings


# ----- Passwords -----
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ----- JWT -----
def _now() -> datetime:
    return datetime.now(tz=UTC)


def create_access_token(subject: str, claims: dict[str, Any] | None = None) -> str:
    expire = _now() + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": "access",
        "iat": _now(),
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    if claims:
        payload.update(claims)
    return jwt.encode(payload, settings.auth_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    expire = _now() + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": subject,
        "type": "refresh",
        "iat": _now(),
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.auth_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.auth_secret, algorithms=[settings.jwt_algorithm])
