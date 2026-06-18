# Chapter 16: Feedback Systems — The Circuit That Watches Itself

In 1927 a Bell Labs engineer named Harold Black was riding the ferry to work when he scribbled an idea on the only paper he had — a page of the *New York Times*. Telephone amplifiers of the era drifted. Push a signal through a chain of them across a continent and by the far end the voices were distorted, the gain unpredictable, the whole line at the mercy of how warm the vacuum tubes happened to be that afternoon. Black's idea was almost perverse: take a slice of the amplifier's *output*, flip it upside down, and feed it back into the *input* so it fights the very signal you're trying to amplify. You throw away most of your gain on purpose. In exchange, you get an amplifier that no longer cares about the tubes — its behavior is set by a couple of resistors and nothing else. The drift vanishes. The distortion collapses. The patent office didn't believe him; they thought a perpetual-motion machine had snuck past the front desk. It took nine years to issue.

That single inverted wire — output fed back to oppose the input — is the most important idea in all of electronics, and one of the most important in this entire book. It is the difference between a circuit that merely *acts* and a circuit that *watches itself act and corrects*. Every thermostat, every cruise control, every op-amp, every stable amplifier on Earth runs on Black's inverted wire. So does every cognitive architecture that can catch its own drift before it ships.

But the same wire has an evil twin. Feed the output back so it *reinforces* the input instead of opposing it, and you don't get stability — you get a system that grabs its own tail and spins faster and faster until it slams into a wall. That is how an oscillator works. It is also how a panic attack works, how a bank run works, and how an AI conversation spirals from a mild worry into a confident catastrophe. The wire is the same. The sign is everything.

This chapter is about that sign — and about the precise, unglamorous mathematics that tells you, *before* you build anything, whether your feedback loop will settle down or scream. It is the capstone of Part III because everything we've built so far — transistors, resistors, capacitors, filters — becomes safe, predictable, and self-correcting only when wrapped in feedback. And it is the seed of Part V: the circuit that watches itself is the circuit that can be deployed.

## Open-Loop vs Closed-Loop: Why Feedback Changes Everything

Start with the distinction that organizes the whole chapter. An **open-loop** system takes an input, processes it, and produces an output — and never looks back. The output has no idea whether it was right. A toaster is open-loop: you set the dial, it heats for that long, and it has no notion of how dark your toast actually got. If the wall voltage sags, your toast comes out pale, and the toaster never knows.

A **closed-loop** system measures its own output and feeds that measurement back to the input, so the system can compare *what it produced* against *what it intended* and adjust. An oven with a thermostat is closed-loop: it measures the actual temperature, compares it to the target, and switches the heat on or off to close the gap. Sag the wall voltage and the oven simply stays on a little longer. It self-corrects, because it can see what it's doing.

The control-theory skeleton of every closed loop is one equation. Call the forward path's raw gain `A` (the "open-loop gain" — how much the amplifier multiplies its input before any feedback). Call `β` the **feedback factor** — the fraction of the output that gets routed back to the input. Then the actual, real-world gain you observe — the **closed-loop gain** — is:

```
                A
   A_closed = -------
              1 + Aβ
```

This little fraction is the engine of the entire chapter, so read it slowly. The quantity `Aβ` is the **loop gain**: how much a signal is multiplied as it travels all the way around the loop once. When the feedback opposes the input (negative feedback), `1 + Aβ` is a number bigger than one, so the closed-loop gain is *smaller* than the raw gain. You gave up gain. Here's what you bought: if `A` is enormous — and in a real op-amp it's 100,000 or more — then `Aβ` dominates the denominator, the `1` becomes negligible, and the equation collapses to `A_closed ≈ A/(Aβ) = 1/β`. The forward gain `A` *cancels out entirely*. Your gain is now set by `β` alone — by the feedback network, by a couple of resistors — and is utterly indifferent to whether `A` is 100,000 or 80,000 or drifting with temperature. That is Black's miracle in one line: **make the loop gain large and the system's behavior stops depending on the messy, drifting forward path and starts depending only on the clean, stable feedback path.**

## Negative Feedback: Output Opposes Input → Stability

Negative feedback is the inverted wire. The output is sampled, its sign flipped, and fed back to subtract from the input. The system is forever computing *error = intended − actual* and driving that error toward zero. Three gifts come with it, every time.

**Stability.** Drift in the forward path gets divided by `1 + Aβ`. A 10% wobble in `A` becomes a fraction of a percent wobble in `A_closed`. The loop swallows the forward path's sins.

**Linearity.** Real amplifiers bend — they amplify small signals more than large ones, producing distortion. Negative feedback compares output to input and corrects the bends, because a bend *is* an error, and the loop kills errors. Black's distortion collapse.

**Bandwidth extension.** An open-loop amplifier might have huge gain but only over a narrow band of frequencies. Trade some of that gain back through feedback and the *range* of frequencies it handles cleanly widens, by exactly the factor you gave up in gain. The gain-bandwidth product stays constant; feedback lets you choose where on that trade-off to sit.

### The op-amp paradigm

The cleanest embodiment of all this is the **operational amplifier** — an amplifier with two inputs (a `+` non-inverting and a `−` inverting) and one output, with a forward gain so enormous (100,000+) that we treat it as practically infinite. On its own, that gain is useless: the slightest input pins the output to its limit. Wrap it in negative feedback and it becomes the most versatile building block in analog electronics.

The canonical **non-inverting amplifier** ties the input signal to the `+` terminal and feeds a slice of the output back to the `−` terminal through a resistor divider: feedback resistor `Rf` from output to the `−` node, and `Rg` from that node to ground. The closed-loop gain works out to the cleanest formula in the field:

```
   A_closed = 1 + Rf/Rg
```

Notice what isn't in that equation: the op-amp's own gain `A`. It cancelled, exactly as the `1/β` argument promised (here `β = Rg/(Rf+Rg)`, so `1/β = 1 + Rf/Rg`). Pick `Rf = 20kΩ` and `Rg = 10kΩ` and you have a gain of exactly 3, set in metal, immune to whatever the silicon is doing. We will build precisely that circuit, in CAS, in a moment.

### The cognitive mapping

The structural role transfers directly. In a cognitive circuit, the forward path is an expansion — a CJT that takes a prompt and broadens it, surfacing interpretations and possibilities. The canonical expansion node is an `^8` **Above/Cause** state in the Cognitive domain: an Idea that triggers other Ideas to come to Mind. Left open-loop, expansion runs unchecked — every prompt blooms into a thicket of associations with nothing to prune it.

Negative feedback supplies the pruning. We sample the output of an evaluation step — a `^6` **Male** state in the Evaluative domain, the decomposition-and-test operation that takes the expanded material apart and checks whether it holds — and feed it *back* to oppose the expansion. When the evaluation finds the expansion overreaching, the fed-back signal subtracts from the drive to expand. `^6^E` evaluation tempers `^8^C` expansion. The loop computes the same error-correcting subtraction Black's amplifier does: the more the expansion overshoots, the harder the evaluation pulls it back. The result is the cognitive analog of stability and linearity — interpretations that stay proportionate to the prompt instead of ballooning.

> **Bench Note — feedback is sampled output, not a second forward stage.** A common design bug is to wire the evaluation node *forward* (`expand -> evaluate -> respond`) and call it feedback. That's a pipeline, not a loop — the evaluation never gets to *restrain* the expansion, it only inspects what already happened. True feedback routes the evaluation's output *back* to the bias of the expansion CJT, where it changes the next expansion. In CCDL the keyword is literally `feedback`, and the direction of the arrow is the whole point.

## Positive Feedback: Output Reinforces Input → Escalation

Flip the sign. Sample the output, *don't* invert it, feed it back to *add* to the input. Now `β` is effectively negative in our equation and the denominator `1 + Aβ` *shrinks*. As loop gain `Aβ` approaches `−1`, the denominator approaches zero and the closed-loop gain approaches *infinity*. The system amplifies its own output without limit. A vanishing input — even thermal noise — gets fed back, amplified, fed back again, amplified again. The output runs away to a rail and slams there (latch-up), or, if there's a phase delay in the loop, swings back and forth forever (**oscillation**).

Positive feedback isn't always a fault — controlled, it's how you build oscillators (Chapter 11), memory latches, and clean digital thresholds. But uncontrolled, it's the runaway. And it is exactly the shape of a cognitive failure we must be able to recognize and damp.

### The cognitive anxiety loop

Consider an anxiety spiral, rendered in CAS. A worry is decomposed and dwelt upon — a `^6` **Male** operation in the Evaluative domain, taking the fearful situation apart, register `|f` because it's felt, not coolly analytical. That decomposition surfaces a worse possibility by association — an `^8` **Above/Cause** trigger in the Cognitive domain, "and that reminds me it could get even worse." The catastrophized trigger feeds *back* and intensifies the original fear, which drives more frantic decomposition, which surfaces a still-worse trigger. Each lap multiplies the last. There is no `^6^E` evaluation *opposing* the loop — only `^6^E` and `^8^C` *reinforcing* each other around the circle.

```
   ^6^E|f  (decompose the fear)
      |
      v
   ^8^C    (catastrophizing trigger: "it could get worse")
      |
      +-----> feeds back to amplify ^6^E|f
```

This is positive feedback with the sign of dread. The engineering insight is liberating: you don't break an anxiety loop by arguing with any single thought. You break it by changing the *sign* of the loop — inserting a negative-feedback element that opposes the escalation instead of feeding it. That's what a grounding technique does, and it's what a cognitive circuit's damping element does. We'll build the loop *and* its damper below.

> **Anti-drift check.** The decomposition-and-dwell operation is `^6` Male — taking an Idea apart — *not* `^3` Negative. `^3` is visceral recoil, "can't stomach it." An anxiety loop isn't recoiling from the fear; it's compulsively *decomposing* it. And the "it could get worse" leap is `^8` Above/Cause (associative triggering), not deductive reasoning. Get these right or the loop's structure is mislabeled.

### The Schmitt trigger: positive feedback on a leash

Positive feedback's most domesticated form is the **Schmitt trigger** — a comparator with a sliver of positive feedback added on purpose to give it **hysteresis**. A plain comparator flips its output the instant the input crosses a single threshold; near that threshold, noise makes it chatter, flipping wildly back and forth. The Schmitt trigger uses positive feedback to make the *output* shift the threshold: once it flips high, the threshold to flip back *low* moves down, so the input must travel a clear distance before the next flip. Two thresholds, a dead band between them, no chatter. The positive feedback is strong enough to snap the output decisively but bounded by the resistor ratio so it can't run away. In a cognitive circuit this is exactly how you want a *commitment* to behave: once a refusal latches, a small contrary nudge shouldn't unlatch it — the threshold to reverse should sit well below the threshold that triggered it. Controlled positive feedback gives a decision *backbone*.

## The Bode Plot: Gain and Phase vs Frequency

Whether a feedback loop stabilizes or screams comes down to one question: *how does the loop gain `Aβ` behave as the signal frequency changes?* A real amplifier doesn't have one fixed gain. At low frequencies its gain is high; past some corner it starts falling; and crucially, it also **delays** the signal — and the delay grows with frequency. That delay is measured as **phase shift**: how many degrees the output lags the input. The tool that shows both at once is the **Bode plot** (pronounced *boh-dee*, after Hendrik Bode), and learning to read it is the core skill of this chapter.

A Bode plot is two stacked graphs sharing a horizontal frequency axis, drawn on a logarithmic scale so that decades of frequency fit on one page:

- **Top graph: gain vs frequency.** Vertical axis in decibels (dB) — a logarithmic measure where every 20 dB is a 10× change in gain. Flat at the left (full gain), then sloping down past each corner frequency.
- **Bottom graph: phase vs frequency.** Vertical axis in degrees, running from 0° down toward −180° and beyond. Each corner adds up to −90° of lag.

Here is why it matters from first principles. Negative feedback works by *opposing* the input — that opposition is a 180° phase relationship built into the inverted wire. Now suppose the amplifier itself adds *another* 180° of phase lag at some high frequency. The intended-opposite feedback, lagged by a further 180°, arrives back *in phase* with the input. Negative feedback has silently become positive feedback. If the loop gain is still 1 or more at that frequency, the runaway condition `Aβ = −1` is met and the circuit oscillates. **The whole game is to make sure the gain has dropped below 1 before the phase lag reaches −180°.**

A single corner (one pole — the frequency where a stage's gain starts falling) contributes a gain slope of −20 dB per decade and asymptotically −90° of phase. *One* corner can never reach −180°, so a single-pole amplifier is unconditionally stable — it cannot oscillate, no matter how much feedback you apply. The trouble starts with *two* corners. Two poles can stack to −180°, and now stability is a real question. A two-stage amplifier — like the two-stage CJT amplifier in this chapter's marquee exercise — has at least two poles, and is exactly where Bode analysis earns its keep.

```{=latex}
\begin{center}
\begin{tikzpicture}
\begin{groupplot}[
    group style={group size=1 by 2, vertical sep=6mm,
      xticklabels at=edge bottom, x descriptions at=edge bottom},
    casaxis, width=10.6cm, height=4.4cm,
    xmode=log, xmin=10, xmax=1e7, log basis x=10,
    xtick={10,100,1000,1e4,1e5,1e6,1e7},
    xticklabels={10,100,1k,10k,100k,1M,10M},
  ]
  % TOP: magnitude (dB) -- flat 60 dB to 1k, -20 dB/dec to 100k, -40 dB/dec above
  \nextgroupplot[ylabel={magnitude (dB)}, ymin=-50, ymax=70,
      ytick={-40,-20,0,20,40,60}]
    \addplot[casCedge, line width=1.1pt] coordinates {
      (10,60) (1000,60) (1e5,20) (1e7,-60) };
    \draw[casNedge, line width=0.4pt, densely dashed] (axis cs:10,0) -- (axis cs:1e7,0);
    \addplot[only marks, mark=*, mark size=1.6pt, black] coordinates {(3.16e5,0)};
    \node[font=\sffamily\scriptsize, anchor=south west] at (axis cs:3.4e5,1) {0\,dB crossover};
    \draw[casNedge, line width=0.4pt, densely dotted] (axis cs:1e6,-50) -- (axis cs:1e6,70);
    \addplot[only marks, mark=square*, mark size=1.6pt, casEedge] coordinates {(1e6,-20)};
    \draw[{Latex[length=1.6mm]}-{Latex[length=1.6mm]}, casEedge, line width=0.7pt]
      (axis cs:1e6,0) -- (axis cs:1e6,-20);
    \node[casEedge, font=\sffamily\scriptsize, anchor=east] at (axis cs:8e5,-10)
      {gain margin $\approx$ 20\,dB};
    \node[font=\sffamily\scriptsize\bfseries, anchor=north west] at (axis cs:12,68) {Gain};
  % BOTTOM: phase (deg) -- 0 to -45 at 1k, -135 at 100k, -180 ~1M
  \nextgroupplot[ylabel={phase (deg)}, xlabel={frequency (log)},
      ymin=-200, ymax=10, ytick={0,-45,-90,-135,-180}]
    \addplot[casOedge, line width=1.1pt, smooth] coordinates {
      (10,0) (100,-3) (1000,-45) (1e4,-78) (1e5,-135) (1e6,-177) (1e7,-180) };
    \draw[casNedge, line width=0.4pt, densely dashed] (axis cs:10,-180) -- (axis cs:1e7,-180);
    \draw[casNedge, line width=0.4pt, densely dotted] (axis cs:1e6,-200) -- (axis cs:1e6,10);
    \addplot[only marks, mark=*, mark size=1.6pt, black] coordinates {(1e6,-177)};
    \node[font=\sffamily\scriptsize, anchor=south east] at (axis cs:9e5,-175)
      {$-180^\circ$ crossing ($\approx$1\,MHz)};
    \addplot[only marks, mark=triangle*, mark size=1.8pt, casCedge] coordinates {(3.16e5,-150)};
    \draw[{Latex[length=1.6mm]}-{Latex[length=1.6mm]}, casCedge, line width=0.7pt]
      (axis cs:3.16e5,-180) -- (axis cs:3.16e5,-150);
    \node[casCedge, font=\sffamily\scriptsize, anchor=east] at (axis cs:2.4e5,-115)
      {phase margin $\approx$ 30$^\circ$};
    \node[font=\sffamily\scriptsize\bfseries, anchor=north west] at (axis cs:12,5) {Phase};
\end{groupplot}
\end{tikzpicture}
\end{center}
```

Lay the two graphs over each other and the stability question becomes geometric: at the frequency where the gain curve crosses 0 dB (gain = 1), *how far is the phase from −180°?* And at the frequency where the phase hits −180°, *how far is the gain below 0 dB?* Those two distances have names.

## Phase Margin and Gain Margin: How Close to the Edge

**Phase margin** is the safety cushion on phase. Find the frequency where the loop gain crosses 0 dB (called the *gain crossover*). Read the phase there. The phase margin is how many degrees that phase sits *above* −180°:

```
   phase margin = 180° + (phase at the 0-dB crossover)
```

If the phase at crossover is −120°, the phase margin is 60°. That's a comfortable, well-behaved design. A phase margin of 45° is the usual minimum for a clean response; below ~30° the system *rings* — it overshoots and oscillates a few times before settling; at 0° it oscillates forever. Negative phase margin means it's already unstable.

**Gain margin** is the mirror cushion, measured on gain. Find the frequency where the phase hits −180° (the *phase crossover*). Read the gain there. The gain margin is how many dB the gain sits *below* 0 dB:

```
   gain margin = 0 dB − (gain at the −180° crossover)
```

If the gain at the −180° point is −12 dB, the gain margin is 12 dB — you could multiply the loop gain by 4× before it reached the runaway threshold. A gain margin of 6–12 dB is the typical target. A small or negative gain margin says the loop is one disturbance away from screaming.

> **Bench Note — margins are design constructs, not measurements.** Everything in this section — the Bode curves, the phase and gain margins, the −180° crossover — is *analytical*. You compute it from the circuit's poles before you build, the way you compute load on a beam before you pour concrete. Nothing here is a measured result from a running model, and the chapter never claims it is. When you see a phase margin quoted for a cognitive circuit in this book, read it as "this is what the design math predicts," not "this is what we observed in a deployed system."

## The Nyquist Criterion: Encircling −1

Bode plots are the working engineer's everyday tool, but the deepest statement of stability is the **Nyquist criterion**, and it's worth knowing because it makes the −1 condition vivid. Take the loop gain `Aβ` and plot it as a single curve on the complex plane — for every frequency from zero to infinity, mark the point whose distance from the origin is the gain and whose angle is the phase. As frequency sweeps, that point traces a closed loop called the **Nyquist plot**.

The criterion is almost shockingly simple to state: **if that curve encircles the point −1 (that is, the point at distance 1, angle −180°), the closed-loop system is unstable.** Encircle −1 and it screams; stay clear of −1 and it's stable. Phase margin and gain margin are just two measurements of *how close the curve passes to −1* — the phase margin is the angle by which the curve clears −1 as it crosses the unit circle; the gain margin is how short the curve falls of −1 as it crosses the negative-real axis. The point −1 is the cliff edge. The entire discipline of feedback design is the art of routing your loop-gain curve safely around that one point.

## Compensation: Rolling Off Gain Before the Phase Turns

What do you do when the analysis says your loop *will* oscillate — gain still above 1 when phase hits −180°? You **compensate**: deliberately reshape the gain curve so it crosses 0 dB *earlier*, before the phase has had a chance to reach −180°. The standard move is to add capacitance at a well-chosen node, creating a new dominant pole at a low frequency. (Recall from Chapter 8 that a capacitor and resistor form a low-pass filter whose corner is where gain begins rolling off.) That low corner pulls the whole gain curve down sooner, so it reaches 0 dB while there's still healthy phase margin. You sacrifice high-frequency gain — bandwidth — to buy stability. It's the same trade as always: give up reach to gain control. Every op-amp you buy has a compensation capacitor built into it for exactly this reason; that's what makes it "unconditionally stable" and safe to drop into a feedback circuit without a stability analysis every time.

The cognitive analog is **slowing the loop down on purpose**. An expansion-evaluation loop that reacts to every flicker of new information can chase its own tail. Adding the cognitive equivalent of a compensation capacitor — a `Capacitor< … >` element on the feedback node that stores and smooths the evaluation signal so it can't swing too fast — gives the loop the same low dominant pole. The evaluation feedback responds to the *trend* of the expansion, not its every twitch. The circuit becomes deliberate instead of jittery. We damp the oscillator below with exactly this technique.

## Worked Build 1: A Negative-Feedback Amplifier, Closed-Loop Gain = 3

We'll build the cognitive twin of the non-inverting op-amp with gain 3. The forward path is a high-gain expansion CJT (our "op-amp"). The feedback path samples an evaluation node and feeds it back to oppose the expansion, set so the closed-loop gain lands at exactly 3.

Recall the op-amp formula: `A_closed = 1 + Rf/Rg`. For a gain of 3 we need `Rf/Rg = 2`. In CAS feedback terms, the feedback factor is `β = Rg/(Rf+Rg) = 1/3`, and with large forward gain the closed-loop gain is `1/β = 3`. So we set the forward CJT's open-loop gain high and the feedback path's `β = 0.333`.

```cas
circuit nfb_amplifier_gain3 {
    input:  prompt;
    output: response;

    // Forward path: high-gain expansion ("the op-amp")
    node expand:          ^8^C_{F2}|A;     // Above/Cause: surface interpretations
    node evaluate:        ^6^E_{F6}|A;     // Male: decompose-and-test the expansion
    node respond:         ^9^C_{F2}|A;     // Below/Effect: the produced conclusion
    node bias_principles: ^5^P_{F7}|T;     // Female: accumulated substrate / bias

    // High open-loop gain — the forward path is deliberately "too hot"
    cjt c_fwd: CJT< prompt   | bias_principles => expand   > [β=12.0];
    cjt c_eval: CJT< expand  | bias_principles => evaluate > [β=1.5];
    cjt c_out:  CJT< evaluate| bias_principles => respond  > [β=1.0];

    // Negative feedback: sample evaluation, oppose the expansion.
    // β = 1/3 → closed-loop gain = 1 + Rf/Rg = 3
    feedback evaluate -> expand [β=0.333];

    probe tp_fwd:  expand;     // watch the raw, hot expansion
    probe tp_out:  evaluate;   // watch the tempered, fed-back result
}
```

Walk it line by line. The forward CJT `c_fwd` has `β=12.0` — an aggressive, unstable-on-its-own expansion, our stand-in for the op-amp's runaway open-loop gain. Left alone it would blow every prompt out of proportion. The `feedback evaluate -> expand [β=0.333]` line is Black's inverted wire: it samples the evaluation node and routes one-third of it back to *oppose* the expansion's bias. By the closed-loop formula, the observed gain settles to `1/β = 3`, regardless of whether the forward `β` is 12 or 10 or drifting — the loop divides out the forward path's volatility. The two probes let you see the contrast: `tp_fwd` shows the hot raw expansion, `tp_out` shows the disciplined result after feedback. Gain of exactly 3, set by the feedback factor, immune to the forward path. This is the current-limited, self-stabilizing topology that the CSB's reasoning rail uses in Chapter 18.

> **Bench Note — keep the loop gain large.** The gain only locks to `1/β` when the forward `β` is much larger than `1/β`. Here forward `β=12` against a target of 3 — a loop gain of 4×, enough to make the forward path's drift negligible. If you set the forward `β` only slightly above 3, the `1` in `1 + Aβ` stops being negligible and your gain wanders with the forward path. Hot forward path, gentle feedback: that's the recipe for a stable, drift-immune amplifier.

## Worked Build 2: A Positive-Feedback Oscillator That Escalates Unless Damped

Now the evil twin: the anxiety loop. Same two operations — decomposition and triggering — but wired to *reinforce* instead of oppose. Then we add the damper.

```cas
circuit anxiety_oscillator {
    input:  worry;
    output: spiral;

    node decompose:  ^6^E|f;          // Male, felt: take the fear apart, dwell on it
    node catastroph: ^8^C;            // Above/Cause: "it could get worse" trigger
    node bias_state: ^5^P_{F3}|f;     // Female: the anxious substrate

    cjt c_dec: CJT< worry      | bias_state => decompose  > [β=1.4];
    cjt c_cat: CJT< decompose  | bias_state => catastroph > [β=1.4];

    // POSITIVE feedback: the catastrophe trigger AMPLIFIES the decomposition.
    // Loop gain = 1.4 × 1.4 × 1.6 ≈ 3.1 > 1  → runaway escalation.
    feedback catastroph -> decompose [β=1.6];

    probe tp_loop: catastroph;        // watch the spiral climb each lap
}
```

The fault is the `feedback catastroph -> decompose [β=1.6]` line. Because `β` is positive *and* the feedback adds to (rather than opposes) the decomposition, and because the loop gain `1.4 × 1.4 × 1.6 ≈ 3.1` exceeds 1, every lap multiplies the last. The probe `tp_loop` would show the catastrophizing climbing each cycle until it saturates at a rail — the cognitive picture of a panic spiral, or of an AI conversation that talks itself from mild caution into confident doom. This is the structural signature the compiler flags as a short-circuit / runaway condition (`W-CJT-006`-class).

Now damp it. We change the *sign* of the loop — turn reinforcement into opposition — and add a compensation capacitor so the feedback responds to the trend, not every twitch:

```cas
circuit anxiety_damped {
    input:  worry;
    output: settled;

    node decompose:  ^6^E|f;
    node catastroph: ^8^C;
    node evaluate:   ^6^E_{F6}|A;     // Male, analytical: cool decompose-and-test
    node bias_state: ^5^P_{F2}|T;     // Female substrate, weighted toward Wisdom

    cjt c_dec: CJT< worry     | bias_state => decompose  > [β=1.4];
    cjt c_cat: CJT< decompose | bias_state => catastroph > [β=1.4];
    cjt c_ev:  CJT< catastroph| bias_state => evaluate   > [β=1.0];

    // Compensation: smooth the feedback so it can't swing too fast (dominant pole).
    cap comp: Capacitor< ^6^E_{F6}|A, C=120, leakage=0.02 >;

    // NEGATIVE feedback: analytical evaluation OPPOSES the decomposition.
    // β chosen so loop gain stays < 1 with comfortable margin.
    feedback evaluate -> decompose [β=0.45];

    probe tp_loop: catastroph;
    probe tp_damp: evaluate;
}
```

Two changes break the spiral. First, an **analytical** evaluation node (`^6^E_{F6}|A` — cool decompose-and-test, register `|A`, not the felt `|f`) is inserted and its output fed *back to oppose* the decomposition: negative feedback. Second, the `Capacitor` on the evaluation node is the compensation cap — it stores and smooths the feedback signal so the loop reacts to the overall trend of the catastrophizing rather than chasing each twitch, giving the loop a low dominant pole and healthy phase margin. With the loop gain now below 1, the spiral converges instead of climbing. The probes show it: `tp_loop` settles, `tp_damp` shows the steadying analytical opposition doing its work. That is the engineering of "talking yourself down," rendered as a circuit.

## Datasheet: Feedback Parameters

| Parameter | Symbol | Meaning | Typical / safe range |
|---|---|---|---|
| Open-loop gain | `A` | Raw forward-path gain before feedback | Large (≫ target gain) |
| Feedback factor | `β` | Fraction of output routed back | `0 < β ≤ 1` (neg. fb) |
| Loop gain | `Aβ` | Gain once around the loop | `≫ 1` for neg. fb to lock |
| Closed-loop gain | `A_closed` | `A / (1 + Aβ)` ≈ `1/β` | Set by `β` alone |
| Phase margin | `PM` | `180° + phase at 0-dB crossover` | `≥ 45°` clean; `< 30°` rings |
| Gain margin | `GM` | dB below 0 dB at −180° crossover | `6–12 dB` |
| Runaway condition | — | `Aβ = −1` (encircles −1 on Nyquist) | Avoid by design |
| Compensation cap | `C` | Adds dominant pole; rolls off gain early | Sized to set 0-dB before −180° |

## Failure Modes

| Failure | Symptom | Structural cause | Detection / fix |
|---|---|---|---|
| **Oscillation** | Output rings or never settles | Loop gain > 1 when phase hits −180° | Add compensation cap; lower loop gain |
| **Latch-up** | Output pins to a rail and stays | Positive feedback, loop gain ≫ 1 | Change loop sign to negative; add bound |
| **Wrong-sign feedback** | "Feedback" that escalates instead of damping | Feedback adds to input instead of opposing | Verify the loop *opposes* deviation |
| **Loop gain too low** | Gain wanders with forward path | Forward `β` not ≫ target `1/β` | Raise forward gain so `Aβ ≫ 1` |
| **Pipeline-not-loop** | Inspection never restrains the cause | Eval wired forward, not fed back | Route eval output back to the cause's bias |
| **Insufficient phase margin** | Overshoot, ringing before settling | Two poles too close; PM < 30° | Compensate; separate the poles |

## The Self-Improving Circuit: Monitoring Its Own β

We end where Part V begins. Everything above is static design — you compute the margins once, build the loop, ship it. But the most powerful feedback loop is the one that operates on the circuit *itself*, over time, slower than the signal loop. A real amplifier's gain `β` drifts as components age. A truly self-maintaining amplifier would *measure its own `β` periodically* and re-trim its bias to hold the design value — a feedback loop wrapped around the feedback loop, correcting the corrector.

A cognitive circuit can do the same, and this is the seed of the **Continual Harness** used in deployment (Chapter 25). The signal loop runs fast: every response is shaped by the `^6^E` evaluation tempering the `^8^C` expansion. A second, slower loop runs over the *trajectory* of many responses:

1. **Trajectory review** — log the circuit's outputs over time, not one at a time.
2. **Failure-signature detection** — scan the trajectory for the structural signatures we've catalogued: rising loop gain, shrinking phase margin, the runaway escalation pattern of Worked Build 2, drift in the closed-loop gain away from its design value.
3. **Bias adjustment** — when a signature is detected, re-trim the bias substrate (`^5` Female — the accumulated formation) or tighten a feedback factor to restore the margins. The slow loop adjusts the parameters the fast loop runs on.

This is the same architecture as the self-trimming amplifier, one level up: the fast loop stabilizes each response; the slow loop stabilizes the *circuit's behavior across responses*, catching drift before it becomes a deployed failure. It is also the feedback path on the CSB itself — the `O → P` route from Chapter 2, where the consequences of operational outputs feed back up to re-tune the principled bias. The Continual Harness is that `O → P` path made into a standing process, and Chapter 18 wires it onto the board.

> **Honesty note.** The Continual Harness is a *design* — trajectory review, signature detection, bias adjustment as an architecture. Its failure-signatures are the analytical patterns of this chapter (loop gain, phase margin, the runaway shape), not measured statistics from a running deployment. Build it as a design and the margins tell you where to look; never report a margin or a detected drift as an observed model result it isn't.

## Key Takeaways

- **Open-loop acts blind; closed-loop watches its own output and corrects.** The governing equation is `A_closed = A / (1 + Aβ)`. Make loop gain `Aβ` large and behavior depends on the clean feedback path (`1/β`), not the drifting forward path.
- **Negative feedback opposes deviation** → stability, linearity, bandwidth extension. The op-amp non-inverting gain is `1 + Rf/Rg`. Cognitive analog: `^6^E` (Male) evaluation fed back to temper `^8^C` (Above/Cause) expansion.
- **Positive feedback reinforces deviation** → oscillation, escalation, latch-up. Cognitive analog: the anxiety loop, `^6^E|f` decomposition → `^8^C` catastrophizing trigger → more fear. The Schmitt trigger is positive feedback leashed by hysteresis — controlled, decisive, bounded.
- **The Bode plot** shows gain (dB) and phase (degrees) vs frequency. Oscillation happens when loop gain is still ≥ 1 at the frequency where phase reaches −180°. One pole is always stable; two poles can reach −180°.
- **Phase margin** = how far phase clears −180° at the 0-dB crossover (want ≥ 45°). **Gain margin** = how far gain sits below 0 dB at the −180° crossover (want 6–12 dB). The **Nyquist criterion**: encircling −1 in the complex plane = unstable.
- **Compensation** adds a capacitor to roll gain off *before* phase hits −180°, trading bandwidth for stability. Cognitive analog: smoothing the feedback so the loop responds to the trend, not every twitch.
- **The self-improving circuit** wraps a slow loop around the fast one — monitoring its own `β`, recalibrating bias. This is the **Continual Harness** (trajectory review → failure-signature detection → bias adjustment), the foundation of deployment self-monitoring (Chapter 25) and the CSB feedback path (Chapter 18).
- **Honesty:** Bode curves, margins, and harness signatures are analytical *design* constructs computed before the build — never measured model results. Canonical Noetic names throughout: `^6` is **Male**, `^8` is **Above/Cause**.

---

## Exercises

**Exercise 16.1: Set the Gain**

You need a negative-feedback cognitive amplifier with a closed-loop gain of **5** (instead of the gain-3 build above). Using the op-amp formula `A_closed = 1 + Rf/Rg`:

a) What ratio `Rf/Rg` do you need?
b) What feedback factor `β` should the `feedback … -> … [β=…]` line carry?
c) Roughly how large should the forward CJT's `β` be for the loop to lock cleanly to gain 5? Explain in one sentence why "a little above 5" is not enough.

**Exercise 16.2: Diagnose the Sign**

A junior engineer's circuit oscillates uncontrollably. They show you this feedback line and insist it's negative feedback:

```cas
feedback catastroph -> decompose [β=1.6]
```

a) Is this negative or positive feedback, and how can you tell from the *role* of the two nodes (not just the number)?
b) The forward CJTs have `β=1.4` each. Compute the loop gain and state whether the loop runs away.
c) Give the *two* changes that damp it (one about the loop's sign, one about its speed). (Answers in Appendix E.)

**Exercise 16.3: Write the Damped Loop**

Write a CCDL `circuit` block for a feedback loop that takes an over-eager expansion (`^8^C_{F2}|A`, forward `β=10`) and tempers it with an analytical evaluation (`^6^E_{F6}|A`) fed back to oppose it, with a compensation capacitor on the evaluation node, targeting a closed-loop gain of **4**. Include at least one `probe`. (One valid answer in Appendix E; the load-bearing checks are: the feedback *opposes* the expansion, `β = 1/4 = 0.25`, and a `Capacitor` sits on the feedback node.)

**Exercise 16.4 (Marquee): Plot the Two-Stage CJT Bode Response**

Take a two-stage CJT amplifier whose two stages contribute corner frequencies (poles) at **1 kHz** and **100 kHz**, with a combined low-frequency loop gain of **60 dB**. Each pole contributes −20 dB/decade of gain roll-off and asymptotically −90° of phase.

a) Sketch the Bode gain and phase plots (you may reuse this chapter's ASCII style).
b) **At what frequency does the phase reach −180°?** (Both poles contribute their full −90° well above the second corner.)
c) Read the gain at that frequency off your gain plot. **What is the gain margin** — how many dB below 0 dB does the gain sit when phase hits −180°? Is this a stable design, and if not, what single compensation move fixes it?

(Answer in **Appendix E.** Remember: these are analytical design figures, not measured results. For the one-page notation reference, see **Appendix A: the CAS Quick-Reference Card.**)
