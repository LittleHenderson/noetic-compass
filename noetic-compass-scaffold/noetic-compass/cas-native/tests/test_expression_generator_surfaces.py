"""Expression-generator coverage for compiler-admitted CAS surfaces."""

from __future__ import annotations

from api.notation import compile_expression

from cas_native.data.expression_generator import (
    COMPILER_SURFACE_EXEMPLARS,
    TYPED_META_LOGIC_EXEMPLARS,
    V75_REGISTER_EXEMPLARS,
    V76_RECIPE_EXEMPLARS,
    V77_REGISTER_INTEGRATION_EXEMPLARS,
    CASExpressionGenerator,
)

def test_compiler_surface_exemplars_all_compile():
    assert COMPILER_SURFACE_EXEMPLARS

    for expression in COMPILER_SURFACE_EXEMPLARS:
        artifact = compile_expression(expression)
        assert artifact.valid, f"{expression}: {artifact.error}"


def test_surface_exemplar_groups_cover_requested_constructs():
    joined = "\n".join(COMPILER_SURFACE_EXEMPLARS)

    assert any("|T" in expr or "|A" in expr for expr in V75_REGISTER_EXEMPLARS)
    assert any("Theta(Omega_" in expr for expr in V76_RECIPE_EXEMPLARS)
    assert any("Y_T(Omega_" in expr or "eta(Omega_" in expr for expr in V76_RECIPE_EXEMPLARS)
    assert any("|" + chr(0x27E8) in expr for expr in V77_REGISTER_INTEGRATION_EXEMPLARS)
    assert any("= fused" in expr for expr in V77_REGISTER_INTEGRATION_EXEMPLARS)
    assert "NoeticCluster" in joined
    assert "StateVariantCluster" in joined
    assert chr(0x2208) in joined
    assert "|States| = 40" in TYPED_META_LOGIC_EXEMPLARS
    assert "Coordinate{^2, P, F2, A}" in TYPED_META_LOGIC_EXEMPLARS
    assert "Product(Noetics, Domains)" in TYPED_META_LOGIC_EXEMPLARS
    assert any(expr.startswith("CoverOf(") for expr in TYPED_META_LOGIC_EXEMPLARS)


def test_typed_meta_logic_exemplars_cover_extended_token_classes():
    """Day-1 SDG sprint Track A: surface coverage for the eight token classes
    audited in docs/working/generator_compiler_coverage_audit.md.

    Seven of the eight classes (Union, Difference, ∅, ∉, ⊂, ⊃, ⊇) are
    represented here. NoeticSet/StateSet are deliberately excluded pending a
    CONSTRUCT_SPECS update — the compiler grammar admits them but
    cas-native/model/meta_logic_constructs.py does not yet enumerate them.
    """

    joined = "\n".join(TYPED_META_LOGIC_EXEMPLARS)

    # Union ∪ — Unicode + ASCII keyword + call-form + empty-set edge.
    assert chr(0x222A) in joined
    assert any("union" in expr for expr in TYPED_META_LOGIC_EXEMPLARS)
    assert any(expr.startswith("Union(") for expr in TYPED_META_LOGIC_EXEMPLARS)

    # Difference ∖ — Unicode + ASCII keyword + call-form + empty-set edge.
    assert chr(0x2216) in joined
    assert any("setminus" in expr for expr in TYPED_META_LOGIC_EXEMPLARS)
    assert any(expr.startswith("Difference(") for expr in TYPED_META_LOGIC_EXEMPLARS)

    # Empty set ∅ — subset assertion, cardinality, reflexive subset edge.
    assert chr(0x2205) in joined
    assert f"|{chr(0x2205)}| = 0" in TYPED_META_LOGIC_EXEMPLARS

    # Not-member ∉ — typed-but-carrier-incompatible cases.
    assert chr(0x2209) in joined

    # Strict subset ⊂ — cluster strictly inside carrier.
    assert chr(0x2282) in joined

    # Superset ⊃ and superset-or-equal ⊇.
    assert chr(0x2283) in joined
    assert chr(0x2287) in joined


def test_extended_token_class_invalid_counterparts_are_rejected():
    """Verify directive-specified invalid counterparts fail at typecheck.

    These are NOT exemplars — they are negative cases ensuring the Python
    compiler enforces meta-set typing for set-operation operands. Each must
    return ``valid=False``.
    """

    invalid_cases = [
        # Bare-noetic operand on a set operation should fail.
        ("^2 " + chr(0x222A) + " ^7", "UNION requires a meta-set"),
        ("Noetics " + chr(0x2216) + " ^2", "SET_DIFF requires a meta-set"),
        ("^2 " + chr(0x2282) + " Noetics", "SUBSET requires a meta-set"),
    ]

    for expression, fragment in invalid_cases:
        artifact = compile_expression(expression)
        assert not artifact.valid, f"expected rejection: {expression}"
        assert artifact.error is not None
        assert fragment in artifact.error, (
            f"unexpected rejection reason for {expression}: {artifact.error}"
        )


def test_named_generation_modes_validate_through_compiler():
    modes = [
        "v75_register",
        "v76_recipe",
        "v77_register",
        "meta_logic",
        "compiler_surface",
    ]

    for index, mode in enumerate(modes):
        generator = CASExpressionGenerator(compile_expression, seed=index)
        result = generator.generate_and_validate(mode, max_attempts=10)
        assert result is not None, mode
        expression, artifact = result
        assert artifact.valid, f"{mode}: {expression}: {artifact.error}"


def test_compiler_surface_corpus_is_exposed_deterministically():
    generator = CASExpressionGenerator(compile_expression, seed=17)

    assert generator.compiler_surface_exemplars() == COMPILER_SURFACE_EXEMPLARS
    assert set(V75_REGISTER_EXEMPLARS).issubset(generator.compiler_surface_exemplars())
    assert set(V76_RECIPE_EXEMPLARS).issubset(generator.compiler_surface_exemplars())
    assert set(V77_REGISTER_INTEGRATION_EXEMPLARS).issubset(
        generator.compiler_surface_exemplars()
    )
    assert set(TYPED_META_LOGIC_EXEMPLARS).issubset(
        generator.compiler_surface_exemplars()
    )
