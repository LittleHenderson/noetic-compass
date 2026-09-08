# Teaching inputs and the unchanged native child-A boundary

Source-only review at HEAD `46b6ab303ad260ddac12df65f916bf3d3d5da9c6`. No model, tensor, NumPy, SQLite or AWS execution was performed. No source, accepted weights, live job, scoring inputs, reservation or budget was changed. This file is the sole new review record.

## Finding

The teaching vectors meet the native adapter's numeric shape and amplitude checks. This does **not** establish that the unchanged child A will accept them. No current teaching vector has been shown to fail by this review.

`cas_meta2/teaching_cycle/data.py:47` constructs each eight-number row as `rng.randint(-8192, 8192) / 8192.0`, within `[-1,1]`. A read-only JSON count/min/max check of the exact training and development files found:

| File under `records/teaching_cycle_001/material_001/teaching/` | Cases | Numeric values | Observed minimum | Observed maximum | Raw SHA256 |
| --- | ---: | ---: | ---: | ---: | --- |
| `train.json` | 256 | 6144 | -0.9981689453125 | 0.9998779296875 | `e51015ba0ee3ac05ed8526f51a468d48641d5df4f0c33c3a96f989d04ebb54c5` |
| `development.json` | 64 | 1536 | -0.9998779296875 | 0.9993896484375 | `f12851d848f10b69abc8db73b380ec002972ba2dbc651acb2e08924fb34efd16` |

The adapter rejects absolute values above 2 (`native.py:50`), reshapes the selected row to `[1,2,4]` (`:155`), and always supplies the authored expectation **A -> L1** (`:26`, `:195`, `:210`). The teaching binding target says which observation to select; it does not prove that observation produces L1.

The unchanged decoder averages logits and takes argmax (`cas_cjt/semantic.py:65-79`), using fixture labels L0/L1/L2/L3. It is not a constant-L1 decoder. A normal non-L1 decoded symbol fails the authored expectation and receives `REPAIR / SEMANTIC_OFF_AXIS` (`verifier.py:324-339`). The frozen topology has A->B, B->C, C->R and R->C (`cas_meta/fixture.py:23-27`), with no return edge to A. Repair requires a distinct permitted round trip (`runtime.py:549-577`). Thus, **if** A reaches the semantic-repair branch, it has no eligible repair child and raises `repair cannot open without a durable distinct ^6 round trip` (`runtime.py:942-944`). Other nonacceptance outcomes are also possible; none is measured here for the current inputs.

## Exact source identities

All paths below are relative to the `research` directory at:

```text
C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research
```

| Source | SHA256 |
| --- | --- |
| `CAS_META_2_COMPOSITION/cas_meta2/teaching_cycle/data.py` | `8ae27c6cbe93e1def78b5516493eaff6c5b17cf6a4b0929d8031dece8ae5f1d6` |
| `CAS_META_2_COMPOSITION/cas_meta2/native.py` | `16131d98dcbd76d274a1c083e9bc5f100cadfbbba7dfcdb38282c23946c20512` |
| `CASFORMER_v0_3_META_LOGIC_WIP/cas_meta/fixture.py` | `0038db2ed122e7d1ccb312771e0ea14388ee8564d3ffaa9a9f6c7316c6eb1735` |
| `CAS_CJT_TRANSFORMER_v0_2/cas_cjt/runtime.py` | `5eda27339d0d216d5359116617c6dc8c9f99c376d6cfa6be386845b59ec00187` |
| `CAS_CJT_TRANSFORMER_v0_2/cas_cjt/semantic.py` | `826de6ff11dde52e3b7796e53aee8cca26519366ab14b4490bdf7ecfd75832bf` |
| `CAS_CJT_TRANSFORMER_v0_2/cas_cjt/verifier.py` | `c1604059580a553e131233ecdbb5b1de8439edbba03865f7985a71b0dfdfb736` |
| `CAS_META_2_COMPOSITION/cas_meta2/child_curriculum_v8.py` | `dc764d36754599b627c14a19876fdd57a30ca781e178f50e29e7ed232ba79c7d` |
| `CAS_META_2_COMPOSITION/cas_meta2/child_qualification_gpu_v8.py` | `e6a27ffe5b3d38158be0564011f6e8197d68cf48e537138fb4277945b2af4175` |

## Reuse the old evidence; do not repeat the old diagnostic

The existing v8 qualification worker hard-calls `qualification_tasks()` at `child_qualification_gpu_v8.py:183`. Those four requests share one fresh context and binding 0 (`child_curriculum_v8.py:246-254`); its rows use coordinate `base/10 +/- 0.0004` (`:233`), not the teaching pilot's broad range. Its CLI has no replacement-input option (`child_qualification_gpu_v8.py:220-232`). The package and remote launcher pin this same fixed experiment.

The prior job `cas-meta2-20260906155525-195f5ad8`, source `b61b011c3d53ae49a1f7f988397df632e95e82a6`, already produced a verified qualification refusal. Its saved analysis records five attempts, four completed executions and 21 ticks in those completed records. The later saved-database export identifies the failed attempt's sixth tick: **R decoded L0 against L1**, while A at tick 1 accepted L1. This is useful evidence about that old input and longer program, not evidence for or against current teaching A inputs. It does not reopen accepted core, META-0 or META-1 audits.

Relevant existing records under `CAS_META_2_COMPOSITION/`:

- `records/aws_child_qualification_v8_001/analysis_001/receipt.json`, SHA256 `748d74771d7d8e3d3e9bbf0e841033186c72636d30a67da228c22167903af449`, binds the original result ZIP `39a2441a2eaa4c7403af11225356a98aee2a4477e26acffbc483254befa1ed7f`.
- `records/aws_native_failure_inspection_v8_001/analysis_001/REPORT.md`, SHA256 `67c9617f85f2de75483aa5817ad75797b448117169df895bc4c9890a67d9611c`, and its `command_receipt.json` bind the saved export ZIP `fe2a65efe0dc9119ffdc29cf5931e5e6b550774471747e4634dd53ce510862b3`.

These are inspected saved receipts, not a new independent native reproduction. Re-running the old paid entrypoint would repeat a different, already diagnosed experiment and still would not qualify the current vectors.

## Smallest separate qualification still needed

Native execution on the current teaching inputs remains **UNEXECUTED**. No examined existing CLI directly accepts this teaching train/development format for the fixed-A check; `native.execute_task` (`native.py:361`) is the reusable execution API, not a CLI.

A separate, source-pinned thin driver can map a predeclared development-only panel into the existing public/action format and execute one unchanged RUN(A) per chosen observation, using fresh native state with no active outer caller. Keep the existing L1 expectation, decoder, verifier, topology and accepted weights. Retain actual input bytes, outcome or failure, source/model identities, traces and artifacts; report failures as input/native qualification results, not selector mistakes. Do not select examples based on whether they pass. A small panel only screens those exact rows: full coverage means all 320 train/development target rows, or all 960 observation rows if claiming coverage of every possible binding choice. It cannot prove acceptance for the whole continuous interval `[-1,1]`.

This needs a separately complete native dependency package and bounded AWS execution after registration, not a change to the current teaching job. No final targets, new labels, weakened expectations, weight updates, retry, spending or launch is proposed or performed by this record.

## Search-scope limitation

This review is **not a blinded evaluation**. An initial search was too broad and was stopped before searches were narrowed to exact source files, old v8 records, and the two teaching input files. The exact command, run from `research/CAS_META_2_COMPOSITION`, was:

```powershell
rg -n 'qualification|SEMANTIC_OFF_AXIS|round trip|INPUT_DOMAIN|input.domain|child.A|native.*range' records/teaching_cycle_001 records/child* records/condition_skill_v9_001 tools aws -g '*.json' -g '*.md' -g '*.py' -g '*.txt'
```

`records/child*` produced a Windows path error, but other roots were searched. Tool output was heavily truncated. Visible returned paths included the confirmed synthetic test-output files `records/teaching_cycle_001/transport_smoke_003/pytest_tmp/test_provider_failure_records_6/ledger.json` and `records/teaching_cycle_001/transport_smoke_003/pytest_tmp/test_provider_failure_records_6/ledger.json.history/00000018.json`, plus `records/teaching_cycle_001/bundle_001/extracted/cas_meta2/features_v2.py`. The truncated result also displayed fixture text whose originating path was not retained in the visible excerpt. Exact coverage of actual `evaluation_private` files traversed or read by this command is **unknown**; this review does not claim private targets were unopened. No target values from that search are included or used in this finding. No insight from final targets may guide current or future candidate choices or training. The current AWS worker and frozen scoring inputs remain unchanged. The broad search was not repeated.
