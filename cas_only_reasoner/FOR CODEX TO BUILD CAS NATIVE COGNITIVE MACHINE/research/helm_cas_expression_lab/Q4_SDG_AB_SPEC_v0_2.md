# Q4-SDG-1 A-versus-B comparison, spec v0.2 (revision 3b)

**Status: PROPOSED_FOR_REVIEW** (revision 3b; not frozen; the launcher refuses it)

How this status was set, and what it binds:
- Revision 1 (commit `3771f989`) went to two independent reviews. They found one MAJOR defect and eight MINOR ones
  (`_handoffs/HELM_NEXT_PHASE_20260923/Q4_AB_REVIEW_20260924.md`). Revision 2 (commit `294471a5`) fixed them and was
  set to frozen, with rules hash `3100f376...`.
- A fresh verification of revision 2 (commit `fbcc279b`, same review file) returned **CHANGES_REQUIRED**: one MAJOR
  point (a shape-and-operator reader was still graded NONE), two MINOR points and one process note. So revision 2 is
  **not** the approved revision any more.
- Revision 3 applies the coordinator's five decisions of 2026-09-24, quoted word for word in section 15. It goes back
  to `PROPOSED_FOR_REVIEW`. It needs a new review.
- A fresh verification of revision 3 (commit `502a5704`, same review file) returned **CHANGES_REQUIRED** with one
  MINOR point, W1: a run whose FINAL checkpoint file exists but gives no reading was left out, so JUSTIFIED could still
  fire. **Revision 3a** fixes W1 and records the coordinator's confirmations of 2026-09-24 (section 16). It stays
  `PROPOSED_FOR_REVIEW`.
- A fresh review of revision 3a (commit `ae3c7ba2`, same review file) returned **CHANGES_REQUIRED** with one MINOR
  point, X1: a run whose checkpoint-0 file exists but gives no reading was left out of the calibration guard, which
  still printed SILENT, so both JUSTIFIED and NOT_JUSTIFIED could still be printed. **Revision 3b** applies the
  coordinator's two decisions of 2026-09-24 on that review, quoted word for word in section 17. It stays
  `PROPOSED_FOR_REVIEW`.
- The training launcher (`records/q4_sdg_1_20260923/ab_job/launch.py`) still holds revision 2's approved values
  (`APPROVED_FROZEN_SHA256` and `APPROVED_LF_SHA256`). Revision 3b's rules hash differs, and this status line is not
  the frozen one. So the launcher refuses revision 3b (`FROZEN_RULES_NOT_THE_APPROVED_ONES`). A test checks this.
- After a review approves revision 3b: set this line to the frozen form (`**Status: FROZEN_BEFORE_LAUNCH**` followed
  by the rules hash), then write the new approved values into `launch.py` in a commit of their own.

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
- The two reviews of revision 1 (`Q4_AB_REVIEW_20260924.md`): section 14 lists what changed because of them.
- The verification of revision 2 and the coordinator's decisions of 2026-09-24: section 15.
- The verification of revision 3 and the coordinator's confirmations of 2026-09-24: section 16.
- The fresh review of revision 3a and the coordinator's decisions of 2026-09-24 on it: section 17.

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
the untrained model; it calibrates the input-use tests (section 7.4). Checkpoint 128 is run_001's budget. Checkpoint
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
| Setup, panels, Stage 0, B rebuild, smoke (with one reload) | 13.5 min | 22.5 min |
| **Training machine** (g4dn.xlarge, $0.541959 per hour with address and disk) | **62 min, $0.56** | **143 min, $1.29** |
| Data-build machine (c7i.large, section 10) | about 10 min, $0.02 | $0.0813 at its deadline |

**Hard ceiling arithmetic.** Data build worst case $0.0813 + training worst case $2.1678 (240-minute client deadline)
= **$2.2491 <= $5.00**. Both launchers check it. The training launcher uses the data build's MEASURED cost bound from its
watch record. The smoke stage projects the time of all six runs (x 1.25) and stops the job (`PROJECTED_OVER_TIME`)
before any main run if the projection does not fit the runner's 190-minute limit or a run's 50-minute limit.

## 6. Shared panels (review M2)

| Panel | Rows | Definition | Role |
|---|---:|---|---|
| **SP1** `FAMILIAR_STRUCTURE_NEW_CONTENT` | 256 | Visible Q3 G train rows, reserved before any arm, never taught to either arm. Drawn only from rows the diagnostic never showed (its 48 inspected train rows are excluded). Allocated to the G-train shapes in proportion to their available rows (largest remainder; never more than half of a shape's rows, so every shape keeps rows for arm A). Within a shape: seeded shuffle (20260965) of the rows in file order; shapes in sorted key order. Digest `dab48792...` (`q4_ab_rules.SP1_DIGEST`). | shared; **primary** |
| **SP2U** `NEW_STRUCTURE_UNINSPECTED` | 208 | The visible G dev split (the 9 held-out depth-3 shapes) minus the 48 dev rows the diagnostic inspected (old_dev16 plus the 32 in public64; digest `d91d914b...`). SP2 as a whole: digest `00e55a80...` (`SP2_DIGEST`). | shared; **primary** |
| **SP2ALL** `NEW_STRUCTURE_ALL` | 256 | The whole visible G dev split, the 48 inspected rows included. | shared; labelled and reported |
| **B_DEV** | about 256 | The B package's own dev split. **B-internal**: drawn from B's own mixture, so it favours B. | reported only; never in a rule |
| **TEACH_FIT** | 64 | The first 64 rows of each run's own first epoch. | per run; reported; never in a rule (section 12) |
| **EDIT64** | 64 | SP1 rows 0, 4, 8, ...: 773 compilable one-field edits (196 noetic, 185 domain, 196 drive, 196 register; 11 domain fields have no compilable edit). Digest `05d62b99...`. Of the 773: **538 value edits** and **235 presence edits** (section 7.1; kinds digest `c276d894...`). | the edit-sensitivity measure |

The targets of SP1 and SP2 (ids, target tokens, slot kinds, in panel order) are pinned too: digest `ba04a4de...`
(`PANEL_TARGETS_DIGEST`). The reader judges exactness and recounts the SP1 field values only from these pinned targets.

**SP1 by shape** (rows): `(L L)` 95, `(L (L L))` 53, `((L L) L)` 26, `(L (L (L L)))` 24, `((L L) (L L))` 17,
`((L L) (L (L L)))` 16, `((L (L L)) L)` 6, `(L ((L L) (L L)))` 6, `((L L) ((L L) (L L)))` 5, and 1-2 rows each for five deep
shapes. Two G-train shapes have 0 rows here: they have only 4 and 2 rows in all of G train. Targets: 5,337 tokens,
799 noetic positions. Measured: 44 distinct (shape, operators) classes and 180 distinct (shape, operators,
field-presence) classes.

**Exclusion, both ways.**
- Arm A's pool is G train minus the 256 SP1 rows (digest `9064635d...`, 1,792 rows). No arm-A row has the tree of any
  SP1 or SP2 row.
- Arm B's pool drops every package row whose tree (content sha256) equals an SP1 or SP2 row. The count dropped is
  written in `prep.json`. The package already excludes G-dev shapes and every Q3 dev text.
- The panels are fixed before any arm runs: every digest above was measured on the laptop from visible files only,
  with the pure-Python compiler engine, and the machine must reproduce all of them before any GPU work
  (`q4_ab_rules.MEASURED_DIGEST_KEYS`).

**Which arm do the shared panels favour?** Both are drawn from the family-G distribution, which is arm A's own
teaching distribution. B meets these shapes in its family-C "mixed allowed shapes" lessons (15% of its pool) and
single-depth shapes in family B. So if either arm is favoured, it is A, the control. A B win on SP1 or SP2U is
therefore not a panel artefact. A B loss may be partly distribution shift; that is reported, not relabelled.

**Near twins (review A2), disclosed, not decisive.** Every SP1/SP2 row carries its smallest token distance to each
arm's pool. Against arm A: 6 of the 512 rows are one token away from a teaching row (measured). The reader reports
every pair comparison again without rows at distance 0 or 1 from either arm.

**A panel the directive asks for is missing, on purpose.** Directive section 8 names four panels. The fourth is
"Longer or deeper expressions than those taught". It is not built. The only visible rows of that kind are the protected
Q3 G eval (depths 4 and 5), which no loop may touch; using them needs a pre-registered arm and the owner's approval.
So this comparison says nothing about longer or deeper expressions.

## 7. Decision rules (review M1)

A program, `read_q4_ab_results.py`, emits every label below from the result files. It calls the decision functions in
`q4_ab_rules.py` (`input_use_level`, `calibration_guard_fires`, `calibration_state`, `arm_decision` and its
`arm_label`, `architecture_decision`, `fields_not_read_in_any_run`, `overall_lessons`). No person chooses a label.

### 7.1 The four input-use tests (one run, one checkpoint)

**T1: Noetic accuracy above what an input-blind model can reach.**
- Measure: teacher-forced (correct previous tokens), grammar-masked choices at every **noetic** position of SP1
  (799 positions). k = correct choices.
- Null rate p0 = the larger of (a) the most frequent noetic value's share in **that arm's teaching pool** and (b) its
  share among the SP1 targets. Both are frozen where they can be: SP1 **90/799** (`SP1_NOETIC_NULL`), arm A's pool
  **605/5,671** (`A_POOL_NOETIC_NULL`). For arm A, p0 = 90/799 = 0.1126. Arm B's pool rate comes from the pinned
  package, is written in `prep.json`, and can only raise p0 above 90/799.
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

**The two kinds of one-field edit.** Each EDIT64 edit changes one field of one leaf. It is a **presence edit** when it
adds or removes an optional drive or register (the input text gets longer or shorter). It is a **value edit**
otherwise (a value changes in place; the input length stays the same). Rule: presence iff the field is drive or
register and "None" is the old or the new value. Measured on the frozen panel, this rule and the input-length rule
agree on all 773 edits.
- Value edits: **538** (noetic 196, domain 185, drive 88, register 69).
- Presence edits: **235** (drive 108, register 127). Their new tokens: F1 95, REG_T 102, REG_ABSENT 25, F_NONE 13.
Reading a presence edit needs only the input's length or layout, not any field value.

For every edit: delta = p(new token | edited input) - p(new token | original input), with the correct previous tokens
held fixed, full-vocabulary softmax. A rise is delta >= **0.01**; a fall is delta <= -0.01. Why 0.01: the saved model's
largest move over 1,812 edits was 3.6378e-06 (noetic), every median 0.0. 0.01 is about 2,700 times that noise floor.

**T2V: field-value reading (value edits only, 538).**
- Pass iff rises u >= **1/10** of 538 (**54**) AND the exact one-sided sign test P(X >= u | u + d, 1/2) <= **1/100**
  (d = falls).
- Why: a model that reads even one field's values well moves many of that field's edits toward the new token. The sign
  test needs the moves to go TOWARD the new token, which an untrained model's random input dependence does not do.
- Per-field value-edit results are reported, not decisive.

**T2P: presence reading (presence edits only, 235).** The same test on the 235 presence edits (**24** rises needed).
It shows that the model reads something of its input, but not a field value.

T2 over all 773 edits (revision 1's T2) is reported and never decisive. Measured: a structure-only model passes it.

**T3: free generation has not collapsed.**
- Measure: distinct free-decoded token sequences over the 256 SP1 rows. Pass iff at least **32**.
- What it shows: only that free generation depends on the input and is not one fixed output. The saved model produced
  1 distinct output for 96 inputs.
- What it does NOT show: field-value reading. A model that reads only shape, operators and field presence can reach
  **180** distinct outputs on SP1 (measured). So T3 never counts as field-value reading. It separates FULL from
  TEACHER_FORCED_ONLY.

**The distinct-output count D also decides NONE** (coordinator decision 1 of 2026-09-24, section 15). D = the number of
distinct free-decoded token sequences over the 256 SP1 rows (the same count T3 uses). Free decoding is greedy, so it is
deterministic: D >= 2 means the output depends on the input. **NONE needs D = 1 exactly** (total collapse). Any run
with D >= 2 is not NONE, whatever T3 says. Measured on fakes (section 7.2): a shape-and-operator reader gives D = 44
(T3 passes), a shape-only reader gives D = 14 (T3 fails); neither is NONE.

Reported with every reading, never decisive: the summary cosine between SP1 partners of the same shape (the saved
model: minimum 0.9966), the masked choice changes under edits, first-wrong-decision kinds, outcomes and mean lengths.

### 7.2 The input-use level (one run, one checkpoint)

Checked in this order. D = distinct free outputs over the 256 SP1 rows. Every combination of T1, T2V, T2P and D has
exactly one level. A test checks all 40 combinations (2 x 2 x 2 x 5 values of D: 1, 2, 31, 32, 256).

| Level | Condition | In plain words |
|---|---|---|
| **FULL** | T1 and T2V and T3 | reads field values, and free generation uses them |
| **TEACHER_FORCED_ONLY** | (T1 or T2V) and not T3 | reads field values with the correct previous tokens, but free generation collapses |
| **PARTIAL_FIELDS** | T3 and exactly one of T1, T2V | reads some field values (for example domain, drive and register, not the Noetic) |
| **STRUCTURE_OR_OUTPUT_VARIATION** | not T1, not T2V, and (T2P or D >= 2) | reads no field value, but reads drive/register presence, or its free output changes with the input (for example with the tree's shape or operators) |
| **NONE** | not T1, not T2V, not T2P, and D = 1 | total collapse: no input reading detected, and one fixed free output for all 256 rows |

T1 or T2V passes exactly in the first three levels (the "field levels").

`STRUCTURE_OR_OUTPUT_VARIATION` replaces revision 2's `STRUCTURE_ONLY`. The coordinator's definition ("2 or more
distinct free outputs, or T2P passes, while T1 and T2V fail") contains every STRUCTURE_ONLY case. Which of the two
parts fired is in the reading (T2P, and D with `output_varies`).

Measured on the runner's own `evaluate()` with pure-Python fakes (NOT Q4; each value is asserted by a test):

| Fake model | T1 (of 799) | T2V (538 value edits) | T2P (235 presence edits) | D (of 256) | Level |
|---|---:|---|---|---:|---|
| blind | 88 (fails) | fails | fails | 1 | NONE |
| reader | 799 | 538 up, 0 down | 235 up | 256 | FULL |
| tf_reader_freegen_collapse | 799 | passes | - | 1 | TEACHER_FORCED_ONLY |
| no_noetic | 88 (fails) | 342 up (passes) | - | passes T3 | PARTIAL_FIELDS |
| structure_only | 88 (fails) | 0 up (fails) | 235 up, 0 down | 180 | STRUCTURE_OR_OUTPUT_VARIATION |
| shape_operators_only (verification V1) | 88 (fails) | 0 up, 0 down | 0 up, 0 down | 44 (T3 passes) | STRUCTURE_OR_OUTPUT_VARIATION |
| shape_only (verification V2) | 88 (fails) | 0 up, 0 down | 0 up, 0 down | 14 (T3 fails) | STRUCTURE_OR_OUTPUT_VARIATION |

Revision 2 graded the last two NONE.

Labels: `INPUT_USE_FULL`, `INPUT_USE_TEACHER_FORCED_ONLY`, `INPUT_USE_PARTIAL_FIELDS`,
`INPUT_USE_STRUCTURE_OR_OUTPUT_VARIATION`, `INPUT_USE_NONE`.

### 7.3 Arms

For each arm, over its 3 seeds, at the FINAL checkpoint. A run "has a FINAL reading" when its run manifest and its
final checkpoint file exist and the file agrees with the reader's recomputation, whether or not the run is valid
(section 7.7).
- **ARM_<arm>_SHOWS_INPUT_USE** iff at least **2** VALID runs are FULL (unchanged).
- **ARM_<arm>_SHOWS_NO_INPUT_USE** iff at least **2** VALID runs are NONE, AND every run of the arm that has a FINAL
  reading, valid or not, is NONE, AND no run of the arm has a FINAL checkpoint file without a FINAL reading
  (revision 3b).
- **ARM_<arm>_INPUT_USE_UNDETERMINED** otherwise.

A run with no FINAL reading gives no level to the arm. If that run's FINAL checkpoint file EXISTS (it was written, but
the reader could not take a reading from it), two rules hold it back:
- **The arm label** (revision 3b; coordinator decision 2 of 2026-09-24, section 17). If the arm would otherwise be
  SHOWS_NO_INPUT_USE, that label is withheld: the arm is **ARM_<arm>_INPUT_USE_UNDETERMINED**, with the named reason
  `FINAL_CHECKPOINT_PRESENT_WITHOUT_READING`, also emitted as
  `ARM_<arm>_INPUT_USE_UNDETERMINED_BECAUSE_FINAL_CHECKPOINT_PRESENT_WITHOUT_READING`. The verdict carries it in
  `arms.<arm>.label_reasons`. The reason is named only when it changed the label.
- **The architecture label** withholds JUSTIFIED (section 7.5, reason `FINAL_CHECKPOINT_PRESENT_WITHOUT_READING`).

**SHOWS_INPUT_USE is not withheld for such a file.** Decision 2 also says "The same for any other arm-level label that
3a's unread-FINAL rule does not already cover". The only other decisive arm label is SHOWS_INPUT_USE. An unread FINAL
file cannot make it false: SHOWS_INPUT_USE counts VALID FULL runs only, and a run whose FINAL file gives no reading is
never valid (it is RUN_INCOMPLETE or RUN_INVALID_<reason>, section 7.7). Whatever that file held, the two valid FULL
runs still stand. A test fills the unread run with every possible invalid reading and the label stays. So there is no
gap to close there, and withholding it would make NOT_JUSTIFIED rarer, which decision 2 does not ask for. (The builder's
reading of that sentence; it is an open question in the builder report.) INPUT_USE_UNDETERMINED claims nothing, so
there is nothing to withhold.

The verdict lists such runs per arm (`final_checkpoints_present_without_reading`). The architecture label is the
decision; with revision 3b an arm label no longer says SHOWS_NO_INPUT_USE while one of its FINAL files is unread.

### 7.4 Calibration guard

The guard uses **T1, T2V and T2P only** (coordinator decision 5 of 2026-09-24). If any run passes T1, T2V or T2P at
checkpoint 0 (untrained), the tests are not trustworthy on this machine: **INPUT_USE_RULE_FIRES_AT_INITIALISATION**,
and the architecture label is ARCHITECTURE_DECISION_INCOMPLETE. Otherwise **INPUT_USE_RULE_SILENT_AT_INITIALISATION**.

**The calibration state has three values** (revision 3b; coordinator decision 1 of 2026-09-24, section 17). The guard
can only look at runs whose checkpoint-0 file gave a reading. So the reader first lists every run whose checkpoint-0
file EXISTS but gives no checkpoint-0 reading (a path check, as for the FINAL file in 3a). Causes: the run manifest is
missing; the file names another rules hash or another checkpoint; the file holds no record (JSON `null`); or any
recomputation in it fails, including an exact-flag check on SP1, SP2, B_DEV or TEACH_FIT. Then, in this order:
1. **CALIBRATION_UNREADABLE** if there is at least one such run, whatever the readable runs show. The architecture
   label is then ARCHITECTURE_DECISION_INCOMPLETE with the one reason `CHECKPOINT0_PRESENT_WITHOUT_READING`.
2. **INPUT_USE_RULE_FIRES_AT_INITIALISATION** if a run with a checkpoint-0 reading passes T1, T2V or T2P.
3. **INPUT_USE_RULE_SILENT_AT_INITIALISATION** otherwise.

Why the third value comes first, even when a readable run fires: decision 1 says the state is the third value "instead
of silent or fired" whenever such a run exists. The label then says plainly that some starting file could not be read.
The verdict still reports what the readable runs showed, in `calibration_guard_fires_over_readable_runs` (report only,
never decisive), and lists the unread runs in `checkpoint_0_files_present_without_reading`. Both roads lead to
INCOMPLETE, so this order changes no decisive label.

A checkpoint-0 file that does NOT exist is not flagged (the path check). Its run is left out of the guard, as before.
A checkpoint-0 file that holds neither a JSON object nor JSON `null` still stops the whole reader, as before.

D and T3 are not in the guard. An untrained model's free outputs may vary with the input, so its level at checkpoint 0
may be STRUCTURE_OR_OUTPUT_VARIATION; that does not fire the guard. (In revision 2 the guard was "the level at
checkpoint 0 is not NONE", which then meant exactly "T1, T2V or T2P passes"; the test is the same.)

**Reported for every run:** its checkpoint-0 distinct-output count D (`checkpoint_0_distinct_free_outputs`; null for a
run with no checkpoint-0 reading), and its checkpoint-0 T1, T2V, T2P and level (`calibration_checkpoint_0`). A FINAL D
can then be compared with the same run's untrained D. Each run also carries `checkpoint_0_file_present` and
`checkpoint_0_present_without_reading`.

### 7.5 The architecture label

In this order:
0. The calibration state is CALIBRATION_UNREADABLE (section 7.4): **ARCHITECTURE_DECISION_INCOMPLETE**, with the one
   reason CHECKPOINT0_PRESENT_WITHOUT_READING (revision 3b; coordinator decision 1, section 17).
1. The calibration guard fires: **ARCHITECTURE_DECISION_INCOMPLETE**, reason INPUT_USE_RULE_FIRES_AT_INITIALISATION.
2. Some arm SHOWS_INPUT_USE: **ARCHITECTURE_CHANGE_NOT_JUSTIFIED_BY_INPUT_USE_RULE**.
3. Both arms SHOW_NO_INPUT_USE, and no run has a FINAL checkpoint file without a FINAL reading:
   **ARCHITECTURE_CHANGE_JUSTIFIED**. That is: the calibration state is SILENT (every checkpoint-0 file that exists
   gave a reading, and none passes T1, T2V or T2P); every run that has a FINAL reading (valid or not) is NONE; each arm
   has at least 2 VALID NONE runs (coordinator decision 3); and every FINAL checkpoint file that exists gave a reading
   (verification of revision 3, W1).
4. Otherwise **ARCHITECTURE_DECISION_INCOMPLETE** (the verdict is withheld), with every reason that applies, each also
   emitted as `ARCHITECTURE_INCOMPLETE_BECAUSE_<REASON>`:
   - `TEACHER_FORCED_ONLY`, `PARTIAL_FIELDS`, `STRUCTURE_OR_OUTPUT_VARIATION`: a run with a FINAL reading (valid or
     not) has that level;
   - `SEED_DEPENDENT`: a run with a FINAL reading (valid or not) is FULL, but no arm has 2 valid FULL runs;
   - `NOT_NONE_IN_A_RUN_THAT_IS_NOT_VALID`: a run that is not valid has a FINAL reading other than NONE;
   - `TOO_FEW_VALID_RUNS`: an arm has fewer than 2 valid runs;
   - `FINAL_CHECKPOINT_PRESENT_WITHOUT_READING`: a run's FINAL checkpoint file exists, but the reader took no FINAL
     reading from it. Causes: the run manifest is missing; the file names another rules hash or another checkpoint;
     the file holds no record (for example JSON `null`); or any recomputation in it fails, including an exact-flag
     check on SP1, SP2, B_DEV or TEACH_FIT. Listed last.

   Steps 2 and 3 run only when the calibration state is SILENT. In steps 0 and 1 the calibration reason stands alone
   (coordinator confirmation (d) for the guard; the same shape for the third state):
   - `CHECKPOINT0_PRESENT_WITHOUT_READING`: a run's checkpoint-0 file exists, but the reader took no checkpoint-0
     reading from it (section 7.4). The calibration state is CALIBRATION_UNREADABLE.

   Every INCOMPLETE carries at least one reason (a test enumerates every arm of 0 to 3 readings).

**Why an unread FINAL checkpoint withholds JUSTIFIED** (verification of revision 3, W1). The run trained to the end
and wrote its final file, but the reader could not take a reading from it. Nothing then shows that the run is NONE.
It may have read its input fully (the verifier measured three such cases, each giving JUSTIFIED under revision 3). A
failed check does not undo what the run read; a wrong exact flag on a teaching row does not either. So such a run
cannot count toward "neither arm shows input use". It changes nothing else:
- ARCHITECTURE_CHANGE_NOT_JUSTIFIED_BY_INPUT_USE_RULE is unchanged. Two valid FULL runs in one arm are not undone by
  another run's unreadable file.
- The calibration guard is unchanged. When it fires, it stays the only reason (coordinator confirmation (d),
  section 16).
- A run whose FINAL checkpoint file does NOT exist is left out, as before (it cannot have been read by anyone).
- A FINAL file that holds neither a JSON object nor JSON `null` (invalid JSON, duplicate keys, a non-finite number, a
  list) still stops the whole reader with an error, as before: no verdict and no label at all. A test checks this.

So the rule can only make JUSTIFIED rarer. A test checks every pair of the 286 distinct arms with 0, 1, 2 and 6 such
runs: the 9 JUSTIFIED pairs become INCOMPLETE [FINAL_CHECKPOINT_PRESENT_WITHOUT_READING]; every other INCOMPLETE gains
that reason last; NOT_JUSTIFIED is unchanged.

**Why an unread checkpoint-0 file withholds both decisive labels** (review of revision 3a, X1; coordinator decision 1).
The calibration guard exists to stop both JUSTIFIED and NOT_JUSTIFIED when the tests are not trustworthy at the start.
A starting file that exists but cannot be read may have fired the guard. The reviewer measured it: with both starting
files of one seed pair unread, revision 3a printed SILENT and then JUSTIFIED (case G1), or SILENT and NOT_JUSTIFIED
(case G3); with those files readable, the guard fired. So such a file makes the calibration state CALIBRATION_UNREADABLE,
and the architecture label is INCOMPLETE. The decision says this "must only make both JUSTIFIED and NOT_JUSTIFIED
rarer, never more common". A test checks it over every pair of the 286 distinct arms, under a silent or a firing
guard, with 0 or 1 unread FINAL files: every pair becomes INCOMPLETE [CHECKPOINT0_PRESENT_WITHOUT_READING]. That moves
the 9 JUSTIFIED pairs (with 0 unread FINAL files) and the 6,171 NOT_JUSTIFIED pairs (with 0 and again with 1 unread
FINAL file); nothing becomes JUSTIFIED or NOT_JUSTIFIED. With no such file, the rule is revision 3a's rule exactly.

**ARCHITECTURE_NOT_EVALUATED** when there is no verdict at all (section 8).

**How decision 3 is read, and why.** "Every run that has a FINAL reading (valid or invalid) is NONE in at least 2 of its
arm's 3 seeds" is read as two conditions: (a) every FINAL reading, valid or not, is NONE; and (b) each arm has at least
2 VALID NONE runs. Condition (b) counts valid runs only, because the decision says JUSTIFIED "can only become rarer".
Revision 2 required at least 2 valid runs per arm. Counting an invalid NONE run toward the 2 would let JUSTIFIED fire
where revision 2 gave TOO_FEW_VALID_RUNS. A test enumerates 3,375 arms and checks that every arm that shows no input
use under revision 3 also did under revision 2. It also checks three revision-2 JUSTIFIED arms that revision 3
withholds: D = 44, D = 14, and an invalid FULL run (the verification's V1, V2 and V3).

Why this shape (review of revision 1, MAJOR, and the verification of revision 2). The owner's decision says: "If
neither arm shows input use at the final checkpoint, an architecture change is justified." A run that reads its input
only partly, or only with the correct previous tokens, or only its structure, does show input use. So does a run whose
free output changes with its input (the verification of revision 2 reports that the owner's decision names distinct
outputs as an input-use measure; the builder did not re-read that document for revision 3). Directive
section 3 also says that when behaviour differs with correct previous tokens, one should "investigate that
training/generation difference rather than blaming capacity alone". So JUSTIFIED needs total collapse in every run
that has a FINAL reading. A single fully reading run, valid or not, already shows the architecture can carry the input,
so it blocks JUSTIFIED too (SEED_DEPENDENT; for an invalid run also NOT_NONE_IN_A_RUN_THAT_IS_NOT_VALID).

What the labels mean, and do not mean:
- "Justified" means only what the owner's decision says: an architecture change may then be designed as a separately
  named, reviewed arm. The rule does not choose the change and does not start it.
- "Not justified by the input-use rule" is named by its scope. The rule does not test teaching fit (section 12).
- "Incomplete" hands the question back to the owner with the named reasons and the full readings.

### 7.6 Lessons: B versus A

Per panel P in SP1, SP2U, SP2ALL. For seed pair i (A and B on the same seed), at the FINAL checkpoint, on exact
canonical trees (the free-decoded tokens equal the target tokens, EOS included, outcome GENERATED), row by row:
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

**The one answer to "did the lessons help?"** (review of revision 1, MINOR 2). The primary panels are **SP1 and SP2U**.
`LESSONS_OVERALL_<X>`, in this order:
- NOT_EVALUATED if either primary panel is not evaluated;
- COMPARISON_INCOMPLETE if either is incomplete;
- **MIXED** if one is HELP and the other is HURT;
- **HURT** if either is HURT;
- **HELP** only if both are HELP;
- EFFECT_NOT_SHOWN otherwise.

SP2ALL keeps its own label and never enters the overall answer. B_DEV is reported for both arms and labelled
B-internal; it enters no rule.

### 7.7 Run validity

**RUN_VALID** iff: the run manifest, all 7 checkpoint files, the run result (status COMPLETE, 32,768 updates) and a
reload check with status RELOAD_REPRODUCED are present; every file carries the frozen-rules hash; and the runner's own
totals agree with the reader's recomputation (exact flags, teacher-forced counts, distinct outputs, exactly 773 edit
values in the frozen edit order, 538 value and 235 presence edits). A missing file gives **RUN_INCOMPLETE**. Anything
else gives **RUN_INVALID_<reason>**.

A run that is not valid still counts in the architecture rule when it has a FINAL reading (section 7.3, 7.5). It
never counts in a pair comparison (section 7.6), and never toward the 2 valid FULL or the 2 valid NONE runs of an arm.
A run whose FINAL checkpoint file exists but gave no FINAL reading (it is then RUN_INCOMPLETE or RUN_INVALID_<reason>)
withholds JUSTIFIED (section 7.5, `FINAL_CHECKPOINT_PRESENT_WITHOUT_READING`) and its arm's SHOWS_NO_INPUT_USE (section
7.3). A run whose checkpoint-0 file exists but gave no checkpoint-0 reading (again never valid) makes the calibration
state CALIBRATION_UNREADABLE (section 7.4). Each run in the verdict carries `final_checkpoint_file_present`,
`final_checkpoint_present_without_reading`, `checkpoint_0_file_present` and `checkpoint_0_present_without_reading`.

### 7.8 Information-only label (coordinator decision 4 of 2026-09-24)

**FIELDS_NOT_READ_IN_ANY_RUN** is emitted iff at least one run has a FINAL reading, and no run with a FINAL reading
(valid or not) passes T1 or T2V at the FINAL checkpoint. (With no FINAL reading at all there is nothing to say, so the
label is not emitted.)
- It is **information only**. It justifies nothing by itself. It changes no other label.
- It names the target for a later, separately approved design discussion: getting field values into the output.
- It can appear next to any architecture label. Examples: six input-blind runs give ARCHITECTURE_CHANGE_JUSTIFIED and
  this label; six shape-only runs give ARCHITECTURE_DECISION_INCOMPLETE [STRUCTURE_OR_OUTPUT_VARIATION] and this label.
- **Scope** (revision 3a): it speaks only about runs with a FINAL reading. A run whose FINAL checkpoint file exists but
  gave no reading is NOT covered by it. Such runs are listed beside it, in the verdict's `information` block
  (`final_checkpoints_present_without_reading`). The rule itself is unchanged, as the coordinator confirmed
  (confirmation (c), section 16).

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
| `PANEL_DIGEST_MISMATCH` | any panel, the panel targets, the edit list, the edit kinds, arm A's pool or a frozen null rate differs from its frozen value |
| `B_PACKAGE_NOT_PINNED` | `Q4_SDG_DATA_PINS.json` has no entry for the package |
| `B_PIN_NOT_THE_FROZEN_PACKAGE` | the pin names another engine, size, seed or folder |
| `B_PACKAGE_BUILD_FAILED` | the rebuild on the machine fails |
| `B_PACKAGE_MISMATCH` | the rebuilt package differs from the pin |
| `STAGE0_NOT_REPRODUCED`, `REINIT_NOT_REPRODUCED` | see above |
| `SMOKE_NONDETERMINISTIC` | two identical 64-update smoke runs differ in any weight or output |
| `SMOKE_PAIR_INIT_MISMATCH` | arm A and arm B do not start from the same tensors |
| `SMOKE_RELOAD_FAILED` | the fresh-process reload of smoke run A_first does not report RELOAD_REPRODUCED (the same path every main run uses; checked before any main run) |
| `SMOKE_FAILED` | reserved for a smoke failure without a more specific code |
| `PROJECTED_OVER_TIME` | the smoke projection (x 1.25) exceeds the time left or a run's 3,000 s |
| `NUMERICAL_FAILURE` | a non-finite loss or gradient |
| `RUN_WALL_LIMIT`, `JOB_WALL_LIMIT` | a run exceeds 3,000 s, or the runner exceeds 11,400 s |

Outside the runner: the in-machine timer (225 min), the shutdown (228 min) and the watcher's client deadline
(240 min) end the machine whatever happens. Before the machine exists, the launcher refuses a source commit whose
rules, programs or spec are not the approved ones, and a B package whose builder sources changed since the pinned data
build (section 10).

## 9. Reading rule

| Program | Reads | Writes |
|---|---|---|
| `q4_ab_train.py` (T4 machine) | visible Q3 v0.7 files, run_001's records and weights, the B package's visible files and manifest, `Q4_SDG_DATA_PINS.json` | `out/ab/`: `gates.json`, `stage0.json`, `prep.json`, `smoke/`, `smoke_summary.json`, `runs/<arm>_<seed>/{run_manifest.json, checkpoint_<NNNNN>.json, updates.json, run_result.json, checkpoint/, reload_check.json, reload.log}`, `job_result.json`, `STOP.json` (all create-only) |
| `read_q4_ab_results.py` (laptop, and once on the machine) | ONLY `job_result.json`, `STOP.json`, `stage0.json`, `prep.json` and `runs/*/{run_manifest.json, checkpoint_*.json, run_result.json, reload_check.json}`. Never `smoke/`, data, weights, or any eval/sealed name. | `verdict.json` and the label list on standard output |

The reader refuses results written under other rules (`NO_VERDICT_FROZEN_RULES_DIFFER`). It refuses a `prep.json` that
fails any check against the frozen record (`NO_VERDICT_PREP_NOT_FROZEN`, with the failing checks listed): the SP1 and
SP2 digests, the pinned panel targets, the inspected-row flags, arm A's pool, the edit list, the edit kinds (recomputed
from each edit's old and new values), the edit count, the SP1 field counts (recounted from the pinned targets), both
frozen null rates, and well-formed pool counts. It recomputes exactness from tokens, teacher-forced counts from
per-position bits, and every edit move from raw probabilities, edit by edit (each edit value carries its row and
position, and must follow `prep.json`'s edit order). A disagreement with the runner's totals makes that run invalid.
The verdict records the LF sha256 of the reader and of the rules module it ran with.

**The exact output labels** (the reader's `LABELS` constant):
- job: `JOB_COMPLETE`, `JOB_STOPPED_<STOP_CODE>`, `JOB_FAILED`, `JOB_RESULT_MISSING`
- Stage 0: `STAGE0_REPRODUCED`, `STAGE0_NOT_REPRODUCED`, `STAGE0_MISSING`
- no verdict: `NO_VERDICT_STAGE0`, `NO_VERDICT_PREP_MISSING`, `NO_VERDICT_FROZEN_RULES_DIFFER`, `NO_VERDICT_PREP_NOT_FROZEN`
- run: `RUN_VALID`, `RUN_INCOMPLETE`, `RUN_INVALID_<REASON>`
- checkpoint: `INPUT_USE_FULL`, `INPUT_USE_TEACHER_FORCED_ONLY`, `INPUT_USE_PARTIAL_FIELDS`, `INPUT_USE_STRUCTURE_OR_OUTPUT_VARIATION`, `INPUT_USE_NONE`
- calibration: `INPUT_USE_RULE_SILENT_AT_INITIALISATION`, `INPUT_USE_RULE_FIRES_AT_INITIALISATION`, `CALIBRATION_UNREADABLE`
- arm: `ARM_A_…` / `ARM_B_…`: `SHOWS_INPUT_USE`, `SHOWS_NO_INPUT_USE`, `INPUT_USE_UNDETERMINED`
- arm reason: `ARM_A_…` / `ARM_B_…`: `INPUT_USE_UNDETERMINED_BECAUSE_FINAL_CHECKPOINT_PRESENT_WITHOUT_READING`
- architecture: `ARCHITECTURE_CHANGE_JUSTIFIED`, `ARCHITECTURE_CHANGE_NOT_JUSTIFIED_BY_INPUT_USE_RULE`, `ARCHITECTURE_DECISION_INCOMPLETE`, `ARCHITECTURE_NOT_EVALUATED`
- architecture reasons: `ARCHITECTURE_INCOMPLETE_BECAUSE_` + one of `INPUT_USE_RULE_FIRES_AT_INITIALISATION`, `CHECKPOINT0_PRESENT_WITHOUT_READING`, `TEACHER_FORCED_ONLY`, `PARTIAL_FIELDS`, `STRUCTURE_OR_OUTPUT_VARIATION`, `SEED_DEPENDENT`, `NOT_NONE_IN_A_RUN_THAT_IS_NOT_VALID`, `TOO_FEW_VALID_RUNS`, `FINAL_CHECKPOINT_PRESENT_WITHOUT_READING`
- information only (section 7.8): `FIELDS_NOT_READ_IN_ANY_RUN`
- pair: `B_BEATS_A_<P>_PAIR<i>`, `A_BEATS_B_<P>_PAIR<i>`, `NO_PAIRED_DIFFERENCE_<P>_PAIR<i>`, `PAIR_INCOMPLETE_<P>_PAIR<i>`
- lessons: `LESSONS_HELP_<P>`, `LESSONS_HURT_<P>`, `LESSONS_EFFECT_NOT_SHOWN_<P>`, `LESSONS_COMPARISON_INCOMPLETE_<P>`, `LESSONS_NOT_EVALUATED_<P>`
- overall: `LESSONS_OVERALL_HELP`, `LESSONS_OVERALL_HURT`, `LESSONS_OVERALL_MIXED`, `LESSONS_OVERALL_EFFECT_NOT_SHOWN`, `LESSONS_OVERALL_COMPARISON_INCOMPLETE`, `LESSONS_OVERALL_NOT_EVALUATED`

with P in SP1, SP2U, SP2ALL and i in 1, 2, 3. Every verdict also carries `status: PROGRAM_READING_NOT_CERTIFIED` and the
label `CLAUDE_BUILT_CLAUDE_CHECKED`.

## 10. The B package and its pin (review A1; A3 as far as it touches A-C)

- **Separate data-build job** (`records/q4_sdg_1_20260923/data_build_job/`, one c7i.large CPU machine, no torch):
  build with `--expect-engine python` (the machines have no Rust engine), build again with another hash seed, compare
  every file byte for byte, re-verify with the pinned compiler, return digests and the manifest only.
- **Pin.** The coordinator runs `pin_package.py --write`. It refuses unless the two builds were byte-identical and
  verified, and the manifest's seeds, size and engine equal `q4_ab_rules.B_PACKAGE`. It writes ONE entry into
  `LAB/Q4_SDG_DATA_PINS.json`, with the engine, size, seeds, every file's sha256 and record count, and provenance. The
  same commit must add the data build's `results/manifest.json`.
- **The training job refuses** an unpinned package (launcher and runner) and a rebuilt package that differs from the
  pin (runner: manifest sha256, then `q4_sdg_curriculum.check_pin`, then every declared file hash). The runner rebuilds
  the package on the T4 machine from the same source; row files never travel through the laptop.
- **Refused at $0 before launch** (review of revision 1, MINOR 6): the launcher reads the committed data-build manifest
  at the source commit. It must hash to the pin, and every source hash it recorded (`sources_lf_sha256`: the package
  builder and its imports; the compiler snapshot; the Q3 files) must equal the same file at the source commit
  (`B_PACKAGE_SOURCES_CHANGED_SINCE_THE_DATA_BUILD`). So `q4_sdg_curriculum.py` stays unchanged from the data build
  until the training job ends.
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
- FIELDS_NOT_READ_IN_ANY_RUN justifies nothing (section 7.8). It only names a target for a later, separately
  approved design discussion.
- **Teaching fit is not tested** (review of revision 1, MINOR 5). Directive section 9 names two triggers for an
  architecture change: failing "to fit small teaching sets" or to "use input distinctions". The owner's decision
  names only input use, so the rule tests only that. TEACH_FIT is reported per run and never compared. A run that
  passes the input-use tests but fits none of its 64 teaching rows still gives
  ARCHITECTURE_CHANGE_NOT_JUSTIFIED_BY_INPUT_USE_RULE, and the label says so by its name. Adding a teaching-fit floor
  would be a new criterion; that is the owner's choice (open question in the review record).
- **No claim about longer or deeper expressions** (section 6: directive section 8's fourth panel is not built).
- No claim about the protected examination.

## 13. Changes from v0.1 (`Q4_SDG_LESSONS_SPEC_v0_1.md`, kept unchanged)

- M1: frozen rules, seeds and thresholds; a program emits the labels.
- M2: panel 2 was the package dev split (favours B). Now SP1 and SP2 are shared G-distribution panels; B_DEV is
  B-internal only. P4: all 48 inspected dev rows are flagged; SP2U excludes them.
- Budget: 32,768 updates (v0.1 proposed 16,384; that point is kept as a checkpoint for comparison).
- A1: the engine is pinned (`python`) and the package is pinned from a separate, byte-checked build.
- Money: $5.00 ceiling from the owner's decision.

## 14. Changes in revision 2 (after the two reviews of `3771f989`)

History. This table describes revision 2. Revision 3 changes the levels, the arm rule and the architecture rule again
(section 15); where the two differ, section 7 and section 15 are current.

| Review finding | Change |
|---|---|
| MAJOR: JUSTIFIED could fire for a model that reads its input | Five input-use levels (7.2); JUSTIFIED only when every valid run of both arms is NONE with 2 or more valid runs per arm; otherwise INCOMPLETE with named reasons (7.5); tests with the reviewers' two fakes and a structure-only fake |
| MINOR 1: T2 and T3 did not test what the text said | T2V on the 538 value edits (54 rises) decides; T2P on the 235 presence edits defines STRUCTURE_ONLY; T2 on all edits is reported only; T3 restated as a collapse test (7.1) |
| MINOR 2: no single answer to "did the lessons help?" | SP1 and SP2U are the primary panels; one LESSONS_OVERALL label (7.6) |
| MINOR 3: the freeze was not tied to the reviewed rules | The status line carries the frozen_sha256; the launcher refuses other rules, and other bytes of the four decision programs or this spec |
| MINOR 4: the reader trusted prep.json values | Frozen SP1 and arm-A null rates, SP2 and panel-target digests, edit-kind digest; the reader recounts SP1 field values and requires 773 edit values in the frozen order (9) |
| MINOR 5: two directive items were not covered | Both gaps stated (6, 12); the negative label is named by its scope |
| MINOR 6: the B rebuild could fail after setup | The launcher compares the data build's source hashes with the source commit at $0 (10) |
| MINOR 7: the reload path had never run | The smoke stage runs the fresh-process reload before any main run; new stop `SMOKE_RELOAD_FAILED`; the reload now takes its rows from the saved checkpoint |
| MINOR 8: the pin commit would break an existing test | `test_q4_sdg_curriculum.py` now uses an empty temporary pin file; `q4_sdg_curriculum.py` unchanged |

## 15. Changes in revision 3 (the verification of revision 2, and the coordinator's decisions of 2026-09-24)

**The verification** of revision 2 (commit `294471a5`) is recorded in `Q4_AB_REVIEW_20260924.md` (commit `fbcc279b`).
Its verdict: CHANGES_REQUIRED. Its points, in short:
- V1 (MAJOR): a model that reads the trees' shape and operators, but no field value, passes T3 (44 distinct of 256)
  yet was graded NONE, so six such runs gave ARCHITECTURE_CHANGE_JUSTIFIED.
- V2 (MINOR): a shape-only reader (14 distinct, below the T3 threshold 32) was also graded NONE.
- V3 (MINOR): an invalid run whose final reading is FULL was ignored, so JUSTIFIED could fire while one run showed full
  input use.
- V4 (NOTE): the fix needs a new revision, a new review, and new approved hashes in the job's `launch.py`.

**Coordinator decisions of 2026-09-24**, quoted word for word as the builder received them:

> 1. NONE means TOTAL collapse only: T1, T2V and T2P all fail AND the run gives exactly 1 distinct free output over the
>    256 SP1 rows. Any run with 2 or more distinct free outputs is NOT NONE.
> 2. Add levels between NONE and the field levels: STRUCTURE_OR_OUTPUT_VARIATION (2 or more distinct free outputs, or
>    T2P passes, while T1 and T2V fail). It blocks ARCHITECTURE_CHANGE_JUSTIFIED. Keep FULL as it is.
> 3. ARCHITECTURE_CHANGE_JUSTIFIED fires only if every run that has a FINAL reading (valid or invalid) is NONE in at
>    least 2 of its arm's 3 seeds, for both arms, and the calibration guard is clean. Otherwise the architecture verdict
>    is withheld with named reasons (it can only become rarer).
> 4. Add an information-only label FIELDS_NOT_READ_IN_ANY_RUN when no run at the final checkpoint passes T1 or T2V. It
>    justifies nothing by itself; it names the target for a later, separately approved design discussion.
> 5. Keep the calibration guard on T1, T2V and T2P, say so, and report the checkpoint-0 distinct-output counts for
>    every run.

**What revision 3 changed** (code: `q4_ab_rules.py`, `read_q4_ab_results.py`; tests: `test_q4_ab.py`):

| Decision / point | Change | Where |
|---|---|---|
| 1 (V1, V2) | NONE = not T1, not T2V, not T2P, and D = 1 (`NONE_DISTINCT_FREE_OUTPUTS = 1`). `input_use_level` now takes the distinct count D, not a T3 flag, so T3 and D cannot disagree | 7.1, 7.2 |
| 2 | New level `STRUCTURE_OR_OUTPUT_VARIATION` = not T1, not T2V, and (T2P or D >= 2). It replaces `STRUCTURE_ONLY` (disclosed below). FULL is unchanged | 7.2 |
| 3 (V3) | Arm and architecture rules read every run with a FINAL reading, valid or not. JUSTIFIED needs all of them NONE and at least 2 VALID NONE runs per arm. New reason `NOT_NONE_IN_A_RUN_THAT_IS_NOT_VALID`; the level reasons and SEED_DEPENDENT now also count invalid runs' readings | 7.3, 7.5, 7.7 |
| 4 | New information-only label `FIELDS_NOT_READ_IN_ANY_RUN` (`fields_not_read_in_any_run`) | 7.8, 9, 12 |
| 5 | The guard is `calibration_guard_fires` on T1, T2V, T2P at checkpoint 0 (the same test as revision 2). The verdict reports `checkpoint_0_distinct_free_outputs` and `calibration_checkpoint_0` for every run | 7.4 |
| V4 | Status back to PROPOSED_FOR_REVIEW. The approved values in `launch.py` are NOT changed; the launcher therefore refuses revision 3 | status block |

**Choices the builder made in applying the decisions (disclosed; the reviewer should check them).** Choices 1, 2, 4
and 5 were confirmed by the coordinator on 2026-09-24 (confirmations (a), (b), (c), (d); section 16).
1. *One new level, replacing STRUCTURE_ONLY.* Decision 2 says "levels" but names one. Its definition contains every
   revision-2 STRUCTURE_ONLY case (T2P passes, T1 and T2V fail). Keeping STRUCTURE_ONLY as well would have split the
   named level, so it was folded in. The reading still shows which part fired (T2P, and D). **Confirmed (a).**
2. *Decision 3's "2 of 3 seeds" counts VALID runs.* See 7.5. Counting invalid NONE runs would make JUSTIFIED more
   common than in revision 2, which the decision rules out ("it can only become rarer"). **Confirmed (b).**
3. *Reasons count invalid runs' readings.* When an invalid run blocks JUSTIFIED, the reasons name its level (for
   example SEED_DEPENDENT for an invalid FULL run) and add `NOT_NONE_IN_A_RUN_THAT_IS_NOT_VALID`.
4. *FIELDS_NOT_READ_IN_ANY_RUN needs at least one FINAL reading,* and it counts invalid runs' readings too (a field
   reading in any run, valid or not, suppresses it). With no reading at all the label would be vacuous.
   **Confirmed (c).**
5. *The guard still returns only its own reason.* When it fires, no other architecture reason is listed (as in
   revision 2). **Confirmed (d).**

**New or changed tests (torch-free):**
- The verifier's scratch fakes are now lab fakes: `shape_operators_only` (D = 44) and `shape_only` (D = 14). Both are
  graded STRUCTURE_OR_OUTPUT_VARIATION; six such runs give INCOMPLETE [STRUCTURE_OR_OUTPUT_VARIATION] and
  FIELDS_NOT_READ_IN_ANY_RUN.
- The partition test covers all 40 combinations of T1, T2V, T2P and D in (1, 2, 31, 32, 256); NONE is exactly one of
  them.
- An enumeration of 3,375 arms (and all pairs of the 286 distinct ones) checks decision 3, "only rarer than revision
  2", and that every INCOMPLETE names a reason.
- V3 as a test: an invalid FULL run gives INCOMPLETE [SEED_DEPENDENT, NOT_NONE_IN_A_RUN_THAT_IS_NOT_VALID].
- The guard ignores D at checkpoint 0 (D = 44 everywhere: silent) and fires on T2P at checkpoint 0; the checkpoint-0
  counts are reported for all 6 runs.
- The launcher test now has two states: under review (this revision), the launcher must refuse the working copy;
  approved, its values must equal the working copy.

## 16. Changes in revision 3a (the verification of revision 3, and the coordinator's confirmations of 2026-09-24)

**The verification** of revision 3 (commit `793a4f68`) is recorded in `Q4_AB_REVIEW_20260924.md` (commit
`502a5704`). Its verdict: CHANGES_REQUIRED, one MINOR point, no BLOCKER, no MAJOR.
- W1 (MINOR): decision 3 did not reach a run whose FINAL checkpoint file exists but gives no reading. The reader
  dropped the whole reading when the run manifest was missing, when the file's identity was wrong, or when any
  recomputation in the file failed (even an exact flag on a teaching row). A fully reading run could then be left out,
  and ARCHITECTURE_CHANGE_JUSTIFIED could still fire. The verifier measured three such cases.

**What revision 3a changed** (code: `q4_ab_rules.py`, `read_q4_ab_results.py`; tests: `test_q4_ab.py`):

| Point | Change | Where |
|---|---|---|
| W1 | `read_q4_ab_results.read_run` records, for every run, whether its FINAL checkpoint file exists (`final_checkpoint_file_present`, checked on the path, so a file holding JSON `null` counts) and whether that file gave no FINAL reading (`final_checkpoint_present_without_reading`). `final_checkpoints_without_reading` lists those runs; the verdict reports them overall, per arm and in the `information` block | 7.3, 7.7, 7.8 |
| W1 | `q4_ab_rules.architecture_decision(finals_by_arm, guard_fires, final_checkpoints_without_reading)` takes the number of such runs (a required argument; not a non-negative int is refused). Any such run withholds JUSTIFIED with the new reason `FINAL_CHECKPOINT_PRESENT_WITHOUT_READING`, added last to every other INCOMPLETE. NOT_JUSTIFIED and the guard are unchanged | 7.5, 9 |
| W1 | The frozen record states the new condition and the new reason, and the scope of FIELDS_NOT_READ_IN_ANY_RUN. So `frozen_sha256` changes | `q4_ab_rules.frozen_record` |

**Coordinator confirmations of 2026-09-24**, recorded word for word as the builder received them:

> (a) folding STRUCTURE_ONLY into STRUCTURE_OR_OUTPUT_VARIATION is confirmed;
> (b) decision 3 means at least 2 VALID NONE runs per arm AND every FINAL reading (valid or not) NONE, confirmed;
> (c) FIELDS_NOT_READ_IN_ANY_RUN is emitted only when at least one run has a FINAL reading, and a field reading in an
>     invalid run suppresses it, confirmed;
> (d) when the calibration guard fires it stays the only architecture reason, confirmed.

They confirm the builder's choices 1, 2, 4 and 5 of revision 3 (section 15). Revision 3a does not change any of them.

**Choices the builder made in revision 3a (disclosed; the reviewer should check them):**
1. *The arm labels are unchanged.* The coordinator asked for the architecture rule to withhold JUSTIFIED. An arm label
   still speaks only about runs with a FINAL reading (7.3), so an arm can say SHOWS_NO_INPUT_USE while the
   architecture label is INCOMPLETE. The unread runs are listed per arm. If the arm label should also be withheld,
   that is a small change; it is not made here.
2. *FIELDS_NOT_READ_IN_ANY_RUN is unchanged; its scope is stated (7.8).* Confirmation (c) fixes when it is emitted.
   The verifier offered two fixes: suppress it, or state its scope. Suppressing would add a condition that (c) does
   not name, so the scope is stated and the unread runs are listed beside it.
3. *No partial reading is kept.* The verifier's optional idea (keep the input-use reading when only an exact-flag
   check failed) is not done. A file that fails any check gives no reading, and it withholds JUSTIFIED instead.
4. *Only the FINAL checkpoint is covered.* A checkpoint-0 file that exists but gives no reading still leaves that
   run out of the calibration guard, as in revision 3. This is outside W1; it is an open question for the coordinator.

**New or changed tests (torch-free):**
- New `test_reader_final_checkpoint_present_without_reading_withholds_justified`. Run B 20260933's FINAL file exists
  but gives no reading, and the other five runs are input-blind: a flipped SP1 exact flag, a flipped TEACH_FIT exact
  flag, a missing run manifest (the verifier's three measured cases, all JUSTIFIED under revision 3), a wrong rules
  hash, a file holding JSON `null`, and an input-blind run with a flipped flag. Each gives INCOMPLETE
  [FINAL_CHECKPOINT_PRESENT_WITHOUT_READING]. Controls: a FINAL file that does not exist is not flagged (JUSTIFIED, as
  before); two valid FULL runs still give NOT_JUSTIFIED with no reason; a firing guard stays the only reason; two
  flagged runs are listed in run order and the reason is added after STRUCTURE_OR_OUTPUT_VARIATION; unparsable FINAL
  files still stop the reader.
- `test_architecture_rule_can_only_become_rarer_and_always_names_a_reason` now also runs every pair of the 286
  distinct arms with 1, 2 and 6 unread FINAL files (27 JUSTIFIED cases become INCOMPLETE; nothing becomes JUSTIFIED),
  and refuses a count that is not a non-negative int.
- `test_reader_recomputes_what_prep_claims`: its two cases with a dropped or swapped edit value in B 20260931's FINAL
  file said JUSTIFIED under revision 3. They now give INCOMPLETE [FINAL_CHECKPOINT_PRESENT_WITHOUT_READING]. This is
  W1 itself, so the assertion changed.
- `test_reader_labels_are_the_declared_ones` now also sees `ARCHITECTURE_INCOMPLETE_BECAUSE_FINAL_CHECKPOINT_PRESENT_WITHOUT_READING`.

## 17. Changes in revision 3b (the fresh review of revision 3a, and the coordinator's decisions of 2026-09-24 on it)

**The review** of revision 3a (commit `f32b5739`) is recorded in `Q4_AB_REVIEW_20260924.md` (commit `ae3c7ba2`). Its
verdict: CHANGES_REQUIRED, one MINOR finding, no BLOCKER, no MAJOR, five NOTEs.
- X1 (MINOR): the calibration guard skipped every run whose checkpoint-0 file exists but gives no reading, and still
  printed INPUT_USE_RULE_SILENT_AT_INITIALISATION. A decisive architecture label could follow. The reviewer measured
  it: with both checkpoint-0 files of one seed pair unread (and that pair passing T2P at checkpoint 0), revision 3a
  printed SILENT and ARCHITECTURE_CHANGE_JUSTIFIED (case G1), or SILENT and
  ARCHITECTURE_CHANGE_NOT_JUSTIFIED_BY_INPUT_USE_RULE (case G3). With the files readable, the guard fired (case G0).
- NOTE N1: arm labels speak past two known unknowns (a firing guard; an unread FINAL file). Decision 2 below covers
  the second. The first is unchanged (open question in the builder report).

**Coordinator decisions of 2026-09-24**, quoted word for word as the builder received them:

> 1. List every run whose checkpoint-0 file exists but gives no reading (a path check, as for the FINAL file in 3a).
>    If any exists, the calibration state is a third value (for example CALIBRATION_UNREADABLE) instead of silent or
>    fired, and the architecture verdict is INCOMPLETE with the named reason CHECKPOINT0_PRESENT_WITHOUT_READING. It
>    must only make both JUSTIFIED and NOT_JUSTIFIED rarer, never more common.
> 2. Arm labels: ARM_x_SHOWS_NO_INPUT_USE is withheld (with a named reason) when any run of that arm has a FINAL file
>    without a reading. The same for any other arm-level label that 3a's unread-FINAL rule does not already cover.

**What revision 3b changed** (code: `q4_ab_rules.py`, `read_q4_ab_results.py`; tests: `test_q4_ab.py`):

| Decision | Change | Where |
|---|---|---|
| 1 | `read_q4_ab_results.read_run` records, for every run, `checkpoint_0_file_present` (the path) and `checkpoint_0_present_without_reading`; the missing-manifest return sets it too. `checkpoint_0_files_without_reading` lists those runs; the verdict reports them in `checkpoint_0_files_present_without_reading` | 7.4, 7.7 |
| 1 | New `q4_ab_rules.calibration_state(checkpoint_0_tests, checkpoint_0_files_without_reading)`: CALIBRATION_UNREADABLE first, then FIRES, then SILENT (`CALIBRATION_STATES`). The count is required; anything but a non-negative int is refused | 7.4 |
| 1 | `q4_ab_rules.architecture_decision(finals_by_arm, calibration, final_checkpoints_without_reading)`: the second argument is now the calibration state itself (one of `CALIBRATION_STATES`; revision 3a's bool is refused), so the printed calibration label and the decision cannot disagree. CALIBRATION_UNREADABLE gives INCOMPLETE with the one reason `CHECKPOINT0_PRESENT_WITHOUT_READING` | 7.5 |
| 1 | The verdict reports `calibration_guard_fires_over_readable_runs` (report only) | 7.4 |
| 2 | New `q4_ab_rules.arm_decision(arm, finals, final_checkpoints_without_reading)` returns (label, reasons); `arm_label` is its label and now takes the arm's count too (required). An unread FINAL file in the arm withholds SHOWS_NO_INPUT_USE: INPUT_USE_UNDETERMINED with the reason `FINAL_CHECKPOINT_PRESENT_WITHOUT_READING` (`ARM_REASONS`), emitted as `ARM_<arm>_INPUT_USE_UNDETERMINED_BECAUSE_FINAL_CHECKPOINT_PRESENT_WITHOUT_READING` and in `arms.<arm>.label_reasons` | 7.3, 9 |
| 2 | SHOWS_INPUT_USE is not withheld (it cannot be made false by such a file; 7.3) | 7.3 |
| 1, 2 | The frozen record states the three calibration states, the new reason, the arm rule and the new JUSTIFIED and NOT_JUSTIFIED conditions; `SPEC_REVISION` says revision 3b. So `frozen_sha256` changes | `q4_ab_rules.frozen_record` |

Revision 3a's own disclosed choices 1 ("the arm labels are unchanged") and 4 ("only the FINAL checkpoint is covered")
are replaced by decisions 2 and 1. Its choices 2, 3 and 5 are unchanged.

**Choices the builder made in applying the decisions (disclosed; the reviewer should check them):**
1. *The label name* `CALIBRATION_UNREADABLE` is the coordinator's example, used as given.
2. *The third state comes first.* When a readable run fires AND a checkpoint-0 file is unread, the state is
   CALIBRATION_UNREADABLE, as decision 1 says ("instead of silent or fired"). The readable runs' result stays in the
   verdict (`calibration_guard_fires_over_readable_runs`). Both roads give INCOMPLETE, so no decisive label depends on
   this order.
3. *The calibration reason stands alone.* Under CALIBRATION_UNREADABLE the architecture reasons are exactly
   `[CHECKPOINT0_PRESENT_WITHOUT_READING]`, the same shape as the guard (confirmation (d)). Decision 1 names one reason.
4. *"The same for any other arm-level label" (decision 2, second sentence).* Read as: withhold every arm-level label
   that an unread FINAL file could make false. Only SHOWS_NO_INPUT_USE can be. SHOWS_INPUT_USE cannot (7.3), and a test
   proves it; withholding it would also make NOT_JUSTIFIED rarer, which decision 2 does not say. The pair and lessons
   labels are already covered: an unread run is never valid, so its pairs are PAIR_INCOMPLETE.
5. *The arm reason is named only when it changed the label.* An arm that is UNDETERMINED for another cause gets no
   reason, as in revision 3a; its unread runs are still listed per arm.
6. *The architecture rule reads the arm labels without the arm counts* (`arm_label(..., 0)`, revision 3a's labels)
   and keeps its own W1 condition. The printed arm labels (with the counts) give the same architecture label, because
   JUSTIFIED already needs no unread FINAL file, and SHOWS_INPUT_USE is never withheld.

**New or changed tests (torch-free):**
- New `test_reader_checkpoint_0_present_without_reading_makes_calibration_unreadable`: the reviewer's G0 (control:
  FIRES), G1 (was SILENT and JUSTIFIED; now CALIBRATION_UNREADABLE and INCOMPLETE [CHECKPOINT0_PRESENT_WITHOUT_READING]),
  G2 (only one run of the pair unread; was FIRES; now CALIBRATION_UNREADABLE, the readable firing reported), G3 (was
  SILENT and NOT_JUSTIFIED; now INCOMPLETE). Also a wrong rules hash, a wrong checkpoint number, JSON `null` and a
  missing run manifest in checkpoint 0. Controls: an ABSENT checkpoint-0 file is not flagged (JUSTIFIED stays, as the
  path check says); unparsable checkpoint-0 files still stop the reader.
- `test_architecture_rule_can_only_become_rarer_and_always_names_a_reason` now also covers both decisions:
  - decision 2: all 4,096 arms where each seed may also be a run with an unread FINAL file. Exactly 3 arms move, from
    SHOWS_NO_INPUT_USE to INPUT_USE_UNDETERMINED [FINAL_CHECKPOINT_PRESENT_WITHOUT_READING]; every other arm label is
    unchanged. The 3 SHOWS_INPUT_USE arms with an unread file keep it for every possible invalid content of that run;
  - decision 1: all 81,796 pairs of the 286 distinct arms, with 0 or 1 unread FINAL files: CALIBRATION_UNREADABLE
    gives INCOMPLETE [CHECKPOINT0_PRESENT_WITHOUT_READING] in every case. The 9 JUSTIFIED pairs and 2 x 6,171
    NOT_JUSTIFIED cases move; nothing becomes decisive;
  - revision 3a's bool in place of the calibration state is refused.
- `test_calibration_guard_uses_t1_t2v_t2p_only` covers `calibration_state` (every single-run outcome, alone and among
  five silent runs, with 0, 1, 2 and 6 unread files).
- `test_reader_final_checkpoint_present_without_reading_withholds_justified`: arm B is now
  INPUT_USE_UNDETERMINED [FINAL_CHECKPOINT_PRESENT_WITHOUT_READING] in every case; a new case with the unread FINAL
  file in the same arm as 2 valid FULL runs keeps SHOWS_INPUT_USE and NOT_JUSTIFIED. The missing-manifest case also
  leaves checkpoint 0 unread, so it now gives CALIBRATION_UNREADABLE and the reason CHECKPOINT0_PRESENT_WITHOUT_READING.
- `test_reader_labels_are_the_declared_ones` now also sees `CALIBRATION_UNREADABLE`,
  `ARCHITECTURE_INCOMPLETE_BECAUSE_CHECKPOINT0_PRESENT_WITHOUT_READING` and
  `ARM_B_INPUT_USE_UNDETERMINED_BECAUSE_FINAL_CHECKPOINT_PRESENT_WITHOUT_READING`.
