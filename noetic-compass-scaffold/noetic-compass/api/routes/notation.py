"""CAS notation compiler routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.notation.compiler import (
    CAS_GRAMMAR_BNF, CAS_LANGUAGE_NOTES, compile_expression,
    OPERATOR_NAMES, DOMAIN_NAMES, DRIVE_NAMES,
)
from api.pipeline.text_signal_analyzer import analyze_text_signals
from api.pipeline.notation_synthesizer import synthesize_notation

router = APIRouter(prefix="/notation", tags=["notation"])


class NotationCompileRequest(BaseModel):
    expression: str = Field(min_length=1, max_length=5000)


class TextAnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000)


@router.get("/grammar")
def notation_grammar() -> dict:
    return {"grammar": CAS_GRAMMAR_BNF, "notes": CAS_LANGUAGE_NOTES}


@router.post("/compile")
def compile_notation(req: NotationCompileRequest) -> dict:
    artifact = compile_expression(req.expression)
    if not artifact.valid:
        raise HTTPException(status_code=422, detail=artifact.error)
    payload = artifact.to_dict()
    payload["diagram"] = artifact.diagram()
    return payload


@router.post("/analyze")
def analyze_text_to_notation(req: TextAnalyzeRequest) -> dict:
    """Analyze raw text and return a compiler-validated CAS notation in real-time.

    This is the live endpoint — called as the user types, with debouncing on
    the client side.  It extracts CAS signals from the text (operators, domains,
    drives), feeds them through the notation synthesizer, and validates through
    the compiler.  No LLM call needed — runs in <50ms.
    """
    signals = analyze_text_signals(req.text)

    # Convert flat drive scores to chain format [D, W, P] for the synthesizer.
    # Without a full LLM assessment we approximate: D = signal strength,
    # W and P degrade from D (section-retraction semantics).
    drive_chains = []
    for score in signals.drive_scores:
        d = score
        w = round(d * 0.8, 4)
        p = round(w * 0.7, 4)
        drive_chains.append([d, w, p])

    result = synthesize_notation(
        operator_scores=[s / 10.0 for s in signals.operator_scores],
        raw_scores_0_to_10=signals.operator_scores,
        domain_averages=signals.domain_scores,
        drive_chains=drive_chains,
        a0_score=min(1.0, signals.word_count / 100.0),
        rpm_completeness=signals.rpm_signal,
        inversion_axis_scores=[0.8] * 7,  # no inversion data from text alone
        fractal_sequence=None,
        fractal_classification=None,
    )

    return {
        "source": result.source,
        "valid": result.valid,
        "english": result.english,
        "provenance": result.provenance,
        "signals": {
            "operator_scores": signals.operator_scores,
            "domain_scores": signals.domain_scores,
            "drive_scores": signals.drive_scores,
            "rpm_signal": signals.rpm_signal,
            "word_count": signals.word_count,
        },
    }


class NaturalLanguageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=50000)
    compile: bool = True


def _build_interpretation(
    operator_scores: list[float],
    domain_scores: list[float],
    drive_scores: list[float],
    notation_source: str,
    notation_valid: bool,
) -> str:
    """Build a plain-English interpretation of the cognitive analysis."""
    parts: list[str] = []

    # Find dominant operators
    top_ops = sorted(
        [(i, s) for i, s in enumerate(operator_scores) if s >= 5.0],
        key=lambda x: -x[1],
    )[:3]
    if top_ops:
        op_names = [f"{OPERATOR_NAMES[i]} (CO-{i})" for i, _ in top_ops]
        parts.append(f"Dominant cognitive operations: {', '.join(op_names)}.")

    # Domain emphasis
    dom_codes = ["P", "C", "E", "O"]
    dom_labels = {0: "Principled", 1: "Cognitive", 2: "Evaluative", 3: "Operational"}
    top_doms = sorted(
        [(i, s) for i, s in enumerate(domain_scores) if s > 0.3],
        key=lambda x: -x[1],
    )[:2]
    if top_doms:
        dom_names = [dom_labels[i] for i, _ in top_doms]
        parts.append(f"Processing emphasis in the {' and '.join(dom_names)} {'Domains' if len(dom_names) > 1 else 'Domain'}.")

    # Active drives
    drive_labels = ["Unity", "Wisdom", "Vitality", "Connection", "Agency", "Structure", "Purpose"]
    top_drives = sorted(
        [(i, s) for i, s in enumerate(drive_scores) if s > 0.2],
        key=lambda x: -x[1],
    )[:2]
    if top_drives:
        drv_names = [f"F{i+1} {drive_labels[i]}" for i, _ in top_drives]
        parts.append(f"Active drives: {', '.join(drv_names)}.")

    if notation_valid:
        parts.append("The compiled expression is admissible under CAS v7.4 axioms.")
    elif notation_source:
        parts.append("The notation was generated but could not be fully compiled.")

    return " ".join(parts) if parts else "Insufficient cognitive signal detected in the input text."


@router.post("/natural-language")
def natural_language_pipeline(req: NaturalLanguageRequest) -> dict:
    """Full CAS pipeline: text in, cognitive architecture out.

    1. Signal Analyzer extracts operator, domain, drive scores from text
    2. Synthesizer builds CAS notation from the scores
    3. Compiler validates, type-checks, generates bytecode, executes
    4. Interpretation describes the result in plain English

    Accepts any English text: sentences, paragraphs, questions, quotes,
    song lyrics, AI responses. The signal analyzer extracts cognitive
    structure from ANY text.
    """
    # 1. Signal extraction
    signals = analyze_text_signals(req.text)

    # 2. Synthesis
    drive_chains = []
    for score in signals.drive_scores:
        d = score
        w = round(d * 0.8, 4)
        p = round(w * 0.7, 4)
        drive_chains.append([d, w, p])

    synth = synthesize_notation(
        operator_scores=[s / 10.0 for s in signals.operator_scores],
        raw_scores_0_to_10=signals.operator_scores,
        domain_averages=signals.domain_scores,
        drive_chains=drive_chains,
        a0_score=min(1.0, signals.word_count / 100.0),
        rpm_completeness=signals.rpm_signal,
        inversion_axis_scores=[0.8] * 7,
        fractal_sequence=None,
        fractal_classification=None,
    )

    # 3. Compilation (optional but default)
    compilation = None
    if req.compile and synth.source:
        artifact = compile_expression(synth.source)
        compilation = {
            "valid": artifact.valid,
            "error": artifact.error,
            "engine": artifact.engine,
            "tokens": len(artifact.tokens),
            "bytecode": len(artifact.bytecode),
            "warnings": artifact.warnings,
            "ast": artifact.to_dict().get("ast") if artifact.valid else None,
            "result": artifact.to_dict().get("result") if artifact.valid else None,
            "diagram": artifact.diagram() if artifact.valid else None,
        }

    # 4. Interpretation
    interpretation = _build_interpretation(
        signals.operator_scores,
        signals.domain_scores,
        signals.drive_scores,
        synth.source,
        compilation["valid"] if compilation else False,
    )

    return {
        "text": req.text[:200],
        "signals": {
            "operator_scores": signals.operator_scores,
            "domain_scores": signals.domain_scores,
            "drive_scores": signals.drive_scores,
            "rpm_signal": signals.rpm_signal,
            "word_count": signals.word_count,
        },
        "synthesized_notation": synth.source,
        "notation_english": synth.english,
        "compilation": compilation,
        "interpretation": interpretation,
    }
