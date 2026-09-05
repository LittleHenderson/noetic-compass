# CAS-META-0: fixed-weight callable procedure prototype

WIP. Unreviewed release candidate. Not part of reproduced CASformer v0.2.
No neural training, new Noetics, memory oscillation, or capability promotion.

This first implementation compiles an explicitly authored program into real
bounded child calls over the unchanged v0.2 runtime. It tests composition, not
program induction or the ability to solve new reasoning problems.

## What runs

`programs/fixed_chain.json` contains the oracle labels and this program:

```text
main:      A -> Call(worker)
worker:    B -> C -> [on repair: Call(repair_c)] -> resume C
repair_c:  R -> return its accepted Effect
```

The native sequence is A, B, rejected C, R, resumed C. It yields four accepted
Effects in five native traces. The expected candidate symbols are L1, L3, L2,
L1, L2. The model parameters remain fixed. The original v0.2 acceptance demo
uses **learning** at its fifth tick; our fifth tick is **inference only**.
We do not claim equivalence to that learning step or its changed-output proof.

Three real frames coexist during repair. `main` and `worker` stop at their call
sites while `repair_c` executes. Its return names the exact waiting caller and
instruction position. Call-instance IDs include the chain label, a unique run
ID, and an invocation counter; a program path is not used as an invocation ID.

## Small language and authority boundary

Only `sequence`, `call`, and `run` are supported. Sequences lower into an
instruction list inside each procedure; calls remain runtime stack operations.
Procedure inputs are native Cause kinds `IDEA`, `EFFECT`, or `RPM_SUBGOAL`.
Their output is a Cause derived from an accepted native Effect. That transport
type must not be confused with the neural operation's `DECOMPOSITION_SIGNAL`.

The compiler checks names, types, extra fields, scope, call cycles, and size
limits. Every operation must be `^6`; the executor also checks the actual
native operation contract, CJT binding, and decoder labels. A child can only
use CJTs already permitted to its parent. The independent v0.2 verifier and
coordinator still decide publication and durable updates.

`Compose`, `Within`, dynamic calls, loops, self-recursion, general policy
strings, ten-Noetic translation, and Foundation scheduling are rejected or
absent. Bounded nested procedure calls are implemented; arbitrary recursive
programs are not. v0.2's single-open-repair scheduling restriction remains.
Entering/returning a call frame does not execute a neural operator or advance
the native clock.

Each frame owns its input, instruction position, return binding, and allowance.
Persistent Bias remains **per native CJT**, not a fresh isolated Bias for every
invocation. Reusing a CJT reuses its saved state. There is one active executor
owner; concurrent execution against the same database is unsupported.

## Budget and persistence rules

The ledger conservatively sums five predeclared native policy ceilings:
routes, reasoning steps, branches, memory reads, and diagnostic probes.
Each fixture tick charges 72 units; all five charge 360 of the root's 512.
The rejected C still costs 72. These are reserved policy units, not measured
FLOPs, elapsed time, energy, or a neural execution profiler.

Every child draws an allowance from its parent's remaining allowance. A tick
charges every active ancestor. A failed state proposal never refunds compute.
Call depth, meta-step count, Cause bytes, and input shape are bounded separately.
Planning/hash work is outside the policy ledger; explicit external memory
references are rejected in this first build. No learning instruction exists.

Native accepted steps are immediately durable. The wrapper cannot roll them
back if a parent later fails. In particular, an accepted repair Effect remains
stored across restart. Frame-local return bookkeeping is separate from those
durable native Effects and Bias updates.

A checkpoint binds program, contracts, decoders, topology, model, state/trace
head, caller stack, chain/run identities, limits, consumed units, and events.
Restore requires a separately retained SHA-256 receipt. Changed bytes, program,
limits, authority, model, or native head are rejected. The demo closes the
native runtime after R commits, starts a fresh Python process, restores the
three frames, returns to the exact caller, and resumes C without rerunning R.

This proves **clean-boundary restart**, not atomic crash recovery across the
native database and the separate checkpoint file. Do not auto-retry after a
partly completed native call. Checkpoint hashes detect changes relative to a
trusted receipt; they are not signatures, protection against a hostile Python
caller, or protection if both checkpoint and trusted receipt are replaced.

## Trace and equivalence evidence

Native v0.2 traces are unchanged and validated against their published schema.
New meta events use `schemas/meta_event.schema.json`, exact field validation,
and a SHA-256 chain; native event links are checked against stored receipts.

The common semantic projection compares Causes, candidates, verifier receipts,
published Effects, pre/post state, repair opening/closure, state/model/memory
intents, compute plans, and compute observations. It does not require native
and meta trace files to have identical hashes. The meta trace retains the
additional call and return records. See `cas_meta/demo.py`.

`tests/` covers the parser, schema, actual execution, suspension/return, scopes,
fixed weights, unchanged other-CJT Bias, rejected-work accounting, clean
restart, changed bindings, call identity, and resource limits. The fresh-process
test is `tests/test_demo.py`. These tests are not an external execution audit.

## Rerun

Use a Python environment with the two frozen wheels installed. The wheels are
in the sibling v0.2 release reproduction artifacts; the original dependency
lock is at `../CAS_CJT_TRANSFORMER_v0_2/requirements.lock`. The wheel paths are:

```text
../CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/casformer_reference-0.1.0-py3-none-any.whl
../CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/cas_neural_cjt-0.2.0-py3-none-any.whl
```

Install `requirements-meta.txt` in that environment. Run these commands from
this directory, replacing `python` with the environment's Python executable:

```powershell
python -m pytest tests -q --tb=short --basetemp _rerun_tests
python -m cas_meta.demo --output _rerun_demo
python tools/validate_build.py --output records/my_new_validation
```

Use a **new** output directory for each demo/validation run. The validation
script captures exact commands, outputs, JUnit counts, environment identity,
source hashes, unchanged-v0.2 manifest checks, and restart/demo evidence.
Do not place a pytest `--basetemp` over user data: pytest clears that directory.

### Standalone prepare and resume

`--output` runs the WHOLE demo, including its automatic restart. After it
returns, its root `compiled.db` is at native step 5 but its original
`checkpoint.json` is still at step 4. Replaying that recorded resume command
against the completed database correctly fails with `NATIVE_HEAD_MISMATCH`.
The native head is SQLite's committed runtime head, not Git HEAD.

To stop before continuation, use this public two-process workflow from this
directory. Choose a new directory name for each preparation:

```powershell
python -m cas_meta.demo --prepare _rerun_paused
$receipt = Get-Content -Raw _rerun_paused/creation_receipt.json | ConvertFrom-Json
python -m cas_meta.demo --resume _rerun_paused --expected-digest $receipt.checkpoint_digest
```

The first command exits with three saved call frames (two suspended callers),
four native traces, and
288 reserved policy units spent. The second restores those exact frames and
adds only resumed C: five traces, 360 units spent, 152 remaining, closed repair,
and unchanged neural parameters. `worker_result.json` records the restored
frames, before/after native heads, budget, and preservation of prior events.

Restart requires BOTH `checkpoint.json` and its matching `compiled.db`, plus
the matching program, frozen dependencies, and separately retained expected
digest. Missing files are named and rejected before SQLite opens. A checkpoint
does not contain a standalone database backup. Do not replace database heads
or weaken either identity check to make an incompatible pair load.

Both `--prepare` and `--output` now retain a closed, matching step-4 bundle in
`paused/`. To replay one, copy that entire folder to a NEW writable location,
read that copy's `creation_receipt.json`, and resume the copy. Preserve the
original evidence bundle. The older `records/validation/demo` predates this
snapshot addition; its root step-4 checkpoint and completed step-5 database
are not a resumable pair. Do not rewrite those historical files.

The expected digest is SHA-256 of the complete checkpoint bytes. It includes
the invocation's UUID `run_id`, call identities, event hash chain, runtime
bindings, frames, and native head. Two independently prepared runs can have
different checkpoint digests while their model/program digests and defined
native semantics agree. Use each artifact's own creation receipt; a program
digest or semantic-projection digest is not its checkpoint digest.

This workflow proves clean-boundary continuation, not crash-atomic recovery.
The CLI is for this fixed demo, not arbitrary checkpoint execution. A second
resume of an already consumed bundle remains an explicit stale-head rejection.

## Evidence boundary and next work

The frozen source is `dec08c81644f1c47b4b94c29a406a9432df7c7bd`; its separate
release evidence is `b5d52d1fc9d5dce231ccb0f91ece2be0168dfa78`. This build changes
neither. The prior v0.2/v0.1/CNCM full regression receipt is separate from the
new composition tests; do not report those old counts as newly rerun here.

Current design input: owner-supplied attachment
`e707bf14-75fa-4590-9fc3-b775d48ad575/pasted-text.txt`, SHA-256
`23440a19c8ee10611112e8d9e61e4a7e9c7f7222e8093bed54abf27a3cfb0ed5`.
It narrows the preserved `CAS_META_0_DESIGN_INPUT.md`; it does not authorize
the broader memory/training proposals in that earlier document.

Still open: external review, a new v0.3 release audit, procedure retrieval,
dynamic recursion, learning isolation, atomic crash recovery, and matched
non-CAS controls. Explicit tags, bounded pulses, oscillation, trajectory
readout, and hybrid memory strategies remain future interchangeable options;
oscillatory phase must never become the sole chain identity.

No language capability, general reasoning ability, CAS-specific advantage,
CNCM brain completion, AGI, or production readiness is claimed.
