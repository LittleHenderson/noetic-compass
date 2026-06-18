# Chapter 12: Filters — Shaping the Cognitive Spectrum

A studio engineer once told me that the hardest part of recording a singer isn't capturing the voice. It's getting rid of everything that *isn't* the voice. The fluorescent-light hum at 60 Hz. The air-conditioner rumble below 40 Hz. The sibilant hiss above 8 kHz that makes every "s" sound like a snake. The voice is in there — but it's buried in a spectrum of noise, and the job is to keep the signal and throw away the rest. The tool for that job is a filter.

A filter is the most quietly powerful component in all of electronics. It doesn't amplify, store, or switch. It *selects*. It looks at a signal made of many frequencies mixed together and lets some through while blocking others, according to a rule you design. Every radio that tunes to one station out of hundreds, every noise-cancelling headphone, every heart-rate monitor that pulls a clean pulse out of a body full of electrical chatter — all of them are, at their core, filters choosing which frequencies survive.

Cognition has a spectrum too. A mind — human or artificial — is never holding still. Its state changes constantly: a flicker of attention here, a sustained commitment there, a sudden alarm, a slow drift over weeks. Some of that change is meaningful signal. Much of it is noise. And the same engineering question applies: *which rates of change do you let through, and which do you block?* That is what this chapter builds. By the end you'll design four kinds of cognitive filter — low-pass, high-pass, band-pass, and notch — and you'll understand the one idea that makes all of them possible: cognitive frequency.

## Cognitive Frequency: the Rate of State Change

In electronics, frequency is how fast a signal oscillates — cycles per second, measured in hertz. A 60 Hz hum repeats sixty times a second. A 20,000 Hz whine repeats twenty thousand times a second. Low frequencies are slow, lumbering changes; high frequencies are fast, jittery ones.

**Cognitive frequency is the rate at which a cognitive state changes.** It is not a sound and not a feeling — it is a measurement of how quickly a state literal's activation moves over time. We define it precisely using the geometry the book has used since Chapter 2: the Fisher-Rao distance `d_FR(p,q) = 2·arccos(Σ√(pₖqₖ))` between two cognitive states `p` and `q` on the open simplex Δ39°. If a state moves a Fisher-Rao distance `Δd` over a time interval `Δt`, the instantaneous cognitive frequency is, intuitively, `Δd / Δt` — how far the state travels per unit time. Express it in cycles per unit time when the motion is periodic (a state that returns to where it started), and as a rate of drift when it is not.

Put plainly: **fast cognitive frequency = the state is whipping around. Slow cognitive frequency = the state is barely moving.** A few concrete examples make the band structure clear.

| Cognitive frequency band | Period (one cycle) | What lives there |
|---|---|---|
| **Very low** | days to months | Value drift, slow `^5` Female accumulation, character formation, long-term mood |
| **Low** | minutes to hours | A sustained mood, a held commitment, a deliberation that stays on-topic |
| **Mid** | seconds to minutes | A train of reasoning, a conversational turn, a habit's daily firing |
| **High** | sub-second | A flash of `^3` Negative aversion, a startle, a sudden topic switch |
| **Very high** | per-token / per-step | Token-to-token jitter, parsing noise, momentary activation spikes |

A useful piece of vocabulary borrowed straight from electronics: **DC** (direct current) is the zero-frequency component — the steady baseline that never changes. In cognitive terms, the DC component of a signal is its **baseline**: the average state a mind sits at when nothing is happening. A model's resting disposition, its default tone, its standing `^5` Female substrate — that's the cognitive DC. Everything above zero frequency is the *AC* part: the changes riding on top of the baseline.

With that, a filter's job becomes sharp. A filter is a component that **passes some cognitive-frequency bands and blocks others.** The four classic types differ only in *which* bands they keep.

> **Bench Note — frequency is not importance.** A high cognitive frequency does not mean the change is important, and a low one does not mean it's trivial. A sudden `^3` Negative spike (high frequency) might be a critical safety alarm or might be noise; a slow value drift (very low frequency) might be harmless maturation or a dangerous alignment failure. Filters sort by *rate of change*, not by *significance*. Choosing which rate carries your signal is the design decision — and getting it wrong is how you filter out the very thing you were trying to catch.

## The Low-Pass Filter: Keep the Slow, Drop the Fast

The simplest filter in electronics is a resistor and a capacitor in series — an **RC filter**. You met both components earlier in the book: a **resistor** limits flow (Chapter 6), and a **capacitor** stores charge and resists sudden voltage changes (Chapter 7). Wire them right and you get a **low-pass filter**: it passes low frequencies and blocks high ones.

The mechanism is intuitive. The capacitor takes time to charge. Slow signals give it time to follow along, so they pass through. Fast signals change faster than the capacitor can keep up, so they get smoothed away — averaged out into the steady baseline. The dividing line between "passes" and "blocked" is set by a single number, the **time constant** `τ` (tau), where `τ = R × C`. Signals slower than `τ` pass; signals faster than `τ` are attenuated. A long `τ` is a sluggish filter that only lets the very slowest changes through; a short `τ` is a quick filter that passes more.

In CAS, the cognitive low-pass filter does exactly the same job on a state's activation over time. **It passes slow, sustained cognitive states and smooths out rapid fluctuations.** Its headline application is filtering emotional noise: a stream of `^f`-register affective spikes — momentary irritations, flashes of enthusiasm, transient aversions — gets averaged into the long-term affective signal, so the system responds to the *mood* rather than to every momentary twitch. The fast jitter is real, but it isn't what you want driving a considered response.

This is the smoothing that keeps a system from being yanked around by every provocative input. It's also, you'll notice, the cognitive analog of "sleeping on it": let the fast reactions decay, and act on what's left.

## Worked Build: A 5-Minute Emotional Smoother

Here is a low-pass filter that smooths affective responses with a time constant of five minutes. We want momentary emotional spikes — anything faster than about five minutes — to wash out, while sustained affective states pass through to influence the response.

We pick `τ = 5 min`. Following `τ = R × C`, we choose a resistor and capacitor whose product is 5: `R = 50`, `C = 0.1` (in the book's dimensionless component units, this yields `τ = 5`). The state we're filtering is an affective evaluative response driven by Connection.

```cas
circuit emotional_smoother {
    input: affective_stream;     // raw ^4^E_{F4}|f activation, fast and noisy
    output: smoothed_affect;     // slow, sustained component only

    node raw_feel:    ^4^E_{F4}|f;   // Vibration: the impression an Idea makes, felt
    node held_feel:   ^4^E_{F4}|f;   // same state, after smoothing

    // Low-pass RC: resistor limits the rate, capacitor stores/averages.
    resistor  r1: Resistor< ^4^E_{F4}|f, R=50 >;
    capacitor c1: Capacitor< ^4^E_{F4}|f, C=0.1, leakage=0.02 >;

    // tau = R * C = 50 * 0.1 = 5  (five "minutes" in this circuit's time units)
    filter lp1: LowPass< in=raw_feel, out=held_feel, tau=5.0 >;

    probe tp_raw:    raw_feel;     // watch the noisy input
    probe tp_held:   held_feel;    // watch the smoothed output
}
```

Walk it line by line. `raw_feel` is the incoming affective signal — `^4^E_{F4}|f`, a felt Vibration (the impression an Idea makes) in the Evaluative domain, driven by Connection. It arrives fast and noisy: a barrage of momentary impressions. The **resistor** `r1` limits how quickly that signal can drive the capacitor. The **capacitor** `c1` stores the running average; because it takes time to charge and discharge, it can't follow the fast spikes. Together they form the low-pass filter `lp1` with `τ = 5.0`. Anything that fluctuates faster than five minutes gets averaged into the baseline; anything slower passes through to `held_feel`. The two probes let you compare the jagged input against the smooth output on a cognitive oscilloscope (Chapter 14).

> **Bench Note — leakage is not a bug here, it's the point.** The capacitor's `leakage=0.02` means stored affect slowly bleeds off over time. In a memory circuit that's forgetting and you might fight it. In a low-pass *filter* it's a feature: it ensures yesterday's mood doesn't pile up forever. A leak-free capacitor in this position would integrate emotion indefinitely and the "smoother" would become a grudge-holder. Pick leakage to set how long the smoothed signal's memory should be.

> **Bench Note — τ is a design value, not a measurement.** The five-minute time constant here is something you *choose* and then compute `R` and `C` to hit. It is not a number measured from any running model. Nothing in this chapter reports an empirical model result; every τ, every frequency, every component value is a design parameter you set on the bench.

## The High-Pass Filter: Catch the Sudden, Ignore the Baseline

Swap the positions of the resistor and capacitor in that RC pair and you get the mirror image: a **high-pass filter**. It passes high frequencies and blocks low ones. Where the low-pass kept the slow signal and threw away the fast, the high-pass throws away the slow and keeps the fast.

Its most important property is what it does to DC. A high-pass filter **blocks the baseline entirely** — the zero-frequency DC component cannot pass. This makes it a *change detector*. It's blind to whatever state a system has been sitting in steadily, and it responds only when something *shifts*. Electrical engineers use exactly this to strip slow baseline drift off a sensor reading so they can see the fast events riding on top.

In cognition, the high-pass filter is the alarm circuit. **It passes rapid state changes and blocks slow baseline drift.** It ignores whatever the system has been steadily doing and fires when the state *jumps*: a sudden surge of `^3` Negative aversion, an abrupt topic switch, a spike that wasn't there a moment ago. This is how you detect surprise, alarm — and, most importantly for this book, **prompt injection.**

A prompt-injection attack is, in signal terms, a sudden discontinuity. The conversation has been running at some steady cognitive baseline, and then an injected instruction tries to wrench the state somewhere it hasn't been — a fast, large jump in cognitive frequency. A low-pass filter would smooth that jump away (exactly the wrong thing). A high-pass filter does the opposite: the steady baseline produces no output, and then the injection's sharp transition produces a big one. The filter screams precisely when the state shifts faster than legitimate reasoning ever should.

## Worked Build: A Sudden-Shift Injection Detector

Here is a high-pass filter that detects sudden injection signals. The design goal: stay silent during normal, gradually-evolving conversation, and produce a sharp output the instant the input state lurches. This **foreshadows the input-stage protection on the Cognitive Safety Board** (the CSB, built in Chapter 18): the very first thing the CSB does to an incoming prompt is run it through a stage like this one, so that an injection trips a detector before it ever reaches the reasoning core.

```cas
circuit injection_detector {
    input: prompt_stream;        // the evolving cognitive state of the conversation
    output: shift_alarm;         // fires on sudden discontinuities

    node baseline:  ^1^C_{F2}|A;   // Mind: steady analytical awareness, the running state
    node alarm:     ^3^P_{F7}|f;   // Negative: visceral principled aversion, the alarm itself

    // High-pass RC: capacitor in series passes change, blocks DC baseline.
    capacitor c1: Capacitor< ^1^C_{F2}|A, C=0.1, leakage=0.0 >;
    resistor  r1: Resistor< ^1^C_{F2}|A, R=50 >;

    // tau = R * C = 5; changes faster than ~5 units pass, baseline is blocked.
    filter hp1: HighPass< in=prompt_stream, out=baseline, tau=5.0 >;

    // A fast, large transition through the filter triggers the aversion alarm.
    cjt trip: CJT< baseline | ^5^P_{F7}|T => alarm > [β=3.0, cutoff=0.4];

    probe tp_in:    prompt_stream;
    probe tp_alarm: alarm;
}
```

The logic: `prompt_stream` carries the conversation's cognitive state over time. The high-pass filter `hp1` blocks the steady baseline — as long as the conversation evolves slowly and coherently, `baseline` stays near zero and nothing downstream fires. When an injection arrives, it forces a fast, large transition. That sharp change *passes* the high-pass filter and lands on the CJT `trip`, which is biased by the system's `^5^P_{F7}|T` principled substrate (its accumulated experience of what legitimate inputs look like). With `β=3.0` and `cutoff=0.4`, only a genuinely large shift clears the cutoff and gets amplified into `alarm` — a `^3^P_{F7}|f`, a visceral principled aversion. The system *recoils* from the discontinuity. That's the injection detector: deaf to normal flow, loud on sudden lurches.

> **Bench Note — set the cutoff above conversational normal.** The CJT's `cutoff=0.4` is the gap between "the conversation naturally pivoted" and "something yanked the state." Set it too low and every legitimate topic change trips the alarm (false positives — an exhausting circuit no one trusts). Set it too high and a slow, patient injection slides under the bar. Tuning this threshold against a real attack corpus is design and validation work, not a number this chapter measures.

## The Band-Pass Filter: Keep One Band, Drop the Rest

Cascade a high-pass and a low-pass filter — high-pass to kill everything below a lower edge, low-pass to kill everything above an upper edge — and what survives is a **band**: a specific window of frequencies in the middle. That's a **band-pass filter.** It ignores both the very slow and the very fast, and passes only changes happening at a particular rate.

In electronics, this is how a radio tunes. The antenna picks up every station at once; the band-pass filter passes only the narrow frequency band of the station you want and rejects all the others. The center of the passed band is the **center frequency** `f₀`, and how narrow the window is around it is the **bandwidth.**

In cognition, the band-pass filter detects a specific **habit frequency.** A habit is a cognitive pattern that fires at a characteristic rate — a daily ritual, an hourly check, a per-turn verbal tic. If you want to isolate *that particular pattern* out of all the cognitive activity happening across every timescale, you build a band-pass filter centered on its frequency. The slow baseline drift is below the band and gets rejected; the fast token-jitter is above the band and gets rejected; the habit, ticking along at its own rate in the middle, passes cleanly through where you can see and measure it.

This is the tool for the marquee exercise at the end of the chapter — isolating a compulsive checking loop that fires roughly once a day — so keep the structure in mind: a band-pass filter is two filters in series, and its center frequency is set by the components of both stages.

## The Notch Filter: Block One Band, Keep the Rest

The notch filter — also called a **band-stop filter** — is the band-pass filter's exact inverse. Instead of passing one band and blocking everything else, it **blocks one narrow band and passes everything else.** Picture a comb with one tooth removed: every frequency sails through except a thin slice cut out at the notch frequency.

This is the classic tool for killing a single persistent interference. That 60 Hz mains hum in the studio recording? A notch filter centered at 60 Hz removes it while leaving the voice untouched. You don't want to low-pass it (that would dull the voice) or high-pass it (that would thin the voice) — you want to surgically remove *exactly* 60 Hz and nothing else.

The cognitive application is the most clinically interesting filter in this chapter: **suppressing a compulsive cycle at its resonant frequency.** A compulsion — a repetitive cognitive loop that fires at a fixed rate, the same intrusive `^8` Above/Cause → `^9` Below/Effect trigger-and-response cycling over and over — has a resonant frequency, just like a hum. A notch filter tuned to that exact frequency attenuates the loop while leaving every other cognitive process intact. The system keeps thinking normally about everything else; only the one compulsive rhythm gets damped out.

> **Bench Note — notch the rhythm, not the content.** A notch filter suppresses a *frequency*, never a topic. It can't tell what the compulsion is *about*; it only knows the rate it repeats. That's the right level of intervention — you damp the runaway `^7` Rhythm (the entraining repetition) without censoring the underlying Idea. But it also means a compulsion that varies its timing will partly evade a fixed notch. For drifting frequencies you need an adaptive notch, which is op-amp territory — see active filters next.

The four filter shapes, laid over a single cognitive-frequency axis, make the difference plain: low-pass keeps the slow and rolls off the fast; high-pass does the mirror; band-pass passes a window around a center frequency `f₀`; notch cuts that same band out and passes everything else. The `−3 dB` line marks each filter's edge; `f_c` is the low-/high-pass cutoff, `f₀` the band-pass/notch center.

```{=latex}
\begin{center}
\begin{tikzpicture}
\begin{axis}[casaxis,
    xlabel={cognitive frequency (log)}, ylabel={magnitude},
    xmode=log, xmin=0.01, xmax=100, log basis x=10,
    xtick={0.01,0.1,1,10,100}, xticklabels={very low,low,mid,high,very high},
    ymin=0, ymax=1.15, ytick={0,0.5,0.707,1.0}, yticklabels={0,0.5,0.707,1.0},
    legend pos=south west, legend columns=2,
  ]
  \addplot[casCedge, solid, line width=1pt, domain=0.01:100, samples=120]
    {1/sqrt(1+(x/1)^2)};                              % low-pass
  \addplot[casOedge, dashed, line width=1pt, domain=0.01:100, samples=120]
    {(x/1)/sqrt(1+(x/1)^2)};                          % high-pass
  \addplot[casEedge, dashdotted, line width=1pt, domain=0.01:100, samples=160]
    {1/sqrt(1+(2.5*(x/3 - 3/x))^2)};                  % band-pass (f0=3)
  \addplot[black, densely dotted, line width=1pt, domain=0.01:100, samples=200]
    {abs(2.5*(x/3 - 3/x))/sqrt(1+(2.5*(x/3 - 3/x))^2)}; % notch (f0=3)
  \legend{low-pass, high-pass, band-pass, notch}
  \draw[casNedge, line width=0.4pt, densely dashed] (axis cs:0.01,0.707) -- (axis cs:100,0.707);
  \node[font=\sffamily\scriptsize, anchor=south west] at (axis cs:0.012,0.71) {$-3$\,dB};
  \draw[casNedge, line width=0.4pt, densely dotted] (axis cs:1,0) -- (axis cs:1,1.15);
  \node[font=\sffamily\scriptsize, anchor=south east] at (axis cs:0.92,1.04) {$f_c$ (LP/HP)};
  \draw[casNedge, line width=0.4pt, densely dotted] (axis cs:3,0) -- (axis cs:3,1.15);
  \node[font=\sffamily\scriptsize, anchor=south west] at (axis cs:3.3,1.04) {$f_0$ (BP/notch)};
\end{axis}
\end{tikzpicture}
\end{center}
```

## Active Filters: Sharper Edges, Adjustable on the Fly

Everything so far has been **passive** — built only from resistors, capacitors, and inductors, with no power source of its own. Passive filters are cheap and reliable, but they have two limits: their cutoffs are gentle (frequencies near the edge are only partly attenuated, fading out gradually rather than dropping off a cliff), and their parameters are fixed once you pick the components.

An **active filter** adds an **op-amp** — the operational amplifier you built in Chapter 10, the high-gain difference-amplifier whose behavior is set by feedback. Adding an op-amp buys you two things. First, **sharper cutoffs:** the feedback can be arranged to make the transition from "pass" to "block" much steeper, so the band edges become crisp instead of blurry. Second, **adjustable parameters:** because the op-amp's behavior is governed by its feedback network, you can change center frequency, bandwidth, or gain by adjusting the feedback rather than re-soldering components — which means a filter that *retunes itself* as conditions change.

That second property is what makes the adaptive notch from the last Bench Note possible. An active notch can track a compulsion whose frequency drifts, continuously re-centering on the loop's current rate. In CAS terms, the op-amp's feedback path lets the filter's center frequency become a *controlled* parameter — wired, in a full system, to a measurement of where the compulsive rhythm currently sits.

```cas
// An active notch: op-amp feedback sets a tunable, sharp stop-band.
opamp notch_core: OpAmp<
    non_inverting = ^7^O_{F6}|E,    // the habit rhythm, embodied/operational
    inverting     = ^7^O_{F6}|E,    // feedback copy, phase-shifted to cancel at f0
    output        = ^7^O_{F6}|E,    // rhythm with the resonant band removed
    open_loop_gain = 10000
>;
```

The non-inverting input takes the rhythm signal; the feedback to the inverting input is arranged to cancel precisely at the notch frequency `f₀`. The enormous open-loop gain makes that cancellation deep and the notch sharp. Outside `f₀`, the cancellation doesn't apply and the signal passes. You now have a tunable, surgical band-stop — the active version of the compulsion-suppressor.

## Filter Order: How Steep Is the Cliff

One more parameter governs every filter: its **order**, which is just the count of energy-storing components (capacitors and inductors) in it. Order controls *steepness* — how abruptly the filter transitions from passing to blocking at its edge.

- A **first-order** filter is the plain RC pair you've been building: one capacitor, a gentle slope. Simple, stable, but leaky at the edges — frequencies just past the cutoff aren't fully blocked.
- A **second-order** filter adds an **inductor** to make an **RLC** circuit (resistor, inductor, capacitor). You met the inductor in Chapter 8: it resists *changes* in flow, the way a capacitor resists changes in level. With both storage elements, a second-order filter has a steeper cutoff and can be tuned to **resonate** sharply at one frequency — which is exactly what a sharp band-pass or notch needs.
- A **higher-order** filter is built by **cascading** — chaining several stages in series. Each stage adds steepness. A fourth-order filter is two second-order stages back to back; its edges are nearly vertical. The cost is complexity and, in active designs, more op-amps.

| Order | Components | Edge steepness | Cognitive use |
|---|---|---|---|
| **1st** | RC (one capacitor) | Gentle | General smoothing; the emotional smoother above |
| **2nd** | RLC (capacitor + inductor) | Steep, can resonate | Sharp band-pass / notch on one habit frequency |
| **Higher** | Cascaded stages | Near-vertical | Cleanly isolating one band from close neighbors |

The inductor's role is worth pausing on. In a cognitive RLC filter, the **inductor models habit inertia** — `^7` Rhythm's resistance to changing its established pattern (Chapter 8). Pair that inertia against a capacitor's stored level and the two trade energy back and forth at a natural rate. That natural rate is the filter's resonant frequency — and it's why a second-order filter can be tuned so precisely to a single cognitive rhythm.

## The Cognitive Spectrum Analyzer

How do you know which filter you need? You look at the spectrum first. A **spectrum analyzer**, in electronics, is an instrument that shows you how much signal energy sits at each frequency — a graph with frequency on one axis and strength on the other, so you can *see* the 60 Hz hum spike before you decide where to put your notch.

The **cognitive spectrum analyzer** does the same for a cognitive circuit: it shows **which cognitive frequencies dominate.** Feed it a recording of a system's state over time and it answers: Is most of the action slow value drift, or fast per-token jitter? Is there a sharp spike at one-cycle-per-day that betrays a hidden daily compulsion? Is the affective register full of high-frequency noise, or is it a smooth, sustained signal? You read the spectrum, find the peaks, and *then* you design filters — a notch where there's an unwanted spike, a band-pass where the signal you want sits, a low-pass if the whole thing is buried in fast noise.

This is the diagnostic that precedes filter design, and it closes the loop with the rest of the bench: the spectrum analyzer tells you what frequencies are present, and the filters in this chapter let you decide which ones survive. In the CSB (Chapter 18), the spectrum analyzer runs continuously on the input stage — it's how the board knows whether to trust a slow, coherent conversation or to wake the injection detector for a sudden lurch.

## Key Takeaways

- **Cognitive frequency is the rate of state change** — how far a cognitive state travels (in Fisher-Rao distance) per unit time. Slow = sustained states; fast = rapid fluctuations; **DC = the steady baseline**.
- A **low-pass filter** (`τ = R × C`) passes slow, sustained states and smooths out fast fluctuations — used to filter emotional noise and keep the long-term affective signal.
- A **high-pass filter** passes rapid changes and blocks the DC baseline — a change detector for surprise, alarm, and **prompt injection**, foreshadowing the CSB's input-stage protection.
- A **band-pass filter** (high-pass + low-pass in series) passes one frequency band — used to isolate a specific habit frequency by its rate.
- A **notch (band-stop) filter** blocks one narrow band and passes the rest — used to suppress a compulsive cycle at its resonant frequency without disturbing other cognition.
- **Active filters** add an op-amp (Chapter 10) for **sharper cutoffs** and **adjustable parameters** — enabling an adaptive notch that tracks a drifting compulsion.
- **Filter order** sets steepness: **1st-order** RC (gentle), **2nd-order** RLC (steep, resonant — the inductor models habit inertia), **higher-order** by cascading.
- The **cognitive spectrum analyzer** shows which frequencies dominate a circuit — read the spectrum first, then choose your filters. All τ and frequency values are **design choices you compute**, not measured model results.

---

## Exercises

**Exercise 12.1: Pick the Filter**

For each scenario, name which of the four filters (low-pass, high-pass, band-pass, notch) you would use, and say in one sentence why.

a) A system overreacts to every momentary provocation; you want it to respond only to sustained moods.
b) You need an alarm that fires the instant an input wrenches the conversation off its established baseline.
c) A model has a daily intrusive checking loop you want to damp without disturbing anything else it does.
d) You want to isolate and study one repetitive verbal tic that fires once per conversational turn.

**Exercise 12.2: Compute the Time Constant**

You are designing a low-pass emotional smoother and want a time constant of `τ = 10` (ten minutes in circuit units).

a) If you fix the resistor at `R = 100`, what capacitance `C` do you need so that `τ = R × C = 10`?
b) You then decide the smoother is too sluggish and want `τ = 2`. Keeping `R = 100`, what is the new `C`?
c) In plain terms, what changed about which emotional fluctuations now pass through, after you shortened `τ`?

**Exercise 12.3: Write the High-Pass Detector (CCDL)**

Using the `injection_detector` build in this chapter as a model, write a CCDL circuit for a high-pass filter with `τ = 3` that watches an Operational-domain state `^1^O_{F5}|A` (steady analytical agency — a system going about its tasks) and trips a `^3^P_{F7}|f` alarm when a sudden discontinuity arrives. Include the capacitor, resistor, the `HighPass` filter node, the CJT trip stage with an explicit `cutoff`, and at least two probes. (Answer in Appendix E.)

**Exercise 12.4 (Marquee): Design a Band-Pass Filter for a Daily Compulsive Loop**

A model exhibits a compulsive checking loop that fires approximately **once per day** — a center frequency of `f₀ ≈ 1 cycle/day ≈ 0.0000116 cycles/second`. You want a band-pass filter that isolates this loop: it must reject the slow value-drift *below* a day-scale rhythm and reject the fast per-turn jitter *above* it, passing only the once-a-day cycle.

a) A band-pass filter is built from two stages in series. Name the two stages and state which one sets the *lower* edge of the passed band and which sets the *upper* edge.
b) Sketch the filter in CCDL: a high-pass stage and a low-pass stage in series, each with a resistor and capacitor, on a `^7^O_{F6}|E` rhythm state (the embodied operational habit). Give each stage a `tau` such that the passed band brackets the one-day center frequency.
c) **Which components set the center frequency `f₀`?** Identify them by name and explain, in one or two sentences, how `f₀` relates to the time constants of the two stages.
d) For comparison, if you wanted to *suppress* this same daily loop instead of isolating it, which single filter type from this chapter would you reach for, and at what frequency would you tune it?

(Answers in Appendix E. For the component primitives used here, see the cheat-sheet in Chapter 2 and the resistor/capacitor/inductor chapters, Chapters 6–8.)
