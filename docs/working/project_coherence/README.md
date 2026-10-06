# Project Coherence Phase 0 controls

Status: `DRAFT / OPEN / NOT FROZEN`

This directory is the controlled starting point for Project Coherence and the proposed Provable Systems Release 8.0 (`PSR-8`). It records source identity, semantic authority, migration questions, theorem and claim contracts, and the boundary between research inputs and admitted results.

Nothing in this directory releases TKS v8, Noetic Topos 2.0, CAS Core v8, CAS PCBA v8, CAS-Ohm v1.0, or CAS Harness v2. Nothing here changes a current CAS Harness product claim from `OPEN` or `NOT LICENSED` to `LICENSED`.

## Controlled artifacts

- `PROJECT_COHERENCE_MASTER_CHARTER_v0.1.md` - program constitution, admission rings, workstreams, gates, and first-year sequence.
- `CANONICAL_SOURCE_AUTHORITY_MATRIX_v0.1.json` - byte identities, authority scopes, conflicts, and mutability rules.
- `SYMBOL_AND_TERMINOLOGY_REGISTRY_v0.1.json` - load-bearing names and typed distinctions that successor work must preserve.
- `INITIAL_MIGRATION_MATRIX_v0.1.json` - first audit queue; every entry is `UNASSESSED` or `IN_REVIEW`.
- `THEOREM_RECORD.schema.json` - contract for formal statements and proof status.
- `CLAIM_RECORD.schema.json` - contract for empirical and product claims.
- `THEOREM_LEDGER_v0.1.json` - initial load-bearing theorem, counterexample, and proof-obligation records.
- `CLAIM_LEDGER_v0.1.json` - initial nonclaims for Noetic Topos, projector capacity, CAS-Ohm, and historical Harness readiness.
- `PROVISIONAL_TRANSFER_QUARANTINE_v0.1.json` - chapter-by-chapter quarantine for *Ten Advances in Mathematics and Theoretical Computer Science* and proposed CAS/TKS transfers.
- `MATHEMATICAL_RED_TEAM_REPORT_v0.1.md` - counterexamples, theorem defects, safe standard results, and correction obligations.
- `LITERATURE_AND_TRANSFER_AUDIT_v0.1.md` - publication-status audit, primary literature, exact transfer hypotheses, and citation rules.
- `OPEN_VS_HELD_BOUNDARY_v0.1.md` - non-legal disclosure-control draft requiring owner and counsel review.
- `CHANGELOG.md` - changes to this Phase 0 package.

## Authority rule

A filename, title-page declaration, generated proof, saved result, or prior summary is not sufficient authority by itself. Exact source hashes and explicit correction overlays govern. Byte-different sources remain distinct until a reviewed transformation or adjudication record resolves them.

The owner-signed semantic registry remains the highest recorded semantic manifest, but it is time-indexed and leaves twelve conflicts unresolved. Later byte variants, including the current foundational-clarifications file, require an amendment or other explicit adjudication before anyone may claim they are covered by the earlier receipt.

## Verification

From the repository root, run:

```powershell
python scripts/verify_project_coherence_phase0.py
```

The verifier uses only the Python standard library. It validates JSON structure and enums, unique identifiers, static source hashes that are locally available, the transfer quarantine, and the charter's fail-closed status. The live CAS Harness production TODO is deliberately checked for presence but not pinned to a hash because it is mutable.

Passing this verifier means only that the Phase 0 control package is internally well formed. It is not mathematical peer review, empirical validation, product acceptance, IP clearance, or a charter freeze.

## Freeze rule

Gate 0 remains `OPEN`. Freezing requires owner review, resolution or explicit ownership of source conflicts, incorporation of mathematical and literature audits, review of the open-vs-held boundary, and an explicit recorded approval. Silence is not approval.
