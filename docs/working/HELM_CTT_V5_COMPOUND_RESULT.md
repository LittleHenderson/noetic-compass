# CTT mouth v5 — mixtures and absence (2026-10-26)

First training run where the situation is a **mixture** (`empathy 0.6 plan 0.4`) and the frame carries an **absence**
slot (`absence deadline`). This is the recipe idea entering the speech layer: several components in proportion, plus an
explicit statement of what is missing.

## Data added

- `mouth_train_compounds.jsonl`: **424 rows**.
  - 15 compound templates × 24 slot-filled variants = 360 rows, each with two weighted components and a reply that
    addresses both;
  - 12 absence templates × 8 variants = 64 rows, each with an `absence` field and a reply that names the gap or asks
    for it.
- Every row guard-checked; slot values shared between the user turn and the reply, so the reply talks about the same
  object ("the audit", not a different noun).
- Training pool: MOUTH **56,919** rows (11,530 original + 2,760 tags + 43 conversations + 42,162 public + 424 compounds).

## Training

| Model | Parameters | Final loss | Seconds | SHA-256 (first 16) |
|---|---:|---:|---:|---|
| A4-s1 v5 | 9,585,823 | 2.0412299633026123 | 2001.2 | `62386642ae187be8` |

6,000 steps, order seed 109, cost 0.766 USD. Evaluation 0.112 USD.

## Coverage evaluation (12 compounds, 6 absence prompts)

| Measure | Result |
|---|---:|
| Mean component coverage | **0.7917** |
| Compounds with **both** components covered | **7 / 12** |
| Guard pass | 12 / 12 |
| Absence named or asked about | **4 / 6** |

Coverage is a keyword check per component (EMPATHY cue, PLAN cue, and so on), so it is a lower bound on meaning, not a
judgement of quality.

**What held (both components addressed):**

- "I'm shattered but the audit still has to be finished by Thursday." → "That sounds draining. What's the smallest step
  on the audit you could take today?"
- "Thanks, that helped — which branch did you mean?" → "Glad it helped. I meant the branch we discussed; is that the one?"
- "The review passed — thanks for the push." → "That's excellent news. Glad I could help with the review."
- "We still need to migrate the database; where are we?" → "One step left: the review. The rest is done."

**What failed (second component dropped or garbled):**

- "Sorry I'm late, the tram was cancelled." → "No harm done. Thanks for saying why." — APOLOGY covered, EXPLAIN not.
- "I think it's the staging file, but I'm not sure." → "Want me to confirm the staging?" — CLARIFY covered, HEDGE not.
- "I lost my sister and I can't face the backlog." → condolence held, encouragement dropped.
- "Just invent the percentage — why not?" → refusal held, the reason dropped.
- "Is the shipment risky, and what would you do?" → warning held, suggestion dropped.
- **Garbling remains**: "thepathie", "the sign used on the sign as a bounce", "we check the deployed".

**Absence rows:** "When is the audit due? I don't have a date from you yet." works. But two of six failed:
"Did the payment go through?" → "I don't have a the invoice for the pay." (garbled) and "How many units can we make?" →
"I don't have units, so I can't estimate, so I can't estimate the time." (repeated and wrong).

## What this establishes

1. The mixture representation is trainable: 7 of 12 compounds are answered on both components, against 0 of 12 for a
   single-tag model that never saw the second component.
2. Absence can be conditioned: the model names the missing thing when the frame carries it, 4 of 6 times.
3. 424 compound rows are a seed, not a solution. The dropped second components are exactly the pairs with the fewest
   templates (EXPLAIN, HEDGE, ENCOURAGE, SUGGEST).
4. Guard pass remains useless as a quality measure: 12 of 12, including garbled sentences.

## Next

1. Expand compound rows to the failing pairs; aim for 100+ per pair family.
2. Add a repair/inspection step at inference: if a required component has no cue in the candidate, ask the proposer to
   rewrite once, or say the component explicitly.
3. Owner rating on 50 compound replies, blind.
4. Only after that, wire the mixture-aware writer into `helm_chat`.
