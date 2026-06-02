"""Tests for the design-stage compliance governance stub (workstream 09).

Import-isolated: imports ONLY from ``api.services.production.compliance``. Exercises the
honesty-critical behaviors from the blueprint — a consent record is real/revocable (not a
boolean ack), ``check`` never silently grants, the governance audit trail is tamper-evident,
a ``ComplianceControl`` cannot be ``MET`` without evidence, and a ``DataSubjectRequest``
(especially erasure) is never falsely reported ``fulfilled`` by a stub. None of this touches
the live app.
"""

from __future__ import annotations

import pytest

from api.services.production.compliance import (
    AuditTrailEntry,
    ComplianceControl,
    ConsentDecision,
    ConsentLedger,
    ConsentRecord,
    DataSubjectRequest,
    InMemoryAuditTrail,
    InMemoryConsentLedger,
    ResidencyPolicy,
    RetentionPolicy,
    StubAttestationError,
    open_data_subject_request,
    stub_control_catalog,
)


def _ledger() -> InMemoryConsentLedger:
    return InMemoryConsentLedger()


# --- consent is a real, recorded, revocable artifact (not a boolean ack) --------------------
def test_stub_satisfies_consent_ledger_protocol():
    assert isinstance(_ledger(), ConsentLedger)


def test_record_consent_creates_active_artifact_with_subject_and_basis():
    ledger = _ledger()
    rec = ledger.record(
        subject_id="tenant-acme",
        scope=("model_input_output", "cas_native_training_reuse"),
        basis="contract",
        tenant_id="tenant-acme",
    )
    assert isinstance(rec, ConsentRecord)
    # The whole point of workstream 09: this is NOT a bare bool — it has subject, scope, basis,
    # a grant time, and a (currently null) revocation time.
    assert rec.subject_id == "tenant-acme"
    assert rec.basis == "contract"
    assert rec.granted_at
    assert rec.revoked_at is None
    assert rec.active is True
    assert "cas_native_training_reuse" in rec.scope


def test_check_grants_only_when_active_consent_covers_scope():
    ledger = _ledger()
    ledger.record(subject_id="s1", scope=("model_input_output",), basis="consent")

    covered = ledger.check(subject_id="s1", scope=("model_input_output",))
    assert isinstance(covered, ConsentDecision)
    assert covered.state == "granted"
    assert covered.scope_satisfied is True
    assert covered.may_capture is True

    # Active consent that does not cover the requested scope must NOT authorize capture.
    uncovered = ledger.check(subject_id="s1", scope=("pooled_hidden_state_activations",))
    assert uncovered.state == "granted"
    assert uncovered.scope_satisfied is False
    assert uncovered.may_capture is False


def test_check_unknown_subject_is_no_record_never_silent_grant():
    decision = _ledger().check(subject_id="never-seen", scope=("audit_verdict",))
    assert decision.state == "no_record"
    assert decision.may_capture is False
    assert decision.consent_id is None


def test_revoke_makes_check_return_revoked_and_is_monotonic():
    ledger = _ledger()
    ledger.record(subject_id="s2", scope=("model_input_output",), basis="consent")

    revoked = ledger.revoke(subject_id="s2")
    assert len(revoked) == 1
    assert revoked[0].revoked_at is not None
    assert revoked[0].active is False

    after = ledger.check(subject_id="s2", scope=("model_input_output",))
    assert after.state == "revoked"
    assert after.may_capture is False

    # Re-revoking an already-revoked subject is a no-op, never a fabricated revocation.
    assert ledger.revoke(subject_id="s2") == ()


def test_revoke_absent_subject_is_noop_not_error():
    assert _ledger().revoke(subject_id="ghost") == ()


def test_for_subject_preserves_grant_and_revoke_history():
    ledger = _ledger()
    ledger.record(subject_id="s3", scope=("model_input_output",), basis="consent")
    ledger.revoke(subject_id="s3")
    history = ledger.for_subject("s3")
    # The granted record is replaced in place by its revoked copy (monotonic), so the subject
    # still has exactly one record and it is now revoked — the revocation is auditable.
    assert len(history) == 1
    assert history[0].revoked_at is not None


def test_record_requires_subject_and_scope():
    ledger = _ledger()
    with pytest.raises(Exception):
        ledger.record(subject_id="  ", scope=("model_input_output",), basis="consent")
    with pytest.raises(Exception):
        ledger.record(subject_id="s4", scope=(), basis="consent")


# --- tamper-evident governance audit trail --------------------------------------------------
def test_audit_trail_chains_and_verifies():
    trail = InMemoryAuditTrail()
    a = trail.append(event_type="consent.granted", subject_id="s1")
    b = trail.append(event_type="capture.authorized", subject_id="s1", trace_id="trace-1")

    assert isinstance(a, AuditTrailEntry)
    assert a.previous_entry_sha256 is None
    assert b.previous_entry_sha256 == a.entry_sha256
    assert trail.verify_chain() is True


def test_audit_trail_detects_tampering():
    trail = InMemoryAuditTrail()
    trail.append(event_type="consent.granted", subject_id="s1")
    trail.append(event_type="dsr.received", subject_id="s1")

    # Mutate a committed entry's body behind the chain — the recomputed hash no longer matches.
    trail._entries[0].detail["smuggled"] = "value"
    assert trail.verify_chain() is False


# --- a control cannot be MET without evidence (no fabricated certification) ------------------
def test_control_cannot_be_met_without_evidence():
    with pytest.raises(StubAttestationError):
        ComplianceControl(
            control_id="CC6.1",
            framework="soc2",
            title="x",
            status="MET",
            what_flips_to_met="real auditor report",
            evidence_ref=None,
        )


def test_control_may_be_met_with_evidence_ref():
    control = ComplianceControl(
        control_id="CC6.1",
        framework="soc2",
        title="x",
        status="MET",
        what_flips_to_met="real auditor report",
        evidence_ref="s3://attestations/soc2-typeii-2026.pdf",
    )
    assert control.status == "MET"


def test_stub_control_catalog_claims_no_certification():
    catalog = stub_control_catalog()
    assert catalog  # non-empty
    # The honesty invariant: a stub catalog reports NOT_MET / PARTIAL — never MET.
    assert all(c.status in {"NOT_MET", "PARTIAL", "NOT_APPLICABLE"} for c in catalog)
    assert all(c.what_flips_to_met for c in catalog)
    frameworks = {c.framework for c in catalog}
    assert {"soc2", "iso27001", "gdpr"}.issubset(frameworks)


# --- DSR / erasure is never falsely reported fulfilled by a stub ----------------------------
def test_open_dsr_is_received_never_fulfilled():
    req = open_data_subject_request(subject_id="s1", request_type="erasure")
    assert isinstance(req, DataSubjectRequest)
    assert req.status == "received"
    assert req.fulfilled_at is None
    # A stub must not claim it shredded anything.
    assert req.status != "fulfilled"


@pytest.mark.parametrize("kind", ["access", "erasure", "portability"])
def test_open_dsr_each_type_starts_unfulfilled(kind):
    req = open_data_subject_request(subject_id="s1", request_type=kind)  # type: ignore[arg-type]
    assert req.request_type == kind
    assert req.status == "received"


# --- retention / residency policy honesty ---------------------------------------------------
def test_residency_policy_permits_and_defaults_to_not_enforced():
    policy = ResidencyPolicy(policy_id="res-eu", allowed_regions=("eu",), tenant_id="t1")
    assert policy.permits("eu") is True
    assert policy.permits("us") is False
    # Honest default: a policy object alone does not imply enforcement (blueprint §3 Phase C).
    assert policy.enforced is False


def test_residency_unrestricted_permits_any_region():
    policy = ResidencyPolicy(policy_id="res-any", allowed_regions=("unrestricted",))
    assert policy.permits("us") is True
    assert policy.permits("ap") is True


def test_retention_policy_records_basis_and_erasure_mechanism():
    policy = RetentionPolicy(
        policy_id="ret-1",
        retention_class="worm_indefinite",
        duration_days=None,
        legal_basis="legitimate_interest",
        erasure_mechanism="crypto_shred",
        applies_to=("pooled_hidden_state_activations",),
    )
    payload = policy.to_dict()
    # Replaces the bare "write_once_read_many" constant with an inspectable basis + the
    # erasure mechanism that reconciles WORM with erasure (blueprint §4).
    assert payload["legal_basis"] == "legitimate_interest"
    assert payload["erasure_mechanism"] == "crypto_shred"
    assert payload["duration_days"] is None
