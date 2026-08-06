from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
ROOT_KERNEL_TESTS = REPO_ROOT / "tests" / "cas_harness_v2"
if str(ROOT_KERNEL_TESTS) not in sys.path:
    sys.path.insert(0, str(ROOT_KERNEL_TESTS))

from test_research_control_kernel import Fixture, encode  # noqa: E402

from api.services.cas_harness_v2_route_envelopes import (  # noqa: E402
    AUTHORIZATION_REQUEST_SCHEMA,
    CONSUMPTION_REQUEST_SCHEMA,
    NONREPORTING_REQUEST_SCHEMA,
    OUTPUT_RETENTION_SCHEMA,
    OUTCOME_SEAL_REQUEST_SCHEMA,
    PACKET_ATTACHMENT_REQUEST_SCHEMA,
    RECONCILIATION_REQUEST_SCHEMA,
    RouteEnvelopeError,
    load_authorization_request_envelope,
    load_consumption_request_envelope,
    load_nonreporting_request_envelope,
    load_outcome_seal_request_envelope,
    load_output_retention_envelope,
    load_packet_attachment_request_envelope,
    load_reconciliation_request,
)


def _exact(raw: bytes, **metadata: object) -> dict[str, object]:
    return {
        **metadata,
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
        "byte_length": len(raw),
        "raw_base64": base64.b64encode(raw).decode("ascii"),
    }


def _binding(
    raw: bytes,
    *,
    artifact_id: str,
    media_type: str,
) -> dict[str, object]:
    exact = _exact(raw)
    return {
        "artifact_id": artifact_id,
        "media_type": media_type,
        "sha256": exact["sha256"],
        "byte_length": exact["byte_length"],
    }


def _authorization_value() -> tuple[Fixture, dict[str, object]]:
    fixture = Fixture()
    return fixture, {
        "schema_version": AUTHORIZATION_REQUEST_SCHEMA,
        "authorization_id": "fleet-job-envelope-001",
        "authorization_window": {
            "authorized_at": "2026-08-05T08:30:00Z",
            "expires_at": "2026-08-05T09:30:00Z",
            "time_assurance": "CALLER_DECLARED_NOT_TRUSTED",
        },
        "preregistration_chain": {
            "claim_ledger": _exact(fixture.claim_ledger_bytes),
            "base_preregistration": _exact(fixture.prereg_bytes),
            "amendments": [],
        },
        "artifact_bodies": [
            _exact(fixture.blobs[reference.artifact_id], artifact_id=reference.artifact_id)
            for reference in sorted(
                fixture.loaded.artifact_refs,
                key=lambda item: item.artifact_id,
            )
            if reference.artifact_id != "claim-ledger"
        ],
    }


def test_authorization_request_reconstructs_exact_pre_outcome_chain() -> None:
    fixture, value = _authorization_value()
    raw = encode(value)
    loaded = load_authorization_request_envelope(raw)
    assert loaded.raw_bytes == raw
    assert loaded.authorization_id == "fleet-job-envelope-001"
    assert loaded.claim_ledger.raw_bytes == fixture.claim_ledger_bytes
    assert loaded.base_preregistration.raw_bytes == fixture.prereg_bytes
    assert loaded.amendments == ()
    assert loaded.chain.base.sha256 == fixture.loaded.sha256
    assert loaded.chain.outcome_access is None
    assert loaded.criteria_status == "OPEN"
    assert loaded.trusted_time == "NOT_ESTABLISHED"
    assert loaded.license_status == "NOT LICENSED"
    assert loaded.disclosure_status == "HELD"


@pytest.mark.parametrize("duplicate_body", (b"conflicting-claim-ledger", None))
def test_authorization_request_rejects_duplicate_claim_ledger_source(
    duplicate_body: bytes | None,
) -> None:
    fixture, value = _authorization_value()
    raw = fixture.claim_ledger_bytes if duplicate_body is None else duplicate_body
    value["artifact_bodies"].append(
        _exact(raw, artifact_id="claim-ledger")
    )
    value["artifact_bodies"].sort(key=lambda row: row["artifact_id"])

    with pytest.raises(RouteEnvelopeError, match="dedicated claim-ledger body"):
        load_authorization_request_envelope(encode(value))


@pytest.mark.parametrize(
    "mutate",
    (
        lambda value: value.__setitem__("lease_token", "secret-forbidden"),
        lambda value: value["preregistration_chain"]["claim_ledger"].__setitem__(
            "sha256", "A" * 64
        ),
        lambda value: value["authorization_window"].__setitem__(
            "time_assurance", "TRUSTED"
        ),
        lambda value: value["preregistration_chain"].__setitem__(
            "amendments", [value["preregistration_chain"]["base_preregistration"]]
        ),
    ),
)
def test_authorization_request_rejects_secret_extension_tamper_and_bad_chain(
    mutate,
) -> None:
    _fixture, value = _authorization_value()
    mutate(value)
    with pytest.raises(RouteEnvelopeError):
        load_authorization_request_envelope(encode(value))


def test_duplicate_json_key_is_rejected_before_chain_loading() -> None:
    _fixture, value = _authorization_value()
    raw = encode(value).replace(
        b'"authorization_id":',
        b'"authorization_id":"forged","authorization_id":',
        1,
    )
    with pytest.raises(RouteEnvelopeError, match="strict bounded JSON"):
        load_authorization_request_envelope(raw)


def test_outcome_seal_envelope_binds_terminal_head_and_forbids_client_time() -> None:
    terminal = b"exact terminal bytes\n"
    value = {
        "schema_version": OUTCOME_SEAL_REQUEST_SCHEMA,
        "terminal_status": "SUCCESS",
        "terminal_artifact": _binding(
            terminal,
            artifact_id="terminal-001",
            media_type="application/json",
        ),
        "terminal_event_sha256": "A" * 64,
        "expected_lifecycle_head_sha256": "A" * 64,
    }
    loaded = load_outcome_seal_request_envelope(encode(value))
    assert loaded.terminal_status == "SUCCESS"
    assert loaded.terminal_artifact.artifact_id == "terminal-001"
    assert loaded.terminal_event_sha256 == "A" * 64

    with_client_time = deepcopy(value)
    with_client_time["accessed_at"] = "2026-08-05T09:30:00Z"
    with pytest.raises(RouteEnvelopeError, match="missing or unknown"):
        load_outcome_seal_request_envelope(encode(with_client_time))

    lowercase = deepcopy(value)
    lowercase["terminal_event_sha256"] = "a" * 64
    with pytest.raises(RouteEnvelopeError, match="uppercase SHA-256"):
        load_outcome_seal_request_envelope(encode(lowercase))


def test_packet_attachment_envelope_requires_ordered_unique_exact_dependencies() -> None:
    packet = b"exact packet bytes\n"
    value = {
        "schema_version": PACKET_ATTACHMENT_REQUEST_SCHEMA,
        "terminal_artifact": _binding(
            b"terminal\n",
            artifact_id="terminal-001",
            media_type="application/json",
        ),
        "outcome_access_artifact": _binding(
            b"outcome\n",
            artifact_id="outcome-001",
            media_type="application/json",
        ),
        "sealed_preregistration_chain_sha256": "B" * 64,
        "expected_lifecycle_head_sha256": "C" * 64,
        "packet": _exact(packet),
        "artifact_bodies": [
            _exact(b"alpha\n", artifact_id="alpha"),
            _exact(b"beta\n", artifact_id="beta"),
        ],
    }
    loaded = load_packet_attachment_request_envelope(encode(value))
    assert loaded.packet.raw_bytes == packet
    assert [item.artifact_id for item in loaded.artifact_bodies] == [
        "alpha",
        "beta",
    ]

    unsorted = deepcopy(value)
    unsorted["artifact_bodies"].reverse()
    with pytest.raises(RouteEnvelopeError, match="lexical order"):
        load_packet_attachment_request_envelope(encode(unsorted))

    duplicate = deepcopy(value)
    duplicate["artifact_bodies"][1] = duplicate["artifact_bodies"][0]
    with pytest.raises(RouteEnvelopeError, match="unique artifact IDs"):
        load_packet_attachment_request_envelope(encode(duplicate))

    with_client_time = deepcopy(value)
    with_client_time["recorded_at"] = "2026-08-05T10:00:00Z"
    with pytest.raises(RouteEnvelopeError, match="missing or unknown"):
        load_packet_attachment_request_envelope(encode(with_client_time))


def test_nonreporting_envelope_closes_state_reason_and_outcome_shape() -> None:
    terminal = _binding(
        b"failed terminal\n",
        artifact_id="terminal-failed-001",
        media_type="application/json",
    )
    outcome = _binding(
        b"outcome access\n",
        artifact_id="outcome-001",
        media_type="application/json",
    )
    value = {
        "schema_version": NONREPORTING_REQUEST_SCHEMA,
        "terminal_status": "FAILURE",
        "terminal_artifact": terminal,
        "outcome_access_artifact": outcome,
        "expected_lifecycle_head_sha256": "D" * 64,
        "reason_code": "TERMINAL_FAILURE_NO_PACKET",
    }
    loaded = load_nonreporting_request_envelope(encode(value))
    assert loaded.outcome_access_artifact == loaded.outcome_access_artifact
    assert loaded.reason_code == "TERMINAL_FAILURE_NO_PACKET"

    direct = {
        **value,
        "terminal_status": "INDETERMINATE",
        "outcome_access_artifact": None,
        "reason_code": "NO_OUTCOME_INDETERMINATE",
    }
    assert load_nonreporting_request_envelope(
        encode(direct)
    ).outcome_access_artifact is None

    wrong_reason = deepcopy(value)
    wrong_reason["reason_code"] = "NO_OUTCOME_REJECTED"
    with pytest.raises(RouteEnvelopeError, match="not allowed"):
        load_nonreporting_request_envelope(encode(wrong_reason))

    caller_envelope = deepcopy(value)
    caller_envelope["authority"] = "CLIENT_DECLARED"
    with pytest.raises(RouteEnvelopeError, match="missing or unknown"):
        load_nonreporting_request_envelope(encode(caller_envelope))


def test_consumption_envelope_contains_run_nonce_but_no_lease_capability() -> None:
    nonce = base64.urlsafe_b64encode(bytes(range(32))).decode("ascii").rstrip("=")
    value = {
        "schema_version": CONSUMPTION_REQUEST_SCHEMA,
        "run_nonce_b64url": nonce,
    }
    loaded = load_consumption_request_envelope(encode(value))
    assert loaded.run_nonce_b64url == nonce
    with pytest.raises(RouteEnvelopeError, match="missing or unknown"):
        load_consumption_request_envelope(
            encode({**value, "lease_token": "never-retain-this-secret"})
        )


def test_output_envelope_binds_exact_artifact_and_rejects_digest_drift() -> None:
    body = b"exact output bytes\n"
    value = {
        "schema_version": OUTPUT_RETENTION_SCHEMA,
        "output_name": "raw-outcomes",
        "artifact": _exact(
            body,
            artifact_id="output-envelope-001",
            media_type="application/jsonl",
        ),
    }
    loaded = load_output_retention_envelope(encode(value))
    assert loaded.output_name == "raw-outcomes"
    assert loaded.artifact.raw_bytes == body
    assert loaded.artifact.artifact_id == "output-envelope-001"
    changed = deepcopy(value)
    changed["artifact"]["byte_length"] += 1
    with pytest.raises(RouteEnvelopeError, match="exact byte identity"):
        load_output_retention_envelope(encode(changed))


def test_reconciliation_request_is_closed_and_carries_no_claims() -> None:
    raw = json.dumps(
        {"schema_version": RECONCILIATION_REQUEST_SCHEMA},
        separators=(",", ":"),
    ).encode("ascii")
    assert load_reconciliation_request(raw) == raw
    with pytest.raises(RouteEnvelopeError, match="missing or unknown"):
        load_reconciliation_request(
            encode(
                {
                    "schema_version": RECONCILIATION_REQUEST_SCHEMA,
                    "claim_gate_closed": True,
                }
            )
        )
