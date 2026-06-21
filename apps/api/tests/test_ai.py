"""AI feature tests: suggestion-only, citations / insufficient-evidence."""
from tests.conftest import auth

P = "/api/v1"


def _a_proposal_id(client, token):
    return client.get(f"{P}/proposals", headers=auth(token),
                      params={"limit": 1}).json()["items"][0]["id"]


def test_ai_output_is_draft(client, officer_token):
    pid = _a_proposal_id(client, officer_token)
    r = client.post(f"{P}/ai/jobs", headers=auth(officer_token),
                    json={"feature_code": "PROPOSAL_COMPLETENESS", "entity_type": "proposal",
                          "entity_id": pid})
    assert r.status_code == 201
    body = r.json()
    # Human-in-the-loop: never auto-accepted
    assert body["human_status"] == "DRAFT"
    assert "findings" in body["content_json"]


def test_ai_consistency_runs(client, officer_token):
    pid = _a_proposal_id(client, officer_token)
    r = client.post(f"{P}/ai/jobs", headers=auth(officer_token),
                    json={"feature_code": "PROPOSAL_CONSISTENCY_REVIEW", "entity_type": "proposal",
                          "entity_id": pid})
    assert r.status_code == 201
    assert r.json()["output_type"] == "FINDINGS"


def test_ai_feedback_accept(client, officer_token):
    pid = _a_proposal_id(client, officer_token)
    out = client.post(f"{P}/ai/jobs", headers=auth(officer_token),
                      json={"feature_code": "PROPOSAL_SUMMARY", "entity_type": "proposal",
                            "entity_id": pid}).json()
    r = client.post(f"{P}/ai/outputs/{out['id']}/feedback", headers=auth(officer_token),
                    json={"rating": "UP", "accept": True})
    assert r.status_code == 200
    assert r.json()["human_status"] == "ACCEPTED"


def test_rag_chat_without_docs_is_honest(client, officer_token):
    # Scope the question to a fresh proposal that has no linked documents:
    # retrieval must return nothing and the assistant must decline, not fabricate.
    call_id = client.get(f"{P}/funding-calls", headers=auth(officer_token)).json()["items"][0]["id"]
    pid = client.post(f"{P}/proposals", headers=auth(officer_token),
                      json={"call_id": call_id, "title": "No-docs proposal"}).json()["id"]
    r = client.post(f"{P}/ai/chat", headers=auth(officer_token),
                    json={"message": "Tài liệu này nói gì?", "entity_type": "proposal",
                          "entity_id": pid})
    assert r.status_code == 200
    assert r.json()["insufficient_evidence"] is True
