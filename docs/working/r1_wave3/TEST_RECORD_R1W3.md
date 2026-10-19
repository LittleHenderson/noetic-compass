# TEST_RECORD_R1W3 — what was tested on the laptop before the seal (2026-10-19, Pacific)

Laptop MSI, Windows, Python 3.14, one process at a time (free RAM 950-1,200 MB at the times read). No AWS. No spend. No
torch. Everything below is a FACT about the code and the builder's fixtures; nothing here is a result about HELM.

## 1. All pure-Python suites, run from an extracted copy of the SEALED zip (`build/test_from_seal.py`)

Zip `2d5b4f0eab1c151c05194d6fe7ee2c3c247a55f3a7d91c2445cdf9cb186b45f7` (v1, now VOID_UNSIGNED; v2 in section 4). Counts file `TEST_COUNTS_R1W3.json` (sha256
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

## 4. v2 reseal: the cube store's read path repaired before signing (2026-10-19)

Coordinator's decision: the two cube-store faults in section 2 are plumbing, not what the CUBE_STORE switch measures;
the owner had not signed, so a reseal carries no governance drift.

- Old package `HELM_R1_W3_20261019_SOURCE_R1W3.zip` `2d5b4f0eab1c151c05194d6fe7ee2c3c247a55f3a7d91c2445cdf9cb186b45f7`
  (freeze `be1b321de2ef2545832b7281e7b53b7f263e6e381fd2b011783a550a447d3c65`): **VOID_UNSIGNED** (kept in `void_v1/`).
- New package `HELM_R1_W3_20261019_SOURCE_R1W3_v2.zip` `26b0ef7ed25c8431334d98ddf3a566704b105e53feab15103494cea9893f7bf3`
  (929,130 bytes), freeze `a72063f5223b04f01a428dfa55bfeb3fb9f45bec847286c41a5160f5761da1f3`, 205 members + the freeze,
  resealed byte-identical. Sources cut at thread commit `554fce5c`.
- Fixes: `turn.py` — the S6 "do we have X and Y" check needs the WORD `and` (it matched inside "hand"); `operations.py`
  `list_parts` — the latest branch to a part is its current word; a part whose latest branch is absent is not listed.
  Two new cube_store cases: before the fix 19 / 21 (both new ones FAIL), after 21 / 21.
- Diff between the seals (exactly 4 members; every other member byte-identical, incl. `FROZEN_R1W3.json` `e9777c2b...`):

| Member | v1 sha256 | v2 sha256 |
|---|---|---|
| `helm/SOURCE_CUT.json` | `a553ea923023f61887ea420c46fa0e2bde72643c6613a4eeae84bf5c4c9e65e7` | `970ad501504fbc5c7ab31e85b0ef4e5683bac4d4e0b08f97933ed131b97ea2f6` |
| `helm/docs/working/noetic_council/cube_store/operations.py` | `75a210eadfd1180f987107ec9a4afd25f3b0d7a834596addb3f35e099d496a9d` | `c3cc20aae0a7a5d7d9d1f0135aabb868c03bcbf382d2eb91dace9982a534834d` |
| `helm/docs/working/noetic_council/cube_store/test_all.py` | `91ec14d8a170e016e24bcfa80029f006cd94ac2cc7044afc4ee4200bb23b2540` | `0154df4fd1beac637d512421db0c99c35c75ef8a120de687eccef95d07e9da6b` |
| `helm/docs/working/noetic_council/cube_store/turn.py` | `3fb0020bd8810f69df643bf2f35545864c1886a5cc879f7a131507e9cef4c6c4` | `006bf3cb5f8da12cd35d928f78c036bcb8e32eefc02dbf98c277dc2ea19ab89c` |

- Full suite from the v2 sealed zip (`TEST_COUNTS_R1W3_v2.json`): 497 run, **493 passed, 4 skipped (AWS-only), 0
  failed** (as section 1, with cube_store now 21 / 21).
- Fixture check after the fix (not a result): the three English-16 store-read fixture items now read RIGHT under FULL
  (e.g. "Currently on hand: 15 Egg, 20 Sugar, 21 Salt." with the absent item no longer listed).
- The drive-loop rule and everything else are unchanged.

## 5. v3 reseal: amendment R1W3-A1, the text rule checks each item's statement only (2026-10-19)

Cause (`x2_custody\X2_BLOCKED_20261019T093121Z.json`): the receiver's checker and the host's first stage tested every
English-16 / Faces-16 turn whole, but the generator's last turn is one of 15 templated follow-up questions, 14 of which are
in the builder's practice files, so no seed could pass (the custodian's statement-only check: 0 statement hits).

- v2 `HELM_R1_W3_20261019_SOURCE_R1W3_v2.zip` `26b0ef7ed25c8431334d98ddf3a566704b105e53feab15103494cea9893f7bf3` (freeze `a72063f5223b04f01a428dfa55bfeb3fb9f45bec847286c41a5160f5761da1f3`): **VOID_SUPERSEDED_BY_A1**. It WAS signed by the
  owner; that approval does not carry over: the owner must sign again on the v3 hash.
- v3 `HELM_R1_W3_20261019_SOURCE_R1W3_v3.zip` `152bca2a3c869212642f96514e7d485413727bf92cf67e9aff1774cefa532362` (930,756 bytes), freeze `bd06f324a9643a8aacefab3d8ef52de4cf673a68820544897def95854b73d310`, 205 members + the freeze,
  resealed byte-identical.
- Change: `gen_live.FOLLOWUPS` (the 15 sentences, sha256 `14f5cb49c7fb60a0d40686d0d6b18e8d34aa81de0a61fed345d0f1749d751ef5`, tested equal to what the generator can produce),
  `statement_turns` (strips exactly one follow-up, only from the end of the last turn), `text_rule_hits` (statement only),
  `followup_tails` (the receipt); `check_x2_format` and `test_run_r1w3` record every stripped tail and the list hash. The
  generator's item code is unchanged (fixture determinism tests still pass). Three new tests: a statement repeating a
  forbidden sentence still FAILS; a file whose only overlap is a tail PASSES and its tails are recorded; the list hash.
- Diff between the seals (exactly 4 members; everything else byte-identical, incl. `FROZEN_R1W3.json` and `helm/`):

| Member | v2 sha256 | v3 sha256 |
|---|---|---|
| `r1w3/check_x2_format.py` | `2d7c21ccebeceb39a38d844b632db4e1d58e312c12a050bc7501fd3d6e8e49ab` | `56616457c5ad6d269f2c88024bfe792241d241a7b4971c67d11c7fb599cb8201` |
| `r1w3/gen_live.py` | `0809076a8ff92761a446a43c0572ff20074d8bdb480ef239b440e0b0b539d7c0` | `e296e003d8f6cf1cf8029afba85fdb114380cc2c930aace27455ab54b0a16038` |
| `tests_r1w3/test_run_r1w3.py` | `aeabeb78d056e4ee2db65eaf8bcf5b2253729e34985953a62b4bd09dd69df30b` | `3371789c62b54f19b1d10248337f0769588a08eb30707e95f11919d87fc1f17b` |
| `tests_r1w3/test_units_w3.py` | `0148245645e50de18fa882839ff1d709204aafb27c4df2bddbf76d971c3ec4a7` | `c43dee902a47a9bde10d05310c8c4a415321d72c49b4e0ee7190e8490fbe91b1` |

- Full suite from the v3 sealed zip (`TEST_COUNTS_R1W3_v3.json`): 500 run, **496 passed, 4 skipped (AWS-only), 0 failed**
  (wave 3 units now 36).
