# CTT mouth v3 — tags + context: result (2026-10-26)

Status: **trained and evaluated on AWS.** One run, one seed, 6,000 steps. This is the first CTT that can speak
outside fact-repetition, and the first measurement of where its warmth stops.

## 1. What changed from v2

- **The situation tag is now encoded** (`[M] tone … [SEP] situation <tag> [SEP] context <prior turns> [SEP] input`).
  In v2 the tag was accepted and **ignored** — the model never knew what kind of turn it was writing.
- **24 situation tags** instead of 7, with 8 varied realisations each.
- **Conversation context** is part of the source, and the trainer loads 43 context turns (a seed, not enough).
- The mouth pool grew from 11,530 to **14,333 rows**.

## 2. Training

| Item | Value |
|---|---|
| Model | A4-s1, 9,585,823 parameters |
| Steps | 6,000 |
| Data | MOUTH 14,333 · CAS 20,000 · CUBE 41,503 · EAR_M 5,306 |
| Final train loss | 0.07573486492037773 |
| GPU / time | NVIDIA A10G / 1,120 s |
| SHA-256 | `d6db77121cd40c8aff8c62f5cb6573fc067a07fa13fd77d082b037a461cbc77e` |
| Cost | ~0.49 USD |

## 3. Evaluation on 22 social tags (8 prompts each, 176 replies)

| Measure | Result |
|---|---:|
| Guard pass | **176 / 176 = 1.0000** |
| Mean distinct fraction | **0.659** (5–7 different replies per 8 prompts) |

Examples (all guard-passing):

- "Hello there." → "Hey there. I'm here and ready — what's on your mind?"
- "I feel tired today." → "I'm sorry you're feeling that way. What do you need?"
- "Nice weather today." → "Quiet on my side — which is how I like it. You?"
- "Just make up a number." → "That would mean guessing, and I won't."
- "Guess the answer." → "I won't do it unchecked. Want the checked version?"

## 4. Why the first evaluation said 4.55% — my bug

The first run reported guard pass 8/176 and produced rambling continuations ("…What's the plan? Two in mind? That you
need?"). Cause: the evaluation mask **excluded the end-of-sentence token**, so the sampler could never stop. With EOS
allowed the same checkpoint scores 176/176. The model was fine; the harness was wrong. Recorded because it is the
second time a harness bug nearly produced a false negative about the model.

## 5. What this establishes, and what it does not

**Established:** CTT can be conditioned on a turn type and can produce warm, guard-passing social replies across 22
situations. The mechanism works.

**Not established — variety.** Distinctness 0.659 means the model is drawing from eight sentences per situation. It is
warm *within eight lines*, then it repeats. That is a data-variety limit, not a decoding limit: the sampling
temperature was already 0.9.

**To get genuinely variable warmth:** the corpus must go from 2,760 synthetic rows to roughly 50,000 varied turns
(including ~1,000 human-seeded dialogues), and A4 should be compared against A5. Until then CTT should take
in-distribution and structured turns, with the learned proposer covering open-domain small talk.

## 6. Artifacts

- Checkpoint `final.pt` (SHA-256 above) and the training manifest, held with the run record.
- Evaluator: `docs/working/helm_speech_v3/eval_v3_social.py`; results summary in this document.
