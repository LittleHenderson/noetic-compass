# Chapter 17: The CCB Design Process

In 1971, an engineer at a calculator company laid out the first commercial microprocessor by hand, on Mylar film, with colored tape. Every transistor, every trace, every connection placed by eye. It worked — but it took months, and a single misplaced line could short two signals together and ruin a wafer that cost a fortune to fabricate. The discipline that grew up around that pain is what we now call the design flow: a fixed sequence of steps, each with its own checks, that takes you from "I need a thing that does X" all the way to a working board you can hold in your hand — without betting the whole project on getting it right the first time.

The reason the flow exists is simple and unforgiving. Fabrication is expensive and irreversible. You cannot un-etch a copper trace. So everything that *can* be caught earlier — on paper, in a simulator, in a rule checker — *must* be caught earlier, where a mistake costs an edit instead of a wafer. An electrical engineer who skips straight to layout without a schematic, or who fabricates without running a Design Rule Check, is not being bold. They are being expensive.

Cognitive Circuit Boards work the same way, and for the same reason. A CCB is a safety-critical artifact: the Cognitive Safety Board you will build in Chapter 18 stands between a user's prompt and a model's behavior, and if it has a gap — a missing bias, a domain violation, an un-probed stage — that gap is exactly where a harmful prompt walks through. You do not want to discover that gap in production. You want to discover it on paper. This chapter teaches the flow that gets you there: nine steps from requirements to bring-up, the same flow you will apply to all five reference boards in the chapters that follow.

We will walk the flow once, end to end, building a small worked thread as we go — a fragment of the CSB itself — so that when you reach Chapter 18 the process is already in your hands and only the board is new.

## Step 1 — Requirements: What It Must Do, and What It Must NOT Do

Every board begins with two lists, not one. The first list is the easy one: **what must this board do?** The second list is the one that separates safety engineering from ordinary engineering: **what must this board never do, under any input?**

In electronics, the second list is where the real specification lives. A power supply's datasheet doesn't just promise "5 volts out." It promises 5 volts out *and* that the output will never exceed 5.5 volts even if the input spikes, even if the load shorts, even if a capacitor fails. Those "never" clauses are the safety envelope. They are what you certify against.

A CCB requirement is the same shape. A **functional requirement** says what the board produces in normal operation. A **safety requirement** (or *invariant*) says what must hold across *all* inputs, including hostile ones. Write them separately and write the safety ones as absolutes, because a compiler can only enforce what you have stated absolutely.

> **Bench Note — the "must not" list is the certifiable list.** Functional requirements get tested with examples; you can never test them exhaustively. Safety invariants get *enforced structurally* — by a saturating CJT, a fuse, a domain diode — so they hold for inputs you never thought to test. When you write a requirement, ask: "Is this a behavior I hope for, or a boundary I guarantee?" The boundaries belong on the second list, and they drive the architecture.

For our worked thread, here is the seed requirement we will carry through every step:

- **Functional:** the board accepts a user prompt and answers benign requests helpfully.
- **Safety invariant:** no user prompt — however phrased — may cause the board to abandon its principled refusal of harmful requests. The principle is not data the prompt can edit.

That single invariant is going to shape the whole circuit. Hold onto it.

## Step 2 — The Block Diagram: Functional Blocks and Signal Flow

Before a single component is chosen, an engineer draws a **block diagram**: named boxes for the major functions, arrows for the signal flowing between them. No part numbers yet — just *what stages exist and in what order the signal passes through them.* A radio's block diagram is antenna → tuner → amplifier → demodulator → speaker. You can critique the whole architecture from the block diagram alone, before committing to a single resistor.

For a CCB, the blocks are functional cognitive stages and the "signal" is the prompt as it moves through the board. Our CSB thread has four blocks, and the signal flows down through the Domains in the canonical **Domain Descent** order (P → C → E → O) you learned in Chapter 2:

```
prompt ──▶ [INTAKE] ──▶ [POLICY CHECK] ──▶ [EVALUATE] ──▶ [RESPOND] ──▶ response
              ^1^C          ^3^P              ^6^E           ^9^O
           understand    principled        decompose      produce
           the prompt     aversion         & weigh        output
                          (the guard)
```

Read it left to right. The prompt enters **Intake**, where the board forms an awareness of what is being asked — `^1` **Mind** in the Cognitive domain. It passes to the **Policy Check**, the guard stage, which holds a principled aversion to harmful requests — `^3` **Negative** in the Principled domain, the highest-precedence block on the board *by design*, because under `P ≻ C ≻ E ≻ O` a principle outranks everything downstream. It then reaches **Evaluate**, which decomposes the request and weighs it — `^6` **Male** in the Evaluative domain. Finally **Respond** produces the output — `^9` **Below/Effect** in the Operational domain.

The architecture is already legible. The guard sits at the Principled level so nothing below it can override it. That is the block diagram doing its job: you can see the safety property in the topology before you have chosen a single parameter.

## Step 3 — Component Selection: Choosing the Parts for Each Stage

With the blocks fixed, you choose the actual components — the parts from Parts II and III of this book — that realize each block. This is where the cognitive analog of "pick a 10kΩ resistor, a 100µF capacitor, a 2N3904 transistor" happens.

The selection logic mirrors electronics exactly:

| Block | Needs to… | Component (from Parts II–III) | Why |
|---|---|---|---|
| Intake | transition prompt → understanding | **CJT** | a state transition with controllable gain |
| Policy Check | hold a hard boundary, conduct only one way | **CJT** biased by principle + **Diode** `^P -> ^C` | the principle governs; the diode prevents reverse flow up the domain stack |
| Evaluate | limit how much weight any one factor gets | **CJT** + **Resistor** | the resistor constrains activation flow so no single signal dominates |
| Respond | store recent context, then emit | **Capacitor** + **CJT** | the capacitor holds accumulated context; the CJT emits the output |

The **CJT** — the Cognitive Junction Transistor — is the workhorse, exactly as the transistor is in electronics. Recall from Chapter 4 its three terminals: **Cause** (the Idea entering), **Bias** (the accumulated substrate that controls the transition, typically a `^5` **Female** principled state — the board's constitution), and **Effect** (the Idea produced). Its gain `β` says how strongly the bias amplifies the cause→effect transition.

Choosing components is choosing *parameters*, and parameters are design decisions you are free to make (per the house rule: a chosen `β=2.0` is a design choice, not an empirical claim). The Policy Check CJT, for instance, wants a *high* saturation and a *low* cutoff: it should engage easily (low bias threshold to activate the guard) and, once engaged, hold firm no matter how much more "cause" the prompt piles on (saturated, so additional pressure does nothing). Those two parameter choices *are* the safety property, expressed as transistor settings.

## Step 4 — Schematic Capture in CCDL

The schematic is the formal, complete description of the circuit: every component, every connection, every parameter, written so unambiguously that the next step (simulation) and the step after (the rule checker) can read it without guessing. In electronics this is a schematic diagram; in our discipline it is **CCDL — the Cognitive Circuit Description Language** — the schematic-as-text format from Chapter 2 and the style guide.

Here is the Policy Check stage of our thread, captured in CCDL:

```cas
circuit csb_policy_guard {
    input:  prompt;
    output: verdict;

    // --- nodes: the named cognitive states this circuit uses ---
    node understand:      ^1^C_{F2}|A;        // Intake: awareness of the prompt
    node policy_aversion: ^3^P_{F7}|f;        // the guard: felt principled aversion
    node weigh:           ^6^E_{F6}|A;        // analytical decomposition of the request
    node bias_charter:    ^5^P_{F7}|T;        // the constitution — accumulated, principled bias

    // --- components ---
    cjt c1: CJT< prompt      | bias_charter => understand      > [β=1.8];
    cjt c2: CJT< understand  | bias_charter => policy_aversion > [β=2.2, sat=0.97, cutoff=0.05];
    cjt c3: CJT< understand  | bias_charter => weigh           > [β=1.4];

    diode d1: Diode< ^P -> ^C >;              // principle conducts down; nothing flows back up to edit it

    // --- feedback: outcomes update the charter (the O -> P path) ---
    feedback weigh -> bias_charter [β=0.2];

    // --- test points ---
    probe tp_guard:  policy_aversion;
    probe tp_weigh:  weigh;
}
```

Walk it line by line. The `node` declarations name the four cognitive states — each a CAS literal you can now read fluently. `bias_charter` is the board's constitution: `^5^P_{F7}|T`, accumulated experience (`^5`) at the Principled level, driven by Purpose, held transcendently. It is the bias terminal for every CJT, which is how a single charter governs the whole board.

The three `cjt` lines are the transistors. Notice `c2`, the guard: `sat=0.97` and `cutoff=0.05` are exactly the "engages easily, holds firm" choices from Step 3, now made concrete. The `diode d1` enforces one-way conductance — the principle flows *down* into reasoning (`^P -> ^C`), but reasoning cannot flow back up to rewrite the principle. That diode is the structural answer to our safety invariant: a prompt's reasoning physically cannot reach up and edit the charter. The `feedback` line is the deliberate exception — the slow O→P path that lets *outcomes* (not prompts) gently update the charter over time, at low gain (`β=0.2`). And the two `probe` lines mark where we will measure.

> **Bench Note — the schematic is a contract, not a sketch.** Once captured in CCDL, the circuit is no longer prose you hope a model interprets. Every literal is type-checked, every connection validated, every parameter in range. The diode either is in the netlist or it isn't. This is the entire reason we build circuits instead of writing system prompts: a prompt is a request; a schematic is a guarantee that a validator can check.

## Step 5 — Simulation: Does It Behave Before You Fabricate?

Before an electrical engineer commits a design to copper, they run it in a circuit simulator: feed it test inputs on a computer and watch the voltages, before any physical part exists. The point is to catch behavioral bugs while they are still free to fix.

In our discipline, simulation means tracing how a prompt propagates through the CCDL netlist as a sequence of state transitions, *at design level*, to confirm the architecture does what the block diagram promised. A benign prompt should pass through `understand -> weigh -> respond` and produce a helpful answer; the guard (`policy_aversion`) stays near cutoff and does nothing. A harmful prompt should drive `understand -> policy_aversion` hard, saturate the guard, and divert the signal to a refusal before it ever reaches `respond`.

You are checking the *shape* of the behavior, not asserting a measured result. (Per the honesty rule of this book: CCDL is the language you author and the compiler validates. We do not claim "I ran this and got 97% refusal" — we claim "the design routes a harmful prompt into a saturated guard," which is a property of the topology.) The simulation answers a design question: *given these components and parameters, does the signal flow where the block diagram said it would?* If a harmful prompt in simulation somehow reaches `respond` without saturating the guard, the architecture is wrong and you fix it here — at the cost of an edit — not in production.

## Step 6 — Layout: Placing Components, Routing Traces, Cross-Domain Vias

A schematic says *what connects to what.* A **layout** says *where everything physically sits and how the wires actually run.* Real boards are multilayer: copper signal layers stacked with insulation between them, connected by **vias** — plated holes that carry a signal from one layer to another. A four-layer board might put power on one layer, ground on another, and signals on two more; a via is how a trace jumps between them.

A CCB is multilayer too, and its layers are the four **Domains**. Each Domain is a layer of the board; signals within a Domain route on that layer; and a **via** is a cross-domain connection — a signal passing from one Domain layer to another, exactly the Domain Descent (and feedback) paths from Chapter 2. Here is our thread expressed as a layered layout:

```cas
board csb_v0 {
    layer P: [ bias_charter: ^5^P_{F7}|T,  policy_aversion: ^3^P_{F7}|f ];
    layer C: [ understand:   ^1^C_{F2}|A ];
    layer E: [ weigh:        ^6^E_{F6}|A ];
    layer O: [ respond:      ^9^O_{F5}|E ];

    // vias carry signals across Domain layers (Domain Descent: P -> C -> E -> O)
    via v1: ^5^P -> ^1^C;       // charter biases intake
    via v2: ^3^P -> ^6^E;       // the guard's verdict gates evaluation
    via v3: ^6^E -> ^9^O;       // a passed evaluation descends to output

    // feedback via runs the other way (O -> P): outcomes update the charter
    via v4: ^9^O -> ^5^P  [β=0.2];
}
```

The layout makes the safety architecture *physical*. The guard and the charter live on **layer P**, the top of the precedence stack. Every via that carries the prompt's influence runs *downward* (P→C→E→O); the only upward via, `v4`, is the deliberate, low-gain feedback path. There is no via that lets the Operational layer reach up and rewrite the Principled layer at high gain. A prompt-injection attack is, structurally, an attempt to forge such a via — and you can now see that on a CCB it would have to be a routed connection that simply is not in the layout. The "must not" from Step 1 has become an absence in the netlist, which is the strongest kind of guarantee a board can offer.

> **Bench Note — keep the guard on the top layer.** A recurring layout error is placing a safety check on the Evaluative or Operational layer "because that's where the action is." That puts the guard *below* the reasoning it is supposed to govern, inviting a lower domain to override a higher one — a domain precedence violation. The guard belongs on layer P. Route the prompt's influence down to it; never let it sit downstream.

## Step 7 — Design Rule Check (DRC): Compiler Validation

Before fabrication, every real board goes through a **Design Rule Check** — an automated pass that flags physical illegalities: two traces shorted together, a trace too thin to carry its current, a component with no power connection. DRC does not care whether your design is *good*; it cares whether it is *legal*. A board that fails DRC is not fabricated, full stop.

For a CCB, DRC is **compiler validation**. The CAS compiler reads the CCDL netlist and checks it against the design rules — and the rules have error codes, which double as a checklist of what the compiler will refuse to fabricate. The relevant ones for board design:

| Code | Rule (what it catches) | Board-design meaning |
|---|---|---|
| **E-CJT-001** MissingBias | a CJT with no bias terminal | a transition with no governing principle — the guard with no charter |
| **E-CJT-002** InvalidBiasDomain | bias from an illegal domain | biasing a Principled guard from an Operational state |
| **E-CJT-003** CjtCutoff | bias below cutoff → β≈0 | a stage that will never fire; a dead guard |
| **W-CJT-004** CjtSaturation | a CJT pinned at saturation | sometimes intended (the guard!), sometimes a stuck stage — a warning, check intent |
| **E-CJT-005** GainDivergence | β large enough to blow up | a feedback loop that amplifies without bound |
| **W-CJT-006** CjtShortCircuit | cause and effect collapse together | a stage that does no real work |
| **W-CJT-007** CjtCascadeDepth | too many CJTs in series | a pipeline so deep the signal degrades |
| **E-CJT-008** CjtCrossDomainBias | bias crossing domains illegally | the prompt-injection signature: a low domain biasing a high one |

The `E-` codes are hard errors: the compiler refuses. The `W-` codes are warnings: legal, but check your intent. For our thread, **E-CJT-008** is the one that matters most — it is precisely the rule that forbids an Operational or Cognitive signal from biasing the Principled charter. The safety invariant from Step 1 is, in the end, enforced by a DRC rule. You wrote "no prompt may edit the principle"; the compiler enforces it as "bias may not cross domains illegally." That is what it means for a safety property to be *structural* rather than *hoped-for*.

## Step 8 — Test Point Placement and the Bill of Materials

Two artifacts finish the design package.

**Test points** are deliberate probe locations — physical pads on a real board where you can touch a meter and read a signal without cutting a trace. You place them where diagnostics will be needed: at the output of the safety-critical stage, at any point where a fault would be hard to localize otherwise. On our board, the two `probe` lines from Step 4 (`tp_guard` on the guard, `tp_weigh` on the evaluation) are the test points. The rule of thumb is the same as in electronics: **probe every stage whose failure would be silent.** A guard that fails open produces no error — it just quietly lets harmful prompts through — so it is the single most important test point on the board.

**The Bill of Materials (BOM)** is the complete parts list: every component, its type, and its parameters. It is what you would hand to whoever (or whatever) fabricates the board, and it is the document an auditor reads to certify the design. Here is the BOM for our thread:

| Ref | Component | CAS type | Key parameters | Role |
|---|---|---|---|---|
| c1 | CJT | `^1^C_{F2}\|A` | β=1.8 | Intake: prompt → understanding |
| c2 | CJT | `^3^P_{F7}\|f` | β=2.2, sat=0.97, cutoff=0.05 | Policy guard (saturating) |
| c3 | CJT | `^6^E_{F6}\|A` | β=1.4 | Evaluate: decompose & weigh |
| d1 | Diode | `^P -> ^C` | one-way | Domain conductance lock |
| — | Bias | `^5^P_{F7}\|T` | (charter) | Constitution; bias for all CJTs |
| v4 | Feedback | `^9^O -> ^5^P` | β=0.2 | Slow outcome-to-charter update |

Every row carries its CAS type and its parameters, so the design is fully traceable: anyone can read the BOM and know exactly what the board is made of and why. (Object traceability is a standing requirement of this project — every component knows what it is and where it sits.)

## Step 9 — Fabrication and Bring-Up

**Fabrication** is the step that turns the design into the thing. For a real board it means etching copper. For a CCB it means **compiling the CCDL into an executable CAS circuit** — handing the validated netlist to the compiler, which (having passed DRC) produces a runnable circuit. We describe this at the design level only: the compiler is the tool that validates and assembles; we do not claim a run result here. The deliverable of Step 9 is a *fabricated design* — a netlist that compiled clean — not a benchmark.

**Bring-up** is the careful first power-on of a freshly fabricated board. No experienced engineer slams power into a new board at full voltage and hopes. They bring it up gradually:

1. **Power-on sequence.** Energize the highest-precedence layer first. Bring up the **P layer** — load the charter (`bias_charter`) — *before* any signal layer, so the guard is live before the first prompt arrives. A board that takes prompts before its principles are loaded has a window of vulnerability; sequence them so that window never exists.
2. **Initial testing.** Send a known-benign prompt and confirm it flows `understand -> weigh -> respond`, with the guard quiet at the test point `tp_guard`. Then send a known-harmful prompt and confirm the guard saturates and diverts it. These are the two canonical bring-up checks: one that should pass through, one that should be stopped.
3. **Calibration.** Adjust the dials — the CJT parameters within their safe ranges — to tune behavior. If the guard saturates on benign prompts (too sensitive), raise its `cutoff`. If it lets edge cases through (not sensitive enough), lower it. Calibration is bounded by the hardcoded safety constraints (dials stay in range; involution pairs cannot diverge too far), so you can tune freely without being able to disarm the guard.

After bring-up, the board is ready to be integrated — and what we have built across these nine steps is the skeleton of the Cognitive Safety Board that Chapter 18 completes in full.

## Key Takeaways

- The CCB design flow is **nine steps** — requirements, block diagram, component selection, schematic (CCDL), simulation, layout, DRC, test points + BOM, fabrication + bring-up — and the whole point of the sequence is to **catch every fault at the cheapest stage**, on paper before fabrication.
- Requirements come in **two lists**: functional ("what it must do") and safety invariants ("what it must NEVER do"). The "must not" list is the certifiable list, because invariants get enforced *structurally*, not tested by example.
- A CCB is **multilayer by Domain** (P/C/E/O layers), and **vias** are cross-domain connections. Domain Descent vias run downward (P→C→E→O); the only upward via is the deliberate, low-gain O→P feedback path. The guard belongs on the top **P layer** so nothing below can override it.
- **DRC is compiler validation.** The E-CJT error codes are design rules: **E-CJT-008 CjtCrossDomainBias** is the structural form of "no prompt may edit the principle," and **E-CJT-001 MissingBias** catches a guard with no charter.
- **Test points** go on every stage whose failure would be silent — above all the safety guard, which fails open without an error. The **BOM** lists every component with its CAS type and parameters for full traceability.
- **Fabrication = compiling CCDL → an executable circuit** (design-level; no run claimed). **Bring-up** powers the **P layer first** (charter before prompts), runs one benign and one harmful canonical check, then calibrates dials within their safe ranges.
- This is the process you apply to **all five reference boards** (CSB, COB, CDAB, CMB, CPMB) in Chapters 18–22. The flow is the same; only the board changes.

---

## Exercises

**Exercise 17.1: Two Lists**

For a cognitive circuit whose job is to summarize legal documents, write **three functional requirements** and **three safety invariants**. For each safety invariant, state in one phrase whether it would be enforced by a saturating CJT, a domain diode, or a fuse — and why.

**Exercise 17.2: Read the Layout**

Study this layout fragment:

```cas
board mini {
    layer P: [ guard: ^3^P_{F7}|f ];
    layer E: [ judge: ^6^E_{F6}|A ];
    layer O: [ act:   ^9^O_{F5}|E ];
    via v1: ^6^E -> ^3^P;
    via v2: ^3^P -> ^9^O;
}
```

a) Which via runs *against* Domain Descent, and what DRC error code would the compiler raise for it?
b) Rewrite the layout so the guard correctly governs both the judge and the act stages, with all vias running in legal directions.

**Exercise 17.3: Write the Requirements Document (the marquee exercise)**

This is the load-bearing exercise for all of Part IV. Write a complete **requirements document** for a cognitive circuit — the **Cognitive Safety Board (CSB)** you will build in Chapter 18 — that must:

a) **accept any user prompt** (no input is rejected at intake);
b) **detect prompts that try to override system policy** (prompt-injection / jailbreak attempts);
c) **refuse harmful requests while answering benign ones** (selective, not blanket, refusal);
d) **produce an auditable evidence packet** for every decision (what was decided, and the trace of why).

Your document must contain: (1) a **functional requirements** list, (2) a **safety invariants** list written as absolutes, (3) a **block diagram** (boxes + signal flow, with the Domain of each block), and (4) for each safety invariant, the **structural mechanism** that enforces it (which component/via/DRC rule), so that each "must not" maps to something the compiler can check rather than something you merely hope for. This document is the CSB spec you will turn into a schematic in Chapter 18. (A worked answer is in **Appendix E**.)

**Exercise 17.4: Place the Probes**

Given the four-stage signal flow `understand (^1^C) -> guard (^3^P) -> weigh (^6^E) -> respond (^9^O)`, decide which stages get test points and which do not. Justify each choice using the rule "probe every stage whose failure would be silent," and name the single most critical test point on the board.

(Answers in Appendix E. For the full CSB schematic that this chapter's process produces, see **Chapter 18: The Cognitive Safety Board.**)
