def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["model_id"] == "EleutherAI/pythia-160m"
    # M2 default in CI: LIVE_TRACE_DEMO_MODE=1 keeps the worker in demo
    # mode. is_real_model + model_loaded both False; load_error None.
    assert body["is_real_model"] is False
    assert body["model_loaded"] is False
    assert body["load_error"] is None
    assert body["worker_version"] == "m2-real-pythia"
