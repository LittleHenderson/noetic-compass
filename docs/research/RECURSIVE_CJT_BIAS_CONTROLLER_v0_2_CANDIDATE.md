# Recursive CJT Bias Controller v0.2 — CANDIDATE

Status: **CANDIDATE — PROPOSED_UNTESTED.** Documentation + deterministic simulator only.
No model, no GPU, no neural experiment, no claim-bearing data, no condition sweep. This
document repairs the type, temporal, and authority defects the owner identified in v0.1
(`RECURSIVE_CJT_BIAS_CONTROLLER_v0_1.md`, which is preserved unmodified). Everything in
v0.1 not repaired here carries forward.

Reference implementation and proofs: `cas_only_reasoner/recursive_cjt_rc0/`
(`sim/rc0_types.py`, `sim/rc0_routing.py`, `sim/rc0_coordinator.py`,
`sim/rc0_simulator.py`, `tests/test_rc0.py` — **17/17 permanent tests pass**).

## 0. Artifact-version finding (RC-0 requirement 1)

The reported I/J fix DID land: commit `7bf2a3b9`'s blob, HEAD's blob, and the working
tree of `RECURSIVE_CJT_BIAS_CONTROLLER_v0_1.md` are byte-identical (git blob
`bef7ff92ebf9b6a796f41ae847f03c6b6bcb9527`; working-file SHA-256
`a1c40086756da592db2cd971727b61c60b7f6e5399b5666f390257c9b41174db`), and the committed
file contains arms I and J with the `I ≥ F` / `J ≥ F` falsifiers. The copy the owner
reviewed was the pre-audit intermediate draft. No version was overwritten. Test 17 now
digest-locks v0.1 against drift. The A–J lettering is retired regardless (§8).

## 1. Repaired state symbols

- The Bias tuple is now `B_{j,t} = (S, M, P_RPM, Z, Θ, G)`. **`P_RPM` is the RPM
  prerequisite state; lower-case `r` is reserved for CAS-Ohm resistance.** In code they
  are distinct types (`RPMState` vs `Resistance`) that cannot be confused: passing one
  for the other raises, and `RPMState` refuses all arithmetic (tests 1).
- The transition function is renamed **`CJTStep`**: `(E_{j,t}, B̂_{j,t+1}) =
  CJTStep_j(C_{j,t}, B_{j,t})`. `J` is reserved for Jacobians in the η–ε lane. The hat
  on `B̂` marks a PROPOSED update — it becomes `B_{t+1}` only at COMMIT.

## 2. Repaired ASOM typing (factorized)

- `region_posterior ∈ Δ³` over EXACTLY the four source-defined regions
  (cutoff / active / saturation / breakdown). A 7-entry posterior is rejected (test 2).
- Separate enumerated fields: `response_model_status` (ohmic | non_ohmic | unassessed),
  `stability_status` (stable | unstable | unassessed), `semantic_outcome`
  (intended | opposite | off_axis | unassessed). "Unstable" is not a fifth place on the
  characteristic curve.
- ASOM is a DERIVED, human-readable dashboard letter computed from the record. It is
  never the authoritative stored state.

## 3. Repaired route equation

```
score_j,t = hard_mask(G_j,t) · rpm_ready_j,t · route_multiplier(region_j,t-1) · V_j,t / (r_j,t + ε)
```

- `route_multiplier` is a SCALAR in [0,1] (cutoff 0, active 1, saturation 0.5 = capped,
  breakdown 0, unassessed 1 so a new expert is not silently starved).
- The control action `{RUN, CAP, SPLIT, REPAIR, QUARANTINE, HALT}` is a separate TYPED
  enum; any attempt to multiply an action by a number raises (test 3). SPLIT creates
  child work; it never masquerades as arithmetic.
- All-zero scores → `NO_READY_CJT`; RPM opens a repair subgoal or the kernel halts;
  normalization never divides by zero (test 4).
- A policy mask is 0/1 and absolute: `V = 10¹²` cannot outvote `mask = 0`; a soft mask
  value like 0.5 is rejected at construction (test 5).

## 4. Frozen tick order (temporal repair)

READ → CANDIDATE → READINESS → **ROUTE using Z_{t−1}** → EXECUTE → OBSERVE → VERIFY →
DIAGNOSE → EMIT `BiasUpdateIntent` → ATOMIC COMMIT → SEAL TRACE. Full semantics:
`recursive_cjt_rc0/RECURSIVE_CJT_TICK_SEMANTICS_v0_1.md`. The same-tick causal loop is
closed by construction; test 6 proves flipping the verifier's registered outcomes changes
verdicts and changes NOTHING in any tick's allocation. Region evidence comes from
usage/readiness observations only — the semantic outcome is stored beside it, never
folded in (the two-axis discipline).

## 5. Authority repair

The CJT never mutates authoritative Bias state. `BiasState` is immutable (a direct write
raises); CJTs emit `BiasUpdateIntent`s; only the transaction coordinator commits, and it
commits atomically — one invalid intent rejects the whole batch with rollback.
Governance fields are owner-only; intents touching them are rejected (test 7). This
mirrors the CNCM kernel's atomic state-owner rule.

## 6. D/W/P non-duplication contract

One source table governs every quantity (`RECURSIVE_CJT_STATE_SCHEMA_v0_1.json`,
`measurement_contract`; completeness enforced by test 8):

| Quantity | Role |
|---|---|
| Desire | hard relevance threshold (readiness) AND above-threshold surplus supplies `V = max(0, D − τ_D)` — registered dual role; a deficiency is never counted twice |
| Wisdom | hard applicability threshold — readiness ONLY, never a resistance |
| Power | hard minimum-capability threshold; above threshold MAY modulate `r_cap` — registered dual role (hook registered, not active in RC-0) |
| Policy | hard mask, NEVER a resistance |
| Context / resource | soft resistance terms `r_context`, `r_resource` |

So `r_{j,t} = r_cap + r_context + r_resource`, with policy outside the equation.

## 7. Compute budget typing

Frozen for the first experiment: `compute_unit = CJT_EXPERT_EVALUATION`.
`B_t` = maximum CJT expert executions permitted this episode; `B_{j,t} = B_t · g_{j,t}`;
repairs cost 1 unit. Tokens, FLOPs, tool calls, and milliseconds are NOT interchangeable
with this unit; each later unit gets its own registered calibration profile.

## 8. Condition tables (lettering repaired)

The ambiguous A–H/I–J lettering is retired for this study. Two stage tables:
`recursive_cjt_rc0/STATIC_CONDITIONS_v1.yaml` (**S0–S7**; S7 = matched non-CAS semantic
control, required for any "CAS-specific" language) and
`recursive_cjt_rc0/RECURSIVE_CONDITIONS_v1.yaml` (**R0–R9**; R7 = matched generic
hierarchical controller; R8 = random matched state stream; R9 = CAS stream physically
disconnected). Sequencing: simulator (Gate 0, DONE) → static (Gate 1) → recursive
additions one at a time (Gate 2) → selective plasticity (Gate 3) → full CJT Transformer
(Gate 4); each gate requires an owner-signed phase record.

## 9. The deterministic simulator (Gate 0 artifact)

`recursive_cjt_rc0/sim/` implements, with no neural network: four CJT experts
(`^2_attract`, `^3_averse`, `^6_decompose`, `^8_trigger`), typed D/W/P, RPM subgoals with
return addresses, depth/branch limits and typed cycle detection, factorized operating
records, CAS-Ohm route scores with hard masks, the finite budget, a semantic verifier
stub with registered exact outcomes, `BiasUpdateIntent`s, the atomic coordinator, board
reports that never hide a failed child, ablation flags reproducing the pre-registered
signatures, and digest-identical deterministic replay. Receipt:
`recursive_cjt_rc0/RC0_SIMULATOR_RECEIPT.json`.

## 10. Claims

Permitted: "the RC-0 controller semantics are implemented and 17/17 type/temporal/
authority properties hold in a deterministic simulator."
Prohibited: any capability, performance, efficiency, interpretability, or CAS-specificity
claim; any neural result; any statement that the controller helps learning. Those await
Gates 1+ under owner-signed phase records, with statuses emitted by the deterministic
promotion program.
