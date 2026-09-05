"""Synthetic receipt fixtures only: no fixture represents a GPU run or audit.

The synthetic stored-audit receipt is an explicit test double. These tests
check reporting/admission arithmetic, not native semantics or model quality.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys

import pytest

from cas_meta2.curriculum import generate_dataset, graph_signature
from cas_meta2.ir import validate_program
from tools import summarize_learning as report


pytestmark = pytest.mark.not_gpu
FIXTURE = "FIXTURE_ONLY_SYNTHETIC_RECEIPTS_NOT_A_GPU_RUN_OR_SEMANTIC_AUDIT"
ARMS, B, FIELDS = report.ARMS, report.BASE, report.VERDICT_FIELDS
REAL_CODE = report._code_hashes()


def raw(value):
    return report.canonical(value) + b"\n"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if type(value) is bytes else raw(value))


def read(path):
    return json.loads(path.read_bytes())


def hashed(label):
    return sha256((FIXTURE + ":" + label).encode()).hexdigest()


def invalid_topology(binding):
    return {"binding": binding, "program": {"schema": "cas-meta2-program/0.1", "entry": "main", "procedures": {
        "main": {"input": "arg", "allowed_cjts": ["A", "C"], "steps": [
            {"kind": "RUN", "cjt_id": "A", "input": "arg", "output": "v0"},
            {"kind": "RUN", "cjt_id": "C", "input": "v0", "output": "v1"}], "return": "v1"}}}}


def make_packet(root):
    """Create source-derived synthetic tasks using a NON-LIVE dataset seed."""
    extracted = root / "fixture_packet_extracted"
    payload = {}
    dataset = generate_dataset(seed=99104421)
    parts = {"train.json": dataset["splits"]["train"], "validation.json": dataset["splits"]["validation"],
             "test_private.json": dataset["splits"]["test"],
             "test_public.json": [task["public"] for task in dataset["splits"]["test"]]}
    manifest = deepcopy(dataset["manifest"])
    manifest["sha256"] = {}
    for name, value in parts.items():
        payload[B + "dataset/" + name] = raw(value)
        manifest["sha256"][name] = sha256(raw(value)).hexdigest()
    payload[B + "dataset/dataset_manifest.json"] = raw(manifest)
    predictions, cases, audited = [], [], []
    for index, task in enumerate(parts["test_private.json"]):
        target = task["target"]
        actions = {}
        for arm in ARMS:
            action = deepcopy(target)
            if arm == "generic_untrained":
                action = {"status": "REJECTED", "reason": "ACTION_TOKEN_UNEXPECTED:PROC", "token_ids": [1, 2]}
            elif arm == "cas_untrained" and index % 4 != 0:
                action = {"status": "REJECTED", "reason": "GENERATION_LENGTH_EXHAUSTED:NO_SILENT_TRUNCATION", "token_ids": [1]}
            elif arm == "generic_trained" and index % 4 not in (0, 2):
                action = invalid_topology(target["binding"])
            elif arm == "cas_trained" and index % 4 not in (0, 1):
                action["binding"] = (target["binding"] + 1) % 3
            elif arm == "cas_trained" and index == 0:
                # Structural equality need not be exact source equality.
                for proc in action["program"]["procedures"].values():
                    proc["allowed_cjts"].reverse()
            actions[arm] = action
        predictions.append({"case_index": index, "public_sha256": report.canonical_sha256(task["public"]), "actions": actions})
        folder = B + f"evaluation/case_{index:04d}/"
        rows, derived = {}, {}
        for arm, action in actions.items():
            rejected = action.get("status") == "REJECTED" or arm == "generic_trained" and index % 4 in (1, 3)
            if rejected:
                verdict = {key: False for key in FIELDS}
                verdict.update(native_runs=0, reserved_policy_units=0)
                failure = {"code": "PREDICTED_PROGRAM_INVALID",
                           "type": "PolicyContractError" if action.get("status") == "REJECTED" else "CurriculumError",
                           "message": "ACTION_FIELDS_INVALID" if action.get("status") == "REJECTED" else "NATIVE_TOPOLOGY_MISMATCH"}
            else:
                binding = action["binding"] == target["binding"]
                procedure = graph_signature(action["program"]) == graph_signature(target["program"])
                verdict = {"task_correct": binding and procedure, "procedure_correct": procedure,
                           "binding_correct": binding, "dependency_correct": procedure,
                           "actual_output_correct": binding and procedure, "trace_valid": True,
                           "native_runs": validate_program(action["program"])["expanded_run_count"],
                           "reserved_policy_units": validate_program(action["program"])["expanded_run_count"] * 10}
                failure = None
            derived[arm] = {**verdict, "model_rejection": rejected}
            verified = {**verdict, "repair_required": False, "repair_success": None}
            rows[arm] = {"case_index": index, "arm": arm, "action": action, "verification": verified,
                         "model_rejection": rejected, "execution_status": "REJECTED" if rejected else "EXECUTED",
                         "failure": failure, "wall_seconds": 0.25}
            payload[folder + arm + "/case_receipt.json"] = raw(rows[arm])
            payload[folder + arm + "/verification.json"] = raw(verified)
        runs = validate_program(target["program"])["expanded_run_count"]
        reference = {**{key: True for key in FIELDS}, "native_runs": runs, "reserved_policy_units": runs * 10}
        case = {"case_index": index, "task_id": task["task_id"], "arms": rows,
                "reference_verification": {**reference, "repair_required": False, "repair_success": None},
                "reference_wall_seconds": 0.5, "case_wall_seconds": 2}
        cases.append(case)
        audited.append({"case_index": index, "reference": reference, "arms": derived})
        payload[folder + "case_receipt.json"] = raw(case)
        payload[folder + "reference_verdict.json"] = raw(case["reference_verification"])
    payload[B + "predictions.jsonl"] = b"".join(raw(row) for row in predictions)
    seal = {"test_private_labels_loaded": False, "arms": list(ARMS), "test_examples": 72, "prediction_count": 360,
            "sha256": sha256(payload[B + "predictions.jsonl"]).hexdigest(),
            "test_public_sha256": manifest["sha256"]["test_public.json"],
            "test_private_sha256": manifest["sha256"]["test_private.json"],
            "sealed_utc": "2026-09-01T01:00:00+00:00",
            "selection_timing": {arm: {"wall_seconds": 1.0, "device": FIXTURE} for arm in ARMS}}
    payload[B + "predictions_seal.json"] = raw(seal)
    payload[B + "test_gold_opening_receipt.json"] = raw({"opened_utc": "2026-09-01T01:00:01+00:00",
        "prediction_sha256_before_opening": seal["sha256"], "test_private_sha256": seal["test_private_sha256"]})
    history = [{"epoch": epoch, "optimizer_steps": {family: epoch * 16 for family in ("cas", "generic")},
                "families": {family: {"validation": {"token_cross_entropy": loss}, "training_tokens": 1000}
                             for family, loss in (("cas", 0.8 if epoch == 1 else 0.4),
                                                  ("generic", 0.3 if epoch == 1 else 0.5))}}
               for epoch in (1, 2)]
    matching = {"cas_trainable_parameters": 1000, "generic_trainable_parameters": 1001,
                "relative_difference": 0.001, "frozen_candidate_parameter_names": []}
    gradients = {family: {"all_parameter_tensors_connected": True, "trainable_parameters": size,
                         "connected_trainable_parameters": size} for family, size in (("cas", 1000), ("generic", 1001))}
    checkpoints = {}
    for family in ("cas", "generic"):
        checkpoints[family] = {}
        for state, suffix in (("initial", "initial"), ("selected", "best"), ("last", "last")):
            name = f"candidate_{family}_{suffix}.pt"
            content = (FIXTURE + " OPAQUE_CHECKPOINT_BYTES " + name).encode()
            epoch = 0 if state == "initial" else 1 if state == "selected" and family == "generic" else 2
            payload[B + name] = content
            checkpoints[family][state] = {"path": "/fixture/" + name, "sha256": sha256(content).hexdigest(), "bytes": len(content),
                "epoch": epoch, "optimizer_steps": epoch * 16,
                "validation": {"token_cross_entropy": 1.0} if epoch == 0 else history[epoch - 1]["families"][family]["validation"]}
    prereg = {"config": {"seed": 7, "epochs": 2, "batch_size": 16}, "train_examples": 256,
              "validation_examples": 48, "test_examples": 72, "arms": list(ARMS), "dataset_sha256": manifest["sha256"]}
    training = {"checkpoints": checkpoints, "completed_epochs": 2, "requested_epochs": 2,
                "optimizer_steps": {"cas": 32, "generic": 32}, "learning_conditions_matched": True,
                "parameter_matching": matching, "active_parameters": gradients, "stop_reason": "REQUESTED_EPOCHS_COMPLETED",
                "selection_rule": "Minimum validation token cross-entropy; earliest trained epoch wins exact ties.",
                "training_step_wall_seconds": {"cas": 5.0, "generic": 2.0}, "paired_training_wall_seconds": 10.0}
    for name, value in (("training_receipt.json", training), ("checkpoints.json", checkpoints),
                        ("training_preregistration.json", prereg), ("training_history.json", history),
                        ("parameter_matching.json", matching), ("gradient_connectivity.json", gradients)):
        payload[B + name] = raw(value)
    metrics, audit_metrics = {}, {}
    for arm in ARMS:
        values = [row["arms"][arm] for row in audited]
        counts = {key: sum(row[key] for row in values) for key in (*FIELDS, "native_runs", "reserved_policy_units")}
        rejected = sum(row["model_rejection"] for row in values)
        metrics[arm] = {"total": 72, **counts, "model_rejections": rejected, "native_executed": 72 - rejected,
                        "task_accuracy": counts["task_correct"] / 72, "repair_required_total": 0, "repair_success": None,
                        "all_cases_in_denominator": True, "worker_wall_seconds": 18.0}
        audit_metrics[arm] = {"total": 72, **counts, "model_rejection": rejected}
    payload[B + "evaluation_results.json"] = raw({"results": metrics, "cases": cases})
    campaign = {"status": "CAS_META_2_AWS_CAMPAIGN_COMPLETED", "completed": True, "evaluation_completed": True,
                "smoke_only": False, "all_test_cases_evaluated_per_arm": 72, "reference_cases": 72, "arm_verdicts": 360,
                "training": training, "results": metrics, "wall_seconds": 20.0, "workers": 8,
                "cas_task_accuracy_gain": 0.25, "generic_task_accuracy_gain": 0.5}
    payload[B + "campaign_receipt.json"] = raw(campaign)
    payload[B + "environment.json"] = raw({"cuda_device_name": FIXTURE, "torch": FIXTURE})
    fake_db = B + "fixture_only/native.db"
    payload[fake_db] = (FIXTURE + " NOT_SQLITE_NOT_A_NATIVE_TRACE").encode()
    empty_db = B + "fixture_only_incidental/native.db"
    payload[empty_db] = (FIXTURE + " INCIDENTAL_ZERO_TRACE_DATABASE_TEST_DOUBLE").encode()
    for name, value in payload.items():
        write(extracted / name, value)
    folder = root / "inspection"
    entries = [{"path": name, "bytes": len(value), "sha256": sha256(value).hexdigest()}
               for name, value in sorted(payload.items())]
    packet_sha, source_sha = hashed("packet"), hashed("source")[:40]
    index_path = folder / "full_member_index.json"
    write(index_path, {"schema": "cas-meta2-full-packet-index/1", "packet_sha256": packet_sha, "entries": entries})
    index_hash = sha256(index_path.read_bytes()).hexdigest()
    inspection = {"schema": "cas-meta2-packet-inspection/1", "status": "CAS_META_2_PACKET_FULL_EVIDENCE_VERIFIED",
        "packet_sha256": packet_sha, "source_sha": source_sha, "job": FIXTURE, "issues": [],
        "completed_run_evidence_verified": True, "archive_safety_and_all_included_bytes_checked": True,
        "original_full_index_verified": True, "collection": {"returncode": 0, "partial_evidence": False,
            "omitted_full_file_count": 0, "smoke_only": False},
        "extraction": {"path": str(extracted), "files_verified": len(entries), "all_member_bytes_verified_after_write": True},
        "full_member_index": str(index_path), "full_member_index_sha256": index_hash, "member_files": len(entries)}
    inspection_path = folder / "inspection_receipt.json"
    write(inspection_path, inspection)
    audit = {"schema": "cas-meta2-stored-packet-audit/1", "status": "CAS_META_2_STORED_FULL_AUDIT_PASSED",
        "completed": True, "errors": [], "completed_stages": ["inspection_inputs", "published_schema", "all_stored_trace_schemas",
                                                               "smoke_stored_semantics", "full_sealed_stored_semantics"],
        "packet_sha256": packet_sha, "source_sha": source_sha, "inspection_receipt": str(inspection_path),
        "inspection_receipt_sha256": sha256(inspection_path.read_bytes()).hexdigest(), "full_member_index_sha256": index_hash,
        "extracted_path": str(extracted), "all_extracted_files_unchanged_before_after": True, "member_files_reverified": len(entries),
        "published_schema": {"baseline_sha": report.BASELINE_SHA, "sha256": hashed("fixture-only-schema")},
        "audit_code_sha256": {str(report.ROOT / name): REAL_CODE[name] for name in report.AUDIT_CODE},
        "trace_schema_validation": {"databases": 2, "stored_traces": 1, "per_database": {fake_db: 1, empty_db: 0}},
        "smoke": {"reference_runs": 3, "candidate_runs": 3, "cases": [FIXTURE] * 3},
        "full": {"reference_runs": 72, "arm_choices": 360, "cases": audited, "metrics": audit_metrics},
        "neural_execution_performed": False, "checkpoint_loading_performed": False,
        "boundary": FIXTURE}
    audit_path = root / "audit" / "stored_audit_receipt.json"
    write(audit_path, audit)
    return {"root": root, "inspection": inspection_path, "audit": audit_path, "extracted": extracted}


@pytest.fixture(scope="module")
def packet(tmp_path_factory):
    return make_packet(tmp_path_factory.mktemp("summary_fixture_only"))


@pytest.fixture
def work(tmp_path, monkeypatch):
    monkeypatch.setattr(report, "ROOT", tmp_path)
    monkeypatch.setattr(report, "_code_hashes", lambda: dict(REAL_CODE))
    return tmp_path


def run(packet, work, **kwargs):
    return report.summarize(packet["inspection"], packet["audit"], output=work / "records" / "summary", **kwargs)


def test_complete_synthetic_summary_recounts_pairs_depth_and_output_boundaries(packet, work):
    result = run(packet, work)
    # Incidental empty databases do not remove any authoritative case verdict.
    assert sorted(read(packet["audit"])["trace_schema_validation"]["per_database"].values()) == [0, 1]
    assert [result["arms"][arm]["task_correct"] for arm in ARMS] == [18, 36, 0, 36, 72]
    assert all(row["total"] == 72 for row in result["arms"].values())
    assert result["arms"]["cas_trained"]["trace_valid"] == 72
    assert result["arms"]["cas_trained"]["exact_program_correct"] == 71
    assert result["arms"]["cas_trained"]["exact_program_and_binding_correct"] == 35
    assert result["arms"]["cas_trained"]["structurally_equivalent_not_exact"] == 1
    assert result["arms"]["generic_trained"]["decoded_binding_correct"] == 72
    pair = result["paired_comparisons"][2]
    assert (pair["both_correct"], pair["first_only_correct"], pair["second_only_correct"], pair["neither_correct"]) == (18, 18, 18, 18)
    assert result["learning_gains"] == {"cas_accuracy_gain": 0.25, "generic_accuracy_gain": 0.5,
        "cas_minus_generic_gain": -0.25, "cas_improved_on_these_tasks": True, "generic_improved_on_these_tasks": True}
    assert {depth: value["total"] for depth, value in result["depth_results"].items()} == {"2": 36, "3": 36}
    assert sum(value["arms"]["cas_trained"]["task_correct"] for value in result["depth_results"].values()) == 36
    assert result["repair"] == {"required": 0, "success": None, "status": "NOT_EXERCISED"}
    assert result["neural_execution_performed"] is False and result["checkpoint_loading_performed"] is False
    assert FIXTURE in result["compute"]["environment"]["cuda_device_name"]
    path = work / "records/summary"
    assert result["case_comparisons_sha256"] == sha256((path / "case_comparisons.json").read_bytes()).hexdigest()
    body = {key: value for key, value in result.items() if key != "summary_body_sha256"}
    assert result["summary_body_sha256"] == sha256(report.canonical(body)).hexdigest()
    assert result["evidence"]["stored_audit_receipt_sha256"] == sha256(packet["audit"].read_bytes()).hexdigest()


def test_rejections_keep_decoder_reason_not_wrapper_and_compute_is_separate(packet, work):
    result = run(packet, work)
    reasons = result["rejections"]
    assert reasons["cas_untrained"]["exact_reasons"] == {"GENERATION_LENGTH_EXHAUSTED:NO_SILENT_TRUNCATION": 54}
    assert reasons["generic_untrained"]["exact_reasons"] == {"ACTION_TOKEN_UNEXPECTED:PROC": 72}
    assert reasons["generic_trained"]["by_stage"] == {"native_admission": 36}
    assert reasons["generic_trained"]["by_category"] == {"native_topology": 36}
    assert result["training"]["families"]["cas"]["selected_epoch"] == 2
    assert result["training"]["families"]["generic"]["selected_epoch"] == 1
    assert result["training"]["parameter_mismatch_fraction"] == 0.001
    assert result["compute"]["campaign_wall_seconds"] == 20
    assert result["arms"]["rule"]["worker_wall_seconds"] == 18
    assert result["compute"]["provider_cost"]["available"] is False


@pytest.mark.parametrize("key,value", [
    ("status", "CAS_META_2_STORED_FULL_AUDIT_REJECTED"), ("completed", False),
    ("errors", [{"reason": "FIXTURE_ONLY_FAILURE"}]), ("all_extracted_files_unchanged_before_after", False),
    ("completed_stages", []), ("packet_sha256", "0" * 64), ("source_sha", "0" * 40),
    ("inspection_receipt_sha256", "0" * 64), ("full_member_index_sha256", "0" * 64),
    ("member_files_reverified", 0), ("neural_execution_performed", True), ("checkpoint_loading_performed", True),
])
def test_failed_or_unbound_audit_rejected_before_private_read(packet, work, monkeypatch, key, value):
    altered = read(packet["audit"])
    altered[key] = value
    path = work / "invalid_audit.json"
    write(path, altered)
    monkeypatch.setattr(report, "_test_mapping", lambda *_: pytest.fail("UNVERIFIED_AUDIT_REACHED_PRIVATE_TASKS"))
    with pytest.raises(ValueError):
        report.summarize(packet["inspection"], path, output=work / "records/summary")
    assert not (work / "records/summary").exists()


@pytest.mark.parametrize("key,value", [
    ("status", "CAS_META_2_PACKET_PARTIAL_EVIDENCE"), ("completed_run_evidence_verified", False),
    ("original_full_index_verified", False), ("issues", ["fixture-only mismatch"]),
])
def test_unverified_inspection_is_rejected(packet, work, key, value):
    altered = read(packet["inspection"])
    altered[key] = value
    path = work / "bad_inspection.json"
    write(path, altered)
    with pytest.raises(ValueError):
        report.summarize(path, packet["audit"], output=work / "records/summary")


@pytest.mark.parametrize("mutation", ["duplicate_case", "missing_arm", "wrong_verdict", "wrong_total", "bad_code_hash", "missing_trace"])
def test_recount_rejects_inconsistent_stored_audit_data(packet, work, mutation):
    altered = read(packet["audit"])
    if mutation == "duplicate_case":
        altered["full"]["cases"][1]["case_index"] = 0
    elif mutation == "missing_arm":
        del altered["full"]["cases"][0]["arms"]["rule"]
    elif mutation == "wrong_verdict":
        altered["full"]["cases"][0]["arms"]["rule"]["task_correct"] = False
    elif mutation == "wrong_total":
        altered["full"]["metrics"]["rule"]["task_correct"] = 71
    elif mutation == "bad_code_hash":
        altered["audit_code_sha256"][next(iter(altered["audit_code_sha256"]))] = "0" * 64
    else:
        altered["trace_schema_validation"]["per_database"] = {}
    path = work / "inconsistent_audit.json"
    write(path, altered)
    with pytest.raises(ValueError):
        report.summarize(packet["inspection"], path, output=work / "records/summary")


@pytest.mark.parametrize("mode", ["negative", "boolean", "all_zero"])
def test_invalid_or_entirely_empty_trace_counts_rejected_before_private_read(packet, work, monkeypatch, mode):
    altered = read(packet["audit"])
    traces = altered["trace_schema_validation"]
    incidental = B + "fixture_only_incidental/native.db"
    if mode == "all_zero":
        traces["per_database"] = {name: 0 for name in traces["per_database"]}
    else:
        traces["per_database"][incidental] = -1 if mode == "negative" else False
    traces["stored_traces"] = sum(traces["per_database"].values())
    path = work / "invalid_trace_counts.json"
    write(path, altered)
    monkeypatch.setattr(report, "_test_mapping", lambda *_: pytest.fail("INVALID_TRACE_COUNTS_REACHED_PRIVATE_TASKS"))
    with pytest.raises(ValueError, match="STORED_TRACE_COVERAGE_MISMATCH"):
        report.summarize(packet["inspection"], path, output=work / "records/summary")
    assert not (work / "records/summary").exists()


def test_changed_checkpoint_bytes_are_hashed_but_never_loaded(packet, work):
    checkpoint = packet["extracted"] / B / "candidate_cas_best.pt"
    original = checkpoint.read_bytes()
    try:
        checkpoint.write_bytes(original + b"FIXTURE_ONLY_TAMPER")
        with pytest.raises(ValueError, match="EXTRACTED_MEMBER_CHANGED"):
            run(packet, work)
    finally:
        checkpoint.write_bytes(original)


def test_unindexed_file_is_rejected_and_restored(packet, work):
    extra = packet["extracted"] / "fixture_only_unindexed.txt"
    try:
        extra.write_bytes(FIXTURE.encode())
        with pytest.raises(ValueError, match="UNINDEXED_EXTRACTED_FILE"):
            run(packet, work)
    finally:
        extra.unlink()


def test_input_change_during_analysis_prevents_output(packet, work, monkeypatch):
    original = report._training

    def changed_code(*args):
        result = original(*args)
        monkeypatch.setattr(report, "_code_hashes", lambda: {**REAL_CODE, "tools/summarize_learning.py": "0" * 64})
        return result

    monkeypatch.setattr(report, "_training", changed_code)
    with pytest.raises(ValueError, match="SUMMARY_INPUT_CHANGED"):
        run(packet, work)
    assert not (work / "records/summary").exists()


@pytest.mark.parametrize("destination", ["existing", "outside", "records_root"])
def test_output_is_new_and_contained(packet, work, destination):
    path = work / ("records/existing" if destination == "existing" else "outside" if destination == "outside" else "records")
    if destination != "outside":
        path.mkdir(parents=True)
        (path / "keep.txt").write_text(FIXTURE)
    with pytest.raises(ValueError, match="OUTPUT_MUST_BE_NEW_RECORDS_DIRECTORY"):
        report.summarize(packet["inspection"], packet["audit"], output=path)
    if destination != "outside":
        assert (path / "keep.txt").read_text() == FIXTURE


def test_optional_launcher_cost_is_hash_bound_and_not_an_invoice(packet, work):
    inspected = read(packet["inspection"])
    launch = {"status": "AWS_JOB_FINISHED", "job": inspected["job"], "source_sha": inspected["source_sha"],
        "result": {"sha256": inspected["packet_sha256"], "returncode": 0}, "termination_confirmed": True,
        "plan": {"instance_type": FIXTURE}, "cost_estimate": {"instance_wall_clock_seconds_upper_observation": 30,
            "compute_ebs_ipv4_usd_estimate": "0.012345", "excluded": FIXTURE + "; not an AWS invoice"}}
    path = work / "fixture_only_launch.json"
    write(path, launch)
    result = run(packet, work, launch_receipt=path)
    cost = result["compute"]["provider_cost"]
    assert cost["receipt_sha256"] == sha256(path.read_bytes()).hexdigest()
    assert cost["estimate"]["compute_ebs_ipv4_usd_estimate"] == "0.012345"
    assert "not an AWS invoice" in cost["boundary"]


def test_source_is_pure_and_gates_precede_private_task_reading():
    source = Path(report.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    imports |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    assert not any(name.startswith(("torch", "numpy", "pickle", "casformer", "cas_cjt", "cas_meta2.train", "cas_meta2.policy")) for name in imports)
    assert not any(isinstance(node, ast.Attribute) and node.attr in ("load_state_dict", "torch_load", "model", "backward") for node in ast.walk(tree))
    body = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "summarize")
    gate = next(node.lineno for node in ast.walk(body) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_audit_gate")
    private = next(node.lineno for node in ast.walk(body) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_test_mapping")
    assert gate < private
    assert "torch" not in sys.modules
