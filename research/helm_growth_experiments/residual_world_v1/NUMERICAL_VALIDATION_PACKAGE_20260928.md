# Numerical validation package — residual_world_v1 at `c70e1a04` (prepared 2026-09-28, NOT RUN)

Machine-readable twin: `NUMERICAL_VALIDATION_PACKAGE_20260928.json`. Claim state: **prepared, not run**. Nothing in
this package has executed with torch anywhere. Only a junit produced by the designated runner from this exact
binding changes that, and it changes only level L1 below.

## What a pass here does and does not establish

| Level | What it is | Covered by this package? |
|---|---|---|
| **L1** standalone module tests | 15 numeric cases + 22 pure-Python cases on a labeled test-double container | **Yes.** This is all the package can show. |
| **L2** migration of an actual copied HELM checkpoint | restore a copied admitted parent through the exact learner, attach, migrate, preserve exactly | **No.** See `REAL_CHECKPOINT_INTEGRATION_STEP_20260928.md`. |
| **L3** additional training with growth | a grown learner taking updates from a copied parent under a new schema and run identity | **No.** Needs the learner integration under a lease, a continuation seam, a separate allowance. |
| **L4** measured task benefit | a preregistered readout against an unchanged-capacity control | **No.** No claim made or licensed. |

Passing L1 does not establish L2, L3 or L4.

## Source binding (verify first, refuse on any mismatch)

Commit `c70e1a048d5130e5268b4a6556265aa53225b6c1`, branch `claude/focused-mccarthy-uj45ul`, PR #245. Pins file
`numeric_gpu/SOURCE_PINS_c70e1a04.sha256` (content sha256 `c5f7e3965a3e14f07df57d8c6a06334984da294ea3603e7e00169d66e85a7bd2`):

```
0dcf4c05975711f10559a19599eb8a10503c135a2b2ee075e15d0c1640caba29  research/helm_growth_experiments/residual_world_v1/growth_migration_plan.py
c48c42050d48d81890dc78d3947e4a91edc5559c80b85e23ff84004e8eddaaaf  research/helm_growth_experiments/residual_world_v1/numeric_gpu/test_world_residual_specialist_numeric.py
21ea6597212bc949e6524811673be5f5e63de9ab1c0feaa6637ed078d291cba4  research/helm_growth_experiments/residual_world_v1/test_growth_migration_plan.py
ae49a34117db4a88ef36a9bdbbde8cfb4b79b565453eb1debe12de90df54e996  research/helm_growth_experiments/residual_world_v1/world_residual_specialist.py
```

## Dependencies

Python 3.11.x (prepared under 3.11.15); pytest ≥ 8 (prepared under 9.0.2); torch 2.x with CUDA; one visible CUDA
device. No network, no dataset, no checkpoint, no file outside the namespace, no environment flag. Without CUDA the
numeric file raises `RuntimeError("GPU_REQUIRED: …")` at import, which pytest reports as a collection **error**,
never as a pass.

## Exact commands (`<repo>` = checkout root, `<out>` = a job-owned output directory)

```
# C0 verify pins
cd <repo> && sha256sum -c research/helm_growth_experiments/residual_world_v1/numeric_gpu/SOURCE_PINS_c70e1a04.sha256
# C1 the 15 numeric cases (GPU)
python -B -m pytest -q -p no:cacheprovider --basetemp=<out>/pytest-temp --junitxml=<out>/growth-specialist-numeric-junit.xml -rA research/helm_growth_experiments/residual_world_v1/numeric_gpu/test_world_residual_specialist_numeric.py
# C2 optional second record of the 22 pure-Python cases
python -B -m pytest -q -p no:cacheprovider --basetemp=<out>/pytest-temp --junitxml=<out>/growth-plan-junit.xml -rA research/helm_growth_experiments/residual_world_v1/test_growth_migration_plan.py
# C3 hash the outputs
cd <out> && sha256sum growth-specialist-numeric-junit.xml growth-plan-junit.xml > junit-sha256.txt
```

Expected if collection matches: C1 `tests=15 failures=0 errors=0 skipped=0`; C2 `tests=22 failures=0 errors=0 skipped=0`.

## Expected collected identities

Numeric (15, derived from the pinned file's AST because torch is absent here; no parametrize):
`test_disabled_specialist_returns_the_base_object_unchanged`, `test_initial_contribution_is_exactly_zero_when_the_intermediate_is_finite`,
`test_nonfinite_and_wrong_shape_inputs_are_refused`, `test_attach_preserves_originals_and_optimizer_state_exactly_and_counts_new_parameters`,
`test_state_dict_save_reload_and_plan_consistency`, `test_two_step_trainability_b_first_then_a_under_generic_inputs_and_sum_loss`,
`test_contribution_ablation_after_two_steps`, `test_finding1_constructing_the_specialist_leaves_cpu_and_cuda_generators_exactly_unchanged`,
`test_finding1_counterexample_of_the_0_1_layout_is_detected_by_the_probe`, `test_finding2_migration_refuses_a_group_that_is_not_the_verified_parameter_set`,
`test_finding2_group_settings_come_from_the_old_group_and_a_differing_config_is_refused`, `test_finding3_enabled_nonzero_b_and_optimizer_state_survive_save_and_reload_together`,
`test_finding3_missing_or_tampered_sidecar_and_files_are_refused`, `test_finding4_extreme_finite_input_overflows_the_intermediate_and_is_refused_before_b`,
`test_finding4_zero_input_and_zero_upstream_gradient_leave_b_without_gradient`.

Pure Python (22, collected locally with `pytest --collect-only` at `c70e1a04`): the 14 revision-0.1 names (four of
them the parametrized `test_bad_sizes_and_missing_seed_are_refused[...]` rows) plus the 8 `test_finding*` /
`test_file_sha256_matches_hashlib` cases; full list in the JSON twin.

## Output paths and what to publish

`<out>/growth-specialist-numeric-junit.xml`, `<out>/growth-plan-junit.xml`, `<out>/junit-sha256.txt`; `pytest-temp/`
may be deleted once the junits are hashed. Publish the junits, their hashes and the job identity on PR #245. The
tests read no protected answers and produce none, so the whole output is public aggregate evidence.

## Resource requirements and venue

One CUDA device of any size (well under 100 MB of device memory), under 2 GB RAM, under 50 MB of disk, under two
minutes of test time after torch import. Venue: the designated runner, **after** the seed-19 job
`helm-cont19-p20-p40-20260927-a1` releases the shared GPU slot and a separate finite job allowance is recorded.
**Never on the active training instance `i-0ab8b5a4bee9d0dc4`.** No new budget is granted by this package. Claude
launches nothing.

## Pass / fail semantics

- Pass: C0 all OK and C1 `15 / 0 / 0 / 0`. Then, for this exact binding only, the torch halves of findings 1-4 move
  from NOT_RUN to real (executed). The spec-sheet status stays `ENGINEERED-NOT-VALIDATED`; L2-L4 stay open.
- Collection error mentioning `GPU_REQUIRED`: the venue had no CUDA. Not a pass, not a failure of the code.
- Any failure: report the failing ids verbatim; do not rerun on another commit; Claude fixes in the namespace on the
  next authorized slice.
