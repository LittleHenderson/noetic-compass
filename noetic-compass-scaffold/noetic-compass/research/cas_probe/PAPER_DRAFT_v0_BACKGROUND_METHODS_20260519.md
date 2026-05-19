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
