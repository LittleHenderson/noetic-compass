"""Unit tests for the frontier probe-readout gate (frontier run-gate 7).

These exercise the honesty contract at the service layer, mirroring the
provenance (5) and architecture (6) gates' declared-vs-verified split:

* A missing spec, a wrong ``schema_version``, an empty axis set, a non-positive
  feature dimension, a malformed integrity hash, or a declared pooled-feature
  dimension that contradicts the probe's vector length is
  ``PROBE_COMPATIBILITY_UNSUPPORTED`` and the frontier validator raises (callers
  turn that into HTTP 422).
* A structurally loadable, dimensionally self-consistent spec is
  ``PROBE_COMPATIBILITY_DECLARED`` -- enough to create a run, never a verdict.
* ``PROBE_COMPATIBILITY_VERIFIED`` is reserved for the probe worker, the only
  place the probe is actually loaded and run against real pooled activations, so
  it is never produced at this service tier.

The checks are anchored to the worker's real loader contract
(``compute_cas_axis_readout``): schema_version must be ``cas_probe_linear_v1``,
``axes`` must be non-empty, and each axis weight-vector length must match the
pooled-activation feature dimension -- a mismatch is the worker's
"incompatible hidden size" RuntimeError, which aborts the whole shard.
"""

from __future__ import annotations

import pytest

from api.services.cas_harness_probe_compatibility import (
    REQUIRED_PROBE_SCHEMA_VERSION,
    ProbeReadoutSpecification,
    summarize_probe_compatibility,
    validate_frontier_probe_compatibility,
)
from api.services.cas_harness_tks_definition_lock import LOCKED_TKS_DEFINITION_SHA256


def _good_spec(**overrides: object) -> ProbeReadoutSpecification:
    """A structurally loadable probe spec; overrides poke individual fields."""

    base: dict[str, object] = {
        "schema_version": REQUIRED_PROBE_SCHEMA_VERSION,
        "axes": ("F1", "F2", "F3"),
        "feature_dimension": 200,
        "definition_sha256": LOCKED_TKS_DEFINITION_SHA256,
    }
    base.update(overrides)
    return ProbeReadoutSpecification(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Missing / malformed -> UNSUPPORTED
# ---------------------------------------------------------------------------


def test_missing_specification_is_unsupported():
    summary = summarize_probe_compatibility(specification=None)

    assert summary.status == "PROBE_COMPATIBILITY_UNSUPPORTED"
    assert summary.accepted is False
    assert summary.probe_loadable is False
    assert summary.reasons  # an honest reason is always attached


def test_wrong_schema_version_is_unsupported():
    summary = summarize_probe_compatibility(
        specification=_good_spec(schema_version="cas_probe_linear_v2")
    )

    assert summary.status == "PROBE_COMPATIBILITY_UNSUPPORTED"
    assert summary.probe_loadable is False
    assert any("schema_version" in reason for reason in summary.reasons)
    # The required schema is named in the notice so the caller can fix it.
    assert REQUIRED_PROBE_SCHEMA_VERSION in summary.notice


def test_empty_axes_is_unsupported():
    summary = summarize_probe_compatibility(specification=_good_spec(axes=()))

    assert summary.status == "PROBE_COMPATIBILITY_UNSUPPORTED"
    assert summary.axis_count == 0
    assert any("axes" in reason for reason in summary.reasons)


def test_missing_definition_sha256_is_unsupported():
    summary = summarize_probe_compatibility(
        specification=_good_spec(definition_sha256=None)
    )

    assert summary.status == "PROBE_COMPATIBILITY_UNSUPPORTED"
    assert summary.tks_definition_locked is False
    assert any("definition_sha256" in reason for reason in summary.reasons)


def test_wrong_definition_sha256_is_unsupported():
    summary = summarize_probe_compatibility(
        specification=_good_spec(definition_sha256="0" * 64)
    )

    assert summary.status == "PROBE_COMPATIBILITY_UNSUPPORTED"
    assert summary.tks_definition_locked is False
    assert any(LOCKED_TKS_DEFINITION_SHA256 in reason for reason in summary.reasons)


def test_whitespace_only_axes_are_treated_as_empty():
    # The worker needs real axis names; blank strings score nothing.
    summary = summarize_probe_compatibility(specification=_good_spec(axes=("  ", "")))

    assert summary.status == "PROBE_COMPATIBILITY_UNSUPPORTED"
    assert summary.axis_count == 0


def test_missing_feature_dimension_is_unsupported():
    summary = summarize_probe_compatibility(
        specification=_good_spec(feature_dimension=None)
    )

    assert summary.status == "PROBE_COMPATIBILITY_UNSUPPORTED"
    assert any("feature_dimension" in reason for reason in summary.reasons)


@pytest.mark.parametrize("bad_dimension", [0, -1, -512])
def test_non_positive_feature_dimension_is_unsupported(bad_dimension):
    summary = summarize_probe_compatibility(
        specification=_good_spec(feature_dimension=bad_dimension)
    )

    assert summary.status == "PROBE_COMPATIBILITY_UNSUPPORTED"
    assert summary.declared_feature_dimension == bad_dimension
    assert any("positive" in reason for reason in summary.reasons)


def test_malformed_weights_sha256_is_unsupported():
    summary = summarize_probe_compatibility(
        specification=_good_spec(weights_sha256="not-a-real-hash")
    )

    assert summary.status == "PROBE_COMPATIBILITY_UNSUPPORTED"
    assert any("sha-256" in reason.lower() for reason in summary.reasons)


def test_dimension_mismatch_against_declared_pooling_is_unsupported():
    # The caller declared the run's pooled-feature dimension; it disagrees with
    # the probe's per-axis vector length, so the worker would raise
    # "incompatible hidden size" and abort the shard. Refuse honestly now.
    summary = summarize_probe_compatibility(
        specification=_good_spec(feature_dimension=200, expected_pooled_features=384)
    )

    assert summary.status == "PROBE_COMPATIBILITY_UNSUPPORTED"
    assert summary.dimension_consistent is False
    assert summary.declared_feature_dimension == 200
    assert summary.expected_pooled_features == 384
    assert any("incompatible hidden size" in reason for reason in summary.reasons)


def test_multiple_problems_are_all_reported():
    # An honest gate names every reason it refuses, not just the first.
    summary = summarize_probe_compatibility(
        specification=ProbeReadoutSpecification(
            schema_version="wrong",
            axes=(),
            feature_dimension=None,
        )
    )

    assert summary.status == "PROBE_COMPATIBILITY_UNSUPPORTED"
    assert len(summary.reasons) >= 3


# ---------------------------------------------------------------------------
# Loadable specs -> DECLARED (never VERIFIED at this tier)
# ---------------------------------------------------------------------------


def test_good_spec_is_declared_not_verified():
    summary = summarize_probe_compatibility(specification=_good_spec())

    assert summary.status == "PROBE_COMPATIBILITY_DECLARED"
    assert summary.accepted is True
    assert summary.probe_loadable is True
    assert summary.schema_version == REQUIRED_PROBE_SCHEMA_VERSION
    assert summary.axis_count == 3
    assert summary.declared_feature_dimension == 200
    assert summary.definition_sha256 == LOCKED_TKS_DEFINITION_SHA256
    assert summary.tks_definition_locked is True
    assert summary.reasons == ()
    # Worker-side load is the only place VERIFIED can be claimed.
    assert summary.status != "PROBE_COMPATIBILITY_VERIFIED"
    assert summary.weights_hash_verified is False


def test_dimension_consistent_is_none_without_declared_pooling():
    # Without expected_pooled_features the final match is confirmed worker-side;
    # the gate must NOT claim consistency it has not checked.
    summary = summarize_probe_compatibility(specification=_good_spec())

    assert summary.status == "PROBE_COMPATIBILITY_DECLARED"
    assert summary.dimension_consistent is None
    assert "worker-side" in summary.notice


def test_dimension_match_against_declared_pooling_is_consistent():
    summary = summarize_probe_compatibility(
        specification=_good_spec(feature_dimension=512, expected_pooled_features=512)
    )

    assert summary.status == "PROBE_COMPATIBILITY_DECLARED"
    assert summary.dimension_consistent is True
    assert summary.expected_pooled_features == 512


def test_wellformed_weights_sha256_is_recorded_but_not_verified():
    digest = "a" * 64
    summary = summarize_probe_compatibility(
        specification=_good_spec(weights_sha256=digest)
    )

    assert summary.status == "PROBE_COMPATIBILITY_DECLARED"
    assert summary.weights_sha256 == digest
    # Declared, not verified: the worker recomputes the hash against real weights.
    assert summary.weights_hash_verified is False


def test_uppercase_weights_sha256_is_normalized_lowercase():
    summary = summarize_probe_compatibility(
        specification=_good_spec(weights_sha256="A" * 64)
    )

    assert summary.status == "PROBE_COMPATIBILITY_DECLARED"
    assert summary.weights_sha256 == "a" * 64


def test_probe_id_is_recorded_when_present():
    summary = summarize_probe_compatibility(
        specification=_good_spec(probe_id="cas-pythia-linear-2026-06")
    )

    assert summary.probe_id == "cas-pythia-linear-2026-06"
    assert "cas-pythia-linear-2026-06" in summary.notice


def test_notice_is_honest_about_declared_not_validated():
    # A frontier run is EXPERIMENTAL_NOT_VALIDATED by definition; the gate must
    # certify loadability WITHOUT implying the probe's scores are validated.
    summary = summarize_probe_compatibility(specification=_good_spec())

    assert "EXPERIMENTAL_NOT_VALIDATED" in summary.notice
    assert "NOT" in summary.notice


def test_summary_to_dict_round_trips_keys():
    summary = summarize_probe_compatibility(specification=_good_spec())
    data = summary.to_dict()

    assert data["status"] == "PROBE_COMPATIBILITY_DECLARED"
    assert data["schema_version"] == REQUIRED_PROBE_SCHEMA_VERSION
    assert data["axis_count"] == 3
    assert isinstance(data["axes"], list)
    assert data["probe_loadable"] is True
    assert data["definition_sha256"] == LOCKED_TKS_DEFINITION_SHA256
    assert data["tks_definition_locked"] is True
    assert data["weights_hash_verified"] is False
    assert isinstance(data["reasons"], list)


# ---------------------------------------------------------------------------
# Frontier validator: raises on UNSUPPORTED, returns on loadable
# ---------------------------------------------------------------------------


def test_validate_frontier_probe_raises_without_specification():
    with pytest.raises(ValueError) as exc:
        validate_frontier_probe_compatibility(specification=None)

    assert "frontier-scale run refused" in str(exc.value)
    assert "incompatible CAS probe readout" in str(exc.value)


def test_validate_frontier_probe_raises_for_wrong_schema():
    with pytest.raises(ValueError) as exc:
        validate_frontier_probe_compatibility(
            specification=_good_spec(schema_version="cas_probe_linear_v2")
        )

    assert "frontier-scale run refused" in str(exc.value)


def test_validate_frontier_probe_returns_summary_for_loadable_spec():
    summary = validate_frontier_probe_compatibility(specification=_good_spec())

    assert summary.status == "PROBE_COMPATIBILITY_DECLARED"
    assert summary.probe_loadable is True
