# CAS / RPM / RPA mapping for Q1 compiler output (source-bound)

Author: Q1-Claude. Basis: `helm_quantum/contracts.py` and `helm_quantum/admission.py`
at commit 35236511. No other host interface export has been admitted to Q1, so every
mapping below is either bound to a field that exists in that source or marked
UNSUPPORTED. Nothing here dispatches, commits or retains.

## What the compiler consumes and produces

| Object | Source of truth | Fields the compiler reads / writes |
| --- | --- | --- |
| `QuantumProblem` (Codex) | `contracts.py` | reads `family`, `domain`, `instruction_library`, `program_length`, `max_program_length`, `prerequisites`, `target_outputs`, `decoding_order`, `problem_digest`, `source_digest`; never reads `goal` to special-case a target; never writes |
| `CompilerBinding` (Claude) | `compiler/boundary.py` | `problem_digest`, `source_digest`, `compiler_source_digest`, `semantics_digest`, `circuit_digest`, `execution_authority = "NONE"` |
| `SearchOutcome` (Claude) | `compiler/search.py` | sampled program or none, oracle calls, rounds, samples, `execution_kind = LOCAL_IDEAL_SIMULATION`; not a `QuantumProposal`, not a `QuantumRunReceipt` |

## Return-address (RPM) identity

The admitted return identity is `ReturnAddress` in `contracts.py`:
`parent_ref`, `snapshot_ref`, `snapshot_digest`, `branch_id`, `caller_id`,
`caller_frame`, `continuation`, `checkpoint_digest`. The compiler does not copy,
alter or re-derive it. A future proposal built from a `SearchOutcome` must carry
`problem.binding` unchanged (Codex's `_bound` check enforces equality) so the
immediate caller, branch, frame and continuation are exactly preserved. The
offline admission fixes these to `offline-fixture:*` values; no live HELM parent,
snapshot or continuation has been exported.

| RPM concern | Status | Bound to |
| --- | --- | --- |
| exact immediate-parent return | supported by contract, untested against a live host | `ReturnAddress.parent_ref`, `continuation` |
| snapshot binding | supported by contract | `ReturnAddress.snapshot_ref`, `snapshot_digest` |
| nested / shared prerequisites | UNSUPPORTED (`UNSUPPORTED_PREREQUISITES`) | `QuantumProblem.prerequisites` must be empty |
| checkpoint compatibility | UNSUPPORTED | `checkpoint_digest` is null in the offline fixture |

## Verifier output

Only `helm_quantum/verifier.py` (Codex) may accept a candidate; the compiler's
`marks()` and the search's classical check are the compiler's own semantics and
carry no acceptance authority. A `SearchOutcome.program` becomes a candidate only
through Codex's `propose`/`verify`, which recompute behaviour over all four inputs.

## RPA (display / replay)

UNSUPPORTED: no RPA adapter, typed relation export or viewer interface is admitted
to Q1. When one is exported, the display must label separately: declared search
space (64 selection states), observed samples (`SearchOutcome.samples`) and the
verified retained outcome (none yet). No viewer action may dispatch or commit.

## Noetic / Drive / Register mapping

None. The fixture instructions are synthetic (see `instruction_semantics.json`).
Inventorying actual CAS operations and classifying each as reversible, reversibly
embeddable, measurement-based or unsupported requires source-bound exports from
the incumbent owner. Until then every runtime semantic mapping is UNSUPPORTED.

## Missing bridge (precise)

The missing connection is a Codex-owned adapter that turns an accepted
`SearchOutcome.program` into a `QuantumProposal` with `origin` admitted for a
simulator source. `contracts.py` currently admits only `origin == "offline-classical"`
and receipts with `execution_kind == "CLASSICAL_OFFLINE"`, so no simulator-sourced
candidate can be proposed, receipted or verified today. That is by design and is
Codex's file scope, not this lease's.
