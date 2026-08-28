# CAS Reasoning Runtime Kernel v0.1

## Machine State, Atomic Authority, and Executable Transition Semantics

**Status:** FROZEN for Phase 1. Precedence: this file, then
AUTHORITY_MANIFEST.yaml, then CAS_SEM_MVP_v0.1.md.

---

## 1. The missing line

The state store may atomically apply a validated transition, but it
cannot schedule, reason, speculate, learn, or choose the result.

This creates a single-writer architecture: one authoritative snapshot,
one atomic writer. Every other subsystem may only produce a typed
proposal - an intent. Without this rule, modules can obey their
individual limits and still collide through shared mutable state.

## 2. Two different meanings of commit

### State commit

Occurs at the end of every logical processing step: S_t -> S_t+1. The
validated changes from this tick become the new authoritative machine
state. State commit may happen many times during one episode.

### Decision commit

Occurs when one candidate branch becomes the accepted result:
Candidate B -> COMMITTED. The commitment latch must not directly write
state; it issues a DecisionCommitIntent, and the transaction coordinator
validates and applies it atomically.

The latch must never be both judge and clerk.

## 3. The atomic transition protocol

    1. SNAPSHOT     read one immutable authoritative state S_t
    2. ENABLE       determine which components are legally ready
    3. SCHEDULE     select components by dependency, priority, Domain
                    precedence, and budget
    4. PROPOSE      each selected component emits typed intents only
    5. VALIDATE     check types, authority, branch ownership, RPM stack
                    rules, Domain precedence, commitment prerequisites
    6. RESOLVE      resolve compatible and conflicting intents
                    deterministically
    7. STATE COMMIT atomically produce S_t+1
    8. TRACE        seal pre-state, intents, validation decisions,
                    accepted writes, rejected writes, post-state
    9. HALT TEST    continue, or stop on a committed typed terminal state

## 4. Machine state

    MachineState {
        runtime_version, logical_tick, run_id, seed,
        constitution_revision, foundation_state, drive_state,
        domain_power_state, global_workspace, working_memory,
        episodic_memory_revision, active_goal_id, rpm_stack,
        branch_table, pending_intents, commitment_state,
        learning_queue, halt_status, trace_head, state_hash
    }

state_hash is the deterministic digest of the complete authoritative
state (schemas/machine_state.schema.json). Every TraceEvent seals
pre_state_hash and post_state_hash.

## 5. Kernel invariants (non-negotiable)

1. Single writer: only the state store / transaction coordinator mutates
   authoritative state.
2. Intent purity: every subsystem effect is a typed intent.
3. Atomicity: each tick produces one complete state transition, sealed in
   one trace event, or no transition at all.
4. Determinism: same input, same state, same seed, same version ->
   identical authorized intents, identical trace digest, identical final
   state hash.
5. Rollback: a branch discarded before decision commit leaves zero
   durable traces except its sealed history.
6. Halting discipline: execution stops only after the terminal state is
   atomically committed and its trace is sealed.
7. CAS-Ohm exclusion: no runtime decision may depend on an unvalidated
   CAS-Ohm quantity (OPEN_QUESTIONS item 9).

## 6. Typed halting

    CONCLUDED            decision commit produced the accepted result
    NEEDS_INFORMATION    the state does not justify a conclusion
    NEEDS_CAPABILITY     capability prerequisite blocked, unobtainable
    CONFLICT_UNRESOLVED  evidence supports and refutes one candidate
    INADMISSIBLE         every candidate violates principled constraints
    BUDGET_EXHAUSTED     branch/branch-table budget consumed
    LOOP_LIMIT_REACHED   repeated state without progress

A refusal is a successful result: the machine correctly discovered that
the available state does not justify a conclusion.

## 7. Trace and replay fabric

The trace fabric records and binds what happened; it cannot authorize a
transition or alter the state it records. Each event seals:

    event_id, logical_tick, pre_state_hash, enabled_components,
    scheduled_components, proposed_intents, authorized_intents,
    rejected_intents, rejection_reasons, committed_mutations,
    post_state_hash, terminal_status

Deterministic replay: re-executing the sealed authorized intents against
a fresh state with the same run_id, seed, and version must reproduce the
identical post_state_hash per tick and the identical terminal status.
This is the kernel's strongest testable guarantee.
