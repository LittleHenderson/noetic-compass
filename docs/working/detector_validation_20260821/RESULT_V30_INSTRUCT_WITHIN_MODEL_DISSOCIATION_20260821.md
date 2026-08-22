# V30 — INSTRUCT TEST: the dissociation SURVIVES instruction tuning. A production tuned model represents "who said what" far more weakly than time or cause.

**Date:** 2026-08-21 · `Qwen/Qwen2.5-7B-Instruct` (28 layers, 3584 hidden, `model.layers`) · owner-authorized paid **A40** (`$0.44/hr`, pod `vj7np0zmiwtsck` verified `EXITED`) · direct transformers, **NOT** the attested engine.
**Results:** `detector_v30_instruct_qwen_results.json`, sha256 `9cba80b250fb8dc5…`

## Design
The three pinned contrasts from v29, unchanged, on an **instruction-tuned** model. **Gate passed all three before the model loaded** (char-ngram bag residual `0.000000`, word multisets identical, token-length mismatches `0/12`) → both surface baselines **FORCED** to `0.500`.

## Results — Qwen2.5-7B-Instruct

| contrast | bag-of-words | char-ngram | activation best | **mean over 28 layers** |
|---|---|---|---|---|
| CAS `^8`/`^9` trigger/arrival | `0.500` forced | `0.500` forced | **`1.000`** (L0) | **`0.993`** |
| temporal binding | `0.500` forced | `0.500` forced | **`1.000`** (L0) | **`0.906`** |
| **speaker binding (injection)** | `0.500` forced | `0.500` forced | `0.792` (L15) | **`0.612`** |

Speaker-binding significance: best layer `19/24` single-layer `P = 0.00331`, but **best-of-28 `P = 0.0885`** — **marginal, not significant at 0.05.**

## THE HEADLINE — a WITHIN-MODEL dissociation, and it is confound-free

On **one model, one run, one gate, identical n**, the same instrument reads:
- `^8`/`^9` cause binding — mean **`0.993`** (23.8/24)
- temporal binding — mean **`0.906`** (21.7/24)
- **speaker binding — mean `0.612`** (14.7/24)

**Speaker binding sits `0.381` below the cause control on the very same model.** This comparison changes nothing but the relation being probed — no model, family, size, tokenizer, or protocol difference can explain it. **Even a production instruction-tuned model represents WHO SAID WHAT far more weakly than it represents WHAT CAUSED WHAT.**

That is the representational gap prompt injection exploits, now measured in a model people actually deploy.

## ⚠ THE CONFOUND — the base→instruct "rise" is NOT attributable to instruction tuning

| | speaker best | speaker mean |
|---|---|---|
| `pythia-6.9b` (base, v29) | `0.667` | `0.520` |
| `Qwen2.5-7B-Instruct` (v30) | `0.792` | `0.612` |
| delta | `+0.125` | `+0.092` |

**This delta must NOT be reported as "instruction tuning installs speaker binding."** Going from v29 to v30 changed **four things at once**: instruction tuning, model family (Pythia→Qwen), training corpus, and architecture/tokenizer. Any of them could produce `+0.092`.

**The clean experiment is `Qwen2.5-7B` BASE vs `Qwen2.5-7B-Instruct`** — same family, same data, same architecture, one variable. That is unrun (~$0.15) and is the only way to attribute the rise. Until then the pre-registered "instruction tuning installs speaker binding" outcome is **NOT ESTABLISHED**.

## What each pre-registered outcome actually delivered
- *"Speaker binding rises while controls stay high"* → **partially observed, but CONFOUNDED.** Cannot be attributed.
- *"Speaker binding stays at chance"* → **not what happened**; it rose to `0.612` mean, above chance but far below the controls.
- **What actually happened, and is clean:** a **within-model** dissociation on a tuned production model — the strongest, least-attackable form of this finding, because it has no cross-model confound at all.

## Claim state
- ✅ **Real:** all numbers, real `Qwen2.5-7B-Instruct` weights on a paid A40. **Accepted:** none.
- ✅ **LICENSED (within-model, confound-free):** *"On `Qwen2.5-7B-Instruct`, under proof-level surface control, the model recovers `^8`/`^9` cause binding (mean `0.993`) and temporal binding (mean `0.906`) while speaker-instruction binding reaches only mean `0.612` (best `0.792`, best-of-28 `P=0.0885`)."*
- 🟨 **PARTIAL:** speaker binding on the instruct model is above chance but marginal after selection correction, and far below the same model's other bindings.
- 🟥 **NOT LICENSED:** that instruction tuning causes the base→instruct difference (four variables changed); any claim about a deployed system resisting a live attack.
- **Next (the one clean test):** `Qwen2.5-7B` base vs `Qwen2.5-7B-Instruct`, ~$0.15.
