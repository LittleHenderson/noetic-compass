"""Active end-to-end endpoint smoke CLI for CAS Forex.

Hits every endpoint in :data:`cas_forex.e2e_smoke.BUILT_IN_ENDPOINTS`,
validates response shape, and reports pass/fail per endpoint.

    py -3.12 scripts/run_e2e_smoke.py
    py -3.12 scripts/run_e2e_smoke.py --summary-only
    py -3.12 scripts/run_e2e_smoke.py --json
    py -3.12 scripts/run_e2e_smoke.py --exit-code-on-failure

Output is observational only — it lists which surfaces responded with
the expected shape and which did not. It does NOT advise trades.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from cas_forex.e2e_smoke import (  # noqa: E402
    E2ESmokeReport,
    report_to_dict,
    run_endpoint_smoke,
)


_STATUS_OK = "[OK]"
_STATUS_FAIL = "[FAIL]"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Active end-to-end endpoint smoke check for CAS Forex "
            "(observational only)."
        )
    )
    parser.add_argument(
        "--api-base",
        default="http://127.0.0.1:8765",
        help="Base URL for the cockpit API (default: http://127.0.0.1:8765).",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=10.0,
        help="Per-request timeout in seconds (default: 10).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full E2ESmokeReport as JSON.",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print only passed/failed counts and the failure list.",
    )
    parser.add_argument(
        "--exit-code-on-failure",
        action="store_true",
        help="Return non-zero exit code if any endpoint check failed.",
    )
    return parser.parse_args(argv)


def _render_human(report: E2ESmokeReport) -> str:
    lines: list[str] = []
    lines.append(
        f"Endpoint smoke against {report.api_base}: "
        f"{report.passed} passed / {report.failed} failed "
        f"/ {report.total_checks} total "
        f"({report.elapsed_ms:.1f} ms wall)"
    )
    lines.append("")
    lines.append(report.plain_english_summary)
    lines.append("")

    # Per-category counts
    cats: Counter[str] = Counter()
    cat_pass: Counter[str] = Counter()
    for r in report.results:
        cats[r.category] += 1
        if r.success:
            cat_pass[r.category] += 1
    if cats:
        lines.append("By category:")
        for cat, total in sorted(cats.items()):
            ok = cat_pass[cat]
            marker = _STATUS_OK if ok == total else _STATUS_FAIL
            lines.append(f"  {marker} {cat}: {ok}/{total}")
        lines.append("")

    # All results
    lines.append("Per-endpoint:")
    for r in report.results:
        marker = _STATUS_OK if r.success else _STATUS_FAIL
        status = r.status_code if r.status_code is not None else "n/a"
        lines.append(
            f"  {marker} {r.method:<6} {r.path:<55} "
            f"status={status} schema={r.schema_check} "
            f"({r.elapsed_ms:.1f} ms)"
        )

    if report.failures:
        lines.append("")
        lines.append("Failures:")
        for r in report.failures:
            err = r.error_message or "(no error message)"
            lines.append(f"  {_STATUS_FAIL} {r.method} {r.path}: {err}")
    return "\n".join(lines)


def _render_summary(report: E2ESmokeReport) -> str:
    lines: list[str] = []
    lines.append(
        f"{report.passed} passed / {report.failed} failed "
        f"/ {report.total_checks} total"
    )
    lines.append(report.plain_english_summary)
    if report.failures:
        lines.append("")
        lines.append("Failures:")
        for r in report.failures:
            err = r.error_message or "(no error message)"
            lines.append(f"  {_STATUS_FAIL} {r.method} {r.path}: {err}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = run_endpoint_smoke(
        api_base=args.api_base,
        timeout_seconds=args.timeout_seconds,
    )
    if args.json:
        print(json.dumps(report_to_dict(report), indent=2, default=str))
    elif args.summary_only:
        print(_render_summary(report))
    else:
        print(_render_human(report))

    if args.exit_code_on_failure and report.failed > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
