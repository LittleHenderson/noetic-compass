# PRE-REGISTRATION — `SPEC-AUTHORED-SCENARIOS-v1`

**Committed BEFORE any scenario is generated.**
**Date:** 2026-07-27
**Gate 2 status:** OPEN at `0.38`

---

## The question

`JUDGE-POSITIVE-CONTROL-v1` (`d755665b`) established:

- the judge harness is sound (`T0 = 28/28` on verbatim definitions), and
- the existing authored scenarios carry **no recoverable signal** — `12/280 = 0.0429` against
  chance `0.0357`, one-sided binomial `p = 0.3011`.

Those scenarios were written by `models/gemini-2.5-flash-lite` under a thin authoring prompt.
The owner has since supplied a 27-section authoring specification ("Scenarioizing the 28 Tootra
Foundations") requiring four aligned anchors, a recoverable causal spine, contrastive authoring
against nearest confusables, a lexical-distance requirement, and a 12-point acceptance rubric.

**Question:** does the authoring protocol account for the missing signal?

## Why this is a clean test

The baseline already exists and used the **same author model**. Holding the model fixed at
`models/gemini-2.5-flash-lite` and changing only the protocol isolates the protocol.

| | Author model | Protocol | Result |
|---|---|---|---|
| Baseline (`T2`, already run) | `gemini-2.5-flash-lite` | thin prompt | `0.0429` (`p = 0.3011`) |
| This run | `gemini-2.5-flash-lite` | owner's 27-section spec | — |

If a stronger author model were used instead, a positive result would be ambiguous between
"better spec" and "better writer." It is therefore **frozen to flash-lite**.

## Materials

- `28` foundations × `3` scenarios = **`84` items**. Levels `S1` and `S2` only; the spec forbids
  `S3` until `S1`/`S2` pass recovery tests.
- Targets are addressed by **TKS legacy codes** (`1a`–`7d`), mapped to `F`-codes via the canon
  file's `legacy_tks_id`. **One convention throughout** — items authored against TKS semantics,
  judged against the TKS key. This is the defect that voided `SMALL-MODEL-SEMANTIC-MATCH-v1`
  (`cb0eaffd`) and it is not repeated.
- Judge: `models/gemini-2.5-flash`, TKS 28-definition choice set — **the exact configuration that
  scored `T0 = 28/28`**.

## Surface controls — the fair comparison

Computed on the identical `84` items against the `28` TKS definitions:

- **char 3–5-gram TF-IDF**, cosine (mandatory char-level control)
- **word TF-IDF**, cosine

`best_surface = max(char, word)`.

---

## Frozen criteria

| # | Criterion | Bar |
|---|---|---|
| `P1` | **Beats the thin-prompt baseline** | `accuracy - 0.0429 >= 0.15` AND bootstrap 95% CI of the difference excludes `0` |
| `P2` | **Above chance** | one-sided binomial `p < 0.01` against `1/28` |
| `P3` | **Beats surface** | `accuracy - best_surface >= 0.10` |
| `P4` | **No degenerate collapse** | no single foundation predicted for `> 30%` of items |
| `P5` | **Not lexically solvable** | mean word-Jaccard between each scenario and its target definition `<= 0.15` |

Bootstrap: `10,000` percentile iterations over the `84` items. At `n = 84` the interval is wide
and **will be reported at full width**.

---

## Pre-committed consequences

- **`P2` FAILS** → `SPEC_INSUFFICIENT`. The protocol does not close the gap; the difficulty is
  not (only) authoring discipline. Per the owner's §26, this still does **not** establish that the
  foundations are unrecoverable — it removes one of six candidate causes.
- **`P2` passes, `P3` FAILS** → `NOT_LICENSED_LEXICAL`. Signal is present but a bag of characters
  finds it too. Under the standing char-level rule this licenses nothing.
- **`P2` passes, `P5` FAILS** → `VOID_LEAKAGE`. The spec's §12 lexical-distance requirement was
  not met and the items are solvable by phrase matching.
- **`P4` FAILS** → `VOID_DEGENERATE`.
- **`P1`, `P2`, `P3` PASS with `P4`, `P5` clean** → `LICENSED`, ceiling below.

---

## Ceiling on what a PASS licenses

> *"Scenarios authored under the owner's specification by `models/gemini-2.5-flash-lite` carry
> recoverable foundation signal, above chance and above word- and character-level surface
> baselines on the same items, where scenarios by the same model under a thin prompt did not
> (`p = 0.3011`). The deficit was in authoring protocol."*

It licenses **nothing** about: TKS versus CAS definition quality (no arm comparison here), any
small model (the judge is `gemini-2.5-flash`), human performance, or product capability. **It
would not close Gate 2**, whose wording requires a small model.

## Deviations from the owner's spec, disclosed

- **§19 blind self-classification is recorded but NOT used as a gate.** The author knows what it
  meant, which is the shared-authorship confound that defeated sixteen prior instruments. It is
  logged as metadata; the independent judge is the only gate. This follows the spec's own Phase 5.
- **§14 minimal-contrast partners are generated and stored but not scored in the primary
  endpoint.** They double the item count and their analysis is a separate design.
- **§18 self-scoring rubric output is recorded, not enforced.** Author-side acceptance filtering
  would let the generator select its own test set.

## Why this cannot manufacture a favourable result

- The baseline (`0.0429`) is **already committed and published**; it cannot be renegotiated.
- The author model is pinned to the weaker one used for the baseline.
- Surface controls take the **max**, favouring the control.
- `P5` can VOID the run on lexical leakage regardless of accuracy.
- Author self-assessment is excluded from every gate.

## Status

`LOCKED / COMMITTED BEFORE GENERATION / NOTHING LICENSED`
