"""Python-side bridge + cache to the Rust CAS engine.

ADR-06 (Python side, Wave 6B) — batches PyO3 calls across a training batch and
caches validation results by structural hash. Two primary goals:

1. **Batch amortization**: one PyO3 crossing per batch of cache misses, rather
   than N crossings per batch of N samples.
2. **Structural cache**: training data contains heavy repetition of recipe
   archetypes; 80-95% hit rate is expected (ADR-06, §3).

Correctness invariants (ADR-06, §Correctness guarantees):
- Rust remains authoritative. The cache is a performance layer only.
- Cache is invalidated when the Rust engine version changes.
- Structural hash must capture every semantically-relevant discrete feature
  (see :mod:`.structural_hash`); a false cache hit would be a silent
  validation bug.

Agent 29 dependency: Agent 29 is implementing the Rust batch API in parallel
(``validate_same_noetic_cross_product_batch``, ``verify_named_emergent_register_batch``,
``compute_yield_batch``). Until those bindings land in the vendored
``cas_engine`` module, this bridge falls back to per-sample calls (with a
warning) or a user-supplied callback (for tests).
"""

from __future__ import annotations

import collections
import logging
import os
import threading
import warnings
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Sequence

from .structural_hash import StructuralPattern, structural_hash

__all__ = [
    "BatchValidationCache",
    "RustValidationBridge",
    "CacheStats",
    "BridgeConfig",
]


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cache statistics
# ---------------------------------------------------------------------------


@dataclass
class CacheStats:
    """Lightweight counters for observability."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    invalidations: int = 0

    @property
    def total(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        total = self.total
        return (self.hits / total) if total > 0 else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "invalidations": self.invalidations,
            "hit_rate": self.hit_rate,
        }


# ---------------------------------------------------------------------------
# BatchValidationCache — LRU
# ---------------------------------------------------------------------------


class BatchValidationCache:
    """LRU cache keyed by structural hash.

    Capacity-bounded (default 10,000 per ADR-06 §Hyperparameter defaults).
    Thread-safe for concurrent reads/writes — training data loaders on Windows
    frequently run single-process but the invariant is cheap to preserve.
    """

    DEFAULT_CAPACITY = 10_000

    def __init__(self, capacity: int = DEFAULT_CAPACITY) -> None:
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity}")
        self._capacity = capacity
        self._store: "collections.OrderedDict[bytes, Any]" = collections.OrderedDict()
        self._lock = threading.Lock()
        self._stats = CacheStats()

    # ------------------------------------------------------------------ basic

    @property
    def capacity(self) -> int:
        return self._capacity

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)

    def __contains__(self, key: bytes) -> bool:
        with self._lock:
            return key in self._store

    def stats(self) -> CacheStats:
        """Return a snapshot of current stats (a copy, safe to read)."""
        with self._lock:
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                invalidations=self._stats.invalidations,
            )

    # ------------------------------------------------------------------ ops

    def get(self, key: bytes, default: Any = None) -> Any:
        """Return cached value; update LRU order. Records hit/miss in stats."""
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
                self._stats.hits += 1
                return self._store[key]
            self._stats.misses += 1
            return default

    def put(self, key: bytes, value: Any) -> None:
        """Insert ``value`` at ``key``; evict oldest if over capacity."""
        with self._lock:
            if key in self._store:
                # Refresh LRU order but do not double-count an insert as a
                # miss — the caller decided it was worth re-inserting.
                self._store.move_to_end(key)
                self._store[key] = value
                return
            self._store[key] = value
            if len(self._store) > self._capacity:
                self._store.popitem(last=False)  # evict oldest
                self._stats.evictions += 1

    def clear(self) -> None:
        """Drop all entries; record as an invalidation event."""
        with self._lock:
            self._store.clear()
            self._stats.invalidations += 1

    def reset_stats(self) -> None:
        with self._lock:
            self._stats = CacheStats()


# ---------------------------------------------------------------------------
# Bridge configuration
# ---------------------------------------------------------------------------


@dataclass
class BridgeConfig:
    """Tunables + injection points for :class:`RustValidationBridge`.

    ``rust_engine`` allows tests to inject a stub / mock in place of the real
    ``cas_engine`` PyO3 module. In production this is left ``None`` and the
    bridge imports ``cas_engine`` itself.
    """

    cache_capacity: int = BatchValidationCache.DEFAULT_CAPACITY
    rust_engine: Any = None
    # If the Rust engine exposes no batch API, fall back to per-sample calls.
    allow_per_sample_fallback: bool = True


# ---------------------------------------------------------------------------
# Version detection
# ---------------------------------------------------------------------------


def _detect_engine_version(rust_engine: Any) -> str:
    """Best-effort Rust engine version string for cache-invalidation keying.

    Looks for ``__version__`` (PEP 8) then ``VERSION`` then ``version``.
    Falls back to ``"unknown"`` — the bridge will still function but cache
    invalidation on version bump must be done manually via
    :meth:`RustValidationBridge.invalidate_all`.
    """
    if rust_engine is None:
        return "no-engine"
    for attr in ("__version__", "VERSION", "version"):
        val = getattr(rust_engine, attr, None)
        if callable(val):
            try:
                val = val()
            except Exception:  # pragma: no cover - defensive
                val = None
        if isinstance(val, str) and val:
            return val
    return "unknown"


# ---------------------------------------------------------------------------
# RustValidationBridge — batching + per-validation-type caching
# ---------------------------------------------------------------------------


class RustValidationBridge:
    """Batching, caching wrapper around Rust engine validation.

    Exposes three batch entry points, one per Rust batch function queued in
    ADR-06:

    - :meth:`validate_rule_four_batch` — Clarification 10 same-Noetic cross
      product admissibility.
    - :meth:`verify_named_emergent_batch` — named emergent register identity.
    - :meth:`compute_yield_batch` — CAS v7.6 production-semantics yield.

    Each entry point maintains its own :class:`BatchValidationCache` instance
    so that a hit in one class cannot mask a miss in another. The cache key is
    the structural hash of the per-sample pattern descriptor.
    """

    # Rust function names we dispatch against; mirror the names in the
    # ``docs/working/cas_v7_7_rollout_plan.md`` Rust engine queue.
    _BATCH_FN_NAMES = {
        "rule_four": "validate_same_noetic_cross_product_batch",
        "rule_four_distance": "rule_four_distance_batch",
        "named_emergent": "verify_named_emergent_register_batch",
        "yield": "compute_yield_batch",
    }
    _PER_SAMPLE_FN_NAMES = {
        "rule_four": "validate_same_noetic_cross_product",
        "rule_four_distance": "rule_four_distance",
        "named_emergent": "verify_named_emergent_register",
        "yield": "compute_yield",
    }

    def __init__(
        self,
        config: BridgeConfig | None = None,
        *,
        cache_capacity: int | None = None,
        rust_engine: Any = None,
    ) -> None:
        if config is None:
            config = BridgeConfig()
        if cache_capacity is not None:
            config.cache_capacity = cache_capacity
        if rust_engine is not None:
            config.rust_engine = rust_engine
        self._config = config

        if config.rust_engine is None:
            config.rust_engine = self._try_import_engine()

        self._engine = config.rust_engine
        self._engine_version = _detect_engine_version(self._engine)

        self._caches: dict[str, BatchValidationCache] = {
            kind: BatchValidationCache(capacity=config.cache_capacity)
            for kind in self._BATCH_FN_NAMES
        }

    # ------------------------------------------------------------- bootstrap

    @staticmethod
    def _try_import_engine() -> Any:
        """Import the vendored / installed ``cas_engine`` module if possible.

        Failure is non-fatal — the bridge can operate in
        ``rust_engine=<mock>`` mode for tests, or in pure-cache mode where
        misses simply raise at call time.
        """
        try:
            import cas_engine  # type: ignore[import-not-found]

            return cas_engine
        except Exception as exc:  # pragma: no cover - exercised via tests
            logger.warning(
                "RustValidationBridge: cas_engine import failed (%s); "
                "bridge is operating without a real Rust backend.",
                exc,
            )
            return None

    # --------------------------------------------------------- version + inv.

    @property
    def engine_version(self) -> str:
        return self._engine_version

    def refresh_engine_version(self) -> str:
        """Re-probe the Rust engine version; invalidate caches on change.

        Call after any process-level operation that could swap the engine
        (e.g. hot reload in a long-running training server).
        """
        new_version = _detect_engine_version(self._engine)
        if new_version != self._engine_version:
            logger.info(
                "RustValidationBridge: engine version changed %r -> %r; "
                "invalidating all caches.",
                self._engine_version,
                new_version,
            )
            self.invalidate_all()
            self._engine_version = new_version
        return self._engine_version

    def invalidate_all(self) -> None:
        """Drop every cached validation result.

        Call on Rust engine version change, framework version bump, or any
        time the Python side loses confidence that cached results reflect
        current Rust semantics.
        """
        for cache in self._caches.values():
            cache.clear()

    def cache_stats(self, kind: str | None = None) -> dict[str, CacheStats]:
        """Per-kind cache stats; ``kind=None`` returns all."""
        if kind is None:
            return {k: c.stats() for k, c in self._caches.items()}
        if kind not in self._caches:
            raise KeyError(f"unknown validation kind: {kind!r}")
        return {kind: self._caches[kind].stats()}

    # ------------------------------------------------------------------ core

    def _resolve_fn(self, kind: str, batch: bool) -> Callable[..., Any] | None:
        """Return the Rust function for ``kind`` in batch or per-sample mode."""
        if self._engine is None:
            return None
        fn_name = (
            self._BATCH_FN_NAMES[kind] if batch else self._PER_SAMPLE_FN_NAMES[kind]
        )
        return getattr(self._engine, fn_name, None)

    def _run_batch(
        self,
        kind: str,
        patterns: Sequence[Any],
        call_args: Sequence[Any],
    ) -> list[Any]:
        """Execute the Rust batch API (or fall back) on ``call_args``.

        ``patterns`` is passed only so error messages can reference the
        originating pattern when a fallback per-sample call fails; the Rust
        side sees ``call_args``.
        """
        if self._engine is None:
            raise RuntimeError(
                "RustValidationBridge: no Rust engine available; cannot "
                "resolve cache misses. Inject a rust_engine via BridgeConfig "
                "or ensure cas_engine is importable."
            )

        batch_fn = self._resolve_fn(kind, batch=True)
        if batch_fn is not None:
            return list(batch_fn(list(call_args)))

        # Graceful degradation: Agent 29's batch API is not yet landed.
        per_sample_fn = self._resolve_fn(kind, batch=False)
        if per_sample_fn is None:
            raise RuntimeError(
                f"RustValidationBridge: engine exposes neither batch "
                f"({self._BATCH_FN_NAMES[kind]!r}) nor per-sample "
                f"({self._PER_SAMPLE_FN_NAMES[kind]!r}) entry point for "
                f"validation kind {kind!r}. "
                "TODO(agent-29): once the batch API lands, this fallback "
                "path becomes dead code."
            )
        if not self._config.allow_per_sample_fallback:
            raise RuntimeError(
                f"RustValidationBridge: batch API for {kind!r} is missing "
                "and per-sample fallback is disabled."
            )

        warnings.warn(
            f"RustValidationBridge: batch API {self._BATCH_FN_NAMES[kind]!r} "
            "unavailable; falling back to per-sample calls. This is a "
            "performance regression tracked by Agent 29's batch-API PR.",
            RuntimeWarning,
            stacklevel=3,
        )
        return [per_sample_fn(arg) for arg in call_args]

    def _dispatch(
        self,
        kind: str,
        patterns: Sequence[Any],
        call_args_for: Callable[[int, Any], Any],
    ) -> list[Any]:
        """Shared batching + caching logic.

        :param kind: validation kind key (``"rule_four"``, ``"named_emergent"``,
            ``"yield"``).
        :param patterns: list of structural descriptors (one per sample). These
            must canonicalize via :func:`structural_hash`.
        :param call_args_for: callable ``(index, pattern) -> rust_call_arg``
            that maps a pattern to the argument the Rust function expects for
            that sample.
        """
        if kind not in self._caches:
            raise KeyError(f"unknown validation kind: {kind!r}")

        cache = self._caches[kind]
        n = len(patterns)
        results: list[Any] = [None] * n
        miss_indices: list[int] = []
        miss_keys: list[bytes] = []
        miss_call_args: list[Any] = []

        for i, pattern in enumerate(patterns):
            key = structural_hash(pattern)
            hit = cache.get(key, default=_MISS_SENTINEL)
            if hit is not _MISS_SENTINEL:
                results[i] = hit
            else:
                miss_indices.append(i)
                miss_keys.append(key)
                miss_call_args.append(call_args_for(i, pattern))

        if miss_indices:
            fresh = self._run_batch(kind, patterns, miss_call_args)
            if len(fresh) != len(miss_indices):
                raise RuntimeError(
                    f"RustValidationBridge: batch API for {kind!r} returned "
                    f"{len(fresh)} results for {len(miss_indices)} misses."
                )
            for idx, key, result in zip(miss_indices, miss_keys, fresh):
                cache.put(key, result)
                results[idx] = result

        return results

    # --------------------------------------------------------- public batch API

    def validate_rule_four_batch(
        self,
        expressions: Sequence[Any],
        *,
        call_args: Sequence[Any] | None = None,
    ) -> list[Any]:
        """Validate Clarification 10 Rule 4 for each expression.

        :param expressions: structural descriptors (one per sample) suitable
            for :func:`structural_hash`.
        :param call_args: optional parallel sequence of Rust-call arguments;
            if omitted, each expression is passed through verbatim.
        """
        args = list(call_args) if call_args is not None else list(expressions)
        if len(args) != len(expressions):
            raise ValueError("call_args length must match expressions length")
        return self._dispatch(
            "rule_four",
            expressions,
            call_args_for=lambda i, _p: args[i],
        )

    def rule_four_distance_batch(
        self,
        expressions: Sequence[Any],
        *,
        call_args: Sequence[Any] | None = None,
    ) -> list[float]:
        """Continuous distance-to-valid Rule 4 signal (ADR-06 §Continuous
        validation signal).

        Wraps ``cas_engine.rule_four_distance_batch`` (PyO3, wheel 0.1.1+)
        with structural-hash caching. Returns a float per expression:
        ``0.0`` for admissible, and a positive severity-weighted scalar for
        a violation (1.0 / 1.5 / 2.0 across 2- / 3- / 4-register violations
        in the current Rust emitter).

        Cache namespace is ``"rule_four_distance"`` — separate from the
        binary ``"rule_four"`` cache so cross-contamination between the two
        result types is structurally impossible.

        When ``rule_four_distance_batch`` is absent from the loaded
        ``cas_engine`` module (pre-0.1.1 wheels) the bridge falls back via
        :meth:`_run_batch`'s per-sample path to ``rule_four_distance`` if
        present. When neither is present the caller should fall back to
        :meth:`validate_rule_four_batch` (binary 0.0/1.0 signal).

        :param expressions: structural descriptors (one per sample) suitable
            for :func:`structural_hash`.
        :param call_args: optional parallel sequence of Rust-call arguments
            in the `(operands, named_emergent_result)` tuple shape; if
            omitted each expression is passed through verbatim.
        """
        args = list(call_args) if call_args is not None else list(expressions)
        if len(args) != len(expressions):
            raise ValueError("call_args length must match expressions length")
        # Cast results to float — Rust returns Vec<f64>, we normalize to
        # Python float for downstream tensor construction.
        results = self._dispatch(
            "rule_four_distance",
            expressions,
            call_args_for=lambda i, _p: args[i],
        )
        return [float(r) for r in results]

    def has_rule_four_distance(self) -> bool:
        """True iff the loaded Rust engine exposes the continuous Rule 4
        distance API (``rule_four_distance_batch`` or per-sample
        ``rule_four_distance``).

        Used by the trainer to decide between the continuous gradient-bearing
        signal and the binary 0.0/1.0 fallback when older wheels are loaded.
        """
        if self._engine is None:
            return False
        return (
            self._resolve_fn("rule_four_distance", batch=True) is not None
            or self._resolve_fn("rule_four_distance", batch=False) is not None
        )

    def verify_named_emergent_batch(
        self,
        inputs: Sequence[Any],
        *,
        call_args: Sequence[Any] | None = None,
    ) -> list[Any]:
        """Verify named emergent register identity per sample."""
        args = list(call_args) if call_args is not None else list(inputs)
        if len(args) != len(inputs):
            raise ValueError("call_args length must match inputs length")
        return self._dispatch(
            "named_emergent",
            inputs,
            call_args_for=lambda i, _p: args[i],
        )

    def compute_yield_batch(
        self,
        inputs: Sequence[Any],
        *,
        call_args: Sequence[Any] | None = None,
    ) -> list[Any]:
        """Compute theoretical/actual yield per sample (CAS v7.6)."""
        args = list(call_args) if call_args is not None else list(inputs)
        if len(args) != len(inputs):
            raise ValueError("call_args length must match inputs length")
        return self._dispatch(
            "yield",
            inputs,
            call_args_for=lambda i, _p: args[i],
        )


# Sentinel — distinct from any valid Rust return value.
_MISS_SENTINEL: Any = object()
