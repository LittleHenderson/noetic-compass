# CASformer v0.1

CASformer v0.1 is a working PyTorch reference implementation of a
CAS-Ohm-shaped, CJT-inspired Transformer. It is an executable v0.1 research
starting point, not a complete reasoning transistor, a trained language model,
or a CNCM-authoritative component.

## What is implemented

- Multi-head self-attention with ordinary learned query, key, value, output,
  and feed-forward parameters in the baseline mode.
- Positive, reference-normalized CAS-Ohm-shaped route-current proxies using
  independently visible Drive, capability, policy, context, and resource
  resistance fields.
- Relative conductance `G_hat = R_ref/R_total` as the weight-like attention
  routing factor.
- Separate semantic allocation, pre-softmax route-flow magnitude, normalized
  Ohmic attention, and total-flow telemetry.
- Exact topology and permission masks, including safe all-closed rows.
- Relation-ID-selected operators that make each local neural relation channel
  select different machinery. These IDs are not canonical CAS-Sem types.
- A bounded CJT gate with explicit Bias, separate `beta`, and cutoff, active,
  saturation, and explicit breakdown states.
- A nonlinear Cause/Bias/Effect socket before the residual merge.
- A stacked encoder and a causal decoder-style language-model wrapper.
- An optional learned positive-control adapter that cannot train policy
  resistance.
- An optional `linear_weight_mode="differential_conductance"` that replaces
  dense projections, relation operators, gate projections, feed-forward layers,
  and an untied language head with signed weights derived from two positive
  conductance rails.
- An optional differentiable graph-circuit solve using
  `L = B.T @ diag(G) @ B`.
- Detached, checksum-bound, contract-checked `NEURAL_PROXY_UNVALIDATED` traces.
  They are not signed, independently anchored, or WORM-retained evidence.
  Their mode is `NEURAL_PROXY`, not the CNCM protocol's admitted
  `NEURAL_PROFILE` mode.

`make_trace()` includes full tensors by default. On those records,
`verify_trace()` also checks shapes, tensor summaries, operating-region counts,
types, and closed-route redaction. Callers can explicitly request a smaller
summary-only trace, but its verification is limited to structure, summaries,
zero-authority fields, and checksum because the omitted tensor values cannot be
cross-checked.

## Core law

For each open route:

```text
R_total = R_capability + R_policy + R_context + R_resource
i_hat    = readiness * region_multiplier * (V_drive / V_ref) * (R_ref / R_total)
I_hat_total = sum(i_hat)
alpha    = softmax(semantic_score + log(i_hat))
```

`alpha` controls where content goes. `I_hat_total` preserves the
reference-normalized CAS flow magnitude available before attention
normalization. It is a dimensionless neural proxy, not raw amperes. The scalar
route has an exact ordinary logit-bias twin; the package tests and reports that
boundary instead of calling it new expressiveness.

Every mode uses conductance as its attention-routing weight. No registered
neural profile or activation-to-CAS calibration bridge exists, so these are
proxy neural quantities, not native calibrated CAS-Ohm measurements. Standard
signed matrices remain the default comparison mode. The optional differential
mode represents dense signed transforms with positive `1/R+` and `1/R-` rails;
it is bounded and is still a reparameterization, not a new neural mechanism.

`I_hat_total` is a sum over open paths. With the same per-edge Drive, it
therefore grows with fan-in (and with causal sequence position). That is
parallel-path accounting, not a cognition score. Comparisons across lengths or
topologies must use a declared per-query Drive/resource budget or an
independently calibrated full-scale reference.

The language shell enforces a causal topology mask and is tested for prefix
invariance. Its control and Bias tensors are caller-owned, however, so the shell
cannot prove that a caller did not encode future information into them.

The canonical import package is `casformer`. Its main public classes are
`CASControl`, `OhmicMultiheadAttention`, `CJTRegionGate`, `CASformerBlock`,
`CASformerEncoder`, `CASformerLanguageModel`, and
`DifferentialConductanceLinear`.

## Run

From this directory:

```powershell
python -m pytest
python examples/minimal_forward.py
python tools/validate_reference.py --output artifacts/CASFORMER_V0_1_VALIDATION_RECEIPT.json
python tools/validate_all.py
```

The local validation requires PyTorch. No Hugging Face model, network access,
GPU, tokenizer, or training run is required.
`validate_all.py` regenerates the source manifest, runs the independent core
checks, runs both the CASformer and existing CNCM test suites, runs the
untrained example, and writes the completion receipt.

The finite-backward check covers seeded nominal inputs and the stated masking
cases. It is not a claim that gradients remain finite for every extreme finite
floating-point input.

Installed wheels include the trace schema plus the full specification and claim
boundary. The local source-reference record contains host paths and is
deliberately not packaged. Call `load_trace_schema()` to read the schema without
assuming a checkout path.

## Important boundary

This prototype can route and transform neural tensors. It cannot determine
truth, meaning, proof validity, commitment, permission, memory writes, or
external action. It is not imported by the current `cncm` kernel package.

Its `breakdown_mask` is a deliberate safety override: it suppresses the neural
effect. The PCBA source describes destructive or inverted breakdown behavior;
this prototype does not reproduce that unsafe behavior. Declared feedback tick
metadata is checked for ordering, but it is caller-supplied and is not proof of
the data's provenance.

See [SPEC.md](SPEC.md) for the full contract and [CLAIMS.md](CLAIMS.md) for the
claim boundary.
