"""Create a CAS Forex web/PWA/APK phone release evidence bundle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from cas_forex.phone_release_bundle import (  # noqa: E402
    DEFAULT_APK_PATH,
    DEFAULT_OUTPUT_DIR,
    build_phone_release_bundle,
    bundle_to_dict,
)
from cas_forex.mobile_web_base import default_mobile_web_base  # noqa: E402


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Package the verified CAS Forex phone/PWA/APK artifacts and smoke report."
    )
    parser.add_argument(
        "--web-base",
        default=None,
        help="Phone/web URL to smoke before packaging. Defaults to the current Owner Access LAN pairing base.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Evidence bundle output directory.",
    )
    parser.add_argument(
        "--apk-path",
        default=str(DEFAULT_APK_PATH),
        help="Debug APK path to hash and copy.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=10.0,
        help="Per-request smoke timeout in seconds.",
    )
    parser.add_argument(
        "--no-copy-apk",
        action="store_true",
        help="Hash the APK but do not copy it into the evidence bundle.",
    )
    parser.add_argument(
        "--skip-api-proxy",
        action="store_true",
        help="Skip the same-origin /api/forex/health smoke check.",
    )
    parser.add_argument(
        "--skip-apk",
        action="store_true",
        help="Skip APK validation in the web/phone smoke checker.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full bundle manifest as JSON.",
    )
    parser.add_argument(
        "--exit-code-on-failure",
        action="store_true",
        help="Return non-zero when the bundle is not ready for phone install testing.",
    )
    return parser.parse_args(argv)


def _render_human(bundle) -> str:
    manifest = bundle_to_dict(bundle)
    lines = [
        bundle.summary,
        f"Output: {bundle.output_dir}",
        f"Phone web URL: {manifest.get('tested_web_base') or bundle.web_base}",
        f"Phone Quick Start URL: {manifest.get('phone_quick_start_url') or 'unavailable'}",
        f"Smoke: {bundle.smoke_report.get('passed')} passed / {bundle.smoke_report.get('failed')} failed",
        f"Mobile readiness: {bundle.mobile_readiness_report.get('summary')}",
        f"Readiness report: {bundle.mobile_readiness_report_path}",
        f"Ready for phone install testing: {str(bundle.ready_for_phone_install).lower()}",
        f"Android device: {manifest.get('android_device_detail') or 'unknown'}",
        f"adb: {manifest.get('android_adb_path') or 'unavailable'}",
        f"APK install-pair attempt: {manifest.get('apk_install_pairing_attempt_status') or 'none'}",
        f"Docker Engine: {manifest.get('docker_engine_status') or 'unknown'}",
        "",
        "Artifacts:",
    ]
    for artifact in bundle.artifacts:
        status = "exists" if artifact.exists else "missing"
        copied = f", copied to {artifact.copied_to}" if artifact.copied_to else ""
        lines.append(
            f"  - {artifact.artifact_id}: {status}, "
            f"{artifact.size_bytes or 0} bytes, sha256={artifact.sha256 or 'n/a'}{copied}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    web_base = args.web_base or default_mobile_web_base()
    bundle = build_phone_release_bundle(
        workspace_root=_REPO_ROOT,
        output_dir=args.output_dir,
        web_base=web_base,
        apk_path=args.apk_path,
        timeout_seconds=args.timeout_seconds,
        copy_apk=not args.no_copy_apk,
        check_api_proxy=not args.skip_api_proxy,
        check_apk=not args.skip_apk,
    )
    if args.json:
        print(json.dumps(bundle_to_dict(bundle), indent=2))
    else:
        print(_render_human(bundle))
    if args.exit_code_on_failure and not bundle.ready_for_phone_install:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
