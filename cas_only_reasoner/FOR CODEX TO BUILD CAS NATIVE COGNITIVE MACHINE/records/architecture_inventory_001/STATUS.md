# Architecture inventory — the architecture declares four operations; exactly one is canonical

**Record:** `records/architecture_inventory_001/STATUS.md`
**Reproducer:** `verify_inventory.py` (output `inventory.txt`) — self-checks and reports staleness
**Spend:** $0.00. Read-only inspection of the reference wheel. No forward pass, no device, no target.
**Extends:** `records/bias_role_001/STATUS.md` and OS-027.

---

## What the architecture declares

Read from `cas_cjt.neural.OPERATION_REGISTRATIONS` and
`RegisteredOperationBank(CASformerConfig(d_model=64, …))`:

| op | name | admission | parameters | module |
|---|---|---:|---:|---|
| **`^6`** | decompose | **`CANONICAL_ADMITTED`** | **16,384** | `_DecomposeTransform` |
| `^2` | experimental_attract | `EXPERIMENTAL_OPEN_SEMANTICS` | 8,192 | `_AttractTransform` |
| `^3` | experimental_avert | `EXPERIMENTAL_OPEN_SEMANTICS` | 8,192 | `_AvertTransform` |
| `^8` | experimental_trigger | **`EXPERIMENTAL_CONFLICTED_SEMANTICS`** | 8,192 | `_TriggerTransform` |
| | | | **40,960** | **bank total** |

All four are executable (`bank.executable_registration` resolves for each).

## What the run exercises

`^6` alone, at **16,384 of 40,960 parameters — 40.0%**. The other **24,576 — 60.0%** belong to
operations the wheel itself marks `EXPERIMENTAL_OPEN_SEMANTICS` or
`EXPERIMENTAL_CONFLICTED_SEMANTICS`.

**The run's choice is well founded, and this inventory is what makes that precise.** `^6` is the
only operation whose semantics are *frozen*. The other three carry exactly the condition this
project's ledger records as `OPEN-SEMANTICS`, under which implementation must not derive behaviour
from invented meaning.

## This bounds what "use the full potential of the architecture" can mean

The objective is a machine that uses the full potential of its architecture. **The inventory shows
that 60% of the declared plastic capacity is currently unreachable for a reason that is not
engineering:**

- it is not missing code — the modules exist, are instantiated, and are executable;
- it is not missing capacity — the parameters are there;
- it is **unfrozen or contested semantics**, which the project has explicitly declined to invent.

So the honest statement of where the machine stands is: **of the architecture's declared plastic
capacity, 40% is canonical and exercised, and 60% is experimental and correctly left alone.** The
binding constraint on "full potential" right now is the ontology, not the implementation.

## A second, independent confirmation of the same pattern

Correction 1 required admissibility relations `Dk ⊆ I × I` for each of the ten operators. The
instructions freeze `D0` and state no other; this record measured that the CNCM homebase implements
the guard with **`D0` frozen and `D1`–`D9` refused as unresolved**
(`records/noetica_corrections_001/STATUS.md`).

**The same shape appears here at the operation level**: one operation canonically admitted, three
carrying open or conflicted semantics. Two independent artifacts — the master instructions and the
reference wheel — agree that the CAS ontology is only partially frozen, and that the machine's reach
is bounded by that.

## `^8` is marked *conflicted*, and the project's own instructions say why

The wheel marks `^8` `EXPERIMENTAL_CONFLICTED_SEMANTICS` — stronger than "open". The master
instructions document the specific drift that makes it conflicted, in the anti-drift annotations:

> **`^8` Above/Cause is associative TRIGGERING, not analytical reasoning.** The colloquialisms "that
> reminds me," "one thing leads to another," "triggered a memory" describe associative surfacing of
> Ideas, not deductive inference. Deductive causal analysis is a compound of `^6` Male
> (decomposition) and `^9` Below/Effect (landing), not `^8`. This catches Scheme-B "Causal Reasoning"
> drift that appeared in compiler code, cas-engine docstrings, and multiple chapter examples.

**So the wheel's `EXPERIMENTAL_CONFLICTED_SEMANTICS` on `^8` and the instructions' anti-drift
annotation are the same finding recorded independently.** The architecture is self-consistent about
declining to use `^8`, and that is a point in its favour rather than a gap.

## Where the admitted-but-unused capacity actually is

Excluding the three experimental operations, one genuinely admitted plastic role remains unused, and
it belongs to the **canonical** operation's own contract:

| | |
|---|---|
| contract | `cas.cjt.operation.^6.decompose/0.2` (digest `6bfc2602…`) |
| `plasticity_groups` | `('operation:^6', 'bias_update_head')` |
| used by the run | `operation:^6` — 16,384 parameters |
| **not used** | **`bias_update_head` — 4,096 parameters (64 × 64)** |
| why not | the run's module is a bare `_DecomposeTransform`; the head lives on `NeuralCJT` |

**So OS-027 is the only live question here.** The 24,576 experimental parameters are correctly
untouched; the 4,096 admitted-but-absent ones are the open decision.

## What is NOT established here

- **Nothing was executed.** Modules were instantiated so their parameters could be counted; no
  forward pass, no training, no device, no provider.
- **Parameter counts are not capability.** 40,960 parameters declared says nothing about what any of
  them would achieve.
- **The inventory is a snapshot of the installed wheel**, not of the repository. The reproducer
  compares against the recorded list and prints `THE RECORD IS STALE` if it changes, so the record
  cannot silently rot.
- **No claim that the three experimental operations would help if their semantics were frozen.**
  Nothing here measures what `^2`, `^3` or `^8` would contribute.
- **No claim that `bias_update_head` would help.** See OS-027; the hypothesis there is explicitly
  unsupported.
- **`NeuralCJT`'s parameter list was enumerated, not analysed.** Beyond `bias_update_head`, its other
  parameters were counted but not examined.
