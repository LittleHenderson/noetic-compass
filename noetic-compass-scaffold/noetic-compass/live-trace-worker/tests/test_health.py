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
    monkeypatch.setattr(model_loader, "_LOADED", None)
    r = client.get("/health/realmode")
    assert r.status_code == 200
    body = r.json()
    assert body["is_real_model"] is False
    assert body["fake_runtime_env"] is True
    assert body["model_id"] == "EleutherAI/pythia-160m"
    # No model has been loaded in the test session — cheap probe must
    # report False without trying to warm_load.
    assert body["model_loaded"] is False
    assert body["load_error"] is None
    assert body["worker_version"]


def test_health_realmode_env_unset_but_unloaded_is_not_real(client, monkeypatch):
    """LIVE_TRACE_DEMO_MODE unset BUT no real weights loaded yet -> NOT real-mode.

    Real-mode requires actual Pythia weights to be loaded right now.
    Merely having demo mode unset is not enough — a cold worker is not
    in real-mode even though it isn't forced to demo. The cheap probe
    MUST NOT trigger a load to satisfy the check; it reports the
    truthful "not loaded yet" state.
    """
    monkeypatch.delenv("LIVE_TRACE_DEMO_MODE", raising=False)
    monkeypatch.setattr(model_loader, "_LOADED", None)
    r = client.get("/health/realmode")
    assert r.status_code == 200
    body = r.json()
    assert body["fake_runtime_env"] is False
    assert body["model_loaded"] is False
    assert body["load_error"] is None
    assert body["is_real_model"] is False
    assert body["model_id"] == "EleutherAI/pythia-160m"


def test_health_realmode_reports_loaded_when_singleton_real(client, monkeypatch):
    """If warm_load has populated _LOADED with real weights, all four signals green."""
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
    assert body["load_error"] is None
    assert body["worker_version"] == "m2-real-pythia"


def test_health_realmode_load_error_is_not_real(client, monkeypatch):
    """If warm_load recorded a load_error, is_real_model=False and error surfaces.

    This is the "RunPod tried to load Pythia but the HF download failed"
    failure mode. The endpoint must surface the error string so operators
    can see WHY real-mode is unavailable, and is_real_model must be False
    so the verification script fails loudly.
    """
    monkeypatch.delenv("LIVE_TRACE_DEMO_MODE", raising=False)
    error_loaded = model_loader.LoadedModel(
        manifest=model_loader.PYTHIA_160M_MANIFEST,
        model=None,
        tokenizer=None,
        load_error="HF download timed out after 60s",
    )
    monkeypatch.setattr(model_loader, "_LOADED", error_loaded)
    r = client.get("/health/realmode")
    assert r.status_code == 200
    body = r.json()
    assert body["model_loaded"] is False
    assert body["load_error"] == "HF download timed out after 60s"
    assert body["is_real_model"] is False
    assert body["fake_runtime_env"] is False


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
