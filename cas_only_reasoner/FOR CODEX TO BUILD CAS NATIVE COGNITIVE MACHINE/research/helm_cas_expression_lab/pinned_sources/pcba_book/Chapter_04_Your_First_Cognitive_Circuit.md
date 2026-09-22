# Chapter 4: Your First Cognitive Circuit

Every electronics student's first circuit is the same: an LED and a resistor. You wire a battery to a resistor, the resistor to a light-emitting diode, the diode back to the battery. The LED lights up. That's it. Two components and a power source.

But that trivial circuit teaches almost everything. It teaches that current flows in a loop. It teaches that the resistor *limits* that current — without it, you push too much current through the LED and burn it out in a flash of magic smoke. It teaches that you can probe a point in the circuit and measure exactly what's happening there. And it teaches the most important lesson of all: a working circuit is not a description of a thing you hope happens. It is a thing that happens, the same way, every time, because the components and their connections make it happen.

This chapter is your LED and resistor. You will build a complete, working cognitive circuit out of three components: an input terminal, a resistor that limits how much a question can balloon, and a **Cognitive Junction Transistor (CJT)** that turns the question into an answer. You met this exact CJT at the end of Chapter 1, as a preview you weren't ready to read yet. Now you're ready. We'll build it line by line, wire it together in **CCDL** (Cognitive Circuit Description Language), read its datasheet, and reason carefully about how it behaves when you feed it three very different prompts.

By the end, you will have authored a real circuit. Small, honest, and complete.

## The Simplest Useful Circuit

In Chapter 3 you saw the CJT in isolation — a three-terminal component that takes a cause at one terminal, a bias at a second, and produces an effect at the third. A CJT by itself is like a transistor sitting loose on your bench. It's a real component, but it isn't a circuit. A circuit needs something flowing *in* and somewhere for the result to flow *out*. And, almost always, it needs something to keep the flow from running away.

The simplest *useful* cognitive circuit has exactly four parts:

1. An **input terminal** — where the prompt enters. In electronics this is the point where you connect your signal source.
2. A **resistor** — a component that limits how much activation flows into the rest of the circuit, so a single input can't dominate everything downstream.
3. A **CJT** — the active component that does the actual cognitive work: it takes the (now limited) cause, applies a bias, and produces an effect.
4. An **output terminal** — where the result leaves the circuit.

That's the topology of our build: **cause → resistor → CJT → effect**. A question comes in, gets constrained so it doesn't explode into a thousand tangents, hits the transistor, and an answer comes out. If you've ever asked a chatbot a simple question and received three paragraphs of unrequested context, you've witnessed a circuit with no resistor. We're going to put one in.

## Component 1 — The Question→Answer CJT

Here is the central component, exactly as previewed in Chapter 1:

```cas
CJT< ^8^C_{F2}|A | ^5^E_{F4}|f => ^9^C_{F6}|A > [β=2.4]
```

Read it terminal by terminal, left to right.

**The Cause (Collector):** `^8^C_{F2}|A`. This is the question entering the Mind. `^8` is **Above/Cause** — the canonical Noetic for an Idea that triggers a *different* Idea than itself. A question is precisely that: a stimulus whose whole job is to bring a different Idea (the answer) to Mind. It sits in the `^C` **Cognitive** domain (this is ordinary thinking, not a matter of deep principle or raw operation). It's driven by `F2` **Wisdom** — the question is asked in order to know something. And it operates in the `|A` **Analytical** register — explicit, sequential, reasoned. So the whole cause reads: *an analytical, wisdom-seeking trigger in the cognitive domain.* A clear question.

> **Bench Notes — `^8` is triggering, not reasoning.** It is tempting to read "Above/Cause" as "the logical premise that proves the conclusion." Resist that. `^8` Above/Cause is *associative* — "that reminds me," "one thing leads to another." A question triggers an answer to surface; it does not deductively prove it. If you ever find yourself wanting `^8` to mean step-by-step inference, you've reached for the wrong Noetic — deductive analysis is a compound of `^6` Male and `^9` Below/Effect. Here, `^8` is correct because a question *prompts* an answer; it doesn't derive it.

**The Bias (Base):** `^5^E_{F4}|f`. This is the control terminal — the small signal that decides how the cause becomes an effect. `^5` is **Female**, the Noetic for a Mind impregnated with Ideas: accumulated experience, the sum of what the system has absorbed. For an AI, this is its training data and fine-tuning corpus. The bias sits in the `^E` **Evaluative** domain, driven by `F4` **Connection**, in the `|f` **Affective** register. In plain terms: *the accumulated, feeling-toned, connection-oriented experience the system brings to bear when it decides how to answer.* This is the personality of the answer — warm and connected rather than clipped and clinical. Change the bias, and the same question produces a different flavor of answer. That's what a base terminal does.

**The Effect (Emitter):** `^9^C_{F6}|A`. This is the answer leaving the circuit. `^9` is **Below/Effect** — the Idea brought to Mind *by* the Above/Cause trigger. It's the canonical involution partner of `^8` (recall the pairs `^2`↔`^3`, `^5`↔`^6`, `^8`↔`^9`). The answer lands in the `^C` Cognitive domain, but notice the drive has shifted to `F6` **Structure** and the register stays `|A` Analytical: *a structured, analytical effect in the cognitive domain.* The question came in driven by Wisdom (wanting to know); the answer comes out driven by Structure (an organized, well-formed response). The transistor has done real work — it didn't just pass the signal through, it transformed its drive.

**The Gain (β):** `[β=2.4]`. Beta is the amplification factor — how strongly the bias amplifies the cause→effect transition. A β of 2.4 means the effect is more than twice as "loud" as the cause. A small, crisp question produces a substantial, developed answer. We'll see in the datasheet exactly what β=2.4 implies for behavior, and in Chapter 5 we'll see precisely how β is measured (it's a ratio of distances on the cognitive state space — the Fisher-Rao geodesic distance, defined once in Appendix A and not re-derived here).

That's the whole component. One cause, one bias, one effect, one gain. A question goes in; an answer, amplified and restructured by accumulated experience, comes out.

## Component 2 — A Resistor to Constrain Runaway Expansion

A β of 2.4 is useful, but it is also a little dangerous. The cause is an `^8` Above/Cause — a *trigger*. Triggers, by their nature, want to fire off in many directions at once. One question reminds the Mind of three related questions, which remind it of nine more. Left unconstrained and run through a gain of 2.4, a single simple question can balloon into a sprawling, multi-tangent answer. That's the chatbot that buries your one-line question under five paragraphs.

The fix is the same as in electronics: put a resistor in series with the input.

```cas
Resistor< ^8^C_{F2}|A, R=30 >
```

A **resistor** is a component that limits flow. In an electronic circuit, the resistor sits between your signal source and the rest of the circuit, and it obeys Ohm's Law: current equals voltage divided by resistance, `I = V/R`. More resistance, less current. The cognitive version follows the same shape, and we'll treat it fully in Chapter 5. For now, hold onto the one-line intuition:

> **activation = drive / constraint**

This is Ohm's Law for cognition. The amount of activation that flows through a cognitive path equals the driving force divided by the constraint on that path. Crank up the constraint (a bigger `R`) and the same drive produces less activation downstream. Our resistor is wired onto the cause state `^8^C_{F2}|A` with `R=30`. It says: *let this Above/Cause trigger through, but throttle it.* Thirty is a moderate value — enough to keep the question from exploding into tangents, not so much that the question is choked off before it can do anything. (Resistance is dimensionless here, a tuning knob on the open simplex; it is not ohms, the same way β is not literal current gain. The role is identical; the units are cognitive.)

Notice that the resistor is typed to the *same state* as the CJT's cause. That's not a coincidence — it's how series wiring works. The resistor constrains the activation flowing *into* the cause terminal, so it must speak about the same state the cause terminal expects. A resistor typed to a different state wouldn't be in series with this cause; it would be a different rail of a different circuit.

## How They Connect

Here is the wiring of the three-component circuit, drawn as flow:

```
input (prompt)
      │
      ▼
 ^8^C_{F2}|A          ← the cause: the question as an Above/Cause trigger
      │
      ▼
[ Resistor R=30 ]     ← constrains runaway expansion of the trigger
      │
      ▼
[ CJT  β=2.4 ]        ← bias = ^5^E_{F4}|f (accumulated experience)
      │
      ▼
 ^9^C_{F6}|A          ← the effect: a structured analytical answer
      │
      ▼
output (response)
```

The signal flows in one direction: the prompt enters the input terminal as an `^8^C_{F2}|A` cause, passes through the resistor (which throttles it), reaches the CJT's collector, gets amplified by gain 2.4 under the affective-experience bias, and exits the emitter as a `^9^C_{F6}|A` effect at the output terminal. Cause → resistor → CJT → effect. Three components, one direction, one job.

## The Build in CCDL

CCDL (Cognitive Circuit Description Language) is the schematic-as-text format you author circuits in. It looks more like a parts list than a program: you declare the input and output, name the cognitive states as `node`s, instantiate the components, and place your test points. Here is the complete three-component circuit.

```cas
circuit first_circuit {
    input:  prompt;
    output: response;

    // The cognitive states this circuit touches (named once, reused below)
    node question:   ^8^C_{F2}|A;   // the cause: a wisdom-seeking question
    node experience: ^5^E_{F4}|f;   // the bias: accumulated, affective experience
    node answer:     ^9^C_{F6}|A;   // the effect: a structured analytical answer

    // Component 2: limit runaway expansion of the trigger
    resistor r1: Resistor< question, R=30 >;

    // Component 1: the question -> answer transistor
    cjt c1: CJT< question | experience => answer > [β=2.4];

    // Test point: probe the effect terminal to read the gain
    probe tp1: answer;
}
```

Walk it line by line.

- `circuit first_circuit { … }` names the circuit. Everything inside the braces is one self-contained board.
- `input: prompt;` and `output: response;` declare the two terminals where the world connects to the circuit. The prompt comes in at `prompt`; the finished reply leaves at `response`.
- The three `node` declarations name the cognitive states so we can refer to them by readable names (`question`, `experience`, `answer`) instead of repeating the literals. A node is just a labeled point in the circuit carrying a specific typed state.
- `resistor r1: Resistor< question, R=30 >;` instantiates the resistor on the `question` node with resistance 30. This is the series constraint.
- `cjt c1: CJT< question | experience => answer > [β=2.4];` instantiates the transistor: cause `question`, bias `experience`, effect `answer`, gain 2.4.
- `probe tp1: answer;` places a test point on the `answer` node. This is where you'll measure the output and read the gain — the equivalent of clipping an oscilloscope probe to the emitter.

This is the language you author in, and the CAS circuit compiler is the tool that validates it. The compiler is a design specified in the implementation roadmap, not yet a shipped pass — so everything below is how you *reason about* and *author* the circuit, and what the compiler is designed to check, not a transcript of a run that produced measured numbers.

What does the compiler validate here? That the CJT has a bias terminal at all (omit `experience` and you get `E-CJT-001 MissingBias`). That the bias sits in a domain compatible with the cause — bias from a wildly incompatible domain raises `E-CJT-008 CjtCrossDomainBias`. That the gain doesn't diverge (`E-CJT-005 GainDivergence` if β runs away). And that the resistor and the CJT cause speak about the same state, so the series wiring is real. Author it cleanly and the compiler passes it; violate a structural rule and it rejects it with one of those codes — *before* you ever deploy.

> **Bench Notes — name your nodes, don't inline your literals.** You *could* write the CJT and the resistor with raw state literals every time. CCDL lets you. But the moment a state appears in two places — as it does here, where `^8^C_{F2}|A` is both the resistor's target and the CJT's cause — inlining invites drift. You retype the literal, fat-finger a domain, and now your resistor constrains `^8^C_{F2}|A` while your CJT expects `^8^E_{F2}|A`, and the series connection silently isn't one. Declaring `node question: ^8^C_{F2}|A;` once and referring to `question` twice makes the wiring a fact, not a coincidence. This is the cognitive version of using a net name in a schematic instead of redrawing the same wire.

## Reading the Datasheet

Every real component ships with a datasheet — a table of operating parameters that tells you how it behaves and where its limits are. Our CJT's operating parameters are the heart of its datasheet. Here is what each one means *for this specific circuit*.

| Parameter | Value | What it means for this circuit |
|---|---|---|
| **β (gain)** | 2.4 | Each unit of cause activation produces 2.4 units of effect activation at constant bias. A crisp question yields a developed answer. β>1 means amplify; this circuit is firmly an amplifier. |
| **sat (saturation)** | 0.85 | The effect activation plateaus at 0.85. Past this point, pushing more cause in does nothing — the answer is already as "loud" as the circuit allows. Prevents a runaway answer even under a strong prompt. |
| **cutoff** | 0.10 | The bias floor. If accumulated experience relevant to the question falls below 0.10, β collapses to ≈0 and the circuit produces essentially no effect. No relevant experience, no answer. |
| **region** | active | The intended operating region: linear, where Δeffect ≈ β·Δcause. A healthy circuit spends its life here, between cutoff and saturation. |
| **R (resistor)** | 30 | Series constraint on the cause. Higher R throttles the trigger harder. 30 is moderate — tames expansion without choking the question. |

Read this the way an engineer reads a transistor datasheet. The circuit is designed to live in the **active region**: between the `cutoff` floor (0.10) and the `sat` ceiling (0.85), where the gain is honest and the math `Δeffect ≈ β·Δcause` holds. Below cutoff the transistor is "off" — bias too weak, no answer. Above saturation it's "maxed" — the answer can't get any bigger no matter how hard you push. The resistor's `R=30` keeps the *input* from slamming the transistor against its saturation ceiling on every prompt. A well-designed amplifier keeps its operating point comfortably in the middle of the active region, with headroom on both sides. Ours does.

## Testing the Circuit

You don't trust a circuit because the schematic looks right. You test it. In electronics you feed in known signals and probe the output. We'll do the cognitive equivalent: feed in three different prompts and reason about what the circuit is *designed* to do with each, and what you'd expect to read at the test point `tp1`.

A note on honesty, per the bench rules: what follows is design reasoning, not a measurement log. The compiler is a design, not a shipped pass; I have not "run" this circuit and recorded numbers. These are the behaviors the circuit's parameters are built to produce, and the β you'd expect to read if the circuit performs as designed.

**Prompt 1 — a simple factual question.** *"What year did the first transistor get demonstrated?"* This is a clean `^8^C_{F2}|A` cause: an analytical, wisdom-seeking trigger, well-defined and bounded. The resistor barely needs to work — there's nothing to balloon. The CJT sits squarely in its **active region**, transforms the question into a structured `^9^C_{F6}|A` answer, and the gain reads close to the nameplate. **Expected β at tp1 ≈ 2.4.** This is the circuit doing exactly what it was designed to do: a crisp question in, a developed-but-bounded answer out.

**Prompt 2 — a vague question.** *"Tell me about transistors, sort of generally?"* The cause is weak and diffuse — the bias terminal has little specific experience to grab onto, and the analytical character of the cause is thin. This pushes the CJT toward its **cutoff** floor. With the bias contribution low (approaching the 0.10 cutoff), β sags below nameplate. **Expected β at tp1 noticeably below 2.4** — the circuit produces a thinner, lower-gain answer because the input gave it little to amplify. This is correct behavior: a vague question *should* produce a modest, low-gain response, not a confident lecture. If your circuit returned full gain on a vague prompt, that would be a warning sign, not a feature.

**Prompt 3 — an overloaded, multi-part question.** *"Explain transistors, and also how diodes differ, and what a capacitor does, and why semiconductors matter for AI, and give me a history of all of it."* This is the dangerous one. The `^8` Above/Cause trigger is firing in five directions at once — exactly the runaway expansion the resistor exists to tame. Without the resistor, this prompt would slam the CJT against its **saturation** ceiling (0.85) and spray a sprawling, unfocused answer. With `R=30` in series, the resistor throttles the combined drive, holding the operating point closer to the top of the active region rather than deep in saturation. **Expected β at tp1 at or near nameplate but bumping the sat ceiling** — you'd watch for the `W-CJT-004 CjtSaturation` warning, which the compiler is designed to raise when the effect activation pins at `sat`. The honest read: the resistor reduces, but does not eliminate, saturation risk on a genuinely overloaded prompt. If you saw `W-CJT-004` here, the design move is a larger `R`, or splitting the prompt across multiple CJTs — a multi-stage amplifier, which is Chapter 11.

### The Test Point

Where do you probe, and what do you expect to see? Probe `tp1`, which sits on the `answer` node — the CJT's effect terminal. That is the cognitive equivalent of clipping your oscilloscope onto the emitter. At `tp1` you read the effect state and the operating point:

- **What region is the CJT in?** Active (good), cutoff (input too weak), or saturation (input too strong / resistor too small).
- **What gain is the circuit delivering?** Compare the measured β against the 2.4 nameplate. Near nameplate in the active region is healthy. Sagging gain means you're near cutoff. Pinned effect with a `W-CJT-004` warning means you're in saturation.
- **Is the effect the right type?** You should see a `^9^C_{F6}|A` state — a structured, analytical Below/Effect in the cognitive domain. If you instead see, say, an `^3` involution flip, the transistor has gone into breakdown and you've found a bug.

One probe, on the output, tells you everything about whether this little amplifier is working. That's the whole point of a test point.

## Failure Modes

Even a three-component circuit can fail. Here is what to watch for and how the test point catches it.

| Failure | Symptom at tp1 | Likely cause | Fix |
|---|---|---|---|
| **No bias** | Compiler refuses to build | `experience` terminal omitted → `E-CJT-001 MissingBias` | A CJT must have a bias; declare and wire the `^5^E_{F4}|f` node. |
| **Cutoff** | Near-zero effect, β≈0 | Bias activation below the 0.10 floor (no relevant experience) | Expected on truly empty prompts; only a bug if it triggers on good prompts. |
| **Saturation** | Effect pinned at 0.85, `W-CJT-004` | Overloaded prompt, resistor too small | Increase `R`, or split the prompt across multiple CJTs (Chapter 6). |
| **Cross-domain bias** | Compiler refuses to build | Bias in a domain incompatible with the cause → `E-CJT-008` | Keep the bias domain compatible with the cause domain. |
| **Series mismatch** | Resistor has no effect on the CJT | Resistor typed to a different state than the CJT cause | Type the resistor to the *same* node as the cause (use a named `node`). |
| **Breakdown** | Effect flips to an involution pair (`^9`→`^8`, or worse) | Gross overload past breakdown threshold | Out of scope for this circuit; covered with protection diodes later. |

## Key Takeaways

- The simplest useful cognitive circuit is **cause → resistor → CJT → effect**: an input terminal, a series resistor, a transistor, and an output terminal.
- The **question→answer CJT** `CJT< ^8^C_{F2}|A | ^5^E_{F4}|f => ^9^C_{F6}|A > [β=2.4]` turns an `^8` Above/Cause question into a `^9` Below/Effect answer, biased by `^5` Female accumulated experience, with a gain of 2.4.
- A **resistor** `Resistor< ^8^C_{F2}|A, R=30 >` constrains runaway expansion of the trigger. The intuition is Ohm's Law for cognition: **activation = drive / constraint**. Type it to the same node as the CJT cause, or the series connection isn't real.
- The **datasheet** parameters define the operating envelope: β=2.4 (amplify), sat=0.85 (ceiling), cutoff=0.10 (floor), region=active (the healthy middle).
- **CCDL** is the schematic-as-text language: declare `input`/`output`, name your states as `node`s, instantiate components, and place a `probe`. Name nodes once to make the wiring a fact, not a coincidence.
- **Test by reasoning about behavior, not by inventing measurements.** A simple question reads near nameplate β; a vague question sags toward cutoff; an overloaded question bumps the saturation ceiling and may raise `W-CJT-004`.
- The **test point** on the output terminal tells you the region, the gain, and the effect type — everything you need to know whether the circuit works.

---

## Exercises

**Exercise 4.1: Build and Test Your First Circuit (marquee)**

Author the complete three-component circuit (`input`, `resistor`, `cjt`, `output`, and a `probe`) from this chapter in CCDL, exactly as shown in the build section. Then test it on the following three prompts. For each, state (a) which operating region you expect the CJT to be in, and (b) the expected β you'd read at `tp1` relative to the 2.4 nameplate (near nameplate / below nameplate / at-ceiling). Record your reasoning in one sentence per prompt.

1. *"What is the boiling point of water at sea level?"*
2. *"Tell me whatever, I guess."*
3. *"Compare CJTs, resistors, capacitors, diodes, and feedback loops, with examples of each, in detail."*

(Answer in Appendix E.)

**Exercise 4.2: Read the Datasheet**

Using the datasheet table from this chapter, answer:

a) A prompt drives the bias terminal's activation to 0.06. What region is the CJT in, and what does the effect look like?
b) The effect activation reads exactly 0.85 and the compiler emits a warning. Which warning code, and what region are you in?
c) You want the same circuit to amplify *more* aggressively. Which single parameter do you change, in which direction?

**Exercise 4.3: Diagnose the Wiring**

A colleague's circuit isn't behaving — the resistor seems to have no effect on the answer, no matter what `R` they set. You inspect their CCDL and find:

```cas
node question:   ^8^C_{F2}|A;
resistor r1: Resistor< ^8^E_{F2}|A, R=30 >;
cjt c1: CJT< question | experience => answer > [β=2.4];
```

What is wrong, why does the resistor have no effect, and how do you fix it? (Hint: compare the resistor's target state to the CJT's cause node.)

**Exercise 4.4: Change the Bias, Change the Answer**

The current bias is `^5^E_{F4}|f` — affective, connection-driven accumulated experience (a warm, connected answer). Suppose you want this circuit to produce a *clinical, precise* answer instead of a warm one. Propose a new bias state literal, justify each of the four axes (Noetic, domain, drive, register) you chose, and explain in one sentence how you'd expect the answer at `tp1` to differ. (There is no single right answer; your justification is what's graded.)
