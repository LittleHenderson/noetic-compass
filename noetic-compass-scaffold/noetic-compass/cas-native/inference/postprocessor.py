"""Gated post-generation pipeline for CAS-Native NL generation.

Composes:
  1. compilability-gated task routing (:mod:`cas_native.inference.cas_routing`)
  2. identifier repair (:mod:`cas_native.inference.identifier_repair`)
  3. quality checks on the (optionally repaired) output

This module is the durable seam where the model's raw generation is
turned into an audit-friendly final response. It is **opt-in by
design**: callers ask for routing and repair explicitly. The
postprocessor never silently mutates a generation.

Quality discipline (per user feedback memory `feedback_separate_evidence_levels_in_status`):
  - identifier repair: deterministic, only fills slots that already exist
  - quality checks: read-only signals; do not mutate
  - SFE/structural checks are NOT run here (they live in
    cas-synthetic/scripts/sfe.py and require cross-package access).
    Callers that want SFE round-trip validation can run it on the
    ``final_text`` field of :class:`PostprocessResult`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from cas_native.inference.cas_routing import (
    RoutingDecision,
    route_by_compilability,
    build_prompt_from_routing,
)
from cas_native.inference.identifier_repair import (
    IdentifierRecoveryScore,
    RepairLog,
    repair_identifiers,
    score_identifier_recovery,
)


# ---------------------------------------------------------------------------
# Quality-check primitives (read-only; no mutation)
# ---------------------------------------------------------------------------

# Hard CAS notation that should never appear in final English output.
_HARD_NOTATION_RX = re.compile(
    r"\^\d"                                     # ^N
    r"|\bF[1-7]\b"                              # bare F-drive
    r"|StateCluster|RelationCluster|NoeticCluster"
    r"|[∩∪∖∈⊂⊆⊃⊇]"                            # meta-logic ops
    r"|→"                                       # arrow
)

# Jargon (technical CAS vocabulary) that leaks framework lexicon.
_JARGON_RX = re.compile(
    r"\boperator(s|ial|ially)?\b"
    r"|\bnoetic(s)?\b"
    r"|\bcognitive operation",
    re.IGNORECASE,
)


def count_hard_notation(text: str) -> int:
    return len(_HARD_NOTATION_RX.findall(text))


def count_jargon(text: str) -> int:
    return len(_JARGON_RX.findall(text))


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class PostprocessResult:
    """Audit-friendly bundle of everything the postprocessor produced.

    ``final_text`` is what the caller should surface to the user. It
    is either the raw generation (when ``apply_repair=False``) or the
    repaired generation (when ``apply_repair=True``). ``raw_text`` is
    the unmodified model output for comparison.

    ``routing`` records the compiler's verdict, including which task
    was routed and any error diagnostics. ``repair_log`` captures every
    identifier substitution applied. ``quality`` carries hard-notation
    / jargon counts and identifier-recovery scores both BEFORE and
    AFTER repair so callers can audit the delta. ``truncated`` is True
    when the underlying generation hit ``max_new_tokens`` without
    emitting EOS — this catches the v1-PREFIX128-5ep failure pattern
    where records 7 and 8 produced the same incomplete sentence
    "...A careful reader would noti..." for two different tasks.
    """
    final_text: str
    raw_text: str
    routing: RoutingDecision
    repair_applied: bool
    repair_log: Optional[RepairLog] = None
    recovery_pre_repair: Optional[IdentifierRecoveryScore] = None
    recovery_post_repair: Optional[IdentifierRecoveryScore] = None
    hard_notation_count: int = 0
    jargon_count: int = 0
    truncated: bool = False
    quality_passed: bool = True
    quality_failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "final_text": self.final_text,
            "raw_text": self.raw_text,
            "routing": self.routing.to_dict(),
            "repair_applied": self.repair_applied,
            "repair_log": (
                {
                    "omega_substitutions": self.repair_log.omega_substitutions,
                    "coefficient_substitutions": self.repair_log.coefficient_substitutions,
                    "variable_substitutions": self.repair_log.variable_substitutions,
                    "total": self.repair_log.total,
                }
                if self.repair_log is not None else None
            ),
            "recovery_pre_repair": (
                self.recovery_pre_repair.to_dict()
                if self.recovery_pre_repair is not None else None
            ),
            "recovery_post_repair": (
                self.recovery_post_repair.to_dict()
                if self.recovery_post_repair is not None else None
            ),
            "hard_notation_count": self.hard_notation_count,
            "jargon_count": self.jargon_count,
            "truncated": self.truncated,
            "quality_passed": self.quality_passed,
            "quality_failures": list(self.quality_failures),
        }


# ---------------------------------------------------------------------------
# Postprocess entry point
# ---------------------------------------------------------------------------

def postprocess(
    *,
    source_cas: str,
    raw_gen: str,
    routing: Optional[RoutingDecision] = None,
    apply_repair: bool = False,
    score_recovery: bool = True,
    quality_check: bool = True,
    stopped_on_eos: Optional[bool] = None,
) -> PostprocessResult:
    """Run the post-generation pipeline.

    Args:
        source_cas: the source CAS expression (used for routing,
            identifier extraction, and recovery scoring).
        raw_gen: the model's raw generation, before any postprocessing.
        routing: optional precomputed routing; when None, this function
            computes it via :func:`route_by_compilability`. Callers
            that already have routing (e.g. to construct the prompt
            before invoking the model) should pass it through here so
            the result is consistent.
        apply_repair: when True, run identifier repair and use the
            repaired text as ``final_text``. Default False (opt-in).
        score_recovery: when True, compute pre-repair and (if applied)
            post-repair identifier-recovery scores.
        quality_check: when True, count hard-notation and jargon hits
            in ``final_text`` and set ``quality_passed`` accordingly.
        stopped_on_eos: pass-through from generate_reply's metadata.
            When False, the generation hit ``max_new_tokens`` without
            emitting EOS — flagged as ``truncated`` in the result and
            counted as a quality failure. Pass ``None`` to skip the
            truncation check (e.g. for unit tests on raw text snippets).

    The return value is always populated; specific fields may be
    ``None`` when the corresponding option is disabled.
    """
    if routing is None:
        routing = route_by_compilability(source_cas)

    repair_log: Optional[RepairLog] = None
    final_text = raw_gen
    if apply_repair:
        final_text, repair_log = repair_identifiers(
            source_cas=source_cas, english=raw_gen,
        )

    recovery_pre: Optional[IdentifierRecoveryScore] = None
    recovery_post: Optional[IdentifierRecoveryScore] = None
    if score_recovery:
        recovery_pre = score_identifier_recovery(
            source_cas=source_cas, english=raw_gen,
        )
        if apply_repair:
            recovery_post = score_identifier_recovery(
                source_cas=source_cas, english=final_text,
            )

    hard = 0
    jargon = 0
    quality_passed = True
    quality_failures: list[str] = []
    truncated = False
    if quality_check:
        hard = count_hard_notation(final_text)
        jargon = count_jargon(final_text)
        if hard > 0:
            quality_passed = False
            quality_failures.append(f"hard_notation_count={hard}")
        if jargon > 0:
            quality_passed = False
            quality_failures.append(f"jargon_count={jargon}")
        # Truncation check: stopped_on_eos=False means generation
        # hit max_new_tokens without emitting EOS — caller should
        # either retry with a higher budget or surface the gen as
        # incomplete rather than ship a clipped sentence.
        if stopped_on_eos is False:
            truncated = True
            quality_passed = False
            quality_failures.append("truncated_at_max_tokens")

    return PostprocessResult(
        final_text=final_text,
        raw_text=raw_gen,
        routing=routing,
        repair_applied=apply_repair,
        repair_log=repair_log,
        recovery_pre_repair=recovery_pre,
        recovery_post_repair=recovery_post,
        hard_notation_count=hard,
        jargon_count=jargon,
        truncated=truncated,
        quality_passed=quality_passed,
        quality_failures=quality_failures,
    )


__all__ = [
    "PostprocessResult",
    "postprocess",
    "count_hard_notation",
    "count_jargon",
    "build_prompt_from_routing",
    "route_by_compilability",
]
