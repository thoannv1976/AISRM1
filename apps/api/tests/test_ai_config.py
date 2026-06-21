"""Admin AI configuration & key management tests."""
from tests.conftest import auth

P = "/api/v1"


def test_get_config_default(client, officer_token):
    r = client.get(f"{P}/ai/config", headers=auth(officer_token))
    assert r.status_code == 200
    cfg = r.json()
    assert cfg["mode"] in {"AUTO", "CLAUDE", "MOCK"}
    assert cfg["api_key_source"] in {"NONE", "ENV", "DB"}
    assert "available_models" in cfg
    # No plaintext key is ever returned.
    assert "api_key" not in cfg


def test_save_key_is_encrypted_and_masked(client, officer_token):
    r = client.put(
        f"{P}/ai/config",
        headers=auth(officer_token),
        json={"mode": "CLAUDE", "llm_model": "claude-opus-4-8", "api_key": "sk-ant-test-WXYZ"},
    )
    assert r.status_code == 200
    cfg = r.json()
    assert cfg["mode"] == "CLAUDE"
    assert cfg["llm_model"] == "claude-opus-4-8"
    assert cfg["api_key_masked"] == "••••WXYZ"
    assert cfg["api_key_source"] == "DB"
    assert cfg["effective_provider"] == "anthropic"


def test_config_change_is_audited(client, officer_token):
    client.put(f"{P}/ai/config", headers=auth(officer_token), json={"monthly_budget": 50})
    logs = client.get(f"{P}/audit-logs", headers=auth(officer_token),
                      params={"action": "ai.config.save"}).json()
    assert logs["total"] >= 1


def test_clear_key(client, officer_token):
    client.put(f"{P}/ai/config", headers=auth(officer_token), json={"api_key": "sk-ant-keep-1234"})
    r = client.put(f"{P}/ai/config", headers=auth(officer_token),
                   json={"clear_key": True, "mode": "AUTO"})
    assert r.json()["api_key_masked"] is None


def test_test_connection(client, officer_token):
    r = client.post(f"{P}/ai/config/test", headers=auth(officer_token))
    assert r.status_code == 200
    assert "ok" in r.json() and "message" in r.json()


def test_usage_summary(client, officer_token):
    # Generate some usage first.
    pid = client.get(f"{P}/proposals", headers=auth(officer_token),
                     params={"limit": 1}).json()["items"][0]["id"]
    client.post(f"{P}/ai/jobs", headers=auth(officer_token),
                json={"feature_code": "PROPOSAL_SUMMARY", "entity_type": "proposal", "entity_id": pid})
    r = client.get(f"{P}/ai/usage", headers=auth(officer_token))
    assert r.status_code == 200
    u = r.json()
    assert u["calls"] >= 1
    assert "total_tokens" in u and "estimated_cost" in u


def test_feature_toggle(client, officer_token):
    feat = client.get(f"{P}/ai/features", headers=auth(officer_token)).json()[0]
    off = client.patch(f"{P}/ai/features/{feat['id']}/toggle", headers=auth(officer_token),
                       json={"enabled": False})
    assert off.json()["enabled"] is False
    on = client.patch(f"{P}/ai/features/{feat['id']}/toggle", headers=auth(officer_token),
                      json={"enabled": True})
    assert on.json()["enabled"] is True


def test_non_admin_cannot_access_config(client, reviewer_token):
    assert client.get(f"{P}/ai/config", headers=auth(reviewer_token)).status_code == 403
    assert client.put(f"{P}/ai/config", headers=auth(reviewer_token),
                      json={"mode": "MOCK"}).status_code == 403
