"""Tests for Level2MixController."""

from __future__ import annotations

from collections import Counter

import pytest

from cas_synthetic.mix_controller import Level2MixController, Level2MixConfig


class TestLevel2MixController:
    def test_fractions_sum_to_one(self):
        cfg = Level2MixConfig()
        assert abs(sum(cfg.fractions().values()) - 1.0) < 1e-9

    def test_bucket_sizes_total_exact(self):
        ctrl = Level2MixController(Level2MixConfig(seed=1))
        sizes = ctrl.bucket_sizes(10000)
        assert sum(sizes.values()) == 10000

    def test_bucket_sizes_level2_spec(self):
        ctrl = Level2MixController(Level2MixConfig(seed=1))
        sizes = ctrl.bucket_sizes(10000)
        # Tolerance ±2 for rounding drift (v74 absorbs)
        assert abs(sizes["v75_register"] - 2500) <= 2
        assert abs(sizes["v77_rule_four"] - 1500) <= 2
        assert abs(sizes["v77_omega"] - 2000) <= 2
        assert abs(sizes["v76_production"] - 1000) <= 2
        assert abs(sizes["meta_logic"] - 1000) <= 2

    def test_iter_examples_count(self):
        ctrl = Level2MixController(Level2MixConfig(seed=1))
        out = list(ctrl.iter_examples(100))
        assert len(out) == 100

    def test_mix_counts_100_match_target(self):
        ctrl = Level2MixController(Level2MixConfig(seed=1))
        out = list(ctrl.iter_examples(100))
        counts = Counter(ex.bucket for ex in out)
        # Level 2 with meta-logic bucket for n=100: 20/25/15/20/10/10
        assert counts["v74_baseline"] == 20
        assert counts["v75_register"] == 25
        assert counts["v77_rule_four"] == 15
        assert counts["v77_omega"] == 20
        assert counts["v76_production"] == 10
        assert counts["meta_logic"] == 10

    def test_reproducible_with_seed(self):
        c1 = Level2MixController(Level2MixConfig(seed=42))
        c2 = Level2MixController(Level2MixConfig(seed=42))
        a = [ex.cas_expression for ex in c1.iter_examples(50)]
        b = [ex.cas_expression for ex in c2.iter_examples(50)]
        assert a == b

    def test_bad_fractions_raise(self):
        cfg = Level2MixConfig(v74_fraction=0.5)
        with pytest.raises(ValueError):
            Level2MixController(cfg)

    def test_generate_to_jsonl_writes_file(self, tmp_path):
        ctrl = Level2MixController(Level2MixConfig(seed=1))
        path = tmp_path / "out.jsonl"
        report = ctrl.generate_to_jsonl(path, n=100)
        assert report["written"] == 100
        # Verify file on disk
        import json as _json
        with open(path, encoding="utf-8") as f:
            lines = [line for line in f if line.strip()]
        assert len(lines) == 100
        first = _json.loads(lines[0])
        assert "prompt" in first and "response" in first

    def test_resume_from_appends(self, tmp_path):
        ctrl = Level2MixController(Level2MixConfig(seed=1))
        path = tmp_path / "out.jsonl"
        r1 = ctrl.generate_to_jsonl(path, n=50)
        assert r1["written"] == 50
        r2 = ctrl.generate_to_jsonl(path, n=100, resume_from=50)
        assert r2["written"] == 50
        assert r2["skipped"] == 50
        with open(path, encoding="utf-8") as f:
            assert sum(1 for line in f if line.strip()) == 100
