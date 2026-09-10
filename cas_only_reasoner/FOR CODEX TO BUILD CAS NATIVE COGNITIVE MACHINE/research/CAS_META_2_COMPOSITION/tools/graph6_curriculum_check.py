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
        "final_panel": {
            "schema": panel["schema"],
            "panel_seed": panel["panel_seed"],
            "family_count": panel["family_count"],
            "case_count": panel["case_count"],
            "cases_per_op": panel["cases_per_op"],
            "reach_label_counts": panel["reach_label_counts"],
            "distinct_shape_patterns": panel["distinct_shape_patterns"],
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
