# RESULT — CAS domain-precedence test on 20B (2026-08-18)

**Verdict: PARTIAL — present, but plausibly generic.** Unlike the involution test (clean
disconfirm) and flat detection (chance), the domain-precedence structure IS in the model:
the four domains are separable and line up in CAS's order P→C→E→O. But that order coincides
with a generic abstract→concrete gradient any LM would carry, and the strict test does not
single CAS out. So: presence, **not** established CAS-specificity.

## Test
On the real Condition-3 GPT-NeoX-20B activations (`condition3_gptneox20b_activations_20260531.npz`,
360 rows/domain, balanced), for the 4 domains P(Principled) C(Cognitive) E(Evaluative)
O(Operational): (a) are the domains separable? (4-way nearest-centroid, held-out balanced
acc, chance 0.25); (b) do the 4 centroids project **monotonically** in CAS order P→C→E→O
on the descent axis (O−P)?; (c) on the stricter "distance grows with order-gap" fit, does
CAS's order rank best among the 12 distinct orderings? Pure numpy; no model/GPU.
`cas_precedence_test.py`.

## Result
- **Domains are genuinely separable** — 4-way acc climbs from 0.250 (embeddings = chance)
  to **0.52–0.56** in deep layers (32–42). Real signal — this is the key contrast with the
  operator/involution collapse to chance.
- **CAS order P→C→E→O is monotone on the descent axis on 43/44 layers** (only the final
  layer 43 breaks, → PCOE). The free bit the test actually decides — is C nearer P and E
  nearer O — holds consistently.
- **Strict spacing test is good-but-not-unique:** CAS order is in the top-3 fits on 20/44
  layers; best layer 32 fit r=+0.597 ranks **2/12** (one non-CAS order fits slightly better
  even at the best layer). Layers 13–18 the fit inverts (negative).

## Read
- The clean positive: the **domain axis is a real geometric shape in the model**, and it runs
  in CAS's order. This is the first CAS-aligned relational signal that did **not** fail — and
  it lines up with the "shape of the thought" framing (the domain gradient is part of the shape).
- The honest deflation: P>C>E>O = most-abstract/foundational → most-concrete/operational.
  That is an **abstract→concrete gradient every language model already represents**, regardless
  of CAS. Finding the four domains ordered on it is expected with or without CAS. The strict
  test not singling CAS out (rank 2/12) is consistent with "generic gradient, CAS-compatible."
- So this is **presence, not CAS-specificity.** To make it CAS-specific you'd need a matched
  non-CAS 4-level abstractness taxonomy to do *worse* on the same fixtures (an MTC-style control).

## RPM — not tested here
These captures carry noetic/domain/element labels only — **no drive/RPM labels** — so the
RPM prerequisite-chain geometry (A0→D→W→P) cannot be tested on them. Separately, RPM's owner-
intended role is the **steering-back mechanism** (the diagnose→localize→repair loop), which is
a live-model white-box task, not a static-capture detection test. OPEN, needs different data
or the live repair loop.

## Where this leaves CAS-specificity (updated)
Four lines now:
- Flat 40-cell detection (leakage-controlled): **chance**.
- Involution pairs (^2↔^3 etc.): **disconfirmed** (least antipodal of 15).
- Domain precedence (P≻C≻E≻O): **partial — present but confounded with generic abstractness**.
- RPM chain: **not testable on these captures**.
The one CAS relation that survives is the domain gradient, and even that has a generic
explanation. CAS-specificity remains NOT LICENSED. The honest next lever is an MTC-style
abstractness control on the domain axis — the only place a positive CAS-specific signal
could still be won.

---

## CORRECTION appended 2026-08-19 — description corrected, NUMBERS UNAMENDED

Found during the audit of `docs/CAS_HARNESS_SPEC_SHEET.md`. Two descriptions in this
document do not match `cas_precedence_result.json`, which this correction leaves
byte-unchanged. Same rule as the D18 / D30 / D45 disclosures in the Component Atlas
arc: correct the description in place, in public, change no number.

**(i) The negative-fit layer range is understated by two layers, and omits one more.**
This document says the strict "distance grows with order-gap" fit inverts to negative
"on layers 13-18". The actual negative `cas_fit` layers in `cas_precedence_result.json`
are `[13, 14, 15, 16, 17, 18, 19, 20, 43]`. The correct statement is **layers 13 through
20, and again at layer 43**.

**(ii) The deep-layer separability band excludes two of its own layers.**
This document says 4-way `domain_sep4` reaches "0.52-0.56 in deep layers 32-42". Two of
the eleven layers named fall outside the band it states: `L35 = 0.51647513026651` is
below `0.52`, and `L42 = 0.4501382188394754` is far below the whole range. The correct
statement is **0.5165-0.5638 across layers 32-41, dropping to 0.4501 at layer 42**.

Exact `domain_sep4`, `L32` through `L42`:
`0.526927665254082`, `0.541678851836555`, `0.5466191907969111`, `0.51647513026651`,
`0.5290198786853538`, `0.5377906316966481`, `0.5500028320718944`, `0.5523746382582272`,
`0.5478589312727197`, `0.5637608036399963`, `0.4501382188394754`.

**Neither correction changes the verdict.** Domain precedence remains `PARTIAL` —
present, but confounded with a generic abstract-to-concrete gradient, ranking 2/12 on
the strict fit even at its best layer. If anything (i) mildly strengthens the
deflationary read, since the fit is negative on more layers than reported.
