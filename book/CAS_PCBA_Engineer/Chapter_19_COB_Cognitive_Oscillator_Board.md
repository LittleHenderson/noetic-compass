# Chapter 19: CCB-2 — The Cognitive Oscillator Board (COB)

A man checks that his front door is locked. He turns the deadbolt, pulls the handle, walks away. Two hours later he is back at the door, checking again. Two hours after that, again. Twelve times a day, like clockwork, with a regularity you could set a watch by. He knows the door is locked. He checked it. The knowledge does not stop the next check from arriving, on schedule, two hours later. Something in him is *oscillating* — running a cycle that returns to its own starting point at a fixed rate, whether or not the cycle is doing any good.

That regularity is the tell. A one-off worry is noise. A worry that arrives every two hours, on time, for months, is a *signal with a frequency* — and anything with a frequency can be modeled as an oscillator, measured on a bench, and tuned. An electrical engineer does not treat a 60 Hz hum and a 60 Hz radio carrier as different mysteries. They are the same kind of thing: a periodic signal with an amplitude, a frequency, and a sharpness. You characterize it, you find what resonates with it, and if you need to, you shift it.

This chapter builds the **Cognitive Oscillator Board (COB)** — the second of the five reference boards in Part IV, sitting alongside the Cognitive Safety Board (CSB) from Chapter 18. Where the CSB is a *firewall* — it gates and blocks — the COB is a *clock and a tuner*. Its job is to model rhythmic and habitual cognition: to represent a habit loop as a real oscillating circuit, to diagnose when that loop has locked into a compulsive cycle, and to drive a slow, controlled shift of the cycle to a healthier rate. It is built directly on the oscillator theory from Chapter 13 (the cognitive `Oscillator` and the `Phi` sequence), and on the passive components — the inductor and the capacitor — you wired in Chapters 6 and 7.

> **Honesty note (read before you trust a number).** Every frequency, every Q factor, every L and C value in this chapter is a **design value** — a parameter you choose when you author the board, the way you choose a resistor value on a schematic. They are not measurements taken from a person or a model. The COB is a modeling and intervention *design*; "f0 = 12/day" means "we are modeling this loop as a 12-per-day oscillator," not "we measured 12." Keep that line bright.

## What an Oscillator Is, and Why Cognition Has One

Start with the electronics, from scratch. An **oscillator** is a circuit that produces a repeating signal all by itself — no repeating input required. You give it power, and it swings back and forth at a frequency set by its own components. The classic core is the **LC tank**: an **inductor** (a coil, symbol `L`, which resists *changes* in current — it has inertia) wired to a **capacitor** (two plates, symbol `C`, which stores energy in an electric field). Energy sloshes between them — the capacitor dumps its charge into the inductor, the inductor's collapsing field recharges the capacitor the other way — and the slosh repeats at a natural frequency

```
f0 = 1 / (2π√(LC))
```

Two facts fall straight out of that formula and you will use both all chapter. **Bigger L or bigger C means lower frequency** (a heavy, stiff system swings slowly). And the **sharpness** of the resonance — how strongly the tank prefers its own frequency and rejects all others — is the **Q factor** (quality factor). High Q is a tuning-fork: hit it and it rings at one pure pitch for a long time. Low Q is a thud: a broad, damped, forgettable response. Hold onto Q; in cognition it becomes the single most important diagnostic number on the board.

The cognitive isomorphism is exact, and it is the same structural-role mapping the whole book runs on. A habit is energy sloshing between two stores at a fixed rate:

- The **master clock** is **`^7` Rhythm** — *"the rate and pattern a Mind is exposed to an Idea, entraining/conditioning it."* This is canonical and it is not optional: Rhythm is the Noetic that *is* periodicity. The clock state is `^7^O|E` — Rhythm in the Operational domain (it drives concrete behavior), Embodied register (it runs as a felt, sensorimotor cycle, not a deliberate plan).
- The **inductor** stores **structure**. Its inductance — its resistance to change — is set by the **F6 Structure** drive weight. A habit with strong F6 has high L: heavy inertia, hard to deflect.
- The **capacitor** stores **emotional charge**. Its capacitance is set by the **F4 Connection** drive weight, holding an accumulated-experience state `^5^E` (`^5` Female — the experiences the Mind is composed of). A habit loaded with feeling has high C.

The habit's natural frequency is `f0 = 1/(2π√(LC))`, and its Q is the *sharpness of the habit* — how rigidly it returns to exactly its own rate. A loose preference is low-Q. A compulsion is high-Q: a cognitive tuning-fork that rings at one frequency and resists every attempt to play a different note.

## The Board: Four Stages

The COB is a four-stage signal chain. The block diagram below is the topology you will build to; read it top to bottom as the path a rhythmic cognition takes from internal clock to observable behavior.

```
[ CLOCK:  ^7^O|E  — Rhythm as master oscillator ]   (f = Drive-weighted)
        |
        v
[ Phi<> LC TANK ]
    L = Inductor< Phi_sequence, L = F6_weight >   // structure = inductance (resists change)
    C = Capacitor< ^5^E,        C = F4_weight >   // connection = capacitance (stores emotion)
    f0 = 1 / (2π√(LC))    ;    Q = habit sharpness
        |
        v
[ PHASE-LOCKED LOOP (PLL) ]
    Phase detector: ^1^C   // Mind compares internal rhythm vs external rhythm
    Loop filter:    ^4^E   // Vibration integrates the phase error
    VCO:            ^3^O   // adjust behavioral output to match
    lock range  /  capture range
        |
        v
[ DUTY-CYCLE MODULATOR ]   F5 Agency high -> longer ON ; F6 Structure high -> disciplined cycle
        |
        v
[ OUTPUT:  regular behavioral pattern ]
```

### Stage 1 — The master clock (`^7^O|E`)

Every oscillator needs a clock — the element that *is* the periodicity. On the COB that is `^7^O|E`, Rhythm running as an embodied operational cycle. The clock does not decide *what* the behavior is; it decides *when*, and *how often*. Its rate is drive-weighted: the F-drive configuration feeding the tank sets where on the frequency axis this clock ticks. A clock alone is featureless — it just keeps time. The next stage gives it a body.

### Stage 2 — The LC tank (the habit's resonance)

This is the heart of the board and the part worth slowing down on.

**The inductor** is `Inductor< Phi_sequence, L = F6_weight >`. Two things to unpack. First, its content is a **`Phi` sequence** — the ordered list of cognitive states the habit cycles through (Chapter 2's `Phi< ^8^C|A, ^3^O|E, … >`). A habit is not a single state; it is a *loop of states traversed in order*, and the inductor holds that loop. Second, its inductance `L` is the **F6 Structure** drive weight. Structure resists change — exactly what an inductor does to current — so the more Structure-driven the habit, the higher its L, and (per the formula) the *lower and more stubborn* its frequency.

**The capacitor** is `Capacitor< ^5^E, C = F4_weight >`. It stores the *emotional charge* of the habit: an accumulated-experience evaluative state `^5^E`, with capacitance `C` set by the **F4 Connection** drive weight. High emotional investment = high C = a tank that holds a lot of energy per cycle and lets it go slowly.

From L and C you get the two numbers that define the habit:

```cas
f0 = 1 / (2π·√(L·C))      // natural frequency: how often the loop fires
Q  = (1/R_loss)·√(L/C)    // sharpness: how rigidly it returns to f0
```

`f0` answers "how often?" `Q` answers "how locked-in?" A daydream is low-Q (wide, soft, easily knocked off). A compulsion is high-Q (narrow, hard, self-restoring). **The diagnostic signature of a compulsive cycle is high Q plus a locked PLL** — the next stage.

### Stage 3 — The phase-locked loop (entrainment)

Here is the stage that makes the COB more than a passive resonator. A **phase-locked loop (PLL)** is a circuit that makes one oscillator *track* another. It compares its own phase to an external reference, and continuously nudges itself until the two are in step — "locked." Once locked, it follows the reference's frequency even as that reference drifts. PLLs are how a radio stays tuned to a station and how your circadian clock follows the sunrise. In the COB, the PLL is the mechanism of **entrainment**: how an internal habit-rhythm can be pulled into step with an external rhythm.

It has three parts, and each maps to a canonical Noetic:

- **Phase detector — `^1^C` (Mind).** `^1` Mind is *awareness that processes and compares Ideas.* The phase detector is the part of the system that *notices* the difference between its internal rhythm and an external one — "I am checking far more often than my partner thinks is normal." It runs in the Cognitive domain because it is a comparison, a piece of awareness, not yet an action. Note: this is `^1` **Mind**, the comparing-awareness — never call it "Differentiation."
- **Loop filter — `^4^E` (Vibration).** `^4` Vibration is *the degree to which an Idea resonates with the Mind, its impression.* The loop filter *integrates the phase error over time* — it smooths the moment-to-moment comparison into a steady, accumulating impression of how far off the rhythm is. A raw phase detector is jittery; the filter is what lets the system respond to the *trend* rather than every twitch. It runs in the Evaluative domain. This is `^4` **Vibration**, the accumulating resonance — never call it "Integration."
- **VCO (voltage-controlled oscillator) — `^3^O`.** The VCO is the *output* oscillator whose frequency the loop adjusts. `^3` Negative in the Operational domain: the felt push to *change the behavioral output* to close the gap. As the filtered error says "you're firing too fast," the VCO slows the actual behavior toward the reference.

Two ranges govern whether the PLL can do its job, and they are different sizes on purpose:

| Range | What it is | Cognitive meaning |
|---|---|---|
| **Capture range** | The band of external frequencies the PLL can *grab onto* from an unlocked start. | How close a new external rhythm must be before the habit will even begin to entrain to it. |
| **Lock range** | The (wider) band the PLL can *hold onto* once locked. | Once entrained, how far you can drag the rhythm before the habit breaks free again. |

The lock range is wider than the capture range — it is easier to *keep* a habit in step than to *get* it there. This is the entire engineering basis of entrainment therapy: you cannot yank a compulsion straight to a healthy rate (that's outside the capture range — the PLL never grabs), but you *can* capture it at a nearby rate and then slowly drag it, staying inside the lock range, all the way to the target.

### Stage 4 — The duty-cycle modulator

The PLL fixes *frequency*. The **duty-cycle modulator** shapes the *waveform* — what fraction of each cycle the behavior is "ON." Two drives set it:

- **F5 Agency high → longer ON.** Strong agency means the behavior, once triggered, runs longer and more forcefully — a wider pulse.
- **F6 Structure high → disciplined cycle.** Strong structure means clean, even, predictable cycles — sharp edges, consistent timing.

A habit can have the same frequency but very different duty cycles: a brief, sharp check every two hours is low duty cycle; a two-hour spiral every two hours is high duty cycle, and far more disabling even at identical f0.

## Worked Build: A Compulsive Checking Loop

Now we author the man from the opening as a COB, in CCDL. He checks every two hours — twelve times a day — so we model the loop at `f0 = 12/day`. The cycle is high-Q (rigid, self-restoring) and we will demonstrate two things: that a healthy external rhythm can capture it via the PLL, and what happens to f0 when we reduce L.

```cas
circuit compulsive_checking_loop {
    input:  internal_anxiety;
    output: checking_behavior;

    // --- Stage 1: master clock (Rhythm, embodied, operational) ---
    node clock: ^7^O|E;

    // --- Stage 2: the LC tank that sets the habit's frequency ---
    // The Phi sequence the habit traverses each cycle:
    let check_cycle = Phi< ^8^C|A,    // a trigger surfaces ("did I lock it?")
                           ^3^E|f,     // felt aversion / dread of the unlocked door
                           ^3^O|E,     // the embodied act of going to check
                           ^9^C|A >;   // momentary relief: "it's locked" (the effect)

    inductor L_struct: Inductor< check_cycle, L = F6_weight >;   // F6 Structure = 0.85 (high inertia)
    capacitor C_emot:  Capacitor< ^5^E,       C = F4_weight >;   // F4 Connection = 0.70 (high charge)

    tank habit: LC< L_struct, C_emot >;
    // f0 = 1/(2π√(LC)) -> modeled at 12/day ; Q -> 9.0 (HIGH: compulsive signature)

    // --- Stage 3: phase-locked loop (entrainment path) ---
    node phase_det:  ^1^C;     // Mind compares internal rhythm vs external reference
    node loop_filt:  ^4^E;     // Vibration integrates the phase error
    node vco:        ^3^O;     // push to adjust behavioral output toward reference

    pll entrain: PLL< detector  = phase_det,
                      filter    = loop_filt,
                      vco       = vco,
                      reference = external_rhythm,
                      capture_range = 0.20,    // ±20% of current f0 — can only grab a NEARBY rhythm
                      lock_range    = 0.55 >;  // ±55% — can be DRAGGED far once locked

    // --- Stage 4: duty-cycle modulator ---
    modulator duty: DutyCycle< on_drive = F5, structure_drive = F6 >;
    // F5 Agency 0.40 -> moderate ON width ; F6 0.85 -> very disciplined, sharp-edged cycle

    // --- diagnostic / therapeutic test points ---
    probe tp_freq: habit;        // measure f0 and Q
    probe tp_lock: entrain;      // is the PLL locked? to what reference?
    probe tp_duty: duty;         // ON-fraction of each cycle
}
```

> **Bench Notes — reading this build.**
> - **Q = 9.0 is the alarm.** A Q this high means the loop snaps back to exactly 12/day after any perturbation. That self-restoring stiffness, *combined with* a PLL that locks hard to its own internal reference, is the structural definition of a compulsion on this board. Neither alone is pathological — a disciplined exercise habit is also high-Q. It is high-Q *locked to a maladaptive rhythm* that flags.
> - **The `Phi` cycle is where the content lives.** Note the `^3^E|f` (felt dread) → `^3^O|E` (the embodied checking act) → `^9^C|A` (the relief). The relief at the end is what *recharges the capacitor* — the emotional payoff is the energy source that keeps the tank ringing. Break the relief and you drain the tank; that is a different intervention (covered under therapeutic mode).
> - **The compiler will reject a PLL whose `capture_range` exceeds its `lock_range`.** That ordering is physical law for this component: you cannot capture across a band wider than you can hold. Authoring `capture_range = 0.6, lock_range = 0.55` is a design error, not a clever trick.

### Demonstrating PLL lock to a healthy external rhythm

The patient's partner keeps a normal evening routine — say, a single lock-up check at bedtime, a rhythm of roughly `f = 1/day`. Can the PLL lock the compulsive loop directly to that? **No** — `1/day` is an 92% drop from `12/day`, far outside the `capture_range = ±20%` (which only reaches down to ~`9.6/day`). The detector sees an error so large it never grabs; the loops run independently. This is the engineering reason direct exhortation ("just check once a day!") does nothing: the target is outside the capture range, so no entrainment even begins.

But pick a reference *inside* the capture range — `f = 10/day` (a structured routine of checking every ~2.4 hours instead of every 2) — and the phase detector `^1^C` registers a small, closeable error. The loop filter `^4^E` integrates it into a steady correction signal, the VCO `^3^O` nudges the behavioral output, and within a few cycles `tp_lock` reports **locked at 10/day**. The habit is now *entrained to an external reference* rather than free-running. That is the foothold.

### The frequency shift when L is reduced

Once locked, two levers move f0. The PLL can *drag* the reference (staying inside the wider `lock_range`), and we can directly *retune the tank* by changing L or C. Consider reducing the inductor — lowering the F6 Structure weight that gives the habit its inertia, from `0.85` to, say, `0.30` (in practice: loosening the rigid "it MUST be checked" structural rule). Because `f0 = 1/(2π√(LC))` and f0 scales as `1/√L`, cutting L by a factor of ~2.8 *raises* f0 by √2.8 ≈ 1.67× — the loop gets *faster and looser*, and critically its **Q drops** (Q ∝ √(L/C)), so the resonance broadens. A broader, lower-Q tank is far easier for the PLL to drag. This is the counter-intuitive but correct sequencing: you first make the habit *less* rigid (lower L, lower Q, even if briefly faster), which widens the lock range, and *then* you walk the entrained frequency down to the target. Loosen, then lower.

## Diagnostic Mode and Therapeutic Mode

The COB runs in two operating modes, like a piece of test equipment that can both measure and source a signal.

**Diagnostic mode — the forced frequency sweep.** To characterize an unknown habit loop, you do exactly what a bench engineer does to find a circuit's resonance: you *sweep*. You present the cognition with rhythmic prompts across a range of frequencies and watch where it responds strongly. The frequency at which the response peaks is f0; the *narrowness* of that peak is Q. A sharp, tall spike at one frequency = high-Q compulsion. A broad, low hump = a loose, low-Q preference. The sweep turns a vague "he checks a lot" into two numbers — f0 and Q — that you can act on.

**Therapeutic mode — gradual L/C adjustment.** Once characterized, you shift the resonant frequency *slowly*, never abruptly. Two knobs:

- **Lower L (F6 Structure weight):** loosens the habit, broadens Q, widens the lock range. Do this *first*.
- **Lower C (F4 Connection weight):** drains emotional charge from the cycle (e.g., by interrupting the `^9` relief payoff so each cycle deposits less energy back into the capacitor). Lowering C *raises* Q, so it sharpens — use it to *settle* a loop at a new target once you've arrived, not to move it.

The therapeutic arc is therefore: **sweep to characterize → capture with a nearby reference → lower L to loosen → drag the entrained frequency down inside the lock range → lower C to settle at the target.** Slow throughout: every adjustment must stay inside the PLL's lock range, or the loop breaks free and snaps back to its old f0.

> **Bench Note — why "gradual" is non-negotiable.** A jump from 12/day to 4/day is a 67% drop, well outside any sane lock range. Attempt it and the PLL loses lock; the high-Q tank, unentrained, rings straight back to 12/day. The frustration of "I tried to quit cold and it came right back" is, in this model, simply a lock-range violation. The fix is not more willpower; it is a smaller step that stays inside the lock range.

## Datasheet — COB Parameters

| Parameter | Symbol | Set by | Meaning | Typical design range |
|---|---|---|---|---|
| Natural frequency | `f0` | `1/(2π√(LC))` | How often the loop fires | model-specific (e.g., 12/day) |
| Quality factor | `Q` | `√(L/C)/R_loss` | Sharpness / rigidity of the habit | 0.5 (loose) – 10 (compulsive) |
| Inductance | `L` | F6 Structure weight | Habit inertia; resistance to change | 0.0 – 1.0 |
| Capacitance | `C` | F4 Connection weight | Stored emotional charge | 0.0 – 1.0 |
| Capture range | — | PLL design | Band it can entrain to from unlocked | ±10% – ±30% of f0 |
| Lock range | — | PLL design | Band it can hold once locked | ±30% – ±70% of f0 |
| Duty cycle | — | F5 Agency / F6 Structure | ON-fraction of each cycle | 0.05 – 0.60 |
| Clock state | — | `^7^O\|E` | Master Rhythm oscillator | fixed |

## Failure Modes

| Failure | Signature on the board | What it means | Detection |
|---|---|---|---|
| **Compulsive lock** | High Q (>6) + PLL locked to internal reference | A rigid, self-restoring loop entrained to a maladaptive rhythm | `tp_freq` (Q) + `tp_lock` |
| **Lock-range violation** | PLL drops lock mid-therapy; f0 snaps to old value | Therapeutic step was too large | `tp_lock` flips locked→unlocked |
| **Runaway sharpening** | Q climbs over sessions | Lowering C without lowering L first; tank narrows | trend on `tp_freq` Q |
| **Duty-cycle bloat** | Same f0, rising ON-fraction | Cycles getting longer/more disabling even at fixed rate | `tp_duty` |
| **Capture failure** | PLL never locks to a reference | Reference offered is outside capture range | `tp_lock` stays unlocked |
| **Circadian desync** | Clock `^7^O\|E` free-runs off external day/night | Internal rhythm decoupled from environmental reference | sweep vs. external rhythm |

## Applications

- **Compulsive-cycle diagnosis.** The high-Q-plus-locked-PLL signature is the board's headline diagnostic: it distinguishes a *compulsion* (rigid, self-restoring, entrained to a bad rhythm) from a mere *strong preference* (high-Q but not maladaptively locked) and from a *passing worry* (low-Q, no lock). The frequency sweep produces the f0 and Q that make the distinction concrete.
- **Entrainment therapy.** The PLL is the formal model of why slow, nearby-reference rhythm-shifting works where willpower fails: capture inside the capture range, then drag inside the lock range. Every "cold turkey snapback" is a lock-range violation in this framework.
- **Circadian modeling.** A sleep/wake cycle is the cleanest natural COB: `^7^O|E` clock, an LC tank set by the body's inertia and the day's emotional load, and a PLL that entrains to the external light/dark reference. Jet lag is the PLL re-capturing a shifted reference; shift-work disorder is chronic capture failure.
- **Habit formation and breaking.** Building a *good* habit is raising L and C until the tank rings on its own (it becomes self-sustaining — Chapter 13's positive-feedback oscillator). Breaking a *bad* one is the therapeutic arc above: loosen L, drag the frequency, settle with C. The COB models both directions on the same board.

## Key Takeaways

- The **COB** is the second reference board (alongside the CSB): a *clock and tuner* for rhythmic, habitual cognition — model a habit loop, diagnose compulsive locking, drive entrainment therapy. It is built on Chapter 13's oscillator theory.
- The **master clock is `^7^O|E`** — `^7` **Rhythm** (canonical), the Noetic that *is* periodicity, running as an embodied operational cycle.
- The **LC tank** sets the habit's frequency: **L = F6 Structure weight** (inertia, resistance to change), **C = F4 Connection weight** (stored emotional charge), `f0 = 1/(2π√(LC))`, and **Q = the sharpness of the habit**. High Q is the compulsive signature.
- The **PLL entrains** an internal rhythm to an external one. Its parts are `^1^C` **Mind** (phase detector — comparing awareness, *not* "Differentiation"), `^4^E` **Vibration** (loop filter — accumulating impression, *not* "Integration"), and `^3^O` (VCO — push to adjust output). **Capture range < lock range:** easier to hold a rhythm than to grab it.
- The **duty-cycle modulator** shapes the waveform: **F5 Agency → longer ON**, **F6 Structure → disciplined cycle**.
- **Diagnostic mode** is a forced frequency sweep (find f0 and Q); **therapeutic mode** is gradual L/C adjustment — **loosen (lower L) first, then lower the frequency inside the lock range, then settle (lower C).** Jumps that exceed the lock range snap back.
- **All frequencies and Q values in this chapter are design values, not measurements.** The COB is a modeling-and-intervention design.

---

## Exercises

**Exercise 19.1: Read the Tank**

A habit loop is modeled with `L = F6_weight = 0.81` and `C = F4_weight = 0.64`.

a) Using `f0 = 1/(2π√(LC))`, is this loop's natural frequency higher or lower than a second loop with `L = 0.20, C = 0.64`? (You don't need a calculator — reason from the formula.)
b) Using `Q ∝ √(L/C)`, which of the two loops is sharper (more compulsive in signature)?
c) In plain words, what does the high-L loop "feel like" compared to the low-L loop?

**Exercise 19.2: Diagnose the Signature**

For each description, state whether the board would flag it as a **compulsion**, a **strong preference**, or a **passing worry**, and name the two test points (`tp_freq` / `tp_lock`) you'd read to decide:

a) Fires at a sharp, narrow peak at one frequency on the sweep; PLL locked to its own internal reference; Q = 8.5.
b) A tall-ish but broad hump on the sweep; Q = 1.2; PLL not locked to anything maladaptive.
c) A single low, wide bump; Q = 0.4; no lock.

**Exercise 19.3: Write the Board (CCDL)**

A nail-biting habit fires roughly **20 times a day**, is *highly* emotionally charged (high C) but *not* very structurally rigid (low L), and runs in short, sharp bursts (low duty cycle, disciplined edges). Author a COB for it in CCDL. You must:

a) Write the four-state `Phi` cycle (trigger → felt state → embodied act → effect), using canonical Noetics.
b) Set `L_struct` and `C_emot` with F6 and F4 weights that match "high charge, low rigidity."
c) Set the duty-cycle modulator's drives to match "short, sharp bursts."
d) Add the three correctly-named PLL nodes (`^1^C`, `^4^E`, `^3^O`) and one diagnostic probe.

(Answer in Appendix E.)

**Exercise 19.4 — Marquee: Design the Entrainment Intervention**

A patient has a compulsive checking cycle modeled at **f0 = 12/day** (checking every 2 hours), high-Q (Q = 9.0), PLL locked to its own internal reference. The clinical goal is to shift the cycle to **f = 4/day** (every 6 hours). A direct jump fails — explain why, then design a **PLL-entrainment intervention** that reaches 4/day. Your answer must:

a) Explain, in terms of **capture range** and **lock range**, why offering a 4/day reference to the untreated 12/day loop produces no entrainment at all.
b) Choose a *first* external reference frequency inside the capture range (±20% of f0) that the PLL *can* capture, and say what real-world routine it corresponds to.
c) Specify the order of tank adjustments — **when to lower L, when to drag the frequency, when to lower C** — and justify the ordering using how L and C each affect Q and the lock range.
d) Lay out the step-down schedule from 12/day to 4/day as a sequence of references, each step staying inside the lock range (±55% of the *current* f0), and state how you'd read `tp_lock` to confirm the loop never breaks free.

(Full worked answer in **Appendix E**. Reminder: all frequencies and Q values here are design values, not measurements from a patient.)
