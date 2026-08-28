# Compiler / Runtime Boundary — CAS-RRK v0.1

## What the compiler owns (future Stage 2)

- Lexing, parsing, desugaring of CAS/TKS/CCDL source.
- Type and effect inference, row-polymorphic effect checking.
- Lowering to the shared CAS Kernel IR.
- Static legality: a board is well-formed before it runs.

The compiler VALIDATES. It does not execute.

## What the kernel owns (now)

- Machine state, the atomic transition protocol, the sole-writer rule.
- Scheduling, branching, RPM stack, commitment, write-back, halting.
- Sealed traces and deterministic replay.
- The proof kernel: every INFER and every DecisionCommitIntent is
  re-proven against authoritative state before it is applied.

The kernel EXECUTES. It does not parse CAS source.

## The contract between them (Stage 2)

    CAS/TKS source ──┐
                     ├──> CAS-KIR ──> CAS-RRK
    CCDL source ────┘

CAS-KIR is the problem packet plus the kernel instruction set
(spec/CAS_KERNEL_IR_v0.1.md). Phase 1 consumes typed problem packets
directly; nothing in the kernel knows how to parse a .tks or .ccdl
file, and nothing in the compiler decides runtime transitions.

## What must never cross the boundary

- Compiler diagnostics are not runtime authority.
- Runtime traces are not source transformations.
- No runtime decision may depend on an unvalidated CAS-Ohm quantity.
- The proof checker is the only authority over SUPPORTED.
