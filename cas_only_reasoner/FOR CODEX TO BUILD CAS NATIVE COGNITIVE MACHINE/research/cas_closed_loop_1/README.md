# CAS-CLOSED-LOOP-1 — initial source binding and contract

Codex is the single integration writer on `codex/cas-closed-loop-1`, based on
`2636bbb6e0f41a37ba2c20df08cdf51185718617`. Claude reviews the changed path and runs AWS checks. Helm has queue priority.

This commit prepares T01/T02: exact reusable source pins, ownership, the first operation/measurement contract and
the existing-test mapping for nested returns. It has not executed a runtime, built the adapter or produced a nested
trace. The immutable assignment is under `_handoffs/CAS_CLOSED_LOOP_1/`; its COMPLETE manifest is package assembly,
not implementation acceptance.

Next coding deliverable: `native_step_adapter.py` joins one typed grant to `CompoundMachine.advance`, records
independent execution observations and binds the suspended return chain to existing atlas identities. It cannot
write native state itself. Then add the real demo/observe/replay entry points and focus the new tests on the changed
path. The final learned pilot waits for Claude's saved Q4 summary and a separately admitted execution manifest.

Existing baseline acceptance command, to be run on AWS from the CNCM directory:

```powershell
python -m pytest tests/test_compound_kernel.py::test_real_nested_construction_installs_program_and_resumes_exact_parent tests/test_compound_recovery.py::test_actual_source_fresh_process_recovers_each_cut_then_reuses_program
```

This is an existing command, not a claimed pass or launch instruction. The new adapter acceptance command will be
pinned with its actual test file when implemented. Do not infer runtime behavior from JSON checks.
