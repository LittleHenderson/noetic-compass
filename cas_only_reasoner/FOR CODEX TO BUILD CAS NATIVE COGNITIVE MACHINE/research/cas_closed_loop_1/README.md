# CAS-CLOSED-LOOP-1 — initial source binding and contract

Codex is the single integration writer on `codex/cas-closed-loop-1`, based on
`2636bbb6e0f41a37ba2c20df08cdf51185718617`. Claude reviews the changed path and runs AWS checks. Helm has queue priority.

This commit prepares T01/T02: exact reusable source pins, ownership, the first operation/measurement contract and
the existing-test mapping for nested returns. The first host adapter is implemented but has not executed a runtime or produced a nested
trace. The immutable assignment is under `_handoffs/CAS_CLOSED_LOOP_1/`; its COMPLETE manifest is package assembly,
not implementation acceptance.

`native_step_adapter.py` joins one typed grant to `CompoundMachine.advance` and records actual host calls, native
events and charged policy units separately. It snapshots the native return chain without granting return authority.
Actual primitive-work joins, Ohm predictions, PCBA mappings and atlas node bindings remain pending. It cannot write
native state itself. Next connect those existing interfaces and add real demo/observe/replay entry points. The final learned pilot waits for Claude's saved Q4 summary and a separately admitted execution manifest.

Existing baseline acceptance command, to be run on AWS from the CNCM directory:

```powershell
python -m pytest tests/test_compound_kernel.py::test_real_nested_construction_installs_program_and_resumes_exact_parent tests/test_compound_recovery.py::test_actual_source_fresh_process_recovers_each_cut_then_reuses_program
```

This is an existing command, not a claimed pass or launch instruction. The focused new adapter acceptance command is:

```powershell
python -m pytest research/cas_closed_loop_1/test_native_step_adapter.py
```

Neither command was run locally. Do not infer runtime behavior from syntax or JSON checks.
