# Authority Contract v0.1

## The constitution of the kernel

**Status:** FROZEN verbatim from the design brief.

---

No subsystem may directly mutate authoritative machine state.

Every subsystem emits a typed intent.

The scheduler may select enabled work, but cannot derive, commit, learn,
or halt.

Reasoning components may derive provisional branch-local states, but
cannot publish authoritative conclusions.

The branch manager may create, isolate, compare, merge, and discard
provisional branches, but cannot write durable memory or produce
Operational output.

The RPM stack may suspend a parent and push a prerequisite subgoal, but
every child must preserve a valid parent identity and return address.

The comparison system may report structural differences and dominance,
but cannot commit a winner.

The commitment latch may request a decision commit only after all
required gates pass, but cannot mutate state directly.

The write-back controller may request durable learning only from a
committed outcome with a sealed trace.

The halting controller may request a typed terminal state, but execution
stops only after the terminal state is atomically committed and traced.

The transaction coordinator and state store are the sole writers of
authoritative state.

The trace system records transitions but cannot authorize them.

---

## The two commits, never collapsed

    STATE COMMIT
        occurs after each valid runtime tick

    DECISION COMMIT
        occurs when a candidate branch becomes the accepted conclusion

## Intent table

    Scheduler          -> FireIntent
    Reasoning          -> DeriveIntent
    Branch manager     -> ForkIntent / DiscardIntent
    RPM stack          -> PushGoalIntent / ReturnGoalIntent
    Commitment latch   -> DecisionCommitIntent
    Write-back         -> MemoryWriteIntent
    Halting controller -> HaltIntent

The state store, acting through the transaction coordinator, may turn
approved intents into the next authoritative machine state. It cannot
invent reasoning content or choose goals.
