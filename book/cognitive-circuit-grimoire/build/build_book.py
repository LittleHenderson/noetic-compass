"""Assemble The Cognitive Circuit Grimoire into pandoc-ready Markdown.

Mirrors book/CAS_PCBA_Engineer/build/build_book.py, which is the proven path for
this series: assemble -> pandoc -> postprocess -> index marks -> xelatex ->
makeindex -> xelatex -> xelatex.

Ordering matters and is the thing most easily got wrong: index marks go in AFTER
pandoc and BEFORE the first xelatex pass, and \\index{} must never land inside a
moving argument (a heading, caption or label) or it corrupts the .aux.
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

# Front matter that runs as prose before \mainmatter.
FRONT_PROSE = [
    "02_preface.md",
    "03_how_to_use.md",
    "04_quickstart.md",
]

# (Part title, part tagline, [chapter files in order])
PARTS: list[tuple[str, str, list[str]]] = [
    ("Foundations",
     "The substrate, the notation, and the transistor at the centre of it",
     ["ch01_the_landscape.md",
      "ch02_cas_notation.md",
      "ch03_cjt.md",
      "ch04_cas_ohms_law.md",
      "ch05_st_johns_equation.md"]),
    ("The Component Library",
     "Every part on the bench, with its datasheet and its failure modes",
     ["ch06_resistors.md",
      "ch07_capacitors.md",
      "ch08_diodes.md",
      "ch09_inductors.md",
      "ch10_cjt_deep_dive.md",
      "ch11_special_components.md"]),
    ("The Board Catalog",
     "Nine boards, each with a schematic, a bill of materials, and a counter-circuit",
     ["ch12_reading_a_ccb.md",
      "ch13_ccb_d_desire.md",
      "ch14_ccb_h_hyperstition.md",
      "ch15_ccb_o_overton.md",
      "ch16_ccb_mk_mind_control.md",
      "ch17_ccb_hyp_hypnosis.md",
      "ch18_ccb_adv_advertising.md",
      "ch19_ccb_pw_psychological_warfare.md",
      "ch20_ccb_self_programming.md"]),
    ("Operations",
     "Gating, measuring, calibrating, and refusing",
     ["ch21_rpm_gate.md",
      "ch22_quantitative_table.md",
      "ch23_st_johns_advanced.md",
      "ch24_csb_safety_board.md"]),
]

APPENDICES = [
    "appendix_a_notation_card.md",
    "appendix_b_ccdl_reference.md",
    "appendix_c_component_datasheets.md",
    "appendix_d_board_designs.md",
    "appendix_e_tks_crosswalk.md",
    "appendix_f_st_johns_worksheet.md",
    "appendix_g_quantitative_table.md",
    "appendix_h_exercise_answers.md",
    "appendix_i_glossary.md",
    "appendix_j_further_reading.md",
    "appendix_k_tootra_oath.md",
    "appendix_l_mathematical_foundations.md",
    "appendix_m_safety_checklist.md",
]


def raw_latex(s: str) -> str:
    return "```{=latex}\n" + s + "\n```"


def strip_h1_prefix(text: str, kind: str) -> str:
    """Drop a leading '# CHAPTER n' banner so the real title becomes the heading.

    The drafts carry two shapes: '# CHAPTER 16' then '## CCB-MK — ...', and a
    plain '# Title'. Normalise both to a single H1 that pandoc turns into
    \\chapter{}.
    """
    lines = text.split("\n")
    out, seen_banner = [], False
    for line in lines:
        m = re.match(r"^#\s+(CHAPTER|APPENDIX)\s+[0-9A-M]+\s*$", line.strip(), re.I)
        if m and not seen_banner:
            seen_banner = True
            continue
        if seen_banner and re.match(r"^##\s+\S", line):
            out.append("# " + line.lstrip("# ").strip())
            seen_banner = False
            continue
        out.append(line)
    return "\n".join(out)


def missing(paths: list[Path]) -> list[str]:
    return [p.name for p in paths if not p.exists()]


def read_normalized(path: Path, kind: str) -> str:
    """Read one chapter/appendix and require one printable top-level title."""
    raw = path.read_text(encoding="utf-8")
    bannered = bool(re.search(
        r"(?m)^#\s+(?:CHAPTER|APPENDIX)\s+[0-9A-M]+\s*$",
        raw,
        re.I,
    ))
    text = strip_h1_prefix(raw, kind).strip()
    # Ordinary bannered sources use H3 for their n.1/A.1 sections because the
    # source keeps both a '# CHAPTER n' banner and an H2 title. Once the banner
    # is removed and the title becomes H1, promote H3+ by one level so pandoc
    # emits real sections. Appendix H deliberately retains later H2 chapter
    # groups and H3 answers; the presence of those H2s preserves that hierarchy.
    if bannered and not re.search(r"(?m)^##\s+\S", text):
        text = re.sub(
            r"(?m)^(#{3,})(?=\s)",
            lambda match: match.group(1)[1:],
            text,
        )
    headings = re.findall(r"(?m)^#\s+\S.*$", text)
    if len(headings) != 1:
        raise ValueError(
            f"{path.name}: expected exactly one normalized H1, found "
            f"{len(headings)} ({headings})"
        )
    return text


def build_front_prose() -> None:
    parts = []
    for fname in FRONT_PROSE:
        p = MS / fname
        if not p.exists():
            raise FileNotFoundError(
                f"required front-matter source is missing: {p}"
            )
        parts.append(p.read_text(encoding="utf-8").strip())
    (BUILD / "front_prose.md").write_text("\n\n".join(parts) + "\n", encoding="utf-8")


def build_main_body() -> list[str]:
    out: list[str] = []
    absent: list[str] = []

    for part_title, part_sub, files in PARTS:
        t = part_title.replace("&", r"\&")
        s = part_sub.replace("&", r"\&")
        out.append(raw_latex(
            r"\part[" + t + "]{" + t
            + r"\\[0.45em]{\large\upshape " + s + "}}"))
        for fname in files:
            p = MS / fname
            if not p.exists():
                absent.append(fname)
                continue
            out.append(read_normalized(p, "chapter"))
            out.append("\n")

    out.append(raw_latex(
        "\\appendix\n\\part*{Appendices}\n"
        "\\addcontentsline{toc}{part}{Appendices}"))
    for fname in APPENDICES:
        p = MS / fname
        if not p.exists():
            absent.append(fname)
            continue
        out.append(read_normalized(p, "appendix"))
        out.append("\n")

    author = MS / "about_the_author.md"
    if author.exists():
        body = re.sub(r"^#\s+About the Author\s*$", "", author.read_text(encoding="utf-8"),
                      count=1, flags=re.M)
        out.append(raw_latex(
            "\\backmatter\n\\chapter*{About the Author}\n"
            "\\addcontentsline{toc}{chapter}{About the Author}\n"
            "\\markboth{ABOUT THE AUTHOR}{ABOUT THE AUTHOR}"))
        out.append(body.strip())
        out.append("\n")
    else:
        absent.append("about_the_author.md")

    out.append(raw_latex("\\printindex"))
    (BUILD / "main_body.md").write_text("\n\n".join(out) + "\n", encoding="utf-8")

    total = sum(len(f) for _, _, f in PARTS) + len(APPENDICES) + 1
    print(f"  assembled {total - len(absent)}/{total} source files")
    if absent:
        print(f"  NOT YET WRITTEN ({len(absent)}):")
        for a in absent:
            print(f"     - {a}")
    return absent


def main() -> int:
    build_front_prose()
    absent = build_main_body()
    body = (BUILD / "main_body.md").read_text(encoding="utf-8")
    print(f"  main_body.md: {len(body.split()):,} words")
    return 1 if absent else 0


if __name__ == "__main__":
    raise SystemExit(main())
