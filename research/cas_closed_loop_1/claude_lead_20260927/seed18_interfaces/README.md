# seed18_interfaces — frozen learned model interface, with and without the CAS repair path

Owner task `SEED18-INTERFACE-IMPLEMENT-02` (2026-09-27) continuing packet `B1-SEED18-INTERFACES-20260927-01`
(`7e990eb6…`). Serial lead work in session `session_011hJxopymaeoPQ67KvchtwW`, model `claude-fable-5-1`; zero
children; zero cloud, provider or model calls; no neural execution. Writes are confined to this directory plus the
root `CHANGELOG.md`. Base CAS source `7bbf1e0f7bae635126c05b3203cca706ea8654dc`; corrected joint source
`d7808d59c13ea94c6ff35d2327a4acb8535daabc`. Ownership acknowledgment from Codex requested on PR #245 (comment
5856429415); pending at the time of this commit.

Claim states: **real** = executed here with a retained record; **not run** = never executed; **not implemented**
= raises `NotImplementedError` with an exact reason. Nothing here is acceptance or a HELM result.

| File | What it is | State |
|---|---|---|
| `frozen_model_interface.py` | Slice 1 implemented: typed validation of identities, admission bindings, budgets, work accounts and records; public-record validation by an explicit permitted-field table, typed formats and provenance; `RecordLedger` enforcing prediction-before-repair; `BudgetLedger` charging before work; `repair_none` preserving the original prediction; `episode_parity_check` returning totals and no verdict. Standard library only; opens no file. | real (local) |
| `test_frozen_model_interface_slice1.py` | 32 test functions, 43 cases, every object a labeled test double (`CLAUDE_TEST_DOUBLE_NOT_A_HELM_RUN`). | real: 43 passed, 0 failed, 0 errors, 0 skipped; Python 3.11.15, pytest 9.0.2; junit `slice1_local_junit.xml` |
| `INTERFACE_CONTRACT.json` | The contract as data (0.2): bindings, invariants, the closed refusal set, implemented and not-implemented lists. | record |
| `TEST_MAP.json` | The 16 declared cases with slice-1 status: 10 written and executed locally (some as no-model variants), 6 not written; plus the slice-1 execution record. | record |
| `REMAINING_VALIDATION_REQUIREMENTS.md` | Remaining CAS validation commands and the declared interface command. | record |
| `SEED18_PARENT_AND_ARMS.json` | Codex's stated parent (`5a8a3069…`, cursor `2940`) and the two arms (constant `0.003` vs `0.001`, 20 additional passes), readouts fixed before results. | stated by Codex, not verified here |

## Executable test command (real, local)

```
python3 -B -m pytest -q -p no:cacheprovider --junitxml=research/cas_closed_loop_1/claude_lead_20260927/seed18_interfaces/slice1_local_junit.xml research/cas_closed_loop_1/claude_lead_20260927/seed18_interfaces/test_frozen_model_interface_slice1.py
```

The lane `conftest.py` applies (it puts the repo root and the pinned runtime on the path); the module is imported
from its own directory. No model, checkpoint, answer key or private body is touched by any test.

## Not implemented, exactly

| Function | Reason string | What unblocks it |
|---|---|---|
| `admit_frozen_model`, `predict_raw` | `NOT_IMPLEMENTED_AWAITING_EXACT_C45_LEARNER_API` | Codex pastes the exact `restore_checkpoint` and `predict` signatures and refusal names from `c45f775f` (asked in comment 5856429415). The archived 2026-09-22 copy is not used. |
| `repair_cas_closed_loop` | `NOT_IMPLEMENTED_MISSING_NATIVE_OPERATION_FOR_LEARNED_PREDICTION` | see "Next missing connection" |
| `evaluate` | `NOT_IMPLEMENTED_REQUIRES_ADMITTED_EVALUATOR` | the admitted evaluator in the AWS venue; this module never reads an answer key |

## Next missing connection (named, not faked)

The learned task is typed-pointer prediction over course packets (`PointerCourseLearner.predict(packet, depth)`).
The native repair runtime at CAS `7bbf1e0f` exposes, through `control.py`, exactly three PCBA board operation
groups: `parent_transform` {`REQUEST_COMPOUND`, `APPLY_COMPOUND`}, `prerequisite_acquisition`
{`PUSH_COMPOUND_ACQUISITION`, `PUSH_PRIMITIVE_ACQUISITION`, `SELECT_PRIMITIVE`, `INSTALL_PRIMITIVE`,
`RETURN_PRIMITIVE`, `CONSTRUCT_COMPOUND`, `INSTALL_COMPOUND`, `RETURN_COMPOUND`, `FAIL_COMPOUND`} and
`verification_commit` {`CHECK_MEMORY_RESOLUTION`, `ORDINARY_REASONING_AND_COMMITMENT`, `HALT`}. Each maps to
`CompoundMachine.advance` on a fixed board whose declared scope reads "no passive, feedback, timing or neural
execution". None takes a prediction as input. The equation witness (`predicted_flow(Design(...))`, output `3`) is a
symbolic Ohm calculation and is not a neural repair; it is not reported as one.

**Missing operation, exactly:** a native operation whose input is a `PredictionRecord` (item inputs digest, raw
prediction digest, private body reference) and whose checked effect is a verified answer for that item, journaled
like every other native event. It exists neither in runtime `8182ad52` nor in `control.py`. Because the runtime
commit is byte-frozen by the retained evidence's admission identity, adding it is a runtime-commit change with its
own bootstrap and freeze, which is Codex's scope to assign. Until it is assigned, `repair_cas_closed_loop` raises
its exact reason and no CAS-path result is claimed.

## Open gates

- G1 joint acceptance of the CAS validation in the admitted venue (Codex runner; the stale concurrency identity
  and the four-file worker list are pre-launch blockers).
- G2 Codex's ownership acknowledgment of this namespace (requested).
- G3 the exact `c45f775f` learner API (requested) for `admit_frozen_model` and `predict_raw`.
- G4 assignment of the missing native operation or bridge for `repair_cas_closed_loop`.
- G5 the admitted evaluator for `evaluate`.
