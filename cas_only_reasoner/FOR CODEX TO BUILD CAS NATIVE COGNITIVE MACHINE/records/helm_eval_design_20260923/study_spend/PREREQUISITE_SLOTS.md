# HELM-REPAIR-CONTROLLED-1: study slots, caps, receipts and the admission gate (answers Codex `codex-0007`)

Label `CLAUDE_BUILT_CLAUDE_CHECKED`. Every number below is program output from `study_spend.py` on 2026-09-24.
Never edit `STUDY_SPEND_STATE.json` by hand; re-run the program.

## Where things live

| File | What it is |
|---|---|
| `STUDY_SLOTS.json` | **The ONE list of slots.** Input. Each slot: status, cap, the cap's arithmetic basis, the receipt spec. The runner edits it; the program never writes it |
| `study_spend.py` | Reads the list and every receipt **fresh** on every run. Report mode writes `STUDY_SPEND_STATE.json`. `--admit SLOT` is the gate |
| `STUDY_SPEND_STATE.json` | Output only: bounds, totals, and a money-gate preview for every planned slot |
| `test_study_spend.py` | 23 small synthetic tests: `python -B test_study_spend.py` |

## How to use it

```text
python -B study_spend.py               # report; exit 0, or 1 if a DONE receipt is rejected, 2 on any input error
python -B study_spend.py --admit P1b   # the gate; exit 0 ADMIT, 1 REFUSE (reasons printed), 2 any error
```

- `--admit` checks money, the owner's stop, one-machine-at-a-time and receipt validity **only**.
- It does **not** check technical readiness (reviews, builds). Those stay a separate admission. The decision prints
  each slot's open preconditions so nobody reads ADMIT as "ready".
- The decision prints the sha256 of `STUDY_SLOTS.json` and of every receipt it used, so it is tied to exact inputs.

## Slot status (one list, no separate "future" list)

| Status | How it is counted |
|---|---|
| `PLANNED` | Nothing spent. If mandatory, its cap is reserved |
| `RUNNING` | Its **full cap**. While any slot is RUNNING, every admission is refused (one machine at a time) |
| `DONE` | The bound from its receipt, **only if the receipt passes validation**. A rejected receipt counts at the full cap, and every admission is refused until the runner fixes the pins or marks the slot `INVALID` |
| `INVALID` | Its full cap, forever. Needs a written `invalid_reason` |

**What the runner does at each change:**

1. Before a launch: `python -B study_spend.py --admit <slot>` must exit 0. Then set the slot to `RUNNING`.
2. After the watcher (or launcher) finishes: fill the receipt pins (paths, sha256, job / instance / source identity),
   set `DONE`, re-run the report. If the receipt is rejected, fix the pins or set `INVALID` with a reason.

## Receipt validation (defect 3)

A receipt is **rejected** (so the slot counts at its full cap) if any of these fail:

- **Pinned bytes.** The file's sha256 must equal the pin. A replaced or stale file is rejected. A missing file is rejected.
- **Identity.** Job id, source commit, instance id (and, for T4/CPU jobs, launch time and bundle sha256) must equal the
  pins. For watched jobs this is checked in **both** the launch record and the watch record.
- **Numbers.** Every number must be a real finite number: not missing, not text, not true/false, not NaN, not
  infinite. Elapsed seconds must be above 0. A watcher cost must be at least 0 and at most the cap.
- **Cleanup.** Training: cleanup complete and that one instance `CONFIRMED_TERMINATED`. Watched: terminated confirmed
  and an empty list of leftover volumes (an "unknown" answer is rejected).
- **Cost scope.** Machine, price, disk and client deadline must fit the slot's cap basis. The job's own ceiling must
  equal the slot's cap. The watcher's cost must not be below the cost recomputed from its two timestamps. The bound
  uses the larger of the two.

**S1 is a special, narrow case.** AWS refused to create its machine. The launcher could not prove that, so it marked
its own receipt "compute identity uncertain". The program accepts S1 only through the `pointer_capacity_refusal` rule:

- the status is FAILED and no launch record, instance id or pending termination exists;
- the only cleanup failure is `INSTANCE_IDENTITY_UNKNOWN_AFTER_LAUNCH_ATTEMPT`;
- the error is AWS's own `InsufficientInstanceCapacity` answer to `RunInstances`, with zero client retries;
- that refusal is the **last** provider call: the pinned `provider_0025.json`, with no later `provider_NNNN.json`.

The program prints this override every time. **This rule is load-bearing** (see Totals).

## The all-services bound (defect 1)

| Job type | Bound |
|---|---|
| Training (S1, S2, M1-M6) | elapsed (or at most 14,400 s) x $2.52/h rate ceiling + the launcher's declared $1.48 ancillary + $0.10 S3/transfer/retention |
| Watched T4 or CPU (P1a, P1b, P2, E1) | (machine price + $0.005/h public address + disk GB x $0.08 / 730 h) x time + $0.10 S3/transfer/retention + an evidence-collection allowance (E1 only: $0.10) |

- The $0.10 S3/transfer/retention allowance is the coordinator's figure. It covers S3 requests, transfer out of AWS,
  and 12 months of storage of up to about 0.36 GB at $0.023 per GB-month. Measured today: S2 retains 49,097,828 bytes;
  P1a stored a 10,230,760-byte bundle plus about 1 MB. No better measured figure exists.
- The $1.48 is the launcher's **declared** allowance (`typed_pointer_launch.py`). It is not a provider invoice.
- **Every cap must cover its own basis, or the program stops with exit 2.** The old P1a figure ($1.66, below its own
  $1.6639) is now caught by a test. P1a keeps its full $3.00 cap for any case where its receipt is not validated.

## Slots

| Slot | What | Status | Machine | Cap | Basis worst case | Counted now | Timing feasibility |
|---|---|---|---|---|---|---|---|
| S1 | switch-ON smoke attempt 1 (AWS capacity refusal) | DONE | g7.2xlarge, never created | $11.66 | $11.66 | **$1.60** (exact $1.597966: 25.666 s x $2.52/h + $1.48 + $0.10) | n/a |
| S2 | switch-ON smoke attempt 2 (passed) | DONE | g7.2xlarge `i-039b7ae505c4c6245` | $11.66 | $11.66 | **$3.29** (exact $3.281907: 2,431.295 s) | measured |
| P1a | larger-question route checks, both arms | DONE | g4dn.2xlarge `i-09e14d4afd0e0ebfa` | $3.00 | $1.77 (exact $1.763911) | **$0.55** (max(watcher $0.4489, recomputed $0.448829 over 2,104 s) + $0.10 = $0.5489) | measured: 35.1 min |
| P1b | reader acceptance + corrected-probe validation + admission validation, one T4 job | PLANNED | g4dn.2xlarge (g4dn.xlarge allowed) | $2.00 | $1.77 | $0.00 | **not established** (not built) |
| P2 | HSET-2 custodian build | PLANNED | c7i.2xlarge | $1.00 | $0.91 (exact $0.908078) | $0.00 | sister job HSET-1A measured 30.1 min |
| M1 | unchanged reproduction, seed 20260917 of `20208c92` (first) | PLANNED | g7.2xlarge | $11.66 | $11.66 | $0.00 | Helm 2.0 measured 10,471.8 to 10,529.1 s |
| M2-M4 | repaired seeds 20260917, 20260918, 20260919 | PLANNED | g7.2xlarge | $11.66 each | $11.66 | $0.00 | as M1 |
| E1 | evidence collection + TEST readout + 18 checkpoint probe reads + gates + partial-study path | PLANNED | g4dn.2xlarge | $2.00 | $1.87 (exact $1.863911) | $0.00 | **not established** (not built) |
| M5, M6 | fallback B (unchanged seeds 20260918, 20260919), optional | PLANNED | g7.2xlarge | $11.66 each | $11.66 | $0.00 | as M1 |

## Totals (program output)

- **Spent upper bound: $5.44** (S1 $1.60 + S2 $3.29 + P1a $0.55). No DONE receipt is rejected.
- Remaining mandatory caps: **$51.64** (P1b, P2, M1-M4, E1).
- **Plan C at worst case: $57.08. It fits $60.00, with $2.92 to spare.**
- **Fallback B adds $23.32 and does not fit.** Admitting M5 now would total $68.74.
- **Sensitivity** (plan C total if one DONE slot were counted at its full cap instead):
  - S1: **$67.14 — does not fit.** So plan C fits only because the S1 capacity-refusal rule is accepted.
  - S2: $65.45 — does not fit.
  - P1a: $59.53 — still fits.
- Money gate today: P1b, P2, M1-M4 and E1 each pass; M5 and M6 are refused (over the ceiling).
- Real gate run: `--admit P1b` exit 0, "$5.44 + P1b $2.00 + other mandatory caps $49.64 (P2,M1,M2,M3,M4,E1) = $57.08
  vs ceiling $60.00"; owner stop not triggered. `--admit M5` exit 1; `--admit S2` exit 1; `--admit Z9` exit 2.
- Compared with the previous version ($57.59): the training cap rose $0.10 per job (the retention allowance), P1a now
  counts its validated $0.55 instead of $1.66, and S1/S2 each rose $0.10.

## The admission rule (defect 2)

`--admit <slot>` exits 0 only if **all** hold:

1. The slot exists and is `PLANNED`. No slot is `RUNNING`. No `DONE` receipt is rejected.
2. **Spent upper bound + the slot's cap + the caps of every other PLANNED mandatory slot (E1 included) <= $60.00.**
3. **The owner's stop is not triggered.** The stop triggers when the spent upper bound is **more than** $30.00 while
   fewer than 3 main-comparison training jobs (M1-M6) are RUNNING or DONE. Then every admission is refused and the
   runner reports to the owner.
   - The smoke runs S1 and S2 do not count toward the 3; the owner's words were "before the third seed". An INVALID
     slot does not count either. Both choices keep the stop active as long as possible.
   - The stop uses the upper bound, not a provider invoice. It can trigger while real spend is lower. That is the safe side.

Any error or missing input exits 2. A missing receipt of a DONE slot is a rejected receipt, so the gate refuses (exit 1).

## P1b and E1: complete bounds (defect 4)

**Both (limits copied from P1a, which ran under them):**

- **Machine:** ONE g4dn.2xlarge at most (g4dn.xlarge is cheaper and allowed).
- **Disk:** at most 100 GB, deleted with the machine.
- **Time:** in-machine timer 120 min; the operating system powers off at 123 min; the machine is destroyed on
  shutdown; the client deadline is at most 130 min, when the watcher terminates it and waits for "terminated".
- **Cleanup evidence:** the watcher confirms "terminated" and an empty volume list. It must be bound to the same
  instance id and launch time as the launch record, or the receipt is rejected.
- **Money:** the bound holds **whatever the work does**, because the deadline ends the machine.
  - P1b: $0.767959/h x 130/60 h + $0.10 = $1.763911, cap $2.00.
  - E1: the same + $0.10 evidence collection = $1.863911, cap $2.00.

**Timing feasibility: NOT ESTABLISHED for either.** Neither job is built.

- The basis we have is P1a on the same T4 class: boot, setup and finish took about 7 min (35.1 min in total, of
  which the checks were 1,690.1 s). That leaves about 113 min of the 120-min timer.
- Each job's work must carry its own wall limit of at most 3,600 s. It must also run a timing preflight that refuses
  before any work if its projection is over.
- E1 needs the per-checkpoint probe-read time on T4. P1b's corrected-probe validation is to measure it. E1's
  admission then needs 18 x that time + readout + gates within 3,600 s.
- If a preflight refuses, the money is still spent and bounded. A re-run needs its own slot, which must pass the gate.

**E1 scope, stated plainly.** E1 runs in every branch of the plan, so its cap is always reserved. It **includes**:

1. **Retained-evidence collection.** It collects the checkpoint and measurement objects that each training receipt
   lists, from the retained buckets or the local receipts, into E1's bundle.
2. **The readout.** The TEST readout, the 18 checkpoint probe reads, and the gates.
3. **A partial-study readout path.** If the study stops early (the $30 stop, a failed seed, or fallback B
   unfundable), E1 reads whatever checkpoints exist and reports `COMPARISON_INCOMPLETE`. It uses the same machine and
   deadline, so it stays under the same cap.

- **Cap basis:** $1.763911 machine, address and disk at the 130-min deadline + $0.10 S3/transfer + $0.10 collection
  transfer = $1.863911, rounded up to a **$2.00** cap.

## Ledgers (unchanged)

- The canonical meta1 ledger is written only by the typed-pointer training launcher. Its fixed $15 bookings are
  bookkeeping, not spend. This program never reads or writes it.
- Non-training jobs (P1a, P1b, P2, E1) enter the study only through `study_spend.py`, from their own pinned records.

## Codex `codex-0007` defects and where each is fixed

| # | Defect | Fix |
|---|---|---|
| 1 | P1a hardcoded 1.66 < 1.6639; no all-services bound | Caps are checked against their own basis (exit 2 if below); P1a cap $3.00; every bound adds the $0.10 S3/transfer allowance; P1a now counts its validated $0.55 |
| 2 | static calculator, no admission gate | One slot list with statuses; `--admit SLOT` with the $60 rule, the $30 stop, one machine at a time, and receipt validity; exit 0/1/2 |
| 3 | missing elapsed became 0; any cost accepted; no identity binding | Receipt validation above: pinned sha256, identity in every file, finite non-negative numbers, cleanup, cost scope; rejected = full cap |
| 4 | P1b/E1 bounds and E1 scope | Section above; timing feasibility honestly NOT ESTABLISHED |
| 5 | route reader bindings and exit | `../larger_question_t4_job/read_results.py`: machine `identity.json` = launch identity, bundle and wheel hashes from `env.txt`, the machine's own "bundle.tar.gz: OK", cleanup bound to the same instance and launch time; strict exit (0 only for ROUTE_ACCEPTED); 20 tests |
