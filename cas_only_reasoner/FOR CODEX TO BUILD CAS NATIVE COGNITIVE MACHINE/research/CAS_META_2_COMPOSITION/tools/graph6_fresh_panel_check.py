"""Deterministic fresh-panel evidence for GRAPH6_CONFIRMATION_001.

NO neural work, NO GPU, NO training: this tool only builds the pure-Python
lesson datasets and audits the pre-registered fresh panel. It answers, with
exact numbers, the questions the owner's directive turns on:

  * how many families and cases the panel has, and one question per operation;
  * whether any case is a used case or a trivially renamed duplicate of one
    (exact record ids AND label-invariant structural signatures);
  * whether the reach operation is covered across direct / via / absent;
  * how much of the available pattern space the 90 cases cover;
  * what the panel's content digest is, so the paid run can be bound to it.

The tool never trains, never fits the tokenizer, and never exposes an answer.
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

from cas_meta2.graph_teaching import fresh_panel  # noqa: E402


def canonical(value):
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True,
                      allow_nan=False) + "\n"


def build_report():
    panel = fresh_panel.build_panel()
    used_ids, used_signatures = fresh_panel.used_index()
    cases = panel["cases"]
    ids = {case["record_id"] for case in cases}
    signatures = {case["signature"] for case in cases}
    return {
        "schema": "cas-graph-training-graph6-fresh-panel-check/1",
        "neural_work": False,
        "gpu_used": False,
        "panel_seed": panel["panel_seed"],
        "family_count": panel["family_count"],
        "case_count": panel["case_count"],
        "cases_per_op": panel["cases_per_op"],
        "reach_label_counts": panel["reach_label_counts"],
        "distinct_family_patterns": panel["distinct_family_patterns"],
        "distinct_case_patterns": panel["distinct_case_patterns"],
        "candidate_families": panel["candidate_families"],
        "rejected_candidates": panel["rejected"],
        "excluded_dataset_seeds": panel["excluded_dataset_seeds"],
        "excluded_case_ids": len(used_ids),
        "excluded_signatures": len(used_signatures),
        "overlap_with_used_case_ids": sorted(ids & used_ids),
        "overlap_with_used_signatures": sorted(signatures & used_signatures),
        "panel_content_digest": fresh_panel.panel_digest(panel),
        "panel_sha256": sha256(canonical(panel).encode("utf-8")).hexdigest(),
        "family_seeds": [family["family_seed"] for family in panel["families"]],
        "case_ids": [case["record_id"] for case in cases],
        "boundary": panel["boundary"],
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
