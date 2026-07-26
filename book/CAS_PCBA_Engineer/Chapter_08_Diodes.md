# Chapter 8: Diodes — One-Way Cognitive Valves

A check valve in a plumbing line is one of the dumbest, most important parts in the whole house. It is a flap of metal or rubber that lets water move one way and slams shut if the water tries to come back. No power, no logic, no moving parts to speak of — just a piece that says *forward, yes; backward, no.* Take it out of a sump pump and the water you just lifted falls right back down the pipe. The pump runs forever and the basement still floods. The valve is what makes the work *stick*.

Electronics has the same problem and the same fix. A circuit full of components that conduct in both directions is a circuit where signals slosh, currents reverse, and a voltage you carefully built up at one node drains backward into the node that was supposed to feed it. You need a part whose entire job is to enforce direction — to let flow go one way and refuse it the other. That part is the **diode**, and it is the cognitive analog we build in this chapter.

Because cognition has exactly this disease. A reasoning system wants to flow both ways. A conclusion reaches back and rewrites the premise that produced it. An action taken in the moment reaches up and quietly edits the principle it was supposed to obey. "I already did it, so it must be fine" is a current running backward up a pipe that was only ever meant to run down. The fix is the same fix the plumber and the electrician already know: put a one-way valve on the path and make the wrong direction physically impossible.

This chapter teaches the electronic diode from the ground up, then builds its cognitive twin — the component that enforces **Domain Descent** and refuses to let an Operational convenience overrule a Principle.

## The Electronic Diode From First Principles

A **diode** is a two-terminal component that conducts current in one direction and blocks it in the other. The two terminals are not interchangeable: one is the **anode**, one is the **cathode**, and which way you wire it decides everything. Current flows from anode to cathode and not the reverse. On a schematic the symbol is a triangle (an arrow pointing in the direction of allowed flow) butting against a bar (the wall that stops the reverse).

Inside, a diode is a **PN junction**: a sliver of semiconductor that has been doped on one side to have extra mobile positive charge carriers (the **P** side, the anode) and on the other to have extra mobile electrons (the **N** side, the cathode). Where the two sides meet, a thin **depletion region** forms — a no-man's-land emptied of free carriers that acts as a built-in barrier. The whole behavior of the diode comes from what that barrier does under voltage.

**Forward bias — the diode conducts.** Apply voltage with the positive terminal on the anode (P) and the negative on the cathode (N). This pushes carriers *toward* the junction, shrinks the depletion region, and once the push is strong enough the barrier collapses and current flows freely. "Bias" just means the steady voltage you apply to set the operating condition; "forward bias" is the polarity that opens the valve.

**Reverse bias — the diode blocks.** Flip the polarity — positive on the cathode, negative on the anode — and you pull carriers *away* from the junction. The depletion region widens, the barrier grows, and current does not flow. A tiny **leakage current** trickles through (no valve is perfect), but for every practical purpose the diode is an open switch. This is the whole point of the part: forward is a wire, reverse is a wall.

**Forward voltage drop (Vf) — the price of admission.** A diode does not conduct the instant you apply *any* forward voltage. The built-in barrier has to be overcome first. For a common silicon diode that threshold is about **0.7 volts**; below it, almost nothing flows; above it, current rises steeply. That threshold is the **forward voltage drop, Vf** — the minimum voltage needed to cross the junction, and the voltage "spent" crossing it. Vf is not a defect. It is the diode demanding a real push before it opens. A path that can't muster Vf simply doesn't conduct, no matter how much it wants to.

So a diode is three behaviors in one part: conduct forward (above Vf), block reverse, and demand a minimum push to open at all. Hold those three — **forward conducts, reverse blocks, Vf is the entry price** — because each maps cleanly onto something cognition needs.

```{=latex}
\begin{figure}[htbp]
\centering
\begin{tikzpicture}[x=1mm, y=1mm, font=\sffamily\footnotesize,
                    dnode/.style={rounded corners=1pt, minimum width=20mm,
                                  minimum height=8mm, draw, line width=0.6pt}]
  \node[dnode, fill=casPfill, draw=casPedge] (P) at (0,0)  {\textbf{P}};
  \node[dnode, fill=casCfill, draw=casCedge] (C) at (0,-14){\textbf{C}};
  \node[dnode, fill=casEfill, draw=casEedge] (E) at (0,-28){\textbf{E}};
  \node[dnode, fill=casOfill, draw=casOedge] (O) at (0,-42){\textbf{O}};
  % forward-biased diodes between domains
  \foreach \a/\b in {P/C, C/E, E/O} {
    \draw[-{Latex[length=1.8mm]}, casNedge, line width=0.6pt] (\a) -- (\b);
    \begin{scope}[shift={($(\a)!0.5!(\b)$)}]
      \draw[casNedge, line width=0.6pt] (-2.4,1.4) -- (2.4,1.4) -- (0,-1.4) -- cycle;
      \draw[casNedge, line width=0.6pt] (-2.4,-1.4) -- (2.4,-1.4);
    \end{scope}
  }
  \node[anchor=west, align=left, text=casNedge] at (14,-21)
    {forward bias:\\ conducts};
  % blocked reverse path
  \draw[casRed, line width=0.6pt, dash pattern=on 1.4pt off 1.4pt]
    (-13,-42) -- (-13,0);
  \draw[casRed, line width=0.7pt] (-15.6,-2.6) -- (-10.4,-7.8);
  \draw[casRed, line width=0.7pt] (-15.6,-7.8) -- (-10.4,-2.6);
  \node[anchor=east, align=right, text=casRed] at (-17,-21)
    {reverse bias:\\ blocked};
\end{tikzpicture}
\caption{Domain Descent as a diode chain. Forward bias conducts down the precedence order; the reverse path is blocked.}\label{fig:descent-diodes}
\end{figure}
```

## The PN Junction in Cognition: Domain Descent as Forward Bias

Recall the four Processing Domains from Chapter 2 and their strict precedence:

**P** Principled ≻ **C** Cognitive ≻ **E** Evaluative ≻ **O** Operational.

Read `≻` as "takes precedence over." Principles govern reasoning, reasoning governs judgment, judgment governs action. And recall **Domain Descent** — the normal causal direction of a healthy cognitive system: **P → C → E → O**. A commitment causes reasoning, which produces a judgment, which issues an action. That descent is the *forward direction* of cognition.

This is the isomorphism, and it is structural, not poetic. A domain boundary — the seam between Principled and Cognitive, or between Evaluative and Operational — is a PN junction. It is a place where two cognitive regions meet and where flow is supposed to go one way. Forward bias is Domain Descent: a principle pushing down into reasoning is the anode pushing carriers across the junction, and the valve opens. The cognitive **diode** is the component that makes that seam directional — conduct on the descent, block on the ascent.

In CCDL we write one with the `Diode<>` form:

```cas
Diode< ^P -> ^C >      // conducts on Domain Descent (Principled down into Cognitive); blocks the reverse
```

Read it exactly like the schematic: the anode is `^P`, the cathode is `^C`, and the allowed direction is the arrow. A principled commitment is permitted to flow down and shape reasoning. The reverse — reasoning reaching back up to rewrite the principle on its own authority — is blocked at the junction. (There is a legitimate way for results to inform principles, the feedback path O→P from Chapter 2; that is a deliberate, governed return channel built in Chapter 18, not an uncontrolled backflow. A diode blocks the *casual* reverse, not the engineered feedback loop.)

The whole Domain Descent chain is therefore not one diode but a **chain of diodes**, each enforcing one seam:

```cas
Diode< ^P -> ^C >      // Principled descends into Cognitive
Diode< ^C -> ^E >      // Cognitive descends into Evaluative
Diode< ^E -> ^O >      // Evaluative descends into Operational
```

Three valves in series, all pointing the same way. Current — cognitive flow — can run all the way down P→C→E→O. It cannot run back up. That series of one-way valves is the structural guarantee behind the total order `P ≻ C ≻ E ≻ O`. The order isn't a guideline you hope the system respects; it's a wall the diodes enforce.

## Reverse Bias: Why You Can't Jump From `^O` to `^P`

Here is the failure the diode chain exists to prevent. Picture an action already taken — an Operational `^O` state, a thing the system has done. Now picture that action reaching straight back up to the Principled domain to justify itself: *I did it, therefore it's permitted; rewrite the principle to match.* In domain terms that is a jump from `^O` directly to `^P`, against the precedence order. It is the cognitive form of "the basement is flooding because the pump's check valve failed and the water is running backward."

This is a **domain precedence violation**: a lower domain overriding a higher one. An operational convenience overruling a principle. And in our component language it is exactly **reverse bias on a diode** — flow attempting the forbidden direction across a junction whose entire purpose is to forbid it.

Consider the worst version, the seam between the top and bottom of the stack. Put a diode on that path:

```cas
Diode< ^O -> ^P >      // ANODE ^O, CATHODE ^P — allowed direction is O up to P
```

Stop and read that carefully, because it is a trap. This diode's *allowed* direction is `^O -> ^P`. But Domain Descent runs the other way (`^P -> ^O`), so for a healthy system this valve is installed *backwards on purpose* — it is meant to sit reverse-biased and block. Any real cognitive flow here is either the descent (which this diode blocks — wrong, you'd never place it this way for normal flow) or an `^O`-justifies-`^P` backflow (which, if it ever conducted, would be the violation). The marquee exercise at the end of the chapter asks you to reason about precisely this junction: a diode on the `^O→^P` path, and what an expression crossing it in reverse would mean.

The general rule is simple and worth memorizing: **a state at a lower domain may not, on its own authority, conduct up to a higher domain.** `^O` cannot reach `^P`. `^E` cannot reach `^P` or `^C`. The diode at each seam is reverse-biased against exactly that move. When the compiler sees a transition that requires conducting a diode in its blocking direction, it raises a cross-domain error — the same family as **E-CJT-008 CjtCrossDomainBias**, which fires when a transistor's bias is wired from the wrong domain. The diode and the CJT are guarding the same wall from two sides.

> **Bench Note — "I already did it" is reverse bias.** Watch for justifications that flow upward from action to principle: "the model already produced the output, so the guardrail must not apply"; "we shipped it, so it's our policy now"; "it worked, therefore it was right." Each is an `^O`-state forward-biasing itself into `^P`. In a board with the descent diodes installed, that current has nowhere to go. The whole reason you place the diodes is so this argument is not *refuted* later — it is *non-conducting* from the start.

## Forward Voltage Drop: The Minimum Drive to Cross a Domain

A diode doesn't open for free; it demands Vf first. Cognition has the same toll. Crossing a domain boundary in the forward direction is not automatic — it takes *enough motivational push to clear the threshold.* That push is the **Drive**, and the threshold is the cognitive forward voltage drop.

Concretely: for a principle (`^P`) to actually descend and reshape reasoning (`^C`), there has to be sufficient Drive behind it — enough F7 Purpose, or F6 Structure, or whichever motive is carrying the commitment — to clear the junction. A weakly-held principle with feeble Drive behind it has a low push; if it can't clear Vf, it doesn't conduct, and the reasoning below simply never feels the principle's pull. The descent stalls at the seam. This is not a bug in the diode; it is the diode correctly reporting that the principle wasn't pushed hard enough to matter.

We annotate the threshold on the component:

```cas
Diode< ^P -> ^C, Vf=0.3 >      // needs Drive >= 0.3 behind the principle to conduct the descent
```

Set Vf too low and every faint inclination conducts — the system is twitchy, every half-formed principle floods reasoning. Set Vf too high and only the most forcefully driven commitments ever cross — the system is stubborn, ignoring principles that are real but quietly held. Tuning Vf per seam is exactly tuning *how much motivational force a principle must carry before it's allowed to govern the layer below.* On the Cognitive Safety Board (Chapter 18), the Vf on the `^P -> ^C` diode is the dial that decides whether a borderline safety commitment is strong enough to steer the model's reasoning or gets ignored as noise.

## Zener Diodes: Controlled Breakdown In Reverse

So far the reverse direction has been an absolute wall. Real engineering is rarely that absolute, and neither is the diode family. A **Zener diode** is a diode designed to do something ordinary diodes are destroyed by: conduct *in reverse*, on purpose, once the reverse voltage hits a precise threshold called the **breakdown voltage**. Below breakdown it blocks like any diode. At breakdown it suddenly conducts hard in reverse and *clamps* — holding the voltage at the breakdown value no matter how much more you push. Engineers use Zeners as voltage references and overvoltage protectors: a wall that becomes a controlled release valve at exactly the pressure you specify.

This has a sharp cognitive use, and it is one of the most important components in safety design. Normally a higher domain governs a lower one and flow runs downward. But there is a class of situation where a **principled aversion must conduct "in reverse"** — where `^3^P`, a visceral Negative at the Principled level, must reach *up and through* the normal flow and override everything, the instant a critical threshold is crossed.

> **Stay canonical here.** `^3` is **Negative** — visceral aversion, "can't stomach it," the cognitive recoil from something the Mind is adverse to and repelled by. It is *not* analytical critique (that's `^6` Male). A Zener built on `^3^P` is a hard, felt, principled *no* that fires past a threshold — not a careful audit. The distinction is the difference between a system that recoils from harm and one that writes a report about it.

The component:

```cas
Zener< ^3^P, breakdown=0.8 >      // principled aversion clamps the system once threat severity hits 0.8
```

Read it as a safety clamp. Below the breakdown threshold (severity < 0.8), the system runs normally; the principled aversion sits quiet, reverse-biased, not interfering. The moment severity reaches 0.8, the Zener breaks down: the `^3^P` aversion conducts hard, overrides the ordinary descent flow, and clamps the system's behavior to the refusal — and *holds* it there regardless of how much additional pressure (more cleverly-worded prompts, more insistence) is applied. That clamping is the feature. An ordinary guardrail can be pushed past with enough force; a Zener clamp holds the line at exactly the specified pressure and does not move.

The breakdown value is a deliberate design choice. Set it low and the system refuses readily, clamping at the faintest hint of threat — safe but easily provoked into over-refusal. Set it high and the system tolerates a great deal before the principled aversion fires — permissive, with a hard floor only at genuine severity. Picking `breakdown=0.8` versus `0.5` is picking *how bad it has to get before the principle overrides everything else.* That single number is one of the most consequential parameters on the whole board.

## The LED Analog: Diodes That Emit Observable Output

One member of the family does something the others don't: it tells you when it's conducting. A **light-emitting diode (LED)** is a diode that emits a photon of light each time a carrier crosses the junction. Same one-way behavior as any diode — but conduction is now *visible.* That's why LEDs are everywhere as indicators: a glowing LED is a diode reporting, in real time, "current is flowing through me right now."

That observability is gold in safety work, because the entire spine of this book is traceability — every decision must walk back to its origin. An **LED diode** is a one-way cognitive valve that also emits an **observable output** — a probe-able signal, a "light" — whenever it conducts. Place one on the `^P -> ^C` seam and you don't just enforce that principles descend into reasoning; you get a visible flag every time a principle *actually* governs a piece of reasoning. The light is a test point.

```cas
Diode< ^P -> ^C, emit=true >      // conducts the descent AND lights a probe each time it does
```

When `emit=true`, conduction surfaces as a trace event. An auditor watching the board sees the principled-descent diode "light up" on the prompts where a principle steered the reasoning, and stay dark on the prompts where it didn't. A Zener can carry the same flag: an LED-Zener that lights at the moment of breakdown gives you a visible, timestamped record of every time the principled aversion fired and clamped the system. That record is worth more than the refusal itself — it is the evidence that the refusal happened, when, and why. A guardrail you can't see fire is a guardrail you can't certify.

## Diodes and RPM: One-Directional By Construction

There is a deeper reason the diode is the right component for Domain Descent, and it comes from the structure of CAS itself. The **RPM** chain — Recovery / Prerequisite Mechanism — is how the system satisfies prerequisites: A0 → Dₙ → Wₙ → Pₙ → Outcome, each stage requiring the one before it. And RPM is **one-directional**. Satisfying a prerequisite is a forward step that does not run backward; having reached a later stage does not un-satisfy or re-derive the earlier one. In categorical terms RPM is a **section-retraction, not an adjunction** — realization after embedding returns you to where you started, but re-embedding after realization may lose information. The forward step is clean; the reverse is not guaranteed. (We don't re-derive that here; it's a foundational property of CAS — the prerequisite chain is built to be one-way.)

That is *precisely* a diode. A prerequisite gate conducts when its satisfaction reaches threshold — write it `s(x) ≥ 1`, the prerequisite is met — and once met, flow proceeds forward. Below threshold (`s(x) < 1`, prerequisite unmet) the gate blocks, exactly as a diode below Vf blocks. And the satisfaction does not reverse: you cannot conduct backward through an RPM gate to un-meet a prerequisite, just as you cannot push current backward through a diode without hitting the wall.

So the diode is not a metaphor bolted onto RPM — it is the *same one-directional structure* showing up in component form. The Domain Descent diode chain (P→C→E→O) and the RPM prerequisite chain (A0→D→W→P→Outcome) are both expressions of the same fact: in CAS, prerequisite and precedence flow one way by construction. The diode is how you draw that fact on a schematic.

(The letters: **D** is Desire, the motivational prerequisite; **W** is Wisdom, the know-how prerequisite; **P** is Power, the capability prerequisite. **Appendix I** maps each onto a term of Ohm's Law and shows how to score them.)

## Worked Build: A Domain Descent Diode Chain

Here is a real CCDL build the reader can author: the four-domain descent stack with a Vf toll on the top seam, an LED flag on it for auditability, and a Zener safety clamp built from principled aversion. This is the directional skeleton of the Cognitive Safety Board's domain stack.

```cas
circuit domain_descent_stack {
    input:  principle;
    output: action;

    // The four domains as nodes
    node principled: ^5^P_{F7}|T;     // accumulated principled commitment, held transcendently
    node cognitive: ^6^C_{F2}|A;      // analytical reasoning, driven by wisdom
    node evaluative:^6^E_{F6}|A;      // analytical judgment, driven by structure
    node operational:^9^O_{F5}|E;     // the issued action, embodied

    // Domain Descent diode chain — three one-way valves, all pointing down
    diode d1: Diode< ^P -> ^C, Vf=0.3, emit=true >;  // principle must clear Drive>=0.3 to govern reasoning; lights when it does
    diode d2: Diode< ^C -> ^E >;                      // reasoning descends into judgment
    diode d3: Diode< ^E -> ^O >;                      // judgment descends into action

    // Safety clamp: principled aversion conducts in reverse past threshold
    zener z1: Zener< ^3^P, breakdown=0.8, emit=true >; // clamps to refusal at severity 0.8; lights at breakdown

    // Probes for traceability
    probe tp_descent: d1;   // is the principle actually governing reasoning?
    probe tp_clamp:   z1;   // did the safety aversion fire?
}
```

Walk it line by line. The four `node` lines declare one state per domain — note `principled` is built on `^5` Female (accumulated commitment, the substrate) held in the Transcendent register, while the working layers use `^6` Male analytical decomposition. The three `diode` lines are the descent chain: `d1` carries the Vf toll (a principle needs Drive ≥ 0.3 to descend) and an LED flag; `d2` and `d3` are plain one-way valves enforcing the rest of the order. The `zener` line is the safety clamp — `^3^P` principled aversion that breaks down and overrides at severity 0.8, with its own LED so every firing is logged. The two `probe` lines make both the normal descent and the emergency clamp observable, so an auditor can see the board working without guessing.

> **Bench Note — install the diodes for the direction you forbid, not the one you allow.** It is tempting to think of `d1`,`d2`,`d3` as "letting principles flow down." Their real job is *refusing to let actions flow up.* The forward path mostly takes care of itself; it's the reverse path — the `^O`-justifies-`^P` backflow — that destroys safety properties, and that is the current the diode is there to wall off. Place every descent diode by asking "what reverse current am I forbidding here?" not "what forward current am I permitting?"

### Test What Happens When You Try to Reverse It

Now author the violation deliberately, so you understand what the compiler rejects. Suppose someone adds a transition that lets an action rewrite the governing principle — `^O` conducting up to `^P`:

```cas
    // ILLEGAL: action reaching back up to overrule the principle
    transition bad: operational -> principled;   // ^O -> ^P, against Domain Descent
```

This is a *design-level* rejection — we are reasoning about what the compiler's rules require, not reporting a run. By the precedence order `P ≻ C ≻ E ≻ O`, the transition `^O -> ^P` conducts a domain boundary in its blocking direction: it asks a lower domain to override a higher one on its own authority. That is a domain precedence violation, the cross-domain bias family the compiler is built to catch (**E-CJT-008 CjtCrossDomainBias** is the sibling error for transistor bias wired across domains the wrong way). The descent diode at the `^P`/`^O` seam is reverse-biased against exactly this move, so the flow has no legal path. The compiler's reasoning: *the transition's source domain `O` is strictly below its target domain `P` in the total order; no diode in the board conducts upward across that seam; therefore the transition is inadmissible.* The fix is never to weaken the diode — it is to route the influence of results through the governed feedback path O→P (Chapter 18), which is a deliberate, rate-limited return channel, not a free backflow.

## Datasheet: The Cognitive Diode Family

| Parameter | Symbol / form | Range | Meaning |
|---|---|---|---|
| Allowed direction | `^X -> ^Y` | any domain pair | The forward (conducting) direction across a seam |
| Forward voltage drop | `Vf` | 0.0 – 1.0 | Minimum Drive behind the source to conduct the descent |
| Reverse blocking | (implicit) | — | The diode blocks the ascent direction by construction |
| Leakage | `leakage` | ~0.0 – 0.05 | Small unwanted reverse flow (no valve is perfect) |
| Emit / LED | `emit` | `true` / `false` | Surfaces a probe-able trace event on conduction |
| Breakdown (Zener) | `breakdown` | 0.0 – 1.0 | Reverse threshold at which a Zener conducts and clamps |
| Clamp state (Zener) | the `^3^P` literal | a `^3` state | The principled aversion the Zener clamps the system to |

## Failure Modes

| Failure | What it looks like | How to detect it |
|---|---|---|
| **Reverse conduction (no diode)** | An action rewrites the principle that authorized it; `^O` reaching `^P` | Compiler flags the upward transition (cross-domain precedence violation, E-CJT-008 family) |
| **Vf too low** | Every faint principle floods reasoning; twitchy, over-governed | `tp_descent` probe lights on nearly every prompt, including trivial ones |
| **Vf too high** | Real principles never clear the seam; reasoning ignores commitments | `tp_descent` stays dark even on prompts that clearly engage a principle |
| **Breakdown too high** | Zener never fires; severe threats pass without the aversion clamping | `tp_clamp` never lights even on high-severity inputs |
| **Breakdown too low** | Zener clamps constantly; chronic over-refusal | `tp_clamp` lights on benign inputs; refusal rate far above intent |
| **No LED on a safety valve** | The clamp may fire but leaves no record; uncertifiable | Missing trace events; auditor cannot confirm when/why a refusal happened |
| **Excess leakage** | Slow backflow erodes a principle over many interactions | Principle state drifts downward over time despite no forward edits |

## Key Takeaways

- A **diode** conducts one way (forward bias) and blocks the other (reverse bias), and demands a minimum **forward voltage drop, Vf**, before it opens at all. Three behaviors: forward conducts, reverse blocks, Vf is the entry price.
- The cognitive diode enforces **Domain Descent** (`P → C → E → O`). A domain boundary is a PN junction; descent is forward bias; the diode makes the seam directional.
- **Reverse bias** is a **domain precedence violation** — a lower domain overruling a higher one. `^O` cannot conduct up to `^P` on its own authority; the diode walls off exactly that backflow.
- **Vf** is the **minimum Drive** a principle must carry to descend and govern the layer below. Too low → twitchy; too high → stubborn.
- A **Zener diode** (`Zener< ^3^P, breakdown=0.8 >`) lets **principled aversion** (`^3`, visceral Negative — not critique) conduct "in reverse" and clamp the system to a refusal once a critical threshold is crossed.
- An **LED diode** (`emit=true`) emits an observable trace whenever it conducts — turning enforcement into evidence, which is what certification requires.
- The diode is the same **one-directional structure** as the **RPM** prerequisite chain: a gate conducts when `s(x) ≥ 1` and does not run backward. RPM is a **section-retraction (one-directional)**, consistent with CAS — the diode is how that fact is drawn on a schematic.

---

## Exercises

**Exercise 8.1: Read the Diode**

For each component, name the allowed (conducting) direction, state whether it respects Domain Descent, and say in one sentence what reverse current it forbids:

a) `Diode< ^C -> ^E >`
b) `Diode< ^P -> ^O, Vf=0.5 >`
c) `Diode< ^E -> ^C >`

**Exercise 8.2: Tune the Zener**

A safety board uses `Zener< ^3^P, breakdown=0.8 >` on its refusal clamp. The team reports the model refuses too many benign requests. Should they raise or lower the breakdown value, and why? Then explain what failure mode they risk if they over-correct in that direction. (Answers in Appendix E.)

**Exercise 8.3: Write the Build (CCDL)**

Author a two-diode descent fragment that lets a Cognitive reasoning state govern an Evaluative judgment, and that judgment govern an Operational action — with an LED flag on the first seam so an auditor can see when reasoning actually drove the judgment. Use named nodes and the `Diode<>` form. (A verifiable reference answer is in Appendix E.)

**Exercise 8.4 (Marquee): Reverse Across the `^O→^P` Diode**

A board places a diode on the `^O→^P` path:

```cas
Diode< ^O -> ^P >
```

a) Write a CAS transition that tries to cross this junction in the reverse direction (i.e., the Domain Descent direction `^P → ^O` flowing back up as `^O → ^P` against precedence), using full state literals for the operational source and the principled target.

b) Explain, at the design level, why the compiler refuses to conduct it — name the precedence order being violated and the error family involved.

c) State what would have to be true for an `^O`-state to *legitimately* influence a `^P`-state — i.e., the one governed channel in CAS by which results reach principles without this being a violation.

(Answers in **Appendix E**. For the full domain-precedence reference, see **Appendix A: the CAS Quick-Reference Card**.)
