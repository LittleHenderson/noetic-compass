# TEST_RECORD_R1W3 — what was tested on the laptop before the seal (2026-10-19, Pacific)

Laptop MSI, Windows, Python 3.14, one process at a time (free RAM 950-1,200 MB at the times read). No AWS. No spend. No
torch. Everything below is a FACT about the code and the builder's fixtures; nothing here is a result about HELM.

## 1. All pure-Python suites, run from an extracted copy of the SEALED zip (`build/test_from_seal.py`)

Zip `2d5b4f0eab1c151c05194d6fe7ee2c3c247a55f3a7d91c2445cdf9cb186b45f7`. Counts file `TEST_COUNTS_R1W3.json` (sha256
`ae40ea05e8f946dbd2afabe53f4afc52ea0f2138a341057cd7ac5116b399ee10`).

| Suite | Ran | Result | Seconds |
|---|---|---|---|
| wave 3 `tests_r1w3.test_units_w3` | 33 | OK | 4.31 |
| wave 3 `tests_r1w3.test_kit_r1w3` | 5 | OK | 0.40 |
| wave 3 `tests_r1w3.test_run_r1w3` (host, AWS only) | 4 | OK (skipped=4) — NOT_RUN_HERE | 0.20 |
| wave 2 carried `test_units_r1w2` + `test_kit_r1w2` (wave-2 folder) | 34 | OK | 3.68 |
| `test_helm_end_to_end_loop` | 18 | OK | 1.07 |
| `test_helm_english_in` | 31 | OK | 0.65 |
| `test_helm_voice` | 22 | OK | 0.88 |
| `test_helm_triad` | 15 | OK | 0.50 |
| `test_helm_faces_in` (new) | 16 | OK | 0.21 |
| `test_helm_chat_nuance` (pytest) | 5 | passed | 2.23 |
| language_v3: lm_t1 26, t1b 11, t1c 5, t1v3 26, lexicon_v2 19 | 87 | OK | 2.44 |
| repair_performer `test_all.py` | 16 | 16 / 16 | 1.58 |
| the_loop_v3 `test_all.py` | 35 | 35 / 35 | 0.79 |
| cube_store `test_all.py` | 19 | 19 / 19 | 0.24 |
| return_address `test_all.py` | 27 | 27 / 27 | 0.28 |
| wave 1 carried (v3 folder; 5 modules) | 128 | OK | 73.21 |
| **Total** | **495 run** | **491 passed, 4 skipped (AWS-only), 0 failed** | |

Torch parts: NOT_RUN_HERE (the X2 Gate B regeneration I5 and the custodian's Gate B worlds; AWS only).

## 2. Plumbing dry run (`build/dry_run_r1w3.py`; exposed data and FIXTURES only; run on the tree before the final
## FROZEN / README / RUN_LIMITS / NOT_IN_WAVE-text / seed-rule-option edits, none of which touches a unit's code path)

62 units, every one exit 0, 52.2 s: wave 2's carried Gate B arms on E1 (c21's exposed worlds), the Gate B pair arm
A1_GATE_LC on E1, every arm of X2-E16 / X2-F16 / X2-CASC / X2-IDLE on the builder's fixtures. `summary_w3.build` and
the frozen reader ran end to end: verdict `INSTRUMENT_ERROR` as designed (no X2, no torch I5, no Task B, no depth, no
approval). Files: `dry_run/R1_W3_HOST.json` (`a8d00bdf...`), `dry_run/R1_W3_READING_DRY.json` (`96e426b4...`).

Fixture numbers, shown so the owner can see the machinery move (NOT results; fixtures are the builder's own):
- Cascade (64 fixture chains): FULL GOOD 64 / WRONG 0, 209 descents; FIXED_CAP GOOD 60 (the 4 depth-6 chains hit the
  cap), 752 descents; -CASCADE 36 / 28 WRONG; -EYE 56 (stale-consolidation family WRONG); -ATLAS 56 (return attacks
  WRONG); -CUBE_STORE 56 (stale family WRONG, 947 descents: nothing is ever consolidated); -TRIAD 56 (face-shock WRONG).
  DECOUPLING word on the fixture: DECOUPLING_EARNED (24 / 24 fewer descents, every C2 fault found).
- English-16 fixture: FULL 12 RIGHT / 3 WRONG — the 3 WRONG are the store-read family: the cube store listed an absent
  item ("None Water") and sent "What do we have on hand?" to FIND_SHARED_PART. -CUBE_STORE: 0 WRONG (it cannot answer
  a store question, so it asks). These are real defects of the cube store's read path, found here; not fixed (they are
  what wave 3 measures; a fix would be a separate repair and a reseal).
- Faces-16 fixture: FULL 12 RIGHT / 1 WRONG (a paraphrase with no cue word, missed silently as designed); -TRIAD 4 / 8.
- Idle fixture (173 items): FULL 52 resolved, -DRIVE_LOOP 37, reported FIXED_TABLE_RR 103. The builder did not change
  the drive loop after seeing this.

## 3. Other checks
- Gate B pair arm on exposed c21 worlds: teach ran with driver arm `rb_roundrobin_gate_off`, policy `roundrobin`, 512
  ticks, 512 keyed episodes, every admitted write receipted.
- Depth adapter: `r1w3.d34_x2 preflight` ok (197 files, 0 bad); part D00 on X1's exposed depth files through an X2-shaped
  pins file: COMPLETED in 37.35 s, 10 / 10 code tests.
- X2 seed rule: whole 1,000,000-wide bands free; GB 954 / 1,000, TB 23 / 33, D34 31 / 45 free slots; a dummy-line
  derivation printed `overlap_check: PASS`, every part `in_band: true`; the `--start-slot E16=5` step also PASS.
- Seal: two seals byte-identical (`build/seal_r1w3.py`); 205 members + the freeze.
