"""CLI for the CAS Forex static UI layout/zoom contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from cas_forex.ui_layout_contract import build_ui_layout_contract  # noqa: E402


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run static CAS Forex UI layout and browser-zoom contract checks."
    )
    parser.add_argument("--json", action="store_true", help="Print JSON.")
    parser.add_argument(
        "--exit-code-on-attention",
        action="store_true",
        help="Return non-zero when any layout contract check needs attention.",
    )
    return parser.parse_args(argv)


def _render_human(report: dict) -> str:
    lines = [
        (
            f"UI layout contract: {report.get('status', 'UNKNOWN')} "
            f"({report.get('ok_count', 0)} OK / {report.get('attention_count', 0)} attention)"
        ),
        f"Routes covered: {report.get('route_count', 0)}",
        "",
    ]
    for check in report.get("checks") or []:
        marker = "[OK]" if check.get("status") == "OK" else "[ATTENTION]"
        lines.append(f"{marker} {check.get('check_id', 'check')}: {check.get('detail', '')}")
        if check.get("next_action"):
            lines.append(f"  next: {check['next_action']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = build_ui_layout_contract(_REPO_ROOT)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(_render_human(report))
    if args.exit_code_on_attention and report.get("status") != "OK":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
