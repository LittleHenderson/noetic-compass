#!/usr/bin/env python3
"""
Assemble the CAS PCBA Engineer book into pandoc-ready Markdown + a patched
XeLaTeX preamble, ready to compile to a designed 6x9 PDF via memoir/XeLaTeX.

Outputs into build/:
  - preamble_pcba.tex   (patched copy of the proven CAS manuscript preamble)
  - front_prose.md      (Preface + How to Use This Book, unnumbered front matter)
  - main_body.md        (5 parts of chapters + appendices, with \part / \appendix)
"""
import re
from pathlib import Path

BOOK = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\book\CAS_PCBA_Engineer")
BUILD = BOOK / "build"
SRC_PREAMBLE = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\book\publishing\latex\preamble.tex")

PARTS = [
    ("Foundations", "Learning to Read the Schematic", [
        "Chapter_01_Why_Build_Cognitive_Circuits.md",
        "Chapter_02_CAS_Notation_in_One_Chapter.md",
        "Chapter_03_The_Transistor_That_Changed_Everything.md",
        "Chapter_04_Your_First_Cognitive_Circuit.md",
    ]),
    ("The Component Library", "Every Part in the Bin", [
        "Chapter_05_Resistors.md",
        "Chapter_06_Capacitors.md",
        "Chapter_07_Inductors.md",
        "Chapter_08_Diodes.md",
        "Chapter_09_CJT_Deep_Dive.md",
        "Chapter_10_Special_Purpose_Components.md",
    ]),
    ("Circuit Design", "Putting Components to Work", [
        "Chapter_11_Amplifiers.md",
        "Chapter_12_Filters.md",
        "Chapter_13_Oscillators.md",
        "Chapter_14_Power_Management.md",
        "Chapter_15_Mixed_Signal_Design.md",
        "Chapter_16_Feedback_Systems.md",
    ]),
    ("Cognitive Circuit Boards", "Full System Designs", [
        "Chapter_17_CCB_Design_Process.md",
        "Chapter_18_CSB_Cognitive_Safety_Board.md",
        "Chapter_19_COB_Cognitive_Oscillator_Board.md",
        "Chapter_20_CDAB_Differential_Amplifier_Board.md",
        "Chapter_21_CMB_Cognitive_Memory_Board.md",
        "Chapter_22_CPMB_Power_Management_Board.md",
    ]),
    ("Deployment & Governance", "From Breadboard to Production", [
        "Chapter_23_Testing_Cognitive_Circuits.md",
        "Chapter_24_Debugging_Cognitive_Circuits.md",
        "Chapter_25_Production_Deployment.md",
        "Chapter_26_Governance.md",
    ]),
]

APPENDICES = [
    "Appendix_A_Notation_Quick_Reference.md",
    "Appendix_B_Component_Datasheets.md",
    "Appendix_C_CCDL_Language_Reference.md",
    "Appendix_D_CCB_Reference_Designs.md",
    "Appendix_E_Exercise_Answers.md",
    "Appendix_F_Lab_Setup_Guide.md",
    "Appendix_G_Glossary.md",
    "Appendix_H_Further_Reading.md",
    "Appendix_I_CAS_Ohm_Measurement_and_Calibration.md",
]

CH_PREFIX = re.compile(r"^#\s+Chapter\s+\d+\s*[:\-—]\s*")
APX_PREFIX = re.compile(r"^#\s+Appendix\s+[A-Z]\s*[:\-—–]\s*")


def strip_h1_prefix(text: str, kind: str) -> str:
    """Strip 'Chapter N:' / 'Appendix X —' from the first H1 so memoir's
    \\chapter (which already prints 'Chapter N' / 'Appendix A') isn't doubled."""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("# "):
            if kind == "chapter":
                lines[i] = CH_PREFIX.sub("# ", ln)
            else:
                lines[i] = APX_PREFIX.sub("# ", ln)
            break
    return "\n".join(lines)


def raw_latex(s: str) -> str:
    return "```{=latex}\n" + s + "\n```\n"


def build_front_prose() -> None:
    fm = (BOOK / "00_Front_Matter.md").read_text(encoding="utf-8")
    idx = fm.find("## Preface")
    front = fm[idx:] if idx >= 0 else fm
    # Promote the two front sections to unnumbered chapters.
    front = re.sub(r"^##\s+Preface.*$", "# Preface {-}", front, count=1, flags=re.M)
    front = re.sub(r"^##\s+How to Use This Book.*$", "# How to Use This Book {-}",
                   front, count=1, flags=re.M)
    # Drop any trailing horizontal rule.
    front = front.rstrip().rstrip("-").rstrip()
    (BUILD / "front_prose.md").write_text(front + "\n", encoding="utf-8")


def build_main_body() -> None:
    out = []
    for part_title, part_sub, files in PARTS:
        t = part_title.replace("&", r"\&")
        s = part_sub.replace("&", r"\&")
        # memoir already prints "Part I"; give it only the descriptive name plus a
        # tagline folded into the title, and a short [..] form for the TOC/headers.
        part_line = (r"\part[" + t + "]{" + t
                     + r"\\[0.45em]{\large\upshape " + s + "}}")
        out.append(raw_latex(part_line))
        for fname in files:
            txt = (BOOK / fname).read_text(encoding="utf-8")
            out.append(strip_h1_prefix(txt, "chapter").strip())
            out.append("\n")
    # Appendices: switch to letter numbering, unnumbered part divider.
    out.append(raw_latex(
        "\\appendix\n\\part*{Appendices}\n"
        "\\addcontentsline{toc}{part}{Appendices}"))
    for fname in APPENDICES:
        txt = (BOOK / fname).read_text(encoding="utf-8")
        out.append(strip_h1_prefix(txt, "appendix").strip())
        out.append("\n")
    # Back matter: an unnumbered chapter, so it does not take an appendix letter.
    author = BOOK / "About_the_Author.md"
    if author.exists():
        body = author.read_text(encoding="utf-8")
        body = re.sub(r"^#\s+About the Author\s*$", "", body, count=1, flags=re.M)
        out.append(raw_latex(
            "\\backmatter\n"
            "\\chapter*{About the Author}\n"
            "\\addcontentsline{toc}{chapter}{About the Author}\n"
            "\\markboth{ABOUT THE AUTHOR}{ABOUT THE AUTHOR}"))
        out.append(body.strip())
        out.append("\n")
    # Index, built from the \index marks publishing/build_indexes.py inserts
    # into body.tex after pandoc.
    out.append(raw_latex("\\printindex"))
    out.append("\n")
    (BUILD / "main_body.md").write_text("\n\n".join(out) + "\n", encoding="utf-8")


def patch_preamble() -> None:
    p = SRC_PREAMBLE.read_text(encoding="utf-8")
    # Broader-Unicode mono font for CAS code blocks (Greek/arrows/operators).
    p = p.replace(r"\setmonofont{Consolas}[Scale=0.92]",
                  r"\setmonofont{DejaVu Sans Mono}[Scale=0.82]")
    # Retitle everything that says the old book name.
    p = p.replace("Thinking in Cognitive Architecture", "CAS PCBA Engineer")
    # hyperref metadata refresh
    p = p.replace("A Universal Framework for Humans, AI, and Biological Minds",
                  "Designing Cognitive Circuits with the Cognitive Architecture System")
    p = p.replace(
        "cognitive architecture, CAS, AI alignment, topos theory, Noetic Compass",
        "CAS, CJT, cognitive circuit board, AI safety, PCBA, CCDL")
    # Unnumbered sections (book has many short ## sections); chapters/parts still numbered.
    p = p.replace(r"\setcounter{secnumdepth}{1}", r"\setcounter{secnumdepth}{0}")
    p = p.replace(r"\setcounter{tocdepth}{1}", r"\setcounter{tocdepth}{0}")
    # fvextra: line-breaking code blocks so long CCDL/ASCII lines fit the 6x9 measure.
    p = p.replace(r"\usepackage{fancyvrb}",
                  "\\usepackage{fancyvrb}\n\\usepackage{fvextra}\n"
                  "\\fvset{breaklines=true,breakanywhere=true,fontsize=\\footnotesize}")
    # A few CAS/math glyphs the mono+body fonts lack -> route through math mode.
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
    # Global typographic polish: let justified prose stretch as a last resort
    # (kills most overfull boxes from long inline CAS literals), and shrink the
    # many wide datasheet tables so their columns fit the 6x9 measure.
    p += (
        "\n% --- CAS PCBA Engineer build: overfull-box mitigation ---\n"
        "\\usepackage{etoolbox}\n"
        "\\setlength{\\emergencystretch}{3em}\n"
        "\\AtBeginEnvironment{longtable}{\\footnotesize}\n"
        "\\AtBeginEnvironment{tabular}{\\small}\n"
        "\\appto\\UrlBreaks{\\do\\^\\do\\|\\do\\<\\do\\>\\do\\_}\n"
    )
    # --- TikZ vector schematics (replace the ASCII block diagrams) ---------
    # figures_preamble.tex is a hand-written, preamble-safe file (TikZ + color
    # defs + reusable block/flow \tikzset styles) used by the {=latex} figure
    # blocks embedded in chapters 3, 18, 19, 20, 21, 22, 25.
    p += (
        "\n% --- CAS PCBA Engineer build: TikZ figure styles ---\n"
        "\\input{figures_preamble.tex}\n"
    )
    (BUILD / "preamble_pcba.tex").write_text(p, encoding="utf-8")


def main() -> None:
    BUILD.mkdir(exist_ok=True)
    patch_preamble()
    build_front_prose()
    build_main_body()
    print("OK: wrote preamble_pcba.tex, front_prose.md, main_body.md to", BUILD)


if __name__ == "__main__":
    main()
