import hashlib

from app.runtime import model_loader


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body == {"status": "ok"}


def _loaded_model(
    *,
    manifest_is_real: bool,
    load_error: str | None = None,
    binding: model_loader.ModelBinding | None = None,
):
    binding = binding or model_loader._pythia_binding()
    identity = (
        {
            "execution_kind": "real_model_weights",
            "resolved_revision": binding.revision,
            "revision_verified": True,
            "weights_filename": binding.weights_filename,
            "weights_sha256": binding.weights_sha256,
            "weights_bytes": binding.weights_bytes,
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
            **model_loader.bootstrap_manifest(binding).model_dump(),
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


def test_health_realmode_default_pythia_response_is_byte_exact(client, monkeypatch):
    monkeypatch.delenv(model_loader.ACTIVE_MODEL_ENV, raising=False)
    monkeypatch.delenv("LIVE_TRACE_DEMO_MODE", raising=False)
    monkeypatch.setattr(model_loader, "_LOADED", _loaded_model(manifest_is_real=True))

    r = client.get("/health/realmode")

    assert r.status_code == 200
    assert r.content == (
        b'{"verdict":"REAL_PYTHIA_WEIGHTS_LOADED","is_real_model":true,'
        b'"fake_runtime_env":false,"model_loaded":true,"load_error":null,'
        b'"manifest_is_real_model":true,"model_id":"EleutherAI/pythia-160m",'
        b'"requested_revision":"50f5173d932e8e61f858120bcb800b97af589f46",'
        b'"resolved_revision":"50f5173d932e8e61f858120bcb800b97af589f46",'
        b'"revision_verified":true,"weights_filename":"model.safetensors",'
        b'"weights_sha256":"29d2e457a664e41c12c735f20a36dc0956a665f614a54ce5db21a32e75965270",'
        b'"weights_bytes":374998696,"weights_hash_verified":true,'
        b'"model_identity_status":"PINNED_REVISION_AND_WEIGHTS_SHA256",'
        b'"runtime_execution":{"profile":"development","device":"cpu",'
        b'"dtype":"torch.float32","torch_version":"2.13.0+cu126",'
        b'"torch_native_jit_disabled":false,"cuda_bfloat16_supported":null,'
        b'"cuda_runtime_version":null,"cuda_driver_version":null,'
        b'"cuda_device_name":null,"cuda_device_capability":null},'
        b'"worker_version":"m2-real-pythia"}'
    )


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


def test_demo_warm_load_preserves_selected_qwen_manifest(client, monkeypatch):
    monkeypatch.setenv(
        model_loader.ACTIVE_MODEL_ENV,
        model_loader.QWEN_05B_INSTRUCT_BINDING_KEY,
    )
    monkeypatch.setenv("LIVE_TRACE_DEMO_MODE", "1")
    monkeypatch.setattr(model_loader, "_LOADED", None)

    loaded = model_loader.warm_load()
    response = client.get("/health/realmode")

    assert loaded.manifest.model_id == model_loader.QWEN_05B_INSTRUCT_MODEL_ID
    assert loaded.manifest.model_arch.family == "qwen2"
    assert loaded.manifest.model_arch.n_layers == 24
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "NOT_REAL_QWEN2_5_0_5B_INSTRUCT_WEIGHTS"
    assert body["model_id"] == model_loader.QWEN_05B_INSTRUCT_MODEL_ID
    assert body["requested_revision"] == model_loader.QWEN_05B_INSTRUCT_REVISION
    assert body["worker_version"] == "stageb-real-qwen2.5-0.5b-instruct"


def test_demo_warm_load_keeps_historical_pythia_manifest_bytes(monkeypatch):
    monkeypatch.delenv(model_loader.ACTIVE_MODEL_ENV, raising=False)
    monkeypatch.setenv("LIVE_TRACE_DEMO_MODE", "1")
    monkeypatch.setattr(model_loader, "_LOADED", None)

    loaded = model_loader.warm_load()
    raw = loaded.manifest.model_dump_json().encode("utf-8")

    assert loaded.manifest is model_loader.PYTHIA_160M_MANIFEST
    assert len(raw) == 1093
    assert hashlib.sha256(raw).hexdigest() == (
        "3957cd051d1a7de53f49f791b0de5c409506625bf6ed0e94b684ba57c2aa1b37"
    )


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


def test_health_realmode_reports_selected_qwen_identity_and_runtime(
    client,
    monkeypatch,
):
    monkeypatch.setenv(
        model_loader.ACTIVE_MODEL_ENV,
        model_loader.QWEN_05B_INSTRUCT_BINDING_KEY,
    )
    monkeypatch.delenv("LIVE_TRACE_DEMO_MODE", raising=False)
    binding = model_loader.active_model_binding()
    monkeypatch.setattr(
        model_loader,
        "_LOADED",
        _loaded_model(manifest_is_real=True, binding=binding),
    )

    r = client.get("/health/realmode")

    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "REAL_QWEN2_5_0_5B_INSTRUCT_WEIGHTS_LOADED"
    assert body["is_real_model"] is True
    assert body["fake_runtime_env"] is False
    assert body["model_loaded"] is True
    assert body["load_error"] is None
    assert body["manifest_is_real_model"] is True
    assert body["model_id"] == model_loader.QWEN_05B_INSTRUCT_MODEL_ID
    assert body["requested_revision"] == model_loader.QWEN_05B_INSTRUCT_REVISION
    assert body["resolved_revision"] == model_loader.QWEN_05B_INSTRUCT_REVISION
    assert body["revision_verified"] is True
    assert (
        body["weights_filename"]
        == model_loader.QWEN_05B_INSTRUCT_WEIGHTS_FILENAME
    )
    assert body["weights_sha256"] == model_loader.QWEN_05B_INSTRUCT_WEIGHTS_SHA256
    assert body["weights_bytes"] == model_loader.QWEN_05B_INSTRUCT_WEIGHTS_BYTES
    assert body["weights_hash_verified"] is True
    assert body["model_identity_status"] == "PINNED_REVISION_AND_WEIGHTS_SHA256"
    assert body["runtime_execution"]["device"] == "cpu"
    assert body["runtime_execution"]["dtype"] == "torch.float32"
    assert body["worker_version"] == binding.worker_version


def test_health_realmode_cold_qwen_reports_selected_unloaded_identity(
    client,
    monkeypatch,
):
    monkeypatch.setenv(
        model_loader.ACTIVE_MODEL_ENV,
        model_loader.QWEN_05B_INSTRUCT_BINDING_KEY,
    )
    monkeypatch.delenv("LIVE_TRACE_DEMO_MODE", raising=False)
    monkeypatch.setattr(model_loader, "_LOADED", None)

    def _boom():
        raise AssertionError("/health/realmode must not trigger warm_load()")

    monkeypatch.setattr(model_loader, "warm_load", _boom)
    r = client.get("/health/realmode")

    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "NOT_REAL_QWEN2_5_0_5B_INSTRUCT_WEIGHTS"
    assert body["is_real_model"] is False
    assert body["model_loaded"] is False
    assert body["manifest_is_real_model"] is False
    assert body["model_id"] == model_loader.QWEN_05B_INSTRUCT_MODEL_ID
    assert body["requested_revision"] == model_loader.QWEN_05B_INSTRUCT_REVISION
    assert body["resolved_revision"] is None
    assert body["revision_verified"] is False
    assert body["weights_filename"] is None
    assert body["weights_sha256"] is None
    assert body["weights_bytes"] is None
    assert body["weights_hash_verified"] is False
    assert body["model_identity_status"] == "DEMO_OR_UNLOADED"
    assert body["runtime_execution"] is None
    assert body["worker_version"] == "stageb-real-qwen2.5-0.5b-instruct"
