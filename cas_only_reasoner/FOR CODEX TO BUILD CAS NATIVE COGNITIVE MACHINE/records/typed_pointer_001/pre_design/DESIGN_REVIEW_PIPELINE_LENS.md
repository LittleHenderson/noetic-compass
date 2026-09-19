# Adversarial design review — run-killers and pipeline fit lens

> Produced 2026-09-19 by a read-only $0 sub-agent reviewing `DESIGN_DRAFT_v0.1.md`. Its scratch scripts r1-r5 are in `measurements/pipeline_review/`.

FINDINGS REPORT: CNCM pointer design draft v0.1. Lens: run-killers and pipeline fit.

Reviewer: adversarial. Cost: $0. No torch, no model runs.
Repo (read-only): `.../_worktrees/vision-next/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE`. HEAD is e577947f.
Scratch scripts, all pure Python and re-runnable: `C:\Users\wakil\AppData\Local\Temp\claude\C--Users-wakil-OneDrive-Desktop-tksCAS-cas-only-reasoner\12c87ae7-c1f0-44b3-9b95-de65d5efbd48\scratchpad\design_review\`
- `r1_material.py`
- `r2_restore_identity.py`
- `r3_inputs.py`
- `r4_reach_lexical.py`
- `r5_flag_rules.py`

Path correction: the practice study records are at `records/typed_practice_001` under the CNCM root. They are not under `research/CAS_META_2_COMPOSITION/records/`; that folder holds only `package_daeb6497`.

VERDICT: The design does not fit the pipeline as written.
- 7 run-killers must be fixed in new files (zero shared edits is achievable).
- 2 more items are not job crashes but block the label or the launch: RK8 (reused gate reader returns VOID) and RK9 (launch blocked if the code tree changes between jobs).
- 3 false-positive risks. The worst is FP1: the unchanged primary gate can print LEARNS_NEW_WORLDS from flag copying alone.

## RUN_KILLER

**RK1 — The shared training step rejects any weight that got no gradient.** [MEASURED + READ]
- Evidence: `learner.py:271` requires every weight in `self.module` to have a non-None gradient after `total.backward()`. `stage_batch` zeroes gradients with `set_to_none=True` (`learner.py:185`).
- Measured on the 1,470 practice batches: role_set is missing from 1,150 batches, definition from 1,050, context from 1,070, analogy from 1,120, edge_account from 950, correspondence from 670, parts from 630, reach from 400. All 16 interference batches are definition+context only.
- Effect: any per-kind head (edge MLP, role embedding, world-choice head, option vectors) gets no gradient in most batches. The first such batch fails with `TYPED_LEARNER_GRADIENTS`.
- Fix: write the learner's own `train_sealed_batch` in a new file. Require finite gradients only on weights that took part, require at least one gradient, and log which weights got gradients per update. Register how AdamW treats skipped weights. The alternative, `0*sum(params)`, still applies weight decay to unused heads; if used, register that.

**RK2 — The registered learner class cannot host the new network.** [READ]
- Evidence, `TypedCourseLearner.__init__`:
  - `learner.py:82-86`: scope must equal exactly the ^6 contract, and weights must be exactly `left/right/merge` with shapes `(64,64)/(64,64)/(64,128)`. A container network fails with `TYPED_LEARNER_REGISTERED_SCOPE` / `PARAMETER_SHAPE`.
  - `learner.py:93-96`: `max_updates` ≤ 176 and wall ≤ 3,600.
  - `learner.py:97-101`: `condition` and `source_seed` must come from fixed sets.
- Evidence, `restore_checkpoint`:
  - `learner.py:336` compares against the module-level `learner.profile()`, which a subclass cannot override. That profile describes the old machine ("no learned head").
  - `learner.py:341` loads weights strictly into `framework.module` before the object is built.
- The silent workaround (pass the registered ^6 framework, keep heads outside `module`) fails late:
  - the optimizer covers only the three ^6 weights (`learner.py:107-109`);
  - the identity and the checkpoint export cover only `module.state_dict()` (`learner.py:111`, `298`);
  - so the heads are never trained and never saved. Reload then fails with `RELOAD_PREDICTION_MISMATCH` after the full 3-hour spend.
- Also: `scope_parameters` sets `requires_grad=False` on every non-^6 weight (`graph_teaching/trainer.py:86-87`). Never call it on a container.
- Fix: a new `PointerCourseLearner` class. `self.module` must be ONE container holding every learned weight. Own `__init__`, `export_checkpoint`, `restore_checkpoint` and `profile`. Reuse shared code only by calling functions (e.g. `TypedCourseLearner._tensor_loss(self, …)`, which uses only `self.torch`), and pin `learner.py` in the new profile.

**RK3 — Label lookups through the tokenizer blow the time limit.** [MEASURED]
- Evidence: `FrameTokenizer.encode_text` rebuilds its 3,829-entry lookup on every call (`tokenization.py:151`). Measured: 0.0111 s per call.
- The world-choice slots list every world: `setting_ref` / `kind_ref` / `function_ref` have 64 symbols (70 records each); analogy `world_id` has 65. So one such packet needs about 64 × (labels + 4 declarations) ≈ 512 encodes ≈ 5.7 s.
- Across 8,180 training presentations plus evaluations, that far exceeds `WORKER_DEADLINE_SECONDS` = 12,300.
- Fix: tokenize all 230 distinct labels (244 nodes) and all declaration texts once. Pin the digest of that cache. Build one lookup dict. Get projection rows once via `encoder.export_state()`, never per packet.

**RK4 — Job names longer than the practice study's break the storage bucket name.** [MEASURED]
- Evidence: bucket = job + "-807562639912". It must match `[a-z0-9][a-z0-9-]{1,61}[a-z0-9]`, i.e. at most 63 characters (`practice_contract.py:226`; S3 has the same limit).
- Measured: token "tprac" gives exactly 63. "tptr" gives 62. "tpoint" gives 64 and fails. "tpointer" gives 66.
- Fix: the study token after "cas-meta2-" must be at most 5 characters. Add a length test.

**RK5 — Subclassing the practice launcher silently keeps practice-only settings.** [READ]
- `typed_practice_launch.py:320`: `_user_data` checks the PRACTICE job pattern. A new job name fails with `PRACTICE_WATCHDOG_JOB`.
- `:359-360`: `bind_authority` calls the practice `validate_authority` (practice CANDIDATE and config). Hard fail.
- `:261`: `reservation_plan_for` writes `task_scope` "cncm_typed_practice_001". The budget ledger would be silently mislabeled.
- `:365`: `failure_statuses` must include the new worker's FAILED status. Otherwise a failed worker is read as REMOTE_FINISHED and collection demands artifacts (`graph_training_curriculum_launch.py:1023`, `1096`). The result schema must match exactly (`:1018`).
- `:201-203`: `git_package_bytes` only admits `research/*`, `cncm/*.py`, or paths in `contract.MATERIAL`. Checkpoint files under `records/typed_practice_001/...` fail with `PRACTICE_SOURCE_MEMBER_SCOPE` unless they are in the NEW contract's MATERIAL.
- `PACKAGING_SOURCES` must list the new launcher and any launcher it imports.
- Fix: override `_user_data`, `bind_authority`, `reservation_plan`, `failure_statuses` and `git_package_bytes`, or copy the provider class. Keep the `_probe()` constant check.

**RK6 — A "reported, not gating" checkpoint check can still fail the whole job.** [READ + INFERRED]
- Missing artifact: a successful delivery requires every name in `EXPECTED_ARTIFACTS` (`typed_practice_worker.py:187-188`), and the lifecycle evidence contract requires them too. If the check fails and skips its files, the job becomes FAILED and gate I1 reads VOID.
- Import failure: if the check hits an import error inside a try/except, `ManifestImporter.failed` stays set. Then `attestor.snapshot()` raises `FAILED_IMPORTS` at `final_source_verification` (`typed_source_attestation.py:98`), after all the money is spent.
- Fix: the check always writes its artifact with `status` COMPLETE or FAILED inside. Import every module it needs at startup, outside any try.

**RK7 — Strict reproducible-math mode may reject the message-passing operations.** [INFERRED — must be smoke-tested]
- Evidence: the worker turns on `torch.use_deterministic_algorithms(True)` (`typed_practice_worker.py:252`). Some CUDA scatter, index and embedding-backward paths raise under this mode, and so may some `linalg` solvers used for GPU probes.
- Fix: dense adjacency matrix multiplies (4-node worlds; at most 244 bank nodes as one block), one-hot matrix multiplies instead of embedding lookups, and a closed-form ridge solve. Prove it with GPU smoke test S1.

## RUN_KILLER for the check, the label or the launch

**RK8 — Reusing the old gate reader returns VOID.** [READ]
- I1 imports `cncm.typed_practice_worker` and checks its `SUCCESS_STATUS` and `EXPECTED_ARTIFACTS` (`evaluate_gates.py:162-165`).
- I3 compares the start weights against the matched study's `initial_checkpoint` (`:182-189`). The pointer container can never match, so any failure gives VOID (`:226-237`).
- Fix: a new gate reader at `records/typed_pointer_001/evaluate_gates.py`, outside `cncm/` and `cas_meta2/`. I3 must be redefined as in DG4.

**RK9 — Adding a code file between jobs blocks the remaining launches.** [READ]
- Evidence: `validate_authority` re-hashes the live code inventory at execute time (`typed_practice_launch.py:125-127`). That inventory is every `.py` under `cncm/` and `research/CAS_META_2_COMPOSITION/cas_meta2` (`worker_contract.py:138-143`).
- Adding new files is allowed: the config is rebuilt from the tree, the manifest pins every row, and the loader only admits listed modules.
- Traps:
  - any `.py` added under those two folders between authority and launch (for example a gate reader or analysis script) blocks jobs 2–3;
  - any uncommitted `.py` fails the package build with `PRACTICE_INPUT_NOT_COMMITTED`.
- Fix: keep all analysis scripts under `records/`. Freeze the tree from authority until the third job.

**RK10 — The checkpoint check breaks on any byte change to about 15 shared files.** [MEASURED]
- `PracticeCourseLearner.restore_checkpoint` requires that today's values equal the checkpoint's recorded values for:
  - `learner.profile()`, which hashes `learner.py`, `loss_plan.py`, `recurrent_cjt/recurrence.py`, `graph_teaching/trainer.py`, `graph_teaching/real_framework.py`, `teaching_cycle/gpu_adapter.py` and `slots.profile()` (which pulls in `course`);
  - `practice_profile()`;
  - the encoder identity (`encoder.py`, `binding.py`, `tokenization.py`, `input_frames.py`, `slots.py`, `course.py`).
- Measured today: all 9 checkpoints match (3 seeds × initial / pass_01 / final): `learner_profile`, `practice_profile`, `encoder_identity`, the run identity digest, and the `.pt` hash against its json.
- The only `.py` change since c4f7c321 is `records/typed_practice_001/failure_anatomy.py`, which is outside the inventory.
- Fix: turn `r2_restore_identity.py` into a pytest that must pass at the frozen commit.

## FALSE_POSITIVE_RISK (could print a wrong "learns" label)

**FP1 — Flag copying alone passes the unchanged primary gate.** [MEASURED]
- Evidence:
  - The checker's definition answer = `declared_whole` + the focus world's kind/function. Its context answer = the focus world's setting + the declared participants (`checker.py:169-183`).
  - The draft feeds exactly these as input flags (is declared_whole, is participant, is focus world).
  - Eligible held questions: 10 are definition 5 + context 5, over 5 worlds.
  - A pure flag copier gets b=10, c=0, so p = 1/1024 = 0.0009765625 ≤ 0.01. It also meets ≥2 kinds and ≥2 worlds. So `G_LEARN_p0_to_p10` passes every seed and prints LEARNS_NEW_WORLDS.
- The draft only "prints the per-tier split" next to the label. That is prose, not the program's reading.
- Fix: LEARNS_NEW_WORLDS must require the RELATIONAL-tier test to pass (29 eligible questions, 5 worlds: correspondence 5, edge_account 5, reach 9, analogy 5, parts 5). The all-kinds `G_LEARN` becomes a reported flag. Add a gate-reader test showing that a flag-copy-only outcome does not get the label.

**FP2 — The "relational" tier is not flag-free.** [MEASURED]
- Evidence: an edge-free flag rule solves 3 of 5 eligible held `parts` questions. The rule: `parts(whole=declared_whole)` = participants minus whole. Records: held parts 3/9, trained parts 4/44, held reach 5/26, trained reach 19/71.
- In 20 of 64 worlds, participants minus whole = the children of the declared whole.
- Fix: freeze a per-question flag-rule baseline before the run. Remove flag-solved questions from the relational gate population, as the 5 shortcut questions were removed.

**FP3 — Running the checkpoint probe first breaks the answer-custody rule.** [READ]
- Evidence: the probe labels need private answers (`checker.derive_target`) for held-world slots. Running it as the "first phase" means the worker reads held-back correct answers before training.
- The registered custody says otherwise: `practice_contract.py:11-12` ("so that the worker never reads a correct answer before training") and `typed_course_worker.py:149` (the checker is imported only after readback).
- Fix:
  - Phase A, first: restore the old checkpoints, extract public vectors only, seal them with create-only writes, verify logits. Cheap failure detection, no answers read.
  - Phase B, last: after all pointer evaluations, reloads and replays, derive the answers and fit the probes.

## DESIGN_GAP

**DG1 — Training depth is not 8.** [MEASURED]
- Batches use `depth` 1 / 2 / 4 / 8 for 380 / 370 / 340 / 380 of the 1,470 updates. So 74% of updates would run fewer than 8 rounds. Evaluation always uses 8.
- Reach VIA answers and isomorphism need at least 2–3 rounds.
- The draft's "`depth` (=8, the worker's existing argument)" is wrong for training.
- Fix: fixed K=8 rounds, with the batch depth recorded only as a schedule coordinate (`loss_plan` checks only depth ∈ {1,2,4,8}). Pin this in the learner profile.

**DG2 — The reach rule is not an input.** [MEASURED]
- The query vector is only the kind embedding plus arguments.
- Swapping the reach rule changes the answer for 1 held, 9 trained and 1 excluded record.
- Fix: add a rule embedding.

**DG3 — Some reach answers depend on hidden node-name order.** [MEASURED]
- Across all name relabelings of the focus world, the answer depends on the hidden alphabetical order of node names for 5/26 held, 11/71 trained and 2/10 excluded reach records. That covers 2 of the 9 eligible held reach questions.
- A machine blind to node order cannot solve these, except by symbol-order tie luck. It also trains on contradictory targets for them.
- Fix: either add a world-independent input "rank among the world's sorted node names", or register these as a fixed ceiling and remove them from the gate population before the run.

**DG4 — The new I3 ("re-derives from the seed") cannot be computed by a pure-Python gate reader.** [READ]
- The reader cannot run torch, so this I3 would collapse into comparing the job to itself (VACUOUS).
- Fix, in-job checks recorded for the reader:
  - (a) build `matched._framework(torch, device, seed)` FIRST. The ^6 sub-block identity must equal the matched study's `initial_checkpoint` `model_state_identity` for that seed.
  - (b) build the whole model a second time independently; the identity must be equal.
  - (c) the three seeds' identities must be pairwise different.
  - (d) the start weights must be identical whether the checkpoint check runs or not.

**DG5 — Held worlds are seen during training as wrong options.** [MEASURED]
- Held-world graphs and labels pass through the trainable world encoder as world-choice candidates in 1,340 of 8,180 training presentations (definition 460, context 470, analogy 410).
- This is comparable to the old hash sum, but it must be declared.
- Say "never the focus of a trained question", not "never seen".

**DG6 — The output format must match the loss plan exactly.** [READ]
- Predictions must carry `loss_plan.validate_prediction`'s exact field set, including a 64-hex `encoder_identity_digest` and `run_context_digest`.
- Each slot's logits tensor must follow `slot["symbols"]` order. The `whole` slot follows the world's node order (`slots.py:88`), not alias order.

**DG7 — Score size and loss-agreement limits can crash mid-run.** [READ + INFERRED]
- Scores must stay within |score| ≤ 1e6 (`slots.py:248`).
- The tensor loss and the plain-Python loss must agree within 2e-5 (`learner.py:261`).
- A residual recurrence with no normalization, feeding dot-product pointers, could break either mid-run.
- Fix: normalize (RMS) each round, and smoke-test S8.

**DG8 — Post-run ablations are unspecified.**
- They must run on restored copies (reset weights taken from `initial.pt`), only after the reload and replay checks.
- They must be in `EXPECTED_ARTIFACTS`, be timed, and write via create-only publishing.

**DG9 — Governance and budget are not yet executable.**
- The machine changed, so 3 new owner-signed per-job records are needed (`validate_owner` checks CANDIDATE and job).
- The $15 / 4 h per-job envelope is assumed, not measured. The old worker took 5,466 s; the check adds about 9–15 minutes; the pointer cost is unknown. If a GPU smoke projects more than about 11,000 s, the reservation must rise, which exceeds the owner's $45 cap and needs a new approval.

**DG10 — Reusing `practice_contract.DESIGN` would carry false fields.**
- It says `"registered_learner_unchanged": True` and `initialization` REGISTERED_RANDOM_SAME_AS_MATCHED_STUDY.
- Its schedule stats (`planned_slot_core_passes` 124510, `presentation_slots`) are old-machine work counts.
- `expected_main_delta` (`typed_practice_worker.py:174-180`) and the check at `:361` count old per-slot core passes, which the new machine does not have.
- Fix: a new DESIGN and a new planned-work formula (e.g. packet forwards; rounds × worlds read), tested against real counters in a smoke run.

## VACUOUS

- **V1** — `base._encoding_checks` (`typed_course_worker.py:228-275`) checks the old encoder's packet/slot vectors and its 90 readout rows. The pointer machine never uses them. Replace it with checks on the pointer inputs: finite, cache equal to direct, label cache pinned, no leak of node aliases.
- **V2** — Pre-block probes at initial / pass_01 / final all read the same frozen encoder, so the vectors are identical. Compute them once. The $0 half is feasible in pure Python: `binding.py` rows and permutations are SHA-256 based. Only post-block vectors need the GPU.
- **V3** — An I3 that compares the job's recorded start identity with itself proves nothing (see DG4).
- Note: a node-relabeling equivariance test is correctly not evidence of learning. It is still a required ENGINEERING test that no alias channel exists (S9).

## MINOR

- **M1** — Each practice checkpoint exists twice: `checkpoints/` and `collected/results/artifacts/`. Measured: byte-identical for all 3 seeds. Pin one path (`checkpoints/`).
- **M2** — The owner-facing claim "checkpoint check at no extra cost" is false. It costs about 3 course-sized passes per job. Old measurements: 173.8 s warm and 300.5 s cold per 564-packet evaluation. That is about 9–15 minutes, or $0.38–0.63 per job at $2.52/hour.
- **M3** — Restoring an old checkpoint overwrites the global torch CPU, CUDA and Python random-number state (`learner.py:360`), and `matched._framework` re-seeds. Phase A must finish before the pointer model is seeded and built.
- **M4** — The old forward pass does not expose the post-block vector: `predict` returns only the slot's own logits. So the extraction code must copy the forward internals (`encode_slot` + `recurrence.run_passes` with the same `rms`, `cast` and `zeros`). It must be proven equal by rebuilding logits from the extracted vector and comparing bit-for-bit with `restored.predict` scores in the same job. Comparing with the receipts' sealed scores is report-only.

## CHECKPOINT CHECK: facts

**Files to ship** (one package serves all 3 jobs):
- For each seed 20260917 / 20260918 / 20260919: `records/typed_practice_001/receipt_<seed>/checkpoints/{initial,pass_01,final}.pt` and `{initial,pass_01,final}_checkpoint.json`.
- 18 files, 15,259,777 bytes raw. The 9 `.pt` files compress to 3,462,330 bytes, so the archive is about 5,776,657 bytes against a 25,165,824 limit.
- Inventory becomes 236 + 18 rows (limit 2000). Largest file 1,717,171 bytes (limit 4 MiB). Total well under 96 MiB.
- Add them to the new contract's MATERIAL and its input inventory (appended, like the matched study appends its development file). Also pin each file's sha256 and `run_identity_digest` as constants.

**Can `PracticeCourseLearner.restore_checkpoint` run in the new worker?** YES, under these conditions:
- Linux, with `CAS_META2_RUN_TEACHING_CYCLE=1` (the bootstrap sets it).
- CUDA with torch 2.11.0+cu128.
- The framework from `matched._framework(torch, device, seed)`.
- Zero byte change to the pinned sources (measured equal today).
- Stored limits pass the practice ceilings: `max_updates` 1486 ≤ 2048, wall 12300 ≤ 14400. Context MIXED_SAME_ITEMS / 101 is inside the allowed sets.
- Time budget left after restore: final checkpoints record 5,005.3 / 5,016.0 / 4,992.2 s used of 12,300 s. Core-call budget: 191,198 used of 600,000, with 20,784 per course pass.

**Risk it adds:** RK6, RK10, FP3, M2, M3, M4.

## MINIMAL BUILD PLAN (new files only; zero shared edits)

1. **`cas_meta2/typed_teaching/pointer_contract.py`** (pure)
   - Import the practice `split`, `practice_schedule`, `interference_batches`, `retention_packets`, `development_packets` and `held_back_questions` unchanged.
   - New CANDIDATE, CONFIG_SCHEMA, and JOB_PATTERN with a token of at most 5 characters.
   - MATERIAL + checkpoint pins; `input_inventory` wrapper; new DESIGN and deadlines; the pointer `expected_main_delta`; `make_config` / `validate_config`.
2. **`cas_meta2/typed_teaching/pointer_inputs.py`** (pure)
   - Deterministic public reader with a digest.
   - Label and declaration token cache built once.
   - Flags, adjacency, the reach rule, excerpt token ids.
   - Never reads supports, cue, instruction or node order; the rank feature appears only if DG3 is resolved that way.
3. **`cas_meta2/typed_teaching/pointer_learner.py`** (torch only when called)
   - The container `module` includes the ^6 block from `matched._framework`, built first.
   - Own `__init__`, `predict`, `stage_batch`, `train_sealed_batch`, `export_checkpoint`, `restore_checkpoint`, `profile`.
   - Borrows `TypedCourseLearner._tensor_loss`.
   - `.torch`, `.optimizer`, `.encoder` (the frozen typed encoder, providing `export_state`), `.counters`, `.cursor`, `.model_revision`, `.failed`, `.run_identity_digest`.
4. **`cncm/typed_pointer_worker.py`**
   - Reuses `typed_practice_worker` helpers (`_publish`, `_move_in`, `_append`, `_train_logged`, `_evaluate`, `_split_score`) and `base._ProgressWriter`, `_state`, `_check_state`, `_partial_checkpoint`, `_score_seal`.
   - Phases: preflight → packets → phase A → seed + double build → 10 passes → evaluations → reloads/replays → phase B → ablations → source verification → deliver.
   - Its own EXPECTED_ARTIFACTS.
5. **`research/CAS_META_2_COMPOSITION/aws/typed_pointer_launch.py`**
   - Copy or subclass with the RK5 overrides.
   - `bootstrap_source().replace("typed_matched_worker", "typed_pointer_worker")`, keeping the count==2 check.
6. **`records/typed_pointer_001/evaluate_gates.py`**
   - Copy with a new I1 (new worker) and the DG4 I3.
   - RELATIONAL tier as primary; the DG3 and FP2 removals from the population; DIRECT_READ reported only.
7. **`tests/test_typed_pointer_study.py`** — see the list below.

## TESTS REQUIRED BEFORE ANY PAID LAUNCH

**Pure ($0, pytest, with the numeric-import guard):**
- **P1** — Holdout and schedule identical to the practice study: held digest 668e6ce7…, excluded digest b82108e1…, `batches_digest` daf95831…, 45 eligible / 5 shortcut.
- **P2** — Bucket length ≤ 63 for all seeds.
- **P3** — Inventory has the 18 pinned checkpoint rows and stays within the row, byte and member bounds.
- **P4** — The r2 restore-identity freeze test, for all 9 checkpoints.
- **P5** — Package dry run with a fake git reader: archive ≤ 24 MiB; rendered worker names `typed_pointer_worker` and no old worker.
- **P6** — Launcher overrides: watchdog accepts the new job pattern and refuses the practice one; `bind_authority`; `task_scope`; `failure_statuses`; `_probe` constants.
- **P7** — EXPECTED_ARTIFACTS unique and < 500; covers checkpoint-check files; `required_count` = len + 3.
- **P8** — Worker refuses Windows before any numeric import and delivers a FAILED result with the new schema.
- **P9** — `pointer_inputs` purity, determinism and cache equality for all 230 labels; per-packet read time bounded.
- **P10** — Inputs exclude supports, cue, instruction and node order; include the reach rule.
- **P11** — Planned-work formula matches the schedule.
- **P12** — Gate reader: a flag-copy-only outcome gets no label; exact arithmetic; the new I3.
- **P13** — Frozen flag-rule baseline and DG3 removal list.
- **P14** — Custody: the checker is imported and targets derived only after the first pointer seal, except in phase B.

**GPU smoke (local RTX 4070, dev only, not claim-bearing):**
- **S1** — All 8 kinds run forward and backward with strict reproducible-math mode on; two runs are bit-identical.
- **S2** — `train_sealed_batch` works on a batch missing most kinds and on an interference batch.
- **S3** — Export → restore → predict gives identical output; `_check_state` equal; replay from prelast equals final.
- **S4** — Evaluation leaves the learned state unchanged (uses no randomness).
- **S5** — Start weights identical with the checkpoint check on or off; ^6 sub-block identity equals the matched study's start for the seed.
- **S6** — Phase A restores all 3 checkpoints; rebuilt logits equal `restored.predict` bit-for-bit; a forced failure still writes the artifact and does not poison `attestor.snapshot()`.
- **S7** — Time one pass (147 updates) plus one course evaluation; the projection must fit under 12,300 s with margin, or go back to the owner.
- **S8** — |scores| ≤ 1e6 and loss agreement ≤ 2e-5 for all kinds, including joint correspondence.
- **S9** — Node-relabeling equivariance (engineering check only).
- **S10** — Worker `run()` end-to-end on a shrunken schedule. Project rule: run `main()` end-to-end before every paid launch.

**Governance:** 3 owner-signed per-job approval records, and a frozen study doc and commit before the package is built.
