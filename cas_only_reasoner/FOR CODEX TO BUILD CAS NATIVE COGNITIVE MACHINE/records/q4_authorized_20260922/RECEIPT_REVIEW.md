# Q4 run 001: separate-agent review of saved receipts

Recorded at **2026-09-23 00:43:58 UTC**. Reviewer: the current task's
`/root/q4_authorization_review` agent. This agent previously contributed the
conversation-authorization module. This is a separate reading of saved evidence,
**not independent evaluation custody**, model certification, or a new test suite.

The review read existing files only. It did not import Torch, create or reload a
model, rerun inference or training, or change runtime sources. This document is
the only file written for the receipt review. Ad hoc command output was returned
to the conversation; no separate stdout transcript was saved or is claimed here.

## Finding

The engineering job completed. Its learned reconstruction failed on all sixteen
inspected development cases. All sixteen distinct inputs produced the same AST,
rendered as `(^7^E + ^7^C)`, using thirteen decoding steps each. The frozen checker
found **0/16 exact matches**. All sixteen reference expressions have depth 3.

`GENERATED` means a grammar-valid decoder output, not a correct reconstruction.
These observations do not establish operation learning, general CAS reasoning,
or a complete Helm 3.0 result.

| Recorded quantity | Verified value |
| --- | --- |
| Task | `T14_R1_G_ENGINEERING_SMOKE` |
| Optimizer updates | 128 numbered records, exactly 1 through 128 |
| Supervisor elapsed seconds | `75.91282699999283` |
| Supervisor status / return code | `COMPLETE` / `0` |
| Automatic retries | 0 |
| Learned parameters | 70,818 |
| Development predictions / distinct record IDs | 16 / 16 |
| Distinct prediction ASTs | 1 |
| Canonical exact matches | 0 |
| Runtime temperature samples | 30 |
| Maximum sampled temperature | 64 degrees Celsius |
| Checkpoint file bytes | 287045 |
| Worker log bytes | 0 |
| Runtime source files matched | 12 |

The 70,818 parameter count also agrees with arithmetic from the frozen width-64
architecture: a 257-by-64 input embedding, two GRUs, a 35-by-64 output embedding,
and a 64-to-34 output head. No checkpoint tensors were deserialized to establish
this arithmetic. The frozen training loop and seeded index order imply 128
distinct training examples received updates from the 2,048 loaded examples.
The update records do not themselves save selected example IDs; this last count
is a reconstruction from the frozen loop and seed, not a per-example log claim.

## One genuine saved case

```text
Record ID: c12aa3c699ee2af86b148e5e
Task: reconstruct the visible expression's AST
Input: (^6^O_{F2}|E + ((^5^C_{F6}|E + ^1^C) + ^7^O|E))
Original learned output: (^7^E + ^7^C)
Checker canonical exact: false
CAS profile: NOT_ASSIGNED
CAS-Ohm measurement: NOT_AVAILABLE
```

The reference AST is a frozen Q3 development target, separate from the original
learned prediction. No compiler answer or demonstration Ohm value was substituted
for a model output.

## Identity and integrity checks

Source commit: `d4c3fc7643201a83693ea9073c14ab42ecc5a570`.

Canonical execution-plan SHA-256:
`9dacc83627422d704c9db58f5ddbac82936e7d52211ec061247419fbad78095c`.

Checkpoint SHA-256:
`d54f57155a54cbd28621d92af9cb5f45e425c015a559cf80103966ccbf275477`.

The reviewer recomputed the canonical plan digest and checkpoint-byte digest;
checked their agreement with preparation, result, and checkpoint metadata;
matched all twelve runtime source hashes using the recorded LF normalization;
and confirmed those runtime files have no difference against the source commit.
All 128 update records had finite loss and pre-clipping gradient norm values.

The pinned Q3 manifest and both original development files
(`visible_G_dev.jsonl` and `sealed_G_dev.jsonl`) matched their expected hashes.
All sixteen inspected inputs, record IDs, reference ASTs, and checker booleans
matched those original saved records and `run_001/dev_predictions.jsonl`.

Raw-file SHA-256 values observed during review:

| File relative to this document | SHA-256 |
| --- | --- |
| `saved_run_verification.json` | `093c6f900b51f85a733b1b4ba49893516de4ee5d70d723e42d84a4a82bde1357` |
| `inspected_predictions.json` | `8cbbcb6ba3a689ae8beae0fedf98b2fcd3304fa26d21418227a49e786bc76f9a` |
| `run_001/dev_predictions.jsonl` | `0be01e6162abbb57a4632ec9df841b82933963ad89c7d04c2c156c8c36c0e9cb` |
| `run_001/result.json` | `d333d9ee25b7566f37e5be323c446ab8f09b75f6d64cbf4dec55aff4c6b3c57e` |
| `run_001/supervisor.json` | `bd6a7e7bf7bd87b6aef1716935b5184a5ba45506a634f8622df0fcc03fa6db43` |
| `run_001/updates.jsonl` | `6faac5e782610134140dd66b011e5ea1a8cc4f0a3685583f98627dcbbd6dbad9` |

## Review commands and limits

Read-only commands included `Get-Content`, `Get-FileHash -Algorithm SHA256`,
`Get-Item`, and the following Git checks, run from the expression-lab directory:

```powershell
git diff --exit-code d4c3fc7643201a83693ea9073c14ab42ecc5a570 -- learner_q4_decoder.py learner_q4_memory.py learner_q4_neural.py learner_q4_representation.py q3_behaviour_records.py q3_load.py q4_checkpoint.py q4_conversation_authorization.py q4_device_capacity.py q4_runtime_metadata.py q4_smoke_job.py reference_ops.py
git cat-file -t d4c3fc7643201a83693ea9073c14ab42ecc5a570
```

The Git diff was empty and the object type was `commit`. Additional inline
standard-library-only Python checks ran through `C:/Python314/python.exe -B -`.
They read and compared JSON, SHA-256 values, finite numbers, deterministic index
order, and parameter-count arithmetic, then printed findings to the tool output.
They did not call `inspect_saved_run.py` again or create new verification files.

One initial ad hoc comparison failed because that review command used Windows'
default text decoding for the inspection JSON, affecting multiplication signs.
The command was corrected to explicit UTF-8 and passed against all sixteen
original records. This was a review-command decoding error, not a training or
checker failure; no saved run data was changed.

The first and last loss values concern different training examples, so their
difference is not a fixed-set before/after score. Temperature is sampled, not a
continuous peak measurement. No fresh-process neural reload was performed.
Evaluation remains `EVALUATION_NOT_INDEPENDENT` and `NOT_CERTIFIED`. This review
does not promote the engineering completion status into a learning-performance
pass.
