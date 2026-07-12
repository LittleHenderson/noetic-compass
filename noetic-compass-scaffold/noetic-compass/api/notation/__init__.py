"""CAS assessment notation tools.

`parser.py` keeps the original lightweight assessment parser.
`compiler.py` provides the executable typed DSL pipeline.
"""

from .compiler import (
    CAS_GRAMMAR_BNF,
    CAS_LANGUAGE_NOTES,
    RegisterActivation,
    VALID_REGISTERS,
    build_diagram,
    compile_expression,
    compile_file,
    extract_register_activations,
)
from .turn_admissibility import (
    TURN_TYPES,
    MetaLogicRelation,
    TurnAdmissibilityContext,
    TurnAdmissibilityResult,
    TurnAdmissibilityRule,
    list_turn_admissibility_rules,
    turn_admissibility_artifact,
    validate_turn_admissibility,
)

__all__ = [
    "CAS_GRAMMAR_BNF",
    "CAS_LANGUAGE_NOTES",
    "RegisterActivation",
    "VALID_REGISTERS",
    "build_diagram",
    "compile_expression",
    "compile_file",
    "extract_register_activations",
    "TURN_TYPES",
    "MetaLogicRelation",
    "TurnAdmissibilityContext",
    "TurnAdmissibilityResult",
    "TurnAdmissibilityRule",
    "list_turn_admissibility_rules",
    "turn_admissibility_artifact",
    "validate_turn_admissibility",
]
