# HELM-REPAIR-CONTROLLED-1: study slots, caps, receipts and the admission gate

Label `CLAUDE_BUILT_CLAUDE_CHECKED`. Answers Codex `codex-0007` and the builder review of `bb942461` (see `REVIEW.md`).
Every number below is program output from `study_spend.py` on 2026-09-24. Never edit `STUDY_SPEND_STATE.json` by
hand; re-run the program.

## Where things live

| File | What it is |
|---|---|
| `STUDY_SLOTS.json` | **The ONE list of slots.** Each slot: status, cap, the cap's arithmetic basis, the receipt spec, and (once admitted) its admission record |
| `study_spend.py` | Reads the list and every receipt **fresh** on every run. Report mode writes `STUDY_SPEND_STATE.json`. `--admit SLOT` is the gate, and on ADMIT it writes the slot as `RUNNING` |
| `STUDY_SPEND_STATE.json` | Output only: bounds, totals, and a money-gate **preview** for every planned slot (a preview is not an admission) |
| `test_study_spend.py` | 57 small synthetic tests: `python -B test_study_spend.py` |
| `REVIEW.md` | The review findings on `bb942461` and what was done about each |

## What is frozen, and what can change

**Frozen in the code** (never read from the file; if the file disagrees, exit 2):

- the **$60.00** ceiling; the owner's **$30.00** stop before the **3rd** training job; the **$0.10** S3/transfer/retention
  allowance per job;
- the **slot definitions**: the slot set, every cap, cap basis, mandatory flag, stop flag, seed, arm, precondition and
  note, and the **whole rows** of S1, S2 and P1a (done before the gate existed). Their digest must equal
  `FROZEN_DEFINITIONS_SHA256` (`82e809500f14ad8988b3b45ad6a7265f0601a5791f13cb8ea5a4608771456764`). Changing any
  of them needs a reviewed code change.

**Can change** (only for slots other than S1, S2, P1a): `status`, `receipt`, `invalid_reason`, `admission`.
Moves go forward only. The program checks this against **every committed version** of `STUDY_SLOTS.json`; a
violation is exit 2:

| Once committed as | It may later be |
|---|---|
| `RUNNING` | `RUNNING`, `DONE` or `INVALID`, always with the same admission record |
| `DONE` | `DONE` or `INVALID`, always with the same receipt and admission record |
| `INVALID` | exactly the same, forever |

No committed `RUNNING`, `DONE` or `INVALID` row may disappear.

## How the runner uses it

```text
python -B study_spend.py                                              # report; exit 0, or 1 (rejected / shared receipt,
                                                                      # unconfirmed cleanup), 2 on any input error
python -B study_spend.py --admit P1b --source <40-hex> --bundle <64-hex>   # watched slot
python -B study_spend.py --admit M1  --source <40-hex>                     # training slot
```

1. Commit and push `STUDY_SLOTS.json` and `study_spend.py`. The gate refuses while either differs from HEAD.
2. `--admit <slot> --source <commit> [--bundle <sha256>]`. Exit 0 means ADMIT, and the program has already written
   the slot as `RUNNING` with an admission record (time, source, bundle or seed and arm, the slots-file sha256 before,
   the program sha256, the arithmetic). Commit and push that, then launch. **Order matters (round 3):** admit
   first, then prepare the job, then launch, all inside the slot's lifetime (training 14,400 s; watched: its client
   deadline, 130 min for P1b and E1). A training job's id carries the UTC time the job was **prepared**
   (`prepare_study.py` / `prepare_smoke.py` stamp it); a job prepared before its admission, or launched after
   admission time + the lifetime, is not this admission's launch. It is rejected at `DONE`, and after `INVALID` its
   cleanup is `UNCONFIRMED`, which stops the study. Do not edit the admission record by hand.
3. When the job ends, fill the receipt pins (paths, sha256, job / instance / source identity), set `DONE`, and run
   the report. **Check the report before committing:** after the commit, the pins of a DONE row are frozen. If the
   receipt is rejected, fix the pins before committing, or set `INVALID` with a reason. If the report says a slot's
   cleanup is `UNCONFIRMED`, stop and report to the owner: `INVALID` does **not** clear it (round 2).
4. Commit and push. Only then can the next `--admit` pass.

- `--admit` checks money, the owner's stop, one machine at a time, committed state and receipt validity **only**.
  It does **not** check technical readiness (reviews, builds). Each decision prints the slot's preconditions, or
  `NOT ASSESSED` if the slot has none listed, so nobody reads ADMIT as "ready".

## Counting

| Status | How it is counted |
|---|---|
| `PLANNED` | Nothing spent. If mandatory, its cap is reserved |
| `RUNNING` | Its **full cap** (more, if a receipt it already names shows more). While any slot is RUNNING, every admission is refused (one machine at a time) |
| `DONE`, receipt accepted | The bound computed from its receipt |
| `DONE`, receipt rejected | **The larger of** the cap and every cost figure the receipt itself shows. Every admission is refused until the slot is marked `INVALID` |
| `INVALID` | **The larger of** the cap and every cost figure its receipt shows (if it has one), forever. Needs a written `invalid_reason` |

"Every cost figure the receipt shows" means: the recorded cost plus the allowances; the cost recomputed from its
timestamps; and the cost at its own deadline or instance-seconds limit. Each is priced at the highest price the
receipt or the basis shows. So a job that broke its own cost basis is **never counted below what it recorded**.

The receipt is read for these figures **first**, from whatever commit and path its spec gives, before any check of
the spec or the pins (round 2). An empty spec field or a stale pin can get a receipt rejected. It can never shrink
the count.

## Receipt validation

A receipt is **rejected** if any of these fail:

- **Pinned bytes.** The file's sha256 must equal the pin. A replaced, stale or missing file is rejected. A watched
  job's paths must stay inside the design folder (no drive letter, backslash, `..` or absolute path).
- **Identity.** Job id, source commit, instance id (and, for T4/CPU jobs, launch time and bundle sha256) must equal the
  pins. For watched jobs this is checked in **both** the launch record and the watch record.
- **One receipt, one slot.** No receipt sha256 or path, job id, instance id, launch or watch record sha256 or path,
  or provider record may be claimed by two `RUNNING`, `DONE` or `INVALID` slots. If one is, **both** receipts are
  rejected and every admission is refused.
- **Its own admission** (every slot admitted by the gate). The receipt's source commit must equal the admitted
  source; a watched job's bundle must equal the admitted bundle; a training job's model seed
  (`authority.worker_config.design.model_seed`) must equal the slot's seed; the launch time (the time in the job id,
  or the launch record's `launched_utc`) must be **at or after** the admission time and **before** admission time +
  the slot's lifetime (round 3). A committed version of `STUDY_SLOTS.json` must show the slot `RUNNING` with the
  **identical** admission record (round 2). So a record typed by hand, never committed as RUNNING, is refused.
- **An admission record `--admit` wrote** (round 3, NOTE-F). The record must carry `gate` (`study_spend.py --admit`),
  `program_sha256` and `slots_sha256_before`. `program_sha256` must be the sha256 of some committed `study_spend.py`.
  `slots_sha256_before` must be the sha256 of the committed `STUDY_SLOTS.json` version just before the first
  committed version that shows the slot `RUNNING` with this record. A careless hand edit fails; a careful one that
  copies these values and is committed can still pass (the gate cannot tell who wrote a committed line).
- **Numbers.** Every number must be a real finite number. Elapsed seconds must be above 0 and within the basis. A
  watcher cost must be at least 0 and at most the cap.
- **Cleanup.** Training: cleanup complete and that one instance `CONFIRMED_TERMINATED`. Watched: terminated confirmed
  and an empty list of leftover volumes.
- **Cleanup fails closed** (round 2). A cleanup counts as **confirmed** only when records whose sha256 matches the
  pin show **this slot's own machine** gone:
  - training: cleanup complete, identity certain, the one launched instance `CONFIRMED_TERMINATED`, nothing pending,
    no failure, compute cleanup `COMPLETE`;
  - watched: terminated confirmed, final state terminated or gone, no volume left, and the same instance and launch
    time in both records;
  - any id the spec does give must agree; a receipt identity that another slot also claims never confirms.

  The one other way out is a **proven** capacity refusal under the S1 rule (receipt hash matches, every refusal check
  passes). A `DONE` or `INVALID` slot, or a `RUNNING` slot past its lifetime (admission time + its basis's instance
  seconds or client deadline), that has neither is **cleanup UNCONFIRMED**. A missing, unreadable, stale, incomplete or
  silent receipt is never a confirmation. Every admission is then refused, even after `INVALID`: stop and report to
  the owner. Nothing in the program clears it.
- **The receipt must be this slot's own launch** (round 3, MAJOR-E). For every slot except S1, S2 and P1a, a
  confirmed cleanup or a proven refusal counts only when the verified receipt is **this slot's admitted launch**,
  whatever the slot's status (`DONE`, `INVALID`, or `RUNNING` past its lifetime):
  1. the admission record is one `--admit` wrote and a committed version showed the slot `RUNNING` with it (the
     two bullets above, now applied to `INVALID` rows too);
  2. the launch time the verified receipt **itself** shows (the time in its own job id; `launched_utc` in both
     watched records) is at or after the admission time and before admission time + the slot's lifetime;
  3. training slots: the receipt's own model seed is the slot's seed, and its own source is the admitted source
     (the arm is bound through the source).

  Otherwise the cleanup is `UNCONFIRMED` ("the verified receipt is not this slot's admitted launch"). So naming
  another job's clean receipt on an `INVALID` row no longer reopens the gate. A wrong source is now a stop, not only a
  rejection (open question 8).
- **Cost scope.** The machine must be one the basis lists, **at that machine's own listed price**. Disk and client
  deadline must fit the basis. The job's own ceiling must equal the slot's cap. The watcher's cost must not be below
  the cost recomputed from its two timestamps; the bound uses the larger of the two.

**S1 is a special, narrow case.** AWS refused to create its machine. The launcher could not prove that, so it marked
its own receipt "compute identity uncertain". The program accepts S1 only through the `pointer_capacity_refusal` rule
(status FAILED; no launch, instance or pending termination; the only cleanup failure is
`INSTANCE_IDENTITY_UNKNOWN_AFTER_LAUNCH_ATTEMPT`; AWS's own `InsufficientInstanceCapacity` answer to `RunInstances`
with zero client retries; that refusal is the **last** provider call). The override is printed every time. **This
rule is `CLAUDE_PROPOSED` and load-bearing:** Codex or the owner must accept or reject it (open question 4).

## The all-services bound

| Job type | Bound |
|---|---|
| Training (S1, S2, M1-M6) | elapsed (at most 14,400 s) x $2.52/h rate ceiling + the launcher's declared $1.48 ancillary + $0.10 S3/transfer/retention |
| Watched T4 or CPU (P1a, P1b, P2, E1) | (machine price + $0.005/h public address + disk GB x $0.08 / 730 h) x time + $0.10 S3/transfer/retention + an evidence-collection allowance (E1 only: $0.10) |

- The $0.10 allowance is the coordinator's figure. It covers S3 requests, transfer out of AWS, and **12 months** of
  storage of up to about 0.36 GB at $0.023 per GB-month. The evidence buckets have no end date
  (`DELETION_DENIED`), so storage after 12 months is **outside** this bound (open question 5).
- The $1.48 is the launcher's **declared** allowance (`typed_pointer_launch.py`). It is not a provider invoice.
- **Every cap must cover its own basis, or the program stops with exit 2.** The old P1a figure ($1.66, below its own
  $1.6639) is caught by a test.
- Watched bases list their allowed machines, each with its own price. The cap check uses the dearest one. Prices:
  g4dn.2xlarge $0.752/h and g4dn.xlarge $0.526/h (`larger_question_t4_job/launch.py` PRICES); c7i.2xlarge $0.357/h.
  P2 lists only c7i.2xlarge ("or cheaper" is gone: no cheaper price is on record).

## Slots

| Slot | What | Status | Machine | Cap | Basis worst case | Counted now | Timing feasibility |
|---|---|---|---|---|---|---|---|
| S1 | switch-ON smoke attempt 1 (AWS capacity refusal) | DONE | g7.2xlarge, never created | $11.66 | $11.66 | **$1.60** (exact $1.597966) | n/a |
| S2 | switch-ON smoke attempt 2 (passed) | DONE | g7.2xlarge `i-039b7ae505c4c6245` | $11.66 | $11.66 | **$3.29** (exact $3.281907) | measured |
| P1a | larger-question route checks, both arms | DONE | g4dn.2xlarge `i-09e14d4afd0e0ebfa` | $3.00 | $1.77 (exact $1.763911) | **$0.55** (exact $0.5489) | measured: 35.1 min |
| P1b | reader acceptance + corrected-probe validation + admission validation, one T4 job | PLANNED | g4dn.2xlarge or g4dn.xlarge | $2.00 | $1.77 | $0.00 | **not established** (not built) |
| P2 | HSET-2 custodian build | PLANNED | c7i.2xlarge | $1.00 | $0.91 (exact $0.908078) | $0.00 | sister job HSET-1A measured 30.1 min |
| M1 | unchanged reproduction, seed 20260917 (arm UNCHANGED) | PLANNED | g7.2xlarge | $11.66 | $11.66 | $0.00 | Helm 2.0 measured 10,471.8 to 10,529.1 s |
| M2-M4 | repaired seeds 20260917, 20260918, 20260919 (arm REPAIRED) | PLANNED | g7.2xlarge | $11.66 each | $11.66 | $0.00 | as M1 |
| E1 | evidence collection + TEST readout + 18 checkpoint probe reads + gates + partial-study path | PLANNED | g4dn.2xlarge or g4dn.xlarge | $2.00 | $1.87 (exact $1.863911) | $0.00 | **not established** (not built) |
| M5, M6 | fallback B: unchanged seeds 20260918, 20260919 (arm UNCHANGED), optional | PLANNED | g7.2xlarge | $11.66 each | $11.66 | $0.00 | as M1 |

Every M slot now lists its preconditions (outside the money gate; from the plan text and the review; Codex or the
owner to confirm): the reviewed source for its arm, M1 admitted first (M2-M4), P1b passed, E1 built and reviewed.

## Totals (program output)

- **Spent upper bound: $5.44** (S1 $1.60 + S2 $3.29 + P1a $0.55). No DONE receipt is rejected. No receipt identity is
  shared. No cleanup is unconfirmed. Training jobs started: none.
- Remaining mandatory caps: **$51.64** (P1b, P2, M1-M4, E1).
- **Plan C at worst case: $57.08. It fits $60.00, with $2.92 to spare.**
- **Fallback B adds $23.32 and does not fit.** Admitting M5 now would total $68.74.
- **Sensitivity** (plan C total if one DONE slot were counted at its full cap instead):
  - S1: **$67.14 — does not fit.** Plan C fits only because the S1 capacity-refusal rule is accepted.
  - S2: $65.45 — does not fit.
  - P1a: $59.53 — still fits.
- Money-gate preview today: P1b, P2, M1-M4 and E1 each pass; M5 and M6 are refused (over the ceiling).
- **No real `--admit` was run**: it now writes the slot as RUNNING, which would announce a launch.

## The admission rule

`--admit <slot> --source <commit> [--bundle <sha256>]` exits 0 only if **all** hold (any input error exits 2):

1. The slot is `PLANNED`. No slot is `RUNNING`. No `DONE` receipt is rejected. No receipt identity is shared. No
   slot's cleanup is `UNCONFIRMED` (see "Cleanup fails closed").
2. `STUDY_SLOTS.json` and `study_spend.py` equal HEAD.
3. **Spent upper bound + the slot's cap + the caps of every other PLANNED mandatory slot (E1 included) <= $60.00.**
4. **The owner's stop is not triggered.** It triggers when the spent upper bound is **more than** $30.00 while fewer
   than 3 main-comparison training jobs (M1-M6) have **started**. Then every admission is refused and the runner
   reports to the owner.
   - **Started** means `RUNNING`, or `DONE` with an **accepted** `pointer_finished` receipt. An AWS capacity refusal,
     a rejected receipt and an `INVALID` slot never count: a machine that never ran cannot switch the stop off.
   - A training job that **launched and then failed** (a machine ran, the receipt is accepted) counts as started under
     this rule. Whether it should is **open** (question 6); the behaviour is unchanged.
   - The smoke runs S1 and S2 do not count toward the 3.
   - The stop uses the upper bound, not a provider invoice. It can trigger while real spend is lower. That is the
     safe side.
5. Training slots: all admissions of one arm (UNCHANGED or REPAIRED) use one source commit, and the two arms never
   share one. The receipt has no explicit "arm" field, so the arm is bound through the source commit.

## P1b and E1: complete bounds

**Both (limits copied from P1a, which ran under them):**

- **Machine:** ONE g4dn.2xlarge or g4dn.xlarge, each checked at its own listed price.
- **Disk:** at most 100 GB, deleted with the machine.
- **Time:** in-machine timer 120 min; the operating system powers off at 123 min; the machine is destroyed on
  shutdown; the client deadline is at most 130 min, when the watcher terminates it and waits for "terminated".
- **Cleanup evidence:** the watcher confirms "terminated" and an empty volume list, bound to the same instance id and
  launch time as the launch record, or the receipt is rejected.
- **Money:** the bound holds **whatever the work does**, because the deadline ends the machine.
  - P1b: $0.767959/h x 130/60 h + $0.10 = $1.763911, cap $2.00.
  - E1: the same + $0.10 evidence collection = $1.863911, cap $2.00.

**Timing feasibility: NOT ESTABLISHED for either.** Neither job is built.

- The basis we have is P1a on the same T4 class: boot, setup and finish took about 7 min (35.1 min in total, of
  which the checks were 1,690.1 s). That leaves about 113 min of the 120-min timer.
- Each job's work must carry its own wall limit of at most 3,600 s, and a timing preflight that refuses before any
  work if its projection is over.
- E1 needs the per-checkpoint probe-read time on T4. P1b's corrected-probe validation is to measure it. E1's
  admission then needs 18 x that time + readout + gates within 3,600 s.
- If a preflight refuses, the money is still spent and bounded. A re-run needs its own slot (a reviewed code change).
- A later job's machine script must write its own instance id (`instance_id=` from IMDSv2) into `env.txt`. The T4
  reader requires it for every launch except the finished P1a job: its template `dc05f4af` **and** its instance
  `i-09e14d4afd0e0ebfa`, both together (round 2). The current `larger_question_t4_job/job.sh.template` still has
  sha256 `dc05f4af` and does **not** write the line. So the next T4 job needs a template change, with its own review,
  or the reader refuses its route.
- **The next T4 launch goes to a NEW folder** (round 3, NOTE-G). `larger_question_t4_job/launch_record.json` and
  `watch_record.json` are P1a's pinned receipt: they are never moved, renamed, edited or overwritten. Moving them
  aside to relaunch there would reject P1a, mark its cleanup `UNCONFIRMED` and stop every admission; P1a's row is
  frozen whole, so it cannot be marked `INVALID`. Copy the job code into a new folder for P1b or E1.

**E1 scope, stated plainly.** E1 runs in every branch of the plan, so its cap is always reserved. It **includes**:

1. **Retained-evidence collection.** It collects the checkpoint and measurement objects that each training receipt
   lists, from the retained buckets or the local receipts, into E1's bundle.
2. **The readout.** The TEST readout, the 18 checkpoint probe reads, and the gates.
3. **A partial-study readout path.** If the study stops early (the $30 stop, a failed seed, or fallback B
   unfundable), E1 reads whatever checkpoints exist and reports `COMPARISON_INCOMPLETE`. It uses the same machine and
   deadline, so it stays under the same cap.

- **Cap basis:** $1.763911 machine, address and disk at the 130-min deadline + $0.10 S3/transfer + $0.10 collection
  transfer = $1.863911, rounded up to a **$2.00** cap.

## Open questions (FLAG_FOR_HUMAN_REVIEW; for Codex or the owner, not decided here)

These are also in `STUDY_SLOTS.json` and printed with every decision.

1. **Other AWS jobs in this design folder are not slots.** analogy_repair_t4_job attempt 1 $0.5596 and attempt 2
   $0.67; aws_probe_job $0.4834; hset1a_aws_job attempt 1 $0.0223 and attempt 2 $0.1827. Total $1.9180, plus $0.50
   if each got the $0.10 allowance (watcher figures, not program-validated). Are they inside the $60.00? If yes,
   plan C's $2.92 headroom falls to about $0.50.
2. **Spend or bookings?** This program counts worst-case **spend**. The training launcher books a fixed **$15.00**
   per job; Codex (`codex-0007`) put plan C at $90 and plan B at $120 in bookings, including the existing $30. Under
   bookings, plan C is over the ceiling.
3. **Which job is "the third seed"?** Counted as training jobs M1-M6 with M1 included (M1 and M2 share seed
   20260917), the stop is checked last at M3's admission. The owner may have meant M4.
4. **The S1 capacity-refusal rule** (above) needs acceptance. S1's provider log shows no cleanup calls after
   `provider_0025`, so "last provider call" means last **logged** call.
5. **Retention after 12 months** is outside the $0.10 allowance.
6. **Does a training job that launched and then failed count as "started"** for the owner's $30.00 stop? Today it
   does (a machine ran and its receipt is accepted). The round-2 verification's probe P7: M1-M3 each fail after 60 s,
   all three count as started, spent $10.33, and the stop is then off for the rest of the study. Not decided here.
   (Listed here and in `REVIEW.md`. It is not yet in `STUDY_SLOTS.json`: that file's open-question list is covered by
   the frozen definitions digest, so adding it needs a re-freeze in a reviewed change. The same holds for 7 and 8.)
7. **Cancelling a slot that was never admitted and never launched.** Today, marking it `INVALID` stops the study
   (fail closed: no receipt, no admission, cleanup `UNCONFIRMED`); leaving it `PLANNED` keeps its cap reserved. Not
   decided here.
8. **Should a wrong source stop the study?** Round 3 binds a training receipt's own source to the admitted source
   before its cleanup counts (the ordered fix: "arm/source where the receipt shows them"). The round-3 verifier had
   suggested a wrong source stay a rejection reason only, because the machine may still be this slot's. With the
   binding, a slot launched from the wrong commit ends `UNCONFIRMED` for good (stop and report), even when its
   machine is shown gone. Codex or the owner may keep this or relax it.

## Ledgers (unchanged)

- The canonical meta1 ledger is written only by the typed-pointer training launcher. This program never reads or
  writes it.
- Non-training jobs (P1a, P1b, P2, E1) enter the study only through `study_spend.py`, from their own pinned records.
