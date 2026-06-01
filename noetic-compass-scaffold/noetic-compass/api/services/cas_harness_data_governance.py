"""Run-gate (8): data-capture acknowledgment for the distributed CAS Harness probe.

The distributed CAS Harness audit is not only a measurement -- it is a data
*harvest*. Every run captures the target model's real signal -- its inputs and
outputs, the pooled hidden-state activations the probe hooks, the CAS axis readout
each worker shard emits (declared in every shard's ``expected_outputs``), and the
run's verdict -- and commits it to an immutable, write-once store, where it becomes
labelled training signal for CAS-Native. That harvest is a property of the *method*:
it happens on **every** distributed run, frontier or not, because every run hooks
real activations and emits a real readout.

This gate makes that capture explicit and requires the caller to acknowledge it.
The specific dishonest-by-omission failure it prevents: a customer's model signal
being persisted (immutably, indefinitely) and reused to improve a product we sell,
without the customer ever having been told or asked.

It is **universal, not frontier-only** -- mirroring gate (2) and for the same kind of
reason. The frontier artifact gates (3)/(5)/(6)/(7) relax below the frontier because
their concerns (compute headroom, provenance rigor, probe/architecture support)
genuinely scale with model size. Data capture does not: a 20B run harvests exactly
as a 1T run does, because the harvest is intrinsic to how the audit works. So the
acknowledgment is required for *every* distributed run regardless of scale. It is a
**run** gate, not a **plan** gate, though: a planning-only ``/scale-plan`` preview
captures nothing, so it is never asked for there.

Honesty contract, mirroring the other gates' declared-vs-verified split:
  * ``DATA_CAPTURE_WORM_COMMITTED`` -- the fleet actually wrote the captured signal
      to the immutable store. Fleet-side only; **never** produced at the API tier,
      where no capture has happened yet.
  * ``DATA_CAPTURE_ACKNOWLEDGED``   -- the caller acknowledged the capture/retention/
      reuse terms. Enough to *create* a run, never on its own a customer ACCEPT.
  * ``DATA_CAPTURE_NOT_ACKNOWLEDGED`` -- a run with no acknowledgment -> a
      ``ValueError`` -> HTTP 422.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


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
# Write-once-read-many: the store is immutable, so captured signal cannot be
# selectively redacted after the fact. Stated plainly rather than softened.
RETENTION_MODEL = "write_once_read_many"
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
    # Always False at the API tier: the captured signal is written to the immutable
    # store fleet-side, when the workers run, never at this tier where no model has
    # executed. Mirrors the other gates' *_verified / *_metered fields.
    capture_committed: bool
    captured_signal_classes: tuple[str, ...]
    retention_model: str
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
            "reuse_purpose": self.reuse_purpose,
            "notice": self.notice,
            "reasons": list(self.reasons),
        }


def data_capture_requirement_notice() -> str:
    return (
        "A distributed CAS Harness audit captures the target model's real signal -- its "
        "inputs and outputs, the pooled hidden-state activations the probe hooks, the CAS "
        "axis readout each worker shard emits, and the run's verdict -- and commits it to an "
        "immutable, write-once store, where it becomes labelled training signal for CAS-Native. "
        "This capture happens on every distributed run regardless of model size and is retained "
        "indefinitely; it is not billed back and cannot be selectively deleted from the "
        "write-once store. This gate requires the caller to acknowledge that capture, retention, "
        "and reuse before a run is created. The actual write is performed fleet-side when the "
        "workers run -- nothing is captured at the API tier, which only records the acknowledgment."
    )


def summarize_data_capture(*, acknowledged: bool) -> DataCaptureSummary:
    """Resolve a data-capture acknowledgement to its honest tri-state summary.

    Acknowledged -> ``DATA_CAPTURE_ACKNOWLEDGED`` (never ``DATA_CAPTURE_WORM_COMMITTED``
    here; the immutable write happens fleet-side). Not acknowledged ->
    ``DATA_CAPTURE_NOT_ACKNOWLEDGED`` with a reason that names what is captured, where
    it goes, and the acknowledgement flag.
    """

    reasons: list[str] = []
    if not acknowledged:
        reasons.append(
            "a distributed CAS Harness audit captures the target model's inputs/outputs, "
            "pooled hidden-state activations, CAS axis readout, and verdict and commits them to "
            "an immutable write-once store reused as CAS-Native training signal. Set "
            "accept_audit_data_capture=true to acknowledge that capture, indefinite WORM "
            "retention, and reuse before the run is created."
        )

    status: DataCaptureStatus = (
        "DATA_CAPTURE_NOT_ACKNOWLEDGED" if reasons else "DATA_CAPTURE_ACKNOWLEDGED"
    )
    return DataCaptureSummary(
        status=status,
        acknowledged=acknowledged,
        capture_committed=False,
        captured_signal_classes=CAPTURED_SIGNAL_CLASSES,
        retention_model=RETENTION_MODEL,
        reuse_purpose=REUSE_PURPOSE,
        notice=data_capture_requirement_notice(),
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
