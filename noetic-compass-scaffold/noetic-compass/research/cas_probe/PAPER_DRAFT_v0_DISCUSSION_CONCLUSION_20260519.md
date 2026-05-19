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
