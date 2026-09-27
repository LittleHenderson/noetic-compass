# Remaining test and command requirements for the CAS validation (packet B1, 2026-09-27)

Everything here is a requirement or a declared command. Nothing was run. Full inventory with per-case executed
status: `../A5_ACCEPTANCE_PACKAGE_20260927.json`.

## 1. Joint acceptance (Codex runner, admitted AWS venue, after explicit admission)

Command, verbatim from `JOINT_ACCEPTANCE_PLAN.json` at `d7808d59`:

```
HELM_SI_EXECUTION_VENUE=ADMITTED_AWS python -B -m pytest -q -p no:cacheprovider --basetemp=/opt/helm-si-output/pytest-temp --junitxml=/opt/helm-si-output/joint-junit.xml research/cas_closed_loop_1/test_native_step_adapter.py research/cas_closed_loop_1/test_closed_loop.py research/cas_closed_loop_1/test_artifacts.py research/cas_closed_loop_1/aws_validation/test_launch_transport.py research/cas_closed_loop_1/test_return_addresses.py research/helm_self_improvement/test_contracts.py research/helm_self_improvement/test_episode.py
```

Requirements: collected count declared by the freeze (73 CAS + 69 SI = 142 by AST; collection decides); `failures 0,
errors 0, skipped 0`; Python 3.12 exact patch recorded; pytest 9.0.2, pydantic 2.12.5, pydantic_core 2.41.5, boto3
1.43.87, botocore 1.43.87; basetemp outside the source tree with no symlinked ancestor (SI-4); junit and console
bytes retained; then the frozen-protocol steps for the CAS files: retained replay against bundle
`eae7eb1bedb67af537187d409c89fca9e55a1580d52bf14be9b01e560a198d2c`, witness `output 3`, `12` host entries, `18`
native events, fresh-process replay `EXACT_NATIVE_REPLAY_AND_CHECKED_EFFECT`.

Known pre-launch blockers (Codex's files): `worker.py` line 123 runs only the four CAS files; `launch.py` 103-108 and
`package.py` 213-216 permit only the 2026-09-25 seed-18 instance, so an unchanged launch blocks with
`UNDECLARED_ACTIVE_INSTANCE_CONCURRENCY_BLOCK` while seed 19 runs.

## 2. Frozen-model interface (this packet), declared command for a file that does not exist yet

```
HELM_SI_EXECUTION_VENUE=ADMITTED_AWS python -B -m pytest -q -p no:cacheprovider --basetemp=/opt/helm-si-output/pytest-temp --junitxml=/opt/helm-si-output/seed18-interfaces-junit.xml research/cas_closed_loop_1/test_seed18_interfaces.py
```

CPU dry subset (never loads a model), for the CPU protocol once the file exists:

```
python -B -m pytest -q -p no:cacheprovider --junitxml=<out>/seed18-interfaces-dry.xml research/cas_closed_loop_1/test_seed18_interfaces.py -k "refused or forbidden or required or public or parity or budget or score"
```

Declared cases: 16 (`TEST_MAP.json`), 8 CPU-dry and 8 admitted-AWS; written 0; executed 0. Writing the test file and
implementing `frozen_model_interface.py` needs a new packet naming the scope; loading the checkpoint needs the
admitted venue and an owner-signed admission.

## 3. What is not a requirement of this packet

Any score, threshold or acceptance claim; any run of the seed-18 arms; growth; SI-1/SI-2 fixes (Codex).
