"""Unit tests for scripts/verify_atlas_live.py.

Covers exit codes + check ordering by mocking httpx.get to return canned
responses for the API + worker endpoints.
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest

# Make scripts/ importable as a package-less module.
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


def _install_router(monkeypatch, routes: dict[str, _Resp | Exception]):
    """Route httpx.get(url) -> routes[url], raising if url is unknown."""

    def _fake_get(url, headers=None, timeout=None):
        if url not in routes:
            raise AssertionError(f"unexpected GET {url} (known: {list(routes)})")
        entry = routes[url]
        if isinstance(entry, Exception):
            raise entry
        return entry

    monkeypatch.setattr(verify_atlas_live.httpx, "get", _fake_get)


# --- happy path ----------------------------------------------------------------


def test_all_green_when_api_reports_real_model(monkeypatch, capsys):
    api_url = "https://api.example.com"
    routes = {
        f"{api_url}/atlas/live/health": _Resp(
            200,
            {
                "status": "ok",
                "worker_version": "m2-real-pythia",
                "model_id": "EleutherAI/pythia-160m",
                "is_real_model": True,
                "model_loaded": True,
                "load_error": None,
            },
        ),
        f"{api_url}/atlas/live/health/realmode": _Resp(
            200,
            {
                "is_real_model": True,
                "fake_runtime_env": False,
                "model_id": "EleutherAI/pythia-160m",
                "model_loaded": True,
                "worker_version": "m2-real-pythia",
            },
        ),
    }
    _install_router(monkeypatch, routes)

    exit_code = verify_atlas_live.main(["--api-url", api_url])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "API reachable" in out
    assert "is_real_model = true" in out
    assert "fake_runtime_env = false" in out
    assert "EleutherAI/pythia-160m" in out
    assert "PASS" in out
    # No red checks in a green run.
    assert " [✗]" not in out


# --- fault matrix --------------------------------------------------------------


def test_red_when_api_unreachable(monkeypatch, capsys):
    api_url = "https://api.example.com"
    routes = {
        f"{api_url}/atlas/live/health": httpx.ConnectError("simulated dns failure"),
    }
    _install_router(monkeypatch, routes)

    exit_code = verify_atlas_live.main(["--api-url", api_url])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "FAIL" in out
    assert "[✗] API reachable" in out


def test_red_when_worker_url_disabled(monkeypatch, capsys):
    """503 with detail=atlas_live_disabled -> red on 'Worker URL configured'."""
    api_url = "https://api.example.com"
    routes = {
        f"{api_url}/atlas/live/health": _Resp(503, {"detail": "atlas_live_disabled"}),
    }
    _install_router(monkeypatch, routes)

    exit_code = verify_atlas_live.main(["--api-url", api_url])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "[✓] API reachable" in out
    assert "[✗] Worker URL configured" in out
    assert "atlas_live_disabled" in out


def test_red_when_worker_unreachable_from_api(monkeypatch, capsys):
    """503 atlas_live_worker_unavailable -> API up, worker down."""
    api_url = "https://api.example.com"
    routes = {
        f"{api_url}/atlas/live/health": _Resp(
            503, {"detail": "atlas_live_worker_unavailable"}
        ),
    }
    _install_router(monkeypatch, routes)

    exit_code = verify_atlas_live.main(["--api-url", api_url])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "[✓] API reachable" in out
    assert "[✓] Worker URL configured" in out
    assert "[✗] Worker reachable (via API)" in out


def test_red_when_worker_is_in_fake_mode(monkeypatch, capsys):
    api_url = "https://api.example.com"
    routes = {
        f"{api_url}/atlas/live/health": _Resp(
            200,
            {
                "status": "ok",
                "worker_version": "m2-real-pythia",
                "model_id": "EleutherAI/pythia-160m",
                "is_real_model": False,
                "model_loaded": False,
                "load_error": None,
            },
        ),
        f"{api_url}/atlas/live/health/realmode": _Resp(
            200,
            {
                "is_real_model": False,
                "fake_runtime_env": True,
                "model_id": "EleutherAI/pythia-160m",
                "model_loaded": False,
                "worker_version": "m2-real-pythia",
            },
        ),
    }
    _install_router(monkeypatch, routes)

    exit_code = verify_atlas_live.main(["--api-url", api_url])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "[✗] is_real_model = true" in out
    assert "[✗] fake_runtime_env = false" in out


def test_red_when_model_id_mismatches(monkeypatch, capsys):
    api_url = "https://api.example.com"
    routes = {
        f"{api_url}/atlas/live/health": _Resp(
            200, {"status": "ok", "model_id": "wrong"}
        ),
        f"{api_url}/atlas/live/health/realmode": _Resp(
            200,
            {
                "is_real_model": True,
                "fake_runtime_env": False,
                "model_id": "EleutherAI/pythia-70m",
                "model_loaded": True,
                "worker_version": "m2-real-pythia",
            },
        ),
    }
    _install_router(monkeypatch, routes)

    exit_code = verify_atlas_live.main(["--api-url", api_url])
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "model_id == EleutherAI/pythia-160m" in out
    assert "[✗] model_id == EleutherAI/pythia-160m" in out


# --- worker-direct path --------------------------------------------------------


def test_worker_direct_probe_green(monkeypatch, capsys):
    api_url = "https://api.example.com"
    worker_url = "https://worker.example.com"
    api_key = "secret-bearer"
    seen_headers: dict = {}

    def _fake_get(url, headers=None, timeout=None):
        seen_headers[url] = headers or {}
        if url == f"{api_url}/atlas/live/health":
            return _Resp(
                200,
                {
                    "status": "ok",
                    "model_id": "EleutherAI/pythia-160m",
                    "is_real_model": True,
                },
            )
        if url == f"{api_url}/atlas/live/health/realmode":
            return _Resp(
                200,
                {
                    "is_real_model": True,
                    "fake_runtime_env": False,
                    "model_id": "EleutherAI/pythia-160m",
                    "model_loaded": True,
                    "worker_version": "m2-real-pythia",
                },
            )
        if url == f"{worker_url}/health/realmode":
            return _Resp(
                200,
                {
                    "is_real_model": True,
                    "fake_runtime_env": False,
                    "model_id": "EleutherAI/pythia-160m",
                    "model_loaded": True,
                    "worker_version": "m2-real-pythia",
                },
            )
        raise AssertionError(f"unexpected GET {url}")

    monkeypatch.setattr(verify_atlas_live.httpx, "get", _fake_get)

    exit_code = verify_atlas_live.main(
        ["--api-url", api_url, "--worker-url", worker_url, "--api-key", api_key]
    )
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Worker reachable (direct)" in out
    # Bearer token must be forwarded to the worker probe.
    worker_headers = seen_headers[f"{worker_url}/health/realmode"]
    assert worker_headers.get("Authorization") == f"Bearer {api_key}"
    # And NOT to the API probe.
    api_headers = seen_headers[f"{api_url}/atlas/live/health"]
    assert "Authorization" not in api_headers


# --- CLI --------------------------------------------------------------------


def test_help_runs_cleanly():
    parser = verify_atlas_live._build_parser()
    # If parser is malformed argparse will raise; this just exercises the
    # construction path mirrored by `python verify_atlas_live.py --help`.
    text = parser.format_help()
    assert "verify_atlas_live.py" in text
    assert "--api-url" in text
    assert "--worker-url" in text
    assert "--api-key" in text


def test_main_with_no_args_uses_default_api_url(monkeypatch, capsys):
    """No --api-url -> DEFAULT_API_URL, which we redirect to a benign error here."""
    routes = {
        f"{verify_atlas_live.DEFAULT_API_URL}/atlas/live/health": httpx.ConnectError(
            "simulated"
        ),
    }
    _install_router(monkeypatch, routes)
    exit_code = verify_atlas_live.main([])
    assert exit_code == 1
    out = capsys.readouterr().out
    assert verify_atlas_live.DEFAULT_API_URL in out
