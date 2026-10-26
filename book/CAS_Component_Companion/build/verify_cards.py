#!/usr/bin/env python3
"""Verify the frozen 56-card companion print master and delivered PDF."""
from __future__ import annotations

import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

BUILD = Path(__file__).resolve().parent
BOOK = BUILD.parent
TEX = BUILD / "companion_cards.tex"
PDF = BOOK / "CAS_Component_Companion_Cards.pdf"
LOG = BUILD / "companion_cards.log"


def fail(message: str) -> None:
    raise AssertionError(message)


def main() -> int:
    source = TEX.read_text(encoding="utf-8")
    log = LOG.read_text(encoding="utf-8", errors="replace") if LOG.exists() else ""

    cards = re.findall(r"\\(?:PCard|CCard)\{(\d+)\}\{([^{}]+)\}\{(ISO|ENG|PED)\}", source)
    numbers = [int(n) for n, _, _ in cards]
    if numbers != list(range(1, 57)):
        fail(f"card numbers are not exactly 1..56: {numbers}")
    if len(cards) != 56:
        fail(f"expected 56 cards, found {len(cards)}")

    classes = Counter(badge for _, _, badge in cards)
    if sum(classes.values()) != 56 or set(classes) - {"ISO", "ENG", "PED"}:
        fail(f"bad badge inventory: {dict(classes)}")
    for stale in ("{ISO / ENG}", "{ISO/ENG}", "{ISO after threshold}"):
        if stale in source:
            fail(f"hybrid badge survived: {stale}")

    if source.count(r"\CropFrame{") != 7:
        fail("expected seven sheet crop frames")
    if source.count(r"\null\newpage") != 6:
        fail("expected six page breaks between seven sheets")

    grouped = {
        35: "RAIL · Drive Supply",
        36: "REF · Reference Node",
        37: "TP · Probe",
        38: "SW · Switch / Enable",
        39: "M · Meter / CAS-Ohm",
        40: "NET · Typed Label",
        41: "Solid Arrow",
        42: "Dashed Arrow",
    }
    names = {int(n): name for n, name, _ in cards}
    for number, name in grouped.items():
        if names.get(number) != name:
            fail(f"grouped annotation card {number} mismatch: {names.get(number)!r}")

    semantic_guards = {
        "XOR exactly-one": "{XOR Gate}{ENG}",
        "AND both-active": "{C05 · Ambiguity Stabilizer}{ENG}",
        "photodiode Mind intake": "The output is a $^1$ intake",
        "bridge non-valence": "Never convert $^3$ Negative repulsion into $^2$ Positive attraction.",
        "CJT terminal caveat": "not universal BJT terminal identities",
        "op-amp arithmetic caveat": "Arithmetic minus is not Noetic involution",
        "reference caveat": "It is a convention, and it can be wrong",
        "ADC identity": "Quantizing is lossy",
        "DAC non-inverse": "Not the inverse of lossy ADC",
        "reachable fuse": "$0.05<0.1$ is load-bearing",
        "capacitor keeps the ^5 boundary": "not a container",
        "current mirror folded": "Folds Current Mirror",
        "NAND/NOR/XNOR folded": "NAND/NOR",
        "deck accounting names the folded five":
            "NAND, NOR and XNOR are taught on their parent cards",
    }
    for label, needle in semantic_guards.items():
        if needle not in source:
            fail(f"missing semantic guard: {label}")

    for needle in ("BridgeRectifier< ^2", "XOR< ^2", "Relay< control=^9", "Photodiode< stimulus -> ^0"):
        if needle in source:
            fail(f"forbidden stale semantic form: {needle}")

    if not PDF.exists():
        fail(f"missing delivered PDF: {PDF}")
    info = subprocess.run(["pdfinfo", str(PDF)], text=True, capture_output=True, check=True).stdout
    if not re.search(r"^Pages:\s+7\s*$", info, re.MULTILINE):
        fail("delivered PDF is not seven pages")
    if "612 x 792 pts" not in info:
        fail("delivered PDF is not US Letter")

    warning_patterns = {
        "overfull hbox": r"Overfull \\hbox",
        "overfull vbox": r"Overfull \\vbox",
        "underfull box": r"Underfull \\[hv]box",
        "missing character": r"Missing character",
        "LaTeX warning": r"LaTeX Warning",
        "font substitution": r"Font shape .* not available",
    }
    for label, pattern in warning_patterns.items():
        if re.search(pattern, log):
            fail(f"build log contains {label}")

    print("PASS companion card deck")
    print(f"cards=56 pages=7 per_page=8 badges={dict(classes)} size=US-Letter")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, subprocess.CalledProcessError) as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        raise SystemExit(1)
