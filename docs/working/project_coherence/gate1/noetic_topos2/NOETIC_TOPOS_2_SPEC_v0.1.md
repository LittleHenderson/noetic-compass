# Noetic Topos 2.0 formal research specification v0.1

Status: `DRAFT / GATE 1 RESEARCH CANDIDATE / NOT LICENSED`

Date: 2026-08-04

This document replaces no baseline. It gives the first conservative successor
construction that survives the Phase 0 collapse counterexample. All statements
remain Ring 4 until independent category-theory review, proof-assistant work,
and the Gate 1 integration decision are complete.

## 1. Defect being repaired

In the registered conservative paper, the ACBE cover clause includes
`id_X` by reflexivity. The RPM clause includes a split epimorphism
`epsilon_X` with section `eta_X`; sieve closure therefore also includes
`id_X`. Each clause alone generates only maximal sieves. With the observational
clause present, both reduce to the same jointly-surjective topology. The old
topos-existence theorem remains valid, but ACBE/RPM provenance and distinct
modalities are absent.

The successor must therefore change the cover generators. Renaming the old
maps is not a repair.

## 2. Typed successor data

Let `C` denote the registered legacy category `Noetica`, and let `J_legacy`
denote its proven jointly-surjective topology. No subcanonicity assumption is
added. A distinguished legacy object `X` is represented inside the legacy
sheaf topos by `a_legacy(yX)`, not by the bare site object or an unproved
representable sheaf.

Define the finite context lattice

```text
L = P(Omega),       Omega = {0,1} x {0,1},
U -> V              iff U is a subset of V.
```

The first coordinate is the formal ACBE mark and the second is the formal RPM
mark. These are structural labels only. They carry no empirical interpretation
until a separate operationalization and validation record exists.

For `V` in `L`, define two marked families:

```text
K_A(V) = { V intersect A_0 -> V, V intersect A_1 -> V }
K_R(V) = { V intersect R_0 -> V, V intersect R_1 -> V }

A_i = {(i,0),(i,1)}
R_j = {(0,j),(1,j)}.
```

The empty family covers the empty context. The successor architecture requires
cover records for `OBSERVATIONAL`, `ACBE`, and `RPM`, with a source reference
and the exact typed member arrows. The v0.1 executable schema is deliberately
narrower: it represents ACBE/RPM context-factor families and their joint
refinement only. Typed observational covers in the legacy `C` coordinate and
full product-site arrows remain `OPEN`. The ordinary Grothendieck topology
intentionally forgets a tag after generation; the parallel provenance record
must not.

The executable reference model enforces that separation with an immutable
`MarkedCover`. Its canonical JSON and SHA-256 bind the target, members, mark,
and a sorted set of parent-cover digests. Pullback creates a new record whose
provenance chain contains its parent digest. The ACBE/RPM common refinement is
a derivation node with both generating-cover digests as parents. This matters
at singleton contexts, where the bare ACBE and RPM families coincide but their
marked records and digests remain distinct. Unknown or duplicate JSON keys and
uncontrolled review states are rejected. The topology consumes the unmarked
family; audit and migration code must consume the marked record. An enclosing
Evidence Packet must separately bind the raw ingress bytes; the cover digest
is the canonical semantic-record digest.

Each serialized record also declares `GENERATOR`, `PULLBACK`, or
`COMMON_REFINEMENT`. Deserialization of a derived record requires a parent
resolver: every parent digest is rehashed, the complete acyclic parent
derivation is checked, and the child members and mark are recomputed. A join
without exactly one ACBE and one RPM generating parent, or a pullback without
its exact parent, is rejected rather than treated as evidence.

The successor is not defined as the already-joined sheaf category. Doing so
would make the ACBE and RPM reflectors identity on every admitted object and
would erase the nontrivial modal structure a second time.

Instead, begin with the ambient presheaf topos

```text
E_amb = PSh(C x L).
```

On this one ambient topos, generate three topology refinements from:

1. legacy observational covers in the `C` coordinate;
2. `K_A` covers in the `L` coordinate; and
3. `K_R` covers in the `L` coordinate.

Write their sheafification reflectors, followed by inclusion back into the
ambient topos, as `M_obs`, `M_A`, and `M_R`. The fully resolved topology and
subtopos are

```text
J_res = J_obs join J_A join J_R,
E_res = Sh(C x L, J_res).
```

Assuming the registered legacy category `C` is small in the chosen universe,
the underlying Noetic Topos 2.0 candidate is

```text
NoeTop_2 := E_amb.
```

It is equipped with the three modalities and the resolved subtopos. The full
research object is named separately:

```text
NoeSystem_2 = (NoeTop_2, M_obs, M_A, M_R, E_res, EXTERNAL_MARK_RECORD).
```

`NoeSystem_2` is a structured package, not itself a topos or category, and the
provenance record is external audit data rather than an internal topos object.

The modalities are nontrivial on `E_amb`. On `E_res`, both `M_A` and `M_R`
restrict to identity, as every resolved object already satisfies both sheaf
conditions. This distinction is part of the contract: raw and partially
resolved evidence lives in the ambient topos; only jointly resolved objects
enter `E_res`. The construction remains a candidate until the product-site
comparison and migration proof are discharged.

## 3. Finite theorems and proofs

### Theorem NT2-1

Each `K_A` and `K_R` basis is jointly exhaustive, stable under pullback, and
stable under its own cover composition. Hence its generated covering sieves
form a Grothendieck topology.

Proof. Pullbacks in `L` are intersections. Pulling `V intersect A_i -> V`
back along `U -> V` gives `U intersect A_i -> U`, and similarly for RPM.
The union of the two pieces is `V`. Refining either piece by the same coordinate
partition returns that piece together with an empty piece, so the composite
family refines the original cover. Identity families and the null cover at the
empty context give the remaining pretopology cases. The standard passage from
a pretopology to covering sieves then gives a Grothendieck topology.

### Theorem NT2-2

Both context-factor topologies are subcanonical.

Proof. Let `yW` be representable. A section of `yW` on `V` exists exactly when
`V` is a subset of `W`, and is then unique. If both pieces of a marked cover
map into `W`, their union `V` maps into `W`; conversely a map from `V` restricts
uniquely. The empty case is also unique. Thus the representable gluing map is a
bijection for every generator.

This theorem applies only to `L`. It does not repair or assume subcanonicity of
`(C,J_legacy)`.

### Theorem NT2-3

The ACBE and RPM sheafification modalities on `PSh(L)` are distinct and neither
is the identity modality.

Proof. Define `F_A(V)` to be the set of bit assignments to those complete ACBE
blocks `A_i` contained in `V`. Restriction forgets coordinates. Complete ACBE
blocks split uniquely across `K_A(V)`, so `F_A` satisfies ACBE gluing. At
`V=Omega`, `F_A(Omega)` has four sections, while each RPM half contains no
complete ACBE block. The RPM matching-family set has one element, so the RPM
gluing map is not injective. Thus `F_A` is an ACBE sheaf but not an RPM sheaf.
The symmetric construction `F_R` reverses the roles. Therefore the reflective
subcategories and their reflectors differ, and each reflector changes at least
one presheaf.

### Theorem NT2-4

The common refinement of the ACBE and RPM global covers is the four-singleton
cover.

Proof. Every intersection `A_i intersect R_j` is the singleton `{(i,j)}`.
At an arbitrary `V`, the refinement consists of the singletons belonging to
`V`. This is the atomic cover. Every jointly exhaustive family of subcontexts
contains, in its generated sieve, each singleton of `V`; conversely every
generator is jointly exhaustive. Thus the joined context coverage is the
ordinary union topology on the finite powerset lattice.

The dependency-free checker exhausts all 16 contexts, all 16 representables,
both witness presheaves, and every generating-cover pullback. Its certificate is
`FINITE_MODEL_CERTIFICATE_v0.1.json`. Execution is corroboration of these finite
proofs, not formal verification.

The eight-page frozen baseline PDF was rendered in full and visually inspected.
The identity descent axiom appears on PDF page 3, the RPM section equation on
PDF page 4, and the three coverage clauses and reduction lemma on PDF page 5.
Exact raw and normalized source hashes are recorded in
`SOURCE_VERIFICATION_v0.1.json`.

## 4. Modalities and markings

Let `a_A` and `a_R` be the respective sheafification functors and `i_A`, `i_R`
their inclusions into the ambient presheaf topos. The candidate modalities are
the left-exact idempotent reflectors

```text
M_A = i_A a_A,      M_R = i_R a_R.
```

Theorem NT2-3 proves the distinction first on `PSh(L)`. It lifts to
`PSh(C x L)` by taking the external product of each witness with a
representable `yC_0`: at `(C_0,Omega)`, the identity of `C_0` preserves the
four-versus-one witness. Thus `M_A` and `M_R` are distinct and non-identity on
the ambient successor topos. They are both identity after restriction to
`E_res`; no text may describe them as nontrivial endomodalities of the resolved
subtopos.

For the finite context factor alone, an internal proof candidate now gives

```text
M_A M_R ~= M_atom ~= M_R M_A
```

naturally on `PSh(L,Set)`, with `J_atom = J_A join J_R`. The proof constructs
the one-partition reflector explicitly, handles the null cover by the empty
product, and flattens the two nested transverse products to the four atomic
factors. Its proof, exhaustive 298-sieve topology certificate, and six tests
are in `modality_composition/`. These are natural isomorphisms, not strict
equalities.

The pointwise lift to the ambient `PSh(C x L)`, its coherence in the `C`
coordinate, and interaction with the observational topology remain `OPEN`.
No release text may extend the finite-context theorem to those settings until
that comparison is proved and reviewed.

Marked data are not bare site objects. A mark record contains:

```text
COVER_MARK_RECORD = {
  cover_kind,
  source_authority_ref,
  assumptions,
  evidence_or_proof_refs,
  review_state,
  provenance_chain
}.

MARKED_COVER = {
  derivation_kind,
  target,
  exact_member_arrows,
  COVER_MARK_RECORD,
  parent_cover_sha256s
}.
```

An application-level marked sheaf object additionally needs a
`sheaf_object_ref` and `context_atom_or_block`; that separate object schema is
still `OPEN`. A cover record must not pretend to identify a sheaf object.

## 5. Gluing boundary

For Set-valued presheaves, gluing means exactly that the canonical map from a
global section to matching local sections is bijective. For vector-valued
cellular data, a separate linear representation, finite-dimensional stalks,
and inner products are required before a Laplacian is defined.

Probability distributions do not inherit Set-valued gluing by analogy.
Pairwise-compatible marginals may lack a global joint distribution. A
probabilistic successor must use one of the following explicit gates:

- an acyclic or junction-tree cover with a proved extension theorem;
- a finite linear-program feasibility certificate for the joint distribution;
- an obstruction calculation with a stated coefficient system; or
- a quantitative relaxation whose residual and uncertainty are reported.

No passing Set-valued sheaf test licenses a probabilistic consistency claim.

## 6. Backward-compatibility contract

The legacy topos is preserved verbatim as

```text
E_legacy = Sh(C,J_legacy).
```

The target comparison is `E_res ~= E_legacy^4` after the joined context
coverage is imposed. It concerns the resolved subtopos, not the larger modal
package. Under that comparison, choose one registry-controlled neutral atom
`omega_00`. The proposed fully faithful legacy embedding sends

```text
X |-> (X, 1, 1, 1),
```

with `X` in the neutral channel and terminal objects in the remaining channels.
Categorically, evaluation at the neutral channel must be connected to `X` by a
specified natural isomorphism, giving an isomorphism
`ev_00 o iota ~= Id_E_legacy`. Separately, the serialization implementation
must preserve registered identifiers and canonical payload hashes by strict
equality. A categorical natural isomorphism is not a bit-for-bit serialization
receipt. This comparison, full-faithfulness proof, serialization rule, and both
round-trip checks are still `PROOF_REQUIRED`; they are not silently assumed by
v0.1.

Legacy observational cover tags and source identities must remain readable
after migration, but the typed observational/product-site serialization and
round-trip test are still `PROOF_REQUIRED`. The v0.1 context-factor checker
does not establish them. No legacy theorem is promoted merely because it has
been serialized into the new context factor.

The comparison also exposes a strict expressivity boundary. If established,
`E_res ~= E_legacy^4` is four independent legacy channels: the discrete
resolved context factor contains no remaining overlap, transition law, or
cross-atom coupling. The present sixteen-context construction is therefore a
finite separation and provenance reference model, not yet a substantively rich
final semantics for Noetic Topos 2.0. A final successor must either (a) name the
ambient modal package, rather than the discrete resolved product alone, as its
principal semantics, or (b) add typed overlaps/transition data and prove their
coherence. Which route is canonical remains `OPEN`; v0.1 licenses neither.

## 7. Admission gates

Noetic Topos 2.0 may leave Ring 4 only after all of the following are present:

1. an independent category-theory review of Theorems NT2-1 through NT2-4;
2. proof-assistant artifacts for the finite site, witness presheaves, and the
   product-site comparison;
3. a verified legacy round-trip with stable identifiers and hashes;
4. a theorem-ledger merge linking every statement to exact source and proof
   artifacts;
5. a proof and review of the product-site lift of the finite-context modality
   composition theorem and its interaction with observational coverage;
6. separate probability-gluing theorems or feasibility certificates; and
7. a canonical decision and proof package for ambient semantics versus genuine
   cross-context coupling in the resolved semantics; and
8. explicit confirmation that no empirical or product wording was licensed.

## 8. References and provenance

The standard facts used here are the construction of a topology from a site or
pretopology and the exact left-adjoint sheafification functor. Governing
references remain Mac Lane--Moerdijk, *Sheaves in Geometry and Logic*, Chapters
III and VII, and the Stacks Project, Tags `00ZC` and `00W1`. The finite
transverse-partition construction and its CAS/TKS interpretation are a Project
Coherence research candidate and therefore remain novelty-unassessed pending a
literature search and independent review.
