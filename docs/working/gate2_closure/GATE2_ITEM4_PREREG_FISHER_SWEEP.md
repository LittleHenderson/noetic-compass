# ITEM 4 — `FISHER-RAO-TEMPERATURE-SWEEP-v1`

**Committed BEFORE the run. Owner-authorized after I declined to run it unilaterally.**

## Disclosure, stated first

The tenth instrument (`FISHER-RAO-SIMPLEX-v1`, `7e806675`) came back `VOID_SATURATED`: all three arms
scored under `0.018`, far inside the `0.05` floor guard. Diagnosis: the softmax projection at
`temperature = 1.0` over cosine similarities of near-parallel embeddings produces near-uniform
distributions, so geodesics between them collapse to near zero.

**Changing that temperature after seeing a void result is post-hoc parameter adjustment.** I said so and
declined to do it unilaterally. The owner has authorized it, noting that human authors are unavailable,
so mathematical instruments are the only avenue currently open. This document exists so no later reader
can mistake this for a fresh independent test.

## The design that makes it honest

**Do not pick a temperature. Sweep a pre-declared grid and report every point.**

Grid, fixed here before running: `T ∈ {0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0}`.

Every temperature's full results are reported — no selection, no best-of. A reversal appearing at one
isolated setting is noise. A reversal holding across most of the usable range is a finding. This turns
a tunable knob into a robustness check, which is the only form in which a post-hoc parameter change can
carry evidential weight.

## Frozen criteria

| # | Criterion | Bar |
|---|---|---|
| S1 | Usable range exists | `>= 3` temperatures pass the non-saturation guard (no arm within `0.05` of `0` or `π`) |
| S2 | **Reversal is robust** | `d(TKS) < d(compact)` at `>= 2/3` of usable temperatures |
| S3 | TKS beats its own shuffled control | `d(TKS) < d(shuffled)` at `>= 2/3` of usable temperatures |
| S4 | Significant at the median usable temperature | permutation `p < 0.01` |
| S5 | Lexical gradient confirmed opposite | already measured: `+2.15` favouring compact |

**S2 is the load-bearing one.** The lexical baseline puts compact far ahead (`0.316` vs `2.467`), so a
model reversal runs against a strong confound and cannot be produced by shared vocabulary.

## Pre-committed consequences

- **S1–S4 pass** → first scoped positive in eleven attempts, and it is robust to the free parameter
  rather than dependent on it.
- **S1 fails** → the projection cannot be rescued by temperature at all. Instrument dead.
- **S2 fails** → the model reproduces the lexical ordering across the range. **Definitive negative.**
  The definition-comparison effort ends, and the independent bank becomes the sole path.
- **ABSOLUTELY FINAL. No twelfth instrument, no further parameters.** Whatever the sweep returns is the
  last word on item 4's experimental phase.

## What a pass could not license

Nothing about human comprehension, nothing beyond `pythia-1b`, and **not** Gate 2 item 4's A/B, which
still requires an independently-authored bank. A pass licenses only: *TKS definition geometry
reconstructs better than compact CAS under Fisher-Rao, robustly across projection temperature, against
the lexical gradient.*

## Status

`LOCKED / COMMITTED BEFORE RESULTS EXIST / NOTHING LICENSED`
