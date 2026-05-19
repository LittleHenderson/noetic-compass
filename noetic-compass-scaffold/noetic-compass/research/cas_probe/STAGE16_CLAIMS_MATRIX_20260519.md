# Stage 16 Claims Matrix - Qwen2.5-1.5B

**Status:** `PASS_CLEAN_STAGE16_QWEN15B_CPL2_REPLICATES`

Stage 16 tested whether the eta-to-epsilon CAS Harness bridge transfers to a
third model family: `Qwen/Qwen2.5-1.5B`.

## Provenance

| Item | Value |
|---|---|
| Branch | `experiment/cas-probe-pythia` |
| Pre-registration | `STAGE16_QWEN15B_GATES_20260519.md` |
| Model | `Qwen/Qwen2.5-1.5B` |
| Model revision | `8faed761d45a263340a0528343f099c05c9a4323` |
| Fixture | `stage7_foundation_pilot_20260517.jsonl` |
| Fixture SHA-256 | `3e4a1aca9f168a190116578b0b4fdb5bab633232ba06902039b233e589121250` |
| Activation binary | `stage16_qwen15b_activations_20260519.npz` |
| Activation SHA-256 | `ccb79afe5a3215f0f6aac828c574a0d14cf8115ab769489ea4269c70ce43fe8e` |
| Activation binary committed? | No |
| Manifest SHA-256 | `4bddb609c48b7c02568bd19d21bfd3ca2aa07b49da321a1f796aa86460c7a0e4` |
| Probe report SHA-256 | `182aaaa752e49099bb70390f799f1fc43997c6fccc0ca5859690cb275f06cf74` |
| CPL2 report SHA-256 | `0aad3bdaccecd2d9d12db08dc0dc1f35250ae1d224e9d8966e266f4261421507` |

## Layer Selection

Layer choice was made by validation accuracy before test reporting.

| Metric | Value |
|---|---:|
| Candidate layer positions | `8-28` |
| Selected layer | `11` |
| Validation accuracy | `0.9985` |
| Validation lacunarity | `0.0001` |
| Test accuracy | `0.8202` |
| Test lacunarity | `0.0084` |
| Selected-row Foundation accuracy | `0.8036` |
| Selected-row Drive accuracy | `0.9107` |

## CPL2 Gate

Load-bearing condition: `probe_readable`.

| Metric | Result | Gate |
|---|---:|---:|
| Probe-readable delta vs none | `+0.7960` | `> +0.15` |
| Probe-readable minus partner-readable margin | `+1.6253` | `> +0.30` |
| Positive cases | `83/112` | `> 60/112` |
| Paired Wilcoxon p | `2.92e-12` | `< 0.05` |

Verdict: all PASS_CLEAN gates passed.

## Controls

| Condition | Mean delta vs none | Positive cases |
|---|---:|---:|
| `gold_readable` | `+0.9366` | `89/112` |
| `probe_readable` | `+0.7960` | `83/112` |
| `partner_readable` | `-0.8293` | `31/112` |
| `gold_raw` | `+0.0037` | `65/112` |
| `probe_raw` | `-0.0002` | `66/112` |
| `partner_raw` | `-0.0082` | `56/112` |

The raw-symbol controls remain effectively null in mean effect. The mechanism is
readable realization conditioning, not raw CAS-symbol understanding.

## Cross-Model Line

| Model | Delta vs none | Margin over partner | Positive cases |
|---|---:|---:|---:|
| Pythia-160M | `+0.2828` | `+0.6829` | `81/112` |
| Pythia-1B | `+0.5542` | `+1.2460` | `90/112` |
| Pythia-2.8B | `+0.5832` | `+1.3363` | `92/112` |
| OLMo-1B | `+0.6037` | `+1.3047` | `87/112` |
| Qwen2.5-1.5B | `+0.7960` | `+1.6253` | `83/112` |

## Claim Levels

| Claim | Status | Evidence |
|---|---|---|
| Qwen hidden states contain recoverable 28-Foundation signal | Supported | selected layer 11, test accuracy `0.8202` |
| Qwen readable-prefix CPL2 bridge passes | Supported | all PASS_CLEAN thresholds passed |
| Cross-architecture replication across Pythia, OLMo, Qwen | Supported | OLMo and Qwen both pass clean outside Pythia family |
| Raw CAS tokens steer Qwen | Not supported | raw controls near-zero mean effect |
| Hidden-state steering in Qwen | Not tested in Stage 16 | out of scope |
| Exact causal neurons or weights fired | Not claimed | Stage 16 uses probes and likelihood conditioning |
| Open-ended visible generation control | Not claimed | CPL2 is a bounded likelihood assay |

## Defensible Wording

> CAS Harness replicated on Qwen2.5-1.5B: a validation-selected Foundation
> probe recovered CAS structure from hidden activations, and a readable
> eta-to-epsilon realization prefix shifted semantic likelihood under the
> pre-registered CPL2 gate. This is third-family evidence across Pythia,
> OLMo, and Qwen. It is not a claim of exact neuron causality, raw CAS-symbol
> understanding, or open-ended generation control.
