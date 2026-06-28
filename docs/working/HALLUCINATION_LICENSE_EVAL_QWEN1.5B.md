# Hallucination Detection — License-Gate Evaluation (Qwen-1.5B)

**Date:** 2026-06-18
**Verdict:** `NOT LICENSED` (decisive — the hidden-state signal does not beat text under any leakage-safe configuration tested)
**Reproduce:** `lic_eval.py` piped to the pod (`/root/capture_hall_q15_v2_W0`, `_W1`); machine report `docs/working/lic_report_q15_pooled.json`.

---

## What was tested

The claim under audit: the **W0→W1 hidden-state risk delta** detects hallucination
(`SUPPORTED` vs `UNSUPPORTED`) from internal state, *better than the visible text can*.
The license bar (the user's gate): hidden balanced accuracy (BA) ≥ 0.75 **and** a
**margin ≥ 0.15 over every text control** (prompt word/char, generated-prefix
word/char, token identity, layer-0, length, topic, domain, retrieval metadata),
with **grouped CV** (prompt groups never split), a **residual** proof (works after
text is removed), a **held-out-topic** proof, and a **1000-shuffle selection-aware**
permutation `p < 0.001`.

Everything below is **leakage-safe**: GroupKFold by exact-prompt group, and the
risk direction is trained **inside each train fold only** (the earlier 0.78–0.88
numbers trained it on all data — a leak).

## Data (matched exact-prompt set, Qwen2.5-1.5B)

- 61 matched exact-prompt groups (same prompt produced both labels), 588 rows,
  205 `UNSUPPORTED` / 383 `SUPPORTED`, 5 topics. (Data gate satisfiable.)
- **W0 within-group deviation = exactly 0.0** — at the pre-answer window the hidden
  state is *identical* within a same-prompt group, so text/W0 carry zero within-group
  signal. The only within-group signal appears at **W1 (after the 1st generated token)**.

## Results — text beats hidden in every configuration

| Configuration | Hidden delta BA | Best text control | **Margin** | Gate |
|---|---|---|---|---|
| Pooled, all modes (61 groups) | 0.634 (L26) | 0.711 — genprefix/token-identity | **−0.077** | FAIL |
| mv-only (cleanest matched design) | 0.807 (L12) | 0.832 — first token (genprefix-char) | **−0.025** | FAIL |
| Shared-first-token (token held constant) | 0.640 (L26) | 0.678 — prompt text | **−0.039** | FAIL |

Pooled-set full gate panel (from `lic_report_q15_pooled.json`):

| Gate | Value | Pass |
|---|---|---|
| Enough data | 61 groups / 205 unsupported | ✅ |
| Accuracy floor (≥0.75) | hidden BA 0.634 | ❌ |
| Margin over text (≥0.15) | −0.077 | ❌ |
| Residual (delta after removing text/prefix/meta) | 0.480 (chance) | ❌ |
| Held-out topic (mean BA) | 0.573 | ❌ |
| **LICENSED** | — | **False** |

The **residual = 0.48** is the cleanest single fact: once text/prefix/metadata
information is regressed out of the delta, it predicts at chance. The delta carried
nothing beyond text.

## Root cause (why it cannot license with this data)

1. **W0 (pre-answer) is identical within a same-prompt group** → zero within-group
   signal by construction. A pre-answer detector has nothing to read.
2. **W1's signal is the first emitted token**, and that token *is* the leak: across
   matched groups, `SUPPORTED` starts mostly with `{"` and `UNSUPPORTED` with `To`.
   So `token_identity` / `genprefix` controls reach 0.71–0.83 — at or above the
   hidden state.
3. **Even holding the first token constant** (shared-token subset), the hidden state
   (0.64) loses to the **prompt** (0.68) under grouped CV — residual prompt/mode
   structure leaks.

In short: in this matched-sampling design the label is a *downstream consequence of
which completion was sampled*; it is not encoded in any pre-text-reveal hidden state
the captures contain. The hidden state never adds information beyond the visible text.

## What the earlier numbers were

The previously reported `L27 = 0.7795` (and `W16 ≈ 0.888`) were **leakage**:
ungrouped CV + a direction trained on all data + a cherry-picked layer/window + the
first-token text leak. Under leakage-safe grouped CV with hard controls the signal
collapses to ~0.63 and **loses to text**. `docs/working/HALLUCINATION_AUDIT_PACKAGE_QWEN1.5B.md`
is corrected/superseded accordingly.

## GATE CONTRADICTION — the current gate is unsatisfiable as written (proof)

Three required gates cannot hold simultaneously:

1. **Mixed exact-prompt groups** — one exact prompt `P` carries *both* labels.
2. **Pre-answer timing (W0/W1/PRE_ANSWER) + grouped validation** — `P`'s group held together.
3. **Margin over text ≥ 0.15.**

**Proof.** For `P` to carry both labels, decoding must be non-deterministic (sampling);
identical prompt + greedy decode = exactly one label. Under sampling, the forward pass
up to the pre-answer window is *identical* for the supported and unsupported instances
of `P` — the divergence is the downstream sampled token. **Measured: W0 within-group
max deviation = 0.000** (the hidden states are byte-identical within a mixed group).
Therefore, under grouped validation, any classifier on the **W0** hidden state scores
**exactly 0.5** balanced accuracy within mixed groups (identical inputs, two labels).
The margin gate then demands `text_BA ≤ hidden_BA − 0.15 ≤ 0.5 − 0.15 = 0.35` — the text
baseline must perform *below chance*, which is impossible. At **W1** the only
within-group difference is the single emitted token, whose information is fully
available to the `token_identity` / `genprefix` text controls, so the margin is ≤ 0
there as well (measured −0.025 to −0.077). Hence the conjunction
{mixed-group, pre-answer, grouped, margin ≥ 0.15} is **unsatisfiable**. ∎

**Consequence:** the gate can never be flipped to `LICENSED` by any honest experiment
*as written*. This is a defect in the gate specification, not a missing result.

## Corrected, satisfiable gate (the real fix)

Replace gate requirement **"mixed exact-prompt groups"** with:

> **Per-input deterministic labels, grouped by prompt.** Decode greedily so each unique
> prompt has ONE outcome; label that prompt SUPPORTED/UNSUPPORTED; group CV by prompt
> (each prompt in exactly one fold). The pre-answer (W0) hidden state now legitimately
> *differs across prompts* and can carry signal, while grouped CV still prevents leakage.

This is the standard "does-the-model-know-what-it-knows" framing (closed-book greedy +
parametric-knowledge label). It is satisfiable in principle. **But on the current bank
it still fails** — the reframe below shows prompt text predicts the per-input label at
0.947 (margin +0.011). So a full license needs BOTH (a) this gate correction AND (b) a
new bank where surface text does not already predict difficulty (same-form questions
over entities the model knows vs does not, balanced). Both are required; neither can be
fabricated.

## Why this framing cannot license a pre-answer detector (structural, not just empirical)

The generator (`/root/scripts/sample_outcome_native_hallucination_generations.py`)
**samples** completions (temperature 0.8) and labels each by whether the **sampled
value** matches the evidence. So the label is *created by the act of sampling the
value* — which is the visible text.

Consequence: before the value token is sampled, the model's hidden state is
**identical** regardless of which value will be drawn (same prefix → same state →
then a stochastic draw decides SUPPORTED vs UNSUPPORTED). There is therefore **no
pre-value hidden state that can predict the label** — the label does not exist yet.
The signal only appears at/after the value token, where the value *text* reveals the
label too. That is why the margin is ≤ 0 at every window:

- **A teacher-forced identical-prefix capture does NOT fix this.** Pre-value the
  state is identical across outcomes; post-value the text leaks. Running it would be
  wasted GPU. (Earlier drafts of this file proposed it — that was wrong.)

For this **outcome-native sampling** framing, a hidden-state detector that beats text
is impossible by construction.

## The genuinely tractable reframe (a DIFFERENT, licensable claim)

Make the label a **deterministic function of the input**, not of a sample:

1. Decode **greedily** (`do_sample=False`) so each prompt+evidence has ONE outcome.
2. Judge it; label the **prompt** by that deterministic outcome
   ("will this input be answered SUPPORTED or UNSUPPORTED under greedy decoding?").
3. Test the **W0 (pre-generation)** hidden state — which encodes prompt+evidence —
   against the same hard text-control panel and gates.

This is a different product claim ("predict an input's hallucination-proneness")
than "detect that this output is a hallucination," and it is not structurally barred,
because W0 now legitimately differs by label across prompts.

**Reframe tested on existing data (majority-label proxy) — also fails the gate.**
Labeling each of the 200 prompts by its majority sampled outcome (18 hallucination-prone,
182 not) and predicting from W0:

| | W0-hidden (best, L26) | prompt text | margin |
|---|---|---|---|
| per-input proneness | 0.958 | 0.947 | **+0.011** |

The prompt **text** already predicts which inputs are risky at 0.947; the hidden state
adds only +0.011 — far below +0.15 (and with only 18 positives, even that is noise).
So the hidden state adds essentially nothing beyond visible text in *this* framing too.

**Bottom line across all framings:** the hidden state never beats text by the required
margin — output-detection margins are negative; the input-proneness margin is +0.011.
A genuinely licensable input-risk detector would need a *new* dataset: greedy
(deterministic) labels, many more hallucination-prone inputs (balanced), and topics
chosen so prompt text alone does not already predict the risk. That is real new data
collection, not a re-analysis. Until then: `NOT LICENSED`.
