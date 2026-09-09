"""Deterministic, pure analysis of a collected ln(3) diagnostic result.

Reads the collected ``ln3_diagnostic_result.json`` (no torch, no model
execution) and prints the measured statistics behind the four bound decision
rules from ``training_mode_001/LN3_DIAGNOSTIC.md``:

  1. equal scores (spread ~ 0) with distinct option vectors -> the fixed
     readout/projection loses the distinction;
  2. near-parallel option vectors (cosine ~ 1) -> projection/pooling erases
     distinctions before the readout;
  3. differing per-target losses with ~0 gradient norms -> the corrective
     signal does not reach the module;
  4. usefully different per-target gradient norms -> the machinery can
     express a preference, and the flat ln(3) pilot points to the small
     allowance or optimization dynamics.

Usage: python tools/graph_training_ln3_result_analysis.py <result.json>
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path


def stats(values):
    values = [float(value) for value in values]
    return {"n": len(values), "min": min(values), "median": statistics.median(values),
            "max": max(values), "mean": statistics.fmean(values)}


def nonzero(values):
    return [value for value in values if abs(value) > 1e-12]


def main(argv=None):
    path = Path(argv[1] if argv and len(argv) > 1 else sys.argv[1]).resolve()
    document = json.loads(path.read_bytes())
    if document.get("schema") != "cas-graph-training-ln3-diagnostic-result/1":
        raise SystemExit("LN3_RESULT_SCHEMA_MISMATCH")
    report = {"path": str(path), "job": document.get("job"),
              "optimizer_steps_taken": document.get("optimizer_steps_taken"),
              "arms": {}}
    for arm in document.get("arms", []):
        name = arm["arm"]
        measurements = arm["report"]
        rows = measurements["scores"]
        spreads = [row["spread"] for row in rows]
        geometry_rows = measurements["option_geometry"]
        pair_cosines = [value for row in geometry_rows
                        for value in row["option_pair_cosines"]]
        problem_option_cosines = [value for row in geometry_rows
                                  for value in row["problem_option_cosines"]]
        gradient_rows = measurements["gradient_test"]
        per_target_losses = {target: [] for target in (0, 1, 2)}
        per_matrix_norms = {}
        for row in gradient_rows:
            for entry in row["results"]:
                per_target_losses[entry["target"]].append(entry["loss"])
                for matrix, norm in entry["gradient_norms"].items():
                    per_matrix_norms.setdefault(matrix, []).append(norm)
        correct_slot_top = sum(
            1 for row in rows
            if row["scores"].index(max(row["scores"])) == row["correct_slot"])
        all_scores = [value for row in rows for value in row["scores"]]
        tie_records = sum(1 for row in rows if row["spread"] == 0.0)
        report["arms"][name] = {
            "checkpoint_unchanged": arm["checkpoint_before"] == arm["checkpoint_after"],
            "records": len(rows),
            "score_spread": stats(spreads),
            "spread_exactly_zero": tie_records,
            "spread_lt_1e-6": sum(1 for value in spreads if value < 1e-6),
            "correct_slot_top1_argmax": correct_slot_top,
            "correct_slot_chance": len(rows) / 3.0,
            "tie_argmax_lands_on_correct": sum(
                1 for row in rows if row["spread"] == 0.0 and row["correct_slot"] == 0),
            "all_score_values": stats(all_scores),
            "option_pair_cosines": stats(pair_cosines),
            "problem_option_cosines": stats(problem_option_cosines),
            "per_target_loss": {target: stats(values)
                                for target, values in per_target_losses.items()},
            "gradient_norms_by_matrix": {matrix: stats(values)
                                         for matrix, values in per_matrix_norms.items()},
            "gradient_norm_max_any": max(
                max(values) for values in per_matrix_norms.values()),
            "gradient_norm_nonzero_fraction": {
                matrix: len(nonzero(values)) / max(1, len(values))
                for matrix, values in per_matrix_norms.items()},
            "gradient_sample": gradient_rows[0] if gradient_rows else None,
            "score_sample": rows[0] if rows else None,
            "geometry_sample": geometry_rows[0] if geometry_rows else None,
        }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
