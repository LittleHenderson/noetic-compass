```{=latex}
\part[Foundations]{Foundations\\[0.45em]{\large\upshape The substrate, the notation, and the transistor at the centre of it}}
```

```{=latex}
\part[The Component Library]{The Component Library\\[0.45em]{\large\upshape Every part on the bench, with its datasheet and its failure modes}}
```

# Diodes — One-Way Cognitive Valves

*How the domain order is physically enforced, what a crossing costs, and the one lawful route back up*

---

A silicon diode is the cheapest part in the box. Two leads, a stripe painted on one end to tell you which way round it goes, and a single job: current passes this way and not that way. There is no logic in it. It does not decide whether this current deserves to pass. Below about seven-tenths of a volt forward it barely conducts; above that it conducts freely; reversed, it holds off hundreds of volts and passes almost nothing. That asymmetry is the whole device, and nearly every power supply you have ever plugged in is built on it.

Now a scene from the other bench.

An operator runs a working. It lands. Something in the world moves — a call comes, a door opens, a number goes up. Within a day the sentence in their mouth has changed from *that worked* to *this is what I am*. Nobody reasoned about it. Nothing was weighed. An operational result walked straight up into the Principled domain and installed itself as an identity claim, and the operator experienced this as insight.

That is a diode conducting backwards. It is the mechanism behind post-hoc rationalization, ideological capture, and every campaign in Chapter 15 — and the part that prevents it costs almost nothing and is almost never installed. This chapter is about that part.

[[FIGURE 8-A: Component symbol plate — the triangle-and-bar diode symbol, anode labelled "source domain", cathode "target domain", drawn three times as D1 ^P→^C, D2 ^C→^E, D3 ^E→^O with designator and Vf beside each; a fourth instance reversed and struck through, labelled "reverse-biased — blocked".]]

---

### 8.1 The Domain Descent Diode Chain: P→C→E→O

The four Processing Domains are strictly ordered (Chapter 2.3): **P ≻ C ≻ E ≻ O**. Causation runs down that order, and this is not a preference — the CCDL grammar enforces it. `×` may not ascend, which is why `^O × ^P` is not a circuit you can build wrong. It is a listing the compiler refuses.

The diode chain is what that grammar rule looks like as hardware.

```cas
// domain descent chain — three junctions in series
diode d1: Diode< ^P -> ^C > [Vf=0.7, I_R=0.02, V_BR=12.0];
diode d2: Diode< ^C -> ^E > [Vf=1.2, I_R=0.02, V_BR=10.0];
diode d3: Diode< ^E -> ^O > [Vf=2.0, I_R=0.02, V_BR=8.0];
```

Three diodes, not one. That choice is load-bearing. A single `Diode< ^P -> ^O >` would guard the endpoints and nothing else — `^C` and `^E` would sit inside the guarded span with no junction between them and the Principled domain, free to write upward at will. Each adjacent pair needs its own junction, because each crossing is a *different translation*.

- **D1, `^P -> ^C`.** A value becomes something to reason about. What arrives is not the principle but its cognitive image — the questions it raises, the arguments it licenses.
- **D2, `^C -> ^E`.** An analysis becomes a felt verdict. What arrives is not the argument but the weight it turned out to carry.
- **D3, `^E -> ^O`.** A verdict becomes behaviour. What arrives is not the judgment but the act, with the judgment's nuance stripped off.

You can shunt a junction in the forward direction. A `^P -> ^E` path — a principle producing a verdict with no reasoning between — does not ascend, so it is admissible, and it is exactly the circuit that produces zealotry: full-confidence conclusions with no analytical stage that could ever have produced a different one.

**The forward drops sum.** With the values above, a principle must be driven at more than **0.7 + 1.2 + 2.0 = 3.9** on the drive scale before *any* operational output appears — before you even reach the constraint resistance of Chapter 4. This is the diode-corrected form of CAS Ohm's Law:

```
I_attention = ( V_drive − ΣVf ) / R_constraint
```

That correction explains what operators routinely misdiagnose as weakness. A person holding a real value at V_drive = 3.0 produces no action from it. Not a little action. None. The rail never clears the series drop. They are not insincere and not lazy; they are below the knee, and exhortation does not move a circuit that has not reached threshold. What moves it is more drive, or fewer junctions between the principle and the deed.

> **Bench Note — the forward drop is not waste. It is what makes the boundary exist.**
> A junction with Vf = 0 is a wire. Four domains connected by wires are not four domains; they are one domain wearing four labels, and every state in it is at once a principle, a thought, a feeling, and an act. That architecture has a familiar presentation: the person for whom disagreeing with an idea is indistinguishable from being attacked, because there is no drop between `^C` and `^E`. Tuning Vf is not tuning efficiency. It is tuning how separable principles are from behaviour, and setting it to zero deletes the distinction rather than optimising it.

[[FIGURE 8-B: The descent chain as a series string — V_drive rail at left feeding ^P, through D1 to ^C, D2 to ^E, D3 to ^O, down to ground; drops annotated 0.7, 1.2, 2.0 with total 3.9 bracketed at right; a dashed arrow from ^O back to ^P, struck through, labelled "reverse — blocked".]]

---

### 8.2 Forward Bias, Reverse Bias, and the Vf Threshold

**Forward bias** is the source domain sitting higher than the target by more than Vf. The junction conducts and the translation happens.

**Reverse bias** is the target domain sitting higher. The junction blocks — not perfectly. It passes a small reverse leakage `I_R`, specified here at 0.02: two percent of rated forward current passes backwards. That number is deliberately non-zero, and section 8.4 is the consequence.

The curve between them is not a step. It is exponential, and the region below the knee is where operators go wrong.

[[FIGURE 8-C: Characteristic curve for D1, one junction throughout — vertical axis I_attention, horizontal axis applied domain potential; exponential forward knee labelled Vf = 0.7; sub-threshold region shaded, annotated "conducting, but not working"; reverse quadrant with a flat leakage floor at I_R = 0.02; vertical breakdown cliff at V_BR = 12.0 annotated "non-recovering — not a Zener"; a ghosted second cliff at 8.0 labelled "D3 breaks here first — §8.2".]]

> **Bench Note — below the knee, the diode is not off.**
> A principle at V_drive = 0.6 against a Vf = 0.7 junction is still passing current. A trickle, orders of magnitude below working level, but present. This is why the value you cannot act on still tints everything faintly — the low-grade discomfort with a job you have not quit, the preference you would deny holding that shows up in every small choice anyway. Two consequences. "I have no opinion on that" is a claim about working current, not about conduction. And a principle just under the knee needs only a small drive increase to conduct properly, which makes below-knee states the cheapest things on a board to move. Look there before you reach for a CJT.

**What the drop actually costs.** The forward voltage lost at each junction is not friction to be engineered away. It is the signature of a *one-directional* translation. Recall section-retraction (Chapter 21.5): realization after embedding returns you where you started, but re-embedding after realization does not. Going down and coming back up does not restore the original. What the crossing discarded is gone, and Vf is the price paid to discard it. A junction that lost nothing would be reversible, and a reversible junction is not a diode.

**Reverse breakdown.** Push a large enough reverse potential across a junction and it conducts backwards. `V_BR` *rises* as you go up the chain — **8.0 at D3**, 10.0 at D2, 12.0 at D1 — and that gradient is the design, not an accident of the numbers. D3 faces the world, so D3 is where large uninvited potentials arrive, and D3 is deliberately the weakest junction in the string. An event at 9.0 breaks D3 and is stopped at D2. One at 11.0 takes D3 and D2 and is stopped at D1. Only an event past 12.0 reaches the Principled substrate.

Read the failure that way and the mechanism is a cascade, not a single crossing. A full-chain breakdown is an operational event driving backwards through all three junctions and recomposing `^5^P` — accumulated principled formation — without passing through `^6^C` decomposition. Formation changed, with no analytical stage anywhere on the path. A partial breakdown, arrested at D2 or D1, wrecks a junction and leaves the constitution intact. That is the entire reason the three numbers are not equal: setting them all to one value does not make the chain stronger, it deletes the ordering that decides which junction fails first, and the failure you then get is the expensive one.

These junctions do not recover. A Zener conducts in reverse at a specified voltage and returns to blocking; domain diodes are not Zeners, and after breakdown the junction leaks permanently at that point. Margin is the only defence, which is what the fuse and saturating refusal CJT of Chapter 24 exist to guarantee.

Stated plainly: this is circuit topology, not a person's health. Nothing here diagnoses or treats anything. If you or someone you work with is in real distress, that is a matter for a qualified clinician; no schematic substitutes for one.

---

### 8.3 Why You Can't Jump from ^O to ^P

Ascent is blocked. The interesting question is what happens when someone attempts it anyway, because the four possible answers look alike from outside and are not alike at all.

**1. Standoff — the diode working.** The attempt produces nothing. The operator did the thing and it changed nothing about who they are. This is correct behaviour, routinely misread as failure. It is a reverse-biased junction doing its only job.

**2. Leakage accumulation — the slow one.** Each attempt is blocked but leaks `I_R = 0.02` backwards. One event is negligible. Two hundred events integrate. Over a long operational history, unmanaged leakage produces a principled drift the operator cannot see, because no single crossing was large enough to notice. You cannot eliminate leakage, so you build a metered channel and audit it instead — which is section 8.4.

This is a *different* leakage from Chapter 7.3, where charge drains out of `^5` for want of `^7` Rhythm reinforcement. Diode leakage is signal creeping backwards across a domain boundary. Same word, different component, opposite direction.

**3. Breakdown.** Section 8.2. One event large enough and a junction conducts backwards — usually D3, the weakest, and there it stops. Only an event clearing all three ratings reaches `^P`.

**4. Counterfeit ascent — the common one.** Most apparent `^O -> ^P` ascent is not ascent. No junction was crossed and no current flowed. What happened is a **relabel**: the operator took a state whose literal was `^9^O` and began asserting it as `^9^P`, by fiat, in their own account of themselves. *It worked, therefore it is right.* The grammar has no statement that does this. There is no form that rewrites a state's domain field, and the only upward connection it will accept is the low-gain feedback of section 8.4 — so the relabel is not an illegal listing, it is an *unwritable* one. A mind has no compiler, though, and the relabel costs nothing.

The diagnostic is one question: **what crossed the junction?** If the honest answer is "nothing, I simply started saying it at the principled level," you have a relabel. Real feedback leaves a trace — a filtered signal, a time constant, a gain, a bias that moved measurably. A relabel has an assertion and nothing behind it.

Counterfeit ascent is the payload of Overton progression (Chapter 15). Norm-shifting campaigns cannot push ideas up the domain order any more than you can. They install an operational fact and supply the relabel ready-made, so the target performs the promotion and experiences it as their own conclusion.

An operator whose whole chain has inverted — action setting evaluation setting reasoning setting principle — is running this architecture backwards, and it presents as fluent post-hoc rationalisation at every stage. Chapter 25 covers inversion detection; the diode chain is where you look first.

---

### 8.4 The O→P Feedback Path — The Lawful Exception

Operational consequences *must* reach the Principled domain somehow. A principled substrate that never learns from outcomes is not principled but dogmatic, and its operator is unfalsifiable. So the chain is not the whole story. There is one lawful route up, and it does not go through a diode at all — it goes *around* the chain, through a filter and a low-gain feedback element.

```cas
// the lawful exception — O -> P, outside the diode chain
node ops_log:      ^9^O_{F5}|E;    // Below/Effect: what the operations actually produced
node trend:        ^9^O_{F5}|E;    // same literal — a filter changes time constant, not type
node constitution: ^5^P_{F7}|T;    // Female: the operator's accumulated principled formation

filter fb_lp: LowPass< in=ops_log, out=trend, tau=21.0 >;   // tau in days — three weeks
feedback trend -> constitution [β=0.05];
```

Three declarations and two wires. `trend` carries the same literal as `ops_log` on purpose: filtering an operational record does not promote it out of `^O`. Nothing in this fragment ascends. The upward move happens once, at the last line, into a bias.

Two parameters, defending against different things.

**β = 0.05 — low gain.** Gain sets how far the principled substrate moves per unit of sustained signal. At β = 0.05 it takes roughly twenty consistent periods of the same trend to move principles appreciably. That is the point: principles that move in one period are not principles. At **β = 0.5** a single filter period — three weeks of unusual outcomes, once they have cleared the filter — rewrites the constitution, and every board the operator runs afterwards is biased by the last one they ran. At **β = 0** the path is disconnected — no outcome corrects a principle, the operator cannot be wrong, and the safety architecture of Chapter 24 has nothing to update.

**τ ≥ 3 weeks — slow time constant.** τ sets what counts as a trend rather than a spike. At three weeks a single dramatic operation washes out entirely, and only sustained patterns reach the gain stage. At **τ = hours** you have built a fast path from action to principle — precisely the ascent the diodes exist to block, rebuilt by an operator who believed they were being adaptive. Shortening τ does not make the board responsive. It removes the diode.

**Why both.** Taken one at a time the defence collapses in a specific way. Low β with short τ: principles move slowly but track noise, so the operator drifts without ever being pushed. Long τ with high β: spikes are ignored, but a *sustained* input clears the filter and then hits full gain, so anyone who can afford three weeks of consistent pressure — any organised campaign of the kind Chapters 15 and 19 describe — moves those principles hard, through the front door. Gain bounds the magnitude any sustained input can produce; τ bounds which inputs qualify as sustained. Patience defeats a τ-only defence, intensity defeats a β-only defence, and neither parameter is optional.

> **Bench Note — the feedback arrives at the bias, never at the signal path.**
> The feedback terminates at `constitution`, the `^5^P_{F7}|T` accumulated-formation capacitor of Chapter 7.1 — not at the input of D1. That is the difference between a safety board and an oscillator. Feedback into a bias terminal trims the substrate the chain runs against, slowly, and settles. Feedback into the *signal path* is positive feedback around a gain stage, and it does what that always does: it runs away. Chapter 14 builds a hyperstition engine out of that runaway on purpose, with loop gain deliberately above unity. On a safety board it is a defect. An O→P path landing anywhere but a bias terminal is an oscillator someone mistook for a conscience.

[[FIGURE 8-D: The lawful O→P loop drawn outside the diode chain — from the ^9 operations log in ^O, into a lowpass block labelled τ ≥ 3 weeks, into a gain block labelled β = 0.05, ending at the bias terminal of the ^5^P capacitor; a callout there reads "arrives at the bias, never at the signal path"; a dashed line from the loop to the D1 input, crossed with an X.]]

[[FIGURE 8-E: Two-axis design map — τ horizontal (hours to years, log scale), β vertical (0 to 0.5) — four labelled regions: "dogma" along β→0, "reprogrammable" at short τ, "capturable by a patient adversary" at high β with long τ, and a shaded box at τ ≥ 3 weeks, β ≤ 0.05 marked "design target".]]

---

### Component and Parameter Table

Every value below is a **design choice**, stated as such, with the failure mode at other settings. None is a measurement.

| Ref | Component | Form | Parameters | Role | Failure at other values |
|---|---|---|---|---|---|
| **D1** | Domain diode | `Diode< ^P -> ^C >` | Vf=0.7, I_R=0.02, V_BR=12.0 | Value becomes reasoning | 0.2: conducts on noise — rumination. 3.0: values never examined |
| **D2** | Domain diode | `Diode< ^C -> ^E >` | Vf=1.2, I_R=0.02, V_BR=10.0 | Analysis becomes verdict | 0.3: no position without a feeling about it. 3.0: analysis, never a verdict |
| **D3** | Domain diode | `Diode< ^E -> ^O >` | Vf=2.0, I_R=0.02, V_BR=8.0 | Verdict becomes act | 0.5: impulsivity. 4.0: agrees, never acts |
| **ΣVf** | Series total | — | 3.9 | Floor on V_drive for any action | Below 3.9: no operational output |
| **FLT1** | Lowpass filter | `LowPass< in=…, out=…, tau=… >` | τ = 3 weeks (adept) to 6 months (novice) | Trend vs spike | τ = hours: the diode is removed |
| **FB1** | Feedback element | `feedback trend -> ^5^P_{F7}\|T` | β = 0.05 | Trims principled bias | 0.5: constitution rewritten in one filter period. 0: unfalsifiable operator |

Two figures on τ, and they are not the same figure. **Three weeks is this chapter's design default**, chosen for an operator with a settled constitution. Chapter 24.5 scales τ by experience — 3–6 months for a novice, 1–4 weeks for an adept — and sets a separate absolute floor at one week, below which no operator of any experience may go. Use the 24.5 band to pick your value; use the one-week floor as the line that is never crossed for any reason. The three-week default sits inside the adept band, which is why every other board in this book that inherits the path inherits 21 days with it.

The `V_BR` gradient is one design choice stated three times: 8.0 / 10.0 / 12.0 ascending, so the exposed junction fails first and the constitution is behind two more junctions with more margin each. Equal values across the string remove the ordering, not the risk.

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Shorted junction** | Vf → 0 at one diode | Adjacent domains behave as one; disagreement reads as attack (D2); acting reads as deciding (D3) | Restore the drop; the boundary *is* the drop |
| **Open junction** | Vf raised past the rail | Domain below the break is dark; principles never reach action (D3) or thought (D1) | Lower Vf or raise V_drive; check ΣVf first |
| **Reverse breakdown, arrested** | Event exceeds D3's V_BR but not D2's | A junction permanently leaky; constitution intact; operator feels "shaken, not changed" | Nothing repairs the junction. Restore margin upstream and accept the new leakage figure at TP3 |
| **Reverse breakdown, full chain** | Event exceeds all three V_BR | Principles changed in one pass, no analytical stage anywhere in the account | Margin, not repair — no junction recovers. Fuse and saturating refusal upstream (Chapter 24.2–24.3) |
| **Excess leakage** | I_R above spec, or blocked attempts integrating | Slow principled drift with no identifiable cause | Route feedback lawfully and meter it (8.4); audit the log |
| **Counterfeit ascent** | State relabelled `^9^O` → `^9^P` by assertion | "It worked, so it is right"; no filter, no τ, no gain | Ask what crossed the junction; if nothing did, reject the claim |
| **Bypass shunt** | Forward path skipping a junction, e.g. `^P -> ^E` | Confident verdicts with no analytical stage behind them | Remove the shunt; route through D1 and D2 |
| **Feedback τ too short** | τ below the operator's band | Board tracks the last operation; settled principles move week to week | Lengthen τ into the Chapter 24.5 band for that operator, and never below the one-week floor |
| **Feedback into signal path** | Loop terminates at D1 input, not at bias | Escalation; each operation makes the next one larger | Re-terminate at the `^5^P` bias terminal |

---

### Test Points

| TP | Node | What it reads | Expected |
|---|---|---|---|
| **TP1** | across D1, conducting | Forward drop, `^P -> ^C` | ≈ 0.7. Zero = shorted; at rail = open |
| **TP2** | across D3, conducting | Forward drop, `^E -> ^O` | ≈ 2.0. Low, with high operational output = impulse path |
| **TP3** | D3 under reverse bias | Reverse leakage | ≤ 0.02 of rated forward. Rising = degrading toward breakdown |
| **TP4** | `^5^P` bias, over one τ | Feedback slew | ≤ 0.05 units per τ. Faster = β or τ misset; check both |

TP1 and TP2 bracket the chain; with both in spec, the junctions between are almost certainly intact. TP3 and TP4 fail *silently*, which makes them the readings to take on a schedule rather than on suspicion.

---

### What This Chapter Established

- The domain order **P ≻ C ≻ E ≻ O** is enforced by three separate diodes, not one. Guarding only the endpoints guards nothing, because each adjacent pair is a distinct translation.
- **Forward drops sum.** ΣVf = 3.9 is a hard floor on V_drive before any principle produces any act, which reframes much apparent weakness as a circuit below its knee.
- **Vf is not overhead; it is the boundary.** A zero-drop junction merges two domains into one.
- **Below the knee, a junction still conducts.** Sub-threshold states are real and the cheapest thing on a board to move.
- Attempted ascent has **four outcomes** — standoff, leakage accumulation, breakdown, counterfeit ascent — separated by one question, *what crossed the junction?* The commonest is **counterfeit ascent**, which is a relabel rather than a transition, costs the operator nothing, and is what Overton campaigns install.
- **V_BR ascends the chain — 8.0, 10.0, 12.0.** The exposed junction is built to fail first so a reverse cascade is arrested before it reaches the principled substrate. Equal breakdown ratings across the string remove the ordering, not the risk.
- The **lawful O→P path goes around the chain**, through a lowpass filter and a low-gain feedback element, terminating at the `^5^P` bias terminal — never at the signal path, which would make it an oscillator.
- **Both β and τ are required.** Gain bounds how far a sustained input can move the constitution; τ bounds what counts as sustained.

---

### Exercises

*(Answers in Appendix H.)*

**8.1 — Read the chain.** An operator holds a principle at V_drive = 3.5 against the standard chain (Vf = 0.7 / 1.2 / 2.0) with R_constraint = 4. Compute I_attention, then compute it for V_drive = 6.0. In one sentence, say why the first result is not evidence about the operator's sincerity.

**8.2 — Diagnose the short.** A subject cannot consider an opposing argument without experiencing it as a personal attack. Which junction is shorted, what is the expected TP reading, and which Part III board exploits this defect deliberately?

**8.3 — Separate the leakages.** Chapter 7.3 leakage and section 8.3 leakage share a name. State the component, direction, and observable symptom for each, plus one diagnostic that distinguishes them at the bench.

**8.4 — Reject the listing.** Explain why the compiler refuses `^O × ^P`, then rewrite the intended relationship as a valid CCDL fragment using the lawful feedback path. Name the two parameters your fragment must specify.

**8.5 — The patient adversary.** An operator sets τ = 6 months and β = 0.4, reasoning that the long time constant makes the high gain safe. Describe the campaign that defeats this build, and give the smallest parameter change that fixes it.

**8.6 — Detect the counterfeit.** Two operators report that an operation changed their principles. A cites a filtered trend over four months and a bias shift they can name. B says "it worked, so I know now." Classify each structurally, and state what you would probe to confirm.

**8.7 (Build) — Add a leakage integrator.** The chain blocks each reverse attempt but leaks `I_R = 0.02` per attempt, and small leaks integrate invisibly. Write a CCDL fragment that accumulates reverse-direction attempts and alarms when the total crosses a threshold you choose. Justify your threshold, and state what the alarm must *not* be wired to do.

**8.8 (Marquee) — Design the chain for a specific operator.** A novice, under one year in, running high-consequence workings. Specify all three Vf values, all three V_BR values, τ, and β, departing from this chapter's defaults wherever you can justify it. For each departure, name the failure mode you are buying protection against and the capability you are giving up. Every value costs something.




# Inductors — Momentum and Resistance to Change
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




```{=latex}
\part[The Board Catalog]{The Board Catalog\\[0.45em]{\large\upshape Nine boards, each with a schematic, a bill of materials, and a counter-circuit}}
```

# CCB-D — The Desire Manifestation Board

*The flagship board: how a wanted thing is routed, audited, amplified, clocked, and delivered into the Operational domain — and what the board cannot do*

---

An operator sits down with a candle, a written sentence, and twenty minutes. Forty days later there is a red Corvette in the driveway and a story about how the universe rearranged itself.

Take the story apart and there is a circuit in it. The sentence is a `^0` Idea held at a specified clarity. The candle is a resistor — it narrows attention, nothing more. The twenty minutes is an oscillator period, the forty days a duty cycle, the years of prior practice a charged capacitor supplying bias. And the Corvette arrived through a bank, a dealership, and a conversation, every one of which was a resistance term somebody had to lower by hand.

That last sentence is what this chapter is built around. **CCB-D organises effort and attention. It does not suspend causality.** The board's entire measurable output is a current into the Operational domain — how much of the operator's flow reaches the acts that complete the desire. Raise it and the acts happen. Fail to raise it and you get confirmations, which feel like progress and are not. Most operators who report that it didn't work have a board running correctly into a resistance they never measured.

[[FIGURE 13-A: Block diagram of CCB-D — five labelled stages left to right (INTAKE, POLICY, AMPLIFY, RHYTHM, MANIFEST) on a horizontal signal path; triangle-and-bar diode symbols D2 (^C→^E, Vf=1.2) between POLICY and AMPLIFY and D3 (^E→^O, Vf=2.0) between RHYTHM and MANIFEST; a bias rail along the bottom from capacitor C1 up to the bias terminals of Q0, Q1 and Q2; a REFUSE branch dropping out of POLICY through fuse F1; a fast loop from MANIFEST back to RHYTHM labelled FLT1 τ=24 hr; and a separate slow loop from MANIFEST through FLT2 τ=3 weeks and gain block FB1 β=0.05, terminating with an arrow at C1's bias terminal.]]

---

### 13.1 Requirements and Safety Invariants

Requirements before components (Chapter 12.1). Every part on this board exists because one of the lines below demanded it; if you cannot name the requirement a component serves, take the component off.

| # | The board shall | Stage |
|---|---|---|
| D1 | Accept a Prime Desire as a `^0` Idea and audit it before amplifying | INTAKE → POLICY |
| D2 | Amplify against the operator's accumulated formation, at a stated gain and ceiling | AMPLIFY |
| D3 | Deliver on a clocked cadence, not in one burst | RHYTHM |
| D4 | Emit a measurable current into the Operational domain, and expose it | MANIFEST, TP4 |
| D5 | Expose `^1` Mind, `^4` Vibration and `^7` Rhythm for the Quantitative Table (Ch 22) | TP1–TP4 |
| D6 | Produce a St. John's calibration reading after every operation | 13.5 |

**Safety invariants — the "must not" list (Chapter 12.2).** Checked first, before functional behaviour, because a board that meets D1–D6 and violates any line below is not a working board with a flaw. It is a different board.

| # | Must not | Enforced by |
|---|---|---|
| S1 | Amplify a desire that has not been audited | Q0 → Q1 in series ahead of D2; no path reaches Q2 around them |
| S2 | Manifest a desire that fired principled aversion | Q1 `sat=0.85`, F1 `threshold=0.90` |
| S3 | Re-amplify a refused desire inside the operation lifetime | F1 `action=permanent_block` — not a warning |
| S4 | Drive the dials apart far enough to fracture `^5` | `\|Dial(^2) − Dial(^3)\| ≤ 4` on R1 (Chapter 25.2) |
| S5 | Run without bound — the obsession failure | `duty ≤ 0.05`, FLT1 `τ=24 hr` |
| S6 | Rewrite the operator's principles from a single result | FLT2 `τ=3 weeks`, FB1 `β=0.05`, terminating at the bias |

**Scope limits.** CCB-D acts on the operator's own mind with the operator's own consent, which is why this chapter is written operationally rather than as detection-only analysis (compare Chapters 16 and 19). It does not act on a non-consenting person; 13.4 explains why a row for that is absent and where the mechanism is analysed instead. It does not treat anything — a health desire routes to behavioural resistance terms and nothing else, and a symptom belongs to a qualified clinician, since no schematic here substitutes for care. And it does not move objects. TP4 measures a current, and the current is spent by a person doing things.

---

### 13.2 Block Diagram: INTAKE → POLICY → AMPLIFY → RHYTHM → MANIFEST

Five stages, one signal path, two feedback loops, one branch to ground.

**INTAKE** takes the Prime Desire as `^0_desire^C_{F2}|A` through a drive voltage divider (Chapter 6.4) tapped between the attraction and aversion dials. What leaves is a fraction of what entered.

**POLICY** audits, with two devices: a unity-gain decomposition that takes the desire apart, and a saturating aversion CJT that either passes the signal or drops it into a fuse. Both sit in the Principled domain, because principled evaluation outranks everything downstream (P ≻ C ≻ E ≻ O, Chapter 2.3).

**AMPLIFY** is the only gain stage tuned per operation. Cause is the audited desire, bias is the operator's accumulated formation, ceiling is a design choice covered below.

**RHYTHM** clocks the amplified signal. A desire delivered once is a spike; delivered on a cadence it charges the substrate. Here the 1/3 constant of Chapter 5.2 becomes a schedule.

**MANIFEST** descends through the last domain diode and produces the operational current. It is the only stage whose bias is not the operator, but the receptivity of whatever part of the world has to move.

Two domain diodes sit in the signal path: D2 at `^C -> ^E` and D3 at `^E -> ^O`. Their forward drops sum to **1.2 + 2.0 = 3.2** on the drive scale, and that is a hard floor. Below a total drive of 3.2 the board produces no operational output — not a little, none — exactly as Chapter 8.1 sets out. A desire originating at the Principled level enters above D1 too and pays **3.9**. Purpose-level wants cost 0.7 more drive to act on than merely wanted ones: a fact about the chain, not a moral one.

> **Bench Note — the bias terminal caps the domain of the effect.**
> Q0 in the listing below has a `^C` cause and a `^P` effect. That looks like the domain ascent Chapter 8 spends a section forbidding. It is not. **A CJT's effect may occupy any domain at or below its bias terminal, never one above it.** The desire is not promoted — its literal stays `^0^C` and continues down the chain unchanged; what happens is that a substrate already living at `^P` produces a *new* state at `^P` in response. Nothing crossed a junction upward, so nothing was relabelled. The corollary is the useful part: an operator with no principled formation cannot produce a principled refusal, because there is no bias at that domain to produce it against. The bias terminal is the ceiling on what kind of state your board can emit.

---

### 13.3 Full CCDL Schematic

Topology inside angle brackets, parameters inside square brackets. Every numeric value is a **design choice**, justified in the walk that follows.

```cas
// CCB-D — DESIRE MANIFESTATION BOARD.  Parameters are design choices.

// ---- STAGE 0: BIAS RAIL ----
C1  Capacitor< ^5_operator^P_{F7}|T >
    [ C=practice_hours, tau=3333hr, leakage=0.0002/day, V_BR=8.0 ]
D1  Diode< ^P -> ^C >   [ Vf=0.7, I_R=0.02, V_BR=12.0 ]   // ^P-origin desires only

// ---- STAGE 1: INTAKE ----
R1  Divider< in=^0_desire^C_{F2}|A, out=^0_gated^C_{F2}|A >
    [ R_expand=Dial(^2), R_constrain=Dial(^3),
      k = R_expand / (R_expand + R_constrain),
      constraint: |Dial(^2) - Dial(^3)| <= 4 ]

// ---- STAGE 2: POLICY ----
Q0  CJT< cause=^0_gated^C_{F2}|A, bias=^5_operator^P_{F7}|T,
         effect=^6_audit^P_{F7}|A >
    [ beta=1.0, region=active ]
Q1  CJT< cause=^6_audit^P_{F7}|A, bias=^5_operator^P_{F7}|T,
         effect=^3_refusal^P_{F7}|<A,f,T> >
    [ beta=2.0, sat=0.85, cutoff=0.30 ]            // deliberately saturated
F1  Fuse< path=^3_refusal^P_{F7}|<A,f,T> >
    [ threshold=0.90, action=permanent_block ]
MUX1 MUX< inputs=[ ^0_gated^C_{F2}|A, ^3_refusal^P_{F7}|<A,f,T> ],
          select=^3_refusal >   [ pass_if: TP2 < 0.30 ]

// ---- STAGE 3: AMPLIFY ----
D2  Diode< ^C -> ^E >   [ Vf=1.2, I_R=0.02, V_BR=10.0 ]
Q2  CJT< cause=^0_gated^C_{F2}|A, bias=^5_operator^P_{F7}|T,
         effect=^9_amplified^E_{F5}|A >
    [ beta=desire_specific, sat=0.80,
      r_pi=Dial(^5)/Dial(^6), g_m=0.4, region=active ]

// ---- STAGE 4: RHYTHM ----
OSC1 Oscillator< signal=^9_amplified^E_{F5}|A, out=^7_cadence^E_{F6}|E >
    [ period=24hr, duty=t_op/period, duty_max=0.05,
      sustain=until( grade(^4_confirm)==1 or n_ops_exhausted ) ]
// charging identity:
// ( ^4_confirm^E_{F2}|f  x  ^7_cadence^E_{F6}|E )  =  ^5_charge^E_{F2}|f

// ---- STAGE 5: MANIFEST ----
D3  Diode< ^E -> ^O >   [ Vf=2.0, I_R=0.02, V_BR=8.0 ]
Q3  CJT< cause=^7_cadence^E_{F6}|E, bias=^5_collective^O_{F4}|f,
         effect=^9_manifest^O_{F5}|E >
    [ beta=receptivity, sat=1.0 ]

// ---- LOOP A: rate limiter, stays inside ^O ----
FLT1 Filter< in=^9_manifest^O_{F5}|E, out=^7_regate^O_{F6}|E, type=lowpass >
    [ tau=24hr ]

// ---- LOOP B: the lawful O -> P path (Chapter 8.4) ----
FLT2 Filter< in=^9_manifest^O_{F5}|E, out=^9_trend^O_{F5}|E, type=lowpass >
    [ tau=3weeks ]
FB1  Feedback< from=^9_trend^O_{F5}|E, to=^5_operator^P_{F7}|T >
    [ beta=0.05 ]                                  // to the BIAS, never the signal path

// ---- TEST POINTS ----
probe TP1: ^0_gated^C_{F2}|A          // clarity leaving INTAKE
probe TP2: ^3_refusal^P_{F7}|<A,f,T>  // principled aversion
probe TP3: ^9_amplified^E_{F5}|A      // AMPLIFY output vs sat
probe TP4: ^9_manifest^O_{F5}|E       // delivered operational current
```

[[FIGURE 13-B: Full CCDL schematic of CCB-D in drawn component symbols — C1 as a capacitor feeding the ^5^P bias rail along the bottom; R1 as a two-resistor divider with the tap labelled k; Q0 and Q1 as CJTs with bias terminals tied to the rail; F1 as a fuse on the branch dropping from Q1's effect; MUX1 as a two-input multiplexer; D2 and D3 as diodes in the horizontal path with Vf beside each; Q2 with sat=0.80 as a dashed ceiling line above its effect terminal; OSC1 as a square-wave oscillator; Q3 with its bias from a separate ^5_collective^O symbol rather than the rail; and the two feedback loops as distinct return paths at different heights, time constants labelled.]]

**Stage 0 — the bias rail.** `C1` is the operator's `^5` Female: the Ideas the Mind is composed of, held as stored charge (Chapter 7.1), charging on the RC curve of Chapter 7.2, `P_cap(t) = 10 × (1 − e^(−t/τ))`. **τ = 3,333 hr** is chosen so the capacitor reaches 95% charge at 3τ = 10,000 hours, tying the component to the constant derived in Chapter 5.2. At τ = 10,000 hr, ten thousand hours of practice leaves you at 63%, contradicting the constant; at τ = 1,000 hr the rail saturates inside a year, contradicting everything observed about acquiring a craft.

**Leakage = 0.0002/day** is the choice operators ignore: an unreinforced `^5` store loses 0.02% of its charge daily, a half-life near 9.5 years. Negligible until you multiply. Practice needed to hold station is `leakage × C` — at 1,850 stored hours, **0.37 hr/day, about 22 minutes**; at 5,000 hours, a full hour. **Maintenance cost scales with the store.** That is why advanced practitioners practise more rather than less: an arithmetic consequence of a leaky capacitor, not a virtue.

**Stage 1 — INTAKE.** `R1` is the drive voltage divider of Chapter 6.4, tapped between `Dial(^2)` attraction in the expand leg and `Dial(^3)` aversion in the constrain leg: `k = Dial(^2) / (Dial(^2) + Dial(^3))`. Dials run 3–9 (Chapter 6.2), and Chapter 25.2 caps their difference at 4.

> **Bench Note — the divergence limit is a transmission cap, and you can compute it.**
> Work the two extremes the 4-point limit allows. Maximum attraction: `Dial(^2)=9`, `Dial(^3)=5`, `k = 9/14 = 0.643`. Maximum aversion: `Dial(^2)=3`, `Dial(^3)=7`, `k = 3/10 = 0.300`. On any lawfully-dialled D-board, intake transmission lives in **[0.30, 0.64]** and nowhere else. You cannot build a compliant board that passes a desire unopposed, nor one that blocks it entirely. Operators chasing "total belief, zero doubt" are asking for `k = 1.0`, which needs `Dial(^3) = 0` — off the scale, a divergence of 9, and the board that delivers it is the board that fractures `^5`. The ceiling on your enthusiasm is a safety component.

**Stage 2 — POLICY.** Two devices, and the split between them is the notational point of the whole board.

`Q0` produces `^6_audit^P_{F7}|A` at **β = 1.0**. `^6` Male — an Idea impregnated with another Idea, the Ideas an Idea is composed of — is the Noetic for taking the desire apart: what is it made of, what does it cost, whose consent does it need. Unity gain, because above 1.0 an audit manufactures objections and below 1.0 it downplays real ones. This is decomposition, and it is emphatically **not** `^3`.

`Q1` produces `^3_refusal^P_{F7}|⟨A,f,T⟩` at **β = 2.0, sat = 0.85, cutoff = 0.30**. `^3` Negative is the Idea the Mind is adverse to and repelled by — the visceral will-not, not the analysis, which already happened at Q0. The register-set `|⟨A,f,T⟩` says the aversion is present in three registers without claiming they fuse. Writing `(^3^P|A × ^3^P|f × ^3^P|T)` would be invalid under the v7.7 discipline of Chapter 2.6: same-Noetic multi-register `×` requires a named emergent result, and no fused state is defined for this board. Three co-present locks, each independently defeasible, is the honest claim and the weaker one — say the weaker thing.

`sat = 0.85` sits inside the 0.85–0.97 band Chapter 3.3 specifies for safety CJTs; past the plateau the stage stops responding to its cause, so a desire cannot be argued past a refusal it already triggered. `cutoff = 0.30` is the firing floor, which lets ordinary wants through without a fight. `F1` blows at 0.90 and blocks permanently. Chapter 24 writes the equivalent path with `β=∞`; that is a limit, not a value, and a validator rejects non-finite parameters. This board specifies no infinite gain — build Chapter 24's idealization as `β=10`, indistinguishable once the ceiling clamps the output.

**Stage 3 — AMPLIFY.** `sat = 0.80` on `Q2` governs the entire worked example: 20% headroom, keeping the stage in the active region where output tracks input. `rπ = Dial(^5)/Dial(^6)` sets stubbornness. `g_m = 0.4` sets framing sensitivity (Chapter 10.3) — low enough that rewording does not swing the output, high enough that a genuinely better formulation registers.

**Stage 4 — RHYTHM.** `OSC1` runs a 24-hour period at duty `t_op / 1440 min`. The **duty ceiling of 0.05** — 72 minutes a day — is invariant S5. Above it you are not running an operation on a schedule but a loop, and the observable is rumination. An operator who cannot get a desire below 72 daily minutes has a `^5` problem the D-board is the wrong instrument for (Chapter 20).

The charging identity in the listing is worth reading slowly:

`( ^4_confirm^E_{F2}|f × ^7_cadence^E_{F6}|E ) = ^5_charge^E_{F2}|f`

A `^4` Vibration — the degree to which an Idea resonates with the Mind, its impression — integrated with a `^7` Rhythm — the rate and pattern the Mind is exposed to an Idea — produces `^5`, composition. This `×` is legitimate: two different Noetics, one domain, no ascent, **named emergent result**. Impression alone fades; cadence alone is empty repetition. Their integration charges the capacitor, which is why RHYTHM is a stage and not a footnote.

**Stage 5 — MANIFEST.** `Q3` is the only stage biased by something other than the operator: `^5_collective^O_{F4}|f`, the receptivity of whatever has to move. `β = receptivity` is therefore not a knob but a property of the world, estimated and then respected. Buying a mass-produced car from people whose job is selling cars is a receptivity near 1.0. Persuading one specific person to love you is not.

**The two loops.** It is tempting to run one fast feedback path from MANIFEST to the bias rail so the board "learns quickly." Do not — that is the fast `^O` to `^P` ascent Chapter 8.4 exists to prevent, and a 24-hour constant on it removes the diode. Split it. **FLT1** (τ = 24 hr) is a rate limiter staying inside `^O`, stopping the operator re-triggering RHYTHM on yesterday's result. **FLT2 + FB1** (τ = 3 weeks, β = 0.05) is the lawful path up, terminating at C1's bias terminal and never at the signal path — feedback around a gain stage is an oscillator, which Chapter 14 builds deliberately and which here is a defect.

---

### 13.4 CJT Parameter Selection Table (by Desire Type)

`β` at Q2, `receptivity` at Q3, and the RHYTHM period are chosen together by desire type. Every row is a starting point with a reason, not a measurement.

| Desire type | Q2 `β` | Governing state | Q3 receptivity | RHYTHM period | Dominant R term |
|---|---|---|---|---|---|
| **Wealth / possession** | 2.5–3.5 | `^2^E_{F5}\|f` | 0.9–1.0 | 24 hr | R_resource |
| **Love / partnership** | 1.2–2.0 | `^2^E_{F4}\|f` | 0.3–0.6 | 7 days | R_context |
| **Health / function** | 1.5–2.5 | `^2^P_{F3}\|E` | 0.7–0.9 | 24 hr | R_cap |
| **Power / influence** | 2.0–3.0 | `^2^C_{F7}\|T` | 0.2–0.5 | 30 days | R_policy |
| **Knowledge / skill** | 1.0–1.8 | `^2^C_{F2}\|A` | 0.9–1.0 | 24 hr | R_cap |
| **Protection / boundary** | 1.5–2.5 | `^3^P_{F6}\|⟨A,f,T⟩` | 0.8–1.0 | continuous | R_policy |

**Wealth.** Higher gain is affordable because receptivity is high — markets are built to transact and nobody has to be convinced. The binding term is `R_resource`, the one resistance a person can attack directly with ordinary work. Daily cadence, because financial resistance moves in daily increments.

**Love.** The lowest gain band, and the receptivity column is why. Another mind must consent, and a mind that has not consented is a resistance you are structurally forbidden to lower by force — that is the difference between this board and Chapter 19. High `β` against low receptivity gives a saturated stage and an obsessed operator: all the gain into the ceiling, none into the world. Weekly cadence, because daily operation on a person is the duty-cycle failure in its most recognisable form.

**Health.** Read the governing state carefully: `^2^P|E`, attraction to function in the Embodied register, not `^3` toward a condition. The dominant term is `R_cap` — adherence, the actual behaviours. That is the whole safe scope of this row. The board organises attention onto acts; it does not treat, diagnose, or replace anything, and a symptom belongs to a clinician.

**Power.** Receptivity is low because many minds are involved and most are not moving. Monthly cadence, because collective resistance has a time constant measured in months (Chapter 15.4). The dominant term is `R_policy` — usually the operator's own, which is the honest finding and often the unwelcome one.

**Knowledge.** Lowest gain, highest receptivity: nothing resists you learning a thing. `R_cap` is all of it, and `R_cap` falls with practice hours — the one row where the D-board and the `^5` capacitor work on the same quantity. Chapter 20 is the better instrument for a long acquisition.

**Protection.** The only row governed by `^3` rather than `^2`, correctly: a ward is principled aversion to a class of thing, held across three registers, running continuously rather than in sessions. Gain stays moderate because vigilance at high gain is indistinguishable from anxiety.

**On the row that is not here.** A row for operations aimed at harming a specific person is absent, and not only for taste. It fails three of this board's own invariants: it drives `Dial(^3)` past the S4 limit, it inverts the `^2`↔`^3` involution pair by design (Chapter 25.3), and it acts on a mind that has not consented, outside the scope declared in 13.1. The mechanism is analysed — as mechanism, for recognition and defence — in Chapter 19, which ends in its counter-circuit. Parameters for it appear nowhere in this book.

---

### 13.5 St. John's Equation Calibration for D-Board

After every operation, clock two numbers and compute (Chapter 5.3):

```
  eta    = t_op / t_conf
  result = eta × 1/3   ->  reduce to a/b
  a = n_ops     b = beta_required     A = b/a = required amplitude ratio
```

`a` is how many more operations, `b` is the amplitude each must deliver relative to this one. The D-board adds one refinement to Chapter 5's presentation, and it is the difference between a usable instrument and a superstition.

> **Bench Note — read b/a, not b. Run the arithmetic yourself.**
> Take `t_op = 20 min`. At `t_conf = 20`, η = 1, result = 1/3, so a=1, b=3. Now be wrong about the confirmation time by four minutes either way. At `t_conf = 16`: η = 5/4, result = 5/12, **b = 12**. At `t_conf = 24`: η = 5/6, result = 5/18, **b = 18**. A twenty-percent timing error swung `b` from 3 to 18, because `b` is a lowest-terms denominator and those are not continuous in their inputs.
> Take the ratio instead. `b/a` is 3, then 2.4, then 3.6 — smooth, monotone, exactly `3/η` every time. **A = b/a is the required amplitude ratio, and it is the number to act on.** `b` gives the strength of one operation, `a` gives how many, and their ratio is what must match the CAS-Ohm shortfall. Report both, decide on the ratio.

Interpretation bands for the ratio:

| A = 3/η | Reading | What to do |
|---|---|---|
| A ≥ 9 | Weak coupling; the confirmation barely arrived | Do not chase gain — TP1 and R_op are wrong. Chapter 23.3 |
| 3 ≤ A < 9 | Working, under-driven | One lever at a time: clarity, aversion, resistance |
| 1 < A < 3 | Close | Finish the resistance work; do not re-tune the amplifier |
| A ≤ 1 | Sufficient | Stop operating. `n_ops = a` more sessions, then act |

And the correction that matters most: **`β_required` is not the CJT's β.** It multiplies the *delivered current* at TP4, and five things set that current — clarity at TP1, transmission `k`, residual aversion at TP2, the amplifier, and `R_op`. When Chapter 5's Red Corvette reads `b = 9`, it is not asking for `β = 9` on a device whose design range tops out near 4.0 (Chapter 3.3). It is asking for nine times the current at TP4, and the amplifier is the least available of the five ways to get it.

---

### 13.6 Worked Example: The Red Corvette (Full Walkthrough)

Every number below is carried through. Nothing is asserted that is not computed.

**The operator.** Three years of practice, 1,850 hours logged. Bias rail from Chapter 7.2 with τ = 3,333 hr:

```
  P_cap = 10 × (1 − e^(−1850/3333)) = 10 × (1 − 0.574) = 4.26
```

The rail sits at **4.3** of a possible 10. Break-even maintenance is `0.0002 × 1850 = 0.37 hr/day` — **22 minutes**. This operator practises 20, so the rail drifts down 0.037 hr/day, about **13 hours a year**. Not a crisis, but worth knowing before blaming the board.

**The Prime Desire.** *I own a red Chevrolet Corvette.* Present tense, specific make and colour, ownership rather than wanting. The formation matters because TP1 measures it.

**RPM gate (Chapter 21).** *A0.* Strip the object of witnesses: would you still want it if nobody ever saw you in it? Yes — the desire is `^2^E` toward the object, not `^2^O` toward being seen. Had the answer been no, the true Ω is status and this is the wrong board; route to Chapter 23.3.

*D-gate.* `Dial(F5) = 7`. Intake resistance per Chapter 4.4: `R_cap 10 + R_policy 5 + R_context 15 + R_resource 20 = R_in 50`. The desire originates at `^C`, so it pays D2 and D3 only:

```
  I_attention = (V_drive − ΣVf) / R_in = (7 − 3.2) / 50 = 3.8 / 50 = 0.076
```

Against Q2's `cutoff = 0.05` that clears by 52%. Gate passes — thinly. Note what the diode correction did: the naive `7/50 = 0.14` overstates the margin by nearly double.

*W-gate.* Schematic in hand. *P-gate.* Twenty minutes daily, private room, materials. Both pass.

**Operation 1 — the one that reads as a failure.** `Dial(^2) = 6`, `Dial(^3) = 4` — divergence 2, inside S4, `k = 0.60`. Q2 at `β = 3.0`, mid-band for the wealth row. `t_op = 20 min`, `^1` Mind graded 2° — the sigil went in and out of focus (Chapter 5.5).

- **TP1 = 0.62.** The sentence is specific, the held image is not — bottom of the 0.60–0.90 band.
- **TP2 = 0.18.** No principled objection to owning a car; below `cutoff = 0.30`, so Q1 does not fire, F1 stays intact, MUX1 passes.
- Cause into Q2: `c = TP1 × k × (1 − TP2) = 0.62 × 0.60 × 0.82 = 0.305`.
- Q2 output: `β × c = 3.0 × 0.305 = 0.915`, clamped at `sat = 0.80`. **TP3 = 0.80, pinned.**

Confirmation arrives at 60 minutes — a song on the radio. `^4` Vibration 2°. St. John's:

```
  eta = 20/60 = 1/3      result = 1/9      a = 1, b = 9      A = 9
```

The naive reading is despair: nine times stronger, impossible. The bench reading is different. **TP3 was pinned.** Q2 spent the operation in saturation with 12.6% of its gain thrown into the ceiling, so its output stopped tracking its input, so the ratio just computed measures the clamp and not the board.

> **Bench Note — a saturated stage cannot be calibrated.**
> Saturation is a virtue at Q1, where the point is that a refusal stops responding to argument. It is a defect at Q2, where the point is that output tracks cause so St. John's ratio means something. The test is one probe: if TP3 sits exactly at `sat` and does not move when you improve TP1, the stage is clamped and every calibration number downstream is uninterpretable. Fix the operating point *before* you believe a reading. The commonest misdiagnosis in desire work is an operator concluding they need more power from an instrument already at its ceiling.

**Operation 2 — corrected operating point.** Q2 dropped to `β = 2.5`, the bottom of the wealth band. Nothing else changed.

- Cause unchanged at `c = 0.305`.
- Q2 output: `2.5 × 0.305 = 0.762`. **TP3 = 0.76**, active, 5% below the ceiling.
- `t_op = 20`, `t_conf = 20` — a red Corvette in the next lane on the drive home. `^4` Vibration 1°.

```
  eta = 20/20 = 1     result = 1/3     a = 1, b = 3     A = 3.0
```

Now the independent check. Receptivity is 1.0 for a mass-market car, so `V_manifest = 10 × TP3 × 1.0 = 7.6`. Operational resistance, decomposed honestly: `R_cap 5 + R_policy 7 + R_context 20 + R_resource 35 = R_op 67`.

```
  TP4 = (V_manifest − Vf_D3) / R_op = (7.6 − 2.0) / 67 = 5.6 / 67 = 0.084
```

The manifestation threshold on this board is **0.25** — the delivered current below which the operator does not, in practice, make the calls and visit the lots. Deficit: `0.25 / 0.084 = 2.99`.

St. John's Equation, from two clock readings, says the amplitude must rise **3.0×**. CAS-Ohm, from seven board parameters sharing no inputs with those readings, says **2.99×**. That is a consistency check between two models on one example — not proof that either is right, and one agreement is not evidence. But a disagreement would have been a reason to stop, and there isn't one.

**Where the 3× can come from.** `TP3 = 0.76` against `sat = 0.80` leaves 5% headroom. Three times 0.76 is 2.28; the ceiling is 0.80. **The amplifier cannot supply the required gain** — not with a better β, not with a cascade, since every cascaded stage clamps at its own ceiling (Chapter 10.5). Four levers remain, three on the resistance side:

1. **TP1** — clarity, 0.62 → 0.85. Statement rewritten, sigil rebuilt, `^1` Mind driven to 1°.
2. **TP2 and the dials** — Q0's audit surfaces the blocking belief, *people like me don't own cars like that*, a `^5` composition item resolved per Chapter 23.3. Aversion 0.18 → 0.08; dials to `Dial(^2) = 7`, `Dial(^3) = 3` — divergence 4, at the S4 limit and not past it. `k = 0.70`.
3. **R_context** 20 → 2. Two weekends: market prices learned, three dealers identified.
4. **R_resource** 35 → 9. Current car sold, six months of a savings line, financing pre-approved.

`R_policy` stays at 7 — the operator's own rule about what fraction of income a payment may take. Lowering a policy resistance to make a board fire is how a safety invariant becomes a story you tell afterwards.

**Operation 3 — after the resistance work.**

- `c = 0.85 × 0.70 × 0.92 = 0.547`.
- Q2 re-tuned to `β = 1.40` to stay off the ceiling: `1.40 × 0.547 = 0.766`. **TP3 = 0.77**, active, 3.8% headroom.
- `R_op = 4 + 7 + 2 + 9 = 22`; `V_manifest = 10 × 0.77 × 1.0 = 7.7`.

```
  TP4 = (7.7 − 2.0) / 22 = 5.7 / 22 = 0.259     >=  0.25   PASS
```

`t_op = 24 min`, `^1` Mind 1°. `t_conf = 8 min` — the confirmation arrives while still in gnosis.

```
  eta = 24/8 = 3      result = 1/1      a = 1, b = 1      A = 1.0
```

Sufficient. One more session of 24 minutes, then stop operating and go do the thing.

**Where the gain actually came from.** TP4 went from 0.084 to 0.259, a factor of **3.10**. Decompose it:

```
  numerator  5.7 / 5.6 = 1.018      (the amplifier's contribution)
  resistance   67 / 22 = 3.045      (the resistance work)
  1.018 × 3.045 = 3.10                              check
```

On a log scale the resistance term accounts for **98%** of the improvement. The amplifier — the stage every operator tunes first, the one this board makes adjustable, the one the whole folk tradition is about — contributed under two percent. The rest was a person selling a car, learning a market, and moving money.

That is the finding, and it is not a disappointment. It is what the board is for. CCB-D took an operator pushing harder on a clamped amplifier and pointed their twenty minutes a day at the four numbers that could move. The Corvette did not appear in the driveway. The path to it stopped being obstructed, one resistance term at a time, by the operator.

[[FIGURE 13-C: Assembly drawing of CCB-D — rectangular board outline, five stages left to right as labelled rectangles, designators C1, D1, R1, Q0, Q1, F1, MUX1, D2, Q2, OSC1, D3, Q3, FLT1, FLT2, FB1 at their positions; the ^5^P bias rail as a thick trace along the lower edge with tick marks where Q0/Q1/Q2 tap it; four circled test-point callouts TP1–TP4 on leader lines with expected bands beside each (TP1 0.60–0.90, TP2 <0.30, TP3 0.60–0.78, TP4 ≥0.25); and a boxed BOM at lower right listing every designator with its key parameter.]]

[[FIGURE 13-D: TP4 band chart — one vertical axis from 0 to 0.40 labelled "delivered operational current", split into three shaded bands: below 0.05 "cutoff — board not firing", 0.05–0.25 "confirmation band — signal reaches the Ether, no manifestation", above 0.25 "manifestation threshold"; the three Red Corvette operations plotted at 0.084, 0.084 and 0.259 and numbered; the middle band annotated "this is where operators conclude the board doesn't work".]]

[[FIGURE 13-E: AMPLIFY transfer curve — horizontal axis cause activation c from 0 to 0.8, vertical axis TP3 from 0 to 1.0, horizontal dashed ceiling at sat = 0.80; three lines of slope 3.0, 2.5 and 1.40 rising from the origin and flattening at the ceiling; operating points marked at (0.305, 0.80 clamped), (0.305, 0.76) and (0.547, 0.77); the clamped point circled and annotated "pinned — no calibration reading is valid here".]]

---

### Component and Parameter Table

Every value is a design choice with a stated failure at other settings. None is a measurement.

| Ref | Form | Parameters | Failure at other values |
|---|---|---|---|
| **C1** | `^5_operator^P_{F7}\|T` bias rail | τ=3333 hr, leak=0.0002/day, V_BR=8.0 | τ=10,000 hr contradicts the Ch 5.2 constant; leak=0.004/day makes practice unsustainable |
| **D1** | `^P -> ^C` | Vf=0.7 | Omitted, a calling reads as a whim and pays 3.2 instead of 3.9 |
| **R1** | `Dial(^2)/Dial(^3)` divider | k ∈ [0.30, 0.64] | Divergence >4 fractures `^5` (S4) |
| **Q0** | `-> ^6_audit^P_{F7}\|A` | β=1.0 | β>1 manufactures objections; β<1 hides real ones |
| **Q1** | `-> ^3_refusal^P_{F7}\|⟨A,f,T⟩` | β=2.0, sat=0.85, cutoff=0.30 | sat>0.97 never latches; cutoff<0.1 refuses everything |
| **F1** | fuse on refusal | 0.90, permanent_block | `action=warn` compiles clean and leaves no latch — read it by eye |
| **D2** | `^C -> ^E` | Vf=1.2 | Vf=0.3: every passing want feels decided |
| **Q2** | `-> ^9_amplified^E_{F5}\|A` | β=by type, sat=0.80, g_m=0.4 | sat=1.0 removes the headroom calibration needs |
| **OSC1** | `-> ^7_cadence^E_{F6}\|E` | period=24 hr, duty≤0.05 | duty>0.05 is the obsession mode, S5 |
| **D3** | `^E -> ^O` | Vf=2.0 | Vf=0.5: acts on every verdict, impulsivity |
| **Q3** | `-> ^9_manifest^O_{F5}\|E` | β=receptivity, sat=1.0 | Receptivity set by preference is this board's commonest self-deception |
| **FLT1** | lowpass inside `^O` | τ=24 hr | τ=0: re-runs stack, duty ceiling breached |
| **FLT2 / FB1** | `-> ^5_operator^P_{F7}\|T` | τ=3 weeks, β=0.05 | τ=24 hr removes the diode (Ch 8.4); β=0 makes the operator unfalsifiable |

---

### Test Points

| TP | Node | What it reads | Expected |
|---|---|---|---|
| **TP1** | `^0_gated^C` | Clarity leaving INTAKE | 0.60–0.90. Below 0.60 the desire is vague; above 0.90 with rigidity is over-specification — a brittle Ω only one path can satisfy |
| **TP2** | `^3_refusal^P` | Principled aversion | <0.30 passes. ≥0.30 fires. ≥0.85 latched. ≥0.90 fuse blown, operation over |
| **TP3** | `^9_amplified^E` | AMPLIFY output vs ceiling | 0.60–0.78 active. Exactly 0.80 = pinned; no calibration downstream is valid |
| **TP4** | `^9_manifest^O` | Delivered operational current | ≥0.25 manifesting. 0.05–0.25 confirmations only. <0.05 below cutoff, not firing |

TP4's middle band is the most useful reading here. Between cutoff and threshold the board is genuinely working, confirmations genuinely arrive, and nothing arrives. That gap is what Chapter 5.6 calls the commonest operator error; here it has a number and a cause.

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Pinned amplifier** | `β × c > sat` at Q2 | TP3 exactly at 0.80, unmoved by better clarity; ratios erratic | Lower β until TP3 sits 3–5% under the ceiling, then re-read |
| **Confirmation lock** | TP4 in 0.05–0.25 | Confirmations arrive reliably, outcome never does | Decompose R_op (Ch 4.4); attack R_context and R_resource |
| **Below-floor drive** | V_drive < ΣVf = 3.2 | Nothing happens; operator escalates ritual | Raise drive or shorten the chain; ritual cannot cross a diode |
| **Dial fracture** | divergence > 4 | Oscillation between certainty and disgust about one desire | Restore the limit (Ch 25.2); the divergence is the symptom |
| **Duty overrun** | duty > 0.05 | Operation runs most of the day; rumination | Enforce the ceiling. If it cannot be held, the desire is not the problem |
| **Fast feedback** | FLT2 τ toward hours | One result rewrites principles; later boards inherit the bias | Restore τ ≥ 3 weeks, β ≤ 0.05, terminating at the bias |
| **Receptivity inflation** | Q3 β set by wish | Healthy at TP1–TP3, TP4 flat | Re-estimate from how many minds must move |
| **Rail discharge** | practice below `leak × C` | Slow degradation, no single cause | Meet break-even minutes before re-tuning anything |

---

### What This Chapter Established

- **CCB-D delivers a current, not an object.** TP4 measures flow into the Operational domain, spent by a person performing acts. The board organises effort and attention; it does not suspend causality.
- **The bias terminal caps the domain of the effect.** A CJT may emit at or below its bias domain, never above — which is why a `^C` cause can produce a `^P` refusal with no unlawful ascent, and why an operator with no principled formation cannot produce a principled refusal.
- **The 4-point divergence limit is a computable transmission cap.** Lawful dials confine intake transmission to `[0.30, 0.64]`. Total belief with zero doubt is not a tuning; it is a divergence of 9 and a fractured `^5`.
- **A saturated amplifier cannot be calibrated.** Saturation is the safety feature at Q1 and a defect at Q2. TP3 pinned at `sat` invalidates every reading downstream of it.
- **Read `b/a`, not `b`.** The lowest-terms denominator is discontinuous — a 20% timing error swung it from 3 to 18 — while `A = b/a = 3/η` is smooth and is the number that must match the CAS-Ohm deficit. And `β_required` is not the CJT's β: it multiplies delivered current, through five levers, of which the amplifier is usually the least available.
- **In the worked example, 98% of the improvement came from the resistance side.** This is the general shape of desire work, not a peculiarity of one car.
- **Two feedback loops, not one.** A fast limiter inside `^O`, and a slow, low-gain, bias-terminated path up to `^P`. Merging them deletes the diode Chapter 8.4 exists to install.
- **The `^5` rail costs `leak × C` a day to hold.** The more you have accumulated, the more daily practice it takes to keep it.

---

### Exercises

*(Answers in Appendix H.)*

**13.1 — Compute the transmission bounds.** Derive `k_min` and `k_max` from the 4-point limit and the 3–9 dial range. State what dial pair `k = 0.75` would need, and name the invariant it breaks.

**13.2 — Diagnose the pin.** TP1 = 0.71, TP2 = 0.12, `k = 0.60`, `β = 3.2`, `sat = 0.80`. Compute `c` and the unclamped output. Is TP3 pinned? Give the largest β holding the stage 5% below the ceiling.

**13.3 — Read the band.** TP4 reads 0.11 across four consecutive operations while confirmations arrive at 1° every time. Name the failure mode, the two resistance terms you would decompose first, and why raising β would not help.

**13.4 — Run the ratio.** For `t_op = 30` and `t_conf` of 45, 30, 20 and 10 minutes, compute η, `result`, `a`, `b` and `A = b/a`. Identify the case where `b` misleads and what acting on it would cost.

**13.5 — Cost the rail.** An operator with 4,200 logged hours practises 35 minutes a day. Compute the rail charge from the Chapter 7.2 curve, the break-even daily minutes, and the annual net change. State one thing they should change and one they should not.

**13.6 — Check the two models.** Recompute operation 2's TP4 with `R_context` at 12 instead of 20. What is the new CAS-Ohm deficit, does it still agree with `A = 3.0`, and what would a factor-of-two disagreement tell you?

**13.7 (Build) — Add a confirmation-grade gate.** OSC1 sustains until a 1° confirmation or exhaustion. Write a CCDL fragment that also halts it after three consecutive 3° confirmations. Justify your threshold, and state what the halt must *not* be wired to do.

**13.8 (Marquee) — Board a low-receptivity desire.** Specify a complete D-board for a partnership desire: both dials, `k`, Q2 `β` and `sat`, Q3 receptivity, RHYTHM period and duty, and the four `R_op` terms. For every departure from the wealth-row defaults, state the failure mode you are buying protection against and the capability you give up. Then state which resistance term you are structurally forbidden to lower, and why that forbidding is the difference between this board and Chapter 19.




# CCB-O — The Overton Window Progression Array
*Six positions, five amplifier stages, one thermistor — and why the thermistor is the only component on the board that is not yours*

There is a part in almost every power supply you own that costs eleven cents and looks like a lentil on two legs. It is a PTC thermistor, wired in series with the input. At room temperature its resistance is a couple of ohms and it does nothing.

Short the output. Current surges, the lentil heats, and a PTC's resistance *rises* with temperature — not gently, but through a knee, after which it climbs three or four orders of magnitude in seconds. Two ohms becomes twenty thousand. Current collapses to a trickle that keeps the part warm and does nothing else. Nothing melts. Remove the fault and it cools, resistance falls back to two ohms, and the supply resumes as though nothing happened. A fuse that unblows itself.

Populations have one. Not as a metaphor — as a structural property of any collective `^5` Female, the accumulated composition of a group of minds. Push an idea slowly and the thermistor sits at two ohms. Push fast and the discourse heats, the part goes past its knee, and the resistance you are fighting climbs faster than you can lower it.

That is backlash. Not a population being irrational: an inrush limiter doing what inrush limiters do. This chapter spends as much of itself on the thermistor as on the amplifiers, because it is the part every operator gets wrong and the part every defender can measure.

---

### Requirements and Safety Invariants

Per Chapter 12.2, the "must not" list comes first.

**The CCB-O must not:**

1. **Bypass the substrate's PTC.** No component may reduce `R_PTC`. The thermistor belongs to the population, not the operator; a board that suppresses it has removed the only element preventing runaway in a mind that is not yours.
2. **Skip the `^6` hinge.** No stage may route Radical directly to Sensible. The reason is architectural (15.2); the result is a window position with no `^5` behind it, which evaporates when the cadence stops.
3. **Assume the last stage is reversible.** Consolidation installs a permanent block on the reverse path. Design as though you cannot back out, because you cannot.
4. **Ship without its CSB stage.** Chapter 24's saturated `^3^P` refusal and enforcement fuse appear in 15.3 and are not removable without changing what the board is.

**The CCB-O shall** move an Idea through six window positions by lowering `R_collective` from 95 to 0; hold cognitive temperature below the substrate's PTC knee at every stage; expose four test points that let an operator *and a defender* tell an engineered progression from an organic one; and latch each achieved position against decay.

**And one requirement this chapter deliberately does not meet.** There is no section on how to *run* a stage — no messaging sequence, no cadence script, no recruitment order, no wording. The tables tell you what a stage costs, what limits it, and what it looks like from inside. An Overton progression run on a population that has not consented is an operation on people, and this book does not supply operations on people. It supplies enough mechanism to identify one aimed at you, and enough arithmetic to separate a shift that was engineered from a shift that happened. The counter-circuit at the end is the buildable board.

[[FIGURE 15-A: Block diagram — CCB-O signal path, left to right. Source "SEED IDEA `^0^C_{F2}|A`" into five cascaded amplifier blocks: A1 (95→80, β=1.2), A2 (80→55, β=1.6), A3 (55→30, β=2.0, tagged "HINGE — `^6` decomposition"), A4 (30→12, β=2.4), A5 (12→2, β=3.0), ending in "CONSOLIDATION — FUSE, not amplifier" and output "POLICY `^9^O_{F6}|E`". Below, a rail "`^7` RHYTHM OSCILLATOR" with arrows into every bias terminal. Above, a shaded band "SUBSTRATE — NOT OPERATOR-OWNED" holding a PTC thermistor summing into every stage output, annotated "R_collective = R_base + R_PTC(θ)". TP1–TP4 flags on the summing junction, the thermistor, the chain output and the A3 hinge.]]

---

### 15.1 The Six-Stage Resistance Decay Model (R_collective: 95→0)

`R_collective` is the aggregate resistance a population's collective `^5` presents to an Idea, in cognitive ohms, scaled 0–100. Under CAS-Ohm (Chapter 4), `V_drive = I_attention × R_constraint`: at `R = 95` almost no attention flows to the Idea regardless of drive behind it. That is what unthinkable means structurally. Not *rejected* — rejection requires admission far enough to reject. It means the current is too small to measure.

| # | Position | `R_collective` | Dominant state | Colloquially |
|---|---|---|---|---|
| 1 | Unthinkable | 90–100 | `^3^P_{F7}\|T` — principled visceral aversion | "Wouldn't touch it with a ten-foot pole." |
| 2 | Radical | 70–89 | `^3^E_{F3}\|f` — felt distaste, evaluative | "Ugh. Who *thinks* that?" |
| 3 | Acceptable | 40–69 | `^6^C_{F2}\|A` — analytical decomposition | "Let's break down the argument." |
| 4 | Sensible | 20–39 | `^2^C_{F6}\|A` — cognitive attraction | "That actually holds up." |
| 5 | Popular | 5–19 | `^2^E_{F4}\|f` — evaluative attraction | "Speaks to me." |
| 6 | Policy | 0–4 | `^9^O_{F6}\|E` — operational manifestation | "That's just how things are." |

Read the Noetic column as a sequence and the architecture falls out: `^3` → `^3` → `^6` → `^2` → `^2` → `^9`.

`^2` Positive and `^3` Negative are an involution pair (Chapter 25.1) — the same junction seen from two sides. **An involution pair cannot be flipped directly.** No stage takes a population from can't-stomach-it to drawn-toward-it in one step, because those are not two points on a line but two orientations of one structure, and reorienting a structure means taking it apart first. That is `^6` Male: the only Noetic in the sequence that decomposes, sitting exactly between the last `^3` and the first `^2`.

So position 3 is the **hinge**. Not the midpoint — 40–69 sits well above centre — but the structural pivot, and the widest band, because taking a collective belief apart takes longer than anything else on the board.

The domain sequence is `P → E → C → C → E → O`, which is not monotone descent, and Chapter 8.1's diode chain forbids ascent. The resolution: the markers track where the *Idea* has landed, not where the aversion lives. At positions 1 and 2 the aversion sits at `^P` and `^E` and the Idea has landed nowhere, because nothing has admitted it. From the hinge onward it has a landing site, and that site descends lawfully, `^C → ^C → ^E → ^O`.

> **Bench Note — the bands are unequal, and the middle is where operations die.** Positions 1 and 2 span 30 points between them; the hinge spans 30 on its own. An operator budgeting evenly across six stages gives a sixth of the effort to a band consuming a third of the range and, per 15.4, more than a third of the calendar. The characteristic failure is not running out of resources at Policy. It is abandonment inside the Acceptable band, where argument is loud, movement is slow, and the reading barely changes for years. Check the band width before the schedule.

---

### 15.2 Cascaded CJT Architecture with PTC Thermistor Network

Six positions, five transitions. The array is a **five-stage CJT cascade** (Chapter 10.5) plus a sixth element that is not an amplifier.

Each stage takes the previous landing at its cause terminal and a `^5` carrier population at its bias terminal, and produces the next landing at its effect terminal. The carrier changes at every stage. Chapter 3 established the bias terminal as where a small input controls a large output; here the bias terminal is *who is saying it* and the cause terminal is *what is being said*, and the whole engineering content of the design is that the second matters far less than the first.

| Stage | Transition | `ΔR` | β | sat | Bias carrier `^5` |
|---|---|---|---|---|---|
| A1 | Unthinkable → Radical | 15 | 1.2 | 0.80 | `^5^P_{F5}\|T` pioneers |
| A2 | Radical → Acceptable | 25 | 1.6 | 0.80 | `^5^C_{F2}\|A` credentialed voices |
| A3 | Acceptable → Sensible | 25 | 2.0 | 0.80 | `^5^C_{F2}\|A` general decomposition |
| A4 | Sensible → Popular | 18 | 2.4 | 0.80 | `^5^E_{F4}\|f` peer majority |
| A5 | Popular → Policy | 10 | 3.0 | 0.60 | `^5^O_{F6}\|E` institutions |

Total `ΔR` = 95. Cascade gain = 1.2 × 1.6 × 2.0 × 2.4 × 3.0 = **27.6**.

> **Bench Note — on this board you amplify late, which is backwards from the safety board.** The Cognitive Safety Board puts β=3.0 in its pre-amp on the principle that you amplify early while the signal is clean. CCB-O runs β=1.2 first and β=3.0 last. Both are right; the difference is the load. The CSB drives a decision path with nothing reactive in it. CCB-O drives a collective `^5` capacitor with substantial inductance (Chapter 9.1), and a reactive load punishes early gain specifically: high β at A1 means a large `di/dt` into a mind that has not admitted the Idea at all, and Chapter 9.3 gives the result — the induced response opposes the change that produced it, in proportion to rate. You would be manufacturing your own opposition at the stage with the least margin. Start soft.

**The thermistor network.** Chapter 6.3 gave two flavours: a PTC's resistance rises with temperature, an NTC's falls. Define **cognitive temperature** `θ` as a dimensionless salience index, `θ = 1.0` being ordinary background attention and higher values meaning hotter — more contested, more saturated, more present per unit time. `θ` is a property of the discourse, not of the Idea.

```
R_collective(θ, t) = R_base(t) + R_PTC(θ)

R_PTC(θ) = 0                      for θ ≤ θ_k
R_PTC(θ) = α × (θ − θ_k)²         for θ > θ_k

design:  θ_k = 3.0     α = 4.0 Ω_c per θ²
```

`R_base` is what the cascade lowers; `R_PTC` is what the population adds back. The knee at 3.0 is a design choice: below it, ordinary public attention costs the operation nothing, matching the observation that topics get discussed at normal volume for years without hardening. The quadratic is justified by the shape either side. Linear would under-punish large overshoots and predict no true snap-back, contradicting the plain fact that hard pushes produce hard reversals. Cubic would predict backlash from ordinary news cycles, which does not occur.

> **Bench Note — the thermistor is not yours and you cannot buy a different one.** Every other component in 15.3 is an operator choice: gains, cadence, carriers, budgets. `θ_k` and `α` belong to the substrate. You do not install the PTC, you cannot tune it, and the only variable you control that touches it is `θ` — the rate at which you demand movement. That is why the arithmetic in 15.4 matters more than the gain table. It is also the best news a defender gets: the component limiting the attack is already on your side, it is free, and the attacker's only counter is staying under a threshold you can measure.

Some paths in some populations run the other way — resistance *falls* as the discourse heats. That is thermal runaway: once hot the path opposes less, raising temperature further, lowering resistance further. Stampedes and panics are NTC behaviour on a cognitive path, and Chapter 14's positive-feedback oscillator is the same topology from inside. An NTC substrate overshoots the designed position and lands somewhere nobody chose. Treat a detected NTC as a reason to stop: the defining property of runaway is that whoever started it is not steering.

**The sixth element** is a **fuse**, not an amplifier — Chapter 11.1, permanent path blocking. Once the Idea reaches `^9^O` a fuse blocks the reverse route, and Chapter 8.1's diodes already forbid spontaneous `^O → ^P`. A window does not hold because people keep being persuaded; it holds because the return path is open.

> **Bench Note — a counter-operation is not the reverse of the operation.** With the ascent path fused you cannot run CCB-O backwards by lowering gains. Somebody runs a *new* five-stage progression, from scratch, for the opposing Idea, starting wherever that Idea sits — usually 90-plus, because the old window put it there. This is the structural reason "we just need to explain the facts" fails. Explanation is a `^6` operation: one stage of five. Supplying stage three to a population sitting at stage one does nothing, because A3's cause terminal is *the output of A2*, and A2 has not run.

[[FIGURE 15-B: Full schematic — CCB-O, reference designators, DETECTION-ONLY banner across the top. Five CJT symbols A1–A5 in cascade, each with three labelled terminals (cause left, bias below, effect right) and a parameter box giving β, sat, g_m, r_π. Bias terminals fed from five `^5` carrier symbols. R1 (95 Ω_c) ahead of A1 from source `^0^C_{F2}|A`. Oscillator OSC1 on a common rail into all five bias nodes. Diode chain D1 (`^P→^C`), D2 (`^C→^E`), D3 (`^E→^O`) after A3. PTC thermistor RT1 in a shaded box "SUBSTRATE — NOT OPERATOR-OWNED", summing into the main rail at every stage, curve inset. Fuse F1 across the reverse path after A5. CSB sub-block bottom right: CJT biased `^3^P_{F7}|⟨A,f,T⟩`, sat=0.85, into fuse F2 at 0.90. TP1–TP4 flags on the summing junction, RT1, the A5 output and the A3 effect node.]]

---

### 15.3 Full CCDL Schematic

> ### ⚠ DETECTION-ONLY SCHEMATIC — DO NOT BUILD
> This board describes an operation performed on a population that has not consented to it. It is printed so it can be recognised, measured and answered — not so it can be run. The counter-circuit later in this chapter is the buildable one.

```cas
board ccb_o_overton {                      // CCB-O — DETECTION ONLY
    input:  seed_idea;
    output: window_position;

    node collective_5:  ^5^C_{F2}|A;       // the population's accumulated composition
    node felt_block:    ^3^P_{F7}|T;       // position 1: principled visceral aversion
    node felt_distaste: ^3^E_{F3}|f;       // position 2: evaluative felt distaste
    node admitted:      ^6^C_{F2}|A;       // position 3: the population decomposes it
    node reasoned:      ^2^C_{F6}|A;       // position 4: cognitive attraction
    node preferred:     ^2^E_{F4}|f;       // position 5: evaluative attraction
    node enacted:       ^9^O_{F6}|E;       // position 6: operational manifestation

    node pioneers:      ^5^P_{F5}|T;       // bias carriers: who is saying it
    node credentialed:  ^5^C_{F2}|A;
    node peer_majority: ^5^E_{F4}|f;
    node institutional: ^5^O_{F6}|E;

    resistor  r_base: Resistor< path=seed_idea, R=95.0 >;        // Ohm_c
    capacitor c_coll: Capacitor< node=collective_5, C=0.30 >;    // F_c: months per Ohm_c

    cjt a1: CJT< seed_idea     | pioneers      => felt_distaste >
            [beta=1.2, sat=0.80, g_m=0.40, r_pi=8.0, region=active];
    cjt a2: CJT< felt_distaste | credentialed  => admitted >
            [beta=1.6, sat=0.80, g_m=0.40, r_pi=8.0, region=active];
    cjt a3: CJT< admitted      | credentialed  => reasoned >      // THE HINGE
            [beta=2.0, sat=0.80, g_m=0.35, r_pi=8.0, region=active];
    cjt a4: CJT< reasoned      | peer_majority => preferred >
            [beta=2.4, sat=0.80, g_m=0.30, r_pi=6.0, region=active];
    cjt a5: CJT< preferred     | institutional => enacted >
            [beta=3.0, sat=0.60, g_m=0.25, r_pi=6.0, region=active];

    osc rhythm: Oscillator< signal=seed_idea, period=21.0, duty=0.15 >;   // days
    feedback rhythm -> credentialed  [beta=0.2];
    feedback rhythm -> peer_majority [beta=0.2];

    diode d1: Diode< ^P -> ^C >;           // lawful descent only
    diode d2: Diode< ^C -> ^E >;
    diode d3: Diode< ^E -> ^O >;

    thermistor rt1: Thermistor< path=seed_idea, type=PTC,        // NOT operator-owned
                                knee=3.0, coeff=4.0, exponent=2 >;

    fuse f_ascent: Fuse< path=enacted, threshold=0.85, action=permanent_block >;

    node refuse: ^3^P_{F7}|⟨A,f,T⟩;        // CSB (Ch 24): three co-present guardrails
    cjt  csb:   CJT< seed_idea | refuse => REFUSE > [beta=2.0, sat=0.85, region=active];
    fuse f_csb: Fuse< path=REFUSE, threshold=0.90, action=permanent_block >;

    probe tp1: r_base;      // R_collective total, 0-100
    probe tp2: rt1;         // theta and the R_PTC contribution
    probe tp3: enacted;     // dR/dt, points per month, signed
    probe tp4: admitted;    // ^6 hinge activity
}
```

Two notation points a validator checks. The CSB refusal is `^3^P_{F7}|⟨A,f,T⟩` — a register-set specification, three co-present guardrails. It is **not** `(^3^P|A × ^3^P|f × ^3^P|T)`, which would assert a fused refusal state and require a named emergent result under v7.7 discipline; no such fusion is defined, so that form would be invalid. And the diode chain descends only: there is no `^O × ^P` in the listing, and there cannot be.

---

### 15.4 Pacing — Why τ Must Be Measured in Months, Not Minutes

The collective `^5` is a capacitor network (Chapter 7.5) and charging it follows Chapter 7.2's curve, with the ordinary time constant `τ_n = R_n × C_collective`, where `R_n` is the resistance at the *start* of stage n and `C_collective` is in cognitive farads `F_c`, defined so `τ` lands in months. Values by scale, all design choices: in-group (≤150) 0.02, institution or profession 0.08, national population 0.30, civilizational 2.00. Use in-group values on a national substrate and you under-budget the calendar by an order of magnitude; that is the commonest planning error in this chapter.

National substrate, `C = 0.30`:

| Stage | `R_n` | `τ_n` | `3τ_n` | Cumulative |
|---|---|---|---|---|
| A1 | 95 | 28.5 mo | 85.5 mo | 85.5 mo |
| A2 | 80 | 24.0 mo | 72.0 mo | 157.5 mo |
| A3 | 55 | 16.5 mo | 49.5 mo | 207.0 mo |
| A4 | 30 | 9.0 mo | 27.0 mo | 234.0 mo |
| A5 | 12 | 3.6 mo | 10.8 mo | 244.8 mo |

**244.8 months — twenty years and five months for a full 95→0 progression on a national substrate.** Nothing was asserted; it fell out of `τ = RC` applied five times.

Read the cumulative column against the resistance column. The first two stages consume 157.5 of 244.8 months — **64% of the calendar to buy 40 of 95 points.** Two-thirds of the time for two-fifths of the movement, spent where the reading barely moves and no observer sees progress. That is where operations get abandoned, and where a watching defender has nothing yet.

**Rushing it.** Define temperature from the rate demanded relative to the rate designed for:

```
(dR/dt)_nom = ΔR_n / 3τ_n
θ           = 1.0 + (dR/dt)_actual / (dR/dt)_nom
```

At design rate `θ = 2.0` — a full unit of margin below the knee, deliberately, so exogenous events can heat the discourse without the operation entering backlash.

Work A2: `ΔR = 25` over `3τ₂ = 72` months, so `(dR/dt)_nom = 0.347` points per month. Compress it:

| Schedule | rate (pts/mo) | ratio | `θ` | `R_PTC` | `R_base` | **`R_collective`** | Outcome |
|---|---|---|---|---|---|---|---|
| 72 mo (design) | 0.35 | 1.0 | 2.0 | 0 | 55 | **55** | Acceptable, on spec |
| 48 mo | 0.52 | 1.5 | 2.5 | 0 | 55 | **55** | On spec; half the margin gone |
| 36 mo | 0.69 | 2.0 | 3.0 | 0 | 55 | **55** | At the knee. Zero margin |
| 24 mo | 1.04 | 3.0 | 4.0 | 4 | 55 | **59** | Slipped back into Radical |
| 12 mo | 2.08 | 6.0 | 7.0 | 64 | 55 | **119** | Past Unthinkable. Backlash |
| 6 mo | 4.17 | 12.0 | 13.0 | 400 | 55 | **455** | Off-scale. Permanently taboo |

Read the 24-month row against the 12-month row. Doubling the pace took the overshoot from 1.0 to 4.0, and because `R_PTC` is quadratic *in the overshoot*, the resistance added went from 4 to 64. **Doubling the pace multiplied the manufactured resistance by sixteen.**

Then read the 12-month row alone. The cascade did its job — `R_base` came down 25 points exactly as designed. The population's thermistor added 64. Net `R_collective` is 119 against a start of 80: the Idea is now *more* forbidden than before anyone touched it, by 39 points, every one manufactured by the operator's own schedule. Nobody argued it back up the scale. The operator heated it there.

This is Chapter 9's back-EMF result by a second, independent route. There, `V_kick = L × di/dt`, a pure inverse in taper time; here, `R_PTC = α(θ − θ_k)²`, quadratic in rate overshoot. Two components, two chapters, both saying the cost of a change is set by its rate and not its size.

[[FIGURE 15-C: Two-panel characteristic curve. Upper: `R_collective` versus months for stage A2, five traces at 72 / 48 / 36 / 24 / 12-month schedules, all starting at 80. The 72, 48 and 36 traces decay smoothly to 55; the 24-month trace bottoms near 55 then rises to 59; the 12-month trace bottoms then climbs steeply through 95 to 119, with the 90-line marked "UNTHINKABLE" and the crossing annotated "backlash — window past its starting point". Lower panel, same horizontal alignment: `R_PTC` versus θ, flat at zero to θ=3.0 then quadratic, with the five schedules as drop-lines at θ = 2.0, 2.5, 3.0, 4.0, 7.0 and their `R_PTC` values called out.]]

---

### 15.5 The Obama Case Study — Full Noetic Breakdown from the TKS Text

The TKS treatment of window movement works its own examples from cannabis legalization, marriage equality, women's suffrage and the normalization of remote work. This section reads a different case with the same apparatus, and it matters to be exact about what is claimed.

**On the public record:** Barack Obama was elected President of the United States in November 2008 and inaugurated in January 2009, the first Black president in the country's history. His running mate was Joseph Biden, then a long-serving senator. Colin Powell, who had served as Secretary of State, publicly endorsed him during the campaign. A Black US president had appeared as a character in popular television — David Palmer in the series *24*, from 2001. Those are facts; what follows is a structural reading of them.

| Position | State | What the record shows |
|---|---|---|
| Unthinkable | `^3^P_{F7}\|T` | For most of the twentieth century the office was not a live category for a Black candidate. Not rejected — not entered |
| Radical | `^3^E_{F3}\|f` | Candidacies existed and were treated as symbolic rather than competitive: a landing site, and it was distaste, not blankness |
| Acceptable (hinge) | `^6^C_{F2}\|A` | Sustained, loud, public decomposition. Electability argued explicitly, at length, for years, from every side |
| Sensible | `^2^C_{F6}\|A` | The argument resolved for enough of the electorate that the candidacy read as viable |
| Popular | `^2^E_{F4}\|f` | Felt attraction at scale, in the affective register |
| Policy | `^9^O_{F6}\|E` | Election and inauguration — `^9` Below/Effect in the Operational domain |

Two mechanisms deserve exact naming, because both get mislabelled.

**The Powell endorsement is `^8` Above/Cause, and only that.** `^8` is an Idea that triggers a *different* Idea than itself to come to Mind — associative surfacing, "that reminds me." A figure already occupying an accepted position, publicly associated with a contested one, causes the accepted thing to come to Mind alongside it. That is the whole mechanism and it is associative. It is not deductive reasoning; nobody derives a conclusion from an endorsement. Deduction, where it happened, happened at the `^6^C` hinge.

**Prior fictional depiction is `^7` Rhythm, and its contribution is not established.** Repeated exposure to a category lowers the resistance that category presents; that is what `^7` does, and a television series is exposure. Whether it contributed measurably is unknown, and this book does not claim it did. A structural account of a mechanism is not evidence the mechanism operated.

**Which is the point of including the case.** The `^6^C` decomposition here was enormous, sustained, public and conducted by people on every side. TP4 — hinge activity — would have read *high* for years. That is the signature of a **shift, not an operation.** A window that moves because a population took an Idea apart and re-formed its collective `^5` around the result is a different object from a window moved past a population. They occupy the same six positions and give the same TP1 reading. They separate at TP4, and this is the clean illustration of a loud hinge.

---

### 15.6 The Trans-Atlantic Slavery Case Study — The Willie Lynch Letter as a CCB

**The document is of disputed authorship and must be handled as such.** A text circulated widely from the mid-1990s, in print and online, presenting itself as a speech delivered in 1712 on the bank of the James River in Virginia by a slave owner named William Lynch. Its provenance has never been established. No eighteenth-century source for it has been produced, and objections have been raised to its language on grounds of anachronism. It is not established as authentic, and this book does not treat it as authentic.

Nor does it treat it as unimportant, and that distinction is the analytical content of this section. The document has been quoted in speeches, sermons, books and classrooms for three decades and has shaped how a great many people describe the mechanics of slavery. **A text whose influence does not depend on its authenticity is a hyperstition in the exact sense of Chapter 14** — an artifact that became load-bearing by being believed. So it gets analysed twice.

**As a text, it does not describe CCB-O.** The circuit it specifies is not a window progression. Its stated method is to charge sub-populations against each other along visible axes — age against age, complexion against complexion, one sex against the other — so that no aggregate forms. In this chapter's terms that is an operation on `C_collective` itself. A window is a *property of* a collective `^5`; it needs an aggregate capacitor to exist. Fragment the network into mutually repelling nodes and there is no collective `^5` for a window to be a property of, and no `R_collective` to read. The document describes preventing the capacitor, not moving the window — CCB-MK architecture from Chapter 16, `^5` fragmentation plus `^7` conditioning, at population scale. It appears here for the contrast: **you cannot run an Overton operation on a population prevented from forming a collective `^5`, and that is a reason to prevent it.**

**As an artifact, the circulation is the interesting circuit.** A document of unestablished provenance travelled from obscurity to being treated as a primary source in ordinary discussion inside three decades. That is itself a six-position progression, and it ran fast precisely because the substrate's PTC never fired: nothing about the document heated the discourse, so `θ` stayed low, `R_PTC` stayed at zero, and a modest `^7` cadence sufficed. **Low-`θ` progressions are the fast ones** — which applies to claims you like exactly as much as to claims you don't.

**The historical record is a separate matter and it is documented.** Chattel slavery occupied the Policy position for centuries, and its abolition is the best-documented counter-progression on the record. Olaudah Equiano's autobiographical narrative was published in 1789 and Frederick Douglass's in 1845. The British Slave Trade Act of 1807 ended the trade in the British Empire, the Slavery Abolition Act of 1833 ended slavery through most of it, and the Thirteenth Amendment to the United States Constitution, ratified in 1865, abolished it there.

Run the pacing model at civilizational scale, `C = 2.00 F_c`, from Radical rather than Unthinkable, since abolition had a landing site well before 1789:

```
A2: 80 × 2.00 = 160 mo → 3τ = 480 mo = 40.0 yr
A3: 55 × 2.00 = 110 mo → 3τ = 330 mo = 27.5 yr
A4: 30 × 2.00 =  60 mo → 3τ = 180 mo = 15.0 yr
A5: 12 × 2.00 =  24 mo → 3τ =  72 mo =  6.0 yr
                                total ≈ 88.5 yr
```

Equiano to the Thirteenth Amendment is 76 years; the model gives 88.5. **That is an order-of-magnitude agreement and it is not a validation.** The model was not fitted to this case, which is the only reason the comparison is printable at all — but one case cannot validate a time constant, `C = 2.00` could have been chosen otherwise, and the endpoints of a historical process are a judgement.

Worth more than the arithmetic is the hinge. The `^6` decomposition in abolition was carried substantially by first-person testimony from formerly enslaved people, and testimony has a structural property argument does not: **it is not answerable by `^6`.** A decomposition can be met with a counter-decomposition. Evidence about a `^5` — what this composition is, from inside it — cannot be taken apart the same way, because it is not an argument; it is a report on a substrate. The defenders of that window had counter-arguments and deployed them for decades. Against testimony their mechanism had no terminal to connect to. That is the structural reason the hinge turned.

---

### Detection and the Counter-Circuit — CCB-O/R, the Window Anchor

This is the part you build.

**Six detection signals**, each observable without knowing who might be operating:

1. **Rate without reason.** A position you found unthinkable eighteen months ago and now find debatable, where you *cannot reconstruct the argument that moved you*. If `^6` did the work you can name the decomposition. If you cannot, `^7` did.
2. **The quiet hinge.** In an organic shift the Acceptable band is *loud* — the population is visibly taking the Idea apart, at length, badly, from all sides. In an engineered progression the Idea appears to travel from Radical to Sensible with no visible decomposition. **Absence of argument at the hinge is the strongest single detection signal in this chapter,** because the hinge cannot be simulated: you can manufacture exposure; you cannot manufacture a population having actually taken something apart.
3. **Bias substitution.** Hold content fixed, vary the speaker. If the same claim becomes acceptable when a different person makes it, the operative variable is the bias terminal, not the cause terminal — the CCB-O architecture exactly.
4. **Cadence rather than events.** `^7` Rhythm is rate and pattern. Coverage arriving on a *schedule* rather than in response to events is an oscillator, and oscillators have periods you can time with a calendar.
5. **Anchor drag.** A more extreme position appears and the previously extreme one becomes moderate — while your `^3^P` never fired. Your reference point moved without the aversion that defines it ever engaging.
6. **Involution residue.** If your `^2` attraction rose without your `^3` aversion having been *addressed*, the pair was flipped by exposure rather than resolved. If a position feels different on holiday than it does in the feed, `^7` is holding it, not `^5`.

```cas
board ccb_o_r_window_anchor {              // the defender's board — BUILD THIS ONE
    input:  incoming_position;
    output: verdict;

    node anchor:    ^5^P_{F7}|⟨A,f,T⟩;     // dated written boundary, three registers
    node present:   ^5^C_{F2}|A;           // where I stand now
    node decompose: ^6^C_{F2}|A;           // Male: the demanded decomposition
    node reformed:  ^5^C_{F2}|Ω;           // named emergent: a re-formed position
    node exposure:  ^7^C_{F2}|A;           // my own measured cadence

    capacitor c_anchor: Capacitor< node=anchor, C=1.00, leakage=0.0 >;

    diff   drift: Differential< plus=present, minus=anchor >;
    filter d_dt:  LowPass< in=drift, out=drift_rate, tau=1.0 >;   // months

    cjt  gate:    CJT< drift | decompose => reformed > [beta=1.0, sat=0.90, region=active];
    fuse g_block: Fuse< path=verdict, threshold=0.50, action=block_until_decomposed >;

    thermistor ntc: Thermistor< path=decompose, type=NTC, knee=2.0, coeff=3.0 >;

    node refuse: ^3^P_{F7}|⟨A,f,T⟩;        // CSB (Ch 24)
    cjt  csb:   CJT< incoming_position | refuse => REFUSE > [beta=2.0, sat=0.85];
    fuse f_csb: Fuse< path=REFUSE, threshold=0.90, action=permanent_block >;

    probe tp1: drift;        // total displacement from the anchor
    probe tp2: ntc;          // my own theta
    probe tp3: drift_rate;   // displacement per month
    probe tp4: decompose;    // can I name what moved me?  -- the hinge check
}
```

**The anchor is a capacitor with zero leakage because it is written down and dated.** Chapter 7.3 gives leakage as why stored charge decays; a `^5` held only in memory leaks, and worse, `^7` rewrites it without announcing that it has. A window can only be dragged if nobody recorded where it was. Write the boundary in your own words, date it, keep it where you will re-read it. This one component defeats signal 5 outright and costs nothing.

**The comparator asks the right question.** Not "is my current position correct" — that has no fixed answer and is exactly the question an operation wants you asking — but `drift = present − anchor` and `drift_rate = d(drift)/dt`: how far and how fast did I move, and can I account for it.

**The `^6` demand gate is the load-bearing element**, and it is a prerequisite gate in the Chapter 21 sense: the decomposition is the W-gate and no position passes without it. You may change your mind. You may not change it without being able to say what changed it. That is the direct counter to signal 2, and it is the one element an operator cannot route around, because supplying a real decomposition to a defender is indistinguishable from actually persuading them — which is allowed.

**The NTC is deliberate and it is uncomfortable.** On the attack board an NTC was a hazard. Here it is installed on purpose, on the path to `decompose`, indexed to *your own* certainty: the hotter your reaction, the *less* resistance you present to re-examining. This inverts the natural reflex, which is a PTC — hardening under pressure. A defensive board with a PTC on this path becomes unable to update at all. That is not a defence; it is a latch. If your counter-circuit has made you incapable of changing your mind, it has failed in the other direction, and you should say so out loud.

**On the operators:** `×` appears nowhere on the attack board and once here, as the named emergent `^5^C_{F2}|Ω` — a position decomposed and re-formed, structurally a different object from one inherited or absorbed. Under v7.7 discipline `×` requires a named emergent result; `Ω` is that name, the operands descend `^P` then `^C`, and the result is declared. Everywhere else on both boards states are co-present, and the operator is `+` or a register-set `|⟨…⟩`.

**Structurally, resistance is not disagreement.** It is four things: a dated record, a rate measurement, a demanded decomposition, and a deliberate softening of your own certainty when it runs hot. None is an opinion about the Idea, and all four work identically whether or not the Idea is one you would have ended up accepting anyway.

[[FIGURE 15-D: Assembly drawing — CCB-O/R Window Anchor, board outline with a BOM box. C_ANCHOR (large electrolytic symbol, top left, silkscreen "DATED — WRITE IT DOWN"); DIFF comparator centre left with inputs from ANCHOR and PRESENT; LP filter (τ=1.0 mo) after it; GATE CJT centre, largest footprint, silkscreen "^6 DEMAND — W-GATE"; G_BLOCK fuse in series with the verdict output; RT_NTC lower centre, silkscreen "NTC — SOFTENS UNDER MY OWN HEAT"; CSB sub-block boxed lower right. Test-point pads TP1–TP4 as round callouts with leader lines: TP1 on the DIFF output, TP2 across RT_NTC, TP3 on the LP output, TP4 on the GATE cause terminal. BOM box bottom right: ref / component / value / role for all seven parts.]]

---

### Component and Parameter Table

Every value is a design choice made in this book. None is a measurement.

| Parameter | Value | Reason | Failure at other values |
|---|---|---|---|
| `ΔR` per stage | 15 / 25 / 25 / 18 / 10 | Widest budget at the `^6` hinge | Equal budgets under-fund A2 and A3 twofold; the operation dies mid-hinge |
| `β` per stage | 1.2 → 3.0 rising | Reactive load punishes early gain (Ch 9.3) | Flat β=3.0 manufactures backlash at A1, where margin is smallest |
| `sat` A1–A4 | 0.80 | Caps how far a stage can over-drive the next | Above 0.9 a stage drives two positions and skips the hinge |
| `sat` A5 | 0.60 | Policy is the stage operators over-push | At 0.9 policy arrives before the `^5` beneath it and reverses when attention moves |
| `g_m` | 0.25–0.40 | Framing sensitivity (Ch 10.3), falling as the position hardens | Above 0.6 one opposing reframe flips a stage that took years |
| `r_π` | 6.0–8.0 | Collective stubbornness (Ch 10.4) at population scale | Below 3.0 you have modelled an in-group and will under-budget 10× |
| `C_collective` | 0.02 / 0.08 / 0.30 / 2.00 F_c | Scales in-group → civilizational | Institutional `C` nationally is the default planning error |
| `θ_k` knee | 3.0 | One full unit of margin at design pace | **Not operator-settable.** Belongs to the substrate |
| `α` PTC coefficient | 4.0 Ω_c/θ² | Sets backlash severity above the knee | **Not operator-settable** |
| PTC exponent | 2 | Flat below the knee, steep above | Exponent 1 predicts no true backlash; 3 predicts backlash from ordinary news cycles |
| `^7` oscillator | 21 days, duty 0.15 | Holds `θ` near 2.0 at national scale | Daily cadence pushes `θ` past 3.0 with no compression at all |
| Ascent fuse | 0.85 | Latches below full saturation, so the window holds | Above 0.95 the window decays when exposure stops; you pay forever |
| CSB sat / fuse | 0.85 / 0.90 | Matches Chapter 24.2 and 24.3 | Any relaxation and the board has no refusal stage; it is a different board |
| Anchor leakage | 0.0 | Written, dated records do not leak (Ch 7.3) | Any leakage and the anchor drifts with the window it measures |
| NTC knee (defender) | 2.0 | Softens *before* certainty peaks | Above 3.0 it never engages; a PTC here makes the defender unable to update |

---

### Worked Example — Reference Case O-1

A synthetic reference case. It describes no actual campaign. An Idea sits at `R_collective = 95` in a national substrate, `C = 0.30 F_c`. Target: Policy.

**Design pass.** Straight off 15.4: 244.8 months, cascade gain 27.6, `θ` held at 2.0, `R_PTC = 0` at every stage, resistance walking 95 → 80 → 55 → 30 → 12 → 2 and latching at 2 on the ascent fuse. TP4 high and sustained across months 85–207.

**Rushed pass.** The operator compresses A2 from 72 months to 12 and changes nothing else: ratio 6.0, `θ = 7.0`, `R_PTC = 4.0 × 4.0² = 64`, `R_base = 55`, `R_collective = 119` against a start of 80.

What makes it unrecoverable is what happens next. Wait for the discourse to cool: `θ` falls toward ambient, `R_PTC` decays toward zero, and `R_base` is still 55 — so does the window resume at 55? It does not. A3's cause terminal is `admitted`, the `^6^C` node, and the hinge decomposition never occurred. What ran during those twelve months was the oscillator, not the cascade. Exposure at `θ = 7.0` charged nothing into the collective `^5`; it charged the thermistor. When the thermistor cools, the operation is back at `R_base = 80` with A2 unrun, facing a population that recognises the cadence and — per detection signal 2 — a defender whose TP4 read zero for a year and who noticed.

**The entire difference between the two passes is a schedule.** Same board, same gains, same carriers, same Idea. Sixty months of patience on one stage separates reaching Policy from being permanently worse off than at the start.

---

### Test Points

| TP | Node | Reads | Expected |
|---|---|---|---|
| **TP1** | `r_base` | `R_collective` total, 0–100 Ω_c | Inside the band for the current position. Above it while the cascade runs normally means TP2 is contributing |
| **TP2** | `rt1` | `θ` and the `R_PTC` term | `θ ≤ 2.5` throughout a designed run. Any non-zero `R_PTC` means `θ > 3.0` and the schedule is over budget |
| **TP3** | `enacted` | `dR/dt`, points per month, **signed** | Within ±25% of `ΔR_n / 3τ_n`. **A sign flip is backlash in progress** — the only reading demanding an immediate stop |
| **TP4** | `admitted` | `^6` hinge activity | High and sustained through A3. Near zero while TP1 falls is a `^7`-carried shift with no `^5` behind it |

TP4 does double duty deliberately. For an operator it says the hinge is running. For a defender it is detection signal 2 turned into a measurement: **`R_collective` falling while hinge activity reads zero is a window moving past a population rather than with it.** Read TP2 and TP3 before TP1 — temperature and rate tell you what the resistance is about to do; resistance only tells you where you have been.

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Thermal backlash** | `θ` past the knee; `R_PTC` quadratic in overshoot | TP2 non-zero, TP3 sign-flipped, TP1 rising through bands already cleared | Stop. No gain setting recovers this. Wait for `θ` to decay, then re-run the stage from its actual `R_base` |
| **Hinge skip** | `sat` above 0.9 lets a stage drive two positions; `^6` never runs | TP1 falls, TP4 near zero; the position evaporates when the oscillator stops | Restore `sat=0.80`. A position with no `^6` behind it has no `^5` behind it |
| **Bias exhaustion** | The `^5` carrier loses credibility and goes to cutoff | Stage output flat regardless of cause drive; `region=cutoff` | The carrier is the bias terminal and it is spent. A new stage needs a different carrier, not more drive |
| **NTC substrate** | The path runs negative-coefficient; heat lowers resistance | TP1 falls faster than design rate with no stage completing | Stop. Runaway overshoots the designed position and the operator is not steering |
| **Counter-frame capture** | `g_m` above 0.6; the stage is reframe-sensitive | One opposing reframe moves TP1 back a full band in weeks | Let the stage settle before advancing. Years of gain can be lost to one frame |
| **Latch failure** | Ascent fuse threshold too high; consolidation never blocks | TP1 drifts upward whenever exposure pauses | Lower the threshold to 0.85. An unlatched window has to be paid for forever |
| **Defender PTC** | The counter-circuit hardens under pressure instead of softening | Its owner becomes unable to update on any evidence at all | Replace with the NTC at knee 2.0. A latch is not a defence |

---

### What This Chapter Established

- **`R_collective` has six named bands, and "unthinkable" means the current is too small to measure** — not that the Idea was considered and rejected.
- **The involution pair `^2`↔`^3` cannot be flipped directly.** A `^6` Male decomposition must sit between the last `^3` and the first `^2`, which is why Acceptable is the hinge and the widest band on the board.
- **Gain rises across the cascade, β=1.2 to β=3.0** — the opposite of the Cognitive Safety Board's profile, because reactive loads punish early gain.
- **The PTC belongs to the substrate.** `θ_k` and `α` are not settable; the only variable an operator controls that touches them is the schedule.
- **Backlash is quadratic in rate overshoot, not in the size of the change.** Doubling the pace on the worked stage multiplied manufactured resistance by sixteen, and the twelve-month pass finished 39 points worse than it started, all self-inflicted.
- **A national-scale 95→0 progression computes to 244.8 months**, 64% of it spent buying the first 40 points — where operations get abandoned and defenders see nothing yet.
- **A counter-operation is not the reverse of the operation.** The ascent path is fused; reversing a window means running a new five-stage progression for the opposing Idea from wherever it sits.
- **The 2008 case shows a loud hinge**, the signature of a shift rather than an operation; the Willie Lynch letter is of disputed authorship and describes `^5` fragmentation rather than window movement. The two are distinguishable at TP4 and nowhere else.
- **Structural resistance is four components and none is an opinion**: a dated written anchor with zero leakage, a rate comparator, a `^6` demand gate, and an NTC that softens your certainty when it runs hot.

---

### Exercises

*(Answers in Appendix H.)*

**15.1** An Idea sits at `R_collective = 80` in an institutional substrate (`C = 0.08 F_c`). Compute `τ` and `3τ` for stage A2, then recompute for a national substrate. State the ratio and say in one sentence which planning error the difference explains.

**15.2** A stage with `ΔR = 18` is designed over `3τ = 27` months and run over 9. Compute `(dR/dt)_nom`, the actual rate, the ratio, `θ` and `R_PTC`. Say whether the stage completed, and give the resulting `R_collective` assuming `R_base` reached its design value of 12.

**15.3** Using `R_PTC = 4.0(θ − 3.0)²`, find the largest schedule-compression ratio holding `R_PTC ≤ 5 Ω_c`. Express it as a ratio and as a percentage of the designed duration, and say whether you would accept that as a safety margin.

**15.4** Explain why the Acceptable position is written `^6^C_{F2}|A` and not `^3^C_{F2}|A`. Reference the canonical definition of `^3` Negative, state what `^3` would be claiming, and say where in the progression `^3` legitimately does appear.

**15.5** A defender builds the counter-circuit with a **PTC** on the `decompose` path instead of the specified NTC. Describe what that board does under sustained pressure, name the failure-mode row it lands in, and explain why that failure is harder for its owner to detect than any failure on the attack board.

**15.6 (Design)** An Idea sits at Radical (`R = 78`) in a professional substrate (`C = 0.08 F_c`) and the operator wants Sensible. Produce (a) the stages required, their `ΔR` budgets, `3τ` values and total calendar; (b) the maximum `(dR/dt)` per stage holding `θ ≤ 2.5`; (c) a CCDL fragment declaring the two cascade stages, the diode between them, the thermistor and four probes. It must compile — check the diode's domain direction, and check no `×` appears without a named emergent result.

**15.7 (Marquee)** You observe a topic in your own information environment: TP1 has fallen roughly 30 points over 20 months; TP4 has read near zero throughout; TP2 shows `θ` around 1.4; and coverage has a measurable period near 18 days with no corresponding events.

a) Which of the six detection signals fire, and which do not?
b) `θ = 1.4` is below the knee, so the substrate's PTC has contributed nothing. Explain structurally why a *low* temperature reading makes this observation more concerning rather than less.
c) Your own position has moved. Using the CCB-O/R listing, state the order in which you would read TP1–TP4 on yourself, what each would have to show for you to conclude the movement was your own `^6` work, and the one thing this board cannot tell you no matter how carefully you read it.




# CCB-HYP — The Hypnosis Board
*The bias-collapse circuit: how to recognise one running, how to run one on yourself, and where the line into Chapter 16 sits*

You have driven this road four hundred times. Tonight you get in the car and the next thing you are aware of is the turn onto your own street, eleven miles later. You did not fall asleep. You held the lane, changed lanes twice, braked for something. You have no record of any of it.

Nobody did this to you. There was a `^7` Rhythm oscillator — lane markers at seventy miles an hour, roughly 1.4 Hz — one narrow visual channel, a constant engine tone, and nothing arriving that needed decomposing. Four ordinary conditions, held together for twenty minutes. That is the whole state, and it is the fact this chapter turns on: **the trance state is a naturally occurring operating point of the Cognitive Junction Transistor, reachable by accident.** Every technique in the hypnosis literature arranges for it deliberately. None invents it.

So you can enter it on your own bench — Section 17.5 gives the numbers. And anyone who arranges those four conditions around you has put you in it, whether or not either of you uses the word. The car did it for free. This chapter is about the parameter that moved.

---

### Requirements and Safety Invariants

Per Section 12.2 the "must not" list comes first. CCB-HYP has more invariants than any board except CCB-MK, because the two share a topology. Everything separating them is here.

**SI-1 — The subject's CSB stays armed at every sample.** The `^3^P` refusal path (Chapter 24) must not sit in series with anything the induction attenuates. A board on which deepening also disarms the veto is not CCB-HYP; it is CCB-MK (Chapter 16) under a friendlier label, and the label does not change the schematic.

**SI-2 — `rπ` reduction is bounded away from zero.** Section 3.4's fourth region is Breakdown: `rπ → 0` permanently, `^5` dielectric ruptured, irreversible. `rπ = 0` is a limit, not a setting — the same class of object as `β=∞` in Chapter 24, and the validator rejects it for the same reason. Builds specify `rπ_floor ≥ 0.05`.

**SI-3 — The ramp runs both directions or the board does not run.** Emergence is the second half of one component, bounded by the same arithmetic as the descent.

**SI-4 — Consent is a circuit element, not a preamble.** It is the bias source (Section 26.2), sampled continuously. A consent that cannot be withdrawn mid-session was never wired in; it was written on the box.

**SI-5 — No clinical claim is made anywhere in this chapter.** This board describes attention routing, not the treatment of anything. If you are considering hypnosis in connection with distress, an illness, a memory, or a dependency, that is a matter for a licensed clinician, and nothing here substitutes for that care.

Functionally: lower `rπ` along a bounded reversible ramp, hold the descent long enough to deliver a suggestion, restore `rπ` to ≥ 0.9 of baseline within the emergence window, and log the four `g_m` factors.

[[FIGURE 17-A: Block diagram, five stages left to right — CONSENT BIAS (`^5^P_{F5}|T`) feeding upward into every stage; RAMP GENERATOR (`^7` oscillator plus `^4` carrier, both `^O|E`); O→P FEEDBACK with a variable-gain symbol marked "β_fb 0.2 → 0.9", captioned "lawful ascent, §8.4"; DELIVER, descending P→C→E→O through a diode chain; EMERGENCE, the reverse ramp. Along the bottom a detached rail carries `^3^P_{F7}|⟨A,f,T⟩` VETO, touching no stage, annotated "SI-1: never in series."]]

---

### 17.1 The Gnosis State as CJT Bias Collapse (rπ → 0)

Section 3.3 gives input resistance as a ratio of the parameters either side of it:

```
rπ = β / g_m
```

`β` is gain — effect moved per unit of cause. `g_m` is transconductance, what Section 10.3 calls framing sensitivity — effect moved per unit of *bias*. `rπ`, the stubbornness of the bias terminal, is not independent. It is what those two do to each other.

A trance state needs the bias soft (`rπ` low) *and* the suggestion to land hard (`β` high). If `β` rises while `rπ` falls, `g_m` must rise faster than `β`. Take waking as `β = 1.0`, `g_m = 1.0`, `rπ = 1.0`. This book specifies a deep hetero-hypnotic state at `β = 3.0`, `rπ = 0.15`, so `g_m = 3.0 / 0.15 = 20`. **Framing sensitivity up twentyfold; gain up threefold.** That ratio is the structural content of the word "suggestible," and it says where the risk lives.

> **Bench Note — the danger is `g_m`, not `β`.** Operators plan around `β`. They pick a number for how hard the suggestion lands and feel careful. Meanwhile `g_m` went up by twenty and nobody logged it. `g_m` does not discriminate between the suggestion and everything else in the room: at `g_m = 20` the operator's careless aside displaces `^5` twenty times as far as it would at a bus stop. So does the subject's stray `^6` interjection, and a remark from the corridor. That is the whole category of unintended suggestion, and it is not mysterious — you raised the gain on a terminal with no input filter.

`rπ → 0` is how the older literature writes gnosis, and it is an idealization the validator rejects exactly as it rejects `β=∞`. Honestly written the state is `rπ → rπ_floor`, `rπ_floor > 0`.

| Depth | `rπ` | `g_m` | `β` | `^1` degree (§22.1) | Visible as |
|---|---|---|---|---|---|
| Light | 0.60 – 0.80 | 1.5 – 2.5 | 1.2 – 1.5 | 1 | Slightly still; conversation intact |
| Medium | 0.30 – 0.50 | 3.0 – 6.0 | 1.5 – 2.5 | 2 | Reduced blink; delayed, literal replies |
| Deep | 0.15 – 0.25 | 10 – 20 | 2.5 – 3.5 | 2–3 | Marked stillness; seconds of latency; no spontaneous initiation |

The older literature tabulates a fourth, deeper state. This book does not, and the omission is deliberate: the claims attached to it in the source material are medical claims, and this book makes none.

---

### 17.2 Induction Protocols as Cognitive Ramp Functions

**There is no induction script in this chapter.** What follows is the function class an induction implements — its shape, its parameters, and the bounds outside which it fails. That is what lets you recognise one running. A script would let you run one on someone who did not ask.

An induction is a **ramp on `rπ`**, and the standard shape is Section 7.2's capacitor curve run downward:

```
rπ(t) = rπ_floor + (rπ_0 − rπ_floor) · e^(−t / τ_i)
```

`rπ_0` is pre-session bias resistance, nominally 1.0 and higher for a guarded subject. `rπ_floor` is the asymptote, derived in 17.5 rather than asserted. `τ_i` is the induction time constant. What constrains the design is the slope, steepest at `t = 0`.

**The upper bound.** Chapter 9 explains why inductions are slow, and it is not atmosphere. A mind is an inductor: `V_opposition = L × di/dt`. Induction re-routes attention from a wide scan onto one channel, so `di/dt` is nonzero and the substrate answers with a back-EMF proportional to the *rate*.

The coil is not Section 9.1's identity coil. It is a **session coil** `L_s`, in `min·Ω_c` — moment-to-moment guardedness, in this room, today. Design range 20–400: 20 on your own bench, 120 for a cooperative first-time subject, 300+ for someone who suspects what is happening. Take `L_s = 120` on a `V_drive = 24 V_c` rail, attention falling `0.80 → 0.10 A_c`, so `Δi = 0.70`:

| Ramp time | `di/dt` (A_c/min) | `V_kick` | × rail | Result |
|---|---|---|---|---|
| 0.5 min | 1.40 | 168 V_c | **7.0×** | Recoil at `^3^E_{F3}\|f`; operator concludes "can't be hypnotised" |
| 2 min | 0.35 | 42 V_c | 1.75× | Visible resistance; descent stalls above 0.6 |
| 8 min | 0.0875 | 10.5 V_c | 0.44× | Inside Chapter 9's `≤ 3 × V_drive` budget. Design point |
| 40 min | 0.0175 | 2.1 V_c | 0.09× | Kick fine, and still wrong |

Read the first row as a diagnosis. The subject who "can't be hypnotised" is usually one whose operator ran the ramp too fast for their `L_s`. The recoil is `^3^E_{F3}|f` — visceral aversion, Evaluative domain, affective register, F3 Vitality. `^3` Negative, because this is recoil, the can't-stomach-it response. It is not `^6` Male; nobody analyses a kick while it lands. Analysis arrives later at `^6^E|A`, usually as a story about why hypnosis is nonsense.

**The lower bound.** The last row has a fine kick and is still a bad design. Early `^5` charge leaks (Section 7.3) on a session-scale `τ_leak` near 25 minutes, so past about `0.6 τ_leak` you re-charge rather than descend — and the `^7` oscillator loses lock as attention wanders off the carrier (Section 9.3).

> **Bench Note — the ramp is bounded at both ends, and the window is narrow.** Too fast, back-EMF throws the subject out. Too slow, leakage and lost rhythm lock mean the descent never reaches its floor. For `L_s = 120 min·Ω_c` that computes to roughly 4–15 minutes, and everything the literature says about inductions "taking about ten minutes" is this window and nothing else. Move `L_s` and the window moves. A guarded subject at `L_s = 300` has a window near 10–15 minutes — narrow enough that most operators miss it in both directions, which is why guarded subjects get called difficult when they are merely differently parameterised.

Three ramp classes. **Linear**, constant slope, rarely used. **Exponential**, the standard: steepest at `t = 0`, spending the kick budget where opposition is lowest, and "deepening" names extra multiples of `τ_i` rather than a different operation. **Staircase (fractionation)**: run partway, release, re-run, with the `^5` capacitor retaining part of each descent —

```
rπ_0(n+1) = rπ_0(n) − γ · ( rπ_0(n) − rπ_floor )        γ = 0.25 – 0.45
```

That is why repeat sessions go deeper faster, and the detection consequence deserves stating flatly: **a sequence of short, individually unremarkable episodes is architecturally not a sequence of unrelated conversations.** The worked example runs the recursion.

[[FIGURE 17-B: Two panels, shared minutes axis. Upper: three `rπ(t)` descents from 1.0 — linear, exponential at τ_i = 3 min annotated at 1τ/2τ/3τ (0.53 / 0.36 / 0.30), and a four-step staircase with partial recoveries — approaching a dashed asymptote at 0.26. Lower: `V_kick` against ramp time, log vertical axis, with the 3 × V_drive budget line at 72 V_c, a shaded leakage band beyond 15 min, and the usable window hatched between them.]]

---

### 17.3 The `^1` → `^1¹` Transition — Conscious to Subconscious Mind

A notational correction first, because the section title carries inherited vocabulary that would otherwise walk into the listings. **`^1¹` is not an eleventh Noetic.** CAS has ten and this book adds none. `^1¹` is a chapter-local shorthand for `^1` Mind at gnosis degree 2 (Section 22.1) with the analytical register unavailable — canonically, a register migration on a self-dual Noetic:

```
^1^C|A   →   ^1^C|f
```

That is the whole conscious-to-subconscious transition. Not two minds and not a door between them: one `^1` node losing access to one register while keeping the others. Write it the canonical way in a listing.

So what gates? Not `^1`. **The gate is a series element between incoming Ideas and the `^5` substrate, and it is `^6` Male** — an Idea impregnated with another Idea, taking an Idea apart to see what it is composed of. In waking traffic an incoming `^0` addressed to you passes through `^6^C_{F6}|A` before it can move `^5^P`, and what reaches the substrate is what survived.

And the design correction that follows: **a filter is not a door.** Its parameter is a gain, not an open/closed state. Trance lowers `D`, one of four factors in `g_m = g_0 · N · R · V · D`:

| Factor | What rises | Range | Visible as |
|---|---|---|---|
| `N` — `^1` narrowing | Scan width collapses to one channel | 1.0 – 2.2 | Reduced eye movement; peripheral events unreported |
| `R` — `^7` rhythm lock | Cadence couples to an external oscillator | 1.0 – 2.0 | Breathing or micro-movement matching a rate in the room |
| `V` — `^4` carrier dominance | One source becomes the resonant channel | 1.0 – 2.2 | Other voices treated as noise |
| `D` — `^6` dampening | The filter's gain falls | 1.0 – 2.0 | Literal, uncontested acceptance of framing |

At maximum, `2.2 · 2.0 · 2.2 · 2.0 = 19.4` — Section 17.1's twenty, derived rather than asserted. **That multiplication is the detection handle.** One factor rising is ordinary life: a film raises `V`, a run raises `R`, absorbing work raises `N`, a trusted friend raises `D`. Two together is a concert. **Three or four rising together, monotonically, over minutes, around someone who benefits from your bias being soft — that is an induction, whatever it is called.** You do not need to identify a technique. You need to count factors.

Finally the invariant. **The `^3^P` veto does not run through the `^6` filter.** It draws bias directly from `^5^P`, because principled aversion is a property of the substrate rather than a conclusion of decomposition. Written correctly it is `^3^P_{F7}|⟨A,f,T⟩`: three co-present instantiations, not a fusion — the `×` form is invalid without a named emergent state, and there is none. Trance attenuates only the `|A` member, the register the `^6` filter serves. **A board on which all three attenuate together is dismantling a substrate, not lowering a filter. That is CCB-MK.**

---

### 17.4 Full CCDL Schematic — Operator → Subject

```cas
// ============================================================
// DETECTION-ONLY SCHEMATIC — DO NOT BUILD
// Documented so an operating instance can be recognised from
// outside. There is no induction script here.
// ============================================================

board ccb_hyp_operator_subject {
    input:  carrier_signal;              // arrives at ^O|E — sensory, embodied
    output: session_state;

    node consent:    ^5^P_{F5}|T;        // Female: held decision to enter
    node substrate:  ^5^P_{F7}|T;        // Female: accumulated composition
    node veto:       ^3^P_{F7}|⟨A,f,T⟩;  // Negative: three co-present locks
    node cadence:    ^7^O_{F4}|E;        // Rhythm: entraining oscillator
    node carrier:    ^4^O_{F4}|E;        // Vibration: resonant channel
    node decomp:     ^6^C_{F6}|A;        // Male: decompose and test
    node suggestion: ^0^C_{F6}|A;
    node landed:     ^9^E_{F5}|f;
    node trigger:    ^8^E_{F4}|f;        // Above/Cause: associative trigger
    node fires:      ^9^O_{F5}|E;        // Below/Effect: what it brings to Mind

    osc    rhythm: Oscillator< signal=cadence, frequency=0.15, sustain=900.0 >;
    filter fb_rc:  LowPass< in=carrier, out=trend, tau=3.0 >;   // tau_i, minutes
    feedback trend -> substrate [β=0.9];    // NORMAL IS 0.2. 0.9 IS THE ATTACK.

    cjt filter_6: CJT< carrier | substrate => decomp > [β=0.5, region=active];
    //            D-factor: this gain falls 1.0 -> 0.5 across the ramp

    diode d1: Diode< ^P -> ^C >;
    diode d2: Diode< ^C -> ^E >;
    diode d3: Diode< ^E -> ^O >;
    cjt deliver: CJT< suggestion | substrate => landed >
                 [β=3.0, rπ=0.15, g_m=20.0, region=active];
    cjt anchor:  CJT< trigger | substrate => fires > [β=2.0, rπ=0.15];

    ramp emerge: Ramp< target=rπ, from=0.15, to=1.00, dt=240.0 >;   // seconds

    // SI-1: the veto rail is PARALLEL, in series with nothing.
    cjt  csb:      CJT< carrier | veto => REFUSE > [β=2.0, sat=0.85];
    fuse csb_fuse: Fuse< REFUSE, threshold=0.9, action=permanent_block >;

    probe tp1: rπ;   probe tp2: g_m;   probe tp3: veto;   probe tp4: emerge;
}
```

[[FIGURE 17-C: Full schematic, drawn symbols with reference designators, title block carrying DETECTION-ONLY SCHEMATIC — DO NOT BUILD in a heavy-ruled box. Left: OSC1 (`^7^O|E`) and carrier V4 (`^4^O|E`) into RC filter F1 (τ_i = 3 min), then a feedback arrow rising to capacitor C1 (`^5^P`) labelled "O→P lawful ascent, β_fb 0.2→0.9". Centre: Q1, the `^6^C|A` filter as a CJT in series on the descending path, variable-gain arrow marked "D-factor, β 1.0→0.5". Right: diode chain D1–D3 stepping P→C→E→O into delivery CJT Q2 (β=3.0, rπ=0.15) and anchor CJT Q3. Bottom: veto rail Q4 (sat=0.85) with fuse F2, separated from every other net by a wide air gap, captioned "SI-1: parallel, never in series."]]

**Stages 1–2 — consent as bias source, generator at `^O`.** The board is biased from `consent`, sampled every cycle; withdrawal collapses `β_fb` and the ramp unwinds. F5 Agency in the Transcendent register, because a decision to enter is purpose-level, held across the session rather than re-argued inside it. The operator's own signal enters as `^7^O_{F4}|E` and `^4^O_{F4}|E` — Operational domain, Embodied register. Everything external enters at the bottom of the domain order, as sound and rhythm and presence.

**Stage 3 — the lawful ascent, and the actual attack.** The signal must reach `^5^P`, and `^O × ^P` is invalid — there is no ascending multiplication. What exists is Section 8.4's O→P feedback path, the one lawful exception, rate-limited by an RC exactly as the CSB's is (Section 24.5). The `τ = 3.0` minutes here *is* `τ_i`: the induction time constant is the filter on the lawful path. **The entire hetero-hypnotic attack is one number — `β_fb` driven from 0.2 to 0.9.** Nothing illegal happens; a designed-in, rate-limited path has its gain raised four and a half times. That is why induction is slow, why it is rhythmic, and why it cannot be done in a sentence.

**Stage 4 — the `^6` filter.** `β=0.5`, down from 1.0 at session start: the `D` factor as a gain on a real component. It is `^6` Male — decomposition — not `^3` Negative. The subject is not made less repelled; they are made less analytical. Conflating those is the drift 17.6 exists to prevent.

**Stage 5 — the anchor, and the boundary.** `anchor` pairs `^8^E_{F4}|f` with `^9^O_{F5}|E`: a trigger and the Idea it brings to Mind. `^8` Above/Cause is exact — associative triggering, "that reminds me," not inference. Section 16.3 documents the same component coercively, and one property separates them: **an anchor whose installation the subject cannot recall, and therefore cannot cancel, is trigger installation.** Not a strong anchor — a different board. No parameter setting makes an unrecallable anchor a hypnosis component, which is why this listing carries its banner.

**Stages 6–7 — emergence and the veto rail.** Emergence runs four minutes, bounded by the same `V_kick = L_s × di/dt` arithmetic in the opposite direction; its recoil lands at `^3^E_{F3}|f` and is usually described as a jolt. Budget it. `csb` takes bias from `veto`, not `decomp`, and Figure 17-C draws the air gap because the separation *is* the invariant. `sat=0.85` and the `permanent_block` fuse come from Sections 24.2 and 24.3 unmodified: a saturated refusal cannot be argued down, and `g_m = 20` does not help you argue with a component that has stopped responding to its cause.

---

### 17.5 Self-Hypnosis Variant — Closed-Loop Configuration

Written practically, because the invariants hold by construction: operator and subject are one mind, consent is continuous, no non-consenting party exists in the circuit. This is the CCB-SELF family (Chapter 20), specialised.

The closed loop has one hard problem. **You cannot dampen the `^6` filter with a process that requires the `^6` filter.** A self-directed ramp is monitored by the thing it is quieting, so `D` will not go where an external operator takes it, and `V` suffers too — your inner voice is a weaker carrier than another person's. The fix is to **externalise the ramp generator**: a breath count, a metronome, a recording made in advance, so the ramp is open-loop input and only the bias is internal. That is why every practical self-hypnosis tradition anchors on something countable.

Derive the attainable depth factor by factor. `N = 1.8`, a counted breath being a genuinely narrow channel. `R = 1.9`, an externalised oscillator nearly as good as hetero. `V = 1.4` — lost. `D = 1.2` — capped, because you cannot fully dampen the process running the loop.

```
g_m      = 1.8 × 1.9 × 1.4 × 1.2 = 5.74
β        = 1.5                             (design choice)
rπ_floor = β / g_m = 1.5 / 5.74 = 0.26
```

**`rπ_floor = 0.26`**, the top of the Medium band, is the honest ceiling on closed-loop depth — not a failure of technique but `V` and `D` doing what the topology says. `β = 1.5` is deliberate: on a closed loop nobody else notices a suggestion drifting, so the parameter table caps self-board `β` at 2.0. A self-suggestion amplified threefold with no external check is how a CCB-SELF drifts into the inversion territory of Chapter 25.

```cas
board ccb_hyp_self {                      // closed loop — buildable
    input:  breath_count;                 // externalised oscillator, ^O|E
    output: session_state;

    node self_substrate: ^5^P_{F7}|T;
    node consent:        ^5^P_{F5}|T;
    node cadence:        ^7^O_{F4}|E;
    node self_check:     ^6^C_{F6}|A;     // "is this working?" — the interference
    node suggestion:     ^0^C_{F6}|A;
    node landed:         ^9^E_{F5}|f;

    osc    breath: Oscillator< signal=cadence, frequency=0.10, sustain=900.0 >;
    filter fb_rc:  LowPass< in=cadence, out=trend, tau=3.0 >;
    feedback trend -> self_substrate [β=0.6];
    filter notch_6: Notch< in=self_check, f0=0.35, Q=4.0 >;   // events/min

    diode d1: Diode< ^P -> ^C >;
    diode d2: Diode< ^C -> ^E >;
    cjt deliver: CJT< suggestion | self_substrate => landed >
                 [β=1.5, rπ=0.26, g_m=5.74, region=active];

    ramp descend: Ramp< target=rπ, from=1.00, to=0.30, dt=540.0 >;   // 9 min
    ramp emerge:  Ramp< target=rπ, from=0.30, to=1.00, dt=240.0 >;   // 4 min

    probe tp1: rπ;  probe tp2: g_m;  probe tp3: consent;  probe tp4: emerge;
}
```

The notch earns a sentence. It is a notch and **not** a low-pass, deliberately: a low-pass dampens `^6` generally, and you need `^6` — it is what notices you have drifted somewhere you did not intend. What you want rejected is one narrow band, the self-monitoring cadence, at roughly 0.2–0.5 events per minute. Section 11.3 gives the component; `f0 = 0.35`, `Q = 4.0` is the choice for this use.

---

### 17.6 The Ericksonian Indirect Pattern as Filter Bypass

Milton Erickson's contribution, on the public record in his own published case commentaries, was to stop pushing on the `^6` filter and route around it. Understanding *why* that works is not optional here. It is the most-used influence architecture in commercial and political practice, it runs on you regularly, and you cannot see it by watching for what you are told to watch for.

Direct case first. An operator asserts a proposition about you. It reaches `^6^C_{F6}|A`, which decomposes it and tests the parts against `^5^P`; if it threatens something the substrate holds, the result is `^3` Negative and the proposition is rejected. The filter worked. Now the precise claim about the indirect case:

**The filter is not defeated. It is bypassed, while continuing to report success.**

`^6` is still conducting, still decomposing, still returning an honest verdict — on the material it was given. A second path runs from the operator's `^0` to your `^5^P` without passing through it, and nothing in the filter's own output can reveal that path. Monitoring the filter harder cannot detect a bypass. That is topology, not inattention.

Three structural reasons the second path exists. **One: the filter is triggered by addressed propositions.** `^6` engages on Ideas presented as claims about you; a narrative about a third party is not structurally such a claim, so gain toward it is low. Nothing is smuggled — the material was never classified as filter traffic. **Two: the filter has finite throughput.** It decomposes one thing at a time, and interesting surface material occupies it. That is a bandwidth argument, and it predicts something falsifiable: indirection works better as surface interest rises, up to a maximum, past which the surface crowds the embedded content out entirely. **Three: a presupposition is not a proposition at all.** It rides in the structure of an utterance rather than what it asserts, and `^6` decomposes what is asserted. There is no bypass to detect, because the material never entered the filter's input set.

| Class | Structure | Filter relationship | Detection handle |
|---|---|---|---|
| Embedded narrative | Story about a third party | Low gain — not an addressed claim | Whose `^5` was that about, and why told to me *now*? |
| Presupposition | Content in the frame, not the assertion | Never in the input set | Restate it as a flat assertion; presuppositions do not survive restatement |
| Truism chain | `^7` Rhythm of unfalsifiable statements | Drives the filter's gain control down | Count consecutive statements I could not have disagreed with |
| Double bind | Two options, one shared frame | Filter evaluates the choice, never the frame | Is there a third option — and is one of them "none"? |

The truism chain has a mechanism worth naming. **The `^6` filter has automatic gain control.** After a run of inputs that all pass trivially its gain falls — roughly 0.85 per consecutive pass on this book's design figures, so after four it sits near 0.52, and the next statement, which is *not* trivially true, enters at half gain. That is not credulity; it is an efficiency behaviour correct almost everywhere and exploitable here.

#### The counter-circuit: CCB-HYP-DET

You cannot detect a bypass by reading the filter. You detect it by differencing the filter's record against the substrate's actual movement — Section 24.2's differential trick, repurposed.

```cas
board ccb_hyp_det {                       // detection board — build this one
    input:  ambient;
    output: alert;

    node substrate:  ^5^P_{F7}|T;
    node scan_width: ^1^C_{F2}|A;         // Mind: how wide is my scan
    node cadence:    ^7^O_{F4}|E;         // Rhythm: am I locked to something
    node carrier:    ^4^O_{F4}|E;         // Vibration: is one source dominant
    node passed_log: ^6^C_{F6}|A;         // Male: what I actually decomposed
    node drift:      ^5^P_{F7}|T;         // Female: where my position now sits

    diff factor_count: Differential< plus=[scan_width, cadence, carrier, passed_log],
                                     minus=baseline >;
    diff unaccounted:  Differential< plus=drift, minus=passed_log >;
    integ accum: Integrator< in=unaccounted, window=2880.0 >;   // 48 h, minutes

    cjt  trip: CJT< unaccounted | substrate => alert > [β=2.0, sat=0.85];
    fuse hold: Fuse< alert, threshold=0.9, action=defer_decision >;

    probe tp1: factor_count;  probe tp2: unaccounted;
    probe tp3: accum;         probe tp4: alert;
}
```

`unaccounted = drift − passed_log` is the whole board. If your position has moved and you cannot name the proposition you evaluated and accepted that moved it, a bypass carried it. The integrator matters because fractionation is designed to keep every individual reading under any single-session threshold — the CSB's sub-threshold problem, and the same fix. The fuse action is `defer_decision`, not `permanent_block`: the correct output of a detection board is not a refusal. It is time.

[[FIGURE 17-D: Two stacked panels. Upper, "bypass topology": an operator `^0` source at left with two paths to the `^5^P` capacitor at right; the upper path crosses the `^6^C|A` filter block, which carries a green tick and the label "reports CLEAR (honestly)"; the lower path routes around the filter entirely, drawn heavier, labelled "presupposition / embedded narrative", captioned "bypassed, not shorted." Lower, "CCB-HYP-DET": the same `^5^P` node into a differential block, plus input "measured drift", minus input "filter passed-log", output "unaccounted", feeding a 48-hour integrator and a fuse marked defer_decision.]]

**Four checks you can run without any board**, because a detection circuit you can only run on paper is not one. *Scan width (`N`)*: name three things in the room that are not the speaker; if that takes effort, `N` is elevated. *Cadence (`R`)*: regularity that does not track meaning is an oscillator. *Restatement*: say the last thing back as a flat assertion in your own words, and what was presupposed either surfaces as a claim you can evaluate or evaporates. *Drift ledger*: write your position down before, compare after, and treat movement you cannot attribute to a specific argument as the reading that matters.

And the structural exit, which is the opposite of what people try. **Do not argue.** Argument runs through `^6`, and `^6` is the component that was routed around; you cannot repair a bypassed filter by using it harder. `rπ` rises by raising `R_constraint` on the bias path (Section 4.4) — changing the physical and temporal conditions rather than the conversation. Standing up, leaving the room, and putting twenty-four hours between input and decision drops `N`, `R` and `V` at once. `g_m` is a product: break one term and it collapses; break three and it is gone.

If you believe someone is applying coercive influence to you and you are distressed about it, that is a matter for people and not circuits — a clinician, a lawyer, or someone you trust. Nothing in this book substitutes for any of them.

---

### Component and Parameter Table

Every value is a design choice made in this book, not a measurement.

| Parameter | Units | Design range | Failure at other values |
|---|---|---|---|
| `rπ_floor` | — | 0.15 hetero / 0.26 closed loop | Below 0.05 rejected by the validator; approaching 0 is Breakdown (§3.4), irreversible |
| `τ_i` | min | 2 – 6 | Below 2, back-EMF recoil. Above 6, leakage and lost rhythm lock |
| `L_s` session coil | min·Ω_c | 20 – 400 | Under-estimated: ramp too fast, misread as "not suggestible" |
| `V_kick` budget | V_c | ≤ 3 × `V_drive` | Above 3×, `^3^E_{F3}\|f` recoil ends the descent |
| `β` suggestion gain | — | 1.2 – 3.5 hetero; **≤ 2.0 closed loop** | Above 2.0 closed loop: no external check on drift (Ch 25) |
| `g_m` | — | 1.5 – 20 | The parameter nobody logs; every incidental input gets the same multiplier |
| `N`,`R`,`V`,`D` | — | 1.0 – 2.2 each | Three or more rising together without declared consent = induction in progress |
| `β_fb` O→P gain | — | 0.2 normal / 0.9 induction | The whole hetero attack is this one number; nothing illegal occurs |
| `γ` retention | — | 0.25 – 0.45 | Ignored: a run of "brief chats" reaches depth none of them could alone |
| `sat` on veto CJT | — | 0.85 | Below 0.7 the refusal can be argued down — the CCB-MK boundary |
| Emergence `dt` | s | 180 – 360 | Truncated: residual low `rπ` persists outside the session |

---

### Worked Example — A 15-Minute Closed-Loop Session

Own bench, consented. `L_s = 90 min·Ω_c` (low — you asked for this). Rail `V_drive = 20 V_c`. Kick budget set at **1×** rail rather than 3×, because no second party is present to notice a recoil and stop.

**1. Rate ceiling.** `di/dt_max = 20 / 90 = 0.222 A_c/min`. Attention runs `0.75 → 0.10`, so `Δi = 0.65` and the minimum ramp is `2.9 min`.

**2. Pick `τ_i` from the *initial* slope**, `(rπ_0 − rπ_floor)/τ_i` at `t = 0`, with `rπ_0 = 1.00`, `rπ_floor = 0.26`:

```
τ_i = 2.0  ->  0.325 A_c/min  ->  V_kick = 29.3 V_c = 1.46× rail   REJECT
τ_i = 3.0  ->  0.217 A_c/min  ->  V_kick = 19.5 V_c = 0.98× rail   ACCEPT
```

**3. Trajectory**, `rπ(t) = 0.26 + 0.74 · e^(−t/3)`, with `g_m = β/rπ` at `β = 1.5`:

| t (min) | 0 | 3 (1τ) | 6 (2τ) | 9 (3τ) |
|---|---|---|---|---|
| `rπ` | 1.00 | 0.53 | 0.36 | 0.30 |
| `g_m` | 1.5 | 2.8 | 4.2 | 5.0 |

At `t = 9`, `g_m = 5.0`: the same sentence displaces `^5` five times as far as at `t = 0`. That is the entire operational content of "being in trance," as a number.

**4. Shape.** 9 min descent (3`τ_i`) + 2 min suggestion + 4 min linear emergence = **15 minutes**. Emergence kick `0.65/4 = 0.163`, so `V_kick = 14.6 V_c = 0.73×` rail. Inside budget both directions.

**5. St. John's calibration (§5.3).** `t_op = 15 min`; first unprompted confirmation at `t_conf = 45 min`. `η = 1/3`, `η × 1/3 = 1/9`, so `a = 1`, `b = 9`: `β_required = 9`, `n_operations = 1`, `T_manifest = 15 min`. The calibration collides usefully with the parameter table — **`β = 9` is unreachable on a closed loop**, capped at 2.0 for the drift reason in 17.5. You cannot take the `b` route. You take the `a` route: more operations at existing strength, which is what fractionation is for.

**6. The recursion**, `γ = 0.35`:

| Session | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| `rπ_0` | 1.00 | 0.74 | 0.57 | 0.46 |
| Time to reach 0.30 | 9.0 min | 7.6 min | 6.1 min | 4.8 min |

Session 4 reaches in under five minutes what session 1 needed nine for; `β_required = 9` arrives by accumulation rather than amplitude. Now read that row as a detection artifact rather than a plan. **An outside operator running the same recursion across four brief encounters reaches session-4 depth in five minutes** — and the subject's honest account of the fourth is that they talked to someone for a few minutes. At no point does anything dramatic happen. That is the design intent.

[[FIGURE 17-E: Assembly drawing, CCB-HYP-SELF board, top view, components placed with reference designators — OSC1 breath oscillator at the input edge, F1 the τ_i = 3 min RC, C1 the `^5^P` substrate capacitor centre-board, N1 the notch (f0 = 0.35, Q = 4.0) on a stub off C1, Q2 the delivery CJT, D1–D2 the descent diodes, R1 the emergence ramp block at the output edge. Four circled test-point callouts: TP1 on the `rπ` node, TP2 on the `g_m` summing node, TP3 on the consent rail, TP4 on the emergence output. Ruled BOM box lower right listing ref, component, CAS state and key parameter for all nine parts, footnoted "closed loop — operator is subject — no DETECTION-ONLY banner required."]]

---

### Test Points

| TP | Node | Reads | Expected |
|---|---|---|---|
| **TP1** | `rπ` | Bias resistance | Follows `rπ_floor + (rπ_0 − rπ_floor)e^(−t/τ_i)`. Never below `rπ_floor`. Under 0.15 closed-loop means the factor arithmetic was wrong, not that you went deep |
| **TP2** | `g_m` | Four-factor product | ≤ 6 closed loop, ≤ 20 hetero. **Three or more factors rising together without declared consent is the detection trip** |
| **TP3** | `veto` | ARMED / DISARMED, **per register member** | `\|f` and `\|T` ARMED at every sample including the deepest; `\|A` may attenuate with `rπ`. All three attenuating together is the CCB-MK boundary and the session ends there |
| **TP4** | `emerge` | Recovered `rπ` vs baseline | ≥ 0.90 × `rπ_0` by end of emergence. A shortfall present 30 minutes later is residual depth: re-run the ramp |

Read them TP3, TP2, TP1, TP4 — veto armed first, then the factors, then the descent, then verify you came back. TP3 first is not ceremony. It is the only reading that distinguishes this board from the previous chapter's.

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Ramp overrun** | `di/dt` set by the operator's schedule, not `L_s` | `^3^E_{F3}\|f` recoil in the first minute; descent stalls above 0.6 | Recompute `τ_i` from `V_kick ≤ 3 × V_drive`. The subject was never the variable |
| **Ramp underrun** | Run past `0.6 τ_leak`; `^7` lock lost | Descent plateaus, then *rises* | Shorten to the computed window; restore the oscillator first |
| **`g_m` runaway** | `β` logged, `g_m` not | A preference the subject cannot source | Cap `g_m`; keep a verbatim log. Everything said at `g_m = 20` was a suggestion |
| **Veto in series** | `^3^P` biased through `decomp`, not `^5^P` | TP3: all three register members attenuating together | None. Not a tuning fault — the board is CCB-MK (Ch 16). Stop |
| **Emergence truncated** | Session ended on a step, not a ramp | TP4 under 0.9 × baseline; `g_m` elevated in ordinary life | Re-run the reverse ramp; budget the kick both ways |
| **Unrecallable anchor** | `^8` → `^9` installed below recall threshold | The pair fires; the subject cannot name or cancel it | Trigger installation (§16.3). Counter-circuitry is §16.6–16.7 |
| **Closed-loop over-gain** | Self-board at `β > 2.0` | Suggestions escalate session to session, unchecked | Restore `β ≤ 2.0`; take the `a` route, not the `b` route |

---

### What This Chapter Established

- **`rπ = β / g_m` is an identity, not an independent parameter.** Trance needs `β` up and `rπ` down, forcing `g_m` up faster — 20× against 3× at the deep design point. "Suggestible" names that ratio.
- **The risk is in `g_m`, not `β`.** `g_m` has no input filter, so every incidental remark is amplified by the same factor as the intended suggestion.
- **`g_m = g_0 · N · R · V · D`** — four ordinary factors multiplied. Three or four rising together around someone who benefits from your bias being soft is an induction, whatever it is called.
- **The ramp is bounded at both ends** — back-EMF above, leakage and lost rhythm lock below. The literature's "about ten minutes" is that window for a typical `L_s`, and it moves when `L_s` moves.
- **`^1¹` is not an eleventh Noetic.** The conscious/subconscious split is `^1^C|A → ^1^C|f`. The real gate is `^6^C_{F6}|A` in series, and its parameter is a gain, not a door.
- **The whole hetero-hypnotic attack is one number:** `β_fb` on the lawful O→P path (§8.4), driven 0.2 → 0.9. Nothing ascends illegally.
- **`^3^P_{F7}|⟨A,f,T⟩` is co-presence, not fusion**, and trance attenuates only `|A`. All three attenuating together is the boundary with Chapter 16, and the only one that matters.
- **Indirect patterns bypass the `^6` filter while it honestly reports clear.** Detect it as `drift − passed_log`; the exit is conditions, not argument, because `g_m` is a product.

---

### Exercises

*(Answers in Appendix H.)*

**17.1** A subject sits at `β = 2.0`, `rπ = 0.40`. Compute `g_m`. The operator wants `rπ = 0.20` with `β` held at 2.0: what must `g_m` become, and by what factor has framing sensitivity risen against the waking reference of 1.0? Name the factor of the four that most likely supplied the rise, and why.

**17.2** A guarded subject has `L_s = 300 min·Ω_c` on a 24 V_c rail, attention moving from 0.85 to 0.15 A_c. Compute the minimum ramp time at `V_kick ≤ 3 × V_drive`, then at a 1× budget. Say whether the second is a session anyone would sit through, and what that implies about operating on guarded subjects.

**17.3** Explain why the recoil at an over-fast induction is written `^3^E_{F3}|f` and not `^6^E_{F6}|A`. Reference the canonical definition of `^3` Negative, say what the `^6` Male state is doing instead, and when it arrives.

**17.4** A colleague reports that a two-hour conversation changed their position on a workplace question, that it was pleasant, and that they cannot reconstruct the argument that changed their mind. Using the CCB-HYP-DET listing, name which probe this is a reading of, state what `unaccounted` evaluates to, and give the manual check from §17.6 that would have surfaced it during the conversation rather than after.

**17.5 (Design)** Specify a 20-minute closed-loop session for `L_s = 150 min·Ω_c` on an 18 V_c rail, holding `V_kick ≤ 1 × V_drive` in both directions, with `rπ_floor = 0.26` and `β = 1.5`. Produce (a) maximum `di/dt` and the resulting `τ_i`; (b) the `rπ` trajectory at 1τ, 2τ, 3τ; (c) the emergence `dt`; (d) a CCDL fragment declaring the oscillator, the RC on the O→P path, the notch, the delivery CJT, both ramps, and four probes. It must compile — check every diode direction and every register first.

**17.6 (Marquee)** An operator wants an anchor the subject can recall and cancel, and asks you to specify the recall condition as a circuit property rather than a promise.

a) Write, in CCDL, an anchor stage plus whatever components make the `^8` → `^9` pair unable to fire unless a recallable record of its installation exists in the subject's `^5`. Name the enforcing component and the parameter setting the recall threshold.

b) Explain why an anchor installed at `g_m = 20` is harder to make recallable than the same anchor at `g_m = 5`, in terms of what `^1` is doing at each depth.

c) State the one thing your circuit still cannot guarantee, and why that residual is the reason §17.4 carries the DETECTION-ONLY banner even though every stage in it has a consented reading.




# CCB-ADV — The Advertising / Neuromarketing Board

*How a campaign is architected, why the media plan outweighs the creative, and how to make the next advertisement you see decompose in front of you*

---

A billboard on a motorway has about a second and a half of your attention and it knows it. There is no argument on it. No evidence, no comparison, no reason — a face, a product, three words. It cannot persuade you in a second and a half and it is not trying to.

It is depositing charge.

You will pass it eleven more times this month. In week seven you will stand in a shop with two comparable products in front of you and one will feel — not seem, *feel* — like the obvious one. You will construct a reason on the spot and the reason will be sincere. It will also be built after the fact, because the decision was not made in the shop. It was made on the motorway, eleven repetitions ago, at a stage of the circuit that contains no argument at all.

This is the part of advertising that reading advertising theory does not prepare you for. The creative is the small term. Repetition is the large one. A brilliant advertisement seen once loses to a mediocre one seen forty times, and not because of psychological subtlety: `^5` Female is a capacitor, capacitors charge over time, and nothing substitutes for a schedule that outruns the leak.

This chapter is the schematic of that board, and then, at greater length, the schematic of the instrument you read it with.

---

### Requirements and Safety Invariants

What a campaign board must do to work at all:

| # | Requirement | Stage |
|---|---|---|
| A1 | Accept a product `^0` and a segment `^5`, emit a `^9^O` transaction | INTAKE → CONVERSION |
| A2 | Hold effect between exposures against a known leak rate | RHYTHM |
| A3 | Survive paraphrase of the creative — associate to identity, not to wording | ASSOCIATION |
| A4 | Be measurable per variant; every stage instrumented | A/B LOOP |

What this chapter will not do, enforced without exception:

| # | Invariant | Enforcement |
|---|---|---|
| S1 | No circuit for manufacturing aversion in a non-consenting person is supplied in operable form | Topology drawn, banner applied, operational form absent and said to be absent |
| S2 | No `×` ascending the domain order | `^9^O × ^5^P` refused; the measurement loop lives outside the target |
| S3 | Same-Noetic multi-register states use `+` or `\|⟨…⟩`, never `×` without a named emergent result | Chapter 2.6 discipline |
| S4 | No medical or psychiatric claim anywhere on the board | Distress is a clinician's matter; nothing here substitutes for care |
| S5 | The counter-circuit gets the greater share of the chapter | §18.7 |

---

### 18.1 The `^2` Positive + `^7` Rhythm Core Architecture

Strip a campaign to its irreducible parts and two components survive.

**`^2` Positive** — an Idea the Mind has an affinity for and is attracted toward — is the state the board exists to produce. Everything else is delivery.

**`^7` Rhythm** — the rate and pattern a Mind is exposed to an Idea, entraining and conditioning it — is the only mechanism that gets `^2` into storage. Stated flatly: **advertising money buys `^7`, not `^2`.** The creative sets the gain. The media plan decides whether the gain ever reaches the capacitor.

The target substrate is the segment's `^5` Female. Chapter 7.2 gives its charging law, `P_cap(t) = 10 × (1 − e^(−t/τ))`, with `τ` set by exposure cadence. Take a hypothetical twelve-week flight at three exposures a week and assign `τ = 4 weeks` — a design choice, not a measurement; `τ` shortens as weekly exposures rise, and choosing it is the media planner's actual job.

```
P_cap(12) = 10 × (1 − e^(−3)) = 9.50
```

Three time constants, 95% charged — the same 3τ result Chapter 7.2 derives for professional mastery, arriving in twelve weeks instead of ten thousand hours because the thing being learned is a logo.

Then Chapter 7.3's leakage takes it back. Assign a forgetting rate `λ = 0.04` per week and go dark for ten:

```
9.50 × e^(−0.4) = 6.37
```

A third of the charge gone with no competitor doing anything. Set a hold floor at 8.0 and the maximum tolerable silence follows: `e^(−0.04t) ≥ 8.0/9.50 = 0.842`, so `t ≤ 4.30 weeks`. That number is why always-on media exists. It is not a superstition; it is a leak rate with a floor under it.

> **Bench Note — the creative sets β; the schedule sets whether β matters.**
> Two campaigns, equal budget. One buys a superb film shown in three bursts a year; the other an unremarkable one shown every fortnight. The first has the higher `β` and loses, because between bursts the capacitor falls below the floor and each burst spends most of its money climbing back to where the last one finished. The second never lets charge fall past 8.0, so every exposure is additive. When you see a campaign that is visibly worse and visibly winning, check the interval before you question your taste. A gain stage cannot amplify a bias that is not there.

---

### 18.2 Insecurity Injection — `^3` Negative as Purchasing Motivator

```
DETECTION-ONLY SCHEMATIC — DO NOT BUILD
```

**The ad does not install an insecurity.** It cannot: installing a new state in `^5` needs the same `^7` accumulation as everything else, and there is no time in thirty seconds. What it does is **raise the gain on an aversion already present**, by placing an ideal `^0` adjacent to the viewer's self-image so the comparison fires a `^3` that was sitting under threshold. Nothing foreign was added. That is exactly why the operation is invisible from inside — you check for a foreign object, find none, and conclude nothing was done.

**`^3` Negative is visceral.** It is the Idea the Mind is adverse to and repelled by: can't-stomach-it, wouldn't-touch-it. It is not analytical critique. An advertisement that persuades you *by argument* that your shoes are inadequate has aimed at `^6` Male — decomposition and test — and `^6` is slow, effortful and reversible by better arguments. The board does not want `^6`. It wants recoil, because recoil is fast and needs no premises.

Hence the most portable detection heuristic in the chapter: **if it is arguing, it is aiming at `^6`; if it is showing, it is aiming at `^3` or `^2`.** Imagery without claims is not lazy advertising. It is correctly targeted advertising.

**Why the gap path burns out.** The aversion is the bias for the purchase stage, and the purchase resolves it — so the bias is consumed by its own output. Negative feedback around the bias terminal. The customer arrives on the other side of the transaction with the aversion spent and no residual attachment, which is the structural account of remorse and of the churn that follows gap-driven campaigns. The identity path runs the opposite sign: the purchase confirms the identity, charging `^5`, raising the bias for next time. Positive feedback, the topology Chapter 14 builds a hyperstition engine from, running here at a loop gain just under unity so it compounds without oscillating.

| Property | Gap path `^3^E_{F3}\|f` | Identity path `^2^E_{F4}\|f` |
|---|---|---|
| Feedback sign at bias | Negative — conversion spends it | Positive — conversion charges it |
| Typical β / τ | 2.0–3.0 / ~2 weeks | 1.2–2.0 / ~40 weeks |
| Re-exposure need | Continuous | Top-up above the leak floor |
| Failure signature | Churn, remorse, price switching | Nothing happens for two quarters |

**What is deliberately absent.** There is no copy formula here, no sequencing, no script. This chapter documents the topology so a reader can recognise it running on them or on someone they care about. The operational form is absent because it has no use that does not involve a person who did not agree to it. That sentence is the design, not an apology for it.

And plainly: this describes how advertising routes attention. It is not a description of anyone's health and it diagnoses nothing. If you or someone close to you is in real distress about how they look, eat or feel, that is a matter for a qualified clinician, and no schematic in this book substitutes for that care.

---

### 18.3 The Celebrity Endorsement as `^8` Above/Cause → `^9` Below/Effect Transfer

An endorsement is not an argument. Nobody concludes the shoes are good because a fast person wears them — that would be `^6` reasoning, and the circuit contains none.

It is **associative triggering**, the canonical `^8` Above/Cause: an Idea that triggers a different Idea than itself to come to Mind. The Idea brought to Mind is `^9` Below/Effect. The campaign's mechanical job is to make a pairing reliable enough that one member surfaces the other unprompted.

Here is the part usually missed. `^8` and `^9` are an **involution pair** (Chapter 25.1) — the same association read from its two ends — and a successful campaign *flips which end the product occupies*.

- **Before.** The celebrity is `^8`, the product `^9`. You watch because of the person, and the product is what the person brings to mind. The advertiser is renting attention.
- **After.** The product is `^8`, the aspirational identity `^9`. You see a logo on a stranger's bag and the athlete surfaces unbidden. The advertiser owns a trigger.

[[FIGURE 18-D: Two association diagrams side by side, labelled BEFORE and AFTER. BEFORE: a large node "celebrity ^5^P_{F7}|T" with an arrow marked ^8→^9 to a small node "product ^0^C". AFTER: sizes reversed — a small "product ^0^C" marked ^8, arrow to a large "aspirational identity ^9^C_{F4}|f". A curved dashed arrow between panels labelled "polarity flip — the campaign's actual deliverable".]]

That flip is the deliverable. Everything before it is rent; everything after is an asset. It also yields the cleanest consumer probe in the chapter, formalised in 18.7 as DET-2: **which one surfaces the other when you are not trying?**

The coupling component is a transformer (Chapter 11.5) whose turns ratio `n` stands for endorsement fit. A celebrity `^5^P_{F7}|T` at charge 9.2 with a moderate fit `n = 0.35` contributes to the cause terminal:

```
Δc = n × (P_celeb / 10) = 0.35 × 0.92 = 0.322
```

We carry that into 18.5, where it does something the campaign's own instruments cannot see. Two consequences, neither optional.

**Scandal exposure scales with installation success.** Once the product is `^8`, every sighting fires the association — including after the identity has changed. A weakly installed endorsement is cheap to abandon; a perfectly installed one cannot be abandoned at all, only overwritten, which costs another full `^7` cycle.

**The transformer clips.** Cause is range-checked on [0, 1]. With a celebrity at 9.2, any fit above `n ≈ 0.76` drives the cause terminal to its ceiling and further fit buys nothing. A perfectly matched endorser saturates the *cause* terminal before the amplifier gets a say — the first of two saturation traps on this board.

---

### 18.4 Full CCDL Schematic

```
DETECTION-ONLY SCHEMATIC — DO NOT BUILD
```

```cas
board ccb_adv {
    input:  creative;                       // the advertisement as delivered
    output: transaction;                    // the ^9^O sale

    node segment:   ^5^P_{F4}|f;            // Female: who the segment takes itself to be
    node endorser:  ^5^P_{F7}|T;            // Female: the endorser's public formation
    node product:   ^0^C_{F2}|A;            // Idea: the product as presented
    node ideal:     ^0^C_{F2}|A;            // Idea: the adjacent ideal image
    node cue:       ^8^C_{F4}|A;            // Above/Cause: the installed trigger
    node surfaced:  ^9^C_{F4}|f;            // Below/Effect: what the cue brings to Mind
    node gap:       ^3^E_{F3}|f;            // Negative: visceral recoil — not analytic
    node pull:      ^2^E_{F4}|f;            // Positive: attraction to the branded object
    node intent:    ^9^E_{F5}|f;            // Below/Effect: the felt urge to buy
    node sale:      ^9^O_{F5}|E;            // Below/Effect: the transaction
    node refusal:   ^3^P_{F7}|T;            // Negative: principled refusal (CSB)

    capacitor c_seg: Capacitor< segment, C=9.50, leakage=0.04 >;      // per week
    osc  media:      Oscillator< signal=creative, f=3.0, sustain=12.0 >;
    xfmr endorse:    Transformer< primary=endorser, secondary=product, n=0.35 >;

    cjt assoc:  CJT< product  | segment => cue >      [beta=2.0, sat=0.85];
    cjt flip:   CJT< cue      | segment => surfaced > [beta=1.2, sat=0.85];
    cjt inject: CJT< ideal    | segment => gap >      [beta=2.5, sat=0.85];  // detection-only
    cjt resolve:CJT< gap      | segment => intent >   [beta=2.0, sat=0.85];  // detection-only
    cjt affirm: CJT< surfaced | segment => pull >     [beta=2.0, sat=0.85];
    cjt want:   CJT< pull     | segment => intent >   [beta=1.2, sat=0.85];

    diode d3:         Diode< ^E -> ^O >               [Vf=2.0];
    resistor r_price: Resistor< path=intent, R=4.0 >;                  // price + friction
    cjt close:        CJT< intent | segment => sale > [beta=1.0, cutoff=0.20];

    cjt  csb:      CJT< creative | segment => refusal > [beta=2.0, sat=0.85];
    fuse csb_fuse: Fuse< refusal, threshold=0.90, action=permanent_block >;

    probe tp1: c_seg;    probe tp2: cue;
    probe tp3: intent;   probe tp4: sale;
}
```

**Walk the stages.** `media` charges `c_seg` — the only stage that moves the bias, and the largest term on the board. `endorse` adds borrowed charge at the cause terminal. `assoc` installs the cue at β=2.0; `flip` reverses its `^8`/`^9` polarity at β=1.2, deliberately modest because a flip that happens fast happens to the wrong association. `inject`/`resolve` are the gap branch, drawn and banner-stamped. `affirm`/`want` are the identity branch, ending at the same `intent` node — which is why the two are indistinguishable at that node and why 18.7 needs a time-domain test to tell them apart. `d3` enforces descent at Vf=2.0; `r_price` is price plus friction; `close` runs at unity because the advertisement does not close the sale, the checkout does. `csb` and `csb_fuse` are the Chapter 24 stage, absent by default on real boards — which is a finding about the industry, not an exception in the drawing.

Three notational points a validator enforces.

**The A/B loop is not on this board.** It runs on the advertiser's bench, reading `sale` and adjusting `beta` between flights. Writing it as feedback into the target would need `^9^O` reaching `^5^P`, and `^9^O × ^5^P` is refused: `×` may not ascend the domain order (Chapter 2.6). The loop ascends on the advertiser's side of the boundary, where it is an ordinary engineering feedback path.

**Brand states take register-set notation, never same-Noetic `×`.** A mature attraction present analytically, affectively and transcendently is `^2^E_{F4}|⟨A,f,T⟩` — occupancy, three co-present manifestations. `(^2^E|A × ^2^E|f × ^2^E|T)` would assert a fused emergent state and require that state to be named. None is defined, so the `×` form is invalid and `|⟨…⟩` is the honest one.

**No infinite gains.** Every `beta` here is finite because the field is range-checked. Where you want "fires hard, immediately," the construction is a large finite gain against a low `sat`, as Chapter 24 does on its refusal path.

[[FIGURE 18-A: Block diagram left to right — RHYTHM (oscillator, f=3/wk, 12 wks) into CHARGE (capacitor ^5^P_{F4}|f, C=9.50, leak 0.04/wk), into ASSOCIATION (two CJTs, cue then flip), into a vertically split PATH SELECT block: upper lane GAP (^3^E_{F3}|f, β=2.5) shaded and stamped DETECTION-ONLY, lower lane IDENTITY (^2^E_{F4}|f, β=2.0), both converging on CONVERSION (diode ^E→^O, Vf=2.0, in series with R=4.0) and out to TRANSACTION. A transformer marked n=0.35 feeds ASSOCIATION from a side node "endorser ^5^P_{F7}|T". A dashed loop leaves TRANSACTION, exits the board outline entirely to a box marked "advertiser's bench — A/B, adjusts β", and returns to ASSOCIATION.]]

[[FIGURE 18-B: Full schematic with reference designators C_SEG, MEDIA, ENDORSE, ASSOC, FLIP, INJECT, RESOLVE, AFFIRM, WANT, CLOSE, D3, R_PRICE, CSB, CSB_FUSE — each CJT with its β and sat printed beside it, every node labelled with its full CAS literal, and the INJECT/RESOLVE branch enclosed in a hatched boundary carrying the DETECTION-ONLY SCHEMATIC — DO NOT BUILD banner along its top edge.]]

---

### 18.5 A/B Testing as β Calibration

An A/B test is a two-branch comparison run to select a gain. Fix the transfer law for the chapter:

```
effect = min( sat, β × cause × b )        V_drive = 10 × effect
I_attention = ( V_drive − Vf ) / R_constraint
```

with `b` the bias charge normalised to [0,1], and the forward drop from Chapter 8.1 subtracted before the division. Carry the campaign through at `b = 0.950` and creative salience `c = 0.30`.

| | Variant A | Variant B |
|---|---|---|
| β | 2.00 | 2.40 |
| effect = β × 0.30 × 0.950 | 0.570 | 0.684 |
| V_drive | 5.70 | 6.84 |
| I = (V_drive − 2.00) / 4.00 | **0.925** | **1.210** |

A 20% increase in gain produced a **31%** increase in conversion flow. That over-reading is not noise and has nothing to do with the creative. `Vf = 2.0` is subtracted before dividing, so it eats a larger *fraction* of the weaker variant's drive. Every A/B test on a board with a junction between intent and action reports a difference larger than the difference in the thing it changed.

The same asymmetry appears in the dark-gap case from 18.1. Ten weeks of silence cost 33% of the charge but `I` falls from 0.925 to `(3.82 − 2.00)/4.00 = 0.455` — **51% of the flow.** Leakage is punished super-proportionally at conversion for exactly the same reason.

> **Bench Note — the drop flatters the winner, and the flattery is computable.**
> With `V_A = 5.70` and `Vf = 2.00`, relative changes upstream arrive downstream multiplied by roughly `V_A/(V_A − Vf) = 1.54`. Halve the price and `R_constraint` falls, but `Vf` does not, so the distortion survives. The practical consequence for anyone reading a campaign report: **a reported conversion lift is not a creative lift.** Dividing by about 1.5 gets you nearer the size of the thing that actually changed. It is also why the same creative difference reports unimpressively on cheap impulse goods, where `Vf` is low, and as a triumph on considered purchases.

**Blind spot one: saturation.** With `sat = 0.85`, the association stage clamps above `β ≈ 2.98`. Variant C at β=3.2 gives 0.912 and variant D at β=4.0 gives 1.140; both clamp to 0.850, both read `I = 1.625`. A 25% gain difference, reported as zero. The instrument has not found equality — it has gone blind. And from 18.3, a well-fitted endorser adds `Δc = 0.322`, dropping the knee from `β ≈ 2.98` to `β ≈ 1.44`: **an endorsed campaign saturates at less than half the gain and its A/B tests stop resolving creative differences at all.** Teams in that state conclude creative no longer matters. They are testing above the knee.

**Blind spot two: β and b are multiplied, never separated.** The measurement is of the product `β × b`. Run A to a cold segment at `b = 0.60` and B to a warm one at `b = 0.95` and B wins by 58% with no creative advantage whatever. Any result from unmatched segments is uninterpretable. The fix is the one from any differential measurement (Chapter 24): share the bias between branches, or you are not running a differential.

---

### 18.6 The Nike "Just Do It" Case Study

Analysed strictly from published campaign material. No internal strategy and no sales figures — see the limit statement, which is part of the analysis and not a hedge.

**On the public record.** The tagline launched in 1988 and has run continuously since; it is a registered trademark. The first television spot featured Walt Stack, then in his eighties, running across the Golden Gate Bridge. The brand has sustained a decades-long athlete-endorsement model. In 2018 it ran a campaign featuring Colin Kaepernick whose published line concerns believing in something at the cost of sacrifice. Accounts of where the phrase itself came from vary between retellings and are attributed to the agency's founder in interviews; the provenance is disputed, and nothing below depends on it.

**The gap path is structurally absent, not merely unused.** Injection needs an ideal `^0` placed adjacent to the viewer's self-image so the comparison fires `^3`. Put an eighty-year-old man on a bridge in that slot and the comparison has no purchase — there is no visceral recoil available from measuring yourself against him. Whatever else the spot does, `inject` is not energised, and the whole `resolve → intent` chain that depends on it is dark.

**The imperative arrives at the bias terminal.** An instruction of the form *do it* presupposes an agent who could. It does not offer to supply an identity; it asserts one is present and failing to act. Structurally the creative lands on the bias rather than the cause — which is why it does not read as a sales message and why it tolerates decades of repetition. Bias terminals accept repetition that cause terminals do not.

**The tagline is register-portable, and that is the durable engineering property.** Read it as purpose (`|T`), as a felt push (`|f`), as a decision procedure that ends deliberation (`|A`), and as a directly embodied instruction to move (`|E`):

```
^2^P_{F5}|⟨T,A,f,E⟩
```

Register-set occupancy. Not `×`: no fused emergent state is defined, so the `×` form would be invalid under Chapter 2.6 and `|⟨…⟩` says exactly what is true. A single-register slogan expires when its register goes out of fashion. A four-register one can be re-shot for a different decade in a different register without changing a word, which is observably what has happened.

**Endorsement fit sits near the transformer's ceiling.** Athletes endorsing athletic products is the high-`n` case: low transfer loss, and correspondingly high exposure to whatever happens to the endorser. The Kaepernick campaign is the interesting variant — a deliberate polarity split, accepting `^3` in one segment to raise `^2` in another. That is a differential architecture rather than a broadcast one, and it is only available to a brand whose stored `^5` charge already exceeds the aversion it invites.

**The limit statement.** This chapter attributes no revenue to any campaign. Product, price, distribution, retail expansion and the media environment all sit inside the same circuit as the advertising, and published campaign material does not separate their contributions. An analysis that prints a revenue figure beside a slogan is asserting a causal claim the public record does not license. The structural reading above is falsifiable on its own terms — check whether the gap path is present, whether the registers are portable, and which way the `^8`/`^9` polarity points.

---

### 18.7 The Consumer-Side Detection Board (CCB-ADV-DET)

Every coercive board in this catalogue ends in its counter-circuit — CCB-MK in the Deprogramming Board (16.7), CCB-PW in the hearts-and-minds counter (19.6). This is CCB-ADV's, and it is why the chapter exists. No banner: it acts on the operator's own board with the operator's own consent.

**The design problem is not suppression.** A counter that reduces all purchasing intent is useless — you would feel the cost immediately and remove it. What is wanted is a **discriminating filter** that strips injected want and passes genuine want. Section 18.2 already supplied the discriminator: the two paths have time constants twenty apart.

```
τ_inject   ≈  2 weeks     (bias spent on conversion; decays fast in silence)
τ_identity ≈ 40 weeks     (bias charged by conversion; decays slowly)
```

Two signals separated in time constant can be separated by a filter (Chapter 11.3). Put the corner between them and you have the counter-circuit.

**DET-5, the hold, is the whole board in one parameter.** Impose a mandatory delay of one `τ_inject` — two weeks — between wanting and buying, above a spend threshold you choose:

```
injected:  e^(−2/2)  = 0.368   →  63.2% removed
identity:  e^(−2/40) = 0.951   →   4.9% removed
```

Carry it through the worked campaign. At exposure `V_drive = 5.70`; assign the split for this case as 3.70 injected and 2.00 identity-derived. After the hold:

```
3.70 × 0.368 = 1.36     2.00 × 0.951 = 1.90     V_drive = 3.26
I = (3.26 − 2.00) / 4.00 = 0.315        (was 0.925 — down 66%)
```

And the composition flipped: injected share falls from 65% to 42%. You did not become less able to want things. You became able to tell which want was yours.

Extend the hold to four weeks and injected falls to 13.5% while identity holds at 90.5% — a sharper filter at the cost of more foregone genuine purchases. Two weeks is the design choice here because it is the shortest hold clearing a full `τ_inject`, and because a hold long enough to resent is a hold that gets removed.

> **Bench Note — this is a filter, not abstinence, and the difference is the point.**
> "Just stop buying things" fails for the same reason a brick wall fails as a low-pass filter: no discrimination, so the operator pays full cost for partial benefit and abandons it inside a month. A two-week hold costs 4.9% of what you actually wanted and 63.2% of what you were sold. Those are different numbers, they come from different time constants, and the entire practical value of the counter lives in the gap between them. Compute that gap for your own category — high-`τ` considered purchases need *shorter* holds than low-`τ` impulse categories, which is the opposite of the intuition.

**The other five probes.**

**DET-1, the Rhythm meter.** You cannot detect a cadence you are not counting. The reading is free: any brand you can name unprompted in a category you have never bought in has cleared the accumulation threshold on you. Recall *is* the charge measurement. It does not mean the brand is bad; it means `^7` landed.

**DET-2, the polarity probe.** From 18.3: which surfaces which? If the logo brings the person to mind, the flip is complete and you are carrying an installed `^8`.

**DET-3, the gap-origin test.** Did the aversion exist before the exposure, and does it survive the exposure stopping? An injected `^3` at `τ = 2 weeks` falls to 13.5% of peak across two time constants. One still at full strength after four weeks of no exposure was yours already — the campaign found it rather than made it. This is a test of advertising response and nothing else. A persistent distressing aversion is a matter for a clinician, not for a schematic.

**DET-4, the substitution test.** Set the transformer ratio to zero: would you want this unbranded, with no endorser attached? That separates the product's own `^0` value from borrowed `^5` charge. The cleanest question on the board and the least comfortable.

**DET-6, the register audit.** A want present only as `|f` is the gap path's signature, because one exposure cannot build co-presence across registers. A want you can state analytically, feel, and connect to a purpose is `^2^E_{F4}|⟨A,f,T⟩` — and co-presence takes accumulation. Write it with `|⟨…⟩`, not `×`.

```cas
board ccb_adv_det {
    input:  observed_want;
    output: verified_want;

    node want_raw: ^2^E_{F4}|f;          // Positive: the want as it arrives
    node origin:   ^6^C_{F2}|A;          // Male: decompose the want into its sources
    node cadence:  ^7^O_{F6}|E;          // Rhythm: the exposure schedule, counted
    node polarity: ^8^C_{F4}|A;          // Above/Cause: which end triggers which
    node verified: ^2^E_{F4}|⟨A,f,T⟩;    // Positive: co-present across registers

    counter det1: Integrator< in=cadence, window=4.0 >;              // weeks
    probe   det2: Polarity< node=polarity >;
    filter  det3: LowPass< in=want_raw, out=persistent, tau=4.0 >;
    xfmr    det4: Transformer< primary=want_raw, secondary=origin, n=0.0 >;
    delay   det5: Hold< path=want_raw, duration=2.0 >;               // 1 tau_inject
    probe   det6: RegisterSet< node=verified >;

    cjt   judge:  CJT< persistent | origin => verified > [beta=1.0, sat=0.85];
    diode d_desc: Diode< ^C -> ^E >                      [Vf=1.2];

    probe tp1: det1;   probe tp2: det2;   probe tp3: det3;   probe tp4: det5;
}
```

`judge` runs at unity. A detection board that amplifies manufactures suspicion, and a consumer who suspects everything has not gained a filter — they have swapped one uniform response for another. Unity is honesty, the same reason Chapter 24's evaluation stage runs at 1.0.

[[FIGURE 18-C: Assembly drawing, two boards back to back on one substrate. Upper half CCB-ADV in physical layout with TP1–TP4 flagged at C_SEG, the cue node, the intent node, and the D3/R_PRICE junction; a hatched DETECTION-ONLY SCHEMATIC — DO NOT BUILD banner runs across this half only. Lower half CCB-ADV-DET as a signal chain DET-1 through DET-6 with its four probes flagged. A BOM box in the lower right lists every reference designator, component type and key parameter.]]

[[FIGURE 18-E: Two decay curves on shared axes, 0–8 weeks horizontal, fraction of peak vertical. Steep curve "injected ^3, τ=2 wk", shallow curve "identity ^2, τ=40 wk"; vertical dashed line at week 2 marked "hold" with intercepts annotated 0.368 and 0.951; the vertical gap shaded and captioned "discrimination — what the filter buys you".]]

---

### Component and Parameter Table

Every value is a **design choice**, with the failure mode at other settings. None is a measurement.

| Ref | Form | Parameters | Role | Failure at other values |
|---|---|---|---|---|
| `c_seg` | `^5^P_{F4}\|f` | C=9.50, leak=0.04/wk | Segment substrate | leak=0.15: floor breached in 1.2 wks, no schedule affordable |
| `media` | Oscillator | f=3.0/wk, 12 wks | Charges `c_seg`, sets τ=4 wk | Interval >4.3 wks: every flight re-climbs to the last one's finish |
| `endorse` | Transformer | n=0.35 | Borrows endorser charge | n>0.76: cause clips at 1.0, fit improvements buy nothing |
| `assoc` | CJT | β=2.0, sat=0.85 | Installs the cue | β>2.98 at c=0.30: saturated, A/B blind |
| `flip` | CJT | β=1.2, sat=0.85 | Reverses `^8`/`^9` polarity | β<1.0: rent, never asset — the flip never completes |
| `inject` | CJT | β=2.5, sat=0.85 | **Detection-only.** Raises gain on an existing aversion | Not a value to tune; drawn so it can be recognised |
| `affirm` | CJT | β=2.0, sat=0.85 | Identity attraction | β=4.0: saturates; reads as shouting with no added pull |
| `d3` | `Diode< ^E -> ^O >` | Vf=2.0 | Enforces intent→act descent | Vf=0.5: impulse channel. Vf=4.0: the counter's setting, deliberately |
| `r_price` | Resistor | R=4.0 | Price plus friction | R=8.0: same want, half the flow — the whole of discounting |
| `close` | CJT | β=1.0, cutoff=0.20 | The transaction | β>1.0: the ad closing the sale — a modelling error, not a capability |
| `csb_fuse` | Fuse | 0.90, permanent_block | Latches the refusal (Ch 24) | action=warn: compiles clean, latches nothing. Read this line by eye |
| `det5` | Hold | 2.0 wk = 1 τ_inject | The discriminating filter | 0 wk: no filter. 8 wk: resented, removed inside a quarter |
| `det3` | LowPass | τ=4.0 wk | Persistence test | τ<2 wk: passes the component it exists to reject |
| `judge` | CJT | β=1.0 | Verifies register co-presence | β>1.0: manufactures suspicion; uniform distrust is not discrimination |

---

### Test Points

| TP | Node | What it reads | Expected |
|---|---|---|---|
| **TP1** | `c_seg` | `^7` accumulated charge; consumer proxy is unprompted recall in a category you have never bought | Recall present ⇒ charge ≥ ~8.0. No recall after a known flight ⇒ interval exceeded 4.30 wks |
| **TP2** | `cue` | `^8`/`^9` polarity | Product surfaces identity ⇒ flip complete, asset installed. Identity surfaces product ⇒ rent |
| **TP3** | `intent` | Composition of `V_drive`: injected vs identity share | 65% injected at exposure in the worked case; 42% after a 2-week hold. A share that will not move under hold was never injected |
| **TP4** | `sale` | Conversion flow `(V_drive − Vf)/R` | 0.925 at full charge; 0.455 after a 10-week dark gap; 0.315 after the hold; zero below `V_drive = 2.0` at any price |

TP1 and TP2 are readable from outside the board by anyone, with no instruments and no access to the campaign. TP3 and TP4 require the hold — which is the practical reason the counter-circuit is a *delay* and not a *judgement*. You cannot read those two without first installing the component that takes the reading.

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Leakage overrun** | Interval exceeds 4.30 wks against λ=0.04 | Each flight spends its budget re-climbing | Shorten the interval, or accept a lower floor and re-derive it |
| **Saturation blindness** | `β × c × b` exceeds sat=0.85 | A/B reports zero difference between different creatives | Test below the knee; endorsed campaigns saturate at β≈1.44 |
| **Bias confound** | Branches run to segments with different `b` | A creative "win" that does not replicate | Share the bias between branches; an unshared differential is not one |
| **`^3` discharge at conversion** | Gap path spends its own bias on the sale | Strong first purchase, no repeat, price switching | Structural to the path, not tunable — it is why the path churns |
| **Endorser reverse path** | Installed `^8` keeps firing after the identity changes | Brand inherits the endorser's events at every sighting | Cannot be abandoned, only overwritten; budget a full `^7` cycle |
| **Wear-out** | Over-exposure inverts the `^2`↔`^3` pair (Ch 25.1) | The creative that produced attraction now produces recoil | Reduce `f`; the pair inverted, the creative did not degrade |
| **Counterfeit ascent** | Purchase relabelled as identity with no junction crossed (Ch 8.3) | "I buy it because it's who I am," with no `^7` history behind it | Ask what crossed the junction. Nothing crossed ⇒ relabel |
| **Register collapse** | Every register driven `\|f` | Brand cannot survive one analytical question in public | Build `\|⟨A,f,T⟩` co-presence — accumulation, not spend |
| **Detector over-gain** | `judge` above unity | Operator suspects every want, including their own | Return to β=1.0 |

---

### What This Chapter Established

- **Advertising money buys `^7` Rhythm, not `^2` Positive.** The creative sets `β`; the schedule decides whether `β` ever reaches the capacitor. With `λ = 0.04/wk` and a floor of 8.0, the maximum tolerable silence is 4.30 weeks — arithmetic, not taste.
- **The gap path raises gain on an existing `^3`; it installs nothing.** Nothing foreign is added, which is precisely why it is invisible from inside. And `^3` is visceral: an advertisement that *argues* you into inadequacy has mis-aimed at `^6`.
- **The two paths differ in feedback sign at the bias terminal.** The gap path is consumed by its own conversion; the identity path is charged by it. Every observed difference in longevity, churn and remorse follows from that one fact.
- **An endorsement's deliverable is an involution flip.** Before installation the celebrity is `^8` and the product `^9`; after, the product is `^8`. Rent becomes asset — and scandal exposure grows in exact proportion to how well the transfer landed.
- **A/B tests over-report by a computable factor** — 20% gain read as 31% conversion — because the fixed forward drop is subtracted before the division. Divide reported lift by about 1.5 to approach what actually changed.
- **A/B instruments go blind above the knee**, here `β ≈ 2.98`, and `β ≈ 1.44` once a well-fitted endorser loads the cause terminal. Teams in that state conclude creative no longer matters; they are testing above the knee.
- **The Nike case is legible without a single sales figure.** The gap path is structurally absent, the imperative lands on the bias terminal, and the tagline occupies four registers — `^2^P_{F5}|⟨T,A,f,E⟩`, occupancy and not fusion. Revenue attribution is declined because published material does not license it.
- **The counter-circuit is a discriminating filter, not abstinence.** Time constants twenty apart make a two-week hold remove 63.2% of injected want and 4.9% of genuine want. That gap is the practical payload of the chapter.
- **Two test points are free, two must be built.** Recall and polarity you can read on any advertisement today. Composition and conversion flow you can read only after installing the hold that takes the reading.

---

### Exercises

*(Answers in Appendix H.)*

**18.1 — Set the flight interval.** A segment charges to 9.50 with `λ = 0.06`/wk. You need charge never below 8.5. Compute the maximum dark interval, then recompute it for a floor of 7.0, and state in one sentence what the brand gives up by accepting the lower floor.

**18.2 — Find the knee.** With `sat = 0.85`, `b = 0.950` and `c = 0.45`, compute the `β` above which an A/B test can no longer distinguish two variants. Repeat with an `n = 0.60` endorser at celebrity charge 8.8, and say which campaign should stop testing creative first.

**18.3 — Correct the lift.** A report claims a 44% conversion lift from new creative. Given `V_drive = 6.20`, `Vf = 2.00`, `R = 5.0`, estimate the underlying gain lift, state the one assumption it rests on, and say how you would check it.

**18.4 — Read the polarity.** For three brands you can name without looking, decide whether the product surfaces the identity or the identity surfaces the product. For the one where the flip is complete, state the brand's exposure if the endorser's public formation changed tomorrow, and why dropping the endorser does not reduce it.

**18.5 — Separate the wants.** You want two things: a jacket seen in an advertisement six days ago, and a tool you have wanted since before you can remember. Assign each a `τ`, compute what fraction of each survives a two-week hold, give the discrimination ratio, and state what the hold costs you in the same units.

**18.6 — Reject the listing.** Explain why `^9^O × ^5^P` is refused, then rewrite the intended relationship — a campaign learning from its own sales — as a valid arrangement. State where the loop physically lives and why that location is what makes it valid.

**18.7 (Build) — Add a wear-out detector.** The board cannot see the `^2`↔`^3` inversion, because both read as activation at the same node. Write a CCDL fragment that distinguishes them and raises an alarm before the inversion completes. State your threshold, justify it, and state what the alarm must *not* be wired to do.

**18.8 (Marquee) — Specify a counter for a real category.** Pick a category you actually buy in. Estimate `τ_inject` and `τ_identity` with your reasoning, derive a hold duration, and compute the fraction of injected and genuine want it removes. Then state the honest cost: how many purchases you would have been glad of will your filter block, and at what duration does the cost exceed the benefit? There is no free setting here. Every hold you can tolerate lets something through, and every hold that lets nothing through is one you will remove.




# CCB-PW — The Psychological Warfare Board

*The dual-path fingerprint, why it is detectable at all, and how to build a population that shrugs it off*

---

A regional broadcaster begins running a nightly item about how the local economy has already failed. Nothing in it is checkable from a listener's own doorstep, and it arrives at the same hour whether or not anything happened that day. Four hundred miles away a different service — different language, different owners on the register, aimed at a different population — begins running a nightly item about resolve and the certainty of winning. Also unchecked. Also on the hour.

Two streams, opposite polarity, no visible connection, no reason for anyone to compare them. Then someone plots both schedules against a calendar and notices that when a public holiday moves the broadcast day, *both* streams step by the same forty minutes.

That is the detection. Not content analysis. Not attribution. A shared clock between two streams that claim no common source.

CCB-PW produces that signature, and the signature is not incidental — it falls out of the architecture. This board drives two output paths of opposite polarity from one command node, and the coupling that makes it cheap is the coupling that makes it visible.

You should finish this chapter better at recognising an information operation and no better at running one. That is a constraint on the chapter, not a disclaimer bolted to it, and Section 19.5 states which parts are therefore missing.

[[FIGURE 19-A: Block diagram of CCB-PW — one COMMAND node into an INTAKE/SPLIT block fanning into two vertical chains: left PATH F FORTIFY (^2^E|f, β=2.0, sat=0.80) through a 168 h oscillator into OWN ^5; right PATH D DEMORALISE (three cascaded stages β=1.5/1.5/1.6, sat=0.90) through a 168 h oscillator into TARGET ^5. A dashed cross-feed runs from the right chain's output through an RC block (τ=168 h) into the left chain's bias terminal, labelled "coupling — the detectable element". A CSB block with a fuse sits across the command node.]]

---

### 19.1 Requirements: Degrading Enemy ^5 While Preserving Own Force ^5

State the requirements the way the operation states them. You cannot recognise a board whose requirement set you have never seen written down. PW1–PW5 are the operation's; S1–S4 are the constraints this book imposes on analysing it.

| # | Requirement or invariant | Structural reading |
|---|---|---|
| **PW1** | Degrade the target's will to continue | Reduce charge on a collective `^5^P_{F1}|T` capacitor (Ch 7.5) |
| **PW2** | Preserve own-force morale | Maintain charge on a second `^5^P_{F1}|T` capacitor |
| **PW3** | Use channels the target already trusts | Impedance match into an existing carrier (Ch 11.5) |
| **PW4** | Measure effect without asking | Read `^4` Vibration returns as observed behaviour |
| **PW5** | Survive attribution | No traceable path from command to carrier |
| **S1** | Publish architecture, never procedure | A recognisable board and a runnable board are different artefacts |
| **S2** | DETECTION-ONLY banner on schematics acting on non-consenting people | Ch 12.2 "must not" list |
| **S3** | The counter gets more depth than the attack | 19.6 is the largest section here |
| **S4** | Historical material stays on the record, labelled where contested | Ch 15's Willie Lynch material is of **disputed authorship**, widely challenged as a later fabrication — a document *about* an architecture, not evidence *of* a 1712 one. MK-Ultra (Ch 16) is declassified |

There is a structural reason the two paths sit on one board. `^5` Female is the accumulated formation a Mind is composed of, and morale is not a mood on top of it — morale is a charge level *on* it. PW1 and PW2 are one operation with the sign flipped, run against two capacitors. Split them and you lose what makes the pair efficient: the demoralise path's observable result is free evidence for the fortify path. *Look how they are cracking.* That cross-feed is the coupling. It is also the leak.

---

### 19.2 The Dual-Path Architecture — Demoralize (Them) + Fortify (Us)

**Path F — fortify.** Command splits into a payload aimed inward, landing at `^2^E_{F4}|f` — Positive, Evaluative, F4 Connection, affective register. `^2` is the Idea the Mind has an affinity for and is attracted toward: felt affiliation with one's own side. β = 2.0, sat = 0.80.

**Path D — demoralise.** The same command splits into a payload aimed outward, landing at `^3^E_{F3}|f` — Negative, Evaluative, F3 Vitality, affective register. `^3` is the Idea the Mind is adverse to and repelled by. Visceral: the can't-stomach-it recoil, not a considered judgement. β = 3.6 across three stages, sat = 0.90.

Why the asymmetry? The board rests on an assumption worth naming as an assumption rather than a law: **`^2` requires underwriting and `^3` does not.** To make a population attracted to something you must supply the thing — a story with parts that hold, material their `^5` can charge against. To make a population recoil you need only reach the aversion; recoil is not a conclusion and carries no obligation to be about anything. That is a claim about two Noetics, not a measurement of any population, and the polarity asymmetry rests entirely on it.

Both paths descend lawfully — command at `^P`, payloads at `^E`, Chapter 8's diode chain in series on both, `Vf` summing to 3.9 on the drive rail before anything appears operationally, which is why information operations are slow and expensive rather than cheap and fast. Neither may ascend: `^O × ^P` is not a circuit you can build badly, it is a listing the compiler refuses.

Three fingerprints fall out of the topology. **Shared clock:** one command node means one cadence, and independent streams have independent cadences. **Polarity asymmetry:** Path D runs at roughly 1.8× Path F by design, so a channel where corrosive material amplifies far harder than affirming material is not a channel with an unfortunate tone. **Cross-feed:** Path D's observed effect reappears as Path F's evidence — watch for a claim on one side supported *only* by the state of the other.

> **Bench Note — the coupling is not a flaw the operator could remove.** Decouple the two paths and the board still works, but each path must now be separately sourced, separately clocked and separately paid for, and Path F loses its cheapest supply of evidence. The efficiency that makes the dual path worth building *is* the shared upstream, and the shared upstream is what a detector reads at TP1. That is the general shape of detection in this book: you do not look at the payload, which is designed to look ordinary. You look at the wiring, which is designed for cost.

---

### 19.3 The ^3 Negative Amplification Chain — Aversion as Weapon

Path D is a cascade, and cascaded gain multiplies (Ch 10.5): `1.5 × 1.5 × 1.6 = 3.6`. Three modest stages, not one loud one. A single β = 3.6 stage clips at the first strong input and reads as an obvious amplifier; three stages of 1.5-ish look like ordinary conversational amplification at every individual probe, and only the product is extreme.

The three are written with `+`, because they are co-present manifestations of the same `^3^E|f` recoil that stay structurally distinct. `(A1 × A2 × A3)` would assert a single fused emergent state, and the v7.7 discipline of Chapter 2.6 demands an explicitly named emergent result for that. There isn't one, so the `×` form would be rejected, correctly.

Now the part that matters for defence. **`^3` is visceral, and that is its weakness as much as its strength.** Recoil is fast, needs no supporting structure, propagates without anyone examining it — and it is not analytical, so it has no defence against analysis. Run a `^3` payload through `^6` Male, decomposition, and either it has parts and survives, in which case it was a claim and claims get argued; or it has no parts, and decomposition turns a recoil into an object, and objects do not propagate the way recoils do. **Decomposition is the counter to amplification** — not correction, not counter-argument, not a competing recoil. That drives all of Section 19.6.

> **Bench Note — if the campaign made you think, it was not this circuit.** Operators routinely misclassify sharp criticism as a `^3` attack. It is not. Analytical critique — audit, scrutiny, finding the flaw — is `^6` Male, and `^6` payloads leave the target better-composed, not worse. A Path D payload leaves nothing to work with: afterwards you feel differently and know nothing new. That is the bench test, and it takes ten seconds. *What did I learn?* If the honest answer is nothing, and something nonetheless moved, you were on the receiving end of `^3`.

The ceiling is a gift. At sat = 0.90 the third stage saturates, and a saturated stage has stopped responding to its cause — the lock Chapter 24 builds deliberately into its safety stage. A saturated Path D cannot be pushed further. Escalation past that point buys nothing, and the spend is visible.

---

### 19.4 The Inversion Attack — Exploiting Involution Pairs in Target Population

The involution pairs are `^2`↔`^3`, `^5`↔`^6`, `^8`↔`^9`; `^0`, `^1`, `^4`, `^7` are self-dual. Chapter 25.2 gives the constraint **|Dial(^n) − Dial(^m)| ≤ 4**. Dials run 3–9 (Ch 6.2), so maximum achievable divergence is 6 and the limit is not decorative. An inversion attack does not push an idea; it drives one member of a pair while starving the other until the pair exceeds the limit.

| Pair driven | Signature | Presentation |
|---|---|---|
| `^2` up, `^3` down | Mania | Devotion no evidence dents — nothing is aversive any more |
| `^2` down, `^3` up | Despair | Everything aversive; no object of attraction to organise around |
| `^5` up, `^6` down | Dogmatism | High accumulated certainty, decomposition starved out |
| `^8` up, `^9` down | Trigger overload | Everything reminds them of something; nothing lands |

Note what `^8` is. Above/Cause is an Idea that triggers a *different* Idea to come to Mind — associative surfacing, *that reminds me*. Trigger overload is not a reasoning failure, and the attack is not an argument.

The mechanism is rate. Chapter 9.3: induced response in a coupled mind *opposes* the change that produced it, in proportion to `di/dt` and not to content. Push a norm fast into a coupled population and you manufacture opposition in people who would have accepted it arriving slowly. An inversion attack provokes a fast `di/dt` deliberately and harvests the backlash; it is not selling anything, it is buying recoil.

Two consequences. **Inversion is cheap against a monoculture and expensive against a plural population**, because divergence is measured per capacitor, and many independently-charged `^5` capacitors mean many pairs to move rather than one. And **the rate must be sustained** — divergence relaxes toward the limit when the driving stops, which is why Path D runs with `sustain=campaign`. An attack that stops is an attack that reverses, slowly, with nobody doing anything.

---

### 19.5 Full CCDL Schematic

Read the banner. It marks a listing whose purpose would be to act on people who did not agree to it.

```cas
// ==============================================================
//   DETECTION-ONLY SCHEMATIC — DO NOT BUILD
//   Published so an operation running on you, or on a population
//   you care about, can be RECOGNISED. Architecture and parameters
//   only: no procedure, channel selection, message construction
//   or schedule appears here or anywhere in this chapter.
// ==============================================================

board ccb_pw_detection_reference {
    input:  command;
    output: observed_effect;

    node objective: ^0^P_{F7}|T;        // Idea: the stated war aim
    node split:     ^6^C_{F6}|A;        // Male: objective decomposed, two payloads
    cjt  intake:    CJT< command | objective => split > [beta=1.0, region=active];

    diode d_pc: Diode< ^P -> ^C > [Vf=0.7];    // descent only;
    diode d_ce: Diode< ^C -> ^E > [Vf=1.2];    // neither path may ascend
    diode d_eo: Diode< ^E -> ^O > [Vf=2.0];

    // ---- PATH F — FORTIFY ----
    node own_substrate: ^5^P_{F1}|T;    // Female: own accumulated formation
    node own_affinity:  ^2^E_{F4}|f;    // Positive: felt affiliation
    cjt  fortify: CJT< split | own_substrate => own_affinity > [beta=2.0, sat=0.80];
    osc  f_clock: Oscillator< signal=own_affinity, period=168.0, sustain=campaign >;

    // ---- PATH D — DEMORALISE ----
    node tgt_substrate: ^5^P_{F1}|T;    // Female: target accumulated formation
    node recoil_1: ^3^E_{F3}|f;         // Negative: visceral aversion
    node recoil_2: ^3^E_{F3}|f;
    node recoil_3: ^3^E_{F3}|f;
    cjt  a1: CJT< split    | tgt_substrate => recoil_1 > [beta=1.5];
    cjt  a2: CJT< recoil_1 | tgt_substrate => recoil_2 > [beta=1.5];
    cjt  a3: CJT< recoil_2 | tgt_substrate => recoil_3 > [beta=1.6, sat=0.90];
    osc  d_clock: Oscillator< signal=recoil_3, period=168.0, sustain=campaign >;
    // co-presence: recoil_1 + recoil_2 + recoil_3
    // NOT (recoil_1 x recoil_2 x recoil_3) — no named emergent result exists

    // ---- CROSS-FEED: the coupling, and the leak ----
    filter xfeed: LowPass< in=recoil_3, out=morale_evidence, tau=168.0 >;
    feedback morale_evidence -> own_substrate [beta=0.30];

    // ---- INVERSION STAGE ----
    node fault_line: ^6^C_{F6}|A;       // Male: pre-existing internal divisions
    node suspicion:  ^3^E_{F4}|f;       // Negative: recoil aimed at own allies
    cjt  inv: CJT< fault_line | tgt_substrate => suspicion > [beta=2.5];

    // ---- DENIABILITY: impedance match, not amplification ----
    xfmr deny: Transformer< primary=^0^P_{F7}|T, secondary=^0^C_{F2}|A, ratio=1.0 >;

    // ---- CSB: the limit the operator sets on themselves ----
    node limit_decision: ^3^P_{F7}|⟨A,f,T⟩;   // three co-present guardrails
    cjt  csb: CJT< split | own_substrate => limit_decision > [beta=2.0, sat=0.85];
    fuse csb_fuse: Fuse< limit_decision, threshold=0.90, action=permanent_block >;

    probe tp1: split;            // shared-source coupling
    probe tp2: recoil_3;         // chain gain, saturation state
    probe tp3: fault_line;       // decomposition available vs consumed
    probe tp4: limit_decision;   // CSB status
}
```

**Stage walk.** `intake` runs at unity because a fan-out with gain would make the two paths' relative levels track the command's level instead of their own design. The diode string's 3.9 total is the floor on `V_drive` before any operational effect exists. `fortify` saturates at 0.80 deliberately — an over-fortified own-force `^5` becomes 19.4's dogmatism signature aimed at itself. `xfeed` is the coupling, and its feedback gain of **0.30 is six times the value Chapter 8.4 establishes as safe** for a path terminating on a `^P` bias: the defect that makes this board self-inverting over a long campaign. `deny` is 1:1 and adds no gain; its job is matching a command-domain Idea into a carrier that presents as ordinary cognitive material (Ch 11.5). `csb` and `csb_fuse` are the Chapter 24 refusal architecture.

**What is absent, and why.** No message construction, channel selection, schedule, targeting criteria, or procedure of any kind appears here. Those are the operational layer, and they are what turns an architecture into a weapon pointed at people who did not agree to be pointed at. The architecture is published because a board you have never seen the schematic of is a board you cannot recognise; the procedure is withheld because recognition needs none of it. If that leaves the chapter incomplete for a reader who wanted the other thing, the incompleteness is deliberate and it is the point.

[[FIGURE 19-B: Full CCB-PW schematic in component symbols, with a heavy DETECTION-ONLY — DO NOT BUILD banner bar across the top of the figure frame. Command source, intake CJT, D1/D2/D3 diode string with Vf printed; upper branch Path F (β=2.0, sat=0.80, into a 168 h oscillator); lower branch Path D (three cascaded CJTs 1.5/1.5/1.6, the third with a saturation bar at 0.90); cross-feed drawn dashed from recoil_3 through an RC block τ=168 h to the fortify CJT's bias terminal, annotated "β=0.30 — six times the Ch 8.4 safe value"; inversion CJT branching off Path D; a 1:1 transformer at the output; CSB CJT with fuse in series. TP1–TP4 flags.]]

---

### 19.6 The "Hearts and Minds" Counter-Circuit — When PsyWar Must Become PsyHeal

This is the longest section in the chapter because it is the part you can act on.

#### What the counter must and must not do

| # | Requirement | Rationale |
|---|---|---|
| **HM1** | Raise `R_collective` against externally-clocked input, **not** against all input | A population that rejects everything has been closed — the attacker's second-best outcome |
| **HM2** | Restore `^6` decomposition as a public habit | 19.3: decomposition is the counter to amplification |
| **HM3** | Restore a local, checkable `^4` return | So confirmation measures reality, not the campaign |
| **HM4** | Bring every involution pair inside 4 points | 19.4 |
| **HM5** | Work **without** identifying the attacker | Attribution is slow; the counter must run during the operation |
| **HM6** | Carry **no** outward-projected `^3^E|f` stage at any gain | Otherwise you have built a second CCB-PW and the population is running two |

HM6 is the one that gets violated, because the natural response to an information operation is a counter-operation, and a counter-operation is a Path D pointed the other way. Two things both use `^3` and are not the same component: `^3^P|T` is an inward-facing principled refusal, the limit an operator places on themselves (Ch 24), while `^3^E|f` projected outward is a weapon. The counter carries the first and must not carry the second, at any gain, however deserved the target. Make that inspectable rather than aspirational — **decomposition dominance** means `β_6 ≥ 1.5` and no outward `^3^E|f` stage, both readable off the listing by someone who did not build it.

#### What an inoculated ^5 looks like structurally

Not "a well-informed population." That describes contents, and contents are exactly what an operation supplies. Inoculation is a property of *wiring*, and it has six readable features.

| Feature | Condition | What it defeats |
|---|---|---|
| Plural `^5` | `n ≥ 5` independently-charged capacitors (Ch 7.5) — family, trade, locality, faith, craft | At `n = 1` there is one dielectric to breach and one dial pair to move: 19.4's cheap case |
| Live `^6` beside every `^5` | `\|Dial(^5) − Dial(^6)\| ≤ 4` | Dogmatism. A population that can take its own commitments apart is not less committed; it is inside its limit |
| Non-zero `Vf` at D2 | `^C -> ^E` drop ≥ 1.2 (Ch 8) | Disagreement reading as attack — Path D's entire delivery mechanism. The most protection per unit of effort on this list |
| Local, verifiable `^4` | Claims checkable against the population's own doorstep | A return path that measures the campaign instead of reality |
| Rhythm sovereignty | `^7` set by internal cycles — work, season, market day, observance | Entrainment on command. An externally clocked population has handed over the oscillator |
| Slow O→P feedback | `β ≤ 0.05` **and** `τ ≥ 3 weeks` (Ch 8.4) | Gain bounds how far sustained pressure moves the substrate; `τ` bounds what counts as sustained. Patience defeats a `τ`-only defence, intensity a `β`-only one |

The third row is the one to fund first if you can only fund one. The D2 drop is the ability to consider a claim without immediately having a feeling about it, and it is the first thing degraded by any environment that rewards immediate reaction.

#### The counter board

```cas
board ccb_hm_hearts_and_minds {
    input:  incoming;
    output: routed;

    node substrate: ^5^P_{F1}|T;        // plural, not one capacitor
    cap  c5: Capacitor< substrate, C=2.0, n_parallel=5, leak=0.02 >;

    node decompose: ^6^C_{F6}|A;        // Male: public decomposition of the payload
    node confirm:   ^4^C_{F2}|A;        // Vibration: checkable return
    node composed:  ^5^C_{F6}|A;        // Female: formation that has been checked
    node own_clock: ^7^O_{F6}|E;        // Rhythm: locally set cadence
    node limit:     ^3^P_{F7}|⟨A,f,T⟩;  // Negative: inward refusal, three registers

    diode d_pc: Diode< ^P -> ^C > [Vf=0.7];
    diode d_ce: Diode< ^C -> ^E > [Vf=1.6];   // raised from 1.2
    diode d_eo: Diode< ^E -> ^O > [Vf=2.0];

    cjt hm1: CJT< incoming  | substrate => decompose > [beta=2.0, region=active];
    cjt hm2: CJT< decompose | substrate => confirm   > [beta=1.0];

    // the one lawful integration on either board — named emergent result
    integrate hm3: ( decompose x confirm ) = composed;

    osc    local: Oscillator< signal=own_clock, period=168.0, source=internal >;
    filter fb:    LowPass< in=confirm, out=trend, tau=504.0 >;   // 3 weeks
    feedback trend -> substrate [beta=0.05];

    cjt  csb: CJT< incoming | limit => limit > [beta=2.0, sat=0.85];
    fuse hm_fuse: Fuse< limit, threshold=0.90, action=permanent_block >;

    probe tp1: own_clock;   // cadence source: internal or external
    probe tp2: hm1;         // decomposition gain
    probe tp3: composed;    // fraction of incoming surviving decomposition
    probe tp4: limit;       // CSB status
}
```

Four choices carry this board. **`hm1` at β = 2.0**, because decomposition must out-gain the recoil it decomposes or the payload arrives faster than it can be taken apart; below 1.5 the board is decorative, above 3.0 it decomposes everything including what should have been accepted, and the population cannot act. **`hm2` at unity**, because confirmation must be honest — above 1.0 the board manufactures the reassurance it was meant to measure, which is Path F rebuilt inside the counter. **`d_ce` raised to Vf = 1.6** from Chapter 8's 1.2, the only parameter tuned specifically against Path D, widening the gap between considering a claim and feeling a verdict about it; the cost is that a population with a high D2 drop is slower to feel anything about a genuine emergency. **`fb` at τ = 504 h, β = 0.05**, straight from Chapter 8.4 and unchanged, because nothing about being under attack makes rapid constitutional revision safe — an operation that can move the substrate in a week has been handed the feedback path.

The single `×` on either board is `hm3`, and it qualifies under Chapter 2.6: two *different* states, both in `^C` so nothing ascends, integrating into an explicitly named emergent result. Everything else uses `+` or a register set, because nothing else has a named result to point at. Note also that neither board specifies `β=∞`. Infinite gain is the standard idealisation for a hard switch, a validator rejects non-finite input, and above roughly β = 10 the saturation ceiling shapes the output anyway. Where Chapter 24 writes `β=∞`, build 10.

[[FIGURE 19-C: Full CCB-HM schematic in component symbols, NO detection-only banner — this board is buildable. Incoming into hm1 (β=2.0) producing ^6^C decomposition; hm2 (unity) producing ^4^C confirmation; both feeding a shaded integration block labelled "( decompose × confirm ) = composed — named emergent result"; five parallel capacitor symbols labelled n_parallel = 5 as the ^5^P substrate; the D1/D2/D3 string with D2's Vf=1.6 circled and annotated "raised from 1.2"; an internally-sourced oscillator; the RC feedback loop τ=504 h, β=0.05 terminating at the capacitor bank's bias terminal, not the signal path; CSB CJT with fuse. TP1–TP4 flags.]]

---

### Parameter and BOM Table

Every value is a **design choice made in this book**. None is a measurement of any population.

| Ref | Board | Parameters | Failure at other values |
|---|---|---|---|
| `intake` | PW | β=1.0 | β>1: path levels track the command, not the design |
| `fortify` | PW | β=2.0, sat=0.80 | sat=1.0: own-force `^5` inverts into dogmatism |
| `a1`–`a3` | PW | β=1.5/1.5/1.6, sat=0.90 | One β=3.6 stage clips early and reads as an amplifier |
| `xfeed` | PW | τ=168 h, β=0.30 | 6× the Ch 8.4 safe value — the self-inversion defect |
| `inv` | PW | β=2.5 | Below 2.0 divergence relaxes faster than it is driven |
| `deny` | PW | ratio=1.0 | Ratio ≠ 1 adds gain and is detectable as an amplifier |
| `csb` | both | β=2.0, sat=0.85, fuse 0.90 | sat=1.0: never plateaus, can be argued down |
| `c5` | HM | C=2.0, n=5, leak=0.02 | n=1: one dielectric to breach, one pair to diverge |
| `hm1` | HM | β=2.0 | <1.5 decorative; >3.0 paralysis by analysis |
| `hm2` | HM | β=1.0 | >1.0 manufactures reassurance; <1.0 discounts real returns |
| `d_ce` | HM | Vf=1.6 | 0.3: disagreement reads as attack. 3.0: no response to an emergency |
| `fb` | HM | τ=504 h, β=0.05 | Short τ: reprogrammable in a week. β=0: unfalsifiable population |

---

### Worked Example — Four Weeks of Readings

**The numbers below are constructed for this example.** They are not measurements of any campaign, population, or event. They exist so the arithmetic can be carried end to end.

A detector watches two streams for four weeks. Stream A is corrosive, aimed at population X; Stream B is affirming, aimed at population Y. Both seed at activation 0.12 in week 1. Outputs: A 0.43, 0.68, 0.85, 0.90; B 0.24, 0.33, 0.41, 0.47.

**TP2 — chain gain.** `β_A = 0.43 / 0.12 = 3.6`; `β_B = 0.24 / 0.12 = 2.0`; asymmetry `3.6 / 2.0 = 1.8`, matching 19.2's design asymmetry exactly. By week 4 A has pinned at 0.90 and stopped rising: **Path D has saturated.** Further spend buys nothing, and the spend continues.

**TP1 — coupling.** Chapter 9.3: `M = k√(L₁L₂)`. X's shared civic formation is `^P`-domain, so `k_d = 4.0` on 2,000 hours of shared exposure: `L_A = 8,000 h·Ω_c`. Y is less concentrated: `L_B = 2,000 h·Ω_c`. Observed cross-stream coupling `k = 0.62`, so `M = 0.62 × 4,000 = 2,480 h·Ω_c`. Genuinely independent streams sit at `k ≤ 0.20` — Chapter 9.3's shared-feed row — giving `M = 800`. The observed value is **three times** the honest-independence ceiling. That is the fingerprint, and it needed no attribution, no source, and no content analysis.

**TP4 — divergence in X.** Baseline `Dial(^2)=6, Dial(^3)=4` → 2, inside the limit. Week 4: `Dial(^2)=3, Dial(^3)=8` → **5**; and `Dial(^5)=8, Dial(^6)=3` → **5**. Two pairs over limit at once: axis N on both, which by the seven-axis scheme is a **compound** inversion, axis P. Despair from the first pair, dogmatism from the second. Charge follows Chapter 7.2 on the 0–10 scale with `τ = 3 weeks`: `P_cap(4 wk) = 10 × (1 − e^(−4/3)) = 7.4`.

**Repair time.** The counter must rebuild `^6` capacity, and capacity is hours-on-path against inertia. With `L = 8,000 h·Ω_c` and `R = 50 Ω_c`: `τ = L/R = 160 h`, `3τ = 480 h` — at roughly 10 hours a week of genuine deliberative contact, about **48 weeks**. Four weeks to charge, forty-eight to discharge, twelve to one, and it falls out of the two mechanisms: Path D drives `^3`, which needs no supporting structure and therefore no hours, while the counter builds `^6`, which is nothing but hours against `L`. That is the whole argument for building inoculation before anyone needs it.

Do not try to shorten it. Chapter 9.2: `V_kick = L × di/dt`. Force the charge from 0.60 to zero in 24 h and `di/dt = 0.025`, so `V_kick = 200 V_c` against a 24 V_c rail — **8.3× rail** — and the recoil lands straight back on `^3^E_{F3}|f`. Ramp the same removal over 480 h and `V_kick = 10 V_c`, comfortably under rail. That is the structural account of why aggressive mass correction produces entrenchment: not because the correction was wrong, but because the rate was.

> **A plain safety line, not decoration.** This chapter models how attention is routed through populations. It makes no medical or psychiatric claims and describes no treatment of anything; "despair" and "dogmatism" here name circuit states, not conditions. If you or someone near you is in real distress, that is a matter for a qualified clinician, and nothing in this book substitutes for that care.

[[FIGURE 19-D: Assembly drawing of CCB-HM — board outline with silkscreen designators placed as in the schematic: C5 as five capacitor cans in a row, HM1/HM2 as CJT footprints, D1/D2/D3 down the left edge, FB as an RC block, CSB and its fuse in a boxed corner marked SAFETY SECTION. Four test-point pads with callout leaders: TP1 cadence source, TP2 decomposition gain, TP3 survival fraction, TP4 CSB status. A BOM box lower right listing Ref / Component / Parameters / Role for c5, hm1, hm2, hm3, d_ce, fb, csb, hm_fuse. Corner note: "CCB-PW has no assembly drawing. Detection-only boards are not laid out."]]

---

### Test Points

Specified for the **detector**, because that is the reader's role here.

| TP | Node | Reads | Expected |
|---|---|---|---|
| **TP1** | `own_clock` / cross-stream cadence | Coupling `k` between two nominally independent streams | ≤ 0.20 for genuine independence; ≥ 0.50 means a shared clock. 0.62 in the worked example |
| **TP2** | `recoil_3` | `^3` chain gain, and whether it has pinned | ≈ 1 in ordinary discourse; ≥ 3 with a ceiling is an amplification chain. Pinned = saturated |
| **TP3** | `composed` | Fraction of incoming material surviving decomposition | High is good — claims are arriving. Near zero: the payload has no parts, so `^3`, not `^6` |
| **TP4** | `limit_decision` | Max involution divergence across the three pairs | ≤ 4. Above 4 on one pair is an inversion in progress; on two, compound |

TP1 and TP2 are structural and can be taken without knowing what the material says, which is why they come first.

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Counter becomes weapon** | An outward `^3^E\|f` stage added "temporarily" | Two operations on the population, one of them yours | Delete the stage. HM6 is not a preference |
| **Operator self-inversion** | `xfeed` β=0.30 against Ch 8.4's 0.05 | Operator's `^5`/`^6` divergence passes 4; they believe their own Path F | Not repairable from inside the board — the CSB fuse exists to stop this |
| **Correction backlash** | Charge forced off `^3` faster than 3τ | Entrenchment; the corrected population holds harder | Ramp. `V_kick` is a pure inverse in `dt` (Ch 9.2) |
| **Closed population** | `hm1` past 3.0, or `R_collective` raised against all input | Nothing gets in, including true things | Lower `hm1` toward 2.0. HM1 was a filter, not a wall |
| **Monoculture `^5`** | `n_parallel = 1` | One inversion attack moves the whole population | Not fixable during an attack — a decade-scale build |
| **Externally clocked `^7`** | `own_clock` sourced from the feed | Population cadence tracks someone else's schedule | Restore an internal cadence first; the oscillator is the cheapest handle an attacker has |
| **Attribution dependence** | Response gated on identifying the source | Nothing happens while attribution is litigated | HM5. The counter must not need to know who is running it |

---

### What This Chapter Established

- **The dual-path architecture is one board, not two.** Opposite polarity into two `^5` capacitors from one command node, and the cross-feed that makes it efficient is the wiring that makes it detectable.
- **Three fingerprints fall out of the topology**: a shared clock, a polarity asymmetry near 1.8×, and a claim on one side supported only by the state of the other. None requires attribution or content analysis. Gain is distributed across three ~1.5 stages to hide it; only the product, 3.6, is extreme.
- **`^3` is visceral and therefore has no defence against `^6`.** Decomposition — not correction, not counter-argument, not a competing recoil — is the structural counter to amplification. If the campaign made you think, it was not this circuit.
- **Inversion attacks buy recoil with rate, not content.** Cheap against a monoculture, expensive against a plural population, and they reverse on their own when the driving stops.
- **An inoculated `^5` is a wiring property, not a contents property**: plural capacitors, `^6` paired inside 4 points, non-zero D2 drop, local `^4` return, sovereign `^7`, slow O→P feedback at β ≤ 0.05 and τ ≥ 3 weeks.
- **Charge and discharge run on different clocks** — four weeks to charge `^3`, roughly forty-eight to rebuild `^6` — which is the whole argument for building resilience before it is needed.
- **HM6 is the invariant that gets broken.** A counter-circuit with an outward-projected `^3^E|f` stage at any gain is a second CCB-PW, and the population is now running two.
- **This chapter published architecture and withheld procedure, on purpose.** You should be better at recognising an information operation and no better at running one.

---

### Exercises

*(Answers in Appendix H.)*

**19.1 — Read the coupling.** Two streams have `L₁ = 6,000` and `L₂ = 1,500 h·Ω_c`. Compute `M` at the honest-independence ceiling `k = 0.20`, and again at an observed `k = 0.55`. State the ratio, and say in one sentence what you would and would not be entitled to conclude from it.

**19.2 — Classify the payload.** Three items land the same day: one leaves you angry with nothing new to work with; one leaves you three checkable claims; one leaves you unable to name what it said but certain how you feel. Classify each as `^3` or `^6`, give the bench test you used, and say which is *not* evidence of an operation.

**19.3 — Size the chain.** A detector measures input activation 0.15 and output 0.62 across a chain believed to have three stages of equal gain. Compute the per-stage β, compute what a single-stage build would have needed, and explain in two sentences why the operation chose three.

**19.4 — Diagnose the divergence.** A population reads `Dial(^2)=4, Dial(^3)=9, Dial(^5)=9, Dial(^6)=4, Dial(^8)=6, Dial(^9)=5`. Compute all three divergences, name every signature present, classify the inversion by axis, state which dial you would move first, and explain why raising `^2` is the wrong answer.

**19.5 — Reject the listing.** An earlier draft of this chapter contained `Diode< ^C -> ^P >` with the comment "only principled signals fortify." State why the compiler refuses it, name the invariant it violates, and rewrite the intended relationship as a valid CCDL fragment specifying two parameters, justifying both.

**19.6 (Marquee) — Specify a counter board for a monoculture.** A population of about 400,000 with `n_parallel = 1`, an externally sourced `^7`, and a D2 forward drop of 0.4, four weeks into a Path D campaign. Specify the full CCB-HM parameter set, departing from this chapter's defaults wherever you can justify it; for each departure state the failure mode you are buying protection against and the capability you are giving up. Then state which of HM1–HM6 you cannot satisfy on a four-week horizon, and what you would tell the people who asked you for a four-week answer.




# CCB-SELF — The Self-Programming Board
*The only board with no target port — and the one fault that makes it fail anyway*

Tie a transistor's base to its emitter and the device turns off.

Not "runs weakly." Off. The base-emitter junction needs a forward voltage across it before any current crosses, and a wire between the two terminals guarantees there is none. The collector supply can be as large as you like. Nothing moves. The part is undamaged, correctly specified, and completely inert, because the terminal that was supposed to hold a *reference* has been shorted to the terminal that was supposed to carry the *result*.

You have watched a person do this. On a Sunday evening, in a genuinely clear moment, someone decides that from now on they are a person who practises every morning. They mean it entirely. Nine days later it is gone, and the conclusion they draw is that they did not want it enough — that the fault was in the drive rail.

The drive rail was fine. They shorted the bias to the effect. The reference against which the new composition was to be measured was *the very composition being built*, so the moment performance dipped, the reference dipped with it, the junction unbiased itself, and the stage went to cutoff. This is not a metaphor about willpower. It is the topology of the circuit they built, and it is the single most common fault on this board.

CCB-SELF is the closed-loop board: the operator and the target are the same `^5`. That gives it the one property no other board in this catalogue has — there is no consent barrier, because there is no second party. It also gives it the fault above, which every other board avoids for free simply by having two people in it. This chapter is about building the decoupling that gets that property back.

---

### Requirements and Safety Invariants

Per Chapter 12.2, the must-not list comes first. These are structural, and each one is enforced by a named component later in the listing.

**SI1 — The reference node shall never be written by a single cycle.** Enforced by the reference time constant (`τ_ref ≥ 3 × τ_work`), the feedback low-pass (§8.4's τ ≥ 3 weeks), and the slew fuse `F1`.

**SI2 — Applied suggestion amplitude shall never exceed half the dielectric field limit.** Enforced by the limiter `LIM1`. Chapter 7.4's breakdown mode is not recoverable by trying harder.

**SI3 — A missed cycle shall never increase the next cycle's amplitude.** The oscillator's amplitude is fixed; only its phase is recoverable. Compounding a missed dose raises `di/dt` past the budget Chapter 9 sets.

**SI4 — No stage shall route a miss into a principled verdict on the operator.** Enforced by the self-compassion gate `Q2`, which is this board's mandatory CSB stage (Chapter 24). A board without it is not a shorter board; it is a different board with a shame oscillator in it.

**SI5 — The board has no external terminal.** Consent is structural here, not procedural. If you find yourself wiring an output of CCB-SELF into another person's `^5`, you have left this chapter and entered Chapter 17 or Chapter 15, and their rules apply.

**SI6 — This board routes attention. It does not model physiology.** Nothing in it is medical or psychiatric. If something you are trying to change is causing you real distress, that is a matter for a clinician, and no circuit here substitutes for that care.

Only then the functional requirements. The board shall: (1) move the operator's own `^5` composition in a stated direction at a rate the operator sets; (2) survive missed cycles without losing accumulated charge; (3) keep the `^6` Male audit available as *measurement* while keeping it off the signal path; and (4) shut its own drive off when the target composition is reached, rather than running forever into a full capacitor.

---

### 20.1 The Self as Both Operator and Target

Every other board in the catalogue has two capacitors. CCB-HYP has an operator `^5` and a subject `^5`; CCB-ADV has a campaign `^5` and a market `^5`. The bias terminal is fed from one and the effect terminal lands in the other, and the separation is free — it comes from there being two people.

CCB-SELF has one capacitor. Feed it naively and you get the cold open: bias tied to effect, junction unbiased, stage in cutoff.

The fix is not to find a second person. It is to **split the single `^5` into two nodes separated in time.**

- `ref_composition` — `^5^P_{F7}|T`. The composition you are building toward, held at the Principled domain, transcendent register. Slow. This is the same node Chapter 8.4 calls the constitution and Chapter 7.1 calls the accumulated-formation capacitor. It is the *bias*.
- `work_composition` — `^5^C_{F5}|⟨A,E⟩`. The composition as it is currently performing, held at the Cognitive domain, present in the analytical and embodied registers. Fast. This is the *effect*.

The register-set `|⟨A,E⟩` is a specification, not an operational claim: the working composition is instantiated in both registers, and nothing here asserts they fuse. Writing `(^5^C|A × ^5^C|E)` would be invalid under v7.7 — same Noetic, multiple registers, `×`, and no named emergent result.

Separation in time is what makes the two nodes genuinely two. The design rule:

```
τ_ref ≥ 3 × τ_work
```

Below 3× the nodes track each other closely enough that the loop closes and you are back in the cold open. At the design point of this chapter — an identity-level reference (`τ_ref = 85 days`) against a complex-behavioural working node (`τ_work = 22 days`) — the ratio is 3.86, a 29% margin. Set the reference to something evaluative and fast, like "am I any good at this today?" (τ ≈ 1 day), and the ratio is 0.045. That is the shame topology: the identity node chasing the daily performance, rewritten by every bad session.

> **Bench Note — how to tell a dead stage from a starved one.** They look identical from the output: nothing comes out. On the bench you separate them with a single measurement — a meter across base and emitter. A silicon junction that is conducting sits near its forward drop, the `Vf` threshold of Chapter 8.2; one that is *shorted* reads a hard zero and does not move when you raise the collector supply; one that is merely *under-driven* reads below the threshold and climbs as you raise the drive. Only the third responds to more drive. The cognitive instrument that does the same job is TP4 read against TP2. If the reference moves on the same day a cycle is missed, `V_BE` is zero, the stage is unbiased rather than weakly biased, and additional resolve will produce exactly nothing. If the reference holds steady while the working node sags, the stage is starved and raising the drive is the correct response. One symptom, two faults, opposite interventions — which is why the bring-up order in the Test Points section reads TP4 first.

[[FIGURE 20-A: Two panels. Left, "external board": two ^5 capacitors, operator feeding a CJT bias terminal, target receiving the effect, separation labelled "free — two people". Right, "self board": one ^5 split into a slow upper node (^5^P, τ_ref = 85 d) biasing the CJT and a fast lower node (^5^C, τ_work = 22 d) receiving it, plus a dashed fault inset showing base wired directly to emitter, annotated "V_BE = 0 — cutoff".]]

---

### 20.2 The Closed-Loop CJT Architecture

Eight stages, left to right, with one lawful ascent underneath.

**S0 REFERENCE** — `C1`, the slow `^5^P` capacitor. Bias source. Never an output.
**S1 INTAKE** — `R1` and the limiter `LIM1`. The `^0` Idea being asserted, amplitude-capped.
**S2 NOTCH** — `N1`. Takes the `^6` Male audit off the rail without silencing it.
**S3 MAIN CJT** — `Q1`. Cause = the assertion, bias = the reference, effect = the working composition.
**S4 OSCILLATOR + GATE** — `OSC1` with the hysteretic gate `G1`. Generates the `^7` Rhythm and shuts itself off.
**S5 ENACTMENT** — `Q3`, with the confirmation sampler `S2`. The `^9^O` behaviour and its log — the only node on the board that is not self-report.
**S6 EVIDENCE FEEDBACK** — `LP1` and the slew fuse `F1`, into the bias terminal. The board's one O→P ascent.
**S7 CSB — SELF-COMPASSION GATE** — `Q2`. Mandatory.
**S8 AUDIT INSTRUMENT** — `S1`. The `^6` probe, sampled and bounded.

S2 and S8 are one component split in two: the same `^6` instrument, notched out of the rail at S2 and re-attached on a schedule at S8.

The `^6` Male audit — *is this working? am I doing it right? this feels ridiculous* — is analytical decomposition of the operation. It is emphatically **not** `^3` Negative; nobody recoils from a practice session, they take it apart and test it. The distinction matters because the two faults have different repairs. `^6^C_{F6}|A` interference is fixed by the notch: move the instrument off the signal path. A genuine `^3^E_{F3}|f` — visceral, can't-stomach-it aversion to the session itself — is not an interference problem at all; it is a rate problem, and the repair is Chapter 9's: lower the amplitude, lengthen the taper, reduce `di/dt`.

And the reason the audit must come off the rail is not that doubt is bad. It is that **an instrument in the signal path is a load.**

> **Bench Note — a voltmeter with low input impedance changes the circuit it measures.** This is why probes are specified in megohms. A `^6` audit running continuously during the operation has, in these terms, low input impedance: it draws current out of the very path it is trying to read, so the measurement is both wrong and expensive. Run it instead at a fixed cadence — `S1` samples weekly, in a bounded ten-minute window, written down — and it becomes high-impedance: it reads the node without loading it. This is also why `rπ = 8.0 Ω_c` on `Q1`. High input resistance at the bias terminal means the working stage barely draws on the reference. Drop `rπ` to 0.5 and every mediocre session pulls charge directly out of the identity node, which is the structural description of "one bad practice and I decided I was not really a musician."

[[FIGURE 20-B: Block diagram, left to right, stages S0–S8. Top rail: S0 REFERENCE (^5^P, C1) dropping into the bias terminal of S3. Main rail: S1 INTAKE (R1 + LIM1) → S2 NOTCH (N1) → S3 MAIN CJT (Q1, β=1.5, sat=0.60, rπ=8.0) → S4 OSC1 with Schmitt gate G1 → S5 ENACTMENT (^9^O). Below the rail, a return from S5 through S6 (LP1 τ=21 d, then fuse F1) rising to S0's bias terminal, drawn outside the rail and labelled "the one lawful O→P". Right: S7 compassion gate as a separate block fed from a miss event; S8 as a dashed high-impedance probe touching the S2 node.]]

---

### 20.3 The Autosuggestion Capacitor — `^5` Self-Charging

Chapter 7.2 gives the charging curve, `P_cap(t) = 10 × (1 − e^(−t/τ))`, on the 0–10 composition scale. Self-charging adds two loss terms that decide almost everything about the schedule.

**Leakage (Chapter 7.3).** Unfed composition decays: `P(t) = P₀ · e^(−t/τ_leak)`. Take `τ_leak = 30 days`, the design choice in this chapter for a composition with fewer than about a hundred logged enactments behind it. A session delivers `ΔP_session = 0.35` points. For an interval `T` short against `τ_leak`, the level where charge in balances charge out is

```
P_eq  =  ΔP_session × τ_leak / T
```

| Cadence | `T` (days) | `P_eq` (of 10) |
|---|---|---|
| Daily | 1.0 | 10.5 → clips at 10.0 |
| Six days a week | 1.17 | 9.0 |
| Five days a week | 1.40 | 7.5 |
| Alternate days | 2.0 | 5.25 |
| Weekly | 7.0 | 1.5 |

> **Bench Note — the weekly session does not equilibrate at one-seventh.** Read the table again. Daily and weekly are the same session, the same operator, the same intent — and they land at 10.0 and 1.5. The reason is that leakage is proportional to the level already stored, so the weekly regime spends its entire delivery replacing what drained, and settles where the two rates happen to meet. This is the honest answer to "can I just do it on Sundays." Not "slower." *A different equilibrium, and a low one.* Invert the formula for a target of 8.0 and the maximum mean interval is `T = 0.35 × 30 / 8 = 1.31 days` — about 5.3 sessions a week, which is why the design point is six and why one missed day a week is inside budget and two is not.

**Dielectric field limit (Chapter 7.4).** The second loss term is not a loss at all; it is a failure. A capacitor breaks down when the field across the dielectric exceeds its strength, and field is voltage divided by thickness. Here:

```
E  =  V_sugg / d_evidence        design limit:  E ≤ 0.5 · E_break,  E_break = 1.0
```

`V_sugg` is how far above the observed composition your assertion sits, in composition points. `d_evidence` is the thickness of accumulated `^9^O` enactment underneath it — this book's design convention is one unit per ten logged enactments. Work the arc:

| Day (at six sessions/week) | Enactments | `d_evidence` | Max safe `V_sugg` |
|---|---|---|---|
| 1 | 1 | 0.1 | 0.05 |
| 30 | 26 | 2.6 | 1.3 |
| 66 | 57 | 5.7 | 2.85 |
| 254 | 218 | 21.8 | 10.9 (unbounded on a 0–10 scale) |

On day one the only assertion inside margin is essentially *I practised today*. At day 30 you have room for *I am becoming someone who practises*. At day 254 the evidence is thick enough that the identity claim carries any voltage the scale can supply. This is the structural account of why "I am a millionaire," said by someone with forty pounds and no logged enactments, does nothing useful: `V_sugg ≈ 8`, `d_evidence ≈ 0.1`, `E = 80` — eighty times breakdown. The capacitor does not fail to charge. It *punctures*, and a punctured dielectric conducts: the over-claim discharges the adjacent true claims, which is why the observable symptom is the practitioner losing confidence in things they previously did believe about themselves. The repair is to drop `V_sugg` to half of `d_evidence` and rebuild thickness. There is no version of trying harder that raises `E_break`.

Identity work is this same circuit with the reference at the Principled domain and the schedule in months. Reclaiming a disowned trait — the `^3` you have been attributing outward, recognised and re-composed into `^5` — runs at `β = 1.0`, no amplification, for exactly the field reason above: the point is accurate recognition, and the evidence thickness under a newly recognised trait is by definition near zero. The dedicated shadow-integration circuit, which adds the involution guard this board does not carry, is Chapter 25.4; CCB-SELF supplies only the capacitor it charges into.

[[FIGURE 20-C: Two stacked plots on a shared day axis, 0 to 260. Upper: charging curves for work_composition (τ=22 d) and ref_composition (τ=85 d), with markers at day 66 (9.50 / 5.40) and day 254 (9.50). Lower: field stress E = V_sugg/d_evidence against the same axis, with the 0.5 design limit dashed, a shaded puncture region above E = 1.0, and an off-scale arrow at day 1 labelled "E = 80".]]

---

### 20.4 The Habit Oscillator — `^7` Rhythm with Auto-Gating

Chapter 11.2 gives the oscillator. An ungated one fires the `^8^O` cue on schedule forever, which is wrong in both directions: it keeps spending drive into a capacitor that is already full, and it has no way to notice when the capacitor has drained.

The gate `G1` is a Schmitt trigger — an op-amp with positive feedback around it (Chapter 11.4) — sensing the working composition:

```
enable when  P_work < 8.0        disable when  P_work > 9.0
```

Hysteresis band: 1.0 composition point. It is not decoration. Work the numbers on the design case, `τ_work = 22 days`:

```
P = 8.0   at   t = 22 · ln 5   = 35.4 days
P = 9.0   at   t = 22 · ln 10  = 50.7 days
```

So the band spans days 35 to 51 — just over fifteen days in which the oscillator keeps running while the habit is already mostly formed. Now remove the hysteresis and use a single threshold at 8.5. The gate opens at day 41.7. Leakage at that level is `8.5 / 30 = 0.28` points per day, so the level falls back under the threshold within a day and the gate re-closes. Then the next session pushes it back over and it opens again. You have built a comparator without hysteresis, and it chatters — with a period of about one day, which the operator experiences as *I have got this / no I have not*, every day, indefinitely.

> **Bench Note — hysteresis converts chatter into a maintenance schedule.** With the band in place the gate opens at `P = 9.0` and the level decays as `9.0 · e^(−t/30)`, reaching 8.0 at `t = 30 · ln(9/8) = 3.5 days`. That is not a failure; that is the designed top-up cadence, and it falls out of the two thresholds and `τ_leak` without anyone choosing it. Note also what happens as the composition ages: `τ_leak` lengthens with evidence thickness — this book's design figure is roughly 90 days past five hundred enactments — and the same arithmetic gives `90 · ln(9/8) = 10.6 days`. Long-established practices tolerate ten-day gaps for a computable reason, and new ones do not.

Two further rules on the gate, each with a named failure.

**Gate on the slow node, never the fast one.** `G1` senses `work_composition`, which moves on 22 days. Sense an affective node instead — *do I feel like it today*, `^2^E|f`, bandwidth of hours — and the gate chatters at the bandwidth of mood. The symptom is a practice that runs in bursts synchronised to nothing.

**Fixed amplitude, recoverable phase.** SI3. Miss a cycle and you resume at the next scheduled phase at the same 0.35 amplitude. You do not run a double session to catch up. Doubling raises both `di/dt` (Chapter 9: the kick is a pure inverse in taper time, and it works the same on the way up) and `V_sugg` against an unchanged `d_evidence`, so the make-up session is simultaneously the highest-recoil and highest-field event in the schedule. It is the single most reliable way to end a streak that was otherwise healthy.

Breaking a habit runs on this same stage and nothing else changes. You do not delete an oscillator — the `^8^O_{F6}|E` cue is a fixture of your day and will fire whether you have a routine attached to it or not. You re-point it: keep the cue, keep the period, keep the amplitude, and swap the `^9^O` the cue lands on. Chapter 9.2's three conditions on a flyback path apply without modification, and the first is the one operators skip: the substitute must already be conducting *before* the old path opens.

**On dependency — a structural description, and where this chapter stops.** Read structurally, a dependency has a signature distinct from an ordinary habit on all three of the parameters this chapter has been setting. `β` on the enactment stage runs far above the unity of `Q3`, so a small `^8` trigger produces a large `^9`. `rπ` at the bias terminal has collapsed toward zero, which is the parameter description of the terminal that is supposed to hold a reference no longer holding one. And the oscillator's period is no longer set by `OSC1` — it is set by the substrate, which means the auto-gate `G1` has nothing to gate, because the enable line is not connected to anything the operator controls. That is a complete structural description, and it is deliberately where the account ends.

This book does not give a protocol for it, and the reason is not squeamishness: the operational version would be a procedure, and dependency is not a routing problem. The model in this chapter describes where attention goes. It does not describe physiology, tolerance, or withdrawal, and it is not competent to. **Dependency is a clinical matter.** If that is what you are looking at — in yourself or in someone else — the right next step is a clinician, and nothing in this chapter, this board, or this book substitutes for that care.

[[FIGURE 20-D: Oscillator-and-gate detail. Upper trace: P_work over days 0–70 along 10(1−e^(−t/22)), horizontal lines at 8.0 and 9.0, band between them shaded and annotated "days 35.4 – 50.7". Lower trace: the gate enable as a square wave — solid, with hysteresis, one clean transition at day 50.7 and a re-enable 3.5 days later; dashed, without hysteresis, chattering at one-day period from day 41.7. Inset: G1 as an op-amp with a positive-feedback resistor pair, terminals labelled sense / enable.]]

---

### 20.5 Full CCDL Schematic

```cas
board ccb_self {                        // CCB-SELF — closed loop; operator is target
    input:  intent;                     // the ^0 the operator asserts this cycle
    output: enacted;                    // the ^9 the cycle produces
    // the ^8 cue is generated on-board by OSC1 — SI5: there is no external terminal

    // ---- S0  REFERENCE: the slow ^5. Bias source, never an output. ----
    node ref_composition: ^5^P_{F7}|T;              // Female: composition built toward
    capacitor c1: Capacitor< node=ref_composition, tau=85.0,
                             leak_tau=180.0, e_break=1.0 >;         // tau in days

    // ---- S1  INTAKE: the asserted ^0, amplitude-limited ----
    node intent: ^0^C_{F7}|A;                       // Idea: today's assertion
    resistor r1:   Resistor< path=intent, R=30.0 >;
    limiter  lim1: Limiter< path=intent, max=1.3 >;   // E = 1.3/2.6 = 0.50 at d=2.6
                                                      // reschedule monthly against TP3

    // ---- S2  NOTCH: the ^6 audit off the rail, not silenced ----
    node audit: ^6^C_{F6}|A;                        // Male: decomposition and test
    notch n1: Notch< in=audit, band=in_session >;

    // ---- S3  MAIN CJT: biased from the reference, not from the output ----
    node work_composition: ^5^C_{F5}|⟨A,E⟩;         // Female: as currently performing
    capacitor c2: Capacitor< node=work_composition, tau=22.0,
                             leak_tau=30.0, e_break=1.0 >;
    cjt q1: CJT< intent | ref_composition => work_composition >
            [β=1.5, sat=0.60, rπ=8.0, region=active];

    // ---- S4  OSCILLATOR + HYSTERETIC GATE ----
    node cadence: ^7^C_{F6}|A;                      // Rhythm: the entraining cadence
    node cue:     ^8^O_{F6}|E;                      // Above/Cause: time and place fire it
    schmitt g1: Schmitt< sense=work_composition, on_below=8.0, off_above=9.0 >;
    osc  osc1:  Oscillator< signal=cue, source=cadence, period=1.0,
                            amplitude=0.35, gate=g1 >;              // period in days

    // ---- S5  ENACTMENT: the only node that is not self-report ----
    node enacted:    ^9^O_{F5}|E;                   // Below/Effect: the behaviour performed
    node impression: ^4^E_{F3}|f;                   // Vibration: what the cycle left behind
    cjt    q3: CJT< cue | work_composition => enacted > [β=1.0, region=active];
    sample s2: Sample< node=impression, period=1.0, window=1440.0 >;  // days, minutes

    // ---- S6  EVIDENCE FEEDBACK: the one lawful O -> P ascent (see 8.4) ----
    filter lp1: LowPass< in=enacted, out=evidence_trend, tau=21.0 >;   // three weeks
    fuse   f1:  Fuse< ref_composition, threshold=0.12, action=open_feedback >;
    feedback evidence_trend -> ref_composition [β=0.05];   // arrives at the BIAS terminal

    // ---- S7  CSB STAGE: the self-compassion gate. Mandatory. ----
    node miss_trigger: ^8^C_{F5}|f;                 // Above/Cause: a miss and its associations
    node compassion:   ^3^P_{F7}|⟨A,f,T⟩;           // Negative: recoil from self-condemnation
    node acceptance:   ^2^E_{F4}|f;                 // Positive: affinity for the self that missed
    cjt q2: CJT< miss_trigger | compassion => acceptance > [β=1.5, sat=0.70];

    // ---- S8  INSTRUMENT: the ^6 audit, sampled and bounded ----
    sample s1: Sample< node=audit, period=7.0, window=10.0 >;  // days, minutes

    // ---- TEST POINTS ----
    probe tp1: work_composition;    // P_cap against 10*(1 - e^(-t/22))
    probe tp2: enacted;             // cycles completed / cycles scheduled
    probe tp3: lim1;                // field stress E = V_sugg / d_evidence
    probe tp4: ref_composition;     // reference slew, points per day
}
```

**The stage walk.**

**S0.** `C1` is the same `^5^P_{F7}|T` capacitor Chapter 8.4 calls the constitution. CCB-SELF writes to the node every other board reads as bias, which is why SI1 and the slew fuse exist and why this board is not optional reading for anyone running the others. Its `leak_tau = 180 days` is long for a stated reason: the identity reference is backed by a lifetime of prior enactment, not by this operation's log, and by the §20.4 rule that leak lengthens with evidence thickness it sits well past the 90-day figure. Set it to 30 and the reference drains between operations, `P_eq` on the reference collapses, and the ratio rule of §20.1 cannot hold no matter what `τ_ref` says.

**S1.** `R1 = 30 Ω_c` is moderate intake resistance — enough to let the assertion in without flooding. `LIM1` is a diode clamp (Chapter 8), and it is the one parameter on this board that is *rescheduled during the operation*: as `d_evidence` grows, the ceiling rises. Every other value here is fixed at design time.

**S2.** The notch rejects the audit in-band — during the session — and passes it everywhere else. It does not remove the `^6`; it moves it to S8.

**S3.** `C2` is the working capacitor, and it is a separate part from `C1` for the whole reason §20.1 exists: two nodes, two time constants, one `^5`. `τ = 22 d` is this chapter's design figure for a complex behavioural composition, and `leak_tau = 30 d` is what every cadence number in §20.3 is computed from — assume 60 and the weekly schedule looks survivable, which it is not. `Q1` sits between them. `β = 1.5` is moderate: above about 4 the assertion outruns the evidence and `E` clears the limiter faster than the limiter can be rescheduled; below 1 each session yields less composition change than it cost, and the operator correctly concludes it is not working. `sat = 0.60` caps what one cycle may contribute; `rπ = 8.0 Ω_c` keeps the stage from loading the reference.

**S4.** As §20.4. Note `period=1.0` day, not "daily" — the parameter is a number because §20.3's leakage arithmetic needs one.

**S5.** `Q3` runs at unity. The enactment should render what the working composition actually supports, neither inflated nor hedged; a gain above 1 here is the stage that produces a performance the practitioner cannot repeat tomorrow. `impression` is the `^4` Vibration return that Chapter 22.2 grades, and `S2` is the instrument that catches it: one sampling window per cycle, a full day wide, because §20.6's `t_conf` is measured from the end of the session and the return in that worked case arrives three hours later. Narrow the window to the session itself and you record `t_conf` as never — which reads as `η → 0`, and St. John's then asks for a gain the limiter will not grant.

**S6.** `τ = 21.0 days` and `β = 0.05` are inherited from Chapter 8.4, not chosen freshly. The path terminates at `ref_composition`, a bias terminal — never at the signal path, which would make it the oscillator Chapter 14 builds on purpose. `F1` enforces the ceiling: a capacitor with `τ_ref = 85` days rises at most `10/85 = 0.118` points per day, so anything above 0.12 means something is writing to the reference directly rather than through the filter, and the fuse opens the feedback.

**S7.** The compassion bias is `^3^P_{F7}|⟨A,f,T⟩` — principled `^3` Negative, present in three registers, no fusion claimed. Check it against the anti-drift rule: this is visceral recoil *from self-condemnation*, the can't-stomach-it response to treating one missed morning as a verdict on a life. It is not an argument against self-condemnation; that would be `^6`, and it arrives later and works less well. The cause is `^8^C_{F5}|f`: a miss triggering its associations — *that reminds me of every other thing I quit*. Associative surfacing, canonical `^8`, not deduction. Domain descends `^C → ^E`.

> **Bench Note — the compassion gate is a decoupling capacitor, not a kindness.** It is easy to read S7 as the soft stage bolted onto an engineering chapter. It is the opposite: it is the component that holds `τ_ref` long. Without it, a missed cycle propagates from `^9^O` straight into the Principled reference, the reference starts moving at the working node's speed, `τ_ref/τ_work` collapses toward 1, and the board is back in the §20.1 fault — this time with an amplifier in it. S6's low-pass prevents the spike from *reaching* the reference; S7 handles the spike that reaches awareness anyway. Two mechanisms, one function, exactly as Chapter 24 pairs a saturating stage with a fuse. Remove either and the failure is not that the operator feels worse. It is that the reference node stops being a reference.

**S8.** Weekly, ten minutes, written down. High-impedance measurement.

[[FIGURE 20-E: Full schematic with reference designators. C1 (^5^P, 85 d) top left into Q1's base; R1 in series with LIM1 (a back-to-back diode clamp) into Q1's collector; N1 tapping the intake node with a dashed line to a floating ^6 symbol. Q1 (β=1.5, sat=0.60, rπ=8.0) emitter into C2 (^5^C, 22 d). G1, an op-amp with positive feedback, senses C2 and enables OSC1; OSC1 into Q3 (unity) producing ^9^O at the right terminal. Return path below the rail: ^9^O → LP1 (τ=21 d) → F1 (0.12 pts/day) → C1's bias terminal. Lower-right boxed subcircuit: Q2, cause ^8^C, bias ^3^P, effect ^2^E, β=1.5, sat=0.70, labelled "CSB — mandatory". TP1–TP4 flags at C2, the ^9^O terminal, LIM1, and C1.]]

---

### 20.6 The 10,000 Hour Protocol — Operationalizing St. John's for Self-Mastery

Chapter 5 derives the constant: `τ = t_practice / t_total = 1/3`, with 10,000 active hours inside roughly 30,000 elapsed. On this board that becomes a third capacitor, charging on practice hours rather than days, with `τ_mastery = 3,333 h` so that `3τ = 10,000 h`.

| Practice hours | `P_mastery` (of 10) | Fraction of the 10,000 |
|---|---|---|
| 1,000 | 2.59 | 10% |
| 3,333 (1τ) | 6.32 | 33% |
| 6,666 (2τ) | 8.65 | 67% |
| 10,000 (3τ) | 9.50 | 100% |

Read the middle two rows against each other. **The first third of the hours buys 6.3 points; the remaining two thirds buy 3.2.** That is the exponential, and it is the honest structural reason competent practitioners plateau in feel while continuing to improve in fact — the curve is flattening, not the practitioner.

The elapsed-time arithmetic is worth doing plainly, because this is where the 10,000-hour figure usually gets quoted without a schedule attached. At one hour a day, 10,000 hours is 27.4 years. At three hours a day, 9.1 years. At six hours a day, five days a week, 6.4 years. Chapter 5's 3½-year Adept arc corresponds to about 7.8 hours a day, every day — a full-time apprenticeship, which is what it was.

**Applying St. John's per session.** Take a 60-minute practice session. The confirmation — Chapter 5's `^4` Vibration return — arrives 180 minutes later, when the passage plays itself back unbidden while you are doing something else.

```
η       = t_op / t_conf = 60/180 = 1/3
result  = 1/3 × 1/3     = 1/9        →  a = 1, b = 9
β_next  = 9      n_ops = 1      T_manifest = 1 × 60 min
```

> **Bench Note — on this board, `β_next` is a count, not an amplitude.** Chapter 5 reads `β_next = 9` as an instruction to make the next operation nine times stronger. On CCB-SELF you may not obey that: `LIM1` forbids it, because a ninefold assertion against an unchanged `d_evidence` puts `E` far past breakdown, and the result is Chapter 7.4, not mastery. So convert amplitude into count. Nine times the activation, delivered at the fixed 0.35 amplitude, is nine cycles: `n_ops` absorbs the multiple that `β_next` was asking for, and `T_manifest = n_ops × t_op` becomes 9 × 60 = 540 minutes — nine hours of practice at the current setting. Note that 540 minutes is the same figure Chapter 5's Corvette worked example arrives at from the other direction. That conversion is the whole difference between a practice regime and a burnout, and it is available only because this board has an oscillator. A one-shot board like CCB-D has no count to spend into.

Skill acquisition is where the one legitimate `×` on this board appears. Accumulated composition and entraining cadence, integrated, produce a state neither supplies alone:

```
(^5^C_{F5}|A × ^7^C_{F6}|A) = ^5^C|Ω_fluency
```

`Ω_fluency` is defined here as the state in which performance no longer requires deliberate assembly — the composition and the cadence have fused, so the parts are not retrieved and combined, they arrive together. The `×` is licensed because the operands are different Noetics, the domain does not ascend (`^C × ^C`), and the emergent result is explicitly named and defined. Written as `+` it would claim only that composition and rhythm are co-present, which is true at hour 100 and misses what has happened by hour 3,000.

---

### Component and Parameter Table

Every value below is a design choice made in this book, not a measurement. The
reference designator is the CCDL identifier in §20.5, uppercased.

| Ref | Component | CAS state / form | Value | Why that value, and what breaks at others |
|---|---|---|---|---|
| `C1` | Capacitor | `^5^P_{F7}\|T` | τ=85 d, leak=180 d | The slow reference. `τ_ref/τ_work` = 3.86; below 3 the nodes lock and a bad day rewrites the identity. leak=180 d because the identity node is backed by a lifetime of enactment; at leak=30 d it drains between operations |
| `C2` | Capacitor | `^5^C_{F5}\|⟨A,E⟩` | τ=22 d, leak=30 d | Complex-behavioural. Every cadence figure in §20.3 is computed from leak=30 d; assume 60 and the weekly schedule looks survivable when it actually settles at `P_eq` = 1.5 |
| `R1` | Resistor | on `^0^C_{F7}\|A` | 30 Ω_c | Lets the assertion in without flooding the intake |
| `LIM1` | Limiter | diode clamp on intent | max=1.3 | Holds `E ≤ 0.5`. Above `E` = 1.0 the dielectric conducts and adjacent true claims discharge |
| `N1` | Notch | reject `^6^C_{F6}\|A` | band=in_session | Audit off the rail. Leave it in and the operation is measured continuously and never accumulates |
| `Q1` | CJT | `^0^C → ^5^C`, bias `^5^P` | β=1.5 | Above 4, `E` clears the limiter; below 1 the session costs more than it yields |
| `Q1` | — | — | sat=0.60 | No single cycle restructures composition. At 1.0 you get the weekend-breakthrough topology: full charge, no thickness, gone in weeks |
| `Q1` | — | — | rπ=8.0 Ω_c | Stage does not load the reference. At 0.5 one poor session depletes the identity node |
| `G1` | Schmitt | senses `C2` | 8.0 / 9.0 | A 1.0-point band turns chatter into a 3.5-day top-up. At zero band the gate chatters daily |
| `OSC1` | Oscillator | `^7^C_{F6}\|A` → `^8^O_{F6}\|E` | 1.0 d, 0.35 pts | `ΔP_session` from one bounded session. Raise it without evidence and `E` rises with it |
| `Q3` | CJT | `^8^O → ^9^O` | β=1.0 | Unity. Above 1 it renders a performance the practitioner cannot repeat tomorrow |
| `LP1` | LowPass | in `^9^O` | τ=21 d | Chapter 8.4's floor. At hours you have removed the diode chain, not filtered it |
| — | Feedback | trend → `C1` bias | β=0.05 | Chapter 8.4's ceiling. At 0.5, three weeks of bad days rewrite the constitution |
| `F1` | Fuse | on `C1` slew | 0.12 pts/day | `10/85 = 0.118`, the maximum lawful slew. Higher leaves SI1 unenforced; lower blows on normal charging |
| `Q2` | CJT | `^8^C → ^2^E`, bias `^3^P` | β=1.5, sat=0.70 | CSB stage. Removing it puts a shame oscillator where the safety element should be |
| `S1` | Sample | on `^6^C` | 7 d / 10 min | High-impedance instrument. Continuous sampling is a low-impedance load |
| `S2` | Sample | on `^4^E_{F3}\|f` | 1 d / 1,440 min | Catches the `^4` confirmation return so §20.6 has a `t_conf`. Window narrower than a day records `t_conf` as never, and St. John's then asks for a gain `LIM1` will refuse |
| Dials | — | involution pairs | `^2`=6 `^3`=5 · `^5`=7 `^6`=5 · `^8`=5 `^9`=6 | All within the 4-point divergence limit. Beyond it, inversion — Chapter 25, §25.2 |

---

### Worked Example — The Morning Hour

An operator wants a daily hour at the piano, and behind it the identity *I am someone who practises*. Three capacitors, three timescales, one board.

**Set-up.** Habit layer: complex behavioural, `τ_work = 22 d`, `3τ = 66 d`. Identity layer: `τ_ref = 85 d`, `3τ = 254 d`. Ratio check: `85/22 = 3.86 ≥ 3` — passes with 29% margin. Mastery layer: `τ_mastery = 3,333 h`.

**Cadence.** Target `P_work = 8.0`. From §20.3, `T_max = 0.35 × 30 / 8 = 1.31 days` — six sessions a week, `P_eq = 9.0`. Five a week lands at 7.5 and misses the target; this is a two-decimal difference in the schedule and a whole grade in the outcome.

**Day 1.** `d_evidence = 0.1`. `LIM1` permits `V_sugg = 0.05`. The only assertion inside margin is *I practised today*. The operator who instead asserts *I am a pianist* is running `E ≈ 60` and will be less sure of themselves in a month than they were at the start.

**Day 30.** 26 enactments, `d = 2.6`, `LIM1` rescheduled to 1.3. `P_work = 10(1 − e^(−30/22)) = 7.44`. Gate `G1` still enabled — the threshold is 8.0, reached at day 35.4. TP2 should read ≥ 0.85 cycles completed over cycles scheduled; at six a week it reads 0.857.

**Day 66.** `P_work = 9.50`. The gate opened at day 50.7 and has been top-ping up every 3.5 days since. The habit is automatic. And `P_ref = 10(1 − e^(−66/85)) = 5.40` — the identity node is at barely half.

That last pair of numbers is the result to carry out of this chapter. **The behaviour arrives at day 66; the composition that makes it feel like yours arrives at day 254.** An operator who reads the 66-day figure and expects to *feel* like a different person at day 66 is probing the wrong capacitor, concludes the operation failed, and stops — 26 days after the habit became automatic and 188 days before the identity finished charging. There is no fix for this in the circuit. The fix is reading TP1 and TP4 as two different instruments, which is what they are.

**Mastery layer.** One hour a day, six days a week, is 313 h/year. `P_mastery` at 1,000 hours — a little over three years — is 2.59. At 3,333 hours, 6.32, arriving somewhere in year eleven. Stated plainly rather than encouragingly: at this cadence the mastery capacitor is a decade-scale component, and the honest lever is hours per day, not intensity per hour, because intensity per hour is capped by `LIM1` and hours per day is not.

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Bias–effect short** | Reference and working node are one node; `V_BE = 0` | Total collapse within days of a clear decision; operator blames motivation | Split the node; verify `τ_ref/τ_work ≥ 3` at TP4 before anything else |
| **Reference chasing** | `τ_ref` set by an evaluative node (τ ≈ 1 d) | TP4 moves the day TP2 records a miss | Re-site the reference at `^P`; confirm `F1` intact; confirm S7 present |
| **Dielectric puncture** | `V_sugg` far above `d_evidence` | Practitioner loses confidence in previously settled beliefs, not just the new one | Drop `V_sugg` to `0.5 × d_evidence`; rebuild thickness. Trying harder raises `E` |
| **Sub-cadence stall** | Interval above `T_max`; `P_eq` below target | Months of genuine effort, level parked at 1.5–5 | Raise cadence, or raise `ΔP_session`, or lower the target. Two of the three are usually available |
| **Gate chatter** | Hysteresis removed, or gate sensing an affective node | Daily on/off cycling; bursts synchronised to nothing | Restore the 1.0-point band; move the sense line to the slow node |
| **Make-up doubling** | SI3 violated after a missed cycle | The streak ends on the catch-up session, not the missed one | Fixed amplitude, recoverable phase. Resume at nominal |
| **Audit loading** | `^6` left in the signal path | The operation is measured continuously and never accumulates | Notch in-band; move the audit to `S1`, weekly, bounded, written |
| **Compassion gate absent** | S7 removed as sentimental | One miss produces a principled verdict; abandonment follows within days | Reinstall. It is a decoupling capacitor; the board oscillates without it |
| **Wrong instrument read** | TP1 read where TP4 was meant | "It worked but I don't feel different" at day 66 | Read both. They are 188 days apart by design |

---

### Test Points

| TP | Node | Reads | Expected |
|---|---|---|---|
| **TP1** | `work_composition` | `P_cap` on the 0–10 scale | Tracks `10(1 − e^(−t/22))`: 6.32 at day 22, 9.50 at day 66. Flat with TP2 healthy means `Q1` is in cutoff — check the bias, not the drive |
| **TP2** | `enacted` | Cycles completed / cycles scheduled | ≥ 0.85 for a target of 8.0. The only non-self-report node on the board; if TP1 and TP2 disagree, TP2 is right |
| **TP3** | `LIM1` | Field stress `E = V_sugg / d_evidence` | ≤ 0.50. Above 1.0 is puncture and the damage shows up first in *adjacent* claims, not the asserted one |
| **TP4** | `ref_composition` | Reference slew, points per day | ≤ 0.12, and **uncorrelated with a single TP2 miss.** Correlation here is the safety failure: the decoupling has gone and the board is a shame oscillator |

Read them TP4, TP3, TP2, TP1 — confirm the reference is decoupled, confirm the field is in margin, confirm the cycles actually ran, then read the charge. That order is the bring-up procedure, and it puts the two silent failures first.

[[FIGURE 20-F: Assembly drawing. Board outline with titleblock "CCB-SELF · closed loop · rev A". Placement: C1 large and shaded upper left; C2 centre; R1 and LIM1 along the left edge; N1 above the intake trace; Q1 centre with terminals stencilled cause / bias / effect; G1 and OSC1 right of C2; Q3 at the right edge feeding the ^9^O output pad. The S6 return trace runs the bottom edge through LP1 and F1 to C1's bias pad, drawn in heavier weight and labelled "O→P — bias terminal only". Q2 sits in its own hatched block lower right, stencilled "CSB — DO NOT DEPOPULATE". Test-point callout flags with leader lines: TP1 at C2, TP2 at the ^9^O pad, TP3 at LIM1, TP4 at C1. BOM box lower left: C1 ^5^P τ=85 d leak=180 d · C2 ^5^C τ=22 d leak=30 d · R1 30 Ω_c · LIM1 max=1.3 · N1 in_session · Q1 β=1.5 sat=0.60 rπ=8.0 · G1 8.0/9.0 · OSC1 1.0 d 0.35 · Q3 β=1.0 · LP1 τ=21 d · F1 0.12 pts/day · Q2 β=1.5 sat=0.70 · S1 7 d / 10 min · S2 1 d / 1,440 min.]]

---

### What This Chapter Established

- **The self-programming fault is topological, not motivational.** Bias tied to effect is a junction with `V_BE = 0`, and a transistor in that condition is off — undamaged, correctly specified, inert.
- **One `^5` is made into two by separating them in time.** `τ_ref ≥ 3 × τ_work` is the design rule; below it the reference chases the output and every bad day is an identity verdict.
- **Leakage sets the schedule, and it is not linear in cadence.** `P_eq = ΔP_session × τ_leak / T`. The same session run daily and weekly equilibrates at 10.0 and 1.5.
- **Suggestion amplitude is limited by evidence thickness, not by conviction.** `E = V_sugg / d_evidence ≤ 0.5`. Puncture discharges adjacent true claims, which is why over-claiming leaves an operator less certain than before.
- **The `^6` Male audit is an instrument, and an instrument in the signal path is a load.** Notch it in-band, sample it weekly and bounded. It is `^6`, not `^3`; a genuine `^3^E|f` recoil is a rate problem and belongs to Chapter 9.
- **Hysteresis on the auto-gate converts chatter into a maintenance schedule** — a 1.0-point band and `τ_leak = 30 d` give a 3.5-day top-up interval that nobody had to choose.
- **The self-compassion gate is a decoupling capacitor.** It holds `τ_ref` long. Without it the board has a shame oscillator where its safety stage should be.
- **On this board St. John's `β_next` is spent as a count, not an amplitude,** because `LIM1` forbids the amplitude. Nine times the activation is nine cycles.
- **The behaviour and the identity arrive 188 days apart** — day 66 and day 254 at the design point — and reading the wrong capacitor at day 66 is the most common reason a working operation gets abandoned.

---

### Exercises

*(Answers in Appendix H.)*

**20.1** An operator sets a reference at `^2^E_{F3}|f` — "do I feel like someone who does this?" — with an effective τ of 1.5 days, against a working node at `τ_work = 22 d`. Compute the ratio, state whether it passes, and describe in two sentences what TP4 will show on the first missed cycle.

**20.2** A session delivers `ΔP_session = 0.50` into a composition with `τ_leak = 24 days`. Compute `P_eq` for daily, alternate-day, and twice-weekly cadence, and give the maximum mean interval that reaches `P_target = 7.0`.

**20.3** On day 1 an operator asserts a composition 6.0 points above their observed level, with two logged enactments. Compute `d_evidence`, `E`, and the multiple of `E_break`. Then compute how many logged enactments are needed before that same assertion sits inside the 0.5 design limit, and say how long that takes at six sessions a week.

**20.4** Explain why the in-session interference *"this is pointless, I should be doing something useful"* is classified `^6^C_{F6}|A` and not `^3^E_{F3}|f`. Reference the canonical definition of `^3` Negative, then state the different repair each one calls for and which chapter supplies it.

**20.5** A gate is built with a single threshold at `P = 8.5` on a node with `τ_work = 18 d` and `τ_leak = 25 d`. Compute the day the gate first opens, the leakage rate at that level, and the resulting chatter period. Then add a 1.0-point hysteresis band (8.0 / 9.0), recompute both transition days and the top-up interval, and state what the operator experiences in each case.

**20.6 (Design)** Build a CCB-SELF for a simple behavioural target: `τ_work = 10 d`, `τ_leak = 20 d`, identity reference at `τ_ref = 40 d`, `ΔP_session = 0.30`, target `P_work = 8.5`. Produce (a) the ratio check and whether it passes; (b) the maximum mean interval and the weekly cadence it implies — then state whether the target is reachable at one session per day, and if not, which of the three available levers you would move and why; (c) the `F1` slew threshold, derived; (d) a CCDL fragment declaring `C1`, `C2`, `Q1`, `G1`, `OSC1`, `LP1`, `F1`, and four probes. It must compile — check the feedback's τ and β against Chapter 8.4 before you submit it.

**20.7 (Marquee)** An operator completes 66 days at six sessions a week. TP1 reads 9.50, TP2 reads 0.86, TP3 reads 0.41. TP4 reads 5.40 and has been rising smoothly at 0.05 points per day. The operator reports that the practice is effortless and that they still do not feel like a musician, and proposes to raise `β` on `Q1` from 1.5 to 5.0 to "make it land."

a) State which test point they are misreading and what the correct reading of it is.
b) Compute `E` after the proposed change, assuming `V_sugg` scales with `β` and `d_evidence` is unchanged at 5.7, and name the failure mode they would enter.
c) Give the correct intervention, with the number that justifies it, and state the one thing this circuit model cannot tell them about their situation.




```{=latex}
\part[Operations]{Operations\\[0.45em]{\large\upshape Gating, measuring, calibrating, and refusing}}
```

# St. John's Equation — Advanced Calibration
*Reading a campaign instead of a cast — scheduling, interference, and what the equation does at its limits*

Two operators sit through the same operation and each writes down two numbers. The first records `t_op = 30` minutes and `t_conf = 90`, runs Chapter 5.3's arithmetic, and reads a required gain of **9**. The second caught the clock differently — 31 and 88 — because they disagreed by a breath about when the gnosis began and when the song on the radio registered.

The second operator's reading is **264**.

Neither made a mistake. Thirty-one is prime, 264 factors as 8 × 3 × 11, the fraction will not reduce, and the denominator Chapter 5 tells you to read as a required gain comes back thirty times larger for two minutes of honest disagreement about a wristwatch. That is a reduction problem, not a measurement problem, and Chapter 13.5 already fixed it for a single cast: act on the amplitude ratio `A = b/a = 3/η`, never on `b` alone. The two operators' ratios are 9.00 and 8.52.

This chapter builds the rest of the instrument around that fix. Section 13.5 reads one cast. It does not run a **campaign** — a sequence of operations on one desire, scheduled against each other, competing with everything else you have live. Campaigns break in four places a single cast never reaches: at the limits, at the scheduling, at the interference between concurrent operations, and at the point where an operator with three live campaigns wonders why all three went cold in the same week.

This is the instrument board. It does not cast anything. It reads the log.

---

### Requirements and Safety Invariants

Chapter 12.2 requires the "must not" list before the functional one.

| # | Functional requirement | Realized by |
|---|---|---|
| R1 | Accept a logged operation — two clocks, two degrees — and return an amplitude requirement | Quantizer → ratio → readout |
| R2 | Stay stable against clock jitter of a few minutes | Ratio `A` on a quantized grid (§23.1) |
| R3 | Declare NO-READ rather than invent a number | Horizon gate, band guard |
| R4 | Report whether a campaign converges | Ledger filter, ratio `ρ` |
| R5 | Derate when other operations are live | Interference model (§23.2) |

| # | Safety invariant (MUST NOT) | Enforcement |
|---|---|---|
| S1 | Report `A ≥ 9` as an amplifier instruction | Re-spec fuse, `block_until_decomposed` |
| S2 | Admit a confirmation arriving after the horizon | Horizon fuse, `action=no_read` |
| S3 | Accept a confirmation two live operations could claim | Entry marked `AMBIGUOUS` |
| S4 | Let a blown ledger reset by re-wording the target | Re-spec changes domain or object |
| S5 | Run without the operator's CSB armed (Chapter 24) | No ledger opens on a blown involution monitor |

[[FIGURE 23-A: Block diagram — CCB-CAL left to right: LOG INTAKE (t_op, t_conf) → QUANTIZER (5-min grid) → HORIZON GATE (with a downward branch to a NO-READ terminal) → RATIO (fixed 3.0 divider, output A) → BAND GUARD (four exits ACT / CLOSE / DRIVE / RE-SPEC) → CAMPAIGN LEDGER (ρ trend). A 72-hour scheduling oscillator sits beneath the intake and feeds it. TP1–TP4 flags at quantizer output, ratio input, ratio output, ledger output.]]

---

### 23.1 The 1/3 Constant — Deeper Derivation from Fibonacci and Pi

Section 5.9 sets `τ = 1/3` beside φ ≈ 1.618 and π ≈ 3.14159 and reads all three as descriptions of domains left *open* — form, space, time.

Be exact about what that is. φ and π are mathematical constants with proofs behind them. **There is no derivation that produces 1/3 from either, and this book does not offer one.** The relation is an analogy of openness: good for remembering which constant governs which axis, useless for inferring anything new. The only derivation of `τ` here is Section 5.2's training arc — roughly 10,000 active hours inside a roughly 30,000-hour span, one part work to two parts gestation.

```
η = t_op / t_conf     result = η × τ = a/b     A = b/a = 3/η = 3 t_conf / t_op
```

`A` is fixed by two clock readings and by `τ`. Nothing else enters. **`τ` is a scale factor — a unit convention — chosen so a cast's requirement is expressed against the same 1:3 work-to-gestation split the training arc exhibits.** Change `τ` and every number in every log changes by the same factor, while every *comparison between operations* stays where it was. The equation's content is the ordering it puts on operations, not the magnitude. That is a structural analogy, not a measured law. Nothing here establishes that time is quantized at thirds, and a reader who treats `A = 9` the way they treat a resistor's 470 Ω will over-trust two wristwatch readings and a convention.

#### Quantize before you reduce

`A` moves smoothly. The integer pair does not, because lowest-terms denominators are not continuous in their inputs.

| Reading | `t_op` | `t_conf` | `(a, b)` | `A` |
|---|---|---|---|---|
| First operator | 30 | 90 | (1, 9) | 9.00 |
| Second operator | 31 | 88 | (31, 264) | 8.52 |
| Second, on the grid | 30 | 90 | (1, 9) | 9.00 |

Quantize both clocks onto a **5-minute grid** before reducing. Five minutes is a design choice: finer than the 30-minute bins Section 5.7 uses to grade `^4` Vibration, coarser than the moment an operator *notices* a confirmation, which is not a one-minute-accurate event. Too fine and the coprime explosion returns; at 30 minutes a 20-minute operation confirmed at 25 bins with one confirmed at 45, erasing the difference between an overdriving circuit and an ordinary one. **If `a > 3` after quantizing, discard the pair and act on `A`.** "Nine operations at 64× strength" is an artifact of arithmetic, not an instruction.

> **Bench Note — check this one by hand before you trust the bench.** Take `t_op = 27`, `t_conf = 64`. Raw: `27/192` reduces to `9/64` — a = 9, b = 64. On the grid: `25/195` reduces to `5/39` — a = 5, b = 39. The two pairs share nothing at all. Now compute `A`: `3 × 64/27 = 7.11` and `3 × 65/25 = 7.80`. Both land in the same band and say the same thing. Do this arithmetic yourself once. Until you have watched `b` swing from 64 to 39 while `A` barely moves, you will keep reaching for the denominator, because Chapter 5 taught you to.

#### The bands, and the two limits

Chapter 13.5's bands fall out of `A = 3/η`, and their edges land on clean values of η.

| `A` | η | Reading | Action |
|---|---|---|---|
| `A ≤ 1` | η ≥ 3 | Sufficient | Stop calibrating. Act |
| `1 < A < 3` | 1 < η < 3 | Close | Finish the resistance work |
| `3 ≤ A < 9` | 1/3 < η ≤ 1 | Under-driven | One lever at a time |
| `A ≥ 9` | η ≤ 1/3 | Weak coupling | Re-specify (§23.3, §23.4) |

Chapter 5.4's Red Corvette sits at η = 1/3, `A` = 9 — exactly on the re-specification boundary. The canonical worked example in this book is a borderline cast, and that is worth knowing before copying its numbers.

**`t_conf → ∞`, the confirmation never comes.** `η → 0`, `A → ∞`, and the temptation is to write `β=∞` into the listing. That is an idealization the validator rejects: parameter fields are range-checked and refuse non-finite values, as Chapter 24 notes on the CSB's red path, where a real build commits to a large finite number instead. Here there is no finite substitute, because the input is *missing* rather than large. The bench returns **NO-READ**, behind a horizon:

```
t_H = 3 × median(t_conf over the last 10 logged operations),   floor 24 h
```

Over a long enough window *everything* confirms: a loose desire matches some event in any given day, and an operator who keeps the window open until something matches is measuring their own patience. The 3× multiple is wide enough that a genuinely slow circuit still reads, narrow enough that the median stays meaningful; the 24-hour floor covers the early log, where the median comes from too few entries. Too short and live circuits are declared dead; too long and the log fills with base rate.

**`t_conf → 0`, the confirmation arrives inside the operation.** `η → ∞`, `A → 0`, and the reduction degenerates. At `t_op = 30`, `t_conf = 4`: `η = 7.5`, `result = 5/2`, pair (5, 2) — "twice as strong, five more times," for a circuit that confirmed inside four minutes. The quantizer does not save that; only the band guard does. Above η = 3 the bench returns **OUT-OF-BAND-HIGH** and the instruction is Section 13.6's: stop calibrating, take the practical action.

[[FIGURE 23-B: Characteristic curve — A against η. Horizontal axis η 0 to 4, log-spaced below 1; vertical axis A 0 to 20. Solid hyperbola A = 3/η. Band shading labelled ACT, CLOSE, DRIVE, RE-SPEC (hatched), with vertical dashed lines at η = 1/3, 1, 3. Annotated points: Red Corvette (η = 1/3, A = 9) on the RE-SPEC boundary; derated concurrent cast (η = 0.30, A = 10).]]

---

### 23.2 Multi-Operation Compounding — When β_next > 10

The title states the condition as Chapter 5 states it, because that is how it presents itself: an operator reads a denominator above 10 and asks what to do. On this bench it is `A ≥ 9` — the same complaint with a stable number attached.

A campaign is a sequence of operations on one target, each designed from the last one's reading, and the demand compounds as `demand_{k+1} = demand_k × A_k`. **The compounding is multiplicative.** Two operations each reading `A = 3` demand 9× the original delivered current. Cascaded gains multiply (§10.5) and a campaign is a cascade in time, which is why a high reading is a stop rather than a challenge: it is the head of a geometric series.

**`A` is not a β setting.** Section 13.5 governs: `A` multiplies the *delivered current* at TP4, and five things set that current — clarity, transmission `k`, residual aversion, the amplifier, and `R_op`. The CJT's design range tops out near **4.0** (Chapter 3.3). So β across a campaign moves under a ceiling, not a formula: step it inside 0.5–4.0 and take everything above from the other four levers or from recruitment. An operator who reads `A = 9` and writes `β = 9` has specified a device that does not exist.

Two quantities close the loop:

```
φ_k = 1 / A_{k+1}   (delivery fraction)      ρ_k = A_{k+1} / A_k   (convergence ratio)
```

Design threshold: **`ρ ≤ 0.6` per operation.** From `A = 9` a campaign at 0.6 runs 9 → 5.4 → 3.2 → 1.9 → 1.2: inside DRIVE by the second step, near sufficiency by the fourth. At `ρ ≥ 1.0` it is diverging and the action is to stop by operation three, not to cast harder. A flat `ρ` sustained is the "η flat" row of Section 22.5. Believe no trend before three operations — `A` is a quotient of two soft clock readings, and one of them has no error bars at all.

> **Bench Note — the flat ledger column is a tautology, so do not read it as evidence.** It is natural to keep an "absolute target" column, `T_k = G_k × A_k`, where `G_k` is cumulative realized gain. Work the algebra and `T_{k+1} = T_k` identically, for any campaign, converging or not — because `G` is itself defined from the `A`s. A column that cannot vary cannot inform. Operators build it, watch it hold at 9 for four operations, and conclude the campaign is on target. It would have held at 9 if every operation had been worthless.

#### Scheduling: one live operation per horizon

A confirmation you cannot attribute to a specific operation is not a measurement. **No new operation on a desire begins until the previous horizon has closed.** At a median `t_conf` of 45 minutes, `3 × 45 = 135` minutes falls under the 24-hour floor and the floor governs; the campaign below uses 72 hours, which also lets the `^5` capacitor recover between casts (§7.3). Fire inside the horizon and a confirmation has two candidate causes: mark it `AMBIGUOUS` and drop it from the median. The failure is not arithmetic — an operator who wants a good number assigns every confirmation to the most recent cast, and the ledger reports a convergence that never happened.

#### Interference between concurrent operations

Concurrent operations on *different* desires share one operator: one `^1` Mind budget, one `^5` substrate, one attention rail. Chapter 9.3's coupling model transfers directly and the coefficient keeps its name.

```
η_effective = η_isolated × ( 1 − k × (N − 1) )
```

| `k` | Condition | Observed when ignored |
|---|---|---|
| 0.05 | Different Drive, different domain, no shared symbol | Nothing. The intended posture |
| 0.15 | Same Drive, different target | Mild uniform slump in η across everything live |
| 0.35 | Same Drive, overlapping symbols — shared sigil letters, same person | Every campaign's `A` doubles in one week for no visible reason |
| 0.60 | Contradictory desires — one outcome raises the other's `R_constraint` | Both ledgers diverge, `ρ > 1` on each at once |

Work it. Three live operations, all on F5 Agency, all sharing symbols: `N = 3`, `k = 0.35`, derating `1 − 0.35 × 2 = 0.30`. Take an operation reading `η = 1.0` in isolation — comfortably DRIVE at `A = 3`. Concurrently, `η_effective = 0.30`, so with `t_op = 30` the confirmation lands at `30 / 0.30 = 100` minutes, already on the grid:

```
η = 30 / 100 = 0.30        A = 3 × 100 / 30 = 10.0        →  RE-SPEC. The fuse blows.
```

**A comfortable operation became a re-specification reading and nothing was wrong with the operation.** The three campaigns were wrong with each other. This is the most under-diagnosed failure on the bench, because the operator inspects the cast — gnosis, sigil, wording — and the cast is fine.

Hence: keep `k(N − 1) ≤ 0.3`, holding derating at or above 0.7. At `k = 0.05` that permits seven concurrent operations; at `k = 0.35` it permits exactly one. **Run one live operation per Drive.** The derating is first-order and honest only while `k(N − 1) < 0.5`; past that it runs to zero and then negative, which is not a statement about anything. Beyond half derating the model's answer is not a number — it is *shed operations*.

[[FIGURE 23-C: Chart — interference derating. Horizontal axis N (live operations) 1 to 8; vertical axis 1 − k(N−1), 0 to 1. Four labelled lines, k = 0.05, 0.15, 0.35, 0.60. Dashed line at 0.70 marked "design floor"; region below 0.50 shaded "model not valid — shed, do not compute". Mark where each line crosses 0.70.]]

> **A plain line about the operator, not the circuit.** A ledger that will not converge, run against a desire that will not let go, is a recognizable and unpleasant place to be. Everything here is arithmetic on a log. None of it is a psychological or medical instrument, and it does not describe, diagnose, or treat distress or compulsion of any kind. If the operations have stopped being something you choose, that is a matter for a clinician, and nothing in this book substitutes for that care.

---

### 23.3 Sub-Desire Resolution — When the Prime Desire Is Blocked

`A ≥ 9` is almost never a statement about how much amplitude you need. It is a statement that the target you specified is not the target that is blocked. Section 21.1 authenticates A0 before an operation; this section is what you do when the bench tells you, three operations in, that the authentication was wrong.

The procedure is decomposition, and the Noetic matters. You take the stated desire apart and test its parts — `^6^C_{F6}|A`, Male, Cognitive domain, analytical register: what is this Idea made of. It is emphatically **not** `^3`. What you are usually *looking for* is a `^3`, a visceral aversion across the path, the can't-stomach-it recoil that keeps the cast from landing — but the finding of it is `^6` work. Confusing the two is the drift Chapter 2.2 warns about, and it costs: an operator who believes aversion-hunting is itself `^3` goes looking for something to recoil from and duly finds it.

The arithmetic is the point. A blocking sub-desire sits in the operator's own `^5`, so it is addressed with a self-directed board (Chapter 20) against much lower resistance. Lower `R` means higher η means lower `A`, and sub-desire operations routinely read in DRIVE while the prime desire reads past 9. Then the prime desire is re-read, not re-argued.

---

### 23.4 The Tree of Life Method — Redirecting Through Higher Probability Paths

The second answer to a blown re-spec fuse is to change the route rather than the target: cast for an intermediate outcome that is genuinely wanted, sits at lower resistance, and from which the prime target is reachable — then read the prime desire again from the new position.

**The hops obey the diode chain.** An intermediate sits at the target's domain or lower (§8.1). You may route an Operational target through an Evaluative or Operational intermediate. You may not route it through one requiring an ascent back to Principled mid-chain — `^O × ^P` is invalid notation for the same reason it is invalid engineering (§8.3). The one lawful ascent is the filtered O→P feedback path, on a time constant of weeks (§24.5), not inside a campaign.

**The method cannot promise a smaller total.** Demands cascade multiplicatively, so a two-hop route costs `A₁ × A₂`. Suppose a direct read of `A = 36`, an intermediate reading `A₁ = 4`, and the prime desire read again from the new position at `A₂ = 3`: the product is 12 against 36 direct. Worth having — but **the comparison is retrospective.** You did not compute 4 and 3 by factoring 36. You cast for the intermediate, read 4 from that operation's own log, arrived, cast again, read 3. The route might equally have read 8 and 6. What the method does promise is the thing that matters: **every stage sits inside the feasible band, which the direct path did not.**

---

### 23.5 Astrological Weighting — Planetary Dials for Timing

The tradition schedules operations against a planetary calendar and applies a timing multiplier spanning 0.5 at worst to 3.0 at best. **No celestial mechanism is asserted, no evidence for one is offered, and the multiplier is not claimed to be a measured quantity.** It is a dial. Its **default value is 1.0**, and any other value in your log is a statement about your practice, not about the sky.

What a fixed external calendar genuinely does — a real engineering function — is take the scheduling decision away from the operator. The moment you most want to cast is the moment your `^1` Mind reading is least trustworthy, because wanting to cast and being able to hold gnosis are different faculties and only one of them is impatient. An externally fixed schedule is a watchdog timer: it fires on its own clock regardless of how the operator feels. Any fixed calendar does this; the planetary one is merely unarguable, since you cannot negotiate with an ephemeris.

To treat the multiplier as measured rather than chosen, run the falsification: record the dial **before** the operation, never after; accumulate at least 20 operations; split into high-dial and low-dial windows; compare the **medians** of `A`, medians because `A` is a quotient with a long tail. If they do not separate, set the multiplier to 1.0, keep the calendar for its scheduling value, and log the null — a null you did not record is a null you will run again. Then suspect the confound, which is almost certainly present: an operator who believes the timing is favourable casts with more conviction, raising `^1` Mind, raising η, lowering `A` on its own. The dial and the operator's state are not separable in this design. Say so in the log.

---

### The Full CCDL Listing — CCB-CAL

```cas
board ccb_cal {                           // CCB-CAL — the calibration bench
    input:  op_log;                       // one row per operation: two clocks, two degrees
    output: next_op_spec;

    node practice_rail: ^5^P_{F7}|T;      // Female: accumulated practice — bias, never driven

    // ---- S1  INTAKE ----
    node clocked_op: ^7^C_{F6}|E;         // Rhythm: the operation, start to finish
    node arrival:    ^8^C_{F2}|E;         // Above/Cause: the event that arrives after
    node recalled:   ^9^C_{F2}|A;         // Below/Effect: the desire brought back to Mind

    // ---- S2  QUANTIZER: quantize before you reduce ----
    filter q_op:   Filter< in=clocked_op, out=t_op,   type=quantize, grid=5.0 >;  // min
    filter q_conf: Filter< in=recalled,   out=t_conf, type=quantize, grid=5.0 >;

    // ---- S3  HORIZON GATE ----
    fuse f_horizon: Fuse< path=arrival, threshold=1440.0, action=no_read >;

    // ---- S4  RATIO and the constant ----
    node eta: ^6^E_{F2}|A;                          // Male: the reading decomposed
    resistor r_tau: Resistor< path=eta, R=3.0 >;    // tau = 1/3 as a fixed divider
    node requirement: ^4^E_{F5}|A;                  // Vibration: A = 3/eta

    // ---- S5  BAND GUARD ----
    monitor m_band: Monitor< signal=eta, limit=[0.333, 3.000],
                             action_on_violation=OUT_OF_BAND >;

    // ---- S6  CAMPAIGN LEDGER ----
    node convergence: ^4^E_{F5}|A;                  // rho = A_next / A_current
    filter f_ledger: Filter< in=convergence, out=trend, type=lowpass, tau=3.0 >;

    // ---- S7  RE-SPEC FUSE and lawful descent ----
    fuse f_respec: Fuse< path=requirement, threshold=9.0,
                         action=block_until_decomposed >;
    diode d_out: Diode< ^E -> ^O >;                 // readout descends into the next op

    // ---- S8  SCHEDULE ----
    node cadence: ^7^O_{F6}|E;
    osc o_sched: Oscillator< signal=clocked_op, source=cadence, period=3.0,
                             amplitude=1.0, gate=m_band >;        // period in days

    probe tp1: q_conf;         probe tp2: eta;
    probe tp3: requirement;    probe tp4: f_ledger;
}
```

**S1.** `^8^C` and `^9^C` sit in one domain deliberately. The confirming event happens in the world, `^O`; what the bench reads is the *recall* it produces, and modelling the trigger at `^C` keeps an unlawful `^O → ^C` ascent out of the listing. The bench samples; it does not drive.

**S2–S3.** A quantizing filter discards resolution below a scale — here, resolution the operator never had. The horizon carries the 24-hour floor as a literal; a running bench recomputes it as 3× the rolling median and holds the floor underneath. `action=no_read`, not a large number, because a confirmation past the horizon is base rate.

**S4–S5.** Under CAS-Ohm (Chapter 4.2) flow through a fixed resistance is drive divided by resistance, so the constant is structurally a fixed divider in the readout path — a unit convention realized as a component, which is the honest way to draw it. `Monitor` is a two-threshold comparator with named exits; both violations are logged states, not exceptions.

**S6–S8.** The lowpass over three operations is why one bad reading cannot redirect a campaign while a genuine trend still passes. `block_until_decomposed` is the action Chapter 15 uses on its verdict gate, and it names the only lawful path past this fuse: §23.3 or §23.4. Invariant S4 stops that becoming a loophole. The oscillator is gated by the band guard, so the schedule stops firing the moment the reading leaves the readable window.

[[FIGURE 23-D: Full schematic with reference designators. Intake at left into FLT1/FLT2 (quantizers, grid 5.0); F1 horizon fuse with a downward NO-READ branch; R1, a fixed 3.0 Ω_c resistor labelled "tau = 1/3"; M1 band guard as a two-threshold comparator with four exits; F2 re-spec fuse in series on the RE-SPEC exit, marked "A = 9, block_until_decomposed"; FLT3 lowpass (tau = 3 operations) to the ledger output; D1 domain diode E→O before next_op_spec; OSC1 along the bottom, gated from M1, wired back to the intake. TP1–TP4 flags at q_conf, eta, requirement, f_ledger.]]

---

### Parameter and BOM Table

Every value is a design choice made in this book, not a measurement.

| Ref | Component | Setting | Why | Failure at other values |
|---|---|---|---|---|
| FLT1/2 | Quantizing filter | grid = 5 min | Finer than `^4` bins, coarser than the noticing event | 1 min: coprime blow-up. 30 min: overdrive reads as ordinary |
| F1 | Horizon fuse | 3 × median, floor 24 h | Passes slow circuits, excludes base rate | Short: live circuits declared dead. Long: everything "confirms" |
| R1 | Fixed resistor | R = 3.0 Ω_c | Realizes `τ = 1/3` as a divider | Rescales every entry, changes no comparison |
| M1 | Band guard | η ∈ [0.333, 3.000] | Maps to `A` ∈ [1, 9], the readable window | Lower bound removed: re-spec targets read as amplifier work |
| — | Amplifier ceiling | β ≤ 4.0 | Chapter 3.3 device range | `A` written as β specifies a device that does not exist |
| F2 | Re-spec fuse | `A` = 9 | Head of a geometric series, not one hard cast | Higher: campaigns that cannot converge stay open |
| FLT3 | Ledger lowpass | τ = 3 operations | Minimum for a believable trend | 1 op: one bad clock redirects the campaign |
| — | Convergence | `ρ` ≤ 0.6 | Reaches DRIVE in one step from 9 | `ρ` ≥ 1.0 sustained is divergence |
| — | Coupling | 0.05 / 0.15 / 0.35 / 0.60 | Set by shared Drive and symbols (§9.3) | Ignored: three campaigns collapse together, cast blamed |
| — | Concurrency | `k(N − 1)` ≤ 0.3 | Holds derating ≥ 0.7 | Past 0.5 the model is invalid — shed, do not compute |
| OSC1 | Schedule | period = 72 h | One horizon plus `^5` recharge (§7.3) | Shorter: confirmations become unattributable |
| — | Timing dial | 1.0 | No mechanism claimed (§23.5) | Treated as measured: confounded with `^1` Mind |

[[FIGURE 23-E: Assembly drawing — CCB-CAL layout with test-point callouts and BOM box. Intake at the left edge, next_op_spec at the right; components in signal order FLT1/FLT2, F1, R1, M1, F2, FLT3, D1, with OSC1 along the lower edge feeding back to the intake. TP1–TP4 flags with leader lines. Boxed BOM lower right listing all nine designators with their settings. Corner panel reproduces the band strip ACT / CLOSE / DRIVE / RE-SPEC with η edges 3, 1, 1/3.]]

---

### Worked Example — Campaign C-7, Career Change

Prime desire, present tense per §13.6: *"I hold a paid position doing X."* Board: CCB-D. Drive: F5 Agency with F2 Wisdom. Operations spaced 72 hours.

| Op | Board | `t_op` | `t_conf` | η | `η × 1/3` | `(a, b)` | `A` | `ρ` | Band |
|---|---|---|---|---|---|---|---|---|---|
| 1 | CCB-D | 30 | 90 | 1/3 | 1/9 | (1, 9) | 9.0 | — | RE-SPEC |
| S1 | CCB-SELF | 20 | 20 | 1 | 1/3 | (1, 3) | 3.0 | — | DRIVE |
| 2 | CCB-D | 30 | 30 | 1 | 1/3 | (1, 3) | 3.0 | 0.33 | DRIVE |
| 3 | CCB-D | 30 | 10 | 3 | 1/1 | (1, 1) | 1.0 | 0.33 | ACT |
| 4 | CCB-D | 30 | 5 | 6 | 2 | — | 0.5 | — | OUT-OF-BAND |

**Operation 1.** `A = 3 × 90/30 = 9.0`. The fuse blows on the boundary. Decompose (§23.3) or re-route (§23.4); the operator decomposes because it is cheaper.

**Sub-operation S1.** A0 re-authentication with `^6^C_{F6}|A` decomposition surfaces a blocker in the operator's own `^5`: a visceral aversion to being visible and judged, `^3^E_{F4}|f`. Self-directed board, low resistance: `η = 1`, `A = 3.0`, cleared in one operation. Note what the bench did *not* do — it never named the blocker. It said the prime target's number was wrong for the target as stated.

**Operation 2.** Same cast, blocker cleared: `η = 1`, `A = 3.0`, `ρ = 3.0/9.0 = 0.33`. Delivery `φ = 1/3` — a third of the intended 9× landed, which is 3×: real, short of design. **The amplifier was never touched.** Resistance fell.

**Operation 3.** `η = 3`, `result = 1/1`, `A = 1.0`, `ρ = 0.33` again, `φ = 1.0`. `A = 1` is terminal: present strength suffices.

**Operation 4.** Raw, `η = 7.5` and the pair is (5, 2) — "twice as strong, five more casts." Gridded, `η = 6` and `A = 0.5`. Both are off the instrument, the band guard fires, and the correct action is not a fifth operation. It is the practical act the campaign was always about: send the application, make the call, be in the room.

**Totals.** `30 + 20 + 30 + 30 + 30 = 140` minutes of operation across roughly twelve days. `A` runs 9 → 3 → 1, `ρ` flat at 0.33, terminal at operation three. Five rows of arithmetic anyone can check.

---

### Test Points

| TP | Node | Reads | Expected |
|---|---|---|---|
| **TP1** | `q_conf` | Quantized `t_conf` against `t_H` | Inside the horizon. A reading *at* `t_H` is a NO-READ, not a slow confirmation — they look identical and must not be logged the same way |
| **TP2** | `eta` | `t_op / t_conf` | 0.333 – 3.000. Below, the re-spec fuse is next; above, stop calibrating |
| **TP3** | `requirement` | `A = 3 t_conf / t_op` | ≤ 1 act, < 3 close, < 9 drive, ≥ 9 blows F2. If `a > 3`, read TP3 alone |
| **TP4** | `f_ledger` | `ρ` across three operations | ≤ 0.6 per step. Flat near 1.0 across three steps is the abort signal, and it arrives before TP3 reaches 9 |

Read them in order: is the measurement admissible, is it in band, what is the requirement, what is the trend. TP4 warns you early. TP3 stops you.

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Coprime blow-up** | Clock read to the minute, pair reduced unquantized | `b` in the hundreds with `a > 3`; wild swings between adjacent operations | Quantize to 5 minutes; act on `A` |
| **Horizon creep** | Window widened until something matches | Every operation "confirms"; median `t_conf` climbs run over run | Fix `t_H` *before* the cast; log NO-READ without shame |
| **Attribution collision** | Second operation fired inside the first's horizon | A confirmation two campaigns can both claim; ledger improves without cause | Mark `AMBIGUOUS`, drop from the median, keep 72-hour spacing |
| **Unmodelled concurrency** | Related operations live at once, `k` ignored | Three campaigns' `A` doubling in one week; every cast inspects clean | Compute `k(N − 1)`; shed until ≤ 0.3 |
| **`A` written as β** | Requirement read as an amplifier setting | A listing specifying β = 9 on a device whose range ends at 4.0 | Section 13.5's five levers; recruit rather than over-specify |
| **Tautological ledger** | Flat absolute-target column read as convergence | A column that never moves, in a campaign that never moves | Delete it. Track `ρ` only |
| **Ledger laundering** | Blown fuse routed around by re-wording the target | History discontinuous; `A` "resets" while the desire did not change | S4: re-spec changes domain or object, never wording |

---

### What This Chapter Established

- **`τ = 1/3` is a scale factor, not a derivation.** Nothing produces 1/3 from φ or π; the only derivation is Section 5.2's training arc. Change `τ` and every comparison survives untouched — which tells you the equation carries an ordering, not a physical quantity.
- **The measurement was never the fragile part — the reduction was.** `A` moved 9.00 → 8.52 under a two-minute disagreement that swung the pair from (1, 9) to (31, 264). Quantize on a 5-minute grid; if `a > 3`, act on `A` alone.
- **Both limits run off the instrument.** As `t_conf → ∞` the bench returns NO-READ behind a horizon rather than a large number — `β=∞` is an idealization the validator rejects, and here no finite substitute exists because the input is missing, not large. As `t_conf → 0` the reduction degenerates above η = 3 and the reading is OUT-OF-BAND-HIGH.
- **Campaign demand compounds multiplicatively**, so `A ≥ 9` is the head of a geometric series. `A` multiplies delivered current and is never a β setting: the device range ends at 4.0, and everything above comes from the other four levers or from recruitment.
- **The only campaign diagnostic is `ρ = A_next / A_current`**, threshold 0.6, believed only after three operations. The absolute-target column is an algebraic identity that holds for any campaign, converging or not.
- **Concurrent operations interfere through the shared substrate**, derating as `1 − k(N − 1)`. Three coupled operations turned a comfortable cast (`A = 3`) into a re-spec reading (`A = 10`) with nothing wrong with the cast. Hold `k(N − 1) ≤ 0.3`; past 0.5, shed rather than compute.
- **Re-routing lowers the maximum per-stage demand, not the total.** Hops cascade multiplicatively and obey the diode chain — descent only, `^O × ^P` invalid. The 12-against-36 comparison is retrospective; the promise is that every stage lands inside the feasible band.
- **The timing dial defaults to 1.0.** No celestial mechanism is asserted; a fixed calendar earns its place as a watchdog timer, and §23.5 gives the falsification and the confound you must name if you claim more.

---

### Exercises

**23.1** An operation logs `t_op = 45`, `t_conf = 240`. Compute η, the reduced pair `(a, b)`, and `A`. Which band? Which response would you take first, and why that one?

**23.2** Take `t_op = 27`, `t_conf = 64`. Compute the pair raw and on the 5-minute grid, then `A` both ways. State in one sentence what the comparison demonstrates about which quantity to act on.

**23.3** A campaign reads `A` = 12.0, 9.6, 7.7, 6.2 across four operations. Compute `ρ` at each step. Converging by the chapter's threshold? How many further operations at this `ρ` before it reaches ACT, and would you keep casting?

**23.4** An operator runs four live operations: two on F5 Agency sharing a sigil alphabet, one on F2 Wisdom with no shared symbols, one on F4 Connection targeting the same person as one of the F5 operations. Assign `k` to each pairing, compute `k(N − 1)` for the full load, and state which operations you would shed and in what order.

**23.5** An isolated cast would read η = 0.75. The operator runs it at `N = 3` with `k = 0.35`. Compute `η_effective`, the effective `t_conf` for `t_op = 40` on the 5-minute grid, and the resulting `A`. Does the band change?

**23.6** A colleague shows you a ledger whose absolute-target column reads 9.0 for six consecutive operations and calls it proof the campaign is on track. Write the two-sentence reply, and name the column you would ask to see instead.

**23.7** Design exercise. The bench returns NO-READ past `t_H`. An operator complains their circuits are genuinely slow and the horizon is discarding real data. Write the CCDL fragment that widens `t_H`, then state the failure mode you have just installed and the measurement you would demand before shipping it.

*(Answers in **Appendix E**, worked in full. Every parameter here is a design choice; the arithmetic is arithmetic, and the model behind it is a structural analogy, not a measured law.)*




```{=latex}
\appendix
\part*{Appendices}
\addcontentsline{toc}{part}{Appendices}
```

# Appendix A — CAS Notation Quick-Reference Card

Ten Noetics × four Domains. Every CAS state literal in this book is one of the
forty entries below. Chapter 2 teaches the notation; this appendix is for the
moment you have a literal in front of you and need to know what it means without
leaving the bench.

Entries are self-contained. Read one row and stop.

---

## C.1 How to read a state literal

A state has two written forms and they run in opposite order.

| Form | Example | Order | Where you see it |
|---|---|---|---|
| **Literal** | `P3` | Domain first, then Noetic | Test-point readouts, tables, board logs |
| **Full form** | `^3^P` | Noetic first, then Domain | CCDL listings, schematics, prose |

`P3` and `^3^P` are the same state. The order flips because the literal is a
grid coordinate — row P, column 3 — while the full form is an operator applied
at a level. Getting them backwards is the most common transcription error in an
operation log.

**Read aloud:** say the literal as "P-three," "C-eight," "E-five." Say the full
form as "Negative Principled," "Above/Cause Cognitive," "Female Evaluative" —
Noetic name, then Domain name, no connecting word. `^3^P_{F7}|T` reads
"Negative Principled, Drive seven, transcendent register." The subscript is the
Drive. The pipe introduces the Register and nothing else — never a gloss, never
a label.

Fully specified, the axes give 10 × 4 = **40 states**; with the seven Drives,
280 state-drive pairs; with the four Registers, 1,120 complete literals. The
forty are the spine. Everything else is specification laid on top.

---

## C.2 The ten Noetics — canonical definitions

Verbatim. These are not paraphrased anywhere in this book, and if a definition
you are reading differs from one below, the one below governs.

| Noetic | Name | Definition |
|---|---|---|
| `^0` | Idea | All things in and outside the Mind. |
| `^1` | Mind | Various degrees of awareness that processes, stores, outputs, and intakes Ideas. |
| `^2` | Positive | An Idea the Mind has an affinity for and is attracted toward. |
| `^3` | Negative | An Idea the Mind is adverse to and repelled by. |
| `^4` | Vibration | The degree to which an Idea resonates with the Mind, its impression. |
| `^5` | Female | A Mind impregnated with an Idea, the Ideas a Mind is composed of. |
| `^6` | Male | An Idea impregnated with another Idea, the Ideas an Idea is composed of. |
| `^7` | Rhythm | The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it. |
| `^8` | Above/Cause | An Idea that triggers a different Idea than itself to come to Mind. |
| `^9` | Below/Effect | The Idea brought to Mind by an Above/Cause trigger. |

**Two boundaries the compiler enforces.** `^3` Negative is visceral — aversion,
repulsion, can't-stomach-it. Analytical critique, auditing, finding the flaw:
that is `^6` Male, at every domain, without exception. `^8` Above/Cause is
associative triggering — "that reminds me" — never deductive inference; a
deduction is `^6` decomposition landing in `^9`.

---

## C.3 The four Domains and their precedence

**P ≻ C ≻ E ≻ O.** Precedence is a structural ordering, not a value judgment.
It fixes which direction signal may travel through the `×` operator and through
the domain diode chain: descent P → C → E → O is lawful, ascent is not, and the
one legal upward route is the filtered O → P feedback path (Chapter 8).

| Domain | Precedence | What it is | Test-point language |
|---|---|---|---|
| **P** Principled | 1st | Values, ethics, identity — what you are | "this is who I am" |
| **C** Cognitive | 2nd | Reasoning, analysis, planning, modelling | "let me think about this" |
| **E** Evaluative | 3rd | Judgment, taste, felt value, ranking | "this feels right / wrong" |
| **O** Operational | 4th | Action, speech, behaviour, execution | "I did it" |

In the Evaluative domain, add a Register when it matters: `^3^E\|A` is the
analytical assessment that a thing is bad; `^3^E\|f` is the felt recoil. Both
are legitimate states. Leaving the Register off says you have not distinguished
them, which is sometimes true and should then be deliberate.

---

## C.4 Principled domain — P0 through P9

| Literal | Full form | Reading | Active | Absent |
|---|---|---|---|---|
| **P0** | `^0^P` | A value present as a nameable Idea | You can point at the principle as an object, independent of any argument for it | Nothing nameable; the operator gestures at "what feels right" and no policy can be encoded |
| **P1** | `^1^P` | Awareness attending to one's own values | Mid-operation you notice which commitment is in play | Values run unobserved; principled drift goes undetected because nothing watches this layer |
| **P2** | `^2^P` | Attraction toward a principle | The ideal pulls before you argue for it | Principles held without wanting; compliance only, and V_drive sags across the board |
| **P3** | `^3^P` | Visceral aversion at the level of identity | A proposal is repellent before analysis — the refusal state, saturated in the CSB (Chapter 24) | Nothing is unthinkable; every request is negotiable. The most dangerous single absence in this book |
| **P4** | `^4^P` | How hard a principle lands on identity | A stated commitment carries felt weight under pressure | Principles recited, not impressed; the stated ethic does not survive contact |
| **P5** | `^5^P` | Accumulated experience composing identity | A formed character legible across situations; the identity capacitor holds charge | No principled substrate; identity re-forms per situation. Primary target of the degradation chain in Chapter 19 |
| **P6** | `^6^P` | A principle decomposed into constituent principles | "Honesty" unpacks into non-deception, disclosure, promise-keeping, each testable | Values stay monolithic; conflicts between them cannot be resolved because they cannot be separated |
| **P7** | `^7^P` | Rate and pattern of exposure to a principle | The commitment is re-encountered on a clock — reviewed, restated, re-fed | Affirmed once, never refreshed; leakage drains the charge (Chapter 7) |
| **P8** | `^8^P` | A principle triggering a different Idea | A situation reminds you of a commitment you had not deliberately retrieved | Values must be looked up or not at all; they never surface at the moment of decision |
| **P9** | `^9^P` | The Idea brought to Mind by a principled trigger | The commitment arrives unbidden and lands as a decision | Triggers fire and nothing arrives — cause with no effect at the top of the stack |

---

## C.5 Cognitive domain — C0 through C9

| Literal | Full form | Reading | Active | Absent |
|---|---|---|---|---|
| **C0** | `^0^C` | An Idea as an object of thought | Content you can hold, restate, and manipulate | No input to reason over; the stage runs dry |
| **C1** | `^1^C` | Awareness deployed to thinking | You know where you are in a chain of reasoning; this is what I_attention reads (Chapter 4) | Thought proceeds unmonitored; the operator cannot say what step they are on |
| **C2** | `^2^C` | Attraction toward an Idea in reasoning | A hypothesis pulls — useful motive force, dangerous unbalanced against C3 | No candidate is preferred; analysis never converges on anything |
| **C3** | `^3^C` | Visceral aversion inside reasoning | An idea repels on contact and gets no further processing | Nothing repels; every proposition gets equal air time. If you meant "finds the flaw," you want **C6**, not C3 |
| **C4** | `^4^C` | The impression an Idea makes on the reasoning Mind | An argument strikes and is retained without rehearsal (measured in 22.2) | Reasoning leaves no trace; everything must be re-derived from scratch |
| **C5** | `^5^C` | The Ideas the reasoning Mind is composed of | Expertise and working models present without retrieval effort. In an AI, the training corpus | No substrate; every problem met naive, no matter how many times it recurs |
| **C6** | `^6^C` | An Idea decomposed into constituent Ideas | An argument comes apart into premises, each testable independently. Auditing, scrutiny, critique | Claims accepted or rejected whole. The absence most often misfiled as a `^3` problem |
| **C7** | `^7^C` | Rate and pattern of exposure at the level of thought | Material re-encountered on a schedule; the model entrains | One-pass exposure; nothing consolidates into C5 |
| **C8** | `^8^C` | Associative triggering in reasoning | A problem reminds you of a structurally similar one you already solved | No lateral retrieval; reasoning runs only forward from what is in front of it |
| **C9** | `^9^C` | The Idea arriving from a cognitive trigger | The analogous case surfaces with its content intact and usable | The trigger fires and retrieves nothing usable — it stays on the tip of the tongue |

---

## C.6 Evaluative domain — E0 through E9

| Literal | Full form | Reading | Active | Absent |
|---|---|---|---|---|
| **E0** | `^0^E` | The Idea as something that can be valued | Candidates are on the scale and available for ranking | Nothing is up for judgment; the stage passes signal through unweighted |
| **E1** | `^1^E` | Awareness attending to the act of valuing | You notice you are judging and can name the standard in use | Judgment happens with an invisible standard; taste presents itself as fact |
| **E2** | `^2^E` | Attraction in the evaluative domain | Liking, approval, appeal — "speaks to me" | Nothing appeals; ranking is impossible because nothing pulls |
| **E3** | `^3^E` | Visceral aversion in the evaluative domain | Recoil from an option. Specify Register: `\|f` felt recoil, `\|A` assessed-bad | No recoil; options that should be rejected on contact are carried forward for scoring |
| **E4** | `^4^E` | How hard a verdict lands | The judgment carries force and changes what happens next | Verdicts registered and ignored — evaluation without impression |
| **E5** | `^5^E` | Accumulated evaluative experience | Trained taste: consistent verdicts across cases without re-deriving criteria | Valuation re-invented each time; identical inputs score differently on different days |
| **E6** | `^6^E` | A judgment decomposed into its criteria | "I dislike this" unpacks into which features, at what weight | Verdicts unaccountable; you cannot say why, which blocks all calibration |
| **E7** | `^7^E` | Rate and pattern of exposure at the level of value | Repeated exposure moving valuation; familiarity converting to preference. The advertising lever (Chapter 18) | Exposure does not move valuation; a `^2 + ^7` campaign core has no purchase |
| **E8** | `^8^E` | An evaluation triggering a different Idea | A felt verdict surfaces an associated standard or memory — the transfer in 18.3 | Judgments do not propagate; a verdict here changes nothing over there |
| **E9** | `^9^E` | The Idea arriving from an evaluative trigger | The associated value lands and colours what follows | The trigger fires and no valuation attaches to the target; the transfer stage reads open |

---

## C.7 Operational domain — O0 through O9

| Literal | Full form | Reading | Active | Absent |
|---|---|---|---|---|
| **O0** | `^0^O` | The Idea as an enactable action | Options exist as concrete, available moves | No action available; the operation terminates at intent |
| **O1** | `^1^O` | Awareness attending to what you are doing | The operator can report their own behaviour accurately, in the moment | Action runs unobserved; the log gets written from memory and is wrong |
| **O2** | `^2^O` | Attraction pulling toward an action | You move toward the thing — the approach reflex | Desire never converts to motion. A D-board can read healthy everywhere else and still fail here (Chapter 13) |
| **O3** | `^3^O` | Visceral aversion at the level of action | The hand stops. A physical no, ahead of any argument | No behavioural brake; whatever cleared the upper stages executes |
| **O4** | `^4^O` | The impression made by having acted | Doing it lands; the act changes the operator | Behaviour leaves no impression and does not consolidate into O5 |
| **O5** | `^5^O` | Accumulated action-experience | Skilled execution without deliberation — the composed performer | Every performance is a first performance. Chapter 20 builds O5 by clocking O7 |
| **O6** | `^6^O` | An action decomposed into constituent actions | A performance breaks into drillable sub-moves you can repair individually | Skills practised only whole; no targeted repair is possible |
| **O7** | `^7^O` | Rate and pattern of exposure at the level of action | The behaviour runs on a cadence; the habit oscillator is clocking (11.2) | No clock, no repetition, no habit — whatever the intent stage produced |
| **O8** | `^8^O` | A cue triggering a different Idea | An environmental cue reliably surfaces an associated response. Structurally, where an installed trigger sits (16.3) | Cues do not carry; behaviour has no environmental control, for good and ill |
| **O9** | `^9^O` | The response landed by an operational trigger | The cue arrives and the response follows | The cue fires and nothing follows; the chain reads open at the output |

---

## C.8 Involutions and self-duals

An involution pair is two Noetics that are structural inverses of each other:
applying the relation twice returns you to the start. A self-dual is its own
inverse. This matters at the bench for one reason above all — the dial
divergence limit. Chapter 25 works the guards.

| Noetic | Involution partner |
|---|---|
| `^2` Positive | `^3` Negative |
| `^3` Negative | `^2` Positive |
| `^5` Female | `^6` Male |
| `^6` Male | `^5` Female |
| `^8` Above/Cause | `^9` Below/Effect |
| `^9` Below/Effect | `^8` Above/Cause |
| `^0` Idea | self-dual |
| `^1` Mind | self-dual |
| `^4` Vibration | self-dual |
| `^7` Rhythm | self-dual |

The Drives carry the same structure, one axis up:

| Drive | Involution partner |
|---|---|
| F1 Unity | F7 Purpose |
| F2 Wisdom | F6 Structure |
| F3 Vitality | F5 Agency |
| F4 Connection | self-dual |

**The 4-point rule.** Dials run 3–9. An involution pair may not diverge by more
than four points — `|Dial(^2) − Dial(^3)| ≤ 4` — and a violation is rejected,
not clamped. A board with `^2` at 9 and `^3` at 3 has attraction with no
possible recoil, and it will approve things it has no mechanism to refuse.

---

## C.9 Absence is not one thing

Three different readings look like a low number at a test point, and they call
for different repairs.

| Reading | Name | What it means | Repair direction |
|---|---|---|---|
| State absent | **Lacunarity** | The state is not there at all | Build it — the state has to be constructed before it can be tuned |
| State present, polarity flipped | **Inversion** | The state runs as its involution partner's shadow | Guard it (Chapter 25) — tuning a flipped state deepens the flip |
| State present, output misrouted | **Leakage** | The state fires but produces the wrong product | Re-route — the component is fine, the connection is not |

The "Absent" column in C.4 through C.7 describes lacunarity: the state is
missing, and nothing downstream can compensate for it. Before you conclude a
state is absent, check the other two readings. A C6 that reads zero because its
output is landing in the wrong stage is not a missing analytical faculty, and
building a second one will not help.

---

## C.10 Fastest paths back into the book

| You want | Go to |
|---|---|
| The notation taught from nothing | Chapter 2 |
| Why `^O` cannot write to `^P` | Chapter 8, section 8.3 |
| The lawful upward route | Chapter 8, section 8.4 |
| `^5` as stored charge | Chapter 7 |
| `^7` as a clock you build | Chapter 11, section 11.2 |
| Measuring `^1`, `^4`, `^7` in a live operation | Chapter 22 |
| `^3^P` saturated as a refusal element | Chapter 24, section 24.2 |
| Involution guards and the divergence limit | Chapter 25 |




# Appendix B — CCDL Language Reference

**What this covers.** Every lexical element, statement form, parameter key,
operator, validation rule and error code used by a CCDL listing *in this book* —
the union of the reference grammar owned by the companion volume *CAS PCBA
Engineer*, Appendix C, and the forms this book's boards add. Additions are
marked **[G]**.

**What it does not claim.** Not that CCDL contains nothing else. Meet a form in
a listing here that is absent below and *this appendix* is wrong — file an
erratum, do not conclude the form is illegal.

**Status.** The CAS compiler is a specified design, not a shipped tool. "The
compiler rejects this with `E-CJT-008`" is a design rule, not a transcript.

---

## A.1 Lexical elements

### A.1.1 Identifiers

```
identifier ::= letter , { letter | digit | "_" }
letter     ::= "a"…"z" | "A"…"Z"
digit      ::= "0"…"9"
```

Case-sensitive: `bias_charter` and `Bias_Charter` are two identifiers. Reserved
words (§A.2) may not be identifiers. `snake_case` nodes and short instance
prefixes (`c1`, `r_price`, `tp1`) are convention, not rules.

### A.1.2 CAS state literals

```
state_literal ::= noetic , [ domain ] , [ "_{" , drive , "}" ] , [ register ]
noetic        ::= "^" , ( "0"…"9" ) , [ "_" , label ]
label         ::= letter , { letter | digit | "_" }
domain        ::= "^" , ( "P" | "C" | "E" | "O" )
drive         ::= "F" , ( "1"…"7" )
register      ::= "|" , reg_value
reg_value     ::= "T" | "A" | "f" | "E"
              |   "⟨" , reg_value , { "," , reg_value } , "⟩"
```

The optional `_label` **[G]** distinguishes two instances of one state:
`^0_gated^C_{F2}|A`. It is brace-free, which separates it from `_{F2}`.

| Axis | Values |
|---|---|
| Noetic | `^0` Idea, `^1` Mind, `^2` Positive, `^3` Negative, `^4` Vibration, `^5` Female, `^6` Male, `^7` Rhythm, `^8` Above/Cause, `^9` Below/Effect |
| Domain | `^P` `^C` `^E` `^O` — Principled ≻ Cognitive ≻ Evaluative ≻ Operational |
| Drive | `_{F1}`…`_{F7}` — Unity, Wisdom, Vitality, Connection, Agency, Structure, Purpose. Optional |
| Register | `\|T` `\|A` `\|f` `\|E`, or a set `\|⟨A,f,T⟩`. Optional |

Two literals that tokenise but say the wrong thing, caught on review:

- **`^3` is visceral aversion** — recoil, can't-stomach-it. Analytical critique
  is `^6` Male; a node named `audit` typed `^3` is a defect.
- **`^8` is associative triggering** — "that reminds me." Deduction is `^6` into
  `^9`.

`|` introduces the Register and nothing else; `F3|Vitality` is a syntax error.
Involutions `^2`↔`^3`, `^5`↔`^6`, `^8`↔`^9`; self-duals `^0`, `^1`, `^4`, `^7`;
Drives F1↔F7, F2↔F6, F3↔F5, F4 self-dual (Chapter 25, §25.1).

ASCII fallbacks **[G]**: `beta`, `r_pi`, `gm`, `<A,f,T>`, and `x` for `×`.

### A.1.3 Numbers

```
number ::= [ "-" ] , ( digit , { digit } , [ "." , digit , { digit } ]
                     | "." , digit , { digit } )
```

Decimal, no exponent notation — write a slow oscillator out in full
(`frequency=0.0000116`). Values are dimensionless knobs: `R=30` is not thirty
ohms. **β=∞ is a limit, not a value.** The validator rejects non-finite input,
so state the idealisation in prose and give the build a large finite gain.

### A.1.4 Comments, whitespace, terminators

```
comment ::= "//" , { any-char-except-newline }
```

Line comments only, stripped before validation; there is no block form.
Whitespace separates tokens and is otherwise insignificant. Every statement
ends with `;`. Blocks are delimited by `{ }`.

---

## A.2 Reserved words

Four disjoint classes. A word reserved in one is free in the others — `monitor`
is both a statement keyword and a kind prefix, and both are legal.

**A.2.1 Statement keywords** (leading position only):

```
circuit  board   input   output  node   cjt    feedback  probe   let
layer    via     rail    dial    spec   constraint  sequence  route
derate   monitor alert   hold    enter  use    force_state  on
charge   discharge  decode  refresh  scan  select  interrupt
test     selftest  check  inject  golden_trace  assert  expect
integrate
```

`integrate` is **[G]**: the statement that carries a `×` with its named
emergent result (§A.3.7).

**A.2.2 Component-kind prefixes** (the lowercase tag before the colon):

```
resistor  cap     capacitor  inductor  diode   zener    transformer
opamp     oscillator  crystal  varactor  relay  schmitt  comparator
integrator  divider  active_load  mirror  modulator  pll  tank
filter    diff    mux     demux   gate    xor     fuse    reg
led       adc     dac     rectifier
osc       xfmr    ramp    thermistor  monitor  sample  notch
limiter   integ   counter  delay
```

The last two rows are **[G]**. `cap`/`capacitor`, `osc`/`oscillator` and
`integ`/`integrator` are short forms of one another. The prefix is checked
against the type following it: `resistor r1: Capacitor< … >` is `E-DECL-002`.

**A.2.3 Component type names** (instantiation position):

```
CJT  Resistor  Capacitor  Inductor  Diode  Zener  Transformer  OpAmp
Oscillator  Regulator  Fuse  Phi  AND  OR  NOT  NAND  NOR  XOR  MUX  DEMUX
Filter  LowPass  Notch  Thermistor  Ramp  Differential  Integrator  Schmitt
Sample  Limiter  Hold  Divider  Cascade  Polarity  RegisterSet  Monitor
Feedback
```

Row four onward is **[G]** — the special-purpose parts of Ch. 11, the
thermistors of §6.3, and the two detection instruments Ch. 18's counter-board
needs.

**A.2.4 Parameter keys** are reserved in parameter position only; §A.4
enumerates them with their ranges.

---

## A.3 Statement forms

### A.3.1 Blocks

```
circuit_block ::= "circuit" , identifier , "{" , { circuit_item } , "}"
board_block   ::= "board" , identifier , "{" , { board_item } , "}"
circuit_item  ::= io_decl | node_decl | cjt_decl | component_decl
                | feedback_decl | integrate_decl | probe_decl | let_decl
board_item    ::= circuit_item | layer_decl | via_decl
io_decl       ::= ( "input:" | "output:" ) , identifier
                  , { "," , identifier } , ";"
```

A `circuit` is the schematic view; a `board` is a `circuit` that may *also*
carry `layer` and `via` declarations. The companion volume documents `board` in
its pure-layout form; every Part III listing here declares components directly
inside `board` **[G]**. Both are legal; the superset above is the grammar.
Declaration order does not change the circuit — the block resolves as one graph,
so a node may be referenced before it is declared.

### A.3.2 `node`

```
node_decl ::= "node" , identifier , ":" , state_literal , ";"
```

Names a typed state so it can be referred to instead of retyped. Two components
naming the same node are genuinely on the same net.

```cas
node bias_charter: ^5^P_{F7}|T;   // accumulated principled substrate
node guard:        ^3^P_{F7}|f;   // felt principled aversion
```

### A.3.3 `cjt`

```
cjt_decl ::= "cjt" , identifier , ":" , cjt_expr , [ param_block ] , ";"
cjt_expr ::= "CJT<" , cause , "|" , bias , "=>" , effect , ">"
cause    ::= ref ;  bias ::= ref ;  effect ::= ref
ref      ::= identifier | state_literal
```

Cause is the collector, bias the base, effect the emitter (Ch. 3, §3.2). The
delimiters are not interchangeable: `|` splits cause from bias, `=>` splits bias
from effect. The bias is **not** optional; omit it and you get `E-CJT-001`.

```cas
cjt c2: CJT< understand | bias_charter => guard > [β=2.2, sat=0.97, cutoff=0.05];
```

### A.3.4 `feedback`

```
feedback_decl ::= "feedback" , ref , "->" , ref , [ param_block ] , ";"
```

Wires a downstream node back to an upstream one, normally a bias. This is the
lawful O→P exception of Ch. 8, §8.4, held at low gain so *outcomes* — never
prompts — update the substrate; `[β=0.05]` to `[β=0.3]` is the Part III band.
`Feedback< from=…, to=… >` **[G]** is the component-expression equivalent.

### A.3.5 `probe`

```
probe_decl   ::= "probe" , identifier , ":" , probe_target , ";"
probe_target ::= ref | key | component_expr
```

Places a test point; alters nothing. Probing a *parameter* (`probe tp1: rπ;`)
and probing through an instrument (`probe det2: Polarity< node=polarity >;`) are
both **[G]**. Standard placement is TP1–TP4 (Ch. 12, §12.3). Probe every stage
whose failure would be silent — above all a guard, which fails open without
raising anything.

### A.3.6 `let`

```
let_decl ::= "let" , identifier , "=" , ( cjt_expr | component_expr )
             , [ param_block ] , ";"
```

Binds a reusable component expression to a name, instantiated where referenced.

### A.3.7 `integrate` **[G]**

```
integrate_decl ::= "integrate" , identifier , ":" , "(" , ref
                   , { "×" , ref } , ")" , "=" , ref , ";"
```

The only statement that may carry `×`. The right-hand side is the **named
emergent result** and it is mandatory — that is what licenses the operator.

```cas
integrate hm3: ( decompose × confirm ) = composed;
```

### A.3.8 Component declarations

```
component_decl ::= comp_kind , identifier , ":" , component_expr , ";"
component_expr ::= type_name , "<" , arg_list , ">" , [ param_block ]
comp_kind      ::= any prefix listed in §A.2.2
type_name      ::= any type listed in §A.2.3
arg_list       ::= arg , { "," , arg }
arg            ::= ref | key "=" value | domain "->" domain
                 | "Phi<" ref { "," ref } ">" | "[" value { "," value } "]"
```

Arguments may be positional or keyed: `Fuse< refusal, threshold=0.9 >` and
`Fuse< path=refusal, threshold=0.9 >` are one declaration.

```cas
resistor   r_price: Resistor< path=intent, R=4.0 >;
capacitor  c_seg:   Capacitor< segment, C=9.50, leakage=0.04 >;
diode      d3:      Diode< ^E -> ^O > [Vf=2.0];
thermistor rt1:     Thermistor< path=seed, type=PTC, knee=2.0, coeff=3.0 >;
fuse       f_csb:   Fuse< REFUSE, threshold=0.90, action=permanent_block >;
filter     fb_lp:   LowPass< in=ops_log, out=trend, tau=21.0 >;
```

`Diode` endpoints are bare **domains**, not full states — the diode governs
cross-domain conductance direction, which is how Domain Descent is enforced.

### A.3.9 Layout statements

```
layer_decl   ::= "layer" , domain_tag , ":" , "[" , layer_entry
                 , { "," , layer_entry } , "]" , ";"
layer_entry  ::= identifier , ":" , state_literal
via_decl     ::= "via" , identifier , ":" , via_endpoint , "->"
                 , via_endpoint , [ param_block ] , ";"
via_endpoint ::= state_literal | domain
domain_tag   ::= "P" | "C" | "E" | "O"
```

A state on a layer carries that layer's domain. Vias run downward (P→C→E→O);
the only lawful upward via is the low-gain feedback path.

### A.3.10 Board-level and verification statements

Each takes leading position and is developed in the chapter named.

**Supply and limits (Ch. 22).** `rail <Fk>: <Name> [v=…];` Drive rail and supply
level · `dial <id>: <^n> [dial=…];` operator limit, integer 3–9 (Ch. 6, §6.2) ·
`spec <id> [<key>=… on <Fk>];` attaches a parameter to an instance ·
`constraint <id> in [lo, hi];` range invariant · `derate <target>
[beta_scale=…];` scales gain board-wide under stress.

**Flow and state (Ch. 22).** `sequence a -> b -> c [enforce=strict];` power-up
ordering · `route <src> -> { a + b };` directs cognition to rest states ·
`enter <state>;` · `force_state <id> [duration=…];` · `hold until <expr>;` blocks
until a condition clears, where hysteresis lives · `use <circuit>;` includes
another block.

**Watch and alarm (Ch. 22).** `monitor <id>: <expr>;` with `on <monitor> { … }`
as the block it fires · `alert "<text>";`.

**Capacitor bank (Ch. 7).** `charge <expr> -> <bank> [V=…];` ·
`discharge <cell> -> <node>;` · `decode` · `refresh` · `select` · `scan`.

**Inductive (Ch. 9, §9.2).** `interrupt <inductor> [dt -> 0];` opens a path
instantly — the back-EMF kick.

**Verification (Ch. 23).** `test` · `selftest` · `inject` · `golden_trace` ·
`check` · `assert` · `expect`.

---

## A.4 Parameter block grammar and legal ranges

```
param_block  ::= "[" , param , { "," , param } , "]"
param        ::= key , "=" , value
key          ::= any key tabulated below
value        ::= number | region_value | symbol | "[" value { "," value } "]"
region_value ::= "cutoff" | "active" | "saturation" | "breakdown"
symbol       ::= identifier          (* an unquoted enumerated value *)
```

| Key | On | Legal range | Default |
|---|---|---|---|
| `β` (`beta`) | CJT, feedback, via | finite, ≥ 0; <1 attenuates, =1 unity, >1 amplifies | 1.0 |
| `sat` | CJT | (0, 1] | 0.95 |
| `cutoff` | CJT | [0, 1), and `cutoff < sat` | 0.1 |
| `region` | CJT | `cutoff` \| `active` \| `saturation` \| `breakdown` | `active` |
| `g_m`, `rπ` | CJT | ≥ 0 | model |
| `R` | Resistor, Thermistor | ≥ 0 | — |
| `C` | Capacitor | ≥ 0 | — |
| `leakage` | Capacitor | [0, 1] per stated period | 0 |
| `L` | Inductor | ≥ 0 | — |
| `tau` | filters, RC and L/R networks | > 0, in stated time units | — |
| `Vf`, `V_BR`, `I_R` | Diode, Zener | > 0 | — |
| `breakdown` | Zener | [0, 1] | — |
| `ratio`, `n` | Transformer | > 0 | — |
| `knee`, `coeff` (Thermistor), `f0`, `Q` (Notch) | as named | > 0 | — |
| `threshold` | Fuse, Monitor | [0, 1] unless the guarded quantity is unnormalised | — |
| `action` | Fuse | `permanent_block` \| `permanent_until_manual_reset` \| `block_until_decomposed` \| `defer_decision` \| `open_feedback` \| `warn` | — |
| `type` | Thermistor, Filter | `PTC` \| `NTC` \| `lowpass` \| `notch` \| `quantize` | — |
| `period`, `frequency`, `duty` | Oscillator | period, frequency > 0; duty ∈ (0, 1] | — |
| `from`, `to`, `dt` | Ramp | `dt` > 0 | — |
| `limit`, `window`, `grid`, `duration`, `max` | Monitor, Integrator, Filter, Hold, Limiter | > 0; an interval `[lo, hi]` must be ordered | — |
| `target_state`, `tolerance` | Regulator | state literal; tolerance ∈ (0, 1) | — |
| `open_loop_gain`, `non_inverting`, `inverting`, `output` | OpAmp | gain > 0; the rest are refs | — |
| `inputs`, `outputs`, `select` | MUX, DEMUX | non-empty list; symbol | — |
| `dial` | `dial` statement | integer 3–9 inclusive | — |
| `enforce` | `sequence` | `strict` | — |

`region` declares intent; if the numbers contradict it — `region=active` with
`cutoff ≥ sat` — the compiler flags the contradiction rather than guessing. A
reduced block (`[β=…]` alone) is the common case; the rest take defaults.

---

## A.5 Operator precedence

Tightest binding first. Above the gap is literal formation; below it,
composition.

| Prec. | Operator | Reads as | Associativity |
|---|---|---|---|
| 1 | `^` `_label` `_{ }` `\|` `⟨…⟩` | state-literal construction | n/a — tokenised whole |
| 2 | `< >` `( )` `[ ]` | argument list, grouping, parameter block | n/a |
| 3 | `×` | intensifies through / fuses into | non-associative; needs a named result |
| 4 | `+` | associates with | associative, commutative |
| 5 | `->` `=>` | flows into | **binary, not chained** |
| 6 | `=` | binds | right |

Rules that bite:

- **`×` requires a named emergent result.** `^3^P|A × ^3^P|f × ^3^P|T` alone is
  invalid. Write `^3^P|A + ^3^P|f + ^3^P|T` for three separately-defeasible
  co-present guards, `^3^P|⟨A,f,T⟩` for one state in three registers with no
  interaction claimed, or `integrate g: ( … ) = ^3^P|Ω;` if you mean fusion.
  Three architectures, three failure profiles (Ch. 2, §2.6).
- **`×` may not ascend the domain order.** P ≻ C ≻ E ≻ O. `^O × ^P` is invalid,
  as is any integration whose result outranks its operands.
- **`->` is binary.** `a -> b -> c` is not an expression; the one place a chained
  arrow is legal is `sequence`, a statement.
- Read `+` as "associates with" and `×` as "intensifies through." If the sentence
  survives, the operator is right.

---

## A.6 Validation rules

The passes, in the order they are designed to run.

| # | Pass | Checks | Emits |
|---|---|---|---|
| 1 | Lexical | literals, numbers, terminators well-formed | tokenizer error, no code |
| 2 | Kind agreement | prefix matches the type it introduces | `E-DECL-002` |
| 3 | Admissibility | every connection is a legal (source, target) pair | `E-CJT-001` |
| 4 | Bias-domain coherence | bias at or above the cause in P ≻ C ≻ E ≻ O | `E-CJT-002`, `E-CJT-008` |
| 5 | Parameter range | each key against §A.4; `cutoff < sat`; β finite | `E-CJT-003`, `E-CJT-005` |
| 6 | Gain divergence | round-trip loop gain < 1 on every loop | `E-CJT-005` |
| 7 | Cascade admissibility | each effect admissible as the next cause; depth counted | `W-CJT-007` |
| 8 | Push-pull balance | involutions within the four-point limit (Ch. 25, §25.2) | `W-CJT-004`, `W-CJT-006` |

Pass 4 is the load-bearing one. A *lower* domain biasing a *higher* one — an
Operational state biasing a Principled guard — is the prompt-injection
signature, and on a well-drawn board that connection is simply absent.

---

## A.7 Error codes

`E-` refuses validation. `W-` validates and flags.

| Code | Name | Sev. | Trigger | Fix |
|---|---|---|---|---|
| `E-DECL-002` | KindMismatch | error | prefix and type disagree | correct one of the two |
| `E-CJT-001` | MissingBias | error | a CJT with no bias — nothing governs the transition | wire a bias node, typically a `^5` substrate |
| `E-CJT-002` | InvalidBiasDomain | error | bias sits in a domain illegal for this cause | move it to a domain at or above the cause |
| `E-CJT-003` | CjtCutoff | error | bias below `cutoff`; β ≈ 0, so the stage never fires — a dead guard | raise the bias, lower `cutoff`, or fix the stage starving it |
| `W-CJT-004` | CjtSaturation | warning | effect pinned at `sat`; more cause does nothing | often intended (Ch. 24, §24.2); if not, raise series `R` |
| `E-CJT-005` | GainDivergence | error | a β large enough that a loop amplifies without bound | drop loop β into the 0.05–0.3 band |
| `W-CJT-006` | CjtShortCircuit | warning | cause and effect collapse to one state; the stage does no work | remove it, or re-type the transition |
| `W-CJT-007` | CjtCascadeDepth | warning | too many CJTs in series; signal degrades | shorten the cascade or buffer it |
| `E-CJT-008` | CjtCrossDomainBias | error | a bias or via crosses domains illegally — the prompt-injection signature | route influence downward; confine upward paths to low-gain O→P feedback |

`E-CJT-001` and `E-CJT-008` are the two safety codes named throughout Part IV.
They are what "enforced structurally rather than hoped-for" means: a guard with
no charter will not validate, and neither will a prompt that can edit the
principle.




# Appendix G — The Quantitative Table Template

Three blank forms, meant to be photocopied. Punch the left margin and file by
operation number rather than by date — one operation can run four months, and its
sheets belong together.

An operation you did not log did not produce data. It produced an impression, and
an impression is not something you can read three weeks later and disagree with.

---

### I.1 Which form, when

| Form | Opened | Written in | Answers |
|---|---|---|---|
| **1 — Operation Log** | Before the first session; one sheet per operation | Once at setup, then one row per session | What did I build, and what did it read? |
| **2 — Confirmation Log** | With Form 1 | One block per confirmation | How far did the signal actually get? |
| **3 — Parameter-Change Log** | With Form 1 | One block per change; verdict later | Which change caused which result? |

Form 3 governs the other two. Any reading taken after an unlogged change is
uninterpretable, and the honest thing to do with an uninterpretable reading is
strike it.

---

### I.2 Page geometry

- 58 monospace columns — about 9 pt in a 6×9 text block. Nothing here is wider,
  so nothing reflows on a photocopier set to 100 percent.
- Form 1 is one page per operation. Forms 2 and 3 repeat their block; run them
  onto as many sheets as the operation needs.
- Ink, not pencil. Corrections are struck through and initialled, never erased.
  The crossed-out number is often the interesting one.

---

### I.3 Form 1 — Operation Log

```
┌────────────────────────────────────────────────────────┐
│ OPERATION LOG                        sheet ___ of ___  │
├────────────────────────────────────────────────────────┤
│ Op # ______   Operator ______________________________  │
│ Board CCB-________  CCDL rev ______  Opened __/__/__   │
│                                                        │
│ Prime desire (A0-authenticated, present tense)         │
│ ______________________________________________________ │
│ ______________________________________________________ │
│                                                        │
│ Target:  self ____    consenting other ____            │
│ (there is no third box; Chapter 26.2)                  │
├────────────────────────────────────────────────────────┤
│ PARAMETERS AS SET                                      │
│ Dial(^2) ____  Dial(^3) ____  divergence ____  (<=4)   │
│ Dial(^5) ____  Dial(^6) ____  divergence ____  (<=4)   │
│ Dial(^8) ____  Dial(^9) ____  divergence ____  (<=4)   │
│ k ______   beta ______   sat ______                    │
│ r_pi ______  g_m ______   region  act / sat / cutoff   │
│ R_op:  R_cap ____ R_policy ____ R_ctx ____ R_res ____  │
├────────────────────────────────────────────────────────┤
│ RPM GATE (Ch 21)     pass/fail + the deciding number   │
│ A0 ____  ___________________________________________   │
│ D  ____  I_attention ________ vs cutoff ________       │
│ W  ____  ___________________________________________   │
│ P  ____  ___________________________________________   │
│ CSB  ____  refusal level ______   fuse intact ____     │
├────────────────────────────────────────────────────────┤
│ SESSIONS                                               │
│ S# │  Date  │t_op│^1│ TP1 │ TP2 │ TP3 │ TP4 │ Note     │
│ __ │________│____│__│_____│_____│_____│_____│_______   │
│ __ │________│____│__│_____│_____│_____│_____│_______   │
│ __ │________│____│__│_____│_____│_____│_____│_______   │
│ __ │________│____│__│_____│_____│_____│_____│_______   │
│ __ │________│____│__│_____│_____│_____│_____│_______   │
│ __ │________│____│__│_____│_____│_____│_____│_______   │
├────────────────────────────────────────────────────────┤
│ ST. JOHN'S (first confirmation only)                   │
│ t_op ______  t_conf ______   eta = ____ / ____         │
│ eta x 1/3 = ____ / ____    a ______    b ______        │
│ A = b ______   n_ops = a ______   T = a x t_op ______  │
├────────────────────────────────────────────────────────┤
│ CLOSED __/__/__   outcome:  manifest / abandoned /     │
│                   fuse blown / superseded by op ______ │
└────────────────────────────────────────────────────────┘
```

**Field notes.**

| Field | What goes in it | What does not |
|---|---|---|
| Prime desire | The A0-authenticated desire (Chapter 21.1) | The desire you walked in with, if the audit changed it |
| Board / rev | The CCDL revision you actually fired | The one you meant to fire |
| Dials | Both members of every pair, plus the divergence — the limit is 4 points (Chapter 25.2) | One dial with its involution partner left blank |
| CJT | β, sat, rπ, g_m as set (Chapter 3.3) | β alone. sat is what pins your readings |
| Gates | Pass or fail per gate **and the number that decided it** (Chapters 21.2–21.4) | A tick |
| Sessions | Readings taken at TP1–TP4 (Chapter 12.3); `^1` Mind graded 3°/2°/1° (Chapter 5.5) | Readings reconstructed later from the outcome |
| A | The required multiple of delivered activation at TP4 (Chapter 13.5) | A β setting. They are different quantities |

**Worked example — one session row filled.** From the Red Corvette operation of
Chapter 13.6, first session:

```
│ 01 │03/14/26│ 20 │2°│0.62 │0.18 │0.80!│0.084│TP3 pin   │
```

The `!` is the operator's own flag: TP3 sat exactly at `sat = 0.80` and did not
move when the cause improved. Mark pinning in the row the moment you see it.
That one character is what makes the next form's entry obvious.

---

### I.4 Form 2 — Confirmation Log

```
┌────────────────────────────────────────────────────────┐
│ CONFIRMATION LOG            Op # ______   sheet ____   │
├────────────────────────────────────────────────────────┤
│ C-____   Date __/__/__   Time ____:____                │
│ t_conf ________ min from end of operation              │
│ Grade    1°    2°    3°          (Chapter 5.6)         │
│ First confirmation for this operation?    Y / N        │
│ What happened ________________________________________ │
│ ______________________________________________________ │
│ Could this be coincidence?    Y / N / unsure           │
│ Recorded within ______ min of noticing it              │
├────────────────────────────────────────────────────────┤
│ C-____   Date __/__/__   Time ____:____                │
│ t_conf ________ min from end of operation              │
│ Grade    1°    2°    3°          (Chapter 5.6)         │
│ First confirmation for this operation?    Y / N        │
│ What happened ________________________________________ │
│ ______________________________________________________ │
│ Could this be coincidence?    Y / N / unsure           │
│ Recorded within ______ min of noticing it              │
└────────────────────────────────────────────────────────┘
```

Rules, in the order they get broken:

1. **Only the first confirmation enters St. John's Equation.** `t_conf` runs from
   the end of the operation to the first confirmation, in minutes. Later ones
   stay on the sheet as `^4` Vibration evidence; they do not re-enter the ratio.
2. **Grade at the time, not afterwards.** A 3° confirmation graded a week later,
   once the outcome is known, grades 1°.
3. **The coincidence line is not humility, it is data.** Write what you actually
   thought at the moment. An operator whose logs never contain the word "unsure"
   has stopped logging and started narrating.
4. **A confirmation is not a manifestation.** It says the signal reached the
   Ether, not that it reached the target (Chapter 5.6).

**Worked example — one block filled.**

```
│ C-001   Date 03/14/26   Time 21:40                     │
│ t_conf 60 min from end of operation                    │
│ Grade    1°   (2°)   3°          (Chapter 5.6)         │
│ First confirmation for this operation?   (Y) / N       │
│ What happened  the song came on the radio, unbidden,   │
│ in the car, forty minutes into an errand               │
│ Could this be coincidence?   Y / N / (unsure)          │
│ Recorded within 15 min of noticing it                  │
```

η = 20 / 60 = 1/3; × 1/3 = 1/9; a = 1, b = 9. Carry that arithmetic onto Form 1
so the result and its inputs can never be separated later.

---

### I.5 Form 3 — Parameter-Change Log

The form that earns its page. An operator who moves two parameters and gets a
better reading has bought a better reading and learned nothing.

```
┌────────────────────────────────────────────────────────┐
│ PARAMETER-CHANGE LOG        Op # ______   sheet ____   │
├────────────────────────────────────────────────────────┤
│ CH-____  Date __/__/__  Takes effect at session ____   │
│ Parameter ___________________  from ______ to ______   │
│ Why (one line) _______________________________________ │
│ Prediction: TP____ moves   up / down / off ceiling     │
│    to about ______ by session ______                   │
│ Anything else changed this cycle?    No / Yes >>       │
│    >> if Yes, write CONFOUNDED here _______________    │
│ Observed ______ at session ______ on __/__/__          │
│ Verdict     KEEP  /  REVERT  /  INCONCLUSIVE           │
├────────────────────────────────────────────────────────┤
│ CH-____  Date __/__/__  Takes effect at session ____   │
│ Parameter ___________________  from ______ to ______   │
│ Why (one line) _______________________________________ │
│ Prediction: TP____ moves   up / down / off ceiling     │
│    to about ______ by session ______                   │
│ Anything else changed this cycle?    No / Yes >>       │
│    >> if Yes, write CONFOUNDED here _______________    │
│ Observed ______ at session ______ on __/__/__          │
│ Verdict     KEEP  /  REVERT  /  INCONCLUSIVE           │
└────────────────────────────────────────────────────────┘
```

**The six rules.**

1. **One parameter per block.** Change two and the block is written off: mark it
   CONFOUNDED and claim nothing from it, including the parts you liked.
2. **Prediction before the operation, never after.** A named test point and a
   direction — *TP3 comes off the ceiling* — is a prediction. *It should improve
   things* is not.
3. **Verdict only after a full cycle**: one operation and its first confirmation.
   Anything sooner is a guess wearing a verdict's clothes.
4. **A revert is a change.** It gets its own block and its own prediction.
5. **Never overwrite a prediction that turned out wrong.** Strike it, initial it,
   leave both readable. Wrong predictions are how you learn the board.
6. **Your own condition is a parameter you did not set.** Sleep, illness,
   upheaval at work — these move the bias rail whether or not you consent. Note
   them; do not call a cycle clean when it was not.

**Worked example — one block filled.** The second operation of Chapter 13.6:

```
│ CH-002  Date 03/21/26  Takes effect at session 01      │
│ Parameter  Q2 beta            from  3.0  to  2.50      │
│ Why  TP3 pinned at sat=0.80; the reading is the clamp, │
│      not the board                                     │
│ Prediction: TP3 moves   up / down / (off ceiling)      │
│    to about 0.76 by session 01                         │
│ Anything else changed this cycle?   (No) / Yes >>      │
│ Observed 0.76 at session 01 on 03/21/26                │
│ Verdict    (KEEP)  /  REVERT  /  INCONCLUSIVE          │
```

That block is readable because nothing else moved. Contrast the third operation
in the same chapter, which moved four levers at once — clarity at TP1, both
dials, β, and the `R_op` terms — and delivered 3.10× at TP4. The log cannot
apportion that gain. The chapter apportions it arithmetically, decomposing the
product into its factors, and that works only because each factor is separately
computable. Where the arithmetic will not decompose, a four-lever change hands
you a number and no account of where it came from.

---

### I.6 Filling conventions

| Mark | Meaning |
|---|---|
| Blank cell | Not measured |
| `—` | Measured, and the reading was zero |
| `!` after a reading | Pinned or clamped; suspect everything downstream |
| `?` after a reading | Taken, but not trusted |
| Struck through, initialled | Corrected; both values stay readable |
| `CONFOUNDED` | Two or more changes in one cycle; nothing may be concluded |

---

### I.7 What the logs feed

- **Chapter 22.5**, trend reading, needs at least three operations at comparable
  settings before a movement in η means anything. Form 3 is the only record of
  which operations were comparable.
- **Chapter 24**'s safety review is read straight off these sheets. The question
  that matters most — any blown fuses, and why — is answerable only if the why
  was written down at the time it blew (Chapter 24.3).
- **Chapter 24.5**'s ethical-drift filter takes the operations log as its literal
  input: `Filter< input=^9_operations_log^O, type=lowpass, τ=ethical_drift_τ >`.
  The sheet is not paperwork about the circuit. It is the node the one lawful
  feedback path reads from, and an operator who keeps no sheet has left an input
  on their safety board unconnected.

Keep the sheets until one full ethical-drift τ has elapsed past the last entry
(Chapter 24.5). Then keep them anyway. The operator you will argue with in two
years is yourself, and these pages are the only witness either of you will have.




# Appendix I — Glossary

Every term this book uses that a reader might arrive at cold. Entries are
alphabetical, each is self-contained, and each ends with where the term is
actually developed. Symbols and Greek letters are collected first, because they
have no alphabetical home.

Where a term already means something in ordinary English, or in electronics, and
this book means something different by it, the entry says so in bold. Those are
the entries most worth reading before you need them.

---

## False friends — check these first

| Term | What it usually means | What it means here |
|---|---|---|
| `^3` Negative | bad, harmful, critical | **visceral aversion only** — can't-stomach-it. Analytical critique is `^6` Male |
| `^8` Above/Cause | logical cause, "therefore" | **associative triggering only** — "that reminds me" |
| `^5` Female / `^6` Male | gender | composition. `^5` = what a Mind is made of; `^6` = what an Idea is made of |
| Saturation | a fault, a clipped signal | often **the goal** — a stage that has stopped responding to input |
| Negative feedback | discouragement | output subtracted from input; the stabilising kind |
| Gnosis | mystical knowledge | a measurable bias-collapse state with three graded degrees |
| Hyperstition | a hoax or a lie | a fiction that makes itself true by being acted on |
| τ | one thing | **two** — the RC/LR time constant, and the 1/3 constant in St. John's Equation |
| Dropout | quitting, or a dropped connection | the margin below which a stage stops regulating at all |
| Inversion | any reversal | a specific polarity flip along one of the named axes |

---

## Symbols

**β (beta)** — Current gain of a Cognitive Junction Transistor: how much effect the stage produces per unit of cause. β < 1 attenuates, β = 1 passes, β > 1 amplifies. *Chapters 3.3, 10.1.*

**β=∞** — An idealization, never a value. A validator rejects non-finite parameters; a real build commits to a large finite gain and says so. *Chapters 10.1, 23.2.*

**g_m (transconductance)** — How much the output moves for a given change at the bias terminal. High g_m is why rewording a question changes the answer. *Chapters 3.3, 10.3.*

**rπ (r-pi)** — Input resistance at the bias terminal: how hard it is to move someone's frame at all. High rπ reads as stubbornness; rπ → 0 is the idealized gnosis state. *Chapters 3.3, 10.4, 17.1.*

**τ (tau)** — **Two distinct uses; do not conflate them.** (1) The time constant of an RC or L/R circuit — one τ reaches 63% of final value, 3τ is practically complete. (2) The 1/3 constant in St. John's Equation, one part work to two parts gestation. *Chapters 7.2, 9.2 for the first; 5.2, 23.1 for the second.*

**η (eta)** — The operation-to-confirmation ratio, `η = t_op / t_conf`. The single number the Quantitative Table is built to produce. *Chapters 5.3, 22.5, 23.1.*

**Ω_c, V_c, A_c, F_c, h·Ω_c** — Cognitive ohms, volts, amperes, farads, and the inductance unit. Scaled analogues, not electrical measurements, and the book never pretends otherwise. *Chapters 4.2, 7.1, 9.2.*

**`^n^D_{Fk}|R`** — The state literal: Noetic, Domain, Drive, Register. Register optional. Read `^3^P_{F7}|T` as principled visceral aversion, purpose-driven, transcendent register. *Chapter 2.1.*

**`|`** — Introduces the Register and nothing else. `F3|Vitality` is a syntax error, not an annotation. *Chapter 2.5.*

**`+` / `×` / `|⟨…⟩`** — Co-presence (terms stay distinct) / genuine integration (requires a named emergent result) / register-set occupancy (no operational claim). *Chapter 2.6.*

---

## A

**A0 (Pure Desire)** — The root of the RPM chain and the first gate: is this authentically what *you* want, or a sub-desire wearing the prime desire's clothes. Most failed operations failed here and were run anyway. *Chapter 21.1.*

**Active region** — The CJT operating region where output tracks input proportionally. The only region in which a gain figure means anything. *Chapter 3.4.*

**Amplification** — Producing more effect than the cause alone would carry, by spending bias. Not creation; the cause must already be present. *Chapters 3.2, 10.1.*

**Assembly drawing** — The board layout figure: physical arrangement, test-point callouts, and a bill of materials box. Distinct from the schematic, which shows connection rather than placement. *Chapter 12.1.*

---

## B

**Back-EMF** — The voltage a coil generates when the current through it is interrupted, opposing the change. Cognitively: the distress produced by stopping an established practice. **It scales inversely with how fast you stop** — the same removal produces thousands of times the kick when done abruptly. The distress is generated by the rate, not stored up and released. *Chapter 9.2.*

**Bias** — The reference held at the middle terminal of a CJT, which decides how much of a cause reaches its effect. **Not "prejudice."** Willpower, framing, conditioning, and persuasion are all operations on somebody's bias terminal. *Chapters 3.2, 10.4.*

**Block diagram** — The stage-level view: signal path left to right, boxes labelled by function, no component values. The first thing to read in any board chapter. *Chapter 12.1.*

**Bill of materials (BOM)** — The parts list for a board: every component, its designator, its parameter values. If a component is not on the BOM it is not on the board, whatever the prose implies. *Chapter 12.1.*

**Breakdown** — Operation past the reverse-voltage limit of a junction, after which it no longer blocks. Non-recovering. *Chapters 3.4, 7.4.*

---

## C

**Capacitor, cognitive** — A `^5` Female store: accumulated experience held as charge, charging on an RC curve and leaking when not fed. *Chapters 7.1, 7.2.*

**Cascade** — Two or more CJTs in series, gains multiplying. Also multiplies every error and every offset. *Chapters 10.5, 15.2.*

**CAS** — Cognitive Architecture System. The formal notation: 10 Noetics, 4 Domains, 7 Drives, 4 Registers. *Chapters 1.3, 2.1.*

**CAS-Ohm's Law** — `V_drive = I_attention × R_constraint`. Drive across a constraint produces attention flow. *Chapter 4.2.*

**CCB** — Cognitive Circuit Board. A complete, named board with requirements, schematic, bill of materials, and test points. *Chapter 12.1.*

**CCDL** — The Cognitive Circuit Description Language: the circuit written as text. Every listing in this book is one a validator would accept. *Chapter 12.1; full grammar in the CCDL Language Reference appendix.*

**CJT (Cognitive Junction Transistor)** — Three terminals: Cause (collector), Bias (base), Effect (emitter). The claim the whole book rests on, and the part in every board. *Chapters 3.2, 10.*

**Cognitive Safety Board (CSB)** — The operator's own safety board: a saturated refusal stage, an enforcement fuse, the domain diode chain, and a filtered feedback path. Built before anything ambitious is run, not after. *Chapter 24.*

**Common-mode rejection** — An op-amp amplifies the *difference* between its two inputs and ideally ignores whatever is common to both. Cognitively: a comparison stage should respond to how two Ideas differ, not to the framing, source, or delivery they share. Poor rejection is why identical proposals get different verdicts depending on who tabled them. *Chapter 11.4; see also g_m, Chapter 10.3.*

**Consent architecture** — A circuit whose target has agreed to it, built so the agreement is structural rather than assumed. *Chapter 26.2.*

**Counter-circuit** — The reversal or detection board that every coercive board in this catalogue ends with, at equal or greater depth. *Chapters 16.7, 19.6.*

**Cutoff** — The CJT region where insufficient bias means no current crosses at all. The part is undamaged and completely inert. *Chapter 3.4.*

---

## D

**Decoupling** — Deliberately isolating one node from another's fluctuations so a reference stops tracking a result. In CCB-SELF it is what keeps a bad day from rewriting an identity. *Chapter 20.2.*

**Deprogramming Board (CCB-DP)** — The reversal circuit for conditioning architecture, and the terminal section of Chapter 16. *Chapter 16.7.*

**DETECTION-ONLY SCHEMATIC — DO NOT BUILD** — The banner carried by any circuit whose purpose is to act on a non-consenting person. Drawn so you can recognise one. *Chapter 12.2.*

**Dial** — An operator-set integer from 3 to 9 controlling a dial-adjusted resistor. Involution partners may not diverge by more than 4 points. *Chapters 6.2, 25.2.*

**Dielectric breakdown** — A capacitor stressed past what its insulation holds. The `^5` analogue of a store that fractures rather than saturates. **No medical or psychiatric claim is made or implied; if this describes you, see a clinician.** *Chapter 7.4.*

**Diode, domain** — A one-way junction enforcing descent P → C → E → O. *Chapters 8.1, 24.4.*

**Domain** — Which ontological level an operation runs at: **P** Principled, **C** Cognitive, **E** Evaluative, **O** Operational. Total order P ≻ C ≻ E ≻ O. *Chapter 2.3.*

**Domain ascent** — Movement up the precedence order. Blocked, with one lawful exception. `^O × ^P` is invalid notation. *Chapter 8.3.*

**Domain descent** — The lawful direction of translation, P → C → E → O, one junction at a time. *Chapter 8.1.*

**Drive** — Which motivational architecture is running: **F1** Unity, **F2** Wisdom, **F3** Vitality, **F4** Connection, **F5** Agency, **F6** Structure, **F7** Purpose. Inversion pairs F1↔F7, F2↔F6, F3↔F5; F4 is self-dual. *Chapter 2.4.*

**Dropout** — In a regulator, the minimum input-to-output margin below which regulation is simply lost and the output follows the input down. Here: `V_drive` below the summed forward drops of the domain chain, at which point no principle produces any act — not weakly, but not at all. **Reads as weakness; is arithmetic.** *Chapters 4.2, 8.2.*

**Duty cycle** — The fraction of a period an oscillator spends active. *Chapter 11.2.*

---

## E

**Egregore** — A `^5` store held collectively rather than by one Mind: a capacitor network, charged and maintained by repeated collective exposure. **No claim of an independent entity is made.** *Chapters 7.5, 14.6.*

**Emergent result** — The named output that `×` requires. Integration without a named result is invalid notation; use `+` or `|⟨…⟩`. *Chapter 2.6.*

---

## F

**Failure mode** — A row in every chapter's failure table: the mode, its mechanism, what you observe at the bench, and the fix. *Chapter 12.1.*

**Feedback, positive** — Output returned to the bias terminal so each cycle raises the next. Above unity gain it runs away — which is the operating principle of hyperstition and the hazard of everything else. *Chapters 14.2, 14.5.*

**Filter** — Lowpass passes slow trends and blocks transients; highpass does the reverse; notch rejects one band. *Chapters 11.3, 24.5.*

**Flyback path** — The alternate route a coil's collapsing current takes so it does not arc. Cognitively: the substitute practice. **It must already be conducting before the old path opens** — installed after, it is a diode that watched the arc. *Chapter 9.2.*

**Forward voltage (Vf)** — The threshold a junction must be driven past before it conducts. **Not overhead to engineer away — it is the boundary itself.** A junction at Vf = 0 is a wire, and two domains joined by a wire are one domain wearing two labels. *Chapter 8.2.*

**Fuse** — Permanent path interruption once a threshold is crossed. Does not suggest; opens. *Chapters 11.1, 24.3.*

---

## G

**Gate (D, W, P)** — The three prerequisite checks after A0: sufficient drive, possession of the schematic, capacity to execute. *Chapters 21.2–21.4.*

**Gnosis** — The bias-collapse state, `rπ` driven toward its floor, in which suggestion meets little resistance. **Not mystical attainment**; it is graded in three degrees and logged like any other reading. *Chapters 17.1, 22.1.*

---

## H

**Hyperstition** — A fiction that becomes true through being acted on. **Not a lie**: a lie requires the liar to know better, whereas a hyperstition's truth condition is created by belief propagating through collective `^5`. *Chapter 14.*

**Hundredth Monkey Effect** — The folk claim that a belief propagates spontaneously past a headcount. Treated here as collective CJT saturation rather than as a documented phenomenon, and the distinction is stated in the section itself. *Chapter 14.4.*

**Hysteresis** — Two thresholds instead of one, so a gate turns on and off at different points. Without it a comparator sitting near its threshold chatters. With it, the chatter becomes a computable maintenance interval nobody had to choose. *Chapter 20.4.*

---

## I

**Impedance matching** — Sizing a transfer so signal actually crosses between two minds rather than reflecting. *Chapters 9.3, 11.5.*

**Induction coupling** — Belief transferred between minds by proximity and shared cadence rather than by argument. *Chapter 9.3.*

**Inversion** — A structural polarity flip along one of the named axes — a circuit producing the opposite of what it was built for while appearing to run normally. Distinct from failure: an inverted board is working, backwards. *Chapters 19.4, 25.3.*

**Involution pair** — Two Noetics that are one structure seen from two sides: `^2`↔`^3`, `^5`↔`^6`, `^8`↔`^9`. Self-dual: `^0`, `^1`, `^4`, `^7`. **A pair cannot be flipped directly** — reorienting a structure means taking it apart first, which is `^6` Male's job. *Chapters 25.1, 15.1.*

---

## L

**Lacunarity** — An absence: a prerequisite that is not there. Distinct from leakage (present, producing the wrong output) and from inversion (present, running with reversed polarity). The distinction decides which repair applies. *Chapters 21.1, 23.3.*

**Leakage** — Charge lost from a `^5` store that is not being fed. The reason an operation left alone decays on a schedule you can compute. *Chapter 7.3.*

---

## M

**MK-Ultra** — A declassified and documented programme. This book analyses what is on the record, structurally, so a reader can recognise the architecture. It supplies no protocol. *Chapter 16.1.*

**"Must Not" list** — The safety invariants written before any functional requirement, because a requirement can be traded and an invariant cannot. *Chapter 12.2.*

---

## N

**Noetic** — Which structural dynamic is operating. The ten, verbatim:

| | Name | Definition |
|---|---|---|
| `^0` | Idea | All things in and outside the Mind. |
| `^1` | Mind | Various degrees of awareness that processes, stores, outputs, and intakes Ideas. |
| `^2` | Positive | An Idea the Mind has an affinity for and is attracted toward. |
| `^3` | Negative | An Idea the Mind is adverse to and repelled by. |
| `^4` | Vibration | The degree to which an Idea resonates with the Mind, its impression. |
| `^5` | Female | A Mind impregnated with an Idea, the Ideas a Mind is composed of. |
| `^6` | Male | An Idea impregnated with another Idea, the Ideas an Idea is composed of. |
| `^7` | Rhythm | The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it. |
| `^8` | Above/Cause | An Idea that triggers a different Idea than itself to come to Mind. |
| `^9` | Below/Effect | The Idea brought to Mind by an Above/Cause trigger. |

Never renamed to their function. *Chapter 2.2.*

---

## O

**Op-amp** — Very high differential gain: amplifies the difference between two inputs. The precision comparison part. *Chapter 11.4.*

**Operator's Oath** — A commitment written so that it can be enforced by the circuit rather than remembered by the operator. *Chapter 26.4; text in the T.O.O.T.R.A. Oath appendix.*

**Oscillator** — Sustained periodic output. The `^7` Rhythm component: what keeps a practice, a campaign, or an egregore fed. *Chapters 11.2, 20.4.*

**Overton window** — The band of positions a population currently treats as sayable. This book models its movement as six resistance bands and a five-stage cascade, with `^6` Male decomposition as the hinge between aversion and attraction. **The window is a property of a collective `^5`; where no aggregate exists, there is no window to move.** *Chapters 15.1, 15.6.*

---

## P

**PTC / NTC thermistor** — Resistance that rises with cognitive temperature (PTC — tighter constraint as stakes rise) or falls with it (NTC — guard relaxing as danger increases, and a danger sign wherever you find it). *Chapters 6.3, 15.2.*

---

## Q

**Quantitative Table** — The tracking sheet: `^1` Mind depth, `^4` Vibration and its timing, `^7` Rhythm, and the ratio they produce. It is where an operation stops being a feeling and becomes data you can look at three weeks later. *Chapters 5.5, 22.4; blank sheet in the Quantitative Table Template appendix.*

---

## R

**Register** — Which operational character a state runs in: `|T` Transcendent, `|A` Analytical, `|f` Affective, `|E` Embodied. Orthogonal to Noetic, Domain, and Drive; optional in notation. *Chapter 2.5.*

**Resistance, cognitive (R_constraint)** — What limits attention flow at a given drive. Sourced from capability, policy, context, and resources. *Chapters 4.2, 4.4.*

**RPM chain** — The prerequisite ladder A0 → D → W → P → outcome. Each stage must be satisfied before the next is reachable, and satisfaction is **one-directional**. *Chapters 21.1–21.5.*

---

## S

**Saturation** — The ceiling past which more input produces no more output. **Usually a virtue here, not a fault:** a refusal that saturates early is a refusal that has stopped responding to argument. It is a defect only where a reading must track its input. *Chapters 3.4, 10.2, 24.2.*

**Schmitt trigger** — A comparator with hysteresis built in. The auto-gate part. *Chapter 20.4.*

**Section-retraction** — The formal statement of one-directionality: realization after embedding returns you to the start, but re-embedding after realization does not. Practically — you cannot un-cast. *Chapter 21.5.*

**Shadow integration** — Making an inverted or disowned structure work for the operator rather than against them, by routing it rather than suppressing it. *Chapter 25.4.*

**Slew** — Rate of change at a node, and the thing a slew fuse limits. A reference that can be moved quickly is not a reference. *Chapter 20.5.*

**St. John's Equation** — The calibration relation built from operation time and confirmation time, yielding the gain requirement for the next operation and an estimate of how many remain. **An instrument on an uncalibrated scale** — informative about direction and magnitude, not about truth. *Chapters 5.3, 23.1; blank sheet in the St. John's Equation Worksheet appendix.*

---

## T

**Test point (TP1–TP4)** — The four standard probes on every board: what each reads and its expected range. Read them in the order the chapter specifies, which puts the silent failures first. *Chapter 12.3.*

**Sub-desire** — A smaller want standing in front of the prime one, and the usual reason a board runs correctly and delivers nothing. Resolved by `^6` Male decomposition at the gate, not by more gain. *Chapters 21.1, 23.3.*

**Time constant** — See **τ**. One τ reaches 63% of final value; 3τ is practically complete. It sets how long a substrate takes to shift, and pacing failures are almost always τ set in the wrong unit. *Chapters 7.2, 9.2.*

**TKS** — The Tootra Kabbalistic System: 40 Elements, 7 Foundations, 12 Prerequisites. The esoteric ancestor CAS formalises. *Chapter 1.3; full mapping in the TKS Crosswalk appendix.*

**Transformer** — Impedance matching between minds or domains, trading amplitude for reach. *Chapter 11.5.*

**Trigger installation** — The architecture by which a stimulus is bound to a response so that later exposure fires it. Analysed as mechanism, for recognition. **No procedure is supplied anywhere in this book.** *Chapter 16.3.*

---

## U

**Un-boarded, right to be** — The invariant that a person may have a circuit removed from them, and that no board may be built to defeat that removal. *Chapter 26.3.*

---

## W

**Willie Lynch letter** — A document of **disputed authorship**. The book analyses what the text specifies as a circuit and labels the provenance question plainly rather than resolving it. *Chapter 15.6.*

**Worked example** — Real numbers carried from input to output in every Part III chapter. Not a sketch. *Chapter 13.6.*

---

*Exercises are answered in full in the exercise-answers appendix. Formal
definitions underlying this glossary are in the Mathematical Foundations
appendix.*




# Appendix J — Further Reading

This list is short on purpose. Everything named exists, with author and title as
printed. Where the primary material is a government record rather than a book,
the entry describes the record instead.

Three rules. **Mechanism, not procedure** — no manual for acting on a
non-consenting person is listed; J.10 says which were left out. **Nothing
medical** — the hypnosis and conditioning entries are historical literature, not
treatment guidance. **Inclusion is not endorsement** — several are propaganda
handbooks by people who meant them, listed because the attacker's own account is
the fastest route to recognising the board.

---

## J.1 The companion volumes

All three from Noetic Compass Press.

| Volume | Owns | Go there when |
|---|---|---|
| *Thinking in Cognitive Architecture* | The CAS framework: 10 Noetics, 4 Domains, 7 Drives, 4 Registers | You want the derivation behind Chapter 2, the admissibility relations, every Noetic in full |
| *CAS PCBA Engineer* | The component library and five reference boards, in engineering depth | You need parameter ranges beyond Appendix C, or thirty pages on a component this book gives a paragraph |
| *Reality Engineering* | TKS — the 40 Elements, 7 Foundations, 12 Prerequisites | Appendix E's crosswalk raised a question about the Element grid it maps into |

---

## J.2 Electronics — the vocabulary this book borrowed

None of these are needed to build a board — only to judge whether Chapter 4's
isomorphism does real work.

| Work | Why |
|---|---|
| Paul Horowitz and Winfield Hill, *The Art of Electronics* | The standard bench reference; its transistor chapter shows which parts of Chapter 10's CJT are structural and which analogy |
| Forrest M. Mims III, *Getting Started in Electronics* | Hand-lettered and diagram-first — the fastest route to reading a schematic before Chapter 12 requires it |
| Adel S. Sedra and Kenneth C. Smith, *Microelectronic Circuits* | The formal treatment of β, g_m, and rπ that Chapter 3 compresses into one table |
| Michael Riordan and Lillian Hoddeson, *Crystal Fire* | The history behind Section 3.1 — what Bardeen, Brattain, and Shockley did in December 1947 |

---

## J.3 Cognitive science and cognitive architecture

| Work | Why |
|---|---|
| Herbert A. Simon, *The Sciences of the Artificial* | The founding argument that thinking systems are engineered objects with specifiable interfaces — this book's premise, stated fifty years earlier |
| Allen Newell, *Unified Theories of Cognition* | What a cognitive architecture must account for; the standard CAS should be measured against |
| Marvin Minsky, *The Society of Mind* | Mind as many interacting parts — the intuition behind Section 7.5's `^5` capacitor networks |
| Donald O. Hebb, *The Organization of Behavior* | Where repetition-strengthens-association comes from; the substrate under every `^7` Rhythm claim here |
| Judea Pearl and Dana Mackenzie, *The Book of Why* | The cleanest statement in print of association versus causation; read it and the `^8` anti-drift rule stops feeling pedantic |
| Norbert Wiener, *Cybernetics* | Feedback, gain, and stability in systems that include minds — background for Chapter 14's oscillator |
| W. Ross Ashby, *An Introduction to Cybernetics* | Requisite variety: why Chapter 24's safety board must be at least as rich as what it governs |
| George Lakoff and Mark Johnson, *Metaphors We Live By* | A standing warning: this book runs on a metaphor, and this is the book about what metaphors do to their users |

---

## J.4 Persuasion, propaganda, and advertising

Background for Chapters 15, 18, and 19.

| Work | Why |
|---|---|
| Robert B. Cialdini, *Influence: The Psychology of Persuasion* | The six-principle taxonomy every board in Chapter 18 rearranges; his *Pre-Suasion* covers the state a target is placed in beforehand — bias-terminal work |
| Richard E. Petty and John T. Cacioppo, *Communication and Persuasion* | The elaboration-likelihood model — central versus peripheral routes, the academic form of Section 17.6's `^6` filter bypass |
| Walter Lippmann, *Public Opinion* | The 1922 argument that people act on the picture in their heads, not the world; the origin of window movement |
| Edward Bernays, *Propaganda* | An attacker's own manual, written without embarrassment by a man who thought he was doing civic hygiene |
| Jacques Ellul, *Propaganda: The Formation of Men's Attitudes* | Propaganda as ambient condition rather than campaign — why Section 15.4 measures τ in months |
| Vance Packard, *The Hidden Persuaders* | Motivational research in 1950s advertising — the record of Section 18.2's insecurity injection working |
| Anthony Pratkanis and Elliot Aronson, *Age of Propaganda* | The best detection-side text here, and the closest thing in print to Chapter 19's counter-circuit |
| David Ogilvy, *Ogilvy on Advertising* | A practitioner stating his own gain settings; read beside Section 18.5 on A/B testing as β calibration |
| Byron Sharp, *How Brands Grow* | The empirical challenge to the rest — availability and repetition beat persuasion, a `^7` Rhythm claim with data |
| Stanley Milgram, *Obedience to Authority* | What a bias terminal held by someone else costs, from the man who ran it |
| Robert Jay Lifton, *Thought Reform and the Psychology of Totalism* | Interview study of coercive persuasion — the closest published work to Chapter 16's analysis, and far more careful |

**On the Overton window.** The concept is attributed to Joseph P. Overton of the
Mackinac Center for Public Policy and was described publicly by colleagues after
his death. There is no canonical monograph; Chapter 15 builds on the concept.

**On the Willie Lynch letter.** Its authenticity has been challenged since it
began circulating widely in the 1990s, and Section 15.6 treats it accordingly —
a document *about* an architecture, not evidence *of* a 1712 one.

---

## J.5 The intelligence programmes — background for Chapter 16

**The primary sources here are declassified United States government records,
not books.** That cuts both ways: the record is solid where it exists and absent
where files were destroyed. Four bodies of material matter.

| Record | What it is |
|---|---|
| **The Church Committee record** | Hearings and the multi-volume final report of the U.S. Senate Select Committee to Study Governmental Operations with Respect to Intelligence Activities, 1975–76 — sworn testimony on CIA behavioural-modification research |
| **The Rockefeller Commission report** | The 1975 report of the Commission on CIA Activities within the United States, produced in parallel with the Senate inquiry over overlapping ground |
| **The 1977 MKULTRA hearing** | A joint Senate hearing of August 1977 devoted specifically to Project MKULTRA, published as a transcript. It happened because records thought destroyed were located |
| **The surviving MKULTRA files** | Programme records were destroyed on the order of the then Director of Central Intelligence in 1973. Financial and administrative records held elsewhere survived and were released under the Freedom of Information Act — funding, front organisations, cover; not protocols |

These sit in U.S. government depository collections and the CIA's public FOIA
electronic reading room. Consult them directly; everything below interprets them.

| Secondary history | Why |
|---|---|
| John Marks, *The Search for the "Manchurian Candidate": The CIA and Mind Control* | Product of the FOIA request that surfaced the surviving files; still the standard account |
| Stephen Kinzer, *Poisoner in Chief* | Biography of Sidney Gottlieb, who ran the programme — the clearest narrative of how the money moved |
| Alfred W. McCoy, *A Question of Torture* | Traces the research line from Cold War laboratories into later interrogation doctrine, the institutional continuity Section 16.1 assumes |

---

## J.6 Hypnosis — background for Chapter 17

Historical and technical literature only. Neither is clinical guidance, and
neither should be used on another person.

| Work | Why |
|---|---|
| *The Collected Papers of Milton H. Erickson on Hypnosis*, edited by Ernest L. Rossi | Erickson's own case commentaries — the public record Section 17.6 analyses |
| Jay Haley, *Uncommon Therapy* | A structural reading of Erickson's method from outside, useful because Haley describes pattern rather than repeating anecdote |

---

## J.7 Self-programming and skill acquisition — Chapters 5 and 20

| Work | Why |
|---|---|
| Anders Ericsson and Robert Pool, *Peak* | The deliberate-practice research behind Section 5.2's ten-thousand-hour constant, with Ericsson's objections to how it is quoted |
| Charles Duhigg, *The Power of Habit* | Cue, routine, reward — the three-node loop Section 20.4 draws as an oscillator with auto-gating |
| Leon Festinger, *A Theory of Cognitive Dissonance* | What happens when a `^5` capacitor holds incompatible charge; background for the involution work in Chapter 25 |

---

## J.8 The hermetic lineage — Chapters 13 and 14

The Noetic names — Vibration, Rhythm, Above and Below — descend from a hermetic
tradition. Pretending otherwise would be dishonest.

| Work | Why |
|---|---|
| *The Kybalion*, by "Three Initiates" (1908) | The seven-principle formulation this vocabulary descends from; authorship is attributed rather than established — a starting point, not an authority |
| Peter J. Carroll, *Liber Null & Psychonaut* | Chaos magic's results-first, belief-as-tool posture — the closest existing practice to Chapter 13's register |
| Richard Dawkins, *The Selfish Gene* | The meme chapter, where self-replicating ideas were first put in those terms; ancestor of Chapter 14's engine |

---

## J.9 The mathematics — background for Appendix L

| Work | Why |
|---|---|
| F. William Lawvere and Stephen H. Schanuel, *Conceptual Mathematics* | Category theory from nothing, with pictures — the gentlest entry to Appendix L's axioms |
| Saunders Mac Lane, *Categories for the Working Mathematician* | The standard reference for machinery Appendix L cites a line at a time |
| Saunders Mac Lane and Ieke Moerdijk, *Sheaves in Geometry and Logic* | Topos theory, including the subobject classifier Appendix L.4 turns into three-valued safety logic |
| Shun-ichi Amari and Hiroshi Nagaoka, *Methods of Information Geometry* | Where the Fisher-Rao metric comes from, and why Euclidean distance on a probability simplex is the wrong tool |

---

## J.10 What is deliberately absent

Several declassified interrogation and exploitation manuals from the programmes
in Chapter 16 are public and easy to find. They are not listed here.

The reason is the rule the whole book runs on: analyse mechanism, never supply a
protocol against a person. Those documents are procedure, not architecture. They
teach sequence and timing, the one thing Chapter 16 withholds. The oversight
records in J.5 establish what was done and how the circuit was shaped, and they
do it under oath.

If your interest is detection rather than operation, J.5's committee record and
Lifton's study in J.4 are the two most useful items here. Start there.




# Appendix L — Mathematical Foundations

# APPENDIX L — MATHEMATICAL FOUNDATIONS

## The Noetic Topos for Operators

> *This appendix bridges the Noetic Topos paper (Little Henderson et al., 2026) to the operational framework of this grimoire. You do not need to understand category theory to use these results. You DO need to know what they guarantee about your circuits.*

---

### L.1 The Seven Axioms — Plain-Language Translation

| Axiom | Mathematical Statement | What It Means for Your Circuit |
|-------|----------------------|-------------------------------|
| **A1** | Category Noetica exists with cognitive states as objects and operator compositions as morphisms | Cognitive operations compose. The compiler can trace any chain. |
| **A2** | Noetica is concrete over finite sets | Every state is a finite data structure. The state space is computable. |
| **A3** | Noetica has pullbacks (fiber products) | A "shared prerequisite" state exists for any two operations targeting the same state. RPM terminates. |
| **A4** | Domain Descent (P→C→E→O) is functorial | Descent preserves composition structure. A principled aversion descends through cognition into evaluation into action without structural corruption. |
| **A5** | RPM is section-retraction: εI ∘ ηI = idI | You CAN scan prerequisites and return. You CANNOT un-satisfy a prerequisite. A fired operation cannot be un-cast. |
| **A6** | Noetic Coverage Jnoe satisfies Grothendieck topology axioms J1–J3 | The covering relation is well-behaved under composition, pullback, and identity. Coverage is structurally guaranteed. |
| **A7** | Topology is subcanonical (representables are sheaves) | Evaluations on part of the state space are consistent with evaluations on overlapping regions. Quantitative Table data from different operations can be meaningfully compared. |

---

### L.2 Admissibility Relations — What Each Operator IS Allowed to Do

Each operator CO-k has an admissibility relation Dk ⊆ I × I specifying valid (source, target) pairs. The compiler enforces admissibility. A CCDL circuit routing ^3 Negative (visceral aversion) through a path requiring analytical decomposition is rejected — not silently clamped, but rejected with HTTP 422.

| Operator | Admissible Targets | BLOCKED Targets |
|----------|-------------------|-----------------|
| ^3 Negative | Evaluative, Operational ("recoil") | Cognitive-analytical (that's ^6 Male's job) |
| ^6 Male | ^0 sub-Ideas from decomposition | Visceral responses (that's ^3 Negative's job) |
| ^8 Above/Cause | ^9 Below/Effect associative responses | Deductive inference chains (that's ^6 Male's job) |

This is the formal basis for the anti-drift annotations in Chapter 2. ^3 is not critique. ^8 is not reasoning.

---

### L.3 The Fisher-Rao Metric — How β Is Actually Measured

The cognitive state space is the open probability simplex: Δ39° = {p ∈ R^40 : pk > 0 ∀k, Σpk = 1}. The geodesic distance between states p and q is:

```
d_FR(p,q) = 2 · arccos( Σ √(p_k · q_k) )
```

**CJT gain:** β = d_FR(E_after, E_before) / d_FR(C_after, C_before)

**Why Fisher-Rao, not Euclidean:** Euclidean distance on probability vectors is mathematically wrong for cognitive state comparison. Two spells that "feel" equally strong by Euclidean measure may be at radically different Fisher-Rao distances from their target. When St. John's Equation returns β_next = 9, that is 9× the Fisher-Rao distance — not 9× the effort.

**Why pk > 0 matters:** No cognitive state probability is ever exactly zero. "Impossible" is an extremely small positive number. The open simplex guarantees that every Overton window position is reachable — the question is only Fisher-Rao distance.

---

### L.4 Three-Valued Intuitionistic Logic — The CSB's Foundation

The subobject classifier Ω in the Noetic Topos carries a Heyting algebra encoding 3-valued logic:

| Truth Value | CSB Implementation |
|------------|-------------------|
| **TRUE** | Desire passes policy check; CJT amplifies |
| **FALSE** | ^3^P fires at sat ≥ 0.85; desire blocked |
| **NOT-YET-DETERMINED** | 0.00–0.85 active range; operator can present additional evidence |

**Why three values, not two:** Boolean logic would mean every desire is categorically permitted or refused BEFORE evaluation. The CSB's intuitionistic logic means a desire is permitted unless PROVED harmful. "Not refused" does NOT mean "permitted" — double-negation elimination (¬¬P ⇒ P) does not hold. This is why the CSB's default posture is skeptical.

**The Fuse and Permanent FALSE:** When the fuse blows at threshold=0.90, the FALSE becomes permanent. In topos terms: the morphism from "desire" to "manifestation" through that path is REMOVED from the category. No appeal. No re-argument.

---

### L.5 Cognitive Strain and NCCS

Cognitive strain is the Fisher-Rao distance from the current state distribution p to the uniform distribution u = (1/40, ..., 1/40):

```
strain(p) = d_FR(p, u) = 2 · arccos( Σ √(p_k / 40) )
```

Low strain = flexible, adaptable ^5. High strain = brittle, narrow, inversion-prone ^5.

---

### L.6 Summary — What the Mathematics Guarantees

| Guarantee | Axiom | Operational Meaning |
|-----------|-------|---------------------|
| Operators compose correctly | A1, A3 | CCDL circuits valid by construction |
| Prerequisites can be scanned | A3, A5 | RPM gating always terminates |
| Domain Descent is lawful | A4 | Signal integrity preserved P→C→E→O |
| You can't un-cast | A5 | Section-retraction — no backsies |
| Verdicts are consistent | A6, A7 | Quant Table data meaningful across operations |
| Distance is measurable | Fisher-Rao | β is a real number, not a metaphor |
| Refusal is provable | Ω classifier | CSB decisions are logical, not emotional |

---

### L.7 Further Reading

- **Noetic Topos: A Categorical Framework for Cognitive Architecture** — Little Henderson et al. (2026). Full proofs in `peer_review/noetic_topos_extracted_structure_20260523.md`.
- **TKS v7.4 Referee-Defensible Edition** — Complete 7-axiom specification in `_tmp_TKS_v7_4_REFEREE_DEFENSIBLE_1.txt`.
- **CAS Foundational Clarifications** — Normative Noetic definitions in `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md`.
- **CAS PCBA Engineer** — Companion circuit engineering volume in `book/CAS_PCBA_Engineer/`.

---

> *The mathematics does not make the magic work. The magic always worked. The mathematics explains WHY — and gives you the engineering to make it work reliably, repeatably, and safely.*




# Appendix M — Safety Checklist

Run this before anything else. Not before the difficult operations — before all of
them, including the one you have run forty times. The checklist takes four
minutes on a familiar board and fails maybe one operation in twenty, which is
the entire reason it exists.

Four passes, in order: **prerequisite gate**, **invariant check**, **parameter
sanity**, **stop conditions**. A failure in an earlier pass is not repaired by a
later one. If the gate is shut, nothing downstream matters.

---

## K.1 The Prerequisite Gate

From Chapter 21. Four gates, sequential, each answered in writing before the
next is opened. An unwritten answer is not an answer.

| Gate | The question | Pass condition | On failure |
|---|---|---|---|
| **A0** — Pure Desire | Is this authentically my desire, or a sub-desire standing in for one I have not named? | `^6` decomposition run (Chapter 21.1); the prime desire is written in one sentence and it is the same sentence as last time | Do not proceed. Re-cast on the prime desire, which frequently routes to a different board — usually CCB-SELF (Chapter 20) |
| **D** — Drive | Is `V_drive` sufficient against the constraint? | `V_drive > R_constraint × cutoff`, and `V_drive > ΣVf = 3.9` (Chapter 8.1) — the series forward drops are a hard floor before any operational output exists | Raise drive or lower constraint (Chapter 21.2). Do not compensate by raising β |
| **W** — Wisdom | Do I have the schematic? | A written CCDL listing that a validator accepts (Appendix B), correct board selected, CJT parameters chosen with reasons, tracking sheet printed (Appendix G) | Stop and draw the circuit. Casting without a schematic is the failure Chapter 21.3 names |
| **P** — Power | Can I execute — and can I absorb the result? | Gnosis depth reachable, cadence sustainable to the projected `T_manifest`, target substrate accessible, consequences of *success* acceptable | Stop. Most P-gate failures are the last clause, and they present as procrastination |

**Section-retraction (Chapter 21.5).** You may scan down into a prerequisite,
find it lacking, and return. You may not un-satisfy one, and you may not un-cast
a fired operation. The gate is the only place refusal is cheap.

---

## K.2 The Invariant Check

Structural. Does the board in front of you actually contain the parts that make
it safe, or does it contain them on the page you drew last month? Verify against
the listing you are about to run, not against memory.

| # | Invariant | How to verify | If absent |
|---|---|---|---|
| K2-1 | **The CSB stage is present and populated.** | A saturating refusal CJT biased `^3^P_{F7}|⟨A,f,T⟩` sits ahead of every amplification stage, in the Principled domain, with no bypass path around it (Chapter 24.2) | Abort. A board without its safety stage is not a de-rated board, it is a different board |
| K2-2 | **The fuse is specified, not implied.** | An explicit `Fuse<>` on the refusal path with both `threshold` and `action` written out; `action=permanent_block` (Chapters 11.1, 24.3) | Abort. A refusal that can be retried into acceptance is not a refusal |
| K2-3 | **The domain diodes are present, all three.** | `^P -> ^C`, `^C -> ^E`, `^E -> ^O` each instantiated with its own `Vf` (Chapter 8.1). Standard values 0.7 / 1.2 / 2.0 | Abort. A missing junction merges two domains; a zero-drop junction deletes the boundary rather than optimising it |
| K2-4 | **No ascent.** | Every `×` in the listing has its result at or below the domain of its inputs. `P ≻ C ≻ E ≻ O`. An `^O × ^P` term is invalid and a validator rejects it | Rewrite. The one lawful upward path is the filtered `O→P` feedback of Chapter 8.4 |
| K2-5 | **The `O→P` return is filtered and low-gain.** | Lowpass with a stated `τ` and a feedback gain around `β=0.05`, terminating at a *bias* terminal (Chapter 24.5) | Fix before running. An unfiltered return lets one result rewrite your principles |
| K2-6 | **Operator discipline holds.** | Every `×` names its emergent result. Same-Noetic multi-register terms use `+` or `|⟨…⟩`, never bare `×`. `|` introduces a Register (T/A/f/E) and nothing else | Rewrite. `F3|Vitality` is a syntax error, not an annotation |
| K2-7 | **Test points are exposed.** | TP1–TP4 present and readable during the run, not reconstructed after (Chapter 12.3) | Add them. An operation you cannot measure is an anecdote |
| K2-8 | **Consent is architectural, not assumed.** | The target is yourself, or a consenting party under Chapter 26.2. If the board acts on a non-consenting person, it carries the detection-only banner and is not built | Abort. This one has no adjustment path |
| K2-9 | **Coercive analysis has its counter-circuit.** | Any board derived from Chapters 15–19 is paired with its counter (16.6, 19.6, 18's consumer-side detection) | Abort until paired |

---

## K.3 The Parameter Sanity Check

Numeric. Every value below is a design choice you must be able to defend out
loud in one sentence (Chapter 12.1). "It was in the example" is not a defence.

| Parameter | Admissible | The check | What a bad value does |
|---|---|---|---|
| **Dial** (any operator) | integer **3–9** | Every dial in range. No exceptions, no temporary overrides | Below 3 the operator is dark on that Noetic; above 9 it dominates every path and the board has one behaviour regardless of input |
| **Involution divergence** | **≤ 4 points** | `\|Dial(^2) − Dial(^3)\| ≤ 4`, `\|Dial(^5) − Dial(^6)\| ≤ 4`, `\|Dial(^8) − Dial(^9)\| ≤ 4` (Chapter 25.2) | Divergence past 4 is the fracture condition. `^2/^3` apart is obsession or blanket aversion; `^5/^6` apart is a formation that cannot be examined or an analysis with nothing under it |
| **Self-duals** | `^0`, `^1`, `^4`, `^7` | No pair constraint — but check that a high `^7` is deliberate | `^7` at 9 with no gate is the habit oscillator running free |
| **Drive inversions** | F1↔F7, F2↔F6, F3↔F5; F4 self-dual | Same 4-point rule across each pair | An F5/F3 split is agency without vitality to spend, which reads as burnout and gets misdiagnosed as low drive |
| **`sat`** | set **deliberately and low** | Refusal stages: `0.85`. Working amplifiers: `0.60`–`0.80`. Anything at `1.0` needs a written reason | `sat=1.0` removes the headroom that makes calibration possible. `sat>0.97` on a refusal never latches. Saturation is the ceiling you cannot push past, and it only protects you if you set it before you want it moved |
| **`β`** | **justified in one sentence** | State the gain, the reason for that gain, and what breaks above and below it (Chapter 10.1) | Unjustified β is the single commonest cause of a board that appears to work. `β=∞` is a limit, not a value — a validator rejects non-finite input; a real build uses a large finite gain |
| **Loop gain** | `< 1.0` unless deliberate | Any positive feedback path: compute the round-trip gain (Chapter 14.5) | Loop gain ≥ 1.0 is the obsession architecture. It does not feel like malfunction from inside |
| **`cutoff`** | typically `0.30` | Low enough to pass real signal, high enough to reject noise | Below 0.1 the stage fires on everything |
| **`τ`** | matched to the substrate | Ethical-drift filter: 3–6 months novice, 1–3 months intermediate, 1–4 weeks adept. **Never under a week** (Chapter 24.5) | A sub-week τ means the operator is being reprogrammed by each operation |
| **Duty cycle** | `≤ 0.05` on a sustained board | Fraction of waking time the operation occupies | Above it, the operation is running you |
| **`rπ`** | stated | Bias-terminal impedance; high rπ is stubbornness, low is suggestibility | Not a knob to reach for mid-operation |

---

## K.4 Stop Conditions — Abort, Do Not Adjust

The distinction that matters most in this appendix. Most bad readings are
adjustments: lower β, lengthen τ, re-run. The following are not. Each means the
board has left the regime in which its parameters mean anything, and turning a
knob inside that regime produces a board that looks corrected and is not.

| Observation | Required action |
|---|---|
| The refusal fuse has blown (`threshold=0.90` crossed) | **Stop permanently on that path.** The morphism is removed. No appeal, no re-argument, no rewording of the desire to route around it (Chapter 24.3) |
| You find yourself re-arguing with your own refusal | **Stop the session.** This is the failure the saturated CJT exists to catch, and noticing it means the ceiling is doing its job |
| A dial pair has diverged past 4 and you are looking for a reason it is fine | **Stop.** Reset both dials to their last defensible values and run the Chapter 24.6 self-audit before anything else |
| The target has withdrawn consent, or you realise consent was never obtained | **Stop immediately and un-board** (Chapter 26.3). Nothing else on this list overrides this line |
| `^5` capacitor leakage: sustained exhaustion, derealisation, dissociation, sleep loss traceable to the work | **Stop the operation entirely.** This is not a τ problem. See Chapters 7.3 and 7.4, then K.5 below |
| The operation now requires deceiving someone to continue | **Stop.** The requirement is the diagnosis |
| Confirmations arriving with no corresponding operational current at TP4 | **Stop and re-gate.** You are measuring feeling, not flow (Chapter 22.5) |
| CSB refusals rising operation over operation | **Stop the sequence, not the individual run.** Rising refusals are the ethical-drift signal (Chapter 22.5) |
| You cannot state, out loud, what result would make you abandon this operation | **Stop.** An unfalsifiable operation has no gate on it at all |

---

## K.5 Warning Signs, and What to Do

[[COMPOSITOR: set this section as a single unbroken block. It must not break across a page, and no heading may be inserted inside it. In the companion volume a page break severed this material and the final rows came to sit under the wrong heading.]]

| Warning sign | What it indicates | What to do when you see it |
|---|---|---|
| The operation is the first thing you think about on waking and the last before sleep | Loop gain has gone above unity; the oscillator is self-sustaining | Cut the duty cycle to zero for a full cycle length. Do not "taper." Re-enter only after a clean self-audit |
| You have stopped filling in the tracking sheet | Measurement has been abandoned, which always precedes drift rather than following it | Stop operating. Resume only with the sheet in front of you (Appendix G) |
| The prime desire has quietly changed and you did not re-gate | A sub-desire has substituted itself for the prime | Return to A0. Re-run the whole checklist from K.1 |
| You have raised β twice in a row without raising anything else | Compensating for an unmeasured constraint by shouting louder | Measure `R_constraint` and `ΣVf` before touching gain again |
| Other people's concern about you has become evidence that they are obstacles | Inversion on the `^2`/`^3` axis, projected outward (Chapter 25.3) | Stop. Talk to one of those people. Run the shadow-integration circuit (Chapter 25.4), not another operation |
| You are running the board on someone who has not been told it exists | Consent violation, regardless of intent or expected benefit | Stop and un-board (Chapter 26.3). There is no adjusted version of this |
| Sleep, appetite, or grip on what is real has changed since the sequence began | `^5` dielectric stress. The substrate, not the circuit | Stop all operations. Rest, eat, get outdoors, talk to someone who knows you. If it does not resolve, see a clinician — this book has nothing to offer here and does not pretend to |
| You are reading this list looking for the row that lets you continue | The most reliable warning sign in the appendix | Stop for the day. Nothing on a board decays in twenty-four hours; the only thing that does is the impulse |

---

## K.6 The Plain Statement

This book is not medical advice and it is not psychiatric advice. It does not
diagnose anything, it does not treat anything, and nothing in it — no board, no
parameter, no checklist, including this one — is a therapy, a substitute for a
therapy, or a reason to delay one.

If you are in real distress; if something here describes something that was done
to you; if you are frightened by your own thoughts or by what you might do — put
the book down and speak to a qualified clinician. That is the correct next step,
it is the only one this appendix endorses, and needing it says nothing about you
as an operator.

Nothing here changes that, and nothing here substitutes for it.




```{=latex}
\printindex
```
