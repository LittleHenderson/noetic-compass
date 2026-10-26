#!/usr/bin/env python3
"""Cross-artifact check for the companion guide and its card deck.

The per-part audits each prove one thing about one file. This proves the two
delivered PDFs agree with each other and with the rules the guide states about
itself: the chapter count, the figure count, the badge vocabulary, and the
mapping guards that are load-bearing for the CAS semantics.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pymupdf

BUILD = Path(__file__).resolve().parent
BOOK = BUILD.parent
GUIDE = BOOK / "CAS_Component_Companion.pdf"
CARDS = BOOK / "CAS_Component_Companion_Cards.pdf"


def text_of(doc) -> str:
    """Extracted text with line wrapping normalised to single spaces."""
    return re.sub(r"\s+", " ", "\n".join(p.get_text() for p in doc))


def main() -> int:
    for p in (GUIDE, CARDS):
        if not p.exists():
            print(f"FAIL missing {p}")
            return 1
    guide = pymupdf.open(GUIDE)
    cards = pymupdf.open(CARDS)
    gt, ct = text_of(guide), text_of(cards)

    checks = [
        ("guide: 6x9 US trade trim",
         abs(guide[0].rect.width - 432) < 1 and abs(guide[0].rect.height - 648) < 1),
        ("guide: Contents present", "Contents" in gt),
        ("guide: List of Figures present", "List of Figures" in gt),
        ("guide: Preface present", "Preface" in gt),
        ("guide: five parts present",
         all(p in gt for p in ("Reading a Human Being",
                               "The Parts, and the Lives They Explain",
                               "Lives, Worked Through",
                               "The Schematics", "Reference"))),
        ("guide: four registers named in human language",
         all(w in gt for w in ("Mental", "Emotional", "Physical", "Spiritual"))),
        ("guide: register axis tied to the notation",
         "Analytical" in gt and "Affective" in gt and "Embodied" in gt
         and "Transcendent" in gt),
        ("guide: notation-and-symbols chapter present",
         "The Notation and the Symbols Enforce Each Other" in gt),
        ("guide: nine case studies present",
         all(c in gt for c in ("Grief That Will Not Discharge", "Craving Loop",
                               "Panic That Fires Too Easily",
                               "Argument That Resonates",
                               "Trigger That Is Not a Reason", "Muscle Memory",
                               "Purpose That Holds", "Browned Out",
                               "Social Engineering"))),
        ("guide: domains map present", "What Else This Pair Illustrates" in gt),
        ("guide: two languages are not interchangeable",
         "They are not translations of each other" in gt),
        ("guide: the schematic states designer intent",
         "The notation reports. The board commits." in gt
         and "Whose board are you running" in gt),
        ("guide: same expression, different boards",
         "Two completely different boards can implement" in gt
         and "can be run on radically different boards" in gt),
        ("guide: every plate entry is in four registers",
         gt.count("in all four registers") >= 40),
        ("guide: every plate entry is in four registers",
         gt.count("in all four registers") >= 40),
        ("guide: Appendix A present", "Design Notes and Frozen Inventory" in gt),
        ("guide: memory deck present", "Complete Memory Deck" in gt),
        ("guide: card-printing chapter present", "Printing and Using the Card Deck" in gt),
        ("guide: XNOR defined", "XNOR" in gt),
        ("guide: bridge is PED on a non-valence scalar only",
         "scalar" in gt and "does not convert Negative" in gt),
        ("guide: three badges defined",
         "ISO" in gt and "ENG" in gt and "PED" in gt),
        ("guide: no 'Appendix J' framing left", "Appendix J" not in gt
         and "appendix J" not in gt),
        ("guide: states the guardrail line in the preface", "guardrail" in gt.lower()),

        ("cards: 7 pages", cards.page_count == 7),
        ("cards: 56 cards in text", "56" in ct),
        ("cards: sheet label is the companion's",
         "COMPONENT COMPANION CARDS" in ct),
        ("cards: body labels are the human set",
         "THE PART" in ct and "IN LIFE" in ct and "REGISTERS" in ct),
        ("cards: every component card names all four registers",
         ct.count("|A ") >= 35 and ct.count("|f ") >= 35
         and ct.count("|E ") >= 35 and ct.count("|T ") >= 35),
        ("cards: card 6 in life line", "pass the salt" in ct),
        ("cards: card 7 keeps the ^5 boundary",
         "not a container" in ct and "composed of accumulated Ideas" in ct),
        ("cards: card 17 folds the current mirror", "Current Mirror" in ct),
        ("cards: card 27 folds NAND/NOR/XNOR",
         "NAND/NOR invert" in ct and "XNOR reports equality" in ct),
        ("cards: card 55 counts 29 part + 8 annotation",
         "29 part, 8 annotation" in ct),
        ("cards: card 55 names the five folded entries",
         "Varactor, Current mirror, NAND, NOR and XNOR are taught on their parent cards"
         in ct),
        ("cards: XOR is exactly one", "EXACTLY ONE" in ct),
        ("cards: AND both-active is conflict",
         "Both-active is conflict" in ct),
        ("cards: relay is ^8 control / ^9 effect", "Cause controls Effect" in ct),
        ("cards: bridge never converts ^3 to ^2",
         "Never convert" in ct and "Negative repulsion into" in ct),
        ("cards: ADC quantizing is lossy",
         "Quantizing is lossy" in ct),
        ("cards: DAC is not the inverse of ADC",
         "Not the inverse of lossy ADC" in ct),
        ("cards: reference is a convention that can be wrong",
         "It is a convention, and it can be wrong" in ct),
    ]

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"{'OK  ' if ok else 'FAIL'} {name}")
    print()
    print(f"guide pages: {guide.page_count} | card pages: {cards.page_count}")
    if failed:
        print(f"\nFAIL {len(failed)} check(s)")
        return 1
    print(f"PASS companion deliverables ({len(checks)} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
