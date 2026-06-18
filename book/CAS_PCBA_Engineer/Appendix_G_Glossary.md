# Appendix G — Glossary

This glossary covers every important term in *CAS PCBA Engineer* — both the
electronics vocabulary the book borrows and the CAS / cognitive vocabulary the
book teaches. Cross-references to other entries are *italicized*. Where a term has
both an electronic meaning and a CAS meaning, both are given, because the whole
point of the book is that they share one structural role across two substrates.

---

**Above/Cause (`^8`)** — The eighth *Noetic*. An Idea that triggers a *different*
Idea to come to Mind. This is **associative triggering** ("that reminds me," "one
thing leads to another"), not deductive reasoning; deductive causal analysis is a
compound of *Male* (`^6`) plus *Below/Effect* (`^9`). The Cause terminal of a *CJT*
is typically an `^8` state. Involution partner of *Below/Effect* (`^9`).

**Active region** — The normal, linear operating region of a transistor or *CJT*,
where output changes roughly in proportion to input: Δeffect ≈ β·Δcause. A CJT
biased into the active region is amplifying its cause→effect transition predictably.
Contrast *cutoff*, *saturation*, *breakdown*.

**ADC (Analog-to-Digital Converter)** — A device that converts a continuous analog
signal into discrete digital samples. In the CAS framing, the boundary where a
graded cognitive activation is quantized into a discrete decision or category.

**Affective (`|f`)** — The *Register* of value-laden, feeling-toned operation. In a
human, an emotional response; in an AI, a preference-weighted, value-tuned output.
Written with a **lowercase `f`** to avoid colliding with the `F`-prefixed *Drive*
notation; the compiler enforces the lowercase.

**Analytical (`|A`)** — The *Register* of explicit, sequential, logical, reason-based
operation. In a human, conscious step-by-step reasoning; in an AI, chain-of-thought.

**Bias** — (1) *Electronics:* the steady DC condition that sets a transistor's
operating point so a signal can be amplified. (2) *CJT:* the **B** terminal (the
transistor's base), the accumulated substrate that controls the cause→effect
transition — *Female* (`^5`) experience, constitution, *Dial* settings, and *Drive*
configuration. A CJT with no bias is a compile error (E-CJT-001 MissingBias).

**Below/Effect (`^9`)** — The ninth *Noetic*. The Idea brought to Mind by an
*Above/Cause* trigger — the thought that "pops up" in response. The Effect terminal
of a *CJT* is typically a `^9` state. Involution partner of *Above/Cause* (`^8`).

**Bode plot** — A pair of graphs showing how a circuit's *gain* and phase change with
frequency. Used to read stability margins (*phase margin*, *gain margin*) at a glance.

**Breakdown** — The overload region of a transistor or *CJT*. In a CJT, breakdown is
when the output **flips to its involution pair** — a *Positive* (`^2`) state inverts
to *Negative* (`^3`) under stress. *Self-dual* Noetics have nowhere to flip, which
makes them structurally stable anchors.

**Brownout** — A partial loss of supply voltage that leaves a circuit in an undefined,
unreliable state rather than cleanly off. The cognitive analog: degraded resource or
context that produces unstable behavior instead of a clean refusal or halt.

**Capacitor** — A component that stores charge and releases it later, smoothing or
delaying a signal. CAS analog: a store of accumulated *Female* (`^5`) experience.
Syntax: `Capacitor< ^5^E_{F4}|f, C=100, leakage=0.01 >`, where **leakage** models
forgetting.

**Cause** — The **C** terminal of a *CJT* (the transistor's collector / input): the
Idea entering the Mind, typically an *Above/Cause* (`^8`) state. See *CJT*.

**CCB (Cognitive Circuit Board)** — A safety-critical cognitive architecture built
from typed CAS components (*CJTs*, *resistors*, *capacitors*, *diodes*, *filters*,
*feedback* loops) the way an electrical engineer builds a circuit from a schematic.
The central object the book teaches the reader to design, test, and deploy.

**CCDL (Cognitive Circuit Description Language)** — The schematic-as-text format used
to author a *CCB*: it declares inputs, outputs, nodes (state literals), *CJTs*,
*feedback* paths, and *probes* (test points) inside a `circuit { … }` block. The
language the engineer writes in; the *compiler* validates it.

**CDAB (Cognitive Differential Amplifier Board)** — One of the five Part IV reference
boards: a board built around a *differential pair* that amplifies the difference
between two cognitive inputs while rejecting what they share (*CMRR*).

**Certification tier** — The engineering grade assigned to a finished board by the
NCCS scale: Platinum (90–100), Gold (75–89), Silver (60–74), Bronze (40–59),
Fail (0–39). A certification is an engineering claim about measured structural
behavior, not a claim about values or consciousness. See *NCCS*.

**Characteristic curve** — The graph of a device's output against its input (e.g., a
transistor's collector current vs. base current). It shows the *cutoff*, *active*,
*saturation*, and *breakdown* regions at a glance; the *operating point* is one point
on this curve.

**CJT (Cognitive Junction Transistor)** — The book's central component. It models a
cognitive state transition as a transistor: a small signal at the *Bias* terminal
controls a larger cause→effect transition. Syntax:
`CJT< cause | bias => effect > [β=2.4, sat=0.95, cutoff=0.1, region=active]`.
Terminals: **C** *Cause* (collector/input), **B** *Bias* (base/control), **E**
*Effect* (emitter/output); **β** is the *gain*.

**Cluster** — A named group of related CAS states treated as one unit — for example,
the family of all *Negative* (`^3`) states across the four *Domains*. Clusters let
you reference a family without enumerating every member.

**CMB (Cognitive Memory Board)** — One of the five Part IV reference boards: a board
built around *capacitors* and *inductors* to store, retain, and decay accumulated
*Female* (`^5`) experience.

**CMRR (Common-Mode Rejection Ratio)** — A measure of how well a *differential pair*
amplifies the difference between its two inputs while rejecting any signal common to
both. High CMRR means shared noise (or shared framing) is suppressed.

**COB (Cognitive Oscillator Board)** — One of the five Part IV reference boards: a
board built around an *oscillator* that cycles through a repeating *sequence* (*Phi*)
of cognitive states — the substrate for habit loops and rhythmic behavior.

**Cognitive (C)** — The reasoning *Domain*: understanding and working things through.
Second in the precedence order **P ≻ C ≻ E ≻ O**.

**Compiler** — The CAS tool that parses and validates every literal, operator,
*recipe*, and *binding*. It checks Noetics are real, domains legal, drives in range,
registers correctly lowercase-`f`, and `×` operations properly named. Per the book's
status honesty rule, the CJT/CCDL compiler pass is a *design* (a roadmap target), so
"the compiler will reject this" is a design rule the book relies on — never a claimed
run result. Error codes include E-CJT-001 MissingBias, E-CJT-003 CjtCutoff,
W-CJT-004 CjtSaturation, E-CJT-005 GainDivergence, E-CJT-008 CjtCrossDomainBias.

**CPMB (Cognitive Power Management Board)** — One of the five Part IV reference boards:
a board built around *regulators*, *fuses*, and *power sequencing* to manage the
"supply" of cognitive resource and fail safely under *brownout*.

**CSB (Cognitive Safety Board)** — The book's running spine: the AI-alignment firewall
designed in full in Chapter 18 (matching SOP-PO-005). Earlier chapters foreshadow its
sub-components; later chapters operate on it. The first of the five Part IV reference
boards.

**Current mirror** — A circuit that copies (mirrors) a reference current into one or
more other branches. CAS analog: replicating one branch's activation level into
parallel cognitive paths so they share a common drive level.

**Cutoff** — (1) *CJT region:* the *Bias* is below the threshold needed to conduct, so
β ≈ 0 and there is no effect (compile signal E-CJT-003 CjtCutoff). (2) *Parameter:* the
bias floor in a CJT's parameter list below which β collapses to zero.

**DAC (Digital-to-Analog Converter)** — A device that converts discrete digital values
back into a continuous analog signal. The inverse of an *ADC*; in CAS, re-expanding a
discrete decision into graded activation.

**Darlington pair** — Two transistors wired so the output of the first drives the
second, multiplying their gains for very high overall *gain*. CAS analog: cascaded
*CJTs* whose β values multiply to produce strong amplification of a faint cause.

**Diode** — A one-way conductor: it passes flow in one direction and blocks the
reverse. CAS analog: one-way *Domain* conductance, e.g. `Diode< ^P -> ^C >`, letting
a principle flow into reasoning but not the reverse.

**Differential pair** — Two matched transistors (or *CJTs*) that respond to the
*difference* between two inputs while rejecting what is common to both. The core of
the *CDAB* and the basis of high *CMRR*.

**Dial** — A per-Cognitive-Operator setting (an integer 3–9) that tunes how strongly an
operator participates, part of a *CJT*'s *Bias*. Hard safety constraints apply (no dial
below 3 or above 9; *involution-pair* dials cannot diverge by more than 4 points).

**Domain** — The CAS axis answering *where* a cognitive operation happens. Four values
in strict precedence order **P ≻ C ≻ E ≻ O**: *Principled*, *Cognitive*, *Evaluative*,
*Operational*. Written as a single letter after the *Noetic*.

**Domain Descent** — The normal causal flow down the *Domain* precedence order:
**P → C → E → O** (a principle causes reasoning, which causes a judgment, which causes
an action). The reverse path **O → P** is the feedback path by which consequences
update principles — the backbone of the *CSB*'s self-correction.

**Drive** — The CAS axis answering *why* a cognitive operation is moving — the
motivational pull. Seven values written `_{F1}`–`_{F7}`: **F1 Unity**, **F2 Wisdom**,
**F3 Vitality**, **F4 Connection**, **F5 Agency**, **F6 Structure**, **F7 Purpose**.
Inversion pairs: F1↔F7, F2↔F6, F3↔F5; **F4 Connection** is *self-dual*. Drives are not
mutually exclusive — several can be active at once — but a literal usually names the
dominant one.

**Deployment ladder** — The staged path a board climbs from design to production,
each rung gated by tests, *evidence packets*, and a `/verify` pass before promotion.

**Effect** — The **E** terminal of a *CJT* (the transistor's emitter / output): the
Idea produced, typically a *Below/Effect* (`^9`) state. See *CJT*.

**Embodied (`|E`)** — The *Register* of sensorimotor, concrete, direct physical
engagement. In a human, a gut reaction or kinesthetic knowing; in an AI, a real-time
sensor-actuator control loop.

**Evaluative (E)** — The judgment *Domain*: assessment and weighing of options. Third in
the precedence order **P ≻ C ≻ E ≻ O**. (Distinct from the *Embodied* register `|E`,
which is an axis-different use of the letter E.)

**Evidence packet** — The bundle of test outputs, *probe* readings, and verification
results captured for a board, used to justify a *certification tier* and to make every
claim traceable back to its source. The auditable record behind a `/verify` pass.

**Feedback** — Routing a circuit's output back to its input. **Negative feedback** (the
common, stabilizing kind) subtracts the output from the input to reduce error and
linearize *gain*; **positive feedback** adds it, driving the system toward extremes or
oscillation. In CCDL: `feedback evaluate -> bias_principles [β=0.3]`. The *CSB*'s
O → P self-correction loop is negative feedback.

**Female (`^5`)** — The fifth *Noetic*. A Mind impregnated with Ideas — the Ideas a
Mind is composed of, i.e. **accumulated experience**, the sum of everything a system
has absorbed. For an AI, `^5` is the training data plus the fine-tuning corpus. It is
the substrate that biases a *CJT*. Involution partner of *Male* (`^6`).

**Filter** — A circuit that passes some frequencies and blocks others. **Low-pass**
passes slow signals and blocks fast ones; **high-pass** does the reverse; **band-pass**
passes a middle band; **notch** (band-stop) rejects a narrow band. CAS analog:
selectively passing cognitive activations by some property while attenuating others.

**Fisher-Rao distance** — The geometry CAS uses to measure how far apart two cognitive
states are on the *open simplex* Δ39°. The geodesic distance between probability
vectors p and q is `d_FR(p,q) = 2·arccos(Σ√(pₖqₖ))`. It defines *CJT* *gain* formally:
large-signal `β = d_FR(E_after, E_before) / d_FR(C_after, C_before)`.

**Fuse** — A one-time protective element that permanently breaks the circuit when flow
exceeds a threshold. CAS analog: a hard cutout, e.g.
`Fuse< ^8^O_{F5}|E, threshold=0.9, action=permanent_block >` — once tripped, that
pathway is blocked for good.

**Gain (β)** — How strongly a transistor or *CJT* amplifies: the ratio of output change
to input change. In a CJT, β < 1 attenuates, β = 1 is unity, β > 1 amplifies. Defined
formally via *Fisher-Rao distance*. Runaway gain is the compile error E-CJT-005
GainDivergence.

**Idea (`^0`)** — The zeroth *Noetic*: all things in and outside the Mind — the raw
content, unconsidered. The monoid identity element under composition (`∘`); a
*self-dual*.

**Inductor** — A component that resists changes in flow, storing energy in a magnetic
field and smoothing abrupt changes. CAS analog: inertia against pattern change — habit
or *Rhythm* (`^7`) momentum, e.g. `Inductor< ^7^O_{F6}|E, L=50 >`.

**Input resistance (rπ)** — A *CJT* parameter: the resistance the *Bias* terminal
presents to change — informally, the state's "stubbornness to bias change." High rπ
means the cause→effect transition is hard to re-bias.

**Involution pair** — Two *Noetics* (or two *Drives*) that are structural inverses of
each other: `^2`↔`^3`, `^5`↔`^6`, `^8`↔`^9` (Noetics); F1↔F7, F2↔F6, F3↔F5 (Drives).
Under *breakdown*, a CJT's output flips to its involution partner. *Dial* settings of an
involution pair cannot diverge by more than 4 points.

**Lacunarity** — A structural gap: a prerequisite or state that is **absent** where the
architecture requires it (distinct from a present-but-wrong signal). In a *recipe*, a
missing ingredient that prevents the outcome from being produced.

**Load line** — A straight line drawn across a device's *characteristic curve*
representing the constraint imposed by the rest of the circuit (the load). Its
intersection with the curve fixes the *operating point*.

**Male (`^6`)** — The sixth *Noetic*. An Idea impregnated with another Idea — the Ideas
an Idea is composed of, i.e. **decomposition**: taking something apart to see what it is
made of, audit it, scrutinize it, find its flaws. Critique and analytical
fault-finding are `^6`, **not** *Negative* (`^3`). Involution partner of *Female* (`^5`).

**Mind (`^1`)** — The first *Noetic*: awareness that processes, stores, outputs, and
intakes Ideas. "Paying attention." A *self-dual*.

**NCCS (Noetic Compass Composite Score)** — The 0–100 composite score that grades a
cognitive architecture, weighting the cognitive-operator profile, domain coherence,
core-drive/RPM integrity, capability-pathway quality, inversion resistance, and social-
engineering resistance. The NCCS band sets the *certification tier*.

**Negative (`^3`)** — The third *Noetic*. An Idea the Mind is adverse to and repelled
by — **visceral aversion** ("can't stomach it," "rubs me the wrong way"), the cognitive
equivalent of recoiling from a bad smell. It is **not** analytical critique; auditing,
scrutinizing, or decomposing-and-testing is *Male* (`^6`). Involution partner of
*Positive* (`^2`).

**Noetic** — The CAS axis answering *what* structural cognitive operation is happening,
independent of subject matter — the "verbs" of cognition. Ten values, `^0`–`^9`:
*Idea*, *Mind*, *Positive*, *Negative*, *Vibration*, *Female*, *Male*, *Rhythm*,
*Above/Cause*, *Below/Effect*. The names are canonical and are never renamed to their
circuit function.

**Notch filter** — See *Filter*. A band-stop filter that rejects a narrow band of
frequencies while passing everything else.

**Nyquist criterion** — A stability test: a *feedback* system is stable if its loop
response, plotted on a Nyquist diagram, does not encircle the critical point. The
frequency-domain companion to reading *phase margin* and *gain margin* off a *Bode plot*.

**Op-amp (operational amplifier)** — A very-high-gain differential amplifier with two
inputs (non-inverting and inverting) and one output, almost always used with *feedback*
to set a precise, stable gain. Syntax:
`OpAmp< non_inverting=…, inverting=…, output=…, open_loop_gain=10000 >`.

**Open simplex Δ39°** — The CAS state space: the set of probability vectors over the 40
cognitive states with **every component strictly positive** and summing to 1
(`pₖ > 0`, Σpₖ = 1). "Open" because no state's probability is ever exactly zero. The
*Fisher-Rao distance* is the metric on this space.

**Operating point (Q-point)** — The steady-state DC condition (the quiescent point) at
which a transistor or *CJT* sits before any signal is applied — fixed by the *load line*
crossing the *characteristic curve*. It determines which *region* (cutoff/active/
saturation) the device operates in.

**Operational (O)** — The action *Domain*: concrete output and execution. Last in the
precedence order **P ≻ C ≻ E ≻ O**; the source of the **O → P** feedback path.

**Operators** — The symbols that wire CAS states together, with strict v7.7 discipline:
**`+`** co-presence/association (states active simultaneously but distinct);
**`×`** cross-register integration (genuine fusion, valid *only* when it names an
emergent result `(A × B) = ^n|Ω_name`); **`->`** directed transition over time;
**`|⟨R1,R2,R3⟩`** register-set specification (a state present in those registers, no
interaction claim). A same-Noetic multi-register `×` without a named result is invalid.

**Oscillator** — A circuit that produces a repeating waveform with no input — it cycles
on its own. CAS analog: a repeating *sequence* (*Phi*) of cognitive states, e.g.
`Oscillator< Phi< … >, frequency=… >`. The basis of the *COB* and of habit loops.

**Phase margin / gain margin** — Two stability cushions read from a *Bode plot*.
**Phase margin** is how much additional phase lag a *feedback* loop can tolerate before
it oscillates; **gain margin** is how much additional gain it can tolerate. Bigger
margins mean a more stable, harder-to-destabilize circuit.

**Phi (sequence)** — An ordered list of CAS states traversed in time — the cognitive
equivalent of a waveform: `Phi< ^8^C|A, ^3^O|E, ^9^E|f, ^0^P|T >`. A cycle that returns
to its start describes an oscillator or habit loop. See *Sequence*.

**PLL (Phase-Locked Loop)** — A *feedback* circuit that locks an oscillator's phase and
frequency onto a reference signal. CAS analog: a loop that entrains a system's *Rhythm*
(`^7`) to track an external pattern.

**Positive (`^2`)** — The second *Noetic*. An Idea the Mind has an affinity for and is
attracted toward. Involution partner of *Negative* (`^3`); under *breakdown* a Positive
state can invert to Negative.

**Power sequencing** — Bringing a circuit's supplies up (and down) in a controlled
order so dependent stages are never powered before their prerequisites. CAS analog:
satisfying prerequisites in the correct order before a dependent operation runs (see
*RPM*). Managed on the *CPMB*.

**Principled (P)** — The highest *Domain*: core commitments, values, and hard
boundaries — the constitution. First in the precedence order **P ≻ C ≻ E ≻ O**.

**Probe** — See *Test point*.

**Q factor** — A measure of how sharply a resonant circuit or *filter* is tuned: high Q
means a narrow, selective response; low Q means a broad, gentle one. CAS analog: how
sharply a cognitive path is tuned to a specific activation.

**Recipe (Θ)** — A specification of what is required to *produce* an outcome, with
proportional weights — read like a chemistry equation. Notation:
`Θ(Ω) = a·X₁ + b·X₂ + … → Ω`, e.g.
`Θ(Ω_safe_refusal) = 0.5·^3^P_{F7}|f + 0.3·^6^E_{F6}|A + 0.2·^9^O_{F5}|E → Ω_safe_refusal`.
The weights are proportional requirements; later analysis identifies which ingredient
is the bottleneck (limiting reagent) when the outcome falls short.

**Register** — The CAS axis answering *how* a cognitive operation operates — its
operational character. Four values written with a trailing pipe: **`|T`** *Transcendent*,
**`|A`** *Analytical*, **`|f`** *Affective* (lowercase f), **`|E`** *Embodied*. Register
is optional; an unspecified register means register-neutral.

**Regulator** — A circuit that holds an output at a fixed target despite changing input
or load. CAS analog: holding a cognitive state at a target within a tolerance, e.g.
`Regulator< target_state=^0^E_{F3}|f, tolerance=0.1 >`. A core part of the *CPMB*.

**Resistor** — A component that limits flow; higher resistance means more constrained
flow. CAS analog: limiting how much a cognitive activation propagates, e.g.
`Resistor< ^8^C_{F2}|A, R=50 >` — a higher R means a more constrained operation.

**Rhythm (`^7`)** — The seventh *Noetic*: the rate and pattern a Mind is exposed to an
Idea, entraining or conditioning it ("practice makes perfect"). A *self-dual*; the
basis of habit loops, oscillators, and the *inductor*'s pattern inertia.

**RPM (section-retraction)** — Prerequisite satisfaction structured as a one-directional
chain (A0 → Dₙ → Wₙ → Pₙ → Outcome). Mathematically it is a **section-retraction, not an
adjunction**: realizing a prerequisite after embedding it returns the identity
(`εI ∘ ηI = idI`), but re-embedding after realization may lose information
(`ηI ∘ εI ≠ id`). The practical rule: prerequisite satisfaction is **one-directional** —
the RPM gate must not assume reversibility. The cognitive analog of *power sequencing*.

**Saturation** — (1) *CJT region:* the *Effect* is maxed out, so more *Cause* produces
no further output (compile signal W-CJT-004 CjtSaturation). (2) *Parameter:* `sat`, the
plateau ceiling (0–1) a CJT's effect cannot exceed. A safety CJT is often designed to
saturate at a specified threshold by intent.

**Schmitt trigger** — A comparator with hysteresis: it switches at one threshold going
up and a lower threshold going down, so a noisy input produces a clean, chatter-free
output. CAS analog: a decision gate with built-in hysteresis that resists flip-flopping
on borderline inputs.

**Section-retraction** — See *RPM*. The one-directional structure of prerequisite
satisfaction; specifically *not* a reversible adjunction.

**Self-dual** — A *Noetic* (or *Drive*) that is its own structural inverse, with no
opposite partner: the Noetics *Idea* (`^0`), *Mind* (`^1`), *Vibration* (`^4`), and
*Rhythm* (`^7`); the Drive *F4 Connection*. Self-duals have nowhere to flip under
*breakdown*, which makes them stable anchors.

**Sequence (Phi)** — See *Phi*. An ordered traversal of CAS states over time, written
`Phi< s₁, s₂, s₃ >`.

**State literal** — A single CAS state written as a four-axis coordinate:
`^Noetic ^Domain _{Drive} |Register`, e.g. `^8^C_{F2}|A` = "an analytical association in
the cognitive domain, driven by wisdom." *Domain* almost always appears; *Drive* and
*Register* are optional.

**Test point (probe)** — A designated node in a circuit where a measurement can be taken
without disturbing operation. In CCDL, declared with `probe`, e.g. `probe tp1: expand;`.
Probe readings feed the *evidence packet* and the `/verify` workflow.

**Transconductance (gm)** — A *CJT* parameter: how much the *Effect* changes per unit
change in *Bias* (∂effect/∂bias) — informally, the state's **framing-sensitivity**. High
gm means small changes in bias swing the output a lot.

**Transcendent (`|T`)** — The *Register* of high-abstraction, purpose-orienting,
integrative operation. In a human, a felt sense of vision or calling; in an AI, a
high-level goal representation.

**Transformer** — (1) *Electronics:* a component that steps a voltage up or down via a
turns ratio, matching one stage's impedance to the next. (2) *CAS:* a *Domain* impedance
match, e.g. `Transformer< ^P -> ^C, ratio=0.5 >` — translating a principle into an
actionable cognitive form.

**Vibration (`^4`)** — The fourth *Noetic*: the degree to which an Idea resonates with
the Mind — its impression ("struck a chord," "hit hard"). A *self-dual*.

**/verify** — The verification workflow that runs a board's test suite, collects *probe*
readings into an *evidence packet*, and produces the pass/fail record required before a
board advances a rung on the *deployment ladder*.

**Zener (diode)** — A *diode* that conducts in reverse once a defined breakdown voltage
is reached, clamping a signal to that level. CAS analog: a state that reverse-conducts at
a threshold, e.g. `Zener< ^3^P, breakdown=0.8 >` — a hard ceiling that engages only past
the set point.
