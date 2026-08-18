# CAS Harness — capability spec sheet + white-box loop (A) scope (2026-08-18)

**Goal:** not a one-off test. Build a **capability spec sheet** that exhibits the *width* of
the harness across a model-size ladder. The white-box diagnose→localize→repair loop (A) is
one row; run it first on a tiny model to prove it end-to-end, then up the ladder.

**All white-box work runs on RunPod, never local** (local CPU is slower AND bogs down the
owner's working machine — see [[feedback_gpu_work_goes_to_runpod_not_local_install]]).

**White-box requires OPEN weights.** The closed API models (DeepSeek-V4-Pro etc.) can only be
read black-box (they were our lens *readers*). The spec-sheet capabilities run on open models.

## The model ladder (open weights)
| Tier | Model (open) | GPU need (RunPod) | Priority |
|---|---|---|---|
| tiny | `pythia-160m` | 1 small GPU (proof run) | **first — proves the loop** |
| **20B** | `GPT-NeoX-20B` (already on hand) | 1× A100 80GB | **immediate real target** |
| ~70-100B | Llama-70B-class | 2-4× A100/H100 | next |
| 300-800B | Llama-405B / DeepSeek-V3-671B (MoE) | sharded-audit "Fleet" | aspirational; needs the sharded architecture |

## The unit job (model-agnostic — write once, swap the model)
Given a loaded open model + one "part" (a behavioral function, e.g. *caveating*, *weighing*):
1. **Probe set:** short present/absent examples of the part (reuse the proxy-loop fault items).
2. **Capture + probe:** grab hidden states at each layer; train a linear probe → the part's *direction*. Report probe accuracy per layer (which layer carries it).
3. **Ablate** the direction → generate → measure the part weakened (+ **matched control**: a random same-norm direction, must move less).
4. **Steer** +direction → generate → measure the part strengthened (+ matched control).
5. **Residual read (the CAS-Ohm piece):** define `I_obs` as the probe-direction activation magnitude; compare predicted vs observed under the intervention; report `ΔI` + which layer/direction localized it.
6. **Report a row:** {model, part, best layer, probe acc, ablate effect vs control, steer effect vs control, ΔI}. Honest claim-status per cell.

This is the **real-model twin of the proxy** we just ran (localization 6/8, targeting beat generic 7.2 vs 4.6) — but now the "repair" is *actual steering of the weights' activations*, not re-prompting.

## The spec-sheet matrix (the WIDTH)
Rows = harness capabilities; columns = model tier. Fill with real measured numbers + claim-status.

| Capability | 160m | 20B | ~100B | 300-800B |
|---|---|---|---|---|
| Hidden-state capture | validated (Gate 1) | validated (Stage 9) | — | Fleet |
| Linear probe (find a part) | **A** | **A-next** | — | — |
| Subspace ablation (causal) | validated (Gate 1) | — | — | — |
| Steering (add direction) | validated (drive-eraser) | validated (Qwen) | — | — |
| Layer trajectory (shape of thought) | **A** | **A-next** | — | — |
| Jacobian / JVP-VJP lens | validated (Gate 1) | — | — | — |
| Matched controls (every claim) | validated | — | — | — |
| **Residual diagnose→localize→repair** | **A (new)** | **A-next** | — | — |
| Neuron-cover / circuit localize | validated | — | — | — |

Many cells are already validated at *some* scale — the spec sheet's job is to run them
**systematically up the ladder**, add the residual/repair row, and present it as one coherent
sheet with honest claim-status (real / matched-control / not-yet-run per cell).

## Sequence
1. **Now (pending pod SSH):** unit job on `pythia-160m` — one part (caveating), full loop, cheap. Proves A end-to-end.
2. **Immediate real target:** same job on `GPT-NeoX-20B` — the first "real" spec-sheet row.
3. **Widen:** more parts + the other capability rows at 160m/20B.
4. **Scale:** 70-100B multi-GPU; then 300-800B via the sharded-audit Fleet.

## Honest flags
- **`I_obs` is the open problem.** Defining "attention flow" from activations is the CAS-Ohm whitepaper's own untested hypothesis. Step 5's probe-magnitude proxy is our *first concrete attempt*, labeled as such — not a validated measurement.
- **Cost scales hard.** 160m ~ minutes/cents; 20B ~ GPU-hours; 300-800B ~ the Fleet + real money. Log cost/time per cell. Expensive pod launches follow the `AUTHORIZED: yes` protocol.
- **Claim discipline.** Every cell carries its status; matched controls required before any causal claim; "steering restored the part" only if it beats the random-direction control.
- **Write-once-run-many.** The unit job takes `--model`; the same code runs every tier. No per-model rewrites.

## Blocked on
Owner's RunPod SSH line (pasted in chat) to run tier-1. Script adapts the existing harness
probe/steer code (`cas_probe` / live-trace-worker) on the pod — not re-implemented.
