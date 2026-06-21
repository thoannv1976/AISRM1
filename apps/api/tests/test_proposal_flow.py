"""End-to-end proposal lifecycle tests."""
from tests.conftest import auth

P = "/api/v1"


def _new_proposal(client, token):
    me = client.get(f"{P}/me", headers=auth(token)).json()
    call_id = client.get(f"{P}/funding-calls", headers=auth(token)).json()["items"][0]["id"]
    r = client.post(f"{P}/proposals", headers=auth(token),
                    json={"call_id": call_id, "title": "Test proposal", "abstract": "x"})
    assert r.status_code == 201
    pid = r.json()["id"]
    client.patch(f"{P}/proposals/{pid}", headers=auth(token),
                 json={"content_json": {"objectives": "o", "methods": "m"},
                       "lead_unit_id": me["user"]["primary_unit_id"]})
    return pid


def test_submit_requires_completeness(client, officer_token):
    """A bare proposal cannot be submitted (missing team/budget/deliverables)."""
    call_id = client.get(f"{P}/funding-calls", headers=auth(officer_token)).json()["items"][0]["id"]
    pid = client.post(f"{P}/proposals", headers=auth(officer_token),
                      json={"call_id": call_id, "title": "Bare"}).json()["id"]
    r = client.post(f"{P}/proposals/{pid}/submit", headers=auth(officer_token), json={})
    assert r.status_code == 422
    assert r.json()["code"] == "SUBMISSION_INCOMPLETE"


def test_full_lifecycle(client, officer_token):
    pid = _new_proposal(client, officer_token)
    client.post(f"{P}/proposals/{pid}/team", headers=auth(officer_token),
                json={"external_person_name": "M", "role": "MEMBER"})
    client.post(f"{P}/proposals/{pid}/deliverables", headers=auth(officer_token),
                json={"code": "D1", "title": "Report"})
    client.post(f"{P}/proposals/{pid}/budget-lines", headers=auth(officer_token),
                json={"category": "Labor", "amount": "1000000", "year": 2026})

    v = client.post(f"{P}/proposals/{pid}/validate", headers=auth(officer_token)).json()
    assert v["ok"] is True

    s = client.post(f"{P}/proposals/{pid}/submit", headers=auth(officer_token),
                    json={"submission_note": "go"})
    assert s.status_code == 200
    assert s.json()["status"] == "SUBMITTED"

    # immutable version created
    d = client.post(f"{P}/proposals/{pid}/decision", headers=auth(officer_token),
                    json={"outcome": "APPROVED", "approved_budget": "1000000"})
    assert d.json()["proposal_status"] == "APPROVED"

    a = client.post(f"{P}/proposals/{pid}/activate-project", headers=auth(officer_token))
    assert a.status_code == 200
    assert a.json()["project_code"].startswith("DT-")


def test_cannot_edit_after_submit(client, officer_token):
    pid = _new_proposal(client, officer_token)
    for ep, body in [("team", {"external_person_name": "M", "role": "MEMBER"}),
                     ("deliverables", {"code": "D1", "title": "R"}),
                     ("budget-lines", {"category": "L", "amount": "1000000"})]:
        client.post(f"{P}/proposals/{pid}/{ep}", headers=auth(officer_token), json=body)
    client.post(f"{P}/proposals/{pid}/submit", headers=auth(officer_token), json={})
    r = client.patch(f"{P}/proposals/{pid}", headers=auth(officer_token), json={"title": "new"})
    assert r.status_code == 409
    assert r.json()["code"] == "INVALID_STATE_TRANSITION"
