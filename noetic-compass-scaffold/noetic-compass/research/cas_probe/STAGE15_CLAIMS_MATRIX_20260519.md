# Stage 15 Claims Matrix / Evidence Packet

**Status:** `PASS_CLEAN_STAGE15_OLMO1B_CPL2_REPLICATES`

**Branch:** `experiment/cas-probe-pythia`

## Executive Summary

Plain English:

> CAS Harness replicated the read-realize-condition loop on OLMo-1B, a different model family from Pythia. The harness reads a 28-Foundation label from hidden activations, realizes that label as readable context, and the readable context shifts OLMo-1B's semantic likelihood in the intended direction.

What this proves:

> The eta-to-epsilon readable-prefix bridge is no longer only a Pythia-family result. It has now passed on Pythia-160M, Pythia-1B, Pythia-2.8B, and OLMo-1B.

What this does not prove:

> Stage 15 does not prove hidden-neuron steering, raw CAS-symbol understanding, open-ended generation control, or universal transfer to every model family.

## Locked Artifacts

| Artifact | File | SHA-256 / Status |
|---|---|---|
| Pre-registration | `STAGE15_OLMO1B_GATES_20260519.md` | committed before run in `502b293` |
| Capture script | `capture_stage15_olmo1b_activations.py` | committed before run in `502b293` |
| CPL2 script | `probe_stage15_olmo1b_cpl2.py` | committed before run in `502b293` |
| Frozen Stage 7 fixture | `stage7_foundation_pilot_20260517.jsonl` | `3e4a1aca9f168a190116578b0b4fdb5bab633232ba06902039b233e589121250` |
| OLMo-1B activation binary | `stage15_olmo1b_activations_20260519.npz` | `b2fbf6661c4b3b9067bdc74edb27c587cee498bc9b6717ee4f74682d07a47e8b`; RunPod artifact, not committed |
| OLMo-1B activation manifest | `stage15_olmo1b_activations_manifest_20260519.json` | `6a18789784cb0d26c020ffb8efb7a598e26093addc000ed514d8610596e1cb86` |
| OLMo-1B probe report | `STAGE15_OLMO1B_PROBE_REPORT_20260519.json` | `e2fae94962100871b591b20066fba552212161fe3e8d08513206b0ba26024fe2` |
| OLMo-1B CPL2 report | `STAGE15_OLMO1B_CPL2_REPORT_20260519.json` | `7d898af8048aa0cf14158df2d5561378d7ec43b80c06f0196663604eb9ecb07d` |
| Summary | `STAGE15_OLMO1B_SUMMARY_20260519.md` | committed |

## Pre-Registered Gate Result

| Gate | Floor | Actual | Status |
|---|---:|---:|---|
| Probe-readable delta vs no-prefix | `> +0.15` | `+0.6037` | PASS |
| Paired Wilcoxon p | `< 0.05` | `3.17e-12` | PASS |
| Probe-readable minus partner-readable margin | `> +0.30` | `+1.3047` | PASS |
| Positive cases | `> 60/112` | `87/112` | PASS |

Verdict: `PASS_CLEAN_STAGE15_OLMO1B_CPL2_REPLICATES`.

## Layer Selection

| Model | Candidate layers | Selected layer | Val acc | Test acc | Test lacunarity |
|---|---:|---:|---:|---:|---:|
| OLMo-1B | `6-16` | `16` | `0.9911` | `0.9060` | `0.0038` |

Layer choice was made by validation accuracy before test reporting.

## Cross-Model Comparison

| Model | Delta vs none | Margin over partner | Positive cases | CPL2 status |
|---|---:|---:|---:|---|
| Pythia-160M | `+0.2828` | `+0.6829` | `81/112` | pass |
| Pythia-1B | `+0.5542` | `+1.2460` | `90/112` | pass-clean |
| Pythia-2.8B | `+0.5832` | `+1.3363` | `92/112` | pass-clean |
| OLMo-1B | `+0.6037` | `+1.3047` | `87/112` | pass-clean |

## Claim Matrix

| Claim | Status | Evidence Supporting It | Boundary |
|---|---|---|---|
| OLMo-1B carries a 28-Foundation hidden-state readout. | Supported | Validation-selected layer 16, test acc `0.9060`, lacunarity `0.0038`. | Synthetic role-bound fixture, not natural web benchmark. |
| The eta-to-epsilon readable-prefix bridge transfers to OLMo-1B. | Supported | CPL2 passes all four pre-registered gates. | Likelihood-space result, not open-ended text-control proof. |
| CAS Harness now has cross-architecture evidence. | Supported | Pythia-family plus OLMo-1B pass-clean. | Still only two architecture families. |
| Raw CAS symbols condition OLMo-1B. | Not supported | `probe_raw` delta `+0.0063`, near zero; sign p `0.2543`. | Use readable realization, not raw-symbol claim. |
| CAS directly steers OLMo-1B neurons. | Not supported | Stage 15 used readable prefix conditioning, not hidden-state intervention. | Do not claim hidden-neuron control. |
| CAS has universal model coverage. | Not established | Only Pythia and OLMo tested. | Next gates should test Qwen/Llama-family. |

## Stakeholder-Safe Language

Use:

> "CAS Harness has replicated its read-realize-condition loop across Pythia and OLMo. The system reads a bounded CAS Foundation signal from hidden activations and realizes it as readable context that shifts semantic likelihood in the intended direction."

Do not use:

> "CAS controls OLMo's neurons."

Do not use:

> "OLMo understands raw CAS notation."

Do not use:

> "CAS has solved open-ended generation steering."

## Bottom Line

Stage 15 is the first pass-clean cross-architecture result. The supported product claim moves from within-Pythia scale replication to bounded cross-architecture likelihood conditioning.
