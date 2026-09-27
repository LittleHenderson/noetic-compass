# CNCM native procedures authority and kernel IR v0.2

Status: **BOUNDED IMPLEMENTATION — acceptance evidence retained separately.**
This document defines the opt-in profile; it is not an acceptance receipt, an
amendment to runtime 0.1.0, or evidence of general native learning completion.
Exact implementation, replay, compatibility, and adversarial test outcomes are
recorded in records/native_procedure_001/STATUS.md. The existing
AUTHORITY_MANIFEST.yaml and v0.1 contracts remain unchanged by this document.

## 1. Source and scope

The controlling homebase charter is cas_reasoner.txt, SHA-256
`a72312231bfb346dc4895b1a0963e0c255d26b707c8a4fbc94d90ac52979dfea`.
Its sole-writer, exact RPM return, verification, and rollback requirements govern
this design. Existing spec/AUTHORITY_CONTRACT_v0.1.md and
spec/CAS_KERNEL_IR_v0.1.md define the preserved default profile.

The new profile is runtime **0.2.0** with versioned native procedure state and
coordinator behavior. It admits one bounded capability: proposing an exact
rational solution to `a*x+b=c`, for canonical bounded rational inputs with
`a != 0`, through a sealed six-instruction candidate and independent exact
substitution checking. Arithmetic and checker bounds remain explicit.

Finite selection among twelve authored program forms is the acquisition method.
It is not neural program synthesis, arbitrary program discovery, unrestricted
mathematics, or a claim of general intelligence. The qualifier uses public fixed
engineering panels. They are not secret exams, authenticated human custody, or
independent empirical evidence of generalization. Every deployed call is checked
again. CAS-Ohm, confidence, teacher identity, and selection rank have no proof,
permission, write, or promotion authority on this path.

## 2. Version and sole-writer boundary

Runtime 0.1.0 remains the default. Its accepted problem, state, intent, proof,
trace, and evidence wire forms and their hashes must remain unchanged. Adding
members to a v0.2 enum union must not make those members accepted by a v0.1
coordinator. A v0.1 coordinator must reject each new intent, including an intent
with a plausible issuer or capability string. Unknown versions fail closed.

MachineStateV2 extends native MachineState with procedure records; a versioned
coordinator owns validation and transition application. Shared hooks may preserve
the existing atomic-tick implementation, but hook defaults must leave v0.1
behavior unchanged. The native StateStore/coordinator commit path remains the
only writer. No separate teaching store, registry dictionary, wrapper, or host
checkpoint loader may substitute for native transition application.

Teachers and selectors propose immutable data. The mathematical checker issues
reconstructible mathematical receipts, not installation authority. The
coordinator decides whether a typed state transition is admitted. Trace recording
observes and seals the result; it grants no authority. Role strings are logical
software boundaries, not operating-system authentication or cryptographic
principal identity.

## 3. Versioned state

MachineStateV2 must retain and hash all of the following:

- Complete immutable procedure artifacts, including exact program, contract,
  interpreter revision, bit limits, revision, provenance, and content digest.
- Active procedure heads indexed by the declared capability key, with immutable
  version lineage and previous-head pointers.
- Finite-selection records and engineering qualification records, bound to their
  exact policy, checker, candidate artifact, and costs.
- Checked execution records bound to call, input, procedure version, original
  branch, inner mathematical proof scope, theory, and checker revision.
- Pending calls, their lifecycle, and acquisition continuations.
- Monotone per-run procedural work counters, reservations, and charged-work
  records, including checks that failed to admit a requested mutation.
- Episode lineage linking a new authorized episode to the preceding terminal
  coordinator state and retained transition journal.

Records are canonical immutable snapshots. Caller mutation after an intent or
record is constructed cannot change its content, digest, or later execution.
Identifiers and state hashes bind the actual bytes; a digest alone proves neither
correctness nor authenticated provenance. Versioned deserializers reject unknown
fields, wrong raw types, floats, invalid integer bounds and duplicate registry
identities. CanonicalRecord bodies are bounded immutable canonical JSON with a
closed record-kind set. Decoding alone does not validate their historical links
or grant authority. Recovery reconstructs every record and cross-record link
through coordinator transitions; saved state and record bodies are never imported
as authoritative state. JSON Schemas describe shape, not semantic acceptance.

## 4. Exact additional issuer matrix

The following triples are admitted only by the 0.2 coordinator, in addition to
the preserved v0.1 triples applicable to the current state:

| Issuer | Intent | Required capability |
|---|---|---|
| `procedure_controller` | `REQUEST_PROCEDURE_CALL` | `request_typed_procedure_call` |
| `rpm_controller` | `PUSH_ACQUISITION` | `suspend_for_procedure_acquisition` |
| `procedure_controller` | `SELECT_PROCEDURE` | `select_finite_candidate` |
| `procedure_controller` | `INSTALL_PROCEDURE` | `install_checked_procedure` |
| `rpm_controller` | `RETURN_ACQUISITION` | `resume_exact_procedure_caller` |
| `procedure_controller` | `APPLY_PROCEDURE` | `apply_checked_procedure` |
| `procedure_controller` | `ROLLBACK_PROCEDURE` | `rollback_procedure_head` |

Unknown issuer/intent/capability triples reject. An issuer must be enabled and
scheduled. Intent envelopes retain exact tick, current state-hash precondition,
content-derived identity, branch/goal binding, and target-scope validation.
No new intent authorizes file/network access, tools, arbitrary code, mutation of
the checker, constitutional changes, or bypass of commitment gates.

## 5. Call request and acquisition suspension

REQUEST_PROCEDURE_CALL records a unique typed pending call, not an output. The
call binds its original run, goal, branch, capability requirement, exact a/b/c
inputs, input digest, output contract, and continuation stage. It contains no
expected x, answer literal, caller-selected proof, hidden target, or permission
to skip verification. Reject a closed/discarded branch, stale caller, duplicate
call identity, unsupported contract, or inputs outside the bounded schema.

If an admitted active head is available, bind that exact version for application.
If no head is available, PUSH_ACQUISITION may suspend the existing caller. It
must not construct a new equivalent parent episode or claim that a restart is
a resume. The acquisition frame binds:

- Unique frame, child-goal, parent-goal, original run, branch, and pending-call
  identities, with next stack depth and cycle checks.
- Exact input and output-contract digests and the missing capability key.
- Saved parent branch content digest and exact return stage/address.
- The parent budget snapshot and the admitted child work allocation, including
  enough remaining transition budget for a traced failure/return or halt.

The frame is valid only for the exact pending call in the current state. An
available parent inference or exact recall must not be hidden by unnecessary
acquisition. Once suspended, the parent may not infer, compare, commit, write an
episode, apply a different procedure, or change its caller data. Only the
matching child acquisition actions, return/failure, and governed halt are
admitted. Nested depth/cycle rules remain bounded. Candidate or qualification
records cannot override the saved return address, branch, goal, or budget.

## 6. Selection and installation

SELECT_PROCEDURE operates only within the matching active acquisition child.
It reconstructs the declared twelve candidates and runs only the frozen public
development cases. The candidate grammar is exactly the substrate's closed
six-instruction grammar: three distinct a/b/c loads, ADD_EXACT or SUBTRACT_EXACT,
DIVIDE_EXACT, and EMIT_REGISTER. No constants, literal answers, lookup, dynamic
imports, evaluation, jumps, or loops are admitted. Selection records the full
candidate identities, development checks, unique selected artifact or typed
selection failure, and charged work. Selection supplies a proposal, not truth or
installation. Qualification cases must not choose the candidate.

INSTALL_PROCEDURE binds the active child, exact sealed proposed artifact,
capability key, current prior head, and frozen qualification policy. If a
selection record exists, the artifact must match it exactly. The coordinator also
accepts a directly proposed artifact when no selection exists, subject to the
same closed grammar, full qualification, work charge, and installation gates.
The supplied native host uses the finite selector; neither proposal route grants
installation authority by itself. Before any
qualification work it must pass cheap authority, shape, scope, version, digest,
stack, prior-head, and budget-reservation checks. The coordinator reconstructs
qualification from the artifact bytes using the independently implemented
substitution checker and the fixed engineering panel. Supplied receipt booleans,
labels, digests, or local teaching-store status are insufficient.

Installation requires both exact reconstruction and the reconstructed status
`ENGINEERING_PANEL_PASSED`. In particular, verify_qualification returning true
for an authentic `ENGINEERING_PANEL_FAILED` report does not authorize installation.
An obvious proposer/examiner identity collision is rejected; role labels do not
establish stronger external custody than actually exists.

An accepted install atomically records artifact, qualification, lineage, and
active head in MachineStateV2. A refused install changes none of those records or
heads, but spent checking allocations remain charged and traced. Installation
establishes no parent proposition, mathematical answer, global commitment, or
external action. Reinstalling or retrying the same artifact requires current
state/version/child binding and does not bypass work accounting.

## 7. Exact return and application

RETURN_ACQUISITION must match the top acquisition frame and exact pending call.
Success requires that the same child installed the required admitted artifact
and that the saved parent branch/call/input binding remains unchanged. The
coordinator pins that artifact to the pending call, restores the original parent
goal and return stage, and pops exactly one frame. Failure records a typed reason
and returns or halts without supplying a result. A wrong child/frame/branch,
unrelated capability, changed input, duplicate return, or forged success rejects.

Return uses the current debited shared budget. The saved parent budget is an
integrity bound, never a value to restore or refund. Resumption must not invoke a
fresh boot, reset counters, substitute a new parent, or run the teacher again.

APPLY_PROCEDURE uses the exact call-bound active artifact. It validates the
artifact and input schema, reserves work, and executes those bytes as the sole
producer of candidate x. It must not call solve_math or another answer-producing
solver behind the artifact. A=0, division failure, arithmetic limit, insufficient
budget, wrong version, or checker refusal supplies no checked result.

The protected CAS-Math VERIFY_LINEAR_SOLUTION operation checks x against the
original equation constructed from the bound inputs. Runtime 0.1's mathematical
checker retains its fixed `math_root` branch. The outer checked record binds the
actual caller and branch; no inner proof is silently relabeled as if that checker
supported arbitrary branches. Future changes to this checker scope require their
own version and evidence.

The accepted checked execution becomes a native branch-local result, linked to
its exact proof receipt and input/artifact/caller context. It may support a typed
predicate procedure_checked(call_id) only through semantic reconstruction
of that link. An arbitrary proposition with verified=true or a provenance string
is not a substitute. Normal parent inference, comparison, empty-stack,
contradiction, and commitment gates remain necessary for a final conclusion.

## 8. Work allocation and failed checks

The frozen conservative procedural allocations are:

| Transition | Instruction allocation | Checker-call allocation |
|---|---:|---:|
| SELECT_PROCEDURE | 144 | 24 |
| INSTALL_PROCEDURE | 60 | 10 |
| APPLY_PROCEDURE | 6 | 1 |

These are bounded policy work units, not measured FLOPs, time, energy, or cloud
bills. The current selected candidate's installation panel actually executes 58
instructions and 8 checker calls; its reservation remains 60/10. Keep actual
observations and allocated/charged work distinct. No unspecified refund may
increase remaining counters.

Shape/type/authority/stale-state/stack failures must be rejected before expensive
selection, qualification, execution, or checker work. If the full conservative
allocation cannot be reserved, refuse before that work. The coordinator's
prevalidation reservation must be applied to native counters even if the typed
semantic request later fails. Refused mathematical checks, wrong candidates,
failed engineering panels, and replayed valid-but-stale semantic proposals cannot
be used to obtain uncharged repeated work. Ordinary tick accounting and traced
rejection behavior still apply.

The reservation must occur once for each admitted work attempt, before the
expensive validation hook. Conflict resolution, duplicate handling, and semantic
reconstruction must not secretly execute the same work repeatedly under one
allocation. Cache only immutable results bound to the exact pre-state and attempt;
never cache an authority decision across states. Rejected malformed or
unauthorized requests consume their ordinary rejection tick but must not invoke
the expensive work in the first place. Aggregate allocations must fit the same
pre-state, including rejected checked attempts, before executing a batch.

Selection or qualification performed outside the coordinator may be retained as
proposal evidence, but cannot replace native reconstruction. Every actual native
reconstruction consumes a new allocation. Reconstructing qualification again at
installation is additional work if it already ran during preparation.

## 9. Rollback and episode boundaries

ROLLBACK_PROCEDURE binds the capability key, exact current head, and recorded
ancestor or first-installation absence. This version installs only when a head
is absent; the demonstrated rollback is removal of that first installed head.
Replacement of an active version is not implemented by this profile. It requires a running,
quiescent control state: no active acquisition frame or unresolved call may be
silently rebound by rollback. An ongoing call must complete or fail under its
original binding before a head change. Reject foreign lineage, nonexistent or
unqualified ancestors, stale expected heads, and a guessed restore target.

Rollback changes only the active head and appends a lineage record. Artifacts,
qualifications, executions, and previous trace records remain immutable. Prior
independently checked mathematical conclusions are not erased or treated as new
unchecked facts. Future calls use the restored head or request acquisition when
the first installed head was removed.

A terminal episode remains immutable. A new episode may boot with fresh per-run
budgets only through an explicit trusted native transition from the preceding
terminal coordinator state. The new run binds that terminal state hash, journal
head, and inherited procedure-registry digest. It obtains registry content from
that verified predecessor, never a caller-supplied external store or a bare
serialized registry. This explicit new-episode allocation is distinct from the
prohibited budget refund during RPM return.

If the ordinary tick budget expires while acquisition is active, the terminal
state retains its unresolved frame and cannot start a new episode. Recovery can
reproduce that failure; it does not grant new budget or complete the caller.

## 10. Persistence, semantic replay, and restart

The host may atomically retain a versioned genesis/episode chain, complete native
transition journal, and checkpoints. Host I/O is not a procedure intent. A
checkpoint is an optimization over replay, not independent authority to populate
MachineStateV2. Recovery must reconstruct the chain from its trusted genesis or
previously validated native anchor through the same versioned coordinator.

Recovery verifies versions, immutable artifacts, issuer/capability/scope/tick
bindings, selection and qualification reconstruction, call and RPM identities,
original inputs, checker receipts, prior heads/rollback lineage, allocated and
actual work, and every pre/post state and trace hash. Rehashed false records must
fail semantic replay even if their local content digests are consistent.
Reconstruction must reproduce original charges, refusals, and state transitions;
it must not call a teacher or use cached answers to replace the candidate.

Each episode also retains proposal_batches aligned with the trace. A batch stores
up to eight normalized proposal occurrences in original order, including duplicate
occurrences and an explicit malformed-normalization flag. This preserves rejected
input histories that the shared v0.1 trace's grouped proposals cannot represent
alone. Replay regenerates malformed surrogates inside the kernel and checks both
the complete event and normalization batch; supplied rejection labels authorize
nothing. Native normalization rejects non-JSON values and duplicate object keys
before their lossy serialization. The v0.1 normalization policy is unchanged.

Fresh-process reuse means a separate process recovers the native state and uses
the installed procedure on new inputs without reacquisition. Restoring only a
Python object, the local apprenticeship store, or a caller-selected artifact does
not satisfy this claim. Hash chains demonstrate integrity, not authenticated
ownership; claims must state the actual trusted genesis/host boundary.

## 11. Acceptance and open gates

Bounded acceptance requires exact retained evidence showing:

1. Preserved v0.1 tests and frozen accepted wire behavior, including rejection of
   every new intent through the default coordinator.
2. A parent call with a=3,b=5,c=26 and no expected answer suspends because no
   native procedure head exists; finite selection and checked installation occur
   through accepted native transitions.
3. The identical caller resumes at its saved stage with debited budgets; its
   installed procedure produces x=7 and independent substitution checking admits
   the branch-local result before ordinary parent completion.
4. A fresh process replays the native journal, then a new authorized episode
   reuses the procedure for a=-4,b=7,c=13 and obtains checked x=-3/2 without teacher
   or selector access.
5. A native rollback changes subsequent dispatch to the recorded prior head or
   absence, while preserving immutable evidence and caller isolation.
6. Wrong caller/frame/input/head, stale or duplicate requests, forged qualification,
   authentic failed qualification, wrong output, rehashed semantic corruption,
   unsupported operations, a=0, arithmetic limits, insufficient allocation, failed
   checker charging, budget refill, and unauthorized writes all fail closed.

Evidence must bind source/runtime/profile identities, exact initial/final states,
transition journal, costs, qualification/checker records, separate-process
recovery outputs, and scope of regression tests. Passing this bounded acceptance
does not close general learning, neural network assembly, CAS-Ohm capability,
canonical open ontology semantics, or full-machine readiness.
