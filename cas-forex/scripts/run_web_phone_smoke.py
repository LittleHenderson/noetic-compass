"""CLI for CAS Forex web/PWA/APK phone readiness smoke checks.

Examples:

    py -3.12 scripts/run_web_phone_smoke.py
    py -3.12 scripts/run_web_phone_smoke.py --web-base http://10.0.0.6:4173
    py -3.12 scripts/run_web_phone_smoke.py --expect-cloud-api-auth --owner-token <token>
    py -3.12 scripts/run_web_phone_smoke.py --skip-apk --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from cas_forex.web_phone_smoke import report_to_dict, run_web_phone_smoke  # noqa: E402


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Smoke-check the CAS Forex web/PWA phone URL and Android debug APK."
    )
    parser.add_argument(
        "--web-base",
        default="http://127.0.0.1:4173",
        help="Base URL serving the built phone/web app (default: http://127.0.0.1:4173).",
    )
    parser.add_argument(
        "--apk-path",
        default="ui/android/app/build/outputs/apk/debug/app-debug.apk",
        help="Debug APK path to verify.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=10.0,
        help="Per-request timeout in seconds.",
    )
    parser.add_argument(
        "--skip-api-proxy",
        action="store_true",
        help="Skip the /api/forex/health same-origin proxy check.",
    )
    parser.add_argument(
        "--expect-cloud-api-auth",
        action="store_true",
        help=(
            "Also verify a protected API route refuses no-token requests and "
            "accepts the owner token. Use this against CAS_FOREX_CLOUD_MODE=1."
        ),
    )
    parser.add_argument(
        "--owner-token",
        default=None,
        help="Owner token for --expect-cloud-api-auth (defaults to CAS_FOREX_OWNER_TOKEN).",
    )
    parser.add_argument(
        "--skip-apk",
        action="store_true",
        help="Skip checking the Android debug APK artifact.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the report as JSON.",
    )
    parser.add_argument(
        "--exit-code-on-failure",
        action="store_true",
        help="Return non-zero if any check fails.",
    )
    return parser.parse_args(argv)


def _render_human(report) -> str:
    lines = [
        (
            f"Web/phone smoke against {report.web_base}: "
            f"{report.passed} passed / {report.failed} failed / {report.total_checks} total "
            f"({report.elapsed_ms:.1f} ms)"
        ),
        report.plain_english_summary,
        "",
    ]
    for result in report.results:
        marker = "[OK]" if result.success else "[FAIL]"
        status = result.status_code if result.status_code is not None else "n/a"
        lines.append(
            f"{marker} {result.check_id:<24} status={status:<4} "
            f"{result.detail} ({result.elapsed_ms:.1f} ms)"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = run_web_phone_smoke(
        web_base=args.web_base,
        apk_path=args.apk_path,
        timeout_seconds=args.timeout_seconds,
        check_api_proxy=not args.skip_api_proxy,
        check_cloud_api_auth=args.expect_cloud_api_auth,
        owner_token=args.owner_token or os.environ.get("CAS_FOREX_OWNER_TOKEN"),
        check_apk=not args.skip_apk,
    )
    if args.json:
        print(json.dumps(report_to_dict(report), indent=2))
    else:
        print(_render_human(report))
    if args.exit_code_on_failure and report.failed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
