# Chapter 10: CAS Runtime and Traceability

If CAS is a programming language, it needs an environment to run in. The CAS Runtime is the software layer that executes cognitive state transitions, manages memory, and provides the rigorous traceability required for aligned AI.

This chapter explores how the runtime manages the flow of thought during an active session.

## Runtime Frames

When you launch a CAS session (like `cas chat` in the CLI), the runtime initializes a **Runtime Frame**. 

A frame is a secure sandbox for cognitive execution. It tracks:
- **The Context:** Who is the user? What is the current task?
- **The Current State:** Where is the system structurally right now? (e.g., is it currently exploring `^8`, or executing `^3`?)
- **The Available Substrate:** Which memories and tools are currently loaded into active awareness?

Every action the AI takes occurs within a specific frame. When a task is completed, the frame resolves, and its output is passed up to the parent process.

## Turn Execution

A "turn" is a single cycle of interaction (User Input -> AI Output). In a standard LLM, a turn is just appending text to a prompt and running inference. In CAS, Turn Execution is a highly structured, multi-step process:

1.  **Parse Input:** The user's text is parsed.
2.  **Rewrite/Shim (If necessary):** If the user spoke colloquial English, the CLI's rewrite shim maps it into a formal CAS state request.
3.  **State Prediction:** The CAS-Native model (see Chapter 12) predicts the necessary structural response (`^Noetic^Domain_{Drive}|Register`).
4.  **Validation:** The CAS compiler checks the predicted state. If it violates rules (e.g., an illegal domain jump), the runtime rejects it and forces the model to re-predict.
5.  **Execution/Generation:** Only after the state is validated does the model generate the English text that matches that specific structural state.

This "Structure-First" generation is the core of CAS-Native alignment.

## Generation Traces

Because every step of the Turn Execution is explicitly tracked, the runtime can produce a **Generation Trace**. 

A Generation Trace is an immutable log of exactly how a decision was made. It includes:
- **Trace ID:** A unique identifier for the thought.
- **Parent ID:** The previous trace that led to this one (forming a chain of reasoning).
- **The Structural Path:** The exact CAS equations the model traversed.

### Example Trace Log

```json
{
  "trace_id": "tr_8f92a1",
  "parent_id": "tr_8f92a0",
  "input_stimulus": "User asked for a project deadline.",
  "predicted_state": "^3^C_{F5}|A",
  "validation_status": "PASS",
  "generated_output": "The project deadline is Friday at 5 PM. I have updated the tracker."
}
```

## Why Traceability Matters

If an AI makes a catastrophic error—for example, approving a dangerous chemical synthesis—a standard LLM leaves you with a black box. You don't know *why* it output those specific tokens.

With CAS Generation Traces, you can audit the exact cognitive path. Did the model get stuck in `^8^C` (endless brainstorming) and fail to evaluate the danger (`^6^E`)? Did a user prompt hijack its `F5` Agency drive?

Traceability makes decisions inspectable, debuggable, and legally defensible. It is the foundation of structural alignment.