#!/usr/bin/env python3
"""Measure the real print margins of a produced interior PDF.

The book's changelog has claimed "0 margin violations" since v0.8.1, but no
script that measures margins existed in the repository -- the claim rested on
a KDP previewer run and a hand-read preamble constant. This measures the
finished PDF instead: for every page it takes the union of all text spans and
vector drawing rectangles, and reports the distance from that ink to each
trim edge.

Gutter side depends on the page's parity: on a recto (odd) page the spine is
on the left, on a verso (even) page it is on the right.

  python verify_print_margins.py [pdf] [--pages N]

Exit status is non-zero only when ink comes closer than MARGIN_FLOOR to any
trim edge. The measured gutter is *reported* against the KDP requirement for
the page count so a human can confirm the band; nothing here re-derives KDP
policy from the PDF.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pymupdf

MM = 72.0 / 25.4
MARGIN_FLOOR = 0.25 * 72.0      # 18 pt: KDP's minimum outside margin, no bleed
GUTTER_TARGET = 0.875 * 72.0    # 63 pt: KDP inside margin at 701-828 pages


def ink_bbox(page) -> pymupdf.Rect | None:
    box = None

    def add(r):
        nonlocal box
        if r is None or r.is_empty or r.is_infinite:
            return
        box = r if box is None else box | r

    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                if span["text"].strip():
                    add(pymupdf.Rect(span["bbox"]))
    for d in page.get_drawings():
        add(d.get("rect"))
    for info in page.get_image_info():
        add(pymupdf.Rect(info["bbox"]))
    return box


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    path = Path(args[0]) if args else Path(__file__).resolve().parent.parent / "CAS_PCBA_Engineer_print.pdf"
    limit = None
    for a in sys.argv[1:]:
        if a.startswith("--pages="):
            limit = int(a.split("=", 1)[1])

    doc = pymupdf.open(path)
    width, height = doc[0].rect.width, doc[0].rect.height
    print(f"{path.name}: {doc.page_count} pages, {width:.1f} x {height:.1f} pt "
          f"({width / 72:.3f} x {height / 72:.3f} in)")

    worst = {"top": (1e9, 0), "bottom": (1e9, 0), "inside": (1e9, 0), "outside": (1e9, 0)}
    blank = 0
    for i, page in enumerate(doc):
        if limit and i >= limit:
            break
        box = ink_bbox(page)
        if box is None:
            blank += 1
            continue
        top = box.y0
        bottom = height - box.y1
        if (i + 1) % 2 == 0:            # verso: spine on the right
            inside, outside = width - box.x1, box.x0
        else:                            # recto: spine on the left
            inside, outside = box.x0, width - box.x1
        for name, value in (("top", top), ("bottom", bottom),
                            ("inside", inside), ("outside", outside)):
            if value < worst[name][0]:
                worst[name] = (value, i + 1)

    print(f"\nblank pages (no ink): {blank}")
    print(f"{'edge':9} {'min (pt)':>9} {'min (in)':>9}   page")
    for name in ("inside", "outside", "top", "bottom"):
        value, page = worst[name]
        print(f"{name:9} {value:9.1f} {value / 72:9.3f}   {page}")

    problems = []
    for name in ("inside", "outside", "top", "bottom"):
        value, page = worst[name]
        if value < MARGIN_FLOOR:
            problems.append(f"{name} margin {value / 72:.3f} in on page {page} "
                            f"is below the {MARGIN_FLOOR / 72:.2f} in floor")
    inside, page = worst["inside"]
    band = "OK" if inside >= GUTTER_TARGET else "BELOW the 0.875 in requirement"
    print(f"\ngutter: {inside / 72:.4f} in on page {page} -- {band}")
    if problems:
        print("\nFAIL print margins")
        for p in problems:
            print("  " + p)
        return 1
    print(f"PASS print margins (no ink within {MARGIN_FLOOR / 72:.2f} in of a trim edge)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
