# Q4-SDG-1 A-versus-B comparison, spec v0.2

**Status: PROPOSED_FOR_REVIEW**

How this status changes: after a fresh review approves this spec and the code it names, the coordinator replaces
the status line above, and nothing else, with the frozen status. The training launcher (`records/q4_sdg_1_20260923/ab_job/launch.py`)
refuses to launch unless that exact frozen status line is present at the source commit. Any other change after
that needs a new version number.

Label: `CLAUDE_BUILT_CLAUDE_CHECKED` (temporary takeover while Codex is away). Experiment id **Q4-SDG-1**. Builder: a
Claude sub-agent. Nothing here has run on AWS. No model has been trained under this spec.

**Authority.**
- The owner's directive `Q4_SDG_AND_TARGETED_FEEDBACK_DIRECTIVE_20260923.md`, sections 5 to 9.
- The owner's grant and the decision taken under it: `OWNER_AUTHORITY_AND_DECISIONS_20260924.md` (research branch
  `9656dc19`). Keep Q4's architecture. Run A versus B. 3 seeds per arm, declared before launch. Measure input use at
  fixed checkpoints. A rule frozen in advance decides whether an architecture change is justified. **$5.00 ceiling**,
  the pinned data build included. One GPU machine at a time. No automatic retries. The protected examination stays
  out of every loop.
- The fresh review `Q4_REVIEW_0b702cb8.md`: this spec fixes M1 (a frozen, program-emitted rule), M2 (shared panels
  that favour neither arm) and A1 (the compiler engine pinned for the build). A3 is addressed only where it touches
  families A-C (section 10).

**Where every frozen value lives.** `q4_ab_rules.py` (standard library only). This document explains those values. If
the two ever disagree, the program wins, and the disagreement is a defect to report.

Paths are relative to `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/`. `LAB` =
`research/helm_cas_expression_lab/`.

## 1. What is compared

| Arm | Teaching rows | Rows in the pool |
|---|---|---:|
| **A** | the existing family-G teaching: visible Q3 v0.7 G train rows, minus the 256 rows reserved for panel SP1 | 1,792 |
| **B** | the new CAS SDG lessons: the pinned package `helm-cas-expression-lab.q4-sdg-lessons/0.1`, size 4096, families A, B and C, train split, minus any row whose tree equals a panel row. **No family D.** | about 4,100 (exact count in `prep.json`) |

Everything else is the same for both arms: the model, the loss, the optimizer, the learning rate, the clipping, the
number of updates, the starting tensors of each seed pair, the panels and the measures.

## 2. Seeds (declared before launch)

| Seed | Use |
|---|---|
| **20260931, 20260932, 20260933** | Training. Pair i uses the SAME seed for arm A and arm B, so both arms of a pair start from identical tensors. New values: not 20260921-20260925 (Q3), not 20260941/20260951/20260971 (SDG package, feedback panel, error panel), not 20260961/20260980+ (D rounds). |
| 20260965 | Selection of panel SP1 (new). |
| 20260921 | Only the Stage-0 re-initialisation check of the original run. |
| 20260941, 20260951 | The B package's own seeds (unchanged from `q4_sdg_curriculum.py`). |

Run order: A 20260931, B 20260931, A 20260932, B 20260932, A 20260933, B 20260933. A timeout therefore keeps whole pairs.

## 3. Hyperparameters

Every value below is identical to `records/q4_authorized_20260922/run_001/plan.json` (plan sha256 `9dacc836...`),
except the two rows marked **DIFFERENT**. A test re-reads that plan and checks the call order of `q4_smoke_job.py`.

| Setting | This comparison | run_001 |
|---|---|---|
| Model | `build_model(NeuralConfig(64))`: width-64 GRU encoder and decoder, 70,818 parameters, unchanged code | same |
| Build order | `torch.manual_seed(seed)`; `torch.cuda.manual_seed_all(seed)`; deterministic flags; `build_model`; `AdamW`; then the seeded order | same (`q4_smoke_job._worker`) |
| Optimizer | `torch.optim.AdamW(model.parameters(), lr=0.001)`, every other argument at the torch default | same |
| Learning rate | 0.001 | same |
| Gradient clipping | `clip_grad_norm_(..., 1.0, error_if_nonfinite=True)` | same |
| Loss | `cross_entropy(logits, gold)`: full vocabulary, mean over target positions, EOS included | same |
| Batch | one example per update | same |
| Numerical policy | `CUDA_FLOAT32_DETERMINISTIC_OR_FAIL_NO_FALLBACK`; `CUBLAS_WORKSPACE_CONFIG=:4096:8` | same |
| Presentation order | epoch 0: `order = list(range(n)); random.Random(seed).shuffle(order)`, exactly as run_001; later epochs: a fresh shuffle from the same `random.Random(seed)` | same for epoch 0 (run_001 never finished one epoch) |
| **Number of updates** | **32,768** | **DIFFERENT**: 128 |
| **Teaching data** | **arm A: G train minus SP1 (1,792 rows); arm B: the SDG package** | **DIFFERENT**: 2,048 G train rows |

**Why the two differences.**
- *Updates.* The directive (section 7) asks for "a meaningful declared practice budget". run_001 presented 128 of
  2,048 rows once. The diagnosis cannot tell "the input path cannot carry the information" from "it has not yet
  learned to" (RUN_LOG, "What this does NOT show"). Only a longer run separates them. 32,768 is 256 times run_001, 16
  times the earlier 2,000-update job, and it fits the money (section 5).
- *Teaching data.* B's data is the thing under test. A loses the 256 rows reserved for the shared panel SP1, so that
  no panel row is ever taught (review M2).

Also different, and not a training setting: evaluation decodes stop at 64 tokens (every panel target has at most 56
tokens, so a longer decode is wrong under any limit; exactness is unchanged). The grammar mask is the default one.

## 4. Practice budget and checkpoints

| Item | Arm A | Arm B |
|---|---|---|
| Updates per run | 32,768 | 32,768 |
| Presentations per run (one row per update) | 32,768 | 32,768 |
| Runs | 3 | 3 |
| Updates and presentations per arm | 98,304 | 98,304 |
| Passes over the pool per run | 32,768 / 1,792 = 18.3 | about 32,768 / 4,100 = 8 |
| Mean target length (tokens) | 21.15 (37,905 tokens over 1,792 rows) | measured and written per run |

**Equal updates are not equal compute** (directive section 7). Each run records the target tokens and source bytes it
consumed, the distinct rows it saw, its training time, its evaluation time and its peak GPU memory. These are reported.
They do not enter any rule.

**Checkpoints** (measured after this many updates): **0, 128, 512, 2048, 8192, 16384, 32768**. 32,768 is FINAL. The
final checkpoint is the only one any decision uses. There is no early stopping and no model selection. Checkpoint 0 is
the untrained model; it calibrates the input-use rule (section 7.4). Checkpoint 128 is run_001's budget. Checkpoint
16,384 is v0.1's proposed budget. Evaluation reads the model only; it never touches the optimizer, the training order
or any random stream, so the checkpoints do not change the training path.

## 5. Runtime and money

**Measured anchor.** The error-panel diagnostic took **26.7 s** on a T4 for about 14,200 decoder calls, about 2,000
encoder calls and 385 backward passes. So one decoder call costs at most about 1.6 ms. The cost of one training update
(forward, backward, AdamW step) is an **assumption** of about 5 ms until the smoke stage measures it on the machine.

| Part | Typical | Upper |
|---|---|---|
| One checkpoint (832 decodes of at most 64 tokens, 832 teacher-forced passes, 773 edits) | 41 s | 90 s |
| Training, one run (32,768 updates) | 2.7 min | 8.2 min (at 15 ms per update) |
| One run (7 checkpoints, training, reload check) | 8 min | 20 min |
| Six runs | 48 min | 120 min |
| Setup, panels, Stage 0, B rebuild, smoke | 13 min | 22 min |
| **Training machine** (g4dn.xlarge, $0.541959 per hour with address and disk) | **61 min, $0.55** | **142 min, $1.28** |
| Data-build machine (c7i.large, section 10) | about 10 min, $0.02 | $0.0813 at its deadline |

**Hard ceiling arithmetic.** Data build worst case $0.0813 + training worst case $2.1678 (240-minute client deadline)
= **$2.2491 <= $5.00**. Both launchers check it. The training launcher uses the data build's MEASURED cost bound from its
watch record. The smoke stage projects the time of all six runs (x 1.25) and stops the job (`PROJECTED_OVER_TIME`)
before any main run if the projection does not fit the runner's 190-minute limit or a run's 50-minute limit.

## 6. Shared panels (review M2)

| Panel | Rows | Definition | Role |
|---|---:|---|---|
| **SP1** `FAMILIAR_STRUCTURE_NEW_CONTENT` | 256 | Visible Q3 G train rows, reserved before any arm, never taught to either arm. Drawn only from rows the diagnostic never showed (its 48 inspected train rows are excluded). Allocated to the G-train shapes in proportion to their available rows (largest remainder; never more than half of a shape's rows, so every shape keeps rows for arm A). Within a shape: seeded shuffle (20260965) of the rows in file order; shapes in sorted key order. Digest `dab48792...` (`q4_ab_rules.SP1_DIGEST`). | shared; **decisive** |
| **SP2U** `NEW_STRUCTURE_UNINSPECTED` | 208 | The visible G dev split (the 9 held-out depth-3 shapes) minus the 48 dev rows the diagnostic inspected (old_dev16 plus the 32 in public64; digest `d91d914b...`). | shared; **decisive** |
| **SP2ALL** `NEW_STRUCTURE_ALL` | 256 | The whole visible G dev split, the 48 inspected rows included. | shared; labelled and reported |
| **B_DEV** | about 256 | The B package's own dev split. **B-internal**: drawn from B's own mixture, so it favours B. | reported only; never in a rule |
| **TEACH_FIT** | 64 | The first 64 rows of each run's own first epoch. | per run; never compared |
| **EDIT64** | 64 | SP1 rows 0, 4, 8, ...: 773 compilable one-field edits (196 noetic, 185 domain, 196 drive, 196 register; 11 domain fields have no compilable edit). Digest `05d62b99...`. | the edit-sensitivity measure |

**SP1 by shape** (rows): `(L L)` 95, `(L (L L))` 53, `((L L) L)` 26, `(L (L (L L)))` 24, `((L L) (L L))` 17,
`((L L) (L (L L)))` 16, `((L (L L)) L)` 6, `(L ((L L) (L L)))` 6, `((L L) ((L L) (L L)))` 5, and 1-2 rows each for five deep
shapes. Two G-train shapes have 0 rows here: they have only 4 and 2 rows in all of G train. Targets: 5,337 tokens,
799 noetic positions.

**Exclusion, both ways.**
- Arm A's pool is G train minus the 256 SP1 rows (digest `9064635d...`, 1,792 rows). No arm-A row has the tree of any
  SP1 or SP2 row.
- Arm B's pool drops every package row whose tree (content sha256) equals an SP1 or SP2 row. The count dropped is
  written in `prep.json`. The package already excludes G-dev shapes and every Q3 dev text.
- The panels are fixed before any arm runs: every digest above was measured on the laptop from visible files only,
  with the pure-Python compiler engine, and the machine must reproduce all of them before any GPU work.

**Which arm do the shared panels favour?** Both are drawn from the family-G distribution, which is arm A's own
teaching distribution. B meets these shapes in its family-C "mixed allowed shapes" lessons (15% of its pool) and
single-depth shapes in family B. So if either arm is favoured, it is A, the control. A B win on SP1 or SP2U is
therefore not a panel artefact. A B loss may be partly distribution shift; that is reported, not relabelled.

**Near twins (review A2), disclosed, not decisive.** Every SP1/SP2 row carries its smallest token distance to each
arm's pool. Against arm A: 6 of the 512 rows are one token away from a teaching row (measured). The reader reports
every pair comparison again without rows at distance 0 or 1 from either arm.

## 7. Decision rules (review M1)

A program, `read_q4_ab_results.py`, emits every label below from the result files. No person chooses a label.

### 7.1 INPUT_USE_DETECTED(arm, seed, checkpoint)

**INPUT_USE_DETECTED iff T1 and T2 and T3.** Otherwise **INPUT_USE_NOT_DETECTED**.

**T1: field accuracy above what an input-blind model can reach.**
- Measure: teacher-forced (correct previous tokens), grammar-masked choices at every **noetic** position of SP1
  (799 positions). k = correct choices.
- Null rate p0 = the larger of (a) the most frequent noetic value's share in **that arm's teaching pool** and (b) its
  share among the SP1 targets. For arm A: max(605/5,671, 90/799) = 90/799 = 0.1126.
- Pass iff the exact one-sided binomial P(X >= k | 799, p0) <= **1/100**.
- For arm A this means **k >= 112 of 799 (14.0%)**.
- Why noetic: in both arms the Noetic is close to uniform over 10 values and nearly independent of the earlier tokens,
  so a model that ignores the input cannot beat p0 by reading the prefix. Domain, drive and register are partly
  predictable without the input: TIMES forces its two operands into one domain, and "no drive" / "no register" are
  about half of all leaves (SP1: 406 and 410 of 799). The diagnosis shows exactly this: noetic 36/453 (below chance),
  but drive 227/453 and register 214/453 (the "none" rate). Those three fields are tested the same way and reported;
  they are not decisive.
- Why the larger of the two rates: a model that always writes one value scores that value's panel share. Using the
  larger rate means such a model can never pass.

**T2: the right output moves when one input field changes.**
- Measure: for each of the 773 EDIT64 edits, with the correct previous tokens held fixed, delta = p(new token | edited
  input) - p(new token | original input), full-vocabulary softmax.
- u = edits with delta >= **0.01**; d = edits with delta <= -0.01.
- Pass iff u >= **1/10** of the edits (78 of 773) AND the exact one-sided sign test P(X >= u | u + d, 1/2) <= **1/100**.
- Why 0.01: the saved model's largest move over 1,812 edits was 3.6378e-06 (noetic), every median 0.0. 0.01 is about
  2,700 times that noise floor.
- Why 1/10: a model that reads even one of the four fields well moves about a quarter of the edits. 1/10 needs
  real reading of at least part of one field. The sign test needs the moves to go TOWARD the new token, which an
  untrained model's random input dependence does not do.

**T3: free generation depends on the input.**
- Measure: distinct free-decoded token sequences over the 256 SP1 rows.
- Pass iff at least **32**.
- Why 32: the saved model produced 1 distinct output for 96 inputs. SP1 holds 14 shapes, so reading the shape alone
  gives at most 14 outputs; 32 needs outputs that depend on content.

Reported with every reading, never decisive: the summary cosine between SP1 partners of the same shape (the saved
model: minimum 0.9966), the masked choice changes under edits, first-wrong-decision kinds, outcomes and mean lengths.

### 7.2 Arms

For each arm, over its 3 seeds, at the FINAL checkpoint:
- **ARM_<arm>_SHOWS_INPUT_USE** iff at least **2** valid runs are INPUT_USE_DETECTED.
- **ARM_<arm>_DOES_NOT_SHOW_INPUT_USE** iff detected runs + runs that are not valid < 2.
- **ARM_<arm>_INPUT_USE_UNDETERMINED** otherwise (missing or invalid runs could still change the answer).

### 7.3 ARCHITECTURE_CHANGE_JUSTIFIED

- **ARCHITECTURE_CHANGE_NOT_JUSTIFIED** iff some arm SHOWS_INPUT_USE.
- **ARCHITECTURE_CHANGE_JUSTIFIED** iff every arm DOES_NOT_SHOW_INPUT_USE, that is, no arm shows INPUT_USE_DETECTED at the
  final checkpoint in at least 2 of its 3 seeds.
- **ARCHITECTURE_DECISION_INCOMPLETE** otherwise, or when the calibration guard fires (7.4).
- **ARCHITECTURE_NOT_EVALUATED** when there is no verdict at all (section 8).

"Justified" means only what the owner's decision says: an architecture change may then be designed as a separately
named, reviewed arm. The rule does not choose the change and does not start it.

### 7.4 Calibration guard

If any run shows INPUT_USE_DETECTED at checkpoint 0 (untrained), the rule is not trustworthy on this machine:
**INPUT_USE_RULE_FIRES_AT_INITIALISATION**, and the architecture label is ARCHITECTURE_DECISION_INCOMPLETE. Otherwise
**INPUT_USE_RULE_SILENT_AT_INITIALISATION**.

### 7.5 Lessons: B versus A, per panel P in SP1, SP2U, SP2ALL

For seed pair i (A and B on the same seed), at the FINAL checkpoint, on exact canonical trees (the free-decoded tokens
equal the target tokens, EOS included, outcome GENERATED), row by row:
- b = rows where B is exact and A is not; c = rows where A is exact and B is not.
- **B_BEATS_A_P_PAIR<i>** iff b > c and the exact one-sided sign test P(X >= b | b + c, 1/2) <= **1/100** (b >= 7 when c = 0).
- **A_BEATS_B_P_PAIR<i>** by the mirror rule. **NO_PAIRED_DIFFERENCE_P_PAIR<i>** otherwise.
- **PAIR_INCOMPLETE_P_PAIR<i>** if either run is not valid, or the two runs did not start from identical tensors (their
  initial state hashes differ, or their checkpoint-0 outputs on SP1 and SP2 differ).

Then, per panel:
- **LESSONS_HELP_P** iff B_BEATS_A in all 3 pairs.
- **LESSONS_HURT_P** iff A_BEATS_B in all 3 pairs.
- **LESSONS_COMPARISON_INCOMPLETE_P** if any pair is incomplete.
- **LESSONS_EFFECT_NOT_SHOWN_P** otherwise.

B_DEV is reported for both arms and labelled B-internal; it enters no rule.

### 7.6 Run validity

**RUN_VALID** iff: the run manifest, all 7 checkpoint files, the run result (status COMPLETE, 32,768 updates) and a
reload check with status RELOAD_REPRODUCED are present; every file carries the frozen-rules hash; and the runner's own
totals agree with the reader's recomputation (exact flags, teacher-forced counts, distinct outputs). A missing file
gives **RUN_INCOMPLETE**. Anything else gives **RUN_INVALID_<reason>**.

## 8. Stops

Stage 0 comes first. Before anything is trained, the machine must reproduce the diagnostic on itself:
- the original checkpoint (`run_001`, weights `d54f5715...`) replays its 16 saved dev decodes exactly
  (**STAGE0_NOT_REPRODUCED** otherwise);
- the model rebuilt with seed 20260921 in q4_smoke_job's call order reproduces update 1's loss and gradient norm
  (**REINIT_NOT_REPRODUCED** otherwise).

If Stage 0 does not reproduce, the job stops and the reader emits **NO_VERDICT_STAGE0**. No label about arms, the
architecture or the lessons is emitted.

Every stop writes `STOP.json` with its code and ends the job. Nothing is retried. Completed runs stay valid evidence.

| Code | When |
|---|---|
| `GPU_REQUIRED` | no explicit `cuda:N`, or CUDA unavailable. Checked before any torch import or file write. No CPU path. |
| `GPU_BUSY_OR_UNKNOWN` | nvidia-smi reports another compute user, or cannot be read |
| `RUNTIME_VERSION_MISMATCH` | torch other than 2.11.0+cu128, or Python other than 3.14 |
| `CUBLAS_WORKSPACE_CONFIG_DIFFERS` | not `:4096:8` |
| `CUSTODY_REFUSED` | an eval or sealed name in the Q3 data folder, or in a read path |
| `RUN_001_RECORDS_INCONSISTENT` | the original run's plan, weights or records differ from their digests |
| `Q3_DATA_NOT_PINNED` | the Q3 v0.7 manifest or visible files differ from their pins |
| `COMPILER_ENGINE_NOT_PYTHON` | the compiler would use the optional Rust engine |
| `PANEL_DIGEST_MISMATCH` | any panel, the edit list or arm A's pool differs from its frozen digest |
| `B_PACKAGE_NOT_PINNED` | `Q4_SDG_DATA_PINS.json` has no entry for the package |
| `B_PIN_NOT_THE_FROZEN_PACKAGE` | the pin names another engine, size, seed or folder |
| `B_PACKAGE_BUILD_FAILED` | the rebuild on the machine fails |
| `B_PACKAGE_MISMATCH` | the rebuilt package differs from the pin |
| `STAGE0_NOT_REPRODUCED`, `REINIT_NOT_REPRODUCED` | see above |
| `SMOKE_NONDETERMINISTIC` | two identical 64-update smoke runs differ in any weight or output |
| `SMOKE_PAIR_INIT_MISMATCH` | arm A and arm B do not start from the same tensors |
| `SMOKE_FAILED` | reserved for a smoke failure without a more specific code |
| `PROJECTED_OVER_TIME` | the smoke projection (x 1.25) exceeds the time left or a run's 3,000 s |
| `NUMERICAL_FAILURE` | a non-finite loss or gradient |
| `RUN_WALL_LIMIT`, `JOB_WALL_LIMIT` | a run exceeds 3,000 s, or the runner exceeds 11,400 s |

Outside the runner: the in-machine timer (225 min), the shutdown (228 min) and the watcher's client deadline
(240 min) end the machine whatever happens.

## 9. Reading rule

| Program | Reads | Writes |
|---|---|---|
| `q4_ab_train.py` (T4 machine) | visible Q3 v0.7 files, run_001's records and weights, the B package's visible files and manifest, `Q4_SDG_DATA_PINS.json` | `out/ab/`: `gates.json`, `stage0.json`, `prep.json`, `smoke/`, `smoke_summary.json`, `runs/<arm>_<seed>/{run_manifest.json, checkpoint_<NNNNN>.json, updates.json, run_result.json, checkpoint/, reload_check.json, reload.log}`, `job_result.json`, `STOP.json` (all create-only) |
| `read_q4_ab_results.py` (laptop, and once on the machine) | ONLY `job_result.json`, `STOP.json`, `stage0.json`, `prep.json` and `runs/*/{run_manifest.json, checkpoint_*.json, run_result.json, reload_check.json}`. Never `smoke/`, data, weights, or any eval/sealed name. | `verdict.json` and the label list on standard output |

The reader refuses results written under other rules (`NO_VERDICT_FROZEN_RULES_DIFFER`) and a `prep.json` whose panels
do not recompute to the frozen digests (`NO_VERDICT_PREP_NOT_FROZEN`). It recomputes exactness from tokens,
teacher-forced counts from per-position bits, and edit counts from raw probabilities; a disagreement with the
runner's totals makes that run invalid.

**The exact output labels** (the reader's `LABELS` constant):
- job: `JOB_COMPLETE`, `JOB_STOPPED_<STOP_CODE>`, `JOB_FAILED`, `JOB_RESULT_MISSING`
- Stage 0: `STAGE0_REPRODUCED`, `STAGE0_NOT_REPRODUCED`, `STAGE0_MISSING`
- no verdict: `NO_VERDICT_STAGE0`, `NO_VERDICT_PREP_MISSING`, `NO_VERDICT_FROZEN_RULES_DIFFER`, `NO_VERDICT_PREP_NOT_FROZEN`
- run: `RUN_VALID`, `RUN_INCOMPLETE`, `RUN_INVALID_<REASON>`
- checkpoint: `INPUT_USE_DETECTED`, `INPUT_USE_NOT_DETECTED`
- calibration: `INPUT_USE_RULE_SILENT_AT_INITIALISATION`, `INPUT_USE_RULE_FIRES_AT_INITIALISATION`
- arm: `ARM_A_…` / `ARM_B_…`: `SHOWS_INPUT_USE`, `DOES_NOT_SHOW_INPUT_USE`, `INPUT_USE_UNDETERMINED`
- architecture: `ARCHITECTURE_CHANGE_JUSTIFIED`, `ARCHITECTURE_CHANGE_NOT_JUSTIFIED`, `ARCHITECTURE_DECISION_INCOMPLETE`, `ARCHITECTURE_NOT_EVALUATED`
- pair: `B_BEATS_A_<P>_PAIR<i>`, `A_BEATS_B_<P>_PAIR<i>`, `NO_PAIRED_DIFFERENCE_<P>_PAIR<i>`, `PAIR_INCOMPLETE_<P>_PAIR<i>`
- lessons: `LESSONS_HELP_<P>`, `LESSONS_HURT_<P>`, `LESSONS_EFFECT_NOT_SHOWN_<P>`, `LESSONS_COMPARISON_INCOMPLETE_<P>`, `LESSONS_NOT_EVALUATED_<P>`

with P in SP1, SP2U, SP2ALL and i in 1, 2, 3. Every verdict also carries `status: PROGRAM_READING_NOT_CERTIFIED` and the
label `CLAUDE_BUILT_CLAUDE_CHECKED`.

## 10. The B package and its pin (review A1; A3 as far as it touches A-C)

- **Separate data-build job** (`records/q4_sdg_1_20260923/data_build_job/`, one c7i.large CPU machine, no torch):
  build with `--expect-engine python` (the machines have no Rust engine), build again with another hash seed, compare
  every file byte for byte, re-verify with the pinned compiler, return digests and the manifest only.
- **Pin.** The coordinator runs `pin_package.py --write`. It refuses unless the two builds were byte-identical and
  verified, and the manifest's seeds, size and engine equal `q4_ab_rules.B_PACKAGE`. It writes ONE entry into
  `LAB/Q4_SDG_DATA_PINS.json`, with the engine, size, seeds, every file's sha256 and record count, and provenance.
- **The training job refuses** an unpinned package (launcher and runner) and a rebuilt package that differs from the
  pin (runner: manifest sha256, then `q4_sdg_curriculum.check_pin`, then every declared file hash). The runner rebuilds
  the package on the T4 machine from the same source; row files never travel through the laptop.
- **A3 (family D).** Family D is not used. This job writes no trigger file. None of its predictions or panel rows may
  ever be used as a family-D trigger. A3(a) touches A-C builds only in one way: a build that fails leaves
  `<out>.partial` behind; both jobs build into fresh folders on throwaway machines and never retry, so it cannot
  block them. A3(b)-(e) concern D rounds only and stay open.

## 11. Custody

- No `*_eval.jsonl`, no name containing `sealed`, `hset1a` or `hset1b` is bundled, opened by the runner or reader, or
  brought back to the laptop. Checked by name in the launchers (twice), on the machines, on the way out, and by the
  watchers.
- Every target is recompiled from visible text with the pinned compiler (`61ed5a45...`). The B package's own sidecar
  files are written by the build on the machines; the data-build machine's verify and digest steps read them there;
  the training runner never opens them.
- **The protected examination** (Q3 G eval, depths 4-5, visible and sealed) is not in any bundle and is in no loop.
  Using it needs a pre-registered arm and the owner's approval. This spec does not register one.

## 12. What this does not license

- A single job. Any label is a program reading of one job, `PROGRAM_READING_NOT_CERTIFIED`, `CLAUDE_BUILT_CLAUDE_CHECKED`.
- LESSONS_HELP is about these panels, this model and this budget. It is not "CAS SDG lessons help" in general, not
  a Helm result, and not general CAS reasoning.
- ARCHITECTURE_CHANGE_JUSTIFIED does not choose or start a change. The owner's go-ahead and a separate spec do.
- No claim about the protected examination.

## 13. Changes from v0.1 (`Q4_SDG_LESSONS_SPEC_v0_1.md`, kept unchanged)

- M1: frozen rules, seeds and thresholds; a program emits the labels.
- M2: panel 2 was the package dev split (favours B). Now SP1 and SP2 are shared G-distribution panels; B_DEV is
  B-internal only. P4: all 48 inspected dev rows are flagged; SP2U excludes them.
- Budget: 32,768 updates (v0.1 proposed 16,384; that point is kept as a checkpoint for comparison).
- A1: the engine is pinned (`python`) and the package is pinned from a separate, byte-checked build.
- Money: $5.00 ceiling from the owner's decision.
