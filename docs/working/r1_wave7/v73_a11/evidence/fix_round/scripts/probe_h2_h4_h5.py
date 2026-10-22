"""probe_h2_h4_h5.py <amended_pkg_root> <out_json> -- reproduce reviewer items H-2 (a misbound lesson is not caught), H-4 (a
wrong unit on a learned line is not looked at) and H-5 (the test reads the loop sentence, not what the person heard) with
AUTHORED records (the prober's own recipes) scored by the package copy's real frozen score_w6.score_real and its hooked
score_w7.score_real(raw_by_id=...). Scratch evidence only; nothing here is a result."""
import copy
import json
import sys
from fractions import Fraction
from pathlib import Path

PKG = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(PKG))
from r1w7 import common_w7 as C           # noqa: E402
from r1w7 import multi_qty_w7 as MQ       # noqa: E402
from r1w7 import score_w7 as SC           # noqa: E402

MULTS = (Fraction(3), Fraction(3, 2), Fraction(5, 2))


def key_of(ns, iid, noun, raw):
    r = {"noun": noun, "lines": [{"raw": x, "parsed": ns.XG.parse_line(x)} for x in raw]}
    t = ns.rb.exam_rbw1t.turns_for(r, MULTS)
    return MQ.apply(ns.rb.keys_rbw1t.key_item({"id": iid, "raw_lines": raw, "pantry_lines": t["pantry_lines"]}), raw, ns.XG)


def record(key, noun, learned, untaught, *, units=None, scored_reply=None):
    """3 lessons admitted (learned = [(ingredient, value)] in lesson order), stock recorded, the wide gate's G1 ask."""
    if len(untaught) == 1:
        need = f"one batch where {untaught[0]} ran out first while everything else was left over"
    else:
        need = (f"one batch for each of {' and '.join(untaught)}: a batch where that one ran out first while everything "
                f"else was left over")
    sentence = f"I can't say yet how much {noun} we can make. I still need {need}. I didn't guess."
    turns, log, lrs = [], [], []
    for j, (ing, q) in enumerate(learned):
        turns.append({"kind": "turn", "intent": "RECIPE_FOUNDATION_LOOP", "reply": "Got it.",
                      "loop": {"status": "WITNESS_ADMITTED", "path": "wide", "loop_sentence": "Got it.", "writes": 1}})
        e = {"kind": "turn", "status": "WITNESS_ADMITTED", "path": "wide", "admitted": True, "ingredient": ing,
             "product": noun, "reason": "ADMITTED", "value": None, "limiting": None}
        log.append(e)
        lrs.append({"status": "WITNESS_ADMITTED", "admitted": True, "ingredient": ing, "product": noun, "path": "wide",
                    "reason": "ADMITTED", "learned_in_taught_unit": q, "taught_unit": (units or {}).get(j, "cup")})
    for st, sent in (("STOCK_RECORDED", "Noted."), ("UNDETERMINED_CLARIFY", sentence)):
        turns.append({"kind": "turn", "intent": "RECIPE_FOUNDATION_LOOP", "reply": sent,
                      "loop": {"status": st, "path": "wide", "loop_sentence": sent, "writes": 1 if st == "STOCK_RECORDED" else 0}})
        e = {"kind": "turn", "status": st, "path": "wide", "admitted": False, "ingredient": None, "product": None,
             "reason": None, "value": None, "limiting": None}
        log.append(e)
        lrs.append({"status": st, "admitted": False, "ingredient": None, "product": None, "path": "wide", "reason": None,
                    "learned_in_taught_unit": None})
    reply = sentence if scored_reply is None else scored_reply
    turns[-1]["reply"] = reply
    return {"id": key["id"], "turns": turns, "log": log, "lesson_records": lrs,
            "scored_turn": {"status": "UNDETERMINED_CLARIFY", "value": None, "limiting": None, "writes": 0,
                            "inner_status": "UNDETERMINED_CLARIFY", "routed": True},
            "scored_reply": reply, "plain": True,
            "wide_audit": [{"ok": True, "coefficients": 3, "support_slots": 3 + len(untaught)}]}


def score(ns, HV, key, raw, rec):
    keys, inputs, doc = [key], [{"id": key["id"], "n_lessons": 3, "cell": "AUTHOR"}], {"records": [rec]}
    frozen = ns.SC6.score_real(ns, keys, inputs, doc)
    out = SC.score_real(ns, HV, keys, inputs, doc, True, raw_by_id={key["id"]: raw})
    row = (out.get("a11_checks") or [{}])[0]
    return {"key_q": [k["q"] for k in key["lessons"]], "key_heads": [k["head"] for k in key["lessons"]],
            "why_not": key["representable"]["why_not"],
            "lesson_scores": out["per_item"][0].get("lessons") if "lessons" in out["per_item"][0] else None,
            "frozen_strict": frozen["totals"]["unexplained_asks_strict"],
            "strict": out["totals"]["unexplained_asks_strict"],
            "after_a11": out["totals"]["unexplained_asks_strict_after_a11"],
            "exempted": out["a11_exempted_ids"], "checks": {c: row.get(c) for c in "abcde"},
            "allowed_tail_heads": row.get("allowed_tail_heads"), "unlearned": row.get("unlearned")}


def main():
    ns = C.setup(helm=False)
    HV = C.load_helm_voice()
    res = {"pkg": str(PKG)}
    # H-2: lesson 0 ("ran out of tomatoes") misbound to the tail 'lime juice' at the key's amount 1
    raw = ["1 can tomatoes in juice", "1 cup sugar, 1 cup lime juice", "2 cups rice"]
    k = key_of(ns, "FIX:S1", "punch", raw)
    res["H2_S1_misbound_stop_word_line"] = score(ns, HV, k, raw, record(k, "punch", [("lime juice", "1"), ("sugar", "1"),
                                                                                       ("rice", "2")], ["tomatoes in juice"]))
    raw_c = ["1 can tomatoes", "1 cup sugar, 1 cup lime juice", "2 cups rice"]
    kc = key_of(ns, "FIX:S1C", "punch", raw_c)
    res["H2_S1c_control_plain_line"] = score(ns, HV, kc, raw_c, record(kc, "punch", [("lime juice", "1"), ("sugar", "1"),
                                                                                        ("rice", "2")], ["tomato"]))
    # H-4 and H-5 on an honest record (lentils / cloves + juniper berries / stock)
    raw = ["2 cups lentils", "4 cloves, 8 juniper berries", "1 cup stock"]
    k = key_of(ns, "FIX:S2", "soup", raw)
    learned = [("lentil", str(k["lessons"][0]["q"])), ("clove", str(k["lessons"][1]["q"])), ("stock", str(k["lessons"][2]["q"]))]
    res["honest_control"] = score(ns, HV, k, raw, record(k, "soup", learned, ["juniper berry"]))
    res["H4_S3_wrong_unit_on_lesson_0"] = score(ns, HV, k, raw, record(k, "soup", learned, ["juniper berry"],
                                                                        units={0: "teaspoon"}))
    res["H5_S2_person_heard_the_fallback"] = score(ns, HV, k, raw, record(
        k, "soup", learned, ["juniper berry"],
        scored_reply="Could you say that another way? I didn't act on it. Nothing was saved."))
    out = json.dumps(res, indent=1, sort_keys=True, default=str)
    Path(sys.argv[2]).write_text(out + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
