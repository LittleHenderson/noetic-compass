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
                # Must include Unicode `×` cross-register integration operator
                # without `=` (no named emergent — the deliberate Rule 4
                # violation pattern that the compiler rejects at typecheck).
                assert " × " in ex.cas_expression
                assert "=" not in ex.cas_expression

    def test_valid_compliant_records_do_not_carry_omega_labels(self):
        """Post-2026-05-02 contract: the compliant arm is `+` co-presence
        ONLY. The previous valid `×=Ω_*` arm was structurally identical to
        v77_omega output and 100% misclassified at the 85.1% checkpoint
        because the recoverable user_prompt could not distinguish it from
        v77_omega; removing it preserves the bucket distinction. See
        cas-native/training/runs/structured-token-20epoch-gpu-20260502-001907/
        current_unique_eval_confusion.md and the historical-note comment in
        v77_rule_four._generate_compliant.
        """

        gen = V77RuleFourGenerator(seed=42)
        for ex in gen.iter_examples(500):
            if ex.is_valid and ex.omega_labels:
                pytest.fail(
                    "v77_rule_four compliant arm must not produce records with "
                    "omega_labels post-2026-05-02 fix; got: "
                    f"{ex.cas_expression!r}"
                )

    def test_copresence_uses_plus(self):
        gen = V77RuleFourGenerator(seed=42)
        saw_copresence = False
        for ex in gen.iter_examples(500):
            if ex.is_valid and not ex.omega_labels and " + " in ex.cas_expression:
                saw_copresence = True
                assert " × " not in ex.cas_expression
        assert saw_copresence, "expected at least some co-presence examples"

    def test_same_noetic_only(self):
        """Rule 4 applicable only when same Noetic appears on both sides of × or +."""
        gen = V77RuleFourGenerator(seed=42)
        noetic_re = re.compile(r"\^(\d+)")
        for ex in gen.iter_examples(50):
            if " + " in ex.cas_expression or " × " in ex.cas_expression:
                noetics = set(noetic_re.findall(ex.cas_expression.split("=")[0]))
                assert len(noetics) == 1
