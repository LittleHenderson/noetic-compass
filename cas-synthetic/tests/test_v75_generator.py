"""Tests for V75RegisterGenerator."""

from __future__ import annotations

import re

from cas_synthetic.generator import V75RegisterGenerator


_OPERAND_RE = re.compile(r"\^(\d+)\^([PCEO])\|([TAfE])_\{F(\d)\}")


class TestV75Register:
    def test_bucket_tag(self):
        gen = V75RegisterGenerator(seed=1)
        ex = next(gen.iter_examples(1))
        assert ex.bucket == "v75_register"

    def test_has_register_labels(self):
        gen = V75RegisterGenerator(seed=1)
        for ex in gen.iter_examples(20):
            assert ex.register_labels, "expected register labels populated"
            for lbl in ex.register_labels:
                assert lbl["register"] in ("T", "A", "f", "E")

    def test_register_in_expression(self):
        gen = V75RegisterGenerator(seed=1)
        for ex in gen.iter_examples(20):
            matches = _OPERAND_RE.findall(ex.cas_expression)
            assert matches
            regs_in_expr = [m[2] for m in matches]
            regs_in_labels = [lbl["register"] for lbl in ex.register_labels]
            assert regs_in_expr == regs_in_labels

    def test_no_omega_or_production(self):
        gen = V75RegisterGenerator(seed=1)
        for ex in gen.iter_examples(20):
            assert ex.omega_labels == []
            assert ex.production_target is None

    def test_affective_is_lowercase(self):
        """Clarification 8 mandates lowercase f for Affective."""
        gen = V75RegisterGenerator(seed=1)
        for ex in gen.iter_examples(50):
            assert "|F_" not in ex.cas_expression  # wrong
            for lbl in ex.register_labels:
                assert lbl["register"] != "F"

    def test_seed_reproducibility(self):
        g1 = V75RegisterGenerator(seed=11)
        g2 = V75RegisterGenerator(seed=11)
        a = list(g1.iter_examples(3))
        b = list(g2.iter_examples(3))
        assert [x.cas_expression for x in a] == [x.cas_expression for x in b]

    def test_is_valid_true(self):
        gen = V75RegisterGenerator(seed=1)
        for ex in gen.iter_examples(10):
            assert ex.is_valid is True
