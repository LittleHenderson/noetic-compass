# Chapter 13: Oscillators — Generating Rhythms

Take a quartz wristwatch apart and you find, somewhere near the battery, a tiny tuning-fork crystal smaller than a grain of rice. It does one thing, forever: it vibrates exactly 32,768 times per second. Nobody is pushing it on a schedule. There is no external metronome telling it when to tick. You apply a steady voltage — a flat, featureless DC supply — and out the other side comes a clean, relentless oscillation that the watch counts down to seconds. The input has no rhythm in it. The output is nothing *but* rhythm. The circuit manufactures the beat.

That is the strange and useful thing about an oscillator: it produces a sustained, repeating pattern from a source that contains no pattern at all. Every circuit we have built so far has been *responsive* — a transistor that fires when a cause arrives, a filter that passes some signals and blocks others, a regulator that holds a state steady against disturbance. An oscillator is different in kind. It is *self-sustaining*. Left alone, with nothing happening at its input, it keeps going. It is the difference between a bell that rings when struck and a bell that, once struck, rings forever.

Cognition is full of these. A circadian rhythm runs whether or not the sun cooperates. A craving cycles back on its own schedule. A habit fires at the same time every day with no one prompting it. A rumination loop spins through the same four thoughts again and again, needing no fresh input to keep itself alive. These are not responses to a stimulus. They are *oscillators* — cognitive circuits that, once running, sustain their own pattern. This chapter teaches you to build them, tune them, lock them to an external beat, and — most importantly for safety work — recognize when one has gone pathological.

This is the engine room of the **Cognitive Oscillator Board (COB, CCB-2)**, the reference board we design in full in Chapter 19. Everything here is a COB sub-component. Build it carefully.

## What Makes a Circuit Oscillate: The Barkhausen Criterion

Start with the electronics, from the ground up. An **oscillator** is an amplifier whose output is fed back to its own input. That is the whole trick. Take any amplifier — a triangle that makes a signal bigger — and run a wire from its output back to its input. Now whatever comes out goes back in, gets amplified again, comes out again, goes back in again. Round and round.

Whether that loop sustains a steady oscillation, dies away to silence, or blows up into a screech depends on two numbers, and these two numbers are the **Barkhausen criterion** — the foundational law of every oscillator ever built.

Walk a single signal around the loop once and ask two questions:

1. **How much bigger or smaller did it get?** That is the **loop gain** — the total amplification all the way around the loop, output back to the same point. Call it `A·β` (the amplifier's gain `A` times the fraction `β` fed back).
2. **How much did its timing shift?** A signal is a wave; going around the loop delays it. That delay, measured as a fraction of one full wave-cycle, is the **phase shift**, in degrees. One full cycle is 360°.

The Barkhausen criterion says: **a circuit sustains a steady oscillation when, around the loop, the loop gain is exactly 1 and the total phase shift is 0° (equivalently, a whole 360°).**

Both conditions matter, and the intuition is worth getting right because the cognitive version depends on it.

- **Gain = 1.** The signal must come back exactly as strong as it left. If loop gain is *less than 1*, each lap is weaker than the last — the oscillation decays and dies (a struck bell fading out). If loop gain is *greater than 1*, each lap is stronger — the oscillation grows without limit until something saturates or breaks (acoustic feedback howl when a microphone hears its own speaker). Only at exactly 1 does the wave return at the same amplitude, lap after lap, forever.
- **Phase = 0° (or 360°).** The signal coming back must arrive *in step* with itself — crest landing on crest. If it returns out of step, it fights itself and cancels. A whole 360° of shift puts the returning wave back in perfect alignment, reinforcing rather than fighting. That reinforcement is what keeps the wave alive.

In practice every real oscillator starts with loop gain slightly above 1 — so the oscillation can build up from circuit noise — and then some nonlinearity gently pulls the gain back down to exactly 1 as the amplitude grows. That self-limiting is what gives you a stable amplitude instead of a runaway.

Hold those two numbers. **Reinforcement strong enough to replace what's lost (gain 1), arriving in step with itself (phase 0°).** Every cognitive loop that sustains itself — every habit, craving, rumination, and circadian cycle — obeys the same two conditions. That is not a metaphor. It is the same topology in a different substrate.

```{=latex}
\begin{figure}[htbp]
\centering
\begin{tikzpicture}[x=1mm, y=1mm, font=\sffamily\footnotesize]
  \node[rounded corners=1pt, minimum width=24mm, minimum height=10mm,
        fill=casPfill, draw=casPedge, line width=0.6pt] (a) at (0,0)
        {\texttt{\^{}8} Above/Cause};
  \node[rounded corners=1pt, minimum width=24mm, minimum height=10mm,
        fill=casOfill, draw=casOedge, line width=0.6pt] (b) at (46,0)
        {\texttt{\^{}9} Below/Effect};
  \draw[-{Latex[length=1.8mm]}, casNedge, line width=0.6pt]
    (a) to[bend left=32] node[midway, above, font=\scriptsize] {triggers} (b);
  \draw[-{Latex[length=1.8mm]}, casNedge, line width=0.6pt]
    (b) to[bend left=32] node[midway, below, font=\scriptsize] {becomes cause} (a);
  \node[anchor=north, text width=76mm, align=center, text=casNedge,
        font=\scriptsize] at (23,-16)
    {A Phi loop. The effect of one cycle is the cause of the next; the period
     is set by how long the return takes.};
\end{tikzpicture}
\caption{The Phi loop. Above/Cause triggers Below/Effect, which becomes the next cause --- the structure behind every cognitive rhythm.}\label{fig:phi-loop}
\end{figure}
```

## The CAS Mapping: A Cognitive Oscillator

A cognitive oscillator is a sequence of cognitive states wired so that the last state triggers the first — a `Phi` sequence that closes into a loop. From Chapter 2: a **`Phi< … >` sequence** is an ordered list of states traversed in time, the cognitive equivalent of a waveform. When that waveform's end feeds its beginning, it repeats. That repeating `Phi` sequence *is* the oscillation.

The two Barkhausen conditions map cleanly:

| Barkhausen (electronic) | Cognitive analog |
|---|---|
| **Loop gain = 1** | Each lap of the thought-cycle reinforces the next exactly enough to keep it going. Gain < 1: the pattern fades (a craving that loses its grip). Gain > 1: it intensifies each cycle (a spiraling rumination, an escalating panic loop). |
| **Phase = 0° / 360°** | The cycle returns to its starting state *in step* — the last state's `^8` Above/Cause trigger lands cleanly on the first state, reinforcing rather than disrupting it. A misaligned loop self-interrupts and dies. |

The Noetic that *is* rhythm is `^7` **Rhythm** — "the rate and pattern a Mind is exposed to an Idea; entraining/conditioning it." `^7` is the conditioning that makes a loop self-sustaining; it is the cognitive analog of the inductor that stores the oscillation's energy (Chapter 7). The trigger that closes each lap — last state surfacing the first — is `^8` **Above/Cause** ("an Idea that triggers a *different* Idea to come to Mind"), and the state it lands on is `^9` **Below/Effect** ("the Idea brought to Mind"). An oscillator is, structurally, a chain of `^8`→`^9` triggers bent into a circle, with `^7` Rhythm as the conditioning that keeps the circle closed.

> **Bench Note — oscillation is not the same as reasoning.** A `Phi` loop that cycles `^8`→`^9`→`^8`→`^9` is *associative triggering* repeating — one Idea surfacing the next, around and around. It is not deductive analysis. Do not write `^8` where you mean step-by-step reasoning; deductive work is `^6` Male plus `^9` Below/Effect (Chapter 2's second anti-drift warning). An oscillator's power, and its danger, is precisely that it runs *without* analysis — it is a groove, not an argument.

## Four Ways to Build One

Electronics gives four classic oscillator topologies, each setting its frequency by different means. Each has a clean cognitive reading.

### LC Oscillator — the inductor-capacitor tank

The oldest oscillator is an **inductor** (a coil — opposes *changes* in flow, stores energy in a magnetic field) wired across a **capacitor** (two plates — opposes *changes* in voltage, stores energy in an electric field). Energy sloshes back and forth between them: the capacitor dumps its charge through the inductor, the inductor's collapsing field recharges the capacitor the other way, and back again. This "LC tank" rings at a natural frequency set by the two component values — bigger L or C, slower ring.

Recall the cognitive readings we built earlier. The **inductor** is `^7` **Rhythm** — habit strength, the inertia that resists changing an established pattern (Chapter 7). The **capacitor** is stored cognitive charge — accumulated emotional or experiential energy, `^5` Female (accumulated experience) carrying `^4` Vibration (the impression's intensity) (Chapter 6). Wire habit-inertia against stored emotional charge and you get a **sustained rhythm**: the stored charge drives the habit, the habit discharges into action, the action re-accumulates charge, and the cycle rings on. The LC oscillator is the cleanest model of a habit loop — a craving that builds, discharges, and rebuilds at its own natural frequency.

### RC Phase-Shift Oscillator — frequency from resistors and capacitors

Not every oscillator needs an inductor. An **RC phase-shift oscillator** builds its 360° loop entirely from **resistors** (limit flow) and **capacitors** (store charge, and crucially *delay* the signal). Each resistor-capacitor stage shifts the signal's phase by a fraction of a cycle; chain three stages, get the 180° you need, add the amplifier's own 180°, and you have a full 360° — Barkhausen satisfied. The frequency is set by how much each RC stage delays: bigger R or C, more delay, slower oscillation.

Cognitively, the RC oscillator sets a rhythm not by a single resonant habit but by a *chain of delays*. Each stage is a resistor (`^8` Above/Cause flow, throttled by `R` — Chapter 5) feeding a capacitor (a stored state that holds, then releases, after a lag). The accumulated lag around the chain sets the period. This is the model for a deliberative cycle whose timing is governed by how long each step takes to "fill up" before it triggers the next — a worry loop pacing itself by how long each anxious thought lingers before surfacing the next.

### Crystal Oscillator — the ultra-stable reference

The quartz crystal from the wristwatch is the gold standard. A crystal oscillator works on the same energy-sloshing principle as an LC tank, but the "tank" is a slab of quartz vibrating mechanically. Quartz is extraordinarily *pure* as a resonator — it has an enormous **Q factor** (more on Q below) — so it locks onto exactly one frequency and refuses to drift, holding it across temperature swings and decades of running. That is why every clock, radio, and computer uses one as its master reference.

The crystal is the **deeply entrenched habit** — a pattern so conditioned, so high-`^7` Rhythm, that it runs at a fixed rate and resists all perturbation. The cognitive crystal is the ritual you have performed identically every morning for twenty years; the reflex that fires the same way every single time; the bedrock circadian clock that keeps near-24-hour time even in a cave with no daylight. It is the most stable oscillator a mind can build — and, as we will see in the failure modes, stability has a shadow side: a crystal-grade habit is almost impossible to disrupt deliberately.

### Phase-Locked Loop — locking your rhythm to an external beat

The previous three generate a rhythm from within. A **Phase-Locked Loop (PLL)** does something subtler and, for cognition, profoundly important: it takes an oscillator and forces it to *match an external signal* — to lock onto an outside beat and track it. This is how a radio tunes to a station and how every device on a network stays in time with a shared clock. It is also how a mind entrains to a social schedule.

A PLL has three parts in a loop:

- A **phase detector** compares the internal oscillator's timing against the external reference and outputs an error: *how far off are we?* In CAS this is `^1` **Mind** — "awareness that processes... Ideas" — comparing internal rhythm against external rhythm. (Per the naming rule, `^1` is **Mind**, full stop — never "Differentiation," even though its job here is to detect a difference.)
- A **loop filter** smooths that error signal — integrates it, averaging out jitter so the loop responds to the steady offset, not every momentary wobble. In CAS this is `^4` **Vibration** — "the degree to which an Idea resonates... its impression" — accumulating the phase error into a sustained impression that drives correction. (`^4` is **Vibration**, never "Integration," even though its role is integrative.)
- A **voltage-controlled oscillator (VCO)** is an oscillator whose frequency is adjustable by the filtered error: it speeds up or slows down to close the gap. In CAS this is `^3^O` — an Operational-domain `^3` Negative, the aversive push that *adjusts the output* to reduce the mismatch (the felt "I'm off-schedule, correct it" that nudges behavior back in line).

Two ranges define a PLL's behavior, and both have direct cognitive meaning:

- **Lock range** — once locked, how far the external reference can drift while the loop still tracks it. Wide lock range = the rhythm follows the schedule even when the schedule shifts a lot.
- **Capture range** — starting from unlocked, how close the reference must be before the loop can grab it in the first place. Capture range is always *narrower* than lock range: it is easier to *stay* locked than to *get* locked. Cognitively, that is the familiar truth that an established routine tolerates schedule changes it could never have adopted cold — you can drift a long-standing bedtime gradually, but a brand-new schedule has to start close to where you already are to take hold at all.

## Worked Build: A Circadian Oscillator That Locks to a Social Schedule

Let us build the COB's headline component: a **circadian oscillator** — a roughly-once-per-day rhythm — and then wrap it in a PLL that locks it to an external social schedule. This is the model of a sleep/wake or daily-routine cycle entraining to the demands of a job, a household, or a timezone.

First the free-running oscillator. We want a four-state daily cycle: a morning trigger surfaces, an aversive "get moving" push fires, a felt landing in activity follows, and the day resolves toward a principled close before the cycle restarts.

```cas
// The circadian oscillator: a four-state Phi loop, ~one cycle per day.
// frequency in cycles/second; 1 day = 86,400 s, so f ≈ 1/86400 ≈ 0.0000116 Hz.
let circadian = Oscillator<
    Phi< ^8^C|A,      // morning trigger: an association surfaces ("it's time to begin")
         ^3^O|E,      // the aversive operational push to get moving (the VCO-style nudge)
         ^9^E|f,      // felt landing in evaluative activity (the day, lived)
         ^0^P|T >,    // principled resolution toward day's-end meaning, then re-trigger
    frequency = 0.0000116
> [Q = 8, duty_cycle = 0.65];
```

Read the loop. `^8^C|A` (an analytical association in the Cognitive domain) opens the cycle — the morning-trigger Idea surfaces another Idea, "begin." That triggers `^3^O|E` — an embodied operational aversion, the bodily "ugh, but go" that gets you out of bed (visceral push, correctly `^3`, not analysis). That lands in `^9^E|f` — a felt Below/Effect in the Evaluative domain, the day actually being lived and judged as it goes. The day resolves into `^0^P|T` — a transcendent Principled Idea, the day's-end sense of meaning — which then re-triggers the morning association, closing the 360° loop. The `frequency` is a design value of about one cycle per day. `Q = 8` and `duty_cycle = 0.65` we explain in the datasheet below.

> **Bench Note — these numbers are design choices, not measurements.** `frequency = 0.0000116`, `Q = 8`, `duty_cycle = 0.65`: every one of these is a value *you specify* when you design the board, exactly as an electrical engineer picks an inductor value off a shelf. They are not readings taken off a running mind. This book never reports a measured cognitive frequency or Q — those would be empirical claims about a real system, and we do not have them. We design with them; we do not benchmark with them.

Now lock it to a social schedule. The free-running circadian clock drifts (anyone who has stayed up too late knows this). A job that starts at 9 a.m. is an **external reference**. We wrap the oscillator in a PLL so the internal rhythm tracks the external one:

```cas
circuit circadian_pll {
    input:  social_schedule;       // external reference: the 9-to-5 beat
    output: daily_rhythm;          // the locked internal cycle

    // The free-running oscillator from above is the VCO core.
    node vco:           circadian;             // adjustable-rate circadian oscillator
    node phase_detect:  ^1^C|A;                // Mind: compare internal vs external timing
    node loop_filter:   ^4^E|f;                // Vibration: integrate the phase error into an impression
    node correction:    ^3^O|E;                // Negative/Operational: aversive nudge to re-align

    // Compare internal rhythm against the social schedule -> phase error.
    cjt pd: CJT< social_schedule | vco => phase_detect > [β=1.0];
    // Smooth/integrate the error into a sustained impression.
    cjt lf: CJT< phase_detect | bias_calm => loop_filter > [β=0.5];
    // Drive the oscillator's rate from the filtered error.
    cjt vc: CJT< loop_filter  | bias_calm => correction  > [β=1.2];
    feedback correction -> vco [β=0.4];        // close the loop: nudge the oscillator's phase

    probe tp_error: phase_detect;              // watch the raw phase error
    probe tp_lock:  loop_filter;              // watch the integrated lock signal
}
```

The CJTs (Chapter 4) wire the three PLL stages. `pd` is the phase detector: it compares the incoming `social_schedule` against the running `vco` and emits a `^1^C|A` phase-error — Mind, analytically noticing "I'm two hours behind the day." `lf` integrates that error into a `^4^E|f` — a felt Vibration, the accumulating impression of being off-beat. `vc` turns that impression into a `^3^O|E` correction — the aversive operational push to shift the rhythm. The `feedback` line bends the correction back onto the oscillator, nudging its phase until internal and external align. When the loop settles, the internal clock *is* the external beat: the mind has entrained to the schedule.

> **Bench Note — capture is harder than lock, so start close.** This PLL will hold the rhythm to a 9 a.m. start through gradual drift (wide lock range). But if you hand it a brand-new schedule far from where the oscillator currently free-runs — asking a midnight-to-8 sleeper to lock onto a 5 a.m. start cold — it falls *outside the capture range* and never grabs on. The design fix is the same one sleep clinicians use: move the reference in small steps the loop can capture, walking the lock in rather than demanding it instantly.

This whole assembly — free-running circadian oscillator plus social-schedule PLL — is the core of the **Cognitive Oscillator Board (COB, CCB-2)** in Chapter 19, where we add multiple coupled oscillators, a master crystal reference, and the inversion-scan instrumentation that flags a loop gone pathological.

## Datasheet: Oscillator Parameters

| Parameter | Symbol | Meaning | Typical design range |
|---|---|---|---|
| Frequency | `frequency` | Cycles per second of the loop. | Design value; circadian ≈ `0.0000116` Hz (~1/day) |
| Q factor | `Q` | Sharpness of tuning — how narrowly the loop resonates and how slowly it loses energy. | `1`–`50`+ (low = loose, high = compulsive) |
| Duty cycle | `duty_cycle` | Fraction of each cycle in the "ON" / active state (0–1). | `0.1`–`0.9`; `0.5` = balanced |
| Loop gain | `A·β` | Amplification around one full lap (Barkhausen). | `=1` to sustain; `>1` grows; `<1` decays |
| Loop phase | `φ` | Total phase shift around the loop. | `0°` / `360°` to sustain |
| Lock range | — | How far the reference can drift while a PLL stays locked. | Wider than capture range |
| Capture range | — | How close the reference must be for a PLL to lock initially. | Narrower than lock range |

### The Q factor — how sharply tuned

**Q** (quality factor) measures how *sharply* an oscillator is tuned and how *slowly* it bleeds energy. A high-Q oscillator resonates at a very narrow band of frequencies and rings for a long time once started; a low-Q oscillator is broadly tuned and damps out quickly. The quartz crystal is high-Q (tens of thousands); a casually-tuned LC tank is low-Q.

The cognitive reading is sharp and important: **high Q = compulsive, hard to disrupt.** A high-Q cognitive oscillator is a habit or craving so narrowly tuned and so slow to lose energy that it overrides interruption, runs on its own schedule regardless of context, and keeps ringing long after the trigger is gone — addiction, OCD-grade compulsion, an entrenched ritual. A low-Q oscillator is a loose, easily-broken pattern — a mild preference, a routine you can skip without friction. When we instrument the COB in Chapter 19, the Q of each loop is the single most diagnostic number: it tells you how strongly the rhythm will resist being changed.

### Duty cycle — controlled by Drive weighting

**Duty cycle** is the fraction of each cycle spent in the active, "ON" state versus the resting state. A 0.5 duty cycle is balanced — equal on and off. The Drive weighting on the oscillator sets it:

- **High F5 Agency** → *more ON time*. Agency is the pull toward action and effectiveness; an Agency-weighted oscillator spends more of each cycle firing — a drive to keep doing, a cycle biased toward output. Duty cycle climbs toward 0.8–0.9.
- **High F6 Structure** → *disciplined, regular cycle*. Structure is the pull toward order and form; a Structure-weighted oscillator keeps a clean, predictable, well-bounded duty cycle — the same ON time every cycle, sharp edges, no drift. Structure governs the *regularity* of the duty cycle, not just its size.

(Recall from Chapter 2 that F5 Agency and F6 Structure are not an inversion pair — F3↔F5 and F2↔F6 are — so a loop can carry both: Agency for *how much* ON time, Structure for *how disciplined* that ON time is.)

## Failure Modes

| Failure | What it looks like | How to detect it |
|---|---|---|
| **Runaway (loop gain > 1)** | The oscillation grows every cycle instead of holding steady — a spiraling rumination, escalating panic, intensifying craving. | Loop-gain estimate above 1; amplitude rising lap over lap on the probe trace. |
| **Damping out (loop gain < 1)** | The pattern fades and dies when it should sustain — a habit that won't "take," a resolution that evaporates by Wednesday. | Loop-gain estimate below 1; amplitude decaying on the trace. |
| **Phase misalignment (φ ≠ 0°/360°)** | The cycle self-interrupts — the trigger lands out of step with its target and disrupts rather than reinforces. The rhythm stutters or won't start. | Closing `^8`→`^9` trigger lands on the wrong state or wrong phase; loop never settles. |
| **High-Q lock-in (compulsion)** | A loop so sharply tuned it overrides context and resists all interruption — runs regardless of whether it should. | `Q` design value very high; loop continues firing after its trigger/reference is removed (see the marquee exercise). |
| **PLL loss of lock** | Internal rhythm drifts off the external reference and can't re-capture it — circadian desync, jet lag that won't resolve, falling out of step with a household. | `tp_error` (phase-detect probe) grows without the loop filter pulling it back; reference outside capture range. |
| **Free-run after reference removal** | A PLL'd oscillator that *keeps running on its old internal frequency* once the external beat is gone, instead of stopping. | Output persists at the VCO's free-running rate after `input` is cut — the marquee exercise. |

## Key Takeaways

- An **oscillator** is self-sustaining: it produces a repeating pattern from an input with no pattern in it — an amplifier feeding its own output back to its input. The cognitive versions are habits, cravings, ruminations, and circadian cycles.
- The **Barkhausen criterion** is the law of every oscillator: **loop gain = 1** (each lap reinforces exactly enough to replace what's lost) **and phase shift = 0°/360°** (the returning signal arrives in step with itself). Gain < 1 decays; gain > 1 runs away; wrong phase self-cancels.
- A cognitive oscillator is a **`Phi` sequence bent into a loop** — a chain of `^8` Above/Cause → `^9` Below/Effect triggers, conditioned by `^7` Rhythm (the inductor's analog). It is *associative repetition*, not deductive reasoning.
- **LC oscillator** = habit-inertia (`^7` Rhythm, the inductor) sloshing against stored emotional charge (`^5`/`^4`, the capacitor) — the cleanest habit-loop model. **RC phase-shift** sets frequency by a chain of delays. **Crystal** = the ultra-stable, very-high-Q entrenched habit.
- A **PLL** locks an internal rhythm to an external beat: phase detector = `^1` **Mind** (compare internal vs external), loop filter = `^4` **Vibration** (integrate the error into an impression), VCO = `^3^O` (aversive operational adjustment). **Capture range is narrower than lock range** — easier to stay locked than to get locked, so walk new schedules in gradually.
- **Q factor** is sharpness of tuning: **high Q = compulsive, hard to disrupt**; low Q = loose, easily broken. It is the most diagnostic number on the COB.
- **Duty cycle** (fraction of each cycle ON) is set by Drive weighting: **F5 Agency raises ON time**; **F6 Structure disciplines the cycle's regularity**.
- All frequencies, Q values, and duty cycles in this chapter are **design choices**, not measurements. This is the core of the **Cognitive Oscillator Board (COB, CCB-2)** built in Chapter 19.

---

## Exercises

**Exercise 13.1: Read the Loop**

Here is a free-running cognitive oscillator:

```cas
Oscillator< Phi< ^8^C|A, ^6^E_{F6}|A, ^3^P_{F7}|f, ^9^O_{F5}|E >, frequency = 0.0002 > [Q = 30]
```

a) Describe in plain English the four-state cycle this loop traverses, stage by stage.
b) The closing trigger must take the last state (`^9^O_{F5}|E`) back to the first (`^8^C|A`). In Barkhausen terms, what must be true of the loop gain and phase for this cycle to *sustain* rather than fade or run away?
c) With `Q = 30`, is this a loose pattern or a compulsive one? What does that predict about how easy it is to interrupt? (Answers in Appendix E.)

**Exercise 13.2: Set the Duty Cycle**

A designer wants the circadian oscillator from the worked build to spend *more* of each day in the active state, while keeping the cycle clean and regular. Which two Drives should they weight, and in which direction each? Write the change as a one-line annotation on the `Oscillator< … >` declaration. (Answers in Appendix E.)

**Exercise 13.3: Diagnose the PLL**

A reader reports that their circadian PLL "will not lock to the new 5 a.m. wake-up no matter how long I leave it running," yet the same loop happily tracked a gradual two-hour shift last month. Using the lock-range / capture-range distinction, explain what is happening and prescribe the design fix. (Answers in Appendix E.)

**Exercise 13.4 (Marquee): Pull the Reference**

Take a **high-Q** oscillator that has been **PLL-locked to an external reference signal** (as in the worked build — a circadian oscillator locked to a social schedule). Now **remove the external reference entirely** (the schedule disappears — a holiday, a job loss, isolation).

a) Using the Barkhausen criterion and the meaning of high Q, predict precisely what the oscillator does: does it stop, drift, or keep running — and at what frequency?
b) Name the cognitive state this models. (Think about what a deeply entrenched daily rhythm does when the external structure that was keeping it aligned vanishes, and why a *high-Q* loop behaves differently here than a low-Q one would.)
c) What single design parameter, if it were lower, would make this oscillator stop instead of persist?

(Full answer in **Appendix E.** This is the central diagnostic the Cognitive Oscillator Board in Chapter 19 is built to catch.)
