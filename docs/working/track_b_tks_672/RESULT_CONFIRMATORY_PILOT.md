# RESULT — `CONFIRMATORY-PILOT-R1-R6`

**Verdict (mechanical): `V3_AUTHORIZED: False`.** Table in `authorization_table.json`; no prose
override applies, per the frozen rule.

```
R1        PASS   0.0250 overall, worst cell 0.100
R1B       PASS   0.0394
R2        FAIL   world 0.6345 > 0.60   (drive 0.5001, foundation16 0.3173 under)
R3-WORLD  ----   train 0.5833          (chance 0.25)
R3-DRIVE  ----   train 0.4236          (chance 0.1429)
R3-JOINT  FAIL   0.2222                (bar 0.70)
R4        FAIL   heldout joint 0.3542  (bar 0.55); gap -0.1319 — heldout BETTER
R5        PASS   judge 0.7500 vs char 0.5208 / tfidf 0.5625 on heldout World
R6A/R6B   PASS   1/160 each — low-leakage regime reproduced in both families
```

---

## What passed matters

- **The corpus is not a family-specific cue system.** Held-out realization families were judged
  *better* than train families (`gap -0.13`). The trap the held-out design existed to catch did
  not occur.
- **`R5` is the first lexical-resistance pass in the campaign** on sibling-safe folds: the judge
  beats both surface baselines on held-out World by `+0.19`/`+0.23`.
- Leakage control and replayability both held (`R1`, `R1B`, `R6A/B`).

**The corpus is clean and not mute — but what it says is blurry.**

## The broken axis is DRIVE, and the confusions are semantically adjacent

```
7 lust/reproduction  -> judged 4 companionship   x14   <- largest
6 material things    -> judged 3 life/health     x13
1 God                -> judged 2 wisdom          x9
6 material things    -> judged 2 wisdom          x9
7 lust/reproduction  -> judged 5 power           x9
```

Under silent enforcement, lust written without its vocabulary reads as romance; material
sustenance reads as health; longing for God reads as seeking wisdom. **The de-labeled scenarios
preserve the World's location better than the drive's identity.**

Against the frozen interpretation map, this is closest to the **"World passes, drive fails"**
row (World `0.58`–`0.75` vs chance `0.25`, beats lexical; drive `0.42`–`0.48` vs chance `0.14`,
confusing neighbors): *repair belongs in the **motive block**, not the World criteria* —
targeted repair under a **new lock**. Formally the joint bar failed, so v3 stays unauthorized
regardless of row.

## Two apparatus caveats, disclosed — neither reverses a verdict

1. **`R2` was run with the June gate's own ungrouped CV on a sibling-structured corpus.** Random
   folds split siblings across train/test, so the lexical model partially matches *siblings*, not
   Worlds. Diagnostic with family-grouped folds: `world 0.6345 → 0.5521`, `foundation16
   0.3173 → 0.0521`, `drive 0.5001 → 0.4062`. **`R2` stands as FAIL under the frozen
   instrument** — and grouped world `0.55` vs chance `0.25` shows a real residual surface-world
   component — but the successor gate must group by family. My application error: the June corpus
   had no sibling structure; this one does.
2. **The judge here received a far thinner label key** (four register names + seven one-line
   wants) **than the judge that scored `84/84` drive on the leaky corpus** (full 28-cell
   canonical definitions). Two variables changed at once — items de-leaked AND taxonomy thinned —
   so `R3`'s level conflates them. The successor must judge with the full canonical definitions
   so the item effect is isolated. My design error, disclosed; the frozen bars failed as frozen
   and are not re-scored.

## Successor (new lock, not a re-run)

1. **Motive-block repair** per the frozen map: the drive's *want* must be made structurally
   explicit (obstacle and success condition keyed to the want, not just the World's location) —
   without reintroducing drive-topic vocabulary.
2. **Judge with the full canonical definitions** as the label key.
3. **Family-grouped folds inside the surface gate.**
4. Same 16 cells, same logging standard, same mechanical table.

## Status

```
V3_FULL_CORPUS_AUTHORIZATION   NOT GRANTED
corpus                          clean, transferable, World-recoverable, DRIVE-BLURRY
Gate 2                          OPEN at 0.38
```
