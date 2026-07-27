# RESULT — `JUDGE-POSITIVE-CONTROL-v1`

**Pre-registration:** `8ab16b2d` + Amendment 1 (`35c9f62a`), both committed before data.
**Run:** 2026-07-27. Judge `models/gemini-2.5-flash`, `temperature 0.0`.
**Verdict:** `JUDGE_FUNCTIONAL` — all four pre-registered criteria PASS.

---

## Results

| Tier | Item text | Accuracy | vs chance `0.0357` |
|---|---|---|---|
| `T0` | definition, verbatim | **`1.000`** (`28/28`) | `p = 3.0e-41` |
| `T1` | mechanical rewrite | **`1.000`** (`160/160`) | `p = 2.8e-232` |
| `T2` | real authored scenarios | **`0.0429`** (`12/280`) | **`p = 0.3011`** |

`T1 − T2 = 0.9571`

| Criterion | Bar | Result |
|---|---|---|
| `C1` harness integrity | `T0 >= 0.90` | **PASS** (`1.000`) |
| `C2` instrument sensitivity | `T1 >= 0.50` | **PASS** (`1.000`) |
| `C3` difficulty localized | `T1 - T2 >= 0.20` | **PASS** (`0.9571`) |
| `C4` no degenerate collapse | max share `<= 0.30` | **PASS** (`T2` at `0.2857`) |

---

## 1. The harness is sound — this closes the branch that mattered

`T0 = 28/28`. The judge identifies a definition handed to it verbatim, every time.

The `C1`-failure branch — under which every `NOT_LICENSED` verdict in the ledger would have been
reclassified as uninterpretable pending repair — **does not obtain**. The choice-set wiring, id
alignment, prompt neutralization, JSON parse repair, and validator all work. The eight prior null
results stand as interpretable nulls.

This was the reason to run the control, and it came back clean.

---

## 2. The authored scenarios carry NO recoverable signal

`T2 = 12/280`. Expected under blind guessing: `10`. Observed: `12`.

**One-sided binomial `p = 0.3011`. The 95% CI is `[0.0249, 1.0000]` and contains chance.**

This is not "weak signal." It is **statistically indistinguishable from random guessing.** The
scenarios were authored to embody a specific foundation, and a judge that maps definitions to
foundations flawlessly cannot recover which foundation a scenario was built from.

`C4` nearly tripped here: the judge concentrated `28.57%` of its `T2` answers on one foundation
against a `30%` bar. Drifting toward a default answer is what a model does when the input carries
nothing to discriminate on.

### What this explains

The scaled matched A/B returned `NOT_LICENSED_DEGENERATE` with both arms near the floor
(`0.0636` and `0.0423` against chance `0.0357`). That result is now fully accounted for: **both
arms were near the floor because scenario text in both arms carries no recoverable foundation
signal.** The comparison was never between two definition sets — it was between two piles of
noise, measured very carefully.

Every instrument downstream of the scenario-authoring step inherits this defect.

---

## 3. Honest caveat on `T1` — read before quoting the number

`T1 = 160/160` is a stronger number than it deserves to be treated as.

`T1` items are clause-rotations and frozen-synonym substitutions of the target definition. They
remain **lexically very close** to it. A pure string-similarity matcher, with no semantic
understanding at all, would also score near `1.000` on this tier.

So `T1` demonstrates that the apparatus **reads, parses, maps, and validates correctly**. It does
**not** demonstrate that the judge understands meaning. My `C2` bar of `0.50` was set on the
assumption that `T1` posed a genuine semantic discrimination problem. The perfect score is
evidence that it does not.

**A future version needs a middle tier** — items that preserve meaning while breaking lexical
overlap — to separate "matches strings" from "recovers meaning." That tier does not exist yet,
and no claim about semantic discrimination is licensed by this run.

---

## 4. What is and is not licensed

**Licensed:**

> *On `models/gemini-2.5-flash`, the 28-way foundation-matching apparatus is correctly wired and
> recovers the target foundation at `1.000` when the item is definition-level text. The
> near-chance performance observed in the matched A/B is attributable to the authored-scenario
> step, not to the judge or the harness. Authored scenarios carry foundation signal that is
> statistically indistinguishable from chance (`p = 0.3011`).*

**NOT licensed:**

- That the judge discriminates **semantically** — `T1`'s lexical proximity confounds this.
- Anything about TKS versus compact definitions. No arm comparison occurred in this design.
- Anything about a **small model**. `gemini-2.5-flash` is not small; Gate 2's "small model"
  wording is not addressed by this run.
- **Gate 2 closure.** This removes an explanation for the nulls and localizes the defect. It does
  not itself demonstrate the scoring works on a small model.

**Gate 2 remains OPEN at `0.38`.**

---

## 5. What this changes going forward

1. **A stronger judge model will not help.** The signal is absent from the items; a better reader
   cannot recover what was never written down. This saves the cost of that swap.
2. **The defect is upstream, in scenario authoring.** `models/gemini-2.5-flash-lite` was asked to
   write vignettes embodying a foundation and produced text from which the foundation cannot be
   recovered. Any future instrument must validate its items *before* comparing arms.
3. **A positive control belongs in every future design.** Sixteen instruments ran without one.
   This one cost under an hour and reframed the whole ledger.
4. **The human-panel protocol should be re-scoped.** Asking people to recover foundations from
   these scenarios would reproduce the same null on more expensive labour. Either fix authoring
   first, or put people on the definition-matching task, which is demonstrably tractable.

---

## Reproduce

```bash
python -u docs/working/gate2_closure/matched_ab_20260726/run_judge_positive_control.py
```

Artifacts: `posctl_results.json`, `posctl_preds_T0.json`, `posctl_preds_T1.json`,
`posctl_preds_T2.json`.
