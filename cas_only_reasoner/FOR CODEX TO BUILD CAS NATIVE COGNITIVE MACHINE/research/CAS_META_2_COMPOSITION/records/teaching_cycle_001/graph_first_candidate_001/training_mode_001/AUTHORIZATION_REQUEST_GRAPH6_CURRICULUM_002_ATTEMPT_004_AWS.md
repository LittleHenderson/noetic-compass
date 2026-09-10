# GRAPH6_CURRICULUM_002 — attempt 004 (REPLACEMENT) — bound request for approval

Status: **AWAITING_OWNER_APPROVAL.** The delivery rehearsal the owner required has
passed; the package identities below are updated for every changed member.

## 1. The rehearsal (no neural execution, no paid launch)

`tests/test_graph_training_delivery_rehearsal.py` runs the **actual exported
chain** — the rendered worker's inner runner → the exported `upload_results` →
the launcher's real `wait/collect/cleanup` — against a simulated bucket, with a
dummy result and four dummy checkpoint files. Only the training call and the
storage service are substituted.

| Path | What is demonstrated |
| --- | --- |
| **Normal completion** | The collector receives the known result (byte-identical, sha256 checked) and **every** dummy checkpoint with matching hashes and byte counts. The completion signal `results/result.json` is uploaded **last** — every artifact and the manifest are already in the bucket when it appears. Verified collection ⇒ cleanup deletes the bucket; the instance is `CONFIRMED_TERMINATED`. |
| **Upload failure after the dummy experiment returns** | The original result survives **byte-for-byte**; the failure is written to a separate `failure.json`; no completion signal ever appears; collection cannot start (`CURRICULUM_COLLECT_STATE`); **cleanup retains the bucket**, names it in `retained_bucket`, records `EVIDENCE_RETAINED_PENDING_COLLECTION`, and the compute **still stops** (`CONFIRMED_TERMINATED`, nothing pending). |
| **Checkpoints lost in transport** | The missing checkpoint is named explicitly (`artifacts_missing: ["<name>"]`, `reason: ARTIFACTS_MISSING:<name>`), `artifacts_available: false`, collection **not** verified, bucket retained. |
| **Three outcomes reported separately** | `stages.execution` / `stages.collection` / `stages.cleanup` and `completed_deliverable` (true only when all three succeeded). |

**Conditional evidence deletion (new behaviour).** Compute shutdown and evidence
deletion are now separate: the instance always terminates by its deadline, while
the bucket is deleted **only** when `collection_is_verified(collected)` holds —
the local receipt contains the result bytes and every artifact the result
promised. Otherwise the bucket is retained as a bounded, explicit exception, and
the job is reported incomplete.

**What the rehearsal does not establish:** that real cloud transport can never
fail. It establishes that the program behaves correctly on the failures it was
deliberately given.

**257 graph tests pass** (4 of them the rehearsal).

## 2. Corrections the owner asked for

* Attempt 003's traceback position is **reported execution progress**, not a
  recovered scientific result: with the result and checkpoints gone, the
  comparison's outcome is **unavailable** and none of its numbers are reported.
* The four failed allocations are **`$27.00` consumed from the campaign's
  reservation allowance**; no invoices were inspected, so this is not
  independently verified billing.
* The earlier claim "a completed result can no longer be destroyed" was
  over-stated; the rehearsal now demonstrates delivery instead of asserting
  preservation.

## 3. Bound package (built; NOT launched)

| Field | Value |
| --- | --- |
| source_sha | `aecb5d07eed62fad8e18fd859484f253870d8c3b` |
| archive_sha256 | `fd9b4902ebf5aadfceab304797f69cdd8731f4ce3a09b82b57a8d63e8cbe2ac7` |
| archive_bytes | 410024 |
| manifest_sha256 | `45fd5339dbee6c8e86f48cd488f4085c8a6b966bf729630fd401ab5c2dd577ac` |
| member_count | 37 |
| package | `training_mode_001/graph6_curriculum_package_005/` |
| launch request | `training_mode_001/graph6_curriculum_launch_005/launch_request.json` (sha256 `950bd79868d0c7c4f073c1e9922fe9c34d5136a72a03c3f8211aff6134a0729a`, `launch_authorized: false`) |
| proposed job | `cas-meta2-graph6curr-20260910133000-aecb5d07` |
| launcher | `aws/graph_training_curriculum_launch.py` at commit `aecb5d07` |

## 4. The experiment is unchanged

Frozen candidate, encoder, tokenizer fitting set, CAS framing, `operation:^6`
scope, scoring and thresholds; **control** = the existing 30 lessons, **varied** =
the 30 new relationship lessons (with `none` offered in 7 shared-part lessons:
correct in 4, an incorrect distractor in 3); **three paired seeds**
`20260913/14/15` with matched initial weights and separate optimizer states;
balanced schedule identical in both conditions; **checkpoints at 64 and 256
updates**; **six learners / 1,536 updates**; the untouched final panel (30
pairwise non-isomorphic arrangements, 90 cases, reach 10/10/10, teaching envelope
and vocabulary only — equal difficulty not claimed); real checkpoint files
reloaded and verified in-job; pre-registered rules unchanged
(`VARIED_CURRICULUM_BETTER` iff ≥ 2 of 3 seeds show varied−control ≥ +0.10 with
family-clustered 95 % CI low > 0 **and** ≥ 2 reach 0.50 absolute). No new
diagnostic job is added.

## 5. Budget

| Item | Value |
| --- | --- |
| Instance | 1 × `g7.2xlarge` (RTX PRO 4500), no T4 fallback |
| Wall ceiling | 900 s per learner, 3,600 s worker, 7,200 s instance (2 h) |
| Reservation | one new **`$7.00`** (single attempt, no automatic retry) |
| Ledger after | revision 50 → 51: `$270.00` reserved / `$130.00` unreserved (cap `$400.00`) |

## 6. Deliverable

The collected result and the usable checkpoint files, with execution, collection
and cleanup outcomes reported separately. "The experiment finished but its result
disappeared" is not a completed deliverable, and `completed_deliverable` now
records that distinction in the evidence.

**Awaiting GO for this single bound attempt.**
