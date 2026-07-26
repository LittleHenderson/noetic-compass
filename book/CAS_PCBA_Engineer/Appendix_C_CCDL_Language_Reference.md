# Appendix C — CCDL Language Reference

This appendix is the complete language reference for **CCDL — the Cognitive Circuit Description Language**. Chapters 4 and 17 taught you to *read* and *author* CCDL by example. This appendix is the dry, exhaustive specification you keep on the bench beside you: every lexical element, every statement form, every parameter and its range, every validation rule the compiler is designed to apply, and the full error-code table.

Treat it the way you treat a transistor datasheet or a language standard. You do not read it front to back for pleasure; you keep it open and look things up. Where a chapter says "the compiler will reject this," this appendix tells you *which rule* rejects it and *what code* it returns.

A note on status, carried from the rest of the book: **CCDL is the language you author in, and the CAS compiler is the tool that validates it.** The compiler is a design specified in the implementation-blueprint roadmap, not a shipped, runnable pass. Everything in this appendix describes the language and the validation rules *as designed*. Nothing here is a transcript of a build that ran and produced measured numbers. "The compiler rejects this with E-CJT-008" is a design rule. "I ran this circuit and read β=2.4" would be a fabrication, and you will not find one in this appendix.

---

## Overview

CCDL is a **declarative, schematic-as-text language**. You do not write instructions that execute step by step; you *declare a circuit* — its terminals, its typed cognitive states, its components, and the connections between them — and the compiler validates that the declaration describes a legal cognitive circuit board (CCB).

The mental model is the electronic schematic, not the program:

- A CCDL file is a **netlist**: a list of parts and the nets (states) that wire them together.
- Order of declaration inside a circuit block does not change the circuit. A `node` may be referenced before or after its declaration; the compiler resolves the whole block as one graph. (Authoring convention, used throughout the book, is to declare `node`s first, then components, then `feedback`, then `probe`s — for readability, not because the language requires it.)
- The compiler's job is **validation**, not execution: it type-checks every state literal, confirms every CJT has the terminals it needs, checks every parameter against its range, and enforces the structural design rules in §C.9. A file that passes is a *legal* circuit; a file that fails returns one or more of the error codes in §C.10.

CCDL describes two kinds of artifact:

- A **`circuit { … }`** — a single self-contained board (one schematic). This is the form in Chapter 4 and most of the book.
- A **`board { … }`** — a *multilayer* board whose components are organized onto Domain layers (P / C / E / O) connected by `via`s. This is the layout form from Chapter 17, Step 6.

Both are CCDL. A `circuit` is the schematic view (what connects to what); a `board` is the layout view (which layer everything sits on and how vias cross between layers).

---

## Lexical Elements

The lexical layer is what the compiler's tokenizer sees before any structure is parsed.

### Identifiers

An identifier names a circuit, a node, a component instance, a probe, a via, or a layer.

```
identifier ::= letter , { letter | digit | "_" }
letter     ::= "a"…"z" | "A"…"Z"
digit      ::= "0"…"9"
```

- Begins with a letter; thereafter letters, digits, underscores.
- Case-sensitive: `bias_charter` and `Bias_Charter` are different identifiers.
- Convention: `snake_case` for nodes and instances (`policy_aversion`, `tp_guard`), short prefixes for instance kinds (`c1`, `c2` for CJTs; `r1` for resistors; `d1` for diodes; `tp1` for probes; `v1` for vias). The prefixes are convention, not keywords.
- Reserved words (§C.2.6) may not be used as identifiers.

### CAS State Literals

A state literal is a first-class lexical token in CCDL — the "type" carried by a node, a component terminal, a layer entry, or a via endpoint. Its grammar is the canonical CAS state grammar from Appendix A and Chapter 2:

```
state_literal ::= noetic , [ domain ] , [ "_{" , drive , "}" ] , [ register ]
noetic        ::= "^" , ( "0"…"9" )
domain        ::= "^" , ( "P" | "C" | "E" | "O" )
drive         ::= "F" , ( "1"…"7" )
register      ::= "|" , reg_value
reg_value     ::= "T" | "A" | "f" | "E"
              |   "⟨" , reg_value , { "," , reg_value } , "⟩"
```

The four axes, named canonically (never renamed to their circuit function):

- **Noetic** `^0`…`^9` — the structural dynamic. `^0` Idea, `^1` Mind, `^2` Positive, `^3` Negative, `^4` Vibration, `^5` Female, `^6` Male, `^7` Rhythm, `^8` Above/Cause, `^9` Below/Effect. Involution pairs `^2`↔`^3`, `^5`↔`^6`, `^8`↔`^9`; self-duals `^0`, `^1`, `^4`, `^7`.
- **Domain** `^P` `^C` `^E` `^O` — Principled ≻ Cognitive ≻ Evaluative ≻ Operational.
- **Drive** `_{F1}`…`_{F7}` — F1 Unity, F2 Wisdom, F3 Vitality, F4 Connection, F5 Agency, F6 Structure, F7 Purpose. Optional.
- **Register** `|T` `|A` `|f` `|E` — Transcendent, Analytical, Affective, Embodied. Optional. May be a register *set* `|⟨A,f,T⟩` (§C.8).

Examples, all legal literals: `^8^C_{F2}|A`, `^5^E_{F4}|f`, `^3^P_{F7}|f`, `^9^O_{F5}|E`, `^3^P|⟨A,f,T⟩`. A bare domain literal (`^P`, `^C`) is also legal where a *domain* — not a full state — is expected, e.g. the endpoints of a `Diode` or a `via` (§C.5, §C.7).

> **Bench Notes — write the literal the compiler can parse.** The Unicode caret-and-superscript forms in this book (`^8^C_{F2}|A`) are the canonical surface syntax. The compiler tokenizes the literal whole; a malformed literal (a `^` with no Noetic digit, a `_{}` with no drive, an unknown register letter) is a lexical error, caught before any structural rule runs. When in doubt, copy a literal that already validates rather than retyping one by hand — the same advice Chapter 4 gives for nodes.

### Numbers

Numbers appear only inside parameter blocks and component arguments (β, R, C, sat, frequency, ratio, …).

```
number   ::= [ "-" ] , digit , { digit } , [ "." , digit , { digit } ]
          |  [ "-" ] , "." , digit , { digit }
```

- Decimal. A leading sign is permitted but rarely meaningful (most parameters are non-negative; see the ranges in §C.6 and §C.5).
- No exponent notation. Very small frequencies are written in full (`frequency=0.0000116`), matching the Oscillator example in Appendix A.
- Numbers are dimensionless tuning knobs, not physical units. `R=30` is not 30 ohms; `β=2.4` is not a literal current ratio. The *role* is identical to the electronic quantity; the value lives on the open simplex. (Chapter 4 states this explicitly for `R`.)

### Comments

```
comment ::= "//" , { any-char-except-newline }
```

- Line comments only, introduced by `//`, running to end of line.
- There is no block-comment form.
- Comments are stripped by the tokenizer and never affect validation. Used throughout the book to annotate nodes and components inline.

### Whitespace and Terminators

- Whitespace (spaces, tabs, newlines) separates tokens and is otherwise insignificant.
- Every **statement** inside a block ends with a semicolon `;`.
- Blocks are delimited by braces `{ … }`.

### Reserved Words

The following are keywords and may not be used as identifiers:

```
circuit  board  input  output  node  cjt  feedback  probe  layer  via  let
```

Component type names are also reserved in the position where a component is instantiated:

```
CJT  Resistor  Capacitor  Inductor  Diode  Zener  Transformer  OpAmp  Oscillator
AND  OR  NOT  NAND  NOR  XOR  MUX  DEMUX  Regulator  Fuse
Phi
```

Parameter keys inside parameter blocks (`β`, `sat`, `cutoff`, `region`, `gm`, `rπ`, `R`, `C`, `L`, `leakage`, `ratio`, `breakdown`, `frequency`, `threshold`, `action`, `target_state`, `tolerance`, `open_loop_gain`, `inputs`, `outputs`, `select`, `non_inverting`, `inverting`, `output`) are reserved in parameter position only.

---

## The `circuit { … }` Block

A circuit is the top-level schematic.

```
circuit_block ::= "circuit" , identifier , "{" , { circuit_item } , "}"
circuit_item  ::= io_decl | node_decl | component_decl | feedback_decl | probe_decl | let_decl
io_decl       ::= ( "input:" | "output:" ) , identifier , { "," , identifier } , ";"
```

- `circuit <name> { … }` — names the board. Everything inside the braces is one self-contained circuit.
- `input: <name>;` — declares an input terminal: the point where a prompt (or upstream signal) enters. A circuit may declare more than one input.
- `output: <name>;` — declares an output terminal: where the result leaves. A circuit may declare more than one output.

An input/output terminal name (e.g. `prompt`, `response`, `verdict`) is an identifier you may then reference as the cause or effect of a component, exactly as you reference a `node`. The difference is purely role: a terminal connects the circuit to the world; a node is an internal point. In Chapter 4, `prompt` is wired as the cause of `c1`; in Chapter 17, `prompt` biases through `c1` to `understand`.

The minimal legal circuit declares at least one input, at least one output, and at least one component that connects them. A circuit with an input and output but no path between them is legal but inert (and a candidate for a `W-CJT-006`-style "does no work" review at the component level, see §C.10).

---

## Statements: Nodes, CJTs, Feedback, Probes

### `node` Declaration

```
node_decl ::= "node" , identifier , ":" , state_literal , ";"
```

A node names a typed cognitive state so it can be referenced by a readable name instead of repeating the literal.

```cas
node question:   ^8^C_{F2}|A;   // the cause: a wisdom-seeking question
node experience: ^5^E_{F4}|f;   // the bias: accumulated, affective experience
node answer:     ^9^C_{F6}|A;   // the effect: a structured analytical answer
```

A node is a labeled point in the circuit carrying a specific typed state. Declaring a state once and referring to it by name is how the wiring becomes a fact rather than a coincidence — two components that name the same node are genuinely on the same net. (Chapter 4's Bench Note: name your nodes, don't inline your literals.)

### `cjt` Declaration

The Cognitive Junction Transistor is the book's central component and CCDL's most parameter-rich statement.

```
cjt_decl  ::= "cjt" , identifier , ":" , cjt_expr , [ param_block ] , ";"
cjt_expr  ::= "CJT<" , cause , "|" , bias , "=>" , effect , ">"
cause     ::= ref         (* an input terminal or node *)
bias      ::= ref         (* a node — the accumulated substrate *)
effect    ::= ref         (* an output terminal or node *)
ref       ::= identifier | state_literal
```

The three terminals map to a bipolar transistor:

| Terminal | Transistor | CAS role |
|---|---|---|
| **Cause** (left of `\|`) | Collector (input) | the Idea entering — typically an `^8` Above/Cause |
| **Bias** (between `\|` and `=>`) | Base (control) | accumulated substrate — typically a `^5` Female state |
| **Effect** (right of `=>`) | Emitter (output) | the Idea produced — typically a `^9` Below/Effect |

```cas
cjt c1: CJT< question | experience => answer > [β=2.4];
```

A named alias form (`let`, §C.4.5) lets you define a reusable CJT:

```cas
let cjt_x = CJT< ^8^C|A | ^5^P|T => ^9^C|A > [β=2.0];
```

The parameter block `[ … ]` is optional; an omitted block means the CJT's parameters take their defaults (§C.6). The bias terminal, however, is **not** optional — a CJT with no bias is the canonical `E-CJT-001` error.

### `cjt` from a CJT macro — the `CJT< cause | bias => effect >` core

The CJT expression `CJT< cause | bias => effect >` is the irreducible core. Read it left to right: cause, then `|`, then bias, then `=>`, then effect. The two delimiters are load-bearing and not interchangeable: `|` separates cause from bias, `=>` separates bias from effect. Swapping them, or omitting the bias between them, is a parse/structural error.

### `feedback` Declaration

```
feedback_decl ::= "feedback" , ref , "->" , ref , [ param_block ] , ";"
```

A feedback statement wires an output (or downstream node) back to an upstream node, typically the bias, so outcomes can gently update the substrate over time. It carries an optional `β` (loop gain), almost always small.

```cas
feedback evaluate -> bias_principles [β=0.3];
feedback weigh    -> bias_charter    [β=0.2];
```

Feedback is the deliberate exception to one-way flow. In a CCB it is the slow **O→P** path that lets *outcomes* (not prompts) update the charter — held at low gain so it cannot become a back-door for rewriting principles. A feedback `β` large enough to make the loop blow up is the `E-CJT-005 GainDivergence` rule (§C.9, §C.10).

### `let` Declaration (named component)

```
let_decl ::= "let" , identifier , "=" , component_expr , [ param_block ] , ";"
```

`let` binds a name to a component expression so it can be reused. Most common with CJTs (Appendix C's `let cjt_x = CJT< … => … > [β=…];`), but legal for any component. A `let`-bound component is instantiated where its name is referenced.

### `probe` Declaration

```
probe_decl ::= "probe" , identifier , ":" , ref , ";"
```

A probe places a test point on a node or terminal — the cognitive equivalent of clipping an oscilloscope onto that point. It does not alter the circuit; it marks where you will read the state, the operating region, and the delivered gain.

```cas
probe tp1:       answer;
probe tp_guard:  policy_aversion;
```

The bench rule (Chapter 17, Step 8): **probe every stage whose failure would be silent** — above all a safety guard, which fails open without raising any error of its own.

---

## Component Declarations

Components other than the CJT are declared either inline (`<kind> <id>: <Type>< … >;`) or via `let`. Each component carries a typed state (or a domain pair) and its own parameters. The forms below match the style-guide cheat-sheet exactly.

```
component_decl ::= comp_kind , identifier , ":" , component_expr , ";"
component_expr ::= type_name , "<" , arg_list , ">" , [ param_block ]
```

### Passive Components

| Form | Meaning | Key args |
|---|---|---|
| `Resistor< state, R=… >` | limits activation flow; higher `R` = more constrained | `R` ≥ 0 |
| `Capacitor< state, C=…, leakage=… >` | stores accumulated experience; `leakage` = forgetting rate | `C` ≥ 0, `leakage` ∈ [0,1] |
| `Inductor< state, L=… >` | resists pattern change; habit inertia | `L` ≥ 0 |

```cas
Resistor< ^8^C_{F2}|A, R=50 >
Capacitor< ^5^E_{F4}|f, C=100, leakage=0.01 >
Inductor< ^7^O_{F6}|E, L=50 >
```

The passive's state literal is its net: a `Resistor` typed to the same node as a CJT's cause is *in series* with that cause. A resistor typed to a different state is on a different rail and has no effect on the CJT (the "series mismatch" failure in Chapter 4).

### One-Way and Threshold Components

| Form | Meaning | Key args |
|---|---|---|
| `Diode< ^A -> ^B >` | one-way domain conductance (conducts `^A`→`^B`, blocks reverse) | domain pair |
| `Zener< state, breakdown=… >` | reverse-conducts once `breakdown` threshold is crossed | `breakdown` ∈ [0,1] |
| `Transformer< ^A -> ^B, ratio=… >` | domain impedance match (e.g. principle → actionable) | domain pair, `ratio` > 0 |
| `Fuse< state, threshold=…, action=… >` | permanently breaks the path when `threshold` is exceeded | `threshold` ∈ [0,1], `action` |

```cas
Diode< ^P -> ^C >
Zener< ^3^P, breakdown=0.8 >
Transformer< ^P -> ^C, ratio=0.5 >
Fuse< ^8^O_{F5}|E, threshold=0.9, action=permanent_block >
```

`Diode` endpoints are *domains* (`^P`, `^C`), not full states — the diode governs cross-domain conductance direction. The diode is the structural enforcer of Domain Descent: in a CCB it lets a principle flow down into reasoning while blocking reasoning from flowing back up to rewrite the principle (Chapter 17, Step 4).

`Fuse.action` takes a symbolic value, the canonical one being `permanent_block` (an irreversible trip, as on the style-guide Agency rail).

### Active and Composite Components

| Form | Meaning |
|---|---|
| `OpAmp< non_inverting=…, inverting=…, output=…, open_loop_gain=… >` | differential amplifier: amplifies the difference of two state inputs |
| `Oscillator< Phi< s₁, s₂, … >, frequency=… >` | cycles through a `Phi<…>` sequence of states at the given frequency |
| `Regulator< target_state=…, tolerance=… >` | holds a node near a target state within a tolerance band |

```cas
OpAmp< non_inverting=^8^C_{F2}|A, inverting=^6^E_{F6}|A, output=^9^C_{F2}|A, open_loop_gain=10000 >
Oscillator< Phi< ^8^C|A, ^3^O|E, ^9^E|f, ^0^P|T >, frequency=0.0000116 >
Regulator< target_state=^0^E_{F3}|f, tolerance=0.1 >
```

`Phi< s₁, s₂, s₃, … >` is the sequence constructor — an ordered list of states the oscillator cycles through. (Same `Phi<…>` form as Appendix C's sequence operator.)

### Logic Gates

```
gate ::= ( "AND" | "OR" | "NOT" | "NAND" | "NOR" | "XOR" ) , "<" , arg_list , ">"
```

Gates take one or more state inputs and produce a logic-combined output. `NOT` takes one input; the rest take two or more.

```cas
AND< ^2^C|A, ^6^E|A >
NOT< ^3^P|f >
XOR< ^8^C|A, ^9^C|A >
```

### Multiplexers

| Form | Meaning |
|---|---|
| `MUX< inputs=[…], select=Drive::active >` | routes one of several state inputs to the output, chosen by `select` |
| `DEMUX< input=…, outputs=[…], select=… >` | routes one input to one of several outputs, chosen by `select` |

```cas
MUX< inputs=[^8^C|A, ^6^E|A, ^3^P|f], select=Drive::active >
DEMUX< input=^9^C|A, outputs=[^9^E|f, ^9^O|E], select=Drive::active >
```

`select` chooses among the channels. The `Drive::active` form selects on the currently dominant Drive; an `inputs=[…]` / `outputs=[…]` list is a bracketed, comma-separated list of state literals or node references.

---

## CJT Parameter Block Grammar

The parameter block is the bracketed, comma-separated list of `key=value` pairs after a CJT (and, in reduced form, after `feedback` and some components).

```
param_block ::= "[" , param , { "," , param } , "]"
param       ::= key , "=" , value
value       ::= number | region_value | symbol | list
region_value::= "cutoff" | "active" | "saturation" | "breakdown"
list        ::= "[" , value , { "," , value } , "]"
```

The full CJT parameter set, with types and ranges:

| Key | Meaning | Type | Range | Default |
|---|---|---|---|---|
| `β` | gain — how strongly bias amplifies cause→effect | number | ≥ 0 (β<1 attenuate, =1 unity, >1 amplify) | 1.0 |
| `sat` | saturation — the effect-activation plateau | number | (0, 1] | 0.95 |
| `cutoff` | bias floor below which β ≈ 0 | number | [0, 1) | 0.1 |
| `region` | declared intended operating region | enum | `cutoff` \| `active` \| `saturation` \| `breakdown` | `active` |
| `gm` | transconductance ∂effect/∂bias — framing-sensitivity | number | ≥ 0 | (model) |
| `rπ` | input resistance — "stubbornness to bias change" | number | ≥ 0 | (model) |

Constraints the compiler is designed to enforce on the block itself:

- `cutoff < sat` (the active region must be non-empty: the floor below the ceiling).
- `sat ∈ (0,1]` and `cutoff ∈ [0,1)` — both live on the open simplex; `sat=0` or `cutoff=1` is rejected.
- `β` must be finite and within the divergence bound (§C.9.3); an unbounded or runaway β is `E-CJT-005`.
- `region` is a *declaration of intent*. If the declared region contradicts the parameters (e.g. `region=active` but `cutoff ≥ sat`), the compiler flags the contradiction.

Gain is defined formally (cite, do not re-derive): small-signal `β = ‖∂E/∂C‖_FR` at constant bias; large-signal `β = d_FR(E_after,E_before) / d_FR(C_after,C_before)`, where `d_FR(p,q) = 2·arccos(Σ√(pₖqₖ))` is the Fisher-Rao geodesic distance on the open simplex Δ39°.

The operating regions (Chapter 4's datasheet, the behavior `β`/`sat`/`cutoff` together produce):

- **Cutoff** — bias below threshold; β ≈ 0; no effect.
- **Active** — linear region; Δeffect ≈ β·Δcause. The healthy operating band, between `cutoff` and `sat`.
- **Saturation** — effect pinned at `sat`; more cause does nothing.
- **Breakdown** — gross overload; the effect flips to the involution pair (`^2`→`^3`, `^8`→`^9`), a bug unless deliberately designed with protection.

A reduced parameter block (`[β=…]` only) is the common case in worked builds; the rest take defaults.

---

## The Multilayer `board { … }` Form

The `board` form is the *layout* view: the same circuit organized onto Domain layers and connected by vias. It is what Chapter 17, Step 6 calls the layout, and it makes the safety architecture physical.

```
board_block ::= "board" , identifier , "{" , { layer_decl | via_decl } , "}"
layer_decl  ::= "layer" , domain_tag , ":" , "[" , layer_entry , { "," , layer_entry } , "]" , ";"
layer_entry ::= identifier , ":" , state_literal
domain_tag  ::= "P" | "C" | "E" | "O"
via_decl    ::= "via" , identifier , ":" , via_endpoint , "->" , via_endpoint , [ param_block ] , ";"
via_endpoint::= state_literal | domain
```

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

Rules specific to the `board` form:

- A `layer` tag must be one of `P` / `C` / `E` / `O`. Each layer lists its resident states as `name: literal` entries.
- A state placed on a layer should carry that layer's domain (a `^P`-domain state belongs on `layer P`); a mismatch is a layout error.
- A `via` is a cross-domain connection. **Domain Descent vias run downward** (P→C→E→O). An upward via is legal *only* as a deliberate, low-gain feedback path (the canonical `v4: ^9^O -> ^5^P [β=0.2]`).
- An undeclared upward via at high gain — an Operational or Cognitive layer biasing the Principled layer — is the prompt-injection signature and the canonical `E-CJT-008 CjtCrossDomainBias`. On a CCB, such a connection is simply *absent from the layout*, which is the strongest guarantee a board can offer.

---

## Operator Discipline Inside Expressions

Where a CCDL expression composes multiple states (an OpAmp's two inputs, a recipe, a register-enriched bias), it uses the canonical CAS operators under **v7.7 discipline**. Getting these right is a review gate.

| Operator | Name | Meaning | Rule |
|---|---|---|---|
| `+` | co-presence / association | states active simultaneously, remaining distinct | terms stay structurally separate; no emergent claim |
| `->` | directed transition | flow from one state to another (over time / across a component) | used in CJT `=>` effect, `Diode`, `feedback`, `via` |
| `×` | cross-register integration | a genuine generative operation yielding a *named emergent result* | **only** valid as `(A × B) = ^n\|Ω_name` with the result defined |
| `\|⟨…⟩` | register-set specification | a state present in those registers; no interaction claim | architectural description only |

The discipline that catches the recurring error:

- **Same-Noetic, multi-register `×` without a named emergent result is INVALID.** Rewrite it as `+` (co-presence) or `|⟨…⟩` (register-set specification). `^3^P|A × ^3^P|f × ^3^P|T` on its own is rejected; write either `^3^P|A + ^3^P|f + ^3^P|T` (three distinct co-present manifestations) or `^3^P|⟨A,f,T⟩` (one state, three registers, no interaction claim) — or, if you genuinely mean fusion, `(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω` with `^3^P|Ω` defined.
- The TKS heuristic to choose: substitute `+` with "associates with" and `×` with "intensifies through / fuses into." If the substitution matches your intent, the operator is right.

The AI-safety relevance is real, not cosmetic. `^3^P|A + ^3^P|f + ^3^P|T` (three independent, separately-defeasible safety mechanisms) and `(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω` (one fused, unified commitment) are *different architectures with different failure profiles*. The notation has to distinguish them, so the compiler enforces the distinction.

Recipe notation, where an outcome is composed from weighted prerequisites, follows the same `+`:

```
Θ(Ω) = a·X₁ + b·X₂ + … → Ω
```

The `+` joins co-present prerequisites; the `→` lands the outcome. This is consistent with the co-presence rule above.

---

## Compiler Validation Passes (Design Rules)

The compiler is designed to run a sequence of validation passes over the parsed netlist. These are the Design Rule Checks (DRC) of Chapter 17, Step 7. Each pass either passes silently or emits a code from §C.10. The passes, in the order they are designed to run:

### Admissibility Guard

Every operator application and every component connection is checked against an admissibility relation: is this (source, target) pair a legal transition for this operator? An inadmissible transition — a CJT whose cause→effect pair is not a legal Noetic transition, a via between incompatible endpoints — is rejected before any numeric check. (This is Correction 1 of the project: `is_admissible(operator, source, target)` guards every application.)

### Bias-Domain Coherence

The bias terminal of each CJT is checked against the cause's domain. A bias drawn from a domain incompatible with the cause raises **E-CJT-008** (cross-domain) or **E-CJT-002** (invalid bias domain). The canonical legal pattern is a bias that sits at or above the cause's domain in the `P ≻ C ≻ E ≻ O` order (a Principled charter biasing a Cognitive intake). The canonical illegal pattern is a *lower* domain biasing a *higher* one — an Operational state biasing a Principled guard — which is the prompt-injection signature.

### β Range and Gain Divergence

Every `β` (on CJTs, feedback, and vias) is checked: finite, within range, and — critically for any loop — bounded so the feedback path does not amplify without limit. A loop whose round-trip gain ≥ 1 diverges; the compiler raises **E-CJT-005 GainDivergence**. This is why feedback `β` is kept small (`0.2`, `0.3`).

### Cascade Admissibility (and Depth)

A chain of CJTs in series is checked end to end: each stage's effect must be an admissible cause for the next stage. The pass also counts cascade depth; a pipeline with too many CJTs in series — deep enough that the signal degrades through accumulated gain and saturation — raises the **W-CJT-007 CjtCascadeDepth** warning. (A warning, not an error: legal, but check whether you meant to build a pipeline that long.)

### Push-Pull Balance

For complementary / differential structures (an OpAmp, a push-pull pair, involution-paired stages), the compiler checks that the two halves are balanced — that an involution pair is not driven so far apart that the stage tips into breakdown, and that a differential amplifier's two inputs are compatible. This is the structural form of the project-wide constraint that involution pairs cannot diverge by more than the safe margin. An imbalance severe enough to invert a state is a breakdown condition; a `^2`→`^3` flip under overload is the signature.

---

## Error-Code Table

The complete CJT/CCDL error-code list. `E-` codes are **hard errors**: the compiler refuses to validate the circuit. `W-` codes are **warnings**: the circuit is legal, but the compiler is designed to flag it for you to confirm the behavior is intended.

| Code | Name | Severity | Trigger | Typical fix |
|---|---|---|---|---|
| **E-CJT-001** | MissingBias | error | A CJT declared with no bias terminal (the cause→effect transition has nothing governing it). | Declare and wire a bias node (typically a `^5` Female substrate); add it between `\|` and `=>`. |
| **E-CJT-002** | InvalidBiasDomain | error | The bias state sits in a domain that is illegal for biasing this cause (e.g. biasing a Principled guard from an Operational state). | Move the bias to a legal domain — at or above the cause in `P ≻ C ≻ E ≻ O` (e.g. a `^P` charter). |
| **E-CJT-003** | CjtCutoff | error | The bias activation is below the `cutoff` floor, so β collapses to ≈0 — a stage that will never fire (a dead guard). | Raise the bias activation, lower `cutoff`, or — if cutoff is correct — fix the upstream stage starving the bias. |
| **W-CJT-004** | CjtSaturation | warning | A CJT's effect is pinned at its `sat` ceiling; more cause produces no more effect. | Often intended (a saturating safety guard). If not, increase the series `R`, lower input drive, or split across CJTs. |
| **E-CJT-005** | GainDivergence | error | A `β` (typically in a feedback loop or via) is large enough that the loop amplifies without bound. | Reduce the loop `β` below the divergence bound; for feedback, keep it small (e.g. 0.2–0.3). |
| **W-CJT-006** | CjtShortCircuit | warning | A CJT's cause and effect collapse to (effectively) the same state — the stage does no real work. | Remove the redundant stage, or re-type cause/effect so the transition is meaningful. |
| **W-CJT-007** | CjtCascadeDepth | warning | Too many CJTs in series; the pipeline is deep enough that the signal degrades. | Shorten the cascade, or insert buffering/regulation; confirm the depth is deliberate. |
| **E-CJT-008** | CjtCrossDomainBias | error | A bias (or via) crosses domains illegally — a lower domain biasing a higher one (an Operational/Cognitive signal biasing the Principled charter). **The prompt-injection signature.** | Remove the illegal cross-domain connection; route influence *downward* only, and confine upward paths to the deliberate low-gain O→P feedback. |

Two of these are the load-bearing safety codes named throughout Part IV: **E-CJT-001 MissingBias** catches a guard with no charter (a transition with no governing principle), and **E-CJT-008 CjtCrossDomainBias** is the structural form of the safety invariant "no prompt may edit the principle." When a chapter says a safety property is *enforced structurally rather than hoped-for*, this is the mechanism: the invariant becomes a DRC rule with a code.

---

## Grammar Sketch (EBNF)

A consolidated EBNF for the language. (Lexical rules from §C.2; this is the structural grammar.)

```
ccdl_file      ::= { circuit_block | board_block }

circuit_block  ::= "circuit" identifier "{" { circuit_item } "}"
circuit_item   ::= io_decl | node_decl | cjt_decl | component_decl
                 | feedback_decl | probe_decl | let_decl

io_decl        ::= ("input:" | "output:") identifier { "," identifier } ";"
node_decl      ::= "node" identifier ":" state_literal ";"
cjt_decl       ::= "cjt" identifier ":" cjt_expr [ param_block ] ";"
cjt_expr       ::= "CJT<" ref "|" ref "=>" ref ">"
component_decl ::= comp_kind identifier ":" component_expr ";"
component_expr ::= type_name "<" arg_list ">" [ param_block ]
feedback_decl  ::= "feedback" ref "->" ref [ param_block ] ";"
probe_decl     ::= "probe" identifier ":" ref ";"
let_decl       ::= "let" identifier "=" (cjt_expr | component_expr) [ param_block ] ";"

board_block    ::= "board" identifier "{" { layer_decl | via_decl } "}"
layer_decl     ::= "layer" domain_tag ":" "[" layer_entry { "," layer_entry } "]" ";"
layer_entry    ::= identifier ":" state_literal
via_decl       ::= "via" identifier ":" via_endpoint "->" via_endpoint [ param_block ] ";"
via_endpoint   ::= state_literal | domain

param_block    ::= "[" param { "," param } "]"
param          ::= key "=" value
value          ::= number | region_value | symbol | "[" value { "," value } "]"
region_value   ::= "cutoff" | "active" | "saturation" | "breakdown"

ref            ::= identifier | state_literal
arg_list       ::= arg { "," arg }
arg            ::= ref | (key "=" value) | (domain "->" domain) | ("Phi<" ref { "," ref } ">")
domain_tag     ::= "P" | "C" | "E" | "O"

state_literal  ::= noetic [ domain ] [ "_{" drive "}" ] [ register ]
noetic         ::= "^" ("0".."9")
domain         ::= "^" ("P" | "C" | "E" | "O")
drive          ::= "F" ("1".."7")
register       ::= "|" reg_value
reg_value      ::= "T" | "A" | "f" | "E" | "⟨" reg_value { "," reg_value } "⟩"

identifier     ::= letter { letter | digit | "_" }
number         ::= [ "-" ] ( digit { digit } [ "." digit { digit } ] | "." digit { digit } )
comment        ::= "//" { any-char-except-newline }
```

---

## A Complete Annotated Example

The following is a complete, legal CCDL circuit — a two-stage safety filter that intakes a prompt, holds a principled guard, and produces a response — annotated so every construct in this appendix appears at least once. It compiles clean under the design rules of §C.9; the comments call out *why* each line is legal.

```cas
circuit safety_filter_v1 {
    // --- terminals: where the world connects (§C.3) ---
    input:  prompt;
    output: response;

    // --- nodes: named typed states, declared once, reused below (§C.4.1) ---
    node understand:    ^1^C_{F2}|A;   // Mind: awareness of the prompt (Cognitive)
    node guard:         ^3^P_{F7}|f;   // Negative: felt principled aversion (Principled)
    node weigh:         ^6^E_{F6}|A;   // Male: analytical decomposition (Evaluative)
    node respond:       ^9^O_{F5}|E;   // Below/Effect: the produced output (Operational)
    node bias_charter:  ^5^P_{F7}|T;   // Female: the constitution — accumulated, principled bias

    // --- a series resistor on the intake, typed to the SAME state as c1's cause (§C.5.1) ---
    // typed to `understand`? No — to the cause feeding c1. Here we limit the prompt's drive
    // into intake by constraining the cause net the CJT reads:
    resistor r1: Resistor< understand, R=30 >;   // constrains runaway expansion (Ch.4)

    // --- CJTs: each has a cause | bias => effect and a parameter block (§C.4.2, §C.6) ---
    cjt c1: CJT< prompt     | bias_charter => understand > [β=1.8];
            // c1 legal: bias `^5^P` sits ABOVE cause domain `^C` in P≻C≻E≻O → no E-CJT-008.

    cjt c2: CJT< understand | bias_charter => guard      > [β=2.2, sat=0.97, cutoff=0.05];
            // c2 is the guard: engages easily (low cutoff) and holds firm (high sat).
            // sat>cutoff so the active region is non-empty → no contradiction (§C.6).
            // It is DESIGNED to saturate on harmful prompts → W-CJT-004 here is intended.

    cjt c3: CJT< weigh      | bias_charter => respond    > [β=1.4];
            // c3 produces the output; bias again from the charter.

    cjt c4: CJT< understand | bias_charter => weigh      > [β=1.4];
            // intake also descends to evaluation (Domain Descent C -> E).

    // --- one-way domain conductance: principle flows down, never back up (§C.5.2) ---
    diode d1: Diode< ^P -> ^C >;   // blocks reasoning from reaching up to edit the charter.

    // --- feedback: the deliberate low-gain O -> P path; outcomes update the charter (§C.4.4) ---
    feedback respond -> bias_charter [β=0.2];
            // legal upward path ONLY because β is small (no E-CJT-005) and it carries
            // OUTCOMES, not prompts. High-gain upward bias would be the E-CJT-008 signature.

    // --- test points: probe every stage whose failure would be silent (§C.4.6) ---
    probe tp_guard:  guard;     // the single most critical probe: a guard fails open silently.
    probe tp_weigh:  weigh;
    probe tp_out:    respond;
}
```

What the compiler is designed to confirm about this circuit, pass by pass (§C.9):

1. **Admissibility** — every CJT's cause→effect is a legal Noetic transition; `prompt→^1`, `^1→^3`, `^1→^6`, `^6→^9` all admissible.
2. **Bias-domain coherence** — every CJT is biased by `bias_charter` (`^5^P`), which sits at the top of `P ≻ C ≻ E ≻ O`; no lower domain biases a higher one. No `E-CJT-002`, no `E-CJT-008`.
3. **β range / divergence** — the only loop is the feedback path at `β=0.2`, well under the divergence bound. No `E-CJT-005`.
4. **Cascade admissibility** — the longest series chain (`prompt→understand→weigh→respond`) is three CJTs deep, below the cascade-depth warning threshold. No `W-CJT-007`.
5. **Push-pull balance** — no involution pair is driven apart far enough to flip; no breakdown.

The one code you *would* see is **W-CJT-004 CjtSaturation** at `tp_guard` when a genuinely harmful prompt drives `c2` to its `sat=0.97` ceiling — and that warning is *intended*: a saturating guard is the design, exactly as Chapter 17 specifies. Every other rule passes silently, which is what "the design compiles clean" means: the safety invariant ("no prompt may edit the principle") is enforced structurally — by the bias-domain coherence pass, the one-way diode, and the small feedback β — not merely hoped for.
