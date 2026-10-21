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
