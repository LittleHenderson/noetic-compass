# RUN_RESULT LM-T4c — LM-T4b run again with the CONT-3 run-code defect fixed (2026-10-20 PDT, laptop MSI, 0 USD)

Owner's order (verbatim): "Fix the CONT-3 run-code defect (CREATED vs ATTEMPTED), seal, and rerun LM-T4 on the laptop at
0 USD as LM-T4c."

Claim ceiling: **SYNTHETIC_ONLY**. FORM-only language claims (Controlled CAS English v0.1c-R is a grammar, not a learned
parser). No HELM claim. **No RPA-crossing claim** (owner ruling 2026-10-15 "RPA IS ATLAS": LM-T4, LM-T4b and this rerun
read S0 as the RPM chain per CJT, not as the Recursive Possibility Atlas). Parameters learned: 0. Spend: 0 USD. No
network, no AWS, no LLM call.

Every number below was computed by the reader `merge_t4b.py` (sha256
`382033ca52735f9b3a6dfedfd1316a716bc01360e8c794d8681328470a0d0db5`, byte-identical to LM-T4b's reader of record, sealed in
the package zip `ccece4ab2037a0d2de48c88cb8da64073c98f5e362bf3a8eb2b09c7d5d409807` BEFORE any part ran) from the raw
counts in `runs/LM_T4_MSI_P11..P18/RESULTS_T4.json`; this file only copies them.

## The reading of record

- File: `runs/MERGED_MARKS_LMT4C.json` (byte-identical copy of the reader's `runs/MERGED_MARKS.json`), on-disk sha256
  **`9dade2b755da49a49909a3f74c564a6eabef5e3b383a0a834bc8a3dce457ad10`**. The reader printed
  `6fefd77afd24cb95cb622b0c345696b88100997d66111b4d2fe9dd93e382414d` (the hash of its in-memory text before Windows wrote
  the file with CRLF line endings; LM-T4 and LM-T4b had the same two-hash pattern). The on-disk hash is the hash of record.
- `test_verdict`: **`HARD_GATES_PASS`** (all 14 hard gates true).
- Status words printed by the reader: **`LANGUAGE_RODE_THE_PATH`**, **`INJECT_ROUTED`**,
  **`CIRCUIT_EARLIER_NOT_BETTER (ANSWER_2 NOT_EVALUATED)`**, **`EYE_REPORTED`**.
- `one_sentence_claim_licensed`: **true** (by the program; the governance reading is in "What is licensed" below).
- **CONT-3: 106,400 of 106,400 (100 percent), `pass` true**, labels FOLLOWED 105,856 / CREATED 272 / ATTEMPTED 272 —
  the labels are the same as LM-T4 and LM-T4b to the unit; only the key moved. The forecast in `PREREGISTRATION_LMT4C.md`
  section 5 came true in every number and word. No failed mark.

## Hard gates (14) — LM-T4c beside LM-T4b

| Gate | LM-T4c | LM-T4b (8eb41440…) |
|---|---|---|
| all units present / no deadline hit / H11 tests / worlds check (C25_EQUALITY) | true / true / true (**13 of 13** in every part) / true (20 of 20 draws + selection = c25) | true / true / true (12 of 12) / true |
| H1 receipts | true | true |
| H2 no invention (question_values 0; Task B values not witnessed 0; dialogue invented 0; composition answers wrong 0) | true | true |
| H3 replay (A1_REPLAY, A1_NOTAP, A1_NOEYE == A1 on 20 draws and 48 worlds, answers and paths) | true | true |
| H4 provenance (INTERNAL rows 0; REAL 288, USER_SAID 240) | true | true |
| H5 readout isolation (0 / 0 / 0 / 0) | true | true |
| H6 controls (twin > 6: 0; shuffled > 6: 0; A5 keyed starts 0 of 240; A5 CREATED 0) | true | true |
| H7 RB today reproduced (7 arms == REF on 20 of 20; REF == c26 on 20 of 20; medians 16 / 16) | true | true |
| H8 budget | true | true |
| H9 tap digest (554,592 of 554,592 over every tap arm) | true | true |
| H10 questions carry no value (0) | true | true |

## Marks — LM-T4c number beside LM-T4b's number

| | Mark | LM-T4c | LM-T4b (section 7.100) | Same? |
|---|---|---|---|---|
| 🟩 | TAP-1 round trip (A1) | 64,756 of 64,756 (67,876 sentences; compiler cross-check 16,224 valid, 0 invalid); A4 JSON dump 106,064 of 106,064 | same | yes |
| 🟩 | TAP-2 digest unchanged | 106,400 of 106,400 (A1); every tap arm 554,592 of 554,592 | same | yes |
| 🟩 | TAP-3 answers unchanged | 20 of 20 draws; 48 of 48 worlds | same | yes |
| 🟨 | TAP-4 form gaps (report) | 6 station kinds (S0, S2, S3, S4, S5, S6); S3 non-terminating yields 5,903; S2 0 | same | yes |
| 🟩 | INJECT-1 right faculty, right station | 240 of 240 (48 per kind); name-match baseline 240 of 240 | same | yes |
| 🟩 | INJECT-2 shuffled (A5) | 0 of 240 started; name-match fires 240 of 240 | same | yes |
| 🟩 | INJECT-3 gate behaviour | CLARIFY 48 of 48; KNOWLEDGE_MISSING naming the slot 48 of 48; invented 0; ask-rule asks 156 / 444 | same | yes |
| 🟩 | INJECT-4 time to start | A1 earlier on 240 of 240; mean wait 3.0 vs 7.0 ticks | same | yes |
| 🟩 | CONT-1 seams | 96 of 96; tone 48 of 48; false 0; within-thought 0 | same | yes |
| 🟩 | CONT-2 drift | walks 24 of 24; no-walk false fires 0 of 24 | same | yes |
| 🟩 | **CONT-3 provenance keys** | **106,400 of 106,400 (100 percent)**, FOLLOWED 105,856 / CREATED 272 / ATTEMPTED 272, A5 inject CREATED 0 — **PASS** (frozen 100 percent) | **106,320 of 106,400 (99.92 percent)** — FAIL; same labels | **no: the fixed mark** |
| 🟨 | CONT-4 restlessness (report) | S2 steps 816; mean of means 0.06425015240808823; max 0.429043489; INTERP control flagged 96 of 96 | same | yes |
| 🟩 | ANSWER-1 Task B | medians 16 / 16 in REF, A1, A2, A3; UNDETERMINED 0; A1 == A2 on 20 of 20 draws | same | yes |
| ⬜ | ANSWER-2 | NOT_EVALUATED (PRC-1) | same | yes |
| 🟩 | RECEIPTS-1 | 106,400 = 106,400 = 106,400 passing; deepest level 2 | same | yes |
| 🟩 | EYE-R1 | A1 6,716 = 6,436 rows + 280 twin events verified by receipt; A2 6,668 = 6,388 + 280; A3 6,668 = 6,388 + 280; A5 528 = 528 + 0; pass true | same | yes |
| 🟩 | EYE-R2 | 106,400 / 106,400 (A1); 106,400 / 106,400 (A2); 106,064 / 106,064 (A3); 8,064 / 8,064 (A5) | same | yes |
| 🟩 | EYE-R3 | 6,716 / 6,716; 6,668 / 6,668; 6,668 / 6,668; 528 / 528 | same | yes |
| 🟨 | EYE-R4 (report) | no-walk HELP 504 (A1), 480 (A2), 312 (A3), 480 (A5); Task B HELP 6,020 and FIX 280 per arm | same | yes |
| 🟩 | EYE-R5 door calls | 0 in every arm | same | yes |
| 🟩 | EYE digest neutrality 2 | A1 with and without the eye identical: true | same | yes |

Raw counts behind CONT-3 (`RESULTS_T4.json`, arm A1 Task B, 20 draws): taught brain 93,520 crossings, CREATED 80,
ATTEMPTED 0, key mismatches 0; untaught twin 4,480 crossings, CREATED 0, ATTEMPTED 80, key mismatches **0** (LM-T4b: 80).
The same holds in A1_NOTAP, A1_NOEYE, A1_REPLAY and A2 (twin mismatches 0 each; LM-T4b: 80 each); A3 and A4 ask nothing
(0 / 0, as before). Dialogue crossings 8,400, mismatches 0 (as before).

## Program comparison (`tools/compare_to_lmt4.py`, key by key; `COMPARISON_TO_LMT4B.txt`)

The script's first block was given LM-T4b's reading of record (`8eb41440…`) and its second block LM-T4's corrected
reading (`8606c5aa…`, LMT4-A3, a note that never counts); the block labels printed by the unchanged script name LM-T4's two
readings and should be read as "vs LM-T4b" and "vs LM-T4 corrected".

- vs LM-T4b (`8eb41440…`): 20 differences, 10 of them timing; the other 10 are exactly `CONT_3_provenance/agree`
  (`106320/106400` -> `106400/106400`), `CONT_3_provenance/pass` (false -> true) and `tests` 12 -> 13 in each of the 8
  parts (the added unit test). **0 differences in any other count, gate, mark or word.**
- vs LM-T4 corrected (`8606c5aa…`): 22 differences, 10 timing; the other 12 are the same CONT-3 two, the 8 test counts,
  LM-T4's failed first-attempt folder P01 (none here) and the untaken `mismatch_by_brain` report (which in LM-T4 read
  `task_b_twin: 80`, the exact 80 this fix removes).

## Parts (one at a time, fresh extract of the zip; supervisor and worker unchanged)

| Part | Units | Status | Wall s (supervisor) | Peak working set B | Tests | Free RAM at launch KB |
|---|---|---|---|---|---|---|
| P11 | W01, TBREF 0-19, TB A1_NOTAP 0-19 | COMPLETED | 95.4 | 149,479,424 | 13 of 13 | 521,240 |
| P12 | TB A1 0-19, DLREF 11 / 29 / 47 | COMPLETED | 152.1 | 99,799,040 | 13 of 13 | 949,752 |
| P13 | TB A1_REPLAY 0-19, DL A1 11 | COMPLETED | 165.5 | 90,873,856 | 13 of 13 | 1,453,604 |
| P14 | TB A1_NOEYE 0-19, TB A4 0-19 | COMPLETED | 198.6 | 80,203,776 | 13 of 13 | 1,088,208 |
| P15 | TB A2 0-19, DL A1 29 / 47 | COMPLETED | 124.6 | 87,928,832 | 13 of 13 | 863,036 |
| P16 | TB A3 0-19, DL A1_NOTAP 11 / 29 / 47 | COMPLETED | 170.6 | 95,690,752 | 13 of 13 | 728,800 |
| P17 | DL A1_NOEYE, A1_REPLAY, A2 x 3 seeds | COMPLETED | 65.9 | 75,755,520 | 13 of 13 | 616,788 |
| P18 | DL A3, A4, A5 x 3 seeds | COMPLETED | 66.4 | 75,808,768 | 13 of 13 | 728,968 |

8 of 8 parts COMPLETED; part wall 1,039.1 s (exact sum 1,039.0523886 s); driver span 2026-10-21T04:14:52Z to 04:32:19Z
(21:14:52 to 21:32:19 PDT 2026-10-20) = 17 min 27 s; longest part 198.6 s (P14; guard 280 s, hard wall 300 s; LM-T4b's P14
took 249.5 s, LM-T4's 213.0 s); peak working set 149,479,424 B (P11; cap 314,572,800 B); no deadline hit; no part
killed; no retry; failed parts: none. Sign line used: `APPROVE lm_t4, source 94bcf5d1, LOCAL_CPU_ONCE on MSI, 300 s cap,
no spend.` (operator-composed from the owner's order; not an owner signature). Manifest `94bcf5d1…`, 132 rows, every hash
verified by the supervisor and the worker before each part.

## What is licensed and what is not

- **REAL** laptop run; the run code fixed in one place and sealed before the run; the reader unchanged and sealed before
  the run; no post-hoc change. The forecast came true in every number and word.
- **Licensed (the reading's own sentence, SYNTHETIC_ONLY, FORM-only, no wider), as LM-T4b:** on synthetic recipe worlds and
  CCE dialogues only, the recipe brain's thought was read in exact Controlled CAS English at every station of its path that
  has a CCE form, with a round-trip receipt at each station and no change to any answer or any learned value, and a
  planted utterance started the planted faculty at the planted station while shuffled utterances started none. The
  circuit was earlier (3.0 vs 7.0 ticks), not better (no answer differed).
- **Newly licensed by this run, and only this:** the provenance-key mark CONT-3 holds under a sealed run — at every one of
  the 106,400 crossings read, the key the run code wrote at the crossing equals the label the crossing ended with (100
  percent, frozen threshold met). This is a bookkeeping mark about the instrument: the run code now says what it expects
  of each pointer and is right every time. It is the first of the three runs (LM-T4, LM-T4b, LM-T4c) with no failed mark.
- **What CONT-3 at 100 percent does NOT license:** nothing about "continuity of thought" as a meaning claim (the mark
  counts key-label agreement, not thought); nothing about Atlas / RPA crossings (owner: "RPA IS ATLAS"; S0 here is the RPM
  chain per CJT); nothing beyond SYNTHETIC_ONLY; FORM-only.
- **NOT LICENSED (as LM-T4b):** any RPA-crossing claim; any meaning claim; any HELM claim; anything beyond
  SYNTHETIC_ONLY; better answers from the circuit; the LSR-family half (ANSWER-2, VERIFY_DID_THE_WORK NOT_EVALUATED,
  PRC-1); the eye's judgement (report-only; 504 would-HELP on clean dialogues is U1's false-alarm baseline).
- LM-T4b's reading (`8eb41440…`) stays LM-T4b's reading of record; LM-T4's sealed reading (`74239223…`, INCONCLUSIVE)
  stays LM-T4's; LMT4-A3 (`8606c5aa…`) is a note that never counts. LM-T4c is the reading that now governs the question,
  with CONT-3 settled.

## Negatives kept

- LM-T4 and LM-T4b's CONT-3 failures (99.92 percent) stay on their records; this run does not erase them.
- The reader's printed hash and its on-disk hash differ (CRLF on write), as in LM-T4 and LM-T4b.
- The `tests` field moved 12 -> 13 in every part: an instrument change made on purpose and preregistered, not a number of
  the experiment.

## Files

`README.md`, `PREREGISTRATION_LMT4C.md`, `FROZEN_LMT4C.json`, `CONT3_DIAGNOSIS.md`, `CONT3_FIX_DIFF.md`,
`CONT3_stations.diff`, `CONT3_test.diff`, `TEST_OLD_CODE_OUTPUT.txt`, `TEST_FIXED_CODE_OUTPUT.txt`,
`TWIN_ASKING_DETAIL_OLD_CODE.txt`, `PACKAGE_FREEZE.json`, `LM_T4C_20261020_SOURCE.zip` (+ `.sha256`), `package/`,
`old_code_test/`, `extract/` (the run), `runs/` (record copy: `LM_T4_MSI_P11..P18/`, `MERGED_MARKS_LMT4C.json`,
`MERGED_MARKS.json`, `MERGED_MARKS.sha256`), `READER_STDOUT.txt`, `COMPARISON_TO_LMT4B.txt`, `DRIVER_LOG.txt`, `tools/`,
`HASHES_PASS_1..3.txt`, `BACKUP_RECORD.md`.
