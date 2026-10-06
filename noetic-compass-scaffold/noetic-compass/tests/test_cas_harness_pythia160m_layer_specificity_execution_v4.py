from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SERVICE_ROOT = REPO_ROOT / "noetic-compass-scaffold/noetic-compass/api/services"
EXECUTOR_PATH = SERVICE_ROOT / "cas_harness_pythia160m_layer_specificity_executor_v4.py"
AUDITOR_PATH = SERVICE_ROOT / "cas_harness_pythia160m_layer_specificity_auditor_v4.py"
BOOTSTRAP_PATH = SERVICE_ROOT / "cas_harness_pythia160m_layer_specificity_bootstrap_v4.py"
LOCK_PATH = (
    REPO_ROOT
    / "docs/working/research_intervention_pythia160m_v4_execution"
    / "PYTHIA160M_EXECUTION_SUCCESSOR_LOCK_V4.json"
)


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _static_receipt(executor, lock: dict, lock_path: Path, run_id: str) -> dict:
    bindings = {
        label: lock["frozen_files"][label]["sha256"]
        for label in lock["receipt_contract"]["must_bind_frozen_files"]
    }
    bindings.update(
        {
            label: lock["preserved_prior_evidence"][label]["sha256"]
            for label in lock["receipt_contract"]["must_bind_preserved_evidence"]
        }
    )
    bindings.update(
        {
            "request_count": 1536,
            "compute_cap_sha256": executor.canonical_sha256(lock["compute_cap"]),
            "seed_schedule_sha256": executor.canonical_sha256(lock["seed_schedule"]),
        }
    )
    receipt = {
        "schema_version": executor.RECEIPT_SCHEMA,
        "status": "STATIC_TEST_FIXTURE_ONLY / NO EXECUTION AUTHORITY",
        "run_id": run_id,
        "nonce": "a" * 64,
        "source_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "execution_lock_sha256": executor.sha256_file(lock_path),
        "bindings": bindings,
        "created_at": "2099-01-01T00:00:00Z",
        "expires_at": "2099-01-01T00:01:00Z",
    }
    receipt["receipt_payload_sha256"] = executor.canonical_sha256(receipt)
    return receipt


def test_modules_import_without_framework_or_model_load():
    before = {name for name in ("torch", "transformers") if name in sys.modules}
    _load(EXECUTOR_PATH, "v4_exec_import_test")
    _load(AUDITOR_PATH, "v4_audit_import_test")
    _load(BOOTSTRAP_PATH, "v4_boot_import_test")
    after = {name for name in ("torch", "transformers") if name in sys.modules}
    assert after == before


def test_execution_lock_validates_model_free_and_creates_no_output(tmp_path: Path):
    executor = _load(EXECUTOR_PATH, "v4_exec_lock_test")
    result = executor.validate_execution_lock(REPO_ROOT, LOCK_PATH)
    assert result["request_count"] == 1536
    assert executor.frameworks_loaded() == []
    assert list(tmp_path.iterdir()) == []


def test_missing_receipt_fails_before_import_model_or_output(tmp_path: Path):
    executor = _load(EXECUTOR_PATH, "v4_exec_missing_receipt_test")
    output_root = tmp_path / "pythia160m-riv4-missingreceipt0001"
    with pytest.raises(executor.V4AuthorizationError, match="receipt is missing"):
        executor.validate_owner_receipt(
            repo_root=REPO_ROOT,
            lock_path=LOCK_PATH,
            receipt_path=tmp_path / "missing.json",
            output_root=output_root,
        )
    assert executor.frameworks_loaded() == []
    assert not output_root.exists()


@pytest.mark.parametrize(
    "label",
    ["executor", "model_manifest", "prompt_split", "intervention_map_v2"],
)
def test_drifted_frozen_requirement_fails_before_import_or_output(
    tmp_path: Path, label: str
):
    executor = _load(EXECUTOR_PATH, f"v4_exec_drift_{label}")
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    lock["frozen_files"][label]["sha256"] = "0" * 64
    drifted = tmp_path / f"{label}.json"
    drifted.write_text(json.dumps(lock), encoding="utf-8")
    with pytest.raises(executor.V4ExecutionError, match="hash drift"):
        executor.validate_execution_lock(REPO_ROOT, drifted)
    assert executor.frameworks_loaded() == []
    assert sorted(path.name for path in tmp_path.iterdir()) == [drifted.name]


def test_drifted_lock_schema_fails_before_import_or_output(tmp_path: Path):
    executor = _load(EXECUTOR_PATH, "v4_exec_schema_drift")
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    lock["schema_version"] = "drift"
    drifted = tmp_path / "lock.json"
    drifted.write_text(json.dumps(lock), encoding="utf-8")
    with pytest.raises(executor.V4ExecutionError, match="schema drift"):
        executor.validate_execution_lock(REPO_ROOT, drifted)
    assert executor.frameworks_loaded() == []


def test_drifted_receipt_binding_fails_before_import_or_output(tmp_path: Path):
    executor = _load(EXECUTOR_PATH, "v4_exec_receipt_drift")
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    run_id = "pythia160m-riv4-staticfixture0001"
    receipt = _static_receipt(executor, lock, LOCK_PATH, run_id)
    receipt["bindings"]["prompt_split"] = "0" * 64
    receipt["receipt_payload_sha256"] = executor.canonical_sha256(
        {key: value for key, value in receipt.items() if key != "receipt_payload_sha256"}
    )
    receipt_path = tmp_path / "fixture.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    output_root = tmp_path / run_id
    with pytest.raises(executor.V4AuthorizationError, match="prompt_split"):
        executor.validate_owner_receipt(
            repo_root=REPO_ROOT,
            lock_path=LOCK_PATH,
            receipt_path=receipt_path,
            output_root=output_root,
            allow_static_test_fixture=True,
        )
    assert executor.frameworks_loaded() == []
    assert not output_root.exists()


def test_complete_static_fixture_receipt_validates_without_import_or_output(
    tmp_path: Path,
):
    executor = _load(EXECUTOR_PATH, "v4_exec_receipt_complete")
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    run_id = "pythia160m-riv4-staticfixture0003"
    receipt = _static_receipt(executor, lock, LOCK_PATH, run_id)
    receipt_path = tmp_path / "fixture.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    output_root = tmp_path / run_id
    token = executor.validate_owner_receipt(
        repo_root=REPO_ROOT,
        lock_path=LOCK_PATH,
        receipt_path=receipt_path,
        output_root=output_root,
        allow_static_test_fixture=True,
    )
    assert token.run_id == run_id
    assert token.nonce_consumed is False
    assert executor.frameworks_loaded() == []
    assert not output_root.exists()
    assert not token.nonce_marker.exists()


def test_existing_output_fails_before_import_or_model_load(tmp_path: Path):
    executor = _load(EXECUTOR_PATH, "v4_exec_output_exists")
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    run_id = "pythia160m-riv4-staticfixture0002"
    receipt = _static_receipt(executor, lock, LOCK_PATH, run_id)
    receipt_path = tmp_path / "fixture.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    output_root = tmp_path / run_id
    output_root.mkdir()
    with pytest.raises(executor.V4AuthorizationError, match="already exists"):
        executor.validate_owner_receipt(
            repo_root=REPO_ROOT,
            lock_path=LOCK_PATH,
            receipt_path=receipt_path,
            output_root=output_root,
            allow_static_test_fixture=True,
        )
    assert executor.frameworks_loaded() == []
    assert list(output_root.iterdir()) == []


def test_exact_final_allowed_and_first_prohibited_request_boundary():
    executor = _load(EXECUTOR_PATH, "v4_exec_cap_test")
    validation = executor.validate_execution_lock(REPO_ROOT, LOCK_PATH)
    assert validation["request_count"] == 1536
    assert validation["lock"]["compute_cap"]["max_forward_passes"] == 1536
    assert validation["lock"]["compute_cap"]["first_prohibited_forward_pass_index_zero_based"] == 1536


def test_precondition_order_is_receipt_then_nonce_then_framework_then_output():
    source = EXECUTOR_PATH.read_text(encoding="utf-8")
    execute_body = source[source.index("def execute_authorized_run(") :]
    assert execute_body.index("validate_owner_receipt(") < execute_body.index("_consume_nonce(")
    assert execute_body.index("_consume_nonce(") < execute_body.index('importlib.import_module("torch")')
    assert execute_body.index('importlib.import_module("torch")') < execute_body.index("from_pretrained(")
    assert execute_body.index("from_pretrained(") < execute_body.index("output_root.mkdir(")


def test_independent_auditor_rejects_failure_packet_without_framework_import(
    tmp_path: Path,
):
    auditor = _load(AUDITOR_PATH, "v4_auditor_failure_test")
    run_dir = tmp_path / "failed"
    run_dir.mkdir()
    (run_dir / "failure.json").write_text("{}", encoding="utf-8")
    with pytest.raises(auditor.V4AuditError, match="fail-closed"):
        auditor.audit_result_directory(
            repo_root=REPO_ROOT, lock_path=LOCK_PATH, run_dir=run_dir
        )
    assert not ({"torch", "transformers"} & set(sys.modules))
