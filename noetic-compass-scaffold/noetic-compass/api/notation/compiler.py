"""Executable CAS notation compiler/interpreter.

This module turns the existing CAS notation into a real, typed DSL with an
explicit compilation pipeline:

1. Lexing
2. Parsing into an AST
3. Static type and admissibility checking
4. Lowering to a small stack-machine bytecode
5. Execution on a Python VM

The semantics here are intentionally conservative and documented. They make CAS
notation executable inside this repository without claiming that every algebraic
law from the broader manuscripts has already been formalized.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import importlib.util
import math
import os
from pathlib import Path
import re
import sys
from typing import Any

try:
    import cas_engine
except ImportError:  # pragma: no cover - exercised via fallback tests
    cas_engine = None


OPERATOR_NAMES = [
    "Idea",
    "Mind",
    "Positive",
    "Negative",
    "Vibration",
    "Female",
    "Male",
    "Rhythm",
    "Above/Cause",
    "Below/Effect",
]

DOMAIN_NAMES = {
    "P": "Principled",
    "C": "Cognitive",
    "E": "Evaluative",
    "O": "Operational",
}

DRIVE_NAMES = {
    1: "Unity",
    2: "Wisdom",
    3: "Vitality",
    4: "Connection",
    5: "Agency",
    6: "Structure",
    7: "Purpose",
}

DOMAIN_ORDER = {"P": 0, "C": 1, "E": 2, "O": 3}

# CAS v7.5 Phenomenological Register axis (Clarification 8).
# Register attaches optionally to Noetic primitives, Drive primitives, or
# compound states via the `|R` suffix. Values:
#   T = Transcendent, A = Analytical, f = Affective (lowercase authoritative),
#   E = Embodied.
# Register is a specification of operational character layered on top of the
# existing primitives; it does not modify the 40 Cognitive States, the 7 Core
# Drives, or axioms A1-A7. Expressions without `|R` are register-neutral and
# remain valid as in CAS v7.4.
VALID_REGISTERS = ("T", "A", "f", "E")

REGISTER_NAMES = {
    "T": "Transcendent",
    "A": "Analytical",
    "f": "Affective",
    "E": "Embodied",
}

UNICODE_ARROW = "\u2192"
UNICODE_LARROW = "\u2190"
UNICODE_BIARROW = "\u2194"
UNICODE_TIMES = "\u00d7"
UNICODE_DIVIDE = "\u00f7"
UNICODE_PHI = "\u03a6"
UNICODE_LANGLE = "\u27e8"
UNICODE_RANGLE = "\u27e9"
UNICODE_MEMBER = "\u2208"
UNICODE_NOT_MEMBER = "\u2209"
UNICODE_SUBSET = "\u2282"
UNICODE_SUBSET_EQ = "\u2286"
UNICODE_SUPERSET = "\u2283"
UNICODE_SUPERSET_EQ = "\u2287"
UNICODE_EMPTY_SET = "\u2205"
UNICODE_UNION = "\u222a"
UNICODE_INTERSECTION = "\u2229"
UNICODE_SET_MINUS = "\u2216"
UNICODE_TENSOR = "\u2297"

# CAS v7.6 Stoichiometric Production Semantics (Clarification 9) Unicode
# symbols. Recipe notation introduces Greek letters plus the middle-dot
# coefficient separator as first-class tokens. Each Unicode symbol has an
# ASCII keyword alias (Theta, Omega, Lambda, kappa, iota, eta) so sources
# authored on keyboards without Greek input still compose recipes. The
# middle dot (U+00B7) is additionally accepted wherever `*` would be
# inside recipe prerequisites.
UNICODE_THETA = "Θ"   # Theta  - recipe function
UNICODE_OMEGA = "Ω"   # Omega  - production target
UNICODE_LAMBDA = "Λ"  # Lambda - leakage coefficient marker
UNICODE_KAPPA = "κ"   # kappa  - catalyst marker
UNICODE_IOTA = "ι"    # iota   - inhibitor marker
UNICODE_ETA = "η"     # eta    - efficiency function
UNICODE_CDOT = "·"    # middle dot - coefficient separator


_LEGACY_CAS_GRAMMAR_BNF = """<program>       ::= <statement> (";" <statement>)* ;
<statement>     ::= <let_stmt> | <fn_stmt> | <use_stmt> | <expression> ;
<let_stmt>      ::= "let" <ident> "=" <expression> ;
<fn_stmt>       ::= "fn" <ident> "(" <param_list>? ")" "=" <expression> ;
<use_stmt>      ::= "use" <string> ;
<param_list>    ::= <ident> ("," <ident>)* ;
<expression>    ::= <relation> ;
<relation>      ::= <sum> (("->" | "→" | "<-" | "←" | "<->" | "↔") <sum>)* ;
<sum>           ::= <product> (("+" | "-") <product>)* ;
<product>       ::= <primary> (("*" | "×" | "/" | "÷" | "∘") <primary>)* ;
<primary>       ::= <state> | <state_ref> | <drive_ref> | <rpm_call> | <phi_literal> | <call> | <ident> | <string> | "(" <expression> ")" ;
<call>          ::= <ident> "(" <arg_list>? ")" ;
<arg_list>      ::= <expression> ("," <expression>)* ;
<rpm_call>      ::= "RPM" "(" (<state> | <state_ref> | <drive_ref>) ")" ;
<phi_literal>   ::= ("Phi" | "Φ") ("<" | "⟨") <sequence> (">" | "⟩") ;
<sequence>      ::= <digit> (":" <digit>)* ;
<state>         ::= <operator> "^" <domain> ("_{" <drive_ref> "}")? ;
<state_ref>     ::= <domain> <digit> ;
<operator>      ::= "CO-" <digit> ;
<drive_ref>     ::= "F" <drive_digit> ;
<ident>         ::= <letter> (<letter> | <digit> | "_")* ;
<string>        ::= '"' <char>* '"' ;
<domain>        ::= "P" | "C" | "E" | "O" ;
<letter>        ::= "A" | ... | "Z" | "a" | ... | "z" | "_" ;
<digit>         ::= "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" ;
<drive_digit>   ::= "1" | "2" | "3" | "4" | "5" | "6" | "7" ;"""

_LEGACY_CAS_LANGUAGE_NOTES = {
    "state": "A singular CAS state such as CO-2^C_{F2} or shorthand C2.",
    "relation": "Relations express dependency, result flow, or bidirectional linkage between singular states.",
    "composition": "*, ×, /, ÷ operate on singular states in the same domain; ∘ builds fractal operator sequences.",
    "rpm": "RPM(...) wraps a drive or state and evaluates prerequisite-chain completeness.",
    "program": "Programs may contain multiple statements separated by semicolons or newlines; the final result is preserved.",
    "binding": "let binds a name to the runtime value of an expression.",
    "function": "fn defines an expression-bodied function with arity checking and runtime body evaluation.",
    "module": "use imports another .cas file relative to the current file when executed from compile_file or the CLI.",
}

# Override the legacy grammar/help text with an ASCII-clean, typed module-aware
# version so the public grammar endpoint matches the actual implementation.
CAS_GRAMMAR_BNF = """<program>       ::= <statement> (";" <statement>)* ;
<statement>     ::= <export_stmt> | <let_stmt> | <fn_stmt> | <use_stmt> | <expression> ;
<export_stmt>   ::= "export" (<let_stmt> | <fn_stmt>) ;
<let_stmt>      ::= "let" <ident> (":" <type_expr>)? "=" <expression> ;
<fn_stmt>       ::= "fn" <ident> "(" <typed_param_list>? ")" (":" <type_expr>)? "=" <expression> ;
<use_stmt>      ::= "use" <string> ;
<typed_param_list> ::= <typed_param> ("," <typed_param>)* ;
<typed_param>   ::= <ident> (":" <type_expr>)? ;
<type_expr>     ::= <type_name> ("[" <domain_list> "]")? ;
<type_name>     ::= "state" | "drive" | "string" | "void" | "function" | "fractal" | "rpm" | "relation" | "program" | "number" | "tuple" | "meta_set" | "meta_symbol" | "meta_assertion" | "ohm_scale" | "ohm_drive" | "ohm_attention" | "ohm_constraint" | "any" ;
<domain_list>   ::= <domain> ("," <domain>)* ;
<expression>    ::= <meta_relation> ;
<meta_relation> ::= <set_expr> (("∈" | "∉" | "⊂" | "⊆" | "⊃" | "⊇") <set_expr>)* ;
<set_expr>      ::= <relation> (("∪" | "∩" | "∖" | "union" | "intersect" | "setminus") <relation>)* ;
<relation>      ::= <sum> (("->" | "<-" | "<->") <sum>)* ;
<sum>           ::= <product> (("+" | "-") <product>)* ;
<product>       ::= <primary> (("*" | "/" | "∘" | "×" | "÷") <primary>)* ;
<primary>       ::= <state> | <state_ref> | <drive_ref> | <rpm_call> | <phi_literal> | <tuple_literal> | <cardinality> | <meta_set> | <typed_meta_set> | <meta_symbol> | "∅" | <number> | <call> | <ident> | <string> | "(" <expression> ")" ;
<cardinality>   ::= "|" <relation> "|" ;
<meta_set>      ::= "Noetics" | "Domains" | "Worlds" | "Drives" | "Registers" | "States" | "Foundations" | "SubFoundations" | "Foundation_1" | ... | "Foundation_7" ;
<typed_meta_set> ::= "{" <arg_list>? "}" | ("NoeticSet" | "NoeticCluster" | "Cluster" | "StateSet" | "StateCluster" | "StateVariantSet" | "StateVariantCluster" | "RelationSet" | "RelationCluster" | "DriveSet" | "DomainSet" | "RegisterSet" | "FoundationSet" | "SubFoundationSet") "{" <arg_list>? "}" ;
<tuple_literal> ::= ("Tuple" | "Coordinate") "{" <arg_list>? "}" | ("⟨" | "<") <arg_list>? ("⟩" | ">") ;
<meta_symbol>   ::= <domain> | "T" | "A" | "f" | "E" ;
<call>          ::= <ident> "(" <arg_list>? ")" ;
<arg_list>      ::= <expression> ("," <expression>)* ;
<rpm_call>      ::= "RPM" "(" (<state> | <state_ref> | <drive_ref>) ")" ;
<phi_literal>   ::= ("Phi" | "Φ") ("<" | "⟨") <sequence> (">" | "⟩") ;
<sequence>      ::= <digit> (":" <digit>)* ;
<state>         ::= <operator> "^" <domain> ("_{" <drive_ref> "}")? ;
<state_ref>     ::= <domain> <digit> ;
<operator>      ::= "CO-" <digit> ;
<drive_ref>     ::= "F" <drive_digit> ;
<ident>         ::= <letter> (<letter> | <digit> | "_")* ;
<string>        ::= '"' <char>* '"' ;
<domain>        ::= "P" | "C" | "E" | "O" ;
<letter>        ::= "A" | ... | "Z" | "a" | ... | "z" | "_" ;
<digit>         ::= "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" ;
<drive_digit>   ::= "1" | "2" | "3" | "4" | "5" | "6" | "7" ;"""

CAS_LANGUAGE_NOTES = {
    "state": "A singular CAS state such as CO-2^C_{F2} or shorthand C2.",
    "relation": "Relations express dependency, result flow, or bidirectional linkage between singular states.",
    "composition": "*, ×, /, ÷ operate on singular states in the same domain; ∘ builds fractal operator sequences.",
    "rpm": "RPM(...) wraps a drive or state and evaluates prerequisite-chain completeness.",
    "program": "Programs may contain multiple statements separated by semicolons or newlines; the final result is preserved.",
    "binding": "let binds a name to the runtime value of an expression and may declare an expected type.",
    "function": "fn defines an expression-bodied function with typed parameters and an optional declared return type.",
    "module": "use imports another .cas file relative to the current file when executed from compile_file or the CLI; explicit export statements constrain the imported surface.",
    "types": "Type expressions such as state[C], relation, rpm, or any drive static checking and document intended contracts.",
    "aliases": "Unicode aliases are accepted for arrows (→, ←, ↔), product/division (×, ÷), and fractal composition (∘).",
    "typed_meta_sets": "Finite typed clusters such as NoeticSet{^2, ^7}, NoeticCluster{^2, ^7}, StateCluster{^2^P, C7}, RelationCluster{^5^P -> ^5^C}, and StateVariantCluster{^2^P_{F2}|A, C7|f} compile as meta_set values for membership, subset, and cardinality assertions.",
    "set_operations": "Finite meta-sets support ∪ union, ∩ intersection, ∖ set difference, Pullback(A, B) as a finite subobject meet, Product(A, B) as a namespaced Cartesian product, and validated CoverOf/PartitionOf over an explicit base universe.",
    "tuples": "Tuple{^2, P, F2, A}, Coordinate{^2, P, F2, A}, and ⟨^2, P, F2, A⟩ compile as typed tuple/coordinate values.",
    "diagrams": "Every valid compiled artifact can be projected to a graph diagram with nodes, edges, containment boxes, and layout hints for radial, dependency, recipe, and topos-style renderers.",
    "cas_ohm": "Named ohm_scale/ohm_drive/ohm_attention/ohm_constraint constructors and ohm_flow/ohm_required_drive/ohm_effective_constraint calculations preserve declared linear scales and provenance. Supply decimal strings for exact decimal input. Calculations are not measurements, empirical validation, or Helm control; existing CAS symbols keep their meanings.",
}


class CompilerStage(Enum):
    LEXING = "lexing"
    PARSING = "parsing"
    TYPECHECK = "typecheck"
    LOWERING = "lowering"
    EXECUTION = "execution"


class TokenKind(Enum):
    EXPORT = "EXPORT"
    LET = "LET"
    FN = "FN"
    USE = "USE"
    CO = "CO"
    NOETIC = "NOETIC"
    STATE_REF = "STATE_REF"
    DOMAIN = "DOMAIN"
    DRIVE = "DRIVE"
    REGISTER = "REGISTER"
    RPM = "RPM"
    PHI = "PHI"
    IDENT = "IDENT"
    STRING = "STRING"
    NUMBER = "NUMBER"
    PLUS = "PLUS"
    MINUS = "MINUS"
    TIMES = "TIMES"
    DIVIDE = "DIVIDE"
    CIRC = "CIRC"
    ARROW = "ARROW"
    LARROW = "LARROW"
    BIARROW = "BIARROW"
    MEMBER = "MEMBER"
    NOT_MEMBER = "NOT_MEMBER"
    SUBSET = "SUBSET"
    SUBSET_EQ = "SUBSET_EQ"
    SUPERSET = "SUPERSET"
    SUPERSET_EQ = "SUPERSET_EQ"
    UNION = "UNION"
    INTERSECTION = "INTERSECTION"
    SET_DIFF = "SET_DIFF"
    EMPTY_SET = "EMPTY_SET"
    CARET = "CARET"
    UNDERSCORE = "UNDERSCORE"
    LBRACE = "LBRACE"
    RBRACE = "RBRACE"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    LANGLE = "LANGLE"
    RANGLE = "RANGLE"
    COLON = "COLON"
    COMMA = "COMMA"
    EQUALS = "EQUALS"
    LBRACKET = "LBRACKET"
    RBRACKET = "RBRACKET"
    SEMI = "SEMI"
    # CAS v7.6 Stoichiometric Production Semantics (Clarification 9):
    # recipe/production primitives. These are additive tokens; none of them
    # clash with v7.5 tokens, so every v7.4/v7.5 source continues to lex
    # unchanged.
    THETA = "THETA"            # Theta or Θ  - recipe function
    OMEGA = "OMEGA"            # Omega or Ω  - production target
    LAMBDA_TOK = "LAMBDA"      # Lambda or Λ - leakage coefficient marker
    KAPPA_TOK = "KAPPA"        # kappa or κ  - catalyst marker
    IOTA_TOK = "IOTA"          # iota or ι   - inhibitor marker
    ETA_TOK = "ETA"            # eta or η    - efficiency function
    CDOT = "CDOT"              # middle dot  - coefficient separator
    STATE_VECTOR = "STATE_VECTOR"  # bare S keyword - v7.6 state-vector literal
    YIELD_T = "YIELD_T"        # Y_T - theoretical yield function
    YIELD_A = "YIELD_A"        # Y_A - actual yield function
    PIPE = "PIPE"              # bare `|` condition separator (v7.6 recipes)
    EOF = "EOF"


class TypeKind(Enum):
    ANY = "any"
    STATE = "state"
    DRIVE = "drive"
    STRING = "string"
    VOID = "void"
    FUNCTION = "function"
    FRACTAL = "fractal"
    RPM = "rpm"
    RELATION = "relation"
    PROGRAM = "program"
    NUMBER = "number"
    TUPLE = "tuple"
    META_SET = "meta_set"
    META_SYMBOL = "meta_symbol"
    META_ASSERTION = "meta_assertion"
    OHM_SCALE = "ohm_scale"
    OHM_DRIVE = "ohm_drive"
    OHM_ATTENTION = "ohm_attention"
    OHM_CONSTRAINT = "ohm_constraint"


@dataclass(frozen=True)
class LexToken:
    kind: TokenKind
    value: str
    position: int


@dataclass
class TypeInfo:
    kind: TypeKind
    domains: tuple[str, ...] = ()
    singular: bool = False


@dataclass
class FunctionSignature:
    param_types: tuple[TypeInfo, ...]
    return_type: TypeInfo


@dataclass
class TypeEnv:
    vars: dict[str, TypeInfo] = field(default_factory=dict)
    funcs: dict[str, FunctionSignature] = field(default_factory=dict)
    module_dir: str | None = None
    import_stack: set[str] = field(default_factory=set)
    exports: set[str] = field(default_factory=set)


@dataclass
class Instruction:
    opcode: str
    arg: Any | None = None


class CompilerError(ValueError):
    def __init__(self, stage: CompilerStage, message: str, position: int | None = None):
        self.stage = stage
        self.position = position
        prefix = stage.value
        if position is not None:
            prefix = f"{prefix}@{position}"
        super().__init__(f"{prefix}: {message}")


_CAS_OHM_MODULE = None


def _load_cas_ohm():
    """Load only this compiler's sibling helper, also for file-spec imports.

    No package/cwd/sys.path discovery: an unrelated checkout cannot supply the
    numerical implementation. Register before execution for dataclass support,
    and execute the same bytes used to identify the private namespace.
    """
    global _CAS_OHM_MODULE
    if _CAS_OHM_MODULE is not None:
        return _CAS_OHM_MODULE
    path = Path(__file__).resolve().with_name("cas_ohm.py")
    try:
        source = path.read_bytes()
        identity = hashlib.sha256(str(path).encode("utf-8") + b"\0" + source).hexdigest()
        name = "_cas_ohm_compiler_" + identity
        existing = sys.modules.get(name)
        if existing is not None:
            if getattr(existing, "__cas_ohm_identity__", None) != identity:
                raise CompilerError(CompilerStage.EXECUTION, "CAS-Ohm private module namespace is occupied")
            _CAS_OHM_MODULE = existing
            return existing
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            exec(compile(source, str(path), "exec"), module.__dict__)
        except Exception:
            sys.modules.pop(name, None)
            raise
        module.__cas_ohm_identity__ = identity
        _CAS_OHM_MODULE = module
        return module
    except (OSError, ImportError, SyntaxError) as exc:
        raise CompilerError(CompilerStage.EXECUTION, f"CAS-Ohm sibling helper unavailable: {exc}") from exc


@dataclass
class StateLiteral:
    operator: int
    domain: str
    drive: int | None = None
    # CAS v7.5 Phenomenological Register (Clarification 8). Optional — when
    # None, the state is register-neutral (CAS v7.4-compatible).
    # `register` carries the Noetic-level or compound-state register.
    # `drive_register` carries an independent Drive-level register when the
    # notation specifies both (e.g. `^2|T^C_{F2|A}`).
    #
    # CAS v7.7 (Clarification 10 §2): `register` may ALSO be a
    # `tuple[str, ...]` when the source uses the `|⟨R1,R2,...⟩` register-set
    # notation (e.g. `^3^P|⟨A,f,T⟩`). Representation choice: we extend the
    # existing field rather than introducing a new `RegisterSet` AST node so
    # that downstream consumers that only care whether a register is present
    # (JSON serializers, register-aware scoring, etc.) continue to work via
    # `state.register is not None`; consumers that need to distinguish single
    # register vs register-set call `isinstance(state.register, tuple)`. The
    # serializer (`serialize_ast`) and runtime (`StateValue`) emit a stable
    # `register_set: [...]` key when the field is a tuple so JSON round-trip
    # preserves set form without collapsing it to a single register.
    # `drive_register` follows the same extension.
    register: str | tuple[str, ...] | None = None
    drive_register: str | tuple[str, ...] | None = None
    # True when the source explicitly specified a processing Domain
    # (`^n^D`, `CO-n^D`, or shorthand `D n`). Bare `CO-n` / `^n` keeps the
    # legacy default P-domain runtime behavior, but meta-logic can still
    # distinguish "Noetic primitive" from "explicit P-state" when checking
    # assertions such as `CO-3 in Noetics`.
    domain_explicit: bool = False


@dataclass
class DriveLiteral:
    drive: int
    # CAS v7.5 Phenomenological Register. Optional; None means register-neutral.
    # CAS v7.7 (Clarification 10 §2): may also be a `tuple[str, ...]` when the
    # source uses `F_k|⟨R1,R2⟩` register-set notation. See StateLiteral for
    # the representation rationale.
    register: str | tuple[str, ...] | None = None
    # CAS v7.6 (Clarification 9) Section 4 allows the shorthand
    # `F_k^D` / `F_k^D|R` for a drive specified in a particular domain
    # (e.g., `F2^C|A` = Wisdom-driven analytical cognitive work). The
    # optional `domain` field carries the domain when this shorthand is
    # used; it is None for register-neutral or domain-less v7.4/v7.5
    # drive references so legacy parsing paths are unaffected.
    domain: str | None = None


@dataclass
class FractalLiteral:
    sequence: list[int]


@dataclass
class RpmCall:
    expr: Any


@dataclass
class Identifier:
    name: str


@dataclass
class StringLiteral:
    value: str


@dataclass
class CallExpr:
    callee: str
    args: list[Any]


@dataclass
class BinaryExpr:
    op: str
    left: Any
    right: Any


@dataclass
class NumberLiteral:
    value: int | float


@dataclass
class MetaSetLiteral:
    name: str


@dataclass
class TypedMetaSetLiteral:
    constructor: str
    element_type: str
    elements: list[Any]


@dataclass
class TupleLiteral:
    constructor: str
    elements: list[Any]


@dataclass
class MetaSymbol:
    name: str
    symbol_kind: str = "symbol"


@dataclass
class EmptySetLiteral:
    pass


@dataclass
class CardinalityExpr:
    collection: Any


@dataclass
class MetaAssertion:
    op: str
    left: Any
    right: Any


@dataclass
class EmergentResult:
    """CAS v7.7 (Clarification 10 §4) named emergent result wrapper.

    A parenthesized `×` chain explicitly assigned a named emergent register
    is modeled as `EmergentResult(inner, assigned_name)`. Example:

        (^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω

    parses to an EmergentResult whose `inner` is the ×-chain BinaryExpr and
    whose `assigned_name` is the fully-rendered emergent register identifier
    (e.g. `"^3^P|Ω"`). Representation choice: a dedicated AST node rather
    than extending BinaryExpr with an optional field — this keeps bare
    `×` chains (pre-v7.7) free of new fields and isolates the admissibility
    carve-out of Rule 4 (Section 4) to a single node type, so the Rule 4
    typecheck only needs to know "if this ×-chain is wrapped in
    EmergentResult, the named result is specified and the chain is licensed".
    """

    inner: Any
    assigned_name: str


@dataclass
class LetStatement:
    name: str
    expr: Any
    annotation: TypeInfo | None = None


@dataclass
class FunctionDef:
    name: str
    params: list[str]
    body: Any
    param_types: list[TypeInfo] = field(default_factory=list)
    return_type: TypeInfo | None = None


@dataclass
class UseStatement:
    path: str


@dataclass
class ExportStatement:
    statement: LetStatement | FunctionDef


@dataclass
class Program:
    statements: list[Any]


# ---------------------------------------------------------------------------
# CAS v7.5 Phenomenological Register — per-position register activation
# extraction for trainer consumption (ADR-02 in cas-native v2).
#
# `RegisterActivation` is an additive, opt-in data view over already-parsed
# ASTs. It surfaces per-cognitive-state-position register metadata in a
# shape that is trivial for a PyTorch trainer to turn into tensors
# (cf. `cas-native/training/data_format.md` `register_labels` schema) while
# leaving the existing compiler output (`CompilationArtifact`, `serialize_ast`,
# `serialize_value`, bytecode) untouched. Consumers that only care about the
# AST or the scalar compile result see no change; trainers call
# `extract_register_activations(artifact.ast)` (or `artifact.activations()`)
# to obtain a `list[RegisterActivation]`.
#
# Representation choice (Format A in the dispatch): one frozen dataclass per
# cognitive-state position encountered, emitted in source order. This keeps
# the walker output trivially hashable and equality-comparable (register-set
# ordering is normalized via `frozenset`), lets the trainer iterate and
# scatter into tensor slots without re-walking the AST, and is a stable JSON
# shape if the activation view is later exported over the API boundary. The
# alternative parallel-list shape (Format B) is a trivial derivation at
# batch time and does not need to be the authoritative surface here.
#
# Semantics per field, tied to the grammar:
#   - `position`: the canonical 40-state-bank index computed by
#     `_state_index(operator, domain)` — same formula used everywhere else
#     in the compiler so trainer tensor slots align with the engine's
#     Cognitive State index.
#   - `registers_active`: the concrete register letters that this AST node
#     claims are active. Empty set means *register-neutral*: the CAS v7.4
#     expression did not specify a register. The trainer treats an empty
#     set as "skip register supervision for this example" (per the
#     `register_labels` masking rule in `data_format.md`); it is NOT
#     equivalent to "zero registers" or a negative supervision signal.
#   - `is_register_set`: True when the source used the CAS v7.7
#     `|⟨R1,R2,...⟩` register-set specification (Clarification 10 §2).
#     False for the single-register form `|R` and for register-neutral
#     nodes. Trainers that care about Rule 4 compliance or architectural
#     specification vs co-presence distinguish these two cases; empty-set
#     plus False ⇒ neutral, one-element set plus False ⇒ single register,
#     any cardinality plus True ⇒ explicit set specification.
#   - `emergent_name`: the name on the RHS of a CAS v7.7 named
#     emergent-result assignment (e.g. `Ω_refusal`). Set on a trailing
#     activation record appended for the emergent result itself, and on
#     each operand activation whose position participates in the same
#     emergent result (so the trainer can associate inputs with their
#     fused output). `None` for ordinary positions. The emergent record's
#     `registers_active` carries the *union* of the operand registers —
#     see the walker docstring below for rationale.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RegisterActivation:
    """Per-position Phenomenological Register activation for trainer consumption.

    Emitted by :func:`extract_register_activations` (or the
    :meth:`CompilationArtifact.activations` convenience method) one per
    cognitive-state position walked in source order. See the module header
    comment for semantics of each field.
    """

    position: int
    registers_active: frozenset[str]
    is_register_set: bool
    emergent_name: str | None = None


# ---------------------------------------------------------------------------
# CAS v7.6 Stoichiometric Production Semantics (Clarification 9) AST nodes.
#
# These are parse-only literals: the compiler validates recipe SYNTAX and
# captures the parsed structure as AST. Yield calculation, limiting reagent
# analysis, efficiency computation, and recipe-algebra execution are
# delegated to the Rust cas-engine (parallel v7.6 backend). The bytecode
# path here pushes recipe/production literals as opaque values so they
# survive round-tripping but are not "executed" by the Python VM.
# ---------------------------------------------------------------------------


@dataclass
class ProductionTargetLiteral:
    """A v7.6 production target `Ω_{name}` or `Ω_name` (Clarification 9 §2).

    `name` is the free-form identifier following the `Ω_` prefix. Targets
    are opaque labels from the compiler's perspective; they acquire meaning
    only via a Recipe definition and yield queries.
    """

    name: str


@dataclass
class RecipePrerequisite:
    """A single `a_i · X_i` pair on the left-hand side of a v7.6 recipe.

    The coefficient is stored as a `float` (integer literals are widened),
    and `primitive` is any v7.5 primitive AST node — StateLiteral,
    DriveLiteral, or a BinaryExpr for compound states — already covered by
    the existing parser.
    """

    coefficient: float
    primitive: Any


@dataclass
class LeakageAnnotation:
    """A `Λ_i · Ω_side` entry appearing after the `→` of a recipe RHS
    (Clarification 9 §3 leakage notation). Represents a side-reaction
    diversion of prerequisite into an unintended production target.
    """

    coefficient: float
    target: ProductionTargetLiteral


@dataclass
class ConditionAnnotation:
    """A `κ_name` catalyst or `ι_name` inhibitor appearing on the arrow of a
    recipe (Clarification 9 §3 catalyst/inhibitor notation). `kind` is
    literal "catalyst" or "inhibitor"; `name` is the free-form identifier
    following the marker (may be empty for a bare `κ` / `ι`).
    """

    kind: str
    name: str


@dataclass
class RecipeLiteral:
    """A full v7.6 recipe:

        Θ(Ω_name) [| κ_n, ι_n ...] = a_1·X_1 + ... + a_n·X_n → Ω_name [+ Λ·Ω_side ...]

    Parse-only: the compiler does NOT compute yield, limiting reagent, or
    efficiency from a RecipeLiteral. Those are Rust cas-engine
    responsibilities. The AST captures the parsed structure faithfully so
    downstream tooling (engine bindings, renderers) can consume it.
    """

    target: ProductionTargetLiteral
    prerequisites: list[RecipePrerequisite] = field(default_factory=list)
    leakages: list[LeakageAnnotation] = field(default_factory=list)
    catalysts: list[ConditionAnnotation] = field(default_factory=list)
    inhibitors: list[ConditionAnnotation] = field(default_factory=list)


@dataclass
class StateVectorLiteral:
    """A v7.6 state-vector literal `S = {X_1: x_1, ..., X_n: x_n}`
    (Clarification 9 §3). Each entry binds a v7.5 primitive to a numeric
    activation quantity. The compiler parses the mapping and captures it
    as an ordered list of `(primitive_ast, number)` pairs; the Rust engine
    consumes the vector for yield computations.
    """

    entries: list[tuple[Any, float]] = field(default_factory=list)


@dataclass
class YieldExpression:
    """A v7.6 yield query:

      Y_T(Ω | S, Θ)     - theoretical yield, kind="theoretical"
      Y_A(Ω)            - actual yield,       kind="actual"
      η(Ω)              - efficiency,         kind="efficiency"

    The compiler parses the shape but does NOT evaluate yields. Execution
    of these queries is a Rust cas-engine responsibility.
    """

    kind: str
    target: ProductionTargetLiteral
    state: Any | None = None
    recipe: Any | None = None


@dataclass
class StateValue:
    states: dict[int, float]
    drive_weights: dict[int, float] = field(default_factory=dict)
    explicit_drive: bool = False
    domain_explicit: bool = True
    # CAS v7.5 Phenomenological Register (Clarification 8). Optional; None
    # means the state is register-neutral (v7.4-compatible). `register`
    # carries the Noetic/compound-level register; `drive_register` carries
    # an independent Drive-level register when the notation specifies both.
    # CAS v7.7 (Clarification 10 §2): these fields may be `tuple[str, ...]`
    # when the source uses the `|⟨…⟩` register-set notation; `to_dict()`
    # surfaces the set under a `register_set` key to preserve the
    # specification shape without collapsing to a single register.
    register: str | tuple[str, ...] | None = None
    drive_register: str | tuple[str, ...] | None = None
    # CAS v7.7 (Clarification 10 §4): named emergent register assigned via
    # `(... × ...) = X|Ω` syntax. Only set when the ×-chain was wrapped in
    # an EmergentResult node; None otherwise so legacy ×-chain output is
    # unchanged. The value is the raw author-supplied label (e.g. `^3^P|Ω`
    # or `^2^P|TF`) preserved verbatim for downstream consumption.
    emergent_register: str | None = None

    def dominant_state(self) -> int:
        return max(self.states, key=self.states.get)

    def dominant_domain(self) -> str:
        idx = self.dominant_state()
        return "PCEO"[idx // 10]

    def dominant_operator(self) -> int:
        return self.dominant_state() % 10

    def normalized(self) -> "StateValue":
        total = sum(self.states.values()) or 1.0
        drive_total = sum(self.drive_weights.values())
        return StateValue(
            states={k: v / total for k, v in self.states.items()},
            drive_weights=(
                {k: v / drive_total for k, v in self.drive_weights.items()}
                if drive_total > 0
                else {}
            ),
            explicit_drive=self.explicit_drive,
            domain_explicit=self.domain_explicit,
            register=self.register,
            drive_register=self.drive_register,
            # CAS v7.7 Clarification 10 §4: preserve named emergent register
            # through normalization so the authored label survives the
            # `×`-chain execution path end-to-end.
            emergent_register=self.emergent_register,
        )

    def to_dict(self) -> dict[str, Any]:
        dominant = self.dominant_state()
        dom = "PCEO"[dominant // 10]
        op = dominant % 10
        drive = None
        if self.drive_weights:
            drive = max(self.drive_weights, key=self.drive_weights.get)
        payload: dict[str, Any] = {
            "kind": "state",
            "states": {str(k): round(v, 6) for k, v in sorted(self.states.items())},
            "dominant_state": f"{dom}{op}",
            "dominant_operator": f"CO-{op}",
            "dominant_domain": dom,
            "dominant_drive": f"F{drive}" if drive is not None else None,
        }
        # CAS v7.5: expose register metadata on the state output. Only include
        # the keys when actually set so register-neutral states look identical
        # to v7.4 output and downstream consumers aren't surprised by new
        # fields on legacy expressions.
        # CAS v7.7 (Clarification 10 §2): a tuple-valued register represents
        # the `|⟨…⟩` register-set form. Surface it under `register_set` with
        # the full ordered list so consumers can distinguish "one register"
        # from "a set of registers" without collapsing the set form.
        if isinstance(self.register, tuple):
            payload["register_set"] = list(self.register)
            payload["register_set_names"] = [
                REGISTER_NAMES[r] for r in self.register
            ]
        elif self.register is not None:
            payload["register"] = self.register
            payload["register_name"] = REGISTER_NAMES[self.register]
        if isinstance(self.drive_register, tuple):
            payload["drive_register_set"] = list(self.drive_register)
            payload["drive_register_set_names"] = [
                REGISTER_NAMES[r] for r in self.drive_register
            ]
        elif self.drive_register is not None:
            payload["drive_register"] = self.drive_register
            payload["drive_register_name"] = REGISTER_NAMES[self.drive_register]
        # CAS v7.7 (Clarification 10 §4): named emergent register from a
        # `(... × ...) = X|Ω` assignment. Surface the raw label for
        # downstream engine / renderer / report consumers.
        if self.emergent_register is not None:
            payload["emergent_register"] = self.emergent_register
        return payload


@dataclass
class RelationValue:
    relation: str
    source: StateValue
    target: StateValue
    admissible: bool
    domain_descent_ok: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "relation",
            "relation": self.relation,
            "admissible": self.admissible,
            "domain_descent_ok": self.domain_descent_ok,
            "source": self.source.to_dict(),
            "target": self.target.to_dict(),
        }


# ---------------------------------------------------------------------------
# The Nesting Operator: the canon book's meaning, ADDED beside the legacy fields
# ---------------------------------------------------------------------------
# Source: "Thinking in Cognitive Architecture", Chapter 26 (The Fractal
# Calculus) -- Definition 26.1, Theorem 26.2 (Dual Cancellation Criterion), the
# Classification Theorem -- and Chapter 10 (canonical form by cancellation).
#
# What the book states mechanically is computed here. Where the book is in two
# minds, BOTH readings are reported and the open question is named by id;
# nothing is settled silently. The legacy fields of a fractal value
# (`sequence`, `composed_operator`, `orbit_length`, `domain`) are unchanged.

NESTING_SCHEMA = "cas.nesting/0.2"
NESTING_SURFACING_MEMBER = {2: 3, 5: 6, 8: 9}      # surfacing-side member -> its landing-side partner
NESTING_PARTNER = {2: 3, 3: 2, 5: 6, 6: 5, 8: 9, 9: 8}
NESTING_LANDING_SIDE = frozenset({3, 6, 9})          # Theorem 26.2 text and the chapter's Key Insight
NESTING_RHYTHM = 7                                   # listed surfacing-side, but the book names no partner for it
NESTING_OPEN_QUESTIONS = {
    "N1": "Which side is the container. Definition 26.1 (line 6021) and three worked examples (2890, 1845, 6309) put the LEFT thought inside the RIGHT one; three other worked examples (3199, 3203, 4624/4670) read the LEFT thought as the host, and the TKS book's `X.Y` puts the container on the left. This block follows Definition 26.1. Time order is a separate question: line 6044 writes an applied sequence as f_n ∘ ... ∘ f_1 with f_1 applied FIRST, so the right-hand thought may be the EARLIER one; 'later partner' below means 'written to the right'.",
    "N2": "Is nesting with ^0 really a no-op. Definition 26.1 says yes; line 1847 says an ^0^P container changes what is admissible. ^0 terms are dropped from the canonical form here and listed in `identity_terms`.",
    "N3": "Does the order inside a cancelling pair matter. The glossary cancels each pair (7146); lines 3683-3687 say ^5 nested in ^6 gives ^0 while ^6 nested in ^5 is a rupture; Chapter 10 Analysis 3 reduces a ^6-then-^5 word to ^0^E. Both readings are computed, for the canonical form AND for the criterion.",
    "N4": "Which Noetics are surfacing-side and which landing-side. Line 6052 has ^6 landing; line 6073 has ^6 surfacing and ^0 landing; ^7 is surfacing-side in both lists yet has no partner; ^1 and ^4 are in no list. This block uses the 6052 list for ^2/^3, ^5/^6, ^8/^9, treats ^1 and ^4 as neutral, and treats ^7 as a THIRD category: it never resolves and never cancels; a word of ^7 alone is not classed (line 3161 calls a ^7 word 'Amplifying', Template 23 at 6787 calls one 'the healthiest sustained-work signature'); ^7 does not veto a class earned by the other thoughts.",
    "N5": "Where a healthy orbit ends: at ^0 (6075, 6079, 6089) or on ^9 or ^3 (6048), or on ^9 with no cancellation at all (Chapter 10, 2902-2906).",
    "N6": "An alternating involution pair (^2^3^2^3, ^5^6^5^6 ...) is called stabilizing in Chapter 26 (6089, Template 27) and oscillatory in Chapter 10 (2916-2920, Analysis 3). Attached whenever such a pattern is present, whatever class is reported.",
    "N7": "Cancellation needs 'equal intensity' and the chapter names a Closure Ratio; the notation has no intensity and the book gives no formula. Equal intensity is ASSUMED here.",
    "N8": "The book nests across Domains, Drives and Registers but never states the Domain, Drive or Register of the nested whole. Each term keeps its own; the legacy `domain` field is picked by position. A Drive stated on one side only never cancels here ('driven by the same fuel', 6057, never covers an unstated fuel); Register is ignored in the cancelling condition (6013), though Chapter 10 lines 2948 and 3015 describe register-crossing as what makes a cancellation take.",
    "N9": "Short words. Most amplifying and oscillatory examples in the book repeat (`^8 ∘ ^8 ∘ ^8`, `^8 ∘ ^6 ∘ ^8 ∘ ^6`), so those two classes are reported only for repeating patterns; but two-term words are read both ways: `^8 ∘ ^3` is 'highly productive' (6027), `^8 ∘ ^6` is a loop to be fixed (6142), `^2^P ∘ ^6^P` is 'stable' (6124). A non-repeating unresolved word is left unclassed with this id.",
    "N10": "Adjacent or eventual. Chapter 10 cancels pairs 'applied sequentially' (2995) and says of ^8^C followed two steps later by ^9^C that no cancellation appears (2980); Theorem 26.2 says a partner 'must eventually exist' (6052). `canonical_form` cancels ADJACENT pairs only; `dual_cancellation_criterion` accepts ANY partner written to the right. Attached whenever the two disagree.",
    "N11": "Exact partner or any landing-side thought. Line 6052 asks for 'a corresponding landing-side operator (CO_{3,6,9})' and lines 6151, 3015, 3061 and 2902-2904 let ^6 or ^9 resolve an ^8; line 6093 says ^8 'should be matched with ^9, not ^6'. The criterion is computed under both readings (`by_exact_partner`, `by_any_landing`).",
    "N12": "Does a landing-side thought with no surfacing partner break the criterion. Lines 6052 and 6089 are one-directional (only surfacing thoughts need partners); lines 6073 and 6079 are symmetric ('both members eventually appear'; pure landing 'grinds inward to nothing'); Chapter 10 Analyses 1 and 4 call such words Stabilizing. A word with an unpartnered landing thought is left unclassed with this id.",
    "N13": "Chapter 10's five worked analyses (2930-2982) classify by the Domain walk and the ending Noetic, with judgment beyond these rules; this block reproduces the stated class for 1 of the 5 (Analysis 2). Their `→` sequences may not even be the same object as a `∘` word. Attached to every word of two or more thoughts.",
}
NESTING_CROSS_DOMAIN_WARNING = (
    "this nesting crosses Domains: the canon book nests across Domains but does not state the Domain of the "
    "nested whole, so the legacy `domain` field is picked by position; read each term's own Domain in `nesting.terms`"
)
WORLDS_ALIAS_WARNING = (
    "`Worlds` is a compiler alias of `Domains` (P, C, E, O), as the book's Appendix J.3 documents. It is not the "
    "TKS World axis of the 28 Foundations: per Clarification 8 that axis corresponds to `Registers` (T, A, f, E) by "
    "position. The owner selected the original `28 Foundations 1.0` definitions and 1a..7d labels; "
    "the remaining W-A/W-B/W-C questions concern the World/Domain/Register crosswalk. "
    "Write `Domains` or `Registers` explicitly in new work."
)


def _nested_term_label(term: dict[str, Any]) -> str:
    label = f"^{term['noetic']}"
    if term.get("domain"):
        label += f"^{term['domain']}"
    drive_register = term.get("drive_register")
    if isinstance(drive_register, list):
        drive_register = tuple(drive_register)
    if term.get("drive"):
        label += "_{" + str(term["drive"]) + _meta_register_suffix(drive_register) + "}"
    elif drive_register is not None:
        label += "_{" + _meta_register_suffix(drive_register).lstrip("|") + "}"
    register = term.get("register")
    if isinstance(register, list):
        label += "|<" + ",".join(register) + ">"
    elif register:
        label += f"|{register}"
    if term.get("emergent_register") is not None:
        label += f"={term['emergent_register']}"
    return label


def _nested_term_from_digit(noetic: int) -> dict[str, Any]:
    term: dict[str, Any] = {
        "noetic": int(noetic),
        "name": OPERATOR_NAMES[int(noetic)] if 0 <= int(noetic) < len(OPERATOR_NAMES) else "?",
        "domain": None,
        "drive": None,
        "register": None,
    }
    term["label"] = _nested_term_label(term)
    return term


def _nested_term_from_state(value: "StateValue") -> dict[str, Any]:
    term = _nested_term_from_digit(value.dominant_operator())
    if value.domain_explicit:
        term["domain"] = value.dominant_domain()
    if value.explicit_drive and value.drive_weights:
        term["drive"] = f"F{max(value.drive_weights, key=value.drive_weights.get)}"
    if isinstance(value.register, tuple):
        term["register"] = list(value.register)
    elif value.register is not None:
        term["register"] = value.register
    if value.drive_register is not None:
        term["drive_register"] = list(value.drive_register) if isinstance(value.drive_register, tuple) else value.drive_register
    if value.emergent_register is not None:
        term["emergent_register"] = value.emergent_register
    term["label"] = _nested_term_label(term)
    return term


def _nesting_same_setting(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """The book's condition for cancelling: 'in the same domain and driven by the same fuel'."""
    return a.get("domain") == b.get("domain") and a.get("drive") == b.get("drive")


def _nesting_criterion(terms: list[dict[str, Any]], positions: list[int], *, either_order: bool, any_landing: bool) -> dict[str, Any]:
    """Theorem 26.2 under one reading: which surfacing-side thoughts find a partner written to their right.

    either_order: a landing thought written to the LEFT of the surfacing one also counts (N3).
    any_landing:  any landing-side Noetic in the same Domain with the same Drive resolves, not only the exact partner (N11).
    """
    live = [p for p in positions if terms[p]["noetic"] != 0]
    resolved: list[list[int]] = []
    used: set[int] = set()
    unresolved: list[int] = []
    for position in live:
        term = terms[position]
        if term["noetic"] not in NESTING_SURFACING_MEMBER:
            continue
        wanted = NESTING_LANDING_SIDE if any_landing else {NESTING_SURFACING_MEMBER[term["noetic"]]}
        candidates = [q for q in live if q > position and q not in used and terms[q]["noetic"] in wanted and _nesting_same_setting(term, terms[q])]
        if not candidates and either_order:
            candidates = [q for q in live if q < position and q not in used and terms[q]["noetic"] in wanted and _nesting_same_setting(term, terms[q])]
        if candidates:
            partner = candidates[0]
            used.add(partner)
            resolved.append(sorted([position, partner]))
        else:
            unresolved.append(position)
    unpartnered_landing = [p for p in live if terms[p]["noetic"] in NESTING_LANDING_SIDE and p not in used]
    rhythm = [p for p in live if terms[p]["noetic"] == NESTING_RHYTHM]
    surfacing_present = any(terms[p]["noetic"] in NESTING_SURFACING_MEMBER for p in live)
    met: bool | None = False if unresolved else (True if surfacing_present else None)
    return {"resolved": resolved, "unresolved_surfacing": unresolved, "unpartnered_landing": unpartnered_landing, "rhythm_terms": rhythm, "met": met}


def _nesting_reduce(terms: list[dict[str, Any]], positions: list[int], *, either_order: bool) -> tuple[list[int], list[list[int]]]:
    survivors: list[int] = []
    cancelled: list[list[int]] = []
    for position in positions:
        term = terms[position]
        if survivors:
            top = terms[survivors[-1]]
            is_pair = NESTING_PARTNER.get(top["noetic"]) == term["noetic"]
            order_ok = either_order or top["noetic"] in NESTING_SURFACING_MEMBER
            if is_pair and order_ok and _nesting_same_setting(top, term):
                cancelled.append([survivors.pop(), position])
                continue
        survivors.append(position)
    return survivors, cancelled


def _analyse_nesting(terms: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(terms)
    listed: list[dict[str, Any]] = []
    for position, term in enumerate(terms):
        entry = {"position": position, **term}
        if count == 1:
            entry["role"] = "only term"
        elif position == 0:
            entry["role"] = "innermost"
        elif position == count - 1:
            entry["role"] = "governing"
        else:
            entry["role"] = "inside every term to its right; governs every term to its left"
        listed.append(entry)

    identity = [p for p, t in enumerate(terms) if t["noetic"] == 0]
    live = [p for p, t in enumerate(terms) if t["noetic"] != 0]
    domains = {t.get("domain") for t in terms}
    single_domain = next(iter(domains)) if len(domains) == 1 else None

    def _form(survivors: list[int]) -> list[str]:
        if survivors:
            return [terms[p]["label"] for p in survivors]
        return ["^0" + (f"^{single_domain}" if single_domain else "")]

    ordered, ordered_cancelled = _nesting_reduce(terms, live, either_order=False)
    free, free_cancelled = _nesting_reduce(terms, live, either_order=True)
    agreed = ordered == free

    # Theorem 26.2 under the three readings the book supports (N3, N11); the first is the base reading.
    base = _nesting_criterion(terms, live, either_order=False, any_landing=False)
    by_either_order = _nesting_criterion(terms, live, either_order=True, any_landing=False)
    by_any_landing = _nesting_criterion(terms, live, either_order=False, any_landing=True)
    readings_agree = base["met"] == by_either_order["met"] == by_any_landing["met"] and base["unpartnered_landing"] == by_any_landing["unpartnered_landing"]
    resolved, unresolved = base["resolved"], base["unresolved_surfacing"]
    unpartnered_landing, rhythm, met = base["unpartnered_landing"], base["rhythm_terms"], base["met"]
    non_adjacent = [pair for pair in resolved if any(terms[q]["noetic"] != 0 for q in range(pair[0] + 1, pair[1]))]   # a live thought sits between the two
    cancelled_positions = {p for pair in ordered_cancelled for p in pair}
    adjacency_disagrees = any(p not in cancelled_positions for pair in resolved for p in pair)

    present = {terms[p]["noetic"] for p in live}
    has_surfacing = bool(present & set(NESTING_SURFACING_MEMBER))
    has_landing = bool(present & NESTING_LANDING_SIDE)
    alternating_pair = (
        len(live) >= 4 and len(present) == 2 and all(NESTING_PARTNER.get(terms[live[i]]["noetic"]) == terms[live[i + 1]]["noetic"] for i in range(len(live) - 1))
    )
    pure_rhythm = bool(rhythm) and not has_surfacing and not has_landing

    # Conservatively require the full labelled live word to repeat, not just
    # a digit occurring twice. This does not settle the book's N9 threshold.
    labels = [terms[p]["label"] for p in live]
    repeating_word = any(
        len(labels) % period == 0
        and all(label == labels[i % period] for i, label in enumerate(labels))
        for period in range(1, len(labels) // 2 + 1)
    )

    def classify(reading: dict[str, Any]) -> tuple[str, str]:
        """The Classification Theorem (6085-6095) applied to one reading of the criterion."""
        r_unresolved, r_resolved, r_unpartnered = reading["unresolved_surfacing"], reading["resolved"], reading["unpartnered_landing"]
        # Most amplifying and oscillatory examples in the book REPEAT (`^8 ∘ ^8 ∘ ^8 ...`,
        # `^8 ∘ ^6 ∘ ^8 ∘ ^6`); two-term words are read both ways (N9). So those two classes are
        # reported only when the unresolved pattern repeats. ^7 never resolves and never vetoes (N4).
        repeats = repeating_word
        wrong_partners_only = bool(r_unresolved) and all(NESTING_SURFACING_MEMBER[terms[p]["noetic"]] not in present for p in r_unresolved)
        if reading["met"] is True and not r_unpartnered:
            return "stabilizing", "every surfacing-side thought is resolved by a landing-side partner written to its right, in the same Domain with the same Drive"
        if reading["met"] is True and r_unpartnered:
            return "NOT_DECIDED_BY_THE_BOOK", "every surfacing-side thought is resolved, but a landing-side thought has no surfacing partner (N12)"
        if has_surfacing and not has_landing and repeats:
            return "amplifying", "surfacing-side thoughts repeat with no landing-side thought at all"
        if wrong_partners_only and has_landing and not r_resolved and repeats:
            return "oscillatory", "surfacing-side and landing-side thoughts both repeat, but never the right partner"
        if r_unresolved and not repeats and not r_resolved:
            return "NOT_DECIDED_BY_THE_BOOK", "the full labelled word does not repeat (N9)"
        if pure_rhythm:
            return "NOT_DECIDED_BY_THE_BOOK", "^7 Rhythm alone: line 3161 calls such a word Amplifying, Template 23 calls it the healthiest sustained-work signature (N4)"
        if not has_surfacing:
            return "NOT_DECIDED_BY_THE_BOOK", "no surfacing-side thought; the theorem's three classes do not cover this case (N12)"
        return "NOT_DECIDED_BY_THE_BOOK", "some surfacing-side thoughts are resolved and others are not"

    by_reading = {
        "exact_partner_written_to_the_right": classify(base),
        "either_order": classify(by_either_order),
        "any_landing_side": classify(by_any_landing),
    }
    classes = {c for c, _ in by_reading.values()}
    if len(classes) == 1:
        orbit, reason = by_reading["exact_partner_written_to_the_right"]
    else:
        orbit, reason = "NOT_DECIDED_BY_THE_BOOK", "the book's readings of the Dual Cancellation criterion give different classes for this word: " + "; ".join("%s -> %s" % (k, v[0]) for k, v in by_reading.items()) + " (see N3, N11)"

    questions = ["N1"] if count > 1 else []
    if identity:
        questions.append("N2")
    if not agreed or base["met"] != by_either_order["met"]:
        questions.append("N3")
    if present & {6, 7} or (present and present <= {1, 4}):
        questions.append("N4")
    if orbit == "stabilizing":
        questions.append("N5")
    if alternating_pair:
        questions.append("N6")
    if ordered_cancelled or free_cancelled or resolved:
        questions.append("N7")
    mixed = len(domains) > 1 or len({t.get("drive") for t in terms}) > 1 or len({str(t.get("register")) for t in terms}) > 1
    if mixed:
        questions.append("N8")
    if unresolved and not repeating_word:
        questions.append("N9")
    if non_adjacent or adjacency_disagrees:
        questions.append("N10")
    if base["met"] != by_any_landing["met"] or base["unpartnered_landing"] != by_any_landing["unpartnered_landing"]:
        questions.append("N11")
    if unpartnered_landing or (not has_surfacing and has_landing):
        questions.append("N12")
    if count > 1:
        questions.append("N13")

    return {
        "schema": NESTING_SCHEMA,
        "source": "Thinking in Cognitive Architecture, Chapter 26 (Definition 26.1, Theorem 26.2, Classification Theorem) and Chapter 10",
        "reading": "in `f ∘ g` the thought f sits inside the governing environment of g: the FIRST written thought is innermost, the LAST written thought governs",
        "terms": listed,
        "innermost": terms[0]["label"] if terms else None,
        "governing": terms[-1]["label"] if terms else None,
        "crosses_domains": len(domains) > 1,
        "identity_terms": identity,
        "canonical_form": {
            "rule": "identity law, then adjacent involution pairs in the same Domain with the same Drive cancel to ^0",
            "surfacing_member_first": {"cancelled": ordered_cancelled, "form": _form(ordered)},
            "either_order": {"cancelled": free_cancelled, "form": _form(free)},
            "agreed": agreed,
            "form": _form(ordered) if agreed else None,
        },
        "dual_cancellation_criterion": {
            "rule": "every surfacing-side thought needs its exact landing-side partner written to its RIGHT (anywhere, not only adjacent), in the same Domain with the same Drive; the other readings the book supports are computed beside it",
            "resolved": resolved,
            "unresolved_surfacing": unresolved,
            "unpartnered_landing": unpartnered_landing,
            "rhythm_terms": rhythm,
            "met": met,
            "non_adjacent_pairs": non_adjacent,
            "by_either_order": by_either_order,
            "by_any_landing": by_any_landing,
            "readings_agree": readings_agree,
        },
        "chapter_10_analyses": "NOT_REPRODUCED: the five worked analyses of Chapter 10 (lines 2930-2982) are matched on 1 of 5 by these rules (N13)",
        "orbit_class": orbit,
        "orbit_class_reason": reason,
        "orbit_class_by_reading": {k: v[0] for k, v in by_reading.items()},
        "assumed": ["equal intensity (the notation has no intensity field)"],
        "open_questions": questions,
    }


def _nesting_terms_of(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, StateValue):
        return [_nested_term_from_state(value)]
    if isinstance(value, FractalValue):
        if value.terms is not None:
            return [dict(term) for term in value.terms]
        return [_nested_term_from_digit(noetic) for noetic in value.sequence]
    return []


@dataclass
class FractalValue:
    sequence: list[int]
    composed_operator: int
    orbit_length: int
    domain: str | None = None
    terms: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        terms = self.terms if self.terms is not None else [_nested_term_from_digit(noetic) for noetic in self.sequence]
        return {
            "kind": "fractal",
            "sequence": self.sequence,
            "composed_operator": f"CO-{self.composed_operator}",
            "orbit_length": self.orbit_length,
            "domain": self.domain,
            "nesting": _analyse_nesting(terms),
        }


@dataclass
class RpmValue:
    drive: int | None
    completeness: float
    chain: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "rpm",
            "drive": f"F{self.drive}" if self.drive is not None else None,
            "completeness": round(self.completeness, 6),
            "chain": self.chain,
        }


@dataclass
class ProgramValue:
    results: list[Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "program",
            "results": [serialize_value(result) for result in self.results],
            "final_result": serialize_value(self.results[-1]) if self.results else None,
        }


@dataclass
class BindingValue:
    name: str
    value: Any

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "binding", "name": self.name, "value": serialize_value(self.value)}


@dataclass
class FunctionValue:
    name: str
    params: list[str]
    param_types: list[TypeInfo] = field(default_factory=list)
    return_type: TypeInfo | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "function",
            "name": self.name,
            "params": self.params,
            "param_types": [serialize_typeinfo(info) for info in self.param_types],
            "return_type": serialize_typeinfo(self.return_type),
        }


@dataclass
class ModuleValue:
    path: str
    exports: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "module", "path": self.path, "exports": self.exports}


# ---------------------------------------------------------------------------
# CAS v7.6 runtime values. Each parse-only v7.6 literal lowers to a single
# PUSH_* instruction whose argument is the AST node itself; the VM wraps
# the AST node in a thin *Value dataclass so the result survives program
# serialization unchanged. Execution does NOT compute yields, limiting
# reagents, or efficiency -- those are Rust cas-engine responsibilities.
# ---------------------------------------------------------------------------


@dataclass
class ProductionTargetValue:
    """Runtime value for a `Ω_{name}` production target literal."""

    name: str

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "production_target", "name": self.name}


@dataclass
class RecipeValue:
    """Runtime value for a `Θ(Ω) = ... → Ω [+ Λ·Ω_side]` recipe literal.

    Prerequisites, leakages, catalysts, and inhibitors are preserved as
    serializable dicts so the Rust cas-engine can round-trip the recipe
    without re-parsing.
    """

    target: str
    prerequisites: list[dict[str, Any]] = field(default_factory=list)
    leakages: list[dict[str, Any]] = field(default_factory=list)
    catalysts: list[str] = field(default_factory=list)
    inhibitors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "recipe",
            "target": self.target,
            "prerequisites": self.prerequisites,
            "leakages": self.leakages,
            "catalysts": self.catalysts,
            "inhibitors": self.inhibitors,
        }


@dataclass
class StateVectorValue:
    """Runtime value for a `S = { X: x, ... }` state-vector literal."""

    entries: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "state_vector", "entries": self.entries}


@dataclass
class YieldExpressionValue:
    """Runtime value for a `Y_T(...)`, `Y_A(...)`, or `η(...)` query.

    The compiler emits this as an un-evaluated query; the Rust cas-engine
    is responsible for computing yields when it consumes the AST.
    """

    kind: str  # "theoretical" | "actual" | "efficiency"
    target: str
    state: Any | None = None
    recipe: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "yield_expression",
            "yield_kind": self.kind,
            "target": self.target,
            "state": serialize_value(self.state) if self.state is not None else None,
            "recipe": serialize_value(self.recipe) if self.recipe is not None else None,
        }


@dataclass(frozen=True)
class MetaSetValue:
    """Runtime value for a built-in finite CAS meta-set.

    Meta-sets are the compiler's assertion layer over CAS objects. They do
    not replace state/drive/register objects; they let the compiler check
    claims about them (`x in States`, `Foundation_1 subset SubFoundations`,
    `|States| = 40`).
    """

    name: str
    elements: frozenset[str]
    element_type: str = "meta"
    origin: str = "builtin"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "meta_set",
            "name": self.name,
            "element_type": self.element_type,
            "cardinality": len(self.elements),
            "elements": sorted(self.elements),
        }


@dataclass(frozen=True)
class MetaSymbolValue:
    """Runtime value for an atomic symbol used in meta-logic assertions."""

    name: str
    symbol_kind: str = "symbol"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "meta_symbol",
            "name": self.name,
            "symbol_kind": self.symbol_kind,
        }


@dataclass(frozen=True)
class CardinalityValue:
    collection: MetaSetValue

    @property
    def value(self) -> int:
        return len(self.collection.elements)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "cardinality",
            "set": self.collection.name,
            "value": self.value,
        }


@dataclass(frozen=True)
class MetaAssertionValue:
    op: str
    left: Any
    right: Any
    holds: bool
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "meta_assertion",
            "operator": self.op,
            "holds": self.holds,
            "message": self.message,
            "left": serialize_value(self.left),
            "right": serialize_value(self.right),
        }


@dataclass(frozen=True)
class TupleValue:
    constructor: str
    elements: tuple[Any, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "tuple",
            "constructor": self.constructor,
            "arity": len(self.elements),
            "elements": [serialize_value(element) for element in self.elements],
            "labels": [_meta_value_label(element) for element in self.elements],
        }


@dataclass
class UserFunction:
    name: str
    params: list[str]
    param_types: list[TypeInfo]
    return_type: TypeInfo
    bytecode: list[Instruction]


@dataclass
class LoadedModule:
    program: ProgramValue
    vars: dict[str, Any]
    funcs: dict[str, UserFunction]
    exports: list[str]


@dataclass
class RuntimeEnv:
    vars: dict[str, Any] = field(default_factory=dict)
    funcs: dict[str, UserFunction] = field(default_factory=dict)
    parent: "RuntimeEnv | None" = None
    module_dir: str | None = None
    module_cache: dict[str, LoadedModule] = field(default_factory=dict)
    module_stack: set[str] = field(default_factory=set)
    exports: set[str] = field(default_factory=set)
    warnings: list[str] = field(default_factory=list)

    def warn_nesting(self, terms: list[dict[str, Any]]) -> None:
        domains = {term.get("domain") for term in terms if term.get("domain")}
        if len(domains) > 1 and NESTING_CROSS_DOMAIN_WARNING not in self.warnings:
            self.warnings.append(NESTING_CROSS_DOMAIN_WARNING)

    def resolve_var(self, name: str) -> Any:
        if name in self.vars:
            return self.vars[name]
        if self.parent is not None:
            return self.parent.resolve_var(name)
        raise CompilerError(CompilerStage.EXECUTION, f"undefined variable {name}")

    def resolve_func(self, name: str) -> UserFunction:
        if name in self.funcs:
            return self.funcs[name]
        if self.parent is not None:
            return self.parent.resolve_func(name)
        raise CompilerError(CompilerStage.EXECUTION, f"undefined function {name}")


BUILTIN_NAMES = {
    "dominant_state",
    "dominant_domain",
    "dominant_operator",
    "compose",
    "rpm_of",
    "fractal",
    "Pullback",
    "Product",
    "Union",
    "Intersection",
    "Difference",
    "CoverOf",
    "PartitionOf",
    "ohm_scale",
    "ohm_drive",
    "ohm_attention",
    "ohm_constraint",
    "ohm_flow",
    "ohm_required_drive",
    "ohm_effective_constraint",
}

OHM_CONSTRUCTORS = {
    "ohm_drive": TypeKind.OHM_DRIVE,
    "ohm_attention": TypeKind.OHM_ATTENTION,
    "ohm_constraint": TypeKind.OHM_CONSTRAINT,
}
OHM_OPERATIONS = {
    "ohm_flow": ((TypeKind.OHM_DRIVE, TypeKind.OHM_CONSTRAINT), TypeKind.OHM_ATTENTION, "attention_flow"),
    "ohm_required_drive": ((TypeKind.OHM_ATTENTION, TypeKind.OHM_CONSTRAINT), TypeKind.OHM_DRIVE, "required_drive"),
    "ohm_effective_constraint": ((TypeKind.OHM_DRIVE, TypeKind.OHM_ATTENTION), TypeKind.OHM_CONSTRAINT, "effective_constraint"),
}
OHM_TYPE_QUANTITIES = {
    TypeKind.OHM_DRIVE: "drive",
    TypeKind.OHM_ATTENTION: "attention",
    TypeKind.OHM_CONSTRAINT: "constraint",
}


_FOUNDATION_SET_NAMES = tuple(f"Foundation_{i}" for i in range(1, 8))

TYPED_META_SET_CONSTRUCTORS = {
    "Set": "meta",
    "MetaSet": "meta",
    "NoeticSet": "noetic",
    "NoeticCluster": "noetic",
    "Cluster": "noetic",
    "StateSet": "state",
    "StateCluster": "state",
    "StateVariantSet": "state_variant",
    "StateVariantCluster": "state_variant",
    "RelationSet": "relation",
    "RelationCluster": "relation",
    "DriveSet": "drive",
    "DomainSet": "domain",
    "RegisterSet": "register",
    "FoundationSet": "foundation",
    "SubFoundationSet": "subfoundation",
}

TUPLE_CONSTRUCTORS = {"Tuple", "Coordinate", "CASTuple", "CASCoordinate"}

_BUILTIN_META_SET_TYPES = {
    "Noetics": "noetic",
    "Domains": "domain",
    "Drives": "drive",
    "Registers": "register",
    "States": "state",
    "Foundations": "foundation",
    "SubFoundations": "subfoundation",
    "EmptySet": "empty",
    **{name: "subfoundation" for name in _FOUNDATION_SET_NAMES},
}


def _drive_key(drive: int) -> str:
    return f"F{drive}"


def _drive_register_key(drive: int, register: str) -> str:
    return f"F{drive}|{register}"


def _state_key(index: int) -> str:
    return f"{'PCEO'[index // 10]}{index % 10}"


def _build_builtin_meta_sets() -> dict[str, frozenset[str]]:
    noetics = frozenset(f"CO-{index}" for index in range(10))
    domains = frozenset(DOMAIN_NAMES)
    drives = frozenset(_drive_key(index) for index in range(1, 8))
    registers = frozenset(VALID_REGISTERS)
    states = frozenset(_state_key(index) for index in range(40))
    foundation_sets = {
        name: frozenset(
            _drive_register_key(index, register)
            for register in VALID_REGISTERS
        )
        for index, name in enumerate(_FOUNDATION_SET_NAMES, start=1)
    }
    subfoundations = frozenset().union(*foundation_sets.values())
    return {
        "Noetics": noetics,
        "Domains": domains,
        "Drives": drives,
        "Registers": registers,
        "States": states,
        "Foundations": frozenset(_FOUNDATION_SET_NAMES),
        "SubFoundations": subfoundations,
        "EmptySet": frozenset(),
        **foundation_sets,
    }


BUILTIN_META_SETS = _build_builtin_meta_sets()
META_SET_ALIASES = {
    # `Worlds` is a legacy TKS-era alias of `Domains` (book Appendix J.3). It is NOT the
    # TKS World axis of the 28 Foundations; that axis corresponds to `Registers` by position
    # (Clarification 8 and docs/reference/tks_28_foundations_translation_key.md). The alias
    # is kept so old programs still run; using it raises WORLDS_ALIAS_WARNING.
    "Worlds": "Domains",
    "DriveRegisterPositions": "SubFoundations",
    "SubFoundationPositions": "SubFoundations",
}
BUILTIN_META_SET_NAMES = set(BUILTIN_META_SETS) | set(META_SET_ALIASES)
RESERVED_BINDING_NAMES = frozenset(BUILTIN_META_SET_NAMES) | frozenset({"T", "A", "f", "E"})


@dataclass
class CompilationArtifact:
    source: str
    tokens: list[LexToken]
    ast: Any | None
    type_info: TypeInfo | None
    bytecode: list[Instruction]
    result: Any | None
    warnings: list[str] = field(default_factory=list)
    valid: bool = True
    error: str | None = None
    engine: str = "python"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "valid": self.valid,
            "error": self.error,
            "engine": self.engine,
            "warnings": self.warnings,
            "tokens": [
                {"kind": tok.kind.value, "value": tok.value, "position": tok.position}
                for tok in self.tokens
            ],
            "ast": serialize_ast(self.ast) if self.ast is not None else None,
            "type": {
                "kind": self.type_info.kind.value,
                "domains": list(self.type_info.domains),
                "singular": self.type_info.singular,
            }
            if self.type_info is not None
            else None,
            "bytecode": [
                {"opcode": ins.opcode, "arg": serialize_instruction_arg(ins.arg)}
                for ins in self.bytecode
            ],
            "result": serialize_value(self.result),
        }

    def activations(self) -> list["RegisterActivation"]:
        """Per-position register activation view for trainer consumption.

        Additive convenience wrapper around :func:`extract_register_activations`
        that walks :attr:`ast`. Returns an empty list for a failed compile
        (``valid=False``) or for an expression with no cognitive-state nodes
        (e.g. a pure RPM drive query). See the :class:`RegisterActivation`
        docstring and the module header comment for semantics.
        """
        if self.ast is None or not self.valid:
            return []
        return extract_register_activations(self.ast)

    def diagram(self) -> dict[str, Any]:
        """Graph/geometry view for real-time CAS teaching surfaces."""
        if self.ast is None or not self.valid:
            return empty_diagram()
        return build_diagram(self.ast)


TOKEN_PATTERNS: list[tuple[str, TokenKind | None]] = [
    (r"[ \t\r]+", None),
    (r"\r?\n+", TokenKind.SEMI),
    (r"\#[^\r\n]*", None),
    (r"//[^\r\n]*", None),
    (r"export\b", TokenKind.EXPORT),
    (r"let\b", TokenKind.LET),
    (r"fn\b", TokenKind.FN),
    (r"use\b", TokenKind.USE),
    (r"<->|" + re.escape(UNICODE_BIARROW), TokenKind.BIARROW),
    (r"->|" + re.escape(UNICODE_ARROW), TokenKind.ARROW),
    (r"<-|" + re.escape(UNICODE_LARROW), TokenKind.LARROW),
    (re.escape(UNICODE_NOT_MEMBER), TokenKind.NOT_MEMBER),
    (re.escape(UNICODE_MEMBER), TokenKind.MEMBER),
    (re.escape(UNICODE_SUBSET_EQ), TokenKind.SUBSET_EQ),
    (re.escape(UNICODE_SUBSET), TokenKind.SUBSET),
    (re.escape(UNICODE_SUPERSET_EQ), TokenKind.SUPERSET_EQ),
    (re.escape(UNICODE_SUPERSET), TokenKind.SUPERSET),
    (r"union\b|" + re.escape(UNICODE_UNION), TokenKind.UNION),
    (r"intersect(?:ion)?\b|" + re.escape(UNICODE_INTERSECTION), TokenKind.INTERSECTION),
    (r"setminus\b|difference\b|diff\b|" + re.escape(UNICODE_SET_MINUS), TokenKind.SET_DIFF),
    (re.escape(UNICODE_EMPTY_SET), TokenKind.EMPTY_SET),
    (r"RPM\b", TokenKind.RPM),
    (r"Phi\b|" + re.escape(UNICODE_PHI), TokenKind.PHI),
    # CAS v7.6 yield-query keywords `Y_T` and `Y_A`. Listed BEFORE the
    # generic identifier/drive patterns so `Y_T(...)` and `Y_A(...)` of
    # Clarification 9 Section 3 tokenize as single tokens rather than
    # `Y` + `_T`. Anchored with `\b` so a longer identifier starting with
    # `Y_T`/`Y_A` is not silently swallowed.
    (r"Y_T\b", TokenKind.YIELD_T),
    (r"Y_A\b", TokenKind.YIELD_A),
    # CAS v7.6 ASCII aliases for the Greek production-semantics tokens.
    # Listed BEFORE domain/state-ref/ident so `Omega` does not tokenize
    # as DOMAIN `O` + IDENT `mega` and `S` (state-vector keyword) does
    # not get swallowed. No `\b` anchor -- production-target / condition
    # names follow the keyword via `_` (e.g. `Ω_book`, `κ_deadline`),
    # and `_` is a word character, so `\b` would fail after the keyword
    # in every realistic shape. These six keywords are reserved in v7.6
    # and cannot be used as user identifiers.
    (r"Theta|" + re.escape(UNICODE_THETA), TokenKind.THETA),
    (r"Omega|" + re.escape(UNICODE_OMEGA), TokenKind.OMEGA),
    (r"Lambda|" + re.escape(UNICODE_LAMBDA), TokenKind.LAMBDA_TOK),
    (r"kappa|" + re.escape(UNICODE_KAPPA), TokenKind.KAPPA_TOK),
    (r"iota|" + re.escape(UNICODE_IOTA), TokenKind.IOTA_TOK),
    (r"eta|" + re.escape(UNICODE_ETA), TokenKind.ETA_TOK),
    # CAS v7.6 state-vector keyword `S`. Matched with word-boundary so it
    # only consumes a bare `S`, never the leading `S` of some longer
    # identifier.
    (r"S\b", TokenKind.STATE_VECTOR),
    (r'"(?:[^"\\]|\\.)*"', TokenKind.STRING),
    (r"CO-\d+", TokenKind.CO),
    # CAS v7.8 meta-logic cardinality `|X|`. This lookahead lets a leading
    # bar before a collection name tokenize as PIPE without stealing legacy
    # register suffixes such as `|A` after state/drive primitives.
    (
        r"\|(?=(?:[A-Za-z_][A-Za-z0-9_]*(?:\{|\|)|[A-Za-z_][A-Za-z0-9_]+|\{|" + re.escape(UNICODE_EMPTY_SET) + r"\|))",
        TokenKind.PIPE,
    ),
    # CAS v7.5: `|R` register suffix. Matched permissively as `|<letter>` so
    # invalid values like `|Q` are lexed and rejected at parse time with a
    # helpful CAS v7.5 error rather than a generic lexing failure.
    (r"\|[A-Za-z]", TokenKind.REGISTER),
    # CAS v7.6: bare `|` condition-separator token used by recipe catalyst /
    # inhibitor annotations: `Θ(Ω) | κ_n, ι_n → Ω`. Matches only when NOT
    # followed by an ASCII letter, so it cannot collide with the v7.5
    # REGISTER pattern above (which requires `|` immediately followed by a
    # letter). The greedy REGISTER match therefore wins whenever a register
    # suffix is intended.
    (r"\|(?![A-Za-z])", TokenKind.PIPE),
    # CAS v7.5 shorthand Noetic primitive: `^n` is equivalent to `CO-n`.
    # Must come before CARET so `^2` tokenizes as a whole rather than as
    # CARET + NUMBER.
    (r"\^\d+", TokenKind.NOETIC),
    (r"[PCEO]\d+(?![A-Za-z0-9]|_(?!\{))", TokenKind.STATE_REF),
    # Accept both `F_n` (CAS v7.5 Clarification 8 notation, with underscore)
    # and `Fn` (CAS v7.4 compatibility) for drive primitives.
    (r"F_\d+(?![A-Za-z0-9_])", TokenKind.DRIVE),
    (r"F\d+(?![A-Za-z0-9_])", TokenKind.DRIVE),
    # Uppercase constructors/builtins that begin with P/C/E/O must be claimed
    # before the single-letter DOMAIN rule, otherwise `Pullback(...)` would
    # tokenize as DOMAIN `P` + IDENT `ullback`.
    (r"(?:Pullback|Product|Coordinate|CASCoordinate|CASTuple|CoverOf|PartitionOf|Cluster|EmptySet)\b", TokenKind.IDENT),
    (r"[PCEO](?![A-Za-z0-9]|_(?!\{))", TokenKind.DOMAIN),
    # CAS v7.7 (Clarification 10 §2): single uppercase letters lex as
    # IDENT. This enables the register-set form `|⟨T,A,f⟩` where each
    # element tokenizes individually, and enables diagnostic-quality
    # errors for invalid register letters (e.g. `|⟨A,Q,T⟩` surfaces a
    # v7.7 "invalid register" error at parse time rather than an opaque
    # lexing failure). Domain letters P/C/E/O are claimed earlier by the
    # DOMAIN pattern so this fallback does not collide; S is claimed by
    # STATE_VECTOR, and F-prefixed drive tokens (`F_n`, `Fn`) are claimed
    # by the DRIVE patterns. A bare `F` had no prior semantic use.
    # Single-letter uppercase identifiers were not previously lexable
    # (bare `T` raised a lexing error), so adding this pattern expands
    # the lexable surface without conflicting with any pre-v7.7 valid
    # token.
    (r"[A-Z][A-Za-z0-9_]*", TokenKind.IDENT),
    # Numeric literal: integer or decimal. CAS v7.6 recipe coefficients may
    # be floats (e.g. `0.3·Ω_procrastination`); v7.4/v7.5 integer-only
    # callers still lex NUMBER on integers unchanged because the decimal
    # branch is optional.
    (r"\d+\.\d+|\d+", TokenKind.NUMBER),
    (r"\+|\u2295", TokenKind.PLUS),
    (r"-", TokenKind.MINUS),
    # CAS v7.6: the middle dot `·` (U+00B7) is additionally accepted
    # wherever `*` or `×` would be. Inside recipe prerequisites `a·X`
    # reads as "a times X" without the visual noise of `*`. The CDOT is
    # folded into TIMES so existing TIMES handling applies unchanged.
    (r"\*|" + re.escape(UNICODE_TIMES) + r"|" + re.escape(UNICODE_CDOT), TokenKind.TIMES),
    (r"/|" + re.escape(UNICODE_DIVIDE), TokenKind.DIVIDE),
    (r"\u2218", TokenKind.CIRC),
    (r"\^", TokenKind.CARET),
    (r"_", TokenKind.UNDERSCORE),
    (r"[a-z][A-Za-z0-9_]*", TokenKind.IDENT),
    (r"\{", TokenKind.LBRACE),
    (r"\}", TokenKind.RBRACE),
    (r"\(", TokenKind.LPAREN),
    (r"\)", TokenKind.RPAREN),
    (r"\[", TokenKind.LBRACKET),
    (r"\]", TokenKind.RBRACKET),
    (r"<|" + re.escape(UNICODE_LANGLE), TokenKind.LANGLE),
    (r">|" + re.escape(UNICODE_RANGLE), TokenKind.RANGLE),
    (r":", TokenKind.COLON),
    (r",", TokenKind.COMMA),
    (r"=", TokenKind.EQUALS),
    (r";", TokenKind.SEMI),
]


def _state_index(operator: int, domain: str) -> int:
    return DOMAIN_ORDER[domain] * 10 + operator


def _canonical_meta_set_name(name: str) -> str:
    return META_SET_ALIASES.get(name, name)


def _is_builtin_meta_set_name(name: str) -> bool:
    return name in BUILTIN_META_SET_NAMES


def _meta_set_value(name: str) -> MetaSetValue:
    canonical = _canonical_meta_set_name(name)
    if canonical not in BUILTIN_META_SETS:
        raise CompilerError(
            CompilerStage.TYPECHECK,
            f"unknown CAS meta-set {name!r}",
        )
    return MetaSetValue(
        name=canonical,
        elements=BUILTIN_META_SETS[canonical],
        element_type=_BUILTIN_META_SET_TYPES.get(canonical, "meta"),
        origin="builtin",
    )


def _validate_register_token(token: "LexToken") -> str:
    """Extract and validate a `|R` register suffix from a REGISTER token.

    CAS v7.5 Clarification 8 defines the Phenomenological Register axis with
    four authoritative values: T (Transcendent), A (Analytical), f (Affective,
    lowercase is authoritative), E (Embodied). Any other value is rejected
    with a clear error referencing CAS v7.5 and the valid set.
    """
    value = token.value[1:]  # strip leading `|`
    if value not in VALID_REGISTERS:
        raise CompilerError(
            CompilerStage.PARSING,
            (
                f"invalid register {value!r}: CAS v7.5 Phenomenological Register "
                f"must be one of {{T, A, f, E}} (lowercase f is authoritative "
                f"for Affective)"
            ),
            position=token.position,
        )
    return value


def _validate_register_identifier(value: str, position: int | None) -> str:
    """Validate a bare register identifier value (no leading `|`).

    Used by the CAS v7.7 (Clarification 10 §2) register-set parser when
    collecting comma-separated identifiers inside `|⟨R1,R2,...⟩`. Enforces
    exactly the same `VALID_REGISTERS` constraint as the single-register
    path so there is one source of truth for the 4-value Register axis.
    """
    if value not in VALID_REGISTERS:
        raise CompilerError(
            CompilerStage.PARSING,
            (
                f"invalid register {value!r}: CAS v7.5/v7.7 Phenomenological "
                f"Register must be one of {{T, A, f, E}} (lowercase f is "
                f"authoritative for Affective)"
            ),
            position=position,
        )
    return value


def _decode_string_literal(raw: str) -> str:
    body = raw[1:-1]
    mapping = {
        '"': '"',
        "\\": "\\",
        "n": "\n",
        "r": "\r",
        "t": "\t",
    }
    chars: list[str] = []
    index = 0
    while index < len(body):
        current = body[index]
        if current == "\\" and index + 1 < len(body):
            nxt = body[index + 1]
            if nxt in mapping:
                chars.append(mapping[nxt])
                index += 2
                continue
            chars.append("\\")
            chars.append(nxt)
            index += 2
            continue
        chars.append(current)
        index += 1
    return "".join(chars)


def _decode_path_literal(raw: str) -> str:
    body = raw[1:-1]
    return body.replace('\\"', '"').replace("\\\\", "\\")


def _type_keyword_to_kind(name: str) -> TypeKind:
    mapping = {
        "any": TypeKind.ANY,
        "state": TypeKind.STATE,
        "drive": TypeKind.DRIVE,
        "string": TypeKind.STRING,
        "void": TypeKind.VOID,
        "function": TypeKind.FUNCTION,
        "fractal": TypeKind.FRACTAL,
        "rpm": TypeKind.RPM,
        "relation": TypeKind.RELATION,
        "program": TypeKind.PROGRAM,
        "number": TypeKind.NUMBER,
        "tuple": TypeKind.TUPLE,
        "meta_set": TypeKind.META_SET,
        "meta_symbol": TypeKind.META_SYMBOL,
        "meta_assertion": TypeKind.META_ASSERTION,
        "ohm_scale": TypeKind.OHM_SCALE,
        "ohm_drive": TypeKind.OHM_DRIVE,
        "ohm_attention": TypeKind.OHM_ATTENTION,
        "ohm_constraint": TypeKind.OHM_CONSTRAINT,
    }
    if name not in mapping:
        raise CompilerError(CompilerStage.PARSING, f"unknown type {name}")
    return mapping[name]


def serialize_typeinfo(info: TypeInfo | None) -> dict[str, Any] | None:
    if info is None:
        return None
    return {
        "kind": info.kind.value,
        "domains": list(info.domains),
        "singular": info.singular,
    }


def _format_typeinfo(info: TypeInfo) -> str:
    label = info.kind.value
    if info.domains:
        label = f"{label}[{','.join(info.domains)}]"
    if not info.singular and info.kind in {TypeKind.STATE, TypeKind.RELATION}:
        label = f"{label}*"
    return label


def _type_matches(actual: TypeInfo, expected: TypeInfo) -> bool:
    if expected.kind == TypeKind.ANY or actual.kind == TypeKind.ANY:
        return True
    if actual.kind != expected.kind:
        return False
    if expected.singular and not actual.singular:
        return False
    if expected.domains and actual.domains and not set(actual.domains).issubset(set(expected.domains)):
        return False
    return True


def _assert_type_compatible(actual: TypeInfo, expected: TypeInfo, *, context: str) -> None:
    if not _type_matches(actual, expected):
        raise CompilerError(
            CompilerStage.TYPECHECK,
            f"{context}: expected {_format_typeinfo(expected)}, got {_format_typeinfo(actual)}",
        )


def _infer_cas_ohm_call(name: str, arguments: list[TypeInfo]) -> TypeInfo:
    if name == "ohm_scale":
        expected = ((TypeKind.STRING,),) * 3
        result = TypeKind.OHM_SCALE
    elif name in OHM_CONSTRUCTORS:
        expected = ((TypeKind.STRING, TypeKind.NUMBER), (TypeKind.OHM_SCALE,), (TypeKind.STRING,), (TypeKind.STRING,))
        result = OHM_CONSTRUCTORS[name]
    else:
        kinds, result, _ = OHM_OPERATIONS[name]
        expected = tuple((kind,) for kind in kinds)
    if len(arguments) != len(expected):
        raise CompilerError(CompilerStage.TYPECHECK, f"builtin {name} expects {len(expected)} arguments, got {len(arguments)}")
    for index, (actual, allowed) in enumerate(zip(arguments, expected), 1):
        if actual.kind not in (*allowed, TypeKind.ANY):
            label = " or ".join(kind.value for kind in allowed)
            raise CompilerError(CompilerStage.TYPECHECK, f"builtin {name} argument {index} expects {label}, got {actual.kind.value}")
    return TypeInfo(kind=result, singular=True)


def _execute_cas_ohm_call(name: str, args: list[Any]) -> Any:
    """Repeat contracts at runtime so untyped user functions cannot bypass them."""
    expected_count = 3 if name == "ohm_scale" else 4 if name in OHM_CONSTRUCTORS else 2
    if len(args) != expected_count:
        raise CompilerError(CompilerStage.EXECUTION, f"{name} expects {expected_count} arguments, got {len(args)}")
    module = _load_cas_ohm()
    try:
        if name == "ohm_scale":
            if not all(isinstance(value, str) for value in args):
                raise CompilerError(CompilerStage.EXECUTION, "ohm_scale expects three strings")
            return module.make_scale(*args)
        if name in OHM_CONSTRUCTORS:
            value, scale, origin, reference = args
            if isinstance(value, CardinalityValue):
                value = value.value
            if isinstance(value, bool) or not isinstance(value, (str, int, float)):
                raise CompilerError(CompilerStage.EXECUTION, f"{name} value must be a number or decimal string")
            if not isinstance(scale, module.OhmScale):
                raise CompilerError(CompilerStage.EXECUTION, f"{name} expects an ohm_scale")
            if not isinstance(origin, str) or not isinstance(reference, str):
                raise CompilerError(CompilerStage.EXECUTION, f"{name} origin and reference must be strings")
            return module.make_quantity(OHM_TYPE_QUANTITIES[OHM_CONSTRUCTORS[name]], value, scale, origin, reference)
        expected, _, implementation = OHM_OPERATIONS[name]
        for index, (value, kind) in enumerate(zip(args, expected), 1):
            if not isinstance(value, module.OhmQuantity) or value.quantity != OHM_TYPE_QUANTITIES[kind]:
                raise CompilerError(CompilerStage.EXECUTION, f"{name} argument {index} expects {kind.value}")
        return getattr(module, implementation)(*args)
    except module.CasOhmError as exc:
        raise CompilerError(CompilerStage.EXECUTION, f"CAS-Ohm: {exc}") from exc


def _compose_operators(left: int, right: int) -> int:
    if cas_engine is not None:
        return cas_engine.CognitiveOperator(left).compose(cas_engine.CognitiveOperator(right)).index
    return (left + right) % 10


_OPERATOR_INVOLUTION_PAIRS = {(2, 3), (3, 2), (5, 6), (6, 5), (8, 9), (9, 8)}


def _is_involution_pair(a: int, b: int) -> bool:
    return (a, b) in _OPERATOR_INVOLUTION_PAIRS


def _is_admissible(operator: int, source_index: int, target_index: int) -> bool:
    if cas_engine is not None:
        return cas_engine.CognitiveOperator(operator).is_admissible(source_index, target_index)
    if operator == 0:
        return source_index == target_index
    return (source_index // 10) == (target_index // 10) or (target_index % 10) == operator


def lex(source: str) -> list[LexToken]:
    tokens: list[LexToken] = []
    pos = 0
    while pos < len(source):
        for pattern, kind in TOKEN_PATTERNS:
            match = re.match(pattern, source[pos:])
            if not match:
                continue
            if kind is not None:
                tokens.append(LexToken(kind=kind, value=match.group(0), position=pos))
            pos += match.end()
            break
        else:
            raise CompilerError(
                CompilerStage.LEXING,
                f"unexpected character {source[pos]!r}",
                position=pos,
            )
    tokens.append(LexToken(kind=TokenKind.EOF, value="", position=len(source)))
    return tokens


class Parser:
    def __init__(self, tokens: list[LexToken]):
        self.tokens = tokens
        self.index = 0
        self.meta_set_aliases_used: list[str] = []      # e.g. `Worlds`; read by _compile_source for WORLDS_ALIAS_WARNING

    def current(self) -> LexToken:
        return self.tokens[self.index]

    def advance(self) -> LexToken:
        token = self.current()
        self.index += 1
        return token

    def expect(self, kind: TokenKind) -> LexToken:
        token = self.current()
        if token.kind != kind:
            raise CompilerError(
                CompilerStage.PARSING,
                f"expected {kind.value}, got {token.kind.value}",
                position=token.position,
            )
        return self.advance()

    def parse(self) -> Any:
        statements: list[Any] = []
        while self.current().kind == TokenKind.SEMI:
            self.advance()
        while self.current().kind != TokenKind.EOF:
            statements.append(self.parse_statement())
            while self.current().kind == TokenKind.SEMI:
                self.advance()
        if not statements:
            raise CompilerError(CompilerStage.PARSING, "empty program")
        if len(statements) == 1:
            return statements[0]
        return Program(statements=statements)

    def _expect_binding_name(self, what: str) -> str:
        token = self.current()
        if token.value in RESERVED_BINDING_NAMES or (token.kind != TokenKind.IDENT and re.match(r"[A-Za-z]", token.value)):
            raise CompilerError(
                CompilerStage.PARSING,
                (
                    f"{token.value!r} is reserved in CAS notation and cannot be used as a {what} name. "
                    "Reserved: domain letters P C E O; register letters T A f E; S (state vector); "
                    "state refs like P1 and drive tokens like F1 or F_1; keywords let fn use export "
                    "RPM Phi Y_T Y_A union intersect intersection setminus difference diff; names that "
                    "start with Theta Omega Lambda kappa iota eta; built-in sets "
                    + ", ".join(sorted(BUILTIN_META_SET_NAMES))
                ),
                position=token.position,
            )
        if token.kind != TokenKind.IDENT:
            raise CompilerError(CompilerStage.PARSING, f"expected IDENT, got {token.kind.value}", position=token.position)
        return self.advance().value

    def parse_statement(self) -> Any:
        token = self.current()
        if token.kind == TokenKind.EXPORT:
            self.advance()
            exported = self.parse_statement()
            if not isinstance(exported, (LetStatement, FunctionDef)):
                raise CompilerError(
                    CompilerStage.PARSING,
                    "export may only be applied to let or fn statements",
                    position=token.position,
                )
            return ExportStatement(statement=exported)
        if token.kind == TokenKind.LET:
            self.advance()
            name = self._expect_binding_name("let")
            annotation = None
            if self.current().kind == TokenKind.COLON:
                self.advance()
                annotation = self.parse_type()
            self.expect(TokenKind.EQUALS)
            return LetStatement(name=name, expr=self.parse_expression(), annotation=annotation)
        if token.kind == TokenKind.FN:
            self.advance()
            name = self.expect(TokenKind.IDENT).value          # fn names are looked up by call and were never mis-bound: not reserved
            self.expect(TokenKind.LPAREN)
            params: list[str] = []
            param_types: list[TypeInfo] = []
            if self.current().kind != TokenKind.RPAREN:
                params.append(self._expect_binding_name("parameter"))
                if self.current().kind == TokenKind.COLON:
                    self.advance()
                    param_types.append(self.parse_type())
                else:
                    param_types.append(TypeInfo(kind=TypeKind.ANY))
                while self.current().kind == TokenKind.COMMA:
                    self.advance()
                    params.append(self._expect_binding_name("parameter"))
                    if self.current().kind == TokenKind.COLON:
                        self.advance()
                        param_types.append(self.parse_type())
                    else:
                        param_types.append(TypeInfo(kind=TypeKind.ANY))
            self.expect(TokenKind.RPAREN)
            return_type = None
            if self.current().kind == TokenKind.COLON:
                self.advance()
                return_type = self.parse_type()
            self.expect(TokenKind.EQUALS)
            return FunctionDef(
                name=name,
                params=params,
                body=self.parse_expression(),
                param_types=param_types,
                return_type=return_type,
            )
        if token.kind == TokenKind.USE:
            self.advance()
            path_token = self.expect(TokenKind.STRING)
            return UseStatement(path=_decode_path_literal(path_token.value))
        # CAS v7.6 state-vector statement: `S = { X1: x1, ... }` (Clarification
        # 9 Section 3). Captured at the statement level so it can coexist
        # with existing state/relation expressions in a multi-statement
        # program.
        if token.kind == TokenKind.STATE_VECTOR:
            return self.parse_state_vector()
        expr = self.parse_expression()
        # CAS v7.7 Clarification 10 §4: named emergent result assignment.
        # If the expression is followed by `=` and a register-named identifier,
        # wrap it in an EmergentResult node. Example:
        #   `(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω`
        # This syntax is the only way to license a same-Noetic multi-register
        # `×` chain (Rule 4). `let`/`fn` statements have already consumed
        # their `=` by this point, so seeing `=` here at statement level
        # unambiguously indicates an emergent-result assignment.
        if self.current().kind == TokenKind.EQUALS:
            self.advance()
            if isinstance(expr, CardinalityExpr):
                rhs = self.parse_expression()
                return MetaAssertion(op="EQUALS", left=expr, right=rhs)
            assigned_name = self._parse_emergent_register_name()
            return EmergentResult(inner=expr, assigned_name=assigned_name)
        return expr

    def _parse_emergent_register_name(self) -> str:
        """Parse the right-hand side of a CAS v7.7 named-emergent-result
        assignment: `(... × ... × ...) = <name>`.

        The name is an identifier-like label per Clarification 10 §4. We
        accept two shapes that appear in the spec examples:

          - Bare identifier-like label (e.g. `TF`, `Ω`, `fused_commitment`).
            Must start with a letter or the uppercase Greek Omega Ω.
          - State-literal-shaped label (e.g. `^3^P|Ω`, `^2^P|TF`) — a
            compound-state notation whose register field names the
            emergent unified register. Parsed by the existing state parser
            path, with the register-letter constraint loosened by storing
            the raw tokens as the assigned name.

        The method captures the raw token stream from the current position
        forward, up to (but not including) the next statement terminator
        (SEMI, EOF). The captured substring is returned as the `assigned_name`
        payload, preserved verbatim so downstream tooling (engine bindings,
        renderers, documentation extractors) can re-interpret the assigned
        emergent register without the compiler overloading its own register
        validation onto author-chosen emergent labels.
        """
        start_tok = self.current()
        if start_tok.kind in (TokenKind.SEMI, TokenKind.EOF):
            raise CompilerError(
                CompilerStage.PARSING,
                (
                    "CAS v7.7 named emergent result: expected an identifier "
                    "after `=` (Clarification 10 §4)"
                ),
                position=start_tok.position,
            )
        # Light shape check: the first token must be a letter-started or
        # Ω-started token. The lexer already constrains what appears here;
        # we re-verify the "starts with letter / Ω / ^" contract so clearly
        # malformed names (e.g. `= 123`, `= +`) surface a specific error.
        leader_ok = start_tok.kind in (
            TokenKind.IDENT,
            TokenKind.DOMAIN,
            TokenKind.STATE_REF,
            TokenKind.NOETIC,
            TokenKind.CO,
            TokenKind.OMEGA,
            TokenKind.THETA,
        )
        if not leader_ok:
            raise CompilerError(
                CompilerStage.PARSING,
                (
                    f"CAS v7.7 named emergent result: expected identifier-like "
                    f"label after `=`, got {start_tok.kind.value} "
                    f"(Clarification 10 §4 allows letters, digits, "
                    f"underscores, and `Ω` as the starting token)"
                ),
                position=start_tok.position,
            )
        # Collect tokens up to the next statement boundary. We stop at SEMI,
        # EOF, RPAREN, RBRACE, RBRACKET, or RANGLE (the close-brackets so a
        # nested assignment `f((...) = X)` surfaces cleanly — though that
        # shape is not in the normative examples, it's a safe boundary).
        terminators = (
            TokenKind.SEMI,
            TokenKind.EOF,
            TokenKind.RPAREN,
            TokenKind.RBRACE,
            TokenKind.RBRACKET,
        )
        parts: list[str] = []
        while self.current().kind not in terminators:
            tok = self.advance()
            parts.append(tok.value)
        name = "".join(parts).strip()
        if not name:
            raise CompilerError(
                CompilerStage.PARSING,
                (
                    "CAS v7.7 named emergent result: empty name after `=` "
                    "(Clarification 10 §4)"
                ),
                position=start_tok.position,
            )
        return name

    def parse_type(self) -> TypeInfo:
        token = self.expect(TokenKind.IDENT)
        kind = _type_keyword_to_kind(token.value)
        domains: list[str] = []
        if self.current().kind == TokenKind.LBRACKET:
            self.advance()
            domains.append(self.expect(TokenKind.DOMAIN).value)
            while self.current().kind == TokenKind.COMMA:
                self.advance()
                domains.append(self.expect(TokenKind.DOMAIN).value)
            self.expect(TokenKind.RBRACKET)
        if domains and (kind == TypeKind.OHM_SCALE or kind in OHM_TYPE_QUANTITIES):
            raise CompilerError(CompilerStage.PARSING, "CAS-Ohm quantity types use declared scales, not CAS Domain qualifiers", position=token.position)
        singular = kind in {
            TypeKind.STATE,
            TypeKind.DRIVE,
            TypeKind.STRING,
            TypeKind.FUNCTION,
            TypeKind.FRACTAL,
            TypeKind.RPM,
            TypeKind.NUMBER,
            TypeKind.TUPLE,
            TypeKind.META_SET,
            TypeKind.META_SYMBOL,
            TypeKind.META_ASSERTION,
            TypeKind.OHM_SCALE,
            TypeKind.OHM_DRIVE,
            TypeKind.OHM_ATTENTION,
            TypeKind.OHM_CONSTRAINT,
        }
        return TypeInfo(kind=kind, domains=tuple(domains), singular=singular)

    def parse_expression(self) -> Any:
        expr = self.parse_set_expression()
        while self.current().kind in {
            TokenKind.MEMBER,
            TokenKind.NOT_MEMBER,
            TokenKind.SUBSET,
            TokenKind.SUBSET_EQ,
            TokenKind.SUPERSET,
            TokenKind.SUPERSET_EQ,
        }:
            token = self.advance()
            if isinstance(expr, MetaAssertion):
                raise CompilerError(
                    CompilerStage.PARSING,
                    "chained set comparisons are not supported; write each comparison as its own statement",
                    position=token.position,
                )
            rhs = self.parse_set_expression()
            expr = MetaAssertion(op=token.kind.value, left=expr, right=rhs)
        if self.current().kind == TokenKind.EQUALS and isinstance(expr, CardinalityExpr):
            self.advance()
            rhs = self.parse_expression()
            expr = MetaAssertion(op="EQUALS", left=expr, right=rhs)
        return expr

    def parse_set_expression(self) -> Any:
        expr = self.parse_relation()
        while self.current().kind in {TokenKind.UNION, TokenKind.INTERSECTION, TokenKind.SET_DIFF}:
            token = self.advance()
            rhs = self.parse_relation()
            expr = BinaryExpr(op=token.kind.value, left=expr, right=rhs)
        return expr

    def parse_relation(self) -> Any:
        expr = self.parse_additive()
        while self.current().kind in {TokenKind.ARROW, TokenKind.LARROW, TokenKind.BIARROW}:
            token = self.advance()
            rhs = self.parse_additive()
            expr = BinaryExpr(op=token.kind.value, left=expr, right=rhs)
        return expr

    def parse_additive(self) -> Any:
        expr = self.parse_multiplicative()
        while self.current().kind in {TokenKind.PLUS, TokenKind.MINUS}:
            token = self.advance()
            rhs = self.parse_multiplicative()
            expr = BinaryExpr(op=token.kind.value, left=expr, right=rhs)
        return expr

    def parse_multiplicative(self) -> Any:
        expr = self.parse_primary()
        while self.current().kind in {TokenKind.TIMES, TokenKind.DIVIDE, TokenKind.CIRC}:
            token = self.advance()
            rhs = self.parse_primary()
            expr = BinaryExpr(op=token.kind.value, left=expr, right=rhs)
        return expr

    def parse_primary(self) -> Any:
        token = self.current()
        if token.kind == TokenKind.LPAREN:
            self.advance()
            expr = self.parse_expression()
            self.expect(TokenKind.RPAREN)
            return expr
        if token.kind == TokenKind.LANGLE:
            return self.parse_tuple_literal("Tuple", close_kind=TokenKind.RANGLE)
        if token.kind == TokenKind.LBRACE:
            return self.parse_typed_meta_set("Set")
        if token.kind == TokenKind.PIPE:
            return self.parse_cardinality()
        if token.kind == TokenKind.RPM:
            self.advance()
            self.expect(TokenKind.LPAREN)
            expr = self.parse_expression()
            self.expect(TokenKind.RPAREN)
            return RpmCall(expr=expr)
        if token.kind == TokenKind.PHI:
            return self.parse_fractal()
        # CAS v7.6 (Clarification 9): production-semantics primaries.
        # A `Θ(...)` expression is either a recipe definition
        # `Θ(Ω) [| conditions] = a_1·X_1 + ... → Ω [leakages]` or (inside
        # a higher-level arithmetic form like `Θ(Ω1) + Θ(Ω2)`) a bare
        # recipe reference — `parse_recipe` handles both by checking for
        # the `=` that distinguishes a full recipe from a reference.
        if token.kind == TokenKind.THETA:
            return self.parse_recipe()
        # `Ω_{name}` / `Ω_name` as a standalone production target literal.
        if token.kind == TokenKind.OMEGA:
            return self.parse_production_target()
        # Yield queries: `Y_T(Ω | S, Θ)`, `Y_A(Ω)`, `η(Ω)`. Parse-only —
        # execution is delegated to the Rust cas-engine.
        if token.kind in (TokenKind.YIELD_T, TokenKind.YIELD_A, TokenKind.ETA_TOK):
            return self.parse_yield_expression()
        if token.kind == TokenKind.CO:
            return self.parse_state()
        if token.kind == TokenKind.NOETIC:
            # CAS v7.5 shorthand: `^n` is equivalent to `CO-n`. Reuse the same
            # parsing path so register suffixes and compound notation work the
            # same way as with `CO-n`.
            return self.parse_state()
        if token.kind == TokenKind.STATE_REF:
            return self.parse_state_ref()
        if token.kind == TokenKind.STRING:
            return StringLiteral(value=_decode_string_literal(self.advance().value))
        if token.kind == TokenKind.NUMBER:
            return self.parse_number()
        if token.kind == TokenKind.EMPTY_SET:
            self.advance()
            return EmptySetLiteral()
        if token.kind == TokenKind.DOMAIN:
            return MetaSymbol(name=self.advance().value, symbol_kind="domain")
        if token.kind == TokenKind.IDENT:
            name = self.advance().value
            if self.current().kind == TokenKind.LBRACE and name in TYPED_META_SET_CONSTRUCTORS:
                return self.parse_typed_meta_set(name)
            if self.current().kind == TokenKind.LBRACE and name in TUPLE_CONSTRUCTORS:
                return self.parse_tuple_literal(name, close_kind=TokenKind.RBRACE)
            if self.current().kind == TokenKind.LPAREN:
                self.advance()
                args: list[Any] = []
                if self.current().kind != TokenKind.RPAREN:
                    args.append(self.parse_expression())
                    while self.current().kind == TokenKind.COMMA:
                        self.advance()
                        args.append(self.parse_expression())
                self.expect(TokenKind.RPAREN)
                return CallExpr(callee=name, args=args)
            if _is_builtin_meta_set_name(name):
                if name in META_SET_ALIASES:
                    self.meta_set_aliases_used.append(name)
                return MetaSetLiteral(name=_canonical_meta_set_name(name))
            if name in VALID_REGISTERS:
                return MetaSymbol(name=name, symbol_kind="register")
            return Identifier(name=name)
        if token.kind == TokenKind.DRIVE:
            drive_token = self.advance()
            drive = self._drive_token_index(drive_token)
            # CAS v7.5: optional `|R` register suffix may attach directly to
            # the drive primitive (`F_2|A`).
            pre_domain_register = self._consume_optional_register()
            domain: str | None = None
            tail_register: str | None = None
            # CAS v7.6 (Clarification 9) Section 4 shorthand: a drive may be
            # specified in a particular domain via `F_k^D` / `F_k^D|R`
            # (e.g. `F2^C|A` = "Wisdom-driven analytical cognitive work").
            # This extends, rather than replaces, the v7.4/v7.5 bare-drive
            # form; legacy expressions without `^D` continue to produce a
            # domain-less DriveLiteral.
            if self.current().kind == TokenKind.CARET:
                self.advance()
                domain = self.expect(TokenKind.DOMAIN).value
                tail_register = self._consume_optional_register()
            # When both a pre-domain register and a tail register appear,
            # prefer the tail (compound) register since it attaches to the
            # drive-in-domain compound. This mirrors the v7.5 state parser's
            # handling of noetic_register / tail_register.
            register = tail_register or pre_domain_register
            return DriveLiteral(drive=drive, register=register, domain=domain)
        raise CompilerError(
            CompilerStage.PARSING,
            f"unexpected token {token.value!r}",
            position=token.position,
        )

    def parse_typed_meta_set(self, constructor: str) -> TypedMetaSetLiteral:
        """Parse a finite typed meta-set or cluster literal.

        Examples:
          - `{^2, ^7}` generic finite meta-set
          - `NoeticSet{^2, ^7}` typed Noetic collection
          - `NoeticCluster{^2, ^7}` semantic alias for a NoeticSet
          - `StateSet{^2^P, C7}` typed Cognitive State collection
          - `StateCluster{^2^P, C7}` teaching-friendly StateSet alias
          - `StateVariantCluster{^2^P_{F2}|A, C7|f}` full
            Drive/Register-qualified state collection
        """
        element_type = TYPED_META_SET_CONSTRUCTORS[constructor]
        self.expect(TokenKind.LBRACE)
        elements: list[Any] = []
        if self.current().kind != TokenKind.RBRACE:
            elements.append(self.parse_expression())
            while self.current().kind == TokenKind.COMMA:
                self.advance()
                elements.append(self.parse_expression())
        self.expect(TokenKind.RBRACE)
        return TypedMetaSetLiteral(
            constructor=constructor,
            element_type=element_type,
            elements=elements,
        )

    def parse_tuple_literal(self, constructor: str, *, close_kind: TokenKind) -> TupleLiteral:
        open_kind = TokenKind.RBRACE if close_kind == TokenKind.RBRACE else TokenKind.RANGLE
        if open_kind == TokenKind.RBRACE:
            self.expect(TokenKind.LBRACE)
        else:
            self.expect(TokenKind.LANGLE)
        elements: list[Any] = []
        if self.current().kind != close_kind:
            elements.append(self.parse_expression())
            while self.current().kind == TokenKind.COMMA:
                self.advance()
                elements.append(self.parse_expression())
        self.expect(close_kind)
        return TupleLiteral(constructor=constructor, elements=elements)

    def parse_number(self) -> NumberLiteral:
        token = self.expect(TokenKind.NUMBER)
        try:
            if "." in token.value:
                return NumberLiteral(value=float(token.value))
            return NumberLiteral(value=int(token.value))
        except (ValueError, OverflowError) as exc:
            raise CompilerError(CompilerStage.PARSING, "numeric literal exceeds the supported conversion limit", position=token.position) from exc

    def parse_cardinality(self) -> CardinalityExpr:
        start = self.expect(TokenKind.PIPE)
        if self.current().kind == TokenKind.PIPE:
            raise CompilerError(
                CompilerStage.PARSING,
                "cardinality expression `|X|` requires a collection name",
                position=start.position,
            )
        collection = self.parse_set_expression()
        self.expect(TokenKind.PIPE)
        return CardinalityExpr(collection=collection)

    def parse_fractal(self) -> FractalLiteral:
        self.expect(TokenKind.PHI)
        self.expect(TokenKind.LANGLE)
        sequence = [int(self.expect(TokenKind.NUMBER).value)]
        while self.current().kind == TokenKind.COLON:
            self.advance()
            sequence.append(int(self.expect(TokenKind.NUMBER).value))
        self.expect(TokenKind.RANGLE)
        return FractalLiteral(sequence=sequence)

    def _drive_token_index(self, token: LexToken) -> int:
        """Extract the numeric drive index from a DRIVE token.

        Accepts both the CAS v7.5 `F_n` form (with underscore, per Clarification
        8 Section 3) and the CAS v7.4 `Fn` form (without underscore).
        """
        value = token.value
        body = value[2:] if value.startswith("F_") else value[1:]
        return int(body)

    def _consume_optional_register(self) -> str | tuple[str, ...] | None:
        """Consume and validate an optional `|R` register suffix if present.

        CAS v7.5 (Clarification 8): returns a single validated register char
        (one of {T, A, f, E}) for bare `|R` forms.

        CAS v7.7 (Clarification 10 §2): additionally accepts the register-set
        form `|⟨R1,R2,...⟩` and returns a `tuple[str, ...]` preserving source
        order. Duplicates and empty sets are rejected at this layer so the
        caller can treat the return value as a canonical specification.

        Returns None if no register suffix is present. Rejects invalid values
        with an explicit CAS v7.5/v7.7 error.
        """
        if self.current().kind == TokenKind.REGISTER:
            return _validate_register_token(self.advance())
        # CAS v7.7 Clarification 10 §2: `|⟨R1,R2,...⟩` register-set form.
        # The lexer splits this into PIPE + LANGLE + identifier tokens + RANGLE.
        # The PIPE pattern `\|(?![A-Za-z])` matches bare `|` when not followed
        # by an ASCII letter; the register-set opening `⟨` (U+27E8) or ASCII
        # `<` that follows is not a letter, so PIPE wins over the REGISTER
        # greedy match. Both Unicode (canonical) and ASCII `<`/`>` are
        # accepted via the existing LANGLE/RANGLE token fold.
        if (
            self.current().kind == TokenKind.PIPE
            and self.index + 1 < len(self.tokens)
            and self.tokens[self.index + 1].kind == TokenKind.LANGLE
        ):
            return self._consume_register_set()
        return None

    def _consume_register_set(self) -> tuple[str, ...]:
        """Parse a `|⟨R1,R2,...⟩` register-set suffix (CAS v7.7 §2).

        Grammar: PIPE LANGLE IDENT_OR_DOMAIN (COMMA IDENT_OR_DOMAIN)* RANGLE.
        Each element must be one of the four authoritative register values
        ({T, A, f, E}); duplicates and empty sets are rejected as structurally
        invalid (Clarification 10 §2). The returned tuple preserves source
        order so round-trip AST → serialization → re-parse survives.

        The lexer classifies:
          - `A`, `T`, `E` (single capital letter) as DOMAIN tokens, because
            the domain pattern `[PCEO]` matches a subset of register letters.
            Only `A` is both a valid register AND a DOMAIN (it is ambiguous
            with no domain letter; P/C/E/O are domain-only). The `T` and `f`
            identifiers tokenize as IDENT because `T` doesn't match any
            single-letter token pattern; lowercase `f` tokenizes as IDENT.
          - Lowercase `f` tokenizes as IDENT.
        We therefore accept IDENT, DOMAIN, and (defensively) STATE_REF-style
        tokens here, extract the literal value, and validate it against
        VALID_REGISTERS — giving a single source of truth for what counts
        as a register.
        """
        self.expect(TokenKind.PIPE)
        open_tok = self.expect(TokenKind.LANGLE)
        registers: list[str] = []
        seen: set[str] = set()
        if self.current().kind == TokenKind.RANGLE:
            # Empty `|⟨⟩` — explicitly rejected per Clarification 10 §2 (a
            # register set must specify at least one register; use the bare
            # no-register form to leave register unspecified).
            raise CompilerError(
                CompilerStage.PARSING,
                (
                    "CAS v7.7 register set `|⟨…⟩` must contain at least one "
                    "register (Clarification 10 §2); use a bare primitive "
                    "without `|R` to leave register unspecified"
                ),
                position=open_tok.position,
            )
        value, pos = self._consume_register_set_element()
        _validate_register_identifier(value, pos)
        registers.append(value)
        seen.add(value)
        while self.current().kind == TokenKind.COMMA:
            self.advance()
            value, pos = self._consume_register_set_element()
            _validate_register_identifier(value, pos)
            if value in seen:
                raise CompilerError(
                    CompilerStage.PARSING,
                    (
                        f"CAS v7.7 register set: duplicate register "
                        f"{value!r} in `|⟨…⟩` (Clarification 10 §2 requires "
                        f"distinct register identifiers)"
                    ),
                    position=pos,
                )
            seen.add(value)
            registers.append(value)
        self.expect(TokenKind.RANGLE)
        return tuple(registers)

    def _consume_register_set_element(self) -> tuple[str, int]:
        """Consume the next token as a register identifier and return
        `(raw_value, position)`. Accepts the token kinds that naturally
        tokenize from the four register letters under the existing lexer:

          - `A` → DOMAIN (because `A` is not in `[PCEO]`... actually `A` is
            NOT a domain letter and thus tokenizes as IDENT since the IDENT
            pattern `[a-z]` doesn't match uppercase. The pre-existing
            behavior: `A` matches no single-letter token pattern, so it
            falls through to the generic IDENT pattern — but IDENT is
            lowercase-only. Let's trace more carefully: `A` has no matching
            rule among DOMAIN ([PCEO]), IDENT ([a-z]...), or STATE_REF
            ([PCEO]\\d+). It would fail to lex. We therefore need the lexer
            to accept single uppercase letters as register identifiers in
            this context.)

        In practice, the lexer handles these cases via existing token
        families (IDENT for lowercase `f`, and we add a STATE_REF-like
        fallback for single uppercase letters T/A/E). Rather than add
        new lexer patterns, we accept any of the tokens the lexer is known
        to produce for register letters here, plus a fallback that parses
        the raw source character at the token's position.
        """
        tok = self.current()
        if tok.kind in (
            TokenKind.IDENT,
            TokenKind.DOMAIN,
            TokenKind.STATE_REF,
        ):
            self.advance()
            return tok.value, tok.position
        # Fallback: anything else is a lex-level problem. Report with
        # a v7.7 register-set error so the author gets a specific hint.
        raise CompilerError(
            CompilerStage.PARSING,
            (
                f"CAS v7.7 register set: expected a register identifier "
                f"(T, A, f, or E), got {tok.kind.value} {tok.value!r}"
            ),
            position=tok.position,
        )

    def parse_state_ref(self) -> StateLiteral:
        """Parse a shorthand state reference like `P3` with optional `|R`."""
        token = self.expect(TokenKind.STATE_REF)
        register = self._consume_optional_register()
        return StateLiteral(
            operator=int(token.value[1:]),
            domain=token.value[0],
            drive=None,
            register=register,
            domain_explicit=True,
        )

    def parse_state(self) -> StateLiteral:
        """Parse a CAS state literal, optionally carrying Phenomenological
        Register suffixes per CAS v7.5 Clarification 8.

        Accepts both the canonical `CO-n` form and the v7.5 shorthand `^n`
        form as the leading Noetic primitive. Register suffixes may attach at:
          - Noetic level:    `^2|T`  or  `CO-2|T`
          - Drive level:     `_{F_2|A}`
          - Compound level:  `^2^C_{F2}|A`  or  `CO-2^C_{F2}|A`

        Independent Noetic and Drive registers (per Section 3 of Clarification
        8) are preserved when both are specified.
        """
        token = self.current()
        if token.kind == TokenKind.CO:
            self.advance()
            operator = int(token.value.split("-")[1])
        elif token.kind == TokenKind.NOETIC:
            self.advance()
            # NOETIC value looks like `^2`; strip the leading caret.
            operator = int(token.value[1:])
        else:
            raise CompilerError(
                CompilerStage.PARSING,
                f"expected a Noetic primitive (CO-n or ^n), got {token.kind.value}",
                position=token.position,
            )

        domain = "P"
        domain_explicit = False
        drive: int | None = None
        drive_register: str | None = None

        # Optional Noetic-level register: `^2|T` or `CO-2|T` before the domain.
        noetic_register = self._consume_optional_register()

        if self.current().kind == TokenKind.CARET:
            self.advance()
            domain = self.expect(TokenKind.DOMAIN).value
            domain_explicit = True
        if self.current().kind == TokenKind.UNDERSCORE:
            self.advance()
            self.expect(TokenKind.LBRACE)
            drive_token = self.expect(TokenKind.DRIVE)
            drive = self._drive_token_index(drive_token)
            # Optional Drive-level register inside the braces: `_{F_2|A}`.
            drive_register = self._consume_optional_register()
            self.expect(TokenKind.RBRACE)

        # Optional compound-level register at the tail: `^2^C_{F2}|A`. If a
        # Noetic-level register was already consumed before the domain, we
        # treat a trailing register here as an independent compound register
        # (retaining the Noetic-level register distinctly is fine for the
        # shape `^2|T^C_{F2|A}`; the trailing form is simply the compound
        # register when no earlier Noetic register was set).
        tail_register = self._consume_optional_register()

        if noetic_register is not None and tail_register is not None:
            # Both specified: keep the Noetic-level one on `register` and
            # treat the trailing register as the compound register overriding
            # it for the compound. Per Section 3 Example 4, the canonical
            # independent-register shape is `^n|R_n^D_{F_k|R_d}`, so a
            # trailing register is rare when a Noetic-level one is present.
            # We prefer the tail register as the compound register and keep
            # the Noetic register preserved via the compound's semantic.
            register = tail_register
        elif tail_register is not None:
            register = tail_register
        else:
            register = noetic_register

        return StateLiteral(
            operator=operator,
            domain=domain,
            drive=drive,
            register=register,
            drive_register=drive_register,
            domain_explicit=domain_explicit,
        )

    # ----------------------------------------------------------------------
    # CAS v7.6 Stoichiometric Production Semantics (Clarification 9) parsers.
    #
    # These methods handle the additive grammar extension for recipe
    # notation. They do NOT compute yields, limiting reagents, or efficiency
    # values -- those are Rust cas-engine responsibilities. The compiler's
    # responsibility here is parse-only: accept syntactically well-formed
    # recipes / yield queries / state vectors and emit the corresponding
    # AST node, or reject clearly-invalid input with a v7.6-specific error.
    #
    # Backward compatibility note: every token added for v7.6 (THETA,
    # OMEGA, LAMBDA_TOK, KAPPA_TOK, IOTA_TOK, ETA_TOK, CDOT, STATE_VECTOR,
    # YIELD_T, YIELD_A, PIPE) is additive. None of them clash with any
    # v7.4/v7.5 production, so every pre-v7.6 expression continues to
    # parse unchanged.
    # ----------------------------------------------------------------------

    def _parse_production_name(self) -> str:
        """Parse the identifier portion of a production-target literal.

        Accepts both notational forms from Clarification 9 Section 3:
          - `Ω_{name}` -- canonical brace form
          - `Ω_name`   -- bare underscore form used throughout the spec
                          examples (Ω_book, Ω_paper, Ω_refusal)

        The caller has already consumed the leading OMEGA token. Name
        characters are captured as a free-form identifier: ASCII letters,
        digits, and underscores after the initial `_`.
        """
        # Underscore is mandatory between the production marker and its name.
        if self.current().kind != TokenKind.UNDERSCORE:
            token = self.current()
            raise CompilerError(
                CompilerStage.PARSING,
                (
                    f"CAS v7.6 production-target literal: expected `_` after `Ω` "
                    f"(form `Ω_name` or `Ω_{{name}}`), got {token.kind.value}"
                ),
                position=token.position,
            )
        self.advance()
        # Brace form `Ω_{name}`.
        if self.current().kind == TokenKind.LBRACE:
            self.advance()
            name_parts: list[str] = []
            # Accept any sequence of identifier-shaped tokens inside braces.
            while self.current().kind not in (TokenKind.RBRACE, TokenKind.EOF):
                name_parts.append(self._consume_name_fragment())
            self.expect(TokenKind.RBRACE)
            name = "".join(name_parts)
        else:
            # Bare form `Ω_name` -- read a single name fragment.
            name = self._consume_name_fragment()
        if not name:
            token = self.current()
            raise CompilerError(
                CompilerStage.PARSING,
                "CAS v7.6 production-target literal: empty name",
                position=token.position,
            )
        return name

    def _consume_name_fragment(self) -> str:
        """Consume the next token as a fragment of a production / condition
        identifier. Fragments that are naturally part of identifier bodies
        (IDENT, NUMBER, DOMAIN, STATE_REF, DRIVE, underscore) are accepted;
        anything else stops the scan.
        """
        tok = self.current()
        fragment_kinds = (
            TokenKind.IDENT,
            TokenKind.NUMBER,
            TokenKind.DOMAIN,
            TokenKind.STATE_REF,
            TokenKind.DRIVE,
        )
        if tok.kind in fragment_kinds:
            self.advance()
            return tok.value
        if tok.kind == TokenKind.UNDERSCORE:
            self.advance()
            return "_"
        raise CompilerError(
            CompilerStage.PARSING,
            f"CAS v7.6: expected identifier fragment, got {tok.kind.value}",
            position=tok.position,
        )

    def parse_production_target(self) -> ProductionTargetLiteral:
        """Parse a standalone production-target literal `Ω_{name}` / `Ω_name`."""
        self.expect(TokenKind.OMEGA)
        name = self._parse_production_name()
        return ProductionTargetLiteral(name=name)

    def _parse_condition_annotation(self, kind: str) -> ConditionAnnotation:
        """Parse a single catalyst (`κ_name`) or inhibitor (`ι_name`).

        The caller has already consumed the KAPPA_TOK / IOTA_TOK. A bare
        `κ` / `ι` with no following `_name` is accepted and produces a
        ConditionAnnotation with an empty name, so the recipe author can
        record "some catalyst" placeholders during authoring.
        """
        name = ""
        if self.current().kind == TokenKind.UNDERSCORE:
            self.advance()
            if self.current().kind == TokenKind.LBRACE:
                self.advance()
                parts: list[str] = []
                while self.current().kind not in (TokenKind.RBRACE, TokenKind.EOF):
                    parts.append(self._consume_name_fragment())
                self.expect(TokenKind.RBRACE)
                name = "".join(parts)
            else:
                name = self._consume_name_fragment()
        return ConditionAnnotation(kind=kind, name=name)

    def _parse_conditions(
        self,
    ) -> tuple[list[ConditionAnnotation], list[ConditionAnnotation]]:
        """Parse a comma-separated list of catalyst/inhibitor annotations
        following a `|` separator inside a recipe header.

        Entries may appear in any order; each is classified as catalyst or
        inhibitor by its leading marker (κ or ι). Returns the two lists
        split by kind.
        """
        catalysts: list[ConditionAnnotation] = []
        inhibitors: list[ConditionAnnotation] = []

        def consume_one() -> None:
            tok = self.current()
            if tok.kind == TokenKind.KAPPA_TOK:
                self.advance()
                catalysts.append(self._parse_condition_annotation("catalyst"))
            elif tok.kind == TokenKind.IOTA_TOK:
                self.advance()
                inhibitors.append(self._parse_condition_annotation("inhibitor"))
            else:
                raise CompilerError(
                    CompilerStage.PARSING,
                    (
                        f"CAS v7.6 recipe conditions: expected a catalyst (κ) "
                        f"or inhibitor (ι) marker, got {tok.kind.value}"
                    ),
                    position=tok.position,
                )

        consume_one()
        while self.current().kind == TokenKind.COMMA:
            self.advance()
            consume_one()
        return catalysts, inhibitors

    def _parse_coefficient_primitive(self) -> RecipePrerequisite:
        """Parse a single `a · X` term from a recipe left-hand side.

        `a` is a numeric literal (integer or decimal). The separator is
        TIMES (which lex-wise accepts `*`, `×`, or `·`). `X` is any
        v7.5-legal primary expression, so compound primitives like
        `^3^P_{F2}|A` or `CO-2^C` continue to be accepted unchanged.
        """
        tok = self.current()
        if tok.kind != TokenKind.NUMBER:
            raise CompilerError(
                CompilerStage.PARSING,
                (
                    f"CAS v7.6 recipe prerequisite: expected numeric "
                    f"coefficient, got {tok.kind.value}"
                ),
                position=tok.position,
            )
        self.advance()
        try:
            coeff = float(tok.value)
        except ValueError as exc:  # pragma: no cover - lexer guards shape
            raise CompilerError(
                CompilerStage.PARSING,
                f"CAS v7.6 recipe: malformed coefficient {tok.value!r}",
                position=tok.position,
            ) from exc
        if coeff <= 0:
            # Section 2: recipe weights are proportional requirements;
            # zero or negative coefficients are structurally invalid.
            raise CompilerError(
                CompilerStage.PARSING,
                (
                    f"CAS v7.6 recipe: coefficient must be positive, got "
                    f"{coeff}"
                ),
                position=tok.position,
            )
        # Require the coefficient separator (`*`, `×`, or `·`). This
        # catches shapes like `2 F_2` where the author forgot the dot.
        sep = self.current()
        if sep.kind != TokenKind.TIMES:
            raise CompilerError(
                CompilerStage.PARSING,
                (
                    f"CAS v7.6 recipe prerequisite: expected `·` (or `*`) "
                    f"between coefficient and primitive, got {sep.kind.value}"
                ),
                position=sep.position,
            )
        self.advance()
        primitive = self.parse_primary()
        return RecipePrerequisite(coefficient=coeff, primitive=primitive)

    def _parse_leakage_annotation(self) -> LeakageAnnotation:
        """Parse one leakage entry `Λ [·] Ω_side` or `Λ_i · Ω_side`.

        Leakage annotations appear on the RHS of a recipe arrow, separated
        by `+` signs. The coefficient is carried either by a numeric
        subscript on Λ (`Λ_0.3`) or by a preceding number-TIMES pair that
        has already been consumed by the caller. In the minimal shape used
        by Section 3 examples, `Λ·Ω_side` is treated as coefficient 1.0.
        """
        self.expect(TokenKind.LAMBDA_TOK)
        coefficient = 1.0
        # Optional `_{...}` numeric subscript on Λ to encode a named or
        # numeric tag. The authoritative spec shape is `Λ_i` where `i` is
        # an index; we accept an optional numeric subscript and fold it
        # into the coefficient when parseable.
        if self.current().kind == TokenKind.UNDERSCORE:
            self.advance()
            sub = self.current()
            if sub.kind == TokenKind.NUMBER:
                self.advance()
                # An integer subscript on Λ is an index tag (Λ_1, Λ_2),
                # not a coefficient -- keep coefficient at 1.0.
                try:
                    float(sub.value)
                except ValueError:  # pragma: no cover - lexer guards shape
                    pass
            elif sub.kind == TokenKind.IDENT:
                self.advance()
            elif sub.kind == TokenKind.LBRACE:
                self.advance()
                while self.current().kind not in (TokenKind.RBRACE, TokenKind.EOF):
                    self.advance()
                self.expect(TokenKind.RBRACE)
            else:
                raise CompilerError(
                    CompilerStage.PARSING,
                    (
                        f"CAS v7.6 leakage annotation: expected identifier "
                        f"or number after `Λ_`, got {sub.kind.value}"
                    ),
                    position=sub.position,
                )
        # Optional `·` between Λ[_i] and the side target.
        if self.current().kind == TokenKind.TIMES:
            self.advance()
        if self.current().kind != TokenKind.OMEGA:
            tok = self.current()
            raise CompilerError(
                CompilerStage.PARSING,
                (
                    f"CAS v7.6 leakage annotation: expected `Ω_side` after "
                    f"`Λ`, got {tok.kind.value}"
                ),
                position=tok.position,
            )
        target = self.parse_production_target()
        return LeakageAnnotation(coefficient=coefficient, target=target)

    def parse_recipe(self) -> RecipeLiteral:
        """Parse a v7.6 recipe literal (Clarification 9 Section 3).

        Recipe shape (conditions are optional, leakages are optional):

            Θ(Ω_name) [| κ_n [, ι_m ...]] = a_1·X_1 + ... + a_n·X_n
                → Ω_name [+ Λ·Ω_side_1 [+ Λ·Ω_side_2 ...]]

        For a bare `Θ(Ω_name)` with no `=`, the method still returns a
        RecipeLiteral so that recipe-algebra forms from Clarification 9
        Section 6 (`Θ(Ω_1) + Θ(Ω_2)`, `Θ(Ω_full) − Θ(Ω_achieved)`, etc.)
        parse at the additive / multiplicative layer. Such bare forms
        carry an empty prerequisites list and are understood by the
        caller (Rust engine) as a reference to a separately-defined
        recipe.
        """
        self.expect(TokenKind.THETA)
        self.expect(TokenKind.LPAREN)
        if self.current().kind != TokenKind.OMEGA:
            tok = self.current()
            raise CompilerError(
                CompilerStage.PARSING,
                (
                    f"CAS v7.6 recipe: expected `Ω_...` production target "
                    f"inside Θ(...), got {tok.kind.value}"
                ),
                position=tok.position,
            )
        target = self.parse_production_target()
        catalysts: list[ConditionAnnotation] = []
        inhibitors: list[ConditionAnnotation] = []
        # Optional conditions clause `| κ_n, ι_m, ...` before closing `)`.
        if self.current().kind == TokenKind.PIPE:
            self.advance()
            catalysts, inhibitors = self._parse_conditions()
        self.expect(TokenKind.RPAREN)
        # Also accept the outer-position conditions form
        # `Θ(Ω) | κ_n, ι_m → Ω` where conditions appear AFTER the closing
        # parenthesis but BEFORE the `=`. This matches Section 3's
        # catalyst/inhibitor notation which specifies conditions as
        # modifiers on the arrow.
        if self.current().kind == TokenKind.PIPE:
            self.advance()
            extra_cats, extra_inhs = self._parse_conditions()
            catalysts.extend(extra_cats)
            inhibitors.extend(extra_inhs)
        # A bare `Θ(Ω)` with no `=` is a recipe reference. Return an
        # empty-body RecipeLiteral so higher-level arithmetic can
        # combine it via `+` / `−` / `×` / `÷` / `∘` (Clarification 9
        # Section 6 recipe operations).
        if self.current().kind != TokenKind.EQUALS:
            return RecipeLiteral(
                target=target,
                prerequisites=[],
                leakages=[],
                catalysts=catalysts,
                inhibitors=inhibitors,
            )
        self.expect(TokenKind.EQUALS)
        prerequisites: list[RecipePrerequisite] = [self._parse_coefficient_primitive()]
        while self.current().kind == TokenKind.PLUS:
            self.advance()
            prerequisites.append(self._parse_coefficient_primitive())
        # CAS v7.6 Clarification 9 Section 3 says catalyst/inhibitor
        # conditions are specified "as modifiers on the arrow". Accept a
        # third legal position for the condition clause: between the last
        # prerequisite and the `→`. Any conditions found here extend the
        # lists already collected from the earlier two positions.
        if self.current().kind == TokenKind.PIPE:
            self.advance()
            arrow_cats, arrow_inhs = self._parse_conditions()
            catalysts.extend(arrow_cats)
            inhibitors.extend(arrow_inhs)
        # The `→` is mandatory on a recipe with a body; if it's missing,
        # surface a v7.6-specific error so the failure mode is obvious.
        if self.current().kind != TokenKind.ARROW:
            tok = self.current()
            raise CompilerError(
                CompilerStage.PARSING,
                (
                    f"CAS v7.6 recipe: expected `→` after prerequisites, "
                    f"got {tok.kind.value}"
                ),
                position=tok.position,
            )
        self.advance()  # consume ARROW
        # Right-hand side: the target itself (possibly an alias of the
        # header target -- we accept either spelling) followed by
        # optional `+ Λ·Ω_side` leakage terms.
        if self.current().kind != TokenKind.OMEGA:
            tok = self.current()
            raise CompilerError(
                CompilerStage.PARSING,
                (
                    f"CAS v7.6 recipe: expected `Ω_name` on right-hand side "
                    f"of `→`, got {tok.kind.value}"
                ),
                position=tok.position,
            )
        self.parse_production_target()  # consumed but implied to equal the header target
        leakages: list[LeakageAnnotation] = []
        while self.current().kind == TokenKind.PLUS:
            self.advance()
            # A leakage entry may be shaped as `Λ·Ω_side` or as
            # `coeff·Λ·Ω_side` / `coeff·Ω_side`. Accept the three shapes
            # uniformly: if a NUMBER-TIMES prefix appears, consume it
            # and use it as the leakage coefficient; otherwise default
            # to 1.0.
            coeff: float = 1.0
            if self.current().kind == TokenKind.NUMBER:
                num_tok = self.advance()
                try:
                    coeff = float(num_tok.value)
                except ValueError as exc:  # pragma: no cover
                    raise CompilerError(
                        CompilerStage.PARSING,
                        f"CAS v7.6 leakage: malformed coefficient {num_tok.value!r}",
                        position=num_tok.position,
                    ) from exc
                if coeff <= 0:
                    raise CompilerError(
                        CompilerStage.PARSING,
                        (
                            f"CAS v7.6 leakage: coefficient must be "
                            f"positive, got {coeff}"
                        ),
                        position=num_tok.position,
                    )
                if self.current().kind != TokenKind.TIMES:
                    tok = self.current()
                    raise CompilerError(
                        CompilerStage.PARSING,
                        (
                            f"CAS v7.6 leakage: expected `·` after "
                            f"coefficient, got {tok.kind.value}"
                        ),
                        position=tok.position,
                    )
                self.advance()
            if self.current().kind == TokenKind.LAMBDA_TOK:
                entry = self._parse_leakage_annotation()
                entry.coefficient = coeff
                leakages.append(entry)
            elif self.current().kind == TokenKind.OMEGA:
                # Short form: `coeff · Ω_side` with no explicit Λ marker.
                side = self.parse_production_target()
                leakages.append(LeakageAnnotation(coefficient=coeff, target=side))
            else:
                tok = self.current()
                raise CompilerError(
                    CompilerStage.PARSING,
                    (
                        f"CAS v7.6 recipe RHS: expected `Λ·Ω_side` or "
                        f"`Ω_side` leakage term, got {tok.kind.value}"
                    ),
                    position=tok.position,
                )
        return RecipeLiteral(
            target=target,
            prerequisites=prerequisites,
            leakages=leakages,
            catalysts=catalysts,
            inhibitors=inhibitors,
        )

    def parse_yield_expression(self) -> YieldExpression:
        """Parse a v7.6 yield query:

          Y_T(Ω | S, Θ)   -> kind="theoretical"
          Y_A(Ω)          -> kind="actual"
          η(Ω)            -> kind="efficiency"

        The compiler accepts the full shape from Clarification 9 Section 3
        but does NOT evaluate the query. The Rust cas-engine computes yield,
        efficiency, and limiting-reagent analysis against the parsed AST.
        """
        head = self.advance()
        if head.kind == TokenKind.YIELD_T:
            kind = "theoretical"
        elif head.kind == TokenKind.YIELD_A:
            kind = "actual"
        elif head.kind == TokenKind.ETA_TOK:
            kind = "efficiency"
        else:  # pragma: no cover - parse_primary gates the entry
            raise CompilerError(
                CompilerStage.PARSING,
                f"CAS v7.6: unexpected yield-query head {head.kind.value}",
                position=head.position,
            )
        self.expect(TokenKind.LPAREN)
        if self.current().kind != TokenKind.OMEGA:
            tok = self.current()
            raise CompilerError(
                CompilerStage.PARSING,
                (
                    f"CAS v7.6 yield query: expected `Ω_...` as first "
                    f"argument, got {tok.kind.value}"
                ),
                position=tok.position,
            )
        target = self.parse_production_target()
        state: Any | None = None
        recipe: Any | None = None
        if self.current().kind == TokenKind.PIPE:
            # `Y_T(Ω | S, Θ)` form: pipe separator introduces the state
            # vector and recipe reference(s). Only Y_T uses this form in
            # Section 3, but we accept the syntax for any yield query so
            # the parser stays uniform.
            self.advance()
            state = self.parse_primary()
            if self.current().kind == TokenKind.COMMA:
                self.advance()
                recipe = self.parse_primary()
        self.expect(TokenKind.RPAREN)
        return YieldExpression(kind=kind, target=target, state=state, recipe=recipe)

    def parse_state_vector(self) -> StateVectorLiteral:
        """Parse a v7.6 state-vector literal `S = {X_1: x_1, ..., X_n: x_n}`.

        Each entry is a v7.5 primitive followed by `:` and a numeric
        activation quantity. The compiler captures the mapping faithfully;
        no validation beyond syntax is performed here.
        """
        self.expect(TokenKind.STATE_VECTOR)
        self.expect(TokenKind.EQUALS)
        self.expect(TokenKind.LBRACE)
        entries: list[tuple[Any, float]] = []
        if self.current().kind != TokenKind.RBRACE:
            entries.append(self._parse_state_vector_entry())
            while self.current().kind == TokenKind.COMMA:
                self.advance()
                entries.append(self._parse_state_vector_entry())
        self.expect(TokenKind.RBRACE)
        return StateVectorLiteral(entries=entries)

    def _parse_state_vector_entry(self) -> tuple[Any, float]:
        primitive = self.parse_primary()
        self.expect(TokenKind.COLON)
        num = self.current()
        if num.kind != TokenKind.NUMBER:
            raise CompilerError(
                CompilerStage.PARSING,
                (
                    f"CAS v7.6 state-vector entry: expected numeric "
                    f"activation, got {num.kind.value}"
                ),
                position=num.position,
            )
        self.advance()
        try:
            value = float(num.value)
        except ValueError as exc:  # pragma: no cover
            raise CompilerError(
                CompilerStage.PARSING,
                f"CAS v7.6 state-vector entry: malformed number {num.value!r}",
                position=num.position,
            ) from exc
        return primitive, value


def _collect_times_chain(node: Any) -> list[Any] | None:
    """If `node` is a left-associative `×` BinaryExpr chain composed only of
    StateLiteral operands, return the list of operands in source order.
    Otherwise return None — the chain is not a candidate for Rule 4 analysis.

    The parser builds `×` chains left-associatively, so `A × B × C` becomes
    `BinaryExpr(×, BinaryExpr(×, A, B), C)`. We walk the left spine to
    recover the flat operand list.
    """
    operands: list[Any] = []

    def walk(n: Any) -> bool:
        if isinstance(n, BinaryExpr) and n.op == "TIMES":
            if not walk(n.left):
                return False
            if not walk(n.right):
                return False
            return True
        if isinstance(n, StateLiteral):
            operands.append(n)
            return True
        # Any non-Times non-State node breaks the candidate chain — the
        # expression is not a pure state-literal `×` chain, so Rule 4
        # (which applies specifically to same-Noetic multi-register state
        # chains) does not apply.
        return False

    return operands if walk(node) else None


def _rule4_check_times_chain(node: Any) -> None:
    """CAS v7.7 Clarification 10 §4 admissibility enforcement.

    For a `×` chain of StateLiteral operands, reject when ALL operands share
    the same Noetic × Domain × Drive core but differ in register. The Rule
    requires either:
      (a) explicit emergent-result assignment via `= X|Ω` (parse layer
          wraps such a chain in EmergentResult, so this function is never
          called on licensed chains), OR
      (b) rewrite to `+` (co-presence) or `|⟨…⟩` (specification).

    Chains with different Noetics, different Domains, different Drives, or
    where at least one operand carries a register-set (tuple register) are
    valid cross-register integration and are NOT flagged.
    """
    operands = _collect_times_chain(node)
    if operands is None or len(operands) < 2:
        return
    # All operands must be StateLiterals — guaranteed by _collect_times_chain.
    # Extract the (operator, domain, drive) core and the set of registers.
    cores = {(op.operator, op.domain, op.drive) for op in operands}
    if len(cores) != 1:
        # Different Noetic / Domain / Drive somewhere in the chain — valid
        # cross-state integration under v7.4 monoid semantics.
        return
    # Same core across the chain. Rule 4 applies only when the operands
    # differ solely in register AND at least one carries a register
    # specification. Collect registers; any operand carrying a tuple
    # register (register-set) is already an explicit specification, so we
    # exempt the chain (author has chosen the `|⟨…⟩` form deliberately).
    registers: list[Any] = []
    for op in operands:
        if isinstance(op.register, tuple):
            return
        registers.append(op.register)
    # Require at least two distinct single-register specifications to flag.
    distinct = {r for r in registers if r is not None}
    if len(distinct) < 2:
        # Either all register-neutral (not a multi-register case) or only
        # one register value appears — neither triggers Rule 4.
        return
    # Construct a diagnostic rendering of the offending chain for the
    # error message. We use the canonical compact form the author likely
    # typed: `^n^D|R1 × ^n^D|R2 × ...`.
    parts: list[str] = []
    for op in operands:
        core = f"^{op.operator}^{op.domain}"
        if op.drive is not None:
            core = f"{core}_{{F{op.drive}}}"
        if op.register is not None:
            core = f"{core}|{op.register}"
        parts.append(core)
    rendered = " × ".join(parts)
    raise CompilerError(
        CompilerStage.TYPECHECK,
        (
            f"CAS v7.7 Clarification 10 Section 4 admissibility rule: "
            f"same-Noetic multi-register `×` expression is invalid by "
            f"default. Offending expression: `{rendered}`. The `×` "
            f"operator is reserved for genuine generative integration; "
            f"same-state multi-register co-presence must use `+` "
            f"(co-presence, e.g. `{parts[0]} + {parts[1]}`) or "
            f"`|⟨…⟩` (specification, e.g. "
            f"`^{operands[0].operator}^{operands[0].domain}|⟨"
            f"{','.join(str(r) for r in registers if r is not None)}⟩`). "
            f"If true integration into a fused state is intended, "
            f"assign a named emergent result: `({rendered}) = "
            f"^{operands[0].operator}^{operands[0].domain}|Ω`."
        ),
    )


def _infer(node: Any, warnings: list[str], env: TypeEnv | None = None) -> TypeInfo:
    env = env or TypeEnv()

    def require_stateish(info: TypeInfo, op_name: str) -> TypeInfo:
        if info.kind in {TypeKind.STATE, TypeKind.ANY}:
            return info
        raise CompilerError(
            CompilerStage.TYPECHECK,
            f"{op_name} is only defined for state expressions",
        )

    if isinstance(node, StateLiteral):
        if not 0 <= node.operator <= 9:
            raise CompilerError(
                CompilerStage.TYPECHECK,
                f"operator index must be 0-9, got {node.operator}",
            )
        if node.domain not in DOMAIN_NAMES:
            raise CompilerError(
                CompilerStage.TYPECHECK,
                f"domain must be one of {sorted(DOMAIN_NAMES)}, got {node.domain}",
            )
        if node.drive is not None and not 1 <= node.drive <= 7:
            raise CompilerError(
                CompilerStage.TYPECHECK,
                f"drive number must be 1-7, got F{node.drive}",
            )
        # CAS v7.5 register values are validated during parsing (_validate_register_token);
        # by the time we get here, any non-None value is already in VALID_REGISTERS.
        return TypeInfo(kind=TypeKind.STATE, domains=(node.domain,), singular=True)

    if isinstance(node, DriveLiteral):
        if not 1 <= node.drive <= 7:
            raise CompilerError(
                CompilerStage.TYPECHECK,
                f"drive number must be 1-7, got F{node.drive}",
            )
        return TypeInfo(kind=TypeKind.DRIVE, singular=True)

    if isinstance(node, StringLiteral):
        return TypeInfo(kind=TypeKind.STRING, singular=True)

    if isinstance(node, NumberLiteral):
        return TypeInfo(kind=TypeKind.NUMBER, singular=True)

    if isinstance(node, MetaSetLiteral):
        _meta_set_value(node.name)
        return TypeInfo(kind=TypeKind.META_SET, singular=True)

    if isinstance(node, TypedMetaSetLiteral):
        for element in node.elements:
            element_type = _infer(element, warnings, env)
            if element_type.kind not in {
                TypeKind.STATE,
                TypeKind.DRIVE,
                TypeKind.RELATION,
                TypeKind.RPM,
                TypeKind.FRACTAL,
                TypeKind.TUPLE,
                TypeKind.META_SET,
                TypeKind.META_SYMBOL,
                TypeKind.STRING,
                TypeKind.ANY,
            }:
                raise CompilerError(
                    CompilerStage.TYPECHECK,
                    (
                        f"{node.constructor}{{...}} elements must be CAS "
                        f"objects or meta-symbols, got {element_type.kind.value}"
                    ),
                )
        return TypeInfo(kind=TypeKind.META_SET, singular=True)

    if isinstance(node, TupleLiteral):
        element_types = [_infer(element, warnings, env) for element in node.elements]
        if node.constructor in {"Coordinate", "CASCoordinate"}:
            if len(element_types) != 4:
                raise CompilerError(
                    CompilerStage.TYPECHECK,
                    f"{node.constructor}{{...}} requires 4 slots: Noetic, Domain, Drive, Register",
                )
            expected = (
                TypeKind.STATE,
                TypeKind.META_SYMBOL,
                TypeKind.DRIVE,
                TypeKind.META_SYMBOL,
            )
            for index, (actual, expected_kind) in enumerate(zip(element_types, expected), start=1):
                if actual.kind not in {expected_kind, TypeKind.ANY}:
                    raise CompilerError(
                        CompilerStage.TYPECHECK,
                        (
                            f"{node.constructor} slot {index} must be "
                            f"{expected_kind.value}, got {actual.kind.value}"
                        ),
                    )
            domain_node = node.elements[1]
            register_node = node.elements[3]
            if not (isinstance(domain_node, MetaSymbol) and domain_node.symbol_kind == "domain"):
                raise CompilerError(
                    CompilerStage.TYPECHECK,
                    f"{node.constructor} slot 2 must be a processing Domain symbol (P, C, E, or O)",
                )
            if not (isinstance(register_node, MetaSymbol) and register_node.symbol_kind == "register"):
                raise CompilerError(
                    CompilerStage.TYPECHECK,
                    f"{node.constructor} slot 4 must be a Register symbol (T, A, f, or E)",
                )
        return TypeInfo(kind=TypeKind.TUPLE, singular=True)

    if isinstance(node, EmptySetLiteral):
        return TypeInfo(kind=TypeKind.META_SET, singular=True)

    if isinstance(node, MetaSymbol):
        return TypeInfo(kind=TypeKind.META_SYMBOL, singular=True)

    if isinstance(node, CardinalityExpr):
        collection_type = _infer(node.collection, warnings, env)
        if collection_type.kind not in {TypeKind.META_SET, TypeKind.ANY}:
            raise CompilerError(
                CompilerStage.TYPECHECK,
                f"cardinality `|X|` requires a meta-set, got {collection_type.kind.value}",
            )
        return TypeInfo(kind=TypeKind.NUMBER, singular=True)

    if isinstance(node, MetaAssertion):
        left = _infer(node.left, warnings, env)
        right = _infer(node.right, warnings, env)
        if node.op in {"MEMBER", "NOT_MEMBER"}:
            if right.kind not in {TypeKind.META_SET, TypeKind.ANY}:
                raise CompilerError(
                    CompilerStage.TYPECHECK,
                    f"{node.op} requires a meta-set on the right",
                )
            return TypeInfo(kind=TypeKind.META_ASSERTION, singular=True)
        if node.op in {"SUBSET", "SUBSET_EQ", "SUPERSET", "SUPERSET_EQ"}:
            if left.kind not in {TypeKind.META_SET, TypeKind.ANY}:
                raise CompilerError(
                    CompilerStage.TYPECHECK,
                    f"{node.op} requires a meta-set on the left",
                )
            if right.kind not in {TypeKind.META_SET, TypeKind.ANY}:
                raise CompilerError(
                    CompilerStage.TYPECHECK,
                    f"{node.op} requires a meta-set on the right",
                )
            return TypeInfo(kind=TypeKind.META_ASSERTION, singular=True)
        if node.op == "EQUALS":
            if left.kind not in {TypeKind.NUMBER, TypeKind.ANY}:
                raise CompilerError(
                    CompilerStage.TYPECHECK,
                    f"{node.op} requires a numeric left operand",
                )
            if right.kind not in {TypeKind.NUMBER, TypeKind.ANY}:
                raise CompilerError(
                    CompilerStage.TYPECHECK,
                    f"{node.op} requires a numeric right operand",
                )
            return TypeInfo(kind=TypeKind.META_ASSERTION, singular=True)
        raise CompilerError(CompilerStage.TYPECHECK, f"unsupported meta assertion {node.op}")

    # CAS v7.6 (Clarification 9): production-semantics AST nodes are
    # parse-only from the Python compiler's perspective. We type them as
    # ANY so they compose freely with recipe-algebra forms at the
    # additive / multiplicative layer (`Θ(Ω1) + Θ(Ω2)`,
    # `Θ(Ω_full) − Θ(Ω_achieved)`, `Θ(Ω_int) ∘ Θ(Ω_final)`). The Rust
    # cas-engine enforces whatever stronger typing it needs when it
    # consumes the AST.
    if isinstance(node, (ProductionTargetLiteral, RecipeLiteral, StateVectorLiteral, YieldExpression)):
        if isinstance(node, RecipeLiteral) and node.prerequisites:
            # Light sanity check: recipe prerequisites should all have
            # positive coefficients. The parser already enforces this on
            # literal recipes; we re-check here to guard against AST
            # construction from non-parser paths (e.g. future builders).
            for prereq in node.prerequisites:
                if prereq.coefficient <= 0:
                    raise CompilerError(
                        CompilerStage.TYPECHECK,
                        (
                            f"CAS v7.6 recipe: coefficient must be "
                            f"positive, got {prereq.coefficient}"
                        ),
                    )
        return TypeInfo(kind=TypeKind.ANY)

    if isinstance(node, Identifier):
        if node.name in env.vars:
            return env.vars[node.name]
        raise CompilerError(CompilerStage.TYPECHECK, f"undefined variable {node.name}")

    if isinstance(node, FractalLiteral):
        if not node.sequence:
            raise CompilerError(CompilerStage.TYPECHECK, "fractal sequence cannot be empty")
        if any(not 0 <= part <= 9 for part in node.sequence):
            raise CompilerError(
                CompilerStage.TYPECHECK,
                f"fractal sequence must use operator indices 0-9, got {node.sequence}",
            )
        return TypeInfo(kind=TypeKind.FRACTAL, singular=True)

    if isinstance(node, RpmCall):
        inner = _infer(node.expr, warnings, env)
        if inner.kind not in {TypeKind.STATE, TypeKind.DRIVE, TypeKind.ANY}:
            raise CompilerError(
                CompilerStage.TYPECHECK,
                "RPM(...) accepts only a state or drive literal",
            )
        return TypeInfo(kind=TypeKind.RPM, singular=True)

    if isinstance(node, CallExpr):
        if node.callee in BUILTIN_NAMES:
            arg_types = [_infer(arg, warnings, env) for arg in node.args]
            if node.callee == "ohm_scale" or node.callee in OHM_CONSTRUCTORS or node.callee in OHM_OPERATIONS:
                return _infer_cas_ohm_call(node.callee, arg_types)
            if node.callee in {"dominant_state", "dominant_domain", "dominant_operator"}:
                if len(arg_types) != 1:
                    raise CompilerError(
                        CompilerStage.TYPECHECK,
                        f"builtin {node.callee} expects 1 argument, got {len(arg_types)}",
                    )
                _assert_type_compatible(
                    arg_types[0],
                    TypeInfo(kind=TypeKind.STATE, singular=True),
                    context=f"builtin {node.callee}",
                )
                return TypeInfo(kind=TypeKind.STRING, singular=True)
            if node.callee == "compose":
                if len(arg_types) != 2:
                    raise CompilerError(
                        CompilerStage.TYPECHECK,
                        f"builtin {node.callee} expects 2 arguments, got {len(arg_types)}",
                    )
                _assert_type_compatible(
                    arg_types[0],
                    TypeInfo(kind=TypeKind.STATE, singular=True),
                    context="builtin compose arg1",
                )
                _assert_type_compatible(
                    arg_types[1],
                    TypeInfo(kind=TypeKind.STATE, singular=True),
                    context="builtin compose arg2",
                )
                if (
                    arg_types[0].kind != TypeKind.ANY
                    and arg_types[1].kind != TypeKind.ANY
                    and arg_types[0].domains
                    and arg_types[1].domains
                    and arg_types[0].domains != arg_types[1].domains
                ):
                    raise CompilerError(CompilerStage.TYPECHECK, "builtin compose requires both states to share a domain")
                return TypeInfo(kind=TypeKind.STATE, domains=arg_types[0].domains or arg_types[1].domains, singular=True)
            if node.callee == "rpm_of":
                if len(arg_types) != 1:
                    raise CompilerError(
                        CompilerStage.TYPECHECK,
                        f"builtin {node.callee} expects 1 argument, got {len(arg_types)}",
                    )
                if arg_types[0].kind not in {TypeKind.STATE, TypeKind.DRIVE, TypeKind.ANY}:
                    raise CompilerError(CompilerStage.TYPECHECK, "builtin rpm_of expects a state or drive argument")
                return TypeInfo(kind=TypeKind.RPM, singular=True)
            if node.callee == "fractal":
                if len(arg_types) < 2:
                    raise CompilerError(CompilerStage.TYPECHECK, "builtin fractal expects at least 2 arguments")
                domains: tuple[str, ...] = ()
                for index, arg_type in enumerate(arg_types, start=1):
                    if arg_type.kind not in {TypeKind.STATE, TypeKind.FRACTAL, TypeKind.ANY}:
                        raise CompilerError(
                            CompilerStage.TYPECHECK,
                            f"builtin fractal argument {index} must be a state or fractal",
                        )
                    if domains == () and arg_type.domains:
                        domains = arg_type.domains
                return TypeInfo(kind=TypeKind.FRACTAL, domains=domains, singular=True)
            if node.callee in {"Pullback", "Product", "Union", "Intersection", "Difference"}:
                if len(arg_types) != 2:
                    raise CompilerError(
                        CompilerStage.TYPECHECK,
                        f"builtin {node.callee} expects 2 arguments, got {len(arg_types)}",
                    )
                for index, arg_type in enumerate(arg_types, start=1):
                    if arg_type.kind not in {TypeKind.META_SET, TypeKind.ANY}:
                        raise CompilerError(
                            CompilerStage.TYPECHECK,
                            f"builtin {node.callee} argument {index} must be a meta_set",
                        )
                return TypeInfo(kind=TypeKind.META_SET, singular=True)
            if node.callee in {"CoverOf", "PartitionOf"}:
                if len(arg_types) < 2:
                    raise CompilerError(
                        CompilerStage.TYPECHECK,
                        f"builtin {node.callee} expects a base meta_set plus at least one family member",
                    )
                for index, arg_type in enumerate(arg_types, start=1):
                    if arg_type.kind not in {TypeKind.META_SET, TypeKind.ANY}:
                        raise CompilerError(
                            CompilerStage.TYPECHECK,
                            f"builtin {node.callee} argument {index} must be a meta_set",
                        )
                return TypeInfo(kind=TypeKind.META_SET, singular=True)
        if node.callee not in env.funcs:
            raise CompilerError(CompilerStage.TYPECHECK, f"undefined function {node.callee}")
        signature = env.funcs[node.callee]
        if len(signature.param_types) != len(node.args):
            raise CompilerError(
                CompilerStage.TYPECHECK,
                f"function {node.callee} expects {len(signature.param_types)} arguments, got {len(node.args)}",
            )
        for index, (arg, expected) in enumerate(zip(node.args, signature.param_types, strict=True), start=1):
            actual = _infer(arg, warnings, env)
            _assert_type_compatible(actual, expected, context=f"function {node.callee} argument {index}")
        if any(param.kind == TypeKind.ANY for param in signature.param_types) or signature.return_type.kind == TypeKind.ANY:
            warnings.append(f"function {node.callee}(...) contains inferred any-typed contracts; prefer explicit annotations")
        return signature.return_type

    if isinstance(node, EmergentResult):
        # CAS v7.7 Clarification 10 §4: named-emergent-result wrapper.
        # The inner expression is a licensed ×-chain (Rule 4 bypassed).
        # Mark the inner tree as Rule 4-exempt by carrying a marker through
        # the env's vars dictionary under a reserved key so recursive
        # _infer calls for the inner chain skip the Rule 4 check. The
        # marker is cleared after inference so subsequent top-level
        # statements in the same program are unaffected.
        env.vars["__cas_v77_rule4_exempt__"] = TypeInfo(kind=TypeKind.ANY)
        try:
            return _infer(node.inner, warnings, env)
        finally:
            env.vars.pop("__cas_v77_rule4_exempt__", None)

    if isinstance(node, BinaryExpr):
        # CAS v7.7 Clarification 10 §4: Rule 4 admissibility for same-Noetic
        # multi-register `×`. Evaluated before operand inference so the
        # diagnostic fires with a framework-aware message rather than a
        # generic typecheck error on an intermediate product. Skipped when
        # the enclosing scope is already a licensed EmergentResult wrapper.
        if node.op == "TIMES" and "__cas_v77_rule4_exempt__" not in env.vars:
            _rule4_check_times_chain(node)
        left = _infer(node.left, warnings, env)
        right = _infer(node.right, warnings, env)

        if node.op in {"PLUS", "MINUS"}:
            # + and - are syntactic assemblers: they work on states, drives, and RPM
            allowed = {TypeKind.STATE, TypeKind.DRIVE, TypeKind.RPM, TypeKind.ANY}
            if left.kind not in allowed or right.kind not in allowed:
                raise CompilerError(
                    CompilerStage.TYPECHECK,
                    f"{node.op} is only defined for state, drive, or RPM expressions",
                )
            # If both are states, produce a state; otherwise produce a program
            if left.kind in {TypeKind.STATE, TypeKind.ANY} and right.kind in {TypeKind.STATE, TypeKind.ANY}:
                domains = tuple(sorted(set(left.domains) | set(right.domains)))
                return TypeInfo(kind=TypeKind.STATE, domains=domains, singular=False)
            # Mixed types: produce a program-like result
            return TypeInfo(kind=TypeKind.STATE, domains=(), singular=False)

        if node.op in {"UNION", "INTERSECTION", "SET_DIFF"}:
            if left.kind not in {TypeKind.META_SET, TypeKind.ANY}:
                raise CompilerError(
                    CompilerStage.TYPECHECK,
                    f"{node.op} requires a meta-set on the left",
                )
            if right.kind not in {TypeKind.META_SET, TypeKind.ANY}:
                raise CompilerError(
                    CompilerStage.TYPECHECK,
                    f"{node.op} requires a meta-set on the right",
                )
            return TypeInfo(kind=TypeKind.META_SET, singular=True)

        if node.op in {"TIMES", "DIVIDE"}:
            require_stateish(left, node.op)
            require_stateish(right, node.op)
            if left.kind != TypeKind.ANY and not left.singular:
                raise CompilerError(
                    CompilerStage.TYPECHECK,
                    f"{node.op} requires singular state operands",
                )
            if right.kind != TypeKind.ANY and not right.singular:
                raise CompilerError(
                    CompilerStage.TYPECHECK,
                    f"{node.op} requires singular state operands",
                )
            # DIVIDE requires same domain; TIMES allows domain descent (P×C=C)
            if node.op == "DIVIDE" and (
                left.kind != TypeKind.ANY
                and right.kind != TypeKind.ANY
                and left.domains != right.domains
            ):
                raise CompilerError(
                    CompilerStage.TYPECHECK,
                    "DIVIDE requires both states to share a domain",
                )
            domains = left.domains or right.domains
            return TypeInfo(kind=TypeKind.STATE, domains=domains, singular=True)

        if node.op == "CIRC":
            if left.kind in {TypeKind.STATE, TypeKind.ANY} and right.kind in {TypeKind.STATE, TypeKind.ANY}:
                if left.kind != TypeKind.ANY and not left.singular:
                    raise CompilerError(CompilerStage.TYPECHECK, "CIRC requires singular state operands")
                if right.kind != TypeKind.ANY and not right.singular:
                    raise CompilerError(CompilerStage.TYPECHECK, "CIRC requires singular state operands")
                if (
                    left.kind != TypeKind.ANY
                    and right.kind != TypeKind.ANY
                    and left.domains
                    and right.domains
                    and left.domains != right.domains
                ):
                    # The canon book nests across Domains (seven written examples, among them
                    # `^7^C|A ∘ ^7^O|E` and Template 23 `CO-7^P ∘ CO-7^C ∘ CO-7^E ∘ CO-7^O`).
                    # The old refusal contradicted the book and was enforced on this one path
                    # only (a fractal operand, an any-typed parameter or fractal(...) slipped past it).
                    if NESTING_CROSS_DOMAIN_WARNING not in warnings:
                        warnings.append(NESTING_CROSS_DOMAIN_WARNING)
                return TypeInfo(kind=TypeKind.FRACTAL, domains=left.domains or right.domains, singular=True)
            if left.domains and right.domains and left.domains != right.domains and NESTING_CROSS_DOMAIN_WARNING not in warnings:
                warnings.append(NESTING_CROSS_DOMAIN_WARNING)          # the same warning on the fractal paths (review finding)
            if left.kind == TypeKind.FRACTAL and right.kind in {TypeKind.STATE, TypeKind.ANY}:
                return TypeInfo(kind=TypeKind.FRACTAL, domains=right.domains, singular=True)
            if left.kind in {TypeKind.STATE, TypeKind.ANY} and right.kind == TypeKind.FRACTAL:
                return TypeInfo(kind=TypeKind.FRACTAL, domains=left.domains, singular=True)
            if left.kind == TypeKind.FRACTAL and right.kind == TypeKind.FRACTAL:
                return TypeInfo(kind=TypeKind.FRACTAL, domains=left.domains or right.domains, singular=True)
            raise CompilerError(
                CompilerStage.TYPECHECK,
                "CIRC is only defined for state and fractal expressions",
            )

        if node.op in {"ARROW", "LARROW", "BIARROW"}:
            # Arrow accepts any state-typed operand: singular states,
            # × compositions (resolve to singular), and + compositions
            # (co-present states, valid if they share a domain).
            allowed_kinds = {TypeKind.STATE, TypeKind.ANY}
            if left.kind not in allowed_kinds:
                raise CompilerError(
                    CompilerStage.TYPECHECK,
                    f"{node.op} requires state-typed operands (got {left.kind.value})",
                )
            if right.kind not in allowed_kinds:
                raise CompilerError(
                    CompilerStage.TYPECHECK,
                    f"{node.op} requires state-typed operands (got {right.kind.value})",
                )
            # Domain descent check: use the dominant (first) domain from each side
            if (
                left.kind != TypeKind.ANY
                and right.kind != TypeKind.ANY
                and left.domains
                and right.domains
            ):
                left_domain = left.domains[0]
                right_domain = right.domains[0]
                if node.op == "ARROW" and DOMAIN_ORDER.get(left_domain, 0) > DOMAIN_ORDER.get(right_domain, 0):
                    raise CompilerError(
                        CompilerStage.TYPECHECK,
                        f"domain descent violated: {left_domain} cannot descend to {right_domain}",
                    )
                if node.op == "LARROW" and DOMAIN_ORDER.get(right_domain, 0) > DOMAIN_ORDER.get(left_domain, 0):
                    raise CompilerError(
                        CompilerStage.TYPECHECK,
                        f"reverse dependency violated: {right_domain} cannot descend to {left_domain}",
                    )
                if node.op == "BIARROW" and left_domain != right_domain:
                    raise CompilerError(
                        CompilerStage.TYPECHECK,
                        "bidirectional relation requires matching domains",
                    )
            return TypeInfo(kind=TypeKind.RELATION, singular=False)

    if isinstance(node, LetStatement):
        expr_type = _infer(node.expr, warnings, env)
        if node.annotation is not None:
            _assert_type_compatible(expr_type, node.annotation, context=f"binding {node.name}")
            expr_type = node.annotation
        env.vars[node.name] = expr_type
        return TypeInfo(kind=TypeKind.VOID)

    if isinstance(node, FunctionDef):
        if node.name in env.funcs or node.name in BUILTIN_NAMES:
            raise CompilerError(CompilerStage.TYPECHECK, f"function {node.name} already defined")
        param_types = tuple(node.param_types or [TypeInfo(kind=TypeKind.ANY) for _ in node.params])
        provisional_return = node.return_type or TypeInfo(kind=TypeKind.ANY)
        env.funcs[node.name] = FunctionSignature(param_types=param_types, return_type=provisional_return)
        local_env = TypeEnv(vars=dict(env.vars), funcs=dict(env.funcs), module_dir=env.module_dir, import_stack=env.import_stack)
        for param, param_type in zip(node.params, param_types, strict=True):
            local_env.vars[param] = param_type
        body_type = _infer(node.body, warnings, local_env)
        if node.return_type is not None:
            _assert_type_compatible(body_type, node.return_type, context=f"function {node.name} return")
        env.funcs[node.name] = FunctionSignature(param_types=param_types, return_type=node.return_type or body_type)
        return TypeInfo(kind=TypeKind.FUNCTION)

    if isinstance(node, ExportStatement):
        inner_type = _infer(node.statement, warnings, env)
        env.exports.add(node.statement.name)
        return inner_type

    if isinstance(node, UseStatement):
        resolved = node.path
        if env.module_dir is not None and not os.path.isabs(resolved):
            resolved = os.path.join(env.module_dir, resolved)
        resolved = os.path.abspath(resolved)
        if resolved in env.import_stack:
            raise CompilerError(CompilerStage.TYPECHECK, f"cyclic import detected for {resolved}")
        if not os.path.exists(resolved):
            raise CompilerError(CompilerStage.TYPECHECK, f"import target not found: {resolved}")
        env.import_stack.add(resolved)
        try:
            with open(resolved, encoding="utf-8") as handle:
                source = handle.read()
            imported_env = TypeEnv(
                module_dir=os.path.dirname(resolved),
                import_stack=env.import_stack,
            )
            imported_ast = Parser(lex(source)).parse()
            _infer(imported_ast, warnings, imported_env)
            imported_names = imported_env.exports or set(imported_env.vars) | set(imported_env.funcs)
            for name in imported_names:
                if name in imported_env.vars:
                    env.vars[name] = imported_env.vars[name]
                if name in imported_env.funcs:
                    env.funcs[name] = imported_env.funcs[name]
        finally:
            env.import_stack.discard(resolved)
        return TypeInfo(kind=TypeKind.VOID)

    if isinstance(node, Program):
        if not node.statements:
            raise CompilerError(CompilerStage.TYPECHECK, "program cannot be empty")
        last_type = TypeInfo(kind=TypeKind.VOID)
        for stmt in node.statements:
            last_type = _infer(stmt, warnings, env)
        return TypeInfo(kind=TypeKind.PROGRAM, domains=last_type.domains, singular=last_type.singular)

    raise CompilerError(CompilerStage.TYPECHECK, f"unsupported AST node {type(node).__name__}")


def lower(node: Any) -> list[Instruction]:
    bytecode: list[Instruction] = []

    def emit(expr: Any) -> None:
        if isinstance(expr, StateLiteral):
            bytecode.append(
                Instruction(
                    "PUSH_STATE",
                    {
                        "operator": expr.operator,
                        "domain": expr.domain,
                        "drive": expr.drive,
                        # CAS v7.5 register metadata (Clarification 8). None
                        # means register-neutral (v7.4-compatible).
                        "register": expr.register,
                        "drive_register": expr.drive_register,
                        "domain_explicit": expr.domain_explicit,
                    },
                )
            )
            return
        if isinstance(expr, DriveLiteral):
            bytecode.append(
                Instruction(
                    "PUSH_DRIVE",
                    {
                        "drive": expr.drive,
                        "register": expr.register,
                        # CAS v7.6 Section 4 drive-in-domain shorthand:
                        # surface the domain when present so the runtime
                        # DriveLiteral reconstructed downstream carries the
                        # same v7.6 metadata.
                        "domain": expr.domain,
                    },
                )
            )
            return
        if isinstance(expr, StringLiteral):
            bytecode.append(Instruction("PUSH_STRING", expr.value))
            return
        if isinstance(expr, NumberLiteral):
            bytecode.append(Instruction("PUSH_NUMBER", expr.value))
            return
        if isinstance(expr, MetaSetLiteral):
            bytecode.append(Instruction("PUSH_META_SET", {"name": expr.name}))
            return
        if isinstance(expr, TypedMetaSetLiteral):
            for element in expr.elements:
                emit(element)
            bytecode.append(
                Instruction(
                    "BUILD_META_SET",
                    {
                        "constructor": expr.constructor,
                        "element_type": expr.element_type,
                        "count": len(expr.elements),
                    },
                )
            )
            return
        if isinstance(expr, TupleLiteral):
            for element in expr.elements:
                emit(element)
            bytecode.append(
                Instruction(
                    "BUILD_TUPLE",
                    {
                        "constructor": expr.constructor,
                        "count": len(expr.elements),
                    },
                )
            )
            return
        if isinstance(expr, EmptySetLiteral):
            bytecode.append(Instruction("PUSH_META_SET", {"name": "EmptySet"}))
            return
        if isinstance(expr, MetaSymbol):
            bytecode.append(
                Instruction(
                    "PUSH_META_SYMBOL",
                    {"name": expr.name, "symbol_kind": expr.symbol_kind},
                )
            )
            return
        if isinstance(expr, CardinalityExpr):
            emit(expr.collection)
            bytecode.append(Instruction("CARDINALITY"))
            return
        if isinstance(expr, MetaAssertion):
            emit(expr.left)
            emit(expr.right)
            bytecode.append(Instruction("META_ASSERT", {"op": expr.op}))
            return
        # CAS v7.6 (Clarification 9): production-semantics literals lower to
        # opaque PUSH_* instructions. The runtime just wraps the AST in a
        # *Value dataclass so the parsed recipe/state-vector/yield query
        # survives into the final serialized artifact. The Rust cas-engine
        # performs yield / limiting-reagent / efficiency computation.
        if isinstance(expr, ProductionTargetLiteral):
            bytecode.append(Instruction("PUSH_PRODUCTION_TARGET", {"name": expr.name}))
            return
        if isinstance(expr, RecipeLiteral):
            bytecode.append(
                Instruction(
                    "PUSH_RECIPE",
                    {
                        "target": expr.target.name,
                        "prerequisites": [
                            {
                                "coefficient": prereq.coefficient,
                                "primitive": serialize_ast(prereq.primitive),
                            }
                            for prereq in expr.prerequisites
                        ],
                        "leakages": [
                            {
                                "coefficient": leak.coefficient,
                                "target": leak.target.name,
                            }
                            for leak in expr.leakages
                        ],
                        "catalysts": [cat.name for cat in expr.catalysts],
                        "inhibitors": [inh.name for inh in expr.inhibitors],
                    },
                )
            )
            return
        if isinstance(expr, StateVectorLiteral):
            bytecode.append(
                Instruction(
                    "PUSH_STATE_VECTOR",
                    {
                        "entries": [
                            {
                                "primitive": serialize_ast(prim),
                                "activation": value,
                            }
                            for prim, value in expr.entries
                        ]
                    },
                )
            )
            return
        if isinstance(expr, YieldExpression):
            bytecode.append(
                Instruction(
                    "PUSH_YIELD",
                    {
                        "yield_kind": expr.kind,
                        "target": expr.target.name,
                        "state": serialize_ast(expr.state) if expr.state is not None else None,
                        "recipe": serialize_ast(expr.recipe) if expr.recipe is not None else None,
                    },
                )
            )
            return
        if isinstance(expr, Identifier):
            bytecode.append(Instruction("LOAD_VAR", expr.name))
            return
        if isinstance(expr, FractalLiteral):
            bytecode.append(Instruction("PUSH_FRACTAL", expr.sequence))
            return
        if isinstance(expr, RpmCall):
            emit(expr.expr)
            bytecode.append(Instruction("RPM"))
            return
        if isinstance(expr, CallExpr):
            for arg in expr.args:
                emit(arg)
            bytecode.append(Instruction("CALL", {"name": expr.callee, "argc": len(expr.args)}))
            return
        if isinstance(expr, EmergentResult):
            # CAS v7.7 Clarification 10 §4: the inner ×-chain lowers
            # identically to a plain TIMES chain; the assigned_name is
            # attached by a follow-up ATTACH_EMERGENT_RESULT instruction
            # so the runtime value carries the emergent label into
            # serialization unchanged.
            emit(expr.inner)
            bytecode.append(
                Instruction(
                    "ATTACH_EMERGENT_RESULT",
                    {"assigned_name": expr.assigned_name},
                )
            )
            return
        if isinstance(expr, BinaryExpr):
            emit(expr.left)
            emit(expr.right)
            bytecode.append(Instruction(expr.op))
            return
        if isinstance(expr, LetStatement):
            emit(expr.expr)
            bytecode.append(
                Instruction(
                    "STORE_VAR",
                    {"name": expr.name, "annotation": expr.annotation},
                )
            )
            return
        if isinstance(expr, FunctionDef):
            body_bytecode = lower(expr.body)
            bytecode.append(
                Instruction(
                    "DEF_FUNC",
                    {
                        "name": expr.name,
                        "params": expr.params,
                        "param_types": expr.param_types,
                        "return_type": expr.return_type,
                        "body": body_bytecode,
                    },
                )
            )
            return
        if isinstance(expr, ExportStatement):
            emit(expr.statement)
            bytecode.append(Instruction("EXPORT_NAME", expr.statement.name))
            return
        if isinstance(expr, UseStatement):
            bytecode.append(Instruction("IMPORT", expr.path))
            return
        if isinstance(expr, Program):
            for index, statement in enumerate(expr.statements):
                emit(statement)
                if index < len(expr.statements) - 1:
                    bytecode.append(Instruction("EMIT_RESULT"))
            bytecode.append(Instruction("BUILD_PROGRAM_RESULT"))
            return
        raise CompilerError(CompilerStage.LOWERING, f"cannot lower {type(expr).__name__}")

    emit(node)
    return bytecode


def _merge_drives(left: dict[int, float], right: dict[int, float]) -> dict[int, float]:
    merged: dict[int, float] = dict(left)
    for key, value in right.items():
        merged[key] = merged.get(key, 0.0) + value
    return merged


def _value_matches_type(value: Any, expected: TypeInfo) -> bool:
    if expected.kind == TypeKind.ANY:
        return True
    if expected.kind == TypeKind.OHM_SCALE or expected.kind in OHM_TYPE_QUANTITIES:
        module = _load_cas_ohm()
        if expected.kind == TypeKind.OHM_SCALE:
            return isinstance(value, module.OhmScale)
        return isinstance(value, module.OhmQuantity) and value.quantity == OHM_TYPE_QUANTITIES[expected.kind]
    if expected.kind == TypeKind.STRING:
        return isinstance(value, str)
    if expected.kind == TypeKind.NUMBER:
        return isinstance(value, (int, float, CardinalityValue))
    if expected.kind == TypeKind.TUPLE:
        return isinstance(value, TupleValue)
    if expected.kind == TypeKind.META_SET:
        return isinstance(value, MetaSetValue)
    if expected.kind == TypeKind.META_SYMBOL:
        return isinstance(value, MetaSymbolValue)
    if expected.kind == TypeKind.META_ASSERTION:
        return isinstance(value, MetaAssertionValue)
    if expected.kind == TypeKind.DRIVE:
        return isinstance(value, DriveLiteral)
    if expected.kind == TypeKind.STATE:
        if not isinstance(value, StateValue):
            return False
        if expected.domains and value.dominant_domain() not in expected.domains:
            return False
        return True
    if expected.kind == TypeKind.RELATION:
        return isinstance(value, RelationValue)
    if expected.kind == TypeKind.RPM:
        return isinstance(value, RpmValue)
    if expected.kind == TypeKind.FRACTAL:
        return isinstance(value, FractalValue)
    if expected.kind == TypeKind.FUNCTION:
        return isinstance(value, FunctionValue)
    if expected.kind == TypeKind.PROGRAM:
        return isinstance(value, ProgramValue)
    if expected.kind == TypeKind.VOID:
        return value is None
    return True


def _require_meta_set_value(value: Any, *, context: str) -> MetaSetValue:
    if isinstance(value, MetaSetValue):
        return value
    raise CompilerError(
        CompilerStage.EXECUTION,
        f"{context} requires a meta-set value",
    )


def _numeric_value(value: Any, *, context: str) -> int | float:
    if isinstance(value, CardinalityValue):
        return value.value
    if isinstance(value, (int, float)):
        return value
    raise CompilerError(
        CompilerStage.EXECUTION,
        f"{context} requires a numeric value",
    )


def _meta_member_keys(value: Any) -> frozenset[str]:
    if isinstance(value, StateValue):
        dominant = value.dominant_state()
        keys = {_state_key(dominant)}
        keys.add(_state_variant_key(value))
        if not value.domain_explicit and not value.explicit_drive:
            keys.add(f"CO-{value.dominant_operator()}")
        return frozenset(keys)
    if isinstance(value, DriveLiteral):
        keys = {_drive_key(value.drive)}
        if isinstance(value.register, str):
            keys.add(_drive_register_key(value.drive, value.register))
        return frozenset(keys)
    if isinstance(value, MetaSymbolValue):
        return frozenset({value.name})
    if isinstance(value, MetaSetValue):
        return frozenset({value.name})
    if isinstance(value, TupleValue):
        return frozenset({_tuple_key(value)})
    if isinstance(value, RelationValue):
        return frozenset({_relation_key(value)})
    if isinstance(value, FractalValue):
        return frozenset({_fractal_key(value)})
    if isinstance(value, str):
        return frozenset({value})
    return frozenset()


def _meta_value_label(value: Any) -> str:
    if isinstance(value, StateValue):
        if (
            value.explicit_drive
            or value.register is not None
            or value.drive_register is not None
            or value.emergent_register is not None
        ):
            return _state_variant_key(value)
        if not value.domain_explicit and not value.explicit_drive:
            return f"CO-{value.dominant_operator()}"
        return _state_key(value.dominant_state())
    if isinstance(value, DriveLiteral):
        base = _drive_key(value.drive)
        if isinstance(value.register, str):
            return _drive_register_key(value.drive, value.register)
        return base
    if isinstance(value, MetaSymbolValue):
        return value.name
    if isinstance(value, MetaSetValue):
        return value.name
    if isinstance(value, CardinalityValue):
        return f"|{value.collection.name}|"
    if isinstance(value, RelationValue):
        return _relation_key(value)
    if isinstance(value, TupleValue):
        return _tuple_key(value)
    if isinstance(value, FractalValue):
        return _fractal_key(value)
    return str(value)


def _meta_register_suffix(register: str | tuple[str, ...] | None) -> str:
    if isinstance(register, tuple):
        return "|<" + ",".join(register) + ">"
    if register is not None:
        return f"|{register}"
    return ""


def _state_variant_key(value: StateValue) -> str:
    label = _state_key(value.dominant_state())
    drive = max(value.drive_weights, key=value.drive_weights.get) if value.drive_weights else None
    if drive is not None and value.explicit_drive:
        drive_label = f"F{drive}{_meta_register_suffix(value.drive_register)}"
        label += f"_{{{drive_label}}}"
    elif value.drive_register is not None:
        label += f"_{{{_meta_register_suffix(value.drive_register).lstrip('|')}}}"
    label += _meta_register_suffix(value.register)
    if value.emergent_register is not None:
        label += f"={value.emergent_register}"
    return label


def _relation_key(value: RelationValue) -> str:
    arrows = {
        "dependency": "->",
        "results_from": "<-",
        "bidirectional": "<->",
    }
    return (
        f"{_meta_value_label(value.source)}"
        f"{arrows.get(value.relation, '->')}"
        f"{_meta_value_label(value.target)}"
    )


def _fractal_key(value: FractalValue) -> str:
    """Set-element key of a ring result: every term with its own Domain, Drive and Register, in written order.

    `^8^C_{F2}|A ∘ ^3^C|f` -> 'Phi<^8^C_{F2}|A:^3^C|f>'; the bare literal `Phi<8:3>` -> 'Phi<^8:^3>'. Two nestings that
    differ in any term's Domain, Drive, Register or order are different elements (review finding, 2026-09-21).
    """
    return "Phi<" + ":".join(term["label"] for term in _nesting_terms_of(value)) + ">"


def _tuple_key(value: TupleValue) -> str:
    opener = "Coordinate" if value.constructor in {"Coordinate", "CASCoordinate"} else "Tuple"
    return f"{opener}<" + ",".join(_meta_value_label(element) for element in value.elements) + ">"


def _canonical_meta_set_element(value: Any, element_type: str, *, context: str) -> str:
    label = _meta_value_label(value)
    if element_type == "meta":
        return label
    if element_type == "state_variant":
        if not isinstance(value, StateValue):
            raise CompilerError(
                CompilerStage.EXECUTION,
                f"{context} requires state_variant elements; got {_meta_value_label(value)}",
            )
        if (
            not value.domain_explicit
            and not value.explicit_drive
            and value.register is None
            and value.drive_register is None
        ):
            raise CompilerError(
                CompilerStage.EXECUTION,
                (
                    f"{context} requires explicit State variants; got "
                    f"{_meta_value_label(value)} (use ^n^D, ^n^D_{{Fk}}, "
                    f"or ^n^D|R rather than bare ^n)"
                ),
            )
        return _state_variant_key(value)
    if element_type == "relation":
        if not isinstance(value, RelationValue):
            raise CompilerError(
                CompilerStage.EXECUTION,
                f"{context} requires relation elements; got {_meta_value_label(value)}",
            )
        return _relation_key(value)
    if element_type == "meta_set":
        if not isinstance(value, MetaSetValue):
            raise CompilerError(
                CompilerStage.EXECUTION,
                f"{context} requires meta_set elements; got {_meta_value_label(value)}",
            )
        return value.name
    if element_type == "tuple":
        if not isinstance(value, TupleValue):
            raise CompilerError(
                CompilerStage.EXECUTION,
                f"{context} requires tuple elements; got {_meta_value_label(value)}",
            )
        return _tuple_key(value)

    universes = {
        "noetic": BUILTIN_META_SETS["Noetics"],
        "state": BUILTIN_META_SETS["States"],
        "drive": BUILTIN_META_SETS["Drives"],
        "domain": BUILTIN_META_SETS["Domains"],
        "register": BUILTIN_META_SETS["Registers"],
        "foundation": BUILTIN_META_SETS["Foundations"],
        "subfoundation": BUILTIN_META_SETS["SubFoundations"],
    }
    universe = universes.get(element_type)
    if universe is None:
        raise CompilerError(
            CompilerStage.EXECUTION,
            f"{context} uses unsupported meta-set element type {element_type!r}",
        )
    if label in universe:
        return label
    if element_type == "noetic":
        hint = "use bare Noetics such as ^2 or CO-2, not explicit states such as ^2^P"
    elif element_type == "state":
        hint = "use explicit Cognitive States such as ^2^P, P2, or C7"
    else:
        hint = f"use elements from {element_type} universe"
    raise CompilerError(
        CompilerStage.EXECUTION,
        f"{context} requires {element_type} elements; got {_meta_value_label(value)} ({hint})",
    )


def _build_typed_meta_set_value(
    constructor: str,
    element_type: str,
    values: list[Any],
) -> MetaSetValue:
    elements = frozenset(
        _canonical_meta_set_element(value, element_type, context=constructor)
        for value in values
    )
    name = f"{constructor}{{{', '.join(sorted(elements))}}}"
    return MetaSetValue(
        name=name,
        elements=elements,
        element_type=element_type,
        origin="literal",
    )


def _compatible_meta_set_element_type(left: MetaSetValue, right: MetaSetValue, *, op: str) -> str:
    if left.element_type == right.element_type:
        return left.element_type
    if left.element_type == "empty":
        return right.element_type
    if right.element_type == "empty":
        return left.element_type
    if left.element_type == "meta" or right.element_type == "meta":
        return "meta"
    raise CompilerError(
        CompilerStage.EXECUTION,
        (
            f"{op} requires compatible typed meta-sets "
            f"(got {left.element_type} and {right.element_type})"
        ),
    )


def _set_operation_value(op: str, left: MetaSetValue, right: MetaSetValue) -> MetaSetValue:
    element_type = _compatible_meta_set_element_type(left, right, op=op)
    if op == "UNION":
        elements = left.elements | right.elements
        symbol = UNICODE_UNION
    elif op in {"INTERSECTION", "PULLBACK"}:
        elements = left.elements & right.elements
        symbol = UNICODE_INTERSECTION if op == "INTERSECTION" else "Pullback"
    elif op == "SET_DIFF":
        elements = left.elements - right.elements
        element_type = left.element_type
        symbol = UNICODE_SET_MINUS
    else:
        raise CompilerError(CompilerStage.EXECUTION, f"unsupported set operation {op}")
    name = f"({left.name} {symbol} {right.name})"
    return MetaSetValue(name=name, elements=frozenset(elements), element_type=element_type, origin="derived")


def _product_value(left: MetaSetValue, right: MetaSetValue) -> MetaSetValue:
    elements = frozenset(f"Tuple<{a},{b}>" for a in sorted(left.elements) for b in sorted(right.elements))
    return MetaSetValue(
        name=f"Product({left.name}, {right.name})",
        elements=elements,
        element_type="tuple",
        origin="derived",
    )


def _cover_family_value(base: MetaSetValue, members: list[MetaSetValue], *, partition: bool) -> MetaSetValue:
    if not members:
        raise CompilerError(
            CompilerStage.EXECUTION,
            "CoverOf/PartitionOf requires at least one family member",
        )
    covered: set[str] = set()
    seen: set[str] = set()
    for member in members:
        _compatible_meta_set_element_type(base, member, op="CoverOf")
        if not member.elements.issubset(base.elements):
            raise CompilerError(
                CompilerStage.EXECUTION,
                f"{'PartitionOf' if partition else 'CoverOf'} member {member.name} is not a subset of base {base.name}",
            )
        if partition:
            overlap = seen & set(member.elements)
            if overlap:
                raise CompilerError(
                    CompilerStage.EXECUTION,
                    f"PartitionOf requires disjoint members; overlap: {sorted(overlap)}",
                )
            seen.update(member.elements)
        covered.update(member.elements)
    missing = base.elements - frozenset(covered)
    if missing:
        raise CompilerError(
            CompilerStage.EXECUTION,
            (
                f"{'PartitionOf' if partition else 'CoverOf'} does not cover "
                f"base {base.name}; missing {sorted(missing)}"
            )
        )
    name = f"{'PartitionOf' if partition else 'CoverOf'}({base.name}; {', '.join(member.name for member in members)})"
    return MetaSetValue(
        name=name,
        elements=frozenset(member.name for member in members),
        element_type="meta_set",
        origin="derived",
    )


def _evaluate_meta_assertion(op: str, left: Any, right: Any) -> MetaAssertionValue:
    if op in {"MEMBER", "NOT_MEMBER"}:
        right_set = _require_meta_set_value(right, context=op)
        member_keys = _meta_member_keys(left)
        base_holds = any(key in right_set.elements for key in member_keys)
        holds = not base_holds if op == "NOT_MEMBER" else base_holds
        symbol = UNICODE_NOT_MEMBER if op == "NOT_MEMBER" else UNICODE_MEMBER
        verb = "is not a member of" if op == "NOT_MEMBER" else "is a member of"
        return MetaAssertionValue(
            op=symbol,
            left=left,
            right=right,
            holds=holds,
            message=f"{_meta_value_label(left)} {verb} {right_set.name}",
        )

    if op in {"SUBSET", "SUBSET_EQ", "SUPERSET", "SUPERSET_EQ"}:
        left_set = _require_meta_set_value(left, context=op)
        right_set = _require_meta_set_value(right, context=op)
        if op in {"SUPERSET", "SUPERSET_EQ"}:
            candidate = right_set.elements
            container = left_set.elements
            proper = op == "SUPERSET"
            symbol = UNICODE_SUPERSET if proper else UNICODE_SUPERSET_EQ
            relation = "proper superset" if proper else "superset"
        else:
            candidate = left_set.elements
            container = right_set.elements
            proper = op == "SUBSET"
            symbol = UNICODE_SUBSET if proper else UNICODE_SUBSET_EQ
            relation = "proper subset" if proper else "subset"
        base_holds = candidate.issubset(container)
        holds = base_holds and (candidate != container if proper else True)
        return MetaAssertionValue(
            op=symbol,
            left=left,
            right=right,
            holds=holds,
            message=f"{left_set.name} is a {relation} of {right_set.name}",
        )

    if op == "EQUALS":
        left_number = _numeric_value(left, context=op)
        right_number = _numeric_value(right, context=op)
        holds = math.isclose(float(left_number), float(right_number))
        return MetaAssertionValue(
            op="=",
            left=left,
            right=right,
            holds=holds,
            message=f"{_meta_value_label(left)} = {right_number}",
        )

    raise CompilerError(CompilerStage.EXECUTION, f"unsupported meta assertion {op}")


def _execute_instruction(stack: list[Any], instruction: Instruction, env: RuntimeEnv) -> None:
    opcode = instruction.opcode

    if opcode == "EMIT_RESULT":
        value = stack.pop()
        results = stack.pop() if stack and isinstance(stack[-1], list) else []
        if not isinstance(results, list):
            raise CompilerError(CompilerStage.EXECUTION, "internal program result stack corrupted")
        results.append(value)
        stack.append(results)
        return

    if opcode == "BUILD_PROGRAM_RESULT":
        final_value = stack.pop()
        results = stack.pop() if stack and isinstance(stack[-1], list) else []
        if not isinstance(results, list):
            raise CompilerError(CompilerStage.EXECUTION, "internal program result stack corrupted")
        results.append(final_value)
        stack.append(ProgramValue(results=results))
        return

    if opcode == "PUSH_STATE":
        operator = instruction.arg["operator"]
        domain = instruction.arg["domain"]
        drive = instruction.arg["drive"]
        # CAS v7.5 register metadata (Clarification 8). Defaults to None for
        # backward compatibility with v7.4 bytecode streams that don't carry
        # register fields.
        # CAS v7.7 (Clarification 10 §2): tuple-valued register fields carry
        # the `|⟨…⟩` register-set form; lists coming from serialized bytecode
        # JSON round-trips are rehydrated to tuples so tests comparing
        # register shape get a stable container type.
        register = instruction.arg.get("register")
        drive_register = instruction.arg.get("drive_register")
        if isinstance(register, list):
            register = tuple(register)
        if isinstance(drive_register, list):
            drive_register = tuple(drive_register)
        domain_explicit = bool(instruction.arg.get("domain_explicit", True))
        state_index = _state_index(operator, domain)
        drives = {drive: 1.0} if drive is not None else {}
        stack.append(
            StateValue(
                states={state_index: 1.0},
                drive_weights=drives,
                explicit_drive=drive is not None,
                domain_explicit=domain_explicit,
                register=register,
                drive_register=drive_register,
            )
        )
        return

    if opcode == "PUSH_STRING":
        stack.append(instruction.arg)
        return

    if opcode == "PUSH_NUMBER":
        stack.append(instruction.arg)
        return

    if opcode == "PUSH_META_SET":
        payload = instruction.arg
        stack.append(_meta_set_value(str(payload["name"])))
        return

    if opcode == "BUILD_META_SET":
        payload = instruction.arg
        count = int(payload.get("count", 0))
        if count > len(stack):
            raise CompilerError(
                CompilerStage.EXECUTION,
                "internal meta-set stack underflow",
            )
        values = [stack.pop() for _ in range(count)]
        values.reverse()
        stack.append(
            _build_typed_meta_set_value(
                constructor=str(payload["constructor"]),
                element_type=str(payload["element_type"]),
                values=values,
            )
        )
        return

    if opcode == "BUILD_TUPLE":
        payload = instruction.arg
        count = int(payload.get("count", 0))
        if count > len(stack):
            raise CompilerError(
                CompilerStage.EXECUTION,
                "internal tuple stack underflow",
            )
        values = [stack.pop() for _ in range(count)]
        values.reverse()
        stack.append(
            TupleValue(
                constructor=str(payload.get("constructor", "Tuple")),
                elements=tuple(values),
            )
        )
        return

    if opcode == "PUSH_META_SYMBOL":
        payload = instruction.arg
        stack.append(
            MetaSymbolValue(
                name=str(payload["name"]),
                symbol_kind=str(payload.get("symbol_kind", "symbol")),
            )
        )
        return

    if opcode == "CARDINALITY":
        collection = _require_meta_set_value(stack.pop(), context="CARDINALITY")
        stack.append(CardinalityValue(collection=collection))
        return

    if opcode == "PUSH_DRIVE":
        # Accept both the legacy integer-arg form (v7.4) and the v7.5
        # dict form that carries an optional register. CAS v7.6 adds an
        # optional `domain` field for drive-in-domain shorthand `F_k^D`;
        # when absent the DriveLiteral remains domain-less and behaves
        # identically to v7.4.
        payload = instruction.arg
        if isinstance(payload, dict):
            drive_index = int(payload["drive"])
            register = payload.get("register")
            domain = payload.get("domain")
        else:
            drive_index = int(payload)
            register = None
            domain = None
        stack.append(DriveLiteral(drive=drive_index, register=register, domain=domain))
        return

    if opcode == "LOAD_VAR":
        stack.append(env.resolve_var(str(instruction.arg)))
        return

    if opcode == "STORE_VAR":
        value = stack.pop()
        payload = instruction.arg
        name = str(payload["name"])
        annotation = payload.get("annotation")
        if annotation is not None and not _value_matches_type(value, annotation):
            raise CompilerError(
                CompilerStage.EXECUTION,
                f"binding {name} violated its declared type {_format_typeinfo(annotation)}",
            )
        if isinstance(value, MetaSetValue) and value.origin == "literal":
            value = MetaSetValue(
                name=name,
                elements=value.elements,
                element_type=value.element_type,
                origin="binding",
            )
        env.vars[name] = value
        stack.append(BindingValue(name=name, value=value))
        return

    if opcode == "DEF_FUNC":
        payload = instruction.arg
        func = UserFunction(
            name=payload["name"],
            params=list(payload["params"]),
            param_types=list(payload["param_types"]),
            return_type=payload["return_type"] or TypeInfo(kind=TypeKind.ANY),
            bytecode=list(payload["body"]),
        )
        env.funcs[func.name] = func
        stack.append(
            FunctionValue(
                name=func.name,
                params=func.params,
                param_types=func.param_types,
                return_type=func.return_type,
            )
        )
        return

    if opcode == "EXPORT_NAME":
        env.exports.add(str(instruction.arg))
        return

    if opcode == "IMPORT":
        import_path = str(instruction.arg)
        resolved = import_path
        if env.module_dir is not None and not os.path.isabs(resolved):
            resolved = os.path.join(env.module_dir, resolved)
        resolved = os.path.abspath(resolved)
        if resolved in env.module_stack:
            raise CompilerError(CompilerStage.EXECUTION, f"cyclic import detected for {resolved}")
        if resolved in env.module_cache:
            loaded = env.module_cache[resolved]
            for key in loaded.exports:
                if key in loaded.vars:
                    env.vars[key] = loaded.vars[key]
                if key in loaded.funcs:
                    env.funcs[key] = loaded.funcs[key]
            stack.append(ModuleValue(path=resolved, exports=list(loaded.exports)))
        else:
            env.module_stack.add(resolved)
            try:
                with open(resolved, encoding="utf-8") as handle:
                    source = handle.read()
                child_env = RuntimeEnv(
                    parent=env,
                    module_dir=os.path.dirname(resolved),
                    module_cache=env.module_cache,
                    module_stack=env.module_stack,
                    warnings=env.warnings,
                )
                child_tokens = lex(source)
                child_parser = Parser(child_tokens)
                child_ast = child_parser.parse()
                if "Worlds" in child_parser.meta_set_aliases_used and WORLDS_ALIAS_WARNING not in env.warnings:
                    env.warnings.append(WORLDS_ALIAS_WARNING)
                _infer(child_ast, env.warnings, TypeEnv(module_dir=os.path.dirname(resolved)))
                child_bytecode = lower(child_ast)
                child_result = execute(child_bytecode, env=child_env)
                exports = sorted(child_env.exports or (set(child_env.vars) | set(child_env.funcs)))
                imported_vars = {key: value for key, value in child_env.vars.items() if key in exports}
                imported_funcs = {key: value for key, value in child_env.funcs.items() if key in exports}
                for key, value in imported_vars.items():
                    env.vars[key] = value
                for key, value in imported_funcs.items():
                    env.funcs[key] = value
                program_value = child_result if isinstance(child_result, ProgramValue) else ProgramValue(results=[child_result])
                env.module_cache[resolved] = LoadedModule(
                    program=program_value,
                    vars=imported_vars,
                    funcs=imported_funcs,
                    exports=exports,
                )
                stack.append(ModuleValue(path=resolved, exports=exports))
                return
            finally:
                env.module_stack.discard(resolved)
        return

    if opcode == "PUSH_FRACTAL":
        sequence = list(instruction.arg)
        composed = 0
        for op in sequence:
            composed = _compose_operators(composed, op)
        stack.append(FractalValue(sequence=sequence, composed_operator=composed, orbit_length=max(1, len(sequence))))
        return

    # CAS v7.6 production-semantics opcodes. Each one simply rehydrates the
    # lowered dict payload into a *Value dataclass and pushes it on the
    # stack. The Python VM does NOT compute yields or recipe algebra;
    # those are Rust cas-engine responsibilities (Clarification 9 §6, §10).
    if opcode == "PUSH_PRODUCTION_TARGET":
        payload = instruction.arg
        stack.append(ProductionTargetValue(name=str(payload["name"])))
        return

    if opcode == "PUSH_RECIPE":
        payload = instruction.arg
        stack.append(
            RecipeValue(
                target=str(payload["target"]),
                prerequisites=list(payload.get("prerequisites", [])),
                leakages=list(payload.get("leakages", [])),
                catalysts=list(payload.get("catalysts", [])),
                inhibitors=list(payload.get("inhibitors", [])),
            )
        )
        return

    if opcode == "PUSH_STATE_VECTOR":
        payload = instruction.arg
        stack.append(StateVectorValue(entries=list(payload.get("entries", []))))
        return

    if opcode == "PUSH_YIELD":
        payload = instruction.arg
        stack.append(
            YieldExpressionValue(
                kind=str(payload["yield_kind"]),
                target=str(payload["target"]),
                state=payload.get("state"),
                recipe=payload.get("recipe"),
            )
        )
        return

    if opcode == "RPM":
        value = stack.pop()
        if isinstance(value, DriveLiteral):
            drive = value.drive
            stack.append(
                RpmValue(
                    drive=drive,
                    completeness=1.0,
                    chain=[f"A0 -> D{drive}", f"D{drive} -> W{drive}", f"W{drive} -> P{drive}"],
                )
            )
            return
        if isinstance(value, StateValue):
            drive = max(value.drive_weights, key=value.drive_weights.get) if value.drive_weights else None
            completeness = 1.0 if drive is not None else 0.0
            chain = (
                [f"A0 -> D{drive}", f"D{drive} -> W{drive}", f"W{drive} -> P{drive}"]
                if drive is not None
                else ["No explicit drive attached to the source state"]
            )
            stack.append(RpmValue(drive=drive, completeness=completeness, chain=chain))
            return
        raise CompilerError(CompilerStage.EXECUTION, "RPM expected a drive or state")

    if opcode == "ATTACH_EMERGENT_RESULT":
        # CAS v7.7 Clarification 10 §4: annotate the top-of-stack result
        # (the ×-chain product) with the author-supplied emergent register
        # name so downstream serialization surfaces the named unified state.
        # If the top is a StateValue, stamp the emergent_register field on
        # it; otherwise surface an execution error (we expect a state at
        # this point because the parser only admits EmergentResult wrapping
        # a ×-chain whose terminal type is a state).
        payload = instruction.arg
        assigned = str(payload["assigned_name"])
        value = stack.pop()
        if isinstance(value, StateValue):
            value.emergent_register = assigned
            stack.append(value)
            return
        raise CompilerError(
            CompilerStage.EXECUTION,
            (
                "CAS v7.7 emergent-result assignment expects a state "
                "value at the ×-chain terminal position"
            ),
        )

    if opcode == "CALL":
        payload = instruction.arg
        argc = int(payload["argc"])
        args = [stack.pop() for _ in range(argc)]
        args.reverse()
        name = str(payload["name"])

        if name == "ohm_scale" or name in OHM_CONSTRUCTORS or name in OHM_OPERATIONS:
            stack.append(_execute_cas_ohm_call(name, args))
            return

        if name == "dominant_state":
            value = args[0]
            if not isinstance(value, StateValue):
                raise CompilerError(CompilerStage.EXECUTION, "dominant_state expects a state")
            stack.append(value.to_dict()["dominant_state"])
            return
        if name == "dominant_domain":
            value = args[0]
            if not isinstance(value, StateValue):
                raise CompilerError(CompilerStage.EXECUTION, "dominant_domain expects a state")
            stack.append(value.dominant_domain())
            return
        if name == "dominant_operator":
            value = args[0]
            if not isinstance(value, StateValue):
                raise CompilerError(CompilerStage.EXECUTION, "dominant_operator expects a state")
            stack.append(f"CO-{value.dominant_operator()}")
            return
        if name == "compose":
            if len(args) != 2 or not all(isinstance(arg, StateValue) for arg in args):
                raise CompilerError(CompilerStage.EXECUTION, "compose expects two states")
            left, right = args
            composed = _compose_operators(left.dominant_operator(), right.dominant_operator())
            domain = left.dominant_domain()
            stack.append(
                StateValue(
                    states={_state_index(composed, domain): 1.0},
                    drive_weights=_merge_drives(left.drive_weights, right.drive_weights),
                    explicit_drive=left.explicit_drive or right.explicit_drive,
                ).normalized()
            )
            return
        if name == "rpm_of":
            if len(args) != 1:
                raise CompilerError(CompilerStage.EXECUTION, "rpm_of expects one argument")
            temp_stack = [args[0]]
            _execute_instruction(temp_stack, Instruction("RPM"), env)
            stack.append(temp_stack.pop())
            return
        if name == "fractal":
            if len(args) < 2:
                raise CompilerError(CompilerStage.EXECUTION, "fractal expects at least two arguments")
            sequence: list[int] = []
            domain: str | None = None
            nested_terms: list[dict[str, Any]] = []
            for arg in args:
                if isinstance(arg, StateValue):
                    sequence.append(arg.dominant_operator())
                    domain = domain or arg.dominant_domain()
                elif isinstance(arg, FractalValue):
                    sequence.extend(arg.sequence)
                    domain = domain or arg.domain
                else:
                    raise CompilerError(CompilerStage.EXECUTION, "fractal expects state or fractal arguments")
                nested_terms.extend(_nesting_terms_of(arg))
            env.warn_nesting(nested_terms)
            composed = 0
            for op in sequence:
                composed = _compose_operators(composed, op)
            stack.append(
                FractalValue(
                    sequence=sequence,
                    composed_operator=composed,
                    orbit_length=len(sequence),
                    domain=domain,
                    terms=nested_terms,
                )
            )
            return
        if name in {"Pullback", "Product", "Union", "Intersection", "Difference"}:
            if len(args) != 2:
                raise CompilerError(CompilerStage.EXECUTION, f"{name} expects two meta_set arguments")
            left_set = _require_meta_set_value(args[0], context=name)
            right_set = _require_meta_set_value(args[1], context=name)
            if name == "Product":
                stack.append(_product_value(left_set, right_set))
                return
            op = {
                "Pullback": "PULLBACK",
                "Union": "UNION",
                "Intersection": "INTERSECTION",
                "Difference": "SET_DIFF",
            }[name]
            stack.append(_set_operation_value(op, left_set, right_set))
            return
        if name in {"CoverOf", "PartitionOf"}:
            if len(args) < 2:
                raise CompilerError(
                    CompilerStage.EXECUTION,
                    f"{name} expects a base meta_set plus at least one family member",
                )
            base = _require_meta_set_value(args[0], context=name)
            members = [
                _require_meta_set_value(arg, context=name)
                for arg in args[1:]
            ]
            stack.append(_cover_family_value(base, members, partition=name == "PartitionOf"))
            return

        func = env.resolve_func(name)
        if len(func.params) != len(args):
            raise CompilerError(
                CompilerStage.EXECUTION,
                f"function {name} expects {len(func.params)} arguments, got {len(args)}",
            )
        for param, expected_type, arg in zip(func.params, func.param_types, args, strict=True):
            if not _value_matches_type(arg, expected_type):
                raise CompilerError(
                    CompilerStage.EXECUTION,
                    f"function {name} argument {param} violated type {_format_typeinfo(expected_type)}",
                )
        child_env = RuntimeEnv(parent=env, module_dir=env.module_dir, module_cache=env.module_cache, warnings=env.warnings)
        for param, arg in zip(func.params, args, strict=True):
            child_env.vars[param] = arg
        result = execute(func.bytecode, env=child_env)
        if not _value_matches_type(result, func.return_type):
            raise CompilerError(
                CompilerStage.EXECUTION,
                f"function {name} returned a value incompatible with {_format_typeinfo(func.return_type)}",
            )
        stack.append(result)
        return

    right = stack.pop()
    left = stack.pop()

    if opcode == "META_ASSERT":
        payload = instruction.arg
        stack.append(_evaluate_meta_assertion(str(payload["op"]), left, right))
        return

    if opcode in {"UNION", "INTERSECTION", "SET_DIFF"}:
        left_set = _require_meta_set_value(left, context=opcode)
        right_set = _require_meta_set_value(right, context=opcode)
        stack.append(_set_operation_value(opcode, left_set, right_set))
        return

    if opcode == "PLUS":
        # State + State: merge probability distributions
        if isinstance(left, StateValue) and isinstance(right, StateValue):
            merged = dict(left.states)
            for key, value in right.states.items():
                merged[key] = merged.get(key, 0.0) + value
            stack.append(
                StateValue(
                    states=merged,
                    drive_weights=_merge_drives(left.drive_weights, right.drive_weights),
                    explicit_drive=left.explicit_drive or right.explicit_drive,
                ).normalized()
            )
            return
        # Mixed types (RPM + State, Drive + RPM, etc.): co-presence as program
        # The left value is the primary; right is aggregated alongside it
        results = []
        for val in (left, right):
            if isinstance(val, ProgramValue):
                results.extend(val.results)
            else:
                results.append(val)
        stack.append(ProgramValue(results=results))
        return

    if opcode == "MINUS":
        if not isinstance(left, StateValue) or not isinstance(right, StateValue):
            # Non-state MINUS: wrap as program with left only (subtraction removes right)
            stack.append(left if not isinstance(left, ProgramValue) else left)
            return
        remaining = dict(left.states)
        for key, value in right.states.items():
            if key in remaining:
                remaining[key] = max(0.0, remaining[key] - value)
        if not any(remaining.values()):
            remaining = dict(left.states)
        stack.append(
            StateValue(
                states=remaining,
                drive_weights=dict(left.drive_weights),
                explicit_drive=left.explicit_drive,
            ).normalized()
        )
        return

    if opcode in {"TIMES", "DIVIDE"}:
        if not isinstance(left, StateValue) or not isinstance(right, StateValue):
            raise CompilerError(CompilerStage.EXECUTION, f"{opcode} expects state operands")
        left_op = left.dominant_operator()
        right_op = right.dominant_operator()
        left_dom = left.dominant_domain()
        right_dom = right.dominant_domain()
        left_drive = left.explicit_drive or 4  # default to F4 Connection
        right_drive = right.explicit_drive or 4

        if cas_engine is not None:
            # Route through Rust algebra (formally verified)
            try:
                if opcode == "TIMES":
                    res_op, res_dom_idx, res_drive = cas_engine.multiply_cognitive_states(
                        left_op, DOMAIN_ORDER.get(left_dom, 0), left_drive,
                        right_op, DOMAIN_ORDER.get(right_dom, 0), right_drive,
                    )
                else:
                    res_op, res_dom_idx, res_drive = cas_engine.divide_cognitive_states(
                        left_op, DOMAIN_ORDER.get(left_dom, 0), left_drive,
                        right_op, DOMAIN_ORDER.get(right_dom, 0), right_drive,
                    )
                res_domain = {0: "P", 1: "C", 2: "E", 3: "O"}.get(res_dom_idx, left_dom)
                stack.append(
                    StateValue(
                        states={_state_index(res_op, res_domain): 1.0},
                        drive_weights=_merge_drives(left.drive_weights, right.drive_weights),
                        explicit_drive=res_drive,
                    ).normalized()
                )
                return
            except (ValueError, Exception):
                pass  # fall through to Python fallback

        # Python fallback (when Rust engine not available)
        domain = left_dom
        if opcode == "TIMES":
            composed = _compose_operators(left_op, right_op)
            # Domain descent: use lower-precedence domain
            if DOMAIN_ORDER.get(right_dom, 0) > DOMAIN_ORDER.get(left_dom, 0):
                domain = right_dom
            elif DOMAIN_ORDER.get(left_dom, 0) > DOMAIN_ORDER.get(right_dom, 0):
                raise CompilerError(
                    CompilerStage.EXECUTION,
                    f"domain ascent violation: {left_dom} × {right_dom}",
                )
        else:
            if left_dom != right_dom:
                raise CompilerError(
                    CompilerStage.EXECUTION,
                    f"cross-domain division: {left_dom} ÷ {right_dom}",
                )
            if left_op == right_op or _is_involution_pair(left_op, right_op):
                composed = 0  # CO-0 identity
            else:
                composed = ((left_op + right_op) // 2) % 10
        stack.append(
            StateValue(
                states={_state_index(composed, domain): 1.0},
                drive_weights=_merge_drives(left.drive_weights, right.drive_weights),
                explicit_drive=left.explicit_drive or right.explicit_drive,
            ).normalized()
        )
        return

    if opcode == "CIRC":
        if isinstance(left, (StateValue, FractalValue)) and isinstance(right, (StateValue, FractalValue)):
            env.warn_nesting(_nesting_terms_of(left) + _nesting_terms_of(right))
        if isinstance(left, StateValue) and isinstance(right, StateValue):
            sequence = [left.dominant_operator(), right.dominant_operator()]
            composed = 0
            for op in sequence:
                composed = _compose_operators(composed, op)
            stack.append(
                FractalValue(
                    sequence=sequence,
                    composed_operator=composed,
                    orbit_length=len(sequence),
                    terms=_nesting_terms_of(left) + _nesting_terms_of(right),
                    domain=left.dominant_domain(),
                )
            )
            return
        if isinstance(left, FractalValue) and isinstance(right, StateValue):
            sequence = [*left.sequence, right.dominant_operator()]
            composed = 0
            for op in sequence:
                composed = _compose_operators(composed, op)
            stack.append(
                FractalValue(
                    sequence=sequence,
                    composed_operator=composed,
                    orbit_length=len(sequence),
                    terms=_nesting_terms_of(left) + _nesting_terms_of(right),
                    domain=right.dominant_domain(),
                )
            )
            return
        if isinstance(left, StateValue) and isinstance(right, FractalValue):
            sequence = [left.dominant_operator(), *right.sequence]
            composed = 0
            for op in sequence:
                composed = _compose_operators(composed, op)
            stack.append(
                FractalValue(
                    sequence=sequence,
                    composed_operator=composed,
                    orbit_length=len(sequence),
                    terms=_nesting_terms_of(left) + _nesting_terms_of(right),
                    domain=left.dominant_domain(),
                )
            )
            return
        if isinstance(left, FractalValue) and isinstance(right, FractalValue):
            sequence = [*left.sequence, *right.sequence]
            composed = 0
            for op in sequence:
                composed = _compose_operators(composed, op)
            stack.append(
                FractalValue(
                    sequence=sequence,
                    composed_operator=composed,
                    orbit_length=len(sequence),
                    terms=_nesting_terms_of(left) + _nesting_terms_of(right),
                    domain=left.domain or right.domain,
                )
            )
            return
        raise CompilerError(CompilerStage.EXECUTION, "CIRC expects state or fractal operands")

    if opcode in {"ARROW", "LARROW", "BIARROW"}:
        if not isinstance(left, StateValue) or not isinstance(right, StateValue):
            raise CompilerError(CompilerStage.EXECUTION, f"{opcode} expects state operands")
        left_idx = left.dominant_state()
        right_idx = right.dominant_state()
        left_domain = left.dominant_domain()
        right_domain = right.dominant_domain()
        if opcode == "ARROW":
            admissible = _is_admissible(right.dominant_operator(), left_idx, right_idx)
            domain_ok = DOMAIN_ORDER[left_domain] <= DOMAIN_ORDER[right_domain]
            relation = "dependency"
        elif opcode == "LARROW":
            admissible = _is_admissible(left.dominant_operator(), right_idx, left_idx)
            domain_ok = DOMAIN_ORDER[right_domain] <= DOMAIN_ORDER[left_domain]
            relation = "results_from"
        else:
            admissible = _is_admissible(right.dominant_operator(), left_idx, right_idx) and _is_admissible(
                left.dominant_operator(), right_idx, left_idx
            )
            domain_ok = left_domain == right_domain
            relation = "bidirectional"
        stack.append(
            RelationValue(
                relation=relation,
                source=left,
                target=right,
                admissible=admissible,
                domain_descent_ok=domain_ok,
            )
        )
        return

    raise CompilerError(CompilerStage.EXECUTION, f"unknown opcode {opcode}")


def execute(bytecode: list[Instruction], env: RuntimeEnv | None = None) -> Any:
    env = env or RuntimeEnv()
    stack: list[Any] = []
    for instruction in bytecode:
        _execute_instruction(stack, instruction, env)
    if len(stack) != 1:
        raise CompilerError(
            CompilerStage.EXECUTION,
            f"vm halted with stack depth {len(stack)} instead of 1",
        )
    return stack[0]


def serialize_ast(node: Any) -> Any:
    if isinstance(node, StateLiteral):
        payload = {
            "node": "StateLiteral",
            "operator": f"CO-{node.operator}",
            "domain": node.domain,
            "drive": f"F{node.drive}" if node.drive is not None else None,
        }
        # CAS v7.5: surface register metadata when present. Omitted for
        # register-neutral nodes so v7.4-style AST output is unchanged.
        # CAS v7.7 (Clarification 10 §2): tuple-valued register is the
        # `|⟨…⟩` register-set form; serialize as a list under a distinct
        # `register_set` key so round-trip serialization preserves the
        # set shape without collapsing it to a single register.
        if isinstance(node.register, tuple):
            payload["register_set"] = list(node.register)
        elif node.register is not None:
            payload["register"] = node.register
        if isinstance(node.drive_register, tuple):
            payload["drive_register_set"] = list(node.drive_register)
        elif node.drive_register is not None:
            payload["drive_register"] = node.drive_register
        return payload
    if isinstance(node, DriveLiteral):
        payload = {"node": "DriveLiteral", "drive": f"F{node.drive}"}
        # CAS v7.7 (Clarification 10 §2): tuple-valued register is the
        # `|⟨…⟩` register-set form on a drive primitive.
        if isinstance(node.register, tuple):
            payload["register_set"] = list(node.register)
        elif node.register is not None:
            payload["register"] = node.register
        # CAS v7.6 Section 4 drive-in-domain shorthand `F_k^D|R` surfaces
        # the domain when present. Register-neutral v7.4 drive references
        # produce no new fields.
        if node.domain is not None:
            payload["domain"] = node.domain
        return payload
    if isinstance(node, EmergentResult):
        # CAS v7.7 Clarification 10 §4: named emergent result wrapper.
        return {
            "node": "EmergentResult",
            "inner": serialize_ast(node.inner),
            "assigned_name": node.assigned_name,
        }
    if isinstance(node, NumberLiteral):
        return {"node": "NumberLiteral", "value": node.value}
    if isinstance(node, MetaSetLiteral):
        return {"node": "MetaSetLiteral", "name": node.name}
    if isinstance(node, TypedMetaSetLiteral):
        return {
            "node": "TypedMetaSetLiteral",
            "constructor": node.constructor,
            "element_type": node.element_type,
            "elements": [serialize_ast(element) for element in node.elements],
        }
    if isinstance(node, TupleLiteral):
        return {
            "node": "TupleLiteral",
            "constructor": node.constructor,
            "elements": [serialize_ast(element) for element in node.elements],
        }
    if isinstance(node, MetaSymbol):
        return {"node": "MetaSymbol", "name": node.name, "symbol_kind": node.symbol_kind}
    if isinstance(node, EmptySetLiteral):
        return {"node": "EmptySetLiteral"}
    if isinstance(node, CardinalityExpr):
        return {"node": "CardinalityExpr", "collection": serialize_ast(node.collection)}
    if isinstance(node, MetaAssertion):
        return {
            "node": "MetaAssertion",
            "op": node.op,
            "left": serialize_ast(node.left),
            "right": serialize_ast(node.right),
        }
    if isinstance(node, StringLiteral):
        return {"node": "StringLiteral", "value": node.value}
    if isinstance(node, Identifier):
        return {"node": "Identifier", "name": node.name}
    if isinstance(node, FractalLiteral):
        return {"node": "FractalLiteral", "sequence": node.sequence}
    if isinstance(node, RpmCall):
        return {"node": "RpmCall", "expr": serialize_ast(node.expr)}
    if isinstance(node, CallExpr):
        return {
            "node": "CallExpr",
            "callee": node.callee,
            "args": [serialize_ast(arg) for arg in node.args],
        }
    if isinstance(node, BinaryExpr):
        return {
            "node": "BinaryExpr",
            "op": node.op,
            "left": serialize_ast(node.left),
            "right": serialize_ast(node.right),
        }
    if isinstance(node, LetStatement):
        return {
            "node": "LetStatement",
            "name": node.name,
            "annotation": serialize_typeinfo(node.annotation),
            "expr": serialize_ast(node.expr),
        }
    if isinstance(node, FunctionDef):
        return {
            "node": "FunctionDef",
            "name": node.name,
            "params": node.params,
            "param_types": [serialize_typeinfo(info) for info in node.param_types],
            "return_type": serialize_typeinfo(node.return_type),
            "body": serialize_ast(node.body),
        }
    if isinstance(node, UseStatement):
        return {"node": "UseStatement", "path": node.path}
    if isinstance(node, ExportStatement):
        return {"node": "ExportStatement", "statement": serialize_ast(node.statement)}
    if isinstance(node, Program):
        return {
            "node": "Program",
            "statements": [serialize_ast(statement) for statement in node.statements],
        }
    # CAS v7.6 (Clarification 9) AST nodes. Serialize to stable dict shapes
    # so callers (JSON API, renderer, Rust engine bindings) can round-trip
    # parse-only recipes and yield queries without re-implementing the
    # grammar.
    if isinstance(node, ProductionTargetLiteral):
        return {"node": "ProductionTargetLiteral", "name": node.name}
    if isinstance(node, RecipeLiteral):
        return {
            "node": "RecipeLiteral",
            "target": serialize_ast(node.target),
            "prerequisites": [
                {
                    "coefficient": prereq.coefficient,
                    "primitive": serialize_ast(prereq.primitive),
                }
                for prereq in node.prerequisites
            ],
            "leakages": [
                {
                    "coefficient": leak.coefficient,
                    "target": serialize_ast(leak.target),
                }
                for leak in node.leakages
            ],
            "catalysts": [
                {"kind": cat.kind, "name": cat.name} for cat in node.catalysts
            ],
            "inhibitors": [
                {"kind": inh.kind, "name": inh.name} for inh in node.inhibitors
            ],
        }
    if isinstance(node, StateVectorLiteral):
        return {
            "node": "StateVectorLiteral",
            "entries": [
                {"primitive": serialize_ast(prim), "activation": value}
                for prim, value in node.entries
            ],
        }
    if isinstance(node, YieldExpression):
        return {
            "node": "YieldExpression",
            "yield_kind": node.kind,
            "target": serialize_ast(node.target),
            "state": serialize_ast(node.state) if node.state is not None else None,
            "recipe": serialize_ast(node.recipe) if node.recipe is not None else None,
        }
    if isinstance(node, LeakageAnnotation):
        return {
            "node": "LeakageAnnotation",
            "coefficient": node.coefficient,
            "target": serialize_ast(node.target),
        }
    if isinstance(node, ConditionAnnotation):
        return {
            "node": "ConditionAnnotation",
            "kind": node.kind,
            "name": node.name,
        }
    return repr(node)


def serialize_instruction_arg(arg: Any) -> Any:
    if isinstance(arg, list):
        return [serialize_instruction_arg(item) for item in arg]
    if isinstance(arg, Instruction):
        return {"opcode": arg.opcode, "arg": serialize_instruction_arg(arg.arg)}
    if isinstance(arg, TypeInfo):
        return serialize_typeinfo(arg)
    if isinstance(arg, dict):
        return {key: serialize_instruction_arg(value) for key, value in arg.items()}
    return arg


def serialize_value(value: Any) -> Any:
    if value is None:
        return None
    if _CAS_OHM_MODULE is not None and isinstance(value, (_CAS_OHM_MODULE.OhmScale, _CAS_OHM_MODULE.OhmQuantity)):
        return value.to_dict()
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, StateValue):
        return value.to_dict()
    if isinstance(value, RelationValue):
        return value.to_dict()
    if isinstance(value, FractalValue):
        return value.to_dict()
    if isinstance(value, RpmValue):
        return value.to_dict()
    if isinstance(value, ProgramValue):
        return value.to_dict()
    if isinstance(value, BindingValue):
        return value.to_dict()
    if isinstance(value, FunctionValue):
        return value.to_dict()
    if isinstance(value, ModuleValue):
        return value.to_dict()
    if isinstance(value, MetaSetValue):
        return value.to_dict()
    if isinstance(value, MetaSymbolValue):
        return value.to_dict()
    if isinstance(value, CardinalityValue):
        return value.to_dict()
    if isinstance(value, MetaAssertionValue):
        return value.to_dict()
    if isinstance(value, TupleValue):
        return value.to_dict()
    if isinstance(value, DriveLiteral):
        payload: dict[str, Any] = {"kind": "drive", "drive": f"F{value.drive}"}
        # CAS v7.5: surface register metadata when present.
        # CAS v7.7 (Clarification 10 §2): tuple-valued register is the
        # `|⟨…⟩` register-set form on a drive.
        if isinstance(value.register, tuple):
            payload["register_set"] = list(value.register)
            payload["register_set_names"] = [
                REGISTER_NAMES[r] for r in value.register
            ]
        elif value.register is not None:
            payload["register"] = value.register
            payload["register_name"] = REGISTER_NAMES[value.register]
        # CAS v7.6 Section 4 drive-in-domain shorthand: surface the
        # domain when present so downstream consumers can distinguish
        # `F2` from `F2^C`.
        if value.domain is not None:
            payload["domain"] = value.domain
            payload["domain_name"] = DOMAIN_NAMES.get(value.domain)
        return payload
    # CAS v7.6 (Clarification 9) runtime values.
    if isinstance(value, ProductionTargetValue):
        return value.to_dict()
    if isinstance(value, RecipeValue):
        return value.to_dict()
    if isinstance(value, StateVectorValue):
        return value.to_dict()
    if isinstance(value, YieldExpressionValue):
        return value.to_dict()
    return repr(value)


# ---------------------------------------------------------------------------
# CAS diagram export.
#
# This view is intentionally descriptive: it does not add new CAS semantics.
# It projects already-valid AST structures into a graph schema suitable for
# SVG/canvas renderers: nodes, edges, containment boxes, and layout hints.
# ---------------------------------------------------------------------------


def empty_diagram() -> dict[str, Any]:
    return {
        "kind": "cas_diagram",
        "schema_version": "1.0",
        "layouts": ["semantic"],
        "nodes": [],
        "edges": [],
        "containers": [],
    }


def _diagram_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.:-]+", "_", value).strip("_")
    return slug or "item"


def _register_suffix(register: str | tuple[str, ...] | None) -> str:
    if isinstance(register, tuple):
        return "|<" + ",".join(register) + ">"
    if register is not None:
        return f"|{register}"
    return ""


def _state_literal_label(node: StateLiteral) -> str:
    base = (
        f"{node.domain}{node.operator}"
        if node.domain_explicit or node.drive is not None
        else f"CO-{node.operator}"
    )
    if node.drive is not None:
        base += f"_F{node.drive}"
    base += _register_suffix(node.register)
    return base


def _drive_literal_label(node: DriveLiteral) -> str:
    label = f"F{node.drive}"
    if node.domain is not None:
        label += f"^{node.domain}"
    label += _register_suffix(node.register)
    return label


def _ast_diagram_label(node: Any) -> str:
    if isinstance(node, StateLiteral):
        return _state_literal_label(node)
    if isinstance(node, DriveLiteral):
        return _drive_literal_label(node)
    if isinstance(node, MetaSymbol):
        return node.name
    if isinstance(node, MetaSetLiteral):
        return node.name
    if isinstance(node, TupleLiteral):
        return f"{node.constructor}<" + ",".join(_ast_diagram_label(element) for element in node.elements) + ">"
    if isinstance(node, BinaryExpr) and node.op in {"ARROW", "LARROW", "BIARROW"}:
        arrows = {"ARROW": "->", "LARROW": "<-", "BIARROW": "<->"}
        return f"{_ast_diagram_label(node.left)}{arrows[node.op]}{_ast_diagram_label(node.right)}"
    return type(node).__name__


def _typed_set_label(node: TypedMetaSetLiteral) -> str:
    parts = [_ast_diagram_label(element) for element in node.elements]
    return f"{node.constructor}{{{', '.join(parts)}}}"


class _DiagramBuilder:
    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[dict[str, Any]] = []
        self.containers: dict[str, dict[str, Any]] = {}
        self.layouts: set[str] = {"semantic"}
        self._edge_index = 0
        self._anon_index = 0

    def add_layout(self, layout: str) -> None:
        self.layouts.add(layout)

    def add_node(
        self,
        kind: str,
        label: str,
        *,
        role: str | None = None,
        id_hint: str | None = None,
        **attrs: Any,
    ) -> str:
        node_id = id_hint or f"{kind}:{_diagram_slug(label)}"
        payload = self.nodes.setdefault(
            node_id,
            {"id": node_id, "kind": kind, "label": label},
        )
        if role is not None:
            payload["role"] = role
        for key, value in attrs.items():
            if value is not None:
                payload[key] = value
        return node_id

    def add_edge(
        self,
        source: str,
        target: str,
        kind: str,
        *,
        label: str | None = None,
        directed: bool = True,
        **attrs: Any,
    ) -> str:
        self._edge_index += 1
        edge_id = f"edge:{self._edge_index}"
        payload: dict[str, Any] = {
            "id": edge_id,
            "source": source,
            "target": target,
            "kind": kind,
            "directed": directed,
        }
        if label is not None:
            payload["label"] = label
        for key, value in attrs.items():
            if value is not None:
                payload[key] = value
        self.edges.append(payload)
        return edge_id

    def add_container(
        self,
        label: str,
        *,
        kind: str = "meta_set",
        id_hint: str | None = None,
        contains: list[str] | None = None,
        **attrs: Any,
    ) -> str:
        container_id = id_hint or f"container:{_diagram_slug(label)}"
        payload = self.containers.setdefault(
            container_id,
            {
                "id": container_id,
                "kind": kind,
                "label": label,
                "contains": [],
            },
        )
        for child in contains or []:
            if child not in payload["contains"]:
                payload["contains"].append(child)
        for key, value in attrs.items():
            if value is not None:
                payload[key] = value
        self.add_layout("containment")
        return container_id

    def anon_node(self, kind: str, label: str, **attrs: Any) -> str:
        self._anon_index += 1
        return self.add_node(kind, label, id_hint=f"{kind}:{self._anon_index}", **attrs)

    def add_meta_element_node(self, key: str, element_type: str) -> str:
        if element_type == "noetic":
            self.add_layout("radial")
            return self.add_node("noetic", key, role="atomic_noetic")
        if element_type == "state":
            return self.add_node("state", key, role="cognitive_state")
        if element_type == "state_variant":
            return self.add_node("state_variant", key, role="cognitive_state_variant")
        if element_type == "drive":
            return self.add_node("drive", key, role="foundation_drive")
        if element_type == "domain":
            return self.add_node("domain", key, role="processing_domain")
        if element_type == "register":
            return self.add_node("register", key, role="phenomenological_register")
        if element_type == "subfoundation":
            return self.add_node("subfoundation", key, role="drive_register_position")
        if element_type == "foundation":
            return self.add_node("foundation", key, role="foundation_family")
        if element_type == "relation":
            return self.add_node("relation", key, role="relation_element")
        if element_type == "tuple":
            return self.add_node("tuple", key, role="tuple_element")
        return self.add_node("symbol", key, role="meta_symbol")

    def walk(self, node: Any) -> str | None:
        if node is None:
            return None
        if isinstance(node, Program):
            roots = [self.walk(statement) for statement in node.statements]
            roots = [root for root in roots if root is not None]
            program_id = self.anon_node("program", "CAS program", statement_count=len(roots))
            for index, root in enumerate(roots, start=1):
                self.add_edge(program_id, root, "statement", label=str(index))
            return program_id
        if isinstance(node, StateLiteral):
            bare_noetic = not node.domain_explicit and node.drive is None
            if bare_noetic:
                noetic_id = self.add_node(
                    "noetic",
                    f"CO-{node.operator}",
                    role="atomic_noetic",
                    operator=node.operator,
                    register=node.register,
                )
                self.add_layout("radial")
                return noetic_id
            label = _state_literal_label(node)
            state_id = self.add_node(
                "state",
                label,
                role="cognitive_state",
                operator=node.operator,
                noetic=f"CO-{node.operator}",
                domain=node.domain,
                drive=f"F{node.drive}" if node.drive is not None else None,
                register=node.register,
            )
            noetic_id = self.add_node("noetic", f"CO-{node.operator}", role="atomic_noetic")
            domain_id = self.add_node("domain", node.domain, role="processing_domain")
            self.add_edge(noetic_id, state_id, "instantiates", label="Noetic")
            self.add_edge(domain_id, state_id, "locates", label="Domain")
            if node.drive is not None:
                drive_id = self.add_node("drive", f"F{node.drive}", role="foundation_drive")
                self.add_edge(drive_id, state_id, "modulates", label="Drive")
            if node.register is not None:
                regs = node.register if isinstance(node.register, tuple) else (node.register,)
                for reg in regs:
                    reg_id = self.add_node("register", reg, role="phenomenological_register")
                    self.add_edge(reg_id, state_id, "register", label="Register")
            return state_id
        if isinstance(node, DriveLiteral):
            return self.add_node(
                "drive",
                _drive_literal_label(node),
                role="foundation_drive",
                drive=node.drive,
                domain=node.domain,
                register=node.register,
            )
        if isinstance(node, MetaSymbol):
            return self.add_node(node.symbol_kind, node.name, role=f"{node.symbol_kind}_symbol")
        if isinstance(node, MetaSetLiteral):
            value = _meta_set_value(node.name)
            container_id = self.add_container(
                value.name,
                kind="meta_set",
                element_type=value.element_type,
                cardinality=len(value.elements),
                expanded=len(value.elements) <= 12,
            )
            if len(value.elements) <= 12:
                for element in sorted(value.elements):
                    child = self.add_meta_element_node(element, value.element_type)
                    self.containers[container_id]["contains"].append(child)
            return container_id
        if isinstance(node, TypedMetaSetLiteral):
            container_kind = "typed_meta_set"
            if node.element_type == "noetic":
                container_kind = "noetic_cluster"
            elif node.element_type == "state_variant":
                container_kind = "state_variant_cluster"
            elif node.element_type == "state":
                container_kind = "state_cluster"
            elif node.element_type == "relation":
                container_kind = "relation_cluster"
            container_id = self.add_container(
                _typed_set_label(node),
                kind=container_kind,
                element_type=node.element_type,
                cardinality=len(node.elements),
            )
            if node.element_type == "noetic":
                self.add_layout("radial")
            for element in node.elements:
                child = self.walk(element)
                if child is not None and child not in self.containers[container_id]["contains"]:
                    self.containers[container_id]["contains"].append(child)
            return container_id
        if isinstance(node, TupleLiteral):
            tuple_id = self.anon_node(
                "coordinate" if node.constructor in {"Coordinate", "CASCoordinate"} else "tuple",
                node.constructor,
                role="typed_tuple",
                arity=len(node.elements),
            )
            for index, element in enumerate(node.elements, start=1):
                child = self.walk(element)
                if child is not None:
                    self.add_edge(child, tuple_id, "tuple_slot", label=str(index))
            return tuple_id
        if isinstance(node, EmptySetLiteral):
            return self.add_container("EmptySet", kind="meta_set", element_type="empty", cardinality=0)
        if isinstance(node, CardinalityExpr):
            collection = self.walk(node.collection)
            card_id = self.anon_node("cardinality", "|X|", role="cardinality_query")
            if collection is not None:
                self.add_edge(collection, card_id, "cardinality", label="| |")
            return card_id
        if isinstance(node, MetaAssertion):
            left = self.walk(node.left)
            right = self.walk(node.right)
            if left is None or right is None:
                return left or right
            if node.op in {"MEMBER", "NOT_MEMBER"}:
                self.add_layout("topos")
                self.add_edge(left, right, "membership", label=UNICODE_MEMBER if node.op == "MEMBER" else UNICODE_NOT_MEMBER)
            elif node.op in {"SUBSET", "SUBSET_EQ", "SUPERSET", "SUPERSET_EQ"}:
                self.add_layout("topos")
                self.add_layout("containment")
                label = {
                    "SUBSET": UNICODE_SUBSET,
                    "SUBSET_EQ": UNICODE_SUBSET_EQ,
                    "SUPERSET": UNICODE_SUPERSET,
                    "SUPERSET_EQ": UNICODE_SUPERSET_EQ,
                }[node.op]
                edge_kind = {
                    "SUBSET": "proper_subset",
                    "SUBSET_EQ": "subset",
                    "SUPERSET": "proper_superset",
                    "SUPERSET_EQ": "superset",
                }[node.op]
                self.add_edge(left, right, edge_kind, label=label)
            elif node.op == "EQUALS":
                self.add_edge(left, right, "equals", label="=")
            return right
        if isinstance(node, BinaryExpr):
            left = self.walk(node.left)
            right = self.walk(node.right)
            if left is None or right is None:
                return left or right
            if node.op in {"ARROW", "LARROW", "BIARROW"}:
                self.add_layout("dependency")
                if node.op == "LARROW":
                    self.add_edge(right, left, "results_from", label=UNICODE_LARROW)
                    return left
                if node.op == "BIARROW":
                    self.add_edge(left, right, "bidirectional", label=UNICODE_BIARROW, directed=False)
                    return right
                self.add_edge(left, right, "dependency", label=UNICODE_ARROW)
                return right
            operator_labels = {
                "PLUS": "+",
                "MINUS": "-",
                "TIMES": UNICODE_TIMES,
                "DIVIDE": UNICODE_DIVIDE,
                "CIRC": "compose",
                "UNION": UNICODE_UNION,
                "INTERSECTION": UNICODE_INTERSECTION,
                "SET_DIFF": UNICODE_SET_MINUS,
            }
            op_id = self.anon_node(
                "operator",
                operator_labels.get(node.op, node.op),
                role="cas_operator",
                operator=node.op,
            )
            self.add_layout("branch")
            self.add_edge(left, op_id, "operand", label="left")
            self.add_edge(right, op_id, "operand", label="right")
            return op_id
        if isinstance(node, EmergentResult):
            inner = self.walk(node.inner)
            target = self.add_node("emergent", node.assigned_name, role="named_emergent_result")
            if inner is not None:
                self.add_edge(inner, target, "emerges_as", label="=")
            self.add_layout("branch")
            return target
        if isinstance(node, FractalLiteral):
            self.add_layout("fractal")
            self.add_layout("radial")
            previous: str | None = None
            root: str | None = None
            for index, op in enumerate(node.sequence, start=1):
                current = self.add_node("noetic", f"CO-{op}", role="fractal_step", step=index)
                root = root or current
                if previous is not None:
                    self.add_edge(previous, current, "fractal_step", label="compose")
                previous = current
            return previous or root
        if isinstance(node, RpmCall):
            self.add_layout("dependency")
            root = self.walk(node.expr)
            drive: int | None = None
            if isinstance(node.expr, DriveLiteral):
                drive = node.expr.drive
            elif isinstance(node.expr, StateLiteral):
                drive = node.expr.drive
            if drive is None:
                rpm_id = self.anon_node("rpm", "RPM", role="prerequisite_chain")
                if root is not None:
                    self.add_edge(root, rpm_id, "rpm_query", label="RPM")
                return rpm_id
            labels = ["A0", f"D{drive}", f"W{drive}", f"P{drive}"]
            ids = [self.add_node("rpm_stage", label, role="rpm_stage") for label in labels]
            for source, target in zip(ids, ids[1:]):
                self.add_edge(source, target, "rpm_descent", label="section")
            if root is not None:
                self.add_edge(root, ids[0], "rpm_query", label="RPM")
            return ids[-1]
        if isinstance(node, ProductionTargetLiteral):
            return self.add_node("production_target", f"Omega_{node.name}", role="production_target")
        if isinstance(node, RecipeLiteral):
            self.add_layout("recipe")
            target = self.walk(node.target)
            for prereq in node.prerequisites:
                source = self.walk(prereq.primitive)
                if source is not None and target is not None:
                    self.add_edge(source, target, "recipe_prerequisite", label=str(prereq.coefficient), coefficient=prereq.coefficient)
            for condition in node.catalysts:
                condition_id = self.add_node("catalyst", condition.name or "kappa", role="recipe_condition")
                if target is not None:
                    self.add_edge(condition_id, target, "catalyst", label="kappa")
            for condition in node.inhibitors:
                condition_id = self.add_node("inhibitor", condition.name or "iota", role="recipe_condition")
                if target is not None:
                    self.add_edge(condition_id, target, "inhibitor", label="iota")
            for leakage in node.leakages:
                side = self.walk(leakage.target)
                if target is not None and side is not None:
                    self.add_edge(target, side, "leakage", label=str(leakage.coefficient), coefficient=leakage.coefficient)
            return target
        if isinstance(node, StateVectorLiteral):
            vector_id = self.anon_node("state_vector", "S", role="activation_vector")
            for primitive, activation in node.entries:
                child = self.walk(primitive)
                if child is not None:
                    self.add_edge(child, vector_id, "activation", label=str(activation), activation=activation)
            return vector_id
        if isinstance(node, YieldExpression):
            target = self.walk(node.target)
            yield_id = self.anon_node("yield", node.kind, role="yield_query")
            if target is not None:
                self.add_edge(target, yield_id, "yield_query", label=node.kind)
            if node.state is not None:
                state = self.walk(node.state)
                if state is not None:
                    self.add_edge(state, yield_id, "yield_input", label="state")
            if node.recipe is not None:
                recipe = self.walk(node.recipe)
                if recipe is not None:
                    self.add_edge(recipe, yield_id, "yield_input", label="recipe")
            return yield_id
        if isinstance(node, LetStatement):
            value = self.walk(node.expr)
            binding = self.add_node("binding", node.name, role="let_binding")
            if value is not None:
                self.add_edge(value, binding, "binds", label="let")
            return binding
        if isinstance(node, Identifier):
            return self.add_node("identifier", node.name, role="bound_reference")
        if isinstance(node, NumberLiteral):
            return self.add_node("number", str(node.value), role="numeric_literal")
        if isinstance(node, StringLiteral):
            return self.add_node("string", node.value, role="string_literal")
        if isinstance(node, CallExpr):
            call_id = self.anon_node("call", node.callee, role="function_call")
            if node.callee == "Product":
                self.add_layout("grid")
            elif node.callee in {"CoverOf", "PartitionOf"}:
                self.add_layout("petals")
                self.add_layout("containment")
            elif node.callee == "Pullback":
                self.add_layout("topos")
                self.add_layout("containment")
            for index, arg in enumerate(node.args):
                arg_id = self.walk(arg)
                if arg_id is not None:
                    edge_kind = "argument"
                    edge_label: str | None = None
                    if node.callee == "Product":
                        edge_kind = "product_axis"
                        edge_label = "axis" if index == 0 else str(index + 1)
                    elif node.callee == "CoverOf":
                        edge_kind = "cover_base" if index == 0 else "cover_member"
                        edge_label = "base" if index == 0 else "covers"
                    elif node.callee == "PartitionOf":
                        edge_kind = "partition_base" if index == 0 else "partition_member"
                        edge_label = "base" if index == 0 else "part"
                    elif node.callee == "Pullback":
                        edge_kind = "pullback_leg"
                        edge_label = "meet"
                    self.add_edge(arg_id, call_id, edge_kind, label=edge_label)
            return call_id
        if isinstance(node, FunctionDef):
            return self.add_node("function", node.name, role="function_definition")
        if isinstance(node, ExportStatement):
            return self.walk(node.statement)
        if isinstance(node, UseStatement):
            return self.add_node("module", node.path, role="module_import")
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "cas_diagram",
            "schema_version": "1.0",
            "layouts": sorted(self.layouts),
            "nodes": list(self.nodes.values()),
            "edges": self.edges,
            "containers": list(self.containers.values()),
        }


def build_diagram(ast: Any) -> dict[str, Any]:
    builder = _DiagramBuilder()
    builder.walk(ast)
    return builder.to_dict()


# ---------------------------------------------------------------------------
# Per-position register activation extraction (ADR-02 trainer integration).
#
# `extract_register_activations` walks a parsed AST and emits one
# `RegisterActivation` record per cognitive-state position encountered, in
# source order. Design choices:
#
#   1. The walker is PURE — it does not mutate the AST, does not depend on
#      typecheck or execution, and does not depend on the Rust `cas_engine`
#      fallback. A trainer can call it against any parsed `ast` (including
#      one that would fail downstream Rule 4 admissibility); validation and
#      activation extraction are independent concerns. This matches the
#      dispatch requirement that Rule 4 validation is a separate concern.
#
#   2. `StateLiteral` is the only cognitive-state position the walker emits.
#      `DriveLiteral` is NOT emitted as a state-bank position: drives are the
#      Core Drive F1-F7 primitives and live on a separate axis from the 40
#      Cognitive States (10 Noetics × 4 Domains). The `data_format.md`
#      `register_labels` schema uses positions in `[0, 40)`, i.e. the state
#      bank. Drive-level register information (`DriveLiteral.register`) is
#      therefore not projected into this trainer-facing view; when a
#      compound state has an independent drive register (`^2|T^C_{F2|A}`),
#      only the Noetic-level register on the compound is surfaced. This is
#      a deliberate alignment with the trainer-side ADR-02 embedding
#      (register-modulated *state* representation); drive-level register
#      supervision is a separate follow-on if ever needed.
#
#   3. VALID_REGISTERS is the single source of truth. When the walker
#      builds `registers_active`, every element is cross-checked against
#      VALID_REGISTERS defensively — the parser already enforces this, but
#      the defensive check means a hand-constructed AST (e.g. in a test)
#      cannot smuggle an invalid register letter past the activation view.
#      A raised ValueError here is a programming error, not a user-facing
#      diagnostic.
#
#   4. EmergentResult emission: the walker descends into the inner `×` chain
#      and emits one `RegisterActivation` per operand (with
#      `emergent_name` set to the assigned name so the trainer can
#      associate the operand with its fused output), then appends ONE
#      additional record for the emergent result itself whose
#      `registers_active` is the set-union of the operand register sets.
#      Rationale for union: when a recipe author writes
#      `(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω`, the emergent Ω is defined by
#      integrating the listed registers; the natural supervision target
#      for the emergent position is therefore the set of input registers.
#      The emergent record's `is_register_set` is False — the emergent is
#      not itself a `|⟨…⟩` specification — so consumers that need to
#      distinguish "architectural specification" from "union-of-emergent-
#      inputs" can do so via the flag. `emergent_name` carries the
#      author-chosen name verbatim (`Ω_refusal`, `fused`, `^3^P|Ω`, etc.)
#      so the trainer can look it up in `omega_registry.yaml`.
# ---------------------------------------------------------------------------


def _state_literal_activation(
    node: "StateLiteral",
    *,
    emergent_name: str | None = None,
) -> "RegisterActivation":
    """Project a StateLiteral onto a RegisterActivation record."""
    position = _state_index(node.operator, node.domain)
    if isinstance(node.register, tuple):
        # CAS v7.7 |⟨R1,R2,...⟩ register-set specification.
        regs = node.register
        is_set = True
    elif node.register is not None:
        # CAS v7.5 single-register |R specification.
        regs = (node.register,)
        is_set = False
    else:
        # Register-neutral (CAS v7.4-compatible) position.
        regs = ()
        is_set = False
    for reg in regs:
        if reg not in VALID_REGISTERS:
            # Defensive guard — parser already rejects invalid letters.
            raise ValueError(
                f"RegisterActivation encountered non-canonical register "
                f"{reg!r}; valid registers are {VALID_REGISTERS}"
            )
    return RegisterActivation(
        position=position,
        registers_active=frozenset(regs),
        is_register_set=is_set,
        emergent_name=emergent_name,
    )


def extract_register_activations(expr: Any) -> list[RegisterActivation]:
    """Walk a parsed CAS expression and emit per-position register activations.

    Returns a list of :class:`RegisterActivation` records, one per
    cognitive-state position encountered, in source order. Register-neutral
    positions produce records with an empty ``registers_active`` set — the
    trainer interprets empty as "no register supervision for this position"
    per the masking rule in ``cas-native/training/data_format.md``.

    The walker descends into composite AST nodes (BinaryExpr, RpmCall,
    CallExpr, EmergentResult, LetStatement, FunctionDef, ExportStatement,
    Program, and the v7.6 recipe/state-vector/yield literals) but only
    emits records for :class:`StateLiteral` leaves. :class:`DriveLiteral`
    carries its own register axis but does not map to the 40-state bank;
    drive-level registers are intentionally not surfaced through this
    trainer-facing view (see module comment for rationale).

    For a :class:`EmergentResult` wrapper (CAS v7.7 Clarification 10 §4),
    the walker emits each operand's activation with ``emergent_name`` set
    to the assigned name, then appends ONE additional record for the
    emergent position whose ``registers_active`` is the union of the
    operand register sets. This matches the data_format.md
    ``omega_labels`` schema, which expects the emergent-result position to
    carry the emergent name and the input registers that compose it.

    Returns an empty list when the AST contains no cognitive-state nodes
    (e.g. pure drive queries, fractal literals, RPM calls on drives).
    """
    out: list[RegisterActivation] = []
    _walk(expr, out, emergent_name=None)
    return out


def _walk(
    node: Any,
    out: list[RegisterActivation],
    *,
    emergent_name: str | None,
) -> None:
    """Recursive AST walker for register activation extraction."""
    if node is None:
        return
    if isinstance(node, StateLiteral):
        out.append(_state_literal_activation(node, emergent_name=emergent_name))
        return
    if isinstance(node, DriveLiteral):
        # Drive-level register is intentionally not projected onto the
        # state bank; see module comment (3).
        return
    if isinstance(node, EmergentResult):
        # CAS v7.7 Clarification 10 §4: named emergent-result assignment.
        # Emit one activation per operand (with emergent_name attached),
        # then one trailing activation for the emergent position whose
        # registers_active is the union of operand register sets. The
        # emergent position is derived from the first StateLiteral in the
        # inner chain (all operands share the same Noetic × Domain core
        # by Rule 4 construction); if the inner expression has no state
        # literals (defensive — should not occur for well-formed
        # emergent-result wrappers), no trailing record is emitted.
        start = len(out)
        _walk(node.inner, out, emergent_name=node.assigned_name)
        operand_records = out[start:]
        if operand_records:
            union_regs: set[str] = set()
            for rec in operand_records:
                union_regs.update(rec.registers_active)
            # Position of the emergent result mirrors the position of the
            # operands — Rule 4 guarantees all operands share the same
            # (operator, domain) core when the chain is licensed via
            # EmergentResult, so any operand's position is representative.
            emergent_position = operand_records[0].position
            out.append(
                RegisterActivation(
                    position=emergent_position,
                    registers_active=frozenset(union_regs),
                    is_register_set=False,
                    emergent_name=node.assigned_name,
                )
            )
        return
    if isinstance(node, BinaryExpr):
        _walk(node.left, out, emergent_name=emergent_name)
        _walk(node.right, out, emergent_name=emergent_name)
        return
    if isinstance(node, RpmCall):
        _walk(node.expr, out, emergent_name=emergent_name)
        return
    if isinstance(node, CallExpr):
        for arg in node.args:
            _walk(arg, out, emergent_name=emergent_name)
        return
    if isinstance(node, LetStatement):
        _walk(node.expr, out, emergent_name=emergent_name)
        return
    if isinstance(node, FunctionDef):
        _walk(node.body, out, emergent_name=emergent_name)
        return
    if isinstance(node, ExportStatement):
        _walk(node.statement, out, emergent_name=emergent_name)
        return
    if isinstance(node, Program):
        for stmt in node.statements:
            _walk(stmt, out, emergent_name=emergent_name)
        return
    if isinstance(node, RecipeLiteral):
        for prereq in node.prerequisites:
            _walk(prereq.primitive, out, emergent_name=emergent_name)
        for leak in node.leakages:
            _walk(leak.target, out, emergent_name=emergent_name)
        return
    if isinstance(node, StateVectorLiteral):
        for primitive, _ in node.entries:
            _walk(primitive, out, emergent_name=emergent_name)
        return
    if isinstance(node, YieldExpression):
        _walk(node.state, out, emergent_name=emergent_name)
        _walk(node.recipe, out, emergent_name=emergent_name)
        return
    # Terminal nodes with no cognitive-state children (Identifier, StringLiteral,
    # FractalLiteral, ProductionTargetLiteral, LeakageAnnotation,
    # ConditionAnnotation, RecipePrerequisite, UseStatement) contribute no
    # activations. RecipePrerequisite is only ever reached via RecipeLiteral
    # traversal above, so it is handled there.
    return


def _compile_source(source: str, *, module_dir: str | None = None) -> CompilationArtifact:
    ast: Any | None = None
    try:
        tokens = lex(source)
        parser = Parser(tokens)
        ast = parser.parse()
        warnings: list[str] = []
        if "Worlds" in parser.meta_set_aliases_used:
            warnings.append(WORLDS_ALIAS_WARNING)
        type_info = _infer(
            ast,
            warnings,
            TypeEnv(module_dir=module_dir),
        )
        bytecode = lower(ast)
        result = execute(bytecode, env=RuntimeEnv(module_dir=module_dir, warnings=warnings))
        return CompilationArtifact(
            source=source,
            tokens=tokens[:-1],
            ast=ast,
            type_info=type_info,
            bytecode=bytecode,
            result=result,
            warnings=warnings,
            valid=True,
            engine="rust+python" if cas_engine is not None else "python",
        )
    except (CompilerError, RecursionError) as exc:
        if isinstance(exc, RecursionError):
            exc = CompilerError(
                CompilerStage.PARSING if ast is None else CompilerStage.TYPECHECK,
                "expression is too deeply nested or too long for this compiler "
                "(Python recursion limit reached); split it into let-bindings",
            )
            ast = None          # a tree that deep cannot be serialised either (review finding)
        partial_tokens: list[LexToken] = []
        try:
            partial_tokens = lex(source)[:-1]
        except CompilerError:
            partial_tokens = []
        return CompilationArtifact(
            source=source,
            tokens=partial_tokens,
            ast=ast,
            type_info=None,
            bytecode=[],
            result=None,
            valid=False,
            error=str(exc),
            engine="rust+python" if cas_engine is not None else "python",
        )


def compile_expression(source: str) -> CompilationArtifact:
    return _compile_source(source)


def compile_file(path: str) -> CompilationArtifact:
    resolved = os.path.abspath(path)
    with open(resolved, encoding="utf-8") as handle:
        return _compile_source(handle.read(), module_dir=os.path.dirname(resolved))
