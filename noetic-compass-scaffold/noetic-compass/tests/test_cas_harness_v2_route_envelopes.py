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
    OUTPUT_RETENTION_SCHEMA,
    RECONCILIATION_REQUEST_SCHEMA,
    RouteEnvelopeError,
    load_authorization_request_envelope,
    load_consumption_request_envelope,
    load_output_retention_envelope,
    load_reconciliation_request,
)


def _exact(raw: bytes, **metadata: object) -> dict[str, object]:
    return {
        **metadata,
        "sha256": hashlib.sha256(raw).hexdigest().upper(),
        "byte_length": len(raw),
        "raw_base64": base64.b64encode(raw).decode("ascii"),
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
