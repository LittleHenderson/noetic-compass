"""ASGI route tests for api.routes.forex_fury_promote.

The route is intentionally not yet wired into api/server.py — that's the
parent agent's integration step. To exercise it end-to-end we mount the
router on a local FastAPI app inside the test module.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest
from fastapi import FastAPI

from api.routes import forex_fury_promote as route_module


SET_CONTENT = b"ForexFury|profile=demo|tp=10|sl=5|window=04:00-05:00\n"
SET_SHA256 = hashlib.sha256(SET_CONTENT).hexdigest()
ROUTE_PREFIX = "/api/forex/forex-fury-promote"


@pytest.fixture()
def test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(route_module.router, prefix=ROUTE_PREFIX, tags=["forex-fury-promote"])
    return app


@pytest.fixture(autouse=True)
def _reset_loader_between_tests():
    route_module.reset_loader_for_testing()
    yield
    route_module.reset_loader_for_testing()


def _candidate(
    candidate_id: str = "ff-replay-eur-usd-m5-scalping-abc1234567",
    relative_set: str = "sets/demo.set",
    sha256: str = SET_SHA256,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "source_profile_id": "ff-demo-profile-1",
        "source_set_path": relative_set,
        "source_set_sha256": sha256,
        "family": "scalping",
        "cas_symbol": "EUR/USD",
        "timeframe": "M5",
        "evidence": {
            "profit_factor": 1.85,
            "equity_drawdown_relative_pct": 12.5,
            "total_trades": 240,
            "walk_forward_grade": "WALK_FORWARD_LEAD",
        },
    }


async def _asgi(
    app: FastAPI,
    method: str,
    path: str,
    body: bytes = b"",
    content_type: str | None = None,
) -> tuple[int, Any]:
    sent: list[dict[str, Any]] = []
    sent_request = False

    async def receive() -> dict[str, Any]:
        nonlocal sent_request
        if sent_request:
            return {"type": "http.disconnect"}
        sent_request = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    parsed = urlsplit(path)
    headers = [(b"host", b"testserver")]
    if content_type:
        headers.append((b"content-type", content_type.encode("utf-8")))
    if body:
        headers.append((b"content-length", str(len(body)).encode("utf-8")))

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
    body_bytes = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else None
    return int(status), payload


def _wire_test_env(tmp_path: Path, candidates_payload: dict[str, Any]) -> Path:
    leads_path = tmp_path / "strategy_leads.json"
    route_module.set_loader_for_testing(lambda: candidates_payload)
    route_module.set_leads_path_for_testing(leads_path)
    route_module.set_repo_root_for_testing(tmp_path)
    return leads_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_post_promote_200_on_success(tmp_path: Path, test_app: FastAPI) -> None:
    (tmp_path / "sets").mkdir(parents=True)
    (tmp_path / "sets" / "demo.set").write_bytes(SET_CONTENT)
    cand = _candidate()
    leads_path = _wire_test_env(tmp_path, {"candidates": [cand]})

    body = json.dumps({"candidate_id": cand["candidate_id"]}).encode("utf-8")
    status, payload = asyncio.run(
        _asgi(test_app, "POST", f"{ROUTE_PREFIX}/promote", body, "application/json")
    )

    assert status == 200, payload
    assert payload["accepted"] is True
    assert payload["lead_id"]
    assert payload["lead_path"] == str(leads_path)
    assert payload["integrity"]["verified"] is True

    document = json.loads(leads_path.read_text(encoding="utf-8"))
    assert document["leads"][0]["status"] == "PROMOTED_PAPER_LANE"


def test_post_promote_400_on_integrity_failure(tmp_path: Path, test_app: FastAPI) -> None:
    # No .set file on disk -> integrity fails.
    cand = _candidate()
    _wire_test_env(tmp_path, {"candidates": [cand]})

    body = json.dumps({"candidate_id": cand["candidate_id"]}).encode("utf-8")
    status, payload = asyncio.run(
        _asgi(test_app, "POST", f"{ROUTE_PREFIX}/promote", body, "application/json")
    )

    assert status == 400, payload
    assert "detail" in payload
    detail = payload["detail"]
    assert detail["error"] == "set file missing"
    assert detail["integrity"]["verified"] is False
    assert "missing" in (detail["integrity"]["error_message"] or "")


def test_post_promote_400_on_unknown_candidate(tmp_path: Path, test_app: FastAPI) -> None:
    _wire_test_env(tmp_path, {"candidates": []})

    body = json.dumps({"candidate_id": "ff-does-not-exist"}).encode("utf-8")
    status, payload = asyncio.run(
        _asgi(test_app, "POST", f"{ROUTE_PREFIX}/promote", body, "application/json")
    )

    assert status == 400, payload
    assert payload["detail"]["error"] == "candidate not found"


def test_get_promotion_status_unknown_candidate(tmp_path: Path, test_app: FastAPI) -> None:
    _wire_test_env(tmp_path, {"candidates": []})

    status, payload = asyncio.run(
        _asgi(test_app, "GET", f"{ROUTE_PREFIX}/promotion-status?candidate_id=ff-nope")
    )
    assert status == 200, payload
    assert payload == {"candidate_id": "ff-nope", "promoted": False, "lead_id": None}


def test_get_promotion_status_after_successful_promotion(tmp_path: Path, test_app: FastAPI) -> None:
    (tmp_path / "sets").mkdir(parents=True)
    (tmp_path / "sets" / "demo.set").write_bytes(SET_CONTENT)
    cand = _candidate()
    _wire_test_env(tmp_path, {"candidates": [cand]})

    body = json.dumps({"candidate_id": cand["candidate_id"]}).encode("utf-8")
    promote_status, promote_payload = asyncio.run(
        _asgi(test_app, "POST", f"{ROUTE_PREFIX}/promote", body, "application/json")
    )
    assert promote_status == 200, promote_payload

    status, payload = asyncio.run(
        _asgi(
            test_app,
            "GET",
            f"{ROUTE_PREFIX}/promotion-status?candidate_id={cand['candidate_id']}",
        )
    )
    assert status == 200, payload
    assert payload["candidate_id"] == cand["candidate_id"]
    assert payload["promoted"] is True
    assert payload["lead_id"] == promote_payload["lead_id"]
