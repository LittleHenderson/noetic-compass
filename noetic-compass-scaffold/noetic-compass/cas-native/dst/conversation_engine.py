"""Top-level orchestrator for the Phase 2 multi-turn conversation engine.

The ``ConversationEngine`` glues together:

  1. The dialog grammar (admissibility relation over TurnType).
  2. The state tracker (DialogState evolution).
  3. The repair-strategy selector and applier.
  4. A predictor callable that proposes a CAS expression for a given
     user utterance + dialog context.
  5. An NL generation head that turns a (CAS state, turn type) pair into
     user-facing text.

At the scaffold stage, the predictor and the NL head are stubs.
``DefaultStubPredictor`` returns a deterministic CAS expression based on
a tiny rule table; the NL head defers to ``nl_generation_head.generate``.
The follow-on session wires a real CAS-Native predictor and a learned NL
head without changing this orchestrator.

Mathematical posture:
  Per Correction 1 (admissibility), every turn-type transition is gated
  by ``is_admissible`` before emission. Per Correction 2 (RPM is
  section-retraction), repair walk-back is value-restoration from the
  walk-back stack, not inverse computation.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .dialog_grammar import (
    ADMISSIBILITY,
    CAS_LOAD_BEARING,
    TurnType,
    is_admissible,
)
from .nl_generation_head import (
    GenerationRequest,
    GenerationResult,
    default_nl_head,
    generate as default_generate,
)
from .repair_strategies import (
    RESET_AFTER_REPAIRS,
    RepairStrategy,
    apply_repair,
    derive_followup_turn_type,
    select_repair_strategy,
)
from .state_tracker import (
    DialogState,
    Turn,
    apply_turn,
    compress_history,
    detect_repair,
    initial_state,
    make_turn,
)


# ---------------------------------------------------------------------------
# Predictor protocol + default stub
# ---------------------------------------------------------------------------

# A predictor is a callable that takes (user_text, state) and returns a
# dict like {"cas_state": "<expression>", "transition": "...",
# "confidence": 0.0-1.0, ...}. The ConversationEngine accepts any
# callable with this signature; nothing else about the predictor's
# implementation is observable.

PredictorFn = Callable[[str, DialogState], dict[str, Any]]
NLHeadFn = Callable[[GenerationRequest], GenerationResult]


@dataclass
class DefaultStubPredictor:
    """Deterministic stub predictor for the scaffold smoke tests.

    Looks at trigger words in the user text and returns a canned CAS
    expression. NOT a real predictor -- the smoke tests just need
    something that returns sensibly-shaped output. The follow-on
    session replaces this with the real CAS-Native predictor.
    """

    default_state: str = "^4^E|f"        # Vibration / evaluative / felt -- safe default
    default_confidence: float = 0.4

    # Tiny lexicon -> CAS expression. Mirrors a fragment of the
    # rewrite_shim's pattern set, deliberately undersized.
    _RULES: tuple[tuple[str, str, str], ...] = field(
        default_factory=lambda: (
            ("can't stand", "^3^E|f", "visceral aversion"),
            ("can't stomach", "^3^E|f", "visceral aversion"),
            ("rubs me the wrong way", "^3^E|f", "visceral aversion"),
            ("love", "^2^E|f", "felt attraction"),
            ("drawn to", "^2^E|f", "felt attraction"),
            ("struck a chord", "^4^E|f", "resonance / impression"),
            ("popped into my head", "^9^C|A", "Idea brought to Mind"),
            ("breaking it down", "^6^C|A", "compositional decomposition"),
            ("practice makes perfect", "^7^O|E", "rhythmic entrainment"),
            ("reminds me", "^8^C|A", "associative triggering"),
            ("who I am", "^5^P|T", "accumulated experience"),
        ),
    )

    def __call__(self, user_text: str, state: DialogState) -> dict[str, Any]:
        text = (user_text or "").lower()
        for trigger, cas_expr, transition in self._RULES:
            if trigger in text:
                return {
                    "cas_state": cas_expr,
                    "transition": transition,
                    "confidence": 0.85,
                    "source": "stub_lexicon",
                }
        return {
            "cas_state": self.default_state,
            "transition": "default fallback (no clear signal)",
            "confidence": self.default_confidence,
            "source": "stub_default",
        }


# ---------------------------------------------------------------------------
# Engine response container
# ---------------------------------------------------------------------------

@dataclass
class EngineStep:
    """The result of a single ``ConversationEngine.respond`` call.

    Carries the full bookkeeping so callers (chat UI, logging,
    scheduler) can introspect what happened on this turn.
    """

    user_turn: Turn
    assistant_turn: Turn
    state: DialogState
    repair_strategy: Optional[RepairStrategy] = None
    predictor_output: Optional[dict[str, Any]] = None
    nl_result: Optional[GenerationResult] = None
    elapsed_ms: float = 0.0


# ---------------------------------------------------------------------------
# ConversationEngine
# ---------------------------------------------------------------------------

class ConversationEngine:
    """Top-level orchestrator.

    Each call to ``respond(user_text, state)`` does:

      1. Classify the user turn (OPEN, REPAIR, or generic continuation).
      2. Append the user turn to ``state``.
      3. If REPAIR: select + apply a repair strategy; pick a follow-up
         assistant turn type from the strategy.
      4. Else: run the predictor on the user text + state; pick an
         assistant turn type from the admissibility set (defaulting to
         ANSWER if the predictor's confidence is high, MIRROR otherwise).
      5. Generate the assistant NL response via the NL head.
      6. Append the assistant turn to ``state``.
      7. Return the full ``EngineStep``.

    The engine is **deterministic** when the predictor and NL head are
    deterministic. This matters for the smoke tests.

    Constructor args:
      predictor       -- callable matching ``PredictorFn``. If None,
                         uses ``DefaultStubPredictor()``.
      nl_head         -- callable matching ``NLHeadFn``. If None, uses
                         ``nl_generation_head.generate``.
      max_repairs     -- after this many repairs, RESET fires.
      max_history     -- compress turn history above this length.
      confidence_floor -- predictor confidence below which the engine
                         emits MIRROR (echo and ask) rather than ANSWER
                         (commit).
    """

    def __init__(
        self,
        predictor: Optional[PredictorFn] = None,
        nl_head: Optional[NLHeadFn] = None,
        *,
        max_repairs: int = RESET_AFTER_REPAIRS,
        max_history: int = 20,
        confidence_floor: float = 0.7,
    ) -> None:
        self.predictor: PredictorFn = predictor if predictor is not None else DefaultStubPredictor()
        self.nl_head: NLHeadFn = nl_head if nl_head is not None else default_generate
        self.max_repairs = max_repairs
        self.max_history = max_history
        self.confidence_floor = confidence_floor

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def respond(
        self,
        user_text: str,
        state: Optional[DialogState] = None,
    ) -> EngineStep:
        """Process ``user_text`` and produce one assistant response.

        ``state`` defaults to a fresh ``initial_state()`` when omitted.
        Returns an ``EngineStep`` carrying the user turn, the assistant
        turn, and the new state. Callers should pass the returned
        ``state`` back in on the next call.
        """
        t0 = time.time()
        if state is None:
            state = initial_state()

        # Step 1: classify user turn.
        user_turn_type = self._classify_user_turn(state, user_text)

        # Step 2: append user turn.
        user_turn = make_turn(role="user", text=user_text, turn_type=user_turn_type)
        state = apply_turn(state, user_turn)

        # Step 3 + 4 + 5: branch on repair vs not. If the user has
        # CLOSEd the conversation, emit a quiet assistant CLOSE that
        # bypasses admissibility (CLOSE is terminal so its admissibility
        # set is empty).
        if user_turn_type == TurnType.CLOSE:
            assistant_turn, state, predictor_output, nl_result = self._handle_close(
                state, user_text
            )
            repair_strategy = None
        elif user_turn_type == TurnType.REPAIR:
            assistant_turn, state, repair_strategy, predictor_output, nl_result = (
                self._handle_repair(state, user_text)
            )
        else:
            assistant_turn, state, predictor_output, nl_result = self._handle_normal_turn(
                state, user_text
            )
            repair_strategy = None

        # Step 6: compress history if needed.
        state = compress_history(state, max_turns=self.max_history)

        elapsed_ms = (time.time() - t0) * 1000.0
        return EngineStep(
            user_turn=user_turn,
            assistant_turn=assistant_turn,
            state=state,
            repair_strategy=repair_strategy,
            predictor_output=predictor_output,
            nl_result=nl_result,
            elapsed_ms=elapsed_ms,
        )

    # ------------------------------------------------------------------
    # User-turn classification
    # ------------------------------------------------------------------

    def _classify_user_turn(self, state: DialogState, user_text: str) -> TurnType:
        """Classify the incoming user text into a TurnType.

        The user can only legally emit OPEN, REPAIR, or CLOSE in this
        scaffold. (Future extension: free-form CLARIFY from the user.)

        Decision:
          - If the conversation is fresh (no turns yet) -> OPEN.
          - If detect_repair fires AND state has at least one CAS-load
            -bearing assistant turn -> REPAIR.
          - If user says "bye" / "thanks" / explicit close -> CLOSE.
          - Otherwise -> OPEN (a fresh thread mid-conversation).
        """
        text = (user_text or "").strip().lower()

        if state.num_turns == 0:
            return TurnType.OPEN

        if detect_repair(state, user_text):
            return TurnType.REPAIR

        # Cheap CLOSE heuristic.
        if any(phrase in text for phrase in ("thanks, that's it", "goodbye", "bye for now")):
            # Only valid after some completed exchange.
            if state.last_turn_type in (
                TurnType.ANSWER, TurnType.PLAN, TurnType.MIRROR, TurnType.REFUSE,
            ):
                return TurnType.CLOSE

        # Default: treat as a new opener / continuation.
        return TurnType.OPEN

    # ------------------------------------------------------------------
    # Normal turn (no repair)
    # ------------------------------------------------------------------

    def _handle_normal_turn(
        self,
        state: DialogState,
        user_text: str,
    ) -> tuple[Turn, DialogState, dict[str, Any], GenerationResult]:
        """Predict, pick a turn type, generate, append. No repair logic."""
        prediction = self.predictor(user_text, state)
        cas_state = str(prediction.get("cas_state", "") or "")
        confidence = float(prediction.get("confidence", 0.0))

        # Pick an assistant turn type from the admissible set.
        chosen = self._pick_assistant_turn_type(state, cas_state, confidence)

        # Generate NL.
        nl_req = GenerationRequest(
            turn_type=chosen,
            cas_state=cas_state,
            user_text=user_text,
            metadata={"prediction": prediction},
        )
        nl_result = self.nl_head(nl_req)

        # Build assistant turn.
        cas_state_after = cas_state if chosen in CAS_LOAD_BEARING else None
        transition = str(prediction.get("transition", "") or "") if cas_state_after else None

        assistant_turn = make_turn(
            role="assistant",
            text=nl_result.text,
            turn_type=chosen,
            cas_state_after=cas_state_after,
            cas_transition=transition,
            metadata={
                "prediction_confidence": confidence,
                "nl_template": nl_result.template_used,
            },
        )
        state = apply_turn(state, assistant_turn)
        return assistant_turn, state, prediction, nl_result

    def _pick_assistant_turn_type(
        self,
        state: DialogState,
        cas_state: str,
        confidence: float,
    ) -> TurnType:
        """Pick an assistant turn type from the admissible set.

        Decision (in order):
          - If admissible_next_moves is empty (CLOSE was the last turn),
            we are at conversation end and should not emit; this branch
            is a safety net that returns CLOSE.
          - If confidence < confidence_floor and MIRROR is admissible,
            emit MIRROR (echo and invite confirmation).
          - Else if ANSWER is admissible, emit ANSWER.
          - Else fall back to the first admissible CAS-load-bearing
            turn type, then to the first admissible turn type at all.
        """
        admissible = state.admissible_next_moves
        if not admissible:
            return TurnType.CLOSE

        if confidence < self.confidence_floor and TurnType.MIRROR in admissible:
            return TurnType.MIRROR

        if TurnType.ANSWER in admissible:
            return TurnType.ANSWER

        # Fall back to admissible CAS-load-bearing types in priority order.
        for candidate in (TurnType.MIRROR, TurnType.PLAN, TurnType.REFUSE_CLAIM):
            if candidate in admissible:
                return candidate

        # Last resort: any admissible.
        # Sort by name for determinism.
        return sorted(admissible, key=lambda t: t.value)[0]

    # ------------------------------------------------------------------
    # CLOSE handling
    # ------------------------------------------------------------------

    def _handle_close(
        self,
        state: DialogState,
        user_text: str,
    ) -> tuple[Turn, DialogState, Optional[dict[str, Any]], GenerationResult]:
        """User has CLOSEd; emit a quiet assistant farewell.

        The user's CLOSE turn has already been appended, so
        ``state.admissible_next_moves`` is empty. We emit an assistant
        CLOSE with ``enforce_admissibility=False`` -- the conversation
        is over and no further legal moves exist.
        """
        nl_req = GenerationRequest(
            turn_type=TurnType.CLOSE,
            cas_state=state.current_cas_state,
            user_text=user_text,
        )
        nl_result = self.nl_head(nl_req)
        assistant_turn = make_turn(
            role="assistant",
            text=nl_result.text,
            turn_type=TurnType.CLOSE,
            metadata={"nl_template": nl_result.template_used},
        )
        state = apply_turn(state, assistant_turn, enforce_admissibility=False)
        return assistant_turn, state, None, nl_result

    # ------------------------------------------------------------------
    # Repair handling
    # ------------------------------------------------------------------

    def _handle_repair(
        self,
        state: DialogState,
        user_text: str,
    ) -> tuple[Turn, DialogState, RepairStrategy, Optional[dict[str, Any]], GenerationResult]:
        """Run the repair-strategy pipeline and produce an assistant turn."""
        strategy = select_repair_strategy(state, user_text)
        state = apply_repair(state, strategy, user_text)

        followup_type = derive_followup_turn_type(strategy)

        # Some follow-up types require a fresh prediction (REFINE -> ANSWER).
        prediction: Optional[dict[str, Any]] = None
        cas_state = state.current_cas_state
        if followup_type == TurnType.ANSWER:
            prediction = self.predictor(user_text, state)
            cas_state = str(prediction.get("cas_state", "") or "")

        nl_req = GenerationRequest(
            turn_type=followup_type,
            cas_state=cas_state,
            user_text=user_text,
            metadata={"prediction": prediction, "repair_strategy": strategy.value},
        )
        nl_result = self.nl_head(nl_req)

        # If followup_type is not admissible after REPAIR, fall back to
        # MIRROR (always admissible after REPAIR per the grammar).
        if followup_type not in state.admissible_next_moves:
            followup_type = TurnType.MIRROR

        cas_state_after = cas_state if followup_type in CAS_LOAD_BEARING else None
        transition = (
            f"repair[{strategy.value}]"
            + (f": {prediction.get('transition', '')}" if prediction else "")
        )

        assistant_turn = make_turn(
            role="assistant",
            text=nl_result.text,
            turn_type=followup_type,
            cas_state_after=cas_state_after,
            cas_transition=transition if cas_state_after else None,
            metadata={
                "repair_strategy": strategy.value,
                "nl_template": nl_result.template_used,
            },
        )
        state = apply_turn(state, assistant_turn)
        return assistant_turn, state, strategy, prediction, nl_result


__all__ = [
    "ConversationEngine",
    "EngineStep",
    "DefaultStubPredictor",
    "PredictorFn",
    "NLHeadFn",
]
