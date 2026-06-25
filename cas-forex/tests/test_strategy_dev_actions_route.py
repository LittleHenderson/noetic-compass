"""ASGI tests for the /api/forex/strategy-dev-actions routes.

These tests register the strategy-dev-actions router on a fresh FastAPI app
(parent integration into ``api/server.py`` is a separate slice). They
exercise each endpoint through the ASGI protocol with the loader-injection
hook so no real evidence_runs/ files are touched.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest
from fastapi import FastAPI

from api.routes import strategy_dev_actions as route_module


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(
        route_module.router,
        prefix="/api/forex/strategy-dev-actions",
        tags=["strategy-dev-actions"],
    )
    return app


async def _asgi_post(app: FastAPI, path: str, body: dict[str, Any]) -> tuple[int, Any]:
    payload = json.dumps(body).encode("utf-8")
    body_sent = False

    async def receive() -> dict[str, Any]:
        nonlocal body_sent
        if body_sent:
            return {"type": "http.disconnect"}
        body_sent = True
        return {"type": "http.request", "body": payload, "more_body": False}

    sent: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    parsed = urlsplit(path)
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": parsed.path,
        "raw_path": parsed.path.encode("utf-8"),
        "query_string": parsed.query.encode("utf-8"),
        "headers": [
            (b"host", b"testserver"),
            (b"content-type", b"application/json"),
            (b"content-length", str(len(payload)).encode("ascii")),
        ],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "root_path": "",
    }
    await app(scope, receive, send)
    status = next(m["status"] for m in sent if m["type"] == "http.response.start")
    out = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    parsed_body = json.loads(out.decode("utf-8")) if out else None
    return int(status), parsed_body


@pytest.fixture(autouse=True)
def _reset_loader_between_tests():
    route_module.reset_loader_for_testing()
    yield
    route_module.reset_loader_for_testing()


def _install_loader(tmp_path: Path, queue: dict) -> Path:
    path = tmp_path / "queue.json"
    path.write_text(json.dumps(queue), encoding="utf-8")
    route_module.set_loader_for_testing(lambda: (json.loads(path.read_text(encoding="utf-8")), path))
    return path


def test_promote_endpoint_walks_one_stage(tmp_path):
    queue = {"items": [{"strategy_id": "abc", "stage": "RESEARCH"}]}
    path = _install_loader(tmp_path, queue)
    app = _build_app()
    status, body = asyncio.run(
        _asgi_post(app, "/api/forex/strategy-dev-actions/promote", {"strategy_id": "abc"})
    )
    assert status == 200, body
    assert body["accepted"] is True
    assert body["previous_stage"] == "RESEARCH"
    assert body["next_stage"] == "REPLAY"
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["items"][0]["stage"] == "REPLAY"


def test_demote_endpoint_walks_back(tmp_path):
    queue = {"items": [{"strategy_id": "abc", "stage": "PAPER"}]}
    _install_loader(tmp_path, queue)
    app = _build_app()
    status, body = asyncio.run(
        _asgi_post(app, "/api/forex/strategy-dev-actions/demote", {"strategy_id": "abc"})
    )
    assert status == 200, body
    assert body["accepted"] is True
    assert body["next_stage"] == "REPLAY"


def test_reject_endpoint_sets_terminal(tmp_path):
    queue = {"items": [{"strategy_id": "abc", "stage": "REVIEW"}]}
    _install_loader(tmp_path, queue)
    app = _build_app()
    status, body = asyncio.run(
        _asgi_post(app, "/api/forex/strategy-dev-actions/reject", {"strategy_id": "abc"})
    )
    assert status == 200, body
    assert body["next_stage"] == "REJECTED"


def test_archive_endpoint_sets_terminal(tmp_path):
    queue = {"items": [{"strategy_id": "abc", "stage": "PAPER"}]}
    _install_loader(tmp_path, queue)
    app = _build_app()
    status, body = asyncio.run(
        _asgi_post(app, "/api/forex/strategy-dev-actions/archive", {"strategy_id": "abc"})
    )
    assert status == 200, body
    assert body["next_stage"] == "ARCHIVED"


def test_review_endpoint_keeps_stage_and_tags_review_iso(tmp_path):
    queue = {"items": [{"strategy_id": "abc", "stage": "PAPER"}]}
    path = _install_loader(tmp_path, queue)
    app = _build_app()
    status, body = asyncio.run(
        _asgi_post(
            app,
            "/api/forex/strategy-dev-actions/review",
            {"strategy_id": "abc", "note": "spot-check"},
        )
    )
    assert status == 200, body
    assert body["accepted"] is True
    assert body["next_stage"] == "PAPER"
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["items"][0]["stage"] == "PAPER"
    assert "last_reviewed_at_iso" in written["items"][0]


def test_missing_strategy_id_returns_400(tmp_path):
    queue = {"items": [{"strategy_id": "abc", "stage": "RESEARCH"}]}
    _install_loader(tmp_path, queue)
    app = _build_app()
    status, body = asyncio.run(
        _asgi_post(
            app,
            "/api/forex/strategy-dev-actions/promote",
            {"strategy_id": "missing"},
        )
    )
    assert status == 400
    assert body["detail"]["error"] == "action_rejected"
    assert "not found" in body["detail"]["message"].lower()
    assert body["detail"]["current_stage"] is None


def test_illegal_transition_returns_400_with_current_stage(tmp_path):
    queue = {"items": [{"strategy_id": "abc", "stage": "RESEARCH"}]}
    _install_loader(tmp_path, queue)
    app = _build_app()
    status, body = asyncio.run(
        _asgi_post(
            app,
            "/api/forex/strategy-dev-actions/demote",
            {"strategy_id": "abc"},
        )
    )
    assert status == 400
    assert body["detail"]["error"] == "action_rejected"
    assert body["detail"]["current_stage"] == "RESEARCH"
    assert "RESEARCH" in body["detail"]["message"]


def test_note_is_carried_through_and_history_entry_created(tmp_path):
    queue = {"items": [{"strategy_id": "abc", "stage": "REPLAY"}]}
    path = _install_loader(tmp_path, queue)
    app = _build_app()
    status, body = asyncio.run(
        _asgi_post(
            app,
            "/api/forex/strategy-dev-actions/promote",
            {"strategy_id": "abc", "note": "regime fit confirmed"},
        )
    )
    assert status == 200, body
    assert body["note"] == "regime fit confirmed"
    written = json.loads(path.read_text(encoding="utf-8"))
    history = written["items"][0].get("history") or []
    assert len(history) == 1
    assert history[0]["action"] == "PROMOTE"
    assert history[0]["from_stage"] == "REPLAY"
    assert history[0]["to_stage"] == "PAPER"
    assert history[0]["note"] == "regime fit confirmed"


def test_queue_unavailable_returns_400(tmp_path):
    route_module.set_loader_for_testing(lambda: (None, None))
    app = _build_app()
    status, body = asyncio.run(
        _asgi_post(
            app,
            "/api/forex/strategy-dev-actions/promote",
            {"strategy_id": "abc"},
        )
    )
    assert status == 400
    assert body["detail"]["error"] == "queue_unavailable"
