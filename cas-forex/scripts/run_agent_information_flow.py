"""Generate the CAS Forex inter-agent information-flow plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.agent_information_flow import (
    DEFAULT_OUTPUT_DIR,
    build_agent_information_flow_plan,
    write_agent_information_flow_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    if args.summary_only:
        report = build_agent_information_flow_plan()
        payload = {
            "flow_status": report["flow_status"],
            "summary": report["summary"],
            "packets": [packet["packet_name"] for packet in report["canonical_packets"]],
            "stages": [stage["name"] for stage in report["flow_stages"]],
        }
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
        return 0

    paths = write_agent_information_flow_report(args.output_dir)
    print(json.dumps({key: str(value) for key, value in paths.items()}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

