# Noetic Markov Sheaves for Contextual AI Assessment

Publication track: Project Coherence charter Paper 4
Artifact status: `DRAFT / OPEN / RING 4 / NOT LICENSED / HELD / NOT FROZEN`
Research status: `METHODS AND TYPE ARCHITECTURE DRAFT / NO QUALIFYING EXPERIMENT`
Base commit: `a1cd990109e7561dfd03949bf0e1653461c7ae44`
As of: 2026-08-05

## Abstract

Contextual AI assessment often produces local measurements: distributions or model responses conditioned on prompts, layers, tokens, interventions, taxonomies, or other context selections. A tempting but invalid shortcut is to call compatible local measurements a sheaf and infer the existence of one global account. Pairwise-compatible probability marginals need not admit a global joint distribution, and even when an extension exists it need not be unique. Likewise, a Markov-kernel-valued diagram is not automatically a Set-valued Grothendieck sheaf or a weighted linear cellular sheaf.

This paper specifies a conservative research architecture for “Noetic Markov Sheaves.” The title names a program, not an established mathematical object. The architecture keeps six layers type-distinct: deterministic maps, Markov kernels, induced affine classical channels, finite families of local distributions with marginalization maps, Set-valued Grothendieck sheaves, and weighted linear cellular sheaves. Explicit conversion records are required between layers. For a frozen finite context schema, global probability extension is reduced to a linear feasibility problem whose evidence is a retained joint table or an independently checkable infeasibility dual. Acyclic extension theorems are available only after their exact hypotheses are proved and do not by themselves provide the uniqueness required by an ordinary sheaf condition.

The proposed AI-assessment protocol is preregistration-first and control-heavy. It separates structural feasibility from predictive utility, requires matched taxonomies and shuffled or wrong-location controls, binds every run to exact model and context identities, and treats negative results as admissible outputs. No current Evidence Packet establishes that the architecture measures cognition, alignment, safety, causal abstraction, or model truth. Implementation, experiments, formal comparison to existing probability-sheaf work, novelty review, and independent replication remain open.

## 1. Title and prior-art boundary

“Noetic Markov Sheaves” is the working title fixed by the Project Coherence charter. It must not be read as a novelty claim or as proof that the proposed data already form a sheaf.

Probability sheaves are established prior work. Simpson introduced probability sheaves and extended the Giry monad to their category [CIT-SIMPSON-2017]. Markov categories provide a compositional account of stochastic maps, conditional independence, and statistical structure [CIT-FRITZ-2020]. A 2025 preprint explicitly develops abstract sample spaces and probability sheaves from suitable Markov categories [CIT-STEIN-2025]. That preprint's peer-review status was not established from its primary record, but its conceptual overlap is direct and must be addressed.

Accordingly, this draft claims none of the following:

- that it is the first use of sheaves in probability;
- that it is the first connection between Markov categories and sheaves;
- that a Noetic label creates a new mathematical type;
- that the present architecture is equivalent to Simpson's or Stein's construction;
- that the architecture is already implemented; or
- that any AI assessment result has been obtained.

Any eventual contribution must be narrower: a source-bound CAS/TKS specialization with explicit context objects, typed comparison functors, finite extension certificates, controls, and evidence governance. Novelty remains `UNASSESSED`.

## 2. Governing corrections

The architecture inherits four nonnegotiable corrections from the Project Coherence migration and red-team records.

First, the legacy ACBE and RPM coverage clauses reduce to maximal sieves and do not provide distinct probability contexts. A Paper 4 context schema must be defined anew and cannot inherit empirical meaning from those labels.

Second, pairwise-compatible marginals may fail to extend globally. Three binary variables that are pairwise perfectly anticorrelated have matching uniform singleton marginals but no joint distribution. The contradiction is immediate: from `X!=Y` and `Y!=Z` one obtains `X=Z`, contradicting `X!=Z`.

Third, a Markov kernel is not a linear cellular sheaf. A cellular Laplacian requires finite-dimensional real or complex stalks, linear restriction maps, and chosen inner products [CIT-HANSEN-GHRIST-2019].

Fourth, deterministic maps, stochastic maps, induced channels, and unitary or quantum channels must remain distinct. Shared matrix notation does not erase different domains, normalization rules, composition laws, reversibility, or norm properties.

These corrections are recorded in `MIG-PROBABILISTIC-GLUING` and `MIG-DYNAMICS-TYPE-SEPARATION`. The empirical nonclaim is governed by `CLM-NOETOPOS-EMPIRICAL-ASSESSMENT`.

## 3. A six-layer type architecture

The proposed architecture is a stack of related but nonidentical types.

| Layer | Proposed type | Composition or restriction | What it does not imply |
|---|---|---|---|
| Deterministic dynamics | total map `f:X->Y` | ordinary function composition | stochastic calibration, reversibility, or sheaf descent |
| Stochastic dynamics | Markov kernel `K:X~>Y` | Chapman-Kolmogorov/Kleisli composition | causal identification, contraction, or global marginal extension |
| Classical distribution channel | affine map `K_*:Delta(X)->Delta(Y)` induced by a frozen finite kernel | affine composition | identity with the kernel record at the serialization/type level |
| Contextual probability data | presheaf candidate `Marg:K^op->Set`, `U |-> Delta(Omega_U)` | marginalization along context inclusions | the sheaf condition or a unique global distribution |
| Grothendieck sheaf | Set-valued presheaf satisfying unique descent for a named topology | restriction and unique gluing | vector-space structure, inner products, or a Laplacian |
| Linear/cellular analysis | functor on a finite cell poset into finite-dimensional vector spaces, plus weights | linear restrictions, coboundary, adjoint | probability normalization, positivity, or Markov semantics without a proved representation |

Each stored object must declare `semantic_type`, source and target identities, normalization convention, coefficient domain, and conversion provenance. A conversion is a typed morphism or data transformation, not an alias.

### 3.1 Deterministic and stochastic maps

For finite sets, a Markov kernel is a row-stochastic family

```text
K(y|x) >= 0,
sum_y K(y|x) = 1.
```

Given `K:X~>Y` and `L:Y~>Z`, composition is

```text
(L o K)(z|x) = sum_y K(y|x)L(z|y).
```

A deterministic map embeds by the Dirac kernel

```text
delta_f(y|x) = 1 if y=f(x), else 0.
```

The induced affine channel acts on distributions by

```text
(K_* p)(y) = sum_x p(x)K(y|x).
```

In a finite mathematical presentation, a kernel and its induced affine map determine one another under chosen bases. The implementation must still keep their records type-distinct: one has conditional rows indexed by source states; the other is an affine morphism between distribution objects. This avoids silently reusing deterministic-map, channel, or operator theorems at the wrong type. Giry's probability monad and modern Markov-category treatments supply the standard background [CIT-GIRY-1982; CIT-FRITZ-2020].

### 3.2 Context restrictions for kernels

Suppose `V` is a richer context than `U`. Any statement that a kernel family is context-compatible requires explicit restriction maps on inputs and outputs and a named commuting square. In the simplest deterministic-restriction profile, the candidate condition is

```text
r^Y_(V->U) o K_V = K_U o r^X_(V->U),
```

interpreted in the selected stochastic category. If either restriction is itself stochastic, the equation must use the same Markov-category composition on both sides. Equality may be exact, statistical, or approximate only if the record declares which one and how it is verified.

No such full Noetic kernel family exists in the current repository. This is a schema obligation, not an observed property.

## 4. Contextual distributions as a presheaf candidate

Let `K` be a finite category of measurement contexts ordered by inclusion. A context `U` identifies a finite set of variables or observables and a finite assignment space `Omega_U`. For `U subset V`, marginalization gives

```text
pi_(V->U) : Delta(Omega_V) -> Delta(Omega_U).
```

Because arrows run from smaller to larger contexts while marginalization runs from larger to smaller distributions, the assignment

```text
Marg(U) = Delta(Omega_U)
```

is a Set-valued presheaf candidate on `K`, once identity and composition of every registered marginalization map are checked.

Given a family of contexts `{U_i}` covering `V`, local distributions `mu_i` form a matching family when their marginals agree on all registered overlaps:

```text
pi_(U_i -> U_i intersect U_j)(mu_i)
  =
pi_(U_j -> U_i intersect U_j)(mu_j).
```

The ordinary sheaf condition would demand one and only one `mu_V` whose marginals are the `mu_i`. Probability data generally fail both parts:

- existence may fail on cyclic context families; and
- even when an extension exists, several global joint distributions may have the same local marginals.

Thus `Marg` must not be called a Grothendieck sheaf until the exact value objects, topology, existence rule, and uniqueness rule are proved. One defensible alternative is to store the set of all feasible global extensions rather than claim a unique distribution. Another is to select a canonical reconstruction by an explicit optimization rule, but then uniqueness belongs to that optimization theorem and its hypotheses, not to probability compatibility alone.

## 5. The finite marginal-feasibility certificate

For a frozen finite variable universe, global extension is an exact linear feasibility problem.

Enumerate the global assignments `omega in Omega`. Let `q_omega` be the proposed joint mass. Collect the registered local marginal entries into a vector `b`, and let `A` be the exact zero-one marginalization matrix. Feasibility is

```text
Aq = b,
q >= 0.
```

Normalization may be included as a row of `Aq=b`. The candidate evidence format has two legitimate outcomes.

### 5.1 Feasible outcome

Retain:

- the exact context schema and assignment ordering;
- the rational or precision-declared matrix `A` and local vector `b`;
- one nonnegative normalized joint table `q`;
- an independently recomputed residual `Aq-b`;
- the solver identity and settings; and
- a verifier result that checks normalization, nonnegativity, and every marginal equation.

This proves existence for those exact inputs. It does not prove uniqueness, semantic correctness of the contexts, causal structure, or predictive usefulness.

### 5.2 Infeasible outcome

For the standard Farkas alternative, retain a vector `y` satisfying

```text
A^T y >= 0,
b^T y < 0.
```

An independent verifier checks the inequalities under the declared exact or interval arithmetic profile. This is an auditable obstruction to a nonnegative `q` with `Aq=b`.

The current repository contains neither certificate type for AI data. Implementing the schema, exact arithmetic policy, solver-independent verifier, and adversarial fixtures remains open.

### 5.3 Approximate consistency is a different endpoint

Noisy measurements may motivate an optimization such as

```text
minimize ||W(Aq-b)||
subject to q >= 0 and sum(q)=1,
```

with a preregistered norm, weight matrix, tolerance, missing-data policy, and uncertainty procedure. A small residual is not a sheaf theorem. It is a profile-specific statistic and must be reported with its control distribution, uncertainty, and sensitivity to the context schema.

## 6. Acyclic extension is conditional, not automatic gluing

Classical marginal theory identifies regular or acyclic complexes on which every compatible family of measures is extendable [CIT-VOROBEV-1962]. Junction-tree methods provide closely related constructive factorizations in finite graphical models.

That background offers a valid research route:

1. define the exact finite assessment hypergraph;
2. prove its running-intersection or source-specific regularity property;
3. type every local distribution and separator marginal;
4. apply the exact extension theorem; and
5. retain a reconstruction and verification certificate.

Three caveats remain.

First, no current CAS context family has been proved acyclic or regular in the source theorem's sense. Second, an extension theorem establishes existence under its hypotheses, not automatically uniqueness among all global distributions. Third, choosing the maximum-entropy or graph-Markov extension introduces an additional model class and optimization rule. It must not be disguised as ordinary sheaf gluing.

## 7. Global-section obstructions and contextuality

Abramsky and Brandenburger use sheaf-theoretic global-section obstructions to organize nonlocal and contextual empirical models [CIT-ABRAMSKY-BRANDENBURGER-2011]. That work is directly relevant to the mathematical shape of local-versus-global probability data.

It does not license a transfer of quantum contextuality to AI. A Noetic assessment would need to define:

- the measurement labels and contexts;
- the event presheaf or probability object;
- the compatibility/no-disturbance assumptions;
- the global-section question;
- the coefficient or obstruction system, if cohomology is used; and
- a reduction showing that the AI data meet those definitions.

Without that bridge, “contextual” in this paper means context-indexed assessment, not a proved quantum, logical, or causal contextuality phenomenon.

## 8. A separate weighted cellular representation

Applied and spectral sheaf methods offer useful consistency tools when data are represented linearly [CIT-ROBINSON-2017; CIT-HANSEN-GHRIST-2019]. To use them here, one must construct a separate finite cell complex `X` and a cellular sheaf `F_lin` whose stalks are finite-dimensional real or complex vector spaces and whose face maps are linear.

Chosen inner products give adjoints. At degree zero the candidate consistency operator is

```text
L^0 = (delta^0)* delta^0.
```

In higher degrees the Hodge Laplacian includes both up and down terms. Its kernel, spectrum, heat flow, or residual interpretation depends on the exact sheaf, weights, and coefficient field.

A proposed conversion from probability data must declare, for example:

- whether a distribution is embedded as raw probabilities, logits, square roots, moments, or another chart;
- how normalization and zero probabilities are handled;
- which restriction maps become linear;
- whether the conversion is injective or information-losing;
- how uncertainty propagates; and
- whether the resulting residual has any statistical calibration.

No current artifact supplies this comparison functor. A Laplacian computed after an unregistered embedding cannot be reported as a property of the original Markov kernel or Grothendieck sheaf.

## 9. Proposed contextual AI assessment protocol

The architecture becomes an empirical method only through a preregistered protocol. The present section specifies a candidate protocol; it reports no result.

### 9.1 Frozen experimental unit

Every run should bind:

- model provider, model identifier, architecture and weights digest when available;
- tokenizer and prompt-rendering identity;
- layer, token position, hook, and intervention identity;
- dataset and split digests;
- context-category version and exact cover/hypergraph;
- variable alphabets and assignment ordering;
- kernel, channel, marginalization, and conversion schema versions;
- random seeds and solver profiles; and
- code, dependency, and environment identities.

An unavailable identity is a stated limitation, not a blank field.

### 9.2 Primary endpoints

Candidate primary endpoints are deliberately structural:

1. exact global-feasibility rate over held-out groups;
2. preregistered approximate-consistency residual when exact feasibility fails;
3. stability of the result under repeated seeds and sampling;
4. difference from matched control context systems; and
5. independent verification rate for retained certificates.

Predicting a behavior label may be a secondary endpoint. It does not by itself establish that the representation implements the Noetic ontology.

### 9.3 Required controls

At minimum, the protocol should compare against:

- label-shuffled contexts;
- size- and overlap-matched random context hypergraphs;
- matched alternative taxonomies;
- wrong-layer and wrong-token measurements;
- random or norm-matched intervention directions when interventions are used;
- prompt-group permutations that preserve marginal counts;
- a known infeasible marginal fixture;
- a known feasible but nonunique fixture; and
- an acyclic positive-control fixture with a retained extension.

Probe controls are necessary because a flexible readout can learn the task rather than reveal a property of the representation [CIT-HEWITT-LIANG-2019]. Controls must be evaluated with the same data budget and selection process as the target analysis.

### 9.4 Statistical plan

Before execution, register:

- the unit of analysis and dependence structure;
- the train/calibration/validation split;
- primary and secondary endpoints;
- multiplicity correction;
- uncertainty intervals or randomization tests;
- handling of missing or invalid measurements;
- exclusion rules;
- exact-versus-approximate tolerance; and
- the falsification threshold.

Results should be stratified by model, architecture, context family, and time. Pooling across incompatible profiles is prohibited.

### 9.5 Falsifiers

The research hypothesis is weakened or rejected if any of the following occurs:

- target coherence does not exceed matched controls;
- results reverse under held-out replication;
- certificate verification fails;
- the effect is driven by one model, layer, prompt family, or solver tolerance;
- random context systems perform equally well or better;
- the context labels cannot be operationalized independently of the model outputs; or
- the proposed conversion loses the information needed for its interpretation.

A negative result remains a versioned result.

## 10. Evidence Packet boundary

Paper 4 depends eventually on CAS Harness 2, but no current Gate 5 artifact supplies an admitted Paper 4 experiment. A future packet must distinguish:

- raw measurement bytes;
- typed normalized observations;
- context and cover identities;
- solver inputs and outputs;
- independent certificate-verifier output;
- control results;
- statistical analysis;
- claim record and allowed wording; and
- review and disclosure state.

The packet must not be self-authorizing. A valid hash proves byte identity, not scientific validity. The exact model runner, replication, WORM/retention policy, and independent review gates remain outside this draft and open.

## 11. Relationship to Papers 2 and 5

Paper 2 provides a sixteen-context Set-valued reference model with transverse coverages and external provenance records. Its atomic join yields four independent channels. Paper 4 may reuse its software patterns for exact context identity and derivation tracking, but it may not infer probability gluing or empirical meaning from Paper 2's Set-valued theorems.

Paper 5 is reserved for ACBE as Approximate Causal Abstraction. Paper 4 makes no causal-abstraction claim. Markov composition expresses stochastic information flow; it does not identify causal direction. A global distribution, unique optimizer, low residual, or naturality square does not substitute for interventions and a causal comparison theorem.

## 12. Related literature and the proposed comparison program

The literature separates into four bodies:

1. categorical probability and Markov categories [CIT-GIRY-1982; CIT-FRITZ-2020];
2. probability sheaves and their emerging Markov-category bridge [CIT-SIMPSON-2017; CIT-STEIN-2025];
3. marginal extension and global-section obstruction theory [CIT-VOROBEV-1962; CIT-ABRAMSKY-BRANDENBURGER-2011]; and
4. applied and weighted cellular sheaves [CIT-ROBINSON-2017; CIT-HANSEN-GHRIST-2019].

The first formal literature task is not to rename these constructions. It is to build a comparison matrix:

| Question | Required result |
|---|---|
| Does the Noetic context category satisfy a probability-sheaf site axiom? | Typed proof or counterexample |
| Does a chosen Markov category induce the proposed context category? | Explicit functor and hypothesis audit |
| Are local distributions objects, sections, or morphisms in the chosen construction? | One unambiguous typing |
| Is gluing existence-only, unique, set-valued, or optimizer-selected? | Exact descent or reconstruction theorem |
| Does the linear cellular representation preserve stochastic information? | Comparison functor with loss/nonloss statement |
| What is Project Coherence-specific? | Dedicated novelty and prior-art review |

Until this matrix closes, “Noetic Markov Sheaves” remains a working program label.

## 13. Implementation and proof plan

The shortest defensible implementation sequence is:

1. freeze a small synthetic context schema with feasible, infeasible, and nonunique fixtures;
2. implement exact context, distribution, marginalization, kernel, channel, and conversion types;
3. verify presheaf identity and composition laws;
4. implement rational finite-feasibility and dual-certificate verification;
5. test the anticorrelation obstruction and acyclic positive controls;
6. define one optional linear cellular representation and document its information loss;
7. build adversarial tests preventing cross-type substitution;
8. perform the Simpson/Fritz/Stein comparison and novelty audit;
9. integrate with the joined runner only after its Gate 5 evidence path is admitted; and
10. preregister and execute a held-out study with independent replication.

No GPU resource is required for steps 1 through 8. Model-scale experiments begin only after the runner, budget, stop conditions, and claim record are frozen.

## 14. Open obligations before submission

This paper remains open until all of the following are present:

1. an exact definition of “Noetic Markov sheaf” or a title revision that avoids claiming a sheaf;
2. a proof-level comparison with Simpson 2017 and Stein 2025;
3. a complete novelty search and citation review;
4. a typed finite implementation and exact-schema artifacts;
5. presheaf-law, marginal-feasibility, dual-certificate, and negative-fixture tests;
6. a theorem specifying the exact acyclic extension profile, if used;
7. a proof or explicit rejection of unique gluing for the chosen value objects;
8. an explicit comparison to any linear cellular representation;
9. a preregistered empirical protocol and power or sensitivity analysis;
10. qualifying Evidence Packets and independent replication;
11. external review in category theory, probability, applied sheaf theory, and ML evaluation;
12. authorship, disclosure, IP, and licensing decisions; and
13. lead-agent reconciliation with shared notation and claim registries.

## 15. Conclusion

The viable core of Noetic Markov Sheaves is not an assertion that local probability data glue. It is a fail-closed architecture for asking whether they do, at which type, under which hypotheses, with what certificate, and relative to which controls.

The architecture separates deterministic dynamics, stochastic kernels, induced channels, marginal presheaves, Grothendieck sheaves, and weighted cellular sheaves. It makes exact feasibility and obstruction evidence first-class and treats approximate residuals as statistics rather than theorems. It also places the work honestly within existing probability-sheaf and Markov-category literature.

At present this is a substantial methods draft, not an empirical paper. No result licenses a claim about cognition, alignment, safety, causal abstraction, or product performance. Those boundaries remain visible so that future experiments can add evidence without rewriting the mathematics after the fact.

## References

- `[CIT-GIRY-1982]` M. Giry, “A categorical approach to probability theory.” DOI: <https://doi.org/10.1007/BFb0092872>
- `[CIT-FRITZ-2020]` T. Fritz, “A synthetic approach to Markov kernels, conditional independence and theorems on sufficient statistics.” DOI: <https://doi.org/10.1016/j.aim.2020.107239>
- `[CIT-SIMPSON-2017]` A. Simpson, “Probability Sheaves and the Giry Monad.” DOI: <https://doi.org/10.4230/LIPIcs.CALCO.2017.1>
- `[CIT-STEIN-2025]` D. Stein, “Random Variables, Conditional Independence and Categories of Abstract Sample Spaces,” arXiv:2503.02477v2. <https://arxiv.org/abs/2503.02477>
- `[CIT-VOROBEV-1962]` N. N. Vorob'ev, “Consistent Families of Measures and Their Extensions.” DOI: <https://doi.org/10.1137/1107014>
- `[CIT-ABRAMSKY-BRANDENBURGER-2011]` S. Abramsky and A. Brandenburger, “The Sheaf-Theoretic Structure of Non-Locality and Contextuality.” DOI: <https://doi.org/10.1088/1367-2630/13/11/113036>
- `[CIT-HANSEN-GHRIST-2019]` J. Hansen and R. Ghrist, “Toward a spectral theory of cellular sheaves.” DOI: <https://doi.org/10.1007/s41468-019-00038-7>
- `[CIT-ROBINSON-2017]` M. Robinson, “Sheaves are the canonical data structure for sensor integration.” DOI: <https://doi.org/10.1016/j.inffus.2016.12.002>
- `[CIT-HEWITT-LIANG-2019]` J. Hewitt and P. Liang, “Designing and Interpreting Probes with Control Tasks.” DOI: <https://doi.org/10.18653/v1/D19-1275>

Full bibliographic metadata, source URLs, verification dates, and use boundaries are recorded in `CITATION_LEDGER_v0.1.json`.
