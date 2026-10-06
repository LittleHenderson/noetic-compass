from __future__ import annotations

import ast
import copy
import importlib.util
import inspect
import json
import os
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
LOCK_PATH = (
    ROOT
    / "docs"
    / "working"
    / "research_intervention_pythia160m_v2"
    / "PYTHIA160M_RESEARCH_SUCCESSOR_LOCK_V2.json"
)
EXECUTOR_PATH = (
    ROOT
    / "noetic-compass-scaffold"
    / "noetic-compass"
    / "api"
    / "services"
    / "cas_harness_pythia160m_research_executor.py"
)
AUDITOR_PATH = (
    ROOT
    / "noetic-compass-scaffold"
    / "noetic-compass"
    / "api"
    / "services"
    / "cas_harness_pythia160m_research_auditor.py"
)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


EXECUTOR = _load("pythia160m_research_executor_v2_test", EXECUTOR_PATH)
AUDITOR = _load("pythia160m_research_auditor_v2_test", AUDITOR_PATH)


@pytest.fixture(autouse=True)
def _clear_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(EXECUTOR.FEATURE_FLAG, raising=False)
    monkeypatch.delenv(EXECUTOR.LIVE_FLAG, raising=False)


def _lock() -> dict:
    return json.loads(LOCK_PATH.read_text(encoding="utf-8"))


def _prompt_split(lock: dict) -> dict:
    return json.loads(
        (ROOT / lock["frozen_files"]["prompt_split"]["path"]).read_text(
            encoding="utf-8"
        )
    )


def _fake_result(lock: dict, prompt_split: dict) -> dict:
    records: list[dict] = []
    seeds = lock["experiment"]["seeds"]
    calibration_ids = [
        prompt_id
        for label in ("^0|C", "^0|E")
        for prompt_id in prompt_split["calibration"][label]
    ]
    heldout: list[tuple[str, str]] = []
    for label in ("^0|C", "^0|E"):
        heldout.extend(
            (prompt_id, label) for prompt_id in prompt_split["heldout"][label]
        )
    heldout.extend(
        (row["prompt_id"], f"collateral:{row['category']}")
        for row in prompt_split["collateral_heldout"]
    )
    for index, prompt_id in enumerate(calibration_ids):
        records.append(
            {
                "prompt_id": prompt_id,
                "label": "^0|C" if index < 8 else "^0|E",
                "split": "calibration",
                "condition": "baseline",
                "dose": 0.0,
                "seed": seeds[index % len(seeds)],
                "target_projection": 0.0,
                "finite_logits": True,
                "logits_inline": [2.0, 0.0],
            }
        )
    conditions = [
        ("baseline", 0.0),
        ("no_op", 0.0),
        ("target_direction", -0.5),
        ("target_direction", -0.25),
        ("target_direction", 0.25),
        ("target_direction", 0.5),
        ("same_norm_random_direction", 0.5),
        ("wrong_layer", 0.5),
        ("wrong_token", 0.5),
        ("wrong_sign", 0.5),
        ("wrong_axis", 0.5),
        ("patch_back", 0.5),
    ]
    for index, (prompt_id, label) in enumerate(heldout):
        for condition, dose in conditions:
            projection = 0.0
            logits = [2.0, 0.0]
            if condition == "target_direction":
                projection = dose
                logits = [2.0, 0.01 * dose]
            elif condition in {
                "same_norm_random_direction",
                "wrong_layer",
                "wrong_token",
                "wrong_axis",
            }:
                projection = 0.05
                logits = [2.0, 0.001]
            elif condition == "wrong_sign":
                projection = -0.5
                logits = [2.0, -0.005]
            records.append(
                {
                    "prompt_id": prompt_id,
                    "label": label,
                    "split": "heldout",
                    "condition": condition,
                    "dose": dose,
                    "seed": seeds[index % len(seeds)],
                    "target_projection": projection,
                    "finite_logits": True,
                    "logits_inline": logits,
                }
            )
    payload = {
        "schema_version": AUDITOR.RESULT_SCHEMA,
        "status": "TERMINAL_UNAUDITED_RESEARCH_ONLY",
        "run_id": "static-model-free-fixture",
        "source_commit": "0" * 40,
        "lock_sha256": "static-fixture",
        "receipt_sha256": "not-a-live-receipt",
        "request_count": len(records),
        "records": records,
        "network_attempts": 0,
        "claim_status": "OPEN / NOT_LICENSED / NO ACCEPT / NO PRODUCTION EFFECT",
    }
    payload["result_payload_sha256"] = AUDITOR.canonical_sha256(payload)
    return payload


def test_successor_lock_and_guard_pass_without_framework_import() -> None:
    before = set(sys.modules)
    report = EXECUTOR.validate_successor_lock(ROOT, LOCK_PATH)
    guard = EXECUTOR.static_guard_fixture()
    after = set(sys.modules)
    assert report["status"] == "SUCCESSOR_LOCK_MODEL_FREE_PASS / RUN_NOT_AUTHORIZED"
    assert report["snapshot_file_count"] == 5
    assert report["heldout_prompt_count"] == 38
    assert report["model_loads"] == 0
    assert guard["status"] == "STATIC_ZERO_NETWORK_GUARD_PASS"
    assert guard["blocked_attempts"] == 1
    assert not (EXECUTOR.FORBIDDEN_FRAMEWORK_MODULES & (after - before))


def test_top_level_imports_are_standard_library_and_auditor_is_independent() -> None:
    tree = ast.parse(EXECUTOR_PATH.read_text(encoding="utf-8"))
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports |= {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not ({"torch", "transformers", "tokenizers", "safetensors"} & imports)
    auditor_source = AUDITOR_PATH.read_text(encoding="utf-8")
    assert "cas_harness_pythia160m_research_executor" not in auditor_source


def test_precondition_order_places_import_and_model_load_after_receipt_and_guard() -> None:
    source = inspect.getsource(EXECUTOR.execute_authorized_run)
    assert source.index("validate_owner_receipt") < source.index("_consume_nonce")
    assert source.index("_consume_nonce") < source.index("guard.install")
    assert source.index("guard.install") < source.index(
        "_import_frameworks_after_authorization"
    )
    assert source.index("_import_frameworks_after_authorization") < source.index(
        "_load_exact_model"
    )
    assert source.index("_load_exact_model") < source.index("output_root.mkdir")


def test_disabled_and_missing_receipt_fail_before_import_or_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "never-created"
    receipt = tmp_path / "missing.json"
    imported = False

    def forbidden_import(*args, **kwargs):
        nonlocal imported
        imported = True
        raise AssertionError("framework import path reached")

    monkeypatch.setattr(
        EXECUTOR, "_import_frameworks_after_authorization", forbidden_import
    )
    with pytest.raises(EXECUTOR.PythiaResearchDisabled):
        EXECUTOR.execute_authorized_run(
            repo_root=ROOT,
            lock_path=LOCK_PATH,
            receipt_path=receipt,
            output_root=output,
        )
    assert not imported and not output.exists()

    monkeypatch.setenv(EXECUTOR.FEATURE_FLAG, "1")
    with pytest.raises(
        EXECUTOR.PythiaResearchAuthorizationError, match="receipt is missing"
    ):
        EXECUTOR.execute_authorized_run(
            repo_root=ROOT,
            lock_path=LOCK_PATH,
            receipt_path=receipt,
            output_root=output,
        )
    assert not imported and not output.exists()


def test_invalid_test_receipt_fails_before_import_or_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "never-created"
    receipt = tmp_path / "STATIC_TEST_INVALID_RECEIPT.json"
    receipt.write_text(
        json.dumps(
            {
                "schema_version": "STATIC_TEST_INVALID / CANNOT_AUTHORIZE",
                "authorization_kind": "STATIC_TEST_ONLY",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv(EXECUTOR.FEATURE_FLAG, "true")
    imported = False

    def forbidden_import(*args, **kwargs):
        nonlocal imported
        imported = True
        raise AssertionError("framework import path reached")

    monkeypatch.setattr(
        EXECUTOR, "_import_frameworks_after_authorization", forbidden_import
    )
    with pytest.raises(EXECUTOR.PythiaResearchAuthorizationError):
        EXECUTOR.execute_authorized_run(
            repo_root=ROOT,
            lock_path=LOCK_PATH,
            receipt_path=receipt,
            output_root=output,
        )
    assert not imported and not output.exists()


def test_live_flag_is_permanently_rejected_before_receipt_or_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "never-created"
    monkeypatch.setenv(EXECUTOR.FEATURE_FLAG, "1")
    monkeypatch.setenv(EXECUTOR.LIVE_FLAG, "1")
    with pytest.raises(EXECUTOR.PythiaResearchDisabled, match="permanently"):
        EXECUTOR.execute_authorized_run(
            repo_root=ROOT,
            lock_path=LOCK_PATH,
            receipt_path=tmp_path / "missing.json",
            output_root=output,
        )
    assert not output.exists()
    assert not EXECUTOR._frameworks_loaded()


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda lock: lock["family_scope"].update(model_id="gpt2"), "Model family"),
        (lambda lock: lock["experiment"].update(seeds=[1]), "seed"),
        (
            lambda lock: lock["compute_cap"].update(network_allowed=True),
            "compute manifest",
        ),
        (
            lambda lock: lock["frozen_files"]["executor"].update(sha256="0" * 64),
            "executor",
        ),
        (
            lambda lock: lock["family_scope"].update(
                revision="607a30d783dfa663caf39e06633721c8d4cfcd7e"
            ),
            "revision",
        ),
    ],
)
def test_drifted_lock_fails_closed_before_framework_import(
    mutation, message: str
) -> None:
    lock = copy.deepcopy(_lock())
    mutation(lock)
    with pytest.raises(EXECUTOR.PythiaResearchLockError, match=message):
        EXECUTOR.validate_successor_lock(ROOT, LOCK_PATH, lock_override=lock)
    assert not EXECUTOR._frameworks_loaded()


def test_exact_model_free_request_plan_is_bounded() -> None:
    lock = _lock()
    split = _prompt_split(lock)
    requests = EXECUTOR.build_request_plan(lock, split)
    assert len(requests) == 472
    assert sum(row["split"] == "calibration" for row in requests) == 16
    assert sum(row["split"] == "heldout" for row in requests) == 456
    assert len(requests) <= lock["compute_cap"]["max_forward_passes"]


def test_independent_auditor_passes_complete_static_fixture_and_detects_drift() -> None:
    lock = _lock()
    split = _prompt_split(lock)
    result = _fake_result(lock, split)
    report = AUDITOR.audit_result_mapping(
        lock=lock, prompt_split=split, result=result
    )
    assert report["audit_status"] == "AUDIT_PASS_RESEARCH_ONLY"
    assert all(report["gates"].values())
    assert report["spearman_rho"] == pytest.approx(1.0)

    drifted = copy.deepcopy(result)
    for record in drifted["records"]:
        if (
            record["split"] == "heldout"
            and record["condition"] == "same_norm_random_direction"
        ):
            record["target_projection"] = 0.5
    payload = dict(drifted)
    payload.pop("result_payload_sha256")
    drifted["result_payload_sha256"] = AUDITOR.canonical_sha256(payload)
    failed = AUDITOR.audit_result_mapping(
        lock=lock, prompt_split=split, result=drifted
    )
    assert failed["audit_status"] == "FAIL_CLOSED"
    assert any(
        finding == "CONTROL_EFFECT_CEILING_FAIL:same_norm_random_direction"
        for finding in failed["findings"]
    )
