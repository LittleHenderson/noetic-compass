"""CCE v0.1b = CCE v0.1 (cce.py, unchanged, imported) + nested Noetics (fractal sequences, depth 1-5),
set meta-logic over CAS objects, and CAS expressions. GRAMMAR_CCE_v0_1b_ADDENDUM.md sections A-D.

Same contract as cce.py: parse(text) -> content or Refusal; render(content, rng=None) -> text; normalize;
round_trip; say. New content fields: "fractal" (list of term objects), "meta" (list of statements), "expr".
"""
import hashlib
import json
import random
import re

import cce
from cce import Refusal, NOETIC_NAMES, DOMAINS, REGISTERS, DRIVES, NUM_RX

MAX_FRACTAL_DEPTH = 5
_INV_NAME = {v: k for k, v in NOETIC_NAMES.items()}
_INV_DOM = {v: k for k, v in DOMAINS.items()}
_INV_REG = {v: k for k, v in REGISTERS.items()}
_INV_DRV = {v: k for k, v in DRIVES.items()}
BUILTINS = ("Noetics", "Domains", "Registers", "Drives", "States", "Foundations", "SubFoundations")
KIND_WORDS = {"Noetic": "noetic", "State": "state", "State variant": "state_variant", "Domain": "domain",
              "Register": "register", "Drive": "drive", "relation": "relation"}
WORD_OF_KIND = {v: k for k, v in KIND_WORDS.items()}
SET_OPS = {"union": "union", "intersection": "intersection", "difference": "difference", "pullback": "pullback",
           "product": "product"}
SUBSET_WORDS = [(" is strictly within ", "⊂"), (" is within ", "⊆"), (" strictly contains ", "⊃"),
                (" contains ", "⊇")]
EXPR_OPS = [(") plus (", "plus"), (") less (", "minus"), (") integrated with (", "times"),
            (") divided by (", "divide"), (") leads to (", "arrow"), (") comes from (", "back_arrow"),
            (") is linked both ways with (", "both_arrow")]
WORD_OF_EXPR_OP = {v: k[2:-2] for k, v in EXPR_OPS}


# --- normalization ---------------------------------------------------------------------------------------------
def _fterm(t):
    if isinstance(t, int):
        return {"noetic": t, "domain": None, "register": None, "drive": None}
    return cce.norm_state(t)


def _nset(s):
    if "builtin" in s:
        return {"builtin": s["builtin"]}
    if "name" in s:
        return {"name": s["name"]}
    if "op" in s:
        return {"op": s["op"], "left": _nset(s["left"]), "right": _nset(s["right"])}
    return {"kind": s["kind"], "elements": sorted(set(s["elements"]))}


def _nstmt(st):
    k = st[0]
    if k == "member":
        return ["member", st[1], _nset(st[2]), bool(st[3])]
    if k == "subset":
        return ["subset", _nset(st[1]), st[2], _nset(st[3])]
    if k == "size":
        return ["size", _nset(st[1]), cce.num(str(st[2]))]
    if k == "let":
        return ["let", st[1], _nset(st[2])]
    if k in ("cover", "partition"):
        return [k, _nset(st[1]), [_nset(m) for m in st[2]]]
    raise ValueError("unknown meta statement %r" % k)


def _nexpr(e):
    if e is None:
        return None
    if "state" in e:
        return {"state": cce.norm_state(e["state"])}
    return {"op": e["op"], "left": _nexpr(e["left"]), "right": _nexpr(e["right"])}


def canonical(c):
    base = dict(c)
    fr = base.pop("fractal", []) or []
    meta = base.pop("meta", []) or []
    expr = base.pop("expr", None)
    out = cce.canonical(base)
    out["fractal"] = [_fterm(t) for t in fr]
    out["meta"] = [_nstmt(s) for s in meta]
    out["expr"] = _nexpr(expr)
    return out


def normalize(c):
    return json.dumps(canonical(c), sort_keys=True, ensure_ascii=False)


def digest(c):
    return hashlib.sha256(normalize(c).encode("utf-8")).hexdigest()


def empty_content():
    c = cce.empty_content()
    c.update({"fractal": [], "meta": [], "expr": None})
    return c


# --- helpers -----------------------------------------------------------------------------------------------------
def _match_paren(text, start):
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    raise Refusal("NOT_CCE", "unbalanced parentheses")


def parse_element(text):
    m = re.fullmatch(r"(.+?) to (.+)", text)
    if m and " to " in text:
        a, b = parse_element(m.group(1)), parse_element(m.group(2))
        if not (re.fullmatch(r"\^\d\^[PCEO]", a) and re.fullmatch(r"\^\d\^[PCEO]", b)):
            raise Refusal("NOT_CCE", "relation element: " + text)
        return a + " -> " + b
    if text in _INV_DOM:
        return _INV_DOM[text]
    if text in _INV_REG:
        return _INV_REG[text]
    if text in _INV_DRV:
        return _INV_DRV[text]
    for name in sorted(_INV_NAME, key=len, reverse=True):
        if text == name:
            return "^%d" % _INV_NAME[name]
        if text.startswith(name + " "):
            rest = text[len(name) + 1:]
            m = re.fullmatch(r"(principled|cognitive|evaluative|operational)(?: for ([A-Z][a-z]+))?(?: in ([a-z]+))?", rest)
            if not m:
                raise Refusal("NOT_CCE", "element: " + text)
            out = "^%d^%s" % (_INV_NAME[name], _INV_DOM[m.group(1)])
            if m.group(2):
                if m.group(2) not in _INV_DRV:
                    raise Refusal("NOT_CCE", "drive word")
                out += "_{%s}" % _INV_DRV[m.group(2)]
            if m.group(3):
                if m.group(3) not in _INV_REG:
                    raise Refusal("NOT_CCE", "register word")
                out += "|" + _INV_REG[m.group(3)]
            return out
    raise Refusal("NOT_CCE", "unknown element word: " + text)


def render_element(e):
    m = re.fullmatch(r"(.+) -> (.+)", e)
    if m:
        return render_element(m.group(1)) + " to " + render_element(m.group(2))
    if e in DOMAINS:
        return DOMAINS[e]
    if e in REGISTERS:
        return REGISTERS[e]
    if e in DRIVES:
        return DRIVES[e]
    m = re.fullmatch(r"\^(\d)(?:\^([PCEO]))?(?:_\{(F\d)\})?(?:\|([TAfE]))?", e)
    if not m:
        raise ValueError("unsayable element %r" % e)
    out = NOETIC_NAMES[int(m.group(1))]
    if m.group(2):
        out += " " + DOMAINS[m.group(2)]
    if m.group(3):
        out += " for " + DRIVES[m.group(3)]
    if m.group(4):
        out += " in " + REGISTERS[m.group(4)]
    return out


def parse_set(text):
    m = re.fullmatch(r"all ([A-Za-z]+)", text)
    if m:
        if m.group(1) not in BUILTINS:
            raise Refusal("NOT_CCE", "unknown built-in set: " + m.group(1))
        return {"builtin": m.group(1)}
    m = re.fullmatch(r"the set named ([A-Z][A-Za-z0-9_]*)", text)
    if m:
        return {"name": m.group(1)}
    m = re.fullmatch(r"the (union|intersection|difference|pullback|product) of \(", text[:text.find("(") + 1]) if "(" in text else None
    if m:
        start = text.find("(")
        end = _match_paren(text, start)
        rest = text[end + 1:]
        if not rest.startswith(" and (") or not rest.endswith(")"):
            raise Refusal("NOT_CCE", "set operation form")
        right_start = end + 1 + len(" and ")
        if _match_paren(text, right_start) != len(text) - 1:
            raise Refusal("NOT_CCE", "set operation form")
        return {"op": m.group(1), "left": parse_set(text[start + 1:end]),
                "right": parse_set(text[right_start + 1:-1])}
    m = re.fullmatch(r"the (Noetic|State variant|State|Domain|Register|Drive|relation) set \{(.*)\}", text)
    if m:
        kind = KIND_WORDS[m.group(1)]
        raw = [x.strip() for x in cce._split_top(m.group(2), ", ")] if m.group(2).strip() else []
        elements = [parse_element(x) for x in raw]
        if not elements:
            raise Refusal("NOT_CCE", "empty typed set")
        _check_kind(kind, elements)
        return {"kind": kind, "elements": sorted(set(elements))}
    raise Refusal("NOT_CCE", "not a set phrase: " + text[:60])


def _check_kind(kind, elements):
    pats = {"noetic": r"\^\d", "state": r"\^\d\^[PCEO]", "state_variant": r"\^\d\^[PCEO](?:_\{F\d\})?(?:\|[TAfE])?",
            "domain": r"[PCEO]", "register": r"[TAfE]", "drive": r"F\d", "relation": r"\^\d\^[PCEO] -> \^\d\^[PCEO]"}
    for e in elements:
        if not re.fullmatch(pats[kind], e):
            raise Refusal("NOT_CCE", "element %s does not fit a %s set" % (e, kind))


def render_set(s):
    if "builtin" in s:
        return "all " + s["builtin"]
    if "name" in s:
        return "the set named " + s["name"]
    if "op" in s:
        return "the %s of (%s) and (%s)" % (s["op"], render_set(s["left"]), render_set(s["right"]))
    return "the %s set {%s}" % (WORD_OF_KIND[s["kind"]], ", ".join(render_element(e) for e in sorted(set(s["elements"]))))


def parse_meta(body):
    """Return a meta statement or None if the sentence is not a meta-logic form."""
    m = re.fullmatch(r"Let the set named ([A-Z][A-Za-z0-9_]*) be (.+)", body)
    if m:
        return ["let", m.group(1), parse_set(m.group(2))]
    m = re.fullmatch(r"The size of (.+) is (%s)" % NUM_RX, body)
    if m:
        return ["size", parse_set(m.group(1)), cce.num(m.group(2))]
    for word, kind in ((" is covered by: ", "cover"), (" is partitioned into: ", "partition")):
        parts = cce._split_top(body, word)
        if len(parts) == 2:
            members = cce._split_top(parts[1], "; ")
            return [kind, parse_set(parts[0]), [parse_set(x) for x in members]]
    for word, sym in SUBSET_WORDS:
        parts = cce._split_top(body, word)
        if len(parts) == 2 and (parts[0].startswith("the ") or parts[0].startswith("all ")):
            return ["subset", parse_set(parts[0]), sym, parse_set(parts[1])]
    for word, neg in ((" is not in ", True), (" is in ", False)):
        parts = cce._split_top(body, word)
        if len(parts) == 2 and (parts[1].startswith("the ") or parts[1].startswith("all ")):
            return ["member", parse_element(parts[0]), parse_set(parts[1]), neg]
    return None


def render_meta(st):
    k = st[0]
    if k == "member":
        return "%s is %sin %s." % (render_element(st[1]), "not " if st[3] else "", render_set(st[2]))
    if k == "subset":
        word = {sym: w for w, sym in SUBSET_WORDS}[st[2]]
        return render_set(st[1]) + word + render_set(st[3]) + "."
    if k == "size":
        return "The size of %s is %s." % (render_set(st[1]), st[2])
    if k == "let":
        return "Let the set named %s be %s." % (st[1], render_set(st[2]))
    word = " is covered by: " if k == "cover" else " is partitioned into: "
    return render_set(st[1]) + word + "; ".join(render_set(x) for x in st[2]) + "."


def parse_fractal(seq_text, sep):
    terms = cce._split_top(seq_text, sep)
    if len(terms) > MAX_FRACTAL_DEPTH:
        raise Refusal("NEST_TOO_DEEP", "a nested Noetic sequence of %d terms (cap %d)" % (len(terms), MAX_FRACTAL_DEPTH))
    return [cce.parse_state(t, require_domain=False) for t in terms]


def render_fractal(terms, rng=None):
    sep, lead = " : ", "The fractal sequence is "
    if rng is not None and rng.random() < 0.5:
        sep, lead = " inside ", "The nesting is "
    return lead + sep.join(cce.render_state(cce.norm_state(_fterm(t)), rng) for t in terms) + "."


def parse_expr(text):
    if text.startswith("("):
        end = _match_paren(text, 0)
        for word, op in EXPR_OPS:
            if text[end:].startswith(word):
                rstart = end + len(word) - 1
                if _match_paren(text, rstart) != len(text) - 1:
                    raise Refusal("NOT_CCE", "expression form")
                left, right = parse_expr(text[1:end]), parse_expr(text[rstart + 1:-1])
                if op == "times" and "state" in left and "state" in right and \
                        left["state"]["noetic"] == right["state"]["noetic"]:
                    raise Refusal("OPERATOR_DISCIPLINE", "same-Noetic x needs a named emergent result")
                return {"op": op, "left": left, "right": right}
        raise Refusal("NOT_CCE", "unknown expression operator")
    if "combined" in text:
        raise Refusal("OPERATOR_DISCIPLINE", "'combined' needs a named result")
    return {"state": cce.parse_state(text, require_domain=False)}


def render_expr(e, rng=None):
    if "state" in e:
        return cce.render_state(cce.norm_state(e["state"]), rng)
    return "(%s) %s (%s)" % (render_expr(e["left"], rng), WORD_OF_EXPR_OP[e["op"]], render_expr(e["right"], rng))


# --- parse / render ----------------------------------------------------------------------------------------------
def parse(text, max_depth=cce.MAX_NEST_DEPTH):
    if not isinstance(text, str) or not text.strip():
        raise Refusal("NOT_CCE", "empty")
    s = text.strip()
    if s == cce.FIXED_UNDETERMINED or re.match(r"I need .+ What is it\?$|I cannot support that: |Are we still on ", s):
        c = cce.parse(s, max_depth)
        c.update({"fractal": [], "meta": [], "expr": None})
        return c
    evidence = "NONE"
    for lead, ev in (("I checked: ", "CHECKED"), ("You said: ", "USER_SAID")):
        if s.startswith(lead):
            s, evidence = s[len(lead):], ev
            break
    cce._global_checks(s)
    c = cce.empty_content()
    c["evidence"] = evidence
    extra = {"fractal": [], "meta": [], "expr": None}
    minds = set()
    for sent in cce.split_sentences(s):
        if sent.endswith("?"):
            raise Refusal("NOT_CCE", "question form not in CCE")
        body = sent[:-1]
        m = re.fullmatch(r"The fractal sequence is (.+)", body)
        if m:
            extra["fractal"] = parse_fractal(m.group(1), " : ")
            continue
        m = re.fullmatch(r"The nesting is (.+)", body)
        if m:
            extra["fractal"] = parse_fractal(m.group(1), " inside ")
            continue
        m = re.fullmatch(r"The expression is (.+)", body)
        if m:
            if extra["expr"] is not None:
                raise Refusal("NOT_CCE", "two expressions")
            extra["expr"] = parse_expr(m.group(1))
            continue
        st = parse_meta(body)
        if st is not None:
            extra["meta"].append(st)
            continue
        cce._parse_sentence(sent, c, minds, max_depth)
    c.update(extra)
    return c


def render(content, rng=None):
    c = canonical(content)
    base = {k: v for k, v in c.items() if k not in ("fractal", "meta", "expr")}
    base["fractal"] = []
    extras = []
    if c["fractal"]:
        if len(c["fractal"]) > MAX_FRACTAL_DEPTH:
            raise ValueError("fractal deeper than %d" % MAX_FRACTAL_DEPTH)
        extras.append(render_fractal(c["fractal"], rng))
    extras += [render_meta(st) for st in c["meta"]]
    if c["expr"] is not None:
        extras.append("The expression is %s." % render_expr(c["expr"], rng))
    base_has = (base["gate"] != "RIGHT_PATH" or base["turn"] != "ANSWER" or base["topic"] or base["terms"]
                or base["sequence"] or base["recipe"] or base["stocks"] or base["relations"])
    if not extras:
        return cce.render(base, rng)
    if base["gate"] == "UNDETERMINED" or base["turn"] in ("CLARIFY", "REFUSE_CLAIM"):
        raise ValueError("a fixed turn form cannot carry extra sentences")
    lead = {"CHECKED": "I checked: ", "USER_SAID": "You said: ", "NONE": ""}[base["evidence"]]
    head = ""
    if base_has:
        b = dict(base)
        b["evidence"] = "NONE"
        head = cce.render(b, rng) + " "
    return lead + head + " ".join(extras)


def round_trip(content, rng=None, seed=None):
    receipt = {"cce_version": "cce-v0.1b", "content_hash_in": None, "seed": seed, "sentence": None,
               "content_hash_out": None, "ok": False, "rejection": None}
    try:
        receipt["content_hash_in"] = digest(content)
        sentence = render(content, rng)
        receipt["sentence"] = sentence
        back = parse(sentence)
        receipt["content_hash_out"] = digest(back)
        receipt["ok"] = receipt["content_hash_out"] == receipt["content_hash_in"]
    except Refusal as exc:
        receipt["rejection"] = exc.code
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        receipt["rejection"] = "RENDER_" + type(exc).__name__
    receipt["receipt_id"] = hashlib.sha256(json.dumps(receipt, sort_keys=True, ensure_ascii=False)
                                           .encode("utf-8")).hexdigest()[:16]
    return receipt


def say(content, seed, cap=cce.DRAW_CAP):
    if canonical(content)["gate"] == "UNDETERMINED":
        return {"sentence": cce.FIXED_UNDETERMINED, "drawn": False, "tries": 0}
    rng = random.Random(seed)
    for attempt in range(1, cap + 1):
        r = round_trip(content, rng, seed)
        if r["ok"]:
            return {"sentence": r["sentence"], "drawn": True, "tries": attempt, "receipt": r}
    r = round_trip(content, None, seed)
    return {"sentence": r["sentence"] if r["ok"] else None, "drawn": False, "tries": cap, "receipt": r}
