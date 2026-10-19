# TEST_RECORD_R1W5 — builder tests and laptop dry run on PRACTICE files (facts, not claims)

Written 2026-10-19 (Pacific) by the wave-5 builder. Laptop MSI, 0 USD, no network, one python worker at a time (the
wave-4 builder's `worker.py` was checked for before each run; none was running). **Practice files only**: builder
seeds outside every band and every RB-I3 seed. Nothing here is scored; nothing here is a claim about X5.

Sealed package: `HELM_R1_W5_20261019_SOURCE_R1W5.zip` sha256
`b6598687190bc9e41f52695144eeeac5428913ab804f8bec64841093ea825d6c` (118,635 bytes, 37 members + the freeze);
`PACKAGE_FREEZE.json` sha256 `a325ea13b8851f9d8ed928dd73c2c3892315fa534fc876a146c6eb975bdc0334`; resealed
byte-identical.

## 1. Tests from the sealed extracts (`build/test_from_seal.py`, `TEST_COUNTS_R1W5.json` `ccc82353...`)

| Suite | Ran | Verdict | Seconds |
|---|---|---|---|
| wave 5 `tests_r1w5.test_units_w5` | 32 | OK | 26.77 |
| wave 5 `tests_r1w5.test_kit_w5` | 5 | OK | 0.44 |
| wave 5 `tests_r1w5.test_run_w5` (AWS only) | 3 | OK (skipped=3) | 0.21 |
| wave 3b `tests_r1w3b.test_units_w3b` (sealed wave-3b zip) | 18 | OK | 14.43 |
| wave 3b `tests_r1w3b.test_kit_w3b` | 5 | OK | 0.35 |
| wave 3 `tests_r1w3.test_units_w3` (sealed wave-3 zip) | 36 | OK | 3.08 |
| wave 3 `tests_r1w3.test_kit_r1w3` | 5 | OK | 0.34 |
| wave 2 carried units | 34 | OK | 3.48 |
| wave 1 carried (v3 folder) | 128 | OK | 72.18 |

Every process stayed under 300 s. One X5 unit (3 lives) peaked at 77 MiB.

## 2. Dry run (`build/dry_run_r1w5.py`, `build_dry_stdout.json` `9219a1d0...`, run from the SEALED extract)

39 units (all but the two reproduction units, which need the spent X3 files the builder never opens) through wave 2's
dispatcher, one at a time, 123.6 s in all; longest unit the job map, 33.0 s. Practice X5_PAIR file
`f556f7ce...` (11 lives, 7.2 MB). The reader ran end to end in 2.9 s and said `INSTRUMENT_ERROR` as designed (no X5
pins, no repro, no approval, no seal record); failing rows I1, I3, I4, I6, I7, I9, I10, I14 for those reasons only.
Rows that do not need the scored exam held: I11 (cut violator: 184-236 faculty calls and 207-267 attention steps in
conversation per life, all 9 lives), I12 (guard violator tripped on every idle tick: 976, 1,062, 1,010; the canary
write was refused in every life), I13 (D-W5-6: no-decline candidate - frozen = +8/9 points on C_NULL, band 5). Every
hard gate held (H1-H10, H12).

### Practice marks (what the reader would say if the instruments held)

| Mark | Practice value | Rule |
|---|---|---|
| (a) NO_HARM | E64: FULL 61, candidate 61 (loss 0); F64: 60 and 60 (loss 0) | loss <= 2 |
| (b1) BEATS_RIVALS | candidate 26450/381 = 69.42 points; RANDOM 37.01; ROUND_ROBIN 33.86; gaps 32.41 and 35.56; per life >= 30.5 | >= 20 pooled, >= 10 per life |
| (b2) LEARNING_CONTROL | FROZEN 38.39 <= 37.01 + 5; candidate - FROZEN = 31.04 | both |

3-valued, family A pooled (RESOLVED / WRONG / UNDETERMINED of 1,524): candidate 1,058 / 0 / 466; FULL 600 / 0 / 924;
RANDOM 564 / 0 / 960; ROUND_ROBIN 516 / 0 / 1,008; FROZEN 585 / 0 / 939.

### Practice pair words (family A pooled, denominator 1,524, margin 381/2 = 190.5)

| Pair | L_a (EYE_PAIRING) | L_b (part) | L_ab | E | Slack to ceiling | Word |
|---|---|---|---|---|---|---|
| EYE_PAIRING x CASCADE | 458 | 165 | 605 | 623 | 244.5 | ADDITIVE |
| EYE_PAIRING x CUBE_STORE | 458 | 210 | 652 | 668 | 199.5 | ADDITIVE |
| EYE_PAIRING x ENGLISH_IN | 458 | 162 | 626 | 620 | 247.5 | ADDITIVE |
| EYE_PAIRING x TRIAD | 458 | 130 | 620 | 588 | 279.5 | ADDITIVE |

All four readable with room. The job map held on all 5,606 practice items: with each part off, exactly its kind
failed (CASCADE 834, CUBE_STORE 814, ENGLISH_IN 803, TRIAD 795 items) and no other item changed.

### Practice reported rows

- R1 geometry: FR variant - candidate = +1.71 points (A), -4.48 points (B).
- R2 best cell = true best faculty: 7, 6, 7 of 7 (A); 3, 5, 6 of 7 against the new key at the end of B.
- R3 drift (Q9): sessions to recover after the planted change: candidate not by session 32 / 14 / 3; FR not / not /
  13; FROZEN not / not / not.
- R5 declines (Q5): candidate 347 on A (about 116 per life), 456 on B, 468 on C; live exams 3 and 2.
  **The decline rule COSTS points on practice**: the no-decline counterfactual scored 74.21 against the candidate's
  69.42 on A (+4.79 points), and on C_NULL the candidate sat 6.22 points BELOW the frozen table while the no-decline
  arm sat 0.89 above it. This is why D-W5-6 exists (section 3).
- R6 RB-I1 dynamic pair-cap would-trips (Q6, reported only): candidate 245 on A (about 82 per life), FULL 16.
- Live exams: the drive loop resolved 44 and 41 backlog items in the idle gaps, was offered 234 and 278 ticks in
  conversation and made 0 faculty calls there; records identical to FULL item by item.

## 3. Changes made after the first full practice run (each a numbered deviation in the preregistration)

- **D-W5-6** (instrument row I13). First full practice run: I13 failed (candidate - frozen = -6.22 points on C_NULL).
  Cause, traced: the Q5 decline rule fires only when the Eye's table has learned (a cell with >= 4 tries and score
  below 1/4); the frozen table never declines. So the two arms differ in two things, not one, and on the null world
  the declines cost points. The null control's job (RB-I3's I1) is to catch an invented pairing GAIN from table
  learning. Fix: I13 compares `FULL+EYE_PAIRING_NODECLINE` with `FULL+EYE_PAIRING_FROZEN` (like for like); the
  candidate's own gap is reported beside it. The NODECLINE arm was added to C_NULL. No deciding mark changed; the
  decline rule itself was NOT changed (it is the coordinator's PROPOSED Q5 default, for the owner to keep or override).
- **D-W5-5** (reported arm `FULL+EYE_PAIRING_NODECLINE` on A) was added before the full practice run, after a one-life
  smoke test showed about 100 declines per life, so the owner can see what Q5 costs or gains.

## 4. Builder predictions that the practice run already missed (kept as written)

- Q5 declines "a few dozen per life at most": about 116 per life on A.
- RB-I1 would-trips "> 100 per life": about 82 per life for the candidate, about 5 for FULL.
- Drift recovery "about 5-12 sessions": practice 3, 14 and one not by session 32.
