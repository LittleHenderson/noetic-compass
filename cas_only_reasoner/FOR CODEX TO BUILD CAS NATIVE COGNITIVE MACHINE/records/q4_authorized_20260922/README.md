# Actual first authorized Q4 learning run

The run completed, but reconstruction accuracy was **0/16**. All sixteen
outputs were syntactically valid and identical. This is an engineering smoke
with a negative accuracy result, not the complete Helm 3.0 result.

The user's actual current authorization is preserved in
`conversation_authorization.json` and `../../docs/OWNER_RUN_AUTHORIZATION_20260922.md`.
It is a conversation transcription, not a fabricated owner signature or key.
Future ordinary AI/LLM research runs have standing user authorization; each job
still needs an explicit task, resource scope, limits, source identity and receipts.

## Exact job and result

| Item | Actual value |
| --- | --- |
| Task | T14_R1_G_ENGINEERING_SMOKE; reconstruct visible expression into its AST |
| Architecture | R1 width-64 GRU encoder/decoder; 70,818 learned parameters |
| Data | Q3 v0.7; family G; train and development only |
| Training | Seed 20260921; pool of 2,048 rows; 128 single-example optimizer updates |
| Development | First 16 saved dev records, all depth 3; not a representative full benchmark |
| Result | 16 GENERATED; 0 canonical-exact; one unique predicted tree |
| Time | 75.91282699999283 seconds; cap 1,800 seconds |
| Device | RTX 4070 Laptop GPU, cuda:0; GPU-7cfee18b-e83d-b6fb-a946-ae444b329fdd |
| Runtime | Python 3.14.0, Torch 2.11.0+cu128, CUDA 12.8 |
| Recorded resource use | Peak Torch allocation 78,352,896 bytes; maximum sampled temperature 64 C |
| Failures/retries | No runtime exception; 16 wrong reconstructions; zero automatic retries |

First/last logged training losses were 3.5241360664367676 and
1.600077748298645. These use different examples and do not measure fixed-set
improvement. No eval split, cloud, paid API, CPU neural fallback or resume was used.

## Genuine saved prediction

Record `c12aa3c699ee2af86b148e5e` asked the model to reconstruct:

```text
(^6^O_{F2}|E + ((^5^C_{F6}|E + ^1^C) + ^7^O|E))
```

Its original saved prediction is a PLUS tree with left state `^7^E` and right
state `^7^C`, both with null drive: displayed as `(^7^E + ^7^C)`.
The exact raw AST remains in `run_001/dev_predictions.jsonl`. The checker
compares it with the frozen reference AST and returns false. All sixteen
original predictions were this same tree. No correct example exists in this run.

`inspected_predictions.json` joins every original input, unchanged learned
prediction, checkpoint identity and separately labelled reference/checker result.
CAS profile stays NOT_ASSIGNED and CAS-Ohm stays NOT_AVAILABLE. No internal
thought sequence, demo measurement or compiler answer was invented.

## Identity and preserved checkpoint

- Preserved reconciliation: `5f7111d5204e872c18df717badc2e2021f31ad70`; its original worktree remains unchanged.
- Executed source: `d4c3fc7643201a83693ea9073c14ab42ecc5a570` on `codex/q4-authorized-20260922`.
- New canonical plan: `9dacc83627422d704c9db58f5ddbac82936e7d52211ec061247419fbad78095c`.
- Weights: `d54f57155a54cbd28621d92af9cb5f45e425c015a559cf80103966ccbf275477`.
- Previous prepared plan `a3f5a8b30ac80ee820a85e301802effd77552da2e5fb3b1fb71e96d4a3496863` remains preserved; it was not executed unchanged.

Only worktree/data-output paths, runtime source bindings and device policy changed
in the plan. The model implementation, training loop, data identity, seed, width,
learning rate, work limits and number of dev examples remained the same.
The launcher now supports actual conversation permission alongside its unchanged
signed-approval mode. It explicitly admits measured shared WDDM display capacity;
the original guard treated all C+G desktop contexts as blocking. No process was
mislabelled graphics-only or terminated to free the GPU.

The shared policy requires three <=10% load samples, >=4,096 MiB free and <=75 C
at admission. A monitor checks device identity/temperature every two seconds plus
query latency, stopping the owned worker at >=80 C, unavailable telemetry or the
wall limit. It reserves the query timeout near the deadline and can stop early.
These are conservative operational choices, not manufacturer limits.

## Tests, checks and evidence limits

Final deterministic verification: **251 cases / 87 functions**, all passing.
This consists of **144 new cases / 36 new functions** and **107 existing cases /
51 existing functions**. All six selected files loaded. A tracked filename census
lists 1,051 other test files as unselected; this does not claim they are one runnable
suite or that the entire repository was tested. `TEST_SCOPE.json` retains the list.

`tests/combined_001` retains the earlier 249-pass run. Independent review found a
deadline edge, repaired before launch; two new tests cover it in `combined_002`.
The initial single-module receipts overlap the final selection and are not added
again. No failed test run was erased. The model's 16 failed reconstruction checks
are separate from passing software tests.

Executed final test command from this CNCM directory:

```powershell
& 'C:\Python314\python.exe' -B records/q4_authorized_20260922/run_checks.py combined_002
```

The exact expanded pytest command and environment are retained in the receipt.
`execute_once.ps1` is the exact single-use launch command; it refuses a second
launch log. `inspect_saved_run.py` rechecked update continuity, finite losses,
checkpoint bytes, source/plan identity and all sixteen saved comparisons without
importing Torch or making another learned prediction. This is a deterministic
checker replay, not independent semantic reimplementation or neural reload.

`ACCEPTANCE_MANIFEST.json` gives every evidence artifact's path, size and SHA-256;
`.gitattributes` preserves raw receipt bytes. Source files also record LF-normalized
hashes so Git line-ending conversion does not invalidate source identity.
The original shared module inventory
is retained, with the twelve executed runtime modules indexed in
`../../docs/CAS_SHARED_MODULE_INVENTORY_Q4_20260922.json`. The shared arithmetic
core stays an unselected proposal.

Remaining limits: operation learning, trained R2, benefit testing, fresh-process
neural reload and independent final evaluation are unperformed. No certification
or Helm release was produced. Diagnose the identical-output behavior before
interpreting a later, longer experiment as evidence of learning.

Next safe command, from this CNCM directory, verifies the saved bundle only:

```powershell
& 'C:\Python314\python.exe' -B records/q4_authorized_20260922/verify_bundle.py
```
