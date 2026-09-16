# Proposed derived-result memory acceptance plan v0.6

Status: **HISTORICAL DESIGN AND ACCEPTANCE PLAN.**

The proposed gates and examples below are preserved as planning history. The
implemented contract is `spec/CNCM_DERIVED_MEMORY_v0.6.md`; actual run status is
`records/derived_memory_001/STATUS.md`. The implementation and final runtime
reproduction now exist. This plan itself is not a passing-run receipt, and its
illustrative API/sequence wording must not override the versioned contract.

This is a machine-facing acceptance and reproduction plan. It does not report a
passing runtime, complete Phase 3, or establish independently verified world
facts, general memory, general learning, or a CAS-specific advantage. No UI,
model, provider, AWS execution, or paid compute belongs to this plan.

## 1. Charter and existing evidence

The controlling source is `cas_reasoner.txt`. Relevant one-based source lines:

| Source lines | Requirement | Proposed bounded evidence |
| --- | --- | --- |
| 7944–7988 | Working, episodic, semantic, procedural and constitutional memory; distinguish types of ignorance | Keep a suspended caller separate from append-only episode evidence and checked derived records; preserve distinct missing, stale, contradicted and unsupported states. This is not all five memory classes. |
| 12899–12924 | Build memory, planning and verification together; distinguish their contents | An actual native parent obtains a missing checked scalar through an RPM child, then reuses it in another episode. |
| 12927–12951 | Content/type/provenance/confidence/status/time/use/history/source/refresh metadata | Bind the derived record to its exact claim, verifier, source/definition revisions, logical creation/use events and explicit freshness policy. Do not invent a probability or physical decay model. |
| 12957–12986 | RPM target, local workspace, saved return address, resume stage and conditions | Check every saved parent field, frame identity, child result and remaining budget before return. |
| 12990–13029 | Independent verifier and typed dispositions | Frozen exact arithmetic/proof checking remains enabled while new candidate generation can be disabled. A resealed false receipt must fail. |
| 13031–13070 | Combined demonstration and Phase 3 exit gates | Demonstrate exact prior-memory influence, trace attribution, correct child return, invalid-proof rejection, bounded recursion and distinct missing-knowledge/capability failures. This bounded example does not establish the entire exit gate or qualification targets. |
| 13689–13708 | Integrated steps 10–12 and 17–19 | Exercise a real missing prerequisite, exact return and an explicitly identified fixture correction affecting a later task. Public engineering variants are not a protected held-out learning study. |

The latest appendices in `docs/CNCM_COMPLETE_REQUIREMENT_LEDGER.md` and the
native/nested/semantic/compound status records govern current implementation
claims; older summary rows predate those checkpoints. Runtime 0.5 already
retains procedure artifacts, source history and execution records. Its ordinary
new calls recompute arithmetic. `MemoryRef` recalls active `SourceStatement`
heads; it does not name a stored checked result.

Reusable implementation and evidence anchors:

- `cncm/compound_engine.py`: `CompoundMachine.start`, `advance`, `run`, `journal`.
- `cncm/compound_kernel.py`: protected source substitution, saved acquisition
  frames, checked execution records and `_trusted_root_keys`.
- `cncm/compound_verification.py`: `verify_original(inputs, x)` checks the
  original expression by substitution without solving for the candidate.
- `cncm/math_kernel.py`: `check_math_step` and `verify_math_receipt` reconstruct
  the exact proposed formal step independently of candidate solving.
- `cncm/compound_recovery.py`: externally anchored full journal reconstruction.
- `tools/reproduce_compound_construction.py`: all-cut fresh-process replay,
  disabled acquisition aliases on new tasks, exact budgets and rollback probes.
- `tests/test_compound_recovery.py`, `tests/test_semantic_recovery.py` and
  `tests/test_nested_recovery.py`: source chronology, rejected proposal retention,
  exact continuation and refusal of fresh-budget restart with unresolved frames.

`records/derived_memory_001/design_probe_001/receipt.json` is only a frozen
formal-checker design probe. It accepts `y=5` for `2*y+1=11`, rejects `y=6`, and
checks the corrected RHS 17 independently of the solver. Its receipt explicitly
does not establish source custody, memory scope or runtime integration.

## 2. Proposed API and version boundary

The builder's high-level API, pending final closed wire contracts, is:

```text
DerivedResultRef(scope, key, evidence_requirement='CHECKED_FORMAL_DERIVATION')
DerivedDefinition(scope, key, revision, supersedes, variable, parameters)
create_problem(parameters, variable, definitions=(), updates=(),
               store_result=None, budget=..., ...)
DerivedMachine(trusted_ingress=(...))
machine.start(problem, ...)
machine.advance(allow_generation=bool, allow_acquisition=bool)
machine.run(problem=None, allow_generation=bool, allow_acquisition=bool, ...)
```

Definition parameters `a,b,c,d,e` admit exact rational literals, existing
scoped `MemoryRef` values and `DerivedResultRef` values used to authorize exact
saved-consumer lineage. Parent parameters admit the same scalar forms.
`store_result`, when requested, names a derived-result destination. First-version
acquisition does not execute definitions that request derived references. This limit
does not excuse missing transitive freshness checks for saved consumer results.
Exact field names, bounds, enum values and schemas remain subject to the new
model contract; the sketch is not an implemented API promise.

Use new runtime/profile/state/intent/journal/schema identities. Preserve every
accepted 0.1–0.5 source profile and receipt-bound artifact byte-for-byte. Old
coordinators must reject new intents and wire versions. A plausible issuer,
digest, schema-valid object or imported saved state grants no new authority.

The coordinator is the sole durable writer. Definition/source admissions require
the exact externally supplied ingress authority and supersession chronology.
Definition parameters become formal assumptions only through that explicit
boundary. A mathematical receipt proves the stated derivation conditional on
those premises; it cannot upgrade their factual evidence status.

Two authorized origin paths must remain explicit:

1. A checked child derivation may supply the missing scalar through its governed
   child-result/storage/return stages before the outer parent commits. The exact
   independent proof and saved continuation authorize that return.
2. A requested store of the compound parent's result occurs after its exact
   commitment and before HALT. A raw executor output or merely proposed branch
   is not a committed compound-result record.

The existing 0.5 `advance()` immediately halts after commitment. The new stage
must belong to the new version; do not alter that frozen behavior.

## 3. Gate A: a missing checked scalar becomes an RPM child

Admit one identified engineering definition for `math-demo/y`, revision 1:

```text
variable y; a=1, b=2, c=1, d=0, e=11
formal equation: 1*(2*y+1)+0=11
```

The parent supplies:

```text
2*(3*x+DerivedResultRef(math-demo, y))+7=35
```

It contains neither `y=5` nor a candidate proof. Empty derived memory is a real
missing prerequisite. Required path:

```text
parent blocked on y
→ bounded child frame preserves parent inputs, goal, branch and resume stage
→ candidate y=5 is proposed
→ independent formal checker reconstructs y=5 from the admitted equation
→ governed checked record and exact child return
→ parent resolves c=5
→ ordinary compound execution/check/commit yields x=3
```

If the initial procedure is absent, the existing primitive/compound acquisition
path must also remain real and use the same conserved episode budget. Acceptance
records the actual maximum stack depth and each frame kind; no fabricated depth
or pre-populated procedure substitutes for the cold path.

In a later episode, submit `2*(3*x+ref(y))+7=41`. After authenticating history,
disable new generation and acquisition. The machine must recall the checked
`y=5`, perform the current compound call and conclude `x=4`. The stored answer
and the later answer differ. Trace and resolved-input evidence must identify the
exact derived record used; the request contains no cached numeric value.

Supersede the definition with RHS 17 under externally admitted revision 2.
With generation disabled, the old `y=5` record must refuse as stale before any
consumer execution. In a separately authorized generation-enabled continuation,
derive and check `y=8`; the same later parent now concludes `x=3`. Preserve both
records and the invalidation/refresh evidence. Failure to refresh is not proof
that no mathematical solution exists.

## 4. Gate B: stored compound result becomes another task's input

This stronger chain distinguishes retained execution history from actual
machine-consumed derived memory. Use scoped fixture source `offset=5` and an
explicit requested result destination `producer/x`.

| Episode | Task | Required outcome |
| --- | --- | --- |
| B1: producer | `2*(3*x+MemoryRef(offset))+7=35` | Independently checked and committed `x=3`; coordinator stores revision 1 with the original expression, inputs, execution/proof and source lineage. |
| B2: consumer | `DerivedResultRef(producer, x)*(2*y+1)+4=28` | With new generation/acquisition disabled, recall `3`, execute the consumer and conclude `y=7/2`. No producer procedure is executed again. |
| B3: invalidation | Admit exact source correction `offset=8`; submit the same consumer with generation disabled | A typed stale-derived-result refusal occurs before consumer execution/commit. The old record remains in history. |
| B4: refresh | Re-run the producer with installed procedures, acquisition disabled, and the requested result destination | Checked `x=2` becomes a new revision through the governed storage path. |
| B5: later consumer | Repeat B2 against current derived memory | Conclude `y=11/2`, with revision-2 provenance and current-call checking. |

The consumer request does not contain the producer's answer or resupply its
source scalar. Assert this structurally, not by an incidental string search.
B1–B3 are the minimal proof of reuse plus invalidation; B4–B5 close the practical
correction-and-reuse loop. Store B2's consumer result in a variant, then correct
the producer's source: that downstream saved record must also become stale.
This transitive freshness test does not require nested derived-definition
acquisition, which remains out of scope for the first version.

## 5. Required invariants and probes

1. **Exact proof join.** Definition, source assumptions, normalized expression,
   candidate, proposal, checker receipt, scope, variable, episode, origin call
   and source profile agree. Borrowing a valid proof from another input or
   variable must fail even if the proposed numeric output happens to match.
2. **Independent checking.** A resealed false proposal/receipt is rejected by
   reconstructed checker behavior. Generation cannot grade itself, alter the
   checker or directly write a binding, memory head, parent result or commitment.
3. **Freshness covers the full source set.** Recompute all active heads for every
   dependency, not only whether recorded heads remain present. Test correction,
   retraction, newly conflicting source, same-value new revision, superseded
   definition, changed checker/profile, missing proof dependency and unrelated
   scope retention. Current policy must define same-value revision behavior.
4. **Transitive freshness.** Saved consumer records retain the full checked
   dependency closure. Reject missing witnesses, cycles, excess depth/count and
   stale ancestors without silently falling back to an older result.
5. **Scoped authority and statuses.** Cross-scope collisions, untrusted
   definitions, forged stronger evidence requirements and self-authorizing
   journals fail closed. Preserve TEST_FIXTURE/USER_ATTESTED premises as such.
   Missing, stale, contradicted, malformed proof, disabled generation, missing
   procedure and exhausted budget remain distinguishable causes.
6. **Working-memory isolation.** While the parent is suspended, preserve its
   original inputs, branch, goal, return address and resume stage. Only the exact
   successful top-child return binds its missing scalar. Wrong return IDs,
   altered caller snapshots and duplicate returns cannot overwrite it.
7. **Append-only history.** Corrections, stored revisions, supersession and use
   events preserve earlier records. Creation/last-use identify deterministic
   logical events. Confidence may explicitly be uncalibrated/unsupported; do not
   invent a numeric probability. Refresh is evidence-based, not an implied
   elapsed-time decay model.
8. **Conserved work.** Freeze policy allocations for generation, proof checking,
   storage, retrieval, freshness and substitution. Failed expensive checks keep
   their charges; malformed envelopes cannot trigger expensive work. No resume
   refunds or unearned new budget. Report policy units separately from CPU time.
9. **Procedure permission remains separate.** Rollback retains historical
   derivations and source evidence but blocks unauthorized future dispatch. A
   remembered answer cannot bypass the current task's procedure/check/commit
   gates, and recall must not reinstall a rolled-back capability.
10. **Closed representation.** Refuse unknown fields/versions, bool/int/float
    aliases, duplicate JSON keys, malformed exact rationals, unbounded graphs,
    over-wide scalar composition, mutable caller aliases and partial writes.

## 6. Generator-disabled continuation and restart evidence

The two controls have separate meanings: `allow_generation=False` prevents new
derived candidates; `allow_acquisition=False` prevents new procedure acquisition.
Acceptance must instrument the actual called aliases, not merely pass flags.

After historical reconstruction, patch the new generation entry point and all
new-call acquisition aliases to raise and count attempts. Current known aliases
include `construct_program`, `qualify_program`, `select_finite_candidate` and
`qualify_procedure`; the final list must follow actual 0.6 imports. During proof
admission/reuse probes, also forbid `math_engine.solve_linear_equation` and
`math_engine.verify_math_result` as substitutes for the independent step gate.
Keep `check_math_step`, `verify_math_receipt` and actual consumer-call checking
enabled. Count producer dispatch separately from proof rechecking.

Historical recovery replays earlier acquisition/generation to authenticate the
recorded history. It therefore cannot honestly be described as generator-disabled
throughout the fresh process. Record two distinct phases:

```text
historical reconstruction under the pinned accepted profile
→ enable refusal instrumentation for future work
→ new continuation with generation/acquisition disabled
```

For every main, refresh and refusal episode, retain cut 0 and every sealed event
boundary through terminal completion. Include child push, candidate/check/store,
return, resolved inputs, parent execution, commitment, result store and halt;
rejected and malformed proposal occurrences also count. An event is the atomic
pause boundary; do not claim crash safety inside uncommitted Python operations.

A different process reconstructs each externally anchored prefix and requires:

- exact prefix journal equality before continuation;
- exact final state, full trace, proposal batches, saved frames, records, heads,
  remaining budgets and complete journal equality after continuation;
- the same external genesis, initial ingress and ordered boundary extensions;
- the same source-profile/checker bytes and caller-held expected journal digest;
- no serialized-state import or authority inferred from journal metadata;
- no fresh-budget episode while any unresolved native frame remains.

For reuse/stale cuts, reconstruct history first and install refusal instrumentation
before continuing the cut. Keep historical and new-call attempt counts separate.
Preserve every failed initial run in a unique directory before any repair.

## 7. Required acceptance artifacts and remaining gates

A new reproducer should retain original problems and definitions, external
ingress chronology, source/profile hashes, all journal anchors, complete results,
derived records and verifier evidence, an all-cut table, actual parent/child PIDs,
disabled-function attempt counters, failure cases, budgets and file hashes.
The all-cut table reports observed counts; it does not hard-code a convenient
number of transitions. Include a clean control that lacks the target record and
cannot conclude with generation disabled, without deleting authoritative state.

The final acceptance statement requires both Gate A and Gate B, freshness and
adversarial probes, separate-process all-cut reproduction, appropriate full-suite
checks and unchanged earlier source profiles. Schema tests prove shape only;
source authority and mathematical/runtime validity require the independent checks.

Exact metadata fields, costs, enums and public recovery APIs must be frozen with
the implemented model before schema promotion. Proposed ownership is new
`schemas/derived_v0_6/*` and `tests/test_derived_v06_schemas.py`, separate from
builder core modules/tests, reviewer adversarial tests and root reproduction.

Even a passing bounded acceptance would leave general semantic concepts,
similarity retrieval, forgetting/lacunarity, broad verifier federation, protected
held-out learning, full D/W/P/Foundation semantics and the complete integrated
20-step episode open. Any claim of automatic recursive refresh beyond this
bounded contract requires its own real child/return acceptance.
