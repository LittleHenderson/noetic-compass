"""CAS side for LM-T1b: the newest CAS compiler (cas-online dist, sha256 464fd4ad..., read-only) parses CAS text;
this module maps its AST to CCE v0.1b content (supported constructs only; anything else is a named FORM_GAP), and
renders content back to CAS text in the compiler's own syntax (Φ⟨⟩ / ∘, typed sets, ∈ ⊆ ..., CoverOf, Θ recipes).
"""
from decimal import Decimal
import re
import sys

COMPILER_ROOT = r"C:\Users\wakil\Documents\Codex\2026-10-08\task-4\cas-online\dist\compiler"
COMPILER_SHA256 = "464fd4adfae90a35ba54aa794829da1fe713b9b9cccd68b630ecccfdfbca2f56"
_C = None


def compiler():
    global _C
    if _C is None:
        if COMPILER_ROOT not in sys.path:
            sys.path.insert(0, COMPILER_ROOT)
        import api.notation.compiler as c
        _C = c
    return _C


class FormGap(Exception):
    def __init__(self, construct):
        super().__init__(construct)
        self.construct = construct


CONSTRUCTOR = {"noetic": "NoeticSet", "state": "StateCluster", "state_variant": "StateVariantCluster",
               "domain": "DomainSet", "register": "RegisterSet", "drive": "DriveSet", "relation": "RelationCluster"}
SUBSET_OPS = {"SUBSET": "⊂", "SUBSET_EQ": "⊆", "SUPERSET": "⊃", "SUPERSET_EQ": "⊇"}
SET_BIN = {"UNION": "union", "INTERSECTION": "intersection", "SET_DIFF": "difference"}
SET_CALL = {"Union": "union", "Intersection": "intersection", "Difference": "difference", "Pullback": "pullback",
            "Product": "product"}
EXPR_BIN = {"PLUS": "plus", "MINUS": "minus", "TIMES": "times", "DIVIDE": "divide", "ARROW": "arrow",
            "LARROW": "back_arrow", "BIARROW": "both_arrow"}
EXPR_SYM = {"plus": "+", "minus": "-", "times": "×", "divide": "÷", "arrow": "→", "back_arrow": "←", "both_arrow": "↔"}


def _num(x):
    import cce
    if isinstance(x, float):
        return cce.num(repr(x))
    return cce.num(x)


# --- AST -> content ----------------------------------------------------------------------------------------------
def _state(node):
    c = compiler()
    if not isinstance(node, c.StateLiteral):
        raise FormGap(type(node).__name__)
    if getattr(node, "drive_register", None) is not None:
        raise FormGap("drive-level register")
    reg = node.register
    reg = None if reg is None else ([reg] if isinstance(reg, str) else list(reg))
    return {"noetic": node.operator, "domain": node.domain, "register": reg,
            "drive": None if node.drive is None else "F%d" % node.drive}


def _state_str(node, kind):
    s = _state(node)
    out = "^%d" % s["noetic"]
    if kind == "noetic":
        return out
    out += "^" + s["domain"]
    if kind == "state":
        return out
    if s["drive"]:
        out += "_{%s}" % s["drive"]
    if s["register"]:
        if len(s["register"]) != 1:
            raise FormGap("register set inside a set element")
        out += "|" + s["register"][0]
    return out


def _element(node, kind):
    c = compiler()
    if kind in ("noetic", "state", "state_variant"):
        return _state_str(node, kind)
    if kind in ("domain", "register"):
        if isinstance(node, c.MetaSymbol):
            return node.name
        raise FormGap("set element " + type(node).__name__)
    if kind == "drive":
        if isinstance(node, c.DriveLiteral):
            return "F%d" % node.drive
        raise FormGap("drive element " + type(node).__name__)
    if kind == "relation":
        if isinstance(node, c.BinaryExpr) and node.op == "ARROW":
            return _state_str(node.left, "state") + " -> " + _state_str(node.right, "state")
        raise FormGap("relation element")
    raise FormGap("set kind " + kind)


def _set(node):
    c = compiler()
    if isinstance(node, c.MetaSetLiteral):
        if node.name not in ("Noetics", "Domains", "Registers", "Drives", "States", "Foundations", "SubFoundations"):
            raise FormGap("built-in set " + node.name)
        return {"builtin": node.name}
    if isinstance(node, c.TypedMetaSetLiteral):
        kind = node.element_type
        if kind not in CONSTRUCTOR:
            raise FormGap("typed set kind " + kind)
        return {"kind": kind, "elements": sorted({_element(e, kind) for e in node.elements})}
    if isinstance(node, c.Identifier):
        return {"name": node.name}
    if isinstance(node, c.BinaryExpr) and node.op in SET_BIN:
        return {"op": SET_BIN[node.op], "left": _set(node.left), "right": _set(node.right)}
    if isinstance(node, c.CallExpr) and node.callee in SET_CALL and len(node.args) == 2:
        return {"op": SET_CALL[node.callee], "left": _set(node.args[0]), "right": _set(node.args[1])}
    raise FormGap("set expression " + type(node).__name__)


def _fractal_chain(node):
    c = compiler()
    if isinstance(node, c.BinaryExpr) and node.op == "CIRC":
        return _fractal_chain(node.left) + _fractal_chain(node.right)
    return [_state(node)]


def _expr(node):
    c = compiler()
    if isinstance(node, c.StateLiteral):
        return {"state": _state(node)}
    if isinstance(node, c.BinaryExpr) and node.op in EXPR_BIN:
        return {"op": EXPR_BIN[node.op], "left": _expr(node.left), "right": _expr(node.right)}
    raise FormGap("expression " + (node.op if isinstance(node, c.BinaryExpr) else type(node).__name__))


def _statement(node, content):
    c = compiler()
    if isinstance(node, c.LetStatement):
        content["meta"].append(["let", node.name, _set(node.expr)])
        return
    if isinstance(node, c.MetaAssertion):
        if node.op in ("MEMBER", "NOT_MEMBER"):
            left = node.left
            if isinstance(left, c.StateLiteral):
                right = _set(node.right)
                kind = right.get("kind") or {"States": "state"}.get(right.get("builtin"), "noetic")
                el = _state_str(left, kind if kind in ("noetic", "state", "state_variant") else "noetic")
            elif isinstance(left, c.MetaSymbol):
                el = left.name
            elif isinstance(left, c.DriveLiteral):
                el = "F%d" % left.drive
            else:
                raise FormGap("member element " + type(left).__name__)
            content["meta"].append(["member", el, _set(node.right), node.op == "NOT_MEMBER"])
            return
        if node.op in SUBSET_OPS:
            content["meta"].append(["subset", _set(node.left), SUBSET_OPS[node.op], _set(node.right)])
            return
        if node.op == "EQUALS" and isinstance(node.left, c.CardinalityExpr) and isinstance(node.right, c.NumberLiteral):
            content["meta"].append(["size", _set(node.left.collection), _num(node.right.value)])
            return
        raise FormGap("assertion " + node.op)
    if isinstance(node, c.CallExpr) and node.callee in ("CoverOf", "PartitionOf"):
        content["meta"].append(["cover" if node.callee == "CoverOf" else "partition", _set(node.args[0]),
                                [_set(a) for a in node.args[1:]]])
        return
    if isinstance(node, c.FractalLiteral):
        content["fractal"] = [{"noetic": k, "domain": None, "register": None, "drive": None} for k in node.sequence]
        return
    if isinstance(node, c.BinaryExpr) and node.op == "CIRC":
        content["fractal"] = _fractal_chain(node)
        return
    if isinstance(node, c.RecipeLiteral):
        content["recipe"] = _recipe(node)
        return
    content["expr"] = _expr(node)


def _recipe(node):
    c = compiler()
    terms = []
    for p in node.prerequisites:
        prim = p.primitive
        if isinstance(prim, c.StateLiteral):
            st = _state(prim)
            if st["register"] is not None and len(st["register"]) > 1:
                raise FormGap("register set in a recipe term")
            st.update({"kind": "state", "coefficient": _num(p.coefficient)})
            terms.append(st)
        elif isinstance(prim, c.ProductionTargetLiteral):
            terms.append({"kind": "outcome", "coefficient": _num(p.coefficient), "name": "Ω_" + prim.name})
        else:
            raise FormGap("recipe prerequisite " + type(prim).__name__)
    return {"omega": "Ω_" + node.target.name, "terms": terms,
            "leakage": [{"coefficient": _num(k.coefficient), "side": "Ω_" + k.target.name, "implicit": False}
                        for k in node.leakages],
            "catalysts": ["Ω_" + k.name for k in node.catalysts],
            "inhibitors": ["Ω_" + k.name for k in node.inhibitors]}


def content_from_cas(source):
    """CAS text -> CCE v0.1b content via the compiler's parser. Raises FormGap or the compiler's error."""
    import cce_v01b
    c = compiler()
    ast = c.Parser(c.lex(source)).parse()
    content = cce_v01b.empty_content()
    stmts = ast.statements if isinstance(ast, c.Program) else [ast]
    for st in stmts:
        _statement(st, content)
    if sum(bool(x) for x in (content["fractal"], content["recipe"], content["expr"])) > 1:
        raise FormGap("several non-meta statements in one program")
    return content


# --- content -> CAS ----------------------------------------------------------------------------------------------
def state_cas(s, require_domain=False):
    out = "^%d" % s["noetic"]
    if s.get("domain"):
        out += "^" + s["domain"]
    if s.get("drive"):
        out += "_{%s}" % s["drive"]
    reg = s.get("register")
    if reg:
        out += "|" + reg[0] if len(reg) == 1 else "|⟨" + ",".join(reg) + "⟩"
    return out


def set_cas(s):
    if "builtin" in s:
        return s["builtin"]
    if "name" in s:
        return s["name"]
    if "op" in s:
        if s["op"] in ("pullback", "product"):
            return "%s(%s, %s)" % (s["op"].capitalize(), set_cas(s["left"]), set_cas(s["right"]))
        sym = {"union": "∪", "intersection": "∩", "difference": "∖"}[s["op"]]
        return "(%s %s %s)" % (set_cas(s["left"]), sym, set_cas(s["right"]))
    return "%s{%s}" % (CONSTRUCTOR[s["kind"]], ", ".join(s["elements"]))


def element_cas(e):
    return e


def meta_cas(st):
    k = st[0]
    if k == "member":
        return "%s %s %s" % (element_cas(st[1]), "∉" if st[3] else "∈", set_cas(st[2]))
    if k == "subset":
        return "%s %s %s" % (set_cas(st[1]), st[2], set_cas(st[3]))
    if k == "size":
        return "|%s| = %s" % (set_cas(st[1]), st[2])
    if k == "let":
        return "let %s = %s" % (st[1], set_cas(st[2]))
    return "%s(%s)" % ("CoverOf" if k == "cover" else "PartitionOf", ", ".join([set_cas(st[1])] + [set_cas(m) for m in st[2]]))


def fractal_cas(terms):
    if all(t.get("domain") is None and not t.get("register") and not t.get("drive") for t in terms):
        return "Φ⟨%s⟩" % ":".join(str(t["noetic"]) for t in terms)
    return " ∘ ".join(state_cas(t) for t in terms)


def expr_cas(e):
    if "state" in e:
        return state_cas(e["state"])
    return "(%s) %s (%s)" % (expr_cas(e["left"]), EXPR_SYM[e["op"]], expr_cas(e["right"]))


def recipe_cas(r):
    terms = []
    for t in r["terms"]:
        if t["kind"] == "state":
            terms.append("%s*%s" % (t["coefficient"], state_cas(t)))
        elif t["kind"] == "outcome":
            terms.append("%s*%s" % (t["coefficient"], t["name"]))
        else:
            raise FormGap("emergent term (the compiler cannot read it inside a recipe)")
    cond = ""
    marks = ["κ_" + x[2:] for x in r["catalysts"]] + ["ι_" + x[2:] for x in r["inhibitors"]]
    if marks:
        cond = " | " + ", ".join(marks)
    text = "Θ(%s)%s = %s → %s" % (r["omega"], cond, " + ".join(terms), r["omega"])
    for k in r["leakage"]:
        text += " + %s*Λ·%s" % (k["coefficient"], k["side"])
    return text


def cas_parts(content):
    """CAS text for each compiler-readable part of a content: {'fractal'|'meta'|'expr'|'recipe': text}."""
    import cce_v01b
    c = cce_v01b.canonical(content)
    out = {}
    if c["fractal"]:
        out["fractal"] = fractal_cas(c["fractal"])
    if c["meta"]:
        out["meta"] = "; ".join(meta_cas(s) for s in c["meta"])
    if c["expr"] is not None:
        out["expr"] = expr_cas(c["expr"])
    if c["recipe"] is not None:
        out["recipe"] = recipe_cas(c["recipe"])
    return out


def compile_view(source):
    """Compiler result as a comparable dict; set/assertion display labels removed (constructor spelling is surface)."""
    art = compiler().compile_expression(source)
    if not art.valid:
        err = str(art.error)
        return {"valid": False, "stage": err.split(":")[0].split("@")[0]}
    d = art.result.to_dict() if hasattr(art.result, "to_dict") else {"repr": repr(art.result)}

    def strip(x):
        if isinstance(x, dict):
            return {k: strip(v) for k, v in x.items() if k not in ("name", "message", "set")}
        if isinstance(x, list):
            return [strip(v) for v in x]
        return x
    d = strip(d)
    if isinstance(d, dict) and d.get("kind") == "recipe":
        import json as _j
        for key in ("prerequisites", "leakages", "catalysts", "inhibitors"):
            if isinstance(d.get(key), list):
                d[key] = sorted(d[key], key=lambda x: _j.dumps(x, sort_keys=True, ensure_ascii=False, default=str))
    return {"valid": True, "result": d}
