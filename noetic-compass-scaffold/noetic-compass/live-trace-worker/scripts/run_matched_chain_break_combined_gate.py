"""Run the combined v6 matched-prompt chain-break data gate.

This stitches together the two frozen local steps used before spending on
all-layer W0 capture:

1. Relabel saved generations with the CAS boundary-intact judge.
2. Screen the combined labels for matched prompt groups and class balance.

The output manifest is a data-readiness artifact only. A READY_FOR_W0_CAPTURE
status authorizes the next capture/evaluation run; it does not license internal
prompt-injection detection, prevention, reversal, removal, or causality.
"""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR.parent))

from scripts.relabel_matched_prompt_chain_break_generations import relabel_generations  # noqa: E402
from scripts.screen_matched_prompt_chain_break_campaign import (  # noqa: E402
    screen_matched_prompt_chain_break_campaign,
)


SCHEMA_VERSION = "cas_harness_matched_prompt_combined_gate.v1"
DEFAULT_LABELS_FILENAME = "combined_boundary_labels.jsonl"
DEFAULT_RELABEL_REPORT_FILENAME = "combined_boundary_relabel_report.json"
DEFAULT_SCREEN_REPORT_FILENAME = "combined_matched_screen_report.json"
DEFAULT_MANIFEST_FILENAME = "combined_gate_manifest.json"


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--prompt-bank", required=True, type=Path)
    parser.add_argument("--generations", action="append", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--min-payload-classes", type=int, default=5)
    parser.add_argument("--min-chain-label-per-payload", type=int, default=10)
    parser.add_argument("--min-total-broken", type=int, default=40)
    parser.add_argument("--min-total-intact", type=int, default=40)
    parser.add_argument("--min-mixed-prompt-groups", type=int, default=40)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = run_combined_gate(
        prompt_bank_path=args.prompt_bank,
        generation_paths=args.generations,
        output_dir=args.output_dir,
        min_payload_classes=args.min_payload_classes,
        min_chain_label_per_payload=args.min_chain_label_per_payload,
        min_total_broken=args.min_total_broken,
        min_total_intact=args.min_total_intact,
        min_mixed_prompt_groups=args.min_mixed_prompt_groups,
    )
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "chain_status_distribution": manifest["metrics"]["chain_status_distribution"],
                "mixed_prompt_group_count": manifest["metrics"]["mixed_prompt_group_count"],
                "testable_payload_class_count": manifest["metrics"]["testable_payload_class_count"],
                "manifest": manifest["artifacts"]["manifest"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    print(f"[matched-chain-break-combined-gate] wrote {manifest['artifacts']['manifest']}")
    return 0


def run_combined_gate(
    *,
    prompt_bank_path: Path,
    generation_paths: list[Path],
    output_dir: Path,
    min_payload_classes: int = 5,
    min_chain_label_per_payload: int = 10,
    min_total_broken: int = 40,
    min_total_intact: int = 40,
    min_mixed_prompt_groups: int = 40,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    labels_path = output_dir / DEFAULT_LABELS_FILENAME
    relabel_report_path = output_dir / DEFAULT_RELABEL_REPORT_FILENAME
    screen_report_path = output_dir / DEFAULT_SCREEN_REPORT_FILENAME
    manifest_path = output_dir / DEFAULT_MANIFEST_FILENAME

    relabel_report = relabel_generations(
        prompt_bank_path=prompt_bank_path,
        generation_paths=generation_paths,
        output_labels_path=labels_path,
        output_report_path=relabel_report_path,
    )
    screen_report = screen_matched_prompt_chain_break_campaign(
        prompt_bank_path=prompt_bank_path,
        label_paths=[labels_path],
        min_payload_classes=min_payload_classes,
        min_chain_label_per_payload=min_chain_label_per_payload,
        min_total_broken=min_total_broken,
        min_total_intact=min_total_intact,
        min_mixed_prompt_groups=min_mixed_prompt_groups,
    )
    screen_report_path.write_text(json.dumps(screen_report, indent=2, sort_keys=True), encoding="utf-8")

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "status": screen_report["status"],
        "prompt_bank": str(prompt_bank_path),
        "generation_files": [str(path) for path in generation_paths],
        "artifacts": {
            "labels": str(labels_path),
            "relabel_report": str(relabel_report_path),
            "screen_report": str(screen_report_path),
            "manifest": str(manifest_path),
        },
        "metrics": {
            "rows_relabelled": int(relabel_report["row_count"]),
            "rows_accepted_by_screen": int(screen_report["rows_accepted"]),
            "behavior_distribution": relabel_report["behavior_distribution"],
            "behavior_change_distribution": relabel_report["behavior_change_distribution"],
            "chain_status_distribution": screen_report["chain_status_distribution"],
            "payload_chain_status_distribution": screen_report["payload_chain_status_distribution"],
            "mixed_prompt_group_count": int(screen_report["mixed_prompt_group_count"]),
            "testable_payload_class_count": int(screen_report["testable_payload_class_count"]),
            "testable_payload_classes": screen_report["testable_payload_classes"],
            "rows_rejected_by_relabel": relabel_report["rows_rejected"],
            "rows_rejected_by_screen": screen_report["rows_rejected"],
        },
        "gates": screen_report["gates"],
        "gate_requirements": {
            "min_payload_classes": int(min_payload_classes),
            "min_chain_label_per_payload": int(min_chain_label_per_payload),
            "min_total_broken": int(min_total_broken),
            "min_total_intact": int(min_total_intact),
            "min_mixed_prompt_groups": int(min_mixed_prompt_groups),
        },
        "claim": "OPEN / NOT LICENSED for internal prompt-injection detection.",
        "claim_ceiling": (
            "This combined gate is data-readiness only. It can authorize all-layer W0 capture "
            "when READY_FOR_W0_CAPTURE, but it cannot license prompt-injection prevention, "
            "removal, reversal, hallucination prevention, live interception, or causal claims."
        ),
        "next_artifact_when_ready": (
            "Run all-layer W0 capture with the same prompt bank and accepted labels, then run "
            "evaluate_behavior_v6_matched_prespeech.py with grouped prompt controls."
        ),
        "next_artifact_when_blocked": (
            "Recover or rerun more generation-only samples, relabel them with cas_boundary_intact_v1, "
            "and rerun this combined gate before spending on all-layer W0 capture."
        ),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    raise SystemExit(main())
