# CAS-Ohm Attention Integration Protocol v0.1

## Native Attention Semantics, Neural Calibration, Cortex Diagnostics, and Generative Memory Retrieval

**Source:** owner directive, 2026-08-28.
**Status:** ADOPTED. Supersedes the blunt "keep CAS-Ohm out" reading.
The revised architectural law:

    CAS-Ohm governs FLOW.
    CJTs govern transformation.
    CAS-Sem governs meaning.
    The verifier governs validity.
    The commitment latch governs authority.
    The trace preserves the evidence.

R10 of the instrumentation panel NARROWS accordingly: the reasoning
runtime must not depend on any CAS-Ohm quantity **for truth, validity,
meaning, commitment, or permission**. Flow governance — attention
allocation, resource budgets, diagnostics, tuning — is CAS-Ohm's
proper native role. An attention reading may never impersonate truth.

## 1. The three substrates (the key reconciliation)

| Substrate | What I means | Status |
|---|---|---|
| Native CAS runtime | an explicit local attention/activation-flow variable defined BY the runtime | exact by construction (like a game engine defining gravity) |
| Neural cortex | a measured activation projection with calibrated effective resistance | empirical, profile-specific, held-out-validated |
| Human/biological | a proposed cognitive correspondence | open research question |

Bridges between substrates must be DECLARED and calibrated:
`I_attention_observed = H_profile(y_activation)`. Without the bridge,
neural activation ≠ CAS attention, and neither ≠ human attention. The
paper's anti-circularity rule stands: computing resistance from one
observation and "predicting" that observation is rejected.

## 2. The CAS attention-flow type system

Every quantity carries: quantity kind, mode (native_runtime /
neural_profile / memory_retrieval), unit, method, calibration
identity, uncertainty, provenance, trace id. Bare numbers that drift
between design score, behavioral proxy, and instrumented measurement
are rejected.

## 3. Drive rails and resistance decomposition

    I_attention = V_drive / R_total          (native: exact by rule)
    R_total = R_capability + R_lexical + R_role_binding + R_context
            + R_ambiguity + R_policy + R_compute

The named subtypes are proposed refinements of the guide's capability
/ context / policy / resource terms, not new physical quantities.

## 4. Scheduler allocation semantics

    branch_attention_i = V_goal_i / R_branch_i
    allocated_i = floor(base_budget + k * normalized_I_i)   [clamped]

WITH: minimum exploration allocation, maximum branch ceiling, fairness
floor, hard safety gates — the highest-current branch must never
monopolize the Mind. This gives Foundations/RPM a quantitative way to
direct cognitive WORK without authority over truth.

## 5. CJT flow versus gain versus effect

I tells how much processing flow reached the junction; β tells how
strongly it transformed; Effect tells what was produced. A path may
receive plenty of attention and still produce the wrong meaning —
operating region and semantic outcome are classified SEPARATELY
(ASOM). Healthy flow + wrong effect → probe bias, gain, saturation,
breakdown, or semantic transformation — never "add more Drive."

## 6. Cortex language-stage profiles (implemented v0.1 slice)

Pipeline stages, each with a CAS-Ohm profile: raw cortex output →
schema validation → lexical grounding → content faithfulness (role
binding) → kernel admission → commitment. Case studies from the live
gates:

- **glimmerfor fabrication**: invented word ⇒ R_lexical high ⇒ I_pred
  low; the cortex conducted anyway ⇒ I_obs >> I_pred. The residual
  FLAGS THE NEIGHBORHOOD (unexpected amplification / missing lexical
  resistance / bypass); the grounding probe then IDENTIFIED the
  component. Residuals rank probes; they never name causes.
- **passive-voice role error**: flow healthy, Effect wrong (agent/
  patient swapped) — semantic misalignment, not attention starvation.
  Repair the bias/rule/topology, not the Drive.
- **ambiguity**: R_reference/R_context rise ⇒ I below the
  clarification threshold ⇒ CJT cutoff for direct execution ⇒ RPM
  clarification subgoal.

## 7. CAS-GEM retrieval-current model

Cue = Cause; stored capsule = bias substrate; recall goal = V_drive;
R_retrieval = R_distance + R_decay + R_interference +
R_anchor_conflict + R_policy; retrieval attention I per candidate;
reconstructed narrative = Effect. Behavior: one dominant I → retrieve;
similar I → ambiguity or ask for another clue; all below cutoff →
NEEDS_INFORMATION; dominance despite anchor conflict → suspect
saturation/bypass; high flow + wrong episode → semantic misalignment.

## 8. Parallel memory-candidate allocation

Current-division across candidate capsules (w_i = fraction of
reconstruction attention) — PROPOSED CAS-GEM extension, licensed only
when branches are genuine alternatives with compatible endpoints;
child probes stay visible even when a parent equivalent is computed.

## 9. Stateful retrieval-resistance extension

Frequent successful recall lowers R_access; disuse raises it;
conflicting reconstructions raise R_interference; trusted correction
rewires anchor resistance. This matches the paper's PROVISIONAL
stateful extension: requires defined initialization, update law,
reset, uncertainty, and PROOF that the stateful model beats a matched
memoryless baseline on held-out hysteresis. Not called "memristive"
until earned.

## 10. Calibration and anti-circularity

Neural mode requires: calibration/validation splits DISJOINT, model
profile identity, uncertainty, and no same-sample resistance tricks.
Only instrumented neural mode makes empirical claims about the
Transformer.

## 11. Residual and ASOM diagnostics

ΔI = I_obs − I_pred ranks follow-up probes. ASOM classifies operating
condition (Starved / Aligned / Oversaturated / Misaligned) from
response region and semantic outcome INDEPENDENTLY. Active ≠ correct;
flat has several causes.

## 12. Trace-record schema

CASOhmStageRecord: mode, stage/board/branch/goal ids, V_drive, the R
decomposition + R_total, I_pred / I_obs / delta_I, (neural mode:
alpha_dose, y_activation, r_effective), beta, cutoff, saturation,
operating_region, effect_activation, effect_type, semantic_outcome,
uncertainty, calibration_profile, provenance, trace_id. Implemented
v0.1: `CAS_CORTEX_v0.1/cortex/attention.py`, attached to every
TurnTrace, COMPUTE-ONLY (nothing reads it for decisions — tested).

## 13. Held-out experiments and controls (the Phase 4.3+ program)

- **A lexical resistance**: known / rare / locally-defined / invented /
  near-spelling words → R_lexical rises with grounding difficulty;
  ungrounded falls below admission. Measure cortex activation, native
  gate flow, semantic correctness, commitment SEPARATELY.
- **B role-binding resistance**: active/passive/reversed triplets →
  normal I with wrong roles = transformation fault.
- **C ambiguity load line**: rising ambiguity → R_context up,
  I_direct down, I_clarification up through the alternate RPM branch.
- **D cortex scale curve** (0.5B / 1.5B / 3B): R_capability, semantic
  β, false-commit rate, role-binding accuracy, latency resistance,
  memory footprint — "3B lowered role resistance but cost compute
  resistance; 1.5B best operating point" beats "3B scored higher."
- **E CAS-GEM cue strength**: vague / distinctive / corroborating /
  contradictory clues vs retrieval resistance.
- **F history dependence**: stateful R_access,t vs memoryless
  baseline on held-out retrieval and hysteresis.

## 14. Foundry visualization

The cognitive power grid: watch Drive enter, resistance oppose,
attention flow through branches, CJTs transform, memories compete,
RPM reroute energy toward missing prerequisites — and the verifier
prevent a bright current from being mistaken for a correct idea.

## 15. Admission and falsification gates

CAS-Ohm never decides: truth of a proposition, correctness of a word
meaning, validity of a proof, whether a memory happened, whether an
action is authorized, whether a self-modification is safe. It reports:
flow reached, resistance opposed, response vs prediction, cutoff/
saturation, which stage to probe next. Any use of a CAS-Ohm quantity
inside a truth/commitment/permission decision is a defect. Neural-mode
claims admit only through calibration + held-out validation; stateful
extensions admit only by beating matched memoryless baselines.
