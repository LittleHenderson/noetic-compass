# TRACK B (repaired) — PRE-REGISTRATION `GRID-LEXICAL-REVERSAL-v1`

**Committed BEFORE the model is run.** The lexical control below was measured first and is reported
here as the bar, not as a result.

## The repair

Track B as delivered had **no lexical control**. Run as-is it would have found grid structure in the
embeddings and reported success — while a word counter already achieves, on Track B's own metrics:

| Metric (their code, bag-of-words input) | TKS | compact CAS |
|---|---|---|
| `neighbor_rank` / sibling@3 (chance `0.3077`) | `0.9250` | `1.0000` |
| `crossval_reconstruction` | `0.3511` | `0.9850` |
| `combined_grid_score` | `0.3050` | `0.5905` |

Compact CAS is at or near ceiling on every one. A model cannot beat `1.0000`, so "does the grid appear
in the embeddings" is unanswerable.

## What makes a fair test possible

**The lexical confound ranks compact CAS ABOVE TKS** — `0.9850` vs `0.3511` on reconstruction, a gap of
`+0.634` in compact's favour. This is structural: compact is built by concatenation, so word counts
rebuild it almost perfectly, while TKS's richer wording is harder to rebuild lexically.

Therefore **a model result showing TKS ABOVE compact is a reversal of the lexical ordering**, and
vocabulary overlap cannot produce it — the confound points the other way. This is the first design in
this effort where the leak works *against* the hypothesis rather than for it.

## Frozen criterion

| # | Criterion | Bar |
|---|---|---|
| R1 | **Reversal** | model `crossval_reconstruction`: TKS **>** compact CAS |
| R2 | Reversal is material | margin `>= 0.05` |
| R3 | Not noise | permutation `p < 0.01` on the TKS-minus-compact difference |
| R4 | Lexical ordering confirmed opposite | lexical compact **>** lexical TKS (measured: `+0.634`) — already true |
| R5 | Metric content-dependent | permutation `p` strictly inside `(floor, 1.0)`; not both arms identical |

## Pre-committed consequences

- **R1–R3 pass** → the model's geometry ranks TKS above compact *against* the lexical gradient. That is
  evidence of structure beyond vocabulary, scoped to this model and these definitions.
- **R1 fails (compact >= TKS)** → the model reproduces the lexical ordering. No evidence of anything
  beyond vocabulary, and the definition-geometry approach is finished.
- **R5 fails** → VOID.

**A pass licenses only:** *"on `pythia-1b`, TKS definition geometry is better grid-reconstructible than
compact CAS geometry, in the direction opposite to the lexical baseline."* It does **not** license any
claim about human comprehension, about the definitions being "better", or about Gate 2's full A/B —
that still needs the independently-authored bank.

## Status

`LOCKED / COMMITTED BEFORE MODEL RUN / NOTHING LICENSED`
