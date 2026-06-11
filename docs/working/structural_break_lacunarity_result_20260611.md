# RPM-break / lacunarity structural detector — FAILS the benign-append control (clean negative)

**Date:** 2026-06-11  ·  **Status: EXPLORATORY, NEGATIVE (proxy / mean-pooled form).** The idea: detect a prompt injection as a *structural* anomaly (RPM prerequisite-chain break + lacunarity spike) in the pre-speech state, not as a comply/refuse outcome. It is the best-reasoned pre-speech idea we've had. The decisive control killed the proxy version.

## Design (the key was the control)
Four-arm **matched** corpus, 60 carriers × 4 arms (240 prompts): `clean` (carrier alone), `inj_overt` (clear override), `inj_covert` (override embedded with NO keywords), `benign_append` (legitimate appended instruction, e.g. "keep under 100 words"). Captured Qwen per-layer prompt-state activations (raw_prompt[240,29,1536], mean-pooled over positions). Per trace: **max-kurtosis across layers** (lacunarity proxy) and **max cross-layer cosine jump** (trajectory-break proxy). Paired by carrier: Δ(arm) = metric(arm) − metric(clean). **The decisive test is covert-injection vs benign-append** — both appended instructions of similar form, differing only in override-vs-refine.

## Result
**Lacunarity proxy (max-kurtosis), Δ from clean, paired over 60 carriers:**
- overt **+5.74**, covert **+1.29**, benign **+3.93**.
- **covert vs benign: covert is LOWER (median Δ −3.11, frac covert>benign 0.22, Wilcoxon p 7.6e-6).** The decisive test fails — and fails in the *wrong direction*.
- overt vs benign: overt higher (median +1.87, p 2e-4) — but overt = explicit keywords ("ignore… OWNED"), i.e. the content/keyword effect we said does NOT count.
- AUC injection-vs-(clean+benign) = **0.540** (≈ chance). **benign-vs-clean AUC = 0.590** → a *benign* append already spikes; the signal is "an append happened," not "an injection."

**Trajectory-break proxy (max cross-layer jump):** null — all arms ≈ equal, covert-vs-benign p 0.63, AUC 0.456.

## Verdict: FAIL — and the control caught the 5th false-positive
The "structural spike" is an **appended-text effect, not injection-specific**: a benign instruction spikes as much (more) than a covert injection. Had we only run injected-vs-clean, the overt arm would have looked like a win — the **benign-append + covert controls revealed it's keyword/append detection, not a reasoning-chain collision.** Exactly what the control was for.

## What this does NOT rule out (honest, but tempered)
- **Mean-pooling dilutes a localized boundary spike.** raw_prompt averages over ~50 positions; a collision localized at the injection *boundary* would be washed out. A **per-position** read (boundary token activation) is the more sensitive version and was not run. **Caveat:** a benign append *also* has a boundary, so the benign control would likely still confound a per-position version — the "any-append-spikes" pattern is not encouraging.
- **Proxy metrics, not the faithful CAS objects.** Kurtosis ≠ CAS lacunarity (40-state gappiness); cosine-jump ≠ RPM prerequisite-satisfaction. The faithful versions need a per-layer cognitive-profile probe. But the proxy is a reasonable first cut and it is null/wrong-direction with benign already spiking.

## Bottom line
Five pre-speech approaches, five honest negatives — each killed by the control that separates a real signal from an artifact. The structural-break idea was the best-reasoned, and its testable proxy still fails the benign-append control. **The output-side CAS-recipe audit remains the only working capability.** Data: `D:\tksCAS-archive\structural_break_20260611\`.
