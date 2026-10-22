"""CCE v0.1c-R = CCE v0.1b (cce_v01b.py, imported unchanged) + the dotted fractal notation under the owner's N1
ruling ("CAS Φ / Definition 26.1 (outer last) both . and :"): first term = innermost for BOTH separators;
dotted a.b.c == Φ⟨a:b:c⟩; no reversal; "fractal_notation" kept only to say it back in the input's separator.
"""
import hashlib
import json
import random
import re

import cce
import cce_v01b as b
from cce import Refusal, NOETIC_NAMES

_INV = {v: k for k, v in NOETIC_NAMES.items()}
DOTTED_RX = re.compile(r"The Noetic fractal is (.+)")


def canonical(c):
    out = b.canonical(c)
    nota = c.get("fractal_notation")
    out["fractal_notation"] = (nota or "PHI") if out["fractal"] else None
    return out


def normalize(c):
    return json.dumps(canonical(c), sort_keys=True, ensure_ascii=False)


def digest(c):
    return hashlib.sha256(normalize(c).encode("utf-8")).hexdigest()


def _term(n):
    return {"noetic": n, "domain": None, "register": None, "drive": None}


def parse_dotted(body):
    text = body
    if re.fullmatch(r"[0-9.:]+", text):
        if ":" in text:
            raise Refusal("NOT_CCE", "mixed separators in one nested Noetic")
        digits = text.split(".")
        if not all(re.fullmatch(r"[0-9]", d) for d in digits) or len(digits) < 2:
            raise Refusal("NOT_CCE", "dotted form needs 2 or more single digits")
        seq = [int(d) for d in digits]
    else:
        names = text.split(" within ")
        if len(names) < 2 or not all(n in _INV for n in names):
            raise Refusal("NOT_CCE", "dotted words form: " + text[:60])
        seq = [_INV[n] for n in names]
    if len(seq) > b.MAX_FRACTAL_DEPTH:
        raise Refusal("NEST_TOO_DEEP", "a nested Noetic of %d levels (cap %d)" % (len(seq), b.MAX_FRACTAL_DEPTH))
    return [_term(n) for n in seq]


def render_dotted(terms, rng=None):
    if any(t.get("domain") or t.get("register") or t.get("drive") for t in terms):
        raise ValueError("dotted form carries no tails in v0.1c-R")
    if rng is not None and rng.random() < 0.5:
        return "The Noetic fractal is %s." % " within ".join(NOETIC_NAMES[t["noetic"]] for t in terms)
    return "The Noetic fractal is %s." % ".".join(str(t["noetic"]) for t in terms)


def parse(text, max_depth=cce.MAX_NEST_DEPTH):
    if not isinstance(text, str) or not text.strip():
        raise Refusal("NOT_CCE", "empty")
    s = text.strip()
    lead = ""
    for ld in ("I checked: ", "You said: "):
        if s.startswith(ld):
            lead, s = ld, s[len(ld):]
    if "The Noetic fractal is " not in s:
        c = b.parse(text, max_depth)
        c["fractal_notation"] = "PHI" if c["fractal"] else None
        return c
    cce._global_checks(s)
    rest, fractal = [], None
    for sent in cce.split_sentences(s):
        m = DOTTED_RX.fullmatch(sent[:-1]) if sent.endswith(".") else None
        if m:
            if fractal is not None:
                raise Refusal("NOT_CCE", "two nested Noetics in one text")
            fractal = parse_dotted(m.group(1))
        else:
            rest.append(sent)
    if rest:
        c = b.parse(lead + " ".join(rest), max_depth)
        if c["fractal"]:
            raise Refusal("NOT_CCE", "two nested Noetics in one text")
    else:
        c = b.empty_content()
        c["evidence"] = {"I checked: ": "CHECKED", "You said: ": "USER_SAID", "": "NONE"}[lead]
    c["fractal"] = fractal
    c["fractal_notation"] = "DOTTED"
    return c


def render(content, rng=None):
    c = canonical(content)
    if c["fractal_notation"] != "DOTTED":
        return b.render(content, rng)
    base = dict(content)
    base["fractal"] = []
    base.pop("fractal_notation", None)
    bc = b.canonical(base)
    lead = {"CHECKED": "I checked: ", "USER_SAID": "You said: ", "NONE": ""}[bc["evidence"]]
    has_base = (bc["terms"] or bc["sequence"] or bc["recipe"] or bc["stocks"] or bc["relations"] or bc["meta"]
                or bc["expr"] is not None or bc["topic"] or bc["turn"] != "ANSWER" or bc["gate"] != "RIGHT_PATH")
    head = ""
    if has_base:
        bb = dict(base)
        bb["evidence"] = "NONE"
        head = b.render(bb, rng) + " "
    return lead + head + render_dotted(c["fractal"], rng)


def round_trip(content, rng=None, seed=None):
    receipt = {"cce_version": "cce-v0.1c-R", "content_hash_in": None, "seed": seed, "sentence": None,
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
