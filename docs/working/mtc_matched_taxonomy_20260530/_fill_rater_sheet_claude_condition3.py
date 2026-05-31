"""One-off: write Claude's blind rater fills into a filled copy of the Condition-3 sheet.

Claude rated each item from the PROMPT text + the 40-Element definition sheet
(`lsa_definition_sheet_40e_v0_1.md`) ONLY, reading the focused role's noetic
dynamic (verb phrase after "the one who ...") and its register adjective
(A=Spiritual, B=Mental, C=Emotional, D=Physical). The original sheet ships with
the answer leaked in both the item_id suffix and the chosen_label column; this
script IGNORES both and overwrites chosen_label with Claude's independent choice,
applied by ROW POSITION so no long item_id is transcribed by hand. The private
answer key (condition3_mp_answer_key_20260531.json) was NOT opened during rating.
Run, then score the FILLED file.
"""
from __future__ import annotations
import csv
from pathlib import Path

_HERE = Path(__file__).resolve().parent
SRC = _HERE / "condition3_mp_rater_sheet_20260531.csv"
DST = _HERE / "condition3_mp_rater_sheet_20260531_FILLED_claude.csv"

# Claude's blind choices, in the SAME order as the rows of SRC (40 items).
CHOICES = [
    "B4", "B2", "D8", "A8", "A6", "A7", "D4", "D1", "B9", "D5",
    "A3", "D3", "B8", "A5", "B3", "A1", "B5", "C5", "B10", "C6",
    "C4", "A9", "D6", "A10", "D9", "B7", "B1", "D7", "C3", "C2",
    "C10", "B6", "D10", "A4", "C1", "A2", "C8", "D2", "C9", "C7",
]


def main() -> int:
    rows = list(csv.DictReader(SRC.open(encoding="utf-8", newline="")))
    if len(rows) != len(CHOICES):
        raise SystemExit(f"row/choice mismatch: {len(rows)} rows vs {len(CHOICES)} choices")
    with DST.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["item_id", "prompt", "chosen_label", "confidence_1to5"])
        for r, choice in zip(rows, CHOICES):
            w.writerow([r["item_id"], r["prompt"], choice, 5])
    print(f"wrote {DST.name} ({len(rows)} rows, all rated)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
