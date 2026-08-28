# CAS Kernel IR v0.1

## The Native Reasoning Instruction Set

**Status:** FROZEN for Phase 1. Each instruction is an intent type plus
its validation and effect. Execution rights are owned by the transaction
coordinator; components only propose.

---

| Instruction | Issuer | Intent type | Validated effect |
| --- | --- | --- | --- |
| RECALL | reasoning | MemoryRecallIntent | working memory receives retrieved items; lacunae recorded |
| FORK | branch manager | ForkIntent | new isolated branch frame with snapshot of workspace |
| ASSOCIATE | reasoning | DeriveIntent | candidate hypothesis surfaced (^8); never marked SUPPORTED |
| DECOMPOSE | reasoning | DeriveIntent | candidate premises, unknowns, contradictions recorded |
| INFER | reasoning | DeriveIntent | SUPPORTED conclusion iff re-proven by the coordinator |
| COMPARE | reasoning | DeriveIntent | structural difference report under shared bias |
| CONTRADICT | reasoning | DeriveIntent | contradiction flagged with its dependencies |
| PUSH_RPM | RPM stack | PushGoalIntent | parent suspended, child goal pushed with return address |
| RETURN_RPM | RPM stack | ReturnGoalIntent | typed child result returned; parent resumes |
| COMMIT_BRANCH | commitment latch | DecisionCommitIntent | one branch becomes the accepted result (after all gates) |
| WRITE_EPISODE | write-back controller | MemoryWriteIntent | episodic store, only from committed outcome + sealed trace |
| HALT | halting controller | HaltIntent | typed terminal status committed, then execution stops |

## Validation rules (coordinator)

- intent type must be legal for the issuing subsystem (capability table);
- INFER intents are accepted only when the proposed conclusion re-proves
  against the authoritative state;
- DecisionCommitIntent is accepted only when the candidate is SUPPORTED,
  uncontradicted, goal-relevant, and all commitment gates passed;
- MemoryWriteIntent is accepted only with a committed outcome and sealed
  evidence; references to discarded branches are rejected;
- ReturnGoalIntent is accepted only when a matching parent frame exists;
- HaltIntent is accepted only once, and execution stops only after the
  terminal state is atomically committed and traced;
- two intents mutating the same field resolve deterministically (first
  by issuer priority, then by intent_id) or raise a typed conflict.

## Boundaries

The IR says nothing about CAS-Ohm, neural activation, English, or
probabilities. It is the reasoning instruction set, nothing more.
