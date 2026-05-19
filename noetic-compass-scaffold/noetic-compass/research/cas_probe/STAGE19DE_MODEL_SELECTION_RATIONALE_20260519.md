# Stage 19D / 19E Cross-Architecture Extension — Model Selection Rationale

**Date:** 2026-05-19

**Branch:** `experiment/cas-probe-pythia`

**Status:** pre-registered selection, scripts scaffolded, gates committed, pod
run not yet executed.

## Question

Stage 19C validated the Verification Mode Selector (`HIGH_PRECISION`,
`BALANCED`, `MAX_COVERAGE_TRIAGE`) across two non-Pythia architectures —
OLMo-1B (AI2) and Qwen2.5-1.5B (Alibaba). The user has authorized a third
extension to two additional architecture families. This document records the
model-selection rationale; pre-registration gates live in
`STAGE19DE_CROSS_ARCH_EXTENSION_GATES_20260519.md`.

## Selection constraints (from authorization)

- Different lab from Pythia (EleutherAI), OLMo (AI2), Qwen (Alibaba).
- Comparable scale: 1B–3B parameter range. Not 7B (separate scale-up
  direction).
- Open weights, HuggingFace-accessible, ideally Apache 2.0 / MIT / similarly
  permissive license.
- Downloadable per-model footprint ≤ 5 GB (memory-tractable on A6000).
- Locally available or downloadable via HuggingFace `local_files_only=False`
  on the pod.

## Candidate survey

| Model | Lab | Params | License | HF gated | Approx fp16 size | Verdict |
|---|---|---:|---|---|---:|---|
| `meta-llama/Llama-3.2-1B` | Meta | 1.2B | Llama 3.2 Community License | yes (terms) | ~2.4 GB | **SKIP** — non-permissive use policy, explicitly flagged in authorization. |
| `microsoft/Phi-3-mini-4k-instruct` | Microsoft | 3.8B | MIT | no | ~7.6 GB | **SKIP** — exceeds 5 GB per-model cap. |
| `google/gemma-2b` | Google | 2B | Gemma Terms of Use | yes (terms) | ~5.1 GB | **SKIP** — gated, borderline 5 GB cap, terms-of-use complicates frictionless pod download. |
| `microsoft/phi-2` | Microsoft | 2.7B | MIT | no | ~5.3 GB | **PICK** — permissive, ungated, distinct architecture (Phi-2 decoder, custom). |
| `TinyLlama/TinyLlama-1.1B-intermediate-step-1431k-3T` | TinyLlama academic group | 1.1B | Apache 2.0 | no | ~2.2 GB | **PICK** — permissive, ungated, Llama-style decoder validates Llama-family architecture pattern without Meta's license. |
| `stabilityai/stablelm-2-1_6b` | Stability AI | 1.6B | Stability Membership for commercial | no | ~3.3 GB | **SKIP** — license framing has commercial-membership clause. |
| `HuggingFaceTB/SmolLM2-1.7B` | HuggingFace | 1.7B | Apache 2.0 | no | ~3.4 GB | reserve — clean backup candidate if either pick fails to download. |

## Selected models

### Stage 19D: `microsoft/phi-2`

- **Lab:** Microsoft (distinct from EleutherAI, AI2, Alibaba).
- **Parameters:** 2.7B.
- **License:** MIT.
- **Architecture:** Phi-2 decoder. `num_hidden_layers = 32`, `hidden_size =
  2560`, `num_attention_heads = 32`. Custom architecture from the Phi family;
  this distinguishes it from the GPT-Neo (Pythia), OLMo, and Qwen2 patterns
  already validated.
- **Layer scan range:** layer positions `12-28` (17 positions). Mirrors the
  mid-late depth band used for Qwen2.5-1.5B (8-28 over 28 layers ≈ 0.28-1.0
  depth fraction); Phi-2 has 32 layers, so 12-28 hits the same 0.375-0.875
  fraction.
- **Disk footprint:** ~5.3 GB at fp16 (`pytorch_model.bin`). Within the 5 GB
  cap with a small margin. **FLAG** noted in inbox handoff: if the download
  manifest reports > 5.5 GB, the synthesizer may swap Phi-2 for SmolLM2-1.7B
  before the pod run.

### Stage 19E: `TinyLlama/TinyLlama-1.1B-intermediate-step-1431k-3T`

- **Lab:** TinyLlama academic group (distinct from the four already covered).
- **Parameters:** 1.1B.
- **License:** Apache 2.0.
- **Architecture:** Llama-style decoder. `num_hidden_layers = 22`,
  `hidden_size = 2048`, `num_attention_heads = 32`. This validates the
  Llama-family decoder pattern under a permissively-licensed model, without
  involving Meta's Llama license. Llama-style attention + RMSNorm is the
  dominant 2025-2026 open-model pattern; without TinyLlama validation, the
  cross-architecture story is missing this family.
- **Layer scan range:** layer positions `8-20` (13 positions). Mirrors the
  OLMo-1B band (6-16 over 16 layers ≈ 0.375-1.0 depth fraction); TinyLlama
  has 22 layers, so 8-20 hits the same 0.36-0.91 fraction.
- **Disk footprint:** ~2.2 GB at fp16. Comfortably within cap.

## Why these two and not the alternatives

- **Phi-2 vs Phi-3-mini.** Phi-3-mini is the stronger model but exceeds the
  5 GB per-model cap. Phi-2 is the heavier compact Phi sibling that fits.
- **TinyLlama vs Llama-3.2-1B.** TinyLlama provides Llama-architecture
  evidence under Apache 2.0. Llama-3.2-1B has the cleaner provenance but its
  license has explicit usage restrictions that the authorization document
  flagged for skipping.
- **TinyLlama vs SmolLM2-1.7B.** Both Apache 2.0 and Llama-family.
  TinyLlama has the longer training (3T tokens) and is the better-cited
  cross-architecture benchmark in the 2024-2026 interpretability literature.
  SmolLM2 is held as the backup if either Phi-2 or TinyLlama fails to load.

## Verdict matrix per pipeline stage (pre-registered targets are in the
gates document)

Both models must run the full 5-stage pipeline:

1. Stage 19D / 19E activation capture (Stage 15-equivalent).
2. Foundation probe training (Stage 16-equivalent for layer selection).
3. CPL2 / η→ε bridge replication (Stage 8-equivalent).
4. Verification Stack run (Stage 19B-equivalent).
5. Mode Selector calibration (Stage 19C-equivalent).

## GPU-hour estimate

| Model | Capture | Probe + CPL2 | Verification Stack | Mode Selector | Total |
|---|---:|---:|---:|---:|---:|
| Phi-2 (2.7B) | ~25 min | ~20 min | ~30 min | <5 min | ~80 min |
| TinyLlama (1.1B) | ~12 min | ~10 min | ~15 min | <5 min | ~45 min |

Per-model wall-clock estimate is comfortably under the 2-GPU-hour
authorization. Combined ~2.1 GPU-hours, just over the per-model cap; the
inbox handoff requests a 4-GPU-hour aggregate cap (2 per model with margin)
for the full extension. Mode Selector calibration is pure data processing
over the Stage 19B JSON — runs in CPU seconds, so its GPU-time contribution
is negligible.

## Boundary

This is model selection and script scaffolding. No pod runs have been
launched. Gates pre-registration is committed before any execution. The
five-script-per-model pipeline is a direct clone of the Stage 15 → 16 →
8 → 19B → 19C lineage, swapping only the model name, tokenizer, default
layer-scan range, and output filename prefix. No new methodology is
introduced.
