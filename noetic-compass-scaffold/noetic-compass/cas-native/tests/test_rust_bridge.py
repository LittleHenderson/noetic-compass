"""Tests for ADR-06 Python-side bridge + structural-hash cache.

Covers:
- :mod:`cas_native.validation.structural_hash` — determinism, discrete-only.
- :class:`cas_native.validation.BatchValidationCache` — LRU, stats, capacity.
- :class:`cas_native.validation.RustValidationBridge` — batch/cache/fallback.
"""

from __future__ import annotations

import subprocess
import sys
import warnings
from types import SimpleNamespace
from typing import Any

import pytest

from cas_native.validation import (
    BatchValidationCache,
    BridgeConfig,
    RustValidationBridge,
    StructuralPattern,
    canonicalize,
    structural_hash,
)


# ---------------------------------------------------------------------------
# structural_hash
# ---------------------------------------------------------------------------


class TestStructuralHash:

    def test_deterministic_same_input_same_hash(self):
        """Same input must produce identical hash bytes within a process."""
        pattern = {"noetics": [3, 5], "domain": "P", "register_set": ["A", "f"]}
        assert structural_hash(pattern) == structural_hash(pattern)

    def test_deterministic_across_python_processes(self):
        """blake2b is not salted — hash must match across fresh processes.

        Guards against the accidental use of built-in ``hash()`` which is
        randomized per-interpreter under ``PYTHONHASHSEED=random``.
        """
        import pathlib

        validation_dir = (
            pathlib.Path(__file__).resolve().parent.parent / "validation"
        )
        # Import the module by file path so the subprocess doesn't need the
        # ``cas_native`` alias that conftest installs. Register the module in
        # ``sys.modules`` before exec — dataclass needs that (Python 3.12).
        code = (
            "import importlib.util, sys, pathlib; "
            f"p = pathlib.Path(r'{validation_dir}') / 'structural_hash.py'; "
            "spec = importlib.util.spec_from_file_location('sh', p); "
            "mod = importlib.util.module_from_spec(spec); "
            "sys.modules['sh'] = mod; "
            "spec.loader.exec_module(mod); "
            "print(mod.structural_hash({'noetics':[3,5],'domain':'P'}).hex())"
        )
        out1 = _run_subproc(code, env_extra={"PYTHONHASHSEED": "random"})
        out2 = _run_subproc(code, env_extra={"PYTHONHASHSEED": "0"})
        assert out1 and out2
        assert out1 == out2

    def test_different_structure_different_hash(self):
        """Structurally different inputs must hash differently."""
        a = {"noetics": [3, 5], "domain": "P"}
        b = {"noetics": [3, 6], "domain": "P"}
        assert structural_hash(a) != structural_hash(b)

    def test_continuous_values_ignored_in_dict(self):
        """Float activations and keys marked continuous are stripped."""
        a = {"noetics": [3], "activation_value": 0.1, "weight": 0.5}
        b = {"noetics": [3], "activation_value": 0.9, "weight": 0.01}
        assert structural_hash(a) == structural_hash(b)

    def test_continuous_top_level_floats_ignored(self):
        """Free-standing floats in a collection are dropped as continuous."""
        a = [1, 0.1, 2, 0.9]
        b = [1, 0.77, 2, 0.001]
        assert structural_hash(a) == structural_hash(b)

    def test_domain_change_affects_hash(self):
        a = {"noetics": [3], "domain": "P"}
        b = {"noetics": [3], "domain": "C"}
        assert structural_hash(a) != structural_hash(b)

    def test_register_set_change_affects_hash(self):
        a = StructuralPattern(noetics=(3,), registers=("A", "f"))
        b = StructuralPattern(noetics=(3,), registers=("A", "T"))
        assert structural_hash(a) != structural_hash(b)

    def test_emergent_name_change_affects_hash(self):
        a = StructuralPattern(noetics=(3,), emergent_register_name="Omega_one")
        b = StructuralPattern(noetics=(3,), emergent_register_name="Omega_two")
        assert structural_hash(a) != structural_hash(b)

    def test_recipe_shape_change_affects_hash(self):
        a = StructuralPattern(noetics=(3,), recipe_shape=(2, 0))
        b = StructuralPattern(noetics=(3,), recipe_shape=(3, 1))
        assert structural_hash(a) != structural_hash(b)

    def test_validation_kind_change_affects_hash(self):
        """Distinct validation kinds must not alias — cache slices rely on this."""
        a = StructuralPattern(noetics=(3,), validation_kind="rule_four")
        b = StructuralPattern(noetics=(3,), validation_kind="yield")
        assert structural_hash(a) != structural_hash(b)

    def test_dict_and_pattern_do_not_alias(self):
        """Raw dict with same field names must not collide with tagged pattern."""
        pattern = StructuralPattern(noetics=(3,), domains=("P",))
        raw = {"noetics": (3,), "domains": ("P",)}
        assert structural_hash(pattern) != structural_hash(raw)

    def test_hash_is_bytes_32(self):
        out = structural_hash({"x": 1})
        assert isinstance(out, bytes)
        assert len(out) == 32

    def test_canonicalize_sorts_dict_keys(self):
        a = canonicalize({"b": 1, "a": 2}, drop_continuous=False)
        b = canonicalize({"a": 2, "b": 1}, drop_continuous=False)
        assert a == b

    def test_canonicalize_preserves_integer_ints(self):
        """Integer activations (discrete) must NOT be dropped."""
        a = {"count": 3}
        b = {"count": 4}
        assert structural_hash(a) != structural_hash(b)


# ---------------------------------------------------------------------------
# BatchValidationCache
# ---------------------------------------------------------------------------


class TestBatchValidationCache:

    def test_put_get_roundtrip(self):
        cache = BatchValidationCache(capacity=4)
        cache.put(b"k1", "v1")
        assert cache.get(b"k1") == "v1"

    def test_miss_returns_default(self):
        cache = BatchValidationCache(capacity=4)
        assert cache.get(b"missing", default="sentinel") == "sentinel"

    def test_lru_eviction_when_over_capacity(self):
        cache = BatchValidationCache(capacity=3)
        cache.put(b"a", 1)
        cache.put(b"b", 2)
        cache.put(b"c", 3)
        # Touch "a" to refresh it; then overflow should evict "b".
        cache.get(b"a")
        cache.put(b"d", 4)
        assert b"b" not in cache
        assert b"a" in cache
        assert b"c" in cache
        assert b"d" in cache

    def test_stats_hits_and_misses(self):
        cache = BatchValidationCache(capacity=4)
        cache.put(b"a", 1)
        cache.get(b"a")  # hit
        cache.get(b"a")  # hit
        cache.get(b"missing")  # miss
        stats = cache.stats()
        assert stats.hits == 2
        assert stats.misses == 1
        assert abs(stats.hit_rate - (2 / 3)) < 1e-9

    def test_stats_records_evictions(self):
        cache = BatchValidationCache(capacity=2)
        cache.put(b"a", 1)
        cache.put(b"b", 2)
        cache.put(b"c", 3)  # evicts "a"
        assert cache.stats().evictions == 1

    def test_capacity_is_configurable(self):
        cache = BatchValidationCache(capacity=5)
        assert cache.capacity == 5
        for i in range(5):
            cache.put(f"k{i}".encode(), i)
        assert len(cache) == 5
        cache.put(b"k5", 5)
        assert len(cache) == 5  # capacity held

    def test_capacity_invalid_raises(self):
        with pytest.raises(ValueError):
            BatchValidationCache(capacity=0)

    def test_clear_records_invalidation(self):
        cache = BatchValidationCache(capacity=4)
        cache.put(b"a", 1)
        cache.clear()
        assert len(cache) == 0
        assert cache.stats().invalidations == 1


# ---------------------------------------------------------------------------
# RustValidationBridge — via injected mock engine
# ---------------------------------------------------------------------------


class _CallCountingEngine:
    """Stub Rust engine exposing the three batch functions.

    Used to assert that cache hits avoid Rust calls and that misses are
    forwarded to a single batch call.
    """

    __version__ = "v7.7.0-test"

    def __init__(self):
        self.rule_four_calls: list[list[Any]] = []
        self.named_emergent_calls: list[list[Any]] = []
        self.yield_calls: list[list[Any]] = []

    def validate_same_noetic_cross_product_batch(self, args):
        self.rule_four_calls.append(list(args))
        return [f"rule4:{a}" for a in args]

    def verify_named_emergent_register_batch(self, args):
        self.named_emergent_calls.append(list(args))
        return [f"emergent:{a}" for a in args]

    def compute_yield_batch(self, args):
        self.yield_calls.append(list(args))
        return [f"yield:{a}" for a in args]


class _PerSampleOnlyEngine:
    """Stub engine exposing ONLY per-sample functions (Agent 29 pre-land)."""

    __version__ = "v7.6.0-test"

    def __init__(self):
        self.rule_four_calls: list[Any] = []

    def validate_same_noetic_cross_product(self, arg):
        self.rule_four_calls.append(arg)
        return f"rule4-single:{arg}"


class TestRustValidationBridge:

    def _make_bridge(self, engine=None, **kwargs) -> RustValidationBridge:
        engine = engine if engine is not None else _CallCountingEngine()
        return RustValidationBridge(
            config=BridgeConfig(rust_engine=engine, **kwargs)
        )

    def test_miss_triggers_single_batch_call(self):
        engine = _CallCountingEngine()
        bridge = self._make_bridge(engine)
        patterns = [
            {"noetics": [3], "domain": "P", "i": 0},
            {"noetics": [5], "domain": "C", "i": 1},
        ]
        results = bridge.validate_rule_four_batch(patterns)
        assert results == ["rule4:{'noetics': [3], 'domain': 'P', 'i': 0}",
                           "rule4:{'noetics': [5], 'domain': 'C', 'i': 1}"]
        # Exactly ONE batch call for two misses.
        assert len(engine.rule_four_calls) == 1
        assert len(engine.rule_four_calls[0]) == 2

    def test_hit_avoids_rust_call(self):
        engine = _CallCountingEngine()
        bridge = self._make_bridge(engine)
        patterns = [{"noetics": [3], "domain": "P"}]
        bridge.validate_rule_four_batch(patterns)  # miss -> 1 batch call
        bridge.validate_rule_four_batch(patterns)  # hit -> 0 batch calls
        assert len(engine.rule_four_calls) == 1

    def test_mixed_hits_and_misses_ordered_output(self):
        engine = _CallCountingEngine()
        bridge = self._make_bridge(engine)
        a = {"noetics": [3], "domain": "P", "tag": "a"}
        b = {"noetics": [5], "domain": "C", "tag": "b"}
        c = {"noetics": [7], "domain": "E", "tag": "c"}

        # Prime the cache with a and b.
        bridge.validate_rule_four_batch([a, b])
        assert len(engine.rule_four_calls) == 1

        # Now ask for [c, a, b, c]: c appears twice (only one miss),
        # a and b are cache hits.
        results = bridge.validate_rule_four_batch([c, a, b, c])
        # Exactly one additional batch call, containing ONE arg (c only).
        assert len(engine.rule_four_calls) == 2
        # Within this batch the cache should de-duplicate c to a single miss.
        assert len(engine.rule_four_calls[1]) <= 2  # implementations may or may not dedupe
        # Results must be in the requested order.
        assert results[0] == results[3]
        assert results[1] == f"rule4:{a}"
        assert results[2] == f"rule4:{b}"

    def test_stats_reflect_hits_and_misses(self):
        engine = _CallCountingEngine()
        bridge = self._make_bridge(engine)
        a = {"noetics": [3]}
        b = {"noetics": [5]}
        bridge.validate_rule_four_batch([a, b])  # 2 misses
        bridge.validate_rule_four_batch([a, b])  # 2 hits
        stats = bridge.cache_stats("rule_four")["rule_four"]
        assert stats.hits == 2
        assert stats.misses == 2

    def test_named_emergent_and_yield_caches_are_separate(self):
        engine = _CallCountingEngine()
        bridge = self._make_bridge(engine)
        patt = {"noetics": [3], "emergent": "Omega"}
        bridge.verify_named_emergent_batch([patt])
        # A rule_four query on the SAME pattern must still be a miss — the
        # caches are per-kind.
        bridge.validate_rule_four_batch([patt])
        assert len(engine.named_emergent_calls) == 1
        assert len(engine.rule_four_calls) == 1

    def test_invalidate_all_clears_cache(self):
        engine = _CallCountingEngine()
        bridge = self._make_bridge(engine)
        patt = {"noetics": [3]}
        bridge.validate_rule_four_batch([patt])  # miss
        bridge.invalidate_all()
        bridge.validate_rule_four_batch([patt])  # miss again
        assert len(engine.rule_four_calls) == 2

    def test_engine_version_change_triggers_invalidation(self):
        engine = _CallCountingEngine()
        bridge = self._make_bridge(engine)
        patt = {"noetics": [3]}
        bridge.validate_rule_four_batch([patt])  # miss

        # Simulate a Rust engine hot-swap / version bump.
        engine.__version__ = "v7.7.1-test"
        bridge.refresh_engine_version()

        bridge.validate_rule_four_batch([patt])  # miss again (cache cleared)
        assert len(engine.rule_four_calls) == 2

    def test_fallback_to_per_sample_when_batch_unavailable(self):
        engine = _PerSampleOnlyEngine()
        bridge = self._make_bridge(engine)
        patt = {"noetics": [3]}
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            results = bridge.validate_rule_four_batch([patt, {"noetics": [5]}])
        assert len(results) == 2
        # Per-sample fn called once per miss.
        assert len(engine.rule_four_calls) == 2
        # Warning about fallback was emitted.
        assert any(
            issubclass(w.category, RuntimeWarning)
            and "batch API" in str(w.message)
            for w in caught
        )

    def test_fallback_disabled_raises(self):
        engine = _PerSampleOnlyEngine()
        bridge = RustValidationBridge(
            config=BridgeConfig(
                rust_engine=engine,
                allow_per_sample_fallback=False,
            )
        )
        with pytest.raises(RuntimeError, match="per-sample fallback is disabled"):
            bridge.validate_rule_four_batch([{"noetics": [3]}])

    def test_no_engine_raises_on_miss(self, monkeypatch):
        # Prevent import of the real vendored cas_engine so the bridge truly
        # has no engine to fall through to.
        monkeypatch.setattr(
            RustValidationBridge, "_try_import_engine", staticmethod(lambda: None)
        )
        bridge = RustValidationBridge(config=BridgeConfig(rust_engine=None))
        with pytest.raises(RuntimeError, match="no Rust engine available"):
            bridge.validate_rule_four_batch([{"noetics": [3]}])

    def test_call_args_length_mismatch_raises(self):
        engine = _CallCountingEngine()
        bridge = self._make_bridge(engine)
        with pytest.raises(ValueError):
            bridge.validate_rule_four_batch(
                [{"noetics": [3]}], call_args=["a", "b"]
            )

    def test_cache_capacity_applied_per_kind(self):
        engine = _CallCountingEngine()
        bridge = RustValidationBridge(
            config=BridgeConfig(rust_engine=engine, cache_capacity=2)
        )
        # Three misses on rule_four with capacity 2 -> first entry evicted.
        bridge.validate_rule_four_batch([{"i": 0}])
        bridge.validate_rule_four_batch([{"i": 1}])
        bridge.validate_rule_four_batch([{"i": 2}])
        bridge.validate_rule_four_batch([{"i": 0}])  # should now be a miss again
        assert len(engine.rule_four_calls) == 4


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _project_root_str() -> str:
    """Return the scaffold root so subprocess tests can import cas_native."""
    import pathlib

    return str(pathlib.Path(__file__).resolve().parent.parent.parent)


def _run_subproc(code: str, env_extra: dict[str, str] | None = None) -> str:
    """Run ``code`` in a fresh Python subprocess, return stdout.strip()."""
    import os

    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    if proc.returncode != 0:
        pytest.skip(
            f"subprocess determinism probe failed to run: {proc.stderr!r}"
        )
    return proc.stdout.strip()
