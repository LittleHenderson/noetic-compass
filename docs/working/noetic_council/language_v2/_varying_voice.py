"""_varying_voice.py -- the owner's ruling: the canonical word is the INSIDE, the English
outside it is allowed to vary. This shows the varying speaker that already exists (`say`),
how many distinct sentences each content has, and that every one draws safe.

Nothing here is new machinery. It is the proof that `say()` was built and never called:
every demo until now used the fixed-twin renderer, so every demo showed the same sentence.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import cce_render
import roundtrip
from content import CASContent, Recipe, RecipeTerm, State, Term

CASES = [
    ("attraction", CASContent(terms=(Term(2, slots={"M": "I", "I": '"the offer"'}),))),
    ("aversion", CASContent(terms=(Term(3, slots={"M": "I", "I": '"the offer"'}),))),
    ("stored thought",
     CASContent(terms=(Term(1, slots={"M": "I",
                                      "I": CASContent(terms=(Term(2, slots={"M": "Ana", "I": '"the offer"'}),)),
                                      "ACT": "stores"}),),
                relations=(("is_a", "Ana", "Mind"),))),
    ("resonance with a degree",
     CASContent(terms=(Term(4, slots={"M": "I", "I": '"the offer"', "D": "7"}),))),
    ("recipe",
     CASContent(recipe=Recipe(omega="\u03a9_bread",
         terms=(RecipeTerm("1/3", kind="state", state=State(5, domain="C")),
                RecipeTerm("2", kind="state", state=State(7, domain="O", register=("A",), drive="F6")),
                RecipeTerm("3/7", kind="outcome", name="\u03a9_starter"))))),
]

SEEDS = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11)

total_drawn = total_said = 0
all_safe = True

for kind, content in CASES:
    print("=" * 100)
    print("CONTENT: %s   fingerprint %s" % (kind, content.digest()))
    print("=" * 100)

    table = cce_render.wordings(content)
    print("wordings enumerated (cap %d): %d" % (cce_render.MAX_WORDINGS, len(table)))

    said = []
    for seed in SEEDS:
        try:
            drew = roundtrip.say(content, seed)
        except Exception as exc:
            print("  seed %2d  REFUSED  %s: %s" % (seed, type(exc).__name__, exc))
            all_safe = False
            continue
        ok = drew["receipt"].ok
        all_safe = all_safe and ok
        total_drawn += 1 if drew["drawn"] else 0
        total_said += 1
        said.append(drew["sentence"])
        print("  seed %2d  %-4s  %s" % (seed, "OK" if ok else "BAD", drew["sentence"]))

    print("\n  distinct sentences drawn from %d seeds: %d" % (len(SEEDS), len(set(said))))
    print()

print("=" * 100)
print("every drawn sentence read back to the identical content: %s" % ("YES" if all_safe else "NO"))
print("seeds drawn freely (not fallen back to the fixed twin): %d of %d" % (total_drawn, total_said))
print("=" * 100)
