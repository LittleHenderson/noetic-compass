# RESULT — `SPEC-AUTHORED-SCENARIOS-v1`

**Pre-registration:** `59d63dd5`, committed before any scenario was generated.
**Run:** 2026-07-27. Author `models/gemini-2.5-flash-lite` (**pinned to the baseline's author**),
judge `models/gemini-2.5-flash`.
**Verdict:** `LICENSED` — all five pre-registered criteria PASS.

---

## Headline

| | Author model | Protocol | 28-way accuracy |
|---|---|---|---|
| Baseline (`T2`, published `d755665b`) | `gemini-2.5-flash-lite` | thin prompt | `0.0429` (`p = 0.3011`) |
| **This run** | **same model** | owner's 27-section spec | **`0.9167`** (`77/84`) |

`chance = 0.0357` · binomial `p = 1.3e-102` · bootstrap 95% CI on the improvement
`[+0.8142, +0.9333]`

| Criterion | Bar | Observed | |
|---|---|---|---|
| `P1` beats baseline | `>= +0.15`, CI excludes 0 | `+0.8738` | **PASS** |
| `P2` above chance | `p < 0.01` | `1.3e-102` | **PASS** |
| `P3` beats surface | `>= +0.10` | `+0.7024` | **PASS** |
| `P4` no collapse | `<= 0.30` | `0.0714` | **PASS** |
| `P5` not lexical | Jaccard `<= 0.15` | `0.0260` | **PASS** |

**The author model was held fixed.** Only the protocol changed.

### Claim scope — narrowed 2026-07-27 at owner instruction

Two earlier phrasings were too broad and are corrected here. The corrections are recorded rather
than silently edited.

**Was:** *"a 21× improvement attributable to the instructions alone."*
**Now:** the `21×` figure is supportable **for this controlled authoring comparison**, and only
because the following were unchanged between arms — verified: author model
(`gemini-2.5-flash-lite`), decoding parameters (`temperature 0.95`, `top_p 0.95`), label
inventory (the same 28 TKS definitions), and judge procedure (`gemini-2.5-flash`, same prompt
builder, same parse path). It is **not** a claim that instructions alone explain every historical
failure. Item populations still differ between arms, as the pre-registration already flagged.

**Was:** *"the cause was the prompt."*
**Now:** **the original authoring prompt was a *sufficient* cause of the scenario-signal failure,
and appears to explain a major portion of the downstream nulls.** The intervention establishes
that changing the prompt repairs recoverability. It does **not** establish that each of the
sixteen instruments was otherwise flawless or affected only by this defect.

---

## The honest part: a leak `P5` did not measure

After the criteria passed, I audited for leakage channels the pre-registration missed. **It
missed one.**

`P5` measured word overlap between each scenario and the **TKS definition** (`0.0260` — clean).
It did **not** measure overlap with the **World and drive descriptors that my own author prompt
contained verbatim**.

| Post-hoc audit | Value |
|---|---|
| Recall of drive-descriptor words in scenarios | `0.3591` |
| Scenarios literally containing the World name (*Spiritual/Mental/Emotional/Physical*) | **`47/84 = 0.560`** |
| Spec §11 explicit-contrast-phrase violations | `1/84` |
| Legacy code leak / terminology leak / legacy name leak | `0` / `1` / `0` |

More than half the scenarios contain the literal World word. That is a direct label leak on the
World axis, introduced by my prompt design, and `P5` was blind to it.

## The decisive control, run post-hoc against my own result

I rebuilt the lexical baselines **keyed on the exact descriptor text the author prompt
contained** — the leak channel itself — to see how far it alone gets you:

| | full 28-way | World | drive |
|---|---|---|---|
| char 3–5-gram, descriptor-keyed | `0.1429` | `0.6310` | `0.2738` |
| word TF-IDF, descriptor-keyed | `0.1190` | `0.5714` | `0.1786` |
| **independent judge** | **`0.9167`** | **`0.9167`** | **`1.0000`** |
| chance | `0.0357` | `0.2500` | `0.1429` |

**What this establishes:**

- **The World leak is real and it is exploitable.** A bag of character n-grams reaches `0.6310`
  World accuracy against chance `0.2500` purely by finding the leaked word. The World number is
  contaminated and must be reported as such.
- **The judge still beats the best exploit of that leak by `+0.2857` on World.**
- **The drive axis is clean.** The judge is **perfect — `84/84`** — where the best lexical
  exploit reaches `0.2738`. A `73`-point gap with no leak channel that explains it.
- **Full-foundation gap is `+0.7738`** over the best lexical method with privileged access to the
  leak.

The owner's pre-specified success pattern — `judge > lexical > chance` — holds on every axis. The
suspicious pattern — `char n-grams >= judge` — does not occur anywhere.

## The error structure is informative

All **`7`** errors have the **correct drive and the wrong World**:

```
F4T Spiritual Love     -> F4f Emotional Love    (x3)
F6T Spiritual Resources-> F6E Physical Resources
F6A Mental Resources   -> F6E Physical Resources (x2)
F6E Physical Resources -> F6f Emotional Resources
```

Zero drive errors. Confusion concentrates in Foundation `6` (Resources) and `4a` (Spiritual
Love) — precisely the cells where the owner's spec warns about `3` vs `6`, `1` vs `4`, and
Spiritual-vs-Emotional disambiguation.

---

## What is licensed

> *"Scenarios authored under the owner's specification by `models/gemini-2.5-flash-lite` carry
> foundation signal recoverable by an independent judge at `0.9167` (`77/84`) against chance
> `0.0357`, where scenarios by the same model under a thin prompt scored `0.0429` (`p = 0.3011`).
> The drive axis is recovered perfectly (`84/84`) and exceeds the best descriptor-keyed lexical
> baseline by `+0.7262`. The deficit in the earlier campaign was authoring protocol."*

## What is NOT licensed

- **The World-axis number.** `0.9167` sits on a dataset where `56%` of items name the World
  outright. It exceeds the leak-exploiting baseline, but it is not a clean measurement and a
  successor must strip the World word.
- **Gate 2.** `gemini-2.5-flash` is not a small model. The gate's wording is unmet.
- **Anything about TKS vs CAS definition quality.** No arm comparison exists here.
- **Anything about human authoring or judging.**

---

## Why this matters for the campaign

This is the **first instrument in the campaign that discriminates**. Sixteen predecessors returned
nulls, and the positive control (`d755665b`) localized the cause to authoring. That diagnosis is
now confirmed by intervention: fix the authoring protocol, hold the model fixed, and recovery goes
from indistinguishable-from-chance to `0.9167`.

**The remaining gap to Gate 2 is now a single, well-posed experiment:** run these same `84` items,
with these same baselines, through a **small model**. The premise is clean — an independent judge
confirms the signal is present in the items, which was never true of any earlier dataset.

## Dataset versioning — both versions preserved, neither overwritten

Per owner instruction, the contaminated dataset is **not** repaired in place:

| Version | Contents | What it measures |
|---|---|---|
| **`V1_RAW`** | the original 84 scenarios, World-name leakage intact | the protocol **as implemented** |
| **`V1_DELEAKED`** | deterministic removal of prohibited descriptors | the stronger **semantic** claim |

`V1_RAW` is what is committed here (`spec_authored_items.json`, item-set sha256
`c2ad86df5bac9792dd02685925f9750f`). Both are reported side by side in any successor.

**Caveat on deterministic stripping, recorded before it is applied:** removing `spirit/spiritual`,
`mind/mental`, `emotion/emotional`, `physical` also removes ordinary semantic content — especially
*mind* and *feeling* — and will damage some classes more than others. Deterministic stripping is
therefore a **sensitivity analysis**, not the primary de-leak. The primary de-leak is
**regeneration under a prohibited-token list**, and because that decision follows sight of the
`V1_RAW` result it must be filed as a **new pre-registered dataset, not a correction to this one**.

## Required for the successor

1. **Regenerate** under a prohibited-token list (new pre-registration, new dataset name).
2. **Extend `P5` to cover every string the author prompt contains**, not just the definition text.
3. Report `V1_RAW` and `V1_DELEAKED` together; the delta quantifies the leak's contribution.
4. **Preserve the seven errors** as a targeted diagnostic set — do **not** repair them before the
   small-model run. They are informative boundary cases (`4a` vs `4c`; `6a`/`6b`/`6c`/`6d`), and
   the pattern suggests the drive is recoverable while **ontological location** is not always
   behaviorally anchored. A separate adversarial set for Foundations `4` and `6` comes after.

Artifacts: `spec_authored_results.json`, `spec_authored_items.json`, `spec_authored_preds.json`.
Gate 2 remains **OPEN at `0.38`**.
