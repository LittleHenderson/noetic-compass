"""Verify saved Q4 artifacts and replay its dev checker, without model execution."""
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
CN = ROOT.parents[1]
LAB = CN / "research/helm_cas_expression_lab"
sys.path.insert(0, str(LAB))
import q4_smoke_job as job
from q4_checkpoint import verify_checkpoint
from q3_load import load_split


def read_lines(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def inspect():
    run = ROOT / "run_001"
    supervisor = job._read_json(run / "supervisor.json")
    if supervisor["status"] != "COMPLETE" or supervisor["returncode"] != 0:
        raise ValueError("Run did not complete; preserve negative receipts instead")
    plan = job.validate_plan(job._read_json(ROOT / "plan.json"))
    plan_hash = job.digest(job.canonical(plan))
    preparation = job._read_json(ROOT / "preparation.json")
    if preparation["new_plan_canonical_sha256"] != plan_hash or supervisor["plan_sha256"] != plan_hash:
        raise ValueError("Plan binding differs")
    receipt = job._authorization_receipt(plan,
        conversation_authorization=ROOT / "conversation_authorization.json",
        conversation_sha256=preparation["authorization"]["record_sha256"])
    result = job._read_json(run / "result.json")
    if result["authorization"] != receipt or result["plan_sha256"] != plan_hash:
        raise ValueError("Result authorization differs")
    identity = {"source_pins": plan["source_pins"], "data_version": plan["data_version"],
                "manifest_sha256": plan["manifest_sha256"], "contract_digest": plan["contract_digest"],
                "environment": plan["environment"], "plan_sha256": plan_hash, "authorization": receipt}
    checkpoint = verify_checkpoint(run / "checkpoint", expected_identity=identity,
        expected_width=plan["width"], expected_weights_sha256=result["checkpoint_weights_sha256"])
    updates = read_lines(run / "updates.jsonl")
    if ([row["update"] for row in updates] != list(range(1, plan["max_updates"] + 1))
            or result["actual_updates"] != len(updates)
            or any(not math.isfinite(row[key]) for row in updates for key in ("loss", "pre_clip_gradient_norm"))):
        raise ValueError("Update receipt differs or contains nonfinite values")
    predictions = read_lines(run / "dev_predictions.jsonl")
    if len(predictions) != plan["dev_examples"]:
        raise ValueError("Prediction count differs")
    # Post-run deterministic inspection only. These targets never replace predictions.
    pairs = load_split(Path(plan["data_dir"]), "G", "dev")[:plan["dev_examples"]]
    cases, depths = [], {}
    for prediction, (visible, target) in zip(predictions, pairs, strict=True):
        if prediction["record_id"] != visible["record_id"]:
            raise ValueError("Prediction ID differs")
        exact = prediction["ast"] == target["target_ast"]
        score = depths.setdefault(str(target["depth"]), {"n": 0, "generated": 0, "canonical_exact": 0})
        score["n"] += 1
        score["generated"] += prediction["outcome"] == "GENERATED"
        score["canonical_exact"] += exact
        cases.append({"record_id": visible["record_id"], "task": "RECONSTRUCT_VISIBLE_EXPRESSION_AST",
            "input": visible["observation"], "original_learned_prediction": prediction,
            "checker_reference_ast": target["target_ast"], "checker_canonical_exact": exact,
            "checker_origin": "FROZEN_Q3_DEV_REFERENCE_NOT_A_LEARNED_ANSWER",
            "checkpoint_weights_sha256": checkpoint["weights_sha256"],
            "cas_profile": "NOT_ASSIGNED", "cas_ohm_measurement": "NOT_AVAILABLE"})
    if depths != result["dev_by_depth"]:
        raise ValueError("Saved scores differ from deterministic replay")
    telemetry = read_lines(run / "device_monitor.jsonl")
    summary = {"schema": "helm-cas-expression-lab.q4-saved-run-verification/0.1",
        "verified_utc": datetime.now(timezone.utc).isoformat(), "integrity": "PASS",
        "plan_sha256": plan_hash, "source_commit": preparation["source_commit"],
        "checkpoint_weights_sha256": checkpoint["weights_sha256"],
        "actual_updates": len(updates), "prediction_count": len(predictions),
        "exact_count": sum(row["checker_canonical_exact"] for row in cases),
        "outcomes": dict(Counter(row["outcome"] for row in predictions)), "by_depth": depths,
        "elapsed_seconds": supervisor["elapsed_seconds"],
        "maximum_sampled_temperature_c": max(row["sample"]["temperature_c"] for row in telemetry),
        "learned_parameter_count": result["learned_parameter_count"],
        "cuda_peak_allocated_bytes": result["cuda_peak_allocated_bytes"],
        "first_training_loss": updates[0]["loss"], "last_training_loss": updates[-1]["loss"],
        "loss_caveat": "Different training examples; not a fixed-set before/after score",
        "torch_imported": "torch" in sys.modules, "neural_execution_by_inspector": False,
        "fresh_process_neural_reload": "NOT_EXECUTED", "operation_learning": "NOT_EVALUATED",
        "evaluation_custody": "EVALUATION_NOT_INDEPENDENT", "certification": "NOT_CERTIFIED"}
    return summary, cases


if __name__ == "__main__":
    summary, cases = inspect()
    job._write_json(ROOT / "saved_run_verification.json", summary)
    job._write_json(ROOT / "inspected_predictions.json", {"cases": cases})
    print(json.dumps(summary, indent=2))
