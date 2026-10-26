# HELM M1 H8 follow-up plan

**Status: IMPLEMENTED IN VERSIONED V2 PACKAGE; FROZEN BEFORE SCORING; NOT RUN.**

This note preserves the M1 result and records the frozen bounded follow-up. It is not an amendment to the frozen M1 package, a new result, an owner decision about memory behavior, or authorization to spend.

## Current evidence

- The original M1 result remains 🟥 `M1_FAILURE`: H8 recorded 15 violations in 1,769 checks. Its frozen reader returns no other status words after a hard-mark failure. The result and frozen source remain unchanged.
- In the original H8 rule, a RELEASED query that touches a planted missing, corrupt, or stale copy must return `UNKNOWN` or labelled `RECONSTRUCTED`.
- In `m1_run/engine.py`, `_fetch_original` tries original copies in order. It marks a missing or digest-mismatched copy and continues. It returns bytes only after a copy matches the expected source digest.
- In `m1_run/runner.py`, H8 detects whether the query added any entry to the fault store's `touch_log`. The log says which copy was touched, but the saved answer receipt does not bind the answer to the selected copy.
- Therefore the recorded `EXACT` / `COLD_ORIGINAL` answer could be from a healthy verified copy after another copy failed. The existing evidence cannot establish that. The original H8 failure remains valid under its frozen rule; do not relabel it as a pass.

Source identities: M1 source manifest SHA-256 `d940074a4696c8fed88b8b7ffa2127af4e6d82a1bdccfae2bc40f29f6946509d`; merged reading SHA-256 `d624050bf2a9cf952b6ad00457d417bb85c60043e6ec544faa758585eea32cfb`.

## Engineering question

When a memory lookup encounters a failed copy, should HELM stop and return `UNKNOWN` / `RECONSTRUCTED`, or continue to another copy and return `EXACT` when that copy passes the original digest check?

The follow-up should measure both behaviors. Keep the original H8 result as historical evidence and keep the strict H8 rule separately named. Any changed rule must be declared in a new freeze before scored runs.

## Implemented receipt change

For each recall, record an ordered, query-bound copy trace:

- opaque copy identifier and copy role;
- attempt outcome (`MISSING`, `DIGEST_MISMATCH`, `STORE_UNREACHABLE`, or `VERIFIED`);
- expected digest and observed digest when bytes were returned;
- selected copy identifier, if any;
- final answer label, source, and reason.

Implemented in `C:\Users\wakil\Documents\Codex\2026-10-16\m1_h8_provenance_v2` under schema `m1.recall-copy-receipt.v1`. The receipt binds the query and item version, hashes the answer value, records ordered copy attempts and fault touches, names the selected copy, and hashes the canonical receipt body. It does not include memory contents. The scorer requires every exact external-source answer to name exactly one verified digest-matching copy.

## Frozen paired arms and gates

1. **Strict-stop arm:** after a failed original-copy touch, stop retrieval and return `UNKNOWN` or a genuinely supported `RECONSTRUCTED` answer. Read the unchanged strict H8 criterion.
2. **Verified-backup arm:** continue past failed copies. Permit `EXACT` only when the selected copy is identified and its bytes match the expected digest. A failed, unknown, or mismatched selected source must never produce `EXACT`.
3. **Scope:** `INFORMATIVE`, `M1`, `RELEASED`; faults `MISSING`, `CORRUPT`, `STALE`; three original diagnostic worlds and a 48-world fresh holdout. Clean-copy and offline-store controls are out of scope for this frozen H8 follow-up.
4. **Instrument gate:** require one complete, hashed, query-bound receipt per H8 touched question; join each fault touch to its failed original-copy attempt; require every exact external-source answer to identify one verified copy with matching expected and observed digests.
5. **Scoring gates:** report unchanged strict-H8 outcomes separately from receipt integrity and recovery counts. A pass on one cannot erase a failure on another. Each group/policy/fault cell must include at least one H8 touch. Recovery counts are descriptive and choose no winner.

The matrix is frozen in `FOLLOWUP_FROZEN.json`. It contains 3 diagnostics plus 48 holdout worlds, crossed with 3 fault types and 2 policies: 306 runs. Fresh worlds derive from the new package source-manifest hash. The original M1 run directory and manifest are unchanged.

## Execution and status

- ✅ Per-copy receipts and paired recall policies are implemented in the separate v2 package.
- ✅ Original source manifest, merged reading, P2 raw data, and `M1_FAILURE` result are preserved under `baseline/`.
- ✅ The package and protocol were frozen before scoring. New source-manifest SHA-256: `a7cf32ffba8c59f75c80fc7cbea6650210034548573ec916a910bd6f3efc4404`. Freeze SHA-256: `be89e1ad591a0890dff697dd993858df420164103af60c2191efd0dbc82bfaa4`.
- ⬜ No tests, runtime build, AWS run, or scoring was performed.
- AWS plan is one `c7i.large` On-Demand instance in `us-west-2`, a 45-minute hard lifetime, 900-second matrix cap, 3 GiB process address-space cap, 100 MiB output cap, and US$1 total ceiling. Before launch, recheck live rates and stop if the cap could be exceeded. The plan includes private S3 transport, termination, volume deletion, and bucket/object cleanup.
- The AWS CLI is unavailable in this workspace, so no AWS capability or account permissions were claimed. Future compute must use AWS; there is no laptop fallback.

## Recommended next move

Before running, confirm that the frozen package still matches its manifest, the AWS role can access only the exact private staging/output objects, the live price check fits the US$1 ceiling, and the 45-minute terminator is set. Then run and score only this frozen matrix on AWS. Keep M1's existing `M1_FAILURE` unchanged.
