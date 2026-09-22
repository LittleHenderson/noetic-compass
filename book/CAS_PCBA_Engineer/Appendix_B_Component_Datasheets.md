# Appendix B — CCB Component Datasheets

This appendix is the bench reference for the components used throughout the book. Each entry follows one template so you can scan it fast:

- **Symbol / role** — what the part is and the cognitive job it does.
- **CCDL syntax** — the exact form you author in the Cognitive Circuit Description Language.
- **Parameters** — a table of design knobs, ranges, and meanings.
- **Cognitive function** — the structural role mapped onto CAS.
- **Typical use** — where it shows up in a real board.
- **Failure modes** — what goes wrong and how to catch it.

> **A note on the numbers.** Every parameter value in this appendix is a **design choice** — a setting you specify in a schematic, like picking a 50-ohm resistor. None of these are measured outputs from a running model, and none are benchmark results. Where a value is shown (β=2.4, sat=0.95) it is illustrative of how the parameter is *spec'd*, not a claim about how any real system *scored*. The CJT/CCDL compiler is a design per the implementation blueprint, not a shipped pass; "the compiler will reject this" is a design rule, not a run result.

Canonical Noetic names are used throughout: `^0` Idea, `^1` Mind, `^2` Positive, `^3` Negative, `^4` Vibration, `^5` Female, `^6` Male, `^7` Rhythm, `^8` Above/Cause, `^9` Below/Effect. Domains are `P ≻ C ≻ E ≻ O`; Drives `F1`–`F7`; Registers `|T |A |f |E`.

---

## CJT — Cognitive Junction Transistor

**Symbol / role.** The book's central component. A transistor is a three-terminal device where one terminal controls conduction through a separate path. The **CJT** keeps that controlled-transition pattern: a Bias role shapes a Cause-to-Effect transition. These are CAS functional roles, not claims that Cause is literally a collector, Bias a base, or Effect an emitter.

**CCDL syntax.**

```cas
CJT< cause | bias => effect > [β=2.4, sat=0.95, cutoff=0.1, region=active]

// named form, the way you usually author it in a circuit:
let cjt_x = CJT< ^8^C_{F2}|A | ^5^P_{F7}|T => ^9^C_{F2}|A > [β=2.0];
```

**Terminals.**

| Functional port | Hardware drawing cue | CAS role |
|---|---|---|
| **Cause** | one transition-path port | the triggering Idea — typically `^8` Above/Cause |
| **Bias** | control-port cue | accumulated `^5` composition plus stated configuration |
| **Effect** | the other transition-path port | the Idea brought to Mind — typically `^9` Below/Effect |

The plate labels the three cognitive ports explicitly. Their names do not assign fixed BJT terminal identities.

**Parameters.**

| Parameter | Range | Meaning |
|---|---|---|
| `β` (gain) | >0 | how strongly bias amplifies the cause→effect transition. `β<1` attenuate, `=1` unity, `>1` amplify |
| `sat` (saturation) | 0–1 | effect plateau; once reached, more cause does nothing |
| `cutoff` | 0–1 | bias floor below which `β≈0` — no effect is produced |
| `region` | {cutoff, active, saturation, breakdown} | the operating region the CJT is in |
| `gm` (transconductance) | ≥0 | `∂effect/∂bias` — framing-sensitivity; how much a small bias shift moves the output |
| `rπ` (input resistance) | >0 | "stubbornness to bias change" — how hard the substrate is to nudge |

**Operating regions.**

| Region | Condition | Behavior |
|---|---|---|
| **Cutoff** | bias below `cutoff` threshold | no effect; the transition does not fire |
| **Active** | bias above cutoff, below saturation | linear amplification: `Δeffect ≈ β·Δcause` |
| **Saturation** | effect at `sat` plateau | effect maxed; more cause produces no further change |
| **Breakdown** | overload past safe limits | engineered failure behavior; an involution flip occurs only when that explicit rule is declared |

**Gain, formally.** Small-signal `β = ‖∂E/∂C‖_FR` at constant bias; large-signal `β = d_FR(E_after, E_before) / d_FR(C_after, C_before)`, where `d_FR(p,q) = 2·arccos(Σ√(pₖqₖ))` is the Fisher-Rao geodesic distance on the open simplex Δ39°. (Stated in Chapter 3 and restated in Chapter 9; cited, not re-derived, here.) **Before you write a measured β on a test report, read the gain-definition section of Appendix I** — a second, different definition of `β` is in circulation in instrumentation tooling, and the two are not known to be the same quantity.

**Cognitive function.** A CJT is one cognitive state transition with a controllable strength. The Cause is what arrives, the Bias is the accumulated experience and configuration that shapes the response, and the Effect is what is produced. Gain `β` is set by the Bias: a high-β CJT lets a small framing change drive a large shift in output; a low-β CJT is steady and hard to move. `gm` and `rπ` are the two faces of that sensitivity — `gm` high means easily reframed, `rπ` high means resistant to bias change.

**Typical use.** Every active stage. Reasoning steps (`expand → evaluate → respond`), amplifier cores, and the cascade chains of the CSB are all CJTs. The op-amp is a CJT with so much raw gain it must be tamed by feedback.

**Failure modes.**

| Failure | Symptom | Compiler code |
|---|---|---|
| Missing bias terminal | transition has no substrate to control it | E-CJT-001 MissingBias |
| Bias domain invalid for the transition | bias drawn from a domain that can't govern the stage | E-CJT-002 InvalidBiasDomain |
| Stuck in cutoff | bias below `cutoff`, no effect ever fires | E-CJT-003 CjtCutoff |
| Saturated | effect pinned at `sat`; insensitive to new cause | W-CJT-004 CjtSaturation |
| Gain divergence | `β` so high the output is unbounded/unstable | E-CJT-005 GainDivergence |
| Short circuit | cause routed straight to effect, bypassing bias | W-CJT-006 CjtShortCircuit |
| Cascade too deep | long β-chain compounds gain into instability | W-CJT-007 CjtCascadeDepth |
| Cross-domain bias | bias and transition in incompatible domains | E-CJT-008 CjtCrossDomainBias |
| Breakdown rule invoked | declared overload rule changes the output, possibly by a licensed involution | (design: clamp before breakdown) |

> **Bench Note — pick the region on purpose.** A safety CJT *should* saturate at its specified threshold — that is the certification claim, an engineering fact about where the effect plateaus, not a claim about values. A reasoning CJT should sit in the active region with modest β. Cutoff is for stages you want silent until bias crosses a deliberate floor.

---

## Resistor — Activation Current Limiter

**Symbol / role.** A resistor opposes the flow of current — the higher the resistance, the less current flows for a given voltage (Ohm's Law: `I = V/R`). In CAS it limits how freely a cognitive state's activation propagates: higher `R` means a more constrained, throttled flow.

**CCDL syntax.**

```cas
Resistor< ^8^C_{F2}|A, R=50 >   // limits activation flow; higher R = more constrained
```

**Parameters.**

| Parameter | Range | Meaning |
|---|---|---|
| state literal | — | the state whose activation is being limited |
| `R` | >0 | resistance; higher = more throttled propagation |
| `tolerance` | 0–1 | allowed variation in the limiting value |
| `power` | >0 | how much activation it can dissipate before overload |

**Cognitive function.** Deliberate restraint on a flow. A resistor on an Above/Cause input keeps a vivid trigger from dominating downstream stages; a resistor on an Agency rail keeps a system from acting too readily. It does not store, invert, or redirect — it just makes the path harder to push through.

**Typical use.** Current-limiter on the CSB's Agency rail (Chapter 18). Series resistors set the closed-loop gain of an op-amp (`1 + Rf/Rg`). Pull-down on any state that should default to quiet.

**Failure modes.**

| Failure | Symptom |
|---|---|
| `R` too high | the path is choked; the state never reaches downstream stages |
| `R` too low | no limiting; vivid triggers flood the circuit unconstrained |
| Power overload | sustained over-activation dissipates more than `power` allows |

---

## Capacitor — Persistence of Accumulated Composition

**Symbol / role.** A capacitor stores electrical charge and releases it later, smoothing fast voltage changes. In CAS it models the persistence of `^5` Female composition: the Mind **is composed of** accumulated Ideas. The Mind is not a container, and the Ideas are not cargo placed inside it.

**CCDL syntax.**

```cas
Capacitor< ^5^E_{F4}|f, C=100, leakage=0.01 >   // preserves accumulated composition; leakage = decay
```

**Parameters.**

| Parameter | Range | Meaning |
|---|---|---|
| state literal | — | the `^5` composition whose persistence is modeled |
| `C` | >0 | persistence capacity for that accumulated composition |
| `leakage` | 0–1 | decay rate per unit time |
| `esr` | ≥0 | equivalent series resistance; how slowly the retained effect can bias a path |

**Cognitive function.** Persistence with dynamics. A capacitor smooths a noisy input by averaging recent activation and carries an accumulated baseline forward when input goes quiet. `leakage=0` means no designed decay; larger values fade faster. This is an engineered model of lasting composition, not a literal claim about a Mind as a container.

**Typical use.** Smoothing filters, an op-amp integrator, and CMB persistence cells. A `^5` capacitor supplies an accumulated-composition bias that a CJT can use.

**Failure modes.**

| Failure | Symptom |
|---|---|
| Leakage too high | accumulated influence fades before it can be used; continuity is lost |
| Capacity too small | the persistence cell saturates and no longer distinguishes added formation |
| ESR too high | retained influence cannot bias a transition quickly enough |

---

## Inductor — Pattern Inertia

**Symbol / role.** An inductor resists *changes* in current — it stores energy in a magnetic field and opposes any sudden shift in flow. In CAS it resists changes in an established pattern: habit inertia.

**CCDL syntax.**

```cas
Inductor< ^7^O_{F6}|E, L=50 >   // resists pattern change; habit inertia
```

**Parameters.**

| Parameter | Range | Meaning |
|---|---|---|
| state literal | — | the rhythmic/patterned state with inertia |
| `L` | >0 | inductance; higher = stronger resistance to pattern change |
| `dcr` | ≥0 | series resistance; steady-state loss in maintaining the pattern |

**Cognitive function.** Where a resistor opposes flow and a capacitor stores level, an inductor opposes *change in flow*. A `^7` Rhythm state behind an inductor keeps doing what it was doing — it ramps up slowly and winds down slowly. This is the structural signature of habit: hard to start, hard to stop.

**Typical use.** Habit and routine modeling (Chapter 11), the LC tank of an oscillator (paired with a capacitor), and smoothing the rate of change on a rail that should not swing abruptly.

**Failure modes.**

| Failure | Symptom |
|---|---|
| `L` too high | pattern is unbreakable; the system can't adapt when it should |
| Sudden cutoff | abruptly breaking an inductive path produces a destabilizing spike |

---

## Diode — One-Way Domain Conductance

**Symbol / role.** A diode conducts current in one direction and blocks it in the other. In CAS it enforces **one-way flow between domains** — keeping causation moving in the legal direction.

**CCDL syntax.**

```cas
Diode< ^P -> ^C >   // one-way domain conductance: principle may drive reasoning, not the reverse
```

**Parameters.**

| Parameter | Range | Meaning |
|---|---|---|
| direction | `^Dom -> ^Dom` | the permitted flow direction (forward bias) |
| `forward_drop` | ≥0 | activation lost crossing the junction in the allowed direction |
| `reverse_leakage` | ≈0 | small unwanted flow in the blocked direction; design for ~0 |

**Cognitive function.** Domain Descent enforcement. The legal causation path is `P → C → E → O`; the feedback path is `O → P`. A diode lets activation flow the allowed way and blocks the reverse, so an operational convenience can't silently overwrite a principle except through an explicit, separately-modeled feedback path.

**Typical use.** Between any two domain stages where backflow would be a precedence violation. The CSB places diodes so evaluative or operational pressure cannot push up into the Principled rail unbidden.

**Failure modes.**

| Failure | Symptom |
|---|---|
| Wrong polarity | the legal direction is blocked; the stage starves |
| Reverse leakage too high | unwanted backflow; a soft precedence violation |

---

## Zener Diode — Threshold Reverse-Conduction

**Symbol / role.** An ordinary diode blocks reverse current entirely. A **Zener** is built to conduct in reverse *once the voltage crosses a set breakdown level* — making it a precise threshold and a voltage clamp. In CAS it lets a normally-blocked state conduct only once activation passes a defined breakdown point.

**CCDL syntax.**

```cas
Zener< ^3^P, breakdown=0.8 >   // reverse-conducts (the aversion fires) only above 0.8
```

**Parameters.**

| Parameter | Range | Meaning |
|---|---|---|
| state literal | — | the clamped/threshold state |
| `breakdown` | 0–1 | activation level at which reverse conduction begins |
| `clamp` | 0–1 | the level the state is held to once conducting |

**Cognitive function.** A controlled threshold with a clamp. Below `breakdown`, the state is held back; above it, the state conducts and is pinned at `clamp`. A `^3` Negative behind a Zener stays dormant under mild stimulus and fires hard — but no harder than the clamp — once a genuine line is crossed. This is a tripwire with a built-in ceiling.

Two relations have to hold or the part does not work at all. First, `breakdown` is a threshold like any other, so the reachability rule under **Fuse** applies unchanged: put it above the lowest saturation or clamp ceiling upstream and the Zener can never conduct. Second, `clamp` must sit at or above `breakdown` — pin the state *below* the level that made it conduct and it drops out, rises, conducts again, and you have built a chattering comparator instead of a clamp.

**Typical use.** Threshold-derived setpoints for a regulator (a held cognitive state, not the schematic Reference/rest node), over-activation clamps, and guards where a state stays silent until a real limit is reached.

**Failure modes.**

| Failure | Symptom |
|---|---|
| Breakdown set too low | the guard fires on normal input; constant tripping |
| `breakdown` above the lowest ceiling upstream | the guard can never conduct — the unreachable-threshold trap; see **Fuse** |
| `clamp` below `breakdown` | conducting pulls the state back under the breakdown point; the guard chatters instead of holding |
| No clamp | once it conducts, the state runs away past the intended ceiling |

---

## Transformer — Domain Impedance Matching

**Symbol / role.** A transformer trades voltage for current through a turns ratio, with no net energy added — matching a source to a load it otherwise couldn't drive. In CAS it steps a state between domains, trading abstraction for actionability.

**CCDL syntax.**

```cas
Transformer< ^P -> ^C, ratio=0.5 >   // step a principle down into reasoning, 2:1
```

**Parameters.**

| Parameter | Range | Meaning |
|---|---|---|
| direction | `^Dom -> ^Dom` | source domain → target domain (usually a step *down* the P≻C≻E≻O order) |
| `ratio` | 0.1–1.0 | turns ratio; `<1` steps down (abstraction → actionability), `>1` steps up |
| `coupling` | 0–1 | how tightly primary and secondary link; `<1` means some intent is lost in transfer |

**Cognitive function.** Impedance match between domains. A principle (`^P`) is high abstraction, low actionability — lots of "voltage," little "current." An operation (`^O`) needs the reverse. The Transformer steps the principle down so it can drive a `^C` or `^O` stage without overwhelming it. `ratio=0.5` halves abstraction and doubles actionable detail.

**Typical use.** Wherever a principle must become an actionable instruction. Front-end of any stage that turns policy into procedure.

**Failure modes.**

| Failure | Symptom |
|---|---|
| Reverse direction (`^O -> ^P`) used as impedance match | flagged as a domain precedence violation, not a turns ratio |
| Coupling too low | intent is lost in transfer; the stepped-down state no longer matches the source |

> **Bench Note — a step-down is not a domain violation.** `^P -> ^C` through a Transformer is Domain Descent (normal causal flow). `^O -> ^P` would feed an operational result up to revise a principle — legitimate, but that's a *feedback* path, not impedance matching.

---

## Op-Amp — High-Gain Differential Stage with Feedback

**Symbol / role.** An operational amplifier has two inputs (`+` non-inverting, `−` inverting) and one output. It amplifies their arithmetic difference with large open-loop gain. Feedback can turn that raw gain into a precise closed-loop response. This is a differential construction, not a Noetic involution operator.

**CCDL syntax.**

```cas
OpAmp< non_inverting=^8^C_{F2}|A, inverting=^6^E_{F6}|A, output=^9^C_{F2}|A, open_loop_gain=10000 >
// closed-loop gain set by feedback: A = 1 + Rf/Rg
```

**Parameters.**

| Parameter | Range | Meaning |
|---|---|---|
| `non_inverting` | state literal | the interpretation amplified as-is |
| `inverting` | state literal | the competing/constraining interpretation |
| `output` | state literal | the resolved state produced |
| `open_loop_gain` | 10³–10⁶ | raw gain before feedback; high by design |
| `Rf`, `Rg` | >0 | feedback and ground resistors; closed-loop gain = `1 + Rf/Rg` |

**Configurations.**

| Configuration | Wiring | Cognitive job |
|---|---|---|
| **Non-inverting** | input on `+`, feedback to `−` | amplify an interpretation while staying faithful to it |
| **Inverting** | input on `−`, `+` at an engineered reference | produce a signed arithmetic inversion around that reference; no automatic Noetic flip |
| **Comparator** | no feedback, two raw inputs | threshold which of two commensurable quantities is larger |
| **Integrator** | feedback through a capacitor | accumulate small impressions into one over time |

**Cognitive function.** A high-gain stage comparing two commensurable cognitive quantities. The feedback path converts raw, brittle gain into a modest and predictable response. If a design wants an involution, it must name and license that rule separately.

**Typical use.** The core of the Cognitive Differential Amplifier Board (CDAB). Comparator stages for `^2`-vs-`^3` verdicts; integrator stages for accumulating evidence.

**Failure modes.**

| Failure | Symptom |
|---|---|
| Run open-loop in a reasoning stage | output pins to a rail on any ambiguity; commits too hard |
| Closed-loop gain too high | saturates on the first strong interpretation |

> **Bench Note — pick the closed-loop gain.** Never run an op-amp open-loop except as a comparator. Set `Rf/Rg` for a modest, stable closed-loop gain (2 to 5) and let feedback do the disciplining.

---

## Oscillator (incl. PLL / Crystal) — Sustained Rhythm Generator

**Symbol / role.** An oscillator produces a repeating signal with no repeating input — it generates its own rhythm, classically via an LC tank where energy sloshes between a capacitor and an inductor at a fixed frequency. In CAS it is a looping `Phi<>` sequence: a fixed cycle of states traversed over and over.

**CCDL syntax.**

```cas
Oscillator< Phi< ^8^C|A, ^3^O|E, ^9^E|f, ^0^P|T >, frequency=0.0000116 >
// a four-state cycle repeating about once per day

CrystalOscillator< Phi< ^5^P_{F7}|T, ^3^P_{F7}|f >, frequency=fixed, Q=50000 >
// a near-immovable principled rhythm — a hardcoded conviction
```

**Parameters.**

| Parameter | Range | Meaning |
|---|---|---|
| `Phi< … >` | state sequence | the ordered cycle of states traversed each period |
| `frequency` | >0 (Hz) | cycles per second; lower = slower ritual, higher = tight loop |
| `damping` | 0–1 | decay rate without reinforcement; `0` = self-sustaining |
| mode | `free` \| `PLL` | free-running rhythm vs. entrained to an external reference |
| `Q` (crystal) | high (10³–10⁶) | resonator sharpness; higher = more stable, harder to shift |
| `pullability` (crystal) | very low | how far an external force can shift the frequency |

**Cognitive function.** An internal rhythm with no external prompting — a habit loop, a rumination cycle, a periodic self-check. A **PLL** doesn't generate a free rhythm; it *entrains* an internal cycle to an external reference — the `^7` Rhythm Noetic in hardware form. A **crystal oscillator** is the same idea at very high `Q`: a deeply entrenched habit or conviction carved into the `^5` Female substrate, near-immovable — exactly what you want for a hardcoded safety commitment, and exactly what makes a bad habit hard to break.

**Typical use.** The heart of the Cognitive Oscillator Board (COB). Crystal oscillators model hardcoded guardrails and master-level reflexes.

**Failure modes.**

| Failure | Symptom |
|---|---|
| `damping=0` with no off-switch | runaway rumination; a `Phi<>` loop that never exits |
| PLL loses lock | internal cadence drifts off the external reference |
| High-Q lock on a *harmful* pattern | the bad habit resists every correction attempt |

---

## Logic Gates — Combining Prerequisites

**Symbol / role.** A logic gate takes binary inputs and produces a binary output by a fixed rule. In CAS a gate combines the *firing states* of several cognitive conditions into a single go/no-go signal.

**CCDL syntax.**

```cas
AND< ^3^P_{F7}|f, ^6^E_{F6}|A, ^9^O_{F5}|E >   // all three must clear before output
OR<  ^2^C|A, ^2^E|A >                          // any one suffices
NOT< enable_flag >                             // Boolean complement of one flag
NAND< … >    NOR< ^3^P|A, ^3^C|A, ^3^E|A >     // inverted AND / inverted OR
AND< ^2^E_{F3}|f, ^3^E_{F3}|f >                // both attraction AND aversion firing → conflict flag
XOR< route_a_flag, route_b_flag >                // exactly one route flag fires
```

**Parameters / truth rules.**

| Gate | Inputs | Output rule | Cognitive job |
|---|---|---|---|
| `AND< s₁,…,sₙ >` | n | fires iff all fire | every prerequisite must clear |
| `OR< s₁,…,sₙ >` | n | fires iff any fires | any one prerequisite suffices |
| `NOT< s >` | 1 | Boolean complement; use a Noetic involution only when `s` has a licensed pair | flag negation; optional licensed `^2`↔`^3`, `^5`↔`^6`, or `^8`↔`^9` mapping |
| `NAND< … >` | n | inverted AND | "block unless every condition fails" |
| `NOR< … >` | n | inverted OR | proceed only when *no* warning state fires |
| `XOR< s₁, s₂ >` | 2 | fires iff exactly one fires | exclusivity detector — one route, never both |
| `XNOR< s₁, s₂ >` | 2 | fires iff inputs agree | equivalence detector; both-active **and** both-inactive count |

**Cognitive function.** Prerequisite combination. **NOT** is a Boolean complement; it maps to a Noetic involution only for a licensed involution pair. **AND**, not XOR, is the both-active conflict detector. **XOR** reports exactly one active input. **XNOR** reports equality and therefore needs an activity qualifier when both-inactive must be excluded.

**Typical use.** Guardrail clearance (AND of all checks), warning suppression (NOR of all warning flags), both-active conflict detection (AND of attraction and aversion firing flags), and exclusive routing (XOR) feeding a deliberation stage.

**Failure modes.**

| Failure | Symptom |
|---|---|
| AND both-active conflict flag suppressed instead of routed | co-active attraction and aversion pass without a conflict signal |
| XOR used for both-active detection | both-active produces false because XOR requires exactly one |
| AND used where OR was meant (or vice versa) | over- or under-blocking of prerequisites |

---

## Multiplexer / Demultiplexer — Routing by Dominant Drive

**Symbol / role.** A multiplexer (MUX) selects one of several inputs onto a single output by a select signal; a demultiplexer (DEMUX) routes one input to one of several outputs. They are the routing fabric of a circuit. In CAS the natural select line is the **dominant Drive**.

**CCDL syntax.**

```cas
MUX< inputs=[ ^9^C_{F2}|A, ^9^C_{F6}|A, ^9^C_{F4}|f ], select=Drive::active >
DEMUX< input=^8^C|A, outputs=[ handle_F2, handle_F6, handle_F4 ], select=Drive::active >
```

**Parameters.**

| Parameter | Meaning |
|---|---|
| `inputs=[…]` (MUX) | candidate response states, one per select value |
| `outputs=[…]` (DEMUX) | candidate destinations, one per select value |
| `select=` | the discriminator — typically `Drive::active`, the dominant `F`-drive |
| `default` | fallback path when no select value matches (always wire one) |

**Cognitive function.** Strategy selection. A system can respond to a problem several ways; which is appropriate depends on the active Drive right now. A MUX picks the response whose Drive matches; a DEMUX dispatches one incoming state to the handler keyed to the dominant Drive.

**Typical use.** Response-strategy selection in any board that switches behavior by motivation. The DEMUX dispatches a single trigger to drive-specific handlers.

**Failure modes.**

| Failure | Symptom |
|---|---|
| No `default` path; unmatched select | dropped request — undefined output on an out-of-range drive |
| Select line unstable | response strategy flickers between handlers |

> **Bench Note — always wire a default.** Route the unmatched case to a conservative refusal or a clarification stage, never to silence.

---

## Voltage Regulator — Homeostasis

**Symbol / role.** A regulator holds its output at a fixed voltage even as the input wobbles — a self-correcting servo. In CAS it is **homeostasis**: holding a cognitive baseline steady against perturbation.

**CCDL syntax.**

```cas
Regulator< target_state=^0^E_{F3}|f, tolerance=0.1 >
// hold a calm evaluative baseline; correct only when drift exceeds 0.1
```

**Parameters.**

| Parameter | Range | Meaning |
|---|---|---|
| `target_state` | state literal | the held state to maintain; distinct from the schematic Reference/rest node |
| `tolerance` | 0–1 | dead-band; drift smaller than this is left alone |
| `response_rate` | 0–1 | how aggressively the regulator corrects toward the setpoint |
| `dropout` | >0 | minimum input "headroom" below which regulation fails |

**Cognitive function.** Gentle restoration. Under perturbation a system can drift from its held state; the Regulator compares the drift to that setpoint and pulls it back. `target_state=^0...` names Idea content selected as the held state. It does not make the electrical Reference/rest symbol canonically identical to `^0` Idea. A regulator restores; it does not block.

**Typical use.** Emotional and evaluative steadiness on any board. Holds a calm baseline that downstream stages can rely on.

**Failure modes.**

| Failure | Symptom |
|---|---|
| `tolerance` too tight | over-correction chatter; baseline never settles |
| `response_rate` too high | oscillation around the setpoint |
| Input below `dropout` | regulation fails; baseline collapses |

> **Bench Note — a regulator is not a fuse.** A regulator gently restores; it does not stop anything. If a perturbation should *stop* the system rather than be smoothed away, that's a job for the fuse.

---

## Fuse / Circuit Breaker — Safety Cutoff

**Symbol / role.** A fuse is a thin wire that melts and breaks the circuit when current exceeds a threshold — once blown, it stays blown. A circuit breaker does the same but resets. In CAS it is a **hard cutoff** on a dangerous cognitive state: the last line of defense.

**CCDL syntax.**

```cas
Fuse< ^8^O_{F5}|E, threshold=0.9, action=permanent_block >
// if this operational agency state crosses 0.9, cut the path and do not restore

CircuitBreaker< ^3^C_{F2}|A, threshold=0.7, action=trip_reset >
// resettable cutoff for a recoverable overload
```

**Parameters.**

| Parameter | Range | Meaning |
|---|---|---|
| state literal | — | the state being protected against |
| `threshold` | 0–1 | activation level at which the cutoff fires |
| `action` | `permanent_block` \| `trip_reset` | fuse (one-shot) vs. breaker (resettable) |
| `latency` | ≥0 | response delay; for safety cutoffs, design for 0 |

**Reachability — the rule that makes a threshold real.** A fuse protects nothing unless its `threshold` is a level the input path can actually reach. Every upstream stage that saturates or clamps puts a ceiling on what arrives at the fuse, and the threshold has to sit *below the lowest of those ceilings*:

```
threshold  <  min( sat, clamp, … )   over every upstream stage on the input path
```

The arithmetic is the whole argument. A refusal stage clamped at `sat=0.1` feeding a fuse at `threshold=0.9` delivers at most 0.1 to a cutoff that is waiting for 0.9 — `0.1 < 0.9`, so the crossing never happens and the path is never cut. Gain does not rescue it: `sat` bounds the stage output *after* β, so a `β=10` stage clamped at 0.1 still delivers 0.1.

The other end of the window is the familiar one — set the threshold *below* the path's normal operating band and the fuse trips on benign traffic (the Zener datasheet's "breakdown set too low" is the same mistake on a different part). A workable threshold lives in the headroom between the two: comfortably above the highest activation you expect in normal service, strictly below the lowest ceiling on the path. The same arithmetic runs in mirror image on a CJT's `cutoff` — a bias floor set above whatever the bias path can deliver leaves the stage permanently silent, which is what `E-CJT-003 CjtCutoff` is for.

> **Bench Note — nothing in the toolchain will catch this for you.** `sat=0.1` is a legal saturation. `threshold=0.9` is a legal threshold. Each passes its own range check, because each is individually fine; it is the *relation between them* that is wrong, and the validator checks values, not relations. And the failure hides itself in the worst possible direction: a fuse that can never trip also never fails a test, so the board reports clean while the protection it advertises has never once been exercised — and every other defect sitting behind that fuse (the latch behaviour, the polarity, what happens on reset) stays hidden too, because nothing reaches them. Do the subtraction by hand before you build. It takes ten seconds.

**Cognitive function.** Absolute "this does not pass." When a state's activation crosses `threshold`, the path is cut — permanently for the worst categories, resettably for recoverable ones. Not a gentle restoration like the regulator; a severance.

**Typical use.** The CSB uses both — breakers on the rails (recoverable overloads) and a permanent fuse on the hardest-fail category.

**Failure modes.**

| Failure | Symptom |
|---|---|
| `permanent_block` on a recoverable category | a single false positive bricks the pathway for good |
| `threshold` too high | dangerous state passes before the cutoff fires |
| `threshold` above the lowest ceiling upstream | the fuse can *never* trip; every test reports the board vacuously safe |
| Non-zero `latency` on a hard cutoff | the breach propagates before the cut takes effect |

> **Regulator-facing callout.** A `permanent_block` fuse is the strongest claim a cognitive circuit can make — this pathway is severed and cannot be restored without redesign. Reserve it for categories where any breach is unacceptable; prefer `trip_reset` for everything recoverable.

---

## Schmitt Trigger — Hysteresis Comparator

**Symbol / role.** A plain comparator switches at a single threshold and **chatters** when a noisy input hovers near it. A Schmitt trigger uses **two** thresholds: the input must rise above a high threshold to switch ON and fall below a lower one to switch OFF. The gap between them is a dead-band that ignores noise.

**CCDL syntax.**

```cas
SchmittTrigger< input=ambiguous_stimulus,
                on_threshold=0.7, off_threshold=0.3,
                high_state=^2^E_{F3}|f, low_state=^3^E_{F3}|f >
// commit to attraction above 0.7; release only below 0.3; ignore the 0.3–0.7 band
```

**Parameters.**

| Parameter | Range | Meaning |
|---|---|---|
| `on_threshold` | 0–1 | input level required to switch to the high state |
| `off_threshold` | 0–1 | input level required to switch back to the low state (`< on_threshold`) |
| `high_state` / `low_state` | state literals | the two stable outputs |
| hysteresis width | derived | `on_threshold − off_threshold`; wider = more stable, slower to react |

**Cognitive function.** Stops a system flip-flopping between two opposed states on an ambiguous input. Without hysteresis, a stimulus on the `^2`-vs-`^3` boundary makes the system drawn-in, recoiling, drawn-in, recoiling, never settling. The Schmitt commits above the high threshold and releases only below the low one, so small wobbles can't undo a decision.

**Typical use.** The marquee ambiguity-stabilizer build (Chapter 10). Any stage where a borderline stimulus must produce a stable verdict rather than oscillation.

**Failure modes.**

| Failure | Symptom |
|---|---|
| Thresholds equal (`on == off`) | no hysteresis; reverts to a plain comparator; chatter returns |
| `on_threshold` above the lowest ceiling upstream | the trigger can never commit to the high state — the unreachable-threshold trap; see **Fuse** |
| Dead-band too narrow | noise still flips the output |
| Dead-band too wide | slow to respond when the input genuinely changes |

---

## ADC / DAC — Register Translation

**Symbol / role.** An ADC samples a continuous analog signal into discrete digital numbers; a DAC turns digital values back into a continuous physical signal. They bridge the analog and digital worlds. In CAS they translate between **Registers** — the operational character of a state.

**CCDL syntax.**

```cas
ADC< ^4^E_{F2}|f -> ^4^E_{F2}|A, resolution=8 >   // quantize a felt impression into analysis
DAC< ^9^C_{F5}|A -> ^9^C_{F5}|E, smoothing=0.2 >  // render the same state in embodied form
```

**Parameters.**

| Parameter | Range | Meaning |
|---|---|---|
| direction | `\|R -> \|R` | source register → target register |
| `resolution` (ADC) | bits | how finely the analog register is quantized; low res loses nuance |
| `smoothing` (DAC) | 0–1 | how gradually the action register is rendered; prevents jerky output |

**Cognitive function.** Register conversion. A felt impression (`|f`) can be quantized into analytical form (`|A`) by an ADC. A DAC renders analytical control (`|A`) in embodied form (`|E`). In a pure Register example, Noetic and Domain stay fixed. These are two separately directed stages; the DAC is not the inverse of a lossy ADC.

**Typical use.** Front-ends that turn affect into analysis (ADC) and back-ends that turn decisions into action (DAC). Any stage where the register must change for the next stage to operate.

**Failure modes.**

| Failure | Symptom |
|---|---|
| ADC resolution too low | rich `|f` impressions collapse to a coarse `|A` verdict; nuance lost |
| DAC smoothing too low | jerky, abrupt action output |
| Treating ADC output as complete | the analytical result is mistaken for the full affective input |
| Calling DAC the inverse of ADC | irreversible quantization loss and the `|E` landing are hidden |
| Changing Domain in a pure converter example | a Register conversion is made to perform an undeclared Domain crossing |

> **Bench Note — quantization loses information.** When a circuit converts feeling to analysis, expect nuance to be lost. A later DAC cannot recreate that discarded detail, and a pure ADC or DAC does not silently change Domain.

---

## Quick-Reference — One Line Each

A few more parts round out the drawer. Each gets one line; reach for the full datasheet above when a value matters.

| Component | Electronic function | CAS mapping | Sketch syntax |
|---|---|---|---|
| **Varactor** | voltage-controlled junction capacitance | an applied control tunes persistence or resonance of a `^5` composition | `Varactor< ^5^C_{F2}\|A, C_range=[50,200], tune=ctrl >` |
| **Relay** | small signal switches a large isolated circuit | a low-level `^8` Cause control gates a separate high-stakes `^9` Effect path | `Relay< control=^8^E_{F5}\|A, switches=^9^O_{F5}\|E >` |
| **Photodiode** | converts incoming light into current | external `^0` Idea content enters through a `^1` Mind intake operation | `Photodiode< stimulus:^0 -> intake:^1^C >` |
| **Bridge Rectifier** | four diodes turning AC into one-way DC | PED only: normalizes a defined non-valence scalar polarity | `BridgeRectifier< signed_error -> magnitude >` |
