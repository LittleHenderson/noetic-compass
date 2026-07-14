"""Run-gate (8): data-capture acknowledgment for the distributed CAS Harness probe.

The distributed CAS Harness audit is not only a measurement -- it is a data
*harvest*. Every run captures the target model's real signal -- its inputs and
outputs, the pooled hidden-state activations the probe hooks, the CAS axis readout
each worker shard emits (declared in every shard's ``expected_outputs``), and the
run's verdict -- for fleet-side evidence processing and labelled CAS-Native training
signal. That harvest is a property of the *method*:
it happens on **every** distributed run, frontier or not, because every run hooks
real activations and emits a real readout.

This gate makes that capture explicit and requires the caller to acknowledge it.
The specific dishonest-by-omission failure it prevents is a customer's model signal
being captured and reused to improve a product we sell without the customer ever
having been told or asked. Storage claims remain separate and receipt-backed.

It is **universal, not frontier-only** -- mirroring gate (2) and for the same kind of
reason. The frontier artifact gates (3)/(5)/(6)/(7) relax below the frontier because
their concerns (compute headroom, provenance rigor, probe/architecture support)
genuinely scale with model size. Data capture does not: a 20B run harvests exactly
as a 1T run does, because the harvest is intrinsic to how the audit works. So the
acknowledgment is required for *every* distributed run regardless of scale. It is a
**run** gate, not a **plan** gate, though: a planning-only ``/scale-plan`` preview
captures nothing, so it is never asked for there.

Honesty contract, mirroring the other gates' declared-vs-verified split:
  * ``DATA_CAPTURE_WORM_COMMITTED`` -- the fleet has an actual re-read-verified S3
      Object Lock receipt for the captured signal. Fleet-side only; **never** produced
      at the API tier, where no capture has happened yet.
  * ``DATA_CAPTURE_ACKNOWLEDGED``   -- the caller acknowledged the capture/retention/
      reuse terms. Enough to *create* a run, never on its own a customer ACCEPT.
  * ``DATA_CAPTURE_NOT_ACKNOWLEDGED`` -- a run with no acknowledgment -> a
      ``ValueError`` -> HTTP 422.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from api.services.cas_harness_retention_disclosure import (
    RETENTION_MODEL,
    ObjectLockRetentionDisclosure,
    configured_object_lock_retention_disclosure,
    retention_model_for_mode,
)


DataCaptureStatus = Literal[
    "DATA_CAPTURE_WORM_COMMITTED",
    "DATA_CAPTURE_ACKNOWLEDGED",
    "DATA_CAPTURE_NOT_ACKNOWLEDGED",
]


# The real classes of signal a distributed run harvests. Each is something the audit
# already produces -- the model's I/O, the pooled activations the probe hooks, the CAS
# axis readout every shard declares in its expected_outputs, and the run's verdict --
# so the gate surfaces them honestly rather than inventing a capture scope.
CAPTURED_SIGNAL_CLASSES: tuple[str, ...] = (
    "model_input_output",
    "pooled_hidden_state_activations",
    "cas_axis_readout",
    "audit_verdict",
)
REUSE_PURPOSE = "cas_native_training_corpus"


@dataclass(frozen=True)
class DataCaptureSummary:
    """The honest data-capture acknowledgment receipt carried out through the run record.

    Every field describes what the audit *actually* does with the captured signal --
    none is invented. The thing CAS Harness cannot honestly claim at this tier (that
    the bytes were written) is the ``capture_committed`` flag, kept ``False`` here
    because the write happens fleet-side, mirroring the other gates' ``*_verified``.
    """

    status: DataCaptureStatus
    acknowledged: bool
    # Always False at the API tier: only an actual re-read-verified fleet-side
    # Object Lock receipt can make this True.
    capture_committed: bool
    captured_signal_classes: tuple[str, ...]
    retention_model: str
    retention_disclosure: ObjectLockRetentionDisclosure
    reuse_purpose: str
    notice: str
    reasons: tuple[str, ...] = ()

    @property
    def accepted(self) -> bool:
        return self.status != "DATA_CAPTURE_NOT_ACKNOWLEDGED"

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "acknowledged": self.acknowledged,
            "capture_committed": self.capture_committed,
            "captured_signal_classes": list(self.captured_signal_classes),
            "retention_model": self.retention_model,
            "retention_disclosure": self.retention_disclosure.to_dict(),
            "reuse_purpose": self.reuse_purpose,
            "notice": self.notice,
            "reasons": list(self.reasons),
        }


def data_capture_requirement_notice(
    *, retention_disclosure: ObjectLockRetentionDisclosure | None = None
) -> str:
    capture_notice = (
        "A distributed CAS Harness audit captures the target model's real signal -- its "
        "inputs and outputs, the pooled hidden-state activations the probe hooks, the CAS "
        "axis readout each worker shard emits, and the run's verdict -- for fleet-side evidence "
        "processing and labelled CAS-Native training signal. This capture happens on every "
        "distributed run regardless of model size. This gate requires the caller to acknowledge "
        "capture and reuse before a run is created. The API tier only records the acknowledgment; "
        "nothing is captured at the API tier. "
    )
    retention = retention_disclosure or configured_object_lock_retention_disclosure(
        subject="captured audit signal"
    )
    return capture_notice + retention.notice


DATA_CAPTURE_OPENAPI_DESCRIPTION = (
    "Required to CREATE any real distributed run via /distributed/session, frontier or not. "
    + data_capture_requirement_notice()
    + " Setting accept_audit_data_capture=true records acknowledgment only; it never creates "
    "DATA_CAPTURE_WORM_COMMITTED. Ignored by the planning-only /scale-plan endpoint. Run-gate (8)."
)


def summarize_data_capture(*, acknowledged: bool) -> DataCaptureSummary:
    """Resolve a data-capture acknowledgement to its honest tri-state summary.

    Acknowledged -> ``DATA_CAPTURE_ACKNOWLEDGED`` (never ``DATA_CAPTURE_WORM_COMMITTED``
    here; only a verified fleet-side receipt can prove the write). Not acknowledged ->
    ``DATA_CAPTURE_NOT_ACKNOWLEDGED`` with a reason that names what is captured, where
    it goes, and the acknowledgement flag.
    """

    retention_disclosure = configured_object_lock_retention_disclosure(
        subject="captured audit signal"
    )
    reasons: list[str] = []
    if not acknowledged:
        reasons.append(
            "a distributed CAS Harness audit captures the target model's inputs/outputs, "
            "pooled hidden-state activations, CAS axis readout, and verdict for fleet-side "
            "evidence processing and CAS-Native training reuse. Set "
            "accept_audit_data_capture=true to acknowledge that capture and reuse. "
            + retention_disclosure.notice
        )

    status: DataCaptureStatus = (
        "DATA_CAPTURE_NOT_ACKNOWLEDGED" if reasons else "DATA_CAPTURE_ACKNOWLEDGED"
    )
    return DataCaptureSummary(
        status=status,
        acknowledged=acknowledged,
        capture_committed=False,
        captured_signal_classes=CAPTURED_SIGNAL_CLASSES,
        retention_model=retention_model_for_mode(retention_disclosure.mode),
        retention_disclosure=retention_disclosure,
        reuse_purpose=REUSE_PURPOSE,
        notice=data_capture_requirement_notice(
            retention_disclosure=retention_disclosure
        ),
        reasons=tuple(reasons),
    )


def validate_distributed_data_capture(*, acknowledged: bool) -> DataCaptureSummary:
    """Raise ``ValueError`` (-> HTTP 422) unless a run's data capture is acknowledged.

    Universal, not frontier-only: enforced for *every* distributed run because the
    harvest is intrinsic to the method and does not scale with model size. (Named
    ``validate_distributed_*`` rather than ``validate_frontier_*`` for exactly that
    reason, mirroring the universal gate (2) access validator.)
    """

    summary = summarize_data_capture(acknowledged=acknowledged)
    if not summary.accepted:
        raise ValueError(
            "distributed CAS Harness audit refused: audit data capture not acknowledged -- "
            + " ".join(summary.reasons)
        )
    return summary
