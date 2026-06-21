"""Tests for reports export, ethics workflow, KPI run and rewards."""
from tests.conftest import auth

P = "/api/v1"


# ----- Reports -----
def test_report_run_and_export(client, officer_token):
    runs = client.post(f"{P}/reports/R01/runs", headers=auth(officer_token))
    assert runs.status_code == 201
    run = runs.json()
    assert run["report_code"] == "R01"
    assert "columns" in run["snapshot"]
    assert run["snapshot_hash"].startswith("sha256:")
    rid = run["id"]

    xlsx = client.get(f"{P}/reports/runs/{rid}/export", headers=auth(officer_token),
                      params={"format": "xlsx"})
    assert xlsx.status_code == 200
    assert "spreadsheetml" in xlsx.headers["content-type"]

    csv = client.get(f"{P}/reports/runs/{rid}/export", headers=auth(officer_token),
                     params={"format": "csv"})
    assert csv.status_code == 200
    assert "text/csv" in csv.headers["content-type"]


def test_report_list(client, officer_token):
    r = client.get(f"{P}/reports", headers=auth(officer_token))
    assert r.status_code == 200
    codes = {x["code"] for x in r.json()}
    assert "R01" in codes and "R28" in codes


# ----- Ethics -----
def test_ethics_full_flow(client, officer_token):
    a = client.post(f"{P}/ethics", headers=auth(officer_token),
                    json={"title": "Nghiên cứu trên người", "review_type": "FULL",
                          "involves_human_subjects": True})
    assert a.status_code == 201
    aid = a.json()["id"]
    assert a.json()["classification"] == "RESTRICTED"

    assert client.post(f"{P}/ethics/{aid}/submit", headers=auth(officer_token)).json()["status"] == "SUBMITTED"
    sc = client.post(f"{P}/ethics/{aid}/screen", headers=auth(officer_token), params={"review_type": "FULL"})
    assert sc.json()["status"] == "UNDER_REVIEW"
    dec = client.post(f"{P}/ethics/{aid}/decision", headers=auth(officer_token),
                      json={"outcome": "APPROVED", "valid_months": 12})
    assert dec.json()["status"] == "APPROVED"
    assert dec.json()["valid_to"] is not None


def test_ethics_rbac(client, reviewer_token):
    # REVIEWER role has no ethics permissions
    assert client.get(f"{P}/ethics", headers=auth(reviewer_token)).status_code == 403


# ----- KPI -----
def test_kpi_run_reproducible(client, officer_token):
    r1 = client.post(f"{P}/kpi-runs", headers=auth(officer_token), json={"period": "2026"})
    assert r1.status_code == 201
    run = r1.json()
    assert run["status"] == "FROZEN"
    detail = client.get(f"{P}/kpi-runs/{run['id']}", headers=auth(officer_token)).json()
    assert "contributions" in detail
    # Same data + rule => same rule hash
    r2 = client.post(f"{P}/kpi-runs", headers=auth(officer_token), json={"period": "2026"})
    assert r2.json()["rule_hash"] == run["rule_hash"]


# ----- Rewards -----
def test_reward_workflow(client, officer_token):
    r = client.post(f"{P}/reward-applications", headers=auth(officer_token),
                    json={"title": "Thưởng bài Q1", "points": "1.0", "amount": "5000000"})
    assert r.status_code == 201
    rid = r.json()["id"]
    for target in ["SUBMITTED", "UNIT_CONFIRMED", "OFFICE_REVIEWED", "APPROVED", "PAID"]:
        resp = client.post(f"{P}/reward-applications/{rid}/transition", headers=auth(officer_token),
                           json={"target_status": target})
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == target


def test_reward_invalid_transition(client, officer_token):
    rid = client.post(f"{P}/reward-applications", headers=auth(officer_token),
                      json={"title": "x"}).json()["id"]
    # DRAFT -> APPROVED is not allowed
    resp = client.post(f"{P}/reward-applications/{rid}/transition", headers=auth(officer_token),
                       json={"target_status": "APPROVED"})
    assert resp.status_code == 409
