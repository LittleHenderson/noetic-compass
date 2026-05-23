def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["model_id"] == "EleutherAI/pythia-160m"
    # M1 is the scaffold — the worker MUST advertise is_real_model=False so
    # callers can't confuse it with the real-Pythia milestone.
    assert body["is_real_model"] is False
    assert body["worker_version"] == "m1-scaffold"
