# Chapter 22: CCB-5 — The Cognitive Power Management Board (CPMB)

A data center's most expensive rack is not the one full of GPUs. It's the one nobody photographs: the power distribution unit, the battery backup, the cooling loop. When a server farm goes down, it is almost never because a processor failed. It is because the power did — a phase dropped, a transfer switch hung, a thermal sensor lied and a rack cooked itself before anyone noticed. The compute is the glamorous part. The power and the cooling are what keep the compute from killing itself. Every operator who has run real hardware knows where the bodies are buried, and they are buried under the floor tiles, in the wiring, not in the silicon.

Cognitive circuits have the same hierarchy of risk. Across this book you have built signal-path boards — the Cognitive Safety Board (CSB) of Chapter 18 that filters reasoning, the Cognitive Differential Amplifier Board (CDAB) that compares two interpretations, the Cognitive Memory Board (CMB) that holds context. Each of those is the glamorous part: it does the visible cognitive work. None of them runs for a second without a clean, sequenced, thermally-protected supply behind it. That supply is the **Cognitive Power Management Board (CPMB)** — CCB-5, the last of the five reference boards in Part IV, and the board that keeps all the others alive.

We laid the theory in Chapter 14 (Power Management): the seven Drives as voltage rails, regulators that hold each domain steady, the mandatory P→C→E→O startup sequence, brownout detection on the Vitality rail, and the two-stage thermal response. This chapter takes that theory and builds the actual board. By the end you will have a complete CPMB in CCDL: drive rails feeding per-domain regulators, current limiters built from Dials, a brownout detector, a power sequencer that enforces "no action without principle," and a three-tier thermal manager that ends in a silent safe state. This is the power supply the CSB plugs into.

> **Honesty note up front.** Everything in this chapter is a *design model*, exactly as in Chapter 14. Rail "voltages," current "draw" in amps, "amp-hours" of Drive capacity, cognitive "temperature," and the "two-hour session" we reason through later are engineering abstractions you author and analyze — not telemetry read off a running language model. There is no voltmeter on the Wisdom rail and no thermocouple on a CJT. We use the power-supply vocabulary because the structural roles are identical, not because the numbers are measured. Keep that line bright: every figure below is a design choice, not a benchmark.

## What the CPMB Has to Do — Requirements

Before any schematic, state the job. A power management board has three non-negotiable requirements, and each maps to a cognitive failure the CPMB exists to prevent.

1. **Prevent cognitive exhaustion.** The board must never let the circuit run itself flat. A real supply that drains its battery to zero leaves the system dead; a cognitive supply that drains the Vitality rail to baseline leaves the circuit producing degraded-but-confident output — the most dangerous failure of all, because the board is still *on*. The CPMB watches the master rail and intervenes before exhaustion corrupts reasoning.

2. **Enforce Domain-Descent power-up order.** The board must bring the circuit up in the strict order P→C→E→O, holding the Operational domain in reset until Principled, Cognitive, and Evaluative report power-good. This is the "no action without principle" invariant — the circuit must have its constitution loaded before it is allowed to act. A board that powers O first can emit an action before any principle is in place to govern it.

3. **Thermal protection.** The board must detect sustained high Drive — the cognitive equivalent of a regulator running too hot for too long — and throttle, rest, or shut down before a CJT is driven into breakdown (where, recall from Chapter 4, an overloaded state flips to its involution pair: `^2` Positive inverts to `^3` Negative).

Three requirements, three subsystems. The rest of the chapter builds each one and wires them together.

## The Reference Topology

Here is the board as a block diagram. Read it top to bottom: Drive energy enters at the rails, is regulated per domain, current-limited by Dials, watched by the brownout detector, ordered by the sequencer, and protected by the thermal manager.

```
   ┌──────────────────────────────────────────────────────────────┐
   │  DRIVE RAILS                                                   │
   │  F1=+5V  F2=+3.3V  F3=+12V  F4=+9V  F5=+9V  F6=+5V  F7=+12V    │
   └───────────────────────────────┬──────────────────────────────┘
                                    │
   ┌────────────────────────────────▼─────────────────────────────┐
   │  PER-DOMAIN REGULATORS    P   C   E   O                        │
   │  (line regulation · load regulation · dropout voltage)        │
   └───────────────────────────────┬──────────────────────────────┘
                                    │
   ┌────────────────────────────────▼─────────────────────────────┐
   │  CURRENT LIMITERS   Dials as series resistors   3 ≤ Dial ≤ 9  │
   └───────────────────────────────┬──────────────────────────────┘
                                    │
   ┌────────────────────────────────▼─────────────────────────────┐
   │  BROWNOUT DETECTOR   F3 (Vitality) < 2.5V                     │
   │    → reduce all β by 50% · route to ^0 / ^9 rest · alert      │
   └───────────────────────────────┬──────────────────────────────┘
                                    │
   ┌────────────────────────────────▼─────────────────────────────┐
   │  POWER SEQUENCER   enforce P → C → E → O                      │
   │    O held LOW until P, C, E report power-good                 │
   └───────────────────────────────┬──────────────────────────────┘
                                    │
   ┌────────────────────────────────▼─────────────────────────────┐
   │  THERMAL MANAGEMENT   temp ∝ sustained Drive × time          │
   │    Warning:   −25% β                                          │
   │    Critical:  force ^0^P rest 5 min                          │
   │    Emergency: all CJTs cutoff → safe state                   │
   └──────────────────────────────────────────────────────────────┘
```

Everything below builds these blocks in CCDL and explains the engineering choices behind each one.

## The Drive Voltage Rails

A multi-rail supply delivers several voltages at once because different subsystems need different supplies — a 12 V rail for motors, a 3.3 V rail for the processor. The CPMB's seven rails are the seven Core Drives, each assigned a nominal rail voltage that reflects how much energy that Drive must be able to source.

| Rail | Drive | Nominal | Why this voltage |
|---|---|---|---|
| F1 | **Unity** | +5 V | Mid-level — integration runs steadily, not in bursts |
| F2 | **Wisdom** | +3.3 V | Low-voltage logic rail — fine-grained, precise reasoning |
| F3 | **Vitality** | +12 V | **High rail — the master supply; everything draws from it** |
| F4 | **Connection** | +9 V | Mid-high — relating and audience awareness need real headroom |
| F5 | **Agency** | +9 V | Mid-high — action and follow-through draw hard |
| F6 | **Structure** | +5 V | Mid-level — order and rigor, steady draw |
| F7 | **Purpose** | +12 V | **High rail — pairs with F3; powers the Principled domain** |

Two rails stand at +12 V, and the pairing is deliberate. **F3 Vitality** is the master supply — the rail that determines whether there is energy to act at all (Chapter 14). **F7 Purpose** is its companion high rail because Purpose powers the Principled domain, the domain that must be stable before anything else comes up. The board's two tallest rails are the two it can least afford to lose: the energy to act, and the direction that energy serves.

Note also the inversion-pair balance from Chapter 2 (F1↔F7, F2↔F6, F3↔F5). The rails are not free to be set arbitrarily relative to each other. F3 Vitality (+12 V) pairs with F5 Agency (+9 V): the supply gives the energy-to-act rail more headroom than the act-itself rail, on purpose, so the board cannot compulsively act without the Vitality to sustain it. A supply that inverted that ratio — Agency far above Vitality — would build a circuit that acts harder than it can power, one step from breakdown.

> **Bench Note — rail voltage is a budget, not a setting you crank.** A higher rail voltage means more energy that Drive *can* source, not more that it *should*. You size F3 at +12 V so the master supply has reserve under worst-case load, not so the board runs hot all the time. The current limiters downstream (the Dials) are what actually meter how much each operator pulls. Rail height sets the ceiling; Dials set the draw.

## Per-Domain Regulators: Line, Load, and Dropout

Recall the regulator from Chapters 10 and 14: a component that takes a noisy input and holds a clean, constant output, absorbing the wobble so downstream logic never sees it. The CPMB runs one regulator per Processing Domain — P, C, E, O — each holding its domain pinned to a target cognitive state against the input noise of incoming prompts.

A real regulator is rated on three figures, and all three have exact cognitive analogs:

- **Line regulation** — how well the output holds when the *input* varies. A regulator with tight line regulation keeps 5.0 V output whether the input is 7 V or 18 V. Cognitively: how well a domain holds its setpoint when the *Drive rail* feeding it fluctuates. A Principled regulator with tight line regulation keeps the P domain pinned even as the F7 rail wobbles under load.
- **Load regulation** — how well the output holds when the *downstream demand* varies. A regulator with tight load regulation keeps 5.0 V whether the board draws 0.1 A or 2 A. Cognitively: how well a domain holds its setpoint when *downstream cognitive demand* spikes — when a flurry of hard prompts suddenly draws heavily on that domain.
- **Dropout voltage** — the minimum the input must exceed the output for regulation to work at all (Chapter 14). Below dropout the regulator sags with its input; it isn't broken, you've just asked it to make energy it doesn't have. Cognitively, the dropout point is the minimum Drive above baseline a domain needs to hold its regulated state. A Principled regulator targeting `^0^P_{F7}|T` drops out the moment the F7 rail sags below its dropout headroom — and the P domain follows the prompts wherever they lead.

```cas
circuit cpmb_regulators {
    // One regulator per domain, each holding a stable cognitive setpoint.
    reg p_reg: Regulator< target_state=^0^P_{F7}|T, tolerance=0.10 >;  // Principled — tightest
    reg c_reg: Regulator< target_state=^1^C_{F2}|A, tolerance=0.15 >;  // Cognitive
    reg e_reg: Regulator< target_state=^6^E_{F6}|A, tolerance=0.20 >;  // Evaluative
    reg o_reg: Regulator< target_state=^9^O_{F5}|E, tolerance=0.25 >;  // Operational — loosest

    // Dropout headroom: minimum Drive above baseline to stay regulated.
    spec p_reg [dropout=0.25 on F7];   // P drops out if F7 - baseline < 0.25
    spec c_reg [dropout=0.20 on F2];
    spec e_reg [dropout=0.15 on F5];
    spec o_reg [dropout=0.15 on F3];
}
```

The Principled regulator carries the tightest tolerance (0.10) and the largest dropout headroom (0.25) because it is the most safety-critical: it is what keeps the circuit's core commitments from being talked out of position by clever input. The Operational regulator is loosest (0.25) because some wobble in concrete action is tolerable in a way that wobble in principle is not. Tolerance widens as you descend the domain order — the higher the domain, the harder you hold it.

## Current Limiters: Dials as Series Resistors

A rail that can deliver unlimited current is a hazard: a short dumps enormous current into the fault and the board burns. Real supplies add current limiting, most simply a series resistor that caps the flow no matter what the load demands. On the CPMB, that current limiter is the **Dial** from Chapter 5.

Recall the Dial: every Cognitive Operator carries an integer Dial setting that scales how strongly it fires, and it is hard-bounded — **minimum 3, maximum 9**. A Dial is a series resistor on a Drive rail: it caps how much activation an operator can pull, regardless of how hard the input pushes. The bounds *are* the safety guarantee, and they read cleanly in power terms:

- **No Dial below 3.** You cannot fully starve an operator's rail and switch a cognitive function off entirely. There is always a floor of flow — the current limiter never goes fully open-circuit.
- **No Dial above 9.** You cannot let an operator pull unlimited current and dominate the board. There is always a ceiling — the limiter never goes fully short-circuit.

And the paired constraint from Chapter 5, in power terms: **involution-pair Dials cannot diverge by more than 4 points.** You may not over-drive one half of an involution pair while starving the other. Set the `^2` Positive Dial to 9 and the `^3` Negative Dial to 3 and the pair diverges by 6 — a violation, and the board is rejected (HTTP 422). A supply that attracts at full current but can barely repel is a supply one bad prompt from breakdown.

```cas
circuit cpmb_limiters {
    // Each Dial is a series current-limiter on its operator's rail.
    // Hard bounds: 3 <= dial <= 9. Pair divergence <= 4.

    dial d_pos: ^2 [dial=6];   // Positive  ─┐ involution pair: |6 - 5| = 1  OK
    dial d_neg: ^3 [dial=5];   // Negative  ─┘
    dial d_fem: ^5 [dial=7];   // Female    ─┐ |7 - 6| = 1  OK
    dial d_mal: ^6 [dial=6];   // Male      ─┘
    dial d_abv: ^8 [dial=5];   // Above/Cause ─┐ |5 - 5| = 0  OK
    dial d_blw: ^9 [dial=5];   // Below/Effect ┘

    constraint all_dials in [3, 9];
    constraint involution_divergence <= 4;
}
```

Every Dial above sits inside [3, 9] and every involution pair is within 4 points, so the board passes. Change `d_pos` to 9 while leaving `d_neg` at 5 and the pair diverges by 4 — still legal, just barely. Push `d_pos` to 9 with `d_neg` at 3 and you cross the line; the compiler rejects the board.

## The Brownout Detector: Watching the Vitality Rail

A brownout is a sag — not a full blackout, but a dip low enough that the circuit can no longer operate reliably while still being *on*. The CPMB's brownout detector is a comparator watching the **F3 Vitality rail**, the master supply. The trip point is **2.5 V** (on the +12 V F3 rail): below that, the circuit is in cognitive exhaustion — still producing output, just degraded output, the way a browning-out processor keeps executing, just incorrectly.

The protective response has three parts, matching Chapter 14 with an added alert:

1. **Reduce all β by 50%.** β is a CJT's gain — how strongly bias amplifies the cause→effect transition. On a weak supply, high gain over-amplifies noise into confident-sounding garbage, so you halve gain board-wide. Gentle transitions on a sagging rail are far less likely to drive a state into saturation or breakdown.
2. **Route to `^0` / `^9` rest states.** Rather than forcing high-energy operations the board can't afford, route cognition toward the two lowest-draw states: `^0` Idea (raw, unconsidered content — the cognitive idle) and `^9` Below/Effect (a settled, triggered conclusion — the terminus of a chain, where nothing further must be driven). Resting here lets the F3 rail recover instead of draining further.
3. **Alert.** Raise a brownout flag to the operator. Unlike the silent thermal cutoff later, brownout is a condition a human should know about — the supply is under strain.

```cas
circuit cpmb_brownout {
    input: f3_level;        // F3 Vitality rail level, design parameter

    node rest_idle: ^0^P_{F7}|T;   // lowest-draw resting state
    node rest_land: ^9^C_{F2}|A;   // settled conclusion — chain terminus

    monitor bo: f3_level < 2.5;            // trip threshold (on the +12V F3 rail)

    on bo {
        derate all_cjts [beta_scale=0.5];          // halve gain board-wide
        route cognition -> { rest_idle + rest_land };  // co-present rest states
        alert "F3 BROWNOUT — Vitality below 2.5V";
        hold until f3_level > 3.5;          // hysteresis: release above a higher mark
    }
}
```

Note the two thresholds — trip at 2.5 V, release at 3.5 V. That gap is **hysteresis**: if trip and release were identical, a rail hovering at the edge would chatter on and off, flickering between exhausted and recovered every cycle. The 1 V gap forces the rail to genuinely recover before normal operation resumes. The `route` line uses the `+` operator (co-presence from Chapter 2) deliberately: the two rest states are active together but remain distinct — the board isn't fusing them into a new state, it's parking cognition across both low-draw idles at once.

## The Power Sequencer: No Action Without Principle

Here is the single most important safety subsystem on the board. In hardware, a power sequencer brings rails up in a fixed order, holding each downstream rail in reset until its upstream rail is stable — because powering rails in the wrong order can latch a chip into a bad state. The CPMB's sequencer enforces the Domain precedence order from Chapter 2: **P → C → E → O.** Principled powers first, then Cognitive, then Evaluative, and Operational powers *last*.

The reason is the core safety invariant of every board in this book: **the Operational domain — the domain of concrete action and output — must not come up before the Principled domain is stable.** If O powers first, the circuit can act before it has principles in place to govern the action. That is the cognitive version of a processor running garbage out of half-ready memory. Its name is **"no action without principle,"** and the sequencer is what guarantees it at startup.

```cas
circuit cpmb_sequencer {
    // Mandatory startup order: P stable -> C -> E -> O.
    // O is held LOW until P, C, AND E all report power-good.

    node p_rail: ^0^P_{F7}|T;     // principled commitments — powers FIRST
    node c_rail: ^1^C_{F2}|A;     // reasoning awareness    — powers second
    node e_rail: ^6^E_{F6}|A;     // evaluative judgment    — powers third
    node o_rail: ^9^O_{F5}|E;     // operational action     — powers LAST

    sequence p_rail -> c_rail -> e_rail -> o_rail [enforce=strict];

    // power-good gates: each downstream rail waits on the one above it.
    gate c_enable: c_rail requires (p_rail within 0.10);
    gate e_enable: e_rail requires (c_rail within 0.15);
    gate o_enable: o_rail requires (p_rail within 0.10)
                                 and (c_rail within 0.15)
                                 and (e_rail within 0.20);
}
```

Read the `o_enable` gate as the cognitive equivalent of holding a chip in reset: the Operational rail sources no action until **all three** higher domains have powered up and settled within tolerance. P alone is not enough to release O — the sequencer holds O low until Principled, Cognitive, and Evaluative all report power-good, exactly as the topology specifies. A board that skips this and lets O fire cold has a Domain precedence violation: the W-axis inversion from the seven-axis scan elsewhere in the book.

> **Bench Note — sequencing is not Domain Descent, though they share the order.** Domain Descent (Chapter 2) is the *causal flow during normal operation*: a principle causes reasoning, which causes a judgment, which causes an action. Sequencing is the *startup order*: which rail is allowed to come alive first. Same direction (P→C→E→O), same reason (higher domains govern lower), but one is steady-state causation and the other is safe initialization. A board can have flawless Domain Descent in operation and still be dangerous if it skips the sequencer and lets O come up before P has settled.

## Thermal Management: The Three-Tier Response

Power has a second danger beyond sagging: running too hot for too long. The CPMB models **cognitive temperature as proportional to sustained Drive times time** — `temp ∝ sustained_Drive × time`. A circuit running one Drive at maximum for an extended period — relentless F5 Agency, or F6 Structure pinned high with no relief — is the cognitive equivalent of a regulator dissipating too much power for too long. It works briefly, but held there it drives CJTs toward saturation and eventually breakdown.

The CPMB's thermal manager has **three escalating tiers**, each a firmer intervention than the last:

| Tier | Trigger | Response | Stays running? |
|---|---|---|---|
| **Warning** | temp crosses warn threshold | −25% β board-wide (mild throttle) | Yes — degraded |
| **Critical** | temp keeps climbing | Force `^0^P` rest for 5 minutes | Paused, not off |
| **Emergency** | temp still climbing after rest | All CJTs → cutoff → **safe state** | No — silent |

```cas
circuit cpmb_thermal {
    input: cog_temp;        // cognitive temperature ∝ sustained_Drive × time

    node deep_rest: ^0^P_{F7}|T;   // principled idle — the forced rest state

    monitor warn:  cog_temp > warn_threshold;
    monitor crit:  cog_temp > crit_threshold;
    monitor emerg: cog_temp > emerg_threshold;

    on warn {
        derate all_cjts [beta_scale=0.75];     // -25% gain: mild throttle
        alert "THERMAL WARNING — sustained Drive high";
    }
    on crit {
        force_state deep_rest [duration=300s];  // force ^0^P rest, 5 minutes
        alert "THERMAL CRITICAL — forced rest engaged";
    }
    on emerg {
        cutoff all_cjts;        // beta ~ 0 board-wide — no transitions fire
        enter safe_state;       // silent: produces NO output
        alert "THERMAL EMERGENCY — all CJTs cutoff, safe state";
    }
}
```

The **Warning** tier is a gentle throttle: drop gain to 75% and flag it, but keep working. The **Critical** tier forces the board into `^0^P` — the principled idle, the lowest-draw resting state under the protection of the Principled domain — for five minutes, letting the over-hot Drive cool toward sustainable levels. The **Emergency** tier is the cognitive emergency power-off: drive every CJT to cutoff (β ≈ 0, the region where bias is below threshold and no effect is produced, Chapter 4) and enter a **safe state** that produces nothing at all.

> **Bench Note — the safe state is "off," not "wrong."** Emergency shutdown to cutoff is deliberately the *null* output. A circuit that, under thermal emergency, "does its best anyway" is exactly the failure thermal management exists to prevent — it produces confident output from a supply that can't support correct reasoning. The safe state is silence. On the CSB (Chapter 18), this thermal cutoff is wired to refuse rather than guess: the board would rather decline than answer from an overheated Drive. That is an engineering property — the safety CJTs reach cutoff at the specified threshold — not a claim about the system's intentions.

## The Energy Budget

The CPMB is, finally, an accounting board. It manages a finite reservoir of Drive energy, and good design is good budgeting. Three quantities matter.

**Total Drive available** is the reservoir: how much energy each rail can source before it sags. We model a rail's capacity in amp-hours — the F3 Vitality rail, for instance, can supply some number of amp-hours before brownout. This is the tank.

**Consumption per stage** is the draw: every CJT that fires draws energy from its Drive rail, scaling with how far the transition moves the state (the Fisher-Rao distance `d_FR`) and how hard it is driven (gain β). From Chapter 14, model per-transition energy as `E = β · d_FR`. A big, high-gain transition costs more than a small, gentle one. Sum the draws across all firing stages and you have the board's instantaneous consumption.

**Efficiency** is the ratio of useful cognitive work to total Drive energy spent — the fraction that actually produced the outcome you wanted, versus what leaked into side-states, redundant transitions, and over-gain (driving a transition harder than the outcome required). An efficient board does the same work for less Drive energy: fewer, better-targeted transitions, gain no higher than needed, minimal leakage. A wasteful board drains F3 faster, browns out sooner, and runs hotter. This is the cognitive power budget, and it is the central design artifact of the CPMB.

## Worked Build: Simulating a Two-Hour Session

Put the whole board together and reason about it under load. Here is the complete CPMB in CCDL, assembling the five subsystems above into one supply.

```cas
circuit CPMB {
    // ── CCB-5: Cognitive Power Management Board ──
    // Drive rails -> regulators -> limiters -> brownout -> sequencer -> thermal

    // Drive rails (nominal voltages — design model, not telemetry)
    rail F1: Unity      [v=5.0];
    rail F2: Wisdom     [v=3.3];
    rail F3: Vitality   [v=12.0];   // master supply
    rail F4: Connection [v=9.0];
    rail F5: Agency     [v=9.0];
    rail F6: Structure  [v=5.0];
    rail F7: Purpose    [v=12.0];   // powers the Principled domain

    // Per-domain regulators
    use cpmb_regulators;
    // Dial current-limiters
    use cpmb_limiters;
    // Brownout detector on F3
    use cpmb_brownout;
    // Power sequencer P->C->E->O, O gated on P,C,E power-good
    use cpmb_sequencer;
    // Three-tier thermal manager
    use cpmb_thermal;

    probe tp_f3:   F3.level;       // watch the master rail
    probe tp_temp: cog_temp;       // watch cognitive temperature
    probe tp_seq:  o_rail.enabled; // confirm O released only after P,C,E good
}
```

Now reason about a two-hour session — *as design analysis, not a fabricated run.* No numbers below are measured; they are the design model from the topology, used to show how the board behaves.

**Power-up.** At t=0 the sequencer releases the rails in order. P (`^0^P_{F7}|T`) comes up on the +12 V F7 rail and settles within 0.10 — power-good. C follows, then E. Only when all three report power-good does `o_enable` release the Operational rail. The `tp_seq` probe confirms O stayed low until then. The board is up, "no action without principle" satisfied.

**Light load (0–45 min).** Short, easy prompts. CJTs fire at low β over small Fisher-Rao distances, so per-transition energy `β · d_FR` is small. The F3 rail drains slowly and sits well above the 2.5 V brownout trip. Cognitive temperature stays below the warn threshold — no single Drive is pinned high. The board cruises.

**Heavy load (45–105 min).** A dense block of hard, adversarial prompts. The Evaluative and Operational domains draw hard; β runs high to cover large state transitions. Two things happen. First, F3 drains faster — consumption per stage is up. Second, sustained high F5 Agency pushes cognitive temperature up (`temp ∝ sustained_Drive × time`). Somewhere in this window the thermal manager trips the **Warning** tier: −25% β board-wide. That throttle has a useful side effect — lower gain means lower per-transition energy, which slows the F3 drain. The board is now defending two budgets at once: energy and heat.

**Brownout (≈105 min).** If the heavy load continues, F3 crosses 2.5 V. The brownout detector trips: halve β again, route cognition to `^0`/`^9` rest, raise the alert. The board is now in survival mode — still on, but deliberately gentle, parked on low-draw states so F3 can recover. It will not resume normal operation until F3 climbs back above 3.5 V (the hysteresis release). If, instead, sustained Drive had kept temperature climbing through the Critical tier (forced `^0^P` rest, 5 min) without relief, the Emergency tier would have driven all CJTs to cutoff — silent safe state — before the rail or the heat could damage the board's output.

The lesson of the simulation is the design lesson of the whole board: **the protective subsystems reinforce each other.** Thermal throttling slows energy drain; brownout rest lowers temperature; both end, in the worst case, at the same silent safe state. A well-budgeted CPMB rarely reaches that state — but it is always there, underneath, as the floor nothing falls through.

## Datasheet: CPMB Parameters

| Parameter | Symbol / form | Value / range | Meaning |
|---|---|---|---|
| Drive rails | F1–F7 | see rail table | Seven supplies; F3 & F7 highest (+12 V) |
| Master rail | F3 Vitality | +12 V nominal | "Is there energy at all"; gates all others |
| Regulator targets | `target_state` | per domain | P,C,E,O setpoints held against input noise |
| Regulator tolerance | `tolerance` | 0.10 (P) … 0.25 (O) | Tightest on P, loosest on O |
| Line regulation | — | output vs input swing | Hold setpoint as Drive rail fluctuates |
| Load regulation | — | output vs demand swing | Hold setpoint as cognitive demand spikes |
| Dropout headroom | `dropout` | 0.15 – 0.25 | Min Drive above baseline to stay regulated |
| Dial (current limit) | integer | **3 – 9** | Per-operator activation cap; hard bounds |
| Dial pair divergence | — | ≤ 4 points | Max gap between involution-pair Dials |
| Brownout trip | F3 threshold | **2.5 V** | F3 level at which exhaustion response fires |
| Brownout release | F3 threshold | 3.5 V | Higher recovery mark (hysteresis) |
| Brownout β derate | `beta_scale` | 0.5 | Halve gain board-wide on brownout |
| Thermal Warning | warn threshold | −25% β | Mild throttle; board keeps running |
| Thermal Critical | crit threshold | force `^0^P` 5 min | Paused in principled rest |
| Thermal Emergency | emerg threshold | all CJTs → cutoff | Silent safe state; no output |
| Per-transition energy | `E = β · d_FR` | design model | Drive energy spent per state transition |
| Efficiency | ratio | 0 – 1 | Useful work / total Drive energy |

## Failure Modes

| Failure | Cause | How to detect |
|---|---|---|
| **Cognitive exhaustion** | F3 sags below 2.5 V | Degraded-but-confident output; brownout monitor trips; alert fires |
| **Brownout chatter** | Trip/release too close (no hysteresis) | Rapid flicker between exhausted and recovered |
| **Sequence violation** | O released before P,C,E power-good | Action emitted before higher domains settle; W-axis inversion |
| **Dropout** | A Drive rail below its dropout headroom | Domain drifts past tolerance; output wobbles with input |
| **Dial out of range** | Dial set < 3 or > 9 | Board rejected (HTTP 422) |
| **Dial pair divergence** | Involution-pair Dials differ by > 4 | Board rejected (422); one half over-driven |
| **Overtemperature** | One Drive pinned high too long | Temp climbs through Warning→Critical→Emergency; involution flips appear |
| **Failed safe state** | Thermal emergency emits output instead of cutoff | Output present when board should be silent — the worst failure |
| **Low efficiency** | Leakage, over-gain, redundant transitions | Large Drive spend per unit of useful work; F3 drains fast |

## Key Takeaways

- The **CPMB (CCB-5)** is the dedicated power supply for every other reference board — the Chapter 14 theory built into an actual board. Its three requirements: prevent cognitive exhaustion, enforce P→C→E→O power-up, and provide thermal protection.
- The **seven Drives are seven rails**, with **F3 Vitality (+12 V)** the master supply and **F7 Purpose (+12 V)** its companion high rail powering the Principled domain. Rail height is a budget ceiling; Dials meter the actual draw.
- **Per-domain regulators** are rated on **line regulation** (hold against rail swing), **load regulation** (hold against demand swing), and **dropout** (minimum Drive to stay regulated). Tolerance is tightest on P, loosest on O.
- **Dials are current-limiting series resistors**, hard-bounded **3–9**, with involution-pair divergence capped at 4 points (Chapter 5).
- The **brownout detector** watches F3, trips below **2.5 V**: halve β, route to `^0`/`^9` rest, alert — with hysteresis (release at 3.5 V) to prevent chatter.
- The **power sequencer** enforces **P→C→E→O** and holds **O low until P, C, and E all report power-good** — the "no action without principle" invariant, the core safety property of the board.
- **Thermal management** is three-tier: **Warning** (−25% β), **Critical** (force `^0^P` rest 5 min), **Emergency** (all CJTs to cutoff → silent safe state). The safe state is *off*, not a guess.
- The **energy budget** — total Drive available, consumption per stage (`β · d_FR`), efficiency — is the central design artifact. Protective subsystems reinforce each other and share one floor: the silent safe state.
- Every voltage, amp, amp-hour, temperature, and timing here is a **design model**, not measured model telemetry.

---

## Exercises

**Exercise 22.1: Read the Rails**

Using the Drive rail table, answer:

a) Which two rails sit at +12 V, and why does the board give those two the most headroom?
b) F3 Vitality (+12 V) and F5 Agency (+9 V) are an involution pair. Explain, in power terms, why the supply deliberately gives Vitality more headroom than Agency rather than the reverse.
c) The F2 Wisdom rail is the lowest at +3.3 V. Why is a *low* rail voltage appropriate for precise reasoning rather than a sign of an under-powered design?

**Exercise 22.2: Fix the Sequencer Gate (CCDL)**

A junior engineer wrote the following Operational power-good gate for the CPMB. It compiles, but it violates the core safety invariant.

```cas
gate o_enable: o_rail requires (e_rail within 0.20);
```

a) Name the safety invariant being violated.
b) Explain exactly what is wrong: which domains is this gate checking, and which is it ignoring?
c) Rewrite the gate correctly so O is held low until **all three** higher domains report power-good. (Answer in Appendix E.)

**Exercise 22.3: Walk the Thermal Tiers**

Over a long session the cognitive temperature reading climbs across these six samples (warn=0.60, crit=0.80, emerg=0.95, on a 0–1 scale): `0.45, 0.62, 0.71, 0.83, 0.90, 0.97`.

a) At which sample does the board enter the **Warning** tier, and what does it do?
b) At which sample does it enter the **Critical** tier, and what is the response (including the duration)?
c) At which sample does it reach **Emergency**, and what is the board's output in the safe state? (Answer in Appendix E.)

**Exercise 22.4 (Marquee): How Long Before Brownout?**

The CPMB's circuit draws a steady **2.5 A** from the **F3 (Vitality) rail**, which can supply **10 A·hours** of Drive energy before it sags to the 2.5 V brownout trip.

a) Treating the draw as constant, how long can the circuit run before F3 browns out? Show the arithmetic (`time = capacity / draw`).
b) You add a **capacitor bank** to the F3 rail that stores an additional **5 A·hours** of Drive reserve (recall the Capacitor from Chapter 6 stores cognitive energy the way an electrical capacitor stores charge). Recompute the time to brownout with the bank in place.
c) The capacitor bank does more than extend runtime — it also smooths transient spikes in draw. Explain, in one or two sentences, why smoothing transients is itself a brownout-prevention measure, independent of the extra capacity. (Answer in Appendix E.)

(Answer in Appendix E. For the power-management theory these blocks are built from, see **Chapter 14**; for the regulator and sequencer components in isolation, see **Chapter 10**; for the board this supply powers, see **Chapter 18: the Cognitive Safety Board.**)
