"""Phase 2 Dialogue State Tracker (DST) for CAS-Native multi-turn chat.

This package turns CAS-Native from a single-turn structured-prediction
classifier into a chat model. It owns:

  - ``dialog_grammar``: 11 conversational move types and the
    admissibility relation that gates legal next moves.
  - ``state_tracker``: ``DialogState`` data model + pure update
    functions (``apply_turn``, ``compress_history``, ``detect_repair``).
  - ``repair_strategies``: WALK_BACK / REFINE / CLARIFY / RESET
    selection and application when the user corrects.
  - ``conversation_engine``: top-level orchestrator wrapping a predictor
    + an NL generation head into a turn-by-turn chat loop.
  - ``nl_generation_head``: stub NL generator -- defers to the existing
    CAS renderer for ANSWER/MIRROR turns and uses templates otherwise.

This is **scaffolding**. The 11 turn types, the admissibility graph,
the data model, the repair strategy taxonomy, and the engine call
contract are stable and testable. The follow-on session wires real
predictors and a learned NL head without restructuring the API.

See ``docs/working/phase2_dst_spec_2026_05_04.md`` for the architecture
spec and ``docs/working/phase2_completion_2026_05_04.md`` for the
deliverable report from the scaffold session.

Mathematical posture:
  - Correction 1 (admissibility relations): every dialog transition is
    gated by ``is_admissible(prev, next)``.
  - Correction 2 (RPM is section-retraction): repair walk-back is
    value-restoration from the walk-back stack, not inverse computation.

Authoritative Noetic / Domain / Drive / Register names follow the
Project Identity section of ``noetic-compass-scaffold/noetic-compass/CLAUDE.md``.
"""

from __future__ import annotations

from .conversation_engine import (
    ConversationEngine,
    DefaultStubPredictor,
    EngineStep,
    NLHeadFn,
    PredictorFn,
)
from .dialog_grammar import (
    ADMISSIBILITY,
    ASSISTANT_EMITTED,
    CAS_LOAD_BEARING,
    CAS_MUTATING,
    CAS_NEUTRAL,
    EITHER_EMITTED,
    TURN_SEMANTICS,
    TurnSemantics,
    TurnType,
    USER_EMITTED,
    admissibility_graph_is_connected,
    admissible_next,
    carries_cas,
    describe,
    expected_role,
    is_admissible,
    mutates_cas_state,
    reachable_from,
)
from .nl_generation_head import (
    GenerationRequest,
    GenerationResult,
    default_nl_head,
    generate,
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

__all__ = [
    # dialog_grammar
    "TurnType",
    "ADMISSIBILITY",
    "is_admissible",
    "admissible_next",
    "carries_cas",
    "mutates_cas_state",
    "expected_role",
    "reachable_from",
    "admissibility_graph_is_connected",
    "CAS_LOAD_BEARING",
    "CAS_MUTATING",
    "CAS_NEUTRAL",
    "USER_EMITTED",
    "ASSISTANT_EMITTED",
    "EITHER_EMITTED",
    "TurnSemantics",
    "TURN_SEMANTICS",
    "describe",
    # state_tracker
    "Turn",
    "DialogState",
    "initial_state",
    "apply_turn",
    "compress_history",
    "detect_repair",
    "make_turn",
    # repair_strategies
    "RepairStrategy",
    "RESET_AFTER_REPAIRS",
    "select_repair_strategy",
    "apply_repair",
    "derive_followup_turn_type",
    # nl_generation_head
    "GenerationRequest",
    "GenerationResult",
    "generate",
    "default_nl_head",
    # conversation_engine
    "ConversationEngine",
    "EngineStep",
    "DefaultStubPredictor",
    "PredictorFn",
    "NLHeadFn",
]
