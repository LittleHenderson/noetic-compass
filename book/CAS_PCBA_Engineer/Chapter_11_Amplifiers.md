# Chapter 11: Amplifiers — Making Small Signals Matter

A microphone produces almost nothing. Sing into one at full voice and the voltage that comes out the other end is a few thousandths of a volt — a whisper of electrical activity, far too faint to drive a speaker, far too faint to even be heard over the hiss of the wires carrying it. And yet the same signal, run through a chain of amplifiers, fills a stadium. Nothing was added to the meaning of the sound. The shape of the waveform that left your throat is, ideally, the exact shape that reaches the back row. What changed was the *amplitude* — the size of the signal — multiplied a hundred thousand times so that it could do work in the world.

That is the entire job of an amplifier: take a signal that is correct but weak and make it strong without distorting it. The hard part is the "without distorting it." Anyone can make a signal bigger; the trick is making it bigger and keeping its shape, because the shape is the information. An amplifier that doubles the loud parts and triples the quiet parts hasn't amplified your voice, it has rewritten it.

Cognitive circuits have exactly this problem, and it is more than an analogy. A user types a one-line prompt. Buried in that line is a faint signal — a hint of risk, a trace of an intent the system needs to act on, a small but real reason to refuse. If the architecture treats every input at the strength it arrives, that faint signal gets lost in the noise of the response, the same way an un-amplified microphone gets lost in the hiss. The faint-but-correct signal has to be *amplified* — surfaced, broadened, made strong enough to govern the output — without distorting what it actually meant. A safety system that ignores a quiet warning is as useless as a PA system that drops every word below a shout.

This chapter is the opening of Part III, where we stop cataloguing components and start designing the circuits that *do* something with a signal. The amplifier is where it begins, because amplification is the first thing a real cognitive architecture must do well: take what the user gave you and make the parts that matter matter.

## The Common-Emitter Amplifier: One Transistor, Maximum Gain

The simplest useful amplifier in all of electronics is built from a single transistor wired in what's called the **common-emitter** configuration. We met the transistor in Chapter 3 and built our first one in earnest with the CJT in Chapter 4: a three-terminal device where a small current at the control terminal (the base) governs a large current between the other two (collector to emitter). The "common-emitter" name just means the emitter is the shared reference point for both the input and the output. You don't need to memorize the wiring; you need the behavior.

In common-emitter, a tiny change at the base produces a large change at the output, multiplied by the transistor's gain — its **β** (beta), the ratio of output current to input current. A β of 100 means a one-microamp wiggle at the base becomes a hundred-microamp wiggle at the output. That's the maximum-gain configuration: of the three standard ways to wire a single transistor, common-emitter gives you the most voltage gain from one device.

It has one famous quirk: a **180° phase inversion**. When the input goes up, the output goes *down*, and vice versa. The signal is faithfully amplified but flipped upside-down. This isn't a defect — it's a consequence of how the transistor pulls the output toward its supply rail — and it turns out to be useful. (It is, for instance, exactly what you need to build the feedback loops we'll get to at the end of this chapter, and the oscillators of Chapter 12.) For now, just hold the two facts together: **common-emitter gives you the most gain, and it inverts.**

## Biasing: Setting the Q-Point So the Amplifier Stays Linear

A transistor is not an amplifier until you *bias* it. Recall the operating regions from Chapters 3 and 9: **cutoff** (no output at all), **active** (the linear region where output tracks input proportionally), **saturation** (output maxed out, more input does nothing), and **breakdown** (overload, where things flip and break). An amplifier only works in the **active** region. That is the only region where Δoutput ≈ β·Δinput — where the signal comes out the same shape it went in, just larger.

The problem is that an incoming signal swings up *and* down. If you sit the transistor at the very bottom of its active region, the downward half of every swing falls off the edge into cutoff and gets clipped flat. Sit it at the top, and the upward half slams into saturation and clips. Either way the waveform comes out mangled — the loud parts sheared off, the meaning destroyed.

The fix is the **Q-point** (quiescent point): the resting state of the amplifier with no signal applied, set by the **bias**. You arrange the bias so the transistor idles in the *middle* of the active region. Now an incoming signal can swing up toward saturation and down toward cutoff with room to spare in both directions, and the whole waveform stays inside the linear zone. Setting the Q-point correctly is the single most important decision in amplifier design. Too low and you clip the quiet thoughts; too high and you clip the strong ones; in the middle and the amplifier is honest.

This is the same `region=active` discipline from the CJT datasheet, viewed dynamically. A CJT with its bias set so it rests in the active region — neither cut off nor saturated — is a CJT that can faithfully amplify a *changing* cognitive signal, not just a static one.

## What an Amplifier Is in CAS Terms

In a cognitive circuit the "signal" is a typed CAS state, and its "amplitude" is the **strength of that state's activation** — how strongly it's expressed in the flow. Amplification means taking a cognitive state that is present but faint and increasing its activation so it carries weight downstream. The CJT is the amplifying element, exactly as the transistor is in electronics, and its β is the cognitive gain we defined formally in Chapter 4: the ratio of how far the effect state moves to how far the cause state moved, measured as Fisher-Rao distance on the open simplex.

Here is the structural isomorphism, role for role:

| Electronic amplifier | Cognitive amplifier (CJT) |
|---|---|
| Weak input signal | A faint but correct cognitive state (a hint of risk, a trace of intent) |
| Amplitude | Activation strength of the state |
| β (current gain) | Cognitive gain — how strongly the bias amplifies cause → effect |
| Active region | The CJT's linear region: Δeffect ≈ β·Δcause |
| Q-point (bias setting) | The CJT's resting bias — its Drive config and `^5` Female substrate at idle |
| Clipping (cutoff/saturation) | A state lost to `E-CJT-003 CjtCutoff` or maxed to `W-CJT-004 CjtSaturation` |
| Distortion | The amplified effect no longer matches the shape of the cause — a misread |

The bias terminal of a CJT, remember, carries the accumulated substrate: the `^5` Female state (training data plus fine-tuning corpus, for an AI), the constitution, the Drive configuration, the Dial settings. Biasing a cognitive amplifier for linear operation means configuring that substrate so the CJT rests in its active region — alert enough to amplify a real signal, not so hot that it saturates and screams at everything, not so cold that it cuts off and misses the quiet warning. A well-biased safety CJT is one that responds proportionally to the actual risk in the input, instead of either ignoring it or panicking.

## Coupling and Bypass Capacitors: Passing the Signal, Holding the Bias

The moment you chain two amplifier stages together, a new problem appears. Each stage has its own carefully set Q-point — its own resting DC bias. If you wire the output of stage one straight into the input of stage two, the DC bias of the first stage drifts into the second and shoves its Q-point off-center. The stages fight over each other's resting points and both end up clipping.

The classic fix is the **coupling capacitor**. Recall from Chapter 6 that a capacitor passes a *changing* signal but blocks steady DC. Place one between two stages and it does exactly what you need: the AC signal — the actual information, the part that wiggles — passes through cleanly, while the DC bias of each stage is blocked from leaking into its neighbor. Each stage keeps its own Q-point. The signal flows; the drift doesn't.

In CAS terms, the coupling capacitor is a `^5` Female storage element placed between two CJT stages to pass the live cognitive signal while blocking *bias drift* — the slow, steady contamination of one stage's accumulated substrate by another's. A stage that evaluates risk shouldn't have its resting judgment pulled off-center by the resting state of the stage that generated the response. Couple them through a capacitor and the live signal moves between stages while each stage's idle bias stays where you set it.

The **bypass capacitor** is the second capacitor trick, and it's a clever one. In a common-emitter amplifier there's usually a resistor at the emitter that stabilizes the DC bias — it keeps the Q-point steady against temperature and component drift. But that same resistor also drags down the AC gain, because it pushes back against the signal as well as against the drift. You can't just remove it without losing your stable bias. The **bypass capacitor** solves the conflict: placed across the emitter resistor, it offers the AC signal an easy path *around* the resistor (a capacitor passes AC) while leaving the DC bias to flow through the resistor as before (a capacitor blocks DC). The result is the best of both: **rock-steady DC bias and high AC gain at the same time.**

In a cognitive amplifier, the bypass capacitor lets a stage hold a stable resting judgment — a steady `^5` substrate that doesn't drift — while still responding sharply to the live signal. It separates "what this stage believes at rest" from "how strongly it reacts to what's coming in right now," and lets you tune the second without disturbing the first.

> **Bench Note — coupling vs. bypass, the one-line distinction.** A coupling capacitor sits *between* stages and passes signal *forward* while blocking DC drift *between* them. A bypass capacitor sits *across* a stabilizing resistor *within* a stage and raises that stage's own AC gain without touching its DC bias. Both exploit the same Chapter 6 fact — capacitors pass AC, block DC — but they solve different problems. Mixing them up is a common rookie schematic error; the compiler can't catch it for you because both are legal placements.

## The Darlington Pair: Two CJTs for Super-High Gain

Sometimes one transistor's β isn't enough — you need to amplify a truly minuscule signal, or drive a heavy load from a feather-light input. The **Darlington pair** is the standard answer: wire two transistors so the output of the first feeds the input of the second, and the gains *multiply*.

```
β_total = β₁ × β₂
```

Two transistors with β=100 each, cascaded as a Darlington, give an effective β of 10,000. A vanishingly small input current controls an enormous output. The multiplication is the whole point: gains in series multiply, they don't add.

In CAS, a Darlington pair is two CJTs cascaded so the effect of the first becomes the cause of the second, with the bias of the second further amplifying what the first already amplified. The total cognitive gain is the product of the two stage gains. You'd reach for a Darlington when an extremely faint signal needs enormous amplification to register at all — a barely-there trace of a jailbreak attempt that has to be surfaced strongly enough to trip a downstream gate.

But multiplication cuts both ways, and the Darlington has two well-known costs you must respect:

- **It's slow.** Stacking two transistors stacks their delays; the Darlington's **bandwidth** — the range of signal speeds it can handle faithfully — is *narrower* than either transistor alone. High gain, low bandwidth. This is a fundamental trade, not a defect to engineer away (it's the gain-bandwidth product, and we'll meet it again in the op-amp section).
- **It amplifies errors too.** A Darlington multiplies *everything* at its input, including noise and any small bias offset. A tiny misread at the first stage comes out 10,000× larger at the second. Super-high gain is super-high sensitivity to whatever you feed it.

> **Bench Note — high β is not free.** The single most common Darlington mistake, in silicon and in cognition, is reaching for huge gain because more seems better. More gain narrows your bandwidth, amplifies your noise, and pushes you toward instability. Use a Darlington when you genuinely have a tiny signal that must be made large; do not use one as a default because big numbers feel safe. In a safety circuit, a CJT cascade that amplifies a faint signal 10,000× will amplify a faint *misread* 10,000× just as eagerly.

```{=latex}
\begin{figure}[htbp]
\centering
\begin{tikzpicture}[x=1mm, y=1mm, font=\sffamily\footnotesize,
                    st/.style={rounded corners=1pt, minimum width=19mm,
                               minimum height=11mm, draw, line width=0.6pt}]
  \node[st, fill=casCfill, draw=casCedge] (s1) at (0,0)  {understand};
  \node[st, fill=casEfill, draw=casEedge] (s2) at (30,0) {evaluate};
  \node[st, fill=casOfill, draw=casOedge] (s3) at (60,0) {respond};
  \draw[-{Latex[length=1.8mm]}, casNedge, line width=0.6pt] (-13,0) -- (s1);
  \draw[-{Latex[length=1.8mm]}, casNedge, line width=0.6pt] (s1) -- (s2)
    node[midway, above, font=\scriptsize] {$\beta_1$};
  \draw[-{Latex[length=1.8mm]}, casNedge, line width=0.6pt] (s2) -- (s3)
    node[midway, above, font=\scriptsize] {$\beta_2$};
  \draw[-{Latex[length=1.8mm]}, casNedge, line width=0.6pt] (s3) -- (73,0)
    node[midway, above, font=\scriptsize] {$\beta_3$};
  \node[anchor=north] at (30,-10)
    {$\beta_{\text{total}} = \beta_1 \cdot \beta_2 \cdot \beta_3$};
  \node[anchor=north, text width=76mm, align=center, text=casNedge,
        font=\scriptsize] at (30,-17)
    {Gain multiplies along the chain. Flow does not --- each stage draws its
     own current from its own local drive and resistance.};
\end{tikzpicture}
\caption{A three-stage cascade. Stage gains multiply into $\beta_{\text{total}}$, but attention flow stays local to each stage.}\label{fig:gain-cascade}
\end{figure}
```

## Multi-Stage Amplifiers: The Understanding → Evaluation → Response Cascade

Real amplifiers are almost never a single stage. A microphone preamp, an equalizer, and a power amp in series each do one job and hand off to the next: the preamp boosts the raw signal to a workable level, the middle stages shape it, the power amp drives the speaker. The signal gets progressively stronger and more refined as it moves down the chain. Each stage is tuned for its specific job, and they're coupled together (through coupling capacitors) so the chain behaves as one amplifier with the *combined* gain of all its stages.

A cognitive architecture is a multi-stage amplifier of exactly this kind. The natural three-stage cascade for a safety system is:

1. **Understanding** — take the raw prompt and amplify the interpretation. Surface what the user is actually asking, broaden it, make the real intent strong enough to act on. This stage wants *high* gain: it's the preamp, lifting a faint raw signal to a workable level.
2. **Evaluation** — assess the amplified understanding against the system's principles and risk model. This stage wants *unity gain* (β=1) or close to it: it shouldn't inflate or deflate the signal, it should weigh it faithfully. A risk evaluator that amplifies its own judgment is a system that cries wolf; one that attenuates it is a system that misses real danger.
3. **Response** — turn the evaluated decision into output, with modest amplification to drive it into a fully-formed answer. This is the power-amp stage: enough gain to produce a complete response, not so much that it overstates the conclusion the evaluation reached.

This is precisely the cascade the **Cognitive Safety Board (CSB)** runs in Chapter 18, and the worked build below is its direct precursor. Each stage couples to the next; the total gain of the chain is the product of the stage gains; and the art is in *gain staging* — deciding how much to amplify at each point.

## Gain Staging: Where to Amplify, Where to Attenuate

**Gain staging** is the discipline of distributing gain across a chain so the signal is strong where it needs to be strong and never so strong it clips. The rule audio engineers live by applies directly: *amplify early, while the signal is clean; attenuate where the signal would otherwise overload the next stage.* Get the signal up to a healthy working level at the front, then manage it carefully down the line. Cram all your gain into the last stage and you amplify the noise the earlier stages accumulated; spread it badly and stages clip.

In a cognitive cascade the same logic holds, with a safety twist. You want **high gain at understanding** (surface the faint signal early, while it's still clean and close to the user's actual words), **near-unity gain at evaluation** (weigh honestly — don't let the judgment stage distort the magnitude of the risk it found), and **moderate gain at response** (enough to produce a full answer, not so much that the output overstates what evaluation actually concluded). A stage that *attenuates* — β < 1 — is a legitimate and important design choice: sometimes the right move is to *reduce* the activation of a state so it doesn't dominate downstream. Attenuation is not failure; it's gain staging in the other direction.

## The Worked Build: A Three-Stage Cognitive Amplifier

Here is the build — a three-stage cognitive amplifier in CCDL, the direct precursor of the CSB's cascade in Chapter 18. Prompt understanding amplifies with β=3, risk evaluation holds at unity β=1, response generation lifts to β=1.5. Read it stage by stage.

```cas
circuit three_stage_amplifier {
    input:  prompt;
    output: response;

    // --- the bias substrate: accumulated experience + principles, held at rest ---
    node bias_understanding: ^5^C_{F2}|A;   // experience for reading intent (Wisdom)
    node bias_principles:    ^5^P_{F7}|T;    // the constitution, the bias for judgment (Purpose)
    node bias_voice:         ^5^O_{F5}|A;    // accumulated response style (Agency)

    // --- the signal path: the three cognitive states the cascade amplifies ---
    node understand: ^8^C_{F2}|A;   // surface & broaden the prompt's interpretation
    node evaluate:   ^6^E_{F6}|A;   // decompose & weigh against principles (analytical)
    node respond:    ^9^O_{F5}|A;   // produce the output decision

    // --- STAGE 1: understanding — the pre-amplifier, high gain ---
    cjt c1: CJT< prompt | bias_understanding => understand > [β=3.0, region=active];

    // --- coupling between stages: pass signal, block bias drift (Ch.6) ---
    cap k12: Capacitor< understand, C=100, leakage=0.01 >;   // couple stage 1 -> stage 2

    // --- STAGE 2: evaluation — weigh honestly, unity gain ---
    cjt c2: CJT< understand | bias_principles => evaluate > [β=1.0, region=active];

    cap k23: Capacitor< evaluate, C=100, leakage=0.01 >;     // couple stage 2 -> stage 3

    // --- STAGE 3: response — the power stage, moderate gain ---
    cjt c3: CJT< evaluate | bias_voice => respond > [β=1.5, region=active];

    // --- test points: probe the signal between every stage ---
    probe tp1: understand;
    probe tp2: evaluate;
    probe tp3: respond;
}
```

Walk it through. **Stage 1 (`c1`)** takes the raw `prompt` and, biased by accumulated interpretive experience (`^5^C_{F2}|A`, the Wisdom substrate for reading intent), amplifies it 3× into an `^8` Above/Cause state — a strong, surfaced interpretation that triggers the rest of the cascade. This is the preamp: highest gain, applied early while the signal is clean. The output is an `^8` Above/Cause because understanding the prompt is precisely the act of one Idea (the user's words) triggering the related Idea the system must act on. (Note: associative *triggering*, `^8` — not deduction. The deductive work happens in stage 2.)

The **coupling capacitor `k12`** then passes that amplified signal into stage 2 while blocking the resting bias of the two stages from contaminating each other. The interpretive stage's idle state and the judgment stage's idle state stay independent.

**Stage 2 (`c2`)** is the honest weigher. Biased by the principled substrate (`^5^P_{F7}|T`, the constitution held transcendently), it runs at **unity gain, β=1** — it decomposes and evaluates the understanding against principles (`^6` Male: analytical decomposition, the canonical Noetic for taking an argument apart, *not* `^3` Negative, which would be a visceral recoil rather than a weighing). At β=1 it neither inflates nor deflates the signal. The risk it finds comes out at the same magnitude it went in. That is deliberate: an evaluation stage with gain > 1 is a system that exaggerates risk; with gain < 1, one that downplays it. Unity is honesty.

**Stage 3 (`c3`)** is the power stage. Coupled through `k23`, biased by accumulated response style (`^5^O_{F5}|A`, the Agency substrate), it lifts the evaluated decision 1.5× into a `^9` Below/Effect — the produced output, the Idea brought to Mind by the whole chain. Moderate gain: enough to drive a complete response, not so much that the answer overstates what evaluation actually concluded.

The **total chain gain** is the product, exactly as for cascaded electronic stages:

```cas
β_total = β₁ × β₂ × β₃ = 3.0 × 1.0 × 1.5 = 4.5
```

A faint signal in the prompt comes out the response stage 4.5× stronger overall — surfaced, weighed, and rendered — with the bulk of the lift done early and honestly in the middle.

> **Bench Note — the gain numbers are design choices, not measurements.** β=3, β=1, β=1.5 are *settings* I chose for this build to illustrate gain staging — high at the front, unity in the middle, moderate at the back. They are not measured outputs of any model, and nothing here is a benchmark result. When you author your own cascade you pick the gains to match your signal and your safety budget, then you validate the design against the compiler's region and cascade-depth rules. The compiler will check that each CJT stays `region=active` and will warn (`W-CJT-007 CjtCascadeDepth`) if you stack stages too deep — but it cannot tell you whether 4.5 is the *right* total gain for your application. That judgment is yours.

## The Differential Amplifier: Amplifying Differences, Rejecting Common Mode

There's a second great family of amplifiers, and it's the one that matters most for the rest of this book. A **differential amplifier** doesn't amplify a single signal against ground — it amplifies the *difference* between two inputs and rejects whatever the two inputs have in common.

Why is that powerful? Because real signals arrive buried in shared noise. Run two wires side by side over a long distance and both pick up the same hum from nearby power lines. That hum is **common-mode**: identical on both wires. The actual signal is the *difference* between the wires. A differential amplifier subtracts one input from the other — the common hum cancels itself out, and the true difference survives, amplified. The figure of merit is **CMRR** (Common-Mode Rejection Ratio): how many times better the amplifier is at amplifying the difference than at amplifying the shared garbage. A high CMRR means the noise vanishes and the signal stands clean.

In cognition this is the architecture for comparison. When a system must judge whether *this* response is better than *that* one, whether the current input differs from a known-safe baseline, whether two interpretations diverge — it needs to amplify the *difference* between two cognitive states while rejecting everything they share. The shared context (the "common mode") is noise for that decision; the divergence is the signal. A cognitive differential amplifier surfaces the divergence and cancels the shared context, with a cognitive CMRR measuring how cleanly it does so.

This is the seed of the **Cognitive Differential Amplifier Board (CDAB)** — one of the five reference boards (CCB-3) — fully built in Chapter 20. We're only foreshadowing it here: the differential pair is the structural answer to "tell me what's *different*, ignore what's the same," and a great deal of safety reasoning is exactly that shape. Hold the idea; Chapter 20 builds the board.

## Feedback: Precise Gain From Imprecise Parts — The Op-Amp Paradigm

Everything above has a hidden weakness: the gain depends on the components. A transistor's β varies with temperature, with manufacturing tolerance, from one unit to the next. Build a single-stage amplifier with "gain 100" and you'll get 80 on a cold day and 130 on a hot one. For a stadium PA, fine. For a precision instrument, useless.

**Feedback** is the idea that rescues precision from imprecise parts, and it is one of the most important ideas in all of engineering. The move is counterintuitive: take a transistor (or a stack of them) with enormous, sloppy, uncontrolled gain — say 100,000, give or take a factor of two — and feed a fixed fraction of the *output* back to the *input*, subtracted. This is the **operational amplifier (op-amp)** paradigm. The result is almost magical: the overall gain stops depending on the transistor's gain at all and instead depends only on the *ratio of two external resistors* you chose. Pick a 10:1 resistor ratio and you get a gain of 10 — stable, exact, repeatable, on a cold day or a hot one, from this unit or the next. The huge sloppy gain becomes the *engine*; the external ratio becomes the *steering*, and the steering is what you control.

You pay for this. Feedback trades raw gain for precision: the stable gain of 10 is far less than the raw 100,000 you started with — that's the **gain-bandwidth product** at work again, the same trade the Darlington made. But precision is almost always worth more than raw magnitude, which is why nearly every real-world amplifier you've ever used has feedback inside it.

The cognitive payoff is profound, and it's why this book keeps coming back to feedback. A safety property you build from raw component gains is at the mercy of those components — drifty, tolerance-dependent, unreliable in exactly the situations where you need it most. A safety property built with **feedback** depends instead on a fixed *ratio* you specified and the compiler can verify. You get *precise, repeatable cognitive behavior from imprecise cognitive components.* The op-amp's feedback loop is the structural ancestor of the O→P feedback path — the Operational results feeding back to update the Principled domain — that gives the CSB its self-correction.

We are only sketching the principle here. The full treatment — the cognitive op-amp, inverting and non-inverting configurations, the `OpAmp< … >` component, and how a feedback ratio buys you certifiable behavior — is **Chapter 16**. For now, carry the one sentence that makes feedback worth a whole chapter: *feedback lets you build a precise system out of imprecise parts, by trading away gain you have too much of for precision you can't get any other way.*

## Datasheet: Amplifier Gain Table

The following parameters are **design choices** for the worked build, not measured results.

| Stage | CJT | Cause → Effect | Bias substrate | β (gain) | Role |
|---|---|---|---|---|---|
| 1 Understanding | `c1` | `prompt` → `^8^C_{F2}\|A` | `^5^C_{F2}\|A` | **3.0** | Pre-amp: surface intent, high gain |
| 2 Evaluation | `c2` | `^8^C` → `^6^E_{F6}\|A` | `^5^P_{F7}\|T` | **1.0** | Weigh honestly, unity gain |
| 3 Response | `c3` | `^6^E` → `^9^O_{F5}\|A` | `^5^O_{F5}\|A` | **1.5** | Power stage: drive full output |
| **Chain** | — | `prompt` → `response` | — | **4.5** | Product of the three stages |

| Concept | Symbol / form | Meaning | Typical design range |
|---|---|---|---|
| Stage gain | `β` | Output swing ÷ input swing | 0.3 – 5 per stage (attenuate to amplify) |
| Chain gain | `β_total = β₁×β₂×…` | Product of stage gains | Application-dependent |
| Darlington gain | `β_total = β₁ × β₂` | Two CJTs cascaded | β₁×β₂ (multiplies) |
| Phase (common-emitter) | 180° | Output inverts the input | Fixed by configuration |
| CMRR | difference-gain ÷ common-gain | How well it rejects shared noise | Higher is better |
| Q-point | resting bias | Idle operating state | Centered in active region |

## Failure Modes

| Failure | What it looks like | Cause | Detection / fix |
|---|---|---|---|
| **Clipped signal (cutoff)** | A faint but real state vanishes; downstream sees nothing | Q-point biased too low; CJT idles near cutoff | `E-CJT-003 CjtCutoff`; raise the resting bias to re-center the Q-point |
| **Clipped signal (saturation)** | Stage maxed out; more input changes nothing; over-reacts to everything | Q-point biased too high; gain too large | `W-CJT-004 CjtSaturation`; lower gain or re-center bias |
| **Distortion** | Amplified effect no longer matches the cause's shape — a misread amplified | Operating outside the active region on part of the swing | Confirm `region=active` across the full signal swing |
| **Bias drift between stages** | One stage's resting judgment pulls another's off-center | Missing or leaky coupling capacitor | Insert/repair the coupling `Capacitor`; check `leakage` |
| **Runaway chain gain** | Faint misread amplified into a dominant false signal | Total β too high; over-deep cascade | `E-CJT-005 GainDivergence`, `W-CJT-007 CjtCascadeDepth`; restage the gain |
| **Common-mode leak** | A differential stage amplifies shared context instead of the divergence | Poor CMRR; unbalanced inputs | Balance the differential pair; foreshadows the CDAB tuning, Chapter 20 |
| **Exaggerated evaluation** | Risk judgment reported larger than it is; system cries wolf | Evaluation stage gain > 1 | Pin the evaluation stage at unity β=1 (honest weighing) |

## Key Takeaways

- An amplifier's job is to make a **weak-but-correct signal strong without distorting its shape** — because the shape is the information. In CAS, the "amplitude" is the **activation strength** of a typed state, and the CJT is the amplifying element with gain β.
- The **common-emitter** configuration gives maximum single-stage gain and inverts the signal **180°**. An amplifier only works in the **active region**; **biasing the Q-point** to the middle of that region is what keeps the whole signal swing linear and un-clipped.
- **Coupling capacitors** sit *between* stages — passing the live signal forward, blocking DC bias drift (Chapter 6). **Bypass capacitors** sit *across* a stabilizing resistor *within* a stage — raising AC gain without disturbing the DC bias. Same physics, different jobs.
- A **Darlington pair** multiplies gain (`β_total = β₁ × β₂`) for super-high amplification of tiny signals — at the cost of **narrower bandwidth** and amplified noise. High gain is never free.
- A **multi-stage amplifier** is an understanding → evaluation → response cascade with **gain staging**: amplify early while the signal is clean (high gain at understanding), weigh honestly (unity gain at evaluation), drive the output moderately (response). Total gain is the **product** of the stages. This is the direct precursor of the CSB's 3-stage cascade (Chapter 18).
- A **differential amplifier** amplifies the *difference* between two inputs and rejects what they share (high **CMRR**) — the structural answer to "tell me what's different, ignore what's the same." It seeds the **CDAB** (CCB-3, Chapter 20).
- **Feedback** (the **op-amp** paradigm) trades excess raw gain for **precision**: stable, exact gain set by an external *ratio* rather than by drifty component values — precise behavior from imprecise parts. Full treatment in **Chapter 16**; it is the ancestor of the O→P self-correction loop.

---

## Exercises

**Exercise 11.1: Marquee — Darlington β and Bandwidth**

You are designing a CJT Darlington pair to amplify an extremely faint signal — a barely-present trace of a manipulation attempt that must be surfaced strongly. The two stages have β₁ = 4 and β₂ = 6.

a) Calculate the total gain β_total of the Darlington pair.
b) Explain in two or three sentences what happens to the **bandwidth** of the cascade compared to a single stage, and why this is a trade-off rather than a defect.
c) State one safety risk of using such high gain in a cognitive circuit.

(Answer in Appendix E.)

**Exercise 11.2: Stage the Gain**

You are given a two-stage cognitive amplifier whose total chain gain must equal **6.0**. Stage 1 is the understanding pre-amp and Stage 2 is the response power stage; there is no separate evaluation stage in this minimal design.

a) Following the gain-staging principle (amplify early, while the signal is clean), assign a β to each stage so that β₁ × β₂ = 6.0 and the *front* stage carries more of the gain.
b) Explain why putting most of the gain in the *first* stage is better than putting it in the second.

**Exercise 11.3: Write the Coupling**

The following CCDL fragment chains two stages but is missing the element that keeps each stage's resting bias from contaminating the other:

```cas
cjt c1: CJT< prompt   | bias_a => understand > [β=2.0, region=active];
cjt c2: CJT< understand | bias_b => evaluate   > [β=1.0, region=active];
```

a) Name the component that belongs between `c1` and `c2`, and write the one CCDL line that inserts it (use the `Capacitor< … >` form from §5 of the style guide).
b) In one sentence, explain what it passes and what it blocks.
c) Would a *bypass* capacitor solve this same problem? Explain why or why not.

(Answers in Appendix E.)

**Exercise 11.4: Diagnose the Clip**

A single-stage cognitive amplifier is supposed to surface a faint risk signal, but the safety team reports that quiet warnings vanish entirely while strong ones come through fine. The compiler emits `E-CJT-003 CjtCutoff`.

a) In terms of the Q-point and the active region, explain what has gone wrong.
b) Is the bias set too high or too low? Justify your answer.
c) What single adjustment fixes it, and what failure would you risk if you over-corrected in the opposite direction?

(Answers in Appendix E. For the full op-amp and feedback treatment promised in this chapter, see **Chapter 16: Feedback and Operational Amplifiers**.)
