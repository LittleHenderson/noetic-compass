"""LM-T1b scoring parts (FROZEN_T1B.json): B1 nesting ledger, B2 meta-logic ledger, B3 added hand set, B4 compiler
identity, B5 no-damage regression, B6 held-out book examples, B7 recipe grammar comparison."""
from fractions import Fraction
import json
import re

import cce
import cce_v01b as b
import cas_ast as ca
from lacunarity_machine.universe import Universe, Cell
from lacunarity_machine.ledger import Ledger
from lacunarity_machine.readers import deterministic_read

EXAMPLES = r"C:\Users\wakil\Documents\Codex\2026-10-08\task-4\cas-online\dist\downloads\Programming_in_CAS_Corrected_Examples_2026-10-11.txt"


def _with(c, **kw):
    out = b.empty_content()
    out.update(c)
    out.update(kw)
    return out


# --- B1 ---------------------------------------------------------------------------------------------------------
def nest_probes(k, n):
    seq = [(n + 1 + i) % 10 for i in range(k - 1)] + [n]
    plain = [{"noetic": x, "domain": None, "register": None, "drive": None} for x in seq]
    tails = [{"noetic": x, "domain": "C", "register": (["f"] if i == k - 1 else None), "drive": None}
             for i, x in enumerate(seq)]
    return [_with({}, fractal=plain), _with({}, fractal=tails)], seq


def _compiler_seq_ok(content, seq):
    v = ca.compile_view(ca.cas_parts(content)["fractal"])
    if not v["valid"]:
        return False
    r = v["result"]
    if r.get("kind") == "fractal":
        return r.get("sequence") == seq
    return len(seq) == 1 and r.get("kind") == "state" and r.get("dominant_operator") == "CO-%d" % seq[0]


def b1():
    cells = [Cell("depth%d|^%d" % (k, n), True, "fractal") for k in range(1, 6) for n in range(10)]
    uni = Universe("U-NEST (depth 1..5 x governing Noetic)", cells)
    led = Ledger(uni)
    for cell in cells:
        led.charge(cell.cell_id, 0, tag="'The fractal sequence is ...' / 'The nesting is ... inside ...'")
    rt_ok = comp_ok = total = 0
    contents = []
    for k in range(1, 6):
        for n in range(10):
            probes, seq = nest_probes(k, n)
            hits = 0
            for p in probes:
                total += 1
                r = b.round_trip(p)
                c_ok = _compiler_seq_ok(p, seq)
                rt_ok += r["ok"]
                comp_ok += c_ok
                hits += r["ok"] and c_ok
                contents.append(p)
            led.probe("depth%d|^%d" % (k, n), 1, hits, len(probes), tag="roundtrip")
    read = deterministic_read(uni, led, Fraction(1), "roundtrip")
    return {"state_counts": read["state_counts"], "probes": total, "round_trip_ok": rt_ok, "compiler_sequence_ok": comp_ok,
            "covered_without_charge": sum(r["covered_without_charge"] for r in read["rows"]),
            "pass": read["state_counts"]["COVERED"] == 50 and rt_ok == comp_ok == total}, contents


# --- B2 ---------------------------------------------------------------------------------------------------------
SAMPLE = {"noetic": (["^2", "^7"], ["^2"]), "state": (["^2^P", "^7^C"], ["^2^P"]),
          "state_variant": (["^2^P_{F2}|A", "^7^C|f"], ["^2^P_{F2}|A"]), "domain": (["P", "C"], ["P"]),
          "register": (["A", "f"], ["A"]), "drive": (["F1", "F2"], ["F1"]),
          "relation": (["^5^P -> ^5^C", "^2^C -> ^2^E"], ["^5^P -> ^5^C"])}
OPERATORS = ["member", "nonmember", "subset_eq", "subset_strict", "superset_eq", "superset_strict", "union",
             "intersection", "difference", "pullback", "product", "cover", "partition", "size", "let"]
KINDS = list(SAMPLE) + ["builtin"]


def meta_probe(op, kind):
    if kind == "builtin":
        S, T = {"builtin": "Domains"}, {"kind": "domain", "elements": ["P"]}
        el = "P"
        cover_members = [{"kind": "domain", "elements": ["C", "P"]}, {"kind": "domain", "elements": ["E", "O"]}]
    else:
        s, t = SAMPLE[kind]
        S, T = {"kind": kind, "elements": sorted(s)}, {"kind": kind, "elements": sorted(t)}
        el = s[0]
        cover_members = [{"kind": kind, "elements": [s[0]]}, {"kind": kind, "elements": [s[1]]}]
    st = {"member": [["member", el, S, False]], "nonmember": [["member", el, S, True]],
          "subset_eq": [["subset", T, "⊆", S]], "subset_strict": [["subset", T, "⊂", S]],
          "superset_eq": [["subset", S, "⊇", T]], "superset_strict": [["subset", S, "⊃", T]],
          "size": [["size", S, str(len(S.get("elements", [])) or 4)]],
          "let": [["let", "Core", S], ["subset", T, "⊆", {"name": "Core"}]],
          "cover": [["cover", S, cover_members]], "partition": [["partition", S, cover_members]]}.get(op)
    if st is None:
        st = [["size", {"op": op, "left": S, "right": T}, "1"]]
    return _with({}, meta=st)


def b2():
    cells, probes = [], {}
    for op in OPERATORS:
        for kind in KINDS:
            p = meta_probe(op, kind)
            v = ca.compile_view(ca.cas_parts(p)["meta"])
            eligible = v["valid"] or v.get("stage", "").startswith("execution")
            cells.append(Cell("%s|%s" % (op, kind), eligible, "meta"))
            probes["%s|%s" % (op, kind)] = (p, v)
    uni = Universe("U-META (operator x set kind)", cells)
    led = Ledger(uni)
    for cell in cells:
        if cell.eligible:
            led.charge(cell.cell_id, 0, tag="addendum section B")
    rt = 0
    for cell in cells:
        if cell.eligible:
            ok = b.round_trip(probes[cell.cell_id][0])["ok"]
            rt += ok
            led.probe(cell.cell_id, 1, 1 if ok else 0, 1, tag="roundtrip")
    read = deterministic_read(uni, led, Fraction(1), "roundtrip")
    ineligible = [c.cell_id for c in cells if not c.eligible]
    return {"cells": len(cells), "eligible": read["n_eligible"], "ineligible_by_compiler": ineligible,
            "state_counts": read["state_counts"], "round_trip_ok": rt,
            "covered_without_charge": sum(r["covered_without_charge"] for r in read["rows"]),
            "pass": read["state_counts"]["COVERED"] == read["n_eligible"]}, [probes[c.cell_id][0] for c in cells if c.eligible]


# --- B3 ---------------------------------------------------------------------------------------------------------
def b3(items):
    rows = []
    for it in items:
        exp = it["expect"]
        row = {"id": it["id"], "group": it.get("group"), "kind": it["kind"], "wording": it.get("wording")}
        try:
            got, row["refusal"] = b.parse(it["text"]), None
        except b.Refusal as exc:
            got, row["refusal"] = None, exc.code
            row["refusal_detail"] = exc.detail[:160]
        if "refusal" in exp:
            row["ok"] = got is None and row["refusal"] == exp["refusal"]
        else:
            try:
                gold = b.normalize(exp["content"])
            except Exception as exc:
                gold = None
                row["gold_error"] = "%s: %s" % (type(exc).__name__, exc)
            same = got is not None and gold is not None and b.normalize(got) == gold
            rt = b.round_trip(got)["ok"] if got is not None else False
            row.update({"content_equal": same, "round_trip": rt, "ok": bool(same and rt)})
            if got is not None and not same:
                row["got"] = b.canonical(got)
        rows.append(row)
    by = {}
    for g in ("NESTED", "METALOGIC"):
        sub = [r for r in rows if r["group"] == g]
        by[g] = "%d of %d" % (sum(r["ok"] for r in sub), len(sub))
    return {"items": len(rows), "ok": sum(r["ok"] for r in rows), "by_group": by, "pass": sum(r["ok"] for r in rows) == len(rows) == 16,
            "rows": rows}


# --- B4 ---------------------------------------------------------------------------------------------------------
def b4(contents):
    checked = equal = valid = 0
    bad = []
    for c in contents:
        try:
            back = b.parse(b.render(c))
        except Exception:
            continue
        p1, p2 = ca.cas_parts(c), ca.cas_parts(back)
        for key in p1:
            if key == "recipe" and any(t["kind"] == "emergent" for t in b.canonical(c)["recipe"]["terms"]):
                continue
            checked += 1
            v1, v2 = ca.compile_view(p1[key]), ca.compile_view(p2.get(key, ""))
            valid += v1["valid"]
            if v1 == v2:
                equal += 1
            elif len(bad) < 10:
                bad.append({"part": key, "cas": p1[key]})
    return {"parts_checked": checked, "equal": equal, "compiler_valid": valid, "pass": checked == equal, "first_unequal": bad}


# --- B5 ---------------------------------------------------------------------------------------------------------
def b5(recipe_contents, hand_items):
    r_ok = sum(b.round_trip(_with(c))["ok"] for c in recipe_contents)
    h_ok = 0
    for it in hand_items:
        exp = it["expect"]
        try:
            got = b.parse(it["text"])
        except b.Refusal as exc:
            h_ok += "refusal" in exp and exp["refusal"] == exc.code
            continue
        if "content" in exp:
            try:
                h_ok += b.normalize(got) == b.normalize(exp["content"]) and b.round_trip(got)["ok"]
            except Exception:
                pass
    return {"recipes_round_trip": r_ok, "of": len(recipe_contents), "hand_set_ok": h_ok, "hand_of": len(hand_items),
            "pass": r_ok == len(recipe_contents) == 576 and h_ok == len(hand_items) == 64}


# --- B6 ---------------------------------------------------------------------------------------------------------
def load_examples(path=EXAMPLES):
    """Each case = the header block after the previous END SOURCE (first line = name, 'Expected: ...' lines)
    plus the lines between SOURCE and END SOURCE."""
    lines = open(path, encoding="utf-8").read().splitlines()
    cases, header, i = [], [], 0
    while i < len(lines):
        if lines[i] == "SOURCE":
            j = lines.index("END SOURCE", i + 1)
            block = [h for h in header if h.strip()]
            exp_lines = [h for h in block if h.startswith("Expected")]
            name = [h for h in block if not h.startswith("Expected")][-1]
            accepted = any(h.strip() == "Expected: accepted" for h in exp_lines)
            cases.append({"name": name.strip(), "expected": "accepted" if accepted else "rejected",
                          "source": chr(10).join(lines[i + 1:j])})
            header, i = [], j + 1
            continue
        header.append(lines[i])
        i += 1
    return cases


def b6(cases):
    rows = []
    for case in cases:
        row = {"name": case["name"], "expected": case["expected"]}
        v0 = ca.compile_view(case["source"])
        row["compiler_valid"] = v0["valid"]
        if not v0["valid"]:
            row["status"] = "NO_CONTENT_REJECTED_BY_COMPILER"
            rows.append(row)
            continue
        try:
            content = ca.content_from_cas(case["source"])
        except ca.FormGap as g:
            row["status"], row["gap"] = "FORM_GAP", g.construct
            rows.append(row)
            continue
        except Exception as exc:
            row["status"], row["gap"] = "FORM_GAP", "%s: %s" % (type(exc).__name__, str(exc)[:80])
            rows.append(row)
            continue
        r = b.round_trip(content)
        row["cce_round_trip"] = r["ok"]
        row["sentence"] = r["sentence"]
        if not r["ok"]:
            row["status"], row["rejection"] = "CCE_ROUND_TRIP_FAIL", r["rejection"]
            rows.append(row)
            continue
        back = b.parse(r["sentence"])
        try:
            parts = ca.cas_parts(back)
        except ca.FormGap as g:
            row["status"], row["gap"] = "FORM_GAP", g.construct
            rows.append(row)
            continue
        if len(parts) != 1:
            row["status"], row["gap"] = "FORM_GAP", "several parts"
            rows.append(row)
            continue
        cas_back = list(parts.values())[0]
        row["cas_back"] = cas_back
        row["status"] = "EXACT" if ca.compile_view(cas_back) == v0 else "COMPILER_VIEW_DIFFERS"
        rows.append(row)
    from collections import Counter
    acc = [r for r in rows if r["expected"] == "accepted"]
    return {"cases": len(rows), "accepted_cases": len(acc), "rejected_cases": len(rows) - len(acc),
            "status_counts_accepted": dict(Counter(r["status"] for r in acc)),
            "status_counts_rejected": dict(Counter(r["status"] for r in rows if r["expected"] != "accepted")),
            "exact_of_accepted": sum(r["status"] == "EXACT" for r in acc),
            "gaps": dict(Counter(r.get("gap") for r in rows if r["status"] == "FORM_GAP")),
            "rows": rows}


# --- B7 ---------------------------------------------------------------------------------------------------------
def b7(recipes):
    dis = []
    for r in recipes:
        try:
            new = ca.content_from_cas(r["expression"])
            same = b.normalize(new) == b.normalize(_with(r["content"]))
        except Exception as exc:
            same, new = False, None
        if not same:
            dis.append({"seed_id": r["seed_id"], "expression": r["expression"]})
    return {"seeds": len(recipes), "disagreements": len(dis), "rows": dis[:50]}
