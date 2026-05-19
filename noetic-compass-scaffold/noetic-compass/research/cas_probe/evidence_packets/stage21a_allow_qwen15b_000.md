# Evidence Packet: stage21a_allow_qwen15b_000

Status: `allow`

## Boundary

This packet shows a bounded CAS Harness readout and readiness decision for one locked example. It does not claim raw CAS-symbol understanding, exact sentence forcing, or a complete neuron-by-neuron map.

## Model

- Name: `Qwen/Qwen2.5-1.5B`
- Family: `Qwen`
- Revision: `8faed761d45a263340a0528343f099c05c9a4323`

## Provenance

- Code commit: `2c72e37a60efe0e9ad42e1093cabe05342472207`
- Fixture SHA-256: `3e4a1aca9f168a190116578b0b4fdb5bab633232ba06902039b233e589121250`
- Activation SHA-256: `ccb79afe5a3215f0f6aac828c574a0d14cf8115ab769489ea4269c70ce43fe8e`
- Source reports: `stage19b_cross_arch_foundation_verification_stack_20260519.json, stage19c_verification_mode_selector_20260519.json, stage20b_generation_readiness_packets_20260519.json`

## Readout

- Axis: `foundation`
- Layer: `11`
- Position: `focus_token`
- Label: `F1T`
- Confidence tier: `high`

## Verification

- Mode: `BALANCED`
- Accepted: `True`
- Suppression reasons: `none`
- Mode profile: `{"accepted_accuracy": 0.9660842754367934, "coverage": 0.8273809523809523, "silent_error_rate": 0.03391572456320657, "source_component": "factor_consistent", "suppressed_rate": 0.17261904761904767}`

## Generation Readiness

- Policy: `allow`
- Risk score: `0.0`
- Reasons: `all_readiness_signals_within_mode_thresholds`
- Recommended mode: `BALANCED`

## Diagnostics

- Lacunarity: `None`
- Blindspot flags: `none`

## Controls

- Text baseline: `None`
- Metadata baseline: `None`
- Random ablation: `random null controls are reported in the source claims matrices`
- Raw-symbol delta: `-0.0002`

## Conditioning

- Probe-readable delta: `0.796`
- Partner margin: `1.6253`
- p-value: `2.92e-12`

## Caveats

- EvidencePacket v1 is an export artifact over locked Stage 19/20B reports; it does not rerun hidden-state inference.
- Readiness policy is generated from Verification Stack status in this export; neural lacunarity-head values are not present in the Stage 19 reports.
- Likelihood conditioning is supported by CPL2; exact sentence forcing in free-form decoding is not claimed.

## Rejected Claims

- `exact_causal_neurons`
- `weights_firing`
- `host_model_internal_cas_compiler`
- `raw_cas_symbol_understanding`
- `hidden_state_steering_as_supported_mechanism`
- `exact_sentence_forcing_in_free_form_decoding`
- `complete_neuron_by_neuron_causal_map`
