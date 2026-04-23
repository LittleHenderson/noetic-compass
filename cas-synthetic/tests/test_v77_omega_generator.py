"""Tests for V77OmegaGenerator."""

from __future__ import annotations

from cas_synthetic.generator import V77OmegaGenerator


class TestV77Omega:
    def test_bucket_tag(self):
        gen = V77OmegaGenerator(seed=1)
        ex = next(gen.iter_examples(1))
        assert ex.bucket == "v77_omega"

    def test_omega_labels_populated(self):
        gen = V77OmegaGenerator(seed=1)
        for ex in gen.iter_examples(20):
            assert ex.omega_labels, "omega generator must emit omega_labels"
            assert len(ex.omega_labels) == 1
            assert ex.omega_labels[0]["omega_name"].startswith("Omega_")

    def test_only_admitted_omega_names(self):
        """Only registry-admitted names appear — currently Omega_presence + Omega_refusal."""
        gen = V77OmegaGenerator(seed=1)
        admitted = gen.admitted_omega_names if hasattr(gen, "admitted_omega_names") else None
        # Fall back: inspect registry directly
        if admitted is None:
            admitted = {e["name"] for e in gen.omega_registry["admitted"]}
        for ex in gen.iter_examples(50):
            for lbl in ex.omega_labels:
                assert lbl["omega_name"] in admitted

    def test_register_labels_populated(self):
        gen = V77OmegaGenerator(seed=1)
        for ex in gen.iter_examples(20):
            assert ex.register_labels
            for lbl in ex.register_labels:
                assert lbl["register"] in ("T", "A", "f", "E")

    def test_expression_contains_equals_and_omega(self):
        gen = V77OmegaGenerator(seed=1)
        for ex in gen.iter_examples(20):
            assert "Omega_" in ex.cas_expression
            assert "=" in ex.cas_expression

    def test_is_valid_true(self):
        gen = V77OmegaGenerator(seed=1)
        for ex in gen.iter_examples(10):
            assert ex.is_valid is True
