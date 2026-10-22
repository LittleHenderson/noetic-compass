"""Scratch probe (build of reader v7.3): what the given HELM tree does on the T1 sentences (authored only).
usage: python -X utf8 -B -I probe_cases.py <helm tree>"""
import os
import sys

sys.path.insert(0, sys.argv[1])
os.environ["HELM_WIDE_BRAIN"] = "1"
import helm_wide_turn as WT  # noqa: E402
import helm_brain_wide as W  # noqa: E402
import helm_end_to_end_loop as E2E  # noqa: E402

print("READER", WT.READER_VERSION)
for ln in ("1 can tomatoes or", "1 can tomatoes", "2 cups flour", "2 large or 4 small green peppers", "1 cup coffee liquor",
           "1 cup dry beans or whole peas", "1 can tomatoes or;", "2 beef stock cubes", "1 cup tomato paste"):
    print("parse_line", repr(ln), "->", WT.parse_line(ln))
print("parse_line butter+notes or ->", WT.parse_line("1 cup butter", "or"))
print("unit_of cupfuls:", W.unit_of("cupfuls"), "unit_of can:", W.unit_of("can"))
print("K1", WT.resolve_ran_out("tomato", ["tomatoes with juice", "chopped tomato", "onion"],
                               {"tomatoes with juice": "3 cups tomatoes with juice", "chopped tomato": "2 cup chopped tomatoes",
                                "onion": "4 onions"}))
print("K2", WT.resolve_ran_out("sugar", ["sugar beet", "brown sugar"]))
print("K4", WT.resolve_ran_out("sugar", ["sugar", "brown sugar"]), WT.resolve_ran_out("stock", ["stock", "beef stock cube"]))
print("K5", WT.resolve_ran_out("cupfuls of sifted", ["cake flour", "sugar"],
                               {"cake flour": "2 cups sifted cake flour", "sugar": "1 cup sugar"}))
SENT = [
    "We made 1 sauce from 1 can tomatoes or, 8 cups chopped tomatoes and 4 onions and ran out of tomatoes.",
    "We made 1 sauce from 1 can tomatoes or; 8 cups chopped tomatoes and 4 onions and ran out of tomatoes.",
    "We made 1 cake from 2 cups flour, 2 cup butter, or and 2 cup margarine and ran out of flour.",
    "We made 1 sauce from 3 cups tomatoes with juice, 2 can tomatoes or and 4 onions and ran out of tomatoes.",
    "We made 1 sauce from 8 cups chopped tomatoes, 4 onions and 1 can tomatoes or and ran out of tomatoes.",
    "We have 3 can tomatoes or, 6 cups chopped tomatoes and 5 onions.",
    "We made 1 batch from 1 can tomatoes or, 8 cups chopped tomatoes and 4 onions and ran out of tomatoes.",
    "We made 1 sauce from 1 can tomatoes or, 8 cups fresh tomatoes and 4 onions and ran out of tomatoes.",
    "We made 1 sauce from 1 can tomatoes in juice, 4 tomatoes and 4 onions and ran out of tomatoes.",
    "We made 1 cake from 1 cup sugar, 2 cups brown sugar and 4 cups flour and ran out of sugar.",
    "We made 1 soup from 1 cup stock, 2 beef stock cubes and 2 onions and ran out of stock.",
    "We made 1 sauce from 2 tomatoes, 1 cup tomato paste and 2 onions and ran out of tomatoes.",
    "We have 6 cups spelt flour or, 2 cups oat milk.",
]
for s in SENT:
    r = WT.read_wide(s)
    print("read_wide", repr(s))
    print("    ", r["status"], r["clarify"], (r["witness"] or {}).get("ran_out"), sorted((r["witness"] or {}).get("stock") or []),
          r.get("stock"), "pending" in r)


def run(label, turns):
    loop = E2E.HELMEndToEndLoop(wide_brain=True)
    print("LOOP", label)
    for k, s in enumerate(turns, 1):
        res = loop.process_turn(s, tick=k)
        print("    ", k, res.get("loop_status"), res.get("path"), len(res.get("cubes_written") or []), res.get("output_value"),
              "|", res.get("everyday_english_response"))
    print("     recipes:", {p: {n: loop.wide_book.requirement_said(p, n) for n in loop.wide_book.support_of(p)}
                               for p in loop.wide_book.recipes})
    return loop


D1 = ["We made 1 sauce from 1 can tomatoes or, 8 cups chopped tomatoes and 4 onions and ran out of tomatoes.",
      "We made 1 sauce from 2 can tomatoes or, 4 cups chopped tomatoes and 4 onions and ran out of chopped tomatoes.",
      "We made 1 sauce from 2 can tomatoes or, 8 cups chopped tomatoes and 2 onions and ran out of onions.",
      "We have 3 can tomatoes or, 6 cups chopped tomatoes and 5 onions.", "How much sauce can we make?"]
run("D1", D1)
run("D3", [s.replace("chopped", "fresh") for s in D1])
run("A1", ["We made 1 sauce from 3 cups tomatoes with juice, 2 cup chopped tomatoes and 4 onions and ran out of tomatoes.",
           "We made 1 sauce from 6 cups tomatoes with juice, 1 cup chopped tomatoes and 4 onions and ran out of chopped tomatoes.",
           "We made 1 sauce from 6 cups tomatoes with juice, 2 cup chopped tomatoes and 2 onions and ran out of onions.",
           "We have 9 cups tomatoes with juice, 3/2 cup chopped tomatoes and 5 onions.", "How much sauce can we make?"])
run("X1", ["We made 1 sauce from 3 cups tomatoes with juice, 2 can tomatoes or and 4 onions and ran out of tomatoes.",
           "We made 1 sauce from 6 cups tomatoes with juice, 1 can tomatoes or and 4 onions and ran out of tomatoes.",
           "We made 1 sauce from 6 cups tomatoes with juice, 2 can tomatoes or and 2 onions and ran out of onions.",
           "We have 9 cups tomatoes with juice, 3/2 can tomatoes or and 5 onions.", "How much sauce can we make?"])
run("X2", ["We made 1 sauce from 1 can tomatoes in juice, 4 tomatoes and 4 onions and ran out of tomatoes.",
           "We made 1 sauce from 2 can tomatoes in juice, 2 tomatoes and 4 onions and ran out of tomatoes.",
           "We made 1 sauce from 2 can tomatoes in juice, 4 tomatoes and 2 onions and ran out of onions.",
           "We have 3 can tomatoes in juice, 3 tomatoes and 5 onions.", "How much sauce can we make?"])
LESSONS = ["We made 1 oatcake from 2 cups spelt flour, 2 cups oat milk and 6 duck eggs and ran out of spelt flour.",
           "We made 1 oatcake from 4 cups spelt flour, 1 cup oat milk and 6 duck eggs and ran out of oat milk.",
           "We made 1 oatcake from 4 cups spelt flour, 2 cups oat milk and 3 duck eggs and ran out of duck eggs."]
loop = run("J8", LESSONS + ["We have 6 cups spelt flour, 2 cups oat milk and 9 duck eggs.",
                            "We have 6 cups spelt flour or, 2 cups oat milk.", "How much oatcake can we make?"])
print("     wide stock after:", getattr(loop, "wide_stock", None))
