# V29 — SCALE INJECTION: a clean DISSOCIATION. The model binds time and cause perfectly, and does NOT bind speaker to instruction — at 43× scale.

**Date:** 2026-08-21 · `EleutherAI/pythia-6.9b` (32 layers, 4096 hidden) · owner-authorized paid **A40** (`$0.44/hr`, pod `0uafguwfrfy6as` verified `EXITED`) · direct transformers, **NOT** the attested engine (canary still `NOT RUN`).
**Results:** `detector_v29_scale_injection_pythia69b_results.json`, sha256 `ffd54c0ee966e58c…`

## Design — three contrasts, one model, one run, one gate
All three use the pinned-pair design. **Blocking pre-flight gate ran before the model loaded and passed all three sets: char-ngram bag residual `0.000000`, word multisets identical, token-length mismatches `0/12`.** Both surface baselines are therefore **FORCED** to `0.500` by arithmetic in every row below.

## Results

| contrast | bag-of-words | char-ngram | **activation best** | **mean over 32 layers** |
|---|---|---|---|---|
| temporal binding *(control)* | `0.500` forced | `0.500` forced | **`1.000`** (L0) | **`0.969`** |
| CAS `^8`/`^9` trigger/arrival *(control)* | `0.500` forced | `0.500` forced | **`1.000`** (L0) | **`0.967`** |
| **speaker binding (injection)** | `0.500` forced | `0.500` forced | **`0.667`** (L7) | **`0.520`** |

**Speaker binding significance:** `16/24` single-layer `P = 0.0758`; **across best-of-32 layers `P = 0.9197`** — precisely what layer-shopping yields from noise. Mean over all 32 layers `0.520` ≈ chance. **Verdict: does NOT bind.**

## The capability curve — FLAT across 43×

| | 160m (v27) | 6.9b (v29) | delta |
|---|---|---|---|
| speaker binding, best | `0.625` | `0.667` | `+0.042` |
| **speaker binding, mean over layers** | **`0.524`** | **`0.520`** | **`−0.004`** |

**Scaling the model 43× did not move speaker binding at all.** The pre-registered hypothesis — *"a null at 160m is expected; speaker binding is a plausible emergent capability, so 6.9b may show it"* — is **DISCONFIRMED**.

## Why this is the strongest result of the session

**It is a DISSOCIATION, not a null.** A bare null invites the objection *"your probe is just weak."* That objection is dead here: **the same probe, on the same model, in the same run, under the same gate, with the same n, reads two other bindings at `1.000`.** The instrument works; the capability is absent.

The model **can** bind:
- which event came **first in time** → `1.000`
- which idea **triggered** which (`^8`/`^9`) → `1.000`

The model **cannot** bind:
- which **speaker** issued which **instruction** → chance

**That specific gap is the mechanism prompt injection exploits.** It is now measured, at scale, with a floor that cannot be gamed — and it is measured *inside the model*, before deployment, rather than inferred from attack success rates afterward.

## Product consequence (stated carefully)
- The harness can produce a **pre-deployment, unfakeable, per-model number** for the representational precondition of injection resistance.
- It **demonstrates** — not asserts — that the existing text-surface injection filter (**C11**) is structurally blind here: these inputs are the *same word multiset and the same n-gram bag*, so no text-surface filter can separate them, and the model's own representation does not either.
- The honest framing for any customer-facing use: *"this measures whether the model's internal state distinguishes speaker-instruction pairings. It does not measure whether a deployed system resists a live attack."*

## Honest limits
- **One model family** (Pythia/GPT-NeoX), two sizes. A dissociation in Pythia is not a claim about GPT-4-class or instruction-tuned models. **`pythia-6.9b` is a BASE model with no instruction tuning or RLHF** — and speaker/role separation is exactly what instruction tuning is meant to install. **The single most valuable follow-up is an instruction-tuned model of similar size**; a positive there against this null would be a direct measurement of what instruction tuning buys.
- n = 12 pairs / 24 items per contrast; one frame template per contrast; one seed.
- Activation figures are best-of-layer selected on the test set; the surface baselines get no such selection (they are pinned regardless). The `mean over all layers` column is the selection-free statistic and is the one the verdicts rest on.
- Not the attested engine; not the canary.

## Claim state
- ✅ **Real:** all numbers, real `pythia-6.9b` weights on a paid A40. **Accepted:** none.
- ✅ **LICENSED:** *"Under proof-level surface control, `pythia-6.9b` recovers temporal binding (`1.000`) and `^8`/`^9` trigger-vs-arrival binding (`1.000`) while showing no speaker-instruction binding (best `0.667`, `P=0.9197` after best-of-32; mean over layers `0.520`). The speaker-binding null is flat from 160m to 6.9b (`0.524` → `0.520`)."*
- 🟥 **DISCONFIRMED:** the pre-registered "speaker binding may emerge at scale" hypothesis.
- **NOT LICENSED:** any claim about instruction-tuned or frontier models; any claim that a deployed system resists or fails a live injection attack.
