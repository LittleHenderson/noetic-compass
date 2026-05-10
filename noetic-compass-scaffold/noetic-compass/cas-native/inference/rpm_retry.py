"""Phase 3 experiment — corrective retry for rpm_chain renderings.

Per user directive 2026-05-10 (post Phase 2 audit bbcf5d7):

  Next best experiment is an RPM-only corrective retry using the
  Phase 2 drift log as feedback for records 19-21. If that moves
  19/20 from yellow to high-yellow or green without breaking
  identifiers/edges, then Phase 2 becomes the trigger for a
  targeted RPM retry path.

This module is the EXPERIMENT. It is opt-in by default — the user
must set ``apply_rpm_retry=True`` on routed_generate (or
``USE_V1C_RPM_RETRY=1`` on the eval script) to engage it.

How the retry works:
  1. The first generation runs through Phase 1 (structural repair)
     and Phase 2 (semantic verifier) as usual.
  2. If Phase 2's drift log has at least one ``SemanticDrift`` AND
     Phase 1's structure is intact (all stage_vars present, edge
     matched post-repair), the retry path is triggered.
  3. A corrective prompt is built from the source CAS PLUS a list
     of vocabulary hints derived from the drifted axes (which
     Noetic / Domain / Drive labels the previous output got wrong,
     and what the canonical colloquialism for each is).
  4. ``generate_reply`` is called again with the corrective prompt.
  5. The retry output is postprocessed through Phase 1 + Phase 2.
  6. Comparison heuristic: retry "wins" iff it has STRICTLY FEWER
     drifts AND preserves all stage_vars AND the edge still
     matches source. Anything else falls back to the first attempt.

Failure mode to expect: the model was trained on a single prompt
format ("Describe the following CAS expression in plain English:")
and never on corrective/instructional prompts, so it may ignore
the vocabulary hint section. The experiment will tell us whether
in-context learning is enough to bias the output, or whether
seed-enrichment / training-side intervention is necessary.

This module does NOT touch the post-generated text directly. The
user's "don't auto-rewrite semantic labels yet" guard is satisfied:
the retry path produces a new generation; if the new generation is
better by structural metrics, it's used; otherwise the original
stands. No string substitution at the label level.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from cas_native.inference.rpm_repair import (
    RpmRepairLog,
    SemanticDrift,
)


# ---------------------------------------------------------------------------
# Canonical vocabulary hints (derived from CLAUDE.md Clarification 6)
# ---------------------------------------------------------------------------
#
# The corrective prompt only includes hints for axes that actually
# drifted. We do NOT dump the full colloquialism map every time —
# that would make the prompt hugely OOD relative to training. Hints
# stay narrow and named.

_NOETIC_HINTS: dict[int, str] = {
    0: '"a foundational thought" / "an idea"',
    1: '"paying attention" / "cognitive attention"',
    2: '"drawn to" / "speaks to"',
    3: '"rubs the wrong way" / "averse to"',
    4: '"struck a chord" / "made an impression"',
    5: '"who one is" / "shaped by experiences"',
    6: '"breaking it down" / "unpacking"',
    7: '"practiced rhythm" / "muscle memory"',
    8: '"that reminds me" / "triggered a memory"',
    9: '"popped into mind" / "just clicked"',
}

_DOMAIN_HINTS: dict[str, str] = {
    "P": '"principled foundation" / "principled"',
    "C": '"cognitive thinking" / "cognitive"',
    "E": '"evaluative judgment" / "evaluative"',
    "O": '"operational behavior" / "operational"',
}

_DRIVE_HINTS: dict[int, str] = {
    1: '"unity" / "togetherness"',
    2: '"wisdom and insight"',
    3: '"vitality and energy"',
    4: '"connection" / "attachment"',
    5: '"agency and self-determination"',
    6: '"structure" / "order"',
    7: '"purpose" / "meaning"',
}


# ---------------------------------------------------------------------------
# Retry log (audit-friendly)
# ---------------------------------------------------------------------------

@dataclass
class RpmRetryLog:
    """Audit-friendly summary of one Phase 3 retry attempt.

    ``attempted`` is True when the retry path actually fired (drift
    log non-empty AND structure intact). ``used_retry`` is True when
    the retry result strictly beat the original by the comparison
    heuristic. ``hint_axes`` lists which axes contributed hints to
    the corrective prompt (e.g., ``["noetic", "drive"]``).
    """
    attempted: bool = False
    used_retry: bool = False
    reason: str = ""  # one-line explanation if retry skipped or rejected
    n_drifts_original: int = 0
    n_drifts_retry: int = 0
    hint_axes: list[str] = field(default_factory=list)
    corrective_prompt: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "attempted": self.attempted,
            "used_retry": self.used_retry,
            "reason": self.reason,
            "n_drifts_original": self.n_drifts_original,
            "n_drifts_retry": self.n_drifts_retry,
            "hint_axes": list(self.hint_axes),
            "corrective_prompt": self.corrective_prompt,
        }


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def _hint_lines_from_drifts(drifts: list[SemanticDrift]) -> tuple[list[str], list[str]]:
    """Return (hint_lines, axes_used) — the hint section of the
    corrective prompt and the list of axes that contributed.

    Each drift contributes one hint per axis it flagged. Duplicates
    across stages are deduplicated (one hint per unique axis-value
    pair) so the prompt stays compact.
    """
    seen: set[tuple[str, object]] = set()
    lines: list[str] = []
    axes: list[str] = []

    for d in drifts:
        # Noetic
        if d.expected_noetic is not None and any(
            "noetic" in k for k in d.drift_kinds
        ):
            key = ("noetic", d.expected_noetic)
            if key not in seen:
                seen.add(key)
                hint = _NOETIC_HINTS.get(d.expected_noetic)
                if hint:
                    lines.append(f"- ^{d.expected_noetic} should sound like {hint}")
                    if "noetic" not in axes:
                        axes.append("noetic")
        # Domain
        if d.expected_domain is not None and any(
            "domain" in k for k in d.drift_kinds
        ):
            key = ("domain", d.expected_domain)
            if key not in seen:
                seen.add(key)
                hint = _DOMAIN_HINTS.get(d.expected_domain)
                if hint:
                    lines.append(f"- ^{d.expected_domain} should sound like {hint}")
                    if "domain" not in axes:
                        axes.append("domain")
        # Drive
        if d.expected_drive is not None and any(
            "drive" in k for k in d.drift_kinds
        ):
            key = ("drive", d.expected_drive)
            if key not in seen:
                seen.add(key)
                hint = _DRIVE_HINTS.get(d.expected_drive)
                if hint:
                    lines.append(f"- F{d.expected_drive} should sound like {hint}")
                    if "drive" not in axes:
                        axes.append("drive")

    return lines, axes


def build_corrective_prompt(
    source_cas: str, drifts: list[SemanticDrift],
) -> tuple[str, list[str]]:
    """Build the Phase 3 corrective prompt + return the axes used.

    The prompt format intentionally extends the model's training
    prompt minimally:

        Describe the following CAS expression in plain English.
        Use these vocabulary mappings:
        - <hint 1>
        - <hint 2>
        ...

        <CAS>

    The model was NOT trained on this format. The experiment is
    whether in-context learning lets the hint section bias the
    output toward canonical colloquialisms. If not, the comparison
    heuristic falls back to the original generation.
    """
    hint_lines, axes_used = _hint_lines_from_drifts(drifts)
    if not hint_lines:
        # No hints to give — return a no-op prompt that's identical
        # to the standard format. Caller should detect this via
        # axes_used == [] and skip the retry.
        return (
            f"Describe the following CAS expression in plain English:\n\n{source_cas}",
            axes_used,
        )
    hint_block = "\n".join(hint_lines)
    prompt = (
        "Describe the following CAS expression in plain English. "
        "Use these vocabulary mappings:\n"
        f"{hint_block}\n\n"
        f"{source_cas}"
    )
    return prompt, axes_used


# ---------------------------------------------------------------------------
# Comparison heuristic
# ---------------------------------------------------------------------------

def retry_strictly_beats_original(
    *,
    original_log: RpmRepairLog,
    retry_log: RpmRepairLog,
) -> tuple[bool, str]:
    """Return ``(is_better, reason)``. The retry "wins" iff:
      - retry has STRICTLY FEWER semantic drifts than original
      - retry preserves the same number of stage_vars
        (n_stages_found_post_repair >= original's count)
      - retry's edge_matched_post_repair is True if source has an edge
        (i.e., edge integrity not regressed)
    Any condition failing -> retry rejected, fall back to original.
    """
    n_orig = len(original_log.semantic_drifts)
    n_retry = len(retry_log.semantic_drifts)
    if n_retry >= n_orig:
        return False, (
            f"retry drift count {n_retry} not strictly less than "
            f"original {n_orig}"
        )
    if retry_log.n_stages_found_post_repair < original_log.n_stages_found_post_repair:
        return False, (
            f"retry lost stage coverage "
            f"({retry_log.n_stages_found_post_repair} vs "
            f"{original_log.n_stages_found_post_repair})"
        )
    if (
        original_log.edge_present_in_source
        and not retry_log.edge_matched_post_repair
    ):
        return False, "retry broke the closing edge"
    return True, (
        f"retry strictly better: drifts {n_orig} -> {n_retry}, "
        f"stages {original_log.n_stages_found_post_repair} -> "
        f"{retry_log.n_stages_found_post_repair}"
    )


def should_attempt_retry(log: RpmRepairLog) -> tuple[bool, str]:
    """Gate the retry: only fire when there's something to fix AND
    the structural skeleton is intact (no point retrying if the
    base is already broken — that's a different bug)."""
    if not log.chain_parsed:
        return False, "not an rpm_chain"
    if not log.semantic_drifts:
        return False, "no semantic drifts to correct"
    if log.n_stages_found_post_repair < log.n_stages_expected:
        return False, "stage coverage incomplete; retry won't help"
    if log.edge_present_in_source and not log.edge_matched_post_repair:
        return False, "edge unmatched; retry would compound the issue"
    return True, "drift-only mismatch with structure intact"


__all__ = [
    "RpmRetryLog",
    "build_corrective_prompt",
    "retry_strictly_beats_original",
    "should_attempt_retry",
]
