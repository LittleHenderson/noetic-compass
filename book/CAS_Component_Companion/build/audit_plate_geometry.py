#!/usr/bin/env python3
"""Geometry audit for the companion guide's plate and schematic figures.

The source regression lock (`audit_plate_connectivity.py`) asserts literal
strings, so it can only catch a defect that someone already wrote down. This
audit instead reads the *compiled* PDF geometry of every figure and looks for
the defect class that actually occurred: wire endpoints that touch no other ink.

Method
  1. Take each figure block from the companion's chapter files.
  2. Rebuild it in a scratch directory with three magenta calibration
     dots at known TikZ coordinates, so the TikZ -> PDF transform can be
     recovered exactly (including any non-uniform x/y unit vectors).
  3. Extract every stroked/filled path, flatten curves, and collect segments.
  4. For every segment endpoint, measure the distance to the nearest other ink.
     Endpoints further than TOL from all other ink are "dangling".
  5. Compare the dangling set against `dangling_whitelist.json`,
     which records the reviewed intentional free ends (component terminals
     that are deliberately left unconnected, rail crossbar tips, and so on).
     A new dangling endpoint fails the audit; a whitelist entry that has since
     become connected also fails, so the whitelist cannot go stale.

Nothing outside `build/plates_geo/` is written.
"""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

import pymupdf

import plates

BUILD = Path(__file__).resolve().parent
BOOK = BUILD.parent
# CAS_CHAPTERS lets the negative-control test point the audit at a deliberately
# broken copy of one chapter; CAS_FIGURES_PREAMBLE does the same for the library.
CHAPTER_OVERRIDE = os.environ.get("CAS_CHAPTERS")
STYLES = Path(os.environ.get("CAS_FIGURES_PREAMBLE", plates.STYLES))
WORK = BUILD / "plates_geo"
WHITELIST = BUILD / "dangling_whitelist.json"

PT_PER_MM = 72.0 / 25.4
TOL_PT = 1.25 * PT_PER_MM   # 0.71 mm glyph corners are noise; wires break by >1.25 mm
SMALL_PATH_PT = 3.0 * PT_PER_MM   # closed glyphs smaller than 3 mm act as junction nodes

# Scope. The design rule "every wire must land on other ink" holds for the ten
# schematics. The seven symbol plates deliberately display each glyph in
# isolation with its own terminals exposed, so their dangling ends are the
# design, not a defect; those plates are covered by audit_symbol_invariants.py
# instead. `--all` widens the geometry report to the plates for inspection.
STRICT_PREFIX = "sch-"

FIGURE_RE = plates.FIGURE_RE

TEMPLATE = r"""\documentclass[border=8pt]{standalone}
\usepackage{fontspec}
\defaultfontfeatures{Ligatures=TeX}
\setmainfont{Palatino Linotype}
\setsansfont{Arial}
\usepackage{amsmath,amssymb}
%s
\definecolor{calmag}{rgb}{1,0,1}
\begin{document}
%s
\end{document}
"""

CAL_DOTS = r"""
  \fill[calmag] (0,0) circle (0.6mm);
  \fill[calmag] (100,0) circle (0.6mm);
  \fill[calmag] (0,100) circle (0.6mm);
"""

TIKZ_OPEN_RE = re.compile(r"\\begin\{tikzpicture\}(\[[^\]]*\])?")


# --------------------------------------------------------------- extraction
def flatten(items):
    """Return a list of (p1, p2) segments in PDF points for one drawing item list."""
    segs = []
    for item in items:
        op = item[0]
        if op == "l":
            segs.append((item[1], item[2]))
        elif op == "re":
            r = item[1]
            corners = [pymupdf.Point(r.x0, r.y0), pymupdf.Point(r.x1, r.y0),
                       pymupdf.Point(r.x1, r.y1), pymupdf.Point(r.x0, r.y1)]
            for i in range(4):
                segs.append((corners[i], corners[(i + 1) % 4]))
        elif op == "qu":
            quad = item[1]
            pts = [quad.ul, quad.ur, quad.lr, quad.ll]
            for i in range(4):
                segs.append((pts[i], pts[(i + 1) % 4]))
        elif op == "c":
            p0, p1, p2, p3 = item[1], item[2], item[3], item[4]
            prev = p0
            for k in range(1, 17):
                t = k / 16.0
                mt = 1.0 - t
                x = (mt ** 3) * p0.x + 3 * (mt ** 2) * t * p1.x + 3 * mt * (t ** 2) * p2.x + (t ** 3) * p3.x
                y = (mt ** 3) * p0.y + 3 * (mt ** 2) * t * p1.y + 3 * mt * (t ** 2) * p2.y + (t ** 3) * p3.y
                cur = pymupdf.Point(x, y)
                segs.append((prev, cur))
                prev = cur
    return segs


def drawing_segments(page):
    segs = []
    for d in page.get_drawings():
        items = d.get("items") or []
        if not items:
            continue
        segs.extend(flatten(items))
    return segs


def point_seg_dist(p, a, b):
    ax, ay = a.x, a.y
    bx, by = b.x, b.y
    dx, dy = bx - ax, by - ay
    if dx == 0.0 and dy == 0.0:
        return math.hypot(p.x - ax, p.y - ay)
    t = ((p.x - ax) * dx + (p.y - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(p.x - (ax + t * dx), p.y - (ay + t * dy))


def small_path_centres(page):
    """Centres of tiny *closed* glyphs (junction dots, probe circles).

    Open short stubs (a 1.5 mm lead, for example) also have a small bounding
    box but are not connection nodes, so `closePath` is required.
    """
    centres = []
    for d in page.get_drawings():
        items = d.get("items") or []
        r = d.get("rect")
        if not items or r is None or not d.get("closePath"):
            continue
        if r.width <= SMALL_PATH_PT and r.height <= SMALL_PATH_PT and r.width > 0:
            centres.append(pymupdf.Point((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2))
    return centres


def transform(page):
    """Recover the affine TikZ -> PDF map from the three magenta dots.

    Returns `(to_tikz, to_pdf)`. `to_tikz` maps a PDF point to figure units;
    `to_pdf(tx, ty)` maps figure units back to a PDF point.
    """
    pts = {}
    for d in page.get_drawings():
        fill = d.get("fill")
        if not fill:
            continue
        if abs(fill[0] - 1.0) < 0.02 and abs(fill[1]) < 0.02 and abs(fill[2] - 1.0) < 0.02:
            r = d["rect"]
            pts.setdefault("dot", []).append(
                pymupdf.Point((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2))
    got = pts.get("dot", [])
    if len(got) != 3:
        raise RuntimeError(f"expected 3 calibration dots, found {len(got)}")
    # Identify origin = the dot closest to the other two's corner.
    best = None
    for i in range(3):
        others = [got[j] for j in range(3) if j != i]
        v1 = others[0] - got[i]
        v2 = others[1] - got[i]
        # The three TikZ points are (0,0), (100,0), (0,100): the origin dot has
        # two near-perpendicular vectors of similar length.
        if abs(v1.x * v2.x + v1.y * v2.y) < 1e-6 + 0.05 * abs(v1) * abs(v2):
            if best is None or abs(abs(v1) - abs(v2)) < best[0]:
                best = (abs(abs(v1) - abs(v2)), i, others)
    if best is None:
        raise RuntimeError("calibration dots are not a right angle")
    _, oi, others = best
    origin = got[oi]
    a = others[0] - origin
    b = others[1] - origin
    # TikZ x runs left->right on the page; y runs bottom->top (PDF y is flipped),
    # so the x-axis dot is the one whose page-space vector is the more horizontal.
    if abs(a.x) >= abs(b.x):
        ex, ey = a, b
    else:
        ex, ey = b, a
    sx, sy = ex.x / 100.0, ey.y / 100.0

    def to_tikz(p):
        return ((p.x - origin.x) / sx, (p.y - origin.y) / sy)

    def to_pdf(tx, ty):
        return pymupdf.Point(origin.x + tx * sx, origin.y + ty * sy)

    return to_tikz, to_pdf


def calibration(page):
    """Backwards-compatible accessor for the PDF -> figure-unit direction."""
    return transform(page)[0]


def straight_segments(page):
    """Only true line items, with no curve flattening.

    Flattened curves create dense collinear sub-segments whose midpoints sit
    within a fraction of a millimetre of their neighbours' endpoints, which
    makes junction detection on them meaningless.
    """
    segs = []
    for d in page.get_drawings():
        for item in (d.get("items") or []):
            if item[0] == "l":
                segs.append((item[1], item[2]))
            elif item[0] == "re":
                r = item[1]
                c = [pymupdf.Point(r.x0, r.y0), pymupdf.Point(r.x1, r.y0),
                     pymupdf.Point(r.x1, r.y1), pymupdf.Point(r.x0, r.y1)]
                for i in range(4):
                    segs.append((c[i], c[(i + 1) % 4]))
    return segs


def to_tikz_units(p, origin, sx, sy, dx, dy):
    return ((p.x - origin.x) / sx - dx, (p.y - origin.y) / sy - dy)


# ------------------------------------------------------------------- driver
def chapter_figures():
    """[(label, body)] for every figure, in reading order across the chapters."""
    if CHAPTER_OVERRIDE:
        text = Path(CHAPTER_OVERRIDE).read_text(encoding="utf-8")
        return [(m.group("label"), m.group("body")) for m in FIGURE_RE.finditer(text)]
    return [(m.group("label"), m.group("body")) for _, m in plates.figures()]


def build(with_dots: bool, outdir: Path):
    styles = STYLES.read_text(encoding="utf-8")
    outdir.mkdir(parents=True, exist_ok=True)
    results = {}
    for label, body in chapter_figures():
        body = body.strip()
        if with_dots:
            body = TIKZ_OPEN_RE.sub(
                lambda m: m.group(0) + CAL_DOTS, body, count=1)
        tex = outdir / f"{label}.tex"
        tex.write_text(TEMPLATE % (styles, body), encoding="utf-8")
        done = subprocess.run(
            ["xelatex", "-halt-on-error", "-interaction=nonstopmode",
             f"-output-directory={outdir}", str(tex)],
            cwd=BOOK, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace")
        pdf = outdir / f"{label}.pdf"
        if done.returncode != 0 or not pdf.exists():
            raise RuntimeError(f"{label}: probe build failed")
        results[label] = pdf
    return results


def main() -> int:
    # The dotted probe needs the label's own caption removed (standalone body
    # only), which the regex already isolates.
    dotted = build(True, WORK / "dotted")
    plain = build(False, WORK / "plain")

    findings = []
    for label, pdf in dotted.items():
        dpage = pymupdf.open(pdf)[0]
        to_tikz = calibration(dpage)
        segs = drawing_segments(dpage)
        attached_centres = small_path_centres(dpage)

        def nearest(p, skip_index):
            best = float("inf")
            for k, (a, b) in enumerate(segs):
                if k == skip_index:
                    continue
                v = point_seg_dist(p, a, b)
                if v < best:
                    best = v
            return best

        dangling = []
        for idx, (a, b) in enumerate(segs):
            for p in (a, b):
                v = nearest(p, idx)
                if v > TOL_PT:
                    # A junction dot drawn as a tiny closed glyph counts as ink
                    # only at its own path; treat its centre as attached.
                    v2 = min((math.hypot(p.x - c.x, p.y - c.y)
                              for c in attached_centres), default=float("inf"))
                    if v2 <= SMALL_PATH_PT:
                        continue
                    tx, ty = to_tikz(p)
                    dangling.append((round(tx, 1), round(ty, 1), round(v / PT_PER_MM, 2)))

        # Merge duplicates within 1 mm and drop findings that sit on another
        # finding (a broken wire reports both of its loose ends).
        merged = []
        for tx, ty, gap in sorted(dangling, key=lambda t: -t[2]):
            if all(math.hypot(tx - mx, ty - my) > 1.0 for mx, my, _ in merged):
                merged.append((tx, ty, gap))
        findings.append((label, merged))

    total = sum(len(m) for _, m in findings)
    print(f"figures={len(findings)} dangling_endpoints={total}")
    for label, merged in findings:
        print(f"\n{label}: {len(merged)}")
        for tx, ty, gap in merged:
            print(f"   tikz=({tx:8.1f},{ty:8.1f})  gap={gap:5.2f} mm")

    if "--all" not in sys.argv:
        findings = [(l, m) for l, m in findings if l.startswith(STRICT_PREFIX)]
        print(f"\nstrict scope: {len(findings)} schematics, "
              f"{sum(len(m) for _, m in findings)} endpoints "
              f"(symbol plates reported only with --all)")

    if "--write" in sys.argv:
        data = {label: {"note": "REVIEW ME", "free": [[tx, ty] for tx, ty, _ in merged]}
                for label, merged in findings}
        WHITELIST.write_text(json.dumps(data, indent=1), encoding="utf-8")
        print(f"\nwrote {WHITELIST}")
        return 0

    if not WHITELIST.exists():
        print("FAIL no whitelist; run with --write and review each entry", file=sys.stderr)
        return 1
    approved = json.loads(WHITELIST.read_text(encoding="utf-8"))
    problems = []
    for label, merged in findings:
        entry = approved.get(label)
        if entry is None and not merged:
            continue          # fully connected schematic, nothing to record
        if entry is None:
            entry = {}
        want = [tuple(p) for p in entry.get("free", [])]
        if merged and not entry.get("note"):
            problems.append(f"{label}: whitelist entry has no reviewed note")
        unmatched = list(want)
        for tx, ty, gap in merged:
            hit = None
            for i, (wx, wy) in enumerate(unmatched):
                if math.hypot(tx - wx, ty - wy) <= 1.5:
                    hit = i
                    break
            if hit is None:
                problems.append(f"{label}: NEW dangling endpoint at ({tx},{ty}) gap={gap} mm")
            else:
                unmatched.pop(hit)
        for wx, wy in unmatched:
            problems.append(f"{label}: whitelisted free end ({wx},{wy}) is now connected (stale entry)")
    if problems:
        print("\nFAIL geometry audit")
        for p in problems:
            print("  " + p)
        return 1
    print("\nPASS companion plate geometry audit (no new dangling endpoints)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        raise SystemExit(1)
