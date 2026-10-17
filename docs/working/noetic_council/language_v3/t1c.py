"""LM-T1c scoring (FROZEN_T1C.json): C1 dotted ledger, C2 ruled hand set, C3 same nesting, C4 refusals, C5 no damage."""
from fractions import Fraction
import random

import cce_v01b as b
import cce_v01c as c
import cas_ast as ca
import t1b
from lacunarity_machine.universe import Universe, Cell
from lacunarity_machine.ledger import Ledger
from lacunarity_machine.readers import deterministic_read


def dotted_content(seq):
    x = b.empty_content()
    x["fractal"] = [c._term(n) for n in seq]
    x["fractal_notation"] = "DOTTED"
    return x


def c1_c3():
    cells = [Cell("depth%d|last^%d" % (k, n), True, "dotted") for k in range(2, 6) for n in range(10)]
    uni = Universe("U-DOTTED (depth 2..5 x outermost Noetic)", cells)
    led = Ledger(uni)
    for cell in cells:
        led.charge(cell.cell_id, 0, tag="'The Noetic fractal is a.b.c.' / '... within ...'")
    comp_ok = same_ok = total = 0
    forms = {"digits": 0, "within": 0}
    for k in range(2, 6):
        for n in range(10):
            seq = [(n + 1 + i) % 10 for i in range(k - 1)] + [n]
            content = dotted_content(seq)
            hits = 0
            seen = set()
            for seed in range(40):
                r = c.round_trip(content, random.Random(seed))
                form = "within" if (r["sentence"] and " within " in r["sentence"]) else "digits"
                if form in seen:
                    continue
                seen.add(form)
                forms[form] += 1
                hits += r["ok"]
                if len(seen) == 2:
                    break
            total += 1
            cas = ca.fractal_cas(c.canonical(content)["fractal"])
            v = ca.compile_view(cas)
            ok_c = v["valid"] and v["result"].get("sequence") == seq
            comp_ok += ok_c
            phi = b.empty_content()
            phi["fractal"] = [c._term(x) for x in seq]
            a1, a2 = c.canonical(content), c.canonical(phi)
            same = ({k2: v2 for k2, v2 in a1.items() if k2 != "fractal_notation"} ==
                    {k2: v2 for k2, v2 in a2.items() if k2 != "fractal_notation"}
                    and ca.fractal_cas(a1["fractal"]) == ca.fractal_cas(a2["fractal"]) and a2["fractal_notation"] == "PHI")
            same_ok += same
            led.probe("depth%d|last^%d" % (k, n), 1, hits if ok_c else 0, 2, tag="roundtrip")
    read = deterministic_read(uni, led, Fraction(1), "roundtrip")
    c1 = {"state_counts": read["state_counts"], "compiler_sequence_equal": comp_ok, "of": total,
          "forms_exercised": forms, "covered_without_charge": sum(r["covered_without_charge"] for r in read["rows"]),
          "pass": read["state_counts"]["COVERED"] == 40 and comp_ok == total}
    c3 = {"same_nesting_as_phi": same_ok, "of": total, "pass": same_ok == total}
    return c1, c3


def c2(items):
    rows = []
    for it in items:
        row = {"id": it["id"], "wording": it.get("wording")}
        try:
            got = c.parse(it["text"])
            gold = c.normalize(it["expect"]["content"])
            row["content_equal"] = c.normalize(got) == gold
            row["round_trip"] = c.round_trip(got)["ok"]
            if not row["content_equal"]:
                row["got"] = c.canonical(got)
        except c.Refusal as exc:
            row.update({"content_equal": False, "round_trip": False, "refusal": exc.code})
        except Exception as exc:
            row.update({"content_equal": False, "round_trip": False, "error": "%s: %s" % (type(exc).__name__, exc)})
        row["ok"] = row["content_equal"] and row["round_trip"]
        rows.append(row)
    return {"items": len(rows), "ok": sum(r["ok"] for r in rows), "pass": sum(r["ok"] for r in rows) == len(rows) == 4,
            "rows": rows}


def c4():
    cases = {"The Noetic fractal is 5.1:3.": "NOT_CCE", "The Noetic fractal is 1.2.3.4.5.6.": "NEST_TOO_DEEP",
             "The Noetic fractal is 5.": "NOT_CCE"}
    got = {}
    for text, code in cases.items():
        try:
            c.parse(text)
            got[text] = "PARSED"
        except c.Refusal as exc:
            got[text] = exc.code
    ok = sum(got[t] == code for t, code in cases.items())
    return {"cases": got, "ok": ok, "pass": ok == 3}


def c5(recipe_contents, hand64, add16):
    r_ok = sum(c.round_trip(t1b._with(x))["ok"] for x in recipe_contents)

    def score(items):
        n = 0
        for it in items:
            exp = it["expect"]
            try:
                got = c.parse(it["text"])
            except c.Refusal as exc:
                n += "refusal" in exp and exp["refusal"] == exc.code
                continue
            if "content" in exp:
                try:
                    want = dict(exp["content"])
                    n += c.normalize(got) == c.normalize(want) and c.round_trip(got)["ok"]
                except Exception:
                    pass
        return n
    h64, h16 = score(hand64), score(add16)
    nest = 0
    for k in range(1, 6):
        for n in range(10):
            probes, _ = t1b.nest_probes(k, n)
            nest += sum(c.round_trip(p)["ok"] for p in probes)
    return {"recipes": r_ok, "hand64": h64, "add16": h16, "nest_probes": nest,
            "pass": r_ok == 576 and h64 == 64 and h16 == 16 and nest == 100}
