"""Tests for V77RuleFourGenerator.

Covers compliant examples (no Rule 4 violation) and deliberate violation
examples (labeled is_valid=false with distance_to_valid > 0).
"""

from __future__ import annotations

import re

import pytest

from cas_synthetic.generator import V77RuleFourGenerator


class TestV77RuleFour:
    def test_bucket_tag(self):
        gen = V77RuleFourGenerator(seed=1)
        ex = next(gen.iter_examples(1))
        assert ex.bucket == "v77_rule_four"

    def test_register_labels_populated(self):
        gen = V77RuleFourGenerator(seed=1)
        for ex in gen.iter_examples(20):
            assert ex.register_labels, "Rule 4 examples must carry register labels"

    def test_violation_rate_within_tolerance(self):
        """20% of Rule 4 bucket should be deliberate violations."""
        gen = V77RuleFourGenerator(seed=42)
        batch = list(gen.iter_examples(500))
        violations = [ex for ex in batch if not ex.is_valid]
        rate = len(violations) / len(batch)
        # Expect ~0.20 ± 0.05 at n=500
        assert 0.14 <= rate <= 0.26, f"unexpected violation rate: {rate}"

    def test_violations_have_distance(self):
        gen = V77RuleFourGenerator(seed=42)
        for ex in gen.iter_examples(500):
            if not ex.is_valid:
                assert ex.distance_to_valid > 0
                assert ex.violation_type == "same_noetic_cross_no_emergent"

    def test_compliant_examples_have_zero_distance(self):
        gen = V77RuleFourGenerator(seed=42)
        for ex in gen.iter_examples(500):
            if ex.is_valid:
                assert ex.distance_to_valid == 0.0
                assert ex.violation_type is None

    def test_violation_expression_uses_times(self):
        gen = V77RuleFourGenerator(seed=42)
        for ex in gen.iter_examples(500):
            if not ex.is_valid:
                # Must include times operator without `=` (no emergent)
                assert " x " in ex.cas_expression
                assert "=" not in ex.cas_expression

    def test_valid_emergent_expression_has_omega_label(self):
        gen = V77RuleFourGenerator(seed=42)
        saw_omega = False
        for ex in gen.iter_examples(500):
            if ex.is_valid and ex.omega_labels:
                saw_omega = True
                assert "=" in ex.cas_expression
                assert "Omega_" in ex.cas_expression
        assert saw_omega, "expected at least some valid examples to carry omega labels"

    def test_copresence_uses_plus(self):
        gen = V77RuleFourGenerator(seed=42)
        saw_copresence = False
        for ex in gen.iter_examples(500):
            if ex.is_valid and not ex.omega_labels and " + " in ex.cas_expression:
                saw_copresence = True
                assert " x " not in ex.cas_expression
        assert saw_copresence, "expected at least some co-presence examples"

    def test_same_noetic_only(self):
        """Rule 4 applicable only when same Noetic appears on both sides of × or +."""
        gen = V77RuleFourGenerator(seed=42)
        noetic_re = re.compile(r"\^(\d+)")
        for ex in gen.iter_examples(50):
            if " + " in ex.cas_expression or " x " in ex.cas_expression:
                noetics = set(noetic_re.findall(ex.cas_expression.split("=")[0]))
                assert len(noetics) == 1
