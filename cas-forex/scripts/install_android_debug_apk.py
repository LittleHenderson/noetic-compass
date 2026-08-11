"""Install or inspect the CAS Forex Android debug APK."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from cas_forex.android_apk_install import (
    DEFAULT_APK_PATH,
    DEFAULT_ANDROID_PACKAGE_ID,
    deep_link_launch_report_to_dict,
    deep_link_launch_report_to_json,
    device_probe_to_json,
    install_android_debug_apk,
    install_report_to_dict,
    install_report_to_json,
    launch_android_native_pairing_deep_link,
    probe_android_devices,
    render_deep_link_launch_report,
    render_device_probe,
    render_install_report,
)
from cas_forex.mobile_apk_proof import record_android_apk_install_pairing_proof  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install the CAS Forex debug APK on an attached Android device.")
    parser.add_argument("--apk", default=str(DEFAULT_APK_PATH), help="APK path relative to the repo root, or absolute path.")
    parser.add_argument("--adb", default=None, help="Optional adb executable path. CAS_FOREX_ADB is also supported.")
    parser.add_argument("--serial", default=None, help="Device serial when more than one ready Android device is attached.")
    parser.add_argument("--dry-run", action="store_true", help="Check adb, APK, and device selection without installing.")
    parser.add_argument("--list-devices", action="store_true", help="Only list Android devices visible to adb.")
    parser.add_argument("--launch-native-pairing", action="store_true", help="After install, launch the casforex://pair native pairing deep link.")
    parser.add_argument("--launch-only", action="store_true", help="Skip APK install and only launch the native pairing deep link.")
    parser.add_argument("--pairing-url", default=None, help="Native pairing URL to launch. Defaults to the first locally generated casforex://pair URL.")
    parser.add_argument("--package-id", default=DEFAULT_ANDROID_PACKAGE_ID, help="Android package id that should receive the deep link.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--timeout-seconds", type=float, default=120.0, help="Install command timeout.")
    parser.add_argument("--wait-for-device", action="store_true", help="Poll adb until a ready Android device is attached before installing or launching.")
    parser.add_argument("--wait-timeout-seconds", type=float, default=600.0, help="Maximum time to wait for an attached/authorized Android device.")
    parser.add_argument("--wait-poll-seconds", type=float, default=2.0, help="Seconds between adb device probes while waiting.")
    parser.add_argument("--exit-code-on-failure", action="store_true", help="Return exit code 1 when the check/install fails.")
    args = parser.parse_args(argv)

    workspace_root = Path(__file__).resolve().parents[1]
    if args.list_devices:
        probe = probe_android_devices(adb_path=args.adb, timeout_seconds=min(args.timeout_seconds, 10.0))
        print(device_probe_to_json(probe) if args.json else render_device_probe(probe))
        return 1 if args.exit_code_on_failure and not probe.success else 0

    if args.launch_only:
        launch = launch_android_native_pairing_deep_link(
            pairing_url=args.pairing_url,
            serial=args.serial,
            adb_path=args.adb,
            package_id=args.package_id,
            dry_run=args.dry_run,
            timeout_seconds=min(args.timeout_seconds, 30.0),
            wait_for_device=args.wait_for_device,
            wait_timeout_seconds=args.wait_timeout_seconds,
            wait_poll_seconds=args.wait_poll_seconds,
        )
        print(deep_link_launch_report_to_json(launch) if args.json else render_deep_link_launch_report(launch))
        return 1 if args.exit_code_on_failure and not launch.success else 0

    report = install_android_debug_apk(
        workspace_root=workspace_root,
        apk_path=args.apk,
        serial=args.serial,
        adb_path=args.adb,
        dry_run=args.dry_run,
        timeout_seconds=args.timeout_seconds,
        wait_for_device=args.wait_for_device,
        wait_timeout_seconds=args.wait_timeout_seconds,
        wait_poll_seconds=args.wait_poll_seconds,
    )
    if not args.launch_native_pairing:
        print(install_report_to_json(report) if args.json else render_install_report(report))
        return 1 if args.exit_code_on_failure and not report.success else 0

    launch = None
    if report.success:
        launch = launch_android_native_pairing_deep_link(
            pairing_url=args.pairing_url,
            serial=report.selected_serial or args.serial,
            adb_path=args.adb,
            package_id=args.package_id,
            dry_run=args.dry_run,
            timeout_seconds=min(args.timeout_seconds, 30.0),
        )

    install_payload = install_report_to_dict(report)
    launch_payload = (
        deep_link_launch_report_to_dict(launch)
        if launch is not None
        else _skipped_native_pairing_launch_payload(
            install_payload=install_payload,
            package_id=args.package_id,
            dry_run=args.dry_run,
        )
    )
    apk_proof = record_android_apk_install_pairing_proof(
        workspace_root=workspace_root,
        install_report=install_payload,
        native_pairing_launch=launch_payload,
    )

    if args.json:
        import json

        print(json.dumps(
            {
                "install": install_payload,
                "native_pairing_launch": launch_payload,
                "android_apk_install_pairing_proof": apk_proof,
            },
            indent=2,
        ))
    else:
        print(render_install_report(report))
        if launch:
            print()
            print(render_deep_link_launch_report(launch))
        if apk_proof:
            print()
            print(
                "Android APK install/native pairing proof: "
                + ("verified" if apk_proof.get("android_apk_install_pairing_verified") else "not verified")
            )
    failed = not report.success or (launch is not None and not launch.success)
    return 1 if args.exit_code_on_failure and failed else 0


def _skipped_native_pairing_launch_payload(
    *,
    install_payload: dict,
    package_id: str,
    dry_run: bool,
) -> dict:
    return {
        "success": False,
        "dry_run": dry_run,
        "adb_path": install_payload.get("adb_path"),
        "package_id": package_id,
        "devices": install_payload.get("devices") or [],
        "selected_serial": install_payload.get("selected_serial"),
        "pairing_url": None,
        "command": (),
        "returncode": None,
        "stdout": "",
        "stderr": "",
        "message": "Native pairing launch was not attempted because APK install did not succeed.",
    }


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
