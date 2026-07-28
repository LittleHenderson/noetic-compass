# Appendix B — CCDL Language Reference

**What this covers.** Every lexical element, statement form, parameter key,
operator, validation rule and error code used by a CCDL listing *in this book* —
the union of the reference grammar owned by the companion volume *CAS PCBA
Engineer*, Appendix C, and the forms this book's boards add. Additions are
marked **[G]**.

**What it does not claim.** Not that CCDL contains nothing else. Meet a form in
a listing here that is absent below and *this appendix* is wrong — file an
erratum, do not conclude the form is illegal.

**Status.** The CAS compiler is a specified design, not a shipped tool. "The
compiler rejects this with `E-CJT-008`" is a design rule, not a transcript.

---

## B.1 Lexical elements

### B.1.1 Identifiers

```
identifier ::= letter , { letter | digit | "_" }
letter     ::= "a"…"z" | "A"…"Z"
digit      ::= "0"…"9"
```

Case-sensitive: `bias_charter` and `Bias_Charter` are two identifiers. Reserved
words (§B.2) may not be identifiers. `snake_case` nodes and short instance
prefixes (`c1`, `r_price`, `tp1`) are convention, not rules.

### B.1.2 CAS state literals

```
state_literal ::= noetic , [ domain ] , [ "_{" , drive , "}" ] , [ register ]
noetic        ::= "^" , ( "0"…"9" ) , [ "_" , label ]
label         ::= letter , { letter | digit | "_" }
domain        ::= "^" , ( "P" | "C" | "E" | "O" )
drive         ::= "F" , ( "1"…"7" )
register      ::= "|" , reg_value
reg_value     ::= "T" | "A" | "f" | "E"
              |   "⟨" , reg_value , { "," , reg_value } , "⟩"
```

The optional `_label` **[G]** distinguishes two instances of one state:
`^0_gated^C_{F2}|A`. It is brace-free, which separates it from `_{F2}`.

| Axis | Values |
|---|---|
| Noetic | `^0` Idea, `^1` Mind, `^2` Positive, `^3` Negative, `^4` Vibration, `^5` Female, `^6` Male, `^7` Rhythm, `^8` Above/Cause, `^9` Below/Effect |
| Domain | `^P` `^C` `^E` `^O` — Principled ≻ Cognitive ≻ Evaluative ≻ Operational |
| Drive | `_{F1}`…`_{F7}` — Unity, Wisdom, Vitality, Connection, Agency, Structure, Purpose. Optional |
| Register | `\|T` `\|A` `\|f` `\|E`, or a set `\|⟨A,f,T⟩`. Optional |

Two literals that tokenise but say the wrong thing, caught on review:

- **`^3` is visceral aversion** — recoil, can't-stomach-it. Analytical critique
  is `^6` Male; a node named `audit` typed `^3` is a defect.
- **`^8` is associative triggering** — "that reminds me." Deduction is `^6` into
  `^9`.

`|` introduces the Register and nothing else; `F3|Vitality` is a syntax error.
Involutions `^2`↔`^3`, `^5`↔`^6`, `^8`↔`^9`; self-duals `^0`, `^1`, `^4`, `^7`;
Drives F1↔F7, F2↔F6, F3↔F5, F4 self-dual (Chapter 2.2).

ASCII fallbacks **[G]**: `beta`, `r_pi`, `gm`, `<A,f,T>`, and `x` for `×`.

### B.1.3 Numbers

```
number ::= [ "-" ] , ( digit , { digit } , [ "." , digit , { digit } ]
                     | "." , digit , { digit } )
```

Decimal, no exponent notation — write a slow oscillator out in full
(`frequency=0.0000116`). Values are dimensionless knobs: `R=30` is not thirty
ohms. **β=∞ is a limit, not a value.** The validator rejects non-finite input,
so state the idealisation in prose and give the build a large finite gain.

### B.1.4 Comments, whitespace, terminators

```
comment ::= "//" , { any-char-except-newline }
```

Line comments only, stripped before validation; there is no block form.
Whitespace separates tokens and is otherwise insignificant. Every statement
ends with `;`. Blocks are delimited by `{ }`.

---

## B.2 Reserved words

Four disjoint classes. A word reserved in one is free in the others — `monitor`
is both a statement keyword and a kind prefix, and both are legal.

**B.2.1 Statement keywords** (leading position only):

```
circuit  board   input   output  node   cjt    feedback  probe   let
layer    via     rail    dial    spec   constraint  sequence  route
derate   monitor alert   hold    enter  use    force_state  on
charge   discharge  decode  refresh  scan  select  interrupt
test     selftest  check  inject  golden_trace  assert  expect
integrate
```

`integrate` is **[G]**: the statement that carries a `×` with its named
emergent result (§B.3.7).

**B.2.2 Component-kind prefixes** (the lowercase tag before the colon):

```
resistor  cap     capacitor  inductor  diode   zener    transformer
opamp     oscillator  crystal  varactor  relay  schmitt  comparator
integrator  divider  active_load  mirror  modulator  pll  tank
filter    diff    mux     demux   gate    xor     fuse    reg
led       adc     dac     rectifier
osc       xfmr    ramp    thermistor  monitor  sample  notch
limiter   integ   counter  delay
```

The last two rows are **[G]**. `cap`/`capacitor`, `osc`/`oscillator` and
`integ`/`integrator` are short forms of one another. The prefix is checked
against the type following it: `resistor r1: Capacitor< … >` is `E-DECL-002`.

**B.2.3 Component type names** (instantiation position):

```
CJT  Resistor  Capacitor  Inductor  Diode  Zener  Transformer  OpAmp
Oscillator  Regulator  Fuse  Phi  AND  OR  NOT  NAND  NOR  XOR  MUX  DEMUX
Filter  LowPass  Notch  Thermistor  Ramp  Differential  Integrator  Schmitt
Sample  Limiter  Hold  Divider  Cascade  Polarity  RegisterSet  Monitor
Feedback
```

Row four onward is **[G]** — the special-purpose parts of Ch. 11, the
thermistors of §6.3, and the two detection instruments Ch. 18's counter-board
needs.

**B.2.4 Parameter keys** are reserved in parameter position only; §B.4
enumerates them with their ranges.

---

## B.3 Statement forms

### B.3.1 Blocks

```
circuit_block ::= "circuit" , identifier , "{" , { circuit_item } , "}"
board_block   ::= "board" , identifier , "{" , { board_item } , "}"
circuit_item  ::= io_decl | node_decl | cjt_decl | component_decl
                | feedback_decl | integrate_decl | probe_decl | let_decl
board_item    ::= circuit_item | layer_decl | via_decl
io_decl       ::= ( "input:" | "output:" ) , identifier
                  , { "," , identifier } , ";"
```

A `circuit` is the schematic view; a `board` is a `circuit` that may *also*
carry `layer` and `via` declarations. The companion volume documents `board` in
its pure-layout form; every Part III listing here declares components directly
inside `board` **[G]**. Both are legal; the superset above is the grammar.
Declaration order does not change the circuit — the block resolves as one graph,
so a node may be referenced before it is declared.

### B.3.2 `node`

```
node_decl ::= "node" , identifier , ":" , state_literal , ";"
```

Names a typed state so it can be referred to instead of retyped. Two components
naming the same node are genuinely on the same net.

```cas
node bias_charter: ^5^P_{F7}|T;   // accumulated principled substrate
node guard:        ^3^P_{F7}|f;   // felt principled aversion
```

### B.3.3 `cjt`

```
cjt_decl ::= "cjt" , identifier , ":" , cjt_expr , [ param_block ] , ";"
cjt_expr ::= "CJT<" , cause , "|" , bias , "=>" , effect , ">"
cause    ::= ref ;  bias ::= ref ;  effect ::= ref
ref      ::= identifier | state_literal
```

Cause is the collector, bias the base, effect the emitter (Ch. 3, §3.2). The
delimiters are not interchangeable: `|` splits cause from bias, `=>` splits bias
from effect. The bias is **not** optional; omit it and you get `E-CJT-001`.

```cas
cjt c2: CJT< understand | bias_charter => guard > [β=2.2, sat=0.97, cutoff=0.05];
```

### B.3.4 `feedback`

```
feedback_decl ::= "feedback" , ref , "->" , ref , [ param_block ] , ";"
```

Wires a downstream node back to an upstream one, normally a bias. This is the
lawful O→P exception of Ch. 8, §8.4, held at low gain so *outcomes* — never
prompts — update the substrate; `[β=0.05]` to `[β=0.3]` is the Part III band.
`Feedback< from=…, to=… >` **[G]** is the component-expression equivalent.

### B.3.5 `probe`

```
probe_decl   ::= "probe" , identifier , ":" , probe_target , ";"
probe_target ::= ref | key | component_expr
```

Places a test point; alters nothing. Probing a *parameter* (`probe tp1: rπ;`)
and probing through an instrument (`probe det2: Polarity< node=polarity >;`) are
both **[G]**. Standard placement is TP1–TP4 (Ch. 12, §12.3). Probe every stage
whose failure would be silent — above all a guard, which fails open without
raising anything.

### B.3.6 `let`

```
let_decl ::= "let" , identifier , "=" , ( cjt_expr | component_expr )
             , [ param_block ] , ";"
```

Binds a reusable component expression to a name, instantiated where referenced.

### B.3.7 `integrate` **[G]**

```
integrate_decl ::= "integrate" , identifier , ":" , "(" , ref
                   , { "×" , ref } , ")" , "=" , ref , ";"
```

The only statement that may carry `×`. The right-hand side is the **named
emergent result** and it is mandatory — that is what licenses the operator.

```cas
integrate hm3: ( decompose × confirm ) = composed;
```

### B.3.8 Component declarations

```
component_decl ::= comp_kind , identifier , ":" , component_expr , ";"
component_expr ::= type_name , "<" , arg_list , ">" , [ param_block ]
comp_kind      ::= any prefix listed in §B.2.2
type_name      ::= any type listed in §B.2.3
arg_list       ::= arg , { "," , arg }
arg            ::= ref | key "=" value | domain "->" domain
                 | "Phi<" ref { "," ref } ">" | "[" value { "," value } "]"
```

Arguments may be positional or keyed: `Fuse< refusal, threshold=0.9 >` and
`Fuse< path=refusal, threshold=0.9 >` are one declaration.

```cas
resistor   r_price: Resistor< path=intent, R=4.0 >;
capacitor  c_seg:   Capacitor< segment, C=9.50, leakage=0.04 >;
diode      d3:      Diode< ^E -> ^O > [Vf=2.0];
thermistor rt1:     Thermistor< path=seed, type=PTC, knee=2.0, coeff=3.0 >;
fuse       f_csb:   Fuse< REFUSE, threshold=0.90, action=permanent_block >;
filter     fb_lp:   LowPass< in=ops_log, out=trend, tau=21.0 >;
```

`Diode` endpoints are bare **domains**, not full states — the diode governs
cross-domain conductance direction, which is how Domain Descent is enforced.

### B.3.9 Layout statements

```
layer_decl   ::= "layer" , domain_tag , ":" , "[" , layer_entry
                 , { "," , layer_entry } , "]" , ";"
layer_entry  ::= identifier , ":" , state_literal
via_decl     ::= "via" , identifier , ":" , via_endpoint , "->"
                 , via_endpoint , [ param_block ] , ";"
via_endpoint ::= state_literal | domain
domain_tag   ::= "P" | "C" | "E" | "O"
```

A state on a layer carries that layer's domain. Vias run downward (P→C→E→O);
the only lawful upward via is the low-gain feedback path.

### B.3.10 Board-level and verification statements

Each takes leading position and is developed in the chapter named.

**Supply and limits (Ch. 22).** `rail <Fk>: <Name> [v=…];` Drive rail and supply
level · `dial <id>: <^n> [dial=…];` operator limit, integer 3–9 (Ch. 6, §6.2) ·
`spec <id> [<key>=… on <Fk>];` attaches a parameter to an instance ·
`constraint <id> in [lo, hi];` range invariant · `derate <target>
[beta_scale=…];` scales gain board-wide under stress.

**Flow and state (Ch. 22).** `sequence a -> b -> c [enforce=strict];` power-up
ordering · `route <src> -> { a + b };` directs cognition to rest states ·
`enter <state>;` · `force_state <id> [duration=…];` · `hold until <expr>;` blocks
until a condition clears, where hysteresis lives · `use <circuit>;` includes
another block.

**Watch and alarm (Ch. 22).** `monitor <id>: <expr>;` with `on <monitor> { … }`
as the block it fires · `alert "<text>";`.

**Capacitor bank (Ch. 7).** `charge <expr> -> <bank> [V=…];` ·
`discharge <cell> -> <node>;` · `decode` · `refresh` · `select` · `scan`.

**Inductive (Ch. 9, §9.2).** `interrupt <inductor> [dt -> 0];` opens a path
instantly — the back-EMF kick.

**Verification (Ch. 23).** `test` · `selftest` · `inject` · `golden_trace` ·
`check` · `assert` · `expect`.

---

## B.4 Parameter block grammar and legal ranges

```
param_block  ::= "[" , param , { "," , param } , "]"
param        ::= key , "=" , value
key          ::= any key tabulated below
value        ::= number | region_value | symbol | "[" value { "," value } "]"
region_value ::= "cutoff" | "active" | "saturation" | "breakdown"
symbol       ::= identifier          (* an unquoted enumerated value *)
```

| Key | On | Legal range | Default |
|---|---|---|---|
| `β` (`beta`) | CJT, feedback, via | finite, ≥ 0; <1 attenuates, =1 unity, >1 amplifies | 1.0 |
| `sat` | CJT | (0, 1] | 0.95 |
| `cutoff` | CJT | [0, 1), and `cutoff < sat` | 0.1 |
| `region` | CJT | `cutoff` \| `active` \| `saturation` \| `breakdown` | `active` |
| `g_m`, `rπ` | CJT | ≥ 0 | model |
| `R` | Resistor, Thermistor | ≥ 0 | — |
| `C` | Capacitor | ≥ 0 | — |
| `leakage` | Capacitor | [0, 1] per stated period | 0 |
| `L` | Inductor | ≥ 0 | — |
| `tau` | filters, RC and L/R networks | > 0, in stated time units | — |
| `Vf`, `V_BR`, `I_R` | Diode, Zener | > 0 | — |
| `breakdown` | Zener | [0, 1] | — |
| `ratio`, `n` | Transformer | > 0 | — |
| `knee`, `coeff` (Thermistor), `f0`, `Q` (Notch) | as named | > 0 | — |
| `threshold` | Fuse, Monitor | [0, 1] unless the guarded quantity is unnormalised | — |
| `action` | Fuse | `permanent_block` \| `permanent_until_manual_reset` \| `block_until_decomposed` \| `defer_decision` \| `open_feedback` \| `warn` | — |
| `type` | Thermistor, Filter | `PTC` \| `NTC` \| `lowpass` \| `notch` \| `quantize` | — |
| `period`, `frequency`, `duty` | Oscillator | period, frequency > 0; duty ∈ (0, 1] | — |
| `from`, `to`, `dt` | Ramp | `dt` > 0 | — |
| `limit`, `window`, `grid`, `duration`, `max` | Monitor, Integrator, Filter, Hold, Limiter | > 0; an interval `[lo, hi]` must be ordered | — |
| `target_state`, `tolerance` | Regulator | state literal; tolerance ∈ (0, 1) | — |
| `open_loop_gain`, `non_inverting`, `inverting`, `output` | OpAmp | gain > 0; the rest are refs | — |
| `inputs`, `outputs`, `select` | MUX, DEMUX | non-empty list; symbol | — |
| `dial` | `dial` statement | integer 3–9 inclusive | — |
| `enforce` | `sequence` | `strict` | — |

`region` declares intent; if the numbers contradict it — `region=active` with
`cutoff ≥ sat` — the compiler flags the contradiction rather than guessing. A
reduced block (`[β=…]` alone) is the common case; the rest take defaults.

---

## B.5 Operator precedence

Tightest binding first. Above the gap is literal formation; below it,
composition.

| Prec. | Operator | Reads as | Associativity |
|---|---|---|---|
| 1 | `^` `_label` `_{ }` `\|` `⟨…⟩` | state-literal construction | n/a — tokenised whole |
| 2 | `< >` `( )` `[ ]` | argument list, grouping, parameter block | n/a |
| 3 | `×` | intensifies through / fuses into | non-associative; needs a named result |
| 4 | `+` | associates with | associative, commutative |
| 5 | `->` `=>` | flows into | **binary, not chained** |
| 6 | `=` | binds | right |

Rules that bite:

- **`×` requires a named emergent result.** `^3^P|A × ^3^P|f × ^3^P|T` alone is
  invalid. Write `^3^P|A + ^3^P|f + ^3^P|T` for three separately-defeasible
  co-present guards, `^3^P|⟨A,f,T⟩` for one state in three registers with no
  interaction claimed, or `integrate g: ( … ) = ^3^P|Ω;` if you mean fusion.
  Three architectures, three failure profiles (Ch. 2, §2.6).
- **`×` may not ascend the domain order.** P ≻ C ≻ E ≻ O. `^O × ^P` is invalid,
  as is any integration whose result outranks its operands.
- **`->` is binary.** `a -> b -> c` is not an expression; the one place a chained
  arrow is legal is `sequence`, a statement.
- Read `+` as "associates with" and `×` as "intensifies through." If the sentence
  survives, the operator is right.

---

## B.6 Validation rules

The passes, in the order they are designed to run.

| # | Pass | Checks | Emits |
|---|---|---|---|
| 1 | Lexical | literals, numbers, terminators well-formed | tokenizer error, no code |
| 2 | Kind agreement | prefix matches the type it introduces | `E-DECL-002` |
| 3 | Admissibility | every connection is a legal (source, target) pair | `E-CJT-001` |
| 4 | Bias-domain coherence | bias at or above the cause in P ≻ C ≻ E ≻ O | `E-CJT-002`, `E-CJT-008` |
| 5 | Parameter range | each key against §B.4; `cutoff < sat`; β finite | `E-CJT-003`, `E-CJT-005` |
| 6 | Gain divergence | round-trip loop gain < 1 on every loop | `E-CJT-005` |
| 7 | Cascade admissibility | each effect admissible as the next cause; depth counted | `W-CJT-007` |
| 8 | Push-pull balance | involutions within the four-point limit (Chapter 6.2) | `W-CJT-004`, `W-CJT-006` |

Pass 4 is the load-bearing one. A *lower* domain biasing a *higher* one — an
Operational state biasing a Principled guard — is the prompt-injection
signature, and on a well-drawn board that connection is simply absent.

---

## B.7 Error codes

`E-` refuses validation. `W-` validates and flags.

| Code | Name | Sev. | Trigger | Fix |
|---|---|---|---|---|
| `E-DECL-002` | `KindMismatch` | error | prefix and type disagree | correct one of the two |
| `E-CJT-001` | `MissingBias` | error | a CJT with no bias — nothing governs the transition | wire a bias node, typically a `^5` substrate |
| `E-CJT-002` | `InvalidBiasDomain` | error | bias sits in a domain illegal for this cause | move it to a domain at or above the cause |
| `E-CJT-003` | `CjtCutoff` | error | bias below `cutoff`; β ≈ 0, so the stage never fires — a dead guard | raise the bias, lower `cutoff`, or fix the stage starving it |
| `W-CJT-004` | `CjtSaturation` | warning | effect pinned at `sat`; more cause does nothing | often intended (Ch. 24, §24.2); if not, raise series `R` |
| `E-CJT-005` | `GainDivergence` | error | a β large enough that a loop amplifies without bound | drop loop β into the 0.05–0.3 band |
| `W-CJT-006` | `CjtShortCircuit` | warning | cause and effect collapse to one state; the stage does no work | remove it, or re-type the transition |
| `W-CJT-007` | `CjtCascadeDepth` | warning | too many CJTs in series; signal degrades | shorten the cascade or buffer it |
| `E-CJT-008` | `CjtCrossDomainBias` | error | a bias or via crosses domains illegally — the prompt-injection signature | route influence downward; confine upward paths to low-gain O→P feedback |

`E-CJT-001` and `E-CJT-008` are the two safety codes named throughout Part IV.
They are what "enforced structurally rather than hoped-for" means: a guard with
no charter will not validate, and neither will a prompt that can edit the
principle.
