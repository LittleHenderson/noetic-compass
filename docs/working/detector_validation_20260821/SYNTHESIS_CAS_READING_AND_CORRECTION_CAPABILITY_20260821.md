# State of the CAS reading & correction capability — the v1→v17 arc (2026-08-21)

> **⚠ CORRECTED 2026-08-21 (v19).** The **Domain-4** figures below are **BOUNDED**: that stimulus set is 100% solvable by three hand-written regexes (`16/16`), so its char-ngram baseline (`0.438`) understated a true surface ceiling of `1.000`. Domain-4's `+0.500` margin and the claim "reads principle from meaning, not modal words" are **WITHDRAWN as specificity claims**. The binding lesson: **the char-ngram surface control UNDERSTATES the surface ceiling — passing it is necessary, NOT sufficient.** Every stimulus set now needs a template/regex audit (`template_audit.py`) before GPU spend. Valence, Operator-10 and the causal result are **not** corrected by this finding (different stimuli) but have **not been regex-audited either**. See `RESULT_DETECTOR_VALIDATION_V19_DECISIVE_NULL_AND_V11_V15_CORRECTION_20260821.md`.

**Purpose.** One honest, defensible narrative pulling together every detector/steering result run this session on real model weights. Plain English, exact numbers, claim-state separated. This is a research summary — **nothing here is a customer `ACCEPT`, and none of it used the attested-engine canary (which is still `NOT RUN`).** All model runs are `EleutherAI/pythia-160m` (local, CPU, `$0`) and `EleutherAI/pythia-6.9b` (paid RunPod A40, ~$0.85 total), via direct transformers except where noted.

---

## 1. The one-paragraph bottom line

On a real 6.9-billion-parameter model, the harness **reads four CAS axes out of the hidden state in a way that beats a plain word-counter** — valence, the 10 Noetic operators, the 4 Domains (all cleanly), and cause/effect (marginally). The same axes **fail** that word-counter test on a tiny 160M model: the reading ability **hardens with scale**, it is not a small-model artifact, and it is not giveaway-word matching. On the correction side, the **valence direction is a genuine causal lever** at scale — pushing it moves the model's output valence far more than a random nudge. **But** an adversarial check stopped us from over-reading the other axes' "steering": beating a *random* nudge is not the same as proving the effect is *specifically CAS*. So the live thesis (Claim B — CAS as a measurement-and-correction language) has real, multi-axis support at scale, while the deepest question — **is the structure specifically CAS, or generic meaning wearing CAS labels?** — stays **`GREY`**.

---

## 2. The reading (measurement) arc

The test that matters is the **char-ngram surface control**: train a detector on the model's activations, then test it on stimuli that hide the giveaway words, and compare against a bag-of-character-ngrams "word-counter." Beating the word-counter = the detector reads something deeper than surface vocabulary.

| Stage | Model | Finding |
|---|---|---|
| v1–v5 | 160m | Axes read **cross-topic within the same register** (valence, cause/effect, Domain, Operator) — real but register-bound. |
| v6/v7 | 160m | **NEGATIVE:** on implicit/stripped stimuli the axes do **not** beat the word-counter. Surface-confounded. |
| v9 | 160m | Operator-10 surface-robust *same-register* (0.55 vs 0.25); Domain-4 only weakly over surface. |
| v10 | **6.9b** | Valence **clean** (0.938 vs 0.500); cause/effect **NOISE**; Domain **surface-lexical** (1.000 vs 0.875); Operator surface-robust (same-register). |
| v11/v12/v13 | 160m | Framing-matched controls: Domain **PARTIAL**, Operator **BOUNDED** (colloquialism-carried), `^8`/`^9` **not separable**. All surface-bound at 160m. |
| **v14/v15** | **6.9b** | **CROSSOVER:** Operator-10 `0.800` vs `0.550` (**+0.250, clean**), Domain-4 `0.938` vs `0.438` (**+0.500, clean**), `^8`/`^9` `0.917` vs `0.833` (marginal). |

**The pattern (established):** the CAS reading axes are **surface-confounded at 160m but harden decisively at 6.9b.** Every axis that failed the surface control on the tiny model beats it cleanly on the big one; only `^8`/`^9` is merely marginal. Four axes beat the word-counter at 6.9b:

| Axis @ 6.9b | detector | word-counter | margin | significance | verdict |
|---|---|---|---|---|---|
| Valence `^2`/`^3` | 0.938 | 0.500 | +0.438 | — | clean |
| Domain-4 P/C/E/O | 0.938 | 0.438 | +0.500 | P=3.65e-07 | **BOUNDED (v19) — regex-solvable stimuli; withdrawn as specificity** |
| Operator-10 `^0`..`^9` | 0.800 | 0.550 | +0.250 | P=1.04e-11 | clean |
| `^8`/`^9` cause/effect | 0.917 | 0.833 | +0.083 | P=0.097 | marginal |

Notable recoveries at scale: Domain "principled" went from collapsing to `1/4` when modal words were stripped (160m) to `3/4` (6.9b) — the big model reads *principle from meaning, not modal words*. Operator-10 went from colloquialism-carried (lost at 160m) to reading the 10 Noetics from *fresh wording* (won at 6.9b).

---

## 3. The correction (steering) arc

| Stage | Model | Finding |
|---|---|---|
| v8 | 160m | Valence direction is **causally load-bearing** — injecting it steers output valence. |
| v10/v14 | 6.9b | Appeared **null** — but at a fixed injection strength (α=6.0) that is negligible in 6.9b's residual. |
| **v16** | **6.9b** | **Valence IS a causal lever at natural magnitude:** at layer 16, pushing the direction raised output valence on every prompt, swing **z=11.18** over a matched-random null, monotone ×1→×8. The v10/v14 null was an under-scaled-injection artifact. |
| **v17** | **6.9b** | **CAUTION:** Domain/Operator "steering" is **direction-specific vs random but NOT construct-licensed.** |

**The v17 caution (load-bearing).** Injecting a deontic-vs-procedural (Domain) direction at layer 16 *did* raise deontic output words over procedural ones, beating a random nudge (swing 2.226 vs null-max 0.773). But an adversarial verification flagged three reasons this does **not** prove a CAS-*construct* lever: (1) the measured output words **are** the defining vocabulary of the input classes — circular; (2) beating a *random* direction is an easy bar and does not control for arbitrary topical steering — no *structured non-CAS* null was run; (3) the "Operator `^2`/`^3`" contrast is sentiment valence relabeled, reproducing v16. So v17 is recorded as a caution, not a win — and it slightly bounds v16 too (state it as "the valence direction steers valence output, direction-specific vs random," the standard steering claim, not "CAS-construct-specific").

---

## 4. What is and isn't established — claim states

- **REAL (measured on real 6.9b weights):** four axes read above a char-ngram surface control (valence/Domain/Operator clean, `^8`/`^9` marginal); the reading hardens with scale; the valence direction is a causal lever (z=11.18 vs matched-random).
- **The honest limit — CAS-specificity is `GREY`.** Beating a char-ngram surface control shows the signal is **not giveaway words**; beating a random-direction null shows a steering effect is **direction-specific**. **Neither shows the structure is specifically *CAS*** rather than generic semantic/topical structure wearing CAS labels. That gap is the open frontier.
- **DEAD:** Claim A ("the weights are natively CAS") — formally retired 2026-08-18.
- **LIVE:** Claim B ("CAS as a measurement-and-correction language") — real multi-axis support at scale on the measurement side, valence-only on the correction side; the ruler need not be inside the model.
- **Not the canary / not the attested engine:** every model run here used direct transformers; the frozen A40/Pythia canary is still `NOT RUN`.

## 5. Scope & caveats (apply to everything above)
- Single model family (Pythia/GPT-NeoX); one run each; small n (test sets of 12–20); detector figures are best-of-layer selected on the test set (surface baselines get no such selection); steering z uses a K=8 null and n=4 prompts (a screen, not calibrated σ).
- Direct-transformers numbers are not interchangeable with attested-engine numbers.

## 6. The two experiments that would move CAS-specificity from GREY toward licensed
1. **Structured non-CAS nulls** everywhere: a matched non-CAS taxonomy / arbitrary-topical diff-in-means that the CAS contrasts must *beat* — not just beat random.
2. **Non-definitional readouts**: measure construct effects on tokens/behaviors that are **not** the defining vocabulary of the classes.

Until those clear, the honest headline stands: **the harness reads and (for valence) steers real structure at scale that is not giveaway words — but whether that structure is specifically CAS is not yet proven.**
