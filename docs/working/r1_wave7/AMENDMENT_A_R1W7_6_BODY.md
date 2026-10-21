
## 18. Amendment A-R1W7-6 (v6, written BEFORE the v6 reseal; owner order 2026-10-21 "Fourth chat round: fix the platform-bound pin test, run the host's exact test list from the seal, reseal v6 at 0 USD, then give me the line"; 2026-10-21)

**Why.** The v5 package (zip `%(v5)s`, freeze `8cc543d2…`,
HELM cut `f45a8570`) ran on the host as job c53 (`RUN_RESULT_R1W7V5_C53.md`; reading `R1_W7_READING.json`). The frozen reader
said verdict `INSTRUMENT_ERROR`, status word `INCONCLUSIVE`: all 10 hard gates true, all six marks true as facts (K4 0: the
round-3 fix held on fresh data), but instrument row I6 (`suites_ok`) false because HELM's own suite on the host read
`Ran 236, FAILED (failures=1, skipped=2)`: `test_helm_cas_address.C_LoopStamps.test_off_is_byte_identical_to_the_pre_change_code`
compared the sha256 of the OFF records (host `6bf323adcde8e01391125280f0f88ec6cb94b9e5ef2baff2a3b45c7f778e9606`) with the one
stored value `56f356ea7302a80fd7073c6b76335fb7453ee32ac2950e1c2e4a1cf18b64acc8` (computed on the laptop, Windows, Python 3.14.0,
base 159c7d2b). The same test passes on the laptop on the same cut. The test had never run on a host before (the v5 cut rule
pulled it in). Line 4 of this document forbids re-reading c53's data; the c53 word stands. **v5 is `VOID_SUPERSEDED_BY_V6`** for
any further run (its c53 record stands as written).

**The cause (proven on the laptop by program; `PIN_TEST_DIAGNOSIS.md` beside the zip).** The only value in the hashed records
that depends on the machine is the absolute path of the wave-1 brain folder: `helm_brain_canonical.load_package` writes it as
`brain_dir` into the two brain trace rows, and the two turn receipts of those turns hash over the rows (`_h16` in the loop).
With the same brain at another laptop folder, exactly 6 leaves of the records differ (2 `brain_dir`, 4 `receipt_hash` = 2
distinct values). Making the loop report the host's path (`/opt/helm-shared-r2/sources/w1/HELM_R1_W1_20261015`) on the laptop
gives `6bf323ad…` exactly, on the v5 cut and on base 159c7d2b; reporting the laptop's default folder gives `56f356ea…` on both.
So the host's OFF path WAS byte-identical to the pre-change code; the test held one machine's value. Not the platform, not the
Python version, not line endings.

**What changed in HELM (commit `%(fix)s`, branch `claude/helm-pin-hygiene-2-20261021`, PR #429 to the
thread, 1 commit on thread head `5f07c5d7`; written by a second builder on the owner's direct order; the commit hash is
unchanged by a merge, so the cut names it whether PR #429 is merged before or after this seal).** A first pass
(`3dae274f`, PR #428, merged as `5f07c5d7`) replaced absolute paths by their last component; the v6 builder's diff found it
insufficient (the laptop and host folders have different last components, and the receipt hashes are computed inside the
loop over the raw path: 6 leaves still differed; host-path hash `d2e5fb18…`), so it was superseded. Second pass: new module
`helm_test_pins.py` (`neutral()` strips the `brain_dir` and `receipt_hash` leaves to `<stripped:NAME>` and replaces any other
absolute path by `<path>/<last component>`; `canon()`, `canon_sha256()`, `offending()`); `test_helm_cas_address.py` hashes
through it, new pin `312ddfd687f73182be524acc64f0829d67d11c29ba9546915f344998927abf64`; new `test_helm_pin_hygiene.py`
(9 tests: every record pin goes through the canonicaliser; the canon carries no path, user, home, platform or interpreter
word; the hash is invariant to the session folder, the working directory AND a copy of the licensed brain under another
parent; the strip rule itself). Verified by the v6 builder on `ad4fde73`: the pin `312ddfd6…` in five brain-folder cases (the
host's path reported, the laptop default path reported, the deps folder, a copy under another parent, the laptop default
folder), 0 differing leaves after `neutral()` between the laptop and host paths; `helm_brain_canonical.py` = base
`24df53c9…`; `helm_wide_turn.py` byte-identical to the round-3 fix `f45a8570`; `helm_end_to_end_loop.py` unchanged. Suites on
the laptop: brain_wide 54, cas_address 17, end_to_end_loop 18, english_in 37, english_in_stock_frame 17, faces_in 16,
pin_hygiene 9, triad 15, units_note 15, voice 22, wide_alongside 25 (= 245), all OK; pytest-style agentic_planner 8,
chat_nuance 8, memory 4 passed; the host's 11-name command form on a scratch copy `Ran 245, OK (skipped=1)`.

**What changed in this package (v6). Exactly these, nothing else.**

1. **`helm_now/` recut at `%(fix)s`** by the contract's rule (wave 6 v3's 159 files + every
   `helm_*.py` / `test_helm_*.py` at the commit + `helm_test_pins.py` named explicitly, since only tests import it; each by
   `git show`, never the working tree): **166 files** (v5: 164; + `helm_test_pins.py`, `test_helm_pin_hygiene.py`;
   `test_helm_cas_address.py` changed; every other file equal to v5's cut). `contract/HELM_CUT_R1W7.json` carries the commit
   and all 166 hashes; `helm_brain_canonical.py` = base `d4488f2a` `24df53c9…`.
2. **The host's HELM self-check list** (`kit/run_r1w7.py` `HELM_TESTS`): the 10 names of v5 + `test_helm_pin_hygiene` =
   **11 names**, one process, the same command form as c53. The three pytest-style files stay carried but not run as
   unittest suites.
3. **Exclusions:** `contract/EXCLUDE_R1W7_PRIOR_USED.json` gains block `X7v5_c53` = lists `X7v5_c53_real` (X7v5's 128 REAL
   ids) and `X7v5_c53_conv` (64 CONV pool ids), read by program from the custodian's seal record
   `x7v5_custody/X7_SEALED_20261021T060622Z.json` (keys `real_drawn_frame_ids_sorted` / `conv_pool_ids_sorted`; ids only; no
   input, key or exam file opened). Every list applies to BOTH pools (A-R1W7-4 rule kept): 20 lists.
4. **Seed bands** (section 10 superseded again): REAL 2,012,000,001-2,013,000,000; CONV 2,014,000,001-2,015,000,000; NOISE
   2,016,000,001-2,017,000,000 (each 1,000,000 wide; below INT32_MAX 2,147,483,647). Used table 1-2,011,000,000 as one range
   (everything up to wave 7 v5 / c53's 2,006-2,011 M, spent by the X7v5 draw; the continuity packet's reserved 1,996-1,999 M
   inside it); gap 1,000,000; slot stepping and STOP as before.
5. **The owner's line** (section 8 superseded again): **`CHAT WAVE 4 at 1 USD`** (20 UTF-8 bytes; `CHAT WAVE at 1 USD`
   was consumed by c51's approval record, `CHAT WAVE 2 at 1 USD` by c52's, `CHAT WAVE 3 at 1 USD` by c53's; none may bind
   a second zip). Seed text `H = sha256(UTF-8("CHAT WAVE 4 at 1 USD" + ":" + <v6 zip sha256, 64 lower-case hex>))`, no
   trailing newline. Cap 1.00 USD; one attempt + one plumbing retry; expected about 0.01-0.02 USD.
6. **New rule, the host-exact suite list from the seal:** the seal step runs EXACTLY the host's suite list (`HELM_TESTS` of
   the sealed `kit/run_r1w7.py`, the file the stage plan `kit/STAGE_R1W7.json` runs) with the host's command form
   (`python -X utf8 -B -I -c <HELM_LOADER> <scratch copy of helm_now/> <the names>`, from inside the scratch copy,
   `HELM_SESSION_DIR` inside the scratch, `HELM_CANONICAL_BRAIN_DIR` = the wave-1 package folder) from a FRESH extract of the
   sealed zip, and records the list, the command and the `Ran` / `OK` line in `TEST_COUNTS_R1W7_v6.json` under
   `host_exact_suite_list`. The seal tool computes the list twice (the sealed kit's `HELM_TESTS`; its own typed copy of the
   eleven names) and refuses unless they are equal and the stage plan's `argv[0]` is `kit/run_r1w7.py`. The v5 seal record
   ran an 8-file scratch list (Ran 204) while the host ran 10 files (Ran 236); that gap is closed. README and
   `TEST_RECORD_R1W7.md` carry the rule.
7. Labels: `PACKAGE_VERSION` = `v6`; `RUN_LIMITS_R1W7.json` `package_version` and the line in `cost_cap_status`; the
   stage note; README (the stale "eight unittest files" wording replaced); the custodian procedure; FROZEN re-derived from
   the constants (the kit test checks they agree); the tests that pin the bands, the line, the blocked table, the cut size
   and the exclusion lists.

**Unchanged (checked by the tests and the freeze):** the v4 reader (`r1w7.merge_r1w7 v2`), the v4 recorder unit and fixture,
every mark, threshold, arm, status word, exam size, instrument row and hard gate; the noise sentences; the five neighbours by
freeze; the practice pools; the scoring functions; the units and their commands; the wide reader's round-3 rule.

**What this amendment does not do.** It does not re-read c53. It does not launch. It does not draw an exam. It licenses
nothing. Forecast: on the host HELM's suite reads `Ran 245, OK (skipped=1)` (the pin is invariant to the brain folder), so I6
reads true; every other row as c53. A fresh draw can still miss a mark on a shape no practice run has shown.
