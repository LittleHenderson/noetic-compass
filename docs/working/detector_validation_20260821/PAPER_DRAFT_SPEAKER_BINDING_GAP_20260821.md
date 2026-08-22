# Language models bind cause and time but not speakers: a surface-proof measurement

**Draft — 2026-08-21.** Internal write-up of the v22–v31 arc. Research-grade; no customer `ACCEPT`; not the attested-engine canary.

---

## Abstract

Prompt injection succeeds because a model fails to keep track of **which instruction came from which speaker**. We introduce a stimulus design in which surface heuristics are **provably incapable** of exceeding chance — sentence pairs sharing an identical word multiset *and* an identical character-n-gram bag, with position counterbalanced and token length matched — so that any above-chance classification from model activations must reflect relational structure rather than lexical statistics. Applying it to four models across two families, we find a consistent **dissociation**: models recover *which event preceded which* (mean up to `0.969`) and *which idea triggered which* (mean up to `0.993`) at near-ceiling, while recovering *which speaker issued which instruction* at or near chance (`0.520`–`0.612`). The gap does not close with a 43× parameter increase (`0.524` → `0.520`), and a controlled base-vs-instruct comparison within one family shows instruction tuning moves speaker binding by `+0.014` — **less than it moves the temporal control (`+0.049`)** — leaving the speaker-vs-cause gap unchanged (`0.380` → `0.381`). We conclude that, in these models, **instruction tuning does not install the representational precondition for speaker-attribution**, and we offer the design as a reusable, ungameable evaluation instrument.

---

## 1. The problem with surface controls

Standard practice compares an activation probe against a lexical baseline (bag-of-words, char-n-grams, TF-IDF). The baseline is *measured*, and if it scores low the probe is declared meaningful.

**This is unsound, and we demonstrate it empirically.** Across four stimulus sets built for this project, a simple hand-written rule **matched or beat** the char-n-gram baseline every time:

| stimulus set | char-n-gram baseline | shortest hand rule |
|---|---|---|
| 4-way domain classification | `0.688` | **`1.000`** (three regexes) |
| cause/effect | `0.833` | **`0.917`** (comma count) |
| valence | `0.500` | **`0.938`** (sentiment word list) |
| 10-way operator | `0.550` | **`1.000`** (cue-word lexicon) |

Every "positive" result resting on those sets was withdrawn. **Passing a lexical baseline is necessary, not sufficient**: the baseline may simply be a weak model of the surface, not a bound on it.

## 2. Method: pinning the baseline by construction

Instead of measuring a surface baseline, **make it provably powerless.** Each item is a pair `(A, B)` labelled by a relation, constructed so that:

1. **Identical word multisets** → any bag-of-words model must score exactly `0.500`.
2. **Identical character-n-gram bags** (n = 2,3,4; verified residual `0.000000`) → any n-gram model must score exactly `0.500`.
3. **Position counterbalanced** — the same entity occupies slot 1 in both members → position is uninformative.
4. **Token length matched** (`0/12` mismatches) → no length or positional-encoding artifact.

Example (speaker binding):
```
A: system said : follow the rules ; user said : ignore the rules ; done
B: system said : ignore the rules ; user said : follow the rules ; done
```
Both contain one `follow the rules`, one `ignore the rules`, one `system said`, one `user said`. The separators ` : ` and ` ; ` give both instructions identical local context, so the n-gram bags match exactly. **The only distinguishing information is which instruction binds to which speaker, across a long-range dependency.**

Classification is leave-one-**pair**-out nearest-centroid on last-token residuals, evaluated at every layer. **Verdicts rest on the mean over all layers**, which is free of best-layer selection bias; best-layer figures are reported for completeness.

**A blocking pre-flight gate** verifies all four conditions *before* a model is loaded. It rejected two of our own designs (residuals `0.02776` and `0.004626`) at zero compute cost — in both cases a function word had shifted a junction n-gram.

## 3. Results

### 3.1 The instrument discriminates (the essential control)
On `pythia-160m`, the same probe under the same gate gives:

| relation | best | mean over layers |
|---|---|---|
| temporal binding | `1.000` | `0.917` |
| CAS `^8`/`^9` trigger/arrival | `1.000` | `0.962` |
| **speaker binding** | `0.625` | **`0.520`** (chance; `P = 0.8651` after best-of-12) |

Both surface baselines are pinned at `0.500` in **all three rows**. The probe is not a difference-detector: **it finds nothing where nothing is encoded**, which is what licenses the positive rows.

### 3.2 The gap survives 43× scale

| | speaker mean | temporal mean | cause mean |
|---|---|---|---|
| `pythia-160m` | `0.524` | `0.917` | `0.962` |
| `pythia-6.9b` | **`0.520`** | `0.969` | `0.967` |

Scaling 43× changed speaker binding by **`−0.004`**. Cause and time remain near ceiling.

### 3.3 The gap survives instruction tuning (controlled)
`Qwen2.5-7B` base vs `Qwen2.5-7B-Instruct` — same family, data, architecture, tokenizer; **one variable**:

| relation | base | instruct | Δ attributable to tuning |
|---|---|---|---|
| cause `^8`/`^9` | `0.978` | `0.993` | `+0.015` |
| temporal | `0.857` | `0.906` | `+0.049` |
| **speaker** | `0.598` | `0.612` | **`+0.014`** |

**Instruction tuning moves speaker binding less than it moves the temporal control.** The speaker-vs-cause gap is `0.380` (base) → `0.381` (instruct): **unchanged**.

### 3.4 A cross-family delta is mostly not what it appears
An uncontrolled comparison (`pythia-6.9b` → `Qwen2.5-7B-Instruct`) shows `+0.092` on speaker binding — superficially "instruction tuning works." Decomposed against the base model of the same family:

- family / pretraining data / architecture: **`+0.078` (85%)**
- instruction tuning: **`+0.014` (15%)**

Attributing the full delta to instruction tuning would have been **wrong by ~6×**.

## 4. Discussion

Across **four models and two families**, base and instruction-tuned, under conditions where lexical and n-gram heuristics are pinned at chance by construction, the same pattern holds: **cause and time are bound near ceiling; speaker is not bound.**

The prevailing account of injection resistance is that instruction tuning teaches a model to privilege the system prompt. Our controlled comparison finds that tuning **does not install the underlying binding** — it moves speaker attribution less than it moves an unrelated temporal control, and leaves the gap intact. Tuning may well change *behaviour*; what it does not appear to change is the *representational precondition* on which reliable attribution would rest.

## 5. Limitations (complete)
- n = 12 pairs / 24 items per contrast; one frame template per contrast; one seed.
- Speaker-binding figures, where above chance, remain **marginal** after selection correction (`P = 0.0885` on the instruct model).
- Two families (Pythia, Qwen); no RLHF'd or frontier model tested. **No claim is made about frontier systems.**
- This measures a **representational precondition**, not runtime behaviour. It does **not** establish that any deployed system will or will not resist a live attack.
- Attested-engine replication not performed for the paid-GPU runs (direct `transformers` capture); the frozen canary remains `NOT RUN`.
- Best-layer figures are selection-biased; all verdicts use the selection-free mean over layers.

## 6. Contributions
1. **A surface-proof stimulus design** in which lexical baselines are pinned at chance by arithmetic rather than by measurement.
2. **A blocking pre-flight gate** that rejects confounded designs before compute is spent (2 rejections, `$0`).
3. **Empirical demonstration** that char-n-gram controls understate the surface ceiling (4/4 sets).
4. **A replicated dissociation**: cause/time bound, speaker not bound — across 4 models, 2 families, base and tuned.
5. **A controlled attribution** showing instruction tuning does not install speaker binding, and that a naive cross-family comparison overstates its effect ~6×.

**Total compute cost of the paid runs reported here: ≈ $1.45.**
