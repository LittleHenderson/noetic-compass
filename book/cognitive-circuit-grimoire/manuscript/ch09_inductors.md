# CHAPTER 9

## Inductors — Momentum and Resistance to Change

*Why a mind resists the rate and not the idea — and what the collapsing field does when you cut a habit at the switch*

---

The demonstration costs the price of a battery. A 9-volt cell, an old automotive relay, two wires. Touch the wires to the coil, hold them a second while the current settles, then pull one off.

A spark jumps the gap as it separates — across an air gap nine volts cannot bridge. Something manufactured hundreds of volts in the microsecond you took the wire away, and nothing added energy; the battery was leaving the circuit. The coil did it. While current flowed it stored energy in a magnetic field, at no cost to anyone. When you opened the circuit you demanded that current go from steady to zero *instantly*, and the coil's answer is fixed: it produces whatever voltage keeps the current going. Cut fast enough and "whatever is required" is enormous. Anyone who services relay panels knows this in their fingers, and knows the fix, which costs four cents and is half of this chapter.

Minds do this. Every entrenched pattern is a coil with a field in it. Interrupt one at the switch and you get the spark — and the spark is not proportional to how large the habit was. It is proportional to how fast you opened the contacts.

[[FIGURE 9-A: Symbol plate — cognitive inductor as a four-loop coil, designator L1, terminals attention-in and attention-out, annotation box giving L in h·Ω_c; beside it the mutual-inductance symbol (two coils on a dashed shared core, labelled M and k) and the flyback-diode-across-coil symbol.]]

---

### 9.1 Cognitive Inertia — Why Minds Resist New Ideas

Chapter 6 gave you the resistor: it opposes *flow*. Chapter 7 gave you the capacitor: it opposes *changes in voltage*, holding charge as accumulated `^5` Female composition. The inductor opposes the one thing left to oppose.

**An inductor opposes changes in current.** Not current. Changes in current.

Under CAS-Ohm (Chapter 4), current is `I_attention` — flow of attention along a path. A cognitive inductor therefore opposes *changes in how attention is routed*. Misreading this is why most attempts to change a mind fail in a way that looks like stubbornness and is not.

The naive model says a mind pushes back in proportion to the distance between what it holds and what you offer: big idea, big pushback. You have watched that be wrong. Someone accepts a radical revision over eighteen months without visible strain, then comes apart over a trivial change to a morning routine imposed on Tuesday with no notice. Magnitude was not the variable. The **rate** was.

```
V_opposition = L × (di/dt)
```

`L` is the **inductance** of the pattern — how much accumulated `^5` Female composition it represents, and how deeply the `^7` Rhythm that built it entrained the substrate. `di/dt` is the rate of redirection you demand. Note what is absent on the right: Δi, the size of the change, does not appear anywhere. Only its derivative does.

The corollary is immediate. **For any pattern, however entrenched, there is a rate slow enough to produce arbitrarily little opposition.** Drive `di/dt` toward zero and `V_opposition` goes to zero regardless of `L`. No idea is too foreign to introduce without resistance; there are only rates too fast for the budget. That is the principle behind the Overton progression array of Chapter 15.

`L` has two factors, and they multiply: `L = k_d × H_practice`, where `H_practice` is cumulative hours of `^7` Rhythm exposure and `k_d` is the **depth coefficient**, in cognitive ohms, set by the domain the pattern lives in.

| Pattern lives in | `k_d` (Ω_c) |
|---|---|
| `^O` Operational, `\|E` — a motor routine | 0.5 |
| `^E` Evaluative, `\|f` — a taste, a felt preference | 1.0 |
| `^C` Cognitive, `\|A` — a professional method | 2.0 |
| `^P` Principled, `\|T` — an identity commitment | 4.0 |

**Inductance rises with domain precedence.** A principled commitment resists redirection eight times harder per rehearsal hour than an operational habit. That is what makes such commitments load-bearing — a value re-routable at operational speed would not be a value — and what makes them the most dangerous thing to interrupt abruptly.

> **Bench Note — inertia is not resistance, and the diagnosis differs.** Anyone running Chapter 4's diagnose mode will attribute pushback to `R_constraint`. Check the time signature first. Resistive opposition is *constant* while the flow is constant. Inductive opposition appears only during the transition and **decays as the transition completes** — large at t=0, near zero at 3τ. If someone objects hard on day one and the objection fades on its own schedule while nothing was argued, that was `L`, not `R`, and arguing was never going to shorten it. If it is as strong in month six, that is `R`, and a different repair.

---

### 9.2 The L/R Time Constant — How Long Until the Substrate Shifts

Put an inductor and a resistor in series across a drive rail and close the switch. Current climbs an exponential governed by one time constant:

```
i(t) = I_final × (1 − e^(−t/τ))      τ = L / R      I_final = V_drive / R
```

Same shape as the capacitor curve in Section 7.2, but the parameters are coupled in a way that surprises operators.

Work a case. A practitioner has a default analytical method — `^C|A`, so `k_d = 2.0` — rehearsed 1,600 hours, giving `L = 3,200 h·Ω_c`. The retraining environment has `R = 40 Ω_c` (Section 4.4: `R_cap` 15, `R_policy` 0, `R_context` 15, `R_resource` 10) on a rail of `V_drive = 24 V_c`.

```
τ       = 3,200 / 40 = 80 hours
3τ      = 240 hours          (95% of the substrate shift)
I_final = 24 / 40 = 0.60 A_c
```

Two hundred and forty hours before the new method sits where the old one did — hours on the path, not calendar hours. Now vary `R` on a 1,000-hour version (`L = 2,000 h·Ω_c`):

| `R` (Ω_c) | `τ` | `3τ` | `I_final` |
|---|---|---|---|
| 80 — strict protocol | 25 h | 75 h | 0.30 A_c |
| 40 — design point | 50 h | 150 h | 0.60 A_c |
| 20 — loosened | 100 h | 300 h | 1.20, clips at `I_max` = 1.0 |

> **Bench Note — adding constraint makes the change faster and smaller at once.** `τ = L/R` and `I_final = V/R` share a denominator. Raise `R` and the transient completes sooner *and* settles lower. The strict protocol reaches steady state in a quarter of the time and parks the practitioner at half the eventual flow. Loosen the constraint to "make it easier" and you have quadrupled the transient and pushed `I_final` past what the path carries, where it clips and spills into competing routes. Pick `R` by deciding whether you need arrival speed or final depth; one resistor will not give you both.

The same arithmetic on a principled pattern rehearsed only 800 hours: `k_d = 4.0`, so `L = 3,200 h·Ω_c` again, and at `R = 40` the horizon is the same 240 hours. Against a motor routine the gap is wider still, because `k_d` there is 0.5: **eight hundred principled hours carry the time constant of 6,400 operational ones**, which is the 8× ratio of the `k_d` column and nothing more. Count only rehearsal hours and you under-budget exactly the transitions that matter most.

[[FIGURE 9-B: RL current rise. Time 0 to 5τ on x, i(t)/I_final 0 to 1 on y. Three curves for R = 20, 40, 80 Ω_c, annotated with absolute I_final (1.20 clipped at 1.0, 0.60, 0.30). Dashed gridlines at 0.632, 0.865, 0.950; τ, 2τ, 3τ marked.]]

#### The Back-EMF Result

Everything above is the switch *closing*. The engineering is at the switch *opening*. The sign flips and the coil drives the circuit instead of the reverse:

```
V_kick = L × |di/dt|
```

Take the principled pattern: `L = 3,200 h·Ω_c`, steady at `I = 0.60 A_c`, on a 24 V_c rail.

| Taper Δt | `di/dt` (A_c/h) | `V_kick` (V_c) | × the 24 V_c rail |
|---|---|---|---|
| 0.1 h — "I quit today" | 6.0 | 19,200 | **800×** |
| 2.4 h — an afternoon | 0.25 | 800 | 33× |
| 24 h — one day | 0.025 | 80 | 3.3× |
| 240 h — a proper 3τ taper | 0.0025 | 8 | 0.33× |

Read the first and last rows against each other. **Same pattern, same endpoint, and the kick is two thousand four hundred times larger when you open the contacts instead of ramping them.** Only `dt` changed, and `V_kick` is a pure inverse in `dt`: halve the taper, double the kick, without limit.

That is the structural account of why abrupt cessation of an entrenched routine produces sharp distress while the same removal, tapered, produces very little. The distress is not stored inside the habit awaiting release; it is *generated at the moment of interruption* by the substrate's own opposition to the rate demanded. It lands as `^3^E_{F3}|f` — visceral aversion, Evaluative domain, affective register, F3 Vitality. Note the Noetic: `^3` Negative, because this is recoil and repulsion, the can't-stomach-it response. It is not `^6` Male. Nobody analyzes the kick while it is happening; analysis arrives later at `^6^E|A`, by which time the transient has peaked.

> **A plain safety line, not decoration.** This chapter models the routing of attention. It says nothing about physiology, physical dependence, or withdrawal — mechanisms this book does not describe and is not competent to describe. Nothing here is medical or psychiatric guidance. If stopping something is causing you real distress, that is a matter for a clinician, and no circuit here substitutes for that care.

[[FIGURE 9-C: Back-EMF versus taper time. Two stacked panels, shared time axis. Upper: i(t) falling from 0.60 A_c to zero — an abrupt near-vertical drop and a smooth 240-hour ramp. Lower: corresponding V_kick — a narrow spike reaching 19,200 V_c and a broad plateau at 8 V_c — with the 24 V_c rail dashed across both panels.]]

#### The Flyback Path

CCDL will let you write the abrupt cut. Appendix B §B.3.10 lists exactly one inductive statement, and this is it:

```cas
interrupt coil [dt -> 0];    // legal, compiles clean, almost never correct
```

The four-cent fix on the relay panel is a diode wired backwards across the coil. It does nothing while current flows normally — reverse-biased, blocking, as Section 8.2 describes. The instant the switch opens and the coil's voltage reverses, the diode conducts and offers the collapsing field a loop to circulate in. The current does not stop; it *re-routes* and decays gently. The cognitive equivalent is a **substitute path**, with three load-bearing properties:

1. **It conducts before the switch opens.** A flyback diode installed after the arc is a diode that watched the arc.
2. **It runs downward.** Section 8.1's chain permits descent, `P → C → E → O`, and blocks ascent. The kick appears at `^E`; the diode carries it down into an `^O` act. A substitute one domain *above* the interrupted pattern is not a circuit — `^O × ^P` is invalid notation and invalid engineering for the same reason.
3. **It inherits the pattern's `^7` Rhythm.** Same time of day, same duration, same cadence — keep the `^8^O|E` cue and swap only the `^9^O|E` it lands on.

```cas
board habit_transition {
    input:  cue;
    output: routed_flow;

    node substrate: ^5^C_{F6}|A;         // Female: the accumulated routine
    node trigger:   ^8^O_{F6}|E;         // Above/Cause: the cue that fires it
    node old_path:  ^9_old^O_{F6}|E;     // Below/Effect: the routine as performed
    node new_path:  ^9_new^O_{F6}|E;     // Below/Effect: the substitute routine
    node felt_kick: ^3^E_{F3}|f;         // Negative: visceral recoil at interruption

    inductor coil:  Inductor< path=old_path, L=3200.0 >;   // h*Ohm_c
    resistor r_ctx: Resistor< path=old_path, R=40.0 >;     // tau = L/R = 80 h
    diode  flyback: Diode< ^E -> ^O > [Vf=2.0];            // descent only

    hold until new_path > 0.0;                    // substitute conducts BEFORE the cut
    constraint taper_rate in [0.0, 0.0025];       // A_c/h — the kick budget
    monitor m_kick: felt_kick [threshold=72.0];   // V_c, unnormalised — 3x rail
    on m_kick { alert "V_kick over budget - lengthen the taper"; }

    probe tp1: taper_rate;   // di/dt at the switching node
    probe tp2: old_path;     // i(t) against I_final
    probe tp3: felt_kick;    // V_kick across the coil
    probe tp4: new_path;     // substitute conducting before the cut
}
```

Two lines do the safety work. `hold until` refuses to open the switch until the substitute carries flow. `constraint taper_rate` is the kick budget from the table above, written where a validator enforces it rather than left in the operator's intentions. The monitor threshold is in volts, not activation, so it sits outside `[0, 1]`; Appendix B §B.4 permits that where the guarded quantity is unnormalised.

Note `^9_old` and `^9_new`. Both nodes are the same state — Below/Effect, Operational, F6 Structure, embodied — because that is the honest typing: the substitute is not a nobler act than the one it replaces, only a different landing for the same cue. The `_label` suffix of Appendix B §B.1.2 exists for exactly this case, two instances of one state on one board, and without it the two `node` lines are indistinguishable to a reader and the TP2/TP4 pair below has nothing to name.

[[FIGURE 9-D: Flyback schematic. Drive rail into a switch, then L1 (3,200 h·Ω_c) in series with R (40 Ω_c) to ground; a diode across L1 in reverse-blocking orientation, with a curved arrow showing the circulating decay loop when the switch opens; TP1–TP4 as callout flags.]]

---

### 9.3 Induction Coupling — Transferring Belief Between Minds

Bring two coils near each other and a changing current in the first induces a voltage in the second, with no wire between them:

```
M = k × √(L₁ × L₂)          V₂ = M × (di₁/dt)
```

`k` is the **coupling coefficient**, on [0, 1), set by how much `^7` Rhythm the two minds share. Not agreement, not affection — shared cadence, shared exposure schedule, shared tempo of contact. Chapter 11's transformer (Section 11.5) is this physics with coupling deliberately maximized; here we care about the coupling you did not choose.

| `k` | Condition | Cost of assuming otherwise |
|---|---|---|
| 0.05 | Asynchronous text, no shared cadence | Budgeting transfer that never arrives |
| 0.20 | Shared feed, common daily cadence | Unexplained drift in a population you thought isolated |
| 0.50 | Live co-present group, shared tempo | Under-predicting backlash by 10× |
| 0.90 | Sustained dyad — household, mentor | Transitions leaking into someone you never modelled |
| 1.00 | Ideal limit, no leakage flux | **Not buildable.** `k` is bounded `0 ≤ k < 1` by construction — perfect coupling means no leakage flux, and no real pair has none. Build at ≤ 0.90, the discipline Chapter 24 applies to `β=∞` |

Work it. A speaker with `L₁ = 3,200 h·Ω_c` publicly reverses a position over an afternoon: `Δt = 2.4 h` from `I = 0.60` to zero, so `di₁/dt = 0.25 A_c/h`. A listener in the room has `L₂ = 800 h·Ω_c` on the same question, `k = 0.50`.

```
M  = 0.50 × √(3,200 × 800) = 0.50 × 1,600 = 800 h·Ω_c
V₂ = 800 × 0.25 = 200 V_c
```

Two hundred cognitive volts induced in the listener against their own 24 V_c rail — **8.3× anything they generate on their own account**, from a speaker who never addressed them, through a mechanism with no wire in it.

> **Bench Note — a steady belief induces nothing.** `V₂ = M × di₁/dt`. If `di₁/dt` is zero, `V₂` is zero regardless of how large `L₁` is or how tight the coupling. Someone who has held a conviction quietly for thirty years transmits *nothing at all* by holding it, and an operator expecting transmission from depth is reading the wrong term. The convert is the effective evangelist for no reason to do with sincerity or content: the convert has a large `di/dt`. It is also why an operation at steady state stops recruiting, and why the fix is never "believe harder" — it is to introduce a change, which is what Chapter 14's oscillator manufactures on purpose.

Then polarity. In a real coil the induced current flows in the direction that *opposes* the change producing it; that is not a convention, it is what conservation requires. The cognitive statement is identical: **the induced response in a coupled mind initially opposes the change it detects.**

This is backlash, and it explains a shape that otherwise looks irrational. A movement that shifts fast induces in every coupled mind a counter-flow proportional to `di/dt` — not to the content of the shift, and not to whether the coupled mind agrees with it. Push a norm quickly and you generate opposition in people who would have accepted the same norm arriving slowly. Section 15.4 sets its calendar from a different component — the collective capacitor, `τ = RC` — but the penalty it names for compressing that calendar is this equation: rush the schedule and what you buy is priced in `di/dt`. Section 19.4 runs the same term on purpose, provoking a fast `di/dt` and harvesting the recoil rather than arguing for anything.

[[FIGURE 9-E: Mutual induction, opposing polarity. Coils L₁ (3,200) and L₂ (800) side by side, coupling flux as dashed field lines labelled k = 0.50. In L₁ a downward arrow marked "di₁/dt = 0.25 A_c/h"; in L₂ an induced-current arrow drawn in the OPPOSING direction, labelled "V₂ = 200 V_c, opposing"; caption box: "backlash is proportional to the rate, not the content."]]

---

### Component and Parameter Table

Every value below is a design choice made in this book, not a measurement.

| Parameter | Design range | Failure at other values |
|---|---|---|
| `L`, h·Ω_c | 100 – 20,000 | Under-estimate: taper too short, full kick lands. Over-estimate: years budgeted needlessly |
| `k_d`, Ω_c | 0.5 / 1.0 / 2.0 / 4.0 by domain | Flat across domains: principled transitions under-budgeted 8× |
| `R`, Ω_c | 10 – 90 | Too low: `τ` balloons, `I_final` clips. Too high: fast settling at a shallow ceiling |
| `I_final = V/R`, A_c | 0.05 – 1.00 | Above `I_max` = 1.0 the path clips and spills to competing routes |
| `di/dt`, A_c/h | 0.002 – 0.03 | Recompute the ceiling per coil: `di/dt_max = 3 × V_drive / L`. On the worked coil (`L` = 3,200, 24 V_c) that is 0.0225, so the top of the range is already over budget; at 6.0 the kick is 800× rail |
| `V_kick`, V_c | ≤ 3 × `V_drive` | Above 10× rail the substitute cannot absorb it and recoil dominates |

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Rate overrun** | `di/dt` set by convenience, not by kick budget | Sharp recoil at `^3^E\|f` on day one; transition reverses within a week | Recompute the taper from `V_kick ≤ 3 × V_drive` |
| **Inductance under-estimate** | `L` from `H_practice` alone, `k_d` ignored | Pattern fully present at the planned end date | Re-derive `L = k_d × H_practice`; principled patterns are the usual casualty |
| **No flyback path** | Substitute not conducting before the cut | Full kick at `^3^E_{F3}\|f`; the vacated cadence refills with whatever is nearest | Install the substitute first, same `^7` Rhythm, descending domain; confirm TP4 before TP1 |
| **Low-`R` stall** | `R` cut to "make it easier", so `τ = L/R` rises | No apparent progress; `I_final` computes above `I_max` and clips | Restore `R`. Reduced constraint buys depth, not speed |
| **Unmodelled coupling** | A `k ≥ 0.5` partner was never in the model | Backlash from someone who was never the subject of the operation | Enumerate every `k ≥ 0.2` coupling before setting `di/dt` |
| **Core saturation** | Flow driven far past `I_max` | The substrate stops opposing; the pattern floods and `L` collapses | Cap the rail. A path that stopped resisting was not changed — it stopped regulating |

---

### Test Points

| TP | Node | Reads | Expected |
|---|---|---|---|
| **TP1** | `taper_rate` | `di/dt`, A_c/h | 0.002 – 0.03 for a designed taper. Above 0.05, contacts are being opened, not ramped |
| **TP2** | `old_path` | `i(t)` against `I_final` | Follows `I_final × e^(−t/τ)`; ≈ 0.05 × `I_final` at 3τ. A flat trace means the switch never opened |
| **TP3** | `felt_kick` | `V_kick`, V_c | ≤ 3 × `V_drive` — here, ≤ 72 V_c. Hundreds means TP1 is out of range |
| **TP4** | `new_path` | Substitute flow, A_c | Non-zero **before** TP1 leaves zero. Still zero as TP2 falls is the no-flyback failure, one probe ahead of the damage |

Read them TP4, TP1, TP2, TP3 — confirm the substitute conducts, set the rate, watch the decay, verify the kick stayed in budget. That order is the bring-up procedure.

---

### What This Chapter Established

- **The inductor opposes changes in attention flow, not attention flow itself.** `V_opposition = L × di/dt`; the magnitude Δi never appears on the right.
- **For any pattern there is a rate slow enough to introduce it without meaningful opposition.** No idea is too foreign — only rates are too fast.
- **Inductance rises with domain precedence.** `k_d` runs 0.5 / 1.0 / 2.0 / 4.0 across `^O` / `^E` / `^C` / `^P`, so 800 principled hours carry the same τ as 6,400 operational ones.
- **Constraint makes a transition faster and shallower at once**, because `τ = L/R` and `I_final = V/R` share a denominator. Arrival speed and final depth trade on one component.
- **Back-EMF is a pure inverse in taper time** — 2,400× larger at six minutes than at 240 hours for the same removal. The distress is generated by the rate, not released from storage, and lands as `^3^E_{F3}|f`.
- **The flyback path must conduct before the switch opens**, run downward (`^E -> ^O`, never ascending), and inherit the pattern's `^7` Rhythm. `interrupt coil [dt -> 0];` compiles clean — only `hold until` and the taper constraint stop you writing it.
- **Induction transmits only change.** `V₂ = M × di₁/dt`. A steady conviction induces nothing, and the induced response initially *opposes* the change that produced it: backlash is proportional to rate, not content.

---

### Exercises

*(Answers in Appendix H.)*

**9.1** A behavioural routine (`^O`, `|E`) has 900 rehearsal hours on a path with `R = 30 Ω_c`. Compute `k_d`, `L`, `τ`, 3τ. Repeat treating those 900 hours as a principled commitment (`^P`, `|T`), and say what the ratio between the two 3τ figures means for a schedule.

**9.2** An operator drops `R` from 60 Ω_c to 15 Ω_c on a path with `L = 2,400 h·Ω_c` and `V_drive = 18 V_c`, reasoning that less constraint speeds things up. Compute `τ` and `I_final` before and after, state what actually happened, and name the failure-modes row they landed in.

**9.3** A pattern with `L = 5,000 h·Ω_c` runs at `I = 0.80 A_c` on a 20 V_c rail. Solve for the minimum taper `dt` holding `V_kick ≤ 3 × V_drive`, then the `dt` holding it at 1× the rail. Say whether that second schedule is one you would accept.

**9.4** Explain why the kick is written `^3^E_{F3}|f` and not `^6^E_{F6}|A`. Reference the canonical definition of `^3` Negative, and say what the `^6` Male state does instead and when it arrives.

**9.5 (Design)** Move a practitioner off a `^C|A` method with `H_practice = 2,500 h`, at `R = 40 Ω_c` and `V_drive = 24 V_c`, holding `V_kick ≤ 2 × V_drive`. Give (a) `L`, `τ`, 3τ, `I_final`; (b) the maximum `di/dt` and the taper it implies; (c) a CCDL fragment declaring coil, resistor, flyback diode, the `hold until` and `constraint` guards, and four probes. Check the diode's domain direction before you submit it.

**9.6 (Marquee)** An operator plans a 60-hour taper for themselves, from `I = 0.60 A_c` on a 24 V_c rail, with `L₁ = 3,200 h·Ω_c`, and confirms their own kick is inside the 3× budget. They live with a partner who shares the affected cadence at `k = 0.90`, with `L₂ = 2,000 h·Ω_c`.

a) Compute the operator's `V_kick`, then `M` and the `V₂` induced in the partner, each as a multiple of the same 24 V_c rail.
b) The partner's induced voltage is the smaller of the two, yet the partner is likelier to experience the transition as abrupt. Explain structurally why — the partner never set `di/dt` and has no substitute path installed.
c) Find the taper bringing `V₂` under 0.3× the partner's rail, state what it cost in schedule, then state the one thing this circuit model cannot tell you about the situation.
