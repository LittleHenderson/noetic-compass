# Q4-SDG-1 A-versus-B builder report (2026-09-24)

**Builder:** a Claude sub-agent, working only in `D:/tksCAS-worktrees/q4-sdg` on branch `claude/q4-sdg-feedback-20260923`.
**Label:** `CLAUDE_BUILT_CLAUDE_CHECKED` (temporary takeover while Codex is away). A Claude check of Claude work is
not an independent review.
**Status:** built and tested on the laptop in pure Python. **Nothing was launched. No AWS call was made. No money was
spent. No model was built or trained.** The spec is `PROPOSED_FOR_REVIEW`, not frozen.

**Superseded in part (2026-09-24):** this report describes revision 1 (commit `3771f989`). Two reviews found one MAJOR
and eight MINOR defects; revision 2 fixes them and freezes the spec. See `Q4_AB_REVIEW_20260924.md`. The file hashes,
the rules hash and decision 4 below are those of revision 1.
**Superseded again (2026-09-24):** a verification of revision 2 returned CHANGES_REQUIRED. The spec's revision 3 applies
the coordinator's decisions and is `PROPOSED_FOR_REVIEW`. See the section "Revision 2 of this report" at the end.

Paths are relative to `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/`. `LAB` =
`research/helm_cas_expression_lab/`.

## In plain words

- The owner decided the next step: compare A (the old family-G teaching) with B (the new CAS SDG lessons) on the
  same Q4 model, 3 seeds each, and let a rule written in advance say whether a new design is justified.
- I built everything that comparison needs, in new files only:
  - the written rules (spec) and the same rules as a small program;
  - the training program for the AWS T4 machine;
  - the program that reads the results and prints the verdict labels;
  - a small AWS job that builds the B lessons and proves they rebuild byte for byte, and a tool to pin them;
  - the AWS training job;
  - 31 tests that run without torch.
- The shared test sets (panels) are fixed now, before any training, and their fingerprints (sha256 digests) are
  written into the rules. The AWS machine must reproduce every fingerprint before it trains.

## Files (all new; sha256 of the committed bytes, LF)

| File | sha256 | What it is |
|---|---|---|
| `LAB/Q4_SDG_AB_SPEC_v0_2.md` | `0a8b03d0158e03b4e273ed370339ed414906571188e67a7b035b595a52e81152` | the spec (M1, M2, A1), `PROPOSED_FOR_REVIEW` |
| `LAB/q4_ab_rules.py` | `bdd060206897acf5a8ca14f8275a9662cf9e9546fc2b7c662523a35e3b92cf1f` | every frozen value, the exact tests; standard library only |
| `LAB/q4_ab_prep.py` | `e35e256ee279ce0154549934434c22d1c9660fc6d227c8c64fe89cd6c224aa35` | torch-free panels, pools, edits, B-package checks, `measure`, `package-digests` |
| `LAB/q4_ab_train.py` | `7a9b07ccc4ac7b24e65a672495a3e91701b6d60d0ec84ad5adf3f25501f1fe2d` | the Linux T4 runner (torch only inside functions) |
| `LAB/read_q4_ab_results.py` | `48adf81de8e30187eaba4eb964f134a309ae4b9fd115693968d49bfb2554f627` | the verdict reader; standard library only |
| `LAB/test_q4_ab.py` | `0b9a15d6fb5445512996cd70f9b29f213ad2ae964d0c4f7918dfdc5bf2de2e75` | 31 torch-free tests |
| `records/q4_sdg_1_20260923/data_build_job/launch.py` | `93609c5b6e7d8cee2d5d53c24053c9408e88f585e79d2142579cc5bb6306f704` | CPU data-build launcher |
| `records/q4_sdg_1_20260923/data_build_job/job.sh.template` | `65fd1d7de5473f0d3db59e4bf0bba042f8143be060115ebdcf53b7dbdcb90a63` | data-build machine script |
| `records/q4_sdg_1_20260923/data_build_job/watch.py` | `a73a75544e407228415e77e859db4384e3a5ad12d2d504df63536b0da4f81bad` | data-build watcher (flat, safe) |
| `records/q4_sdg_1_20260923/data_build_job/pin_package.py` | `67d3828fdaf0f77e0a2e8862f039418065b649a23e90644cb513fd36a39daeae` | the coordinator's pin tool |
| `records/q4_sdg_1_20260923/data_build_job/JOB_LIMITS.md` | `a2ecb602dc38ed40d23abfd4483d5e02600437d3b414b5cdf99c88719c8cab9d` | limits, ceiling arithmetic |
| `records/q4_sdg_1_20260923/ab_job/launch.py` | `d2c0900e1a68debc9f499db4a55256879d56dd78e01a0e4ba3dc043aa40b7850` | T4 training launcher |
| `records/q4_sdg_1_20260923/ab_job/job.sh.template` | `e85cdcd65d15c39a7b143c957a6fdb6579434eaf56c20b32450f3e98d3f36a2b` | training machine script |
| `records/q4_sdg_1_20260923/ab_job/watch.py` | `142ebc79e00fbb01c4c67f43e64db9763825d9a9fdccd4d4b4840043e920a830` | training watcher (nested folders, safe) |
| `records/q4_sdg_1_20260923/ab_job/JOB_LIMITS.md` | `2083441cf89edfca69270a5125e4423ba852a5c9e2093e12595bf7bda22365d1` | limits, runtime and cost estimate |
| this report | (not listed in itself) | |

**Frozen-rules hash** (`q4_ab_rules.frozen_sha256()`): `27b940019c54325d81db0bdc6366d21f03c178f90e439c68f802e3dc2ed0663e`.

**No existing file was changed.** Not touched: `q3_behaviour_records.py`, `q3_load.py`, `Q3_DATA_PINS.json`,
`data/q3_v0_7/`, the 12 pinned runtime files, `q4_panel_evaluation.py`, `q4_error_panel.py`, `q4_sdg_curriculum.py`,
`Q4_SDG_DATA_PINS.json`, `records/q4_authorized_20260922/`, the `error_panel_job/` files. No new file is named `learner*`.

## What the build decides, and where I had to choose (please review these)

1. **SP1 cannot be "16 rows per shape".** Measured: the 16 G-train shapes have very uneven row counts (747, 417, 204,
   190, 135, 128, 52, 52, 43, 20, 18, 15, 13, 8, 4, 2). I allocate the 256 reserved rows **in proportion** to each
   shape's rows that the diagnostic never showed (largest remainder; never more than half a shape). Result: 14
   shapes, `(L L)` 95 rows; two tiny shapes get 0. SP1 is therefore arm A's natural distribution.
2. **T1 tests the Noetic field only.** Domain, drive and register can be partly guessed without reading the input
   (TIMES forces one domain; "none" is about half of all drives and registers). The diagnosis shows it: noetic 36/453,
   but drive 227/453 and register 214/453. The other three fields are tested and reported, not decisive.
3. **T1's null rate is the larger of** the arm's teaching-pool rate (the task's wording) and the SP1 panel's own rate.
   Reason: a model that always writes one value scores that value's panel share; with the larger rate it can never
   pass. For arm A: 90/799. The exact threshold: **k >= 112 of 799 (14.0%)**.
4. **INPUT_USE_DETECTED = T1 and T2 and T3** (the task names all three). Consequence to confirm: a model that reads
   the input with the correct previous tokens, but whose free generation still collapses, counts as "no input use".
   Directive section 9 names "supply the same final summary at every decoding step" for exactly that failure, so I
   think the conjunction is right. It is the owner's call.
5. **Calibration guard (added).** If the rule fires on an untrained model (checkpoint 0), no architecture verdict is
   given (`ARCHITECTURE_DECISION_INCOMPLETE`).
6. **Budget: 32,768 updates per run**, checkpoints 0, 128, 512, 2048, 8192, 16384, 32768. It is 256 times run_001 and
   fits the money with a wide margin.
7. **The T4 machine rebuilds the B package** from the same source and must match the pin (manifest sha256, then
   `check_pin`, then the declared file hashes). Row files never travel through the laptop. The risk: if a third
   build differed across machines, the job would stop at `B_PACKAGE_MISMATCH` after about 15 minutes (about $0.14).
   The alternative is to fetch the archived package from S3 by its key.
8. **Evaluation decodes stop at 64 tokens.** Every panel target has at most 56 tokens, so exactness is unchanged. It
   bounds the time of an untrained model's long decodes.
9. **The spec is not frozen by me.** Its status line is `PROPOSED_FOR_REVIEW`. The launcher refuses unless the status
   line is exactly `**Status: FROZEN_BEFORE_LAUNCH**` at the source commit (the word appearing elsewhere does not count;
   a test checks this).

## What each test covers (`LAB/test_q4_ab.py`, 31 tests)

| Group | Tests | What they prove (torch-free) |
|---|---:|---|
| Frozen values | 5 | lr 0.001, clip 1.0, width 64, numerical policy equal run_001's plan (plan sha `9dacc836...`); the build and update calls appear in `q4_smoke_job.py`'s order in both programs; seeds are new and paired; every frozen panel digest reproduces from VISIBLE files with the pure-Python engine; any changed digest refuses (`PANEL_DIGEST_MISMATCH`) |
| Panels and exclusions | 5 | SP1 = 256 rows, proportional, none of the 48 inspected train rows, never in arm A's pool, arm A = 1,792 rows in file order; SP2 flags exactly the 48 inspected dev rows; every EDIT64 edit changes exactly one token of its field; panel content is dropped from B's teaching (a real tiny B package built in the test); near-twin distances and class counts |
| Order | 1 | epoch 0 of the stream equals `random.Random(seed).shuffle(range(n))` (q4_smoke_job); every epoch is a permutation |
| Package and pin | 5 | the real pin file is either empty or the frozen package; a pin with another engine, seed, file list or digest is refused; a rebuilt package must equal the pin; `package-digests` finds a one-byte change; `pin_package.py` refuses non-identical or unverified builds, a tampered manifest, and never overwrites a different pin (`PIN_CONFLICT`) |
| Reader | 9 | results made by the RUNNER'S OWN `evaluate()` with two pure-Python fake models (NOT Q4: one reads its input perfectly, one ignores it) pass the reader's recomputation; the rule separates them (blind: T1 88/799, 1 distinct output); B reads / A does not gives `ARCHITECTURE_CHANGE_NOT_JUSTIFIED` and `LESSONS_HELP_*`; nobody reads gives `JUSTIFIED`; 2 of 3 seeds is enough, 1 is not, a missing run gives `UNDETERMINED`; 7 wins pass and 6 do not (p = 1/64); inspected dev rows count only in SP2ALL; Stage-0 failure, changed rules, reload mismatch, inconsistent totals, unequal starting tensors, a rule firing at initialisation, a stopped job and an empty folder each give their declared label; eval/sealed names are refused; every emitted label matches the declared list |
| Statistics | 2 | exact binomial tail equals brute force; sign test 7-0 = 1/128 passes, 6-0 = 1/64 fails; T1 threshold 112 of 799; T2 boundary at 78 of 773 rises and at delta 0.009 |
| Jobs | 4 (skipped on the AWS machine, which has no job folders) | data build $0.0813 + training $2.1678 <= $5.00, measured-spend check; launcher custody filters (eval, sealed, hset1a/b, nested folders, the B package folder) and pre-launch refusals (no pin, wrong engine, not frozen); both templates fill under the 16 KB limit and refuse a missing placeholder; watchers write only safe nested files and refuse `..`, absolute paths, links, hidden names, eval/sealed/hset names, too-deep and oversized members |
| Fail-closed | 2 | `GPU_REQUIRED` for `cpu`, `cuda`, empty, None, `cuda:x`, before any torch import or file write; stop codes map exactly; no eval/sealed door and no `extractall` in the new modules; create-only outputs |

## What I checked on the laptop (pure Python; no torch model, no GPU, no AWS; each run under 2 minutes)

| Check | Result (measured) |
|---|---|
| `pytest test_q4_ab.py` | **31 passed** in 83.16 s |
| `pytest test_q4_sdg_curriculum.py test_q4_error_panel.py` (existing, unchanged) | **38 passed** in 18.52 s |
| `q4_ab_prep.py measure`, pure-Python engine | all 8 frozen values reproduce; 10.9 s |
| the same, with the local Rust engine | all 8 reproduce (engine parity of the panels) |
| Diagnostic selection digest | `0b98bfc9...` reproduced |
| SP1 | 256 rows, 5,337 target tokens, 799 noetic positions; digest `dab48792...` |
| SP2 | 256 rows, 208 not inspected; inspected-48 digest `d91d914b...` |
| EDIT64 | 64 rows, 773 edits (196 noetic, 185 domain, 196 drive, 196 register; 11 domain fields with no compilable edit); digest `05d62b99...` |
| Arm A pool | 1,792 rows, 37,905 target tokens, 63,545 source bytes; noetic most frequent 605/5,671; digest `9064635d...` |
| Near twins vs arm A | 6 of the 512 SP1/SP2 rows are one token from an arm-A row; 32 are two tokens away |
| Machine scripts | both fill to 11,003 and 10,490 bytes (limit 16,000) with 1,600-character links; `bash -n` syntax OK |
| New files | LF only, no control characters, all compile |

## What can only run on AWS

- Everything with torch: Stage 0 on the T4, the update-1 re-initialisation check, training, evaluation, the
  smoke determinism check, the fresh-process reload, the real time per update.
- The size-4096 B build, its run time, its refusal rates, its byte-identical rebuild, its engine label.
- The launchers' AWS calls and the watchers' S3/EC2 calls (never called here; their pure parts are tested).

## Runtime and cost estimate

- **Anchor (measured):** the diagnostic took 26.7 s on a T4 for about 14,200 decoder calls, so at most about 1.6 ms
  per decoder call. One training update is an **assumption** of about 5 ms until the smoke stage measures it.
- **Training machine:** typical about 61 min, **about $0.55**; upper about 142 min, **about $1.28**. The smoke
  projection stops the job before the main runs if it cannot finish in the runner's 190 minutes.
- **Data build:** about 10 minutes on a c7i.large, about $0.02.
- **Hard worst case:** $0.0813 + $2.1678 = **$2.2491 <= $5.00** (both launchers enforce it).

## Next steps (in order; none is done)

1. A fresh review of this commit.
2. The coordinator launches `data_build_job/launch.py`, then `watch.py`, then `pin_package.py --check` and `--write`,
   and commits the pin.
3. After review approval: change the spec's status line to the frozen one, commit.
4. `ab_job/launch.py --source-commit <that commit>`, then `watch.py`, then `read_q4_ab_results.py --results
   results/ab --out verdict.json` on the laptop.

## Open questions

1. **An existing test will fail after pinning.** `test_q4_sdg_curriculum.py::test_pinning_is_required_and_create_only`
   expects `NO_PIN_FOR_THIS_DATA_VERSION` from the REAL pin file. After the real pin exists it gets
   `MANIFEST_NOT_THE_PINNED_ONE`. The fix is one line in that test (point `sdg.PINS` at an empty temporary copy first).
   That file is outside my new-files-only scope. Who edits it: the coordinator with the pin commit, or Codex?
2. **T3 inside the conjunction** (decision 4 above): confirm.
3. **SP1 in the natural distribution** (decision 1), with two tiny shapes absent: confirm.
4. **B rebuilt on the T4 machine versus fetched from S3** (decision 7): confirm.
5. **The c7i.large price** ($0.0893 per hour) is from my knowledge, not re-read from AWS (I made no AWS call). The
   ceiling margin is wide, but the coordinator may want to confirm it.
6. **Who flips the spec's status line** after review, and at which commit.
7. B's exact pool size and mean target length are known only after the build (reported in `prep.json`).

## EXPOSURE (everything outside my working copy that I opened or used)

- **Git object store and remote:**
  - `git fetch origin research/helm-integration-20260923`, then `git show FETCH_HEAD:` of exactly two files:
    `Q4_SDG_AND_TARGETED_FEEDBACK_DIRECTIVE_20260923.md` and `OWNER_AUTHORITY_AND_DECISIONS_20260924.md` (FETCH_HEAD
    `9656dc19`).
  - `git fetch origin claude/q4-sdg-feedback-20260923` to check the remote tip before committing (it equalled HEAD).
  - `git grep` over the whole tree at HEAD for candidate seed values, with pathspecs excluding `*sealed*`,
    `*_eval.jsonl`, `*hset1a*` and `*hset1b*` (case-insensitive). It searched committed `.py`, `.md` and `.json` files,
    including folders outside the sparse checkout (for example `records/typed_matched_001/`, `records/typed_pointer_001/`).
    Only matched fragments were printed: floating-point numbers, no seed.
- **My session scratchpad** (`C:/Users/wakil/AppData/Local/Temp/claude/C--Users-wakil-OneDrive-Desktop-tksCAS-cas-only-reasoner/5e8709f4-3151-444f-939b-317c01bc3568/scratchpad/`):
  - a debug script `dbg_fake.py` I wrote;
  - pytest temporary folders `pytest_q4ab/` and `pytest_existing/`. The tests built tiny B packages there, and the
    tests read those packages' own `sealed_*` sidecars (generated there by the tests themselves);
  - two filled machine scripts for the syntax check;
  - all of the above deleted after the checks. One `ls` of the scratchpad also showed the NAMES of other sessions'
    files there; I opened none of them.
- **Python and tools:** `C:/Python314/python.exe` and its standard library; pytest from
  `C:/Users/wakil/AppData/Roaming/Python/Python314/site-packages/`. The pinned compiler imported the optional Rust
  `cas_engine` from that folder (one measure run used it on purpose; the tests switch it off). Git Bash tools
  (`sha256sum`, `timeout`, `bash -n`).
- **Two import checks I should not have made:** at the start I ran `python -c "import torch"` and
  `python -c "import boto3"` once each, only to see whether they were installed. Both loaded. No model, tensor, GPU
  context or AWS client was created. After that, no torch or boto3 import happened (the tests assert torch is absent).
- **Harness side effect:** one long tool output was saved automatically by the tool harness under
  `C:/Users/wakil/.claude/projects/.../tool-results/`. I did not open it.
- **Inside the working copy, for the record:** the error-panel results (`records/q4_sdg_1_20260923/error_panel_job/results/panel/*.json`,
  `RUN_LOG.md`, `JOB_LIMITS.md`, `launch.py`, `job.sh.template`, `watch.py`); run_001's records (its weights file was
  hashed, not loaded); visible Q3 v0.7 files only through `q3_load.load_visible`.
- **Not touched:** any `*_eval.jsonl`, any Q3 `sealed*` file, `D:/tksCAS-archive/`, any hset1a/hset1b path, S3 or any
  AWS service, the meta1 budget ledger, other worktrees, Claude transcripts.

## Revision 2 of this report (2026-09-24): spec v0.2 revision 3, the coordinator's decisions

**Label:** `CLAUDE_BUILT_CLAUDE_CHECKED`. The builder is a Claude sub-agent (temporary builder). A Claude check of
Claude work is not an independent review.
**Status:** built and tested on the laptop in pure Python. **Nothing was launched. No AWS call. No money spent. No
model built or trained. No torch import.** The spec is back to **`PROPOSED_FOR_REVIEW`** (revision 3).

A note on numbers. This is the second revision of THIS REPORT. It describes the SPEC's revision 3. (The spec's
revision 2 is described in `Q4_AB_REVIEW_20260924.md`.)

### In plain words

- The verifier of revision 2 (commit `fbcc279b`) found that a model which reads only the SHAPE of the tree (and maybe
  its operators) was still called "no input use". Six such runs would have said "an architecture change is justified".
  That was wrong: such a model's answers change with its input.
- The coordinator decided five rules on 2026-09-24. I applied them exactly. The spec quotes them word for word
  (section 15).
- Now "no input use" (NONE) means total collapse only: every test fails AND the model gives the same one answer for
  all 256 test rows.
- A new level, STRUCTURE_OR_OUTPUT_VARIATION, catches a model that reads no field value but whose answers still vary,
  or that reads drive/register presence. It blocks "justified".
- A run that is not valid (for example, its reload check failed) now also counts against "justified", if its final
  reading is anything other than NONE.
- A new information-only label, FIELDS_NOT_READ_IN_ANY_RUN, says when no run read any field value. It decides nothing.
- The safety check on the untrained model (the calibration guard) is unchanged: it uses T1, T2V and T2P only. The
  number of different answers each untrained run gives is now reported for every run.
- I did NOT change the approved hashes in the launcher, as instructed. So the launcher refuses this revision until a
  review approves it. I checked that it does.

### The coordinator's decisions and where each landed

| Decision (2026-09-24) | Code | Spec |
|---|---|---|
| 1. NONE = T1, T2V, T2P all fail AND exactly 1 distinct free output over the 256 SP1 rows | `q4_ab_rules.NONE_DISTINCT_FREE_OUTPUTS = 1`; `input_use_level(t1, t2v, t2p, distinct)` now takes the count D itself, so T3 and D cannot disagree | 7.1, 7.2 |
| 2. STRUCTURE_OR_OUTPUT_VARIATION (D >= 2, or T2P, while T1 and T2V fail); blocks JUSTIFIED; FULL unchanged | `LEVELS`, `FIELD_LEVELS`, `ARCHITECTURE_REASONS` | 7.2 |
| 3. JUSTIFIED only if every run with a FINAL reading (valid or invalid) is NONE, in at least 2 of 3 seeds per arm, and the guard is clean | `arm_label` and `architecture_decision` take (level, valid) of every run with a FINAL reading; new reason `NOT_NONE_IN_A_RUN_THAT_IS_NOT_VALID`; `read_q4_ab_results.final_readings` | 7.3, 7.5, 7.7 |
| 4. Information-only FIELDS_NOT_READ_IN_ANY_RUN | `fields_not_read_in_any_run`; `INFORMATION_LABELS`; the reader's `information` block and label list | 7.8, 9, 12 |
| 5. Guard stays on T1, T2V, T2P; report checkpoint-0 distinct counts for every run | `calibration_guard_fires`; the verdict's `calibration_guard_tests`, `calibration_checkpoint_0`, `checkpoint_0_distinct_free_outputs` | 7.4 |

### Choices I made in applying them (disclosed; please review)

1. **One new level, which replaces STRUCTURE_ONLY.** Decision 2 says "levels" but names one. Its definition contains
   every revision-2 STRUCTURE_ONLY case (T2P passes, T1 and T2V fail). Keeping both would split the named level. The
   reading still shows which part fired (T2P, and D with `output_varies`).
2. **"At least 2 of its arm's 3 seeds" counts VALID NONE runs.** Decision 3 says JUSTIFIED "can only become rarer".
   Counting an invalid NONE run toward the 2 would let JUSTIFIED fire where revision 2 said TOO_FEW_VALID_RUNS. A test
   enumerates 3,375 arms. It checks that every arm that "shows no input use" under revision 3 also did under
   revision 2.
3. **The reasons also read invalid runs.** An invalid FULL run gives `SEED_DEPENDENT` and
   `NOT_NONE_IN_A_RUN_THAT_IS_NOT_VALID`.
4. **FIELDS_NOT_READ_IN_ANY_RUN needs at least one FINAL reading.** With none, the label would mean nothing. A field
   reading in ANY run with a FINAL reading, valid or not, suppresses it.
5. **When the guard fires, it is still the only reason given** (as in revision 2).
6. **The launcher test now has two states** (`test_launcher_approves_exactly_the_committed_rules_programs_and_spec`).
   Under review (the spec says PROPOSED_FOR_REVIEW): the launcher must refuse this working copy before the pin check.
   Approved (the spec has the frozen status line): the launcher's values must equal the working copy, as before. The
   old test would now fail by design, because the approved hashes are revision 2's and must not change yet.

### Measured on fakes (pure Python, the runner's own `evaluate()`; each value is asserted by a passing test)

| Fake model (NOT Q4) | T1 (of 799) | T2V (538) | T2P (235) | D (of 256) | Level, revision 2 | Level, revision 3 |
|---|---:|---|---|---:|---|---|
| blind | 88 | fails | fails | 1 | NONE | NONE |
| reader | 799 | 538 up, 0 down | 235 up | 256 | FULL | FULL |
| tf_reader_freegen_collapse | 799 | passes | - | 1 | TEACHER_FORCED_ONLY | TEACHER_FORCED_ONLY |
| no_noetic | 88 | 342 up | - | passes T3 | PARTIAL_FIELDS | PARTIAL_FIELDS |
| structure_only | 88 | 0 up | 235 up, 0 down | 180 | STRUCTURE_ONLY | STRUCTURE_OR_OUTPUT_VARIATION |
| shape_operators_only (the verifier's V1 fake, now a lab test) | 88 | 0 up, 0 down | 0 up, 0 down | 44 | NONE | STRUCTURE_OR_OUTPUT_VARIATION |
| shape_only (the verifier's V2 fake, now a lab test) | 88 | 0 up, 0 down | 0 up, 0 down | 14 | NONE | STRUCTURE_OR_OUTPUT_VARIATION |

The V1 and V2 numbers (88; 0 and 0; 0 and 0; 44 and 14) equal the verifier's own scratch measurements.

| Results folder (all through the reader) | Architecture label [reasons] | FIELDS_NOT_READ_IN_ANY_RUN |
|---|---|---|
| 6 blind runs | JUSTIFIED | yes |
| 6 blind runs, one invalid (reload) | JUSTIFIED (2 valid NONE runs per arm; the invalid run's reading is NONE) | (not asserted) |
| 6 blind runs, arm A: one invalid, one missing | INCOMPLETE [TOO_FEW_VALID_RUNS] | (not asserted) |
| 6 shape_operators_only runs (V1) | INCOMPLETE [STRUCTURE_OR_OUTPUT_VARIATION] | yes |
| 6 shape_only runs (V2) | INCOMPLETE [STRUCTURE_OR_OUTPUT_VARIATION] | yes |
| 6 structure_only runs | INCOMPLETE [STRUCTURE_OR_OUTPUT_VARIATION] | yes |
| 6 tf_reader_freegen_collapse runs | INCOMPLETE [TEACHER_FORCED_ONLY] | no |
| 6 no_noetic runs | INCOMPLETE [PARTIAL_FIELDS] | no |
| B seed 20260933 reads fully, but its reload fails; 5 blind runs (V3) | INCOMPLETE [SEED_DEPENDENT, NOT_NONE_IN_A_RUN_THAT_IS_NOT_VALID] | no |
| A seed 20260931 is shape_only and invalid; 5 blind runs | INCOMPLETE [STRUCTURE_OR_OUTPUT_VARIATION, NOT_NONE_IN_A_RUN_THAT_IS_NOT_VALID] | yes |
| checkpoint 0 = shape_operators_only in all runs (D = 44 each); FINAL blind | guard SILENT; JUSTIFIED; every run's checkpoint-0 D reported as 44 | (not asserted) |
| checkpoint 0 = structure_only in all runs (T2P passes) | guard FIRES; INCOMPLETE [INPUT_USE_RULE_FIRES_AT_INITIALISATION] | (not asserted) |

### Checks run (pure Python on the laptop; one at a time; no torch, no GPU, no AWS)

| Check | Result (measured) |
|---|---|
| `py_compile` of the three changed Python files | OK |
| Fast rule tests only (partition, enumeration, guard, statistics) | **4 passed** in 1.07 s |
| `pytest test_q4_ab.py` (whole file, once) | **41 passed** in 172.36 s (38 before; 3 new tests) |
| `pytest test_q4_sdg_curriculum.py test_q4_error_panel.py` (unchanged files, once) | **38 passed** in 30.97 s |
| The two launcher tests again, after the last spec text edit | **2 passed** in 0.86 s |
| The launcher's own `check_frozen` on this working copy | refuses: `LAUNCH_REFUSED: FROZEN_RULES_NOT_THE_APPROVED_ONES (dc7d014c7889 at this commit, approved 3100f37603cb)` |
| Changed files | LF only, no control characters |

Free memory before the long test run: 640 MB (measured; the laptop has about 16 GB). The run took longer than earlier
runs (172 s, against about 65 s). It finished.

### Identity of revision 3 (NOT approved; the launcher still approves revision 2)

- `q4_ab_rules.frozen_sha256()`: `dc7d014c788980ef851faf2d245bd1006916eccbc380b9d2e0c31e78f0d65eac`
  (revision 2 was `3100f376...`).
- LF sha256 of the five files the launcher pins, as committed here:
  - `LAB/q4_ab_rules.py` `c106d899cdbd8ff5fd88f9a1af29748a66120bb45699f5588efecbde93e10dea` (changed)
  - `LAB/q4_ab_prep.py` `b0601e5382df15441526bf334fb8c548ee6a379d4b633a81adb60e40fca8fd23` (unchanged)
  - `LAB/q4_ab_train.py` `4d793a6afed5ddf6e399fcbcfff2bb1799a28ee725ab98cf4d59578e1bce8cd4` (unchanged)
  - `LAB/read_q4_ab_results.py` `d4e0f1ee3648a3e33bb5d95e26bc84a3396aeee33b275e9ff8b2831107491a50` (changed)
  - `LAB/Q4_SDG_AB_SPEC_v0_2.md` `f5385327bf87f134c2ecd4b7a934267a659100a7708c7c2c7151120fdd73f739` (changed; this
    hash changes again when the status line is set to frozen after review)
- `LAB/test_q4_ab.py` `7cbbcf834cef8e796522b334ba2fafbf336a80b44de72ccbf6cf99a3bb7d4a89`.

### Files changed in this revision

- `LAB/q4_ab_rules.py`, `LAB/read_q4_ab_results.py`, `LAB/test_q4_ab.py`, `LAB/Q4_SDG_AB_SPEC_v0_2.md`, and this report.
- NOT changed: `records/q4_sdg_1_20260923/ab_job/launch.py` (its approved hashes stay revision 2's, as instructed),
  `q4_ab_prep.py`, `q4_ab_train.py`, the job scripts and job limits, `q4_sdg_curriculum.py`, `Q4_SDG_DATA_PINS.json`,
  every Q3 file and pin, `records/q4_authorized_20260922/`.

### Next steps (in order; none is done)

1. A fresh review of revision 3 (this commit). It should check the six disclosed choices above.
2. After approval: set the spec's status line to the frozen form with the rules hash. Then write the new
   `APPROVED_FROZEN_SHA256` and `APPROVED_LF_SHA256` into `ab_job/launch.py`, in a commit of their own.
3. The data build, the pin and the training launch, as before.

### Open questions (for the coordinator and the owner)

1. Folding STRUCTURE_ONLY into STRUCTURE_OR_OUTPUT_VARIATION (choice 1): confirm, or name the second level that
   decision 2 meant.
2. Counting only VALID NONE runs toward "2 of 3 seeds" (choice 2): confirm.
3. Output variation may often be present. An untrained or lightly trained GRU may already give D >= 2. Under decision
   1 such a run blocks JUSTIFIED. The verdict now reports each run's checkpoint-0 D, so it can be set next to its
   FINAL D. The rule itself does not compare them. This follows the decisions, and it makes JUSTIFIED rare.
4. Still open from earlier: a teaching-fit floor (the owner's choice); MIXED as the overall lessons answer; the
   c7i.large price not re-read from AWS; B's exact pool size known only after the data build.

### EXPOSURE (everything outside my working copy that I opened or used)

- **Git:** `git fetch origin claude/q4-sdg-feedback-20260923` and `git pull --ff-only` (already up to date at
  `fbcc279b`); `git show --stat` of the last three commits; `git diff` of my own changes; `git status`.
- **The verifier's scratch file** in this session's scratchpad:
  `C:/Users/wakil/AppData/Local/Temp/claude/C--Users-wakil-OneDrive-Desktop-tksCAS-cas-only-reasoner/5e8709f4-3151-444f-939b-317c01bc3568/scratchpad/verify_294471a5/test_verify_shape_readers.py`
  (read once, to copy its two fakes exactly). One `ls` of that folder showed the names of its pytest folders
  (`pt_ab`, `pt_cur`, `pt_shape`, `pt_shape2`). I opened none of them.
- **My own scratch folder** `.../scratchpad/rev3/`: pytest temporary folders `pt_fast`, `pt_ab`, `pt_cur`,
  `pt_launch`. In them the tests built tiny B packages, and the package code wrote and may have read its own generated
  `sealed_*` sidecars there. I opened none of them myself. I deleted the pytest folders before committing.
- **Launcher module:** loaded once in a Python process to print its `check_frozen` refusal on this working copy. No
  AWS client was created; `launch.py` imports nothing from AWS at load time.
- **Memory queries:** three PowerShell reads of free physical memory (a number only).
- **Python and tools:** `C:/Python314/python.exe` (3.14.0) and its standard library; pytest 9.0.2 from
  `C:/Users/wakil/AppData/Roaming/Python/Python314/site-packages/`. The pinned compiler's optional Rust `cas_engine`
  may load with the compiler; the lab fixture switches it off for every measurement. Git Bash (`timeout`, `grep`,
  `tail`, `od`, `file`, `wc`).
- **Context the harness gave me, not opened by me:** the user's `CLAUDE.md` files and memory index.
- **Inside the working copy, read:** `Q4_AB_REVIEW_20260924.md`, this report, `q4_ab_rules.py`,
  `read_q4_ab_results.py`, `test_q4_ab.py`, `Q4_SDG_AB_SPEC_v0_2.md`, parts of `ab_job/launch.py`, and the decoder's
  token list (`learner_q4_decoder.TOKENS`). The tests read visible Q3 v0.7 files and run_001's records through the
  lab's own fixtures.
- **Not touched:** any `*_eval.jsonl`, any Q3 `sealed*` file, `D:/tksCAS-archive/`, any hset1a/hset1b path, S3 or any
  AWS service, the meta1 budget ledger, other worktrees, Claude transcripts, and the owner's documents on the research
  branch (not re-read for this revision).

## Revision 3a (2026-09-24): W1 fixed, and the coordinator's confirmations recorded

**Label:** `CLAUDE_BUILT_CLAUDE_CHECKED`. The builder is a Claude sub-agent (temporary builder). A Claude check of
Claude work is not an independent review.
**Status:** built and tested on the laptop in pure Python. **Nothing was launched. No AWS call. No money spent. No
model built or trained. No torch import.** The spec stays **`PROPOSED_FOR_REVIEW`** (now revision 3a).
**Scope:** W1 of the verification of revision 3 (commit `502a5704`, `Q4_AB_REVIEW_20260924.md`), and the four
coordinator confirmations of 2026-09-24.

### In plain words

- The verifier found one small gap (W1). Sometimes a run writes its final results file, but the reader cannot read it.
  Examples: one number in the file disagrees with the reader's own count, or the run's manifest file is missing.
- Before this fix, the reader just skipped such a run. So if the other five runs showed no input use, the program
  could still say "an architecture change is justified". The skipped run might have read its input fully.
- Now the reader notes every run whose final file EXISTS but gave no reading. If there is even one such run, the
  program does not say "justified". It says "incomplete", with a new named reason:
  `FINAL_CHECKPOINT_PRESENT_WITHOUT_READING`.
- This can only make "justified" rarer. "Not justified" does not change. The safety check on the untrained model (the
  guard) does not change. A test checks this over every combination the old tests used.
- A run whose final file does NOT exist is still left out, as before. The coordinator's words cover a file that
  exists.
- The coordinator's four confirmations are now in the spec, word for word (section 16).
- I did not touch the approved hashes in the launcher. So the launcher still refuses this revision. A test checks it.

### What changed

| Where | Change |
|---|---|
| `LAB/read_q4_ab_results.py`, `read_run` | For every run: `final_checkpoint_file_present` (the path is checked, so a file holding JSON `null` counts) and `final_checkpoint_present_without_reading` (the file exists and gave no FINAL reading). The early return for a missing manifest sets it too |
| `LAB/read_q4_ab_results.py`, new `final_checkpoints_without_reading` | Lists those runs in run order. The verdict reports them overall, per arm, and in the `information` block |
| `LAB/q4_ab_rules.py`, `architecture_decision` | New REQUIRED third argument: the number of such runs (anything but a non-negative int is refused). Any such run withholds JUSTIFIED; the new reason is added last to every other INCOMPLETE. The guard branch and the NOT_JUSTIFIED branch are unchanged |
| `LAB/q4_ab_rules.py`, frozen record | `ARCHITECTURE_REASONS` gains `FINAL_CHECKPOINT_PRESENT_WITHOUT_READING`; the JUSTIFIED text, the ARM text and the FIELDS_NOT_READ_IN_ANY_RUN text state the new condition and scope; `SPEC_REVISION` says revision 3a. So `frozen_sha256` changes |
| `LAB/Q4_SDG_AB_SPEC_v0_2.md` | Title and status line say revision 3a; status block; 7.3, 7.5 (new reason and why), 7.7, 7.8 (scope), 9 (label list); section 15 marks choices 1, 2, 4, 5 as confirmed; new section 16 with the confirmations |
| `LAB/test_q4_ab.py` | One new reader test; the enumeration test extended; two assertions of revision 3 changed (below) |

### The verifier's cases, and more, through the real reader

The other five runs are input-blind in each row. The "revision 3" column for the first three rows is the verifier's
measurement (`Q4_AB_REVIEW_20260924.md`); I did not re-run revision 3. Every revision-3a cell is asserted by a passing
test.

| B seed 20260933's FINAL file | Revision 3 | Revision 3a |
|---|---|---|
| reads fully; one SP1 exact flag flipped | JUSTIFIED | INCOMPLETE [FINAL_CHECKPOINT_PRESENT_WITHOUT_READING] |
| reads fully; one TEACH_FIT exact flag flipped | JUSTIFIED | the same |
| reads fully; its `run_manifest.json` is missing | JUSTIFIED | the same (run is RUN_INCOMPLETE) |
| reads fully; the file names another rules hash | not measured | the same |
| holds JSON `null` | not measured | the same (run is RUN_INCOMPLETE) |
| input-blind; one SP1 exact flag flipped | not measured | the same (what an unread file held is unknown) |
| absent (deleted) | not measured | JUSTIFIED, unchanged: nothing is flagged; B still has 2 valid NONE runs |

| Other cases | Revision 3a |
|---|---|
| A reads fully in 2 valid seeds; B 20260933's FINAL file unread | NOT_JUSTIFIED_BY_INPUT_USE_RULE, no reason (unchanged) |
| guard fires; B 20260933's FINAL file unread | INCOMPLETE [INPUT_USE_RULE_FIRES_AT_INITIALISATION] only (confirmation (d)) |
| A 20260931 shape_only; A 20260932 and B 20260933 FINAL files unread | INCOMPLETE [STRUCTURE_OR_OUTPUT_VARIATION, FINAL_CHECKPOINT_PRESENT_WITHOUT_READING]; both runs listed, in run order |
| A 20260931's FINAL file holds invalid JSON, duplicate keys, NaN, or a list | the reader stops with an error, no verdict (unchanged) |

In the first six rows the arm labels still say `ARM_A_SHOWS_NO_INPUT_USE` and `ARM_B_SHOWS_NO_INPUT_USE` (choice 1
below), and `FIELDS_NOT_READ_IN_ANY_RUN` is still emitted over the 5 runs with a reading (confirmation (c); its scope is
now stated, choice 2).

**Two assertions of revision 3 changed on purpose.** `test_reader_recomputes_what_prep_claims` drops or swaps one
edit value in B 20260931's FINAL file. Revision 3's test asserted JUSTIFIED there. That is W1 itself. Revision 3a
asserts INCOMPLETE [FINAL_CHECKPOINT_PRESENT_WITHOUT_READING] and that B 20260931 is the one listed run.

**Enumeration** (`test_architecture_rule_can_only_become_rarer_and_always_names_a_reason`): all 81,796 pairs of the
286 distinct arms, each with 0, 1, 2 and 6 unread FINAL files. With 0, no pair has the new reason (asserted), and the
code path is revision 3's (read in the diff: the only changes are the argument check, `and not unread`, and the
appended reason). With 1, 2 or 6 (asserted): the 9 JUSTIFIED pairs become INCOMPLETE
[FINAL_CHECKPOINT_PRESENT_WITHOUT_READING] (27 cases); every other INCOMPLETE gains that reason last; NOT_JUSTIFIED is
unchanged; nothing becomes JUSTIFIED.

### Coordinator confirmations of 2026-09-24 (written into the spec, section 16)

| Confirmation | Builder's choice it confirms (revision 3) | Changed in 3a? |
|---|---|---|
| (a) folding STRUCTURE_ONLY into STRUCTURE_OR_OUTPUT_VARIATION | choice 1 | no |
| (b) at least 2 VALID NONE runs per arm AND every FINAL reading (valid or not) NONE | choice 2 | no |
| (c) FIELDS_NOT_READ_IN_ANY_RUN only with at least one FINAL reading; a field reading in an invalid run suppresses it | choice 4 | no; its scope is stated (choice 2 below) |
| (d) a firing guard stays the only architecture reason | choice 5 | no; a test now also checks it with an unread FINAL file |

### Choices I made (disclosed; please review)

1. **The arm labels are unchanged.** The task named `architecture_decision`. An arm label still speaks only about runs
   with a FINAL reading. So an arm can say SHOWS_NO_INPUT_USE while the architecture label is INCOMPLETE. The unread
   runs are listed per arm, and the spec says the architecture label is the decision (7.3).
2. **FIELDS_NOT_READ_IN_ANY_RUN is unchanged; its scope is stated.** The verifier offered: suppress it, or state its
   scope. Confirmation (c) fixes when it is emitted, so I did not add a condition. The spec (7.8), the frozen record and
   the verdict's `information` block say it covers runs with a reading only, and list the unread runs beside it.
3. **No partial reading is kept** (the verifier's optional idea). A file that fails any check gives no reading. It
   withholds JUSTIFIED instead.
4. **"Exists" means the path exists.** A file holding JSON `null` loads as nothing, but it is still flagged.
5. **The new argument is required.** A caller cannot forget it: `architecture_decision` refuses to run without it.

### Checks run (pure Python on the laptop; one at a time; no torch, no GPU, no AWS)

| Check | Result (measured) |
|---|---|
| `py_compile` of the three changed Python files; one import that printed `frozen_sha256` and two rule calls | OK; `torch` not imported |
| `pytest test_q4_ab.py` (whole file, once) | **42 passed** in 119.12 s (41 before; 1 new test) |
| Changed files | LF only, no control characters (counted in Python) |
| `launch.py` | unchanged since `294471a5`; still approves `3100f376...`; the lab's launcher test (in the 42) asserts it refuses this working copy |

Free memory before the test run: 838 MB (measured; the laptop has about 16 GB).

One edit after the test run: I restored one space in a comment in `q4_ab_rules.py` (line `if not reasons:`), which
my edit had removed. No code changed. The file was compiled again, and the hashes below are of the committed bytes.

Not re-run: `test_q4_sdg_curriculum.py` and `test_q4_error_panel.py`. Their files and the modules they import are
unchanged, and neither imports `q4_ab_rules` or `read_q4_ab_results`.

### Identity of revision 3a (NOT approved; the launcher still approves revision 2)

- `q4_ab_rules.frozen_sha256()`: `59d5a33d05dcd8929ee167b732a21746b5db2c15f79762aa4fb70b6690ac8349`
  (revision 3 was `dc7d014c...`; revision 2, still approved in `launch.py`, `3100f376...`).
- LF sha256 of the five files the launcher pins, as committed here:
  - `LAB/q4_ab_rules.py` `e14b077634f5bd0e6e0501c16fb5e21706a91ff45af48b3f799349f7f1b479e9` (changed)
  - `LAB/q4_ab_prep.py` `b0601e5382df15441526bf334fb8c548ee6a379d4b633a81adb60e40fca8fd23` (unchanged)
  - `LAB/q4_ab_train.py` `4d793a6afed5ddf6e399fcbcfff2bb1799a28ee725ab98cf4d59578e1bce8cd4` (unchanged)
  - `LAB/read_q4_ab_results.py` `08a143fd4f307e79accbf79df53c4a9da99cf3483297ce81b8e88bd450d5d08e` (changed)
  - `LAB/Q4_SDG_AB_SPEC_v0_2.md` `19eff8660ff75abbc116399a402ac55d49c241f310f4207280c7213a8b258aa3` (changed; this
    hash changes again when the status line is set to frozen after review)
- `LAB/test_q4_ab.py` `8fa328b89f5883880f2adb54b4b65d781d4000ae7782015c8258207955f88a6b`.

### Files changed in revision 3a

- `LAB/q4_ab_rules.py`, `LAB/read_q4_ab_results.py`, `LAB/test_q4_ab.py`, `LAB/Q4_SDG_AB_SPEC_v0_2.md`, and this report.
- NOT changed: `records/q4_sdg_1_20260923/ab_job/launch.py` and every other job file, `q4_ab_prep.py`,
  `q4_ab_train.py`, `q4_sdg_curriculum.py`, `Q4_SDG_DATA_PINS.json`, every Q3 file and pin, `records/q4_authorized_20260922/`.

### Next steps (in order; none is done)

1. A fresh review of revision 3a (this commit). It should check W1's fix and the five choices above.
2. After approval: set the spec's status line to the frozen form with the rules hash. Then write the new
   `APPROVED_FROZEN_SHA256` and `APPROVED_LF_SHA256` into `ab_job/launch.py`, in a commit of their own.
3. The data build, the pin and the training launch, as before.

### Open questions (for the coordinator and the owner)

1. **Arm labels** (choice 1): should an arm label also be withheld when one of its runs has an unread FINAL file? It
   is a small change. Not made.
2. **The same gap at checkpoint 0 (noticed, not fixed; outside this task).** A run whose checkpoint-0 file exists but
   gives no reading is left out of the calibration guard. If that untrained run would have fired the guard, and every
   FINAL reading is NONE, JUSTIFIED can still fire. Like W1 it needs a runner or file defect. A fix of the same shape
   would also only make JUSTIFIED rarer. Coordinator's call.
3. Still open from earlier: a teaching-fit floor (the owner's choice); MIXED as the overall lessons answer; the
   c7i.large price not re-read from AWS; B's exact pool size known only after the data build.

### EXPOSURE (everything outside my working copy that I opened or used)

- **Git:** `git pull --ff-only` of `claude/q4-sdg-feedback-20260923` (already up to date at `502a5704`); `git log`,
  `git show --stat` / `--name-only` of the last two commits, `git diff` of my own changes, `git status`,
  `git log -1 -- launch.py`, `git config core.autocrlf`. Then the commit and push of this revision.
- **My own scratch folder**
  `C:/Users/wakil/AppData/Local/Temp/claude/C--Users-wakil-OneDrive-Desktop-tksCAS-cas-only-reasoner/5e8709f4-3151-444f-939b-317c01bc3568/scratchpad/rev3a/`:
  compiled `.pyc` files of the three changed files, and the pytest temporary folder `pt_ab`. In it the lab fixtures
  built tiny B packages; the package code wrote and may have read its own generated `sealed_*` sidecars there. I
  opened none of them myself.
- **Memory queries:** two PowerShell reads of free physical memory (a number only).
- **Python and tools:** `C:/Python314/python.exe` and its standard library; pytest from the user site-packages. The
  pinned compiler's optional Rust `cas_engine` is switched off by the lab fixture for every measurement. Git Bash
  (`timeout`, `grep`, `tail`, `file`, `wc`, `sed`).
- **Context the harness gave me, not opened by me:** the user's `CLAUDE.md` files and memory index.
- **Inside the working copy, read:** `Q4_AB_REVIEW_20260924.md`, this report (its revision-2 section), `q4_ab_rules.py`,
  `read_q4_ab_results.py`, `test_q4_ab.py` (most of it), `Q4_SDG_AB_SPEC_v0_2.md` (status block, sections 7, 9, 12,
  14, 15), and a few `grep` lines of `records/q4_sdg_1_20260923/ab_job/launch.py` (read only). One `grep -l` over the
  lab's and the job folders' `.py` and template files, to find every caller of the rules and the reader (file names
  only). The tests read visible Q3 v0.7 files and run_001's records through the lab's own fixtures.
- **Not touched:** any `*_eval.jsonl`, any Q3 `sealed*` file, `D:/tksCAS-archive/`, any hset1a/hset1b path, S3 or any
  AWS service, the meta1 budget ledger, other worktrees, Claude transcripts, and the owner's documents on the research
  branch.
