# AWS smoke job (S10) — plan and cost model

> Written 2026-09-19. HEAD `7b1ffca7`. **Not yet run.** This plans the one paid step that is not part of the
> three claim-bearing jobs: the end-to-end test of the worker on the real instance, which also produces the timing
> projection the owner's budget item depends on.

**Owner approval, 2026-09-19, verbatim:** *"Approve the smoke job."* The option offered was: *"It costs well under
$1, a few minutes. The project rule is to run the worker end to end before every paid launch."*

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

## 4. What it must measure, and what that buys

1. **Seconds per update and per evaluation, measured on the real instance for the new machine.** From these,
   project the full job: `598.2 + 1470 × s_per_update + evaluations + phase A + phase B`.
2. **The projection against the deadline.** The worker deadline is `WORKER_DEADLINE_SECONDS = 12300`. The owner's
   threshold is about **11,000 s**: if the projection exceeds it, a larger per-job reservation needs a NEW owner
   approval, because the approved envelope is ~$13 expected and $45 reserved in total.
3. **That the worker's full path executes end to end** — every phase in order, every expected artifact written, the
   evidence publisher create-only, source verification clean, delivery complete.
4. **That phase A completes before the model is seeded** (the RNG-overwrite ordering), and that phase B's absence
   is recorded as `SKIPPED` with a status field rather than silently missing.

## 5. Pass and fail

**PASS** requires all of: the worker reports its success status; every name in `EXPECTED_ARTIFACTS` is present;
`final_source_verification` passes with no failed imports; the evidence publisher reports zero conflicts and zero
non-atomic writes; the measurement file carries per-phase seconds; and the projected full-job time is computed and
written down.

**FAIL** on any of those, or on exceeding the cost budget. On failure: read the console output (free) before
re-spending, never guess-and-relaunch. The smoke result is **NOT claim-bearing** — it tests the plumbing, not the
learning, and it must be recorded as such.

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
