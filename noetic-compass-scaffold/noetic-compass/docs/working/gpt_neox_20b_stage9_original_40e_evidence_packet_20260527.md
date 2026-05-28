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
| Causal proof | missing |
| Control proof | missing |
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

## Rationale

Merged packet is review-only because required proof tiers are missing: causal, control, output_bridge, verifier.

## Caveats

- This Stage 9 40E merger scaffold is not an ACCEPT verdict.
- This Stage 9 40E merger scaffold is not a SUPPRESS verdict.
- Final ACCEPT/SUPPRESS requires present causal, control, and output/bridge proof tiers plus an attached verifier decision.
- Readout-only packets preserve the corrected PR #102 baseline but remain flagged for human review.
