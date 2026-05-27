# S7-F28 Balanced Bridge Method Package

Date: 2026-05-26

Read this before proposing or changing CAS Harness large-model methodology.

## Method Label

- Canonical label: `S7-F28-BALANCED-BRIDGE`
- Plain-English name: **S7-F28 Balanced Bridge Method**
- Long name: **Stage 7 Foundation-28 Balanced-Logistic Eta-to-Epsilon Bridge Method**
- Use this label when referring to the successful GPT-NeoX-20B method, and when porting the same method to other open-weight model families.

## One Sentence

`S7-F28-BALANCED-BRIDGE` means CAS Harness large-model validation must use the original source-defined Stage 7 Foundation-28 axis, real open-weight hidden states, the original balanced linear readout, targeted causal controls, the eta-to-epsilon likelihood bridge, trace diagnostics, and then an Evidence Packet/verifier merge.

## Do Not Drift

- Do not replace the original Stage 7 Foundation-28 axis with drive-only, domain-only, or operator-only results.
- Do not replace the original balanced logistic readout with nearest-centroid and call it equivalent.
- Do not remove the TKS source definitions or call canonical colloquialisms "label leakage" by default.
- Do not call a run a CAS Harness ACCEPT/SUPPRESS verdict until the Evidence Packet/verifier merge exists.
- Do not present 20B results as 100B/300B universality proof.

## Correct Step-By-Step Method

1. Use the original source-defined taxonomy.
   - For Foundation-28, use the exact Stage 7 TKS grid: 7 drives x 4 registers.
   - Preserve legacy TKS codes 1a..7d and map them to F1|T..F7|E.
   - For 40 Elements, preserve A1..D10 and map them to operator x domain.

2. Capture real hidden states from the open-weight model.
   - Run the actual model weights.
   - Save layer-by-layer activations.
   - Record model id, revision, architecture, dtype, hidden size, layer count, scenario hash, and label distribution.

3. Read the CAS axis with the original balanced linear probe.
   - Use StandardScaler plus sklearn LogisticRegression(C=0.1, class_weight="balanced").
   - This is the method that corrected the GPT-NeoX-20B Stage 7 bridge.
   - Nearest-centroid is useful for rough inspection, but it is not the original closure readout.

4. Compare against baselines and controls.
   - Majority/chance control.
   - Shuffled-label hidden-state control.
   - Canonical-English surface/text baseline.
   - Treat strong text baselines carefully: canonical CAS colloquialisms are approved English aliases, not automatic contamination.

5. Run targeted causal controls.
   - Suppress the true Foundation cover/subspace.
   - Compare against same-size random covers.
   - Compare against wrong-Foundation covers.
   - The true cover must damage readout more than matched random/wrong controls.

6. Run the eta-to-epsilon behavioral bridge.
   - Eta: read the model's CAS state from hidden states.
   - Epsilon: realize the detected CAS state as readable English prefix context.
   - Run the model again and measure whether likelihood moves in the CAS-predicted direction.
   - Raw CAS-symbol prefixes are negative controls; the load-bearing route is readable epsilon realization.

7. Run trace diagnostics before claiming closure.
   - Compute lacunarity as Var(per-class score) / Mean(per-class score)^2.
   - For Foundation, pass threshold is <= 0.05.
   - Classify the layer trace as Stabilizing / Amplifying / Oscillatory / Neutral.
   - Current implementation is a numeric layer-trace proxy. It is not yet the discrete cas-engine CognitiveFractal orbit classifier.

8. Merge a real Evidence Packet.
   - Include model proof, readout proof, causal proof, control proof, output/likelihood proof, trace diagnostic proof, hashes, confidence, coverage, and caveats.
   - Only after verifier merge should the product return ACCEPT, SUPPRESS, or FLAG FOR HUMAN REVIEW.

## Current GPT-NeoX-20B Result

Model: EleutherAI/gpt-neox-20b

Dataset: exact original Stage 7 Foundation-28 role-bound fixture

Rows: 4,368, exactly 156 per Foundation class

Readout layer: 40

Balanced logistic readout:

- Heldout Foundation accuracy: 86.8622%
- Selected bridge-row Foundation accuracy: 85.7143%
- Selected bridge-row Drive accuracy: 93.75%

Eta-to-epsilon bridge:

- Status: PROBE_PREDICTED_ETA_EPSILON_BRIDGE_PASS
- Probe-readable delta vs none: +0.596413
- Probe-readable positive rows: 90/112
- Sign-test p: 3e-11
- Probe-readable minus partner-readable: +1.244917
- Gold-readable delta vs none: +0.660065
- Gold-readable positive rows: 93/112
- Probe raw delta vs none: +0.002524
- Gold raw delta vs none: +0.002186

Trace diagnostics:

- Status: TRACE_DIAGNOSTICS_PASS
- Gate-layer heldout Foundation accuracy: 86.8622%
- Foundation lacunarity: 0.006715
- Drive lacunarity inside Foundation grid: 0.002752
- Register lacunarity inside Foundation grid: 0.001283
- Numeric layer-trace class: Amplifying

Important comparator:

- Pythia-160M Foundation lacunarity: 0.021
- Pythia-1B Foundation lacunarity: 0.015
- The 20B trace is cleaner than those comparators on this lacunarity gate.

## What This Means

The 20B result now has:

- real open-weight model execution,
- exact Stage 7 Foundation-28 activation capture,
- balanced-logistic hidden readout,
- targeted activation ablation evidence,
- probe-predicted eta-to-epsilon behavioral likelihood bridge,
- trace diagnostic pass.

This is strong 20B evidence.

The Evidence Packet merge is now built for this 20B run:

- `docs/working/S7_F28_BALANCED_BRIDGE_EVIDENCE_PACKET_20260526.json`
- `docs/working/S7_F28_BALANCED_BRIDGE_EVIDENCE_PACKET_20260526.md`

Packet result:

- Verdict: `FLAG_FOR_HUMAN_REVIEW`
- Evidence confidence: `0.803571`
- Formula: `min(balanced_logistic_heldout_accuracy, probe_readable_positive_fraction, causal_control_pass, trace_gate_pass)`

It is still not a final CAS Harness ACCEPT/SUPPRESS verdict, because the Stage 19/20/21 production verifier decision layer is not attached yet.

## Relevant Files

- `live-trace-worker/scripts/run_open_weight_eta_epsilon_bridge.py`
- `live-trace-worker/scripts/run_open_weight_trace_diagnostics.py`
- `live-trace-worker/scripts/merge_s7_f28_balanced_bridge_evidence_packet.py`
- `docs/working/S7_F28_BALANCED_BRIDGE_EVIDENCE_PACKET_20260526.json`
- `docs/working/S7_F28_BALANCED_BRIDGE_EVIDENCE_PACKET_20260526.md`
- `docs/working/cas_harness_large_model_runpod_status_20260526.md`
- `docs/working/cas_harness_foundation28_large_model_protocol_20260526.md`
- `docs/working/S7_F28_BALANCED_BRIDGE_METHOD_PACKAGE_20260526.md`
- `docs/working/cas_harness_original_closure_methodology_20260526.md`
- `docs/working/cas_harness_ai2_one_pager_20260526.md`

## Next Gate

Attach the Stage 19/20/21 production verifier decision layer, or port the exact same packet protocol to the next open-weight model family.

The packet exists now and binds readout, ablation, bridge, trace diagnostics, model metadata, hashes, confidence, coverage, and caveats. Do not upgrade the packet to ACCEPT/SUPPRESS unless the verifier layer explicitly returns that decision.
