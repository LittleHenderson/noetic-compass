#!/usr/bin/env python3
r"""
Correct chapter cross-references that point at the wrong chapter.

The book was renumbered at some earlier point and forward references were not
updated with it. The residue is systematic: oscillators are cited as Chapter 11
or 12 when they are Chapter 13; the op-amp as Chapter 6 or 10 when amplifiers
are Chapter 11; resistors as Chapter 6 when they are Chapter 5; inductors as
Chapter 8 when they are Chapter 7.

Every replacement below was verified by reading the sentence and comparing the
topic it names against the delivered chapter map (which the filenames encode).
Candidates that LOOKED wrong to a keyword scan but were actually right are
deliberately absent -- for example "the Cognitive Oscillator Board (Chapter 19)"
is correct, and "the series resistor from Chapter 4 and 5" is a range that
already includes the resistor chapter.

Idempotent and fail-loud: if a target string is missing, the script says so
rather than silently doing nothing.
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BOOK = Path(__file__).resolve().parent.parent

FIXES = [
    ("Chapter_02_CAS_Notation_in_One_Chapter.md",
     "oscillators and habit loops in Chapter 11",
     "oscillators and habit loops in Chapter 13",
     "oscillators are Chapter 13"),
    ("Chapter_04_Your_First_Cognitive_Circuit.md",
     "a multi-stage amplifier, which is Chapter 6.",
     "a multi-stage amplifier, which is Chapter 11.",
     "amplifiers are Chapter 11"),
    ("Chapter_11_Amplifiers.md",
     "and the oscillators of Chapter 12.",
     "and the oscillators of Chapter 13.",
     "oscillators are Chapter 13"),
    ("Chapter_12_Filters.md",
     "a **resistor** limits flow (Chapter 6)",
     "a **resistor** limits flow (Chapter 5)",
     "resistors are Chapter 5"),
    ("Chapter_12_Filters.md",
     "the operational amplifier you built in Chapter 10",
     "the operational amplifier you built in Chapter 11",
     "amplifiers are Chapter 11"),
    ("Chapter_12_Filters.md",
     "You met the inductor in Chapter 8",
     "You met the inductor in Chapter 7",
     "inductors are Chapter 7"),
    ("Chapter_12_Filters.md",
     "add an op-amp (Chapter 10)",
     "add an op-amp (Chapter 11)",
     "amplifiers are Chapter 11"),
    ("Chapter_12_Filters.md",
     "the resistor/capacitor/inductor chapters, Chapters 6–8.",
     "the resistor/capacitor/inductor chapters, Chapters 5–7.",
     "resistor/capacitor/inductor are Chapters 5-7"),
    ("Chapter_16_Feedback_Systems.md",
     "it's how you build oscillators (Chapter 11)",
     "it's how you build oscillators (Chapter 13)",
     "oscillators are Chapter 13"),
    # Chapter 20 pointed at a "Part IV introduction" the build never emits.
    ("Chapter_20_CDAB_Differential_Amplifier_Board.md",
     "is laid out in the Part IV introduction",
     "is laid out in Appendix D, Standard CCB Reference Designs",
     "no Part IV introduction is emitted; Appendix D is the board binder"),
]


def main() -> None:
    applied = skipped = missing = 0
    for fname, old, new, why in FIXES:
        p = BOOK / fname
        text = p.read_text(encoding="utf-8")
        if new in text and old not in text:
            print(f"  skip {fname[:44]:46s} already correct")
            skipped += 1
            continue
        if old not in text:
            print(f"  MISS {fname[:44]:46s} {old[:52]!r}")
            missing += 1
            continue
        p.write_text(text.replace(old, new), encoding="utf-8")
        print(f"  OK   {fname[:44]:46s} {why}")
        applied += 1
    print(f"\n{applied} corrected, {skipped} already right, {missing} not found")
    if missing:
        raise SystemExit("fix_xrefs: some targets no longer match the text")


if __name__ == "__main__":
    main()
