# AUTHORIZATION_REQUEST_001 — bounded two-condition checked-component pilot

**Status: REQUEST ONLY. Not approved, not scheduled, not reserved, not launched.**
No neural execution, no AWS call, no reservation, and no ledger mutation happens until the
owner approves this specific request. This document prepares the numbers; it does not
authorize them.

**Experiment label:** checked component teaching, two conditions, within-scene probe.
**Not** a test of the complete seven-stage cube program — stages 1, 2, 3, 4 and 6 still
have no numerical delivery path.

## 1. Package and data (exact)

| Item | Value |
|---|---|
| Pinned public graph | `cube_node_001/Cube_Node_Example_v0.1.json`, 29,971 bytes, sha256 `9e62538b807d0b7a6fc04890c4ee0504db53e45bc34b62504f001d7f0610eb32` |
| Teaching records | 8 records from `exports/declared/`, ordering mode **`declared`** |
| Distinct taught questions | **7** (8 records; the `REACHED_VIA(Bicycle, Rim)` route appears once as a component question and once as a whole-answer question) |
| Repeated-question exposure | that route receives **16 corrections across 8 blocks**; the other six distinct questions receive 8 each |
| Untaught probe | **44 questions** = 51 catalog questions − 7 distinct taught; `REACHED_VIA` 25, `FIND_SHARED_PART` 14, `LIST_PARTS` 5 |
| Probe membership rule | catalog minus the union of semantically taught questions, keyed on graph context + operation + named arguments; exercise ids, task-profile labels, phase labels and option order ignored |
| Additional exclusions | none |
| Source for the run | this record's `candidate_run.py`, `verified_training.py`, `verified_teaching.py` at the commit named in the request |

## 2. Conditions (exactly two)

| Condition | Component corrections | Whole-answer corrections | Total | Notes |
|---|---:|---:|---:|---|
| `checked_component_teaching` | 40 | 24 | **64** | 8 blocks: five component questions, then the three whole-answer questions |
| `final_answer_only` | 0 | 64 | **64** | frozen order, round-robin over the three whole-answer questions, remainder to the first: **22 / 21 / 21** |

**Matched comparison.** Two candidate copies from the **same initial weights**; identical
frozen encoder and fitted tokenizer; identical graph, framing, and scoring path; identical
seed, update allowance, and stopping limits. **Separate** optimizer state, checkpoint
identity, and observation records. The teaching allocation is the only intended
difference.

**What this comparison can show:** at the same number of updates, is it better to spend
some practice on the parts of the problem rather than spend every update on the complete
questions?

**What it cannot show:** it does not isolate the effect of adding component instruction
while holding final-question practice equal. The control practises the final questions far
more often (64 versus 24). A third condition would be needed for that; none is proposed.

**Seed:** `20260909` (the frozen encoder seed already used by this path). Any change to the
seed is a change to this request.

## 3. Execution limits

| Limit | Per condition | Combined |
|---|---|---|
| Optimizer updates | 64 | 128 |
| Training wall clock | 600 s (`trainer.FROZEN_MAX_WALL_SECONDS`) | 1,200 s |
| Checkpoints written | the final state, plus the declared checkpoints if the profile requires it | 2 final states |
| Evaluation | 44 probe questions + the 3 taught whole-answer questions, after the final checkpoint, **no updates during evaluation** | as per condition |
| Automatic retries | **0** | **0** |
| Partial-probe rule | the probe never selects a checkpoint, adjusts the curriculum, or extends training mid-run | same |

Frozen training constants reused unchanged: learning rate `0.003`, update allowance
`64`, wall clock `600 s`, arm `cas`.

## 4. Reservation

| Item | Proposed |
|---|---|
| Reservation amount | **`$7.00`** — reusing `aws/graph_training_curriculum_launch.py::RESERVATION_USD` unchanged |
| Basis | the existing frozen resource plan: 1 × `g7.2xlarge` in `us-west-2`, on-demand ceiling `$2.52`/h, `instance_seconds_max` 7200, plus `$1.48` ancillary, rounded up |
| Tighter alternative | `instance_seconds_max` 3600 → 1 h × $2.52 + $1.48 = **`$4.00`**; this changes a frozen resource-plan field and would need its own stated approval |
| Ledger | the campaign ledger last stood at revision 51: `$270.00` reserved of `$400.00`, `$130.00` free. A `$7.00` reservation would be revision 52. The ledger is owned by another workstream and is **not** written by this work |
| Recommendation | the `$7.00` ceiling, because it changes no frozen field |

**An unspecified cost is not approved.** If the owner prefers `$4.00`, that is a stated
change to the resource plan and must be approved as such.

## 5. Checkpoint delivery and collection

Reusing the existing delivery chain, unchanged:

1. The worker writes artifacts **first**, the manifest next, and `result.json` **last**.
2. Each condition's final checkpoint is written, then read back and verified against its
   identity before upload (`CANDIDATE_CHECKPOINT_NOT_VERIFIED` otherwise).
3. Collection is verified (`collection_is_verified`); a partial collection is reported as
   partial, with the missing members named, never as success.
4. Delivered evidence: per-condition `result.json`, the final checkpoint per condition,
   the per-step observation record, the containment report, and the probe results —
   scored separately per condition.

## 6. Cleanup and shutdown policy

Reusing the existing cleanup contract, unchanged:

* The instance is **always** terminated by the deadline, whether or not collection
  succeeded.
* The evidence bucket is deleted **only** when collection is verified. If collection
  fails, the bucket is retained, named in the report, and the run settles as
  `EVIDENCE_RETAINED_PENDING_COLLECTION`.
* Compute shutdown and evidence deletion stay separate decisions.
* Zero automatic retries: a failed condition is reported as failed, not restarted.

## 7. What is reused, and what must differ

**Reused unchanged:** the request/authority binding, the account and region
(`807562639912`, `us-west-2`), the AMI `ami-0fbbd0facbc9e3cff`, the instance type and count,
the resource-plan schema, the staging and upload path, the outer-worker delivery chain,
collection verification, cleanup and evidence retention, and the zero-retry policy.

**Must differ (and therefore needs its own approved binding):** the frozen design block
this launcher currently carries belongs to the curriculum experiment (`FROZEN_CONDITIONS
("control", "varied")`, `FROZEN_TOTAL_UPDATES 1536`, `FROZEN_PAIR_SEEDS` ×3,
`FROZEN_PANEL_SEED 20260930`, job pattern `cas-meta2-graph6curr-…`). This pilot needs its
own frozen block — two named conditions, 64 updates per condition, seed `20260909`, no
panel, the 44-question probe — and its own entrypoint
(`cas_meta2.graph_teaching.candidate_run.run_candidate`) and job pattern. **Producing that
bound request is a launcher change, and it is not made here**: the owner asked to reuse
the infrastructure rather than add another launcher, so the change is proposed, not
applied, until this request is approved.

## 8. Reporting plan

* **Taught whole-answer questions (3):** before and after — the selected answer, all three
  scores, and the loss for each. The primary set holds three questions, so one changed
  answer moves accuracy by 33.3 percentage points; **no single percentage carries the
  conclusion**.
* **Component questions (5):** reported separately — before and after.
* **Untaught probe (44):** counts and accuracy by operation, the **same set for both
  conditions**, gathered after the final checkpoint with no updates.
* **Assisted versus independent:** never merged. "Independent" here means no worked answer
  is supplied during prediction; it does **not** mean the taught questions have become
  unseen questions.
* **Missing measurements:** `unavailable`, never zero.
* **A negative result means:** this component-teaching allocation did not help under these
  conditions. It does **not** mean the complete seven-stage method failed.

## 9. Approval fields (owner-signed)

Until every field is filled by the owner, this request is inert:

```text
run_id:                     ______
approved conditions:        ______   (both, or one named)
updates per condition:      ______   (proposed 64)
reservation amount (USD):   ______   (proposed 7.00, or 4.00 with a changed plan)
instance_seconds_max:       ______   (proposed 7200, or 3600 with the 4.00 plan)
seed:                       ______   (proposed 20260909)
probe approved:             ______   (44 questions, or a named subset with the extra exclusion stated)
cleanup policy accepted:    ______   (instance always terminated; bucket only when collection verified)
auto_retries:               0        (fixed)
owner signature / date:     ______
```

No neural execution, reservation, or paid launch until this record is signed and the
launcher binding in §7 exists.
