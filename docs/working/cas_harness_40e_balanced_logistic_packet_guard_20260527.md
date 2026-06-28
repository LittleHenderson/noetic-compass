# CAS Harness 40E Balanced-Logistic Packet Guard - 2026-05-27

## Purpose

This note records the backend/script slice added for the 40-Element Evidence
Packet path. It does not claim a new 40E closure run. It makes the existing
`evaluate_40_element_probe.py` path stricter and more reproducible.

## Method Contract

The 40E readout now uses the original closure readout family:

- `StandardScaler`
- `LogisticRegression(class_weight="balanced", solver="lbfgs")`
- group-aware train/test split by stripped base prompt
- shuffled-label, majority, and text-hash controls

This matches the original closure methodology's Stage 7-equivalent requirement:
balanced logistic regression after scaling, not nearest-centroid readout.

## Packet Readiness Guard

The evaluator now emits a machine-readable `readiness_gate` and an `artifacts`
list with SHA-256 hashes and byte counts for:

- the activation dataset `.npz`
- the capture metadata `.json`

For a packet-ready 40E run, the dataset must contain:

- `features` shaped `[N_scenarios, N_layers, hidden_dim]`
- `layers`
- `labels_operator`
- `labels_domain`
- `prompts`
- every canonical `^0..^9 x P/C/E/O` cell populated
- at least `--min-samples-per-cell` rows per cell, default `10`

Use `--require-balanced-40e` when the output is intended for Evidence Packet
assembly. If any cell is missing, sparse, or outside the canonical grid, the
script exits before probe training, writes a guard report, and sets:

`status = "blocked_missing_balanced_40e_artifact"`

## Artifact Status

No packet-ready full 40E activation artifact is committed under the owned repo
paths. The existing run status doc points to external/local copies:

- RunPod dataset:
  `/workspace/cas-harness-large-eval/datasets/gpt_neox_20b_augmented_400_layers_0_43.npz`
- RunPod metadata:
  `/workspace/cas-harness-large-eval/datasets/gpt_neox_20b_augmented_400_layers_0_43.metadata.json`
- Local copies noted in the status doc:
  `C:\tmp\gpt_neox_20b_augmented_400_layers_0_43.npz`
  `C:\tmp\gpt_neox_20b_augmented_400_layers_0_43.metadata.json`

To supply the artifact for a formal run, copy or mount the balanced 40E `.npz`
and metadata JSON, then run:

```powershell
python noetic-compass-scaffold\noetic-compass\live-trace-worker\scripts\evaluate_40_element_probe.py `
  --dataset PATH\to\gpt_neox_20b_augmented_400_layers_0_43.npz `
  --metadata PATH\to\gpt_neox_20b_augmented_400_layers_0_43.metadata.json `
  --output PATH\to\gpt_neox_20b_40_element_probe_eval_report.json `
  --require-balanced-40e
```

If the source artifact is only the older diagnostic 400-row capture, the guard
will still document whether it is balanced enough for the configured threshold.
Do not promote a diagnostic report to closure or Evidence Packet status unless
the guard says `packet_ready`.
