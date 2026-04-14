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
    "Generative Potential",
    "Directed Attention",
    "Attraction / Affinity",
    "Aversion / Critical Evaluation",
    "Encoding Intensity",
    "Receptive Integration",
    "Projective Assertion",
    "Pattern Entrainment",
    "Causal Initiation",
    "Consequential Grounding",
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

UNICODE_ARROW = "\u2192"
UNICODE_LARROW = "\u2190"
UNICODE_BIARROW = "\u2194"
UNICODE_TIMES = "\u00d7"
UNICODE_DIVIDE = "\u00f7"
UNICODE_PHI = "\u03a6"
UNICODE_LANGLE = "\u27e8"
UNICODE_RANGLE = "\u27e9"

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
    STATE_REF = "STATE_REF"
    DOMAIN = "DOMAIN"
    DRIVE = "DRIVE"
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


@dataclass
class DriveLiteral:
    drive: int


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


@dataclass
class StateValue:
    states: dict[int, float]
    drive_weights: dict[int, float] = field(default_factory=dict)
    explicit_drive: bool = False

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
        )

    def to_dict(self) -> dict[str, Any]:
        dominant = self.dominant_state()
        dom = "PCEO"[dominant // 10]
        op = dominant % 10
        drive = None
        if self.drive_weights:
            drive = max(self.drive_weights, key=self.drive_weights.get)
        return {
            "kind": "state",
            "states": {str(k): round(v, 6) for k, v in sorted(self.states.items())},
            "dominant_state": f"{dom}{op}",
            "dominant_operator": f"CO-{op}",
            "dominant_domain": dom,
            "dominant_drive": f"F{drive}" if drive is not None else None,
        }


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
    (r'"(?:[^"\\]|\\.)*"', TokenKind.STRING),
    (r"CO-\d+", TokenKind.CO),
    (r"[PCEO]\d+", TokenKind.STATE_REF),
    (r"F\d+", TokenKind.DRIVE),
    (r"[PCEO]", TokenKind.DOMAIN),
    (r"\d+", TokenKind.NUMBER),
    (r"\+|\u2295", TokenKind.PLUS),
    (r"-", TokenKind.MINUS),
    (r"\*|" + re.escape(UNICODE_TIMES), TokenKind.TIMES),
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
        if token.kind == TokenKind.CO:
            return self.parse_state()
        if token.kind == TokenKind.STATE_REF:
            token = self.advance()
            return StateLiteral(operator=int(token.value[1:]), domain=token.value[0], drive=None)
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
            drive = int(self.advance().value[1:])
            return DriveLiteral(drive=drive)
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

    def parse_state(self) -> StateLiteral:
        token = self.expect(TokenKind.CO)
        operator = int(token.value.split("-")[1])
        domain = "P"
        drive = None

        if self.current().kind == TokenKind.CARET:
            self.advance()
            domain = self.expect(TokenKind.DOMAIN).value
        if self.current().kind == TokenKind.UNDERSCORE:
            self.advance()
            self.expect(TokenKind.LBRACE)
            drive_token = self.expect(TokenKind.DRIVE)
            drive = int(drive_token.value[1:])
            self.expect(TokenKind.RBRACE)
        return StateLiteral(operator=operator, domain=domain, drive=drive)


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
            require_stateish(left, node.op)
            require_stateish(right, node.op)
            domains = tuple(sorted(set(left.domains) | set(right.domains)))
            return TypeInfo(kind=TypeKind.STATE, domains=domains, singular=False)

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
            require_stateish(left, node.op)
            require_stateish(right, node.op)
            if left.kind != TypeKind.ANY and not left.singular:
                raise CompilerError(CompilerStage.TYPECHECK, f"{node.op} requires singular state operands")
            if right.kind != TypeKind.ANY and not right.singular:
                raise CompilerError(CompilerStage.TYPECHECK, f"{node.op} requires singular state operands")
            if (
                left.kind != TypeKind.ANY
                and right.kind != TypeKind.ANY
                and (len(left.domains) != 1 or len(right.domains) != 1)
            ):
                raise CompilerError(CompilerStage.TYPECHECK, f"{node.op} requires fully resolved domains")
            if left.kind != TypeKind.ANY and right.kind != TypeKind.ANY:
                left_domain = left.domains[0]
                right_domain = right.domains[0]
                if node.op == "ARROW" and DOMAIN_ORDER[left_domain] > DOMAIN_ORDER[right_domain]:
                    raise CompilerError(
                        CompilerStage.TYPECHECK,
                        f"domain descent violated: {left_domain} cannot descend to {right_domain}",
                    )
                if node.op == "LARROW" and DOMAIN_ORDER[right_domain] > DOMAIN_ORDER[left_domain]:
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
                    {"operator": expr.operator, "domain": expr.domain, "drive": expr.drive},
                )
            )
            return
        if isinstance(expr, DriveLiteral):
            bytecode.append(Instruction("PUSH_DRIVE", expr.drive))
            return
        if isinstance(expr, StringLiteral):
            bytecode.append(Instruction("PUSH_STRING", expr.value))
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
        state_index = _state_index(operator, domain)
        drives = {drive: 1.0} if drive is not None else {}
        stack.append(StateValue(states={state_index: 1.0}, drive_weights=drives, explicit_drive=drive is not None))
        return

    if opcode == "PUSH_STRING":
        stack.append(instruction.arg)
        return

    if opcode == "PUSH_DRIVE":
        stack.append(DriveLiteral(int(instruction.arg)))
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
        if not isinstance(left, StateValue) or not isinstance(right, StateValue):
            raise CompilerError(CompilerStage.EXECUTION, "PLUS expects state operands")
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

    if opcode == "MINUS":
        if not isinstance(left, StateValue) or not isinstance(right, StateValue):
            raise CompilerError(CompilerStage.EXECUTION, "MINUS expects state operands")
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
        return {
            "node": "StateLiteral",
            "operator": f"CO-{node.operator}",
            "domain": node.domain,
            "drive": f"F{node.drive}" if node.drive is not None else None,
        }
    if isinstance(node, DriveLiteral):
        return {"node": "DriveLiteral", "drive": f"F{node.drive}"}
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
        return {"kind": "drive", "drive": f"F{value.drive}"}
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
