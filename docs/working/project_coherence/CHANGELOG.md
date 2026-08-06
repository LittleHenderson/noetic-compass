# Project Coherence Phase 0 changelog

All dates use the repository's working timezone. This changelog records control-package changes, not product releases.

## 2026-08-05 - Gate 5 retained evidence and same-run verifier hardening

### Added

- An additive raw build/security receipt and ten exact retained payloads: the
  original OCI index, platform/config/attestation records, BuildKit history,
  SPDX and SLSA statements, plus a current direct Scout 1.21 SPDX and SARIF
  report. The historical v0.2 issuance-time receipt remains byte-unchanged and
  continues to record that those raw payloads were unavailable at issuance.
- A local Windows runner lock over three interpreter files, 508 exact files
  owned by seven pytest-support distributions, and three `.pth` files disabled
  at startup by `-I -S`. Pytest and explicit-plugin origins are checked against
  the exact file lock before import. The child hashes and parses the same
  identity-checked lock byte buffer.
- Same-process collection/start/finish and exact setup/call/teardown/subtest
  receipts for each admitted suite, with ephemeral digests for executed node
  IDs, outcomes, locked import origins, pre-test module endpoints, and final
  module endpoints.
- Descriptor-bound repository observations that reject symlink/reparse path
  components and hardlinked leaves, compare pathname/open-handle/ancestor
  identities, separately preserve the non-self-hashed manifest identity, and
  recheck the integrated Gate 5/Gate 4/history surface after child execution.
  Ancestor checks bind stable structural identity (device, inode, type, link,
  and reparse state) while intentionally excluding directory size/timestamps,
  which can change when unrelated Codex work occurs outside the worktree.

### Verified bounded receipts

- The intended manifest surface contains 340 hash-bound artifacts, including
  298 syntax-checked Python files, while retaining the exact 537-file historical
  recovery and transitive Gate 4 dependency.
- Harness v2 kernel/history/verifier: 119 tests and 61 subtests, comprising 94
  active kernel tests, 4 historical-recovery tests, and 21 Gate 5 verifier
  red-team tests. Live worker: 364/364; API/launcher/fleet/state: 76/76; focused
  numeric red team: 32/32. These are local same-process engineering receipts,
  not scientific or independently attested execution.
- The direct Scout payload reports 0 critical, 0 high, 3 medium, and 4 low
  findings. Current Ubuntu-source triage leaves six records vulnerable or
  fix-deferred and identifies one scanner/vendor conflict because the exact
  scanned `dpkg` version is vendor-fixed.

### Preserved open boundaries

- Gate 5 remains `OPEN / NOT_STARTED / Ring 4 / NOT LICENSED / HELD / NOT
  FROZEN`; `G5-ENGINEERING-002` remains `OPEN_ENGINEERING` and
  `G5-ENGINEERING-003` remains `OPEN_SECURITY`.
- The endpoint module inventory contains only surviving `sys.modules` file
  origins and maps cache paths to source. It does not capture
  transient/unloaded/dynamic execution, exact loader-executed bytecode,
  unresolved/deleted origins, native-loader dependencies, descendant
  processes, or files absent from upstream distribution `RECORD` inventories.
- Complete standard-library/test/native/process closure, an immutable and
  independently attested snapshot, trusted time/WORM ordering, privileged ABA
  resistance, independent reproduction, real GPU execution, worker-to-kernel
  integration, scientific validation, licensing, product authority, and
  disclosure authority all remain open.

## 2026-08-05 - Gate 5 successor dependency/container candidate hardening

### Added

- A successor v0.2 dependency/container candidate receipt binding the repository
  build controls, 73-distribution lock, exact worker application tree, recorded
  OCI identities, exact five-file Pythia identity, offline CPU engineering
  canary, native dependency preflight, and fail-closed runtime probes.
- Complete Gate 5 direct-or-transitive closure over 325 artifacts, including
  every regular file in the admitted kernel/worker roots, the complete API
  source/resource tree used by the launcher/fleet/state receipt, pytest
  discovery controls, and the unchanged 537-file historical recovery.
- Repository-local rejection of `__pycache__`, bytecode, native-extension, and
  archive shadows before child tests, plus retained red-team checks for forged
  scan status, authority promotion, OCI/source/lock drift, missing controls,
  external-evidence replayability, and post-test rehash ordering.

### Verified bounded receipts

- Harness v2 kernel/history/verifier: 113 tests and 61 subtests, with 94 active
  kernel tests, 4 historical-recovery tests, and 15 verifier red-team tests.
- Live worker: 364/364; API/launcher/fleet/state: 76/76; focused numeric red
  team: 32/32. The worker and API receipts are
  `LOCAL_UNATTESTED_HOST_REGRESSION`: node-ID hashes come from separate
  collect-only subprocesses and do not receipt the actual executed-node set.
- The integrated static replay binds the unchanged historical v0.1
  model/dependency record and composes the still-OPEN Gate 4 dependency.

### Preserved open boundaries

- Gate 5 remains `OPEN / NOT_STARTED / Ring 4 / NOT LICENSED / HELD / NOT FROZEN`.
  `G5-ENGINEERING-003` remains `OPEN_SECURITY`.
- BuildKit SPDX/SLSA and Docker Scout facts are
  `SELF_REPORTED_LOCAL_OBSERVATION_ONLY`: raw payloads were not retained, are
  not repository replayable, and have no independent trust root.
- The recorded package scan has 0 critical, 0 high, 3 medium, and 4 low unfixed
  findings; the direct filesystem scan is `INCOMPLETE / PENDING`.
- Mutable host/user-site runner integrity, same-run executed-node identity,
  authenticated read-only snapshots, hardlink/reparse/ABA resistance,
  independent reproduction, real GPU execution, worker-to-kernel integration,
  scientific validation, licensing, product authority, and disclosure authority
  remain open. The CPU canary was engineering preflight only and did not create
  an admitted experiment, Evidence Packet, or scientific result.

## 2026-08-04 - Gate 4 bounded software candidates and adversarial review

### Added

- Isolated CAS Core v8, CAS PCBA v8, and CAS-Ohm v1 research packages with 208
  focused tests in the integrated unittest receipt: Core 61, PCBA 82, and Ohm
  65. Focused pytest runs additionally exercised 19, 195, and 58 parameterized
  subcases respectively.
- A 53-criterion cross-domain Gate 4 review matrix with 20 explicitly open
  criteria, a human-readable adversarial review, exact candidate specifications,
  and a fail-closed integrated verifier that binds every source/test/control
  artifact plus the exact passing test-ID sets.
- A machine-readable five-board PCBA construct-coverage audit: four direct EBNF
  counterexamples and one bounded listing for which no direct counterexample was
  established. The defensible conclusion is corpus-level noncoverage.
- A machine-readable CAS-Ohm source audit preserving eight conflicts or
  under-specifications with exact source locators and conservative candidate
  rules.
- The integrated Gate 4 verifier passes against 54 hash-bound artifacts, all
  208 exact unittest IDs, the 11-record Ring-4 claim boundary, 53 review
  criteria with 20 open, the five-board PCBA audit, the eight-record Ohm source
  audit, and the integrated Gate 1 dependency chain. This is not a gate-close
  or release/admission claim.

### Corrected

- CAS Core now uses complete semantic identities, bounded type-injective
  canonicalization, exact-byte-backed registries, fresh isolated compiler replay,
  exact-type/primitive boundary comparisons, and structural decisions that can
  never grant authorization. Its v0.2 execution profile also serializes
  cooperating worker processes without retry, binds the finite lock policy and
  sanitized Windows architecture inputs, samples runtime identity before
  compiler execution without WMI or subprocess probing, and emits bounded
  hash/path-only transport and profile-difference diagnostics on failure.
- CAS PCBA now uses fixed versioned decimal arithmetic, exact tagged finite
  values, complete projector/simulation/DRC identities, sounder fuse and
  per-cycle feedback checks, provenance-validated result graphs, fixed research
  boundaries, and a hash-bound TKS adapter certificate.
- CAS-Ohm now binds complete profile/source/evidence identities, derives and
  replays network and operating assessments, enforces exact Q4 and role-aware
  resistance/residual rules, and separates structural research-packet
  completeness from authenticated Evidence Packet eligibility. Authenticated
  eligibility remains false without external authority and trusted time. Its
  canonical form also has an explicit 2,048-bit integer bound and normalizes
  host-runtime integer-conversion failures.
- Renamed the claim-ledger completeness header from the inaccurate
  `INITIAL_LOAD_BEARING_NONCLAIMS_ONLY` to
  `INITIAL_LOAD_BEARING_CLAIM_BOUNDARY_RECORDS`; the ledger contains empirical
  and product claim-boundary records and remains entirely Ring 4 / `NOT LICENSED`.

### Preserved open boundaries

- Gate 4 remains `OPEN / Ring 4 / NOT LICENSED / HELD / NOT FROZEN`.
- No test establishes canon acceptance, full semantic migration, hermetic
  toolchain closure, Python/Rust equivalence, complete CCDL/stateful semantics,
  live calibration, empirical validity, safety, peer review, product readiness,
  claim licensing, or public-disclosure authorization.
- The monolithic repository pytest collector still has older package-shadowing
  collisions; the integrated verifier uses exact isolated subprocess suites and
  binds their full test-ID sets.

## 2026-08-04 - Gate 0 identity correction and Gate 1 prototypes

### Corrected

- Reclassified the apparent active-compiler hash drift as a CRLF/LF serialization difference. Reproducible normalization of the current 248,859-byte CRLF checkout yields the exact 243,046-byte registry-bound LF Git blob and SHA-256 `8169188A...`; no substantive compiler drift was found.
- Updated the source-authority and migration records so raw-hash inequality is no longer a false Gate 0 blocker. Both raw and canonical content hashes remain required provenance.
- Corrected the census's pre-review ASOM expansion to the source-defined Starved, Aligned, Oversaturated, and Misaligned labels.
- Recorded five newly audited source conflicts rather than silently selecting semantics: CAS-Ohm scale/units, gain/network profiles, ASOM axes, PCBA grammar coverage, and the CSB safety-reference contradiction.

### Added

- Gate 0 candidate closure, baseline-freeze, standing-authority, and compiler-normalization receipts with a fail-closed verifier.
- Gate 0 bounded load-bearing term census covering 49 groups and 712 members across 22 hash-pinned sources while preserving 19 conflicts and every competing profile.
- Gate 1 v7.4 declaration-surface inventory and bounded corrigendum with 29 adjudicated correction records; every unlisted declaration remains OPEN by default.
- Gate 1 typed TKS v8 finite-function reference kernel, corrected deterministic-lift fixtures, fixed-order denotational shortlex prototype, ordered-input guards, bounded resource controls, and standard-basis lift functor tests.
- A pinned Lean 4.32.1 proof seed with exact source hashes, no project-specific axioms or `sorry`, a hardcoded `propext` allowlist, and explicit OPEN boundaries for all unformalized universal claims.
- Gate 1 Noetic Topos 2.0 transverse marked-context construction, finite witness presheaves, strict canonical cover provenance, a two-parent ACBE/RPM join derivation, schema-valid theorem/obligation ledgers, source verification, and executable model checks.
- A finite-context proof candidate and exhaustive 298-sieve certificate showing `M_A M_R ~= M_atom ~= M_R M_A` naturally on `PSh(L,Set)`; the product-site lift remains OPEN.
- A 23-entry integrated Gate 1 hash chain and verifier that composes the Phase 0, Gate 0, v7.4, typed TKS, Noetic, modality, and Lean receipts.
- Seven Ring 4 / `NOT LICENSED` Gate 4 claim records covering held-out CAS-Ohm response, effective resistance, gain composition, redundancy, residual localization, PCBA compiler conformance, and CSB safety-effectiveness boundaries.

### Clarified

- The Noetic successor's underlying topos is the ambient presheaf topos equipped with modalities; the broader `NoeSystem_2` tuple is a structured package, not itself a topos.
- The fully resolved finite context factor is only four independent legacy channels. It is a separation/provenance reference model, not yet a rich final Noetic Topos 2.0 semantics.
- The context-factor mark schema currently covers ACBE, RPM, and their joint refinement. Typed observational/product-site provenance remains OPEN.
- The Lean constant-lift module proves the exact vector expansion and noncontractivity counterexample. Its literal matrix/Gram values are not yet bridged to generic matrix, trace, or rank definitions.
- Derived Noetic cover JSON is accepted as evidence only after its complete parent derivation DAG resolves, rehashes, and recomputes successfully.

These are private research candidates. Gate 0 remains open, all successor research remains Ring 4, and no product claim or public disclosure is licensed.

## 2026-08-04 - v0.1 draft

### Added

- Draft Project Coherence Master Charter with four admission rings, seven research cells, six release gates, and a first-year execution sequence.
- Byte-identified source-authority matrix anchored to the owner-signed semantic registry and its approval receipt.
- Initial load-bearing symbol and terminology registry preserving the ten verbatim Noetic definitions and the World/Domain/Register, Foundation/Drive, and RPM type separations.
- Initial migration matrix with no inherited entries.
- Machine-readable theorem and claim record schemas.
- Initial theorem ledger and fail-closed empirical/product claim ledger.
- Chapter-by-chapter quarantine for *Ten Advances in Mathematics and Theoretical Computer Science*.
- Mathematical red-team report with explicit finite counterexamples and correction obligations.
- Primary-source literature and transfer audit with exact theorem/model conditions and citation labels.
- Draft open-vs-held disclosure boundary.
- Standard-library Phase 0 verification command.

### Corrected from the precursor analyses

- The primary Ten Advances manuscript is now `present`, not `unavailable`; its results remain manuscript claims pending independent review.
- The owner-supplied TKS v7.4 FULL_BEAUTIFUL PDF is a verified rendering of the registered FULL_BEAUTIFUL text, while the repository FULL_CORRECTED PDF is materially different and remains unregistered context.
- The owner-supplied Noetic Topos PDF is byte-identical to the registered eight-page rendering and is not a new version.
- CAS Harness v1.6 is historical and superseded, not the current product-readiness authority.
- The current PCBA baseline already uses mixed simplex addresses and explicitly warns against pure one-hot geometry; projector profiles are a proposed extension, not a correction of an absent representation.
- The proposed projector-capacity transfer omitted a load-bearing isometry/intertwining hypothesis and is recorded as a proof gap.
- ACBE and RPM cover clauses in the conservative Noetic Topos do not add coverage beyond jointly-surjective families; separate-topology triviality remains under final independent review.
- The inherited deterministic-lift norm bound, occupation trace/projector cluster, and several spectral/MVR claims fail explicit finite counterexamples and are blocked for corrigendum.
- Current axioms do not imply subcanonicity; a finite injection-category counterexample blocks bare representables as marked sheaf objects.

### Open blockers

- Charter owner review and explicit freeze decision.
- Final mathematical red-team report and theorem-by-theorem v7.4 audit.
- Independent verification of each Ten Advances proof and novelty claim.
- Twelve unresolved conflicts retained by the owner-signed semantic registry.
- Term-census, compatibility-profile, and remaining semantic-conflict closure work; the earlier compiler-drift item is resolved as a line-ending serialization identity.
- PCBA internal version-label ambiguity.
- Human and qualified-counsel review of the open-vs-held boundary.

No successor release, production-readiness claim, empirical license, public-disclosure decision, or theorem admission is made by this draft.
