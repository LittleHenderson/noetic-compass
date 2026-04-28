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
