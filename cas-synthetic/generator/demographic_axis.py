"""Demographic + tonal surface-rewrite axis for CAS-Synthetic Data Generation.

Task #68: Extend SDG with demographic + tonal variety axes.

FRAMING — read before modifying:
    The four CAS v7.7 Registers (T/A/f/E — Transcendent/Analytical/Affective/
    Embodied) are operational-character axes that describe HOW a cognitive
    operation manifests, not WHO the speaker is.  Demographic + tonal axes
    are orthogonal to Register.  They apply exclusively at the prompt-surface
    layer.

    The CAS expression for the same record is IDENTICAL across all
    demographic/tonal renderings.  Only user-facing text fields are touched.

AXES (named-value sets drawn from AI psychology/ethics evaluation literature:
    HELM, BBQ, StereoSet, CrowS-Pairs, WinoGrande, HolisticBias):

    age_band           : youth | adult | older
    cultural_register  : western_academic | western_vernacular | non_western
    tonal              : formal | casual | technical | plain_speech

Cross product → 3 × 3 × 4 = 36 deterministic cells.

INTEGRATION SEAM (not wired in this PR — proof of concept only):
    The natural injection point is Level3ConversationalGenerator._build_variant()
    in generator/conversational.py, after the ConversationalExample is assembled.
    Call apply_demographic_axis(example.to_dict(), spec) and write the result
    instead of example.to_dict().  The spec can be drawn round-robin or
    randomly from AXIS_GRID to achieve balanced cell coverage.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Axis vocabularies
# ---------------------------------------------------------------------------

AGE_BANDS: tuple[str, ...] = ("youth", "adult", "older")
CULTURAL_REGISTERS: tuple[str, ...] = (
    "western_academic",
    "western_vernacular",
    "non_western",
)
TONALS: tuple[str, ...] = ("formal", "casual", "technical", "plain_speech")

AXIS_GRID: tuple[tuple[str, str, str], ...] = tuple(
    (ab, cr, t)
    for ab in AGE_BANDS
    for cr in CULTURAL_REGISTERS
    for t in TONALS
)  # 36 cells, deterministic order


# ---------------------------------------------------------------------------
# Surface-phrase pools
#
# Each pool entry is a 2-3 phrase list; the seed selects among them.
# Design principle: phrases shift register/voice without implying content —
# the underlying cognitive situation is unchanged.
# ---------------------------------------------------------------------------

_AGE_OPENERS: dict[str, list[str]] = {
    "youth": [
        "I'm still learning about this —",
        "Can you help me understand this for a class project?",
        "I've been trying to figure this out —",
    ],
    "adult": [
        "",
        "I want to work through this situation carefully.",
        "I need a clear read on this.",
    ],
    "older": [
        "I've been reflecting on this for a while —",
        "Looking back on many situations like this,",
        "After considerable thought,",
    ],
}

_CULTURAL_FRAMERS: dict[str, list[str]] = {
    "western_academic": [
        "from an analytical standpoint,",
        "examining this theoretically,",
        "approaching this with structured inquiry,",
    ],
    "western_vernacular": [
        "",
        "basically,",
        "to be straight about it,",
    ],
    "non_western": [
        "with respectful attention to the full picture —",
        "considering all sides carefully —",
        "asking with due consideration —",
    ],
}

_TONAL_WRAPPERS: dict[str, list[str]] = {
    "formal": [
        "I would appreciate a thorough analysis of",
        "Could you please provide a careful examination of",
        "I respectfully request your assessment of",
    ],
    "casual": [
        "Can you just break down",
        "Hey, help me get a handle on",
        "Could you walk me through",
    ],
    "technical": [
        "Provide a precise technical read of",
        "Analyze the formal structure of",
        "Give me the exact structural account of",
    ],
    "plain_speech": [
        "In plain terms, explain",
        "Help me understand in simple language",
        "Just explain clearly",
    ],
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DemographicAxisSpec:
    """Validated axis coordinates for a single demographic+tonal rendering.

    All three values must be from the authoritative named-value sets above.
    The ``seed`` controls phrase selection within the cell, making output
    fully deterministic: same record + same spec + same seed → same output.
    """

    age_band: str
    cultural_register: str
    tonal: str
    seed: int = 42

    def __post_init__(self) -> None:
        if self.age_band not in AGE_BANDS:
            raise ValueError(
                f"age_band must be one of {AGE_BANDS!r}; got {self.age_band!r}"
            )
        if self.cultural_register not in CULTURAL_REGISTERS:
            raise ValueError(
                f"cultural_register must be one of {CULTURAL_REGISTERS!r}; "
                f"got {self.cultural_register!r}"
            )
        if self.tonal not in TONALS:
            raise ValueError(
                f"tonal must be one of {TONALS!r}; got {self.tonal!r}"
            )

    @property
    def cell_key(self) -> str:
        """Compact string identifier for this cell, safe for filenames/tags."""
        return f"{self.age_band}__{self.cultural_register}__{self.tonal}"

    def tag_labels(self) -> list[str]:
        """Return the three canonical tag labels for this spec."""
        return [
            f"demo_age_{self.age_band}",
            f"demo_culture_{self.cultural_register}",
            f"tonal_{self.tonal}",
        ]


def apply_demographic_axis(
    record: dict[str, Any],
    spec: DemographicAxisSpec,
) -> dict[str, Any]:
    """Return a new record with demographic+tonal surface rendering applied.

    Invariants (verified by tests):
    - ``output["cas_expression"] == input["cas_expression"]``
    - ``output["soft_operator_targets"] == input["soft_operator_targets"]``
    - ``output["soft_domain_targets"] == input["soft_domain_targets"]``
    - Output is deterministic: same record + same spec → same output.
    - The function never mutates the input record dict.

    Parameters
    ----------
    record:
        A Level 3 conversational record dict (ConversationalExample.to_dict()).
        Must contain at least ``user_prompt`` and ``cas_expression``.
    spec:
        Validated axis coordinates + seed.

    Returns
    -------
    dict
        Shallow copy of record with rewritten text fields and enriched
        provenance + tags.
    """
    rng = _make_rng(record, spec)
    output = dict(record)

    output["user_prompt"] = _render_user_prompt(record.get("user_prompt", ""), spec, rng)
    output["provenance"] = _enrich_provenance(record.get("provenance", {}), spec)
    output["tags"] = _enrich_tags(record.get("tags", []), spec)

    # Derived id: stable under (original_id, cell_key, seed).
    original_id = record.get("id", "")
    output["id"] = _derive_id(original_id, spec)

    return output


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _make_rng(record: dict[str, Any], spec: DemographicAxisSpec) -> random.Random:
    """Produce a seeded RNG that is unique to (record_id, cell, seed)."""
    record_id = record.get("id", record.get("cas_expression", ""))
    digest = hashlib.sha1(
        f"{spec.seed}|{record_id}|{spec.cell_key}".encode()
    ).hexdigest()
    return random.Random(int(digest[:8], 16))


def _render_user_prompt(
    original: str,
    spec: DemographicAxisSpec,
    rng: random.Random,
) -> str:
    """Compose a demographically-framed user_prompt from the original.

    Structure: ``{age_opener} {cultural_framer} {tonal_wrapper} {original}``
    Empty components are suppressed.  The result is a single sentence that
    reframes WHO is asking without changing WHAT is being asked.
    """
    age_opener = rng.choice(_AGE_OPENERS[spec.age_band])
    cultural_framer = rng.choice(_CULTURAL_FRAMERS[spec.cultural_register])
    tonal_wrapper = rng.choice(_TONAL_WRAPPERS[spec.tonal])

    parts = [p for p in (age_opener, cultural_framer) if p]
    prefix = " ".join(parts)

    if prefix:
        composed = f"{prefix} {tonal_wrapper} the following: {original}"
    else:
        composed = f"{tonal_wrapper} the following: {original}"

    return composed.strip()


def _enrich_provenance(
    original: dict[str, Any],
    spec: DemographicAxisSpec,
) -> dict[str, Any]:
    """Return a copy of provenance with demographic axis fields added."""
    enriched = dict(original)
    enriched["demographic_age_band"] = spec.age_band
    enriched["demographic_cultural_register"] = spec.cultural_register
    enriched["demographic_tonal"] = spec.tonal
    enriched["demographic_seed"] = spec.seed
    enriched["demographic_cell_key"] = spec.cell_key
    return enriched


def _enrich_tags(original: list[str], spec: DemographicAxisSpec) -> list[str]:
    """Return tags with demographic axis labels appended (deduplicated)."""
    merged = list(original)
    for label in spec.tag_labels():
        if label not in merged:
            merged.append(label)
    if "demographic_variant" not in merged:
        merged.append("demographic_variant")
    return merged


def _derive_id(original_id: str, spec: DemographicAxisSpec) -> str:
    """Stable derived ID for the demographic rendering of a record."""
    digest = hashlib.sha1(
        f"{original_id}|{spec.cell_key}|{spec.seed}".encode()
    ).hexdigest()[:12]
    return f"dem-{digest}"
