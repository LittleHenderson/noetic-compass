# Noetic Topos 2.0: A Marked and Modal Successor to the Conservative Noetic Site

**White paper, version 0.1 — 2026-08-07**

**Artifact status:** `DRAFT / GATE 1 RESEARCH CANDIDATE / Ring 4 / NOT LICENSED / HELD`

**Source basis:**
- `NOETIC_TOPOS_2_SPEC_v0.1.md` (SHA-256 `156A5D8C5320F36E81E3B46473BA8A038B35672DCD28839A404D96A3DB1A763A`)
- `NOETIC_TOPOS_2_THEOREMS_v0.1.json` (SHA-256 `52E000652C7DECE64C1E2B3F613D85FEFB2F80414CFAAD53AA38FE339B26E536`)
- `NOETIC_TOPOS_2_PROOF_OBLIGATIONS_v0.1.json` (SHA-256 `FD567E3826E4472EFD013DC7F3DEE514B6AD28B9E41CFFFD10087BE1133746C7`)
- `FINITE_MODEL_CERTIFICATE_v0.1.json`; `modality_composition/` proof and certificate
- Publication delta: `PAPER_2_THE_MARKED_AND_MODAL_NOETIC_TOPOS_DRAFT_v0.1.md`
  (base commit `a1cd990109e7561dfd03949bf0e1653461c7ae44`)
- Implementation: `src/noetic_topos2/` (`finite_site.py`, `modality_composition/`)
- Verifier: `scripts/verify_noetic_topos2_gate1.py`

**Authorship / review:** `OPEN / INTERNAL PROOF CANDIDATES PRESENT / FORMAL AND INDEPENDENT REVIEW OPEN`

---

## Abstract

The conservative Noetic Topos construction contains a valid conditional
topos-existence argument, but its ACBE and RPM cover clauses do not retain the
separate information later interpretations assigned to them: ACBE reflexivity
places an identity in the corresponding sieve, and the RPM counit — split by
its section — forces an identity by sieve closure. Each clause alone generates
only maximal sieves, and the combined topology collapses to the
jointly-surjective coverage already present in the source. Distinct modalities
cannot be recovered by relabeling those generators.

Noetic Topos 2.0 is the first conservative successor that survives this
collapse counterexample. It augments the legacy site with a finite four-atom
context lattice `L = P({0,1} × {0,1})` whose coordinates carry formal ACBE and
RPM marks, equips `L` with two transverse coordinate-partition coverages, and
keeps immutable, hash-chained cover provenance *outside* the ordinary topology.
On `PSh(L, Set)`, internal proofs backed by exhaustive finite checks establish
that both generated topologies are subcanonical, their sheafification
reflectors are distinct and non-identity, their join is the topology generated
by the four-singleton partition, and the reflectors commute up to canonical
natural isomorphism. The ambient candidate `NoeTop_2 = PSh(C × L)` carries
three modal reflectors and a resolved subtopos; the full research object
`NoeSystem_2` packages these with an external mark record. The product-site
lift, legacy round-trip comparison, cross-context coupling, proof-assistant
formalization of the sheaf layer, and independent category-theory review remain
open, and the paper's claim discipline treats preserving those boundaries as
part of the result.

---

## 1. The defect being repaired

Let `C` be the registered legacy category `Noetica` and `J_legacy` its proven
coverage. The conservative source admits covering sieves from three routes:
jointly-surjective observational families, designated ACBE descent maps, and
the RPM counit. Two sieve arguments are decisive:

1. **ACBE.** The reflexive descent map at equal contexts is `id_X`. A sieve on
   `X` containing `id_X` is maximal.
2. **RPM.** The section-retraction data `ε_X ∘ η_X = id_X` mean that any sieve
   containing `ε_X` also contains `id_X` after closure under precomposition —
   again maximal.

Hence `J_legacy = J_jointly-surjective`: ordinary sieve generation has
*forgotten* the distinct ACBE and RPM provenance. This does not invalidate the
generic topos-existence statement; it narrows what the topology records. A
successor must change the cover generators — renaming the old maps is not a
repair.

A second, independent gap: there is no derivation of subcanonicity for the
legacy topology. A finite countermodel (sets of size ≤ 2 with injections)
exhibits a jointly-covering pair of point inclusions whose compatible local
injections into a singleton admit no global injection. Until a revised site is
proved subcanonical, the distinguished legacy object is represented in the
sheaf topos by `a_legacy(yX)`, never by silently treating `yX` as a sheaf.

## 2. The finite marked context factor

### 2.1 Context lattice and transverse coverages

Define

```text
Omega = {0,1} × {0,1},     L = P(Omega),     U -> V  iff  U ⊆ V.
```

The first coordinate is the formal ACBE mark; the second the formal RPM mark.
These are structural labels only, with no empirical interpretation until a
separate operationalization and validation record exists.

With blocks `A_i = {(i,0),(i,1)}` and `R_j = {(0,j),(1,j)}`, the generating
families at each context `V` are

```text
K_A(V) = { V ∩ A_0 -> V,  V ∩ A_1 -> V },
K_R(V) = { V ∩ R_0 -> V,  V ∩ R_1 -> V },
```

with the empty family covering the empty context. Unlike the legacy clauses,
the global pieces are *proper* subcontexts: neither family contains an
identity. Pullback along `U -> V` is intersection with `U`, so each basis is
stable under pullback; refining a partition piece by the same partition returns
that piece plus empty pieces.

### 2.2 Marks as parallel audit data

An ordinary Grothendieck topology retains generated sieves, not why a family
was proposed. The reference implementation therefore maintains two distinct
representations. The topology consumes the unmarked family; governance code
consumes an immutable `MarkedCover`:

```text
MARKED_COVER = {
  derivation_kind,          # GENERATOR | PULLBACK | COMMON_REFINEMENT
  target,
  exact_member_arrows,
  COVER_MARK_RECORD,        # cover kind, source authority, assumptions,
                            # evidence refs, review state, provenance chain
  parent_cover_sha256s
}
```

Canonical JSON and SHA-256 bind the target, members, mark, and sorted parent
digests. Pullback creates a new record whose provenance chain contains its
parent digest; the ACBE/RPM common refinement is a derivation node with both
generating-cover digests as parents. This matters at singleton contexts, where
the bare ACBE and RPM families coincide but their marked records and digests
remain distinct. Deserialization of a derived record requires a parent
resolver: every parent digest is rehashed, the acyclic derivation is checked,
and child members and mark are recomputed; a join without exactly one ACBE and
one RPM generating parent fails closed. Unknown or duplicate JSON keys and
uncontrolled review states are rejected.

The mark mechanism is an external serialization and audit invariant — not a
claim that `MarkedCover` is an internal topos object, a colored-site
construction, or a categorical semantics of evidence. Conflating the two
interfaces would repeat the original information-loss error.

## 3. The ambient modal candidate

The successor is *not* defined as the already-joined sheaf category — that
would make the ACBE and RPM reflectors identity on every admitted object and
erase the modal structure a second time. Instead, begin with the ambient
presheaf topos and three topology refinements:

```text
E_amb = PSh(C × L)
J_res = J_obs ∨ J_A ∨ J_R,      E_res = Sh(C × L, J_res)
M_obs = i_obs a_obs,   M_A = i_A a_A,   M_R = i_R a_R
```

Assuming `C` is small in the chosen universe:

```text
NoeTop_2  := E_amb
NoeSystem_2 = (NoeTop_2, M_obs, M_A, M_R, E_res, EXTERNAL_MARK_RECORD)
```

`NoeSystem_2` is a structured package, not itself a topos or category; the
provenance record is external audit data. Raw and partially resolved evidence
lives in the ambient topos; only jointly resolved objects enter `E_res`. On
`E_res`, both `M_A` and `M_R` restrict to identity — no text may describe them
as nontrivial endomodalities of the resolved subtopos.

The v0.1 executable model covers only the `L` coordinate and its mark
derivations. Typed observational covers in `C`, general arrows of `C × L`, and
the product-site comparison remain `OPEN`.

## 4. Theorems on the finite context factor

**NT2-1 (Topologies).** Each of `K_A`, `K_R` is jointly exhaustive, stable
under pullback, and stable under its own composition; the generated covering
sieves form Grothendieck topologies `J_A`, `J_R`. *Proof:* pullbacks in `L` are
intersections; the standard pretopology-to-topology passage applies.

**NT2-2 (Subcanonicity of the context factor).** Both topologies are
subcanonical on `L`: a section of `yW` on `V` exists iff `V ⊆ W` and is then
unique; if both pieces of a cover map into `W`, so does their union. This
applies *only* to `L` — it does not repair the legacy subcanonicity gap.

**NT2-3 (Distinct, non-identity modalities).** Let `F_A(V)` be the set of bit
assignments to complete ACBE blocks contained in `V`, restriction forgetting
missing blocks. `F_A` satisfies ACBE gluing; at `V = Omega` it has four
sections, while each RPM half contains no complete ACBE block, so the RPM
gluing map is not injective. Thus `F_A` is a `J_A`-sheaf but not a `J_R`-sheaf;
the symmetric `F_R` reverses the roles. The reflective subcategories and
reflectors therefore differ, and neither reflector is the identity on
`PSh(L, Set)`.

**NT2-4 (Joined topology).** `A_i ∩ R_j = {(i,j)}`, so the common refinement of
the two global partitions is the four-singleton cover, and

```text
J_A ∨ J_R = J_singleton
```

— the topology generated by the singleton partition (the local label `J_atom`
does not assert the standard category-theoretic atomic topology).

**Modality composition.** With explicit reflectors
`(R_P F)(V) = ∏_{B ∈ P, V ∩ B ≠ ∅} F(V ∩ B)` (empty product a singleton), the
registered internal proof verifies the universal property directly and obtains

```text
M_A M_R ≅ M_atom ≅ M_R M_A     naturally on PSh(L, Set),
```

by flattening nested transverse products to atomic factors. These are natural
isomorphisms, not strict equalities. The corrective narrative point: the finite
modalities are *distinct but commuting*. Distinctness does not imply
noncommutation, and no current artifact licenses a noncommutation claim.

**Ambient lift caveat.** An earlier external-product distinctness witness for
`PSh(C × L)` is false in general (the null cover over `(c, ∅)` obstructs it);
ambient distinctness remains `OPEN`, with the valid result limited to
`PSh(L, Set)`.

### Executable corroboration

A dependency-free checker exhausts all 16 contexts, all 16 representables, both
witness presheaves, and every generating-cover pullback
(`FINITE_MODEL_CERTIFICATE_v0.1.json`). The exact-topology implementation
enumerates all 298 sieves over the sixteen contexts and reports 168 covering
sieves for both the join and singleton presentations; the modality verifier
covers 18 fixtures and 3,012 restriction squares. At the bound commit the
finite-site suite (8 tests), the modality-composition suite (6 tests), and the
pinned Lean Gate 1 verifier all pass. Lean scope covers four-atom
exhaustiveness, proper global pieces, transverse refinement, and witness
separation — not the sheaf conditions, topology generation, reflector universal
properties, or product-site comparison. Execution is corroboration of finite
proofs, not formal verification or independent review.

## 5. Gluing boundary for probabilistic data

For Set-valued presheaves, gluing is bijectivity of the canonical map from
global to matching local sections. Probability distributions do not inherit
this by analogy: pairwise-compatible marginals may lack a global joint
distribution. A probabilistic successor must pass one of four explicit gates —
an acyclic/junction-tree cover with a proved extension theorem; a finite
linear-program feasibility certificate; an obstruction calculation with a
stated coefficient system; or a quantitative relaxation with reported residual
and uncertainty. No passing Set-valued sheaf test licenses a probabilistic
consistency claim.

## 6. Backward compatibility as a conjectural comparison

The legacy topos is preserved verbatim as `E_legacy = Sh(C, J_legacy)`. The
target comparison is `E_res ≅ E_legacy^4` after atomic resolution, with a
proposed fully faithful neutral-channel embedding `X |-> (X, 1, 1, 1)` and
`ev_00 ∘ ι ≅ Id`. A categorical natural isomorphism is not a bit-for-bit
serialization receipt: identifier and canonical-payload-hash preservation is a
separate strict-equality requirement. Both round trips remain `PROOF_REQUIRED`;
this paper claims no backward compatibility.

Even if proved, `E_legacy^4` exposes a strict expressivity boundary: four
independent legacy channels with no remaining overlap, transition law, or
cross-atom coupling. The sixteen-context construction is a finite separation
and provenance reference model — not yet a substantively rich final semantics.
A final successor must either name the ambient modal package as principal
semantics or add typed overlaps/transition data and prove their coherence;
which route is canonical remains `OPEN`, and v0.1 licenses neither.

## 7. Admission gates

Noetic Topos 2.0 may leave Ring 4 only after: (1) independent category-theory
review of NT2-1–NT2-4 and the legacy reduction; (2) proof-assistant artifacts
for the finite site, witness presheaves, and product-site comparison; (3) a
verified legacy round-trip with stable identifiers and hashes; (4) a
theorem-ledger merge linking every statement to exact sources; (5) proof and
review of the product-site lift of modality composition and its interaction
with observational coverage; (6) separate probability-gluing theorems or
feasibility certificates; (7) a canonical decision between ambient semantics
and genuine cross-context coupling; and (8) explicit confirmation that no
empirical or product wording was licensed.

## 8. Conclusion

The correction and the successor fit together cleanly: the legacy ACBE/RPM
clauses collapse because identities enter their sieves, and nontriviality is
recovered only by changing the context generators. In the finite model the new
modalities are distinct and non-identity, but they commute and jointly resolve
to four atomic channels, while hash-chained mark records preserve the
derivational provenance ordinary topology generation forgets. That is a
coherent mathematical reference point, not a finished semantics of contextual
cognition — and maintaining that distinction is itself part of the
contribution.

## References

- The Stacks Project, Tags `00ZC` (topology from a site), `00W1`
  (sheafification), `00WO` (representable sheaves).
  <https://stacks.math.columbia.edu>
- S. Mac Lane and I. Moerdijk, *Sheaves in Geometry and Logic*, Springer, 1994.
  DOI: 10.1007/978-1-4612-0927-0
- Project Coherence, *Mathematical Red-Team Report* v0.1 (collapse
  counterexample and subcanonicity countermodel).

Full bibliographic metadata and use boundaries: `CITATION_LEDGER_v0.1.json`
(category-theory publication package).

---

**Publication boundary.** This white paper is an internal research artifact,
not a released specification, peer-reviewed result, Evidence Packet, product
claim, license decision, canon amendment, or public disclosure authorization.
The finite transverse-partition construction is novelty-unassessed pending a
dedicated literature search. New matter relative to USPTO provisional
64/037,173 requires its own filing or inclusion in the utility conversion.
