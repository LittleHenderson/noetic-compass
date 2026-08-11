"""The authenticated-eligibility axis: constant-false until wired, immune to drift."""

from __future__ import annotations

import os

from cas_forex import eligibility_attestation
from cas_forex.eligibility_attestation import (
    ATTESTED,
    NOT_WIRED,
    REFUSED,
    REQUIRED_ATTESTATIONS,
    Attestation,
    evaluate_authenticated_eligibility,
)


def test_authenticated_eligibility_is_false_until_a_verifier_is_wired():
    report = evaluate_authenticated_eligibility()
    assert report["eligible"] is False
    assert len(report["attestations"]) == len(REQUIRED_ATTESTATIONS) == 3
    assert all(a["status"] == NOT_WIRED for a in report["attestations"])
    assert report["reasons_not_eligible"]


def test_no_drift_by_accumulation_no_data_path_can_flip_the_axis(monkeypatch, tmp_path):
    """Flooding the environment, config, and filesystem with 'evidence' must
    change nothing: the axis reads none of them."""
    for key in (
        "CAS_FOREX_LIVE_TRADING_LICENSED",
        "CAS_FOREX_OWNER_ENABLE_LIVE_TRADING",
        "CAS_FOREX_AUTHENTICATED_ELIGIBILITY",
        "CAS_FOREX_ELIGIBLE",
    ):
        monkeypatch.setenv(key, "1")
    # a plausible-looking runtime override file, in case anything ever reads one
    (tmp_path / "eligibility-overrides.json").write_text(
        '{"eligible": true, "attested": true}', encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)

    report = evaluate_authenticated_eligibility()
    assert report["eligible"] is False, "a data write flipped the authenticated axis"


def test_module_exports_no_setter_or_override_hook():
    mutators = [
        name
        for name in dir(eligibility_attestation)
        if any(word in name.lower() for word in ("set_", "override", "force", "enable"))
    ]
    assert mutators == [], f"authenticated axis must have no write path, found {mutators}"


def test_a_raising_verifier_is_a_refusal_not_a_pass():
    def exploding() -> bool:
        raise RuntimeError("authority unreachable")

    record = Attestation(
        attestation_id="probe",
        authority="probe authority",
        requirement="probe",
        verify=exploding,
    ).evaluate()
    assert record["attested"] is False
    assert record["status"] == REFUSED


def test_a_wired_positive_verifier_is_the_only_path_to_attested():
    record = Attestation(
        attestation_id="probe",
        authority="probe authority",
        requirement="probe",
        verify=lambda: True,
    ).evaluate()
    assert record["attested"] is True
    assert record["status"] == ATTESTED


# ---------------------------------------------------------------------------
# Integration with the live-readiness checklist (the two-axis split).
# ---------------------------------------------------------------------------


def test_overall_status_rule_bounded_exhaustive():
    """All 8 input combinations: READY requires all three axes, nothing less."""
    from itertools import product

    from cas_forex.live_readiness import (
        NOT_READY_FOR_LIVE,
        READY_FOR_LIVE_EXECUTION,
        _resolve_overall_status,
    )

    for structural, authorized, attested in product((False, True), repeat=3):
        expected = (
            READY_FOR_LIVE_EXECUTION
            if structural and authorized and attested
            else NOT_READY_FOR_LIVE
        )
        actual = _resolve_overall_status(
            structural_completeness=structural,
            live_money_authorized=authorized,
            authenticated_eligible=attested,
        )
        assert actual == expected, (structural, authorized, attested)


def test_live_readiness_report_carries_both_axes_and_stays_not_ready():
    """An empty-input build exposes the new fields; the authenticated axis is
    False, so the report cannot be READY regardless of the structural side."""
    from cas_forex.live_readiness import (
        NOT_READY_FOR_LIVE,
        assert_live_readiness_boundary,
        build_live_readiness_report,
    )

    report = build_live_readiness_report(
        ui_readiness={},
        daily_bundle={},
        account_ledger={},
        movement_stream={},
        account_reconciliation={},
        backsolve={},
        walk_forward={},
        mt5_receipt={},
        mt5_probe_status={},
        runtime_gates={},
        authority_boundary={},
    )
    assert report.overall_status == NOT_READY_FOR_LIVE
    assert report.structural_completeness is False
    assert report.authenticated_eligibility is False
    payload = report.to_dict()
    assert payload["authenticated_eligibility"] is False
    assert payload["authenticated_eligibility_report"]["eligible"] is False
    assert payload["authenticated_eligibility_report"]["reasons_not_eligible"]
    assert_live_readiness_boundary(report)  # must not raise


def test_boundary_asserter_rejects_ready_without_attestation():
    """A READY report whose authenticated axis is False is a contract violation."""
    import dataclasses

    import pytest

    from cas_forex.live_readiness import (
        READY_FOR_LIVE_EXECUTION,
        assert_live_readiness_boundary,
        build_live_readiness_report,
    )

    base = build_live_readiness_report(
        ui_readiness={},
        daily_bundle={},
        account_ledger={},
        movement_stream={},
        account_reconciliation={},
        backsolve={},
        walk_forward={},
        mt5_receipt={},
        mt5_probe_status={},
        runtime_gates={},
        authority_boundary={},
    )
    forged = dataclasses.replace(
        base,
        overall_status=READY_FOR_LIVE_EXECUTION,
        authenticated_eligibility=False,
    )
    # The asserter checks structural completeness first (this forged report has
    # none), so that is the violation it names; the authenticated-axis branch
    # is covered by test_forged_ready_report_fails_even_with_self_declared_attestation.
    with pytest.raises(ValueError, match="structural completeness"):
        assert_live_readiness_boundary(forged)


def test_progression_packet_fails_closed_when_readiness_report_is_missing(monkeypatch):
    """A crashed readiness builder must BLOCK the live-money packet, not clear it."""
    from cas_forex import live_money_progression_packet as packet_module

    monkeypatch.setattr(packet_module, "_live_readiness_report", lambda: {})
    packet = packet_module.build_live_money_progression_packet()
    blocker_ids = [b.get("blocker_id") for b in packet.get("blockers", [])]
    assert "live_readiness_ready_for_live_execution" in blocker_ids, (
        "missing readiness report must register a blocker"
    )
    row = next(
        b for b in packet["blockers"]
        if b.get("blocker_id") == "live_readiness_ready_for_live_execution"
    )
    assert row.get("value", {}).get("overall_status") == "REPORT_UNAVAILABLE"


def test_progression_packet_fails_closed_when_payout_recovery_is_unavailable(monkeypatch):
    """A crashed payout-recovery builder must block, not read as 'no pending
    recovery'. (_unavailable() returns a dict WITHOUT has_pending_recovery, and
    `not .get(..., False)` previously counted that crash as all-clear.)"""
    from cas_forex import live_money_progression_packet as packet_module

    monkeypatch.setattr(
        packet_module,
        "_payout_recovery_status",
        lambda: {"report_kind": "cas_forex_payout_recovery", "status": "UNAVAILABLE", "error": "boom"},
    )
    packet = packet_module.build_live_money_progression_packet()
    row = next(
        (b for b in packet.get("blockers", []) if b.get("blocker_id") == "payout_recovery_clear"),
        None,
    )
    assert row is not None, "unavailable payout recovery must register a blocker"
    assert row.get("value", {}).get("recovery_status") == "UNAVAILABLE"


def test_forged_ready_report_fails_even_with_self_declared_attestation():
    """dataclasses.replace(..., authenticated_eligibility=True) must not pass:
    the asserter recomputes the pure axis instead of trusting the flag."""
    import dataclasses

    import pytest

    from cas_forex.live_readiness import (
        READY_FOR_LIVE_EXECUTION,
        assert_live_readiness_boundary,
        build_live_readiness_report,
    )

    base = build_live_readiness_report(
        ui_readiness={},
        daily_bundle={},
        account_ledger={},
        movement_stream={},
        account_reconciliation={},
        backsolve={},
        walk_forward={},
        mt5_receipt={},
        mt5_probe_status={},
        runtime_gates={},
        authority_boundary={},
    )
    forged = dataclasses.replace(
        base,
        overall_status=READY_FOR_LIVE_EXECUTION,
        structural_completeness=True,
        authenticated_eligibility=True,  # self-declared, not attested
    )
    with pytest.raises(ValueError, match="authenticated eligibility"):
        assert_live_readiness_boundary(forged)
