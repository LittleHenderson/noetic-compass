# Graph-first ^6 — ln(3) neural diagnostic — REPLACEMENT request (AUTHORIZED, REGISTERED)

Status: **AUTHORIZED_BY_OWNER / REGISTERED.** The owner's instruction **"GO"**
(recorded `2026-09-09T08:57:56Z`) authorized the replacement. Job id
`cas-meta2-ln3-diagnostic-20260909085756-95693cd8`; owner record
`OWNER_AUTHORIZATION_AWS_LN3_002.json` (sha `b856257b…`); launch inputs
`ln3_diagnostic_launch_002/` (request sha `d7823d54…`, authority sha
`f3c36c94…`). One new `$4.00` reservation, exactly once, no refund, no
automatic retry.

## What failed, and the fix (no machinery finding)

Attempt 001 ran the full pipeline — preflight, reservation, launch, CUDA,
encoder, module, and the cas arm's scores + option-geometry measurements —
then the gradient test raised inside `backward()`:

```
RuntimeError: Trying to backward through the graph a second time ... the graph
are freed when you call .backward() ...
```

The prepared spec computed `scores = learner.forward(position)` ONCE before
the per-target loop; the first `loss.backward()` freed that graph. The module
forward is deterministic (dropout 0.0), so the fix recomputes the forward
INSIDE the loop: one fresh graph per target, identical scores, per-target
gradients (`diagnostic.py` at commit `51f12c61`). Regression tests
(`tests/test_graph_training_diagnostic.py`) reproduce the freed-graph failure
with a fake-torch harness and lock the per-target recomputation; all 90 graph
tests pass. No optimizer step was ever attempted in attempt 001
(`optimizer_steps_taken: 0`); cleanup completed with zero leftovers.

## Replacement package identities (built; NOT launched)

| Field | Value |
|---|---|
| source_sha | `51f12c612429eb1004f0fd4b0f358e04c2914722` |
| archive_sha256 | `507ace06661ecb16d1a149d1dfa7d43754290689f7c0ec0f24056123a34d17e3` |
| manifest_sha256 | `310595ca40be9de7a6378e846eb93ffae00ca8dacbaf7b407e36129f951b09c1` |
| package | `training_mode_001/ln3_diagnostic_package_002/` |
| launcher | `aws/graph_training_ln3_diagnostic_launch.py` at commit `68c9fc7a` (unchanged) |

The replacement job would be minted with a fresh id in the signed record at
approval. Preserved bounds: measurement only, `optimizer_steps_permitted: 0`,
`max_wall_seconds: 1200.0`, both framing arms, one job, one new `$4.00`
reservation, no retries, sealed splits NOT consulted, verified cleanup,
worker fail-closed if any weight changed. Ledger today: revision 34,
`$186.00` reserved / `$214.00` unreserved; a `$4.00` replacement leaves
`$190.00` / `$210.00`.

## What the replacement returns

The measured per-record scores/spread, option geometry, and the
alternative-target gradient norms for BOTH arms (the four bound decision
rules from `LN3_DIAGNOSTIC.md`), or the preserved original error.
