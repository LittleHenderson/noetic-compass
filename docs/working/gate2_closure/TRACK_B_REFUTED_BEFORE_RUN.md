# Track B (bank-free grid geometry) — REFUTED BY ITS OWN CONTROL, BEFORE ANY GPU RUN

**Status:** `NOT RUN / REFUTED AT DESIGN TIME / NO COMPUTE SPENT`

## The proposal

Test whether the 40 definitions exhibit the 10x4 grid (10 Noetics x 4 Worlds) in a model's
embedding geometry — row siblings closer to each other than to unrelated cells, likewise columns.
Attraction: needs no evaluation bank and no independent authors, so it sidesteps the
shared-authorship deadlock that killed six instruments.

## Why it cannot work

The grid is already fully recoverable from **raw word overlap, with no model at all.**

Primary metric — `sibling@3`: for each cell, rank the other 39 by similarity; what fraction of the
top 3 are row-or-column siblings? Each cell has 12 siblings among 39, so **chance = `0.3077`**.

| Representation | sibling@3 |
|---|---|
| chance | `0.3077` |
| **TKS, pure word overlap (no model)** | **`0.9250`** |
| **compact CAS, pure word overlap (no model)** | **`1.0000`** |

Corroborating measure — Jaccard grid lift over unrelated pairs: TKS `7.69x` (row) / `7.95x` (col);
compact CAS `5.01x` / `6.96x`.

**Compact CAS sits exactly at the ceiling.** A model cannot exceed `1.0000`, so the comparison arm
is unbeatable by construction. TKS at `0.9250` leaves `0.075` of headroom — too thin to carry a
claim, and any excess would be indistinguishable from noise on 40 cells.

## Why the vocabulary recovers the grid so perfectly

It is structural, not accidental:

- **compact CAS** is built by concatenation — every `^5` cell opens with the identical string
  *"A Mind impregnated with an Idea, the Ideas a Mind is composed of"*, and every Mental cell ends
  with the identical world clause. Word overlap reconstructs the grid **exactly**, because the grid
  *is* the string-assembly rule.
- **TKS** genuinely shares vocabulary along both axes — the `^5` row carries
  *contains / receives / nurtures* across worlds; the Mental column carries *mind / thinking /
  conscious*.

## The finding this yields — real, and worth stating

**The 10x4 grid structure of these definitions is lexically encoded.** A word counter recovers it at
`0.9250`–`1.0000` against a `0.3077` chance baseline. That is a genuine characterisation of the
artifacts, obtained at zero compute cost.

It does **not** show the definitions are *merely* vocabulary. It shows that *this measurement* cannot
see past vocabulary to whatever else may be there — the same wall all six instruments hit.

## Decision

**Not run.** A GPU experiment whose control is at ceiling cannot produce an interpretable number.
Running it would have produced a figure that looked like evidence and was not — the exact failure
mode of v5, caught this time at design rather than after.

The independently-authored bank remains the sole path to Gate 2 item 4.
