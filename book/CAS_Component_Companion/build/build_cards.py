#!/usr/bin/env python3
"""Build the companion guide's printable card deck.

The guide itself *is* the handbook, so this builds only the cards:
`companion_cards.tex` -> `../CAS_Component_Companion_Cards.pdf`.

Requires XeLaTeX and the fonts listed in BUILD_README.md. The card source reads
`figures_preamble.tex` from this directory, which `companion_build.py` copies
from the main volume's build directory; run that first, or run
`build_companion.py`, which does both.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent
BOOK = BUILD.parent
CARDS_TEX = BUILD / "companion_cards.tex"
CARDS_PDF = BOOK / "CAS_Component_Companion_Cards.pdf"


def main() -> int:
    if not CARDS_TEX.exists():
        raise SystemExit(f"missing card source: {CARDS_TEX}")
    if not (BUILD / "figures_preamble.tex").exists():
        raise SystemExit("missing figures_preamble.tex — run companion_build.py first")
    for _ in range(2):   # two passes for the textpos grid and cross-references
        done = subprocess.run(
            ["xelatex", "-halt-on-error", "-interaction=nonstopmode", CARDS_TEX.name],
            cwd=BUILD, text=True, encoding="utf-8", errors="replace",
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if done.returncode != 0:
            print((done.stdout or "")[-2500:])
            raise SystemExit("card deck failed to compile")
    shutil.copy2(BUILD / "companion_cards.pdf", CARDS_PDF)
    print(f"WROTE {CARDS_PDF}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
