"""Provider-agnostic LLM and Embedding abstractions.

Local/dev default is a deterministic *mock* provider so the app runs fully
offline. Production can switch to Anthropic (direct API) or Vertex AI via
environment variables — without touching business logic.
"""

from __future__ import annotations

import hashlib
import json
import math
from contextvars import ContextVar
from dataclasses import dataclass

from app.core.config import settings


@dataclass
class LLMResult:
    text: str
    model_id: str
    input_tokens: int = 0
    output_tokens: int = 0


class LLMProvider:
    """Interface: turn a system+user prompt into text (optionally JSON)."""

    name = "base"

    def complete(
        self,
        system: str,
        user: str,
        *,
        json_mode: bool = False,
        max_tokens: int = 2000,
        temperature: float = 0.2,
    ) -> LLMResult:  # pragma: no cover - interface
        raise NotImplementedError


class EmbeddingProvider:
    name = "base"
    dim = settings.embedding_dim

    def embed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover
        raise NotImplementedError


class MeteredLLM(LLMProvider):
    """Wraps a provider and accumulates token/call usage for one request."""

    def __init__(self, inner: LLMProvider):
        self.inner = inner
        self.name = inner.name
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.model_id = getattr(inner, "_model", None) or "mock-llm-1"

    def complete(self, system, user, *, json_mode=False, max_tokens=2000, temperature=0.2):
        res = self.inner.complete(
            system, user, json_mode=json_mode, max_tokens=max_tokens, temperature=temperature
        )
        self.calls += 1
        self.input_tokens += res.input_tokens or 0
        self.output_tokens += res.output_tokens or 0
        self.model_id = res.model_id
        return res


# ---------------------------------------------------------------------------
# Mock providers (deterministic, offline)
# ---------------------------------------------------------------------------
class MockLLM(LLMProvider):
    name = "mock"

    def complete(self, system, user, *, json_mode=False, max_tokens=2000, temperature=0.2):
        # Deterministic, grounded-looking output. Real reasoning happens in
        # feature builders; the mock simply echoes a structured envelope so the
        # full pipeline (validation, citations, persistence) can be exercised.
        if json_mode:
            text = json.dumps(
                {
                    "summary": _excerpt(user, 600),
                    "findings": [],
                    "insufficient_evidence": False,
                    "limitations": ["Sinh bởi mock provider (môi trường offline)."],
                },
                ensure_ascii=False,
            )
        else:
            text = _excerpt(user, 800)
        return LLMResult(
            text=text,
            model_id="mock-llm-1",
            input_tokens=_approx_tokens(system + user),
            output_tokens=_approx_tokens(text),
        )


class MockEmbedding(EmbeddingProvider):
    name = "mock"

    def __init__(self, dim: int | None = None):
        self.dim = dim or settings.embedding_dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [_hash_vector(t, self.dim) for t in texts]


# ---------------------------------------------------------------------------
# Anthropic provider (optional; requires `anthropic` + API key)
# ---------------------------------------------------------------------------
class AnthropicLLM(LLMProvider):
    name = "anthropic"

    def __init__(self, model: str, api_key: str):
        import anthropic  # lazy import

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def complete(self, system, user, *, json_mode=False, max_tokens=2000, temperature=0.2):
        if json_mode:
            system = system + "\nReturn ONLY valid JSON, no prose."
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(block.text for block in msg.content if getattr(block, "type", "") == "text")
        usage = getattr(msg, "usage", None)
        return LLMResult(
            text=text,
            model_id=self._model,
            input_tokens=getattr(usage, "input_tokens", 0) if usage else 0,
            output_tokens=getattr(usage, "output_tokens", 0) if usage else 0,
        )


# ---------------------------------------------------------------------------
# Factories & per-request override
# ---------------------------------------------------------------------------
_llm_override: ContextVar[LLMProvider | None] = ContextVar("llm_override", default=None)


def set_llm_override(llm: LLMProvider | None) -> None:
    """Bind the LLM used by feature builders for the current request/job."""
    _llm_override.set(llm)


def build_llm(provider: str, model: str, api_key: str | None) -> LLMProvider:
    """Construct a concrete provider; fall back to mock if not available."""
    provider = (provider or "mock").lower()
    if provider == "anthropic" and api_key:
        try:
            return AnthropicLLM(model, api_key)
        except Exception:  # noqa: BLE001 - SDK missing or bad key -> mock
            return MockLLM()
    return MockLLM()


def get_llm() -> LLMProvider:
    override = _llm_override.get()
    if override is not None:
        return override
    return build_llm(settings.llm_provider, settings.llm_model, settings.anthropic_api_key)


def get_embedder() -> EmbeddingProvider:
    # Only the mock embedder is bundled for offline use; production wires the
    # configured provider here.
    return MockEmbedding()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _excerpt(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text[:limit]


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _hash_vector(text: str, dim: int) -> list[float]:
    """Deterministic pseudo-embedding from sha256 of the text."""
    vec: list[float] = []
    counter = 0
    while len(vec) < dim:
        h = hashlib.sha256(f"{text}|{counter}".encode()).digest()
        for i in range(0, len(h), 2):
            if len(vec) >= dim:
                break
            val = int.from_bytes(h[i : i + 2], "big") / 65535.0 - 0.5
            vec.append(val)
        counter += 1
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]
