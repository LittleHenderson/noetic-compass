"""Tests for the final owner-facing mobile verification handoff."""

from __future__ import annotations

import json
from pathlib import Path

import cas_forex.mobile_final_verification as final_module
import scripts.run_mobile_final_verification as final_cli
from cas_forex.mobile_phone_verifier import PhoneProofWatchStatus
from cas_forex.mobile_proof_session import MobileProofGate, MobileProofSession


def _proof_session(
    *,
    package_ready: bool = True,
    phone_verified: bool = False,
    apk_verified: bool = False,
    docker_available: bool = True,
) -> MobileProofSession:
    gates = (
        MobileProofGate(
            gate_id="phone_browser_proof",
            title="Real phone Quick Start proof",
            satisfied=phone_verified,
            command="npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing",
            target_url="http://10.0.0.6:4173/?page=quick-start#cas_owner_token=secret-token",
            detail="Open Quick Start from the real phone over LAN.",
        ),
        MobileProofGate(
            gate_id="android_apk_install_pairing",
            title="Android APK install and native pairing proof",
            satisfied=apk_verified,
            command="npm --prefix ui run mobile:apk:wait-install-pair",
            target_url=None,
            detail="Plug in, unlock, and authorize the Android phone.",
        ),
        MobileProofGate(
            gate_id="docker_engine",
            title="Docker Engine proof",
            satisfied=docker_available,
            command="npm --prefix ui run mobile:docker-check",
            target_url=None,
            detail="Docker Engine answered.",
        ),
    )
    return MobileProofSession(
        report_kind="cas_forex_mobile_external_proof_session",
        generated_at="2026-07-05T00:00:00+00:00",
        status="external_proof_pending",
        summary="Phone package is ready; external proof remains.",
        package_ready_for_phone_install=package_ready,
        phone_quick_start_url="http://10.0.0.6:4173/?page=quick-start",
        tested_quick_start_url="http://10.0.0.6:4173/?page=quick-start",
        phone_proof_target_url="http://10.0.0.6:4173/?page=quick-start",
        phone_proof_target_kind="quick_start_with_live_pairing_if_needed",
        pairing_context={
            "redacted_pairing_url": (
                "http://10.0.0.6:4173/?page=quick-start"
                "#cas_owner_token=secret-token&cas_api_base=http%3A%2F%2F10.0.0.6%3A4173%2Fapi%2Fforex"
            )
        },
        phone_pairing_handoff=None,
        phone_browser_verified=phone_verified,
        phone_browser_observed=phone_verified,
        apk_install_pairing_verified=apk_verified,
        apk_install_pairing_attempt_status="install_failed",
        paired_api_bases_reachable=True,
        paired_api_bases_status="pass",
        paired_api_bases_detail="paired API bases answered",
        docker_available=docker_available,
        docker_engine_status="pass" if docker_available else "external",
        docker_engine_detail="Docker Engine answered." if docker_available else "Docker is unavailable.",
        docker_desktop_install_command="npm --prefix ui run mobile:docker-install",
        docker_desktop_elevated_install_command="npm --prefix ui run mobile:docker-install-elevated",
        docker_desktop_install_attempt_status="installed_or_started",
        docker_desktop_install_attempt_detail=None,
        docker_desktop_install_attempt_installer_exit_code=None,
        phone_watch_status={},
        proof_state={},
        release_artifact_summary={"android_debug_apk_sha256": "debug-sha"},
        owner_commands={
            "mobile_proof_session": "npm --prefix ui run mobile:proof-session",
            "phone_proof_watcher": "npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing",
            "apk_wait_install_pair": "npm --prefix ui run mobile:apk:wait-install-pair",
            "docker_engine_diagnose": "npm --prefix ui run mobile:docker-check",
        },
        gates=gates,
        remaining_external_gates=tuple(gate.title for gate in gates if not gate.satisfied),
        source_session_status="external_proof_pending",
        source_session_summary="Phone package is ready; external proof remains.",
    )


def _phone_watch_status(*, verified: bool = False) -> PhoneProofWatchStatus:
    return PhoneProofWatchStatus(
        status="VERIFIED" if verified else "MISSING",
        phone_browser_verified=verified,
        phone_browser_observed=verified,
        phone_quick_start_url="http://10.0.0.6:4173/?page=quick-start",
        tested_quick_start_url="http://10.0.0.6:4173/?page=quick-start",
        phone_proof_watcher_command="npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing",
        mobile_readiness_command="npm --prefix ui run mobile:readiness -- --web-base http://10.0.0.6:4173",
        active_evidence_kind="verified_phone_proof" if verified else "none",
        installed_mode_detected=verified,
        effective_client_host="10.0.0.44" if verified else None,
        client_host_source="x-forwarded-for" if verified else None,
        generated_at="2026-07-05T00:00:00+00:00" if verified else None,
        phone_proof_fresh=verified,
        phone_proof_age_seconds=0 if verified else None,
        phone_proof_expires_at="2026-07-06T00:00:00+00:00" if verified else None,
        phone_observation_fresh=False,
        phone_observation_age_seconds=None,
        phone_observation_expires_at=None,
        readiness_source_path=None,
        summary="verified" if verified else "missing",
        next_steps=("Open Quick Start on the phone.",),
    )


def test_mobile_final_verification_reports_pending_phone_first(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(final_module, "build_mobile_proof_session", lambda **kwargs: _proof_session())

    report = final_module.build_mobile_final_verification(workspace_root=tmp_path)
    payload = final_module.mobile_final_verification_to_dict(report)
    rendered = final_module.render_mobile_final_verification(report)

    assert payload["report_kind"] == final_module.REPORT_KIND
    assert payload["status"] == "external_proof_pending"
    assert payload["remaining_external_gates"] == [
        "Real phone Quick Start proof",
        "Android APK install and native pairing proof",
    ]
    assert "Open http://10.0.0.6:4173/?page=quick-start on the real phone" in payload["next_owner_step"]
    assert payload["owner_commands"]["mobile_final_verification"] == "npm --prefix ui run mobile:finish"
    assert payload["owner_commands"]["mobile_final_verification_watch_all"] == "npm --prefix ui run mobile:finish -- --watch-all"
    assert payload["owner_commands"]["mobile_final_verification_watch_all_live_links"] == (
        "npm --prefix ui run mobile:finish -- --watch-all --print-live-pairing-links"
    )
    assert "Final verification: npm --prefix ui run mobile:finish" in rendered
    assert "Watch all final gates: npm --prefix ui run mobile:finish -- --watch-all" in rendered
    assert "Watch all final gates with live links: npm --prefix ui run mobile:finish -- --watch-all --print-live-pairing-links" in rendered
    assert "cas_owner_token=REDACTED" in json.dumps(payload)
    assert "secret-token" not in json.dumps(payload)
    assert "secret-token" not in rendered


def test_mobile_final_verification_next_step_moves_to_apk_after_phone(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        final_module,
        "build_mobile_proof_session",
        lambda **kwargs: _proof_session(phone_verified=True),
    )

    report = final_module.build_mobile_final_verification(workspace_root=tmp_path)

    assert report.status == "external_proof_pending"
    assert report.remaining_external_gates == ("Android APK install and native pairing proof",)
    assert "npm --prefix ui run mobile:apk:wait-install-pair" in report.next_owner_step


def test_mobile_final_verification_writes_redacted_artifacts(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        final_module,
        "build_mobile_proof_session",
        lambda **kwargs: _proof_session(phone_verified=True, apk_verified=True, docker_available=True),
    )

    report = final_module.build_mobile_final_verification(workspace_root=tmp_path)
    paths = final_module.write_mobile_final_verification(report, workspace_root=tmp_path)
    saved_json = Path(paths["json_path"]).read_text(encoding="utf-8")
    saved_readme = Path(paths["readme_path"]).read_text(encoding="utf-8")

    assert report.status == "verified"
    assert "mobile_final_verification.json" in saved_json
    assert "Final mobile verification is complete." in saved_readme
    assert "secret-token" not in saved_json
    assert "secret-token" not in saved_readme


def test_mobile_final_verification_watch_all_skips_apk_until_phone_is_verified(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    monkeypatch.setattr(
        final_cli,
        "_build_report",
        lambda args, watch_phone: final_module.build_mobile_final_verification(workspace_root=tmp_path),  # noqa: ARG005
    )
    monkeypatch.setattr(final_module, "build_mobile_proof_session", lambda **kwargs: _proof_session())
    called: list[bool] = []
    monkeypatch.setattr(final_cli, "_run_apk_install_pairing", lambda **kwargs: called.append(True) or {})

    assert final_cli.main(["--watch-all", "--no-write", "--json", "--timeout-seconds", "0"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["phone_browser_verified"] is False
    assert payload["apk_install_pairing_verified"] is False
    assert called == []


def test_mobile_final_verification_watch_all_prints_phone_wait_handoff(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    monkeypatch.setattr(
        final_cli,
        "_build_report",
        lambda args, watch_phone: final_module.build_mobile_final_verification(workspace_root=tmp_path),  # noqa: ARG005
    )
    monkeypatch.setattr(final_module, "build_mobile_proof_session", lambda **kwargs: _proof_session())
    monkeypatch.setattr(final_cli, "phone_proof_watch_status", lambda workspace_root=".": _phone_watch_status())
    monkeypatch.setattr(final_cli, "_run_apk_install_pairing", lambda **kwargs: {})

    assert final_cli.main(["--watch-all", "--no-write", "--timeout-seconds", "0"]) == 0

    out = capsys.readouterr().out
    assert "Initial phone proof status:" in out
    assert "Waiting up to 0s for verified real-phone proof" in out
    assert "Final phone proof status:" in out
    assert "Phone Quick Start URL: http://10.0.0.6:4173/?page=quick-start" in out
    assert "APK install/native pairing was not started because verified phone proof is still missing." in out


def test_mobile_final_verification_can_print_live_pairing_links_terminal_only(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    monkeypatch.setattr(
        final_cli,
        "_build_report",
        lambda args, watch_phone: final_module.build_mobile_final_verification(workspace_root=tmp_path),  # noqa: ARG005
    )
    monkeypatch.setattr(final_module, "build_mobile_proof_session", lambda **kwargs: _proof_session())
    monkeypatch.setattr(final_cli, "phone_proof_watch_status", lambda workspace_root=".": _phone_watch_status())
    monkeypatch.setattr(final_cli, "_run_apk_install_pairing", lambda **kwargs: {})
    monkeypatch.setattr(
        final_cli,
        "pairing_payload",
        lambda: {
            "lan_mode_enabled": True,
            "pairing_urls": [
                "http://10.0.0.6:4173/?page=quick-start#cas_owner_token=secret-token&cas_api_base=http%3A%2F%2F10.0.0.6%3A4173%2Fapi%2Fforex"
            ],
            "native_pairing_urls": [
                "casforex://pair?cas_owner_token=secret-token&cas_api_base=http%3A%2F%2F10.0.0.6%3A8765%2Fapi%2Fforex&page=quick-start"
            ],
            "pairing_api_bases": ["http://10.0.0.6:4173/api/forex"],
            "direct_api_bases": ["http://10.0.0.6:8765/api/forex"],
        },
    )

    assert final_cli.main(
        ["--watch-all", "--no-write", "--timeout-seconds", "0", "--print-live-pairing-links"]
    ) == 0

    out = capsys.readouterr().out
    assert "Live pairing links (terminal only; not written to evidence):" in out
    assert "LAN access enabled: true" in out
    assert "PWA phone pairing links:" in out
    assert "Android APK pairing links:" in out
    assert "cas_owner_token=secret-token" in out
    assert "PWA/proxy: http://10.0.0.6:4173/api/forex" in out
    assert "APK/direct: http://10.0.0.6:8765/api/forex" in out


def test_mobile_final_verification_json_mode_does_not_print_live_pairing_links(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    monkeypatch.setattr(
        final_cli,
        "_build_report",
        lambda args, watch_phone: final_module.build_mobile_final_verification(workspace_root=tmp_path),  # noqa: ARG005
    )
    monkeypatch.setattr(final_module, "build_mobile_proof_session", lambda **kwargs: _proof_session())
    calls: list[bool] = []
    monkeypatch.setattr(final_cli, "pairing_payload", lambda: calls.append(True) or {})

    assert final_cli.main(
        ["--watch-all", "--no-write", "--json", "--timeout-seconds", "0", "--print-live-pairing-links"]
    ) == 0

    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["status"] == "external_proof_pending"
    assert calls == []
    assert "Live pairing links" not in out
    assert "secret-token" not in out


def test_mobile_final_verification_watch_all_uses_longer_default_phone_timeout() -> None:
    watch_all_args = final_cli._parse_args(["--watch-all"])
    watch_phone_args = final_cli._parse_args(["--watch-phone"])
    explicit_args = final_cli._parse_args(["--watch-all", "--timeout-seconds", "12"])

    assert final_cli._effective_phone_timeout(watch_all_args) == 900.0
    assert final_cli._effective_phone_timeout(watch_phone_args) == 180.0
    assert final_cli._effective_phone_timeout(explicit_args) == 12.0


def test_mobile_final_verification_run_apk_pairing_after_phone_is_verified(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    calls: list[dict] = []
    monkeypatch.setattr(
        final_module,
        "build_mobile_proof_session",
        lambda **kwargs: _proof_session(phone_verified=True, apk_verified=len(calls) > 0),
    )

    def fake_build_report(args, *, watch_phone: bool):  # noqa: ARG001
        return final_module.build_mobile_final_verification(workspace_root=tmp_path)

    def fake_run_apk_install_pairing(**kwargs):
        calls.append(kwargs)
        return {"android_apk_install_pairing_proof": {"android_apk_install_pairing_verified": True}}

    monkeypatch.setattr(final_cli, "_build_report", fake_build_report)
    monkeypatch.setattr(final_cli, "_run_apk_install_pairing", fake_run_apk_install_pairing)

    assert final_cli.main(["--run-apk-pairing", "--no-write", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["phone_browser_verified"] is True
    assert payload["apk_install_pairing_verified"] is True
    assert calls and calls[0]["wait_timeout_seconds"] == 600.0
