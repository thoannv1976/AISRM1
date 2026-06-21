"""AI configuration service: API key management, provider resolution, usage."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.providers import LLMProvider, MeteredLLM, build_llm
from app.core.config import settings
from app.core.crypto import decrypt, encrypt, last4
from app.models.ai import AIJob, AISetting, AIUsageLedger

# Approximate public prices (USD per 1M tokens). Configurable; estimates only.
MODEL_PRICES: dict[str, tuple[float, float]] = {
    "claude-opus-4-8": (15.0, 75.0),
    "claude-opus-4": (15.0, 75.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-sonnet-4": (3.0, 15.0),
    "claude-haiku-4-5": (0.8, 4.0),
    "mock-llm-1": (0.0, 0.0),
}
_DEFAULT_PRICE = (3.0, 15.0)

AVAILABLE_MODELS = [
    "claude-opus-4-8",
    "claude-sonnet-4-6",
    "claude-haiku-4-5",
]


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    pin, pout = MODEL_PRICES.get(model, _DEFAULT_PRICE)
    cost = (input_tokens / 1_000_000) * pin + (output_tokens / 1_000_000) * pout
    return Decimal(str(round(cost, 6)))


def get_setting(db: Session, org_id: uuid.UUID) -> AISetting:
    setting = db.scalar(select(AISetting).where(AISetting.organization_id == org_id))
    if setting is None:
        setting = AISetting(
            organization_id=org_id,
            mode="AUTO",
            provider="anthropic",
            llm_model=settings.llm_model,
        )
        db.add(setting)
        db.flush()
    return setting


def _api_key(setting: AISetting) -> tuple[str | None, str]:
    """Return (api_key, source) where source ∈ DB | ENV | NONE."""
    if setting.api_key_encrypted:
        key = decrypt(setting.api_key_encrypted)
        if key:
            return key, "DB"
    if settings.anthropic_api_key:
        return settings.anthropic_api_key, "ENV"
    return None, "NONE"


def effective(setting: AISetting) -> tuple[str, str, str | None, str]:
    """Resolve (provider, model, api_key, key_source) honouring the mode."""
    key, source = _api_key(setting)
    model = setting.llm_model
    if setting.mode == "MOCK":
        return "mock", model, None, source
    if setting.mode == "CLAUDE":
        return setting.provider, model, key, source
    # AUTO: use the real provider only when a key is available.
    if key:
        return setting.provider, model, key, source
    return "mock", model, None, source


def effective_label(setting: AISetting) -> str:
    provider, _, _, _ = effective(setting)
    return "Claude API (chấm thật)" if provider == "anthropic" else "Mock (offline)"


def resolve_metered_llm(db: Session, org_id: uuid.UUID) -> tuple[MeteredLLM, str]:
    """Build the metered LLM for a request and the resolved model id."""
    setting = get_setting(db, org_id)
    provider, model, key, _ = effective(setting)
    inner: LLMProvider = build_llm(provider, model, key)
    return MeteredLLM(inner), model


def masked(setting: AISetting) -> dict:
    _, source = _api_key(setting)
    provider, model, _, _ = effective(setting)
    return {
        "mode": setting.mode,
        "provider": setting.provider,
        "llm_model": setting.llm_model,
        "embedding_model": setting.embedding_model,
        "monthly_budget": float(setting.monthly_budget or 0),
        "currency": setting.currency,
        "api_key_masked": f"••••{setting.api_key_last4}" if setting.api_key_last4 else None,
        "api_key_source": source,
        "effective_provider": provider,
        "effective_label": effective_label(setting),
        "effective_model": model,
        "available_models": AVAILABLE_MODELS,
        "last_test_at": setting.last_test_at.isoformat() if setting.last_test_at else None,
        "last_test_ok": setting.last_test_ok,
        "last_test_message": setting.last_test_message,
    }


def save_config(
    db: Session,
    setting: AISetting,
    *,
    mode: str | None = None,
    provider: str | None = None,
    llm_model: str | None = None,
    monthly_budget: float | None = None,
    api_key: str | None = None,
    clear_key: bool = False,
) -> AISetting:
    if mode is not None:
        setting.mode = mode
    if provider is not None:
        setting.provider = provider
    if llm_model:
        setting.llm_model = llm_model
    if monthly_budget is not None:
        setting.monthly_budget = Decimal(str(monthly_budget))
    if clear_key:
        setting.api_key_encrypted = None
        setting.api_key_last4 = None
    elif api_key:  # empty string => keep current key
        setting.api_key_encrypted = encrypt(api_key.strip())
        setting.api_key_last4 = last4(api_key.strip())
    setting.version += 1
    db.flush()
    return setting


def usage_summary(db: Session, org_id: uuid.UUID) -> dict:
    row = db.execute(
        select(
            func.count(AIUsageLedger.id),
            func.coalesce(func.sum(AIUsageLedger.input_tokens), 0),
            func.coalesce(func.sum(AIUsageLedger.output_tokens), 0),
            func.coalesce(func.sum(AIUsageLedger.estimated_cost), 0),
        ).where(AIUsageLedger.organization_id == org_id)
    ).one()
    jobs = db.scalar(select(func.count(AIJob.id)).where(AIJob.organization_id == org_id)) or 0
    in_tok, out_tok = int(row[1]), int(row[2])
    setting = get_setting(db, org_id)
    return {
        "calls": int(row[0]),
        "jobs": int(jobs),
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "total_tokens": in_tok + out_tok,
        "estimated_cost": float(row[3]),
        "currency": "USD",
        "monthly_budget": float(setting.monthly_budget or 0),
    }


def test_connection(db: Session, setting: AISetting) -> dict:
    """Run a tiny probe through the effective provider."""
    provider, model, key, _ = effective(setting)
    started = datetime.now(tz=UTC)
    ok = False
    message = ""
    try:
        if provider != "anthropic":
            message = "Đang dùng mock (offline) — không gọi Claude. Đặt mode=CLAUDE và nạp API key để chấm thật."
            ok = True if setting.mode == "MOCK" else False
            if setting.mode == "AUTO" and not key:
                message = "Chưa có API key — hệ thống tự dùng mock. Nạp key để bật Claude."
        else:
            llm = build_llm(provider, model, key)
            res = llm.complete("You are a connection test.", "Reply with: OK", max_tokens=8)
            ok = bool(res.text)
            message = f"Kết nối thành công · model {res.model_id}"
    except Exception as exc:  # noqa: BLE001
        ok = False
        message = f"Lỗi kết nối: {str(exc)[:300]}"
    latency = int((datetime.now(tz=UTC) - started).total_seconds() * 1000)
    setting.last_test_at = datetime.now(tz=UTC)
    setting.last_test_ok = ok
    setting.last_test_message = message
    db.flush()
    return {
        "ok": ok,
        "message": message,
        "latency_ms": latency,
        "provider": provider,
        "model": model,
    }
