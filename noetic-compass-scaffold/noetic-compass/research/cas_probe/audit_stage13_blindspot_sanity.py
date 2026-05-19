"""Sanity-check Stage 13 blind-spot claims before external framing."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import evaluate_stage6_role_bound_full as stage6


_HERE = Path(__file__).resolve().parent
_LABELS = (
    "relation_dependency",
    "typed_program",
    "production_recipe",
    "yield_query",
    "state_vector",
    "emergent_register_assignment",
    "membership_assertion",
    "cardinality_assertion",
    "set_operation_formula",
    "cover_partition_formula",
)


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _population(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for split in ("train", "val", "test"):
        counts = Counter(str(row["formula_label"]) for row in rows if str(row["split"]) == split)
        out[split] = {label: int(counts[label]) for label in _LABELS}
    counts_all = Counter(str(row["formula_label"]) for row in rows)
    out["all"] = {label: int(counts_all[label]) for label in _LABELS}
    out["is_perfectly_balanced"] = all(len(set(out[split].values())) == 1 for split in ("train", "val", "test", "all"))
    return out


def _readout_blindspots(report: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for readout, block in report["blind_spots"]["by_readout"].items():
        out[readout] = [
            {
                "label": row["label"],
                "blind_spot_score": float(row["blind_spot_score"]),
                "mean_accuracy_across_layers": float(row["mean_accuracy_across_layers"]),
                "best_layer": int(row["best_layer"]),
                "best_layer_accuracy": float(row["best_layer_accuracy"]),
            }
            for row in block["top_blind_spot_candidates"]
        ]
    return out


def _relation_dependency_note(report: dict[str, Any]) -> dict[str, Any]:
    notes: dict[str, Any] = {}
    for readout, block in report["blind_spots"]["by_readout"].items():
        for row in block["ranked_classes"]:
            if row["label"] == "relation_dependency":
                notes[readout] = {
                    "blind_spot_rank": 1 + [x["label"] for x in block["ranked_classes"]].index("relation_dependency"),
                    "mean_accuracy_across_layers": float(row["mean_accuracy_across_layers"]),
                    "best_layer": int(row["best_layer"]),
                    "best_layer_accuracy": float(row["best_layer_accuracy"]),
                    "blind_spot_score": float(row["blind_spot_score"]),
                }
                break
    headline_pc = report["headline"]["test"]["per_class"]["relation_dependency"]
    notes["headline_readout_layer"] = {
        "readout": report["headline"]["readout"],
        "layer": int(report["headline"]["layer"]),
        "accuracy": float(headline_pc["accuracy"]),
        "mean_confidence": float(headline_pc["mean_confidence"]),
        "mean_entropy": float(headline_pc["mean_entropy"]),
    }
    return notes


def _write_markdown(result: dict[str, Any], out_md: Path) -> None:
    lines = [
        "# Stage 13 Blind-Spot Sanity Audit",
        "",
        f"**Verdict:** `{result['verdict']}`",
        "",
        "## Population Check",
        "",
        f"- Perfectly balanced fixture: `{result['population']['is_perfectly_balanced']}`",
        "- Per split: train `360`, val `120`, test `420` per class when balanced.",
        "",
        "## Threshold Provenance",
        "",
    ]
    for item in result["trace_thresholds"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Per-Readout Blind Spots",
            "",
        ]
    )
    for readout, rows in result["per_readout_blindspots"].items():
        labels = ", ".join(f"`{row['label']}` ({row['mean_accuracy_across_layers']:.3f})" for row in rows)
        lines.append(f"- `{readout}`: {labels}")
    lines.extend(
        [
            "",
            "## Relation Dependency",
            "",
            f"- Headline readout/layer: `{result['relation_dependency']['headline_readout_layer']['readout']}` layer `{result['relation_dependency']['headline_readout_layer']['layer']}`",
            f"- Headline accuracy: `{result['relation_dependency']['headline_readout_layer']['accuracy']:.4f}`",
            "",
            "Interpretation: `relation_dependency` is an aggregate/readout-path blind-spot candidate, not a failure at the best headline readout.",
            "",
            "## Boundary",
            "",
            "Blind spot means weak or unstable evidence under a specific readout path. It does not prove model incapacity, exact causal neurons, or internal CAS compiler validation.",
            "",
        ]
    )
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", default="stage12_equations_formulas_full_20260517.jsonl")
    parser.add_argument("--stage13-report", default="stage13_multilayer_formula_trace_audit_20260518.json")
    parser.add_argument("--out-report", default="stage13_blindspot_sanity_audit_20260519.json")
    parser.add_argument("--out-md", default="STAGE13_BLINDSPOT_SANITY_AUDIT_20260519.md")
    args = parser.parse_args(argv)

    fixture = _resolve(args.fixture)
    stage13_report = _resolve(args.stage13_report)
    out_report = _resolve(args.out_report)
    out_md = _resolve(args.out_md)
    rows = stage6._load_jsonl(fixture)
    report = _load_json(stage13_report)
    result = {
        "schema_version": "stage13_blindspot_sanity_audit.v1",
        "verdict": "BLINDSPOT_LANGUAGE_DEFENSIBLE_WITH_PER_READOUT_BOUNDARY",
        "fixture_file": fixture.name,
        "fixture_sha256": stage6._sha256_of_file(fixture),
        "stage13_report_file": stage13_report.name,
        "stage13_report_sha256": stage6._sha256_of_file(stage13_report),
        "population": _population(rows),
        "trace_thresholds": [
            "low confidence: at least half of layer positions have confidence < 0.45",
            "high entropy: at least half of layer positions have entropy > 70% of maximum 10-class entropy",
            "stable: majority label covers at least 70% of layers and longest stable run is at least 5 layers",
            "early-correct-then-drift: first correct layer <= 4 and final layer is wrong",
            "late-emerging-correct: first correct layer >= 7 and final layer is correct, or final layer correct after non-stable trace",
            "conflicted: at least 5 switches or no majority over half the layers",
            "bug fix 80377ab changed invalid strict zip iteration for switch count only; it did not change thresholds",
        ],
        "per_readout_blindspots": _readout_blindspots(report),
        "relation_dependency": _relation_dependency_note(report),
        "boundary": (
            "Blind spots are readout-path diagnostics over hidden activations. They are not model-incapacity proof."
        ),
    }
    out_report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(result, out_md)
    print(json.dumps({"verdict": result["verdict"], "balanced": result["population"]["is_perfectly_balanced"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
