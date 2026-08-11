from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from cas_forex import runtime_topology
from scripts import run_api_server


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_launcher_refuses_multiple_stateful_api_workers(capsys):
    result = run_api_server.main(["--workers", "2"])

    assert result == 2
    assert "requires exactly one stateful API worker" in capsys.readouterr().err


def test_worker_count_contract_accepts_exactly_one():
    assert runtime_topology.validate_api_worker_count(1) == 1
    with pytest.raises(runtime_topology.RuntimeTopologyError):
        runtime_topology.validate_api_worker_count(0)
    with pytest.raises(runtime_topology.RuntimeTopologyError):
        runtime_topology.validate_api_worker_count(3)


def test_launcher_explicitly_supplies_windows_selector_loop_factory():
    loop = run_api_server._windows_selector_loop_factory()

    try:
        assert isinstance(loop, run_api_server.asyncio.SelectorEventLoop)
    finally:
        loop.close()


def test_windows_launcher_defaults_to_proactor_and_keeps_selector_fallback(monkeypatch):
    monkeypatch.delenv("CAS_FOREX_WINDOWS_EVENT_LOOP", raising=False)

    args = run_api_server._parse_args([])

    assert args.windows_event_loop == "proactor"
    assert run_api_server._uvicorn_loop_spec("proactor", platform_name="nt") == "asyncio"
    assert run_api_server._uvicorn_loop_spec("selector", platform_name="nt") == (
        "scripts.run_api_server:_windows_selector_loop_factory"
    )
    assert run_api_server._uvicorn_loop_spec("selector", platform_name="posix") == "asyncio"


def test_launcher_passes_selected_windows_loop_to_uvicorn(monkeypatch):
    captured = {}
    fake_uvicorn = SimpleNamespace(
        run=lambda app, **kwargs: captured.update({"app": app, **kwargs})
    )
    monkeypatch.setitem(sys.modules, "uvicorn", fake_uvicorn)
    monkeypatch.setenv("CAS_FOREX_API_EVENT_LOOP", "test-placeholder")

    result = run_api_server.main(
        ["--workers", "1", "--windows-event-loop", "selector"]
    )

    assert result == 0
    assert captured["app"] == "api.server:app"
    assert captured["loop"] == "scripts.run_api_server:_windows_selector_loop_factory"
    assert run_api_server.os.environ["CAS_FOREX_API_EVENT_LOOP"] == "SELECTOR"


def test_required_runtime_owner_refuses_startup_when_lease_is_held(monkeypatch):
    monkeypatch.setattr(runtime_topology, "acquire_runtime_owner", lambda _path: False)

    with pytest.raises(
        runtime_topology.RuntimeTopologyError,
        match="already owns the autonomous runtime",
    ):
        runtime_topology.require_runtime_owner(Path("held.lock"))


def test_runtime_owner_lock_excludes_another_process_and_releases(tmp_path):
    lock_path = tmp_path / "runtime-owner.lock"
    code = (
        "from pathlib import Path; "
        "from cas_forex.runtime_topology import acquire_runtime_owner; "
        "import sys; print(str(acquire_runtime_owner(Path(sys.argv[1]))).lower())"
    )
    try:
        assert runtime_topology.acquire_runtime_owner(lock_path) is True
        blocked = subprocess.run(
            [sys.executable, "-c", code, str(lock_path)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
        assert blocked.stdout.strip() == "false"
    finally:
        runtime_topology.release_runtime_owner()

    acquired = subprocess.run(
        [sys.executable, "-c", code, str(lock_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    )
    assert acquired.stdout.strip() == "true"


def test_topology_status_records_single_owner_evidence(tmp_path):
    lock_path = tmp_path / "runtime-owner.lock"
    status_path = tmp_path / "runtime-topology.json"
    try:
        assert runtime_topology.acquire_runtime_owner(lock_path) is True
        packet = runtime_topology.write_runtime_topology_status(
            status_path=status_path,
            worker_count=1,
            host="0.0.0.0",
            port=8765,
        )
    finally:
        runtime_topology.release_runtime_owner()

    persisted = json.loads(status_path.read_text(encoding="utf-8"))
    assert packet["status"] == "SINGLE_OWNER_READY"
    assert packet["claim_status"] == "ACCEPT"
    assert packet["runtime_owner"] is True
    assert packet["multi_worker_supported"] is False
    assert persisted["runtime_owner_pid"] == packet["runtime_owner_pid"]


def test_topology_status_exposes_active_event_loop_policy(monkeypatch):
    monkeypatch.setenv("CAS_FOREX_API_EVENT_LOOP", "PROACTOR")

    packet = runtime_topology.build_runtime_topology_status()

    assert packet["event_loop_policy"] == "PROACTOR"
