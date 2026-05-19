# Stage 14 Claims Matrix / Evidence Packet

**Status:** `PASS_CLEAN_STAGE14_PYTHIA28B_CPL2_REPLICATES`

**Branch:** `experiment/cas-probe-pythia`

## Executive Summary

Plain English:

> CAS Harness replicated the eta-to-epsilon readable-prefix likelihood bridge on Pythia-2.8B. The harness reads a 28-Foundation label from hidden states, realizes it as readable context, and that readable CAS context shifts Pythia-2.8B's semantic likelihood in the intended direction.

What this proves:

> The readable-prefix CAS Harness bridge transfers across three Pythia scales: 160M, 1B, and 2.8B.

What this does not prove:

> Stage 14 does not prove hidden-neuron steering, raw CAS-symbol understanding, open-ended generation control, or cross-architecture transfer.

## Locked Artifacts

| Artifact | File | SHA-256 / Status |
|---|---|---|
| Pre-registration | `STAGE14_PYTHIA28B_GATES_20260518.md` | committed before run in `ae518ad` |
| Capture script | `capture_stage14_pythia28b_activations.py` | committed before run in `ae518ad` |
| CPL2 script | `probe_stage14_pythia28b_cpl2.py` | committed before run in `ae518ad` |
| Frozen Stage 7 fixture | `stage7_foundation_pilot_20260517.jsonl` | `3e4a1aca9f168a190116578b0b4fdb5bab633232ba06902039b233e589121250` |
| Pythia-2.8B activation binary | `stage14_pythia28b_activations_20260518.npz` | `fc8204bc749ea9932532487f28c7462e491058a2f705e26e9e141427e81901d7`; RunPod artifact, not committed |
| Pythia-2.8B activation manifest | `stage14_pythia28b_activations_manifest_20260518.json` | `35cad3aa63f582f3f66f56ef3498e722bccc5d6eddef85fd7013fd5216c1ae88` |
| Pythia-2.8B probe report | `STAGE14_PYTHIA28B_PROBE_REPORT_20260518.json` | `d1b1d9557f4a3b29786d5856b29cf5e15983e879d2f784367ea0b380d373c1b5` |
| Pythia-2.8B CPL2 report | `STAGE14_PYTHIA28B_CPL2_REPORT_20260518.json` | `3c7ec0fa7effc077f943e495f85eceea5e7aaba069e359d6cf1add340c387123` |
| Summary | `STAGE14_PYTHIA28B_SUMMARY_20260518.md` | committed |

## Pre-Registered Gate Result

| Gate | Floor | Actual | Status |
|---|---:|---:|---|
| Probe-readable delta vs no-prefix | `> +0.15` | `+0.5832` | PASS |
| Paired Wilcoxon p | `< 0.05` | `3.08e-15` | PASS |
| Probe-readable minus partner-readable margin | `> +0.30` | `+1.3363` | PASS |
| Positive cases | `> 60/112` | `92/112` | PASS |

Verdict: `PASS_CLEAN_STAGE14_PYTHIA28B_CPL2_REPLICATES`.

## Layer Selection

| Model | Candidate layers | Selected layer | Val acc | Test acc | Test lacunarity |
|---|---:|---:|---:|---:|---:|
| Pythia-2.8B | `12-27` | `14` | `1.0000` | `0.8588` | `0.0059` |

Layer choice was made by validation accuracy and lacunarity before test reporting. Later candidate layers had slightly higher test accuracy, but they were not selected post-hoc.

## Scale Comparison

| Model | Probe-readable delta | Probe-readable minus partner | Positive cases | CPL2 status |
|---|---:|---:|---:|---|
| Pythia-160M | `+0.2828` | `+0.6829` | `81/112` | pass |
| Pythia-1B | `+0.5542` | `+1.2460` | `90/112` | pass-clean |
| Pythia-2.8B | `+0.5832` | `+1.3363` | `92/112` | pass-clean |

## Claim Matrix

| Claim | Status | Evidence Supporting It | Boundary |
|---|---|---|---|
| Pythia-2.8B carries a 28-Foundation hidden-state readout. | Supported | Validation-selected layer 14, test acc `0.8588`, lacunarity `0.0059`. | Synthetic role-bound fixture, not natural web benchmark. |
| The eta-to-epsilon readable-prefix bridge transfers to Pythia-2.8B. | Supported | CPL2 passes all four pre-registered gates. | Likelihood-space result, not open-ended text-control proof. |
| The bridge strengthens from 160M to 1B and remains strong at 2.8B. | Supported | Delta rises from `+0.2828` to `+0.5542` to `+0.5832`. | Only within Pythia family so far. |
| Raw CAS symbols condition Pythia-2.8B. | Not supported | `probe_raw` delta `+0.0027`, near zero; sign p `0.7457`. | Use readable realization, not raw-symbol claim. |
| CAS directly steers Pythia-2.8B neurons. | Not supported | Stage 14 used readable prefix conditioning, not hidden-state intervention. | Do not claim hidden-neuron control. |
| CAS Harness has cross-architecture validation. | Not yet tested | Pythia family only. | Next gate should be OLMo, Llama, or Qwen. |

## Stakeholder-Safe Language

Use:

> "CAS Harness replicated its read-realize-condition loop across three open Pythia model sizes. The same bounded CAS Foundation signal can be read from hidden activations and realized as readable context that shifts semantic likelihood in the intended direction."

Do not use:

> "CAS controls Pythia's neurons."

Do not use:

> "Pythia understands raw CAS notation."

Do not use:

> "CAS has solved open-ended generation steering."

## Bottom Line

Stage 14 is the strongest scale result so far. Pythia-2.8B passes the same pre-registered CPL2 likelihood bridge gate that Pythia-1B passed, with a slightly larger measured effect. The next clean gate is cross-architecture replication.
