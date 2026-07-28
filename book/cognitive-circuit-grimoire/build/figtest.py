"""Compile one or more figure .tex files standalone, to catch errors early.

    python figtest.py fig_08_A.tex fig_08_B.tex
    python figtest.py --all

A figure that does not compile here will not compile in the book, and a TikZ
error inside a 400-page build is far harder to find than one here. Also renders
a PNG so the artist can LOOK at the drawing rather than assume it is right --
a figure can compile cleanly and still be blank, mis-scaled, or overlapping.
"""

from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BUILD = Path(__file__).resolve().parent
FIGDIR = BUILD / "figures"
TESTDIR = BUILD / "figtest"

# The book measure at 6x9 with the Grimoire margins. A figure wider than this
# overflows into the gutter and prints clipped.
MAX_WIDTH_CM = 11.0

WRAP = r"""\documentclass[11pt,border=3pt]{standalone}
\usepackage{fontspec}
\setmainfont{Palatino Linotype}
\setsansfont{Arial}
\input{../figures_preamble.tex}
\begin{document}
%s
\end{document}
"""


def compile_one(fig: Path) -> tuple[bool, str]:
    TESTDIR.mkdir(exist_ok=True)
    stem = fig.stem
    tex = TESTDIR / f"{stem}.tex"
    tex.write_text(WRAP % fig.read_text(encoding="utf-8"), encoding="utf-8")
    r = subprocess.run(
        ["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex.name],
        cwd=TESTDIR, capture_output=True, text=True, errors="replace")
    pdf = TESTDIR / f"{stem}.pdf"
    if r.returncode != 0 or not pdf.exists():
        out = r.stdout or ""
        err = [ln for ln in out.splitlines() if ln.startswith("!")][:3]
        return False, "; ".join(err) or "compile failed"

    # Size check, and a blank-page check -- a figure can compile and be empty.
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True,
                          errors="replace").stdout
    size = next((l for l in info.splitlines() if "Page size" in l), "")
    try:
        w_pt = float(size.split()[2])
        w_cm = w_pt / 28.3465
    except Exception:
        w_cm = 0.0
    subprocess.run(["pdftoppm", "-png", "-r", "110", str(pdf),
                    str(TESTDIR / stem)], capture_output=True)
    png = TESTDIR / f"{stem}-1.png"
    note = f"{w_cm:.1f}cm wide"
    if w_cm > MAX_WIDTH_CM:
        note += f"  ** TOO WIDE (max {MAX_WIDTH_CM}cm) **"
    if png.exists():
        try:
            from PIL import Image
            im = Image.open(png).convert("L")
            px = list(im.getdata())
            dark = sum(1 for p in px if p < 240)
            frac = dark / max(1, len(px))
            note += f", {frac*100:.1f}% inked"
            if frac < 0.005:
                note += "  ** LOOKS BLANK **"
        except Exception:
            pass
        note += f", preview {png.name}"
    return True, note


def main() -> int:
    args = sys.argv[1:]
    figs = (sorted(FIGDIR.glob("fig_*.tex")) if not args or args[0] == "--all"
            else [FIGDIR / a for a in args])
    if not figs:
        print("  no figures to test")
        return 0
    bad = 0
    for f in figs:
        if not f.exists():
            print(f"  MISSING  {f.name}")
            bad += 1
            continue
        ok, note = compile_one(f)
        print(f"  {'OK  ' if ok else 'FAIL'}  {f.name:18s} {note}")
        if not ok or "**" in note:
            bad += 1
    print(f"\n  {len(figs) - bad}/{len(figs)} clean")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
