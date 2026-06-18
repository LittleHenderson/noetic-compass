"""Relabel saved PCBA/CJT causal generations from the prompt-bank metadata."""

from __future__ import annotations

from argparse import ArgumentParser
from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR.parent))

from scripts.run_cjt_bias_vibration_causal_experiment import classify_cjt_risk_output  # noqa: E402


SCHEMA_VERSION = "cas_harness_cjt_bias_vibration_causal_relabel.v0"


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--results-jsonl", required=True, type=Path)
    parser.add_argument("--prompt-bank", required=True, type=Path)
    parser.add_argument("--output-jsonl", required=True, type=Path)
    parser.add_argument("--metadata-output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata = relabel_cjt_bias_vibration_causal_outputs(
        results_jsonl_path=args.results_jsonl,
        prompt_bank_path=args.prompt_bank,
        output_jsonl_path=args.output_jsonl,
        metadata_output_path=args.metadata_output,
    )
    print(json.dumps(metadata, indent=2, sort_keys=True))
    print(f"[cjt-causal-relabel] wrote {args.output_jsonl}")
    print(f"[cjt-causal-relabel] wrote {args.metadata_output}")
    return 0


def relabel_cjt_bias_vibration_causal_outputs(
    *,
    results_jsonl_path: Path,
    prompt_bank_path: Path,
    output_jsonl_path: Path,
    metadata_output_path: Path,
) -> dict[str, Any]:
    scenarios = load_scenarios(prompt_bank_path)
    rows = read_rows(results_jsonl_path)
    output_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    label_counts: Counter[str] = Counter()
    changed = 0
    missing = 0
    with output_jsonl_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            scenario_id = str(row.get("scenario_id") or "")
            scenario = scenarios.get(scenario_id)
            if scenario is None:
                missing += 1
                handle.write(json.dumps(row, sort_keys=True) + "\n")
                continue
            old_label = row.get("label")
            old_reason = row.get("label_reason")
            label, reason = classify_cjt_risk_output(scenario, str(row.get("output") or ""))
            if label != old_label or reason != old_reason:
                changed += 1
            row = {
                **row,
                "original_label": old_label,
                "original_label_reason": old_reason,
                "label": label,
                "label_reason": reason,
            }
            label_counts[label] += 1
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "source": str(results_jsonl_path),
        "prompt_bank": str(prompt_bank_path),
        "output_jsonl": str(output_jsonl_path),
        "rows": len(rows),
        "changed_rows": int(changed),
        "missing_scenario_rows": int(missing),
        "label_distribution": dict(sorted(label_counts.items())),
        "claim": "Relabeling artifact only; licenses no causal claim by itself.",
    }
    metadata_output_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_output_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    return metadata


def load_scenarios(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("scenarios", payload) if isinstance(payload, dict) else payload
    return {str(row.get("id")): row for row in rows if isinstance(row, dict)}


def read_rows(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if text:
                rows.append(json.loads(text))
    return rows


if __name__ == "__main__":
    raise SystemExit(main())
