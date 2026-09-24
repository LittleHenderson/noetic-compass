# Q4-SDG-1 fresh review of commit 0b702cb8 (2026-09-23)

**Reviewer:** a fresh Claude sub-agent. I had no access to the builder's or the coordinator's conversation.
**Reviewed:** branch `claude/q4-sdg-feedback-20260923`, commit `0b702cb8` (parent `0687e20a`).
**Label:** `CLAUDE_BUILT_CLAUDE_CHECKED`. A Claude review of Claude work is not an independent review.
**Note:** the branch moved while I worked. The coordinator added `1a746ba0` (AWS job files). I did not review
that commit. I only glanced at its job template to check that it calls the panel the way the panel expects.

Paths below are relative to `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/`.
`LAB` = `research/helm_cas_expression_lab/`.

## Verdict

| Part | Verdict |
|---|---|
| Diagnostic job (`LAB/q4_error_panel.py`) | **APPROVE_WITH_MINOR.** It may launch as written. I found no blocker. Three cheap fixes (P1, P2, P3) would make the one $1.00 run more useful. Apply them only if that causes no delay. |
| Lesson adapter, static A/B/C package (`LAB/q4_sdg_curriculum.py`) | **Fit to build data**, with one condition: run the AWS build with `--expect-engine` and pin that exact build (A1). |
| Lesson adapter, family D rounds | **Not yet fit.** Fix A3 before any D arm. D is not part of the first A-versus-B comparison. |
| Proposed spec (`LAB/Q4_SDG_LESSONS_SPEC_v0_1.md`) | **CHANGES_REQUIRED before the A-versus-B training launch** (M1, M2). This does not block the diagnostic job or the data build. |

## What I ran

Everything ran on the laptop in pure Python. No torch. No GPU. No AWS. No money spent. Scratch builds went to my
scratch folder outside the repo and were deleted afterwards.

| Check | Result (measured) |
|---|---|
| `pytest test_q4_sdg_curriculum.py test_q4_error_panel.py` | **33 passed** in 6.89 s |
| LF hashes of the 12 runtime files vs both `records/q4_authorized_20260922/plan.json` and `run_001/plan.json` | 12 of 12 equal |
| `Q3_DATA_PINS.json` and the Q3 v0.7 `manifest.json` vs the plan | both equal |
| Canonical sha256 of the plan | starts `9dacc836`, equals `PLAN_SHA` |
| What `0687e20a` and `0b702cb8` change | 8 files added, 0 files changed; nothing under `records/` or `LAB/data/` |
| Panel selection (`select_panels`) | 16 + 16 + 64 rows; digest `0b98bfc94a5aed8af2d4fef72378fec7dfa9d46808b09ff30f750972387a3059` (the builder's digest) |
| Q3 G visible rows already in the one canonical surface | train 2048 of 2048; dev 256 of 256 |
| `one_field_edits` on **all 96** panel rows (not a sample) | 0 failures. Edits: noetic 453, domain 431, drive 453, register 453. Domain slots with no compilable edit: 22 |
| `matched_partners` | 95 of 96 rows have a partner; 22 partners come from another panel |
| Compiler probe, 14 hand-made PLUS/TIMES texts (domain ascent, same-core multi-register, PLUS operand under TIMES), with and without the Rust engine | same validity on all 14 |
| Size-256 build, Rust engine, `PYTHONHASHSEED=1` vs `4242` | all 19 files byte-identical |
| Size-256 build, Python engine vs Rust engine | 9 visible files byte-identical. Sealed files identical once the engine label is removed. Manifest differs (engine label) |
| `--verify --unpinned --recompile` on both size-256 builds (the Python-engine build re-checked with the Rust engine) | `Q4_SDG_VERIFY_PASS` both. A pinned verify is refused: `NO_PIN_FOR_THIS_DATA_VERSION` |
| Grouping patterns kept (size 256) | 3-leaf all-PLUS, 3-leaf all-TIMES, 4-leaf all-PLUS, 4-leaf all-TIMES, and 4-leaf mixed **only** as PLUS, PLUS, TIMES (2 bracketings) |
| TIMES swap pairs (size 256) | 16 of 16 have both leaves in the same domain |
| Near-twins across splits (size 256) | dev: 0 of 16 rows have a train row one token away. feedback: 2 of 16 (both single states) |
| Q3 v0.7 `manifest.json` stats (I read the manifest only, never an eval file) | G eval depths are `{4: 128, 5: 128}`. The G pool has 21 depth-3 bare shapes = 12 train + 9 dev |

The last row closes the shape question. There are exactly 21 bare tree shapes of depth 3. So the allowed set
("single state or one of the 16 G-train shapes") is exactly "every shape of depth 3 or less, minus the 9 G-dev
shapes". No G eval row can share a shape with a lesson row.

## Findings

### BLOCKER

None.

### MAJOR (spec only; fix before the A-versus-B launch)

**M1. No frozen decision rule.** `LAB/Q4_SDG_LESSONS_SPEC_v0_1.md:97-110` lists panels and metrics. It gives no
threshold, no comparison statistic and no number of starts.
- The directive (section 8) says: "New evaluation thresholds and model-selection rules must be fixed before the
  prospective results." Section 7 asks for "predefined additional starts".
- The owner's rule says a claim status must come from a program reading a frozen threshold.
- Failure scenario: A and B both run. B scores 9 of 256 exact on panel 2 and A scores 3. Nothing written says
  whether that is an improvement. The reader decides after seeing the numbers. The owner's rule forbids that.
- Fix: before launch, freeze the primary metric, the primary panel, the minimum difference, the seeds, and a small
  program that prints the status.

**M2. Panel 2 favours arm B.** `LAB/Q4_SDG_LESSONS_SPEC_v0_1.md:100` uses the package dev split as "new content,
familiar structure" for both arms.
- That split is drawn from B's own lesson mix: 25% family A (single states and one-field pairs), 25% depth-1 B pairs,
  50% C. Arm A trains only on G-train rows.
- The spec reports single states apart. The rest still differs from arm A's data: family A balances "no drive" at
  1 in 8, while G leaves have no drive half the time (builder's open question 7).
- Failure scenario: B beats A on panel 2 only because panel 2 looks like B's training data. It is then reported as
  "SDG lessons help".
- Fix: declare a symmetric primary sub-panel now. One option is fresh G-shape rows with G's leaf rule (the
  `C/mixed_allowed_shapes` generator, on a new seed, at least 256 rows; it is 38 rows at size 4096). Report every
  subfamily separately.

### MINOR

**A1. The package identity depends on the compiler engine, and `--expect-engine` is optional.**
- Where: the engine label is written into every sealed row (`LAB/q4_sdg_curriculum.py:564-565`, `:868`) and the
  manifest (`:994`). `expect_engine` defaults to `None` (`:912`, `:922-923`, CLI `:1413`).
- Measured: at size 256 the content is the same with or without the Rust engine. Only the label differs. So the
  manifest sha256 differs.
- Failure scenario: the pin is taken from one engine's build. A later rebuild or re-check with the other engine
  gets `MANIFEST_NOT_THE_PINNED_ONE`. That is fail-closed, but it can waste a paid job.
- Fix: make `--expect-engine` required for `--build`, and record the engine in the pin entry. The AWS machine has
  no Rust engine, so the AWS build would be `--expect-engine python`.
- Engine parity at size 4096 is not measured. The risk looks low: every refusal rule I probed is decided in the
  same Python code under both engines (for TIMES, the Rust call falls back to the Python check when it raises).

**A2. Family-A near-twins across splits (builder's open question 5).** Policy stated at
`LAB/q4_sdg_curriculum.py:1000-1002`.
- It is not a target leak. No dev target appears in train. The changed field must still be read from the input.
- But at `--size 4096`, family A fills about 1,152 of the 1,600 cells, about 1,024 of them in train. Each cell
  has 23 one-field neighbours. So almost every family-A dev row will have a train row that differs in one field.
  This is an **estimate**, not a measurement: my builds were capped at size 256.
- B and C rows draw leaves at random from a large space, so near-twins there should be rare.
- For the feedback split (the family-D trigger source) this does not matter.
- For panel 2 it matters. The directive (section 8) says: group near-duplicates before the split, or disclose paired
  exposure as a separate test design.
- Fix: store each dev row's smallest token distance to any train row. Report family-A dev rows, and any dev row at
  distance 1, separately.

**A3. Family D rounds are not ready.** None of this affects A versus B.
- (a) The output folder is reserved at `LAB/q4_sdg_curriculum.py:1349`, before the trigger sources are checked at
  `:1352-1357`. A refused trigger leaves `<out>.partial` behind. A retry then fails `PARTIAL_OUTPUT_EXISTS`. The
  refusal test (`LAB/test_q4_sdg_curriculum.py:425-428`) leaves such folders in pytest's temp folder.
- (b) Freshness is checked against the parent package only (`:1344-1348`), not against earlier D rounds. Round 2
  can repeat round-1 rows.
- (c) A D package cannot be pinned (`:1113-1114`). Pins are keyed by schema, so at most one D round could be pinned
  anyway. A trainer would have to load D rows with `pinned=False`, outside the pin defence.
- (d) One `PREDICTION_ENDED` or `GRAMMAR_VIOLATION` trigger stops the whole round (`UNTEACHABLE_TRIGGER`, `:1265`).
  It should be counted and skipped.
- (e) Nothing ties `predicted_tokens` to a real model output. A trigger file could carry a mistake seen on a dev
  row under a train row's id. Record the producing checkpoint sha256 and decode settings in the trigger file.

**P1. Update-1 gradient per module group is computed, then dropped.** `LAB/q4_error_panel.py:594` computes
`at_init["grad_norms"]` for all groups; `:624-627` writes only the total.
- Update 1 is the only gradient the run really applied. Its saved pre-clip norm is 0.7250789403915405, below the
  clip of 1.0, so it was not clipped.
- Fix: write the per-group norms too.

**P2. Weight-change numbers are written even when the re-initialisation does not match.**
`LAB/q4_error_panel.py:620-628` writes `by_module_group` and `by_tensor` in both cases.
- Failure scenario: the status says `REINIT_NOT_REPRODUCED_ON_THIS_DEVICE`, but someone later quotes "the encoder
  moved X%" from the wrong baseline.
- Fix: write `null` for those numbers in that case, or nest them under a key that says they are not the true change.

**P3. A Stage-0 mismatch cannot be explained without a second paid run.** `LAB/q4_error_panel.py:326-336`,
`:676-680` save the decoded trees only.
- Failure scenario: a near-tie flips one decode on the T4. The job stops, as designed. Nobody can tell a near-tie
  from a real source fault.
- Fix: record the gap between the top two allowed logits at each free-decoding step (16 rows, cheap).

**P4. The 32 extra G-dev rows become "inspected".** `public64` shows the original model's behaviour on 32 more
G-dev rows (`LAB/q4_error_panel.py:205-215`). Spec panel 3 (`LAB/Q4_SDG_LESSONS_SPEC_v0_1.md:102`) uses all 256
G-dev rows and flags only the old 16.
- Fix: flag all 48 inspected rows. Report panel 3 with and without them.

### NOTE

- **N1. The 3-leaf mixed grouping claim is true, as "at most one".** With one PLUS and one TIMES, one bracketing
  puts a PLUS subtree under TIMES. The compiler refuses it at type-check ("TIMES requires singular state
  operands"), under both engines. The other bracketing can still fail domain ascent. So "exactly one can compile"
  (`LAB/q4_sdg_curriculum.py:678`; builder report line 61) should read "at most one". The test checks "at most
  one", which is right.
- **N2. The 4-leaf "mixed" grouping has one operator pattern only.** By the same rule, only PLUS, PLUS, TIMES (in
  reading order) leaves two bracketings that compile: `((a + b) + (c × d))` and `(a + (b + (c × d)))`. Measured at
  size 256: that is the only mixed pattern kept. Log it as such.
- **N3. TIMES swap pairs are always same-domain.** Both orders must avoid domain ascent. 16 of 16 at size 256. This
  is a compiler rule, and G has the same rule. It is a possible shortcut cue; the refusal log shows it.
- **N4. `lesson_family` is in the visible rows** (`LAB/q4_sdg_curriculum.py:87`, `:862`). "A" means a single state
  and "B" means depth 1. `sequence_input` (`:1165-1170`) drops it, so this is fine while the trainer uses
  `sequence_input`.
- **N5. Q3 R eval overlap is unknown.** A lesson single state could equal a Q3 R eval text. I cannot check that
  without opening eval. The risk looks low: R dev has 0 rows in the lesson surface (R train has 259 single states).
  It matters only if R eval is ever used on an SDG-trained model.
- **N6. Q5 control and partner length.** The same-example re-encode control is exactly zero by construction; it is
  a determinism check. Partners share the bare shape and token length, but not the input byte length. The directive
  says "prefer substitutions with similar length and shape". Picking the same-shape partner with the closest byte
  length would be closer to that.
- **N7. Q4 edit summaries mix two kinds of edit.** Drive and register edits from "none" to a value (or back) change
  the input length. Other edits do not. `LAB/q4_error_panel.py:453-469` pools them. The raw `from`/`to` fields let
  an analyst split them later.
- **N8. `CUDA_VISIBLE_DEVICES` must not be set.** `q4_smoke_job._check_device_idle` refuses any non-empty value
  (`LAB/q4_smoke_job.py:208-209`). The coordinator's job template does not set it.
- **N9. Record ids are positional.** A size-256 scratch build and the size-4096 AWS build share ids for different
  rows. The pin and the trigger file's `parent_manifest_sha256` stop mixing. Never key data by record id across
  packages.
- **N10. Spec wording to confirm with the owner.** The directive says "change grouping, operator identity and leaf
  values in separate controlled families before combining all three". The spec reads "before" as "as separate
  families", shuffled together, not as an order in time. Also, the curriculum variant's promotion metric
  (`LAB/Q4_SDG_LESSONS_SPEC_v0_1.md:65`) should say teacher-forced or free generation.

## Answers to the five review questions

1. **Custody and leaks.**
   - The shape rule is checked on every row, not a sample: at creation (`check_intended`, `:531-536`), over the
     whole package (`self_check`, `:1015-1032`), at every load (`load_lesson_pairs`, `:1193`), and in D rounds
     (`:1384`).
   - No lesson row can have a G eval shape (eval is depth 4-5) or a G-dev shape. No lesson text can equal a Q3 G or
     R dev text.
   - Groups get their id before the split (`:793`). Whole groups go to one split (`:959-965`). `self_check`
     refuses a straddling group (`:1029-1031`).
   - D triggers must be package train or feedback ids, with the matching split (`:1352-1357`). Q3 dev ids are refused
     (`:1354`). The target comes from the package, not from the trigger file.
   - Neither module calls `load_split` or `load_dataset`. The only Q3 doors used are `check_pins` (manifest and pin
     file) and `load_visible` (visible files). The adapter reads its own package's `sealed_*` sidecars only.
   - The near-twin question: see A2. Fine for feedback use. For the dev panel, report separately.
2. **Row correctness.** One canonical surface; compile must be valid; compiled tree must equal the intended tree
   (fail closed); unsupported nodes are refused, and a spelling that cannot be inverted fails closed; tokens
   round-trip; slot kinds are read from `allowed_next` and cross-checked with a stack. The pair relations are
   checked on the compiled token streams for every group. The 3-leaf mixed claim holds (N1).
3. **Identity and immutability.** New schema, new seeds (20260941, 20260951, 20260971), new data folder, a separate
   pin file. The Q3 files and the 12 runtime files are unchanged (measured). The record-id formula matches the
   report. Writes are create-only (the pin file is rewritten by design). Rebuilds are byte-identical, also across
   hash seeds (measured). Engine: see A1.
4. **Error panel, read as code.** I found no bug that would make the numbers wrong.
   - No optimizer and no step anywhere. Gradients are zeroed before and after every backward pass
     (`:546`, `:563`).
   - `GPU_REQUIRED` fires on the device string before any import or write. After the data checks it tests CUDA,
     the torch and Python versions, and an idle GPU. There is no CPU path.
   - The plan, result, update and prediction records and the weights sha256 are checked (`:129-148`).
     `load_checkpoint` re-checks identity and the 12 runtime pins.
   - Stage 0 compares the same four keys the smoke job saved (`record_id`, `outcome`, `ast`, `steps`) and stops on
     any difference.
   - Alignment is right: logits at position i predict target token i, in the teacher-forced pass, the step-by-step
     pass, the edit probes and the swap probes.
   - The model has no dropout, so train mode versus eval mode changes no formula. The step-by-step versus
     full-sequence gap is recorded anyway.
   - The losses match the smoke job: full-vocabulary cross-entropy, mean. The equal-weight check is recorded. The
     position losses use a 0/1 mask and a mean.
   - The tie-break equals `free_decode`'s. Deterministic flags and `CUBLAS_WORKSPACE_CONFIG=:4096:8` match the
     smoke job.
   - The re-initialisation follows the smoke job's order (seed, then `build_model`) and is checked on update 1. The
     update-1 row and order come from the same seeded shuffle. Weight tensors are small, so the CUDA random kernels
     should launch the same way on a T4. This is reasoning, not a measurement; the update-1 check will tell.
   - No eval or sealed file is opened. Every record or weight file the module opens itself goes through
     `guarded_read`. Source hashing reads a fixed list of source file names. Q3 rows come only through
     `q3_load.load_visible`.
5. **Spec versus directive.** M1 and M2 conflict with sections 7 and 8. Also N10. The rest fits: A versus B first,
   equal update counts with token counts reported, the same seed and optimizer, no model selection, protected G eval
   used once with owner approval.

## What I could not check

- Every torch path: Stage 0 on a T4, the question 3 to 6 numbers, GRU backward determinism on a T4, and whether the
  re-initialisation reproduces update 1.
- The size-4096 build: its run time, its refusal rates, its engine parity and its near-twin rate (A2 is an
  estimate).
- The coordinator's later commit `1a746ba0`. I only read `job.sh.template` and `JOB_LIMITS.md` for integration.
  They set `CUBLAS_WORKSPACE_CONFIG=:4096:8`, do not set `CUDA_VISIBLE_DEVICES`, install torch from the cu128 index,
  and check the same selection digest I reproduced. I saw no conflict with the panel.

## EXPOSURE (everything outside this worktree that I opened or used)

- **Git object store:** `git show 8eb798a5:<directive path>` (the object was already local). `git fetch origin
  claude/q4-sdg-feedback-20260923` to check the remote tip before pushing. No other `git show`.
- **My scratch folder** `C:/Users/wakil/AppData/Local/Temp/claude/C--Users-wakil-OneDrive-Desktop-tksCAS-cas-only-reasoner/5e8709f4-3151-444f-939b-317c01bc3568/scratchpad/q4rev/`:
  - three probe scripts I wrote (`engine_probe.py`, `engine_build.py`, `panel_probe.py`);
  - three size-256 builds I made (`b256_rust`, `b256_rust2`, `b256_py`). I read their `sealed_*` files, which I had
    just generated;
  - all deleted after this review.
- **pytest temp folders** `C:/Users/wakil/AppData/Local/Temp/pytest-of-wakil/pytest-*/`: the tests' own tiny
  builds. I listed the folder names only. I did not delete them, because I could not tell my run's folder from
  another session's.
- **Python:** `C:/Python314/python.exe`, its standard library and pytest. The pinned compiler imported the optional
  Rust `cas_engine` from `C:/Users/wakil/AppData/Roaming/Python/Python314/site-packages/cas_engine/`. I did not open
  those files.
- **Inside the worktree, for the record:** I read `LAB/data/q3_v0_7/manifest.json` (keys and stats; it lists eval
  file hashes and G eval depth counts). I read visible Q3 files only through `q3_load.load_visible`. I opened no
  `*_eval.jsonl` and no Q3 `*sealed*` file.
- **Not touched:** `D:/tksCAS-archive/`, any hset1a path, any other worktree, S3/AWS, and any Claude transcript.
