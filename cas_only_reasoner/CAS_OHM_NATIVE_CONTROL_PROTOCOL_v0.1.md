# CAS-Ohm Native Attention Control Protocol v0.1

**Source:** owner directive, 2026-08-28.
**Status:** ADOPTED. Companion and UPGRADE to
`CAS_OHM_ATTENTION_PROTOCOL_v0.1.md` (which set the substrate
boundaries and calibration law). This protocol makes CAS-Ohm ACTIVE:
the CNCM's Attention Engineering and Load-Control Plane — MEASURE,
DESIGN, DIAGNOSE, RECURSE (the guide's own four cover jobs). CAS-Ohm
participates before, during, and after reasoning, in the bloodstream,
continuously measuring and controlling where the Mind's finite
cognitive power goes.

The division of labor, unchanged and non-negotiable:

    CAS-Ohm governs cognitive FLOW.
    CJTs transform that flow.
    CAS-Sem determines what the resulting state MEANS.
    The verifier checks whether the conclusion is VALID.
    The commitment system decides whether it becomes AUTHORITATIVE.
    The trace proves what happened.

CAS-Ohm never proves a proposition. It proves something different and
vital: that the machinery which was supposed to process and check the
proposition was actually energized, operating in range, and not
bypassed.

## 1. Native attention quantity definitions

Three active modes from the guide's three equations:
    MEASURE   I = V / R      how much attention will this path get?
    DESIGN    V = I × R      what Drive produces the target flow?
    DIAGNOSE  R = V / I      what constraint does observed flow imply?
Design mode is a CONTROL LAW, not an observation. Native quantities
are exact by construction within a declared board profile.

## 2. Per-board calibration profiles (CASOhmBoardProfile)

Every board carries a versioned profile: mode (native /
neural_calibrated / behavioral_proxy), V range, resistance component
ranges, I_full_scale, I target band, minimum_required_I,
overload_limit, residual and relative-error tolerances, cutoff and
saturation thresholds, effect expectation, D/W/P thresholds, test
points, trace schema, calibration digest. Implemented:
`CAS_CORTEX_v0.1/cortex/ohm_control.py`.

## 3. Scheduler budget mapping (I_Q quantization)

Flow normalizes to the guide's Q4 system with exact decimals and
trend (rising ↑, steady →, falling ↓):
    I_Q 0.0–2.49  [Q1]  minimum maintenance budget
    I_Q 2.5–4.99  [Q2]  exploratory budget
    I_Q 5.0–7.49  [Q3]  normal working budget
    I_Q 7.5–10.0  [Q4]  high-priority budget
Budgets translate to logical ticks, memory-query allowance,
branch/proof-search depth, tool budget — per board profile. A board
reports e.g. `Verifier: I_Q = 5.80→ [Q3]`.

## 4. Critical-stage attention floors

Some boards must never starve: verification receives
minimum_required_I; commitment must not open before verification is
active. Design mode computes the required Drive (V = I_min × R) or
the maximum admissible resistance (R_max = V / I_min) — the board is
DESIGNED so verification cannot be underpowered, not merely observed
failing. Commitment invariant:
    COMMIT only if I_verify >= minimum AND verifier region == active
    AND the semantic result passed AND residual within tolerance.

## 5. Overload and task-splitting control

λ = I_raw / I_full_scale.
    λ <= 0.75      normal
    0.75 < λ <= 1  near-capacity warning
    λ > 1          OVERLOAD CONTROL: raise deliberate constraint,
                   reduce local Drive, SPLIT the task into stages or
                   parallel child goals, shorten context, defer
                   lower-priority branches.
A five-part question at λ = 1.8 becomes five RPM child questions —
decomposition BEFORE failure, never one saturated junction forced to
answer everything.

## 6. Candidate-branch allocation

For genuine alternative branches with shared endpoints, local branch
flows I_i normalize to budget shares b_i = I_i / ΣI (a CNCM control
extension, not source-canonical), WITH a minimum fairness allocation
so a high-current early favorite cannot erase alternatives before
comparison. Child test points always retained.

## 7. Cascade bottleneck analysis

Each stage keeps local V, R, I, bias, β, effect; gain multiplies
across the cascade and amplifies error with signal. The plane locates:
lowest local I, largest local R, largest gain jump, first cutoff,
first saturation, first wrong effect type. "Inference was starved at
I = 1.1" beats "the model reasoned badly." The signature failure
pattern made visible: high generation flow + low verification flow +
high commitment flow = imagines enthusiastically, checks weakly,
commits too quickly — repair the verification PATH (placed
constraints), never under-volt the whole system.

## 8. RPM quantitative fault trees

V, R, I_pred, I_obs, ΔI, ASOM attach to every Desire-Tree node. Low
capability maps to high R_cap, low I on the affected path; RPM
creates the child goal that repairs THAT path (e.g. "learn
passive-voice role binding"). CAS-Ohm becomes the learning planner.

## 9. Learning as measured resistance reduction

Improvement is a mechanism, not a pass/fail flip: P_cap rises, R_cap
falls, I enters the active region, effect type becomes correct. A
descendant is not better because it raised Drive or gain; it must
show lower R_cap, equal-or-lower overload, correct semantic effect,
stable residual, no protected regression.

## 10. Cortex activation adapters

Native rules never apply raw to the neural cortex. Neural mode uses
alpha dose / activation response / effective resistance with model
identity, test-point identity, disjoint calibration and validation
splits, uncertainty — no same-sample circularity. Until a bridge
passes held-out validation the UI labels the quantity
NEURAL ACTIVATION PROXY, never NATIVE ATTENTION. The scale study
(0.5B/1.5B/3B) reports per-term profiles (R_capability down,
R_resource up, the best combined operating point) instead of one
score.

## 11. CAS-GEM retrieval flow

V_recall / R_retrieval (semantic distance + decay + interference +
anchor conflict + policy + resource) → I_recall per candidate memory.
One dominant flow: retrieve. Similar flows: keep BOTH as competing
branches and ask for another clue — never merge narratives. All below
cutoff: NEEDS_MORE_CLUE. Strong flow violating an exact anchor:
reject the semantic effect DESPITE the flow. Child probes stay: a
healthy parent aggregate can hide one saturated and one starved
branch.

## 12. Commitment-readiness packets

    CASOhmReadiness { region: active, I_pred, I_obs,
                      residual: within_tolerance, overload: false,
                      effect_type: intended, child_probes: healthy }
The commitment controller may REQUIRE this packet before opening.
It certifies energization, never truth.

## 13. Flow-region × semantic-outcome matrix (axes INDEPENDENT)

    ACTIVE + INTENDED      healthy
    CUTOFF + UNKNOWN       missing knowledge or blocked path
    ACTIVE + OFF-AXIS      well-powered misunderstanding
    SATURATED + INTENDED   correct but overloaded
    SATURATED + OFF-AXIS   confidently wrong and clipped
    BREAKDOWN + OPPOSITE   inversion
Deriving semantic correctness mechanically from the flow region is
PROHIBITED. A small residual never means the answer is correct.

## 14. Foundry visualization

Two independent panels at every test point. Flow panel: V, R
decomposition, R_total, I_pred, I_obs, I_Q, λ, ΔI, region. Meaning
panel: expected vs observed effect, intended / opposite / off-axis /
unknown / verified / contradicted.

## 15. The permanent test battery (tests 1–8)

    T1 fake word          R_lexical up, flow below admission, nothing
                          commits (attention/grounding blockage)
    T2 backwards sentence healthy flow, wrong effect caught
                          (understanding fault, not starvation)
    T3 overloaded input   λ > 1 → split or constrain BEFORE clipping
    T4 starved verifier   generation healthy, verification below
                          minimum → commitment blocked
    T5 hidden branch      healthy parent aggregate + one saturated +
                          one starved child → child probes prevent a
                          false PASS
    T6 learning repair    before: high R_cap, cutoff; after: lower
                          R_cap, active, correct effect
    T7 memory ambiguity   two similar flows → ask for another clue,
                          never merge
    T8 confident misread  active + near-zero residual + off-axis →
                          semantic/topology repair, NEVER gain
                          adjustment

## 16. Held-out neural calibration

Neural-mode admission requires the full research-paper discipline;
behavioral proxies stay labeled as proxies.

## 17. The wider circuit laws (context)

CAS-Ohm is the flow law beside Q = C×V (storage), V = L·dI/dt
(momentum/resistance to change), f₀ = 1/(2π√LC) (habit loops), β
(amplification), RC (encode/recall/forget), diodes (permitted
direction), RPM (which prerequisite receives the next flow). Shared
topology, distinct formalisms — CAS-Ohm is the central law tying the
bench together, not the whole bench.
