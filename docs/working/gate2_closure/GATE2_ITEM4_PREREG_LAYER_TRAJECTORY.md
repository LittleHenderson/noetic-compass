# ITEM 4 — PRE-REGISTRATION `LAYER-TRAJECTORY-v1`

**Committed BEFORE the run.** Ninth instrument. Prior eight are NOT LICENSED / VOID, retained unedited.

## Hypothesis

Vocabulary is available at layer 0. Semantic integration is not. So if TKS definitions carry structure
beyond their words, the model's ability to reconstruct a held-out cell from its row and column siblings
should **climb with depth** for TKS, while compact CAS — trivially reconstructible from tokens alone —
starts high and stays flat.

Measured anchor points (layer 12): TKS `0.979112`, compact `0.997738`. Lexical (no model, no layers):
TKS `0.351074`, compact `0.984950`. **The lexical confound favours compact at every layer**, so a TKS
climb toward compact cannot be produced by shared vocabulary — the confound pushes the other way.

## The confound this design MUST control, and how

**Depth alone smooths representations.** In any transformer, deeper layers are more contextually mixed,
so an additive row+column reconstruction tends to improve with depth *for any text whatsoever*.
Compounding this, compact starts near ceiling (~`0.90`) and therefore *cannot* climb much — so
"TKS climbs more than compact" is partly guaranteed by regression to ceiling.

**Control: a SHUFFLED-TKS arm.** Identical TKS text, identical richness, identical starting position —
but the definition-to-grid-position assignment is randomly permuted, destroying compositional structure
while preserving every lexical and stylistic property. It starts low, exactly like real TKS, so it has
the same headroom.

- If shuffled-TKS **also climbs**, the climb is generic depth-smoothing and the instrument is **VOID**.
- Only a TKS climb that shuffled-TKS does **not** reproduce is evidence of anything.

This is the control the proposal omitted, and without it a positive result would be uninterpretable.

## Frozen criteria

| # | Criterion | Bar |
|---|---|---|
| T1 | TKS climbs | Spearman r(layer, reconstruction) `> 0`, `p < 0.05` |
| T2 | TKS climbs more than compact | TKS slope − compact slope `>= 0.02` per layer |
| T3 | **Shuffled-TKS does NOT climb** | shuffled slope `< 0.5x` TKS slope — **else VOID** |
| T4 | Lexical baseline is flat and favours compact | already measured: `-0.634` in compact's favour |
| T5 | Metric content-dependent | no two arms identical within `1e-6` at any layer |

## Pre-committed consequences

- **All pass** → scoped positive: on `pythia-1b`, TKS grid-reconstructability increases with depth in a
  way that shuffled TKS does not, against the lexical gradient. Evidence of integration beyond
  vocabulary, for this model and these definitions only.
- **T1 or T2 fails** → no trajectory effect. Negative.
- **T3 fails** → VOID. The climb is depth-smoothing, not semantics.
- **FINAL INSTRUMENT.** Win, lose, or void, item 4 ends here until an independently-authored bank exists.

## What a pass would NOT license

Nothing about human comprehension, nothing beyond this model, and **not** Gate 2 item 4's A/B
comparison — that still requires the independent bank. A pass would license only: *TKS definitions are
integrated with depth differently from a shuffled control.*

## Status

`LOCKED / COMMITTED BEFORE RESULTS EXIST / NOTHING LICENSED`
