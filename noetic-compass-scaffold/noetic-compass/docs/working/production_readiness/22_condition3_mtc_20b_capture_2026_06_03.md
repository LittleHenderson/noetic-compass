# Condition-3 MTC 20B Capture Evidence - 2026-06-03

**Status: VERIFIED for claim-neutral capture.** The GPT-NeoX-20B
Condition-3 activation dataset was captured on the replacement H200 pod and
archived locally. The matched-taxonomy comparator was **not** run in this step.

This is data collection only. It does not decide `PASS`, `GREY`, `FALSIFY`, or
`BLOCKED`, and it does not change the Pythia-160M packet verdict.

## Pod

```text
root@212.247.220.166 -p 18611
host: MSI
GPU: 8x NVIDIA H200, 143771 MiB each
workspace: /workspace
```

Runtime:

```text
torch 2.4.1+cu124
transformers 4.44.2
accelerate 0.34.2
numpy 1.26.3
```

The pod initially had `transformers 5.10.1`, which failed before capture because
it expected `torch.float8_e8m0fnu`, a type not present in Torch 2.4.1. The
environment was corrected to `transformers 4.44.2` / `accelerate 0.34.2`, and
the same capture then completed.

## Fixture

Input fixture on pod:

```text
/workspace/mtc_condition3_capture_ready_20260603.json
```

The original adapted fixture was JSONL. It was converted into one JSON list
because `probe_dataset_common.load_labeled_scenarios()` expects one JSON
document. Each row's `sample_id` was preserved as `scenario_id`.

Validation before capture:

```text
rows: 1440
elements: 40
per-element balance: 36 each
splits: train 720, test 720
axes loaded: domain, element, operator, register
```

## Capture Command

```text
HF_HOME=/workspace/hf-cache python scripts/capture_open_weight_probe_dataset.py --model-id EleutherAI/gpt-neox-20b --scenario-path /workspace/mtc_condition3_capture_ready_20260603.json --output /workspace/condition3_gptneox20b_activations.npz --metadata-output /workspace/condition3_gptneox20b_metadata.json --torch-dtype float16 --device-map auto
```

The model was loaded from the pod cache after all 46 safetensor shards were
present. The capture log reached `1440/1440` and wrote both output files.

## Output

Pod outputs:

```text
/workspace/condition3_gptneox20b_activations.npz
/workspace/condition3_gptneox20b_metadata.json
/workspace/condition3_capture_20260603.log
/workspace/PROVENANCE_condition3_mtc_capture_20260603.txt
```

Local archive:

```text
D:\tksCAS-archive\condition3_mtc_capture_20260603
```

Archived files:

```text
condition3_gptneox20b_activations.npz          720117672 bytes
condition3_gptneox20b_metadata.json                 2323 bytes
mtc_condition3_capture_ready_20260603.json       1450810 bytes
mtc_condition3_capture_ready_20260603.jsonl      1039472 bytes
condition3_capture_20260603.log                   176307 bytes
PROVENANCE_condition3_mtc_capture_20260603.txt      1989 bytes
```

## Hashes

```text
condition3_gptneox20b_activations.npz
SHA256 8A98216CD1D4DC5168FE56F46B22B46FF59FDF534FACE17B86ACF1AEC33987F1

condition3_gptneox20b_metadata.json
SHA256 5CF8E3662A2C90C549A4D9098A92502FEA8383A4EE5957461E88080D0E8AA445

mtc_condition3_capture_ready_20260603.json
SHA256 208DA7FCD5A6F11B19D5F517CCD414114BC6EC0A90B9722C6054C5DA16823986

mtc_condition3_capture_ready_20260603.jsonl
SHA256 9705FEB32ADA3D3666FF8384CDE1F09B850E6C142CC6039A8EE7DD440C1478FD

condition3_capture_20260603.log
SHA256 4A8929F2B37F8E62B4BC65E93E6C4335F0C6AA35775E76D286F6452DE2D560C4
```

Local archive hashes matched the pod provenance hashes.

## What This Proves

- GPT-NeoX-20B activation capture for the Condition-3 MTC fixture completed.
- The output dataset and metadata were copied off the pod and hash-verified.
- The capture can now feed the matched-taxonomy comparator once the prereg
  amendment is approved and frozen.

## What This Does Not Prove

- This is not a matched-taxonomy `PASS`.
- This is not a matched-taxonomy `FALSIFY`.
- This is not a Pythia-160M `ACCEPT`.
- This does not replace the WORM-retained Pythia verdict:
  `FLAG_FOR_HUMAN_REVIEW`.
- The comparator remains gated on the A1 prereg amendment being founder-approved
  and frozen before scoring.
