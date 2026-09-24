# Q4-SDG-1 A-versus-B builder report (2026-09-24)

**Builder:** a Claude sub-agent, working only in `D:/tksCAS-worktrees/q4-sdg` on branch `claude/q4-sdg-feedback-20260923`.
**Label:** `CLAUDE_BUILT_CLAUDE_CHECKED` (temporary takeover while Codex is away). A Claude check of Claude work is
not an independent review.
**Status:** built and tested on the laptop in pure Python. **Nothing was launched. No AWS call was made. No money was
spent. No model was built or trained.** The spec is `PROPOSED_FOR_REVIEW`, not frozen.

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
