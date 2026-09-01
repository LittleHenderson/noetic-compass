"""pathb_roundtrip.py -- the INDEPENDENT PATH B round-trip checker.

Construction-gold law: the formal operation graph exists first; deterministic
templates render it; THIS parser must recover the full graph + discourse order
from the SURFACE TEXT alone (template regexes + entity-type membership + verb
inventories), re-derive the answer through the frozen solver, and match the
record exactly. Any mismatch excludes the record (never relabels it).

Independence discipline: the parser reads only the registered template strings,
verb inventories, and entity bundles (public registration data); it never reads
the record's ops/answer fields except to COMPARE at the end. The family is
DERIVED from the surface (family-disjoint verb sets), not taken from metadata.
"""
from __future__ import annotations

import re

from pathb_core import (FAMILIES, FORMS, FORM_ALLOC, IDEAS, MINDS, PARTS,
                        Q_FRAMES, VERBS, family_verbs, solve)

_ENT = r"[a-z]+"


def _clause_patterns(fam):
    """[(cls, compiled_regex)] for one family (its verbs + its forms)."""
    pats = []
    for cls, forms in FORMS.items():
        vs = "|".join(re.escape(v) for v in family_verbs(cls, fam))
        for fi in FORM_ALLOC[fam]:
            t = re.escape(forms[fi])
            t = t.replace(re.escape("{v}"), f"(?P<v>{vs})")
            for slot in ("i", "m", "a", "b", "p1", "p2", "p3"):
                t = t.replace(re.escape("{%s}" % slot),
                              f"(?P<{slot}>{_ENT})")
            pats.append((cls, re.compile("^" + t + "$")))
    return pats


_PATS = {fam: _clause_patterns(fam) for fam in FAMILIES}


def _q_patterns(fam):
    v2 = "|".join(re.escape(v) for v in family_verbs("^2", fam))
    v3 = "|".join(re.escape(v) for v in family_verbs("^3", fam))
    v8 = "|".join(re.escape(v) for v in family_verbs("^8", fam))
    out = []
    for key, frame in Q_FRAMES.items():
        t = re.escape(frame)
        t = t.replace(re.escape("{v2}"), f"(?:{v2})")
        t = t.replace(re.escape("{v3}"), f"(?:{v3})")
        t = t.replace(re.escape("{v8}"), f"(?:{v8})")
        for slot in ("x", "i1", "m"):
            t = t.replace(re.escape("{%s}" % slot), f"(?P<{slot}>{_ENT})")
        # QB_ORD frames repeat {m}: the second occurrence must backreference
        t = t.replace(f"(?P<m>{_ENT})", f"(?P<m>{_ENT})", 1)
        if t.count("(?P<m>") == 2:
            first = t.find("(?P<m>")
            second = t.find("(?P<m>", first + 1)
            t = t[:second] + "(?P=m)" + t[second + len(f"(?P<m>{_ENT})"):]
        out.append((key, re.compile("^" + t + "$")))
    return out


_QPATS = {fam: _q_patterns(fam) for fam in FAMILIES}


def _etype(split, e):
    if e in MINDS[split]:
        return "mind"
    if e in IDEAS[split]:
        return "idea"
    if e in PARTS[split]:
        return "part"
    return None


def parse_clause(text, split, fam):
    """Return (cls, args) or None; requires a UNIQUE type-consistent parse."""
    hits = []
    for cls, pat in _PATS[fam]:
        mo = pat.match(text)
        if not mo:
            continue
        g = mo.groupdict()
        if cls == "^2":
            if _etype(split, g["i"]) == "idea" and _etype(split, g["m"]) == "mind":
                hits.append((cls, (g["i"], g["m"])))
        elif cls == "^3":
            if _etype(split, g["m"]) == "mind" and _etype(split, g["i"]) == "idea":
                hits.append((cls, (g["m"], g["i"])))
        elif cls == "^6":
            if _etype(split, g["i"]) == "idea" and all(
                    _etype(split, g[k]) == "part" for k in ("p1", "p2", "p3")):
                hits.append((cls, (g["i"], (g["p1"], g["p2"], g["p3"]))))
        else:
            if _etype(split, g["a"]) == "idea" and _etype(split, g["b"]) == "idea" \
                    and _etype(split, g["m"]) == "mind":
                hits.append((cls, (g["a"], g["b"], g["m"])))
    uniq = {(c, a) for c, a in hits}
    if len(uniq) != 1:
        return None
    return next(iter(uniq))


def parse_question(text, split, fam):
    for key, pat in _QPATS[fam]:
        mo = pat.match(text)
        if not mo:
            continue
        g = mo.groupdict()
        if key == "QB_REL":
            if _etype(split, g["x"]) == "idea":
                return {"qfam": "QB_REL", "anchors": [g["x"]]}
        elif key == "QB_COMP":
            if _etype(split, g["x"]) == "idea":
                return {"qfam": "QB_COMP", "anchors": [g["x"]]}
        elif key == "QB_INT":
            if _etype(split, g["i1"]) == "idea" and _etype(split, g["m"]) == "mind":
                return {"qfam": "QB_INT", "anchors": [g["i1"], g["m"]]}
        else:
            if _etype(split, g["m"]) == "mind" and _etype(split, g["x"]) == "idea":
                side = "AFTER" if key.endswith("AFTER") else "BEFORE"
                return {"qfam": "QB_ORD", "anchors": [g["m"], g["x"]],
                        "side": side}
    return None


def check_record(rec):
    """(ok, why). Full surface round trip: family derived from verbs; every
    clause uniquely parsed; question parsed; solver answer == record answer;
    recovered graph == record graph (class+args+order)."""
    split = rec["split"]
    fam_hits = []
    for fam in FAMILIES:
        parsed = [parse_clause(c["text"], split, fam) for c in rec["clauses"]]
        if all(p is not None for p in parsed):
            q = parse_question(rec["question"], split, fam)
            if q is not None:
                fam_hits.append((fam, parsed, q))
    if len(fam_hits) != 1:
        return False, f"family not uniquely derivable ({len(fam_hits)})"
    fam, parsed, qspec = fam_hits[0]
    if fam != rec["family"]:
        return False, "derived family mismatch"
    # graph equality (class + args + order)
    want = []
    for entry in rec["ops"]:
        c, a = entry
        want.append((c, (a[0], tuple(a[1])) if c == "^6" else (c, tuple(a))[1]))
    got = [(c, a) for c, a in parsed]
    want2 = []
    for entry in rec["ops"]:
        c, a = entry
        if c == "^6":
            want2.append((c, (a[0], tuple(a[1]))))
        else:
            want2.append((c, tuple(a)))
    if got != want2:
        return False, "recovered graph differs from trace"
    try:
        ans, _ = solve(got, qspec)
    except AssertionError as exc:
        return False, f"solver refused: {exc}"
    if ans != rec["answer"]:
        return False, f"solver answer {ans!r} != record {rec['answer']!r}"
    if qspec["qfam"] != rec["question_type"]:
        return False, "question family mismatch"
    return True, "ok"
