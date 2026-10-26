#!/usr/bin/env python3
"""Symbol-level invariants for the companion guide's drawing library.

`audit_plate_geometry.py` covers the ten schematics, where the design
rule is "every wire lands on other ink". The seven symbol plates draw each
glyph in isolation with its terminals exposed, so that rule does not apply
there. What must hold instead is that each glyph is *electrically itself*.

This audit compiles one `pics/cas*` glyph at a time and checks invariants that
a plausible-looking but wrong drawing would fail:

  casbridge      every diode's cathode bar points at the node it feeds
  casmirror      the reference device is diode-connected and the bias is shared
  casschmitt     the hysteresis mark lies entirely inside the triangle
  casswitch      the arm is open: the moving contact does not touch the far one
  casrelay       the mechanical linkage touches both the coil and the armature
  casbreaker     the trip square is carried on the operating arm
  caszener       the bent cathode bar is attached to the diode apex

Nothing outside `build/plates_symbols/` is written.
"""
from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

import pymupdf

import audit_plate_geometry as G

BUILD = Path(__file__).resolve().parent
BOOK = BUILD.parent
WORK = BUILD / "plates_symbols"
TOL = 0.35 * G.PT_PER_MM          # 0.35 mm: tight, these glyphs are millimetres wide
NODE_SNAP = 0.3 * G.PT_PER_MM

TEMPLATE = r"""\documentclass[border=8pt]{standalone}
\usepackage{fontspec}
\defaultfontfeatures{Ligatures=TeX}
\setmainfont{Palatino Linotype}
\setsansfont{Arial}
\usepackage{amsmath,amssymb}
%s
\definecolor{calmag}{rgb}{1,0,1}
\begin{document}
\begin{tikzpicture}[x=1mm,y=1mm]
  \fill[calmag] (0,0) circle (0.6mm);
  \fill[calmag] (100,0) circle (0.6mm);
  \fill[calmag] (0,100) circle (0.6mm);
  \pic at (0,0) {%s};
\end{tikzpicture}
\end{document}
"""


def compile_pic(pic: str) -> pymupdf.Page:
    WORK.mkdir(parents=True, exist_ok=True)
    tex = WORK / f"{pic}.tex"
    tex.write_text(TEMPLATE % (G.STYLES.read_text(encoding="utf-8"), pic), encoding="utf-8")
    done = subprocess.run(
        ["xelatex", "-halt-on-error", "-interaction=nonstopmode",
         f"-output-directory={WORK}", str(tex)],
        cwd=BOOK, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace")
    pdf = WORK / f"{pic}.pdf"
    if done.returncode != 0 or not pdf.exists():
        raise RuntimeError(f"{pic}: probe build failed")
    return pymupdf.open(pdf)[0]


def segments_of(page):
    return G.drawing_segments(page)


def straight_of(page):
    return G.straight_segments(page)


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def endpoints(segs):
    return [p for s in segs for p in s]


def connected_components(segs):
    """Union-find over segment endpoints snapped to NODE_SNAP."""
    pts = endpoints(segs)
    parent = list(range(len(pts)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    # Join every segment's own two ends, then chain endpoints that coincide and
    # endpoints that land on another segment.
    for k, (a, b) in enumerate(segs):
        union(2 * k, 2 * k + 1)
    for i, p in enumerate(pts):
        for j in range(i + 1, len(pts)):
            if dist(p, pts[j]) <= NODE_SNAP:
                union(i, j)
    for i, p in enumerate(pts):
        for k, (a, b) in enumerate(segs):
            if i in (2 * k, 2 * k + 1):
                continue
            if G.point_seg_dist(p, a, b) <= NODE_SNAP:
                union(i, 2 * k)
    groups = {}
    for i in range(len(pts)):
        groups.setdefault(find(i), []).append(pts[i])
    return list(groups.values())


def nearest_terminal(comp, target):
    return min(dist(p, target) for p in comp)


# ------------------------------------------------------------------ checks
def check_bridge(page) -> list[str]:
    """Each diode's cathode bar must point at the node it feeds.

    Bridge convention used by the glyph: left and right corners are the AC
    (~) inputs; the top corner is DC+ and the bottom corner is DC-. Physics
    then fixes the conduction direction of each of the four diodes:
      upper-left  -> DC+      upper-right -> DC+
      lower-left  <- DC-      lower-right <- DC-
    The apex of the triangle is the cathode, so the apex must sit nearer the
    node its diode feeds than the far end of the same diamond edge.
    """
    segs = straight_of(page)
    problems = []
    # The cathode bar is the segment whose midpoint is the shared endpoint of
    # the two slanted triangle sides.
    apexes = []
    for i, (a, b) in enumerate(segs):
        mid = ((a.x + b.x) / 2, (a.y + b.y) / 2)
        touching = 0
        for j, (c, d) in enumerate(segs):
            if j == i:
                continue
            if dist((c.x, c.y), mid) <= NODE_SNAP or dist((d.x, d.y), mid) <= NODE_SNAP:
                touching += 1
        if touching >= 2:
            apexes.append(mid)
    if len(apexes) != 4:
        return [f"casbridge: found {len(apexes)} diode apexes, expected 4"]
    to_tikz, _ = G.transform(page)
    quadrant_rule = {
        (True, True):   ((0.0, 4.0), (-4.0, 0.0), "DC+"),      # upper-left
        (False, True):  ((0.0, 4.0), (4.0, 0.0), "DC+"),       # upper-right
        (True, False):  ((-4.0, 0.0), (0.0, -4.0), "AC-left"), # lower-left
        (False, False): ((4.0, 0.0), (0.0, -4.0), "AC-right"), # lower-right
    }
    for apex in apexes:
        tx, ty = to_tikz(pymupdf.Point(*apex))
        target, other, want = quadrant_rule[(tx < 0, ty > 0)]
        d_want = math.hypot(tx - target[0], ty - target[1])
        d_other = math.hypot(tx - other[0], ty - other[1])
        if d_want >= d_other:
            problems.append(
                f"casbridge: the diode at ({tx:.1f},{ty:.1f}) has its cathode "
                f"bar pointing away from {want} "
                f"({d_want:.2f} mm to {want} vs {d_other:.2f} mm to the other end)")
    return problems


def check_mirror(page) -> list[str]:
    """The current mirror must be wired as a mirror.

    A current mirror is not defined by "two devices and some wires". Three
    things must hold, and only straight wire segments may be used to establish
    them -- the device circles are bodies, not conductors:

      * the reference device is diode-connected: its base and its collector
        are one node;
      * that node drives the second device's base, so both bases are one node.

    Terminals: base_left (-3.5, 0), base_right (3.5, 0),
    collector_left (-2, 3.5), collector_right (2, 3.5) -- the output.
    """
    wires = G.straight_segments(page)
    _, to_pdf = G.transform(page)
    terminals = {
        "base_left": (-3.5, 0.0),
        "base_right": (3.5, 0.0),
        "collector_left": (-2.0, 3.5),
    }
    problems = []
    pts = [p for s in wires for p in s]
    landed = {}
    for name, t in terminals.items():
        target = to_pdf(*t)
        best = min((dist((p.x, p.y), (target.x, target.y)) for p in pts),
                   default=float("inf"))
        if best > NODE_SNAP:
            problems.append(f"casmirror: no wire reaches terminal {name} at {t} "
                            f"(nearest wire end {best / G.PT_PER_MM:.2f} mm)")
        else:
            landed[name] = target
    if problems:
        return problems
    comps = connected_components(wires)
    home = {}
    for name, target in landed.items():
        best, idx = None, None
        for k, comp in enumerate(comps):
            d = min(dist((p.x, p.y), (target.x, target.y)) for p in comp)
            if best is None or d < best:
                best, idx = d, k
        home[name] = idx
    if len(set(home.values())) != 1:
        detail = "; ".join(sorted(str(sorted(n for n, i in home.items() if i == k))
                                  for k in set(home.values())))
        problems.append("casmirror: bias/reference terminals are not one node set "
                        f"(found {len(set(home.values()))}: {detail})")
    return problems


def check_schmitt(page) -> list[str]:
    """Every hysteresis-mark vertex must lie inside the triangle."""
    to_tikz, _ = G.transform(page)
    verts = [(-3.0, -2.5), (-3.0, 2.5), (3.0, 0.0)]
    boundary = [(-5.0, 0.0), (5.0, 0.0), (3.0, 0.0), (-3.0, 0.0)]

    def signed_area(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])

    def inside(x, y, slack=0.20):
        """True when (x, y) is inside the triangle, or within `slack` mm of it."""
        d = [signed_area(verts[i], verts[(i + 1) % 3], (x, y)) for i in range(3)]
        if all(v >= -slack for v in d) or all(v <= slack for v in d):
            return True
        # A point just outside an edge has one sign flipped by less than slack
        # times the edge length; test the perpendicular distance directly.
        for i in range(3):
            a, b = verts[i], verts[(i + 1) % 3]
            ex, ey = b[0] - a[0], b[1] - a[1]
            length = math.hypot(ex, ey)
            perp = abs((x - a[0]) * ey - (y - a[1]) * ex) / length
            if perp <= slack:
                continue
            proj = ((x - a[0]) * ex + (y - a[1]) * ey) / (length * length)
            if 0.0 <= proj <= 1.0:
                return False
        return True

    problems = []
    for p in G.straight_segments(page):
        for q in (p[0], p[1]):
            tx, ty = to_tikz(q)
            if any(dist((tx, ty), k) <= 0.4 for k in verts + boundary):
                continue
            if tx < -3.4 or tx > 3.4 or ty < -2.9 or ty > 2.9:
                continue                      # calibration dots and stray ink
            if not inside(tx, ty):
                problems.append(
                    f"casschmitt: ink vertex ({tx:.2f},{ty:.2f}) is outside the triangle")
    return problems


def check_gap(page, pic, moving, far, minimum) -> list[str]:
    """A switch must be open: the arm tip must not reach the far contact."""
    _, to_pdf = G.transform(page)
    segs = segments_of(page)
    moving_pt = to_pdf(*moving)
    best = float("inf")
    for a, b in segs:
        if dist((a.x, a.y), (moving_pt.x, moving_pt.y)) < 0.05 or \
           dist((b.x, b.y), (moving_pt.x, moving_pt.y)) < 0.05:
            continue                       # the arm itself
        best = min(best, G.point_seg_dist(moving_pt, a, b))
    got = best / G.PT_PER_MM
    if got < minimum:
        return [f"{pic}: moving contact at {moving} is only {got:.2f} mm from "
                f"{far}; the device must be drawn open (>= {minimum} mm)"]
    return []


def check_attached(page, pic, points, tol=0.45) -> list[str]:
    """Each named point must sit on some other ink (linkage, trip square, bar)."""
    _, to_pdf = G.transform(page)
    segs = segments_of(page)
    problems = []
    for pt in points:
        p = to_pdf(*pt)
        best = float("inf")
        for a, b in segs:
            if dist((a.x, a.y), (p.x, p.y)) < 0.05 or dist((b.x, b.y), (p.x, p.y)) < 0.05:
                continue
            best = min(best, G.point_seg_dist(p, a, b))
        if best / G.PT_PER_MM > tol:
            problems.append(f"{pic}: point {pt} is {best / G.PT_PER_MM:.2f} mm "
                            f"from any other ink (must be attached)")
    return problems


def check_linkage(page, pic, coil_top, arm_y) -> list[str]:
    """A relay's mechanical linkage must span from the coil to the armature.

    Checking only that both ends touch *some* ink is too weak: the coil box
    edge runs through the linkage's lower end and the armature runs through
    its upper end, so a short floating dash passes either way. The linkage
    must actually reach down to the coil and up to the arm.
    """
    to_tikz, _ = G.transform(page)
    wires = G.straight_segments(page)
    candidates = []
    for a, b in wires:
        (ax, ay), (bx, by) = to_tikz(a), to_tikz(b)
        if abs(ax - coil_top[0]) < 0.3 and abs(bx - coil_top[0]) < 0.3:
            candidates.append((min(ay, by), max(ay, by)))
    if not candidates:
        return [f"{pic}: no vertical linkage found at x={coil_top[0]}"]
    problems = []
    for lo, hi in candidates:
        if lo > coil_top[1] + 0.1 or hi < arm_y:
            problems.append(
                f"{pic}: linkage spans y {lo:.2f}..{hi:.2f}, which does not reach "
                f"both the coil top (y={coil_top[1]}) and the armature (y>={arm_y})")
    return problems


CHECKS = [
    ("casbridge", check_bridge),
    ("casmirror", check_mirror),
    ("casschmitt", check_schmitt),
    ("casswitch", lambda p: check_gap(p, "casswitch", (1.2, 1.4), (1.8, 0.0), 0.8)),
    ("casrelay", lambda p: check_linkage(p, "casrelay", (0.0, -1.0), 2.2)),
    # The trip square must sit on the operating arm, which passes (-0.3, 0.7).
    ("casbreaker", lambda p: check_attached(p, "casbreaker", [(-0.3, 0.7)])),
    # The bent cathode bar must cross the diode apex (1.2, 0).
    ("caszener", lambda p: check_attached(p, "caszener", [(1.2, 0.0)])),
]


def main() -> int:
    failed = False
    for pic, fn in CHECKS:
        page = compile_pic(pic)
        problems = fn(page)
        if problems:
            failed = True
            for p in problems:
                print(f"FAIL {p}")
        else:
            print(f"OK   {pic}")
    if failed:
        return 1
    print(f"\nPASS companion symbol invariants ({len(CHECKS)} checks)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        raise SystemExit(1)
