"""Free-running grammar-constrained AST generation, independent of CAS solving.

Output subset: StateLiteral and ordered BinaryExpr (PLUS/TIMES), as in Q3 G.
This is a serialization grammar, not a semantic executor. Other CAS syntax
remains in scope for future codec versions; it is refused by this version.
Neither the grammar mask nor prediction API receives the source or a target.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Callable

from learner_q4_representation import Bottleneck, Q4InputError

SCHEMA = "helm-cas-expression-lab.q4-ast-prefix/0.1"
TOKENS = ("EOS", "STATE", "BINARY", "PLUS", "TIMES",
          *("N%d" % n for n in range(10)), "D_NONE", "D_P", "D_C", "D_E", "D_O",
          "F_NONE", *("F%d" % n for n in range(1, 8)),
          "REG_ABSENT", "REG_NULL", "REG_A", "REG_f", "REG_E", "REG_T")
TOKEN_IDS = {name: i for i, name in enumerate(TOKENS)}
BOS_ID = len(TOKENS)  # neural decoder input only; never a predicted output


class CodecError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class DecodeLimits:
    max_nodes: int = 127
    max_depth: int = 16
    max_tokens: int = 1024

    def __post_init__(self):
        for name, ceiling in (("max_nodes", 127), ("max_depth", 16), ("max_tokens", 1024)):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= ceiling:
                raise CodecError("INVALID_INPUT: %s must be in 1..%d" % (name, ceiling))


_FIELDS = {
    "noetic": frozenset("N%d" % n for n in range(10)),
    "domain": frozenset(("D_NONE", "D_P", "D_C", "D_E", "D_O")),
    "drive": frozenset(("F_NONE", *("F%d" % n for n in range(1, 8)))),
    "register": frozenset(("REG_ABSENT", "REG_NULL", "REG_A", "REG_f", "REG_E", "REG_T")),
    "op": frozenset(("PLUS", "TIMES")),
}


def allowed_next(prefix: tuple[int, ...], limits: DecodeLimits = DecodeLimits()) -> tuple[int, ...]:
    """A mask derived ONLY from generated history and public size limits."""
    if type(prefix) is not tuple:
        raise CodecError("INVALID_INPUT: output history must be a tuple")
    if len(prefix) > limits.max_tokens:
        raise CodecError("BUDGET_EXHAUSTED: oversized output history")
    pending = [("expr", 0)]
    nodes = 0

    def names():
        if not pending:
            return frozenset(("EOS",))
        slot, depth = pending[-1]
        if slot != "expr":
            return _FIELDS[slot]
        # Reserve at least one node for each other unfinished subtree.
        needed = sum(kind == "expr" for kind, _ in pending)
        result = {"STATE"} if nodes + needed <= limits.max_nodes else set()
        if depth < limits.max_depth and nodes + needed + 2 <= limits.max_nodes:
            result.add("BINARY")
        return frozenset(result)

    for index, token in enumerate(prefix):
        if type(token) is not int or not 0 <= token < len(TOKENS) or TOKENS[token] not in names():
            raise CodecError("INVALID_INPUT: invalid AST prefix at token %d" % index)
        name = TOKENS[token]
        if name == "EOS":
            if index != len(prefix) - 1:
                raise CodecError("INVALID_INPUT: tokens after EOS")
            return ()
        slot, depth = pending.pop()
        if slot == "expr":
            nodes += 1
            if name == "STATE":
                pending.extend((kind, depth) for kind in ("register", "drive", "domain", "noetic"))
            else:
                pending.extend((("expr", depth + 1), ("expr", depth + 1), ("op", depth)))
    return tuple(sorted(TOKEN_IDS[name] for name in names()))


def ast_to_tokens(ast: dict, limits: DecodeLimits = DecodeLimits()) -> tuple[int, ...]:
    """TRAINING/EVALUATOR codec; prediction never calls this function.

Reject unknown nodes/fields instead of erasing task-relevant structure. The
caller, not this codec, decides whether an AST is a permitted training target.
"""
    names: list[str] = []
    nodes = 0

    def visit(node, depth):
        nonlocal nodes
        nodes += 1
        if depth > limits.max_depth or nodes > limits.max_nodes:
            raise CodecError("BUDGET_EXHAUSTED: AST is too large")
        if type(node) is not dict:
            raise CodecError("INVALID_INPUT: AST node must be an object")
        if node.get("node") == "StateLiteral":
            if set(node) not in ({"node", "operator", "domain", "drive"},
                                 {"node", "operator", "domain", "drive", "register"}):
                raise CodecError("UNSUPPORTED_OPERATION: StateLiteral fields")
            operator, domain, drive = node["operator"], node["domain"], node["drive"]
            if type(operator) is not str or operator not in tuple("^%d" % n for n in range(10)):
                raise CodecError("INVALID_INPUT: state operator")
            if domain is not None and (type(domain) is not str or domain not in ("P", "C", "E", "O")):
                raise CodecError("INVALID_INPUT: state domain")
            if drive is not None and (type(drive) is not str or drive not in tuple("F%d" % n for n in range(1, 8))):
                raise CodecError("INVALID_INPUT: state drive")
            reg = "REG_ABSENT"
            if "register" in node:
                value = node["register"]
                if value is not None and (type(value) is not str or value not in ("A", "f", "E", "T")):
                    raise CodecError("INVALID_INPUT: state register")
                reg = "REG_NULL" if value is None else "REG_" + value
            names.extend(("STATE", "N" + operator[1:], "D_NONE" if domain is None else "D_" + domain,
                          "F_NONE" if drive is None else drive, reg))
        elif node.get("node") == "BinaryExpr":
            if set(node) != {"node", "op", "left", "right"} or node.get("op") not in ("PLUS", "TIMES"):
                raise CodecError("UNSUPPORTED_OPERATION: BinaryExpr fields or operation")
            names.extend(("BINARY", node["op"]))
            visit(node["left"], depth + 1)
            visit(node["right"], depth + 1)
        else:
            raise CodecError("UNSUPPORTED_OPERATION: AST node type")

    visit(ast, 0)
    result = tuple(TOKEN_IDS[name] for name in (*names, "EOS"))
    if len(result) > limits.max_tokens:
        raise CodecError("BUDGET_EXHAUSTED: AST token count")
    return result


def tokens_to_ast(tokens: tuple[int, ...], limits: DecodeLimits = DecodeLimits()) -> dict:
    if not tokens or tokens[-1] != TOKEN_IDS["EOS"] or allowed_next(tokens, limits):
        raise CodecError("INVALID_INPUT: complete AST plus EOS required")
    stream = iter(TOKENS[token] for token in tokens)

    def node():
        kind = next(stream)
        if kind == "BINARY":
            op = next(stream)
            left = node()
            right = node()
            return {"node": "BinaryExpr", "op": op, "left": left, "right": right}
        operator, domain, drive, register = (next(stream) for _ in range(4))
        result = {"node": "StateLiteral", "operator": "^" + operator[1:],
                  "domain": None if domain == "D_NONE" else domain[2:],
                  "drive": None if drive == "F_NONE" else drive}
        if register != "REG_ABSENT":
            result["register"] = None if register == "REG_NULL" else register[4:]
        return result

    return node()


@dataclass(frozen=True, slots=True)
class DecodeResult:
    outcome: str
    tokens: tuple[int, ...]
    ast: dict | None
    steps: int


def free_decode(bottleneck: Bottleneck,
                next_logits: Callable[[Bottleneck, tuple[int, ...]], tuple[float, ...]],
                limits: DecodeLimits = DecodeLimits()) -> DecodeResult:
    """Greedy free-running decode; no target, source, cache, or teacher history.

The callback gets only the bottleneck and predictions made so far. Grammar
masking is syntactic and independent of the answer; lowest token ID breaks ties.
A Python callback is trusted code, not an OS sandbox. This API does not establish
independent evaluator custody or prevent malicious closure/file access.
"""
    if type(bottleneck) is not Bottleneck:
        raise Q4InputError("INVALID_INPUT: strict bottleneck required")
    prefix: tuple[int, ...] = ()
    for step in range(1, limits.max_tokens + 1):
        logits = next_logits(bottleneck, prefix)
        try:
            valid_logits = (type(logits) is tuple and len(logits) == len(TOKENS)
                            and all(type(x) in (int, float) and isfinite(x) for x in logits))
        except (OverflowError, TypeError):
            valid_logits = False
        if not valid_logits:
            return DecodeResult("NUMERICAL_FAILURE", prefix, None, step)
        allowed = allowed_next(prefix, limits)
        if not allowed:
            return DecodeResult("BUDGET_EXHAUSTED", prefix, None, step)
        chosen = min(allowed, key=lambda token: (-logits[token], token))
        prefix += (chosen,)
        if chosen == TOKEN_IDS["EOS"]:
            return DecodeResult("GENERATED", prefix, tokens_to_ast(prefix, limits), step)
    return DecodeResult("BUDGET_EXHAUSTED", prefix, None, limits.max_tokens)
