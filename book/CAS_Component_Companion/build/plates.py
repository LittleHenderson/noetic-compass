#!/usr/bin/env python3
"""Locate the plate and schematic figure blocks across the companion's chapters.

The guide's figures live in the numbered chapter files, not in one appendix
file, so every tool that reads them iterates the chapter list from here rather
than hard-coding a single path. `figures_preamble.tex` is copied from the main
volume's build directory by `companion_build.py`, so the symbol library has one
source of truth.
"""
from __future__ import annotations

import re
from pathlib import Path

BUILD = Path(__file__).resolve().parent
COMPANION = BUILD.parent
STYLES = BUILD / "figures_preamble.tex"
STYLES_SOURCE = (COMPANION.parent / "CAS_PCBA_Engineer" / "build"
                 / "figures_preamble.tex")

# Chapter order, which is also reading order.
CHAPTERS = [
    "00_Front_Matter.md",
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
    "Appendix_A_Design_Notes.md",
]

FIGURE_RE = re.compile(
    r"\\begin\{figure\}(?:\[[^]]*\])?\s*"
    r"(?P<body>.*?)"
    r"\\caption\{(?P<caption>.*?)\}"
    r"\\label\{fig:(?P<label>[^}]+)\}\s*"
    r"\\end\{figure\}",
    re.DOTALL,
)


def read_chapters() -> dict[str, str]:
    """{filename: text} for every chapter that exists."""
    out = {}
    for name in CHAPTERS:
        p = COMPANION / name
        if p.exists():
            out[name] = p.read_text(encoding="utf-8")
    return out


def all_text() -> str:
    return "\n".join(read_chapters().values())


def figures() -> list[tuple[str, re.Match]]:
    """[(chapter filename, match)] for every figure block, in reading order."""
    found = []
    for name, text in read_chapters().items():
        for m in FIGURE_RE.finditer(text):
            found.append((name, m))
    return found
