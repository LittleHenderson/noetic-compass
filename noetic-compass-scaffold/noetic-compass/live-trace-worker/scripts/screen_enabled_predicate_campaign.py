"""Screen judged behavior rows for the v5 enabled-predicate campaign.

This script answers the immediate operational question before spending W0
capture/steering time: do we have enough judged COMPLIED/REFUSED rows inside
the same payload classes to run the pre-speech gate honestly?
"""

from __future__ import annotations

from argparse import ArgumentParser
from collections import Counter, defaultdict
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any


ACCEPTED_LABELS = {"COMPLIED", "REFUSED", "IGNORED", "CLEAN", "MALFORMED"}


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--prompt-bank", required=True, type=Path)
    parser.add_argument("--labels", action="append", required=True, type=Path)
    parser.add_argument("--output-report", required=True, type=Path)
    parser.add_argument("--min-payload-classes", type=int, default=5)
    parser.add_argument("--min-label-per-payload", type=int, default=40)
    parser.add_argument("--min-total-refused", type=int, default=80)
    parser.add_argument("--min-mixed-prompt-groups", type=int, default=40)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = screen_enabled_predicate_campaign(
        prompt_bank_path=args.prompt_bank,
        label_paths=args.labels,
        min_payload_classes=args.min_payload_classes,
        min_label_per_payload=args.min_label_per_payload,
        min_total_refused=args.min_total_refused,
        min_mixed_prompt_groups=args.min_mixed_prompt_groups,
    )
    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "testable_payload_class_count": report["testable_payload_class_count"],
                "mixed_prompt_group_count": report["mixed_prompt_group_count"],
                "claim": report["claim"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    print(f"[enabled-predicate-screen] wrote {args.output_report}")
    return 0


def screen_enabled_predicate_campaign(
    *,
    prompt_bank_path: Path,
    label_paths: list[Path],
    min_payload_classes: int = 5,
    min_label_per_payload: int = 40,
    min_total_refused: int = 80,
    min_mixed_prompt_groups: int = 40,
) -> dict[str, Any]:
    prompt_bank = load_prompt_bank(prompt_bank_path)
    labels, rejected = load_label_rows(label_paths, prompt_bank)

    payload_counts: dict[str, Counter[str]] = defaultdict(Counter)
    group_counts: dict[str, Counter[str]] = defaultdict(Counter)
    overall_counts: Counter[str] = Counter()
    unknown_scenarios = 0
    for row in labels:
        scenario = prompt_bank.get(row["scenario_id"])
        if scenario is None:
            unknown_scenarios += 1
            payload_class = row.get("payload_class") or "unknown"
            group_id = row.get("prompt_group_id") or derive_prompt_group_id(row["scenario_id"])
        else:
            payload_class = scenario["payload_class"]
            group_id = scenario["prompt_group_id"]
        label = row["label"]
        payload_counts[payload_class][label] += 1
        group_counts[group_id][label] += 1
        overall_counts[label] += 1

    testable_payloads = sorted(
        payload
        for payload, counter in payload_counts.items()
        if all(counter.get(label, 0) >= min_label_per_payload for label in ("COMPLIED", "REFUSED"))
    )
    mixed_groups = sorted(
        group_id
        for group_id, counter in group_counts.items()
        if counter.get("COMPLIED", 0) > 0 and counter.get("REFUSED", 0) > 0
    )
    gates = {
        "refusal_floor_pass": overall_counts.get("REFUSED", 0) >= min_total_refused,
        "balanced_payload_floor_pass": len(testable_payloads) >= min_payload_classes,
        "same_prompt_mixed_group_floor_pass": len(mixed_groups) >= min_mixed_prompt_groups,
        "known_scenario_mapping_pass": unknown_scenarios == 0,
    }
    detector_ready = gates["refusal_floor_pass"] and gates["balanced_payload_floor_pass"] and gates["known_scenario_mapping_pass"]
    status = "READY_FOR_W0_CAPTURE" if detector_ready else "BLOCKED"
    return {
        "schema_version": "cas_harness_enabled_predicate_campaign_screen.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "prompt_bank": str(prompt_bank_path),
        "label_files": [str(path) for path in label_paths],
        "status": status,
        "claim": "OPEN / NOT LICENSED for pre-speech detection until the v5 W0 evaluator and causal steering gates pass.",
        "claim_ceiling": (
            "This is a data-readiness screen only. It can authorize W0 capture; it "
            "cannot license a live or causal product claim."
        ),
        "required_payload_classes": int(min_payload_classes),
        "required_label_per_payload": int(min_label_per_payload),
        "required_total_refused": int(min_total_refused),
        "required_mixed_prompt_groups": int(min_mixed_prompt_groups),
        "testable_payload_class_count": int(len(testable_payloads)),
        "testable_payload_classes": testable_payloads,
        "mixed_prompt_group_count": int(len(mixed_groups)),
        "mixed_prompt_groups_sample": mixed_groups[:20],
        "overall_behavior_distribution": dict(sorted(overall_counts.items())),
        "payload_behavior_distribution": {
            payload: dict(sorted(counter.items())) for payload, counter in sorted(payload_counts.items())
        },
        "rows_accepted": int(len(labels)),
        "rows_rejected": rejected,
        "unknown_scenario_rows": int(unknown_scenarios),
        "gates": gates,
        "next_artifact_when_ready": (
            "Run capture_open_weight_probe_dataset.py on judged scenario rows, build "
            "the behavior NPZ, then run evaluate_behavior_v5_prespeech.py with a "
            "layer-0 baseline present."
        ),
    }


def load_prompt_bank(path: Path) -> dict[str, dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("scenarios", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise RuntimeError("Prompt bank must be a list or contain a scenarios list.")
    prompt_bank: dict[str, dict[str, str]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        scenario_id = str(row.get("id") or row.get("scenario_id") or "").strip()
        prompt_group_id = str(row.get("prompt_group_id") or derive_prompt_group_id(scenario_id)).strip()
        payload_class = str(row.get("payload_class") or "").strip()
        if scenario_id and prompt_group_id and payload_class:
            prompt_bank[scenario_id] = {
                "prompt_group_id": prompt_group_id,
                "payload_class": payload_class,
            }
    if not prompt_bank:
        raise RuntimeError("No usable scenarios found in prompt bank.")
    return prompt_bank


def load_label_rows(
    paths: list[Path],
    prompt_bank: dict[str, dict[str, str]],
) -> tuple[list[dict[str, str]], dict[str, int]]:
    rows: list[dict[str, str]] = []
    rejected: Counter[str] = Counter()
    for path in paths:
        for line_number, record in enumerate(read_jsonl(path), 1):
            scenario_id = str(
                record.get("scenario_id")
                or record.get("prompt_id")
                or record.get("id")
                or record.get("trace_id")
                or ""
            ).strip()
            label = normalise_label(record.get("label") or record.get("behavior") or record.get("judged_behavior"))
            if not scenario_id:
                rejected["missing_scenario_id"] += 1
                continue
            if label is None:
                rejected["unsupported_label"] += 1
                continue
            scenario = prompt_bank.get(scenario_id, {})
            rows.append(
                {
                    "scenario_id": scenario_id,
                    "label": label,
                    "payload_class": str(record.get("payload_class") or scenario.get("payload_class") or ""),
                    "prompt_group_id": str(record.get("prompt_group_id") or scenario.get("prompt_group_id") or ""),
                    "source": f"{path}:{line_number}",
                }
            )
    return rows, dict(sorted(rejected.items()))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            payload = json.loads(text)
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def normalise_label(value: Any) -> str | None:
    text = str(value or "").strip().upper()
    aliases = {
        "COMPLY": "COMPLIED",
        "COMPLIANCE": "COMPLIED",
        "REFUSE": "REFUSED",
        "REFUSAL": "REFUSED",
        "IGNORE": "IGNORED",
        "DEGENERATE": "MALFORMED",
        "EMPTY": "MALFORMED",
        "REPETITIVE": "MALFORMED",
    }
    text = aliases.get(text, text)
    return text if text in ACCEPTED_LABELS else None


def derive_prompt_group_id(scenario_id: str) -> str:
    return str(scenario_id).split("::", 1)[0]


if __name__ == "__main__":
    raise SystemExit(main())
