"""Unit tests for the data-capture acknowledgment gate (run-gate 8).

These exercise the honesty contract at the service layer, mirroring the cost (4),
provenance (5), architecture (6), probe (7), and compute (3) gates' declared-vs-
verified split -- with two defining constraints. First, like the access gate (2)
and unlike the frontier gates, this one is **universal**: the harvest is intrinsic
to the method (every distributed run captures real signal), so the acknowledgment is
required at every size, not just the frontier. Second, the receipt surfaces only what
the audit *actually* does with the captured signal -- the real classes it harvests,
the time-bounded Object Lock policy, the CAS-Native reuse -- and never claims the bytes
were written, because only a fleet-side re-read receipt can prove that.

* ``acknowledged`` -> ``DATA_CAPTURE_ACKNOWLEDGED``: enough to create a run, never on
  its own a verdict. ``capture_committed`` stays ``False`` until an actual fleet-side
  Object Lock receipt is re-read and verified.
* not ``acknowledged`` -> ``DATA_CAPTURE_NOT_ACKNOWLEDGED`` with a reason that names
  what is captured, where it is retained, and the acknowledgement flag; the validator
  raises ``ValueError`` (-> HTTP 422).
* ``DATA_CAPTURE_WORM_COMMITTED`` is reserved for the fleet, the only place a real
  write happens, so it is never produced here.
"""

from __future__ import annotations

import dataclasses

import pytest

from api.services.cas_harness_data_governance import (
    CAPTURED_SIGNAL_CLASSES,
    DataCaptureSummary,
    data_capture_requirement_notice,
    summarize_data_capture,
    validate_distributed_data_capture,
)


@pytest.fixture(autouse=True)
def configured_retention_target(monkeypatch: pytest.MonkeyPatch) -> None:
    """These tests exercise a declared runtime target, not a code default."""

    monkeypatch.setenv(
        "CAS_HARNESS_EVIDENCE_ANCHOR_S3_OBJECT_LOCK_MODE", "GOVERNANCE"
    )
    monkeypatch.setenv("CAS_HARNESS_EVIDENCE_ANCHOR_S3_RETENTION_DAYS", "31")


# ---------------------------------------------------------------------------
# acknowledged -> ACKNOWLEDGED (never COMMITTED at the API tier)
# ---------------------------------------------------------------------------


def test_acknowledged_is_acknowledged_not_committed() -> None:
    summary = summarize_data_capture(acknowledged=True)

    assert summary.status == "DATA_CAPTURE_ACKNOWLEDGED"
    assert summary.accepted is True
    assert summary.acknowledged is True
    # A committed receipt can only be produced by the fleet -- never at this tier.
    assert summary.capture_committed is False
    assert summary.reasons == ()


def test_acknowledged_surfaces_real_capture_scope_not_invented_one() -> None:
    summary = summarize_data_capture(acknowledged=True)

    # Every captured class is real signal the audit already produces.
    assert summary.captured_signal_classes == CAPTURED_SIGNAL_CLASSES
    assert "pooled_hidden_state_activations" in summary.captured_signal_classes
    assert "cas_axis_readout" in summary.captured_signal_classes
    assert "audit_verdict" in summary.captured_signal_classes
    # Honest about retention + reuse: time-bounded Governance, fed to CAS-Native.
    assert summary.retention_model == "s3_object_lock_governance_time_bounded"
    assert summary.reuse_purpose == "cas_native_training_corpus"
    disclosure = summary.retention_disclosure
    assert disclosure.mode == "GOVERNANCE"
    assert disclosure.retention_days == 31
    assert disclosure.rolling_from_each_write is True
    assert disclosure.permanent_or_indefinite is False
    assert disclosure.privileged_operator_override_possible is True
    assert disclosure.tamper_evident_on_reverify is False
    assert disclosure.commit_status_requires_verified_receipt is True
    assert disclosure.receipt_verified is False


# ---------------------------------------------------------------------------
# not acknowledged -> NOT_ACKNOWLEDGED (the 422 case)
# ---------------------------------------------------------------------------


def test_not_acknowledged_is_refused_and_names_what_is_captured() -> None:
    summary = summarize_data_capture(acknowledged=False)

    assert summary.status == "DATA_CAPTURE_NOT_ACKNOWLEDGED"
    assert summary.accepted is False
    assert summary.acknowledged is False
    joined = " ".join(summary.reasons).lower()
    # The refusal surfaces what is captured and the configured lock boundary.
    assert "activations" in joined
    assert "readout" in joined
    assert "object lock governance" in joined
    assert "31 days" in joined
    # ... and names the acknowledgement flag.
    assert "accept_audit_data_capture" in " ".join(summary.reasons)


def test_capture_committed_is_never_true_in_either_state() -> None:
    # The honesty constraint: at the API tier nothing has been written, in either state.
    assert summarize_data_capture(acknowledged=True).capture_committed is False
    assert summarize_data_capture(acknowledged=False).capture_committed is False


# ---------------------------------------------------------------------------
# notice / to_dict / immutability
# ---------------------------------------------------------------------------


def test_notice_is_honest_about_capture_retention_and_tier() -> None:
    notice = data_capture_requirement_notice()
    # It must name capture, the finite Governance policy, and CAS-Native reuse.
    assert "S3 Object Lock GOVERNANCE" in notice
    assert "31 days" in notice
    assert "not permanent or indefinite" in notice
    assert "authorized AWS identity" in notice
    assert "exact bucket, key, S3 version, content SHA-256" in notice
    assert "CAS-Native" in notice
    assert "every distributed run" in notice
    assert "DATA_CAPTURE_WORM_COMMITTED is not asserted" in notice
    # ... and stay honest that nothing is captured at the API tier.
    assert "nothing is captured at the API tier" in notice
    assert "fleet-side" in notice
    assert "retained indefinitely" not in notice
    assert "cannot be selectively deleted" not in notice


def test_to_dict_round_trip_shape() -> None:
    summary = summarize_data_capture(acknowledged=False)
    payload = summary.to_dict()

    assert set(payload) == {
        "status",
        "acknowledged",
        "capture_committed",
        "captured_signal_classes",
        "retention_model",
        "retention_disclosure",
        "reuse_purpose",
        "notice",
        "reasons",
    }
    assert payload["status"] == "DATA_CAPTURE_NOT_ACKNOWLEDGED"
    assert payload["capture_committed"] is False
    assert isinstance(payload["captured_signal_classes"], list)
    assert payload["retention_disclosure"]["permanent_or_indefinite"] is False
    assert payload["retention_disclosure"]["receipt_verified"] is False
    assert isinstance(payload["reasons"], list)
    assert payload["reasons"]  # non-empty for a refusal


def test_summary_is_frozen() -> None:
    summary = summarize_data_capture(acknowledged=True)
    with pytest.raises(dataclasses.FrozenInstanceError):
        summary.status = "DATA_CAPTURE_WORM_COMMITTED"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# validate_distributed_data_capture -- raises on NOT_ACKNOWLEDGED
# ---------------------------------------------------------------------------


def test_validate_returns_summary_when_acknowledged() -> None:
    summary = validate_distributed_data_capture(acknowledged=True)
    assert isinstance(summary, DataCaptureSummary)
    assert summary.status == "DATA_CAPTURE_ACKNOWLEDGED"


def test_validate_raises_when_not_acknowledged() -> None:
    with pytest.raises(ValueError) as excinfo:
        validate_distributed_data_capture(acknowledged=False)
    message = str(excinfo.value)
    assert "audit data capture not acknowledged" in message
    assert "accept_audit_data_capture" in message
