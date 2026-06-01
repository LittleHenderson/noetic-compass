"""Probe-readout compatibility gate for frontier-scale runs (frontier run-gate 7).

Gate (6) confirmed the probe worker can *locate and hook* the decoder stack.
This gate answers the next question: given those hooks, can the worker actually
turn the captured activations into the **CAS axis readout** -- the run's central
deliverable -- or would it silently produce nothing, or abort?

Anchored to the worker's real contract (not an aspirational one). The probe
worker (``live-trace-worker/scripts/run_open_weight_probe_shard.py`` ::
``compute_cas_axis_readout``) loads a JSON probe artifact and:

* **requires** ``schema_version == "cas_probe_linear_v1"`` -- else ``RuntimeError``;
* **requires** a non-empty ``axes`` list and a ``weights`` dict -- else ``RuntimeError``;
* for each axis, **requires** ``weights[axis]`` to be a numeric vector whose length
  equals the pooled-activation feature dimension -- else
  ``RuntimeError("CAS probe axis ... has incompatible hidden size")``.

Two failure modes matter, and they are not the same:

* A *missing* probe degrades gracefully -- the worker reports ``cas_axis_readout``
  as a *missing output* (the strictness rule keeps the fleet verifier from
  overclaiming). No crash, but also no CAS scores.
* A *malformed* probe is worse: ``compute_cas_axis_readout`` raises, which aborts
  the **entire shard**, not just the readout.

Every scale plan declares ``cas_axis_readout`` in each shard's
``expected_outputs`` (``cas_harness_scale_planner``), so the CAS readout *is* the
point of the audit. Burning frontier (300B-4T) compute on a run whose central CAS
readout would silently come back *missing*, or whose shards abort on a malformed
probe, is exactly the dishonest-by-omission outcome the gate series exists to
prevent. So at frontier scale this gate **requires a structurally-loadable probe
specification**, and refuses (HTTP 422) without one or with a malformed one. Below
the frontier rung the spec is optional and recorded, never a blocker.

Honesty contract (mirrors gates 5 and 6 -- declared vs verified):

* ``PROBE_COMPATIBILITY_VERIFIED`` -- the worker actually loaded the probe and
  computed the readout with matching dimensions. Worker-side only; never produced
  at the API tier.
* ``PROBE_COMPATIBILITY_DECLARED`` -- a well-formed, loadable spec: the right
  schema, a non-empty axis set, a positive declared feature dimension, internally
  consistent. Enough to *create* a run; the final dimensional match against real
  pooled activations is confirmed worker-side.
* ``PROBE_COMPATIBILITY_UNSUPPORTED`` -- missing at frontier / wrong schema / empty
  axes / non-positive feature dimension / a declared pooled-feature dimension that
  contradicts the probe's vector length / a malformed artifact hash. Refuses the run.

Scope (kept deliberately narrow, so the gate stays honest): it certifies the probe
is mechanically *loadable and dimensionally self-consistent*. It does **not**
certify the probe's scores are *meaningful* on this model -- a frontier run is
``EXPERIMENTAL_NOT_VALIDATED`` by definition and no probe is empirically validated
on a frontier family. (Note: the worker's "incompatible hidden size" error text is
misleading -- the quantity it checks is the pooled-activation feature dimension,
``scenarios x assigned-layers x top_k``, not the model ``hidden_size``.)
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

ProbeCompatibilityStatus = Literal[
    "PROBE_COMPATIBILITY_VERIFIED",
    "PROBE_COMPATIBILITY_DECLARED",
    "PROBE_COMPATIBILITY_UNSUPPORTED",
]

# The exact schema_version string the worker's compute_cas_axis_readout requires.
REQUIRED_PROBE_SCHEMA_VERSION = "cas_probe_linear_v1"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ProbeReadoutSpecification:
    """Caller-supplied statement of the linear-probe readout artifact.

    A lightweight declaration of the worker-side probe file -- enough to check
    loadability and dimensional self-consistency, without shipping the full
    weight matrices through the control plane. ``feature_dimension`` is the
    per-axis weight-vector length (what the worker compares against the pooled
    activation vector). ``expected_pooled_features`` is optional: if the caller
    knows the run's pooling shape (``scenarios x assigned-layers x top_k``), the
    gate can perform the worker's exact dimensional check at create time instead
    of letting a shard abort. ``weights_sha256`` is an optional integrity hash of
    the probe artifact (declared here, recomputed worker-side).
    """

    schema_version: str
    axes: tuple[str, ...] = ()
    feature_dimension: int | None = None
    probe_id: str | None = None
    weights_sha256: str | None = None
    expected_pooled_features: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "axes": list(self.axes),
            "feature_dimension": self.feature_dimension,
            "probe_id": self.probe_id,
            "weights_sha256": self.weights_sha256,
            "expected_pooled_features": self.expected_pooled_features,
        }


@dataclass(frozen=True)
class ProbeCompatibilitySummary:
    """Honest rollup of the probe-compatibility check, mirroring the gate-6 shape."""

    status: ProbeCompatibilityStatus
    schema_version: str | None
    probe_id: str | None
    axis_count: int
    axes: tuple[str, ...]
    declared_feature_dimension: int | None
    expected_pooled_features: int | None
    dimension_consistent: bool | None
    weights_sha256: str | None
    weights_hash_verified: bool
    probe_loadable: bool
    notice: str
    reasons: tuple[str, ...] = ()

    @property
    def accepted(self) -> bool:
        """True when the probe spec is good enough to *create* a frontier run."""

        return self.status != "PROBE_COMPATIBILITY_UNSUPPORTED"

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "schema_version": self.schema_version,
            "probe_id": self.probe_id,
            "axis_count": self.axis_count,
            "axes": list(self.axes),
            "declared_feature_dimension": self.declared_feature_dimension,
            "expected_pooled_features": self.expected_pooled_features,
            "dimension_consistent": self.dimension_consistent,
            "weights_sha256": self.weights_sha256,
            "weights_hash_verified": self.weights_hash_verified,
            "probe_loadable": self.probe_loadable,
            "notice": self.notice,
            "reasons": list(self.reasons),
        }


def frontier_probe_requirement_notice() -> str:
    return (
        "A frontier-scale (300B-4T) run requires a CAS probe-readout specification the "
        f"worker can load: schema_version '{REQUIRED_PROBE_SCHEMA_VERSION}', a non-empty "
        "axis set, and a positive per-axis feature dimension. The CAS axis readout is the "
        "run's central deliverable (every shard's expected_outputs lists it); without a "
        "loadable probe the worker would report it as a missing output, and a malformed "
        "probe would abort the shard. Probe compatibility is run-gate (7)."
    )


def _unsupported(
    reasons: list[str],
    *,
    schema_version: str | None,
    probe_id: str | None,
    axes: tuple[str, ...],
    declared_feature_dimension: int | None,
    expected_pooled_features: int | None,
    weights_sha256: str | None,
    dimension_consistent: bool | None = None,
) -> ProbeCompatibilitySummary:
    return ProbeCompatibilitySummary(
        status="PROBE_COMPATIBILITY_UNSUPPORTED",
        schema_version=schema_version,
        probe_id=probe_id,
        axis_count=len(axes),
        axes=axes,
        declared_feature_dimension=declared_feature_dimension,
        expected_pooled_features=expected_pooled_features,
        dimension_consistent=dimension_consistent,
        weights_sha256=weights_sha256,
        weights_hash_verified=False,
        probe_loadable=False,
        notice=(
            "CAS probe readout unsupported: "
            + "; ".join(reasons)
            + ". "
            + frontier_probe_requirement_notice()
        ),
        reasons=tuple(reasons),
    )


def summarize_probe_compatibility(
    *,
    specification: ProbeReadoutSpecification | None,
) -> ProbeCompatibilitySummary:
    """Check a declared probe-readout spec against the worker's loader contract.

    Returns ``PROBE_COMPATIBILITY_DECLARED`` when the spec is structurally loadable
    (right schema, non-empty axes, positive feature dimension, internally
    consistent); ``PROBE_COMPATIBILITY_UNSUPPORTED`` otherwise.
    ``PROBE_COMPATIBILITY_VERIFIED`` is reserved for the worker, the only place the
    probe is actually loaded and run against real pooled activations.
    """

    if specification is None:
        return _unsupported(
            ["no probe readout specification attached"],
            schema_version=None,
            probe_id=None,
            axes=(),
            declared_feature_dimension=None,
            expected_pooled_features=None,
            weights_sha256=None,
        )

    schema_version = (specification.schema_version or "").strip() or None
    probe_id = (specification.probe_id or "").strip() or None
    axes = tuple(a for a in (s.strip() for s in specification.axes) if a)
    feature_dimension = specification.feature_dimension
    expected_pooled_features = specification.expected_pooled_features
    weights_sha256 = (specification.weights_sha256 or "").strip().lower() or None

    reasons: list[str] = []

    # 1) schema_version is a hard requirement of compute_cas_axis_readout.
    if schema_version != REQUIRED_PROBE_SCHEMA_VERSION:
        reasons.append(
            f"probe schema_version must be '{REQUIRED_PROBE_SCHEMA_VERSION}' "
            f"(declared: {schema_version!r}) -- the worker rejects any other schema"
        )

    # 2) a non-empty axis set is required (the worker needs axes to score).
    if not axes:
        reasons.append("probe declares no CAS axes (axes is empty)")

    # 3) a positive per-axis feature dimension is required: it is the vector
    #    length the worker matches against the pooled activation dimension.
    if feature_dimension is None:
        reasons.append(
            "probe declares no feature_dimension (the per-axis weight-vector length "
            "the worker matches against the pooled activation dimension)"
        )
    elif feature_dimension <= 0:
        reasons.append(f"probe feature_dimension must be positive (declared: {feature_dimension})")

    # 4) optional integrity hash, when present, must be well-formed (64 hex).
    if weights_sha256 is not None and not _SHA256_RE.match(weights_sha256):
        reasons.append("probe weights_sha256 is not a well-formed lowercase SHA-256 (64 hex chars)")

    # 5) if the caller declares the run's pooled-feature dimension, run the
    #    worker's exact check now -- a mismatch is precisely the RuntimeError the
    #    worker would raise ("incompatible hidden size"), so refuse honestly.
    dimension_consistent: bool | None = None
    if (
        expected_pooled_features is not None
        and feature_dimension is not None
        and feature_dimension > 0
    ):
        dimension_consistent = expected_pooled_features == feature_dimension
        if not dimension_consistent:
            reasons.append(
                "probe feature_dimension "
                f"({feature_dimension}) does not match the run's declared pooled-feature "
                f"dimension ({expected_pooled_features}); the worker would raise "
                "'incompatible hidden size' and abort the shard"
            )

    if reasons:
        return _unsupported(
            reasons,
            schema_version=schema_version,
            probe_id=probe_id,
            axes=axes,
            declared_feature_dimension=feature_dimension,
            expected_pooled_features=expected_pooled_features,
            weights_sha256=weights_sha256,
            dimension_consistent=dimension_consistent,
        )

    dim_note = (
        f"declared pooled-feature dimension {expected_pooled_features} matches the probe's "
        f"{feature_dimension}-d axis vectors"
        if expected_pooled_features is not None
        else (
            f"the probe declares {feature_dimension}-d axis vectors; the final match against "
            "the run's pooled activation dimension is confirmed worker-side at readout time"
        )
    )
    notice = (
        f"CAS probe readout specification is loadable: schema "
        f"'{REQUIRED_PROBE_SCHEMA_VERSION}', {len(axes)} axes"
        + (f", probe_id '{probe_id}'" if probe_id else "")
        + f". {dim_note}. This is a DECLARED spec -- the probe has NOT yet been loaded and "
        "run; that happens worker-side (only then can the status become "
        "PROBE_COMPATIBILITY_VERIFIED). The gate certifies the probe is mechanically loadable "
        "and dimensionally self-consistent, NOT that its scores are validated on this model "
        "(a frontier run is EXPERIMENTAL_NOT_VALIDATED by definition)."
    )

    return ProbeCompatibilitySummary(
        status="PROBE_COMPATIBILITY_DECLARED",
        schema_version=schema_version,
        probe_id=probe_id,
        axis_count=len(axes),
        axes=axes,
        declared_feature_dimension=feature_dimension,
        expected_pooled_features=expected_pooled_features,
        dimension_consistent=dimension_consistent,
        weights_sha256=weights_sha256,
        weights_hash_verified=False,
        probe_loadable=True,
        notice=notice,
        reasons=(),
    )


def validate_frontier_probe_compatibility(
    *,
    specification: ProbeReadoutSpecification | None,
) -> ProbeCompatibilitySummary:
    """Frontier run-gate: raise ``ValueError`` unless the probe spec is loadable.

    Acceptable means PROBE_COMPATIBILITY_DECLARED (or VERIFIED) -- a structurally
    loadable, dimensionally self-consistent spec is enough to *create* a frontier
    run. PROBE_COMPATIBILITY_UNSUPPORTED (missing / wrong schema / empty axes /
    bad dimension) refuses it. Callers convert this ValueError to HTTP 422.
    """

    summary = summarize_probe_compatibility(specification=specification)
    if summary.status == "PROBE_COMPATIBILITY_UNSUPPORTED":
        raise ValueError(
            "frontier-scale run refused: incompatible CAS probe readout -- "
            + "; ".join(summary.reasons)
            + ". "
            + frontier_probe_requirement_notice()
        )
    return summary
