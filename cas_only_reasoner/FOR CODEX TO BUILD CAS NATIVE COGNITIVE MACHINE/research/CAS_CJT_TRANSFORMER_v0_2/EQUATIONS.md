# Implemented Neural CJT v0.2 equations

Status: `LOCAL MECHANISM PROTOTYPE CONTRACT`

These equations describe the current code. They are a computational model,
not a claim about physical electricity, biological cognition, semantic truth,
or superior learning.

## Typed transition and authority

For CJT `j` at tick `t`:

```text
(E_hat[j,t], delta_B_hat[j,t], diagnostics[j,t])
    = NeuralCJTStep_j(C[j,t], B[j,t], model[t])
```

`E_hat` and `delta_B_hat` are proposals. They have no authority by
themselves. A separate verifier produces a receipt, and the sole-writer
coordinator decides whether the whole proposed batch is valid:

```text
(published Effect, next state) = CommitOrRepair(receipt, proposed batch)
```

Missing semantic evidence produces `UNASSESSED/ABSTAIN`, never `ACCEPT`.

## Desire, Wisdom, and Power

The durable Bias stores integer parts-per-million scores `d`, `w`, and `p`
and separate typed statuses. The neural values are:

```text
D = d / 1,000,000
W = w / 1,000,000
P = p / 1,000,000

g_D = 1 only when Desire.status == SUFFICIENT
g_W = 1 only when Wisdom.status == SUFFICIENT
g_P = 1 only when Power.status == SUFFICIENT

rho = D * W * P
g_RPM = g_D * g_W * g_P
effective_readiness = g_RPM * rho
```

The profile ID is `PROTOTYPE_DWP_PRODUCT/0.1`. This product is a local
engineering choice, not canonical CAS semantics. Each axis and its reason
codes remain separately visible.

## Hard admission

For a neural route `r`:

```text
h[r] = topology[r]
     AND permission[r]
     AND NOT quarantine[r]
     AND budget[r]
     AND g_D[r] AND g_W[r] AND g_P[r]
```

These are exact Boolean gates. Drive or a learned value cannot reopen a route
that a hard gate closed.

## Exact pre-execution compute plan

The current planner uses authored integer controls. Let `s_n` be
`flow_scale_units`, `V_n[r]` the native Drive units, and `R_n[r]` the
native total-resistance units. For an admitted route:

```text
u[r] = floor(s_n * V_n[r] / R_n[r])
```

For a closed route or zero native Drive, `u[r] = 0`. Positive native Drive on
an admitted route requires positive native resistance. Then:

```text
U = sum_r u[r]
q = 0                         when U == 0
q = ceil(U / units_per_quantum) otherwise

k = min(q, count(u[r] > 0), max_routes)
```

The planner schedules the first `k` positive routes sorted by descending
`u[r]`, then by canonical route ID. Its per-row ceilings are:

```text
route_quanta             = k
reasoning_step_quanta    = min(q, max_reasoning_steps)
branch_quanta            = min(q, max_branches)
memory_read_quanta       = min(q, max_memory_reads)
diagnostic_probe_quanta  = min(q, max_diagnostic_probes)
```

This is a deterministic top-route ceiling, not a fairness-floor,
largest-remainder, removal-invariant, or globally budget-conserving allocator.
Those stronger properties remain future work if the CNCM admission contract
requires them.

The plan is frozen before the neural CJT executes. A post-execution current or
observation can be checked against the plan but cannot enlarge it.

## Differentiable CAS-Ohm route

Only routes admitted by `h` and selected by the compute plan can conduct. For
such a route:

```text
R[r] = R_capability[r] + R_context[r]
     + R_resource[r] + R_memory[r]

G[r] = R_ref / R[r]

i[r] = rho[r] * psi[r]
     * (V[r] / V_ref)
     * (R_ref / R[r])
```

The implementation evaluates the positive product in log space. `R[r]` must
be finite and at least `minimum_total_resistance`. `psi` comes from the last
committed operating region. Closed, unscheduled, zero-Drive, zero-readiness,
or zero-`psi` routes get exactly zero current.

```text
I_total = sum_r i[r]

alpha[r] = i[r] / I_total   when i[r] > 0 and I_total > 0
alpha[r] = 0                otherwise
```

If `I_total == 0`, every allocation, executed-route count, new candidate
Effect, and routed gradient is zero. There is no uniform fallback.

The floating-point `i` path remains attached to PyTorch autograd for neural
execution. Separately, the runtime makes support-preserving integer audit
evidence after routing:

```text
c[r] = 0                         when i[r] == 0
c[r] = ceil(i[r] * 1,000,000)    when i[r] > 0
C    = sum_r c[r]
```

For each conducting row, integer allocation parts per million are assigned by
largest remainder, with canonical route ID as the exact tie-break, so they sum
to `1,000,000`. A nonconducting row is all zero. This detached conversion is
for authority accounting only; it does not replace or detach the
differentiable current used by the neural path.

Actual route use is the count of positive-current routes. The prototype uses
one reasoning step per conducting row. A durable memory record fetched once
and a repair frame opened once are each charged once globally, then assigned
row-major to the first conducting rows with remaining predeclared capacity.
They are not multiplied by the number of attention rows. v0.2 performs no
separately metered diagnostic-compute action, so
`diagnostic_probes_used == 0`; the fixed OBSERVE fields are authority metadata,
not neural probes. Forced breakdown makes realized current, allocation, and
all actual-use fields zero even when the earlier plan allowed a nonzero ceiling.

## CAS-Ohm attention

The selected CJT still computes ordinary semantic attention logits:

```text
S[q,k] = Q[q] dot K[k] / sqrt(d_head)
```

For a positive admitted current:

```text
A[q,k] = MaskedSoftmax(S[q,k] + log(i[q,k]))
```

This is exactly an additive attention-logit bias on open routes. The runtime
keeps `i`, `I_total`, `alpha`, `A`, the four resistance components, and the
hard masks as different records because they answer different questions.

The current v0.2 `I_total` does not run a global CJT scheduler. It supplies an
observation for the selected CJT and limits learning through the plasticity
factor described below.

## Registered neural transform and candidate Effect

Inside the frozen v0.1 engine, relation IDs select learned value operators and
produce the routed head tensor `H`. The CJT operating gate supplies `gamma`
and a bounded learned gain `0 < beta < beta_max`. With a learned projection of
the recurrent Bias `b(B)`:

```text
E_base = tanh(b(B) + beta * gamma * H) - tanh(b(B))
```

The v0.2 wrapper discards the block's residual/FFN output as an Effect source.
It uses only the gated telemetry tensor:

```text
Z = W_out * MergeHeads(E_base)
E_hat = execution_mask * T_operation(Z)
delta_B_hat = execution_mask * W_bias_update(E_hat)
```

`T_operation` is a distinct registered module for `^6`, `^2`, `^3`, or
`^8`. Only `^6` is canonical-admitted. A zero gate or breakdown mask makes
`execution_mask = 0` and both proposed tensors exactly zero.

In optional differential-conductance mode, each signed linear weight is
represented as:

```text
W_effective = 1 / R_plus - 1 / R_minus
```

with positive rails. Standard signed `torch.nn.Linear` remains supported.

## Deterministic semantic payload

The candidate's semantic content is not supplied by the caller. For a nonzero
Effect tensor, the decoder averages all axes except the final feature axis and
chooses the lowest-index maximum:

```text
logits[c] = mean(E_hat[..., c])
symbol = labels[argmax(logits)]
```

An exactly zero tensor maps to `NO_EFFECT`. The typed payload is exactly:

```text
{operation_id, effect_kind, symbol}
```

The candidate binds the tensor artifact and decoder digest. The coordinator
recomputes this binding before publication.

## Verification and commitment

Semantic outcome and operating region are separate axes:

```text
semantic_outcome in {INTENDED, OPPOSITE, OFF_AXIS, UNASSESSED, UNKNOWN}
disposition      in {ACCEPT, REFUSE, REPAIR, QUARANTINE, ABSTAIN}
```

The default verifier first checks the Cause, Bias, model, operation contract,
candidate digest, evidence port, and independent identities. It then applies:

```text
CUTOFF                         -> UNASSESSED / ABSTAIN
BREAKDOWN                      -> UNKNOWN / QUARANTINE
experimental operation        -> UNKNOWN / ABSTAIN
missing expected evidence      -> UNASSESSED / ABSTAIN
actual == expected             -> INTENDED / ACCEPT
actual == declared opposite    -> OPPOSITE / REPAIR
otherwise                      -> OFF_AXIS / REPAIR
```

A valid `ACCEPT` batch may publish an Effect and commit allowed state or
memory intents. A valid `REPAIR` batch publishes no Effect and may commit only
the bounded repair transition. An audit-only result writes no Bias, model,
memory, or Effect content. Any invalid mixed batch leaves the authoritative
head unchanged.

## Repair timing

```text
opened_tick   = t
eligible_tick = t + 1
repair Cause.tick = t + 1
parent resume Cause.tick = t + 2
```

Resume requires a retained repair frame and a retained committed repair Effect
whose candidate binds the repair subgoal.

The immutable opening frame remains `OPEN`. Successful resumption commits a
separate sealed `RepairOutcome` with `RETURNED` status that binds the frame,
repair Effect and receipt, reconstructed resume Cause, accepted resumed
candidate and verifier receipt, and exact pre-transition Bias.

Only one frame may be OPEN in v0.2. Opening requires a distinct, durably
eligible canonical `^6` executor with both outbound and return topology edges.
The global `t+1` and `t+2` slots are reserved for its exact subgoal and exact
parent resume. The resume operation list and goal context come from the
retained parent Cause. A non-accepted t+1 attempt does not advance the
authoritative tick, and model learning is forbidden on that reserved subgoal.

## Selective learning

Learning starts only from an independently accepted candidate. Let
`readiness_ppm` be zero unless all D/W/P statuses are sufficient; otherwise it
is the minimum of the three stored scores. The runtime derives:

```text
flow_ppm = min(1,000,000,
               round_to_even(mean(total_current_microunits)))
plasticity_ppm = min(readiness_ppm, flow_ppm)
```

The mean and round-to-even rule operate on the sealed integer totals above;
the coordinator and learner use the same deterministic helper.

For the exact allowlisted parameter set `S`, on a deep copy only:

```text
g = gradient of loss with respect to theta[S]
clip = min(1, max_gradient_norm / ||g||)
scale = learning_rate * (plasticity_ppm / 1,000,000) * clip

theta_candidate[S] = theta_active[S] - scale * g
theta_candidate[not S] = theta_active[not S]
```

The candidate checkpoint qualifies only when its target metric improves by the
required integer microunits, every named retention metric stays within its
tolerance, and the supplied regression result is true. The coordinator then
recomputes the checkpoint byte diff and parameter-group scope before the one
global model pointer can move.

The loss function, score function, and regression result are supplied by the
caller in v0.2. This mechanism proves guarded update flow; it does not prove
that those evaluation functions are complete or independent enough for
production learning.

## Trace identity

Let `C(x)` be canonical JSON and `H(x)` SHA-256. The trace body includes the
previous trace digest and all transition fields, including the 11 phases:

```text
trace_id = "trace-" + first_24_hex(H(C(body)))
trace_digest = H(C(body plus trace_id))
```

The next trace stores this `trace_digest` as its previous digest and must also
start from the prior trace's post-state digest. Rejection audits use a separate
hash chain and cannot move the authoritative head.

This provides tamper evidence only. It is not a signature, authenticated
identity, trusted timestamp, independent notarization, or WORM proof.
