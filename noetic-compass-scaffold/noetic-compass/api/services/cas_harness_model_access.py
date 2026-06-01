"""Run-gate (2): model-access modality for the distributed CAS Harness probe.

This gate answers the most basic question a real audit faces, the one that comes
*before* "which weights / can we hook them / can we hold them": **can we
mechanistically reach this model at all?**

The distributed CAS Harness audit is a *mechanistic* probe. Each probe worker
loads the model's weights, hooks its decoder layers, and pools the resulting
hidden-state activations to compute the CAS axis readout -- the run's central
deliverable, declared in every shard's ``expected_outputs`` (see run-gates 6 and
7). That is physically possible only when the weights can be loaded locally:
open-weight or internal-access. A model reachable only as a provider-hosted
text/JSON API exposes **no hidden states**, so the ``cas_axis_readout``
deliverable cannot be produced at all -- the worker would have nothing to pool.

So this gate refuses any access mode but open-weight for the distributed
mechanistic path, and it does so for **every** size, not just the frontier:
unlike the provenance / architecture / probe / compute gates (which are stricter
*at* the frontier and optional below it), mechanistic reachability is a precondition
of the *method itself*. A 20B black-box model is exactly as un-probeable as a 1T
one. The refusal is honest and grounded -- it is a real mechanical limit of the
worker, not an invented criterion -- and it points the caller at the behavioral
``target/verify`` path that *is* appropriate for a hosted/black-box model.

Honesty contract, mirroring the other gates' declared-vs-verified split:
  * ``MODEL_ACCESS_VERIFIED``   -- a worker actually loaded the weights and
      confirmed local access. Fleet-side only; **never produced at the API tier**,
      where no weights are touched.
  * ``MODEL_ACCESS_DECLARED``   -- the caller declared open-weight access. Enough
      to *create* a run, never on its own a customer ACCEPT.
  * ``MODEL_ACCESS_UNSUPPORTED`` -- a hosted / black-box / output-only / unknown
      mode that the mechanistic probe cannot use -> ``ValueError`` -> HTTP 422.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


# The one access mode the mechanistic distributed probe can actually consume.
MECHANISTIC_ACCESS_MODE = "open_weight"

ModelAccessMode = Literal["open_weight", "hosted_api", "black_box", "output_only"]
ModelAccessStatus = Literal[
    "MODEL_ACCESS_VERIFIED",
    "MODEL_ACCESS_DECLARED",
    "MODEL_ACCESS_UNSUPPORTED",
]

# Human-readable description of each recognized *non*-mechanistic mode, so the
# refusal can name precisely why the mode cannot be probed rather than emitting a
# bare "unsupported". Any unrecognized string is treated the same way (refused),
# but described generically.
_NON_MECHANISTIC_MODES: dict[str, str] = {
    "hosted_api": "a provider-hosted inference API (text/JSON in, text/JSON out)",
    "black_box": "a black-box endpoint with no weight or activation access",
    "output_only": "an output-only interface that returns generations but no hidden states",
}


@dataclass(frozen=True)
class ModelAccessSummary:
    """The honest model-access receipt carried out through the run record."""

    status: ModelAccessStatus
    declared_mode: str
    mechanistic_probe_supported: bool
    # Always False at the API tier: confirming a model is genuinely loadable means
    # loading it, which only the workers do. Mirrors the other gates' *_verified
    # fields so a reader never mistakes "declared" for "verified".
    access_verified: bool
    notice: str
    reasons: tuple[str, ...] = ()

    @property
    def accepted(self) -> bool:
        return self.status != "MODEL_ACCESS_UNSUPPORTED"

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "declared_mode": self.declared_mode,
            "mechanistic_probe_supported": self.mechanistic_probe_supported,
            "access_verified": self.access_verified,
            "notice": self.notice,
            "reasons": list(self.reasons),
        }


def mechanistic_access_requirement_notice() -> str:
    return (
        "The distributed CAS Harness audit is a mechanistic probe: it computes the CAS "
        "axis readout from pooled hidden-state activations captured by hooking the model's "
        "decoder layers, so it requires open-weight (locally loadable) access. It is never a "
        "behavioral/black-box test. 'Declared' open-weight access is confirmed worker-side "
        "at model load -- never at the API tier, which touches no weights."
    )


def summarize_model_access(*, declared_mode: str) -> ModelAccessSummary:
    """Resolve a declared access mode to its honest tri-state summary.

    Open-weight -> ``MODEL_ACCESS_DECLARED`` (never ``VERIFIED`` here). Anything
    else -- hosted API, black box, output-only, an empty declaration, or an
    unrecognized string -- -> ``MODEL_ACCESS_UNSUPPORTED`` with a reason that names
    the mechanical limit and points at the behavioral ``target/verify`` path.
    """

    normalized = (declared_mode or "").strip().lower()
    reasons: list[str] = []

    if not normalized:
        reasons.append(
            "no model access mode was declared; declare weight_access='open_weight' for a "
            "mechanistic distributed audit, or use the behavioral target/verify path for a "
            "hosted/black-box model."
        )
    elif normalized != MECHANISTIC_ACCESS_MODE:
        described = _NON_MECHANISTIC_MODES.get(normalized, f"access mode '{normalized}'")
        reasons.append(
            f"model access mode '{normalized}' ({described}) cannot be mechanistically "
            "probed: the distributed audit captures the CAS axis readout from pooled "
            "hidden-state activations, which a text/JSON-only interface does not expose, so "
            "the cas_axis_readout deliverable is physically impossible. Declare "
            "weight_access='open_weight' for a mechanistic audit, or use the behavioral "
            "target/verify path for a hosted/black-box model."
        )

    if reasons:
        return ModelAccessSummary(
            status="MODEL_ACCESS_UNSUPPORTED",
            declared_mode=normalized or "(unspecified)",
            mechanistic_probe_supported=False,
            access_verified=False,
            notice=mechanistic_access_requirement_notice(),
            reasons=tuple(reasons),
        )

    return ModelAccessSummary(
        status="MODEL_ACCESS_DECLARED",
        declared_mode=normalized,
        mechanistic_probe_supported=True,
        access_verified=False,
        notice=mechanistic_access_requirement_notice(),
    )


def validate_distributed_model_access(*, declared_mode: str) -> ModelAccessSummary:
    """Raise ``ValueError`` (-> HTTP 422) unless the access mode is mechanistically probeable.

    Universal: enforced for every distributed run regardless of size, because
    mechanistic reachability is a precondition of the probe method itself.
    """

    summary = summarize_model_access(declared_mode=declared_mode)
    if not summary.accepted:
        raise ValueError(
            "distributed CAS Harness audit refused: unsupported model access mode -- "
            + " ".join(summary.reasons)
        )
    return summary
