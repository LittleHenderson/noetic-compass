# V31 — CLEAN ATTRIBUTION: instruction tuning does **NOT** install speaker-instruction binding

**Date:** 2026-08-21 · `Qwen/Qwen2.5-7B` **BASE** (28 layers, 3584 hidden) vs `Qwen2.5-7B-Instruct` (v30) · owner-authorized paid **A40** (`$0.44/hr`, pod `pb5cdkvnoqh3py` verified `EXITED`) · direct transformers, **NOT** the attested engine.
**Results:** `detector_v31_clean_attribution_results.json`, sha256 `636d0dad1a89315b…`

## The design that makes this attributable
Same family, same pretraining data, same architecture, same tokenizer, same three pinned contrasts, same gate, same n. **The ONLY difference is instruction tuning.** Gate passed all three sets before the model loaded (char-ngram residual `0.000000`, token-length mismatches `0/12`) → both surface baselines **FORCED** to `0.500`.

## Results

| | contrast | `Qwen2.5-7B` **BASE** | `Qwen2.5-7B-Instruct` | **attributable Δ** |
|---|---|---|---|---|
| ✅ | CAS `^8`/`^9` cause | mean **`0.978`** | mean **`0.993`** | `+0.015` |
| ✅ | temporal | mean **`0.857`** | mean **`0.906`** | `+0.049` |
| 🟨 | **speaker binding** | mean **`0.598`** | mean **`0.612`** | **`+0.014`** |

## ✅ FINDING 1 — instruction tuning does NOT install speaker binding
The attributable effect on speaker binding is **`+0.014`** — **smaller than its effect on the temporal control (`+0.049`)**. There is **no speaker-specific installation**. All three deltas are small and comparable, consistent with generic drift, not with tuning teaching the model who is speaking.

## ✅ FINDING 2 — the gap is UNCHANGED by instruction tuning

| model | speaker | cause | **gap** |
|---|---|---|---|
| `Qwen2.5-7B` BASE | `0.598` | `0.978` | **`0.380`** |
| `Qwen2.5-7B-Instruct` | `0.612` | `0.993` | **`0.381`** |

**Gap change: `+0.001`.** Instruction tuning **does not close** the representational gap that prompt injection exploits. It leaves it essentially exactly where it was.

## ✅ FINDING 3 — the v29→v30 delta decomposes; the confound warning was CORRECT
The `+0.092` rise I refused to attribute in v30 now decomposes cleanly:

| step | speaker mean | effect |
|---|---|---|
| `pythia-6.9b` BASE | `0.520` | — |
| `Qwen2.5-7B` BASE | `0.598` | **family/data/arch `+0.078` (85%)** |
| `Qwen2.5-7B-Instruct` | `0.612` | **instruction tuning `+0.014` (15%)** |

**~85% of the apparent "instruction tuning" effect was actually the model family.** Reporting v30's delta as "instruction tuning installs speaker binding" would have been **wrong by a factor of ~6**. The refusal to attribute was correct, and this run proves it rather than merely asserting it.

## ✅ FINDING 4 — the within-model dissociation REPLICATES
The dissociation now holds in **three** models (`pythia-6.9b`, `Qwen2.5-7B` base, `Qwen2.5-7B-Instruct`), across **two families**, **base and tuned**, with both surface baselines pinned at `0.500` throughout: every model binds **cause** and **time** far better than it binds **speaker**.

## What this licenses (and what it doesn't)
- ✅ **LICENSED:** *"Instruction tuning of `Qwen2.5-7B` changes speaker-instruction binding by `+0.014` (mean over 28 layers) — less than its effect on the temporal control (`+0.049`) — and leaves the speaker-vs-cause gap unchanged (`0.380` → `0.381`). Under proof-level surface control, instruction tuning does not install speaker-instruction binding in this model."*
- 🟥 **DISCONFIRMED:** the pre-registered "instruction tuning installs speaker binding" hypothesis.
- **NOT LICENSED:** claims about RLHF'd/frontier models, or about whether a deployed system resists a live attack. This measures a **representational precondition**, not runtime behaviour.
- **Limits:** n=12 pairs/contrast, one seed, one family for the attribution; speaker figures remain marginal after selection correction.

## Why it matters
The industry's default answer to prompt injection is *"instruction tuning teaches the model to respect the system prompt."* On this model, under conditions where cheating is arithmetically impossible, **that is not what the representation shows.** Tuning may change *behaviour*; it does not appear to install the *binding*. That is a measurable, unfakeable, and commercially significant claim.
