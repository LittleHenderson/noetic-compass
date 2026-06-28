"""Generate the CAS Forex agentic trading-day workflow plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.agent_workflow import (
    DEFAULT_OUTPUT_DIR,
    build_agent_workflow_plan,
    write_agent_workflow_plan_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated CAS Forex agent workflow plan artifacts.",
    )
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    if args.summary_only:
        report = build_agent_workflow_plan()
        payload = {
            "workflow_status": report["workflow_status"],
            "summary": report["summary"],
            "agents": [agent["agent_id"] for agent in report["agent_roster"]],
            "autowake_events": [event["event_id"] for event in report["autowake_schedule"]["events"]],
        }
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
        return 0

    paths = write_agent_workflow_plan_report(args.output_dir)
    print(json.dumps({key: str(value) for key, value in paths.items()}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

