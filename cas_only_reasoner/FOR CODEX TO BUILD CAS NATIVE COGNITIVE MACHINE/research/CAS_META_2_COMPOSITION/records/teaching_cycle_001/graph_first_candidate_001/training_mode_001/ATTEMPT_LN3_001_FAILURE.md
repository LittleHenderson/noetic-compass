# Graph-first ^6 — ln(3) neural diagnostic AWS attempt 001: FAILED (spec bug, preserved)

Status: **AWS_GRAPH_TRAINING_LN3_DIAGNOSTIC_FAILED.** The pipeline ran end to
end — preflight, the one new `$4.00` reservation, launch, bootstrap, CUDA,
encoder, candidate module, and the cas arm's scores + option-geometry
measurements — then the gradient test raised inside `backward()`. The
original error is preserved byte-for-byte; no optimizer step was ever
attempted (`optimizer_steps_taken: 0`), weights were never changed, and
cleanup completed with zero leftovers.

## Attempt identity

| Field | Value |
|---|---|
| job | `cas-meta2-ln3-diagnostic-20260909084139-f6f49be5` |
| request sha256 | `c4af2c824ed2427038ca0984965d1826d0923350380bb5cce98bd91aeb3adf3f` |
| authority sha256 | `70e4a4517b9c368ac2fccf34991d0f9e211c69f8ed7050fcca1b07edfa2452c6` |
| owner record sha256 | `836438161b25f0eaf49432ccdcb78781c2bd65d0da0bd750358d915ed5139f38` |
| collected result sha256 | `db6cc8c9e5519c2d02c8655422ae3b292ac8d90ea8e1dd223628416530a1ef76` |
| instance | `i-057211a07fd3eda44` (CONFIRMED_TERMINATED) |
| elapsed | 556.56 s |

Evidence:
`records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/receipt_cas-meta2-ln3-diagnostic-20260909084139-f6f49be5/`

Ledger 33 → 34 (`$182.00 → $186.00` reserved, `$218.00 → $214.00` unreserved).
The reservation stands — no refund, no automatic retry.

## Preserved error (verbatim)

```
INNER_RUNNER_EXIT_1
Traceback (most recent call last):
  File "/opt/cas-ln3-diagnostic/package/_inner_runner.py", line 26, in <module>
    report = diagnostic.launch(run_id=job + '.' + arm, learner=learner)
  File ".../cas_meta2/graph_teaching/diagnostic.py", line 105, in launch
    "gradient_test": [measure_gradient_test(learner, position) ...
  File ".../cas_meta2/graph_teaching/diagnostic.py", line 85, in measure_gradient_test
    loss.backward()
  File ".../torch/autograd/__init__.py", line 381, in backward
    _engine_run_backward(...)
RuntimeError: Trying to backward through the graph a second time (or directly
access saved tensors after they have already been freed). Saved intermediate
values of the graph are freed when you call .backward() or autograd.grad().
Specify retain_graph=True if you need to backward through the graph a second
time or if you need to access saved tensors after calling backward.
```

## Root cause

A bug in the PREPARED diagnostic spec, not a machinery finding:
`measure_gradient_test` computed `scores = learner.forward(position)` once,
before the per-target loop; the first `loss.backward()` freed that graph, so
the second target's backward raised. The module forward is deterministic
(dropout 0.0), so the fix recomputes the forward inside the loop — one fresh
graph per target, identical scores, per-target gradients.

## What is NOT claimed

- This is NOT evidence about the ^6 module, the readout, or the ln(3)
  flat-loss question — the measurement report was never produced.
- The frozen negatives, accepted models, sealed splits, and attempt-010
  result are untouched.
- A replacement run is NOT automatically authorized: it requires a new
  owner-signed record and one new `$4.00` reservation.
