"""Unit tests for scripts/verify_atlas_live.py."""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import verify_atlas_live  # noqa: E402


class _Resp:
    def __init__(self, status_code: int, payload: dict | None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no json body")
        return self._payload


def _realmode_payload(**overrides):
    payload = {
        "verdict": "REAL_PYTHIA_WEIGHTS_LOADED",
        "is_real_model": True,
        "fake_runtime_env": False,
        "model_loaded": True,
        "load_error": None,
        "manifest_is_real_model": True,
        "model_id": "EleutherAI/pythia-160m",
        "worker_version": "m2-real-pythia",
    }
    payload.update(overrides)
    return payload


def _install_router(monkeypatch, routes: dict[str, _Resp | Exception]):
    def _fake_get(url, headers=None, timeout=None):
        if url not in routes:
            raise AssertionError(f"unexpected GET {url}")
        entry = routes[url]
        if isinstance(entry, Exception):
            raise entry
        return entry

    monkeypatch.setattr(verify_atlas_live.httpx, "get", _fake_get)


def test_all_green_when_api_reports_real_model(monkeypatch, capsys):
    api_url = "https://api.example.com"
    _install_router(
        monkeypatch,
        {
            f"{api_url}/atlas/live/health": _Resp(200, {"status": "ok"}),
            f"{api_url}/atlas/live/health/realmode": _Resp(200, _realmode_payload()),
        },
    )

    exit_code = verify_atlas_live.main(["--api-url", api_url])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "[PASS] API realmode verdict == REAL_PYTHIA_WEIGHTS_LOADED" in out
    assert "[PASS] API realmode fake_runtime_env = false" in out
    assert "[PASS] API realmode model_loaded = true" in out
    assert "[PASS] API realmode load_error = null" in out
    assert "[PASS] API realmode manifest_is_real_model = true" in out
    assert "PASS:" in out


def test_red_when_worker_unreachable_from_api(monkeypatch, capsys):
    api_url = "https://api.example.com"
    _install_router(
        monkeypatch,
        {
            f"{api_url}/atlas/live/health": _Resp(
                503,
                {"detail": "atlas_live_worker_unavailable"},
            ),
        },
    )

    exit_code = verify_atlas_live.main(["--api-url", api_url])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "[PASS] API reachable" in out
    assert "[FAIL] Worker reachable via API" in out
    assert "atlas_live_worker_unavailable" in out


def test_red_when_worker_is_in_fake_mode(monkeypatch, capsys):
    api_url = "https://api.example.com"
    _install_router(
        monkeypatch,
        {
            f"{api_url}/atlas/live/health": _Resp(200, {"status": "ok"}),
            f"{api_url}/atlas/live/health/realmode": _Resp(
                200,
                _realmode_payload(
                    verdict="NOT_REAL_PYTHIA_WEIGHTS",
                    is_real_model=False,
                    fake_runtime_env=True,
                ),
            ),
        },
    )

    exit_code = verify_atlas_live.main(["--api-url", api_url])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "[FAIL] API realmode verdict == REAL_PYTHIA_WEIGHTS_LOADED" in out
    assert "[FAIL] API realmode is_real_model = true" in out
    assert "[FAIL] API realmode fake_runtime_env = false" in out


def test_red_when_model_is_unloaded(monkeypatch, capsys):
    api_url = "https://api.example.com"
    _install_router(
        monkeypatch,
        {
            f"{api_url}/atlas/live/health": _Resp(200, {"status": "ok"}),
            f"{api_url}/atlas/live/health/realmode": _Resp(
                200,
                _realmode_payload(
                    verdict="NOT_REAL_PYTHIA_WEIGHTS",
                    is_real_model=False,
                    model_loaded=False,
                ),
            ),
        },
    )

    exit_code = verify_atlas_live.main(["--api-url", api_url])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "[FAIL] API realmode model_loaded = true" in out


def test_red_when_load_error_is_present(monkeypatch, capsys):
    api_url = "https://api.example.com"
    _install_router(
        monkeypatch,
        {
            f"{api_url}/atlas/live/health": _Resp(200, {"status": "ok"}),
            f"{api_url}/atlas/live/health/realmode": _Resp(
                200,
                _realmode_payload(
                    verdict="NOT_REAL_PYTHIA_WEIGHTS",
                    is_real_model=False,
                    load_error="HF download timed out",
                ),
            ),
        },
    )

    exit_code = verify_atlas_live.main(["--api-url", api_url])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "[FAIL] API realmode load_error = null" in out
    assert "HF download timed out" in out


def test_red_when_manifest_is_not_real(monkeypatch, capsys):
    api_url = "https://api.example.com"
    _install_router(
        monkeypatch,
        {
            f"{api_url}/atlas/live/health": _Resp(200, {"status": "ok"}),
            f"{api_url}/atlas/live/health/realmode": _Resp(
                200,
                _realmode_payload(
                    verdict="NOT_REAL_PYTHIA_WEIGHTS",
                    is_real_model=False,
                    manifest_is_real_model=False,
                ),
            ),
        },
    )

    exit_code = verify_atlas_live.main(["--api-url", api_url])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "[FAIL] API realmode manifest_is_real_model = true" in out


def test_worker_direct_probe_forwards_bearer(monkeypatch, capsys):
    api_url = "https://api.example.com"
    worker_url = "https://worker.example.com"
    api_key = "secret"
    seen_headers: dict[str, dict] = {}

    def _fake_get(url, headers=None, timeout=None):
        seen_headers[url] = headers or {}
        if url == f"{api_url}/atlas/live/health":
            return _Resp(200, {"status": "ok"})
        if url == f"{api_url}/atlas/live/health/realmode":
            return _Resp(200, _realmode_payload())
        if url == f"{worker_url}/health/realmode":
            return _Resp(200, _realmode_payload())
        raise AssertionError(f"unexpected GET {url}")

    monkeypatch.setattr(verify_atlas_live.httpx, "get", _fake_get)

    exit_code = verify_atlas_live.main(
        ["--api-url", api_url, "--worker-url", worker_url, "--api-key", api_key]
    )
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Worker direct reachable" in out
    assert seen_headers[f"{worker_url}/health/realmode"]["Authorization"] == (
        f"Bearer {api_key}"
    )
    assert "Authorization" not in seen_headers[f"{api_url}/atlas/live/health"]


def test_api_transport_error_fails(monkeypatch, capsys):
    api_url = "https://api.example.com"
    _install_router(
        monkeypatch,
        {
            f"{api_url}/atlas/live/health": httpx.ConnectError("dns failure"),
        },
    )

    exit_code = verify_atlas_live.main(["--api-url", api_url])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "[FAIL] API reachable" in out
    assert "dns failure" in out
