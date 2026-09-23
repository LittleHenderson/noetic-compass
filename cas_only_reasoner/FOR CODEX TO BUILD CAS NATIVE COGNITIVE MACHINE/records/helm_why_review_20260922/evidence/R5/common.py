"""R5 shared helpers. Pure Python. Reads visible files and records only. No torch."""
import json
import re
import sys
from pathlib import Path

ROOT = Path("C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
LAB = ROOT / "research/helm_cas_expression_lab"
DATA = LAB / "data/q3_v0_7"
REC = ROOT / "records/q4_authorized_20260922"
RUN = REC / "run_001"

sys.path.insert(0, str(LAB))
from learner_q4_decoder import TOKENS, TOKEN_IDS, ast_to_tokens, allowed_next  # pure python, no torch


def read_jsonl(path):
    text = Path(path).read_bytes().replace(b"\r\n", b"\n").decode("utf-8")
    return [json.loads(line) for line in text.split("\n") if line.strip()]


_TOK = re.compile(r"\s*(\(|\)|\+|\u00d7|\^(\d)\^([PCEO])(?:_\{F([1-7])\})?(?:\|([TAfE]))?)")


def parse(text):
    """R5's own 20-line parser for the G surface form. NOT the CAS compiler."""
    toks, pos = [], 0
    while pos < len(text):
        m = _TOK.match(text, pos)
        if not m:
            if text[pos:].strip() == "":
                break
            raise ValueError("unparseable at %d: %r" % (pos, text[pos:pos + 20]))
        toks.append(m)
        pos = m.end()
    i = 0

    def expr():
        nonlocal i
        m = toks[i]
        if m.group(1) == "(":
            i += 1
            left = expr()
            opm = toks[i]; i += 1
            op = {"+": "PLUS", "\u00d7": "TIMES"}[opm.group(1)]
            right = expr()
            assert toks[i].group(1) == ")"
            i += 1
            return {"node": "BinaryExpr", "op": op, "left": left, "right": right}
        if m.group(2) is None:
            raise ValueError("expected literal")
        i += 1
        node = {"node": "StateLiteral", "operator": "^" + m.group(2), "domain": m.group(3),
                "drive": ("F" + m.group(4)) if m.group(4) else None}
        if m.group(5):
            node["register"] = m.group(5)
        return node

    ast = expr()
    if i != len(toks):
        raise ValueError("trailing tokens")
    return ast


def shape(ast):
    if ast["node"] == "BinaryExpr":
        return ["B", shape(ast["left"]), shape(ast["right"])]
    return "L"


def depth(ast):
    if ast["node"] == "BinaryExpr":
        return 1 + max(depth(ast["left"]), depth(ast["right"]))
    return 0


def leaves(ast):
    if ast["node"] == "BinaryExpr":
        return leaves(ast["left"]) + leaves(ast["right"])
    return [ast]


def subtrees(ast):
    out = [ast]
    if ast["node"] == "BinaryExpr":
        out += subtrees(ast["left"]) + subtrees(ast["right"])
    return out


def canon(ast):
    return json.dumps(ast, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def show(ast):
    if ast["node"] == "BinaryExpr":
        return "(%s %s %s)" % (show(ast["left"]), "+" if ast["op"] == "PLUS" else "\u00d7", show(ast["right"]))
    s = ast["operator"] + "^" + ast["domain"]
    if ast["drive"]:
        s += "_{%s}" % ast["drive"]
    if "register" in ast:
        s += "|" + str(ast["register"])
    return s


def slot_sequence(tokens):
    """For each target token position, the grammar slot it fills: expr/op/noetic/domain/drive/register/eos,
    plus the expr node depth. Derived from the token sequence alone (same stack discipline as allowed_next)."""
    pending = [("expr", 0)]
    out = []
    for t in tokens:
        name = TOKENS[t]
        if not pending:
            out.append(("eos", None))
            continue
        slot, d = pending.pop()
        out.append((slot, d))
        if slot == "expr":
            if name == "STATE":
                pending.extend((k, d) for k in ("register", "drive", "domain", "noetic"))
            else:
                pending.extend((("expr", d + 1), ("expr", d + 1), ("op", d)))
    return out
