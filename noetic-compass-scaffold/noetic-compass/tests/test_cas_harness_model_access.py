"""Unit tests for the model-access modality gate (run-gate 2).

These exercise the honesty contract at the service layer, mirroring the
provenance (5), architecture (6), probe (7), and compute (3) gates'
declared-vs-verified split -- but with one structural difference: this gate is
*universal*, not frontier-stricter. Mechanistic reachability is a precondition
of the probe method itself (the worker hooks decoder layers and pools
hidden-state activations to compute the ``cas_axis_readout``), so an unreachable
target is refused at *every* size, not just past the frontier.

* ``open_weight`` (locally loadable) -> ``MODEL_ACCESS_DECLARED``: enough to
  create a run, never on its own a verdict. ``mechanistic_probe_supported`` is
  ``True`` but ``access_verified`` stays ``False`` -- confirming a model is
  genuinely loadable means loading it, which only the workers do.
* A hosted API, black box, output-only interface, an empty declaration, or an
  unrecognized string -> ``MODEL_ACCESS_UNSUPPORTED`` with a reason that names
  the mechanical limit and points the caller at the behavioral ``target/verify``
  path. The validator raises ``ValueError`` (callers turn that into HTTP 422).
* ``MODEL_ACCESS_VERIFIED`` is reserved for the fleet, the only place weights are
  actually loaded, so it is never produced at the API tier.
"""

from __future__ import annotations

import dataclasses

import pytest

from api.services.cas_harness_model_access import (
    MECHANISTIC_ACCESS_MODE,
    ModelAccessSummary,
    mechanistic_access_requirement_notice,
    summarize_model_access,
    validate_distributed_model_access,
)


# ---------------------------------------------------------------------------
# open_weight -> DECLARED (never VERIFIED at the API tier)
# ---------------------------------------------------------------------------


def test_open_weight_is_declared_not_verified() -> None:
    summary = summarize_model_access(declared_mode="open_weight")

    assert summary.status == "MODEL_ACCESS_DECLARED"
    assert summary.accepted is True
    assert summary.mechanistic_probe_supported is True
    # Confirming loadability means loading the weights -- only the fleet does that.
    assert summary.access_verified is False
    assert summary.declared_mode == "open_weight"
    assert summary.reasons == ()


def test_open_weight_constant_is_the_one_mechanistic_mode() -> None:
    assert MECHANISTIC_ACCESS_MODE == "open_weight"
    summary = summarize_model_access(declared_mode=MECHANISTIC_ACCESS_MODE)
    assert summary.status == "MODEL_ACCESS_DECLARED"


@pytest.mark.parametrize("raw", ["OPEN_WEIGHT", "  open_weight  ", "Open_Weight", "open_weight\n"])
def test_open_weight_normalization(raw: str) -> None:
    """Case/whitespace variants normalize to the canonical declared mode."""

    summary = summarize_model_access(declared_mode=raw)
    assert summary.status == "MODEL_ACCESS_DECLARED"
    assert summary.declared_mode == "open_weight"


# ---------------------------------------------------------------------------
# hosted / black-box / output-only / empty / unknown -> UNSUPPORTED
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mode",
    ["hosted_api", "black_box", "output_only"],
)
def test_recognized_non_mechanistic_modes_are_unsupported(mode: str) -> None:
    summary = summarize_model_access(declared_mode=mode)

    assert summary.status == "MODEL_ACCESS_UNSUPPORTED"
    assert summary.accepted is False
    assert summary.mechanistic_probe_supported is False
    assert summary.access_verified is False
    assert summary.declared_mode == mode
    # Every refusal names the open_weight remedy (existing route tests assert this).
    assert any("open_weight" in reason for reason in summary.reasons)
    # ... and points at the behavioral fallback rather than dead-ending.
    assert any("target/verify" in reason for reason in summary.reasons)


def test_unsupported_reason_names_the_cas_axis_readout_limit() -> None:
    summary = summarize_model_access(declared_mode="hosted_api")
    joined = " ".join(summary.reasons)
    # The refusal is grounded in a real mechanical limit, not an invented rule.
    assert "cas_axis_readout" in joined
    assert "hidden-state activations" in joined


def test_empty_declaration_is_unsupported() -> None:
    summary = summarize_model_access(declared_mode="")

    assert summary.status == "MODEL_ACCESS_UNSUPPORTED"
    assert summary.accepted is False
    assert summary.declared_mode == "(unspecified)"
    assert any("open_weight" in reason for reason in summary.reasons)
    assert any("no model access mode was declared" in reason for reason in summary.reasons)


@pytest.mark.parametrize("raw", ["   ", "\t", "\n"])
def test_whitespace_only_declaration_is_unsupported(raw: str) -> None:
    summary = summarize_model_access(declared_mode=raw)
    assert summary.status == "MODEL_ACCESS_UNSUPPORTED"
    assert summary.declared_mode == "(unspecified)"


def test_unknown_mode_is_refused_generically_but_still_named() -> None:
    summary = summarize_model_access(declared_mode="quantum_oracle")

    assert summary.status == "MODEL_ACCESS_UNSUPPORTED"
    assert summary.accepted is False
    assert summary.declared_mode == "quantum_oracle"
    joined = " ".join(summary.reasons)
    assert "quantum_oracle" in joined
    assert "open_weight" in joined


# ---------------------------------------------------------------------------
# notice / to_dict / immutability
# ---------------------------------------------------------------------------


def test_notice_is_honest_about_the_api_tier() -> None:
    notice = mechanistic_access_requirement_notice()
    assert "mechanistic" in notice
    assert "open-weight" in notice
    # The notice must not let a reader mistake declared for verified.
    assert "never at the API tier" in notice


def test_every_summary_carries_the_notice() -> None:
    for mode in ["open_weight", "hosted_api", ""]:
        summary = summarize_model_access(declared_mode=mode)
        assert summary.notice == mechanistic_access_requirement_notice()


def test_to_dict_round_trip_shape() -> None:
    summary = summarize_model_access(declared_mode="black_box")
    payload = summary.to_dict()

    assert set(payload) == {
        "status",
        "declared_mode",
        "mechanistic_probe_supported",
        "access_verified",
        "notice",
        "reasons",
    }
    assert payload["status"] == "MODEL_ACCESS_UNSUPPORTED"
    assert payload["mechanistic_probe_supported"] is False
    assert payload["access_verified"] is False
    assert isinstance(payload["reasons"], list)
    assert payload["reasons"]  # non-empty for a refusal


def test_summary_is_frozen() -> None:
    summary = summarize_model_access(declared_mode="open_weight")
    with pytest.raises(dataclasses.FrozenInstanceError):
        summary.status = "MODEL_ACCESS_VERIFIED"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# validate_distributed_model_access -- raises on UNSUPPORTED, returns on DECLARED
# ---------------------------------------------------------------------------


def test_validate_returns_summary_for_open_weight() -> None:
    summary = validate_distributed_model_access(declared_mode="open_weight")
    assert isinstance(summary, ModelAccessSummary)
    assert summary.status == "MODEL_ACCESS_DECLARED"


@pytest.mark.parametrize(
    "mode",
    ["hosted_api", "black_box", "output_only", "", "   ", "something_else"],
)
def test_validate_raises_for_unsupported(mode: str) -> None:
    with pytest.raises(ValueError) as excinfo:
        validate_distributed_model_access(declared_mode=mode)
    message = str(excinfo.value)
    assert "unsupported model access mode" in message
    assert "open_weight" in message
