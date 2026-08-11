from __future__ import annotations

import json
import subprocess
from pathlib import Path

from cas_forex import docker_desktop_install as installer


def test_docker_desktop_install_attempt_records_admin_elevation(monkeypatch, tmp_path: Path) -> None:
    commands: list[tuple[str, ...]] = []

    def fake_run(command, **kwargs):
        commands.append(tuple(command))
        return subprocess.CompletedProcess(
            command,
            4294967291,
            stdout=(
                "The installer will request to run as administrator. Expect a prompt.\n"
                "Installer failed with exit code: 4294967291"
            ),
            stderr="",
        )

    monkeypatch.setattr(installer.shutil, "which", lambda name: "C:/Users/wakil/AppData/Local/Microsoft/WindowsApps/winget.exe" if name == "winget" else None)
    monkeypatch.setattr(installer.subprocess, "run", fake_run)

    report = installer.run_docker_desktop_install_attempt(
        workspace_root=tmp_path,
        timeout_seconds=5,
    )

    assert commands
    assert commands[0][0].endswith("winget.exe")
    assert "Docker.DockerDesktop" in commands[0]
    assert installer.elevated_install_command_string() == "npm --prefix ui run mobile:docker-install-elevated"
    assert report["report_kind"] == installer.REPORT_KIND
    assert report["status"] == "admin_elevation_required"
    assert report["success"] is False
    assert report["admin_elevation_required"] is True
    assert report["returncode"] == 4294967291
    assert report["installer_exit_code"] == 4294967291
    assert report["elevated_install_command"] == "npm --prefix ui run mobile:docker-install-elevated"
    assert "administrator elevation" in report["detail"]
    written = Path(report["written_path"])
    assert written.exists()
    assert json.loads(written.read_text(encoding="utf-8"))["status"] == "admin_elevation_required"
    latest = installer.latest_docker_desktop_install_attempt(workspace_root=tmp_path)
    assert latest and latest["status"] == "admin_elevation_required"
    rendered = installer.render_docker_desktop_install_attempt(report)
    assert "Elevated command: npm --prefix ui run mobile:docker-install-elevated" in rendered


def test_docker_desktop_install_attempt_records_missing_winget(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(installer.shutil, "which", lambda name: None)

    report = installer.run_docker_desktop_install_attempt(workspace_root=tmp_path)

    assert report["status"] == "winget_unavailable"
    assert report["success"] is False
    assert report["winget_path"] is None
    assert report["elevated_install_command"] == "npm --prefix ui run mobile:docker-install-elevated"
    assert Path(report["written_path"]).exists()


def test_latest_docker_desktop_install_attempt_reads_powershell_utf8_bom(tmp_path: Path) -> None:
    evidence_dir = tmp_path / installer.DEFAULT_OUTPUT_DIR
    evidence_dir.mkdir(parents=True)
    path = evidence_dir / installer.DEFAULT_OUTPUT_FILE
    path.write_text(
        json.dumps(
            {
                "report_kind": installer.REPORT_KIND,
                "status": "elevation_prompt_started",
                "success": False,
            }
        ),
        encoding="utf-8-sig",
    )

    latest = installer.latest_docker_desktop_install_attempt(workspace_root=tmp_path)

    assert latest is not None
    assert latest["status"] == "elevation_prompt_started"
    assert latest["source_path"] == str(path)
