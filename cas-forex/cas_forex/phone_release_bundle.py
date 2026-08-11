"""Build a phone-release evidence bundle for CAS Forex.

The bundle records the installable web/PWA smoke result, hashes the built web
and APK artifacts, and optionally copies the debug APK into an ignored evidence
folder for easy transfer. Phone verification is scoped to app delivery and
network reachability; live operations remain governed by the same owner runtime
gates and broker state used everywhere else in CAS Forex.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from cas_forex.mobile_release_readiness import readiness_to_dict, run_mobile_release_readiness
from cas_forex.web_phone_smoke import (
    Transport,
    report_to_dict,
    run_web_phone_smoke,
)


@dataclass(frozen=True)
class PhoneReleaseArtifact:
    artifact_id: str
    path: str
    exists: bool
    size_bytes: int | None = None
    sha256: str | None = None
    copied_to: str | None = None


@dataclass(frozen=True)
class PhoneReleaseBundle:
    generated_at: str
    web_base: str
    output_dir: str
    ready_for_phone_install: bool
    smoke_report_path: str
    mobile_readiness_report_path: str
    bundle_manifest_path: str
    readme_path: str
    artifacts: tuple[PhoneReleaseArtifact, ...]
    smoke_report: dict[str, Any]
    mobile_readiness_report: dict[str, Any]
    phone_verification_runbook: dict[str, Any]
    remaining_external_gates: tuple[str, ...]
    summary: str


DEFAULT_OUTPUT_DIR = Path("evidence_runs") / "web_phone_release" / "latest"
DEFAULT_APK_PATH = Path("ui") / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
DEFAULT_RELEASE_APK_PATH = Path("ui") / "android" / "app" / "build" / "outputs" / "apk" / "release" / "app-release.apk"
INSTALL_TEST_REQUIRED_ARTIFACT_IDS = ("android_debug_apk", "web_index", "pwa_manifest", "service_worker")
SIGNED_RELEASE_ARTIFACT_ID = "android_release_apk"
WEB_ARTIFACTS = (
    ("web_index", Path("ui") / "dist" / "index.html"),
    ("pwa_manifest", Path("ui") / "dist" / "manifest.webmanifest"),
    ("service_worker", Path("ui") / "dist" / "sw.js"),
)
PHONE_VERIFICATION_SCOPE = (
    "Phone verification proves app delivery, pairing, and network reachability. "
    "Live trading, broker, deposit, payout, and other money-moving actions remain "
    "governed by owner-authorized runtime gates, credentials, and broker state."
)


def build_phone_release_bundle(
    *,
    workspace_root: str | Path = ".",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    web_base: str = "http://127.0.0.1:4173",
    apk_path: str | Path = DEFAULT_APK_PATH,
    release_apk_path: str | Path = DEFAULT_RELEASE_APK_PATH,
    timeout_seconds: float = 10.0,
    copy_apk: bool = True,
    copy_release_apk: bool = True,
    check_api_proxy: bool = True,
    check_apk: bool = True,
    transport: Transport | None = None,
) -> PhoneReleaseBundle:
    """Create a web/PWA/APK release evidence bundle under ``output_dir``."""
    root = Path(workspace_root).resolve()
    resolved_output = _resolve_under_root(root, output_dir)
    resolved_output.mkdir(parents=True, exist_ok=True)

    resolved_apk = _resolve_under_root(root, apk_path)
    resolved_release_apk = _resolve_under_root(root, release_apk_path)
    smoke_report = run_web_phone_smoke(
        web_base=web_base,
        apk_path=resolved_apk,
        timeout_seconds=timeout_seconds,
        check_api_proxy=check_api_proxy,
        check_apk=check_apk,
        web_dist_dir=root / "ui" / "dist",
        transport=transport,
    )
    smoke_payload = report_to_dict(smoke_report)

    copied_apk_path: Path | None = None
    if copy_apk and resolved_apk.exists():
        copied_apk_path = resolved_output / "cas-forex-debug.apk"
        shutil.copy2(resolved_apk, copied_apk_path)
    copied_release_apk_path: Path | None = None
    if copy_release_apk and resolved_release_apk.exists():
        copied_release_apk_path = resolved_output / "cas-forex-release.apk"
        shutil.copy2(resolved_release_apk, copied_release_apk_path)

    artifacts: list[PhoneReleaseArtifact] = []
    artifacts.append(
        _artifact(
            "android_debug_apk",
            resolved_apk,
            copied_to=copied_apk_path,
        )
    )
    if copied_apk_path is not None:
        artifacts.append(_artifact("release_bundle_debug_apk_copy", copied_apk_path))
    artifacts.append(
        _artifact(
            "android_release_apk",
            resolved_release_apk,
            copied_to=copied_release_apk_path,
        )
    )
    if copied_release_apk_path is not None:
        artifacts.append(_artifact("release_bundle_release_apk_copy", copied_release_apk_path))
    for artifact_id, rel_path in WEB_ARTIFACTS:
        artifacts.append(_artifact(artifact_id, root / rel_path))

    generated_at = datetime.now(timezone.utc).isoformat()
    smoke_report_path = resolved_output / "web_phone_smoke.json"
    mobile_readiness_report_path = resolved_output / "mobile_release_readiness.json"
    bundle_manifest_path = resolved_output / "phone_release_bundle.json"
    readme_path = resolved_output / "README.md"
    mobile_readiness = run_mobile_release_readiness(
        workspace_root=root,
        web_base=web_base,
        apk_path=resolved_apk,
        timeout_seconds=timeout_seconds,
        check_api_proxy=check_api_proxy,
        check_apk=check_apk,
        transport=transport,
    )
    mobile_readiness_payload = readiness_to_dict(mobile_readiness)
    artifacts_ready = _required_artifacts_ready(artifacts)
    package_ready = bool(mobile_readiness_payload.get("package_ready_for_phone_install"))
    ready = smoke_report.failed == 0 and artifacts_ready and package_ready
    readiness_gates = mobile_readiness_payload.get("remaining_external_gates")
    remaining_external_gates = tuple(
        gate for gate in readiness_gates if isinstance(gate, str)
    ) if isinstance(readiness_gates, (list, tuple)) else (
        "Open Quick Start from a real phone over the LAN preview to record verified phone browser/PWA runtime proof.",
        "Attach an Android phone and run npm --prefix ui run mobile:apk:wait-install-pair to prove APK install plus native pairing launch.",
        "Build/verify the Docker image on a host with Docker installed if using cloud/container deploy.",
    )
    phone_verification_runbook = _phone_verification_runbook(
        web_base=web_base,
        copied_apk_path=copied_apk_path,
        copied_release_apk_path=copied_release_apk_path,
        mobile_readiness_payload=mobile_readiness_payload,
    )
    summary = (
        "Phone release bundle is ready for install testing."
        if ready
        else "Phone release bundle is not ready; inspect failed smoke checks, missing artifacts, or failed mobile readiness checks."
    )

    bundle = PhoneReleaseBundle(
        generated_at=generated_at,
        web_base=web_base,
        output_dir=str(resolved_output),
        ready_for_phone_install=ready,
        smoke_report_path=str(smoke_report_path),
        mobile_readiness_report_path=str(mobile_readiness_report_path),
        bundle_manifest_path=str(bundle_manifest_path),
        readme_path=str(readme_path),
        artifacts=tuple(artifacts),
        smoke_report=smoke_payload,
        mobile_readiness_report=mobile_readiness_payload,
        phone_verification_runbook=phone_verification_runbook,
        remaining_external_gates=remaining_external_gates,
        summary=summary,
    )

    smoke_report_path.write_text(json.dumps(smoke_payload, indent=2), encoding="utf-8")
    mobile_readiness_report_path.write_text(json.dumps(mobile_readiness_payload, indent=2), encoding="utf-8")
    bundle_manifest_path.write_text(json.dumps(bundle_to_dict(bundle), indent=2), encoding="utf-8")
    readme_path.write_text(_render_readme(bundle), encoding="utf-8")
    return bundle


def bundle_to_dict(bundle: PhoneReleaseBundle) -> dict[str, Any]:
    out = asdict(bundle)
    out["artifacts"] = [asdict(artifact) for artifact in bundle.artifacts]
    out.update(_handoff_summary_fields(bundle))
    out["install_test_required_artifact_ids"] = list(INSTALL_TEST_REQUIRED_ARTIFACT_IDS)
    out["missing_install_test_required_artifacts"] = _missing_required_artifacts(list(bundle.artifacts))
    release_apk = next(
        (artifact for artifact in bundle.artifacts if artifact.artifact_id == SIGNED_RELEASE_ARTIFACT_ID),
        None,
    )
    out["signed_release_apk_present"] = bool(release_apk and release_apk.exists)
    out["signed_release_apk_sha256"] = release_apk.sha256 if release_apk and release_apk.exists else None
    out["signed_release_apk_size_bytes"] = release_apk.size_bytes if release_apk and release_apk.exists else None
    return out


def _handoff_summary_fields(bundle: PhoneReleaseBundle) -> dict[str, Any]:
    readiness = bundle.mobile_readiness_report if isinstance(bundle.mobile_readiness_report, dict) else {}
    runbook = bundle.phone_verification_runbook if isinstance(bundle.phone_verification_runbook, dict) else {}
    device_probe = readiness.get("device_probe") if isinstance(readiness.get("device_probe"), dict) else {}
    devices = device_probe.get("devices") if isinstance(device_probe.get("devices"), list) else []
    ready_devices = [
        device for device in devices
        if isinstance(device, dict) and bool(device.get("is_ready"))
    ]
    android_check = _check_payload(readiness, "android_device_probe")
    docker_check = _check_payload(readiness, "docker_cli")
    apk_check = _check_payload(readiness, "android_apk_install_pairing_attempt")
    tested_quick_start_url = (
        _string_or_none(runbook.get("tested_quick_start_url"))
        or _string_or_none(readiness.get("phone_quick_start_url"))
        or _quick_start_url(bundle.web_base)
    )
    phone_quick_start_url = (
        _string_or_none(runbook.get("phone_quick_start_url"))
        or _phone_reachable_quick_start_url(
            bundle.web_base,
            runbook.get("pairing_context") if isinstance(runbook.get("pairing_context"), dict) else {},
            readiness,
        )
        or tested_quick_start_url
    )
    return {
        "tested_web_base": _string_or_none(runbook.get("tested_web_base")) or bundle.web_base,
        "tested_quick_start_url": tested_quick_start_url,
        "phone_quick_start_url": phone_quick_start_url,
        "package_ready_for_phone_install": bool(readiness.get("package_ready_for_phone_install")),
        "phone_browser_observed": bool(readiness.get("phone_browser_observed")),
        "phone_browser_verified": bool(readiness.get("phone_browser_verified")),
        "phone_proof_fresh": bool(readiness.get("phone_proof_fresh")),
        "phone_observation_fresh": bool(readiness.get("phone_observation_fresh")),
        "apk_install_pairing_attempt_status": (
            _string_or_none(runbook.get("current_apk_install_pairing_attempt_status"))
            or _string_or_none(apk_check.get("status"))
            or "none"
        ),
        "apk_install_pairing_attempt_message": (
            _string_or_none(runbook.get("current_apk_install_pairing_attempt_message"))
            or _string_or_none(apk_check.get("detail"))
        ),
        "android_adb_path": _string_or_none(device_probe.get("adb_path")),
        "android_device_ready": bool(android_check.get("success")) or bool(ready_devices),
        "android_device_count": len(devices),
        "android_device_ready_count": len(ready_devices),
        "android_device_detail": (
            _string_or_none(android_check.get("detail"))
            or _string_or_none(device_probe.get("message"))
        ),
        "docker_engine_status": _string_or_none(docker_check.get("status")) or (
            "ready" if bool(readiness.get("docker_available")) else "external"
        ),
        "docker_engine_detail": _string_or_none(docker_check.get("detail")),
    }


def _resolve_under_root(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


def _artifact(artifact_id: str, path: Path, *, copied_to: Path | None = None) -> PhoneReleaseArtifact:
    if not path.exists():
        return PhoneReleaseArtifact(
            artifact_id=artifact_id,
            path=str(path),
            exists=False,
            copied_to=str(copied_to) if copied_to is not None else None,
        )
    return PhoneReleaseArtifact(
        artifact_id=artifact_id,
        path=str(path),
        exists=True,
        size_bytes=path.stat().st_size,
        sha256=_sha256_file(path),
        copied_to=str(copied_to) if copied_to is not None else None,
    )


def _required_artifacts_ready(artifacts: list[PhoneReleaseArtifact]) -> bool:
    return not _missing_required_artifacts(artifacts)


def _missing_required_artifacts(artifacts: list[PhoneReleaseArtifact]) -> list[str]:
    by_id = {artifact.artifact_id: artifact for artifact in artifacts}
    return [
        artifact_id for artifact_id in INSTALL_TEST_REQUIRED_ARTIFACT_IDS
        if not (by_id.get(artifact_id) and by_id[artifact_id].exists)
    ]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _signed_release_artifact_line(artifacts: list[PhoneReleaseArtifact]) -> str:
    artifact = next((item for item in artifacts if item.artifact_id == SIGNED_RELEASE_ARTIFACT_ID), None)
    if not artifact or not artifact.exists:
        return "missing"
    size = artifact.size_bytes if artifact.size_bytes is not None else 0
    return f"present, {size} bytes, {artifact.sha256 or 'no hash'}"


def _render_readme(bundle: PhoneReleaseBundle) -> str:
    runbook = bundle.phone_verification_runbook
    pairing_context = runbook.get("pairing_context") if isinstance(runbook.get("pairing_context"), dict) else {}
    steps = runbook.get("steps") if isinstance(runbook.get("steps"), list) else []
    lines = [
        "# CAS Forex Phone Release Bundle",
        "",
        f"Generated: `{bundle.generated_at}`",
        f"Web base tested: `{bundle.web_base}`",
        f"Ready for phone install testing: `{str(bundle.ready_for_phone_install).lower()}`",
        "",
        "## Summary",
        "",
        bundle.summary,
        f"Install-test required artifacts: `{', '.join(INSTALL_TEST_REQUIRED_ARTIFACT_IDS)}`",
        f"Missing install-test required artifacts: `{', '.join(_missing_required_artifacts(list(bundle.artifacts))) or 'none'}`",
        f"Signed release APK: `{_signed_release_artifact_line(list(bundle.artifacts))}`",
        "",
        "## Artifacts",
        "",
        "| Artifact | Exists | Size bytes | SHA-256 | Copied to |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for artifact in bundle.artifacts:
        lines.append(
            "| "
            f"`{artifact.artifact_id}` | "
            f"`{str(artifact.exists).lower()}` | "
            f"{artifact.size_bytes if artifact.size_bytes is not None else ''} | "
            f"`{artifact.sha256 or ''}` | "
            f"`{artifact.copied_to or ''}` |"
        )
    lines.extend(
        [
            "",
            "## Smoke Report",
            "",
            f"- Report: `{bundle.smoke_report_path}`",
            f"- Passed: `{bundle.smoke_report.get('passed')}`",
            f"- Failed: `{bundle.smoke_report.get('failed')}`",
            "",
            "## Consolidated Readiness",
            "",
            f"- Report: `{bundle.mobile_readiness_report_path}`",
            "- Run report: `python scripts/run_mobile_release_readiness.py --web-base "
            f"{bundle.web_base}`",
            "- UI shortcut: `npm --prefix ui run mobile:readiness -- --web-base "
            f"{bundle.web_base}`",
            "- Start/reuse stack and write readiness evidence: `python scripts/run_mobile_stack_readiness.py --web-base "
            f"{bundle.web_base}`",
            "",
            "## Phone Verification Runbook",
            "",
            "Pairing URLs in this evidence packet are token-redacted. Reveal the live token only from Owner Access on the PC.",
            "",
            f"- Tested phone web URL: `{runbook.get('tested_web_base') or bundle.web_base}`",
            f"- Tested Quick Start URL: `{runbook.get('tested_quick_start_url') or _quick_start_url(bundle.web_base)}`",
            f"- Phone-reachable Quick Start URL: `{runbook.get('phone_quick_start_url') or runbook.get('tested_quick_start_url') or _quick_start_url(bundle.web_base)}`",
            f"- PWA/proxy API base: `{pairing_context.get('pwa_api_base') or ''}`",
            f"- APK/direct API base: `{pairing_context.get('direct_api_base') or ''}`",
            f"- Redacted PWA pairing URL: `{pairing_context.get('redacted_pairing_url') or ''}`",
            f"- Redacted APK pairing URL: `{pairing_context.get('redacted_native_pairing_url') or ''}`",
            f"- Copied debug APK: `{runbook.get('copied_debug_apk') or ''}`",
            f"- Copied release APK: `{runbook.get('copied_release_apk') or ''}`",
            f"- Current phone browser observed: `{str(runbook.get('current_phone_browser_observed')).lower()}`",
            f"- Current phone browser verified: `{str(runbook.get('current_phone_browser_verified')).lower()}`",
            f"- Current phone proof freshness: `{_runbook_freshness_line(runbook, 'current_phone_proof')}`",
            f"- Current phone observation freshness: `{_runbook_freshness_line(runbook, 'current_phone_observation')}`",
            f"- Current APK runtime: `{_runbook_apk_runtime_line(runbook)}`",
            f"- Current APK install-pair attempt: `{_runbook_apk_attempt_line(runbook)}`",
            f"- Current Android release signing: `{_runbook_release_signing_line(runbook)}`",
            f"- Verification scope: {runbook.get('verification_scope') or runbook.get('claim_boundary') or ''}",
            "",
            "Steps:",
            "",
        ]
    )
    for index, step in enumerate(steps, start=1):
        lines.append(f"{index}. {step}")
    lines.extend(
        [
            "",
            "## Physical Android Verification",
            "",
            "- Combined current proof session: `npm --prefix ui run mobile:proof-session`",
            "- List devices: `npm --prefix ui run mobile:apk:devices`",
            "- Build debug and release APKs serially: `npm --prefix ui run mobile:apk:build-all`",
            "- Install APK only: `npm --prefix ui run mobile:apk:install`",
            "- Wait for phone, install, and launch native pairing: `npm --prefix ui run mobile:apk:wait-install-pair`",
            "- Install and launch native pairing: `npm --prefix ui run mobile:apk:install-pair`",
            "- Launch native pairing on an already installed APK: `npm --prefix ui run mobile:apk:pair`",
            "- Direct helper: `python scripts/install_android_debug_apk.py --launch-native-pairing --wait-for-device --wait-timeout-seconds 600 --exit-code-on-failure`",
            "- Durable proof path after successful install-pair: `evidence_runs/mobile_apk_proof/latest/android_apk_install_pairing_proof.json`",
            "",
            "The helper redacts the owner token from printed commands and JSON output.",
            "",
            "## Docker Verification",
            "",
            "- Diagnose local Docker Engine: `npm --prefix ui run mobile:docker-check`",
            "- Raw Engine version probe: `docker version --format \"{{.Server.Version}}\"`",
            "- Build container image after Engine is available: `docker compose build`",
            "",
            "## Remaining External Gates",
            "",
        ]
    )
    for gate in bundle.remaining_external_gates:
        lines.append(f"- {gate}")
    lines.append("")
    return "\n".join(lines)


def _phone_verification_runbook(
    *,
    web_base: str,
    copied_apk_path: Path | None,
    copied_release_apk_path: Path | None,
    mobile_readiness_payload: dict[str, Any],
) -> dict[str, Any]:
    pairing_evidence = _check_evidence(mobile_readiness_payload, "owner_pairing_payload")
    apk_attempt = (
        mobile_readiness_payload.get("apk_install_pairing_attempt")
        if isinstance(mobile_readiness_payload.get("apk_install_pairing_attempt"), dict)
        else {}
    )
    phone_observed = bool(mobile_readiness_payload.get("phone_browser_observed"))
    phone_verified = bool(mobile_readiness_payload.get("phone_browser_verified"))
    pairing_context = {
        "pwa_api_base": (
            _string_or_none(pairing_evidence.get("selected_pairing_api_base"))
            or _string_or_none(pairing_evidence.get("first_pairing_api_base"))
        ),
        "direct_api_base": (
            _string_or_none(pairing_evidence.get("selected_direct_api_base"))
            or _string_or_none(pairing_evidence.get("first_direct_api_base"))
        ),
        "redacted_pairing_url": (
            _string_or_none(pairing_evidence.get("selected_pairing_url"))
            or _string_or_none(pairing_evidence.get("first_pairing_url"))
        ),
        "redacted_native_pairing_url": (
            _string_or_none(pairing_evidence.get("selected_native_pairing_url"))
            or _string_or_none(pairing_evidence.get("first_native_pairing_url"))
        ),
    }
    tested_quick_start_url = _quick_start_url(web_base)
    phone_quick_start_url = (
        _string_or_none(mobile_readiness_payload.get("phone_quick_start_url"))
        or _phone_reachable_quick_start_url(web_base, pairing_context, mobile_readiness_payload)
        or tested_quick_start_url
    )
    steps = [
        "On the PC, open Owner Access, turn LAN access ON, and click Show pairing token.",
        f"On the phone, open {phone_quick_start_url} or scan the Phone pairing QR shown in Owner Access.",
        "If the phone is not already paired, use the Phone pairing link/QR or paste the owner token when prompted.",
        "Open Quick Start on the phone and wait for Phone network proof to become Browser verified.",
        "On the PC, run python scripts/watch_mobile_phone_proof.py --exit-code-on-missing to wait for fresh verified phone proof.",
        f"Rerun python scripts/run_mobile_release_readiness.py --web-base {web_base} and confirm phone_browser_verified=true.",
        "For the Android APK gate, run npm --prefix ui run mobile:apk:wait-install-pair, then plug in/unlock the Android phone and approve USB debugging.",
        "Confirm evidence_runs/mobile_apk_proof/latest/android_apk_install_pairing_proof.json exists after install-pair succeeds.",
        "For signed distribution, confirm Android release signing is ready and run npm --prefix ui run mobile:apk:release.",
        "For the Docker gate, run npm --prefix ui run mobile:docker-check and verify Docker Engine answers before claiming container readiness.",
        "At any point, run npm --prefix ui run mobile:proof-session for the combined phone/APK/Docker proof checklist.",
        "Regenerate this release bundle after phone browser proof and APK/native pairing proof are verified.",
    ]
    return {
        "tested_web_base": web_base,
        "tested_quick_start_url": tested_quick_start_url,
        "phone_quick_start_url": phone_quick_start_url,
        "copied_debug_apk": str(copied_apk_path) if copied_apk_path is not None else None,
        "copied_release_apk": str(copied_release_apk_path) if copied_release_apk_path is not None else None,
        "apk_install_pairing_proof_path": "evidence_runs/mobile_apk_proof/latest/android_apk_install_pairing_proof.json",
        "current_phone_browser_observed": phone_observed,
        "current_phone_browser_verified": phone_verified,
        "current_phone_proof_fresh": bool(mobile_readiness_payload.get("phone_proof_fresh")),
        "current_phone_proof_age_seconds": mobile_readiness_payload.get("phone_proof_age_seconds"),
        "current_phone_proof_expires_at": _string_or_none(mobile_readiness_payload.get("phone_proof_expires_at")),
        "current_phone_observation_fresh": bool(mobile_readiness_payload.get("phone_observation_fresh")),
        "current_phone_observation_age_seconds": mobile_readiness_payload.get("phone_observation_age_seconds"),
        "current_phone_observation_expires_at": _string_or_none(mobile_readiness_payload.get("phone_observation_expires_at")),
        "current_apk_runtime_status": _string_or_none(mobile_readiness_payload.get("apk_runtime_status")) or _apk_runtime_status(mobile_readiness_payload),
        "current_apk_runtime_observed": bool(mobile_readiness_payload.get("apk_runtime_observed")),
        "current_apk_runtime_verified": bool(mobile_readiness_payload.get("apk_runtime_verified")),
        "current_apk_runtime_fresh": bool(mobile_readiness_payload.get("apk_runtime_fresh")),
        "current_apk_runtime_age_seconds": mobile_readiness_payload.get("apk_runtime_age_seconds"),
        "current_apk_runtime_expires_at": _string_or_none(mobile_readiness_payload.get("apk_runtime_expires_at")),
        "current_apk_install_pairing_attempt_status": _string_or_none(mobile_readiness_payload.get("apk_install_pairing_attempt_status")) or _apk_attempt_status(apk_attempt),
        "current_apk_install_pairing_attempt_fresh": bool(mobile_readiness_payload.get("apk_install_pairing_attempt_fresh") or apk_attempt.get("is_fresh")),
        "current_apk_install_pairing_attempt_age_seconds": mobile_readiness_payload.get("apk_install_pairing_attempt_age_seconds") or apk_attempt.get("age_seconds"),
        "current_apk_install_pairing_attempt_message": _string_or_none(mobile_readiness_payload.get("apk_install_pairing_attempt_message")) or _apk_attempt_message(apk_attempt),
        "current_android_release_signing_ready": bool(mobile_readiness_payload.get("android_release_signing_ready")),
        "current_android_release_signing_status": _string_or_none(mobile_readiness_payload.get("android_release_signing_status")) or "unknown",
        "current_android_release_signing_detail": _string_or_none(mobile_readiness_payload.get("android_release_signing_detail")),
        "current_android_release_apk_exists": bool(mobile_readiness_payload.get("android_release_apk_exists")),
        "current_android_release_apk_sha256": _string_or_none(mobile_readiness_payload.get("android_release_apk_sha256")),
        "pairing_context": pairing_context,
        "steps": steps,
        "verification_scope": PHONE_VERIFICATION_SCOPE,
        "claim_boundary": PHONE_VERIFICATION_SCOPE,
    }


def _check_evidence(payload: dict[str, Any], check_id: str) -> dict[str, Any]:
    check = _check_payload(payload, check_id)
    evidence = check.get("evidence")
    return evidence if isinstance(evidence, dict) else {}


def _check_payload(payload: dict[str, Any], check_id: str) -> dict[str, Any]:
    checks = payload.get("checks")
    if not isinstance(checks, list):
        return {}
    for check in checks:
        if not isinstance(check, dict) or check.get("check_id") != check_id:
            continue
        return check
    return {}


def _apk_attempt_status(attempt: dict[str, Any]) -> str:
    if not attempt:
        return "none"
    if not attempt.get("is_fresh"):
        return "stale"
    if attempt.get("android_apk_install_pairing_verified"):
        return "verified"
    if attempt.get("dry_run"):
        return "dry_run"
    if not attempt.get("install_success"):
        return "install_failed"
    if not attempt.get("native_pairing_success"):
        return "pairing_failed"
    return "not_verified"


def _apk_attempt_message(attempt: dict[str, Any]) -> str | None:
    if not attempt:
        return None
    status = _apk_attempt_status(attempt)
    install_message = _string_or_none(attempt.get("install_message"))
    native_message = _string_or_none(attempt.get("native_pairing_message"))
    if status == "install_failed":
        return install_message or native_message
    return native_message or install_message


def _apk_runtime_status(payload: dict[str, Any]) -> str:
    if bool(payload.get("apk_runtime_verified")):
        return "verified"
    if bool(payload.get("apk_runtime_observed")):
        return "observed"
    if bool(payload.get("apk_runtime_fresh")):
        return "observed"
    return "none"


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _runbook_freshness_line(runbook: dict[str, Any], prefix: str) -> str:
    age = runbook.get(f"{prefix}_age_seconds")
    expires_at = _string_or_none(runbook.get(f"{prefix}_expires_at"))
    if age is None and not expires_at:
        return "none"
    state = "fresh" if runbook.get(f"{prefix}_fresh") else "expired"
    parts = [state]
    if isinstance(age, int):
        parts.append(_format_age(age))
    if expires_at:
        parts.append(f"{'expires' if state == 'fresh' else 'expired'} at {expires_at}")
    return ", ".join(parts)


def _runbook_apk_attempt_line(runbook: dict[str, Any]) -> str:
    status = _string_or_none(runbook.get("current_apk_install_pairing_attempt_status")) or "none"
    if status == "none":
        return "none"
    parts = [status]
    parts.append("fresh" if runbook.get("current_apk_install_pairing_attempt_fresh") else "stale")
    age = runbook.get("current_apk_install_pairing_attempt_age_seconds")
    if isinstance(age, int):
        parts.append(_format_age(age))
    message = _string_or_none(runbook.get("current_apk_install_pairing_attempt_message"))
    if message:
        parts.append(message)
    return ", ".join(parts)


def _runbook_apk_runtime_line(runbook: dict[str, Any]) -> str:
    status = _string_or_none(runbook.get("current_apk_runtime_status")) or "none"
    if status == "none":
        return "none"
    parts = [status]
    parts.append("fresh" if runbook.get("current_apk_runtime_fresh") else "stale")
    age = runbook.get("current_apk_runtime_age_seconds")
    if isinstance(age, int):
        parts.append(_format_age(age))
    expires_at = _string_or_none(runbook.get("current_apk_runtime_expires_at"))
    if expires_at:
        parts.append(f"{'expires' if runbook.get('current_apk_runtime_fresh') else 'expired'} at {expires_at}")
    if status == "verified":
        parts.append("non-local phone/API path")
    elif runbook.get("current_apk_runtime_observed"):
        parts.append("runtime observed only")
    return ", ".join(parts)


def _runbook_release_signing_line(runbook: dict[str, Any]) -> str:
    status = _string_or_none(runbook.get("current_android_release_signing_status")) or "unknown"
    if runbook.get("current_android_release_signing_ready"):
        parts = ["ready"]
        parts.append("release APK present" if runbook.get("current_android_release_apk_exists") else "release APK build pending")
        digest = _string_or_none(runbook.get("current_android_release_apk_sha256"))
        if digest:
            parts.append(digest)
        return ", ".join(parts)
    detail = _string_or_none(runbook.get("current_android_release_signing_detail"))
    return f"{status}: {detail}" if detail else status


def _format_age(age_seconds: int) -> str:
    total = max(0, int(age_seconds))
    if total < 60:
        return f"{total}s old"
    if total < 3600:
        return f"{total // 60}m old"
    if total < 86400:
        hours = total // 3600
        minutes = (total % 3600) // 60
        return f"{hours}h {minutes}m old" if minutes else f"{hours}h old"
    days = total // 86400
    hours = (total % 86400) // 3600
    return f"{days}d {hours}h old" if hours else f"{days}d old"


def _phone_reachable_quick_start_url(
    web_base: str | None,
    pairing_context: dict[str, Any],
    readiness: dict[str, Any],
) -> str | None:
    pairing_url = _string_or_none(pairing_context.get("redacted_pairing_url"))
    from_pairing = _strip_fragment(pairing_url)
    if from_pairing and not _is_loopback_url(from_pairing):
        return from_pairing
    from_readiness = _string_or_none(readiness.get("phone_quick_start_url"))
    if from_readiness and not _is_loopback_url(from_readiness):
        return from_readiness
    from_api_base = _quick_start_from_api_base(_string_or_none(pairing_context.get("pwa_api_base")))
    if from_api_base and not _is_loopback_url(from_api_base):
        return from_api_base
    return _quick_start_url(web_base or "")


def _strip_fragment(url: str | None) -> str | None:
    if not url:
        return None
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return None
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", parts.query, ""))


def _quick_start_from_api_base(api_base: str | None) -> str | None:
    if not api_base:
        return None
    try:
        parts = urlsplit(api_base)
    except ValueError:
        return None
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return None
    return urlunsplit((parts.scheme, parts.netloc, "/", "page=quick-start", ""))


def _is_loopback_url(url: str | None) -> bool:
    if not url:
        return False
    try:
        host = (urlsplit(url).hostname or "").lower()
    except ValueError:
        return False
    return host == "localhost" or host.startswith("127.") or host == "::1"


def _quick_start_url(web_base: str) -> str:
    base = str(web_base or "").strip().rstrip("/")
    if not base:
        return "http://127.0.0.1:4173/?page=quick-start"
    if "?page=quick-start" in base:
        return base
    return f"{base}/?page=quick-start"
