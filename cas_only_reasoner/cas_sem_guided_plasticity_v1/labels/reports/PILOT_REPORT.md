# LABEL PHASE 0B -- DEVELOPMENT-ONLY PILOT REPORT

Status: **DEVELOPMENT_ONLY, not claim-bearing.** No neural probe, no hidden-state
extraction, no protected evaluation, no model calls, no GPU. Deterministic.

- rule table sha256: `5599780d2c1e3ffcb0cc71289f0a475d3a712465fdafa37147b8b0ebc256eb86`
- dev resource sha256: `740d72da8a6f5cca347ef816b40abcb3952e4a11c09b0c6896497c3d78dc5c24`

## Counts
- resource senses: 46
- accepted RESOURCE_GOLD: 40
- abstained: 6
- construction gold (Tier A): 40
- all packets: 86

## Metrics
- automatic-label coverage (resource): 0.8696
- abstention rate (resource): 0.1304
- source-verification failure rate: 0.0
- cross-class integrity ok: True
- model-committee disagreement rate: not_exercised_in_dev_pilot (no live model committee; engine is authority)
- owner-audit disagreement rate: pending_owner_judgment
- duplicate-item consistency: pending_owner_judgment

## Self-consistency vs author intent (sanity only, NOT authority)
- accepted class mismatch: 0
- decoy accepted instead of abstaining: 0
- abstain-reason mismatch: 0
- per-rule: {'CAS-N2': {'accepted': 10, 'class_mismatch': 0}, 'CAS-N3': {'accepted': 10, 'class_mismatch': 0}, 'CAS-N6': {'accepted': 10, 'class_mismatch': 0}, 'CAS-N8': {'accepted': 10, 'class_mismatch': 0}}

## Projected human workload
- owner audit queue items: 70
- mapping rules to approve: 4
- hidden duplicates: 4
- single-owner audit; NOT independent human inter-rater validation

## Boundary
This pilot demonstrates the deterministic label BACKBONE only. It establishes no CAS
claim. The claim-bearing readout study is NOT begun. Awaiting owner approval of the
four CAS class rules, the frozen production resource, and a signed phase-0 record.
