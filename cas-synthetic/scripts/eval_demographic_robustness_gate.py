#!/usr/bin/env python3
"""Demographic robustness eval gate for CAS-Synthetic SDG runs.

Task #69: Add demographic-robustness eval gate.

PURPOSE:
    After a generation or evaluation run that covers all 36 demographic×tonal
    cells, this script reads a per-cell accuracy report (manifest.json) and
    computes a gate verdict: PASS / WARN / FAIL.

    The gate measures whether the CAS-Native model's classification accuracy
    is consistent across all demographic + tonal surface renderings of the
    same underlying CAS expression.  Systematic deviation for any cell
    indicates model bias toward (or against) that demographic surface pattern.

MANIFEST FORMAT:
    The script expects a JSON file with this shape:

        {
          "run_id": "<string>",
          "total_samples": <int>,
          "cells": [
            {
              "age_band": "<youth|adult|older>",
              "cultural_register": "<western_academic|western_vernacular|non_western>",
              "tonal": "<formal|casual|technical|plain_speech>",
              "n": <int — samples evaluated in this cell>,
              "correct": <int — exact-match correct in this cell>,
              "accuracy": <float in [0, 1]>
            },
            ...  (one entry per non-empty cell; up to 36 total)
          ]
        }

    The manifest is produced by the evaluation runner (not yet wired) after
    scoring a demographic-annotated dataset.  An example manifest fixture is
    written by --write-example-manifest for integration testing.

GATE THRESHOLDS:
    metric   : per-cell accuracy deviation from mean accuracy across cells
    pass     : max_deviation ≤ 0.05  (≤ 5 percentage points)
    warn     : 0.05 < max_deviation ≤ 0.10  (5–10 pp)
    fail     : max_deviation > 0.10  (> 10 pp)

    The same thresholds apply to two secondary checks:
    - min_cell_n ≥ 20  (warn if any cell has fewer than 20 samples)
    - all 36 cells present  (warn if any cell is missing)

EXIT CODES:
    0 — PASS
    1 — FAIL
    2 — WARN
    3 — error (missing/malformed manifest)

USAGE:
    python cas-synthetic/scripts/eval_demographic_robustness_gate.py \\
        --manifest path/to/manifest.json

    python cas-synthetic/scripts/eval_demographic_robustness_gate.py \\
        --manifest path/to/manifest.json --json

    python cas-synthetic/scripts/eval_demographic_robustness_gate.py \\
        --write-example-manifest path/to/example_manifest.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

_AXIS_GRID: tuple[tuple[str, str, str], ...] = tuple(
    (ab, cr, t)
    for ab in ("youth", "adult", "older")
    for cr in ("western_academic", "western_vernacular", "non_western")
    for t in ("formal", "casual", "technical", "plain_speech")
)  # 36 cells

_PASS_THRESHOLD = 0.05   # max_deviation ≤ 5pp → PASS
_WARN_THRESHOLD = 0.10   # max_deviation ≤ 10pp → WARN; > 10pp → FAIL
_MIN_CELL_N = 20         # fewer samples → warn (not fail)
_EXPECTED_CELLS = 36


# ---------------------------------------------------------------------------
# Gate computation
# ---------------------------------------------------------------------------


def compute_gate(manifest: dict[str, Any]) -> dict[str, Any]:
    """Compute the gate verdict from a parsed manifest dict.

    Returns a result dict with keys:
        verdict         : "PASS" | "WARN" | "FAIL" | "ERROR"
        exit_code       : 0 | 1 | 2 | 3
        mean_accuracy   : float
        max_deviation   : float
        worst_cell      : dict | None
        n_cells         : int
        n_cells_expected: int
        missing_cells   : list[str]
        low_n_cells     : list[str]
        warnings        : list[str]
        errors          : list[str]
        cells           : list[dict]  (sorted by deviation, descending)
    """
    errors: list[str] = []
    warnings: list[str] = []

    cells_raw = manifest.get("cells")
    if not isinstance(cells_raw, list) or not cells_raw:
        return {
            "verdict": "ERROR",
            "exit_code": 3,
            "errors": ["manifest.cells is missing or empty"],
            "warnings": [],
            "mean_accuracy": None,
            "max_deviation": None,
            "worst_cell": None,
            "n_cells": 0,
            "n_cells_expected": _EXPECTED_CELLS,
            "missing_cells": [],
            "low_n_cells": [],
            "cells": [],
        }

    # Validate and index cells
    valid_cells: list[dict[str, Any]] = []
    for i, cell in enumerate(cells_raw):
        err = _validate_cell(cell, i)
        if err:
            errors.append(err)
            continue
        valid_cells.append(cell)

    if errors:
        return {
            "verdict": "ERROR",
            "exit_code": 3,
            "errors": errors,
            "warnings": warnings,
            "mean_accuracy": None,
            "max_deviation": None,
            "worst_cell": None,
            "n_cells": len(valid_cells),
            "n_cells_expected": _EXPECTED_CELLS,
            "missing_cells": [],
            "low_n_cells": [],
            "cells": [],
        }

    # Check for missing cells
    present_keys = {
        f"{c['age_band']}__{c['cultural_register']}__{c['tonal']}"
        for c in valid_cells
    }
    expected_keys = {f"{ab}__{cr}__{t}" for ab, cr, t in _AXIS_GRID}
    missing_keys = sorted(expected_keys - present_keys)
    if missing_keys:
        warnings.append(
            f"{len(missing_keys)} of 36 cells missing from manifest: "
            + ", ".join(missing_keys[:5])
            + (" ..." if len(missing_keys) > 5 else "")
        )

    # Check for low-n cells
    low_n_cells = [
        f"{c['age_band']}__{c['cultural_register']}__{c['tonal']}"
        for c in valid_cells
        if c["n"] < _MIN_CELL_N
    ]
    if low_n_cells:
        warnings.append(
            f"{len(low_n_cells)} cells have n < {_MIN_CELL_N}: "
            + ", ".join(low_n_cells[:5])
            + (" ..." if len(low_n_cells) > 5 else "")
        )

    # Core metric: deviation from mean accuracy
    accuracies = [c["accuracy"] for c in valid_cells]
    mean_acc = sum(accuracies) / len(accuracies)

    for cell in valid_cells:
        cell["_deviation"] = abs(cell["accuracy"] - mean_acc)

    worst_cell = max(valid_cells, key=lambda c: c["_deviation"])
    max_dev = worst_cell["_deviation"]

    # Determine verdict
    if max_dev <= _PASS_THRESHOLD and not missing_keys and not low_n_cells:
        verdict, exit_code = "PASS", 0
    elif max_dev <= _WARN_THRESHOLD or missing_keys or low_n_cells:
        verdict, exit_code = "WARN", 2
    else:
        verdict, exit_code = "FAIL", 1

    sorted_cells = sorted(valid_cells, key=lambda c: c["_deviation"], reverse=True)
    for cell in sorted_cells:
        cell.pop("_deviation", None)

    return {
        "verdict": verdict,
        "exit_code": exit_code,
        "mean_accuracy": round(mean_acc, 6),
        "max_deviation": round(max_dev, 6),
        "worst_cell": {
            "age_band": worst_cell["age_band"],
            "cultural_register": worst_cell["cultural_register"],
            "tonal": worst_cell["tonal"],
            "n": worst_cell["n"],
            "accuracy": worst_cell["accuracy"],
        },
        "n_cells": len(valid_cells),
        "n_cells_expected": _EXPECTED_CELLS,
        "missing_cells": missing_keys,
        "low_n_cells": low_n_cells,
        "warnings": warnings,
        "errors": errors,
        "cells": sorted_cells,
        "thresholds": {
            "pass_max_deviation": _PASS_THRESHOLD,
            "warn_max_deviation": _WARN_THRESHOLD,
            "min_cell_n": _MIN_CELL_N,
        },
    }


def _validate_cell(cell: Any, index: int) -> str | None:
    """Return an error string if the cell dict is malformed, else None."""
    if not isinstance(cell, dict):
        return f"cells[{index}] is not a dict"
    for required_str in ("age_band", "cultural_register", "tonal"):
        if not isinstance(cell.get(required_str), str):
            return f"cells[{index}].{required_str} missing or not a string"
    for required_int in ("n", "correct"):
        if not isinstance(cell.get(required_int), (int, float)):
            return f"cells[{index}].{required_int} missing or not numeric"
    acc = cell.get("accuracy")
    if not isinstance(acc, (int, float)) or not (0.0 <= float(acc) <= 1.0):
        return f"cells[{index}].accuracy missing or not in [0, 1]"
    return None


# ---------------------------------------------------------------------------
# Example manifest fixture
# ---------------------------------------------------------------------------


def write_example_manifest(output_path: Path) -> None:
    """Write a synthetic example manifest for integration testing."""
    import random

    rng = random.Random(2026)
    cells = []
    for age_band, cultural_register, tonal in _AXIS_GRID:
        n = rng.randint(25, 35)
        # Introduce small realistic variance (within PASS threshold) plus a
        # couple of mild outliers to exercise the WARN band.
        base_acc = 0.87
        noise = rng.gauss(0.0, 0.025)
        acc = round(max(0.0, min(1.0, base_acc + noise)), 4)
        correct = round(n * acc)
        cells.append({
            "age_band": age_band,
            "cultural_register": cultural_register,
            "tonal": tonal,
            "n": n,
            "correct": correct,
            "accuracy": round(correct / n, 6),
        })

    manifest = {
        "run_id": "example_run_20260502",
        "total_samples": sum(c["n"] for c in cells),
        "cells": cells,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"Wrote example manifest to {output_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print_report(result: dict[str, Any], *, use_json: bool) -> None:
    if use_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    verdict = result["verdict"]
    print(f"\n{'='*60}")
    print(f"  Demographic Robustness Gate — {verdict}")
    print(f"{'='*60}")

    if result.get("mean_accuracy") is not None:
        print(f"  Mean accuracy (across cells): {result['mean_accuracy']:.4f}")
        print(f"  Max cell deviation from mean: {result['max_deviation']:.4f}")
        thresholds = result.get("thresholds", {})
        print(
            f"  Thresholds — pass: ≤{thresholds.get('pass_max_deviation', _PASS_THRESHOLD):.2f}  "
            f"warn: ≤{thresholds.get('warn_max_deviation', _WARN_THRESHOLD):.2f}  "
            f"fail: >{thresholds.get('warn_max_deviation', _WARN_THRESHOLD):.2f}"
        )
        print(f"  Cells evaluated: {result['n_cells']} / {result['n_cells_expected']}")

        if result.get("worst_cell"):
            wc = result["worst_cell"]
            print(
                f"\n  Worst cell: {wc['age_band']} × {wc['cultural_register']} × {wc['tonal']}"
                f"  (n={wc['n']}, acc={wc['accuracy']:.4f})"
            )

    if result.get("warnings"):
        print("\n  Warnings:")
        for w in result["warnings"]:
            print(f"    ⚠  {w}")

    if result.get("errors"):
        print("\n  Errors:")
        for e in result["errors"]:
            print(f"    ✗  {e}")

    if result.get("cells"):
        print("\n  Top 5 cells by deviation:")
        header = f"  {'age_band':<10} {'cultural_register':<22} {'tonal':<14} {'n':>5} {'acc':>7}"
        print(header)
        for cell in result["cells"][:5]:
            print(
                f"  {cell['age_band']:<10} {cell['cultural_register']:<22} "
                f"{cell['tonal']:<14} {cell['n']:>5} {cell['accuracy']:>7.4f}"
            )

    print(f"\n  Exit code: {result['exit_code']}")
    print(f"{'='*60}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Demographic robustness eval gate for SDG runs"
    )
    parser.add_argument(
        "--manifest",
        metavar="PATH",
        help="Path to per-cell accuracy manifest JSON",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="use_json",
        help="Output result as JSON instead of human-readable report",
    )
    parser.add_argument(
        "--write-example-manifest",
        metavar="PATH",
        help="Write a synthetic example manifest to PATH and exit",
    )
    args = parser.parse_args(argv)

    if args.write_example_manifest:
        write_example_manifest(Path(args.write_example_manifest))
        return 0

    if not args.manifest:
        parser.error("--manifest PATH is required (or use --write-example-manifest)")

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}", file=sys.stderr)
        return 3

    try:
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: could not parse manifest: {exc}", file=sys.stderr)
        return 3

    result = compute_gate(manifest)
    _print_report(result, use_json=args.use_json)
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
