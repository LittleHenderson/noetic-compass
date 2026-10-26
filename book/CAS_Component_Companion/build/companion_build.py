#!/usr/bin/env python3
"""Assemble *The Component Companion* into pandoc-ready Markdown + a preamble.

Outputs into build/:
  - figures_preamble.tex  (copy of the main volume's TikZ symbol library)
  - preamble_companion.tex (patched copy of the proven CAS manuscript preamble)
  - front_prose.md        (Preface + How to Use + How to Read, unnumbered)
  - main_body.md          (11 chapters + Appendix A)

`figures_preamble.tex` is COPIED rather than duplicated so the symbol library has
one source of truth: fix a glyph in `CAS_PCBA_Engineer/build/figures_preamble.tex`
and this guide picks it up on the next build.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import plates

BOOK = plates.COMPANION
BUILD = plates.BUILD
SRC_PREAMBLE = BOOK.parent / "publishing" / "latex" / "preamble.tex"

CHAPTERS = [
    "01_Four_Kinds_of_Human_Experience.md",
    "02_The_Notation_and_the_Symbols.md",
    "03_The_Signal_and_Annotation_Legend.md",
    "04_Flow_and_State_Retention.md",
    "05_Direction_Threshold_and_Sensing.md",
    "06_Active_and_Comparative_Parts.md",
    "07_Rhythm_and_Register_Conversion.md",
    "08_Logic_and_Routing.md",
    "09_Regulation_Protection_and_Annotations.md",
    "10_Case_Grief_That_Will_Not_Discharge.md",
    "11_Case_The_Craving_Loop.md",
    "12_Case_The_Panic_That_Fires_Too_Easily.md",
    "13_Case_The_Argument_That_Resonates.md",
    "14_Case_The_Trigger_That_Is_Not_a_Reason.md",
    "15_Case_Muscle_Memory.md",
    "16_Case_The_Purpose_That_Holds.md",
    "17_Case_The_Session_That_Browned_Out.md",
    "18_Case_Social_Engineering_Read_Two_Ways.md",
    "19_What_Else_This_Pair_Illustrates.md",
    "20_Single_Stage_Schematics.md",
    "21_Board_Level_Schematics.md",
    "22_The_Complete_Memory_Deck.md",
    "23_Printing_and_Using_the_Card_Deck.md",
]

# Parts group the chapters. The guide is organised around human experience:
# what a person is made of, the parts that explain it, nine lives worked
# through, the schematics, then the reference tables.
PARTS = [
    ("Reading a Human Being", "Four kinds of experience, two languages, one legend",
     CHAPTERS[0:3]),
    ("The Parts, and the Lives They Explain", "Every symbol, in all four registers",
     CHAPTERS[3:9]),
    ("Lives, Worked Through", "Nine situations, beginning to end",
     CHAPTERS[9:19]),
    ("The Schematics", "The same circuits, drawn at reference size",
     CHAPTERS[19:21]),
    ("Reference", "One table to memorise, and the printable deck",
     CHAPTERS[21:23]),
]

APPENDICES = ["Appendix_A_Design_Notes.md"]

CH_PREFIX = re.compile(r"^#\s+Chapter\s+\d+\s*[:\-—]\s*")
APX_PREFIX = re.compile(r"^#\s+Appendix\s+[A-Z]\s*[:\-—–]\s*")


def strip_h1_prefix(text: str, kind: str) -> str:
    """Strip 'Chapter N:' / 'Appendix A —' from the first H1 so memoir's
    \\chapter (which already prints 'Chapter N' / 'Appendix A') isn't doubled."""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("# "):
            lines[i] = (CH_PREFIX if kind == "chapter" else APX_PREFIX).sub("# ", ln)
            break
    return "\n".join(lines)


def raw_latex(s: str) -> str:
    return "```{=latex}\n" + s + "\n```\n"


def copy_figures_preamble() -> None:
    if not plates.STYLES_SOURCE.exists():
        raise SystemExit(f"missing symbol library: {plates.STYLES_SOURCE}")
    shutil.copyfile(plates.STYLES_SOURCE, plates.STYLES)
    print(f"copied figures_preamble.tex from {plates.STYLES_SOURCE.parent.name}/")


def patch_preamble() -> None:
    p = SRC_PREAMBLE.read_text(encoding="utf-8")
    p = p.replace(r"\setmonofont{Consolas}[Scale=0.92]",
                  r"\setmonofont{DejaVu Sans Mono}[Scale=0.82]")
    p = p.replace("Thinking in Cognitive Architecture", "The Component Companion")
    p = p.replace("A Universal Framework for Humans, AI, and Biological Minds",
                  "Illustrated Electrical Symbols and the Cognitive Roles They Map To")
    p = p.replace(
        "cognitive architecture, CAS, AI alignment, topos theory, Noetic Compass",
        "CAS, component library, cognitive circuits, electrical symbols, PCBA")
    # This guide has no numbered sections of its own; chapters carry the structure.
    p = p.replace(r"\setcounter{secnumdepth}{1}", r"\setcounter{secnumdepth}{0}")
    p = p.replace(r"\setcounter{tocdepth}{1}", r"\setcounter{tocdepth}{0}")
    p = p.replace(r"\usepackage{fancyvrb}",
                  "\\usepackage{fancyvrb}\n\\usepackage{fvextra}\n"
                  "\\fvset{breaklines=true,breakanywhere=true,fontsize=\\footnotesize}")
    extra = (
        "\\newunicodechar{∝}{\\ensuremath{\\propto}}\n"
        "\\newunicodechar{≫}{\\ensuremath{\\gg}}\n"
        "\\newunicodechar{≪}{\\ensuremath{\\ll}}\n"
        "\\newunicodechar{⇄}{\\ensuremath{\\rightleftarrows}}\n"
        "\\newunicodechar{ₙ}{\\textsubscript{n}}\n"
        "\\newunicodechar{ₖ}{\\textsubscript{k}}\n"
        "\\newunicodechar{ᵢ}{\\textsubscript{i}}\n"
        "\\newunicodechar{ⱼ}{\\textsubscript{j}}\n"
        "\\newunicodechar{ₘ}{\\textsubscript{m}}\n"
        "% --- Custom math commands used by the manuscript -----------------------\n"
    )
    p = p.replace(
        "% --- Custom math commands used by the manuscript -----------------------\n",
        extra, 1)
    p += (
        "\n% --- Companion build: overfull-box mitigation ---\n"
        "\\usepackage{etoolbox}\n"
        "\\setlength{\\emergencystretch}{3em}\n"
        "\\AtBeginEnvironment{longtable}{\\footnotesize}\n"
        "\\AtBeginEnvironment{tabular}{\\small}\n"
        "\\appto\\UrlBreaks{\\do\\^\\do\\|\\do\\<\\do\\>\\do\\_}\n"
        "\n% --- Companion build: TikZ figure styles (copied symbol library) ---\n"
        "\\input{figures_preamble.tex}\n"
    )
    (BUILD / "preamble_companion.tex").write_text(p, encoding="utf-8")


def build_front_prose() -> None:
    fm = (BOOK / "00_Front_Matter.md").read_text(encoding="utf-8")
    idx = fm.find("## Preface")
    front = fm[idx:] if idx >= 0 else fm
    front = re.sub(r"^##\s+Preface.*$", "# Preface {-}", front, count=1, flags=re.M)
    front = re.sub(r"^##\s+How to Use This Guide.*$", "# How to Use This Guide {-}",
                   front, count=1, flags=re.M)
    front = re.sub(r"^##\s+How to Read These Plates.*$", "# How to Read These Plates {-}",
                   front, count=1, flags=re.M)
    (BUILD / "front_prose.md").write_text(front.rstrip() + "\n", encoding="utf-8")


def build_main_body() -> None:
    out = []
    for title, sub, files in PARTS:
        t = title.replace("&", r"\&")
        s = sub.replace("&", r"\&")
        out.append(raw_latex(r"\part[" + t + "]{" + t
                             + r"\\[0.45em]{\large\upshape " + s + "}}"))
        for fname in files:
            txt = (BOOK / fname).read_text(encoding="utf-8")
            out.append(strip_h1_prefix(txt, "chapter").strip())
            out.append("\n")
    out.append(raw_latex("\\appendix"))
    for fname in APPENDICES:
        txt = (BOOK / fname).read_text(encoding="utf-8")
        out.append(strip_h1_prefix(txt, "appendix").strip())
        out.append("\n")
    (BUILD / "main_body.md").write_text("\n\n".join(out) + "\n", encoding="utf-8")


def main() -> None:
    BUILD.mkdir(exist_ok=True)
    copy_figures_preamble()
    patch_preamble()
    build_front_prose()
    build_main_body()
    print("OK: wrote preamble_companion.tex, front_prose.md, main_body.md to", BUILD)


if __name__ == "__main__":
    main()
