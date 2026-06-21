"""Authentication endpoints (local/JWT; SSO-ready)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import Principal, get_principal
from app.core.errors import AuthUnauthorized
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.identity import Session as SessionModel
from app.models.identity import User
from app.schemas.auth import LoginIn, MeOut, RefreshIn, TokenOut, UserOut
from app.services import audit

router = APIRouter()


@router.post("/auth/login", response_model=TokenOut)
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)) -> TokenOut:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if (
        not user
        or not user.password_hash
        or not verify_password(payload.password, user.password_hash)
    ):
        audit.record(
            db,
            action="auth.login.failed",
            actor_email=payload.email,
            metadata={"reason": "bad_credentials"},
        )
        raise AuthUnauthorized("Email hoặc mật khẩu không đúng.")
    if user.status in {"DISABLED", "SUSPENDED"}:
        raise AuthUnauthorized("Tài khoản bị khóa.")

    claims = {"org": str(user.organization_id), "email": user.email}
    access = create_access_token(str(user.id), claims)
    refresh = create_refresh_token(str(user.id))
    refresh_payload = decode_token(refresh)
    db.add(
        SessionModel(
            user_id=user.id,
            refresh_jti=refresh_payload["jti"],
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent", "")[:255],
            expires_at=datetime.now(tz=UTC) + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    user.last_login_at = datetime.now(tz=UTC)
    audit.record(
        db,
        action="auth.login",
        actor_id=user.id,
        actor_email=user.email,
        organization_id=user.organization_id,
    )
    return TokenOut(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/auth/refresh", response_model=TokenOut)
def refresh(payload: RefreshIn, db: Session = Depends(get_db)) -> TokenOut:
    try:
        data = decode_token(payload.refresh_token)
    except Exception as exc:  # noqa: BLE001
        raise AuthUnauthorized("Refresh token không hợp lệ.") from exc
    if data.get("type") != "refresh":
        raise AuthUnauthorized("Token không hợp lệ.")
    sess = db.scalar(select(SessionModel).where(SessionModel.refresh_jti == data["jti"]))
    if not sess or sess.revoked:
        raise AuthUnauthorized("Phiên đã bị thu hồi.")
    user = db.get(User, uuid.UUID(data["sub"]))
    if not user:
        raise AuthUnauthorized("Người dùng không tồn tại.")
    # rotation: revoke old, issue new
    sess.revoked = True
    new_refresh = create_refresh_token(str(user.id))
    new_payload = decode_token(new_refresh)
    db.add(
        SessionModel(
            user_id=user.id,
            refresh_jti=new_payload["jti"],
            expires_at=datetime.now(tz=UTC) + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    access = create_access_token(
        str(user.id), {"org": str(user.organization_id), "email": user.email}
    )
    return TokenOut(
        access_token=access,
        refresh_token=new_refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/auth/logout")
def logout(payload: RefreshIn, db: Session = Depends(get_db)) -> dict:
    try:
        data = decode_token(payload.refresh_token)
        sess = db.scalar(select(SessionModel).where(SessionModel.refresh_jti == data.get("jti")))
        if sess:
            sess.revoked = True
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True}


@router.get("/me", response_model=MeOut)
def me(principal: Principal = Depends(get_principal)) -> MeOut:
    return MeOut(
        user=UserOut.model_validate(principal.user),
        permissions=sorted(principal.permissions),
        system_roles=sorted(principal.system_roles),
        is_admin=principal.is_admin(),
    )
