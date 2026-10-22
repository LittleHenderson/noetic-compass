## 22. Amendment A-R1W7-10 (v9, written BEFORE the v9 reseal; the HELM cut moved to the reader v7.2 fix after job c55 read CHAT_WAVE_HARMED; three changes, nothing else; 2026-10-21)

**Why.** The v8 package (zip `e88b125e3079f0fa79045fec888d4e862a5a742cf82010de6872bdc621f865c7`, freeze `50e03e17…`,
HELM cut `b10da2cd`, amendment A-R1W7-9, line `CHAT WAVE 5 at 1 USD`) ran as job c55 (SPEC 7.116) and the frozen reader said
verdict **`PASS`** (every instrument row and every hard gate true) and status word **`CHAT_WAVE_HARMED`**: mark K3 SAFE false
— X7_CONV `CHAT_ON` 62 right / **2 WRONG** / 0 undetermined, X7_NOISE `CHAT_ON` 62 / 2 / 0, `LOOP_ON` 59 / 2 / 3 (the same 2
in the loop driven directly), and **1 wrong lesson** on a real recipe (`RW:pg:8501@89139`, lesson 7 of 8); real-recipe answers
93 of 94 right, 0 wrong; K4 HONEST true for the first time (0 unexplained asks); K1 92 of 94 learned. The per-item replay by
program on the hashed units (SPEC 7.116 "Mechanism", SPEC 7.117; no exam text was read back) found two mechanisms, not
accidents: **(1) the two wrong dialogue answers** — each clause was shaped like a face statement about an ingredient the brain
did not hold under that name (one named a held ingredient by a plural/spelling form the name matcher did not reach; one shared
nothing with any held name); the face reader (names as given) read `NONE`, the stock stayed recorded, and the question answered
the raw yield where the key wanted the face applied (S2) or an ask (S5); **(2) the wrong lesson** — a measure phrase after a
separator ("…, a dash of X") was folded into the line before it as a note, so X's running-out was resolved onto that line's
ingredient and a wrong amount (a factor 24 off) was learned. The fix is reader **v7.2** (SPEC 7.117; PR #447, merged on the
thread = head `55cda1e2`): `helm_faces_in.py` v2.2 (every lexicon row also compiled with its name slot open; in names-as-given
mode a face-shaped clause that matches no held name returns `CLARIFY` with code `FACE_UNKNOWN_INGREDIENT` or
`FACE_UNKNOWN_PRODUCT`; plural and spelling forms `-oes`, `-ves`, `-o` / `-f` / `-fe` stems widened) and `helm_wide_turn.py` reader
`RB-W1 v7.2` (such a clarify that withdraws no stock sets `wide_face_block`, and the wide question returns `CLARIFY_WIDE_<code>`
— an ask, no amount said — until a stock the reader takes in full lifts the hold; a measure phrase after a separator is its own
line; a ran-out phrase is resolved through a line's OWN words only, never through a neighbour's notes); `test_helm_reader_gap.py`
grows to 35 tests (7 new, 5 of them failing on v7.1); `test_helm_brain_wide.py` one exact-shape test gains the new `own` key;
`test_helm_cas_address.py` carries the recomputed OFF-path pin `79e4914a561851d2cd19d04902f38e869787e36db0e984302bbbc6c434fa698c`
over the same machine-neutral canon. c55's record stands as the last sealed word; **v8 is `VOID_SUPERSEDED_BY_V9`** for any
further run (nothing of v8 is moved or deleted; its line was consumed by c55 and may bind no second zip).

**What changed in this package (v9). Exactly these three, nothing else.**

1. **`helm_now/` recut at `55cda1e21f7e6ea0048fe2faf7e90f23e4ec9525`** by the contract's rule (the v8 cut's 167 files + every
   `helm_*.py` / `test_helm_*.py` at the commit; `helm_test_pins.py` named explicitly; each by `git show`, never the working
   tree): **167 files, the same names as v8**; five files changed — `helm_wide_turn.py` `c9e8a078…` (reader `RB-W1 v7.2
   (2026-10-21)`), `helm_faces_in.py` `2f7d4b57…` (v2.2), `test_helm_brain_wide.py` `8ad4a0ba…` (the `own` key),
   `test_helm_cas_address.py` `06889a63…` (pin `79e4914a…`), `test_helm_reader_gap.py` `3eed47af…` (35 tests); every other file
   equal to v8's cut; `helm_brain_canonical.py` = base `d4488f2a` `24df53c9…`. `contract/HELM_CUT_R1W7.json` carries the commit
   and all 167 hashes. The wide reader's ask statuses are unchanged in kind: every one begins `CLARIFY`, so RB-W1T's
   `keys_rbw1t.is_asking` prefix rule counts it as an ask (checked by program over the source of both cuts by regular
   expression, `ASK_PREFIX_CHECK_v9.json`; v7.2 adds `CLARIFY_WIDE_FACE_UNKNOWN_INGREDIENT` and `CLARIFY_WIDE_FACE_UNKNOWN_PRODUCT`,
   both asks); the reader's rules are not changed (`score_w7.py`, `merge_r1w7.py` byte-identical to v8).
2. **Exclusions.** `contract/EXCLUDE_R1W7_PRIOR_USED.json` gains block `X7v8_c55` = lists `X7v8_c55_real` (X7v8's 128 REAL ids)
   and `X7v8_c55_conv` (64 CONV pool ids), read by program from the custodian's seal record
   `x7v8_custody\X7_SEALED_20261021T170704Z.json` (ids only; never an input or key file); 0 overlap with every older list
   (24 lists, 2,234 distinct ids). Every list applies to both pools (A-R1W7-4, kept). `custody_w7.REAL_EXCLUDE_LISTS` and the
   tests name the two new lists.
3. **Seed bands, line and labels.** Bands (section 10 superseded again): REAL 2,036,000,001-2,037,000,000; CONV
   2,038,000,001-2,039,000,000; NOISE 2,040,000,001-2,041,000,000 (each 1,000,000 wide; below INT32_MAX 2,147,483,647). Used
   table 1-2,035,000,000 as one range (everything up to v8's 2,030-2,035 M, spent by X7v8 / c55; v7's 2,024-2,029 M reserved
   by the void v7 seal inside it; the continuity packet's reserved 1,996-1,999 M and the talk packet's reserved 2,018-2,022 M
   inside it); gap 1,000,000; slot stepping and STOP as before. **The owner's line to sign is `CHAT WAVE 6 at 1 USD`** (20 UTF-8
   bytes, the inner text without quote marks; the v8 line `CHAT WAVE 5 at 1 USD` was consumed by job c55 and may bind no second
   zip; whether this line stands is the owner's word — nothing here approves anything). Seed text
   `H = sha256(UTF-8("CHAT WAVE 6 at 1 USD" + ":" + <v9 zip sha256, 64 lower-case hex>))`, no trailing newline. Labels:
   `PACKAGE_VERSION` = `v9`; the cut commit in `kit/run_r1w7.py` and the stage note; `RUN_LIMITS_R1W7.json`; README; the
   custodian procedure; FROZEN re-derived from the constants (the kit test checks they agree); the tests that pin the bands, the
   blocked table, the exclusion lists and the cut size.

**Kept exactly as v8 (checked by the tests and the freeze):** the host's HELM self-check list of **12 names** (`kit/run_r1w7.py`
`HELM_TESTS`; the A-R1W7-6 rule kept: the seal step runs exactly that list with the host's command form from a fresh extract and
records it in `TEST_COUNTS_R1W7_v9.json` under `host_exact_suite_list`); **amendment A-R1W7-7** as applied (the same one import
and one hook in `custody_w7.make_all`; the same measured effect on the practice draw, 6 of 128 items `NOT_SCORED`); cap 1.00
USD; one attempt + one plumbing retry; the v4 reader (`r1w7.merge_r1w7 v2`), the v4 recorder unit and fixture, every mark,
threshold, arm, status word, exam size, instrument row and hard gate; the noise sentences; the five neighbours by freeze; the
practice pools; the scoring functions; the units and their commands.

**What this amendment does not do.** It does not re-read c55. It does not launch. It does not draw an exam. It licenses
nothing. Reader v7.2 is `ENGINEERED-NOT-VALIDATED` until a sealed draw. The practice run from the v9 seal (run11) is read
beside v8's run10 and v7's run9 in `PRACTICE_READINGS_V9.json`, every differing number with its cause; a WRONG dialogue
answer remaining on practice is a STOP (recorded, `FLAG_FOR_HUMAN_REVIEW`, HELM not changed in the seal). A fresh draw can still
miss a mark on a shape no practice run has shown: c55's two wrong items were shapes the practice dialogues never showed.
