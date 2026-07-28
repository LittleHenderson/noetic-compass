# RESULT — `LATIN-SQUARE-SUCCESSOR-v1`

**Pre-registration:** `a7381c42`, committed before the run.
**Verdict:** `NOT_LICENSED_LEXICAL` — **replicates** `SMALL-MODEL-RECOVERY-v1` under corrected folds.
**Gate 2:** **OPEN at `0.38`**.

---

## 1. The fold fix worked — `L3` PASS

Every test fold now contains **all four Worlds and all seven drives, each present in its training
fold**:

```
fold 0  test worlds=[a,b,c,d]  drives=7  all present in train: True
fold 1  test worlds=[a,b,c,d]  drives=7  all present in train: True
fold 2  test worlds=[a,b,c,d]  drives=7  all present in train: True
fold 3  test worlds=[a,b,c,d]  drives=7  all present in train: True
```

The frozen Latin square reproduced the owner's table cell for cell. The World endpoint is
**identifiable for the first time** — `0.0000` is gone.

## 2. Both leakage controls PASS — the apparatus is clean

| Control | Observed | Expected | |
|---|---|---|---|
| `C-PERM` group-level label permutation | `0.0595` | `~0.1429` | **PASS** |
| `C-BODY` constant text, no metadata to extractor | `0.1429` | `<=` majority `0.1429` | **PASS** |

`C-BODY` landing **exactly** on the majority rate is the clean signature: with identical input for
every row the probe can only predict the majority class. **No leakage through ordering, file
structure, position, identifiers, or split construction.**

This validates the whole measurement chain, and it is the first time in this campaign that both
controls have been run.

## 3. Results

| Arm | drive | World *(leaked)* |
|---|---|---|
| char 3–5-gram | **`0.4881`** | `0.5238` |
| word TF-IDF | `0.4524` | `0.4643` |
| **pythia-160m L6** | `0.4524` | **`0.5595`** |
| chance | `0.1429` | `0.2500` |

| Criterion | Result |
|---|---|
| `L1` drive above chance | **PASS** — permutation `p = 0.0001` |
| `L2` drive beats lexical | **FAIL** |
| `L3` World identifiable | **PASS** |
| `L4` World above chance | **PASS** — *reported only with the leak disclosure* |
| `L5` `C-PERM` returns to chance | **PASS** |
| `L6` `C-BODY` returns to chance | **PASS** |

## 4. `L2` — descriptive first, significance separately

**Descriptive:** char 3–5-grams `0.4881` vs `pythia-160m` L6 `0.4524`. Margin `-0.0357`.
**Significance, separately:** group-bootstrap 95% CI `[-0.1429, +0.0714]`, contains zero.

**`L2` fails.** Per the standing rule, *statistical uncertainty cannot convert "did not exceed"
into "exceeded."*

Both arms dropped relative to the previous run (`char 0.6071 → 0.4881`, `pythia 0.5595 → 0.4524`)
because the Latin square is a genuinely harder split. **Both dropped together, so the comparison
remains fair** — and the ordering is unchanged.

## 5. The one place the model leads is the contaminated axis

On **World**, `pythia-160m` (`0.5595`) exceeds the best lexical baseline (`0.5238`) by `+0.0357`.

**This is not counted as evidence for semantic extraction, and it should not be.** World is the
axis where `47/84` scenarios (`56%`) contain the literal World name. The model's only advantage
appears precisely where a lexical leak exists, while on **drive — the clean axis, and the one the
independent judge recovered perfectly at `84/84` — the model does not beat character n-grams.**

Read together, that pattern points away from semantic extraction rather than toward it.

---

## 6. Standing

1. The authoring protocol inserts recoverable drive information. **Confirmed.**
2. An independent large judge extracts it perfectly. **Confirmed** (`59e9044c`).
3. A small model extracts substantial drive signal above chance. **Confirmed twice**
   (`p = 0.0001`, two fold designs).
4. A small model outperforms a character-level lexical model. **Not demonstrated, twice.**
5. Pipeline leakage. **Ruled out** — both controls pass.
6. Gate 2. **Open at `0.38`.**

## 7. What would change the answer

- **`336` items** — `28 Foundations × 4 independently authored plans × 3 siblings` — which is the
  minimum for supervised 28-way CV and for the `direct` vs `drive × world` compositional test.
- **A de-leaked dataset** (regeneration under a prohibited-token list) so the World axis becomes
  admissible evidence rather than a flagged number.
- **A different readout.** Mean-pooled hidden states under a linear probe is one choice among
  many; this result constrains that choice at `160M`, not the framework.
