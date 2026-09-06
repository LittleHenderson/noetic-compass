# One-child native qualification: refused, evidence preserved

The AWS run completed with a negative result: `VERIFIED_QUALIFICATION_REFUSAL`. The curriculum is **not qualified for training**. Parent exit 1 records the failed diagnostic; it is not a successful learning run. AWS cleanup is separately confirmed.

## Result

The first public development request asked for the B input and the C-only child. Its private reference and three candidate programs completed. The fourth candidate, R input with the C→R child (`R_CR`), raised `MetaRuntimeError: NATIVE_RESULT_NOT_RETURNABLE` before completing.

| Execution under the same public request | Completed | Native ticks in completed audited record | Whole-task correct | Final output |
| --- | --- | ---: | --- | --- |
| Private B_C reference | Yes | 5 | Private reference check only | Reference |
| Candidate B_C | Yes | 5 | Yes | Matches reference bytes |
| Candidate B_CR | Yes | 6 | No | Different bytes |
| Candidate R_C | Yes | 5 | No | Different bytes |
| Candidate R_CR | No | Unknown | Not evaluated | No completed result |

There were **5 attempts, 4 complete audited executions and 21 ticks in those completed records**. Fifteen of the planned 20 executions were not attempted. The 110-tick plan was not completed. Any additional ticks inside the failed attempt have not been counted; the local analysis did not open its database. The four completed executions reserved 1512 internal policy units; this is not a total for the failed attempt or a FLOP count.

All four completed stored audits explicitly checked the sealed action. The same-public-request preludes matched. The correct candidate passed the unchanged whole-task verifier; two wrong choices executed but failed task verification and changed final output bytes. These limited observations do not qualify all four targets or any held-out task. The full panel stopped before discrimination was finalized because the fourth candidate could not complete.

All 16 candidate actions had been sealed before any private reference execution. Only the first development request was attempted. No weights were trained. The accepted executor, verifier and model bytes were not changed. Earlier CAS held-out composition **0/72** and familiar-program **24/24** remain separate evidence.

## Exact unresolved point

The failed arm has only `failure.json` and `native.db` in the result archive. The database is 1,523,712 bytes and remains preserved. No completed trace export, composition-event export, kernel-event export or result document exists for that arm.

The pinned META-0 source raises this exception after a native inference call has returned and the plan, model and cross-CJT checks have passed, when it cannot accept a single published effect or enter a configured repair continuation. This generated native-step wrapper has no repair branch. This is not the earlier explicit `CJT_SCOPE_DENIED` check.

The available JSON does **not** establish which native operation failed, its decoded versus expected label, the underlying verifier reason or the failed arm's tick count. In particular, do not claim that the final R was the failed operation just because the candidate was R_CR. The next diagnostic must inspect the saved failure database on AWS before any change to the curriculum. Do not weaken the accepted verifier, silently substitute another fixture or train on the unqualified held-out R_CR tasks.

## Bound identities

Job: `cas-meta2-20260906155525-195f5ad8`

Instance: `i-093f35093d672bcae`, account `807562639912`, region `us-west-2`.

- Parent and worker source: `b61b011c3d53ae49a1f7f988397df632e95e82a6`.
- Prelaunch source/evidence registration commit: `a8376f663acc76fa966d9663a9c28a8d61dcba87`.
- Source archive: `d93a39f3a264c23f27ac7dcdd2779eca665150a6bd739820651e953958e8f7d3`, 8,086,367 bytes, 639 members.
- Source root manifest: `a19590941a53a7c3aa0a343501a7330ea5f89e56f10454ad82603eb4c6d0b69d`.
- Result archive: `39a2441a2eaa4c7403af11225356a98aee2a4477e26acffbc483254befa1ed7f`, 893,323 bytes, 95 members including the collection receipt. All 94 indexed files were verified; none was omitted.
- Final parent launch receipt: `2a882e8333f4bf7edd56b0c4ea56748a1334534372fcb654af8a038d4ca0130f`.
- Offline analysis receipt: `748d74771d7d8e3d3e9bbf0e841033186c72636d30a67da228c22167903af449`.
- Separate post-run AWS receipt: `2f29682f9ce28fdeeb70d17e4388757a36cd0922a78512a4a172328fb18ce387`.

The worker recorded Python 3.12.3, torch 2.11.0+cu128, CUDA 12.8 and NVIDIA RTX PRO 4500 Blackwell Server Edition. Worker wall time was 106.21389676699997 seconds. Source and reservation postchecks passed. All 639 packaged source files matched before and after. No T4 or local neural execution was used.

## Where to audit

All paths below are relative to this research package root:

```text
C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION
```

- `records/aws_child_qualification_v8_001/execution_001/cloud_artifacts.zip`: complete actual cloud evidence, including the failed native database.
- `records/aws_child_qualification_v8_001/registration_001/`: request, existing standing authorization, one-shot capture and exact parent command/raw outputs/exit. **Do not rerun the paid capture or reuse this job.**
- `records/aws_child_qualification_v8_001/execution_001/`: provider preflight, source-bound permit, reservation, ledger snapshot and final cleanup receipt.
- `records/aws_child_qualification_v8_001/analysis_001/`: exact offline replay command, input hashes, packet verification, recomputed counts, saved-output comparisons and final receipt. Analyzer exit 0 means evidence verified, not qualification passed.
- `records/aws_child_qualification_v8_001/provider_check_001/receipt.json`: separate read-only AWS observation after parent exit.
- `records/aws_child_qualification_v8_001/independent_review_001/REVIEW.md`: saved-byte/JSON and frozen-source review, not independent native reproduction.
- `records/child_qualification_v8_001/`: curriculum, source ZIP and pure tests. The local suite passed 362 tests; the five shipped test files passed 179 tests in a fresh extraction. Those pure checks did not predict this native acceptance failure.

The actual offline replay argv is in `analysis_001/command.json`; choose a new `analysis_NNN` destination to replay it. It checks JSON and file bytes only, never opens SQLite, loads tensors, contacts AWS or launches a job.

## Cleanup and budget

Termination was confirmed at `2026-09-06T16:06:40.567693+00:00`. The separate provider read confirmed the owned instance terminated, zero job-tagged volumes, and removal of its security group, two roles, instance profile and shutdown schedule. Uploaded inputs were removed after the result archive was downloaded and verified. Exactly three result objects and their bucket remain under the observed seven-day expiration rule; future deletion is not claimed to have already happened.

The recorded launch-attempt-to-termination interval was 607.135387 seconds at the verified $2.52/hour rate: estimated EC2 cost **$0.4249947709**, or $0.4256 with that interval rounded up to whole seconds. This is not an AWS invoice and excludes storage, IPv4, requests, transfer and tax.

Canonical campaign ledger revision 14 retains the **$4 reservation**, with **$90 reserved and $310 unreserved** within the existing $400 cap. Reservations are not actual spending. No automatic refund, extra job, training run, merge or deployment followed this failure.
