"""Compilability-based task routing for CAS-Native NL generation.

Routing valid-vs-invalid CAS expressions is a structural property of
the expression, not a learned semantic one. This module routes based
on the compiler's verdict:

  - If ``compile_expression(source)`` succeeds → ``cas_to_english``
  - If it raises ``CompilerError``                → ``invalid_to_explanation``

This bypasses the learned task-discrimination ambiguity documented in
``docs/working/identifier_repair_and_rpm_routing_2026_05_09.md``: with
the cas_prefix_mask fix in place, the discrete CAS prefix dominates
decoder conditioning, and the encoder/bottleneck-z signal that used
to carry wrapper-text differences becomes negligible. As a result the
model misroutes valid ``rpm_chain`` prompts to ``invalid_to_explanation``
because ``let X = ...; X -> Y`` shapes are shared between the two
families and the more-abundant invalid family wins.

The compiler is the right authority for this decision. It does NOT
require retraining and produces deterministic, audit-friendly routing.

This module is a library — it does NOT call the model. Callers compose
``route_by_compilability(source) → RoutingDecision``, choose the
appropriate prompt template, then invoke ``generate_reply``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from api.notation import compile_expression
from api.notation.compiler import CompilerError  # imported for type docs / future use


# Maps compiler-error message prefixes (which carry the failing
# CompilerStage value) to the error_class labels used in the Path D
# invalid_to_explanation training prompts. The compile_expression
# function returns CompilationArtifact.error as a string of the form
# "<stage>: <message>" or "<stage>@<position>: <message>".
_STAGE_PREFIX_TO_ERROR_CLASS = {
    "lexing": "parse",
    "parsing": "parse",
    "typecheck": "admissibility",
    "execution": "rpm",
}


def _parse_error_string(error: str) -> tuple[str | None, str | None]:
    """Parse the CompilationArtifact.error string back into (stage, position).

    Format observed in compiler.py CompilerError.__init__:
        "<stage_value>" or "<stage_value>@<position>"  followed by ": <message>".
    Returns (stage_lowercase, position_or_None). On parse failure, returns
    (None, None) and callers fall back to a generic error_class.
    """
    if not error:
        return None, None
    head, _, _ = error.partition(": ")
    stage_part, _, pos_part = head.partition("@")
    stage = stage_part.strip().lower() if stage_part else None
    pos = None
    if pos_part:
        try:
            pos = int(pos_part)
        except ValueError:
            pos = None
    return stage, pos


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

@dataclass
class RoutingDecision:
    """Verdict from the compilability gate.

    ``task_type`` is one of ``"cas_to_english"`` (compiled cleanly) or
    ``"invalid_to_explanation"`` (compilation failed). The remaining
    fields carry compiler diagnostics so callers can render the same
    ``Invalid CAS expression (error class: X) ... Compiler error
    message: ...`` shell the training corpus uses.
    """
    task_type: str
    compiled: bool
    error_stage: Optional[str] = None
    error_class: Optional[str] = None
    error_message: Optional[str] = None
    error_position: Optional[int] = None

    def to_dict(self) -> dict[str, object]:
        return {
            "task_type": self.task_type,
            "compiled": self.compiled,
            "error_stage": self.error_stage,
            "error_class": self.error_class,
            "error_message": self.error_message,
            "error_position": self.error_position,
        }


def _stage_to_error_class(stage_name: str | None) -> str:
    """Map a lowercase compiler-stage name to the error_class label
    used in Path D invalid_to_explanation training prompts."""
    if stage_name is None:
        return "unknown"
    key = stage_name.lower()
    return _STAGE_PREFIX_TO_ERROR_CLASS.get(key, key)


# ---------------------------------------------------------------------------
# Routing entry point
# ---------------------------------------------------------------------------

def route_by_compilability(source_cas: str) -> RoutingDecision:
    """Route to the appropriate task by checking the compiler's verdict.

    ``compile_expression`` returns a :class:`CompilationArtifact` with
    ``valid: bool`` and ``error: str | None`` rather than raising on
    invalid input — so we route off the artifact, not exceptions. On
    success returns ``compiled=True`` and ``task_type="cas_to_english"``.
    On failure returns ``compiled=False``, ``task_type=
    "invalid_to_explanation"``, and the compiler's stage / message /
    position so callers can construct a Path-D-shaped invalid prompt:

        Invalid CAS expression (error class: <error_class>):

            <source_cas>

        Compiler error message:

            <error_message>

    Defensive: any unexpected exception from the compiler is also
    treated as an invalid routing with a generic error_class.
    """
    try:
        artifact = compile_expression(source_cas)
    except (ValueError, RuntimeError) as e:
        # Should not happen — compile_expression catches internally.
        # Defensive fallback for compiler bugs / interpreter shifts.
        return RoutingDecision(
            task_type="invalid_to_explanation",
            compiled=False,
            error_stage=None,
            error_class="unknown",
            error_message=str(e),
            error_position=None,
        )

    if artifact.valid:
        return RoutingDecision(task_type="cas_to_english", compiled=True)

    error_str = artifact.error or "compilation failed"
    stage, position = _parse_error_string(error_str)
    return RoutingDecision(
        task_type="invalid_to_explanation",
        compiled=False,
        error_stage=stage.upper() if stage else None,
        error_class=_stage_to_error_class(stage),
        error_message=error_str,
        error_position=position,
    )


# ---------------------------------------------------------------------------
# Prompt construction matching the Path D training-corpus wrapper format
# ---------------------------------------------------------------------------

_CAS_TO_ENGLISH_PROMPT = (
    "Describe the following CAS expression in plain English:\n\n{cas}"
)

_INVALID_PROMPT = (
    "Explain in plain English why the following CAS expression is invalid:\n\n"
    "Invalid CAS expression (error class: {error_class}):\n\n"
    "    {cas}\n\n"
    "Compiler error message:\n\n"
    "    {error_message}"
)


def build_prompt_from_routing(
    *,
    source_cas: str,
    routing: RoutingDecision,
) -> str:
    """Build the prompt_text matching the Path D corpus wrapper for the
    routed task. The same wrapper that was used at training time is
    reproduced here so the encoder sees a familiar shape."""
    if routing.compiled:
        return _CAS_TO_ENGLISH_PROMPT.format(cas=source_cas)
    return _INVALID_PROMPT.format(
        cas=source_cas,
        error_class=routing.error_class or "unknown",
        error_message=routing.error_message or "compilation failed",
    )


__all__ = [
    "RoutingDecision",
    "route_by_compilability",
    "build_prompt_from_routing",
]
