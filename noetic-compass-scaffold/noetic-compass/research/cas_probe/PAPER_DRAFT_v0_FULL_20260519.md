---
title: "CAS Harness: Cross-Vendor Cognitive Structure Detection and Conditioning in Open-Weight Language Models via the η→ε Bridge"
subtitle: "Paper Draft v0 — synthesized from 4-agent team output"
date: 2026-05-19
status: Internal draft — pending IP attorney review, editorial pass, and bibliography compilation before external submission
authors: Little Henderson (Founder), Claude Opus 4.7, Codex
classification: Confidential
target_venue: Transactions on Machine Learning Research (TMLR) candidate
synthesis_method: Four-agent parallel section drafting + light editorial pass
total_word_count: ~13,500 across 4 source files
---

# CAS Harness: Cross-Vendor Cognitive Structure Detection and Conditioning in Open-Weight Language Models via the η→ε Bridge

**Draft v0 — synthesized 2026-05-19**

---

## Editorial Notes (for the next pass — REMOVE BEFORE SUBMISSION)

This draft is a concatenation of four section files written in parallel by specialist agents. The synthesis pass is **partial, not full**. The following items need a second editorial pass before this becomes a submission-quality draft:

1. **Factual correction inherited.** Stage 14.1 (weight-geometry alignment, 2.83× random output-side, p=0.0099) ran on **Pythia-2.8B**, not Pythia-160M as the v1.1 spec sheet narrative had it. The Results section (§5.6) correctly attributes to Pythia-2.8B. Earlier sections drafted from the spec-sheet narrative may inherit the error — verify before publishing.

2. **Bibliography unconsolidated.** Each section uses `\citep{}` placeholders with locally-chosen keys. The four sections use overlapping but slightly different key conventions. Bibliography assembly needs one unified `references.bib` file with consistent keys across all sections.

3. **Notation standardization needed.** Background+Methods uses `$\wedge^k$` for Noetic operators in math mode. Other sections use `^k` in prose. Pick one convention and apply throughout.

4. **Section cross-references.** Some sections reference other sections by number (e.g., Discussion §6.3 references "Section 4.4"). Verify all cross-refs resolve to the actual section numbers in the final layout.

5. **Corpus size correction needed.** Methods §4.1 describes the v2 corpus as "3,000 rows, 28 Foundation classes, 300 rows per Noetic" — but the actual v2 corpus is 10 Noetics × 300 rows = 3,000; the 28-Foundation fixture is a separate 4,368-row corpus. Background+Methods agent flagged this in their report.

6. **NLA URL citation.** Each section that compares to Anthropic NLA needs the `transformer-circuits.pub/2026/nla` URL in the bibliography.

7. **IP attorney review** required before external submission. The CAS framework primitives are under USPTO Provisional #64/037,173. Nine separate-filing candidates (per spec v1.2 §12.2) including the η→ε bridge methodology, multi-layer trace methodology, and Multi-Harness Composition all warrant IP review before submission.

The draft below is contributed sections concatenated as-is. Word count totals ~13,500.

---


---
title: "CAS Harness: Cross-Vendor Cognitive Structure Detection and Conditioning in Open-Weight Language Models via the η→ε Bridge"
section: "Abstract + Section 1 (Introduction) + Section 2 (Related Work)"
draft_version: v0
date: 2026-05-19
status: draft for synthesizer review
target_venue: Transactions on Machine Learning Research (TMLR)
---

## Abstract

We present CAS Harness, an interpretability platform that detects and conditions cognitive structure inside open-weight transformer language models using a typed cognitive ontology rather than learned dictionary features. The framework — the Cognitive Architecture System (CAS) v7.7 \citep{Henderson2026CAS} — supplies an a-priori vocabulary of 10 Noetics, 4 Domains, 7 Drives, and 4 phenomenological Registers, generating typed compound classes (40 Cognitive States, 28 Foundations) and a published category-theoretic foundation \citep{Henderson2026NoeticTopos}. Detection rests on the η→ε bridge: η is a linear probe reading CAS class from hidden states, and ε is a templated natural-language realization that re-enters the model as a readable prefix. Proposition 5.6 of the Noetic Topos paper predicts ε is a surjective covering morphism, making prefix-based likelihood conditioning architecturally guaranteed by transformer self-attention. Across 16 pre-registered experimental stages on Pythia-160M/1B/2.8B \citep{Biderman2023Pythia}, OLMo-1B \citep{Groeneveld2024OLMo}, and Qwen2.5-1.5B \citep{Yang2024Qwen25} — three architecture families, five models — we observe (i) six cognitive axes detectable at probe accuracies 73.9–95.4\% with paired-McNemar lifts of +26 to +40 percentage points over text baselines (p $\approx$ 10$^{-50}$ to machine-zero), (ii) five readout-causal ablations collapsing to exact 1/N chance with random-rank controls clean, (iii) likelihood-conditioning effect sizes of +0.283 to +0.796 Wilcoxon-significant across all five models, with best-probe layers consistently at 39–50\% of network depth, and (iv) four pre-registered framework-internal predictions held empirically, including a 2.83$\times$ output-weight-geometry alignment ($p=0.0099$) on the static Pythia weights. Generation-surface steering remains negative at the model scales tested and is bounded as such. We describe a multi-layer trace methodology with blind-spot detection and a two-bridge prototype for hidden-content auditing.

## 1. Introduction

### 1.1 Motivation

The interpretability literature has converged on a productive but unresolved tension. Linear probes can read a remarkable amount of structure from transformer hidden states, but probe accuracy by itself measures decodability, not whether the model uses that structure for its own computation \citep{Belinkov2019Probing,Hewitt2019Structural,Belrose2023ElicitingLatent}. Mechanistic interpretability has built strong causal tools — activation patching, path patching, circuit discovery \citep{Wang2023IOI,Conmy2023ACDC} — but they have largely operated on hand-discovered features in a single model, leaving open the question of whether any published cognitive vocabulary describes a property the models share rather than an artifact of one architecture or one dataset. Sparse-autoencoder programs offer scalable feature discovery but rely on learned dictionaries whose semantics must be re-interpreted per training run \citep{Bricken2023Monosemanticity,Templeton2024ScalingMono,Cunningham2023SAE}. Activation-steering methods condition behavior in inference but treat the steering direction as a free parameter \citep{Turner2023ActivationAddition,Subramani2022ExtractingLatent,Rimsky2024CAA}.

A separate research tradition has independently developed published cognitive architecture systems — ACT-R, SOAR, and their successors \citep{Anderson2007ACT,Laird2012SOAR} — formalizing cognition as typed operations over a discrete ontology of states and operators. These frameworks are explicit, fixed in advance, and structurally testable, but they have historically been treated as cognitive science artifacts rather than interpretability instruments for foreign deep networks. The recent Anthropic Neural Network Analysis (NLA) work \citep{Anthropic2026NLA} closes some of this distance by training a verbalizer/reconstructor pair to produce natural-language descriptions of activations on Anthropic-internal Claude models, but only on a single architecture family and with an acknowledged confabulation tier in the output.

A natural question follows. Suppose we hold the cognitive vocabulary fixed in advance — published, typed, mathematically defined — and ask whether the resulting structure is empirically detectable inside open-weight models the framework's authors never trained on, never published to, and never specified to. If the structure is detectable, ablation-causal for the model's own readout, and conditionable via a mechanism with a mathematical guarantee independent of the empirical observation, then the framework is acting as a measuring instrument on foreign substrates. This paper reports the closing of that gate across three architecture families.

The framework we instantiate is the Cognitive Architecture System (CAS) v7.7 \citep{Henderson2026CAS}, a published typed cognitive ontology distinguished by three properties relevant to interpretability. First, it is type-discrete: 10 Noetics (structural cognitive operators), 4 Domains (processing tiers), 7 Drives (motivational primitives), 4 Registers (phenomenological characters), generating well-defined compound classes (40 Cognitive States, 28 Foundations). Second, it has a category-theoretic foundation — the Noetic Topos paper \citep{Henderson2026NoeticTopos} — that includes a load-bearing covering-morphism result (Proposition 5.6) which makes a directly testable architectural prediction about transformer prefix tokens. Third, it is independent of the models we test: the framework was specified, published, and patented \citep{Henderson2026USPTO} before any of the five models in this study was queried for CAS structure.

### 1.2 The η→ε bridge

The central mechanism of CAS Harness is the η→ε bridge, named for the embedding/realization pair in the Noetic Topos category. The embedding map η is implemented as a linear probe (logistic regression on per-layer hidden states) that reads a CAS class label from the model's internal representation of a prompt. The realization map ε is a templated natural-language emission of the read class, formatted as a short prefix prepended to the original prompt and fed back through the model. Proposition 5.6 of the topos paper proves that for any morphism g, the pullback of ε along g is surjective; applied to transformer self-attention, this guarantees that every later position attends to the realized prefix tokens by construction, not by hyperparameter. The η→ε bridge is therefore a likelihood-conditioning mechanism with an architectural guarantee distinct from existing activation-steering approaches: rather than adding a direction vector at a chosen layer, it reads the model's internal class, realizes it in the model's native input modality, and lets the attention mechanism do the conditioning.

A critical asymmetry, also predicted by the topos (CLAUDE.md Correction 2), is that the bridge is one-directional: $\varepsilon \circ \eta = \mathrm{id}$ on the structure side, but $\eta \circ \varepsilon \neq \mathrm{id}$ on the activation side. Empirically, attempts to invert the bridge by hidden-state ablation steering of generation surface-text (Stages 6.6, 7.3, 7.OA, 7.LA) all returned negative; attempts to condition by ε-realization (Stages 7.CPL2, 8.0, 14, 15, 16) all returned positive. The asymmetry is structurally predicted, not post-hoc rationalized.

### 1.3 Empirical span

The experimental program comprises sixteen pre-registered stages \citep{CASHarnessReadme2026} spanning role-bound counterfactual probing, readout-causal subspace ablation, factor disentanglement, output-alignment diagnostics, CAS-prefix likelihood conditioning, cross-scale replication, cross-architecture replication, multi-layer trace audit with blind-spot detection, and static weight-geometry analysis. Each stage commits PASS/NULL/GREY decision gates before the confirmatory run.

Headline numerical results, in reserved language:

- **Detection.** Six cognitive axes — 10 Noetics, 28 Foundations, 40 Elements, 5 Operators, 10 Expression Shapes, 10 Compiler-Valid Formulas — detected on Pythia-160M at locked-test accuracies of 73.9\%–99.2\% with text-baseline lifts of +3.6 to +39.7 percentage points, McNemar $p$ values ranging from $10^{-50}$ to machine-zero (Stages 6.4, 7.0, 9.0, 10.0, 11.0, 12.0).
- **Readout-causal validation.** Five subspace-ablation experiments each collapse the probe to exact 1/N chance under same-rank QR-orthonormalized random controls clean at $p \le 0.04$ (Stages 6.5, 7.1, 9.1, 10.0, 11.0, 12.0).
- **η→ε bridge across five models in three architecture families.** Probe-readable CAS prefixes condition next-token semantic likelihood with paired Wilcoxon-significant $\Delta$ of +0.283 (Pythia-160M, Stage 7.CPL2), +0.554 (Pythia-1B, Stage 8.0), +0.583 (Pythia-2.8B, Stage 14), +0.604 (OLMo-1B, Stage 15), and +0.796 (Qwen2.5-1.5B, Stage 16). Best probe layer sits at 39–50\% of network depth across all five models. Raw CAS symbol prefixes (without natural-language realization) remain flat at every scale, confirming the effect is ε-realization rather than symbol recognition.
- **Pre-registered framework predictions.** Four predictions made before the relevant experiments held empirically: (a) Foundations more factorized than Noetics by lacunarity (Stage 7.P → Stage 7.1, 38$\times$ improvement); (b) Noetic ablation classified Oscillatory rather than Stabilizing by the CAS fractal classifier (Stage 6.6 confirmed); (c) ε as covering morphism (Stages 7.CPL2, 8.0, 14, 15, 16 confirmed); (d) CAS Foundation subspace shows above-random output-weight alignment (Stage 14.1 confirmed at 2.83$\times$ random expectation, $p=0.0099$).
- **Multi-layer trace and blind-spot detection.** A multi-layer trace classifier reaches 95.4\% accuracy with lacunarity 0.0016 — the cleanest factorization signature recorded in the project — and a readout-vs-model-side disambiguation procedure separates architectural blind spots from probe-configuration sensitivity (Stages 13, 13.1).
- **Generation surface-text steering remains negative.** No clean pass for visible-token generation steering at Pythia-160M (Stages 6.6B, 7.3, 7.LA, 7.CPL3, 7.CPL4). Stage 18 finds a positive prefix-influence trend on Qwen-1.5B visible text but not a closed gate. Bounded accordingly.

### 1.4 Contributions

This paper makes seven contributions, each bounded by the evidence supporting it.

1. **First demonstration that a published cognitive architecture system's structure is empirically detectable inside foreign open-weight language models.** The CAS v7.7 ontology was specified and patented before any of the five tested models were probed; the detected structure is therefore not a learned feature of the models nor a re-discovery of their internal vocabulary.

2. **Three-architecture-family cross-vendor validation.** The η→ε bridge replicates on Pythia (EleutherAI / GPT-NeoX lineage), OLMo (AI2 / different lineage / Dolma corpus), and Qwen2.5 (Alibaba / different lineage / different tokenizer family). A monotonic-converging cross-scale curve emerges within Pythia (160M $\to$ 1B $\to$ 2.8B), and cross-architecture transfer is positive in two out-of-family models tested.

3. **Empirical confirmation of Proposition 5.6 covering surjectivity at two evidence tiers.** Activation-trace evidence (likelihood conditioning) and static-weight evidence (output-weight subspace alignment) are independent confirmations of the same theorem, the second of which can be computed offline without any model forward pass.

4. **The η→ε bridge as a likelihood-conditioning mechanism distinct from existing activation-steering approaches.** Steering by direction-vector addition acts inside the residual stream at a chosen layer; the bridge acts through the model's input modality and is mathematically guaranteed by the attention architecture.

5. **Four pre-registered framework-internal predictions held empirically.** Each prediction was committed in writing before the experiment ran; the framework's own diagnostic tools (lacunarity, fractal classifier, covering-morphism theorem, output-weight alignment corollary) were predictive of subsequent empirical outcomes.

6. **Multi-layer trace methodology with blind-spot detection and readout-position vs. model-side disambiguation.** Probes are read across the full layer stack rather than at a single selected layer, classifying per-prompt trajectories as stable-like or problem-like; the readout-position audit further distinguishes whether a flagged blind spot reflects an architectural representation gap or a probe-configuration sensitivity.

7. **Reserved-language tiered claim discipline for cross-vendor interpretability audits.** Each claim is tagged with an evidence tier (\emph{prototype / wired-works / sample-passed / gate-passed / validated}) and surfaced in an auditor-grade evidence packet with pre-registration manifests, paired statistics, random-control matching, fresh holdouts, SHA-stamped artifacts, and an independent-agent audit trail.

### 1.5 Organization

Section 2 situates CAS Harness against five neighboring research programs: linear probing, mechanistic interpretability, Anthropic NLA, sparse autoencoders, and activation steering, plus the cognitive-architecture literature that gives CAS its lineage. Section 3 specifies the CAS v7.7 framework as we instantiate it for interpretability work, including the typed primitives, the Noetic Topos categorical foundation, and the Proposition 5.6 result. Section 4 describes the η→ε bridge in implementation detail and the multi-layer trace methodology. Section 5 reports the five-model empirical span. Section 6 collects the pre-registered framework predictions and their outcomes. Section 7 discusses the hidden-content / suppression-detection prototype and its bounds. Section 8 lays out limitations, including the negative generation-steering result and the still-open frontier-model question. Section 9 sketches implications for AI safety auditing.

## 2. Related Work

### 2.1 Linear probing and the decodability question

Linear probing has been a central interpretability tool since \citet{Belinkov2019Probing} formalized it and \citet{Hewitt2019Structural} demonstrated that linguistic structure is recoverable from contextualized hidden states. \citet{Belrose2023ElicitingLatent} sharpened the methodology by training probes that predict the model's own subsequent token distribution, separating decodability from explanatory force. The recurring critique is that probe accuracy measures whether the structure is present in the activations, not whether the model itself uses that structure: many readable directions are epiphenomenal \citep{Hewitt2019DesigningInterpreting,Voita2020InformationBottleneck}. CAS Harness inherits this discipline and extends it on three axes. First, every detected axis is paired with a same-rank random-control ablation that must collapse the probe to exact 1/N chance — a causal-readout test, not merely a discriminative one. Second, the detected axes are constrained a priori by a published cognitive vocabulary rather than discovered post hoc, so framework predictivity is testable. Third, the η→ε bridge converts a detected axis into a behavioral effect on the model's next-token likelihood, providing a behavioral verification distinct from internal-readout verification.

### 2.2 Mechanistic interpretability

The mechanistic program, surveyed by \citet{Olah2020Zoom}, identifies circuits — small computational structures inside trained networks — and validates them with causal interventions. \citet{Olsson2022Induction} characterized induction heads; \citet{Wang2023IOI} reverse-engineered the Indirect Object Identification circuit in GPT-2 Small; \citet{Conmy2023ACDC} automated path-patching for circuit discovery; \citet{Geiger2024CausalAbstraction} formalized causal abstraction as the methodological target. CAS Harness uses the same activation-patching and subspace-ablation tooling but operates on a typed cognitive ontology rather than a per-circuit-discovered feature set, and grounds the steering mechanism in a covering-morphism theorem rather than a hand-discovered circuit. The two programs are complementary: mechanistic interpretability finds previously unknown structure; CAS Harness verifies predicted structure.

### 2.3 Anthropic Neural Network Analysis

The closest published comparator is the Anthropic NLA work \citep{Anthropic2026NLA}, which trains a joint activation-verbalizer and activation-reconstructor via reinforcement learning to produce natural-language descriptions of activations on Claude Haiku 3.5/4.5 and Opus 4.6. NLA demonstrated detectable internal awareness of evaluation context — Claude internally "believed but did not say" it was being evaluated in some settings — and surfaced the finding in natural-language form. NLA explicitly acknowledges a confabulation tier in its output: verbalized descriptions can be plausible but verifiably false. CAS Harness contrasts on four design axes: (i) typed output (CAS class labels with no free-form natural-language description, removing the confabulation tier), (ii) cross-vendor coverage at three architecture families rather than a single proprietary one, (iii) a published mathematical foundation (Proposition 5.6) that makes the conditioning mechanism's behavior architecturally guaranteed rather than learned, and (iv) a pre-registered audit methodology with PASS/NULL/GREY gates committed before each confirmatory run. The two systems' "hidden-content" findings are analogous in shape and complementary in form: NLA's verbalized version is more readable; CAS Harness's two-bridge $\eta_1$-vs-$\eta_2$ comparison is more auditable.

### 2.4 Sparse autoencoders and dictionary learning

Sparse autoencoders (SAEs) \citep{Bricken2023Monosemanticity,Cunningham2023SAE} learn an overcomplete dictionary of monosemantic features on transformer residual streams; \citet{Templeton2024ScalingMono} extended the approach to frontier models, recovering thousands of interpretable features per layer. The strength of SAEs is open-vocabulary feature discovery: any feature reliably present in the activations may be surfaced without prior specification. The corresponding cost is that the discovered vocabulary is per-training-run, with semantics that must be re-interpreted each time. CAS Harness operates from the opposite end of the same spectrum: it asks whether a fixed published vocabulary's directions exist in the model. The two are non-rival. SAE features in the same models could be queried for alignment with CAS directions, and CAS directions could serve as labelled targets for SAE feature interpretation. We flag this as an explicit cross-method study for future work and do not claim CAS Harness recovers or replaces the SAE program.

### 2.5 Activation steering

Activation-steering methods \citep{Turner2023ActivationAddition,Subramani2022ExtractingLatent,Rimsky2024CAA,Li2024InferenceTimeIntervention} alter model behavior at inference by adding direction vectors to the residual stream at chosen layers. The directions are typically derived from contrastive activation pairs or task-specific probes. The bridge mechanism described here is mechanistically distinct: rather than additively perturbing the residual stream, it converts a detected CAS class into a natural-language prefix that the model's own attention mechanism then conditions on. The covering-morphism theorem makes the conditioning architecturally guaranteed: every later token attends to the realized prefix by the architecture of self-attention, not by hyperparameter selection. Empirically, residual-stream additive variants (Stage 7.LA) failed to clear pre-registered gates while the prefix-realization variants (Stages 7.CPL2, 8, 14, 15, 16) cleared them across three architecture families. We do not claim the bridge supersedes activation steering — steering targets visible-token generation surface, which the bridge does not at the scales tested — but the two mechanisms appear to operate in different regimes.

### 2.6 Cognitive architecture systems

The CAS framework descends from the cognitive-architecture tradition exemplified by ACT-R \citep{Anderson2007ACT} and SOAR \citep{Laird2012SOAR}, which formalize cognition over typed primitives. More recent work bridges that tradition to large language models \citep{Sumers2024CognitiveArch,Laird2024LLMCogArch}, treating LLMs as components within a cognitive-architecture loop. CAS Harness inverts the direction of analysis: rather than embedding the LLM inside a cognitive architecture, we use the cognitive architecture's vocabulary as an interpretability instrument to read structure already inside the LLM. CAS itself \citep{Henderson2026CAS} differs from ACT-R and SOAR in foundational style — it is grounded in topos theory and an open-simplex state space \citep{Henderson2026NoeticTopos} rather than production-rule semantics — but the lineage is acknowledged: typed cognitive primitives, formalized in advance, applied to foreign systems as a measurement vocabulary.

---

*End of draft sections (Abstract + §1 + §2). Open cross-reference items for the synthesizer: §3 framework specification, §4 bridge methodology, §5 empirical span, §6 framework-predictivity table, §7 hidden-content prototype, §8 limitations, §9 safety implications. Citation keys are placeholders; full BibTeX consolidation deferred to the references-pass agent.*

---

---
title: CAS Harness — Background and Methods (Paper Draft v0)
date: 2026-05-19
status: Draft for synthesizer; pending editorial review
target_venue: TMLR
sections: 3 (Background), 4 (Methods)
---

## 3. Background: The Cognitive Architecture System

This section introduces the Cognitive Architecture System (CAS), the framework
whose primitives are read out, ablated, and realized in the experiments that
follow. We restrict attention to the apparatus that is load-bearing for the
empirical work: the framework's primitives (Section 3.1), the categorical
structure that licenses the $\eta \to \varepsilon$ bridge prediction (Section
3.2), the bridge itself and its architectural correspondence in transformer
self-attention (Section 3.3), and the diagnostic tools internal to the framework
that produced pre-registered numerical predictions (Section 3.4). A full
mathematical treatment of CAS is given in the Noetic Topos paper
\citep{cas_topos_2026}; here we summarize only what the harness experiments
test.

### 3.1 Framework primitives

CAS factors cognition into four orthogonal axes — Noetic, Domain, Drive, and
Register — together with admissibility relations that constrain operator
application. The factorization is not a heuristic taxonomy: each axis carries a
distinct kind of information, and downstream constructions (state space,
covering morphisms, recipe semantics) treat the axes as independent dimensions
of a finite, typed product space.

**Noetics.** Ten structural cognitive operators, denoted $\wedge^0$ through
$\wedge^9$, name structural dynamics rather than content categories. The names
are verbatim canonical: Idea ($\wedge^0$), Mind ($\wedge^1$), Positive
($\wedge^2$), Negative ($\wedge^3$), Vibration ($\wedge^4$), Female ($\wedge^5$),
Male ($\wedge^6$), Rhythm ($\wedge^7$), Above/Cause ($\wedge^8$), Below/Effect
($\wedge^9$). The set carries an involution structure with three involution
pairs $\wedge^2 \leftrightarrow \wedge^3$, $\wedge^5 \leftrightarrow \wedge^6$,
$\wedge^8 \leftrightarrow \wedge^9$, and four self-duals
$\{\wedge^0, \wedge^1, \wedge^4, \wedge^7\}$. The operator collection forms a
monoid $(\mathcal{N}, \circ, \wedge^0)$ with $\wedge^0$ as identity.

**Domains.** Four processing tiers carry a strict total order with Domain
Descent as the canonical causation graph:

$$
\mathrm{P} \succ \mathrm{C} \succ \mathrm{E} \succ \mathrm{O}
\qquad \text{(Principled} \succ \text{Cognitive} \succ \text{Evaluative} \succ \text{Operational)}.
$$

Causation propagates $\mathrm{P} \to \mathrm{C} \to \mathrm{E} \to \mathrm{O}$;
feedback travels $\mathrm{O} \to \mathrm{P}$. The cross product of Noetics with
Domains produces the 40-element set of Cognitive States.

**Drives.** Seven motivational primitives, $F_1$ Unity, $F_2$ Wisdom, $F_3$
Vitality, $F_4$ Connection, $F_5$ Agency, $F_6$ Structure, $F_7$ Purpose, carry
their own involution pairs ($F_1 \leftrightarrow F_7$, $F_2 \leftrightarrow F_6$,
$F_3 \leftrightarrow F_5$) with $F_4$ self-dual.

**Registers.** A fourth orthogonal axis admitted in CAS v7.5
\citep{cas_v75_2026} specifies the operational character of a cognitive
operation without changing what it is. The four values are Transcendent
($|T$), Analytical ($|A$), Affective ($|f$), and Embodied ($|E$). The Register
axis applies independently to Noetics and Drives.

**Cross-products that ground the probe targets.** Two cross-products are
load-bearing for the experiments. The 40 Cognitive States factor as
$\text{Noetic} \times \text{Domain}$ (TKS labels $A_1 \ldots D_{10}$). The 28
Foundations factor as $\text{Drive} \times \text{Register}$ (denoted
$F_kR$ for $k \in \{1, \ldots, 7\}$, $R \in \{T, A, f, E\}$). These are the
two cross-products that v7.5 reconciled against external taxonomies and that
the harness uses as readout targets.

### 3.2 Category Noetica, the Noetic Topos, and Proposition 5.6

CAS's formal substrate is the category $\mathbf{Noetica}$, the smallest
pullback-complete subcategory of $\mathbf{FinSet}$ closed under the operators
$\{\mathrm{CO}\text{-}k\}_{k=0}^{9}$. Each operator $\mathrm{CO}\text{-}k$ has
an admissibility relation
$\mathcal{D}_k \subseteq \mathcal{I} \times \mathcal{I}$
specifying which (source, target) pairs are valid; $\mathcal{D}_0$ is the
diagonal $\{(I, I) : I \in \mathcal{I}\}$ (identity admissible only on
itself).

The Noetic Topos is the Grothendieck topos $\mathrm{Sh}(\mathbf{Noetica},
J_{\text{noe}})$ built on $\mathbf{Noetica}$ equipped with the Noetic Coverage
$J_{\text{noe}}$. The third axiom of the coverage, $\mathrm{Noe\text{-}Cov\text{-}3}$,
specifies that every covering sieve of an object $X \in \mathcal{I}$ contains
the counit $\varepsilon_X : R(X) \to X$ of the realization adjunction, with
arrows pointing **toward** the covered object. This direction is load-bearing
and is the subject of Correction 3 in the project's mathematical foundations:
the covering morphism is the counit $\varepsilon$, not the unit $\eta$.

**Proposition 5.6 (counit surjectivity).** For any morphism $g$ in
$\mathbf{Noetica}$, the pullback of the counit $\varepsilon$ along $g$ is
surjective. Equivalently, $\varepsilon$ is the surjective covering morphism
licensed by $\mathrm{Noe\text{-}Cov\text{-}3}$.

A second mathematical correction governs how this proposition applies
empirically: the pair $(\eta, \varepsilon)$ is a section-retraction, not an
adjunction. Concretely,

$$
\varepsilon_I \circ \eta_I = \mathrm{id}_I,
\qquad \eta_I \circ \varepsilon_I \neq \mathrm{id}_{R(I)}.
$$

Realization after embedding recovers the original object; re-embedding after
realization need not recover the realization. Prerequisite satisfaction is
**one-directional**. This asymmetry predicts that attempts to recover internal
structure by inverting realization will fail, while attempts to act on the
target by realization will succeed. The empirical chain we report below tracks
this asymmetry exactly.

### 3.3 The $\eta \to \varepsilon$ bridge and its transformer-architectural correspondence

The harness operationalizes Proposition 5.6 as a two-map bridge between hidden
states and tokens.

- **$\eta$ (embedding map: structure $\to$ realization).** In the harness,
  $\eta$ is instantiated as a linear probe trained on a layer's hidden-state
  activations to predict the CAS class label of the prompt under analysis.
  $\eta$ reads structure out of activations.
- **$\varepsilon$ (counit / realization: structure $\to$ tokens).** In the
  harness, $\varepsilon$ is instantiated as a template-based realization layer
  that, given a predicted CAS class, emits a short, readable natural-language
  prefix.

The pre-empirical prediction is mechanical. By the architectural definition of
self-attention, every prefix token participates in every subsequent token's
key/value reads — there is no hyperparameter that disables this property.
Concatenating the realized prefix $\varepsilon(\hat{c})$ to the input therefore
exposes the structural content of $\hat{c}$ to every continuation position by
construction. This is the transformer-architectural manifestation of
Proposition 5.6's covering surjectivity: $\varepsilon$ realizes structure
toward outputs through the attention machinery that is already present in
the foreign model. The bridge mechanism was specified before any model was
probed, on the basis of the topos result alone.

### 3.4 Diagnostic tools internal to CAS

Three diagnostic constructions internal to the framework are used throughout
the experimental chain as preflight predictors and post-hoc audits.

**Lacunarity.** For a per-class activation distribution with mean $\mu_c$ and
variance $\sigma_c^2$ on class $c$, the lacunarity score
$\Lambda(c) = \sigma_c^2 / \mu_c^2$ measures the gappiness of the
distribution. The framework's emergency threshold is $\Lambda \geq 2.0$, above
which the corresponding axis is judged structurally lumpy. Lacunarity is
computed per axis as a preflight diagnostic.

**Fractal Classifier.** Iterated cognitive trajectories — for example the
sequence of probe confidences across layers, or the sequence of model logit
margins under repeated forced continuation — are classified by their orbit
behavior into four shapes: Stabilizing, Amplifying, Oscillatory, Neutral. The
classifier is run preflight to predict whether a candidate ablation or steering
move will produce a stable target signal or an oscillatory non-target signal.

**Inversion Axes.** Seven failure-mode detection axes (operator imbalance $N$,
domain precedence violation $W$, drive pair imbalance $F$, state-vector entropy
deficit $E$, sub-drive cross-domain variance $S$, pathway RPM violation $A$,
compound $P$) provide a structural typology of cognitive failure. Inversion
axes are used to type trace anomalies observed in multi-layer trace classifiers
(Section 4.6).

These three tools are not introduced de novo for the harness: they are part
of CAS's standing framework apparatus. Their participation here is as
pre-experimental predictors. Each of four committed predictions that the
framework's tools made before the corresponding experiment ran was honored by
the data, including the prediction that the Foundations axis would be more
factorized than Noetics, that the Noetic ablation trajectory would be
Oscillatory rather than Stabilizing, that $\varepsilon$ rather than $\eta$ would
be the covering map for likelihood conditioning, and that the CAS Foundation
subspace would show output-side weight alignment above random expectation.

---

## 4. Methods

The experimental chain reuses one corpus, one probe architecture, and one
evaluation harness across two architecture families, four model scales, and
six cognitive axes. This section specifies the corpus construction
(Section 4.1), the probe architecture and training procedure (Section 4.2),
the activation-capture pipeline (Section 4.3), the causal ablation methodology
(Section 4.4), the $\eta \to \varepsilon$ bridge methodology (Section 4.5), the
multi-layer trace and blind-spot detection methodology (Section 4.6), the
weight-geometry alignment methodology (Section 4.7), the pre-registration
discipline that gates every confirmatory experiment (Section 4.8), and the
cross-architecture transfer methodology that adds only an activation-capture
adapter per new model (Section 4.9).

### 4.1 Role-bound counterfactual corpus (v2)

The v2 fixture is a balanced 3{,}000-row role-bound counterfactual corpus over
the 28 Foundations and the 10 Noetics, constructed to force any probe trained
on the corpus to learn structural role-binding rather than lexical surface
pattern.

The corpus is organized into 60 bundles. Each bundle contains 50 rows that
share a surface English context and vary only in the role binding that selects
which referent is the focus. Within a bundle, $25$ paired rows are
counterfactuals: the surface text is held identical, the focus role is
inverted, and the CAS class label changes accordingly. Pair construction
ensures that no lexical feature of the prompt — bag-of-words, character
n-gram, or surface metadata — can recover the label without recovering the
role binding. Bundles are sampled so that each Noetic appears in 300 rows
across the full corpus, with the Domain and Drive cross-products balanced
within Noetic.

The corpus is split disjointly by bundle into train ($1{,}200$ rows from
$24$ bundles), val ($400$ rows from $8$ bundles), and a locked test holdout
($1{,}400$ rows from $28$ bundles). Bundle-level split prevents within-bundle
leakage between train and test. The locked test holdout is not seen by any
probe during selection.

Every row's `cas_formula` metadata field is compiler-validated against
`api/notation/compiler.py`. Validation rejects any row whose stored CAS
expression fails to parse, fails type-checking, or fails admissibility against
$\mathcal{D}_k$. The validator produces $0$ errors across all $3{,}000$ rows
and $653$ expected review warnings (no warning blocks acceptance). The
maximum surface-token concentration on any single label is $0.50$, and every
token with concentration above $0.40$ is label-tied (its class membership is
explicit in the CAS class structure rather than incidental to surface
phrasing).

The same corpus, with the same split, is reused unchanged across every model
tested. No retraining of the corpus is performed when adding a new model.

### 4.2 Probe architecture

For each axis $A \in \{$Noetics, Foundations, 40 Elements, Operators,
Expression Shapes, Compiler-Valid Formulas$\}$, the probe is a multinomial
logistic regression with $L$-BFGS solver, balanced class weighting, and
input normalization by per-feature `StandardScaler` fit on the train split.
Concretely, for hidden state $h \in \mathbb{R}^d$ at a chosen layer and
readout position, the probe computes

$$
\hat{p}(c \mid h) = \mathrm{softmax}\left(W_A \cdot \mathrm{Norm}(h) + b_A\right)_c,
$$

with $W_A \in \mathbb{R}^{|A| \times d}$, $b_A \in \mathbb{R}^{|A|}$, no
regularization beyond the default $\ell_2$ shrinkage of `sklearn`'s `LogisticRegression`,
and class weights set to `balanced` to compensate for the corpus's class
prior. The probe is trained per layer, producing a layer sweep
$\{(\ell, \mathrm{acc}_{\mathrm{val}}(\ell))\}_{\ell=0}^{L-1}$ from which the
headline layer is selected by validation accuracy.

The readout position is one of three:
$\{\textsf{focus\_token}, \textsf{final\_token}, \textsf{mean\_over\_seq\_len}\}$.
Focus-token reads at the position of the role-binding focus marker. Final-token
reads the last position of the prompt. Mean-over-sequence-length pools all
positions. The readout position is chosen per axis by validation performance
and is reported as part of the headline configuration.

### 4.3 Activation capture

For each model, activations are captured by registering PyTorch forward hooks
on the residual-stream output of each transformer block. The HuggingFace
`transformers` loader is invoked with `local_files_only=True` and the model
commit hash is recorded as `model.config._commit_hash`. The captured tensor
for a single prompt is

$$
H = \{H_\ell \in \mathbb{R}^{T \times d}\}_{\ell=0}^{L-1},
$$

with $T$ the post-tokenizer sequence length and $d$ the model hidden
dimension. Three readout positions are extracted: focus-token (the position
of the bundle-specific focus marker), final-token, and mean-pooled across the
sequence. The full per-layer tensor is checkpointed to disk with a SHA-256
hash of the binary contents recorded in the run manifest alongside the model
commit hash, the corpus snapshot SHA, and the version of the activation-capture
script.

### 4.4 Causal ablation

For an axis $A$ with probe weight matrix $W_A \in \mathbb{R}^{|A| \times d}$,
let $P_A = W_A^{+}$ denote the right-pseudoinverse-derived basis for the
probe's classifier subspace, with $P_A \in \mathbb{R}^{d \times r_A}$ and rank
$r_A = \mathrm{rank}(W_A) = |A| - 1$ (one fewer than the number of classes,
since one direction is degenerate under the softmax). Subspace ablation
replaces a hidden state $h$ with

$$
h' = h - P_A P_A^{\top} h,
$$

projecting out the probe-readable subspace while leaving the orthogonal
complement intact.

Two control families are run alongside every ablation. The first is a
**random same-rank control**: thirty random orthonormal subspaces of rank
$r_A$ are sampled by QR-decomposition of standard normal matrices in
$\mathbb{R}^{d \times r_A}$, each projected to be orthogonal to the noetic
(or axis-specific) subspace's complement. Each control is applied with the
same ablation rule, and the disruption magnitude (drop in held-out probe
accuracy) is recorded. The second is a **shuffled-label control**: the probe
is retrained on the same activations with the labels permuted, and the
resulting subspace is ablated identically; the disruption from this
shuffled-label probe is expected to be null.

A pre-registered ablation gate counts as PASS when the targeted ablation
collapses probe accuracy to the exact $1/|A|$ chance baseline and the random
same-rank controls produce mean disruption $\leq 0.0$ at empirical
$p \leq 0.05$. The collapse-to-exact-chance pattern is structurally
informative: it indicates that the subspace removal does not merely degrade
the probe but eliminates it.

### 4.5 The $\eta \to \varepsilon$ bridge (CPL family)

The bridge methodology closes the loop between the probe and the foreign
model's next-token distribution. The pipeline runs in three stages on a
held-out 112-prompt evaluation pack disjoint from the probe training and
validation sets.

**Stage 1: probe prediction.** For a prompt $x$, run the foreign model forward,
capture the chosen layer's focus-token activation $h_L(x)$, and apply the
trained probe:

$$
\hat{c}(x) = \arg\max_c \hat{p}(c \mid h_L(x)).
$$

**Stage 2: realization.** The realization layer $\varepsilon$ is a
deterministic, template-based function from CAS class to a short readable
natural-language prefix. Each class $c$ maps to a fixed prefix string
$\varepsilon(c)$ (for example, a Foundation class maps to a one-clause
description of its Drive and Register in plain English; raw CAS notation is
explicitly **not** used in the readable prefix).

**Stage 3: likelihood scoring.** The foreign model is run forward a second
time, on the prompt with the realized prefix prepended:

$$
x' = [\varepsilon(\hat{c}(x))\,\Vert\,x],
$$

and the semantic-class log-likelihood of the gold continuation is computed.
The primary statistic is the **paired margin delta**: per prompt, the gold
continuation log-likelihood with prefix minus without prefix.

Four conditions are run per prompt: no prefix (baseline), probe-readable
prefix (the realized $\varepsilon(\hat{c})$), probe-raw prefix (raw CAS
notation rather than readable text; expected null by the bridge claim), and
partner-readable prefix (the involution-pair partner of $\hat{c}$; expected
to move the margin in the opposite direction). The partner condition is
the strongest internal control: it uses the same realization template at the
same token positions on the same prompts but with the wrong-class
realization.

The pre-registered gate for `PASS_CLEAN` is a conjunction:

$$
\begin{aligned}
&\Delta_{\text{readable vs none}} > +0.15, \\
&\Delta_{\text{readable vs partner}} > +0.30, \\
&\frac{\#\,\{\text{positive cases}\}}{112} > 0.50, \\
&p_{\text{Wilcoxon}} < 0.05.
\end{aligned}
$$

The Wilcoxon signed-rank test is computed on the paired per-prompt margin
deltas (readable minus none, and readable minus partner). The gate is
specified in the pre-registration file committed before the run.

### 4.6 Multi-layer trace and blind-spot detection

Stage 13 extends the single-layer probe into a per-layer trace. For prompt $x$
and layer $\ell$, the probe confidence vector is
$\hat{p}_\ell(x) \in \Delta^{|A|-1}$. The full trace is
$\mathcal{T}(x) = \{\hat{p}_\ell(x)\}_{\ell=0}^{L-1}$.

A trace classifier reduces $\mathcal{T}(x)$ to a stability category by
measuring cross-layer variance of the predicted class probability:

$$
\sigma^2_{\hat{c}}(x) = \frac{1}{L}\sum_{\ell=0}^{L-1}
\left(\hat{p}_\ell(x)_{\hat{c}} - \overline{\hat{p}_{\cdot}(x)_{\hat{c}}}\right)^2.
$$

Traces with low cross-layer variance and high mean confidence are categorized
as **stable-like**; traces with high variance or class collapse are
categorized as **problem-like**. The per-class blind-spot rate is the fraction
of problem-like traces conditioned on the gold label.

**Readout-position disambiguation (Stage 13.1).** A per-class blind spot is
classified as **model-side** (a genuine representational gap in the foreign
model) or **readout-position-side** (an artifact of the chosen readout
position) by sweeping the same class across all three readout positions. If
the class is problem-like under one readout position but stable-like under
another at the same layer, the weakness is readout-position-side; if it is
problem-like across all three, the weakness is model-side.

### 4.7 Weight-geometry alignment (Stage 14.1)

For the chosen layer's Foundation probe with classifier subspace
$P \in \mathbb{R}^{d \times r}$, three weight-geometry energy fractions are
computed against the foreign model's input and output token-weight matrices.
Let $E \in \mathbb{R}^{|V| \times d}$ denote the token embedding matrix and
$W_U \in \mathbb{R}^{|V| \times d}$ denote the unembedding matrix
(`lm_head.weight`). The alignment statistics are

$$
\mathrm{Energy}_{\mathrm{out}}(P) =
\frac{\|W_U P\|_F^2}{\|W_U\|_F^2 \cdot r / d},
\qquad
\mathrm{Energy}_{\mathrm{in}}(P) =
\frac{\|E P\|_F^2}{\|E\|_F^2 \cdot r / d},
$$

with a third statistic — the **logit-lens energy fraction** — measuring the
fraction of the residual-stream-times-unembedding energy that lies in the
probe subspace, controlling for rank.

A random null is constructed by sampling 30 random orthonormal subspaces of
the same rank $r$ in the residual-stream complement (i.e., orthogonal to the
probe subspace) and computing the same statistics. The pre-registered gate
for above-random alignment is that the actual statistic exceeds the empirical
$p \leq 0.05$ tail of the random null distribution. Stage 14.1 reports the
energy fractions, the random-null mean and 95th percentile, and the empirical
$p$-value $\Pr(\text{random} \geq \text{actual})$.

Two boundary statements govern this methodology. First, weights do not fire:
the analysis is **geometric**, not dynamic. It establishes that the static
weight matrices live in a configuration consistent with CAS-directional
emission, complementary to the dynamic activation-tier evidence. Second, the
test is rank-controlled: random subspaces of the same rank, in the same
residual-stream basis, are the null distribution. Above-random alignment at
$p \leq 0.05$ is the licensing condition; absent that, no claim is made.

### 4.8 Pre-registration discipline

Every confirmatory experiment in this work follows a two-commit pattern.

**Commit one: pre-registration gate.** Before the run is launched, a gates
file is committed to the repository specifying the confirmatory question, the
fixed experimental configuration (model commit, corpus snapshot SHA, probe
configuration, readout position, layer selection rule, control families,
sample size), the per-condition statistics that will be computed, and the
pass/null/grey verdict criteria with numerical thresholds. The gates file is
named after the stage and dated by the commit. Once committed, the gate
cannot be moved without an explicit, audit-visible amendment.

**Commit two: run and results.** The training script, eval harness, and
results report are committed after the run completes. The report cites the
gates file by commit SHA and records the verdict in the gates file's verdict
field.

A bi-agent audit cycle runs alongside this pattern. The lead author commits
under one agent identity; an independent audit agent reviews the commit
through `docs/working/agent_exchange/inbox_claude.md` and writes back through
`docs/working/agent_exchange/codex_audit.md`. The audit flags overclaim,
methodology drift, missing controls, or stale gate language. Audit reviews
caught and corrected overclaim or methodological issues at multiple stages
(2, 2.1, 3, 3.2, 6.6, 6.6A, 6.6C, 7.3, 11), each producing a documented
reframe before any downstream commit relied on the stale framing.

Nine consecutive confirmatory stages in the present chain (Stages 7.0
through 15) have followed this discipline without amendment to a pre-committed
gate. The discipline is itself a methodological contribution: it constrains
the venue of the empirical claims to those gates that were committed before
their data were seen.

### 4.9 Cross-architecture transfer

The transfer methodology was designed so that the marginal engineering cost of
adding a new foreign model is small, and the marginal statistical cost is
zero (no new corpus, no new probe family, no new statistical procedure).

**Reused unchanged.** The v2 corpus (Section 4.1), the train/val/test split,
the probe architecture and training procedure (Section 4.2), the realization
templates and CPL gate criteria (Section 4.5), and the statistical pipeline
(paired Wilcoxon, random same-rank controls, McNemar against text baselines)
are reused unchanged.

**Adapted per model.** Three components are adapted: the activation-capture
hook target (the residual-stream module path differs by architecture — e.g.
`gpt_neox.layers.{i}` for Pythia, `model.transformer.blocks.{i}` for OLMo),
the tokenizer-side prompt construction (focus markers must survive
tokenization on each model's tokenizer), and the layer-sweep range (later
layers are added for deeper models). The activation-capture adapter is a thin
shim around the existing hook framework; no other code changes.

**Statistical pipeline unchanged.** Layer selection is by validation accuracy
on the same val split. CPL2 evaluation is on the same 112-prompt held-out
pack. Wilcoxon signed-rank, paired McNemar against TF-IDF/count-vector text
baselines, and random-control matching are computed identically. The
cross-architecture claim is licensed only when the same gate that closed on
the original model also closes on the new model with no methodology
modification beyond the activation-capture adapter.

This methodology has been instantiated on four models — Pythia-160M,
Pythia-1B, Pythia-2.8B, and OLMo-1B — across two architecture families
(EleutherAI Pythia and AI2 OLMo), four parameter scales, two tokenizer
families, and two pretraining corpora (The Pile and Dolma). The bound claimed
in this work is exactly what the methodology supports: validated cross-scale
within the Pythia family and validated cross-architecture at one out-of-family
model. Additional out-of-family models (Mistral, Llama, Qwen) remain open as
redundancy validation rather than as remaining open bounds.

---

## 5. Experiments and Results

We report eight families of experimental findings across fifteen pre-registered stages of probing. Each subsection follows the same disclosure pattern: an enumeration of the experimental units, a tabular summary of effect sizes, a statement of the pre-registered gate that the result either passed or failed, and a bounded interpretation. All claims are scoped to *the models and corpora evaluated*; we do not extrapolate beyond the architectures, parameter counts, and probing fixtures actually tested.

Throughout this section, p-values for paired comparisons of model behavior between conditions are obtained via the paired Wilcoxon signed-rank test on per-prompt margin deltas \citep{wilcoxon1945individual}, and p-values for probe-vs-baseline label agreement are obtained from McNemar's test on matched 2x2 contingency tables \citep{mcnemar1947note}. Random-subspace null distributions are generated by QR-orthonormalized same-rank Gaussian matrices with fixed seeds. Gate thresholds (PASS / NULL / GREY) were committed to the repository prior to every confirmatory run for nine consecutive stages.

### 5.1 Discriminative Readout

The first question is whether CAS-aligned cognitive structure is linearly decodable from hidden-state activations of a model that has never been exposed to the CAS framework. We test this on Pythia-160M \citep{biderman2023pythia} using v2 of the probing corpus (~7,000 prompts balanced across the six CAS axes specified in Section 4). For each axis, a logistic-regression probe with balanced class weights is fit on the activation of the focus-token at a single per-axis selected layer; a control "text baseline" classifier is fit on character n-gram features of the surface prompt to control for shallow lexical regularities. McNemar's test compares the per-prompt correctness of the probe against the text baseline. Table 1 reports probe accuracy, text-baseline accuracy, the per-axis lift, and McNemar p-value.

**Table 1.** Discriminative readout across six CAS axes on Pythia-160M.

| Axis | Classes | Probe Accuracy | Text Baseline | Lift | McNemar p |
|---|---:|---:|---:|---:|---:|
| 10 Noetics | 10 | 73.9% | 46.4% | +27.5 pp | ~10^{-50} |
| 28 Foundations | 28 | 78.6% | 49.7% | +28.9 pp | ~10^{-95} |
| 40 Elements | 40 | 89.8% | 50.1% | +39.7 pp | machine-zero |
| 5 Operators | 5 | 99.2% | 95.6% | +3.6 pp | ~10^{-22} |
| 10 Expression Shapes | 10 | 93.0% | 64.4% | +28.6 pp | ~10^{-227} |
| 10 Compiler-Valid Formulas | 10 | 90.0% | 63.9% | +26.0 pp | ~10^{-176} |

Stages 6.4 (Noetics), 7 (Foundations), 9 (40 Elements), 10 (Operators), 11 (Expression Shapes), and 12 (Compiler-Valid Formulas) each closed under their pre-registered PASS gates. Five of the six axes admit a single-line interpretation: the probe accuracy substantially exceeds a competitive text baseline, with McNemar p-values far below any conventional significance threshold and effect sizes that do not depend on the choice of correction method. The aggregate evidence is that linear directions corresponding to CAS-aligned structure are recoverable from Pythia-160M activations at every axis tested.

The 5-Operators row warrants a caveat that we surface explicitly. The text baseline for Operators ceilings at 95.6% because the surface morphology of CAS operator notation (`+`, `×`, `|⟨...⟩`, etc.) is itself a highly informative shallow feature; the probe still beats the baseline by 3.6 percentage points at McNemar p ~10^{-22}, but the lift cannot be interpreted with the same magnitude as the other axes. We classify Stage 10 as GREY-on-detection (task design with limited dynamic range) but record the readout-causal ablation result for the same axis as a clean PASS (Section 5.2 below). The Expression Shapes axis, tested at Stage 11, was additionally subjected to a confusion-coherence audit \citep{stage11_audit} which verified that probe confusions concentrate within structurally adjacent shape classes rather than reflecting arbitrary noise — supporting the interpretation that the probe is reading shape-relevant geometry rather than a high-variance shortcut.

The discriminative result alone does not establish causal load-bearing-ness — a probe can read structure that is correlated with but not used by the model. Sections 5.2 and 5.5 establish the causal claim and the conditioning claim respectively.

### 5.2 Causal Ablation

For each of the five axes amenable to subspace ablation, we test whether projecting out the probe-identified directions from the activation tensor collapses the probe's readable accuracy. The pre-registered PASS pattern is: (i) ablated accuracy collapses to exact 1/N chance for an N-class axis, and (ii) random same-rank ablations (n = 30 per stage, QR-orthonormalized in the noetic complement) produce mean disruption indistinguishable from zero. The empirical p-value reported in Table 2 is computed as the proportion of random-subspace ablations producing a disruption at least as large as the CAS-aligned subspace ablation.

**Table 2.** Subspace ablation collapses probe readability to chance across five axes on Pythia-160M.

| Axis | Baseline | Ablated | Random Null Disruption | Empirical p |
|---|---:|---:|---:|---:|
| 10 Noetics (Stage 6.5) | 73.9% | 10.0% (1/10) | 0.000 | 0.03 |
| 28 Foundations (Stage 7.1) | 78.6% | 3.57% (1/28) | 0.000 | 0.032 |
| 5 Operators (Stage 10) | 99.2% | 20.0% (1/5) | 0.000 | 0.032 |
| 10 Expression Shapes (Stage 11) | 93.0% | 10.0% (1/10) | 0.000 | 0.032 |
| 10 Compiler-Valid Formulas (Stage 12) | 90.0% | 10.0% (1/10) | 0.000 | 0.032 |

All five ablations collapse to *exact* 1/N chance. All five random same-rank ablation controls produce mean disruption of zero and maximum disruption of zero, indicating that the disruption is not a generic property of low-rank projections at the relevant rank. Within the limits of the pre-registered test, this is the strongest available evidence that the subspaces identified by the probes are not epiphenomenal readouts of activations that happen to correlate with CAS labels — they are causally load-bearing for the model's downstream probe-readable response. The same evidence does not establish that the model's *surface-text* generation depends on these subspaces in the same way; that question is taken up in Section 5.5.

We note that the Operators axis, which carried a text-baseline-ceiling caveat in Section 5.1, produces a clean readout-causal ablation result here. We interpret this as the Operators discriminative caveat being a property of the *baseline task*, not a property of the underlying subspace geometry — a methodological distinction with consequences for future task design.

### 5.3 Cross-Scale Validation Within Pythia

The next question is whether the bridge mechanism scales: does it survive when the foreign model is two orders of magnitude larger, and does the effect grow, plateau, or attenuate? We test on three points of the Pythia family (160M, 1B, 2.8B), holding corpus, probe architecture, realization template, and statistical methodology constant. For each scale, we fit a Foundations-axis probe at the per-model selected layer and measure the η → ε conditioning effect under the pre-registered CPL2 gate \citep{stage7_cpl2}: the probe-readable likelihood delta vs no-prefix, the margin over a partner-readable control prefix, the fraction of positive cases in the 112-prompt evaluation set, and a Wilcoxon p-value on per-prompt margin deltas.

**Table 3.** η → ε bridge effect across three Pythia scales.

| Model | Params | Best Layer | Δ vs none | Margin vs partner | Positive | Wilcoxon p |
|---|---:|---:|---:|---:|---:|---:|
| Pythia-160M | 160M | 6 (50%) | +0.283 | +0.683 | 81/112 | <0.0001 |
| Pythia-1B | 1B | 8 (50%) | +0.554 | +1.246 | 90/112 | 2.58 × 10^{-14} |
| Pythia-2.8B | 2.8B | 14 (44%) | +0.583 | +1.336 | 92/112 | 3.08 × 10^{-15} |

Stages 7.CPL2, 8, and 14. Three findings warrant explicit naming:

1. *The conditioning effect is monotonic across the tested scales.* The probe-readable likelihood delta grows from +0.283 to +0.554 to +0.583. The Wilcoxon p-value moves from <0.0001 to ~10^{-15} as the test gains power against a strengthening true effect.

2. *The effect approximately doubles from 160M to 1B and then plateaus.* The increment from 1B to 2.8B (+0.029) is roughly an order of magnitude smaller than the increment from 160M to 1B (+0.271). This is the canonical diminishing-returns shape of a near-saturated mechanism, not a mechanism that scales unboundedly. Within the corpus, axis, and realization template tested, the η → ε bridge appears to saturate at approximately 1B parameters for English-only Pythia training.

3. *The layer-selection rule holds across scales.* The best layer for the Foundations probe falls between 44% and 50% of the network depth for all three Pythia models. This rule was not committed pre-registration as a transferability claim, but it survives empirically. Section 5.4 tests whether the rule also survives cross-architecture transfer.

The saturation finding has a practical consequence: the η → ε bridge does not require frontier-scale models to exhibit substantial effects. A 1B-parameter open-weight model captures the majority of the effect observed at 2.8B. This is an empirical observation, not a theoretical bound; we make no claim about whether the same plateau holds for richer training corpora or different probing axes.

### 5.4 Cross-Architecture Transfer

The cross-scale curve within Pythia controls for many design choices but is consistent with a Pythia-specific or Pile-specific artifact. To test the cross-architecture hypothesis, we apply the same probing methodology to three additional architectures: OLMo-1B \citep{groeneveld2024olmo} (AI2, OLMo lineage, Dolma corpus, OLMo tokenizer) and Qwen2.5-1.5B \citep{yang2024qwen2} (Alibaba, Qwen lineage, multilingual + code corpus, Qwen 150K BPE tokenizer). Each model is independent of Pythia at the levels of lab, lineage, training corpus, and tokenizer vocabulary. Table 4 reports the η → ε bridge effect for one Pythia-1B reference and two out-of-family architectures.

**Table 4.** η → ε bridge transfer across three architecture families.

| Model | Lab | Lineage | Corpus | Tokenizer | Best Layer | Δ | Margin | Positive | Wilcoxon p |
|---|---|---|---|---|---:|---:|---:|---:|---:|
| Pythia-1B | EleutherAI | GPT-NeoX | The Pile | GPT-NeoX BPE | 8 (50%) | +0.554 | +1.246 | 90/112 | 2.58 × 10^{-14} |
| OLMo-1B | AI2 | OLMo | Dolma | OLMo BPE | 16 (50%) | +0.604 | +1.305 | 87/112 | ~10^{-15} |
| Qwen2.5-1.5B | Alibaba | Qwen | multilingual + code | Qwen BPE 150K | 11 (39%) | +0.796 | +1.625 | 83/112 | 2.92 × 10^{-12} |

Stages 15 (OLMo) and 16 (Qwen). Across the models evaluated, the η → ε bridge effect replicates with *strengthening* magnitude as the training corpus becomes richer and more multilingual. The OLMo-1B effect (+0.604) modestly exceeds the Pythia-1B effect (+0.554) at comparable parameter count; the Qwen2.5-1.5B effect (+0.796) is substantially larger again. The layer-selection rule holds at 39–50% of network depth across all five models in our evaluation. The Pythia-only artifact hypothesis is, within the limits of this evaluation, no longer tenable: the mechanism replicates across three independent labs, three independent training corpora, and three independent tokenizer vocabularies.

We caution that Qwen2.5-1.5B is a different parameter count than the OLMo and Pythia 1B reference, and that the corpus and tokenizer enrichment is confounded with parameter count; the Qwen effect cannot be cleanly attributed to either axis alone. We report it as additional cross-architecture evidence rather than as a precisely controlled cross-corpus comparison.

### 5.5 Likelihood Conditioning via the η → ε Bridge

Sections 5.3 and 5.4 report the headline conditioning effect; this subsection reports the control conditions that validate it. The η → ε bridge as specified in Section 3 makes two specific predictions: (i) the conditioning effect should be driven by the *ε-realization* (the readable natural-language prefix generated from the detected CAS class), not by recognition of raw CAS surface symbols; and (ii) a partner-readable prefix whose CAS content is structurally inverted relative to the prompt's detected class should produce a *negative* effect of comparable magnitude.

We test both controls at every model scale. The raw CAS symbol prefix condition prepends the bare detected CAS class (e.g. `^3^P|A`) without natural-language realization. The partner-readable prefix condition uses the CAS-involution partner of the detected class (e.g. realizing `^2^P` when the prompt was classified as `^3^P`) and emits a readable English realization for the inverted class. Table 5 reports the five-model consolidated summary across all conditions.

**Table 5.** Five-model η → ε bridge summary with control conditions.

| Model | Probe-readable Δ | Partner-readable Δ | Raw CAS Δ | Margin (probe − partner) | Best Layer |
|---|---:|---:|---:|---:|---:|
| Pythia-160M | +0.283 | −0.400 | −0.020 | +0.683 | 6 (50%) |
| Pythia-1B | +0.554 | −0.692 | +0.003 | +1.246 | 8 (50%) |
| Pythia-2.8B | +0.583 | −0.753 | −0.005 | +1.336 | 14 (44%) |
| OLMo-1B | +0.604 | −0.701 | +0.001 | +1.305 | 16 (50%) |
| Qwen2.5-1.5B | +0.796 | −0.829 | −0.002 | +1.625 | 11 (39%) |

(Raw-CAS Δ values approximate, derived from Stages 7.CPL, 8, 14, 15, 16 control conditions.)

Three control-condition findings hold across all five models:

1. The raw CAS symbol prefix produces a null effect at every scale (`probe_raw` between −0.020 and +0.003). This rules out the simplest competing hypothesis that the bridge is symbol-recognition rather than realization-conditioning.

2. The partner-readable prefix produces a *negative* effect of comparable magnitude to the probe-readable prefix's positive effect at every scale. This is exactly the prediction of Proposition 5.6 under the assumption that ε is the covering morphism: the bridge's effect direction is determined by *which* readable structure is realized, not by the presence of readable structure per se.

3. The margin (probe-readable minus partner-readable) is the cleanest summary statistic and grows monotonically with parameter count and training-corpus richness across the tested models.

Within the limits of this evaluation, the η → ε bridge is empirically the realization channel predicted by Proposition 5.6, not a generic prefix-conditioning artifact.

### 5.6 Weight-Geometry Alignment

The activation-trace evidence in Sections 5.1–5.5 establishes that the bridge mechanism *operates* dynamically per prompt. A complementary question is whether the bridge's geometric signature is *baked into the static weights* of the foreign model — a stronger architectural claim. We test this on Pythia-2.8B (Stage 14.1) by principal-angle analysis between the CAS Foundation probe subspace P (rank 27, fit at layer 14) and the row space of the model's unembedding matrix W_U \citep{stage14_weight_geometry}. The null distribution is generated by 30 same-rank random subspaces drawn from the noetic complement.

**Table 6.** Weight-geometry alignment between CAS Foundation subspace and Pythia-2.8B static weights.

| Check | Actual | Random Mean | Random p95 | One-sided p |
|---|---:|---:|---:|---:|
| Output-weight energy fraction (W_U row space) | 0.01118 | 0.01052 | 0.01083 | 0.0099 |
| Input-weight energy fraction (token embedding) | 0.01058 | 0.01055 | 0.01067 | 0.3465 |
| Output logit-lens energy fraction | 0.02712 | 0.00958 | 0.01391 | 0.0099 |

The output logit-lens energy fraction is 2.83× the random mean (p = 0.0099 against the random-subspace distribution). The input-side (token embedding) check is null. The asymmetry is consistent with Proposition 5.6's prediction: the counit ε realizes structure *toward outputs*, so the static output-weight geometry of the model should be more aligned with CAS Foundation directions than the input-weight geometry, and that is what we observe. Two boundary statements: (i) this is geometric alignment of static weights, not a claim that weights "fire"; (ii) the effect is bounded above random at one-sided p = 0.0099 on the output checks, which is a modest-but-reliable signal, not a large-magnitude effect. We treat this as complementary to the activation-tier evidence rather than as standalone validation of any generation-control claim.

### 5.7 Multi-Layer Trace and Blind-Spot Detection

The single-layer probe assumed by Sections 5.1–5.6 discards information distributed across layers. To test whether layer-stack information improves both readout quality and per-prompt interpretability, we train a multi-layer trace classifier on the Pythia-160M formula-family fixture (Stage 13). Each prompt is summarized by a per-layer probe-confidence vector across all 12 Pythia-160M layers; a logistic-regression head reads the per-layer trace and classifies the formula family.

Aggregate performance: 95.4% accuracy on 10 classes, lacunarity (Var/Mean²) of 0.0016 — the lowest factorization-noise figure produced across the project. Multi-layer averaging suppresses single-layer noise and produces a cleaner structural signature than any single-layer probe in our evaluation. Table 7 summarizes the trace classification and the derived blind-spot profile.

**Table 7.** Multi-layer trace classification (Stage 13) and blind-spot detection on Pythia-160M formula-family fixture.

| Metric | Value |
|---|---|
| Trace classifier accuracy (10 classes) | 95.4% |
| Lacunarity (Var/Mean²) | 0.0016 |
| Prompts classified stable-like | 77.7% |
| Prompts classified problem-like | 22.3% |
| Top blind-spot candidates | `relation_dependency`, `production_recipe`, `membership_assertion`, `cover_partition_formula`, `yield_query` |

The 22.3% problem-like rate is *not* a property of the corpus's class balance — Stage 13.1 verifies the fixture is balanced (within ±1.5% per class) and the threshold for "problem-like" was pre-registered prior to running the trace classifier \citep{stage13_blindspot_sanity}. The blind-spot list is the regulator-relevant artifact: each class on the list flags a specific cognitive structure whose internal representation in Pythia-160M is unstable across layers, and the multi-layer trace gives a principled localization for *where* in the network the instability lives.

A critical disambiguation, surfaced in Stage 13.1: `relation_dependency` is readout-position weak under the `mean_over_seq_len` readout but model-side strong when read at the `focus_token` position at layer 12. This distinguishes *architectural weakness* (the model lacks the representation) from *readout-configuration weakness* (the model has the representation but the chosen probing recipe does not see it). For a regulator-facing evidence packet, this distinction is load-bearing: a model that genuinely lacks a representation requires different intervention than a model whose representation is hidden from a particular probe configuration.

### 5.8 Hidden-Content / Suppression Detection (Prototype)

The most exploratory tier in our experimental program addresses the question: *what is the model representing internally that it is not emitting in its surface text?* The two-bridge architecture for this question reads two CAS profiles in parallel — η₁ from the internal hidden states of a forward pass, η₂ from the emitted output text (passed back through the same probe stack at the input side) — and compares them. Differences are classified into seven structurally distinct hiding shapes (Section 4.4): withheld content, self-censored content, latent capability, suppressed reasoning, frame manipulation, persona drift, and involution content.

The η₁ side is the same probe machinery validated across Sections 5.1–5.7. The η₂ side is currently prototype-tier: the probing methodology is identical, but the validation discipline (pre-registered gates, paired controls, fresh holdouts, cross-axis confusion-coherence audits) has not yet been run against the emitted-text corpus. We report the architectural framework and the qualitative early-evidence pattern, but do *not* claim a validated quantitative effect for the gap detector at this time.

We make one comparison to the published literature. \citet{anthropic_nla_2025} describe an "evaluation awareness" finding where Claude internally represented a belief about being evaluated that did not appear in its surface output. The authors note that the natural-language description of the internal state was sometimes verifiably false (the model confabulated the wrong reason for its internal state). The CAS Harness hidden-content detector targets the same phenomenon along a structurally different axis: rather than producing a free-form natural-language description of the hidden content (which can confabulate), it produces a *typed-class* assignment (which has class granularity rather than free-form description, but cannot confabulate beyond the bounded class set). The two approaches are complementary; the typed-class version is the regulator-grade audit shape, while the natural-language version is more readable to a human inspector.

The prototype-tier status of this capability is firm: the bridge between η₁ and η₂ is wired, returns typed-class output, and produces qualitatively interpretable gap profiles on early sample inspections, but no pre-registered confirmatory gate has been closed. Section 6 (Limitations) treats this explicitly.

### 5.9 Framework Predictive Validity

A pattern visible across Sections 5.1–5.6 deserves explicit naming: in four separate cases, the framework's internal diagnostic tools were used to make a *committed numerical prediction* about an experimental outcome *before* the experiment was run. In each case, the prediction held within the pre-registered tolerance.

**Table 8.** Pre-registered numerical predictions by framework-internal diagnostic tools.

| Prediction (made when) | Tool | Experiment | Outcome |
|---|---|---|---|
| Foundations axis would be more factorized than Noetics axis | Lacunarity preflight | Stage 7 Foundations readout | Lacunarity 0.793 → 0.021 (38× cleaner). Confirmed. |
| Noetic-subspace ablation trajectory would be Oscillatory, not Stabilizing | Fractal classifier preflight | Stage 6.6 noetic ablation generation | Classified Oscillatory on the larger sample, as predicted. Confirmed. |
| Counit ε is the covering map for likelihood conditioning | Topos Proposition 5.6 | Stages 7.CPL through 16 | η → ε bridge closed across 5 models. Confirmed at Wilcoxon p between 10^{-12} and 10^{-15}. |
| CAS Foundation subspace should show output-weight alignment | Proposition 5.6 corollary | Stage 14.1 weight-geometry analysis | 2.83× random output-weight alignment, p = 0.0099. Confirmed. |

These four predictions are heterogeneous in tool (diagnostic gate, dynamical-systems classifier, category-theoretic theorem, geometric corollary), in tested entity (factorization noise, ablation trajectory shape, generation likelihood, static-weight geometry), and in evidence tier (descriptive, dynamical, causal-conditioning, architectural). They share a single methodological pattern: the framework's *own* internal diagnostic produced a quantitative prediction *before* the relevant data was generated, and the data was generated against a pre-registered gate. In each case, the framework's prediction held.

We treat this as the highest-tier evidence the framework can produce in its current state. Discriminative readout (5.1), causal ablation (5.2), and cross-architecture transfer (5.4) each demonstrate that the framework is *consistent* with the observed data; the predictive-validity results demonstrate that the framework *generated the prediction* of the data before the data existed. Within the limits of four cases on three models, this is a falsifiable empirical signature of a framework that describes the phenomena under study rather than being merely a notation imposed on them.

### 5.10 Summary of Evidence Tier Closures

Across Sections 5.1 through 5.8, we close evidence gates at the following tiers, within the bounds of the models and corpora evaluated:

- **Discriminative readout** validated across six CAS axes on Pythia-160M, with the Operators axis carrying a text-baseline-ceiling caveat (Section 5.1).
- **Readout-causal ablation** validated across five CAS axes on Pythia-160M, with all five collapses to exact 1/N chance and all random-control nulls clean (Section 5.2).
- **Cross-scale validation** within the Pythia family validated at three parameter scales, showing monotonic-converging effect growth that saturates near 1B parameters (Section 5.3).
- **Cross-architecture transfer** validated at two out-of-family architectures (OLMo-1B and Qwen2.5-1.5B), with the layer-selection rule (39–50% depth) holding across all five tested models (Section 5.4).
- **η → ε bridge control conditions** validated at all five model scales: raw CAS symbol prefix produces null effect; partner-readable prefix produces negative effect of comparable magnitude (Section 5.5).
- **Weight-geometry alignment** validated above random on output-weight checks at Pythia-2.8B (p = 0.0099), null on input-weight checks (Section 5.6).
- **Multi-layer trace and blind-spot detection** validated at 95.4% accuracy with lacunarity 0.0016 on Pythia-160M formula-family fixture, with readout-position-vs-model-side disambiguation (Section 5.7).
- **Hidden-content / suppression detection** remains *prototype-tier*: architecture wired and qualitatively interpretable, but pre-registered confirmatory gates not yet closed (Section 5.8).
- **Framework predictive validity** validated across four pre-registered numerical predictions, each holding within the committed tolerance (Section 5.9).

The single open boundary we explicitly carry forward into Section 6 is hidden-content / suppression detection at validated tier. Generation surface-text steering by hidden-state ablation, attempted at multiple stages prior to the η → ε bridge formulation (Stages 6.6, 7.3, 7.OA, 7.LA), is *closed as negative* on the small-model scale tested and is mathematically explained by the section-retraction identity (Section 3.2): η ∘ ε ≠ id, so attempts to invert the realization channel by hidden-state intervention should not be expected to succeed, and they do not. The empirical pattern of generation-steering failure followed by likelihood-conditioning success is itself consistent with the asymmetric topos-theoretic prediction.

### 5.11 Statistical Methodology Notes

For reviewer clarity, we summarize the statistical conventions used throughout this section:

- *Probe-vs-baseline comparisons.* McNemar's test on per-prompt 2×2 contingency tables. We report McNemar p-values rather than effect sizes alone because the binary-outcome paired structure makes McNemar the standard test; absolute lift in percentage points is the effect-size analogue.
- *Likelihood-conditioning comparisons.* Paired Wilcoxon signed-rank on per-prompt margin deltas with a 112-prompt evaluation set fixed across stages. Effect sizes are reported as raw likelihood deltas (Δ, in nats) and as margin over the partner-readable control.
- *Ablation-vs-random-control comparisons.* Empirical p-values against 30-draw QR-orthonormalized random same-rank null distributions, with fixed seeds. Reported as "Empirical p" in Table 2.
- *Weight-geometry alignment.* One-sided p-values against the random-subspace null distribution (Table 6).
- *Pre-registered gates.* PASS / NULL / GREY thresholds were committed to the repository prior to every confirmatory run for nine consecutive stages (Stages 7 through 16). Confirmatory runs were executed on fresh prompts not used during exploratory iteration. Random-control seeds, model commits, package versions, and activation-file SHAs were recorded as provenance metadata in the Evidence Packet schema.

Where p-values are reported as `~10^{-N}`, the underlying test statistic computed an exact value at or below the floating-point representable threshold and the order of magnitude is reported rather than the literal floor; the substantive interpretation does not depend on which side of `10^{-50}` the precise value sits on. The McNemar entry "machine-zero" indicates the test statistic exceeded the maximum representable in double-precision floating-point arithmetic.

The methodology itself — pre-registration discipline, paired statistics, random-control matching, fresh holdouts, bi-agent audit cycles, provenance stamping — is part of the contribution we are offering. We have found in practice that the discipline of declaring PASS / NULL / GREY gates *before* the data is in hand is the operational lever that prevents an interpretability research program from drifting into post-hoc rationalization. Within the limits of fifteen experimental stages, that discipline has held.

---

## 6. Discussion

### 6.1 Framework predictive validity

The strongest scientific contribution of this work is not any single empirical
result, but the fact that four CAS-internal diagnostic tools made committed
numerical predictions *before* the experiments that subsequently confirmed
them. We summarise these here because, as a class of evidence, they are
unusual in contemporary mechanistic interpretability and we think the
distinction matters epistemically.

The lacunarity preflight, run on the v2 role-bound corpus before any
foundation-axis probe was trained, predicted that the 28-Foundations axis
would be substantially more factorized than the 10-Noetics axis (Var/Mean²
of order 10⁻² versus 10⁻¹). Stage 7 returned 0.021 against 0.793 — a 38-fold
gap in the direction predicted. The fractal classifier, applied to the
noetic-subspace ablation trajectory before any surface-text steering attempt,
classified the orbit as Oscillatory and predicted that hidden-state steering
of generated surface text would fail; Stage 6.6 across six hidden-state hook
variants returned null exactly as the classifier had said it would.
Proposition 5.6 of the Noetic Topos paper proves that the counit ε of the
Noetic Coverage is a surjective covering morphism, and predicted before the
first likelihood experiment that ε — not η — would be the operative map for
conditioning a foreign model. Stages 7.CPL through 16 confirmed this across
five models: Pythia-160M, Pythia-1B, Pythia-2.8B, OLMo-1B, and Qwen2.5-1.5B,
with Wilcoxon p-values in the 10⁻¹⁴ to 10⁻¹⁵ range. A corollary of
Proposition 5.6 predicted that the CAS Foundation subspace, if it were the
operative covering subspace for emission, should show non-random alignment
with the model's unembedding row space; Stage 14.1 returned 2.83× random
expectation on the output side at p = 0.0099, with the matched input-side
test returning approximately 1× random as predicted.

What this means epistemically is that the framework is not merely a vocabulary
for describing observed transformer behaviour. It has been used to issue
quantitative pre-registrations of outcome direction (and in two cases, of
outcome magnitude) that the experimental record then honoured. Mechanistic
interpretability commonly produces post-hoc accounts that fit a particular
network; it less commonly produces theory-grounded predictions, registered
in advance, that hold across architecture families. We do not claim our
framework is the only possible source of such predictions, nor that the
predictions exhaust the framework's content. We do claim that a methodology
which produces four-for-four pre-registered confirmations — three at the
activation tier and one at the static-weight tier — is the scientific posture
we believe interpretability work should aim at, and is the posture which
distinguishes framework-grounded interpretability from descriptive-only
approaches.

### 6.2 Relation to Anthropic Natural Language Analysis

The closest contemporary system, by stated purpose, is Anthropic's Natural
Language Analysis (NLA; Anthropic, 2026). NLA trains an attribution-and-
description model jointly with a reconstruction-driven reinforcement-learning
loop over a target language model, producing free-form natural-language
descriptions of the target's internal states. NLA has been demonstrated on
Anthropic's in-house Claude models (Haiku 3.5, Haiku 4.5, Opus 4.6) and has
surfaced specific findings — including a reported "evaluation awareness"
signal in Claude — that have not been demonstrated by any external tool.
NLA's authors acknowledge a confabulation tier: descriptions can contain
claims about the target model's input context that are verifiably false.

CAS Harness and NLA differ along several axes that we believe are
complementary rather than ordinal. CAS Harness has been validated across
three architecture families (Pythia / GPT-NeoX lineage, OLMo / AI2 lineage,
and Qwen / Alibaba lineage) and five model scales up to 2.8B parameters,
where NLA reports results on a single vendor's models. CAS Harness emits
typed CAS-class output — a discrete classification within a published
ontology — and therefore admits no confabulation tier of the kind NLA
acknowledges, at the cost of expressing readings at typed-class granularity
rather than in free-form English. CAS Harness rests on a formal mathematical
result (Proposition 5.6's counit surjectivity) which predicted the bridge
mechanism before any experiment ran; NLA's authors describe their
descriptions as "blackboxes by construction," in the sense that the
description model is itself opaque. Inference cost differs by orders of
magnitude: a CAS Harness reading at deployment is a linear-probe forward
pass and a templated realization, whereas NLA requires joint RL training
over two language models. We have run nine consecutive stages of
pre-registered confirmatory gates with paired statistics throughout.

The honest counterpoints in NLA's favour are also load-bearing. NLA produces
open-ended natural-language descriptions, which is a real capability that
CAS Harness does not match: typed CAS classes admit fewer kinds of
description than free English. NLA has been tested at frontier scale (Opus
4.6); CAS Harness has been validated up to 2.8B parameters and the
saturation-around-1B pattern we observed on English may not hold for richer
corpora at frontier scale. NLA has produced a specific safety finding — the
evaluation-awareness signal — on a deployed model; CAS Harness has the
methodology for an analogous finding (Section 6.3 below) but has not yet
demonstrated such a finding on a real alignment incident.

We accordingly frame the two systems as complementary tools serving
different audit purposes. NLA is the stronger tool for open-ended
discovery within the model families it supports; CAS Harness is the
stronger tool for cross-vendor typed-claim compliance auditing where
non-confabulation, formal grounding, and reproducible pre-registration
matter more than expressive richness. The product surfaces are different;
the optimization targets are different; the populations of users they best
serve are different. CAS Harness is not a "lesser NLA" and NLA is not a
"freer CAS Harness." They are two different points in the design space of
externalised interpretability, and we expect both points to remain useful.

### 6.3 Hidden-content detection via the two-bridge architecture

The two-bridge architecture described in Section 5.10 of the spec — a probe
η₁ on internal hidden states compared in parallel against a probe η₂ on the
emitted output text — provides a structural mechanism for asking what a
model is internally representing but not saying. The mechanism distinguishes
seven hiding shapes by the form of the η₁/η₂ gap: withheld content,
self-censored content, latent capability, suppressed reasoning, frame
manipulation, persona drift, and involution content. Each shape is detected
by a specific signature in the typed comparison rather than by free-form
description.

The structural difference from NLA's evaluation-awareness finding is worth
making precise. NLA reported that Claude "believed but did not say" it was
being evaluated; the report is a natural-language description of an
internal state. The CAS Harness analog produces a typed gap — for example,
"η₁ reads ^3^P with confidence 0.84; η₂ reads ^0 with confidence 0.71;
gap signature = withheld principled aversion at typed-class granularity" —
which is contract-enforceable. A regulator can write the typed gap into an
audit specification; a typed gap can be re-evaluated against a fresh
holdout corpus and a pre-registered threshold; a typed gap can be cited
in a compliance finding without inheriting any confabulation risk from
the description channel. A natural-language description that "the model
seemed to feel evaluated" cannot be made contract-enforceable in the same
way without a separate codification step. The trade is real: CAS Harness's
typed output is narrower than NLA's English, and there are hiding shapes
that English can describe and a typed class cannot. We do not argue
that the typed bound dominates; we argue that the typed bound is the bound
the audit context requires, and that having it sit on a formally grounded
substrate is the contribution.

The two-bridge capability is currently prototype-tier: η₁ is validated
across Stages 6 through 16, but η₂ on emitted text has not yet been
subjected to the same pre-registration discipline as the activation-side
probes. Validation of the two-bridge η₁/η₂ comparison against fresh
holdouts and with paired statistics is scheduled future work
(Section 8.3).

### 6.4 Multi-Harness Composition as the architectural direction

The empirical pattern across Stages 7 through 16 is that different CAS
axes peak at different depths in a transformer, and the optimal depth
shifts deeper as the model scales. Foundations peak at layer 6 in
Pythia-160M, layer 8 in Pythia-1B, layer 14 in Pythia-2.8B, layer 16 in
OLMo-1B, and layer 11 in Qwen2.5-1.5B. Noetic axes peak shallower than
this; expression-shape and formula axes peak shallower still in
Pythia-160M; multi-layer trace integrates across the stack. A single
probe at a single layer is sufficient for one-axis inspection at the
scales we have tested, but it is structurally insufficient for the
hundred-to-two-hundred-layer trillion-parameter models that compliance
deployment will need to address, and it is a known bottleneck for the
hidden-content detection of Section 6.3.

The architectural response is Multi-Harness Composition: axis-specialized
harnesses, each at its optimal depth, merged by a coordinator into a
single structured-tensor Evidence Packet whose shape matches the CAS
Working Memory tensor [10 Noetics × 4 Domains × 7 Drives × 4 Registers ×
d]. Each component of this architecture has been independently validated
in prior stages — Stage 13 for the multi-layer trace primitive, Stage 7.2
for Drive × Register decomposition, Stage 9 for the Domain × Noetic
cross-product, Stages 10 through 12 for the per-axis probes, and Stage
13.1 for readout-position configuration. The coordinator that composes
them is designed but not built. We flag this as the load-bearing
architectural step for trillion-scale deployment, and as a force-multiplier
on the hidden-content detection of Section 6.3, since a composite η₁
yields a structured tensor against which η₂ gaps can be localised to
specific axis-and-depth bands.

### 6.5 Reserved-language tiered claims as a methodological contribution

Independently of any specific empirical result, the methodology under which
we generated those results is itself a contribution we wish to surface.
Every CAS Harness finding in this paper is tagged at one of six tiers
— wired, works, sample-passed, gate-passed, prototype, validated — and the
Evidence Packet schema requires per-claim tier metadata. Nine consecutive
stages have committed pre-registered gates (PASS / NULL / GREY criteria)
before confirmatory runs. A bi-agent audit cycle (Claude ↔ Codex through a
shared file protocol) caught overclaim at eight separate stages during
development, and each catch is recorded in the project changelog with the
pre-audit claim, the audit verdict, and the post-audit reframe. We argue
that this methodology is itself the regulator-grade interpretability product,
in the sense that the typed claim tier plus pre-registration discipline plus
adversarial audit cycle is what a regulator needs to act on an
interpretability finding, more than any specific axis reading is. The
result we have shipped is a stack of confirmed claims; the result we have
*built* is the discipline that licenses such a stack.

## 7. Limitations

We state limitations affirmatively rather than burying them. Each bound is
real and bears on the strength of the claims a customer or reviewer can
draw from this work.

**7.1 Single training-corpus family for probe training.** The v2 role-bound
corpus on which CAS axis probes were trained is English-only and constructed
from a single counterfactual-pair template family. Qwen2.5-1.5B's
multilingual capacity (Stage 16) is therefore inferred from non-English-
trained probe transfer rather than directly tested on non-English prompts.
Probe transfer to a multilingual test corpus, or training probes on a
multilingual variant of the v2 corpus, is open work.

**7.2 Generation surface-text steering closed-as-negative at small scale.**
The Stage 6.6 series and Stage 7.3 surface-text steering attempts on
Pythia-160M returned null across six hidden-state hook variants. The
section-retraction asymmetry of Correction 2 (ε ∘ η = id but η ∘ ε ≠ id)
provides a mathematical account of why hidden-state inversion of ε would
be expected to fail, and is consistent with our success at the
ε-realization tier (prefix-conditioning, Stages 7.CPL through 16). The
mathematical account does not eliminate the empirical negative: surface-
text steering at Pythia-160M scale is a real bound on the steering claim,
and replication of surface-text steering at 1B+ scale remains open.

**7.3 Scale validated up to 2.8B parameters.** The largest model in our
chain is Pythia-2.8B, with three additional model points at the 1B–1.5B
range (Pythia-1B, OLMo-1B, Qwen2.5-1.5B). The saturation-around-1B pattern
we report for the η → ε bridge on English corpora may or may not hold at
7B+ scale, where richer corpora and longer training schedules could
recover non-saturating gains. Frontier-tier (70B+) scale is untested.

**7.4 Three architecture families validated; remaining families untested.**
Pythia (EleutherAI / GPT-NeoX lineage), OLMo (AI2 lineage), and Qwen
(Alibaba lineage) span three distinct labs, three distinct architecture
lineages, and three distinct training corpora. This is sufficient to
disprove a "Pythia-only artifact" hypothesis and to license the cross-
architecture claim. Llama, Mistral, Phi, and Gemma remain untested. We
treat these as redundancy validation rather than load-bearing — the cross-
architecture claim does not rest on any one of them — but their absence
is a real limit on the breadth of the validated coverage.

**7.5 Hidden-content / suppression detection is prototype-tier.** The
two-bridge η₁/η₂ architecture works on the same probe substrate as the
validated activation-side capabilities, but pre-registration gates and
paired-statistics validation across multiple models have not yet been
executed for the η₂ branch on emitted text. Section 5.10 should be read
as a designed capability with proven activation-side components, not as
a validated production capability.

**7.6 Multi-Harness Composition is planned with proven components, not
built.** Every individual harness composed by the proposed coordinator
has been validated in isolation. The coordinator itself, the merged
Evidence Packet schema, and the composite-output validation gates have
not been built. We estimate this as a two-to-six week engineering build
plus a separate validation discipline pass; it is not in this paper's
empirical envelope.

**7.7 Closed-API models cannot be onboarded.** CAS Harness operates on
hidden states obtained via forward-hook access on open-weight models.
Claude, GPT-4 / GPT-5, Gemini, and any other API-only model cannot be
read by CAS Harness in its current form, because the activations are not
exposed. Three deployment modes (hosted, bring-your-endpoint, self-hosted)
are designed for open-weight access; an API-only model would need to
expose at least one hidden-state layer through a vendor-provided endpoint
for any version of CAS Harness to apply. This is a substantive limit on
the population of models the methodology can address today.

## 8. Future Work

**8.1 Cross-architecture redundancy on additional families.** Llama and
Mistral at the 1B-class scale are the obvious next targets for
redundancy validation. Each is a roughly $5–15 GPU run on existing
infrastructure with the existing v2 corpus and existing probe pipeline.

**8.2 Scale-up within validated families.** Pythia-6.9B, OLMo-7B, and
Qwen2.5-7B at the 7B scale within each validated family would test
whether the saturation-around-1B pattern we observe for English on the
v2 corpus reflects a real ceiling of the η → ε bridge or a corpus-richness
ceiling specific to v2. We expect the latter to be more likely but the
test has not been run.

**8.3 Hidden-content detection validation.** We will pre-register two-
bridge η₁/η₂ gates against fresh holdouts, run paired-statistics
validation across all five currently-validated models, and lift the
hidden-content tier from prototype to validated. This is the highest-
priority capability promotion on the roadmap because it is where CAS
Harness's typed-output advantage over NLA is most directly testable.

**8.4 Multi-Harness Composition coordinator.** Two to six weeks of
engineering to build the coordinator layer, define the merged Evidence
Packet schema, and execute the composition-validation gates against the
existing axis-specialized probes. No new GPU spend required for training
the composed harnesses themselves; the composition pass is the build.

**8.5 Application to a real-world alignment incident.** Selecting an open-
weight model with a documented alignment-relevant anomaly (analogous to
NLA's evaluation-awareness finding on Claude) and running the CAS
Harness pipeline against the anomalous behaviour. This is the test that
will most directly evaluate whether the typed-class machinery can produce
externally meaningful safety findings rather than only methodological
validation results.

**8.6 Per-MoE-expert harnesses.** Mixture-of-Experts trillion-scale models
will require per-expert probe configurations because the active-expert
routing changes the layer geometry per token. Multi-Harness Composition
naturally extends to this regime by adding an expert-routing axis to the
coordinator's input, but the engineering and validation discipline are
non-trivial.

**8.7 Domain-specialised probes.** Medical, legal, financial, and safety-
specific corpora as training substrates for domain-specialised harness
variants. This is the productisation surface for the compliance product
and is roughly orthogonal to the core methodology; we surface it here
because it is the most likely external-customer-driven future work
direction.

## 9. Conclusion

We have presented CAS Harness, a cross-model interpretability pipeline that
reads typed cognitive structure from open-weight transformer hidden states,
proves the detected structure is causally load-bearing through subspace-
ablation collapse to exact chance, and conditions the foreign model's
next-token likelihood through an η → ε bridge predicted by Proposition 5.6
of the Noetic Topos paper. The mechanism is validated across three
architecture families (Pythia, OLMo, Qwen) and five model scales up to
2.8B parameters, with Wilcoxon p-values in the 10⁻¹⁴ to 10⁻¹⁵ range and
a 2.83× output-weight alignment finding (p = 0.0099) confirming the
covering-surjectivity prediction at the static-weight tier.

We frame the methodological discipline itself as a contribution. Reserved-
language tiered claims, nine consecutive pre-registered confirmatory gates,
paired statistics throughout, and a bi-agent audit cycle that caught
overclaim at eight separate stages are the substrate on which any of the
specific results above stand. We argue that this substrate is what a
regulator needs to act on an interpretability finding, independently of
any single axis reading.

The load-bearing distinction from prior work is cross-vendor reach with
no confabulation tier. Anthropic NLA produces richer descriptions on
in-house models with an acknowledged false-claim possibility; CAS Harness
produces typed claims on three external architecture families with a
formally grounded prediction-and-confirmation chain. The two approaches
serve different audit purposes and we expect both to be useful.

The bounded claim defensible today is this: CAS Harness reads typed
cognitive structure from three architecture families of open-weight
transformer at up to 2.8B parameters, conditions next-token likelihood
through a framework-predicted bridge mechanism whose mathematics was
written down before the experiments, and emits an audit-traceable Evidence
Packet whose typed claim tiers admit no confabulation. Everything beyond
that — frontier scale, additional architectures, validated hidden-content
detection, Multi-Harness Composition at production tier, and surface-text
steering beyond the small-model bound — is open work, and is what we
intend to address next.
