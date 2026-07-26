# Quantum Mutual Information (entanglement.py) — REFUTED BY ITS OWN GUARD, BEFORE ANY GPU RUN

**Status:** `NOT RUN / V2 GUARD FIRED ON THE CPU PRECHECK / NO COMPUTE SPENT`

## The proposal

Treat the 40-cell Gram matrix as a density matrix on `C^4 ⊗ C^10` (Def 20.36 / Thm 20.38 of the
project's own Chapter 20 — provenance VERIFIED at `full_corrected.txt:16132/:16165`), take partial
traces over Worlds and Noetics, and measure quantum mutual information `I(World;Element)`.
Predictions as handed: TKS `I > 0` (entangled), compact `I ≈ 0` (factorizable), shuffled `I ≈ 0`.
Guard V2: lexical TKS `I` must exceed lexical compact `I`.

`entanglement.py` is real, parses clean, and implements the mathematics correctly (partial traces via
explicit index lookup — verified). One defect noted: its shuffle arm used retired seed `20260725`.

## The mandatory CPU precheck (design law L2) — measured, 50 fresh shuffle seeds `1001..1050`

| Arm | lexical `I(World;Element)` | proposal predicted |
|---|---|---|
| TKS | `0.047786` | "> 0, largest" — **it is the SMALLEST** |
| compact CAS | `0.209888` | "≈ 0" — **4.4× larger than TKS** |
| shuffled TKS (mean of 50) | `0.158546` (range `0.1437–0.1683`) | "≈ 0, destroyed" — **3.3× larger than real TKS** |

**V2 fires: `I_lex(TKS) > I_lex(compact)` is FALSE by a factor of 4.4.** By the design's own declared
guard, the run is void before launch. E5's amplification bar also becomes incoherent: the lexical
delta is `−0.162`, so "model delta must exceed lexical delta" would be satisfiable by any model result
better than a large negative number.

## Why the predictions inverted — and the one real observation this yields

Under QMI-on-Gram, **low mutual information means factorizable** — clean row-plus-column structure.
The real TKS grid aligns vocabulary along rows (`contains/receives` across the ^5 row) and columns
(`mind/thinking` down the Mental column), which makes the World and Noetic axes nearly INDEPENDENT:
`I = 0.048`. Scrambling the grid destroys that alignment and MIXES the axes: every one of 50 fresh
scrambles has higher `I` (minimum `0.1437`, 3× the real grid). Compact's boilerplate produces strong
block correlations and the HIGHEST `I` of all.

So the honest lexical observation — recorded, CPU-only, not licensed —
is that **the real TKS grid is more factorizable than 50/50 of its scrambles**: yet another
non-arbitrariness signal, consistent with the licensed `SCRAMBLE-NULL-COMPLETION-v1` result, but in
the OPPOSITE direction to the proposal's entanglement story. On this metric, compositionality (as the
proposal operationalised it) is not what distinguishes the real grid; orthogonal factor structure is.

## Decision

Not run. A GPU result could not be licensed under a design whose own guard fails on the precheck, and
whose sign conventions are refuted in the only channel measurable in advance. This is the third
GPU run killed by the CPU-precheck discipline (Track B, adaptive-τ, this).

Fourteen designs considered; thirteen runs executed; one licensed. Gate 2 remains OPEN at `0.38`.
