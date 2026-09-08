# Faithful four-candidate continuation: source and preparation evidence

Recorded 2026-09-08. This file is a pre-launch report, not proof of a resumed GPU run. The source-freeze commit is the commit containing this report; the later preparation receipt records that exact commit.

## What is preserved

The original logical run is `cas-meta2-teaching-20260908052915-8b5df59c`. The frozen worker remains commit `c8c0e558cf30cd5fe06c2bf3d475697e97698a3e`, source-map SHA-256 `60340b5865c674cc5558a27da6524928ec0db7042163b1ef031591ad7794555e`. No old source or accepted weights were edited for this continuation.

All four candidates resume their own model, optimizer, teaching cursor and readiness history. The original campaign path remains `/opt/cas-teaching/job/train/campaign`; new output goes to `train_continued_001`. Prior history and the old summary must remain byte-identical. A new cloud job is not a new logical training run.

The actual prior-state ZIP has 69,165,594 bytes and SHA-256 `c70cef95b3e38a35fc7411f566b887745995708773aec277cd314714b3c792ec`. Its manifest has SHA-256 `a4fc5dd2c6d19be9740cd57a89d036725d6eaf994f0d6011239fb92cdfc6aa7b`. All 3,278 prior payload files are included. Full expanded size including the internal manifest is 97,664,905 bytes.

Saved update counts remain CAS aligned 411, CAS ordinary 392, generic aligned 392, generic ordinary 392: 1,587 of 3,584 total. There are 1,997 updates left. The original 16-epoch allocation is unchanged. At the prior pace, roughly 100 minutes remain before unmeasured restore/setup effects; one 80-minute training slice will probably save another partial result.

## Completed checks

- `continuation_integrated_checks_001/receipt.json`: **257 passed in 178.84 seconds**, exit 0, no timeout, captured source/input bytes unchanged. Receipt SHA-256 `92880ad64130bfa118b171c868cf3976ef36ce0cd7d2d7df534badfc720a92fd`. The directory retains exact commands, raw stdout/stderr and before/after hashes. These tests use fake processes, tensors and providers, with neural/NumPy/SQLite/AWS imports and socket operations blocked.
- `continuation_input_checks_001/receipt.json`: actual job003 input admission passed, exit 0 in 1.766 seconds; all 54 recorded hashes unchanged. Receipt SHA-256 `e4ddb7fff15ef7283c2a74fb01f54722b5d1786fdcd72d435699631fe3993536`. This checks real saved bytes, not tensor restoration.
- `job_003/prior_package_build_001/receipt.json`: actual package construction and original structural-inspection replay passed, exit 0, originals unchanged. Receipt SHA-256 `83d6c35d287882c876c3753b5fef57d93ecfc24e5835f3680126e6ba31575b81`.
- `live_continuation_preflight_001/receipt.json`: current read-only AWS checks passed in account `807562639912`, region `us-west-2`, for one `g7.2xlarge` / RTX PRO 4500. No conflicting active job was observed there. Compute quote was $2.52/hour; the conservative six-GB-storage worksheet was $6.486097142857142857142857143 within $8. Receipt SHA-256 `e905bb63d7d430b3b5210ee9beca1ebca6c495e758102e40ae2e81be1d2c2ed5`. It is not a capacity guarantee or invoice; execution rechecks current provider state.

## What the live run still must prove

1. Create one new bounded reservation under the existing inclusive $400 authority. At this report's preparation stage, the ledger remains revision 19: $118 reserved, $282 unreserved; SHA-256 `09ab0dcc314cd12f2e317fd6184f2007e2f759cd38eb8b9d90ad019a6589f755`.
2. Verify scheduled shutdown before releasing the guest. Setup, restore, training, prediction and collection share one 7,200-second outer deadline.
3. Restore all four actual CUDA models and optimizer states within the 180-second probe cap. Compare exact optimizer values and check their GPU placement; only AdamW's scalar step may be on CPU. Deny optimizer updates, teaching, predictions and checkpoint writes during this probe. The parent must admit its raw receipt before releasing training.
4. Run at most 4,800 seconds of training. The guest and parent reserve the same 900-second later-phase allowance, so slow setup cannot leave the parent timing out while the guest still expects to train. The worker retains its 30-second graceful-stop margin.
5. Preserve and collect any partial prefix. Only full completion of all four original allocations permits final public inputs. Two independent prediction processes must agree before the unchanged private scorer opens final targets. The new outer evaluator checks the prior-state, restore and continuation bindings without rewriting old records.
6. Verify actual cleanup and reconcile observed use. There are no automatic retries or reservation refunds.

Actual GPU restoration, new updates and final held-out scores are **UNEXECUTED** at this report's pre-launch stage. The 180-second restore duration is unmeasured on AWS. See later launch receipts for any changed status.

## Learning boundary

The CAS plateau remains a real negative. Both CAS candidates scored 21/64 on their latest development check; generic aligned scored 42/64 and generic ordinary 46/64. These are worker-recorded scores, not independent checkpoint reruns. CAS's epoch-7 training loss is also near uniform three-choice prediction. The recorded gradient paths are active, but useful gradient strength and the cause of the plateau are not established. `job_003/BINDING_DIAGNOSIS.md` preserves the evidence and a length-dependent-gate hypothesis without claiming causal proof or changing the experiment.

This pilot teaches input binding, not unfamiliar nested-program composition, full native execution, language, general reasoning or the completed CNCM. Earlier 24/24 familiar-program and CAS 0/72 held-out composition results remain separate evidence. The full CAS/CNCM vision remains the objective.

Use `CONTINUATION_COMMANDS.md` for command order and the full local working-directory address. All paths in this report are relative to this report's directory.
