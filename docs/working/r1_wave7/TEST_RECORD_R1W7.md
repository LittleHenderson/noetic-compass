# TEST RECORD — HELM-R1 wave 7, the CHAT WAVE, v3 (FIX FIRST round 2; builder, laptop, 0 USD; practice data only)

Nothing here is a result. Every number comes from the builder's PRACTICE inputs (RB-W1T's practice draw v2 and wave 6's
published practice conversation pool, both excluded from the exam by id and by text; the same draw for v1, v2 and v3).
No exam exists: the owner has not signed the proposed line `CHAT WAVE at 1 USD`, no approval record was written, and no
custodian seal was run. The builder never opened any exam folder or any `KEYS_*` file. Earlier records are kept as
`v1_void_TEST_RECORD_R1W7.md` and `v2_void_TEST_RECORD_R1W7.md`. Machine copies: `TEST_COUNTS_R1W7.json`
(`aa8160df...`), `dry_run/run5_v3_from_seal/DRY_RUN_SUMMARY.json` (`3e171a32...`) and `R1_W7_READING_DRY.json`
(`798f56f2...`), `build/CUT_CHECK_W7.json` (`f8b8b24b...`).

## 1. What changed between v2 and v3 (amendment A-R1W7-3 in the package's PREREGISTRATION_R1W7.md)

- **HELM under test:** commit `dfc7158d0aba3cca7b0a1ccd1e1c2c8a74e36cf6` (branch `claude/helm-r1w7-chat-wave-packet-20261020`,
  PR #416, 2 commits on `974fe36c`). Of the 161 cut files exactly four differ from v2: `helm_end_to_end_loop.py`,
  `helm_chat.py`, `helm_wide_turn.py`, `test_helm_wide_alongside.py` (+4 tests, class F). Fixes: no tool engine on a
  kitchen sentence (whole-word keywords, the chat's software trigger knows the wide brain's ingredient names); the wide
  reader claims wave 3b's question forms and strips "Hi again." / "Hello there!"; an "X or Y" line binds X; "but we've
  run out of X" is a reader question (`ABSENT_STATED`). `helm_brain_canonical.py` byte-identical to base `d4488f2a`
  (`24df53c9...`). `build/CUT_CHECK_W7.json`: 161 of 161 equal to `git show dfc7158d`, 0 extra.
- **Package:** pins and labels (commit, version v3; FROZEN `0f1157e9...`; README, RUN_LIMITS, stage note) and one reported
  row, D-W7-19 (tool-engine turns per chat unit; must be 0; reported, not a gate). No mark, threshold, arm, word, band,
  exam size, instrument row or hard gate changed.
- **v1** (zip `5107b9c6...`) and **v2** (zip `7e7fa066...`) are VOID_SUPERSEDED: never launched, no exam drawn; kept with
  `v1_void_` / `v2_void_` prefixes (zip, freeze, test counts, test record, zip sha).

## 2. Sealed package v3

- Zip `HELM_R1_W7_20261020_SOURCE_R1W7.zip` sha256 **`5063baba8be9ba807e7905d5f86732cb1a535ff5a533e67c79f5cbe16edbc6a9`**
  (941,565 bytes; 194 members + the freeze; resealed byte-identical).
- `PACKAGE_FREEZE.json` **`2366e85d7a3b73fa0c6cefb94715aa7ba9cfeb6f3b384c4c0ad88d5ed0165da2`** (the runner's
  `--expected-freeze-sha256` once the owner signs); `PREREGISTRATION_R1W7.md` `abf125a4...` (= precode `efe94ed6...`
  verbatim + A-R1W7-1 + A-R1W7-2 + A-R1W7-3); `contract/HELM_CUT_R1W7.json` `6708c9e9...`.
- Neighbours unchanged: wave 1 v3 `8c55c413...`, wave 3 v3 `bd06f324...`, wave 3b `a6d9dbc7...`, wave 6 v3 `da1ec4d2...`,
  RB-W1T v3 `04eef886...`; all re-verified sealed; nothing written to the repo.

## 3. Tests (from the sealed v3 extract, every process `python -X utf8 -B -I`)

| Suite | Result |
|---|---|
| wave-7 suites (`tests_r1w7/run_tests.py`: unit + kit, incl. the two runner-refusal tests) | **Ran 31, OK** (56.9 s) |
| HELM's own 8 unittest files on a scratch copy of `helm_now/` | **Ran 201, OK** (skipped=1; 4.3 s); sealed `helm_now/` unchanged after |
| members re-hashed against the freeze | 194 of 194, 0 bad |
| receiver check on the practice draw | `all_pass: true` |

## 4. Practice dry run v1 -> v2 -> v3 (`dry_run/run1_from_seal`, `run3_v2_from_seal`, `run5_v3_from_seal`; each pre-seal run has identical totals)

Same practice inputs every time; 14 units one at a time (v3: 59.4 s; largest unit 7.5 s; peak process memory 31-51
MiB); every unit exit 0; 0 crashes; 0 `SystemExit`; 0 network attempts; 0 receipt problems; no file changed under
`helm_now/`; every session log under its scratch; replay and diagnostic projections equal; recorder transparent 6 of 6
(v3: byte-identical even before the wall-clock strip). Reader: `INSTRUMENT_ERROR` / `INCONCLUSIVE` as designed for a
practice mock (I0, I1, I6, I7, I9, I10; HG5 only for want of host sandbox hashes).

| Practice number (CHAT_ON unless said) | v1 `974fe36c` | v2 `1b0c6d62` | v3 `dfc7158d` |
|---|---|---|---|
| X7_REAL RIGHT / WRONG / asks / not scored | 90 / 0 / 23 / 15 | 103 / 0 / 10 / 15 | 103 / 0 / 10 / 15 |
| X7_REAL fully learned of 106 (K1 bar 96) | 97 | 102 | 102 |
| X7_REAL lessons learned / wrong / not learned (670) | 578 / 0 / 92 | 594 / 0 / 76 | 594 / 0 / 76 |
| X7_REAL unexplained asks (K4) | 8 | 0 | 0 |
| X7_REAL RIGHT_AND_PLAIN (P) | 35 | 103 | 103 |
| X7_REAL question turns not routed to the loop | 10 | 0 | 0 |
| X7_REAL CHAT_OFF / LOOP_ON / ALWAYS_ASK RIGHT | 0 / 100 / 0 | 0 / 100 / 0 | 0 / 100 / 0 |
| X7_REAL NH-CHAT lost / gained vs LOOP_ON | 13 / 3 | 0 / 3 | 0 / 3 |
| X7_REAL stock recorded but reply "outside what I know" | 110 of 110 | 0 of 115 | 0 of 115 |
| X7_CONV RIGHT / WRONG / UNDETERMINED / RIGHT_AND_PLAIN | 36 / 1 / 27 / 34 | 38 / 1 / 25 / 38 | 43 / 0 / 21 / 43 |
| X7_CONV CHAT_OFF RIGHT; LOOP_ON RIGHT / WRONG | 28; 36 / 1 | 28; 36 / 1 | 28; 41 / 0 |
| X7_CONV NH-CHAT lost / gained vs LOOP_ON | 2 / 2 | 0 / 2 | 0 / 2 |
| X7_NOISE RIGHT / WRONG / RIGHT_AND_PLAIN; items lost to noise | 36 / 1 / 34; 0 | 38 / 1 / 38; 0 | 43 / 0 / 43; 0 |
| X7_NOISE misrouted scored turns (N) / misrouted noise / noise CAS | 10 / 0 / 0 | 5 / 0 / 0 | 0 / 0 / 0 |
| X7_NOISE CHAT_OFF RIGHT / RIGHT_AND_PLAIN | 28 / 28 | 28 / 28 | 28 / 28 |
| tool-engine turns in chat units (D-W7-19) | not recorded | 4 | 0 |
| CHAT_ON - CHAT_OFF RIGHT: REAL / CONV / NOISE | +90 / +8 / +8 | +103 / +10 / +10 | +103 / +15 / +15 |
| marks met on practice | K1 | K1, K4, P, NH-CHAT | **all six** |
| word had the instruments held | HARMED | HARMED (N, K3) | EARNED_KEEP |

### v3 observations (facts; nothing tuned; a practice draw the builder has seen decides nothing)

- X7_CONV's 21 items not RIGHT are all UNDETERMINED: the 18 faces dialogues (S1, S2, S6, S7: the wide path asks for the
  stock it was just given, in the chat and in LOOP_ON alike), 2 of 4 R4 witness-in-English items (`CV23`, `CV25`), and
  the R7 item `CV31` (its stock sentence is not held at the question). `CV22` (WRONG in v1, v2) now learns "one soup
  needs 1 cup of dry bean" and is RIGHT.
- The limiting name of an "X or Y" line is said with the note in it: "Or chicken bouillon runs out first" (`CV18`);
  scored RIGHT by the K-R head.
- X7_REAL: 10 recipes asked as `CLARIFY_ENGLISH_UNKNOWN_PRODUCT` (not fully learned, so explained), 2
  `UNDETERMINED_CLARIFY`, 1 `CLARIFY_NOT_CCE`; 25 of 128 not RIGHT in CHAT_ON, 15 of them UNDETERMINED keys (not scored).
- The chat answers 3 REAL items RIGHT that LOOP_ON (wave 3's triad-wrapped loop build) asks on, in every version
  (`RW:pg:38193@134740`, `RW:pg:42450@482967`, `RW:pg:65061@548598`); not investigated.

## 5. Deviations (all in the package's amendments; D-W7-1..5 are the precode's)

D-W7-6 LOOP_ON = wave 6's `FULL+WIDE_NOASK`. D-W7-7 "quotes the yield" = an exact number. D-W7-8 HG2 on REAL and CONV.
D-W7-9 K4 strict; an unrouted question is an ask. D-W7-10 `new_session` no-op in a chat arm. D-W7-11 isolated python.
D-W7-12 the 161-file cut. D-W7-13 the chat's tool engine roots at `helm_now/`; tree hash per unit. D-W7-14
`NOT_ROUTED_TO_LOOP` rows. D-W7-15 recorder fixture. D-W7-16 owner line proposed. D-W7-17 I12 strips wall-clock fields
(v2). D-W7-18 the loop's tool turns recorded (v2). **New in v3:** D-W7-19 tool-engine turns per chat unit reported, 0
required on practice (reported row, not a gate).

## 6. Forecast after v3 practice (not read by any program)

`CHAT_WAVE_EARNED_KEEP` about 0.45 (every mark holds on the practice draw; a fresh draw can hold a lesson form read
wrongly (K3), a question form not claimed (N), or a yield said in a form the quoting rule does not read (P));
`CHAT_WAVE_HARMED` about 0.2; `CHAT_WAVE_NO_GAIN` about 0.15; `INCONCLUSIVE` about 0.2.

## 7. Still wrong in HELM that this build shows (for the owner to read; not tuned here)

1. Faces stated in a dialogue (S1, S2, S6, S7; 18 of 64 items by construction) are UNDETERMINED in the chat and in the
   loop driven directly: the wide path does not read the face clause and asks for stock it already has. No mark
   suffers (LOOP_ON loses them too), but a quarter of every X7_CONV draw is unanswered.
2. The R7 "next session" dialogue `CV31` loses its stock at the question; `CV30` does not.
3. Two R4 witness-in-English items (`CV23`, `CV25`: "Yesterday we made 1 X from ..., and the Y ran out first.") are not
   admitted as lessons.
4. The "X or Y" limiting name is spoken as "Or chicken bouillon" (`CV18`): right by the key, odd to a person.

## 8. What failed while building v3

Nothing new: the stale-freeze kit test failed before the reseal (expected) and passes from the seal; every suite and the
dry run passed first time on the v3 cut.
