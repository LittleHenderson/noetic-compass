#!/usr/bin/env python3
"""Check a generated cover wrap for text collisions and reserved zones.

The template positions everything absolutely, so a too-long blurb does not
raise a LaTeX warning -- it silently prints text on top of the author bio.
This measures the finished PDF instead, and also checks KDP's barcode clear
zone (2.0 x 1.2 in, inset 0.25 in from the trim, bottom-right of the back
panel) and KDP's rule that a spine under 100 pages carries no type.

PyMuPDF uses a TOP-LEFT origin, so every y below is measured from the top of
the sheet; get that wrong and the barcode check reports the front-cover hook.

  python verify_cover.py cas_component_companion_wrap.pdf --pages=58
"""
from __future__ import annotations

import sys
from pathlib import Path

import pymupdf

BLEED = 0.125
TRIM_W, TRIM_H = 6.0, 9.0
SPINE_PER_PAGE = 0.002252
SPINE_TEXT_MIN_PAGES = 100
PT = 72.0


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    name = args[0] if args else "cas_component_companion_wrap.pdf"
    pages = 58
    for a in sys.argv[1:]:
        if a.startswith("--pages="):
            pages = int(a.split("=", 1)[1])

    page = pymupdf.open(Path(__file__).resolve().parent / name)[0]
    width_in = page.rect.width / PT
    height_in = page.rect.height / PT
    spine_w = pages * SPINE_PER_PAGE
    back_x1 = BLEED + TRIM_W                    # back panel's right edge = spine start
    front_x = BLEED + TRIM_W + spine_w          # front panel's left edge = spine end

    blocks = []
    for i, b in enumerate(page.get_text("dict")["blocks"]):
        txt = " ".join("".join(s["text"] for s in ln["spans"])
                       for ln in b.get("lines", [])).strip()
        if txt:
            blocks.append((i, pymupdf.Rect(b["bbox"]), txt))

    def x0_in(r):
        return r.x0 / PT

    def x1_in(r):
        return r.x1 / PT

    back = [(i, r, t) for i, r, t in blocks if x1_in(r) <= back_x1 + 0.02]
    front = [(i, r, t) for i, r, t in blocks if x0_in(r) >= front_x - 0.02]
    spine_blocks = [(i, r, t) for i, r, t in blocks
                    if back_x1 < x0_in(r) and x1_in(r) < front_x]

    print(f"{name}: {width_in:.4f} x {height_in:.4f} in, "
          f"spine {spine_w:.4f} in @ {pages}pp")
    print(f"  back blocks: {len(back)}   front: {len(front)}   "
          f"spine: {len(spine_blocks)}")

    problems = []

    if pages < SPINE_TEXT_MIN_PAGES and spine_blocks:
        problems.append(f"spine carries {len(spine_blocks)} text block(s) but the "
                        f"book is {pages} pages (KDP prints spine type only at "
                        f"{SPINE_TEXT_MIN_PAGES}+)")

    # Barcode clear zone: bottom-right of the back panel, top-left origin.
    zone = pymupdf.Rect((back_x1 - 0.25 - 2.0) * PT,
                        (height_in - 0.25 - 1.2) * PT,
                        (back_x1 - 0.25) * PT,
                        (height_in - 0.25) * PT)
    for _, r, t in back:
        if r.intersects(zone) and (r & zone).get_area() > 4:
            problems.append(f"back text {t[:44]!r} enters the barcode clear zone")

    trim = pymupdf.Rect(BLEED * PT, BLEED * PT,
                        (BLEED + 2 * TRIM_W + spine_w) * PT,
                        (height_in - BLEED) * PT)
    for _, r, t in blocks:
        if (r.x0 < trim.x0 - 1 or r.x1 > trim.x1 + 1
                or r.y0 < trim.y0 - 1 or r.y1 > trim.y1 + 1):
            problems.append(f"text {t[:44]!r} leaves the trim area")

    # Collisions between DIFFERENT blocks only: consecutive lines of one
    # paragraph always overlap slightly in their bounding boxes.
    for a, ra, ta in back:
        for b, rb, tb in back:
            if b <= a:
                continue
            if ra.intersects(rb) and (ra & rb).get_area() > 20:
                problems.append(f"overlap: {ta[:26]!r} and {tb[:26]!r}")

    if problems:
        print("\nFAIL cover")
        for p in problems:
            print("  " + p)
        return 1
    print("PASS cover (no collisions, barcode zone clear, text inside trim)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
