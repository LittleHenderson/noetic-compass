"""Abstract base class for CAS synthetic data generators.

Each version-specific generator (v7.4, v7.5, v7.6, v7.7) extends this base
and yields `GeneratedExample` instances conforming to the per-example schema
in `noetic-compass-scaffold/noetic-compass/cas-native/training/data_format.md`.

Design:
- Streaming: generators yield one example at a time so 10K / millions can
  be produced without materializing a list.
- Seedable: every generator accepts an optional `seed` and uses a private
  `random.Random` so the same seed reproduces the same sequence regardless
  of global RNG state.
- Template-first: each generator uses a YAML-backed template pool for
  structural correctness, then optionally paraphrases via an LLM provider
  for semantic diversity.
"""

from __future__ import annotations

import abc
import random
from dataclasses import dataclass, field
from typing import Any, Iterator


# ---------------------------------------------------------------------------
# Data schema per cas-native/training/data_format.md
# ---------------------------------------------------------------------------


@dataclass
class GeneratedExample:
    """One training example, schema-compliant with data_format.md.

    Serializes to a dict via `to_dict()` which produces exactly the JSONL
    shape expected by `CASTrainer` / v2 data pipeline. Only `prompt` /
    `response` are required; every other field is optional and masked out
    of the corresponding loss term when absent.
    """

    prompt: str
    response: str
    cas_expression: str = ""                 # source CAS expression (not in data_format.md but kept for traceability)
    scores: dict[str, list[float]] | None = None
    register_labels: list[dict[str, Any]] = field(default_factory=list)
    omega_labels: list[dict[str, Any]] = field(default_factory=list)
    production_target: dict[str, Any] | None = None

    # --- Bucket tracking / validation metadata (not in data_format.md) ---
    bucket: str = ""                         # which generator bucket produced this
    is_valid: bool = True
    violation_type: str | None = None
    distance_to_valid: float = 0.0

    def to_dict(self, *, include_metadata: bool = True) -> dict[str, Any]:
        """Emit the dict that will be written to JSONL.

        `include_metadata` controls inclusion of the bucket / is_valid /
        violation_type / distance_to_valid traceability fields. Downstream
        consumers that strictly require data_format.md shape can call with
        `include_metadata=False`.
        """
        out: dict[str, Any] = {
            "prompt": self.prompt,
            "response": self.response,
        }
        if self.cas_expression:
            out["cas_expression"] = self.cas_expression
        if self.scores is not None:
            out["scores"] = self.scores
        if self.register_labels:
            out["register_labels"] = list(self.register_labels)
        if self.omega_labels:
            out["omega_labels"] = list(self.omega_labels)
        if self.production_target is not None:
            out["production_target"] = dict(self.production_target)
        if include_metadata:
            out["_meta"] = {
                "bucket": self.bucket,
                "is_valid": self.is_valid,
                "violation_type": self.violation_type,
                "distance_to_valid": self.distance_to_valid,
            }
        return out


# ---------------------------------------------------------------------------
# BaseGenerator
# ---------------------------------------------------------------------------


class BaseGenerator(abc.ABC):
    """Abstract base for CAS synthetic generators.

    Subclasses implement `_generate_one` which produces a single
    GeneratedExample. `iter_examples(n)` is the streaming entry point the
    mix controller drives; it yields `n` examples one at a time.
    """

    #: Canonical bucket name used by the mix controller to target this
    #: generator. Must be set on each subclass.
    BUCKET: str = ""

    def __init__(self, seed: int | None = None, llm_provider: Any = None) -> None:
        self._seed = seed
        self.rng = random.Random(seed)
        self.llm_provider = llm_provider
        if not self.BUCKET:
            raise RuntimeError(
                f"{type(self).__name__}: BUCKET class attribute must be set"
            )

    # ----------------------------------------------------------- public API

    def iter_examples(self, n: int) -> Iterator[GeneratedExample]:
        """Yield `n` examples one at a time (streaming)."""
        for _ in range(n):
            yield self._generate_one()

    def generate_batch(self, n: int) -> list[GeneratedExample]:
        """Materialize `n` examples into a list. Convenience only — prefer
        `iter_examples` for large n."""
        return list(self.iter_examples(n))

    # ------------------------------------------------------ subclass hooks

    @abc.abstractmethod
    def _generate_one(self) -> GeneratedExample:
        """Produce one example. Subclasses must implement."""
        raise NotImplementedError

    # ---------------------------------------------------- helper utilities

    # Canonical vocabulary — used by all subclasses. Kept here so a single
    # source of truth exists.
    NOETICS: list[int] = list(range(10))
    DOMAINS: list[str] = ["P", "C", "E", "O"]
    DRIVES: list[int] = list(range(1, 8))
    REGISTERS: list[str] = ["T", "A", "f", "E"]   # lowercase `f` is authoritative per Clarification 8

    def _state_id(self, noetic: int, domain: str) -> int:
        """Return the 0..39 state id for (noetic, domain).

        Ordering matches cas-native convention: P0..P9, C0..C9, E0..E9, O0..O9.
        """
        dom_index = self.DOMAINS.index(domain)
        return dom_index * 10 + noetic

    def _scores_from_states(self, states: list[tuple[int, str]]) -> dict[str, list[float]]:
        """Produce operator/domain score vectors from a list of (noetic, domain) pairs."""
        op_counts = [0.0] * 10
        dom_counts = [0.0] * 4
        for noetic, dom in states:
            op_counts[noetic] += 1.0
            dom_counts[self.DOMAINS.index(dom)] += 1.0
        max_op = max(op_counts) if max(op_counts) > 0 else 1.0
        max_dom = max(dom_counts) if max(dom_counts) > 0 else 1.0
        return {
            "operator_scores": [round(s / max_op, 4) for s in op_counts],
            "domain_scores": [round(s / max_dom, 4) for s in dom_counts],
        }
