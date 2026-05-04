# PR #14 Miscellaneous Test Failure Triage

Branch under review: `consolidation/tier-1-tri-channel` (PR #14, "Tier-1 tri-channel consolidation").
Triage scope: 3 test failures (5 sub-tests total) that did not fall under the other parallel triage agents' scopes.

## TL;DR

All 5 sub-failures **pre-exist on `master`** and **none are introduced by PR #14**.
Verified by `git diff --stat master consolidation/tier-1-tri-channel` against every
relevant test file and production module — diff is empty for all of them. PR #14 does
not touch `test_data.py`, `test_lacunarity.py`, `test_meta_logic_constructs.py`,
`augment.py`, `lacunarity_gate.py`, `structural_hash.py`, or `rust_bridge.py`.

Recommended action: do not block PR #14 on these. Each is logged below with a
recommended follow-up PR scope.

---

## 1. `test_data.py::TestAugmentation::test_domain_averages_w_axis_swap`

**Symptom**

```
assert flipped[0] > flipped[1]   # 0.25 > 0.25
AssertionError: assert 0.25 > 0.25
```

**Root cause — test bug (poor test data, strict-inequality on a tie).**

Input: `avgs = [0.30, 0.20, 0.25, 0.25]`. The W-axis swap in
`cas-native/training/augment.py::_flip_domain_averages` does P↔O and C↔E, then
renormalizes. Output: `[0.25, 0.25, 0.20, 0.30]` (sum already ≈1.0, renormalize is
a no-op). The test asserts `flipped[0] > flipped[1]` with `>`, but both values
are tied at 0.25 because the input had `avgs[2] == avgs[3] == 0.25`.

The production function is correct (matches its docstring and the comment in the
test). The test fixture data fails to discriminate position 0 vs position 1 after
the C↔E swap.

**Recommended action**

Fix the test in a small follow-up PR. Either change input to
`[0.30, 0.20, 0.20, 0.25]` (so position 0 = original[3] = 0.25 > position 1 =
original[2] = 0.20), or replace the strict-inequality assertion with an explicit
positional check `assert flipped[0] == pytest.approx(0.25); assert flipped[3] ==
pytest.approx(0.30)`. **Do not** weaken to `>=`, because that hides bugs.

**Status: pre-existing test bug. Out of PR #14 scope.**

---

## 2. `test_lacunarity.py::TestLacunarityGate::test_high_lacunarity_triggers_correction`

**Symptom (when imports work)**

```
assert tensor(0.9975, grad_fn=<MeanBackward0>) < tensor(0.9610)
```

(On master and on PR #14, the test currently fails earlier in the import phase
because `cas_native/model/structured_token_embedding.py` ↔
`cas_native/training/structured_token_adapter.py` form a circular import. That
import cycle is a separate pre-existing issue affecting all of `test_lacunarity.py`
collection. Reproducing the assertion requires bypassing the package
`__init__.py` and loading `lacunarity_gate.py` directly via `importlib.util` —
which I did to confirm root cause.)

**Root cause — pre-existing design/test mismatch on an untrained learned module.**

`LacunarityGate` is an `nn.Module` with `nn.Linear(num_slots, num_slots)` rebalance
weights. At random init those weights produce arbitrary per-slot deltas, then
`F.softmax(corrected / 0.1, dim=-1)` (temperature 0.1) sharpens whatever the
largest output is. With a 0.96 spike at slot 5 in the input, the random
post-correction logits at slot 5 are typically large enough that the temperature-0.1
softmax sharpens the distribution toward slot 5, **increasing** the spike to
0.9975 instead of dampening it.

The test assumes the gate produces dampening behavior at random init. The
production module does not promise that — it is a *learned* corrector that
requires training before its dampening behavior holds.

**Recommended action**

Two valid follow-up directions, pick one:

- **Option A (test-side):** rewrite the test to either (a) seed the rebalance
  layer with a deterministic dampening initialization (e.g. small negative
  diagonal) before calling `forward`, or (b) train the gate for a few steps on a
  toy dampening objective inside the fixture, then assert behavior.
- **Option B (production-side):** add a deterministic safety shim to
  `LacunarityGate.forward` so that, when `lacunarity > threshold` and gate
  strength is above some floor, the spiky slot is *guaranteed* to be reduced
  even at random init (e.g. mix the correction with a fixed inverse-mass term).

Either is fine for a separate PR. Do not touch in PR #14.

**Status: pre-existing design/test mismatch. Also blocked by separate
pre-existing circular-import bug in `cas_native/model` ↔ `cas_native/training`.**
**Out of PR #14 scope.**

---

## 3. `test_meta_logic_constructs.py` — three sub-tests

These three tests reference production APIs that **do not exist** in current
production code. The tests appear to be aspirational / written against a
planned-but-unshipped extension of `validation/structural_hash.py` and
`validation/rust_bridge.py`.

### 3a. `test_dataset_construct_metadata_is_collated`

**Symptom**

```
assert batch["construct_metadata"][0]["construct_tokens"] == ["Pullback"]
AssertionError: assert ['NoeticCluster', 'Pullback'] == ['Pullback']
```

**Root cause — test bug.**

`cas_native.model.meta_logic_constructs.construct_tokens(expr)` returns *every*
construct in `CONSTRUCT_VOCABULARY` that appears in the expression. For
`"Pullback(NoeticCluster{^2, ^7}, NoeticCluster{^7, ^8})"` it correctly returns
`("NoeticCluster", "Pullback")`. The test assertion expects only the outer
construct (`"Pullback"`), which is inconsistent with the documented behavior of
`construct_tokens` and inconsistent with how
`training/data_pipeline.py::CASDataset.__getitem__` populates the metadata.

**Recommended action**

Update the assertion to `["NoeticCluster", "Pullback"]` (matches actual
production behavior, which is the more useful thing to track).

### 3b. `test_structural_hash_includes_construct_metadata`

**Symptom**

```
TypeError: StructuralPattern.__init__() got an unexpected keyword argument
'expression_kind'
```

**Root cause — test references nonexistent fields.**

`validation/structural_hash.py::StructuralPattern` fields (verified via
`dataclasses.fields`):
`[noetics, domains, drives, registers, register_sets, emergent_register_name,
recipe_shape, validation_kind]`. The test passes `expression_kind=...` and
`construct_tokens=...` — neither field exists.

### 3c. `test_compiler_pass_through_can_return_diagram`

**Symptom**

```
TypeError: BridgeConfig.__init__() got an unexpected keyword argument
'compile_expression'
```

**Root cause — test references nonexistent field and nonexistent method.**

`validation/rust_bridge.py::BridgeConfig` fields:
`[cache_capacity, rust_engine, allow_per_sample_fallback]`. The test passes
`compile_expression=...` which doesn't exist. Additionally,
`RustValidationBridge.validate_compiler_expression_batch(..., include_diagram=...)`
called by the test does not exist in `rust_bridge.py` (no such method, no such
parameter).

**Recommended action for 3b + 3c (combined)**

These tests document a *desired* extension of the validation bridge — capability
to (i) tag patterns by `expression_kind`/`construct_tokens` so that meta-logic
constructs of different kinds get different cache keys, and (ii) pass-through
compiler-produced diagrams via the bridge. That extension has not yet shipped.

Either:
- **Mark these tests `@pytest.mark.xfail(reason="awaiting validation-bridge meta-logic extension")` in a small follow-up PR**, with a tracking issue for the extension itself; or
- Implement the production extension (add `expression_kind` + `construct_tokens`
  fields to `StructuralPattern`, plumb through `structural_hash`; add
  `compile_expression` injector + `validate_compiler_expression_batch(include_diagram=...)`
  method to `BridgeConfig` / `RustValidationBridge`). This is real engineering
  work — out of scope for any "fix the failing test" PR.

**Status: aspirational tests against unshipped production API. Pre-existing on
master. Out of PR #14 scope.**

---

## Summary table

| Test | Category | Pre-existing on master? | PR #14 modifies? | Recommended fix scope |
|------|----------|--------------------------|------------------|----------------------|
| `test_domain_averages_w_axis_swap` | Test bug (tie + strict `>`) | yes | no | Small test-only follow-up PR |
| `test_high_lacunarity_triggers_correction` | Design/test mismatch (untrained learned module) | yes | no | Test fixture or production safety shim — separate PR |
| `test_dataset_construct_metadata_is_collated` | Test bug (wrong expected value) | yes | no | Small test-only follow-up PR |
| `test_structural_hash_includes_construct_metadata` | Aspirational (fields don't exist) | yes | no | Either xfail or implement bridge extension |
| `test_compiler_pass_through_can_return_diagram` | Aspirational (method doesn't exist) | yes | no | Either xfail or implement bridge extension |

## Verification commands (reproducible on pod or local)

```bash
cd /workspace/tksCAS/noetic-compass-scaffold/noetic-compass
# On consolidation/tier-1-tri-channel
python3 -m pytest \
  cas-native/tests/test_data.py::TestAugmentation::test_domain_averages_w_axis_swap \
  cas-native/tests/test_meta_logic_constructs.py -v
# Switch to master and re-run — same 4 failures (lacunarity blocked by import cycle on both).
```
