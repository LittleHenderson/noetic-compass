# ITEM 4 — PRE-REGISTRATION `FISHER-RAO-SIMPLEX-v1`

**Committed BEFORE the run.** Tenth instrument, owner-authorized after the family was closed at nine.
All prior instruments remain NOT LICENSED / VOID and are retained unedited.

## Why a tenth instrument is justified

Instruments 8 and 9 were uninterpretable for a *diagnosed* reason, not bad luck: **cosine on
high-dimensional embeddings saturates.** Shuffled definitions — with grid positions randomly
reassigned, so no compositional structure whatsoever — scored `0.993` at layer 1. A metric returning
`0.993` on scrambled data cannot distinguish structure from its absence.

The Fisher-Rao geodesic on the open probability simplex `Δ°₃₉` is a different measurement, not a
reskin. Its metric `g_p(u,v) = Σ(u_k·v_k / p_k)` **upweights small components** via `1/p_k`, and the
geodesic `d(p,q) = 2·arccos(Σ√(p_k·q_k))` is an angle on the sphere reached by `p → √p`, which
stretches the tail apart. Vocabulary overlap concentrates in the *dominant* components; any
compositional signal plausibly lives in the *tail*.

**Measured, before this run, on lexical features only** (lower = better reconstruction; max = `π`):

| Arm | real | shuffled null | separation |
|---|---|---|---|
| TKS | `2.4674` | `2.8757` | `+0.4083` |
| compact CAS | `0.3158` | `2.2304` | `+1.9145` |

Two facts follow, and they are the entire reason to proceed:
1. **The metric does not saturate.** Values span `0.32`–`2.88` of a possible `3.14`, and the shuffled
   null separates cleanly on both arms. The defect that voided instruments 8 and 9 is repaired.
2. **The lexical gradient runs hard toward compact** (`+2.15` in compact's favour). So a model result
   with TKS *ahead* of compact is a reversal against a strong confound — and unlike the cosine
   reversal test, this metric has dynamic range to express it.

## Design

Identical pipeline to the reversal test (`pythia-1b`, layer 12, 4 frames, last-token, 40 definitions
per arm). Only the representation and metric change:

1. Project each definition's hidden state to the open simplex `Δ°₃₉`: softmax over its cosine
   similarities to the 40 anchor directions, floored strictly positive (`p_k > 0`, `Σp_k = 1`) per
   CLAUDE.md Correction 4.
2. Leave-one-out: compose the held-out cell from row and column siblings **in `√p` space** (the sphere
   the simplex maps to), then renormalise back to the simplex.
3. Score by geodesic distance `d(p,q) = 2·arccos(Σ√(p_k·q_k))` to the true cell. Lower is better.

Arms: TKS, compact CAS, **shuffled TKS** (identical text, scrambled grid assignment — the control that
exposed instrument 9's defect and is mandatory here).

## Frozen criteria

| # | Criterion | Bar |
|---|---|---|
| F1 | TKS beats its own shuffled control | `d(TKS) < d(shuffled)` by `>= 0.10` |
| F2 | **Reversal** | `d(TKS) < d(compact)` — model reverses the lexical ordering |
| F3 | Reversal is significant | permutation `p < 0.01` on the TKS−compact difference |
| F4 | Lexical gradient confirmed opposite | already measured: `+2.15` favouring compact |
| F5 | **No saturation** | no arm within `0.05` of `0` or of `π`; arms not identical within `1e-6` — else VOID |

## Pre-committed consequences

- **F1–F3 pass** → first scoped positive in ten attempts: *on `pythia-1b`, TKS definition geometry
  reconstructs better than compact CAS under Fisher-Rao, against the lexical gradient.*
- **F2 fails** → the model reproduces the lexical ordering. Negative. **The definition-comparison
  effort is over**, and the independently-authored bank is the sole path without qualification.
- **F5 fails** → VOID.
- **FINAL INSTRUMENT. No eleventh.** Whatever this returns closes item 4's experimental phase.

## What a pass could not license

Nothing about human comprehension, nothing beyond this model, and **not** Gate 2 item 4's A/B — that
still requires the independent bank. A pass licenses only the scoped geometry statement above.

## Status

`LOCKED / COMMITTED BEFORE RESULTS EXIST / NOTHING LICENSED`
