"""IntentIR foundation for CAS/NL recovery."""

from .intent_ir import (
    AmbiguityOption,
    AxisBinding,
    BuilderTarget,
    EvidenceSpan,
    IntentIR,
    MetaLogicIntent,
    ProductionIntent,
    ProductionIngredientIntent,
    RegisterIntent,
    StateAtom,
)
from .builders import build_candidate_expressions
from .level3_ingest import (
    intent_from_level3_record,
    intents_from_level3_records,
    load_level3_intents,
)

__all__ = [
    "AmbiguityOption",
    "AxisBinding",
    "BuilderTarget",
    "EvidenceSpan",
    "IntentIR",
    "MetaLogicIntent",
    "ProductionIngredientIntent",
    "ProductionIntent",
    "RegisterIntent",
    "StateAtom",
    "build_candidate_expressions",
    "intent_from_level3_record",
    "intents_from_level3_records",
    "load_level3_intents",
]
