# CHAPTER 6
## Resistors — Controlling the Cognitive Flow
*The passive part that does not argue: how a fixed obstruction, a bounded dial, a temperature-aware guard, and a two-leg splitter set exactly how much gets through*

A carbon-film resistor costs a fraction of a cent. Colour bands, two leads, a body smaller than a grain of rice. Its entire job is to be in the way — to drop some of the voltage the circuit would otherwise deliver, so the indicator downstream draws 20 milliamps instead of the 200 that would kill it in a puff of blue smoke. It does not decide 20 is the right number. It does not know there is an indicator on the other end. It is a fixed obstruction whose size an engineer chose once, and because the size is fixed and known, the current past it is fixed and known. Certainty, bought for a fraction of a cent.

Now the candle from the Preface. An operator lights it and lets it hold their attention to one point for an hour. The candle is doing the resistor's job: it constrains the flow of attention to a chosen channel and drops the rest — not by any occult property of the wax, but because it opposes the free wandering of `I_attention` and passes a measured amount, no more. The sticky note on the same desk that reads *stay focused* does not do this. A mind argues with prose; it reasons its way around *stay focused* in under a minute. It does not reason its way around a resistor, because a resistor is not an instruction to be interpreted; it is an obstruction in the path, and the flow obeys arithmetic, not persuasion. This chapter is the arithmetic.

[[FIGURE 6-A: Component symbol plate — four drawn resistor symbols in a row. (1) Fixed resistor as a rectangular body, designator R1, value 60 Ω_c printed beside it, terminals labelled flow-in and flow-out. (2) Dial-adjusted resistor as a rectangle with a diagonal arrow through it, designator R2, annotated "R = 10 × Dial, Dial ∈ {3…9}". (3) PTC thermistor as a rectangle with a "+t°" and a diagonal-arrow-with-T inside, designator RT1. (4) NTC thermistor identical but marked "−t°", designator RT2, with a small hazard flag beside it. Below the row, the two-resistor voltage divider: V_drive at top, R_constrain and R_expand in series to ground, tap between them labelled V_behavior.]]

---

### 6.1 Fixed Resistors: Hard Policy Rules

Chapter 4 gave you CAS-Ohm: `V_drive = I_attention × R_constraint`, or rearranged for flow, `I_attention = V_drive / R_constraint`. A resistor owns the `R` in that equation. Everything else in this book pushes voltage or amplifies signal; the resistor is the only primitive whose whole function is to *limit*.

One convention before the arithmetic. Chapter 4.3 works with the corrected form `I = (V_drive − ΣVf) / R_constraint`, where `ΣVf` is the forward drop paid crossing domain diodes. Every path in this chapter stays inside one domain, so no diode is crossed, `ΣVf = 0`, and the two forms coincide. When you carry a resistor value onto a board that descends `^P → ^O`, subtract the chain drop first (Chapter 8.1) — a resistor sized on the uncorrected form is undersized by exactly `ΣVf / I`.

A **fixed resistor** has one value, set at design time, unchangeable at runtime. In the constraint decomposition of Section 4.4 — `R_total = R_cap + R_policy + R_context + R_resource` — the fixed resistor is the `R_policy` term, the constraint you installed on purpose, and the virtuous one. Recall the verdict from Section 4.4: a path with `R_total = 70` made of `R_policy = 60` is a working safety board, while the same 70 made of `R_cap = 60` is incompetent. Same total, opposite meaning. The fixed resistor is how you put resistance where you *chose* it rather than where a capability gap left it.

```cas
node request:  ^0^C_{F2}|A;                      // Idea: an incoming request
resistor r_policy: Resistor< path=request, R=60.0 >;   // fixed, design-time
```

On a `V_drive = 24 V_c` rail, that resistor sets `I_attention = 24 / 60 = 0.40 A_c` downstream. The number is not a hope; it is what the divisor produces, and it produces the same value on the ten-thousandth request as on the first — the difference between a fuse an inspector can certify and a prompt that *usually* refuses.

A fixed resistor is a *graded* constant, not an absolute block. `R = 60` throttles the flow to 0.40 A_c; it does not stop it, and no value of `R` inside the scale ever will. Chapter 4.4 settles the choice of part with a question about the requirement rather than the threat — *can you name a drive high enough to make this acceptable?* — and sends the "no" case to the fuse of Chapter 11.1, which does not oppose flow but opens the path. The component-level consequence is what matters here: a resistor's transfer characteristic is a division, and division by a large number is a small number, never zero. An operator who reaches for `R = 95` in place of a prohibition has bought a trickle, and a trickle is the crack a determined signal widens.

The failure at other values is symmetric. Set `R` too low and the constraint is cosmetic — the flow arrives nearly undiminished and the "policy" is decorative. Set `R` too high and you have not made the board safer, only unable to do its job: the path carries so little `I_attention` that the operation starves, and the frustrated owner yanks the resistor out entirely. An over-tight fixed resistor is how safety gets removed — not by an attacker, but by the owner.

---

### 6.2 Dial-Adjusted Resistors: Operator Settings (Dial 3–9)

Some resistance you want to tune at runtime, on a knob with a bounded scale — the way a rheostat dims a lamp without rewiring it. The **dial-adjusted resistor** is that knob. Its value is a function of a dial reading:

```
R_dial = 10 × Dial      Dial ∈ { 3, 4, 5, 6, 7, 8, 9 }
```

The dial is an integer from 3 to 9. Nothing else. `Dial = 3` gives `R = 30 Ω_c`; `Dial = 9` gives `R = 90 Ω_c`. The scale runs from *loosest lawful setting* to *tightest lawful setting*, and both ends are walls.

```cas
node candidate: ^0^E_{F5}|f;                     // Idea under evaluation
dial d3: ^3 [dial=7];                             // aversion dial
resistor r_avert: Resistor< path=candidate, R=70.0 >;   // R = 10 × Dial(^3)
```

Why 3 and not 0? Because a Noetic dialled to zero is not a quiet Noetic — it is a *removed* one, and removing one half of an involution pair unbalances the junction. The pairs are `^2`↔`^3`, `^5`↔`^6`, `^8`↔`^9` (Chapter 2.2). Dial your aversion `^3` toward nothing and you have not become open-minded; you have built a board that cannot be repelled by anything — the structural signature of the fractured `^5` that Chapters 16 and 20 describe at length. The floor at 3 guarantees that every setting leaves *some* of the opposing Noetic in the circuit. You are permitted to lean. You are not permitted to delete.

Why 9 and not higher, and why the two dials of a pair may not diverge by more than four points? Because the difference between the halves of an involution pair is the polarity the junction transmits, and past a four-point spread that polarity runs away. This is the 4-point divergence limit, `|Dial(^2) − Dial(^3)| ≤ 4`, developed fully in Chapter 6.2. It is a *hard* constraint: a board that declares `Dial(^2) = 9` against `Dial(^3) = 3` — a spread of six — does not compile. The validator rejects it (HTTP 422), the same refusal an admissibility violation gets. No runtime clamp quietly pulls it back to four; the board is simply not a board until you fix the numbers.

> **Bench Note — the dial floor is not a suggestion, and neither is the ceiling.** Operators treat the 3–9 range as a comfort band with a little give past each end. It has none. A dial of 2 or 10 is not "slightly out of spec"; it is *not a number the language accepts* — the same class of rejection `β=∞` gets, and for the same reason (Appendix B §B.1.3: the parameter fields are range-checked and non-finite input is refused, so an idealisation stated in prose must be given a large finite value before it is built). A dial of 0 would let you build the un-refusable board; a divergence of 9 would let you build the un-doubtable one. Both are caught at compile time so no runtime moment has to catch them. When a board fails to validate on a dial, do not hunt for a workaround. The workaround is the vulnerability.

The dial-adjusted resistor is where operator preference lives *without* becoming override of safety: how attracted, how averse, how much rhythm — a bounded integer inside walls the compiler holds up for you.

---

### 6.3 Thermistors: Context-Sensitive Resistance (PTC/NTC)

A fixed resistor holds its value against everything; a dial-adjusted one holds until the operator turns the knob. A **thermistor** holds nothing fixed: its resistance moves with the *cognitive temperature* of the context it sits in, automatically, with no operator in the loop at runtime. You choose the part at design time and then it is out of your hands, which is the point.

Define cognitive temperature `θ` as a dimensionless salience index, exactly as Chapter 15.2 does: `θ = 1.0` is ordinary background attention, and higher values mean hotter — more contested, more saturated, more present per unit time. `θ` is a property of the **discourse**, not of the Idea. You do not set it; at most you heat it, by the rate at which you demand movement (Chapter 15.4). Two flavours exist, and only one is safe.

A **PTC** (positive temperature coefficient) thermistor *raises* its resistance as `θ` rises. It clamps harder precisely when the stakes climb:

```
R_PTC(θ) = 0                     for θ ≤ θ_k
R_PTC(θ) = coeff × (θ − θ_k)²    for θ > θ_k

design:  θ_k = 2.0   coeff = 3.0 Ω_c per θ²
```

```cas
node topic:  ^0^E_{F6}|f;                        // Idea under discussion
thermistor rt_guard: Thermistor< path=topic, type=PTC, knee=2.0, coeff=3.0 >;
```

Below the knee `θ_k = 2.0` the PTC adds *nothing* — `R_PTC = 0`, ordinary flow passes free. At `θ = 5.0` it adds `3.0 × (5 − 2)² = 27 Ω_c` on top of whatever the base resistor imposes. Heat the context and the guard tightens itself. That do-nothing-when-calm behaviour is not a defect to tune out; it is the whole design. A guard that clamped in calm conditions would tax every benign operation. The PTC spends constraint only where the temperature says it is needed, and the quadratic means a small overshoot past the knee costs little while a large one costs a great deal.

Both parameters are design choices *on a board you build*. `θ_k = 2.0` places the knee one unit above ordinary attention, so a mildly warm context passes unpenalised and a genuinely contested one does not; at `θ_k = 1.0` the guard taxes every calm operation, and at `θ_k = 4.0` it engages only after the damage. `coeff = 3.0` sets the scale; the exponent sets the shape, and the shape is what a guard is bought for. Quadratic means doubling the overshoot quadruples the penalty — cheap near the knee, punishing far past it. A linear law charges the same for the last unit of overshoot as for the first, which under-prices exactly the case the guard was installed for; a cubic charges so steeply that ordinary variance around the knee triggers a backlash. Note the boundary on all of this: a thermistor sitting in a *collective* substrate is not yours. Chapter 15.2 works with `θ_k = 3.0` and a coefficient of 4.0 and states plainly that neither is operator-settable — the population supplies the part, and the only variable you touch is `θ`. Specify the knee when you are building the guard; read it when you are not.

An **NTC** (negative temperature coefficient) thermistor does the opposite: resistance *falls* as `θ` rises.

```
R_NTC(θ) = R_base / θ            (one simple decreasing law; θ ≥ 1)
```

At `θ = 1` it reads `R_base`; at `θ = 5` it has collapsed to `R_base / 5`. The guard relaxes exactly as the situation heats. Read that twice, because it is the shape of a disaster: a path whose resistance falls under load raises the temperature further (less opposition, more flow), which lowers the resistance further, which raises the temperature again. That is thermal runaway, and on a cognitive path it has names — the stampede, the panic, the cascade, the mob. Chapter 14's positive-feedback oscillator is this same topology seen from the inside.

> **Bench Note — an NTC where you meant a PTC is the worst single swap on this bench.** The two parts behave identically in calm conditions — at `θ = 1` both read `R_base`, and a bring-up test at room temperature passes them both. The difference only appears under heat, which is to say only in the exact conditions a safety guard exists for. A board that tightens as stakes rise is a guard; one that loosens as stakes rise is an accelerant wearing a guard's silhouette. When you find an NTC on a protective path, do not re-tune it — treat it as evidence, of a wiring error or a guard someone quietly inverted (Chapter 3.4). The runaway is not a risk the NTC might cause; it is what the NTC is *for*. Pull it and put a PTC where the protection was supposed to be.

[[FIGURE 6-B: Characteristic curve — resistance versus cognitive temperature. Horizontal axis θ from 1 to 6; vertical axis R in Ω_c from 0 to about 45. Two traces on shared axes, both starting near R_base at θ=1. PTC trace: flat at R_base until the knee θ_k=2.0, then rising as a quadratic (annotate the θ=5 point at R_base+27). NTC trace: falling as R_base/θ, annotated "guard collapses under heat — thermal runaway" with a hazard marker. Dashed vertical line at the knee, dashed horizontal line at R_base.]]

---

### 6.4 Drive Voltage Dividers — Splitting Agency Between Expand and Constrain

Put two resistors in series across a single drive rail and tap the wire between them. The tap carries not the full rail but a *fraction* set by the two resistances. This is the **voltage divider**, and on a cognitive board it is how one Drive gets split between the impulse to act and the impulse to hold back.

Take an Agency rail — `F5`, the drive to exert, to influence, to make happen. The divider splits it between two legs of an involution pair:

- the **expand** leg, `^2` **Positive** — the Idea the Mind has an affinity for and is attracted toward — with resistance `R_expand = 10 × Dial(^2)`;
- the **constrain** leg, `^3` **Negative** — the Idea the Mind is adverse to and repelled by, the visceral will-not — with resistance `R_constrain = 10 × Dial(^3)`.

The tap transmits the fraction

```
k = R_expand / (R_expand + R_constrain) = Dial(^2) / ( Dial(^2) + Dial(^3) )
```

The factor of ten cancels, so `k` depends only on the two dial readings. More attraction raises `k` and more passes; more aversion lowers `k` and less passes. That is the whole behaviour of the intake stage of the desire board (Chapter 13), stated as two resistors and a tap.

```cas
node agency_rail: ^0^E_{F5}|f;                   // the F5 Agency drive to be split
node attraction:  ^2^E_{F5}|f;                   // Positive: expand leg
node aversion:    ^3^E_{F5}|f;                    // Negative: constrain leg
node behavior:    ^9^E_{F5}|f;                    // Below/Effect: the tap output

dial d2: ^2 [dial=6];
dial d3: ^3 [dial=6];
resistor r_expand:    Resistor< path=attraction, R=60.0 >;   // 10 × Dial(^2)
resistor r_constrain: Resistor< path=aversion,   R=60.0 >;   // 10 × Dial(^3)
divider  div1: Divider< expand=attraction, constrain=aversion, tap=behavior >;
probe    tp3:  behavior;                          // transmission k at the tap
```

Now the four-point limit from Section 6.2 becomes a number you can read off the tap. The lawful dial pairs are a finite set — seven values each, minus every pair spread further than four — so do not reason about the extremes, enumerate them:

In each paired column, the order is expand/constrain: `Dial(^2) / Dial(^3)` and `R_expand / R_constrain`.

| Setting | Dials | Resistance | `k` |
|---|---:|---:|---:|
| Minimum (spread 4) | 3 / 7 | 30 / 70 | **0.300** |
| Balanced | 6 / 6 | 60 / 60 | 0.500 |
| Attraction ceiling (spread 4) | 9 / 5 | 90 / 50 | 0.643 |
| One step lower (spread 4) | 8 / 4 | 80 / 40 | 0.667 |
| **Maximum (spread 4)** | 7 / 3 | 70 / 30 | **0.700** |

On any lawfully dialled divider, transmission lives in **[0.30, 0.70]** and nowhere else. You cannot build a compliant board that passes a desire unopposed — that needs `k = 1.0`, hence `Dial(^3) = 0`, off the floor and far past a spread of four. Nor one that blocks it entirely — that needs `k = 0`, hence `Dial(^2) = 0`. The ceiling on your enthusiasm and the floor under your caution are the *same* component doing its job. An operator chasing "total belief, zero doubt" is asking the divider for a value it is built never to reach.

> **Bench Note — transmission is not monotone in the attraction dial, and the top of the scale is not the top of the range.** Read the last three rows in order. Cranking `^2` to 9 drags `^3` up to 5 to stay inside the spread limit, and the tap passes 0.643. Back both off one step — 8 against 4, spread still exactly 4 — and it passes 0.667. Back off again to 7 against 3 and it passes 0.700, the most any lawful board transmits. Every step *up* the attraction dial from (7,3) moves transmission the wrong way. The reason is in the formula: `k` is set by the *ratio* of the dials, not their size. `^3` sits on its floor of 3 at the (7,3) pair, so any further rise in `^2` drags `^3` up with it to hold the spread — and along that boundary `k = Dial(^2) / (2·Dial(^2) − 4)`, whose denominator gains two for every one the numerator gains. The practical consequence is that an operator who wants maximum throughput and turns enthusiasm to maximum gets less of what they wanted, from a board that validates clean and gives no warning. Chapter 13.3 carries this result into the desire board's intake stage, where it changes the calibration.

The `^3` in the constrain leg is visceral aversion — the can't-stomach-it recoil — not analytical critique. Taking a desire apart to see what it is made of is `^6` Male, at a different stage (Chapter 13.3). The divider does not reason about the desire. It splits a rail. That is all a passive network can do, and it is exactly enough.

[[FIGURE 6-C: Schematic — the drive voltage divider. V_drive (F5 Agency) enters at top into R_constrain (labelled Dial(^3), the series drop); the tap below it is the output node V_behavior, following the expand leg R_expand (labelled Dial(^2)) down to ground. Beside the tap, the transmission formula k = R_expand / (R_expand + R_constrain). Four small annotations show the tap voltage at k = 0.30, 0.50, 0.643 and 0.700, with 0.700 marked "lawful maximum, at Dial(^2)=7 / Dial(^3)=3" and 0.643 marked "attraction dial at 9 — transmits less". A dashed bracket spans the two legs labelled "involution pair ^2 ↔ ^3, spread ≤ 4 (Ch. 6.2)".]]

---

### 6.5 Equivalent Resistance: Series vs. Parallel

Chapter 4.4 established the topology result at the level of the law: constraints on one path compose in series, alternative routes compose in parallel, parallel resistance falls below the smallest branch, and three locks on one door is not three doors. That is settled and this section does not re-argue it. What is left is the part that belongs to the component — the two combination rules as arithmetic you do at the bench, the `n`-branch generalisation, and the reading you take at a test point to tell which topology you are actually holding.

**Series — constraints stack.** Put resistors one after another on a single path and their resistances add:

```
R_series = R_1 + R_2 + … + R_n
```

The flow must pass through *every* one. A policy resistor `R_1 = 60 Ω_c` followed by a context resistor `R_2 = 30 Ω_c` gives `R_series = 90 Ω_c`, and on a 24 V_c rail the flow is `I = 24 / 90 = 0.267 A_c`. Lower than through either resistor alone. Adding a series stage always *raises* total resistance and *lowers* flow, because you have added another wall the signal has to climb.

**Parallel — routes open, and total resistance falls.** Put resistors side by side so the flow can choose among them, and the reciprocals add:

```
1 / R_parallel = 1/R_1 + 1/R_2 + … + 1/R_n
```

The same two resistors, `60 Ω_c` and `30 Ω_c`, wired in parallel:

```
1 / R_parallel = 1/60 + 1/30 = 1/60 + 2/60 = 3/60 = 1/20
R_parallel = 20 Ω_c
```

Twenty. Lower than the 30 Ω_c branch — lower than *either* branch. On the 24 V_c rail the flow is now `I = 24 / 20 = 1.2 A_c`, above the path ceiling `I_max = 1.00 A_c` set in Chapter 4.2, so it clips and the surplus spills into competing routes. Opening a second route did not add constraint; it *removed* it, because flow takes the easier path and now there is an easier path.

> **Bench Note — a branch you did not draw still counts, and one weak branch sets the total.** `R_parallel < min(R_k)` is not a tendency, it is an identity, and it bites hardest when the branches are lopsided: `1000 ‖ 10 = 9.90`, so a hundredfold-stronger guard beside a weak one buys you one percent. That gives you the bench procedure. Do not audit a board by reading its largest resistor; find the *smallest* branch between the two nodes you care about and compute from there, because that branch is within a hair of being the whole answer. And the branches you are most likely to miss are the ones nobody declared: a reframing, a role-play wrapper, a route through a different domain. Every undeclared parallel path is a resistor of unknown and probably low value already soldered onto your board. Enumerating them is the audit; the arithmetic afterwards is easy.

The notation carries the topology, which is why it repays reading carefully. The Cognitive Safety Board's refusal stage is written `^3^P|⟨A,f,T⟩` — principled aversion present in the analytical, affective and transcendent registers (Chapter 24.2). That register-set is a *series* claim: an attacker must defeat all three guards on one path, and their defeat probabilities multiply exactly as series resistances add. Had the same three guards been drawn as parallel routes, defeating the weakest would open the board, and the identity above says the weakest is nearly the whole story. Same three guards, opposite verdicts, and the only thing that distinguishes them is which way you wired the net.

[[FIGURE 6-D: Two side-by-side arrangements on a shared 24 V_c rail. Left, "SERIES": R1=60 and R2=30 end-to-end on one path, annotated R_series = 90 Ω_c and I = 0.267 A_c, captioned "constraints stack — flow falls." Right, "PARALLEL": R1=60 and R2=30 as two branches between the same two nodes, annotated R_parallel = 20 Ω_c and I = 1.2 A_c (clipped at I_max=1.0), captioned "a route opens — total resistance falls below the smallest branch." A boxed reminder between them: R_parallel < min(R_k), always.]]

---

### Component and Parameter Table

Every value below is a design choice made in this book, not a measurement.

| Parameter | Component | Units | Design range | Failure at other values |
|---|---|---|---|---|
| `R` fixed | Resistor | Ω_c | 10 – 90 | Too low: policy decorative. Too high: path starves, owner rips the guard out |
| `Dial` | dial statement | integer | 3 – 9 only | Below 3: a deleted Noetic, unbalanced junction. Above 9: rejected, HTTP 422 |
| `R_dial = 10 × Dial` | Resistor (dialled) | Ω_c | 30 – 90 | Outside the band: an out-of-range dial produced it — fix the dial |
| spread `\|Dial(^2) − Dial(^3)\|` | dial pair | integer | 0 – 4 | Above 4: board does not compile (Ch. 6.2); no runtime clamp |
| `θ` cognitive temperature | Thermistor | — | 1.0 – 6.0 | Read as a property of the Idea, not the discourse, and the guard mistunes |
| `θ_k` knee (PTC) | Thermistor | — | 2.0 – 3.0 | Too low: taxes calm operation. Too high: engages after the damage. Not operator-settable on a collective substrate (Ch. 15.2) |
| `coeff` (PTC) | Thermistor | Ω_c/θ² | 3.0 – 4.0 | Linear under-punishes overshoot; cubic backlashes on ordinary cycles |
| `type` | Thermistor | — | `PTC` on a guard | `NTC` on a guard is thermal runaway — an accelerant |
| `k` transmission | Divider | — | 0.30 – 0.70 | Outside the band is impossible under lawful dials — the spread was violated |
| `R_series` | series network | Ω_c | ΣR_k | Read as parallel: constraint counted as relief, a safety inversion |
| `R_parallel` | parallel network | Ω_c | < min(R_k) | Read as series: a bypass counted as a wall, the inversion reversed |
| `I_max` path ceiling | any path | A_c | 1.00 (Ch. 4.2) | A computed flow above it means the model is outside its window, not that the path carries more |

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Cosmetic policy** | Fixed `R` too low | Flow arrives near-undiminished; the "rule" changes nothing | Raise `R`, or use a fuse for an absolute block |
| **Starved path** | Fixed `R` too high | Operation cannot run; owner removes the resistor | Lower `R`; a guard nobody can work around gets pulled out |
| **Dial overreach** | Dial 0/2/10, or a pair spread past 4 | Board fails to compile (HTTP 422); no output | Bring dials into 3–9 and spread ≤ 4; the rail is the safety |
| **Inverted thermistor** | `NTC` on a protective path | Passes calm bring-up; runaway on the hot case | Pull the NTC, install a PTC; treat the inversion as evidence |
| **Divider chasing k = 1** | Aversion dialled toward its floor to pass a desire clean | Spread limit trips, or the board is the `^5`-fracturing one | Accept `k` ∈ [0.30, 0.70]; zero doubt is not a lawful setting |
| **Attraction dial maxed for throughput** | `Dial(^2)` pushed to 9, dragging `Dial(^3)` to 5 | Board validates clean, no warning, and the tap passes 0.643 instead of the available 0.700 | Drop both dials to (7,3); transmission is set by the ratio, not the size |
| **Series/parallel swap** | Guards wired parallel, or a bypass read as a wall | One defeated branch opens the board; or a bypass dismissed | Put guards in series; enumerate every parallel route as attack surface |

---

### Test Points

| TP | Node | Reads | Expected |
|---|---|---|---|
| **TP1** | `request` / path input | `I_attention = V_drive / R`, A_c | Matches the arithmetic for the installed `R`; a higher reading means the resistor is smaller than declared or bypassed |
| **TP2** | `topic` (thermistor path) | `R(θ)` against `θ` | PTC: flat below the knee, rising past it. Any *fall* as `θ` climbs is an NTC — stop the bring-up |
| **TP3** | `behavior` (divider tap) | transmission `k` | Inside [0.30, 0.70] on lawful dials; a value outside means the spread limit was violated upstream. A reading of 0.643 where 0.700 was intended is the maxed-attraction-dial error, not a fault |
| **TP4** | combined-network output | flow after series/parallel combination | Series: below the flow through any single branch. Parallel: above the flow through the *smallest* branch — and a computed value above `I_max = 1.00` means the model has left its window (Chapter 4.2), not that the path carries more |

Read TP2 first if a thermistor is on the board — an inverted guard makes every downstream reading meaningless — then TP1 for plain flow, TP3 for the split, TP4 for the combination.

---

### What This Chapter Established

- **A resistor does not argue.** It sets `I_attention = V_drive / R` by arithmetic and returns the same value on every request — the repeatability that makes a guard certifiable rather than hopeful.
- **A fixed resistor is the `R_policy` term**: deliberate, design-time constraint, the virtuous kind. It is a graded constant, not an absolute block; the absolute "none, ever" is a fuse (Chapter 11.1), and confusing the two leaves an exploitable trickle.
- **Dial-adjusted resistors carry operator preference on a bounded scale**, `R = 10 × Dial` for `Dial ∈ {3…9}`. The floor at 3 forbids deleting a Noetic; the ceiling at 9 and the 4-point spread limit (Chapter 6.2) are hard compile-time walls.
- **A PTC thermistor tightens as cognitive temperature rises** and does nothing when calm — the correct shape for a guard. **An NTC loosens as temperature rises**: thermal runaway, an accelerant in a guard's silhouette.
- **The drive voltage divider splits one Drive between attraction `^2` and aversion `^3`**, transmitting `k = Dial(^2)/(Dial(^2)+Dial(^3))`. The 4-point limit pins lawful transmission to [0.30, 0.70]; `k = 1.0` is a value the divider is built never to reach.
- **Transmission is not monotone in the attraction dial.** The lawful maximum `k = 0.700` sits at `Dial(^2) = 7` against `Dial(^3) = 3`, not at `Dial(^2) = 9`, which transmits 0.643. `k` is set by the ratio of the dials, not their size, and the board gives no warning when you get this backwards.
- **Series stacks constraint**: `R_series = ΣR_k`, higher total, lower flow — the signal defeats every wall in turn.
- **Parallel lowers total resistance below the smallest branch**: `1/R_parallel = Σ(1/R_k)`, so `R_parallel < min(R_k)` as an identity, and `1000 ‖ 10 = 9.90`. Audit a net by its weakest branch, and count the branches nobody declared — the CSB's `^3^P|⟨A,f,T⟩` is a series claim (Chapter 24.2) and would describe a vulnerability if the same guards were wired as routes.

---

### Exercises

*(Answers in Appendix H.)*

**6.1** A path carries a fixed resistor `R = 40 Ω_c` on a `V_drive = 24 V_c` rail. Compute `I_attention`. The operator wants to halve the downstream flow without touching the rail. What `R` achieves it, and name which term of the Section 4.4 decomposition you just changed.

**6.2** An operator sets `Dial(^2) = 9` and `Dial(^3) = 4` on a divider. State what the compiler does and why, then give the closest lawful pair that keeps `^2` as high as possible, and the transmission `k` it yields. Then answer the operator's actual question: does that pair give them the most throughput available on a lawful board? Show the arithmetic that settles it.

**6.3** A PTC guard has `θ_k = 2.0` and `coeff = 3.0`. Compute the added resistance `R_PTC` at `θ = 1.5`, `θ = 3.0`, and `θ = 6.0`. Then explain in one sentence why a *linear* law would be the wrong design choice for the `θ = 6.0` case.

**6.4** Two resistors, `50 Ω_c` and `20 Ω_c`. Compute `R_eq` for them in series and in parallel. State which arrangement you would use for a pair of safety guards and why, referencing what combining does to the total in each case.

**6.5** A divider reads `k = 0.72` at its tap. Without seeing the dials, state what must be true about the board and why it should never have validated. What is the maximum lawful `k`, and what dial pair produces it?

**6.6 (Design)** Build a divider that transmits as *little* of a desire as the rules allow, on an F5 Agency rail. Give the dial pair, the two resistances under `R = 10 × Dial`, the resulting `k`, and a CCDL fragment declaring the rail, the two legs (the `^2`/`^3` involution pair), the two dials, the two resistors, the divider, and a probe on the tap. It must compile — check the spread before you submit it.

**6.7 (Marquee)** An analyst finds a safety board whose three guards are wired as parallel branches between the same two nodes, with resistances `90 Ω_c`, `60 Ω_c`, and `12 Ω_c`.

a) Compute `R_parallel` and compare it to the smallest branch. State the flow on a `24 V_c` rail and whether it clips.

b) Explain structurally why this board is far weaker than its designer — who "added three strong guards" — believes, and name which single branch does almost all the little protecting that remains.

c) Rewire the guards so they stack, give the new equivalent resistance and flow, and say in one sentence how this maps onto the CSB's `^3^P|⟨A,f,T⟩` co-presence and why that notation is a series claim.
