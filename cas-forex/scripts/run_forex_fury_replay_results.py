"""Summarize latest Forex Fury-derived CAS replay evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.forex_fury_replay_results import (
    DEFAULT_OUTPUT_DIR,
    build_forex_fury_replay_results,
    write_forex_fury_replay_results_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated CAS Forex replay result summaries.",
    )
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    if args.summary_only:
        report = build_forex_fury_replay_results()
        payload = {
            "replay_verdict": report["replay_verdict"],
            "adaptive_compounding_next_step": report["adaptive_compounding_next_step"],
            "condition_summary": report["condition_summary"],
            "walk_forward_summary": report["walk_forward_summary"],
        }
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
        return 0

    paths = write_forex_fury_replay_results_report(args.output_dir)
    print(json.dumps({key: str(value) for key, value in paths.items()}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

