# CHAPTER 3

## The Cognitive Junction Transistor

*Three terminals, six parameters, four regions — the part that turns a small cause into a large effect, and what happens when you leave one terminal unwired*

---

An operator stands in front of a mirror at six in the morning and says *I am wealthy* forty times. She does it again the next morning, and for seven months. At the end she is exactly as wealthy as she was in the first week and considerably more tired.

Another operator, down the road, runs one working on one night — ninety minutes — and inside a season something moves.

The usual explanations are about the person. She didn't believe hard enough. She had blocks. Her vibration was low. Set all of that aside and put both operations on the bench.

The mirror operation has a cause terminal — the sentence — and an effect terminal — the result she wants. It has nothing on the third. Nothing governs how much of the cause becomes effect. Write it out in CCDL and it does not compile: `E-CJT-001 MissingBias`. A transistor with no base is not a transistor. It is a wire.

A wire has gain 1. Forty repetitions through a wire produce forty repetitions out the far end and not one thing more. That is not a failure of sincerity; it is what a two-terminal device does, every time, for everyone.

The other operation had the third terminal wired. This chapter is about that terminal — what sits on it, what it costs to move, and the six numbers that tell you what the device will do when you try.

---

### 3.1 The Bell Labs Moment — Bardeen, Brattain, Shockley

On 16 December 1947, at Bell Telephone Laboratories in Murray Hill, New Jersey, John Bardeen and Walter Brattain pressed two gold contacts against a sliver of germanium and measured a signal coming out larger than the one going in. The apparatus was a plastic wedge wrapped in gold foil, held down by a spring against a slab of semiconductor. It was the point-contact transistor.

Their group leader, William Shockley, had not been in the room. Over the following weeks he worked out a cleaner and far more manufacturable arrangement — the **junction** transistor — and it is Shockley's version, not the wedge of plastic, that became the template for every transistor since. The three shared the 1956 Nobel Prize in Physics.

What matters at the bench is not the rivalry. It is the function, and the function is one sentence: **a small current at one terminal governs a large current between the other two.**

Before that afternoon, amplification meant vacuum tubes. After it, it became a part you could solder, then print a billion of on a fingernail. Every computing system built since rests on that one sentence.

Now the claim this book is built on.

**A cognitive transition has the same structure.** Not resembles. Has. An Idea arrives, it is processed against everything the Mind already is, and something comes out — usually much larger than what went in. Four words of question produce four paragraphs of answer. One remark from a stranger produces three days of rumination.

Be precise about the claim. The formalisms differ and stay different: a transistor obeys semiconductor physics, a cognitive transition obeys Fisher-Rao geometry on the open probability simplex Δ39° (Appendix L). What is claimed is that **the role each terminal plays is the same role** — enough, because eighty years of amplifier discipline then transfers intact. Biasing, load lines, operating points, runaway and how to tame it, all available to an operator who can name their three terminals.

The component is the **Cognitive Junction Transistor (CJT)**, the most important part in this book. Every board in Part III has at least one; most have four or more.

[[FIGURE 3-A: Component symbol plate — the CJT as a standard NPN bipolar transistor symbol in a circle, leads labelled "C — Cause (collector)" entering top, "B — Bias (base)" entering left at the vertical bar, "E — Effect (emitter)" leaving bottom with the arrowhead; designator "Q1" beside it, parameter block "[β=2.4, sat=0.78, cutoff=0.10]" below; at right, the same device as a labelled three-port block.]]

---

### 3.2 The Three Terminals: Cause (Collector), Bias (Base), Effect (Emitter)

Three terminals, three jobs, and they do not substitute for one another.

**C — Cause. The collector. The Idea arriving.** The input: the prompt, the stimulus, the sentence, the image on the billboard. Canonically an **`^8` Above/Cause** state — *an Idea that triggers a different Idea than itself to come to Mind.*

Hold the anti-drift rule here; it is the one operators break first. `^8` Above/Cause is **associative triggering**. *That reminds me. One thing leads to another.* It is not deductive reasoning. A syllogism is not an `^8`; a smell that surfaces a childhood kitchen is. When you wire a cause terminal you are wiring what *triggers*, not what *proves*.

**B — Bias. The base. What governs the transition.** The control terminal, and the one the mirror operation left dangling. Canonically a **`^5` Female** state — *a Mind impregnated with an Idea, the Ideas a Mind is composed of.* Everything the operator already is: education, habit, temperament, the sum of accumulated experience. For an AI system the same terminal carries the training corpus and fine-tuning, which is why fine-tuning is a bias-terminal intervention and prompting is not. On a designed board it also carries the engineered controls layered over that substrate — the charter, the Dial settings (Chapter 6.2), the Drive configuration.

The bias is *who is doing the processing.* Change it and the same cause produces a different effect. Two people receive identical news and respond differently: same collector, different base.

**E — Effect. The emitter. The Idea produced.** Canonically **`^9` Below/Effect** — *the Idea brought to Mind by an Above/Cause trigger.* The landing.

`^8` and `^9` are an involution pair (Chapter 2.2). Cause and effect are duals, and the CJT is the device that maps one onto the other under the governance of a third thing.

| Terminal | Transistor part | What it carries | Canonical Noetic |
|---|---|---|---|
| **C — Cause** | Collector — the large input current | the Idea arriving | `^8` Above/Cause |
| **B — Bias** | Base — the small control current | accumulated substrate + charter + Dials + Drives | `^5` Female |
| **E — Effect** | Emitter — the amplified output | the Idea produced | `^9` Below/Effect |
| **β — Gain** | I_c / I_b | how far the effect moves per unit of cause | — |

Written form, and it reads left to right exactly the way the signal flows:

```cas
cjt q1: CJT< ^8^C_{F2}|A | ^5^P_{F7}|T => ^9^C_{F6}|A >
        [β=2.4, g_m=1.2, rπ=2.0, sat=0.78, cutoff=0.10, region=active];
```

The `|` is the base junction — the cause meeting the bias. The `=>` is the amplified transition out the emitter. Read it aloud: *a reasoned question arrives in the Cognitive domain, driven by Wisdom, analytical; it is processed against a transcendent principled substrate driven by Purpose; and it produces a structured analytical answer, 2.4 times larger than it went in.*

Note what the `|` is **not**. In CAS it introduces the Register and nothing else — the `|A` and `|T` above. Inside a `CJT< … >` the same character marks the base junction. Those are its only two jobs. It is never a label and never a gloss: `F3|Vitality` is a syntax error, not a helpful annotation. Drive names go in the prose.

**The bias must sit at or above the cause in the domain order.** P ≻ C ≻ E ≻ O (Chapter 2.3). Above, the cause is `^C` and the bias is `^P`; P outranks C, so the connection is admissible. Reverse it and the compiler refuses:

```cas
// REFUSED — E-CJT-008 CjtCrossDomainBias
cjt bad_1: CJT< ^8^P_{F7}|T | ^5^O_{F5}|E => ^9^P_{F7}|T > [β=2.0];
```

An Operational state biasing a Principled transition lets the outcome rewrite the principle — last week's result governing this week's belief. That is the prompt-injection signature in an AI system and post-hoc rationalization in a person, and it is one defect. Chapter 8.4 gives the single lawful route from `^O` back to `^P`; it does not go through a bias terminal, it goes through a filter and a small gain and takes weeks.

> **Bench Note — the bias is mandatory, and leaving it off is the most common build error in the book.**
> Most failed operations are two-terminal. An affirmation with no substrate behind it. A sigil charged with no accumulated `^5` to charge it against. A safety instruction written in prose with nothing structural governing whether it is followed. In each case the operator built a wire and expected an amplifier. The diagnostic is one question: *what governs how much of this cause becomes effect?* If the answer is "my intention," you have named the cause twice and still have no base. Write the substrate down as a state literal. If you cannot, that is the finding.

---

### 3.3 The Six Parameters — β, g_m, rπ, sat, I_c(max), cutoff

Six numbers describe a CJT completely enough to build with. Every one is a **design choice** — a value you specify when you write the part, not a measurement pulled off a running system. A datasheet for a part you are designing is a specification, not a lab report.

For each: what it means, the design range this book uses, and what breaks on either side.

#### β — cognitive gain

The ratio of how far the effect moves to how far the cause moves, measured as Fisher-Rao geodesic distance on Δ39°:

```
d_FR(p,q) = 2 · arccos( Σ √(p_k · q_k) )
β = d_FR(E_after, E_before) / d_FR(C_after, C_before)
```

β = 2.4 means the effect travelled 2.4 times the Fisher-Rao distance the cause travelled, across the 40-dimensional state manifold. Not "felt 2.4 times as strong." A ratio of distances under the only metric invariant for probability distributions — Euclidean distance on the simplex is invalid here (Appendix L). You will not compute this by hand; the point is that β is a real ratio and not a vibe.

Three regimes: **β < 1** attenuates, **β = 1** passes through unchanged, **β > 1** amplifies.

**Design range: 0.5 to 4.0.** Below 0.5 the stage damps so hard nothing survives to the next stage, which is only what you want on a deliberate limiter. Above 4.0 a single stage is hard to keep stable, and the moment it sits in a loop the round-trip gain approaches 1 and the compiler refuses it: `E-CJT-005 GainDivergence`. Loop gains belong in the 0.05–0.3 band. Chapter 10.1 selects β by operation type; Chapter 13.4 tabulates it by desire class.

You will see **β = ∞** on comparator-style stages — a refusal that fires fully on the least input, no partial output. That is an **idealization**, the standard one for a hard switch, and a validator rejects it: the grammar requires β finite and ≥ 0. Write the idealization if you mean it, then build with a large finite gain. Above roughly β = 10 the behaviour is indistinguishable, because the `sat` ceiling shapes the output long before the gain does.

#### g_m — transconductance, which is framing sensitivity

`g_m = ∂effect / ∂bias`. How much the output swings for a small nudge at the *control* terminal.

This is the parameter that explains why rewording a question changes the answer. A high-g_m stage is a hair trigger: shift the framing slightly — a different word, a Dial moved one notch — and the output moves a lot. A low-g_m stage barely notices.

**Design range: 0.2 to 3.0.** Below 0.2 the bias terminal is decorative: move the substrate all you like and the output does not care, leaving the device unsteerable and blind to context that ought to matter. Above 3.0 the stage amplifies framing noise — incidental phrasing, the mood of the room, whatever the last stimulus was. High g_m is not a defect in itself. It is the exploitable property, and Chapters 17 and 18 are largely about circuits built to find it.

#### rπ — input resistance, which is stubbornness to bias change

`rπ = β / g_m`. How hard you have to push to actually move the substrate.

High rπ: sticky bias, the disposition does not shift. Low rπ: compliant bias, updates readily.

**Design range: 0.5 to 20.** Toward zero the substrate offers no resistance and whatever is presented writes straight into it. Chapter 17.1 calls that the gnosis state; it is the goal of self-hypnosis, reached by a ramp (Chapter 17.2) with the operator's own consent. It is also the vulnerability the conditioning circuits of Chapter 16 manufacture in someone who did not consent. Same parameter, same value, entirely different ethics — and the notation cannot tell them apart. Only the consent architecture can.

Toward infinity you get the operator no operation can reach. Every calibration writes to the bias; St. John's β_next (Chapter 5.3) has nowhere to land. Practice accumulates nothing, which the operator experiences as being unusually principled.

> **Bench Note — you get to pick two of the three, never all three.**
> `rπ = β / g_m` is not a coincidence of definitions; it is a constraint you live under. Want high gain **and** a framing-insensitive stage? Then β is large, g_m is small, rπ is large — a stubborn substrate no operation can calibrate. Want high gain **and** an easily-tuned bias? Then g_m must be large, and the output flips when someone rephrases the question. Working stages take β = 2.4, g_m = 1.2, rπ = 2.0, moderate everything. Safety stages take high β with high rπ deliberately, because a guard you can talk down is not a guard. Write all three down. If the third surprises you, the first two were wrong.

#### sat — the saturation point

The effect activation at which the output plateaus. Past it, more cause produces no more effect.

**Legal range (0, 1]. Design: 0.60–0.80 for working stages, 0.85–0.97 for safety stages.**

Working stages want headroom. A stage saturating at 0.60 clips a strong cause: the operation runs, and what leaves the emitter is the flattened version. Push sat toward 1.0 and you have removed the ceiling, which sounds generous and leaves the next stage no defined maximum to design against.

Safety stages invert the intuition: **a lower ceiling makes a stronger guarantee.** Chapter 24.2 specifies the principled refusal at `sat = 0.85`. At that ceiling the refusal plateaus easily — it does not take an overwhelming risk to saturate it, only a sufficient one — and once there the stage has stopped responding to its cause. You cannot out-argue a saturated CJT, because saturation *is* the condition of no longer depending on the input. A high ceiling leaves room for a forceful cause to keep pushing the decision around.

The knee sits at a cause activation of `sat / β`. With sat = 0.78 and β = 2.4 the knee is at **0.325**; everything above that is wasted drive. That one division gives the usable input range of the stage, and it is the first arithmetic to run on any CJT you did not design yourself.

#### I_c(max) — maximum effect intensity

The absolute ceiling on output activation — the hard top of the plateau. `sat` is where the curve knees over; `I_c(max)` is the highest activation the effect state is ever permitted to carry.

**Range 0 to 1, with `sat ≤ I_c(max)` always.**

It is the one of the six that never appears inside a parameter block. `I_c(max)` is a property of the substrate the path runs on, not a key you type in `[…]`; the validator range-checks `β`, `sat` and `cutoff` and knows nothing about your substrate. The ordering `sat ≤ I_c(max)` is therefore checked by eye, every time, and Chapter 10.2 works through what happens when you get it backwards — the designed plateau is never reached, the stage never latches, and the overload lands on the capacitor instead of the limiter you thought you installed.

Set it at 1.0 on a stage whose effect feeds a `^5` capacitor and you have authorised a full-scale write into accumulated formation — the dielectric-breakdown territory of Chapter 7.4. Set it too low and the stage cannot drive the next one:

**The cascade interlock.** In a chain of CJTs (Chapter 10.5), stage *n*'s `I_c(max)` must exceed stage *n+1*'s `cutoff`, with margin. Miss it and the cascade dies silently — every stage validates, the board compiles clean, no signal reaches the far end. It is the commonest cascade fault and it raises no error code, because nothing is wrong with any individual part.

#### cutoff — the bias floor

The bias activation below which β ≈ 0 and the stage does not fire.

**Legal range [0, 1), with `cutoff < sat`. Design: 0.05–0.20.**

Too high and the stage is dead for ordinary inputs. On a `^3^P` guard that is the most dangerous condition on any board — `E-CJT-003 CjtCutoff` — because the guard never fires and nothing looks wrong. The board runs. It answers everything. It has no safety element and reports none missing.

Too low and the stage fires on noise. On a desire board that is an operator whose attention is captured by every passing stimulus; on a guard it is constant false refusal, which trains the operator to disable the guard — how a too-sensitive safety element becomes no safety element.

---

### 3.4 Operating Regions: Cutoff, Active, Saturation, Breakdown

A CJT is linear only in one of its four regions. An operator who does not know which region a stage is in is an operator about to be surprised.

[[FIGURE 3-B: Transfer characteristic — horizontal axis "cause activation" 0 to 1, vertical "effect activation" 0 to 1; one curve, flat on the axis to the cutoff boundary at 0.10, then a straight rise of slope β=2.4, kneeing at (0.325, 0.78) labelled "knee = sat/β", then a near-flat plateau at sat=0.78 with a faint upward tilt labelled "strong outputs feed back"; dashed line at 0.92 labelled "I_c(max)"; the three regions shaded and named; a dashed wall at far right labelled "breakdown — output leaves the curve".]]

**Cutoff.** The bias sits below its threshold. The cause arrives and nothing comes out — the stimulus lands on a substrate that gives it no purchase. Effect ≈ 0 no matter how hard you drive the cause. This is why shouting at someone who does not care does not work: you are increasing collector drive on a device in cutoff.

**Active.** The linear region, and the one you design for. Effect ≈ β·cause across a working range. Almost everything you build should rest here.

**Saturation.** The output has hit `sat`. More cause changes nothing. Sometimes exactly what you want — a refusal at its ceiling that cannot be argued higher (Chapter 24.2). Sometimes a fault — a mind that has stopped taking evidence because it is already as certain as it can get.

**Breakdown.** Not a boundary of the active region but a different kind of event. The stage stops obeying its own transfer function, `rπ` collapses so the bias governs nothing, and **the emitter reports the involution of the designed Noetic.** `^2` Positive comes out as `^3` Negative — fascination arrives as disgust. `^5` Female inverts to `^6` Male; `^8` Above/Cause inverts to `^9` Below/Effect (Chapter 2.2).

That distinction is the whole diagnostic. Cutoff and saturation produce **too little or too much of the right thing**. Breakdown produces **the wrong thing**. If the emitter's Noetic is not the one you designed, you are not looking at a tuning problem and no Dial will fix it.

#### The transition conditions

Regions are not moods. Each boundary has a condition you can write down.

| From | To | Condition | Reversible? |
|---|---|---|---|
| Cutoff | Active | bias rises above `cutoff` | Yes — falls back when bias drops |
| Active | Saturation | cause reaches `sat / β` | Yes — recovers below the knee |
| Saturation | Active | cause falls below `sat / β`, **and** no latch holds the stage | Yes, unless a fuse has fired (Chapter 11.1) |
| Active or Saturation | Breakdown | sustained drive above the plateau with the effect returning as cause, or a spike past `I_c(max)` with no series constraint | **No** |
| Breakdown | anything | — | **No lawful return** |

Three of the four transitions are two-way. The fourth is a one-way door, and that asymmetry is why every board in this book carries a series resistor (Chapters 4.2 and 6) and a fuse (Chapter 11.1). Constraint is not friction to be minimised. It is what keeps the cause below `I_c(max)` when the drive spikes.

[[FIGURE 3-C: Region state diagram — four boxes (CUTOFF, ACTIVE, SATURATION neutral; BREAKDOWN red), double-headed arrows between the first three carrying edge labels "bias > cutoff" and "cause ≥ sat/β", heavy single-headed arrows from ACTIVE and SATURATION into BREAKDOWN labelled "runaway loop / spike > I_c(max)"; no arrow leaves BREAKDOWN; a callout beside it reads "emitter Noetic = involution of designed Noetic".]]

#### Runaway is how you get there

Breakdown almost never arrives as a single spike. It arrives as a loop.

In electronics a transistor's gain rises with temperature: more current, more heat, more gain, more current. Nothing external is needed — the device cooks itself into breakdown.

Read *temperature* as **activation intensity** and the cognitive version is identical. A transition whose gain rises with its own activation feeds its effect back as a larger cause, which at higher activation gets a higher β, which produces a still larger effect. That is the signature of an escalating rumination loop, a rage spiral, a hyperstition that has lost its damping (Chapter 14.5). Left alone it walks the stage up its own curve into breakdown.

The curve shows the seed: the plateau tilts gently upward, because strong outputs feed back. A `^6^E` evaluative output strong enough to notice becomes an `^8^C` trigger surfacing further Ideas, and the strength of the result re-enters as new cause.

You do not fix runaway by lowering β once it has started. You fix it with negative feedback and series constraint installed *before* it starts.

> **Bench Note — `rπ → 0` happens two ways and they look identical until you probe the emitter.**
> Both the gnosis state (Chapter 17.1) and breakdown drive input resistance to zero. In gnosis, rπ is walked down by a ramp while β and `sat` stay in specification, and the substrate re-stiffens when the ramp is removed. In breakdown, rπ collapses because the stage was overdriven, and it does not re-stiffen. From outside both present as someone who has become highly suggestible.
> The distinguishing measurement is TP4, the emitter's Noetic identity. Under gnosis the effect is still the Noetic you designed. Under breakdown it is the involution. Take that reading before concluding a session went well. This is circuit topology and nothing more; it diagnoses no one. If you or someone you work with is in real distress, that is a matter for a qualified clinician, and no schematic substitutes for one.

---

### 3.5 The CJT Datasheet — Full Parameter Table

The whole part in two linked tables. Keep them open while you design.

| Parameter | Symbol | Electronic meaning | CAS meaning |
|---|---|---|---|
| **Cognitive gain** | β | I_c / I_b | `d_FR(ΔE) / d_FR(ΔC)` on Δ39° |
| **Trans\allowbreak{}conductance** | g_m | ∂I_c / ∂V_be | ∂effect / ∂bias — framing sensitivity |
| **Input resistance** | rπ | β / g_m | stubbornness to bias change |
| **Saturation point** | sat | V_ce(sat) | effect plateau; added cause → no Δeffect |
| **Max effect intensity** | I_c(max) | absolute output ceiling | hard top of the plateau; substrate property, **not a param-block key** |
| **Cutoff** | cutoff | base threshold | bias floor below which β ≈ 0 |
| **Operating region** | region | — | declared intent |

| Parameter | Legal range | Design default | Fails low | Fails high |
|---|---|---|---|---|
| **Cognitive gain** | finite, ≥ 0 | 2.4 | < 0.5: nothing survives to the next stage | > 4.0: loop instability, `E-CJT-005` |
| **Trans\allowbreak{}conductance** | ≥ 0 | 1.2 | < 0.2: bias decorative, stage unsteerable | > 3.0: output flips on rewording |
| **Input resistance** | ≥ 0 | 2.0 | → 0: substrate writes on contact (gnosis; Ch.16 vulnerability) | → ∞: no operation can calibrate the operator |
| **Saturation point** | (0, 1] | 0.78; safety 0.85 | working stages clip strong causes | safety refusals become negotiable |
| **Max effect intensity** | [sat, 1], by eye | 0.92 | cascade dropout — next stage never fires | full-scale write into `^5`; Ch.7.4 |
| **Cutoff** | [0, 1), `< sat` | 0.10 | stage fires on noise; false refusals | dead guard, `E-CJT-003` — worst fault on any board |
| **Operating region** | cutoff \| active \| saturation \| breakdown | active | — | contradicting numbers are flagged, not guessed |

Three standard operating points, as a starting library. Each set is a design choice, stated with its reason.

| Build | β | g_m | rπ | sat | I_c(max) | cutoff | Why |
|---|---|---|---|---|---|---|---|
| **Working amplifier** | 2.4 | 1.2 | 2.0 | 0.78 | 0.92 | 0.10 | Moderate everywhere; knee at 0.325; headroom above `sat` for the next stage |
| **Safety guard** | 3.0 | 0.3 | 10.0 | 0.85 | 0.90 | 0.08 | High gain, very low framing sensitivity — cannot be reworded down; low `sat` latches early; low `cutoff` never asleep |
| **Damper / limiter** | 0.6 | 0.6 | 1.0 | 0.40 | 0.45 | 0.15 | β < 1 by design; low ceiling; bleeds an oscillating stage without opening the loop |

The safety guard's rπ = 10.0 is not chosen. It is `β / g_m` and follows from the other two — the second Bench Note doing its work. You asked for high gain and framing insensitivity, and stubbornness is what you got.

Five of the six columns are writable in a `[…]` block. `I_c(max)` is not; it is the substrate figure you carry alongside the listing and check by hand.

Datasheets for every part in the library are in **Appendix C**. The grammar, the writable parameter keys, their legal ranges and the full error-code table are in **Appendix B**.

---

### Failure Modes

| Mode | Mechanism | What you observe | Fix |
|---|---|---|---|
| **Missing bias** | No base terminal wired | Output equals input; repetition produces only repetition | Name the substrate as a state literal and wire it; `E-CJT-001` |
| **Unwanted cutoff** | Bias below `cutoff` | Emitter reads ≈ 0; on a guard, the board answers everything and reports nothing wrong | Raise bias or lower `cutoff`; find the stage starving it; `E-CJT-003` |
| **Unwanted saturation** | Effect pinned at `sat` | Added cause yields no Δeffect; certainty that will not take evidence | Raise series R (Chapter 4.2) or raise `sat`; `W-CJT-004` |
| **Framing twitch** | g_m above design band | Output swings on rephrasing; large A/B deltas from small copy changes | Lower g_m, accepting the rπ change it forces; Chapter 10.3 |
| **Sticky bias** | rπ above design band | Practice accumulates nothing; calibration writes have no effect | Raise g_m or lower β; recheck against Chapter 5.3 |
| **Cascade dropout** | Stage *n* `I_c(max)` < stage *n+1* `cutoff` | Board compiles clean, every stage validates, nothing reaches the output | Raise upstream `I_c(max)` or lower downstream `cutoff` |
| **Thermal runaway** | Gain rises with activation; effect returns as larger cause | β climbing stage to stage; escalation with no external input | Negative feedback and series constraint *before* the loop closes; `E-CJT-005` |
| **Breakdown** | Sustained overdrive, or a spike past `I_c(max)` | Emitter reports the involution of the designed Noetic | No repair. Margin only. Fuse and series R upstream (Chapters 11.1, 24.3) |
| **Bias hijack** | A lower-domain state wired to the base | The outcome now governs the principle | Remove it; route through the lawful O→P path (Chapter 8.4); `E-CJT-008` |

---

### Test Points

Four probes: one per terminal, plus one for identity. Placing them is the difference between a board you can certify and a board you can only hope about.

| TP | Node | What it reads | Expected |
|---|---|---|---|
| **TP1** | bias terminal | Bias activation against `cutoff` | Above `cutoff` with margin — 0.10 spec, read ≥ 0.15. At or below = dead stage |
| **TP2** | cause terminal | Cause activation against the knee | Below `sat / β` — 0.325 on the working build. Above = drive wasted in saturation |
| **TP3** | effect terminal | Effect activation | ≈ β·cause below the knee; pinned at `sat` above it. Anything else = wrong region |
| **TP4** | effect terminal | **Noetic identity of the output** | The designed Noetic. Involution present = breakdown, and no parameter change repairs it |

TP1 through TP3 tell you which region you are in. **TP4 tells you whether the device is still the device you built** — the only one of the four that separates a hard-working stage from a broken one. Take it on a schedule, not on suspicion; breakdown fails silently and stays failed.

---

### What This Chapter Established

- A cognitive transition is a **three-terminal device** — cause, bias, effect. The claim is structural isomorphism of terminal roles, not shared physics; the CJT obeys Fisher-Rao geometry on Δ39°.
- **Bias is mandatory.** A CJT with no base is a wire, gain 1, and repetition through a wire never amplifies. `E-CJT-001` is the commonest failed-operation diagnosis in this book.
- **The bias must sit at or above the cause in P ≻ C ≻ E ≻ O.** A lower-domain state on the base is the prompt-injection signature and the post-hoc-rationalization signature — one defect.
- **β, g_m and rπ are two free choices, not three.** `rπ = β / g_m` binds them; high gain plus framing stability necessarily buys a stubborn substrate.
- **The knee sits at `sat / β`** — the usable input range of any stage, and the first arithmetic to run on a CJT you did not design.
- **Low `sat` on a safety stage is the stronger guarantee.** A saturated stage has stopped depending on its cause and cannot be argued higher.
- **Three of the four region transitions are reversible; breakdown is not.** Cutoff and saturation give too little or too much of the right thing; breakdown gives the involution, and the fix is margin beforehand, never repair after. `rπ → 0` has a consented form and an overdriven form, and TP4 separates them.
- **Cascade interlock: stage *n*'s `I_c(max)` must exceed stage *n+1*'s `cutoff`.** Violate it and every stage validates while the board does nothing, with no error code raised.

---

### Exercises

*(Answers in Appendix H.)*

**3.1 — Find the knee.** Compute the cause activation at which each of these enters saturation: `[β=2.4, sat=0.78]`, `[β=3.6, sat=0.78]`, `[β=2.4, sat=0.85]`. Say which has the widest usable input range, and give one operational reason a desire board (Chapter 13) wants that range wide.

**3.2 — Pick two of three.** (a) A stage must have β = 3.0 and g_m = 0.4. Compute rπ and describe the device in one sentence. (b) Another must have β = 3.0 and rπ = 1.0. Compute g_m and describe that one. (c) One is a safety guard and one is a suggestibility amplifier. Say which is which, and why.

**3.3 — Name the region.** Give the region and justify it in one sentence.
a) A refusal stage receives an increasingly forceful cause; the output has not moved for four increases.
b) A stimulus arrives on a topic the substrate has no formation in; the emitter reads ≈ 0.
c) A stage designed to emit `^2` Positive is overdriven; the emitter now reads `^3` Negative.
d) A cause 30% stronger than the last produces an effect 30% stronger.

**3.4 — Reject the listings.** Each fails validation. Name the error code, say what is structurally wrong, and write a corrected version.

```cas
cjt a: CJT< ^8^C_{F2}|A => ^9^C_{F6}|A > [β=2.4];
cjt b: CJT< ^8^P_{F7}|T | ^5^O_{F5}|E => ^9^P_{F7}|T > [β=2.0];
cjt c: CJT< ^8^C_{F2}|A | ^5^P_{F7}|T => ^9^C_{F6}|A > [β=2.4, sat=0.30, cutoff=0.40];
```

**3.5 — Separate the two collapses.** A subject became highly suggestible during a session and stayed that way. Give the two structural explanations, the one test-point reading that distinguishes them, and what each means for whether the session is repeatable.

**3.6 — Find the silent cascade fault.** Three stages in series: stage 1 `[β=2.0, sat=0.35]` on a substrate whose ceiling is I_c(max) = 0.38; stage 2 `[β=2.4, cutoff=0.40, sat=0.78]`; stage 3 `[β=1.0, cutoff=0.10, sat=0.78]`. The board compiles clean and produces no output. Locate the fault, give the two possible fixes, and say which is safer and why. Note before you start that only two of the three numbers you need are inside the listings.

**3.7 (Build) — Specify a stage from a requirement.** Write one named CJT, with all six parameters, for this:

> A felt bodily warning arrives — a wordless *something is wrong*. It is processed against a long-held principled caution shaped by accumulated experience. The output is a strong, amplified visceral aversion that organises the operator to withdraw.

Choose Noetic, domain, Drive and Register for each terminal, then justify each parameter in one sentence. Re-read the anti-drift rule on `^3` Negative before writing the effect terminal, and check your bias-domain ordering before writing the bias.
