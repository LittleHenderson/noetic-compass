# Claim Status at Handoff — 2026-07-21

## Governing status

The completed definition-anchor run is `NOT_LICENSED_DIAGNOSTIC_ONLY`, with `claim_eligible=false`.

This status reports what the current evidence licenses. It does not cancel CAS Harness's engineering objective of adaptive open-weight universality or genuine 300B-class execution.

| Item | Current status | What the evidence actually supports |
|---|---|---|
| Exact Pythia-160M hidden-state capture | `present` | All 12 qualified GPT-NeoX block boundaries were captured at the pinned revision. |
| Canary and full diagnostic execution | `present` | The clean canary and full 3,080-prompt run completed with evidence recovery. |
| D3 superiority over A124 | `NOT LICENSED` | Primary delta was +0.4252 pp; 95% CI crossed zero; result is inconclusive. |
| Semantic-probe validity | `NOT LICENSED` | Source-generator and surface-language confounds remain. |
| Causal control / output control | `NOT LICENSED` | This experiment did not intervene on or reliably change model output. |
| Prompt-injection detection | `NOT LICENSED` | This experiment was not a prompt-injection detector evaluation. |
| Cross-architecture universality | `OPEN` | The completed run used one exact Pythia-160M revision. |
| Genuine 300B execution | `OPEN` | No 300B-class weights were executed in this run. |
| Independent object-store durability | `OPEN` | Off-pod local recovery exists; independent escrow/object storage is not verified. |
| Production readiness | `NOT LICENSED` | Research apparatus evidence is not customer-production acceptance. |
| Customer-production `ACCEPT` | `NOT LICENSED` | No `ACCEPT` stands in the project record. |
| Amazon distribution | paused | `DISTRIBUTION_PAUSED_INTERNAL_REVIEW_DRAFT`; do not send. |

## Exact primary result

- D3: `0.09906462585034014`
- A124: `0.09481292517006802`
- D3 minus A124: `0.0042517006802721136`
- Paired clustered-bootstrap 95% CI: `[-0.001275510204081634, 0.010204081632653059]`
- Interpretation: `INCONCLUSIVE_INTERVAL_CROSSES_ZERO`

The result is scientifically useful because it identifies what the present dataset can and cannot distinguish. It is not a failure of the hidden-state capture apparatus.

