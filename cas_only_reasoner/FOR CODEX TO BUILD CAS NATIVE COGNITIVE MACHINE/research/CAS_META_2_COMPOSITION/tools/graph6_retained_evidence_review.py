"""Read-only review of what the RETAINED evidence can answer.

Owner-directed (2026-09-10). Before spending anything more, this tool establishes
which of the questions we care about can be answered from what attempt 004 already
delivered, and which were never measured. It performs NO neural execution: it
reads the delivered result, the delivered checkpoints' METADATA, and the
deterministic curriculum/panel definitions from source.

Questions examined:
  * which per-case evidence is retained (and which fields are absent);
  * which practice/own-curriculum cases each learner answered correctly;
  * for the varied learners: accuracy grouped by the variation kind each lesson
    was built with (consistent renaming, harmless reordering, answer-changing
    rewiring) and by LIST_PARTS distractor profile;
  * the fresh panel by operation and by reach label;
  * an explicit MISSING list: the trained-learner rename / reorder / rewire
    contrasts on correctly answered practice cases, per-option scores, the
    intermediate training history, and any component that was never saved.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cas_meta2.graph_teaching import curriculum, final_panel  # noqa: E402

SCHEMA = "cas-graph-training-retained-evidence-review/1"

MISSING = (
    "predicted option strings for the practice and own-curriculum passes "
    "(only record_id/op/correct were stored), so the rename / reorder / rewire "
    "contrasts on correctly answered practice cases cannot be recovered from the "
    "delivered result",
    "any trained-learner contrast between a practice case and its renamed, "
    "reordered or rewired variant: those forward passes were never run",
    "per-option scores or logits: only the argmax was stored",
    "the intermediate training history between the saved endpoints (0, 64, 256)",
    "any component that was never written to a checkpoint (for example the other "
    "operation modules a RegisteredOperationBank constructs alongside decompose)",
    "the tokenizer artifact itself: only its vocabulary list is inside each checkpoint",
)


def load_result(path):
    return json.loads(Path(path).read_bytes())


def correctness_index(block):
    """record_id -> correct flag, from a practice/own/fresh evaluation block."""
    return {row["record_id"]: bool(row["correct"]) for row in block["results"]}


def practise_index(block):
    return {row["record_id"]: bool(row["correct"]) for row in block["predictions"]}


def build_report(result_path, checkpoint_metadata_path=None):
    result = load_result(result_path)
    varied_records = {record["record_id"]: record for record in curriculum.varied_records()}
    control_records = {record["record_id"]: record
                       for record in curriculum.control_records()}
    panel = final_panel.build_final_panel()
    panel_meta = {case["record_id"]: case for case in panel["cases"]}

    learners = []
    variation_totals = defaultdict(lambda: {"attempted": 0, "correct": 0})
    profile_totals = defaultdict(lambda: {"attempted": 0, "correct": 0})
    fresh_by_op = defaultdict(lambda: {"attempted": 0, "correct": 0})
    fresh_by_reach = defaultdict(lambda: {"attempted": 0, "correct": 0})
    for learner in result["learners"]:
        condition = learner["condition"]
        own_before = practise_index(learner["own_curriculum"]["before"])
        own_after = practise_index(learner["own_curriculum"]["after_256"])
        practice_before = practise_index(learner["practice"]["before"])
        practice_after = practise_index(learner["practice"]["after_256"])
        fresh_after = correctness_index(learner["fresh"]["after_256"])
        library = varied_records if condition == "varied" else control_records
        per_kind = defaultdict(lambda: {"attempted": 0, "correct": 0})
        per_profile = defaultdict(lambda: {"attempted": 0, "correct": 0})
        for record_id, correct in own_after.items():
            record = library.get(record_id)
            if record is None:
                continue
            variation = record.get("variation") or {}
            kind = variation.get("kind", "none")
            per_kind[kind]["attempted"] += 1
            per_kind[kind]["correct"] += int(correct)
            variation_totals[kind]["attempted"] += 1
            variation_totals[kind]["correct"] += int(correct)
            if record["op"] == "LIST_PARTS" and "profile" in variation:
                per_profile[variation["profile"]]["attempted"] += 1
                per_profile[variation["profile"]]["correct"] += int(correct)
                profile_totals[variation["profile"]]["attempted"] += 1
                profile_totals[variation["profile"]]["correct"] += int(correct)
        for record_id, correct in fresh_after.items():
            case = panel_meta.get(record_id)
            if case is None:
                continue
            fresh_by_op[case["op"]]["attempted"] += 1
            fresh_by_op[case["op"]]["correct"] += int(correct)
            if case["op"] == "REACHED_VIA":
                label = case["record"]["correct"].split(":")[0]
                fresh_by_reach[label]["attempted"] += 1
                fresh_by_reach[label]["correct"] += int(correct)
        learners.append({
            "condition": condition,
            "learner_seed": learner["learner_seed"],
            "own_curriculum_correct_by_variation_kind": {kind: dict(stats)
                                                         for kind, stats in sorted(per_kind.items())},
            "own_curriculum_list_profiles": {name: dict(stats)
                                             for name, stats in sorted(per_profile.items())},
            "practice_cases_correct_before_vs_after": {
                "before": sum(1 for value in practice_before.values() if value),
                "after_256": sum(1 for value in practice_after.values() if value),
                "attempted": len(practice_after)},
            "own_cases_correct_before_vs_after": {
                "before": sum(1 for value in own_before.values() if value),
                "after_256": sum(1 for value in own_after.values() if value),
                "attempted": len(own_after)},
            "fresh_correct_after_256": {
                "correct": sum(1 for value in fresh_after.values() if value),
                "attempted": len(fresh_after)},
        })

    def as_rates(table):
        return {key: {"attempted": value["attempted"], "correct": value["correct"],
                      "rate": (value["correct"] / value["attempted"]
                               if value["attempted"] else None)}
                for key, value in sorted(table.items())}

    report = {
        "schema": SCHEMA,
        "neural_work": False,
        "gpu_used": False,
        "result_path": str(result_path),
        "panel_denominator": {
            "cases": panel["case_count"],
            "graph_arrangements": panel["family_count"],
            "note": ("90 questions drawn from 30 distinct graph arrangements; the "
                     "same panel was used by every learner, so pooled scores are "
                     "repeated evaluations of one panel, not independent graphs")},
        "variation_kinds_pooled_own_curriculum": as_rates(variation_totals),
        "list_profiles_pooled_own_curriculum": as_rates(profile_totals),
        "fresh_panel_pooled_by_operation": as_rates(fresh_by_op),
        "fresh_panel_pooled_reach_labels": as_rates(fresh_by_reach),
        "learners": learners,
        "retained_per_case_fields": {
            "fresh": sorted(result["learners"][0]["fresh"]["after_256"]["results"][0]),
            "practice_and_own": sorted(result["learners"][0]["own_curriculum"]["after_256"]
                                       ["predictions"][0]),
        },
        "missing_measurements": list(MISSING),
        "boundary": ("read-only: no training, no checkpoint tensors loaded, no "
                     "provider call, no reservation"),
    }
    if checkpoint_metadata_path and Path(checkpoint_metadata_path).is_file():
        report["checkpoint_metadata"] = json.loads(
            Path(checkpoint_metadata_path).read_bytes())
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", required=True)
    parser.add_argument("--checkpoint-metadata")
    parser.add_argument("--output")
    arguments = parser.parse_args(argv)
    report = build_report(arguments.result, arguments.checkpoint_metadata)
    raw = (json.dumps(report, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if arguments.output:
        path = Path(arguments.output).absolute()
        if not path.exists():
            with path.open("xb") as stream:
                stream.write(raw)
    sys.stdout.write(raw.decode("utf-8"))
    sys.stdout.write("sha256: %s\n" % sha256(raw).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
