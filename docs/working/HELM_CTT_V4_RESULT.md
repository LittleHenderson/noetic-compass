# CTT mouth v4 — trained on the cleaned public corpus (2026-10-26)

Two models trained on 42,162 cleaned, situation-tagged public turns, then evaluated on the 176 social-tag prompts and
on 22 fresh prompts never used in training (including the exact "how's it going" style).

## Training

| Model | Parameters | Final train loss | Seconds | SHA-256 (first 16) |
|---|---:|---:|---:|---|
| A4-s1 | 9,585,823 | 1.615380048751831 | 1992.9 | `08b14caf7c31ad65` |
| A5-s1 | 2,482,847 | 2.0258440375328064 | 1120.4 | `7a9a8a29f979c0b7` |

Data: MOUTH pool 56,639 rows (11,530 original + 2,760 tagged + 43 conversation + 42,306 public), CAS 20,000, CUBE
41,503, EAR_M 5,306. 6,000 steps each, order seed 107. Cost for both: 1.103 USD. Evaluation: 0.117 USD.

## Evaluation

| Measure | A4 (9.6M) | A5 (2.5M) | v3 (14,333 rows, 8 templates) |
|---|---:|---:|---:|
| Guard pass, 176 tag prompts | 174/176 | 165/176 | 176/176 |
| Distinctness | 0.688 | 1.000 (not a virtue here) | 0.659 |
| Guard pass, 22 fresh prompts | **22/22** | 22/22 | not measured |

**A4 is coherent and warm.** Real outputs on fresh prompts:

- "How's it going?" → "Fine, thanks. How are you doing now?"
- "Catch you later." → "Go well. We can pick this up whenever."
- "That's really helpful, thank you." → "Pleasure. Let me know how it goes."
- "Today's been a struggle." → "That sounds draining. Do you want to talk it through or take it easy?"
- "I keep hitting a wall with this." → "You don't have to solve it all at once. One piece at a time."

**A5 is too small and produces incoherent text**, even though it passes the word guard:

- "How's it going?" → "Good morning. What's the dating!"
- "I'm completely worn down." → "I'm sorry, that's possible. I'm sorry, but it's outside."
- "Catch you later." → "Understood. We can redo it."

**Important finding: guard pass is not a quality measure.** A5 scored 22/22 on fresh prompts while saying nonsense,
because the guard checks word rules, names and shape, not whether the reply makes sense. Coherence has to be judged by
a human or by a stronger automatic check.

## What this establishes

- The corpus helped: A4's replies are no longer confined to eight rehearsed sentences per situation. "Fine, thanks.
  How are you doing now?" was never in our templates.
- 9.6M parameters is enough for this register; 2.5M is not. The design's smaller twin check has answered: for social
  speech, A5 under-fits badly.
- The 1:4 interpretability rule remains satisfied: four checks per sentence, CTT at 9,585,823 parameters, brain fixed.

## Next

1. A blind rating by the owner: 100 A4 replies, warm or cold, natural or stilted.
2. Compare A4 against the rented proposer on the same 100 prompts.
3. Wire the best writer into `helm_chat` and measure the DeepSeek share.
