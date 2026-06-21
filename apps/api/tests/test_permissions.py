"""Permission / RBAC enforcement tests."""
from tests.conftest import auth

P = "/api/v1"


def test_reviewer_cannot_create_proposal(client, reviewer_token):
    call_id = None
    # reviewer can't read calls either in some setups; fetch via officer not needed —
    # creation must be blocked regardless of call id.
    r = client.post(f"{P}/proposals", headers=auth(reviewer_token),
                    json={"call_id": "00000000-0000-0000-0000-000000000000", "title": "x"})
    assert r.status_code == 403
    assert r.json()["code"] == "AUTH_FORBIDDEN"
    _ = call_id


def test_reviewer_cannot_read_audit(client, reviewer_token):
    r = client.get(f"{P}/audit-logs", headers=auth(reviewer_token))
    assert r.status_code == 403


def test_officer_can_read_audit(client, officer_token):
    r = client.get(f"{P}/audit-logs", headers=auth(officer_token))
    assert r.status_code == 200


def test_unknown_entity_returns_404(client, officer_token):
    r = client.get(f"{P}/proposals/00000000-0000-0000-0000-000000000000",
                   headers=auth(officer_token))
    assert r.status_code == 404
