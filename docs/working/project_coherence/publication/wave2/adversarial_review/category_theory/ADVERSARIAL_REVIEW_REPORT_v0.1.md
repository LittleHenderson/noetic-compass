# Category and sheaf theory adversarial cross-review v0.1

Status: `DRAFT / OPEN / RING 4 / NOT LICENSED / HELD`

Review class: `INTERNAL CROSS-REVIEW INDEPENDENT OF THE AUTHORING LANE / NOT EXTERNAL PEER REVIEW`

Reviewed lane commit: `643169e9bd8de6d4bd0cc2cbc3cde4e640f1671c`

Underlying publication base: `a1cd990109e7561dfd03949bf0e1653461c7ae44`

Review branch: `codex/project-coherence-review-category`

As of: 2026-08-05

## 1. Disposition

The category lane is viable as a source-bound internal research package, but it is not ready for submission editing. The central finite-context result survives this review in its exact scope:

```text
PSh(L,Set) only,
L = P({0,1} x {0,1}),
M_A M_R ~= M_singleton ~= M_R M_A,
natural isomorphism rather than strict equality.
```

The legacy maximal-sieve correction, finite subcanonicity result, distinct finite witness presheaves, joined singleton-partition topology, reflector universal property, and probability non-gluing counterexample also survive within their declared finite or source-bound scopes. Nothing in this review promotes those statements beyond `DRAFT / OPEN / Ring 4 / NOT LICENSED / HELD`.

Three defects block submission editing:

1. **The ambient external-product witness is false as written.** In general, `yC_0 \boxtimes F_A` is not a `J_A`-sheaf because the null cover at `(c,empty)` requires a singleton value, while its value is `Hom_C(c,C_0) x F_A(empty) ~= Hom_C(c,C_0)`. Replace the representable factor with the terminal presheaf on `C`, after explicitly defining the lifted product-site topology and assuming `C` is nonempty, or leave ambient distinctness open.
2. **Finite dimensionality is stated as a universal prerequisite for a cellular Laplacian.** It is a valid requirement for the proposed finite-matrix certificate profile, not for cellular Laplacians in general. Bounded Hilbert-valued cellular sheaves can have well-defined Laplacians in infinite dimension. Paper 4, `PUB-P4-005`, and the citation use boundary must be narrowed.
3. **The evidence graph misbinds the joined-topology claim.** `PUB-P2-007` is attached to the finite-site and Lean seed nodes, while its actual proof and 298-sieve execution live in the modality-composition proof and certificate nodes. The Lean seed explicitly does not formalize topology generation or reflectors. Rewire that edge and avoid presenting the Lean seed as evidence for claims it does not cover.

Required wording and citation changes that do not overturn the scoped finite theorem are listed in `UNRESOLVED_REQUIRED_CHANGES_v0.1.json`.

## 2. Review boundary

This review examined the completed Wave 1 category package without changing it. It did not:

- edit a governing theorem, claim, symbol, migration, or obligation registry;
- close any Wave 1 or Project Coherence gate;
- establish the product-site lift, observational interaction, legacy equivalence, or serialization round trip;
- define a Noetic Markov sheaf;
- implement a marginal-feasibility certificate or linear cellular conversion;
- run an AI experiment or inspect a qualifying Evidence Packet;
- perform an IP, authorship, disclosure, or license decision; or
- constitute external specialist or peer review.

The review outcomes mean only `survives this bounded internal adversarial check`, `requires correction`, or `remains open`. They are not theorem admissions.

## 3. Frozen input binding

The review began on a clean worktree at exact category commit `643169e9bd8de6d4bd0cc2cbc3cde4e640f1671c`. The commit adds only the nine Wave 1 category artifacts. SHA-256 and byte counts were recalculated independently.

| Wave 1 artifact | Bytes | SHA-256 | Result |
|---|---:|---|---|
| `CITATION_LEDGER_v0.1.json` | 10,320 | `F83B4A5BB6DD43265C5879E7487E2147BF4249A7AE042AC378F4D9CFF927EB40` | MATCH |
| `EVIDENCE_MAP_v0.1.json` | 10,623 | `702978615AF4F25497F4B976CE9636F269157DBE1CEBC68998E8B018908942BD` | MATCH |
| `HANDOFF_PACKAGE_v0.1.md` | 7,993 | `1C0DADCD55E1588E4496187E61A44734B1E12FBECC8BA42C4E70AD68E87A51B9` | MATCH |
| `PAPER_2_THE_MARKED_AND_MODAL_NOETIC_TOPOS_DRAFT_v0.1.md` | 23,431 | `AEEB4C5E5C04E616151D83FBA6816BA217A51B7368FA2894FE0AD2E897B4BC24` | MATCH |
| `PAPER_4_NOETIC_MARKOV_SHEAVES_FOR_CONTEXTUAL_AI_ASSESSMENT_DRAFT_v0.1.md` | 26,028 | `19FEB7E0B923EF5FE8A34435E2F65AF4887ABA0B1375A2DD847F627936E67967` | MATCH |
| `PUBLICATION_ARTIFACT_MANIFEST_v0.1.json` | 3,317 | `6982A8D7F54605C8758C1E7C1E08FA846E85CF5AE46EEC4B4361D90EE3A0B26F` | MATCH / intentionally self-excluded from its own manifest |
| `SOURCE_BOUND_INVENTORY_v0.1.json` | 8,929 | `8D0B39AE52E4084B7ED73C543D9D56E7FE6D09BC3F9A40CCA0D53BBC98436EE4` | MATCH |
| `THEOREM_AND_CLAIM_MATRIX_v0.1.json` | 17,159 | `E1A795B0C1A3BB3CBDC95CC9C6D59BEF8281075F79C532811B2AF85892D51034` | MATCH |
| `UNRESOLVED_OBLIGATIONS_v0.1.json` | 10,897 | `63E01CEA477AE90208095279124682B0FF1926C098C91BA712E7DF4CDCC534B3` | MATCH |

All 26 source records in `SOURCE_BOUND_INVENTORY_v0.1.json` were re-read as exact blobs from base commit `a1cd990109e7561dfd03949bf0e1653461c7ae44`; byte count and SHA-256 mismatches were zero.

The two direct legacy source identities were also checked independently:

| Source | Exact SHA-256 | Result |
|---|---|---|
| `peer_review/journal_submission/main.tex` raw bytes | `E9885F27581626CCF26AC4809F446AB5044BC92C61923B951B7F4686591BAEF8` | MATCH |
| Same TeX after registered LF normalization | `CEE0A4AB335DDAA2BDD4A56030E5B2A7FA0FA350054B1E57278AEC0AE554B0A6` | MATCH |
| `noetic-topos (1).pdf` local frozen rendering | `35772DBA830F0C5ABD63B8316A2750497224731B5CBADF94BA9F59072C178448` | MATCH / portable bundle still OPEN |

The TeX locations recorded for ACBE reflexivity, the RPM section-retraction, and coverage reduction were present at the registered lines. Hash identity confirms bytes and locations, not mathematical validity.

## 4. Reproduction results

The four registered checks were rerun from the reviewed commit:

| Check | Reproduced result | Scope boundary |
|---|---|---|
| Finite Noetic Topos 2 tests | `PASS / 8 tests` | Sixteen-context finite reference model only |
| Modality composition verifier | `PASS / 18 fixtures / 298 sieves / 3,012 restriction squares` | `PSh(L,Set)` only |
| Modality composition unit tests | `PASS / 6 tests` | Executable finite fixtures only |
| Pinned Gate 1 Lean verifier | `PASS / Lean 4.32.1 / 16 axiom audits` | Bounded registered modules; no topology or reflector formalization |

The modality verifier also reproduced 81 inclusion arrows, 168 covering sieves in both the joined and singleton-partition presentations, 486 nested sections, and 388 unit components. These executions corroborate a finite proof candidate; they do not substitute for proof-assistant formalization or external review.

## 5. Mathematical audit

### 5.1 Legacy corrections

The maximal-sieve arguments are type-correct under the registered source:

- Noe-Cov-2 contains the reflexive descent arrow `id_X`, so any such sieve is maximal.
- Noe-Cov-3 contains `epsilon_X`; because `epsilon_X eta_X = id_X` and a sieve is closed under precomposition, it contains `id_X` and is maximal.
- The finite-injection countermodel correctly shows non-derivability of legacy subcanonicity without asserting universal non-subcanonicity.

These results remain source-bound because the underlying conservative source and its axioms remain the premises.

### 5.2 Finite context topology and reflectors

The direct reflector formula survives review. The null cover forces `(R_P F)(empty)=1`; for nonempty `V`, a partition cover has independent nonempty pieces whose overlaps are empty, and the target sheaf's empty value is terminal. The proposed factorization through the unit is natural and unique by gluing. Expanding the transverse partitions yields one factor `F({omega})` per atom, and flattening/regrouping is natural in both `V` and `F` and respects the units.

The notation `J_atom` is locally defined but risks collision with the standard category-theoretic atomic topology, normally described using nonempty sieves under an Ore condition. The reviewed verifier reports only 168 of 298 sieves covering, so this is not a license to call the construction the standard atomic topology. Prefer `J_singleton`, `J_Q`, or the explicit phrase `topology generated by the singleton partition`.

### 5.3 Ambient product-site witness

The finite witness does not lift by arbitrary external product with a representable. Let

```text
H(c,V) = yC_0(c) x F_A(V).
```

At the empty context,

```text
H(c,empty) ~= Hom_C(c,C_0).
```

The null-cover sheaf condition demands that this set be a singleton for every `c`. A general representable does not have that property. At a context meeting two partition blocks, the gluing map also repeats the `Hom_C(c,C_0)` coordinate and acts diagonally, so it is not generally surjective.

The likely repair is

```text
H(c,V) = 1_C(c) x F_A(V) ~= F_A(V),
```

using the terminal presheaf on a nonempty `C`. This preserves the finite witness objectwise. That repair must be stated only after the lifted `L`-coordinate covers on `C x L` are defined exactly; it does not prove composition with `J_obs`.

### 5.4 Probability and Markov typing

The three-variable perfect-anticorrelation obstruction is correct. The kernel restriction square is well typed when

```text
K_V : X_V ~> Y_V,
r^X : X_V ~> X_U,
r^Y : Y_V ~> Y_U,
K_U : X_U ~> Y_U.
```

The Farkas orientation is also correct: if `Aq=b`, `q>=0`, and `A^T y>=0`, then `b^T y=q^T A^T y>=0`; therefore `b^T y<0` excludes feasibility. Implementation, exact arithmetic, and a solver-independent fixture remain open as the draft says.

### 5.5 Cellular-sheaf boundary

The type separation between Set-valued Grothendieck sheaves, Markov kernels, and linear cellular sheaves is sound. The universal finite-dimensional requirement is not. For example, on a one-edge graph, assign the Hilbert space `ell^2` to both vertex stalks and the edge stalk, with bounded identity restriction maps. The coboundary

```text
delta(x_v,x_w) = x_w - x_v
```

is bounded, so `delta* delta` is a well-defined bounded Laplacian although the stalks are infinite-dimensional. Finite-dimensional real or complex stalks should be required only for the proposed finite matrix/certificate profile.

## 6. Citation audit summary

The thirteen recorded citations have identifiable primary or authoritative records and their basic metadata were corroborated. The following use-scope changes are required:

- Hansen and Ghrist explicitly discuss bounded infinite-dimensional Hilbert-valued Laplacians; their paper does not support finite dimensionality as a universal necessity.
- Vorob'ev's primary record supports the stated `regular`-complex extension theorem. The draft's additional `acyclic` and junction-tree wording needs an exact equivalence theorem or a separate primary citation.
- The standard Farkas alternative is used without a ledger entry; add an authoritative optimization reference if the certificate section remains in publication form.
- Hewitt and Liang support control-task methodology for representation probes, not a universal theorem about every AI assessment. The draft's proposed controls are defensible as protocol choices, but the transfer boundary must remain explicit.

The Stacks Project tags support the site-to-topology passage, sheafification universal property and exactness, and subcanonicity boundary. Simpson 2017 establishes probability sheaves and the Giry extension; Stein 2025 remains an arXiv v2 preprint whose direct conceptual overlap is correctly disclosed. A full novelty search and proof-level comparison remain open.

## 7. Evidence-map and registry audit

All 20 publication claim IDs appear exactly once in the evidence-map claim edges. All claim citation references resolve to the 13-entry citation ledger. All 27 governing-record references resolve to existing governing artifacts. The claim count is 20, the obligation count is 23, and every listed obligation remains `OPEN`.

The graph is nevertheless semantically inaccurate for `PUB-P2-007`: the modality proof and execution nodes, not the bounded Lean seed, carry the joined-topology evidence. This must be corrected before the evidence map is used for integration.

No state token in the reviewed lane licenses a promotion. The phrase `INTERNAL PROOF COMPLETE / REVIEW REQUIRED` remains a scoped authoring status, not canon admission or external acceptance.

## 8. Publication readiness

| Area | Internal draft viability | Submission readiness |
|---|---|---|
| Legacy coverage correction | Viable within exact source axioms | Blocked by formal and external review |
| Finite `L` site and reflectors | Viable; proof candidate and execution agree | Blocked by formalization and terminology cleanup |
| Ambient `C x L` modalities | Candidate only | Blocked; representable witness must be corrected and product topology typed |
| Backward comparison | Honest conjectural target | Blocked; no proof or round trip |
| Noetic Markov architecture | Viable methods outline | Blocked; named object, comparison, and implementation absent |
| Marginal certificates | Viable specification | Blocked; no schema, verifier, or Evidence Packet |
| Cellular linearization | Viable boundary after scope correction | Blocked; no conversion or tests |
| Empirical assessment | Properly nonclaimed | Blocked; no preregistration, experiment, or replication |

## 9. Required handoff

The lead may carry this lane into integration only with the following interpretation:

1. Preserve all `DRAFT / OPEN / Ring 4 / NOT LICENSED / HELD` states.
2. Do not rewrite or promote the finite theorem; correct the two overbroad interfaces around it.
3. Apply the evidence-edge correction before relying on the evidence map.
4. Keep product-site composition, observational interaction, backward compatibility, Noetic Markov sheaf definition, experiments, and external review open.
5. Treat this package as internal adversarial cross-review, not as closure of `OBL-P2-001`, `OBL-CAT-001`, or any external-review obligation. A lead-owned reconciliation can cite it as partial evidence for internal cross-review while retaining unresolved issues.

The exact review records are in:

- `CLAIM_BY_CLAIM_DISPOSITION_MATRIX_v0.1.json`;
- `CITATION_AUDIT_v0.1.json`;
- `MATH_TYPE_INTERFACE_COUNTEREXAMPLE_CHECKS_v0.1.md`; and
- `UNRESOLVED_REQUIRED_CHANGES_v0.1.json`.

`ADVERSARIAL_REVIEW_MANIFEST_v0.1.json` intentionally excludes itself and binds the other review files after final generation.
