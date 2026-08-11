"""Start/reuse the CAS Forex mobile stack and run readiness evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from cas_forex.mobile_stack_runner import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    render_stack_report,
    run_mobile_stack_readiness,
    stack_report_to_dict,
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Start or reuse the CAS Forex API/mobile preview and run mobile readiness."
    )
    parser.add_argument("--web-base", default=None, help="Phone-facing web base to test. Defaults to first LAN pairing base.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Evidence/log output directory.")
    parser.add_argument("--api-host", default="0.0.0.0", help="Host for a newly started API process.")
    parser.add_argument("--api-port", type=int, default=8765, help="API port.")
    parser.add_argument(
        "--api-workers",
        type=int,
        default=1,
        help="Stateful API worker count. CAS currently supports exactly one runtime owner.",
    )
    parser.add_argument("--web-host", default="0.0.0.0", help="Host for a newly started preview process.")
    parser.add_argument("--web-port", type=int, default=4173, help="Mobile preview port.")
    parser.add_argument("--python", dest="python_executable", default=None, help="Python executable for the API server wrapper.")
    parser.add_argument("--npm", dest="npm_executable", default=None, help="npm executable.")
    parser.add_argument("--no-start", action="store_true", help="Do not start missing services; only verify current state.")
    parser.add_argument("--stop-started", action="store_true", help="Stop any API/preview processes started by this run before exiting.")
    parser.add_argument("--timeout-seconds", type=float, default=45.0, help="Startup wait timeout.")
    parser.add_argument("--json", action="store_true", help="Print JSON.")
    parser.add_argument("--exit-code-on-package-failure", action="store_true", help="Exit 1 if package readiness fails.")
    parser.add_argument("--exit-code-on-stack-failure", action="store_true", help="Exit 1 if API or preview is not reachable.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = run_mobile_stack_readiness(
        workspace_root=_REPO_ROOT,
        output_dir=args.output_dir,
        web_base=args.web_base,
        api_host=args.api_host,
        api_port=args.api_port,
        api_workers=args.api_workers,
        web_host=args.web_host,
        web_port=args.web_port,
        python_executable=args.python_executable,
        npm_executable=args.npm_executable,
        start_missing=not args.no_start,
        keep_running=not args.stop_started,
        timeout_seconds=args.timeout_seconds,
    )
    if args.json:
        print(json.dumps(stack_report_to_dict(report), indent=2))
    else:
        print(render_stack_report(report))

    if args.exit_code_on_stack_failure and (not report.api_ready or not report.web_ready):
        return 1
    if args.exit_code_on_package_failure and not report.package_ready_for_phone_install:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
