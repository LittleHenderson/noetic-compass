"""Print and write the final CAS Forex mobile verification handoff."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from cas_forex.android_apk_install import (  # noqa: E402
    DEFAULT_ANDROID_PACKAGE_ID,
    deep_link_launch_report_to_dict,
    install_android_debug_apk,
    install_report_to_dict,
    launch_android_native_pairing_deep_link,
)
from cas_forex.mobile_apk_proof import record_android_apk_install_pairing_proof  # noqa: E402
from cas_forex.mobile_final_verification import (  # noqa: E402
    MobileFinalVerificationReport,
    build_mobile_final_verification,
    mobile_final_verification_to_json,
    render_mobile_final_verification,
    write_mobile_final_verification,
)
from cas_forex.mobile_phone_verifier import (  # noqa: E402
    phone_proof_watch_status,
    render_phone_proof_watch_status,
)
from cas_forex.owner_auth import pairing_payload  # noqa: E402

DEFAULT_PHONE_TIMEOUT_SECONDS = 180.0
DEFAULT_WATCH_ALL_PHONE_TIMEOUT_SECONDS = 900.0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show the final CAS Forex phone/APK/Docker verification state and next owner action."
    )
    parser.add_argument("--json", action="store_true", help="Print JSON.")
    parser.add_argument("--no-write", action="store_true", help="Do not write the latest final verification artifact.")
    parser.add_argument("--watch-phone", action="store_true", help="Wait for real phone proof before writing final state.")
    parser.add_argument(
        "--watch-all",
        action="store_true",
        help="Wait for phone proof, then wait for an Android device, install the APK, launch native pairing, and write final state.",
    )
    parser.add_argument(
        "--run-apk-pairing",
        action="store_true",
        help="After verified phone proof exists, run APK install/native-pairing before writing final state.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=None,
        help=(
            "Phone-proof wait timeout. Defaults to 180s for --watch-phone and "
            "900s for --watch-all."
        ),
    )
    parser.add_argument("--poll-seconds", type=float, default=2.0, help="Phone-proof polling interval.")
    parser.add_argument("--apk-timeout-seconds", type=float, default=120.0, help="APK install/native-pairing command timeout.")
    parser.add_argument("--apk-wait-timeout-seconds", type=float, default=600.0, help="Maximum time to wait for an attached Android device.")
    parser.add_argument("--apk-wait-poll-seconds", type=float, default=2.0, help="Seconds between adb device probes.")
    parser.add_argument(
        "--print-live-pairing-links",
        action="store_true",
        help=(
            "Print full live PWA/APK pairing links to this terminal only. "
            "These owner-token links are never written to final verification JSON/README."
        ),
    )
    parser.add_argument("--exit-code-on-any-gate", action="store_true", help="Exit 1 unless all final gates are verified.")
    return parser.parse_args(argv)


def _effective_phone_timeout(args: argparse.Namespace) -> float:
    if args.timeout_seconds is not None:
        return args.timeout_seconds
    if args.watch_all:
        return DEFAULT_WATCH_ALL_PHONE_TIMEOUT_SECONDS
    return DEFAULT_PHONE_TIMEOUT_SECONDS


def _run_apk_install_pairing(
    *,
    timeout_seconds: float,
    wait_timeout_seconds: float,
    wait_poll_seconds: float,
) -> dict[str, Any]:
    install_report = install_android_debug_apk(
        workspace_root=_REPO_ROOT,
        timeout_seconds=timeout_seconds,
        wait_for_device=True,
        wait_timeout_seconds=wait_timeout_seconds,
        wait_poll_seconds=wait_poll_seconds,
    )
    install_payload = install_report_to_dict(install_report)
    if install_report.success:
        launch_report = launch_android_native_pairing_deep_link(
            serial=install_report.selected_serial,
            timeout_seconds=min(timeout_seconds, 30.0),
        )
        launch_payload = deep_link_launch_report_to_dict(launch_report)
    else:
        launch_payload = {
            "success": False,
            "dry_run": False,
            "adb_path": install_payload.get("adb_path"),
            "package_id": DEFAULT_ANDROID_PACKAGE_ID,
            "devices": install_payload.get("devices") or [],
            "selected_serial": install_payload.get("selected_serial"),
            "pairing_url": None,
            "command": (),
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "message": "Native pairing launch was not attempted because APK install did not succeed.",
        }
    proof = record_android_apk_install_pairing_proof(
        workspace_root=_REPO_ROOT,
        install_report=install_payload,
        native_pairing_launch=launch_payload,
    )
    return {
        "install": install_payload,
        "native_pairing_launch": launch_payload,
        "android_apk_install_pairing_proof": proof,
    }


def _build_report(args: argparse.Namespace, *, watch_phone: bool) -> MobileFinalVerificationReport:
    return build_mobile_final_verification(
        workspace_root=_REPO_ROOT,
        watch_phone=watch_phone,
        timeout_seconds=_effective_phone_timeout(args),
        poll_seconds=args.poll_seconds,
    )


def _print_phone_wait_handoff(args: argparse.Namespace) -> None:
    initial = phone_proof_watch_status(workspace_root=_REPO_ROOT)
    if not initial.phone_browser_verified:
        timeout_seconds = _effective_phone_timeout(args)
        print("Initial phone proof status:")
        print(render_phone_proof_watch_status(initial))
        print()
        if args.print_live_pairing_links:
            _print_live_pairing_links()
            print()
        print(f"Waiting up to {timeout_seconds:g}s for verified real-phone proof...")
        print(flush=True)
    else:
        print("Initial phone proof status:")
        print(render_phone_proof_watch_status(initial))
        print()
        if args.print_live_pairing_links:
            _print_live_pairing_links()
            print()


def _print_live_pairing_links() -> None:
    try:
        payload = pairing_payload()
    except Exception as exc:  # pragma: no cover - defensive terminal handoff only
        print(f"Live pairing links unavailable: {exc}")
        return
    pwa_links = _string_list(payload.get("pairing_urls"))
    native_links = _string_list(payload.get("native_pairing_urls"))
    pwa_bases = _string_list(payload.get("pairing_api_bases"))
    direct_bases = _string_list(payload.get("direct_api_bases"))
    print("Live pairing links (terminal only; not written to evidence):")
    print(f"LAN access enabled: {str(bool(payload.get('lan_mode_enabled'))).lower()}")
    if pwa_links:
        print("PWA phone pairing links:")
        for link in pwa_links[:3]:
            print(f"- {link}")
    if native_links:
        print("Android APK pairing links:")
        for link in native_links[:3]:
            print(f"- {link}")
    if pwa_bases or direct_bases:
        print("Phone API bases:")
        for base in pwa_bases[:3]:
            print(f"- PWA/proxy: {base}")
        for base in direct_bases[:3]:
            print(f"- APK/direct: {base}")


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _print_final_phone_status() -> None:
    print("Final phone proof status:")
    print(render_phone_proof_watch_status(phone_proof_watch_status(workspace_root=_REPO_ROOT)))
    print()


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    should_watch_phone = args.watch_phone or args.watch_all
    if should_watch_phone and not args.json:
        _print_phone_wait_handoff(args)
    report = _build_report(args, watch_phone=should_watch_phone)
    if should_watch_phone and not args.json:
        _print_final_phone_status()
    apk_attempt: dict[str, Any] | None = None
    should_run_apk_pairing = args.watch_all or args.run_apk_pairing
    if should_run_apk_pairing and report.phone_browser_verified and not report.apk_install_pairing_verified:
        if not args.json:
            print("Verified phone proof exists. Waiting for Android APK install/native pairing...")
            print(flush=True)
        apk_attempt = _run_apk_install_pairing(
            timeout_seconds=args.apk_timeout_seconds,
            wait_timeout_seconds=args.apk_wait_timeout_seconds,
            wait_poll_seconds=args.apk_wait_poll_seconds,
        )
        report = _build_report(args, watch_phone=False)
    written_paths = None if args.no_write else write_mobile_final_verification(report, workspace_root=_REPO_ROOT)
    if args.json:
        print(mobile_final_verification_to_json(report))
    else:
        print(render_mobile_final_verification(report))
        if should_run_apk_pairing and not report.phone_browser_verified:
            print()
            print("APK install/native pairing was not started because verified phone proof is still missing.")
        if apk_attempt:
            proof = apk_attempt.get("android_apk_install_pairing_proof") or {}
            print()
            print(
                "APK install/native pairing attempt: "
                + ("verified" if proof.get("android_apk_install_pairing_verified") else "not verified")
            )
        if written_paths:
            print()
            print(f"Written JSON: {written_paths['json_path']}")
            print(f"Written README: {written_paths['readme_path']}")
    if args.exit_code_on_any_gate and report.status != "verified":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
