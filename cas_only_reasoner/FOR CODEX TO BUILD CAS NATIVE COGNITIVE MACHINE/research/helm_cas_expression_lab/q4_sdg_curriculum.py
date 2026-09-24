"""Q4-SDG-1 lesson adapter 0.1 -- CAS expression text -> exact ordered tree lessons for Q4. NON-NEURAL.

Q4 is the width-64 GRU that reads CAS expression text and rebuilds the ordered expression tree. This module makes
teaching rows for it. It imports no torch. It trains nothing. It never opens an evaluation or sealed Q3 file.

Specification: the owner's directive Q4_SDG_AND_TARGETED_FEEDBACK_DIRECTIVE_20260923.md, sections 3-8
(sha256 b2092d01..., byte copy at 8eb798a5). Experiment id Q4-SDG-1. Every result is CLAUDE_BUILT_CLAUDE_CHECKED
until an independent review.

ONE CANONICAL SURFACE. Every observation is written one way only:
  leaf    ^n^D  then optional _{Fk}  then optional |R     (n 0-9, D in P C E O, k 1-7, R in T A f E)
  branch  (left + right)  or  (left × right)              (always bracketed, one space around the operator)
A domain is ALWAYS written. A register is only ever the tail |R. Why: the pinned compiler reads a missing domain
as P, and reads ^8|A^C as the same tree as ^8^C|A, so two different texts would share one target.

EVERY ROW IS CHECKED, NOT TRUSTED. The constructor builds the intended tree. The text is rendered from it.
The pinned compiler (historical_compiler, LF sha256 61ed5a45...) compiles the text. The row is kept only if:
the compile is valid; the compiled tree, in lab spelling, EQUALS the intended tree; the output codec accepts it
(an UNSUPPORTED_OPERATION is refused and counted, never simplified); tokens -> tree -> tokens round-trips; and the
bare shape is allowed. A mismatch between the compiled and intended tree stops the build (fail closed).

ALLOWED SHAPES (exclusion proof without opening any eval file). Generated rows use only the single state L or one
of the 16 bare shapes of Q3 v0.7 family-G TRAIN, all of depth <= 3. The 9 family-G DEV bare shapes, including the
4-leaf left chain (((L L) L) L), key f5844b5735f0fe95, are forbidden. Q3 G eval is depths 4-5, so depth <= 3
excludes every eval shape by construction. The 16 and 9 keys are frozen below; a test recomputes them from the
VISIBLE train and dev files only.

LESSON FAMILIES (directive section 5). Every row belongs to a group; the group id is assigned when the group is
made, BEFORE any split, and a whole group goes to one split.
  A  one state: balanced over 10 Noetics x 4 Domains x {none, F1-F7} x {none, T, A, f, E}; plus one-field pairs
     that differ in exactly one token of the COMPILED token stream (noetic, domain, drive or register).
  B  two ordered parts (depth 1, unequal leaves): left/right swap pairs; PLUS/TIMES swap pairs.
  C  grouping: same leaves and operators, different brackets (3 leaves; 4 leaves in the 3 allowed bracketings);
     then operator-only pairs, leaf-only pairs, and a mixed set over all 16 allowed shapes.
  D  mistake-driven: first_wrong_decision() names the first wrong choice; build_d_round() makes fresh rows of that
     kind plus controls. Triggers may come only from this package's TRAIN rows or its FEEDBACK panel (own seed).
     Never from the package's dev split, never from the old 16 Q3 dev rows, never from eval.

FILES. visible_<lesson>_<split>.jsonl carries ONLY {record_id, lesson_family, mode, observation}. The target sidecar
sealed_<lesson>_<split>.jsonl carries the tree, tokens, per-position slot kinds, group, changed field and
provenance. The sealed_ prefix puts it under the existing learner guard (no learner* file may name sealed_).

Build (AWS, not this laptop):  python -B q4_sdg_curriculum.py --build --out data/q4_sdg_v0_1 --size 4096
"""
from __future__ import annotations

import argparse
import collections
import copy
import hashlib
import itertools
import json
import os
from pathlib import Path
import random
import re
import shutil
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import historical_compiler  # noqa: E402  -- the pinned compiler snapshot, hash-checked on every load
import q3_behaviour_records as q3  # noqa: E402  -- read-only reuse: canonical, shapes, spelling maps
from learner_q4_decoder import TOKENS, CodecError, allowed_next, ast_to_tokens, tokens_to_ast  # noqa: E402
from q4_panel_evaluation import shape_key as panel_shape_key  # noqa: E402  -- Codex's shape-key definition

SCHEMA = "helm-cas-expression-lab.q4-sdg-lessons/0.1"
D_SCHEMA = "helm-cas-expression-lab.q4-sdg-lessons-d/0.1"
TRIGGERS_SCHEMA = "helm-cas-expression-lab.q4-sdg-triggers/0.1"
PINS_SCHEMA = "helm-cas-expression-lab.q4-sdg-data-pins/0.1"
EXPERIMENT = "Q4-SDG-1"
LABEL = "CLAUDE_BUILT_CLAUDE_CHECKED"

SEED = 20260941             # main lessons (train + dev). New: Q3 used 20260921..20260925.
FEEDBACK_SEED = 20260951    # the designated public feedback panel, on its own seed
Q3_SEEDS = tuple(range(20260921, 20260926))
DEFAULT_OUT = Path("data") / "q4_sdg_v0_1"
PINS = HERE / "Q4_SDG_DATA_PINS.json"
Q3_DATA = HERE / "data" / "q3_v0_7"

LESSONS = ("A", "B", "C")               # the static package; D rounds are built later from triggers
SPLITS = ("train", "dev", "feedback")
TRIGGER_SPLITS = ("train", "feedback")
MODE = "reconstruction"
VISIBLE_KEYS = frozenset(("record_id", "lesson_family", "mode", "observation"))
SEALED_KEYS = frozenset((
    "record_id", "lesson_family", "subfamily", "group_id", "group_size", "changed_field", "target_ast",
    "target_canonical_ast", "target_tokens", "slot_kinds", "slot_paths", "content_sha256",
    "ordered_operator_shape_sha256", "ordered_bare_shape_sha256", "q3_tree_shape_key", "strict_shape_key",
    "depth", "ast_size", "leaf_count", "shape_text", "provenance"))

FIELDS = ("noetic", "domain", "drive", "register")
NOETICS = tuple(range(10))
DOMAINS = ("P", "C", "E", "O")
DRIVES = (None, 1, 2, 3, 4, 5, 6, 7)
REGISTERS = (None, "T", "A", "f", "E")
VALUES = {"noetic": NOETICS, "domain": DOMAINS, "drive": DRIVES, "register": REGISTERS}
OPS = ("PLUS", "TIMES")
OP_TEXT = {"PLUS": "+", "TIMES": "×"}
TEXT_OP = {text: op for op, text in OP_TEXT.items()}

# Q3 files this experiment must never change. Values read from records/q4_authorized_20260922/plan.json
# (source_pins and pins_file_sha256) and from Q3_DATA_PINS.json; a test re-reads both.
Q3_IMMUTABLE_LF_SHA256 = {
    "q3_behaviour_records.py": "5b3e03cd3b8bc1eac044e30b99781c0e1229e1039f5775b52848582055473787",
    "q3_load.py": "534f486a4cea6ef721f0a62853951d351f79c3a4d7167d554289b6d72a93bb7d",
    "Q3_DATA_PINS.json": "e67fb880bf3f8b9e4802e5567572ee4970a25bc3209999bc4dda4eea6d3968fc",
}
Q3_V07_MANIFEST_SHA256 = "1cf98a2b48ade4acf12c51c0cc74d3dd2504f7eb0e7d24662fe8b6f7d29f8bf9"

# Bare-shape key = first 16 hex of sha256 of the compact sorted JSON of q3.tree_shape (the Q3 tree_shape_key).
G_TRAIN_SHAPES = {   # Q3 v0.7 family G, visible train: 2,048 rows, 16 bare shapes, depths 1-3
    "05fdd4728b8ca588": "(L (L L))",
    "1e11e6ee0747e36b": "(L ((L L) (L L)))",
    "31c44c64e094539b": "(L L)",
    "3baf126600ac57fe": "(((L L) (L L)) (L L))",
    "5c288aa816d66f85": "((L (L L)) L)",
    "5c4d93b89d34fd97": "((L L) (L (L L)))",
    "720ca796c1fa5b66": "((L (L L)) ((L L) L))",
    "80140e17118d40d9": "(((L L) L) ((L L) L))",
    "8d4e8c0eaeb89072": "(((L L) L) (L L))",
    "b233e9e9a57824c5": "(L (L (L L)))",
    "b6ac3a0f67c5aafd": "((L L) L)",
    "b6bd6888c87a4e84": "(((L L) (L L)) L)",
    "c0c59cb447886151": "((L L) (L L))",
    "cd624003d788ad55": "((L L) ((L L) (L L)))",
    "d302f357d770efad": "(((L L) L) (L (L L)))",
    "d7f357ceacd695a4": "((L (L L)) (L (L L)))",
}
G_DEV_SHAPES = {     # Q3 v0.7 family G, visible dev: 256 rows, 9 bare shapes, all depth 3 -- FORBIDDEN here
    "0752986cdd9d2333": "((L (L L)) ((L L) (L L)))",
    "12e026df9873e4e4": "((L L) ((L L) L))",
    "26d2d48fb6249840": "(((L L) (L L)) ((L L) L))",
    "44bb65bea0e68da4": "(L ((L L) L))",
    "7e93530d990a7fbc": "(((L L) L) ((L L) (L L)))",
    "8de25468a32ae305": "((L (L L)) (L L))",
    "bbbcee41f6d4e232": "(((L L) (L L)) (L (L L)))",
    "ce4d93b59c124a9f": "(((L L) (L L)) ((L L) (L L)))",
    "f5844b5735f0fe95": "(((L L) L) L)",
}
SINGLE_STATE_KEY = "8463f556f97cf8fd"   # key of the bare shape "L" (one state); declared new to condition B
MAX_DEPTH = 3
C_SHAPES = {3: ("((L L) L)", "(L (L L))"),
            4: ("((L (L L)) L)", "((L L) (L L))", "(L (L (L L)))")}   # the other two 4-leaf bracketings are G dev

# PROPOSED pool mixture (share of the TRAIN pool, in rows). Not a decision: see Q4_SDG_LESSONS_SPEC_v0_1.md.
SUBFAMILIES = (("A", "single"), ("A", "one_field_pair"), ("B", "swap_pair"), ("B", "op_pair"),
               ("C", "grouping"), ("C", "operator_only"), ("C", "leaf_only"), ("C", "mixed_allowed_shapes"))
MIXTURE = {("A", "single"): 0.125, ("A", "one_field_pair"): 0.125,
           ("B", "swap_pair"): 0.125, ("B", "op_pair"): 0.125,
           ("C", "grouping"): 0.15, ("C", "operator_only"): 0.10, ("C", "leaf_only"): 0.10,
           ("C", "mixed_allowed_shapes"): 0.15}
MIN_GROUP = {"single": 1, "one_field_pair": 2, "swap_pair": 2, "op_pair": 2, "grouping": 2,
             "operator_only": 2, "leaf_only": 2, "mixed_allowed_shapes": 1}
DEV_FRACTION = 1 / 16
FEEDBACK_FRACTION = 1 / 16
A_DISTINCT_CAP = 1200        # of the 1,600 single-state cells, across all splits; the rest is kept for D
SIZE_RANGE = (16, 262144)
MISTAKES = ("LOST_BRANCH", "INVENTED_BRANCH", "PLUS_FOR_TIMES", "TIMES_FOR_PLUS", "WRONG_NOETIC", "WRONG_DOMAIN",
            "WRONG_DRIVE", "WRONG_REGISTER", "PREDICTION_ENDED", "GRAMMAR_VIOLATION")


class LessonError(ValueError):
    """Fail closed. The message starts with a code, e.g. 'CONSTRUCTOR_MISMATCH: ...'."""


class Refusal(Exception):
    """One candidate row or group is refused and counted. The build continues."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def sha256_hex(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def lf_sha256(path) -> str:
    return sha256_hex(Path(path).read_bytes().replace(b"\r\n", b"\n"))


def record_id(schema, seed, lesson, split, index):
    """sha256 of the raw UTF-8 string '<schema>:<seed>:<lesson>:<split>:<index>', first 24 hex. Position only."""
    return sha256_hex(("%s:%d:%s:%s:%d" % (schema, seed, lesson, split, index)).encode("utf-8"))[:24]


def _rng(*parts):
    """A named, seeded stream. String seeds are hashed by CPython (sha512), so streams are stable across runs."""
    return random.Random("|".join(str(p) for p in (SCHEMA,) + parts))


# ------------------------------------------------------------------------------------------------------------
# Shapes
# ------------------------------------------------------------------------------------------------------------
def parse_shape(text):
    """'((L L) L)' -> ['B', ['B', 'L', 'L'], 'L'] (the q3.tree_shape form)."""
    tokens = text.replace("(", " ( ").replace(")", " ) ").split()

    def parse(i):
        if tokens[i] == "L":
            return "L", i + 1
        if tokens[i] != "(":
            raise LessonError("SHAPE_TEXT_INVALID: %r" % text)
        left, i = parse(i + 1)
        right, i = parse(i)
        if tokens[i] != ")":
            raise LessonError("SHAPE_TEXT_INVALID: %r" % text)
        return ["B", left, right], i + 1
    try:
        shape, end = parse(0)
    except IndexError:
        raise LessonError("SHAPE_TEXT_INVALID: %r" % text) from None
    if end != len(tokens):
        raise LessonError("SHAPE_TEXT_INVALID: %r" % text)
    return shape


def shape_text(shape):
    return "L" if shape == "L" else "(%s %s)" % (shape_text(shape[1]), shape_text(shape[2]))


def bare_key16(shape):
    return q3._sha_json(shape)[:16]


def shape_allowed(key16, depth):
    return (depth <= MAX_DEPTH and key16 not in G_DEV_SHAPES
            and (key16 in G_TRAIN_SHAPES or key16 == SINGLE_STATE_KEY))


def node_at(shape, path):
    """'B', 'L', or None (no node at that path). A path is a string of L/R steps from the root ('' = root)."""
    for step in path:
        if shape == "L":
            return None
        shape = shape[1] if step == "L" else shape[2]
    return "L" if shape == "L" else "B"


def allowed_shapes():
    """Every allowed bare shape: the 16 G-train shapes and the single state, sorted by key."""
    shapes = [(key, parse_shape(text)) for key, text in sorted(G_TRAIN_SHAPES.items())]
    return [(SINGLE_STATE_KEY, "L")] + shapes


# ------------------------------------------------------------------------------------------------------------
# Trees and the one canonical surface
# ------------------------------------------------------------------------------------------------------------
def leaf_ast(n, domain, drive=None, register=None):
    node = {"node": "StateLiteral", "operator": "^%d" % n, "domain": domain,
            "drive": None if drive is None else "F%d" % drive}
    if register is not None:
        node["register"] = register
    return node


def binary(op, left, right):
    return {"node": "BinaryExpr", "op": op, "left": left, "right": right}


def leaf_cell(leaf):
    drive = leaf["drive"]
    return (int(leaf["operator"][1:]), leaf["domain"], None if drive is None else int(drive[1:]), leaf.get("register"))


def random_leaf(rng):
    """The same draws, in the same order, as q3_behaviour_records._random_literal (a test checks this)."""
    n, domain = rng.randrange(10), rng.choice(q3.ref.DOMAINS)
    drive = rng.randrange(1, 8) if rng.random() < 0.5 else None
    register = rng.choice(("T", "A", "f", "E")) if rng.random() < 0.5 else None
    return leaf_ast(n, domain, drive, register)


def fill_shape(shape, leaves, ops):
    """Leaves and operators in reading (in-order) order: an operator sits between its two subtrees."""
    leaves, ops = iter(leaves), iter(ops)

    def build(node):
        if node == "L":
            return copy.deepcopy(next(leaves))
        left = build(node[1])
        op = next(ops)
        return binary(op, left, build(node[2]))
    tree = build(shape)
    if next(leaves, None) is not None or next(ops, None) is not None:
        raise LessonError("FILL_COUNT_MISMATCH")
    return tree


def leaves_of(ast):
    return [ast] if ast["node"] == "StateLiteral" else leaves_of(ast["left"]) + leaves_of(ast["right"])


def ops_of(ast):
    return [] if ast["node"] == "StateLiteral" else ops_of(ast["left"]) + [ast["op"]] + ops_of(ast["right"])


def get_at(ast, path):
    for step in path:
        ast = ast["left"] if step == "L" else ast["right"]
    return ast


def replace_at(ast, path, new):
    if not path:
        return copy.deepcopy(new)
    out = copy.deepcopy(ast)
    parent = get_at(out, path[:-1])
    parent["left" if path[-1] == "L" else "right"] = copy.deepcopy(new)
    return out


def leaf_paths(ast, path=""):
    if ast["node"] == "StateLiteral":
        return [path]
    return leaf_paths(ast["left"], path + "L") + leaf_paths(ast["right"], path + "R")


def render_ast(ast):
    """Lab AST -> the one canonical text. Refuses anything the surface cannot write without ambiguity."""
    if type(ast) is not dict:
        raise LessonError("SURFACE_NOT_CANONICAL: node must be an object")
    if ast.get("node") == "StateLiteral":
        if set(ast) not in ({"node", "operator", "domain", "drive"}, {"node", "operator", "domain", "drive", "register"}):
            raise LessonError("UNSUPPORTED_OPERATION: StateLiteral fields %s" % sorted(ast))
        operator, domain, drive = ast["operator"], ast["domain"], ast["drive"]
        if type(operator) is not str or re.fullmatch(r"\^[0-9]", operator) is None:
            raise LessonError("SURFACE_NOT_CANONICAL: noetic %r" % (operator,))
        if domain not in DOMAINS:
            raise LessonError("SURFACE_NOT_CANONICAL: an explicit domain is required, got %r" % (domain,))
        if drive is not None and (type(drive) is not str or re.fullmatch(r"F[1-7]", drive) is None):
            raise LessonError("SURFACE_NOT_CANONICAL: drive %r" % (drive,))
        text = "^%s^%s" % (operator[1], domain)
        if drive is not None:
            text += "_{%s}" % drive
        if "register" in ast:
            if ast["register"] not in ("T", "A", "f", "E"):
                raise LessonError("SURFACE_NOT_CANONICAL: register %r has no canonical text" % (ast["register"],))
            text += "|" + ast["register"]
        return text
    if ast.get("node") == "BinaryExpr":
        if set(ast) != {"node", "op", "left", "right"} or ast["op"] not in OP_TEXT:
            raise LessonError("UNSUPPORTED_OPERATION: BinaryExpr fields or operation")
        return "(%s %s %s)" % (render_ast(ast["left"]), OP_TEXT[ast["op"]], render_ast(ast["right"]))
    raise LessonError("UNSUPPORTED_OPERATION: node type %r" % (ast.get("node"),))


_LEAF = re.compile(r"\^([0-9])\^([PCEO])(?:_\{F([1-7])\})?(?:\|([TAfE]))?")


def parse_surface(text):
    """The canonical surface -> lab AST, without the compiler. Anything else is SURFACE_NOT_CANONICAL."""
    if type(text) is not str:
        raise LessonError("SURFACE_NOT_CANONICAL: text required")

    def expr(i):
        if text.startswith("(", i):
            left, i = expr(i + 1)
            if text[i] != " " or text[i + 1] not in TEXT_OP or text[i + 2] != " ":
                raise LessonError("SURFACE_NOT_CANONICAL: operator at %d" % i)
            op = TEXT_OP[text[i + 1]]
            right, i = expr(i + 3)
            if text[i] != ")":
                raise LessonError("SURFACE_NOT_CANONICAL: missing ')' at %d" % i)
            return binary(op, left, right), i + 1
        match = _LEAF.match(text, i)
        if match is None:
            raise LessonError("SURFACE_NOT_CANONICAL: leaf at %d" % i)
        return (leaf_ast(int(match[1]), match[2], None if match[3] is None else int(match[3]), match[4]),
                match.end())
    try:
        tree, end = expr(0)
    except (IndexError, RecursionError):
        raise LessonError("SURFACE_NOT_CANONICAL: truncated") from None
    if end != len(text):
        raise LessonError("SURFACE_NOT_CANONICAL: trailing text")
    return tree


def is_canonical_surface(text):
    try:
        return render_ast(parse_surface(text)) == text
    except LessonError:
        return False


# ------------------------------------------------------------------------------------------------------------
# Output token slots and the first wrong decision (torch-free; used by training diagnostics and family D)
# ------------------------------------------------------------------------------------------------------------
def _kind_of_name(name):
    if name == "EOS":
        return "eos"
    if name in ("STATE", "BINARY"):
        return "expr"
    if name in OPS:
        return "op"
    if name.startswith("REG_"):
        return "register"
    if name.startswith("D_"):
        return "domain"
    if name == "F_NONE" or re.fullmatch(r"F[1-7]", name):
        return "drive"
    if re.fullmatch(r"N[0-9]", name):
        return "noetic"
    raise LessonError("UNKNOWN_TOKEN: %r" % name)


def slot_kind(prefix):
    """The kind of decision the grammar asks for after `prefix`, read from allowed_next itself."""
    kinds = {_kind_of_name(TOKENS[t]) for t in allowed_next(tuple(prefix))}
    if len(kinds) != 1:
        raise LessonError("SLOT_KIND_AMBIGUOUS: %s" % sorted(kinds))
    return kinds.pop()


def token_slots(tokens):
    """Per position: its slot kind and the tree path of its node ('' root, then L/R steps).

The kind is taken from allowed_next; the path from a stack that mirrors the codec's order. They must agree.
"""
    tokens = tuple(tokens)
    pending = [("expr", "")]
    out = []
    for index, token in enumerate(tokens):
        if not pending:
            if TOKENS[token] != "EOS":
                raise LessonError("TOKENS_AFTER_COMPLETE_TREE")
            kind, path = "eos", ""
        else:
            kind, path = pending.pop()
        if kind != slot_kind(tokens[:index]):
            raise LessonError("SLOT_STACK_DISAGREES_WITH_GRAMMAR at %d" % index)
        out.append({"slot": kind, "path": path})
        name = TOKENS[token]
        if kind == "expr" and name == "STATE":
            pending.extend((k, path) for k in ("register", "drive", "domain", "noetic"))
        elif kind == "expr" and name == "BINARY":
            pending.extend((("expr", path + "R"), ("expr", path + "L"), ("op", path)))
    return out


_FIELD_MISTAKE = {"noetic": "WRONG_NOETIC", "domain": "WRONG_DOMAIN", "drive": "WRONG_DRIVE",
                  "register": "WRONG_REGISTER"}


def first_wrong_decision(pred_tokens, target_tokens):
    """None if the prediction equals the target; else the first differing position and what kind of choice it was.

expr slot -> LOST_BRANCH (chose STATE where BINARY belonged) or INVENTED_BRANCH (the reverse);
op slot   -> PLUS_FOR_TIMES or TIMES_FOR_PLUS; a field slot -> WRONG_<FIELD>.
PREDICTION_ENDED: the prediction stopped (budget/numerical failure) before the target did.
GRAMMAR_VIOLATION: the predicted token is not allowed there (possible for raw, unmasked argmax only).
"""
    pred, target = tuple(pred_tokens), tuple(target_tokens)
    tokens_to_ast(target)  # the target must be one complete tree plus EOS
    slots = token_slots(target)
    for index, gold in enumerate(target):
        where = {"index": index, "slot": slots[index]["slot"], "path": slots[index]["path"],
                 "target": TOKENS[gold]}
        if index >= len(pred):
            return dict(where, mistake="PREDICTION_ENDED", predicted=None)
        if pred[index] == gold:
            continue
        predicted = TOKENS[pred[index]] if type(pred[index]) is int and 0 <= pred[index] < len(TOKENS) else None
        where["predicted"] = predicted
        if pred[index] not in allowed_next(target[:index]):
            return dict(where, mistake="GRAMMAR_VIOLATION")
        kind = where["slot"]
        if kind == "expr":
            return dict(where, mistake="LOST_BRANCH" if TOKENS[gold] == "BINARY" else "INVENTED_BRANCH")
        if kind == "op":
            return dict(where, mistake="PLUS_FOR_TIMES" if predicted == "PLUS" else "TIMES_FOR_PLUS")
        return dict(where, mistake=_FIELD_MISTAKE[kind])
    if len(pred) > len(target):
        extra = pred[len(target)]
        return {"index": len(target), "slot": "eos", "path": "", "target": None, "mistake": "GRAMMAR_VIOLATION",
                "predicted": TOKENS[extra] if type(extra) is int and 0 <= extra < len(TOKENS) else None}
    return None


# ------------------------------------------------------------------------------------------------------------
# The pinned compiler and the per-row check
# ------------------------------------------------------------------------------------------------------------
class Compiler:
    """The pinned pre-CAS-Ohm compiler. The optional Rust cas_engine changes the engine label; it is recorded."""

    def __init__(self):
        module = historical_compiler.load_historical_compiler()
        self.compile_expression = module.compile_expression
        self.engine = "rust+python" if getattr(module, "cas_engine", None) is not None else "python"
        self.receipt = dict(historical_compiler.source_receipt(), engine=self.engine)


def _compiler_reason(error):
    text = (error or "").lower()
    if "domain ascent" in text:
        return "COMPILER_REFUSED:TIMES_DOMAIN_ASCENT"
    if "clarification 10" in text:
        return "COMPILER_REFUSED:TIMES_SAME_CORE_MULTI_REGISTER"
    if "singular" in text:
        return "COMPILER_REFUSED:TIMES_OPERAND_NOT_SINGULAR"
    return "COMPILER_REFUSED:OTHER"


def codec_or_refuse(target):
    """Output codec gate: an unsupported node is REFUSED and counted, never simplified to fit."""
    try:
        return ast_to_tokens(target)
    except CodecError as error:
        raise Refusal("UNSUPPORTED_OPERATION" if "UNSUPPORTED_OPERATION" in str(error) else "CODEC_REFUSED") from None


def describe(target):
    """Content and shape identities of a checked target tree (stored in the sealed sidecar only)."""
    shape = q3.tree_shape(target)
    bare = panel_shape_key(target, operators=False)
    key16 = q3._sha_json(shape)[:16]
    if bare[:16] != key16:
        raise LessonError("BARE_KEY_DEFINITIONS_DISAGREE")
    return {"content_sha256": sha256_hex(q3.canonical(target).encode("utf-8")),
            "ordered_operator_shape_sha256": panel_shape_key(target),
            "ordered_bare_shape_sha256": bare, "q3_tree_shape_key": key16,
            "strict_shape_key": q3._sha_json(q3.strict_shape(q3.to_compiler_spelling(target)))[:16],
            "depth": q3.tree_depth(shape), "ast_size": q3._ast_size(target),
            "leaf_count": len(leaves_of(target)), "shape_text": shape_text(shape)}


def check_intended(intended, compiler):
    """Render, compile, compare, and apply the lesson shape rule. Refusal = counted; LessonError = fail closed."""
    row = compile_intended(intended, compiler)
    if not shape_allowed(row["q3_tree_shape_key"], row["depth"]):
        raise Refusal("FORBIDDEN_SHAPE")
    return row


def compile_intended(intended, compiler):
    """Render, compile, compare -- WITHOUT the lesson shape rule (diagnostics use it on dev-shaped rows)."""
    try:
        observation = render_ast(intended)
    except LessonError as error:
        raise Refusal(str(error).split(":")[0]) from None
    if parse_surface(observation) != intended:
        raise LessonError("SURFACE_ROUNDTRIP_FAILED: %s" % observation)
    artifact = compiler.compile_expression(observation).to_dict()
    if artifact.get("engine") != compiler.engine:
        raise LessonError("COMPILER_ENGINE_CHANGED")
    if not artifact["valid"] or artifact["ast"] is None:
        raise Refusal(_compiler_reason(artifact.get("error")))
    target = q3.to_lab_spelling(artifact["ast"])
    if q3.to_compiler_spelling(target) != artifact["ast"]:
        raise LessonError("SPELLING_NOT_INVERTIBLE: %s" % observation)
    tokens = codec_or_refuse(target)
    if tokens_to_ast(tokens) != target:
        raise LessonError("CODEC_ROUNDTRIP_FAILED: %s" % observation)
    if target != intended:
        raise LessonError("CONSTRUCTOR_MISMATCH: %s" % observation)
    info = describe(target)
    slots = token_slots(tokens)
    return {"observation": observation, "target_ast": target, "target_tokens": list(tokens),
            "slot_kinds": [s["slot"] for s in slots], "slot_paths": [s["path"] for s in slots],
            "compiler": {"sha256_lf": historical_compiler.SHA256_LF, "engine": artifact["engine"],
                         "warnings": list(artifact["warnings"])}, **info}


def differing_positions(a, b):
    if len(a) != len(b):
        return None
    return [i for i, (x, y) in enumerate(zip(a, b)) if x != y]


# ------------------------------------------------------------------------------------------------------------
# Family makers. Each returns a list of checked rows (one group) or raises Refusal.
# ------------------------------------------------------------------------------------------------------------
class BalancedCells:
    """Family A cells: 10 Noetics x 4 Domains x 8 drive options x 5 register options = 1,600, each at most once.

Each pick is the first unused cell, in a seeded shuffled order, with the lowest marginal load (counts scaled by
each field's number of values). This keeps every field's value counts close to equal; the counts are logged.
"""
    CARD = {"noetic": 10, "domain": 4, "drive": 8, "register": 5}

    def __init__(self, rng, used):
        self.order = list(itertools.product(NOETICS, DOMAINS, DRIVES, REGISTERS))
        rng.shuffle(self.order)
        self.used = used
        self.counts = {field: collections.Counter() for field in FIELDS}

    def pick(self):
        best, best_score = None, None
        for cell in self.order:
            if cell in self.used:
                continue
            score = sum(self.counts[f][v] * self.CARD[f] for f, v in zip(FIELDS, cell))
            if best is None or score < best_score:
                best, best_score = cell, score
        if best is None:
            raise LessonError("A_CELLS_EXHAUSTED")
        return best

    def admit(self, cells):
        for cell in cells:
            self.used.add(cell)
            for field, value in zip(FIELDS, cell):
                self.counts[field][value] += 1


def _unequal_leaves(rng, count):
    leaves = []
    while len(leaves) < count:
        leaf = random_leaf(rng)
        if leaf not in leaves:
            leaves.append(leaf)
    return leaves


def _tag(rows, changed_field, **constructor):
    for row in rows:
        row["changed_field"] = changed_field
        row["constructor"] = dict(constructor)
    return rows


def make_a_single(cells, compiler, state):
    cell = cells.pick()
    cells.used.add(cell)             # burned even if refused, so the greedy pick cannot loop on it
    rows = [check_intended(leaf_ast(*cell), compiler)]
    state["admit"] = lambda: cells.admit([cell])
    return _tag(rows, None, kind="A_single", cell=list(cell))


def make_a_pair(cells, compiler, state, rng):
    field = FIELDS[state["kept"] % len(FIELDS)]        # exact rotation over the four fields, by kept groups
    base = cells.pick()
    index = FIELDS.index(field)
    partners = [base[:index] + (value,) + base[index + 1:] for value in VALUES[field] if value != base[index]]
    partners = [cell for cell in partners if cell not in cells.used]
    cells.used.add(base)
    if not partners:
        raise Refusal("A_PAIR_PARTNER_EXHAUSTED")
    partner = rng.choice(partners)
    cells.used.add(partner)
    rows = [check_intended(leaf_ast(*base), compiler), check_intended(leaf_ast(*partner), compiler)]
    diff = differing_positions(rows[0]["target_tokens"], rows[1]["target_tokens"])
    if diff is None or len(diff) != 1 or rows[0]["slot_kinds"][diff[0]] != field:
        raise LessonError("A_PAIR_NOT_ONE_FIELD: %s / %s" % (rows[0]["observation"], rows[1]["observation"]))
    state["admit"] = lambda: cells.admit([base, partner])
    return _tag(rows, field, kind="A_one_field_pair", cells=[list(base), list(partner)])


def make_b_swap(rng, compiler, state):
    op = OPS[state["kept"] % 2]                           # PLUS/TIMES balanced by kept groups
    a, b = _unequal_leaves(rng, 2)
    rows = [check_intended(binary(op, a, b), compiler), check_intended(binary(op, b, a), compiler)]
    return _tag(rows, "left_right_order", kind="B_swap_pair", op=op)


def make_b_op(rng, compiler, state):
    a, b = _unequal_leaves(rng, 2)
    rows = [check_intended(binary("PLUS", a, b), compiler), check_intended(binary("TIMES", a, b), compiler)]
    return _tag(rows, "op", kind="B_op_pair")


def _op_pattern(rng, pattern, count):
    if pattern == "all_plus":
        return ["PLUS"] * count
    if pattern == "all_times":
        return ["TIMES"] * count
    while True:
        ops = [rng.choice(OPS) for _ in range(count)]
        if len(set(ops)) == 2:
            return ops


# (leaves, operator pattern), rotated by kept groups. A 3-leaf MIXED pattern is absent on purpose: with one PLUS and
# one TIMES, exactly one of ((a o b) o c) and (a o (b o c)) compiles, because TIMES needs single-state operands
# (a test checks this), so such a pair can never be kept.
GROUPING_PLAN = ((3, "all_plus"), (3, "all_times"), (4, "all_plus"), (4, "all_times"), (4, "mixed"))


def make_c_grouping(rng, compiler, state, member_refusals):
    """Same leaf sequence and operators; different brackets. 3 leaves: 2 bracketings; 4 leaves: 3 allowed ones."""
    n_leaves, pattern = GROUPING_PLAN[state["kept"] % len(GROUPING_PLAN)]
    leaves = _unequal_leaves(rng, n_leaves)
    ops = _op_pattern(rng, pattern, n_leaves - 1)
    rows = []
    for text in C_SHAPES[n_leaves]:
        try:
            row = check_intended(fill_shape(parse_shape(text), leaves, ops), compiler)
        except Refusal as refusal:
            member_refusals["C_grouping member %s: %s" % (text, refusal.code)] += 1
            continue
        rows.append(row)
    if len(rows) < 2:
        raise Refusal("C_GROUPING_FEWER_THAN_TWO_MEMBERS_COMPILE:%s" % pattern)
    return _tag(rows, "grouping", kind="C_grouping", leaves=n_leaves, op_pattern=pattern,
                bracketings=[r["shape_text"] for r in rows])


def make_c_operator(rng, compiler, state):
    """Same leaves, same brackets; exactly one operator differs."""
    shapes = C_SHAPES[3] + C_SHAPES[4]
    text = shapes[state["kept"] % len(shapes)]
    shape = parse_shape(text)
    n_leaves = text.count("L")
    leaves = _unequal_leaves(rng, n_leaves)
    ops = [rng.choice(OPS) for _ in range(n_leaves - 1)]
    position = rng.randrange(n_leaves - 1)
    flipped = list(ops)
    flipped[position] = "TIMES" if ops[position] == "PLUS" else "PLUS"
    rows = [check_intended(fill_shape(shape, leaves, ops), compiler),
            check_intended(fill_shape(shape, leaves, flipped), compiler)]
    return _tag(rows, "op", kind="C_operator_only", shape=text, op_position=position)


def make_c_leaf(rng, compiler, state):
    """Same brackets, same operators; exactly one leaf differs."""
    shapes = C_SHAPES[3] + C_SHAPES[4]
    text = shapes[state["kept"] % len(shapes)]
    shape = parse_shape(text)
    n_leaves = text.count("L")
    leaves = _unequal_leaves(rng, n_leaves + 1)
    ops = [rng.choice(OPS) for _ in range(n_leaves - 1)]
    position = rng.randrange(n_leaves)
    swapped = list(leaves[:n_leaves])
    swapped[position] = leaves[n_leaves]
    rows = [check_intended(fill_shape(shape, leaves[:n_leaves], ops), compiler),
            check_intended(fill_shape(shape, swapped, ops), compiler)]
    return _tag(rows, "leaf", kind="C_leaf_only", shape=text, leaf_position=position)


def make_c_mixed(rng, compiler, state):
    """All three factors varied at once, over all 16 allowed G-train shapes.

The shape rotates by KEPT groups, so each shape gets an equal share of kept rows. Leaves and operators are redrawn
until the compiler accepts the tree (deep trees with TIMES above PLUS are refused more often; this is logged).
"""
    key, text = sorted(G_TRAIN_SHAPES.items())[state["kept"] % len(G_TRAIN_SHAPES)]
    shape = parse_shape(text)
    n_leaves = text.count("L")
    leaves = [random_leaf(rng) for _ in range(n_leaves)]
    ops = [rng.choice(OPS) for _ in range(n_leaves - 1)]
    rows = [check_intended(fill_shape(shape, leaves, ops), compiler)]
    return _tag(rows, None, kind="C_mixed_allowed_shapes", shape=text)


# ------------------------------------------------------------------------------------------------------------
# Content registry (global uniqueness => no observation can straddle splits) and the group loop
# ------------------------------------------------------------------------------------------------------------
class Registry:
    def __init__(self, forbidden_observations=()):
        self.contents, self.observations = set(), set()
        self.forbidden = set(forbidden_observations)

    def refusal_for(self, rows):
        contents = [r["content_sha256"] for r in rows]
        if len(set(contents)) != len(contents):
            return "DUPLICATE_CONTENT_WITHIN_GROUP"
        if any(c in self.contents for c in contents):
            return "DUPLICATE_CONTENT"
        if any(r["observation"] in self.forbidden for r in rows):
            return "Q3_DEV_OBSERVATION"
        return None

    def add(self, rows):
        for row in rows:
            self.contents.add(row["content_sha256"])
            self.observations.add(row["observation"])


def _make_groups(maker, quota_rows, registry, refusals, *, phase_seed, lesson, subfamily, state):
    groups, rows, attempts = [], 0, 0
    limit = 400 * max(1, quota_rows) + 2000
    while rows < quota_rows:
        attempts += 1
        if attempts > limit:
            raise LessonError("GENERATION_STALLED: %s/%s after %d attempts" % (lesson, subfamily, attempts))
        state.pop("admit", None)
        try:
            members = maker()
        except Refusal as refusal:
            refusals[refusal.code] += 1
            continue
        reason = registry.refusal_for(members)
        if reason:
            refusals[reason] += 1
            continue
        registry.add(members)
        if "admit" in state:
            state["admit"]()
        group_id = sha256_hex(("%s:%d:%s:%s:group:%d" % (SCHEMA, phase_seed, lesson, subfamily, len(groups)))
                              .encode("utf-8"))[:16]
        for member in members:
            member.update(group_id=group_id, group_size=len(members), lesson_family=lesson, subfamily=subfamily)
        groups.append(members)
        rows += len(members)
        state["kept"] += 1
    return groups, attempts


def plan_quotas(size):
    """Declared pool sizes (rows) per subfamily and split. PROPOSED; see the spec."""
    if type(size) is not int or not SIZE_RANGE[0] <= size <= SIZE_RANGE[1]:
        raise LessonError("INVALID_SIZE: declare --size in %d..%d" % SIZE_RANGE)
    quotas = {}
    for lesson, sub in SUBFAMILIES:
        base = size * MIXTURE[(lesson, sub)]
        g = MIN_GROUP[sub]
        quotas[(lesson, sub)] = {"train": max(g, round(base)), "dev": max(g, round(base * DEV_FRACTION)),
                                 "feedback": max(g, round(base * FEEDBACK_FRACTION))}
    a_total = sum(quotas[key][s] for key in quotas if key[0] == "A" for s in SPLITS)
    capped = a_total > A_DISTINCT_CAP
    if capped:
        factor = A_DISTINCT_CAP / a_total
        for key in quotas:
            if key[0] == "A":
                quotas[key] = {s: max(MIN_GROUP[key[1]], int(quotas[key][s] * factor)) for s in SPLITS}
    return quotas, capped


def _visible_q3_observations(family, split):
    """Visible Q3 v0.7 rows only (manifest pinned, file hash checked). Never an eval or sealed file."""
    import q3_load
    q3_load.check_pins(Q3_DATA)
    return [row["observation"] for row in q3_load.load_visible(Q3_DATA, family, split)]


def q3_dev_observations():
    """Every string observation in a visible Q3 v0.7 dev file (families R and G)."""
    return sorted(set(_visible_q3_observations("G", "dev")) | set(_visible_q3_observations("R", "dev")))


def source_pins():
    names = ("q4_sdg_curriculum.py", "q3_behaviour_records.py", "q3_load.py", "learner_q4_decoder.py",
             "learner_q4_representation.py", "q4_panel_evaluation.py", "historical_compiler.py", "reference_ops.py",
             "pinned_sources/compiler_pre_ohm_61ed5a45.py")
    return {name: lf_sha256(HERE / name) for name in names}


def check_q3_immutable():
    for name, digest in Q3_IMMUTABLE_LF_SHA256.items():
        if lf_sha256(HERE / name) != digest:
            raise LessonError("Q3_FILE_CHANGED: %s" % name)
    if lf_sha256(Q3_DATA / "manifest.json") != Q3_V07_MANIFEST_SHA256:
        raise LessonError("Q3_MANIFEST_CHANGED")


# ------------------------------------------------------------------------------------------------------------
# Build
# ------------------------------------------------------------------------------------------------------------
def _json_line(row):
    return json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False)


def _jsonl_bytes(rows):
    return ("\n".join(_json_line(r) for r in rows) + "\n").encode("utf-8") if rows else b""


def _visible_and_sealed(row, rid, phase, phase_seed):
    visible = {"record_id": rid, "lesson_family": row["lesson_family"], "mode": MODE, "observation": row["observation"]}
    sealed = {"record_id": rid, "lesson_family": row["lesson_family"], "subfamily": row["subfamily"],
              "group_id": row["group_id"], "group_size": row["group_size"], "changed_field": row["changed_field"],
              "target_ast": row["target_ast"], "target_canonical_ast": q3.canonical(row["target_ast"]),
              "target_tokens": row["target_tokens"], "slot_kinds": row["slot_kinds"], "slot_paths": row["slot_paths"],
              "provenance": {"experiment": EXPERIMENT, "label": LABEL, "phase": phase, "phase_seed": phase_seed,
                             "constructor": row["constructor"], "compiler": row["compiler"]}}
    for key in ("content_sha256", "ordered_operator_shape_sha256", "ordered_bare_shape_sha256", "q3_tree_shape_key",
                "strict_shape_key", "depth", "ast_size", "leaf_count", "shape_text"):
        sealed[key] = row[key]
    if set(visible) != VISIBLE_KEYS or set(sealed) != SEALED_KEYS:
        raise LessonError("ROW_KEYS_WRONG")
    return visible, sealed


def _coverage(rows):
    """Logged coverage of one split: bare shapes, depths, and (family A) field value counts."""
    out = {"rows": len(rows), "bare_shapes": dict(sorted(collections.Counter(r["shape_text"] for r in rows).items())),
           "depths": {str(k): v for k, v in sorted(collections.Counter(r["depth"] for r in rows).items())},
           "changed_field": dict(sorted(collections.Counter(str(r["changed_field"]) for r in rows).items()))}
    singles = [r for r in rows if r["lesson_family"] == "A"]
    if singles:
        cells = [leaf_cell(r["target_ast"]) for r in singles]
        out["A_field_values"] = {field: {str(k): v for k, v in sorted(collections.Counter(c[i] for c in cells).items(),
                                                                       key=lambda kv: str(kv[0]))}
                                 for i, field in enumerate(FIELDS)}
        out["A_distinct_cells"] = len(set(cells))
        out["A_cells_of_1600"] = 1600
    ops = collections.Counter(op for r in rows for op in ops_of(r["target_ast"]))
    out["operators"] = dict(sorted(ops.items()))
    return out


def _publish(tmp, out):
    if out.exists():
        out.rmdir()      # only an empty directory can be here (checked before building)
    os.replace(tmp, out)


def _reserve_output(out):
    out = Path(out)
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise LessonError("OUTPUT_NOT_EMPTY: %s -- use a fresh data version directory" % out)
    tmp = out.with_name(out.name + ".partial")
    if tmp.exists():
        raise LessonError("PARTIAL_OUTPUT_EXISTS: %s -- inspect and remove it by hand" % tmp)
    tmp.mkdir(parents=True)
    return out, tmp


def build(out, size, *, seed=SEED, feedback_seed=FEEDBACK_SEED, expect_engine=None):
    """Build the static A/B/C lesson package into a NEW directory. Deterministic: two builds are byte-identical."""
    for value in (seed, feedback_seed):
        if type(value) is not int or value in Q3_SEEDS:
            raise LessonError("SEED_NOT_NEW: %r" % (value,))
    if seed == feedback_seed:
        raise LessonError("FEEDBACK_SEED_MUST_DIFFER")
    quotas, a_capped = plan_quotas(size)
    check_q3_immutable()
    compiler = Compiler()
    if expect_engine is not None and compiler.engine != expect_engine:
        raise LessonError("ENGINE_MISMATCH: expected %s, found %s" % (expect_engine, compiler.engine))
    q3_dev = q3_dev_observations()
    q3_g_train = set(_visible_q3_observations("G", "train"))
    out, tmp = _reserve_output(out)
    registry = Registry(q3_dev)
    used_cells = set()
    refusals = {}
    attempts = {}
    by_split = {split: [] for split in SPLITS}
    for phase, phase_seed in (("main", seed), ("feedback", feedback_seed)):
        cells = BalancedCells(_rng(phase_seed, "A", "cells"), used_cells)
        for lesson, sub in SUBFAMILIES:
            rng = _rng(phase_seed, lesson, sub, "make")
            counter = collections.Counter()
            state = {"kept": 0}
            makers = {
                "single": lambda: make_a_single(cells, compiler, state),
                "one_field_pair": lambda: make_a_pair(cells, compiler, state, rng),
                "swap_pair": lambda: make_b_swap(rng, compiler, state),
                "op_pair": lambda: make_b_op(rng, compiler, state),
                "grouping": lambda: make_c_grouping(rng, compiler, state, counter),
                "operator_only": lambda: make_c_operator(rng, compiler, state),
                "leaf_only": lambda: make_c_leaf(rng, compiler, state),
                "mixed_allowed_shapes": lambda: make_c_mixed(rng, compiler, state),
            }
            q = quotas[(lesson, sub)]
            want = q["train"] + q["dev"] if phase == "main" else q["feedback"]
            groups, tries = _make_groups(makers[sub], want, registry, counter, phase_seed=phase_seed,
                                         lesson=lesson, subfamily=sub, state=state)
            refusals["%s/%s/%s" % (phase, lesson, sub)] = dict(sorted(counter.items()))
            attempts["%s/%s/%s" % (phase, lesson, sub)] = {"attempts": tries, "groups_kept": len(groups),
                                                          "rows_kept": sum(len(g) for g in groups)}
            if phase == "feedback":
                for group in groups:
                    by_split["feedback"].extend((row, phase, phase_seed) for row in group)
                continue
            order = list(range(len(groups)))
            _rng(phase_seed, lesson, sub, "split").shuffle(order)    # groups exist (with ids) BEFORE this split
            dev_rows = 0
            for index in order:
                split = "dev" if dev_rows < q["dev"] else "train"
                dev_rows += len(groups[index]) if split == "dev" else 0
                by_split[split].extend((row, phase, phase_seed) for row in groups[index])
    files, counts, emitted = {}, {}, {split: [] for split in SPLITS}
    for split in SPLITS:
        split_seed = feedback_seed if split == "feedback" else seed
        for lesson in LESSONS:
            rows = [item for item in by_split[split] if item[0]["lesson_family"] == lesson]
            _rng(split_seed, lesson, split, "emit").shuffle(rows)
            visible, sealed = [], []
            for index, (row, phase, phase_seed) in enumerate(rows):
                v, s = _visible_and_sealed(row, record_id(SCHEMA, split_seed, lesson, split, index), phase, phase_seed)
                visible.append(v)
                sealed.append(s)
                emitted[split].append(row)
            for kind, body_rows in (("visible", visible), ("sealed", sealed)):
                name = "%s_%s_%s.jsonl" % (kind, lesson, split)
                body = _jsonl_bytes(body_rows)
                with (tmp / name).open("xb") as stream:
                    stream.write(body)
                files[name] = {"records": len(body_rows), "sha256": sha256_hex(body)}
            counts["%s_%s" % (lesson, split)] = len(visible)
    self_check(emitted, q3_dev)
    manifest = {
        "schema": SCHEMA, "experiment": EXPERIMENT, "label": LABEL, "status": "BUILT_NOT_PINNED",
        "seed": seed, "feedback_seed": feedback_seed,
        "record_id_seeds": {"train": seed, "dev": seed, "feedback": feedback_seed},
        "record_id_policy": "sha256 of the raw UTF-8 string '<schema>:<seed>:<lesson>:<split>:<index>', first 24 hex",
        "size_train_pool_declared": size, "mixture_proposed": {"%s/%s" % k: v for k, v in MIXTURE.items()},
        "dev_fraction": DEV_FRACTION, "feedback_fraction": FEEDBACK_FRACTION, "a_distinct_cap": A_DISTINCT_CAP,
        "a_pool_capped": a_capped, "quotas_rows": {"%s/%s" % k: v for k, v in quotas.items()},
        "counts": counts, "files": files, "compiler": compiler.receipt, "sources_lf_sha256": source_pins(),
        "q3_immutable_lf_sha256": Q3_IMMUTABLE_LF_SHA256, "q3_v0_7_manifest_sha256": Q3_V07_MANIFEST_SHA256,
        "allowed_bare_shapes": dict(sorted({SINGLE_STATE_KEY: "L", **G_TRAIN_SHAPES}.items())),
        "forbidden_bare_shapes": G_DEV_SHAPES, "max_depth": MAX_DEPTH,
        "visibility": {"visible": sorted(VISIBLE_KEYS), "sealed": sorted(SEALED_KEYS),
                       "note": "the learner may open visible_* only; the sealed_* sidecar is for loss and diagnosis"},
        "group_policy": "a group id is assigned when a group is made, before any split; a whole group goes to one "
                        "split; every content hash occurs at most once in the whole package, so no observation can "
                        "straddle splits. One-field NEIGHBOURS across groups are not blocked (disclosed).",
        "trigger_policy": "family D triggers may come only from train or feedback rows of this package",
        "stats": {"refusals": refusals, "attempts": attempts,
                  "coverage": {split: _coverage(emitted[split]) for split in SPLITS},
                  "observations_equal_to_a_visible_q3_G_train_row": {
                      split: sum(1 for r in emitted[split] if r["observation"] in q3_g_train) for split in SPLITS}},
    }
    (tmp / "manifest.json").write_bytes((json.dumps(manifest, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
                                        .encode("utf-8"))
    _publish(tmp, out)
    return manifest


def self_check(emitted, q3_dev):
    """Whole-package checks after generation: shapes, uniqueness, group integrity, pair relations."""
    dev_set = set(q3_dev)
    contents, groups = {}, collections.defaultdict(list)
    for split, rows in emitted.items():
        for row in rows:
            if not shape_allowed(row["q3_tree_shape_key"], row["depth"]):
                raise LessonError("SELF_CHECK_FORBIDDEN_SHAPE: %s" % row["observation"])
            if row["observation"] in dev_set:
                raise LessonError("SELF_CHECK_Q3_DEV_OBSERVATION")
            if row["content_sha256"] in contents:
                raise LessonError("SELF_CHECK_DUPLICATE_CONTENT")
            contents[row["content_sha256"]] = split
            groups[row["group_id"]].append((split, row))
    for group_id, members in groups.items():
        if len({split for split, _ in members}) != 1:
            raise LessonError("SELF_CHECK_GROUP_STRADDLES_SPLITS: %s" % group_id)
        check_group_relation([row for _, row in members])


def check_group_relation(rows):
    """The declared relation inside one group must hold on the COMPILED targets."""
    if len(rows) == 1:
        return
    field = rows[0]["changed_field"]
    trees = [r["target_ast"] for r in rows]
    if field in FIELDS:
        diff = differing_positions(rows[0]["target_tokens"], rows[1]["target_tokens"])
        if len(rows) != 2 or diff is None or len(diff) != 1 or rows[0]["slot_kinds"][diff[0]] != field:
            raise LessonError("PAIR_RELATION_BROKEN: one field %s" % field)
    elif field == "left_right_order":
        a, b = trees
        if len(rows) != 2 or a["op"] != b["op"] or a["left"] != b["right"] or a["right"] != b["left"] or a == b:
            raise LessonError("PAIR_RELATION_BROKEN: left/right swap")
    elif field == "op":
        a, b = trees
        diff = differing_positions(rows[0]["target_tokens"], rows[1]["target_tokens"])
        if (len(rows) != 2 or diff is None or len(diff) != 1 or rows[0]["slot_kinds"][diff[0]] != "op"
                or leaves_of(a) != leaves_of(b) or q3.tree_shape(a) != q3.tree_shape(b)):
            raise LessonError("PAIR_RELATION_BROKEN: operator only")
    elif field == "leaf":
        a, b = trees
        la, lb = leaves_of(a), leaves_of(b)
        if (len(rows) != 2 or ops_of(a) != ops_of(b) or q3.tree_shape(a) != q3.tree_shape(b) or len(la) != len(lb)
                or sum(x != y for x, y in zip(la, lb)) != 1):
            raise LessonError("PAIR_RELATION_BROKEN: leaf only")
    elif field == "grouping":
        shapes = [json.dumps(q3.tree_shape(t)) for t in trees]
        if (len(set(shapes)) != len(shapes) or any(leaves_of(t) != leaves_of(trees[0]) for t in trees)
                or any(ops_of(t) != ops_of(trees[0]) for t in trees)):
            raise LessonError("PAIR_RELATION_BROKEN: grouping")
    else:
        raise LessonError("PAIR_RELATION_UNKNOWN: %r" % (field,))


# ------------------------------------------------------------------------------------------------------------
# Loader for the new family (two doors, as in q3_load)
# ------------------------------------------------------------------------------------------------------------
def _strict(text, where):
    from q3_load import strict_loads
    return strict_loads(text, where)


def _read_lf(path):
    try:
        return Path(path).read_bytes().replace(b"\r\n", b"\n")
    except OSError as error:
        raise LessonError("DATA_FILE_MISSING: %s (%s)" % (Path(path).name, type(error).__name__)) from None


def manifest_of(data_dir):
    manifest = _strict(_read_lf(Path(data_dir) / "manifest.json").decode("utf-8"), "manifest.json")
    if type(manifest) is not dict or manifest.get("schema") not in (SCHEMA, D_SCHEMA):
        raise LessonError("MANIFEST_SCHEMA_UNKNOWN")
    if set(manifest.get("visibility", {}).get("visible", [])) != VISIBLE_KEYS:
        raise LessonError("VISIBILITY_POLICY_EDITED")
    return manifest


def manifest_sha(data_dir):
    return sha256_hex(_read_lf(Path(data_dir) / "manifest.json"))


def check_pin(data_dir):
    """The package manifest must be the one pinned OUTSIDE the data folder (Q4_SDG_DATA_PINS.json)."""
    manifest = manifest_of(data_dir)
    pins = _strict(_read_lf(PINS).decode("utf-8"), PINS.name)
    entry = pins.get("data_versions", {}).get(manifest["schema"]) if type(pins) is dict else None
    if type(entry) is not dict:
        raise LessonError("NO_PIN_FOR_THIS_DATA_VERSION: %s" % manifest["schema"])
    if entry.get("manifest_sha256") != manifest_sha(data_dir):
        raise LessonError("MANIFEST_NOT_THE_PINNED_ONE")
    return entry


def pin_dataset(data_dir):
    """Write this package's manifest hash into Q4_SDG_DATA_PINS.json once. Never touches Q3_DATA_PINS.json."""
    manifest, digest = manifest_of(data_dir), manifest_sha(data_dir)
    if manifest["schema"] != SCHEMA:
        raise LessonError("ONLY_THE_STATIC_PACKAGE_IS_PINNED_HERE")
    verify_package(data_dir, pinned=False)
    pins = _strict(_read_lf(PINS).decode("utf-8"), PINS.name)
    versions = pins["data_versions"]
    if manifest["schema"] in versions:
        if versions[manifest["schema"]]["manifest_sha256"] != digest:
            raise LessonError("PIN_CONFLICT: a different package is already pinned for this schema")
        return versions[manifest["schema"]]
    try:
        relative = Path(data_dir).resolve().relative_to(HERE).as_posix()
    except ValueError:
        raise LessonError("PIN_DATA_OUTSIDE_THE_LAB") from None
    versions[manifest["schema"]] = {"data_dir": relative, "manifest_sha256": digest}
    PINS.write_bytes((json.dumps(pins, indent=1, sort_keys=True) + "\n").encode("utf-8"))
    return versions[manifest["schema"]]


def _rows(data_dir, name, manifest, lesson, split):
    if name not in manifest["files"]:
        raise LessonError("FILE_NOT_IN_MANIFEST: %s" % name)
    body = _read_lf(Path(data_dir) / name)
    if sha256_hex(body) != manifest["files"][name]["sha256"]:
        raise LessonError("FILE_HASH_MISMATCH: %s" % name)
    seed = manifest["record_id_seeds"][split]
    rows = []
    for number, line in enumerate(body.decode("utf-8").split("\n"), 1):
        if not line.strip():
            continue
        row = _strict(line, "%s line %d" % (name, number))
        if type(row) is not dict or row.get("record_id") != record_id(manifest["schema"], seed, lesson, split, len(rows)):
            raise LessonError("RECORD_ID_NOT_POSITIONAL: %s line %d" % (name, number))
        rows.append(row)
    if len(rows) != manifest["files"][name]["records"]:
        raise LessonError("RECORD_COUNT_MISMATCH: %s" % name)
    return rows


def load_visible_lessons(data_dir, lesson, split, *, pinned=True):
    """The LEARNER's door: the visible file only; every row carries exactly the four visible keys."""
    manifest = manifest_of(data_dir)
    if pinned:
        check_pin(data_dir)
    rows = _rows(data_dir, "visible_%s_%s.jsonl" % (lesson, split), manifest, lesson, split)
    for row in rows:
        if set(row) != VISIBLE_KEYS or row["lesson_family"] != lesson or row["mode"] != MODE:
            raise LessonError("VISIBLE_ROW_KEYS_WRONG: %s" % row.get("record_id"))
        if not is_canonical_surface(row["observation"]):
            raise LessonError("OBSERVATION_NOT_CANONICAL: %s" % row["record_id"])
    return rows


def sequence_input(visible_row):
    """Visible lesson row -> the model input (bytes of the observation only; id, family and mode are dropped)."""
    from learner_q4_representation import encode_observation
    if type(visible_row) is not dict or set(visible_row) != VISIBLE_KEYS:
        raise LessonError("VISIBLE_ROW_KEYS_WRONG")
    return encode_observation(visible_row["observation"])


def load_lesson_pairs(data_dir, lesson, split, *, pinned=True, compiler=None):
    """The TRAINER/EVALUATOR door: [(visible, sealed)], each target re-derived; recompiled when a compiler is given."""
    manifest = manifest_of(data_dir)
    visible = load_visible_lessons(data_dir, lesson, split, pinned=pinned)
    sealed = _rows(data_dir, "sealed_%s_%s.jsonl" % (lesson, split), manifest, lesson, split)
    if [s["record_id"] for s in sealed] != [v["record_id"] for v in visible]:
        raise LessonError("VISIBLE_AND_SEALED_IDS_DIFFER")
    pairs = []
    for v, s in zip(visible, sealed):
        if set(s) != SEALED_KEYS:
            raise LessonError("SEALED_ROW_KEYS_WRONG: %s" % v["record_id"])
        target = s["target_ast"]
        tokens = ast_to_tokens(target)
        slots = token_slots(tokens)
        info = describe(target)
        if (list(tokens) != s["target_tokens"] or tokens_to_ast(tokens) != target
                or s["target_canonical_ast"] != q3.canonical(target) or render_ast(target) != v["observation"]
                or s["slot_kinds"] != [x["slot"] for x in slots] or s["slot_paths"] != [x["path"] for x in slots]
                or any(s[key] != value for key, value in info.items())):
            raise LessonError("SEALED_TARGET_DOES_NOT_RECOMPUTE: %s" % v["record_id"])
        if not shape_allowed(info["q3_tree_shape_key"], info["depth"]):
            raise LessonError("FORBIDDEN_SHAPE_IN_PACKAGE: %s" % v["record_id"])
        if compiler is not None:
            artifact = compiler.compile_expression(v["observation"]).to_dict()
            if not artifact["valid"] or q3.to_lab_spelling(artifact["ast"]) != target:
                raise LessonError("TARGET_DISAGREES_WITH_THE_PINNED_COMPILER: %s" % v["record_id"])
        pairs.append((v, s))
    return pairs


def verify_package(data_dir, *, pinned=True, recompile=False):
    """Every file of a static package, re-checked as a whole (including group relations and Q3-dev disjointness)."""
    manifest = manifest_of(data_dir)
    compiler = Compiler() if recompile else None
    declared = set(manifest["files"])
    on_disk = {p.name for p in Path(data_dir).glob("*.jsonl")}
    if on_disk != declared:
        raise LessonError("FILES_ON_DISK_DIFFER_FROM_MANIFEST: %s" % sorted(on_disk ^ declared))
    lessons = ("D",) if manifest["schema"] == D_SCHEMA else LESSONS
    splits = ("train",) if manifest["schema"] == D_SCHEMA else SPLITS
    emitted = {split: [] for split in splits}
    for split in splits:
        for lesson in lessons:
            for v, s in load_lesson_pairs(data_dir, lesson, split, pinned=pinned, compiler=compiler):
                emitted[split].append(dict(s, observation=v["observation"]))
    self_check(emitted, q3_dev_observations())
    return {split: len(rows) for split, rows in emitted.items()}


# ------------------------------------------------------------------------------------------------------------
# Family D: mistake-driven rounds
# ------------------------------------------------------------------------------------------------------------
def _field_value(field, token_name):
    """Output token -> the canonical-surface value, or None when the surface cannot write it (then: random)."""
    if token_name is None:
        return None
    if field == "noetic" and re.fullmatch(r"N[0-9]", token_name):
        return ("ok", int(token_name[1:]))
    if field == "domain" and token_name in ("D_P", "D_C", "D_E", "D_O"):
        return ("ok", token_name[2:])
    if field == "drive":
        return ("ok", None) if token_name == "F_NONE" else ("ok", int(token_name[1:]))
    if field == "register" and token_name != "REG_NULL":
        return ("ok", None) if token_name == "REG_ABSENT" else ("ok", token_name[4:])
    return None


def _with_field(leaf, field, value):
    n, domain, drive, register = leaf_cell(leaf)
    cell = {"noetic": n, "domain": domain, "drive": drive, "register": register}
    cell[field] = value
    return leaf_ast(cell["noetic"], cell["domain"], cell["drive"], cell["register"])


def _random_tree(rng, shape):
    n_leaves = shape_text(shape).count("L")
    return fill_shape(shape, [random_leaf(rng) for _ in range(n_leaves)], [rng.choice(OPS) for _ in range(n_leaves - 1)])


def d_rows_for_trigger(trigger, rng, compiler, registry, *, targets=6, controls=2):
    """Fresh rows of the trigger's mistake type, plus controls. Returns (groups, refusals)."""
    mistake, path = trigger["mistake"], trigger["path"]
    refusals = collections.Counter()
    groups = []
    shapes = allowed_shapes()
    if mistake in ("LOST_BRANCH", "INVENTED_BRANCH"):
        want = "B" if mistake == "LOST_BRANCH" else "L"
        other = "L" if want == "B" else "B"
        plan = [(want, "target")] * targets + [(other, "control")] * controls
    elif mistake in ("PLUS_FOR_TIMES", "TIMES_FOR_PLUS") or mistake in _FIELD_MISTAKE.values():
        plan = [("pair", "target")] * targets
    else:
        raise LessonError("UNTEACHABLE_TRIGGER: %s" % mistake)
    for kind, role in plan:
        need = kind if kind in ("B", "L") else ("B" if mistake in ("PLUS_FOR_TIMES", "TIMES_FOR_PLUS") else "L")
        candidates = [s for _, s in shapes if node_at(s, path) == need]
        if not candidates:
            refusals["NO_ALLOWED_SHAPE_WITH_%s_AT_PATH" % need] += 1
            continue
        for _ in range(400):
            try:
                if kind in ("B", "L"):
                    rows = [check_intended(_random_tree(rng, rng.choice(candidates)), compiler)]
                    relation = None
                elif mistake in ("PLUS_FOR_TIMES", "TIMES_FOR_PLUS"):
                    gold_op = "TIMES" if mistake == "PLUS_FOR_TIMES" else "PLUS"
                    tree = _random_tree(rng, rng.choice(candidates))
                    node = get_at(tree, path)
                    target = replace_at(tree, path, dict(node, op=gold_op))
                    control = replace_at(tree, path, dict(node, op="PLUS" if gold_op == "TIMES" else "TIMES"))
                    rows = [check_intended(target, compiler), check_intended(control, compiler)]
                    relation = "op"
                else:
                    field = next(f for f, m in _FIELD_MISTAKE.items() if m == mistake)
                    tree = _random_tree(rng, rng.choice(candidates))
                    leaf = get_at(tree, path)
                    gold, wrong = _field_value(field, trigger["target"]), _field_value(field, trigger["predicted"])
                    gold_value = gold[1] if gold else rng.choice(VALUES[field])
                    others = [v for v in VALUES[field] if v != gold_value]
                    wrong_value = wrong[1] if wrong and wrong[1] != gold_value else rng.choice(others)
                    rows = [check_intended(replace_at(tree, path, _with_field(leaf, field, gold_value)), compiler),
                            check_intended(replace_at(tree, path, _with_field(leaf, field, wrong_value)), compiler)]
                    relation = field
            except Refusal as refusal:
                refusals[refusal.code] += 1
                continue
            reason = registry.refusal_for(rows)
            if reason:
                refusals[reason] += 1
                continue
            registry.add(rows)
            groups.append(_tag(rows, relation, kind="D_" + mistake, role=role, trigger_path=path))
            break
        else:
            refusals["FRESH_CONTENT_EXHAUSTED"] += 1
    return groups, refusals


def trigger_from_prediction(source_split, source_record_id, predicted_tokens, target_tokens):
    if source_split not in TRIGGER_SPLITS:
        raise LessonError("TRIGGER_SOURCE_NOT_ALLOWED: %r (train or feedback only)" % (source_split,))
    decision = first_wrong_decision(predicted_tokens, target_tokens)
    if decision is None:
        raise LessonError("TRIGGER_HAS_NO_MISTAKE")
    return dict(decision, source_split=source_split, source_record_id=source_record_id)


def build_d_round(parent_dir, triggers_path, out, *, seed, targets=6, controls=2, pinned=True):
    """One mistake-driven round: read triggers, check each source, write fresh D rows to a NEW directory."""
    if type(seed) is not int or seed in Q3_SEEDS or seed in (SEED, FEEDBACK_SEED):
        raise LessonError("SEED_NOT_NEW: %r" % (seed,))
    parent = manifest_of(parent_dir)
    if parent["schema"] != SCHEMA:
        raise LessonError("PARENT_NOT_A_STATIC_PACKAGE")
    if pinned:
        check_pin(parent_dir)
    spec = _strict(_read_lf(triggers_path).decode("utf-8"), "triggers")
    if (type(spec) is not dict or spec.get("schema") != TRIGGERS_SCHEMA
            or spec.get("parent_manifest_sha256") != manifest_sha(parent_dir) or type(spec.get("triggers")) is not list):
        raise LessonError("TRIGGERS_FILE_INVALID")
    known = {}
    for split in TRIGGER_SPLITS:
        for lesson in LESSONS:
            for v, s in load_lesson_pairs(parent_dir, lesson, split, pinned=pinned):
                known[v["record_id"]] = (split, s)
    q3_dev_ids = set()
    import q3_load
    q3_load.check_pins(Q3_DATA)
    for family in ("G", "R"):
        q3_dev_ids |= {row["record_id"] for row in q3_load.load_visible(Q3_DATA, family, "dev")}
    compiler = Compiler()
    registry = Registry(q3_dev_observations())
    for split in SPLITS:                     # D rows are fresh against EVERY parent row, dev included
        for lesson in LESSONS:
            for v, s in load_lesson_pairs(parent_dir, lesson, split, pinned=pinned):
                registry.contents.add(s["content_sha256"])
    out, tmp = _reserve_output(out)
    rng = random.Random("%s|%d|D" % (D_SCHEMA, seed))
    groups, refusals, used = [], collections.Counter(), []
    for index, item in enumerate(spec["triggers"]):
        source_id = item.get("source_record_id")
        if source_id in q3_dev_ids:
            raise LessonError("TRIGGER_FROM_Q3_DEV_ROW_REFUSED: %s" % source_id)
        if source_id not in known or known[source_id][0] != item.get("source_split"):
            raise LessonError("TRIGGER_SOURCE_NOT_A_TRAIN_OR_FEEDBACK_ROW: %s" % source_id)
        trigger = trigger_from_prediction(item["source_split"], source_id, item.get("predicted_tokens", []),
                                          known[source_id][1]["target_tokens"])
        made, why = d_rows_for_trigger(trigger, rng, compiler, registry, targets=targets, controls=controls)
        refusals.update(why)
        used.append(trigger)
        for group in made:
            group_id = sha256_hex(("%s:%d:D:group:%d" % (D_SCHEMA, seed, len(groups))).encode("utf-8"))[:16]
            for row in group:
                row.update(group_id=group_id, group_size=len(group), lesson_family="D",
                           subfamily=row["constructor"]["kind"], trigger_index=index)
            groups.append(group)
    rows = [row for group in groups for row in group]
    rng.shuffle(rows)
    visible, sealed = [], []
    for index, row in enumerate(rows):
        v, s = _visible_and_sealed(row, record_id(D_SCHEMA, seed, "D", "train", index), "D", seed)
        s["provenance"]["trigger"] = used[row["trigger_index"]]
        visible.append(v)
        sealed.append(s)
    files = {}
    for kind, body_rows in (("visible", visible), ("sealed", sealed)):
        name = "%s_D_train.jsonl" % kind
        body = _jsonl_bytes(body_rows)
        with (tmp / name).open("xb") as stream:
            stream.write(body)
        files[name] = {"records": len(body_rows), "sha256": sha256_hex(body)}
    self_check({"train": rows}, q3_dev_observations())
    manifest = {"schema": D_SCHEMA, "experiment": EXPERIMENT, "label": LABEL, "seed": seed,
                "record_id_seeds": {"train": seed}, "parent_schema": SCHEMA,
                "parent_manifest_sha256": manifest_sha(parent_dir), "triggers_sha256": sha256_hex(_read_lf(triggers_path)),
                "triggers_used": len(used), "targets_per_trigger": targets, "controls_per_trigger": controls,
                "counts": {"D_train": len(visible)}, "files": files, "compiler": compiler.receipt,
                "sources_lf_sha256": source_pins(),
                "visibility": {"visible": sorted(VISIBLE_KEYS), "sealed": sorted(SEALED_KEYS)},
                "stats": {"refusals": dict(sorted(refusals.items())), "coverage": _coverage(rows),
                          "mistakes": dict(sorted(collections.Counter(t["mistake"] for t in used).items()))}}
    (tmp / "manifest.json").write_bytes((json.dumps(manifest, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
                                        .encode("utf-8"))
    _publish(tmp, out)
    return manifest


# ------------------------------------------------------------------------------------------------------------
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build", action="store_true", help="build the static A/B/C package (run on AWS)")
    mode.add_argument("--verify", action="store_true", help="re-check a built package")
    mode.add_argument("--pin", action="store_true", help="pin a verified package in Q4_SDG_DATA_PINS.json")
    mode.add_argument("--build-d", action="store_true", help="one mistake-driven round from a triggers file")
    parser.add_argument("--out")
    parser.add_argument("--data")
    parser.add_argument("--size", type=int)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--feedback-seed", type=int, default=FEEDBACK_SEED)
    parser.add_argument("--expect-engine", choices=("python", "rust+python"))
    parser.add_argument("--triggers")
    parser.add_argument("--unpinned", action="store_true", help="verify/build-d before pinning (reported)")
    parser.add_argument("--recompile", action="store_true")
    args = parser.parse_args(argv)
    if args.build:
        if not args.out or args.size is None:
            parser.error("--build needs --out and a declared --size")
        manifest = build(args.out, args.size, seed=SEED if args.seed is None else args.seed,
                         feedback_seed=args.feedback_seed,
                         expect_engine=args.expect_engine)
        print(json.dumps({"counts": manifest["counts"], "compiler_engine": manifest["compiler"]["engine"]}, sort_keys=True))
        print("Q4_SDG_BUILD_PASS")
    elif args.verify:
        print(json.dumps(verify_package(args.data, pinned=not args.unpinned, recompile=args.recompile), sort_keys=True))
        print("Q4_SDG_VERIFY_PASS")
    elif args.pin:
        print(json.dumps(pin_dataset(args.data), sort_keys=True))
    else:
        if not (args.data and args.triggers and args.out and args.seed is not None):
            parser.error("--build-d needs --data (parent), --triggers, --out and --seed")
        manifest = build_d_round(args.data, args.triggers, args.out, seed=args.seed, pinned=not args.unpinned)
        print(json.dumps(manifest["counts"], sort_keys=True))
        print("Q4_SDG_D_ROUND_PASS")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (LessonError, OSError) as error:
        print("Q4_SDG_REFUSED: %s" % error, file=sys.stderr)
        sys.exit(1)
