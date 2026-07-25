r"""
For each of the 40 TKS cells, measure how much of its OWN definition vocabulary
appears anywhere in the material a held-out-cell experiment would still show:
its World's definition, its Noetic's definition, and the other three cells in
the same Noetic row.

A cell with near-zero leakage is one where a bag-of-words baseline CANNOT win,
because the giveaway words live only in the definition no arm ever sees. Those
are the cells to hold out.
"""
import io, re, sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SRC = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\book\superiority_of_tks\MANUSCRIPT.md")
lines = SRC.read_text(encoding="utf-8", errors="replace").splitlines()

P1 = re.compile(r"^\s*(?P<name>[A-Za-z/ ]+?)\s*\((?P<w>[ABCD])(?P<n>\d{1,2})\)\s*:\s*(?P<d>.+)$")
P2 = re.compile(r"^\s*(?P<w>[ABCD])(?P<n>\d{1,2})\s*\((?P<name>[A-Za-z/ ]+)\)\s*:\s*(?P<d>.+)$")

cells = {}
for ln in lines:
    m = P2.match(ln) or P1.match(ln)
    if not m:
        continue
    k = f"{m.group('w')}{m.group('n')}"
    d = m.group("d").strip()
    if k not in cells or len(d) > len(cells[k][1]):
        cells[k] = (m.group("name").strip(), d)

STOP = set("""the a an and or of to in is are be that this it its for with as on at by
from not no was were which what when where who how you your our their they them we us i
one two both all any each other others than then so such into out up down over under
more most less least very much many some few own same s t don just now also can may
will would could should must if but because while during before after above below
between through against about across
""".split())


def toks(s):
    return {w for w in re.findall(r"[a-z]+", s.lower()) if len(w) > 3 and w not in STOP}


rows = []
for w in "ABCD":
    for n in list(range(1, 10)) + [10]:
        k = f"{w}{n}"
        if k not in cells:
            continue
        own = toks(cells[k][1])
        if not own:
            continue
        # everything an arm would still see with this cell held out:
        siblings = " ".join(cells[f"{o}{n}"][1] for o in "ABCD"
                            if o != w and f"{o}{n}" in cells)
        same_world = " ".join(cells[f"{w}{m2}"][1] for m2 in list(range(1, 10)) + [10]
                              if m2 != n and f"{w}{m2}" in cells)
        visible = toks(siblings) | toks(same_world)
        leaked = own & visible
        pct = 100 * len(leaked) / len(own)
        rows.append((pct, k, cells[k][0], len(own), len(leaked),
                     sorted(own - visible)[:6]))

rows.sort()
print(f"{'cell':5s} {'name':20s} {'leak%':>6s} {'uniq':>5s}  words found ONLY in the held-out definition")
print("-" * 108)
for pct, k, name, n_own, n_leak, uniq in rows:
    print(f"{k:5s} {name:20s} {pct:5.1f}% {n_own - n_leak:5d}  {', '.join(uniq)}")

print("\n\nBEST HELD-OUT CANDIDATES (lowest vocabulary leakage = baseline at chance):")
for pct, k, name, n_own, n_leak, uniq in rows[:6]:
    print(f"  {k} ({name}) — {pct:.1f}% of its vocabulary appears elsewhere")
