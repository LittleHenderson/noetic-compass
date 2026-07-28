# CHAPTER 8

## Diodes — One-Way Cognitive Valves

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
