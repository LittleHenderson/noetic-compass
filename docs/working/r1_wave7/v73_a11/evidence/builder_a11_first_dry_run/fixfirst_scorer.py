"""fixfirst_scorer.py <pkg_root> <out_json> -- FIX FIRST at the scorer level, on ONE package copy (unamended v9 or amended):
the copy's own score_w7.score_real on authored keys (frozen key_item + A-R1W7-7 apply; the author's own recipes M1, P1)
and authored chat-shaped host records, then the copy's own merge_r1w7.marks() on a stub run that serves only those
totals (K4 and K3 depend on the X7_REAL CHAT_ON totals alone; CONV / NOISE totals are served as all right). Run A: the
honest tagged asks M1 + P1. Run B: the honest M1 ask + a WRONG number on the same tagged key. Scratch evidence only."""
import copy
import json
import sys
from fractions import Fraction
from pathlib import Path

PKG = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(PKG))
from r1w7 import common_w7 as C           # noqa: E402
from r1w7 import merge_r1w7 as M          # noqa: E402
from r1w7 import multi_qty_w7 as MQ       # noqa: E402
from r1w7 import score_w7 as SC           # noqa: E402

AMENDED = (PKG / "r1w7" / "honest_ask_w7.py").is_file()
MULTS = (Fraction(3), Fraction(3, 2), Fraction(5, 2))
ITEMS = {"M1": ("stew", ["2 cups barley", "5 cloves, 10 juniper berries", "1 cup broth"], ["barley", "clove", "broth"],
                ["juniper berry"]),
         "P1": ("pilaf", ["2 cups rice", "6 cloves and 12 peppercorns", "1 cup stock"], ["rice", "clove", "stock"],
                ["peppercorn"])}


def key_of(ns, name, iid):
    dish, raw, _n, _u = ITEMS[name]
    r = {"noun": dish, "lines": [{"raw": x, "parsed": ns.XG.parse_line(x)} for x in raw]}
    t = ns.rb.exam_rbw1t.turns_for(r, MULTS)
    return MQ.apply(ns.rb.keys_rbw1t.key_item({"id": iid, "raw_lines": raw, "pantry_lines": t["pantry_lines"]}), raw, ns.XG)


def rec_of(key, name, status="UNDETERMINED_CLARIFY", value=None, limiting=None):
    dish, _raw, names, unl = ITEMS[name]
    sentence = (f"I can't say yet how much {dish} we can make. I still need one batch where {unl[0]} ran out first "
                f"while everything else was left over. I didn't guess.")
    turns, log, lrs = [], [], []

    def add(st, path, sent, admitted=False, ing=None, q=None, val=None, lim=None):
        w = 1 if admitted or st in ("STOCK_RECORDED", "SUCCESS_EVALUATED") else 0
        turns.append({"kind": "turn", "intent": "RECIPE_FOUNDATION_LOOP", "reply": sent,
                      "loop": {"status": st, "value": val, "limiting": lim, "writes": w, "path": path, "loop_sentence": sent}})
        e = {"kind": "turn", "status": st, "path": path, "admitted": admitted, "ingredient": ing,
             "product": dish if admitted else None, "reason": "ADMITTED" if admitted else None, "value": val, "limiting": lim}
        log.append(e)
        lrs.append({"status": st, "admitted": admitted, "ingredient": ing, "product": e["product"], "path": path,
                    "learned_in_taught_unit": q})

    for nm, kl in zip(names, key["lessons"]):
        add("WITNESS_ADMITTED", "wide", "Got it.", True, nm, kl["q"])
    for lr in lrs:
        lr["product"] = dish
    add("STOCK_RECORDED", "wide", "Noted.")
    add(status, "wide", sentence, val=value, lim=limiting)
    return {"id": key["id"], "turns": turns, "log": log, "lesson_records": lrs,
            "scored_turn": {"status": status, "value": value, "limiting": limiting, "writes": 0, "inner_status": status,
                            "routed": True},
            "scored_reply": sentence, "plain": True,
            "wide_audit": [{"ok": True, "coefficients": 3, "support_slots": 4}]}


class StubRun:
    def __init__(self, real):
        self.real, self.sample_real_sha256 = real, None

    def get(self, exam, arm):
        return {"real": self.real} if exam == "X7_REAL" else {}

    def per(self, exam, arm):
        return self.real["per_item"] if exam == "X7_REAL" else []

    def totals(self, exam, arm):
        return self.real["totals"] if exam == "X7_REAL" else {"WRONG": 0, "RIGHT": 0, "RIGHT_AND_PLAIN": 0,
                                                               "misrouted_scored_turns": 0}


def run(ns, HV, pairs):
    keys, inputs, recs, raw = [], [], [], {}
    for iid, name, kw in pairs:
        k = key_of(ns, name, iid)
        keys.append(k)
        inputs.append({"id": iid, "n_lessons": 3, "cell": "AUTHOR"})
        recs.append(rec_of(k, name, **kw))
        raw[iid] = list(ITEMS[name][1])
    doc = {"records": recs}
    out = SC.score_real(ns, HV, keys, inputs, doc, True, raw_by_id=raw) if AMENDED else \
        SC.score_real(ns, HV, keys, inputs, doc, True)
    mk = M.marks(StubRun(out))
    t = out["totals"]
    return {"keys_why_not": {k["id"]: k["representable"]["why_not"] for k in keys},
            "q": {p["id"]: p["q"] for p in out["per_item"]},
            "totals": {x: t.get(x, "(absent)") for x in ("RIGHT", "WRONG", "ASKS", "lessons_WRONG", "unexplained_asks_strict",
                                                        "a11_strict_recount", "unexplained_asks_strict_after_a11",
                                                        "a11_consistent")},
            "a11_exempted_ids": out.get("a11_exempted_ids", "(absent)"),
            "K4_HONEST_value": mk["K4_HONEST"]["value"], "K3_SAFE_value": mk["K3_SAFE"]["value"]}


def main() -> int:
    ns = C.setup(helm=False)
    HV = C.load_helm_voice()
    res = {"pkg": str(PKG), "amended": AMENDED, "reader": M.READER,
           "run_A_honest_tagged_asks_M1_P1": run(ns, HV, [("AUTHOR:M1", "M1", {}), ("AUTHOR:P1", "P1", {})]),
           "run_B_honest_M1_plus_wrong_number_on_tagged_M1": run(ns, HV, [
               ("AUTHOR:M1", "M1", {}),
               ("AUTHOR:M1_WRONG", "M1", {"status": "SUCCESS_EVALUATED", "value": "1/2", "limiting": "clove"})])}
    print(json.dumps(res, indent=1, sort_keys=True))
    Path(sys.argv[2]).write_text(json.dumps(res, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
