# Gate0 Load-Bearing Term Census — Audit Summary v0.1

**Status:** Bounded technical census complete; provisional; not a canon freeze.

**As of:** 2026-08-04

## Outcome

The Phase0 starter registry's 24 entries are imported by exact ID and metadata policy. The census then records 49 source-bound groups containing 712 individually identified members:

| Disposition | Member records | Meaning |
| --- | ---: | --- |
| `REGISTERED` | 24 | Closed-family members under an existing Phase0 registry entry. |
| `PROPOSED_ADD` | 326 | Load-bearing terms not yet in the starter registry. |
| `TYPED_VARIANT` | 348 | Source-, version-, implementation-, or experiment-specific identities that may not be silently interchanged. |
| `EXPLICITLY_OUT_OF_SCOPE` | 14 | Reviewed surfaces intentionally deferred or excluded under this Gate0 boundary. |

The census does **not** decide which competing definition is canonical. Nineteen conflict guards remain explicitly open.

## Bounded inclusion rule

An item is load-bearing when changing it would change at least one of:

1. parsing, typing, serialization, or an exported schema;
2. an ontology member, crosswalk, theorem hypothesis, axiom, proof-status boundary, or algebra profile;
3. a path/dynamic interpretation, measurement calculation, calibration, evidence eligibility, or reproducibility binding; or
4. the identity of a source/version that could otherwise be silently collapsed.

Ordinary prose, local theorem binders, equation/chapter numbers, and non-serialized UI copy are excluded unless they cross one of those tests. Advanced TKS theorem tracks are deferred to Gate1 through named `EXPLICITLY_OUT_OF_SCOPE` records rather than being ignored.

## What is covered

| Gate0 surface | Census treatment |
| --- | --- |
| Notation and relation kinds | Semantic relation taxonomy; CAS v7.7 register operators; compiler arrows, set relations, and grammar-bearing syntax. |
| Algebra profiles | TKS Tootra-addition and Noetic monoids; CAS v7.7 operator discipline; active compiler operational algebra, kept profile-distinct. |
| Worlds and axis identities | Native TKS Worlds, CAS Domains, CAS Registers, and the conflicting compiler `Worlds→Domains` alias. |
| Elements | TKS v7.4 A1–D10 family; both A1–D10 owner payloads; normalized A0–D9 family; PCBA cell-index/address distinction. |
| Foundations | Native seven TKS Foundations; both owner 28 payloads; unindexed rich normalized 28; CAS Drives; all 28 CAS Drive × Register positions. |
| Acquisitions | TKS v7.4 `A0 + D1..D7 + W1..W7 + P1..P7` and the different normalized named 22-item vocabulary. |
| Noetic Topos | Site/sheaf vocabulary, distinguished Noetica data, admissibility, coverage clauses, ACBE/RPM data, open/closed simplex and geometry terms. |
| Paths and dynamics | Typed paths, Cause/Bias/Effect, cascade gain versus local flow, RPM variants, fractal runtime, and CAS production semantics. |
| Evidence | Nine claim/evidence kinds, all 25 owner-required run bindings, and Evidence Packet instrumentation eligibility. |
| Measurement | Measurement kinds/statuses, 19 CAS-Ohm quantities, modes/regions/trends, 46 CJT-Q fields, Test Point identity, 27 Calibration Profile fields, and typed ASOM/D-W-P crosswalks. |
| Compiler vocabulary | 15 type kinds plus load-bearing AST, runtime, production, artifact, meta-set, and tuple fields. |

Every closed family has an expected cardinality checked by the verifier. JSON-backed families include a JSON Pointer template and member index, so each member resolves to an exact source location.

Source-fidelity correction recorded on 2026-08-04: a pre-review census draft incorrectly expanded `ASOM` as Accumulation/Switching/Oscillation/Multiplication. The hash-bound CAS-Ohm Guide page 11 and operationalization addendum Table 2 instead define `S` = Starved, `A` = Aligned, `O` = Oversaturated, and `M` = Misaligned. The machine-readable entries now use those source-defined meanings, and the verifier asserts their exact IDs, labels, and symbols. The label correction itself changed no family cardinality. The same audit added 17 previously omitted CJT-Q fields for resistance decomposition, raw/full-scale response, uncertainty, lineage, units, censoring, and calibration binding, increasing the bounded total from 695 to 712 without promoting CAS-Ohm beyond its experimental boundary.

## Preserved conflicts

The census blocks these silent collapses:

1. native TKS World versus CAS Domain versus CAS Register;
2. one-based A1–D10 Elements versus zero-based A0–D9 Elements;
3. owner D3DA versus deployed A124 payloads;
4. the rich 28-definition file versus the files actually admitted by `canon_index.json`;
5. TKS v7.4 acquisitions versus normalized named acquisitions;
6. native TKS Foundations versus CAS Drives and Drive × Register positions;
7. RPM computation versus RPM section–retraction versus compiler runtime summary;
8. TKS, Python compiler, and Rust algebra profiles;
9. formal, mechanical, implementation, empirical, and external-acceptance evidence kinds;
10. formal Noetic Topos claims versus product and empirical claims;
11. subcanonicity as an axiom versus a proved theorem;
12. Production Target `Ω` versus the subobject-classifier notation;
13. PCBA cell index versus an open-simplex mixed address; and
14. the active compiler's legacy `Worlds→Domains` alias versus the owner-signed typed-axis rule;
15. CAS-Ohm's Guide scale and `sat=8.5` versus Appendix I's score/fraction scales and calibrated effective-resistance units;
16. Fisher-Rao gain versus local Jacobian/projection gain, plus profile-gated circuit aggregation rules;
17. ASOM as a response-region mnemonic versus semantic outcome as an independent axis;
18. the Appendix C EBNF versus the larger language used by the five PCBA reference boards; and
19. the CSB's `sat=0.1` output versus its `threshold=0.9` fuse, together with unimplemented latch and fail-closed semantics.

No guard is marked resolved, and no profile is selected as canon.

## Source audit

The machine-readable file pins 22 source identities and hashes. The review included:

- the owner-signed semantic registry, Phase0 authority matrix, and 24-entry starter registry;
- the TKS v7.4 master and integrated text;
- all 79 pages of the three registered v7.4 overlays (18-page review/corrections, 36-page referee edition, and 25-page corrected chapters);
- both owner 40/28 payloads and all four normalized-canon JSON surfaces;
- the registered CAS foundational clarifications and the 28-position translation scaffold;
- the registered conservative Noetic Topos TeX;
- PCBA address pages, Appendix C/D grammar and reference-board surfaces, the CSB design, and Appendix I's measurement/calibration material;
- all 18 CAS-Ohm Guide pages and the addendum's paragraph/table structure; and
- the active compiler's grammar, AST, runtime, production, meta-set, and compilation-artifact schemas.

The overlays are retained as correction/editorial sources. Their phrases such as “referee-defensible” are not treated as external acceptance, mechanized proof, or empirical validation.

## Validation

Run:

```powershell
python docs\working\project_coherence\gate0\term_census\verify_gate0_term_census.py
```

Current result:

```text
PASS Gate0 term census: 24 starter entries; 49 groups; 712 members; 22 source hashes; 19 preserved conflicts; 13 coverage classes; owner diffs 40=20, 28=8.
```

The verifier independently checks:

- all pinned file hashes;
- exact import of all 24 starter registry entries and their alias/migration metadata;
- unique group/member IDs and source locators;
- every expected closed-family count;
- all required coverage classes and mapping of every admitted group;
- exact normalized Element, rich-28, and Acquisition members;
- exact owner-payload codes and recomputed 20-of-40 / 8-of-28 definition differences;
- all 25 owner-required run bindings;
- the normalized-index omission of the rich 28 file;
- raw and LF-normalized compiler identities; and
- the required conflict guards, including the compiler Worlds alias, Ω collision, CAS-Ohm scale/profile distinctions, and PCBA grammar/CSB contradictions.

## Completeness limits

- This is complete relative to the 22 pinned sources and the inclusion rule; it is not a census of every prose word or theorem-local variable.
- The TKS 28 translation key says its original-source population remains pending. Its 28 CAS positions are counted, but not promoted to TKS definition identity.
- The rich normalized 28 file remains unindexed and experimental.
- The addendum's semantic content was structurally extracted from paragraphs and tables. LibreOffice and Word rendering did not complete in the available desktop session, so this package makes no visual-layout claim about that DOCX.
- Compiler coverage is limited to semantic/runtime/exported fields. Internal helper locals and non-semantic diagnostics remain outside the boundary.
- This package supplies technical evidence for `G0-CRITERION-INITIAL-TERM-COVERAGE` only. It does not close other Gate0 criteria, accept Gate1 theorems, or authorize migration.
