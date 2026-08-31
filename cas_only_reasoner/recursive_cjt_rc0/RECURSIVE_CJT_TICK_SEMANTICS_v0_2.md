# Recursive CJT Tick Semantics v0.2

Part of PHASE RC-0.1. Supersedes `RECURSIVE_CJT_TICK_SEMANTICS_v0_1.md` (preserved).
Status: implemented and enforced by `sim/rc01_engine.py`; every law below is covered by
a test in `tests/test_rc01.py`. Still PROPOSED_UNTESTED as an architecture claim — this
is deterministic reference semantics, not neural behavior.

## The frozen RC-0.1 tick

```
 0. AUTHORIZED EVENTS   Owner-authorized reopen events land (sealed REOPEN transitions).
 1. READ                Authoritative B_t (+ versions + digests) from the coordinator.
 2. CANDIDATE           From NON-GOLD Cause evidence only: an expert is a candidate iff
                        its registered structural markers intersect Cause.evidence.
                        The router has no access to gold fields — the Cause TYPE cannot
                        carry them (construction rejects gold-shaped markers), and the
                        verifier's table is sealed (name-mangled, no accessor).
 3. READINESS           LATENT readiness (the truth) is always computed from D/W/P.
                        ENFORCEMENT is a separate flag: disabling RPM removes the gate,
                        never rewrites the truth. Typed FIRST_BLOCK always recorded.
 4. ROUTE               score = hard_mask · enforced_ready · κ(region_{t-1}) · V/(r+ε),
                        numeric fail-closed (bool/NaN/±inf rejected; allocation must be
                        a valid simplex). Quarantined experts route at exactly 0.
                        All-zero handling:
                          - Wisdom/Power block  → REPAIR subgoal, then RETRY the cause once
                          - Desire-only block   → DESIRE_DEPRIORITIZED (never invent relevance)
                          - quarantined route   → ROUTE_UNAVAILABLE_QUARANTINED, skip cause,
                                                  episode continues (reopen possible later)
                          - structurally dead   → typed HALT (state+trace sealed first)
 5. DISPATCH            The typed ControlAction is EXECUTED, not logged:
                          RUN         execute the chosen CJT (1 budget unit)
                          CAP         allocation clamped to the registered limit and
                                      renormalized (CAP_ENFORCED event + counter)
                          SPLIT       bounded typed child Causes created with a return
                                      address; registered budget cost spent
                          REPAIR      typed RPM prerequisite subgoal opened
                          QUARANTINE  kernel-authorized sealed transition; excluded from
                                      routing until an authorized reopen event
                          HALT        state and trace sealed FIRST, then stop
 6. EXECUTE             CJTStep(cause, bias, allocation, budget) → CJTStepResult with a
                        typed EffectCandidate (never a bare display string); each expert
                        performs a distinct registered deterministic transformation.
 7. OBSERVE             Compute used, consecutive-use counters, observations.
 8. VERIFY              SealedVerifier lookup → (verdict, receipt digest); the receipt
                        is registered with the coordinator.
 9. PUBLICATION LATCH   A SEPARATE authority from state commitment:
                          intended   → PUBLISHED
                          opposite   → REFUSED + QUARANTINE consequence path
                          off_axis   → REFUSED + REPAIR consequence path
                          unassessed → ABSTAINED (typed)
                        A refused Effect may still update diagnostic state; it never
                        receives publication authority.
10. DIAGNOSE            Region evidence from usage/readiness ONLY (two-axis law); the
                        verdict is stored beside it, never folded into region evidence.
11. EMIT + COMMIT       VersionedIntents (episode id, tick, base state version + digest,
                        verifier receipt digest) → hardened atomic commit. One invalid
                        intent rejects the whole batch; rejections are sealed with the
                        first failed law; state stays byte-identical.
12. CONSEQUENCE         ONLY IF COMMITTED: the verdict's consequence path runs
                        (quarantine / repair), changing NEXT-tick readiness, region,
                        routing, or RPM state. An uncommitted verdict changes nothing.
13. TRACE               Canonical-JSON SHA-256 seal; fresh-process replay is
                        digest-identical; a single changed input changes the digest.
```

## The repaired temporal law (the delayed wire)

- Current tick: the allocation is independent of the verdict produced in that tick
  (`test_current_tick_route_independent_of_current_verdict`).
- Next tick: a COMMITTED rejection changes readiness, region, routing, quarantine, or
  RPM state (`test_committed_rejection_changes_next_tick_state_or_route`).
- An UNCOMMITTED verdict changes nothing
  (`test_uncommitted_verdict_cannot_change_next_tick`).

The RC-0 shell's old test enforced full-sequence identity under flipped verdicts — a
severed wire. That test is amended to same-tick scope; the delayed wire lives here.

## The repaired RPM ablation law

`latent_readiness` (truth, from D/W/P) and `rpm_enforcement_enabled` (the gate) are
separate. Ablation removes the gate only. Metrics that can SEE the failure:
`unready_executions` (executed while latent readiness false) and `forced_publications`
(published while a prerequisite was false). The ablation test requires a STRICT
increase — equality fails.

## Recursion caging (distinct gates)

`max_depth` (chain depth), `max_active_branches` (kernel-level concurrent ceiling, in
addition to per-expert governance), `max_total_branches` (lifetime ceiling), compute
budget — four separate counters, four separate events, each with its own scenario.
Acquisition cache is one-directional (Correction 2); an explicit invalidation event
reopens the prerequisite. Return addresses unwind on every exit path.
