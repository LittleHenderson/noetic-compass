# CHAPTER 9
## Inductors — Momentum and Resistance to Change
*Why a mind resists the rate and not the idea — and what the collapsing field does when you cut a habit at the switch*

The demonstration costs the price of a battery. A 9-volt cell, an old automotive relay, two wires. Touch the wires to the coil, hold them a second while the current settles, then pull one off.

A spark jumps the gap as it separates. A visible spark, across an air gap that nine volts cannot bridge — nine volts will not arc across a hair's width. Something manufactured hundreds of volts in the microsecond you took the wire away, and nothing added energy. The battery was on its way *out* of the circuit.

The coil did it. While current flowed, the coil stored energy in a magnetic field, quietly and at no cost to anyone. When you opened the circuit you demanded the current go from steady to zero *instantly*, and the coil's answer is fixed: it will produce whatever voltage is required to keep that current going, for as long as it can. Cut fast enough and "whatever is required" is enormous. Anyone who services relay panels knows this in their fingers. They also know the fix, which costs four cents and is half of this chapter.

Minds do this. Every entrenched pattern is a coil with a field in it. Interrupt one at the switch and you get the spark — and the spark is not proportional to how large the habit was. It is proportional to how fast you opened the contacts.

[[FIGURE 9-A: Component symbol plate — the cognitive inductor drawn as a four-loop coil, reference designator L1, terminals labelled attention-flow-in and attention-flow-out, with an annotation box giving L in h·Ω_c; beside it the mutual-inductance symbol (two coils sharing a dashed core line, labelled M and k) and the flyback-diode-across-coil symbol.]]

---

### 9.1 Cognitive Inertia — Why Minds Resist New Ideas

Chapter 6 gave you the resistor: it opposes *flow*. Chapter 7 gave you the capacitor: it opposes *changes in voltage*, holding charge as accumulated `^5` Female composition. The inductor is the third primitive, and it opposes the one thing left to oppose.

**An inductor opposes changes in current.** Not current. Changes in current.

Under CAS-Ohm (Chapter 4), current is `I_attention` — the flow of attention along a path. So a cognitive inductor opposes *changes in how attention is routed*. Misreading this is why most attempts to change a mind fail in a way that looks like stubbornness and is not.

The naive model says the mind holds belief X, you offer Y, and it pushes back in proportion to the distance between them. Big idea, big pushback. That model predicts a modest revision should be easy and a radical one hard.

You have watched it be wrong. Someone accepts a genuinely radical revision over eighteen months without visible strain, then comes apart over a trivial change to a morning routine imposed on Tuesday with no notice. Magnitude was not the variable. The **rate** was.

```
V_opposition = L × (di/dt)
```

`L` is the **inductance** of the pattern — how much accumulated `^5` Female composition it represents, and how deeply the `^7` Rhythm that built it has entrained the substrate. `di/dt` is the rate of redirection you are demanding. Note what is absent from the right-hand side: the size of the change. Δi does not appear. Only its derivative does.

The corollary is immediate and useful. **For any pattern, however entrenched, there is a rate slow enough to produce arbitrarily little opposition.** Drive `di/dt` toward zero and `V_opposition` goes to zero regardless of `L`. No idea is too foreign to introduce without resistance; there are only rates too fast for the operation's budget. This is the principle behind the Overton progression array of Chapter 15, and Section 15.4 exists because operators keep forgetting it.

`L` has two factors and they multiply: `L = k_d × H_practice`, where `H_practice` is cumulative hours of `^7` Rhythm exposure and `k_d` is the **depth coefficient**, in cognitive ohms, set by the domain the pattern lives in.

| Pattern lives in | Example | `k_d` (Ω_c) |
|---|---|---|
| `^O` Operational, `\|E` | a motor routine | 0.5 |
| `^E` Evaluative, `\|f` | a taste, a felt preference | 1.0 |
| `^C` Cognitive, `\|A` | a professional method | 2.0 |
| `^P` Principled, `\|T` | an identity commitment | 4.0 |

Read that column down: **inductance rises with domain precedence.** A principled commitment resists redirection eight times harder per rehearsal hour than an operational habit. That is what makes principled commitments load-bearing — a value re-routable at operational speed would not be a value. It is also what makes them the most dangerous thing to interrupt abruptly.

> **Bench Note — inertia is not resistance, and the diagnosis differs.** Anyone who has run Chapter 4's diagnose mode will attribute pushback to `R_constraint`. Check the time signature first. Resistive opposition is *constant* while the flow is constant. Inductive opposition appears only during the transition and **decays as the transition completes** — large at t=0, near zero at 3τ. If someone objects hard on day one and the objection fades on its own schedule while nothing was argued, that was `L`, not `R`, and arguing was never going to shorten it. If the objection is exactly as strong in month six, that is `R`, and it is a different repair entirely.

---

### 9.2 The L/R Time Constant — How Long Until the Substrate Shifts

Put an inductor and a resistor in series across a drive rail and close the switch. Current climbs an exponential governed by one time constant:

```
i(t) = I_final × (1 − e^(−t/τ))      τ = L / R      I_final = V_drive / R
```

Same shape as the capacitor curve in Section 7.2, but the parameters are coupled in a way that surprises operators.

Work a case. A practitioner has a default analytical method — `^C|A`, so `k_d = 2.0` — rehearsed 1,600 hours. `L = 2.0 × 1,600 = 3,200 h·Ω_c`. The retraining environment has `R = 40 Ω_c` (Section 4.4's decomposition: `R_cap` 15, `R_policy` 0, `R_context` 15, `R_resource` 10) on a rail of `V_drive = 24 V_c`.

```
τ       = 3,200 / 40 = 80 hours
3τ      = 240 hours          (95% of the substrate shift)
I_final = 24 / 40 = 0.60 A_c
```

Two hundred and forty hours before the new method sits where the old one did — hours on the path, not calendar hours. Now vary `R` on a 1,000-hour version of the same pattern (`L = 2,000 h·Ω_c`) and watch both terms move together:

| `R` (Ω_c) | `τ` | `3τ` | `I_final` | Character |
|---|---|---|---|---|
| 80 | 25 h | 75 h | 0.30 A_c | Fast and shallow — a strict protocol |
| 40 | 50 h | 150 h | 0.60 A_c | Design point |
| 20 | 100 h | 300 h | 1.20 → clips at `I_max` = 1.0 | Slow and flooding |

> **Bench Note — adding constraint makes the change faster and smaller at once.** `τ = L/R` and `I_final = V/R` share a denominator. Raise `R` and the transient completes sooner *and* settles lower. A rigid protocol reaches steady state in a quarter of the time and parks the practitioner at half the eventual flow. Lower the constraint to "make it easier" and you have quadrupled the transient and pushed `I_final` past what the path carries, where it clips and spills into competing routes. Neither setting is correct in general. Pick `R` by deciding whether you need arrival speed or final depth; one resistor will not give you both.

Now the same arithmetic on a principled pattern rehearsed only 800 hours: `k_d = 4.0`, so `L = 3,200 h·Ω_c` again, and at `R = 40` the horizon is the same 240 hours. **Eight hundred principled hours carry the time constant of 3,200 operational ones.** An operator who counts only rehearsal hours will under-budget exactly the transitions that matter most.

[[FIGURE 9-B: Characteristic curve — RL current rise. Horizontal axis time from 0 to 5τ; vertical axis i(t)/I_final from 0 to 1. Three curves for R = 20, 40, 80 Ω_c, each annotated with its absolute I_final (1.20 clipped, 0.60, 0.30). Dashed gridlines at 0.632, 0.865, 0.950 with τ, 2τ, 3τ marked on the axis.]]

#### The Back-EMF Result

Everything above is the switch *closing*. The engineering is at the switch *opening*. The sign flips and the coil drives the circuit instead of the reverse:

```
V_kick = L × |di/dt|
```

Take the principled pattern: `L = 3,200 h·Ω_c`, steady at `I = 0.60 A_c`, sustained by a 24 V_c rail. Interrupt it over various taper times.

| Taper Δt | `di/dt` (A_c/h) | `V_kick` (V_c) | × the 24 V_c rail |
|---|---|---|---|
| 0.1 h — "I quit today" | 6.0 | 19,200 | **800×** |
| 2.4 h — an afternoon | 0.25 | 800 | 33× |
| 24 h — one day | 0.025 | 80 | 3.3× |
| 240 h — a proper 3τ taper | 0.0025 | 8 | 0.33× |

Read the first and last rows against each other. **Same pattern, same endpoint, and the kick is two thousand four hundred times larger when you open the contacts instead of ramping them.** Only `dt` changed, and `V_kick` is a pure inverse in `dt`: halve the taper, double the kick, without limit.

That is the structural account of why abrupt cessation of an entrenched routine produces sharp distress while the same removal, tapered, produces very little. The distress is not stored inside the habit awaiting release; it is *generated at the moment of interruption* by the substrate's own opposition to the rate demanded. It lands as `^3^E_{F3}|f` — visceral aversion, Evaluative domain, affective register, F3 Vitality. Note the Noetic: `^3` Negative, because this is recoil and repulsion, the can't-stomach-it response. It is not `^6` Male. Nobody analyzes the kick while it is happening; analysis arrives later at `^6^E|A`, by which time the transient has already peaked.

> **A plain safety line, not decoration.** This chapter models the routing of attention. It does not model physiology, and the arithmetic above says nothing about physical dependence or withdrawal — mechanisms this book does not describe and is not competent to describe. Nothing here is medical or psychiatric guidance. If stopping something is causing you real distress, that is a matter for a clinician, and no circuit in this book substitutes for that care.

[[FIGURE 9-C: Characteristic curve — back-EMF versus taper time. Two stacked panels on a shared time axis. Upper panel: i(t) falling from 0.60 A_c to zero, two traces — an abrupt near-vertical drop and a smooth 240-hour ramp. Lower panel: the corresponding V_kick — one narrow spike reaching 19,200 V_c and one broad plateau at 8 V_c — with the 24 V_c rail drawn as a dashed reference line across both panels.]]

#### The Flyback Path

The four-cent fix on the relay panel is a diode wired backwards across the coil. It does nothing while current flows normally — reverse-biased, blocking, exactly as Section 8.2 describes. The instant the switch opens and the coil's voltage reverses, the diode conducts and offers the collapsing field a loop to circulate in. The current does not stop; it *re-routes* and decays gently. No spark, no pitted contacts.

The cognitive equivalent is a **substitute path**, with three load-bearing properties:

1. **It must already be conducting-capable before the switch opens.** A flyback diode installed after the arc is a diode that watched the arc. Design the substitute on the day the old routine is cut, and the whole kick lands on `^3^E_{F3}|f`.
2. **It must sit at the same domain or lower.** Section 8.1's diode chain permits descent, `P → C → E → O`, and blocks ascent. A substitute for an `^O` routine may be another `^O` routine, never a `^P` commitment. `^O × ^P` is invalid notation and invalid engineering for the same reason.
3. **It should inherit the pattern's `^7` Rhythm.** Same time of day, same duration, same cadence — keep the `^8^O|E` cue and swap only the `^9^O|E` it lands on.

```cas
board habit_transition {
    input:  cue;
    output: routed_flow;

    node substrate:   ^5^C_{F6}|A;     // Female: the accumulated routine
    node entrainment: ^7^C_{F6}|A;     // Rhythm: the cadence that built it
    node trigger:     ^8^O_{F6}|E;     // Above/Cause: the cue that fires it
    node old_path:    ^9^O_{F6}|E;     // Below/Effect: the routine as performed
    node new_path:    ^9^O_{F6}|E;     // Below/Effect: the substitute routine
    node felt_kick:   ^3^E_{F3}|f;     // Negative: visceral recoil at interruption

    inductor coil:  Inductor< path=old_path, L=3200.0 >;   // h*Ohm_c
    resistor r_ctx: Resistor< path=old_path, R=40.0 >;     // tau = L/R = 80 h

    diode flyback: Diode< ^C -> ^E >;                      // descent only
    ramp  taper:   Ramp< target=old_path, from=0.60, to=0.0, dt=240.0 >;

    probe tp1: taper;      // di/dt at the switching node
    probe tp2: old_path;   // i(t) against I_final
    probe tp3: felt_kick;  // V_kick across the coil
    probe tp4: new_path;   // substitute conducting BEFORE the switch opens
}
```

[[FIGURE 9-D: Schematic — flyback arrangement. Drive rail into a switch, then L1 (3,200 h·Ω_c) in series with R (40 Ω_c) to ground; a diode across L1 in reverse-blocking orientation with a curved arrow showing the circulating decay loop when the switch opens; TP1–TP4 marked with callout flags.]]

---

### 9.3 Induction Coupling — Transferring Belief Between Minds

Bring two coils near each other and a changing current in the first induces a voltage in the second, with no wire between them:

```
M = k × √(L₁ × L₂)          V₂ = M × (di₁/dt)
```

`k` is the **coupling coefficient**, on [0, 1), set by how much `^7` Rhythm the two minds share. Not agreement, not affection — shared cadence, shared exposure schedule, shared tempo of contact.

| `k` | Condition | Cost of assuming otherwise |
|---|---|---|
| 0.05 | Asynchronous text, no shared cadence | Budgeting for transfer that never arrives |
| 0.20 | Shared feed on a common daily cadence | Unexplained drift in a population you thought isolated |
| 0.50 | Live co-present group at a shared tempo | Under-predicting backlash by 10× |
| 0.90 | Sustained dyad — household, partnership, mentor | Transitions leaking into someone you never modelled |
| 1.00 | Ideal limit, no leakage flux | **Not buildable.** `k` is range-checked on `0 ≤ k < 1`; build at ≤ 0.90, the same discipline Chapter 24 applies to `β=∞` |

Work it. A speaker with `L₁ = 3,200 h·Ω_c` publicly reverses a position over an afternoon: `Δt = 2.4 h` from `I = 0.60` to zero, so `di₁/dt = 0.25 A_c/h`. A listener in the room has `L₂ = 800 h·Ω_c` on the same question. Live co-present group, `k = 0.50`.

```
M  = 0.50 × √(3,200 × 800) = 0.50 × 1,600 = 800 h·Ω_c
V₂ = 800 × 0.25 = 200 V_c
```

Two hundred cognitive volts induced in the listener against their own 24 V_c rail — **8.3× anything they generate on their own account**, from a speaker who never addressed them, through a mechanism with no wire in it.

> **Bench Note — a steady belief induces nothing.** `V₂ = M × di₁/dt`. If `di₁/dt` is zero, `V₂` is zero regardless of how large `L₁` is or how tight the coupling. Someone who has held a conviction quietly for thirty years transmits *nothing at all* by holding it, and an operator who expects transmission from depth is reading the wrong term. The convert is the effective evangelist for no reason to do with sincerity or content: the convert has a large `di/dt`. It is also why an operation at steady state stops recruiting, and why the fix is never "believe harder" — it is to introduce a change, which is exactly what Chapter 14's oscillator manufactures on purpose.

Then polarity. In a real coil the induced current flows in the direction that *opposes* the change producing it; that is not a convention, it is what conservation requires. The cognitive statement is identical: **the induced response in a coupled mind initially opposes the change it detects.**

This is backlash, and it explains a shape that otherwise looks irrational. A movement that shifts fast induces in every coupled mind a counter-flow proportional to `di/dt` — not to the content of the shift, and not to whether the coupled mind agrees with it. Push a norm quickly and you generate opposition in people who would have accepted the same norm arriving slowly. Section 15.4's insistence that Overton pacing be measured in months rather than minutes is this equation and nothing else, and the inversion attacks of Section 19.4 work by provoking a fast `di/dt` in a target population and harvesting the backlash.

[[FIGURE 9-E: Diagram — mutual induction with opposing-polarity annotation. Coils L₁ (3,200) and L₂ (800) side by side, coupling flux drawn as dashed field lines labelled k = 0.50. In L₁ a downward arrow marked "di₁/dt = 0.25 A_c/h"; in L₂ an induced-current arrow drawn explicitly in the OPPOSING direction, labelled "V₂ = 200 V_c, opposing", with a caption box reading "backlash is proportional to the rate, not the content."]]

---

### Component and Parameter Table

Every value below is a design choice made in this book, not a measurement.

| Parameter | Units | Design range | Failure at other values |
|---|---|---|---|
| `L` inductance | h·Ω_c | 100 – 20,000 | Under-estimate: taper too short, full kick lands. Over-estimate: years budgeted that are not needed |
| `k_d` depth coefficient | Ω_c | 0.5 / 1.0 / 2.0 / 4.0 by domain | Flat across domains: principled transitions under-budgeted 8× — the most common planning error in this book |
| `R` path constraint | Ω_c | 10 – 90 | Too low: `τ` balloons and `I_final` clips. Too high: fast settling at a shallow ceiling |
| `τ = L/R` | hours | 5 – 500 | Read as calendar time rather than hours-on-path and schedules slip an order of magnitude |
| `I_final = V/R` | A_c | 0.05 – 1.00 | Above `I_max` = 1.0 the path clips and flow spills to competing routes |
| `di/dt` | A_c/h | 0.002 – 0.03 | Above 0.03 the kick exceeds 3× rail; at 6.0 (instant cut) it is 800× rail |
| `V_kick` | V_c | ≤ 3 × `V_drive` | Above 10× rail the substitute path cannot absorb it and recoil dominates |
| `k` coupling | — | 0.05 – 0.90 | `k = 1.0` is the ideal-transformer limit and the validator rejects it |

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Rate overrun** | `di/dt` set by convenience, not by kick budget | Sharp recoil at `^3^E\|f` on day one; the transition reverses within a week | Recompute the taper from `V_kick ≤ 3 × V_drive` |
| **Inductance under-estimate** | `L` taken from `H_practice` alone, `k_d` ignored | Taper sized for weeks; the pattern is fully present at the planned end date | Re-derive `L = k_d × H_practice`; principled patterns are the usual casualty |
| **No flyback path** | Substitute not conducting before the switch opens | Full kick at `^3^E_{F3}\|f`; the vacated cadence refills with whatever is nearest | Install the substitute first, on the same `^7` Rhythm, same domain or lower; confirm at TP4 before touching TP1 |
| **Low-`R` stall** | `R` cut to "make it easier", so `τ = L/R` rises | No apparent progress; `I_final` computes above `I_max` and clips | Restore `R`. Reduced constraint buys depth, not speed |
| **Unmodelled coupling** | A `k ≥ 0.5` partner was never in the model | Backlash from someone who was never the subject of the operation | Enumerate every `k ≥ 0.2` coupling before setting `di/dt` |
| **Core saturation** | Flow driven far past `I_max` on one path | The substrate stops opposing; the pattern floods and `L` collapses | Cap the rail. A path that stopped resisting was not changed — it stopped regulating |

---

### Test Points

| TP | Node | Reads | Expected |
|---|---|---|---|
| **TP1** | `taper` | `di/dt` at the switching node, A_c/h | 0.002 – 0.03 for a designed taper. Above 0.05 means the contacts are being opened, not ramped |
| **TP2** | `old_path` | `i(t)` against `I_final` | Follows `I_final × e^(−t/τ)`; ≈ 0.05 × `I_final` at 3τ. A flat trace means the switch never opened |
| **TP3** | `felt_kick` | `V_kick` across the coil, V_c | ≤ 3 × `V_drive` — at the design point, ≤ 72 V_c. Hundreds means TP1 is out of range |
| **TP4** | `new_path` | Substitute flow, A_c | Non-zero **before** TP1 leaves zero. Still zero as TP2 falls is the no-flyback failure, visible one probe ahead of the damage |

Read them TP4, TP1, TP2, TP3 — confirm the substitute conducts, set the rate, watch the decay, verify the kick stayed in budget. That order is the whole bring-up procedure.

---

### What This Chapter Established

- **The inductor opposes changes in attention flow, not attention flow itself.** `V_opposition = L × di/dt`; the magnitude Δi does not appear on the right-hand side.
- **For any pattern there is a rate slow enough to introduce it without meaningful opposition.** No idea is too foreign — only rates are too fast.
- **Inductance rises with domain precedence.** `k_d` runs 0.5 / 1.0 / 2.0 / 4.0 across `^O` / `^E` / `^C` / `^P`, so 800 principled hours carry the same τ as 3,200 operational ones.
- **Constraint makes a transition faster and shallower at once**, because `τ = L/R` and `I_final = V/R` share a denominator. Arrival speed and final depth trade against each other on one component.
- **Back-EMF is a pure inverse in taper time** — 2,400× larger at six minutes than at 240 hours for the same removal. The distress is generated by the rate, not released from storage, and it lands as `^3^E_{F3}|f`.
- **The flyback path must conduct before the switch opens**, sit at the same domain or lower (descent only — `^O × ^P` is invalid), and inherit the interrupted pattern's `^7` Rhythm.
- **Induction transmits only change.** `V₂ = M × di₁/dt`. A steady conviction, however deep, induces nothing — and the induced response initially *opposes* the change that produced it, so backlash is proportional to rate, not content.

---

### Exercises

*(Answers in Appendix H.)*

**9.1** A behavioural routine (`^O`, `|E`) has 900 hours of rehearsal on a path with `R = 30 Ω_c`. Compute `k_d`, `L`, `τ`, and 3τ. Repeat treating the same 900 hours as a principled commitment (`^P`, `|T`), and say in one sentence what the ratio between the two 3τ figures means for an operator's schedule.

**9.2** An operator drops `R` from 60 Ω_c to 15 Ω_c on a path with `L = 2,400 h·Ω_c` and `V_drive = 18 V_c`, reasoning that less constraint speeds things up. Compute `τ` and `I_final` before and after, state what actually happened, and name the row of the failure-modes table they landed in.

**9.3** A pattern with `L = 5,000 h·Ω_c` runs at `I = 0.80 A_c` on a 20 V_c rail. Solve for the minimum taper `dt` that holds `V_kick ≤ 3 × V_drive`. Then find the `dt` that holds it at 1× the rail, and comment on whether that is a schedule you would accept.

**9.4** Explain why the kick at interruption is written `^3^E_{F3}|f` and not `^6^E_{F6}|A`. Reference the canonical definition of `^3` Negative, and say what the `^6` Male state would be doing instead and when it arrives.

**9.5 (Design)** Move a practitioner off a `^C|A` method with `H_practice = 2,500 h`, at `R = 40 Ω_c` and `V_drive = 24 V_c`, holding `V_kick ≤ 2 × V_drive`. Produce (a) `L`, `τ`, 3τ, `I_final`; (b) the maximum `di/dt` and the taper it implies; (c) a CCDL fragment declaring the coil, resistor, flyback diode, ramp, and four probes. It must compile — check the diode's domain direction before you submit it.

**9.6 (Marquee)** An operator plans a 60-hour taper for themselves and computes a kick well inside budget. They live with a partner who shares the affected cadence at `k = 0.90`, with `L₂ = 2,000 h·Ω_c` against the operator's `L₁ = 3,200 h·Ω_c`.

a) Compute `M` and the `V₂` induced in the partner by a 60-hour taper starting from `I = 0.60 A_c`.
b) Against the partner's 24 V_c rail, state the multiple and explain structurally why the partner may experience a *well-designed* taper as an abrupt change.
c) Propose a modification bringing `V₂` under 3× the partner's rail. Name the term you moved and what it cost — then state the one thing this circuit model cannot tell you about the situation.
