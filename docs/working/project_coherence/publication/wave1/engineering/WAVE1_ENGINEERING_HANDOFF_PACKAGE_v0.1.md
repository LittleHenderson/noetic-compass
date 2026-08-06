# Project Coherence Publication Wave 1 — Engineering Handoff Package

**Artifact status:** `DRAFT / OPEN / Ring 4 / NOT LICENSED / HELD`

**Lane:** CAS PCBA 8 and CAS-Ohm 1 publication engineering

**Base commit:** `a1cd990109e7561dfd03949bf0e1653461c7ae44`

**Branch:** `codex/project-coherence-publication-engineering`

**Internal cross-review:** `OPEN`

**External specialist review:** `OPEN`

**Public disclosure:** `NOT AUTHORIZED`

## 1. Handoff outcome

This lane delivers a source-bound publication delta over the existing Gate 4
engineering candidate. It does not recreate or change CAS Core v8, CAS PCBA v8,
CAS-Ohm v1, TKS v8, Noetic Topos 2.0, Gate 4, Gate 5, the shared registries, or
the production TODO.

The two narrative products are:

1. a research draft for charter Paper 6, **CAS PCBA 8: Adaptive Cognitive
   Circuit Engineering**; and
2. **CAS-Ohm 1.0: A Profile-Specific Experimental Response and Calibration
   Model**, explicitly labeled a provisional technical report rather than a
   charter-approved standalone paper.

The package also supplies one shared claim/assertion matrix, evidence map,
citation ledger, unresolved-obligations list, and a non-self-hashing artifact
manifest.

## 2. Delivered files

| File | Purpose |
|---|---|
| `CAS_PCBA_8_ADAPTIVE_COGNITIVE_CIRCUIT_ENGINEERING_DRAFT_v0.1.md` | Charter Paper 6 research draft |
| `CAS_OHM_1_PROVISIONAL_TECHNICAL_REPORT_v0.1.md` | Provisional CAS-Ohm report; not an approved extra charter paper |
| `WAVE1_ENGINEERING_CLAIM_ASSERTION_MATRIX_v0.1.json` | Theorem dependency, source finding, software assertion, empirical hypothesis, product-claim, and open-obligation states |
| `WAVE1_ENGINEERING_EVIDENCE_MAP_v0.1.json` | Exact source inventory, hashes, evidence clusters, and bounded-receipt limits |
| `WAVE1_ENGINEERING_CITATION_LEDGER_v0.1.json` | Internal source citations and 15 primary technical/standards sources with exact URLs/DOIs |
| `WAVE1_ENGINEERING_UNRESOLVED_OBLIGATIONS_v0.1.json` | 27 explicit open obligations and the evidence required to close each |
| `WAVE1_ENGINEERING_HANDOFF_PACKAGE_v0.1.md` | Lead-editor and reviewer handoff |
| `WAVE1_ENGINEERING_ARTIFACT_MANIFEST_v0.1.json` | Exact hashes of every lane artifact except itself |

The manifest intentionally excludes its own hash. The lane commit is the Git
commit containing this package and should be recorded by the lead after review
or integration; embedding it here would create a self-reference.

## 3. Source lock

The publication artifacts are bound to the exact base commit and to the
following high-level evidence anchors:

- Project Coherence charter SHA-256
  `B87B2E2B4CC4B10C76EE4AA6EA09094572B2A1008E474475E8F642836B83D2BE`;
- Gate 4 manifest SHA-256
  `49102F9BCBAA2345804F5EE3CA708FD6A84E83F8CF5ABB51E6612893A090D57B`;
- Gate 4 review matrix SHA-256
  `44DD99A847DA742C3EBEBC06D64452A6868421EE12129E789D1CC790DAE41B74`;
- CAS PCBA v8 source collection aggregate
  `9B4C8128C10E330570F0568999F608789A8B03ABDB25D9EF01E3B9E3A44D83F0`;
- CAS-Ohm v1 source collection aggregate
  `A304C716AEF5376F26FE09AD82A3B815454CA60D247735972C196B7F935B104F`;
- CAS Core v8 source collection aggregate
  `2604D0465356A2AA5B00FD48305337C3AC41DF18DE9B7238E3B56854AED9670B`;
- PCBA CCDL coverage record SHA-256
  `5BB797EC37CF289B4CBE8DF1256F07425C3DA13AA8CF2DA03E47DFCE1CB46808`;
- CAS-Ohm conflict record SHA-256
  `F24BD64A21B944724993AC9C3A0996293FE6242E4F724D4B104DBAA7A6505507`;
  and
- Gate 5 preregistration/Evidence Packet v2 specification SHA-256
  `F2803B44FF7236762D491A3B249FF13C4CB8D9F336CE19F223F9F716E9A70D2D`.

The evidence map contains every member path, hash, and byte count for the three
candidate source directories and three focused-test directories, plus the exact
control-artifact inventory.

## 4. Claims the lead may preserve

The drafts support the following narrow statements:

- The exact Gate 4 Python candidates implement and regression-test declared
  typed software contracts.
- The PCBA candidate has deterministic DRC, trace/provenance, geometry, and
  narrow finite-adapter behavior for its admitted profiles.
- The CAS-Ohm candidate has typed quantity/evidence, calibration identity,
  exact Q4, structural network, non-identifying residual, and fail-closed
  eligibility behavior for its admitted profiles.
- The source audit establishes a corpus-level CCDL/EBNF mismatch with four
  direct counterexamples among five audited boards.
- The source audit and known-fault fixture establish that `sat=0.1` cannot reach
  `threshold=0.9` under the stated clamp semantics.
- The CAS-Ohm sources retain eight exact conflicts or under-specifications.
- The Gate 4 receipt is bounded software evidence, not an experiment.

Formal Mathematics Paper 3 is the sole mathematical authority for the
projector Gram-kernel and capacity-transfer statements. Its frozen lane source
is commit `3c8491db6f5559cf090909d9de0efa03d924f53f`, SHA-256
`679E1119CB084D9A429F6FCC26374B18FF1FB6252D7374631975B4FF56BAEFC4`.
The engineering records are read-only summaries: normalized overlap requires
common rank `d > 0`, and the capacity transfer remains
`PROOF_GAP / IN_REVIEW / Ring 4`.

## 5. Claims the lead must not promote

The following remain prohibited or open:

- CAS quantities as physical voltage, current, resistance, charge, flux, power,
  or telemetry;
- complete CCDL conformance;
- cognition/transistor identity;
- a projector profile as a validated latent cognitive subspace;
- causal gain, causal resistance, redundancy, or hidden-cause localization;
- stateful, adaptive, memristive, hysteretic, or material dynamics as already
  implemented or validated;
- live calibration, cross-model comparability, safety effectiveness,
  certification, clinical suitability, or regulatory compliance;
- authenticated Evidence Packet eligibility;
- product readiness, customer efficacy, canon admission, license, or public
  disclosure;
- internal adversarial review as external independent review; and
- draft creation as authorship or peer-review acceptance.

## 6. Cross-review assignments

The lead should route stable hashes, not mutable filenames alone.

### Formal-math reviewer

Review:

- the `StateLiteral -> NDCell` many-to-one statement;
- the mixed-simplex and Fisher-Rao description;
- the optional projector-kernel boundary;
- the capacity-transfer proof-gap wording; and
- the finite-arrow/endomap/semigroupoid distinctions.

Reject any sentence that turns a structural adapter into a CAS semantic theorem.

### Category/sheaf reviewer

Review:

- the ambient-versus-resolved evidence wording;
- the claim that a marked cover does not prove a measurement true;
- the treatment of measurement records as external evidence; and
- any use of restriction, gluing, or sheaf terminology.

Reject any sentence that treats provenance or gluing structure as empirical
truth or authority.

### Systems/engineering reviewer

Review:

- exact DRC coverage and limitations;
- graph-cycle and threshold-bound descriptions against the code;
- simulator/provenance claims;
- CCDL coverage and CSB source locators;
- the structural-only status of CAS-Ohm networks; and
- the distinction between tests, verification, and validation.

### Experimental/causal reviewer

Review:

- split separation and circularity rejection;
- uncertainty and model discrepancy;
- controls and falsifiers for the five registered hypotheses;
- non-identifiability of residuals;
- the causal-language quarantine; and
- the provisional nonphysical memristive state equation.

Reject physical or causal interpretation that lacks an explicit model and
qualifying intervention evidence.

### Claim-language and disclosure reviewer

Review every abstract, conclusion, table caption, and summary against the shared
claim matrix. Confirm that all artifacts remain private and held.

## 7. Suggested editorial integration sequence

1. Freeze this lane commit and compute/verify the lane manifest.
2. Run first-wave cross-review against the frozen hashes.
3. Resolve comments in this lane or a lead-owned integration branch; do not edit
   shared registries from a specialist branch.
4. Recompute the artifact manifest after every accepted revision.
5. Reconcile notation with the formal-math and category/sheaf lanes.
6. Decide whether CAS-Ohm remains a technical report or requires a charter
   amendment.
7. Keep empirical sections as preregistered methods until qualifying Evidence
   Packets exist.
8. Commission external review only after internal cross-review and source locks
   stabilize.
9. Make authorship, venue, disclosure, and submission decisions through explicit
   human governance.

## 8. Validation checklist for integration

- All JSON files parse with duplicate-key rejection.
- Every JSON `entry_count`, `obligation_count`, and source count matches the
  actual array length.
- Every listed repository source hash and byte count matches the base commit.
- Every artifact listed by the lane manifest matches its bytes.
- The manifest does not list itself.
- Every Markdown artifact contains the exact status label.
- No draft calls model quantities physical voltage/current/resistance.
- No known-fault or synthetic test is described as an experiment.
- No software test is described as empirical, causal, safety, clinical,
  regulatory, product, canon, license, disclosure, or peer-review evidence.
- The five CAS-Ohm empirical claims remain open and without an Evidence Packet.
- Gate 5 remains `OPEN / NOT_STARTED / Ring 4 / NOT LICENSED / HELD / NOT
  FROZEN` in all downstream descriptions.
- Cross-review and external review remain open until actual review receipts are
  present.

## 9. Residual obligations

The machine-readable obligations file retains 27 open items. The critical path
is:

1. internal cross-review and source reconciliation;
2. complete CCDL grammar and state/time profiles;
3. hermetic and independent software reproduction;
4. Gate 5 integration for preregistered calibration/response experiments;
5. independent numerical audit and replication;
6. causal, safety, clinical, regulatory, authority, and product gates as
   separately scoped work; and
7. owner/Integration Board/counsel decisions for canon, authorship, publication,
   and disclosure.

No GPU or RunPod execution occurred in this lane. Publication drafting and
software/source verification did not require it.

## 10. Handoff boundary

This package is complete as a Wave 1 engineering draft handoff, not as a
scientific or publication-complete result. The lead may integrate it after
hash-bound review. Nothing in this package changes any Gate 4 or Gate 5
disposition or licenses a claim.
