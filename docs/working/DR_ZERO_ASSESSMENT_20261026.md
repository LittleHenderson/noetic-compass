# Dr. Zero (Meta) — assessment for HELM, 2026-10-26

Question from the owner: could Dr. Zero ameliorate HELM; it appears to be on GitHub.

Sources read: the repository README and the paper abstract.
- Code: https://github.com/facebookresearch/drzero
- Paper: https://arxiv.org/abs/2601.07055 (COLM 2026)

## What it actually is

A **training loop**, not a model you can call. Two agents start from the same base model (Qwen or Llama class):

- a **proposer** writes hard but solvable questions;
- a **solver** answers them with a search tool against a Wikipedia retriever.

The solver is trained with GRPO on the proposer's questions. The proposer is trained with **HRPO** (hop-grouped
relative policy optimization) to keep producing questions at the edge of the solver's ability. No human-written
training data is used; the only knowledge source is the search corpus. Reported result: it matches or beats fully
supervised search agents on question-answering benchmarks.

## What it would take to run

- `verl==0.5.0` plus SGLang, FSDP training, `faiss-gpu`, a Wikipedia dump and an index built with `e5-base-v2`.
- GPU cluster scale: the repo trains 7B-class models with reinforcement learning over multiple iterations.
- Licence: **non-commercial**. HELM is a commercial product, so the code cannot be used directly without legal review.

## Fit with HELM

| HELM need | Does Dr. Zero help? |
|---|---|
| Conversational warmth and variety (current gap: distinctness 0.659, eight realisations per tag) | **No.** Its reward is answer correctness against a search corpus. Warmth has no such verifier. |
| A verifier-driven self-improvement loop | **The idea fits.** HELM already has a deterministic verifier — CAS receipts. A proposer/solver loop where CAS accepts or rejects could generate its own training tasks. |
| Fact-grounded speech | Partly, but HELM deliberately holds no world facts today; adding a retriever is a product decision, not a training trick. |
| Cost | High. RL on 7B models needs A100/H100-class GPUs for days. Our whole mouth budget so far is about 0.58 USD. |

## Verdict

**Not a viable drop-in now.** Three reasons:

1. It is a multi-GPU reinforcement-learning pipeline for 7B search agents, and HELM's model is 9.6M parameters with a
   24-minute single-GPU training loop.
2. Its success measure is answer correctness from retrieved text. HELM's measurable gap is how varied and human its
   small talk sounds, which that reward cannot see.
3. The licence is non-commercial.

**One idea worth borrowing later, as a bounded pilot:** the self-generated curriculum with a deterministic verifier.
HELM's CAS cheque is exactly that verifier. A small experiment could have the proposer write CAS-shaped tasks, the
brain accept or reject them, and the mouth learn from the accepted set — no human labels, no foreign distillation.
That would strengthen fact and translation behaviour, which already passes the guard at 176/176. It would not fix
warmth.

## Recommendation

- Do not adopt Dr. Zero as a component.
- Do not import its code (non-commercial licence).
- Keep the idea on the shelf as a future pilot for CAS-verifiable self-training, not for conversation quality.
- The immediate lever remains the 50,000-turn corpus with human-seeded dialogues.
