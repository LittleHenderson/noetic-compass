"""Run the consolidated CAS Forex mobile release readiness report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from cas_forex.mobile_release_readiness import (  # noqa: E402
    readiness_to_dict,
    render_readiness_report,
    run_mobile_release_readiness,
)
from cas_forex.mobile_web_base import default_mobile_web_base  # noqa: E402


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CAS Forex mobile web/PWA/APK readiness checks.")
    parser.add_argument(
        "--web-base",
        default=None,
        help="Built web/PWA preview base URL. Defaults to the current Owner Access LAN pairing base.",
    )
    parser.add_argument("--apk-path", default="ui/android/app/build/outputs/apk/debug/app-debug.apk", help="Debug APK path.")
    parser.add_argument("--timeout-seconds", type=float, default=10.0, help="Per-check timeout in seconds.")
    parser.add_argument("--skip-api-proxy", action="store_true", help="Skip same-origin /api/forex/health proxy check.")
    parser.add_argument("--skip-apk", action="store_true", help="Skip debug APK artifact check.")
    parser.add_argument("--skip-pairing-payload", action="store_true", help="Skip owner pairing payload check.")
    parser.add_argument("--skip-paired-api-bases", action="store_true", help="Skip paired PWA/direct API-base reachability check.")
    parser.add_argument("--skip-device-probe", action="store_true", help="Skip adb Android device probe.")
    parser.add_argument("--skip-docker", action="store_true", help="Skip Docker Engine availability check.")
    parser.add_argument("--skip-phone-proof", action="store_true", help="Skip latest phone browser/PWA runtime proof check.")
    parser.add_argument("--adb", default=None, help="Optional adb executable path.")
    parser.add_argument("--serial", default=None, help="Android serial when launching native pairing.")
    parser.add_argument(
        "--launch-native-pairing",
        action="store_true",
        help="Also run the native pairing launch helper. Defaults to dry-run unless --real-native-launch is passed.",
    )
    parser.add_argument(
        "--real-native-launch",
        action="store_true",
        help="Actually launch the native pairing intent on the phone instead of dry-running it.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON.")
    parser.add_argument("--exit-code-on-package-failure", action="store_true", help="Exit 1 if the package is not ready.")
    parser.add_argument("--exit-code-on-any-gate", action="store_true", help="Exit 1 if package, physical phone, or Docker gates remain.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    web_base = args.web_base or default_mobile_web_base()
    report = run_mobile_release_readiness(
        web_base=web_base,
        apk_path=args.apk_path,
        timeout_seconds=args.timeout_seconds,
        check_api_proxy=not args.skip_api_proxy,
        check_apk=not args.skip_apk,
        check_pairing_payload=not args.skip_pairing_payload,
        check_paired_api_bases=not args.skip_paired_api_bases and not args.skip_pairing_payload,
        check_android_device=not args.skip_device_probe,
        check_docker=not args.skip_docker,
        check_phone_proof=not args.skip_phone_proof,
        launch_native_pairing=args.launch_native_pairing,
        native_pairing_dry_run=not args.real_native_launch,
        adb_path=args.adb,
        serial=args.serial,
    )
    if args.json:
        print(json.dumps(readiness_to_dict(report), indent=2))
    else:
        print(render_readiness_report(report))

    if args.exit_code_on_any_gate and (
        not report.package_ready_for_phone_install
        or (report.phone_proof_checked and not report.phone_browser_verified)
        or not report.physical_phone_verified
        or not report.docker_available
    ):
        return 1
    if args.exit_code_on_package_failure and not report.package_ready_for_phone_install:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
