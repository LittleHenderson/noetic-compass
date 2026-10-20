# TEST RECORD — HELM-R1 wave 6, the PAIR WAVE (builder, laptop, 0 USD; practice data only)

Nothing here is a result. Every number below comes from the builder's published PRACTICE inputs, never from an exam
(no X6 exam exists yet). Machine copy of the counts: `TEST_COUNTS_R1W6.json`.

## 1. Sealed package

- Zip `HELM_R1_W6_20261019_SOURCE_R1W6.zip` sha256 `f307bdbc51210b87d413b5adb834183f3404ce4da5ac6d37ce23873909d7c9e1`
  (128,056 bytes; 33 members + the freeze); resealed byte-identical (`build/seal_w6.py`).
- `PACKAGE_FREEZE.json` `1b8943c6f9b59a0cef4c179125c4c5cc4c45c6f3d4f55980591f139d4a95db6f`; `FROZEN_R1W6.json`
  `da00f9495c254c3eba494722598589c01ed37453f017f41c4b09b9761e320867`; pre-code preregistration
  `97b5f4f4f7551abe1fb8fbecfc987ef9c38fd272c7fe4f0f2656c53adce21195` (written 2026-10-20T03:34:10Z, before any code).
- HELM code under test: RB-W1T v3's `helm_now/` (cut `65b86282`), equal file for file (158 of 158) to the thread head
  `122b70099f1a5ecac6213bac67b8cc89056cf96e` (`build/CUT_CHECK_W6.json` `673126f2…`); no HELM file changed on the
  thread after that head up to `2b43c4c7`.
- Seven neighbours extracted from their sealed zips into `deps/`, every freeze equal to its pin.

## 2. Tests from the sealed extract (`build/test_from_seal_w6.py`, one process at a time)

| Suite | Result |
|---|---|
| wave-6 units + kit + host run (`tests_r1w6`) | Ran 25, OK (skipped 3: the host-only run test) — includes the STATIC UNSETTLED_ASK test (rule exists, wraps only for the unit, restores, HELM file bytes unchanged, fires on "butter" + "melted butter", not on distinct names, plain question) and the kit refusal of a wrong freeze |
| HELM's own seven suites on a scratch copy of `helm_now/` | Ran 177, OK (skipped 1) |
| members re-hashed against the freeze | 33 of 33, 0 bad |

## 3. Practice dry run (`build/dry_run_w6.py`, `dry_run/run1/`)

- 73 of 77 units (the 4 REPRO_X5 units need the spent X5 files, which the builder never opens), all exit 0, one at a
  time: pool 287.0 s (sum of unit times 264 s; slowest: X6_PAIR job map 28.6 s, X6_PAIRW job map 25.8 s, X6_REAL with
  EYE_SCAN 12.5 s). Peak memory per unit well under 300 MiB.
- The frozen reader (run both from the source tree and from the sealed extract; identical marks and gates) says
  `INSTRUMENT_ERROR` / `INCONCLUSIVE`, as designed: I0 (practice mock), I1 / I6 / I7 / I9 / I10 (no approval, no host
  instruments, REPRO skipped), HG13 / HG14 / HG15 / HG16 (no host carrier list, no sandbox hashes, the 4 skipped units).
  Every other hard gate held: receipts (63 lives re-checked, 0 mismatches), no invention, replays, budgets, the cut,
  Eye writes 0 (including the wide book during scans, whispers and idle ticks), keys and learning audit, open simplex,
  guard trips 0, the WIDE control, parameter audit (35 units), switch hygiene, Eye budget, voice changes no answer.
- Marks on practice: NH met (0 lost on E64 / F64; PAIR A/B/C equal); NH-EYE met; QUIET met (0 findings, 0 whispers);
  K1 met (100 of 106, bar 96); K3 met (0 / 0); K4 met (0; strict 1, the artifact case D-W6-12); K5 met (same-name 8,
  answered 0, limit 1; literal K5-ALL would be 5 of 15 against 3, reported); P met (all six readable, ADDITIVE);
  **NH-CONV missed: 23 new WRONG answers, 10 items lost** (D-W6-13). So the word on practice data would be
  `WIDE_WAVE_HARMED`.

| X6_CONV family (FULL+WIDE, practice) | RIGHT | WRONG | UNDETERMINED |
|---|---|---|---|
| R1 plain / unknown ingredient / unit change | 6 / 4 / 1 | 0 / 0 / 3 | 0 / 0 / 0 |
| R2 absent, R3 question forms, R4 witness, R5 must ask, R7 next session | 4, 0, 2, 4, 0 | 0, 0, 0, 0, 0 | 0, 4, 2, 0, 2 |
| S1 Wisdom, S2 Power, S3 face + unknown | 0, 0, 5 | 6, 5, 1 | 0, 1, 0 |
| S4 recipe purpose absent, S5 ingredient purpose absent, S6 two faces, S7 not a face | 1, 1, 0, 4 | 3, 3, 2, 0 | 0, 0, 0, 0 |

## 4. Findings for the coordinator (before any spend)

1. **HELM defect (FLAG_FOR_HUMAN_REVIEW, D-W6-11):** `helm_english_in.quantities_said` raises `KeyError('stock_words')`
   on a wide-reader reading; HELM's live `helm_chat._recipe_turn` calls it, so a wide teaching turn in chat would crash.
   The wave-6 harness works around it for the exam only.
2. **Integration gaps, predicted to decide the word (D-W6-13):** stated faces, absent purposes and a restated amount
   in a unit of the other kind do not reach the wide path; the wide brain answers anyway.
3. **K-R key-grammar artifact (D-W6-6, D-W6-12):** about half of the UNDETERMINED keys come from the key grammar
   reading a unit word as the ingredient; the caution mark counts the same-name items only.
4. **The voice on wide answers:** with VOICE on, helm_chat speaks a wide answer as "about 0.33 units" (rounded, no dish
   name), while the wide brain's own line says the exact amount. Reported only (scores use the status and the value).
5. **Pair words with one inactive part:** WIDE x VOICE and WIDE x EYE_SCAN are readable only on exams where one of the
   two parts changes nothing; their words will say only that no interaction was possible there (`both_active_on`).
