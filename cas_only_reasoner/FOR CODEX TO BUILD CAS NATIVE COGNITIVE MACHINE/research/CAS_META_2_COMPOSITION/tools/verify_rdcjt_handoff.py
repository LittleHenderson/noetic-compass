"""Read local RDCJT evidence and print JSON; no provider or model imports.

Checkpoint files are streamed only as opaque bytes for SHA-256. No checkpoint
is deserialized, no neural computation occurs, and this program writes no files.
The three source functions exercised below are individually pinned to reviewed,
read-only bodies, so importing a launcher cannot trigger its dependencies.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path


RUNS = (
    (20260912, "20260912152001-abf38e1e", "rescued_evidence"),
    (20260913, "20260913183000-d27a44e4", "collected"),
    (20260914, "20260913184000-d27a44e4", "collected"),
)
REVIEWED_FUNCTION_HASHES = {
    "seeds_already_used": "879935cc4f857b9289939a87e4b4903dc6303d217f6461def19f4116826f5754",
    "require_unused_seed": "bde75ea790033ed7e5be7755dc2c1eb554459b97199f1386fc2924f12a91c1ae",
    "replication_status": "c1a6f704fd25e4225aba4318d5d32c2b1fdd86534fe7afec338ca70450cd8ce5",
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    return json.loads(path.read_bytes())


def verify_run(root, seed, suffix, evidence_folder):
    receipt = root / "records/recurrent_cjt_001" / ("receipt_cas-meta2-rdcjt-" + suffix)
    results = receipt / evidence_folder / "results"
    artifacts = results / "artifacts"
    checks, hashes = {}, {}

    def check(name, condition):
        checks[name] = bool(condition)

    def remember(path):
        actual = sha256(path)
        hashes[path.relative_to(root).as_posix()] = actual
        return actual

    def sidecar(path):
        expected = path.with_name(path.name + ".sha256").read_text().strip()
        check(path.relative_to(receipt).as_posix() + ":sidecar", remember(path) == expected)

    intent = read_json(receipt / "intent.json")
    lifecycle = read_json(receipt / "result.json")
    report = read_json(results / "result.json")
    manifest = read_json(artifacts / "manifest.json")
    sweep = read_json(artifacts / "depth_sweep.json")
    experiment = read_json(artifacts / "experiment.json")
    for path in (receipt / "intent.json", receipt / "result.json", artifacts / "manifest.json"):
        remember(path)
    sidecar(results / "result.json")
    sidecar(receipt / "curriculum_result.json")
    check("archive_matches_intent", remember(receipt / "source.zip") == intent["authority"]["archive_sha256"])
    check("seed_binding", intent["authority"]["seed"] == experiment["plan"]["seed"] == seed)
    check("job_binding", all(document["job"] == intent["authority"]["job"]
                              for document in (lifecycle, report, manifest, sweep, experiment)))
    check("delivered_measurement", report["status"] == "RECURRENT_EXPERIMENT_DELIVERED")
    check("matched_initial_weights", report["matched_initial_weights"] is True
          and experiment["matched_initial_weights"] is True)
    expected_names = {"checkpoint_one_pass.pt", "checkpoint_recurrent.pt", "depth_sweep.json", "experiment.json"}
    check("manifest_names", len(manifest["artifacts"]) == len(expected_names)
          and {entry["name"] for entry in manifest["artifacts"]} == expected_names)
    for entry in manifest["artifacts"]:
        name = entry["name"]
        if name not in expected_names:
            check("unsafe_or_unexpected_artifact_name", False)
            continue
        path = artifacts / name
        check("manifest_artifact:" + name,
              remember(path) == entry["sha256"] and path.stat().st_size == entry["bytes"])
    # Older rescued summaries list artifact names; their separate manifest carries hashes.
    if evidence_folder == "collected":
        summary = read_json(receipt / "curriculum_result.json")
        check("collected_summary_equal", summary == report)
        check("summary_manifest_equal", report["artifacts"] == manifest["artifacts"])
        check("lifecycle_completed", lifecycle["completed_deliverable"] is True)
        check("lifecycle_status", lifecycle["status"] == "AWS_CANDIDATE_FINISHED")
        for key, expected in (("measurement_collection", "COMPLETE_VERIFIED"),
                              ("checkpoint_collection", "COMPLETE_VERIFIED"),
                              ("compute_cleanup", "COMPLETE")):
            check("recorded_stage:" + key, lifecycle["stages"][key] == expected)
        check("recorded_no_missing_objects", lifecycle["stages"]["missing_required_objects"] == [])
    else:
        check("rescued_artifact_names", set(report["artifacts"]) == expected_names)
        check("rescued_manifest_bound_to_result", report["artifact_manifest"] == manifest["artifacts"])
        check("rescue_original_failure_retained", lifecycle["completed_deliverable"] is False)

    for arm, expected in (("one_pass", (128, 896, 1.0)), ("recurrent", (128, 3360, 3.75))):
        accounting = report["arms"][arm]["accounting"]
        check("accounting:" + arm, tuple(accounting[key] for key in
              ("optimizer_updates", "sample_level_core_passes", "mean_depth")) == expected)
    check("trainable_parameters", report["trainable_parameters_by_arm"] == {"one_pass": 3, "recurrent": 3})
    check("panel_record", report["panel"]["panel_item_count"] == 216
          and report["panel"]["examined_during_teaching"] is False)

    inner = sweep["depth_sweep"]
    comparison = report["sweep_comparison"]
    check("comparison_same_in_payload", sweep["sweep_comparison"] == comparison)
    check("depth_labels", set(inner["rows"]) == {"R1", "R2", "R4", "R8", "RESET_8"})
    check("weights_unchanged", inner["weights_unchanged"] is True
          and inner["parameter_digest_before"] == inner["parameter_digest_after"])
    maps = {}
    for label, rows in inner["rows"].items():
        maps[label] = {row["item_id"]: row for row in rows}
        check("unique_panel_items:" + label, len(maps[label]) == len(rows) == 216)
        check("answer_flags:" + label, all(type(row["is_correct"]) is bool
              and row["is_correct"] == (row["selected_answer"] == row["expected_answer"])
              for row in rows))
    baseline = maps["R1"]
    counts = {label: sum(row["is_correct"] for row in rows.values()) for label, rows in maps.items()}
    computed = {}
    for label in ("R2", "R4", "R8"):
        current = maps[label]
        check("same_panel_items:" + label, set(current) == set(baseline))
        check("same_expected_answers:" + label, all(current[key]["expected_answer"] == baseline[key]["expected_answer"] for key in baseline))
        gained = sorted(key for key in baseline if current[key]["is_correct"] and not baseline[key]["is_correct"])
        lost = sorted(key for key in baseline if baseline[key]["is_correct"] and not current[key]["is_correct"])
        value = comparison["per_depth"][label]
        net = counts[label] - counts["R1"]
        check("row_recomputed_tally:" + label,
              gained == sorted(value["gained"]) and lost == sorted(value["lost"])
              and len(gained) == value["gained_count"] and len(lost) == value["lost_count"]
              and net == value["net"] == len(gained) - len(lost))
        computed[label] = {"correct": counts[label], "gained": len(gained), "lost": len(lost), "net": net}
    check("primary_result", comparison["baseline_label"] == "R1" and comparison["primary_label"] == "R8"
          and comparison["baseline_correct"] == counts["R1"] and comparison["primary_correct"] == counts["R8"]
          and comparison["net"] == computed["R8"]["net"])
    check("reset_answers", set(maps["RESET_8"]) == set(baseline)
          and all(row["selected_answer"] == maps["RESET_8"][key]["selected_answer"] for key, row in baseline.items()))
    return {"seed": seed, "receipt": receipt.relative_to(root).as_posix(),
            "evidence_folder": evidence_folder, "lifecycle_completed_deliverable": lifecycle["completed_deliverable"],
            "R1": counts["R1"], "R8": counts["R8"], "R8_minus_R1": computed["R8"]["net"],
            "per_depth_recomputed": computed, "parameter_digest": inner["parameter_digest_before"],
            "checks": checks, "failed_checks": [key for key, ok in checks.items() if not ok],
            "file_sha256": hashes, "all_passed": all(checks.values())}


def verify_guard(root):
    """Run only the pinned read-only function bodies, never the launcher module."""
    source_path = root / "aws/recurrent_cjt_launch.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    functions = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in REVIEWED_FUNCTION_HASHES:
            actual = hashlib.sha256(ast.get_source_segment(source, node).encode()).hexdigest()
            if actual != REVIEWED_FUNCTION_HASHES[node.name]:
                raise ValueError("READ_ONLY_FUNCTION_CHANGED_REVIEW_REQUIRED:" + node.name)
            functions.append(node)
    if len(functions) != len(REVIEWED_FUNCTION_HASHES):
        raise ValueError("READ_ONLY_FUNCTION_MISSING")

    def require(condition, message):
        if not condition:
            raise ValueError(message)

    namespace = {"Path": Path, "json": json, "CANDIDATE": "CAS_RDCJT_001",
                 "FROZEN_SEEDS": tuple(seed for seed, _, _ in RUNS), "require": require}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(source_path), "exec"), namespace)
    record_dir = root / "records/recurrent_cjt_001"
    used = namespace["seeds_already_used"](record_dir)
    decisions = {}
    for seed, _, _ in RUNS:
        try:
            decisions[str(seed)] = {"accepted": True, "result": namespace["require_unused_seed"](seed, record_dir)}
        except ValueError as error:
            decisions[str(seed)] = {"accepted": False, "error": str(error)}
    older = []
    for path in sorted(record_dir.glob("receipt_cas-meta2-rdcjt-20260912*/intent.json")):
        document = read_json(path)
        older.append({"receipt": path.parent.name, "seed": document["authority"]["seed"]})
    return {"source_sha256": sha256(source_path), "reviewed_function_sha256": REVIEWED_FUNCTION_HASHES,
            "used_seeds": sorted(used), "seed_decisions": decisions, "earlier_intents": older,
            "rescued_seed_missing_from_guard": 20260912 not in used,
            "three_pair_count_helper": namespace["replication_status"](3),
            "note": "The helper's satisfied field checks job count only. It does not evaluate the R8-minus-R1 criterion."}


def verify_preservation(root):
    record = root / "records/rdcjt_handoff_20260916"
    manifest = read_json(record / "preservation_manifest.json")
    results = []
    for entry in manifest["files"]:
        copied = record / entry["preserved_path"]
        results.append({"name": entry["name"], "sha256_matches": sha256(copied) == entry["sha256"],
                        "size_matches": copied.stat().st_size == entry["bytes"]})
    return {"files": results, "all_passed": all(row["sha256_matches"] and row["size_matches"] for row in results)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    runs = [verify_run(root, *run) for run in RUNS]
    guard = verify_guard(root)
    preserved = verify_preservation(root)
    valid = all(run["all_passed"] for run in runs)
    positive = sum(run["R8_minus_R1"] > 0 for run in runs)
    report = {"schema": "cas.rdcjt-local-handoff-verification/1", "runs": runs,
              "preservation": preserved, "seed_guard": guard,
              "criterion": {"text": "a positive R8-minus-R1 difference in at least two of three paired runs",
                            "verified_distinct_seeds": len({run["seed"] for run in runs if run["all_passed"]}),
                            "positive_runs": positive, "required_positive_runs": 2,
                            "status": ("NOT_MET" if positive < 2 else "MET") if valid else "NOT_EVALUATED_INVALID_EVIDENCE"},
              "all_integrity_checks_passed": valid and preserved["all_passed"],
              "boundary": "Local byte and JSON consistency verification only. Provider state and billing were not queried. Checkpoints were hashed as opaque bytes, never loaded. No neural work, launch, reservation, repair, or source mutation occurred. Unexamined panel flags do not prove structurally novel families. No general reasoning, CAS advantage, CNCM completion, or production readiness is established."}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["all_integrity_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
