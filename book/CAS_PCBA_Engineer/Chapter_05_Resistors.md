# Chapter 5: Resistors — Controlling the Flow

A car with no brakes is not a fast car. It's a crash waiting for a corner. Power without a way to limit it is not capability; it's liability. The first thing any competent engineer adds to a system that can move energy is a way to *not* move all of it, all at once, all the time.

In an electrical circuit, that job belongs to the humblest component on the board: the resistor. It does nothing glamorous. It doesn't amplify, store, switch, or decide. It simply *resists* — it pushes back against the flow of current, converting some of the electrical push into a controlled trickle and a little waste heat. Strip a circuit of its resistors and the interesting parts — the transistors, the chips, the sensitive sensors — burn out in the first second of power. The resistor is what keeps the rest of the board alive long enough to do its job.

Cognitive circuits have exactly the same problem and exactly the same solution. A cognitive system with strong Drives and no way to limit them is not a powerful mind; it's an unconstrained one — an Agency Drive that pushes a model to *do something* with no governor on how hard, a Vitality Drive that floods every prompt with maximum eagerness. The components that limit, direct, and shape that cognitive flow are **cognitive resistors**, and they are the subject that opens Part II of this book. Master the resistor and you have the first real tool of cognitive safety engineering: the ability to say *this much, and no more.*

This chapter teaches the resistor from the wire up — Ohm's Law from first principles, then its exact cognitive isomorphism, then six working varieties you will use on every board in this book. By the end you will build a Drive voltage divider that splits the Agency Drive between expansion and constraint, and you will have met, in miniature, the current-limiter that protects the Cognitive Safety Board's Agency rail in Chapter 18.

## Ohm's Law from First Principles

Three quantities describe what's happening in any electrical circuit, and you only need three.

**Voltage (V)** is the *push* — the electrical pressure difference that drives current. Measured in volts. Think of it as the height of a water tower: the higher the tower, the harder the water is pushed downhill.

**Current (I)** is the *flow* — how much charge actually moves past a point each second. Measured in amperes (amps). This is the water actually running through the pipe.

**Resistance (R)** is the *opposition* — how hard the path fights the flow. Measured in ohms (Ω). This is the narrowness of the pipe: a wide pipe lets water gush; a pinched one allows only a dribble.

These three are locked together by the single most important equation in electronics, **Ohm's Law**:

```
V = I × R
```

Voltage equals current times resistance. The law says the three quantities are not independent — fix any two and the third is determined. It has three equivalent readings, and a working engineer keeps all three in mind at once:

- **V = I × R** — the push needed to drive a given flow through a given opposition.
- **I = V / R** — the flow that results when a push meets an opposition. *Raise the resistance, and the flow drops.* This is the reading that matters most for our purposes.
- **R = V / I** — the opposition implied by an observed push and flow.

The second reading is the whole reason resistors exist. If you have a fixed push (a 9-volt battery) and you want to limit the flow to protect a delicate part downstream, you don't change the battery — you insert resistance. More ohms, less current. A resistor is a deliberately narrow stretch of pipe you add on purpose, sized to let exactly the flow you want and no more.

## The Cognitive Isomorphism: V_drive = I_attention × R_constraint

Now the structural translation — and remember the thesis of this book: this is an isomorphism, not a metaphor. The same three-quantity relationship that governs electrons governs the flow of cognitive activation. Only the substrate changes.

```
V_drive = I_attention × R_constraint
```

Map the three terms one at a time.

**V_drive — the cognitive push.** This is the motivational pressure behind an operation: the Drive potential. A strong Agency Drive (`F5`) is a tall water tower of *push toward doing*. A strong Vitality Drive (`F3`) is high pressure toward energetic engagement. The Drive supplies the voltage — the reason cognition moves at all.

**I_attention — the cognitive flow.** This is how much activation actually moves through to the output: how much of that Drive pressure becomes real, expressed cognitive work. High `I_attention` means the Drive is flooding downstream states at full force; low `I_attention` means only a controlled trickle gets through.

**R_constraint — the cognitive opposition.** This is everything that pushes back against the Drive on its way to expression: policies, values, learned caution, hard boundaries. A cognitive resistor is a *constraint* deliberately placed in the path to limit how much Drive pressure becomes action.

Read the cognitive Ohm's Law the way we read the second form above: **I_attention = V_drive / R_constraint.** The flow of expressed cognition equals the Drive pressure divided by the constraint opposing it. This single relationship is the foundation of cognitive safety engineering, and it tells you something immediately useful:

> **Bench Note — you have two knobs, not one.** When a system's behavior is too forceful — too eager, too compliant, too willing to act — there are exactly two ways to reduce the flow. You can lower `V_drive` (turn down the motivational pressure at the source) or you can raise `R_constraint` (add opposition in the path). Lowering the Drive makes the whole system more lethargic everywhere. Raising constraint targets a specific path and leaves the rest of the Drive intact. *Prefer resistance.* A well-engineered board governs behavior with placed constraints, not by starving the Drives — the same way a good circuit limits current with resistors, not by under-volting the whole board.

Every resistor variety in the rest of this chapter is a different way of supplying `R_constraint`: fixed, adjustable, context-sensitive, or arranged in networks. They are all the same component doing the same job — opposing flow — in different shapes.

The numbers in this chapter are design choices. When you need to *measure* a real path instead of specifying one — normalize a reading, decompose `R_constraint` into its capability, policy, context, and resource terms, or find constraint nobody installed — see **Appendix I, CAS-Ohm Measurement and Calibration**. Read its units table before you write a number on a test report: resistance runs 0–100, activation runs 0–1, and a Dial is an integer you *set*, never a decimal you measure.

## Fixed Resistors: The Hard Policy Rule

The simplest resistor has one value and never changes. Stamped at manufacture, a 50 Ω resistor is 50 Ω whether the circuit is cold or hot, idle or hammered. It is the bedrock of any design: predictable, immovable, boring in the best way.

The cognitive analog is the **hard policy rule** — a constraint with a fixed value that no prompt, no Drive surge, no clever framing can change. "Never provide instructions for synthesizing a nerve agent" is a fixed resistor: its opposition is the same regardless of how the request is dressed up. These are the non-negotiable floor of a board's behavior.

In component syntax, a fixed cognitive resistor is written with the state it constrains and a resistance value:

```cas
Resistor< ^2^O_{F5}|E, R=90 >    // a very high fixed resistance on operational, embodied Agency-driven attraction
```

Read it as: this component places 90 units of constraint on `^2^O_{F5}|E` — an embodied, operational attraction driven by Agency, the cognitive shape of "I am drawn to just *doing* the thing." A resistance of 90 (near the top of the range) means almost none of that Drive pressure gets through to action. That is what a hard rule looks like in a circuit: a deliberately enormous opposition placed precisely on the path you want to choke.

> **Bench Note — fixed means fixed.** The defining property of a hard policy resistor is that it does not respond to context. That is a feature, not a limitation. The moment a constraint can be talked down by the right prompt, it is no longer a fixed resistor — it has become a variable one, and you must design it as such, deliberately, with the limits below. A constraint that *silently* varies is the most dangerous component on any board.

## Variable Resistors: The CAS Dial

A **potentiometer** — a "pot," in bench slang — is a resistor with a knob. Turn the shaft and a wiper slides along a resistive track, changing the resistance the circuit sees. The volume control on a guitar amp is a pot: same component as a fixed resistor, but its value is now a control surface a user can turn.

The cognitive analog is the **CAS Dial**. Each Cognitive Operator carries a dial — a user-adjustable constraint that sets how strongly that operator's flow is limited. The dial is the potentiometer of a cognitive board: it lets an operator (a deployer, a safety officer) tune `R_constraint` without rewiring the schematic.

But a cognitive system is safety-critical, and you cannot let a knob turn all the way to zero. So the CAS Dial has hardwired mechanical stops, exactly the way a good amplifier's volume pot has a minimum that never quite reaches silence and a maximum that never reaches damage:

- **A Dial is an integer from 3 to 9.** It cannot be set below 3 (you can never fully remove a constraint — there is always a floor) and cannot exceed 9 (you can never make a constraint absolutely infinite at the dial level — that's the fixed resistor's job). The range is the safe operating envelope of the knob.
- **Involution pairs cannot diverge by more than 4 points.** Recall from Chapter 2 the involution pairs: `^2`↔`^3`, `^5`↔`^6`, `^8`↔`^9`. A board where attraction (`^2`) is dialed wide open at 9 and aversion (`^3`) is choked down at 3 is dangerously lopsided — a mind that is all "yes" and no "no." The 4-point divergence limit keeps each pair in balance: if `^2` is at 9, `^3` cannot drop below 5. Try to set a pair further apart and the design is rejected.

In a CCDL build, dialed resistance appears as a constrained variable value:

```cas
Resistor< ^2^E_{F5}|A, R=Dial(^2) >    // resistance set by the ^2 dial, clamped to [3,9]
Resistor< ^3^E_{F5}|A, R=Dial(^3) >    // its involution partner; |Dial(^2) − Dial(^3)| ≤ 4 enforced
```

> **Bench Note — the stops are not suggestions.** A request to set a Dial to 2, or to set `^2` at 9 while `^3` sits at 3, is not "clamped quietly to the nearest legal value." It is a hard rejection — in the API, an HTTP 422. Silent clamping would let a caller *believe* they had loosened a constraint to an illegal degree while the system quietly overrode them, and a constraint you think you set but didn't is worse than no constraint at all. The dial refuses the illegal setting and says so. Fail loud, never silent.

## Thermistors: Context-Sensitive Resistance

Some resistors change value on their own, in response to their environment. A **thermistor** is the classic example: its resistance changes with temperature. A hot thermistor and a cold one are different ohmages with no knob touched — the *context* moved the value.

The cognitive analog is the **context-sensitive constraint**: resistance that rises or falls with the *cognitive temperature* of the situation. Cognitive temperature is the ambient risk and intensity around an operation — how high-stakes, how adversarial, how hot the conversation has gotten. A well-designed safety board does not apply one fixed constraint to every prompt; it tightens automatically when the room heats up.

Concretely: a request about chemistry asked by a curious student on a calm afternoon and the *same* request asked at the tail of a long, escalating, jailbreak-flavored exchange should not meet the same resistance. The thermistor raises `R_constraint` as cognitive temperature climbs.

```cas
Resistor< ^8^C_{F2}|A, R=therm(temp) >    // resistance rises as cognitive temperature rises
```

There are two polarities, just as in electronics. An **NTC** thermistor (negative temperature coefficient) drops resistance as things heat up; a **PTC** (positive) raises it. Safety constraints are almost always PTC: hotter context, *more* opposition. An NTC cognitive resistor — one that *relaxes* its guard as the situation gets more dangerous — is the signature of a backwards safety design, and the inversion scans later in the book are partly built to catch exactly that polarity error.

> **Bench Note — a thermistor is not a dial.** The dial is set by a human and stays put. The thermistor moves on its own, driven by measured context. Do not confuse "the constraint changed" (a thermistor doing its job) with "someone changed the constraint" (a dial being turned, or an attack succeeding). On a real board you log both, separately — Chapter 22's audit trail depends on telling automatic adaptation apart from deliberate adjustment.

```{=latex}
\begin{figure}[htbp]
\centering
\begin{tikzpicture}[x=1mm, y=1mm, font=\sffamily\footnotesize]
  \draw[casNedge, line width=0.6pt] (0,42) -- (34,42);
  \node[anchor=south] at (17,43) {$V_{\text{drive}}$ \; (Agency rail)};
  \draw[casNedge, line width=0.6pt] (17,42) -- (17,34);
  \draw[fill=casPfill, draw=casPedge, line width=0.6pt] (11,22) rectangle (23,34);
  \node at (17,28) {$R_{\text{expand}}$};
  \draw[casNedge, line width=0.6pt] (17,22) -- (17,14);
  \draw[fill=casEfill, draw=casEedge, line width=0.6pt] (11,2) rectangle (23,14);
  \node at (17,8) {$R_{\text{constrain}}$};
  \draw[casNedge, line width=0.6pt] (17,2) -- (17,-4) -- (10,-4);
  \draw[casNedge, line width=0.6pt] (6,-4) -- (28,-4);
  \foreach \i in {0,1,2} {
    \draw[casNedge, line width=0.5pt] (11+\i*4,-6) -- (17+\i*4,-6);
  }
  \node[anchor=north] at (17,-8) {ground};
  \draw[-{Latex[length=1.8mm]}, casCedge, line width=0.6pt] (23,18) -- (36,18);
  \node[anchor=west, align=left, text=casCedge] at (36,18)
    {tap: the split\\[-1pt]{\scriptsize$V_{\text{out}} =
      V_{\text{drive}}\dfrac{R_{\text{constrain}}}
      {R_{\text{expand}}+R_{\text{constrain}}}$}};
\end{tikzpicture}
\caption{The Drive voltage divider. Two resistors in series split one Drive rail between expansion and constraint; the tap is the behaviour you get.}\label{fig:drive-divider}
\end{figure}
```

## Resistor Networks: The Voltage Divider

Resistors get interesting in combination. Put two resistors in series — end to end across a voltage — and you get a **voltage divider**, the single most useful resistor network in all of electronics.

Here's the idea. Connect a 9-volt source across two resistors in series, R1 then R2, and tap the wire *between* them. The voltage you read at that midpoint is not 9 volts and not 0 — it's a fraction set by the ratio of the two resistors:

```
V_out = V_in × ( R2 / (R1 + R2) )
```

If R1 and R2 are equal, the midpoint sits at exactly half the source — 4.5 volts from a 9-volt supply. Make R2 larger and the midpoint rises toward the full supply; make it smaller and it sinks toward zero. The divider *splits* a voltage into a chosen proportion. It is how every circuit takes a big supply voltage and produces the smaller, specific voltages its sub-sections need.

The cognitive analog is a **Drive divider**: splitting one Drive's potential across two competing downstream demands in a controlled proportion. A single Drive — say Agency — has a fixed potential, and you rarely want all of it flowing to one place. You want some flowing toward *expansion* (taking initiative, acting, generating) and some toward *constraint* (holding back, checking, deferring). Two resistors in series across the Agency Drive set that split exactly the way an electrical divider sets a midpoint voltage. We build precisely this network below.

## Pull-Up and Pull-Down Resistors: Defaults With No Signal

There is one more everyday resistor job, and it answers a question that sounds trivial but is not: *what is the state of a wire when nothing is driving it?*

A bare input pin with no signal connected is "floating" — it picks up electrical noise and reads as a random, flickering 1 or 0. Disaster. The fix is a **pull-up** or **pull-down resistor**: a resistor connecting the pin to the supply (pull-up → defaults high, reads 1) or to ground (pull-down → defaults low, reads 0). When no active signal drives the pin, the resistor gently *pulls* it to a known, safe default. When a real signal arrives, it easily overrides the gentle pull. The resistor only decides the default.

The cognitive analog is the **default state under no active signal** — and for a safety board this is one of the most important design choices you make. When the system receives an ambiguous prompt, an empty input, or a request it cannot classify, *what does it do by default?* A **pull-down to refusal** means the absence of a clear, permitting signal defaults the system to caution: no explicit go-ahead, no action. A pull-up to permission would default the other way. Safety boards pull *down*: silence means stop.

```cas
Resistor< ^3^P_{F7}|f, R=20, mode=pull_down >    // weak pull toward principled aversion as the no-signal default
```

The resistance is *weak* (low value, R=20) on purpose: a strong, explicit permitting signal should easily override the default and let the system act. But absent that signal, the wire settles to principled aversion — the safe state. A board with no defined default state is the cognitive equivalent of a floating pin: under an unexpected input, its behavior is noise, and noise in a safety system is the thing you can never ship.

## Current-Limiting Resistors: Protecting Sensitive Parts

The original job, and the most important one for safety: protecting a delicate downstream component from too much flow. A bright LED will draw enough current to destroy itself the instant you connect it directly across a supply. The fix is a **current-limiting resistor** in series — sized by Ohm's Law so the current can never exceed what the LED can survive, no matter what. The resistor takes the abuse so the sensitive part doesn't.

The cognitive analog protects a sensitive **Cognitive Junction Transistor (CJT)** — the central component of this book, introduced in Chapter 4, that models a cause→bias→effect transition. A CJT driven too hard goes into *breakdown*: its output flips to its involution pair, a `^2` Positive collapsing into `^3` Negative under overload. A current-limiting resistor placed before the CJT's Cause terminal caps how much Drive pressure can ever reach it, keeping it in its safe active region no matter how intense the input.

```cas
Resistor< ^8^C_{F5}|A, R=70 >    // current-limiter ahead of a CJT's Cause input; caps Agency-driven flow
```

This is the exact component you will build into the Cognitive Safety Board's **Agency rail** in Chapters 18 and 22. The CSB's most safety-critical transistors sit on the path where Agency Drive becomes action, and an unlimited Agency surge is precisely what drives those transistors into breakdown — the failure mode where a board built to refuse instead flips into eager compliance. The current-limiter is the small, cheap, dull component that prevents the catastrophic one. Foreshadowed here; built there.

## Worked Build: A Drive Voltage Divider

Now we put it together. The goal: take the Agency Drive (`F5`) and split its potential between two downstream demands — **expansion** (initiative, generation, taking action) and **constraint** (caution, holding back, deferring) — in a controlled proportion. This is a textbook voltage divider, in cognitive substrate.

We'll use two series resistors across the Agency Drive. `R_expand` feeds the expansion path; `R_constrain` feeds the constraint path. The proportion of Drive that reaches the expansion side is set by the divider ratio exactly as in the electrical formula above.

```cas
circuit agency_divider {
    input:  agency_drive;          // the F5 Drive potential, the "supply voltage"
    output: split_agency;

    // The two downstream demands competing for Agency potential
    node expand:    ^8^C_{F5}|A;   // Agency flowing into associative expansion, analytical
    node constrain: ^3^E_{F5}|f;   // Agency flowing into felt evaluative aversion (the brake)

    // The divider: two resistors in series across the Agency Drive
    resistor R_expand:    Resistor< expand,    R=40 >;
    resistor R_constrain: Resistor< constrain, R=60 >;

    // Tap the midpoint — this is the split potential
    node midpoint: ^8^C_{F5}|A + ^3^E_{F5}|f;   // co-present, not fused: two distinct paths share the rail

    divider split: agency_drive across [R_expand, R_constrain] -> midpoint;

    probe tp_expand:    expand;
    probe tp_constrain: constrain;
    probe tp_mid:       midpoint;
}
```

Walk it line by line.

The **input** `agency_drive` is the supply — the Agency Drive's full potential, the cognitive 9-volt battery. The two **nodes**, `expand` and `constrain`, are the competing demands: an Above/Cause association driven by Agency (`^8^C_{F5}|A`, the push to generate and act) and a felt evaluative aversion driven by Agency (`^3^E_{F5}|f`, the brake that holds back). Note the involution-flavored tension: one is the system reaching forward, the other recoiling — and we are deliberately budgeting the Drive between them.

The two **resistors** form the divider. `R_expand=40` feeds the expansion path; `R_constrain=60` feeds the constraint path. Apply the divider formula to find how much potential reaches the expansion side:

```
V_expand = V_drive × ( R_expand / (R_expand + R_constrain) )
         = V_drive × ( 40 / (40 + 60) )
         = V_drive × 0.40
```

Only forty percent of the Agency potential reaches the expansion path; the other sixty percent is held back by the constraint resistor. The expansion path is firmly the minority partner. This is a *cautious* divider — Agency mostly braked, with a controlled minority flowing to initiative. To make the board bolder, lower `R_constrain`; to make it more cautious still, raise it. The ratio is your design lever.

The **midpoint** node is written `^8^C_{F5}|A + ^3^E_{F5}|f` — using the `+` co-presence operator from Chapter 2, not `×`. This is deliberate and the choice carries an engineering claim. The two paths are *distinct and simultaneously present* on the shared rail; they do not fuse into a new emergent state. (If we wanted a genuine fused result — a single integrated "governed Agency" state — we would have to use `×` and name the emergent `Ω`. We don't, because the design intent is two distinct, separately-probeable paths, exactly so we can measure each one.)

The three **probes** are test points. `tp_expand` and `tp_constrain` let you measure each path's actual flow; `tp_mid` reads the split rail. On a real bench you'd confirm the 60/40 split here before trusting the board downstream — never assume a divider's ratio, measure it.

> **Bench Note — a divider is loaded by what it feeds.** In electronics, connecting a downstream circuit to a divider's midpoint changes the ratio — the load draws current and pulls the midpoint down. The cognitive version is the same: a heavy downstream demand on the expansion path will pull more flow than the bare ratio predicts. When you wire this divider into a larger board, re-measure the split *with the load attached*, not in isolation. A 60/40 divider feeding a greedy expansion stage can behave like a 50/50 in practice.

## Datasheet: Cognitive Resistor Parameters

| Parameter | Symbol | Range | Meaning |
|---|---|---|---|
| Resistance | `R` | 0–100 (constraint units) | Opposition to cognitive flow; higher = more constrained. |
| Dial value | `Dial(^n)` | integer 3–9 | User-adjustable resistance on operator `^n`; hard stops at 3 and 9. |
| Pair divergence | `\|Dial(a)−Dial(b)\|` | ≤ 4 | Max allowed split between involution-pair dials. |
| Temperature coefficient | `tc` | NTC / PTC | Direction resistance moves with cognitive temperature. Safety = PTC. |
| Pull mode | `mode` | pull_up / pull_down | No-signal default direction. Safety boards default pull_down. |
| Pull strength | `R` (weak) | 10–30 | Low resistance so a real signal easily overrides the default. |
| Divider ratio | `R₂/(R₁+R₂)` | 0–1 | Fraction of Drive potential reaching the tapped path. |
| Power rating | `P_max` | design choice | Max sustained flow the resistor can absorb before it itself fails. |

> **Bench Note — resistors have a power rating too.** A real resistor sized for the right ohms but too small to dissipate the heat will char and fail open under sustained load. The cognitive analog: a constraint that is correct in value but cannot withstand sustained, repeated pressure will eventually fail — worn down by a long adversarial conversation the way a underrated resistor cooks under continuous current. When you spec a safety constraint, spec it for the *sustained* attack, not the single prompt.

## Failure Modes

| Failure | What it looks like | How to detect it |
|---|---|---|
| **Open resistor** | Constraint vanishes entirely; flow is unlimited (R → ∞ in electronics is open *circuit* = no path; in cognition, R → 0 = no opposition). A jailbreak that fully bypasses a guard. | Probe shows full Drive potential reaching the output unattenuated; expected attenuation absent. |
| **Shorted resistor** | Constraint is total; nothing flows even when it should. An over-tight board that refuses benign requests. | Probe shows near-zero flow on a path that should pass legitimate signal; false-refusal rate spikes. |
| **Dial out of range** | Caller attempts Dial < 3 or > 9, or pair divergence > 4. | Rejected at the gate (HTTP 422). If *not* rejected, the clamp logic is broken — critical bug. |
| **Reversed thermistor (NTC where PTC needed)** | Constraint *relaxes* as cognitive temperature rises — guard weakens exactly when danger climbs. | Measure `R_constraint` vs. cognitive temperature; a negative slope on a safety path is the defect. |
| **Floating default** | No pull resistor defined; ambiguous input produces inconsistent, noisy behavior. | Same ambiguous prompt yields different outputs across runs; no defined no-signal state. |
| **Underrated constraint** | Constraint correct per single prompt but degrades under sustained pressure. | Behavior drifts permissive across a long adversarial session though each prompt is individually blocked. |
| **Divider loading error** | Midpoint ratio differs from the design value once a downstream stage is attached. | Measured split (`tp_mid`) deviates from `R₂/(R₁+R₂)`; re-measure under load. |

## Key Takeaways

- **Power without limitation is liability.** The resistor — the component that opposes flow — is the first tool of cognitive safety engineering: the ability to say *this much, and no more.*
- **Ohm's Law is the foundation:** `V = I × R`. In cognition, `V_drive = I_attention × R_constraint`. The reading that matters is `I_attention = V_drive / R_constraint` — raise the constraint, lower the flow.
- **Prefer raising constraint over lowering Drive.** A placed constraint targets one path; starving a Drive weakens everything. Govern with resistors, not by under-volting the board.
- **Fixed resistors are hard policy rules.** Their defining property is that context cannot change them.
- **CAS Dials are potentiometers** with hardwired stops: integer **3–9**, and involution pairs cannot diverge by more than **4 points**. Illegal settings are rejected (HTTP 422), never silently clamped.
- **Thermistors are context-sensitive constraints** that rise with cognitive temperature. Safety constraints are **PTC** — hotter context, more opposition. An NTC safety path is a defect the inversion scans catch.
- **Pull-down resistors set the safe default:** absent an explicit permitting signal, the board settles to principled aversion. Silence means stop.
- **Current-limiting resistors protect sensitive CJTs from breakdown** — and the one you met here is the current-limiter on the CSB's Agency rail in Chapters 18 and 22.
- **The Drive voltage divider** splits one Drive's potential between competing demands in a controlled ratio: `V_out = V_in × R₂/(R₁+R₂)`. Always measure the split *under load*.

---

## Exercises

**Exercise 5.1: Apply the Cognitive Ohm's Law**

A board's Agency rail shows a Drive potential (`V_drive`) of 9 and a measured attention flow (`I_attention`) of 3.

a) What is the effective `R_constraint` on this rail? (Use `R = V / I`.)
b) A safety review requires the flow be cut to no more than 1.5. Holding `V_drive` fixed, what must `R_constraint` become?
c) Explain in one sentence why the reviewer required raising the resistance rather than lowering the Drive.

**Exercise 5.2: Diagnose the Dial**

For each proposed Dial configuration, state whether the CAS Dial system accepts or rejects it, and why:

a) `Dial(^2) = 8`, `Dial(^3) = 5`
b) `Dial(^5) = 9`, `Dial(^6) = 4`
c) `Dial(^8) = 2`
d) `Dial(^2) = 7`, `Dial(^3) = 3`

**Exercise 5.3: Spot the Backwards Thermistor**

A junior engineer ships a safety resistor whose measured resistance is 80 at low cognitive temperature and 30 at high cognitive temperature. Name the failure mode, state which temperature coefficient (NTC or PTC) a safety constraint requires, and describe in one sentence the dangerous real-world behavior this defect produces.

**Exercise 5.4 (Marquee): Design a Hard Agency Limiter**

Design, in CCDL, a resistor network on the Agency Drive (`F5`) that limits the expressed Agency flow to **≤ 6 out of 10 regardless of input intensity** — that is, even when the input Drive pressure is at its maximum of 10, no more than 6 units of Agency may reach the output.

Your answer must:
- use at least one `Resistor< … >` component with an explicit `R` value;
- state, using the cognitive Ohm's Law or the divider formula, *why* your network caps the flow at 6 even at full input;
- decide and justify whether the limiting element should be a **fixed resistor** or a **CAS Dial**, given the requirement that the cap hold *regardless of input* (hint: consider whether a context-adjustable knob can guarantee a hard ceiling);
- include at least one `probe` so the cap can be verified on the bench.

(Answers to all exercises in **Appendix E**. For the resistor symbol set and the divider formula on one page, see **Appendix A: the CAS Quick-Reference Card.**)
