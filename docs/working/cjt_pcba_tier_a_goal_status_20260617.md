# CJT/PCBA Tier-A Build — Goal Status

Generated: 2026-06-17
Goal: Build the buildable-now ("Tier A") CJT/PCBA evidence + visualization layer
recommended in `docs/working/cjt_pcba_cas_forex_ecosystem_fit_analysis_20260617.md`,
plus shared helpers, with honest claim boundaries.
Goal complete: `true` (Tier-A scope)
Current boundary honest: `true`

## What Was Built

| Item | Module | Status |
|---|---|---|
| Shared CAS state-surface helpers | `cas_forex/cas_state_utils.py` | DONE |
| A-1 CJT diagnostic mapper | `cas_forex/cjt_diagnostics.py` | DONE |
| A-3 Cognitive Rule Check (CRC) linter | `cas_forex/crc_linter.py` | DONE |
| A-2 CJT circuit-view renderer | `cas_forex/cjt_circuit_view.py` | DONE |
| A-4 Differential-pair matched-control harness | `cas_forex/cjt_differential.py` | DONE |
| Tier-A tests | `tests/test_cjt_pcba_tier_a.py` | DONE (23 tests) |

Pre-existing foundation reused (already in repo, not built here): `schemas/cjt.py`,
`schemas/pcba.py`, `cjt_syntax.py` (CJT<> parser), `pcba_syntax.py`,
`pcba_compiler.py`, `cjt_readiness.py`, `pcba_readiness.py`, and the
`cjt_diagnostics`/`pcba_diagnostics` fields already present on
`ForexEvidencePacket`.

## Test Evidence

- `python -m pytest tests/test_cjt_pcba_tier_a.py -q` → 23 passed.
- `python -m pytest tests -q` → **200 passed** (23 new + 177 existing; zero regressions).
- Note: a stale `cas-forex/tmppcba-pytest/` directory (pre-existing, permission-locked)
  breaks bare `pytest` collection; scope to `tests/` to run the suite.

## CRC Rule Catalog (static design-time checks)

| Code | Severity | Catches |
|---|---|---|
| CRC-001 | WARN | Bias terminal is not a CAS state (modulation unverifiable) |
| CRC-002 | ERROR | Bias domain too low-precedence to modulate the cause→effect path |
| CRC-003 | ERROR | Short circuit: cause→effect skips a domain-descent tier |
| CRC-004 | WARN | Reverse-flow bypass: feedback ascends precedence without bridging |
| CRC-005 | ERROR | Push-pull gain divergence \|β_a − β_b\| > 4 |
| CRC-006 | WARN | CJT cascade depth > 7 stages |
| CRC-007 | WARN | Gain firewall: β > 10 (hypersensitive) or < 0.1 (constitution-ignoring) |
| CRC-008 | ERROR | Fuse installed downstream of the stage it protects |

## Claim Boundaries (honest split)

LICENSED (locally, scoped to this Tier-A layer):
- Evidence-only CJT diagnostics that explain / `SUPPRESS` / `FLAG_FOR_HUMAN_REVIEW` / `LIVE_LOCKED`.
- Static structural circuit linting (CRC) and circuit-view rendering.
- Differential-pair divergence as a heuristic review signal.

NOT LICENSED / OPEN (unchanged — this build does not touch them):
- Runtime-safety guarantee from a CRC pass. **A well-formed circuit is NOT proven
  safe at runtime.** CRC refuses malformed designs; it does not bless behavior.
- Live-trading permission, broker `ACCEPT` (structurally impossible — no ACCEPT
  enum value; schema validators block `can_create_broker_accept` /
  `can_unlock_live_trading`).
- Compiler-enforced safety as a general AI-safety claim.
- Prompt-injection prevention/removal/reversal; model-internal W0 detection
  (the Qwen W0 gate FAILED: hidden BA 0.745 < 0.75; margin 0.094 < 0.15).
- Governance/regulatory proof.

## Not In This Build (Tier B / C — remain OPEN)

- `CJT<>` production compiler authority (parser exists; semantics/IR review OPEN).
- β / operating-region measurement from real generation traces.
- `CjtPredictionHead`, CJT attention gating, CABS typed-fiber routing (CAS-Native research).
- CCDL parser + SVG schematic renderer + audio sonification.
- CCBs as executable, incident-validated boards (currently schema enums + diagnostics).

## Summary

Tier-A is the evidence-and-visualization layer plus the static "Cognitive Rule
Check" linter. It improves audit clarity and refuses malformed cognitive circuit
designs, while keeping every higher-authority claim (runtime safety, live
trading, broker ACCEPT, governance) `OPEN` / `NOT LICENSED`.
