# CENSUS 2 — the draft 28-cell tag histogram over the c50 and RB-I3 records (counts only; 2026-10-20 PDT; laptop; 0 USD)

Owner word: "Yes, run both free censuses ... the 28-cell tag histogram over the c50 and RB-I3 records. Counts only; STOP
at the floors." Program `census_tags_28_cells.py` (the DRAFT rule table of DESIGN 1.2, DOM-1a..e); output
`CENSUS_TAGS_28_CELLS.json` (sha256 `2a8f1b824c5097893c717ebf3b2d3a92f52816252983b24aff63c044d1beb2e1`); 9.4 s. Only
status, reason, kind and Foundation words were read; no text field entered the report.

## Verdict: **STOP_NOT_EXERCISED** — 0 of 28 cells hold 8 or more items (floor 20 of 28)

| Count | Value |
|---|---|
| Records walked | 80 json files (c50 host output) + 624 json files (RB-I3 runs) |
| Receipt-like items (a status, reason, code, verdict or outcome word) | 172,437 |
| Items with a Foundation (F1-F7) but no Domain the draft rules can set | **101,718** (all RB-I3 drive-loop items; F1 14,594, F2 13,827, F3 15,117, F4 15,431, F5 14,077, F6 14,923, F7 13,551) |
| Items with a Domain but no Foundation | **70,719** (all brain, reader, voice and Eye receipts of c50: C 58,494, O 6,036, E 3,419, P 2,770) |
| Items with BOTH, hence a cell of the 28 | **0** |

The RB-I3 items' words are the Eye's choice reasons (`seeded_alternative` 40,878, `best_first` 28,314, `cyclic` 9,294,
`uniform` 9,293, `key_rotation` 4,805, `rb_today_refit` 4,647, `key_first` 4,289, `CLOSED` 104, `NEW_SESSION` 92): they say
how the Eye chose, not what kind of thing the item is. The wave-6 pairing files hold only per-Foundation totals (keys
`F1`..`F7`), not per-item records, so the c50 backlog cannot be tagged at all from the deliverable.

## What this means for the packet (reading, not a claim)

- Exactly the prerequisite the packet named: **today no record carries both a Foundation and a Domain.** The brain's
  receipts know what kind of thing happened (a lesson, a stock line, a verdict) and nothing about which Foundation it
  serves; the drive loop's items know their Foundation and nothing about their kind. Stage 1 (the `cas_address/1` field
  written at the moment a receipt or a backlog item is created, by the program that creates it) is not optional and
  cannot be done after the fact from these records.
- The draft Domain rules did set a Domain for 70,719 of the brain-side items (41% of all items) from status words alone;
  58,494 of them land in C (readings, lessons, answers, questions), 6,036 in O, 3,419 in E, 2,770 in P. If the Foundation
  were known for those, the cells would be unevenly filled, with C dominating: the honest limit the design named.
- Nothing is sealed; stage 1 is the next build, behind a switch, with H-OFF byte-identity as its gate. The 28-cell exam
  waits for stage 1 and a re-census on records that carry the address.

## Negatives kept
- 0 of 28 cells reachable from existing records; the floor fails by construction, not by a close count.
- The draft rule table maps choice words to UNTAGGED; a per-item kind field must be written by the drive loop itself.
