from app.runtime import model_loader


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body == {"status": "ok"}


def _loaded_model(*, manifest_is_real: bool, load_error: str | None = None):
    identity = (
        {
            "execution_kind": "real_model_weights",
            "resolved_revision": model_loader.PYTHIA_160M_REVISION,
            "revision_verified": True,
            "weights_filename": model_loader.PYTHIA_160M_WEIGHTS_FILENAME,
            "weights_sha256": model_loader.PYTHIA_160M_WEIGHTS_SHA256,
            "weights_bytes": model_loader.PYTHIA_160M_WEIGHTS_BYTES,
            "weights_hash_verified": True,
            "model_identity_status": "PINNED_REVISION_AND_WEIGHTS_SHA256",
            "runtime_execution": {
                "profile": "development",
                "device": "cpu",
                "dtype": "torch.float32",
                "torch_version": "2.13.0+cu126",
            },
        }
        if manifest_is_real
        else {}
    )
    manifest = model_loader.ModelManifest.model_validate(
        {
            **model_loader.PYTHIA_160M_MANIFEST.model_dump(),
            "is_real_model": manifest_is_real,
            **identity,
        },
    )
    return model_loader.LoadedModel(
        manifest=manifest,
        model=object(),
        tokenizer=object(),
        load_error=load_error,
    )


def test_health_realmode_good_state(client, monkeypatch):
    monkeypatch.delenv("LIVE_TRACE_DEMO_MODE", raising=False)
    monkeypatch.setattr(model_loader, "_LOADED", _loaded_model(manifest_is_real=True))

    r = client.get("/health/realmode")

    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "REAL_PYTHIA_WEIGHTS_LOADED"
    assert body["is_real_model"] is True
    assert body["fake_runtime_env"] is False
    assert body["model_loaded"] is True
    assert body["load_error"] is None
    assert body["manifest_is_real_model"] is True
    assert body["model_id"] == "EleutherAI/pythia-160m"
    assert body["requested_revision"] == model_loader.PYTHIA_160M_REVISION
    assert body["resolved_revision"] == model_loader.PYTHIA_160M_REVISION
    assert body["revision_verified"] is True
    assert body["weights_filename"] == model_loader.PYTHIA_160M_WEIGHTS_FILENAME
    assert body["weights_sha256"] == model_loader.PYTHIA_160M_WEIGHTS_SHA256
    assert body["weights_bytes"] == model_loader.PYTHIA_160M_WEIGHTS_BYTES
    assert body["weights_hash_verified"] is True
    assert (
        body["model_identity_status"]
        == "PINNED_REVISION_AND_WEIGHTS_SHA256"
    )
    assert body["runtime_execution"]["device"] == "cpu"


def test_health_realmode_fake_mode_fails_even_with_loaded_model(client, monkeypatch):
    monkeypatch.setenv("LIVE_TRACE_DEMO_MODE", "1")
    monkeypatch.setattr(model_loader, "_LOADED", _loaded_model(manifest_is_real=True))

    r = client.get("/health/realmode")

    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "NOT_REAL_PYTHIA_WEIGHTS"
    assert body["is_real_model"] is False
    assert body["fake_runtime_env"] is True
    assert body["model_loaded"] is True
    assert body["load_error"] is None
    assert body["manifest_is_real_model"] is True


def test_health_realmode_unloaded_model_fails_without_triggering_load(client, monkeypatch):
    monkeypatch.delenv("LIVE_TRACE_DEMO_MODE", raising=False)
    monkeypatch.setattr(model_loader, "_LOADED", None)

    def _boom():
        raise AssertionError("/health/realmode must not trigger warm_load()")

    monkeypatch.setattr(model_loader, "warm_load", _boom)
    r = client.get("/health/realmode")

    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "NOT_REAL_PYTHIA_WEIGHTS"
    assert body["is_real_model"] is False
    assert body["fake_runtime_env"] is False
    assert body["model_loaded"] is False
    assert body["load_error"] is None
    assert body["manifest_is_real_model"] is False


def test_health_realmode_load_error_fails(client, monkeypatch):
    monkeypatch.delenv("LIVE_TRACE_DEMO_MODE", raising=False)
    monkeypatch.setattr(
        model_loader,
        "_LOADED",
        _loaded_model(
            manifest_is_real=True,
            load_error="HF download timed out",
        ),
    )

    r = client.get("/health/realmode")

    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "NOT_REAL_PYTHIA_WEIGHTS"
    assert body["is_real_model"] is False
    assert body["fake_runtime_env"] is False
    assert body["model_loaded"] is True
    assert body["load_error"] == "MODEL_LOAD_FAILED"
    assert body["manifest_is_real_model"] is True


def test_health_realmode_manifest_false_fails(client, monkeypatch):
    monkeypatch.delenv("LIVE_TRACE_DEMO_MODE", raising=False)
    monkeypatch.setattr(model_loader, "_LOADED", _loaded_model(manifest_is_real=False))

    r = client.get("/health/realmode")

    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "NOT_REAL_PYTHIA_WEIGHTS"
    assert body["is_real_model"] is False
    assert body["fake_runtime_env"] is False
    assert body["model_loaded"] is True
    assert body["load_error"] is None
    assert body["manifest_is_real_model"] is False
