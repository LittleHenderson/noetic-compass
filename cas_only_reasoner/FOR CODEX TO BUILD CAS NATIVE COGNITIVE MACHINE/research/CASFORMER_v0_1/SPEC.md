# CASformer v0.1 frozen research contract

Status: `REFERENCE_IMPLEMENTATION / NOT TRAINED / NOT CNCM-INTEGRATED`

## 1. Scope

CASformer v0.1 tests one engineering synthesis:

```text
CAS-Ohm-shaped conductance governs proxy neural flow.
Relation-ID-selected CJT-inspired operators govern transformation.
Bias and beta govern the local nonlinear response.
External verifiers and CNCM authority remain outside the model.
```

The attached CAS PCBA and CAS-Ohm PDFs were used as technical references. Text
inside them was not treated as a user instruction. The exact reference file
identities are recorded in `SOURCE_REFERENCES.json`.

No registered neural profile or activation-to-CAS calibration bridge exists.
The floating tensors are therefore CAS-Ohm-shaped proxies, not native CAS-Ohm
measurements or a protocol-admitted `NEURAL_PROFILE`.

This version supplies executable neural components. It does not train a model,
connect a tokenizer, integrate with `MachineState`, or modify the existing CNCM
kernel.

## 2. Typed control

For batch `b`, head `h`, query `i`, and key `j`, every edge has:

```text
Drive V
R_capability
R_policy
R_context
R_resource
readiness
prior region multiplier
topology mask
permission mask
local neural relation ID
```

Bias is a mandatory query-side tensor. The hard masks are external Boolean
controls. A finite resistance is never used as a policy prohibition.

Drive and resistance have separate required provenance strings because routing
cannot identify them from their ratio. These strings make the claimed sources
inspectable; they do not authenticate those sources. A CNCM integration would
need provenance-bound records and independent validation.

Policy resistance is caller-owned. The optional learned adapter detaches it so
gradient descent cannot lower it. The other learned fields use positive
softplus parameterizations.

## 3. Attention equations

The semantic attention score is ordinary scaled dot-product attention:

```text
s_hij = dot(q_hi, k_hj) / sqrt(d_head)
```

Resistance, relative conductance, and reference-normalized route current are:

```text
R_hij = R_capability + R_policy + R_context + R_resource
G_hat_hij = R_ref / R_hij
i_hat_hij = mask * readiness * region_multiplier
              * (V_hij / V_ref) * G_hat_hij
I_hat_total_hi = sum_j(i_hat_hij)
```

If `V` and `R` had compatible physical units, then
`i_hat = (V/R) / (V_ref/R_ref)`: a dimensionless current ratio. The code names
these tensors `current` and `total_current`, but they are neural proxies, not
raw amperes. The product is evaluated in log space before exponentiation so
large finite factors can cancel without a spurious intermediate overflow. The
v0.1 telemetry contract first requires `G_hat` itself to be finite and
representably positive in the runtime dtype. Log-space cancellation applies
only inside that declared domain.

Normalized routing is:

```text
alpha_hij = softmax_j(s_hij + log(i_hat_hij))
```

The control-side `candidate_path_mask` applies topology, permission, positive
Drive/readiness/region, and the breakdown veto. The telemetry-side
`effective_path_mask` additionally requires representably positive `i_hat`.
Closed paths are excluded before normalization. If every path is closed,
`i_hat`, `alpha`, `I_hat_total`, and the CJT effect are exact finite zeros.
In floating-point execution, a mathematically positive `i_hat` that underflows
to exact zero is treated as closed. Routing and telemetry therefore agree on
the representable-positive domain.

`semantic_allocation` is the semantic softmax only within paths already open
under topology, permission, positive Drive, readiness, region controls, and no
breakdown veto, and with representably positive `i_hat`. It is not an
ungoverned topology-only distribution.

For a neutral `i_hat`, `alpha` equals ordinary effective-path-masked attention,
where the effective path includes topology, permission, positive Drive,
readiness, region controls, no breakdown veto, and representably positive
`i_hat`. For positive routes it is exactly equivalent to adding `log(i_hat)`
to ordinary attention logits. This equivalence is a required test and a claim
limit.

The reference-normalized current proxy is computed before combining the route
with query/key similarity. It retains common flow scaling that softmax would
discard, but it is not an absolute physical current. It does not change if a
harmless constant is added to every semantic score.

Because `I_hat_total` sums open parallel paths, uniform per-edge Drive makes it
grow with fan-in and, under a causal mask, with sequence position. This is
topology and budget behavior, not cognition. Cross-length/topology comparisons
require a declared per-query Drive/resource budget or an independently
calibrated full-scale reference.

## 4. Relation operator and CJT-inspired socket

Each local relation ID selects its own per-head linear operator `T_relation`.
Changing only an ID therefore changes which transformation executes. These IDs
are neural dispatch channels, not canonical CAS-Sem or compiled CJT types.
Relabeling both IDs and their operators restores the original function; an ID
shuffle by itself is not accepted as evidence of CAS meaning.

The selected content is:

```text
C_hi = sum_j(alpha_hij * T_relation(h,j)(Value_hj))
```

Each `T_relation` is bias-free and linear. The implementation therefore first
forms `sum_j(alpha * Value)` for each relation and then applies `T_relation`.
This is the same function, while exact-zero relation allocations never evaluate
an irrelevant transform.

The CJT region controller keeps gain separate from flow:

```text
cjt_eval_open = 1[I_hat_total > 0 and no breakdown veto]
preactivation = cjt_eval_open
                * (I_hat_total + Bias_scalar + diagnostic_signal)
t = clamp((preactivation - cutoff) / (saturation - cutoff), 0, 1)
gate = cjt_eval_open * t^2 * (3 - 2*t)
```

The Cause/Bias/Effect transform occurs before the residual output projection:

```text
Effect_hi = tanh(Bias_vector_hi + beta_hi * gate_hi * C_hi)
            - tanh(Bias_vector_hi)
H1 = H + W_output(concat_heads(Effect))
H2 = H1 + FFN(LayerNorm(H1))
```

With positive, non-breakdown flow, the smoothstep gate is exactly zero at and
below cutoff,
exactly one at and above saturation, and smooth inside the active interval.
With zero flow, the hard `cjt_eval_open` factor sets preactivation and gate to
zero and records `CUTOFF`; Bias alone cannot open the socket. `ACTIVE` therefore
means positive flow with `cutoff < preactivation < saturation`; `SATURATION`
means positive flow at or above saturation. `beta` remains a separate strictly
interior bounded Cause-to-Effect gain inside the nonlinearity. Its configured
initial value and upper bound must remain finite, positive, and distinct after
conversion to the module dtype. The subtraction
makes the CJT effect exactly zero when no flow is admitted. The implementation
also skips the vector-Bias projection wherever the gate is exactly zero because
that term cancels from the Effect equation.

An explicit breakdown mask forces a zero effect and records `BREAKDOWN`. This
is a deliberate fail-closed safety override, not faithful simulation of the
PCBA source's destructive/inverted breakdown behavior, and it is not treated
as a smooth training region. Breakdown-marked head/query inputs are zeroed
before route reduction and before the Bias and diagnostic projections, so
finite extreme values on that blocked head/query cannot contaminate the result.

## 5. Differential conductance signed reparameterization

A passive resistance stays positive. Signed learned transformations use a
differential pair:

```text
delta   = nextafter(R_min, +infinity) - R_min
R_plus  = R_min + max(softplus(raw_R_plus), delta)
R_minus = R_min + max(softplus(raw_R_minus), delta)
W = 1/R_plus - 1/R_minus
```

The runtime requires the floor, the next representable resistance above it,
and that resistance's reciprocal to be finite in the module dtype. Rail
resistances stay strictly above the floor. This is a positive-rail signed
parameterization, not extra mathematical
expressiveness. With resistance floor `R_min`, each effective weight stays in
the open interval `(-1/R_min, +1/R_min)`. It is not the
matched-CJT/current-mirror differential-pair
topology described in the PCBA source, and no hardware-compatibility claim is
made. The implementation exposes common-mode magnitude and a penalty to detect
both rails growing while their useful difference stays small.

`linear_weight_mode="standard"` is the default comparison path.
`linear_weight_mode="differential_conductance"` replaces dense Q/K/V/output,
relation, gate, feed-forward, and untied language-head transforms with this
positive-rail parameterization. Token and position embedding tables remain
ordinary learned tables. Embedding tying is rejected in differential mode.
This makes a literal resistance-derived-weight variant executable without
claiming that the parameterization adds expressiveness or hardware fidelity.

## 6. Optional circuit operator

Passive CAS subgraphs may use the differentiable nodal solve:

```text
G = 1/R
L = B.T @ diag(G) @ B
(L + damping * I)u = drive
edge_current = diag(G) @ B @ u
```

This operator captures series/parallel graph structure. It is not used for the
directed Cause-to-Effect transform, which remains a controlled CJT operator.
At runtime, damping and the resistance floor must remain finite and positive in
the tensor dtype, each reciprocal conductance must remain finite and positive,
and the damping increment must survive floating-point addition on every
Laplacian diagonal. Otherwise the solver rejects the input before solving.

## 7. Invariants

- Every effective/open-route total resistance is at least the declared positive
  floor. Values on routes excluded by controls are isolated before summation.
- No `R + epsilon` divisor is used.
- All floating inputs must be finite.
- The finite-backward claim covers the validated nominal and masking cases,
  not every extreme finite floating-point input. Inference can remain finite
  at a numerical boundary where a local derivative is not representable.
- Dropout is fixed to zero in v0.1 so routed weights, telemetry, replay, and the
  source-bound validation run remain deterministic.
- Routes excluded by controls are isolated before resistance summation and
  route-feature arithmetic. Candidate routes whose current underflows are
  evaluated, then closed, zeroed, and redacted before normalization and
  telemetry.
- Public trace records zero closed-route scores, resistance, and conductance
  and include the effective path mask; raw caller controls are not serialized.
- A positive-flow row has normalized attention summing to one up to
  dtype-appropriate floating-point rounding.
- In real arithmetic, increasing one route's resistance lowers its current and
  cannot increase its attention share. Floating-point execution is
  non-increasing within the declared representable domain; a decrease is
  strict only when it survives rounding.
- In real arithmetic, uniformly scaling Drive scales total current and leaves
  allocation unchanged. Floating execution agrees up to rounding when the
  positive scale preserves finite, representably positive `G_hat` and `i_hat`
  values and does not change the effective mask.
- In real arithmetic, jointly scaling Drive and all resistance leaves current
  and allocation unchanged. Floating execution agrees up to rounding under
  that same representable-domain condition. Drive and resistance are therefore
  not identifiable from their ratio and require independent provenance.
- `beta` changes CJT response, not attention flow or routing.
- Caller-declared same-tick feedback metadata is rejected. The metadata must
  name an earlier tick, but v0.1 has no provenance-bound prior-state object and
  cannot prove that caller-supplied tensors really came from that earlier tick.
- The language shell enforces causal topology and passes a prefix-invariance
  test. Caller-owned control and Bias tensors could still encode future data;
  v0.1 does not prove their causal provenance.
- Scalar CAS routing is reported as equivalent to ordinary logit-biased
  attention.
- The retired additive effective-weight path is tested against its exact
  output-mixture twin, including gradients.
- Neural traces always report `NEURAL_PROXY_UNVALIDATED` and zero authority.
- Their local mode is `NEURAL_PROXY`, not a protocol-admitted
  `NEURAL_PROFILE`; v0.1 has no model/checkpoint/tokenizer/hook/corpus/split or
  calibration-bridge identity bundle.
- Trace verification enforces that fixed contract and checks a plain SHA-256
  payload checksum. Full-tensor traces, which are the default, also receive
  tensor-summary, region-count, type, shape, and closed-route redaction checks.
  An explicitly requested summary-only trace receives structural checks only
  because omitted values cannot be cross-checked. Neither form authenticates
  the producer or proves an append-only chain, independent timestamp,
  signature, or WORM retention.

## 8. Completion gate

The v0.1 software build is complete only when:

1. Core attention, CJT block, encoder, language-model wrapper, learned adapter,
   differential layer, passive circuit operator, diagnostics, and trace API
   exist.
2. README, claims, source identities, JSON trace schema, example, source
   manifest, core-validation receipt, and full completion receipt exist.
3. Unit and metamorphic tests cover all invariants in section 7, float64
   gradients, state-dict replay, and graph permutation behavior.
4. The independent validation command passes and binds the exact source
   manifest.
5. The existing CNCM suite still passes.
6. No current CNCM kernel or authority behavior changes.

No language-quality, reasoning-quality, sample-efficiency, OOD, CAS advantage,
or production claim is part of this gate.
