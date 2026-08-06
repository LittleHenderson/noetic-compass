# Memristive Context, Lacunarity, Injection, and Steering

## Proposed supplemental research track v0.1

**Artifact status:** DRAFT / OPEN / Ring 4 / NOT LICENSED / HELD

**Publication status:** PROPOSED SUPPLEMENTAL TRACK / NO CHARTER PAPER NUMBER

**Base commit:** 56c43caca7e61aea03254ffdc5484ecdf35bcdbe

**Canon effect:** NONE

**Implementation conclusion:** NONE

**Experimental conclusion:** NONE / NOT STARTED

**Physical-device conclusion:** NONE

**Causal, cognitive, safety, clinical, and product conclusions:** NONE

**Internal cross-review:** OPEN

**External specialist review:** OPEN

**Public disclosure:** NOT AUTHORIZED / HELD

This is a source-bound research draft. It does not amend the Project Coherence
charter, assign itself a charter paper number, replace the Wave 1 engineering
papers, change Gate 4 or Gate 5, add a canonical symbol, license a claim,
authorize software development or an experiment, identify a physical device, or
authorize public disclosure.

## Abstract

Classical circuit theory, mathematical dynamical systems, software activation
interventions, and physical memory devices use overlapping words for objects
that are not interchangeable. An ideal electrical memristor is a constitutive
relation between charge and flux. A generalized memristive system is an
electrical state system. A history-state model is a mathematical object. A
software implementation is an executable artifact. A fabricated device is a
physical object. A metaphor may compare any two of them but carries no theorem,
measurement, causal, material, or product consequence.

This supplemental track proposes a typed, nonphysical research question: can a
versioned history state improve held-out prediction of a narrowly defined CAS
response beyond a matched memoryless baseline, and can any improvement survive
order, reset, drift, lacunarity, injection-direction, layer, token, and context
controls? It also separates classical multiscale gliding-box lacunarity from
repository quantities that currently share the word but use different domains
and formulae. The proposed study treats injection as a declared mathematical
addition at a model coordinate and steering as an experimental schedule, not as
electrical current, prompt-injection security, proof of a latent concept, or
causal identification.

No implementation or experiment is supplied. The contribution is a type
system, definitions, candidate equations, falsifiable hypotheses, matched
baselines, threat model, evidence requirements, and explicit non-inference
rules. Every empirical, physical, causal, cognitive, safety, product, licensing,
canon, and disclosure matter remains open.

## 1. Governance position

The Project Coherence charter currently lists seven candidate papers [S1]. This
draft is not one of those seven. The Wave 1 CAS-Ohm report already states that a
standalone extension may not be represented as an eighth charter paper without
a deliberate charter amendment [S6]. The correct status here is therefore
*proposed supplemental track*. The lead editor may later recommend that it
remain a technical note, become an appendix, merge into the CAS-Ohm or PCBA
paper, or seek a charter amendment. This draft makes none of those decisions.

The draft inherits five hard boundaries:

1. Gate 4 remains open, Ring 4, not licensed, held, and not frozen [S13] [S14]
   [S15] [S16] [S17] [S18].
2. Gate 5 remains open with experimental execution not started [S19] [S20]
   [S21] [S22] [S23].
3. Shared CAS-Ohm, PCBA, Harness, safety, and product claims retain their exact
   ledger states [S2].
4. The existing symbol registry is not extended by this paper [S4].
5. Open material remains open; held material remains held [S5].

No later section should be read as silently changing one of these controls.

## 2. Exact scope

The draft does four things:

- separates six frequently conflated object types;
- gives provisional mathematical definitions for context, lacunarity,
  injection, steering, memory state, path dependence, hysteresis, and a matched
  memoryless baseline;
- defines a future, separately authorized comparison protocol; and
- states exactly what evidence would still be required before any stronger
  wording became eligible for review.

The draft does not:

- assert that CAS is an electrical circuit;
- map cognitive quantities to volts, amperes, ohms, charge, or flux;
- assert that CAS contains a memristor or generalized memristive system;
- validate a state variable, hysteresis loop, lacunarity measure, steering
  effect, cognitive construct, or causal mechanism;
- certify any repository source as a conforming implementation of this draft;
- claim a physical material or fabricated device;
- claim safety, clinical, regulatory, product, or commercial value;
- license a claim, admit canon, assign authorship, authorize submission, or
  authorize disclosure; or
- authorize compute, data access, model access, RunPod, or an experiment.

## 3. Source inheritance

### 3.1 Wave 1 engineering

The Wave 1 CAS-Ohm report already proposes, without admitting, a nonphysical
state equation and requires held-out path dependence beyond a matched
memoryless baseline [S6]. The PCBA draft leaves stateful and memristive
time/state semantics open [S7]. Its claim matrix permits only the wording that
classical memristive systems motivate a nonphysical history-dependent research
question [S8]. Its obligation ledger requires initialization, update, timebase,
reset, drift, uncertainty, provenance, negative fixtures, preregistration,
independent audit, and replication [S11].

This paper elaborates that open research question. It does not claim to close
it.

### 3.2 Gate 4

Gate 4 preserves unresolved source scales, unit conflicts, stateful PCBA
semantics, live calibration, empirical validation, causal interpretation,
capability authority, Evidence Packet eligibility, safety, and product
boundaries [S13] [S14] [S15] [S16] [S17] [S18]. In particular, the existing
CAS-Ohm operationalization of
steering alpha and activation projection is a profile-specific research
candidate, not an electrical measurement [S14, S16].

### 3.3 Gate 5

Gate 5 supplies a preregistration and evidence-control architecture [S19] [S20]
[S21] [S22] [S23].
It does not supply this paper with a completed experiment. Any future
memristive-history study would need its own exact claim binding, frozen design,
model and environment identities, ordering, raw evidence, negative results,
outcome-access chronology, independent replay, replication, and claim-language
review.

### 3.4 Repository lacunarity and intervention labels

The repository contains source files whose names and comments use
*lacunarity*, *correction*, *intervention*, and *steering* [S24–S28]. This is a
textual source observation only. It is not a finding that those files execute,
conform to this proposal, implement classical lacunarity, produce valid
interventions, reveal cognition, improve safety, or support a product claim.

## 4. Non-coercible type system

### 4.1 Type EIM: ideal electrical memristor

An ideal charge-controlled electrical memristor is an electrical constitutive
object relating charge \(q\) and flux linkage \(\phi\), with

\[
M(q)=\frac{d\phi}{dq},
\qquad
v(t)=M(q(t))\,i(t),
\qquad
q(t)=\int_{-\infty}^{t}i(\tau)\,d\tau .
\]

This is the historical circuit-theory type introduced by Chua [E1]. Its
variables have electrical dimensions. The equations do not define a cognitive
quantity, software state, or physical CAS component.

### 4.2 Type EMS: generalized electrical memristive system

A current-controlled generalized memristive system has a state \(w\), input
current \(i\), electrical response \(v\), and equations of the form

\[
\dot w=f(w,i,t),
\qquad
v=R(w,i,t)i .
\]

This wider electrical dynamical-system type follows Chua and Kang [E2] and is
not identical to the ideal \(q\)-\(\phi\) memristor. Later memory-circuit
literature broadens the family further [E5]. The generality of the equations
does not make every history-dependent model an electrical memristive system.

### 4.3 Type MET: conceptual metaphor

A conceptual metaphor is a documented comparison such as “a constraint may
remember prior flow.” It may guide questions or diagrams. It supplies no
dimension-preserving map, theorem, state equation, executable behavior,
measurement, causal mechanism, or material identity.

### 4.4 Type MHS: mathematical history-state model

A mathematical history-state model is a tuple

\[
\mathcal H=(X,U,C,J,Y,F,G,\Theta,\Delta,\mathsf{Reset}),
\]

where \(X\) is a state space; \(U\) present input; \(C\) typed context; \(J\)
typed injection; \(Y\) response; \(F\) state update; \(G\) observation or
prediction map; \(\Theta\) frozen parameters; \(\Delta\) timebase; and
\(\mathsf{Reset}\) initialization/reset behavior.

This is a proposed mathematical type. State-space methods motivate explicit
state and update separation [E8], and system-identification practice motivates
comparison of candidate dynamic structures against alternatives [E10]. Neither
source validates this CAS profile.

### 4.5 Type SWI: software implementation

A software implementation would be exact executable bytes plus dependency,
environment, model, data, test, and provenance identities that claim to realize
a particular MHS specification. Source text alone is not an implementation
receipt. A local test alone is not an authenticated execution, scientific
result, or implementation-conformance decision.

No Type SWI conclusion is made here.

### 4.6 Type PHD: physical hardware device

A physical hardware device is a fabricated, instrumented object with materials,
geometry, electrodes, environmental conditions, measurement calibration,
uncertainty, and device-level provenance. Strukov and colleagues reported a
nanoscale physical model and device interpretation [E3], later accompanied by a
corrigendum [E4]. Those papers are evidence about their reported electrical
system, not evidence for a CAS device.

No Type PHD object is in the evidence for this draft.

### 4.7 No implicit casts

The following casts are forbidden:

| From | To | Why the cast is invalid |
|---|---|---|
| EIM | EMS | A generalized state system need not satisfy the ideal \(q\)-\(\phi\) relation. |
| EMS | MHS | Electrical variables and passivity cannot be discarded without an explicit typed abstraction. |
| MET | MHS | A metaphor supplies no state space, update law, reset rule, or prediction. |
| MHS | SWI | Equations do not prove executable conformance. |
| SWI | PHD | Software bytes are not material hardware. |
| PHD | EIM | A physical device label does not by itself prove the ideal constitutive relation. |
| Source presence | Any empirical claim | Text and bytes do not establish a run or result. |
| Randomized injection | Causal construct claim | Manipulation alone does not identify the semantic cause of an outcome. |

Every cross-type claim needs a separately reviewed map, assumptions, evidence,
and authority. None is supplied.

## 5. Provisional definitions

### 5.1 Context

At sequence index \(t\), context is a frozen typed record

\[
c_t=(c_t^{\mathrm{task}},c_t^{\mathrm{prompt}},
c_t^{\mathrm{model}},c_t^{\mathrm{layer}},
c_t^{\mathrm{token}},c_t^{\mathrm{environment}},
c_t^{\mathrm{time}},c_t^{\mathrm{group}}).
\]

Each field must declare its schema, missingness, provenance, and whether it is
available before the response. *Context* here does not mean consciousness,
intent, an unrestricted LLM context window, or an unlogged analyst judgment.
Changing a context field creates a different comparison stratum unless the
design explicitly models the change.

### 5.2 Memory state

Memory state is a versioned mathematical record \(x_t\in X\) that is sufficient
for the candidate model’s declared dependence on admitted history:

\[
x_{t+1}
=
F_\theta(x_t,u_t,c_t,j_t,\Delta t_t,\epsilon_t),
\qquad
\widehat y_t
=
G_\theta(x_t,u_t,c_t,j_t).
\]

The state profile must specify:

- state dimension, domain, and units or explicit dimensionless status;
- initialization and burn-in;
- update ordering;
- sampling interval and missing-time behavior;
- reset, washout, checkpoint, and restore semantics;
- clipping, saturation, drift, and numerical precision;
- randomness and seed control;
- uncertainty and identifiability limits; and
- a complete state-transition provenance log.

An unlogged cache, hidden model KV state, optimizer residue, random-number
state, provider session, or hardware nondeterminism is a nuisance or confounder,
not an admitted memory state.

### 5.3 Injection

Injection is a declared mathematical operator acting on a named software
coordinate:

\[
J_{\ell,k,t}(h_{\ell,k,t};\alpha_t,d_t)
=
h_{\ell,k,t}+\alpha_t d_t ,
\]

where \(\ell\) is a bound layer, \(k\) a token position or position rule,
\(d_t\) a bound direction with norm and construction provenance, and
\(\alpha_t\) a dimensionless profile coefficient unless separately calibrated.

Activation Addition, representation engineering, and contrastive activation
addition provide primary examples of activation-space modification [E11] [E12]
[E13].
They motivate experimental design only. Their reported findings do not transfer
to CAS, to an untested model, or to this state profile.

Injection here is not:

- prompt injection or a security exploit;
- electrical current injection;
- a medical injection;
- causal identification;
- proof that \(d_t\) encodes a concept; or
- a live product capability.

### 5.4 Steering

Steering is the complete preregistered schedule

\[
\mathcal S=(J,\mathcal A,\mathcal D,\mathcal L,\mathcal K,
\mathcal T,\mathcal C,\mathcal N),
\]

covering the injection operator, alpha schedule, directions, layers, token
rules, timing, contexts, and null/control schedules. A response associated with
steering is an observed experimental association until causal identification
requirements close.

### 5.5 Path dependence

For two admitted histories \(H_t^{(a)}\) and \(H_t^{(b)}\) with the same present
input, context, and injection, a candidate model is path-dependent on that
comparison if

\[
H_t^{(a)}\neq H_t^{(b)},\qquad
(u_t,c_t,j_t)^{(a)}=(u_t,c_t,j_t)^{(b)},
\qquad
\widehat y_t^{(a)}\neq \widehat y_t^{(b)}
\]

under a predeclared tolerance and uncertainty rule.

This is a mathematical or predictive criterion. Observing it would not by
itself establish a physical memristor, causal memory mechanism, cognitive
memory, or safety effect.

### 5.6 Hysteresis

For this proposal, hysteresis is a restricted form of path dependence tested by
a preregistered cyclic or reversal schedule. A candidate loop statistic may be

\[
A_{\mathrm{loop}}
=
\left|\oint \widehat y\,d\alpha\right|,
\]

but the statistic is meaningful only with fixed orientation, sampling,
interpolation, normalization, repeated cycles, reset rules, drift controls, and
uncertainty. Classical hysteresis models demonstrate that hysteresis has its own
mathematical structure and applicability conditions [E9]. A visually looped
plot is not sufficient: delay, drift, saturation, filtering, order imbalance,
or plotting choices can also create apparent loops.

### 5.7 Classical gliding-box lacunarity

Let \(M_r\) be mass in a gliding box at scale \(r\), with nonzero mean. Classical
gliding-box lacunarity is

\[
\Lambda_{\mathrm{GB}}(r)
=
\frac{\mathbb E[M_r^2]}{\mathbb E[M_r]^2}
=
1+\frac{\operatorname{Var}(M_r)}{\mathbb E[M_r]^2}.
\]

Allain and Cloitre define lacunarity from fluctuations in a mass distribution
across scales [E6], and Plotnick and colleagues apply the multiscale statistic
to texture [E7]. The box domain, mass rule, scale set, boundary handling, and
zero-mass policy are part of the definition.

### 5.8 Repository-labelled lacunarity

Exact repository text includes several different quantities labelled
*lacunarity* [S24–S27]. One source-level formula is
\(\operatorname{Var}(p)/\operatorname{Mean}(p)^2\), which equals
\(\Lambda_{\mathrm{GB}}-1\) only when \(p\) is the declared box-mass random
variable under the same scale and sampling convention. Other labelled
quantities count active categories or unique operators. Therefore:

- the shared name does not establish mathematical identity;
- a single vector-dispersion score is not automatically multiscale
  gliding-box lacunarity;
- category-coverage complements are not automatically mass-distribution
  lacunarity; and
- source presence is not implementation, validity, calibration, or scientific
  evidence.

This draft does not rename or repair those upstream sources. It requires future
work to use distinct identifiers.

### 5.9 Proposed history lacunarity

A future study may define a history-event mass \(M^{H}_{r,t}\) over a frozen
event ontology and window rule, then compute

\[
\Lambda_H(r,t)
=
\frac{\mathbb E[(M^{H}_{r,t})^2]}
{\mathbb E[M^{H}_{r,t}]^2}.
\]

This is a proposed diagnostic, not an admitted CAS measure. It must be compared
against simpler dispersion, sparsity, entropy, occupancy, and sequence-length
statistics. If it adds no held-out information, the lacunarity-specific claim
fails even if a history model predicts well.

### 5.10 Matched memoryless baseline

The strict memoryless baseline is

\[
\widehat y^{(0)}_t
=
G_{\theta_0}^{(0)}(u_t,c_t,j_t),
\]

with no recursive state and no access to prior sequence elements. Matching
requires the same:

- present-time features and preprocessing;
- model, layer, token, direction, alpha, and context identities;
- train/tune/test groups and sequence exclusions;
- target, loss, optimization budget, regularization, and stopping rule;
- effective parameter or capacity budget, with any mismatch reported;
- evaluation times, missingness policy, and uncertainty method; and
- access to nuisance covariates available at prediction time.

A second *observed-window baseline*

\[
\widehat y^{(W)}_t
=
G_{\theta_W}^{(W)}(u_{t-W:t},c_{t-W:t},j_{t-W:t})
\]

is not memoryless, but is needed to test whether a recursive latent state adds
value beyond an explicit finite history window. Calling \(G^{(W)}\) memoryless
would conceal the comparison.

## 6. Candidate nonphysical model

The proposed study object is

\[
\begin{aligned}
x_{t+1} &=
F_\theta(x_t,u_t,c_t,j_t,\Delta t_t),\\
\rho_t &= R_\theta(x_t,c_t),\\
\widehat y_t &=
G_\theta(x_t,u_t,c_t,j_t,\rho_t).
\end{aligned}
\]

Here \(\rho_t\) is named a *history response coefficient*. It is not resistance,
memristance, an ohmic quantity, or a physical material parameter. It must use a
new typed identifier rather than inherited \(R\), \(M\), \(V\), \(I\), \(q\), or
\(\phi\) symbols.

The model family must include:

- a null state whose update ignores history;
- a state-permutation or equivalent nonidentifiability audit;
- a low-capacity and capacity-matched family;
- deterministic and explicitly stochastic variants if both are proposed;
- a resettable synthetic fixture where the true history law is known;
- a negative fixture generated from a memoryless process;
- a drift-only fixture;
- a delay-only fixture; and
- a saturation-only fixture.

Passing a synthetic fixture would validate only the covered software path, not
the target scientific claim.

## 7. Candidate research questions

Every item below is a preregistration candidate, not a finding.

### H1. Held-out predictive memory

A frozen history-state profile reduces held-out sequence-group prediction loss
relative to the matched strict memoryless baseline by a preregistered margin,
with uncertainty excluding the null margin.

Falsifier: the advantage disappears on held-out groups, reverses, is smaller
than the margin, or is explained by capacity, leakage, or tuning access.

### H2. Added value beyond an observed history window

The history-state profile improves held-out prediction beyond a capacity-matched
finite observed-window baseline.

Falsifier: the window baseline matches or exceeds the stateful profile.

### H3. Order-sensitive path dependence

Two randomized histories with the same present input, context, injection, and
history multiset but different order produce a preregistered response
difference after reset and drift controls.

Falsifier: order effects are absent, unstable, attributable to timestamps or
carryover, or no larger than shuffled-history controls.

### H4. Reversal-loop behavior

A frozen cyclic alpha schedule produces a reproducible, uncertainty-qualified
loop statistic beyond delay-only, drift-only, memoryless, and order-shuffled
controls.

Falsifier: the loop vanishes after synchronization and drift correction, is
explained by saturation, or fails held-out replication.

### H5. Reset and persistence

The declared reset returns the measured state proxy and subsequent response to
the preregistered baseline tolerance, while nonreset intervals show the
prespecified persistence profile.

Falsifier: reset is incomplete, state survives unexpectedly, or the result is
indistinguishable from session contamination.

### H6. Context specificity

History effects follow a preregistered context interaction and do not generalize
outside the declared context strata unless transfer is separately predicted.

Falsifier: effects depend on analyst-selected strata, disappear under grouped
holdout, or transfer unpredictably.

### H7. Lacunarity-specific incremental value

A frozen multiscale history-lacunarity feature improves held-out prediction or
error characterization beyond occupancy, variance, coefficient of variation,
entropy, sparsity, sequence length, and category coverage.

Falsifier: simpler features match it, the selected scale is unstable, or the
effect depends on post-outcome scale selection.

### H8. Injection and steering specificity

Any state-conditioned response to the declared steering schedule exceeds zero,
random same-norm direction, wrong-layer, wrong-token, label-shuffle,
context-shuffle, reversed-history, and alpha-order controls on held-out groups.

Falsifier: a matched control is equal or larger, the direction is not
reproducible, or the response appears only in the tuning split.

## 8. Future protocol requirements

No protocol is authorized by this draft. A candidate submitted for authorization
must freeze:

1. one exact current claim-ledger record or a separately approved new record;
2. the type assignments and forbidden casts;
3. model repository, revision, weights, tokenizer, code, dependencies,
   container, hardware, precision, and environment;
4. data rights, sources, sequence grouping, exclusions, and raw-evidence policy;
5. context schema and missingness;
6. state space, update, initialization, reset, timing, randomness, and drift;
7. direction construction, layer, token, alpha schedule, and all controls;
8. classical, repository-labelled, and proposed lacunarity identifiers;
9. memoryless and observed-window baselines with matching rules;
10. hypotheses, estimands, margins, uncertainty, multiplicity, stopping, and
    falsifiers;
11. preregistration, amendment, outcome-access, packet, anchoring, and review
    ordering; and
12. independent replay, held-out replication, specialist review, and permitted
    claim language.

Preregistration and preservation of negative results are supported by the open
science literature [E15] [E16] [E17], but those sources do not authorize or
validate a
CAS study.

## 9. Sequence design

### 9.1 Experimental unit

The experimental unit must be a sequence group, not an individual token or
correlated row. All elements derived from one prompt family, conversation,
document, subject, session, seed family, or model cache must remain in one split
unless a stricter independence analysis justifies otherwise.

### 9.2 Randomization

Where authorized and technically feasible, randomization should cover:

- forward versus reverse schedule;
- history A versus history B;
- active versus zero alpha;
- genuine versus random same-norm direction;
- declared versus wrong layer;
- declared versus wrong token rule;
- context labels and context-order controls;
- reset versus sham reset; and
- blinded run and review order.

Randomization receipts must be generated before outcome access and retained
with the exact seed and algorithm.

### 9.3 Washout and carryover

The protocol must determine washout from a preregistered synthetic or pilot
stage that cannot be reused for target inference. Insufficient washout,
uncontrolled cache, model process reuse, thermal drift, provider reuse, or
hidden conversation state makes a memory claim ineligible.

### 9.4 Repeated cycles

One loop is descriptive. A hysteresis candidate requires repeated cycles,
counterbalanced orientation, held-out schedules, uncertainty, and a rule for
cycle-to-cycle change. Training on the same cycle used for evaluation is not a
held-out test.

## 10. Candidate estimands

The protocol may consider, but has not selected:

\[
\Delta_{\mathrm{mem}}
=
\mathbb E[
\mathcal L(\widehat y^{(0)},y)
-
\mathcal L(\widehat y^{(H)},y)
],
\]

\[
\Delta_{\mathrm{window}}
=
\mathbb E[
\mathcal L(\widehat y^{(W)},y)
-
\mathcal L(\widehat y^{(H)},y)
],
\]

\[
\Delta_{\mathrm{order}}
=
\mathbb E[
y\mid H^{(a)},u,c,j
]
-
\mathbb E[
y\mid H^{(b)},u,c,j
],
\]

and normalized loop area

\[
\widetilde A_{\mathrm{loop}}
=
\frac{\left|\oint y\,d\alpha\right|}
{(\alpha_{\max}-\alpha_{\min})(y_{\max}-y_{\min})}.
\]

Every estimand needs an exact sampling population, grouping, missingness,
normalization, uncertainty, and multiplicity rule. No numeric threshold or
effect size is selected here.

## 11. Controls and negative evidence

The minimum control family is:

| Control | Main threat addressed |
|---|---|
| Strict memoryless baseline | Extra predictive value of recursive state |
| Observed-window baseline | Extra value beyond visible recent history |
| Capacity-matched static model | Parameter-count advantage |
| History-order shuffle | Spurious history dependence |
| Timestamp shuffle | Time/drift confounding |
| Delay-only synthetic process | Apparent loop from latency |
| Drift-only synthetic process | Apparent memory from drift |
| Saturation-only synthetic process | Apparent branch dependence from clipping |
| Negative memoryless fixture | False-positive state detection |
| Zero-alpha injection | Baseline response |
| Random same-norm direction | Direction specificity |
| Wrong layer and wrong token | Location specificity |
| Label and context shuffle | Semantic-label leakage |
| Sham reset | Reset-procedure artifact |
| Fresh-process reset | Hidden runtime state |
| Reverse and counterbalanced schedules | Order and orientation artifacts |

Negative, null, failed, mixed, or nonreplicated results must remain in the
evidence record. Negative controls are useful for detecting bias and
confounding, but they do not prove the absence of every threat [E16].

## 12. Causal boundary

An injection is an intervention on software state in the ordinary engineering
sense. A randomized schedule can strengthen a local experimental comparison.
Neither fact identifies a high-level cognitive, semantic, safety, or behavioral
cause.

A causal claim would additionally require:

- an explicit causal graph or structural model;
- defined treatment, outcome, unit, interference, and time ordering;
- identification assumptions and estimand;
- exchangeability or a justified randomization analysis;
- consistency and positivity conditions where applicable;
- nuisance, carryover, mediator, and selection-bias analysis;
- negative controls and falsifiers;
- sensitivity analysis; and
- qualified independent review.

Pearl’s causal framework is cited for the distinction between structural causal
claims and association or manipulation [E14]. This draft supplies no causal
identification.

## 13. Cognitive and semantic boundary

A predictable change in an activation, score, or output does not establish that
the injected direction is a stable cognitive concept, that the state stores a
human-like memory, or that a lacunarity score measures a blind spot. Such claims
need construct validity, convergent and discriminant evidence, alternative
taxonomies, wrong-axis and random-subspace controls, cross-model replication,
and careful language review.

The terms *attention*, *memory*, *context*, *state*, and *steering* in this
paper are engineering or mathematical terms unless a separately licensed claim
says otherwise.

## 14. Electrical and physical boundary

The physical-device literature is relevant only to type discipline. A future
physical profile would need:

- material stack, dimensions, terminals, fabrication, and lot;
- instrumentation, calibration, uncertainty, and environmental conditions;
- voltage/current compliance and electrical units;
- repeated sweeps, endurance, retention, temperature, and device variability;
- explicit tests of the claimed constitutive relation;
- model alternatives and physical failure analysis; and
- qualified device-physics and electrical-engineering review.

None of these is present. A pinched or looped software plot, learned scalar,
history-dependent equation, or resistance metaphor is not a physical device.

## 15. Lacunarity threat model

The proposed lacunarity work is vulnerable to:

- omitting the scale \(r\);
- changing the mass ontology after seeing outcomes;
- equating \(\Lambda\) with \(\Lambda-1\);
- using a category-coverage complement as if it were gliding-box lacunarity;
- selecting a favorable scale post hoc;
- ignoring zeros or boundary boxes inconsistently;
- conflating sparsity, variance, entropy, and lacunarity;
- treating a 40-slot vector as a spatial field without a justified adjacency;
- using learned thresholds as validated measurement cutoffs;
- pooling incompatible contexts;
- sequence-length leakage;
- reporting a composite without its components; and
- inferring cognition or safety from a geometric statistic.

A future implementation must use names that encode the domain and definition,
for example \(\Lambda_{\mathrm{GB}}\), \(\Lambda_H\), or a separately named
CAS coverage score.

## 16. History-state threat model

The proposed history-state work is vulnerable to:

- training/test sequence leakage;
- hidden KV cache or process reuse;
- timestamps serving as labels;
- unequal model capacity;
- differential early stopping or tuning;
- reset procedures that do not reset all state;
- unlogged random-number state;
- response lag misread as memory;
- drift misread as persistence;
- clipping or saturation misread as hysteresis;
- nonidentifiable state reparameterizations;
- analyst-selected cycles;
- loss of null or adverse runs;
- outcome access before design freeze; and
- transferring one model’s result to another model or context.

## 17. Software and implementation boundary

No repository source is certified here as an implementation of the proposed
MHS type. A future conformance claim would require:

1. an executable specification version;
2. exact source and generated-artifact closure;
3. strict schemas and type-injective serialization;
4. deterministic reference fixtures and adversarial negatives;
5. complete state-transition and reset traces;
6. cross-language conformance if multiple implementations exist;
7. hermetic dependency and environment identities;
8. authenticated executed-node evidence;
9. independent reproduction; and
10. a narrow claim record.

Existing source labels and tests can inform the audit inventory, but this draft
makes no correctness, runtime, conformance, completeness, or production
implementation conclusion.

## 18. Gate relationship

### 18.1 Gate 4

This paper does not close any Gate 4 criterion. Stateful PCBA semantics,
CAS-Ohm calibration, empirical hypotheses, causal interpretation, safety,
capability authority, and Evidence Packet eligibility remain open.

### 18.2 Gate 5

This paper does not add a Gate 5 experiment. It supplies no preregistration
instance, joined run, authenticated execution, admitted Evidence Packet,
independent replay, replication, WORM receipt, external acceptance, or
disclosure authorization. Gate 5 remains not started experimentally.

### 18.3 Shared ledgers

No shared claim or theorem is changed. This draft asserts no new theorem. The
algebraic identity

\[
\mathbb E[M^2]/\mathbb E[M]^2
=
1+\operatorname{Var}(M)/\mathbb E[M]^2
\]

is a standard consequence of
\(\mathbb E[M^2]=\operatorname{Var}(M)+\mathbb E[M]^2\), not a novel CAS
theorem. The proposed hypotheses remain Ring 4 research questions.

## 19. Permitted and prohibited wording

### Permitted now

- Classical memristor and memristive-system theory motivate a typed,
  nonphysical history-state research question.
- Wave 1 already records that stateful and memristive CAS dynamics are open.
- This draft defines a proposed history-state model and matched baselines.
- Exact repository text contains several nonidentical quantities labelled
  lacunarity.
- Activation-steering papers motivate control designs for a future study.
- No experiment, implementation conclusion, or physical-device conclusion is
  reported.

### Prohibited now

- CAS is memristive.
- CAS contains an ideal or physical memristor.
- CAS history state is implemented or validated.
- Repository lacunarity is classical lacunarity.
- Lacunarity measures cognitive blind spots.
- Injection reveals or controls a cognitive concept.
- Steering causes a semantic, behavioral, or safety effect.
- A hysteresis loop has been observed.
- The model improves prediction.
- A physical, causal, cognitive, safety, clinical, regulatory, product, or
  commercial conclusion exists.
- Any claim is licensed, canonical, accepted, submitted, peer reviewed, or
  authorized for public disclosure.

## 20. Evidence ladder

| Level | Evidence | Current state | Maximum present statement |
|---|---|---|---|
| L0 | Exact source identity | PRESENT | The named bytes existed at the bound revision. |
| L1 | Primary literature | PRESENT | The cited source motivates a definition or comparison. |
| L2 | Typed mathematical proposal | PRESENT AS DRAFT | The proposal is explicitly specified. |
| L3 | Conforming software implementation | ABSENT / OPEN | No conclusion. |
| L4 | Joined authorized experiment | ABSENT / NOT STARTED | No conclusion. |
| L5 | Independent replay and replication | ABSENT / OPEN | No conclusion. |
| L6 | Physical-device evidence | ABSENT / OPEN | No conclusion. |
| L7 | Causal, cognitive, or safety validation | ABSENT / OPEN | No conclusion. |
| L8 | Product, license, canon, and disclosure authority | NOT LICENSED / HELD | No promotion or release. |

Levels do not promote automatically. A software pass would not establish an
experiment; an experiment would not establish a physical device; a predictive
result would not establish cognition or causality; scientific review would not
establish product, license, canon, or disclosure authority.

## 21. Publication decision tree

After internal adversarial review, the lead editor should choose exactly one:

1. retain this work as a held supplemental technical note;
2. merge the type system and baselines into the provisional CAS-Ohm report;
3. merge the stateful component interface into the PCBA paper;
4. retain only an experimental preregistration appendix for CAS Harness 2; or
5. propose a charter amendment for a separately numbered paper.

No choice should be made from title preference alone. The decision should follow
scope, theorem burden, experimental burden, authorship, disclosure, citation,
and specialist-review records.

## 22. Required specialist reviews

Before any experiment:

- nonlinear circuits and memristive-systems review;
- dynamical-systems and hysteresis review;
- lacunarity/fractal-statistics review;
- system-identification and time-series review;
- activation-steering engineering review;
- statistics and causal-inference review;
- data-rights, privacy, and research-governance review;
- security and supply-chain review; and
- claim-language, product, licensing, canon, and disclosure review as separate
  authorities.

No reviewer may accept outside their scope.

## 23. Limitations

This draft has no data, run, trained profile, calibration, state estimate,
effect size, uncertainty interval, replication, device, implementation
conformance receipt, authorship record, or external review. The candidate model
may be unnecessary, nonidentifiable, too flexible, inferior to a static or
finite-window baseline, or scientifically uninteresting. Lacunarity may add no
information beyond simpler statistics. Steering effects may fail every matched
control. Null or negative outcomes are valid possible endpoints.

## 24. Conclusion

The viable contribution is not a claim that CAS has acquired a memristor. It is
a disciplined research interface that prevents electrical theory, history-state
mathematics, activation intervention, repository labels, executable software,
and physical devices from collapsing into one ambiguous word.

The next evidence-bearing step, if separately authorized, is a preregistered
comparison of one typed history-state profile against strict memoryless and
observed-window baselines, with path-order, reversal, reset, drift, lacunarity,
direction, layer, token, context, and negative controls. Until that work and all
independent reviews exist, the correct status remains:

**DRAFT / OPEN / Ring 4 / NOT LICENSED / HELD**

## External primary references

- [E1] L. O. Chua, “Memristor—The Missing Circuit Element,” 1971.
- [E2] L. O. Chua and S. M. Kang, “Memristive Devices and Systems,” 1976.
- [E3] D. B. Strukov et al., “The Missing Memristor Found,” 2008.
- [E4] D. B. Strukov et al., corrigendum to “The Missing Memristor Found,” 2009.
- [E5] M. Di Ventra, Y. V. Pershin, and L. O. Chua, “Circuit Elements With
  Memory: Memristors, Memcapacitors, and Meminductors,” 2009.
- [E6] C. Allain and M. Cloitre, “Characterizing the Lacunarity of Random and
  Deterministic Fractal Sets,” 1991.
- [E7] R. E. Plotnick et al., “Lacunarity Indices as Measures of Landscape
  Texture,” 1993.
- [E8] R. E. Kalman, “A New Approach to Linear Filtering and Prediction
  Problems,” 1960.
- [E9] I. D. Mayergoyz, “Mathematical Models of Hysteresis,” 1986.
- [E10] L. Ljung, *System Identification: Theory for the User*, second edition,
  1999.
- [E11] A. M. Turner et al., “Activation Addition: Steering Language Models
  Without Optimization,” 2023.
- [E12] A. Zou et al., “Representation Engineering: A Top-Down Approach to AI
  Transparency,” 2023.
- [E13] N. Rimsky et al., “Steering Llama 2 via Contrastive Activation
  Addition,” 2024.
- [E14] J. Pearl, *Causality: Models, Reasoning, and Inference*, second edition,
  2009.
- [E15] B. A. Nosek et al., “The Preregistration Revolution,” 2018.
- [E16] M. Lipsitch, E. Tchetgen Tchetgen, and T. Cohen, “Negative Controls: A
  Tool for Detecting Confounding and Bias in Observational Studies,” 2010.
- [E17] National Academies of Sciences, Engineering, and Medicine,
  *Reproducibility and Replicability in Science*, 2019.

The exact identifiers, URLs, narrow uses, and non-inference boundaries are in
the accompanying citation ledger.
