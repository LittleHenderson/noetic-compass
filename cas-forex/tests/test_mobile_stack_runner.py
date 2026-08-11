"""Tests for the CAS Forex mobile stack readiness runner."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Sequence

import pytest

from cas_forex.mobile_release_readiness import MobileReadinessCheck, MobileReleaseReadinessReport
from cas_forex.mobile_stack_runner import render_stack_report, run_mobile_stack_readiness


class FakeProcess:
    def __init__(self, pid: int) -> None:
        self.pid = pid
        self.terminated = False
        self.killed = False

    def poll(self):
        return None if not self.terminated and not self.killed else 0

    def terminate(self) -> None:
        self.terminated = True

    def wait(self, timeout: float | None = None) -> int:  # noqa: ARG002
        return 0

    def kill(self) -> None:
        self.killed = True


def test_mobile_stack_refuses_multiple_stateful_api_workers(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="exactly one stateful API worker"):
        run_mobile_stack_readiness(
            workspace_root=tmp_path,
            output_dir=tmp_path / "out",
            api_workers=2,
            start_missing=False,
        )


def _ready_report() -> MobileReleaseReadinessReport:
    return MobileReleaseReadinessReport(
        generated_at="2026-07-05T00:00:00+00:00",
        web_base="http://10.0.0.6:4173",
        phone_quick_start_url="http://10.0.0.6:4173/?page=quick-start",
        verification_commands={
            "phone_proof_watcher": "npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing",
            "mobile_readiness": "npm --prefix ui run mobile:readiness -- --web-base http://10.0.0.6:4173",
            "mobile_stack": "npm --prefix ui run mobile:stack -- --web-base http://10.0.0.6:4173",
            "release_bundle": "python scripts/build_web_phone_release_bundle.py --web-base http://10.0.0.6:4173 --exit-code-on-failure",
            "apk_debug_build": "npm --prefix ui run mobile:apk:debug",
            "apk_device_list": "npm --prefix ui run mobile:apk:devices",
            "apk_install_pair": "npm --prefix ui run mobile:apk:install-pair",
            "docker_engine_check": 'docker version --format "{{.Server.Version}}"',
            "docker_compose_build": "docker compose build",
        },
        next_verification_actions=(
            {
                "action_id": "phone_browser_proof",
                "status": "pending",
                "title": "Verify real phone Quick Start",
                "detail": "Open Quick Start from the phone.",
                "command": "npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing",
                "target_url": "http://10.0.0.6:4173/?page=quick-start",
                "secondary_commands": [],
                "blocks_completion": True,
            },
        ),
        package_ready_for_phone_install=True,
        physical_phone_verified=False,
        docker_available=False,
        checks=(
            MobileReadinessCheck(
                check_id="web_phone_smoke",
                status="pass",
                success=True,
                detail="ok",
                evidence={},
            ),
        ),
        smoke_report={"failed": 0},
        device_probe=None,
        native_pairing_launch=None,
        summary="ready",
        remaining_external_gates=("phone", "docker"),
    )


def test_mobile_stack_runner_reuses_running_api_and_preview(tmp_path: Path) -> None:
    started: list[tuple[str, ...]] = []

    def starter(args: Sequence[str], cwd: Path, log_path: Path) -> subprocess.Popen:  # noqa: ARG001
        started.append(tuple(args))
        return FakeProcess(1234)  # type: ignore[return-value]

    report = run_mobile_stack_readiness(
        workspace_root=tmp_path,
        output_dir=tmp_path / "out",
        web_base="http://10.0.0.6:4173",
        url_checker=lambda url, timeout: True,  # noqa: ARG005
        readiness_runner=lambda **kwargs: _ready_report(),
        process_starter=starter,
    )

    assert report.api_ready is True
    assert report.web_ready is True
    assert report.package_ready_for_phone_install is True
    assert report.phone_quick_start_url == "http://10.0.0.6:4173/?page=quick-start"
    rendered = render_stack_report(report)
    assert "Phone Quick Start URL: http://10.0.0.6:4173/?page=quick-start" in rendered
    assert "Phone proof freshness: none" in rendered
    assert "Next verification actions:" in rendered
    assert "Verify real phone Quick Start" in rendered
    assert report.processes == ()
    assert started == []
    assert (tmp_path / "out" / "mobile_release_readiness.json").exists()


def test_mobile_stack_runner_uses_readiness_phone_url_when_web_base_is_loopback(tmp_path: Path) -> None:
    report = run_mobile_stack_readiness(
        workspace_root=tmp_path,
        output_dir=tmp_path / "out",
        web_base="http://127.0.0.1:4173",
        url_checker=lambda url, timeout: True,  # noqa: ARG005
        readiness_runner=lambda **kwargs: _ready_report(),
    )

    rendered = render_stack_report(report)

    assert report.web_base == "http://127.0.0.1:4173"
    assert report.phone_quick_start_url == "http://10.0.0.6:4173/?page=quick-start"
    assert "Web base: http://127.0.0.1:4173" in rendered
    assert "Phone Quick Start URL: http://10.0.0.6:4173/?page=quick-start" in rendered
    assert "Phone Quick Start URL: http://127.0.0.1:4173/?page=quick-start" not in rendered


def test_mobile_stack_runner_starts_missing_services_with_lan_hosts(tmp_path: Path) -> None:
    started: list[tuple[str, ...]] = []
    ready = {"api": False, "web": False}

    def checker(url: str, timeout: float) -> bool:  # noqa: ARG001
        return ready["api"] if ":8765" in url else ready["web"]

    def starter(args: Sequence[str], cwd: Path, log_path: Path) -> subprocess.Popen:  # noqa: ARG001
        started.append(tuple(args))
        if any(str(part).replace("\\", "/").endswith("run_api_server.py") for part in args):
            ready["api"] = True
        else:
            ready["web"] = True
        return FakeProcess(4000 + len(started))  # type: ignore[return-value]

    report = run_mobile_stack_readiness(
        workspace_root=tmp_path,
        output_dir=tmp_path / "out",
        web_base="http://10.0.0.6:4173",
        python_executable="python-test",
        npm_executable="npm-test",
        timeout_seconds=0.01,
        poll_seconds=0.001,
        url_checker=checker,
        readiness_runner=lambda **kwargs: _ready_report(),
        process_starter=starter,
    )

    assert report.api_ready is True
    assert report.web_ready is True
    assert len(report.processes) == 2
    assert started[0][0] == "python-test"
    assert started[0][1].replace("\\", "/") == "scripts/run_api_server.py"
    assert started[0][2:4] == ("--host", "0.0.0.0")
    assert "--port" in started[0]
    assert "8765" in started[0]
    assert "--workers" in started[0]
    assert "1" in started[0]
    assert started[1][:6] == ("npm-test", "--prefix", "ui", "run", "preview", "--")
    assert "--host" in started[1]
    assert "0.0.0.0" in started[1]


def test_mobile_stack_runner_can_stop_processes_it_started(tmp_path: Path) -> None:
    processes = [FakeProcess(5001), FakeProcess(5002)]
    all_processes = list(processes)

    def starter(args: Sequence[str], cwd: Path, log_path: Path) -> subprocess.Popen:  # noqa: ARG001
        return processes.pop(0)  # type: ignore[return-value]

    report = run_mobile_stack_readiness(
        workspace_root=tmp_path,
        output_dir=tmp_path / "out",
        web_base="http://10.0.0.6:4173",
        keep_running=False,
        timeout_seconds=0.01,
        poll_seconds=0.001,
        url_checker=lambda url, timeout: False,  # noqa: ARG005
        readiness_runner=lambda **kwargs: _ready_report(),
        process_starter=starter,
    )

    assert report.keep_running is False
    assert len(report.processes) == 2
    assert all(process.started for process in report.processes)
    assert all(process.terminated for process in all_processes)
