"""Tests for Path D Wave 2F compile-trace generator.

Covers:
- Smoke: traces produced for ~50 seeds across all 10 grammar categories.
- Schema conformance: every trace has the 6 required fields; optional
  fields present when applicable, omitted when not.
- Fractal canonical-form spot checks (involution-pair cancellation +
  identity elimination): ⟨2:3⟩ → ⟨0⟩, ⟨5:6:5:6⟩ → ⟨0⟩, ⟨2:3:8⟩ → ⟨8⟩,
  ⟨0⟩ → ⟨0⟩.
- RPM-chain detection: known good chain (A0 → D) is satisfied, known
  broken chain (A0 → P, skip arrow) reports broken_at.
- Recipe analysis: known recipe with Θ + 3 ingredients + named Ω parses,
  reports balanced stoichiometry.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = (
    _REPO_ROOT
    / "cas-synthetic"
    / "scripts"
    / "generate_path_d_compile_traces.py"
)


def _load_generator():
    """Load the generator module from its file path (script-style import)."""
    name = "cas_synthetic_path_d_compile_traces"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None, "spec/loader missing"
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def gen():
    return _load_generator()


@pytest.fixture(scope="module")
def compile_expression(gen):
    compiler = gen._load_compiler()
    return compiler.compile_expression


# ---------------------------------------------------------------------------
# Pure-Python helpers — no compiler invocation needed.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ([2, 3], [0]),
        ([3, 2], [0]),
        ([5, 6, 5, 6], [0]),
        ([6, 5], [0]),
        ([8, 9], [0]),
        ([2, 3, 8], [8]),
        ([0], [0]),
        ([1], [1]),
        ([2, 3, 5, 6, 8, 9], [0]),
        ([7, 0, 7], [7, 7]),
        # Adjacent identical operators are NOT a dual pair; no cancellation.
        ([4, 4], [4, 4]),
    ],
)
def test_canonicalize_fractal(gen, raw, expected):
    assert gen.canonicalize_fractal(raw) == expected


@pytest.mark.parametrize(
    "canonical, expected_class",
    [
        ([0], "Neutral"),
        # Self-dual non-identity sequences settle on a fixed point.
        ([1], "Stabilizing"),
        ([4], "Stabilizing"),
        ([7], "Stabilizing"),
    ],
)
def test_classify_fractal_basic(gen, canonical, expected_class):
    assert gen.classify_fractal(canonical) == expected_class


# ---------------------------------------------------------------------------
# Smoke: produce traces over a representative sample (~50 seeds across all
# 10 grammar categories) using the actual seeds file.
# ---------------------------------------------------------------------------


_SEEDS_PATH = _REPO_ROOT / "cas-synthetic" / "data" / "path_d" / "seeds.jsonl"


def _read_seeds() -> list[dict]:
    with open(_SEEDS_PATH, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _sample_per_category(seeds: list[dict], k: int = 5) -> list[dict]:
    """Pick k seeds from each grammar category — covers all 10 categories."""
    by_cat: dict[str, list[dict]] = {}
    for s in seeds:
        by_cat.setdefault(s["grammar_category"], []).append(s)
    sample: list[dict] = []
    for cat, lst in by_cat.items():
        sample.extend(lst[:k])
    return sample


@pytest.fixture(scope="module")
def smoke_traces(gen, compile_expression):
    if not _SEEDS_PATH.exists():
        pytest.skip(f"seeds.jsonl not found at {_SEEDS_PATH}")
    seeds = _read_seeds()
    sample = _sample_per_category(seeds, k=5)
    traces: list[tuple[dict, dict]] = []
    for s in sample:
        artifact = compile_expression(s["expression"])
        trace = gen.build_trace(s, artifact)
        if trace is not None:
            traces.append((s, trace))
    return traces


def test_smoke_traces_produced_for_all_grammar_categories(smoke_traces):
    """At least one trace per grammar category, ≥30 traces total."""
    cats = {s["grammar_category"] for s, _ in smoke_traces}
    expected_cats = {
        "state_literal",
        "binary_composition",
        "cross_register_omega",
        "recipe",
        "meta_logic_relation",
        "fractal_sequence",
        "let_binding",
        "diagram_export",
        "rpm_chain",
        "inversion",
    }
    missing = expected_cats - cats
    assert not missing, f"missing categories in smoke: {sorted(missing)}"
    assert len(smoke_traces) >= 30, f"expected ≥30 smoke traces, got {len(smoke_traces)}"


_REQUIRED_FIELDS = (
    "trace_id",
    "source_seed_id",
    "expression",
    "parse_tree",
    "ast_summary",
    "admissibility",
)


def test_schema_conformance_required_fields(smoke_traces):
    for _seed, trace in smoke_traces:
        for field in _REQUIRED_FIELDS:
            assert field in trace, f"missing required field {field} in trace {trace.get('trace_id')}"
        # ast_summary diagnostic shape.
        ast_sum = trace["ast_summary"]
        assert "n_nodes" in ast_sum and "depth" in ast_sum and "node_type_counts" in ast_sum
        # admissibility shape.
        adm = trace["admissibility"]
        assert "passes" in adm and "checks_performed" in adm and "violations" in adm
        # All seeds in the smoke set are compiler_validated, so passes
        # must be True.
        assert adm["passes"] is True


def test_optional_fields_present_when_applicable(smoke_traces):
    """Optional fields populated for seeds in the relevant grammar category."""
    for seed, trace in smoke_traces:
        cat = seed["grammar_category"]
        expr = seed["expression"]

        if cat == "fractal_sequence":
            assert "fractal_canonical" in trace, (
                f"fractal_canonical missing on fractal_sequence trace {trace['trace_id']}"
            )
            f = trace["fractal_canonical"]
            assert "raw" in f and "simplified" in f and "convergence_class" in f
        elif cat == "rpm_chain":
            assert "rpm_result" in trace, (
                f"rpm_result missing on rpm_chain trace {trace['trace_id']}"
            )
        elif cat == "recipe":
            # Recipes always carry Θ, so recipe_analysis must be populated.
            assert "recipe_analysis" in trace, (
                f"recipe_analysis missing on recipe trace {trace['trace_id']}"
            )
            r = trace["recipe_analysis"]
            assert "target_omega" in r and "ingredients" in r

        # Register analysis: present iff the expression has any |R or |⟨…⟩.
        has_register = ("|T" in expr or "|A" in expr or "|f" in expr or "|E" in expr) and "Ω_" not in expr.split("|")[-1]
        # Drop the noisy heuristic; just verify when register tags exist
        # we get analysis (omega-only |Ω_… is intentionally a register on
        # a state literal, so it counts as a register).
        if any(tag in expr for tag in ("|T", "|A", "|f", "|E")):
            assert "register_analysis" in trace, (
                f"register_analysis missing on register-tagged expression {expr}"
            )


def test_optional_fields_omitted_when_not_applicable(smoke_traces):
    """Plain state literals must NOT carry the optional analysis blocks."""
    for seed, trace in smoke_traces:
        if seed["grammar_category"] != "state_literal":
            continue
        expr = seed["expression"]
        # Plain `^N` / `^N^D` / `^N^D_{Fk}` literals have no register, no
        # fractal, no recipe, no RPM chain, no meta-logic constructor.
        bare = (
            "|" not in expr
            and "Phi" not in expr
            and "Φ" not in expr
            and "Θ" not in expr
            and "Theta" not in expr
            and "Cluster" not in expr
            and "stage" not in expr
            and "RPM" not in expr
        )
        if bare:
            assert "fractal_canonical" not in trace
            assert "rpm_result" not in trace
            assert "register_analysis" not in trace
            assert "recipe_analysis" not in trace
            assert "meta_logic_analysis" not in trace


# ---------------------------------------------------------------------------
# Fractal canonical-form spot checks via the actual fractal_analysis path.
# ---------------------------------------------------------------------------


def test_fractal_analysis_two_three_cancels(gen):
    out = gen._fractal_analysis("Phi<2:3>")
    assert out is not None
    assert out["raw"] == "⟨2:3⟩"
    assert out["simplified"] == "⟨0⟩"
    assert out["convergence_class"] == "Neutral"


def test_fractal_analysis_5656_cancels(gen):
    out = gen._fractal_analysis("Φ⟨5:6:5:6⟩")
    assert out is not None
    assert out["simplified"] == "⟨0⟩"
    assert out["convergence_class"] == "Neutral"


def test_fractal_analysis_partial_cancellation(gen):
    out = gen._fractal_analysis("Phi<2:3:8>")
    assert out is not None
    assert out["simplified"] == "⟨8⟩"


def test_fractal_analysis_returns_none_when_absent(gen):
    assert gen._fractal_analysis("^2^P") is None


# ---------------------------------------------------------------------------
# RPM-chain detection spot checks.
# ---------------------------------------------------------------------------


def test_rpm_chain_good_arrow_satisfied(gen, compile_expression):
    """A0 -> D arrow is adjacent on the canonical pathway → satisfied."""
    expression = (
        "let stageA0_t1 = ^0^P; "
        "let stageD3_t1 = ^2^P_{F3}; "
        "let stageW3_t1 = ^2^C_{F3}; "
        "let stageP3_t1 = ^2^E_{F3}; "
        "stageA0_t1 -> stageD3_t1"
    )
    artifact = compile_expression(expression)
    out = gen._rpm_analysis(expression, artifact)
    assert out is not None
    assert out["satisfied"] is True
    assert out["broken_at"] is None
    assert "A0" in out["chain"]


def test_rpm_chain_skip_arrow_broken(gen, compile_expression):
    """A0 -> P skip-arrow is not adjacent → broken_at is reported."""
    expression = (
        "let stageA0_t2 = ^0^P; "
        "let stageD2_t2 = ^4^P_{F2}; "
        "let stageW2_t2 = ^4^C_{F2}; "
        "let stageP2_t2 = ^4^E_{F2}; "
        "stageA0_t2 -> stageP2_t2"
    )
    artifact = compile_expression(expression)
    out = gen._rpm_analysis(expression, artifact)
    assert out is not None
    # Even if the compiler accepts the relation, our RPM-pathway analysis
    # tags this as a broken chain because A0 → P is not adjacent on the
    # canonical pathway.
    assert out["broken_at"] is not None
    assert "A0" in out["broken_at"] or "P" in out["broken_at"]


# ---------------------------------------------------------------------------
# Recipe analysis spot check — Θ + 3 ingredients + named Ω.
# ---------------------------------------------------------------------------


def test_recipe_analysis_three_ingredients(gen):
    expression = (
        "Θ(Ω_synthesis_07) = "
        "1.5*^6^P + 0.7*^2^C|A + 1*^4^E_{F2} → Ω_synthesis_07"
    )
    out = gen._recipe_analysis(expression)
    assert out is not None
    assert out["target_omega"] == "Ω_synthesis_07"
    assert len(out["ingredients"]) == 3
    coefficients = [ing["coefficient"] for ing in out["ingredients"]]
    assert coefficients == [1.5, 0.7, 1.0]
    assert out["stoichiometry_balanced"] is True


def test_recipe_analysis_returns_none_without_theta(gen):
    assert gen._recipe_analysis("^2^P + ^3^P") is None


# ---------------------------------------------------------------------------
# Register-analysis spot checks (v7.7 operator discipline).
# ---------------------------------------------------------------------------


def test_register_analysis_cross_register_omega_satisfied(gen):
    expression = "(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω_resolve"
    out = gen._register_analysis(expression)
    assert out is not None
    assert out["single_or_multi"] == "cross-register-integration"
    assert out["v77_operator_discipline_check"] == "satisfied"
    assert sorted(out["registers_used"]) == ["A", "T", "f"]


def test_register_analysis_set_notation(gen):
    expression = "^3^P|⟨A,f,T⟩"
    out = gen._register_analysis(expression)
    assert out is not None
    assert out["single_or_multi"] == "multi-register-set"
    assert out["v77_operator_discipline_check"] == "satisfied"


def test_register_analysis_single(gen):
    out = gen._register_analysis("^2^C|f")
    assert out is not None
    assert out["single_or_multi"] == "single"
    assert out["registers_used"] == ["f"]
