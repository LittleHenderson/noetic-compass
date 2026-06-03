# Stage 9 40E Verifier Report

- Status: `STAGE9_40E_VERIFIER_FLAG_FOR_HUMAN_REVIEW`
- Verdict: `FLAG_FOR_HUMAN_REVIEW`
- Confidence: `0.0`
- Source: `stage9_40e_packet_verifier`
- Trace ID: `pythia-160m-stage9-40e-readout-20260531`
- Mode: `BALANCED`

## Gates

| Gate | Status |
| --- | --- |
| packet | passed |
| proof_chips | blocked |
| readout | passed |
| causal | passed |
| control | passed |
| output_bridge | passed |

## Confidence Components

| Component | Value |
| --- | ---: |
| hidden_probe_test_acc | 0.95625 |
| bridge_selected_element_accuracy | 0.95 |
| causal_guard | 1 |
| control_gate | 1 |
| output_bridge_gate | 1 |
| packet_gate | 1 |

## Reason

proof_chip_gate_blocked

## Boundary

This verifier report is explicit and evidence-bound, but it is built over the Stage 9 40E validation packet. It does not claim live customer inference unless the packet source is a live production run.
