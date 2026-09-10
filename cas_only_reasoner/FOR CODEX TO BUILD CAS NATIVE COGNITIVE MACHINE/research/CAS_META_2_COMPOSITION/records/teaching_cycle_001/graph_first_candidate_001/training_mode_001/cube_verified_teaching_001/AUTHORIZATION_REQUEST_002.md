# AUTHORIZATION_REQUEST_002 — final execution request (checked-component pilot)

**Status: REQUEST ONLY — NOT APPROVED, NOT RESERVED, NOT LAUNCHED.**
Everything the run needs is built, tested and packaged. The only missing pieces are the
owner's authorization-record hash and signature, and the one launch decision.

Supersedes `AUTHORIZATION_REQUEST_001.md` (§8 fields now filled from the built artifacts).

## 1. Package identity

| Item | Value |
|---|---|
| Source commit | `c48f5838fcaecbf507ae58eaa48b430a29cec5ee` |
| Package | `records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/cube_verified_teaching_001/candidate_package_001/source.zip` |
| Archive sha256 | `0a55f4b1eaab561c08b4d94acd4430c6c0f758a0a0648c8b0663f4f5987bdb55` |
| Archive bytes | 488,735 |
| Manifest sha256 | `14fc7d1373cfd18af2ee0e3ae3086e75ad9ebb56ffa440b38eb288cba8d5c5b4` |
| Members | 44 |
| Worker script | `graph6_candidate_worker.py` |
| Status | `SOURCE_ONLY_NO_LAUNCH` (`launch_enabled: false`) |

## 2. Launcher identity

| Item | Value |
|---|---|
| Module | `aws/graph_training_candidate_launch.py` |
| Schema | `cas-graph-training-candidate-launch/1` |
| Experiment profile | `graph_training_candidate_component_pilot` |
| Entrypoint | `cas_meta2.graph_teaching.candidate_experiment.launch` |
| Job pattern | `cas-meta2-graph6cand-\d{14}-[a-f0-9]{8}` |
| Proposed job | `cas-meta2-graph6cand-20260910120000-0a55f4b1` |
| Request record | `candidate_request_001.json` (inert: `launch_authorized: false`) |
| Authority template | `candidate_authority_TEMPLATE.json` — the frozen fields plus three annotation keys (`status`, `unfilled`, `note`) |
| Reused unchanged | resource plan, reservation scope, package builder, staging, delivery, collection verification, cleanup and evidence retention, zero-retry policy |

**Note on the template.** The launcher accepts an authority only with the **exact** field
set, so the signed authority must be the template with the three annotation keys removed
and `owner_authorization_sha256` filled. The template as it stands is refused with
`CANDIDATE_AUTHORITY_FIELDS`; a signed file missing the hash would be refused with
`CANDIDATE_AUTHORITY_HASH:owner_authorization_sha256`. Both refusals are by design.

## 3. Data and design (frozen)

| Item | Value |
|---|---|
| Public graph | `cube_node_001/Cube_Node_Example_v0.1.json`, sha256 `9e62538b…10eb32` |
| Ordering mode | `declared` (the candidate export) |
| Teaching records | 8 records, **7 distinct questions**; `REACHED_VIA(Bicycle, Rim)` is taught twice per block (16 corrections across 8 blocks) |
| Untaught probe | **44 questions** (`REACHED_VIA` 25, `FIND_SHARED_PART` 14, `LIST_PARTS` 5); same set for both conditions |
| Conditions | `checked_component_teaching` (40 component + 24 whole-answer) and `final_answer_only` (0 + 64) |
| Control ordering | frozen round-robin, 22 / 21 / 21 |
| Seed | `20260909` (encoder seed `20260909`), arm `cas` |
| Matched comparison | identical initial weights (proven by snapshot equality at run time), same frozen encoder/graph/framing/scoring, separate optimizer state and checkpoints |
| Per condition | 64 updates, 600 s wall clock |
| Combined | 128 updates, 1,200 s training; the probe runs after each condition's final checkpoint with no update |
| Retries | **0**; a failed condition is reported, never restarted |
| Checkpoints | one final state per condition, saved and read back for identity verification |
| Reporting | before/after selected answer, three scores and loss per taught whole-answer question; component questions separately; probe by operation; independent and assisted never merged; missing = `unavailable` |

## 4. Reservation

| Item | Value |
|---|---|
| Amount | **`$7.00`** — the existing resource plan carried forward unchanged (owner's choice) |
| Basis | 1 × `g7.2xlarge`, `us-west-2`, on-demand ceiling `$2.52`/h, `instance_seconds_max` 7200, plus `$1.48` ancillary, rounded up |
| Ledger | last reported revision 51: `$270.00` reserved of `$400.00`. A `$7.00` reservation would be revision 52. The ledger is owned by another workstream and is not written by this work |
| Not approved by this document | the amount above is proposed; **an unspecified or unsigned cost is not approved** |

## 5. Delivery and cleanup (reused policy)

* Worker-side: artifacts uploaded first, manifest next, **`result.json` last**; a failure
  writes `failure.json` and `result_partial.json` and uploads what exists.
* Collection verified before success is claimed; a partial collection is reported as
  partial with the missing members named.
* The instance is **always** terminated by the deadline; the evidence bucket is deleted
  **only** when collection is verified, otherwise retained with
  `EVIDENCE_RETAINED_PENDING_COLLECTION`.
* Compute shutdown and evidence deletion stay separate decisions.

## 6. The command that will execute it, after approval

```powershell
cd "C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\meta1\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\research\CAS_META_2_COMPOSITION"

# plan only, no provider call (safe to run now)
python -m aws.graph_training_candidate_launch

# the paid run — REFUSES until the authority is signed and hash-bound
python -m aws.graph_training_candidate_launch --execute `
  --request <candidate_request_001.json> `
  --request-sha256 <sha256 of that file> `
  --authority <owner-signed authority.json> `
  --authority-sha256 <sha256 of that file> `
  --owner-authorization <owner signed authorization record path> `
  --receipt-dir records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/cube_verified_teaching_001/receipt_cas-meta2-graph6cand-20260910120000-0a55f4b1
```

The launcher validates the request, the authority, the owner-record hash, the ledger, and
the absence of a prior reservation for this job before it reserves anything.

## 7. What only the owner can fill

```text
owner authorization record path:  ______
owner_authorization_sha256:       ______   (sha256 of that record; goes into the authority file)
run_id / job:                     cas-meta2-graph6cand-20260910120000-0a55f4b1  (or a new name)
reservation amount (USD):         7.00     (or 4.00 with a changed, approved resource plan)
probe approved:                   44 questions (recorded) — or a named subset with an extra exclusion stated
conditions approved:              both     (or one, named)
cleanup policy accepted:          ______   (instance always terminated; bucket deleted only when collection is verified)
owner signature / date:           ______
```

## 8. Attempt log after the owner's `$7.00 run.` authorization

| Attempt | Outcome | Spend |
|---|---|---|
| 001 | `KeyError: 'sts'` at preflight: my client set named three of the five clients the reused lifecycle asks for | **none** — before the reservation |
| 002 | `AccessDeniedException` from `pricing.get_products` at preflight: the Pricing client was built in `us-west-2`, not `us-east-1` | **none** — before the reservation |
| 003 | preflight passed; the **single `$7.00` reservation was taken**; then `launch()` failed with `CURRICULUM_SOURCE_ARCHIVE_REQUIRED` because `main()` never passed the built package's `source.zip` | **`$7.00` consumed** |

Attempt 003's evidence is preserved at
`receipt_cas-meta2-graph6cand-20260910120000-0a55f4b1_attempt003/` (`intent.json`,
`preflight.json`, `provider_000[1-3].json`, `reservation.json`, `failure.json`,
`result.json`). Ledger after it: **revision 52, `$277.00` reserved of `$400.00`,
`$123.00` free**, job `cas-meta2-graph6cand-20260910120000-0a55f4b1` recorded.

Attempt 003 created **no instance and no evidence bucket** and trained nothing. The
cleanup report reads `INCOMPLETE` only because it tried to remove a scheduler and a role
that were never created. One S3 object remains: the budget helper's own reservation
receipt bucket `cas-meta2-graph6cand-20260910120000-0a55f4b1-807562639912`, which is part
of the ledger's audit trail and is left in place.

Four fixes are in, none of which can spend a reservation:

1. `main()` locates and passes the archive by the hash the request binds.
2. `execute()` refuses **before** the reservation unless the provider holds a readable
   source archive whose digest matches the request — two tests prove `reserve()` is never
   reached when the check fails.
3. `_locate_archive()` hashes the candidate file before accepting it, because scratch
   receipts elsewhere in `records/` carry synthetic hashes.
4. The client set and the Pricing region are checked against the reused source by tests.

**No second launch has been made.** The owner's single authorization is consumed, and
another attempt needs a new owner GO for a second `$7.00` reservation (ledger revision
53). The exact command is §6 above with a fresh `--receipt-dir` ending `_attempt004`.

## 9. What this request does NOT authorize

* No reservation, provider call, neural execution, or paid launch until §7 is signed.
* No change to the fixed architecture, readout, pooling, embeddings or tokenizer.
* No reuse of the earlier results, checkpoints, panels or curricula as evidence here.
* No claim that this pilot tests the seven-stage program: definition, analogy,
  correspondence and story presentations remain numerically unimplemented.
* No automatic retry, and no probe-driven checkpoint selection or mid-run curriculum
  change.
