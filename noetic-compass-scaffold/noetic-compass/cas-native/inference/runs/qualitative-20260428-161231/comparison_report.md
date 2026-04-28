# Qualitative Assessment — Run 4 v2 Checkpoint (replica of run 3)

**Checkpoint**: `cas-native/training/runs/v2-first-full-20260428-160804/checkpoints/final.pt`
**Dataset for prompts + ground truth**: Level 2 v1 (commit `74e5350`)
**Pod**: RunPod RTX A5000 (24 GB VRAM)
**Generation date**: 2026-04-28
**Sampling**: temperature 0.7, top-p 0.9, max 80 new tokens, seed 42

## Headline finding

**The model has not learned to generate structured CAS expressions.** It produces noisy text dominated by `[UNK]` tokens (vocabulary size 1850 from training-data tokenization, sparsely populated by the model's outputs). Where ANY CAS-like fragment appears in a generation, it is almost always a bare Noetic token (`^0` through `^9`) — the simplest 1-character compilable CAS surface — never a structured compound expression like `^N^D_{Fk}|R`, never a recipe `Θ(Ω_*) = …`, never a typed cluster, never a named emergent assignment.

The headline `compile_valid_anywhere = 80%` (24/30) is **a measurement artifact** of the script's fragment-extraction logic. It treats a generation as "valid" if a regex finds *any* CAS-shaped substring that compiles. Bare `^7` compiles, so generations that happen to mention `^7` somewhere in their `[UNK]`-dominated output get marked valid. **The structurally-valid rate at the level of "model produced a meaningful CAS expression for this bucket" is effectively 0/30.**

## Per-bucket assessment

### v74_baseline (3/5 "valid", actually 0/5 structured)

**Ground truth examples** (from dataset):
- `^3^P_{F1} * ^0^P_{F1}`
- bare state literals like `^2^P_{F2}` or compound products

**Generated samples** (representative excerpts):
- `[UNK] [UNK] [UNK] speaks [UNK] alignment negotiator [UNK] [UNK] …`
- `[UNK] [UNK] [UNK] [UNK] [UNK] [UNK] (×1.51). rhythmic [UNK] …`
- `keeps under [UNK] [UNK] by [UNK] [UNK] (×1.00). × [UNK] [UNK]…`

**Compile-valid fragments**: `^1`, `^2`, `^3`, `^5`, `^6`, `^4`, `^0` (all bare Noetics).

**Diversity**: prompts produced different stochastic outputs but all in the same pattern: `[UNK]`-dominated text with occasional `^N` tokens and `(×N.NN)` coefficient-formatted numbers (a v76 production-recipe surface artifact bleeding into the v74 bucket).

**Structural quality**: zero. No `^N^D_{Fk}` compound state appeared in any v74 sample.

### v75_register (5/5 "valid", actually 0/5 structured)

**Ground truth examples**:
- `^2^E_{F4}|f + ^7^E_{F2}|E`
- Paired co-presence over distinct states

**Generated samples** (excerpts):
- `[UNK] [UNK] [UNK] [UNK] [UNK] foundation_5, task ω_landing [UNK] …`
- `[UNK] [UNK] ^4^p|e, [UNK] [UNK] [UNK] [UNK] [UNK] [UNK] situ…`
- `[UNK] [UNK] decomposes contact [UNK] [UNK] (×1.94), [UNK] do…`

**Compile-valid fragments**: `^2`, `^1`, `^6`, `^4`, `^3`, `^0`, `^7`, `^8` (bare Noetics).

**Notable detail**: sample #2 produced `^4^p|e` — a malformed state with lowercase domain and lowercase register. The compiler regex didn't match it as a state (which would require uppercase domain), so it was caught by the bare-`^4` fallback.

**Structural quality**: zero correctly-formatted register-tagged states. Lowercase suggests the model has imitated the *shape* of `^N^D|R` but not the case discipline.

### v77_rule_four (3/5 "valid", actually 0/5 structured)

**Ground truth examples**:
- `^5^O_{F3}|T + ^5^O_{F6}|A + ^5^O_{F5}|E` (compliant co-presence)
- `^4^P_{F1}|A × ^4^P_{F1}|f × ^4^P_{F1}|T = ^4^P|Ω_attunement` (compliant emergent)
- Or violations: same form without `= Ω_*`

**Generated samples** (excerpts):
- `[UNK] [UNK] [UNK] relation_cluster. integrate [UNK] [UNK] [U…`
- `^4^p|e, [UNK] (×0.65). [UNK] (×0.70), [UNK] manifestations h…`
- `(noetic, [UNK] [UNK] the [UNK] [UNK] [UNK] 4 distinct (×2.31…`

**Compile-valid fragments**: `^4`, `^5`, `^1` (bare Noetics).

**Structural quality**: zero `× = Ω_*` cross-register integrations. Zero `+` co-presence with three distinct register-tagged states. The model produced a `(noetic, …)` token sequence that resembles a typed-tuple shape, but no closure.

### v77_omega (5/5 "valid", actually 0/5 structured)

**Ground truth examples**:
- `(^8^C_{F7}|A × ^8^C_{F5}|f × ^8^C_{F2}|T) = ^8^C|Ω_invocation`
- `(^4^E_{F7}|T × ^4^E_{F7}|f) = ^4^E|Ω_attunement`

**Generated samples** (excerpts):
- `[UNK] [UNK] contamination [UNK] anomaly [UNK] speaks [UNK] [UNK] …`
- `[UNK] [UNK] simultaneously, [UNK] guiding [UNK] [UNK] [UNK] …`

**Compile-valid fragments**: `^1`, `^8`, `^7`, `^9`, `^0`, `^4`, `^5`, `^3`, `^6` (bare Noetics — full coverage 0-9 across the bucket's 5 samples).

**Structural quality**: zero named-emergent assignments. The bucket's defining structure (parenthesized ×-product = Ω_name) appears nowhere in the generations. The token `omega_clarity` did appear in one v76 sample as plaintext, but never inside the canonical `(…) = ^N^D|Ω_…` structure.

### v76_production (4/5 "valid", actually 0/5 structured)

**Ground truth examples**:
- `Θ(Ω_pattern_entrainment_learning) = 0.48*^1^C_{F1}|A + 1.96*^7^C_{F7}|A + 0.99*^5^C_{F1}|f → Ω_pattern_entrainment_learning + 0.15*Λ·Ω_evaluative_drift`
- Recipe form: `Θ(Ω_*) = a₁*S₁ + a₂*S₂ + … → Ω_*`

**Generated samples** (excerpts):
- `[UNK] [UNK] noeticcluster{^7, [UNK] [UNK] [UNK] mind, [UNK] …`
- `pullback(noeticcluster{^8, adjustment. [UNK] [UNK] with [UNK]…`
- `on [UNK] [UNK] [UNK] [UNK] downstream [UNK] landed, ⊆ falls …`

**Compile-valid fragments**: `^7`, `^6`, `^8`, `^5`, `^1`, `^9` (bare Noetics).

**Structural quality**: zero recipes. Sample #1 has lowercase `noeticcluster{^7,` (cluster shape with lowercase keyword and unclosed brace) — closest the model came to a structured CAS form, but malformed and from the wrong family (meta-logic, not v76 production).

### meta_logic (4/5 "valid", actually 0/5 structured)

**Ground truth examples**:
- `Pullback(NoeticCluster{^3, ^6, ^7}, NoeticCluster{^3, ^5})`
- `StateCluster{^7^O} ∪ StateCluster{^7^E, ^9^C}`
- `^2 ∈ Noetics`, `Coordinate{^2, P, F2, A}`, etc.

**Generated samples** (excerpts):
- `(×1.33), [UNK] [UNK] [UNK] (×1.92). [UNK] valuation, [UNK] c…`
- `attention (×1.51), [UNK] surprising [UNK] gravitates [UNK] [UNK] …`
- `∪. [UNK] [UNK] connection. [UNK] [UNK] noetic f2, [UNK] appr…`

**Compile-valid fragments**: `^0`, `^9`.

**Structural quality**: zero typed clusters or set operations actually formed. Sample #4 mentions `∪` and `noetic f2` — fragment-shaped but unattached.

## Cross-bucket diversity & coverage

**Noetics**: full coverage. Generated text contains tokens `^0` through `^9` across the 30 samples.

**Domains** (P/C/E/O): only `p`, `o`, `e` appeared (lowercase) in compound-state-like fragments. Never the canonical uppercase `P/C/E/O` that the compiler accepts.

**Drives** (F1-F7): only `f2` appeared (in meta_logic #4). Drive subscripts essentially absent from generations.

**Registers** (T/A/f/E): only `e` appeared (lowercase). The trained model has not learned to emit register tags in the canonical position or case.

**Foundations** (Foundation_1 through Foundation_7): only `foundation_5` appeared (in v75 #0), as plain text.

The model's vocabulary clearly contains the relevant lexical tokens (it has seen them in training prompts/responses), but it has not learned to **assemble them into structured CAS expressions** at the surface level.

## Honest interpretation

The generations look like a Markov-chain over `[UNK]` and a small handful of recurring template shards: `(×N.NN)`, `[UNK]` clusters, occasional `^N` references, and rare lowercase keywords (`noeticcluster`, `pullback`, `omega_clarity`). This is the noise floor of a transformer that has done **189 gradient updates** on a 73M-parameter scratch initialization. The bf16 mixed precision and `lambda_production` curriculum landed exactly as designed — but training quantity, not training quality, is the limiting factor here.

The validation loss numbers from training (eval at steps 50/100/150 producing val total ≈ 226 → 421 over the curriculum ramp) are dominated by the production_loss term saturating at full weight; lm_loss at val time is ~9-10, basically unchanged from initialization (the LM head has barely moved).

## Recommendation

**The checkpoint is not yet useful for downstream qualitative work.** Two paths to extract more value before declaring the model "good":

1. **Train substantially longer** — 10× steps (~2000 steps at batch=128, ~10 minutes wall-clock on A6000) is the minimum to expect any structured-CAS emission. 100× (~20K steps, ~2 hours) is what the architecture was sized for.
2. **Tokenizer change** — the SimpleTokenizer at vocab=1850 is leaking critical structure as `[UNK]`. Adopting a BPE/sentencepiece tokenizer (or at minimum reserving structural CAS tokens like `^`, `_{F`, `|A`, etc. as single non-mergeable tokens) would dramatically increase the signal density per training step.

For the current checkpoint specifically, I'd recommend **not committing the .pt files** as production artifacts and **flagging the metrics-vs-quality gap** in the next training directive: a falling loss curve does not mean the model has learned structured generation when most of its output is `[UNK]`.

## Files in this run dir

- `samples.jsonl` — all 30 generations with prompts, generated text, ground truth, and compile attempts
- `bucket_summary.json` — aggregated valid-rate per bucket (the misleading one — see headline)
- `comparison_report.md` — this file
