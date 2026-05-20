"""Tests for the Stage 21B CAS Harness EvidencePacket v1 route.

Covers:

* GET happy path on a canonical Stage 21A sample (allow / caveat / constrain /
  suppress) → 200 with a packet that round-trips through the v1 schema.
* GET /markdown happy path with on-disk ``.md`` → 200, ``text/markdown``
  Content-Type, non-empty body.
* GET /markdown render-on-the-fly when only ``.json`` is on disk → 200 with
  rendered markdown that starts with the v1 ``# Evidence Packet: ...`` header.
* 404 for an unknown trace_id with reserved-language detail
  (``evidence packet not found``).
* Path-traversal attempts (``../foo``, ``foo/../bar``, absolute paths,
  separators, dotted) → 400 BEFORE filesystem access.
* Corrupted JSON / schema-validation failure → 500 with a generic
  reserved-language message.
* Size cap → packet > 8 MiB returns 413.
* Auth gating — unauthenticated requests return 401 from the existing JWT
  middleware.

These tests use the project's standard ``client`` and ``auth_headers``
fixtures from ``tests/conftest.py``.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[1]
_PACKETS_DIR = _REPO_ROOT / "research" / "cas_probe" / "evidence_packets"

# One canonical sample per readiness action — these are the Stage 21A
# locked exports and round-trip through the v1 validator by construction.
_CANONICAL_TRACES = [
    "stage21a_allow_qwen15b_000",
    "stage21a_caveat_olmo1b_009",
    "stage21a_constrain_olmo1b_054",
    "stage21a_suppress_olmo1b_054",
]


# ---------------------------------------------------------------------------
# Helpers — load the Stage 21A schema module by path so the tests can build
# valid packets without redefining the schema. Identical strategy to the
# production route.
# ---------------------------------------------------------------------------


def _load_evidence_packet_module():
    module_path = _REPO_ROOT / "research" / "cas_probe" / "evidence_packet.py"
    spec = importlib.util.spec_from_file_location("test_evidence_packet_v1", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_EP = _load_evidence_packet_module()


def _load_canonical_packet(trace_id: str) -> dict:
    return json.loads((_PACKETS_DIR / f"{trace_id}.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Auth gating — unauthenticated requests must be rejected by JWTAuthMiddleware.
# ---------------------------------------------------------------------------


def test_harness_evidence_get_requires_auth(client):
    resp = client.get(f"/harness/evidence/{_CANONICAL_TRACES[0]}")
    assert resp.status_code == 401


def test_harness_evidence_markdown_requires_auth(client):
    resp = client.get(f"/harness/evidence/{_CANONICAL_TRACES[0]}/markdown")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET happy path — canonical Stage 21A packets.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("trace_id", _CANONICAL_TRACES)
def test_get_canonical_packet_200(client, auth_headers, trace_id):
    resp = client.get(f"/harness/evidence/{trace_id}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Schema version + identity invariants.
    assert body["schema_version"] == _EP.SCHEMA_VERSION
    assert body["trace_id"] == trace_id

    # Body must round-trip through the v1 validator.
    _EP.validate_evidence_packet(body)


# ---------------------------------------------------------------------------
# GET /markdown happy path — on-disk markdown.
# ---------------------------------------------------------------------------


def test_get_markdown_serves_on_disk_file(client, auth_headers):
    trace_id = _CANONICAL_TRACES[0]
    resp = client.get(f"/harness/evidence/{trace_id}/markdown", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/markdown")
    body = resp.text
    assert body
    assert f"# Evidence Packet: {trace_id}" in body


# ---------------------------------------------------------------------------
# GET /markdown render-on-the-fly — no ``.md`` on disk.
# ---------------------------------------------------------------------------


def test_get_markdown_renders_when_md_missing(client, auth_headers, tmp_path, monkeypatch):
    """When only ``{trace_id}.json`` is on disk the route renders Markdown on
    the fly via the Stage 21A ``render_evidence_packet_markdown`` helper.
    """
    trace_id = "fly_render_test_001"
    packet = _load_canonical_packet(_CANONICAL_TRACES[0])
    packet["trace_id"] = trace_id

    (tmp_path / f"{trace_id}.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True), encoding="utf-8"
    )
    # No .md file written — must be rendered on the fly.

    from api.config import settings as api_settings

    monkeypatch.setattr(api_settings, "harness_evidence_packets_dir", str(tmp_path))

    resp = client.get(f"/harness/evidence/{trace_id}/markdown", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/markdown")
    body = resp.text
    assert body
    assert f"# Evidence Packet: {trace_id}" in body
    assert "## Boundary" in body
    assert "## Verification" in body


# ---------------------------------------------------------------------------
# 404 — unknown trace_id.
# ---------------------------------------------------------------------------


def test_get_unknown_trace_id_404(client, auth_headers):
    resp = client.get(
        "/harness/evidence/this_trace_id_does_not_exist_xyz_42",
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "evidence packet not found"


def test_get_markdown_unknown_trace_id_404(client, auth_headers):
    resp = client.get(
        "/harness/evidence/this_trace_id_does_not_exist_xyz_42/markdown",
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "evidence packet not found"


# ---------------------------------------------------------------------------
# Path-traversal guard — 400 BEFORE filesystem access.
#
# These are the values FastAPI will deliver as the ``trace_id`` path parameter
# after URL decoding. The regex must reject them all.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    [
        "../etc_passwd",
        "foo/../bar",
        "/etc/hosts",
        "..%2Fetc",
        "with space",
        ".hidden",
        "trace.with.dot",
        "trace$dollar",
        "trace#hash",
        "",  # empty -> regex {1,128} rejects
    ],
)
def test_get_rejects_path_traversal_attempts(client, auth_headers, bad):
    """Malformed trace_ids are rejected with HTTP 400 BEFORE any filesystem
    access. The route never touches the disk for these requests.
    """
    # Note: an empty trace_id makes the URL path /harness/evidence/ which
    # FastAPI routes to a 404 (no such route) instead of our 400 — we don't
    # exercise that here. Forward-slash inputs are routed differently by
    # FastAPI: ``foo/../bar`` lands on a different path entirely. So the
    # request-level boundary check is on the regex once FastAPI hands us
    # the path param. We assert the request returns *some* non-2xx status,
    # and use the function-level call below for the regex-direct check.
    resp = client.get(f"/harness/evidence/{bad}", headers=auth_headers)
    assert resp.status_code in {400, 404}, (
        f"trace_id {bad!r} must not reach a 2xx path; got {resp.status_code}"
    )


def test_validate_trace_id_rejects_traversal_directly():
    """Direct unit check on the regex guard — bypasses FastAPI's path routing
    so we can confirm every traversal-style string is rejected with 400.
    """
    from api.routes.harness_evidence import _validate_trace_id
    from fastapi import HTTPException

    for bad in [
        "..",
        "../foo",
        "foo/../bar",
        "/etc/hosts",
        "trace id with space",
        ".hidden",
        "trace.with.dot",
        "trace$dollar",
        "trace#hash",
        "trace\x00null",
        "x" * 200,  # too long for the regex bound
        "",
    ]:
        with pytest.raises(HTTPException) as info:
            _validate_trace_id(bad)
        assert info.value.status_code == 400
        assert info.value.detail == "trace_id is not well-formed"


def test_validate_trace_id_accepts_canonical_forms():
    """Sanity: the canonical sample trace_ids must pass the regex guard."""
    from api.routes.harness_evidence import _validate_trace_id

    for good in [
        "stage21a_allow_qwen15b_000",
        "abc123",
        "00000000-0000-4000-8000-000000000000",  # UUID4-shape
        "trace-with-hyphen",
    ]:
        _validate_trace_id(good)  # must not raise


# ---------------------------------------------------------------------------
# Corrupted file → 500 with generic message.
# ---------------------------------------------------------------------------


def test_corrupted_packet_returns_500(client, auth_headers, tmp_path, monkeypatch):
    """A file that exists but fails ``validate_evidence_packet`` surfaces as
    HTTP 500 with a generic reserved-language message. Schema details are
    not leaked to clients.
    """
    trace_id = "corrupted_packet_test_001"
    (tmp_path / f"{trace_id}.json").write_text(
        json.dumps({"this": "is_not_a_v1_packet"}), encoding="utf-8"
    )

    from api.config import settings as api_settings

    monkeypatch.setattr(api_settings, "harness_evidence_packets_dir", str(tmp_path))

    resp = client.get(f"/harness/evidence/{trace_id}", headers=auth_headers)
    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert detail == "evidence packet validation failed"
    # Confirm internal schema details are not surfaced.
    assert "missing top-level keys" not in detail
    assert "schema_version" not in detail


def test_invalid_json_returns_500(client, auth_headers, tmp_path, monkeypatch):
    """A file that exists but is not parseable JSON surfaces as HTTP 500."""
    trace_id = "garbage_packet_test_001"
    (tmp_path / f"{trace_id}.json").write_text("{this is not json", encoding="utf-8")

    from api.config import settings as api_settings

    monkeypatch.setattr(api_settings, "harness_evidence_packets_dir", str(tmp_path))

    resp = client.get(f"/harness/evidence/{trace_id}", headers=auth_headers)
    assert resp.status_code == 500
    assert resp.json()["detail"] == "evidence packet validation failed"


# ---------------------------------------------------------------------------
# Size cap → 413.
# ---------------------------------------------------------------------------


def test_oversized_packet_returns_413(client, auth_headers, tmp_path, monkeypatch):
    """Files larger than the 8 MiB cap are refused with HTTP 413 BEFORE the
    body is read into memory. We allocate just over the cap with a sparse-ish
    payload and rely on ``stat().st_size`` to trigger the guard.
    """
    trace_id = "oversized_packet_test_001"
    target = tmp_path / f"{trace_id}.json"
    # 8 MiB + 1 KB of valid-looking JSON-ish bytes is enough to exceed the
    # cap on disk. We don't need the file to parse — the size check fires
    # before any read.
    payload_bytes = (b'{"x": "' + (b"a" * (8 * 1024 * 1024)) + b'"}')
    target.write_bytes(payload_bytes)
    # Sanity check the size guard precondition.
    assert target.stat().st_size > 8 * 1024 * 1024

    from api.config import settings as api_settings

    monkeypatch.setattr(api_settings, "harness_evidence_packets_dir", str(tmp_path))

    resp = client.get(f"/harness/evidence/{trace_id}", headers=auth_headers)
    assert resp.status_code == 413
    assert resp.json()["detail"] == "evidence packet exceeds size cap"


# ---------------------------------------------------------------------------
# Smoke import — ensure the router module is loadable.
# ---------------------------------------------------------------------------


def test_router_module_importable():
    from api.routes.harness_evidence import router

    assert router.prefix == "/harness/evidence"
    paths = {route.path for route in router.routes}
    assert "/harness/evidence/{trace_id}" in paths
    assert "/harness/evidence/{trace_id}/markdown" in paths


# ---------------------------------------------------------------------------
# Re-validate-on-read — every served packet must round-trip through the v1
# validator. Smoke this by reading every canonical sample through the route.
# ---------------------------------------------------------------------------


def test_every_canonical_packet_round_trips(client, auth_headers):
    for trace_id in _CANONICAL_TRACES:
        resp = client.get(f"/harness/evidence/{trace_id}", headers=auth_headers)
        assert resp.status_code == 200, f"{trace_id}: {resp.text}"
        body = resp.json()
        _EP.validate_evidence_packet(body)
        # Markdown endpoint also round-trips (re-validates inside renderer).
        md_resp = client.get(
            f"/harness/evidence/{trace_id}/markdown", headers=auth_headers
        )
        assert md_resp.status_code == 200, f"{trace_id}: {md_resp.text}"
        assert md_resp.text.startswith(f"# Evidence Packet: {trace_id}")


# ---------------------------------------------------------------------------
# Configurable packets directory — env-var override flows through.
# ---------------------------------------------------------------------------


def test_configurable_packets_dir(client, auth_headers, tmp_path, monkeypatch):
    """Pointing the settings field at an alternate directory makes the route
    serve packets from that directory. This is the production-deployment
    override path.
    """
    trace_id = "configurable_dir_test_001"
    packet = _load_canonical_packet(_CANONICAL_TRACES[0])
    packet["trace_id"] = trace_id
    (tmp_path / f"{trace_id}.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True), encoding="utf-8"
    )

    from api.config import settings as api_settings

    monkeypatch.setattr(api_settings, "harness_evidence_packets_dir", str(tmp_path))

    resp = client.get(f"/harness/evidence/{trace_id}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["trace_id"] == trace_id
    _EP.validate_evidence_packet(body)
