# TEST RECORD — HELM-R1 wave 6, the PAIR WAVE, v2 (builder, laptop, 0 USD; practice data only)

Nothing here is a result. Every number comes from the builder's published PRACTICE inputs (no X6 exam exists). v1
(`f307bdbc…`) is `VOID_SUPERSEDED_BY_V2` (amendment A-R1W6-1, coordinator decision FIX FIRST); its record is kept as
`v1_void_TEST_RECORD_R1W6.md`. Machine copy of the counts: `TEST_COUNTS_R1W6.json`.

## 1. What changed between v1 and v2

- **HELM fix (PR #400, merge `221cab7038ef5088156794d4f941ba6dfdf27ab7`), RB-W1 v4:** face / purpose clauses in a wide
  stock sentence are asked about (`UNREAD_CLAUSE`), a face held by the licensed triad on a wide recipe's ingredient
  makes the wide path ask (`CLARIFY_WIDE_FACE_NOT_HELD`), a restated amount is read as stock and converted or asked
  about (`UNIT_KIND_MISMATCH`), an unreadable restatement withdraws the old amount, and `helm_english_in.quantities_said`
  no longer raises on a wide reading (the `helm_chat` crash). Tests first: `test_helm_wide_alongside.py`, 10 tests, 9
  fail on v3. HELM suites 187 OK; the chat nuance script passes.
- **Package:** HELM is cut into the package (`helm_now/`, 159 files, `git show 221cab70`); the harness workaround is
  gone; WIDE x VOICE and WIDE x EYE_SCAN are `NOT_EXERCISED_BY_CONSTRUCTION` (reported, not read; mark P over four
  pairs); the K5 adaptation recorded as A-R1W6-1.

## 2. Sealed package v2

- Zip `HELM_R1_W6_20261019_SOURCE_R1W6.zip` sha256 `729623429832c5fa99141d96876434d9ebed7417055c87173e7a582b3677be0a`
  (930,005 bytes; 193 members + the freeze); resealed byte-identical.
- `PACKAGE_FREEZE.json` `83983cd4d70efe31d993822fca2f38392327a6f72b9066246af5cd17c014341a`; `FROZEN_R1W6.json`
  `afe9600d7df348bc027017c13a5306d6a11c93505073bd59b81ecfe434c0ed5c`.
- From the sealed extract: wave-6 suites Ran 27, OK (skipped 3: host-only); HELM's own suites on a scratch copy of the
  package's `helm_now/` Ran 187, OK (skipped 1); 193 of 193 members re-hashed, 0 bad. The reader run from the sealed
  extract gives the same marks and gates as from the source tree.

## 3. Practice dry run, before (v1, `dry_run/run1/`) -> after (v2, `dry_run/run3/`)

| Practice number | v1 | v2 |
|---|---|---|
| X6_CONV FULL+WIDE wrong answers | 23 | **0** |
| X6_CONV FULL+WIDE RIGHT_AND_PLAIN (FULL: 30, 0 wrong) | 32 | 38 |
| X6_CONV items lost vs FULL | 10 | 0 |
| X6_E64 / X6_F64 switch ON = OFF (record for record) | 64 / 64 each | 64 / 64 each |
| X6_REAL FULL+WIDE fully learned / RIGHT / WRONG | 100 of 106 / 100 / 0 | 100 of 106 / 100 / 0 |
| same-name recipes answered (limit 1) | 0 of 8 | 0 of 8 |
| X6_PAIRW resolved: FULL / +WIDE / +EYE_PAIRING / both (of 1517) | 332 / 512 / 856 / 1039 | same |
| Eye findings / Eye writes / guard trips on clean arms | 0 / 0 / 0 | 0 / 0 / 0 |
| marks met on practice | all but NH-CONV | all |
| pool (73 units, one at a time) | 287.0 s | 254.1 s |

v2 X6_CONV FULL+WIDE by family: R1 plain 6/6, unknown 4/4, unit change 4/4, R2 4/4, R5 4/4, S3 6/6, S4 4/4, S5 4/4
RIGHT; R3 question forms 4, R4 2, R7 2, S1 6, S2 6, S6 2, S7 4 asked (UNDETERMINED, never wrong). Reported: with the
triad switched off (FULL+WIDE-TRIAD) 7 conversation answers are still wrong; the triad is what makes the wide path ask.

The reader said `INSTRUMENT_ERROR` / `INCONCLUSIVE` on practice, as designed (practice mock, no approval, no host
instruments, REPRO skipped); every other hard gate held.

## 4. Still open (reported, not fixed here)

- With VOICE on, HELM's voice says a wide answer as "about 0.33 units" (rounded, no dish name); scores use the status
  and the value.
- About half of K-R's UNDETERMINED keys are key-grammar artifacts (D-W6-6); the literal count is reported beside K5.
