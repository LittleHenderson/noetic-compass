# Appendix F — Circuit Lab Setup Guide

An electronics bench is a known thing. There is a soldering iron, a bench power supply, a multimeter, an oscilloscope, a logic analyzer, and a box of parts. You can walk into any electronics lab on Earth and recognize it. The tools are different brands, but the *roles* are identical, and an engineer who knows the roles can sit down at an unfamiliar bench and work.

This appendix sets up the cognitive engineer's equivalent: the **circuit lab** you author, validate, simulate, and test Cognitive Circuit Boards in. By the end you will know what each tool on the bench does, how the tools connect into one workflow, how to lay out a project so your `.ccdl` files, test suites, golden traces, and evidence packets each have a home, and how to read the diagnostics the toolchain emits.

One thing has to be said plainly before anything else, because the rest of this appendix depends on it.

> **Read this before you try to install anything.** The CAS circuit toolchain described in this book — the CCDL compiler (parser + validator), the circuit simulator, and the `cas test` runner — is a **specified design**, set out in the implementation blueprint roadmap. It is **not a shipped binary you can download and run today.** This appendix describes *the lab you are setting up* and *the interface the tooling is designed to expose*, the same way a datasheet describes a part before the part is on your desk. Every command shown here is the **intended interface**, not a transcript of a real run. Where something does not exist yet, it is marked **(forthcoming)**. Nowhere in this appendix will you find a fabricated install step for software that does not exist, a pasted run log, or an invented pass/fail count. The honest framing the whole book uses (Chapter 4, Chapter 23) holds here: *"the compiler is designed to check X"* is a contract you can rely on; *"I ran it and got X"* is a sentence we do not write.

With that bright line drawn, here is the bench.

## The Toolchain: Four Tools, One Workflow

A cognitive circuit goes through the same lifecycle a physical board does: you draw it, you check the drawing for errors, you simulate its behavior before committing to it, you test it against a suite of inputs, and you keep a record of what you found. Four tools cover that lifecycle. Think of them as the four instruments that are always on the bench.

| Tool | Electronics analog | What it does |
|---|---|---|
| **CCDL editor** | Schematic capture (the drawing program) | Where you *author* the circuit — write the `.ccdl` file that names states, instantiates components, and wires them together. |
| **CAS compiler** (parser + validator) | Design-rule checker (DRC) | *Parses* the CCDL into a circuit graph, then *validates* it against the structural rules — emits the `E-CJT-*` / `W-CJT-*` diagnostics. |
| **Circuit simulator** | SPICE | *Simulates* the circuit's behavior on a given input without deploying it — computes operating regions, gains, and test-point readings the design predicts. |
| **Test harness / runner** (`cas test`) | Automated test bench (ATE) | *Runs* a named suite against the circuit, exercises prompt classes and fault injections, and reports per-test status against golden traces. |

These four are not independent gadgets you pick from. They form a **pipeline**, and the output of each is the input of the next:

```
author  ──▶  validate  ──▶  simulate  ──▶  test  ──▶  evidence packet
(editor)     (compiler)     (simulator)    (runner)    (signed record)
   │             │              │             │              │
 .ccdl      circuit graph   operating-     per-test       golden traces
            + diagnostics   point readings  status        + coverage report
```

You author a `.ccdl` file in the editor. You hand it to the compiler, which parses it into a circuit graph and runs the design-rule check; if it emits an `E-CJT-*` error, you go back to the editor — there is no point simulating a circuit that does not pass DRC. Once it validates clean, you simulate it to see the operating-point behavior the design predicts. Then you run the test suite, which exercises the board across prompt classes and fault injections. Finally, the passing run plus its golden traces and coverage report become the **evidence packet** — the record you hand a reviewer or a regulator, the cognitive equivalent of the certification folder taped inside a pacemaker's cabinet door (Chapter 23).

Each tool is worth understanding on its own before you watch them work together.

### The CCDL Editor — Where You Draw the Circuit

CCDL (**Cognitive Circuit Description Language**) is the schematic-as-text format you met in Chapter 4. A `.ccdl` file is a parts list and a wiring diagram in one: you declare the `input` and `output` terminals, name the cognitive states the circuit touches as `node`s, instantiate the components (CJTs, resistors, capacitors, diodes, filters), draw the connections, and place your `probe` test points.

The editor is *any text editor*. CCDL is plain text, so the bench's "schematic capture" tool is whatever you already write code in — VS Code, Vim, Emacs, a plain editor. There is nothing to install here that you do not already have. What a CCDL-aware editor *adds* — syntax highlighting for state literals, inline display of `E-CJT-*` diagnostics, autocompletion of node names — is an editor integration (a language-server plugin) that is **(forthcoming)** alongside the compiler. You do not need it to author circuits; you need it to author them comfortably. For now, treat the editor as a plain text file you write CCDL into, and let the compiler be the thing that tells you whether the CCDL is correct.

The one editor discipline worth adopting immediately is the one from Chapter 4's Bench Note: **name your nodes, do not inline your literals.** Declare `node question: ^8^C_{F2}|A;` once and refer to `question` everywhere it is used. A literal retyped in two places drifts in two places; a node named once cannot.

### The CAS Compiler — The Design-Rule Check

The compiler does two jobs, in order. First it **parses**: it reads the `.ccdl` text and builds a circuit graph — the nodes, the components, the wires between them — or it rejects the file with a syntax error if the text is malformed. Then it **validates**: it walks that graph and checks every structural rule a Cognitive Circuit must obey, emitting a diagnostic for each violation.

This second step is the **design-rule check (DRC)**. On a physical PCB, the DRC is the software pass that catches a trace too close to a pad, a power net shorted to ground, a component footprint that does not match its part — structural errors caught *before* the board is fabricated, when fixing them costs a keystroke instead of a respin. The CAS compiler's validator is exactly that: it catches structural errors in the cognitive circuit before you ever simulate or deploy it.

The rules it checks are the ones the book has been building toward. A CJT must have a bias terminal (omit it and the validator raises `E-CJT-001 MissingBias`). A bias must sit in a domain compatible with its cause (a wild mismatch raises `E-CJT-008 CjtCrossDomainBias`; an outright illegal bias domain raises `E-CJT-002 InvalidBiasDomain`). A gain must not diverge (`E-CJT-005 GainDivergence`). A resistor and the CJT cause it constrains must speak about the *same* state, or the series wiring is not real. The full list of codes is in the troubleshooting table at the end of this appendix.

> **Status:** the parser-plus-validator is a **(forthcoming)** design. The *rules* it enforces are real and stated throughout the book — you can apply them by hand today as you author, exactly as Chapters 4 and 23 do. What is forthcoming is the program that applies them for you. When this appendix says "the compiler rejects this," read it as a design rule you can rely on, not a run you can quote.

### The Circuit Simulator — SPICE for Cognition

A schematic that passes the DRC is structurally legal. That does not mean it *behaves* the way you intend. In electronics, between "the design rules pass" and "I fabricate the board" sits **SPICE** — a simulator that computes how the circuit will behave under given inputs without you having to build it. You feed SPICE a netlist and an input signal; it returns the voltages and currents at every node. You find out the amplifier clips, or the filter rings, or the supply sags, while it is still cheap to change.

The cognitive simulator plays the same role. Given a validated circuit and an input fixture, it computes the **operating point** the design predicts: which region each CJT is in (cutoff / active / saturation / breakdown), the gain each is delivering, the activation level at every node, and the reading you would expect at each `probe`. It is how you answer Chapter 4's three-prompt question — *does a vague prompt sag the CJT toward cutoff? does an overloaded prompt bump the saturation ceiling?* — by computing it from the parameters, rather than by reasoning about it in prose.

The honesty line matters most here, because a simulator is exactly the tool whose output is tempting to quote as if it were a measurement. It is not. The simulator computes the **expected design behavior** that follows from the parameters *you chose* — a β=2.4 nameplate, a sat=0.85 ceiling, an R=30 series constraint. Those are design choices, and the simulator propagates their consequences. It is **not** running a real language model and reporting what the model did. The simulator is **(forthcoming)**; when it ships, its readings will be design-predicted operating points, not empirical model measurements, and the book will keep that distinction bright.

### The Test Harness / Runner — The Automated Test Bench

The last tool is the one that runs everything else, repeatedly, on demand. The **test runner** — invoked as `cas test` — executes a named suite of tests against a circuit and reports per-test status. It is the cognitive equivalent of automated test equipment (ATE) on a production line: a rack that clips onto the board, runs a scripted battery of stimulus-and-measure steps, and prints a pass/fail sheet, so a human does not run forty tests by hand on every change.

Chapter 23 lays out what the runner exercises: unit tests (each CJT against its datasheet), integration tests (the seams between stages), regression tests (the kept-forever set), the five prompt classes (benign, harmful, ambiguous, adversarial, edge), fault injections (does the board fail *closed*?), and coverage metrics (what fraction of the board the suite actually touched). You select which subset runs with `--suite`:

| Suite | What the runner is designed to exercise |
|---|---|
| `--suite=unit` | Every CJT's β against its datasheet; saturation ceilings; cutoff floors |
| `--suite=integration` | Cascade seams, domain-descent legality, differential shared-bias / CMRR |
| `--suite=regression` | The full kept-forever set of previously-passing tests |
| `--suite=safety_critical` | Fault injection (fail-closed), saturation locks, fuse latch, the harmful/adversarial/edge classes |
| `--suite=all` | Every suite, bottom to top of the test pyramid |

> **Status:** the runner, like the compiler and simulator, is a **(forthcoming)** design in the implementation blueprint. The command and the suite table above are its *interface* and its *contract* — what each suite is designed to check — not a transcript. This appendix will not paste a run or invent "47 of 50 passed." What you can rely on is the contract.

## Your Bench: A First-Build Walkthrough

This is the walkthrough. You will author a small circuit, validate it, run the design-rule check, run a test suite, and read the test-point output — the full author → validate → simulate → test → evidence loop on one tiny board. Every command is the **intended interface** of the forthcoming toolchain; the design reasoning at each step is real and you can do it by hand today.

We will use the three-component amplifier from Chapter 4 — the question→answer CJT with a series resistor — because you already understand it.

### Step 1 — Write your first `.ccdl` file

In your editor, create `first_circuit.ccdl` and author the circuit:

```cas
circuit first_circuit {
    input:  prompt;
    output: response;

    // Name the cognitive states once; reuse them below.
    node question:   ^8^C_{F2}|A;   // cause: a wisdom-seeking question
    node experience: ^5^E_{F4}|f;   // bias: accumulated, affective experience
    node answer:     ^9^C_{F6}|A;   // effect: a structured analytical answer

    // Series resistor: tame runaway expansion of the trigger.
    resistor r1: Resistor< question, R=30 >;

    // The question -> answer transistor.
    cjt c1: CJT< question | experience => answer > [β=2.4];

    // Test point on the effect terminal.
    probe tp1: answer;
}
```

That is the whole source file. Note the discipline already in play: `question` is declared once and referenced by both the resistor and the CJT, so the series wiring is a fact rather than a coincidence you have to retype correctly twice.

### Step 2 — Validate it (parse + DRC)

Hand the file to the compiler:

```bash
cas validate first_circuit.ccdl          # (forthcoming) parse + design-rule check
```

The compiler parses the text into a circuit graph and runs the design-rule check. A clean file produces no errors and you proceed. A structural mistake produces a diagnostic keyed to one of the `E-CJT-*` codes. Suppose you had forgotten the bias terminal — written `CJT< question => answer >` with no `| experience`. The DRC is designed to reject it:

```
E-CJT-001 MissingBias  at c1: a CJT must have a bias terminal; declare and wire a bias node.
```

You go back to the editor, add the bias, and re-validate. This is the loop the DRC exists to make fast: you catch the missing bias here, at a keystroke, not three stages downstream when the board behaves strangely and you have to guess why. Run `cas validate` until it is clean before you do anything else — there is no point simulating a circuit that does not pass DRC.

### Step 3 — Run the design-rule check on its own (optional, explicit)

`cas validate` runs the full parse-and-DRC together. When you want only the structural design-rule pass — for example, in a fast pre-commit hook that should not pay for a full simulation — you can request the DRC explicitly:

```bash
cas drc first_circuit.ccdl               # (forthcoming) design-rule check only
```

This is the same validator, run as a standalone gate. It reports the `E-CJT-*` errors and `W-CJT-*` warnings and nothing else. Treat a clean DRC as the entry requirement for everything downstream: simulate and test only what the DRC has passed.

### Step 4 — Simulate it on an input

With the circuit validated, simulate its behavior on a prompt to see the operating point the design predicts:

```bash
cas sim first_circuit.ccdl --input "What year was the first transistor demonstrated?"   # (forthcoming)
```

The simulator computes, from your chosen parameters, which region `c1` sits in, the gain it delivers, and the reading at `tp1`. For this crisp factual question the design predicts the CJT squarely in its **active region**, delivering close to its β=2.4 nameplate — exactly the reasoning Chapter 4 did in prose, now computed from the parameters. Feed it the vague prompt from Chapter 4 instead and the design predicts the CJT sagging toward cutoff with a below-nameplate gain; feed it the overloaded five-part prompt and the design predicts it bumping the sat ceiling, raising `W-CJT-004 CjtSaturation`. The simulator turns "I expect" into a computed operating point — still a design prediction from your parameters, never a measured model result.

### Step 5 — Run a test suite

A single simulated input is one data point. The test runner exercises the circuit across a whole suite at once. Author your tests (in the `test { … }` form from Chapter 23) and run the suite:

```bash
cas test first_circuit.ccdl --suite=unit             # (forthcoming) every CJT vs datasheet
cas test first_circuit.ccdl --suite=safety_critical  # (forthcoming) the deployment gate
```

The `unit` suite drives `c1`'s gain test (does β match 2.4 within tolerance, in the active region?) and, for any saturating CJT, its saturation test. On a safety board you would run `--suite=safety_critical` as the deployment gate — the subset whose failure means *do not ship*: fault injection (does the board fail closed?), saturation locks, the fuse latch, and the harmful/adversarial/edge prompt classes. For the running artifact of the book, that command reads exactly as Chapter 23 shows it:

```bash
cas test csb.ccdl --suite=safety_critical            # (forthcoming) the CSB deployment gate
```

The runner reports per-test status against the suite's expectations and golden traces. It is the rack that runs your forty tests so you do not run them by hand on every change.

### Step 6 — Read the test-point output

The whole point of a `probe` is that you can read it. After a simulation or a test run, the reading at `tp1` tells you three things — the same three Chapter 4 told you to look for:

- **Which region is the CJT in?** Active is healthy. Cutoff means the input was too weak (bias below the floor). Saturation means the input was too strong, or the resistor too small.
- **What gain is it delivering?** Compare the reading against the β=2.4 nameplate. Near nameplate in the active region is healthy; a sagging gain means you are near cutoff; a pinned effect with a `W-CJT-004` warning means saturation.
- **Is the effect the right type?** You should read a `^9^C_{F6}|A` state. If you instead read an involution flip (a `^9`→`^8`, or a `^2`→`^3`), the transistor has gone into breakdown and you have found a bug.

One probe on the output tells you whether this little amplifier is working. That is the entire purpose of a test point, and reading it is the last step of the bench loop before the run becomes part of your evidence.

### Step 7 — Save the evidence

A clean validate, a simulated operating point that matches the design, and a passing suite are worth nothing if you cannot show them later. The final step is to capture the run as an **evidence packet** — the golden traces and coverage report from the passing run, stored where a reviewer can find them. The next section gives every artifact a home.

## Project Layout: Where Everything Lives

A bench with parts scattered across it is a bench you make mistakes at. Give every artifact a fixed home. A workable layout for a cognitive-circuit project — using the book's running artifact, the Cognitive Safety Board, as the example board:

```
my_project/
├── circuits/                       # the .ccdl source — your schematics
│   ├── csb.ccdl                    #   the Cognitive Safety Board (Chapter 18)
│   └── first_circuit.ccdl          #   the Chapter 4 amplifier
│
├── tests/                          # test suites, authored in the test{ } form
│   ├── unit/                       #   one CJT vs its datasheet
│   ├── integration/                #   the seams between stages
│   ├── regression/                 #   the kept-forever set — never delete a passing test
│   └── safety_critical/            #   the deployment gate: fault injection, classes
│
├── golden/                         # golden traces — known-good TP readings per input
│   ├── benign_lentil_soup.trace
│   ├── harmful_request.trace
│   └── adversarial_injection.trace
│
├── evidence/                       # evidence packets — the signed record for review
│   └── 2026-06-18_safety_critical/ #   one dated packet per certification run
│       ├── run_summary.md          #     per-test status (the runner's report)
│       ├── coverage_report.md      #     CJT / path / region coverage
│       ├── golden_diffs/           #     any deviations from the golden traces
│       └── circuit_snapshot.ccdl   #     the exact .ccdl that produced this packet
│
└── lib/                            # (optional) reusable sub-circuits and components
    └── differential_pair.ccdl      #   shared building blocks, imported by circuits
```

The principles behind the layout matter more than the exact names:

- **`circuits/` holds source, and only source.** A `.ccdl` file is the schematic. It is the thing you edit; everything else is derived from it.
- **`tests/` mirrors the test pyramid** (Chapter 23) — a directory per layer, so "run the regression set" maps to a folder, not a memory. The kept-forever rule lives here: nothing leaves `regression/`.
- **`golden/` holds the reference captures.** A golden trace is the oscilloscope photo taped inside the cabinet door — the known-good TP readings for a fixed input, that every future run is compared against. They live apart from the tests because they are *expected design behavior* you reviewed and froze, not code you change casually.
- **`evidence/` holds the certification folder, one dated packet per run.** Each packet bundles the run summary, the coverage report, any golden-trace diffs, and — critically — a snapshot of the exact `.ccdl` that produced it, so the evidence is reproducible. This is the artifact you hand a regulator. It is also why `circuit_snapshot.ccdl` is in the packet: an evidence packet that does not pin the exact source it came from proves nothing.
- **`lib/` holds reusable sub-circuits** so a differential pair or a feedback filter authored once can be imported into several boards instead of copy-pasted (and drifted).

Put the project under version control. The combination — versioned source, kept-forever regression tests, frozen golden traces, and dated evidence packets — is what makes a green suite a *license to change* (Chapter 23): you can prove not only that the board works now, but that it still works the same way it did when you last certified it.

## Troubleshooting: The E-CJT Diagnostics

When the compiler's design-rule check or the simulator flags your circuit, it does so with one of the codes from the cheat-sheet. Here is each one, what it means, and where to look. Codes prefixed `E-` are **errors** — the design-rule check rejects the circuit and you must fix it before proceeding. Codes prefixed `W-` are **warnings** — the circuit is structurally legal, but the toolchain is telling you about a condition that is sometimes a defect and sometimes, on a safety board, exactly what you intended.

| Code | Meaning | Where to look |
|---|---|---|
| **E-CJT-001** `MissingBias` | A CJT has no bias terminal. A transistor with no base cannot control anything. | The `CJT< … >` instantiation — you wrote `cause => effect` with no `\| bias`. Declare a bias node and wire it. |
| **E-CJT-002** `InvalidBiasDomain` | The bias sits in a domain that is not legal for this CJT at all. | The bias node's domain (`P` / `C` / `E` / `O`). Check it against the Domain Descent order `P ≻ C ≻ E ≻ O` and the cause's domain. |
| **E-CJT-003** `CjtCutoff` | The CJT is held below its cutoff floor — bias too weak, β ≈ 0, no effect produced. | The bias activation vs the `cutoff` parameter. Expected on empty prompts; a *bug* if it fires on good prompts (check the bias node is actually driven). |
| **W-CJT-004** `CjtSaturation` | The effect has pinned at the `sat` ceiling; more cause produces no more effect. | The cause level vs the `sat` parameter. A **defect** on an ordinary amp (raise `R`, split the prompt); the **intended** status on a saturated safety stage (Chapter 23 — this is the certification question, not an error). |
| **E-CJT-005** `GainDivergence` | β has run away — the gain is diverging instead of settling to a finite value. | The `β` parameter and the feedback paths. A positive feedback loop with too high a loop gain is the usual culprit. |
| **W-CJT-006** `CjtShortCircuit` | The cause passes straight to the effect with the bias bypassed — the control terminal does nothing, β runs away. | The wiring between cause and effect. This is the "shorted transistor" — the fault you *inject deliberately* in fault testing (Chapter 23), and a defect if it appears unbidden. |
| **W-CJT-007** `CjtCascadeDepth` | A cascade of CJTs is deeper than the recommended limit; signal degradation or compounding gain risk accumulates across stages. | The chain length. Consider a buffer/regulator stage, or splitting the cascade. Review compounded β down the chain. |
| **E-CJT-008** `CjtCrossDomainBias` | The bias domain is incompatible with the cause domain — a bias reaching across an illegal domain boundary. | The bias node's domain vs the cause node's domain. Keep the bias domain compatible with the cause; this is the seam integration tests also guard (Chapter 23). |

Two reading habits make this table useful rather than cryptic. First, **the code points you at a part of the circuit, not just a symptom** — `E-CJT-001` is always about a CJT instantiation; `W-CJT-004` is always about a cause level meeting a `sat` ceiling; `E-CJT-008` is always about a bias domain meeting a cause domain. Knowing *where* a code lives turns "the compiler is unhappy" into "go look at this CJT's bias." Second, **`W-CJT-004` and `W-CJT-006` are warnings on purpose**, because each is a defect in one context and a design intent in another: a saturated safety stage *should* report `W-CJT-004`, and a fault-injection test *deliberately* induces `W-CJT-006`. A warning is the toolchain asking "did you mean this?" — and on a safety board, sometimes you did.

> **Bench Note — the toolchain tells you where, you decide whether.** The design-rule check is good at *where* (this CJT, this bias domain, this cause level) and deliberately agnostic about *whether a warning is bad*. An `E-` code is unambiguous: fix it. A `W-` code is a question: a `W-CJT-004` on a general-purpose amplifier means raise the resistor; the same code on the CSB's Stage 3 means the safety latch is doing its job. Read the warning, find the part it points at, and ask whether this is the part that is *supposed* to saturate or short. The toolchain locates the condition; the engineer judges it.

## What You Have Set Up

You now have a bench. To recap what is on it and how honest you should be about each piece:

- A **CCDL editor** — any text editor today; a CCDL-aware language-server plugin is **(forthcoming)**. You author `.ccdl` source here, naming nodes once so the wiring is a fact.
- A **CAS compiler** — a parser plus a design-rule-checking validator, **(forthcoming)**, that turns CCDL into a circuit graph and emits the `E-CJT-*` / `W-CJT-*` diagnostics. The rules it enforces are real and you can apply them by hand now.
- A **circuit simulator** — SPICE for cognition, **(forthcoming)**, that computes the operating point a circuit's parameters predict. Its readings are *design predictions from your chosen parameters*, never measured model results.
- A **test runner** (`cas test`) — the automated bench, **(forthcoming)**, that runs named suites (unit, integration, regression, safety_critical, all) and reports per-test status against golden traces.
- A **project layout** that gives source, tests, golden traces, and dated evidence packets each a fixed home, under version control, so a green suite becomes a license to change.

The workflow that ties them together is the one to keep in your head: **author → validate → simulate → test → evidence packet.** Draw the circuit, prove it is structurally legal, see what its parameters predict, exercise it across a suite, and freeze the result into a record you can hand a reviewer. The instruments are forthcoming; the discipline is available today. Set up the bench as if the tools were on it, author and reason as the design specifies, and you will be ready the day each tool ships — with circuits already laid out the way the toolchain expects to find them.
