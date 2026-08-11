"""CLI for CAS Forex headless browser UI zoom screenshots."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from cas_forex.ui_browser_zoom_smoke import run_ui_browser_zoom_smoke  # noqa: E402


def _parse_csv(value: str | None) -> tuple[str, ...] | None:
    if value is None:
        return None
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture CAS Forex UI screenshots across desktop, zoomed, and phone viewports."
    )
    parser.add_argument(
        "--pages",
        default=None,
        help="Comma-separated page ids to capture, or all. Defaults to every registered page.",
    )
    parser.add_argument(
        "--profiles",
        default=None,
        help="Comma-separated profiles: desktop, desktop_zoom_150_effective, phone, or all.",
    )
    parser.add_argument("--dist-dir", default=None, help="Built UI dist directory. Defaults to ui/dist.")
    parser.add_argument("--output-dir", default=None, help="Directory for screenshot outputs.")
    parser.add_argument("--browser-path", default=None, help="Explicit Chrome/Edge executable path.")
    parser.add_argument("--timeout-seconds", type=float, default=25.0, help="Timeout per screenshot.")
    parser.add_argument("--dry-run", action="store_true", help="Plan screenshots without starting a browser.")
    parser.add_argument("--json", action="store_true", help="Print JSON.")
    parser.add_argument("--exit-code-on-failure", action="store_true", help="Exit non-zero on failed screenshots.")
    return parser.parse_args(argv)


def _render_human(report: dict) -> str:
    lines = [
        (
            f"UI browser zoom smoke: {report.get('status', 'UNKNOWN')} "
            f"({report.get('passed', 0)} passed / {report.get('failed', 0)} failed)"
        ),
        f"Pages: {report.get('page_count', 0)}  Profiles: {report.get('profile_count', 0)}",
        f"Output: {report.get('output_dir', '')}",
        "",
    ]
    for item in report.get("screenshots") or []:
        marker = "[OK]" if item.get("success") else "[FAIL]"
        dims = f"{item.get('width') or '?'}x{item.get('height') or '?'}"
        lines.append(
            f"{marker} {item.get('page')} / {item.get('profile')} "
            f"{dims} {item.get('bytes', 0)} bytes - {item.get('detail', '')}"
        )
    for attention in report.get("top_attention_items") or []:
        lines.append(f"[ATTENTION] {attention}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = run_ui_browser_zoom_smoke(
        root=_REPO_ROOT,
        dist_dir=args.dist_dir,
        output_dir=args.output_dir,
        pages=_parse_csv(args.pages),
        profiles=_parse_csv(args.profiles),
        browser_path=args.browser_path,
        timeout_seconds=args.timeout_seconds,
        dry_run=args.dry_run,
    )
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(_render_human(report))
    if args.exit_code_on_failure and report.get("status") not in {"OK", "DRY_RUN"}:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
