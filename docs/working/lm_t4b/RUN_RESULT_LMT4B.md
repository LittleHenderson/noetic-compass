# RUN_RESULT LM-T4b — LM-T4 rerun under a reader sealed before the run (2026-10-20 PDT, laptop MSI, 0 USD)

Owner's order (verbatim): "the LM-T4 corrected reading. rerun under a sealed reader with the bug fix".

Claim ceiling: **SYNTHETIC_ONLY**. FORM-only language claims (Controlled CAS English v0.1c-R is a grammar, not a learned
parser). No HELM claim. **No RPA-crossing claim** (owner ruling 2026-10-15 "RPA IS ATLAS": LM-T4 and this rerun read S0
as the RPM chain per CJT, not as the Recursive Possibility Atlas). Parameters learned: 0. Spend: 0 USD. No network, no AWS,
no LLM call.

Every number below was computed by the sealed reader `merge_t4b.py` (sha256
`382033ca52735f9b3a6dfedfd1316a716bc01360e8c794d8681328470a0d0db5`, sealed in the package zip
`f93ceba8601ccc579331d1a2c930ac44a857eeba87c3ff6591ac14e8e729efe2` BEFORE any part ran) from the raw counts in
`runs/LM_T4_MSI_P11..P18/RESULTS_T4.json`; this file only copies them.

## The reading of record

- File: `runs/MERGED_MARKS_LMT4B.json` (byte-identical copy of the reader's `runs/MERGED_MARKS.json`), on-disk sha256
  **`8eb41440129f314147ab06f9dd747bd09c9a04b416b8b1a11593080138d3ab71`**. The reader printed
  `02b00854548066faa3fd0d9075cda5f36c4dfc17bc769b6bd3105f273468cf15` (the hash of its in-memory text before Windows
  wrote the file with CRLF line endings; LM-T4 had the same two-hash pattern). The on-disk hash is the hash of record.
- `test_verdict`: **`HARD_GATES_PASS`** (all 14 hard gates true).
- Status words printed by the sealed reader: **`LANGUAGE_RODE_THE_PATH`**, **`INJECT_ROUTED`**,
  **`CIRCUIT_EARLIER_NOT_BETTER (ANSWER_2 NOT_EVALUATED)`**, **`EYE_REPORTED`**.
- `one_sentence_claim_licensed`: **true** (by the program; the governance reading is in "What is licensed" below).
- One failed mark: **CONT-3** 106,320 of 106,400 (99.92%) under the frozen 100% rule — FAIL, as forecast; it feeds no
  status word.

## Hard gates (14)

| Gate | LM-T4b (sealed reader) | LM-T4 sealed reader (7423…) | LM-T4 corrected (8606…, note only) |
|---|---|---|---|
| all units present / no deadline hit / H11 tests / worlds check (C25_EQUALITY) | true / true / true (12 of 12 in every part) / true (20 of 20 draws + selection = c25) | same | same |
| H1 receipts | true | true | true |
| H2 no invention (question_values **0**; Task B values not witnessed 0; dialogue invented 0; composition answers wrong 0) | true | **false** (192 "question values": digits inside outcome names) | true |
| H3 replay (A1_REPLAY, A1_NOTAP, A1_NOEYE == A1 on 20 draws and 48 worlds, answers and paths) | true | true | true |
| H4 provenance (INTERNAL rows 0; REAL 288, USER_SAID 240) | true | true | true |
| H5 readout isolation (buffer / facts / tap log / eye log reads 0 / 0 / 0 / 0) | true | true | true |
| H6 controls (twin > 6: 0; shuffled > 6: 0; A5 keyed starts 0 of 240; A5 CREATED 0) | true | true | true |
| H7 RB today reproduced (7 arms == REF on 20 of 20; REF == c26 on 20 of 20; medians 16 / 16) | true | true | true |
| H8 budget | true | true | true |
| H9 tap digest (554,592 of 554,592 over every tap arm) | true | true | true |
| H10 questions carry no value (**0**) | true | **false** | true |

## Marks — LM-T4b number beside LM-T4's number (every instrument number repeated exactly)

| | Mark | LM-T4b | LM-T4 (section 7.35) | Same? |
|---|---|---|---|---|
| 🟩 | TAP-1 round trip (A1) | 64,756 of 64,756 (67,876 sentences; compiler cross-check 16,224 valid, 0 invalid); A4 JSON dump 106,064 of 106,064 | 64,756 of 64,756 (67,876; 16,224 / 0); 106,064 of 106,064 | yes |
| 🟩 | TAP-2 digest unchanged | 106,400 of 106,400 (A1); every tap arm 554,592 of 554,592 | same | yes |
| 🟩 | TAP-3 answers unchanged | 20 of 20 draws; 48 of 48 worlds | same | yes |
| 🟨 | TAP-4 form gaps (report) | 6 station kinds (S0, S2, S3, S4, S5, S6); S3 non-terminating yields 5,903; S2 0; cells: S0 drive state 14,560, order shape 12,400; S2 absent slot 571; S3 limiting reagent 13,360; S4 region x outcome 14,560; S5 receipt sentence 14,560, level 13,360; S6 chain step 1,840 | same | yes |
| 🟩 | INJECT-1 right faculty, right station | 240 of 240 (48 per kind); name-match baseline 240 of 240 | same | yes |
| 🟩 | INJECT-2 shuffled (A5) | 0 of 240 started (MISSING_FACT 48 + 48, THINK_UNKNOWN 48, NO_TARGET 48, MISSING_SUBJECT 48); name-match fires 240 of 240 | same | yes |
| 🟩 | INJECT-3 gate behaviour | CLARIFY 48 of 48; KNOWLEDGE_MISSING naming the slot 48 of 48; invented 0; ask-rule asks 156 planted / 444 shuffled | same | yes |
| 🟩 | INJECT-4 time to start | A1 earlier on 240 of 240; mean wait 3.0 vs 7.0 ticks | same | yes |
| 🟩 | CONT-1 seams | 96 of 96; tone 48 of 48; false 0; within-thought 0 | same | yes |
| 🟩 | CONT-2 drift | walks 24 of 24; no-walk false fires 0 of 24 | same | yes |
| 🟥 | CONT-3 provenance keys | **106,320 of 106,400 (99.92%)**, FOLLOWED 105,856 / CREATED 272 / ATTEMPTED 272, A5 inject CREATED 0 — FAIL (frozen 100%) | 106,320 of 106,400 — FAIL | yes |
| 🟨 | CONT-4 restlessness (report) | S2 steps 816; mean of means 0.06425015240808823; max 0.429043489; INTERP control flagged 96 of 96 | 816; 0.064250152; 0.429043489 | yes |
| 🟩 | ANSWER-1 Task B | medians 16 / 16 in REF, A1, A2, A3; UNDETERMINED 0; A1 == A2 on 20 of 20 draws | same | yes |
| ⬜ | ANSWER-2 | NOT_EVALUATED (PRC-1) | same | yes |
| 🟩 | RECEIPTS-1 | 106,400 = 106,400 = 106,400 passing; deepest level 2 | same | yes |
| 🟩 | EYE-R1 | A1 6,716 = 6,436 rows + 280 twin events verified by receipt; A2 6,668 = 6,388 + 280; A3 6,668 = 6,388 + 280; A5 528 = 528 + 0; pass **true** | corrected: same numbers, pass true; sealed: pass **false** (the 280 twin events had no rows) | yes |
| 🟩 | EYE-R2 | 106,400 / 106,400 (A1); 106,400 / 106,400 (A2); 106,064 / 106,064 (A3); 8,064 / 8,064 (A5) | same | yes |
| 🟩 | EYE-R3 | 6,716 / 6,716; 6,668 / 6,668; 6,668 / 6,668; 528 / 528 | same | yes |
| 🟨 | EYE-R4 (report) | no-walk HELP 504 (A1), 480 (A2), 312 (A3), 480 (A5); Task B HELP 6,020 and FIX 280 per arm | same | yes |
| 🟩 | EYE-R5 door calls | 0 in every arm | same | yes |
| 🟩 | EYE digest neutrality 2 | A1 with and without the eye identical: true | same | yes |

Eye summary (A1): gates G1 6,600 / open 68 / G3 48; limiting x4a drive pair balance 6,489, x3 stations aligned 620,
x7 answers determined 516, x2 lacunae on cadence 476, x4b drive entropy 68; would FIX 280, HELP 7,548, FAILURE_SEEN 0,
NONE 0 — all as LM-T4.

## Program comparison with LM-T4's two readings (`tools/compare_to_lmt4.py`, key by key)

- Against the corrected reading (8606…, LMT4-A3): 12 differences, 10 of them timing; the 2 others are
  `failed_parts/LM_T4_MSI_P01` (LM-T4 had a failed first attempt; this rerun had none) and
  `marks/CONT_3_provenance/mismatch_by_brain` (the post-run reader's extra report, not taken). **0 differences in any
  count, gate, mark or word.**
- Against the sealed reading (7423…): 36 differences, 10 timing; the 26 others are exactly the two fixed items (H2 /
  H10 question_values 192 → 0; EYE-R1 complete → complete_rows + twin_events_verified_by_receipt, pass false → true) and
  everything that follows from them (verdict FAILURE → HARD_GATES_PASS; words INCONCLUSIVE → the four words;
  claim_licensed false → true) plus the absent P01 folder.

## Parts (one at a time, fresh extract of the zip; supervisor and worker unchanged)

| Part | Units | Status | Wall s (supervisor) | Peak working set B | Tests | Free RAM at launch KB |
|---|---|---|---|---|---|---|
| P11 | W01, TBREF 0-19, TB A1_NOTAP 0-19 | COMPLETED | 127.5 | 148,930,560 | 12 of 12 | 409,528 |
| P12 | TB A1 0-19, DLREF 11 / 29 / 47 | COMPLETED | 191.9 | 102,285,312 | 12 of 12 | 1,347,552 |
| P13 | TB A1_REPLAY 0-19, DL A1 11 | COMPLETED | 183.2 | 90,165,248 | 12 of 12 | 485,520 |
| P14 | TB A1_NOEYE 0-19, TB A4 0-19 | COMPLETED | 249.5 | 80,396,288 | 12 of 12 | 1,255,432 |
| P15 | TB A2 0-19, DL A1 29 / 47 | COMPLETED | 195.5 | 100,573,184 | 12 of 12 | 548,772 |
| P16 | TB A3 0-19, DL A1_NOTAP 11 / 29 / 47 | COMPLETED | 202.5 | 104,910,848 | 12 of 12 | 656,812 |
| P17 | DL A1_NOEYE, A1_REPLAY, A2 x 3 seeds | COMPLETED | 86.3 | 96,342,016 | 12 of 12 | 598,892 |
| P18 | DL A3, A4, A5 x 3 seeds | COMPLETED | 88.9 | 78,413,824 | 12 of 12 | 758,616 |

8 of 8 parts COMPLETED; part wall 1,325.3 s; driver span 2026-10-21T03:20:26Z to 03:42:40Z (20:20:26 to 20:42:40 PDT
2026-10-20) = 22 min 14 s; longest part 249.5 s (P14; guard 280 s, hard wall 300 s — the laptop was slower than on
2026-10-15, when P14 took 213.0 s); peak working set 148,930,560 B (P11; cap 314,572,800 B); no deadline hit; no part
killed; no retry; failed parts: none. Sign line used: `APPROVE lm_t4, source 01da263d, LOCAL_CPU_ONCE on MSI, 300 s cap,
no spend.` (operator-composed from the owner's order; not an owner signature). Manifest `01da263d…`, 128 rows, every
hash verified by the supervisor and the worker before each part.

## What is licensed and what is not

- **REAL** laptop run; reading by a reader sealed before the run; no post-hoc change. The forecast in
  `PREREGISTRATION_LMT4B.md` section 5 came true in every number and word.
- **Licensed (the reading's own sentence, SYNTHETIC_ONLY, FORM-only, no wider):** on synthetic recipe worlds and CCE
  dialogues only, the recipe brain's thought was read in exact Controlled CAS English at every station of its path that
  has a CCE form, with a round-trip receipt at each station and no change to any answer or any learned value, and a
  planted utterance started the planted faculty at the planted station while shuffled utterances started none. The
  circuit was earlier (3.0 vs 7.0 ticks), not better (no answer differed).
- **NOT LICENSED:** any claim that language was carried across an RPA (owner: "RPA IS ATLAS"; S0 here is the RPM chain
  per CJT); any meaning claim; any HELM claim; anything beyond SYNTHETIC_ONLY; better answers from the circuit; the
  LSR-family half (ANSWER-2, VERIFY_DID_THE_WORK NOT_EVALUATED, PRC-1); the eye's judgement (report-only; 504 would-HELP
  on clean dialogues is U1's false-alarm baseline); CONT-3 at 100% (it FAILED at 99.92%: the run code's CREATED key on
  the untaught twin's 80 asking crossings — a run-code defect, outside the owner's order, left unfixed on purpose and
  reproduced exactly).
- The old corrected reading LMT4-A3 (`8606c5aa…`) is a note that never counts; LM-T4's sealed reading (`74239223…`,
  INCONCLUSIVE) stays LM-T4's reading of record; LM-T4b is the reading that governs the question.

## Files

`README.md`, `PREREGISTRATION_LMT4B.md`, `FROZEN_LMT4B.json`, `READER_FIX_DIFF.md`, `PACKAGE_FREEZE.json`,
`LM_T4B_20261020_SOURCE.zip`, `package/`, `extract/` (the run), `runs/` (record copy: `LM_T4_MSI_P11..P18/`,
`MERGED_MARKS_LMT4B.json`, `MERGED_MARKS.json`, `MERGED_MARKS.sha256`), `DRIVER_LOG.txt`, `tools/`,
`HASHES_PASS_1..3.txt`, `BACKUP_RECORD.md`.
