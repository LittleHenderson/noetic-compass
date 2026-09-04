# CASformer v0.1 claim boundary

## Implemented and locally tested

- `conductance_parameterized_attention_routing`
- `pre_softmax_reference_normalized_current_telemetry`
- `local_relation_id_operator_selection`
- `explicit_bias_and_separate_beta`
- `bounded_cjt_pre_residual_nonlinearity`
- `exact_external_topology_and_permission_masks`
- `positive_learned_soft_resistance_fields`
- `fixed_policy_resistance_gradient_boundary`
- `differential_positive_rail_signed_weights`
- `optional_differential_conductance_projection_mode`
- `differentiable_passive_conductance_laplacian`
- `causal_decoder_style_language_model_wrapper`
- `checksum_bound_contract_checked_non_authoritative_trace`
- `nominal_end_to_end_finite_backward`

## Established negative or equivalence results

- `SCALAR_ROUTING_REPARAMETERIZATION_ONLY`: scalar Ohmic routing compiles to
  ordinary attention with an additive logit bias.
- `CONDUCTANCE_ONLY_FOR_ROUTING`: routing observes the product containing
  `V/R`; it does not identify Drive and resistance separately.
- `ADDITIVE_WEIGHT_GENERATION_RETIRED`: the additive effective-weight form is
  exactly its fixed-expert output mixture, including gradients.
- `TYPE_RELABELING_IS_NOT_A_CAUSAL_CONTROL`: permuting type IDs and their
  operator parameters restores the same function.
- `SIGNED_PAIR_VALID_BUT_REPARAMETERIZED`: two positive conductance rails can
  represent a bounded signed matrix, but do not add software expressiveness.

## Not established

- better language modeling;
- better reasoning;
- better sample efficiency;
- out-of-distribution generalization;
- a CAS-specific neural advantage over a matched generic full-state controller;
- a complete recurrent reasoning transistor with persistent governed Bias and
  memory, or an integrated verify, repair, commit, and restart lifecycle;
- a causal or biological model of attention;
- hardware compatibility or the PCBA matched-CJT/current-mirror differential
  pair topology;
- calibrated correspondence to any existing model activation;
- safe phase memory or CMB integration;
- CNCM kernel integration;
- truth, proof, commitment, permission, or action authority;
- canonical CAS-Sem type or compiled CJT type integration;
- provenance proof for caller-declared feedback ticks;
- replay sufficiency, producer authentication, signature, chain anchoring, or
  WORM retention for local trace checksums;
- production readiness;
- finite gradients for every extreme finite floating-point input;
- CRQS, CAS-G, Evidence Tier, or deployment grade.

Any future advantage claim requires a separate preregistered learned experiment
with the same data, masks, raw inputs, socket placement, parameter budget,
optimizer, update count, and compute for a generic full-state controller.
