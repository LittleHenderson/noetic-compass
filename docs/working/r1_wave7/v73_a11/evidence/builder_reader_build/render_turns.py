"""Scratch helper (build of reader v7.3, T1): render the AUTHOR'S OWN recipes through the frozen exam template
(rbw1t.exam_rbw1t.turns_for, code only) so the T1 tests can carry the exact sentence shape of F3. No exam data is read.
usage: python -X utf8 -B -I render_turns.py <deps dir>"""
import os
import sys
from fractions import Fraction

deps = sys.argv[1]
sys.path.insert(0, os.path.join(deps, "HELM_RBW1T_20261019"))
from rbw1t import common_rbw1t as RC  # noqa: E402
RC.vendor_path()
from rbw1t import exam_rbw1t as EX  # noqa: E402
from xreal import grammar as G  # noqa: E402

ITEMS = {
    "D1": ("sauce", ["1 can tomatoes or", "4 cups chopped tomatoes", "2 onions"]),
    "D3": ("sauce", ["1 can tomatoes or", "4 cups fresh tomatoes", "2 onions"]),
    "D4": ("cake", ["2 cups flour", "1 cup butter, or", "1 cup margarine"]),
    "A1": ("sauce", ["3 cups tomatoes with juice", "1 cup chopped tomatoes", "2 onions"]),
    "X1": ("sauce", ["3 cups tomatoes with juice", "1 can tomatoes or", "2 onions"]),
    "X2": ("sauce", ["1 can tomatoes in juice", "2 tomatoes", "2 onions"]),
}
MULTS = [Fraction(3), Fraction(3, 2), Fraction(5, 2)]
for tag, (noun, raw) in ITEMS.items():
    r = {"noun": noun, "lines": [{"raw": x, "parsed": G.parse_line(x)} for x in raw]}
    t = EX.turns_for(r, MULTS[:len(raw)])
    print("=====", tag, raw, "names", t["lesson_names"])
    for s in t["turns"]:
        print("   ", repr(s))
