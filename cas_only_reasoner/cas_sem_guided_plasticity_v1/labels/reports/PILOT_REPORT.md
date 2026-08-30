# LABEL PHASE 0C -- DEVELOPMENT-ONLY PIPELINE FIXTURE REPORT

Status: **SYNTHETIC_PIPELINE_FIXTURE_PASS -- software behavior only, not claim-bearing.**
No neural probe, no hidden-state extraction, no protected evaluation, no model calls,
no GPU. Deterministic. The dev senses were authored to exercise the candidate rules,
so agreement here validates the SOFTWARE, not the rules' semantics.

- claim-bearing packet count: **0** (asserted zero)
- rule table (CANDIDATE, awaiting owner approval) sha256: `f6db8a8c1d6148491ffbd976d461a794b02d86e3daa17c803863ec6e3b586d07`
- dev resource sha256: `38649fe0acf4c17e0229750291534c04cc75970135abda1c516d6fe9bf36b8bc`

## Counts
- resource senses: 46
- RESOURCE_RULE_DERIVED (candidate, non-claim-bearing): 40
- abstained: 6
- controlled template fixtures (retired generator): 40
- all packets: 86

## Metrics
- automatic-label coverage (resource): 0.8696
- abstention rate (resource): 0.1304
- source-verification failure rate: 0.0
- cross-class integrity ok: True
- model-committee disagreement rate: not_exercised_in_dev_pilot (no live model committee; engine emits candidates only)
- owner-audit disagreement rate: not_applicable (queue is DEV_AUDIT_FIXTURE_ONLY; owner not asked to judge it)
- duplicate-item consistency: not_applicable (queue is DEV_AUDIT_FIXTURE_ONLY)

## Development-fixture checks (NOT scientific evidence)
- Development-fixture check ONLY. Agreement with the author of synthetic fixtures is NOT independent validity evidence and is EXCLUDED from scientific reporting.
- accepted class mismatch: 0
- decoy accepted instead of abstaining: 0
- abstain-reason mismatch: 0
- per-rule: {'CAS-N2': {'accepted': 10, 'class_mismatch': 0}, 'CAS-N3': {'accepted': 10, 'class_mismatch': 0}, 'CAS-N6': {'accepted': 10, 'class_mismatch': 0}, 'CAS-N8': {'accepted': 10, 'class_mismatch': 0}}

## Owner workload
- production audit is risk-based (~48 visible judgments + high-risk items), per OWNER_AUDIT_PROTOCOL.md; the dev queue below is a fixture, not owner work
- dev fixture queue items (do NOT judge): 70
- mapping rules to approve: 4
- single-owner audit; NOT independent human inter-rater validation

## Boundary
This run demonstrates the deterministic label BACKBONE only. Zero packets are
claim-bearing. Gold labels can only be created by owner_gated_promotion.py with an
owner-signed approval, an audit receipt, and matching digests. The claim-bearing
readout study is NOT begun.
