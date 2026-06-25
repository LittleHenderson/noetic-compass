"""One-screen stack-health CLI for CAS Forex.

Composes :func:`cas_forex.stack_health_check.load_stack_health_inputs`
into a single pass/fail readout the operator can run from a terminal:

    py -3.12 scripts/run_cas_forex_stack_check.py
    py -3.12 scripts/run_cas_forex_stack_check.py --summary-only
    py -3.12 scripts/run_cas_forex_stack_check.py --json
    py -3.12 scripts/run_cas_forex_stack_check.py --exit-code-on-degraded

The output is observational + factual remediation only — it never tells
the operator what to trade. Remediation strings describe missing
processes/surfaces ("start uvicorn ...", "launch autowake ...").
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

# Make sure we can import the package whether called from repo root or scripts/.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from cas_forex.stack_health_check import (  # noqa: E402
    compose_stack_health_report,
    load_stack_health_inputs,
)


_STATUS_HINTS = {
    "OK": "[OK]",
    "DEGRADED": "[DEGRADED]",
    "MISSING": "[MISSING]",
    "UNKNOWN": "[UNKNOWN]",
}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "One-screen CAS Forex stack-health check (observational + "
            "factual remediation only)."
        )
    )
    parser.add_argument(
        "--api-base",
        default="http://127.0.0.1:8765",
        help="Base URL for the cockpit API (default: http://127.0.0.1:8765).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full StackHealthReport as JSON.",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print only the plain-English summary and next actions.",
    )
    parser.add_argument(
        "--exit-code-on-degraded",
        action="store_true",
        help="Return exit code 1 when overall_status is not OK.",
    )
    parser.add_argument(
        "--repo-root",
        default=str(_REPO_ROOT),
        help="Repo root (default: parent of this script).",
    )
    return parser.parse_args(argv)


def _render_human(report) -> str:
    lines: list[str] = []
    lines.append(f"Overall: {_STATUS_HINTS.get(report.overall_status, report.overall_status)} {report.overall_status}")
    lines.append("")
    lines.append("Checks:")
    for c in report.checks:
        marker = _STATUS_HINTS.get(c.status, c.status)
        lines.append(f"  {marker} {c.name}: {c.headline}")
        if c.detail:
            lines.append(f"      {c.detail}")
    lines.append("")
    lines.append(f"Summary: {report.plain_english_summary}")
    if report.next_actions:
        lines.append("")
        lines.append("Next actions:")
        for i, action in enumerate(report.next_actions, 1):
            lines.append(f"  {i}. {action}")
    return "\n".join(lines)


def _render_summary_only(report) -> str:
    lines: list[str] = [report.plain_english_summary]
    if report.next_actions:
        lines.append("")
        lines.append("Next actions:")
        for i, action in enumerate(report.next_actions, 1):
            lines.append(f"  {i}. {action}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    inputs = load_stack_health_inputs(args.repo_root, api_base=args.api_base)
    report = compose_stack_health_report(**inputs)

    if args.json:
        print(json.dumps(asdict(report), indent=2, default=str))
    elif args.summary_only:
        print(_render_summary_only(report))
    else:
        print(_render_human(report))

    if args.exit_code_on_degraded and report.overall_status != "OK":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
