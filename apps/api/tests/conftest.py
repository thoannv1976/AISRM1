"""Pytest fixtures: schema + seed + authenticated TestClient."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.db import engine
from app.main import app
from app.models import Base
from app.seed import seed_all


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        conn.commit()
    Base.metadata.create_all(engine)
    seed_all(demo=True)
    yield


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _login(client: TestClient, email: str, password: str) -> str:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture()
def officer_token(client: TestClient) -> str:
    return _login(client, "officer@aisrm1.edu.vn", "Officer@12345")


@pytest.fixture()
def reviewer_token(client: TestClient) -> str:
    return _login(client, "reviewer@aisrm1.edu.vn", "Reviewer@12345")


@pytest.fixture()
def admin_token(client: TestClient) -> str:
    return _login(client, "admin@aisrm1.edu.vn", "Admin@12345")


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
