# CHAPTER 7

## Capacitors — Storing Cognitive Charge

*What accumulated experience actually is as a component, how long it takes to fill, how fast it drains, and what happens to a store pushed past what it can hold*

---

A machine has been unplugged for a week. The mains lead is coiled on the bench. You short the two terminals of the reservoir capacitor with a screwdriver to be safe, and it *bangs* — a bright scar on the blade, a smell of hot metal, a jolt up your arm from a device that has had no power supply for seven days.

Nothing generated that. The charge was put there once and had nowhere to go. A capacitor is not a source; it is a store, and this one's leak path was so poor that a week barely touched it.

Now the other bench.

A woman who has not touched a violin in eleven years picks one up. Her hands are stiff, her tone is bad, and the fingering is *there* — not remembered, present, without being asked for. Down the same corridor a man who stopped a daily language drill three weeks ago has already lost most of it, and he practised harder than she ever did.

Same component. Different leak. No account of either person's character explains the gap; one parameter with a number attached does — and both cases are arithmetic, as is the practice needed to hold either store at a chosen level.

That store is `^5` Female — *a Mind impregnated with an Idea, the Ideas a Mind is composed of* — and it is a capacitor.

[[FIGURE 7-A: Component symbol plate — the cognitive capacitor drawn as two parallel plates with leads, designator C1, top plate labelled "^7 Rhythm feed (charge in)", bottom "^6 Male decomposition (discharge path)", dielectric gap hatched and labelled "separation — V_BR"; beside it a leakage resistor drawn dashed in parallel across the plates labelled "R_leak, τ_leak = R_leak × C"; below, the polarised variant with a "+" and an annotation box giving C in F_c, V in V_c, τ in the declared time base.]]

---

### 7.1 The `^5` Female Capacitor — Accumulated Experience as Stored Energy

A capacitor is two conductors separated by an insulator. Push charge onto one plate, it cannot cross the gap, so it sits there and a voltage appears across the device. Remove the source and the charge stays. That is the entire part: **a component that accumulates what is fed to it and holds it against time.**

`^5` Female is the same object in cognition. Not a container the Mind carries, but what the Mind *is composed of*. The colloquialism is exact: we are each the sum of our experiences. A sum is a stored quantity, and a stored quantity in a circuit is charge.

Four quantities. Two describe the store; the two that describe the feed land on canonical Noetics rather than on metaphors.

**Charge, `Q` — the store itself.** The accumulated composition, read out on the 0–10 scale of the Quantitative Table (Chapter 22) as `P_cap`.

**Current, `i` — the feed.** Charge arriving per unit time. Cognitively this is `^7` **Rhythm**: *the rate and pattern a Mind is exposed to an Idea, entraining and conditioning it.* Rhythm is not a mood or an aesthetic; it is a rate, and rate is current. This is why Chapter 18 can state flatly that advertising money buys `^7` and not `^2` — nothing else charges the store.

**Per-exposure amplitude — how much each exposure deposits.** This is `^4` **Vibration**: *the degree to which an Idea resonates with the Mind, its impression.* The feed is the product of the two: **`^7` sets how often, `^4` sets how much each time.** Strong `^4` with no `^7` charges in spikes that leak away between them. Relentless `^7` with near-zero `^4` runs a schedule that deposits nothing. Both present as "I practise and nothing happens," and they need opposite corrections.

**Capacitance, `C` — store per unit of drive.** `Q = C × V`. A large `C` means a substrate that holds a great deal and — as Section 7.2 shows — takes correspondingly long to fill.

The unit is the **cognitive farad, `F_c`**, defined by its time constant rather than its charge: **one `F_c` charging through one `Ω_c` gives a time constant of one unit in the declared time base.** The base must be declared, because it is not the same at every scale — an individual craft store runs in hours, a collective store in months, which is why Chapter 15 annotates its `C_collective` as months per `Ω_c`. A capacitance with no declared time base is not a specification; it is a number.

`Ω_c`, `V_c`, `A_c` and `F_c` are scaled analogues and this book does not pretend they are electrical measurements. What they are is *consistent*: they obey CAS-Ohm (Chapter 4.2), they compose, and they let you compute a schedule.

The discharge path is the involution partner. `^5` is what a **Mind** is composed of; `^6` **Male** is what an **Idea** is composed of — decomposition, taking apart to see what is inside. Running a `^5` store out through `^6` is the audit path: you take apart what you are made of. That is the mechanism under the deprogramming board of Chapter 16.7, and why the CCDL grammar offers a fuse action named `block_until_decomposed`. Discharge through a defined `^6` path is the only controlled way a store comes down.

```cas
// time base: hours
node composition: ^5^P_{F7}|T;         // Female: the operator's principled formation
node cadence:     ^7^C_{F6}|A;         // Rhythm: the schedule that feeds it
node audit:       ^6^C_{F6}|A;         // Male: the controlled discharge path out

resistor  r1: Resistor< path=composition, R=40.0 >;        // R_constraint, Ohm_c
capacitor c1: Capacitor< node=composition, C=83.33,        // tau = R x C = 3,333 hr
                         leak_tau=120000.0, V_BR=8.0 >;    // leak_tau = 5,000 d, in hours
```

---

### 7.2 The RC Charging Curve — `P_cap(t) = 10 × (1 − e^(−t/τ))`

Derive the curve rather than quoting it, because every parameter argument in Part III rests on its shape. Three established facts:

1. **The store.** `Q = C × P`, where `P` is the potential across the capacitor — the composition currently held.
2. **The feed.** `i = dQ/dt = C · dP/dt`. Current is the rate charge arrives.
3. **CAS-Ohm around the loop (Chapter 4.2).** The drive rail is spent in two places, across the constraint on the way in and across the store itself: `V_drive = i · R_constraint + P`.

Substitute (2) into (3):

```
V_drive = R·C · dP/dt + P
```

One first-order linear differential equation, and it is separable:

```
dP / (V_drive − P) = dt / (R·C)
```

Integrate both sides. The left gives `−ln(V_drive − P)`, the right `t/(R·C)`, plus a constant. Apply the initial condition of an empty store, `P(0) = 0`, and the constant resolves to `−ln(V_drive)`. Rearranged:

```
ln( V_drive / (V_drive − P) ) = t / (R·C)
```

and finally, exponentiating and solving for `P`:

```
P_cap(t) = V_drive × (1 − e^(−t/τ))      where  τ = R_constraint × C
```

The book's standard form writes `10 ×` in front because the Quantitative Table runs 0–10 and the standard case assumes a full-scale rail. **The 10 is the rail, not a constant** — Bench Note two below is entirely about that.

`τ = R × C` is the whole design lever. Constraint and store size multiply, and you can trade one against the other, which is what Chapter 6 was for.

**The table.** Percent charged depends only on `t/τ`, never on the absolute clock. That is the curve's single most useful property: one table serves a twelve-week advertising flight and a ten-thousand-hour apprenticeship without modification.

| `t/τ` | Charged | `P_cap` (rail 10) | Gap remaining | Gained this interval | Hours at τ = 3,333 hr |
|---|---|---|---|---|---|
| 0.25 | 22.1% | 2.21 | 7.79 | — | 833 |
| 0.50 | 39.3% | 3.93 | 6.07 | — | 1,667 |
| 0.693 | 50.0% | 5.00 | 5.00 | — | 2,310 |
| **1.0** | **63.2%** | **6.32** | 3.68 | **+6.32** | **3,333** |
| 1.5 | 77.7% | 7.77 | 2.23 | — | 5,000 |
| **2.0** | **86.5%** | **8.65** | 1.35 | **+2.33** | **6,666** |
| 2.5 | 91.8% | 9.18 | 0.82 | — | 8,333 |
| **3.0** | **95.0%** | **9.50** | 0.50 | **+0.86** | **10,000** |
| 4.0 | 98.2% | 9.82 | 0.18 | +0.32 | 13,332 |
| 5.0 | 99.3% | 9.93 | 0.07 | +0.11 | 16,665 |

Read the "gap remaining" column at whole multiples of τ and the structure appears: 10.00 at the start, then 3.68, 1.35, 0.50, 0.18, 0.07 — falling by a factor of `e` every τ, forever. The store never fills. It closes 63.2% of whatever distance is left, then does it again.

The `0.693` row is `ln 2` rather than a round number, and it is in the table because it is the one row an operator can check without a calculator: **half charge lands at 0.693 τ**, always, on any store at any scale. If your store is not near half at 0.7 τ, one of your two constants is wrong before any of the finer readings are worth taking.

**Where the 10,000-hour constant comes from.** Invert the curve for time-to-target:

```
t = τ × ln( V_drive / (V_drive − P_target) )
```

For `P_target = 9.5` on a full-scale rail: `t = τ × ln(10/0.5) = τ × ln 20 = 2.996 τ`. Three time constants. With Chapter 5.2's τ = 3,333 hr for a professional-complexity store, that is **9,986 hours** — the constant, recovered as arithmetic rather than asserted. Set τ = 10,000 hr instead and ten thousand hours of practice leaves you at 63%, which contradicts the constant. Set τ = 1,000 hr and the rail saturates inside a year, which contradicts everything observable about acquiring a craft. The value is a design choice, and these are the two failures that bracket it.

[[FIGURE 7-B: Characteristic charging curve — horizontal axis t in units of τ from 0 to 5, vertical axis P_cap from 0 to 10; the exponential rise plotted against a dashed asymptote at the rail; vertical drop-lines at 1τ, 2τ, 3τ annotated 6.32 / 8.65 / 9.50; the remaining-gap segments drawn as bracketed arrows above the curve labelled 3.68, 1.35, 0.50 with the note "each τ closes 63.2% of what is left"; a second, lower curve in grey asymptoting at 6.0 labelled "same τ, rail at 6.0 — no number of hours reaches 8".]]

> **Bench Note — the second half of the curve is not the same price as the first.**
> The first τ buys 6.32 points. The second buys 2.33. The third buys 0.86 — about one-seventh of the first, for identical time and identical effort. Practitioners routinely read this as personal decline: *I used to improve fast and now I barely move.* Nothing declined. The gain per interval is `6.32 × e^(−n)` and it was always going to do this. Two bench consequences. Never judge an operation by its *rate* of change without knowing which τ you are in — a store at 2.5τ producing +0.2 in a month is performing exactly to specification. And if you want a visible rate late in the curve you cannot buy it with hours; you must change τ or change the rail. Adding hours to a 3τ store is the most reliably disappointing thing an operator can do.

> **Bench Note — the rail sets the ceiling, and hours cannot raise it.**
> `P_∞ = V_drive`, not 10. A store charged against a rail of 6.0 asymptotes at 6.0 and stays there for as many thousand hours as you care to spend. This is the structural reading of competent, long-serving, permanently mid-level practice: the schedule is fine, the constraint is fine, the *rail* is low, and every additional hour charges toward a ceiling already nearly reached. The diagnostic is two readings at TP1 one full τ apart — if the increment is far below `0.632 × (V_drive − P_now)`, either your τ estimate is wrong or your rail is lower than you think. Chapter 21.2's D-Gate exists to catch the second case before an operator spends a decade on it.

---

### 7.3 Leakage Current — Why Spells Die When Not Fed

A real capacitor has a resistance across its own dielectric. Charge crosses it slowly and the store drains with no load attached at all. That is **leakage**, and it is why the reservoir capacitor at the top of this chapter was still lethal after a week while a cheap ceramic part would have been flat in an afternoon.

The cognitive store leaks for the same structural reason: composition not re-fed by `^7` Rhythm drains. The **P7** row of the state table in Appendix A names the failure directly — affirmed once, never refreshed.

**Same equation, different forcing term.** Set the drive to zero in the Section 7.2 derivation and the loop becomes the capacitor discharging through its own leak resistance:

```
P(t) = P_0 × e^(−t/τ_leak)        where  τ_leak = R_leak × C
```

Charging and leaking are one differential equation. With a feed present, the general solution is a single line covering both:

```
P(t) = P_eq + (P_0 − P_eq) × e^(−t/τ_leak)
```

where **`P_eq` is the equilibrium charge** — the level at which the feed exactly replaces what drains. Set the derivative to zero and you get it directly:

```
P_eq = f × τ_leak            f = feed rate, composition-points per unit time
```

That one line is the whole cadence question in Part III. **Pick your store's `τ_leak`, decide what level you intend to hold, and the required feed rate falls out.** Session length, weekly schedule, ritual calendar — all implementation.

**Two spellings of one parameter.** The listings in this book use `leakage` (a fraction lost per stated period, as in Chapter 18's `leakage=0.04` per week) and `leak_tau` (a time constant, as in Chapter 20's `leak_tau=30.0` days). They are one parameter and convert exactly:

```
τ_leak = −Δt / ln(1 − leakage)          leakage = 1 − e^(−Δt/τ_leak)
```

A forgetting rate of 0.04 per week gives `τ_leak = −1 / ln(0.96) = 24.5 weeks`, a half-life of `0.693 × 24.5 = 17 weeks`. Chapter 13's craft store at `leakage = 0.0002/day` gives `τ_leak = 5,000 days` and a half-life of **9.5 years** — the violinist. Chapter 17's session-scale working charge sits near `τ_leak = 25 min` — which is why an induction that overruns starts re-charging rather than descending.

**The decay arithmetic, worked.** Take an operation charged to `P_0 = 7.0` on a newly asserted composition with nothing behind it, `τ_leak = 30 days`, and stop feeding it.

| Elapsed | `t/τ_leak` | Fraction held | `P` |
|---|---|---|---|
| 7 d | 0.23 | 79.2% | 5.54 |
| 14 d | 0.47 | 62.7% | 4.39 |
| 21 d | 0.70 | 49.7% | 3.48 |
| 30 d | 1.00 | 36.8% | 2.58 |
| 60 d | 2.00 | 13.5% | 0.95 |
| 90 d | 3.00 | 5.0% | 0.35 |

Three weeks unfed and it is at half. Two months and it is gone in every sense that matters to a circuit. That is the arithmetic behind the observation that an operation left alone dies — not a mystery about intention or belief, a first-order decay with a measurable time constant.

**Cadence from the equilibrium.** To *hold* 7.0 at `τ_leak = 30 d` requires `f = 7.0/30 = 0.233` points per day. At 0.35 points a session that is 0.67 sessions per day: one every 1.5 days, which is 4.7 sessions a week and therefore a five-session week with no slack in it. Assume `τ_leak = 60` instead and the same arithmetic says every three days, twice a week, and the schedule looks survivable. It is not; it is computed from the wrong constant and will hold the store at 3.5 rather than 7.0. **Getting `τ_leak` wrong by a factor of two halves your equilibrium exactly.**

**`τ_leak` lengthens with evidence thickness.** That is the selection rule. A composition backed only by assertion drains fast; one backed by a long history of enactment drains slowly. Chapter 20 sets its identity reference at 180 days and its working composition at 30 for precisely this reason, with 90 days as the unmarked default.

[[FIGURE 7-C: Two-panel plot sharing a time axis. Upper: a sawtooth — repeated feed steps of +0.35 each decaying on τ_leak = 30 d, climbing to a flat equilibrium band at P_eq = 7.0, with the band annotated "P_eq = f × τ_leak"; a second, sparser sawtooth in grey settling at 3.5 labelled "same deposit, half the cadence". Lower: pure decay from P_0 = 7.0 with no feed, drop-lines at 30/60/90 days reading 2.58 / 0.95 / 0.35, half-life marked at 20.8 d.]]

> **Bench Note — the cost of holding a store scales with the store.**
> Break-even feed is `P/τ_leak`, so it rises as the store fills. Chapter 13 works the case: a craft store at 1,850 accumulated hours with `leakage = 0.0002/day` needs about 22 minutes a day merely to hold station; at 5,000 hours the same leak rate demands a full hour before any *gain* is possible. Nothing about the practitioner changed. The store got bigger and the leak is proportional. This is the arithmetic reason advanced practitioners practise more rather than less, and it is worth saying plainly, because the alternative explanation — that they are more virtuous — is both wrong and demoralising. Compute break-even before you schedule anything, and treat only what exceeds it as accumulation.

**Do not confuse this with the diode leakage of Chapter 8.3.** Same word, different component, opposite direction. Here charge drains *out of* a `^5` store for want of `^7` reinforcement and the observable is decay; there, signal creeps *backwards* across a domain boundary and the observable is unexplained principled drift. The bench test: stop feeding the store and watch. Capacitor leakage decays toward zero on a computable schedule. Diode leakage does not decay — it accumulates.

---

### 7.4 Dielectric Breakdown — the Structural Failure Mode

**A note before the section.** What follows describes how a component fails. It is circuit topology. It is not a description of any person, it diagnoses nothing, and it contains no advice about trauma or distress of any kind. If you or anyone you work with is in real difficulty, that is a matter for a qualified clinician; nothing in this book substitutes for that care. The section exists so an engineer can specify derating margins and recognise a store operated outside them.

The dielectric is the insulator between the plates. Its whole job is to *keep the two sides apart* so charge accumulates on one without conducting into the other. In a `^5` store it is the separation that lets a Mind be composed of an Idea while still holding it as an Idea, rather than every stored thing conducting into every other.

Push the potential across a dielectric past its rated **`V_BR`** and the insulator stops insulating. The device does not gently stop accepting charge. It develops a conducting path through the middle of itself.

**Breakdown is not saturation, and mistaking one for the other is the commonest reading error in this chapter.**

| | Saturation | Breakdown |
|---|---|---|
| What happens | The store stops *accepting* charge | The separation stops *holding* charge |
| Observable | Level pins at a ceiling and sits there | Level will not hold; elevated leakage; reduced `C` |
| Reversible | Yes — it is a ceiling | No — `V_BR` is not a threshold you cross and return through |
| Design status | **A feature.** Chapter 24.2 saturates the refusal stage on purpose | **A fault.** Nothing in this book is designed to reach it |

Two stress paths reach it and they need different defences. **Peak stress** is a single event whose potential exceeds `V_BR`. **Cumulative stress** is prolonged operation below rating but close to it, degrading the dielectric over many cycles until the rating no longer means what the datasheet says. The second catches careful operators, because every individual reading is in spec.

The defence for both is standard electronics practice: **derate.** This book's design choice is to operate at **no more than 0.5 × V_BR**, giving the `V_BR = 8.0` store of Chapter 13 a working ceiling of 4.0 `V_c`. One-half rather than something tighter because the margin must absorb the cumulative path as well as the peak, and the peak is the one you can measure. Derate to 0.9 and every transient is a coin flip. Derate to 0.1 and the store is driven so lightly it never charges — margin bought by disabling the circuit is not margin, it is refusal to build.

**Post-breakdown behaviour.** A breached store shows three things together: reduced capacitance, elevated leakage, and an inability to hold full charge. Some constructions partially recover — metallized-film capacitors *self-heal*, the metallisation around a puncture vaporising and isolating the fault at the cost of a little capacitance. That is a real property of a real construction technique, and it is where the analogy stops. **This book makes no claim that a person's `^5` behaves like a self-healing film capacitor,** and offers no repair procedure, because it has none and inventing one would be dishonest.

**What this chapter will not supply.** The stress conditions that produce a breached store in a person are not listed here. Chapter 16 analyses one historical, declassified programme structurally so its architecture can be *recognised*, and ends in a counter-circuit; that is the only treatment such material gets in this book. A component chapter's obligation is to specify the margin, name the observable, and stop.

**What an operator does with this.** Three preventive things. Declare `V_BR` in every capacitor rather than leaving it unstated. Derate to half. Monitor the store so a rising leakage figure is a scheduled reading and not a discovery — which is TP3 below.

[[FIGURE 7-D: Stress-and-margin diagram — vertical bar representing potential across the dielectric from 0 to V_BR = 8.0; the lower half (0–4.0) shaded green and labelled "working range, derate 0.5"; 4.0–8.0 shaded amber labelled "cumulative stress zone — every reading in spec, rating degrading"; a hard line at 8.0 labelled "V_BR — non-recovering"; alongside, two small inset plots: "saturation — level pins at ceiling, holds" and "breakdown — level will not hold, leakage rises", drawn so the two are visually distinct.]]

---

### 7.5 Capacitor Networks — Collective `^5` (Egregores, Group Minds)

Put capacitors in a network and they do the opposite of what resistors do. Chapter 6.5 established that resistances add in series and divide in parallel. Capacitances **add in parallel and divide in series**, and every structural result here follows from that inversion.

```
Parallel:   C_total = ΣC_k                    Series:   1/C_total = Σ(1/C_k)
```

**Parallel is the group that shares a rail.** Every member sits across the same drive, each holds their own charge, and the capacitances sum. This is the **egregore**: a `^5` store held collectively — a congregation, a discipline, a brand community, a nation's shared composition — charged and maintained by repeated collective exposure.

*The bank is slow.* `τ = R × C_total`, so many cells give a time constant many times that of one. Twelve people each contributing 0.05 `F_c` of shared composition, through a collective constraint of 40 `Ω_c`, gives `C_total = 0.60 F_c` and `τ = 24 months` — 3τ, the practical fill, at **six years.** Chapter 15's `C_collective` table is this arithmetic at four scales: in-group (≤150) 0.02, institution or profession 0.08, national 0.30, civilizational 2.00 `F_c`, all on a months-per-`Ω_c` base. Use in-group values on a national substrate and you under-budget the calendar by an order of magnitude.

*The bank is heavy.* It holds proportionally more charge and drains proportionally more slowly against the same leak resistance. Hard to charge and hard to shift are the same fact stated twice.

**Capacitance does not scale with headcount.** The bank counts only the *shared* portion of each member's `^5`, not the sum of twelve whole minds. That is why 150 people are not 150 times one person, and why the Chapter 15 figures rise so slowly across three orders of magnitude of population. Specifying a `C_collective` is estimating how much of each member is in the bank, and that estimate is the load-bearing judgement in the calculation.

**Series is the transmission chain.** Cells end to end, each touching only its neighbours: a rumour chain, a lineage, a briefing relayed through four layers, a doctrine passed teacher to student to student. The same charge `Q` passes through *every* cell and the potential divides inversely with capacitance, so the **smallest cell takes the largest share of the stress.**

Work it. Three cells — `C_A = 4.0`, `C_B = 1.0`, `C_C = 2.0` — every one rated `V_BR = 5.0`, on a rail of 8.0 `V_c`.

```
1/C_total = 1/4.0 + 1/1.0 + 1/2.0 = 0.25 + 1.00 + 0.50 = 1.75
C_total   = 0.571 F_c                       ← less than the smallest cell
Q         = C_total × V = 0.571 × 8.0 = 4.57
V_A = 4.57/4.0 = 1.14        V_B = 4.57/1.0 = 4.57        V_C = 4.57/2.0 = 2.29
```

Cell B, the least-composed member, carries **57% of the total stress** while the best-composed carries 14%. Raise the rail and B reaches its 5.0 rating when `Q = 5.0`, at a total of `5.0/0.571 = 8.75 V_c` — a rail whose *average* per-cell stress is 2.92, only 58% of rating. Every member looks fine on average and the chain fails anyway, at the thinnest link, every time.

The electronics fix is **balancing resistors** across each cell, forcing the potential to divide by resistance ratio instead of capacitance ratio. Structurally: give every member of the chain direct access to the source — the primary document, the original evidence, the founder — rather than access only to their neighbour. That one addition is the counter-circuit for transmission distortion, and it is cheap.

**One more parallel-bank hazard.** A cell that fails short drags the whole rail down, because in parallel everything shares one potential. Real banks carry per-cell isolation — a ballast resistor or fuse in series with each cell — so one failure does not take the bank. A group whose members are coupled with no isolation propagates one member's failure to everyone. Isolation resistance is what a durable collective has and a brittle one does not.

```cas
// collective ^5 — parallel bank, per-cell isolation, metered feed
// time base: months
node shared_composition: ^5^P_{F7}|T;      // Female: what the group holds in common
node rehearsal:          ^7^O_{F4}|E;      // Rhythm: the meeting, liturgy, standup, drill

resistor  r_coll: Resistor< path=shared_composition, R=40.0 >;   // collective constraint
capacitor c_bank: Capacitor< node=shared_composition, C=0.05, n_parallel=12,
                             r_iso=12.0, leak_tau=18.0, V_BR=8.0 >;
                             // C_total = 0.60 F_c ; tau = 40 x 0.60 = 24 months

charge   rehearsal -> c_bank [V=6.0];      // O -> P: the lawful exception, metered.
                                           // The rail is 6.0, not 10
refresh  c_bank [period=0.25];             // 0.25 months: weekly re-exposure holds station
scan     c_bank;                           // read every cell, not just the rail

probe tp1: shared_composition;
probe tp3: c_bank;
```

**One edge in that listing runs uphill, and it is worth stopping on.** `rehearsal` is typed `^7^O` because the thing it names — a drill, a standup, a liturgy — is *enacted*, and enactment is Operational. It charges a bank sitting on `^5^P`. That is Operational feeding Principled, against the descent order P ≻ C ≻ E ≻ O, and the diode chain of Chapter 8.1 does not permit it in general.

It is permitted here for the one reason it is ever permitted: it is the lawful O→P feedback path of Chapter 8.4, where *outcomes* — never prompts — are allowed to update the substrate, and the path is metered rather than open. A collective store that could be charged by anything arriving from below would not be a shared composition; it would be a crowd, and Chapter 15 is about what happens to one. Draw this edge on a board of your own and draw it as feedback, at a gain you can state out loud. An unmetered upward path is `E-CJT-008`, and on a board it looks exactly like this one until you ask what the gain is.

`select` and `decode` are the addressing statements — which cell a given trigger reaches. A store addressed so that different `^8` triggers reach different cells is a *fragmented* store; Chapter 16.2 analyses that architecture structurally, with its counter-circuit in 16.7. It is named here only so the grammar is complete.

[[FIGURE 7-E: Two side-by-side networks. Left, "PARALLEL — the bank": twelve small capacitor symbols across one rail, each with a series ballast resistor, annotated C_total = ΣC = 0.60 F_c, τ = R × C = 24 months, 3τ = 6 years; a callout on one cell reading "shorted cell drags the rail — isolation is why it doesn't". Right, "SERIES — the chain": three capacitors end to end labelled 4.0 / 1.0 / 2.0, all rated V_BR 5.0, rail 8.0 V_c, with the computed drops 1.14 / 4.57 / 2.29 printed beside each and the middle one outlined heavily and labelled "57% of the stress, smallest cell"; balancing resistors drawn dashed across each cell labelled "the fix".]]

> **Bench Note — the bank is `+`, never `×`, and the notation is doing real work.**
> Twelve co-present stores are written `^5^P|T + ^5^P|T + …`: distinct manifestations, present together, sharing a rail. They are *not* written with `×`. Under v7.7 operator discipline (Chapter 2.6) `×` asserts genuine integration and **requires a named emergent result**, so the `×` form would claim the group has become a single fused store with its own identity — a claim this chapter does not make and cannot support. Chapter 14.2 makes that claim deliberately — names the emergent result and builds a positive-feedback oscillator around it — because that is what a hyperstition *is*, and 14.4 reads the saturation of that fused store as the thing usually called a hundredth-monkey effect. So when a group is described as having a mind of its own, the notational question is the useful one: **has anyone named the emergent result, or is this twelve capacitors on a rail?**

---

### Component and Parameter Table

Every value is a **design choice**, stated as such, with the failure mode at other settings. None is a measurement.

| Key | On | Range / units | This book's default | Failure at other values |
|---|---|---|---|---|
| `C` | Capacitor | ≥ 0, in `F_c` against a declared time base | per scale | Individual `C` on a collective substrate under-budgets the calendar tenfold |
| `tau` | Capacitor, RC network | > 0, `τ = R × C` | 3,333 hr (craft) | 10,000 hr: 10k hours reaches only 63%. 1,000 hr: mastery inside a year |
| `leakage` | Capacitor | [0, 1] per stated period | 0.0002/day craft; 0.04/wk campaign | Halving it doubles your computed `P_eq` and the schedule silently under-delivers |
| `leak_tau` | Capacitor | > 0; `= −Δt / ln(1 − leakage)` | 30 d asserted · 90 d default · 180 d enacted | 60 d on a 30 d store makes an unsustainable schedule look survivable |
| `V_BR` | Capacitor | > 0 | 8.0 `V_c` | Unstated: no margin can be computed. Section 7.4 |
| derating | design rule | fraction of `V_BR` | **0.5** | 0.9: transients unprotected. 0.1: store never charges |
| `n_parallel` | Capacitor bank | integer ≥ 1 | per group size | Counting whole members instead of shared composition inflates `C` and `τ` |
| `V_drive` (rail) | source | 0–10 | 10 = full scale | The rail is the ceiling; hours cannot raise it (7.2, Bench Note 2) |
| `r_iso` | Capacitor bank | ≥ 0 `Ω_c`, per-cell ballast | 12.0 | 0: one cell's failure takes the whole rail |

`leakage` and `leak_tau` are two spellings of one parameter. Convert, do not guess: `τ_leak = −Δt / ln(1 − leakage)`.

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Under-fed store** | Feed below `P/τ_leak` | Slow decay with no single cause; "it used to work" | Compute break-even; everything above it is the only part accumulating |
| **Spike feeding** | High `^4`, no `^7` | Vivid sessions, nothing retained between them | Cadence, not intensity. Fix `^7` before touching `^4` |
| **Empty schedule** | High `^7`, near-zero `^4` | Faultless attendance, no charge | Raise per-exposure impression; a schedule that deposits nothing is a calendar |
| **Rail-limited plateau** | `V_drive` below target `P` | Competent, long-serving, permanently mid-level | Raise the rail (Chapter 21.2). Adding hours cannot help |
| **Wrong `τ_leak`** | Constant assumed, not derived | Schedule looks survivable; store sits at half intent | Convert from a measured `leakage`; halving `τ_leak` halves `P_eq` |
| **Saturation read as breakdown** | Ceiling mistaken for fault | Operator "repairs" a working store | Check whether it *holds*. Pinned-and-holding is saturation, a feature |
| **Cumulative dielectric stress** | Prolonged operation near `V_BR` | Every reading in spec; leakage creeping at TP3 | Derate to 0.5; schedule the TP3 reading rather than waiting for a symptom |
| **Un-isolated bank** | No per-cell ballast | One cell's failure pulls the whole rail | Install `R_iso` per cell; isolation is the difference between durable and brittle |
| **Series-chain stress** | Smallest cell takes largest share | Chain fails at average stress well under rating | Balancing resistors — direct access to source for every link |
| **Unnamed `×` on a bank** | Integration asserted without an emergent result | Group described as having a mind; nothing names it | Rewrite as `+`; if integration is genuinely meant, name the result (Chapter 14.2) |
| **Unmetered upward charge** | An `^O` feed charging a `^P` store with no stated gain | Principles that move whenever activity is busy; no outcome you can point at | Draw it as feedback in the 0.05–0.3 band (Chapter 8.4). Unstated gain is `E-CJT-008` |

---

### Test Points

| TP | Node | What it reads | Expected |
|---|---|---|---|
| **TP1** | `P_cap` on the store | Current charge, 0–10 | Within one point of `V_drive × (1 − e^(−t/τ))`. Persistently below: check the rail before the schedule |
| **TP2** | feed current | Feed rate — `^7` cadence at `^4` amplitude | ≥ `P/τ_leak`. Below break-even, the store is draining however it feels |
| **TP3** | leakage at rest | Drain over one idle period | Matches declared `leakage`. **Rising over months = cumulative dielectric stress.** Take on a schedule |
| **TP4** | potential across the dielectric | Working stress vs rating | ≤ 0.5 × `V_BR`. Above: derating margin is gone |

TP1 and TP2 are the operating pair — charge and feed, read together or not at all, since either alone is uninterpretable. TP3 and TP4 fail *silently*, which makes them calendar readings rather than suspicion readings.

---

### What This Chapter Established

- **`^5` Female is a capacitor and the mapping is exact, not figurative**: `^7` Rhythm is the feed current, `^4` Vibration the per-exposure amplitude, `^6` Male decomposition the controlled discharge path.
- **Charging and leaking are one differential equation** with different forcing terms. `P(t) = P_eq + (P_0 − P_eq)e^(−t/τ_leak)` covers both, and `P_eq = f × τ_leak` converts any intended level directly into a required cadence.
- **The curve depends only on `t/τ`**, so one table serves a twelve-week campaign and a ten-thousand-hour apprenticeship. Each τ closes 63.2% of the remaining gap, so the third τ buys one-seventh of what the first did — arithmetic, not decline. **The 10,000-hour constant is 3τ**, recovered rather than asserted.
- **The rail is the ceiling.** `P_∞ = V_drive`. Hours cannot raise it, which is the structural account of permanently mid-level practice.
- **Holding a store costs `P/τ_leak`, so the cost rises as the store fills.** Advanced practitioners practise more because the leak is proportional, not because they are more virtuous.
- **Saturation and breakdown are opposite conditions.** Saturation stops accepting charge and is a designed feature; breakdown stops holding it and is non-recovering. Derate to 0.5 × `V_BR`, declare `V_BR` in every listing, schedule TP3.
- **Capacitors invert the resistor rules**: parallel adds, series divides. Collective stores are therefore slow and heavy, and transmission chains fail at their smallest cell while every average reading looks safe.
- **A bank is `+`, not `×`.** Asserting an integrated group store requires a named emergent result under v7.7 discipline. Most claimed group minds are twelve capacitors on a rail.

---

### Exercises

*(Answers in Appendix H.)*

**7.1 — Read the curve.** An operator has 1,200 logged hours against τ = 3,333 hr on a full-scale rail. Compute `P_cap`, then the hours required to reach 8.0, then say in one sentence how the cost of the point from 7.0 to 8.0 compares with the point from 0 to 1.0.

**7.2 — Convert the leak.** A campaign store declares `leakage = 0.04` per week. Compute `leak_tau` in weeks and the half-life, then the charge remaining after a ten-week dark period on a store that finished its flight at 9.50.

**7.3 — Cost the cadence.** A store with `τ_leak = 30 days` is to be held at 7.0, each session depositing 0.35 points. Compute the required feed rate and session interval. Recompute assuming the operator wrongly used `τ_leak = 60 days`, and state what level their schedule actually holds.

**7.4 — Tell them apart.** Two stores both read pinned at a ceiling and will not rise. One is saturated, one is breached. Give the single bench reading that separates them, name the TP you take it at, and say which of the two is a designed feature.

**7.5 — Load the chain.** Four cells in series, `C` = 6.0, 3.0, 0.8, 2.0, each rated `V_BR = 5.0`, driven at 7.0 `V_c`. Compute `C_total`, the charge, and the potential across each cell. Name the cell that fails first, compute the rail at which it fails, give the average per-cell stress at that rail, and state the fix in one sentence.

**7.6 — Size the bank.** A working group of 12 shares 0.05 `F_c` each through a collective constraint of 40 `Ω_c`. Compute `C_total`, τ and 3τ in months. Three members leave: recompute τ, then state one thing about the group's behaviour that changes and one that does not.

**7.7 (Build) — Meter the leak.** Write a CCDL fragment declaring a `^5` store with a stated `leak_tau`, a refresh schedule, and a monitor that alarms when charge falls below a threshold you choose. Justify the threshold against `P_eq`, and state one thing the alarm must **not** be wired to do.

**7.8 (Marquee) — Specify the whole store.** An operator runs a two-year working on a substrate shared with four collaborators. Specify `C` and its declared time base, τ and the constraint producing it, `leak_tau` with its evidence-thickness justification, `V_BR` and your derating fraction, the network topology, and whether you install isolation. For every value name the failure mode you are buying protection against and the capability you are giving up. State whether the shared store is written with `+` or `×`, and why.
