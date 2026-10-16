# R1-RT — design, part two: the bridge as code, the trap, and the arms

**Added:** 2026-10-16 PDT by the council's R1-RT turn. **Status:** DESIGN, PART TWO. This is the
part that can be written without the owner's shape choice, because it describes **what the adapter
must do** and every measurement below is identical under both shapes. It runs nothing and changes
no package.

Part one named the three names, the acceptance test and the coupling. Part two adds the bridge, a
trap the runtime sets, and the arms. What still waits on the owner is which process host the bridge
runs in.

---

## 1. The bridge, measured down to the types

The recipe brain's own modules are **torch-free**, and the package says so about itself. Measured
across `rb/` (25 files), `rb2/` (10) and `rb3/` (9): **zero** torch or numpy imports. One file in
the package does import torch — `r1/t_gb_check.py` — and it is **not** part of the recipe brain: it
is a host-side instrument that regenerates GB3's worlds and counts GB3's parameters, and its own
header states the boundary in one line:

> *"Host only (torch; NOT_RUN_HERE on the laptop) … **Imports nothing from rb (rb blocks torch).**"*

So the boundary already exists in writing, inside the package that wave 1 ran. The runtime's core is
**torch through and through**. The bridge is therefore not a translation between two vocabularies —
it is a **type conversion with a thin torch carrier**, and the recipe brain's own arithmetic stays in
the middle, untouched.

### What the runtime hands the brain

`runtime.py:1006` calls `self.network.forward_node(...)`, which reaches
`neural.py:358 NeuralCJT.forward(x, control, operation_id="^6")` with `x` of shape `[1, 8, 64]`
float32. Measured, that is the **only** input path inside the runtime.

### What the runtime demands back

`neural.py:320` fixes the return type:

```python
@dataclass(frozen=True)
class NeuralCJTProposal:
    operation: OperationRegistration
    candidate_effect: Tensor          # <- the answer the decoder reads
    proposed_bias_delta: Tensor
    execution_mask: Tensor
    telemetry: CASformerTelemetry
```

And `semantic.py:103-116` will not read plain numbers. `logits()` raises unless the effect is a
**real** `torch.Tensor`, floating-point, finite, non-empty, and **exactly the contract's width**:

```python
if (not isinstance(effect, Tensor) or not effect.is_floating_point()
    or effect.ndim < 1 or effect.numel() == 0):
    raise SemanticDecodeError("effect must be a nonempty floating-point Tensor")
if not bool(torch.isfinite(effect).all().item()):
    raise SemanticDecodeError("effect must be finite")
if effect.shape[-1] != self.contract.effect_width:
    raise SemanticDecodeError("effect width does not match decoder contract")
```

Then it takes the **mean over all but the last dimension**, slices the **first 8 channels** (v2),
and argmaxes over the eight labels. So the answer the recipe brain produces must arrive as a
**finite float tensor whose last dimension is at least 8**, and the first eight channels carry the
decision.

### The conversion, both ways

| stage | rule |
|---|---|
| **in** | extract the case's public fields from the `[1,8,64]` input into the recipe brain's own vocabulary. The exact rule is **not yet frozen** — the input has 512 floats in three blocks (node identity, outgoing adjacency, route position) and the recipe brain wants ingredients, stock and requirement. This is the one piece of the bridge that is a **choice**, and freezing it before any run is what makes the result attributable. |
| **compute** | the recipe brain's own code, unchanged, in a process that holds no torch. |
| **out** | encode its answer as a finite float tensor of at least 8 in the last dimension, with the decision in the first eight channels, then wrap it in a `NeuralCJTProposal` whose `operation` is a registration carrying a **real** `torch.nn.Module`. |

That last clause is measured, not assumed. `neural.py:211-212` refuses anything else:

```python
if not isinstance(module, nn.Module):
    raise NeuralCJTError("operation module must be a torch.nn.Module")
```

and `neural.py:217-220` refuses to replace the frozen identities, admitting only the frozen `^6` as
canonical. So the shim is a small `nn.Module` that calls out to the torch-free brain and re-encodes
its answer. **The shim is the carrier; it holds no mathematics.**

## 2. The trap the runtime sets, which the design must defeat

`semantic.py:120-121`:

```python
if bool((effect.detach() == 0).all().item()):
    symbol = self.contract.zero_symbol
```

`DecoderContract.zero_symbol` defaults to **`NO_EFFECT`**, and its own validator at
`semantic.py` `__post_init__` requires that the zero symbol is **distinct from every answer label**.
So an all-zero effect is decoded as `NO_EFFECT`, which is **not one of the eight answers**.

**The consequence, stated plainly:** if the recipe brain's answer ever encodes to all zeros — and a
yield of zero, or a blank slot, is exactly the kind of value this brain produces — the runtime will
report `NO_EFFECT` **instead of** the recipe brain's symbol. An identity check that ignored this
would find a mismatch and blame the brain, when the runtime's own zero-trap produced it.

**The design's rule:** the encoder must be **never-all-zero** by construction, and the acceptance
test must include a case whose recipe answer is genuinely zero, to prove the trap is not firing.
This is written down as a mark, not as a note.

## 3. The marks, extended with what part two taught

Part one's six marks stand. Part two adds three, each because a measurement above made it necessary.

| mark | why it exists |
|---|---|
| `RT_ENCODE_ROUNDTRIP` | the in-rule and the out-rule must be inverse on the cases used, or the identity marks are comparing two different questions. Denominator: the frozen case count; pass: every case round-trips. |
| `RT_ZERO_TRAP` | a case whose true recipe answer is zero must still arrive as one of the **eight** labels, never as `NO_EFFECT`. Pass: the symbol is the expected answer label. This mark exists only because `semantic.py:120` exists. |
| `RT_SHIM_NO_MATH` | a static check that the shim module contains no arithmetic of its own: it converts and wraps, nothing else. Pass: the check finds no numeric operation in the shim beyond the encode step. This is what keeps "the brain answered" honest. |

## 4. The arms, which are identical under both shapes

| arm | what it is | what it is for |
|---|---|---|
| `A1_HOSTED` | the recipe brain, hosted, answering the runtime's task | the measured arm |
| `A2_BROKEN_INTERFACE` | the same bridge with the **encode step stripped** | the control that makes `RT_NON_VACUOUS` mean something. If the identity marks still pass, they measured nothing |
| `A3_BRAIN_ALONE` | the recipe brain outside, answering the same frozen cases | the reference the identity marks compare against |
| `A4_NO_EFFECT` | the bridge forced to emit an all-zero effect | the zero-trap control: it must produce `NO_EFFECT`, proving the trap is live and that `RT_ZERO_TRAP` is testing it rather than passing by luck |
| `A5_RESTART` | `A1`, suspended and reloaded, then asked the same cases again | the restart mark |

**Four of the five arms exist to try to falsify the result.** Only `A1` is the claim; the other four
are the reasons to believe it.

## 5. What is measured, and what one thing is still a choice

**Measured, this turn:** the input path, the return type, the decoder's type demands and its exact
slicing, the `nn.Module` requirement, the frozen-identity rule, the zero trap, and the recipe
brain's core being torch-free.

**Still a choice, and it must be frozen before any run:** the exact **in-rule** that turns the
`[1,8,64]` input into the recipe brain's ingredients, stock and requirement. It is a choice because
the two sides describe different things; it is freezable because the input's three blocks are
documented (`TASK_CONTRACT.md:33-39`) and the recipe brain's inputs are integers and exact
fractions. Freezing it is the difference between "the brain answered" and "the adapter answered".

**And still the owner's:** which process hosts the shim. Under shape 1 the shim lives in the
runtime's process (which must hold torch) and calls out to the torch-free brain; under shape 2 the
shim and the brain share one process that holds torch. Every mark above is the same either way.

## 6. What part two does not do

- It does not freeze the in-rule. That is the next piece of work, and it is arithmetic, not
  architecture.
- It does not run anything, and it changes no package. Under shape 2 the recipe brain's blocker
  would have to be lifted, which is a package edit and therefore needs a new seal and the owner's
  line. Nothing of that kind is done here.
- It does not claim the recipe brain can answer the runtime's task. Nobody has measured that, and
  it is the first thing the run itself would measure.
