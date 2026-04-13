"""CAS notation compiler routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.notation.compiler import CAS_GRAMMAR_BNF, CAS_LANGUAGE_NOTES, compile_expression
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
    return artifact.to_dict()


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
