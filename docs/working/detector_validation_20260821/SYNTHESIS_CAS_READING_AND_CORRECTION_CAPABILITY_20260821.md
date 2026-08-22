# State of the CAS harness reading capability — FINAL, v1→v28 (2026-08-21)

**Supersedes** `SYNTHESIS_CAS_READING_AND_CORRECTION_CAPABILITY_20260821.md` (written at v17, before the v19–v21 collapse and the v22–v28 rebuild). That file is retained; this one is current.

**Scope.** All model work is `EleutherAI/pythia-160m` (local CPU, attested engine, `$0`) and `EleutherAI/pythia-6.9b` (paid RunPod A40, **~$1.00 total for the whole session**). **No customer `ACCEPT` anywhere. The attested-engine canary is still `NOT RUN`.**

---

## 1. The one-paragraph state

The session began by producing four strong-looking reading results and ended by **killing all four** — every one was solvable by a hand-written word rule, which meant the experiments could not distinguish comprehension from vocabulary. The recovery was to build a **new class of test where cheating is arithmetically impossible**: sentence pairs with identical word multisets *and* identical character-n-gram bags, so both surface baselines are **forced** to chance rather than merely observed there. Under that instrument the model reads **temporal binding at `1.000`** and the **CAS `^8`/`^9` trigger-vs-arrival relation at `1.000`**, while reading **speaker binding at chance** — and that last null is what proves the instrument discriminates rather than always saying yes. A layer-indexing check ruled out the one artifact that could have explained the positives away. **Net: the harness now has a small number of unfakeable results and an instrument that produces them. CAS-specificity remains `GREY`.**

---

## 2. What was WITHDRAWN, and why (the load-bearing negatives)

| result | headline it had | how it died |
|---|---|---|
| Domain-4 | `0.938` vs char-ngram `0.438` at 6.9b (+`0.500`) | **three regexes classify the stimuli `32/32 = 1.000`** — better than the model (v19) |
| `^8`/`^9` cause-effect | `0.917` vs `0.833` | a **comma-count rule ties it exactly** (v20) |
| Valence reading | `0.938` vs `0.500` | a **generic sentiment word list ties it exactly, 15/16** (v21) |
| Operator-10 reading | `0.800` vs `0.550` | a **word list beats it, 20/20 vs 16/20** (v21) |

**The binding methodological finding:** the char-ngram control this track relied on is **systematically too weak — beaten on 4 of 4 stimulus sets.** Every margin ever reported against it is overstated. Passing char-ngram is **necessary, not sufficient**.

**Second finding:** automated shortest-rule search is a **lower bound** — it found `0.688` on the Domain grid where a hand-written regex reached `1.000`. "No rule found" never means "no rule exists."

---

## 3. What SURVIVES — the results with an unfakeable floor

The instrument: pairs with **identical word multisets** and **identical char-n-gram bags** (residual `0.000000`), **position counterbalanced**, **token-length matched**, verified by a **blocking pre-flight gate before the model loads**.

| test | relation measured | model | bag-of-words | char-ngram |
|---|---|---|---|---|
| **v25** | temporal binding (which came first) | **`1.000`** (mean `0.917`) | `0.500` **forced** | `0.500` **forced** |
| **v26** | **CAS `^8`/`^9`** trigger vs arrival | **`1.000`** (mean `0.962`) | `0.500` **forced** | `0.500` **forced** |
| **v27** | speaker binding (who said what) | `0.625` → **chance** (`P=0.8651`; mean `0.524`) | `0.500` **forced** | `0.500` **forced** |

**v27's null is the keystone.** Without it, a skeptic could say the probe merely detects *that the two strings differ*. It cannot be that: in v27 the strings also differ and the probe finds **nothing**. The instrument **discriminates**.

**v28 removed the one fatal alternative.** `L0` resolves to `gpt_neox.layers.0` — the **output of block 0**, not the embeddings. Had it been embeddings, identical tokens at identical positions would have given identical vectors and v25/v26 would have been artifacts. **Ruled out.** It also fixes the honest ceiling: one attention pass suffices, so this is **binding, not deep multi-layer composition**.

**Also standing (different evidence class):** **v16 causal steering** at 6.9b — injecting the valence direction moves output valence, **z = `11.18`** vs a norm-matched random null, monotone ×1→×8. An *intervention*, structurally immune to the lexical attack that killed the reading results. Bounded by v17 to *"the valence direction steers valence output, direction-specific vs random"* — a standard steering-vector claim, **not** a CAS-construct claim.

---

## 4. What this is FOR (the capability, in one line each)

- **Safety filters** — *"nurse gave patient"* vs *"patient gave nurse"*: identical words, opposite situations. A surface filter cannot separate them; this test says whether yours can.
- **Order-critical procedures** — *"drug A before drug B"* vs the reverse. Same words, different outcome.
- **Contracts** — *"A indemnifies B"* vs the reverse.
- **Prompt injection** — injection subverts **speaker→instruction binding**. v27 measures exactly that capability, at the representation level, **pre-deployment**. And it **demonstrates** that the existing C11 text-surface filter is *provably* blind to same-word injection.
- **Fine-tuning regression** — a comprehension regression test, not a vocabulary one.
- **Vendor comparison** — a vendor **cannot train past** a test whose word statistics are identical between the two answers.

---

## 5. Honest limits (all of them)

- **CAS-specificity is `GREY`.** v26 shows the trigger-vs-arrival relation is present and readable. A skeptic may answer that this is **ordinary role assignment that CAS has NAMED** — recorded *before* the result, and **this test cannot settle it**.
- **Shallow.** One attention pass suffices; deep composition is **NOT LICENSED**.
- **Small.** 12 pairs / 24 items per test; one frame template each; one seed.
- **Scale untested for the instrument.** v25–v28 are all `pythia-160m`. The 6.9b runs (~$0.15 each) are unrun; the **speaker-binding one is the highest-value** — chance → strong would be a genuine capability curve.
- **Claim A is dead** ("the weights are natively CAS", retired 2026-08-18). **Claim B is live** (CAS as a measurement-and-correction language) with real support on the measurement side and valence-only on the correction side.
- **Not the canary.** Every result here is detector research; the frozen A40/Pythia canary remains **`NOT RUN`**.

---

## 6. Process assets built today (reusable, `$0`)

1. **Pinned-pair stimulus design** — surface confounds excluded by arithmetic, not argument.
2. **Blocking pre-flight gate** — rejected **two** of my own designs (v24 residual `0.02776`; v25a `0.004626`) **before any compute**.
3. **`template_audit.py` + shortest-rule search** — the audit that killed the four false results.
4. **Adversarial verification before recording** — caught **five** false claims this session, two of them my own code bugs.

**The record itself:** no number altered, no negative deleted, withdrawn rows flagged in place, every result hash-verified and mirrored to `D:/tksCAS-archive`.
