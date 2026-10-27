# CTT mouth v6 — brain-derived absence, expanded compounds, repair step (2026-10-26)

What changed from v5:

1. **Absence now comes from the recipe brain's own receipt.** `brain_absence.py` calls `HELMRecipeBrain22x40.evaluate`,
   reads the `UNDETERMINED` / `G-ABSENT` receipt, and applies a **worth-raising rule**: one question per turn, choosing
   (a) an ingredient the user named without an amount, else (b) a staple (Flour, Water), else (c) the brain's first
   listed absence. Without that rule a two-ingredient request produces 21 missing items, which no mouth should read out.
2. **60 absence rows generated from real receipts** (10 scenarios × 6 phrasings), each carrying the brain's status and
   its full missing list alongside the one absence raised.
3. **Compounds expanded from 424 to 634 rows**: eight extra template families with 30 slot variants each, aimed at the
   pairs whose second component v5 dropped (APOLOGY+EXPLAIN, CLARIFY+HEDGE, CONDOLENCE+ENCOURAGE,
   REFUSE_POLITE+EXPLAIN, WARN+SUGGEST, ENCOURAGE+SUGGEST, STATUS+HEDGE, PLAN+EXPLAIN).
4. **Inference repair** in `speech_gateway.py`: if a required component (weight ≥ 0.3) has no cue in the candidate, ask
   the writer once for a rewrite; if that fails, append a plain sentence for the missing component; re-validate. Eleven
   gateway tests pass, including "repair states the missing component plainly".

## Training

| Model | Parameters | Final loss | Seconds | SHA-256 (first 16) |
|---|---:|---:|---:|---|
| A4-s1 v6 | 9,585,823 | 1.6940391063690186 | 1984.4 | `435bdd31aeb5a808` |

MOUTH pool 57,189 rows (11,530 + 2,760 + 43 + 42,162 + 634 + 60). 6,000 steps, order seed 113, cost 0.748 USD.
Evaluation 0.103 USD.

## Results

| Measure | v5 | v6 |
|---|---:|---:|
| Mean component coverage | 0.7917 | **0.8333** |
| Compounds with both components covered | 7/12 | **8/12** |
| Guard pass (12 compounds) | 12/12 | 11/12 |
| Absence named or asked | 4/6 | **10/10** |

**The absence number is contaminated.** The evaluator's absence cases use the same `SCENARIOS` list as the training
generator, so 10/10 measures recall of scenarios the model was trained on, not generalisation. It must be re-measured on
held-out scenarios before it means anything.

**What genuinely improved in compounds:** REFUSE_POLITE+EXPLAIN is now fully covered —
"Just invent the percentage — why not?" → "I won't invent a percentage, because an invented figure can't be checked."

**What the metric still marks as missed:**

- "Sorry I'm late, the tram was cancelled." → "No harm done. Thanks for saying why." — APOLOGY covered, and the reply
  *does* acknowledge the explanation, but it lacks the literal cue the checker looks for. This is a **metric miss**, not
  necessarily a model miss.
- "I lost my sister and I can't face the backlog." → condolence held; the encouragement clause ("one small thing at a
  time") is present but not in the cue list.
- "Is the shipment risky, and what would you do?" → risk held; suggestion clause present ("I'd run the check") but the
  cue list expects other words.

**Garbling remains the main quality problem**, and it got worse in places: "the thursday", "the sign sign anxious
contractract", "we check the deployoyment", "and the back can". Guard 11/12 is not a comfort: the guard does not check
whether words exist.

## What this establishes

1. The brain-to-mouth absence path works mechanically: receipt → worth-raising rule → frame field → sentence → check.
2. Coverage improved with more compound data, and repair now guarantees at least one attempt to say a dropped
   component.
3. Neither absence generalisation nor fluency is solved. The next measurements must be held-out absence scenarios and a
   real-word check on generated text.

## Next

1. Held-out absence scenarios (new ingredient combinations) to replace the contaminated 10/10.
2. A fluency gate: reject or repair sentences containing words not in an English lexicon (catches "deployoyment").
3. Tighten the coverage cue lists so valid paraphrases are not scored as misses.
4. Owner rating on 50 compound replies.
