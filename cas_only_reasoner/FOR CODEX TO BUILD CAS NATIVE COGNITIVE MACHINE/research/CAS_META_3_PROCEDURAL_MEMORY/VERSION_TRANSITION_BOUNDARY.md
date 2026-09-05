# Future learning continuity: existing behavior versus missing integration

This is a static source review, not a new execution result or a reopened restart
audit. The accepted source remains `0917267b1354e5d036263eaa6ba9a7197eafb776`.
The saved-procedure registry does not implement the extension described here.

## What already exists

In sibling `CAS_CJT_TRANSFORMER_v0_2/cas_cjt/runtime.py:1389`, `learning_tick`
accepts `resume_repair_id`. It forbids learning during the reserved `t+1` repair
subgoal, but supports learning on the exact parent-resumption tick `t+2`.

The order matters: `_prepare_inference` verifies the resumed Effect under the
old model before `GovernedLearner.propose` stages the new weights. The same-tick
Effect is therefore pre-update evidence. Only subsequent inference uses the
updated model. The existing `tests/test_integrated_runtime.py:221` covers repair
return combined with this update, exact changed-parameter scope, durable reopen,
and a later changed output. These tests were inspected, not rerun in this review.

## What the fixed-weight meta executor intentionally rejects

In sibling `CASFORMER_v0_3_META_LOGIC_WIP/cas_meta/executor.py:138`, the binding
includes the model, program, software, contracts, topology, scope, limits, chain,
and run. `_check_boundary` at line 189 checks this binding, the exact database
head, actual model bytes, and call stack. Its execution path uses `inference_tick`.
Its checkpoint/restore API does not authorize a model-version change. This is a
current safety boundary, not a failure of the accepted restart implementation.

## A later candidate needs a checked transition

A new integration would need an explicit continuation record that binds the
old checkpoint, before/after native heads, model lineage, update receipts,
actual scope/retention evidence, exact caller/input/return position, and remaining
budget. Fresh-process continuation must check that record; it must not simply
replace the accepted executor's private binding or weaken its restore checks.

Neighboring parameter bytes must remain unchanged. Their derived global model
pointers may change in the same native transaction. A caller-supplied claim that
regression passed is not evidence that a retention test actually ran.

The current META3 package pins the whole compatible model identity. After a
model change, the old package does not silently become compatible. Any successor
would require externally checked compatibility and a new package hash/lineage.

This could show governed learning at resumption and later continuation under
the new model. It would not yet show that a missing skill was acquired during
repair and caused the original failed transition to become solvable. Native
network-learning rollback also needs separate evidence; the legacy single-Bias
rollback helper is not that API.
