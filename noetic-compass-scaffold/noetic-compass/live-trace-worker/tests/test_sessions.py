from __future__ import annotations

import hashlib
import json

import pytest

from app.auth import WORKER_TOKEN_HEADER
from app.routes import live_trace as live_trace_route


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _joined_headers(
    raw: bytes,
    *,
    authorization_sha256: str = "A" * 64,
    prospective_run_id: str = "run-joined-0001",
    invocation_id: str = "invocation-0000000000000001",
) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        live_trace_route.JOINED_REQUEST_SHA256_HEADER: hashlib.sha256(
            raw
        ).hexdigest().upper(),
        live_trace_route.JOINED_REQUEST_BYTE_LENGTH_HEADER: str(len(raw)),
        live_trace_route.JOINED_AUTHORIZATION_SHA256_HEADER: authorization_sha256,
        live_trace_route.JOINED_RUN_ID_HEADER: prospective_run_id,
        live_trace_route.JOINED_INVOCATION_ID_HEADER: invocation_id,
    }


def _create(client, **overrides) -> dict:
    body = {"prompt": "A warm coffee cup on the table.", "seed": 42}
    body.update(overrides)
    r = client.post("/sessions", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_joined_headers_do_not_collide_with_auth_or_controller_callback_headers():
    joined = {
        live_trace_route.JOINED_REQUEST_SHA256_HEADER.casefold(),
        live_trace_route.JOINED_REQUEST_BYTE_LENGTH_HEADER.casefold(),
        live_trace_route.JOINED_AUTHORIZATION_SHA256_HEADER.casefold(),
        live_trace_route.JOINED_RUN_ID_HEADER.casefold(),
        live_trace_route.JOINED_INVOCATION_ID_HEADER.casefold(),
    }
    assert len(joined) == 5
    assert joined.isdisjoint(
        {
            WORKER_TOKEN_HEADER.casefold(),
            "authorization",
            "x-cas-tenant-id",
            "x-cas-audit-id",
            "x-cas-service-timestamp",
            "x-cas-service-nonce",
            "x-cas-authorization-sha256",
            "x-cas-lease-token",
        }
    )


def test_create_session_returns_id_and_events_url(client):
    data = _create(client)
    assert "session_id" in data
    assert data["events_url"] == f"/sessions/{data['session_id']}/events"


def test_create_session_rejects_unknown_model(client):
    r = client.post(
        "/sessions",
        json={"prompt": "anything", "model_id": "EleutherAI/pythia-1.4b"},
    )
    assert r.status_code == 400
    assert "not supported" in r.text.lower()


def test_manifest_lookup_returns_full_manifest(client):
    data = _create(client)
    r = client.get(f"/sessions/{data['session_id']}/manifest")
    assert r.status_code == 200
    m = r.json()
    assert m["model_id"] == "EleutherAI/pythia-160m"
    assert m["model_arch"]["n_layers"] == 12
    assert m["model_arch"]["hidden_size"] == 768
    assert m["is_real_model"] is False


def test_manifest_lookup_unknown_session(client):
    r = client.get("/sessions/does-not-exist/manifest")
    assert r.status_code == 404


def test_dump_session_emits_full_event_sequence(client):
    # /sessions/dump is the non-SSE test/debug variant — returns the same
    # event list as the streamed endpoint but as one JSON payload.
    r = client.post(
        "/sessions/dump",
        json={"prompt": "Two short words.", "seed": 7, "max_new_tokens": 6},
    )
    assert r.status_code == 200
    assert set(r.json()) == {"events"}
    events = r.json()["events"]

    # Manifest first, knob_resolution echo, then neuron_covers, complete last.
    assert events[0]["type"] == "manifest"
    assert events[1]["type"] == "knob_resolution"
    assert events[2]["type"] == "neuron_covers"
    assert events[-1]["type"] == "complete"

    # Token events in between, exact count == max_new_tokens.
    token_events = [e for e in events if e["type"] == "token"]
    assert len(token_events) == 6
    assert events[-1]["total_tokens"] == 6

    # Token indices are 0..N-1 and monotonic.
    for i, ev in enumerate(token_events):
        assert ev["token_index"] == i
        # Mode 7 attribution: first token has a single None-from edge, the
        # rest have edges pointing back to earlier indices.
        if i == 0:
            assert ev["mode7_attribution"][0]["from_token_index"] is None
        else:
            for edge in ev["mode7_attribution"]:
                assert edge["from_token_index"] is not None
                assert 0 <= edge["from_token_index"] < i
                assert edge["to_token_index"] == i

    # Cover sets present, now carried as typed NeuronCoverMember records.
    covers = events[2]["per_class_neuron_covers"]
    for cls in ("F1A", "F1T", "F1f", "F1E"):
        assert cls in covers
        for member in covers[cls]:
            # Each member must carry label + confidence_band + evidence_sources.
            assert isinstance(member, dict)
            assert member["label"].startswith("L") and "N" in member["label"]
            assert member["confidence_band"] in {"high", "medium", "low", "unavailable"}
            assert isinstance(member["evidence_sources"], list)


def test_dump_session_is_deterministic_under_seed(client):
    body = {"prompt": "Stability check.", "seed": 1234, "max_new_tokens": 5}
    a = client.post("/sessions/dump", json=body).json()["events"]
    b = client.post("/sessions/dump", json=body).json()["events"]
    # Strip out the manifest (which is identical anyway) and compare the
    # token events directly — same seed must produce same activations.
    a_toks = [e for e in a if e["type"] == "token"]
    b_toks = [e for e in b if e["type"] == "token"]
    assert a_toks == b_toks


def test_dump_session_joined_binding_covers_exact_request_and_events(client):
    request_payload = {
        "prompt": "Joined request alpha.",
        "seed": 17,
        "max_new_tokens": 2,
    }
    raw = _canonical_json_bytes(request_payload)
    invocation_id = "invocation-alpha-000000000001"
    response = client.post(
        "/sessions/dump",
        content=raw,
        headers=_joined_headers(raw, invocation_id=invocation_id),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert set(payload) == {"events", "joined_execution_binding"}
    binding = payload["joined_execution_binding"]
    assert set(binding) == {
        "schema_version",
        "status",
        "authority",
        "authorization_sha256",
        "prospective_run_id",
        "invocation_id_sha256",
        "request_sha256",
        "request_byte_length",
        "events_sha256",
        "events_byte_length",
        "digest_profile",
        "binding_scope",
        "nonclaim",
    }
    assert binding == {
        "schema_version": live_trace_route.JOINED_EXECUTION_BINDING_SCHEMA,
        "status": live_trace_route.JOINED_EXECUTION_BINDING_STATUS,
        "authority": live_trace_route.JOINED_EXECUTION_BINDING_AUTHORITY,
        "authorization_sha256": "A" * 64,
        "prospective_run_id": "run-joined-0001",
        "invocation_id_sha256": hashlib.sha256(
            invocation_id.encode("ascii")
        ).hexdigest().upper(),
        "request_sha256": hashlib.sha256(raw).hexdigest().upper(),
        "request_byte_length": len(raw),
        "events_sha256": hashlib.sha256(
            _canonical_json_bytes(payload["events"])
        ).hexdigest().upper(),
        "events_byte_length": len(_canonical_json_bytes(payload["events"])),
        "digest_profile": live_trace_route.JOINED_EXECUTION_BINDING_DIGEST_PROFILE,
        "binding_scope": live_trace_route.JOINED_EXECUTION_BINDING_SCOPE,
        "nonclaim": live_trace_route.JOINED_EXECUTION_BINDING_NONCLAIM,
    }
    assert invocation_id not in response.text


def test_dump_session_joined_binding_uses_original_body_bytes_after_validation(client):
    spaced_raw = b'{ "prompt" : "Same parsed request" , "seed" : 29 }'
    compact_raw = b'{"prompt":"Same parsed request","seed":29}'

    accepted = client.post(
        "/sessions/dump",
        content=spaced_raw,
        headers=_joined_headers(spaced_raw),
    )
    cross_serialized = client.post(
        "/sessions/dump",
        content=compact_raw,
        headers=_joined_headers(spaced_raw),
    )

    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["joined_execution_binding"]["request_sha256"] == (
        hashlib.sha256(spaced_raw).hexdigest().upper()
    )
    assert cross_serialized.status_code == 400
    assert cross_serialized.json() == {
        "detail": "Joined execution request carrier does not match its declared binding."
    }


def test_dump_session_joined_bindings_make_cross_pairs_detectable(client):
    raw_a = _canonical_json_bytes(
        {"prompt": "Joined alpha output.", "seed": 23, "max_new_tokens": 2}
    )
    raw_b = _canonical_json_bytes(
        {"prompt": "Joined beta output.", "seed": 23, "max_new_tokens": 2}
    )
    response_a = client.post(
        "/sessions/dump",
        content=raw_a,
        headers=_joined_headers(
            raw_a,
            prospective_run_id="run-joined-alpha",
            invocation_id="invocation-alpha-000000000002",
        ),
    )
    response_b = client.post(
        "/sessions/dump",
        content=raw_b,
        headers=_joined_headers(
            raw_b,
            prospective_run_id="run-joined-beta",
            invocation_id="invocation-beta-0000000000003",
        ),
    )

    assert response_a.status_code == 200
    assert response_b.status_code == 200
    binding_a = response_a.json()["joined_execution_binding"]
    binding_b = response_b.json()["joined_execution_binding"]
    assert binding_a["request_sha256"] == hashlib.sha256(raw_a).hexdigest().upper()
    assert binding_b["request_sha256"] == hashlib.sha256(raw_b).hexdigest().upper()
    assert binding_a["request_sha256"] != binding_b["request_sha256"]
    assert binding_a["events_sha256"] != binding_b["events_sha256"]


def test_dump_session_rejects_cross_paired_request_headers_before_model_execution(
    client, monkeypatch
):
    raw_a = _canonical_json_bytes({"prompt": "Authorized request A."})
    raw_b = _canonical_json_bytes({"prompt": "Different request B."})
    calls = {"manifest": 0, "stream": 0}

    def counted_manifest(_model_id):
        calls["manifest"] += 1
        raise AssertionError("model lookup must not run for a mismatched carrier")

    async def counted_stream(_request):
        calls["stream"] += 1
        if False:  # pragma: no cover - retain async-generator shape
            yield None

    monkeypatch.setattr(live_trace_route, "get_manifest", counted_manifest)
    monkeypatch.setattr(live_trace_route, "stream_trace", counted_stream)
    response = client.post(
        "/sessions/dump",
        content=raw_b,
        headers=_joined_headers(raw_a),
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Joined execution request carrier does not match its declared binding."
    }
    assert calls == {"manifest": 0, "stream": 0}


@pytest.mark.parametrize(
    "mutation",
    [
        "partial",
        "lowercase-authorization",
        "noncanonical-length",
        "short-invocation",
    ],
)
def test_dump_session_rejects_bad_or_partial_joined_headers_before_model_execution(
    client, monkeypatch, mutation
):
    raw = _canonical_json_bytes({"prompt": "Never execute malformed joined input."})
    headers = _joined_headers(raw)
    if mutation == "partial":
        del headers[live_trace_route.JOINED_INVOCATION_ID_HEADER]
    elif mutation == "lowercase-authorization":
        headers[live_trace_route.JOINED_AUTHORIZATION_SHA256_HEADER] = "a" * 64
    elif mutation == "noncanonical-length":
        headers[live_trace_route.JOINED_REQUEST_BYTE_LENGTH_HEADER] = f"0{len(raw)}"
    elif mutation == "short-invocation":
        headers[live_trace_route.JOINED_INVOCATION_ID_HEADER] = "too-short"

    calls = {"manifest": 0, "stream": 0}

    def counted_manifest(_model_id):
        calls["manifest"] += 1
        raise AssertionError("model lookup must not run for invalid joined headers")

    async def counted_stream(_request):
        calls["stream"] += 1
        if False:  # pragma: no cover - retain async-generator shape
            yield None

    monkeypatch.setattr(live_trace_route, "get_manifest", counted_manifest)
    monkeypatch.setattr(live_trace_route, "stream_trace", counted_stream)
    response = client.post("/sessions/dump", content=raw, headers=headers)

    assert response.status_code == 400
    assert calls == {"manifest": 0, "stream": 0}
    assert "A" * 64 not in response.text


def test_dump_session_rejects_duplicate_joined_header_before_model_execution(
    client, monkeypatch
):
    raw = _canonical_json_bytes({"prompt": "Never execute duplicate bindings."})
    headers = list(_joined_headers(raw).items())
    headers.append(
        (
            live_trace_route.JOINED_REQUEST_SHA256_HEADER,
            hashlib.sha256(raw).hexdigest().upper(),
        )
    )
    calls = {"manifest": 0}

    def counted_manifest(_model_id):
        calls["manifest"] += 1
        raise AssertionError("model lookup must not run for duplicate joined headers")

    monkeypatch.setattr(live_trace_route, "get_manifest", counted_manifest)
    response = client.post("/sessions/dump", content=raw, headers=headers)

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Joined execution binding headers are incomplete or duplicated."
    }
    assert calls == {"manifest": 0}


def test_dump_session_joined_run_id_must_match_billing_context_before_model_execution(
    client, monkeypatch
):
    raw = _canonical_json_bytes(
        {
            "prompt": "Bind billing identity before execution.",
            "billing_measurement_context": {
                "tenant_id": "tenant-a",
                "billing_account_id": "acct-a",
                "run_id": "billing-run-a",
            },
        }
    )
    calls = {"manifest": 0}

    def counted_manifest(_model_id):
        calls["manifest"] += 1
        raise AssertionError("model lookup must not run for a conflicting run identity")

    monkeypatch.setattr(live_trace_route, "get_manifest", counted_manifest)
    response = client.post(
        "/sessions/dump",
        content=raw,
        headers=_joined_headers(raw, prospective_run_id="different-run"),
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Joined execution run identity conflicts with the request context."
    }
    assert calls == {"manifest": 0}


def test_demo_worker_refuses_to_fabricate_a_billable_measurement(client):
    response = client.post(
        "/sessions/dump",
        json={
            "prompt": "Never bill fake compute.",
            "billing_measurement_context": {
                "tenant_id": "tenant-a",
                "billing_account_id": "acct-a",
                "run_id": "attempt-a",
            },
        },
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Trusted CUDA usage measurement is unavailable."
    }
