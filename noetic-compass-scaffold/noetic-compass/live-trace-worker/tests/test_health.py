from app.runtime import model_loader


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


def test_health_realmode_with_demo_env_set(client, monkeypatch):
    """LIVE_TRACE_DEMO_MODE=1 -> is_real_model=False, fake_runtime_env=True."""
    monkeypatch.setenv("LIVE_TRACE_DEMO_MODE", "1")
    r = client.get("/health/realmode")
    assert r.status_code == 200
    body = r.json()
    assert body["is_real_model"] is False
    assert body["fake_runtime_env"] is True
    assert body["model_id"] == "EleutherAI/pythia-160m"
    # No model has been loaded in the test session — cheap probe must
    # report False without trying to warm_load.
    assert body["model_loaded"] is False
    assert body["worker_version"]


def test_health_realmode_with_demo_env_unset(client, monkeypatch):
    """LIVE_TRACE_DEMO_MODE unset -> is_real_model=True, fake_runtime_env=False.

    This is the "deployed RunPod in real-mode" shape — what
    verify_atlas_live.py expects to see when the worker is correctly
    serving real Pythia weights.
    """
    monkeypatch.delenv("LIVE_TRACE_DEMO_MODE", raising=False)
    r = client.get("/health/realmode")
    assert r.status_code == 200
    body = r.json()
    assert body["is_real_model"] is True
    assert body["fake_runtime_env"] is False
    assert body["model_id"] == "EleutherAI/pythia-160m"
    # Cheap probe: even with demo env unset, we MUST NOT trigger a load.
    # model_loaded stays False until warm_load actually populates it.
    assert body["model_loaded"] is False


def test_health_realmode_reports_loaded_when_singleton_real(client, monkeypatch):
    """If warm_load has populated _LOADED with real weights, model_loaded=True."""
    monkeypatch.delenv("LIVE_TRACE_DEMO_MODE", raising=False)
    real_manifest = model_loader.PYTHIA_160M_MANIFEST.model_copy(
        update={"is_real_model": True},
    )
    fake_loaded = model_loader.LoadedModel(
        manifest=real_manifest,
        model=object(),  # truthy -> is_real == True
        tokenizer=object(),
    )
    monkeypatch.setattr(model_loader, "_LOADED", fake_loaded)
    r = client.get("/health/realmode")
    assert r.status_code == 200
    body = r.json()
    assert body["is_real_model"] is True
    assert body["fake_runtime_env"] is False
    assert body["model_loaded"] is True
    assert body["worker_version"] == "m2-real-pythia"


def test_health_realmode_does_not_trigger_load(client, monkeypatch):
    """The cheap-probe contract: calling /health/realmode must NOT invoke warm_load.

    The whole point of this endpoint is the operator can hit it from CI / a
    verification script without paying a model-load round-trip. If a future
    refactor accidentally wires get_loaded_model() into the realmode handler,
    this test fails.
    """
    monkeypatch.delenv("LIVE_TRACE_DEMO_MODE", raising=False)
    called = {"count": 0}

    def _boom(*args, **kwargs):
        called["count"] += 1
        raise AssertionError("/health/realmode must not trigger warm_load()")

    monkeypatch.setattr(model_loader, "warm_load", _boom)
    r = client.get("/health/realmode")
    assert r.status_code == 200
    assert called["count"] == 0
