# growth_specialist — P1 of PARALLEL-CAPABILITY-01: one optional residual world specialist (2026-09-27)

Prepared serially in the lead session (`session_011hJxopymaeoPQ67KvchtwW`), zero workers, zero cloud, provider or
model calls, no checkpoint opened. Written in Claude's isolated lead area pending Codex's assignment of a new,
non-overlapping experimental growth namespace; it will be moved there unchanged when named. Nothing here is
attached to seed 19, to seed 18's learning-rate comparison, to the original learner, or to any in-flight package.

Claim states: **real** = executed here with a retained record; **written, NOT RUN** = code exists, never executed
anywhere; **reserved** = runs only in the authorized numerical venue (GPU). No capacity or benefit claim is made.

## What the recorded candidate is, confirmed against the exact source

`score(x) = old_world_score(x) + B · GELU(A · x)`, where `x` is the world-candidate input the source's
`world_head` consumes. Confirmed at `c45f775f` (file sha256 `0f424d86…`, blob `d07012d4…`): `world_head` is
`Sequential(Linear(38, 64, bias=False), GELU(), LayerNorm(64), Linear(64, 1, bias=True))` at lines 856-858;
`WIDTH = 64` (197), `DECL_VECTOR_WIDTH = 32` (206), `WORLD_CANDIDATE_WIDTH = 2 + 4 + 32 = 38` (246); the
optimizer is one AdamW group over `list(module.parameters())` with `foreach=False, fused=False, capturable=False`
(1840-1845); fingerprints are `name:dtype:shape` over sorted state-dict keys (515); a checkpoint's
`learnable_names` are the sorted state-dict keys (2128). The source's `analogy_head` (861-864) shows the precedent
for a separately seeded initialization through a forked CPU generator; the specialist uses the same mechanism.
This is an exploratory capacity option, not a diagnosis of HELM's hard-question failures.

| File | What it is | State |
|---|---|---|
| `growth_migration_plan.py` | Pure Python. The plan: original names and signatures preserved, the two new names and exact shapes, init policy (A nonzero from a recorded generator, B zero), by-name optimizer mapping (positional mapping refused, order change refused), deliberate new-state policy (zero step and moments), recorded seed, stated tolerances, `learnable_names_after`, digest; JSON round trip. | real: 14 passed |
| `test_growth_migration_plan.py` | 14 cases on the plan and mapping, including the refusals for both-zero init, name collision, reordering, missing seed, bad sizes, tampered JSON. Fingerprint rows are test doubles. | real: 14 passed, 0 failed, 0 errors, 0 skipped; Python 3.11.15, pytest 9.0.2; junit `plan_tests_local_junit.xml` |
| `world_residual_specialist.py` | Torch. `WorldResidualSpecialist` (explicit size `SPECIALIST_HIDDEN = 16`, not a sweep; `enabled` is a plain attribute), `attach_specialist` (registers it LAST so the original parameter order stays an unchanged prefix), `migrate_optimizer` (new AdamW; original state carried by exact name; new entries get zero step and zero moments; single-group layout required), `scored_world` (the one call site a growth learner would use instead of `world_head(candidate)`, source line 1566), `preservation_report`. | written, NOT RUN (no torch here); syntax parsed |
| `numeric_gpu/test_world_residual_specialist_numeric.py` | 7 numeric cases on a labeled test-double container: disabled behavior returns the base object; initial contribution exactly zero for finite inputs; nonfinite and wrong-shape refusal; exact preservation of original parameters and optimizer state after migration, new-parameter count 624 and optimizer registration; save/reload and plan consistency; two-step trainability (B first, then A); contribution ablation after two steps. Raises `GPU_REQUIRED` unless CUDA is present. | reserved; NOT RUN |

## Initialization and why B learns first (recorded before any result)

A is initialized nonzero from a forked CPU generator seeded with a recorded `init_seed`; B is initialized to
zero. For `y = base + B·GELU(A x)`: `dL/dB = (dL/dy)·GELU(A x)ᵀ` is nonzero whenever A is nonzero and the input is
finite, while `dL/dA = Bᵀ·(dL/dy)·GELU′(A x)·xᵀ` is exactly zero while B is the zero matrix. So B learns first, and
A's gradient becomes informative only after B has taken at least one update. Both-zero initialization is refused
(`INIT_POLICY_INVALID`) because both gradients would stay zero forever.

## Stated tolerance (before seeing any result)

- Same device, finite inputs: the initial contribution is **exactly** zero and `base + 0.0` equals `base`
  (`torch.equal`); a `-0.0` base becomes `+0.0`.
- Any other device or hardware: **no claim** of bitwise function preservation.
- Nonfinite inputs are refused before the forward (`0.0 × inf` is `nan`), never masked.
- Trainability probe: nonzero versus exactly zero gradients; no tolerance needed.

## Parameter and migration mapping

Original parameters are preserved by exact name and shape (the plan records every signature). The two new
parameters `world_specialist.A.weight` `[16, 38]` and `world_specialist.B.weight` `[1, 16]` (624 scalars) are
registered explicitly as the last submodule. Optimizer state is copied by exact name from the old index to the new
index; a parameter AdamW never stepped has no state and none is invented for it; the new entries start with a zero
scalar `step` and zero `exp_avg` / `exp_avg_sq`. Positional guessing is refused. A grown container has a different
`learnable_names` set, so the original restore path refuses it (`POINTER_CHECKPOINT_LAYOUT`), which is the intended
fail-closed behavior: growth is a new checkpoint schema and run identity, versioned together, with the pre-growth
checkpoint kept as the rollback target (see `../A4_GROWTH_CAS_REQUIREMENTS_20260927.md`).

## What is NOT done, exactly

- No real HELM checkpoint was deserialized or mutated; the migration was exercised only in code, on a test double,
  and only in the reserved numeric file, which has not run.
- The specialist is not attached to the original learner: the learner's `_graph` calls `world_head(candidate)`
  at line 1566, and a growth learner must call `scored_world(container, candidate)` there instead. That edit is
  the one missing connection, inside the scientific source, and is not Claude's to make.
- No growth comparison is designed here; it needs its own unchanged-capacity control and a declared
  compute, time and exposure matching rule.

## Exact next AWS test command (reserved venue; not a launch)

```
python -B -m pytest -q -p no:cacheprovider --junitxml=<out>/growth-specialist-numeric-junit.xml research/cas_closed_loop_1/claude_lead_20260927/growth_specialist/numeric_gpu/test_world_residual_specialist_numeric.py
```
Requires torch with CUDA; expected 7 tests, 0 failures, 0 errors, 0 skipped, if collection matches.
