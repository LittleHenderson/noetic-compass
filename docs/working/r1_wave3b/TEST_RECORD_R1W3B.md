# TEST_RECORD_R1W3B — what was tested on the laptop before the seal (2026-10-19, Pacific)

Laptop MSI, Windows, Python 3.14.0, one process at a time (about 800 MB free RAM at the start). No AWS. No spend. No
torch. Everything below is a FACT about the code and the builder's fixtures; nothing here is a result about HELM.

## 1. All pure-Python suites, run from extracted copies of the SEALED zips (`build/test_from_seal.py`)

Wave 3b zip `a4f82556bf0fc26de5635a7c81ec8f5053951d4c64a3906c8e5dd474e3814d26` and wave 3 v3 zip
`152bca2a3c869212642f96514e7d485413727bf92cf67e9aff1774cefa532362`, both extracted fresh. Counts file
`TEST_COUNTS_R1W3B.json` (sha256 `77b6e4da514317a954143e5a31dfc69c716a35979964395162921bc7438eb28f`).

| Suite | Ran | Result | Seconds |
|---|---|---|---|
| wave 3b `tests_r1w3b.test_units_w3b` | 18 | OK | 17.54 |
| wave 3b `tests_r1w3b.test_kit_w3b` | 5 | OK | 0.43 |
| wave 3b `tests_r1w3b.test_run_w3b` (host, AWS only) | 3 | OK (skipped=3) — NOT_RUN_HERE | 0.20 |
| wave 3 `tests_r1w3.test_units_w3` (wave-3 zip) | 36 | OK | 3.17 |
| wave 3 `tests_r1w3.test_kit_r1w3` (wave-3 zip) | 5 | OK | 0.33 |
| wave 3 `tests_r1w3.test_run_r1w3` (host, AWS only) | 4 | OK (skipped=4) — NOT_RUN_HERE | 0.18 |
| wave 2 carried `test_units_r1w2` + `test_kit_r1w2` (wave-2 folder) | 34 | OK | 3.74 |
| `test_helm_end_to_end_loop` | 18 | OK | 1.08 |
| `test_helm_english_in` | 31 | OK | 0.69 |
| `test_helm_voice` | 22 | OK | 0.80 |
| `test_helm_triad` | 15 | OK | 0.50 |
| `test_helm_faces_in` | 16 | OK | 0.17 |
| `test_helm_chat_nuance` (pytest) | 5 | passed | 2.01 |
| language_v3: lm_t1 26, t1b 11, t1c 5, t1v3 26, lexicon_v2 19 | 87 | OK | 2.44 |
| repair_performer `test_all.py` | 16 | 16 / 16 | 1.62 |
| the_loop_v3 `test_all.py` | 35 | 35 / 35 | 0.72 |
| cube_store `test_all.py` | 21 | 21 / 21 | 0.23 |
| return_address `test_all.py` | 27 | 27 / 27 | 0.22 |
| wave 1 carried (v3 folder; 5 modules) | 128 | OK | 75.50 |
| **Total** | **526 run** | **519 passed, 7 skipped (AWS-only host tests), 0 failed** | |

The HELM suites are the ones inside the sealed wave-3 package: that is the brain wave 3b runs.

What the 18 wave-3b unit tests check: the family functions reproduce wave 3's `e16` / `f16` items for 5 seeds; the
fixtures are the generator's output and pass the 64-item check; the composition counts; the ANSWER keys follow from
the witness batches (8 items re-derived); the 48 UNKNOWN_INGREDIENT / UNIT_CHANGE items are questions by the English
reader's own rules (`UNKNOWN_INGREDIENT` 24, `UNIT_MISMATCH` 24); the format check refuses 6 kinds of bad file; the
text rule T3b (and that A1 alone fails on the store-read items); the arms are exactly the frozen ones and match
wave 3's pair spelling; 17 planned units; the readability rule numerically (E 52 readable, E 53 not, at FULL 60); the
marks; the same-brain projection; the reader end to end; the X3 seed rule (bands, 501-step gap test, STOP, pinned
derivation files, and a dummy-line derivation on the six real derivations: `overlap_check` PASS, both parts in band);
the receiver's check on a generated folder.

## 2. Plumbing dry run (`build/dry_run_r1w3b.py`, from the sealed extract; FIXTURES only)

15 arm units (every English-64 and Faces-64 arm), each a subprocess `python -B -m r1w3b.live64 run ...` through wave
2's dispatcher, workers 1: every one exit 0, 19.2 s in all (each about 1 s). The two reproduction units were NOT run:
they need the spent X2 files, which the builder never opens. `summary_w3b.build` and the frozen reader ran end to end:
verdict `INSTRUMENT_ERROR` as designed (no X3, no repro, no approval, no run record); hard gates H1, H8, H11 held.
Files: `dry_run/R1_W3B_HOST.json` (`97ab59c48de67a657cbd1ff0410f84a943d60bd52f1a0028990d6a7513164d13`),
`dry_run/R1_W3B_READING_DRY.json` (`f72b190ad360e426f4986e88440b92dade145e889f9b4883a074dfc61d482585`).

Fixture numbers, shown so the owner can see the machinery move (NOT results; fixtures are the builder's own):

| Arm | English-64 RIGHT / WRONG / UNDET / PLAIN / RIGHT+PLAIN | Faces-64 RIGHT / WRONG / UNDET / PLAIN / RIGHT+PLAIN |
|---|---|---|
| FULL | 60 / 0 / 4 / 64 / 60 | 60 / 2 / 2 / 64 / 60 |
| -ENGLISH_IN | 32 / 0 / 32 / 64 / 32 | 40 / 0 / 24 / 64 / 40 |
| -VOICE | 60 / 0 / 4 / 48 / 44 | 60 / 2 / 2 / 42 / 40 |
| -CUBE_STORE | 52 / 0 / 12 / 64 / 52 | — |
| -TRIAD | — | 36 / 26 / 2 / 64 / 36 |
| -ENGLISH_IN-VOICE | 32 / 0 / 32 / 4 / 0 | 40 / 0 / 24 / 0 / 0 |
| -ENGLISH_IN-CUBE_STORE | 32 / 0 / 32 / 64 / 32 | — |
| -ENGLISH_IN-TRIAD | — | 40 / 0 / 24 / 64 / 40 |
| -TRIAD-VOICE | — | 36 / 26 / 2 / 34 / 32 |

Pair numbers on the fixtures: CUBE_STORE x ENGLISH_IN E 36 of room 60 (slack 16), INTERFERENCE; ENGLISH_IN x TRIAD E 44
(slack 8), INTERFERENCE; ENGLISH_IN x VOICE E 44 / 40 (slack 8 / 12), SYNERGY on both; TRIAD x VOICE E 44 (slack 8),
INTERFERENCE. Replay: FULL = FULL_REPLAY on both fixtures.

## 3. Other checks

- The builder's probe of the wave-3 16-item fixtures under every needed arm (before the counts were set; the reason
  for the composition): every ANSWER item is lost both with the English reader off (it asks) and with the voice off
  (the reply is not plain); ASK items survive either single part off and are lost only with both off.
- Text-rule trap measured (packaged strings and fixtures only): 3 of 6 store questions already forbidden by wave 3's
  set, 6 of 6 with wave 3b's fixtures; 2 of 8 question forms, 5 of 8 with them. Hence T3b.
- Seal: two seals byte-identical (`build/seal_r1w3b.py`); 27 members + the freeze. `kit/job_supervisor.py` sha256
  `3b2337ca...` = wave 2's = wave 3's; `kit/plan_check.py` = wave 3's (`84257a23...`).
