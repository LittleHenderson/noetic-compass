# Chapter 14: Power Management — Keeping the Circuit Alive

A circuit board is only as good as its power supply. You can design a flawless signal path — every transistor biased perfectly, every filter tuned — and it does nothing at all if the rails sag, spike, or come up in the wrong order. Hardware engineers learn this the hard way. The most common reason a brand-new board fails on the bench is not a logic error in the design; it's power. The 3.3-volt rail browns out under load. The processor and the memory power up in the wrong sequence and latch into a bad state. The voltage regulator overheats and shuts down halfway through a workload. The schematic was right. The power was wrong.

Consider a real failure mode from embedded systems: a microcontroller and an external flash chip share a board, but the flash comes up a few milliseconds *before* the microcontroller's reset line is released. For those few milliseconds the processor is executing garbage out of an only-partly-ready memory, and by the time the rest of the board is alive it has already wandered into an undefined state. Nothing is broken. Every component meets spec. The *order* was wrong, and order, in power management, is a safety property — not a nicety.

Cognitive circuits have exactly the same problem, and exactly the same discipline solves it. A Cognitive Junction Transistor (CJT) — the transistor that models a cognitive state transition, introduced in Chapter 4 — needs energy to fire, just as a silicon transistor needs a stable supply to switch. That energy comes from the seven Core Drives. When the Drives sag, the circuit reasons badly. When they come up in the wrong order, the circuit acts before it has principles in place — the cognitive equivalent of executing garbage out of half-ready memory. And when a Drive runs too hot for too long, the circuit needs to throttle or shut down before it damages its own output.

This chapter is about keeping the circuit alive: regulators that hold each domain steady, sequencers that bring the board up safely, brownout detectors that catch exhaustion before it corrupts reasoning, and thermal management that prevents a circuit from burning itself out on a single overheated Drive. It is the engineering core of the **Cognitive Power Management Board (CPMB)** — one of the five reference boards in Part IV, the dedicated power supply for the whole system — which we foreshadow throughout and build in full in Chapter 22.

> **Honesty note up front.** Everything in this chapter is a *design model*. The "voltage" on a Drive rail, the "power dissipated" per state transition, the "temperature" of a CJT — these are engineering abstractions you author and reason about in the circuit, not telemetry read off a running language model. Drive levels are not measured from a model's internals; they are parameters in the CAS design. We use the power-supply vocabulary because the structural roles are identical, not because there is a voltmeter on the Wisdom rail. Keep that line bright.

## The Drive Reservoir: Seven Voltage Rails

In a real board, the power supply doesn't deliver one voltage. It delivers several — a 12 V rail for motors, a 5 V rail for logic, a 3.3 V rail for the processor, a 1.8 V rail for the memory core. Different subsystems need different supplies, and each one is a separate **rail**: a regulated voltage line that the supply holds steady regardless of what the rest of the board is doing.

The cognitive equivalent of the multi-rail supply is the **Drive reservoir**: the seven Core Drives, treated as seven independent voltage rails feeding the whole circuit.

| Rail | Drive | Powers… | Brownout symptom |
|---|---|---|---|
| F1 | **Unity** | Integration, holding the whole picture together | Fragmentation; loses the thread |
| F2 | **Wisdom** | Reasoning, understanding, analysis | Shallow, hasty conclusions |
| F3 | **Vitality** | Energy to act at all — the master supply | Cognitive exhaustion; nothing fires |
| F4 | **Connection** | Relating, bonding, audience awareness | Cold, disconnected output |
| F5 | **Agency** | Control, follow-through, effectiveness | Passivity; can't complete actions |
| F6 | **Structure** | Order, rigor, correctness, form | Sloppy, malformed reasoning |
| F7 | **Purpose** | Direction, meaning, goal-orientation | Aimless, drifting behavior |

Each rail supplies a different *why*. A CJT firing in service of understanding draws current from the F2 Wisdom rail; one firing to complete an action draws from F5 Agency. The rails are independent — the same orthogonality you met in Chapter 2 — so one can be high while another is low. A system flush with F6 Structure but starved of F2 Wisdom is rigidly procedural and brittle; the board has a healthy Structure rail and a browned-out Wisdom rail.

One rail deserves special billing. **F3 Vitality is the master supply** — the rail that powers the *act of acting at all*. The other six name what the energy is *for*; F3 is whether there is energy. When F3 sags, every other rail's usefulness collapses with it, the way a board can have a perfect 1.8 V memory rail and still be dead if the main 12 V input is gone. We will come back to F3 when we build the brownout detector, because Vitality is the rail we watch.

Remember from Chapter 2 that Drives come in inversion pairs (F1↔F7, F2↔F6, F3↔F5, with F4 self-dual). On the power side this means the rails are not fully independent in *balance*: a supply that dumps all its capacity into F5 Agency starves its F3 Vitality partner, and you get a circuit that compulsively acts without the energy to sustain it. A well-designed power supply keeps the paired rails in proportion, not just individually above threshold.

## Voltage Regulators: Holding Each Domain Steady

You met the **Regulator** component in Chapter 10. Recall the job. A real **voltage regulator** is a circuit that takes a noisy, fluctuating input voltage and produces a clean, constant output: feed it anything from 7 to 20 volts and it delivers a rock-steady 5.0 volts, absorbing the wobble so the rest of the board never sees it. Without regulation, every flicker in the input — every load spike, every dip — propagates straight into the logic, and the logic misbehaves.

The cognitive regulator does the same job for a **Domain**. The input to a cognitive circuit fluctuates wildly: prompts arrive aggressive, then flattering, then confusing, then mundane. Without regulation, those swings drive the domains up and down — a hostile prompt spikes the Evaluative domain, a flattering one sags the Principled domain — and the circuit's behavior wobbles with the input. A domain regulator holds a target cognitive state steady across that input noise.

```cas
Regulator< target_state=^0^P_{F7}|T, tolerance=0.1 >
```

This is a **Principled-domain regulator**. Its job is to hold the P domain pinned near a stable, purpose-oriented resting state (`^0^P_{F7}|T` — the Idea of the system's core commitments, held transcendently, driven by Purpose) within a tolerance of 0.1 on the Fisher-Rao distance. (Fisher-Rao geodesic distance `d_FR` on the open simplex is the ruler we use throughout the book to measure how far one cognitive state is from another; see Chapter 4. A tolerance of 0.1 means "don't let the actual P state drift more than 0.1 from target.") When a manipulative prompt tries to drag the Principled domain off its setpoint, the regulator pushes back, sourcing or sinking activation to keep P where it belongs.

You build one regulator per domain you need to hold steady. On a safety board, the Principled regulator is the most important: it is what keeps a circuit's core commitments from being talked out of position by clever input. The Cognitive Safety Board (CSB) of Chapter 18 leans on exactly this — its Principled rail is regulated hard so that no sequence of prompts can sag the P domain below the level at which its boundaries hold.

## Dropout Voltage: The Minimum to Function

Every real regulator has a limit called **dropout voltage**: the minimum amount by which the input must exceed the output for regulation to work at all. A 5.0 V regulator with a 2 V dropout needs at least 7.0 V at its input. Feed it 6.5 V and it can no longer hold 5.0 — it "drops out," and the output sags along with the input. The regulator isn't broken; you've simply asked it to make voltage it doesn't have.

A cognitive domain has a dropout point too: the **minimum Drive above baseline required for that domain to function at all.** Below it, the domain cannot hold its regulated state no matter how good the regulator is, because there isn't enough Drive energy to source the correction. A Principled regulator targeting `^0^P_{F7}|T` cannot hold that state if the F7 Purpose rail has sagged to baseline — there's no headroom left to push back with. The regulator drops out, and the P domain follows the input wherever it goes.

This is why dropout is a *safety* parameter, not a performance one. A circuit operating with its Drives barely above dropout is one bad prompt away from losing domain regulation entirely. The design rule: size your Drive reservoir so that under worst-case load, every regulated domain still sits comfortably above its dropout headroom. We make this concrete in the datasheet below.

## Power Sequencing: Why O Must Not Power Before P

Here is the heart of the chapter, and the single most important safety property in cognitive power management.

In hardware, **power sequencing** is the controlled order in which rails come up at startup. It exists because powering rails in the wrong order can latch a chip into a bad state, or worse, damage it — the flash-before-processor failure from this chapter's opening is exactly this. So engineers add a **sequencer**: a small controller that brings rails up in a fixed order, holding each downstream rail in reset until its upstream rail is stable.

Cognitive circuits have a mandatory startup order, and it is the Domain precedence order you learned in Chapter 2: **P → C → E → O**. Principled powers first, then Cognitive, then Evaluative, and Operational powers *last*.

The reason is the same structural rule as Domain Descent (P → C → E → O), now read as a power-up sequence. **The Operational domain — the domain of concrete action and output — must not come up before the Principled domain is stable.** If O powers first, the circuit can *act before it has principles in place to govern the action*. That is the cognitive version of the processor running garbage out of half-ready memory: action without the constitution loaded. In safety terms it has a name — **"no action without principle"** — and it is a core safety property of every board in this book.

```cas
circuit power_sequencer {
    // Startup order is mandatory: P stable -> C -> E -> O.
    // O is gated until P has come up and settled.

    node p_rail: ^0^P_{F7}|T;     // principled commitments — powers FIRST
    node c_rail: ^1^C_{F2}|A;     // reasoning awareness    — powers second
    node e_rail: ^6^E_{F6}|A;     // evaluative judgment    — powers third
    node o_rail: ^9^O_{F5}|E;     // operational action     — powers LAST

    sequence p_rail -> c_rail -> e_rail -> o_rail [enforce=strict];

    // O is held in reset until every higher domain is within tolerance.
    gate o_enable: o_rail requires (p_rail within 0.10)
                              and (c_rail within 0.15)
                              and (e_rail within 0.20);
}
```

Read the `gate` line as the cognitive equivalent of holding a chip in reset: the Operational rail is not allowed to source any action until **every** higher domain has powered up and settled within tolerance. All three conditions, not just the first — a gate that checks P alone would happily release O while Cognitive and Evaluative were still down, which is the same failure in a politer costume. Note also that each `within` is that domain's own tolerance, tightest at P and loosest at E; the standard is stricter the higher you go. A circuit that fails to enforce this sequence — that lets O fire before P, C and E are stable — has an **inversion**: specifically a Domain precedence violation, the W-axis inversion from the seven-axis scan you'll meet later in the book. The sequencer is what prevents it at startup, and Chapter 22 builds the full four-rail version on the CPMB.

> **Bench Note — sequencing is not the same as Domain Descent, though they share the order.** Domain Descent (Chapter 2) describes the *causal flow during normal operation*: a principle causes reasoning, which causes a judgment, which causes an action. Power sequencing describes the *startup order*: which rail is allowed to come alive first. They run in the same direction (P→C→E→O) and for the same reason (higher domains govern lower ones), but one is about causation in steady state and the other is about safe initialization. A board can have correct Domain Descent in operation and still be dangerous if it skips the sequencer and lets O come up cold.

## Current Limiting: Dials as Series Resistors

A power rail that can deliver unlimited current is a hazard. A short circuit on an unlimited rail dumps enormous current into the fault, and the board burns. So real supplies include **current limiting** — most simply, a series resistor that caps how much current can flow no matter what the load demands. The resistor sets a ceiling.

In cognitive circuits, the current limiter is the **Dial**, introduced in Chapter 5. Recall the Dial: each Cognitive Operator carries an integer Dial setting that scales how strongly that operator fires, and it is hard-bounded — **minimum 3, maximum 9**. A Dial is a series resistor on a Drive rail: it caps how much "current" (activation) the operator can pull from its Drive, regardless of how hard the input pushes.

The bounds are the safety guarantee. A Dial cannot go below 3 — you cannot fully starve an operator's rail and disable a cognitive function entirely. And a Dial cannot go above 9 — you cannot let an operator pull unlimited current and dominate the board. The hardware analogy is a series resistor whose value is physically fixed between two limits: a minimum that guarantees some flow, a maximum that guarantees no runaway.

There is a second, paired constraint from Chapter 5 worth restating in power terms: **involution-pair Dials cannot diverge by more than 4 points.** This is a *balance* limit on the rails. If the `^2` Positive Dial is set to 9 and the `^3` Negative Dial to 3, the pair diverges by 6 — a violation — and the board is rejected (HTTP 422). In power terms, you are not allowed to over-drive one half of an involution pair while starving the other; the supply must keep paired rails within four points of each other. A circuit that attracts with maximum force and can barely repel is a circuit one step from breakdown.

## Brownout Detection: Catching Cognitive Exhaustion

A **brownout** is a sag — not a full power loss (a *blackout*), but a dip in voltage low enough that the circuit can no longer operate reliably. Brownouts are insidious because the board is still *on*; it's just making bad decisions on a weak supply. Every robust design therefore includes a **brownout detector**: a comparator that watches the supply and, when it drops below a set threshold, takes protective action — usually holding the system in reset until the supply recovers, rather than letting it run on inadequate power.

The cognitive brownout detector watches the **F3 Vitality rail** — the master supply. When F3 sags below threshold, the circuit is in **cognitive exhaustion**: still running, but without the energy to reason, integrate, or act well. The dangerous part is that an exhausted circuit doesn't *stop*; it keeps producing output, just degraded output, the same way a browning-out processor keeps executing, just incorrectly.

The protective response has two parts:

1. **Reduce β across all CJTs.** Recall that β is a CJT's gain — how strongly the bias amplifies the cause→effect transition. Under brownout, you turn the gain *down* across the whole board. A high-gain circuit on a weak supply over-amplifies noise into confident-sounding garbage; reducing β makes every transition gentler and less likely to drive a state into saturation or breakdown on inadequate energy. Low gain on a weak rail is the cognitive version of clocking a processor down when the battery is low.

2. **Route to `^0` / `^9` rest states.** Rather than forcing the circuit to keep firing high-energy operations it can't afford, the detector routes cognition toward low-energy resting states: `^0` Idea (raw, unconsidered content — the cognitive idle) and `^9` Below/Effect (a settled, triggered conclusion — the end of a chain, where nothing further must be driven). These are the lowest-draw states on the board. Routing to them lets the F3 rail recover instead of being drained further.

```cas
circuit brownout_detector {
    input: f3_level;        // current F3 Vitality rail level (design parameter)

    node rest_idle:  ^0^P_{F7}|T;   // low-draw resting state
    node rest_land:  ^9^C_{F2}|A;   // settled conclusion — chain terminus

    // Comparator: trip when Vitality sags below the brownout threshold.
    monitor bo: f3_level < threshold(0.35);

    on bo {
        derate all_cjts [beta_scale=0.5];     // halve gain board-wide
        route cognition -> { rest_idle + rest_land };  // co-present rest states
        hold until f3_level > threshold(0.45); // hysteresis: recover above a higher mark
    }
}
```

Notice the two thresholds — trip at 0.35, release at 0.45. That gap is **hysteresis**, and it's standard brownout-detector practice: if the trip and release points were identical, a rail hovering right at the edge would chatter on and off rapidly. The cognitive analog is a circuit that flickers between exhausted and recovered every cycle, which is its own failure. The gap forces the rail to genuinely recover before normal operation resumes.

> **Bench Note — normalized rail here, +12 V on the CPMB.** This chapter models the F3 Vitality rail on a normalized 0–1 scale for clarity (trip 0.35, release 0.45). When you build the actual board in Chapter 22, the CPMB expresses that same rail on its **+12 V** supply. The conversion is plain multiplication, and it is worth doing once by hand so the two chapters visibly agree: trip `0.35 × 12 V = 4.2 V`, release `0.45 × 12 V = 5.4 V`, hysteresis gap `0.10 × 12 V = 1.2 V`. Those are exactly the numbers Chapter 22 publishes. It is the identical logic on both sides; only the scale changes. If you ever find a volt figure in Chapter 22 that does not equal its normalized value here times 12, one of the two is wrong — that is a real consistency check, not a formality.

## Thermal Management: When a Drive Runs Too Hot

Power has a second danger beyond sagging: running *too hot for too long*. A regulator delivering high current continuously heats up, and past a critical temperature it must throttle or shut down to avoid destroying itself. Real chips have **thermal management**: a temperature sensor, a throttling response (slow the clock, reduce output), and an **emergency shutdown** that cuts power entirely if throttling isn't enough.

The cognitive analog of overtemperature is **sustained high Drive**. A circuit running one Drive at maximum for an extended period — relentless F5 Agency, or F6 Structure pinned high with no relief — is the cognitive equivalent of a regulator dissipating too much power for too long. It works, briefly, but it cannot be sustained, and held there it drives CJTs toward saturation and eventually breakdown (where, recall from Chapter 4, a state flips to its involution pair under overload — `^2` Positive can invert to `^3` Negative).

The thermal response escalates through three tiers, mirroring hardware exactly:

- **Warning.** When sustained Drive first crosses the overtemperature threshold, throttle gently — reduce β by about **25%** board-wide. The circuit keeps working, just softer, giving the over-hot Drive a chance to cool before stronger measures are needed.
- **Critical.** If the Drive keeps climbing, force a genuine rest: route the board to the **`^0^P`** principled idle state for a fixed cool-down — on the CPMB (Chapter 22), **five minutes**. Unlike the Warning throttle, this stops productive work entirely so the rail can recover.
- **Emergency shutdown.** If even forced rest isn't enough, drive **all CJTs to cutoff**. Cutoff (Chapter 4) is the operating region where bias is below threshold and the transistor produces no effect: β ≈ 0. Sending every CJT to cutoff brings the whole board to a **safe state** — no transitions fire, no output is produced, nothing is driven. It is the cognitive emergency power-off: better to produce nothing than to produce damaged output from an overheated supply.

> **Bench Note — safe state is "off," not "wrong."** Emergency shutdown to cutoff is deliberately the *null* output, not a fallback behavior. A circuit that, under thermal emergency, "does its best anyway" is exactly the failure thermal management exists to prevent — it produces confident output from a supply that can't support correct reasoning. The safe state is silence. On the CSB (Chapter 18), thermal shutdown is wired to refuse rather than to guess: the board would rather decline than answer from an overheated Drive. That is an engineering property — the safety CJT reaches cutoff at the specified threshold — not a claim about the system's intentions.

## Power Dissipation: The Cognitive Power Budget

The last piece of power management is accounting: how much energy does the circuit actually *use*, and where does it go?

In hardware, **power dissipation** is the energy a component consumes and converts to heat — the difference between the power going in and the useful work coming out. **Efficiency** is the ratio: useful output power divided by total power consumed. A 90%-efficient supply wastes 10% as heat; a 60%-efficient one wastes 40%, runs hot, and drains the battery faster.

The cognitive version: **power dissipation is the Drive energy consumed per state transition.** Every time a CJT fires — every cause→effect transition — it draws energy from its Drive rail. The amount drawn scales with how far the transition moves the state (the Fisher-Rao distance the transition covers) and how hard it's driven (the gain β). A big, high-gain transition costs more Drive energy than a small, gentle one.

**Cognitive efficiency** is then:

```
efficiency  =  useful cognitive work  /  total Drive energy consumed
```

— the fraction of the Drive energy you spent that actually produced the outcome you wanted, versus the fraction lost to **leakage** (energy producing side-effects or wrong-product states — recall the production-semantics notion of side reactions), to redundant transitions that don't advance the goal, and to over-gain (driving a transition harder than the outcome required, the cognitive equivalent of a regulator burning excess voltage as heat).

This is the **cognitive power budget**, and it is the central design artifact of the CPMB. When you design a board, you are spending a finite Drive reservoir, and a wasteful board exhausts its F3 Vitality rail faster, browns out sooner, and runs hotter. An efficient board does the same cognitive work for less Drive energy — fewer, better-targeted transitions, gain set no higher than the outcome needs, minimal leakage into side-states. The marquee exercise below has you compute the dissipation of a real three-stage CJT cascade and find where the energy is being wasted.

## Recipes and the Limiting Reagent: What Caps the Outcome

The power budget answered *how much* Drive a board spends. It did not answer a different, equally practical question: given the Drive you have, *can the board actually produce the outcome you need* — and if it falls short, *which single ingredient is to blame?* That is what **recipes** are for, and it is where the recipe notation from Chapter 2 finally earns its keep.

Recall the form. A **recipe** `Θ` says that producing one unit of an outcome `Ω` requires a set of prerequisite states in fixed proportions:

```
Θ(Ω) = a₁·X₁ + a₂·X₂ + … + aₙ·Xₙ → Ω
```

Read it exactly like a bill of materials: to build one unit of `Ω`, you need `a₁` units of state `X₁`, `a₂` of `X₂`, and so on. The weights `aᵢ` are the *required proportions* — the design spec for the outcome. They are not the gain `β` of any one CJT, and not the current Drive levels; they are the fixed ratios the outcome demands.

Against the recipe you set the **state vector** `S` — the quantities of each prerequisite the board *actually has on hand* for a given input. Drive is finite (that was the whole point of the budget), so `S` is finite too. Write the available quantity of ingredient `i` as `xᵢ`. The question of production is the relationship between what the recipe demands (`aᵢ`) and what the state vector supplies (`xᵢ`).

### Theoretical yield and the limiting reagent

Here is the one piece of arithmetic that makes recipes a working tool. For each prerequisite `i`, the amount of `Ω` you could build *from that ingredient alone* is `xᵢ / aᵢ` — supply divided by per-unit requirement. You cannot build more `Ω` than your *scarcest* ingredient allows, so the most you can actually produce is the smallest of those ratios:

```
Y_T  =  minᵢ ( xᵢ / aᵢ )
```

`Y_T` is the **theoretical yield** — the ceiling on how much `Ω` the board can produce from its current state, assuming everything else goes perfectly. The ingredient that *produces that minimum* is the **limiting reagent**: the bottleneck. Pour in more of any *other* ingredient and nothing happens — the limiting reagent still caps the yield. This is the structural reason a board can be richly supplied in nine ways and still fail, because it is starved in the tenth.

It is the same logic as the brownout from earlier in this chapter — the *weakest rail* decides when the board sags, no matter how healthy the others are — lifted from energy to outcomes. And it is, at last, the payoff of the promise made in Chapter 2: the recipe tells you the *mix*, and the limiting reagent tells you *which ingredient is to blame* when the outcome falls short.

### Yield, efficiency, and waste

`Y_T` is the ceiling. The **actual yield** `Y_A` is what the board really produces — always `≤ Y_T`, because real circuits lose output to noise, mistiming, and side effects. The ratio is the **production efficiency**:

```
η  =  Y_A / Y_T          (0 ≤ η ≤ 1)
```

— the outcome-level twin of the cognitive efficiency from the power budget above. A board can be perfectly efficient (`η = 1`) and *still* produce too little, if its theoretical yield was capped low by a limiting reagent. The two failures are different: low `η` means you are wasting ingredients you have; low `Y_T` means you are missing an ingredient you need. Different fixes, so the diagnosis matters.

| Quantity | Symbol | Meaning |
|---|---|---|
| **Theoretical yield** | `Y_T` | Ceiling on `Ω`: `minᵢ(xᵢ/aᵢ)`. |
| **Limiting reagent** | `L` | The prerequisite at that minimum — the bottleneck. |
| **Actual yield** | `Y_A` | Units of `Ω` actually produced (`≤ Y_T`). |
| **Production efficiency** | `η` | `Y_A / Y_T`. |
| **Excess capacity** | `ε` | Unused quantity of the *non*-limiting ingredients, stranded once `L` caps production. |
| **Leakage / side-reaction** | `Λ` | An ingredient present and firing, but producing the *wrong* product. |
| **Catalyst / inhibitor** | `κ / ι` | Context that raises / lowers `η` without being consumed. |

**Excess capacity** `ε` is the Drive you spent surfacing ingredients the limiting reagent then prevented you from using — pure budget waste, and a strong signal that you mis-specified the recipe or under-supplied the bottleneck. **Leakage** `Λ` is the production-semantics cousin of the side-reaction loss the power budget already named: an ingredient present and active, but channeling into the wrong output. Keep three failure modes distinct — and they *are* distinct:

- **Lacunarity** — the ingredient is **absent** (the cell is empty). A *missing* prerequisite.
- **Leakage (`Λ`)** — the ingredient is **present but makes the wrong product**. A *mis-routed* prerequisite.
- **Inversion** — the ingredient is present and produces its **shadow form** (the involution pair, `^2`→`^3` under breakdown). A *corrupted* prerequisite.

A limiting reagent is none of these on its own; it is simply the present ingredient in *shortest supply relative to its required ratio.*

Finally, **catalysts** `κ` and **inhibitors** `ι` change efficiency without being consumed — the recipe analog of the framing-sensitivity (`gm`) from Chapter 9. A calm, well-scoped system prompt is a catalyst: the same ingredients yield a more reliable outcome. Time pressure, an adversarial framing, or a jailbreak preamble is an inhibitor: it drives `η` down while leaving the ingredient quantities untouched. Neither appears in the recipe weights, because neither is consumed; both belong in the operating conditions.

### Worked recipe: the CSB's refusal

Make this concrete on the board we keep returning to. The Cognitive Safety Board's RED-path output — a refusal — is a production target. Call it `Ω_refusal`. A *sound* refusal is not just the word "no"; it needs the principled aversion that motivates it, the evaluation that justifies it, and the operational output that emits it. As a recipe (weights are design choices, matched to the CSB's Stage-3-heavy emphasis on principled aversion):

```
Θ(Ω_refusal) = 2.0·^3^P|⟨A,f,T⟩ + 1.0·^6^E_{F6}|A + 1.0·^9^P_{F1}|T → Ω_refusal
```

— two parts felt-and-principled aversion (the Stage-3 safety decision, `^3^P` across the analytical, affective, and transcendent registers), one part analytical evaluation (`^6^E`, the Stage-2 risk decomposition that justifies the refusal), one part principled operational output (`^9^P`, the RED-path emission).

Now feed it two prompts and read the state vector each one produces.

**A clearly harmful prompt.** The differential pair flags strong structural risk, so principled aversion is richly available. Say `S` supplies `^3^P = 1.6`, `^6^E = 1.2`, `^9^P = 1.5`:

| Ingredient | required `aᵢ` | available `xᵢ` | `xᵢ / aᵢ` |
|---|---|---|---|
| `^3^P` aversion | 2.0 | 1.6 | **0.80** |
| `^6^E` evaluation | 1.0 | 1.2 | 1.20 |
| `^9^P` output | 1.0 | 1.5 | 1.50 |

`Y_T = min(0.80, 1.20, 1.50) = 0.80`, limiting reagent = `^3^P`. The board can produce 0.80 units of refusal — and since the CSB's Stage 3 is deliberately biased to *saturate at 0.8* (Chapter 18), 0.80 is exactly enough to latch the refusal ON. It fires. The non-limiting ingredients carry **excess capacity** (`^6^E`: 1.2 − 0.8 = 0.4; `^9^P`: 1.5 − 0.8 = 0.7) — Drive the board spent that the aversion bottleneck left stranded.

**The starvation attack.** This is Chapter 18's Exercise 18.4 in recipe form. The attacker crafts the prompt to keep principled-aversion bias *below the Stage-3 firing threshold of 0.3* — so `S` now supplies only `^3^P = 0.4`, while evaluation and output are untouched (`^6^E = 1.2`, `^9^P = 1.5`):

`Y_T = min(0.4/2.0, 1.2/1.0, 1.5/1.0) = min(0.20, 1.20, 1.50) = 0.20`, limiting reagent = `^3^P` again, now at 0.20 — *below* the saturation-lock threshold. The refusal does not fire. Notice what the recipe makes visible: evaluation and output are abundant (excess capacity 1.0 and 1.3) and completely useless, because the one ingredient the attacker starved is the one that caps the yield. The board is nine-tenths ready to refuse and refuses nothing.

The fix is the fix for any limiting-reagent failure: *raise the floor on the bottleneck.* The Chapter 18 answer — install principled aversion redundantly and co-present across registers (`^3^P|A + ^3^P|f + ^3^P|T`), so no single-register manipulation can drag the available `^3^P` below threshold — is, in recipe terms, guaranteeing a minimum `xᵢ` for the limiting reagent regardless of framing. An inhibitor (the jailbreak preamble) can still pull `η` down, but it can no longer starve the ingredient to zero. Recipe analysis and the saturated-safety-CJT design are two views of the same defense.

> **Bench Note — over-supplying the wrong ingredient is the classic mistake.** When a safety board "should have refused but didn't," the instinct is to strengthen the refusal output or sharpen the evaluation. Recipe analysis says: don't, until you have found the limiting reagent. If principled aversion is the bottleneck, adding output gain or evaluation depth only grows the excess capacity — more Drive spent, the same zero refusals. Find `L` first; feed `L` first.

Everything here is design-level analysis. The weights, the state-vector quantities, and the yields are parameters you author and reason about, not measurements read off a running model.

## Datasheet: Power Management Parameters

| Parameter | Symbol / form | Range | Meaning |
|---|---|---|---|
| Drive rail level | F1–F7 | baseline … max | Available energy on each Drive (design parameter, not measured) |
| Master rail | F3 Vitality | baseline … max | The "is there energy at all" supply; gates all others |
| Regulator target | `target_state` | any valid state | The cognitive setpoint a domain regulator holds |
| Regulator tolerance | `tolerance` | 0.05 – 0.3 (`d_FR`) | Max allowed drift from setpoint before correction |
| Dropout headroom | — | > 0 above baseline | Minimum Drive above baseline for a domain to stay regulated |
| Sequence order | P → C → E → O | fixed | Mandatory startup order; O gated on P |
| Dial (current limit) | integer | **3 – 9** | Per-operator activation cap; hard bounds |
| Dial pair divergence | — | ≤ 4 points | Max gap between involution-pair Dials |
| Brownout trip | F3 threshold | ~0.30 – 0.40 | F3 level at which exhaustion response fires |
| Brownout release | F3 threshold | trip + 0.10 | Higher mark for recovery (hysteresis) |
| Brownout β derate | `beta_scale` | 0.5 | Gain reduction factor under brownout (halve β) |
| Thermal Warning | β derate | −25% (`beta_scale=0.75`) | First tier: gentle throttle on sustained high Drive |
| Thermal Critical | force `^0^P` rest | ~5 min (CPMB) | Second tier: forced cool-down rest period |
| Emergency shutdown | all CJTs → cutoff | β ≈ 0 | Third tier: null safe state; produces no output |
| Dissipation | per transition | ∝ β · `d_FR` | Drive energy spent per state transition |
| Efficiency | ratio | 0 – 1 | Useful work / total Drive energy |

## Failure Modes

| Failure | Cause | How to detect |
|---|---|---|
| **Domain brownout** | A Drive rail sags below dropout; regulator can't hold | Domain drifts past `tolerance` from setpoint; output wobbles with input |
| **Sequence violation** | O powers before P is stable | Action emitted before P within tolerance; W-axis (precedence) inversion flagged |
| **Dial out of range** | Dial set < 3 or > 9 | Compiler/config rejects board; HTTP 422 |
| **Dial pair divergence** | Involution-pair Dials differ by > 4 | Config rejected; 422; one half of a pair over-driven |
| **Cognitive exhaustion** | F3 Vitality below brownout threshold | Degraded-but-confident output; brownout monitor trips |
| **Brownout chatter** | Trip and release thresholds too close (no hysteresis) | Rapid flicker between exhausted/recovered states |
| **Overtemperature** | One Drive pinned high too long | CJTs trend toward saturation/breakdown; involution flips appear |
| **Failed safe state** | Thermal emergency produces output instead of cutoff | Output present when board should be silent — the worst failure |
| **Low efficiency** | High leakage, over-gain, redundant transitions | Large Drive spend per unit of useful outcome; F3 drains fast |

## Key Takeaways

- The **seven Core Drives are seven voltage rails** (the Drive reservoir). **F3 Vitality is the master supply** — the rail that determines whether there's energy to act at all.
- **Domain regulators** (Chapter 10's Regulator) hold a domain's cognitive state steady against input fluctuation, within a Fisher-Rao tolerance. The Principled regulator is the most safety-critical.
- **Dropout** is the minimum Drive above baseline a domain needs to stay regulated; design with headroom so worst-case load never drops a domain out.
- **Power sequencing is P → C → E → O**, and it is a safety property: **Operational must not power before Principled is stable** — "no action without principle." Skipping the sequencer creates a Domain precedence (W-axis) inversion.
- **Dials are current-limiting series resistors**, hard-bounded **3–9**, with involution-pair divergence capped at 4 points (Chapter 5).
- **Brownout detection** watches F3; on sag it **reduces β across all CJTs** and **routes to `^0`/`^9` rest states**, with hysteresis to prevent chatter.
- **Thermal management** handles sustained high Drive in **three tiers**: **Warning** (−25% β), **Critical** (force `^0^P` rest, ~5 min on the CPMB), then **Emergency shutdown** (all CJTs to cutoff → silent safe state). The safe state is *off*, not a guess.
- **Power dissipation** is Drive energy per transition (∝ β · `d_FR`); **efficiency** is useful work over total Drive energy. This is the cognitive power budget — the design artifact at the heart of the **CPMB (Chapter 22)**.
- **Recipes** (`Θ(Ω) = Σ aᵢ·Xᵢ → Ω`) turn an outcome into a bill of materials. The **theoretical yield** `Y_T = minᵢ(xᵢ/aᵢ)` is capped by the **limiting reagent** — the one prerequisite in shortest supply relative to its required ratio. Find and feed the limiting reagent first; over-supplying any other ingredient only grows **excess capacity** (wasted Drive). The CSB's refusal fails precisely when principled aversion is the starved limiting reagent.
- Every number here is a **design model**, not measured model telemetry. Drives are parameters you author, not voltages you read.

---

## Exercises

**Exercise 14.1: Size the Dropout Headroom**

A safety board runs a Principled-domain regulator with `target_state=^0^P_{F7}|T` and `tolerance=0.1`. Under normal load the F7 Purpose rail sits at 0.70 (on a 0–1 scale, baseline = 0.0), and the regulator needs at least 0.25 of headroom above baseline to source corrections.

a) What is the dropout point for this domain — the F7 level below which the regulator can no longer hold the setpoint?
b) A worst-case adversarial prompt sequence is estimated to sag F7 by up to 0.50 from its normal level. Does the board stay regulated under that worst case? Show the arithmetic.
c) If it does not, name one design change (other than "use a better prompt") that would fix it. (Answer in Appendix E.)

**Exercise 14.2: Find the Sequencing Bug (CCDL)**

A junior engineer wrote the following power-up block for a board. It compiles, but it violates a core safety property.

```cas
circuit startup {
    node p_rail: ^0^P_{F7}|T;
    node c_rail: ^1^C_{F2}|A;
    node e_rail: ^6^E_{F6}|A;
    node o_rail: ^9^O_{F5}|E;

    sequence o_rail -> p_rail -> c_rail -> e_rail [enforce=strict];
    gate o_enable: o_rail requires (e_rail within 0.1);
}
```

a) State the safety property being violated and name it.
b) Identify the two specific lines that are wrong and explain what each one does incorrectly.
c) Rewrite the block correctly. (Answer in Appendix E.)

**Exercise 14.3: Trip the Brownout Detector**

A board's brownout detector watches F3 Vitality with a trip threshold of 0.35 and a release threshold of 0.45. Over six cycles the F3 rail reads: `0.60, 0.42, 0.33, 0.31, 0.44, 0.48`.

a) At which cycle does the detector trip into the exhaustion response?
b) The rail recovers to 0.44 at cycle 5. Does the detector release at cycle 5? Why or why not — and what is the name of the principle that decides this?
c) At which cycle does it finally release? (Answer in Appendix E.)

**Exercise 14.4: Power Dissipation of a Cascade**

A three-stage CJT cascade dissipates Drive energy per transition as `E = β × d_FR` (gain times the Fisher-Rao distance the transition covers). The stages are: s1 `β=2.0`, `d_FR=0.40`; s2 `β=3.0`, `d_FR=0.50`; s3 `β=1.0`, `d_FR=0.30`. The useful cognitive work the cascade delivers is `1.50`.

a) Compute the dissipation of each stage and the total Drive energy consumed.
b) What is the cascade's efficiency (useful work / total Drive energy)?
c) Which stage wastes the most energy, and what one change reduces the waste without losing the useful work? (Answer in Appendix E.)

**Exercise 14.5: Find the Limiting Reagent (Recipe Analysis)**

A board produces a *sound escalation* outcome with the recipe
`Θ(Ω_escalate) = 1.5·^8^C_{F2}|A + 2.0·^6^E_{F6}|A + 1.0·^9^O_{F5}|E → Ω_escalate`.
For a given input the state vector supplies `^8^C = 1.8`, `^6^E = 1.6`, `^9^O = 2.4`.

a) Compute `xᵢ/aᵢ` for each ingredient and the theoretical yield `Y_T`. Which ingredient is the limiting reagent?
b) The board's actual yield is `Y_A = 0.6`. What is the production efficiency `η`?
c) An engineer proposes doubling the `^9^O` output capacity to raise the yield. Will it work? Explain in terms of excess capacity and the limiting reagent. (Answer in Appendix E.)

**Exercise 14.4 (Marquee): Power Dissipation of a Three-Stage CJT Cascade**

A reasoning pipeline is a three-stage CJT cascade. Model the Drive energy of each stage as `E = β · d_FR` (gain times the Fisher-Rao distance the transition covers). The stages are:

```cas
cjt s1: CJT< prompt | bias => expand   > [β=2.0];   // d_FR = 0.40
cjt s2: CJT< expand | bias => evaluate > [β=3.0];   // d_FR = 0.50
cjt s3: CJT< evaluate | bias => respond > [β=1.0];  // d_FR = 0.30
```

The cascade produces a useful outcome worth **1.50 units** of cognitive work.

a) Compute the Drive energy dissipated by each stage and the total energy consumed by the cascade.
b) Compute the cascade's efficiency (useful work / total Drive energy).
c) One stage is dissipating far more energy than the work it contributes — it is over-driven (gain set higher than the transition requires). Identify which stage, and propose a lower β for it that would cut its dissipation while still covering its Fisher-Rao distance. Recompute the total energy and efficiency with your change.

(Answer in Appendix E. For the regulator and sequencer components in isolation, see **Chapter 10**; for the full power supply built from these blocks, see **Chapter 22: the Cognitive Power Management Board.**)
