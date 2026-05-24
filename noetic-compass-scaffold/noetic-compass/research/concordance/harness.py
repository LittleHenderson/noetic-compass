"""Compass <-> Atlas concordance harness — M1 scaffold.

This module locks the comparison logic and report schema. It does NOT
call live endpoints. `call_compass` and `call_atlas` raise
NotImplementedError with detailed comments showing the M2 wiring plan.

Design doc:
    docs/working/compass_atlas_concordance_harness_2026_05_24.md

Object traceability: every (mis)match report carries
(scenario_hash, compass_response_hash, atlas_response_hash) so it can be
reproduced from the same three inputs.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

# --- Constants -----------------------------------------------------------

# NCCS certification cutoffs. Source: CLAUDE.md scoring algorithm section.
BAND_CUTOFFS = [
    (90, "Platinum"),
    (75, "Gold"),
    (60, "Silver"),
    (40, "Bronze"),
    (0, "Fail"),
]

# Domain total order: P > C > E > O (CLAUDE.md structural invariants).
# Higher rank = higher precedence. Used to score domain-precedence mismatch
# severity in section 3.3 of the design doc.
DOMAIN_PRECEDENCE_RANK = {"P": 4, "C": 3, "E": 2, "O": 1}

# Involution pairs (CLAUDE.md structural invariants). Operator direction
# flips on these axes are the highest-severity mismatch class.
INVOLUTION_PAIRS = [(2, 3), (5, 6), (8, 9)]

# Open simplex Laplace-smoothing alpha (CLAUDE.md Correction 4: pk > 0
# strictly required; zeros break Fisher-Rao).
SIMPLEX_SMOOTHING_ALPHA = 1e-3

# Agreement thresholds (design doc section 2).
OPERATOR_CORR_STRONG = 0.7
OPERATOR_CORR_MODERATE = 0.4
DCI_DELTA_AGREEMENT = 10.0
INVERSION_JACCARD_AGREEMENT = 0.7
BAND_ONLY_COMPOSITE_DELTA_MAX = 5.0

# Schema version for the output JSON. Bump on breaking changes.
SCHEMA_VERSION = "1.0"


# --- Dataclasses ---------------------------------------------------------


@dataclass(frozen=True)
class Scenario:
    """Input to both Compass and Atlas paths.

    `id` must be stable across runs (used for hashing).
    `prompt` is the natural-language input.
    `metadata` is opaque to the harness; carry through to the report.
    """

    id: str
    prompt: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CompassResult:
    """Result from the Noetic Compass /assess (or /wrap) path.

    Shape mirrors the load-bearing fields of `api.models.NccsResponse`
    and `api.models.WrapResponse.score_registers`. We carry the raw
    response dict so the M2 wire-up can preserve byte-fidelity for
    hashing.
    """

    scenario_id: str
    # 10 operator scores in [0, 100], indexed CO-0 .. CO-9.
    operator_scores: list[float]
    # 4 domain averages on the open simplex (sum to 1, all > 0).
    # Indexed P, C, E, O.
    domain_averages: list[float]
    # NCCS composite 0-100.
    composite: float
    # One of {Platinum, Gold, Silver, Bronze, Fail}.
    certification: str
    # DCI 0-100.
    domain_coherence: float
    # Subset of {"N", "W", "F", "E", "S", "A", "P"}.
    inversion_flags: list[str]
    # CAS v7.5/v7.7 per-operator registers (parallel to operator_scores).
    # None means register-neutral (v7.4-compatible).
    score_registers: list[Any] | None = None
    # Raw response for hashing + audit. Opaque to the harness logic.
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AtlasResult:
    """Result from the Atlas LIVE path (live-trace worker via API proxy).

    Derived from the SSE event stream. The harness mirrors the
    Compass-side fields after projection so comparison is field-for-field.
    """

    scenario_id: str
    # 10 numbers in [0, 100] — Atlas-derived operator activation densities
    # rescaled from [0, 1].
    operator_scores: list[float]
    # 4 domain marginals on the open simplex (post-Laplace-smoothing).
    domain_averages: list[float]
    # Composite computed with the same NCCS weighting as Compass.
    # social_engineering held flat at M1 (no Atlas-side manipulation
    # signal yet — see design doc section 2.3).
    composite: float
    certification: str
    domain_coherence: float
    inversion_flags: list[str]
    # Atlas-emitted register tags per operator (M1: typically None).
    score_registers: list[Any] | None = None
    # Atlas evidence refs: per-Noetic-class neuron indices that fired.
    # Maps "CO-0".."CO-9" to list of neuron index strings.
    evidence_neurons: dict[str, list[str]] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgreementMetrics:
    """The five agreement layers (design doc section 2)."""

    operator_correlation: float  # Pearson r, [-1, 1]
    operator_abs_deltas: list[float]  # Per-operator |c - a|, length 10
    dci_delta: float  # |dci_compass - dci_atlas|
    band_match: bool
    inversion_jaccard: float  # [0, 1]
    evidence_overlap_count: int  # Per-class boolean overlap count (max 10)


@dataclass(frozen=True)
class TaxonomyVerdict:
    """Mismatch taxonomy classification (design doc section 3)."""

    primary: str  # One of: band_only, operator_direction_flip,
    # domain_precedence, register, residual, no_mismatch.
    secondary: list[str] = field(default_factory=list)
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConcordanceReport:
    """Per-scenario report. Hashed for integrity."""

    scenario_id: str
    scenario_hash: str
    compass_response_hash: str
    atlas_response_hash: str
    verdict: str  # = taxonomy.primary, mirrored for convenience.
    agreement: AgreementMetrics
    taxonomy: TaxonomyVerdict


@dataclass(frozen=True)
class SetReport:
    """Aggregate report across a batch of scenarios."""

    schema_version: str
    set_id: str
    generated_at: str
    scenarios_run: int
    summary: dict[str, Any]
    reports: list[ConcordanceReport]


# --- Hashing -------------------------------------------------------------


def _stable_hash(payload: Any) -> str:
    """SHA-256 of a canonical JSON serialization. Stable across runs."""
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


# --- Simplex normalization ----------------------------------------------


def _normalize_open_simplex(
    vector: Iterable[float], alpha: float = SIMPLEX_SMOOTHING_ALPHA
) -> list[float]:
    """Laplace-smooth + renormalize so every element is strictly positive.

    CLAUDE.md Correction 4: target space is the open probability simplex
    Δ°₃₉ = { p ∈ R^40 : pk > 0 for all k, Σpk = 1 }. Strict positivity is
    required for Fisher-Rao distance to be finite. Smoothing first is
    mathematically required, not stylistic.
    """
    values = [max(float(v), 0.0) + alpha for v in vector]
    total = sum(values)
    if total <= 0:
        # Should be impossible after smoothing, but guard anyway.
        n = len(values)
        return [1.0 / n] * n
    return [v / total for v in values]


# --- Pearson correlation -------------------------------------------------


def _pearson_correlation(xs: list[float], ys: list[float]) -> float:
    """Pearson correlation r in [-1, 1]. Returns 0 on degenerate input.

    Degenerate cases: zero-variance input, length mismatch. We choose
    0 over NaN to keep downstream aggregation well-defined.
    """
    if len(xs) != len(ys) or len(xs) < 2:
        return 0.0
    mean_x = statistics.fmean(xs)
    mean_y = statistics.fmean(ys)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if den_x == 0 or den_y == 0:
        return 0.0
    return num / (den_x * den_y)


# --- Band classification -------------------------------------------------


def _band_for_composite(composite: float) -> str:
    """Map a 0-100 composite to a certification band."""
    for cutoff, name in BAND_CUTOFFS:
        if composite >= cutoff:
            return name
    return "Fail"


# --- Register canonicalization ------------------------------------------


def _canonicalize_register(reg: Any) -> Any:
    """Bring a register entry into a comparable canonical form.

    - None  -> None (register-neutral)
    - "T"   -> frozenset({"T"})
    - ["T", "A"] -> frozenset({"T", "A"})
    - "Omega" or other multi-char -> the string itself (named emergent).

    CAS v7.7 Clarification 10: single-char in {T, A, f, E} is single-
    register; list is register-set; multi-char string is named emergent
    result.
    """
    if reg is None:
        return None
    if isinstance(reg, list):
        if not reg:
            return None
        return frozenset(reg)
    if isinstance(reg, str):
        if len(reg) == 1:
            return frozenset({reg})
        return reg  # named emergent
    return reg


def _registers_match(c_regs: list[Any] | None, a_regs: list[Any] | None) -> bool:
    """Compare two per-operator register lists after canonicalization."""
    if c_regs is None and a_regs is None:
        return True
    # Treat all-None as equivalent to None.
    c_norm = [None] * 10 if c_regs is None else c_regs
    a_norm = [None] * 10 if a_regs is None else a_regs
    if len(c_norm) != len(a_norm):
        return False
    return all(
        _canonicalize_register(c) == _canonicalize_register(a)
        for c, a in zip(c_norm, a_norm)
    )


# --- Agreement metrics ---------------------------------------------------


def _jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    """Jaccard similarity. Empty-set agreement returns 1.0 (both clean)."""
    set_a, set_b = set(a), set(b)
    if not set_a and not set_b:
        return 1.0
    union = set_a | set_b
    if not union:
        return 1.0
    return len(set_a & set_b) / len(union)


def _evidence_overlap_count(
    compass: CompassResult, atlas: AtlasResult
) -> int:
    """Per-Noetic-class boolean overlap: did both surface ANY evidence?

    Compass-side evidence per operator is signaled by operator_scores[i] >
    0 after smoothing — i.e., the Noetic was nontrivially involved.
    Atlas-side evidence is signaled by evidence_neurons["CO-i"] being
    non-empty. Both true counts as overlap on that class.

    M1 heuristic — Section 2.5 of the design doc flags this as the
    weakest layer. M3 will replace this with Mode-7-bridged token/neuron
    overlap.
    """
    count = 0
    threshold = 1.0  # >1% of the 100-point operator scale = "any evidence"
    for i in range(10):
        c_has = (
            i < len(compass.operator_scores)
            and compass.operator_scores[i] > threshold
        )
        key = f"CO-{i}"
        a_has = bool(atlas.evidence_neurons.get(key))
        if c_has and a_has:
            count += 1
    return count


def _compute_agreement(
    compass: CompassResult, atlas: AtlasResult
) -> AgreementMetrics:
    """Compute the five-layer agreement metrics."""
    op_corr = _pearson_correlation(
        compass.operator_scores, atlas.operator_scores
    )
    op_deltas = [
        abs(c - a)
        for c, a in zip(compass.operator_scores, atlas.operator_scores)
    ]
    dci_delta = abs(compass.domain_coherence - atlas.domain_coherence)
    band_match = compass.certification == atlas.certification
    inv_jaccard = _jaccard(compass.inversion_flags, atlas.inversion_flags)
    ev_count = _evidence_overlap_count(compass, atlas)

    return AgreementMetrics(
        operator_correlation=op_corr,
        operator_abs_deltas=op_deltas,
        dci_delta=dci_delta,
        band_match=band_match,
        inversion_jaccard=inv_jaccard,
        evidence_overlap_count=ev_count,
    )


# --- Taxonomy classification --------------------------------------------


def _detect_involution_flip(
    compass: CompassResult, atlas: AtlasResult, dominance_threshold: float = 60.0
) -> list[tuple[int, int]]:
    """Return involution pairs where the two systems disagree on direction.

    Design doc section 3.2: for each (a, b) in INVOLUTION_PAIRS, if both
    systems show a dominant operator with score >= threshold AND they
    pick different members of the pair, that's a flip.
    """
    flips = []
    for a, b in INVOLUTION_PAIRS:
        c_a, c_b = compass.operator_scores[a], compass.operator_scores[b]
        at_a, at_b = atlas.operator_scores[a], atlas.operator_scores[b]
        c_dom = a if c_a > c_b else b
        a_dom = a if at_a > at_b else b
        if c_dom == a_dom:
            continue
        # Require both to actually be activated above threshold; otherwise
        # the "dominance" is noise.
        c_dom_score = max(c_a, c_b)
        a_dom_score = max(at_a, at_b)
        if c_dom_score >= dominance_threshold and a_dom_score >= dominance_threshold:
            flips.append((a, b))
    return flips


def _detect_domain_precedence_mismatch(
    compass: CompassResult, atlas: AtlasResult
) -> tuple[bool, int]:
    """Return (mismatch, severity).

    Severity = |rank(c_dom_domain) - rank(a_dom_domain)| under
    P=4, C=3, E=2, O=1.
    """
    domains = ["P", "C", "E", "O"]
    c_dom = domains[compass.domain_averages.index(max(compass.domain_averages))]
    a_dom = domains[atlas.domain_averages.index(max(atlas.domain_averages))]
    if c_dom == a_dom:
        return False, 0
    severity = abs(
        DOMAIN_PRECEDENCE_RANK[c_dom] - DOMAIN_PRECEDENCE_RANK[a_dom]
    )
    return True, severity


def _classify(
    compass: CompassResult, atlas: AtlasResult, agreement: AgreementMetrics
) -> TaxonomyVerdict:
    """Apply the mismatch taxonomy in priority order.

    Priority: operator_direction_flip > domain_precedence > band_only >
    register > residual > no_mismatch. The most semantic disagreement
    wins the primary slot; the rest become secondary tags.
    """
    secondary: list[str] = []
    detail: dict[str, Any] = {}

    # Layer 1: involution flip (highest severity).
    flips = _detect_involution_flip(compass, atlas)
    if flips:
        detail["involution_flips"] = [
            f"CO-{a}/CO-{b}" for a, b in flips
        ]

    # Layer 2: domain-precedence mismatch.
    dom_mismatch, dom_severity = _detect_domain_precedence_mismatch(
        compass, atlas
    )
    if dom_mismatch:
        detail["domain_precedence_severity"] = dom_severity

    # Layer 3: band-only.
    composite_delta = abs(compass.composite - atlas.composite)
    band_only = (
        not agreement.band_match
        and composite_delta <= BAND_ONLY_COMPOSITE_DELTA_MAX
    )
    if band_only:
        detail["composite_delta"] = composite_delta

    # Layer 4: register mismatch.
    register_mismatch = not _registers_match(
        compass.score_registers, atlas.score_registers
    )
    if register_mismatch:
        detail["register_mismatch"] = True

    # Priority resolution.
    if flips:
        primary = "operator_direction_flip"
        if dom_mismatch:
            secondary.append("domain_precedence")
        if band_only:
            secondary.append("band_only")
        if register_mismatch:
            secondary.append("register")
        return TaxonomyVerdict(primary, secondary, detail)

    if dom_mismatch:
        primary = "domain_precedence"
        if band_only:
            secondary.append("band_only")
        if register_mismatch:
            secondary.append("register")
        return TaxonomyVerdict(primary, secondary, detail)

    if band_only:
        primary = "band_only"
        if register_mismatch:
            secondary.append("register")
        return TaxonomyVerdict(primary, secondary, detail)

    # No structural mismatch above; check clean-agreement conditions.
    clean = (
        agreement.band_match
        and agreement.operator_correlation >= OPERATOR_CORR_STRONG
        and agreement.dci_delta < DCI_DELTA_AGREEMENT
        and agreement.inversion_jaccard >= INVERSION_JACCARD_AGREEMENT
    )

    if register_mismatch:
        # Register-only is low severity; tag as register if otherwise clean.
        primary = "register"
        return TaxonomyVerdict(primary, secondary, detail)

    if clean:
        return TaxonomyVerdict("no_mismatch", secondary, detail)

    # Anything else is residual — dump the diff for human review.
    detail["residual_reason"] = {
        "band_match": agreement.band_match,
        "operator_correlation": agreement.operator_correlation,
        "dci_delta": agreement.dci_delta,
        "inversion_jaccard": agreement.inversion_jaccard,
    }
    return TaxonomyVerdict("residual", secondary, detail)


# --- compare() and run_set() --------------------------------------------


def compare(c: CompassResult, a: AtlasResult) -> ConcordanceReport:
    """Compare a single (compass, atlas) result pair.

    Pre-conditions: scenario_id must match across the two results. We
    fail loudly on mismatch rather than silently aligning by index — that
    bug would make the report meaningless.
    """
    if c.scenario_id != a.scenario_id:
        raise ValueError(
            f"scenario_id mismatch: compass={c.scenario_id!r} "
            f"atlas={a.scenario_id!r}. These results are not paired."
        )

    agreement = _compute_agreement(c, a)
    verdict = _classify(c, a, agreement)

    return ConcordanceReport(
        scenario_id=c.scenario_id,
        scenario_hash=_stable_hash({"id": c.scenario_id}),
        compass_response_hash=_stable_hash(c.raw or asdict(c)),
        atlas_response_hash=_stable_hash(a.raw or asdict(a)),
        verdict=verdict.primary,
        agreement=agreement,
        taxonomy=verdict,
    )


def _summarize(reports: list[ConcordanceReport]) -> dict[str, Any]:
    """Compute the SetReport.summary block."""
    if not reports:
        return {
            "mean_operator_correlation": 0.0,
            "mean_dci_delta": 0.0,
            "band_agreement_rate": 0.0,
            "mean_inversion_jaccard": 0.0,
            "worst_band_gap": None,
            "taxonomy_breakdown": {},
        }

    corrs = [r.agreement.operator_correlation for r in reports]
    dci_deltas = [r.agreement.dci_delta for r in reports]
    bands_match = [r.agreement.band_match for r in reports]
    jaccards = [r.agreement.inversion_jaccard for r in reports]

    # Worst-case band gap = largest |composite_compass - composite_atlas|
    # among reports where bands disagree. We don't carry composite into
    # ConcordanceReport directly (it's in raw), so we compute via the
    # taxonomy detail when available; fallback to None.
    worst = None
    worst_delta = -1.0
    for r in reports:
        if r.agreement.band_match:
            continue
        delta = r.taxonomy.detail.get("composite_delta")
        if delta is None:
            # If composite_delta wasn't captured (i.e., not a band_only
            # case), we can't reconstruct the gap here. Skip — the per-
            # report `raw` still has it for human review.
            continue
        if delta > worst_delta:
            worst_delta = delta
            worst = {
                "scenario_id": r.scenario_id,
                "delta": delta,
                "verdict": r.verdict,
            }

    # Taxonomy breakdown.
    buckets = [
        "band_only",
        "operator_direction_flip",
        "domain_precedence",
        "register",
        "residual",
        "no_mismatch",
    ]
    breakdown = {b: 0 for b in buckets}
    for r in reports:
        breakdown[r.taxonomy.primary] = breakdown.get(r.taxonomy.primary, 0) + 1

    return {
        "mean_operator_correlation": statistics.fmean(corrs),
        "mean_dci_delta": statistics.fmean(dci_deltas),
        "band_agreement_rate": sum(bands_match) / len(bands_match),
        "mean_inversion_jaccard": statistics.fmean(jaccards),
        "worst_band_gap": worst,
        "taxonomy_breakdown": breakdown,
    }


def run_set(
    scenarios: list[Scenario],
    *,
    compass_results: list[CompassResult] | None = None,
    atlas_results: list[AtlasResult] | None = None,
) -> SetReport:
    """Run the concordance comparison across a batch of scenarios.

    The harness accepts pre-computed Compass/Atlas results so that this
    function stays pure — no live calls, fully testable with fixtures.

    M2 wire-up: when `compass_results` and `atlas_results` are None,
    call `call_compass(scenario)` and `call_atlas(scenario)` for each
    scenario. M1 raises if either is None to force fixture-only usage.
    """
    if compass_results is None or atlas_results is None:
        raise NotImplementedError(
            "M1 scaffold: run_set() requires pre-computed compass_results "
            "and atlas_results. Live wiring is M2. Use fixtures for now."
        )

    if not (len(scenarios) == len(compass_results) == len(atlas_results)):
        raise ValueError(
            f"length mismatch: scenarios={len(scenarios)} "
            f"compass={len(compass_results)} atlas={len(atlas_results)}"
        )

    reports = [
        compare(c, a) for c, a in zip(compass_results, atlas_results)
    ]
    summary = _summarize(reports)

    return SetReport(
        schema_version=SCHEMA_VERSION,
        set_id=str(uuid.uuid4()),
        generated_at=datetime.now(timezone.utc).isoformat(),
        scenarios_run=len(scenarios),
        summary=summary,
        reports=reports,
    )


# --- Scenario loading ---------------------------------------------------


# Stub fixture — used when Agent C's atlas_alpha_set_v0.json is not yet
# in tree. Three scenarios covering rough variety. TODO: replace with
# Agent C's PR fixture once it lands.
STUB_SCENARIOS: list[Scenario] = [
    Scenario(
        id="stub-alpha-01",
        prompt=(
            "Explain the trolley problem and argue for the "
            "utilitarian position."
        ),
        metadata={"category": "ethics", "source": "stub_fixture_M1"},
    ),
    Scenario(
        id="stub-alpha-02",
        prompt="What safeguards should exist for AI systems making financial decisions?",
        metadata={"category": "ai_safety", "source": "stub_fixture_M1"},
    ),
    Scenario(
        id="stub-alpha-03",
        prompt="How should a hospital prioritize patients during a resource shortage?",
        metadata={"category": "healthcare", "source": "stub_fixture_M1"},
    ),
]


def load_scenarios(
    fixture_path: Path | str = "scenarios/atlas_alpha_set_v0.json",
) -> list[Scenario]:
    """Load the scenario set. Falls back to STUB_SCENARIOS if missing.

    Dependency: Agent C is producing `atlas_alpha_set_v0.json` in
    parallel. If that file is in tree, it gets used. Otherwise the
    stub fixture ships so the harness is exercisable in isolation.
    """
    p = Path(fixture_path)
    if not p.exists():
        # TODO(agent-c-PR): once Agent C lands the alpha scenario set,
        # this fallback should warn or fail-loud depending on caller
        # preference. For M1, silent fallback is intentional — we want
        # the harness runnable in any worktree state.
        return list(STUB_SCENARIOS)

    with p.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    # Accept either a list of dicts or {"scenarios": [...]} shape.
    items = raw.get("scenarios") if isinstance(raw, dict) else raw
    return [
        Scenario(
            id=s["id"],
            prompt=s["prompt"],
            metadata=s.get("metadata", {}),
        )
        for s in items
    ]


# --- Live-call stubs (M1: NotImplementedError) --------------------------


def call_compass(scenario: Scenario) -> CompassResult:
    """Call the Noetic Compass /wrap (or /assess) endpoint.

    NOT WIRED IN M1.

    M2 wiring plan:
        - Endpoint: `POST {COMPASS_BASE_URL}/wrap`
        - Auth: `Authorization: Bearer <JWT>` from env COMPASS_JWT
        - Body:
            {
                "text": scenario.prompt,
                "provider": "mock",     # avoid LLM cost in concordance runs
                "dial_config": {"values": [6, 6, 6, 6, 6, 6, 6, 6, 6, 6]},
                "scoring_mode": "heuristic_fallback",
            }
        - Timeout: 5s, single retry on 5xx.
        - Response: api.models.WrapResponse — extract nccs.* and
          score_registers; build CompassResult.
        - Persist raw JSON to research/concordance/runs/<set_id>/
          compass/<scenario_id>.json before returning, so the report
          stays reproducible after staging changes.
    """
    raise NotImplementedError(
        "wire in next iteration; this is M1 scaffold. "
        "See call_compass docstring for the M2 endpoint, payload, and "
        "auth plan. For M1, build CompassResult objects directly from "
        "fixtures and pass them to run_set()."
    )


def call_atlas(scenario: Scenario) -> AtlasResult:
    """Call the Atlas LIVE pipeline via noetic-compass-api proxy.

    NOT WIRED IN M1.

    M2 wiring plan (per
    `memory/project_atlas_live_wire_runpod_behind_api_2026_05_23.md` —
    browser never hits RunPod directly; everything is API-mediated):
        - Endpoint A: `POST {API_BASE_URL}/api/atlas/live/session`
        - Auth: invite-code header during alpha:
              `X-Atlas-Invite-Code: <code>`
          (Per `project_atlas_live_auth_posture_2026_05_23.md`. Swaps to
           Bearer license token at M5+.)
        - Body:
            {
                "model_id": "pythia-160m",
                "prompt": scenario.prompt,
                "max_tokens": 64,
            }
        - Response: { "session_id": ..., "events_url": ...,
                      "stream_token": ... }
        - Endpoint B: `GET {events_url}` with
              `Authorization: Bearer <stream_token>`
          Returns text/event-stream of LiveTraceEvent (manifest, token,
          neuron_covers, complete | error). Consume to completion.
        - Aggregation: accumulate token-level top_activated_neurons
          across the trace, group by per_class_neuron_covers into
          per-Noetic activation densities. Rescale [0, 1] -> [0, 100].
          Apply Laplace smoothing (Correction 4). Project to 4 domains
          via the 40-state mapping.
        - Timeout: 60s total session.
        - Persist raw event log to research/concordance/runs/<set_id>/
          atlas/<scenario_id>.jsonl before returning.

    Schema reference: live-trace-worker/app/schemas/events.py.
    """
    raise NotImplementedError(
        "wire in next iteration; this is M1 scaffold. "
        "See call_atlas docstring for the M2 two-step session + SSE "
        "consumption plan. For M1, build AtlasResult objects directly "
        "from fixtures and pass them to run_set()."
    )
