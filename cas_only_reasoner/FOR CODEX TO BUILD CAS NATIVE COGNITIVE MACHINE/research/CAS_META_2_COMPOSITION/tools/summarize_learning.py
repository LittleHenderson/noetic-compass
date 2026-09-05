"""Post-run, data-only learning summary from two successful audit receipts.

This is separate from the frozen cloud implementation. It rehashes the entire
extracted inventory, binds the stored semantic audit, and recounts case-level
results. It does not load checkpoints, execute models, or rerun native work.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cas_meta2.codec import canonical_sha256, validate_action
from cas_meta2.curriculum import SCHEMA, graph_signature, validate_dataset
from cas_meta2.ir import validate_program
from tools.audit_stored_packet import Extracted, _test_mapping
from tools.inspect_cloud_packet import ARMS, BASE, BASELINE_SHA, MAX_JSON, SHA256, VERDICT_FIELDS, file_hash, json_bytes

AUDIT_CODE = ("tools/audit_stored_packet.py", "tools/inspect_cloud_packet.py",
              *("cas_meta2/" + name + ".py" for name in
                ("stored", "executor", "ir", "codec", "curriculum", "native", "campaign")))
PAIRS = (("cas_trained", "cas_untrained"), ("generic_trained", "generic_untrained"),
         ("cas_trained", "generic_trained"))
BOUNDARY = ("One controlled procedure-language pilot and one training seed. "
            "A complete summary does not establish CAS advantage, general reasoning, "
            "repair skill, restart execution, lifelong learning or production readiness.")


class SummaryInvalid(ValueError):
    pass


def require(value, reason):
    if not value:
        raise SummaryInvalid(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _plain_path(path, *, file=False):
    path = Path(path).absolute()
    for item in (path, *path.parents):
        require(not item.is_symlink() and not getattr(item, "is_junction", lambda: False)(), "INPUT_OR_OUTPUT_LINK_REFUSED")
    if file:
        require(path.is_file(), "REGULAR_INPUT_FILE_REQUIRED")
    return path


def _read_receipt(path):
    path = _plain_path(path, file=True)
    require(path.stat().st_size <= MAX_JSON, "RECEIPT_SIZE_LIMIT")
    raw = path.read_bytes()
    return path, sha256(raw).hexdigest(), json_bytes(raw)


def _integer(value, reason, *, minimum=0):
    require(type(value) is int and value >= minimum, reason)
    return value


def _seconds(value):
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0, "INVALID_MEASURED_TIME")
    return value


def _code_hashes():
    return {name: file_hash(ROOT / name) for name in (*AUDIT_CODE, "tools/summarize_learning.py")}


def _audit_gate(packet, audit, inspection_path, inspection_hash, code):
    """Must complete before any held-out private task is opened here."""
    require(packet.mode == "full", "FULL_RUN_REQUIRED_NOT_SMOKE")
    require(audit.get("schema") == "cas-meta2-stored-packet-audit/1"
            and audit.get("status") == "CAS_META_2_STORED_FULL_AUDIT_PASSED"
            and audit.get("completed") is True and audit.get("errors") == [], "SUCCESSFUL_STORED_AUDIT_REQUIRED")
    require(audit.get("inspection_receipt_sha256") == inspection_hash
            and Path(audit["inspection_receipt"]).resolve() == inspection_path.resolve()
            and audit.get("packet_sha256") == packet.inspection["packet_sha256"]
            and audit.get("source_sha") == packet.inspection["source_sha"]
            and audit.get("full_member_index_sha256") == packet.index_hash
            and Path(audit["extracted_path"]).resolve() == packet.root.resolve(), "AUDIT_INSPECTION_BINDING_MISMATCH")
    require(audit.get("all_extracted_files_unchanged_before_after") is True
            and audit.get("member_files_reverified") == len(packet.inventory)
            and audit.get("neural_execution_performed") is False
            and audit.get("checkpoint_loading_performed") is False, "STORED_AUDIT_EVIDENCE_BOUNDARY_INVALID")
    require(set(audit.get("completed_stages", [])) >= {
        "inspection_inputs", "published_schema", "all_stored_trace_schemas",
        "smoke_stored_semantics", "full_sealed_stored_semantics"}, "STORED_AUDIT_STAGES_INCOMPLETE")
    recorded_code = audit.get("audit_code_sha256", {})
    require(type(recorded_code) is dict and len(recorded_code) == len(AUDIT_CODE), "AUDIT_CODE_IDENTITY_MISSING")
    for relative in AUDIT_CODE:
        matches = [checksum for name, checksum in recorded_code.items()
                   if name.replace("\\", "/").endswith("/" + relative)]
        require(matches == [code[relative]], "AUDITED_CODE_IDENTITY_CHANGED:" + relative)
    schema = audit.get("published_schema", {})
    require(schema.get("baseline_sha") == BASELINE_SHA and SHA256.fullmatch(schema.get("sha256", "")), "PUBLISHED_SCHEMA_BINDING_MISSING")
    traces = audit.get("trace_schema_validation", {})
    counts = traces.get("per_database", {})
    databases = {name for name in packet.inventory if name.endswith("native.db")}
    require(type(counts) is dict and set(counts) == databases and databases
            and all(type(n) is int and n >= 0 for n in counts.values())
            and traces.get("databases") == len(counts)
            and traces.get("stored_traces") == sum(counts.values()) > 0, "STORED_TRACE_COVERAGE_MISMATCH")
    full = audit.get("full", {})
    require(full.get("reference_runs") == 72 and full.get("arm_choices") == 360, "STORED_AUDIT_DENOMINATOR_MISMATCH")
    smoke = audit.get("smoke", {})
    require(smoke.get("reference_runs") == 3 and smoke.get("candidate_runs") == 3
            and len(smoke.get("cases", [])) == 3, "STORED_SMOKE_COVERAGE_MISMATCH")
    return full


def paired(rows, first, second):
    counts = Counter((row["arms"][first]["task_correct"], row["arms"][second]["task_correct"]) for row in rows)
    total = len(rows)
    require(total > 0, "EMPTY_PAIRED_DENOMINATOR")
    difference = counts[True, False] - counts[False, True]
    return {"first": first, "second": second, "total": total,
            "both_correct": counts[True, True], "first_only_correct": counts[True, False],
            "second_only_correct": counts[False, True], "neither_correct": counts[False, False],
            "difference_numerator": difference, "accuracy_difference": difference / total,
            "percentage_point_difference": 100 * difference / total}


def rejection_category(reason):
    code = reason.split(":", 1)[0]
    if code == "GENERATION_LENGTH_EXHAUSTED":
        return "missing_termination_at_length_limit"
    if "TOPOLOGY" in code:
        return "native_topology"
    if code == "ACCEPTED_EFFECT_RESULT_REQUIRED":
        return "raw_input_return"
    if "CYCLE" in code:
        return "call_cycle"
    if "SCOPE" in code or "ALLOWLIST" in code:
        return "permission_scope"
    if "UNBOUND" in code or "UNDECLARED" in code or "CALLEE_MISSING" in code or "UNKNOWN_PROCEDURE" in code:
        return "unbound_reference"
    if code.startswith(("ACTION_TOKEN", "ACTION_BINDING_TOKEN", "PROCEDURE_DUPLICATE")):
        return "token_syntax_or_canonical_order"
    return "other_invalid_program"


def _ordered(rows, label):
    require(type(rows) is list and len(rows) == 72
            and all(type(row) is dict and type(row.get("case_index")) is int for row in rows)
            and sorted(row["case_index"] for row in rows) == list(range(72)), label + "_COVERAGE_INVALID")
    return {row["case_index"]: row for row in rows}


def _case_rows(packet, tasks, predictions, full, evaluation):
    audited = _ordered(full["cases"], "AUDITED_CASE")
    saved = _ordered(evaluation["cases"], "SAVED_CASE")
    rows = []
    for index, (task, prediction) in enumerate(zip(tasks, predictions, strict=True)):
        require(set(audited[index]["arms"]) == set(saved[index]["arms"]) == set(ARMS), "CASE_ARM_COVERAGE_INVALID")
        folder = BASE + f"evaluation/case_{index:04d}/"
        require(packet.json(folder + "case_receipt.json") == saved[index], "CASE_RECEIPT_COPY_MISMATCH")
        expected = task["target"]
        stats = validate_program(expected["program"])
        require(stats["max_call_depth"] == task["provenance"]["depth"], "TARGET_DEPTH_PROVENANCE_MISMATCH")
        result = {"case_index": index, "task_id": task["task_id"], "public_sha256": prediction["public_sha256"],
                  "target_depth_including_entry": stats["max_call_depth"],
                  "target_expanded_runs": stats["expanded_run_count"], "arms": {}}
        for arm in ARMS:
            action = prediction["actions"][arm]
            case = saved[index]["arms"][arm]
            verdict = audited[index]["arms"][arm]
            require(packet.json(folder + arm + "/case_receipt.json") == case
                    and packet.json(folder + arm + "/verification.json") == case["verification"]
                    and case["action"] == action and case["case_index"] == index and case["arm"] == arm,
                    "SEALED_ACTION_OR_VERDICT_COPY_MISMATCH")
            require(all(type(verdict.get(key)) is bool and case["verification"].get(key) is verdict[key]
                        for key in VERDICT_FIELDS)
                    and verdict["task_correct"] == all(verdict[key] for key in VERDICT_FIELDS[1:]), "AUDITED_VERDICT_MISMATCH")
            require(case["verification"].get("repair_required") is False
                    and case["verification"].get("repair_success") is None, "REPAIR_NOT_EXERCISED_BOUNDARY_CHANGED")
            rejected = verdict.get("model_rejection")
            require(type(rejected) is bool and case["model_rejection"] is rejected
                    and case["execution_status"] == ("REJECTED" if rejected else "EXECUTED"), "EXECUTION_ADMISSION_MISMATCH")
            for key in ("native_runs", "reserved_policy_units"):
                _integer(verdict[key], "INVALID_NATIVE_COMPUTE")
                require(case["verification"].get(key, 0) == verdict[key], "AUDITED_COMPUTE_MISMATCH")
            syntax_valid = True
            try:
                validate_action(action)
            except ValueError:
                syntax_valid = False
            require(not verdict["task_correct"] or syntax_valid and not rejected, "INVALID_ACTION_MARKED_CORRECT")
            # A codec-valid prediction can still fail IR/native admission.
            # Exact JSON comparison must not turn that model error into a
            # reporting failure by attempting a second IR admission here.
            exact = syntax_valid and canonical_sha256(action["program"]) == canonical_sha256(expected["program"])
            structural = not rejected and graph_signature(action["program"]) == graph_signature(expected["program"])
            require(structural is verdict["procedure_correct"], "STRUCTURAL_METRIC_MISMATCH")
            binding = syntax_valid and action["binding"] == expected["binding"]
            require(rejected or binding is verdict["binding_correct"], "BINDING_METRIC_MISMATCH")
            rejection = None
            if rejected:
                require(not any(verdict[key] for key in VERDICT_FIELDS) and verdict["native_runs"] == 0
                        and verdict["reserved_policy_units"] == 0, "REJECTED_ACTION_HAS_SUCCESS_OR_COMPUTE")
                decoder_reason = action.get("reason") if action.get("status") == "REJECTED" else None
                failure = case.get("failure")
                require(type(failure) is dict and type(failure.get("message")) is str, "REJECTION_REASON_MISSING")
                reason = decoder_reason if decoder_reason is not None else failure["message"]
                require(type(reason) is str and 0 < len(reason) <= 4096, "REJECTION_REASON_INVALID")
                rejection = {"stage": "decoder" if decoder_reason is not None else "native_admission",
                             "reason": reason, "category": rejection_category(reason), "admission_failure": failure}
            result["arms"][arm] = {**{key: verdict[key] for key in (*VERDICT_FIELDS, "native_runs", "reserved_policy_units")},
                "model_rejection": rejected, "syntax_valid": syntax_valid, "native_admitted": not rejected,
                "exact_program_correct": exact, "exact_program_and_binding_correct": exact and binding,
                "decoded_binding_correct": binding, "structurally_equivalent_not_exact": structural and not exact,
                "rejection": rejection, "worker_wall_seconds": _seconds(case["wall_seconds"])}
        result["reference_wall_seconds"] = _seconds(saved[index]["reference_wall_seconds"])
        result["case_wall_seconds"] = _seconds(saved[index]["case_wall_seconds"])
        rows.append(result)
    return rows


def arm_totals(rows, arm):
    values = [row["arms"][arm] for row in rows]
    fields = (*VERDICT_FIELDS, "syntax_valid", "native_admitted", "exact_program_correct",
              "exact_program_and_binding_correct", "decoded_binding_correct", "structurally_equivalent_not_exact")
    counts = {key: sum(value[key] is True for value in values) for key in fields}
    return {"total": len(values), **counts, "task_accuracy": counts["task_correct"] / len(values),
            "model_rejections": sum(value["model_rejection"] for value in values),
            "native_runs": sum(value["native_runs"] for value in values),
            "reserved_policy_units": sum(value["reserved_policy_units"] for value in values),
            "worker_wall_seconds": sum(value["worker_wall_seconds"] for value in values),
            "all_cases_in_denominator": True}


def _training(packet, campaign):
    training = packet.json(BASE + "training_receipt.json")
    matching = packet.json(BASE + "parameter_matching.json")
    gradients = packet.json(BASE + "gradient_connectivity.json")
    checkpoints = packet.json(BASE + "checkpoints.json")
    prereg = packet.json(BASE + "training_preregistration.json")
    history = packet.json(BASE + "training_history.json")
    require(training == campaign["training"] and matching == training["parameter_matching"]
            and gradients == training["active_parameters"] and checkpoints == training["checkpoints"], "TRAINING_RECORD_COPY_MISMATCH")
    epochs = _integer(training["completed_epochs"], "INVALID_COMPLETED_EPOCHS", minimum=1)
    require(epochs <= training["requested_epochs"] == prereg["config"]["epochs"] <= 200
            and len(history) == epochs and [row["epoch"] for row in history] == list(range(1, epochs + 1)), "TRAINING_EPOCH_COVERAGE_MISMATCH")
    config = prereg["config"]
    require(config["seed"] == 7 and config["batch_size"] == 16
            and prereg["train_examples"] == 256 and prereg["validation_examples"] == 48
            and prereg["test_examples"] == 72 and set(prereg["arms"]) == set(ARMS), "PREREGISTERED_CONDITIONS_MISMATCH")
    expected_steps = epochs * math.ceil(256 / config["batch_size"])
    require(training["optimizer_steps"] == {"cas": expected_steps, "generic": expected_steps}
            and training["learning_conditions_matched"] is True, "PAIRED_OPTIMIZER_STEPS_MISMATCH")
    cas_n = _integer(matching["cas_trainable_parameters"], "INVALID_PARAMETER_COUNT", minimum=1)
    generic_n = _integer(matching["generic_trainable_parameters"], "INVALID_PARAMETER_COUNT", minimum=1)
    mismatch = abs(cas_n - generic_n) / cas_n
    require(mismatch <= 0.01 and matching["relative_difference"] == mismatch
            and matching["frozen_candidate_parameter_names"] == [], "ACTIVE_PARAMETER_MATCH_INVALID")
    records = {}
    for family, number in (("cas", cas_n), ("generic", generic_n)):
        gradient = gradients[family]
        require(gradient["all_parameter_tensors_connected"] is True
                and gradient["connected_trainable_parameters"] == gradient["trainable_parameters"] == number,
                "ACTIVE_GRADIENT_COVERAGE_INVALID")
        require(set(checkpoints[family]) == {"initial", "selected", "last"}, "SIX_CHECKPOINTS_REQUIRED")
        for state, suffix in (("initial", "initial"), ("selected", "best"), ("last", "last")):
            record = checkpoints[family][state]
            name = f"candidate_{family}_{suffix}.pt"
            packet.same_hash(BASE + name, record["sha256"])
            require(record["path"].endswith("/" + name)
                    and packet.inventory[BASE + name]["bytes"] == record["bytes"] > 0, "CHECKPOINT_BYTE_BINDING_MISMATCH")
        selected = checkpoints[family]["selected"]
        losses = [row["families"][family]["validation"]["token_cross_entropy"] for row in history]
        require(all(type(loss) in (int, float) and math.isfinite(loss) and loss >= 0 for loss in losses), "INVALID_VALIDATION_LOSS")
        best_epoch = min(range(1, epochs + 1), key=lambda epoch: (losses[epoch - 1], epoch))
        require(selected["epoch"] == best_epoch and selected["optimizer_steps"] == best_epoch * 16
                and selected["validation"] == history[best_epoch - 1]["families"][family]["validation"]
                and checkpoints[family]["initial"]["epoch"] == checkpoints[family]["initial"]["optimizer_steps"] == 0
                and checkpoints[family]["last"]["epoch"] == epochs
                and checkpoints[family]["last"]["optimizer_steps"] == expected_steps, "CHECKPOINT_SELECTION_MISMATCH")
        records[family] = {"trainable_parameters": number, "all_trainable_parameters_observed_connected": True,
            "completed_optimizer_steps": expected_steps, "selected_epoch": best_epoch,
            "selected_optimizer_steps": selected["optimizer_steps"], "selected_validation": selected["validation"],
            "initial_validation": checkpoints[family]["initial"]["validation"],
            "training_tokens": sum(row["families"][family]["training_tokens"] for row in history),
            "training_step_wall_seconds": _seconds(training["training_step_wall_seconds"][family]),
            "checkpoint_hashes": {state: checkpoints[family][state]["sha256"] for state in checkpoints[family]}}
    for row in history:
        require(row["optimizer_steps"] == {"cas": row["epoch"] * 16, "generic": row["epoch"] * 16}
                and row["families"]["cas"]["training_tokens"] == row["families"]["generic"]["training_tokens"] > 0,
                "PAIRED_EPOCH_EXPOSURE_MISMATCH")
    return {"config": config, "requested_epochs": training["requested_epochs"], "completed_epochs": epochs,
            "stop_reason": training["stop_reason"], "parameter_mismatch_fraction": mismatch,
            "selection_rule": training["selection_rule"], "families": records,
            "paired_training_wall_seconds": _seconds(training["paired_training_wall_seconds"]),
            "timing_boundary": "Synchronized training-step wall time excludes shared encoding, validation and checkpoint writes. "
                               "Selected checkpoints may have different epochs despite matched total training exposure."}


def _launch_cost(path, packet):
    if path is None:
        return {"available": False, "boundary": "No launcher receipt supplied; no dollar cost inferred."}, None
    path, checksum, receipt = _read_receipt(path)
    require(receipt.get("status") == "AWS_JOB_FINISHED" and receipt.get("job") == packet.inspection["job"]
            and receipt.get("source_sha") == packet.inspection["source_sha"]
            and receipt.get("result", {}).get("sha256") == packet.inspection["packet_sha256"]
            and receipt["result"].get("returncode") == 0 and receipt.get("termination_confirmed") is True,
            "LAUNCH_RECEIPT_BINDING_OR_COMPLETION_MISMATCH")
    cost = receipt.get("cost_estimate")
    require(type(cost) is dict and type(cost.get("compute_ebs_ipv4_usd_estimate")) is str, "LAUNCH_COST_ESTIMATE_MISSING")
    _seconds(cost["instance_wall_clock_seconds_upper_observation"])
    value = float(cost["compute_ebs_ipv4_usd_estimate"])
    require(math.isfinite(value) and value >= 0, "LAUNCH_COST_ESTIMATE_INVALID")
    return {"available": True, "receipt_sha256": checksum, "estimate": cost,
            "instance_type": receipt["plan"]["instance_type"],
            "boundary": "Recorded whole-job estimate, not an AWS invoice or per-arm cost."}, (path, checksum)


def summarize(inspection_receipt, stored_audit_receipt, *, output, launch_receipt=None):
    output = _plain_path(output)
    require(output.resolve().is_relative_to((ROOT / "records").resolve())
            and output.resolve() != (ROOT / "records").resolve()
            and not output.exists(), "OUTPUT_MUST_BE_NEW_RECORDS_DIRECTORY")
    inspection_path, inspection_hash, _ = _read_receipt(inspection_receipt)
    audit_path, audit_hash, audit = _read_receipt(stored_audit_receipt)
    code = _code_hashes()
    packet = Extracted(inspection_path)
    require(not output.resolve().is_relative_to(packet.root.resolve()), "OUTPUT_INSIDE_EVIDENCE_REFUSED")
    for name, entry in packet.inventory.items():
        require(not name.endswith((".json", ".jsonl", ".xml")) or entry["bytes"] <= MAX_JSON, "DATA_DOCUMENT_SIZE_LIMIT")
    full = _audit_gate(packet, audit, inspection_path, inspection_hash, code)
    campaign = packet.json(BASE + "campaign_receipt.json")
    require(campaign.get("status") == "CAS_META_2_AWS_CAMPAIGN_COMPLETED" and campaign.get("completed") is True
            and campaign.get("evaluation_completed") is True and campaign.get("smoke_only") is False
            and campaign.get("all_test_cases_evaluated_per_arm") == campaign.get("reference_cases") == 72
            and campaign.get("arm_verdicts") == 360, "FULL_CAMPAIGN_COMPLETION_REQUIRED")
    # Private task reading is deliberately below BOTH successful audit gates.
    tasks, predictions = _test_mapping(packet)
    train = packet.json(BASE + "dataset/train.json")
    validation = packet.json(BASE + "dataset/validation.json")
    dataset_report = validate_dataset({"schema": SCHEMA, "splits": {"train": train, "validation": validation, "test": tasks}})
    evaluation = packet.json(BASE + "evaluation_results.json")
    rows = _case_rows(packet, tasks, predictions, full, evaluation)
    totals = {arm: arm_totals(rows, arm) for arm in ARMS}
    require(set(evaluation["results"]) == set(campaign["results"]) == set(full["metrics"]) == set(ARMS), "AGGREGATE_ARM_COVERAGE_INVALID")
    for arm in ARMS:
        saved = evaluation["results"][arm]
        require(saved == campaign["results"][arm], "CAMPAIGN_AGGREGATE_COPY_MISMATCH")
        for key in ("total", *VERDICT_FIELDS, "native_runs", "reserved_policy_units"):
            require(type(saved[key]) is int and saved[key] == totals[arm][key] == full["metrics"][arm][key], "RECOUNT_DIFFERS_FROM_AUDITED_METRIC:" + key)
        require(saved["model_rejections"] == totals[arm]["model_rejections"] == full["metrics"][arm]["model_rejection"]
                and saved["task_accuracy"] == totals[arm]["task_accuracy"]
                and saved["native_executed"] == totals[arm]["native_admitted"]
                and saved["all_cases_in_denominator"] is True
                and saved["repair_required_total"] == 0 and saved["repair_success"] is None,
                "AGGREGATE_BOUNDARY_OR_COUNTS_MISMATCH")
        require(math.isclose(_seconds(saved["worker_wall_seconds"]), totals[arm]["worker_wall_seconds"], rel_tol=1e-12, abs_tol=1e-9), "WORKER_TIME_RECOUNT_MISMATCH")
    comparisons = [paired(rows, *pair) for pair in PAIRS]
    gains = {family: (totals[family + "_trained"]["task_correct"] - totals[family + "_untrained"]["task_correct"]) / 72
             for family in ("cas", "generic")}
    for family in gains:
        require(math.isclose(campaign[family + "_task_accuracy_gain"], gains[family], abs_tol=1e-15), "LEARNING_GAIN_RECOUNT_MISMATCH")
    depths = {}
    for depth in sorted({row["target_depth_including_entry"] for row in rows}):
        subset = [row for row in rows if row["target_depth_including_entry"] == depth]
        depths[str(depth)] = {"total": len(subset), "arms": {arm: arm_totals(subset, arm) for arm in ARMS},
                              "paired_comparisons": [paired(subset, *pair) for pair in PAIRS]}
    rejection_counts = {}
    for arm in ARMS:
        rejected = [row["arms"][arm]["rejection"] for row in rows if row["arms"][arm]["model_rejection"]]
        rejection_counts[arm] = {"total": len(rejected), **{name: dict(sorted(Counter(row[key] for row in rejected).items()))
            for name, key in (("by_stage", "stage"), ("by_category", "category"), ("exact_reasons", "reason"))}}
    seal = packet.json(BASE + "predictions_seal.json")
    prediction_times = seal["selection_timing"]
    require(set(prediction_times) == set(ARMS), "PREDICTION_TIMING_COVERAGE_MISMATCH")
    for value in prediction_times.values():
        _seconds(value["wall_seconds"])
    training = _training(packet, campaign)
    provider_cost, launch_binding = _launch_cost(launch_receipt, packet)
    summary = {"schema": "cas-meta2-postrun-learning-summary/1", "status": "CAS_META_2_LEARNING_SUMMARY_VERIFIED",
        "completed": True, "evidence": {"source_sha": packet.inspection["source_sha"], "job": packet.inspection["job"],
            "packet_sha256": packet.inspection["packet_sha256"], "inspection_receipt_sha256": inspection_hash,
            "stored_audit_receipt_sha256": audit_hash, "full_member_index_sha256": packet.index_hash,
            "member_files_rehashed": len(packet.inventory), "analysis_code_sha256": code},
        "arms": totals, "paired_comparisons": comparisons,
        "learning_gains": {"cas_accuracy_gain": gains["cas"], "generic_accuracy_gain": gains["generic"],
            "cas_minus_generic_gain": gains["cas"] - gains["generic"],
            "cas_improved_on_these_tasks": gains["cas"] > 0, "generic_improved_on_these_tasks": gains["generic"] > 0},
        "depth_results": depths, "curriculum": dataset_report,
        "depth_boundary": "Depth includes the entry frame. All test graphs and wording are unseen; greater depth is not an isolated intervention.",
        "rejections": rejection_counts, "training": training,
        "compute": {"environment": packet.json(BASE + "environment.json"), "prediction_timing": prediction_times,
            "campaign_wall_seconds": _seconds(campaign["wall_seconds"]), "workers": campaign["workers"],
            "reference_worker_wall_seconds": sum(row["reference_wall_seconds"] for row in rows),
            "all_case_worker_wall_seconds": sum(row["case_wall_seconds"] for row in rows), "provider_cost": provider_cost,
            "boundary": "Worker times overlap across eight processes and are not total GPU time. Reserved policy units are not FLOPs. "
                        "No training peak-memory or per-arm dollar cost is inferred."},
        "metric_definitions": {"procedure_correct": "Expanded call-tree, RUN order, dependencies and selected return match; names are ignored. "
                "This does not require identical procedure-definition reuse or establish general semantic equivalence.",
            "exact_program_correct": "Canonical complete IR equality, including declared names and scopes.",
            "actual_output_correct": "All recorded intermediate rows and final output bytes match the private native reference, not merely the final answer.",
            "task_correct": "Procedure, binding, dependencies, intermediate/final outputs and trace validity all pass.",
            "decoded_binding_correct": "Binding match among syntax-valid actions; rejects stay in the denominator.",
            "uncertainty": "Descriptive paired counts from one training seed; no population or CAS-superiority significance claim."},
        "repair": {"required": 0, "success": None, "status": "NOT_EXERCISED"},
        "neural_execution_performed": False, "checkpoint_loading_performed": False,
        "native_reexecution_performed": False, "boundary": BOUNDARY}
    # Final immutable-input checks precede all output creation.
    packet.verify_all()
    require(file_hash(inspection_path) == inspection_hash and file_hash(audit_path) == audit_hash
            and _code_hashes() == code, "SUMMARY_INPUT_CHANGED_DURING_ANALYSIS")
    if launch_binding:
        require(file_hash(launch_binding[0]) == launch_binding[1], "LAUNCH_RECEIPT_CHANGED_DURING_ANALYSIS")
    _plain_path(output)
    case_bytes = canonical({"schema": "cas-meta2-postrun-case-comparisons/1", "cases": rows}) + b"\n"
    summary["case_comparisons_sha256"] = sha256(case_bytes).hexdigest()
    summary["utc"] = datetime.now(timezone.utc).isoformat()
    summary["summary_body_sha256"] = sha256(canonical(summary)).hexdigest()
    output.mkdir(parents=True, exist_ok=False)
    with (output / "case_comparisons.json").open("xb") as stream:
        stream.write(case_bytes)
    with (output / "learning_summary.json").open("xb") as stream:
        stream.write(canonical(summary) + b"\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspection-receipt", type=Path, required=True)
    parser.add_argument("--stored-audit-receipt", type=Path, required=True)
    parser.add_argument("--launch-receipt", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        summary = summarize(arguments.inspection_receipt, arguments.stored_audit_receipt,
                            output=arguments.output, launch_receipt=arguments.launch_receipt)
    except Exception as error:
        print(json.dumps({"status": "CAS_META_2_LEARNING_SUMMARY_REJECTED",
                          "reason": type(error).__name__ + ":" + str(error)}))
        raise SystemExit(2)
    print(json.dumps({"status": summary["status"], "source_sha": summary["evidence"]["source_sha"],
                      "learning_gains": summary["learning_gains"], "neural_execution_performed": False}))


if __name__ == "__main__":
    main()
