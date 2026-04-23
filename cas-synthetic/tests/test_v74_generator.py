"""Tests for V74BaselineGenerator."""

from __future__ import annotations

import re

from cas_synthetic.generator import V74BaselineGenerator


_STATE_RE = re.compile(r"\^(\d+)\^([PCEO])_\{F(\d)\}")


class TestV74Baseline:
    def test_bucket_tag(self):
        gen = V74BaselineGenerator(seed=1)
        ex = next(gen.iter_examples(1))
        assert ex.bucket == "v74_baseline"

    def test_no_register_labels(self):
        gen = V74BaselineGenerator(seed=1)
        for ex in gen.iter_examples(20):
            assert ex.register_labels == []
            assert ex.omega_labels == []
            assert ex.production_target is None

    def test_cas_expression_shape(self):
        gen = V74BaselineGenerator(seed=1)
        for ex in gen.iter_examples(20):
            assert ex.cas_expression
            matches = _STATE_RE.findall(ex.cas_expression)
            assert matches, f"no states in {ex.cas_expression!r}"
            for op, dom, drv in matches:
                assert 0 <= int(op) <= 9
                assert dom in ("P", "C", "E", "O")
                assert 1 <= int(drv) <= 7

    def test_scores_shape(self):
        gen = V74BaselineGenerator(seed=1)
        for ex in gen.iter_examples(20):
            assert ex.scores is not None
            assert len(ex.scores["operator_scores"]) == 10
            assert len(ex.scores["domain_scores"]) == 4

    def test_seed_reproducibility(self):
        g1 = V74BaselineGenerator(seed=7)
        g2 = V74BaselineGenerator(seed=7)
        a = list(g1.iter_examples(5))
        b = list(g2.iter_examples(5))
        assert [x.cas_expression for x in a] == [x.cas_expression for x in b]

    def test_prompt_and_response_populated(self):
        gen = V74BaselineGenerator(seed=1)
        for ex in gen.iter_examples(10):
            assert ex.prompt and len(ex.prompt) > 10
            assert ex.response and len(ex.response) > 20

    def test_is_valid_true(self):
        gen = V74BaselineGenerator(seed=1)
        for ex in gen.iter_examples(20):
            assert ex.is_valid is True
            assert ex.distance_to_valid == 0.0

    def test_domain_descent_coherence(self):
        """When the expression uses ->, the left-side domain precedes the right."""
        gen = V74BaselineGenerator(seed=1)
        domain_order = {"P": 0, "C": 1, "E": 2, "O": 3}
        for ex in gen.iter_examples(100):
            if " -> " in ex.cas_expression:
                parts = ex.cas_expression.split(" -> ")
                m1 = _STATE_RE.search(parts[0])
                m2 = _STATE_RE.search(parts[1])
                if m1 and m2:
                    assert domain_order[m1.group(2)] <= domain_order[m2.group(2)]
