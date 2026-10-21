# CENSUS 1 — recipe lines that wide reader v5 refuses (counts only; 2026-10-20 PDT; laptop; 0 USD)

Owner word: "Yes, run both free censuses on the laptop at 0 USD ... Counts only; STOP at the floors." No recipe text, line
text, id or title was printed or written. Program `census_gap_lines.py`; output `CENSUS_GAP_LINES.json` (sha256
`4011c41a6704898d4de9ad41ca849394faa735acef24db50222e2336f2b9114d`); 1.9 s.

## Verdict: **PASS_FLOOR** (an upper bound; the custodian's key rule and spent-exam exclusions were not applied)

| Count | PG (Gutenberg cookbooks) | WB (Wikibooks) | Both |
|---|---|---|---|
| Recipes in the frames | 10,368 | 3,318 | **13,686** |
| Ingredient lines | 59,848 | 26,443 | 86,291 |
| Lines read by reader v5 | 56,818 | 19,404 | 76,222 (88.33%) |
| Lines refused | 3,030 | 7,039 | **10,069** (11.67%) |
| Recipes with every line read | 8,767 | 794 | 9,561 |
| Recipes with no line read | 45 | 217 | 262 |
| Recipes mixed (some read, some refused) | 1,556 | 2,307 | 3,863 |
| Recipes over 10 lines (the brain's limit) | 489 | 771 | 1,260 |
| **Gap recipes** (mixed, at most 10 lines) | 1,385 | 1,645 | **3,030** |
| **Refused lines inside gap recipes** | 1,744 | 3,701 | **5,445** (floor 256) |

Gap recipes by number of refused lines: PG 1 line 1,126 / 2 lines 192 / 3 lines 45 / 4+ 22; WB 1 line 627 / 2 lines 466
/ 3 lines 275 / 4 lines 143 / 5+ 134.

## Why reader v5 refuses (all 10,069 refused lines; inside gap recipes in brackets)

| Code | Lines | What it means in plain words |
|---|---|---|
| NO_AMOUNT | 5,164 (2,581) | the line names an ingredient with no number ("salt", "pepper to taste") |
| NO_NAME | 1,746 (588) | an amount with no ingredient word the binder knows |
| UNIT_NOT_IN_TABLE | 1,662 (1,217) | a unit word outside the 20-unit table ("pinch", "slice", "can", "bunch") |
| AMOUNT_IS_A_RANGE | 1,305 (922) | "2 to 3 cups" |
| AMOUNT_HAS_TWO_PARTS | 119 (94) | "1 cup plus 2 tablespoons", "a or b" |
| UNREAD_CLAUSE | 30 (16) | a clause after a separator the reader does not read |
| AMOUNT_APPROXIMATE | 26 (16) | "about 2 cups" |
| AMOUNT_RELATIVE | 17 (11) | a relative form v5 does not hold ("same quantity of") |

## What this means for the packet (reading, not a claim)

- The gap stratum exists in quantity: 5,445 refused lines in 3,030 recipes against a floor of 256, before the custodian's
  key rule and the spent-exam exclusions (X-REAL 128, RB-W1T c46 + c47, X6, X6v3: at most a few hundred recipes).
- The gap is NOT the relative-amount family that wave 6 tripped on (17 lines in the whole frame). It is four plain families:
  lines with no number, units outside the table, ranges, and names the binder does not know. Three of these are about
  what the brain may hold (no amount = not a requirement; a range = not an exact requirement; an unknown unit = no
  conversion), not about reading. A shape ear would at best label such a line as NOTE or ASK; it cannot make "salt to taste"
  a witnessed requirement. So the design's hope that an ear turns refused lines into learned recipes applies mainly to
  NO_NAME (1,746) and UNIT_NOT_IN_TABLE (1,662), and the latter is a table question, not a model question.
- Honest reading for the owner: the floor passes, but the census moves the design's expected gain down. OPEN_QUESTIONS
  gains Q7: whether to widen the unit table (deterministic, 0 USD) and teach the brain a NOTE line (an ingredient with
  no exact amount is recorded as present, never as a requirement) BEFORE any ear is trained; both would shrink the gap
  the ear is meant to fill.

## Negatives kept
- Reader v5 reads 88.33% of lines; 11.67% are refused, 262 recipes entirely.
- WB (Wikibooks) is much harder than PG: 26.62% of lines refused vs 5.06%.
- No key rule applied: some gap recipes have no ANSWER key and would leave the frame at a draw.

## Re-census after stage 1c (2026-10-20 PDT; owner word "build both"; laptop; 0 USD; counts only; ENGINEERED-NOT-VALIDATED)

Same program, same frames, same reader file (`helm_wide_turn.py` with stage 1c inside it, switch OFF then ON). 2.1 s each. No text printed or written.

| Count | OFF (= census 1) | ON (`WIDE_UNITS_NOTE`) |
|---|---|---|
| Lines read | 76,222 (88.33%) | 82,637 (95.77%) |
| Lines refused | 10,069 (11.67%) | 3,654 (4.23%) |
| PG / WB lines refused | 3,030 / 7,039 | 1,909 / 1,745 |
| Recipes with every line read / none read / mixed | 9,561 / 262 / 3,863 | 11,737 / 30 / 1,919 |
| Gap recipes / refused lines inside them (floor 256) | 3,030 / 5,445 PASS_FLOOR | 1,477 / 1,974 PASS_FLOOR |

| Code | OFF | ON | Inside gap recipes OFF → ON |
|---|---|---|---|
| NO_AMOUNT | 5,164 | 291 | 2,581 → 206 |
| UNIT_NOT_IN_TABLE | 1,662 | 0 | 1,217 → 0 |
| NO_NAME | 1,746 | 1,849 | 588 → 662 |
| AMOUNT_IS_A_RANGE | 1,305 | 1,309 | 922 → 955 |
| AMOUNT_HAS_TWO_PARTS | 119 | 125 | 94 → 100 |
| UNREAD_CLAUSE | 30 | 30 | 16 → 18 |
| AMOUNT_APPROXIMATE | 26 | 29 | 16 → 19 |
| AMOUNT_RELATIVE | 17 | 17 | 11 → 13 |
| SAME_INGREDIENT_TWICE | 0 | 4 | 0 → 1 |

What "read" means ON (a second count, same frames): of 82,637 lines read, 74,574 carry an amount in a sized unit, 279 of them in a widened unit (dozen 109, gallon 90, liter 68, deciliter 8, fluid ounce 3, centiliter 1); 8,042 lines are NOTE-only and 21 carry a note beside an amount line; 8,584 NOTE lines in all: 5,384 with no amount, 1,946 in an own-count unit that OFF read as an exact own count (clove 413, slice 367, can 358, pinch 333, package 164, teacup 157, saltspoon 154; bunch and square 0), 1,254 in 62 distinct unsized unit words. So 279 lines gained an exact amount; the other 6,136 fewer refusals are honest presence, not requirements. The 116 lines that moved to another refusal code (NO_NAME +103, two-part +6, range +4, approximate +3, same-twice +4; UNREAD_CLAUSE and AMOUNT_RELATIVE unchanged) are lines that used to stop at NO_AMOUNT or UNIT_NOT_IN_TABLE and now reach a later check.

Files: `CENSUS_GAP_LINES_RERUN_OFF_20261020.json` (sha256 `e3325f5aac208b2b0c9089ad0088ce9b16b53401b895cc01b1923ab2b9fe6625`; every count equal to `CENSUS_GAP_LINES.json`; differs only in the embedded file hashes and the time stamp), `CENSUS_GAP_LINES_STAGE1C_ON_20261020.json` (sha256 `afa8ed5ce47525646a09f17a8d64a3880d848b8533a278f214e0b6c66ad82e84`). Correction to the table above: "pinch", "slice", "can", "bunch" are inside the 20-unit table as own-count units; the UNIT_NOT_IN_TABLE lines were the other unit words (stick, dozen, liter, gallon, dash, handful, ...).
