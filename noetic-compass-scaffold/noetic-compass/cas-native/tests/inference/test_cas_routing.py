"""Tests for compilability-based task routing."""
from __future__ import annotations

import pytest

from cas_native.inference.cas_routing import (
    RoutingDecision,
    route_by_compilability,
    build_prompt_from_routing,
)


# ---------------------------------------------------------------------------
# Routing — valid expressions
# ---------------------------------------------------------------------------

def test_routes_valid_state_literal_to_cas_to_english() -> None:
    routing = route_by_compilability("^7^C_{F2}|T")
    assert routing.task_type == "cas_to_english"
    assert routing.compiled is True
    assert routing.error_message is None


def test_routes_valid_binary_composition() -> None:
    routing = route_by_compilability("^2^C × ^7^C")
    assert routing.task_type == "cas_to_english"
    assert routing.compiled is True


def test_routes_valid_rpm_chain_to_cas_to_english() -> None:
    """The exact CAS body that misroutes inside the model — the
    compilability gate sees through to the structural validity and
    routes correctly."""
    rpm_chain_cas = (
        "let stageA0_3_0234 = ^0^P; "
        "let stageD3_3_0234 = ^9^P_{F3}; "
        "let stageW3_3_0234 = ^9^C_{F3}; "
        "let stageP3_3_0234 = ^9^E_{F3}; "
        "stageW3_3_0234 -> stageP3_3_0234"
    )
    routing = route_by_compilability(rpm_chain_cas)
    assert routing.task_type == "cas_to_english"
    assert routing.compiled is True


# ---------------------------------------------------------------------------
# Routing — invalid expressions
# ---------------------------------------------------------------------------

def test_routes_invalid_undefined_var_to_explanation() -> None:
    """Classic invalid_to_explanation/rpm shape: undefined target var."""
    routing = route_by_compilability(
        "let stageA0_7_5172 = ^0^P; stageA0_7_5172 -> stageW_7_5172"
    )
    assert routing.task_type == "invalid_to_explanation"
    assert routing.compiled is False
    assert routing.error_message is not None


def test_routes_invalid_parse_error() -> None:
    """Garbled source — fails at parse stage."""
    routing = route_by_compilability("^0^|A + ^0^P|T")
    assert routing.task_type == "invalid_to_explanation"
    assert routing.compiled is False
    # Parse errors should map to error_class "parse"
    assert routing.error_class == "parse"


def test_routes_invalid_op_index_out_of_range() -> None:
    """^20 is outside the 0-9 noetic range — should fail compilation."""
    routing = route_by_compilability("^20^E|f + ^1^E|E")
    assert routing.task_type == "invalid_to_explanation"
    assert routing.compiled is False


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def test_build_prompt_for_valid_uses_describe_wrapper() -> None:
    routing = RoutingDecision(task_type="cas_to_english", compiled=True)
    prompt = build_prompt_from_routing(
        source_cas="^7^C_{F2}|T", routing=routing,
    )
    assert "Describe the following CAS expression" in prompt
    assert "^7^C_{F2}|T" in prompt


def test_build_prompt_for_invalid_uses_explain_wrapper_with_error_class() -> None:
    routing = RoutingDecision(
        task_type="invalid_to_explanation",
        compiled=False,
        error_class="rpm",
        error_message="typecheck: undefined variable stageW_3_4762",
    )
    prompt = build_prompt_from_routing(
        source_cas="let X = ^0^P; X -> Y", routing=routing,
    )
    assert "Explain in plain English why" in prompt
    assert "Invalid CAS expression (error class: rpm):" in prompt
    assert "typecheck: undefined variable stageW_3_4762" in prompt
    assert "let X = ^0^P; X -> Y" in prompt


def test_routing_decision_to_dict_round_trip() -> None:
    routing = RoutingDecision(
        task_type="invalid_to_explanation",
        compiled=False,
        error_stage="EXECUTION",
        error_class="rpm",
        error_message="some error",
        error_position=42,
    )
    d = routing.to_dict()
    assert d["task_type"] == "invalid_to_explanation"
    assert d["compiled"] is False
    assert d["error_class"] == "rpm"
    assert d["error_position"] == 42
