# PRE-REGISTRATION — `USORA_FOUNDATION_COMPOSITION_V1`

**Status:** `PROPOSED MEASURABLE EXTENSION — NOT CANONICAL TOOTRA LAW`
**Date:** 2026-07-27 · **Gate 2:** OPEN at `0.38`
**Separate artifact.** Does not modify `TKS_28_FOUNDATION_BENCHMARK` or any running corpus.

---

## 1. What is canonical here and what is not

**Canonical (CAS v7.6, project instructions):** recipe notation
`Θ(Ω) = a₁·X₁ + a₂·X₂ + … → Ω`, weighted prerequisite composition, and the open probability
simplex `Δ°₃₉` in which no state is exactly `0` or `1`.

**NOT canonical:** *percentage-of-World scenario classification*. Applying recipe weights to
**incident classification** is a proposed extension. It is registered under its own name and does
**not** alter the 28 Foundations.

## 2. Three quantities that must never merge

| Quantity | Example | Meaning |
|---|---|---|
| **recipe weight** | `2.0` | raw ingredient strength inside `Θ` |
| **normalized composition** | `0.50` | weight ÷ total weight |
| **model confidence** | `0.87` | how sure the model is about its own estimate |

`"65% Spiritual companionship"` means *that Foundation contributes 65% of the incident* — **not**
that the model is 65% confident. Output schema keeps them in separate fields, always.

## 3. The composition vector

```
P = [p(1a) … p(7d)]     28 values,  p ≥ 0,  Σ p = 1.00
World marginal:  Spiritual = p(1a)+p(2a)+…+p(7a)
Drive marginal:  Companionship = p(4a)+p(4b)+p(4c)+p(4d)
Dominant = argmax(P)
```

## 4. THE CENTRAL RISK — read before designing items

**There is no ground truth for mixture proportions.**

An authored `80/20` is a *claim by the author*, not a measured fact. If the author writes something
they believe is `80/20` and it is actually `55/45`, a model that predicts `55/45` is scored as
*wrong* while being *right*. That is the shared-authorship confound — the defect that produced
sixteen consecutive nulls — reappearing in a new location.

**Therefore the primary endpoint is ORDINAL, not proportional.**

| | Endpoint | Why |
|---|---|---|
| **PRIMARY** | **ordinal consistency** — across a matched triple, does the predicted `4a` share **decrease monotonically** from the `80/20` item to `50/50` to `20/80`? | requires only that authored *ordering* be correct, which is far weaker and far more defensible than authored *magnitude* |
| SECONDARY | absolute mixture error vs authored proportions | **reported, never gating** — authored magnitudes are not ground truth |
| GATE | **item admissibility** — independent blind judges must recover the same *ordering* | if judges cannot order the triple, the items do not carry the gradient and the family is **discarded before any model sees it** |

**A family whose ordering independent judges cannot recover is dropped, not scored.** This is the
positive control the mixture design needs, and it is mandatory.

## 5. Why this is a genuinely new Gate-2 opportunity

The previous campaign **failed** to earn a gradient claim: `SCRAMBLE-NULL-COMPLETION-v1`'s
secondary ordinal test `W1` returned `perm_p = 0.089` — `NOT LICENSED`.

A character n-gram model can match vocabulary. It has no mechanism for tracking a **semantic
gradient across surface-matched items where all four World words are prohibited**. If an internal
representation tracks the ordering and lexical baselines do not, that is exactly the
*small-model semantic authority* Gate 2 asks for — and it is a **new pre-registered experiment**,
not a reinterpretation of the failed `W1`.

## 6. Controlled mixture pilot

```
56 contrast families  (28 same-drive/different-World + 28 same-World/different-drive)
x 3 ratios (80/20, 50/50, 20/80)
= 168 scenarios
```

Within a family, **only intended composition varies**. Preserved: actor, setting, length, tone,
stakes, entity count, narrative complexity, outcome polarity. Written by modifying **one shared
plan**, never independently generated.

Priority pairs — the boundaries this campaign already found empirically:
`4a ↔ 4c` (shared "soul-deep", rank 33/378) · `6a ↔ 6d` · `6b ↔ 6d` · `2b ↔ 6b`

All four World words remain **prohibited by regex at admission**.

## 7. Authorship separation — mandatory

```
Author        writes from a frozen mixture recipe; never sees any prediction
Usora         predicts the mixture; never sees the recipe
Blind judges  independently estimate the mixture; never see the recipe or Usora
Reference     the frozen recipe PLUS independent judge agreement
```

**Usora may not author, declare intent, and judge.** One system doing all three recreates the
confound this document exists to avoid.

Reported: Usora vs authored · Usora vs independent consensus · judge–judge agreement ·
disagreement cases · calibration.

## 8. Frozen criteria

| # | Criterion | Bar |
|---|---|---|
| `U1` | **item admissibility** | blind judges recover the authored **ordering** in ≥ `0.70` of families; failures discarded pre-scoring |
| `U2` | **ordinal recovery** | internal readout tracks the ordering above chance, permutation `p < 0.01` |
| `U3` | **beats lexical** | ordinal recovery exceeds char 3–5-gram **and** word TF-IDF on identical items, same folds, margin `≥ 0.10`, CI excluding `0` |
| `U4` | **no World leak** | `0` admitted items contain a prohibited World word |
| `U5` | **hard-label compatibility** | `argmax(P)` accuracy reported alongside, for continuity with the Gate 2 classification requirement |

`U1` failing → `VOID_ITEMS_DO_NOT_CARRY_GRADIENT`. Not a model result.

## 9. Firewalls

**Two separate recipe vectors. Never merged.**

```
TKS_FOUNDATION_RECIPE_28   Spiritual / Mental / Emotional / Physical   (28 Foundations 1.0)
CAS_NATIVE_STATE_RECIPE_40 Principled / Cognitive / Evaluative / Operational (CAS v7.6)
```

These are **related project layers, not the same axis**. Any correspondence goes only in
`TKS_TO_CAS_TRANSLATION_EXPERIMENT` and must be tested, never presumed.

The running `672` corpus is **untouched**. A soft-annotation layer may be added later, and those
annotations may **never** be used to rewrite or select items.

## 10. Ceiling

A full pass licenses: *"an internal small-model readout tracks authored compositional ordering
across surface-matched, World-word-prohibited contrast families, above chance and above lexical
baselines, on items whose ordering independent blind judges also recover."*

Licenses **nothing** about: absolute mixture proportions being correct, CAS v7.6 recipe validity,
the TKS↔CAS correspondence, or Gate 2 closure — which remains the owner's explicit decision under
`GATE_2_SUCCESSOR_CLOSURE_CONTRACT`.

## 11. Gate 3 extension, recorded not yet registered

Continuous output functional `E_spiritual = Σ` Spiritual weights, then dose-response
`h_new = h + α·u_spiritual` over `α ∈ {−4, −2, 0, +2, +4}`. A genuine direction produces monotone
dose-response; random, orthogonal, wrong-layer, wrong-token and sham stay bounded. **Requires
Phase B first** — Phase A (`4714fa1a`) proved identifiability only, and its own caveat stands:
`wrong_layer` and `sham` sat at `+0.4167`, so a non-specific floor exists.

## Status

`LOCKED / SEPARATE ARTIFACT / NOT CANONICAL LAW / NOTHING LICENSED`
