# Project Coherence Gate 1 candidate

Status: `OPEN / IN REVIEW / NOT FROZEN`

Admission: `Ring 4`

License status: `NOT LICENSED`

This private candidate is a reviewable research tranche, not PSR-8 and not a
release. It integrates the bounded v7.4 audit, typed TKS v8 reference kernel,
Noetic Topos 2 finite-context construction, and scoped Lean proof seed.

## Current verified receipts

- **Gate 0 dependency:** structural candidate verifier passes, including the
  49-group/712-member term census; Gate 0 itself remains OPEN and NOT FROZEN.
- **v7.4:** 1,258 declaration headings inventoried; 29 correction records
  adjudicated; all unlisted declarations default to OPEN.
- **Typed TKS v8:** 20 executable tests pass; 12 implementation, test,
  specification, verifier, and formal artifacts are hash-bound.
- **Lean:** version 4.32.1 at commit
  `f054605aea4b840552cca2e725580bffd1e1b704`; 16 theorem dependency audits;
  no `sorry` or project-specific axioms; only the explicitly allowed standard
  `propext` dependency occurs.
- **Noetic finite model:** all 16 contexts pass; eight canonical-schema theorem
  records and one separate OPEN obligation validate; marked-cover JSON is
  strict, derived records resolve and recompute their provenance DAG, and the
  ACBE/RPM join retains both parent digests.
- **Finite-context modality composition:** an internal proof candidate and
  exhaustive 298-sieve calculation establish
  `M_A M_R ~= M_atom ~= M_R M_A` on `PSh(L,Set)`, with six scoped tests.

## Mandatory boundaries

The v7.4 audit is bounded, the typed kernel is not canonical TKS v8, and the
Noetic result has not been lifted to `PSh(C x L)` or combined with observational
coverage. The resolved finite context is only four independent channels.
Backward compatibility, richer cross-context semantics, the portable frozen-PDF
evidence bundle, universal formal proofs, canonical ledger merge, and
independent specialist review remain OPEN.

No empirical result, product wording, public disclosure, or release admission
follows from a passing verifier.

## Reproduction

From the repository root:

```powershell
python scripts\verify_project_coherence_gate1.py
```

The integrated verifier checks the 23-entry top-level hash chain and runs six
subordinate verifiers. Its manifest is
`GATE1_ARTIFACT_MANIFEST_v0.1.json`; a later reviewed commit or acceptance
receipt must bind the manifest's own SHA-256.
