# Security and Verdict Boundary

Date: 2026-07-21

## Verdict authority

Commit `1e92b5bb` adds a cycle-safe evidence-admissibility boundary.
Nested `cas_harness_research_shadow.*` payloads are rejected at fleet and
audit verdict ingress. Unknown schemas produce unavailable proof chips rather
than inferred proof. Worker-supplied filenames, readiness labels, or
verification strings do not authorize a verdict. Generic fleet evidence stays
`FLAG_FOR_HUMAN_REVIEW` unless an authenticated verifier-authority receipt
exists.

Historical packet bytes remain preserved. The boundary changes decision
authority, not history.

The authenticated verifier-authority receipt protocol is still `OPEN`.
Stage-9 authority requires a separate scoped review. No live deployed smoke was
performed for this continuation.

## Research isolation

All J-Space, Jacobian-lens, CJT Bias/RPM, and CAS-Ohm artifacts remain
`SHADOW` with `verdict_influence=NONE` and `NOT_LICENSED`. They
cannot create a proof chip, suppress review, or create customer
`ACCEPT`.

The exact-token canary's maximum result is `TECHNICAL_CANARY_PASS`. It does
not authorize a semantic, prompt-injection, output-control, universality, or
300B claim.

## Integrity and distribution

- Final source bundle SHA-256:
  `E4E971A7990A4AEFD1EC550A4FFD870256301342EB7F18C6397D236D64FFFB5E`.
- Intermediate source bundle SHA-256:
  `F5756D1D972F2EBA5A998C090BEECEC9A4F5A2591E923503C9F7A6BD9515E88B`.
- Pinned Jacobian-lens bundle SHA-256:
  `1DA9F6D9EF4E185615C1BD7A5B548C1FCAC513340C24B1DD8DE68115FC793E82`.
- Final Bias/RPM/Ohm contract SHA-256:
  `C39EB46BCC5AA3D482C9A53EC82FBF4362058F56817B0C3E644D3FD9636BA4FE`.

Both source bundles and the dependency bundle passed structural Git bundle
verification and contain complete history.

A text-content pattern scan configured to report filenames only found zero
high-signal credential-pattern files. The continuation contains zero `.git`,
`__pycache__`, `.pytest_cache`, virtual-environment,
`node_modules`, model-cache, or similar runtime-cache directories.
No `.env` file, private key, provider token, or browser session was
intentionally copied.

This pattern scan is not a specialized Git-history secret audit. Because the
bundles contain history, keep this continuation internal until a dedicated
history scanner and distribution review clear it.

The handoff manifest and SHA-256 inventory are tamper-evident local checks.
They are not a digital signature, independent escrow, WORM retention, or
third-party timestamp. Those evidence-integrity gates remain `OPEN`.
