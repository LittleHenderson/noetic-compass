"""Unit tests for the data-capture acknowledgment gate (run-gate 8).

These exercise the honesty contract at the service layer, mirroring the cost (4),
provenance (5), architecture (6), probe (7), and compute (3) gates' declared-vs-
verified split -- with two defining constraints. First, like the access gate (2)
and unlike the frontier gates, this one is **universal**: the harvest is intrinsic
to the method (every distributed run captures real signal), so the acknowledgment is
required at every size, not just the frontier. Second, the receipt surfaces only what
the audit *actually* does with the captured signal -- the real classes it harvests,
the immutable write-once retention, the CAS-Native reuse -- and never claims the bytes
were written, because the write happens fleet-side, never at the API tier.

* ``acknowledged`` -> ``DATA_CAPTURE_ACKNOWLEDGED``: enough to create a run, never on
  its own a verdict. ``capture_committed`` stays ``False`` -- the immutable write is
  performed fleet-side, never at the API tier.
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


# ---------------------------------------------------------------------------
# acknowledged -> ACKNOWLEDGED (never COMMITTED at the API tier)
# ---------------------------------------------------------------------------


def test_acknowledged_is_acknowledged_not_committed() -> None:
    summary = summarize_data_capture(acknowledged=True)

    assert summary.status == "DATA_CAPTURE_ACKNOWLEDGED"
    assert summary.accepted is True
    assert summary.acknowledged is True
    # The immutable write can only happen by running the fleet -- never at this tier.
    assert summary.capture_committed is False
    assert summary.reasons == ()


def test_acknowledged_surfaces_real_capture_scope_not_invented_one() -> None:
    summary = summarize_data_capture(acknowledged=True)

    # Every captured class is real signal the audit already produces.
    assert summary.captured_signal_classes == CAPTURED_SIGNAL_CLASSES
    assert "pooled_hidden_state_activations" in summary.captured_signal_classes
    assert "cas_axis_readout" in summary.captured_signal_classes
    assert "audit_verdict" in summary.captured_signal_classes
    # Honest about retention + reuse: immutable write-once, fed to CAS-Native.
    assert summary.retention_model == "write_once_read_many"
    assert summary.reuse_purpose == "cas_native_training_corpus"


# ---------------------------------------------------------------------------
# not acknowledged -> NOT_ACKNOWLEDGED (the 422 case)
# ---------------------------------------------------------------------------


def test_not_acknowledged_is_refused_and_names_what_is_captured() -> None:
    summary = summarize_data_capture(acknowledged=False)

    assert summary.status == "DATA_CAPTURE_NOT_ACKNOWLEDGED"
    assert summary.accepted is False
    assert summary.acknowledged is False
    joined = " ".join(summary.reasons).lower()
    # The refusal surfaces what is actually captured and where it is retained.
    assert "activations" in joined
    assert "readout" in joined
    assert "write-once" in joined
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
    # It must name the capture, the immutable retention, the CAS-Native reuse...
    assert "immutable" in notice
    assert "write-once" in notice
    assert "CAS-Native" in notice
    assert "every distributed run" in notice
    # ... and stay honest that nothing is captured at the API tier.
    assert "nothing is captured at the API tier" in notice
    assert "fleet-side" in notice


def test_to_dict_round_trip_shape() -> None:
    summary = summarize_data_capture(acknowledged=False)
    payload = summary.to_dict()

    assert set(payload) == {
        "status",
        "acknowledged",
        "capture_committed",
        "captured_signal_classes",
        "retention_model",
        "reuse_purpose",
        "notice",
        "reasons",
    }
    assert payload["status"] == "DATA_CAPTURE_NOT_ACKNOWLEDGED"
    assert payload["capture_committed"] is False
    assert isinstance(payload["captured_signal_classes"], list)
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
