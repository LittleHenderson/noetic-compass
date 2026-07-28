"""Replace [[FIGURE n-X: description]] markers with real TikZ figures.

Chapter writers leave a marker naming what must be drawn. Figure artists write
one TikZ file per marker into build/figures/. This script joins them.

Ordering: run AFTER assembly and BEFORE pandoc, so the raw-LaTeX blocks pass
through untouched. The generated main_body.md is modified; chapter sources are
never rewritten by this step.

Fails loudly on a marker with no matching figure file. A silently dropped figure
is worse than a broken build, because the caption numbering shifts and every
"see Figure 13-C" after it points at the wrong drawing.
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BOOK = Path(__file__).resolve().parent.parent
MS = BOOK / "manuscript"
BUILD = BOOK / "build"
FIGDIR = Path(__file__).resolve().parent / "figures"

MARKER = re.compile(r"^\s*\[\[FIGURE\s+([0-9]+)-([A-Z]):\s*(.+?)\]\]\s*$",
                    re.M | re.S)
FUSED_RAW_FENCE = "`" * 6 + "{=latex}"


def fig_path(ch: str, letter: str) -> Path:
    return FIGDIR / f"fig_{int(ch):02d}_{letter}.tex"


LATEX_TEXT_ESCAPE = {
    chr(92): r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "$": r"\$",
    "&": r"\&",
    "#": r"\#",
    "_": r"\_",
    "%": r"\%",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def latex_text(text: str) -> str:
    """Escape marker prose before placing it in a raw-LaTeX caption."""
    # Backticks are Markdown delimiters, not part of the printed caption. Raw
    # LaTeX blocks bypass pandoc, so strip them here and escape every character
    # that TeX would otherwise interpret as syntax.
    text = text.replace("`", "")
    return "".join(LATEX_TEXT_ESCAPE.get(char, char) for char in text)


def latex_block(ch: str, letter: str, caption: str) -> str:
    """A float carrying the drawing, its number, and its caption.

    \\index{} must never appear inside the caption -- it is a moving argument and
    putting an index mark in one corrupts the .aux. That bug cost a companion
    volume 82 pages and an empty index.
    """
    body = fig_path(ch, letter).read_text(encoding="utf-8").strip()
    cap = caption.strip().rstrip(".")
    # Keep the caption to one clean sentence; the marker text is a drawing brief
    # and is often far too long to sit under a figure.
    cap = re.split(r"\s+[-—]\s+|\.\s+", cap)[0].strip()
    if len(cap) > 150:
        cap = cap[:147].rsplit(" ", 1)[0] + "…"
    cap = latex_text(cap)
    # The authored marker letter is authoritative even when figures appear in
    # pedagogical rather than alphabetic order (Chapter 18 intentionally places
    # 18-D before 18-A). Set the pre-caption value explicitly; \caption then
    # advances it to the requested letter.
    figure_counter = ord(letter) - ord("A")
    return (
        "```{=latex}\n"
        "\\begin{figure}[htbp]\n"
        "\\centering\n"
        f"\\setcounter{{figure}}{{{figure_counter}}}\n"
        f"{body}\n"
        f"\\caption{{{cap}}}\n"
        f"\\label{{fig:{int(ch):02d}-{letter}}}\n"
        "\\end{figure}\n"
        # Leave a blank Markdown line between consecutive raw blocks. Without
        # it, adjacent markers fuse into a literal ``````{=latex} line that
        # leaks through pandoc into body.tex.
        "```\n\n"
    )


def process(path: Path, missing: list[str], placed: list[str]) -> int:
    text = path.read_text(encoding="utf-8")
    n = 0

    def repl(m: re.Match) -> str:
        nonlocal n
        ch, letter, desc = m.group(1), m.group(2), m.group(3)
        fid = f"{ch}-{letter}"
        if not fig_path(ch, letter).exists():
            missing.append(f"{fid}  ({path.name})")
            return m.group(0)          # leave the marker; the check below fails
        n += 1
        placed.append(fid)
        return latex_block(ch, letter, desc)

    out = MARKER.sub(repl, text)
    if FUSED_RAW_FENCE in out:
        raise ValueError(
            f"{path.name}: adjacent raw-LaTeX fences fused after figure insertion"
        )
    if out != text:
        path.write_text(out, encoding="utf-8")
    return n


def main() -> int:
    if not FIGDIR.exists():
        FIGDIR.mkdir(parents=True)
        print(f"  created {FIGDIR}")

    missing: list[str] = []
    placed: list[str] = []
    target = BUILD / "main_body.md"
    if not target.exists():
        print(f"  MISSING ASSEMBLED BODY: {target}")
        print("  run build_book.py before insert_figures.py")
        return 1

    total = process(target, missing, placed)

    print(f"  figures placed : {total}")
    print(f"  figure files   : {len(list(FIGDIR.glob('fig_*.tex')))}")

    if missing:
        print(f"\n  NOT YET DRAWN ({len(missing)}):")
        for item in missing:
            print(f"     - {item}")
        print("\n  Markers left in place. Draw these before the final build, or"
              "\n  the book ships with literal [[FIGURE ...]] text in it.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
