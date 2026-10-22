"""FINALIZE PROBE (scratch only, authored items only; feasibility, not a result). For each authored recipe: the frozen
key (rbw1t key_item -> xreal key_r) + A-R1W7-7's tag, the exam's own turns (exam_rbw1t.turns_for), HELM's loop driven
directly (v7.2 = scratch copy of the v9 helm_now; then the FINAL v7.3 rules as in-process replacements), a chat-shaped
host record (turns[kind=turn].loop.loop_sentence, log, lesson_records, scored_turn, wide_audit = frozen audit_brain),
the frozen score_lessons / score_question / unexplained_ask through the frozen wave-6 real_record_view, and the FINAL
A-R1W7-11 honesty test prototype. Then crash / ALWAYS_ASK / LOOP_ON-shaped records through the same test.
usage: python -X utf8 -B -I final_probe.py <helm_now copy> <deps dir> <multi_qty dir> <scripts dir>"""
import copy
import os
import sys
from fractions import Fraction

helm, deps, mqdir, scripts = sys.argv[1:5]
sys.path.insert(0, os.path.join(deps, "HELM_RBW1T_20261019"))
sys.path.insert(0, os.path.join(deps, "HELM_R1_W6_20261019"))
sys.path.insert(0, mqdir)
sys.path.insert(0, helm)
sys.path.insert(0, scripts)
os.environ["HELM_WIDE_BRAIN"] = "1"
from rbw1t import common_rbw1t as RC  # noqa: E402
RC.vendor_path()
from rbw1t import keys_rbw1t as K  # noqa: E402
from rbw1t import exam_rbw1t as EX  # noqa: E402
from rbw1t import arms_rbw1t as RA  # noqa: E402
from xreal import grammar as G  # noqa: E402
from r1w6 import score_w6 as SC6  # noqa: E402
import multi_qty_w7 as MQ  # noqa: E402
import helm_wide_turn as WT  # noqa: E402
import helm_end_to_end_loop as E2E  # noqa: E402
import helm_brain_wide as W  # noqa: E402
import final_patch  # noqa: E402
import honest_check_proto as HA  # noqa: E402

ITEMS = {
    "M2": ("stew", ["2 cups barley", "6 cloves, 12 peppercorns and 2 allspice berries", "1 cup broth"]),
}
_UNUSED = {
    "D1": ("sauce", ["1 can tomatoes or", "4 cups chopped tomatoes", "2 onions"]),
    "D2": ("cake", ["1 cup butter or", "1 cup margarine", "2 cups flour"]),
    "D3": ("sauce", ["1 can tomatoes or", "4 cups fresh tomatoes", "2 onions"]),
    "D4": ("cake", ["2 cups flour", "1 cup butter, or", "1 cup margarine"]),
    "A1": ("sauce", ["3 cups tomatoes with juice", "1 cup chopped tomatoes", "2 onions"]),
    "X1": ("sauce", ["3 cups tomatoes with juice", "1 can tomatoes or", "2 onions"]),
    "X2": ("sauce", ["1 can tomatoes in juice", "2 tomatoes", "2 onions"]),
    "C1": ("bread", ["3 eggs, 1 beaten", "2 cups flour", "1 cup milk"]),
    "C2": ("cake", ["1 cup sugar, 2 tablespoons reserved", "2 cups flour", "1 cup milk"]),
    "C3": ("pie", ["2 cups flour, plus 2 tablespoons", "1 pound beef, a lean cut", "1 cup broth"]),
    "C4": ("salsa", ["1 onion, 2 tomatoes", "1 cup rice", "2 cups tomatoes with juice"]),
    "M1": ("stew", ["2 cups barley", "5 cloves, 10 juniper berries", "1 cup broth"]),
    "P1": ("pilaf", ["2 cups rice", "6 cloves and 12 peppercorns", "1 cup stock"]),
}
MULTS = [Fraction(3), Fraction(3, 2), Fraction(5, 2)]


def ftext(v):
    v = Fraction(v)
    return str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"


def chat_record(item_id, n, results, loop):
    """The chat record's fields A-R1W7-11 reads, built exactly as chat_harness.Dialogue.record builds them."""
    turns, log, lessons = [], [], []
    for res in results:
        lv = {"status": res.get("loop_status"), "value": res.get("output_value"), "limiting": res.get("limiting_reagent"),
              "path": res.get("path"), "loop_sentence": res.get("everyday_english_response")}
        turns.append({"kind": "turn", "loop": lv})
        log.append(H6_log_entry(res, loop))
    book = loop.wide_book
    for e in log:
        rec = {"status": e["status"], "admitted": e["admitted"], "ingredient": e["ingredient"], "product": e["product"],
               "reason": e["reason"], "path": e["path"] or "licensed", "learned_in_taught_unit": None}
        if e["admitted"] and e["path"] == "wide":
            a = book.coefficient(e["product"], e["ingredient"])
            if a is not None:
                tu = book.recipes[W.norm_name(e["product"])]["taught_unit"][W.norm_name(e["ingredient"])]
                rec["learned_in_taught_unit"] = ftext(W.from_base(a, tu))
        lessons.append(rec)
    lv = turns[-1]["loop"]
    return {"id": item_id, "n_lessons": n, "turns": turns, "log": log, "lesson_records": lessons,
            "scored_turn": {"status": lv["status"], "value": lv["value"], "limiting": lv["limiting"], "writes": 0,
                            "inner_status": lv["status"], "routed": True},
            "wide_audit": [RA.audit_brain(book, W)]}


def H6_log_entry(res, loop):
    rr = res.get("recipe_receipt") or {}
    rr = rr if isinstance(rr, dict) else {}
    status = res.get("loop_status")
    ing = rr.get("ingredient") if res.get("path") == "wide" else rr.get("ran_out")
    if isinstance(ing, list):
        ing = ing[0] if len(ing) == 1 else None
    admitted = status in ("WITNESS_ADMITTED",) and bool(rr.get("admitted"))
    return {"kind": "turn", "status": status, "path": res.get("path"), "admitted": admitted,
            "ingredient": ing if admitted else None, "product": rr.get("product") if admitted else None,
            "reason": rr.get("reason")}


def run_item(tag, noun, raw, saved):
    r = {"noun": noun, "lines": [{"raw": x, "parsed": G.parse_line(x)} for x in raw]}
    t = EX.turns_for(r, MULTS[:len(raw)])
    key = MQ.apply(K.key_item({"id": "AUTHOR:" + tag, "raw_lines": raw, "pantry_lines": t["pantry_lines"]}), raw, G)
    loop = E2E.HELMEndToEndLoop(wide_brain=True)
    results = [loop.process_turn(s, tick=k) for k, s in enumerate(t["turns"], 1)]
    n = t["n_lessons"]
    rec = chat_record("AUTHOR:" + tag, n, results, loop)
    v = SC6.real_record_view(rec, n)
    q = v["question"]
    qs = K.score_question(key, q.get("status"), q.get("value"), q.get("limiting"), v["lessons"])
    ls = K.score_lessons(key, v["lessons"])
    unexpl = K.unexplained_ask(key, ls, v["stock_status"], qs)
    ha = HA.honest_ask(K, SC6.real_record_view, G, MQ, RC, key, rec, n, raw)
    saved[tag] = (key, rec, n, raw)
    print("=====", tag, raw)
    print("  key:", key["answer"]["key"], key["answer"].get("yield"), "q", [x["q"] for x in key["lessons"]],
          "why_not", key["representable"]["why_not"])
    for j in range(n):
        print(f"  lesson {j}: {rec['log'][j]['status']} ingredient={rec['lesson_records'][j]['ingredient']} "
              f"learned={rec['lesson_records'][j]['learned_in_taught_unit']} -> {ls[j]}")
    print("  stock:", v["stock_status"], "| question:", q.get("status"), rec["log"][-1]["path"], q.get("value"),
          "| q score:", qs, "| unexplained (frozen):", unexpl)
    print("  lesson-0 sentence:", rec["turns"][0]["loop"]["loop_sentence"])
    print("  question sentence:", rec["turns"][-1]["loop"]["loop_sentence"])
    print("  A-R1W7-11 final:", {k: ha[k] for k in ("a", "b", "c", "d", "e", "exempt", "unlearned", "allowed_tail_heads")},
          ("error=" + ha["error"]) if "error" in ha else "")


def run(label):
    print("##########", label)
    saved = {}
    for tag, (noun, raw) in ITEMS.items():
        try:
            run_item(tag, noun, raw, saved)
        except Exception as exc:          # recorded, never hidden
            print("=====", tag, "PROBE ERROR", type(exc).__name__, exc)
    return saved


pass
final_patch.install(WT)
saved = run("v7.3 FINAL rules (R1 + R1a + R2 + R2g) as in-process replacements")

