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

__all__ = [
    "CAS_GRAMMAR_BNF",
    "CAS_LANGUAGE_NOTES",
    "RegisterActivation",
    "VALID_REGISTERS",
    "build_diagram",
    "compile_expression",
    "compile_file",
    "extract_register_activations",
]
