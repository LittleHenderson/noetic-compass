# CNCM pointer machine — design draft v0.2

This document supersedes `pre_design/DESIGN_DRAFT_v0.1.md`. It is a design draft, not a protocol. Nothing here has
been built, run, dry-run or reviewed a second time. Its purpose is to fold the pipeline review into the design, to
carry the corrections the two interface specs found, and to mark exactly what is still waiting on the two review
lenses that were never captured.

Branch `codex/cncm-vision-next`, HEAD `7b1ffca7`. CNCM root is
`...\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE`. Every relative path below is relative to that root.

## 0. Header block

### 0.1 Owner order, verbatim

From `records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:77`:

> "do option 1, pointer answers plus the checkpoint check BUT EXAMINE THIS TO SEE IF AND HOW IT OR ANYTHING IN HERE CAN
> HELP:      "C:\Users\wakil\Downloads\CAS-RPA × TypeSafe AI × CAS PCBA_ JEV Integration Deep Dive.pdf""

### 0.2 Option 1 as it was offered to the owner, verbatim

From `records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:80-85`. This is what was approved.

> "Pointer answers + checkpoint check (my recommendation). Today the machine answers by choosing from a fixed list of 90 labels,
> like "node 3" or "world 46". A pointer version answers by pointing at a part of the question's own input: "this node here."
> That pointing skill is the same for any world, including new ones. It's the standard fix for "works on things it has seen,
> fails on new ones." Whether it actually works here is what the run would test. I'd build and dry-run it for $0 first. The paid
> run would be about the same size as this one (about $13, with $45 reserved). The checkpoint check from option 3 runs on the
> same machine at no extra cost."

### 0.3 The owner decisions of 2026-09-19, verbatim

The first three were given in the session that picked up the hand-off
(`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:381-391`).

1. **Two corrections — accepted.** Owner answer verbatim: *"Accept both, carry on."* The two corrections are: (a) the
   in-job checkpoint check costs about $0.38–$0.63 per job, not "no extra cost"; (b) pointer answers alone cannot work,
   because the INPUT must change too.
2. **The short AWS smoke job for the end-to-end worker test S10 — approved.** Well under $1.
3. **Gate change — confirmed.** Owner answer verbatim: *"Yes — require the relational kinds."*
   `LEARNS_NEW_WORLDS` will require gains on the RELATIONAL kinds (parts, edge_account, reach, correspondence,
   analogy). The all-kinds result is reported alongside as a flag, not as the label.

The second pair was answered later the same day (2026-09-19). Each was offered as a list of labelled options and the
owner selected one label. The selected labels are recorded verbatim.

4. **On purpose — the owner selected the option labelled "Run it as the transfer test, label honestly (Recommended)".**
   The study runs as the transfer test it was built to be, and the label is printed honestly: a tier or a kind whose
   answer is already in the input is reported as such and never carries a learning claim. The reconciled evidence
   behind the choice is `REVIEW_SYNTHESIS.md` §10.4, "The three-lens reconciled position on what can be learned",
   whose closing line is: *"This is the substance of what the owner decided on 2026-09-19: run it as the transfer test
   and label honestly."*
5. **On training — the owner selected the option labelled "Stratify AND train longer (Recommended)".** The schedule is
   stratified, so every kind appears in every update, and the study trains for more passes than the practice study's
   ten. The numbers behind both halves are in §5.3.1.

### 0.4 Standing rule that never changes

Owner ruling 2026-09-18, recorded at `records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:93-96`: rule-layer gains never
count as machine progress. A gain in a rule, a schedule, a checker or a score is not the machine learning. Only a
change in the trained weights that moves the answers counts.

Standing owner goal, verbatim excerpt, same source: "IT MUST BE LEARNING LEARNING AT THE NEURON LEVEL THE ARCHITECTURE
SHOULD BE SERVING THIS PURPOSE ... CONTINUE ON WITH AI AGENTS RESEARCH AND DEVELOPMENT UNTIL THE ULTIMATE VISION OF
THIS PROJECT IS FULLY FULFILLED MEANING WE HAVE A WORKING CASFORMER LLM/CNCM".

---

## §1 Claim state

Claim-status words used here are the project's own: REAL, VALIDATED, LICENSED, NOT LICENSED, GREY, VACUOUS,
WITHDRAWN, ENGINEERED-NOT-VALIDATED, FLAG_FOR_HUMAN_REVIEW (`docs/CAS_HARNESS_SPEC_SHEET.md` legend), plus OPEN,
MEASURED and INFERRED used as the measurement documents use them.

### REAL (negative) and measured

- **No transfer to a never-practised world.** The old machine, trained ten passes (13 → 85 of 189 practised questions),
  answered 2–3 → 2–5 of 45 held-back questions. Label `NO_TRANSFER_TO_NEW_WORLDS`, commit `8cdbad81`
  (`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:16-18`).
- **The old machine's input makes that transfer fail, for the four kinds that were probed.** A cross-world linear probe
  fitted on practised worlds scores no better than the held majority on never-practised worlds, and every held figure
  sits inside a random-query null (P from 0.1633 to 0.9833). Held accuracy against majority, from
  `pre_design/INPUT_DEFECT_MEASUREMENT.md:117-120` and `measurements/input_defect/RERUN_VERIFICATION_20260919.md:48-49`:

  | kind | trained acc (λ=1) | held acc (λ=1) | held majority |
  |---|---|---|---|
  | parts | 94.1520 | 58.3333 | 52.7778 |
  | context | 96.7949 | 60.2941 | 75.0000 |
  | role_set | 80.5556 | 83.3333 | 83.3333 |
  | edge_account | 82.0155 | 73.8971 | 80.1471 |

- **Any never-seen slot name gets chance, whether it sits in a new world or a practised one.** Held slots whose exact
  spec, or identical vector, occurs among trained slots: **0 of 617** (`INPUT_DEFECT_MEASUREMENT.md:86`). The only part
  of the slot input that changes from slot to slot is the query code: exactly **0.500000** of its squared norm, a
  SHA-256 hash of the slot name (`INPUT_DEFECT_MEASUREMENT.md:81`, `:127-129`).
- **The published 96.3758% was exact-name recall, not world reading.** Seen names 96.8627–100.0000, unseen names
  50.0000 (`INPUT_DEFECT_MEASUREMENT.md:140-143`).
- **The result was independently reproduced on 2026-09-19.** The whole chain was rebuilt and re-run: gate digests
  matched, 2,598 slots and 2,442 distinct rows matched, both analysis stdouts identical after stripping wall-clock
  timings, summary JSON canonically identical. Rebuild cost measured at **903.2 s**
  (`measurements/input_defect/RERUN_VERIFICATION_20260919.md:20-42`, `:62`).

### The measured scope, stated exactly — this correction is load-bearing

**MEASURED covers four of the eight kinds: `parts`, `context`, `role_set`, `edge_account`.** These are the four per-bit
kinds. The probe fitted and tested a linear reader on those four only.

**"Impossible for ANY learner, all kinds" is INFERRED, NOT MEASURED.** It follows from the hash construction
(`binding.py:198-202`) plus the q-blind ceiling. `pre_design/INPUT_DEFECT_MEASUREMENT.md:168` already marks it
INFERRED, and `measurements/input_defect/RERUN_VERIFICATION_20260919.md:52-60` restates the split and records that the
handoff prose of `857af081` ran the two statements together.

**The four choice kinds — `definition`, `analogy`, `correspondence`, `reach` — were never probed.** Three of them
(`correspondence`, `analogy`, `reach`) sit in the new RELATIONAL tier, which is the tier the owner confirmed as the
gate. So the gap between MEASURED and INFERRED is not a wording nicety: it is exactly the gap the pointer gate has to
close. Also, `parts` and `edge_account` agree with the held majority to the digit on the q-blind ceiling
(`INPUT_DEFECT_MEASUREMENT.md:161`), which is why "any rule that gives one answer per packet" cannot do the job.

### INFERRED (stated as INFERRED, not as measurement)

- Impossible for any learner, for all eight kinds, from the hash construction plus the q-blind ceiling. See above.
- That the pointer machine will read a world in a way that transfers. This is the hypothesis the study tests. It is not
  measured, and nothing in this document may be read as evidence for it.
- That the ^6 block starts from exactly the practice study's weights on the same seed. The mechanism was confirmed from
  source order (`research/CAS_CJT_TRANSFORMER_v0_2/cas_cjt/neural.py:181-188` builds `DECOMPOSE` first, so
  `_DecomposeTransform` draws first from the seeded RNG at `cncm/typed_matched_worker.py:44-46`) and measured
  numerically on the local dev GPU to within **7.450580596923828e-09**, but not bit-exactly off the AWS instance
  (`pre_design/measurements/framework_probe/FINDINGS.md:17-35`). See §4.

### OPEN

- Whether a pointer machine's neurons learn a skill that transfers. Nothing built, nothing run
  (`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:363`).
- The final relational gate population after the FP2 flag-rule removals and the DG3 node-order removals. Both reviews
  that would complete it were never captured. See §6.
- Whether node LABEL words survive in the input at all. `INTERFACE_SPEC_POINTER.md:86-88` marks this `OPEN:` and waits
  on lens B.
- The pointer machine's exact head set. `INTERFACE_SPEC_POINTER.md:110` marks this `OPEN:` and waits on lens B's
  expressivity table.
- The pointer machine's own counter key set for `expected_main_delta`
  (`INTERFACE_SPEC_POINTER.md:49`, marked `OPEN:`).
- Whether a job's measured time fits the $15 / 4 h envelope. The smoke S7/S10 was approved but has not been run.

### NOT LICENSED

Any claim about the pointer machine, about CASformer attention, or about the architecture family
(`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:364`).

### VACUOUS — a control that must not be counted as evidence

Relabelling or shuffling controls over a quantity the machine is supposed to be sensitive to are VACUOUS
(`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:109`). Such a control is never evidence of learning
(`records/typed_pointer_001/pre_design/PDF_ASSESSMENT.md:22`).

> **CORRECTED 2026-09-19 — the machine is deliberately NOT permutation-symmetric, so the earlier reasoning does not
> hold as written.** Design v0.1 argued that node-relabelling invariance is vacuous *because* the machine is
> permutation-equivariant over node order. That premise is now false: the input includes the registered node rank
> (§5.1), which is the node's public index, and the reach tie-break it serves is order-dependent by construction. A
> machine required to learn an order-dependent rule cannot be invariant under a change of that order.
>
> The honest position, which replaces the earlier one:
> - The machine is **not** invariant under node relabelling, and no result is reported as if it were.
> - **VACUOUS, never evidence:** any control that relabels or shuffles a quantity the machine is meant to read. Node
>   relabelling is one of these.
> - **REQUIRED, engineering only, never evidence:** that a node influences the answer **only** through its registered
>   features — its raw flags, its rank, and its label tokens if §5.1 keeps them — and never through its position in
>   the packet, its position in the file, or any part of its ref beyond the index the rank is derived from. This is
>   test S9, re-specified in §9.

### Reported only, never gated

- The ten-node development panel: 59 questions (53 reach + 6 parts), and all 53 reach questions use
  `first_direct_constituent_lexical_v1`, a rule the course NEVER teaches. It is reported as "unpractised rule"
  (`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:166-167`).
- The checkpoint check's probe results. Reported with a status field; never a gate input
  (`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:327-328`).

---

## §2 What v0.1 got wrong

One row per finding. The resolution column gives the actionable instruction, not the reasoning. Where a finding's
resolution has since been sharpened by the two interface specs, the row says so and gives the corrected form.

| ID | Problem | Resolution adopted |
|---|---|---|
| RK1 | `learner.py:271` demands a gradient on EVERY weight of `self.module`; `stage_batch` zeroes with `set_to_none=True` (`learner.py:185`), so a per-kind head that took part in no field of a batch dies with `TYPED_LEARNER_GRADIENTS` on the first such batch. Measured: `role_set` is absent from 1,150 of 1,470 batches. | Own `train_sealed_batch` in the new class. Require finiteness only on parameters where `p.grad is not None`; require at least one non-None gradient overall; register that AdamW with `set_to_none=True` applies neither update nor weight decay to a `None`-gradient parameter; log per update which parameters received gradients. |
| RK2 | `TypedCourseLearner.__init__` and `restore_checkpoint` hard-wire the ^6-only scope: scope must be exactly the three `^6` names (`learner.py:82-86`), the optimizer covers only those three (`:107-109`), the identity and checkpoint cover only `module.state_dict()` (`:111`, `:298`), and `restore_checkpoint` compares the module-level `profile()` (`:336`) which a subclass cannot override. A container escapes `TypedCourseLearner`. | New class `PointerCourseLearner`. `self.module` is ONE container holding every learned weight, the ^6 block included. Own `__init__`, `predict`, `stage_batch`, `train_sealed_batch`, `export_checkpoint`, `restore_checkpoint`, `profile`. Borrow `_tensor_loss` by calling it. NEVER call `scope_parameters` on the container (`graph_teaching/trainer.py:86-87` freezes every non-^6 weight). |
| RK3 | `FrameTokenizer.encode_text` rebuilds a 3,571-entry lookup on every call (`tokenization.py:151`), measured 0.0111 s per call. World-choice slots list 64–65 symbols each, so one packet needs about 512 encodes ≈ 5.7 s, and 8,180 training presentations blow `WORKER_DEADLINE_SECONDS` = 12,300. | Build the lookup once and tokenize each of the 230 distinct labels (244 nodes) and each declaration text once. Pin the cache digest. Get projection rows once via `encoder.export_state()`, never per packet. |
| RK4 | Bucket = job + `"-807562639912"` must match `[a-z0-9][a-z0-9-]{1,61}[a-z0-9]`, i.e. ≤ 63 characters (`practice_contract.py:226`). Measured: token `tpoint` gives 64 and fails; `tpointer` gives 66. | The study token after `cas-meta2-` must be ≤ 5 characters. Adopted token: `tpntr`, giving a 63-character bucket (`INTERFACE_SPEC_POINTER.md:40-41`). Add a length test for all three seeds (P2). |
| RK5 | `typed_practice_launch.py` hard-codes practice-only settings: `_user_data` checks the practice job pattern (`:320`), `bind_authority` calls the practice validator (`:359-360`), `reservation_plan_for` writes `task_scope` "cncm_typed_practice_001" (`:261`, silently mislabelling the ledger), `failure_statuses` (`:365`) omits the new worker's FAILED status so a failed worker is read as `REMOTE_FINISHED` and collection then demands an artifact manifest it cannot have produced, and `git_package_bytes` (`:201-203`) admits only `research/*`, `cncm/*.py` or `MATERIAL` paths, so the 18 checkpoint files fail `PRACTICE_SOURCE_MEMBER_SCOPE`. | Copy the practice provider and override `_user_data`, `bind_authority`, `reservation_plan`, `failure_statuses` and `git_package_bytes`; add the 18 checkpoint paths to the new contract's `MATERIAL`; add `"typed_pointer_launch"` to `PACKAGING_SOURCES`. Keep the `_probe()` four-constant check. |
| RK6 | A "reported, not gating" check can still fail the whole job. A missing artifact fails delivery (`typed_practice_worker.py:187-188`); an import error inside a `try` leaves `ManifestImporter.failed` set, so `attestor.snapshot()` raises `FAILED_IMPORTS` at final source verification (`typed_source_attestation.py:98`), after the money is spent. | The checkpoint-check artifact is always written with `status` of `COMPLETE` or `FAILED` INSIDE it, and every module it needs is imported at start-up, outside any `try`. |
| RK7 | `torch.use_deterministic_algorithms(True)` (`typed_practice_worker.py:252`) may reject CUDA scatter, index and embedding-backward paths, and some `linalg` solvers used for the probes. | Dense adjacency matrix multiplies, one-hot matrix multiplies instead of embedding lookups, a closed-form ridge solve. Prove with GPU smoke S1. |
| RK8 | Reusing the practice gate reader returns VOID: I1 imports `cncm.typed_practice_worker` (`evaluate_gates.py:162-165`) and I3 compares the start weights against the matched study's `initial_checkpoint` (`:182-189`), which the pointer container can never match, so any failure becomes VOID. | New gate reader at `records/typed_pointer_001/evaluate_gates.py`, outside `cncm/` and `cas_meta2/`. New I1 and a new I3 carrying the DG4 in-job evidence, in the corrected form given in the DG4 row. |
| RK9 | Any new `.py` under `cncm/` or `research/CAS_META_2_COMPOSITION/cas_meta2` between authority and launch changes `inputs_sha256` and blocks the remaining launches (`worker_contract.py:138-143`; re-validated at execute time, `typed_practice_launch.py:125-127`). Any uncommitted `.py` fails the package build with `PRACTICE_INPUT_NOT_COMMITTED`. | Keep all analysis scripts and the gate reader under `records/`. Freeze the code tree from authority until the third job has launched. Commit before packaging. |
| RK10 | `PracticeCourseLearner.restore_checkpoint` breaks on any byte change to about 15 shared files, because it compares the module-level `profile()` which transitively covers 22 files (`learner.py:336`, `:30-38`, `slots.py:50`, `course.py:70-76`). | Turn `measurements/pipeline_review/r2_restore_identity.py` into a pytest that must pass at the frozen commit, for all 9 checkpoints (P4). |
| FP1 | Copying one input flag passes the unchanged primary gate. Definition answer = `declared_whole` + focus world's kind/function; context answer = focus world's setting + declared participants (`checker.py:169-183`); the draft feeds exactly those flags. A pure flag copier scores b=10, c=0 on the 10 eligible DIRECT_READ questions (definition 5 + context 5) over 5 worlds, so p = 0.0009765625 ≤ 0.01, clears ≥ 2 kinds and ≥ 2 worlds, and the program prints LEARNS_NEW_WORLDS. | `LEARNS_NEW_WORLDS` must require the RELATIONAL-tier test (29 eligible questions over 5 worlds: correspondence 5, edge_account 5, reach 9, analogy 5, parts 5). The all-kinds `G_LEARN` becomes a reported flag, never the label. Add a test showing a flag-copy-only outcome gets no label (P12). |
| FP2 | The "relational" tier is not flag-free. An edge-free rule `parts(whole = declared_whole) = participants − whole` solves 3 of the 5 eligible held `parts` questions, and in 20 of 64 worlds "participants minus whole" equals the children of the declared whole. | Freeze a per-question flag-rule baseline BEFORE the run, and remove the flag-solved questions from the relational gate population, exactly as the 5 shortcut questions were removed. Test P13 freezes the baseline and the removal list. |
| FP3 | Running the checkpoint probe as the "first phase" would read held-back correct answers before training, which breaches the registered custody rule (`practice_contract.py:11-12`; `typed_course_worker.py:149`). | Phase A first = restore the old checkpoints and extract and seal PUBLIC vectors only, no answers. Phase B last = derive answers and fit the probes after all pointer evaluations, reloads and replays. Test P14. |
| DG1 | Training depth is not 8. Batches usedepth 1 / 2 / 4 / 8 for 380 / 370 / 340 / 380 of the 1,470 updates, so 74% of updates would run fewer than 8 rounds. The draft's "`depth` (=8, the worker's existing argument)" is wrong for training. | Fixed K = 8 shared message-passing rounds, independent of the batch's `depth`. `depth` is recorded only as a schedule coordinate. `loss_plan` checks only `depth ∈ (1,2,4,8)` (`loss_plan.py:41`), so this is a study decision, not a schema constraint — pin it in the learner profile. |
| DG2 | The reach rule is not an input. Swapping it changes the answer for 1 held, 9 trained and 1 excluded record. | Add a rule embedding to the query. `INTERFACE_SPEC_POINTER.md:78` fixes the query as `kind` plus a learned `rule` id plus the argument node ids. |
| DG3 | Some reach answers depend on the hidden alphabetical order of node names: 5/26 held, 11/71 trained, 2/10 excluded reach records, covering 2 of the 9 eligible held reach questions. A machine blind to node order cannot solve those except by symbol-order tie luck, and it trains on contradictory targets for them. | Include a world-independent **rank** among the world's sorted node refs as a node feature (`INTERFACE_SPEC_POINTER.md:79`, `:83-85`), AND register a rank-only, no-learning baseline, AND remove the questions that baseline solves from the gate population. |
| DG4 | "I3 re-derives from seed" cannot be computed by a pure-Python gate reader, because the reader cannot run torch; as written it would collapse into comparing the job to itself, which is VACUOUS. | In-job checks recorded for the reader: (a) build `matched._framework(torch, device, seed)` FIRST and check the ^6 identity against the practice start; (b) build the whole model a second time independently and require equal identity; (c) require the three seeds' identities pairwise different; (d) require the start identical with and without the checkpoint check. **SHARPENED — (a) cannot pass as worded.** `model_state_identity` digests the whole `module.state_dict()` (`learner.py:111`, `:306`), and `INTERFACE_SPEC_SHARED.md:669-677` plus `measurements/framework_probe/FINDINGS.md:49-52` correct it: digest the three `^6` tensors ON THEIR OWN — `state_identity(torch, {"left.weight": ..., "right.weight": ..., "merge.weight": ...})` — and compare THAT against the practice value. Record in `measurements.json` which of the two forms was used; they are not the same number. |
| DG5 | Held worlds pass through the trainable world encoder as wrong world-choice candidates in 1,340 of 8,180 training presentations (definition 460, context 470, analogy 410). | Declare it. Say "never the focus of a trained question", never "never seen". |
| DG6 | Prediction schema must match `loss_plan.validate_prediction` exactly — 12 fields, including two 64-hex digests. The `whole` slot's symbols follow the packet's node order (`slots.py:88`), not alias order. | Build predictions with exactly `validate_prediction`'s field set and in `slot["symbols"]` order; test it. **SHARPENED:** `INTERFACE_SPEC_SHARED.md:194-210` shows the two orders produce the SAME list on the frozen bank (0 of 64 bank worlds have declared order ≠ sorted-ref order; 0 of 70 `definition` records differ). So derive `whole` symbols from `inv["whole_refs"]` (or the packet's node order) and never from an assumption, but do not expect a difference today, and record both facts in the pointer tests. |
| DG7 | Scores must stay within `abs(score) ≤ 1000000` (`slots.py:248`) and the tensor loss and the Python `scalar_report` must agree within `rel_tol = abs_tol = 2e-5` (`learner.py:261`). A residual recurrence with no normalisation feeding dot-product pointers can break either mid-run. | RMS-normalise each round, and smoke-test it (S8). |
| DG8 | Post-run ablations are unspecified. | Run them on restored copies after the reload and replay checks; reset one component at a time to its `initial.pt` weights; put them in `EXPECTED_ARTIFACTS`; time them; write them via create-only publishing. |
| DG9 | The machine changed, so 3 new owner-signed per-job records are needed (`validate_owner` checks CANDIDATE and job). The $15 / 4 h per-job envelope is assumed, not measured; the old worker took 5,466 s and the check adds about 9–15 minutes, so the pointer cost is unknown. | Measure one pass plus one evaluation in a smoke (S7). If a job projects above about 11,000 s, go back to the owner before reserving more. |
| DG10 | Reusing `practice_contract.DESIGN` would carry false fields: `"registered_learner_unchanged": True` (`practice_contract.py:213`) and `initialization` REGISTERED_RANDOM_SAME_AS_MATCHED_STUDY; its schedule stats (`planned_slot_core_passes` 124,510, `presentation_slots` 32,280) are old-machine work counts. `expected_main_delta` (`typed_practice_worker.py:174-180`) and the check at `:361` count old per-slot core passes. | New DESIGN and a new planned-work formula keyed on packet forwards plus rounds × worlds read, tested against real counters (P11). Keep the 18 `_INHERITED` keys that are genuinely machine-independent (`practice_contract.py:196-198`); replace `purpose` and the two false fields; drop `"registered_learner_unchanged"`. |
| V1 | `base._encoding_checks` (`typed_course_worker.py:228-275`) checks the old encoder's packet and slot vectors and its 90 readout rows. The pointer machine never uses them. | Replace it with checks on the pointer INPUT READER: finite values; cached read equal to uncached read; the label/declaration token cache pinned by digest and built exactly once; and **no order-like channel other than the registered node rank**, which must itself be pinned and declared. Keep the shape — a dict published as `encoding_checks.json`, which is in `EXPECTED_ARTIFACTS` — and keep `_deadline` discipline. |
| V2 | Pre-block probes at initial / pass_01 / final all read the same frozen encoder, so the pre-block vectors are identical and computing them three times is wasted work. | Compute them ONCE. The $0 half is feasible in pure Python because `binding.py` rows and permutations are SHA-256 based. Only post-block vectors need the GPU. |
| V3 | An I3 that compares the job's recorded start identity with itself proves nothing. | Covered by the DG4 row: the in-job checks must compare against the practice study's RECORDED value, and the reader consumes the job's recorded evidence rather than re-deriving it. |
| M1 | Each practice checkpoint exists twice: `checkpoints/` and `collected/results/artifacts/`. Measured byte-identical for all 3 seeds. | Pin one path only: `receipt_<seed>/checkpoints/`. |
| M2 | The owner-facing claim "checkpoint check at no extra cost" is false. It costs about 3 course-sized passes per job: 173.8 s warm and 300.5 s cold per 564-packet evaluation, about 9–15 minutes, or $0.38–0.63 per job at $2.52/hour. | Tell the owner (done, §0.3 item 1). Ship only `initial`, `pass_01`, `final`; keep `prelast` and `retained` unshipped so the check costs what the owner was told. |
| M3 | Restoring an old checkpoint overwrites the global torch CPU, CUDA and Python RNG state (`learner.py:358-362`), and `matched._framework` re-seeds (`cncm/typed_matched_worker.py:44-46`). Nothing saves the previous state. | Phase A must finish BEFORE the pointer model is seeded and built. This ordering is part of the worker's phase order. |
| M4 | The old forward does not expose the post-block vector: `predict` returns only the slot's own logits. | The extraction code must copy the forward internals — `encode_slot` plus `recurrence.run_passes` with the same `rms`, `cast` and `zeros` — and PROVE equality by rebuilding logits from the extracted vector and comparing bit-for-bit with `restored.predict` scores in the same job. Comparing against the receipts' sealed scores is report-only. |

---

## §3 Corrections the interface specs found

Five source-level corrections. Each one is a place where the design draft or the pipeline review was overruled by the
source or by a later measurement.

**C1 — The module paths in the design draft are wrong.** The draft writes module paths as
`cas_meta2/typed_teaching/...`. Those paths do not exist under the CNCM root. The real package root is
`research/CAS_META_2_COMPOSITION/cas_meta2/`, and every module path recorded inside profiles is relative to
`research/CAS_META_2_COMPOSITION/`. Anchor: `pre_design/INTERFACE_SPEC_SHARED.md:9-35`
(the table is at `:15-23`). The identical shape applies to the worker file: `cncm/typed_pointer_worker.py` is real and
correct as written, but `cas_meta2/typed_teaching/worker_contract.py` resolves to
`research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/worker_contract.py`
(`INTERFACE_SPEC_PIPELINE.md:688-695`).

**C2 — DG4(a) as worded can never pass.** The review says the "^6 sub-block identity must equal the matched study's
`initial_checkpoint` `model_state_identity`". `model_state_identity` digests the WHOLE `module.state_dict()`
(`cas_meta2/typed_teaching/learner.py:111` and `:306`), and the pointer container holds far more than three tensors, so
a pointer run's whole-module identity cannot equal the practice value even when the ^6 weights are identical. Anchors:
`pre_design/INTERFACE_SPEC_SHARED.md:669-677` (correction), `:1287-1289` (GOTCHA 4), and
`pre_design/measurements/framework_probe/FINDINGS.md:49-52` (consequence 2). Corrected form: digest the three ^6
tensors on their own and compare that. The recorded comparison targets for the practice start are seed 20260917
`82d2037ca88593233f1176913b91f54d419ebacd23f5abc4e12bd71795feb794`, seed 20260918
`bc906a0bdd9f0b31e58653bd47ff70dfa2e40b0fbc35f36cc693c97ac3f0d753` and seed 20260919
`d437bbeb1b13a4fd31f1a158d17485821ba52da4a29f1de7b00d8ccd583598f0` (`INTERFACE_SPEC_SHARED.md:678-681`).
CONFLICT: `INTERFACE_SPEC_SHARED.md:678-681` gives the practice-start `model_state_identity` as
`82d2037ca88593233f1176913b91f54d419ebacd23f5abc4e12bd71795feb794` for seed 20260917,
`bc906a0bdd9f0b31e58653bd47ff70dfa2e40b0fbc35f36cc693c97ac3f0d753` for seed 20260918 and
`d437bbeb1b13a4fd31f1a158d17485821ba52da4a29f1de7b00d8ccd583598f0` for seed 20260919. The pin file records something
different for the last two seeds: `pre_design/contract_pins/checkpoint_pins.json:81` records the seed-20260918
`initial.pt` identity as `35081019e8b56f0c0c14aa8168262c23dab4c662c385ddcf26edc794a179b706` and line `:84` records the
seed-20260919 `initial.pt` identity as `91279389cfc22df46415dd56a26b1285fb3ef1ecd59e3aaccef553564528c12e`. Both
versions are recorded in their own files and they do not agree, so this document states both and picks neither.

RESOLVED BY EVIDENCE, 2026-09-19, without running a model: the probe's own output artifact
(`pre_design/measurements/framework_probe/probe_out.txt`) records `recorded_model_state_identity` as
`82d2037ca88593233f1176913b91f54d419ebacd23f5abc4e12bd71795feb794` for seed 20260917 (line 48),
`35081019e8b56f0c0c14aa8168262c23dab4c662c385ddcf26edc794a179b706` for seed 20260918 (line 99) and
`91279389cfc22df46415dd56a26b1285fb3ef1ecd59e3aaccef553564528c12e` for seed 20260919 (line 150), and `FINDINGS.md:25-28`
independently ties `91279389...12e` to seed 20260919. Read straight from each
`receipt_<seed>/checkpoints/initial_checkpoint.json`, the real on-disk values are the same three
(`metadata.model_state_identity`). So the pin file and the probe artifact agree with each other and with the
checkpoints, and the two seed-20260918/20260919 strings in `INTERFACE_SPEC_SHARED.md:679-680` appear to be an error in
that document. **The in-job check must use the pin-file values, not the spec's.** This resolution is a reading of
artifacts on disk, not a measurement; a later agent should still confirm it inside the job, where the check is
comparative and will fail loudly if the value is wrong.

**C3 — DG6's phrasing of the `whole` slot is contradicted by measurement.** The review says the `whole` slot follows
node order "not alias order", implying the two differ. Measured reality: for the frozen bank the two produce the SAME
list — 0 of 64 bank worlds have declared order ≠ `sorted(ref)` order, and 0 of 70 `definition` records have
`whole["symbols"] != [alias_of[ref] for ref in declared node order]`. Anchors: `INTERFACE_SPEC_SHARED.md:203-210`
(the code path is `slots.py:88` via `answers.py:74-75` and `:143`), and GOTCHA 6 at `:1299-1301`. Corrected form:
derive `whole` symbols from `inv["whole_refs"]` or the packet's node order, never from an assumption, and do not expect
a difference today.

**C4 — There are two different "encoder identity digest" values, and the prediction carries the outer one.**
`encoder.identity["identity_digest"]` = `digest(body)` (`cas_meta2/typed_teaching/encoder.py:59`). The value written
into a prediction as `encoder_identity_digest` = `source.digest(encoder.identity)`, the digest of the WHOLE identity
object including the inner digest (`cas_meta2/typed_teaching/learner.py:162`). Both are 64-hex strings and nothing fails
loudly at the point of the mistake. Anchors: `INTERFACE_SPEC_SHARED.md:859-871` and GOTCHA 5 at `:1291-1297`. Measured
values: the outer one is `15d67197fda16cb438c6b6400e78d57ea6963a5909580e1339febeddfcb49fad`, the inner one is
`a00930c51a06adc88ad0194b0439c076a2ddd7096eb8329be5ffc4d4935fc68b` (`INTERFACE_SPEC_SHARED.md:866-869`). Builder
rule: `encoder_identity_digest = digest(encoder.identity)` — never `encoder.identity["identity_digest"]`.

**C5 — The new `JOB_PATTERN` moves the model seed into capture group 1, so `parse_job` cannot be copied.**
`practice_contract.parse_job` returns `CONDITION, int(match.group(2))` (`cas_meta2/typed_teaching/practice_contract.py:77-81`,
verified on disk), and the practice pattern has two groups (source-sha fragment at group 1, model seed at group 2). The
pointer pattern has ONE group:
`r"cas-meta2-tpntr-\d{14}-([a-f0-9]{8})-m-(20260917|20260918|20260919)"` (`INTERFACE_SPEC_POINTER.md:40`). The
conditional `(20260917|...)` is inside a non-capturing bracket expression and is not a group. Anchor:
`pre_design/INTERFACE_SPEC_POINTER.md:50` requires `parse_job`, `make_config` and `validate_config` to keep "the same
shapes as practice, with the new schema/CANDIDATE", which is not achievable by copying the `group(2)` call. Corrected
form: the pointer `parse_job` returns `CONDITION, int(match.group(1))`, and `make_config`'s parameter check
(`practice_contract.py:224-225`) must test the model seed against group 1 and the source-sha fragment against the same
group. Add a unit test that the seed extracted from the pointer job string is the model seed, not the sha fragment —
otherwise `MODEL_SEED` fails at `make_config` or, worse, a wrong seed is pinned.

---

## §4 The ^6 start premise, measured

### 4.1 The measurement

`pre_design/measurements/framework_probe/FINDINGS.md` reports, for all three model seeds, that a freshly built
`cncm.typed_matched_worker._framework(torch, "cuda", seed)` reproduces the practice study's recorded start weights
NUMERICALLY but NOT bit-exactly off the AWS instance. The worst absolute per-tensor difference is
**7.450580596923828e-09** for every one of seed 20260917, 20260918 and 20260919 (`FINDINGS.md:19-23`). The key sets are
identical (`left.weight` 64x64, `merge.weight` 64x128, `right.weight` 64x64), and the first element of `right.weight`
is bit-identical at `0.11040803790092468` on both sides (`FINDINGS.md:29-33`). The probe was read-only, $0, on the
local RTX 4070, and is explicitly not claim-bearing (`FINDINGS.md:9-12`, `:57-59`).

### 4.2 The sanity check that validates the measurement

The probe does not compare ad-hoc digests. It recomputes the learner's OWN `state_identity`
(`cas_meta2/typed_teaching/learner.py:47-61`) over the checkpoint's own `model_state` and requires it to equal the
recorded `metadata.model_state_identity`. For seed 20260919 that check passes and returns
`91279389cfc22df46415dd56a26b1285fb3ef1ecd59e3aaccef553564528c12e` (`FINDINGS.md:25-28`). So the comparison is between
like and like: the probe's identity method is the same one the artifact was built with, and the "false" result is a
real numerical difference, not a bug in the comparison. `state_identity` is a byte-exact SHA-256 over the tensor bytes
(`learner.py:47-61`), so a 7.450580596923828e-09 difference makes two identities differ even though the weights are
numerically equal (`FINDINGS.md:34-35`).

On the AWS instance the build IS bit-exact: the practice study's own integrity check I0–I4 PASSED in all three seeds
(`FINDINGS.md:37-41`). The difference is a property of the laptop's build path.

### 4.3 The three consequences

**Consequence 1 — DG4 and smoke S5 are in-job-only.** Do not add a local test that asserts the fresh ^6 identity
equals the practice study's recorded start. It will fail for the wrong reason and wrongly send a builder looking for a
seed bug. The check runs inside each AWS job, exactly as DG4 already scopes it (`FINDINGS.md:45-48`).

**Consequence 2 — the identity digest must cover the ^6 tensors only.** See §3 C2. Digest
`state_identity(torch, {"left.weight": ..., "right.weight": ..., "merge.weight": ...})` and compare that against the
practice start. Never compare the container's whole-module identity (`FINDINGS.md:49-52`).

**Consequence 3 — a local smoke may still assert the reproducible parts.** These are safe locally and were confirmed
by the probe: building `_framework` twice with the same seed gives identical weights (`REBUILD_IDENTICAL` true in an
earlier run of the probe), and the three seeds' builds are pairwise different (`FINDINGS.md:53-55`). Those are the
local half of DG4(b) and DG4(c). DG4(d) — identical start with and without the checkpoint check — is an ordering
property of the worker and belongs in smoke S5 on the instance, but the ordering rule itself (phase A before seeding)
can be asserted locally at the code level.

---

## §5 The design

This section supersedes v0.1 §2 and §3. It folds in every DG fix. It does not restate the API surface: that is fixed in
`pre_design/INTERFACE_SPEC_POINTER.md`, and this section references it rather than repeating it.

### 5.1 The input reading

What is read. From the public packet ONLY, and only these facts (`INTERFACE_SPEC_POINTER.md:59-88`,
`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:187-192`):

- **The worlds.** The focus world read as a graph. The correspondence target world. For a world-choice slot, every
  world the slot lists. Each world is a set of nodes plus directed `contains` edges.
- **Per node, its own raw flags only**: `is_declared_whole`; `is_participant` with rank 1..3; `is_whole_argument`;
  `is_part_argument`. **`is_primary_label` and its rank 1..3 are REMOVED.** LK5 measured that `is primary label` is
  equivalent to `is participant` in **64 of 64** worlds: `primary_labels == participants` in 64 of 64, and
  `participants_basis` is `PRIMARY_AUTHORED_LABELS_FIRST_THREE` in 64 of 64
  (`DESIGN_REVIEW_LEAKS_LENS.md` LK5; `measurements/leaks_review/lk1_answer_carriers_out.txt` Part H). So one of the
  two flags is redundant and must go. **The flag removed is `is_primary_label` and its rank**, and the one kept is
  `is_participant` with its rank, because `is_participant` is the flag the checker's own `context` answer is derived
  from (`checker.py:178-183`, `participants = sorted(focus["declarations"]["participants"])`), so the kept flag is the
  one the answer function actually reads. The learnability lens reaches the same instruction from its own side:
  *"Drop `primary rank` and pass one participant-rank feature; do not allocate input width for a duplicated flag"*
  (its `context` section).
- **Per node, its rank** among the world's sorted node refs (`INTERFACE_SPEC_POINTER.md:79`) is **EXCLUDED**. No
  order-derived node feature reaches the input. The decision, its reasoning and its numbers are recorded below.
- **Per world**, its domain-text token ids, plus the flags `is_focus` and `is_target`.
- **The query**: `kind` as an 8-way learned id; `rule` as a learned id (DG2: swapping the reach rule changes 11
  answers); the argument node ids where present.
- **For `role_set` only**: the focal excerpt as a frozen bag of token ids, position-free.

> **RESOLVED 2026-09-19 — the rank feature is EXCLUDED, and the order-dependent questions are removed instead. This
> is the final decision, and it supersedes both blocks that stood here: the "the rank IS the node's public alias"
> ruling and the "🔴 REOPENED" case for rank are kept below as the historical record.**
>
> **The reasoning, and the numbers.**
>
> The leaks lens measured the rule *"node rank == the alphabetically last ref"* — **LK7**, reading **only** the rank
> flag and **no adjacency** — as solving **5 of the 45** eligible held questions by itself: `parts` **1 of 5** and
> `reach` **4 of 9**. That is the largest single-flag score of any kind outside the DIRECT_READ pair
> (`DESIGN_REVIEW_LEAKS_LENS.md` LK7; `measurements/leaks_review/lk6_gate_population_out.txt:30` prints the same 5 as
> `{'parts': 1, 'reach': 4}`). The lens's stated preference is to **prefer the removal option so the vacuity law
> survives** (`DESIGN_REVIEW_LEAKS_LENS.md` LK6).
>
> The learnability lens reached the same fork from the hidden-ref-order side: rule-1 `reach`
> (`first_direct_constituent_lexical_v1`) depends on the hidden alphabetical order of node references for **5 held,
> 11 trained and 2 excluded** reach records, and its instruction is to remove those records **or** add the rank
> feature — with the remark that removing is safer, because the rank feature re-introduces exactly the "answer
> expressed by a hidden positional index" channel whose absence is the point of the pointer machine
> (`DESIGN_REVIEW_LEARNABILITY_LENS.md` LB1).
>
> **The arithmetic that settles it** (`REVIEW_SYNTHESIS.md` §10.2; `lk6_gate_population_out.txt:43-53`): adopting rank
> would take the population from **23 to 18** (29 − 11 instead of 29 − 6) and raise the required improvement share
> from **7/23 = 0.3043** to **7/18 = 0.3889**. It would also **withdraw this draft's own vacuity paragraph**, since
> rank *is* the node alias at **244 of 244** refs — every node ref's position in the sorted list equals its own
> stored index.
>
> **DECISION. The rank feature is EXCLUDED and the order-dependent questions are removed instead.** The rank-last
> pointing rule stays registered as a no-learning baseline even though rank is not an input, because it is the rule
> those questions were solved by and the removal list must be reproducible from the contract. See §6.5 for the
> removal table and the exact question ids.
>
> **Every other place in this document that still describes the rank as an input is superseded by this decision, and
> each is left in place unchanged because this fold-in is surgical.** They are, in full:
>
> 1. the `VACUOUS` correction in §1, which rests on the input carrying "the registered node rank" and on the machine
>    therefore being deliberately not invariant under node relabelling;
> 2. the `DG3` row of §2, whose adopted resolution is "include a world-independent **rank** among the world's sorted
>    node refs as a node feature ..., AND register a rank-only, no-learning baseline, AND remove the questions that
>    baseline solves from the gate population" — the **removal half** of that resolution is what is adopted here, the
>    feature half is not;
> 3. the two earlier rank blocks of §5.1, now kept **below** this one as the historical record;
> 4. the rank bullet inside §5.1's "What is NEVER read" paragraph, which has been corrected in place;
> 5. the `PENDING` line that names lens A at the end of §5.1, which is now answered and has been updated in place;
> 6. the `**The rank-only baseline's solved set.**` bullet in §6.4 — the solved set has now been computed and is
>    frozen in §6.5;
> 7. **four items in §9**: the `pointer_inputs.py` row of the build table, which lists "the registered node rank"
>    among what the reader returns; the frozen-protocol row (`docs/CNCM_TYPED_POINTER_STUDY_v0.1.md`), which lists
>    "the rank feature and its baseline" among what the protocol carries; test `P10`, which reads "every order-like
>    channel **other than** the registered node rank"; and GPU smoke `S9`, which reads "no order-like channel beyond
>    the registered rank — a node must influence the answer only through its declared features (raw flags, rank, and
>    its label tokens if kept)". All four must read "no order-like channel at all" when the file is built. They are
>    not edited here because §9's changes in this fold-in are confined to the build-status marks; the row-7 reference
>    to "the three decisions of §0.3" has, however, been corrected in place, because §0.3 now records five.
>
> The decision above governs. §6.5 and §6.6 record what §6.4's rank items were waiting for.

> **HISTORICAL RECORD — the case FOR rank, as it stood earlier on 2026-09-19. It is retained, not deleted, and it is
> no longer the decision.**
>
> **(a) The ruling that rank IS the node's public alias.** The leaks lens measured that `checker._nodes =
> sorted(node['ref'])` (`checker.py:72-73`) and `slots.alias_table` N0..N9 are that same sorted list
> (`slots.py:55-60`), and that **244 of 244** node refs have their position in the sorted list equal to their own
> stored index — `n<i>` is position `i`, for every node in the bank
> (`measurements/leaks_review/lk1_answer_carriers_out.txt` Part H). So the rank would not have been new information
> smuggled past an exclusion: it is the node's own public identifier, and the order the checker's reach tie-break uses
> cannot be supplied without it, because the order and the index are the same fact.
>
> Three reasons were given for including it:
> 1. The reach answer space is literally `VIA_<node>`, so any machine that can point at a node already carries node
>    identity. Withholding rank would not restore symmetry; it would only remove the ordering.
> 2. The tie-break decides **2 of the 9** eligible held `reach` questions, and without the feature the machine trains
>    on contradictory targets for **5/26** held and **11/71** trained reach records.
> 3. The alternative buys nothing: those 2 questions leave the gate population under `DG3` whether rank is in or out.
>    It only costs the machine the one genuinely transferable skill the order carries — *when two nodes tie, take the
>    lower rank*.
>
> That ruling also **WITHDREW** the earlier formulation "NO node alias index", registered a rank-only, no-learning
> baseline, and removed the questions that baseline solves from the gate population before the run
> (`INTERFACE_SPEC_POINTER.md:83-85`).
>
> **(b) The "🔴 REOPENED" case, and why it won.** The leaks lens's single-flag table
> (`measurements/leaks_review/lk2_single_flag_out.txt` line 89-94) measured rule **R10**, *"node rank == the
> alphabetically last ref"*, as solving **4 of the 9** eligible held `reach` questions (and 10 of 26 held reach
> records), which made the two options no longer close:
>
> | | Gate population | Training signal |
> |---|---|---|
> | **rank IN** | `reach` loses up to 4 to R10 **and** 2 to DG3 (the overlap is unmeasured) + `analogy` 5 + `correspondence` 5 → **as low as 13–15** | the order-dependent reach targets stop being contradictory (5/26 held, 11/71 trained) |
> | **rank OUT** | `reach` loses 2 to DG3 + `analogy` 5 + `correspondence` 5 → **17** | 11 of 71 trained `reach` records keep contradictory targets |
>
> Both options clear the floor of `b = 7` on paper, but 17 left materially more headroom than 13–15, and the
> questions rank would remove are exactly the ones that do **not** require following links between a world's parts —
> which is the owner's own stated criterion for the tier. The counter-argument was training noise on one kind. The
> state recorded at the time was that the decision was NOT settled and waited on lens A's authoritative
> required-removals table; lens A has since reported, and the resolution is the one at the top of this block.

What is NEVER read: `supports`, `cue`, `instruction`, and any answer or target. **No order-like channel is read at
all.** The node rank is excluded by the decision above, so these are all excluded: a node's rank among the world's
sorted refs, its position in the packet, its position in the file, and any part of its ref. Test S9 is the engineering
check for exactly that, and it is never evidence of learning.

The directed `contains` adjacency is given ONLY to message passing. It never reaches a readout head
(`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:190-191`). This is what makes the answer depend on relations among
input elements rather than on one copied flag.

The reader is pure, deterministic and digestible: `label_cache(root)`, `read_packet(packet)`, `input_digest(reading)`,
`slot_readings(reading, slots)` (`INTERFACE_SPEC_POINTER.md:64-70`). The label cache is built ONCE — 230 distinct
labels, 244 nodes — and its digest is pinned, which is the RK3 resolution.

**Reach rule embedding.** The query carries a learned `rule` id. `checker.py:115-151` implements BFS over sorted
neighbours and has TWO rules: `bfs_immediate_predecessor_lexical_v1`, used by all 59 course reach records, and
`first_direct_constituent_lexical_v1`, used by all 53 reach questions of the ten-node development panel
(`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:164-167`). The development panel therefore exercises a rule the
course never teaches; it is reported as "unpractised rule" and is never gated on.

**The node rank feature, and the removal that replaces it.** The rank feature is **excluded**. The DG3 resolution is
adopted in its **removal** form instead: the questions the rank-last pointing rule solves are removed from the gate
population before the run, so a shortcut-solved question can never be counted as learning
(`REVIEW_SYNTHESIS.md` §10.2, `lk6_gate_population_out.txt:30`, `:43-47`). Feature: out. Baseline: still registered,
so the removal list is reproducible. Removal: applied. The table and the question ids are in §6.5.

CONFLICT: `REVIEW_SYNTHESIS.md` §10.2 requires "The `node_rank_feature` flag in the contract must be set False",
while the pointer contract on disk still records the opposite: `pointer_contract.py` carries
`"node_rank_feature": True` together with
`"node_rank_decision_status": "REGISTERED_INCLUDED_REOPENED_AT_6cb0b348_PENDING_LENS_A"`, and a comment above it saying
`pointer_inputs.py` "must not be built on either branch until lens A reports". Lens A has now reported and the
decision above is final, so the contract flag must be set False; the two are not yet reconciled. (Observed in the
working tree at HEAD `d5e1dc1b`.)

**RESOLVED 2026-09-19 — node LABEL words are DROPPED from the input.** The question was held open pending lens B, and
lens B has now reported. Four independent measurements agree, and one of them is decisive on its own:

1. **No answer rule can use them.** `checker.py:97` says so in terms, as the docstring of the isomorphism enumerator:
   *"Enumerate every mapping; node labels, root choice and archetypes do not vote."* That is the only mention of a
   label anywhere in the checker.
2. **They are a memorisation channel for held worlds.** All **20 of 20** held-world node labels occur somewhere in
   trained record text — 7,160 (label, trained record) occurrences — and the reader would embed a held-world label
   **30,420** times across the schedule (`measurements/learnability_review/lb10_labels_out.txt`).
3. **They carry no signal for the kinds that matter.** The paired worlds of a `correspondence` question share **no**
   node label (0 of 20 held, 0 of 54 trained, 0 of 14 excluded), and **123 of 123** correct `analogy` candidates have
   zero label overlap with the focus world (`lb14_order_and_labels_out.txt`).
4. **Cost is not the argument, but it agrees.** Uncached, the full run needs 284,900 label encodes at a measured
   0.0219 s per call = **6,225 s** of a 12,300 s deadline; a 230-entry cache costs 5.0 s. So caching would fix the
   cost — which is why the cost alone would not have justified dropping them. The leak is what justifies it.

So the node carries its raw flags and its adjacency — and no words, and no rank. This also removes the
tokenizer-time risk from the input path entirely: only the 136 distinct declaration strings and the `role_set`
excerpt remain to be tokenised, and both are cached once.

**Lens A (leaks/shortcuts/vacuity) has now reported, and the removal list is complete.** The frozen removal table,
its counts and the exact question ids are in §6.5; its findings are in §7. The leaks lens also supplied the
per-question `typed-query-…` ids that the contract's frozen removal list needs, printed by
`lk6_gate_population_out.txt:60-71`.

### 5.2 The network

**The container.** `PointerCourseLearner`, a NEW class. `self.module` is ONE `nn.Module` holding EVERY learned weight,
the registered `^6` block included. `scope_parameters` is NEVER called on it, because
`graph_teaching/trainer.py:86-87` would set `requires_grad_(False)` on every non-^6 weight. The class owns its own
`__init__`, `predict`, `stage_batch`, `train_sealed_batch`, `export_checkpoint`, `restore_checkpoint` and `profile`. It
borrows `TypedCourseLearner._tensor_loss` by CALLING it, which works because that method reads only `self.torch`
(`INTERFACE_SPEC_SHARED.md:441-444`). It keeps a frozen typed encoder alive on `self.encoder` even though it never
encodes a packet, so `base._state`, `_check_state` and `export_state` keep working
(`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:255-256`, `INTERFACE_SPEC_SHARED.md:553-577`).

**The ^6 block.** Taken from `cncm.typed_matched_worker._framework(torch, device, seed)`
(`cncm/typed_matched_worker.py:43-48`), built FIRST. The three parameter names in the container must be exactly
`left.weight` 64x64, `right.weight` 64x64, `merge.weight` 64x128 (`learner.py:25-26`). The registered contract id is
`cas.cjt.operation.^6.decompose/0.2` (`research/CAS_CJT_TRANSFORMER_v0_2/cas_cjt/neural.py:74`,
`cas_meta2/graph_teaching/real_framework.py:23`).

**K = 8 shared rounds.** Fixed at 8 rounds of message passing with SHARED weights, regardless of the batch's `depth`
field. This is the DG1 resolution. `depth` is recorded only as a schedule coordinate. The update rule is
`h ← h + ^6(W_self h + W_down Σ parents + W_up Σ children)`, with `^6` the registered `_DecomposeTransform` used
unchanged as the update function. The block's forward is `torch.cat((torch.tanh(self.left(value)),
torch.tanh(self.right(value))), dim=-1)` then `self.merge(...)` (`cas_cjt/neural.py:124-126`), called on a 2-D tensor
in the learner path (`learner.py:140-141`).

**K is pinned at 8, and the learner is FORBIDDEN to condition on `depth`.** Training batches used depths 1 / 2 / 4 / 8
(for 380 / 370 / 340 / 380 of the 1,470 updates) while **every** evaluation uses depth 8
(`INTERFACE_SPEC_PIPELINE.md:248`). A learner that read the batch's `depth` field could therefore gain from p0 to p10
by extrapolating depth rather than by learning, and that gain would be indistinguishable in the label. LK18 states the
instruction plainly: *"Fix K = 8 (DG1) and register that the learner must not condition on `depth`, or the p0-to-p10
gain can include depth extrapolation rather than learning"* (`DESIGN_REVIEW_LEAKS_LENS.md` LK18,
`REVIEW_SYNTHESIS.md` §10.3). So K = 8 is a fixed constant of the pointer learner, `depth` is recorded only as a
schedule coordinate and is never an input to any head, and both facts are pinned in the learner profile.

**The round count and the normalisation placement are chosen from a measured table, not inherited.** The learnability
lens measured the edge / non-edge separation of the recurrence and found it depends on where the RMS normalisation
sits: with `rms_after=output` it peaks at **4 rounds** (mean cosine of EDGE pairs **0.585565** against NON-edge pairs
**0.197146**, a gap of **0.388418**), and with `rms_after=none` it keeps growing to **8 rounds** (gap **0.406388**)
(`REVIEW_SYNTHESIS.md` §5.5; `DESIGN_REVIEW_LEARNABILITY_LENS.md` `edge_account`). The same lens measured that **3
rounds suffice** for `reach` rule 2, because every bank world has at most 4 nodes, at most 4 edges and a maximum
shortest-path length of 3, so K = 8 is generous there by 5 rounds. So K = 4 with `rms_after=output` and K = 8 with
`rms_after=none` are the two named candidates, and both the round count and the normalisation placement are to be
chosen from that table rather than inherited.

**Dense matmuls, one-hot, no embedding lookups.** Under `torch.use_deterministic_algorithms(True)`
(`cncm/typed_practice_worker.py:252`) the message passing uses dense adjacency matrix multiplies over the small world
graphs and one-hot matrix multiplies instead of embedding lookups. The probes use a closed-form ridge solve. This is
the RK7 resolution; smoke S1 proves it.

**RMS normalisation every round.** Each round is RMS-normalised before it feeds the next. This is the DG7 resolution:
without it, a residual recurrence feeding dot-product pointers can push `|score|` past 1e6 (`slots.py:248`) or break
the 2e-5 tensor/Python loss agreement (`learner.py:261`). Smoke S8 proves it.

**Gradient discipline.** The learner's own `train_sealed_batch` requires finiteness only on parameters where
`p.grad is not None`, requires at least one non-None gradient overall, and records that AdamW with
`zero_grad(set_to_none=True)` applies neither an update nor a weight-decay term to a `None`-gradient parameter for
that step. It logs per update which parameters received gradients. This is the RK1 resolution.

**The heads.** Every head sees states and the query. No head sees raw adjacency.

| head | slots it scores | form |
|---|---|---|
| node yes/no | each node of the focus world: `parts` `node`, `context` `participant` | 2 logits from an MLP over `[h_v, q]` |
| edge yes/no | each ordered pair `a→b` including self-pairs: `edge_account` `edge` | 2 logits from an MLP over `[h_a, h_b, q]` |
| role yes/no | the 6 fixed roles: `role_set` `role` | 2 logits from an MLP over `[q, E_role[r]]`; roles are fixed world-independent categories |
| node choice | `definition` `whole`; `reach` `VIA_Nk`; `correspondence` `mapping_target` | `logit(v) = <W_p q_slot, h_v>`, with `q_slot = q` (+ `h_source` for correspondence) |
| fixed-option choice | `reach` `ABSENT`/`DIRECT`; `analogy` `NO_MATCH`; `correspondence` `mode` | learned option vectors scored against `q`; for the correspondence mode also `g_F` and `g_T` |
| world choice | `definition` `kind_ref`/`function_ref`; `context` `setting_ref`; `analogy` `world_id` | `logit(w) = <W_w [q; g_F], g_w + flag features>` |

The head set is `OPEN:` on lens B's expressivity table (`INTERFACE_SPEC_POINTER.md:110-113`). What is already fixed:
K = 8, RMS each round, dense and one-hot matmuls, deterministic mode.

> **🔴 MEASURED 2026-09-19 — the world-choice row above is a learning risk, and K = 8 is not yet justified.**
> `measurements/learnability_review/lb16_pooling_resolution_out.txt` and `lb17_pool_gradient_out.txt` measured what the
> mean-pooled `g_w` actually contains.
>
> The message passing works at the **node** level. Mean cosine between node states, `rms_after=output`: EDGE pairs
> 0.585565 against NON-edge pairs 0.197146 at four rounds — a gap of **0.388418**; two rounds already separate them.
> So the recurrence does encode the wiring.
>
> **Mean pooling then destroys it.** With random per-node features, two worlds with *different* shapes sit
> **0.831003** apart while two draws of the *same* shape sit **1.213181** apart — a ratio of **0.68**, so different
> shapes are closer together than same-shape samples. Nearest-centroid recovers **8–13 of 123**. The pure-shape signal
> in `g_w` is **3–8 %** of its magnitude, rising only to **13–16 %** with the three real flag dimensions.
>
> That matters because `analogy world_id` and `correspondence`'s target selection are world-choice slots scored
> against `g_w`, and those are the two kinds that are otherwise the clean tests. `lb18_analogy_structure_out.txt`
> sharpens it: **all 17 held analogy records require shape AND domain together** (`correct set == isomorphic AND
> different domain` in 17 of 17), and a shape test alone leaves **24** candidates it cannot reject. So analogy needs
> the machine to read shape and combine it with the domain word, and shape is the half this readout is weak at.
>
> **Claim state, corrected 2026-09-19.** MEASURED in a numpy simulation of this recurrence with **untrained** weights;
> ANALYSED from the gradient path (`lb17`: `d g_w / d h_v^{k} = (1/N) · d h_v^{K} / d h_v^{k}`, with the map's
> spectral norm measured near 1 by LB13, so the pooled vector receives each node's own local update — its own feature
> plus a normalised neighbour sum — dominated by features rather than topology). **NOT measured on a trained model:
> no pointer machine exists yet.** So this is a design risk with a stated mechanism, not a verdict, and the sentence
> *"a readout that cannot see shape cannot learn shape, however long it trains"* is withdrawn as an overstatement.
> The test in point 4 below is what would settle it.
>
> Four changes follow, none of which touch the gate:
> 1. score structural answers at the node level, never after pooling — the `correspondence` `mapping_target` head must
>    read `h_v` and never `g_w`;
> 2. replace mean pooling with a readout that keeps more of the wiring — over 3–4 nodes, candidate options that cost
>    almost nothing are concatenating the **rank-sorted** node states (rank is already a registered input, so the sort
>    is well defined), a sum of outer products, or attention pooling with a learned query;
> 3. choose K and the normalisation placement from the measured table rather than by inheritance — `rms_after=output`
>    peaks at **K = 4** (gap 0.388418) while `rms_after=none` keeps growing to **K = 8** (gap 0.406388);
> 4. add a local, $0 smoke test that asserts the readout separates two *different* shapes by more than two draws of
>    the *same* shape. **Today it does not**, and that test is the guard against this failure returning unnoticed.

**Output.** The same `{slot_id: {symbol: logit}}` shape the old learner produced, one logit for EVERY declared symbol
in `slot["symbols"]` order, so `slots.score_decisions`, `slots.assemble_answer`, the private checker, the
seal-before-targets discipline and the scoring all stay unchanged. World-choice slots must carry all 64 `W0..W63`
logits; a head that emits only a chosen symbol fails `TYPED_SLOT_SCORE_SYMBOLS` before any loss is computed
(`INTERFACE_SPEC_SHARED.md:1354-1356`). The prediction dict carries exactly `loss_plan.validate_prediction`'s
12-field set (`loss_plan.py:35-55`). This is the DG6 resolution.

**The CAS reading, unchanged.** The world encoder is `^6` Male — "An Idea impregnated with another Idea, the Ideas an
Idea is composed of" — applied along the `contains` composition graph, with decomposition carried by the registered
`^6` operation. No new CAS primitive is claimed. This is an engineering architecture that reuses the registered `^6`
block (`DESIGN_DRAFT_v0.1.md:59-62`). The block itself is byte-identical to the practice study's registered block; only
what surrounds it is new. PENDING on the second review: no independent CAS-semantics review of the container has been
done, and the CAS reading is an interpretation of the architecture, not a measured property.

### 5.3 The study design

Same course, same frozen hold-out, same schedule, same seeds, same evaluation points
(`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:198-201`). Every one of these is reused BY IMPORT so the hold-out
stays byte-identical to the practice study (`INTERFACE_SPEC_POINTER.md:52-57`):

| element | value | source |
|---|---|---|
| held records | 127 | `hand-off §4`; `INTERFACE_SPEC_PIPELINE.md:1497` |
| held questions | 50 | `INTERFACE_SPEC_PIPELINE.md:1445` |
| held worlds | 5, twin-free | `hand-off §4`; `practice_contract.HELD_WORLDS` |
| excluded records | 79 | `INTERFACE_SPEC_PIPELINE.md:1498` |
| trained records | 358 | `hand-off §4` |
| main updates | 1,470 (10 passes × 147) | `INTERFACE_SPEC_PIPELINE.md:287` |
| interference | 16 batches | `INTERFACE_SPEC_PIPELINE.md:104` |
| replays | 2 | `INTERFACE_SPEC_PIPELINE.md:109` |
| total expected updates | 1,488 | `typed_practice_launch.py:50` |
| checkpoints | 0, 1, 2, 4, 6, 8, 10 | `typed_practice_worker.py:43` |
| full-course checkpoints | 0, 1, 10 | `typed_practice_worker.py:44` |
| model seeds | 20260917, 20260918, 20260919 | `matched_contract.py:22` |
| condition | `MIXED_SAME_ITEMS` | `INTERFACE_SPEC_SHARED.md:1159` |
| source seed | 101 | `matched_contract.py:23` |
| encoder seed | 20260916 | `matched_contract.py:23` |
| instance | g7.2xlarge, RTX PRO 4500, us-west-2 | `hand-off §9` |
| reservation | `"15.00"` per job, `"45.00"` total cap | `typed_practice_launch.py:48`; `prepare_study.py:28` |
| evaluation depth | 8 for every evaluation | `INTERFACE_SPEC_PIPELINE.md:248` |
| development panel | 59 packets, ten-node worlds | `matched_contract.py:203` |

Reused unchanged by import and pinned by test P1: `split`, `held_back_questions`, `practice_schedule`,
`interference_batches`, `retention_packets`, `development_packets`, `load_material`, `public_packets`. Their frozen
digests are held `668e6ce73c426d1fcf8f2391e1a08d90c045ffb37fba95fc64e2658f5369ab1d`, excluded
`b82108e14554a9fe746a7cfcb1e2cb181a99a3019dc39a3596805f10934c2621`, batches
`daf95831dd6f054f0395e9a868c513650982bd1912247adc698ca067433bc857` (`INTERFACE_SPEC_POINTER.md:54-57`).

**The tiers, fixed before the run** (`INTERFACE_SPEC_POINTER.md:45`, `records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:249-250`):

- DIRECT_READ = `definition`, `context`. The answer is one input flag or the focus marker.
- RELATIONAL = `parts`, `edge_account`, `reach`, `correspondence`, `analogy`. The answer needs relations among input
  elements, not one input flag.
- TEXT = `role_set`.

The primary label is keyed on RELATIONAL (FP1, owner-confirmed). Every tier and every kind is reported.

**The checkpoint check, in its two phases** (`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:317-329`,
`INTERFACE_SPEC_POINTER.md:121-138`):

- **$0 half.** Already DONE. It is the recorded pre-block result and need not be recomputed on the GPU, because the
  encoder is frozen and `binding.py` rows and permutations are SHA-256 based, so the pre-block vectors are identical
  at every checkpoint (V2). This is `INPUT_DEFECT_MEASUREMENT.md` plus its independent reproduction.
- **Phase A, first.** Restore that seed's practice checkpoints `initial`, `pass_01`, `final` with
  `PracticeCourseLearner.restore_checkpoint`. For every slot of all 564 records compute the post-block vector by
  copying the forward internals. Verify by rebuilding logits bit-for-bit against `restored.predict` (M4). Seal the
  vectors create-only. Phase A reads PUBLIC vectors only and derives NO answer (FP3). It must finish BEFORE the pointer
  model is seeded or built, because restoring overwrites all three global RNG streams (M3,
  `learner.py:358-362`).
- **Phase B, last.** After all pointer evaluations, reloads and replays: derive answers and fit the trained-world →
  held-world ridge probe per kind, on the post-block vectors at each checkpoint, and on the pointer machine's node
  states at initial / pass_01 / final. Report only; the artifact always carries a `status` field.

Cost of the check, told to the owner and accepted: about 9–15 minutes per job, about $0.38–$0.63 per job (M2).

#### 5.3.1 Training length and composition

Three things about how long the study trains and how the schedule is composed are recorded here, because the owner's
second decision (§0.3 item 5) is "Stratify AND train longer (Recommended)" and both halves have measured numbers
behind them.

**The practice run stopped while the neurons were still learning.** Its mean raw batch loss fell monotonically at
every one of its ten passes, from **1.2879780873** at pass 1 to **0.3981766156** at pass 10, and the run used
**5,465.811116 s of a 12,300 s deadline — 44.4 % of its budget — and stopped anyway** (`LEARNING_LEVERS.md` §1, read
from `records/typed_practice_001/receipt_<seed>/checkpoints/worker_report.json`, seed 20260917). Ten passes was a
protocol choice, not convergence. So "train longer" is the cheaper half of the decision and the one the receipts
already justify.

**The registered ceiling that made longer training impossible has been raised deliberately.** The practice ceiling
`LEARNER_MAX_UPDATES_CEILING = 2048` (`practice_contract.py:61`), enforced as `main_updates + 16 <= 2048`
(`practice_contract.py:171`, `PRACTICE_UPDATE_BOUND`), capped any study at **13 passes** (1,911 + 16 = 1,927); 14
passes would need 2,074 and would be refused (`LEARNING_LEVERS.md` §2). The pointer study is a new candidate and now
carries its own limit: **`MAX_PASSES_PERMITTED = 24`** and a ceiling of **3544** (24 × 147 + 16), which permits 24
passes and refuses 25 (`pointer_contract.py:112-113`). The change is deliberate and recorded, because the ceiling is
part of the admission contract.

**The schedule is stratified, so every kind appears in every update.** As-is, at 147 updates per pass, each kind is
ABSENT from a large share of updates: `role_set` from **115 of 147**, `analogy` from **112**, `context` from **107**,
`definition` from **105**, `edge_account` from **95**, `correspondence` from **67**, `parts` from **63** and `reach`
from **40** — so a `role_set` head received a gradient in only 32 of 147 updates (`REVIEW_SYNTHESIS.md` §4.7, measured
by `lb11_economics.py`). Stratifying so every kind appears in every update costs **+43.8 %** presentations —
**818 → 1176** per pass — at the same **147** updates per pass. The lens's literal reading of its own instruction
(about 10 × 470 updates) would cost **+359.7 %** and its ten passes would need **4,716** updates, which is above the
raised ceiling of **3,544**, so it is not affordable as literally stated (`REVIEW_SYNTHESIS.md` §4.7). The stratified
schedule is the adopted one, and `STRATIFIED` is True in the contract.

**`PASSES` is set from the smoke job's measured per-update cost, not guessed.** The pass count is the study's own
parameter above the practice study's ten, and it is fixed from the cost measured in the AWS smoke job (S7/S10, §9.1),
which has not been run. At the old machine's measured rate of about **0.6682 s per presentation**, the stratified
schedule's extra **358** presentations per pass cost roughly **+2,392 s** over ten passes, which fits the 12,300 s
deadline against the practice run's **5,465.811116 s** — but the pointer machine's own rate is unmeasured, so that
figure is a projection, not a reading. **The same smoke measurement must re-check `MAX_CORE_CALLS`**, because the
pointer machine calls the registered `^6` block once per node per round, so its core-call count is not the practice
study's (`pointer_contract.py:105-114`). And per DG9, if a job projects above about **11,000 s** the owner must
approve a larger reservation first (§10).

PENDING on the second review: the whole design of §5 is reviewed once, by one lens. The hand-off requires a SECOND full
adversarial review of the BUILT code before any spend, because the practice study's second review found three leaks the
first redesign created (`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:271-273`). Nothing in §5 is frozen until
that review happens.

---

## §6 The gate

### 6.1 The owner-confirmed label

The primary label is keyed on the RELATIONAL tier. Owner answer 2026-09-19, verbatim: *"Yes — require the relational
kinds."* (`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:388-391`). Three labels only, and the printed label IS the
claim status: `LEARNS_NEW_WORLDS` / `NO_TRANSFER_TO_NEW_WORLDS` / `VOID`
(`INTERFACE_SPEC_PIPELINE.md:1411-1418`).

`LEARNS_NEW_WORLDS` requires, per seed: an exact one-sided binomial test on the discordant question pairs with
`b > c` and `p ≤ 0.01`; gains in ≥ 2 kinds; gains in ≥ 2 held worlds; and ALL THREE seeds must pass
(`INTERFACE_SPEC_POINTER.md:163-167`). The all-kinds result is reported as a flag, never as the label.

### 6.2 The exact arithmetic, with the verified numbers

The test is `binomial_upper_tail(b, n) = Fraction(sum(comb(n, k) for k in range(b, n + 1)), 2 ** n)` — exact rational
arithmetic, never floating point (`INTERFACE_SPEC_PIPELINE.md:1319-1329`). `n = b + c`, the number of discordant
questions; ties are excluded from both.

- `ALPHA = Fraction(1, 100)`, `MIN_IMPROVED_KINDS = 2`, `MIN_IMPROVED_WORLDS = 2`
  (`INTERFACE_SPEC_PIPELINE.md:1313-1317`).
- **Smallest passing `b` with `c = 0` is 7**, because `2 ** -7 = 0.0078125 ≤ 0.01`. `b = 6` gives
  `1/64 = 0.015625 > 0.01` and fails (`INTERFACE_SPEC_PIPELINE.md:1361-1364`,
  `records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:251-252`).
- A question counts as correct ONLY if every one of its records is correct — `question_outcomes` requires
  `all(record_correct[r] for r in records)` (`INTERFACE_SPEC_PIPELINE.md:1366-1368`).
- Unanimity, not pooling: each seed is tested on its own and `all(...)` requires all three
  (`INTERFACE_SPEC_PIPELINE.md:1385-1387`).

**The verified population inputs:**

| quantity | value | source |
|---|---|---|
| held-back questions | 50 | `INTERFACE_SPEC_PIPELINE.md:1445` |
| eligible after the 5 shortcut removals | 45 | `INTERFACE_SPEC_PIPELINE.md:1474` |
| shortcut removals | 5, all held `reach` whose admissible set contains the direct answer; the frozen `reach` shortcut is exactly `{"state": "DIRECT", "via": null}` | `INTERFACE_SPEC_PIPELINE.md:1475-1479` |
| eligible DIRECT_READ | 10 (definition 5 + context 5) | `INTERFACE_SPEC_PIPELINE.md:1483` |
| eligible RELATIONAL | 29 (correspondence 5, edge_account 5, reach 9, analogy 5, parts 5) | `INTERFACE_SPEC_PIPELINE.md:1483` |
| eligible TEXT | 6 | `INTERFACE_SPEC_PIPELINE.md:1485-1489`, marked UNCERTAIN there |
| relational per held world | 6, 5, 6, 5, 7 | `INTERFACE_SPEC_POINTER.md:46` |
| FP2 flag-rule removal | solves 3 of 5 eligible held `parts` | `INTERFACE_SPEC_POINTER.md:46` |
| DG3 node-order removal | covers 2 of 9 eligible held `reach` | `INTERFACE_SPEC_POINTER.md:46` |

**Arithmetic with those verified numbers.** 10 + 29 + 6 = 45, which matches the eligible count.

**CORRECTED 2026-09-19 — the population is 23, not 24.** This paragraph previously read "the relational population is
29 − 3 − 2 = 24". That line was **short by the PRESENT-for-every-node removal**, which the leaks lens then measured at
**1** eligible held `reach` question: the pointing policy *"PRESENT for every node / every edge slot; ABSENT for
reach; NO_MATCH for the rest"* answers 1 eligible question (`DESIGN_REVIEW_LEAKS_LENS.md` LK16;
`measurements/leaks_review/lk6_gate_population_out.txt:31`, `:68`). The verified arithmetic at the frozen population
is therefore **29 − 6 = 23**, the six removals being FP2 `parts` **3**, node-order dependence **2** and
PRESENT-for-all **1** — the "3 + 2 + 1" that the earlier line collapsed into "3 + 2". The population is still spread
over 5 held worlds, so 3 improved questions in 2 kinds still satisfies the ≥ 2 kinds and ≥ 2 worlds rule, and the
minimum passing `b` with `c = 0` remains **7**. The full frozen removal table, the ORACLE RULES distinction and the
feasibility table at 23 are in §6.5 and §6.6.

CONFLICT: `INTERFACE_SPEC_POINTER.md:46` labels the relational-per-world figures "verified inputs" and lists them as
6, 5, 6, 5, 7, but those five numbers sum to 29 across five held worlds, i.e. an average of 5.8 relational questions
per world, while `INTERFACE_SPEC_PIPELINE.md:1445` records 50 held questions over the same five worlds (avg 10) and
`INTERFACE_SPEC_PIPELINE.md:1483` derives the 29 relational questions from per-KIND counts, not per-world counts. I
cannot reconcile a per-world breakdown of 6+5+6+5+7 with a per-kind breakdown that reaches the same total unless the
two are counting different things; `INTERFACE_SPEC_POINTER.md:46` does not say which. `UNCERTAIN:` whether the
per-world figures at `INTERFACE_SPEC_POINTER.md:46` are the RELATIONAL-only counts, and if so why they sum to exactly
29. A later agent must settle this before the gate population is frozen, because the removal list is applied
per-question.

### 6.3 The verified inputs a later agent reconciles against

- The 45 eligible questions and their release into eligible vs shortcut are produced by
  `shortcut_answers` + `eligible_questions` (`INTERFACE_SPEC_PIPELINE.md:1448-1472`), and test 5 pins
  `(45, 5)` plus the exact `reach` shortcut (`INTERFACE_SPEC_PIPELINE.md:1912`).
- The three holdout digests of §5.3, pinned by test P1.
- The live code inventory: **236 rows** for the practice study
  (`INTERFACE_SPEC_PIPELINE.md:730-732`).
- The 18 shipped checkpoint files, 15,259,777 bytes total, 9 sidecar sha256 values verified against the real bytes
  (`pre_design/contract_pins/checkpoint_pins.json:120-126`; `INTERFACE_SPEC_POINTER.md:42`). The nine `.pt` files are
  15,053,349 bytes of that total, and the largest single file is 1,717,171 bytes, under the 4 MiB member limit
  (`checkpoint_pins.json:124-125`; `DESIGN_REVIEW_PIPELINE_LENS.md:196`).
- The evidence contract's `required_count == len(EXPECTED_ARTIFACTS) + 3` — 83 for the practice worker
  (`INTERFACE_SPEC_PIPELINE.md:350-365`).

CONFLICT: `DESIGN_REVIEW_PIPELINE_LENS.md:196` says "Inventory becomes 236 + 18 rows (limit 2000)", i.e. 254 rows,
but `baseline.input_inventory` globs every `.py` under `cncm/` and `cas_meta2/` at read time
(`worker_contract.py:138-143`), and the pointer build adds four new `.py` files under those two trees
(`pointer_contract.py`, `pointer_inputs.py`, `pointer_learner.py`, `cncm/typed_pointer_worker.py`, plus
`aws/typed_pointer_launch.py` which is outside both trees). I cannot determine from the sources whether 236 is the row
count AFTER the new files exist or before. `UNCERTAIN:` the exact row count on the pointer path. The bound (≤ 2000
rows, ≤ 96 MiB) is not in danger either way, but no agent should quote 254 as a verified number.

### 6.4 What is PENDING on the gate

- **🔴 THE RELATIONAL TIER ITSELF IS IN QUESTION, and this is the largest open item in the document.** The owner
  confirmed on 2026-09-19 that the label must require gains on the RELATIONAL kinds, describing them as *"the ones
  that need the machine to follow links between a world's parts"*, and named parts, edge_account, reach,
  correspondence and analogy (`HANDOFF_20260919_CNCM_POINTER_MACHINE.md` §12). The leaks lens has since **measured**
  that the proposed input's own directed `contains` adjacency already IS the answer for two of those five, with no
  learned weights at all (`measurements/leaks_review/lk1_answer_carriers_out.txt` lines 58-66):

  | Kind | zero-learning rule | held-eligible solved |
  |---|---|---|
  | `parts` | the whole argument's children, one adjacency hop | **5 / 5** |
  | `edge_account` | the complete edge set, read off the input | **5 / 5** |

  The FP2 rule the project already knew about solved only 3 of 5 `parts`; the adjacency is the wider leak. Applying
  the owner's own criterion honestly leaves the three kinds whose answers are **not** in the input — `reach` (best
  zero-learning rule 1/9), `analogy` (0/17), `correspondence` (0/20) — which is **19** eligible questions, and
  **about 17** after the DG3 removals. That is a materially tighter bar than the 24 the arithmetic above assumes, and
  it must not be adopted silently: narrowing the tier changes what the owner confirmed by name. See
  `REVIEW_SYNTHESIS.md` §1 and §2.
- **The complete removal list.** Known: FP2 solves 3 of 5 eligible held `parts`; DG3 node-order dependence covers 2 of
  9 eligible held `reach`. `INTERFACE_SPEC_POINTER.md:46` marks `RELATIONAL_POPULATION` as `OPEN:` and says it is
  "WAITING on lens A for the complete removal list". Do not freeze the population before lens A reports.
- **The rank-only baseline's solved set.** The baseline is registered
  (`INTERFACE_SPEC_POINTER.md:85`) but the questions it solves have not been computed.
- **The new I3's exact recorded evidence.** Test P12 covers a flag-copy-only outcome receiving no label, but the
  reader's I3 depends on which of the two ^6 identity forms the job recorded (§3 C2), which depends on the 20260918 /
  20260919 value conflict above being settled.
- **Whether the flag-copy-only test passes against the FINAL population.** P12 must be re-run after the removals, not
  before.

### 6.5 The frozen removal table, the ORACLE RULES distinction, and the gate population

`lk6_gate_population.py` was fixed after its earlier crash and now prints the complete table, **including the exact
`typed-query-…` ids for every removal**, which is what the contract's frozen removal list needs
(`DESIGN_REVIEW_LEAKS_LENS.md` LK16; `measurements/leaks_review/lk6_gate_population_out.txt:60-71`). The counting rule
is the gate's own: a question is removed when **every** record of it is answered correctly by a registered
no-learning rule, so the unit of evidence is the question (`evaluate_gates.py:52-54`).

| removal | takes | ids printed |
|---|---|---|
| registered input-blind shortcut | **0** | — |
| FP2 `parts(declared_whole) = participants − declared_whole` | **3** (all `parts`) | 3 ids |
| node-order dependence | **2** (all `reach`) | 2 ids |
| rank-last pointing | **5** (`parts` 1, `reach` 4) | 5 ids |
| PRESENT-for-all | **1** (`reach`) | 1 id |
| **total** | **6** at the frozen population; **11** if the rank feature were adopted | **11 ids printed across the rules** |

**How to read the table, because the arithmetic is easy to mis-take.** The **6 total** is the union of the rules that
apply **without** the rank feature: 3 (FP2 `parts`) + 2 (node-order dependence) + 1 (PRESENT-for-all). The rank-last
row's **5** are **not** removed, because the rule needs the rank feature and the rank feature is excluded (§5.1): as
LK7's own resolution puts it, *"If the rank feature is not adopted, the same 5 questions stay in the population but the
protocol must state that the answer of 4 reach questions happens to coincide with the alphabetically last ref, which a
name-blind machine can only reach structurally."* The **11 ids** are printed because the run printed every rule set,
including the rank-last one; if rank were adopted the union would be 11 and the population 18
(`lk6_gate_population_out.txt:50`). Rules that measured **0** eligible removals, and are therefore registered but
remove nothing: the reach flag rule, the edge flag rule, rank-0 pointing, argument-node pointing, and the best single
trained alias-form constant (`lk6_gate_population_out.txt:28-33`). The **11 ids are available to freeze in the
contract** as explicit `query_id` values.

**ORACLE RULES — reported, NOT removed, and that is a decision.** The same run separates a fifth class, in the
reviewer's own words (`lk6_gate_population_out.txt:35-39`):

> **ORACLE RULES (reported, NOT removed by default: applying the checker's own rule to the input IS the skill under
> test; these are the ceiling baselines the label must be compared against)**
> `parts` = children of the whole argument (one adjacency hop) → removes 5 eligible
> `edge_account` = the full adjacency of the focus world (one-hop copy) → removes 5 eligible
> `reach` = DIRECT iff part is a child, else ABSENT (one adjacency hop) → removes 1 eligible

So the one-hop adjacency rules are **reported, not removed**: `parts` **5/5**, `edge_account` **5/5** and `reach`
**1/9** of their eligible held questions (`DESIGN_REVIEW_LEAKS_LENS.md` LK9). The reason is that applying the
checker's own rule to the input **is the skill under test**, so these rules are the **ceiling baselines** the label
must be compared against, not a reason to delete the questions. This settles the tension between the two lenses: the
leaks lens measured those one-hop rules as leaks and wanted the questions out, and this run keeps them **in** and
makes the rule a **ceiling** instead.

**DECISION. The PRIMARY population of 23 is the gate.** The STRICT variant of **16** — also removing the 11 one-hop
adjacency questions — would remove exactly the questions that test the skill, leaving only the kinds this corpus
cannot test, so it is **not** the label's population: it is reported as a sensitivity analysis, and LK17 records that
its arithmetic is a false-negative trap. The primary population, from
`lk6_gate_population_out.txt:43-48`, is:

| | value |
|---|---|
| eligible held questions | 45 |
| RELATIONAL tier before removals | 29 |
| removals | **6** — FP2 `parts` 3, node-order dependence 2, PRESENT-for-every-node 1 |
| **RELATIONAL population (PRIMARY)** | **23** — analogy 5, correspondence 5, edge_account 5, parts 2, reach 6 |
| spread over the five held worlds | 4 / 4 / 7 / 5 / 3 |
| kinds and worlds available for the ≥ 2 / ≥ 2 rule | 5 and 5 |
| minimum passing `b` at c = 0, p ≤ 0.01 | **7** (2⁻⁷ = 1/128 = 0.0078125; 2⁻⁶ = 1/64 = 0.0156250 fails) |
| required share of the population to improve | **7/23 = 0.3043** |
| STRICT variant (also removing the 11 oracle one-hop questions) | 16, share 7/16 = 0.4375 |
| with the rank feature instead of the removal | 18, share 7/18 = 0.3889 |

### 6.6 The feasibility of the gate at 23

From `pre_design/GATE_FEASIBILITY.md` §5. This is pure arithmetic on the frozen gate rule — no material load, no
torch, no AWS, $0 — and it says how often the gate would print `LEARNS_NEW_WORLDS` **if** the machine genuinely
improved on a given fraction of the honest relational questions. It is a statement about the test, not about the
machine, and **nothing has been run**.

| scenario | N | P(all three seeds) at 30 % true improvement | at 40 % | at 50 % |
|---|---|---|---|---|
| **FROZEN: 29 − 6 removals** | **23** | **0.1757** | **0.6723** | **0.9489** |
| rank adopted instead of removing the order-dependent questions | 18 | 0.0374 | 0.3313 | 0.7697 |
| a strict population also removing the adjacency-solved questions | 16 | 0.0067 → 0.0114 | 0.2286 → 0.3313 | 0.7389 → 0.7697 |

**Required share at the frozen population: 7/23 = 0.3043.** Single-seed figures at N = 23: 0.1598 at 20 %, 0.3463 at
25 %, **0.5601 at 30 %**, 0.7466 at 35 %, 0.8760 at 40 % (`GATE_FEASIBILITY.md` §5).

Read against the honest population the source's own conclusion is that **the gate is tight but NOT hopeless**: at 23,
a genuine 30 % improvement passes all three seeds about 18 % of the time and a 40 % improvement about 67 %. The
source states plainly that every figure above is an **upper bound**, because it assumes no losses (at `c = 1` the
smallest passing `b` is **10**, at `c = 2` it is **12**, at `c = 3` it is **14**), ignores the ≥ 2 kinds and ≥ 2
worlds rules, treats clustered questions as independent, and assumes a uniform improvement.

---

## §7 The leaks, shortcuts and vacuity lens (lens A) — REPORTED

No longer a placeholder. The review this section was waiting for has reported:
`records/typed_pointer_001/pre_design/DESIGN_REVIEW_LEAKS_LENS.md`, **30,790 bytes**, findings **LK1–LK18**. It was
read-only, $0, pure Python, no torch, no GPU, no network, and its scratch scripts and raw stdout are under
`records/typed_pointer_001/pre_design/measurements/leaks_review/` — never under `cncm/` or `cas_meta2/`, because the
code inventory is frozen from authority to the third launch (RK9). Every finding carries one of exactly four severity
tags: `BLOCKS_LABEL`, `FALSE_POSITIVE_RISK`, `FALSE_NEGATIVE_RISK` or `NOTE`.

**Its verdict, in its own words** (`DESIGN_REVIEW_LEAKS_LENS.md:24-38`):

> the proposed input carries held answers in three of the eight kinds, and the relational tier as defined is not
> shortcut-free. role_set's `focal_excerpt` **is** the answer ... definition and context are each the answer's own
> fields, fed back as two input flags (5/5 and 5/5 of their eligible held questions, no learning). Inside the
> RELATIONAL tier a single new input flag — the node's rank among the world's sorted refs — solves 5 of the 45
> eligible held questions by itself (parts 1/5, reach 4/9), and one adjacency hop solves all 5 parts questions and all
> 5 edge_account questions. ... The label only means something if LEARNS_NEW_WORLDS is printed from the RELATIONAL
> test on a population of **23** questions (analogy 5, correspondence 5, edge_account 5, parts 2, reach 6) after the
> six measured removals, with role_set reported separately and never counted; the minimum passing b for c = 0 at
> p ≤ 0.01 is **b = 7** (2⁻⁷ = 1/128 = 0.0078125), i.e. 7/23 = 0.3043 of that population, and the gate's "≥ 2 kinds,
> ≥ 2 held worlds" constraint is still satisfiable (5 kinds, 5 worlds).

**The four things this section was waiting on, and where each is answered.** Whether anything in the proposed input
carries a held answer — yes, in three of the eight kinds: LK1 (`role_set`), LK2 (`definition` and `context`). Which
answers a single input flag gives with no learning — LK7, LK8, LK10. The accuracy of the named pointer-space
shortcuts on held worlds — LK9, LK10. Permutation vacuity — LK13, LK14, LK15. The complete removal list and the
minimum `b` — LK16, LK17.

**Findings LK1–LK18.** One line each for the finding and one line each for the instruction the builder applies. This
is a summary only; `DESIGN_REVIEW_LEAKS_LENS.md` is authoritative for every finding and its evidence.

| ID | severity | finding | instruction |
|---|---|---|---|
| LK1 | BLOCKS_LABEL | `role_set`'s `focal_excerpt` **is** the answer: a published clause-prefix rule with zero learned weights reproduces 6/6 held-back and 30/30 trained records, and the position-free token-bag reading reproduces it identically. | Register `role_set` as ANSWER_IN_INPUT and report it only; it may never enter a learning population and its gains may never contribute to `LEARNS_NEW_WORLDS`. |
| LK2 | BLOCKS_LABEL | `definition` and `context` are the answer's own fields, fed back as two input flags: 5/5 and 5/5 of their eligible held questions, 15/15 and 17/17 of their held records. | Keep them as DIRECT_READ, make the label depend on the RELATIONAL population only, and carry these exact numbers in the flag-copy baseline. |
| LK3 | FALSE_POSITIVE_RISK | `analogy`'s admissible set is 6 or 9 worlds and `NO_MATCH` is admissible in 0/17 held records, so a guess is about 13–15 % per record. | Register and print the per-question chance band, and give each gained analogy question's admissible-answer count; never let analogy be the only improved kind. |
| LK4 | FALSE_POSITIVE_RISK | `correspondence`'s `mode` slot is a constant — `NO_MATCH` is admissible in 0/20 held, 0/54 trained, 0/14 excluded records — and a mapping is a 1-in-24 guess. | Register that the mode slot carries no information, and print per-kind accuracy against the measured chance (24/500 over the held correspondence records) and each gained question's admissible-mapping count. |
| LK5 | NOTE | `is primary label` and `is participant` are the same fact: `primary_labels == participants` in **64/64** worlds, so one of the two flags is redundant. | Drop `is primary label` / `primary rank` from the input list, or state that the list carries four independent node flags, not six. Done in §5.1. |
| LK6 | NOTE | Declared `participants` is in sorted-ref order in only 14/64 worlds, and "rank" is literally the node alias — the sorted position of a node ref equals its own stored index for **244/244** nodes. | If rank is added, say the input carries the node alias index, that the machine is no longer permutation-equivariant and that the §5 vacuity paragraph does not apply; the removal option is the cheaper resolution and keeps the vacuity law intact. §5.1 takes the removal option. |
| LK7 | BLOCKS_LABEL | One input flag — the node's rank among the world's sorted refs — solves **5 of the 45** eligible held questions by itself (`parts` 1/5, `reach` 4/9). | Register the rank-last pointing rule as a per-question baseline; if rank is adopted remove its 5 questions, and if it is not, state that 4 reach answers happen to coincide with the alphabetically last ref. §5.1 excludes rank and §6.5 freezes the removal list. |
| LK8 | FALSE_POSITIVE_RISK | FP2 measured as its own line: `parts(declared_whole) = participants − declared_whole` solves 3/5 held-eligible `parts` (3/9 held records, 4/19 trained questions). | Adopt FP2's fix with these numbers and register the reach and edge flag rules as baselines that remove nothing further. |
| LK9 | FALSE_POSITIVE_RISK | One adjacency hop solves **5/5** held `parts` and **5/5** held `edge_account`, and 1/9 held `reach`. | Freeze the one-hop rule as a per-question ceiling and report two populations — PRIMARY 23 and STRICT 16 — choosing one in writing before the run. §6.5 chooses PRIMARY. |
| LK10 | NOTE | The remaining zero-learning pointing policies, on eligible held questions: argument node 5/45, part argument 0/45, focus-world-plus-declared-whole 5/45, PRESENT for every non-argument node 1/45, PRESENT for every node and edge pair 1/45; the fitted majority symbol scores 0/45, and an all-symbols-tied machine already answers 1/45. | Put all six policies and their measured numbers into the frozen baseline test, and report separately from the gains any question the equal-logits policy already answers. |
| LK11 | FALSE_POSITIVE_RISK | One in three eligible questions is decided by a single record: 20 of 50 held questions, of which **15 of 45** are eligible. | Require the gate reader to print, per gained question, its record count and admissible-answer count, as part of the printed label output. |
| LK12 | NOTE | The existing input-blind removal is not leaky in the constant direction, but it is not frozen: it is recomputed at gate time from the trained set, so a change to the split or the checker profile silently changes the population. | Keep the rule but freeze its output as an explicit id list in the pointer contract rather than recomputing it at gate time. |
| LK13 | NOTE | Six permutation claims cannot fail and must be listed as VACUOUS: world-level relabelling invariance; node-head equivariance; "the assembled answer is unchanged when node refs are shuffled"; the checkpoint probe's accuracy as a transfer measure; I3 as written; and the RELATIONAL_TRANSFER flag as printed. | Write these six lines into the frozen protocol as VACUOUS and print them next to the label, so no reader mistakes a passing invariance test for evidence. |
| LK14 | FALSE_POSITIVE_RISK | Adopting the rank feature breaks the vacuity law itself, because rank is the node's public alias. | If rank were adopted the protocol would have to withdraw the vacuity sentence and replace the equivariance test with a no-alias-channel test; rank is not adopted (§5.1), so the vacuity law stands. |
| LK15 | NOTE | Five required permutation tests follow from the measured facts: E1 no-alias-channel, E2 wiring, E3 symbol-row alignment, E4 rank, E5 answer-side precondition. | Add E1–E5 to the pre-launch test list as engineering checks and count none of them as evidence of learning; E4 does not apply once rank is excluded. |
| LK16 | BLOCKS_LABEL | The exact removal list: **6** questions without the rank feature → RELATIONAL **29 − 6 = 23**, with **11** question ids printed across the removal rules. | Freeze the removal list as explicit `query_id` values in `pointer_contract.py`, print it in the gate reading, and make the primary label the 23-question RELATIONAL population with DIRECT_READ and TEXT printed alongside and never counted. Done in §6.5. |
| LK17 | FALSE_NEGATIVE_RISK | The strict population's arithmetic is a false-negative trap: 16 needs 7/16 = 0.4375 and the kinds left include the two with the largest chance floors, and all three seeds must pass. | Pick the population before the run, in writing, and register the strict variant as a **reported** sensitivity analysis rather than the label's population. Done in §6.5. |
| LK18 | NOTE | Four smaller pipeline routes to a wrong label, measured: training at depths 1/2/4/8 against evaluation depth 8; the joint correspondence loss leaving the `mode` slot a forced constant; the unreported held-back trajectory at checkpoints 2/4/6/8; and the data-dependent removal rule. | Fold (1) into the protocol as "fix K = 8 and register that the learner must not condition on `depth`", (3) as a printed non-gating curve, and (4) as a frozen removal rule; quote (2) so the mode slot's constant nature is on the record. (1) is applied in §5.2 (K pinned at 8, no conditioning on `depth`) and (4) in §6.5. |

**Not restated here.** The report's per-script measurements, its scratch caches (`lk_cache_admissible.json`,
`lk_cache_packets.pkl`, `lk_cache_order.json`, which are regenerable and not deliverables) and its two self-corrections
are all in the source document, which is authoritative.

## §8 The per-kind learnability lens (lens B) — REPORTED

No longer a placeholder. The review this section was waiting for has reported:
`records/typed_pointer_001/pre_design/DESIGN_REVIEW_LEARNABILITY_LENS.md`, **60,599 bytes**, findings **LB0–LB18**.
It was read-only, $0, pure Python plus numpy, no torch, no GPU, no network, and its scratch scripts `lb0`–`lb18` and
their raw stdout are under `records/typed_pointer_001/pre_design/measurements/learnability_review/`. Every finding
carries one of exactly four severity tags: `BLOCKS_RESULT`, `FALSE_NEGATIVE_RISK`, `DESIGN_CHANGE_REQUIRED` or `NOTE`,
defined in the source as: `BLOCKS_RESULT` means the run will print a wrong or no-transfer label for a reason that is
architectural, not statistical; `FALSE_NEGATIVE_RISK` means the run may print a negative that does not generalise;
`DESIGN_CHANGE_REQUIRED` means a specified component cannot produce its answer and must change; `NOTE` means
report-only.

**Its verdict, in its own words** (`DESIGN_REVIEW_LEARNABILITY_LENS.md:72-100`):

> The proposed reading is good enough to learn five of the eight kinds and structurally unable to learn one, with the
> other two at risk for reasons that are about the readout rather than the inputs. The one hard failure is
> **correspondence** ... Its declared tie rule can therefore only emit the first syntactic bijection, and graded
> against the checker that emission is correct in **0/20 held, 5/54 trained and 2/14 excluded** records. On the 5
> eligible held correspondence questions the head contributes b = 0, so the RELATIONAL gate that FP1 makes the primary
> label cannot pass through this kind. The one soft failure that touches five heads at once is **the mean-pooled world
> vector** ... Recommended scope decision for v0.2: register correspondence as a known false negative and remove it
> from the gate population, repair the world-level heads to read the marked node rather than the pooled mean, remove
> the 4 flag-solved questions from the relational population (leaving 25/29), and treat the remaining ceilings as
> registered numbers rather than gates.

**Its per-kind verdict table**, quoted from the source's "One line per kind":

| kind | expressible as drafted? | what is missing |
|---|---|---|
| `role_set` | YES | nothing |
| `definition` | YES, wrong head | score ref heads on declaration text, not `g_w` |
| `context` | YES, wrong head | same |
| `parts` | YES | nothing (1 round suffices) |
| `edge_account` | RISKY | the `a→b` adjacency bit into the edge head's MLP |
| `reach` rule 2 | YES | the rule embedding (DG2) |
| `reach` rule 1 | **NO for 5 of 26 held records** | the hidden node-ref order |
| **`correspondence`** | **NO** | **a joint edge-aware mapping scorer** |
| `analogy` | text half YES, graph half weak | a non-graph-blind world vector |

**Findings LB0–LB18.** One line each for the finding and one line each for the instruction the builder applies. This
is a summary only; `DESIGN_REVIEW_LEARNABILITY_LENS.md` is authoritative for every finding, its exact evidence and its
two recorded self-corrections.

| ID | severity | finding | instruction |
|---|---|---|---|
| LB0 | NOTE | The development panel's structure: 59 packets over 6 focus worlds, 50 with a 10-node focus world and 9 with 9 nodes, kinds parts 6 and reach 53. | Keep the panel report-only, and put that in the contract, not only in the prose. |
| LB1 | FALSE_NEGATIVE_RISK | Rule-1 `reach` is order-dependent: the VIA node follows the hidden ref order for **5/26 held, 11/71 trained, 2/10 excluded** reach records. | Remove those records from the gate, or add the DG3 rank feature with a registered rank-only baseline (removing is safer). §5.1 removes them. |
| LB2 | BLOCKS_RESULT | `definition` and `context` are flag echoes: a zero-learning reader gets 15/15 held definition and 17/17 held context right, and **4 of the 29** eligible relational questions are flag-solved. | Make the RELATIONAL tier the only gate, drop the 4 flag-solved questions and recompute minimum `b`. They are in §6.5's frozen removal table. |
| LB3 | BLOCKS_RESULT | Shape twins: every held world has 7, 6, 11, 6, 11 same-shape trained twins, and **320/2016** bank pairs share a signature and all 320 are isomorphic. | Add a registered shape-class control, and report every world-level kind against its twin count. |
| LB4 | NOTE | Only **6** non-isomorphic structures exist in the bank, class sizes {12: 4, 8: 2}. | Register that the tie grid cannot separate shape from label on this corpus. |
| LB5 | NOTE | The refinement routine reproduces the known colour structure of 6 synthetic shapes and the 6 real classes. | Keep `lb5_refine_debug.py` as the regression test for any future refinement code. |
| LB6 | BLOCKS_RESULT | The pooled world vector separates **2 of 6** shapes with uniform features and collapses **50 of 64** worlds; graph content **3.27 %** at 1 round to **7.98 %** at 8. | Do not read a world-head failure as evidence about the machine; fix the readout first. |
| LB7 | DESIGN_CHANGE_REQUIRED | The sorted (in-degree, out-degree) multiset is a **complete isomorphism invariant** on this corpus: both partitions give 6 groups and coincide exactly, and **0/2016** non-isomorphic pairs are indistinguishable under all 4 colourings. | Use the sorted (in-degree, out-degree) multiset as the registered shape test, and say in the contract that WL is not the binding constraint here. |
| LB8 | NOTE | Exact answer functions and populations: `correspondence` is 88/88 MAPPING and 0/88 NO_MATCH; `analogy`'s correct set is `isomorphic AND different domain` in 70/70 records. | Register the missing positive class for the `mode` slot, and report analogy on the shape-plus-domain rule. |
| LB9 | FALSE_NEGATIVE_RISK | Saturation ranges **75.30–98.03 %** with no norm and **48.02–91.83 %** with the output norm, against **7.65–13.42 %** at the torch default; state scale varies 1.08×–1.16× with node count. | Pin the `^6` initialisation and assert the measured saturation at pass 0 in the worker. |
| LB10 | NOTE | **20/20** held labels occur in trained records (7,160 textual occurrences) and are read **30,420** times in training, but are the focus of a trained question in only 2/20. | Keep labels only with the one-time cache (230 encodes, 5.0 s) and never tokenise per packet (284,900 encodes, 6,225 s) — or drop them, which §5.1 does. |
| LB11 | DESIGN_CHANGE_REQUIRED | The 1,470-update schedule under-covers: the rarest head sees **320/1470** updates and the 64-way text choice gets **550** update events over 113 records. | Rebalance so every kind appears in every pass (about 10 × 470 updates), or drop the untrainable heads. §5.3.1 records the measured cost of the stratified branch. |
| LB12 | DESIGN_CHANGE_REQUIRED | The edge-free per-node score cannot express a bijection: the focus world is the target in 0/88, label sets are disjoint in 88/88, and the admissible set is 1 of 24 in 16/20 held records. | Add a joint edge-aware bijection scorer, or drop `correspondence` from the gate. |
| LB13 | DESIGN_CHANGE_REQUIRED | An additive per-node score is wrong in **81 of 88** correspondence records, and the first syntactic bijection is correct in **0/20 held, 5/54 trained, 2/14 excluded**. | Register `correspondence` as a known false negative in v0.2 and remove it from the population. |
| LB14 | NOTE | Order and label channels buy nothing on the held set: ref-rank, label-rank and degree-rank rules solve **0/20** held correspondence records, and a label-preserving mapping is admissible in 0/88. | Do not add labels or the ref rank hoping to fix correspondence. |
| LB15 | BLOCKS_RESULT | `correspondence` contributes **b = 0** to the relational gate; the lens puts the relational population at **25/29** and finds the minimum passing `b` at α = 1/100 with c = 0 is **7**. | Recompute the gate arithmetic against the reduced population and print the per-kind table next to the label. |
| LB16 | BLOCKS_RESULT | The readout is graph-blind: the edge/non-edge cosine gap is **0.039** at 1 round, **0.388** at 4 and **0.340** at 8, and the pooled shape spread is **3.27 %–7.98 %**. | Relax the "never to a readout head" rule for the edge head only, or drop `edge_account` from the gate. |
| LB17 | BLOCKS_RESULT | The world-vector wash-out is architectural: the graph content of the pooled vector is at most about **4 %** under the readout-layer gradient and **0 %** in the graph-regularised limit. | Condition the world-level heads on the marked node's state or on degree sums, not on the pooled mean. |
| LB18 | FALSE_NEGATIVE_RISK | A same-shape-and-different-domain rule solves **17/17** held analogy records at zero learning. | Report analogy separately, and never read the RELATIONAL aggregate as relational reasoning. |

CONFLICT: the two lenses disagree about `correspondence` in the gate population, and the recorded reconciliation keeps
it in. `DESIGN_REVIEW_LEARNABILITY_LENS.md` LB12, LB13 and LB15 instruct that `correspondence` "must be recorded as a
known false negative and removed from the RELATIONAL gate population", on the measured ground that its head
contributes b = 0; `REVIEW_SYNTHESIS.md` §10.1's frozen PRIMARY population of **23** nevertheless **retains** all 5
eligible held `correspondence` questions (analogy 5, correspondence 5, edge_account 5, parts 2, reach 6), and §10.4
records the reconciled position as "`correspondence` — **no** — not expressible by the drafted head; 0/20 held". Both
readings are exact and they are not reconciled anywhere in the sources. §6.5 and §6.6 follow §10.1, so the frozen gate
population contains the 5 correspondence questions. A later agent must settle this before the protocol is frozen: the
choice changes the population and therefore the required share.

CONFLICT: the lens puts the relational population at 25 and the frozen figure is 23. LB2 and LB15 report the
post-removal relational population as **25/29**, which is 29 less the 4 flag-solved questions (3 `parts`, 1 `reach`).
`REVIEW_SYNTHESIS.md` §10.1 and `lk6_gate_population_out.txt:43` put it at **23**, which is 29 less **6** — the same 4
plus the 2 node-order-dependent `reach` questions from LB1. Both figures are exact and refer to different removal
stages; the frozen gate population is **23**, and the lens's own instruction ("recompute the gate arithmetic against
the reduced population") is what §6.5 and §6.6 do.

UNCERTAIN: LB2 attributes the fourth flag-solved relational question — a `reach` question whose id ends
`2077da4b16f7` — to "the draft's stated flags alone", while `lk6_gate_population_out.txt:21` records the reach flag
rule as removing **0** eligible questions and `:31` attributes 1 eligible `reach` question to the **PRESENT-for-all
pointing policy** (id ending `4b16f7`). The two ids appear to be the same question, and both lenses agree it is
removed exactly once, so the population is unaffected either way. Which rule actually solves that question, and
therefore which baseline row it belongs in, is undetermined.

**Not restated here.** The report's stability, optimiser, WL-limit and development-panel measurements, its nine ranked
predicted false negatives, and its two recorded corrections to its own first pass are all in the source document,
which is authoritative. **Two `OPEN:` items in §5 named this lens.** The first — whether node LABEL words survive in
the input — is resolved in §5.1: they are dropped. The second — the exact head set — is no longer waiting on this lens,
because the lens's expressivity table has now reported; the head set itself is still not frozen by this draft, and the
per-head changes the lens requires are LB6, LB7, LB12, LB16 and LB17.

---

## §9 Build plan

Nine files. One line each on what the file contains. The API surface is NOT restated here: it is fixed in
`pre_design/INTERFACE_SPEC_POINTER.md` §§1-6, and the shared and pipeline contracts it must not contradict are in
`INTERFACE_SPEC_SHARED.md` and `INTERFACE_SPEC_PIPELINE.md`. Read those three before writing any of these.

**Build status at HEAD `d5e1dc1b`.** Two status words are used, one meaning each: **BUILT and verified** means the file
exists, its own tests pass, and an independent verifier has been run against it; **IN BUILD** means the file exists and
work on it is not complete; **planned** means not started.

| # | file | status |
|---|---|---|
| 1 | `pointer_contract.py` | **BUILT and verified.** The pointer test file is green — **20 passed in 128.86 s** (`python -m pytest tests/test_typed_pointer_study.py` at HEAD `d5e1dc1b`) — and an independent contract verifier exists at `pre_design/verify_contract.py`, carrying **25 checks**. See the two notes below. |
| 2 | `pointer_inputs.py` | **IN BUILD.** The file exists in the working tree, and the P9/P10 reader tests in the same test file are green, but the build is not complete. |
| 3–9 | the seven remaining files | **planned**, exactly as in the plan below; none has been started. |

- **The verified test count is 20, not the earlier 11.** The suite grew when the stratified-schedule tests were added
  with the owner's second decision (§0.3 item 5, §5.3.1): the file now also carries
  `test_the_stratified_default_puts_every_kind_in_every_update_at_the_same_update_count`,
  `test_the_stratified_cost_is_the_measured_1176_presentations_and_the_digest_is_pinned` and
  `test_every_stratified_batch_carries_exactly_eight_records_and_eight_kinds`. So the earlier figure of 11 green tests
  is superseded by measurement, not contradicted by it.

CONFLICT: the independent verifier is not green on a re-run at HEAD `d5e1dc1b`. Running `python
records/typed_pointer_001/pre_design/verify_contract.py` reports **25 checks, 3 failed**. The three failures are
exactly the checks that still assert the **as-is** schedule: `pointer_schedule(10) reproduces the practice batches
digest`, `pointer_schedule(10) has 147 updates/pass and 818 presentations/pass` (it measures `147 / 1176`), and
`pointer_schedule(10) matches the practice pointer_schedule line for line`. All three are made false by the
stratified decision of §5.3.1, which changes presentations per pass from **818** to **1176**. The other **22** checks
pass, including `ceiling permits 24 passes and refuses 25  PASS  ceiling=3544, 24 passes=3544` and `the practice
ceiling would have capped this study at 13 passes`. The checked-in output file
`pre_design/verify_contract_out.txt` is also stale: it records **18 checks, 1 failed** and predates the verifier
file's last edit. So the verifier cannot be reported as green until it is updated for the stratified schedule; the
contract and its independent verifier are not yet consistent with each other.

| # | file | what it contains |
|---|---|---|
| 1 | `research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/pointer_contract.py` | Pure. Imports the practice split and schedule unchanged. New `CANDIDATE`, `CONFIG_SCHEMA`, `JOB_PATTERN` with the ≤5-character token `tpntr`, `CHECKPOINT_PINS` loaded from `pre_design/contract_pins/checkpoint_pins.json`, `MATERIAL` = the practice `MATERIAL` plus the 18 checkpoint rows, an `input_inventory` wrapper, a new `DESIGN` without the two false fields, the tier lists, the frozen flag-rule and rank-rule baselines with the frozen gate population, the new `expected_main_delta` formula, `parse_job` / `make_config` / `validate_config` (with the C5 group fix). |
| 2 | `.../typed_teaching/pointer_inputs.py` | Pure, deterministic public reader with a digest: per-world node flags, the registered node rank, directed adjacency, domain-word ids, query kind/rule/argument marks, and the `role_set` excerpt word ids. Never reads supports, cue, instruction or node labels beyond what §5.1 decides. `label_cache` built once with a pinned digest. |
| 3 | `.../typed_teaching/pointer_learner.py` | Torch only when called. `PointerCourseLearner` per §5.2: one container `module` holding every learned weight including the ^6 block from `matched._framework` built FIRST; dense-matmul message passing with K = 8 shared rounds and RMS normalisation; the pointer heads of §5.2; outputs exactly `loss_plan.validate_prediction`'s field set. Own `__init__`, `predict`, `stage_batch`, `train_sealed_batch`, `export_checkpoint`, `restore_checkpoint`, `profile`. |
| 4 | `cncm/typed_pointer_worker.py` | Adapted from `typed_practice_worker.py` (495 lines), reusing `_publish`, `_publish_bytes`, `_move_in`, `_append`, `_seal_predictions`, `_train_logged`, `_stage_and_train`, `_evaluate`, `_split_score` and `base._ProgressWriter`, `_state`, `_check_state`, `_partial_checkpoint`, `_score_seal`, `_write_bytes`, `counter_delta`, `_representatives`. Phase order: preflight → packets → checkpoint check PHASE A → seed + double build → 10 passes with evaluations → retention/interference → reloads/replays → PHASE B probes → ablations → source verification → deliver. Own `EXPECTED_ARTIFACTS` (< 500 names, unique, `required_count == len + 3`) and own expected-work check. Pointer input checks replace `base._encoding_checks`. |
| 5 | `research/CAS_META_2_COMPOSITION/aws/typed_pointer_launch.py` | Copy of the practice launcher with the five schema constants, `WORKER_NAME`, `CANDIDATE`, `CONFIG_SCHEMA`, `JOB_PATTERN`, `_probe()` → `cncm.typed_pointer_worker` keeping the four-constant check, `EXPERIMENT`, `BOUNDS`, `worker_config`, the request/authority/owner validators including the three bindings, `bootstrap_source()` → `typed_pointer_worker` keeping the `count == 2` check, its own `render_worker()`, `evidence_contract()`, a `reservation_plan_for` with a new `task_scope`, and a `git_package_bytes` allowlist admitting the 18 checkpoint paths through the new `MATERIAL`. `PACKAGING_SOURCES` adds `"aws/typed_pointer_launch.py"`. |
| 6 | `records/typed_pointer_001/evaluate_gates.py` | Copy of the practice reader with a new I1 (the new worker's `SUCCESS_STATUS` and `EXPECTED_ARTIFACTS`) and a new I3 carrying the corrected DG4 evidence. Primary label keyed on RELATIONAL, the all-kinds result reported as a flag, per-tier and per-kind tables, the relational removals applied to the population, and the exact arithmetic unchanged. New output schema string. |
| 7 | `records/typed_pointer_001/{prepare_study.py, execute_study.py, preflight_dry_run.py, holdout_audit.py}` | Adaptations of the four practice drivers. The owner's verbatim text of §0.1 plus the owner decisions of §0.3 — all five, including the second pair — go into every job's `owner.json`, one record per job. `prepare_study.py` writes `admission_001/{study.json, 2026091X/{request,authority,owner}.json, rehearsal}`; that freeze is committed and pushed BEFORE the first launch. `execute_study.py` runs one job at a time and stops on the first failure with an explicit `stop_unless`, never `assert`. |
| 8 | `docs/CNCM_TYPED_POINTER_STUDY_v0.1.md` | The frozen protocol, whose sha256 becomes `study.json`'s `protocol_sha256`. Carries the RELATIONAL primary gate, the frozen per-question baseline and removals, the Phase A/B ordering, the K = 8 choice, the rule embedding, the rank feature and its baseline, and the owner's verbatim text. |
| 9 | `tests/test_typed_pointer_study.py` | The test map P1–P14 below, with a self-contained `sys.path` block at the top — other test modules rely on import side effects — and the same `public_only` numeric-import guard the practice test file uses. |

### 9.1 The test map

Pure, $0, no torch, with the numeric-import guard in place (P8 depends on it).

| ID | test |
|---|---|
| P1 | Holdout and schedule identical to the practice study: held digest `668e6ce7...`, excluded digest `b82108e1...`, `batches_digest` `daf95831...`, 45 eligible / 5 shortcut. |
| P2 | Bucket length ≤ 63 for all three seeds. |
| P3 | Inventory has the 18 pinned checkpoint rows and stays within the row, byte and member bounds. |
| P4 | The restore-identity freeze test for all 9 checkpoints. |
| P5 | Package dry run with a fake git reader: archive ≤ 24 MiB; the rendered worker names `typed_pointer_worker` and never the old worker. |
| P6 | Launcher overrides: the watchdog accepts the new job pattern and refuses the practice one; `bind_authority`; `task_scope`; `failure_statuses`; `_probe` constants. |
| P7 | `EXPECTED_ARTIFACTS` unique, < 500, covers the checkpoint-check files, `required_count == len + 3`. |
| P8 | The worker refuses Windows BEFORE any numeric import and delivers a FAILED result with the new schema. |
| P9 | `pointer_inputs` purity, determinism and cache equality for all 230 labels; per-packet read time bounded. |
| P10 | Inputs exclude supports, cue, instruction, and every order-like channel **other than** the registered node rank; include the reach rule. |
| P11 | The planned-work formula matches the real schedule. |
| P12 | Gate reader: a flag-copy-only outcome gets no label; the exact arithmetic; the new I3. |
| P13 | The frozen flag-rule and rank-rule baselines and the removal lists. |
| P14 | Custody: the checker is imported and targets derived only after the first pointer seal, except in phase B. |

GPU smoke, local RTX 4070, dev only, not claim-bearing: S1 all 8 kinds forward and backward under deterministic mode,
bit-identical twice; S2 `train_sealed_batch` on a batch missing most kinds and on an interference batch; S3 export →
restore → predict identical, replay from prelast equals final; S4 evaluation leaves state unchanged; S5 identical
start with the check on/off and the ^6 sub-block identity equal to the matched start; S6 phase A restores all 3
checkpoints and rebuilt logits equal `restored.predict` bit-for-bit, and a forced failure still writes the artifact;
S7 time one pass plus one evaluation → projected job time; S8 score bounds and loss agreement; S9 **no order-like
channel beyond the registered rank** — a node must influence the answer only through its declared features (raw flags,
rank, and its label tokens if kept), never through its position in the packet, its position in the file, or any part of
its ref beyond the index the rank is derived from (engineering only, never evidence; this replaces the earlier
"node-relabelling equivariance", which cannot hold now that rank is an input — see the VACUOUS note in §1); S10 the worker's `run()` end to end on a shrunken schedule.

Where smoke can run (`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:310-313`): `execution_guard()` requires Linux
and `CAS_META2_RUN_TEACHING_CYCLE=1`, and the worker requires torch `2.11.0+cu128` and an "RTX PRO 4500" GPU. S1, S2,
S7, S8 and S9 can run on the local RTX 4070 by driving the network module directly (venv `~/venvs/cas-gpu`, dev only).
S5 cannot assert the ^6 identity locally (§4.3 consequence 1). S10 needs a short AWS smoke job on the real instance —
approved by the owner, §0.3 item 2, well under $1.

### 9.2 Freeze, dry-run, launch

Summarised from `records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:333-356`.

1. Write this design's successor as the frozen protocol, build the nine files, write the tests; `pytest` green. The
   pure baseline that must not regress is 89 passed in 328.56 s at HEAD `52fea7ed`
   (`INTERFACE_SPEC_POINTER.md:24-26`).
2. Adversarial pre-flight review of the BUILT code, TWICE: fix, then review again. Record both as
   `records/typed_pointer_001/PREFLIGHT_REVIEW.md` with findings files.
3. Stand-in dry run (`preflight_dry_run.py`, pattern of the practice one): real everything except the learner;
   create-only publisher simulation; write-audit hook. It must print `PREFLIGHT_PASS` for all three seeds. The pointer
   version needs its own `staging` directory name and its own `expected` integrity-failure list, because the pointer
   reader's I3 is redefined.
4. GPU smoke per §9.1; S10 on AWS only after the owner's OK (already given).
5. Commit everything — the package is built from git HEAD blobs, so any uncommitted `.py` fails
   `INPUT_NOT_COMMITTED` — and push.
6. `python records/typed_pointer_001/prepare_study.py` → `admission_001/{study.json, 2026091X/{request,authority,owner}.json, rehearsal}`; commit and push that freeze BEFORE the first launch.
7. Launch sequentially, in the background, logging to a file:
   `python records/typed_pointer_001/execute_study.py --execute records/typed_pointer_001/admission_001/study.json <sha256>`.
   It stops on the first failure with an explicit `stop_unless`, never `assert`. One job at a time, because the
   us-west-2 GPU quota is 8 vCPU. Change NO `.py` under `cncm/` or `cas_meta2/` until all three jobs have launched.
8. The gate program's printed label IS the claim status. Write `records/typed_pointer_001/POINTER_STUDY_RESULT.md`,
   update `records/MACHINE_STATE_001/STATUS.md`, `CHANGELOG.md` and the spec-sheet row with artifact paths, in the same
   commit. Back up receipts to `D:\tksCAS-archive\cncm_typed_pointer_001_<date>` with sha256 checks. Commit, push,
   report to the owner in plain English.

AWS facts: account 807562639912, region us-west-2, instance g7.2xlarge (RTX PRO 4500) at $2.52/hour observed. The
bucket is `job + "-807562639912"`. Credentials are local, never printed or copied. The practice jobs took
6,064 / 6,082 / 6,025 s of instance time, about $12.72 total (`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:352-355`).

---

## §10 Owner items

### Answered — do not re-ask

The hand-off's owner items were answered in **two rounds on 2026-09-19**. The first three — the two corrections, the
gate change and the AWS smoke job — were answered in the session that picked up the hand-off
(`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:381-391`). The purpose and training questions were answered **later
the same day**, by selecting one labelled option from each list; both selected labels are recorded verbatim in §0.3.

1. **The two corrections — ANSWERED.** Owner answer verbatim: *"Accept both, carry on."* The two corrections, quoted
   from the same source: "At no extra cost" was wrong — the in-job checkpoint check costs about 9–15 minutes per job,
   about $0.38–$0.63 per job; and "Pointer answers" alone cannot work — the INPUT must change too, so the machine
   reads one world as a small graph instead of a blend of all 64 worlds.
2. **The short AWS smoke job for S10 — ANSWERED.** Owner approved it, well under $1. It doubles as the timing
   measurement for S7/DG9 and must run before the paid launch.
3. **The gate change — ANSWERED.** Owner answer verbatim: *"Yes — require the relational kinds."*
   `LEARNS_NEW_WORLDS` will require gains on the RELATIONAL kinds; the all-kinds result is reported alongside as a
   flag, not as the label.
4. **The purpose question — ANSWERED LATER THE SAME DAY.** The owner selected the option labelled **"Run it as the
   transfer test, label honestly (Recommended)"** (§0.3 item 4). The study runs as the transfer test and the label is
   printed honestly; a tier or kind whose answer is already in the input is reported as such and never carries a
   learning claim (`REVIEW_SYNTHESIS.md` §10.4).
5. **The training question — ANSWERED LATER THE SAME DAY.** The owner selected the option labelled **"Stratify AND
   train longer (Recommended)"** (§0.3 item 5). The schedule is stratified so every kind appears in every update, and
   the study trains for more passes than the practice study's ten; both halves are recorded with their measured numbers
   in §5.3.1.

### Still open

**Only one item is still open.**

**The budget, conditional.** If the smoke timing projects a job above about 11,000 s, a larger per-job reservation
needs a NEW approval. The approved envelope is about $13 expected and $45 reserved in total. Nothing has been re-asked
yet (`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:393-396`).

The hand-off lists a fifth item — authorisation of the Vercel MCP server in an interactive `claude` session
(`/mcp`) — and records it as unrelated to this work and untouched. It is not an item for this study
(`records/HANDOFF_20260919_CNCM_POINTER_MACHINE.md:397`).

---

## Appendix — every CONFLICT and UNCERTAIN line in this document

Collected here so a reader can find them without hunting.

- **CONFLICT (§3 C2):** `checkpoint_pins.json` and `INTERFACE_SPEC_SHARED.md` disagree about which `model_state_identity`
  belongs to seeds 20260918 and 20260919. Both versions are stated in §3 C2. The pin file is the one that agrees with
  the on-disk checkpoints and with the probe's own output artifact, so the in-job check must use the pin-file values; the
  disagreement is not silently resolved away, it is recorded with its evidence.
- **CONFLICT (§6.2):** the per-world relational counts at `INTERFACE_SPEC_POINTER.md:46` sum to 29 but read as an
  average of 5.8 per world, while the same 29 is derived per-kind at `INTERFACE_SPEC_PIPELINE.md:1483`.
- **CONFLICT (§6.3):** the inventory row count is quoted as 236 practice rows elsewhere and as "236 + 18" in the
  pipeline review, but the inventory globs the live tree, so neither number is pinned until the new files exist.
- **UNCERTAIN (§6.2):** whether the per-world figures at `INTERFACE_SPEC_POINTER.md:46` are the RELATIONAL-only counts,
  and if so why they sum to exactly 29.
- **UNCERTAIN (§6.3):** the exact inventory row count on the pointer path.
- **UNCERTAIN (§4, and §3 of the hand-off):** the AWS-instance bit-exactness of the ^6 start is established by the
  practice study's passing I3, not by the local probe; the local probe measured a 7.450580596923828e-09 difference on
  all three seeds.
- **CONFLICT (§5.1):** `REVIEW_SYNTHESIS.md` §10.2 requires "The `node_rank_feature` flag in the contract must be set
  False", while `pointer_contract.py` on disk carries `"node_rank_feature": True` with
  `"node_rank_decision_status": "REGISTERED_INCLUDED_REOPENED_AT_6cb0b348_PENDING_LENS_A"`. Lens A has reported and the
  rank feature is excluded, so the contract flag must be set False. Not yet reconciled; observed at HEAD `d5e1dc1b`.
- **CONFLICT (§8):** the learnability lens instructs that `correspondence` "must be recorded as a known false negative
  and removed from the RELATIONAL gate population" (LB12, LB13, LB15), while `REVIEW_SYNTHESIS.md` §10.1's frozen
  PRIMARY population of **23** retains all 5 eligible held `correspondence` questions. Both readings are exact and are
  not reconciled in any source. §6.5 and §6.6 follow §10.1; the choice changes the population and therefore the
  required share, so it must be settled before the protocol is frozen.
- **CONFLICT (§8):** the learnability lens puts the post-removal relational population at **25** (LB2, LB15), while
  `REVIEW_SYNTHESIS.md` §10.1 and `lk6_gate_population_out.txt:43` put it at **23**. The two refer to different
  removal stages — 25 is 29 − 4 flag-solved, 23 is 29 − 6 — and the frozen gate population is 23.
- **UNCERTAIN (§8):** the `reach` question whose id ends `2077da4b16f7` is attributed by the learnability lens (LB2)
  to "the draft's stated flags alone", and by `lk6_gate_population_out.txt:31` to the PRESENT-for-all pointing policy;
  the leaks lens's reach flag rule removes **0** eligible questions (`:21`). Both lenses agree the question is removed
  exactly once, so the population is unaffected either way, but which rule actually solves it is undetermined.
- **CONFLICT (§9):** the independent contract verifier is not green at HEAD `d5e1dc1b`. A re-run reports **25 checks,
  3 failed** — the three checks that still assert the as-is schedule (818 presentations per pass and the practice
  `batches_digest`), which the stratified decision of §5.3.1 makes false (the stratified schedule gives **1176**
  presentations per pass). The other 22 checks pass. The checked-in `pre_design/verify_contract_out.txt` is staler
  still at **18 checks, 1 failed**.
