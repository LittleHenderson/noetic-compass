# Recursive CJT Tick Semantics v0.1

Part of PHASE RC-0. Status: PROPOSED_UNTESTED design semantics; reference implementation
`sim/rc0_simulator.py` (deterministic, no neural network). This is the FROZEN execution
order — without it, RPM, ASOM, routing, verification, and Bias mutation can refer to one
another in a circle.

## The frozen tick order

```
 1. READ       Read authoritative B_t for every expert (from the coordinator) and the
               incoming Cause. Nothing else may be read as state.
 2. CANDIDATE  Determine which CJTs are relevant to this Cause.
 3. READINESS  Assess D/W/P per candidate against frozen thresholds. Record EVERY failed
               prerequisite with its typed reason. FIRST_BLOCK follows the frozen
               D -> W -> P policy order. A scalar readiness without the cause of
               failure is forbidden.
 4. ROUTE      Compute route scores using the LAST COMMITTED operating state Z_{t-1}:
               score = hard_mask(G) * rpm_ready * route_multiplier(region_{t-1}) * V/(r+eps).
               The control action (RUN/CAP/SPLIT/REPAIR/QUARANTINE/HALT) is decided
               here as a TYPED value, separate from all arithmetic.
               If every score is zero: NO_READY_CJT -> RPM opens a repair subgoal or
               the kernel halts. Normalization never divides by zero.
 5. EXECUTE    Run the selected sparse CJTs under the allotted budget. Budget unit is
               CJT_EXPERT_EVALUATION (frozen); every execution and every repair costs 1.
 6. OBSERVE    Record Effect, actual compute, gain, response, and test points.
 7. VERIFY     Determine semantic outcome using the REGISTERED examiner (a pure lookup
               in the exact-outcome table). Region arithmetic never writes this value.
 8. DIAGNOSE   Update region evidence (from usage/readiness observations ONLY — the
               semantic outcome is stored alongside, never folded into region evidence:
               the two-axis discipline) and RPM prerequisite records.
 9. EMIT       The CJT emits BiasUpdateIntent objects. It NEVER writes B directly
               (BiasState is frozen; direct writes raise).
10. COMMIT     The transaction coordinator atomically validates and applies B_{t+1},
               or rejects the WHOLE batch and rolls back (B_{t+1} = B_t). Governance
               fields are owner-only: intents touching G are rejected.
11. TRACE      Seal the complete transition receipt (canonical-JSON SHA-256; replay
               must be digest-identical).
```

## Why ROUTE uses Z_{t-1}

The same-tick causal loop (ASOM depends on execution; routing depends on ASOM) is closed
by construction: routing reads only the last COMMITTED region. This tick's outcome can
influence next tick's route only after COMMIT. Test 6 proves it: flipping the verifier's
registered outcomes changes verdicts and changes NOTHING in any tick's allocation.

## Slow-loop wake conditions (frozen)

The full RPM scan / repair machinery (the slow loop) does not run per token. It wakes on:
a readiness threshold failure; a verifier rejection; residual beyond tolerance; detected
saturation; a goal change; a new skill being learned; NO_READY_CJT.

## Repair semantics (slow loop)

A repair subgoal is typed `(expert, prereq)`. Its signature is the cycle-detection key.
Caging (all enforced, all tested): max depth per governance; max branch count; typed
cycle detection (a signature already on the active stack refuses the subgoal); return
addresses unwound on every exit path; repairs cost budget; prerequisite satisfaction is
cached one-directionally (Correction 2) with the acquisition event recorded, and is
re-verified only on explicit invalidation events.

## Authority

Only the transaction coordinator commits Bias state. A CJT emitting an intent for a
governance field is rejected. One invalid intent rejects its whole batch atomically.
A healthy parent aggregate never hides a failed child: board reports always carry
per-child regions and flags, un-averaged.
