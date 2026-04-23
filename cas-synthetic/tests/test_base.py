"""Tests for BaseGenerator abstract interface."""

from __future__ import annotations

import pytest

from cas_synthetic.generator.base import BaseGenerator, GeneratedExample


class _MinimalGenerator(BaseGenerator):
    BUCKET = "test_minimal"

    def _generate_one(self) -> GeneratedExample:
        return GeneratedExample(
            prompt="p",
            response="r",
            cas_expression="^0^P_{F1}",
            bucket=self.BUCKET,
        )


class TestBaseGenerator:
    def test_requires_bucket(self):
        class _NoBucket(BaseGenerator):
            def _generate_one(self):
                return GeneratedExample(prompt="p", response="r")

        with pytest.raises(RuntimeError):
            _NoBucket()

    def test_iter_examples_yields_n(self):
        gen = _MinimalGenerator(seed=1)
        out = list(gen.iter_examples(5))
        assert len(out) == 5
        assert all(isinstance(x, GeneratedExample) for x in out)

    def test_generate_batch_yields_n(self):
        gen = _MinimalGenerator(seed=1)
        out = gen.generate_batch(3)
        assert len(out) == 3

    def test_seed_reproducibility(self):
        # Seeded generators have reproducible RNG state
        g1 = _MinimalGenerator(seed=42)
        g2 = _MinimalGenerator(seed=42)
        assert g1.rng.random() == g2.rng.random()

    def test_state_id_roundtrip(self):
        gen = _MinimalGenerator(seed=1)
        assert gen._state_id(0, "P") == 0
        assert gen._state_id(9, "P") == 9
        assert gen._state_id(0, "C") == 10
        assert gen._state_id(5, "E") == 25
        assert gen._state_id(9, "O") == 39

    def test_scores_from_states_shape(self):
        gen = _MinimalGenerator(seed=1)
        scores = gen._scores_from_states([(3, "P"), (3, "P"), (5, "C")])
        assert len(scores["operator_scores"]) == 10
        assert len(scores["domain_scores"]) == 4
        assert scores["operator_scores"][3] == 1.0  # max
        assert scores["operator_scores"][5] == 0.5

    def test_generated_example_to_dict_omits_empty(self):
        ex = GeneratedExample(prompt="p", response="r")
        d = ex.to_dict(include_metadata=False)
        assert "prompt" in d and "response" in d
        assert "register_labels" not in d
        assert "omega_labels" not in d
        assert "production_target" not in d

    def test_generated_example_to_dict_with_metadata(self):
        ex = GeneratedExample(prompt="p", response="r", bucket="x", is_valid=False,
                              violation_type="v", distance_to_valid=1.0)
        d = ex.to_dict(include_metadata=True)
        assert d["_meta"]["bucket"] == "x"
        assert d["_meta"]["is_valid"] is False
        assert d["_meta"]["violation_type"] == "v"
        assert d["_meta"]["distance_to_valid"] == 1.0

    def test_registers_vocab_lowercase_f(self):
        """Clarification 8 mandates lowercase `f` for Affective."""
        gen = _MinimalGenerator(seed=1)
        assert "f" in gen.REGISTERS
        assert "F" not in gen.REGISTERS  # uppercase would be wrong
