# Paper 5 — ACBE-P5: Approximate Causal Abstraction

Status: `DRAFT / SOURCE-BOUND DELTA / OPEN CAUSAL TRANSFER / RING 4 / NOT LICENSED / HELD`

Base commit: `143cff40f94cf207a9130d6a7c07975a1fcbf0b9`

This manuscript is a research draft. It does not report a completed experiment,
an authenticated joined-run Evidence Packet, causal validation of CAS/TKS,
model-safety evidence, a product result, canon admission, a license decision,
publication approval, or disclosure approval. Every empirical statement below
is a proposed hypothesis or protocol unless explicitly identified as a
repository fact.

## Abstract

This paper specifies a falsifiable meaning for *approximate causal abstraction*
within Project Coherence. A low-level interventional model and a high-level
interventional model are compared through three maps: a state map, a context
map, and an intervention map. For every preregistered context–intervention pair,
the low-level post-intervention law is pushed through the state map and compared
with the high-level post-intervention law. Their discrepancy is an
interventional commutation defect. The proposal reports the full defect vector,
its worst-case and design-weighted summaries, uncertainty, coverage, and
non-vacuity controls. Zero defect recovers exact interventional commutation;
total-variation defects compose subadditively under compatible abstractions.

The construction is deliberately narrower than causal representation learning,
probing, correlation, stochastic composition, or sheaf gluing. It also does not
reinterpret the legacy Noetic Topos label `ACBE`: the registered source says
that `ACBE` is only a name for a four-level preorder. Paper 5 therefore uses
`ACA` for the mathematical relation and `ACBE-P5` only as the versioned paper
identifier. Counterexamples show why observational fit, constant maps,
many-to-one intervention maps, and average-only scores cannot identify a
nontrivial causal abstraction. The resulting experimental program is
preregistration-first, negative-control-heavy, and fail-closed. No current
Project Coherence artifact supplies the joined-run evidence required for an
empirical conclusion, so causal transfer remains `OPEN`.

## 1. Naming and source boundary

The working publication title in the Project Coherence charter is “ACBE as
Approximate Causal Abstraction.” That title creates a possible historical
collision that must be controlled rather than silently resolved.

In the registered conservative Noetic Topos source,
`peer_review/journal_submission/main.tex`, line 163 states that “ACBE” is only a
name for the fixed preorder

\[
A \succeq B \succeq C \succeq D.
\]

The source does not expand the acronym and does not give the preorder a causal
interpretation. Its designated descent maps are formal categorical inputs. In
addition, the source reduction lemma and the Project Coherence red team show
that the legacy ACBE coverage clause adds no nonmaximal covering information in
the conservative topology. The Noetic Topos 2.0 successor preserves `ACBE` as
a formal mark on one coordinate partition; its own specification explicitly
withholds empirical meaning.

Paper 5 therefore adopts the following namespace rule:

| Token | Type | Meaning in this draft |
|---|---|---|
| `ACBE_legacy` | `LEGACY_PREORDER_AND_DESCENT_LABEL` | The source-bound four-level preorder and its designated descent morphisms. No expansion or causal semantics is inferred. |
| `ACBE_NT2` | `MARKED_CONTEXT_PROVENANCE_LABEL` | The first coordinate-partition mark in the finite Noetic Topos 2.0 candidate. It records formal provenance only. |
| `ACBE-P5` | `PUBLICATION_PROGRAM_IDENTIFIER` | The versioned identifier of this Paper 5 research lane. It is not a mathematical object. |
| `ACA` | `INTERVENTIONAL_MODEL_RELATION` | The new, typed approximate causal-abstraction candidate defined below. |

No theorem in this paper may replace one of these types with another. In
particular, the sentence “legacy ACBE was always approximate causal
abstraction” is prohibited.

## 2. What this paper adds

The paper contributes a source-bound delta rather than another architecture:

1. a finite/measurable interventional response profile suitable for SCMs,
   controlled neural interventions, or other explicitly causal systems;
2. a typed abstraction candidate containing state, context, and intervention
   maps;
3. per-intervention, worst-case, weighted, tail, estimand-transfer, coverage,
   and non-vacuity quantities;
4. bounded mathematical results for zero defect, composition, and estimand
   transfer;
5. explicit counterexamples and identifiability classes;
6. a preregistered experiment and Evidence Packet contract; and
7. interfaces to CAS Harness 2, Noetic Markov Sheaves, TKS v8, CAS-Ohm, and CAS
   PCBA without promoting any of them.

The central object is not a scalar called “causality.” It is an auditable family
of comparisons indexed by interventions and contexts.

## 3. Prior technical foundations

Rubenstein et al. introduced exact transformations between structural-equation
models that agree on intervention effects (`CIT-RUBENSTEIN-2017`). Beckers and
Halpern refined exact abstraction notions and made the intervention map a
load-bearing part of the comparison (`CIT-BECKERS-HALPERN-2019`). Beckers,
Eberhardt, and Halpern then defined approximate causal abstractions using
application-dependent distances between low- and high-level intervention
responses (`CIT-BECKERS-EBERHARDT-HALPERN-2020`). Rischel and Weichwald gave a
finite categorical framework in which an abstraction error is compositional
(`CIT-RISCHEL-WEICHWALD-2021`).

For neural networks, Geiger et al. test alignments between neural locations and
high-level variables through interchange interventions
(`CIT-GEIGER-ETAL-2021`). Soft interventions require additional care because
the induced intervention map need not be automatic; Massidda et al. provide a
dedicated treatment (`CIT-MASSIDDA-ETAL-2023`). Causal representation learning
asks how high-level causal variables can be learned from low-level observations
(`CIT-SCHOLKOPF-ETAL-2021`), but learning a representation is not itself a
certificate that an interventional diagram commutes.

This draft specializes those foundations into a conservative CAS/TKS research
protocol. The specialization and proposed estimands are not claimed as novel
until a dedicated novelty review is complete.

## 4. Type system

### 4.1 Interventional response profile

An interventional response profile is

\[
\mathcal M=(C,X,I,K),
\]

where:

- \(C\) is a measurable context space;
- \(X\) is a measurable state or outcome space;
- \(I\) is a typed set of allowed interventions; and
- \(K:C\times I\rightsquigarrow X\) is a Markov kernel giving the
  post-intervention law.

The intervention label is not decorative. It must refer to a declared
intervention operator in an SCM, randomized experiment, or controlled model
execution. A generic conditional distribution \(P(X\mid Z)\) is not promoted
to \(K(\cdot\mid c,\operatorname{do}(i))\) merely by renaming \(Z\).

Deterministic models are included by Dirac kernels. A solved SCM supplies such
a profile only after its allowed interventions, solution semantics, and context
handling are fixed. For neural systems, the profile must bind model revision,
weights, tokenizer, input, hook location, tensor coordinates, intervention
operator, execution code, and stochastic state.

### 4.2 Abstraction candidate

Given low- and high-level profiles

\[
\mathcal M_L=(C_L,X_L,I_L,K_L),\qquad
\mathcal M_H=(C_H,X_H,I_H,K_H),
\]

an abstraction candidate is

\[
\mathcal A=(\tau,\kappa,\omega,E,d,\mu),
\]

with:

- a measurable state map \(\tau:X_L\to X_H\);
- a measurable context map \(\kappa:C_L\to C_H\);
- a partial intervention map \(\omega:I_L\rightharpoonup I_H\);
- a nonempty preregistered evaluation domain
  \(E\subseteq C_L\times\operatorname{dom}(\omega)\);
- a preregistered probability-law metric or divergence \(d\); and
- an optional preregistered design distribution \(\mu\) on \(E\).

The maps are frozen before confirmatory outcomes are accessed. If \(\tau\) is
learned, the training data and learning rule belong to a disjoint discovery
phase. If \(\omega\) is inferred from \(\tau\), that derivation must be
explicit and checked; it is not assumed to exist for arbitrary hard or soft
interventions. The schema does not silently assume that \(\tau\) is surjective;
unused high-level support must be reported, and a task may preregister
surjectivity on declared support as an admission requirement.

### 4.3 Interventional commutation defect

For \((c,i)\in E\), define

\[
\delta_{\mathcal A}(c,i)
=
d\!\left(
\tau_*K_L(\cdot\mid c,i),
K_H(\cdot\mid \kappa(c),\omega(i))
\right).
\]

The two routes are:

\[
(c,i)\xrightarrow{K_L}P(X_L)\xrightarrow{\tau_*}P(X_H)
\]

and

\[
(c,i)\xrightarrow{(\kappa,\omega)}(\kappa(c),\omega(i))
\xrightarrow{K_H}P(X_H).
\]

The candidate is an \(\varepsilon\)-approximate causal abstraction on \(E\)
when

\[
\Delta_\infty(\mathcal A)
:=
\sup_{(c,i)\in E}\delta_{\mathcal A}(c,i)
\leq \varepsilon.
\]

This is a mathematical relation relative to the declared models, maps, domain,
and metric. Whether data identify or estimate it is a separate question.

### 4.4 Non-vacuous Paper 5 admission

A low defect can be vacuous. A Paper 5 *admissible* candidate must also satisfy
all preregistered gates below:

1. **coverage:** every required intervention and context has a defined map and
   valid response record;
2. **support:** mapped evaluations remain inside declared low/high support, or
   every extrapolation is separately flagged;
3. **retention:** \(\tau\) passes a task-specific non-collapse test fixed before
   outcomes;
4. **intervention separation:** distinct causally material interventions are
   not merged without an explicit equivalence argument and collision test;
5. **specificity:** the candidate beats preregistered sham, random, wrong-site,
   and label controls by the required margin;
6. **uncertainty:** the upper confidence bound, not only a point estimate,
   meets the tolerance; and
7. **replication:** the result survives a held-out joined run with an independent
   numerical replay and claim-language review.

Failure of any gate leaves the result negative or indeterminate. It does not
permit redefining the gate after outcome access.

## 5. Exact distinctions from adjacent constructs

| Construct | Required type | What it can establish | What it cannot establish by itself |
|---|---|---|---|
| `ACBE_legacy` | preorder plus designated descent morphisms | A source-bound formal relation | Causal variables, interventions, causal effects, or empirical validity |
| `ACBE_NT2` | immutable cover-provenance mark | Which formal generator and ancestry produced a cover record | Causal direction or intervention semantics |
| Causal representation learning | learning problem for latent/high-level causal variables | A candidate \(\tau\), variables, or model under stated assumptions | That \(\omega\) exists or that the intervention diagram has low defect |
| Intervention | mechanism-changing operator with a declared target and semantics | A counterfactual/interventional response under the model or experiment | Equivalence to a prompt edit, observation, correlation, or arbitrary distribution shift |
| Markov kernel | stochastic map \(X\rightsquigarrow Y\) | Conditional stochastic transformation and composition | A causal interpretation without an intervention-indexed model |
| Correlation | property of an observational joint law | Association | Direction, intervention response, mediation, or abstraction validity |
| Sheaf compatibility/gluing | local-to-global consistency relative to a cover | Compatibility or existence of a global extension | Causal identification or correctness of the local measurements |
| Approximate causal abstraction (`ACA`) | typed relation between two interventional profiles | Bounded disagreement of paired intervention responses on a declared domain | Truth of either model, semantic uniqueness, safety, cognition, generalization beyond scope, or product fitness |

The categorical Paper 4 boundary remains controlling: Markov composition,
naturality, compatible local distributions, and a global extension do not imply
causal abstraction. They may organize evidence only after intervention
semantics are supplied independently.

## 6. Mathematical results and proof sketches

All results in this section are candidate Paper 5 mathematics. They are not
empirical findings.

### Proposition 6.1 — zero defect recovers exact commutation

Assume \(d\) separates probability measures. Then
\(\Delta_\infty(\mathcal A)=0\) if and only if, for every \((c,i)\in E\),

\[
\tau_*K_L(\cdot\mid c,i)
=
K_H(\cdot\mid\kappa(c),\omega(i)).
\]

*Proof.* A supremum of nonnegative quantities is zero exactly when each
quantity is zero. Metric separation converts zero distance into equality of
the two laws. The converse is immediate. \(\square\)

This is an exact relation only on \(E\); it says nothing about unevaluated
interventions.

### Proposition 6.2 — total-variation composition bound

Let \(\mathcal A_{LM}\) and \(\mathcal A_{MH}\) be compatible abstraction
candidates with total-variation defects at most \(\varepsilon_1\) and
\(\varepsilon_2\), respectively, on a composition-compatible evaluation
domain. Then their composite has defect at most

\[
\varepsilon_1+\varepsilon_2.
\]

*Proof sketch.* Pushforward by a measurable map is nonexpansive in total
variation. Apply this contraction to the first defect and the triangle
inequality to the intermediate and final high-level laws. Compatibility of the
context and intervention maps identifies the second comparison. \(\square\)

For other metrics, this claim requires the appropriate data-processing or
Lipschitz condition and must not be copied unchanged. The result parallels the
compositional-error objective in `CIT-RISCHEL-WEICHWALD-2021` but is stated here
for this draft's kernel profile.

### Proposition 6.3 — bounded estimand-transfer error

Use total variation and let \(g:X_H\to[0,1]\) be measurable. For every
\((c,i)\in E\),

\[
\left|
\mathbb E_{\tau_*K_L(c,i)}g-
\mathbb E_{K_H(\kappa(c),\omega(i))}g
\right|
\leq \delta_{\mathcal A}(c,i).
\]

Consequently, if the defect is at most \(\varepsilon\) for each of two
interventions \(i_1,i_0\), the error in transferring their contrast is at most
\(2\varepsilon\).

*Proof.* The first inequality is the variational characterization of total
variation for functions in \([0,1]\); the contrast bound follows by the
triangle inequality. \(\square\)

This bounds a contrast between two *given interventional laws*. It does not
identify either law from observational data.

### Proposition 6.4 — intervention collisions impose error

Suppose two low-level interventions \(i_0,i_1\) in the same mapped context
satisfy

\[
d_{TV}(\tau_*K_L(c,i_0),\tau_*K_L(c,i_1))=\gamma>0
\]

but \(\omega(i_0)=\omega(i_1)\). Then at least one of their abstraction defects
is at least \(\gamma/2\).

*Proof.* Both low-level pushforwards are compared with the same high-level law.
The triangle inequality gives \(\gamma\leq\delta(c,i_0)+\delta(c,i_1)\).
\(\square\)

This makes intervention-map collisions measurable rather than merely
terminological.

## 7. Counterexamples and non-identifiability

### 7.1 Observational equivalence does not identify intervention response

Let \(U\sim\operatorname{Bernoulli}(1/2)\). Model \(M_1\) has
\(X:=U, Y:=X\). Model \(M_2\) has \(Y:=U, X:=Y\). Both induce

\[
P(X=0,Y=0)=P(X=1,Y=1)=1/2.
\]

Yet under \(\operatorname{do}(X=0)\), \(M_1\) forces \(Y=0\), while in
\(M_2\), \(Y=U\) remains Bernoulli. Thus identical observational laws can
produce different interventional laws. No statistic of the observational joint
law alone decides whether an ACA diagram commutes. This finite witness is the
basic reason that correlation, prediction, probing, and observational gluing
cannot substitute for interventions. Pearl's graphical identification program
and interventional Markov-equivalence results supply the broader technical
boundary (`CIT-PEARL-1995`, `CIT-HAUSER-BUHLMANN-2012`).

### 7.2 Constant-map trivialization

For any low-level model, let \(\tau\) send every state to one high-level state
\(h_0\). Let the high-level model always return \(h_0\), and map every low-level
intervention to the same high-level intervention. The defect is zero for every
evaluation, even though the abstraction preserves no distinctions. Therefore
defect alone is not a non-vacuity certificate. Retention and intervention-
separation gates are necessary.

### 7.3 Average defect can hide a catastrophic intervention

Take 100 equally weighted intervention cases, with defect zero on 99 and defect
one on the remaining case. The weighted mean defect is \(0.01\), while the
worst-case defect is \(1\). A mean-only acceptance rule can therefore pass an
abstraction that fails completely on a rare intervention. Paper 5 requires the
full defect vector, \(\Delta_\infty\), and a preregistered tail summary in
addition to \(\Delta_\mu\).

### 7.4 Hidden confounding

An observational association between a candidate low-level variable and an
outcome can be produced by a direct effect, reverse direction, or an unobserved
common cause. Unless randomization or an explicit identification strategy
closes that ambiguity, the causal transfer is not identified. Counterexamples
to broad observational multi-cause identification reinforce this limitation
(`CIT-DAMOUR-2019`).

### 7.5 Representation non-uniqueness

High predictive accuracy or an apparently disentangled latent code does not
uniquely recover causal variables. Unsupervised disentanglement is
non-identifiable without inductive biases and supervision in the setting of
`CIT-LOCATELLO-ETAL-2019`. Paper 5 therefore treats a learned \(\tau\) as a
hypothesis generated under stated assumptions, not as causal evidence.

### 7.6 Stochastic and sheaf structure without interventions

A Markov kernel can encode a conditional law and a sheaf can encode compatible
local data. Neither object supplies a mechanism-changing operator. Two systems
can have identical observational kernels and identical compatible marginals
while differing under intervention. Cover provenance may record where evidence
came from, but it cannot manufacture causal semantics for that evidence.

## 8. Causal-identifiability classes

Each proposed result receives exactly one identification status:

| Status | Meaning | Permitted language |
|---|---|---|
| `DIRECT_INTERVENTIONAL` | The relevant low/high response laws are estimated from randomized or otherwise controlled interventions with valid execution identity. | “Estimated interventional defect under the registered design.” |
| `ASSUMPTION_IDENTIFIED` | A stated causal model and identification argument express the target from observational data; consistency, exchangeability/no unmeasured confounding, positivity, and other required assumptions are recorded. | “Identified under assumptions A…N.” |
| `PARTIALLY_IDENTIFIED` | Data and assumptions imply a bound or identified set, not a point value. | “The defect/contrast lies in the reported identified set.” |
| `NOT_IDENTIFIED` | Multiple compatible causal models yield different target values. | “Observationally compatible; causal transfer unresolved.” |
| `SIMULATION_ONLY` | Both interventional profiles are synthetic or stipulated. | “Verified in the named simulated model only.” |

A small standard error does not change `NOT_IDENTIFIED` into an identified
claim. Identification is a property of the estimand, design, and assumptions;
estimation precision comes later.

## 9. Necessary assumptions

The following checklist is mandatory where applicable:

1. the low- and high-level causal model classes and intervention semantics are
   specified before confirmatory analysis;
2. consistency links the implemented intervention to the declared potential
   outcome or SCM operator;
3. treatment versions and interference are absent or modeled explicitly;
4. positivity/support overlap holds for every reported target;
5. randomization is valid, or conditional exchangeability and all adjustment
   variables are justified for observational identification;
6. selection, censoring, missingness, and post-treatment conditioning do not
   create unaddressed bias;
7. \(\tau,\kappa,\omega\) and the evaluation domain are stable between
   discovery, confirmation, and replication;
8. measurement mappings are invariant enough for the compared quantities to
   have the same declared meaning;
9. stochastic seeds, decoding, batching, caching, and hook order do not change
   intervention semantics outside the model; and
10. generalization beyond evaluated models, layers, contexts, prompts, and
    interventions is not asserted without a separate transport argument.

For observational causal-effect estimation, the design must also state the
exact estimand and the identification formula. Standard adjustment or
propensity methods require their own assumptions; they are not generic
causality filters (`CIT-ROSENBAUM-RUBIN-1983`,
`CIT-HERNAN-ROBINS-WHATIF`).

## 10. Proposed estimands

The confirmatory protocol reports all of the following, with units and metric
orientation fixed in advance.

### 10.1 Primary abstraction estimands

1. **Worst-case defect**
   \[
   \Delta_\infty=\max_{(c,i)\in E}\delta(c,i).
   \]
2. **Design-weighted defect**
   \[
   \Delta_\mu=\mathbb E_{(c,i)\sim\mu}[\delta(c,i)].
   \]
3. **Tail defect**: a preregistered upper quantile such as
   \(Q_{0.95}(\delta)\).
4. **Coverage**
   \[
   \Gamma=|E_{valid}|/|E_{required}|.
   \]
   Missing or unmappable cases reduce coverage; they are never silently removed.

### 10.2 Causal-effect transfer estimand

For a bounded registered outcome \(g\) and two interventions \(i_1,i_0\),
define the low-to-high contrast-transfer error

\[
T_g=
\left|
[\mathbb E_{\tau_*K_L(c,i_1)}g-\mathbb E_{\tau_*K_L(c,i_0)}g]
-
[\mathbb E_{K_H(\kappa(c),\omega(i_1))}g-
 \mathbb E_{K_H(\kappa(c),\omega(i_0))}g]
\right|.
\]

This is an error between interventional contrasts. Calling it an ATE requires
a separately declared population and treatment contrast.

### 10.3 Specificity and non-vacuity estimands

- **control margin:** candidate-control difference in defect, with uncertainty;
- **intervention discrimination:** minimum distance between mapped responses for
  preregistered intervention pairs that should remain distinct;
- **retention score:** task-specific information or decision retention on a
  held-out set, measured independently of the ACA outcome;
- **collision rate:** proportion of causally distinct required interventions
  merged by \(\omega\); and
- **replication discrepancy:** absolute or distributional difference between
  confirmatory and held-out replication estimates.

No single aggregate replaces the full case-level table.

## 11. Negative and adversarial controls

Controls are selected by the intervention type and frozen before outcomes.
The minimum neural-model suite is:

- zero intervention;
- sham intervention that writes back the unchanged activation;
- same-norm random direction;
- orthogonal or null-space direction where defined;
- norm-matched candidate with shuffled semantic labels;
- wrong layer;
- wrong token or spatial position;
- intervention-assignment permutation;
- output-label permutation;
- matched-taxonomy control;
- length, frequency, and surface-form baselines where relevant;
- unrelated high-level variable and negative-control outcome;
- dose/order perturbation and sign-reversal checks when the mechanism predicts
  them;
- checkpoint, seed, architecture, and prompt-group replication; and
- an intervention-collision audit for \(\omega\).

Negative controls can reveal confounding or design artifacts but do not prove
the absence of all bias (`CIT-LIPSITCH-ETAL-2010`). Probe controls similarly
separate memorization from selectivity but do not establish causal abstraction
(`CIT-HEWITT-LIANG-2019`).

## 12. Preregistration and Evidence Packet requirements

One exact candidate claim must be added to the canonical claim ledger by the
authorized integration process before a confirmatory run. This delta does not
edit that ledger. The preregistration must bind:

- exact claim text and prohibited wording;
- low/high causal-model profiles and their assumptions;
- definitions and byte identities of \(\tau,\kappa,\omega\);
- discovery, confirmatory, and held-out replication splits;
- required evaluation domain, coverage rule, and unmappable-case policy;
- primary, weighted, tail, transfer, specificity, and retention estimands;
- metric, tolerance, confidence level, uncertainty method, multiplicity rule,
  power analysis, sample/group floors, stopping rule, and seeds;
- all controls, falsifiers, failure effects, exclusions, missingness rules, and
  subgroup analyses;
- exact model revision, weights, tokenizer, data, prompt, code, dependency,
  container, runtime, and hardware identities;
- executor, independent numerical auditor, replication team, and claim reviewer;
  and
- governance fixed at `RING 4 / NOT LICENSED / HELD`, with no public or product
  route.

The joined run must serialize an Evidence Packet v2 binding preregistration,
amendment chain, outcome-access event, raw intervention records, raw outputs,
execution manifest, case-level defects, aggregates, uncertainty, controls,
falsifiers, split accounting, numerical audit, replication, and claim review.
The current Harness v2 kernel treats packet hashes as integrity identities, not
signatures or authority. Its reported-criteria axis evaluates reported values,
not their truth. Authentication, durable ordering, a hermetic runner,
independent identity, replication, and external scientific review remain
separate gates.

A post hoc notebook, screenshot, favorable scalar, or unjoined worker log is not
a qualifying Evidence Packet. A structurally valid packet with failed criteria
is retained as negative evidence.

## 13. Proposed first experiment

The first executable profile should be deliberately narrow and non-safety:

1. choose one open-weight model, one exact revision, one synthetic algorithmic
   task, and one high-level causal program with exhaustively enumerable states;
2. generate candidate neural/high-level alignments on a discovery split only;
3. freeze \(\tau\), locations, \(\omega\), the intervention grid, tolerances,
   and controls;
4. run paired high-level and neural interchange interventions on confirmatory
   input pairs;
5. compute the case-level defect vector and all preregistered summaries;
6. run the full control suite and collision/non-collapse checks;
7. repeat on disjoint held-out prompt groups and at least one distinct seed or
   checkpoint;
8. have an independent implementation recompute every statistic from raw
   records; and
9. emit Evidence Packet v2 while preserving negative outcomes.

The high-level outcome can be exact-match for a finite deterministic program,
making total variation reduce to zero or one for a single deterministic case.
That simplicity is a feature for the first runner integration: execution and
mapping defects should be separated before continuous or natural-language
outcomes are introduced.

This is a proposed experiment, not an authorization to run it and not a report
that it has run.

## 14. Interfaces with the rest of Project Coherence

### 14.1 TKS v8

TKS v8 may provide typed low- or high-level deterministic state transitions.
Those functions become causal only after intervention semantics and a causal
model are declared. ACA does not retroactively causalize the forty-state
ontology or a typed transition graph.

### 14.2 Noetic Topos 2.0

Noetic cover marks can bind provenance for contexts, intervention families,
and evidence partitions. A future sheaf layer may test whether local defect
records agree on overlaps. It cannot change an unidentified causal target into
an identified one. `ACBE_NT2` and `ACA` remain different types.

### 14.3 Noetic Markov Sheaves

Paper 4's Markov kernels can carry distributions used in \(K_L\) and \(K_H\)
after causal semantics are supplied. Naturality and gluing are evidence-
consistency conditions, not causal conclusions. Paper 5 consumes Paper 4's
type boundary and does not weaken it.

### 14.4 CAS Harness 2

Harness 2 is the intended execution and evidence-binding layer. It must add a
registered ACA module, exact intervention-map artifacts, case-level defect
serialization, and independent replay. Current Harness controls are necessary
but no existing Evidence Packet proves ACA.

### 14.5 CAS-Ohm and CAS PCBA

Steering amplitude, projection, gain, constraint score, response region, and
physical telemetry retain their existing types. They may parameterize a
low-level intervention only under a calibrated profile. A response curve is not
an abstraction theorem, and an ACA result would not turn a score into voltage,
current, resistance, safety evidence, or hardware certification.

## 15. Current evidence state

At this source-bound delta:

- the mathematical definitions and four bounded propositions are available for
  specialist review;
- repository sources establish the legacy naming boundary and the Paper 4
  causal nonclaim;
- primary literature establishes that exact and approximate causal abstraction
  are existing research areas;
- the experiment, statistical thresholds, power analysis, model profile,
  candidate alignment, and canonical claim registration are not frozen;
- no joined-run ACA experiment has been executed;
- no ACA Evidence Packet v2 exists;
- no authenticated executor/auditor result or held-out replication exists; and
- no empirical, safety, product, canon, license, disclosure, or publication
  conclusion is licensed.

Accordingly, the causal transfer is explicitly `OPEN`.

## 16. Limitations and unresolved questions

The draft does not settle:

- which divergence best matches each high-level outcome space;
- how continuous, sequential, cyclic, or soft interventions should be mapped;
- when learned state maps are identifiable or unique;
- how abstraction error should be decomposed into state-map, context-map,
  intervention-map, measurement, and execution components;
- how to bound transport to new models or deployment contexts;
- whether Noetic provenance structures add useful experimental organization;
- whether the proposed combination is novel;
- whether the four propositions have been formalized and independently checked;
  or
- whether any future empirical result survives adversarial and external review.

These are obligations, not implied successes.

## 17. Conclusion

Approximate causal abstraction can become a precise Project Coherence research
object only by comparing intervention responses across explicitly mapped
low- and high-level models. The relevant evidence is a preregistered defect
family with coverage, uncertainty, controls, non-vacuity checks, replication,
and exact execution provenance. Neither the legacy ACBE preorder, a learned
representation, a Markov kernel, a correlation, nor a sheaf cover supplies that
evidence automatically. This draft defines the bridge; it does not claim that
CAS/TKS has crossed it.

## Appendix A — Compact notation

| Symbol | Type | Meaning |
|---|---|---|
| \(\mathcal M_L,\mathcal M_H\) | interventional response profiles | Low- and high-level causal candidates |
| \(C_L,C_H\) | measurable spaces | Contexts |
| \(X_L,X_H\) | measurable spaces | States/outcomes |
| \(I_L,I_H\) | typed sets | Allowed interventions |
| \(K_L,K_H\) | Markov kernels indexed by contexts and interventions | Post-intervention response laws |
| \(\tau\) | measurable map | Low-to-high state map |
| \(\kappa\) | measurable map | Low-to-high context map |
| \(\omega\) | partial typed map | Low-to-high intervention map |
| \(E\) | preregistered set | Required context–intervention evaluations |
| \(d\) | metric/divergence | Discrepancy between high-level laws |
| \(\delta(c,i)\) | nonnegative scalar | Case-level commutation defect |
| \(\Delta_\infty\) | nonnegative scalar | Worst-case defect |
| \(\Delta_\mu\) | nonnegative scalar | Design-weighted defect |
| \(\Gamma\) | proportion | Valid evaluation coverage |

## Appendix B — Claim-language ceiling

Permitted at this stage:

> “Paper 5 proposes a typed, intervention-indexed definition and validation
> protocol for approximate causal abstraction. Empirical causal transfer is
> open and no qualifying joined-run Evidence Packet exists.”

Prohibited at this stage:

- “ACBE proves CAS/TKS is causal.”
- “The Noetic Topos measures causal structure.”
- “The learned representation is a causal variable because a probe decodes it.”
- “A low observational residual establishes causal abstraction.”
- “The intervention is safe or beneficial.”
- “CAS Harness has validated approximate causal abstraction.”
- “This result is production-ready, licensed, canonical, or approved for public
  release.”
