# GATE 2 ITEM 4 — PRE-REGISTRATION v3 (`TKS-HELDOUT-COMPOSITION-v3`)

**Written and committed BEFORE any v3 result exists.**
**Supersedes** v1 (`TKS-DEFCTX-40E-PRIMARY-v1`) and v2 (`TKS-DEFCTX-40E-SPLITLAYER-v2`), both of which
remain **permanently NOT LICENSED** and are retained unedited.

---

## 1. Why the previous two instruments died, in one line

Both asked *"can a model match a sentence to its definition?"* — a question answerable by **vocabulary
overlap**. A bag of words scored `0.4851` where `pythia-1b` scored `0.1474`, and **39 of 40 classes
carried a word unique to their own definition**. The instruments measured which distinctive word sat
with which label. They never reached the question.

## 2. The owner's actual claim, stated testably

TKS definitions are **derived**, not stated. A cell is what you get by composing its World with its
Noetic, and the composition **generates entailments the parts did not list**:

> `B5` = Mental × Female. Female = *contains / is pregnant with* → to contain, it **must be open** →
> in the mental world, **open-mindedness**. Pregnant → creation → **mental creativity**.

Verified against the real artifact — `B5` reads *"right brain thinking, open mindedness, imaginative,
creative, the subconscious mind"*, and the ^5 row carries the same receive/contain/nurture thread
across worlds (`A5` spiritual womb; `C5` unconditional acceptance; `D5` receptacle, soil for seed).

**The compact CAS arm is built by concatenation, not composition** — verified: every ^5 cell opens with
the identical string *"A Mind impregnated with an Idea…"* and differs only in a stapled world clause.
`B5` compact reads *"Explicit, sequential, logical, reason-based"* — not a vaguer `B5`, close to its
opposite.

**Testable form:** a derived definition system can reconstruct a cell it was never shown. A
concatenated one cannot.

## 3. Design — leave-one-out compositional reconstruction

For each of the 40 cells `c = (World W, Noetic N)`:

1. **Delete `c` entirely.** Its definition text, its title, its code — no arm sees any of it.
2. **Compose a substitute anchor** from what remains, using the fixed rule
   `u_c = normalize( mean(other cells in row N) + mean(other cells in column W) - global mean )`.
   This is plain additive composition. No fitted parameters, identical for every arm.
3. **Score** the held-out class's test items against the full anchor set (39 real + 1 composed).

Report reconstruction accuracy over all 40 leave-one-out folds. **Every cell is held out exactly
once** — there is no cell selection to cherry-pick.

### Why the vocabulary leak cannot operate here

`B5`'s giveaway words (*right brain*, *open mindedness*, *subconscious*) live in `B5`'s definition,
which **no arm ever sees** in `B5`'s fold. A word-counter has nothing to count. It must score at
chance **by construction** — the first time in this whole effort that a control is guaranteed fair
rather than hoped to be.

## 4. Frozen acceptance criteria

| # | Criterion | Bar |
|---|---|---|
| V1 | TKS arm reconstruction above chance | `> 0.025`, permutation `p < 0.01` |
| V2 | TKS arm beats compact CAS arm | margin `>= 0.10`, group-bootstrap CI lower `> 0` |
| V3 | **Lexical control at chance** | `<= 0.05` — *if it is not, the test is void, not passed* |
| V4 | Nulls at chance | shuffled-label and random-anchor `<= 0.05` |
| V5 | Not driven by one cell | at least 25% of the 40 folds individually correct for TKS |

**V3 is the honesty gate.** If word counting can reconstruct held-out cells, this instrument has the
same disease as the last two and must be reported dead — not licensed.

## 5. Pre-committed consequences

- **All criteria pass** → a scoped licensed claim: *on this model and this fixture, TKS definitions
  support compositional reconstruction of unseen cells and compact CAS definitions do not.*
- **V1 or V2 fails** → the owner's claim is **not supported by this instrument**. Reported as a
  negative. Not refuted — the model may simply be too small to compose.
- **V3 fails** → instrument void, same disease, family closed.
- **No third attempt at this design.** One run, one verdict.

## 6. What this cannot license

No claim about human comprehension, no claim beyond the tested model, no product `ACCEPT`. It tests
one property — whether the definition system generates — on one small model.

## 7. Status

`LOCKED / COMMITTED BEFORE RESULTS EXIST / NOTHING LICENSED`

Model: `EleutherAI/pythia-1b`. Bank: repaired 40-Element holdout (5,920 unique, zero split leakage).
Arms: A (owner raw TKS), D (compact CAS), plus lexical, shuffled-label and random-anchor controls.
