# Versioned native procedure integration plan

Status: design, not completed native integration. The separate
`cncm/procedural_substrate.py` supplies candidate artifacts and bounded execution
only. It grants no installation, promotion, proof, state-write, or continuation
authority. This plan is for a future explicitly versioned CNCM kernel path.

## Existing boundary and usable components

Paths in this plan are relative to the vision-next homebase. Source inspected
2026-09-16. No current v0.1 kernel or authority contract is changed by this plan.

- `cncm/model.py:1212`: MachineState contains episodic memory and a learning
  disposition queue, not a procedural registry or installation records.
- `cncm/kernel.py:620`: a suspended RPM parent admits only RPM push/return and
  halt. `PUSH_RPM` at line 1028 requires a caller-declared prerequisite resolver;
  there is no general capability acquisition continuation.
- `cncm/engine.py:116`: each run boots a fresh per-run state. Replay at line 1008
  uses an exact same-process trusted episodic snapshot, not durable cross-process
  procedure recovery.
- `cncm/cognitive_apprenticeship.py:553`: finite straight-line procedure
  interpreter. The six-instruction linear solver at line 2315 computes `(c-b)/a`.
  VersionedTeachingStore and its local promotion receipts are not kernel state
  or authoritative qualification.
- `cncm/math_kernel.py:560`: VERIFY_LINEAR_SOLUTION checks the proposed value by
  substitution into the original exact equation. `check_math_step` at line 601
  and `verify_math_receipt` at line 619 reconstruct the result independently.
- `cncm/model.py:1399`: TraceEvent retains complete proposed intents, providing a
  useful basis for future semantic transition replay.

## 1. New authority and wire version

AUTHORITY_MANIFEST.yaml prohibits procedural learning in runtime 0.1.0. Introduce
a narrow runtime/KIR 0.2 contract admitting exact-rational procedures only.
Preserve 0.1 packet, state, hash, schema, fixture, and behavior compatibility.
Do not silently widen the existing version or repurpose WRITE_EPISODE.

Add versioned problem, state, RPM, proof, evidence, and recovery schemas; add
procedure artifact, qualification, execution, and lineage contracts. The
unchanged protected arithmetic checker may retain cncm.math-checker/0.1.
Bind exact checker/interpreter/contract source identities in admitted records.
Teacher and candidate enumerator remain proposal-only; the coordinator remains
the sole writer. No teacher controls fixtures, checker, qualification result,
promotion, rollback policy, or state. Constitutional and external action
authority remain outside this path.

## 2. Native state and suspended call

Extend the versioned state in cncm/model.py with immutable procedure artifacts,
active capability-version heads, qualifications, executions, and rollback
lineage. These records participate in the native state hash. Do not create an
external capability store and describe it as MachineState integration.

Extend the versioned RPM frame with a discriminated acquisition continuation:
parent goal and branch, pending call ID, input digest, exact output contract,
resume stage, missing capability, parent branch digest, and budget reservation.
The frame captures the existing caller, not a newly constructed equivalent run.
There is no answer in the suspended continuation.

A call `solve-linear(a,b,c)->x` may establish a checked predicate such as
`verified_solution(call_id)`. Retain the actual x and complete checker receipt
in a typed execution record. Bind that record into a new checked proof operation;
do not smuggle x into an asserted fact, provenance string, or proof boolean.

## 3. Actual coordinator transitions

Modification points in cncm/kernel.py:

- ALLOWED_INTENTS at line 53 and EXPECTED_CAPABILITIES at line 72.
- Suspended-parent restrictions at line 620 and exact mutation shapes at 632.
- PUSH_RPM at 1028 and RETURN_RPM at 1095.
- Target scopes at 1510, aggregate budget enforcement at 1633, application at
  1806 onward. Extend conflict keys and semantic replay accordingly.

Add INSTALL_PROCEDURE, APPLY_PROCEDURE, and ROLLBACK_PROCEDURE. Extend versioned
PUSH_RPM/RETURN_RPM with an acquisition-frame kind. INSTALL_PROCEDURE is admitted
only for the active acquisition child after coordinator-side reconstruction of
qualification evidence; it changes the native registry and lineage atomically.
It establishes no mathematical proposition or commitment.

RETURN_RPM checks that this exact child installed the requested artifact, pops
only the matching top frame, and resumes the saved pending call. APPLY_PROCEDURE
executes the pinned bytes, independently verifies the candidate result, and
commits only a branch-local checked result. Normal parent inference, comparison,
and commitment gates then run. Replay of an old return or install fails its
state/frame/version preconditions.

ROLLBACK_PROCEDURE changes the active head to a recorded qualified ancestor, or
to absence for a first installation. Preserve all immutable records and prior
independently checked mathematical results. Reject stale rollback heads, foreign
lineage, invented ancestors, and concurrent head changes.

## 4. Candidate substrate and bounded acquisition

The isolated substrate uses three LOAD_INPUT instructions, one ADD_EXACT or
SUBTRACT_EXACT, one DIVIDE_EXACT, and one EMIT_REGISTER. The first three loads
are a permutation of a,b,c, giving twelve finite candidates. There are no
literal-answer, constant, lookup, dynamic import, evaluation, branch, or loop
instructions. Candidate provenance is self-described and unauthenticated.
Content hashes bind provenance but do not authenticate it.

Exact input numerators/denominators are bounded to at most 128 bits; intermediate
arithmetic is bounded to at most 512 bits. Decimal text is bounded before regex,
integer conversion, and gcd. Cross-product and addition bounds are checked
before multiplication or addition allocations. Conservative refusal is allowed
even when later cancellation might yield a small number. Instruction count alone
does not bound arbitrary rational-arithmetic growth.

Enumerate only the declared finite grammar. Use development cases for selection,
seal the selected artifact, then qualify it using disjoint independently
custodied cases and rejection cases. Record source, dataset/split, checker,
candidate, and budget identities. This is finite program selection from an
authored grammar, not neural program synthesis or unrestricted discovery.

## 5. Independent result checks

Build the original equation from the exact bound call inputs. Feed the procedure's
candidate x into MathStepOperation.VERIFY_LINEAR_SOLUTION. The protected checker
verifies by substitution, then the coordinator reconstructs that receipt.
Bind input, artifact, call, branch, theory, checker version, and receipt bytes.
Never call solve_math to produce an answer behind the learned procedure.

Qualification supplies bounded admission evidence, not a universal proof over
all rational inputs. Every later invocation still requires its own checker
acceptance. Reject zero-divisor/unsupported cases rather than inventing a result.

## 6. Scheduler, budgets, and fresh-process recovery

Refactor cncm/engine.py:116 into start/advance/resume over existing native state.
Add acquisition handling beside _resolve_missing_with_rpm at line 525. The
parent cannot advance while the acquisition frame is active.

Charge candidate execution, selection, qualification, checker work, installation,
and return to explicit bounded shared counters. Reserve enough work for a traced
failure/return. Resume uses current debited counters; restoring the parent's old
snapshot must never refill them. Policy work units are not measured FLOPs,
joules, or cloud dollars. Record exact deterministic costs or frozen conservative
caps and reject before exceeding them.

Add a native recovery API that reconstructs state from a trusted versioned
genesis and replays the transition journal through the same coordinator. Recheck
artifact identities, qualifications, arithmetic receipts, branches, continuation,
versions, budgets, and every pre/post state hash. A host adapter may atomically
persist journal/checkpoint bytes; it cannot populate learned state directly.
Current bundle consistency checks and same-process replay are insufficient.
Hash chains check integrity but do not authenticate ownership by themselves.

## Acceptance episode

1. Start with no installed solver. Parent receives a=3,b=5,c=26 and requests a
   checked solution. It suspends with no x=7 stored in its call or frame.
2. Select and independently qualify the six-instruction procedure. Observe an
   INSTALL_PROCEDURE transition in native state and trace.
3. Resume the identical pending call with remaining debited budget. Execute the
   installed bytes, obtain x=7, independently check it, then complete the normal
   parent inference and commitment path.
4. Restart the process from the native journal. Supply a=-4,b=7,c=13 and reuse
   the installed procedure without teacher access, yielding checked x=-3/2.
5. Roll back through a native transition. A later call uses the restored head or
   requests acquisition if the first installation was removed.
6. Reject forged/resealed qualification, wrong caller/input/version, teacher as
   examiner, stale state, budget refill, a=0, literal-answer substitution,
   corrupt artifacts, invalid rollback lineage, and semantically invalid replay.

Passing this episode would demonstrate bounded native procedural acquisition,
exact continuation, checked reuse, and rollback. It would not establish general
learning, neural assembly, CAS-Ohm competence, or complete-machine status.
