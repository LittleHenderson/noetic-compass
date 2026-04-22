"""Structural hashing for Rust engine validation cache keys.

ADR-06 (Python side) — the cache key must capture the *structural* (discrete,
semantically-relevant) content of a cognitive-state expression while ignoring
continuous activation values. Two expressions whose Rust-engine validation
result must be identical (same Noetic set, Domain set, Register set, emergent
register identity, recipe shape) share a hash; expressions whose result must
differ DO NOT share a hash.

The hash must be deterministic across Python runs — we therefore use
``hashlib.blake2b`` rather than the built-in :func:`hash`, which is salted per
interpreter process (``PYTHONHASHSEED``).

Safety invariant (ADR-06 Consequences, §Correctness guarantees): a false cache
hit is incorrect validation. Every semantically-load-bearing discrete feature
must appear in the canonical-form bytes that feed ``blake2b``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Iterable, Mapping

__all__ = ["StructuralPattern", "structural_hash", "canonicalize"]


# ---------------------------------------------------------------------------
# Canonical-form serialization
# ---------------------------------------------------------------------------


def _canonical_atom(value: Any) -> Any:
    """Return a JSON-canonicalizable representation of an atomic value.

    Continuous / floating-point values are intentionally dropped upstream in
    :func:`canonicalize`; this helper handles the discrete atoms that remain.
    """
    if value is None or isinstance(value, (bool, int, str)):
        return value
    # Bytes are rendered as a tagged hex string so that distinct byte sequences
    # remain distinguishable after serialization.
    if isinstance(value, (bytes, bytearray)):
        return {"__bytes__": bytes(value).hex()}
    # Enums / objects with a ``.name`` attribute (e.g. PyO3 Noetic/Domain enum
    # wrappers) canonicalize on that name.
    if hasattr(value, "name") and isinstance(getattr(value, "name"), str):
        return {"__enum__": value.name}
    # Fallback — rely on repr; stable within a single Python version for
    # primitives we have not special-cased.
    return {"__repr__": repr(value)}


_CONTINUOUS_KEY_MARKERS = (
    "_value",
    "_activation",
    "_magnitude",
    "_weight",
    "_coeff",
    "_observed",
    "_yield",
)


def _is_continuous_key(key: str) -> bool:
    """Heuristic — keys ending in these suffixes are treated as continuous and
    stripped from the structural hash.

    Any explicit :class:`StructuralPattern` field list overrides this heuristic;
    the heuristic only applies when :func:`structural_hash` is called directly
    on a free-form dict.
    """
    if not isinstance(key, str):
        return False
    kl = key.lower()
    return any(kl.endswith(marker) for marker in _CONTINUOUS_KEY_MARKERS)


def canonicalize(obj: Any, *, drop_continuous: bool = True) -> Any:
    """Recursively canonicalize ``obj`` into a JSON-safe structure.

    - ``dict`` keys are sorted for determinism.
    - ``set`` / ``frozenset`` are sorted into tuples; order-independence at the
      set level is preserved by sorting before serialization.
    - ``float`` values are dropped if ``drop_continuous`` is True; they carry no
      structural information for validation caching.
    - ``None`` / ``bool`` / ``int`` / ``str`` pass through.

    The returned object is safe for ``json.dumps(sort_keys=True)``.
    """
    if isinstance(obj, Mapping):
        out: dict[str, Any] = {}
        for key in sorted(obj.keys(), key=lambda k: (type(k).__name__, str(k))):
            str_key = key if isinstance(key, str) else str(key)
            val = obj[key]
            if drop_continuous and (
                isinstance(val, float) or _is_continuous_key(str_key)
            ):
                continue
            out[str_key] = canonicalize(val, drop_continuous=drop_continuous)
        return out
    if isinstance(obj, (set, frozenset)):
        items = [canonicalize(x, drop_continuous=drop_continuous) for x in obj]
        # Sort on the JSON representation so heterogeneous sets are order-stable.
        items.sort(key=lambda x: json.dumps(x, sort_keys=True))
        return {"__set__": items}
    if isinstance(obj, tuple):
        return {
            "__tuple__": [canonicalize(x, drop_continuous=drop_continuous) for x in obj]
        }
    if isinstance(obj, list):
        return [canonicalize(x, drop_continuous=drop_continuous) for x in obj]
    if isinstance(obj, float):
        return None if drop_continuous else obj
    return _canonical_atom(obj)


# ---------------------------------------------------------------------------
# StructuralPattern dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StructuralPattern:
    """Discrete structural schema over which cache hashing operates.

    Fields are intentionally discrete — no coefficients, no activation
    magnitudes. Continuous quantities live elsewhere (in the actual input
    tensor) and never enter the cache key.
    """

    # Which Noetic operators are active in the expression. Values are indices
    # ``0..9`` (``^0`` Idea .. ``^9`` Below/Effect).
    noetics: tuple[int, ...] = field(default_factory=tuple)
    # Which Domains appear. Values from ``{"P", "C", "E", "O"}``.
    domains: tuple[str, ...] = field(default_factory=tuple)
    # Which Drive numbers appear. Values from ``{1..7}``.
    drives: tuple[int, ...] = field(default_factory=tuple)
    # Which Registers appear. Values from ``{"T", "A", "f", "E"}``.
    # ``|f`` is lowercase per Clarification 8 (authoritative).
    registers: tuple[str, ...] = field(default_factory=tuple)
    # Register-set membership per operand slot (order matters): each slot's
    # register-set is a sorted tuple of register symbols.
    register_sets: tuple[tuple[str, ...], ...] = field(default_factory=tuple)
    # Named emergent register identity, if any (e.g. "Ω_principled_aversion").
    emergent_register_name: str | None = None
    # Recipe structural shape, CAS v7.6: ``(prerequisite_count, leakage_count)``.
    recipe_shape: tuple[int, int] | None = None
    # Validation type tag — disambiguates cache slices for Rule 4, named
    # emergent verification, and yield computation.
    validation_kind: str = "rule_four"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# structural_hash — public entry point
# ---------------------------------------------------------------------------


def structural_hash(pattern: Any) -> bytes:
    """Compute a deterministic, cross-run-stable structural hash.

    Accepts:
    - :class:`StructuralPattern` — hashed on all declared fields.
    - ``dict`` / ``Mapping`` — hashed after canonicalization; float values and
      keys matching continuous-value markers are dropped.
    - ``tuple`` / ``list`` — hashed element-wise after canonicalization.

    Returns 32 bytes suitable for use as a dict key.

    Determinism:
    - Uses :func:`hashlib.blake2b` (not Python's built-in randomized hash).
    - Output is stable across Python runs, across processes, and across
      platforms for a given framework version.
    """
    if isinstance(pattern, StructuralPattern):
        payload = canonicalize(pattern.to_dict(), drop_continuous=False)
        # Tag the payload so that a StructuralPattern and a raw dict with the
        # same fields cannot collide — the safety concern is any source of
        # ambiguity in cache-key provenance.
        payload = {"__pattern__": payload}
    elif isinstance(pattern, Mapping):
        payload = canonicalize(pattern, drop_continuous=True)
    elif isinstance(pattern, (list, tuple)):
        payload = canonicalize(pattern, drop_continuous=True)
    else:
        payload = canonicalize(pattern, drop_continuous=True)

    encoded = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.blake2b(encoded, digest_size=32).digest()
