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
| `../../test_seed18_interfaces.py` (lane path assigned by Codex; moved from `test_frozen_model_interface_slice1.py`) | 46 test functions, 58 cases by static count, every object a labeled test double. Slice 1 (32 functions, 43 cases): **real**, 43 passed at commit `2022be45` from the former path, junit `slice1_local_junit.xml`. Slice 2 (14 functions, 17 cases: typed-format refusals, admission boundary, predict-only handle, `predict_raw` ordering): **written, NOT run** under Codex's packet bounds; syntax parsed only. |
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

## Slice 2 (packet B1-SEED18-IMPLEMENT-02, comment 5856489964), written and not run

- Every string field now has a typed format (structured device name, torch version, item id, admission reference,
  besides digests, enums, UTC stamps and `private://` references). No free-text field exists, so a prediction body
  of any length is refused by format, not by length.
- `admit_frozen_model(identity, admission, *, path, device, restore=None, framework_factory=None, encoder=None,
  torch=None, rng_guard=None)`: admission binding; regular file, no symlink; size before bytes; SHA-256 before load;
  CUDA only; then `RESTORE_DEPENDENCIES_NOT_SUPPLIED` at the CPU-dry boundary. With the venue's dependencies it
  calls the confirmed restore signature once per fresh framework and checks the restored cursor. The restore and
  `predict` are GPU-dependent and **unaccepted** until the admitted venue runs them. No host parameter.
- `FrozenModelHandle`: predict-only, depth fixed at 8, each call under the venue's RNG guard, on a separately
  restored clone; `stage_batch`, `train_sealed_batch`, `export_checkpoint` refused.
- `predict_raw`: charge, one call, private-store receipt validated (reference ends in the body digest), public record
  appended last. A `None` result is refused before storing.
- Codex named a public exact source copy `continuation_review_20260927_01/pointer_learner.py`; it was not found on
  any pushed origin branch at about 14:05Z, so the API is taken from Codex's comment and the copy stays unconfirmed.

## Not implemented, exactly

| Function | Reason string | What unblocks it |
|---|---|---|
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
- G2 ownership acknowledged by Codex (comment 5856489964); test file location assigned.
- G3 learner API confirmed by Codex; the named public copy is unconfirmed on origin; the GPU-dependent restore and predict remain unaccepted until the admitted venue.
- G4 assignment of the missing native operation or bridge for `repair_cas_closed_loop`.
- G5 the admitted evaluator for `evaluate`.
