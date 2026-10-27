# Situations are mixtures — the consequence for HELM's speech (2026-10-26)

Owner's point: the brain is made of recipes because logic starts from **knowing what we do not know**. Mental,
emotional and physical states, situations, circumstances and events are usually **mixtures of compounds specific to
their own domains**. A single situation label cannot carry that.

## What this means for the recipe brain

The brain already works this way. A recipe is `Θ(Ω) = a·X + b·Y → Ω`: several prerequisites in proportion, with a
**limiting reagent** deciding the yield. The limiting reagent is the formal version of "what we do not have enough of" —
absence is a first-class answer, not an error. That is exactly the starting point of reasoning the owner names.

## What our speech layer did instead

The 24 situation tags are **single labels**. Each training turn got one tag. That flattens a compound into a category.
"I'm exhausted but I have to finish this report by Friday" became EMPATHY, and the deadline vanished from the target.

## Measurement (crude, and labelled as such)

`situation_mixtures.py` scans the cleaned 42,162-turn corpus with cue rules and proposes a weighted mixture of up to
three components per turn:

| Result | Count |
|---|---:|
| Turns with one detected component | 40,578 |
| Turns with two or more | 1,584 |
| Multi-component fraction | **0.0376** |

**This is a floor, not the truth.** The detector only sees cue words, so it misses implicit compounds. The corpus itself
is also thin here: EmpatheticDialogues prompts are mostly one stated emotion. What the scan does show is real compounds
that our single tag erased, for example:

- "Ok, but what if I'm worried about one of the individuals who is fighting? … What should I do then?" — tagged EMPATHY;
  actually EMPATHY 0.5 + SUGGEST 0.5.
- "They were brilliant, thank you! Which one do you think is best?" — tagged THANKS; actually THANKS + CLARIFY.
- "Thank you. Can you explain American folk music to me?" — tagged THANKS; actually EXPLAIN + THANKS.
- "How much tea does the average person drink each year? … I am not sure." — tagged ASK; actually CLARIFY + SUGGEST +
  HEDGE.

## The design consequence

1. **Encode the situation as a mixture, not a label.** The mouth source should read something like
   `situation empathy 0.5 encourage 0.3 plan 0.2`, and the target sentence should address every component above a
   threshold.
2. **Carry absence explicitly.** The frame must include what the brain does **not** know — missing ingredients, unknown
   deadlines, unlicensed facts — so the reply can name the gap or ask about it, instead of inventing or ignoring it.
3. **Build compound training rows.** The public corpus alone will not teach mixtures; we must compose two- and
   three-component turns and author some by hand.
4. **Measure coverage, not just guard pass.** For each component with weight ≥ 0.3, check whether the reply acknowledges
   it. Guard pass alone proved meaningless when A5 scored 22/22 while talking nonsense.
5. **Retrain A4 on the mixture representation and compare** against the single-tag A4 on the same prompts.

## What stays true

- One checkable basis per sentence: the mixture changes what is said, not who checks it.
- The 1:4 ratio: four checks per sentence, model at 9,585,823 parameters, brain unchanged.
- The guard still rejects invented numbers and names; a mixture does not license new facts.

## Artifacts

- `situation_mixtures.py`; result sample `data/public_corpus/situation_mixtures_sample.json`.
- Cleaned corpus: 42,162 rows (`public_turns_clean.jsonl`), single-tag as built.

## Correction (2026-10-26, owner challenge): absence is decided by the recipe, not by the writer

The owner asked, correctly: absence is already decided by the recipe, so what does "wiring absence into the model"
mean?

**What it does not mean.** The model never decides what is missing. If it did, it would be inventing gaps — the same
failure as inventing facts.

**What it does mean.** The mouth receives a field that says what the brain has already found missing — the limiting
reagent, the absent prerequisite, the unfilled slot. Its only job is to phrase that: name it, or ask for it. The field is
filled from the brain's receipt, not from the writer and not from me.

**Where I was wrong.** The 424 compound/absence rows I built had **hand-written** absence labels. They teach the
phrasing pattern, which is useful, but they are the wrong *source*: an authored absence is a guess, not a receipt. Two
consequences follow:

1. Training rows must be generated from real brain runs: feed the recipe brain a scenario with a missing ingredient or an
   open slot, take its receipt, and pair that receipt with a sentence. Then the model learns to phrase decisions the
   brain actually made.
2. The gateway must enforce both directions, which it now does:
   - if the brain declared an absence, the sentence must name it or ask about it — otherwise rejected
     ("absence not named");
   - if the brain declared none, the sentence may not claim something is missing — otherwise rejected
     ("invented absence").

Both checks are implemented in `speech_gateway.validate` and covered by three tests (9/9 in the gateway suite).

**So the ordering is:** recipe decides absence → frame carries it → writer phrases it → check verifies the phrasing
matches the receipt. The writer never gets a vote.

