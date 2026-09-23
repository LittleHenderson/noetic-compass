"""Recheck and classify EXISTING Q4 results; imports no neural model or torch.

RT1 has a uniform output histogram, not 256 original per-row prediction receipts.
Rows below are explicit derivations from that histogram and the pinned ordering.
"""
import argparse
import json
from pathlib import Path
import random
import subprocess
import sys

CNCM = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(CNCM / "research/helm_cas_expression_lab"))
import q4_panel_evaluation as q
from q3_load import load_split

REVIEW_COMMIT = "26f1b46515c960a7aed6023f370df95d591ca36a"
REL = "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    manifest = q.read(args.manifest)
    q.validate_manifest(manifest, args.manifest_sha256)
    evidence = Path(args.review_root) / REL / "records/helm_why_review_20260922/evidence"
    paths = [evidence / p for p in ("RT1/rt1_results.json", "RT1/rt1_diag.py", "RT1/PREREG_RT1.txt",
                                   "RT2/rt2_results.json", "RT7/rt7_results.json")]
    for path in paths:
        relative = path.relative_to(Path(args.review_root)).as_posix()
        committed = subprocess.check_output(["git", "-C", args.review_root, "show", REVIEW_COMMIT + ":" + relative])
        if committed.replace(b"\r\n", b"\n") != path.read_bytes().replace(b"\r\n", b"\n"):
            raise q.PanelError("REVIEW_COMMITTED_EVIDENCE_MISMATCH")
    rt1 = q.read(paths[0])
    assert rt1["label"] == "DIAGNOSTIC_NOT_CLAIM_BEARING"
    assert rt1["step0"]["reproduced"] == rt1["step0"]["of"] == 16
    run = Path(manifest["historical_run"])
    plan = q.read(run / "plan.json")
    train = load_split(Path(plan["data_dir"]), "G", "train")
    order = list(range(len(train)))
    random.Random(plan["seed"]).shuffle(order)
    seen, unseen = order[:128], order[128:256]
    assert seen == manifest["consumed_training_positions"]
    exposed_shapes = {q.shape_key(train[i][1]["target_ast"]) for i in seen}
    exposed_contents = {q.sha(q.canonical(train[i][1]["target_ast"])) for i in seen}
    exposed_observations = {train[i][0]["observation"] for i in seen}
    familiar = [i for i in unseen if q.shape_key(train[i][1]["target_ast"]) in exposed_shapes
                and q.sha(q.canonical(train[i][1]["target_ast"])) not in exposed_contents
                and train[i][0]["observation"] not in exposed_observations]
    derived = {}
    for group, indices in (("seen128", seen), ("unseen128", unseen)):
        recorded = rt1["step3"][group]
        assert recorded["distinct_outputs"] == 1
        assert len(recorded["outputs"]) == 1 and recorded["outputs"][0][1] == len(indices) == 128
        prediction = json.loads(recorded["outputs"][0][0])
        rows = []
        depth_counts = {}
        for i in indices:
            visible, sealed = train[i]
            checks = q.grade(prediction, sealed["target_ast"])
            row = {"training_position": i, "record_id": visible["record_id"], "checks": checks,
                   "familiar_to_actually_consumed_operator_shapes": i in familiar,
                   "custody": "DERIVED_FROM_UNIFORM_SAVED_HISTOGRAM_NOT_ORIGINAL_PER_ROW_PREDICTION_RECEIPT"}
            rows.append(row)
            depth = str(sealed["depth"])
            counts = depth_counts.setdefault(depth, {"n": 0, "generated": 0, "canonical_exact": 0})
            counts["n"] += 1
            counts["generated"] += int(checks["parse_valid"])
            counts["canonical_exact"] += int(checks["canonical_exact"])
        assert depth_counts == recorded["by_depth"]
        derived[group] = {"uniform_recorded_prediction_ast": prediction, "rows": rows}
    original_predictions = [json.loads(line) for line in (run / "dev_predictions.jsonl").read_text().splitlines()]
    by_id = {r["record_id"]: r for r in original_predictions}
    novel = []
    for row in manifest["panels"]["new_structure"]:
        original = by_id[row["visible"]["record_id"]]
        novel.append({"record_id": original["record_id"], "original_prediction": original,
                      "checks": q.grade(original["ast"], row["reference_ast"]),
                      "matched_teaching_pool_size_depth": row["matched_teaching_pool_size_depth"]})
    def metrics(rows):
        return {"n": len(rows), **{key: sum(r["checks"][key] for r in rows)
                for key in ("canonical_exact", "parse_valid", "operator_structure_exact")}}
    familiar_rows = [r for r in derived["unseen128"]["rows"] if r["training_position"] in familiar]
    result = {"schema": "helm.q4-existing-record-panel-reconciliation/0.1",
              "status": "READ_ONLY_DERIVATION_NO_NEW_MODEL_EXECUTION",
              "checkpoint_sha256": q.WEIGHTS_SHA, "historical_source_commit": q.HISTORICAL_SOURCE,
              "complementary_review_commit": REVIEW_COMMIT,
              "sources": [q.file_pin(p, lf=True) for p in paths + [run / "dev_predictions.jsonl", Path(args.manifest), Path(__file__)]],
              "teaching_fit": dict(metrics(derived["seen128"]["rows"]), source="RT1 full consumed128 saved histogram"),
              "new_content_familiar_structure_within_unconsumed_pool": dict(metrics(familiar_rows),
                  source="Derived113-of128 subset of RT1 next unconsumed128; familiar to actual consumed operator shapes"),
              "other_unconsumed_pool_rows": len(unseen) - len(familiar),
              "genuinely_new_structures": dict(metrics(novel), source="Original saved development predictions"),
              "new_structure_matched_size_depth": metrics([r for r in novel if r["matched_teaching_pool_size_depth"]]),
              "new_structure_unmatched_size_depth": metrics([r for r in novel if not r["matched_teaching_pool_size_depth"]]),
              "new_strict_outside_pool_content_panel": {"status": "NOT_EXECUTED_GPU_ADMISSION_REFUSED", "n_prepared": 16},
              "derivation": derived, "genuine_original_development_records": novel,
              "limits": ["RT1 original row-level prediction receipts are unavailable; uniform histograms determine the derived rows",
                         "Exposure identities reconstructed from pinned shuffle and completion, not historically logged per-row IDs",
                         "113 familiar-content rows are inside the unused teaching pool, not the new strict outside-pool panel",
                         "Diagnostics are not independent hidden evaluation or a new Helm certification",
                         "No explanation proves more training or greater capacity is sufficient"]}
    q.write_once(args.output, result)
    print(json.dumps({key: result[key] for key in ("teaching_fit", "new_content_familiar_structure_within_unconsumed_pool",
                                                 "genuinely_new_structures", "new_structure_matched_size_depth",
                                                 "new_structure_unmatched_size_depth")}, indent=2))


if __name__ == "__main__":
    main()
