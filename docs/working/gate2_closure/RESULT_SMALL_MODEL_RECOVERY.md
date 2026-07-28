# RESULT — `SMALL-MODEL-RECOVERY-v1`

**Pre-registration:** `3af611a5`, committed before any model was loaded.
**Verdict:** `NOT_LICENSED_LEXICAL` — a **useful negative**.
**Gate 2:** remains **OPEN at `0.38`** under the pre-registered rule.

---

## Results

| Arm | drive | World |
|---|---|---|
| char 3–5-gram | **`0.6071`** | `0.0000` **VOID** |
| word TF-IDF | `0.5238` | `0.0000` **VOID** |
| **pythia-160m L6** *(primary)* | `0.5595` | `0.0000` **VOID** |
| pythia-160m L0 | `0.5476` | `0.0000` **VOID** |
| gpt2 L6 *(replication)* | `0.4762` | `0.0000` **VOID** |
| gpt2 L0 | `0.3333` | `0.0000` **VOID** |
| chance | `0.1429` | `0.2500` |

**Effective `n` = `28` groups (foundations), not `84` rows.**

| Criterion | Result |
|---|---|
| `G1` drive above chance | **PASS** — `0.5595` vs `0.1429`, permutation `p = 0.0001` |
| `G2` drive beats best lexical | **FAIL** — see below |
| `G3` no collapse | **PASS** |
| `G4` honest error bars | **PASS** — published at full width |
| `G5` World secondary | **FAIL** — void, not negative (below) |

## `G2` — descriptive ordering, then significance, kept apart

**Descriptive:** character 3–5-grams achieved **higher observed drive accuracy** than
`pythia-160m` L6 — `0.6071` vs `0.5595`, margin `-0.0476`.

**Significance, reported separately:** group-bootstrap 95% CI on the difference is
`[-0.1548, +0.0595]`, which **contains zero**. The two are not statistically distinguishable at
`n = 28` groups.

**The criterion still fails.** Per the owner's standing rule:

> *"Statistical uncertainty cannot convert **did not exceed** into **exceeded**."*

`G2` required the model to *outperform* the lexical baseline. It did not. A wide interval does not
convert a shortfall into a win, and the frozen criterion is not renegotiated after the fact.

## `G5` — the World endpoint is VOID, not negative

`world = 0.0000` **exactly**, across every representation including the baselines. That is the
signature of an impossible generalization setup, not a measurement.

`GroupKFold` over foundations sorted `1a,1b,1c,1d,2a,…` assigned every group sharing a World to
the same fold. Each test fold therefore contained exactly **one** World, **absent from its own
training set** — the classifier structurally could not predict it.

Drive was unaffected because all seven drives appear in every fold. Fixed by the frozen Latin
square in `PREREG_LATIN_SQUARE_SUCCESSOR.md` (`a7381c42`).

## Depth contributed almost nothing

`pythia-160m` L6 (`0.5595`) vs L0 token embeddings (`0.5476`) — a gain of `+0.0119`. Most of what
the probe uses is available at the embedding layer, which is consistent with the lexical reading.

`gpt2` replication came in lower on both layers (`0.4762` / `0.3333`), so no cross-architecture
support for the model arm either.

---

## What this establishes — the evidence state has moved

1. The revised authoring protocol **successfully inserted recoverable drive information**.
2. An independent large judge **extracted it perfectly** (`84/84`, commit `59e9044c`).
3. The tested small representation **extracted substantial drive signal above chance**
   (`0.5595` vs `0.1429`, `p = 0.0001`).
4. It **did not outperform a character-level lexical model**.
5. The World experiment was **structurally unidentifiable** and is void.
6. **Gate 2 remains open under the pre-registered rule.**

The failure has moved from *"the items contain no signal"* to *"the small model has not
demonstrated semantic extraction beyond lexical regularities."* **Those are entirely different
states of evidence**, and only the second one is now in play.

## Not claimed

This does **not** overturn `59e9044c`. The signal is independently confirmed present in the items.
This says a `160M` mean-pooled representation under a linear probe does not reach it better than
counting character sequences — a statement about *this readout at this scale*, not about the
framework.

## Not runnable on this dataset

Supervised 28-way CV. Each Foundation has one sibling group; when it is held out, that class is
absent from training. The `direct 28-way` vs `predicted_drive × predicted_world` compositional
comparison requires **`28 × 4` independently authored plans `× 3` siblings = `336` items** — four
distinct plans, not paraphrases of one.
