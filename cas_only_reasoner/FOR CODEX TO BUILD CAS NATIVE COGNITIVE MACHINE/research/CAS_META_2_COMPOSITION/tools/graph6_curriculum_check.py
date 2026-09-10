"""Deterministic evidence for GRAPH6_CURRICULUM_002 (no neural work, no GPU).

Reports, with exact numbers:
  * the varied curriculum audit (30 records, 10 per operation, mistake kinds,
    equal-length options, reach and shared-part coverage, exposure at 64 and 256
    updates);
  * the untouched final panel audit (30 families / 90 cases, reach 10/10/10,
    exclusions by id AND signature against teaching, the examined panel and the
    varied curriculum);
  * the registered decision rules and the declared budget.
"""
from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cas_meta2.graph_teaching import (curriculum, curriculum_experiment,  # noqa: E402
                                      final_panel, fresh_panel)


def canonical(value):
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True,
                      allow_nan=False) + "\n"


def graph_pattern_key(record):
    """Label-invariant key of the ARRANGEMENT only (no question, no options)."""
    node_ids = fresh_panel._structural_ids(record)
    edges = sorted((relation["kind"], node_ids[relation["source"]],
                    node_ids[relation["target"]])
                   for relation in record["graph"]["relations"])
    return (tuple(sorted(node_ids.values())), tuple(edges))


def frozen_generator_supply(probes=fresh_panel.MAX_FAMILY_PROBES):
    """How much supply the FROZEN lesson generator has, by operation and scope.

    Two scopes are reported, because they answer different questions:

    * `teaching_only` — only the teaching dataset (seed 20260909) is excluded.
      This is the scope in which the examined panel itself was built.
    * `teaching_and_examined_panel` — the examined 90-case panel (seed 20260920)
      is excluded as well. This is the scope that matters for an UNTOUCHED panel.

    For each scope: how many families exist, how many have every record unused,
    how many have all three SELECTED cases unused, and how many distinct graph
    patterns sit behind the eligible questions. That last number separates "new
    examples of familiar arrangements" from "previously unseen arrangements".
    """
    scopes = {
        "teaching_only": fresh_panel.used_index(),
        "teaching_and_examined_panel": fresh_panel.used_index(
            fresh_panel.EXCLUDED_DATASET_SEEDS, fresh_panel.EXAMINED_PANEL_SEEDS),
    }
    report = {}
    for scope_name, (used_ids, used_signatures) in scopes.items():
        per_op = {op: {"distinct": set(), "eligible": set()} for op in fresh_panel.PANEL_OPS}
        eligible_patterns = {op: set() for op in fresh_panel.PANEL_OPS}
        families = families_all_new = families_all_records_new = families_any_new = 0
        for probe in range(1, probes + 1):
            family_seed = (fresh_panel.PANEL_FAMILY_BASE
                           + fresh_panel.PANEL_SEED % 1000 + probe)
            by_op = fresh_panel._family_records(family_seed)
            if set(by_op) != set(fresh_panel.PANEL_OPS):
                continue
            families += 1
            if not any(fresh_panel.signature_key(record) in used_signatures
                       for records in by_op.values() for record in records):
                families_all_records_new += 1
            selected = [fresh_panel._select_case(op, by_op[op], family_seed)
                        for op in fresh_panel.PANEL_OPS]
            new_cases = 0
            for record in selected:
                key = fresh_panel.signature_key(record)
                per_op[record["op"]]["distinct"].add(key)
                if key not in used_signatures:
                    per_op[record["op"]]["eligible"].add(key)
                    eligible_patterns[record["op"]].add(graph_pattern_key(record))
                    new_cases += 1
            families_any_new += int(new_cases > 0)
            families_all_new += int(new_cases == len(fresh_panel.PANEL_OPS))
        report[scope_name] = {
            "excluded_case_ids": len(used_ids),
            "excluded_signatures": len(used_signatures),
            "families_searched": families,
            "families_whose_every_record_is_unused": families_all_records_new,
            "families_with_at_least_one_unused_selected_case": families_any_new,
            "families_with_all_three_selected_cases_unused": families_all_new,
            "per_operation": {
                op: {"distinct_signatures": len(per_op[op]["distinct"]),
                     "eligible_signatures": len(per_op[op]["eligible"]),
                     "distinct_ARRANGEMENTS_among_eligible":
                         len(eligible_patterns[op])}
                for op in fresh_panel.PANEL_OPS},
        }
    return {
        "searched_family_seed_region": [
            fresh_panel.PANEL_FAMILY_BASE + fresh_panel.PANEL_SEED % 1000 + 1,
            fresh_panel.PANEL_FAMILY_BASE + fresh_panel.PANEL_SEED % 1000 + probes],
        "scopes": report,
        "narrowed_finding": (
            "Narrowed to what is demonstrated: (1) excluding only the teaching "
            "set, the frozen generator still supplies new INSTANCES (many "
            "families, but only a handful of distinct graph patterns behind the "
            "eligible questions); (2) excluding the teaching set AND the examined "
            "panel, it supplies no family whose every record is unused, and the "
            "eligible questions per operation fall to the counts in "
            "scopes.teaching_and_examined_panel. The frozen generator therefore "
            "cannot supply an untouched panel of previously unseen arrangements; "
            "it can supply new instances of familiar ones."),
    }


def build_report():
    varied = curriculum.varied_records()
    control = curriculum.control_records()
    panel = final_panel.build_final_panel()
    used_ids, used_signatures = fresh_panel.used_index(
        panel["excluded_dataset_seeds"], tuple(panel["excluded_panels"]),
        tuple(panel["excluded_curriculum_seeds"]))
    panel_ids = {case["record_id"] for case in panel["cases"]}
    panel_signatures = {case["signature"] for case in panel["cases"]}
    return {
        "schema": "cas-graph-training-curriculum-check/1",
        "neural_work": False,
        "gpu_used": False,
        "varied_curriculum": curriculum.curriculum_report(varied),
        "control_curriculum": {
            "records": len(control),
            "records_per_op": {op: sum(1 for record in control if record["op"] == op)
                               for op in curriculum.OPS},
            "identity": curriculum.curriculum_identity(control),
            "exposure_at_256_updates": curriculum.exposure(control, 256),
            "unchanged": True,
        },
        "frozen_generator_supply": frozen_generator_supply(),
        "final_panel": {
            "schema": panel["schema"],
            "panel_seed": panel["panel_seed"],
            "family_count": panel["family_count"],
            "case_count": panel["case_count"],
            "cases_per_op": panel["cases_per_op"],
            "reach_label_counts": panel["reach_label_counts"],
            "distinct_patterns": panel["distinct_patterns"],
            "pattern_pool_size": panel["pattern_pool_size"],
            "distinct_family_patterns": panel["distinct_family_patterns"],
            "distinct_case_patterns": panel["distinct_case_patterns"],
            "rejected": panel["rejected"],
            "excluded_dataset_seeds": panel["excluded_dataset_seeds"],
            "excluded_panels": panel["excluded_panels"],
            "excluded_curriculum_seeds": panel["excluded_curriculum_seeds"],
            "excluded_case_ids": panel["excluded_case_ids"],
            "excluded_signatures": panel["excluded_signatures"],
            "overlap_with_used_ids": sorted(panel_ids & used_ids),
            "overlap_with_used_signatures": sorted(panel_signatures & used_signatures),
            "panel_content_digest": final_panel.final_panel_digest(panel),
            "difficulty_vs_teaching": final_panel.difficulty_report(panel),
            "family_seeds": [family["family_seed"] for family in panel["families"]],
            "case_ids": [case["record_id"] for case in panel["cases"]],
        },
        "examined_panel_reproducibility": {
            "panel_seed": fresh_panel.PANEL_SEED,
            "content_digest": fresh_panel.panel_digest(fresh_panel.build_panel()),
            "expected_content_digest":
                "d1076de3ae310562e97552c4f854fab10661bed78f9d4108187ea2f549ae8209",
        },
        "design": {
            "conditions": list(curriculum_experiment.CONDITIONS),
            "pair_seeds": list(curriculum_experiment.PAIR_SEEDS),
            "checkpoints": list(curriculum_experiment.CHECKPOINTS),
            "updates_per_learner": curriculum_experiment.UPDATES_PER_LEARNER,
            "learners": curriculum_experiment.LEARNER_COUNT,
            "total_optimizer_steps": curriculum_experiment.TOTAL_UPDATES,
            "curriculum_margin": curriculum_experiment.CURRICULUM_MARGIN,
            "transfer_level": curriculum_experiment.TRANSFER_LEVEL,
            "repetition_margin": curriculum_experiment.REPETITION_MARGIN,
            "min_seeds": curriculum_experiment.MIN_SEEDS,
            "bootstrap_resamples": curriculum_experiment.BOOTSTRAP_RESAMPLES,
            "bootstrap_seed": curriculum_experiment.BOOTSTRAP_SEED,
            "max_wall_seconds_per_learner":
                curriculum_experiment.MAX_WALL_SECONDS_PER_LEARNER,
        },
        "boundary": ("preparation evidence only: no training, no checkpoint "
                     "selection, no tokenizer fitting, no answer exposure"),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output")
    arguments = parser.parse_args(argv)
    raw = canonical(build_report()).encode("utf-8")
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
