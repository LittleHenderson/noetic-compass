# CAS Neural CJT Transformer v0.2

Status: `FIRST COMPLETE LOCAL MECHANISM PROTOTYPE`

This package implements the first integrated neural Cognitive Junction
Transistor (CJT) prototype described in `BUILD_CONTRACT.md`. It is more than an
architecture sketch: the code runs several trainable PyTorch CJTs through
typed inference, verification, repair, governed learning, atomic persistence,
process restart, and trace reconstruction.

“Complete” has a narrow meaning here. It means that the 15 prototype behaviors
in `BUILD_CONTRACT.md` run together in one local test, satisfying the owner's
definition of the first complete neural CJT. It does **not** mean that the
complete CAS-native Transformer, the CNCM brain, general reasoning, or AGI has
been built. No experiment here shows that CAS improves learning, reasoning,
accuracy, efficiency, or safety over an ordinary Transformer.

## What is implemented

- A strict `CausePacket` with semantic fields, provenance, goal context, and an
  optional content-addressed tensor.
- A persistent six-part `BiasState`: stable identity, local memory, RPM state,
  operating record, shared model references, and governance.
- Separate Desire, Wisdom, and Power values, gates, and reason codes.
- Differentiable CAS-Ohm routing inside a selected CJT. Hard topology,
  permission, quarantine, readiness, and budget gates run first.
- An exact integer pre-execution compute ceiling. It uses scaled native Drive
  and resistance values and deterministic top-route selection. It is not a
  fairness or largest-remainder allocator.
- Separate support-preserving integer telemetry for realized neural current.
  Its per-row allocation uses largest remainder with canonical route-ID
  tie-breaking, while the differentiable floating-point path remains intact.
  Memory reads and repair openings are counted once globally, not once per
  attention row, and can never exceed the earlier ceiling.
- Four distinct neural operation modules. Only `^6` is canonical-admitted in
  this package. `^2`, `^3`, and `^8` remain experimental and cannot publish an
  authoritative Effect through the default verifier.
- A candidate Effect derived from the gated CJT Effect tensor, followed by a
  deterministic decoder and a separate exact-match verifier.
- An exact 11-phase tick:
  `READ -> CANDIDATE -> READINESS -> ROUTE -> EXECUTE -> OBSERVE -> VERIFY -> DIAGNOSE -> EMIT -> COMMIT -> TRACE`.
- A bounded next-tick repair path, immutable `RepairFrame` openings, separately
  sealed `RepairOutcome` closures, Effect-to-Cause cascades, proposed memory
  writes, selective staged learning, and exact parameter-scope checks.
- Bias memory records accepted-work Cause IDs, candidate Effect IDs, verifier
  IDs, repair IDs, and memory records actually retrieved. Authoritative
  Published Effect IDs and rejected/repair evidence remain in the durable
  commit and trace records instead of being relabeled as accepted Bias memory.
- One global content-addressed checkpoint. Every CJT Bias points to the same
  active model version; a qualified model change updates those pointers in one
  transaction.
- Sole supported semantic writes through `NetworkAtomicCoordinator`,
  transaction rollback on invalid batches, explicit compensating rollback,
  restart recovery, and full retained-transition reconstruction. The raw
  SQLite write-set method and legacy single-Bias coordinator are trusted
  persistence compatibility mechanisms, not untrusted proposal authorization
  APIs.
- A proposal-only CNCM bridge that returns a frozen inert envelope. It grants
  no authority in the current CNCM runtime.

The repair prototype allows one open frame globally. It opens only when a
distinct, ready, permitted `^6` CJT has a two-way topology path. Its `t+1`
subgoal and `t+2` parent resume reserve those ticks and bind back to the
retained parent goal and operation list. This demonstrates controlled repair
routing and closure, not that the synthetic repair corrected a real-world
reasoning error.

CAS-Ohm controls admitted neural flow and declared compute ceilings only. It
does not decide truth, meaning, proof, permission, commitment, memory
occurrence, external action, or halt.

A `QUARANTINE` result in this prototype rejects the current candidate and is
sealed as an audit-only transition. It does not persistently flip the Bias's
governance quarantine flag; that requires a later governance authority design.

v0.2 trusts the in-process `NeuralCJTRuntime` to execute the neural forward.
The coordinator validates the resulting proposal and authority transition, but
does not independently rerun or attest that forward. Reconstruction returns
the retained inputs, outputs, artifacts, and links; it is not proof of an
independent deterministic neural replay.

Learning scores, losses, and the regression result are declarations supplied
by the caller. The regression flag defaults to fail closed. The coordinator
checks the receipt arithmetic, checkpoint difference, and permitted parameter
scope, but this prototype does not independently prove that the caller's
evaluation is scientifically adequate or independent.

## Run the source tree

The v0.2 package depends on the frozen sibling package
`../CASFORMER_v0_1`. From this directory in PowerShell:

```powershell
$env:PYTHONPATH = "$(Resolve-Path ..\CASFORMER_v0_1);$(Get-Location)"
python -m pytest -q -p no:cacheprovider
python .\examples\complete_reasoning_transistor.py
```

The full suite is the release check for the behaviors below. The demo prints
JSON showing the A -> B -> C -> repair R -> resumed C sequence, a
qualified C-only checkpoint change, restart use of retained Bias, rejection of
a cross-CJT update, successful reconstruction, and store integrity.

For installed use, install `casformer-reference==0.1.0` first, then install
this project. The example is also included in the wheel data under
`share/cas-neural-cjt/examples`.

## Read next

- `BUILD_CONTRACT.md` gives the exact completion evidence.
- `ARCHITECTURE.md` shows the implemented authority and data paths.
- `EQUATIONS.md` states the implemented math, including the exact compute-plan
  algorithm.
- `API_CONTRACTS.md` lists the real public entry points.
- `CNCM_INTEGRATION_BOUNDARY.md` explains why current CNCM admission remains
  closed.
- `ROADMAP.md` separates completed prototype work from the larger research
  program.
- `MEMORY_RESEARCH_PLAN.md` records the post-v0.2 chain-tag and pulsation
  comparison without treating either design as implemented or superior.
- `SOURCE_MANIFEST.json` fingerprints the final source, tests, and documents.
- `artifacts/VALIDATION_RECEIPT.json` records the final local test, demo,
  package-build, and isolated-install evidence. It is a same-task validation
  record, not an independent certification or signature.
