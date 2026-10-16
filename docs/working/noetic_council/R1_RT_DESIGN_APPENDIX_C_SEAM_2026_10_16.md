# R1-RT — design, appendix C: the seam, measured, and its consequence for the shape

**Added:** 2026-10-16 PDT by the council's R1-RT turn. **Status:** DESIGN, APPENDIX. This is the
appendix that changes the recommendation. All of it is read from the source; nothing was run,
nothing was changed, nothing was spent.

---

## 1. The question this answers

Part one recommended **shape 1 — two processes** — on the strength of one measurement: the recipe
brain never touches the runtime's store, so a torch-free process holding it is genuinely torch-free.
That recommendation silently assumed the brain's work could be done *outside* the runtime's neural
path. **It cannot**, and this appendix shows why.

## 2. The brain's slot, exactly

`runtime.py:1006` is the only place the runtime invokes a brain:

```python
proposal = self.network.forward_node(cjt_id, materialized.cause_tensor, materialized.control)
```

`network.py:120-128` then dispatches to the node:

```python
spec = self.spec(cjt_id)
return self.node(cjt_id)(x, control, operation_id=spec.operation_id)
```

which is `NeuralCJT.forward` at `neural.py:358`. Inside it, five steps in order:

| line | what happens |
|---|---|
| 365 | `registration = self.operations.executable_registration(operation_id)` |
| 366 | `self._validate_operation_binding(control, registration)` |
| **371** | **`_, telemetry = self.engine(x, control)`** — CASformer runs |
| 373-374 | the attention merges heads and projects: `projected_effect` |
| **375** | **`transformed = self.operations(operation_id, projected_effect)`** — the operation module |
| 377-388 | the execution mask is taken from the telemetry, and the candidate effect is `transformed` where the mask is set, zero elsewhere |
| 393-399 | the `NeuralCJTProposal` is built with **that same telemetry** |

And `neural.py:270-285` shows what an operation module *is*:

```python
def forward(self, operation_id: str, value: Tensor) -> Tensor:
    ...
    if not isinstance(value, Tensor):
        raise NeuralCJTError("operation input must be a torch.Tensor")
    result = self.modules_by_operation[registration.operation_id](value)
    if registration.operation_id in self._extension_ids:
        if not isinstance(result, Tensor):
            raise NeuralCJTError("extension operation must return a torch.Tensor")
        if (result.shape != value.shape or result.dtype != value.dtype
                or result.device != value.device):
            raise NeuralCJTError("extension operation must preserve tensor shape, dtype, and device")
```

**So the operation is a tensor-to-tensor function, and the seam is one call at `neural.py:375`.** It
receives `projected_effect` — a tensor whose shape, dtype and device the returned tensor must match
exactly — and returns the tensor that becomes the answer the decoder reads.

## 3. The barrier that decides the shape

`runtime.py:1011-1025`, immediately after the brain returns:

```python
neural_route = proposal.telemetry.attention
if (not torch.equal(neural_route.effective_path_mask, materialized.routing.effective_mask)
        or not torch.equal(neural_route.current, materialized.routing.current)
        or not torch.equal(neural_route.total_current, materialized.routing.total_current)):
    raise RuntimeContractError(
        "executed neural routing does not match the materialized control route")
```

**The runtime cross-checks the routing the brain reports against the routing it materialized.** And
that telemetry is not something a bridge supplies — it comes out of `self.engine(x, control)` at
`neural.py:371`, which is CASformer attention running on the real tensors.

So a bridge that *replaced* the brain call would have to fabricate a `CASformerTelemetry` whose
attention fields exactly equal the materialized route. **That is not a bridge. That is a forgery of
the check that exists to catch a fabricated route** — the same refusal as shape 3's fabricated type
system, in a different place.

**Therefore the runtime's neural path must actually run.** The recipe brain cannot be substituted for
`network.forward_node`; it can only be substituted for the *operation* that path calls.

## 4. The corrected shape

| | what it is |
|---|---|
| **what stays torch** | the runtime, the engine, the attention, the telemetry, the routing, the store, and `NeuralCJT.forward` |
| **what becomes the recipe brain** | the operation module at `neural.py:375` — a tensor-to-tensor call whose return value becomes the candidate effect |
| **what the bridge must do** | convert `projected_effect` into the brain's ingredients, stock and requirement; carry the request to the torch-free brain; encode its answer back into a tensor of the same shape, dtype and device; return it |
| **what this costs in honesty** | the answer is the recipe brain's, but the routing that carries it is CASformer's. The record must say so: **the brain answered, the network routed** |

**This is neither of the shapes part one offered**, and it is closer to shape 2 than to shape 1. It
is a third shape, and it is the one the code permits:

- **Shape A — the operation is the brain.** `NeuralCJT.forward` runs unchanged, CASformer computes the
  telemetry, and the operation module at line 375 is the bridge: it converts, calls the torch-free
  brain, and encodes the answer. The brain's process stays torch-free **if** the carrier crosses a
  boundary; the shim itself must be an `nn.Module` and therefore holds torch.
- **Shape B — the operation is the brain, in one process.** The same, with the recipe brain's
  `no_torch` blocker lifted so the brain's code runs inside the torch process. Simpler; costs the
  blocker guarantee and needs a new seal.
- **Shape C — replace the brain call.** **Refused**, because it requires forging the telemetry the
  runtime compares against its own materialized route.

## 5. What is still true from part one

- The recipe brain never touches the runtime's store. That measurement stands, and it still means the
  store's custody of the brain's state cannot be direct.
- The `nn.Module` requirement and the frozen `^6` identity stand: `register_operation` refuses to
  replace a built-in, and extension operations must be named `experimental_` — so the shim rides the
  existing operation identity rather than claiming a new one.
- Both frozen conversion rules stand unchanged. The seam receives a **tensor**, so appendix A's
  in-rule now has to extract the case from `projected_effect` rather than from the raw `[1,8,64]`
  input. **That is a change to the in-rule's input, and a change to the in-rule must be re-proved**
  against the runtime's oracle before it is used. It is named here as the next piece of work rather
  than assumed to still hold.

## 6. What the seam actually hands over — measured, and it is not the clean case

The operation receives `projected_effect` from `neural.py:373-374`:

```python
gated_heads = telemetry.cjt_effect
merged_effect = self.engine.attention.merge_heads(gated_heads)
projected_effect = self.engine.attention.out_proj(merged_effect)
```

and `casformer/core.py` shows what the attention does to the trunk before that:
`q = self._split_heads(self.q_proj(x))`, and so on — learned projections.

**The shape is identical to the raw case** (`merge_heads` returns
`[batch, sequence, d_model]` = `[1, 8, 64]`), **but the values are not.** `projected_effect` is a
learned function of the case, not the case's own encoding. Appendix A's in-rule reads channels as
**one-hot identities and raw adjacency**, and a one-hot is destroyed by a linear projection: a 1.0
becomes an arbitrary float. **So appendix A's in-rule cannot read this tensor by testing for
exact 1.0s.**

And the clean `materialized.cause_tensor` — the thing the in-rule was written for — **is not
reachable from this seam.** It is passed to `network.forward_node` at `runtime.py:1008`, and from
there the call chain is `network.node(cjt_id)(x, control, operation_id=…)` → `NeuralCJT.forward` →
`self.operations(operation_id, projected_effect)`. **The operation module is called with one tensor
and an identifier. Nothing carries the case.**

### What follows, and it is a real constraint

| route | verdict |
|---|---|
| read the case from `projected_effect` with appendix A's rule | **impossible** — the one-hots are gone |
| adapt the in-rule to `projected_effect` and re-prove it | **possible but weak** — the projection is a fixed learned function, so a rule could in principle recover the case from it, but the rule would then be reading a transformed tensor and its proof would have to be against that transform, not against the task. It also makes the recipe brain depend on CASformer's weights, which is the opposite of what R1-RT is for |
| reach the case from somewhere else in the call | **not from this seam** — the operation is called with a tensor and an id |
| change the runtime to pass the case to the operation | a runtime edit; the honest version of the fix, and the one that keeps the in-rule intact |

**So the seam is permitted but not sufficient.** The recipe brain can be put where the operation is,
but at that point it can no longer see the question — only the attention's rendering of it.

## 7. The honest options, restated at their true size

| # | shape | what it costs | verdict |
|---|---|---|---|
| **A** | the operation is the brain, two processes | the brain sees `projected_effect`, so the in-rule must be rewritten against the projection and re-proved, and the brain becomes dependent on CASformer's weights | permitted, but it weakens the identity check's meaning |
| **B** | the operation is the brain, one process, blocker lifted | same in-rule problem, plus the blocker guarantee is lost and a new seal is needed | permitted, same weakness |
| **C** | replace `network.forward_node` | requires forging `CASformerTelemetry` to satisfy `runtime.py:1011-1025` | **refused** — fabricating the check that catches fabrication |
| **D** | **pass the case to the operation** | a runtime edit: the operation call gains the case (or `make_input_cause`'s content). The in-rule stays exactly as frozen and proved, and the brain keeps seeing the question rather than a rendering of it | **the only route that keeps the design's meaning**, and it is an edit to the frozen runtime |

**The recommendation changes with this measurement.** Part one recommended shape 1 on a measurement
that turned out not to reach the question. The council now recommends **shape D**, or shape A
explicitly labelled as "the brain answers a projection of the question", because those are the only
two positions that are both permitted by the code and honestly described.

**Between D and A the deciding question is the owner's:** is a runtime edit acceptable in exchange
for an identity check that means what it says?

## 8. What this appendix does not do

- It does not choose. The choice is now narrower and better informed, and it is the owner's.
- It does not measure whether the materialized route and CASformer's attention agree on any given
  input — only that the runtime refuses when they do not.
- It does not re-prove appendix A's in-rule, because on route A the in-rule would have to change and
  on route D it does not. **The freeze still stands for route D and is void for route A.**
- It does not authorise a run. R1-RT's gate is still half met.

