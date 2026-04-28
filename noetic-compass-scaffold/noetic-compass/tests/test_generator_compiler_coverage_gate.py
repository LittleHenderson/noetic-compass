"""Generator-vs-compiler compatibility gate.

These tests cover representative generated-style CAS expressions without
exercising generator internals. Direct generator/synthesizer behavior belongs
in the generator test suite; this file only asserts compiler compatibility for
the surfaces that generated data is expected to emit.
"""

from __future__ import annotations

import pytest

from api.notation.compiler import compile_expression


MEMBER = chr(0x2208)
SUBSET_EQ = chr(0x2286)


VALID_GENERATED_SURFACE_CASES = [
    pytest.param("^2^C_{F2}", "state", id="v74-single-state"),
    pytest.param("^2^C_{F2} * ^4^C_{F2}", "state", id="v74-same-domain-product"),
    pytest.param("^2^P_{F2} -> ^5^E_{F2}", "relation", id="v74-domain-descent"),
    pytest.param("^2^C_{F2}|A", "state", id="v75-state-register"),
    pytest.param("^2|T^C_{F2|A}", "state", id="v75-independent-registers"),
    pytest.param(
        "Theta(Omega_book) = 2*F_2 + 3*F_3 -> Omega_book",
        "recipe",
        id="v76-omega-recipe",
    ),
    pytest.param("S = {F_2: 7, F_3: 5, ^5^C: 4}", "state_vector", id="v76-state-vector"),
    pytest.param("Y_T(Omega_book)", "yield_expression", id="v76-yield-query"),
    pytest.param("^3^P|<A,f,T>", "state", id="v77-register-set"),
    pytest.param("^3^P|A + ^3^P|f", "state", id="v77-same-noetic-copresence"),
    pytest.param(
        "(^3^P|A * ^3^P|f * ^3^P|T) = ^3^P|Omega_refusal",
        "state",
        id="v77-named-emergent",
    ),
    pytest.param(
        f"StateCluster{{^2^P, ^7^O}} {SUBSET_EQ} States",
        "meta_assertion",
        id="meta-state-cluster-subset",
    ),
    pytest.param(
        "StateCluster{^2^P, ^7^O} union StateCluster{^3^P, ^4^C}",
        "meta_set",
        id="meta-set-union",
    ),
    pytest.param("Coordinate{^2, P, F2, A}", "tuple", id="meta-coordinate"),
    pytest.param(
        "Pullback(NoeticCluster{^2, ^7}, NoeticCluster{^7, ^8})",
        "meta_set",
        id="meta-finite-pullback",
    ),
    pytest.param(
        "CoverOf(SubFoundations, Foundation_1, Foundation_2, Foundation_3, "
        "Foundation_4, Foundation_5, Foundation_6, Foundation_7)",
        "meta_set",
        id="meta-cover",
    ),
]


@pytest.mark.parametrize(("source", "expected_kind"), VALID_GENERATED_SURFACE_CASES)
def test_generated_surface_representatives_compile(source: str, expected_kind: str) -> None:
    artifact = compile_expression(source)

    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    assert result["kind"] == expected_kind


def test_generated_rule_four_violation_is_rejected_for_invalid_training_examples() -> None:
    artifact = compile_expression("^3^P|A * ^3^P|f")

    assert not artifact.valid
    assert artifact.error is not None
    assert "Clarification 10" in artifact.error
    assert "Section 4" in artifact.error


def test_generated_meta_logic_diagram_projection_is_available() -> None:
    artifact = compile_expression(
        f"NoeticCluster{{^2, ^7}} {MEMBER} Noetics; "
        "^5^P -> ^5^C; "
        "Theta(Omega_safe) = 0.4*^3^P + 0.6*^2^C -> Omega_safe"
    )
    assert artifact.valid, artifact.error

    diagram = artifact.diagram()

    assert diagram["kind"] == "cas_diagram"
    assert {"dependency", "radial", "recipe", "topos"}.issubset(set(diagram["layouts"]))
    assert any(edge["kind"] == "dependency" for edge in diagram["edges"])
    assert any(edge["kind"] == "recipe_prerequisite" for edge in diagram["edges"])


@pytest.mark.xfail(strict=True, reason="Legacy invalid v7.5 shape places register before drive subscript.")
def test_legacy_v75_register_order_invalid_shape() -> None:
    artifact = compile_expression("^2^C|A_{F2}")

    assert artifact.valid, artifact.error


@pytest.mark.xfail(strict=True, reason="Legacy invalid v7.6 shape emits bare production target names.")
def test_legacy_v76_bare_target_invalid_shape() -> None:
    artifact = compile_expression("Theta(book) = 2*state_12 -> book")

    assert artifact.valid, artifact.error


@pytest.mark.xfail(strict=True, reason="Legacy invalid v7.7 shape uses 'x' as cross-register separator.")
def test_legacy_v77_x_separator_invalid_shape() -> None:
    artifact = compile_expression("(^1|A x ^1|E) = ^1|Omega_presence")

    assert artifact.valid, artifact.error
