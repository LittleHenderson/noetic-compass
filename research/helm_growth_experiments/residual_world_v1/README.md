# residual_world_v1 — P1 of PARALLEL-CAPABILITY-01: one optional residual world specialist (2026-09-27)

Namespace `research/helm_growth_experiments/residual_world_v1/` assigned by Codex (PR #245 comment 5856986121) as one
bounded C3 growth slice; moved unchanged from `research/cas_closed_loop_1/claude_lead_20260927/growth_specialist/`
(original source preserved in git at `19653ec8ea5a363303cd5263dc2a01df45d67d6f`; move commit `819afab5238ba1c7dd61ad7511d132f11af4b525`).
Recorded seed for any newly initialized copy: `RECORDED_INIT_SEED = 2026092701`, never the parent RNG. Source packet:
`research/helm_parallel_capability_20260927/` at `5c81654a2796fba0b0d07f615ec0af18d0f11136` on `codex/helm-si-three-lead-20260927`.

**Revision 0.2 (FORWARD-02, 2026-09-27)** applies the four source findings Codex posted on PR #245 (comment 5857009736),
which Claude confirmed in comment 5857015746. The 0.1 source and its 14 local passes at `19653ec8` stay in git as
history; **no earlier pass is reported as a test of this revision.**

Prepared serially in the lead session (`session_011hJxopymaeoPQ67KvchtwW`), zero workers, zero cloud, provider or
model calls, no checkpoint opened, no torch execution. Nothing here is attached to seed 19, to seed 18's
learning-rate comparison, to the original learner, or to any in-flight package.

Claim states: **real** = executed here with a retained record; **written, NOT RUN** = code exists, never executed
anywhere; **reserved** = runs only in the authorized numerical venue (GPU). No capacity or benefit claim is made.

## The four findings and their state in revision 0.2

| # | Finding (Codex, comment 5857009736) | Fix in 0.2 | Pure-Python half (local venue) | Torch half (GPU venue) |
|---|---|---|---|---|
| 1 | B was built outside `fork_rng`, consuming the shared CPU RNG | Both `A` and `B` are constructed inside ONE `fork_rng(devices=[])` block seeded with `init_seed`; B zeroed inside it. `rng_neutrality_probe(build)` captures the CPU state and every CUDA state before and after and reports exact equality. Plan field `init_generator_scope` records this and the 0.1 wording is refused. | `test_finding1_plan_records_both_constructors_inside_the_seeded_fork` — **real: passed** | `test_finding1_constructing_the_specialist_leaves_cpu_and_cuda_generators_exactly_unchanged`, `test_finding1_counterexample_of_the_0_1_layout_is_detected_by_the_probe` — **written, NOT RUN** |
| 2 | Optimizer state bound by inferred position; config substituted for group settings | `bind_group_parameters(group_params, named_parameters)` binds each actual parameter object to its unique name by identity and refuses foreign, duplicate, missing and doubly-named objects (`OPTIMIZER_BINDING_INVALID`). `check_mapping_against_bindings` verifies the mapping's indices on both sides. `group_settings` copies every setting of the old group (never `params`); `validate_optimizer_config` refuses a supplied config that differs (`OPTIMIZER_CONFIG_MISMATCH`); `settings_preserved` checks the new group afterwards (`OPTIMIZER_GROUP_SETTINGS_NOT_PRESERVED`); carried state tensors must match the parameter's shape and dtype (`OPTIMIZER_STATE_INCOMPATIBLE`). `attach_specialist` now returns the pre-attach `(name, Parameter)` pairs so the caller never guesses. | `test_finding2_binding_is_by_object_identity_and_refuses_foreign_duplicate_and_missing`, `test_finding2_mapping_indices_must_agree_with_verified_bindings_on_both_sides`, `test_finding2_group_settings_are_preserved_and_a_supplied_config_must_match` — **real: passed** | `test_finding2_migration_refuses_a_group_that_is_not_the_verified_parameter_set`, `test_finding2_group_settings_come_from_the_old_group_and_a_differing_config_is_refused` — **written, NOT RUN** |
| 3 | `enabled` not in `state_dict`; save/reload test never enabled the specialist or saved the optimizer | Versioned sidecar `specialist_config.json` (schema `cas.growth.world-residual-specialist.sidecar/0.1`): `enabled`, `hidden`, `input_width`, `init_seed`, plan digest, sha256 of `grown_state.pt` and `grown_optimizer.pt`, the verified group-order parameter names, source pins, and its own digest. `save_grown` writes state, optimizer, plan and sidecar together; `load_grown` reads the sidecar FIRST, refuses missing/tampered files (`SIDECAR_MISSING` / `SIDECAR_MISMATCH` / `SIDECAR_SCHEMA_INVALID`), rebuilds the specialist from the sidecar, restores `enabled`, and reloads the optimizer's state and group settings after checking the binding and shapes. Real-checkpoint integration stays explicitly unimplemented. | `test_finding3_sidecar_carries_enabled_seed_sizes_and_digests_and_round_trips`, `test_finding3_tampered_or_malformed_sidecar_is_refused`, `test_file_sha256_matches_hashlib` — **real: passed** | `test_finding3_enabled_nonzero_b_and_optimizer_state_survive_save_and_reload_together` (enables, steps until B ≠ 0, saves all three, reloads into a fresh container, checks `enabled`, every state tensor, every optimizer state tensor and `step`, group settings, identical output, identical next step), `test_finding3_missing_or_tampered_sidecar_and_files_are_refused` — **written, NOT RUN** |
| 4 | Finite inputs do not imply finite `A·x`; gradient statement too broad | `intermediate(x)` computes `h = GELU(A x)` and refuses a nonfinite `h` before the B multiplication (`SPECIALIST_NONFINITE_INTERMEDIATE`). `TOLERANCES` now state the exact-zero result **under the checked precondition** that `h` is finite, record the counterexample (`A = ones`, `x = finfo(float32).max` on every coordinate: `A x = inf`, `GELU(inf) = inf`, `0.0 × inf = nan`), and state the gradient conditions: `dL/dB ≠ 0` only if `GELU(A x) ≠ 0` for some row **and** `dL/dy ≠ 0`; `x = 0` and a zero upstream gradient are counterexamples; the probe uses generic nonzero inputs and a sum loss (`dL/dy = 1`). | `test_finding4_tolerances_state_the_intermediate_precondition_and_gradient_counterexamples` — **real: passed** | `test_finding4_extreme_finite_input_overflows_the_intermediate_and_is_refused_before_b` (also shows the `nan` the 0.1 check would have let through), `test_finding4_zero_input_and_zero_upstream_gradient_leave_b_without_gradient` — **written, NOT RUN** |

## What the recorded candidate is, confirmed against the exact source

`score(x) = old_world_score(x) + B · GELU(A · x)`, where `x` is the world-candidate input the source's
`world_head` consumes. Confirmed at `c45f775f` (file sha256 `0f424d86…`, blob `d07012d4…`): `world_head` is
`Sequential(Linear(38, 64, bias=False), GELU(), LayerNorm(64), Linear(64, 1, bias=True))` at lines 856-858;
`WIDTH = 64` (197), `DECL_VECTOR_WIDTH = 32` (206), `WORLD_CANDIDATE_WIDTH = 2 + 4 + 32 = 38` (246); the
optimizer is one AdamW group over `list(module.parameters())` with `foreach=False, fused=False, capturable=False`
(1840-1845); fingerprints are `name:dtype:shape` over sorted state-dict keys (515); a checkpoint's
`learnable_names` are the sorted state-dict keys (2128). The source's `analogy_head` (861-864) shows the precedent
for a separately seeded initialization through a forked CPU generator; the specialist uses the same mechanism for
both of its constructors. This is an exploratory capacity option, not a diagnosis of HELM's hard-question failures.

| File | What it is | State (revision 0.2) |
|---|---|---|
| `growth_migration_plan.py` | Pure Python (schema `…/migration-plan/0.2`). The plan: original names and signatures preserved, the two new names and exact shapes, init policy (A nonzero from a recorded generator, B zero, both inside one seeded fork), verified-identity-and-name optimizer mapping, deliberate new-state policy (zero step and moments), recorded seed, stated tolerances and preconditions, `learnable_names_after`, digest; JSON round trip. New in 0.2: `bind_group_parameters`, `group_settings`, `validate_optimizer_config`, `settings_preserved`, `check_mapping_against_bindings`, `build_sidecar` / `validate_sidecar` / `sidecar_to_json` / `sidecar_from_json`, `file_sha256`; nine new refusal codes. | real: 22 passed |
| `test_growth_migration_plan.py` | 22 cases (the 14 of 0.1, revised where the wording changed, plus 8 FORWARD-02 cases). Parameter objects, groups and fingerprint rows are test doubles. | real: **22 passed, 0 failed, 0 errors, 0 skipped**; Python 3.11.15, pytest 9.0.2; junit `plan_tests_local_junit_forward02.xml` (sha256 `14ccc06b9e19884e74df04d6e5a0fbb6fdc72eda9f1ad30025a886714f520bae`). The 0.1 junit `plan_tests_local_junit.xml` (14 passed at `19653ec8`) is kept as history and is NOT a test of 0.2. |
| `world_residual_specialist.py` | Torch. `WorldResidualSpecialist` (explicit size `SPECIALIST_HIDDEN = 16`, not a sweep; A and B built inside one seeded fork; `enabled` is a plain attribute carried by the sidecar), `rng_neutrality_probe`, `intermediate` (nonfinite refusal), `attach_specialist` (registers LAST; returns the pre-attach named parameters), `migrate_optimizer` (verified binding, preserved group settings, config must match, state shape/dtype checked, zero-initialized new entries), `preservation_report`, `save_grown` / `load_grown` (sidecar), `scored_world` (the one call site a growth learner would use instead of `world_head(candidate)`, source line 1566). | written, NOT RUN (no torch here); syntax parsed; every imported name and refusal code cross-checked statically against the plan module |
| `numeric_gpu/test_world_residual_specialist_numeric.py` | 15 numeric cases on a labeled test-double container: the 7 of 0.1 (revised to the new signatures) plus 8 FORWARD-02 cases listed in the findings table. Raises `GPU_REQUIRED` unless CUDA is present. | reserved; **written, NOT RUN** |

## Initialization and why B learns first (recorded before any result)

A is initialized nonzero and B to zero, both inside one forked CPU generator seeded with the recorded `init_seed`.
For `y = base + B·GELU(A x)`: `dL/dB = (dL/dy)·GELU(A x)ᵀ` is nonzero **only when** `GELU(A x)` is nonzero for some
row **and** `dL/dy` is nonzero (`x = 0` and a zero upstream gradient are counterexamples); `dL/dA =
Bᵀ·(dL/dy)·GELU′(A x)·xᵀ` is exactly zero while B is the zero matrix. So under generic nonzero inputs and a nonzero
loss gradient B learns first, and A's gradient becomes informative only after B has taken at least one update.
Both-zero initialization is refused (`INIT_POLICY_INVALID`) because both gradients would stay zero forever.

## Stated tolerance and precondition (before seeing any result)

- Same device, **and** the intermediate `h = GELU(A x)` finite (checked): the initial contribution is **exactly**
  zero and `base + 0.0` equals `base` (`torch.equal`); a `-0.0` base becomes `+0.0`.
- Finite inputs do NOT imply a finite intermediate. A nonfinite `h` is refused before B (`SPECIALIST_NONFINITE_INTERMEDIATE`),
  never masked. Counterexample recorded: `A = ones`, `x = finfo(float32).max` everywhere.
- Nonfinite inputs are refused before the forward (`0.0 × inf` is `nan`), never masked.
- Any other device or hardware: **no claim** of bitwise function preservation.
- Trainability probe: nonzero versus exactly zero gradients under generic nonzero inputs and a sum loss; no tolerance needed.

## Parameter and migration mapping

Original parameters are preserved by exact name and shape (the plan records every signature). The two new
parameters `world_specialist.A.weight` `[16, 38]` and `world_specialist.B.weight` `[1, 16]` (624 scalars) are
registered explicitly as the last submodule. Optimizer state is carried from the old group to the new one through a
binding of the actual parameter objects to their unique names (identity, not position); the mapping's indices are
checked against that binding on both sides; the old group's settings (including any extra key such as `initial_lr`)
are copied onto the new group and verified; a supplied learner `optimizer_config` must equal them. A parameter AdamW
never stepped has no state and none is invented for it; the new entries start with a zero scalar `step` and zero
`exp_avg` / `exp_avg_sq`. A grown container has a different `learnable_names` set, so the original restore path
refuses it (`POINTER_CHECKPOINT_LAYOUT`), which is the intended fail-closed behavior: growth is a new checkpoint
schema and run identity, versioned together (state + optimizer + plan + sidecar), with the pre-growth checkpoint kept
as the rollback target (see `research/cas_closed_loop_1/claude_lead_20260927/A4_GROWTH_CAS_REQUIREMENTS_20260927.md`).

## Future versioned integration seam (identified, not wired)

The scientific learner's `_graph` calls `self.model.world_head(candidate)` at `pointer_learner.py` line 1566 (source
`c45f775f`). A growth learner would call `scored_world(container, candidate)` there instead, under a new checkpoint
schema and run identity versioned together, from a copied admitted parent at a declared safe boundary. That edit is
inside the scientific source and is not part of this slice.

## What is NOT done, exactly

- No real HELM checkpoint was deserialized or mutated; the migration and the sidecar round trip are exercised only
  in code, on a test double, and only in the reserved numeric file, which has not run.
- The specialist is not attached to the original learner (seam at line 1566, Codex's scope).
- No growth comparison is designed here; it needs its own unchanged-capacity control and a declared
  compute, time and exposure matching rule.
- The torch half of each fix is unexecuted. Its status becomes real only with a junit from the authorized venue.

## Exact next AWS test command (reserved venue; not a launch)

```
python -B -m pytest -q -p no:cacheprovider --junitxml=<out>/growth-specialist-numeric-junit.xml research/helm_growth_experiments/residual_world_v1/numeric_gpu/test_world_residual_specialist_numeric.py
```
Requires torch with CUDA; expected 15 tests, 0 failures, 0 errors, 0 skipped, if collection matches. The
pure-Python file can be run in the same job for a second record of the 22 local cases:
```
python -B -m pytest -q -p no:cacheprovider --junitxml=<out>/growth-plan-junit.xml research/helm_growth_experiments/residual_world_v1/test_growth_migration_plan.py
```
