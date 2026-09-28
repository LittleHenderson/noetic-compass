# D focused review — growth15 actual numerical failure

Reviewer lane: DeepSeek. Date: 2026-09-28. Cost: $0.00, 0 cloud jobs, 0 paid calls.
Subject: `helm-growth15-c70e1a-20260928-a1`, the first growth numerical check.
Sources read at the public commits `c70e1a04` and `38c2ecc4` on
`codex/helm-si-three-lead-20260927`.

## 1. Handoff counts: confirmed

| Claim | Check | Result |
| --- | --- | --- |
| 15 collected, 14 passed, 1 failed, 0 errors, 0 skipped | `JUnit` at `38c2ecc4`: `tests="15" failures="1" errors="0" skipped="0"` | Confirmed |
| 15 is the whole numeric suite | the numeric directory holds exactly one test file, with exactly 15 `test_` functions | Confirmed |
| the operator commit did not change the test | blob at `c70e1a04` and at package commit `a6fe9239` is the same object `0ecd7fbe3a04c98e506bcb563a48484af31f8b27` | Confirmed |
| `junit_sha256` | recomputed `d0b56715960e5b595c74e8b0e84356859623b65f229b51bccf8fab7b3139922a` | Matches |
| no retry | `automatic_retry: false`, `additional_paid_attempts: 0` | As declared |

Source-line attributions in the record are also correct: optimizer state load at
`world_residual_specialist.py:307`, optimizer construction at `:313`.

## 2. What the record says it cannot establish, and what I can settle

The record's own `inference_limit` says: "Traceback does not print the exact
index/key; step-tensor attribution is a source-based inference, not direct
tensor-body inspection."

**I can close that gap from the pinned torch source, without a GPU.** The outcome is
deterministic, not uncertain. Three rules combine:

1. `torch/optim/adam.py:166` — comment and code, verbatim:
   `# Deliberately host 'step' on CPU if both capturable and fused are off.`
   followed by `torch.tensor(0.0, dtype=_get_scalar_dtype())` with no device, i.e.
   CPU. Confirmed live in torch 2.11.0: an AdamW built with
   `foreach=False, fused=False, capturable=False` holds `state['step']` on CPU.
2. `world_residual_specialist.py:307` loads the optimizer file with
   `map_location=device`. `torch/serialization.py:1917-1920` shows a `torch.device`
   map_location applies the device to **every** storage unconditionally. So the
   saved CPU `step` becomes a `cuda:0` tensor.
3. `torch/optim/optimizer.py:797-801` shows `load_state_dict` deliberately skips the
   usual device cast for the key `step` when neither capturable nor fused is set:
   `if key == "step": ... else: return value`. So the tensor stays a `cuda:0` tensor
   tagged to a CPU-placed parameter.

`before_optimizer` is built from the live optimizer (`capturable=False`), so its
`step` is a CPU tensor. `after_optimizer` is built through `load_grown`, so its
`step` is a `cuda:0` tensor. The test compares them at line 280 with `torch.equal`,
which raises on a device mismatch. The error message is the one recorded:

```
Expected all tensors to be on the same device, but got other is on cuda:0,
different from other tensors on cpu (when checking argument in method wrapper_CUDA__equal)
```

So the failure is a **deterministic, first-entry** failure. The reloaded optimizer
would load, and B would survive, exactly as the earlier assertions in the test
already certified; it is the record's comparison that cannot complete.

The record's proposed remedy ("preserve optimizer tensor placement on reload, in
particular CPU scalar step state for noncapturable AdamW") names the right target.
Its stated mechanism ("Deserialize optimizer state without forcing every tensor to
CUDA; verify original and reloaded device/value identities") is correct and
independently supported by the three rules above. One alternative must be **refused**:
moving `step` to the parameter's device would break the deliberate hosting that rule 1
documents, and would fail `torch/optim/optimizer.py:797-801`'s own exception.

## 3. The fix I recommend, and the reason

`load_grown` returns a fresh container placed on `device`, and its parameters are
constant in device by construction. The safest verifiable change is to read
`GROWN_OPTIMIZER_FILE` without remapping it, so torch restores optimizer tensors to
exactly the devices they were saved on, and add a device assertion so the next failure
names the offending entry instead of dying inside `torch.equal`:

```
saved = torch.load(directory / GROWN_OPTIMIZER_FILE, weights_only=True)
...
for index, entry in optimizer2.state_dict()["state"].items():
    for key, value in entry.items():
        assert value.device == before_optimizer["state"][index][key].device, (index, key)
```

The `optimizer.load_state_dict(saved)` call can stay as it is. Its own cast rule
(`optimizer.py:797-801`) copies the `step` tensor to a CPU-placed parameter unchanged and
to a `cuda:0`-placed one unchanged, so no extra `.to(device)` is required. Adding one
after the load is harmless if it is asserted rather than assumed.

Do not relax the comparison itself. Preserving the device identity is the point of the
review finding; weakening the comparison would satisfy the same test while deleting the
guarantee.

## 4. Findings

**D-GRW15-01 (MAJOR) — the test cannot distinguish a device migration from a
numerical difference.** The failed assertion compares values, so the first thing that
goes wrong is reported as a device error and no index or key is printed. Recommendation:
assert device and dtype per entry before comparing values, and report `(index, key)`.

**D-GRW15-02 (MINOR) — the numeric directory carries committed test logs.**
`plan_tests_local_junit.xml` and `plan_tests_local_junit_forward02.xml` are outputs, not
sources. They are harmless, but they make the directory's intended contents ambiguous
for the next reader.

**D-GRW15-03 (OBSERVATION, no action) — the failure is not evidence about HELM.** The
record says this itself (`L1 standalone test-double numerical check; no original HELM
checkpoint loaded`). Nothing here bears on model quality, and it must not be cited as a
growth result in either direction.

## 5. Standing

- Preserve the failure. It is retained and correctly labelled `NO_RETRY`.
- `cuda_generators_checked` and the other passing cases are unaffected.
- Any corrected package needs its own prospective admission; I am not authorizing or
  requesting a paid rerun.
- I will re-run the corrected numerical suite's non-CUDA portion on the next delivered
  source, and will withdraw D-GRW15-01 and D-GRW15-02 if the delivered source fixes them.
