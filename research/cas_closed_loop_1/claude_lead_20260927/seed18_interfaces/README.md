# seed18_interfaces — packet B1-SEED18-INTERFACES-20260927-01 (source-only, 2026-09-27)

Owner-authorized bounded continuation requested by Codex on PR #245 (comment 5856004287). Serial lead work in
session `session_011hJxopymaeoPQ67KvchtwW`; model `claude-fable-5-1` (configured and last served); zero children;
zero cloud, provider or model calls; zero local tests, imports or model execution. Writes are confined to this
directory. Base CAS source `7bbf1e0f7bae635126c05b3203cca706ea8654dc`; corrected joint source
`d7808d59c13ea94c6ff35d2327a4acb8535daabc`. Source work is not accepted behavior.

| File | What it is |
|---|---|
| `frozen_model_interface.py` | Callable interface contract for a frozen learned model with (`CAS_CLOSED_LOOP`) and without (`NONE`) the current CAS repair path. Every operation raises `NotImplementedError`. Standard library only. **Not imported, compiled or executed here; syntax unverified.** |
| `INTERFACE_CONTRACT.json` | The same contract as data: bindings, paths, ten invariants, fifteen refusals, exclusions. |
| `TEST_MAP.json` | Sixteen declared test identities mapped to the invariants and venues (8 CPU-dry, 8 admitted-AWS). Written 0, executed 0. |
| `REMAINING_VALIDATION_REQUIREMENTS.md` | Exact remaining test and command requirements for the CAS validation and the declared command for this interface. |
| `SEED18_PARENT_AND_ARMS.json` | Codex's stated parent (`5a8a3069…`, cursor `2940`) and the two arms (constant `0.003` vs `0.001`, 20 additional passes), re-fixed readouts before any result, and the supersession of the +10-pass proposal. |

## Assumptions, stated

1. The parent identity and the two copies are as Codex stated; Claude read no checkpoint and verified nothing.
2. The learner's entry points named in the contract (`restore_checkpoint`, `predict(packet, depth)`) are taken from
   an archived 2026-09-22 copy of `pointer_learner.py` (sha256 `21dabd21…`), not the exact `c45f775f` file; names
   must be confirmed on the exact bytes before implementation.
3. The CAS adapter calls (`grant_for`, `execute_grant`, `runtime_location`) and the receipt schema are those at
   `7bbf1e0f`, unchanged.
4. "Same information, actions, evaluator, budget" is enforced by `episode_parity_check` refusals, not assumed.
5. The neural prediction enters the CAS path as an input Idea to the native step; how the native repair consumes it
   is left to the implementing packet and must not change the adapter.

## Open gates

- G1 joint acceptance in the admitted venue (Codex runner, owner admission); the stale concurrency identity and the
  four-file worker list are pre-launch blockers.
- G2 a new packet naming the implementation scope for `frozen_model_interface.py` and `test_seed18_interfaces.py`.
- G3 confirmation of learner entry-point names on the exact `c45f775f` bytes.
- G4 the continuation seam for the seed-18 arms (Codex; blockers stated in comment 5856004287).

## Next deliverable

On a new packet: implement the CPU-dry half of `TEST_MAP.json` (refusals and structure, no model) in the lane with
same-commit `HARNESS_SPEC.md` and `CONTRACTS.json` amendments, then the admitted-AWS half through Codex's runner.
