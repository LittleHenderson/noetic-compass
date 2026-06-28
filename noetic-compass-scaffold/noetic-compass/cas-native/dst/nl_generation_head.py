"""Natural-language generation head for the Phase 2 DST.

Takes a CAS state and a TurnType and produces an NL response. This is a
**stub** at the scaffold stage:

  - For ANSWER / MIRROR turns, defer to the existing CAS renderer in
    ``cas_native.inference.cas_renderer.render_cas_prediction`` when it
    is available; fall back to a templated description otherwise.
  - For CAS-neutral turn types (CLARIFY, EMPATHIZE, ACK, REFUSE, CLOSE)
    use canned templates.
  - For REFUSE_CLAIM, combine a templated lead-in with the renderer.
  - For PLAN, produce a templated pathway prompt (the real PLAN logic
    requires the RPM scanner; that wiring is follow-on).

The interface is intentionally narrow: a single ``generate`` function
that takes a ``GenerationRequest`` and returns a ``GenerationResult``.
The follow-on session swaps the implementation for a learned NL head
(or a Claude API call) without changing the call sites.

Design constraints:
  - stdlib only.
  - Idempotent: same input -> same output.
  - No I/O. No side effects.
  - Soft-imports the CAS renderer (it pulls in torch); if unavailable,
    use the bundled templates.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .dialog_grammar import TurnType


# ---------------------------------------------------------------------------
# Request / result types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GenerationRequest:
    """Input to the NL generation head."""

    turn_type: TurnType
    cas_state: str = ""                 # the CAS expression, if any
    user_text: str = ""                 # most-recent user utterance, for grounding
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GenerationResult:
    """Output of the NL generation head."""

    text: str
    template_used: str                  # which template / branch produced this
    cas_state: str = ""                 # echoed for caller's convenience
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Templates for CAS-neutral turn types
# ---------------------------------------------------------------------------

# These templates honour the authoritative Noetic verbs ("affinity for",
# "attracted toward", "adverse to", "repelled by", "resonates with") in
# the templates that DO mention the CAS state. CAS-neutral templates are
# plain conversational English.

_TEMPLATES: dict[TurnType, tuple[str, ...]] = {
    TurnType.ACK: (
        "Got it.",
        "Okay.",
        "Hearing you.",
    ),
    TurnType.CLARIFY: (
        "Walk it back -- what's closer to your felt sense?",
        "Can you say a little more about which part of that lands hardest?",
        "Help me anchor this: is the pull more toward what's right, or what feels right?",
    ),
    TurnType.EMPATHIZE: (
        "That sounds like a lot.",
        "I hear you. Take your time.",
        "Yeah, that's heavy.",
    ),
    TurnType.REFUSE: (
        "I can't take that turn -- it would break the admissibility of the dialog. "
        "Can we step back and try a different angle?",
    ),
    TurnType.CLOSE: (
        "Thanks for walking through that.",
        "Take care.",
    ),
    TurnType.OPEN: (
        # Engine never emits OPEN, but defining a template keeps the
        # mapping total.
        "(opening)",
    ),
    TurnType.REPAIR: (
        # Engine never emits REPAIR (it's a user-side turn), but the NL
        # head defines a defensive template so the mapping is total.
        "(user repair)",
    ),
}


# ---------------------------------------------------------------------------
# CAS renderer integration
# ---------------------------------------------------------------------------

# Cache the renderer lookup result: import succeeded -> the function;
# import failed -> a sentinel ``False``.
_RENDERER_CACHE: Optional[Callable[..., str] | bool] = None


def _try_load_renderer() -> Optional[Callable[..., str]]:
    """Try to import the CAS renderer; return None if unavailable.

    The renderer in ``cas_native.inference.cas_renderer`` provides
    ``render_cas_prediction(prediction_dict) -> str``. It pulls in
    PyTorch via the model labels module, so we soft-import it and fall
    back to templates if the environment is torch-free.
    """
    global _RENDERER_CACHE
    if _RENDERER_CACHE is False:
        return None
    if _RENDERER_CACHE is not None and not isinstance(_RENDERER_CACHE, bool):
        return _RENDERER_CACHE  # type: ignore[return-value]

    try:
        mod = importlib.import_module("cas_native.inference.cas_renderer")
        fn = getattr(mod, "render_cas_prediction", None)
        if callable(fn):
            _RENDERER_CACHE = fn
            return fn
    except Exception:
        pass
    _RENDERER_CACHE = False
    return None


def _format_cas_state_inline(cas_state: str) -> str:
    """Return a brief inline description of a CAS expression for templated text.

    This is a *fallback* renderer used when the full CAS renderer is not
    importable (e.g. torch is unavailable in the test environment). It
    produces something like ``"^3^E|f"`` -> ``"the CAS state ^3^E|f
    (Negative, evaluative, felt register)"``. It is intentionally
    *minimal* -- the real renderer in ``cas_native.inference.cas_renderer``
    is far more polished. The follow-on session can drop this fallback
    once torch availability in the test loop is guaranteed.
    """
    s = (cas_state or "").strip()
    if not s:
        return "(no CAS commitment yet)"
    return f"the CAS state {s}"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate(req: GenerationRequest) -> GenerationResult:
    """Produce an NL response for ``req``.

    Dispatches by turn type:
      ANSWER / MIRROR / REFUSE_CLAIM -> CAS-grounded body via renderer or
                                         fallback.
      PLAN                            -> templated pathway prompt
                                         referencing the current CAS state.
      ACK / CLARIFY / EMPATHIZE
      / REFUSE / CLOSE / OPEN         -> canned template.
    """
    tt = req.turn_type

    if tt in (TurnType.ANSWER, TurnType.MIRROR):
        return _generate_cas_body(req, lead_in=_lead_in_for(tt))

    if tt == TurnType.REFUSE_CLAIM:
        return _generate_cas_body(req, lead_in=(
            "I don't think the structure you're proposing fits. The closer "
            "reading I'd stand behind is "
        ))

    if tt == TurnType.PLAN:
        # Templated pathway prompt over the current state. The real
        # PLAN renderer requires the RPM scanner and the 22 capability
        # pathways; that's follow-on work.
        body = _format_cas_state_inline(req.cas_state)
        text = (
            f"Given {body}, the next step on the pathway would be to "
            f"strengthen the prerequisite that's currently weakest. "
            f"Want to walk through the chain?"
        )
        return GenerationResult(
            text=text,
            template_used="plan_pathway_v0",
            cas_state=req.cas_state,
        )

    # Canned templates for CAS-neutral types.
    if tt in _TEMPLATES:
        text = _TEMPLATES[tt][0]
        return GenerationResult(
            text=text,
            template_used=f"canned_{tt.value.lower()}",
            cas_state=req.cas_state,
        )

    raise ValueError(f"no NL generator branch for turn type {tt!r}")


def _lead_in_for(tt: TurnType) -> str:
    return {
        TurnType.MIRROR: "If I'm hearing you, the structural reading is ",
        TurnType.ANSWER: "The reading I'd stand behind is ",
    }.get(tt, "")


def _generate_cas_body(req: GenerationRequest, *, lead_in: str) -> GenerationResult:
    """Render a CAS-grounded body using the renderer if available, else fallback."""
    renderer = _try_load_renderer()
    if renderer is not None:
        # The real renderer expects a prediction dict, not a CAS string.
        # When the engine has the dict it should pass it via metadata;
        # otherwise we fall back to the inline formatter.
        prediction = req.metadata.get("prediction")
        if isinstance(prediction, dict):
            try:
                rendered = renderer(prediction)
                text = f"{lead_in}{rendered}".strip()
                return GenerationResult(
                    text=text,
                    template_used="cas_renderer",
                    cas_state=req.cas_state,
                )
            except Exception:
                pass

    # Fallback: build directly from the CAS state string.
    body = _format_cas_state_inline(req.cas_state)
    text = f"{lead_in}{body}.".strip()
    return GenerationResult(
        text=text,
        template_used="inline_fallback",
        cas_state=req.cas_state,
    )


# ---------------------------------------------------------------------------
# Callable shim (so ConversationEngine can take a simple function reference)
# ---------------------------------------------------------------------------

def default_nl_head() -> Callable[[GenerationRequest], GenerationResult]:
    """Return the default NL generation function.

    Wrapping the function this way lets the engine accept any callable
    with the same signature. The follow-on session can replace this
    with a learned head or a Claude API call.
    """
    return generate


__all__ = [
    "GenerationRequest",
    "GenerationResult",
    "generate",
    "default_nl_head",
]
