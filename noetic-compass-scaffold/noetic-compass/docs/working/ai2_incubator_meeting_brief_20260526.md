# AI2 Incubator Meeting Brief - May 26, 2026

## Purpose

Use the AI2 Incubator discussion to test one focused thesis: CAS Harness can become audit infrastructure for open-weight AI models, with Atlas Viewer as the operator UI and Evidence Packets as the durable audit artifact.

This is not a pitch for another chatbot wrapper. It is a product push around instrumented model auditing: hidden states, activations, ablation, controls, output proof, and one packet-backed verdict.

## Current Live Status

- Atlas / Audit Console reference path can return an Evidence Packet-backed `ACCEPT`.
- The current live path demonstrates that the UI can surface a verdict, proof chips, and supporting packet evidence for a reference audit path.
- The next product milestone is the customer open-weight path: user attaches or selects a supported open-weight model, CAS Harness runs the audit protocol, Atlas shows the trace, and the run emits one final Evidence Packet.
- This is not yet a general customer model intake product. The reference path proves the verdict-to-evidence loop; the open-weight customer path is the next build.

## Product Boundary

CAS Harness is open-weight only for the current product push.

In scope:

- Models whose weights or runtime internals can be inspected through supported adapters.
- Hidden-state and activation capture.
- Layer, neuron, feature, and token-position evidence.
- Ablation and matched-control runs.
- Output proof tied to model-native coordinates and CAS method outputs.
- Evidence Packet export with model metadata, audit config, verdict, confidence, reason codes, proof chips, component scores, errors, and integrity metadata.

Out of scope for this push:

- Black-box API auditing where we cannot inspect activations or run causal interventions.
- Claims that CAS can certify arbitrary closed models.
- Universal "any AI" positioning.
- Safety certification, legal compliance, or truth adjudication.

The honest claim is narrower and stronger: for supported open-weight models, CAS Harness can produce an inspectable audit trail from internal model state to verdict.

## Why AI2

AI2 has the right surface area for this wedge:

- Open model culture and credibility.
- Direct experience hosting, evaluating, and releasing open-weight systems.
- Enterprise and research relationships that care about verifiable model governance.
- Systems depth to stress-test whether this can scale beyond a polished demo.

The ask is not just capital. We need pressure from people who know model hosting, eval infra, interpretability tooling, enterprise trust, and open-weight deployment.

## Five-Minute Demo Path

1. 0:00 - Open Atlas / Audit Console and state the boundary: this is an open-weight audit UI, not a black-box chatbot monitor.
2. 0:45 - Show the reference model path and completed audit status.
3. 1:30 - Open the verdict row showing Evidence Packet-backed `ACCEPT`, confidence, and proof chips.
4. 2:15 - Click through to the packet evidence: model metadata, audit config, reason codes, component scores, and proof references.
5. 3:00 - Show the Atlas evidence view: trace, layer/neuron coordinates, and where the UI links visual claims back to packet rows.
6. 4:00 - Explain the next milestone: customer open-weight attach/run/export, with one orchestrated audit producing one Evidence Packet and one verdict.
7. 4:45 - Ask AI2 for compute, design partners, model-hosting review, systems architecture review, and GTM help.

## What Is Unique Vs Neuronpedia Or TransformerLens?

Short answer: Neuronpedia and TransformerLens are excellent interpretability tools. CAS Harness is trying to become audit infrastructure.

- Neuronpedia helps catalog and browse features. CAS Harness turns model-internal evidence into a run-level audit verdict with provenance.
- TransformerLens gives researchers instrumentation primitives. CAS Harness packages instrumentation, ablation, controls, output proof, and packet export into an operator workflow.
- CAS Harness is verdict-first and evidence-bound: `ACCEPT`, `SUPPRESS`, or `FLAG` must point back to packet rows.
- Atlas Viewer is not the evidence source. It is the UI over a machine-readable Evidence Packet and trace.
- The commercial wedge is enterprise auditability for open-weight models, not exploratory neuron browsing.

## AI2 Asks

- Compute credits for supported open-weight model audits, especially 20B-300B stress testing.
- Enterprise design partners willing to test audit workflows against real internal model governance needs.
- Model-hosting help for secure, cost-controlled open-weight inference and activation capture.
- Systems architecture review for orchestrator, probe workers, artifact storage, and Evidence Packet integrity.
- Go-to-market support: who buys this, what budget it maps to, what proof is needed before procurement takes it seriously.

## Honest Limitations

- Current live capability proves the reference verdict-to-evidence loop, not full customer open-weight intake.
- Large-model activation capture is expensive and operationally hard.
- Adapter coverage must be earned per model family; unknown architectures should be refused or labeled exploratory.
- Evidence Packets prove what CAS observed and decided under a configured audit, not objective truth or full safety.
- Enterprise trust will depend on reproducibility, isolation, cost controls, and tamper-evident records, not UI polish alone.

## Meeting Goal

End the meeting with a concrete decision on whether AI2 sees CAS Harness as a credible open-weight audit infrastructure wedge, and if yes, define the first validation sprint: target models, available compute, design partner profile, success criteria, and the review owners.
