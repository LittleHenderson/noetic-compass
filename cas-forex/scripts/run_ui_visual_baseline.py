"""CLI for CAS Forex UI screenshot visual baseline manifests and diffs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from cas_forex.ui_visual_baseline import (  # noqa: E402
    DEFAULT_BASELINE_PATH,
    compare_visual_baseline,
    write_visual_baseline_manifest,
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write or compare CAS Forex UI screenshot visual baselines."
    )
    parser.add_argument(
        "--source-report",
        required=True,
        help="Path to ui_browser_zoom_smoke_report.json from scripts/run_ui_browser_zoom_smoke.py.",
    )
    parser.add_argument(
        "--baseline",
        default=str(DEFAULT_BASELINE_PATH.relative_to(_REPO_ROOT)),
        help="Visual baseline manifest path. Defaults to ui/visual_baselines/cas_forex_ui_browser_zoom_baseline.json.",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Create or replace the baseline manifest from the source report.",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare the source report against the baseline. This is the default when --write-baseline is omitted.",
    )
    parser.add_argument(
        "--max-mean-delta",
        type=float,
        default=28.0,
        help="Allowed mean luminance delta across the screenshot fingerprint grid.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON.")
    parser.add_argument(
        "--exit-code-on-failure",
        action="store_true",
        help="Exit non-zero when comparison reports attention.",
    )
    return parser.parse_args(argv)


def _render_human(report: dict) -> str:
    if report.get("report_kind") == "cas_forex_ui_visual_baseline_manifest":
        return "\n".join(
            [
                "UI visual baseline manifest: WRITTEN",
                f"Screenshots: {report.get('screenshot_count', 0)}",
                f"Baseline: {report.get('baseline_path', '')}",
                f"Source: {report.get('source_report_path', '')}",
            ]
        )

    lines = [
        (
            f"UI visual baseline diff: {report.get('status', 'UNKNOWN')} "
            f"({report.get('ok_count', 0)} ok / {report.get('attention_count', 0)} attention)"
        ),
        f"Baseline: {report.get('baseline_path', '')}",
        f"Source: {report.get('source_report_path', '')}",
        f"Threshold: {report.get('max_mean_delta', '')}",
        "",
    ]
    for item in report.get("diffs") or []:
        marker = "[OK]" if item.get("status") == "OK" else "[ATTENTION]"
        delta = item.get("mean_delta")
        delta_text = "" if delta is None else f" delta={delta}"
        lines.append(f"{marker} {item.get('key')} {item.get('status')}{delta_text} - {item.get('detail')}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.write_baseline:
        report = write_visual_baseline_manifest(
            source_report_path=args.source_report,
            baseline_path=args.baseline,
            root=_REPO_ROOT,
        )
    else:
        report = compare_visual_baseline(
            source_report_path=args.source_report,
            baseline_path=args.baseline,
            root=_REPO_ROOT,
            max_mean_delta=args.max_mean_delta,
        )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(_render_human(report))
    if args.exit_code_on_failure and report.get("status") == "ATTENTION":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
