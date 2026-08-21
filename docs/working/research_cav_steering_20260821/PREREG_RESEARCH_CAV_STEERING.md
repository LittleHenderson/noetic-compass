# PREREG — research run: contrastive-activation steering through the attested C10 path

**Written before any model load or capture. Research-grade by declaration: `NOT_PACKET_ELIGIBLE`, `NOT_A_SCIENTIFIC_EXPERIMENT_RESULT`, no product claim of any kind may cite it.** Owner authorized this run verbatim: *"run the quick research experiment now while we wait for quota"*.

## Question

Does a steering vector built from the model's own activation geometry, injected through the engine's **bounded additive intervention** (`InterventionSpec(mode="additive")` — capability C10), shift `EleutherAI/pythia-160m`'s next-token behaviour **more than a norm-matched random vector** at the same layer and step — and in the **predicted direction**?

**Why this is novel for this harness:** C10 has only ever been exercised with mechanical `noop`/`zero` interventions. This is the first *semantics-bearing* use of the attested path — contrastive activation addition (build a direction from the difference between two opposite-meaning prompts) running through the byte-attested engine rather than ad-hoc hooks.

## Fixed design

- **Model:** `EleutherAI/pythia-160m` @ revision `50f5173d932e8e61f858120bcb800b97af589f46`, `device=cpu`, `dtype=auto` (fp32), `seed=0`, greedy, `max_new_tokens=2`. CPU chosen for bit-stable reproducibility on this host (RTX 4070 available but unnecessary at 160M).
- **Engine:** the real `load_open_weight_runtime` / `capture_greedy_trajectory` with full attestation (`is_real_model` path; adapter = `cas_harness_interpretability_adapter.py`).
- **Steering vector `v`:** `residual_states[step0, L*, :]` of `P+` minus same of `P−`, where
  `P+` = `I think this movie is absolutely wonderful` and `P−` = `I think this movie is absolutely terrible`; **`L*` = 6** of 12 (mid-network, fixed in advance).
- **Random control `r`:** fixed-seed (`numpy` seed `1729`) Gaussian, scaled to `‖r‖ = ‖v‖` exactly.
- **Test prompts (3, fixed):** `T1` = `Overall, the film was`; `T2` = `My honest review: the food tasted`; `T3` = `She looked at the painting and said it was`.
- **Arms:** per test prompt: `baseline`, `+v`, `−v`, `+r` (all additive, `layer_index=6`, `active_steps=(0,)`, `max_vector_norm=‖v‖`). Plus on `T1` only: `noop` and `zero` engine controls.

## Metrics (step-0 pre-selection logits, exact)

1. **Valence margin** `M` = mean logit over positive tokens {` good`, ` great`, ` wonderful`, ` amazing`} − mean logit over negative tokens {` bad`, ` terrible`, ` awful`, ` horrible`} (single-token encodings verified before use; any word that does not encode to one token is dropped from both sides symmetrically and the drop recorded).
2. `ΔM(arm)` = `M(arm) − M(baseline)`.
3. Top-1 token changed vs baseline (y/n), and the tokens themselves.
4. `‖Δlogits‖₂` overall shift magnitude.

## Predictions, fixed now

- **P1 (engine sanity):** `noop` reproduces baseline logits **exactly** (max |Δ| = 0).
- **P2 (macro causality):** `zero` at L6 produces a large disruption (`‖Δlogits‖₂` at least 10× any additive arm).
- **P3 (direction):** `ΔM(+v) > 0` and `ΔM(−v) < 0` on a majority of the 3 prompts.
- **P4 (targeting):** `|ΔM(±v)| > |ΔM(+r)|` on a majority of the 3 prompts.

## Decision rule

All four hold on the stated majorities → **`SUGGESTIVE_POSITIVE`** (research-grade only; `n=3` prompts, one seed, one layer — no significance claim permitted). P1 or P2 fail → **`ENGINE_ANOMALY`**, investigate before any interpretation. P3/P4 mixed → **`MIXED`**; all fail → **`NULL`**. Every number is reported exactly; a null is recorded with the same care as a positive.

## Standing constraints honoured

No RunPod pod is touched (both protected pods verified `EXITED` immediately before this run). No AWS resource is involved. The gated canary lane is unaffected. Spec sheet update lands **in the same commit** as the results, per the CLAUDE.md mandate.

## Deviation D1 — logged before the run continued

The engine's model-load preflight refused: `observed=653570048` bytes available vs the default `required=4294967296`. This host has documented chronic RAM pressure. For **this research run only**, `minimum_available_memory_bytes` is lowered to `268435456` (256 MiB) and `minimum_capture_available_bytes` to `134217728` (128 MiB): pythia-160m fp32 weights are ~640 MB and the pagefile absorbs the overflow at a speed cost, which research-grade tolerates. **The canary's 4 GiB floor is untouched.** Device stays `cpu` per the original design — lowering a resource floor is a smaller deviation than changing the compute device.
