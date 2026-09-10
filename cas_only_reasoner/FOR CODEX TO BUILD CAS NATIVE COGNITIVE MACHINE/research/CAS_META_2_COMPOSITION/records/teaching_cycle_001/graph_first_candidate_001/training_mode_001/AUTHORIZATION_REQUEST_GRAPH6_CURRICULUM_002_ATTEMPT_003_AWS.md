# GRAPH6_CURRICULUM_002 — attempt 003 (REPLACEMENT) — authorization request (PACKAGE BUILT; NOT REGISTERED, NOT RESERVED, NOT LAUNCHED)

Status: **AWAITING_OWNER_APPROVAL.**

## Honest status first: three paid attempts, three failures, all mine

| Attempt | Job | Spent | Where it died | Defect |
| --- | --- | --- | --- | --- |
| confirmation 001 | `…competence`/graph6conf `…951cab20` lineage | `$6.00` | first candidate's before-loss pass | the learner-init seed was passed where the DATASET seed was required |
| curriculum 001 | `cas-meta2-graph6curr-20260910053000-951cab20` | `$7.00` | first checkpoint reload, before training | payload embedded `torch.__version__` (type `TorchVersion`), refused under PyTorch's `weights_only=True` default; plus `collect()` demanding an artifact manifest from a failed worker |
| curriculum 002 | `cas-meta2-graph6curr-20260910073000-210109c7` | `$7.00` | first learner's before-loss pass | every learner was indexed by the frozen lessons while the **varied** condition trains on the varied curriculum |

Total spent with no measurement: **`$20.00`**. Every failure was in my new
experiment code, every one was caught before any training, every one was preserved
verbatim, and cleanup completed each time (instances terminated, buckets deleted,
hygiene re-checked independently). No frozen machinery has been implicated.

## What attempt 002 exposed, and what changed

A real `GraphLearner` indexes the records it is handed and raises `KeyError` for
any other record id. `launch` built **every** learner over the frozen
train+practice tasks, so the varied learner's first before-loss pass looked up a
record it had never been given. This is the same *class* of defect as confirmation
attempt 001 (training data and learner index disagreeing), so the fix is a
contract change, not a one-line patch:

1. **Per-condition learner tasks** — each learner is built over its OWN
   condition's lessons; the injected factory contract is now explicit:
   `learner_factory(framework, own_tasks)`.
2. **Fail-closed pre-flight guard** — `_require_indexed_learner` scores the
   learner's own records before any training and raises
   `LEARNER_INDEX_MISSING_OWN_CONDITION_RECORDS` instead of a bare `KeyError`.
3. **Reload verification corrected** — `verify_checkpoint` now takes
   `learner_for(framework)` and predicts with the **reloaded** module; before, it
   rebuilt a fresh module but built the learner from the *original* framework, so
   the "reload restores behaviour" check would have been vacuous.
4. **Practice measurement clarified** — practice accuracy is measured on the
   frozen train+practice records for BOTH conditions (comparable, through the
   sealed path), and each learner's accuracy on its **own** curriculum is reported
   separately as `own_curriculum`.
5. **Three regression tests that would have caught this locally** — an
   index-enforcing learner double that reproduces the real `KeyError` contract, an
   end-to-end `launch` test asserting every learner and every reload verification
   is bound to exactly one of the two condition lesson sets, and a
   state-dependent learner proving the reload check fails when the file does not
   match. **249 graph tests pass.**

## What did work

The launcher's fail-closed path again behaved correctly: one reservation created
once, worker error preserved verbatim, evidence persisted, cleanup complete, zero
retries. Attempt 002 also confirmed the attempt-001 fix: the run reported
`AWS_CURRICULUM_FAILED` (a recorded worker failure) rather than the misleading
`AWS_CURRICULUM_LAUNCH_FAILED`.

## Frozen design (unchanged)

Frozen candidate, encoder, tokenizer fitting set, CAS framing, `operation:^6`
scope; control = the existing 30 lessons, varied = the 30 new relationship
lessons (with `none` offered in 7 shared-part lessons: correct in 4, an incorrect
distractor in 3); three **paired** seeds `20260913/14/15` with matched initial
weights and separate optimizers; balanced schedule identical in both conditions;
checkpoints at **64** and **256**; **6 learners / 1,536 updates**; the untouched
final panel (30 pairwise non-isomorphic arrangements, 90 cases, reach 10/10/10,
teaching envelope and vocabulary only — equal difficulty is **not** claimed); real
checkpoint files with in-job reload verification and verified artifact collection
before bucket cleanup; the pre-registered rules with thresholds unchanged.

## Exact package (built; NOT launched)

| Field | Value |
| --- | --- |
| source_sha | `c13f9a5ed85e4aa0460414e3c2d1e25585edcaaa` |
| archive_sha256 | `ae56bc10c13fc17a087fd38c88fe64da45f40d7a8a53f4d52ad5cb50449f601e` |
| archive_bytes | 409373 |
| manifest_sha256 | `d2fcc8fba16b99beb68746e6a5c03c0cb7ddf2ec11f6a68f6b5539b091b8fb4f` |
| member_count | 37 |
| package | `training_mode_001/graph6_curriculum_package_003/` |
| launch request | `training_mode_001/graph6_curriculum_launch_003/launch_request.json` (sha256 `ac71b6ff648dba14143fee31b4fecbde66074f455eedc71fbb21c6702dd024f3`, `launch_authorized: false`) |
| proposed job | `cas-meta2-graph6curr-20260910093000-c13f9a5e` |
| launcher | `aws/graph_training_curriculum_launch.py` at commit `c13f9a5e` |

## Budget

| Item | Value |
| --- | --- |
| Instance | 1 × `g7.2xlarge` (RTX PRO 4500), no T4 fallback |
| Wall ceiling | 900 s per learner, 3,600 s worker, 7,200 s instance (2 h) |
| Reservation | one new **`$7.00`** |
| Ledger after | revision 49 → 50: `$263.00` reserved / `$137.00` unreserved (cap `$400.00`) |
| Retries | zero; original errors preserved; verified cleanup; artifacts collected first |

## What I need from you

**GO / NO-GO** for this replacement job (one new owner-signed record + one new
`$7.00` reservation). I recognise three consecutive failures is a poor record on
this job. The specific reasons for confidence this time: the failure mode is now
guarded by a fail-closed check that fires *before* training, it is covered by an
end-to-end local test that reproduces the real learner's index contract, and the
reload verification has been fixed to actually test the reloaded module. If you
would rather stop spending on this design, the honest alternative is to record the
three failures as the outcome and return to the panel/curriculum design without a
further run.
