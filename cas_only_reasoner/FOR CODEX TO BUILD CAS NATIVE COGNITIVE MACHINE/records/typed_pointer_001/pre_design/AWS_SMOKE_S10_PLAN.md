# AWS smoke job (S10) — plan and cost model

> Written 2026-09-19. HEAD `7b1ffca7`. **Not yet run.** This plans the one paid step that is not part of the
> three claim-bearing jobs: the end-to-end test of the worker on the real instance, which also produces the timing
> projection the owner's budget item depends on.

**Owner approval, 2026-09-19.** The owner selected the option whose exact label was *"Approve the smoke job
(Recommended)"*. The option as offered was: *"It costs well under $1, a few minutes. The project rule is to run the
worker end to end before every paid launch."* The question asked was: *"The worker only runs on the AWS GPU, so
testing it end to end before the real launch needs a short AWS job. It costs well under $1, a few minutes. The
project rule is to run the worker end to end before every paid launch. Approve it?"*

## 1. Why it cannot be done locally

The worker refuses to run anywhere except Linux with `CAS_META2_RUN_TEACHING_CYCLE=1`, torch `2.11.0+cu128`, and a
CUDA device; `execution_guard()` enforces it. The local RTX 4070 runs the network module fine (smoke S1–S9), but the
worker's own `run()` — phases, evidence publisher, attestation, delivery — is only exercised on the instance.

## 2. Cost model, derived from the real practice receipts

Not guessed. Read from `records/typed_practice_001/receipt_20260917/checkpoints/worker_report.json` and the
hand-off's instance figures.

| Quantity | Value | Source |
|---|---|---|
| Instance rate | $2.52 / hour, observed | hand-off §9 |
| Practice job instance time | 6,064 s | hand-off §9 |
| Practice worker's own clock | 5,465.811116456 s | `worker_report.json` `elapsed_seconds` |
| **Non-worker overhead** (boot, package install, delivery) | **598.2 s** | 6,064 − 5,465.811116456 |
| One full course evaluation (564 packets), warm | 173.78626021600007 s | `course_p01` |
| One full course evaluation, cold | 300.51911266499997 s | `course_p00` |
| One held-back evaluation (127 packets) | 38.470995152000114 s | `heldback_p02` |
| One development evaluation (59 packets) | 13.912109693000048 s | `development_p01` |
| Cost of the overhead alone | **$0.42** | 598.2 s × $2.52 / 3600 |

**Budget arithmetic.** The owner approved "under $1". At $2.52/hour that is **1,428.57 s** of instance time total.
Subtracting the 598.2 s of non-worker overhead leaves a **worker clock of at most about 830 s**. Everything the
smoke does must fit inside that.

**Per-update cost, estimated.** Main training ran 1,470 updates inside the job's 5,465.811116456 s. Subtracting the
evaluations that also ran (`course_p00/p01/p10` 648.1 s, held-back 155.7 s, development 97.1 s, retention 44.4 s,
reloads and replays roughly 60 s ≈ 1,005 s) leaves roughly 4,460 s for training, or about **3.0 s per update**.
This is an ESTIMATE derived from the receipts, not a measurement of the new machine; the smoke's job is to replace
it with a measurement.

## 3. What the smoke runs

The real worker, the real package build path, the real instance type and AMI, with a **shrunken schedule** so it
fits the budget:

| Phase | Smoke setting | Estimated worker seconds |
|---|---|---|
| preflight + packet build | real | small |
| checkpoint check **phase A** | **one seed, one checkpoint** (`initial`), not three × three | ~174 (one course pass) |
| seed + double build | real (this is where the ^6 identity check runs) | small |
| training | **8 updates**, not 1,470 | ~24 at the estimated 3.0 s/update |
| course evaluation | **one**, warm | ~174 |
| held-back evaluation | **one** | ~39 |
| retention + interference | skipped or minimal | — |
| reload + replay | real (the code path that fails without the checkpoint fixes) | ~60 |
| checkpoint check **phase B** | **skipped** (report-only, and it is the expensive half) | 0 |
| ablations | skipped | 0 |
| source verification + deliver | real | small |

Estimated worker clock ≈ 470 s, plus 598.2 s overhead ≈ **1,070 s of instance time ≈ $0.75**. Under the approved
$1 with margin. If the smoke's own measurement shows the estimate was low by more than about 25 %, the run must be
killed rather than allowed to exceed the approved amount.

### 3.1 The whole GPU smoke runs HERE — S1 through S9 included, not on the laptop

**Owner order 2026-09-19, verbatim:** *"STOP SAY FOCUSING ON '$0.00 spent. Nothing on AWS.' BECAUSE WE ULTIMATELY NEED
AWS TO GET TO THE BEST VERSION OF OUR BUILD/PRODUCT AND WE ALWAYS ALWAYS US AWS BECAUSE IT FASTER THAN RUNNING LOCALLY
AND SAVES US LOCAL PROCESSING POWER FOR OTHER THINGS IF NECESSARY IT'S A FUCKING LAPTOP SO IT GPU IS NOT THAT STRONG
PLEASE REMEMBER THIS SO USE AWS"*.

The hand-off's earlier plan put S1–S9 on the local RTX 4070 and only S10 on AWS. **That is superseded.** The local
GPU is a laptop GPU; it is not a smoke-test venue, and its power belongs to other work. **Every one of S1–S10 runs in
this one AWS job**, which is the cheapest way to obey that because they share the same boot, the same package
install and the same instance:

| check | what it establishes | added cost |
|---|---|---|
| S1 | all 8 kinds forward and backward under deterministic mode, bit-identical twice | small |
| S2 | `train_sealed_batch` on a batch missing most kinds, and on an interference batch | small |
| S3 | export → restore → predict identical; replay from prelast equals final | small |
| S4 | evaluation leaves the learned state unchanged | small |
| S5 | identical start with the checkpoint check on and off; the three `^6` tensors match the recorded start | small |
| S6 | phase A restores and rebuilt logits equal `restored.predict` bit-for-bit; a forced failure still writes its artifact | small |
| S7 | time one pass plus one evaluation → the projection | shares the run |
| S8 | score bounds `|score| ≤ 1e6` and loss agreement `≤ 2e-5` | small |
| S9 | **no order-like channel beyond the registered rank** — with rank now excluded, assert the reading carries no rank feature at all, and that a node influences the answer only through its declared flags | small |
| S10 | the worker's `run()` end to end on the shrunken schedule | the bulk |

None of S1–S9 trains anything, so together they add only a few minutes and leave the total **under the approved
$1**. They are not claim-bearing and are recorded as plumbing.

### 3.2 AWS is not merely preferred here — it is the ONLY venue, by construction

Measured 2026-09-19 from the built code, and it confirms the owner's order rather than merely agreeing with it:

- `PointerCourseLearner.__init__` (`pointer_learner.py:1177-1180`) calls `execution_guard()` and then requires
  `re.fullmatch(r"cuda(?::[0-9]+)?", device)` **and** `torch.cuda.is_available()`, or raises
  `TYPED_LEARNER_CUDA_REQUIRED`.
- `execution_guard()` (`teaching_cycle/gpu_adapter.py`) requires `platform.system() == "Linux"`
  (`LINUX_WORKER_REQUIRED`) and `CAS_META2_RUN_TEACHING_CYCLE == "1"` (`EXPLICIT_ENABLE_REQUIRED`).

So the learner **cannot be constructed on this Windows laptop at all**, and it cannot be constructed on CPU
anywhere. There is no local fallback to weigh against AWS; the guard is the reason the project's GPU-first rule is
enforceable rather than advisory.

**One thing to be straight about.** While building the learner, a sub-agent ran a **shape-only** check on the local
GPU by monkey-patching `execution_guard` to a no-op inside a throwaway script in `_scratch/`. The guard's own code is
untouched, no training ran, and the check took seconds — but it predates the owner's AWS-first order and it is the
kind of thing that should not become a habit. **The equivalent check is S1 in the table above, and it belongs in the
AWS job.** No further local GPU work is planned.

**A concrete reason this matters, from this session.** Checking a single flag required a material load that **timed
out at 120 s on the laptop** — and the same load is what every test file does. The local machine is not just slower;
it is slow enough to make ordinary verification awkward.

## 4. What it must measure, and what that buys

1. **Seconds per update and per evaluation, measured on the real instance for the new machine.** From these,
   project the full job: `598.2 + PASSES × 147 × s_per_update + evaluations + phase A + phase B`.
2. **The projection against the deadline.** The worker deadline is `WORKER_DEADLINE_SECONDS = 12300`. The owner's
   threshold is about **11,000 s**: if the projection exceeds it, a larger per-job reservation needs a NEW owner
   approval, because the approved envelope is ~$13 expected and $45 reserved in total.
3. **Cores calls, which may bind before the deadline does** — and this one is not optional.
   `pointer_contract.py:107-110` requires the smoke measurement to *"re-check `MAX_CORE_CALLS`: the pointer machine
   calls the registered `^6` block once per node per round (~4 nodes × 8 rounds = 32 calls per world read) against
   the old machine's 8, so the core-call budget may bind before the update budget does. Both are recorded in DESIGN
   and must be reconciled before the study is frozen."* The smoke must therefore read `core_forward_calls` from its
   own counter snapshots over **the passes it actually ran**, and divide `MAX_CORE_CALLS` (`600000`, inherited from
   the practice study) by the measured per-pass core calls to obtain a second, independent pass limit:
   `PASSES = min(deadline-limited, core-call-limited)`. Setting `PASSES` from the clock alone risks a job that
   trains happily and then dies on `MAX_CORE_CALLS` **after the spend**.
4. **That the worker's full path executes end to end** — every phase in order, every expected artifact written, the
   evidence publisher create-only, source verification clean, delivery complete.
5. **That phase A completes before the model is seeded** (the RNG-overwrite ordering), and that phase B's absence
   is recorded as `SKIPPED` with a status field rather than silently missing.

> **Amended 2026-09-19, before the run.** Items 1, 3 and 4 were added or corrected here. The `1470` this section
> first carried is `10 × 147`: the stratified schedule runs **147 updates per pass** at **1,176 presentations per
> pass** against the practice study's 818 (+358, +43.8 %) — `pointer_contract.py:43,46,50`, which also records that
> the *update* count is unchanged at 147. `1470` is right only at `PASSES = 10` and wrong for every other value, so
> the projection is now written in terms of `PASSES`, the one open value in the frozen protocol
> (`pointer_contract.PASSES`, currently 10, inherited from the practice study and explicitly *"NOT FREEZABLE
> AS-IS"*, `pointer_contract.py:90`). Measured per-update cost must also be read against the stratified figure: the
> practice study's ~3.0 s/update was at 5.56 presentations per update, and the stratified pass runs 8, so the same
> measurement is expected to be about 1.438 × the old one — that rise is the cost of the owner's "Stratify AND train
> longer" decision, already paid for in advance by the `LEARNER_MAX_UPDATES_CEILING` raise from the practice
> ceiling of 2,048 (which would have REFUSED 14 passes) to 3,544 (`pointer_contract.py:102-105,113`).

## 5. Pass and fail

**PASS** requires all of: the worker reports its success status; **every name in the worker's own
`required_artifacts`** — the set it records in `schedule_plan.json` for the plan it actually ran — is present;
`final_source_verification` passes with no failed imports; the evidence publisher reports zero conflicts and zero
non-atomic writes; the measurement file carries per-phase seconds; and the projected full-job time is computed and
written down.

> **Corrected 2026-09-19, before the run.** This rule first read "every name in `EXPECTED_ARTIFACTS` is present",
> which the shrunken schedule in §3 makes **impossible to satisfy**. `EXPECTED_ARTIFACTS` is derived from the
> registered plan — `cncm/typed_pointer_worker.py:237`, `expected_artifact_names(FULL_PLAN)`, which is
> `2 × PASSES + 79` names (99 at `PASSES = 10`, confirmed by import) — while a reduced run writes the smaller set
> for the plan it actually ran. As written, the smoke would have had to be marked FAIL for doing exactly what §3
> prescribes.
>
> The correction is **not** a relaxation. The worker enforces
> `set(required) - {"worker_report.json", "measurements.json"} ⊆ present` on that same recorded set
> (`cncm/typed_pointer_worker.py:1411-1414`), and on a full run `required_artifacts` **is** `EXPECTED_ARTIFACTS`.
> `schedule_plan.json` records `required_artifacts`, `registered_required_artifacts` and
> `artifacts_differ_from_the_registered_contract`, so this reading is checkable rather than assumed.

**FAIL** on any of those, or on exceeding the cost budget. On failure: read the console output (free) before
re-spending, never guess-and-relaunch. The smoke result is **NOT claim-bearing** — it tests the plumbing, not the
learning, and it must be recorded as such.

> That last sentence is enforced, not merely promised. The reduced schedule sets `claim_bearing = False`
> (`cncm/typed_pointer_worker.py:273-277`) and records `mode: "REDUCED"` in `schedule_plan.json`, and the frozen gate
> program refuses such a receipt outright: `records/typed_pointer_001/evaluate_gates.py:130` carries the void path
> `I1:<seed>:REDUCED_SCHEDULE:<mode>` — *"the job did not run the REGISTERED plan, so it is not a claim-bearing run
> and may not print a label"*. A smoke receipt cannot be promoted to a label even by mistake.

## 6. Governance

- This is a **fourth** AWS job beyond the three approved claim-bearing ones. Its reservation must be small (the
  approved amount, well under $1) and recorded through the launcher's own reservation path into the canonical
  ledger at the `meta1` worktree path — **never by hand**. The CNCM-tree copy of the ledger is a stale snapshot that
  `validate_ledger_path` refuses.
- The owner's approval covers this step; no new approval is needed unless the projection in §4.2 crosses 11,000 s.
- The smoke's job name uses the same `tpntr` study token, and its artifacts are sealed exactly like a real job's.

## 7. Open questions this plan does not answer

- `UNCERTAIN:` whether the smoke should run phase A on one checkpoint or all three. One checkpoint tests the code
  path and fits the budget; three tests the comparison itself. Recommendation: one checkpoint, because the point of
  S10 is the plumbing, and phase A's full form is exercised in the real jobs.
- `UNCERTAIN:` whether the 8-update training slice is long enough to expose a mid-run failure like the score bound
  (`|score| <= 1e6`) or the loss-agreement limit. The local smoke S8 covers those directly and cheaply; the AWS
  smoke should not be stretched to duplicate it.
