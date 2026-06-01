# Stage 9 40E Evidence Packet

- Schema version: `cas_harness_stage9_40e_evidence_packet.v1`
- Trace ID: `pythia-160m-stage9-40e-readout-20260531`
- Run ID: `pythia-160m-stage9-40e-20260531`
- Method: `S9-40E-ORIGINAL-BASELINE-READOUT`
- Verdict: `ACCEPT`

## Tier Status

| Tier | Status |
| --- | --- |
| Model proof | present |
| Readout proof | present |
| Baseline proof | present |
| Causal proof | present |
| Control proof | present |
| Output/bridge proof | present |
| Verifier | present |

## Proof Chips

| Proof | Status | Detail |
| --- | --- | --- |
| Model proof | present | Model identity/hash evidence is recorded in the packet. |
| CAS readout | verified | Corrected Stage 9 40E hidden-state readout beats text and shuffled controls. |
| Causal proof | verified | Subspace ablation/control evidence is recorded for the Stage 9 40E readout. |
| Control proof | verified | Candidate cover/control evidence is recorded for the Stage 9 40E run. |
| Output proof | verified | Eta-to-epsilon readable bridge output evidence is recorded. |
| Packet proof | present | Evidence Packet schema, trace ID, and source artifact hashes are recorded. |

## Baseline Proof

| Metric | Corrected value |
| --- | ---: |
| Hidden readout | 95.625% |
| Confirmed text | 49.241071% |
| Text-hash baseline | 50% |
| Shuffled-label mean | 2.619% |
| compact-gloss v0 | blocked at 100% text-only |


## Causal Proof

| Metric | Value |
| --- | ---: |
| Original hidden readout | 91.7188% |
| After learned-subspace ablation | 47.7232% |
| True disruption | 43.9955 pp |
| Random same-rank mean disruption | 0.087054 pp |
| Random same-rank max disruption | 0.602679 pp |
| Chance baseline | 2.5% |
| Guard status | passed |

## Control / Cover Proof

| Metric | Value |
| --- | ---: |
| Candidate classes | 40 |
| Selected layer | 3 |
| Top-k neurons per class | 8 |
| Caveat | Cover discovery is candidate-only until matched ablation validates targeted drops against random same-size and wrong-class controls. |

## Output Bridge Proof

| Metric | Value |
| --- | ---: |
| Cases | 80 |
| Selected element accuracy | 0.95 |
| Probe-readable delta vs none | 1.53484 |
| Probe-readable minus partner | 3.22633 |
| Gold-readable delta vs none | 1.71709 |
| Probe-raw delta vs none | -0.000626 |
| Probe-readable gate | passed |

## Verifier Decision

| Field | Value |
| --- | --- |
| Verdict | `ACCEPT` |
| Confidence | 0.95 |
| Source | stage9_40e_packet_verifier |
| Scope | stage9_40e_validation_packet |
| Reason | all_stage9_40e_validation_gates_passed |

## Rationale

All required proof chips are pass-ready and the attached verifier returned `ACCEPT` with confidence 0.95.

## Caveats

- ACCEPT/SUPPRESS requires pass-ready proof chips and an attached explicit verifier decision.
- Readout-only packets preserve the corrected PR #102 baseline but remain flagged for human review.
