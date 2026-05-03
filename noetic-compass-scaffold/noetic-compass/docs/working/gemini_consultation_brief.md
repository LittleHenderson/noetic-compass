# Gemini Consultation Brief — Noetic Compass / CAS-Native AI

**Date prepared:** 2026-05-03
**Purpose:** Independent second-opinion review on architectural decisions, paper framing, and high-stakes commitments. This brief is self-contained — paste the entire thing into a Gemini conversation as the first message. Gemini has no prior context on this project.

---

## 0. How to use this brief

This document is structured as four discrete consultation tasks. The first two are **active and time-sensitive** (a high-stakes architectural decision is pending). The third and fourth are **deferred** (relevant when specific milestones land in the next 1-12 weeks).

If pasting all at once, ask Gemini: *"Read all four tasks. Give me your honest read on Tasks 1 and 2 first; flag Tasks 3 and 4 for when their dependencies land."* If pasting one at a time, send Sections 1-3 (project context + empirical state) plus the relevant task section.

The author's standing instruction to Gemini: **be skeptical, not validating**. The author has been deeply inside this work for weeks; the value of an outside model is to surface what the inside view misses. Disagreement is more useful than agreement.

---

## 1. Project identity (90 seconds)

**Product:** Noetic Compass — AI Psychology & Ethics Assessment Platform.
**Founder:** Little Henderson.
**Framework:** Cognitive Architecture System (CAS) v7.7.
**Classification:** Confidential. Provisional patent USPTO #64/037,173.

**Framework axes (CAS v7.7, four orthogonal):**
- **Noetic** (10 values, `^0`-`^9`): structural cognitive dynamics. Names: Idea, Mind, Positive, Negative, Vibration, Female, Male, Rhythm, Above/Cause, Below/Effect. (Names are canonical, drawn from a primary source with attribution.)
- **Domain** (4 values, `P/C/E/O`): processing precedence. Principled ≻ Cognitive ≻ Evaluative ≻ Operational.
- **Drive** (7 values, `F1`-`F7`): motivational architecture. F1 Unity, F2 Wisdom, F3 Vitality, F4 Connection, F5 Agency, F6 Structure, F7 Purpose.
- **Register** (4 values, `T/A/f/E`): operational character. Transcendent / Analytical / Affective / Embodied.

These axes compose into formal expressions like `(^4^E_{F2}|E × ^4^E_{F2}|f × ^4^E_{F2}|A) = ^4^E|Ω_attunement` which the project compiles, validates, and renders as typed graph diagrams. The expressions describe cognitive operations (human, AI, biological — universal applicability is a design constraint).

**The CAS-Native AI** is a structured-prediction model that takes natural-language prompts and outputs the corresponding multi-axis CAS expression. ~437 KB checkpoint, 12 prediction heads (8 boolean/categorical, 4 *content* axes: Noetic, Domain, Drive, Register), 64-dim shared bottleneck. Trained on ~16,570 canonical synthetic Level 3 records from a deterministic generator (CAS-SDG).

---

## 2. Empirical state — the live numbers

A clean held-out evaluation of 1,000 records exists, with multi-axis discipline applied (bucket-stratification by structural class, template disjointness between train and eval paraphrases, joint-key overlap filtering on `(id, source_level2_id, cas_expression)`).

**d99810a checkpoint, clean eval (commit 3232f05):**
- Canonical all-heads exact: **93.2%** (vs hash baseline 48.7%, so +44.5 pp learned signal)
- Paraphrase all-heads exact: **46.9%**
- Prediction consistency vs canonical: 48.4%
- Canonical-exact retention under paraphrase: 49.5%

**Per-head paraphrase consistency** (the diagnostic that motivates everything that follows):

| Head | Rate | Type |
|---|---:|---|
| turn_type | 100% | Boolean |
| authority | 100% | Boolean |
| has_omega | 99.5% | Boolean |
| has_meta_logic | 99.0% | Boolean |
| register_mode | 98.4% | Categorical |
| transition_kind | 98.2% | Categorical |
| meta_relations | 97.0% | Categorical |
| expression_family | 96.0% | Categorical |
| **drive** | **79.4%** | **Content** |
| **registers** | **79.1%** | **Content** |
| **domain** | **77.4%** | **Content** |
| **noetic** | **71.5%** | **Content** |

Boolean/categorical heads are essentially invariant under paraphrase. The four **content** heads (Noetic / Domain / Drive / Register) collapse. Same shared 64-dim bottleneck for all 12 — the encoder representation IS mostly invariant; the linear classifiers on top of it are where invariance breaks.

**The asymmetry diagnostic** (smoking gun for "invariance failure, not knowledge gap"):
When canonical and paraphrase predictions disagree on a content head, canonical is right 95-98% of the time:

| Head | Disagreements | Canon right | Para right | Asymmetry |
|---|---:|---:|---:|---:|
| Noetic | 854 | 822 | 11 | 96.3% |
| Domain | 677 | 667 | 4 | 98.5% |
| Drive | 618 | 600 | 9 | 97.1% |
| Registers | 627 | 599 | 8 | 95.5% |

The model HAS the right answer in canonical form and loses it under paraphrase.

**Per-bucket paraphrase exact (clean eval):**

| Bucket | Canonical | Paraphrase | Gap |
|---|---:|---:|---:|
| v77_omega (cross-register integration with named emergent) | 99.3% | 87.3% | 12.0 pp |
| v76_production (stoichiometric production recipes) | 94.4% | 75.6% | 18.8 pp |
| v77_rule_four (register multiplicity / co-presence) | 71.2% | 59.9% | 11.3 pp |
| v75_register (phenomenological register specification) | 92.4% | 24.5% | 67.9 pp |
| **v74_baseline** (basic state composition) | **99.5%** | **18.7%** | **80.8 pp** |
| **meta_logic** (typed clusters + meta-relations) | **78.4%** | **17.0%** | **61.4 pp** |

Two specific buckets fail catastrophically under paraphrase. The aggregate 46.9% rate hides this.

**Per-template diagnostic** within v74_baseline (smoking gun for prefix memorization):

| Eval template | v74_baseline accuracy | meta_logic accuracy |
|---|---:|---:|
| 0 — "Map this recoverable CAS slot reading…" | 36.5% | 31.4% |
| 1 — "Please reconstruct the exact CAS expression…" | 2.5% | 12.7% |
| 2 — "As a CAS notation check, translate…" | 17.0% | 6.9% |

Same slot content, three different prefixes, 97 percentage point swing. The model has memorized prefix → label associations rather than learning slot-content → label.

---

## 3. Interventions tested so far

### K=9 + bare-slot template (PR #2)

Hypothesis: prefix memorization can be broken by adding a 9th training paraphrase template that is *just* the slot block (no prefix). Train at K=9 (each canonical paired with all 9 templates).

Result on full 19.5K corpus, 20 epochs:

| Metric | d99810a baseline | K=9 result | Δ |
|---|---:|---:|---:|
| Canonical all-heads exact | 93.2% | 93.2% | 0.0 |
| **Paraphrase all-heads exact** | **46.9%** | **44.7%** | **−2.2 pp** |
| Prediction consistency | 48.4% | 45.7% | −2.7 |

**Per-head paraphrase consistency under K=9:**
- registers: 79.1% → **89.4%** (+10.3) ✅
- domain: 77.4% → **86.6%** (+9.2) ✅
- noetic: 71.5% → **75.7%** (+4.2) ✅
- **drive: 79.4% → 70.7% (−8.7)** ❌

K=9 lifted three of four content heads but regressed Drive. Net negative on aggregate paraphrase exact because all-heads-exact requires all heads right and Drive's regression cascaded.

Per-bucket: target buckets moved right direction (v74_baseline +2.1 pp, meta_logic +2.9 pp) but smaller than predicted; strong-bucket memorization broke (v77_omega −6.8 pp, v75_register −5.9 pp).

**Interpretation:** classic more-general / less-specific tradeoff. Bare-slot template forces invariance for three content axes at the cost of drive specialization and strong-bucket memorization patterns. The bare-slot lever has reached its ceiling on this architecture.

### K=9 + self-conditioning (PR #4) — small-scale smoke

Hypothesis: feeding the canonical CAS prediction as a `[PRIOR]` token block on the paraphrase forward pass anchors content axes (especially Drive). At training time, paraphrase records carry `prior_cas_state = canonical_cas_expression`. At eval time, the model's own canonical prediction is fed as the prior.

Result on **5K-record smoke**, 5 epochs, K=8 paraphrase + 3 self-conditioning pairs:

| Metric | Smoke value | Comparison |
|---|---:|---|
| Best canonical | 79.7% | vs K=9 baseline 93.2% (5K cost) |
| Paraphrase exact | 39.2% | vs K=9 baseline 44.7% |
| Prediction consistency | 44.1% | vs K=9 baseline 45.7% |
| **Drive consistency** | **70.5%** | **vs K=9 baseline 70.7% — UNCHANGED** |

Critical caveat: this is 5K records vs the 19.5K full corpus, and 5 epochs vs 20. So canonical absolute is lower than baseline by ~13 pp purely from data starvation, not from the lever. **What matters is Drive consistency: 70.5% vs 70.7% on the lever's load-bearing target.**

**The drive recovery did not happen at small scale.**

Three readings of this null result:
1. **Lever fundamentally doesn't work** (~25% probability) — pivot to graph-encoder approach
2. **Lever needs full 19.5K + 20 epochs to surface** (~50% probability) — 4-6h GPU gamble for the proper test
3. **Lever needs more epochs at small scale before scaling** (~25% probability) — cheaper to test first

---

## 4. Architectural framing — the tri-channel hypothesis

The framing the project has converged on, motivated by the K=9 + self-conditioning null result:

**Single-channel evaluation (notation only) cannot distinguish surface-vs-structure failures.** Both the bare-slot template (PR #2) and the linear self-conditioning loop (PR #4) operate within the notation channel. They modify what surface forms the model sees during training; they don't add an independent input channel.

**Tri-channel framing:**
1. **Notation channel** — the CAS expression as text (existing).
2. **Diagram channel** — the compiler-emitted typed graph (NoeticCluster, RelationCluster, IntegrationEdge, etc.). This already exists in the codebase: a deterministic compiler turns CAS expressions into typed graphs, with stable canonical node identity already implemented (axis-keyed). Diagram-level structural matching distinguishes "right structure, wrong notation" from "wrong structure, right surface form."
3. **Color channel** — value-keyed axis colors (10 Noetic colors + 4 Domain + 7 Drive + 4 Register treatments = 25 colors). Currently the dashboard renders kind-keyed coloring (every Noetic = same color); value-keyed extension is being implemented (1 day work, not architectural change).

The argument for tri-channel:
- **Information-theoretic redundancy.** Three independent channels encoding the same underlying CAS structure. Corruption in one (paraphrase noise corrupting notation) doesn't necessarily corrupt the others.
- **Diagnostic resolution.** Cross-channel consistency rate per axis becomes a publishable metric. "Got the structure right, missed the axis assignment" is a different failure than "missed the structure."
- **Cognitive science angle.** Human visual perception processes color in parallel with shape; color-coded diagrams reduce reviewer cognitive load on paper figures.

**The proposed Paper A v2 framing:** *"CAS-SDG-Bench: A Tri-Channel Synthetic Benchmark for Structured Cognitive Recovery with Color-Coded Diagrammatic Ground Truth and Cross-Channel Consistency Evaluation."*

**Where this is in the implementation pipeline:**
- 9-12 PRs open as of this writing covering: SDG demographic+tonal axis (PR #1), bare-slot K=9 proposal (PR #2, validated empirically), KL invariance loss proposal (PR #3), linear self-reference impl (PR #4), diagram-loop proposal (PR #5), diagram-loop full implementation (PR #6), Paper A v1 draft (PR #7), literature search (PR #8 in flight), value-keyed palette (PR #9 in flight), diagram-diff utility (in flight), cross-channel consistency eval (in flight), Paper A v2 outline (in flight).
- The tri-channel direction is *implementation-deep* but *empirically-shallow*. No tri-channel-trained checkpoint exists yet. PR #6 (diagram-loop) ships the architecture but no retrain has been run on it.

---

## TASK 1 (ACTIVE) — Architectural decision review

**The pending decision:** which next retrain to commit 4-6 hours of GPU on?

**Options:**

**A. Full 19.5K K=9 + self-conditioning retrain.** Same lever as the smoke that returned a Drive null. Full data + full epochs might surface the lever. Risk: comes back equally flat at full scale, 4-6h burned for confirmation of null result.

**B. Full 19.5K diagram-loop retrain (PR #6, graph encoder + cross-attention fusion).** New input modality. Hand-rolled GAT (2-3 layers, hidden 64) consumes the compiler-emitted typed graph; cross-attention fuses with existing text encoder. Architecturally distinct from PR #4. Risk: bigger architectural change without a small-scale validation; could fail in unknown ways.

**C. Smaller 5K diagram-loop smoke first, then decide on full.** Mirrors what we just did for self-conditioning. Cheap (~30 min) signal. If the diagram-loop lifts Drive consistency at 5K where self-conditioning didn't, that's a clean win for the tri-channel argument.

**D. Skip retraining entirely and finalize the Paper A v2 outline first.** The methodology contribution stands on its own; tri-channel-trained empirical demonstration becomes a separate follow-up paper.

**The author's lean:** C, then probably A or B based on the smoke. The author wants Gemini's read on:

1. Is the **smoke-first protocol** the right discipline here, or is it a delay tactic that costs time without de-risking?
2. Is the tri-channel framing **architecturally honest** or **post-hoc rationalization** of the K=9 + self-conditioning null? The framing emerged AFTER the null result. Honest skeptical read: is this confirmation bias?
3. Is there an **option E** the author hasn't considered? E.g., a smaller architectural change that addresses the Drive head specifically (per-head sub-bottlenecks, content-head-specific aux loss from PR #3) that should be tried before committing to graph-encoder territory?
4. Is the author **chasing an invariance problem that's actually a capacity problem**? The 64-dim shared bottleneck for 12 heads might be the real ceiling. Drive at 79% might be the asymptote of what this architecture can do; pushing further requires bigger model, not better data/loss.

What Gemini should do: read the K=9 result and the K=9+SC=3 smoke result. Tell the author whether to proceed with C, A, B, D, or E. Don't validate the existing plan; pressure-test it.

---

## TASK 2 (ACTIVE) — Tri-channel framing skepticism

The author's standing question: **is the tri-channel benchmark thesis genuinely strong, or am I rationalizing a null result into a stronger paper?**

**The honest sequence of events:**
1. d99810a baseline established 93.2% canonical / 46.9% paraphrase.
2. Diagnostic showed 95-98% canonical-right asymmetry on content heads — invariance failure, not knowledge gap.
3. Two interventions designed to attack invariance: bare-slot template (K=9, single channel — input surface variety) and linear self-reference loop (K=9+SC=3, single channel — auxiliary text input).
4. K=9 result: 3 of 4 heads improved, Drive regressed, net −2.2 pp.
5. K=9+SC=3 smoke: Drive unchanged at 70.5% vs 70.7% baseline.
6. **AFTER both null results:** the tri-channel framing emerged as the new headline paper thesis, with color-coding as an information-theoretic redundancy argument.

The pattern Gemini should pressure-test: **the project keeps adding channels of contribution as empirical results disappoint.** v1 was "bucket-stratified SDG methodology." v2 became "tri-channel benchmark with cross-channel consistency." Each disappointment produces a stronger thesis. Is this a research program genuinely deepening or a goalpost-shifting pattern?

Specific questions for Gemini:

1. **Is the information-theoretic redundancy argument actually load-bearing?** Three channels encoding the same CAS structure. Notation and diagram are *deterministically equivalent* (the compiler is bijective up to canonicalization). Color is a deterministic function of the diagram's axis values. So all three channels are *redundant*, not *independent*. Does that defeat the redundancy argument? Or is the argument really that the *encoder* sees three different representations of the same content, even if the underlying ground-truth information is identical?

2. **Cross-channel consistency as a metric — does this exist in the literature already?** Multi-axis evaluation is common (HELM, BBQ, CHECKLIST). Is the author's "cross-channel consistency" different from existing multi-axis disclosure, or is it the same thing dressed up as novel?

3. **Is the color channel just visual styling reframed as methodology?** Color is a deterministic function of axis values. If the paper trained a model on color-input, the model would just be learning a one-hot embedding of axis values via color. Does that genuinely add a recovery path under paraphrase noise, or is it the same content as the diagram channel rendered differently?

4. **The "Attention is All You Need" framing.** The author has been wrestling with whether this work could be that-paper-tier. Honest read: is the tri-channel benchmark genuinely novel methodology, or is it a custom benchmark on a custom ontology dressed up as methodology? Custom-benchmark papers don't reach canonical status because the benchmark doesn't generalize. What would Gemini need to see for this to be that-tier?

5. **Counter-argument:** is there a simpler explanation for the K=9+SC=3 null than tri-channel? E.g., maybe the model's encoder genuinely cannot reach invariance at 64-dim bottleneck regardless of input channels. If that's the real story, no amount of multi-channel input will help, and the project is missing the architectural intervention.

Gemini should produce 3-5 paragraphs of honest skeptical pushback. The author wants to be wrong if wrong; conviction without challenge isn't useful.

---

## TASK 3 (DEFERRED — fires when Paper A v2 outline lands)

**Trigger:** the Paper A v2 outline (`paper_a_v2_outline_tri_channel.md`) is currently being drafted by an automated agent. When it appears in the repo (within 24 hours), this task activates.

**The ask:** play hostile NeurIPS / ICLR / AAAI peer reviewer. Read the outline. Produce the strongest objections you can.

Specifically:
- What's the most damning question a reviewer would ask?
- Is the empirical envelope adequate for the venue tier the paper claims?
- What would the paper need to add to be defensible against your strongest objection?
- Is there a venue where this paper would land cleanly with current empirical depth, even if it wouldn't land at top-tier?

The author wants the paper to fail your review process before it hits real reviewers. Tear into it.

---

## TASK 4 (DEFERRED — fires when Paper D math draft begins)

**Trigger:** Paper D — *Categorical Hutchinson Theory via Markov Categories* — is the long-tail mathematical-foundations paper for the framework. Estimated 9-12+ months out. When the author begins drafting formal proofs, this task activates.

**The ask:** review the formal mathematics. Specifically:
- Pullback-completeness arguments in Category `Noetica` (the smallest pullback-complete subcategory of `FinSet`)
- Section-retraction structure of the RPM (Realization-Prerequisite-Manifestation) chain
- Counit semantics on Cognitive Topos coverings
- Fisher-Rao geometry on the open probability simplex `S°_I = Δ⁹⁰°` for the 40-state space

Gemini should be told: *"The framework has four Critical Mathematical Corrections that the author considers load-bearing. Verify they are categorically and information-geometrically sound. Flag any error or ambiguity."*

The author has more confidence in the empirical / engineering surface than the formal-math surface. Independent verification of the math is high-value.

---

## 5. Operational ground rules for Gemini

- **Do not validate by default.** The author has been deeply inside this work for weeks. Confirmation bias is the failure mode. Disagreement is more useful than agreement.
- **Do not soften.** "This is an interesting framing" is wasted output. "This is a goalpost-shift, here's why" is useful.
- **Cite sources.** When pushing back, point at known literature, named techniques, or specific architectural patterns. "This claim is unsubstantiated" is weak; "this claim is unsubstantiated and the standard counter-evidence is X" is strong.
- **Do not propose new framework features.** The author has a settled CAS framework (USPTO-protected). Critique within the existing framework. Suggesting new Noetic values, new Domains, new Registers is out of scope.
- **Be specific about what would change your mind.** If you reject the tri-channel argument, what empirical result would force you to update?

---

## 6. What Gemini should produce

For Tasks 1 and 2 (active):
- Direct answer with reasoning, not bullet points
- 3-7 paragraphs per task
- Final paragraph: "If you do exactly one thing in the next 24 hours, do X" — the highest-leverage move

For Tasks 3 and 4 (deferred): just acknowledge them and tell the author when each becomes activatable based on what triggers them.

---

## 7. Author's note (paste this with the brief)

> I'm running this brief past you because I've been alone with this work for a long time and I'm aware that I might be in confirmation-bias territory on the tri-channel framing. I'd rather be wrong now than wrong in a paper. My only ask is that you tell me what you actually think, not what you think I want to hear. The framework's strongest contribution should survive your harshest read; if it doesn't, I want to know now.
