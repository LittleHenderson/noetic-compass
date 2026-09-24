# HELM-REPAIR-CONTROLLED-1: study slots, caps, receipts and the admission gate

Label `CLAUDE_BUILT_CLAUDE_CHECKED`. Answers Codex `codex-0007`, the builder review of `bb942461` and, in **v2**, the
Codex decisions Q1-Q9 and R3-F (`POLICY_DECISIONS_20260924.md` and `SPEND_STATIC_REVIEW_20260924.md` findings 1-2, at
`c3a128ee` on `codex/helm-controlled-prelaunch-20260924`). See `REVIEW.md`, section "v2 (Codex Q1-Q9)". Every number
below is program output from `study_spend.py` on 2026-09-24. Never edit `STUDY_SPEND_STATE.json` by hand; re-run the
program.

## Where things live

| File | What it is |
|---|---|
| `STUDY_SLOTS.json` | **The ONE list of slots** (schema `0.4`). Each slot: status, cap, the cap's arithmetic basis, the receipt spec, and (once admitted) its admission record. Plus `attempt_rows`: the append-only list of retry and reissue attempts (v2) |
| `study_spend.py` | Reads the list and every receipt **fresh** on every run. Report mode writes `STUDY_SPEND_STATE.json`. `--admit SLOT` is the gate; on ADMIT it writes the row as `RUNNING`. `--launch-check SLOT` is the last check immediately before RunInstances (v2) |
| `STUDY_SPEND_STATE.json` | Output only: bounds, totals, latches, and a money-gate **preview** for every planned row (a preview is not an admission) |
| `ADMISSION.lock` | The single-writer admission lock (v2). Created by `--admit`, kept while its admission is open, **never committed** |
| `test_study_spend.py` | 80 small synthetic tests: `python -B test_study_spend.py` (two of them build tiny real git repositories in a temporary folder; no network). One test per v2 rule: `test_v2_r1` ... `test_v2_r9`, `test_v2_q5`, and the verifier's X1, X2, X3 |
| `REVIEW.md` | The review findings on `bb942461`, rounds 2-4, and v2, and what was done about each |

## What is frozen, and what can change

**Frozen in the code** (never read from the file; if the file disagrees, exit 2):

- the **$60.00** ceiling; the owner's **$30.00** stop before the **3rd** main training attempt; the **$0.10**
  S3/transfer/retention allowance per job; the **300-second** admission validity (v2);
- the **slot definitions**: the slot set, every cap, cap basis, mandatory flag, stop flag, seed, arm, precondition and
  note, the open-question list, and the **whole rows** of S1, S2, P1a and PRIOR (done before the gate existed, or
  declared prior spend). Their digest must equal `FROZEN_DEFINITIONS_SHA256`
  (`a9fed7896aab374c6c2ce994dfe697999e37c960366107a1532b7d66b1760ecb`, schema 0.4; it was
  `82e809500f14ad8988b3b45ad6a7265f0601a5791f13cb8ea5a4608771456764` at schema 0.3). Changing any of them needs a
  reviewed code change.

**The v2 schema revision** (0.3 to 0.4) is prospective implementation preparation, recorded in `REVIEW.md`. It added the
PRIOR row, replaced the M1-M6 precondition lists with Codex's Q5 list, rewrote the open questions as decided or open,
rewrote the owner-stop texts, and added the empty `attempt_rows` list. **S1, S2 and P1a are byte-identical**, and no
row's status, receipt, admission or attempts changed. No statistical rule changed.

**Can change** (only for rows other than S1, S2, P1a, PRIOR): `status`, `receipt`, `invalid_reason`, `admission`,
`attempts`, `cancellation`, `closure`; and `attempt_rows` may grow at its end. Moves go forward only. The program checks
this against **every committed version** of `STUDY_SLOTS.json` (`git log --full-history`); a violation is exit 2:

| Once committed as | It may later be |
|---|---|
| `RUNNING` | `RUNNING`, `DONE`, `INVALID` or `CLOSED_NO_LAUNCH`, always with the same admission record. **Never `PLANNED` again** |
| `DONE` | `DONE` or `INVALID`, always with the same receipt and admission record |
| `INVALID` | exactly the same, forever |
| `CANCELLED_NOT_LAUNCHED` (v2) | exactly the same, forever |
| `CLOSED_NO_LAUNCH` (v2) | exactly the same, forever |
| an attempt row, in any status | still there, with the same slot and number; the list only grows at its end |

No committed `RUNNING`, `DONE`, `INVALID`, `CANCELLED_NOT_LAUNCHED` or `CLOSED_NO_LAUNCH` row may disappear.

## How the runner uses it (v2)

```text
python -B study_spend.py                                               # report; exit 0, or 1 (a rejected or shared
                                                                       # receipt, an unconfirmed cleanup, a latched
                                                                       # breach, a wrong identity, an uncertain start),
                                                                       # 2 on any input error
python -B study_spend.py --admit P1b --source <40-hex> --bundle <64-hex> --worker <64-hex> --checker <64-hex>
python -B study_spend.py --launch-check P1b                            # immediately before RunInstances
```

1. Commit and push `STUDY_SLOTS.json` and `study_spend.py`, then `git pull --ff-only`. The gate refuses while either
   file differs from HEAD, and unless HEAD equals the tip of the current branch's upstream that it fetches itself.
2. **`--admit <row> --source --bundle --worker --checker`** (all four hashes, for every slot: v2 R4). It takes the
   single-writer lock `ADMISSION.lock`, recomputes everything, and on exit 0 writes the row `RUNNING` with its
   admission record. The record binds: the admission time and `valid_until_utc` (**admission + 300 s**), the recomputed
   `inventory_sha256`, `gate_version`, `program_sha256`, the slots file before, `cap_usd`,
   `remaining_mandatory_reserve_usd`, `cumulative_upper_bound_usd`, `main_starts`, the lock nonce, and the launch
   identity (source, bundle, worker, checker; seed and arm for training).
3. **Commit and push the `RUNNING` row.** If the push is refused, another runner got there first: do not launch.
4. **Prepare** the job from the **admitted** source (not from HEAD, which is now the `RUNNING` commit).
5. **`--launch-check <row>`, immediately before RunInstances.** Exit 0 (`LAUNCH_ONCE`) only if the lock is still this
   admission's, it has not been used, the time is before `valid_until_utc`, the admission is committed and pushed as
   written, and the recomputed pre-admission inventory hash equals the admitted one. It then marks the lock used.
   Expiry, a second use, a changed input or a lost lock refuses: a fresh check is needed.
6. **Launch once.** Exit 0 authorizes exactly **one** RunInstances attempt, now.
7. When the job ends, fill the receipt pins, set `DONE` (or `INVALID` with a reason), run the report, check it, commit
   and push. Only then can the next `--admit` pass. The next `--admit` releases the old lock once its row is settled.

**If the admission is not used** (expired, the check refused, or the launcher failed before RunInstances): set the row
`CLOSED_NO_LAUNCH` with a `closure` (`reason`, `evidence`, and for a training launcher that failed before RunInstances,
optionally its pinned `pointer_prelaunch_failure` receipt). Then append the next attempt row and admit that. Never
rewrite a `RUNNING` row as `PLANNED`.

## One admission, one attempt; retries are attempt rows (v2 R1, Codex Q9 and static review finding 1)

- **One admission authorizes exactly one RunInstances attempt.** No retry under an admission, inside or outside its
  window. A row that lists more than one attempt in `attempts` is a **latched breach** (below): every admission is
  refused, even after its cleanup. The `attempts` field stays only so that such a violation is counted and seen.
- **A retry is a new attempt row** in `attempt_rows`: `{"id": "M1.2", "slot": "M1", "attempt": 2, "status":
  "PLANNED", "receipt": <planned spec>}`. It carries the slot's frozen definition (cap, basis, seed, arm, flags). It
  may be appended only when the previous attempt is settled (`DONE`, `INVALID` or `CLOSED_NO_LAUNCH`), with the next
  number. While `PLANNED`, a mandatory attempt row's cap is **reserved**.
- **Its own fresh `--admit`** covers the prior spend (every earlier attempt counted), confirmed cleanup of every earlier
  attempt (any unconfirmed cleanup refuses), the replacement cap, the owner stop and every remaining mandatory reserve.
  Example (test): M1's attempt 1 was an AWS capacity refusal ($1.60); `--admit M1.2` totals $7.04 + $11.66 + $39.98 =
  **$58.68**, and the decision names "the replacement cap of attempt 2 of M1".
- **An expired, unused admission** is closed as `CLOSED_NO_LAUNCH` with proof of no launch and reissued through the next
  attempt row. It is never rewritten as `PLANNED` (that is exit 2, `HISTORY_VIOLATION`).

## The unlisted-attempt search (round 4, tightened in v2 R3)

For every `DONE`, `INVALID`, `CLOSED_NO_LAUNCH` or overdue `RUNNING` row, the program searches for launch attempts the
row does not list. A finding, or a search that cannot run, makes the row's cleanup `UNCONFIRMED`, which refuses every
admission.

- **Training rows.** Every `result.json`, `*_result.json` and `provider_NNNN.json`, at any depth, under
  `records/typed_pointer_001/` and under the folder that holds each listed receipt's folder, read at HEAD, at every
  listed commit, and in the working tree. A finding is a job id with this row's **seed**, prepared inside its search
  window (admission time + the lifetime: 14,400 s), with **any source prefix** (v2; round 4 matched the admitted
  source only, which missed the verifier's X2), in a file that is not **listed**.
- **Listed means path AND sha256** (v2; round 4 skipped a listed job id everywhere, which missed X3). A file is listed
  when it is the listed receipt itself (its path and pinned sha256). Beside it, in its folder at the listed commit,
  and only when that commit's copy of the receipt has the pinned sha256 and one job id (v2.1, after the conformance
  check of `d5c8184a` found a hidden attempt inside the listed receipt's folder counted as listed): (a) a
  `provider_NNNN.json` directly in that folder (no subfolder) whose job ids are exactly the receipt's job id; (b) a file
  whose sha256 equals the worker-result pin the receipt itself carries (`collected.result_sha256`), which is what the
  launcher's two copies of the attempt's own worker result are (`curriculum_result.json`,
  `collected/results/result.json`). No other `result.json` or `*_result.json` counts. Another row's listed file is
  that row's.
- **Watched rows** (P1b, P2, E1). Every `*launch_record.json` and `*watch_record.json` under the design folder, on disk
  and at HEAD. A record is skipped only when its **sha256 equals a listed pin or its instance id is listed** (v2;
  never by its path alone, which missed X1), or when another row claims it the same way. A finding is one launched
  inside the window, or, with no readable launch time, inside the row's job folder.
- **S1, S2, P1a** (no admission, so no window): S1 and S2 against every job id with their own seed and their own source
  prefix, at any time; P1a against every watched record under its job folder. On the real data this finds nothing:
  **S1, S2 and P1a are the complete set of attempts of their jobs** (the round-4 verifier's full history search).
- **What the search cannot see:** a receipt only on another branch at a commit no listed attempt pins; a deleted
  receipt; a training job prepared outside the window. Commit every attempt, never delete or move one.

## Receipt validation

A receipt is **rejected** if any of these fail:

- **Pinned bytes.** The file's sha256 must equal the pin. A watched job's paths must stay inside the design folder.
- **Identity against the spec.** Job id, source commit, instance id (and, for watched jobs, launch time and bundle) must
  equal the spec, in both the launch record and the watch record.
- **One receipt, one attempt.** No identity may be claimed by two rows, or twice in one row. If one is, both receipts
  are rejected and every admission is refused.
- **Its own admission** (every admitted row):
  - the admission record is one `--admit` wrote (gate, program, slots-before, and the v2 binding fields) and a
    committed version showed the row `RUNNING` with it;
  - **the launch time lies inside the 300-s validity** `[admitted_utc, admitted_utc + 300 s)` (v2 R2; it was the
    whole lifetime). A training receipt shows no launch time, only the time its job id was **prepared**, so a training
    job is prepared after its admission and launched inside the same 300 s;
  - a training receipt's own model seed is the slot's seed;
  - **the receipt shows the admitted source, bundle, worker and checker** (v2 R4, Codex Q8) at these fields:

    | Slot kind | source | bundle | worker | checker |
    |---|---|---|---|---|
    | training | `authority.source_sha` | `authority.archive_sha256` | `authority.worker_sha256` | `authority.checker_sha256` |
    | watched | `identity.source_commit` | `bundle.sha256` | `identity.worker_sha256` | `identity.checker_sha256` |

    A missing or different value is `IDENTITY_NOT_THE_ADMITTED`: the result is rejected (mark it `INVALID`) and
    **every new admission is refused** (`WRONG_IDENTITY_BLOCKS_THE_STUDY`). The cleanup check still inspects the actual
    launched instance, and its cost is still counted. **Today's launchers do not write `worker_sha256` or
    `checker_sha256`**, so each launcher used from now on must add them (open item 10 below).
- **Numbers.** Every number finite; elapsed above 0 and within the basis; a watcher cost at least 0 and at most the cap.
- **Cleanup fails closed.** Confirmed only when hash-verified records show this row's own machine gone (training:
  cleanup complete, identity certain, the one instance `CONFIRMED_TERMINATED`, nothing pending, no failure; watched:
  terminated, final state terminated or gone, no volume left, same instance and launch time in both records), or a
  **proven capacity refusal** (the S1 rule). Otherwise `UNCONFIRMED`: every admission is refused, even after
  `INVALID`. A receipt that is not this row's launch (wrong time, wrong seed) never confirms.
- **Cost scope.** The machine must be one the basis lists, at its own listed price; disk and deadline within the basis;
  the job's own ceiling equals the cap; the watcher cost not below the cost from its timestamps.

**The S1 rule is ACCEPTED (Codex Q1, v2 R8)**, conditional on the pinned provider failure evidence: AWS's
`InsufficientInstanceCapacity` answer to `RunInstances` with zero client retries, as the last provider record
(`provider_0025.json`, sha256 `d866fbf594c76b09e591dbd96c6df0ecc712386d54d37e34ef21ca4be2da2b33`), no launch, no instance
or pending termination, the security group deleted and the roles removed, and the only cleanup failure
`INSTANCE_IDENTITY_UNKNOWN_AFTER_LAUNCH_ATTEMPT`. Every report prints this evidence under `override_resolved_by`. It is
counted at the elapsed-time bound ($1.60), not proof of the invoice. It is never reused for an ambiguous launched job.

## Latches (v2): what stops the study for good

| Latch | Rule | Cleared by |
|---|---|---|
| `LIMIT_BREACH_LATCHED` | Codex Q4: a job went past an admitted limit: any cost figure above its cap, or `ELAPSED_OVER_BASIS`, `INSTANCE_SECONDS_MAX_OVER_BASIS`, `DISK_OVER_BASIS`, `DEADLINE_OVER_BASIS`, `MACHINE_NOT_IN_BASIS`; or a second attempt under one admission | nothing: it holds after `INVALID` and after the cleanup is confirmed |
| `WRONG_IDENTITY_BLOCKS_THE_STUDY` | Codex Q8: a receipt does not show the admitted source, bundle, worker or checker | nothing |
| `MAIN_START_UNCERTAIN` | Codex Q3/Q6: a main attempt whose start cannot be proven either way | nothing |
| `CLEANUP_UNCONFIRMED_STOP_AND_REPORT` | a machine or disk may still exist | nothing |
| `COMPARISON_INCOMPLETE` | Codex Q7: a mandatory row was cancelled; refuses every **main** admission (M rows and their attempt rows) | nothing |
| `OWNER_STOP_TRIGGERED` | the $30 stop, below | nothing: settled rows only move forward |

A `CLOSED_NO_LAUNCH` row with proof that no instance was created (a prelaunch tool failure, or an unused admission)
does **not** latch anything (Codex Q4).

## Counting

| Status | How it is counted |
|---|---|
| `PLANNED` | Nothing spent. If mandatory, its cap is reserved (attempt rows too) |
| `RUNNING` | Its full cap (more, if a receipt it names shows more), plus every earlier listed attempt |
| `DONE`, receipt accepted | The bound computed from its receipt |
| `DONE`, receipt rejected | The larger of the cap and every cost figure the receipt shows. Every admission is refused until `INVALID` |
| `INVALID` | The larger of the cap and every cost figure its receipt shows, forever |
| `CANCELLED_NOT_LAUNCHED` (v2) | $0.00. An optional row's cap leaves fallback B; a **mandatory row's cap stays reserved** |
| `CLOSED_NO_LAUNCH` (v2) | $0.00 when proven (the search of its admission window finds no launch; a pinned prelaunch-failure receipt shows no launch, no instance and no RunInstances call in its folder); otherwise the full cap and `UNCONFIRMED` |
| PRIOR (v2) | its declared total, rounded up |

"Every cost figure the receipt shows" means the recorded cost plus allowances, the cost from its timestamps, and the
cost at its own deadline or instance-seconds limit, each at the highest price the receipt or the basis shows. The
receipt is read for these figures first, so an empty spec field or a stale pin can reject a receipt but never shrink
its count.

## The all-services bound

| Job type | Bound |
|---|---|
| Training (S1, S2, M1-M6 and their attempt rows) | elapsed (at most 14,400 s) x $2.52/h + the launcher's declared $1.48 ancillary + $0.10 S3/transfer/retention |
| Watched T4 or CPU (P1a, P1b, P2, E1) | (machine price + $0.005/h public address + disk GB x $0.08 / 730 h) x time + $0.10 + an evidence-collection allowance (E1 only: $0.10) |
| PRIOR | the five earlier jobs' declared watcher figures, no allowance added |

- The $0.10 allowance covers S3 requests, transfer out of AWS and **12 months** of storage of up to about 0.36 GB. The
  plan's horizon was execution + 30 days after E1. Both assumptions stay visible; retention beyond 12 months is outside
  the bound (open question 5).
- The $1.48 is the launcher's declared allowance, not a provider invoice.
- Every cap must cover its own basis, or the program stops with exit 2.

## Slots

| Slot | What | Status | Machine | Cap | Basis worst case | Counted now | Timing feasibility |
|---|---|---|---|---|---|---|---|
| S1 | switch-ON smoke attempt 1 (AWS capacity refusal) | DONE | g7.2xlarge, never created | $11.66 | $11.66 | **$1.60** (exact $1.597966) | n/a |
| S2 | switch-ON smoke attempt 2 (passed) | DONE | g7.2xlarge `i-039b7ae505c4c6245` | $11.66 | $11.66 | **$3.29** (exact $3.281907) | measured |
| P1a | larger-question route checks, both arms | DONE | g4dn.2xlarge `i-09e14d4afd0e0ebfa` | $3.00 | $1.77 (exact $1.763911) | **$0.55** (exact $0.5489) | measured: 35.1 min |
| PRIOR | earlier preparation jobs (v2 R9; scope pending the owner) | DONE | none (declared) | $1.92 | $1.9180 | **$1.92** | n/a |
| P1b | reader acceptance + corrected-probe validation + admission validation | PLANNED | g4dn.2xlarge or g4dn.xlarge | $2.00 | $1.77 | $0.00 | **not established** (not built; Codex: P1b runs on the historical g7 environment and needs its own priced launcher, so this T4 cap is not an accepted g7 budget) |
| P2 | HSET-2 custodian build | PLANNED | c7i.2xlarge | $1.00 | $0.91 (exact $0.908078) | $0.00 | sister job HSET-1A measured 30.1 min |
| M1 | unchanged reproduction, seed 20260917 (arm UNCHANGED) | PLANNED | g7.2xlarge | $11.66 | $11.66 | $0.00 | Helm 2.0 measured 10,471.8 to 10,529.1 s |
| M2-M4 | repaired seeds 20260917, 20260918, 20260919 (arm REPAIRED) | PLANNED | g7.2xlarge | $11.66 each | $11.66 | $0.00 | as M1 |
| E1 | evidence collection + TEST readout + 18 checkpoint probe reads + gates + partial-study path | PLANNED | g4dn.2xlarge or g4dn.xlarge | $2.00 | $1.87 (exact $1.863911) | $0.00 | **not established** (not built) |
| M5, M6 | fallback B: unchanged seeds 20260918, 20260919 (arm UNCHANGED), optional | PLANNED | g7.2xlarge | $11.66 each | $11.66 | $0.00 | as M1 |

**PRIOR** lists analogy_repair_t4_job attempt 1 $0.5596 and attempt 2 $0.67, aws_probe_job $0.4834, hset1a_aws_job
attempt 1 $0.0223 and attempt 2 $0.1827: $1.9180, rounded up to $1.92. These are the jobs' own watcher figures, not
validated by this program, and their cleanup is not re-checked here. They are included conservatively so no charge is
hidden, **pending the owner's scope decision**; they are never excluded merely to fit.

### M1-M6 preconditions (Codex Q5; declared, checked by the separate technical admission, not by the money gate)

Every main row lists its slot-specific conditions, then Codex's common list. The money gate prints them with every
decision. No inference may be made from a status label without opening and checking its bound public receipts. The
money gate and the technical gate both run.

- **M1:** the unchanged source (Helm 2.0, 20208c92) and M1's launch folder are reviewed; M1 is the first training slot
  admitted (plan order); P1b passed; E1 is built and reviewed.
- **M2, M3, M4:** the repaired source is built and reviewed; **M1's completed VALID reproduction verdict**, not merely
  that M1 was admitted first (under plan C it must reproduce; under a predeclared, funded fallback B a valid mismatch
  can instead change control provenance); P1b passed; E1 is built and reviewed.
- **M5, M6:** **the valid-mismatch predicate** (M1's completed VALID mismatch verdict), reviewed fallback-B admissions
  and funding within $60.00, not a new owner approval token; the unchanged source is reviewed; P1b passed; E1 is built
  and reviewed.
- **Common to M1-M6:** P2's actual custodian feasibility / exposure receipt, with a testable primary claim and supported
  inference assumptions; corrected mechanism validation; all eighteen checkpoint checks enumerated; both-arm route
  acceptance; the frozen source, data, starting values, worker, checker and environment; reader AWS acceptance; complete
  all-services reserves; the current single-use technical admission and the current single-use spending admission.

## Totals (program output, v2)

- **Spent upper bound: $7.36** (S1 $1.60 + S2 $3.29 + P1a $0.55 + PRIOR $1.92). Nothing rejected, shared, unconfirmed,
  latched or uncertain. Main training attempts started: none. The search finds no unlisted launch attempt.
- Remaining mandatory caps: **$51.64** (P1b, P2, M1-M4, E1).
- **Plan C at worst case: $59.00. It fits $60.00, with $1.00 to spare. This is NOT final** (`plan_C_is_final: false`):
  it is program output, not an invoice or an accepted envelope. P1b is still priced as a T4 job although Codex placed
  it on the g7 environment; E1's real scope, retention past 12 months, and request and transfer charges are not yet
  reconciled; PRIOR's scope is the owner's decision. The earlier $57.08 is not the final maximum either.
- If each PRIOR job also got the $0.10 allowance: **$59.50** (headroom $0.50).
- **Fallback B adds $23.32 and does not fit.** Admitting M5 now would total $70.66.
- **Sensitivity** (plan C if one DONE row were counted at its full cap): S1 **$69.06** (does not fit: plan C fits only
  because the S1 rule is accepted); S2 $67.37 (does not fit); P1a $61.45 (does not fit); PRIOR $59.00.
- Money-gate preview today: P1b, P2, M1-M4 and E1 each pass; M5 and M6 are refused (over the ceiling).
- **No real `--admit` or `--launch-check` was run.**

## The admission rule (v2)

`--admit <row> --source <commit> --bundle <sha256> --worker <sha256> --checker <sha256>` exits 0 only if **all** hold
(any input error exits 2):

1. The single-writer lock is taken. The row is `PLANNED` (a slot row or an attempt row). No row is `RUNNING`.
2. No `DONE` receipt is rejected; no receipt identity is shared; no cleanup is `UNCONFIRMED`; no limit breach, wrong
   identity or uncertain main start is latched; for a main row, no mandatory row is cancelled.
3. `STUDY_SLOTS.json` and `study_spend.py` equal HEAD, and HEAD equals the freshly fetched upstream tip.
4. **Spent upper bound + this row's cap + every other reserved mandatory cap (E1 included) <= $60.00.**
5. **The owner's stop is not triggered** (Codex Q3/Q6): before every admission while fewer than 3 main training attempts
   have started, the spent upper bound must not be more than $30.00.
   - A main attempt **started** when its hash-verified receipt, bound to its admission (time and seed), shows a
     launched instance: accepted or rejected, finished or failed, first or repeated. No success-only reset.
   - A RunInstances refusal proven to create no instance, and a proven `CLOSED_NO_LAUNCH`, do not count; their costs do.
   - Anything else is an **uncertain start**, which refuses every admission.
   - Smoke and prerequisite jobs (S1, S2, P1a, P1b, P2, E1, PRIOR) never count; their costs do. The normal third main
     attempt is M3, after M1 and M2.
   - Settled rows only move forward, so once the stop is triggered it stays triggered: a retry row or an `INVALID` move
     does not reset it. A report taken while a job is `RUNNING` counts that job at its full cap; nothing can be
     admitted then anyway.
6. Training rows: all admissions of one arm use one source commit, and the two arms never share one.

The gate checks money, stops, latches, one machine at a time, committed state and receipt validity **only**. It does
**not** check technical readiness; each decision prints the row's preconditions, or `NOT ASSESSED`.

## P1b and E1: complete bounds

**Both (limits copied from P1a, which ran under them):** ONE g4dn.2xlarge or g4dn.xlarge, each at its own listed price;
at most 100 GB disk, deleted with the machine; in-machine timer 120 min; power-off at 123 min; destroyed on shutdown;
client deadline at most 130 min; the watcher confirms "terminated" and an empty volume list. The money bound holds
whatever the work does, because the deadline ends the machine: P1b $0.767959/h x 130/60 h + $0.10 = $1.763911, cap
$2.00; E1 the same + $0.10 collection = $1.863911, cap $2.00.

**Timing feasibility: NOT ESTABLISHED for either.** Neither job is built. Each job's work must carry its own wall limit
of at most 3,600 s and a timing preflight. E1 needs the per-checkpoint probe-read time on T4. If a preflight refuses,
the money is still spent and bounded; a re-run needs its own attempt row and its own admission (v2 R1).

- A later job's machine script must write its own instance id into `env.txt` (the reader requires it for every launch
  except the finished P1a job), and its launch record must now also carry `identity.worker_sha256` and
  `identity.checker_sha256` (v2 R4).
- **The next T4 launch goes to a NEW folder.** P1a's `larger_question_t4_job/launch_record.json` and
  `watch_record.json` are its pinned receipt: never moved, renamed, edited or overwritten.

**E1 scope.** E1 runs in every branch of the plan, so its cap is always reserved. It includes retained-evidence
collection, the TEST readout, the 18 checkpoint probe reads and the gates, and a partial-study readout path that
reports `COMPARISON_INCOMPLETE` if the study stops early. E1 is not a main admission, so a cancelled mandatory row
does not block it.

## Open questions and open items

These are also in `STUDY_SLOTS.json` and printed with every decision.

1. **INCLUDED, SCOPE OPEN** (FLAG_FOR_HUMAN_REVIEW): the earlier preparation jobs ($1.9180) are counted as PRIOR ($1.92),
   per Codex; whether they belong inside the $60.00 is the owner's decision. With the $0.10 allowance each, +$0.50.
2. **DECIDED (Codex Q2):** the $60.00 caps study charges (this program's worst-case spend across all attempts and
   required remaining work). The $15.00 bookings are bookkeeping, never refunded or rewritten; they do not raise the
   ceiling; the canonical campaign cap must also pass on its own (outside this program).
3. **DECIDED (Codex Q3/Q6):** the third main attempt is normally M3; the stop counts every main attempt that started.
4. **DECIDED (Codex Q1):** the S1 rule is accepted, conditional on its pinned provider evidence.
5. **OPEN** (FLAG_FOR_HUMAN_REVIEW): retention beyond 12 months; reconcile object sizes, transfer, requests and
   retention before the final freeze; report ongoing charges beyond the bound.
6-9. **DECIDED (Codex Q6-Q9):** see "Latches", "Counting" and "One admission, one attempt".
10. **OPEN, for the runner and the launchers** (the gate refuses until they hold): every launcher must write
    `worker_sha256` and `checker_sha256` where the table above reads them; the prepare scripts must take the admitted
    source instead of HEAD; the runner runs `--launch-check` immediately before RunInstances; a training job is
    prepared after its admission and launched inside the 300-s validity, because its receipt shows only the job id's
    preparation time. Codex R3-A puts preparation before admission; that order needs the training launcher to record
    its RunInstances time first.

## Ledgers (unchanged)

- The canonical meta1 ledger is written only by the typed-pointer training launcher. This program never reads or
  writes it.
- Non-training jobs (P1a, P1b, P2, E1) enter the study only through `study_spend.py`, from their own pinned records.
