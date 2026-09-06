# Saved-byte and JSON review of the refused qualification

This is a read-only review of the saved packet and its frozen source, not an independent native reproduction. No SQLite database was opened, no tensor was deserialized, and no neural, GPU or provider call was made. Raw database members were read only as opaque bytes for the packet's hash checks. Only this review record was added.

## Result

The fifth attempted full execution, `case_00/candidate_03` (`R_CR`), stopped with:

```text
MetaRuntimeError: NATIVE_RESULT_NOT_RETURNABLE
```

The saved text establishes the refusal boundary but does **not** identify the failing CJT, its tick, decoded symbol, verifier reason codes, published-effect count, or number of additional committed ticks in this failed execution. These remain unknown in this review.

Do not classify this as a proved expected-label mismatch, an effect-scope failure, or a failure specifically at the last R. Do not report all 20 executions / 110 ticks as completed.

## Identity and byte checks

- Job: `cas-meta2-20260906155525-195f5ad8`.
- Parent and worker source: `b61b011c3d53ae49a1f7f988397df632e95e82a6`.
- [Downloaded archive](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/aws_child_qualification_v8_001/execution_001/cloud_artifacts.zip>): 893323 bytes.
- Archive SHA-256: `39a2441a2eaa4c7403af11225356a98aee2a4477e26acffbc483254befa1ed7f`; matched the saved launch result.
- ZIP path, duplicate/case-fold collision, special-file and bounded expanded-size checks passed.
- All 94 files indexed by `artifact_collection_receipt.json` matched their saved byte sizes and SHA-256 values.
- All 60 entries in `qualification/worker_receipt.json.files_sha256` matched.
- Collection receipt reports `partial_evidence=false`, `omitted_full_file_count=0`, `returncode=1`. This means the configured collection was complete; it does not mean the qualification completed or that missing per-tick JSON exists.
- Frozen source ZIP SHA-256: `d93a39f3a264c23f27ac7dcdd2779eca665150a6bd739820651e953958e8f7d3`.
- Frozen source manifest SHA-256: `a19590941a53a7c3aa0a343501a7330ea5f89e56f10454ad82603eb4c6d0b69d`.

The four local source files used for the causal boundary below were compared byte-for-byte with their copies in that source ZIP:

| Frozen source member | SHA-256 |
| --- | --- |
| research/CASFORMER_v0_3_META_LOGIC_WIP/cas_meta/executor.py | 4570dec76d8f204c7fccb3d54a71b917b160da072322acb609fc8730ce4fa9df |
| research/CAS_CJT_TRANSFORMER_v0_2/cas_cjt/runtime.py | 5eda27339d0d216d5359116617c6dc8c9f99c376d6cfa6be386845b59ec00187 |
| research/CAS_CJT_TRANSFORMER_v0_2/cas_cjt/verifier.py | c1604059580a553e131233ecdbb5b1de8439edbba03865f7985a71b0dfdfb736 |
| research/CAS_META_2_COMPOSITION/cas_meta2/native.py | 16131d98dcbd76d274a1c083e9bc5f100cadfbbba7dfcdb38282c23946c20512 |

## First failure boundary supported by the source

The candidate route invokes the unchanged single-RUN META-0 wrapper at [native.py:216](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/cas_meta2/native.py:216>). Its direct-reference alternative raises `CompositionError`, not the recorded `MetaRuntimeError`.

The exact recorded exception is raised by [META-0 executor.py:349](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CASFORMER_v0_3_META_LOGIC_WIP/cas_meta/executor.py:349>). In that source path:

1. The native `inference_tick` has returned.
2. Its plan, model identity and cross-CJT bias checks have passed.
3. The executor has recorded an in-memory NATIVE event.
4. It cannot use either the normal accepted result with exactly one published effect or the configured repair continuation.

This candidate wrapper supplies no repair branch. The result therefore failed the normal returnable-result condition. The saved failure alone does not expose which part of that condition failed. The explicit CJT-scope guard is a different earlier error, `CJT_SCOPE_DENIED`, at [executor.py:300](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CASFORMER_v0_3_META_LOGIC_WIP/cas_meta/executor.py:300>); the observed exception is not that guard. This does not rule out every lower-level binding or verification cause.

The native tick source commits before returning its result at [runtime.py:1363](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_CJT_TRANSFORMER_v0_2/cas_cjt/runtime.py:1363>). This explains why a refusal can leave durable state; it is not an independently observed count of the failed arm's commits.

The verifier can refuse for distinct causes, including binding failures, zero flow, breakdown, or semantic mismatch. See [verifier.py:286](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_CJT_TRANSFORMER_v0_2/cas_cjt/verifier.py:286>) and [verifier.py:324](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_CJT_TRANSFORMER_v0_2/cas_cjt/verifier.py:324>). The failed arm's verifier receipt was not exported as JSON, so these source alternatives cannot be resolved from the reviewed text.

## What was retained for the failed execution

The packet has exactly these failed-arm members:

```text
qualification/cases/case_00/candidate_03/failure.json
qualification/cases/case_00/candidate_03/native.db
```

The failure JSON is:

```json
{"message":"NATIVE_RESULT_NOT_RETURNABLE","status":"INFRASTRUCTURE_FAILURE","type":"MetaRuntimeError"}
```

There is no failed-arm `native_traces.json`, `native_kernel_events.json`, `composition_events.json` or `result.json`. The adapter exports those records only after the complete run succeeds; its exception path writes the generic failure record. See [native.py:334](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/cas_meta2/native.py:334>) and [native.py:346](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/cas_meta2/native.py:346>). Thus absent JSON does not prove that zero native steps ran. Database size is not a tick counter.

The sealed R_CR action is the ordinary prelude A(arg), B(A), C(B), R(C), followed by a child C(R), R(child C), then return. Its action SHA-256 is `d4edc10c4d14a25b812faec93acaf5224992225237c84f527acdaab00ae74f84`; its planned count is six ticks. Those are the planned operations, not an observed failed-arm execution trace.

## Successful controls and count boundary

For case_00, the saved B_CR control completed six native ticks and the R_C control completed five. Both passed their stored call-tree audits. Both were correctly marked wrong for the case_00 requested B_C task, with binding correct and task/procedure/dependency/output correctness false.

Their first four saved native input/output identities agree. B_CR then ran C from the earlier B result followed by R; R_C ran C from the earlier R result. These controls show those separate executions were usable. They do not show which step failed in the separately initialized R_CR execution.

The qualification receipt records:

| Measure | Observed |
| --- | ---: |
| Scheduled full executions | 20 |
| Attempted full executions | 5 |
| Reported and audited completed full executions | 4 |
| Audited native ticks in those completed executions | 21 |
| Unattempted full executions | 15 |
| Additional partial native ticks in the failed execution | Unknown |
| Fully completed native-tick total | Not reported; null |
| Worker wall time | 106.21389676699997 seconds |

No training ran. The native qualification gate remains refused. A claim about the exact failed tick, decoded symbol or verifier reason needs additional retained-state examination with explicit read-only safeguards; this review did not perform it.

