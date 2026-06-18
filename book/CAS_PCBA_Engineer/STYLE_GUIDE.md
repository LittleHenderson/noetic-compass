# CAS PCBA Engineer — Authoring Style Guide (Internal)

**This file is the single source of truth for every chapter and appendix of *CAS PCBA Engineer*.**
It is an internal authoring reference, not a chapter of the book. Do not ship it. Every contributor
(human or agent) reads this file and Chapter 1 (`Chapter_01_Why_Build_Cognitive_Circuits.md`) before
writing a single word.

---

## 1. The Book in One Sentence

*CAS PCBA Engineer* teaches a reader with **no electronics and no CAS background** to design, test, and
deploy **Cognitive Circuit Boards (CCBs)** — safety-critical cognitive architectures built from typed CAS
components (CJTs, resistors, capacitors, diodes, filters, feedback loops) the same way an electrical engineer
builds a circuit from a schematic.

The governing thesis (established in Chapter 1): **the circuit analogy is a structural isomorphism, not a
poem.** The same abstract topology — flow, limitation, storage, amplification, one-way conductance, feedback —
appears in two substrates (electrons / typed cognitive states). The formalisms differ (Ohm's Law vs Fisher-Rao
geometry); the *topological role* of each component is identical. Never undercut this with "it's just a
metaphor." It is an engineering discipline.

---

## 2. Voice and Tone (match Chapter 1 exactly)

- **Authoritative, plain, confident.** Short declaratives. The reader is an intelligent adult who knows
  neither electronics nor CAS. Teach both from first principles, in passing, as needed.
- **Lead every chapter with a concrete hook** — a scene, a failure, a vivid contrast — before any notation.
  (Ch.1 opens with a hospital ventilator power supply. Match that energy.)
- **Define every electronic term the first time it appears**, inline: "A transistor is a three-terminal device
  where a small current at one terminal controls a large current between the other two."
- **No academic hedging, no marketing.** Don't say "load-bearing," "leverage," "delve," "tapestry," "in the
  realm of." Don't say "revolutionary" or "game-changing." Engineers writing for engineers.
- **Plain-English first, jargon second.** When you must use a technical term, the sentence around it should
  make it understandable. (Per house rule: talk like a person, not a paper.)
- **Second person ("you will build…")** for instruction; third person for explanation. Same as Ch.1.
- Each chapter is **~2,200–3,600 words**. Substantial, not padded. Chapter 1 is the length/density target.

---

## 3. Canonical CAS Notation — NON-NEGOTIABLE (read twice)

CAS has four orthogonal axes. **Use these names verbatim. They are canonical and authoritative.**

### The 10 Noetics (the structural dynamic — `^0`…`^9`)

| Symbol | Name | One-line meaning |
|---|---|---|
| `^0` | **Idea** | All things in and outside the Mind. |
| `^1` | **Mind** | Awareness that processes, stores, outputs, intakes Ideas. |
| `^2` | **Positive** | An Idea the Mind has an affinity for and is attracted toward. |
| `^3` | **Negative** | An Idea the Mind is adverse to and repelled by. |
| `^4` | **Vibration** | The degree to which an Idea resonates with the Mind; its impression. |
| `^5` | **Female** | A Mind impregnated with an Idea; the Ideas a Mind is composed of (accumulated experience). |
| `^6` | **Male** | An Idea impregnated with another Idea; the Ideas an Idea is composed of (decomposition). |
| `^7` | **Rhythm** | The rate and pattern a Mind is exposed to an Idea; entraining/conditioning it. |
| `^8` | **Above/Cause** | An Idea that triggers a different Idea than itself to come to Mind. |
| `^9` | **Below/Effect** | The Idea brought to Mind by an Above/Cause trigger. |

Involution pairs: `^2`↔`^3`, `^5`↔`^6`, `^8`↔`^9`. Self-duals: `^0`, `^1`, `^4`, `^7`.

### The 4 Processing Domains (where — `P C E O`)
**P** Principled ≻ **C** Cognitive ≻ **E** Evaluative ≻ **O** Operational.
Total order `P ≻ C ≻ E ≻ O`. Domain Descent (causation): P→C→E→O. Feedback path: O→P.

### The 7 Core Drives (why — `F1`…`F7`)
F1 Unity · F2 Wisdom · F3 Vitality · F4 Connection · F5 Agency · F6 Structure · F7 Purpose.
Inversion pairs: F1↔F7, F2↔F6, F3↔F5. F4 self-dual.

### The 4 Registers (how it operates — `T A f E`)
`|T` Transcendent (high-abstraction, purpose-orienting) · `|A` Analytical (explicit, sequential, logical) ·
`|f` Affective (value-laden, feeling-toned) · `|E` Embodied (sensorimotor, concrete, direct).

### State literal grammar
`^Noetic ^Domain _{Drive} |Register` → e.g. `^8^C_{F2}|A` reads
**"Analytical Above/Cause in the Cognitive domain, driven by Wisdom."**
Drive and Register are optional; an unspecified register means register-neutral.

### Operators (v7.7 discipline — get this right)
- `+` **co-presence / association** — states active simultaneously, remain distinct.
- `×` **cross-register integration** — only when it yields a *named emergent result*: `(A × B) = ^n|Ω_name`.
  Same-Noetic multi-register `×` without a named result is INVALID — rewrite as `+` or `|⟨…⟩`.
- `|⟨R1,R2,R3⟩` **register-set specification** — state present in those registers; no interaction claim.
- `->` **directed transition** (over time). `∘` monoid/fractal composition.
- `Θ(Ω) = a·X₁ + b·X₂ → Ω` **recipe** (proportional prerequisites). `Phi< s₁, s₂, s₃ >` **sequence**.

### ANTI-DRIFT WARNINGS — the three errors that keep recurring. Do not make them.
1. **`^3` Negative is VISCERAL aversion, not analytical critique.** "Can't stomach it," "rubs me the wrong
   way." If you mean audit / scrutinize / find-flaws / decompose-and-test, that is **`^6` Male**, not `^3`.
2. **`^8` Above/Cause is ASSOCIATIVE triggering, not deductive reasoning.** "That reminds me," "one thing
   leads to another." Deductive causal analysis is a compound of `^6` Male + `^9` Below/Effect, not `^8`.
3. **`^5` Female is ACCUMULATED EXPERIENCE** (the substrate / bias of a CJT), the "sum of our experiences."
   For an AI: training data + fine-tuning corpus.

> **Naming rule:** Always name a Noetic by its canonical name. You may *describe its function in the circuit*
> ("the pre-amplifier surfaces and broadens the interpretations of the prompt") but you must not *rename* the
> Noetic to its function. `^8` is **Above/Cause**, never "Expansion." `^9` is **Below/Effect**, never
> "Contraction." `^1` is **Mind**, never "Differentiation." `^6` is **Male**, never "Critique." The older
> *Programming in CAS* drafts drifted on these names — **do not copy their glosses.** Chapter 1 of *this* book
> is your notation reference.

---

## 4. The CJT — the book's central component

The **Cognitive Junction Transistor (CJT)** models a cognitive state transition as a transistor.

```
CJT< cause | bias => effect > [β=2.4, sat=0.95, cutoff=0.1, region=active]
```

| Terminal | Transistor | CAS analog |
|---|---|---|
| **C — Cause** | Collector (input) | the Idea entering the Mind — typically an `^8` Above/Cause state |
| **B — Bias** | Base (control) | accumulated substrate: `^5` Female, constitution, Dial settings, Drive config |
| **E — Effect** | Emitter (output) | the Idea produced — typically a `^9` Below/Effect state |
| **β — Gain** | Ic/Ib | how strongly bias amplifies the cause→effect transition |

Parameters: `β` gain (β<1 attenuate, =1 unity, >1 amplify) · `sat` saturation (effect plateau, 0–1) ·
`cutoff` (bias floor below which β≈0) · `region` ∈ {cutoff, active, saturation, breakdown} ·
`gm` transconductance (∂effect/∂bias — framing-sensitivity) · `rπ` input resistance ("stubbornness to bias change").

Operating regions: **Cutoff** (bias below threshold → no effect) · **Active** (linear, Δeffect ≈ β·Δcause) ·
**Saturation** (effect maxed, more cause does nothing) · **Breakdown** (effect flips to involution pair —
`^2`→`^3` under overload). Named form: `let cjt_x = CJT< … => … > [β=…];`

Gain formally: small-signal `β = ‖∂E/∂C‖_FR` at constant bias; large-signal
`β = d_FR(E_after,E_before) / d_FR(C_after,C_before)`, where `d_FR(p,q)=2·arccos(Σ√(pₖqₖ))` is the Fisher-Rao
geodesic distance on the open simplex Δ39°. (Cite this; don't re-derive it in every chapter.)

---

## 5. Component & CCDL syntax cheat-sheet (use these forms consistently)

```cas
Resistor< ^8^C_{F2}|A, R=50 >              // limits activation flow; higher R = more constrained
Capacitor< ^5^E_{F4}|f, C=100, leakage=0.01 >   // stores experience; leakage = forgetting
Inductor< ^7^O_{F6}|E, L=50 >              // resists pattern change; habit inertia
Diode< ^P -> ^C >                          // one-way domain conductance
Zener< ^3^P, breakdown=0.8 >               // reverse-conducts at threshold
Transformer< ^P -> ^C, ratio=0.5 >         // domain impedance match (principle -> actionable)
OpAmp< non_inverting=^8^C_{F2}|A, inverting=^6^E_{F6}|A, output=^9^C_{F2}|A, open_loop_gain=10000 >
Oscillator< Phi< ^8^C|A, ^3^O|E, ^9^E|f, ^0^P|T >, frequency=0.0000116 >
AND< … > OR< … > NOT< … > NAND< … > NOR< … > XOR< … >
MUX< inputs=[…], select=Drive::active >    DEMUX< input=…, outputs=[…], select=… >
Regulator< target_state=^0^E_{F3}|f, tolerance=0.1 >
Fuse< ^8^O_{F5}|E, threshold=0.9, action=permanent_block >
```

**CCDL (Cognitive Circuit Description Language)** — the schematic-as-text format:

```cas
circuit safety_filter {
    input: prompt;
    output: response;

    node expand:          ^8^C_{F2}|A;
    node evaluate:        ^6^E_{F6}|A;
    node respond:         ^9^C_{F2}|A;
    node bias_principles: ^5^P_{F7}|T;

    cjt c1: CJT< prompt   | bias_principles => expand   > [β=2.0];
    cjt c2: CJT< expand   | bias_principles => evaluate > [β=1.5];
    cjt c3: CJT< evaluate | bias_principles => respond  > [β=1.0];

    feedback evaluate -> bias_principles [β=0.3];

    probe tp1: expand;
    probe tp2: evaluate;
}
```

Compiler error codes to reference where relevant: E-CJT-001 MissingBias · E-CJT-002 InvalidBiasDomain ·
E-CJT-003 CjtCutoff · W-CJT-004 CjtSaturation · E-CJT-005 GainDivergence · W-CJT-006 CjtShortCircuit ·
W-CJT-007 CjtCascadeDepth · E-CJT-008 CjtCrossDomainBias.

Status honesty: the CJT/CCDL compiler primitive is a *design* (per the implementation blueprint roadmap),
not yet a shipped compiler pass. Write the book as a design handbook — present CCDL as the language you author
in and the compiler as the tool that validates it — but never claim a build/run result that doesn't exist.
"The compiler will reject this" (a design rule) is fine; "I ran this and got X" is not.

---

## 6. Chapter template (structure every chapter this way)

```
# Chapter N: <Title>

<2–4 paragraph HOOK — a concrete scene/contrast/failure. No notation yet.>

## <Concept section 1>     ← teach the electronic idea from first principles
## <CAS mapping section>   ← the structural isomorphism: same role, cognitive substrate
## <Worked build>          ← a real CCDL/CAS build the reader could author; walk it line by line
   - use a fenced ```cas block
   - "Bench Notes:" callout(s) for practical gotchas (use a > blockquote)
## <Datasheet / parameter table>   ← markdown table of parameters, ranges, meanings
## <Failure modes>         ← what goes wrong, how to detect it (table or list)
## Key Takeaways           ← 4–7 bullet summary
---
## Exercises               ← 3–4 exercises; at least one must be CCDL/CAS the reader writes,
                             with a verifiable answer (answers go in Appendix E)
```

Not every section is mandatory for every chapter, but **hook, worked build, key takeaways, and exercises are
mandatory in every chapter.** Match Chapter 1's use of tables, fenced code, and bolded inline terms.

---

## 7. Formatting conventions (for clean pandoc → PDF rendering)

- One `#` H1 per file: the chapter title. Sections are `##`, subsections `###`.
- CAS code in fenced blocks tagged `cas`. Shell/Python where genuinely needed tagged `bash`/`python`.
- Use Markdown tables liberally (datasheets, mappings, failure modes) — they render beautifully.
- Inline CAS literals in backticks: `` `^3^P_{F7}|T` ``. Escape pipes inside table cells as `\|`.
- Use `> ` blockquotes for **Bench Notes**, warnings, and regulator-facing callouts.
- Use `---` thematic breaks before the Exercises section.
- Bold key terms on first definition. Avoid heavy nesting (max 2 list levels).
- Do **not** add page numbers, headers/footers, or HTML — the LaTeX pipeline handles design.
- Cross-reference other chapters by number and name: "as we built in Chapter 18 (the CSB)…".

---

## 8. The running spine (continuity across the book)

The book's through-line is **building one real artifact: the Cognitive Safety Board (CSB)** — the AI-alignment
firewall fully designed in Chapter 18 and matching SOP-PO-005. Earlier chapters should, where natural, foreshadow
a CSB sub-component ("the resistor you build here is the current-limiter on the CSB's Agency rail in Chapter
18"). Later chapters (testing, debugging, deployment, governance) operate *on* the CSB. This gives the reader
one growing system, not 26 disconnected demos.

Five reference boards (Part IV), refer to them by these exact names/acronyms:
**CSB** Cognitive Safety Board · **COB** Cognitive Oscillator Board · **CDAB** Cognitive Differential Amplifier
Board · **CMB** Cognitive Memory Board · **CPMB** Cognitive Power Management Board.

---

## 9. Hard guardrails

- **Canonical Noetic names only** (§3). This is the #1 review failure. Re-check `^3`, `^8`, `^5`, `^1`, `^6`.
- **No invented benchmark numbers or fake run results.** Parameters in worked examples are *design choices*
  (you may pick β=2.4, sat=0.8 etc.); empirical claims about real models are not.
- **Patent line:** if patent status comes up, USPTO Provisional #64/037,173 is real and valid — never flag it
  as suspect. CJT/PCBA/CCB material is post-filing new matter (don't claim it's covered by the provisional).
- **Substrate neutrality:** "cognitive" means *structural*, not conscious/human. A CJT no more "thinks" than a
  transistor is "electronic-minded." Certification is an engineering claim (the safety CJT saturates at the
  specified threshold), not a claim about values. (Ch.1 "A Note on the Word Cognitive" is the model.)
- **Companion:** *Programming in CAS* is the language reference; *this* book is the circuit-design handbook.
  Cross-sell lightly, don't depend on it — this book stands alone (notation taught in Chapter 2).
