# CJT-MECH-0 -- Mechanism-Anchored Neural CJT Cell. DESIGN BRIEF v0.1 (DRAFT)

```
Status            DESIGN BRIEF ONLY.  NOT AUTHORIZED.  NOT BUILT.  $0.  No GPU, no AWS, no training.
Written by        clean-room successor (Claude), 2026-09-02, Phase C of the owner handoff
Requires          owner approval of the QUESTION (section 1) before any design detail is frozen,
                  and an owner-signed phase record before any build or spend
Depends on        CJT_OHM_STATE_OF_EVIDENCE.md (Phase A) and p6/P6_RESOLUTION.md (Phase B)
```

This brief proposes ONE question and the conditions under which a bench could answer it without
repeating any of the six deaths in this arc. It is not an architecture. Every design choice below
is a constraint the record forces, with the death it prevents named beside it.

---

## 1. The one question

> **Does a mechanism-bound recurrent CJT controller reach verified next-tick recovery with fewer
> examples, fewer wrong actions and better transfer to unseen fault combinations than matched
> generic recurrent controllers, in a partially observed world where diagnostic probes cost budget,
> repair actions are state-dependent and non-commutative, and the gold outcome is produced by the
> environment and a verifier rather than by a type-to-repair table?**

Plain English: give a small neural controller a world where it cannot see the cause of a problem
directly, has to spend budget to look, and where doing things in the wrong order wastes the budget.
Then ask whether wiring the controller as typed junctions -- each type allowed to read certain
evidence, take certain actions, touch certain memory, and change its own state under certain rules
-- lets it learn to recover faster than the same-sized controller with no such wiring.

Not asked: whether CAS labels are decodable; whether a product differs from a sum; whether one
fixed order beats another; whether CAS-Ohm generates weights. Each of those has been killed.

## 2. Why this question is non-vacuous -- one line per death it must not repeat

| death in this arc | what killed it | constraint in CJT-MECH-0 |
|---|---|---|
| EX1 (CAS expert nameplates) | meaningless fixed partition tied the CAS partition | types are ports and contracts, not names; the causal test is a **mechanism swap** (rewire which evidence a type may read, which actions it may take), never a label swap |
| D0 (CAS factor nameplates) | architecture permutation-symmetric; shuffle undone by relabelling | the type binding must be something a parameter relabelling cannot undo: fixed evidence ports, action masks owned by the environment, per-type memory stores. Absorption test runs BEFORE any training |
| S0 (random cascade) | world generator = status dial; stage order absorbed | the world's causal structure is drawn from a registered FAMILY with randomised port semantics; the builder never authors a world to match the CAS wiring |
| D1 (one-tick repair) | optimal repair was a closed form; nothing to diagnose | partial observability + costly probes + non-commutative actions; a zero-cost exhaustive-search check must show no closed-form policy reaches the ceiling |
| P6 (order screen) | "held-out" was the training set; bag beat the chains held out; controls failed | held-out drawn from a separate seed stream and asserted non-identical; every baseline capacity-matched (a bag with `U = 0` is not matched); controls in the same code path; status emitted by program |
| additive CAS-Ohm weight law | algebraic identity with output mixing | CAS-Ohm is a **control law** only: `alpha` routes, `I_total` sets compute depth / probe breadth; `V` and `R` come from separately grounded, separately intervenable sources; no weight generation anywhere |

## 3. World requirements (from the handoff §11, made concrete)

- Hidden causes drawn per episode from a family, for example: low Drive, high resource
  resistance, missing knowledge, policy closed, corrupted memory, stale goal. Two or more causes may
  co-occur; held-out evaluation uses combinations never seen in training.
- Different hidden causes produce the same or similar immediate activation. A ratio-only reader
  cannot separate them by construction (equal-conductance collisions must be exact under the
  implemented equation, per the owner's epsilon law).
- Probes reveal one field each and cost budget. Actions: `retrieve`, `split`, `clarify_goal`,
  `check_policy`, `allocate`, `execute`, `abstain`. Effects are state-dependent and
  non-commutative: retrieve-then-split can succeed where split-then-retrieve wastes the budget;
  execute without check_policy is a violation, not a failure.
- Gold: the environment applies the action; the verifier scores the Effect at the NEXT tick as
  intended / opposite / off-axis / unassessed. No repair table anywhere in the controller.

## 4. Arms (exactly the handoff roster; all practical arms matched on observations, action
budget, hard policy mask, parameter count and compute)

```
M0  FLAT GENERIC CONTROLLER
M1  GENERIC RECURRENT CONTROLLER
M2  ANONYMOUS MODULAR CONTROLLER            (same module count and ports, random assignment)
M3  LEARNED-ROUTING MODULAR CONTROLLER
M4  FULL CJT CONTROLLER WITHOUT CAS-OHM
M5  FULL CJT CONTROLLER WITH CAS-OHM alpha ONLY
M6  FULL CJT CONTROLLER WITH alpha + I_total
M7  FULL CJT CONTROLLER WITH TYPED DIAGNOSIS AND NEXT-TICK FEEDBACK
M8  MODEL-BASED SEARCH BASELINE             (the real bar for "is there headroom")
M9  FULL-STATE ORACLE                       (ceiling only; sees hidden state; never a competitor)
```

The generic full-state controller (M1/M3 with the same observations) is the bar. A ratio-only
controller is an information-limited floor and is reported as such, never as the comparison.

## 5. What makes a type real here (mechanism, not name)

Each CJT type differs from the others in at least two of: input contract, output contract,
evidence port, memory port, legal action set, temporal update law, authority boundary, state
transition. These differences are enforced by the environment and the harness, not by the
controller's own parameters, so no gradient step can rename them away. The pre-training absorption
test (all type permutations x all compensating parameter permutations, signed) must show the
CJT arm non-absorbed and M2 absorbed, or the design is a nameplate and returns DO_NOT_BUILD.

## 6. Outcomes and status law

Primary: verified next-tick recovery; wrong-action rate; number of probes; intervention cost;
steps to recovery; held-out fault-combination transfer; examples to threshold; old-skill retention;
new-skill acquisition; policy violations; trace fidelity. Repair-label accuracy is recorded and is
NOT a primary outcome (label accuracy and recovery correlated `r = 0.022389` in the D1 attack).

CAS-Ohm sub-questions get SEPARATE statuses, never joined by OR:
```
Q-alpha    does alpha improve relative routing over learned routing (M5 vs M3)?
Q-Itotal   does I_total improve adaptive compute (M6 vs M5 at matched mean compute)?
Q-diag     does typed source decomposition improve diagnosis (M7 vs M4)?
Q-feedback does verifier history improve next-tick repair (M7 vs M7-minus-feedback)?
Q-plast    does conductance-gated plasticity reduce forgetting (only if separately authorized)?
```
Status per sub-question is emitted by a frozen program from raw results, controls and gates:
`SUPPORTED / REFUTED / INCONCLUSIVE / INSTRUMENT_INVALID`. Prose writes no status.

## 7. Zero-cost kill gates, run BEFORE any neural spend (any one failing -> DO_NOT_BUILD)

1. One-field and two-field rules, linear / tree / kNN readers on raw observations: none may reach
   the M8 ceiling.
2. Candidate identity, construction order, answer-bearing metadata, epsilon or floating-point
   residues: none may predict the cause or the correct action above chance.
3. One-hop and two-hop graph shortcuts on the probe structure: none may reach the ceiling.
4. Exhaustive search over fixed probe orders and fixed action sequences: no fixed policy may
   reach the M8 ceiling (this is the D1 test, made structural).
5. Held-out identity check: training and held-out draws asserted non-identical for every seed
   (this is the P6 test).
6. Capacity-matched mechanism-free baseline registered and reported in every table.
7. Type-permutation absorption (signed) and saturation / type-blind collapse checks on the
   untrained CJT arm.
8. World-family randomisation: the same bench with port semantics permuted must not change which
   arm the harness favours, or the world generator is the status dial.

## 8. What could kill it at $0 (the honest list)

- Gate 4 fails: under partial observability the best policy is still "probe in a fixed order,
  then act", reachable by M0/M1. Then there is nothing for typed diagnosis to do.
- Gate 8 fails: the causal family cannot be randomised without destroying the task, which means
  the builder is authoring the answer.
- Gate 7 fails: the port and contract differences are absorbable after all, and the CJT arm is
  M2 with paint.
- M8 (model-based search) is reachable by M1 on the dev split: no headroom for any typed arm.
- The parameter/compute matching cannot be made exact across M0-M7 (different port widths):
  then any gain is a capacity artefact and the bench cannot be read.

## 9. Compute and governance (unchanged owner law)

`$0` for the design, the world, the kill gates and the absorption tests (deterministic, local
control-plane work, each under 5 minutes). Any neural arm runs on AWS GPU only, after an
owner-signed phase record, with a hard cost ceiling, watchdog, raw-result flush, receipt and
auto-termination on every exit path. Protected split opened once, by the frozen status program.
Claim-bearing results require a different-model-family or human replication before any status
word stronger than `SUPPORTED_NARROWLY` is written.

## 10. What the owner is asked to decide (nothing else is requested)

1. Approve or reject the QUESTION in section 1.
2. If approved: authorize the `$0` world + kill-gate construction (no neural arms, no GPU).
3. Name the independent auditor for the eventual neural result now, before any run.
```
Design status   DRAFT v0.1 -- awaiting owner ruling on the question
Build status    NOT AUTHORIZED
Spend           $0
```
