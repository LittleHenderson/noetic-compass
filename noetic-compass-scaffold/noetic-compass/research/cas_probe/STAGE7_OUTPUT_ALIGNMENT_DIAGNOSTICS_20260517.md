# Stage 7 Output-Alignment Diagnostics

**Status:** `STAGE7_SUBSPACES_NOT_OUTPUT_ALIGNED_ABOVE_RANDOM`

## Read

This diagnostic checks whether the CAS readout subspaces point toward Pythia's output head. It does not run generation and does not prove steering. It tells us whether the already-proven readout directions look like plausible output-writing directions or mostly like observer/readout directions.

## Principal-Angle Check

The unembedding numerical rank is `768` of hidden dim `768`. Degenerate: `True`.

Because Pythia's unembedding is numerically full-rank over the hidden dimension, principal angles to the full unembedding row space are all zero for any hidden-state subspace. The raw principal-angle test proposed in the roundtable is therefore degenerate for this model; the useful version is rank-matched energy/top-mode/logit-lens alignment against random controls.

## Task Diagnostics

| Task | Rank | Status | Unembedding Energy | Random Mean | Logit-Lens Energy | Random Mean |
|---|---:|---|---:|---:|---:|---:|
| drive | 6 | `OUTPUT_ALIGNMENT_NEAR_RANDOM` | 0.010268 | 0.007737 | 0.000965 | 0.002629 |
| interaction | 27 | `OUTPUT_ALIGNMENT_NEAR_RANDOM` | 0.040816 | 0.035258 | 0.018331 | 0.015076 |

## Implication

The tested Stage 7 readout subspaces are not specially aligned with the output head by these diagnostics. That explains why subtraction at layer 6 failed to steer generation and argues against more layer-6 free-generation hooks.
