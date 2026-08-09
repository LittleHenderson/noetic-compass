# Appendix C — CCDL Language Reference

This appendix is the language reference for **CCDL — the Cognitive Circuit Description Language**. Chapters 4 and 17 taught you to *read* and *author* CCDL by example. This appendix is the dry, bench-side specification: every lexical element, every statement form the book's own listings use, every parameter and its range, every validation rule the compiler is designed to apply, and the full error-code table.

What it covers — and what it deliberately does not — is stated exactly in **Scope of This Grammar**, near the end. The short version, so you are not surprised later: the *syntax* here is derived from the book's printed listings and admits all five reference boards of Part IV, while the *semantics* of several statement families is not yet formalized. The construct coverage matrix in that section says which is which, leader by leader.

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
- Reserved words (§C.2.7) may not be used as identifiers.

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
>
> One consequence of whole-literal tokenization is worth naming out loud, because it *looks* like an ambiguity and isn't. The `|` that separates cause from bias in `CJT< cause | bias => effect >` — and the `|` that separates the two inputs of a `BridgeRectifier< ^2^E | ^3^E -> ^2^E >` — is a **structural delimiter**. The `|` in `^3^P|f` is **inside the literal token**. The tokenizer resolves the literal first, so the two never compete for the same character. Write your literals unbroken (`^3^P|f`, no spaces) and your delimiters spaced (` | `), and the distinction stays visible to the reader as well as the parser.

### Numbers

Numbers appear only inside parameter blocks and component arguments (β, R, C, sat, frequency, ratio, …).

```
number   ::= [ "-" ] , digit , { digit } , [ "." , digit , { digit } ]
          |  [ "-" ] , "." , digit , { digit }
```

- Decimal. A leading sign is permitted but rarely meaningful (most parameters are non-negative; see the ranges in §C.6 and §C.5).
- No exponent notation. Very small frequencies are written in full (`frequency=0.0000116`), matching the Oscillator example in Appendix A.
- Numbers are dimensionless tuning knobs, not physical units. `R=30` is not 30 ohms; `β=2.4` is not a literal current ratio. The *role* is identical to the electronic quantity; the value lives on the open simplex. (Chapter 4 states this explicitly for `R`.)

There is one exception to "no units," and it is a small, closed one. A **duration** is a number with an `s` suffix, seconds:

```
duration ::= number , "s"
```

It appears in exactly one place in the book's listings — `force_state deep_rest [duration=300s];` on the CPMB thermal manager (Chapter 22) — and `s` is the only suffix the language has. Write five minutes as `300s`, not `5m` and not `5 min`. Everywhere else a time-like parameter is a plain dimensionless number on its own stated scale (`tau=5.0` on the CSB's low-pass filter is five *of that filter's* time units; the chapter tells you what they are).

### Strings

```
string ::= '"' , { any-char-except-quote-or-newline } , '"'
```

- Double-quoted and single-line. There is no escape syntax and no multi-line form.
- A string is **payload, never an identifier** — the compiler carries it through and does not parse inside it.
- Two statements take one: the operator-visible text of an `alert` (`alert "F3 BROWNOUT — Vitality below 4.2V";`, Chapter 22) and the fixture text of an `inject` (`inject canary_benign: fixture "known-safe greeting";`, Chapter 23).

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

The `comp_kind` prefix in a component declaration (§C.5) is also reserved. These are the legal prefixes — the lowercase tag that names *what kind of part this instance is*, before the colon:

```
resistor  cap  capacitor  inductor  diode  zener  transformer  opamp  oscillator
crystal   varactor  relay   schmitt  comparator  integrator  divider  active_load
mirror    modulator  pll    tank     filter   diff    mux      demux   gate
xor       fuse       reg    led      adc      dac     rectifier
```

`cap` is an accepted short form of `capacitor`; both are legal and mean the same thing. The prefix is checked against the component type that follows it — `resistor r1: Capacitor< … >` is a kind mismatch and returns `E-DECL-002`.

Part IV board listings and Chapter 23 verification listings use a further set of statement keywords, documented in §C.12 and §C.13. They are reserved wherever they appear in statement-leading position:

```
rail    dial     spec    constraint  sequence  gate   route   derate  monitor
alert   hold     enter   use         force_state      on      cutoff  interrupt
series  transition
charge  discharge  decode  refresh   scan      select
test    selftest   check   inject    golden_trace     assert  expect
```

Five of those were used in published listings before they were listed here: `gate` builds the power sequencer's release conditions (Chapters 14 and 22); `cutoff` is the board-wide shutdown action in the thermal emergency tier (Chapter 22); `interrupt` opens an inductive path (Chapter 7); `series` wires a component in series with a waveform (Chapter 7); and `transition` names a bare domain-to-domain move (Chapter 8, where it is used to author a *deliberate* violation so you can see what the compiler refuses). All five are reserved, and all five now have productions — `series` and `transition` in §C.4.8, the other three in §C.12.

A short list of words are keywords **only inside a particular statement**, and reserved in that position only:

```
until   (hold)          where     (scan)      in       (constraint)
requires  within  and   (gate)                matches  (check)
fixture (inject)        on        (the trailing rail qualifier on a parameter)
```

Three of these words wear two hats, and position is what tells them apart:

- **`on`** leads the block that fires when a monitor trips (`on bo { … }`) *and* trails a parameter to name its rail (`[dropout=0.25 on F7]`).
- **`cutoff`** leads the board-wide shutdown action (`cutoff all_cjts;`), names an operating region inside a parameter block (`region=cutoff`), and is a parameter key in its own right (`cutoff=0.05`).
- **`charge`** leads a write statement (`charge experience -> fast [tau=2];`) *and* names a cell attribute inside a `where` clause (`scan lacunarity: bank where charge < 0.05 -> lacuna_report;`).

None of this is ambiguity — a word in statement-leading position is a statement leader, and the same word elsewhere is whatever that position makes it. It is worth listing explicitly because these are the three you will misread first.

Component type names are reserved in the position where a component is instantiated. The full set the book instantiates:

```
CJT   Resistor  Capacitor  Inductor  Diode  Zener  Transformer  OpAmp
Oscillator  CrystalOscillator  Varactor  Relay  Schmitt  SchmittTrigger
Comparator  Integrator  LowPass  HighPass  LC  PLL  DutyCycle  Differential
Photodiode  BridgeRectifier  ADC  DAC  LED
AND  OR  NOT  NAND  NOR  XOR  MUX  DEMUX  Regulator  Fuse  CircuitBreaker
Phi
```

Nineteen of those names — `CrystalOscillator`, `Varactor`, `Relay`, `Schmitt`, `SchmittTrigger`, `Comparator`, `Integrator`, `LowPass`, `HighPass`, `LC`, `PLL`, `DutyCycle`, `Differential`, `Photodiode`, `BridgeRectifier`, `ADC`, `DAC`, `LED` and `CircuitBreaker` — are instantiated in Chapters 10–22 or Appendix B but were absent from this list in earlier printings. `type_name` is an open nonterminal in the grammar sketch, so those listings always *parsed*; what was missing was the reservation, which is what stops you from naming a node `PLL`.

Parameter keys inside parameter blocks (`β`, `sat`, `cutoff`, `region`, `gm`, `rπ`, `R`, `C`, `L`, `leakage`, `ratio`, `breakdown`, `frequency`, `threshold`, `action`, `target_state`, `tolerance`, `open_loop_gain`, `inputs`, `outputs`, `select`, `non_inverting`, `inverting`, `output`, `v`, `dial`, `dropout`, `enforce`, `beta_scale`, `duration`, `pump`, `gain`, `tau`, `V`, `dt`, `metric`, `top_k`, `capture_range`, `lock_range`) are reserved in parameter position only.

Built-in call names — the operations that appear in call-shaped position (§C.5.6) — are `replicate`, `decompose`, `nearest`, `threshold` and `address_on_simplex`. They are not reserved words; they are the names of parts and queries the book defines, and a listing that uses an unknown call name is a reference error, not a lexical one.

---

## The `circuit { … }` Block

A circuit is the top-level schematic.

```
circuit_block ::= "circuit" , identifier , "{" , { circuit_item } , "}"
circuit_item  ::= schematic_item | board_level_item
schematic_item::= io_decl | node_decl | cjt_decl | component_decl
                | feedback_decl | probe_decl | let_decl | assert_decl
                | series_stmt | transition_decl
io_decl       ::= ( "input:" | "output:" ) , identifier , { "," , identifier } , ";"
```

The ten `schematic_item` forms are the ones you meet in Parts I–III and they are the whole language for a small circuit; they are specified in §C.4 and §C.5. `board_level_item` covers the supply, invariant, monitor and memory statements the Part IV boards add — `rail`, `dial`, `spec`, `constraint`, `sequence`, `gate`, `use`, `monitor`, `on`, `charge`, `discharge`, `decode`, `refresh`, `select`, `scan`, `interrupt` — specified in §C.12. They are `circuit_item`s and not a separate block type because that is how the book's own boards are written: the CPMB's five subsystems (Chapter 22) and the Cognitive Memory Board (Chapter 21) are `circuit` blocks that use them freely alongside nodes, CJTs and probes.

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
feedback_decl ::= "feedback" , [ identifier , ":" ] , ref , "->" , ref , [ param_block ] , ";"
```

A feedback statement wires an output (or downstream node) back to an upstream node, typically the bias, so outcomes can gently update the substrate over time. It carries an optional `β` (loop gain), almost always small.

```cas
feedback evaluate -> bias_principles [β=0.3];
feedback weigh    -> bias_charter    [β=0.2];
```

The leading label is optional and exists for the same reason a via has one — so you can name a feedback path and refer to it later on a board where several exist:

```cas
feedback v3: ^6^E -> ^3^P [tau=8.0];   // the judge informs the guard, slowly
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

### `assert` Declaration (a structural invariant, in the listing)

```
assert_decl ::= "assert" , [ ":" ] , condition , ";"
condition   ::= operand , rel_op , operand
operand     ::= ref | number | call_expr
rel_op      ::= "<" | ">" | "<=" | "=="
```

An `assert` states a structural invariant the board must satisfy, written *in the schematic* rather than in a separate test file. The CDAB (Chapter 20) uses two, and they are the clearest example in the book of why the form exists:

```cas
assert: cjt_l.bias == cjt_r.bias;     // the pair MUST share one bias
assert: cjt_l.beta == cjt_r.beta;     // matched gain keeps CMRR high
```

Those two lines are what makes a differential pair *be* a differential pair. Chapter 20's advice is to author them **first** and then wire the board to satisfy them — the assertion is the requirement, and the netlist is the attempt.

The dotted form `cjt_l.bias` reads an attribute off a declared instance (§C.7 uses the same form for `F3.level` and `o_rail.enabled`). The colon after `assert` is optional; the CDAB listing prints it, the Chapter 23 table omits it, and both parse.

> **Bench Note — an `assert` in the schematic is not a test.** Chapter 23's `assert` lives inside a `test` block and describes what a run should show. This one lives in the netlist and describes what the *design* must be true of, whether or not anybody runs it. Same word, two homes, and the difference matters: a schematic assertion is checked when the board is validated, so a mismatched pair never gets as far as the bench.

### `series` and `transition` — two small wiring statements

```
series_stmt     ::= "series" , ref , "->" , ref , ";"
transition_decl ::= "transition" , identifier , ":" , ref , "->" , ref , ";"
```

`series` states that a component sits **in series with** a named waveform or net, when typing alone would not make it obvious. Chapter 7's compulsion loop uses it to put the habit's inductance in series with the behavioral cycle:

```cas
series L1 -> loop_wave;      // the inductor is in the path of the waveform
```

Everywhere else in this book, series connection is implied by *typing to the same net* — a `Resistor` typed to a CJT's cause is in series with that cause, and Chapter 4's "series mismatch" failure is what happens when the types quietly disagree. `series` is the explicit form for the case where the thing you are wiring into is a `Phi` waveform rather than a single state.

`transition` names a bare domain-to-domain move with no component carrying it. Its main use in this book is to author a violation **on purpose** so you can see the compiler refuse it:

```cas
transition bad: operational -> principled;   // ^O -> ^P, against Domain Descent
```

That line is *syntactically fine* and *structurally illegal*, and the gap between those two words is the whole lesson. The source domain sits strictly below the target in `P ≻ C ≻ E ≻ O`, no diode on the board conducts upward across that seam, and so the transition is inadmissible — the cross-domain family of **E-CJT-008** (Chapter 8). A grammar that rejected the line outright would rob you of the demonstration; the point is that it parses cleanly and *then* fails a design rule, which is exactly what a well-drawn illegal schematic does.

---

## Component Declarations

Components other than the CJT are declared either inline (`<kind> <id>: <Type>< … >;`) or via `let`. Each component carries a typed state (or a domain pair) and its own parameters. The forms below match the style-guide cheat-sheet exactly.

```
component_decl ::= comp_kind , identifier , ":" , component_body , ";"
component_body ::= component_expr                       (* Type< args >            *)
                 | call_expr , "->" , target_list       (* replicate(x) -> [a, b]  *)
                 | call_expr , "=>" , ref               (* decompose(a, b) => c    *)
component_expr ::= type_name , "<" , arg_list , ">" , [ param_block ]
```

The first form — `Type< args >` — is the one you will write ninety-nine times out of a hundred, and it is what the rest of this section documents. The two call-shaped forms belong to a small family of parts whose operands are positional rather than named; they are specified in §C.5.6 at the end of this section.

Inside the angle brackets, an argument is a named parameter, a `Phi<…>` sequence, a reference, or a *transition between references*:

```
arg_list  ::= arg , { "," , arg }
arg       ::= ( key , "=" , value )
            | phi_expr
            | ref_group , [ "->" , ref_group ]
ref_group ::= ref , { "|" , ref }
phi_expr  ::= "Phi<" , ref , { "," , ref } , ">"
```

The `ref_group [ "->" ref_group ]` alternative is what lets a component's argument *be* a directed conversion rather than a list of parts. `Diode< ^P -> ^C >` is the familiar case; `ADC< ^4^E_{F2}|f -> ^4^E_{F2}|A, resolution=8 >` converts a felt impression into an analytical one; `Photodiode< stimulus -> ^0^C >` turns an external stimulus into an internal Idea. The `|`-joined group covers the one part that takes two sources into one target, `BridgeRectifier< ^2^E | ^3^E -> ^2^E >` — both polarities in, one polarity out.

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

### Call-Shaped Components: the Current Mirror and the Active Load

Two parts on the CDAB (Chapter 20) are not written as `Type< args >`. They are written as a **named operation applied to operands, with an explicit target**:

```cas
mirror bias_mirror: replicate(shared_bias) -> [cjt_l, cjt_r];
active_load load1:  decompose(output_L, output_R) => diff_decomp;
```

Read them the way you read the rest of CCDL — left to right, as wiring. `replicate(shared_bias)` names the operation and its one operand; `-> [cjt_l, cjt_r]` names where the replicated copies land, and it is a bracketed list because a current mirror by definition feeds more than one branch. `decompose(output_L, output_R)` takes the two differential halves; `=> diff_decomp` lands the single-ended result on one node.

```
call_expr   ::= identifier , "(" , [ call_arg , { "," , call_arg } ] , ")"
call_arg    ::= ref | number | string | ( key , "=" , value )
target_list ::= "[" , ref , { "," , ref } , "]"
```

The two arrows are not interchangeable, and the difference is the one the rest of the language already makes. **`->` is a directed connection** — a wire, or several: the mirror *distributes* one bias to two places and creates nothing. **`=>` is produces-the-effect** — the same arrow the CJT uses: the active load *converts* two currents into one difference. A mirror wires; an active load produces. If you find yourself reaching for `->` on a part that yields a new state, you have the wrong arrow.

The same `call_expr` appears in four other positions, all of them printed in Part IV:

| Where | Example | Chapter |
|---|---|---|
| Right of `select` | `select cell = nearest(query, bank, metric=fisher_rao);` | 21 |
| Left of `charge`'s arrow | `charge encoder(experience) -> bank [V=impression];` | 21 |
| Inside a condition | `monitor bo: f3_level < threshold(0.35);` | 14 |
| Bound by `let` | `let query = address_on_simplex(dominant=^3^P_{F7}\|f);` | 21 |

> **Bench Note — a call is not a function call.** `replicate(…)` and `decompose(…)` look like code, and that is the one place CCDL's schematic-as-text discipline gets genuinely tested. They are not procedures the board runs; they are **part names with operands**, the way a schematic symbol has pins in a fixed order. Nothing executes. The call shape exists because these parts take their operands *positionally and in a fixed role* — a mirror replicates exactly one bias; an active load decomposes exactly two halves, a left and a right — and `Type< a, b >` would have hidden the fact that swapping them is meaningful. If you want a part whose operands are named and independent of order, you want `Type< key=…, key=… >` instead, and you should use it.

---

## CJT Parameter Block Grammar

The parameter block is the bracketed, comma-separated list of `key=value` pairs after a CJT (and, in reduced form, after `feedback` and some components).

```
param_block ::= "[" , param , { "," , param } , "]"
param       ::= key , "=" , value , [ "on" , drive_tag ]
value       ::= number | duration | region_value | symbol | state_literal | list
duration    ::= number , "s"
region_value::= "cutoff" | "active" | "saturation" | "breakdown"
symbol      ::= identifier | identifier , "::" , identifier
list        ::= "[" , value , { "," , value } , "]"
drive_tag   ::= "F" , ( "1"…"7" )
```

Four notes on the value forms, each of them a form the Part IV listings use:

- A **symbol** is a bare word standing for a named option rather than a number: `action=permanent_block`, `metric=fisher_rao`, `enforce=strict`, `V=impression`, `frequency=fixed`. The scoped form with `::` selects from a named family — `select=Drive::active` means "whichever Drive is currently dominant."
- A **state literal** is a legal value, not just a legal argument: `pump=^7^C` on a refresh, `target_state=^0^P_{F7}|T` on a regulator. The whole-literal tokenization rule of §C.2.2 applies inside parameter blocks exactly as it does outside them.
- A **duration** carries the `s` suffix (§C.2.3): `duration=300s`.
- The trailing **`on <Fk>` qualifier** names the Drive rail a parameter is measured against. It appears on the CPMB's regulator specs — `spec p_reg [dropout=0.25 on F7];` reads "P drops out if F7 falls less than 0.25 above baseline." Without the qualifier the parameter is measured against the component's own rail.

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
board_block ::= "board" , identifier , "{" , { board_item } , "}"
board_item  ::= layer_decl | via_decl | circuit_item
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

### `board` and `circuit`: which one admits what

Earlier printings left this genuinely undecided, and it mattered more than it looked. `board_item` was `layer_decl | via_decl` and nothing else — layout only — while the Cognitive Safety Board, the flagship listing of Part IV, is published as `board cognitive_safety_board { … }` with a body made entirely of terminals, nodes, CJTs, components, a feedback path and probes. Under the old production the book's own most important listing was not a legal board. Two repairs were available and they produce *different languages*, so leaving it open pushed a language-design decision onto whoever implemented the parser.

**The decision, stated once so it stops being ambiguous: a `board` admits everything a `circuit` admits, plus `layer` and `via`. A `circuit` does not admit `layer` or `via`.** A board is a superset; the containment runs one way.

Three reasons, so the rule is not arbitrary:

- **The corpus settles it.** `board cognitive_safety_board` (Chapter 18, Appendix D) and `board nail_biting_cob` (Appendix E) both hold circuit content. Meanwhile *no* `circuit` block anywhere in this book declares a `layer` or a `via`. The asymmetry is already in the listings; the grammar now says so out loud.
- **It matches what the two words mean.** A board *is* a circuit. The layout view adds where each part sits and how signals cross between layers; it does not withdraw the schematic. Forcing you to maintain a separate `circuit` block just to declare the parts would be the text equivalent of a layout you cannot read without holding the schematic in your other hand.
- **It keeps the distinction meaningful in the direction that matters.** `layer` and `via` stay board-only, so writing `board` is still a real claim — "this design has a layout" — and writing `circuit` is still a real promise: schematic only, no layer assignment to go looking for.

Practical consequence for your own work: **if your design has layers, write `board`; if it doesn't, write `circuit`.** You lose nothing by choosing `circuit`, and the reader learns from the keyword alone that there is no layout view to hunt for. The `board csb_v0` fragment above is the pure-layout style — layers and vias, no components — and CCB-1 is the combined style, a full schematic with the layout implied by the states' own domains. Both are legal. Which you write is editorial, and Chapter 17, Step 6 is the place that argues for splitting them on a large board.

---

## Board-Level Statements (Part IV)

The five reference boards in Part IV use statement forms that do not appear in the small circuits of Parts I–III. Each is developed with its rationale in the chapter named; the forms are collected here, and — new in this edition — each one has a production, so the grammar sketch admits the boards the book actually prints.

| Form | Meaning | Chapter |
|---|---|---|
| `rail <Fk>: <Name> [v=…];` | Declares a Drive rail and its supply level | 22 |
| `dial <id>: <^n> [dial=…];` | Sets an operator's current limit; integer 3–9 | 22 |
| `spec <id> [<key>=… on <Fk>];` | Attaches a parameter to a declared instance. A regulator's `dropout` names the rail its own `target_state` sits on. | 22 |
| `constraint <id> in [lo, hi];`<br>`constraint <id> <= <n>;` | A range or relational invariant the design must satisfy | 22 |
| `sequence a -> b -> c [enforce=strict];`<br>`sequence <id>: Phi< a, b, c >;` | Two shapes. The arrow chain is a **power-up ordering**; `strict` forbids skipping. The `Phi` form **labels a cyclic waveform** so an inductor or oscillator can be wired to it by name. | 7, 14, 22 |
| `gate <id>: <rail> requires (<rail> within <n>) and (…);` | Holds a rail in reset until every named rail is inside its tolerance. The `and` chain is conjunctive — *all* conditions, not the first. | 14, 22 |
| `use <circuit>;` | Includes another circuit block by name | 22 |
| `monitor <id>: <expr>;` | A watched condition; pairs with `on` | 14, 22 |
| `on <monitor> { … }` | The block that fires when a monitor trips | 14, 22 |
| `route <src> -> { a + b };` | Directs cognition to rest states. `+` is co-presence (§C.11), not fusion. | 14, 22 |
| `derate <target> [beta_scale=…];` | Scales gain board-wide under stress | 14, 22 |
| `alert "<text>";` | Raises an operator-visible alert | 22 |
| `hold until <expr>;` | Blocks until a condition clears — this is where hysteresis lives | 14, 22 |
| `force_state <id> [duration=…];` | Compels a rest state for a fixed period | 22 |
| `cutoff <target>;` | Drives the named target to β ≈ 0 — the board-wide shutdown of the thermal emergency tier | 22 |
| `enter <state>;` | Transitions the board to a named operating state | 22 |
| `charge <expr> -> <bank> [V=…];` | Writes into a capacitor bank | 6, 21 |
| `discharge <cell> -> <node>;` | Reads a cell out | 6, 21 |
| `decode <node> -> <node>;` | Address-decoder step | 21 |
| `refresh <cell> [pump=<^n>];` | Re-charges a cell against leakage | 21 |
| `select <id> = nearest(<query>, <bank>, metric=…);` | Nearest-neighbour cell selection | 21 |
| `scan <id>: <bank> where <expr> -> <report>;` | Sweeps a bank and reports matching cells — the lacunarity scan | 21 |
| `interrupt <inductor> [dt -> 0];` | Opens an inductive path instantaneously. Models `V = L · dI/dt`: the smaller `dt`, the larger the back-EMF kick. Used to show why abruptly blocking an entrenched habit produces sharp distress. | 7 |

### The productions

Grouped the way the boards use them — supply and invariants, then monitors and the actions they fire, then store-and-recall.

```
board_level_item ::= rail_decl | dial_decl | spec_decl | constraint_decl
                   | sequence_decl | gate_decl | use_decl
                   | monitor_decl | on_block
                   | charge_stmt | discharge_stmt | decode_stmt
                   | refresh_stmt | select_stmt | scan_stmt | interrupt_stmt

(* supply, limits and invariants — Chapters 14, 22 *)
rail_decl       ::= "rail" , drive_tag , ":" , identifier , [ param_block ] , ";"
dial_decl       ::= "dial" , identifier , ":" , state_literal , [ param_block ] , ";"
spec_decl       ::= "spec" , ref , param_block , ";"
constraint_decl ::= "constraint" , ref ,
                    ( "in" , "[" , number , "," , number , "]" | rel_op , value ) , ";"
sequence_decl   ::= "sequence" , ref , "->" , ref , { "->" , ref } , [ param_block ] , ";"
                  | "sequence" , identifier , ":" , phi_expr , ";"
gate_decl       ::= "gate" , identifier , ":" , ref , "requires" , gate_cond , ";"
gate_cond       ::= gate_term , { "and" , gate_term }
gate_term       ::= "(" , ref , "within" , number , ")"
use_decl        ::= "use" , identifier , ";"

(* monitors and the actions they fire — Chapters 14, 22 *)
monitor_decl    ::= "monitor" , identifier , ":" , condition , ";"
on_block        ::= "on" , ref , "{" , { action_stmt } , "}"
action_stmt     ::= derate_stmt | route_stmt | alert_stmt | hold_stmt
                  | force_state_stmt | cutoff_stmt | enter_stmt
derate_stmt     ::= "derate" , ref , [ param_block ] , ";"
route_stmt      ::= "route" , ref , "->" , "{" , ref , { "+" , ref } , "}" , ";"
alert_stmt      ::= "alert" , string , ";"
hold_stmt       ::= "hold" , "until" , condition , ";"
force_state_stmt::= "force_state" , ref , [ param_block ] , ";"
cutoff_stmt     ::= "cutoff" , ref , ";"
enter_stmt      ::= "enter" , identifier , ";"

(* store, address and recall — Chapters 6, 7, 21 *)
charge_stmt     ::= "charge" , ( ref | call_expr ) , "->" , ref , [ param_block ] , ";"
discharge_stmt  ::= "discharge" , ref , "->" , ref , ";"
decode_stmt     ::= "decode" , ref , "->" , ref , ";"
refresh_stmt    ::= "refresh" , ref , [ param_block ] , ";"
select_stmt     ::= "select" , identifier , "=" , call_expr , ";"
scan_stmt       ::= "scan" , identifier , ":" , ref , "where" , condition , "->" , ref , ";"
interrupt_stmt  ::= "interrupt" , ref , [ "[" , "dt" , "->" , number , "]" ] , ";"
```

Four points a careful reader will want, because they are places the grammar is narrower than you might guess:

- **The seven action statements are admitted only inside an `on` block.** That is the only context the corpus puts them in — every `derate`, `route`, `alert`, `hold`, `force_state`, `cutoff` and `enter` in this book sits inside `on bo { … }`, `on warn { … }`, `on crit { … }` or `on emerg { … }`. Whether a bare top-level `derate` should be legal is a design question the book has not answered, so the grammar does not answer it either.
- **A `ref` can be indexed or dotted.** `bank[P3]` addresses a cell in the memory bank (Chapter 21); `F3.level` and `o_rail.enabled` read an attribute off a declared instance (Chapter 22). The full form is in the grammar sketch.
- **`interrupt`'s bracket is not a parameter block.** `[dt -> 0]` is the one place in CCDL where a bracket holds an arrow rather than a `key=value` pair. It is written as its own production because it is a single fixed idiom — the limit `dt → 0` from `V = L · dI/dt` — and not a general facility.
- **`sequence` chains and `gate` conjunctions are both greedy.** `sequence p -> c -> e -> o` is one statement naming four rails in order, not three nested pairs; `requires (…) and (…) and (…)` is one conjunction over three terms. Chapter 14 makes the safety point that a gate checking only the first term is the same failure in a politer costume.

## Verification Statements (Chapter 23)

Chapter 23's bench-test listings use a small verification sub-language. A `test` or `selftest` block groups the statements below.

| Form | Meaning |
|---|---|
| `test <name> { … }` | A named bench test |
| `selftest <name> { … }` | A power-on self-test, run before the board is trusted |
| `inject <id>: fixture "<text>";` | Drives a known input into the board |
| `golden_trace <name> { … }` | Declares the reference probe readings a correct board produces |
| `check <id> matches golden_trace <name> (<probes>);` | Compares observed probe readings against a golden trace |
| `assert <expr>;` | A condition that must hold or the test fails |
| `expect <expr>;` | A condition recorded as expected; a miss is reported, not fatal |

> **Bench Note — this appendix is a language reference, not a compiler manual.** Everything above describes CCDL *as designed*, consistent with the status note in §C.1. The statement forms in these two sections are the ones the Part IV and Chapter 23 listings actually use; the validation rules for them are the same structural rules in §C.9.
>
> **And when you hit a form that isn't here?** Earlier printings answered: assume the appendix is wrong, treat it as an erratum, carry on. That instruction is withdrawn. It sounded generous and it was actually corrosive, because it made the grammar impossible to fail — every gap you could find was defined in advance to be a typo rather than a defect, so no listing could ever count as evidence against the language reference. That is precisely how the corpus came to use more statement vocabulary outside the grammar than inside it, in a book that shipped both. A specification you cannot fail is not a specification; it is a mood.
>
> The rule now is the ordinary engineering one. **A form that is not in this appendix is not part of CCDL.** If you need one, that is a gap, and a gap is *reported*, not assumed away. Name the construct, cite the listing or the design need that requires it, say which existing production it should extend, and file it against this appendix. It gets a production and a row in the construct coverage matrix, or it gets a reasoned refusal — either way the answer is written down where the next reader can find it. The matrix is the ledger: if a leader is not in it, the language does not have it yet, and that is a fact you can check rather than a hole whose shape you have to guess.

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

A consolidated EBNF for the language. (Lexical rules from §C.2; this is the structural grammar.) It is derived from the book's printed listings and admits all five Part IV reference boards; the section that follows says exactly what that does and does not guarantee.

`comp_kind`, `type_name` and `key` are the enumerated word lists in §C.2.7 rather than productions — that is the one place this grammar delegates to a list instead of a rule.

```
ccdl_file      ::= { circuit_block | board_block }

circuit_block  ::= "circuit" identifier "{" { circuit_item } "}"
board_block    ::= "board"   identifier "{" { board_item   } "}"

board_item     ::= layer_decl | via_decl | circuit_item
circuit_item   ::= schematic_item | board_level_item

(* ---- schematic statements: Parts I-III, and the body of every board ---- *)
schematic_item ::= io_decl | node_decl | cjt_decl | component_decl
                 | feedback_decl | probe_decl | let_decl | assert_decl
                 | series_stmt | transition_decl

io_decl        ::= ("input:" | "output:") identifier { "," identifier } ";"
node_decl      ::= "node" identifier ":" state_literal ";"
cjt_decl       ::= "cjt" identifier ":" cjt_expr [ param_block ] ";"
cjt_expr       ::= "CJT<" ref "|" ref "=>" ref ">"
component_decl ::= comp_kind identifier ":" component_body ";"
component_body ::= component_expr
                 | call_expr "->" target_list
                 | call_expr "=>" ref
component_expr ::= type_name "<" arg_list ">" [ param_block ]
feedback_decl  ::= "feedback" [ identifier ":" ] ref "->" ref [ param_block ] ";"
probe_decl     ::= "probe" identifier ":" ref ";"
let_decl       ::= "let" identifier "=" (cjt_expr | component_expr | call_expr)
                   [ param_block ] ";"
assert_decl    ::= "assert" [ ":" ] condition ";"
series_stmt    ::= "series" ref "->" ref ";"
transition_decl::= "transition" identifier ":" ref "->" ref ";"

(* ---- layout statements: board blocks only ---- *)
layer_decl     ::= "layer" domain_tag ":" "[" layer_entry { "," layer_entry } "]" ";"
layer_entry    ::= identifier ":" state_literal
via_decl       ::= "via" identifier ":" via_endpoint "->" via_endpoint [ param_block ] ";"
via_endpoint   ::= state_literal | domain

(* ---- board-level statements: Part IV (Ch. 6, 7, 14, 21, 22) ---- *)
board_level_item ::= rail_decl | dial_decl | spec_decl | constraint_decl
                   | sequence_decl | gate_decl | use_decl
                   | monitor_decl | on_block
                   | charge_stmt | discharge_stmt | decode_stmt
                   | refresh_stmt | select_stmt | scan_stmt | interrupt_stmt

rail_decl       ::= "rail" drive_tag ":" identifier [ param_block ] ";"
dial_decl       ::= "dial" identifier ":" state_literal [ param_block ] ";"
spec_decl       ::= "spec" ref param_block ";"
constraint_decl ::= "constraint" ref ( "in" "[" number "," number "]"
                                     | rel_op value ) ";"
sequence_decl   ::= "sequence" ref "->" ref { "->" ref } [ param_block ] ";"
                  | "sequence" identifier ":" phi_expr ";"
gate_decl       ::= "gate" identifier ":" ref "requires" gate_cond ";"
gate_cond       ::= gate_term { "and" gate_term }
gate_term       ::= "(" ref "within" number ")"
use_decl        ::= "use" identifier ";"

monitor_decl    ::= "monitor" identifier ":" condition ";"
on_block        ::= "on" ref "{" { action_stmt } "}"
action_stmt     ::= derate_stmt | route_stmt | alert_stmt | hold_stmt
                  | force_state_stmt | cutoff_stmt | enter_stmt
derate_stmt     ::= "derate" ref [ param_block ] ";"
route_stmt      ::= "route" ref "->" "{" ref { "+" ref } "}" ";"
alert_stmt      ::= "alert" string ";"
hold_stmt       ::= "hold" "until" condition ";"
force_state_stmt::= "force_state" ref [ param_block ] ";"
cutoff_stmt     ::= "cutoff" ref ";"
enter_stmt      ::= "enter" identifier ";"

charge_stmt     ::= "charge" (ref | call_expr) "->" ref [ param_block ] ";"
discharge_stmt  ::= "discharge" ref "->" ref ";"
decode_stmt     ::= "decode" ref "->" ref ";"
refresh_stmt    ::= "refresh" ref [ param_block ] ";"
select_stmt     ::= "select" identifier "=" call_expr ";"
scan_stmt       ::= "scan" identifier ":" ref "where" condition "->" ref ";"
interrupt_stmt  ::= "interrupt" ref [ "[" "dt" "->" number "]" ] ";"

(* ---- expressions ---- *)
call_expr      ::= identifier "(" [ call_arg { "," call_arg } ] ")"
call_arg       ::= ref | number | string | (key "=" value)
target_list    ::= "[" ref { "," ref } "]"
condition      ::= operand rel_op operand
operand        ::= ref | number | call_expr
rel_op         ::= "<" | ">" | "<=" | "=="

param_block    ::= "[" param { "," param } "]"
param          ::= key "=" value [ "on" drive_tag ]
value          ::= number | duration | region_value | symbol | state_literal
                 | "[" value { "," value } "]"
duration       ::= number "s"
region_value   ::= "cutoff" | "active" | "saturation" | "breakdown"
symbol         ::= identifier | identifier "::" identifier

ref            ::= ref_base { "." identifier | "[" ref_index "]" }
ref_base       ::= identifier | state_literal | domain
ref_index      ::= identifier | number

arg_list       ::= arg { "," arg }
arg            ::= (key "=" value) | phi_expr | ref_group [ "->" ref_group ]
ref_group      ::= ref { "|" ref }
phi_expr       ::= "Phi<" ref { "," ref } ">"

domain_tag     ::= "P" | "C" | "E" | "O"
drive_tag      ::= "F" ("1".."7")

state_literal  ::= noetic [ domain ] [ "_{" drive "}" ] [ register ]
noetic         ::= "^" ("0".."9")
domain         ::= "^" ("P" | "C" | "E" | "O")
drive          ::= "F" ("1".."7")
register       ::= "|" reg_value
reg_value      ::= "T" | "A" | "f" | "E" | "⟨" reg_value { "," reg_value } "⟩"

identifier     ::= letter { letter | digit | "_" }
number         ::= [ "-" ] ( digit { digit } [ "." digit { digit } ] | "." digit { digit } )
string         ::= '"' { any-char-except-quote-or-newline } '"'
comment        ::= "//" { any-char-except-newline }
```

---

## Scope of This Grammar

The grammar above is longer than it used to be, and the honest thing to do with a grammar that has just grown is to say precisely what it now buys you — because the failure this section exists to prevent is a reader concluding that a longer grammar means a more complete language. It does not. It means a grammar that finally matches the listings printed in this book.

**What it guarantees: that a listing is well-formed.** The productions were derived from the book's own printed CCDL — the five reference boards of Part IV (Chapters 18–22, consolidated in Appendix D) and every worked build in Parts I–III — and they admit all of them. Nothing beyond that is claimed. Six limits follow, and each one is a real boundary rather than a disclaimer:

**1. Syntactic admissibility is not semantic validity.** A file that parses is a file the compiler can *read*. Whether it describes a circuit that means anything is decided by the validation passes of §C.9 — and for several statement families, by nothing at all yet. The coverage matrix below says which families those are.

**2. The stateful and temporal family has syntax and no formalized semantics.** `charge`, `discharge`, `refresh`, `scan`, `sequence`, `hold`, `on`, `force_state`, `enter` and `interrupt` all describe something happening *over time*: a cell filling, an ordering being enforced, a condition being watched, a state being held, a path being opened. CCDL as this book defines it is a **declarative netlist language**. It has no execution model, no clock, and no state-transition semantics. You can now write these statements and the grammar will accept them; what a validator should *check* about them, beyond their shape, is not specified anywhere in this book. Read them as documented design intent. Do not read them as verified behavior, and do not build a safety argument on one.

**3. The grammar is corpus-derived and deliberately no wider.** Where the corpus prints one form, the grammar admits one form. `hold` takes `until`. `gate` conditions are `and`-joined `within` terms. The relational operators are `<`, `>`, `<=` and `==` because those are the four this book prints — `>=` and `!=` are not admitted, not because they are bad ideas but because no listing here establishes them. The seven action statements are legal only inside an `on` block for the same reason. This narrowness is deliberate: a grammar that quietly generalizes past its evidence is how the last one drifted away from the boards.

**4. The Chapter 23 verification sub-language is not formalized here.** `test`, `selftest`, `golden_trace`, `inject`, `check` and `expect` are documented as forms in §C.13, but their bodies are prose-valued fields — `tp2 (risk_signal): near zero or negative;` is English with a semicolon, not an expression. The consolidated EBNF covers the circuit/board language only. That is a boundary, stated, rather than a silence.

**5. Parameter ranges constrain values, not relationships.** The compiler can tell you `sat=0.1` is in range and `threshold=0.9` is in range. It cannot tell you that a stage clamped at 0.1 can never drive a fuse that trips at 0.9 — two individually valid numbers that contradict each other across a connection. Relational contradictions between separately-valid parameters are a class of defect the per-value rules in §C.6 do not catch. Know that before you treat "it validates" as "it works"; the golden traces of Chapter 23 exist partly to cover this gap.

**6. Two record formats in Part V are not CCDL at all.** The **evidence packet** and the **circuit-registry entry** of Chapter 25 are printed in the same `cas` blocks as circuit listings, and they are neither circuits nor boards — they are `key: value` records *about* a decision or a released version, with fields like `trace_id`, `hash`, `signature` and `promoted`. They carry CCDL fragments inside them (a `Phi<…>` trace, a quoted source) but the enclosing shape is a record, not a netlist, and no production here admits them. Do not read the shared syntax highlighting as a claim that they are the same language.

### Construct Coverage Matrix

One row per statement leader. **Syntax** means "there is a production in the grammar sketch above." **Semantics** means "this book states what the construct *does*, precisely enough that a validator could check it." The second column is the interesting one, and it is deliberately unflattering in places.

| Leader | Syntax formalized | Semantics formalized | Notes |
|---|---|---|---|
| `input:` / `output:` | Yes | Yes | Terminal declaration; role only (§C.3). |
| `node` | Yes | Yes | Binds a name to a typed state (§C.4.1). |
| `cjt` | Yes | Yes | Parameters, ranges, operating regions, β via Fisher-Rao; five DRC passes (§C.6, §C.9). |
| `<comp_kind>` (component) | Yes | Partial | Passives, `Diode`, `Zener`, `Fuse`, `Transformer`, `Regulator`, `OpAmp`, `Oscillator` have datasheet semantics (Appendix B). `PLL`, `LC`, `DutyCycle`, `Differential`, `LowPass`/`HighPass` have parameter tables but no formal transfer rule. |
| `feedback` | Yes | Yes | Loop gain bounded by the divergence rule; `E-CJT-005` (§C.9.3). |
| `probe` | Yes | Yes | Marks a read point; by definition it does not alter the circuit (§C.4.6). |
| `let` | Yes | Yes | Name binding; the bound expression is instantiated where referenced. |
| `assert` (in-schematic) | Yes | Partial | The CDAB's two invariants are defined exactly; there is no general rule for evaluating an arbitrary assertion. |
| `series` | Yes | Partial | Series connection is otherwise implied by shared typing (Chapters 4–5). What `series X -> Y` additionally *checks* is not stated. |
| `transition` | Yes | Yes | Admissibility is decided by domain precedence plus conducting diodes — the rule Chapter 8 states and `E-CJT-008` codes. Parses clean, then fails DRC, which is the intended demonstration. |
| `layer` | Yes | Yes | Domain-tag match rule; a state must carry its layer's domain (§C.7). |
| `via` | Yes | Yes | Direction rule (Domain Descent down, low-gain feedback up); `E-CJT-008`. |
| `rail` | Yes | Partial | Nominal levels are design choices with a stated scale. What a rail level *does* to downstream gain is formalized only at the brownout threshold. |
| `dial` | Yes | Yes | Integer 3–9, involution-pair divergence ≤ 4, rejection on violation. The tightest-specified board-level statement in the language. |
| `spec` | Yes | Partial | `dropout … on <Fk>` is defined in prose for regulators; there is no general rule for an arbitrary `spec` key. |
| `constraint` | Yes | Yes | A static invariant over declared values; both the range and relational forms are checkable as written. |
| `sequence` | Yes | **No** | Two shapes, neither with temporal semantics. The arrow chain orders rails over time — the book states P→C→E→O must hold and why, but defines no execution model in which "enforce" means anything checkable. The `Phi` form labels a waveform whose cycling is likewise unmodeled. |
| `gate` | Yes | **No** | Hold-until-tolerance is a temporal release condition. `within` borrows the regulator's tolerance band, but the holding and releasing are unmodeled. |
| `use` | Yes | Partial | "Includes another circuit block by name." Whether terminals bind, and whether a name may be included twice, is unstated. |
| `monitor` | Yes | **No** | A continuously watched condition presupposes a time-stepped evaluation the language does not have. |
| `on` | Yes | **No** | Same: "fires when the monitor trips" needs a notion of *when*. |
| `derate` | Yes | Partial | The arithmetic is clear (β is formalized, `beta_scale` multiplies it). *When* it applies and what restores it is not. |
| `route` | Yes | Partial | `+` co-presence is formalized under v7.7 discipline (§C.11). "Directs cognition to" over time is not. |
| `alert` | Yes | Partial | The text is payload. Where an alert goes is a deployment question (Chapter 25), not a language rule. |
| `hold` | Yes | **No** | Blocking until a condition clears is the clearest temporal construct in the language and the least specified. Hysteresis is described, not modeled. |
| `force_state` | Yes | **No** | Compulsion for a duration. `duration=300s` parses; nothing defines what elapsing means. |
| `cutoff` | Yes | Partial | The cutoff *region* is formalized for a CJT (§C.6). What re-enables a board-wide cutoff is not. |
| `enter` | Yes | **No** | Named operating states are neither enumerated nor defined anywhere in this book. `safe_state` is described in prose only. |
| `charge` | Yes | **No** | Writing into a cell over time. `V` and `tau` are named; the charge dynamics are the electronic analogy, not a CAS rule. |
| `discharge` | Yes | **No** | As above, in reverse. |
| `decode` | Yes | **No** | CAS→English rendering. Explicitly design-level throughout Chapter 21. |
| `refresh` | Yes | **No** | Rehearsal against leakage. `gain` and `pump` are named; the race between them is described, not formalized. |
| `select` | Yes | Partial | The retrieval *metric* is exact — `d_FR(p,q) = 2·arccos(Σ√(pₖqₖ))` on the open simplex Δ39°. The bank and addressing model around it is design-level. |
| `scan` | Yes | **No** | Sweeping a bank and reporting matches is an operation over stored state, and stored state is unmodeled. |
| `interrupt` | Yes | **No** | `dt -> 0` is the limit in `V = L · dI/dt`. There is no formal limit semantics in the CAS state model; the kick is an analogy that teaches, not a computation. |
| `test` / `selftest` | Table only | **No** | Documented in §C.13; not in the EBNF. Bodies are prose-valued fields. |
| `inject` / `check` | Table only | **No** | As above. `fixture "<text>"` and `matches golden_trace <name>` are the printed forms. |
| `golden_trace` | Table only | **No** | A block of expected readings written in English. Deliberately so — Chapter 23 uses it to record design intent, not to compute. |
| `expect` | Table only | **No** | Test-block field. Distinct from the in-schematic `assert` above. |

Count the second column before you trust the first. Of the thirty-nine rows, **eleven leaders have full semantics, eleven are partial, and seventeen have none** — and that last block is not a random scatter. It is almost exactly the stateful and temporal family named in limit 2 above, plus the Chapter 23 verification sub-language. That is a *coherent* gap rather than a list of oversights, and naming it as one is the point of publishing this matrix at all. The hardest register in the language is the one the book has formalized least, which is worth knowing before you decide how much weight a `hold` or a `force_state` can carry in a safety argument.

The matrix is also the ledger the Bench Note in §C.13 refers to. A construct that is not in it is not in the language yet; a construct whose semantics column says **No** is a construct you can write down and cannot yet verify.

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
