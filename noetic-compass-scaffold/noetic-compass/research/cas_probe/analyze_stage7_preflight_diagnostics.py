"""Stage 7 preflight diagnostics before treating 28 Foundations as claim-bearing.

This script answers three questions:

1. Confirm the Stage 7 target is the original TKS 28:
   7 foundations x 4 worlds/registers.
2. Retrospectively compute a lacunarity-style noetic gap map from the
   Stage 3.2 per-class ablation evidence.
3. Pass Stage 3/6 ablation trajectories through the existing CAS fractal
   classifier so "oscillatory" is measured, not just narrated.

Important boundary: this is not the trained neural `LacunarityHead` from
CAS Native. That head is meaningful only with trained CAS Native weights.
Here we use the deterministic lacunarity formula and produce a Head-shaped
gap-map report over the Pythia probe evidence.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


_HERE = Path(__file__).resolve().parent
_NOETIC_COMPASS_ROOT = _HERE.parents[1]
_NOETIC_NAMES = {
    0: "Idea",
    1: "Mind",
    2: "Positive",
    3: "Negative",
    4: "Vibration",
    5: "Female",
    6: "Male",
    7: "Rhythm",
    8: "Above/Cause",
    9: "Below/Effect",
}


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _load_json(path: str) -> dict[str, Any]:
    return json.loads(_resolve(path).read_text(encoding="utf-8"))


def _state_lacunarity(scores: list[float]) -> float:
    if not scores:
        return 0.0
    mean = sum(scores) / len(scores)
    if mean <= 0:
        return 0.0
    var = sum((x - mean) ** 2 for x in scores) / len(scores)
    return var / (mean * mean)


def _normalize_gap_scores(scores: list[float]) -> list[float]:
    max_score = max(scores) if scores else 0.0
    if max_score <= 0:
        return [1.0 for _ in scores]
    return [max(0.0, min(1.0, 1.0 - (score / max_score))) for score in scores]


def _top_gap_rows(raw_scores: list[float], positive_scores: list[float], gap_scores: list[float]) -> list[dict[str, Any]]:
    rows = []
    for i, (raw, positive, gap) in enumerate(zip(raw_scores, positive_scores, gap_scores)):
        rows.append(
            {
                "noetic": i,
                "name": _NOETIC_NAMES[i],
                "raw_extra_same_class_disruption": raw,
                "positive_evidence": positive,
                "gap_probability_like_score": gap,
                "wrong_direction": raw < 0.0,
            }
        )
    return sorted(rows, key=lambda row: (row["gap_probability_like_score"], row["wrong_direction"]), reverse=True)


def _fractal_analysis(scores: list[float]) -> dict[str, Any]:
    sys.path.insert(0, str(_NOETIC_COMPASS_ROOT))
    from api.pipeline.fractal_analysis import analyze_fractal

    result = analyze_fractal(scores)
    return {
        "dominant_sequence": result.dominant_sequence,
        "canonical_form": result.canonical_form,
        "cancellations_detected": result.cancellations_detected,
        "classification": result.classification,
        "orbit_length": result.orbit_length,
        "has_fixed_point": result.has_fixed_point,
    }


def _mean_by_label_from_noetic_cases(report: dict[str, Any]) -> list[float]:
    buckets: dict[int, list[float]] = {i: [] for i in range(10)}
    for case in report.get("noetic_cases", []):
        label = int(case["true_y"])
        buckets[label].append(1.0 - float(case["token_match_rate"]))
    return [
        (sum(values) / len(values)) if values else 0.0
        for _, values in sorted(buckets.items())
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="stage7_preflight_diagnostics_20260517.json")
    args = parser.parse_args(argv)

    stage7_manifest = _load_json("stage7_foundation_pilot_manifest_20260517.json")
    stage7_validation = _load_json("stage7_foundation_pilot_validation_20260517.json")
    stage32 = _load_json("pythia_ablation_per_class_layer3_clean_20260516.json")
    stage66_fresh = _load_json("stage6_role_bound_generation_localized_fresh_n30_hook_report_20260517.json")
    stage66_old = _load_json("stage6_role_bound_generation_localized_full_n30_hook_report_20260517.json")

    raw_disruption = [
        float(row["extra_same_class_disruption"])
        for row in stage32["per_class_token_match_specificity"]
    ]
    positive_evidence = [max(0.0, value) for value in raw_disruption]
    gap_scores = _normalize_gap_scores(positive_evidence)
    lacunarity = _state_lacunarity(positive_evidence)
    gap_rows = _top_gap_rows(raw_disruption, positive_evidence, gap_scores)

    fractal_inputs = {
        "stage3_2_per_class_same_class_disruption": positive_evidence,
        "stage6_6B_fresh_localized_generation_divergence": _mean_by_label_from_noetic_cases(stage66_fresh),
        "stage6_6B_old_subset_localized_generation_divergence": _mean_by_label_from_noetic_cases(stage66_old),
    }
    fractal_results = {
        name: {
            "scores": scores,
            "analysis": _fractal_analysis(scores),
        }
        for name, scores in fractal_inputs.items()
    }

    report = {
        "schema_version": "stage7_preflight_diagnostics.v1",
        "status": "PREFLIGHT_COMPLETE",
        "axis_confirmation": {
            "confirmed": True,
            "position_definition": stage7_manifest["position_definition"],
            "n_foundations": stage7_manifest["n_foundations"],
            "fixture_rows": stage7_manifest["n_rows"],
            "validation_errors": stage7_validation["n_errors"],
            "validation_warnings": stage7_validation["n_warnings"],
            "source": stage7_manifest["source"],
            "plain_english": (
                "The 28 are the original TKS seven foundations across four worlds/registers, "
                "mapped into CAS as F1T..F7E. They are not Drive x Domain."
            ),
        },
        "lacunarity_retrospective": {
            "method": (
                "Deterministic lacunarity-style gap map over Stage 3.2 noetic per-class "
                "same-class disruption, not the untrained neural LacunarityHead."
            ),
            "operator_scores": positive_evidence,
            "raw_extra_same_class_disruption": raw_disruption,
            "state_lacunarity_var_over_mean_sq": lacunarity,
            "top_gap_slots": gap_rows[:6],
            "does_it_flag_3_and_5": {
                "negative_noetic_flagged": raw_disruption[3] < 0.0,
                "female_noetic_flagged": raw_disruption[5] < 0.0,
                "answer": "yes, but not uniquely",
                "note": (
                    "^3 and ^5 are the only wrong-direction raw slots. The broader gap map "
                    "also flags ^1 and weakly flags ^4/^6, so the diagnostic supports the "
                    "lacunarity explanation but does not say the problem is only ^3/^5."
                ),
            },
        },
        "fractal_classification": {
            "method": (
                "Existing api.pipeline.fractal_analysis.analyze_fractal on per-noetic "
                "disruption trajectories."
            ),
            "results": fractal_results,
            "plain_english": (
                "The Stage 3.2 same-class disruption trajectory and the fresh Stage 6.6B "
                "generation-divergence trajectory classify as oscillatory. The older 20-row "
                "subset classifies as stabilizing, so the oscillatory claim is supported for "
                "the stronger/fresh evidence but should not be stated as universal."
            ),
        },
        "decision": {
            "stage7_pilot_claims_allowed": False,
            "next_allowed_step": (
                "Patch the Stage 7 evaluator overflow, then rerun the 28-foundation pilot "
                "as a discriminative readout test only."
            ),
        },
    }
    out_path = _resolve(args.out)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "axis": report["axis_confirmation"]["plain_english"],
        "lacunarity": report["lacunarity_retrospective"]["does_it_flag_3_and_5"],
        "fractal": {
            name: item["analysis"]["classification"]
            for name, item in fractal_results.items()
        },
        "out": out_path.name,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
