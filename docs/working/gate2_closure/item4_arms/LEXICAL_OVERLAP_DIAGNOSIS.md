# Item 4 — why the definition-anchored instrument died, confirmed with no model at all

## The test

Take each arm's 40 definitions. Take the bank's held-out test items. Match each item to the
definition it shares the most **vocabulary** with — TF-IDF cosine over content words, IDF computed
within the arm's own 40 definitions. **No model. No hidden states. No GPU. No layers.**

## The result

| Arm | Pure lexical overlap | pythia-1b readout |
|---|---:|---:|
| A owner raw | **`0.4851`** | `0.1474` |
| B deployed | **`0.4804`** | `0.1538` |
| D compact CAS | `0.1187` | `0.0374` |
| E non-TKS | `0.0235` | `0.0408` |
| F null | `0.0051` | `0.0097` |

Chance is `0.025`.

## What this establishes

1. **The arm ordering is fully reproduced by word matching.** A ≈ B ≫ D ≫ E > F, identical shape,
   with no model involved. The ordering therefore carries **no evidence** about semantic quality in
   any model — it is explained entirely by shared vocabulary between each arm's definitions and the
   bank's glosses.

2. **The model UNDERPERFORMS word-counting by roughly 3×.** `pythia-1b` scored `0.1474` where a
   bag-of-words scored `0.4851` on the identical task. Whatever the definition-anchored readout was
   doing, it was a worse version of string matching.

3. **It explains every control failure at once.** C1 (scaffold mismatch), C2 (frame mismatch) and C3
   (position break) all left the result nearly intact because vocabulary overlap is invariant to
   framing. A readout that survives having its frame, scaffold and position destroyed was never
   reading the model.

4. **The cause is benign and structural, not misconduct.** The TKS definitions and the bank's glosses
   were authored by the same project, about the same 40 concepts, 17 days apart. Of course they share
   words. The non-TKS ontology and the nulls do not. No one put a thumb on the scale; the instrument
   simply measured the wrong thing.

## What it means for the next instrument

Any future item-4 design **must** report this lexical baseline alongside its headline, and must beat
it. This is the same rule the project already imposes on character n-gram controls for hidden-state
claims — it was simply never applied to a *definition-to-item* readout, because no one had noticed
that a definition and an item can be compared as strings.

The owner's question — does original TKS wording preserve more semantic signal than compact CAS —
remains **open and untested**. It is not refuted. Two instruments have now failed to test it, both
for the same reason: they were solvable by vocabulary.

## Status

`NOT LICENSED / FAMILY CLOSED / QUESTION STILL OPEN`

---

## Addendum — the exact leak, quantified

**39 of 40 classes have bank items containing a word that appears in that class's definition and in
no other class's definition.** A unique giveaway token per class. The task is solvable by spotting one
distinctive word; no semantics required.

Vocabulary overlap with the bank (328 content words):

| Arm | Arm vocab | Shared with bank | % of arm in bank |
|---|---:|---:|---:|
| A owner raw | 464 | 170 | 36.6% |
| B deployed | 462 | 171 | 37.0% |
| D compact CAS | 62 | 11 | 17.7% |
| E non-TKS | 468 | 55 | 11.8% |
| F null (permutation of A) | 464 | 170 | **36.6%** |

**Arm F is the control that proves it.** F1 is a *permutation* of Arm A's definitions — byte-identical
vocabulary, same 36.6% overlap with the bank — but the class assignment is scrambled. It scores
`0.0097`, at chance, against A's `0.1474`. Same words, wrong assignment, no signal.

So what the readout measures is precisely **which distinctive word belongs to which class**, and
nothing else. Arms A and B win because their definitions were written by the people who later wrote
the bank's glosses; D and E lose because they use different words. Arm F loses despite identical
vocabulary because the word→class mapping is broken.

## The hard constraint this imposes

**This bank cannot test the owner's question, by any instrument.** As long as the evaluation items and
the definitions under test share authorship, a per-class giveaway token exists and any definition-to-item
comparison will find it before it finds semantics.

Instrument three therefore requires **either**:
- an evaluation bank whose glosses were authored independently of every arm (no shared vocabulary
  lineage), **or**
- a task where the definition is never compared to the item text at all — e.g. definitions used only
  to shape a representation that is then tested on labels the vocabulary cannot reach.

Choosing between those is a design decision that belongs to the owner, not the assistant. Both are
substantial builds. Neither is attempted here.
