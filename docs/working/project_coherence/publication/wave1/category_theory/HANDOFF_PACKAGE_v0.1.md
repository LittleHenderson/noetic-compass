# Wave 1 category and sheaf theory handoff package v0.1

Status: `DRAFT / OPEN / RING 4 / NOT LICENSED / HELD`
Lane: `Category and Sheaf Theory`
Publication base: `a1cd990109e7561dfd03949bf0e1653461c7ae44`
Branch: `codex/project-coherence-publication-category`
As of: 2026-08-05

## 1. Handoff purpose

This package gives the Project Coherence lead a source-bound publication delta for charter Papers 2 and 4. It does not alter the existing Gate 0-5 specifications, canonical authority matrix, symbol registry, theorem ledger, claim ledger, production TODO, or any other worktree.

The lane commit is reported out-of-band with the Git handoff rather than embedded here, avoiding a self-referential commit identity. The non-self-hashing artifact manifest binds every lane deliverable except itself.

## 2. Deliverables

| Artifact | Purpose |
|---|---|
| `SOURCE_BOUND_INVENTORY_v0.1.json` | Exact base-commit source paths, byte sizes, SHA-256 digests, and local reproduction snapshot |
| `PAPER_2_THE_MARKED_AND_MODAL_NOETIC_TOPOS_DRAFT_v0.1.md` | Source-bound Paper 2 research draft |
| `PAPER_4_NOETIC_MARKOV_SHEAVES_FOR_CONTEXTUAL_AI_ASSESSMENT_DRAFT_v0.1.md` | Source-bound Paper 4 methods and type-architecture draft |
| `THEOREM_AND_CLAIM_MATRIX_v0.1.json` | Publication statements mapped to governing records, evidence status, allowed wording, and prohibited wording |
| `EVIDENCE_MAP_v0.1.json` | Claim-to-source, proof, execution, literature, and missing-evidence map |
| `CITATION_LEDGER_v0.1.json` | Primary technical sources with exact DOI/URL and transfer boundaries |
| `UNRESOLVED_OBLIGATIONS_v0.1.json` | Twenty-three open proof, implementation, experiment, review, and governance obligations |
| `PUBLICATION_ARTIFACT_MANIFEST_v0.1.json` | SHA-256/byte manifest for the preceding seven artifacts plus this handoff; intentionally excludes itself |

## 3. Narrow results carried forward

The package carries forward, without promotion, the following existing internal results:

1. Under the conservative source axioms, ACBE reflexivity and the RPM split epimorphism force maximal sieves, so the labeled clauses add no nonmaximal coverage beyond the jointly-surjective topology.
2. The legacy axioms do not imply subcanonicity; use `a_J(yX)` unless an exact revised site is proved subcanonical.
3. On the finite context factor `L=P({0,1}x{0,1})`, the transverse cover bases generate distinct subcanonical topologies with explicit witness presheaves.
4. Their join is the atomic four-singleton topology.
5. On `PSh(L,Set)`, the two explicit reflectors commute up to a unit-compatible canonical natural isomorphism:

   ```text
   M_A M_R ~= M_atom ~= M_R M_A.
   ```

6. The modalities are distinct and nonidentity in the ambient finite presheaf category, but restrict to identity up to their canonical reflector isomorphisms on the resolved subcategory.

All remain internal candidates subject to formalization and independent review.

## 4. Corrections the lead must preserve

The integration must not reintroduce any of the following errors:

- describing the legacy ACBE/RPM cover clauses as independently nontrivial;
- claiming finite-modal noncommutation;
- extending the finite composition theorem to `PSh(C x L)` or `J_obs`;
- describing a bare legacy representable as a sheaf without subcanonicity;
- calling the external provenance record an internal topos object;
- treating four atomic channels as cross-context coupling;
- inferring probability gluing from Set-valued gluing;
- identifying deterministic maps, Markov kernels, affine channels, Grothendieck sheaves, and weighted cellular sheaves;
- defining a cellular Laplacian without finite-dimensional linear stalks and inner products;
- claiming “Noetic Markov Sheaves” is novel over probability-sheaf and Markov-category literature; or
- writing an empirical, causal, safety, alignment, scientific, product, canon, disclosure, or licensing claim as established.

## 5. Dependency handoff

### Paper 2 dependencies

Paper 2 can enter internal cross-review now. It cannot enter submission editing until the finite proof formalization, product-site construction, observational interaction, backward comparison, cross-context semantic decision, novelty review, and independent category-theory review are complete.

### Paper 4 dependencies

Paper 4 is a methods draft. Its next dependency-ordered sequence is:

```text
exact object definition
  -> probability-sheaf comparison
  -> finite context/type schemas
  -> presheaf and certificate implementation
  -> adversarial synthetic fixtures
  -> preregistration
  -> admitted Gate 5 runner and Evidence Packets
  -> independent replication
```

ACBE causal-abstraction claims belong to charter Paper 5 and remain outside this lane.

## 6. Reproduction evidence

The following were rerun in the dedicated worktree on the publication base:

| Check | Result | Boundary |
|---|---|---|
| Finite Noetic Topos 2 tests | `PASS / 8` | Sixteen-context reference model only |
| Modality composition verifier | `PASS / 18 fixtures / 298 sieves / 3012 restriction squares` | `PSh(L,Set)` only |
| Modality composition tests | `PASS / 6` | Finite executable fixtures only |
| Pinned Gate 1 Lean verifier | `PASS / Lean 4.32.1 / 16 axiom audits` | Bounded modules; full presheaf/topos proof open |

These are local reproduction results, not external replication.

## 7. Citation handoff

The ledger adds primary sources for:

- site-to-topology generation, sheafification, and subcanonicity;
- Markov categories and the Giry monad;
- probability sheaves;
- the emerging Markov-category/probability-sheaf bridge;
- marginal extension and contextual global-section obstructions;
- weighted cellular sheaves and applied sheaf consistency; and
- controls for representation probes.

The most important novelty correction is direct prior art: Simpson 2017 already defines probability sheaves, and Stein 2025 explicitly connects suitable Markov categories to probability sheaves. The latter is recorded as an arXiv preprint whose peer-review status was not established. A dedicated comparison is blocking.

## 8. Cross-review checklist

The formal-math reviewer should check:

- the legacy maximal-sieve arguments and injection-category countermodel;
- every finite reflector formula and null-cover case;
- naturality, unit compatibility, and strict-equality disclaimers; and
- the Farkas certificate orientation in Paper 4.

The engineering reviewer should check:

- whether proposed schemas can fail closed across the six types;
- exact arithmetic and independent certificate verification feasibility;
- source/model/context/run identity requirements; and
- that no methods claim assumes current Harness execution.

The lead should check:

- notation against shared registries without editing them implicitly;
- paper numbering and charter scope;
- overlap with Papers 1, 3, 5, 6, and 7;
- authorship and citation ownership;
- all `OPEN / NOT LICENSED / HELD` wording; and
- whether the Paper 4 title should remain or be narrowed after the prior-art comparison.

## 9. Integration instructions

1. Review or cherry-pick only the dedicated category-lane commit.
2. Do not copy files from the moving Gate 5 worktree into this lane.
3. Run JSON parsing, local-link checks, status-boundary searches, and the four registered reproduction commands.
4. Reconcile notation in a lead-owned integration change; this lane intentionally does not edit shared registries.
5. Record internal cross-review as internal review. Do not describe it as external or independent peer review.
6. Keep every residual obligation open unless its acceptance evidence is present and reviewed.

## 10. Residual state

The package contains 23 open obligations and closes none. Cross-review is `OPEN`. External review is `OPEN`. Gate 1, Gate 3, and Gate 5 remain open under their governing artifacts. No publication, canon, scientific, product, disclosure, or license state changes as a result of this handoff.
