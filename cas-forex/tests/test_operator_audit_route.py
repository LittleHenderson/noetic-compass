"""Tests for the /operator-audit route — HTTP face of the audit primitive.

Mounts the router on a local FastAPI app and drives ASGI directly so
route registration is verified without spinning up uvicorn. The parent
integrator wires :mod:`api.routes.operator_audit` into :mod:`api.server`
in a follow-on slice.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

from fastapi import FastAPI

from api.routes import operator_audit as route_module
from cas_forex.operator_audit import OperatorAuditLog


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(route_module.router, prefix="/api/forex/operator-audit")
    return app


async def _asgi(
    app: FastAPI,
    path: str,
    *,
    method: str = "GET",
    body: Any | None = None,
) -> tuple[int, Any]:
    sent: list[dict[str, Any]] = []

    encoded = b""
    headers: list[tuple[bytes, bytes]] = [(b"host", b"testserver")]
    if body is not None:
        encoded = json.dumps(body).encode("utf-8")
        headers.append((b"content-type", b"application/json"))
        headers.append((b"content-length", str(len(encoded)).encode("ascii")))

    request_sent = {"done": False}

    async def receive() -> dict[str, Any]:
        if request_sent["done"]:
            return {"type": "http.disconnect"}
        request_sent["done"] = True
        return {"type": "http.request", "body": encoded, "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    parsed = urlsplit(path)
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": parsed.path,
        "raw_path": parsed.path.encode("utf-8"),
        "query_string": parsed.query.encode("utf-8"),
        "headers": headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "root_path": "",
    }
    await app(scope, receive, send)
    status = next(m["status"] for m in sent if m["type"] == "http.response.start")
    raw_body = b"".join(
        m.get("body", b"") for m in sent if m["type"] == "http.response.body"
    )
    payload = json.loads(raw_body.decode("utf-8")) if raw_body else None
    return int(status), payload


def _isolate(tmp_path) -> tuple[FastAPI, OperatorAuditLog]:
    log = OperatorAuditLog(path=tmp_path / "operator-audit.jsonl")
    route_module.set_log_for_testing(log)
    return _build_app(), log


# ---------------------------------------------------------------------------


def test_get_entries_on_empty_log_returns_200_with_empty_list(tmp_path):
    app, _ = _isolate(tmp_path)
    status, body = asyncio.run(
        _asgi(app, "/api/forex/operator-audit/entries")
    )
    assert status == 200
    assert body["entries"] == []
    assert body["count"] == 0
    assert body["limit"] == 50


def test_post_record_then_get_entries_returns_recorded_entry(tmp_path):
    app, _ = _isolate(tmp_path)

    status, body = asyncio.run(
        _asgi(
            app,
            "/api/forex/operator-audit/record",
            method="POST",
            body={
                "action_kind": "STRATEGY_PROMOTED",
                "summary": "Promoted SMA-cross to runtime queue.",
                "target_id": "strat-001",
                "target_label": "SMA-cross",
                "payload": {"queue_pos": 1},
                "reversible": True,
                "reversal_hint": "Demote via /api/forex/strategy-dev-actions/demote",
            },
        )
    )
    assert status == 200
    entry_id = body["entry"]["entry_id"]
    assert body["entry"]["action_kind"] == "STRATEGY_PROMOTED"
    assert body["entry"]["target_id"] == "strat-001"

    status, listed = asyncio.run(
        _asgi(app, "/api/forex/operator-audit/entries?limit=10")
    )
    assert status == 200
    assert listed["count"] == 1
    assert listed["entries"][0]["entry_id"] == entry_id


def test_get_entries_filters_by_action_kind(tmp_path):
    app, _ = _isolate(tmp_path)

    for kind, summary, target in (
        ("STRATEGY_PROMOTED", "a", "1"),
        ("STRATEGY_DEMOTED", "b", "2"),
        ("RUNTIME_GATE_FLIP", "c", "3"),
    ):
        status, _ = asyncio.run(
            _asgi(
                app,
                "/api/forex/operator-audit/record",
                method="POST",
                body={
                    "action_kind": kind,
                    "summary": summary,
                    "target_id": target,
                },
            )
        )
        assert status == 200

    status, body = asyncio.run(
        _asgi(
            app,
            "/api/forex/operator-audit/entries"
            "?action_kind=STRATEGY_PROMOTED&action_kind=RUNTIME_GATE_FLIP",
        )
    )
    assert status == 200
    kinds = {e["action_kind"] for e in body["entries"]}
    assert kinds == {"STRATEGY_PROMOTED", "RUNTIME_GATE_FLIP"}
    assert body["count"] == 2


def test_get_stats_returns_required_fields(tmp_path):
    app, _ = _isolate(tmp_path)

    for body in (
        {
            "action_kind": "STRATEGY_PROMOTED",
            "summary": "one",
            "target_id": "t1",
            "reversible": True,
        },
        {
            "action_kind": "LEGACY_RECEIPTS_ARCHIVED",
            "summary": "two",
            "target_id": "t2",
        },
    ):
        status, _ = asyncio.run(
            _asgi(
                app,
                "/api/forex/operator-audit/record",
                method="POST",
                body=body,
            )
        )
        assert status == 200

    status, stats = asyncio.run(
        _asgi(app, "/api/forex/operator-audit/stats")
    )
    assert status == 200
    for key in ("total", "by_kind", "oldest_at_iso", "newest_at_iso", "reversible_count"):
        assert key in stats
    assert stats["total"] == 2
    assert stats["reversible_count"] == 1
    assert stats["oldest_at_iso"] is not None
    assert stats["newest_at_iso"] is not None
    assert stats["by_kind"] == {
        "STRATEGY_PROMOTED": 1,
        "LEGACY_RECEIPTS_ARCHIVED": 1,
    }


def test_post_record_with_guard_phrase_returns_400(tmp_path):
    app, _ = _isolate(tmp_path)
    status, body = asyncio.run(
        _asgi(
            app,
            "/api/forex/operator-audit/record",
            method="POST",
            body={
                "action_kind": "OTHER",
                "summary": "You should sell EURUSD before the close",
                "target_id": "x",
            },
        )
    )
    assert status == 400
    assert body["detail"]["error"] == "advisory_phrase"


def test_post_record_missing_action_kind_returns_400(tmp_path):
    app, _ = _isolate(tmp_path)
    status, body = asyncio.run(
        _asgi(
            app,
            "/api/forex/operator-audit/record",
            method="POST",
            body={"summary": "no action_kind here"},
        )
    )
    assert status == 400
    assert body["detail"]["error"] == "missing_field"


def test_post_record_missing_summary_returns_400(tmp_path):
    app, _ = _isolate(tmp_path)
    status, body = asyncio.run(
        _asgi(
            app,
            "/api/forex/operator-audit/record",
            method="POST",
            body={"action_kind": "OTHER"},
        )
    )
    assert status == 400
    assert body["detail"]["error"] == "missing_field"


def test_get_entries_respects_limit_query(tmp_path):
    app, _ = _isolate(tmp_path)
    for i in range(4):
        status, _ = asyncio.run(
            _asgi(
                app,
                "/api/forex/operator-audit/record",
                method="POST",
                body={
                    "action_kind": "OTHER",
                    "summary": f"entry {i}",
                    "target_id": f"id-{i}",
                },
            )
        )
        assert status == 200

    status, body = asyncio.run(
        _asgi(app, "/api/forex/operator-audit/entries?limit=2")
    )
    assert status == 200
    assert body["count"] == 2
    assert body["limit"] == 2
