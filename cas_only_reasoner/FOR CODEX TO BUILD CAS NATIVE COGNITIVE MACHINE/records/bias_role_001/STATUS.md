# The `^6` contract admits two plastic groups and a `write_bias` requirement; the run used one

**Record:** `records/bias_role_001/STATUS.md`
**Spend:** $0.00. Read-only inspection of the reference wheel and the frozen contract. No model
executed, no device, no target, no provider.
**Status:** finding recorded. **No change proposed, nothing licensed, no run authorised.**

---

## What was inspected

`cas_cjt.state.make_operation_contract("^6")` — the frozen contract the typed-matched run declared
(`cas.cjt.operation.^6.decompose/0.2`, contract digest
`6bfc2602cfa2c78669fab832aa3a4c2bfc4193f2a54f1947036c6ae3a80e4168`) — read directly from the
installed wheel. Verbatim:

| field | value |
|---|---|
| `contract_id` | `cas.cjt.operation.^6.decompose/0.2` |
| `operation_id` / `operation_name` | `^6` / `decompose` |
| `ontology_status` | `CANONICAL_ADMITTED` |
| **`plasticity_groups`** | **`('operation:^6', 'bias_update_head')`** |
| **`governance_requirements`** | **`('execute', 'publish_effect', 'write_bias', 'learn')`** |
| **`legal_bias_paths`** | **`('/memory', '/rpm', '/operating', '/theta')`** |
| `legal_actions` | `('PROPOSE_EFFECT',)` |
| `neural_transform_id` | `cas.op.decompose.v1` |
| `memory_interface` | `('READ_REFERENCES', 'PROPOSE_WRITE')` |
| `temporal_transition_law` | `EFFECT_TO_CAUSE_ONLY_AFTER_COMMIT` |
| `verifier_digest` | `0de372aebd2def84aa106d821be3c2b5e9ff832ab2be072a3c35c85902389585` |

**The contract admits two plastic groups. It also carries a `write_bias` governance requirement
and four legal bias paths.**

## What the run did

`cas_meta2/graph_teaching/real_framework.py` states the choice in its own module docstring:

> "``cas_cjt.state.make_operation_contract("^6")`` whose admitted plasticity roles are
> ``("operation:^6", "bias_update_head")`` — this run uses ONLY ``operation:^6`` (the module's own
> parameters); ``bias_update_head`` stays frozen."

And the module it builds is a bare `_DecomposeTransform`, not a container that has the head:

| object | parameters |
|---|---|
| `RegisteredOperationBank(cfg).modules_by_operation["^6"]` | **`['left.weight', 'right.weight', 'merge.weight']`** — type `_DecomposeTransform` |
| `NeuralCJT(cfg)` | **30 parameters**, including **`bias_update_head.weight`** |

So `bias_update_head` is not "frozen" in the run — **it is absent from the run's module.** The role
is admitted by the contract and unreachable from the typed-teaching path, because that path
constructs `_DecomposeTransform` directly rather than a `NeuralCJT`.

The typed learner then asserts the narrower scope as a hard requirement of its own
(`cas_meta2/typed_teaching/learner.py`, `TYPED_LEARNER_REGISTERED_SCOPE`):

```python
require(self.scope == {"allowed": list(PARAMETERS), "frozen": [],
        "contract_id": "cas.cjt.operation.^6.decompose/0.2", "role": "operation:^6"}, ...)
```

with `PARAMETERS = ("left.weight", "merge.weight", "right.weight")` and `"frozen": []`.

## What `bias_update_head` is

`cas_cjt/neural.py`:

```python
self.bias_update_head = _linear(config, config.d_model, config.d_model)   # 64 x 64
...
raw_bias_delta = self.bias_update_head(candidate_effect)
proposed_bias_delta = torch.where(execution_mask.unsqueeze(-1), raw_bias_delta,
                                  torch.zeros_like(raw_bias_delta))
```

It is a 64 × 64 linear map that turns the candidate effect into a **proposal-only bias delta**.
`NeuralCJT` is described in its own docstring as a "trainable proposal-only reasoning transistor",
and the contract's `legal_actions` is `('PROPOSE_EFFECT',)`. So the mechanism proposes a bias change
and does not apply one.

## Why this is worth recording

The recorded defect this project has measured most precisely is **a bias**. At cursor 160 the
frozen readout emits only 9 of the 64 world aliases across the 210 world-typed reference slots, with
**`W36` accounting for 44.3%** of them and 55 aliases never emitted at all
(`READOUT_COLLAPSE_RESULT.md`). That is a systematic, input-independent preference for particular
symbols — which is what a bias is — and its cause is still **open**.

**A `write_bias` mechanism, with four legal bias paths, is admitted by the very contract that
governs the operation, and the run never exercised it.**

**That connection is offered as a hypothesis and nothing more.** Nothing here shows that a bias
would remove the concentration, and nothing here shows that the concentration is a bias in the
contract's sense of the word. The two facts are recorded next to each other because they are
striking together; they have not been shown to be the same thing, and no measurement in this record
supports treating them as one.

## The tension, stated and not resolved

There is a genuine inconsistency between two registered artifacts:

- the **contract** admits `('operation:^6', 'bias_update_head')`;
- the **learner** asserts the scope is exactly the three `_DecomposeTransform` matrices with
  `"frozen": []`.

Either the learner's assertion is a legitimate narrowing that the run is entitled to make — in
which case the contract's second group is admitted but unusable from this path, and that should be
said plainly — or the assertion is a defect that makes an admitted mechanism unreachable. **That is
an authority decision, not mine.** Filed as **OS-027**.

**No change is proposed here.** Wiring `bias_update_head` in would change what the run optimises,
would require changing the learner's own `TYPED_LEARNER_REGISTERED_SCOPE` assertion, and would put
the run's declared scope in tension with its own contract. That is a contract question before it is
an engineering one.

## What is NOT established here

- **Nothing was executed.** The contract was read and two module parameter lists were enumerated.
  No forward pass, no training, no device.
- **`bias_update_head` was not tested and is not claimed to help.** Its relationship to the recorded
  concentration is a hypothesis with no measurement behind it.
- **The run's choice may be exactly right.** A narrower scope is easier to defend, and
  `real_framework.py` documents the choice deliberately. This record does not say the choice was
  wrong; it says the consequence is that an admitted role is unreachable, and that no record in
  this tree reports having decided which of the two readings applies.
- **`NeuralCJT`'s other 27 parameters were not examined.** Only the presence and shape of
  `bias_update_head` were verified.
- **No claim about `governance_requirements` semantics.** `('execute', 'publish_effect',
  'write_bias', 'learn')` is quoted verbatim; what satisfying each requirement entails is not
  established here.
