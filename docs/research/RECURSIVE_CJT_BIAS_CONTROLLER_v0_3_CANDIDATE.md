# Recursive CJT Bias Controller v0.3 — CANDIDATE

Status: **CANDIDATE.** RC-0.1 (feedback, action, and evidence closure) is implemented in
deterministic CPU code with every registered control path exercised. The controller-level
status emitted by the closure receipt is decided by the status law of the owner
directive (§14) — see `recursive_cjt_rc0/RC01_FEEDBACK_CLOSURE_RECEIPT.json`. No model,
no GPU, no AWS, no neural code, no claim-bearing data. v0.1 and v0.2 are preserved
unmodified; this document supersedes their EXECUTION semantics only.

Reference implementation: `cas_only_reasoner/recursive_cjt_rc0/sim/rc01_*.py`;
proofs: `tests/test_rc01.py` (28 tests) + amended `tests/test_rc0.py` (17 tests);
scenario matrix: `RC01_SCENARIO_MATRIX.json` (22 scenarios, all paths).

## What RC-0.1 closes (each item = implemented + scenario + test)

1. **The actual CJT transformation** — `CJTStep(cause, bias, allocation, budget) →
   CJTStepResult` with a typed `EffectCandidate`; four distinct registered deterministic
   transformations; untyped inputs refused. The central recurrent equation is now
   simulator behavior, not documentation.
2. **State commit vs Effect publication** — two authority paths. The publication law:
   intended → PUBLISHED; opposite → REFUSED + quarantine path; off_axis → REFUSED +
   repair path; unassessed → typed ABSTAINED. A refused Effect updates diagnostic state
   but never receives publication authority.
3. **The delayed feedback wire** — same-tick independence AND committed-rejection
   next-tick consequence AND uncommitted-verdict inertness, each its own test. The RC-0
   shell test that enforced the severed wire is amended (same-tick scope only, with the
   amendment recorded in its docstring).
4. **The strict RPM ablation** — latent readiness (truth) separated from enforcement;
   ablation removes the gate only; `unready_executions` / `forced_publications` must
   STRICTLY increase (equality fails). The shell's blind metric is documented as such.
5. **Operational actions** — RUN executes; CAP clamps the allocation to the registered
   limit (observable event + counter); SPLIT creates bounded typed child Causes with a
   return address and spends budget; REPAIR opens typed subgoals; QUARANTINE is a
   sealed kernel transition excluding the expert until an owner-authorized reopen; HALT
   seals state and trace FIRST. No action exists as a trace label only.
6. **Distinct recursion gates** — depth / kernel active-branch ceiling / lifetime
   branch ceiling / budget: four counters, four events, four scenarios. Acquisition
   cache (one-directional) + explicit invalidation reopening, both scenario-tested.
7. **Hardened coordinator** — versioned intents (episode, tick, base version + digest,
   verifier receipt digest); rejects stale/wrong-tick/wrong-episode/conflicting/
   governance/unknown-receipt intents; atomic with byte-identical rollback; rejections
   sealed naming the first failed law.
8. **Numeric fail-closed** — bool/NaN/±inf/negative rejected at construction and in
   routing (the shell's `RPMState` accepted NaN — found by the new tests, fixed);
   allocations validated as a simplex post-normalization.
9. **The gold wall** — the `Cause` type cannot carry gold (construction rejects
   gold-shaped markers); the verifier table is sealed; the poison test proves flipping
   gold changes verdicts and zero allocations; changing Cause evidence provably changes
   the candidate set. Desire law enforced: a Desire block deprioritizes
   (`DESIRE_DEPRIORITIZED`) — the kernel never invents relevance.
10. **Scenario matrix + fresh-process replay** — 22 scenarios covering every registered
    path (all outcome classes occur: intended/opposite/off_axis/unassessed/published/
    refused/abstained/repaired/quarantined/halted); per-scenario double-run digests;
    fresh-process replay identical across two OS processes; one mutated input changes
    the digest (the digest was initially insensitive to effect payloads — found by the
    mutation test, fixed by recording the payload).

## Honesty ledger

- The dictionary-slot test is renamed `test_controller_configuration_slot_count_matches`
  and claims SIMULATOR_CONFIG_COUNT_MATCH only. Neural parameter matching does not
  exist yet (see `STATIC_CONDITIONS_v2.yaml` for the measured-quantities contract).
- `RECURSIVE_CONDITIONS_v2.yaml` adds the true full-minus-one arms (R5_MINUS_RPM /
  R5_MINUS_ASOM / R5_MINUS_CAS_OHM); R2/R3/R4 are addition arms and are no longer
  cited as dissociation controls.
- The CAS-Ohm ablation claim is split: verifier-FUNCTION invariance is tested;
  behavioral-outcome invariance is NOT claimed (allocations select different experts).
- The RC-0 default-scenario docstring discrepancy (claimed a wisdom-deficient repair;
  shipped none) is superseded: repairs, blocks, and failure paths now run in the
  registered matrix, not in a happy-path default.
- Everything here is deterministic reference semantics. It establishes NO neural
  capability, no learning improvement, no CAS-specific value, no CAS-Ohm predictive
  validity, no reasoning-machine capability, no efficiency advantage.

## Next owner gate

Gate 1A (documentation + freezing only): exact static neural modules, construction-gold
dataset, independent preservation checker, S0–S7 matching per the v2 compute contract,
effect-size and uncertainty thresholds, AWS environment + container digest, cost
ceiling, owner-signed execution record. Gate 1B (AWS GPU) only after 1A is signed.
