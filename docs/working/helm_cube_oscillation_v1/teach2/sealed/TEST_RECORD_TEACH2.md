# TEACH-2 — build, practice and seal record (2026-10-22, 0 USD)

Owner's words: "Yes: pin the CUBE TRAIN weights into the TEACH-2 package and seal it (0 USD), ready for the CUBE EXAM at 1 USD."

## The seal

- Zip `C:\Users\wakil\Documents\Codex\2026-10-22\teach2\HELM_TEACH2_20261022_SOURCE.zip`, sha256 **`89642df571ff602539dad5218e9909f27f7e2fd36b747b047b326840bb2fb2b9`**, 117,471,787 bytes, 349 members; sealed twice, byte-identical.
- PACKAGE_FREEZE sha256 `747b747c74420ea2c77b7f83a99bba624b9395659ff74c43773bb985d98df23f` (this folder). The zip is not in git (size).
- HELM cut: commit `9365331d38ca3ec0a9b62ee9b636026b5e2a02d1`, 190 files (`HELM_CUT_TEACH2.json`, this folder).
- CTT weights pinned (I16): A4-s1 `c39eafb6…`, A4-s2 `3bfbf1f0…`, A4-s3 `6418ef1e…`, A5-s1 `07a54adc…` (the c57 finals; spec 7.125 follow-up 17).
- PREREGISTRATION_TEACH2.md = pre-code `f7b6183b…` + amendments A-TEACH2-1 to -22, byte for byte (this folder).
- From a fresh extract (`TEST_COUNTS_TEACH2.json`): package tests OK (26); cut + CTT check OK; HELM's suites OK; a practice exam of 2 worlds built; route check 0 bad; the pool on 1 world with all 11 arms (the CTT on the laptop's own GPU) all exit 0; package members unchanged after.
- Backup: `D:\tksCAS-archive\teach2_seal_20261022\` (zip, freeze, sha file, test counts; source = destination; digest `79db23e4…`).

## Amendments written during the build (all before their code; all before any exam world)

- **A-TEACH2-18** (`4b8b529a`): how the package is built: pinned weights, one audited GPU server per unit, the exam on one GPU host at the same 1 USD cap (the decoder needs a GPU), the 11 arms, limits by a frozen rule, the TRAP plan, checkable gates, seed bands 2,053–2,060 M.
- **A-TEACH2-19** (`a5c4d4ff`): two contradictions corrected — HG-WRONG-CUBE and U2 apply to the arm under test (CUBE_OSC, REPLAY), not to the rivals whose errors C2 and C3 expect; the reader's counting rules frozen. **For the owner's review.**
- **A-TEACH2-20** (`a29ebaf4`): practice round 1 showed the TRAP decoy taken from CUBE TRAIN ("while <another yard> was quiet in <month>") named another yard, so quote memory answered another fact's question with it; decoys brought back to the pre-code's three (odd "not", second number, a month of another yard only); U1 counts TRAP-fact items apart (quoting a two-number line is what the cube arms are tested against). **For the owner's review.**
- **A-TEACH2-21** (`0aa9ced6`): four MAJOR defects found by the one independent review round, fixed: TABLE source lines (line numbers repeat without a compactor), HG-LIMIT's stretch rule (HELM raises a flag once per stretch), HG-HOLD's scope (an honest RECONSTRUCTED cube answer is not "served from a held record"), the custodian's turn check (now compares every turn with its plan slot and recomputes the keys' agreement). Plus two hardenings (a wrong-shaped CTT reply = a dead server; the seal refuses on any failing test or a harness that differs from the commit).
- **A-TEACH2-22** (`91c8ea21`): FIX FIRST in HELM, found by practice round 3 — a question naming a month was answered from another month's fact (all cube and table arms), and a TABLE answer from a dropped line was labelled EXACT. Fixed in `helm_cube_osc.py` behind the switch (OFF path untouched); 4 tests written first (3 failed on the old code); HELM suites 280 unittest + 212 pytest pass.

## Practice rounds (builder practice worlds, rule-written turns; facts that decide nothing; a practice reading is INCONCLUSIVE by I0)

| Round | Worlds | Units | What it showed |
|---|---|---|---|
| 1 | 4 | 44, all exit 0 | U1 false on one answer (the "other yard" decoy, A-TEACH2-20); HG-H8 false on TABLE (harness had no source line, A-TEACH2-20 D3) |
| 2 | 4 | 44, all exit 0 | every hard gate held; U1 64/64 right, 0 wrong |
| 3 | 2 | 22, all exit 0 | after the review fixes: HG-H8 false on TABLE (a real HELM label defect), U2 false (month defect) → A-TEACH2-22 |
| 4 | 2 | 22 + suites | HELM fix in: U2 holds, 0 WRONG_T in every arm; HG-H8 3 of 804 (the harness read the truth after the turn, not at the answer) |
| 5 | 2 | 22, all exit 0 | harness takes the truth inside the answer call (K4 as written): HG-H8 804/804; every hard gate held (HG-TESTS skipped by choice in this round) |

Practice facts kept as they are (negatives included):
- **C1 not met in any round** (CUBE_OSC − QUOTE_ONLY on Q-REFRESHED, summed over the round's worlds: round 1 +1, round 2 0, round 4 0; +8 needed over 16 worlds): on rule-written practice lines today's quote memory already answers almost everything. 🟥 forecast for the exam: `CUBES_NO_GAIN` unless AI-written turns are harder for quote memory.
- **S-SPACE (a) not met in any round** (round 2: 14,649 against 19,363 bytes; needs at most half): teaching lines that hold a not-yet-confirmed fact are protected and never fade, and on short worlds they are most of memory. 🟥
- CUBE_OSC stored 99 cubes on 4 practice worlds with 0 wrong; the rule-reader rival ONE_READER stored 14–17 wrong (C3 met by that route); CTT_ONLY equalled CUBE_OSC on practice lines (the rounds added nothing there).
- REPLAY equalled CUBE_OSC exactly in every round (HG-REPLAY).
- The memory size limit came out at 2,400–2,500 bytes on practice worlds; over-limit stretches were always named by HELM (HG-LIMIT held).

## The review round

One independent AI reviewer read the code (ran nothing): 0 BLOCKER, 4 MAJOR (fixed, A-TEACH2-21), 5 MINOR (two fixed as hardenings; N5 fixed in round 5; N1 reported — by the pre-code §9 as frozen, C4 between 2 and 4 lost items is neither NO_GAIN nor HARMED; N4 cosmetic).

## Next

A custodian session (not the builder) follows `contract/CUSTODIAN_PROCEDURE_TEACH2.md`: approve from the recorded line `CUBE EXAM at 1 USD`, draw, have the 512 turns written by three model families and keyed by two others, finish. Then `CUBE EXAM at 1 USD` on one GPU host; the frozen reader prints the word.
