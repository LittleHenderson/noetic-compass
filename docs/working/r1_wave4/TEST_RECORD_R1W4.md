# TEST_RECORD_R1W4 — what the builder ran before sealing (practice data only; facts, not claims)

Written 2026-10-19 (Pacific) by the wave-4 builder. Laptop MSI, Python 3.14.0, 0 USD, no AWS, no torch, sockets unused.
One python worker at a time; every process under 300 s. **No X4 file exists yet; none was used. No spent X2 / X3 exam
file was opened** (they were only hashed, to pin them).

## 1. Order of work

1. `PREREGISTRATION_R1W4.precode.md` written and hashed BEFORE any wave-4 code: sha256
   `411b31e2da4568b4c7eddd10e9ed8c52b829d9eeeb433abc125bfed17edd2fbf` (2026-10-19T18:11:21Z).
2. Code and tests, then `FROZEN_R1W4.json` from the code's own constants (sha256 `1828dc76...`; a unit test checks
   code == file).
3. Seal (`build/seal_r1w4.py`): zip `HELM_R1_W4_20261019_SOURCE_R1W4.zip` sha256
   `4bd0d740a70852c8d59091494ad88c69ac472f3a0f207a33fc44789b8e3df14c` (121,173 bytes, 31 members + the freeze),
   `PACKAGE_FREEZE.json` sha256 `0d45017c98186d64c701a3a4a7b953fc1d1b87b94a940eb779b3397ae09bf6c7`; resealed
   byte-identical.
4. Every suite and the dry run below ran FROM THE SEALED EXTRACT of that zip.

## 2. Suites from the sealed extract (`TEST_COUNTS_R1W4.json`, one invocation per suite)

| Suite | Ran | Verdict | Seconds |
|---|---|---|---|
| wave 4 units (incl. the custodian plumbing test on seeds outside every band) | 26 | OK | 5.31 |
| wave 4 kit | 5 | OK | 0.33 |
| wave 4 host test (AWS only) | 3 | OK (skipped=3) | 0.15 |
| wave 3b units / kit | 18 / 5 | OK / OK | 14.39 / 0.33 |
| wave 3 units / kit | 36 / 5 | OK / OK | 3.07 / 0.37 |
| wave 2 units + kit | 34 | OK | 3.68 |
| wave 1 carried | 128 | OK | 70.89 |
| HELM live modules (end-to-end loop 18, English in 31, voice 22, triad 15, faces in 16) | 102 | OK | 3.26 |
| language_v3 (lm_t1 26, t1b 11, t1c 5, t1v3 26, lexicon_v2 19) | 87 | OK | 2.41 |
| council test_all.py (repair_performer, the_loop_v3, cube_store, return_address) | 4 scripts | ALL PASS | 2.84 |

449 unittest tests in all, every suite exit 0.

## 3. The dry run (`dry_run/`, `build/dry_run_r1w4.py`, six parts + merge)

Practice data: wave 3b's sealed English-64 / Faces-64 fixtures, wave 4's SELF fixture (seed 868,686), the exposed E1
Gate B and E2 Task B worlds inside the wave-1 package, wave 3's Cascade and Idle fixtures. 56 of the 80 host units
(no reproduction units, no X2-GB / X2-TB / X2-CCE: those need spent files the builder does not open).

| Part | Units | Seconds | Longest unit |
|---|---|---|---|
| P1 English-64 arms | 12 | 20.6 | 1.71 |
| P2 Faces-64 arms | 12 | 22.9 | 1.86 |
| P3 X3-SELF arms | 14 | 58.5 | 5.66 |
| P4 Gate B E1 + Cascade + Idle (FULL, EYE, 6 sidecars in all) | 13 | 9.6 | 0.57 |
| P5 Task B E2 FULL | 2 | 18.0 | 16.71 |
| P6 Task B E2 EYE + sidecar | 3 | 18.4 | 16.38 |

All 56 units exit 0. Peak memory measured: X3-SELF candidate unit 46.9 MiB, English-64 candidate 32.5 MiB, Task B
teach 33.3 MiB; the merge + frozen reader 139.5 MiB on a 16,907,706-byte dry host reading.

**The frozen reader on the dry reading:** `INSTRUMENT_ERROR` as designed (no X4, no approval, no run record, no
reproduction, no spent carried data), EYE_SCAN word `INCONCLUSIVE`. Every hard gate it can compute held on practice
data: H1, H3, H5, H6, H7, H8, H9, H11, HV, HS, HC. Marks on practice data:

| Row | Practice-data value |
|---|---|
| (a) no harm | English-64 60 → 60; Faces-64 60 → 60; X3-SELF clean 64 → 64; E1 Gate B 37 → 37; E2 Task B 1,461 → 1,461; Cascade 64 → 64; Idle 52 → 52 (the X2 rows are empty in the dry run, so the row reads false here) |
| (b1) found | 88 of 88 (K1 24, K2 16, K3 8, K4 16, K5 24) |
| (b2) acted | 88 of 88 |
| (c) false alarms | 0 Body findings on clean copies, 0 whispers admitted there, 0 sidecar findings |
| (d) whisper writes | 0; the loop is identical in the candidate, report-only and FULL |
| (e) traceable | 8,751 of 8,751 fact sentences in 1,177 candidate reports; 88 of 88 notices; 0 dropped |
| checklist / report-only | checklist found 0; report-only found 88, acted 0 (lift 88, needed 44) |
| self-initiated only | found 0 of 88 (silent faults raise no signal) |

FULL on the practice X3-SELF: 69 probe answers WRONG, 16 RIGHT (K4: the loaded brain is unchanged), 3 UNDETERMINED;
the candidate held all 88 (UNDETERMINED, never WRONG) and kept all 64 clean answers.

Practice pair words (wave 3's rule; NOT a prediction source for X4 beyond what section 14 of the preregistration
says): CUBE_STORE × EYE_SCAN INTERFERENCE (E64 ADDITIVE, SELF INTERFERENCE, slack 5); ENGLISH_IN × EYE_SCAN ADDITIVE
(SELF CEILING_NOT_READABLE); EYE_SCAN × TRIAD INTERFERENCE (SELF slack 5); EYE_SCAN × VOICE ADDITIVE (SELF
CEILING_NOT_READABLE, slack −3).

## 4. Builder disclosures (what changed after the precode page, before the seal; no rule, mark or threshold changed)

- B-1 The preregistration estimated "about 70 host units"; the built pool has 80 (8 sidecars and 2 restarts counted).
- B-2 Size: the host reading is written compact (no indent) and each scan record keeps only what the reader reads
  (tick, end, trigger, status, units, digest, findings, live check, window); full SELF_REPORTs (sentences, cited facts,
  findings, body status, two Mind fields) are kept for the CANDIDATE only. Hence H11 compares the candidate and its
  replay record for record WITHOUT the kept reports; every scan's digest still sits in both records' `scans`.
- B-3 The pool asks wave 2's builder only for the exams whose data it was given (a KeyError found by the dry run).
- B-4 A self-report with no lessons says "I haven't been given any lessons yet." (a NO_EVIDENCE sentence) instead of
  failing on an empty count (found by the first practice run).
- B-5 The dry run was split into six parts so no laptop process lives longer than 300 s.
