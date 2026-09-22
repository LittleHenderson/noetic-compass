"""R2, checkpoint tamper, plan, and supervisor tests; all neural paths unrun."""
import base64
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import learner_q4_memory as memory
from learner_q4_representation import Bottleneck, Q4InputError
import q4_checkpoint as checkpoint
import q4_smoke_job as job


def state(n):
    return {"node": "StateLiteral", "operator": "^%d" % n, "domain": "C", "drive": None}


def test_r2_explicit_roles_order_vectors_and_isolated_intervention():
    tree = {"node": "BinaryExpr", "op": "PLUS", "left": state(2), "right": state(3)}
    vectors = tuple(Bottleneck((float(i),)) for i in range(3))
    encoded = memory.from_structure(tree, vectors, origin="INPUT_STRUCTURE", model_identity="test-untrained")
    assert encoded.nodes[0].children == (1, 2)
    assert [(node.parent, node.role) for node in encoded.nodes] == [(None, "root"), (0, "left"), (0, "right")]
    tree["left"]["operator"] = "^9"
    assert dict(encoded.nodes[1].attributes)["operator"] == "^2"
    changed = memory.replace_vector(encoded, 1, Bottleneck((8.0,)))
    assert changed.nodes[0] == encoded.nodes[0] and changed.nodes[2] == encoded.nodes[2]
    assert changed.nodes[1].attributes == encoded.nodes[1].attributes
    assert changed.nodes[1].vector != encoded.nodes[1].vector
    assert encoded.representation_kind == "R2_STRUCTURED_MEMORY_NOT_STRICT_COMPRESSION"


@pytest.mark.parametrize("change", [{"origin": "TARGET_AST"}, {"vectors": ()},
                                     {"vectors": (Bottleneck((0.0,)), Bottleneck((0.0,)))},
                                     {"context": (("x", "a"), ("x", "b"))}])
def test_r2_bad_binding_shapes_refused(change):
    args = dict(ast=state(2), vectors=(Bottleneck((0.0,)),), origin="INPUT_STRUCTURE", model_identity="test")
    args.update(change)
    with pytest.raises(Q4InputError):
        memory.from_structure(**args)


@pytest.fixture
def package(tmp_path):
    root = tmp_path / "checkpoint"
    root.mkdir()
    body = b"DETERMINISTIC_TEST_BYTES_NOT_A_MODEL"
    identity = {"source_pins": {"example": "a" * 64}, "manifest_sha256": "b" * 64}
    manifest = {"schema": checkpoint.SCHEMA, "purpose": "INFERENCE_ONLY_NO_TRAINING_RESUME", "width": 64,
                "identity": identity, "weights_file": "model_state.pt", "weights_sha256": checkpoint.digest(body),
                "weights_bytes": len(body)}
    (root / "model_state.pt").write_bytes(body)
    (root / "manifest.json").write_bytes(checkpoint.canonical(manifest))
    expected = dict(expected_identity=copy.deepcopy(identity), expected_width=64,
                    expected_weights_sha256=checkpoint.digest(body))
    return root, manifest, expected


def test_checkpoint_verification_is_not_a_neural_load(package):
    root, manifest, expected = package
    assert checkpoint.verify_checkpoint(root, **expected) == manifest


def test_restore_consumes_verified_bytes_even_if_disk_file_changes(package, monkeypatch):
    # Fully fake model/torch objects. This is a custody test, not neural reload.
    from types import SimpleNamespace
    import learner_q4_neural
    root, manifest, expected = package
    original_bytes = (root / "model_state.pt").read_bytes()
    identity = {"source_pins": checkpoint.runtime_source_pins()}
    manifest["identity"] = identity
    (root / "manifest.json").write_bytes(checkpoint.canonical(manifest))
    events = []

    class FakeModel:
        def load_state_dict(self, state, strict):
            events.append((state, strict))
        def eval(self):
            events.append("eval-mode-only-fake")

    def fake_build(*_args, **_kwargs):
        (root / "model_state.pt").write_bytes(b"REPLACED_AFTER_VERIFICATION")
        return FakeModel()

    def fake_load(buffer, *, map_location, weights_only):
        assert buffer.read() == original_bytes
        assert map_location == "cuda:0" and weights_only is True
        return {"test_fixture": "NOT_TENSORS"}

    monkeypatch.setattr(learner_q4_neural, "build_model", fake_build)
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(load=fake_load))
    checkpoint.load_checkpoint(root, expected_identity=identity,
                               expected_weights_sha256=expected["expected_weights_sha256"], width=64, device="cuda:0")
    assert events == [({"test_fixture": "NOT_TENSORS"}, True), "eval-mode-only-fake"]


def test_checkpoint_read_stays_bounded_if_file_grows_after_stat(package, monkeypatch):
    import io
    root, manifest, expected = package
    original_open = Path.open
    requests = []

    class GrewAfterStat(io.BytesIO):
        def read(self, size=-1):
            requests.append(size)
            assert size == manifest["weights_bytes"] + 1
            return b"X" * size

    def changed_open(path, mode="r", *args, **kwargs):
        if path == root / "model_state.pt" and mode == "rb":
            return GrewAfterStat()
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", changed_open)
    with pytest.raises(checkpoint.CheckpointError, match="CHECKPOINT_WEIGHTS_MISMATCH"):
        checkpoint.verify_checkpoint(root, **expected)
    assert requests == [manifest["weights_bytes"] + 1]


@pytest.mark.parametrize("change", ["weights", "weights_and_manifest", "source", "width", "unsafe_path", "extra_key"])
def test_checkpoint_tamper_refused_even_if_local_manifest_resealed(package, change):
    root, manifest, expected = package
    if change in ("weights", "weights_and_manifest"):
        changed = b"MALICIOUS_OTHER_BYTES"
        (root / "model_state.pt").write_bytes(changed)
        if change == "weights_and_manifest":
            manifest["weights_sha256"] = checkpoint.digest(changed)
            manifest["weights_bytes"] = len(changed)
    elif change == "source":
        manifest["identity"]["source_pins"]["example"] = "c" * 64
    elif change == "width":
        manifest["width"] = 128
    elif change == "unsafe_path":
        manifest["weights_file"] = "../other.pt"
    else:
        manifest["target"] = "leaked"
    (root / "manifest.json").write_bytes(checkpoint.canonical(manifest))
    with pytest.raises(checkpoint.CheckpointError):
        checkpoint.verify_checkpoint(root, **expected)


@pytest.fixture
def plan(tmp_path):
    return job.prepare_plan(data_dir=HERE / "data" / "q3_v0_4",
                            data_version="helm-cas-expression-lab.q3-behaviour-records/0.4",
                            output=tmp_path / "one-job", max_updates=2, train_examples=8, dev_examples=2)


def test_dry_run_reads_metadata_only_and_any_explicit_pinned_version(plan, monkeypatch):
    import q3_load
    monkeypatch.setattr(q3_load, "load_split", lambda *_: pytest.fail("dry-run read targets"))
    monkeypatch.setattr(q3_load, "load_visible", lambda *_: pytest.fail("dry-run read observations"))
    assert job.validate_plan(plan) == plan
    assert plan["status"] == "PREPARED_NOT_AUTHORIZATION"
    assert plan["splits"] == ["train", "dev"] and not Path(plan["output"]).exists()


@pytest.mark.parametrize("key,value", [("seed", True), ("max_updates", 129), ("max_wall_seconds", 1801),
                                      ("width", 16), ("device", "cpu"), ("train_examples", 2049),
                                      ("dev_examples", 257), ("data_version", "latest")])
def test_dry_run_limits_and_exact_version_fail_closed(plan, key, value):
    args = {key: plan[key] for key in ("data_dir", "data_version", "output", "seed", "width", "max_updates",
                                      "max_wall_seconds", "train_examples", "dev_examples", "device")}
    args[key] = value
    with pytest.raises(job.JobError):
        job.prepare_plan(**args)


@pytest.mark.parametrize("key,value", [("status", "APPROVED"), ("source_pins", {}), ("splits", ["train", "eval"]),
                                      ("learning_rate", 0.9), ("resume", True), ("answer", 3)])
def test_modified_plan_refused(plan, key, value):
    forged = dict(plan, **{key: value})
    with pytest.raises(job.JobError, match="PLAN_DRIFT"):
        job.validate_plan(forged)


@pytest.fixture
def test_only_signature(plan, tmp_path):
    # Synthetic test key, not an owner key or an authorization for real work.
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    private = Ed25519PrivateKey.generate()
    raw = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    key_path = tmp_path / "TEST_ONLY_public.key"
    key_path.write_bytes(raw)
    payload = {"schema": job.AUTH_SCHEMA, "plan_sha256": checkpoint.digest(checkpoint.canonical(plan)),
               "expires_utc": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()}
    signature = base64.b64encode(private.sign(checkpoint.canonical(payload))).decode("ascii")
    path = tmp_path / "TEST_ONLY_signature.json"
    path.write_bytes(checkpoint.canonical(dict(payload, signature_base64=signature)))
    return path, key_path, checkpoint.digest(raw)


def test_signed_scope_cryptographic_check_only(plan, test_only_signature):
    job.verify_authorization(plan, *test_only_signature)


@pytest.mark.parametrize("change", ["scope", "expiry", "signature", "fingerprint", "approval_word"])
def test_forged_or_expired_signature_refused(plan, test_only_signature, change):
    path, key_path, fingerprint = test_only_signature
    auth = json.loads(path.read_text())
    if change == "scope":
        auth["plan_sha256"] = "0" * 64
    elif change == "expiry":
        auth["expires_utc"] = "2000-01-01T00:00:00+00:00"
    elif change == "signature":
        auth["signature_base64"] = base64.b64encode(b"0" * 64).decode()
    elif change == "fingerprint":
        fingerprint = "0" * 64
    else:
        auth = {"status": "APPROVED", "plan_sha256": auth["plan_sha256"]}
    path.write_bytes(checkpoint.canonical(auth))
    with pytest.raises(job.JobError):
        job.verify_authorization(plan, path, key_path, fingerprint)


def test_external_anchor_location_required(plan, test_only_signature, tmp_path):
    path, key_path, fingerprint = test_only_signature
    out = Path(plan["output"])
    out.mkdir()
    inside = out / "public.key"
    inside.write_bytes(key_path.read_bytes())
    with pytest.raises(job.JobError, match="UNTRUSTED_KEY_LOCATION"):
        job.verify_authorization(plan, path, inside, fingerprint)


def test_no_launch_on_bad_authorization(plan, tmp_path, monkeypatch):
    path = tmp_path / "plan.json"
    path.write_bytes(checkpoint.canonical(plan))
    monkeypatch.setattr(job.subprocess, "Popen", lambda *_args, **_kwargs: pytest.fail("unauthorized launch"))
    with pytest.raises(job.JobError):
        job.execute_plan(path, tmp_path / "absent-auth.json", tmp_path / "absent-key", "0" * 64)
    assert not Path(plan["output"]).exists()


def test_supervisor_kills_timed_out_mock_worker_once(plan, test_only_signature, tmp_path, monkeypatch):
    path = tmp_path / "plan.json"
    path.write_bytes(checkpoint.canonical(plan))
    events = []

    class FakeProcess:
        def __init__(self, *args, **kwargs):
            events.append("launch")
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False
        def wait(self, timeout):
            if "kill" not in events:
                raise subprocess.TimeoutExpired("TEST_ONLY", timeout)
            return -9
        def kill(self):
            events.append("kill")

    monkeypatch.setattr(job.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(job, "_check_device_idle", lambda *_: None)
    lock = tmp_path / "device.lock"
    monkeypatch.setattr(job, "_device_lock_path", lambda *_: lock)
    with pytest.raises(job.JobError, match="BUDGET_EXHAUSTED"):
        job.execute_plan(path, *test_only_signature)
    assert events == ["launch", "kill"] and not lock.exists()
    result = json.loads((Path(plan["output"]) / "supervisor.json").read_text())
    assert result["status"] == "BUDGET_EXHAUSTED" and result["automatic_retries"] == 0
    with pytest.raises(FileExistsError):
        job.execute_plan(path, *test_only_signature)
    assert events == ["launch", "kill"]


def test_busy_device_lock_blocks_a_different_output(plan, test_only_signature, tmp_path, monkeypatch):
    path = tmp_path / "plan.json"
    path.write_bytes(checkpoint.canonical(plan))
    lock = tmp_path / "device.lock"
    lock.write_text("ANOTHER_JOB")
    monkeypatch.setattr(job, "_device_lock_path", lambda *_: lock)
    monkeypatch.setattr(job.subprocess, "Popen", lambda *_args, **_kwargs: pytest.fail("busy-device launch"))
    with pytest.raises(FileExistsError):
        job.execute_plan(path, *test_only_signature)
    assert lock.read_text() == "ANOTHER_JOB"


@pytest.mark.parametrize("code,stdout", [(1, ""), (0, "12345"), (0, "N/A")])
def test_unavailable_or_busy_gpu_metadata_refused(monkeypatch, code, stdout):
    monkeypatch.setattr(job.subprocess, "run", lambda *_args, **_kwargs:
                        subprocess.CompletedProcess([], code, stdout, ""))
    with pytest.raises(job.JobError):
        job._check_device_idle("cuda:0")


def test_remapped_cuda_environment_refused_before_any_gpu_query(monkeypatch):
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "1,0")
    monkeypatch.setattr(job.subprocess, "run", lambda *_args, **_kwargs: pytest.fail("query after remapping"))
    with pytest.raises(job.JobError, match="GPU_MAPPING_UNSUPPORTED"):
        job._check_device_idle("cuda:0")


def test_global_local_lock_and_all_gpu_query(monkeypatch):
    monkeypatch.delenv("CUDA_VISIBLE_DEVICES", raising=False)
    assert job._device_lock_path("cuda:0") == job._device_lock_path("cuda:1")
    calls = []
    def query(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")
    monkeypatch.setattr(job.subprocess, "run", query)
    job._check_device_idle("cuda:0")
    assert len(calls) == 1 and not any(arg.startswith("--id") for arg in calls[0])
