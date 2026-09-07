# Condition-skill v9 — Preregistration Freeze Document (v9_001)

Lane C. Read-only research; this file is the only artifact this lane writes. No
neural work, no AWS/provider call, no reservation, no commit, no push.

- Record UTC: 2026-09-07 (freeze document assembled by Lane C)
- Schema intent: freeze record for the offline candidate-learning pilot
  `condition_skill_v9` (records directory `records/condition_skill_v9_001/`).

This document freezes what the single paid run is allowed to test, what it is
allowed to claim, and the gates that must hold before and after it. It records
real values taken verbatim from the frozen protocol, owner records, audit, and
source code listed below.

---

## 1. Experiment identity and claim scope

- **Experiment identity:** `condition_skill_v9` — offline candidate learning of
  the two-condition skill only. It is a candidate-only learning experiment, not
  a replacement for the accepted native model, not a repair of the saved
  `R_CR` failure, and not completion of the CNCM goal.
- **The skill:** given two labelled conditions, return which conditions hold.
  Each condition carries its original integer value, limit, semantic slot
  (1 or 2), and requested comparison (`at_least` / `>=` or `at_most` / `<=`).
  The two correct bits come from independent integer comparisons. Bit 1 is the
  most significant bit. Four classes: `00`→L0, `01`→L1, `10`→L2, `11`→L3.
- **What `PASS` licenses (and only this):** offline candidate learning of the
  declared input-dependent condition skill on the held-out cases, under the
  registered controls, with both binary decisions above binary chance and with
  improvement through training, for each family separately. Both families
  passing establishes that both met the registered criteria — it does not
  establish a CAS advantage.
- **What `PASS` never licenses:** native admission or installation into the
  accepted runtime database; repair; complete caller return; persistent Bias
  updates; composition (the `0/72` held-out result is unchanged); CAS advantage
  (or superiority) over the matched control; any claim of a complete cognitive
  machine.

Claim-status discipline: the verdict comes from the frozen gate program
(`train.adjudicate`), never from prose. A hard gate that fails is a FAILURE,
never "PASS with caveats". Missing evidence is `EVIDENCE_INCOMPLETE`, never
`PASS`.

---

## 2. Frozen data

- **Dataset manifest SHA-256 (frozen):**
  `6b19020c4653aa535919f4af092020ad3650855bf7f58c6b550169af3d5468dd`
- **Splits (tasks):**

  | Split | Tasks |
  | --- | ---: |
  | Training | 1,536 |
  | Validation | 384 |
  | Fresh instances (test) | 384 |
  | Withheld direction pair (test) | 384 |

  Splits line: `1536 / 384 / 384 / 384`. Total 2,688 tasks, 2,320 atomic
  families. Every class is balanced within each admitted direction pair; a
  constant class predictor scores exactly 25% on each base split. Equality
  passes both comparison directions; equality and one-unit margins receive
  separate reported counts.
- **Sealed target boundary (frozen statement):** the learner stage reads only
  `train.json` and `validation.json` before the sealed boundary. It never reads
  or hashes private test target files there: `bundle.inspect_structure`
  validates the manifest declaration and builder-source pins without touching
  any partition, and `read_partitions` reads only the partitions it is
  explicitly given. Hash-reading private files is byte integrity only and is
  never the boundary that proves targets stayed unopened. Blind test
  predictions are saved with a hash-bound selection receipt first; only then
  does the evaluation stage open the public test files, save blind predictions,
  and finally open the private target files for scoring. Each partition is
  hash-checked against the frozen manifest immediately before it is parsed.
- **The 256-record ruling (not appended):** the historical 256 practice records
  may be included in an affected protocol only as deduplicated training/practice
  data, with sealed, disjoint validation and test data. This pilot builds a new,
  separate synthetic curriculum and does **not** append those historical
  records automatically. `OWNER_256_RECORD_RULING.md` remains the authority;
  it is referenced here, not incorporated into this pilot's dataset.

---

## 3. Frozen evaluation

Deterministic adjudication (`train.adjudicate`). Trainer-side verdict is
`EVIDENCE_INCOMPLETE` by design until the independent outer provider receipt
supplies its attestation and re-adjudicates.

### Metrics, baselines, denominators

- **Joint accuracy** denominator: all attempted rows, including `NO_EFFECT`
  rows. Baseline: `0.25` (balanced four-class constant predictor).
- **Per-bit accuracy** denominator: all attempted rows; `NO_EFFECT` is wrong
  for both bits. Baseline: `0.50` (chance for one ordinary binary decision).
  Per-bit gates are never compared against `0.25`.

### `PASS` gates (conjunction)

- experiment status `COMPLETED_OFFLINE_CANDIDATE_EXPERIMENT`, selection sealed,
  test targets parsed;
- unchanged source identity with baseline, installed-wheel, and candidate pins;
- constant baseline exactly `0.25` on validation and both test splits;
- integer rule (oracle) exactly `1.0` on validation and both test splits;
- trained CAS and trained generic joint accuracy strictly above `0.25` on both
  test splits, and **both per-bit accuracies strictly above `0.50`**;
- trained joint accuracy strictly above untrained joint accuracy on both test
  splits, for each family (improvement through training, kept separate from
  exceeding the constant baseline);
- every evaluation control (row reversal, slot reassignment, both direction
  reversals, both threshold crossings) with joint accuracy exactly `1.0` for
  each trained family on each test split — both original and transformed
  answers correct, never invariance alone;
- exactly `2,400` steps per family;
- a matching independent provider attestation (keys below).

The overall verdict is a conjunction over all gates. Per-family gate rows,
initial-versus-trained observations, and every failed or missing gate are
reported separately and are never erased by the combined verdict.

### Provider attestation keys (frozen, from `train.py` `PROVIDER_ATTESTATION_KEYS`)

| Key | Frozen value |
| --- | --- |
| `account` | `807562639912` |
| `region` | `us-west-2` |
| `ami` | `ami-0fbbd0facbc9e3cff` |
| `instance_type` | `g7.2xlarge` |
| `gpu_name_contains` | `RTX PRO 4500` |
| `t4_rejected` | `true` |
| `visible_gpu_count` | `1` |
| `torch_version` | `2.11.0+cu128` |
| `cuda_version` | `12.8` |
| `actual_cuda_operation` | `true` |
| `automatic_retries` | `0` |
| `reservation_usd` | `4.00` |

plus a well-formed job label matching `cas-meta2-\d{14}-[a-f0-9]{8}`.

### F5 open question (explicit open gate)

`instance_count` is **not** in the frozen attestation key set. The protocol and
owner approval both state "one `g7.2xlarge`", and the launcher preflight
enforces `instance_count == 1`, but `adjudicate` compares only the fixed key
set above, so re-adjudication would accept an attestation that does not itself
carry `instance_count`. Any change to `PROVIDER_ATTESTATION_KEYS` (for example,
adding `"instance_count": 1`) requires a new owner-approved pre-run amendment
before the run.

**This is an open gate, not a resolved item.** Until the owner rules, the run
may either (a) proceed with the adjudicator exactly as frozen (key set
unchanged — `instance_count` then is enforced by launcher preflight but not by
re-adjudication), or (b) wait. Resolving it by amending the key set is itself
an owner-approved pre-run amendment. The three options are carried into the
sign-off section at the bottom.

---

## 4. Frozen resource plan

| Field | Frozen value |
| --- | --- |
| Account | `807562639912` |
| Region | `us-west-2` |
| AMI | `ami-0fbbd0facbc9e3cff` |
| Instance | one `g7.2xlarge` (`instance_count: 1`) |
| GPU name contains | `RTX PRO 4500` |
| T4 | rejected (`t4_rejected: true`, no T4) |
| Visible GPU count | `1` |
| torch | `2.11.0+cu128` |
| CUDA | `12.8` |
| Worker bound | `600` s (`worker_seconds_max`) |
| Trainer output bound | `32` MiB (`trainer_output_bytes_max: 33554432`) |
| Instance limit | `3600` s (`instance_seconds_max`) |
| Guest shutdown | `3400` s (`guest_shutdown_seconds`) |
| Scheduled termination | `3480` s (`cloud_schedule_seconds`) |
| Automatic retries | `0` (zero) |
| Reservation | `$4.00` (`reservation_usd`) |
| Seed | `7` |
| Training | `true` |
| Native execution | `false` |

These match the executable owner phase-approval record
(`OWNER_PHASE_APPROVAL.json` `frozen_resource_plan`) and the frozen
`aws/condition_skill_v9_resource_plan.py` `RESOURCE_PLAN`.

---

## 5. Execution gates (in order)

1. **Hash-bound request + separate standing authority.** The exact request and
   authority pair is hash-bound. The request names the job, exact source and
   archive identities, and frozen run scope, and keeps `launch_authorized`
   false and `new_reservation` false. A separate standing authority carries the
   actual authorization.
2. **Owner-approval record hash verified against `OWNER_PHASE_APPROVAL.json`.**
   The standing authority's binding to the owner record is verified against the
   real `OWNER_PHASE_APPROVAL.json` bytes, not self-asserted.
3. **Read-only preflight.** Account, region, AMI, instance type, and frozen
   resource identity are checked before any reservation.
4. **Single reservation via the canonical budget helper.** Ledger append first,
   AWS-side record after, exactly once, no refund, no automatic retry, and a
   second attempt for the same job is refused (job-in-ledger refusal). The
   reservation must name both task scope (`condition_skill_v9`) and campaign
   scope (`$400` campaign ledger).
5. **One registered instance with `ClientToken=job`.** Exactly one registered
   instance for the job.
6. **Provider identity attested outside the trainer.** IMDSv2, GPU name, torch,
   CUDA, one instance, actual CUDA operation — attested outside the trainer
   execution guard.
7. **Cleanup complete on every exit.** Instance terminated, volumes deleted,
   inputs deleted, results allowlisted, schedule and roles removed — on success
   and on failure.
8. **Result re-adjudicated with the provider attestation.** The trainer-side
   verdict is `EVIDENCE_INCOMPLETE` by design; the outer provider receipt
   supplies the attestation and re-adjudicates with the unchanged adjudicator.
9. **Automatic test-point outputs produced.** Startup identity report,
   per-transition failure record, and development scorecard — observing and
   reporting only; the layer never intervenes and never opens private targets.

---

## 6. Source freeze definition

- The run builds the package from exact Git objects at a single 40-hex commit.
- After this freeze, any change to the trainer, data builder, dataset,
  adjudicator, or protocol requires a new owner-approved pre-run amendment
  before the run. No threshold changes are permitted after scores exist.

**Current bound packet source and hash (recorded here):**

- `publication_packet.json` top-level `source_commit`:
  `c4c2373b5337ebbe617b825cb89d99a8d999f62b`
- `publication_packet.json` SHA-256 (computed by Lane C from the current file
  bytes):
  `c281253f80d2e114d8017bb2c392f92ad03bd7d9b9c8c28e904a037a5c3fd0d8`

The packet is byte-bound evidence generated and re-verified by
`tools/verify_condition_skill_v9_publication_packet.py`; packet bytes are
LF-only by construction.

---

## 7. Reporting

Report untrained/trained CAS, untrained/trained generic, the integer rule, and
constant predictors. Include:

- first-wrong-bit counts;
- equality and unit-margin slices (separate reported counts);
- actual attempted denominators (all attempted rows, including `NO_EFFECT`);
- per-family gate rows (never erased by the combined verdict);
- initial-versus-trained observations (improvement through training);
- class counts, checkpoint identities, and compute used.

"Not reached" is never reported as "failed". Exact-zero neural Effects mean
`NO_EFFECT`, not a free L0 answer. Missing provider attestation prevents final
acceptance without turning recorded predictions into incorrect predictions.

---

## 8. Owner-approval sign-off

Owner: check one box per item. Nothing below is pre-ticked.

Signing this record re-binds the approval to the packet identity recorded in
section 6 (`c4c2373b…` / `c281253f…`) and supersedes the older packet values
still recorded inside `OWNER_PHASE_APPROVAL.json` (which bound the state at
the time of that earlier approval and remains preserved history).

### 8.1 Proceed to freeze

- [ ] I approve proceeding to freeze: no further changes to the trainer, data
      builder, dataset, adjudicator, or protocol after this record.

### 8.2 F5 ruling — `instance_count` and the attestation key set

- [ ] Amend now (owner-approved pre-run amendment): add `"instance_count": 1`
      to `PROVIDER_ATTESTATION_KEYS` so re-adjudication enforces the
      single-instance bound.
- [ ] Run as frozen: proceed with the adjudicator's current key set unchanged
      (`instance_count` remains enforced by launcher preflight only).
- [ ] Wait: hold the run until the F5 question is ruled.

### 8.3 Authorize the single paid run

- [ ] I authorize exactly one paid training run under the frozen resource plan
      and execution gates above (one `$4.00` reservation, zero automatic
      retries).
