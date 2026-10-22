"""CRITIC PROBE (scratch only, authored items only). For each authored recipe: the frozen key (rbw1t key_item ->
xreal key_r) + A-R1W7-7's tag, the exam's own turns (exam_rbw1t.turns_for), HELM's loop driven directly (v7.2 from a
scratch copy of the v9 helm_now, then the design's own R1/R2 probe patch), a chat-shaped record, the frozen
score_lessons / score_question / unexplained_ask, and the design's A-R1W7-11 conditions (a)-(d).
usage: python -X utf8 -B -I critic_probe.py <critic pkgs dir> <design probe dir>"""
import json
import os
import re
import sys
from fractions import Fraction

pk, probe = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(pk, "HELM_RBW1T_20261019"))
sys.path.insert(0, os.path.join(pk, "r1w7c"))
sys.path.insert(0, os.path.join(pk, "helm_now_v72"))
sys.path.insert(0, probe)
os.environ["HELM_WIDE_BRAIN"] = "1"
from rbw1t import common_rbw1t as RC  # noqa: E402
RC.vendor_path()
from rbw1t import keys_rbw1t as K  # noqa: E402
from rbw1t import exam_rbw1t as EX  # noqa: E402
from xreal import grammar as G  # noqa: E402
import multi_qty_w7 as MQ  # noqa: E402
import helm_wide_turn as WT  # noqa: E402
import helm_end_to_end_loop as E2E  # noqa: E402
import helm_brain_wide as W  # noqa: E402
import v73_patch  # noqa: E402

ITEMS = {
    # (1) R1 regression shape: v7.2 refuses lesson 0 (two own-word hits); v7.3's cut name makes an exact wrong hit
    "X1": ("sauce", ["3 cups tomatoes with juice", "1 can tomatoes or", "2 onions"]),
    # (1)/(4) exact-path misbinding R1/R2 never touch: the true line's HELM name has words after the head
    "X2": ("sauce", ["1 can tomatoes in juice", "2 tomatoes", "2 onions"]),
    # (2) phantom ingredient from the tagged line itself (a note read as an ingredient)
    "C1": ("bread", ["3 eggs, 1 beaten", "2 cups flour", "1 cup milk"]),
    "C2": ("cake", ["1 cup sugar, 2 tablespoons reserved", "2 cups flour", "1 cup milk"]),
    # (2) tagged line read as ONE ingredient by HELM; the phantom comes from an UNTAGGED line
    "C3": ("pie", ["2 cups flour, plus 2 tablespoons", "1 pound beef, a lean cut", "1 cup broth"]),
    # (2) misbound ran-out that the frozen score_lessons still calls LEARNED (value coincidence, unit never read)
    "C4": ("salsa", ["1 onion, 2 tomatoes", "1 cup rice", "2 cups tomatoes with juice"]),
    # the design's own honest case, for comparison
    "M1": ("stew", ["2 cups barley", "5 cloves, 10 juniper berries", "1 cup broth"]),
}
MULTS = [Fraction(3), Fraction(3, 2), Fraction(5, 2)]
TAG_RX = re.compile(r"^line(\d+):MULTI_QTY$")


def ftext(v):
    v = Fraction(v)
    return str(v.numerator) if v.denominator == 1 else f"{v.numerator}/{v.denominator}"


def lesson_record(res, loop):
    rr = res.get("recipe_receipt") or {}
    rr = rr if isinstance(rr, dict) else {}
    status = res.get("loop_status")
    on_wide = res.get("path") == "wide"
    ing = rr.get("ingredient") if on_wide else rr.get("ran_out")
    if isinstance(ing, list):
        ing = ing[0] if len(ing) == 1 else None
    admitted = status in ("WITNESS_ADMITTED",) and bool(rr.get("admitted"))
    return {"status": status, "admitted": admitted, "ingredient": ing if admitted else None,
            "product": rr.get("product") if admitted else None, "path": res.get("path")}


def run_item(tag, noun, raw):
    r = {"noun": noun, "lines": [{"raw": x, "parsed": G.parse_line(x)} for x in raw]}
    t = EX.turns_for(r, MULTS[:len(raw)])
    key = MQ.apply(K.key_item({"id": "AUTHOR:" + tag, "raw_lines": raw, "pantry_lines": t["pantry_lines"]}), raw, G)
    loop = E2E.HELMEndToEndLoop(wide_brain=True)
    log, sents = [], []
    for k, s in enumerate(t["turns"], 1):
        res = loop.process_turn(s, tick=k)
        log.append((res, lesson_record(res, loop)))
        sents.append(res.get("everyday_english_response"))
    book = loop.wide_book
    n = t["n_lessons"]
    lessons = []
    for res, rec in log[:n]:
        rec = dict(rec)
        rec["learned_in_taught_unit"] = None
        if rec["admitted"] and rec["path"] == "wide":
            a = book.coefficient(rec["product"], rec["ingredient"])
            if a is not None:
                tu = book.recipes[W.norm_name(rec["product"])]["taught_unit"][W.norm_name(rec["ingredient"])]
                rec["learned_in_taught_unit"] = ftext(W.from_base(a, tu))
        lessons.append(rec)
    qres = log[-1][0]
    stock_status = log[n][0].get("loop_status")
    qs = K.score_question(key, qres.get("loop_status"), qres.get("output_value"), qres.get("limiting_reagent"), lessons)
    ls = K.score_lessons(key, lessons)
    unexpl = K.unexplained_ask(key, ls, stock_status, qs)
    slots = sum(len(rr["support"]) for rr in book.recipes.values())
    coefs = sum(1 for rr in book.recipes.values() for nm in rr["support"] if rr["a"][nm] is not None)
    tagged = [int(TAG_RX.match(w).group(1)) for w in key["representable"]["why_not"] if TAG_RX.match(w)]
    a = key["answer"]["key"] == "ANSWER" and bool(tagged)
    b = unexpl
    c = qres.get("loop_status") == "UNDETERMINED_CLARIFY" and qres.get("path") == "wide"
    prods = {x.get("product") for x in lessons}
    d = (len(book.recipes) >= 1 and len(prods) == 1 and None not in prods and coefs == len(key["lessons"])
         and slots > len(key["lessons"]))
    print("=====", tag, raw)
    print("  key:", key["answer"]["key"], key["answer"].get("yield"), "heads",
          [x["head"] for x in key["lessons"]], "q", [x["q"] for x in key["lessons"]], "why_not",
          key["representable"]["why_not"])
    for j, (res, rec) in enumerate(log[:n]):
        rd = (res.get("english_in") or {}).get("witness") or {}
        print(f"  lesson {j}: {t['turns'][j]}")
        print(f"     -> {rec['status']} ingredient={rec['ingredient']} learned={lessons[j]['learned_in_taught_unit']} "
              f"score={ls[j]} | read names={list((rd.get('stock') or {}).keys())} ran_out={rd.get('ran_out')}")
    print("  stock:", stock_status, "| question:", qres.get("loop_status"), qres.get("path"), qres.get("output_value"),
          "| q score:", qs, "| unexplained:", unexpl)
    print("  book: recipes", len(book.recipes), "support_slots", slots, "coefficients", coefs,
          "support", {p: book.support_of(p) for p in book.recipes})
    print("  question sentence:", sents[-1])
    print(f"  A-R1W7-11: a={a} b={b} c={c} d={d} -> EXEMPT={a and b and c and d}")


def run(label):
    print("##########", label, WT.READER_VERSION)
    for tag, (noun, raw) in ITEMS.items():
        try:
            run_item(tag, noun, raw)
        except Exception as exc:  # recorded, never hidden
            print("=====", tag, "PROBE ERROR", type(exc).__name__, exc)


run("v7.2 (scratch copy of the v9 helm_now)")
v73_patch.install(WT)
run("v7.3 as the design's own probe patch (R1 + R2)")
