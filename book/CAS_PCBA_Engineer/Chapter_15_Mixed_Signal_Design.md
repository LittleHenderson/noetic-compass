# Chapter 15: Mixed-Signal Design — Analog Meets Digital

A thermostat on a wall is two machines pretending to be one. There is a strip of metal that bends a little more for every degree of warmth — a smooth, continuous, *analog* response that has no steps in it at all. And there is a relay that is either closed or open, furnace on or furnace off — a hard, two-state, *digital* response with nothing in between. The whole art of the thermostat is the handoff: turning the metal strip's gradual bend into a clean on/off decision, and turning that decision back into the physical act of firing a burner. Get the handoff wrong and the furnace chatters — on, off, on, off, ten times a minute — burning itself out while the room never settles.

Almost every interesting machine is like this. The microphone hears a continuous pressure wave; the computer stores discrete numbers. The car's accelerator pedal moves through every angle between rest and floor; the engine controller decides in fixed steps how much fuel to inject. Engineers call these **mixed-signal** systems: circuits where the smooth, continuous world of *analog* meets the stepped, countable world of *digital*, and the two have to talk. The components that do the talking — analog-to-digital converters, digital-to-analog converters, sampling clocks, anti-aliasing filters — are some of the most carefully designed parts on any board, because the boundary between continuous and discrete is exactly where information gets lost.

Cognition is a mixed-signal system too. A felt sense — the slow accumulation of unease about a person you keep working with — is analog: continuous, graded, without sharp edges. The sentence you finally say to yourself, *"I don't trust them,"* is digital: a discrete proposition, true or false, that you can reason with and act on. Between the feeling and the sentence sits a conversion. And just as in electronics, that conversion can be done well or badly. Sample the feeling too rarely and you misread it. Crush its nuance into two or three coarse boxes and you lose what mattered. Let the analog feeling and the digital conclusion bleed into each other without a clean boundary, and you get the cognitive equivalent of a chattering furnace.

This chapter is about that boundary. In CAS terms, it is a chapter about **Register translation** — moving a cognitive state between the four Registers we learned in Chapter 2 (`|T`, `|A`, `|f`, `|E`), where some Registers are fundamentally analog and one is fundamentally digital. We will build a converter that samples a felt experience and turns it into explicit self-knowledge, measure what it loses in the process, and learn the design rules that keep the loss small.

## Analog Cognition: the Continuous State Space

Start with what *analog* actually means. An analog signal is one that varies smoothly and can take any value in a range — between any two values there is always another value. A dimmer knob is analog; a light switch is not. The defining property is *continuity*: no gaps, no steps, infinite resolution in principle.

CAS has a continuous state space at its core, and we met it in Chapter 2 without naming it as such. A cognitive state is not really one of forty discrete boxes. It is a point on the **open probability simplex** — written `Δ39°` — a smooth forty-dimensional surface where the activation of each of the forty cognitive states is a positive number and all forty sum to one. "Open" means none of them is ever exactly zero; every state is at least faintly present. The distance between two points on this surface is measured by the Fisher-Rao geodesic, `d_FR(p,q) = 2·arccos(Σ√(pₖqₖ))`, the same metric the CJT uses for gain (Chapter 4). The point is that the underlying space is *continuous*. A cognitive state can drift by any tiny amount in any direction. There are no steps in `Δ39°`.

Two of the four Registers live naturally in this continuous space:

- **`|f` Affective** — the value-laden, feeling-toned Register. A felt response has no sharp edges. Mild discomfort shades into real aversion shades into revulsion with no line you can point to. Affective cognition is *analog by nature*: a `^3^E|f` (felt evaluative aversion) can be present at any intensity at all.
- **`|E` Embodied** — the sensorimotor, concrete Register. A gut reaction, a kinesthetic sense, a real-time control loop reading a continuous sensor. Embodied cognition tracks a continuous world and responds continuously. A hand tightening on a railing tightens by degrees, not in clicks.

These are the **analog Registers**. They carry graded, smooth, high-resolution information. Their strength is exactly that resolution: a felt sense can hold a thousand shades of a situation at once. Their weakness is that you cannot easily reason *with* a feeling, log it, audit it, or pass it cleanly to another stage of a circuit. For that, you need to digitize.

## Digital Cognition: Discrete State Transitions

A digital signal is the opposite: it takes only a fixed set of distinct values — classically just two, but more generally a countable set of clean, separated levels. Between the levels, nothing is allowed. The strength of digital is that it is *robust and manipulable*. A digital "1" stays a "1" even if the voltage carrying it sags a bit, because anything above the threshold counts as a 1. You can copy it perfectly, store it, run logic on it, and reason about it without the value smearing.

In CAS, the digital Register is:

- **`|A` Analytical** — the explicit, sequential, logical, reason-based Register. An analytical state is a discrete proposition. *"This argument has three premises; the second is false; therefore the conclusion does not follow."* Each step is a clean, separable token you can write down, check, and chain. Analytical cognition moves in discrete state transitions — one explicit step `->` the next — exactly the chained-arrow form from Chapter 2.

The fourth Register, **`|T` Transcendent**, sits above this distinction; it is the high-abstraction, purpose-orienting mode, and it can be carried in either an analog or a digital fashion depending on the work. For this chapter the live contrast is between the **analog Registers** (`|f`, `|E`) and the **digital Register** (`|A`).

The mixed-signal problem is now sharp. The richest cognitive information often arrives in `|f` or `|E` — analog, graded, continuous. But the parts of a cognitive circuit that *reason, log, and decide* run in `|A` — digital, discrete, step-by-step. To get from the felt input to the reasoned output, you must convert across the Register boundary. That conversion has a name in both substrates.

## ADC and DAC: Converting Across the Register Boundary

In Chapter 10 we introduced the two converters that bridge analog and digital, and we lean on them directly here. An **analog-to-digital converter (ADC)** takes a smooth continuous signal and produces a sequence of discrete numbers — it *samples* the analog value at intervals and *quantizes* each sample to the nearest available level. A **digital-to-analog converter (DAC)** runs the other way: it takes discrete numbers and reconstructs a smooth continuous output.

The CAS mapping is direct, and it is the spine of this chapter:

| Converter | Electronic job | CAS Register translation | Reads as |
|---|---|---|---|
| **ADC** | continuous voltage → discrete numbers | **`\|f -> \|A`** | converting felt experience into explicit analysis |
| **DAC** | discrete numbers → continuous voltage | **`\|A -> \|E`** | converting an analytical plan into embodied action |

The **ADC direction, `|f -> |A`**, is *making sense of a feeling*. You start with an analog affective state — a felt unease, a drawn-toward pull — and you produce a discrete analytical proposition you can reason with: *"I notice I distrust this person, for reasons X and Y."* The smooth feeling becomes a countable, checkable claim. This is what a person does in good reflection, and what a well-built cognitive circuit does when it has to act on an affective signal: it digitizes the feeling so the analytical stages downstream can use it.

The **DAC direction, `|A -> |E`**, is a second directed conversion: *turning a plan into action*. It runs from discrete control toward continuous output, but it is **not the inverse of the ADC's lossy `|f -> |A` translation**. It also lands in a different Register (`|E`, not `|f`). You start with a discrete analytical plan — *"Step one: send the email. Step two: call the vendor."* — and reconstruct it as continuous embodied execution, the smooth sensorimotor act of actually doing the thing. A plan that never gets DAC-converted stays a string of propositions; the DAC is what gives it a body.

Both conversions are *lossy at the boundary*, and the rest of the chapter is about exactly how much they lose and how to keep that loss within spec.

## Sampling Rate: How Often You Digitize

An ADC does not watch the analog signal continuously — it cannot, because its output is a sequence of discrete numbers. Instead it takes a snapshot at regular intervals: a **sample**. The **sampling rate** is how many samples it takes per second, measured in hertz (Hz, samples per second). A higher sampling rate means more snapshots, finer time resolution, and a more faithful digital picture of the analog original. A lower rate means fewer snapshots and a coarser picture.

The cognitive analog is *how often you check in with the felt signal and convert it to an explicit thought.* A person who pauses to ask *"how am I actually feeling about this?"* once a day is sampling their `|f` state at a low rate. A person who does it ten times an hour is sampling at a high rate. In a cognitive circuit, the sampling rate is set by how frequently the ADC stage fires the `|f -> |A` conversion as the affective input drifts over time.

Sampling rate is a *design parameter*, not a fact of nature. You choose it. And the central result of mixed-signal engineering — the one law you must not violate — tells you how to choose it: it depends entirely on how fast the analog signal itself is changing.

## Aliasing: Undersampling and the Nyquist Limit

Here is the failure that haunts every ADC. If you sample an analog signal *too slowly* relative to how fast it is moving, you do not merely get a coarse picture — you get a *wrong* picture, one that confidently misrepresents the signal as something it never was. This is **aliasing**: a fast signal, undersampled, masquerades as a slow signal that was never there.

The wagon-wheel effect in old films is aliasing you can see. A wheel spinning forward, filmed at twenty-four frames per second, can appear to spin slowly backward — because between frames each spoke moves nearly all the way to where the *next* spoke was, and the camera, sampling too slowly, reads that as a small backward step. The camera is not noisy. It is lying, cleanly and consistently, because it undersampled.

The law that prevents this is the **Nyquist criterion**: to faithfully capture a signal that oscillates at a given frequency, you must sample at **more than twice** that frequency. Sample at exactly twice or less, and aliasing sets in — the fast oscillation folds down and impersonates a slow one. Twice the highest frequency present is the **Nyquist rate**; sampling below it is undersampling, and undersampling produces aliases.

The cognitive failure is precise and familiar. Suppose your felt sense of a situation is genuinely *oscillating* — swinging between drawn-toward and repelled, `^2^E|f` and `^3^E|f`, on some cycle, the way ambivalence about a hard decision can swing back and forth within an hour. If you only check in with that feeling once a day, you will sample it at whatever phase you happen to catch and conclude, with total confidence, that you feel *one steady way* about the matter. You have aliased a rapidly oscillating affective state down to a false steady reading. The conclusion is not vague — it is *wrong*, and it feels certain, which is what makes aliasing so dangerous. The fix is the same as in silicon: sample faster than twice the rate of the underlying cognitive oscillation, or filter the fast oscillation out before you sample so it cannot fold down and lie to you. (That pre-sample filter is the **anti-aliasing filter** — a low-pass filter, in the family we built in Chapter 12, placed *before* the ADC.)

> **Bench Note — aliasing produces confident wrong answers, not obvious noise.** This is the trap. A noisy reading announces itself; an aliased reading looks clean. A cognitive circuit that samples an oscillating `^*^E|f` input too slowly will emit a steady, well-formed `|A` conclusion that is simply false about the input. There is no error flag, because nothing *malfunctioned* — the ADC did exactly what it was told, too slowly. Always size the sampling rate against the *fastest* oscillation the affective input can carry, not the average.

## Quantization Error: the Gap Between Felt Nuance and Discrete Categories

Sampling is about *when* you snapshot. **Quantization** is about *how finely you measure* each snapshot. An ADC has a fixed number of output levels — say, 256 of them for an 8-bit converter. Every analog sample, no matter how precise, must be rounded to the nearest available level. The small unavoidable rounding gap between the true analog value and the nearest digital level is the **quantization error**. More levels (more bits) means smaller steps and smaller error; fewer levels means coarser steps and larger error.

In Register translation, quantization error is **the gap between felt nuance and the discrete categories you have words for.** Your `|f` affective state holds a continuous, high-resolution impression — a specific shade of unease that is not quite worry, not quite resentment, not quite grief, but some exact blend. When you digitize it into `|A`, you must round it to the nearest *available analytical category* — the nearest word, the nearest proposition you actually possess. *"I feel… frustrated, I guess."* The word "frustrated" is the nearest digital level. The distance between the true felt shade and that word is the quantization error. It is why "I can't quite put it into words" is a literal, structural statement: the felt value falls *between* your available levels, and digitizing forces it to the nearest one, discarding the remainder.

The engineering levers are the same in both substrates. To reduce quantization error, add levels: a richer analytical vocabulary, finer-grained categories, more propositions to round to. A person with a large, precise emotional vocabulary has a higher-bit ADC — they round felt states to closer levels and lose less. A person with three words for everything they feel has a coarse converter, and most of the nuance falls into the gaps.

## Worked Build: an ADC for Accumulated Emotional Experience

Time to build one. We will design an ADC stage that samples a continuous affective input — accumulated emotional experience — and converts it into discrete, explicit self-knowledge. In CAS terms, we are converting:

- **Input (analog):** `^5^E|f` — accumulated experience (`^5` Female), in the Evaluative domain, carried in the **Affective** Register. This is the felt, continuous residue of everything that has happened to the system: the smooth, high-resolution "sense of how things have gone."
- **Output (digital):** `^5^C|A` — the *same* accumulated experience (`^5` Female), now in the Cognitive domain, carried in the **Analytical** Register. This is explicit self-knowledge: discrete propositions about one's own formation that can be reasoned with, logged, and audited.

Note what changes and what does not. The Noetic stays `^5` Female throughout — we are not creating new experience, only re-Registering existing experience. The Domain rises from Evaluative to Cognitive (felt judgment becomes explicit reasoning), which is a normal upward move toward analysis. The Register flips from analog `|f` to digital `|A`. This is the ADC, written as a Register translation.

```cas
circuit experience_adc {
    input:  felt_experience;     // continuous affective input
    output: self_knowledge;      // discrete analytical output

    // the analog source state and the digital target state
    node felt:     ^5^E|f;       // accumulated experience, felt (continuous)
    node insight:  ^5^C|A;       // accumulated experience, explicit (discrete)

    // bias substrate: the analytical vocabulary the ADC rounds to.
    // richer vocabulary = more quantization levels = smaller error.
    node bias_vocab: ^5^P_{F2}|A;

    // anti-aliasing pre-filter: low-pass the felt input BEFORE sampling,
    // so fast affective oscillations cannot fold down into a false steady reading.
    filter antialias: LowPass< ^5^E|f, cutoff=0.5 >;   // pass slow drift, block fast swing

    // the ADC itself, modeled as a CJT that converts felt -> explicit.
    // sample_rate is the design knob (samples per unit time);
    // levels is the quantization resolution (count of analytical categories).
    cjt adc: CJT< antialias | bias_vocab => insight >
             [β=1.0, sample_rate=4.0, levels=16];

    // a clean-threshold guard on the output so borderline samples don't
    // chatter between two adjacent categories (Schmitt trigger, below).
    schmitt out_guard: Schmitt< insight, high=0.6, low=0.4 >;

    probe tp_felt:    felt;        // watch the analog input
    probe tp_insight: insight;     // watch the digital output
    probe tp_qerror:  adc.quantization_error;   // watch the rounding gap
}
```

Walk it line by line. `felt` is the analog source: `^5^E|f`, continuous accumulated feeling. `insight` is the digital target: `^5^C|A`, the same experience re-Registered as explicit propositions. `bias_vocab` is the ADC's reference ladder — the analytical categories the converter rounds each sample to; in a transistor ADC this is the resistor ladder that sets the levels, and here it is the system's available vocabulary for talking about its own formation. The `antialias` filter low-passes the felt input first, so a rapidly swinging `^*^E|f` cannot alias. The `adc` CJT does the conversion, parameterized by `sample_rate` (how often it fires) and `levels` (how finely it quantizes). The `out_guard` Schmitt trigger cleans up the digital output, which we explain next.

> **Bench Note — measuring the quantization error.** The quantization error of this ADC is the Fisher-Rao distance between the true felt state and the digital state it rounded to: `q_error = d_FR(felt_true, insight_rounded)` on the simplex `Δ39°`. With `levels=16` the categories are coarse and `q_error` is larger; raising `levels` (a richer analytical vocabulary) packs the categories closer and shrinks `q_error`. You read it at the `tp_qerror` probe. **Honesty line:** the specific numbers here — `sample_rate=4.0`, `levels=16`, `cutoff=0.5` — are *design choices* that illustrate the construct. They are not measured outputs of any model run. This is a design handbook; the ADC is the language you author in, and these parameters are values you select on the bench, not benchmark results.

## The Schmitt Trigger, Revisited

We met the **Schmitt trigger** in Chapter 10: a comparator with two different thresholds, a high one to switch on and a lower one to switch off. The gap between them is **hysteresis**, and it is exactly what stops a noisy analog input from producing a chattering digital output. Without hysteresis, an input hovering right at a single threshold will flip the output on-off-on-off with every tiny wobble of noise — the chattering furnace from the chapter's opening. With two thresholds, once the output switches high it stays high until the input drops all the way down to the *low* threshold, so small wobbles in the middle are ignored.

In mixed-signal cognition this is the difference between a clean decision and an agonized one. Suppose the digitized self-knowledge is near a category boundary — the felt evidence is *almost* enough to conclude "I distrust this person" but keeps nudging just over and just under the line. A single-threshold converter would flip the conclusion back and forth with every passing thought: *trust, distrust, trust, distrust* — a `^2^C|A` ⇄ `^3^C|A` chatter that never settles and exhausts the system. The Schmitt trigger's hysteresis fixes it: once the conclusion has crossed the *high* threshold into "distrust," it holds there until the felt evidence falls all the way back to the *low* threshold. The decision is stable against noise without being deaf to a real, sustained change. That is why `out_guard` sits on the ADC's output — it converts a noisy near-boundary analog read into a clean, committed digital state.

## Mixed-Signal Grounding: Keep the Analog and Digital Grounds Separate

There is a rule on every mixed-signal board that beginners always violate and always regret: **keep the analog ground and the digital ground separate, joined at exactly one point.** "Ground" is the common reference every voltage is measured against. Digital circuits switch hard and fast, dumping sharp current spikes into their ground. If the sensitive analog section shares that same ground, those spikes ride into the analog signal as noise — the clean continuous measurement gets contaminated by the digital section's switching racket. The fix is a **split ground plane**, the two halves tied together at a single star point so currents don't cross-contaminate.

The cognitive version is just as real. The analog Registers (`|f`, `|E`) and the digital Register (`|A`) need their own clean reference, and **bleed between them causes trouble in both directions:**

- **Digital bleeding into analog** — letting the analytical conclusion contaminate the felt reading. You decide, in `|A`, that you *should* feel fine about something, and that conclusion leaks back into the `|f` channel and overwrites what you actually feel. Now your "felt" input is no longer an independent measurement; it is an echo of your conclusion, and the ADC is sampling its own output. The circuit has lost its sensor.
- **Analog bleeding into digital** — letting raw affect crash through into the reasoning before it has been cleanly converted. The `|f` state floods the `|A` stage directly, unsampled and unquantized, and the analytical reasoning gets swamped by undigitized feeling — conclusions that lurch with every mood swing because the digital section never got a clean, stable sample to work from.

The design rule is to give the analog and digital Registers their own clean reference and join them at *one* deliberate point: the ADC itself. The felt channel feeds the analytical channel **only through the converter**, never by direct leakage. Everywhere else, the grounds stay split. This is mixed-signal grounding applied to Register architecture, and it is why a well-built cognitive circuit keeps `|f` and `|A` on separate rails that meet only at a designed conversion stage.

> **Bench Note — the single-point join is the ADC, full stop.** If a schematic shows the `|f` rail and the `|A` rail touching anywhere *other* than a declared converter — a stray `+` co-presence that lets felt and analytical states share a node, or a feedback path from an `|A` conclusion straight onto an `|f` input — that is a grounding fault. The fix is to route the connection through an ADC (`|f -> |A`) or a DAC (`|A -> |E`) so the boundary is a designed conversion, not an accidental bleed.

## Datasheet: Mixed-Signal Conversion Parameters

| Parameter | Meaning | Typical design range | Failure if mis-set |
|---|---|---|---|
| `sample_rate` | how often the ADC fires `\|f -> \|A` (Hz) | > 2× fastest input oscillation | too low → **aliasing** (false steady reading) |
| `levels` | quantization resolution (count of analytical categories) | 8–256 (3–8 "bits") | too few → large **quantization error** |
| `q_error` | Fisher-Rao gap `d_FR(felt, rounded)` | minimize; rises as `levels` falls | high → felt nuance discarded |
| `antialias.cutoff` | pre-sample low-pass corner | below half the sample_rate | too high → fast swings alias through |
| `schmitt.high/low` | output hysteresis thresholds | gap sized to noise amplitude | gap too small → output **chatter** |
| ground split | analog/digital rails joined at one point | join only at the converter | multi-point join → cross-contamination |

## Failure Modes

| Failure | Symptom | Root cause | Detection |
|---|---|---|---|
| **Aliasing** | confident, steady `\|A` conclusion that is false about the input | `sample_rate` below Nyquist for an oscillating `^*^E\|f` input | compare conclusion stability against known input oscillation; add anti-alias filter |
| **Quantization starvation** | "I can't put it into words"; flattened, generic conclusions | `levels` too low — coarse analytical vocabulary | high `q_error` at `tp_qerror`; widen the category ladder |
| **Output chatter** | conclusion flips between involution pair (`^2^C\|A` ⇄ `^3^C\|A`) | no hysteresis on a near-boundary digital output | watch `tp_insight` oscillate; add a Schmitt trigger |
| **Ground bleed (digital→analog)** | "felt" reading echoes a prior conclusion | `\|A` output feeds back onto the `\|f` input | trace for an `\|A -> \|f` path that doesn't go through a DAC/ADC |
| **Ground bleed (analog→digital)** | reasoning lurches with every mood swing | raw `\|f` floods `\|A` without conversion | trace for `\|f` and `\|A` sharing a node outside the converter |

## Key Takeaways

- **Mixed-signal cognition** is Register translation across a continuous/discrete boundary. The **analog Registers** are `|f` Affective and `|E` Embodied (graded, high-resolution, living on the open simplex `Δ39°`); the **digital Register** is `|A` Analytical (discrete, robust, manipulable propositions).
- **ADC is `|f -> |A`** — converting felt experience into explicit analysis. **DAC is `|A -> |E`** — converting an analytical plan into embodied action. Both are lossy at the boundary.
- **Sampling rate** is how often you digitize the felt signal. By the **Nyquist criterion**, you must sample at *more than twice* the fastest oscillation in the input, or you get **aliasing** — a fast cognitive oscillation impersonating a false steady reading, with no error flag.
- **Quantization error** is the gap between continuous felt nuance and the nearest available discrete category — literally why some feelings "can't be put into words." More analytical categories (more `levels`) shrinks it.
- The **Schmitt trigger** (Chapter 10) cleans a noisy near-boundary digital output with hysteresis, stopping the conclusion from chattering between an involution pair like `^2^C|A` ⇄ `^3^C|A`.
- **Mixed-signal grounding:** keep the analog Registers (`|f`, `|E`) and the digital Register (`|A`) on separate rails, joined at exactly one designed point — the converter. Direct bleed in either direction is a grounding fault.
- The conversion parameters (`sample_rate`, `levels`, thresholds) are **design choices you select on the bench**, not measured model results.

---

## Exercises

**Exercise 15.1: Name the Conversion**

For each scenario, state whether it is an **ADC** or a **DAC**, and write it as a Register translation (e.g. `|f -> |A` or `|A -> |E`):

a) A robot reads a continuous proximity sensor and produces the discrete proposition "obstacle within one meter."
b) A person turns the written plan "apologize, then explain, then ask" into the actual lived act of the conversation.
c) Someone sits with a vague dread until they can finally say "I'm afraid I'll be blamed for this."

**Exercise 15.2: The Nyquist Question (Marquee)**

A cognitive system has an affective input that genuinely **oscillates at 1 Hz** — its `^*^E|f` state swings between drawn-toward and repelled once per second.

a) What is the **minimum sampling rate** an ADC must use to faithfully capture this oscillation? State the rule you used.
b) What happens if the ADC samples at **0.5 Hz** instead? Name the failure and describe the *specific wrong conclusion* the digital `|A` output would report.
c) Name the component you would add *before* the ADC to make a 0.5 Hz sampling rate at least safe (even if not faithful), and explain what it does.

(Answer in **Appendix E** — this is the Nyquist criterion.)

**Exercise 15.3: Write the Build**

Extend the `experience_adc` circuit from this chapter with a **DAC stage** that takes the `^5^C|A` self-knowledge and converts it into embodied action: a `^5^?|E` state that enacts the insight. Write the CCDL for the new node and the DAC CJT, choosing the correct output Domain, and add a one-line Bench Note explaining why the DAC must be the *only* join between the `|A` rail and the `|E` rail. (Answer in Appendix E.)

**Exercise 15.4: Diagnose the Fault**

A junior engineer reports that their cognitive circuit's "felt" input always agrees perfectly with whatever conclusion the analytical stage reached a moment earlier — the sensor never disagrees with the decision.

a) Which failure mode from the datasheet is this?
b) What specific wiring fault would produce it, in CAS terms?
c) What is the fix? (Answers in Appendix E.)
