import pytest
from helpers_api import COLS, IDS, make_client


def test_health_ok_and_degraded(client, tmp_path):
    r = client.get("/health").json()
    assert r["status"] == "ok" and r["datasets"] == ["LI"] and r["model_loaded"] and r["demo_mode"]
    from fastapi.testclient import TestClient

    from backend.app.main import create_app
    from backend.app.settings import Settings

    empty = TestClient(create_app(Settings(bundle_dir=tmp_path / "nothing", db_path=str(tmp_path / "e.db"))))
    assert empty.get("/health").json()["status"] == "degraded"
    assert empty.get("/api/dashboard").status_code == 404


def test_datasets_and_dashboard(client):
    assert client.get("/api/datasets").json()["default"] == "LI"
    d = client.get("/api/dashboard?dataset=LI").json()
    assert d["decisions"]["sample_size"] == 6 and d["decisions"]["open_in_sample"] == 6
    assert len(d["latest_alerts"]) == 6 and "SYNTHETIC" in d["disclosure"]
    assert client.get("/api/dashboard?dataset=HI").status_code == 404  # valid value, bundle absent
    assert client.get("/api/dashboard?dataset=XX").status_code == 422


def test_alerts_list_filter_sort_paginate(client):
    r = client.get("/api/alerts?page_size=4&sort=score&order=desc").json()
    assert r["total"] == 6 and len(r["items"]) == 4
    assert [a["score"] for a in r["items"]] == sorted([a["score"] for a in r["items"]], reverse=True)
    assert client.get("/api/alerts?page=2&page_size=4").json()["items"].__len__() == 2
    assert client.get("/api/alerts?priority=P1").json()["total"] == 2
    assert client.get("/api/alerts?q=1403").json()["total"] == 1
    assert client.get("/api/alerts?q=zzz").json()["total"] == 0
    assert client.get("/api/alerts?sort=amount&order=asc").json()["items"][0]["id"] == IDS[0]
    for bad in ("sort=hack", "order=up", "page_size=1000", "page=0", "priority=P9", "status=nope", "q=" + "x" * 65):
        assert client.get(f"/api/alerts?{bad}").status_code == 422, bad


def test_alert_case_network_explanation_and_errors(client):
    a = client.get(f"/api/alerts/{IDS[0]}").json()
    assert a["id"] == IDS[0] and a["status"] == "open"
    c = client.get(f"/api/cases/{IDS[0]}").json()
    assert c["decision_history"] == [] and c["simulated_feedback"] is True
    n = client.get(f"/api/network/{IDS[0]}").json()
    assert n["focal"] == a["account"] and len(n["nodes"]) == 2 and len(n["edges"]) == 1
    e = client.get(f"/api/explanations/{IDS[0]}").json()
    assert "TreeSHAP" in e["method"] and e["top_features"]
    assert client.get("/api/alerts/RG-LI-9999-20250101").status_code == 404
    assert client.get("/api/cases/RG-LI-9999-20250101").status_code == 404
    assert client.get("/api/alerts/not-an-id").status_code == 422
    assert client.get("/api/network/RG-HI-1400-20251010").status_code == 404  # dataset absent


def test_decision_workflow_updates_state(client):
    body = {"decision": "suspicious", "note": "pattern looks circular", "analyst": "a.tester"}
    r = client.post(f"/api/cases/{IDS[1]}/decision", json=body)
    assert r.status_code == 201 and r.json()["simulated"] is True and r.json()["status"] == "suspicious"
    client.post(f"/api/cases/{IDS[1]}/decision", json={"decision": "requires_review"})
    hist = client.get(f"/api/cases/{IDS[1]}").json()
    assert [h["decision"] for h in hist["decision_history"]] == ["suspicious", "requires_review"]
    assert hist["status"] == "requires_review"
    assert client.get("/api/alerts?status=requires_review").json()["total"] == 1
    assert client.get("/api/alerts?status=open").json()["total"] == 5
    assert client.get("/api/cases").json()["total"] == 1 and client.get("/api/cases?all=true").json()["total"] == 6
    d = client.get("/api/dashboard").json()["decisions"]
    assert d["decided_in_sample"] == 1 and d["by_decision"] == {"requires_review": 1}


@pytest.mark.parametrize(
    "body",
    [
        {"decision": "guilty"},
        {"decision": "suspicious", "note": "x" * 501},
        {"decision": "suspicious", "extra": 1},
        {"decision": "suspicious", "analyst": "a'; DROP TABLE decisions;--"},
        {},
        {"decision": "suspicious", "analyst": ""},
    ],
)
def test_decision_validation(client, body):
    assert client.post(f"/api/cases/{IDS[0]}/decision", json=body).status_code == 422


def test_decision_unknown_case_and_api_key(bundle_dir, tmp_path):
    c = make_client(bundle_dir, tmp_path, api_key="s3cret")
    ok = {"decision": "false_positive"}
    assert c.post(f"/api/cases/{IDS[0]}/decision", json=ok).status_code == 401
    assert c.post(f"/api/cases/{IDS[0]}/decision", json=ok, headers={"X-API-Key": "wrong"}).status_code == 401
    assert c.post(f"/api/cases/{IDS[0]}/decision", json=ok, headers={"X-API-Key": "s3cret"}).status_code == 201
    assert (
        c.post("/api/cases/RG-LI-9999-20250101/decision", json=ok, headers={"X-API-Key": "s3cret"}).status_code == 404
    )
    assert (
        c.get("/api/audit").status_code == 401 and c.get("/api/audit", headers={"X-API-Key": "s3cret"}).json()["events"]
    )


def test_sql_injection_attempts_are_inert(client):
    r = client.get("/api/alerts", params={"q": "'; DROP TABLE decisions;--"})
    assert r.status_code == 200 and r.json()["total"] == 0
    assert client.post(f"/api/cases/{IDS[0]}/decision", json={"decision": "suspicious"}).status_code == 201
    assert client.get("/api/alerts/RG-LI-1400-20251010'%20OR%201=1--").status_code == 422


def test_predict(client):
    feats = {c: 1.0 for c in COLS}
    r = client.post("/api/predict", json={"features": feats})
    assert r.status_code == 200
    j = r.json()
    assert 0 <= j["score"] <= 1 and 0 <= j["p_cal"] <= 1 and len(j["contributions"]) <= 8
    assert "not a determination" in j["note"]
    lo = client.post("/api/predict", json={"features": {**feats, "t_n_out_1d": 0.0}}).json()["score"]
    assert lo != j["score"], "prediction must respond to feature changes"
    assert client.post("/api/predict", json={"features": {"t_n_out_1d": 1.0}}).status_code == 422
    assert client.post("/api/predict", json={"features": {**feats, "is_fraud": 1.0}}).status_code == 422
    assert client.post("/api/predict", json={"features": {**feats, "t_n_out_1d": "nan"}}).status_code == 422
    assert client.post("/api/predict", json={"features": {**feats}, "x": 1}).status_code == 422
    assert client.post("/api/predict", json={"features": {"a": "text"}}).status_code == 422


def test_simulate(client):
    base = {"dataset": "LI", "policy": "static", "alpha": 0.1, "capacity_multiplier": 1.0}
    a = client.post("/api/simulate", json=base).json()
    b = client.post("/api/simulate", json=base).json()
    assert a == b and 0 <= a["realised_miss_rate"] <= 1 and a["miss_ci95"] is not None
    none = client.post("/api/simulate", json={**base, "policy": "none"}).json()
    assert none["auto_closed_cases"] == 0
    for bad in (
        {"alpha": 0.9},
        {"alpha": 0},
        {"capacity_multiplier": 100},
        {"policy": "magic"},
        {"dataset": "ZZ"},
        {"extra": 1},
    ):
        assert client.post("/api/simulate", json={**base, **bad}).status_code == 422, bad


def test_model_monitoring_quality_endpoints(client):
    for path in ("/api/model/metrics", "/api/model/calibration", "/api/monitoring", "/api/data-quality"):
        assert client.get(path).status_code == 200, path
    assert "provenance" in client.get("/api/data-quality").json()


def test_cors_headers(client):
    ok = client.options(
        "/api/alerts", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"}
    )
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    bad = client.options(
        "/api/alerts", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"}
    )
    assert "access-control-allow-origin" not in bad.headers
    assert "access-control-allow-credentials" not in ok.headers


def test_security_headers_and_rate_limit(bundle_dir, tmp_path):
    c = make_client(bundle_dir, tmp_path, rate=5)
    r = c.get("/health")
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
    codes = [c.get("/api/datasets").status_code for _ in range(7)]
    assert codes[:5] == [200] * 5 and codes[5:] == [429, 429]
    assert c.get("/health").status_code == 200  # health is exempt


def test_unhandled_errors_do_not_leak(bundle_dir, tmp_path):
    c = make_client(bundle_dir, tmp_path)

    @c.app.get("/boom")
    def boom():
        raise RuntimeError("secret internal detail /etc/passwd")

    r = c.get("/boom")
    assert r.status_code == 500 and "secret" not in r.text and "RuntimeError" not in r.text and r.json()["request_id"]
