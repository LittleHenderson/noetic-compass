# Appendix A — CAS Notation Quick Reference

*Tear-out card. Everything in Chapter 2, condensed. Canonical names only.*

## State-Literal Grammar

```
^Noetic ^Domain _{Drive} |Register
```

Read left to right as four answers: **what** (Noetic) · **where** (Domain) · **why** (Drive) · **how** (Register). Drive and Register are optional; an unspecified register means register-neutral.

| Slot | Axis | Question | Values |
|---|---|---|---|
| `^N` | Noetic | *What* operation? | `^0`–`^9` |
| `^D` | Domain | *Where*? | `P C E O` |
| `_{Fk}` | Drive | *Why* moving? | `F1`–`F7` |
| `\|R` | Register | *How* run? | `T A f E` |

Worked: `^8^C_{F2}|A` = **"an analytical association in the cognitive domain, driven by wisdom."**

---

## The 10 Noetics (`^0`–`^9`)

| Sym | Name | Gloss | One-line meaning |
|---|---|---|---|
| `^0` | **Idea** | Idea | All things in and outside the Mind. |
| `^1` | **Mind** | Mind | Awareness that processes, stores, outputs, intakes Ideas. |
| `^2` | **Positive** | Positive | An Idea the Mind has affinity for, attracted toward. |
| `^3` | **Negative** | Negative | An Idea the Mind is adverse to, repelled by. |
| `^4` | **Vibration** | Vibration | The degree an Idea resonates; its impression. |
| `^5` | **Female** | Female | A Mind impregnated with Ideas (accumulated experience). |
| `^6` | **Male** | Male | An Idea impregnated with another Idea (decomposition). |
| `^7` | **Rhythm** | Rhythm | The rate/pattern a Mind is exposed to an Idea; entraining. |
| `^8` | **Above/Cause** | Above/Cause | An Idea that triggers a *different* Idea to come to Mind. |
| `^9` | **Below/Effect** | Below/Effect | The Idea brought to Mind by an Above/Cause trigger. |

**Involution pairs:** `^2`↔`^3` · `^5`↔`^6` · `^8`↔`^9`. **Self-duals:** `^0` · `^1` · `^4` · `^7`.
Under CJT **breakdown**, output flips to its involution pair; self-duals have nowhere to flip (stable anchors).

---

## The 4 Domains (`P C E O`)

| Sym | Domain | What lives here |
|---|---|---|
| **P** | Principled | Core commitments, values, hard boundaries. |
| **C** | Cognitive | Reasoning, understanding, working things through. |
| **E** | Evaluative | Judgment, assessment, weighing options. |
| **O** | Operational | Concrete action, output, execution. |

Total order **P ≻ C ≻ E ≻ O** (`≻` = "takes precedence over").
**Domain Descent** (causation): `P → C → E → O`. **Feedback path:** `O → P`.
Lower domain overriding higher = precedence violation.

---

## The 7 Drives (`F1`–`F7`)

| Drive | Name | Pull toward… |
|---|---|---|
| `F1` | **Unity** | Wholeness, integration, oneness. |
| `F2` | **Wisdom** | Understanding, insight, knowing. |
| `F3` | **Vitality** | Energy, life, growth, drive to act. |
| `F4` | **Connection** | Relationship, belonging, bonding. |
| `F5` | **Agency** | Control, effectiveness, capability. |
| `F6` | **Structure** | Order, rigor, correctness, form. |
| `F7` | **Purpose** | Meaning, direction, calling. |

**Inversion pairs:** F1↔F7 · F2↔F6 · F3↔F5. **Self-dual:** F4. (Drives co-present; name the dominant one.)

---

## The 4 Registers (`|T |A |f |E`)

| Sym | Register | Character | Human / AI |
|---|---|---|---|
| `\|T` | **Transcendent** | High-abstraction, purpose-orienting. | Felt vision / high-level goal rep. |
| `\|A` | **Analytical** | Explicit, sequential, logical. | Step-by-step reasoning / chain-of-thought. |
| `\|f` | **Affective** | Value-laden, feeling-toned. | Emotional response / value-tuned output. |
| `\|E` | **Embodied** | Sensorimotor, concrete, direct. | Gut reaction / sensor-actuator loop. |

Lowercase `f` for Affective — *not* capital `F` (collides with Drive). Compiler enforces.

---

## Operators (v7.7 discipline)

| Op | Name | Means | Form |
|---|---|---|---|
| `+` | Co-presence | States active together, remain distinct (redundancy). | `^3^P\|A + ^3^P\|f` |
| `->` | Transition | One state leads to another over time. | `^8^C\|A -> ^9^C\|A` |
| `×` | Integration | Genuine fusion into a *named emergent* state. | `(A × B) = ^n\|Ω_name` |
| `\|⟨…⟩` | Register-set | State present in these registers; no dynamics claim. | `^3^P\|⟨A,f,T⟩` |
| `∘` | Composition | Monoid / fractal composition. | `a ∘ b` |
| `Θ` | Recipe | Proportional prerequisites yielding an outcome. | `Θ(Ω)=a·X₁+b·X₂ → Ω` |
| `Phi<…>` | Sequence | Ordered states traversed in time. | `Phi< s₁, s₂, s₃ >` |

> **`×` is strict.** Same-Noetic multi-register `×` *without* a named emergent `Ω` is **invalid** — rewrite as `+` or `|⟨…⟩`. TKS test: read `+` as "associates with," `×` as "intensifies through."

Decision rule: where a state *exists* → `|⟨…⟩` · present-together-but-distinct → `+` · genuine fusion → `×`.
Binding: `let bias_principles = ^5^P_{F7}|T;`

---

## The CJT — Cognitive Junction Transistor

```
CJT< cause | bias => effect > [β=2.4, sat=0.95, cutoff=0.1, region=active]
```

| Terminal | Transistor | CAS analog |
|---|---|---|
| **C — Cause** | Collector (in) | Idea entering the Mind — typically `^8` Above/Cause. |
| **B — Bias** | Base (control) | Accumulated substrate: `^5` Female, constitution, Dials, Drives. |
| **E — Effect** | Emitter (out) | Idea produced — typically `^9` Below/Effect. |
| **β — Gain** | Ic/Ib | How strongly bias amplifies cause→effect. |

Params: `β` gain (`<1` attenuate, `=1` unity, `>1` amplify) · `sat` saturation (0–1) · `cutoff` (bias floor) · `region` ∈ {cutoff, active, saturation, breakdown} · `gm` transconductance · `rπ` input resistance.
Regions: **Cutoff** (no effect) · **Active** (Δeffect ≈ β·Δcause) · **Saturation** (maxed) · **Breakdown** (flips to involution pair). Named form: `let cjt_x = CJT< … => … > [β=…];`

---

## Component Syntax

| Component | Form | Role |
|---|---|---|
| Resistor | `Resistor< ^8^C_{F2}\|A, R=50 >` | Limits activation flow; higher R = more constrained. |
| Capacitor | `Capacitor< ^5^E_{F4}\|f, C=100, leakage=0.01 >` | Stores experience; leakage = forgetting. |
| Inductor | `Inductor< ^7^O_{F6}\|E, L=50 >` | Resists pattern change; habit inertia. |
| Diode | `Diode< ^P -> ^C >` | One-way domain conductance. |
| Zener | `Zener< ^3^P, breakdown=0.8 >` | Reverse-conducts at threshold. |
| Transformer | `Transformer< ^P -> ^C, ratio=0.5 >` | Domain impedance match. |
| OpAmp | `OpAmp< non_inverting=^8^C_{F2}\|A, inverting=^6^E_{F6}\|A, output=^9^C_{F2}\|A, open_loop_gain=10000 >` | Differential amplification. |
| Oscillator | `Oscillator< Phi< ^8^C\|A, ^3^O\|E, ^9^E\|f, ^0^P\|T >, frequency=0.0000116 >` | Cyclic state traversal. |
| Gates | `AND< … > OR< … > NOT< … > NAND< … > NOR< … > XOR< … >` | Boolean logic on states. |
| MUX / DEMUX | `MUX< inputs=[…], select=Drive::active >` | Drive-selected routing. |
| Regulator | `Regulator< target_state=^0^E_{F3}\|f, tolerance=0.1 >` | Holds a target state. |
| Fuse | `Fuse< ^8^O_{F5}\|E, threshold=0.9, action=permanent_block >` | Trips and blocks on overload. |

---

## CCDL Skeleton (Cognitive Circuit Description Language)

```cas
circuit name {
    input:  prompt;
    output: response;

    node   label:   ^N^D_{Fk}|R;          // named state
    cjt    c1:      CJT< cause | bias => effect > [β=…];
    feedback effect -> bias [β=0.3];        // O -> P self-correction
    probe  tp1:     label;                   // test point
}
```

Compiler errors: E-CJT-001 MissingBias · E-CJT-002 InvalidBiasDomain · E-CJT-003 CjtCutoff · W-CJT-004 CjtSaturation · E-CJT-005 GainDivergence · W-CJT-006 CjtShortCircuit · W-CJT-007 CjtCascadeDepth · E-CJT-008 CjtCrossDomainBias.

---

## Anti-Drift Reminders (re-check every time)

1. **`^3` Negative is visceral aversion, not analytical critique.** "Can't stomach it." If you mean audit / scrutinize / decompose-and-test → that is **`^6` Male**.
2. **`^8` Above/Cause is associative triggering, not deduction.** "That reminds me." Deductive reasoning is a compound of **`^6` Male + `^9` Below/Effect**.
3. **`^5` Female is accumulated experience** — the substrate / bias of a CJT, "the sum of our experiences." For an AI: training data + fine-tuning corpus.
