# Paper 5 ACBE-P5 lead handoff

Status: `DRAFT / SOURCE-BOUND DELTA / OPEN CAUSAL TRANSFER / RING 4 / NOT LICENSED / HELD`

Base: `143cff40f94cf207a9130d6a7c07975a1fcbf0b9`

## Integration outcome

This package turns charter Paper 5 into a substantial, reviewable methods draft
without claiming that an experiment has run. It supplies:

- a typed interventional response profile;
- a state/context/intervention abstraction candidate;
- an intervention-indexed commutation defect;
- worst-case, weighted, tail, coverage, transfer, specificity, and non-vacuity
  estimands;
- four bounded proposition candidates with proof sketches;
- explicit observational, constant-map, intervention-collision, and
  average-masking failure modes;
- causal-identifiability classes and necessary assumptions;
- a full negative-control suite;
- a preregistration and Evidence Packet v2 contract; and
- a narrow first joined-run design, explicitly unexecuted.

No shared registry, Gate file, Wave 1 package, source document, or production
TODO was changed.

## Lead decision required: naming

The registered legacy source creates a hard boundary. Its line 163 says ACBE is
only a name for the preorder `A >= B >= C >= D`; it supplies no acronym
expansion or causal meaning. Noetic Topos 2.0 also uses ACBE as a formal
coordinate-partition mark without empirical interpretation.

Recommended integration decision:

| Token | Keep as |
|---|---|
| `ACBE_legacy` | source-bound legacy preorder/descent label |
| `ACBE_NT2` | successor marked-context provenance label |
| `ACBE-P5` | Paper 5 publication-program identifier |
| `ACA` | new mathematical approximate-causal-abstraction relation |

The display title may remain “ACBE-P5: Approximate Causal Abstraction,” but the
lead should not register “ACBE” itself as an alias for `ACA`. An authorized
registry delta is required later; this lane intentionally does not make it.

## Mathematical core for formal review

The proposed profile is

\[
\mathcal M=(C,X,I,K), \qquad K:C\times I\rightsquigarrow X,
\]

and the candidate comparison is

\[
\mathcal A=(\tau,\kappa,\omega,E,d,\mu).
\]

Its case-level defect is

\[
\delta(c,i)=d\bigl(\tau_*K_L(\cdot\mid c,i),
K_H(\cdot\mid\kappa(c),\omega(i))\bigr).
\]

The matrix contains four reviewable proposition candidates:

1. `P5-PROP-001`: zero defect is exact commutation on the declared domain;
2. `P5-PROP-002`: compatible total-variation defects compose with an additive
   upper bound;
3. `P5-PROP-003`: bounded high-level estimands inherit the total-variation
   bound; and
4. `P5-PROP-004`: merging two separated intervention responses forces at least
   one defect of half their separation.

All are proof-sketch candidates, not promoted theorems. They need independent
probability/causal-abstraction review and preferably a finite formal artifact.

## Non-negotiable claim boundaries

Preserve these statements verbatim in substance during integration:

- legacy ACBE, Noetic Topos 2.0 marks, and ACA are different types;
- a causal representation learner can propose `tau` but does not certify ACA;
- an intervention is a declared mechanism-changing operator, not any prompt
  edit, observation, correlation, or distribution shift;
- a Markov kernel becomes part of a causal profile only under independently
  supplied intervention semantics;
- correlation, sheaf compatibility, global gluing, naturality, and a low
  residual do not identify ACA;
- low defect alone is vulnerable to constant-map trivialization;
- average defect alone can hide a worst-case intervention failure;
- every empirical estimand receives a causal-identifiability status before
  estimation language is permitted; and
- no causal claim is available without qualifying joined-run evidence.

## First empirical candidate

`P5-HYP-001` proposes one narrow, non-safety, synthetic algorithmic task using
an exact open-weight model revision, a finite high-level causal program, frozen
neural/high-level alignment, paired interchange interventions, disjoint
confirmatory and replication groups, and case-level defect reporting.

Before execution, the lead must route the following dependency chain:

1. approve the naming decision;
2. freeze the causal models, maps, metric, tolerances, non-vacuity gates, and
   controls;
3. obtain a causal-identification review and statistical power plan;
4. add one exact empirical claim through the authorized canonical registry
   process;
5. implement the ACA module in the joined Harness v2 runner;
6. close authentication, hermetic execution, durable ordering, and raw-evidence
   retention gaps;
7. freeze a strict per-claim preregistration;
8. execute within the protected window;
9. obtain independent numerical and semantic audit; and
10. complete held-out replication and external causal-methods review.

Missing or negative cases must remain in the Evidence Packet. A packet hash is
not a signature, scientific conclusion, license, or product verdict.

## RunPod and budget boundary

No RunPod funding is needed to integrate or review this paper package. The
current $57 balance cannot yet be judged sufficient for the future experiment,
because no exact model, GPU class, sample count, runtime, retry allowance, or
replication multiplier is frozen. `P5-OBL-020` blocks paid execution until a
costed plan and hard spend cap are bound to the preregistration. The lead should
not request more funding or launch a run from this draft alone.

## Suggested integration order

1. Review `P5-NAME-001` and decide the registry notation.
2. Send Propositions 6.1-6.4 and Counterexamples 7.1-7.3 to an independent
   formal/causal reviewer.
3. Reconcile citation IDs with the lead's publication-wide ledger without
   erasing source-specific boundaries.
4. Add candidate claim and symbol records only through an explicit shared-
   registry integration commit.
5. Keep the empirical lane `OPEN / NOT_EXECUTED` until a qualifying joined-run
   Evidence Packet exists.

## Package map

| Artifact | Purpose |
|---|---|
| `PAPER_5_ACBE_AS_APPROXIMATE_CAUSAL_ABSTRACTION_DRAFT_v0.1.md` | Substantial Paper 5 methods draft |
| `THEOREM_CLAIM_AND_CAUSAL_IDENTIFIABILITY_MATRIX_v0.1.json` | Exact statements, assumptions, identification states, and language ceilings |
| `EVIDENCE_MAP_v0.1.json` | Evidence-type and non-inference map |
| `CITATION_LEDGER_v0.1.json` | Primary technical sources with use boundaries |
| `UNRESOLVED_OBLIGATIONS_v0.1.json` | Twenty-one fail-closed obligations |
| `SOURCE_BOUND_INVENTORY_v0.1.json` | Hash-identified repository inputs |
| `PUBLICATION_ARTIFACT_MANIFEST_v0.1.json` | Non-self-hashing package manifest |

## Current ceiling

The package supports definitions, bounded proof sketches, explicit
counterexamples, an identification framework, and an experimental protocol. It
does not support an empirical causal result, a safety claim, a product claim,
canon promotion, licensing, public disclosure, or publication submission.

## Verification receipt

The source-bound delta passed:

- JSON parsing, declared-count checks, citation/dependency cross-reference
  checks, and all 15 repository-source hash/byte checks;
- `verify_project_coherence_phase0.py`;
- `verify_project_coherence_gate1.py`; and
- `verify_project_coherence_gate5.py` after clearing only verifier-generated
  Python caches from the isolated worktree.

The Gate 5 receipt still reports experimental execution `NOT_STARTED` and Gate
5 `OPEN / RING 4 / NOT LICENSED / HELD / NOT FROZEN`. Its PASS is a repository
control receipt, not an ACA experiment or causal conclusion.
