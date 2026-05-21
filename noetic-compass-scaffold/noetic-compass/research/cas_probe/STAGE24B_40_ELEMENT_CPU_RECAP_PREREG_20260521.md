# Stage 24B CPU Recapture Preregistration

**Status:** `PREREGISTERED_REPLACEMENT_ARTIFACT_BEFORE_FORMAL_RERUN`

## Purpose

Stage 24B first ran as diagnostic-only because the locked CUDA Stage 9
activation binary was not present locally. This preregistration authorizes a
formal rerun against the local CPU recapture without mutating the original
Stage 9 CUDA manifest.

## Artifact Contract

| Field | Value |
|---|---|
| Original locked CUDA SHA-256 | `c70582b54f309c805fd90a69e7d23a80a714fc692aac4c1364ebc4e21b410cfb` |
| Replacement CPU recapture SHA-256 | `63702c62e6230e25e891b0e68007780954f9e6c539e4996b69e91017b972c0c9` |
| Input file | `stage9_elements_pilot_20260517.jsonl` |
| Input SHA-256 | `2f8637eedff0fb4d9e6191bd5c051ddc21cea699e33621896469a2e522306889` |
| Records | `8320` |
| Classes | `40` |
| Readout | `focus_token`, layer `5` |

## Formal Rerun Rules

- Runner: `run_stage24b_40_elements_token_sonar.py`
- Activation manifest: `stage24b_40_element_cpu_recap_prereg_20260521.json`
- Random controls: `100`
- Seed: `24040`
- Top tokens per polarity: `12`
- Primary gates: `same_domain_minus_hard_partner`,
  `same_noetic_minus_hard_partner`
- Diagnostic gates: `same_domain_minus_different`,
  `same_noetic_minus_different`
- Readability floor: `0.50`

## Boundary

This replacement contract can support a formal Stage 24B CPU-recapture result
only. It does not replace the Stage 9 CUDA artifact, and it does not authorize
exact-neuron, SAE, raw-symbol, or free-form-generation-control claims.
