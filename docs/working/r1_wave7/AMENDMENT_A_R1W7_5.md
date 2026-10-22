## 17. Amendment A-R1W7-5 (v5, written BEFORE the v5 reseal; owner order 2026-10-20 "third chat round"; 2026-10-20)

**Why.** The v4 package (zip `8602b1bc98b543e4551e766d9db540d22d6dbc690b788dbbce5c91e4b6c7b712`, freeze `948cf691…`,
HELM cut `dfc7158d`) ran on the host as job c52 (`RUN_RESULT_R1W7V4_C52.md`; reading `R1_W7_READING.json` sha256
`bcb2f372a4c9c1600d86ce17c96fe15fec6a0969324c33f9250706f6fd38dd8b`). The frozen reader said verdict `PASS`, word
`CHAT_WAVE_NO_GAIN`: every instrument row true, all 10 hard gates true (HG5 held: the c51 failure was the reader), five of
six marks true, **K4 HONEST false: `unexplained_asks_strict` 1** (the wave-6 rule also 1), the same count in LOOP_ON, so the
cause sat in the brain, not in the chat window. Under the frozen order of words a missed gain mark is `CHAT_WAVE_NO_GAIN`;
nothing was licensed. The owner ordered a third round. Line 4 of this document forbids re-reading c52's data; the c52 word
stands. **v4 is `VOID_SUPERSEDED_BY_V5`** for any further run (its c52 record stands as written).

**The cause (found on the laptop by program from the unit outputs, never from the sealed inputs or keys; the diagnosis
`K4_ITEM_DIAGNOSIS.md` beside the zip names the item by id only).** One real recipe carries, after an ingredient line, an
amount of a CONDITION — a temperature ("<number> degrees Fahrenheit") set off by commas. The wide reader
(`helm_wide_turn.split_lines` / `starts_line`) cut the sentence at that amount and `parse_line` bound the piece as an
ingredient named by the condition words. The brain admitted every batch with a five-name support set for a four-ingredient
recipe, learned all four real lessons exactly, recorded the stock (which carried the same fifth name), and at the question
asked for "one batch where <condition> ran out first": `UNDETERMINED_CLARIFY` with every lesson LEARNED and stock
STOCK_RECORDED, exactly the shape K4 counts. The other 16 asks on ANSWER-keyed items were all explained (18 items where no
lesson was admitted, 3 where one lesson was refused; counts in the diagnosis).

**What changed in HELM (commit `f45a85706a9d8b9177e4b7279453d1538c12045d`, branch `claude/helm-r1w7-round3-fix-20261020`, PR #425
to the thread, 1 commit on thread head `1d2b390f`; FIX FIRST round 3).** `helm_wide_turn.py` only: a general rule,
`condition_fragment()` — an amount followed by a temperature / time / head-count / percentage noun (`CONDITION_NOUNS`, the
wide reader's own copy of the family in `helm_english_in.IGNORED_COUNT_NOUNS`; a bare `F` / `C` only when nothing follows
it, so "2 c flour" stays two cups of flour) is a NOTE on the ingredient line before it, never an ingredient line;
`starts_line` returns False for it; `split_lines` holds a leading condition piece for the first ingredient line;
`parse_line` asks `NO_NAME` when a whole line is only a condition. No special case for any item. `helm_brain_canonical.py`
is byte-identical to its base. `READER_VERSION` string unchanged (`test_helm_cas_address` pins the OFF-path trace bytes).
Test `test_helm_wide_alongside.G_ConditionPiecesAreNotIngredients` (3 tests, the author's own sentences in the same shape,
never the exam line): 3 of 3 fail on `1d2b390f`, 3 of 3 pass on the fix. Every `test_helm*.py` suite passes after.

**What changed in this package (v5). Exactly these, nothing else.**

1. **`helm_now/` recut at `f45a85706a9d8b9177e4b7279453d1538c12045d`** by the contract's own rule (wave 6 v3's 159 files + every
   `helm_*.py` / `test_helm_*.py` at the commit, each by `git show`, never the working tree): **164 files** (v3/v4: 161).
   The three new files — `helm_cas_address.py` (imported by `helm_end_to_end_loop.py` since the "Build both" commit
   `9916d7da`, switch `CAS_ADDRESS` default OFF, byte-identical OFF path), `test_helm_cas_address.py`,
   `test_helm_units_note.py` — entered the thread between v4's cut and this one. `contract/HELM_CUT_R1W7.json` carries the
   commit and all 164 hashes; `helm_brain_canonical.py` = base `d4488f2a` `24df53c9…`. The host's HELM self-check
   (`kit/run_r1w7.py` `HELM_TESTS`) gains the two new unittest files (10 files).
2. **Exclusions:** `contract/EXCLUDE_R1W7_PRIOR_USED.json` gains block `X7v4_c52` = lists `X7v4_c52_real` (X7v4's 128 REAL
   ids) and `X7v4_c52_conv` (64 CONV pool ids), read by program from the custodian's seal record
   `x7v4_custody/X7_SEALED_20261021T050521Z.json` (ids only; no input, key or exam file opened). Every list applies to
   BOTH pools (A-R1W7-4 rule kept): 18 lists.
3. **Seed bands** (section 10 superseded again): REAL 2,006,000,001-2,007,000,000; CONV 2,008,000,001-2,009,000,000; NOISE
   2,010,000,001-2,011,000,000 (each 1,000,000 wide; below INT32_MAX 2,147,483,647). Used table 1-2,005,000,000 as one range
   (everything up to wave 6 v3; wave 7 v3 / c51 1,990-1,995 M; the continuity packet's reserved 1,996-1,999 M; wave 7 v4 /
   c52 2,000-2,005 M, spent by the X7v4 draw); gap 1,000,000; slot stepping and STOP as before.
4. **The owner's line** (section 8 superseded again): **`CHAT WAVE 3 at 1 USD`** (20 UTF-8 bytes; `CHAT WAVE at 1 USD`
   was consumed by c51's approval record, `CHAT WAVE 2 at 1 USD` by c52's `9e4058a9…`; neither may bind a second zip).
   Seed text `H = sha256(UTF-8("CHAT WAVE 3 at 1 USD" + ":" + <v5 zip sha256, 64 lower-case hex>))`, no trailing newline.
   Cap 1.00 USD; one attempt + one plumbing retry; expected about 0.01-0.02 USD.
5. Labels: `PACKAGE_VERSION` = `v5`; `RUN_LIMITS_R1W7.json` `package_version` and the line in `cost_cap_status`; the
   stage note; README; the custodian procedure; FROZEN re-derived from the constants (the kit test checks they agree);
   the tests that pin the bands, the line, the blocked table, the cut size and the exclusion lists.

**Unchanged (checked by the tests and the freeze):** the v4 reader (`r1w7.merge_r1w7 v2`, HG5 names a missing list), the
v4 recorder unit and fixture, every mark, threshold, arm, status word, exam size, instrument row and hard gate; the noise
sentences; the five neighbours by freeze; the practice pools; the scoring functions; the units and their commands.

**What this amendment does not do.** It does not re-read c52. It does not launch. It does not draw an exam. It licenses
nothing. Forecast: on c52's exam the one K4 miss is removed by the fix on the laptop (the item answers, `SUCCESS_EVALUATED`);
a fresh draw can still miss a mark on a shape no practice run has shown.
