"""Tests for V76ProductionGenerator."""

from __future__ import annotations

from cas_synthetic.generator import V76ProductionGenerator


class TestV76Production:
    def test_bucket_tag(self):
        gen = V76ProductionGenerator(seed=1)
        ex = next(gen.iter_examples(1))
        assert ex.bucket == "v76_production"

    def test_production_target_populated(self):
        gen = V76ProductionGenerator(seed=1)
        for ex in gen.iter_examples(20):
            assert ex.production_target is not None
            pt = ex.production_target
            assert isinstance(pt["prereqs"], list) and pt["prereqs"]

    def test_prereq_state_ids_in_range(self):
        gen = V76ProductionGenerator(seed=1)
        for ex in gen.iter_examples(20):
            for sid, coef in ex.production_target["prereqs"]:
                assert 0 <= sid < 40
                assert coef > 0

    def test_observed_yield_non_negative(self):
        gen = V76ProductionGenerator(seed=1)
        for ex in gen.iter_examples(20):
            assert ex.production_target["observed_yield"] >= 0

    def test_leakages_optional_state_ids_in_range(self):
        gen = V76ProductionGenerator(seed=1)
        for ex in gen.iter_examples(50):
            for sid, mag in ex.production_target.get("leakages", []):
                assert 0 <= sid < 40

    def test_no_register_or_omega_labels(self):
        gen = V76ProductionGenerator(seed=1)
        for ex in gen.iter_examples(20):
            assert ex.register_labels == []
            assert ex.omega_labels == []

    def test_seed_reproducibility(self):
        g1 = V76ProductionGenerator(seed=99)
        g2 = V76ProductionGenerator(seed=99)
        a = [e.production_target for e in g1.iter_examples(5)]
        b = [e.production_target for e in g2.iter_examples(5)]
        assert a == b
