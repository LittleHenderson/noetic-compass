"""Tests for the admitted meta-logic construct generator."""

from __future__ import annotations

import sys
from pathlib import Path

from cas_synthetic.generator import MetaLogicGenerator
from cas_synthetic.validation import CompositeValidator, SchemaValidator

_COMPILER_ROOT = Path(__file__).resolve().parents[2] / "noetic-compass-scaffold" / "noetic-compass"
if str(_COMPILER_ROOT) not in sys.path:
    sys.path.insert(0, str(_COMPILER_ROOT))

try:
    from api.notation import compile_expression
except Exception:  # pragma: no cover - test environment import fallback
    compile_expression = None


class TestMetaLogicGenerator:
    def test_bucket_tag(self):
        gen = MetaLogicGenerator(seed=1)
        ex = next(gen.iter_examples(1))
        assert ex.bucket == "meta_logic"

    def test_schema_and_composite_valid(self):
        gen = MetaLogicGenerator(seed=7)
        schema = SchemaValidator(strict=False)
        composite = CompositeValidator()
        for ex in gen.iter_examples(50):
            d = ex.to_dict()
            assert schema.validate(d) == []
            report = composite.validate(d)
            assert report.ok, report.issues

    def test_all_template_expressions_compile(self):
        assert compile_expression is not None
        gen = MetaLogicGenerator(seed=7)
        for construct in gen.constructs:
            artifact = compile_expression(construct["expression"])
            assert artifact.valid, construct["expression"]

    def test_construct_family_coverage_from_templates(self):
        gen = MetaLogicGenerator(seed=3)
        expressions = {item["expression"] for item in gen.constructs}
        required_tokens = [
            "NoeticCluster{^2, ^7}",
            "StateCluster{^2^P, ^7^O}",
            "StateVariantCluster{^3^P_{F2}|A, ^2^C|f}",
            "RelationCluster{^5^P -> ^5^C, ^5^C -> ^5^E}",
            "∪",
            "∩",
            "∖",
            "∈ Noetics",
            "⊆ States",
            "Coordinate{^2, P, F2, A}",
            "<^2, P, F2, A>",
            "Product(Noetics, Domains)",
            "Pullback(NoeticCluster{^2, ^7}, NoeticCluster{^7, ^8})",
            "CoverOf(SubFoundations, Foundation_1, Foundation_2, Foundation_3, Foundation_4, Foundation_5, Foundation_6, Foundation_7)",
            "PartitionOf(SubFoundations, Foundation_1, Foundation_2, Foundation_3, Foundation_4, Foundation_5, Foundation_6, Foundation_7)",
        ]
        for token in required_tokens:
            assert any(token in expr for expr in expressions)

    def test_pullback_is_finite_meet_only(self):
        gen = MetaLogicGenerator(seed=2)
        pullback = [
            item for item in gen.constructs
            if item["expression"] == "Pullback(NoeticCluster{^2, ^7}, NoeticCluster{^7, ^8})"
        ][0]
        # The Pullback construct must be documented as the finite meet
        # constructor (not a general categorical pullback) somewhere in
        # its response copy — either the literal `response` field (legacy)
        # or in the response_templates pool used by operand-randomized
        # rendering (current).
        candidates = list(pullback.get("response_templates") or [])
        if "response" in pullback:
            candidates.append(pullback["response"])
        assert any("finite meet/intersection" in t for t in candidates), candidates
        assert any(
            "not a claim of general categorical pullbacks" in t for t in candidates
        ), candidates

    def test_seed_reproducibility(self):
        g1 = MetaLogicGenerator(seed=99)
        g2 = MetaLogicGenerator(seed=99)
        a = [e.cas_expression for e in g1.iter_examples(10)]
        b = [e.cas_expression for e in g2.iter_examples(10)]
        assert a == b
