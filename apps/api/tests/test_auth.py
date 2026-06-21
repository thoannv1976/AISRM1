"""Auth & RBAC tests."""
from tests.conftest import auth


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_and_me(client, officer_token):
    r = client.get("/api/v1/me", headers=auth(officer_token))
    assert r.status_code == 200
    data = r.json()
    assert data["user"]["email"] == "officer@aisrm1.edu.vn"
    assert len(data["permissions"]) > 0


def test_login_bad_credentials(client):
    r = client.post("/api/v1/auth/login", json={"email": "officer@aisrm1.edu.vn", "password": "wrong"})
    assert r.status_code == 401
    assert r.json()["code"] == "AUTH_UNAUTHORIZED"


def test_requires_auth(client):
    r = client.get("/api/v1/proposals")
    assert r.status_code == 401


def test_admin_has_wildcard(client, admin_token):
    r = client.get("/api/v1/me", headers=auth(admin_token))
    assert r.json()["is_admin"] is True
