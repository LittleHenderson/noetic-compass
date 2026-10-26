# The 1:4 ratio — one part generated speech, four parts verifiable check

Owner, 2026-10-26: the ratio "was a ratio that still allowed the model to be interpretable."

That is the reading I am adopting, and it is the one the architecture already enforces. It is **not** a raw parameter
ratio between the two models, because the recipe brain has 68 learned values and a quarter of that would be 17
parameters — no language model works at that size. The ratio that protects interpretability is the ratio between what
is **generated** and what can **reject** it.

## The rule

**For every one sentence the model writes, four independent deterministic checks must be able to reject it.**

| Check | What it rejects | Where it lives |
|---|---|---|
| 1. Shape | empty text, over-long text, more than three sentences, more than one question | `speech_gateway.validate` |
| 2. Number licence | any digit not in the frame's licensed set | `speech_gateway.validate` |
| 3. Name licence | any proper noun not in the licensed set | `speech_gateway.validate` |
| 4. Word licence / guard | invented facts, recipe-speak, advice, wrong sentence type | `mouth_task.check` |

A fifth check exists for the mouth: the read-back ear (CAS round trip). A sixth is switch-off invariance: the brain's
answers must not change when the model is deleted.

## The growth rule that keeps the ratio

- CTT may grow to at most **four times** its current size: **9,585,823 × 4 = 38,343,292 parameters**, and only when the
  frozen test shows it is missing its own training mark.
- Every new capability CTT gains (a new situation tag or frame type) must arrive with its checks already passing.
  Opacity never outruns verification.
- The brain's readable core does not change when CTT changes. No shared parameters, no write path.
- With CTT switched off or deleted, every brain answer, receipt and exam result is identical.

## Where it stands today

- CTT: **9,585,823 parameters** (25% of the cap, so the ratio is satisfied with room to grow).
- Checks per sentence: **four** deterministic ones plus the ear for mouth output.
- Brain: **68 learned values**, unchanged.
- Growth justified now? **No.** The v3 model fits its training data (loss 0.0757) and fails on variety. That is a data
  problem. Growing the model would break the ratio without buying anything.

## What would change the ratio

Only a decision to let the model carry decisions the brain cannot check. That is exactly what the ratio forbids, and I
will not do it without an explicit owner instruction.
