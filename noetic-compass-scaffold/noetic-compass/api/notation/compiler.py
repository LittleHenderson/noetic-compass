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
import math
import os
import re
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
<type_name>     ::= "state" | "drive" | "string" | "void" | "function" | "fractal" | "rpm" | "relation" | "program" | "any" ;
<domain_list>   ::= <domain> ("," <domain>)* ;
<expression>    ::= <relation> ;
<relation>      ::= <sum> (("->" | "<-" | "<->") <sum>)* ;
<sum>           ::= <product> (("+" | "-") <product>)* ;
<product>       ::= <primary> (("*" | "/" | "∘" | "×" | "÷") <primary>)* ;
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
    register: str | None = None
    drive_register: str | None = None


@dataclass
class DriveLiteral:
    drive: int
    # CAS v7.5 Phenomenological Register. Optional; None means register-neutral.
    register: str | None = None
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
    # CAS v7.5 Phenomenological Register (Clarification 8). Optional; None
    # means the state is register-neutral (v7.4-compatible). `register`
    # carries the Noetic/compound-level register; `drive_register` carries
    # an independent Drive-level register when the notation specifies both.
    register: str | None = None
    drive_register: str | None = None

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
            register=self.register,
            drive_register=self.drive_register,
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
        if self.register is not None:
            payload["register"] = self.register
            payload["register_name"] = REGISTER_NAMES[self.register]
        if self.drive_register is not None:
            payload["drive_register"] = self.drive_register
            payload["drive_register_name"] = REGISTER_NAMES[self.drive_register]
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


@dataclass
class FractalValue:
    sequence: list[int]
    composed_operator: int
    orbit_length: int
    domain: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "fractal",
            "sequence": self.sequence,
            "composed_operator": f"CO-{self.composed_operator}",
            "orbit_length": self.orbit_length,
            "domain": self.domain,
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


BUILTIN_NAMES = {"dominant_state", "dominant_domain", "dominant_operator", "compose", "rpm_of", "fractal"}


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
    (r"[PCEO]\d+", TokenKind.STATE_REF),
    # Accept both `F_n` (CAS v7.5 Clarification 8 notation, with underscore)
    # and `Fn` (CAS v7.4 compatibility) for drive primitives.
    (r"F_\d+", TokenKind.DRIVE),
    (r"F\d+", TokenKind.DRIVE),
    (r"[PCEO]", TokenKind.DOMAIN),
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
            name = self.expect(TokenKind.IDENT).value
            annotation = None
            if self.current().kind == TokenKind.COLON:
                self.advance()
                annotation = self.parse_type()
            self.expect(TokenKind.EQUALS)
            return LetStatement(name=name, expr=self.parse_relation(), annotation=annotation)
        if token.kind == TokenKind.FN:
            self.advance()
            name = self.expect(TokenKind.IDENT).value
            self.expect(TokenKind.LPAREN)
            params: list[str] = []
            param_types: list[TypeInfo] = []
            if self.current().kind != TokenKind.RPAREN:
                params.append(self.expect(TokenKind.IDENT).value)
                if self.current().kind == TokenKind.COLON:
                    self.advance()
                    param_types.append(self.parse_type())
                else:
                    param_types.append(TypeInfo(kind=TypeKind.ANY))
                while self.current().kind == TokenKind.COMMA:
                    self.advance()
                    params.append(self.expect(TokenKind.IDENT).value)
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
                body=self.parse_relation(),
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
        return self.parse_relation()

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
        singular = kind in {
            TypeKind.STATE,
            TypeKind.DRIVE,
            TypeKind.STRING,
            TypeKind.FUNCTION,
            TypeKind.FRACTAL,
            TypeKind.RPM,
        }
        return TypeInfo(kind=kind, domains=tuple(domains), singular=singular)

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
            expr = self.parse_relation()
            self.expect(TokenKind.RPAREN)
            return expr
        if token.kind == TokenKind.RPM:
            self.advance()
            self.expect(TokenKind.LPAREN)
            expr = self.parse_relation()
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
        if token.kind == TokenKind.IDENT:
            name = self.advance().value
            if self.current().kind == TokenKind.LPAREN:
                self.advance()
                args: list[Any] = []
                if self.current().kind != TokenKind.RPAREN:
                    args.append(self.parse_relation())
                    while self.current().kind == TokenKind.COMMA:
                        self.advance()
                        args.append(self.parse_relation())
                self.expect(TokenKind.RPAREN)
                return CallExpr(callee=name, args=args)
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

    def _consume_optional_register(self) -> str | None:
        """Consume and validate an optional `|R` register suffix if present.

        Returns the validated register character (one of {T, A, f, E}) or None
        if no register suffix is present. Rejects invalid values with a CAS
        v7.5 error.
        """
        if self.current().kind == TokenKind.REGISTER:
            return _validate_register_token(self.advance())
        return None

    def parse_state_ref(self) -> StateLiteral:
        """Parse a shorthand state reference like `P3` with optional `|R`."""
        token = self.expect(TokenKind.STATE_REF)
        register = self._consume_optional_register()
        return StateLiteral(
            operator=int(token.value[1:]),
            domain=token.value[0],
            drive=None,
            register=register,
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
        drive: int | None = None
        drive_register: str | None = None

        # Optional Noetic-level register: `^2|T` or `CO-2|T` before the domain.
        noetic_register = self._consume_optional_register()

        if self.current().kind == TokenKind.CARET:
            self.advance()
            domain = self.expect(TokenKind.DOMAIN).value
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

    if isinstance(node, BinaryExpr):
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
                    and left.domains != right.domains
                ):
                    raise CompilerError(CompilerStage.TYPECHECK, "CIRC requires both states to share a domain")
                return TypeInfo(kind=TypeKind.FRACTAL, domains=left.domains or right.domains, singular=True)
            if left.kind == TypeKind.FRACTAL and right.kind in {TypeKind.STATE, TypeKind.ANY}:
                return TypeInfo(kind=TypeKind.FRACTAL, domains=right.domains, singular=True)
            if left.kind in {TypeKind.STATE, TypeKind.ANY} and right.kind == TypeKind.FRACTAL:
                return TypeInfo(kind=TypeKind.FRACTAL, domains=left.domains, singular=True)
            if left.kind == TypeKind.FRACTAL and right.kind == TypeKind.FRACTAL:
                return TypeInfo(kind=TypeKind.FRACTAL, singular=True)
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
    if expected.kind == TypeKind.STRING:
        return isinstance(value, str)
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
        register = instruction.arg.get("register")
        drive_register = instruction.arg.get("drive_register")
        state_index = _state_index(operator, domain)
        drives = {drive: 1.0} if drive is not None else {}
        stack.append(
            StateValue(
                states={state_index: 1.0},
                drive_weights=drives,
                explicit_drive=drive is not None,
                register=register,
                drive_register=drive_register,
            )
        )
        return

    if opcode == "PUSH_STRING":
        stack.append(instruction.arg)
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
                )
                child_tokens = lex(source)
                child_ast = Parser(child_tokens).parse()
                _infer(child_ast, [], TypeEnv(module_dir=os.path.dirname(resolved)))
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

    if opcode == "CALL":
        payload = instruction.arg
        argc = int(payload["argc"])
        args = [stack.pop() for _ in range(argc)]
        args.reverse()
        name = str(payload["name"])

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
            for arg in args:
                if isinstance(arg, StateValue):
                    sequence.append(arg.dominant_operator())
                    domain = domain or arg.dominant_domain()
                elif isinstance(arg, FractalValue):
                    sequence.extend(arg.sequence)
                    domain = domain or arg.domain
                else:
                    raise CompilerError(CompilerStage.EXECUTION, "fractal expects state or fractal arguments")
            composed = 0
            for op in sequence:
                composed = _compose_operators(composed, op)
            stack.append(FractalValue(sequence=sequence, composed_operator=composed, orbit_length=len(sequence), domain=domain))
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
        child_env = RuntimeEnv(parent=env, module_dir=env.module_dir, module_cache=env.module_cache)
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
        if node.register is not None:
            payload["register"] = node.register
        if node.drive_register is not None:
            payload["drive_register"] = node.drive_register
        return payload
    if isinstance(node, DriveLiteral):
        payload = {"node": "DriveLiteral", "drive": f"F{node.drive}"}
        if node.register is not None:
            payload["register"] = node.register
        # CAS v7.6 Section 4 drive-in-domain shorthand `F_k^D|R` surfaces
        # the domain when present. Register-neutral v7.4 drive references
        # produce no new fields.
        if node.domain is not None:
            payload["domain"] = node.domain
        return payload
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
    if isinstance(value, DriveLiteral):
        payload: dict[str, Any] = {"kind": "drive", "drive": f"F{value.drive}"}
        # CAS v7.5: surface register metadata when present.
        if value.register is not None:
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


def _compile_source(source: str, *, module_dir: str | None = None) -> CompilationArtifact:
    try:
        tokens = lex(source)
        parser = Parser(tokens)
        ast = parser.parse()
        warnings: list[str] = []
        type_info = _infer(
            ast,
            warnings,
            TypeEnv(module_dir=module_dir),
        )
        bytecode = lower(ast)
        result = execute(bytecode, env=RuntimeEnv(module_dir=module_dir))
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
    except CompilerError as exc:
        partial_tokens: list[LexToken] = []
        try:
            partial_tokens = lex(source)[:-1]
        except CompilerError:
            partial_tokens = []
        return CompilationArtifact(
            source=source,
            tokens=partial_tokens,
            ast=None,
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
