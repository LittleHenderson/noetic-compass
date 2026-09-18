# HANDOFF — CNCM / CASformer: launch the analytic arm on AWS

**Written 2026-09-17 by the outgoing agent. Branch HEAD `69acd081`, 3 uncommitted files. $0.00 spent, nothing running on AWS.**

You are picking up a measurement-and-architecture campaign on the **CAS Native Cognitive Machine (CNCM)**. The immediate job is **one AWS GPU run**. Everything before it is done, measured, and committed. Read §1, then §5, and you can act.

---

## 1. WHERE EVERYTHING IS — full paths

**Repository root (git root):**
```
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next
```
Branch `codex/cncm-vision-next`, remote `origin` = `https://github.com/LittleHenderson/noetic-compass.git`. HEAD `69acd081`, local == remote, 3 uncommitted files (see §7).

**Project directory — almost every path below is relative to this:**
```
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE
```
Call this **`CNCM`** below. It is the write boundary (see `AGENTS.md` in it).

**Do not touch** `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\CAS_RRK_v0.1` — a separate workstream. Read-only.

### The single most important file to read first
```
CNCM\records\MACHINE_STATE_001\STATUS.md
```
Consolidated state, sections 1–8, every number with its artifact. **Read this before anything else.** It supersedes all earlier narration.

### AWS launch path
```
CNCM\records\typed_matched_001\prepare_study.py      # builds 6 frozen jobs + package
CNCM\records\typed_matched_001\execute_study.py      # runs them sequentially, stops on failure
CNCM\records\typed_matched_001\audit_complete_study.py
CNCM\records\typed_matched_001\STATUS.md
CNCM\records\typed_matched_001\MATCHED_STUDY_RESULT.md
CNCM\research\CAS_META_2_COMPOSITION\aws\typed_matched_launch.py    # the launcher (boto3)
CNCM\research\CAS_META_2_COMPOSITION\cas_meta2\typed_teaching\matched_contract.py   # DESIGN, CONDITIONS, MODEL_SEEDS
```

### Ledger (money)
```
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\meta1\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\research\CAS_META_2_COMPOSITION\records\budget\campaign_ledger.json
```
**Note the nested path** — there is a *different* copy at `CNCM\research\CAS_META_2_COMPOSITION\records\budget\campaign_ledger.json`. `typed_matched_launch.CANONICAL_LEDGER` resolves to the `_worktrees\meta1\...` one. Current position:

```
revision                 84
owner_task_cap_usd       5000.00
total_reserved_usd       501.00
remaining_unreserved_usd 4499.00
no_automatic_refund      True
reservations             86
```

### The run outputs already measured (this is your baseline)
```
CNCM\records\typed_matched_001\receipt_20260917_a   ...and _m, 20260918_a/_m, 20260919_a/_m
    collected\results\artifacts\final_predictions.json     # per-slot scores + decisions
    collected\results\artifacts\final_scoring.json         # per-question correctness
    collected\results\artifacts\development_*_predictions.json   # the held-out panel
    collected\results\artifacts\retention_*_predictions.json
    collected\input\source.zip, collected\input\config.json
```
Six runs, 564 questions each. Arms `a` = `ALT_COMPONENT_WHOLE`, `m` = `MIXED_SAME_ITEMS`; seeds 20260917/18/19; encoder seed 20260916.

### Code built in this campaign
```
CNCM\cncm\answer_constraints.py                        # declared-constraint layer  (§4)
CNCM\cncm\analytic_decompose.py                        # closed-form ^6 init + rectangular solve (§3)
CNCM\tools\prepare_analytic_arm.py                     # arm-A preparation for the analytic init
CNCM\tests\test_answer_constraints.py                  # 21 tests
CNCM\tests\test_analytic_decompose_rectangular.py      # 13 tests
CNCM\tests\test_analytic_decompose.py                  # 31 tests (pre-existing)
CNCM\records\encoder_capacity_001\gpu_smoke_train.py   # local-GPU smoke driver, UNTESTED AND UNCOMMITTED (§7)
CNCM\records\analytic_decompose_phase0_001\PHASE0_RECORD_DRAFT.md   # DRAFT, UNSIGNED, authorises nothing
```

### All measurements and their records — `CNCM\records\encoder_capacity_001\`
Each `*_RESULT.md` has a matching script and a `*.txt` raw output. The load-bearing ones:

| record | what it establishes |
|---|---|
| `BITS_READ_RESULT.md` | per-bit reading accuracy per kind; validates 229/229 in all six runs |
| `BINDING_VARIANTS_RESULT.md` | the packet is inert per slot; the block discards a linear signal |
| `EDGE_DIRECTION_CORRECTION.md` | a bug of mine, found and fixed; supersedes `edge_account` rows elsewhere |
| `AUDIT_RESPONSE_AND_SELFLINKS.md` | an external audit's findings, all accepted; zero self-links in 649,728 declared edges |
| `ALL_DECLARED_CONSTRAINTS_RESULT.md` | constraints on `parts`, `definition`, `edge_account` |
| `CONSTRAINT_LAYER_RESULT.md` | **+6.6194 pooled, +12.4861 many-decision, +0.0000 one-decision** |
| `RECTANGULAR_REALISATION_RESULT.md` | the fitted-readout route is closed; 14.3813% → 4.0134% |
| `STRUCTURAL_CONSTANTS_RESULT.md` | the "declared by absence" class is exactly 8 cells |
| `DEVELOPMENT_PANEL_AND_ROBUSTNESS.md` | the held-out panel is unmeasurable from the receipt |
| `EXPOSURE_VS_STRUCTURE_RESULT.md` | not memorising worlds; exposure is not the explanation |
| `WIRING_AND_INVARIANCE_RESULT.md` | wiring costs one digest; the layer's gain is world-invariant |
| `DROP_IN_RESULT.md` | `score_decisions` is now a faithful drop-in |
| `PANEL_MISREAD_CORRECTION.md`, `INFORMATION_LOSS_WITHDRAWN.md`, `COLLAPSE_CLAIM_WITHDRAWN.md` | earlier self-corrections |

### Environment
```
Local CUDA venv (Windows): C:\Users\wakil\venvs\cas-gpu     # torch 2.11.0+cu128, cuda True, RTX 4070 8 GiB
WSL Ubuntu: wsl -d Ubuntu                                   # torch 2.5.1+cu121, cuda True, RTX 4070 visible
Pinned wheels (importable straight from sys.path, do NOT install):
  CNCM\research\CAS_CJT_TRANSFORMER_v0_2\artifacts\release_reproduction\dist\casformer_reference-0.1.0-py3-none-any.whl
  CNCM\research\CAS_CJT_TRANSFORMER_v0_2\artifacts\release_reproduction\dist\cas_neural_cjt-0.2.0-py3-none-any.whl
Test command: cd CNCM && python -m pytest -q      # 2186 passed, 767 subtests, ~40 min
```

---

## 2. WHAT THIS PROJECT IS

A 564-question typed-teaching examination over 64 declared "worlds". Each question has a `kind` (8 kinds), a focus world, and slots that must be answered. Three frozen components and one trainable one:

- **Frozen encoder** (`cas_meta2/typed_teaching/encoder.py`): `encode_slot` = `normalize((packet + query)/√2)`. Identity pinned by digest.
- **Frozen readout** (`[90, 64]`, one row per symbol).
- **Trainable `^6` block** (`_DecomposeTransform`, 16,384 params): `merge @ concat(tanh(left x), tanh(right x))`, run 8 recurrent passes.
- **Optimizer**: AdamW lr 3e-3, wd 0.01, 160 of ≤176 updates, depth 8, λ=0.5, ε=1e-6.

**The goal, in the owner's words:** a working CASformer/CNCM that uses the architecture's full potential. "IT MUST be learning at the neuron level. The architecture should be serving this purpose."

---

## 3. THE CENTRAL FINDING — the block destroys information its own encoder provides

**This is the single most important result. Do not re-derive it; verify it if you doubt it.**

A plain linear readout (ridge LDA) of the vector the block is handed reads the answer's bits at:

```
context          96.3758%      (the trained block returns 40.8240%)
parts            87.1525%      (block: 70.5314%)
edge_account     62.9181%      (block: 53.5471%)
```

**`context`: 96.38% linearly available → 40.82% after the block — far below the 78.6517% a constant answer earns.** The encoder is fine. The 16,384-parameter block, trained, discards what it was given.

Corroborating, all six runs:
- Held-out development panel: **0 of 59**, every cursor. Retention **falls** 46.8750% → 35.4167%.
- `edge_account`, `context`, `definition`: **0.0000% exact answers in all six runs.**
- `edge_account` balanced reading **54.6353%** (coin flip = 50%); 1,359 false alarms.
- Six runs collapse onto the same direction **`W36`**, which is **not a training target**.
- The block's weights **grew ×19.73** — so it is training, just not on the task.

**Therefore the fix is architectural, and the one with offline evidence is analytic initialisation.**

---

## 4. WHAT IS ALREADY BUILT AND MEASURED

### The analytic initialisation (Fix A) — **this is what to launch**
`CNCM\cncm\analytic_decompose.py`. It writes the `^6` matrices in closed form — `left = I`, `right = 0`, `merge = [T | 0]`, so `forward(x) = T·tanh(x)` **exactly** — with `T` solved to make the frozen readout behave as a fitted one. Measured out-of-fold:

```
62.94% direct          62.06% through the registered recurrence         1.24% trained block   = 50.0×
```

Recurrence-aware refinement is worth **+17.38 points** (naive 44.68% → 61.88% round 1 → 62.06% round 2). Robust to the ridge penalty (0.18-point spread over three orders of magnitude). Prepared by `CNCM\tools\prepare_analytic_arm.py`; proposal at `CNCM\records\analytic_decompose_phase0_001\PHASE0_RECORD_DRAFT.md` — **draft, unsigned**.

**Known limitation, measured in round 36:** `decompose_from_free_readout` needs a square readout and the registered readout is `[90, 64]`, so it refuses. `decompose_from_free_readout_rectangular` (added, 13 tests) handles it, but only the **projection** of a desired readout is reachable, and routing a *fitted* readout that way lands at **4.0134%**, below the machine's own 5.0167%. **So do not launch "install a fitted readout". The launchable form is the identity/transparent-read-path initialisation, which is exact.**

### The declared-constraint layer — built, tested, measured, **not wired**
`CNCM\cncm\answer_constraints.py`. Reads what the packet *declares* about a legal answer and corrects the decision. Measured on the recorded scores, all six runs, **truth-free**:

```
kind             q    unconstrained   constrained      lift    selections changed
parts          318        29.2453%      80.8176%   +51.5723%          71.0692%
definition     420         0.0000%      10.2381%   +10.2381%          97.6190%
context        420         0.0000%       4.0476%    +4.0476%          97.8571%
edge_account   420         0.0000%       0.0000%    +0.0000%          97.8571%
correspond/analogy/reach/role_set   +0.0000%, 0.0000% changed
ONE DECISION  1590        66.5409%      66.5409%    +0.0000%
MANY DECISIONS 1794        6.4103%      18.8963%   +12.4861%
ALL           3384        34.6631%      41.2825%    +6.6194%
```

**No trade-off**: the one-decision half is untouched. **And the wiring is cheap** — measured across 564 packets / 2,598 slots: `plan_digest` changes in 564 of 564, but **slot ids 0/564, encoder query spec 0/2598, encoder query bytes 0/2598**. The encoder, scores, model, readout and block are all unchanged.

`score_decisions(packet, scores, *, declared_constraints=False)` is a faithful drop-in: with the flag off it is byte-identical to `slots.score_decisions` (verified on 24 real packets with real recorded scores).

**Wiring is one line.** `slots.score_decisions` is called in one place: `cas_meta2\typed_teaching\learner.py` line 159, inside `_forward`.

### Rectangular solve
`decompose_from_free_readout_rectangular` in `CNCM\cncm\analytic_decompose.py`, 13 tests.

---

## 5. THE JOB — launch the analytic arm on AWS

**AWS is verified reachable from this machine.** Credentials at `C:\Users\wakil\.aws\` (and `C:\Users\wakil\.cas_llm_keys.env`); no `aws` CLI on PATH, which is fine — the launcher uses **boto3**. Verified this session:

```
identity      arn:aws:iam::807562639912:user/cas-g5-operator
instance_type g7.2xlarge   → 8 vCPU, 32768 MiB RAM, 1× RTX PRO 4500 with 32768 MiB
region        us-west-2
```

`typed_matched_launch.py` holds `BOUNDS = {"training": True, "optimizer_updates_max": 178, "max_wall_seconds": ..., "instance_type": "g7.2xlarge", "region": "us-west-2"}`.

### The exact invocation shape
`execute_study.py` requires **exactly six jobs** (`assert len(study['jobs']) == 6`). For a *different* arm you must either build a new study or call the launcher directly for one job:

```
python CNCM\records\typed_matched_001\prepare_study.py          # builds package + 6 jobs + admission
python CNCM\records\typed_matched_001\execute_study.py --execute <study.json path> <study.json sha256>
```
which calls, per job:
```
launch.main(['--execute',
  '--request',            <request.json>,   '--request-sha256',   <sha>,
  '--authority',          <authority.json>, '--authority-sha256', <sha>,
  '--owner-authorization',<owner.json>,
  '--receipt-dir',        <receipt dir>,
  '--ledger-path',        <CANONICAL_LEDGER>])
```

**Owner approval is already written into the design** — `prepare_study.py` line 39 records `'owner_instruction_raw': 'I give you approval for it all ....GO!'`, and `maximum_new_reservation_usd` is `'42.00'` for six jobs.

### Steps, in order
1. **Read `CNCM\records\MACHINE_STATE_001\STATUS.md` and `CNCM\records\analytic_decompose_phase0_001\PHASE0_RECORD_DRAFT.md`.**
2. **Decide the arm's design.** The launchable change is the analytic initialisation of the `^6` block (`left = I`, `right = 0`, `merge = [T | 0]` with `T` from `cncm.analytic_decompose`). The study's `DESIGN` comes from `cas_meta2\typed_teaching\matched_contract.py`; you will need to add the initialisation as an explicit arm parameter, and update `docs/CNCM_TYPED_MATCHED_STUDY_v0.1.md` (its sha256 is pinned into the admission — `prepare_study.py` line 19/81).
3. **Commit first. The package is built from `git rev-parse HEAD`** (`prepare_study.py` line 24). An uncommitted change will not ship. Commit the 3 dirty files (§7) and your design change.
4. **Run `prepare_study.py`.** It writes `CNCM\records\typed_matched_001\admission_001\` — **note `admission_001` does not currently exist in this checkout**, so this will be a fresh study. It also runs a Windows rehearsal and asserts `LINUX_WORKER_REQUIRED`; that assertion passing is expected, not a failure.
5. **Run `execute_study.py`** with the returned `study.json` path and sha256. It reserves against the ledger, launches `g7.2xlarge`, stops on first failure, and **has no automatic retries**.
6. **Optionally read the result** with `audit_complete_study.py`, `build_result_report.py`, `independent_work_audit.py` in `CNCM\records\typed_matched_001\`.

### Cost
Six jobs under this design were budgeted at **$42.00** (`maximum_new_reservation_usd`). Ledger has **$4,499.00 unreserved** against a $5,000.00 cap. Precedent for a novel workload is **two $7 reservations**. **`no_automatic_refund` is True** — a reservation is not returned automatically.

### What to look for in the result
A pass is **not** "the loss fell". The question is whether the neurons learn *the task*. Specifically:
- exact-answer accuracy on the **development panel** (currently **0 of 59** — any nonzero result is news),
- **retention** (currently *falls*, 46.8750% → 35.4167%),
- the four kinds at **0.0000%** (`edge_account`, `context`, `definition`, and `role_set` at 10.1852%),
- **and the information-destruction measurement**: take the trained block's output, fit a ridge LDA for the bits, and compare against the **96.3758%** available at its input. **If the block still returns ~40% where 96% is present, the architecture is still the problem regardless of the headline score.**

---

## 6. GOVERNANCE RULES THAT APPLY — read these before acting

From `CLAUDE.md` (in `CNCM` and at the worktree root) and `AGENTS.md`:

- **GPU-first / cloud-first.** No neural workload on local CPU (fail closed `GPU_REQUIRED`). Local RTX 4070 = smoke/dev only. **AWS GPU (EC2, not Bedrock) for every claim-bearing run.** Bedrock = teacher-language only.
- **Every run needs an owner-authorised record.** Approval must be *executable* (a signed record in the study's `owner.json` shape), not prose-interpretable.
- **A hard gate that fails is a FAILURE, never "PASS with caveats".**
- **Never delete a negative result.** Disconfirmations are load-bearing.
- **Never upgrade a claim status without an artifact path** in the same edit.
- **Keep every number exact** — never round.
- **Always update `CNCM\..\CHANGELOG.md`** (at the git root: `_worktrees\vision-next\CHANGELOG.md`) and the **CAS Harness spec sheet** (`_worktrees\vision-next\docs\CAS_HARNESS_SPEC_SHEET.md`) in the same commit as a result.
- **Always run `python -m pytest -q` from `CNCM` before committing.** Never commit code that breaks passing tests.
- **Commit and push after every meaningful unit of work.**
- **Plain English in every reply to the owner** — meaning first, then the precise term. The owner has repeatedly caught agents drifting into jargon.
- **Write boundary: everything goes inside `CNCM`.** Never write to `CAS_RRK_v0.1`.
- Claim-status vocabulary (use only these): `REAL` / `VALIDATED` / `LICENSED` / `NOT LICENSED` / `GREY` / `VACUOUS` / `WITHDRAWN` / `ENGINEERED-NOT-VALIDATED` / `FLAG_FOR_HUMAN_REVIEW`.

---

## 7. UNCOMMITTED FILES — commit or discard deliberately

`git status --porcelain` at `_worktrees\vision-next` shows **3** files, all from round 42:

```
CNCM\records\encoder_capacity_001\gpu_smoke_train.py        # local-GPU smoke driver. UNTESTED — its last
                                                            # run failed on a missing `casformer` import;
                                                            # the wheels are now on sys.path but the run
                                                            # after that fix was never completed.
CNCM\records\encoder_capacity_001\measure_bilinear_binding.py
CNCM\records\encoder_capacity_001\bilinear_binding.txt
```

**`bilinear_binding.txt` is a real negative result and should be kept:** adding a Hadamard product to the binding (`normalize((p + q + p⊙q)/√3)`) does **not** improve decodability — `context` 94.2490% → 94.5647%, `edge_account` 67.7176% → 67.3909%. It does make the packet reach the per-slot decision (100.0000% → 96.9874% agreement for `edge_account`, 88.0466% at 4× strength), **but that is not the bottleneck.** **The binding is not the problem; the block is.** Do not spend a run on the binding.

**`gpu_smoke_train.py`** is a dev smoke driver for the local GPU. It was written to answer "are the neurons learning?" by printing loss and probe accuracy per update. It needs `casformer` and `cas_neural_cjt` on `sys.path` (see §1) and a Linux platform (`execution_guard()` requires `platform.system() == "Linux"`), so run it under `wsl -d Ubuntu`. **The owner has said to use AWS instead of local, so treat this as optional.**

---

## 8. OPEN DECISIONS — these are the owner's, not yours

1. **Sign the phase-0 record.** `CNCM\records\analytic_decompose_phase0_001\PHASE0_RECORD_DRAFT.md` is complete and runnable end-to-end and **unsigned**. It needs arms approved (A/B/C), seeds approved, and a reservation amount. **It authorises nothing while unsigned.**
2. **OS-026.** For four of five many-decision kinds the query states `focus_world_id` directly and the world's declarations are in the packet, so the machine is asked to reproduce by classification an identifier the question supplies. **Is that the intended task?**
3. **OS-027.** The `^6` contract admits `plasticity_groups = ('operation:^6', 'bias_update_head')`; the run uses one group, and the `bias_update_head` (a real 4,096-parameter module) is **absent from the run's module**. Is that narrowing legitimate, or does it strand an admitted mechanism? **Round 30 measured that one shared map is the binding constraint, so this is no longer hypothetical.**
4. **Wire the constraint layer or not.** +6.6194 offline, one digest of cost, one line in `learner.py:159`.

---

## 9. TRAPS — mistakes already made; do not repeat them

**These cost this campaign weeks. Every one was found by running against real artifacts, not by reasoning.**

1. **A harness that reports nothing is usually the harness.** When a measurement reported `obs 0` with its *failure counters also 0*, the per-record logic was fine and the counter handling was wrong. When `edge_account` scored **0.0000% when handed the answer**, that was an impossible reading and it exposed a real bug: the per-slot truth sorted `(source, target)`, making a **directed** edge undirected and doubling the edge count. **It had corrupted five rounds of `edge_account` numbers.** See `EDGE_DIRECTION_CORRECTION.md`. **Treat an impossible reading as a bug report about your own instrument first.**

2. **A validation that confirms your oracle does not validate the layer you build on top of it.** The 229/229 check compared the machine's submitted answer to the checker's derived truth and passed six-for-six — correctly. It never touched the per-slot label mapping, which is where the bug was.

3. **Hand-built test fixtures hide real failures. Five rounds in a row.** The packet's world nodes carry `ref`, `kind`, `label` — **no `alias`**; aliases live in the plan's alias table. A fixture that put `alias` on the packet nodes made tests pass while real packets raised `KeyError`. Likewise `slots.compile_slots` runs full packet validation, so hand-built packets are rejected with `TYPED_SOURCE_PUBLIC_FIELDS` — **test the run's decoder against real packets.**

4. **Per-slot accuracy is a trap for `edge_account`.** Only 20.2138% of its edge slots are PRESENT, so **always answering ABSENT earns 79.7862% for free**. Report **edges found**, **false alarms** and **balanced accuracy**. Current: 460 of 1,248 edges found, 1,359 false alarms, **balanced 54.6353%**.

5. **`analogy` and `correspondence` admit 6–9 and 1–6 answers per question.** Correctness is **membership of the whole admissible set**, never equality with `admissible_answers[0]`. Comparing to the first element reports `analogy` at 0.00% when it scores 10–22.86%.

6. **A fixed hyperparameter across differently-scaled feature sets manufactures a capability difference.** An early "information loss" result was the ridge λ = 1.0, not the model. See `INFORMATION_LOSS_WITHDRAWN.md`.

7. **Do not add per-kind gains measured against different baselines.** Round 34's "+36.83 per run" was withdrawn because the pieces overlap; the measured combination from the module is a different number.

8. **The dev panel's `protocol_material.json` holds digests, not packets.** `packet_sha256`, `source_digest`, `slot_plan_digest` — no `source`, no `query`. **The development panel is unmeasurable from these receipts**; `course.model_packet` raises `TYPED_COURSE_RECORD_UNKNOWN`. Do not spend time trying.

9. **The packaged worker is Linux-only by design.** `cas_meta2\teaching_cycle\gpu_adapter.py::execution_guard` requires `platform.system() == "Linux"` and `CAS_META2_RUN_TEACHING_CYCLE=1`. On Windows it fails closed with `LINUX_WORKER_REQUIRED`. That is a deliberate gate, not a bug. **Use AWS.**

10. **The development panel is 6 `parts` + 53 `reach` over TEN-node worlds**, against the exposed course's four-node worlds, with `declarations_authority = NEW_CALLER_AUTHORED_DEVELOPMENT_FACTS_NOT_WORLD_TRUTH`. Size is not the in-course failure axis — three-node worlds score *better* (39.4203%) than four-node (33.4447%).

---

## 10. IF YOU ONLY DO ONE THING

**Read `CNCM\records\MACHINE_STATE_001\STATUS.md`.** It is 500 lines and contains every load-bearing number in this campaign with its artifact path. Then commit the 3 dirty files, make the analytic-initialisation arm explicit in the design, and launch it on `g7.2xlarge`.

**The thing to remember while you do it:** the machine is not failing because it cannot read. `context`'s answer is **96.3758% linearly available** in the vector the block receives. **It is failing because the trained block throws that away.** Any change you evaluate should be judged on whether the neurons keep what the encoder gave them — not on the headline score alone.
