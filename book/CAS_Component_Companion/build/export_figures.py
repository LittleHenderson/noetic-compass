#!/usr/bin/env python3
"""Export the audited plate and schematic figures as PNGs.

Renders from `plates_verify/*.pdf` — the standalone builds that the audits read —
so the exported images are the same drawings that passed verification. Run
`verify_plates.py` first; a PNG here can never be newer than the figure it shows.

    python export_figures.py [--dpi 300]
"""
from __future__ import annotations

import sys
from pathlib import Path

import pymupdf

BUILD = Path(__file__).resolve().parent
SRC = BUILD / "plates_verify"
OUT = BUILD.parent / "figures"


def main() -> int:
    dpi = 300
    for i, a in enumerate(sys.argv[1:]):
        if a == "--dpi" and i + 2 <= len(sys.argv[1:]):
            dpi = int(sys.argv[i + 2])
        elif a.startswith("--dpi="):
            dpi = int(a.split("=", 1)[1])
    if not SRC.exists():
        raise SystemExit("no plates_verify/ — run verify_plates.py first")
    OUT.mkdir(exist_ok=True)
    zoom = dpi / 72.0
    n = 0
    for pdf in sorted(SRC.glob("*.pdf")):
        page = pymupdf.open(pdf)[0]
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        target = OUT / f"fig-{pdf.stem}.png"
        pix.save(target)
        n += 1
        print(f"{target.name}  {pix.width}x{pix.height}")
    print(f"exported {n} figure(s) at {dpi} dpi to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
