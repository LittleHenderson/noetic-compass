# Stage 9 40E Evidence Packet

- Schema version: `cas_harness_stage9_40e_evidence_packet.v1`
- Trace ID: `stage9-40e-original-baseline-readout-20260527`
- Run ID: `gpt-neox-20b-stage9-original-40e-20260527`
- Method: `S9-40E-ORIGINAL-BASELINE-READOUT`
- Verdict: `FLAG_FOR_HUMAN_REVIEW`

## Tier Status

| Tier | Status |
| --- | --- |
| Model proof | present |
| Readout proof | present |
| Baseline proof | present |
| Causal proof | present |
| Control proof | present |
| Output/bridge proof | missing |
| Verifier | missing |

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
| Original hidden readout | 95.625% |
| After learned-subspace ablation | 66.8973% |
| True disruption | 28.7277 pp |
| Random same-rank mean disruption | 0.06808 pp |
| Random same-rank max disruption | 0.267857 pp |
| Chance baseline | 2.5% |
| Guard status | passed |

## Control / Cover Proof

| Metric | Value |
| --- | ---: |
| Candidate classes | 40 |
| Selected layer | 2 |
| Top-k neurons per class | 8 |
| Caveat | Cover discovery is candidate-only until matched ablation validates targeted drops against random same-size and wrong-class controls. |

## Rationale

Merged packet is review-only because required proof tiers are missing: output_bridge, verifier.

## Caveats

- This Stage 9 40E merger scaffold is not an ACCEPT verdict.
- This Stage 9 40E merger scaffold is not a SUPPRESS verdict.
- Final ACCEPT/SUPPRESS requires present causal, control, and output/bridge proof tiers plus an attached verifier decision.
- Readout-only packets preserve the corrected PR #102 baseline but remain flagged for human review.
