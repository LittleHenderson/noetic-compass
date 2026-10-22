"""Scratch probe (build of reader v7.3; feasibility, not a result): the design's 13 authored items (section 1 table)
rendered by the frozen exam template (code only) and driven through the given HELM tree's loop; prints each turn's
status and what the wide book learned, so the built reader can be compared with the design's v7.3 column.
usage: python -X utf8 -B -I probe_items_loop.py <helm tree> <deps dir>"""
import os
import sys
from fractions import Fraction

helm, deps = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(deps, "HELM_RBW1T_20261019"))
from rbw1t import common_rbw1t as RC  # noqa: E402
RC.vendor_path()
from rbw1t import exam_rbw1t as EX  # noqa: E402
from xreal import grammar as G  # noqa: E402
sys.path.insert(0, helm)
os.environ["HELM_WIDE_BRAIN"] = "1"
import helm_wide_turn as WT  # noqa: E402
import helm_end_to_end_loop as E2E  # noqa: E402

ITEMS = {
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
print("READER", WT.READER_VERSION)
for tag, (noun, raw) in ITEMS.items():
    r = {"noun": noun, "lines": [{"raw": x, "parsed": G.parse_line(x)} for x in raw]}
    t = EX.turns_for(r, MULTS[:len(raw)])
    loop = E2E.HELMEndToEndLoop(wide_brain=True)
    res = [loop.process_turn(s, tick=k) for k, s in enumerate(t["turns"], 1)]
    book = loop.wide_book
    learned = {p: {n: book.requirement_said(p, n) for n in book.support_of(p)} for p in book.recipes}
    print(f"{tag}: " + " | ".join(f"{x.get('loop_status')}/{x.get('path')}" for x in res), "| learned", learned,
          "| q value", res[-1].get("output_value"))
