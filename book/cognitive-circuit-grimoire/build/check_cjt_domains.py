"""Verify every CJT in the book obeys bias-domain coherence.

Chapter 3.2: the bias must sit AT OR ABOVE the cause in the domain order
P > C > E > O. A bias below its own cause is `E-CJT-008 CjtCrossDomainBias` --
the same error code the compiler raises for prompt injection, because it is the
same thing: influence arriving from below.

Two things this checker has to get right, both learned by getting them wrong:

1. The cause may carry its own Register (`^8^P_{F7}|T`), so splitting the CJT
   on the FIRST "|" reads the register letter as the bias. Split on " | " with
   surrounding spaces, which is the terminal separator.

2. The book shows illegal forms ON PURPOSE -- Chapter 3 demonstrates refused
   listings, and the exercises ask the reader to reject them. The sentence that
   marks a block as a counter-example usually sits OUTSIDE the fence, so each
   block is examined together with the text introducing it.
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

RANK = {"P": 0, "C": 1, "E": 2, "O": 3}          # lower rank == higher domain
MS = Path(__file__).resolve().parent.parent / "manuscript"

# NOTE: "DO NOT BUILD" is deliberately NOT in this pattern. That banner marks a
# board as ethically off-limits to operate, not as syntactically invalid, and it
# sits on the MAIN schematic of every coercive chapter -- exactly the listings
# whose domain coherence matters most. Including it here skipped nine blocks and
# dropped coverage from 37 CJTs to 13 before anyone noticed.
COUNTEREXAMPLE = re.compile(
    r"REFUSED|INVALID|E-CJT-008|reject the listing|fails validation|"
    r"structurally wrong", re.I)

FENCE = re.compile(r"```cas\n(.*?)```", re.S)
NODE = re.compile(r"node\s+(\w+)\s*:\s*\^[0-9][A-Za-z_]*\^([PCEO])")
CJT = re.compile(r"CJT<\s*(.+?)\s*=>\s*(.+?)\s*>")
LITERAL = re.compile(r"\^[0-9][A-Za-z_]*\^([PCEO])")

# Deliberate and documented. CCB-O's cascade turns illegal at A4 and A5 -- that
# degradation IS the detection criterion, and ch15 carries a Bench Note with the
# per-stage verdict table saying so. Named explicitly rather than filtered by
# pattern, so a suppressed finding stays visible in this file.
ALLOWED = {
    ("ch15_ccb_o_overton.md", "reasoned", "peer_majority"),
    ("ch15_ccb_o_overton.md", "preferred", "institutional"),
}


def main() -> int:
    bad: list[str] = []
    checked = files = skipped = 0

    for path in sorted(MS.glob("ch*.md")):
        text = path.read_text(encoding="utf-8")
        blocks = [(m.group(1), text[max(0, m.start() - 300):m.start()])
                  for m in FENCE.finditer(text)]
        if not blocks:
            continue
        files += 1

        for blk, preamble in blocks:
            if COUNTEREXAMPLE.search(blk + preamble):
                skipped += 1
                continue
            nodes = dict(NODE.findall(blk))

            def domain(tok: str) -> str | None:
                m = LITERAL.search(tok)
                return m.group(1) if m else nodes.get(tok.strip())

            for m in CJT.finditer(blk):
                parts = re.split(r"\s\|\s", m.group(1))
                if len(parts) < 2:
                    continue
                cause, bias = parts[0].strip(), parts[-1].strip()
                dc, db = domain(cause), domain(bias)
                if not dc or not db:
                    continue
                checked += 1
                if RANK[db] > RANK[dc]:
                    if (path.name, cause, bias) in ALLOWED:
                        continue
                    bad.append(f"{path.name}: bias ^{db} BELOW cause ^{dc}"
                               f"  --  CJT< {cause} | {bias} => ... >")

    print(f"  files with CCDL                : {files}")
    print(f"  CJTs resolved and checked      : {checked}")
    print(f"  counter-example blocks skipped : {skipped}")
    print(f"  documented exceptions          : {len(ALLOWED)} (CCB-O A4/A5)")
    print(f"  VIOLATIONS                     : {len(bad)}")
    for b in bad:
        print(f"     {b}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
