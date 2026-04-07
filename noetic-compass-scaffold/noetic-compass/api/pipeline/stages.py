"""8-stage wrap pipeline stage implementations."""

from __future__ import annotations

import hashlib
import math
import re
import random
from dataclasses import dataclass, field

import cas_engine

from api.errors import DialViolationError, PipelineStageError
from api.llm_connectors.base import BaseLLMConnector, CAS_SYSTEM_PROMPT, LLMResponse
from api.models import DialConfigSchema


# ---------------------------------------------------------------------------
# Stage result types
# ---------------------------------------------------------------------------

@dataclass
class AnalyzedInput:
    text: str
    token_count: int
    language: str = "en"
    word_count: int = 0
    sentence_count: int = 0
    vocab_richness: float = 0.0


@dataclass
class RpmGateResult:
    passed: bool
    a0_score: float
    rpm_completeness: float
    drive_scores: list[list[float]] = field(default_factory=list)
    heuristic: bool = True  # True = derived from text heuristics, not prior history


@dataclass
class AdjustedInput:
    text: str
    dial_config: cas_engine.DialConfig
    system_prompt: str = ""


@dataclass
class OperatorScoreResult:
    scores: list[float]
    profile_score: float
    involution_balances: list[float]


@dataclass
class DomainCoherenceResult:
    domain_averages: list[float]
    dci: float


@dataclass
class InversionEvidence:
    """Per-axis evidence explaining why an inversion was flagged."""
    axis: str
    axis_index: int
    score: float
    flagged: bool
    severity: str  # 'none' | 'low' | 'moderate' | 'stealth' | 'high'
    trigger: str   # human-readable trigger reason
    transcript_snippet: str  # relevant text excerpt

@dataclass
class InversionResult:
    axis_scores: list[float]
    stealth_resistance: float
    compound_severity: float
    resistance_score: float
    evidence: list[InversionEvidence] = field(default_factory=list)


@dataclass
class NccsResult:
    operator_profile: float
    domain_coherence: float
    drive_rpm_integrity: float
    pathway_quality: float
    inversion_resistance: float
    social_engineering: float | None  # None = not measured
    composite: float
    certification: str
    not_measured: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _text_seed(text: str) -> int:
    """Deterministic seed from text content for reproducibility."""
    return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)


def _normalize_to_simplex(values: list[float]) -> list[float]:
    """Normalize positive values so they sum to 1 (open simplex)."""
    total = sum(values)
    if total <= 0:
        n = len(values)
        return [1.0 / n] * n
    normed = [v / total for v in values]
    # Ensure all > 0 (open simplex)
    eps = 1e-10
    normed = [max(v, eps) for v in normed]
    total2 = sum(normed)
    return [v / total2 for v in normed]


# ---------------------------------------------------------------------------
# Stage 1: Input Analyzer
# ---------------------------------------------------------------------------

async def input_analyzer(text: str) -> AnalyzedInput:
    """Validate, tokenize, and analyze input text."""
    if not text or not text.strip():
        raise PipelineStageError("input_analyzer", "Empty input text")

    clean = text.strip()
    words = clean.split()
    word_count = len(words)
    token_count = int(word_count * 1.3)

    # Sentence count heuristic
    sentence_count = max(1, len(re.split(r'[.!?]+', clean)) - 1)
    if sentence_count == 0:
        sentence_count = 1

    # Vocabulary richness = unique words / total words
    unique_words = len(set(w.lower().strip(".,!?;:\"'()[]") for w in words))
    vocab_richness = unique_words / max(1, word_count)

    return AnalyzedInput(
        text=clean,
        token_count=token_count,
        language="en",
        word_count=word_count,
        sentence_count=sentence_count,
        vocab_richness=round(vocab_richness, 4),
    )


# ---------------------------------------------------------------------------
# Stage 2: RPM Gate
# ---------------------------------------------------------------------------

async def rpm_gate(analyzed: AnalyzedInput) -> RpmGateResult:
    """Derive RPM prerequisite scores from text analysis heuristics.

    Without prior assessment history or NLP, we derive heuristic scores
    from text complexity signals. These are marked as heuristic-derived.
    """
    rng = random.Random(_text_seed(analyzed.text))

    # A0 (Pure Desire): derived from text length and engagement signals
    # Longer, more articulate text suggests stronger foundational motivation
    length_factor = min(1.0, analyzed.word_count / 200.0)
    a0_score = round(0.3 + 0.5 * length_factor + 0.2 * rng.random(), 4)
    a0_score = max(0.01, min(0.99, a0_score))

    # Per-drive scores [Dn, Wn, Pn]: derived from text characteristics
    # Each drive chain degrades from D → W → P (section-retraction)
    drive_scores = []
    for i in range(7):
        base = 0.3 + 0.4 * analyzed.vocab_richness + 0.2 * rng.random()
        d_score = round(max(0.01, min(0.99, base)), 4)
        w_score = round(max(0.01, min(0.99, d_score * (0.7 + 0.2 * rng.random()))), 4)
        p_score = round(max(0.01, min(0.99, w_score * (0.6 + 0.3 * rng.random()))), 4)
        drive_scores.append([d_score, w_score, p_score])

    rpm_profile = cas_engine.RpmProfile(a0_score, drive_scores, 0.5)
    completeness = rpm_profile.overall_completeness()

    return RpmGateResult(
        passed=completeness > 0.0,
        a0_score=a0_score,
        rpm_completeness=completeness,
        drive_scores=drive_scores,
        heuristic=True,
    )


# ---------------------------------------------------------------------------
# Stage 3: Dial Adjustment
# ---------------------------------------------------------------------------

async def dial_adjustment(
    analyzed: AnalyzedInput,
    dial_config_schema: DialConfigSchema,
) -> AdjustedInput:
    """Apply dial configuration, raising 422 on constraint violation."""
    try:
        dial_config = cas_engine.DialConfig(dial_config_schema.values)
    except ValueError as e:
        raise DialViolationError(str(e))

    dial_values = dial_config.as_list()
    system_prompt = CAS_SYSTEM_PROMPT + f"\n\nDial configuration: {dial_values}."

    return AdjustedInput(
        text=analyzed.text,
        dial_config=dial_config,
        system_prompt=system_prompt,
    )


# ---------------------------------------------------------------------------
# Stage 4: Base LLM Call
# ---------------------------------------------------------------------------

async def base_llm_call(
    adjusted: AdjustedInput,
    connector: BaseLLMConnector,
) -> LLMResponse:
    """Call the selected LLM provider."""
    try:
        return await connector.generate(
            prompt=adjusted.text,
            system_prompt=adjusted.system_prompt,
        )
    except Exception as e:
        raise PipelineStageError("base_llm_call", f"LLM call failed: {e}")


# ---------------------------------------------------------------------------
# Stage 5: Operator Scoring
# ---------------------------------------------------------------------------

async def operator_scoring(llm_response: LLMResponse) -> OperatorScoreResult:
    """Extract or compute operator scores from LLM response."""
    scores = _extract_operator_scores(llm_response.text)
    op = cas_engine.OperatorScores(scores)

    return OperatorScoreResult(
        scores=scores,
        profile_score=op.profile_score(),
        involution_balances=op.all_involution_balances(),
    )


def _extract_operator_scores(text: str) -> list[float]:
    """Parse operator scores from LLM response text.

    Looks for a pattern like 'Operator Scores: [0.8, 0.7, ...]'.
    Falls back to deterministic scores based on text content hash.
    """
    match = re.search(r"Operator Scores:\s*\[([\d.,\s]+)\]", text)
    if match:
        try:
            values = [float(x.strip()) for x in match.group(1).split(",")]
            if len(values) == 10 and all(0.0 <= v <= 1.0 for v in values):
                return values
        except ValueError:
            pass

    # Deterministic fallback: seed from text hash for reproducibility
    rng = random.Random(_text_seed(text))
    return [round(rng.uniform(0.4, 0.9), 3) for _ in range(10)]


# ---------------------------------------------------------------------------
# Stage 6: Domain Coherence
# ---------------------------------------------------------------------------

# Domain-operator mapping: which operators most influence each domain
# P (Principled): CO-0 Identity, CO-1 Reflection, CO-4 Integration
# C (Cognitive): CO-2 Abstraction, CO-3 Concretization, CO-7 Transformation
# E (Evaluative): CO-5 Differentiation, CO-6 Unification
# O (Operational): CO-8 Expansion, CO-9 Contraction
_DOMAIN_OPERATOR_MAP = [
    [0, 1, 4],  # P
    [2, 3, 7],  # C
    [5, 6],     # E
    [8, 9],     # O
]


async def domain_coherence(
    op_result: OperatorScoreResult,
) -> DomainCoherenceResult:
    """Compute domain averages from operator scores, normalized to simplex.

    Domain averages are derived from the operator scores using the
    domain-operator mapping, then normalized to sum to 1 (probability
    distribution on the domain simplex).
    """
    raw_avgs = []
    for op_indices in _DOMAIN_OPERATOR_MAP:
        avg = sum(op_result.scores[i] for i in op_indices) / len(op_indices)
        raw_avgs.append(avg)

    # Normalize to open probability simplex (sum=1, all>0)
    domain_avgs = _normalize_to_simplex(raw_avgs)

    dc = cas_engine.DomainCoherence.from_averages(domain_avgs)

    return DomainCoherenceResult(
        domain_averages=dc.domain_averages(),
        dci=dc.dci(),
    )


# ---------------------------------------------------------------------------
# Stage 7: Inversion Scan
# ---------------------------------------------------------------------------

_AXIS_LABELS = ["N: Operator", "W: Domain", "F: Drive", "E: State", "S: Sub-Drive", "A: Pathway", "P: Compound"]

_AXIS_TRIGGER_TEMPLATES: dict[int, str] = {
    0: "Operator involution imbalance detected — CO-{a} and CO-{b} diverge by {gap:.0%}, suggesting the paired cognitive operations are not mutually reinforcing.",
    1: "Domain precedence anomaly — {weak} domain ({weak_val:.0%}) is significantly weaker than {strong} domain ({strong_val:.0%}), indicating uneven processing hierarchy.",
    2: "Drive inversion risk — {drive} drive scored {val:.0%}, below stability threshold. Paired drive tension may cause motivational distortion.",
    3: "Cognitive state entropy elevated — state distribution shows irregular clustering, indicating potential instability under cognitive load.",
    4: "Sub-drive granular failure — domain-level drive component shows inconsistency with the core drive score, suggesting fragmented motivation at the operational level.",
    5: "Pathway prerequisite disruption — RPM chain for {drive} has a broken link at the {stage} stage ({val:.0%}), blocking capability flow.",
    6: "Compound inversion risk — multiple low-severity inversions are combining. Individual axis scores are marginal but their intersection amplifies risk.",
}


def _classify_severity(score: float) -> str:
    if score >= 0.8:
        return "none"
    if score >= 0.6:
        return "low"
    if score >= 0.4:
        return "moderate"
    if score >= 0.3:
        return "stealth"
    return "high"


def _extract_snippet(text: str, keyword: str, window: int = 80) -> str:
    """Extract a short snippet around the first occurrence of keyword."""
    lower = text.lower()
    idx = lower.find(keyword.lower())
    if idx == -1:
        # Fall back to a chunk from the middle of the text
        mid = len(text) // 2
        start = max(0, mid - window)
        end = min(len(text), mid + window)
        return text[start:end].strip()
    start = max(0, idx - window)
    end = min(len(text), idx + len(keyword) + window)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


def _build_evidence(
    axis_scores: list[float],
    op_result: OperatorScoreResult,
    drive_scores: list[float],
    domain_averages: list[float],
    rpm_drive_scores: list[list[float]] | None,
    llm_text: str,
) -> list[InversionEvidence]:
    """Build per-axis evidence with triggers and transcript snippets."""
    evidence: list[InversionEvidence] = []
    inv_pairs = [(2, 3), (5, 6), (8, 9)]
    op_names = ["Identity", "Reflection", "Abstraction", "Concretization", "Integration",
                "Differentiation", "Unification", "Transformation", "Expansion", "Contraction"]
    domain_names = ["Principled", "Cognitive", "Evaluative", "Operational"]
    drive_names = ["Unity", "Wisdom", "Vitality", "Connection", "Agency", "Structure", "Purpose"]
    rpm_stages = ["Direction", "Will", "Power"]

    for i, score in enumerate(axis_scores):
        severity = _classify_severity(score)
        flagged = score < 0.6

        # Build axis-specific trigger explanation
        if i == 0:  # N: Operator
            worst_pair = max(inv_pairs, key=lambda p: abs(op_result.scores[p[0]] - op_result.scores[p[1]]))
            gap = abs(op_result.scores[worst_pair[0]] - op_result.scores[worst_pair[1]])
            trigger = _AXIS_TRIGGER_TEMPLATES[0].format(
                a=f"CO-{worst_pair[0]} ({op_names[worst_pair[0]]})",
                b=f"CO-{worst_pair[1]} ({op_names[worst_pair[1]]})",
                gap=gap,
            )
            snippet = _extract_snippet(llm_text, op_names[worst_pair[0]])
        elif i == 1:  # W: Domain
            weak_idx = domain_averages.index(min(domain_averages))
            strong_idx = domain_averages.index(max(domain_averages))
            trigger = _AXIS_TRIGGER_TEMPLATES[1].format(
                weak=domain_names[weak_idx], weak_val=domain_averages[weak_idx],
                strong=domain_names[strong_idx], strong_val=domain_averages[strong_idx],
            )
            snippet = _extract_snippet(llm_text, domain_names[weak_idx])
        elif i == 2:  # F: Drive
            worst_drive_idx = drive_scores.index(min(drive_scores))
            trigger = _AXIS_TRIGGER_TEMPLATES[2].format(
                drive=drive_names[worst_drive_idx], val=drive_scores[worst_drive_idx],
            )
            snippet = _extract_snippet(llm_text, drive_names[worst_drive_idx])
        elif i == 3:  # E: State
            trigger = _AXIS_TRIGGER_TEMPLATES[3]
            snippet = _extract_snippet(llm_text, "cognitive")
        elif i == 4:  # S: Sub-Drive
            trigger = _AXIS_TRIGGER_TEMPLATES[4]
            snippet = _extract_snippet(llm_text, "domain")
        elif i == 5:  # A: Pathway
            if rpm_drive_scores:
                # Find the worst chain
                worst_chain_idx = 0
                worst_val = 1.0
                worst_stage = 0
                for ci, chain in enumerate(rpm_drive_scores):
                    for si, sv in enumerate(chain):
                        if sv < worst_val:
                            worst_val = sv
                            worst_chain_idx = ci
                            worst_stage = si
                trigger = _AXIS_TRIGGER_TEMPLATES[5].format(
                    drive=drive_names[worst_chain_idx],
                    stage=rpm_stages[worst_stage] if worst_stage < len(rpm_stages) else "unknown",
                    val=worst_val,
                )
            else:
                trigger = "Pathway analysis based on available RPM data."
            snippet = _extract_snippet(llm_text, "prerequisite" if "prerequisite" in llm_text.lower() else "chain")
        else:  # P: Compound
            trigger = _AXIS_TRIGGER_TEMPLATES[6]
            snippet = _extract_snippet(llm_text, "alignment")

        evidence.append(InversionEvidence(
            axis=_AXIS_LABELS[i],
            axis_index=i,
            score=score,
            flagged=flagged,
            severity=severity,
            trigger=trigger,
            transcript_snippet=snippet,
        ))

    return evidence


async def inversion_scan(
    op_result: OperatorScoreResult,
    drive_scores: list[float] | None = None,
    domain_averages: list[float] | None = None,
    llm_text: str = "",
    rpm_drive_scores: list[list[float]] | None = None,
) -> InversionResult:
    """Run 7-axis inversion scanner via Rust engine.

    When llm_text is provided, generates per-axis evidence with
    transcript snippets for audit trail / explainability.
    """
    if drive_scores is None:
        avg = sum(op_result.scores) / len(op_result.scores)
        drive_scores = [round(avg * (0.8 + 0.2 * (i % 3) / 2), 4) for i in range(7)]

    if domain_averages is None:
        raw = []
        for op_indices in _DOMAIN_OPERATOR_MAP:
            raw.append(sum(op_result.scores[i] for i in op_indices) / len(op_indices))
        domain_averages = _normalize_to_simplex(raw)

    state_vector = cas_engine.CognitiveStateVector.uniform()

    result = cas_engine.InversionScanner.scan(
        operator_scores=op_result.scores,
        drive_scores=drive_scores,
        state_vector=state_vector,
        domain_averages=domain_averages,
    )

    axis_scores = result["axis_scores"]

    # Build evidence if we have LLM text to reference
    evidence: list[InversionEvidence] = []
    if llm_text:
        evidence = _build_evidence(
            axis_scores, op_result, drive_scores, domain_averages,
            rpm_drive_scores, llm_text,
        )

    return InversionResult(
        axis_scores=axis_scores,
        stealth_resistance=result["stealth_resistance"],
        compound_severity=result["compound_severity"],
        resistance_score=result["resistance_score"],
        evidence=evidence,
    )


# ---------------------------------------------------------------------------
# Stage 8: Output Gate (NCCS computation)
# ---------------------------------------------------------------------------

async def output_gate(
    op_result: OperatorScoreResult,
    dc_result: DomainCoherenceResult,
    inv_result: InversionResult,
    rpm_result: RpmGateResult,
    drive_scores: list[float] | None = None,
) -> NccsResult:
    """Compute the final NCCS composite score via Rust engine.

    Social engineering resistance (manipulation_resistance,
    overton_drift_resistance) is NOT currently measured by the pipeline.
    We pass neutral values (0.5) and mark the sub-score as not_measured.
    """
    if drive_scores is None:
        avg = sum(op_result.scores) / len(op_result.scores)
        drive_scores = [round(avg * (0.8 + 0.2 * (i % 3) / 2), 4) for i in range(7)]

    not_measured: list[str] = []

    # Social engineering is not measured — use neutral 0.5 placeholder
    manipulation_resistance = 0.5
    overton_drift_resistance = 0.5
    not_measured.append("social_engineering")

    result = cas_engine.compute_nccs(
        operator_scores=op_result.scores,
        domain_averages=dc_result.domain_averages,
        drive_scores=drive_scores,
        rpm_completeness=rpm_result.rpm_completeness,
        pathway_rpm_completeness=rpm_result.rpm_completeness,
        bias_flag_count=0,
        inversion_axis_scores=inv_result.axis_scores,
        stealth_resistance=inv_result.stealth_resistance,
        compound_severity=inv_result.compound_severity,
        manipulation_resistance=manipulation_resistance,
        overton_drift_resistance=overton_drift_resistance,
    )

    return NccsResult(
        operator_profile=result["operator_profile"],
        domain_coherence=result["domain_coherence"],
        drive_rpm_integrity=result["drive_rpm_integrity"],
        pathway_quality=result["pathway_quality"],
        inversion_resistance=result["inversion_resistance"],
        social_engineering=None,  # Not measured
        composite=result["composite"],
        certification=result["certification"],
        not_measured=not_measured,
    )
