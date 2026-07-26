# ITEM 4 — `OUTPUT-DISTRIBUTION-SIMPLEX-v1` (Option 3)

**Committed BEFORE the run. Owner-directed.** Twelfth instrument.

## The idea, and why it is structurally different

Every previous instrument asked *"how similar are these definition embeddings?"* and then had to
**invent a projection** to reach the simplex. That invention is what killed instrument ten: a softmax
over near-parallel vectors produced near-uniform distributions and the geodesic collapsed.

This instrument asks a different question: **how does each definition shape the model's own output?**
For each definition, the model's next-token probability distribution is read directly from its output
layer. That is **already a probability distribution on the simplex** — strictly positive, sums to one,
by construction. No projection is invented, so the failure mode of instrument ten cannot recur.

It is also downstream of processing rather than upstream: the output distribution reflects what the
model *predicts follows* from the definition, not merely which words the definition contains.

## Declared deviation from the proposal

The source proposal described a **Jacobian** — `∂(output)/∂(input)`. I am using the **output
distribution itself**, not its gradient. Reasons, stated before results:

1. The output distribution is already on the simplex; a gradient is not, and would need its own
   invented projection — reintroducing exactly the defect this design exists to avoid.
2. Adding an unvalidated autograd path as the deciding component of a gate is the v5 failure mode.

This is a **weaker** instrument than a true Jacobian lens and should not be described as one.

## Design

For each of the 40 cells, in each arm:
1. Feed the definition under 4 fixed frames; read the next-token distribution `p_c` over the full
   vocabulary from the output layer; average over frames; renormalise to the open simplex.
2. Leave-one-out: compose the held-out cell in `√p` space from its row and column siblings,
   renormalise back to the simplex.
3. Score by Fisher-Rao geodesic `d(p,q) = 2·arccos(Σ√(p_k·q_k))`. Lower is better.

Arms: **TKS**, **compact CAS**, **shuffled TKS** (identical text, scrambled grid assignment).

## Frozen criteria

| # | Criterion | Bar |
|---|---|---|
| O1 | **Reversal** | `d(TKS) < d(compact)` — the lexical gradient favours compact by `+2.15`, so a reversal cannot be produced by shared vocabulary |
| O2 | TKS beats its own shuffled control | `d(TKS) < d(shuffled)` |
| O3 | Significant | permutation `p < 0.01` on the TKS−compact difference |
| O4 | **No saturation** | no arm within `0.05` of `0` or of `π`; arms not identical within `1e-6` — else VOID |
| O5 | Lexical gradient confirmed opposite | already measured: `+2.15` favouring compact |

## Pre-committed consequences

- **O1–O3 pass with O4 clean** → first scoped positive in twelve attempts.
- **O1 fails** → the model's output distributions reproduce the lexical ordering. Negative.
- **O4 fails** → VOID, and the simplex approach is exhausted in both projections (invented and native).
- **ABSOLUTELY FINAL.** No thirteenth instrument.

## What a pass could not license

Nothing about human comprehension, nothing beyond `pythia-1b`, and **not** Gate 2 item 4's A/B, which
still requires an independently-authored bank.

## Status

`LOCKED / COMMITTED BEFORE RESULTS EXIST / NOTHING LICENSED`
