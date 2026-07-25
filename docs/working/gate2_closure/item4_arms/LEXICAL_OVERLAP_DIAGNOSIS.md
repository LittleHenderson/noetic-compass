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
