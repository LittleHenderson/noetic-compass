# TEST RECORD — HELM-R1 wave 6, the PAIR WAVE, v3 (the K4 re-run; builder, laptop, 0 USD; practice data only)

Nothing here is a result. Every number comes from the builder's published PRACTICE inputs. No new exam exists yet
(the custodian draws X6v3 after this seal). The spent X6 exam was not opened by the builder for any of this. v2's
record is kept as `v2_spent_TEST_RECORD_R1W6.md`; v1's as `v1_void_TEST_RECORD_R1W6.md`. Machine copy of the counts:
`TEST_COUNTS_R1W6.json`. Practice before/after numbers by program: `dry_run/PRACTICE_BEFORE_AFTER_V3.json`
(sha256 `86f13f2809bf669358aab44dcdeef46f4818341c070071f5b2a0bfb1771e7fbd`).

## 1. What changed between v2 and v3 (amendment A-R1W6-2)

- **HELM under test:** cut at thread head `fdf68e0c524298140e663ddda3cf76e34350ef0f` (PR #406 merge). Of the 159 cut
  files, exactly two differ from v2's cut `221cab70`: `helm_wide_turn.py` (reader v5) and `test_helm_wide_alongside.py`
  (+5 tests). `build/CUT_CHECK_W6.json` (sha256 `e6b9281e…`): 159 of 159 equal to the thread head.
- **Owner line:** `FIX K4 at 1 USD` (15 bytes). Cap 1.00 USD, attempts unchanged.
- **Seed bands:** moved to 1,980-1,989 M (used table 1-1,979,000,000).
- **Exclusions:** the spent X6 exam's 128 REAL + 64 CONV + 64 PAIRW ids (`contract/EXCLUDE_R1W6_X6_USED.json`, from
  `MANIFEST_X6.json` `4d81abff…`, ids only); the two spent X6 language files join the text rule (eleven files).
- `FROZEN_R1W6.json` changes only in: owner line / bytes / sha / source, bands, used range, HELM commit, the two new
  extra-text pins. Units (77), arms, marks, words unchanged.

## 2. Sealed package v3

- Zip `HELM_R1_W6_20261019_SOURCE_R1W6.zip` sha256 `f1b64a5edf0df2b152c867f328c71b3df8640a759836108079590e7959c31b47`
  (939,259 bytes; 194 members + the freeze; resealed byte-identical).
- `PACKAGE_FREEZE.json` `da1ec4d2e144a8921d27231e99ff277de0e915b61e2de205cc94646a4723c8a8`; `FROZEN_R1W6.json`
  `94ecafcaecb08203ca331f77d1eb8219bd19418b6b8accda20dc0d1c703a24ca`.
- From the sealed extract (`build/test_from_seal_w6.py`): wave-6 suites **Ran 28, OK** (skipped 3: host-only; one new
  test checks the X6 exclusion contract); HELM's own suites on a scratch copy of the package's `helm_now/` **Ran 192,
  OK** (skipped 1); 194 of 194 members re-hashed, 0 bad.

## 3. Practice dry run, before (v2, `dry_run/run3/`) -> after (v3, `dry_run/run4_v3/`)

Same practice inputs (`dry_run/practice_inputs/`), 73 units one at a time, run from the sealed v3 extract.

| Practice number | v2 (before) | v3 (after) |
|---|---|---|
| X6_REAL FULL+WIDE **K4 unexplained asks** | **0** | **0** |
| K4 strict count (incl. the key-grammar artifact item, D-W6-12; reported) | 1 | 1 |
| X6_CONV FULL+WIDE wrong answers (NH-CONV: lost / new wrong) | **0** (0 / 0) | **0** (0 / 0) |
| X6_CONV RIGHT / WRONG / asks: FULL; FULL+WIDE | 30/0/34; 38/0/26 | 30/0/34; 38/0/26 |
| X6_E64 switch ON = OFF (score for score, FULL vs FULL+WIDE) | 64 / 64 (60 RIGHT, 4 UNDETERMINED) | 64 / 64 (same) |
| X6_F64 switch ON = OFF (score for score) | 64 / 64 (60 RIGHT, 2 UNDET., 2 WRONG in both) | 64 / 64 (same) |
| X6_REAL FULL+WIDE fully learned of 106 (K1 needs 96) | 100 | **99** |
| X6_REAL FULL+WIDE RIGHT / WRONG / asks | 100 / 0 / 13 | **99** / 0 / **14** |
| lessons learned / wrong / not learned (of 670) | 577 / 0 / 93 | 573 / 0 / 97 |
| K5 same-name answered (limit 1); literal reported | 0 of 8; 5 of 15 | 0 of 8; 5 of 15 |
| marks met on practice | all | all |
| reader on practice | `INSTRUMENT_ERROR` / `INCONCLUSIVE` (as designed: practice mock) | same; same failing rows |
| pool (73 units, one at a time) | 254.1 s | 278.6 s |

**The one change, stated plainly (a cost of the fix, kept as a negative).** One practice recipe (`RW:pg:48804@477619`,
public practice data) has the line "1 pint cream and same quantity of milk, slightly sour." Reader v5 sees a relative
amount ("same quantity of") in a form its table does not hold (no "the" before "same"), so it asks
(`AMOUNT_RELATIVE`) instead of reading the line. v2 had learned and answered it. Now it is not learned (4 lessons), so
K1 drops 100 -> 99 (still above the 96 bar) and RIGHT 100 -> 99. It is an honest ask on a not-learned recipe, so K4
does not count it; WRONG stays 0. Not fixed here: v3 may carry only the merged reader-v5 fix, and nothing is tuned on
this. Risk for the fresh draw: more such phrasings would cost K1 margin, not safety.

The record-level `score` field inside the unit files (the old wave-3 item grader) differs from the reader's keyed
numbers; every number above is the frozen reader's or a score-for-score unit comparison.

## 4. Still open (reported, not fixed here)

- The "same quantity of X" form (without "the") and similar relative phrasings are asked, not read (above).
- With VOICE on, HELM's voice says a wide answer as "about 0.33 units" (rounded, no dish name); scores use the status
  and the value.
- About half of K-R's UNDETERMINED keys are key-grammar artifacts (D-W6-6); the literal count is reported beside K5.
