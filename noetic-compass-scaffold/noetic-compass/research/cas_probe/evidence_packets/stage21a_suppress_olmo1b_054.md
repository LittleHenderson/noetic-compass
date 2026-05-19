# Evidence Packet: stage21a_suppress_olmo1b_054

Status: `suppress`

## Boundary

This packet shows a bounded CAS Harness readout and readiness decision for one locked example. It does not claim raw CAS-symbol understanding, exact sentence forcing, or a complete neuron-by-neuron map.

## Model

- Name: `allenai/OLMo-1B-hf`
- Family: `OLMo`
- Revision: `aee7752d9c08ee4775e9b0091426d8410e8f6a89`

## Provenance

- Code commit: `2c72e37a60efe0e9ad42e1093cabe05342472207`
- Fixture SHA-256: `3e4a1aca9f168a190116578b0b4fdb5bab633232ba06902039b233e589121250`
- Activation SHA-256: `b2fbf6661c4b3b9067bdc74edb27c587cee498bc9b6717ee4f74682d07a47e8b`
- Source reports: `stage19b_cross_arch_foundation_verification_stack_20260519.json, stage19c_verification_mode_selector_20260519.json, stage20b_generation_readiness_packets_20260519.json`

## Readout

- Axis: `foundation`
- Layer: `16`
- Position: `focus_token`
- Label: `F2f`
- Confidence tier: `suppressed`

## Verification

- Mode: `BALANCED`
- Accepted: `False`
- Suppression reasons: `factor_conflicted`
- Mode profile: `{"accepted_accuracy": 0.9422084623323014, "coverage": 0.8239795918367347, "silent_error_rate": 0.05779153766769862, "source_component": "factor_consistent", "suppressed_rate": 0.17602040816326525}`

## Generation Readiness

- Policy: `suppress`
- Risk score: `0.9`
- Reasons: `verification_stack_rejected, verification:factor_conflicted`
- Recommended mode: `HIGH_PRECISION`

## Diagnostics

- Lacunarity: `None`
- Blindspot flags: `factor_conflicted`

## Controls

- Text baseline: `None`
- Metadata baseline: `None`
- Random ablation: `random null controls are reported in the source claims matrices`
- Raw-symbol delta: `0.0063`

## Conditioning

- Probe-readable delta: `0.6037`
- Partner margin: `1.3047`
- p-value: `3.17e-12`

## Caveats

- EvidencePacket v1 is an export artifact over locked Stage 19/20B reports; it does not rerun hidden-state inference.
- Readiness policy is generated from Verification Stack status in this export; neural lacunarity-head values are not present in the Stage 19 reports.
- Likelihood conditioning is supported by CPL2; exact sentence forcing in free-form decoding is not claimed.
- The Verification Stack rejected this row; do not present it as a high-confidence accepted readout.

## Rejected Claims

- `exact_causal_neurons`
- `weights_firing`
- `host_model_internal_cas_compiler`
- `raw_cas_symbol_understanding`
- `hidden_state_steering_as_supported_mechanism`
- `exact_sentence_forcing_in_free_form_decoding`
- `complete_neuron_by_neuron_causal_map`
