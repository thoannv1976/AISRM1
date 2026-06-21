"""FastAPI application entrypoint."""

from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import api_router
from app.core.config import settings
from app.core.db import engine
from app.core.errors import register_exception_handlers

app = FastAPI(
    title="AISRM1 — AI-ResearchHub API",
    version="1.0.0",
    description=(
        "AI-integrated Scientific Research Management System for a university "
        "Research Management Office. Human-in-the-loop AI; RBAC + entity scope."
    ),
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Trace-Id"],
)

register_exception_handlers(app)


@app.middleware("http")
async def add_trace_id(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    return response


@app.get("/health", tags=["system"])
def health() -> dict:
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "service": "aisrm1-api",
        "version": "1.0.0",
        "env": settings.app_env,
        "db": db_ok,
    }


@app.get("/", tags=["system"])
def root() -> dict:
    return {
        "name": "AISRM1 — AI-ResearchHub",
        "docs": "/docs",
        "health": "/health",
        "api": settings.api_v1_prefix,
    }


app.include_router(api_router, prefix=settings.api_v1_prefix)
