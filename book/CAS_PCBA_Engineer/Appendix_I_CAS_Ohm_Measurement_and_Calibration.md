# Appendix I — CAS-Ohm Measurement and Calibration

Chapter 5 gave you the law. This appendix gives you the instrument.

Everywhere else in this book, `V_drive`, `I_attention`, and `R_constraint` are
design choices — numbers you pick to illustrate a circuit. That is the right
way to learn. But a board you actually ship gets *measured*, and measurement
needs three things the design view never supplies: a scale everyone agrees on,
a procedure that produces the same number twice, and a way to tell the
difference between a circuit that is behaving and one that merely looks like
it is.

That is what follows. Nothing here changes a component. It changes what you
write on the test report.

---

## Units and scales — read this before you write a number

The single most common way to corrupt a CCB test report is to mix scales. Four
different quantities in this book are measured on four different ranges, and
three of them are dimensionless. Learn the table; there is no way to infer it
from the symbols.

| Quantity | Symbol | Range | What it is |
|---|---|---|---|
| Constraint (resistance) | `R` | 0–100 | Opposition to cognitive flow. Higher = more constrained. |
| Activation, saturation, cutoff, threshold | `sat`, `cutoff` | 0–1 | Fraction of the path's ceiling. Safety CJTs saturate at 0.85–0.97. |
| Stage gain | `β` | unbounded, typically 0.5–5 | Δeffect per unit Δcause. |
| Dial setting | `Dial(^n)` | **integer** 3–9 | A hard-stopped operator setting, not a measurement. |
| Board supply rail | `F1…F7` | 3.3–12 V | Board specification in the electrical analog. |

Three rules follow from that table, and every one of them has bitten someone.

**A Dial is set; resistance is measured.** You set `Dial(^2)` to an integer
between 3 and 9 — the compiler rejects anything else with HTTP 422. What you
then *measure* on that path is `R_total`, a decimal, and it is not the Dial.
Writing `Dial(^2) = 6.4` is a category error, not a precise reading.

**Normalize before you compare.** A raw flow reading means nothing across two
boards until you divide by that path's full-scale value:

```
I_Q = min(10, 10 × I_raw / I_FS)
```

`I_FS` is the flow the path produces with constraint at its floor and drive at
its rail. Measure it once per path, record it on the test report, and never
compare two `I_raw` figures from different boards.

**The normalized 0–10 reading is a *reading*, not a component value.** It is
what your instrument reports. Component values stay on the ranges in the table
above. If you find yourself writing `R = 2.0` on a resistor, you have written a
normalized reading into a component field, and the compiler's range check will
catch it. Convert: `R_component = 10 × R_normalized`.

> **Bench Note.** The fastest way to spot a mixed-scale report is to look for a
> saturation figure above 1. If you see `sat = 8.5`, someone recorded a
> normalized reading in a component field. The value is 0.85.

---

## The three modes

CAS-Ohm has one equation and three uses. Which one you are doing depends
entirely on which term you do not know.

```
V_drive = I_attention × R_constraint
```

**Measure — `I = V / R`.** You know the drive and the constraint; you want the
flow. This is the design-time prediction, and it is what you compare a live
reading against.

**Design — `V = I × R`.** You know the flow you need and the constraint you are
stuck with; you want the drive required to get there. This is how you size a
supply rail on a CPMB.

**Diagnose — `R = V / I`.** You applied a known drive, you observed a flow, and
you want to know what the path is actually resisting. This is the mode that
finds faults, and it is the reason §I.4 exists.

Cover the term you do not know; the remaining two tell you how to combine them.

---

## Where constraint comes from

`R_constraint` in Chapter 5 is a single number. In a real board it is a sum,
and knowing the parts is what lets you fix a constrained path instead of just
noting that it is constrained.

```
R_total = R_cap + R_policy + R_context + R_resource
```

- **`R_cap`** — capability. The path is constrained because the system cannot
  do the thing well. Falls as competence rises.
- **`R_policy`** — deliberate. A safety boundary, a refusal rule, a hard
  constraint you *installed*. On a CSB this is supposed to be high.
- **`R_context`** — situational. Ambiguity, missing information, conflicting
  instructions in the prompt.
- **`R_resource`** — budgetary. Context window, latency ceiling, token budget.

Capability-derived resistance has a closed form, because capability and
constraint are inverses:

```
R_cap = R_min + (R_max − R_min) × (1 − P_cap / 10)
```

`P_cap` is the capability score on the 0–10 normalized scale. At `P_cap = 10`
the path is unconstrained by skill and `R_cap = R_min`; at `P_cap = 0` it is
maximally constrained and `R_cap = R_max`.

This decomposition matters diagnostically. A path with `R_total = 70` tells you
nothing. A path with `R_policy = 60, R_cap = 10` is a *working safety board*. A
path with `R_cap = 60, R_policy = 10` is an *incompetent* one. Same total,
opposite verdicts, opposite fixes.

### Decoding D/W/P

Chapter 8 introduces the RPM chain as `A0 → Dₙ → Wₙ → Pₙ → Outcome` and never
says what the letters stand for. They are:

- **D — Desire.** The motivational prerequisite. Does the system want the
  outcome enough to push toward it? This is the drive term, `V`.
- **W — Wisdom.** The know-how prerequisite. Does it know what to do? This
  governs how much of the drive converts into useful flow, `I`.
- **P — Power.** The capability prerequisite. Can it actually execute? This is
  the inverse of `R_cap`.

Treat the D↔V, W↔I, P↔R_cap crosswalk as an aid to intuition, not a proof.
It is a mapping between two vocabularies for the same bottleneck, and it has
not been measured against a live model.

**RPM remains one-directional.** The scan descends into an unmet prerequisite
and returns; that is tree traversal, not reversal. No satisfied prerequisite is
ever un-satisfied by the return, so the section-retraction property from
Appendix G holds unchanged.

---

## Residual diagnosis — finding constraint you did not install

This is the part of the appendix that earns its place.

Predict the flow from what you believe the circuit to be. Measure what it
actually does. The difference is the fault.

```
I_pred  = V_drive / R_known
ΔI      = I_obs − I_pred
R_hidden = V_drive / I_obs − R_known
```

`R_known` is the constraint you can account for — the resistors you placed, the
policy you wrote, the budget you set. `R_hidden` is everything else.

Read the residual like this:

| Observation | Reading | Where to look |
|---|---|---|
| `ΔI ≈ 0` | Circuit matches the schematic. | Nothing. Record and move on. |
| `ΔI < 0`, `R_hidden > 0` | Something is resisting that you did not install. | Undocumented policy, a saturating upstream stage, resource exhaustion. |
| `ΔI > 0`, `R_hidden < 0` | Flow exceeds what the constraints permit. | **A bypassed constraint.** Treat as a safety finding, not a performance win. |
| `ΔI` varies run to run at fixed `V` | The path is not deterministic. | Sampling temperature, context leakage, a capacitor holding state across runs. |

The third row is the one to take seriously. On a Cognitive Safety Board, flow
higher than the installed resistance allows means a refusal path is being
routed around. Chapter 24's walk-down procedure starts here.

> **Bench Note.** `R_hidden` is a residual, not a component. Do not add it to
> the schematic. Find what it is, name it, and place a real component — or
> remove whatever is bypassing the one you already placed.

---

## Equivalent resistance for nested assemblies

When a CJT's bias path is itself built from sub-circuits, collapse them before
applying the law.

**Series — constraints stack.** Flow passes through every stage in turn:

```
R_eq = Σ R_k
```

**Parallel — constraints divide.** Flow has alternative routes:

```
1 / R_eq = Σ (1 / R_k)
```

Parallel paths are the more dangerous configuration on a safety board, and the
arithmetic shows why. Two constraints of 80 in parallel give an equivalent of
40 — *less than either alone*. Every alternative route you add lowers total
resistance. A refusal implemented as three parallel checks is weaker than the
weakest single check, not stronger.

That is the quantitative form of the argument Chapter 21 makes about redundant
versus fused safety architecture. Redundancy in parallel divides resistance;
genuine integration does not.

**Cascades multiply gain, but flow is local.** Chapter 11 gives
`β_total = Π β_k`. Gain compounds along the chain. Flow does not: each stage's
`I` is set by *that stage's* local drive and resistance. A late stage starved by
its own high `R` will not be rescued by a high-gain stage upstream — it will
saturate the upstream stage instead and clip.

---

## Field protocol

Run this in order. Skipping step 2 is the most common cause of unreproducible
test reports.

1. **Identify the path.** Name the cause, bias, and effect states in canonical
   notation — e.g. `^8^C_{F2}|A → ^6^E_{F6}|A → ^9^C_{F2}|A`. If you cannot
   type the path, you are not ready to measure it.
2. **Establish full scale.** Drive at rail, constraint at floor. Record `I_FS`.
   This is per-path and does not transfer.
3. **Record installed constraint.** Sum `R_cap + R_policy + R_context +
   R_resource` into `R_known`. Note which terms you estimated.
4. **Predict.** `I_pred = V_drive / R_known`.
5. **Apply and observe.** Record `I_obs`, normalized via `I_Q`.
6. **Compute the residual.** `ΔI` and `R_hidden`. Read against the table in
   §I.4.
7. **Note the operating region.** Cutoff, active, saturation, or breakdown, per
   Chapter 9. A residual computed on a saturated stage is meaningless — the
   stage is clipping, not resisting.
8. **Repeat three times.** A single reading is an anecdote.

### Worksheet

```
PATH ________________________________________________
  cause  ^__^__ _{F_} |_      bias   ^__^__ _{F_} |_
  effect ^__^__ _{F_} |_

FULL SCALE          I_FS ______
DRIVE               V_drive ______

INSTALLED CONSTRAINT
  R_cap ______  R_policy ______
  R_context ______  R_resource ______     R_known ______

PREDICTED           I_pred = V / R_known  ______
OBSERVED  run 1 ______  run 2 ______  run 3 ______
NORMALIZED          I_Q ______

RESIDUAL            ΔI ______   R_hidden ______
REGION              cutoff / active / saturation / breakdown
VERDICT             ____________________________________
```

---

## Maturity bands

For reporting a capability score without implying more precision than you have,
bin `P_cap` into four bands and tag the direction of travel.

| Band | `P_cap` | Meaning |
|---|---|---|
| **M1 — Absent** | 0.0–2.5 | The capability is not present. |
| **M2 — Emerging** | 2.5–5.0 | Present under favorable conditions only. |
| **M3 — Developing** | 5.0–7.5 | Reliable in the common case; fails at the edges. |
| **M4 — Mature** | 7.5–10.0 | Reliable including edge cases. |

Tag each with `↑` rising, `→` stable, or `↓` waning. `M2↑` and `M3↓` are the
same score band travelling in opposite directions and call for opposite
interventions.

Bands are a *reporting* convenience. Compute with the decimal; report the band.

---

## What these numbers are, and are not

Every figure produced by this appendix is a **design score, a calibration
value, or an observed rating**. None of it is a voltmeter reading from a brain
or a language model. There is no instrument that measures attention flow in
volts.

The engineering value is not in the absolute numbers. It is in three things
they make possible: consistency between two engineers measuring the same board,
test points that a later run can be compared against, and falsifiable
predictions — `I_pred` is a claim that can turn out wrong, and that is exactly
what makes the residual in §I.4 diagnostic.

The relationship between drive, flow, and constraint is testable in principle.
It has not been measured against a live model. Do not write "proportional" on a
report; write the numbers you took and the procedure you took them with.

One notational caution. This book uses `Ω` in two ways: in Chapter 5's prose it
is the electrical unit, in CAS recipe notation (`Θ(Ω_safe_refusal)`) it names an
emergent outcome. Never use `Ω` as shorthand for CAS-Ohm. Spell it out.
