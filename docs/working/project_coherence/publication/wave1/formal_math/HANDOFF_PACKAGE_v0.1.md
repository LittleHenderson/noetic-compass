# Project Coherence publication Wave 1 — formal-math handoff v0.1

Status: `DRAFT / OPEN / RING 4 / NOT LICENSED / HELD / NOT FROZEN`

Source baseline: `a1cd990109e7561dfd03949bf0e1653461c7ae44`

Lane branch: `codex/project-coherence-publication-formal`

## 1. What this lane produced

This handoff contains source-bound **publication deltas**, not replacement Gate
specifications and not new canonical registries:

1. `PAPER_1_TYPED_NOETIC_DYNAMICS_AND_FINITE_FRACTAL_SEMANTICS_DELTA_v0.1.md`
2. `PAPER_3_NOETIC_PROJECTION_GEOMETRY_AND_STATE_CAPACITY_DELTA_v0.1.md`
3. `THEOREM_AND_CLAIM_MATRIX_v0.1.json`
4. `EVIDENCE_MAP_v0.1.json`
5. `CITATION_LEDGER_v0.1.json`
6. `UNRESOLVED_OBLIGATIONS_v0.1.json`
7. `SOURCE_INVENTORY_v0.1.json`
8. this handoff; and
9. `ARTIFACT_MANIFEST_v0.1.json`, which binds the other lane artifacts and does
   not hash itself.

No Gate 0–5 specification, source artifact, shared theorem/claim/symbol/authority
registry, production TODO, product source, or other worktree was modified.

## 2. Source intake and verification

The source inventory hashes 42 repository dependencies and seven external
registered sources.  All seven external bytes matched the SHA-256 identities in
the source-authority matrix, including:

- the registered v7.4 text and rendering plus three correction overlays;
- the exact 249-page OpenAI technical manuscript; and
- the exact 743-page CAS PCBA engineering reference.

The existing integrated Gate 1 verifier was replayed from the baseline:

```text
Project Coherence integrated Gate 1 verification: PASS
  hash-bound top-level artifacts: 23
  subordinate verifier receipts: 6 / PASS
  Lean theorem audits: 16; scoped finite modality proof: PASS
  Gate 1 status: OPEN / Ring 4 / NOT LICENSED / NOT FROZEN
```

This is a scoped integrity/formal/executable receipt, not publication acceptance
or independent review.

## 3. Paper 1 delta

### Supported mathematical spine

Paper 1 organizes the existing candidate around the following type distinctions:

- a typed path in the category of named finite sets (or in a separately frozen finite semigroupoid) is different from a power of
  one endomap;
- a legacy digit string has no meaning without a versioned typed catalog;
- a deterministic standard-basis lift is different from a stochastic map,
  channel, unitary, partial isometry, or orthogonal projector;
- finite denotational closure is different from a terminating/confluent rewrite
  system; and
- finite set stabilization is different from a compact contractive metric IFS.

The exact finite lift norm is retained:

\[
\|A_f\|^2=\max_y|f^{-1}(y)|.
\]

The two-state constant map remains the permanent counterexample to the inherited
contraction/occupation/projector cluster.  “Finite fractal semantics” is defined
in two layers so that no metric-attractor conclusion can leak from symbolic
finite closure.

### Evidence boundary

Existing Lean code checks typed-category and lift fragments, not the universal
norm theorem, generic matrix/Gram/trace/rank bridge, factorial idempotence,
shortlex leastness, Python correspondence, or full TKS semantics.  The draft
uses those exact limits.

## 4. Paper 3 delta

### Preserved baseline

The CAS PCBA mixed-simplex/Fisher--Rao address remains the baseline.  A
rank-\(d\) orthogonal projector profile is an optional Ring-4 representation;
the paper asserts no identity, isomorphism, or validated equivalence between
the two types.

### Safe standard geometry

For common-rank projectors in one Hilbert space,

\[
k(i,j)=\operatorname{tr}(P_iP_j)/d
\]

is a normalized positive-semidefinite Hilbert--Schmidt kernel.  Principal angles
and chordal distance are stated at their standard types.  The delta supplies a
direct centered-projector simplex bound:

\[
\max_{i\ne j}k(i,j)\geq\frac{dN-D}{D(N-1)}.
\]

If \(\mu<d/D\) and every off-diagonal overlap is at most \(\mu\), the necessary
codebook envelope is

\[
N\leq\frac{D(1-\mu)}{d-D\mu}.
\]

A separate Welch feature-dimension check is included.  Both are standard
geometric necessary conditions and have no automatic cognitive, hardware, or
model-memory interpretation.

### Quarantined manuscript claim

The exact OpenAI manuscript Proposition 4.1 was transcribed with its missing
load-bearing hypothesis restored.  In addition to rank and code coherence, it
requires an isometry \(B:V\to W\otimes V\) satisfying

\[
B^*(\ell_x\otimes u)=\sqrt\Lambda u
\quad\text{for every }u\in\operatorname{im}P_x.
\]

Only under the complete hypotheses does the manuscript claim

\[
|C|\leq\frac{1-s}{\Lambda-s}\frac Dd.
\]

The record remains `MANUSCRIPT_CLAIM / PROOF_GAP`.  No CAS intertwiner exists,
and the weakened rank/coherence-only transfer is refuted by the retained
two-codeword example.  No experimental conclusion is present.

## 5. Citation and novelty controls

The citation ledger uses exact DOI or primary URLs.  It distinguishes:

- primary peer-reviewed standard background;
- direct CAS/TKS specializations;
- local direct proofs and counterexamples;
- scoped Lean fragments;
- the OpenAI technical manuscript whose peer-review status is unverified and for which no review receipt appears in the reviewed source set; and
- empirical hypotheses with no admitted experiment.

The standard sources do not validate CAS semantics.  The OpenAI manuscript does
not establish independent proof, novelty, peer review, named human authorship,
or admission.  Specialist citation/novelty review remains open.

## 6. Integration instructions for the lead

1. Treat the final lane commit reported out-of-band as one atomic publication
   delta.
2. Reconcile it onto the clean post-Gate-5 publication spine; this lane was
   intentionally based on `a1cd9901` while Gate 5 hardening continued elsewhere.
3. Recompute `SOURCE_INVENTORY_v0.1.json` after any rebase that changes a bound
   dependency.
4. Do not copy local publication records into shared registries until internal
   cross-review and external specialist review have resolved conflicts.
5. Preserve local IDs when commenting; if a shared registry record is later
   admitted, add an explicit mapping rather than silently replacing the local
   record.
6. Send Paper 1 to category/semigroup/dynamics and formal-methods reviewers.
7. Send Paper 3 to operator/coding theory, numerical linear algebra, and
   experimental-methods reviewers.
8. Keep both papers private and unsubmitted until the charter's theorem,
   evidence, authorship, disclosure, and citation conditions are met.

## 7. Cross-lane questions

The category/sheaf lane should review whether Paper 1's local “typed path”
vocabulary conflicts with Noetic Topos 2.0 path/morphism usage and whether any
future projector sheaf changes the scalar-kernel information-loss statement.

The engineering lane should review Paper 3's preservation of the mixed-simplex
address, identify the exact PCBA interface for an optional projector profile,
and reject any attempt to turn the mathematical codebook bound into board,
memory, latency, safety, or product capacity.

The publication lead should decide whether the phrase “finite fractal semantics”
survives specialist terminology review.  The mathematical content remains
usable if the phrase is replaced by “finite typed denotational dynamics.”

## 8. Blocking obligations

`UNRESOLVED_OBLIGATIONS_v0.1.json` contains 24 open items.  The principal
blockers are:

- incomplete v7.4 item-level migration and unresolved reference placeholders;
- universal formalization and Python/Lean correspondence gaps;
- no source-bound TKS semantic migration or full exact/approximate calculus;
- no independent verification of the manuscript capacity theorem;
- no CAS-specific intertwiner;
- no admitted projector estimator, experiment, or Evidence Packet;
- internal cross-lane and external specialist review still open;
- shared-registry reconciliation reserved for the lead/Integration Board; and
- authorship, disclosure, reproducibility, and submission authorization open.

The papers are therefore substantial research drafts, not submission-ready
manuscripts.  No GPU work is required to continue the mathematical and review
obligations.  A later authorized projector experiment may need GPU capacity,
but only after preregistration, exact hardware/runtime selection, a spend cap,
and stop conditions.
