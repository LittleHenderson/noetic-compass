#!/usr/bin/env python3
"""Negative control for the card deck's compile-time badge guard.

`\\Badge` must reject anything that is not exactly ISO, ENG or PED -- the deck
allows one mapping class per card, and a hybrid label such as "ISO / ENG"
would quietly claim two. The earlier guard used \\ifcsname, which also accepts
`Node` (because \\BadgeNode exists), so this compiles a card with each bad
label and requires a LaTeX error.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent
WORK = BUILD / "plates_negative"
CARDS = BUILD / "companion_cards.tex"

BAD = ["ISO / ENG", "ENG/PED", "Node", "ISO after threshold"]

PROBE = r"""\documentclass[11pt]{article}
\input{%s}
\begin{document}
\Badge{%s}
\end{document}
"""


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    failures = []
    for label in BAD:
        tex = WORK / "badge_probe.tex"
        tex.write_text(PROBE % (CARDS, label), encoding="utf-8")
        done = subprocess.run(
            ["xelatex", "-halt-on-error", "-interaction=nonstopmode",
             f"-output-directory={WORK}", str(tex)],
            cwd=BUILD, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace")
        rejected = done.returncode != 0
        print(f"{'rejected' if rejected else 'ACCEPTED'}  \\Badge{{{label}}}")
        if not rejected:
            failures.append(label)
    tex = WORK / "badge_probe.tex"
    if tex.exists():
        tex.unlink()
    if failures:
        print("\nFAIL badge guard accepted: " + "; ".join(failures))
        return 1
    print(f"\nPASS badge guard rejects all {len(BAD)} non-canonical labels")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
