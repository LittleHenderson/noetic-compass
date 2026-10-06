# Project Coherence Gate 4 candidate

**Status:** `OPEN / RING 4 / NOT LICENSED / HELD / NOT FROZEN`

**As of:** 2026-08-04

Gate 4 covers the isolated research candidates for CAS Core v8, CAS PCBA v8,
and CAS-Ohm v1. It does not modify the active CAS v7.7 compiler, production
runtime, product claim ledger, CAS Harness routes, or any public artifact.

## Bound baselines

| Source | Exact identity | Authority boundary |
| --- | --- | --- |
| Active CAS v7.7 Python compiler | raw CRLF `065DC4384F7F52D1D8A081DC2D62AF69980F1F6EA9BF9099D22DE776CE05DF87`; canonical LF `8169188AD73DF8FC3CA709731B3FB4EA07B2513D38D69CF66D22D64CFE88FF4C` | Operational compatibility input only; cannot override locked semantics or authorize a claim. |
| CAS PCBA Engineer, 743 pages | `294320B39FA521EAC086E99E2D9DB913E2B6CFF0754FF82DB1EF966424566274` | Engineering reference by date-plus-hash, not a safety certification, complete compiler, or telemetry source. |
| CAS-Ohm Quantification Guide v0.1 | `89AE13C0A5D6208E328E9EDC55F816609BB172076CC13093DCCCCF418145CE64` | Experimental response-model proposal only. |
| CAS-Ohm operationalization addendum v0.1 | `0B62BBC66828A273E5458CC4D98EEE9B341554A474CCACB6387B209B5F0BE5E5` | Experimental measurement proposal; zero-instrumentation records are calibration exercises, not Evidence Packets. |
| PCBA Appendix I CAS-Ohm companion | `9FFFAC3E16B43C6D809ECE913FD8C09E40C65F60F3B4BE693F45D35EC4E6AC45` | Engineering calibration companion; design values remain distinct from measurements. |
| Gate 1 dependency chain | SHA-256 recorded in `GATE4_ARTIFACT_MANIFEST_v0.1.json` | Typed TKS v8 and Noetic Topos 2 remain open reference candidates. |

## Gate effect

The passing Gate 4 verifier proves only that the listed source identities,
candidate code, deterministic fixtures, tests, and conservative status fields
match the manifest-bound bytes. It does not establish:

- semantic canon acceptance;
- mathematical equivalence between legacy and successor profiles;
- physical or cognitive validity of the PCBA/Ohm analogies;
- calibration on a live model;
- safety, regulatory, clinical, or product readiness;
- claim licensing; or
- public-disclosure approval.

The source audit found adverse evidence that is deliberately preserved:

1. the first CAS Core candidate trusted self-authored receipts, mutable records,
   and unbound imports;
2. the published PCBA EBNF does not cover the five-board reference corpus (four
   direct counterexamples; one bounded listing without a direct counterexample),
   and the CSB example cannot trip its downstream fuse under its own saturation
   value; and
3. the CAS-Ohm sources disagree on scales, units, full-scale definitions, gain
   profiles, network rules, and the interpretation of ASOM.

These defects are regression targets and migration records, not hidden edits to
the historical sources.

## Candidate artifacts

- `CAS_CORE_V8_CANDIDATE_SPEC_v0.1.md`
- `CAS_PCBA_V8_SOURCE_AUDIT_AND_SPEC_v0.1.md`
- `CAS_OHM_V1_SOURCE_AUDIT_AND_SPEC_v0.1.md`
- `PCBA_CCDL_CONSTRUCT_COVERAGE_v0.1.json`
- `CAS_OHM_SOURCE_CONFLICT_EVIDENCE_v0.1.json`
- `GATE4_REVIEW_MATRIX_v0.1.json`
- `GATE4_ADVERSARIAL_REVIEW_v0.1.md`
- `GATE4_ARTIFACT_MANIFEST_v0.1.json`
- `src/cas_core_v8/` and `tests/cas_core_v8/`
- `src/cas_pcba_v8/` and `tests/cas_pcba_v8/`
- `src/cas_ohm_v1/` and `tests/cas_ohm_v1/`
- `scripts/verify_project_coherence_gate4.py`

## Closure boundary

Gate 4 remains open until the master charter's conditions close, including
independent specialist review, exact compiler/dependency closure, immutable and
trusted claim authority, declared PCBA grammar conformance, trace-emitting
known-fault diagnosis, calibrated held-out Ohm experiments, and accepted
migration/compatibility profiles. No passing software fixture can close those
external or empirical obligations by itself.
