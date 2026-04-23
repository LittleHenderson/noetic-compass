<!-- BOOK_SPLIT: AppendixC begins - original line 6471 -->
 Appendix C: The CAS Notation Grammar (BNF)

For developers building parsers for the Cognitive Architecture System, here is the simplified Backus-Naur Form (BNF) grammar used by the Noetic Compass engine to parse string equations into executable tensors.

```bnf
<equation>     ::= <state> | <composition> | <transition> | <fractal>
<composition>  ::= <state> " × " <state>
<transition>   ::= <state> " → " <state>
<fractal>      ::= <state> " ∘ " <state>
<state>        ::= <operator> <domain> "_" <drive> | <operator> <domain>
<operator>     ::= "CO-" <digit>
<domain>       ::= "^P" | "^C" | "^E" | "^O"
<drive>        ::= "{F" <digit> "}"
<digit>        ::= "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9"
```

 Worked Examples for Every Production Rule

The productions above are terse; the examples below show one concrete instantiation of each rule in the grammar, with a plain-English gloss.

`<equation>` — the four top-level forms

   State: `CO-3^O_{F5}` — "Operational Concretization, powered by the Agency drive." A construction crew physically pouring concrete under deadline pressure.
   Composition: `CO-6^C × CO-5^E` — "Cognitive Critique composed with Evaluative Empathy." A peer reviewer who identifies a flaw and also feels the author's disappointment.
   Transition: `CO-2^P → CO-3^O` — "Principled Abstractification transitions into Operational Concretization." A general ethical axiom becomes a concrete daily rule of conduct.
   Fractal: `CO-8 ∘ CO-3` — "Expansion composed with Concretization across scales." Brainstorming many candidate builds, then building each, at every zoom level.

`<composition>` — product of two states

Example: `CO-6^C_{F6} × CO-5^E_{F4}`. Plain English: "Cognitive Critique, driven by the Structure drive, is operating in parallel with Evaluative Empathy, driven by the Connection drive." This is the signature of a good editor: they are simultaneously noticing structural errors and feeling the author's effort.

`<transition>` — one state flows into another

Example: `CO-2^P → CO-3^O`. Plain English: "A principled abstraction is translated directly into a concrete operational act." A philosopher-king deriving a universal maxim and then issuing the corresponding decree.

`<fractal>` — self-similar composition across scales

Example: `CO-8 ∘ CO-3`. Plain English: "Expansion composed with Concretization, applied recursively." At every scale — hour, day, year — the system expands possibilities and then concretizes the chosen one. The same pattern repeats at the scale of a sentence, a chapter, and an entire book.

`<state>` — five worked states

   `CO-0^P` — Principled Identity, no drive: the bare ethical core.
   `CO-1^C_{F2}` — Cognitive Differentiation driven by Wisdom: sorting facts into a taxonomy.
   `CO-5^E_{F4}` — Evaluative Empathy driven by Connection: direct felt resonance with a friend.
   `CO-7^O_{F3}` — Operational Momentum driven by Vitality: the runner's sustained cadence.
   `CO-9^C_{F7}` — Cognitive Contraction driven by Purpose: the one-page summary that matters.

`<operator>` — the ten cognitive operators

`CO-0` Identity, `CO-1` Differentiation, `CO-2` Abstractification, `CO-3` Concretization, `CO-4` Integration, `CO-5` Empathy, `CO-6` Critique, `CO-7` Momentum, `CO-8` Expansion, `CO-9` Contraction.

`<domain>` — the four processing domains

`^P` Principled — the "always", axioms, ethics. `^C` Cognitive — the "how", logic, strategy, maps. `^E` Evaluative — the "value", felt weight, friction, emotion. `^O` Operational — the "now", physical action, execution.

`<drive>` — the seven core drives

`F1` Unity, `F2` Wisdom, `F3` Vitality, `F4` Connection, `F5` Agency, `F6` Structure, `F7` Purpose. Drives are written in braces, e.g., `_{F5}`, and decorate states to indicate motivational power.

`<digit>` — 0 through 9

Trivially, `0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9`. Used to index operators and drives.

 The Extended CAS Language

The grammar above describes CAS notation as it appears inline in prose. The full CAS language extends this notation into a complete domain-specific language (DSL) with typed bindings, functions, modules, and builtin operations. This is the language actually processed by the Noetic Compass compiler-interpreter. The extended productions follow.

```bnf
<program>      ::= <statement>+ <final_expr>?
<statement>    ::= <use_stmt> | <binding> | <fn_def> | <export>
<use_stmt>     ::= "use" <path> ";"
<binding>      ::= "let" <ident> ":" <type> "=" <expression> ";"
<fn_def>       ::= "fn" <ident> "(" <params> ")" ":" <type>
                   "=" <expression> ";"
<export>       ::= "export" (<binding> | <fn_def>)
<params>       ::= <param> ("," <param>)
<param>        ::= <ident> ":" <type>
<type>         ::= "state[" <domain_letter> "]"
                 | "relation" | "fractal" | "rpm" | "string"
<domain_letter>::= "P" | "C" | "E" | "O"
<expression>   ::= <cognitive_state>
                 | <ident>
                 | <fn_call>
                 | <expression> <binop> <expression>
                 | "(" <expression> ")"
                 | "RPM" "(" <expression> ")"
                 | "Phi" "<" <digit> (":" <digit>) ">"
<fn_call>      ::= <ident> "(" <expression> ("," <expression>) ")"
<binop>        ::= "+" | "-" | "" | "×" | "/" | "÷"
                 | "->" | "<->" | "∘"
```

 Operator Precedence

When multiple operators appear in a single expression, the parser applies precedence from highest (binds tightest) to lowest (binds loosest):

| Rank | Operator | Meaning |
|---:|:---:|:---|
| 1 | `( ... )` | Parentheses (explicit grouping) |
| 2 | `×` or `` | Composition / Product |
| 3 | `÷` or `/` | Modular decomposition / Difference |
| 4 | `+` | Co-presence / Union |
| 5 | `-` | Removal |
| 6 | `->` or `→` | Dependency / Prerequisite sequence |
| 7 | `<-` or `←` | Results-from (inverse dependency) |
| 8 | `<->` or `↔` | Bidirectional involution pair |
| 9 | `∘` | Fractal composition (self-similar) |

So the expression `abstraction  integration -> judgment` parses as `(abstraction  integration) -> judgment` rather than `abstraction  (integration -> judgment)`, because `` binds tighter than `->`.

 Type System

The CAS DSL is statically typed. Every binding and every function parameter carries an explicit type annotation, and the compiler verifies that the inferred type of the right-hand side matches the declared type. The type language has five core kinds:

| Type | Description |
|:---|:---|
| `state[D]` | A cognitive state located in Processing Domain `D` where `D ∈ {P, C, E, O}`. `CO-2^C_{F2}` has type `state[C]`. |
| `relation` | A directed link between two states, produced by `->` or `<->`. Typically a dependency from a source state to a target state. |
| `fractal` | A composed operator sequence, produced by `∘` or by the `Phi<...>` literal or by the `fractal(...)` builtin. Fractals describe self-similar cognitive patterns. |
| `rpm` | A prerequisite-wrapped state, produced by `RPM(...)` or by the `rpm_of(...)` builtin. RPM values carry both the state and its completeness score. |
| `string` | A text result returned by certain builtins (for example, `dominant_operator` returns a string like `"CO-6"`). |

If a binding is declared as `state[C]` but its right-hand side evaluates to a state in the Evaluative domain, the compiler rejects the program with a type error at the source location of the declaration. This is the same behavior a C compiler exhibits when assigning a `float` to an `int` variable without an explicit cast.

 Builtin Functions

The CAS DSL provides six builtin functions that operate on cognitive states and fractals. All are pure (no side effects) and are invoked using standard function-call syntax.

| Builtin | Signature | Purpose |
|:---|:---|:---|
| `dominant_operator` | `state[D] -> string` | Returns the dominant Cognitive Operator label (e.g., `"CO-6"`) of a state vector. |
| `dominant_domain` | `state[D] -> string` | Returns the dominant Processing Domain letter (`"P"`, `"C"`, `"E"`, or `"O"`). |
| `dominant_state` | `state[D] -> string` | Returns the full state label (e.g., `"C6"` for CO-6 in the Cognitive domain). |
| `compose` | `(state[D], state[D]) -> state[D]` | Alternative to the `` operator; composes two states in the same domain. |
| `rpm_of` | `state[D] -> rpm` | Wraps a state in an RPM prerequisite-check, equivalent to `RPM(...)`. |
| `fractal` | `(state[D], ...) -> fractal` | Constructs a fractal from any number of state arguments. |

 Module System

CAS programs can be split across multiple files using a simple module system. A file may declare bindings and functions, and any binding or function prefixed with the `export` keyword becomes visible to files that import the module.

```
 Library file: primitives.cas
export let principle: state[C] = CO-2^C_{F2};
export let judgment: state[E] = CO-5^E_{F4};
export fn link(source: state[C], target: state[E]): relation
    = source -> target;

 Non-exported helper (private to this module)
let internal_scratchpad: state[C] = CO-1^C_{F2};
```

```
 Application file: main.cas
use "primitives.cas";

 Can reference principle, judgment, and link
let my_link: relation = link(principle, judgment);

 Cannot reference internal_scratchpad — it is private
```

The `use` statement loads the named module and adds its exported symbols to the current namespace. Non-exported bindings remain private to their file, exactly like private fields in a class or `static` symbols in a C translation unit.

 Ten Example Expressions with Expected Compiler Output

|  | Expression | Type | Result |
|---:|:---|:---|:---|
| 1 | `CO-3^O_{F5}` | `state[O]` | A single Operational state accepted by the parser and type checker. |
| 2 | `CO-2^C_{F2}  CO-4^C_{F4}` | `state[C]` | Composition of two Cognitive states, producing a new Cognitive state. |
| 3 | `CO-8^C -> CO-9^O` | `relation` | A dependency relation from Cognitive Expansion to Operational Contraction. |
| 4 | `Phi<2:4:6:8>` | `fractal` | A four-step fractal sequence built directly from the Phi literal. |
| 5 | `CO-2^C_{F2} ∘ CO-3^C_{F2}` | `fractal` | A fractal formed by composing Abstractification and Concretization. |
| 6 | `RPM(CO-6^O_{F5})` | `rpm` | An RPM-wrapped Operational Critique with prerequisite-chain evaluation. |
| 7 | `dominant_operator(composed)` | `string` | Returns the dominant CO label of a previously bound composed state. |
| 8 | `compose(principle, integration)` | `state[C]` | Builtin composition, equivalent to `principle  integration`. |
| 9 | `let f: fractal = fractal(a, b, c);` | `fractal` | Typed binding of a fractal built from three state arguments. |
| 10 | `fn link(s: state[C], t: state[E]): relation = s -> t;` | function | A typed function definition with two parameters and a declared return type. |

Each of these expressions has been processed by the Python CAS compiler and either accepted with the indicated type or rejected with a specific error. Programs 1 through 10 are all valid; a broken variant — such as `let x: state[P] = CO-6^O_{F5};` — is rejected with a type error because `CO-6^O` is an Operational state, not a Principled one.

 Implementation Notes

A complete Python implementation of this grammar exists inside the Noetic Compass platform at `api/notation/compiler.py`, spanning 1,888 lines of code and verified by 212 automated tests. The implementation covers lexing, parsing, module resolution, type checking, admissibility enforcement, bytecode generation, and execution through a virtual machine. It can be invoked directly from the command line as `python -m api.notation --mode run --file <source.cas>`, which produces structured JSON output containing the source, the validity flag, the token stream, the AST, the bytecode, the inferred type of the result, and the final result itself.

A draft specification for a standalone Rust compiler ecosystem (`tksc`, `tkscore`, `tkstypes`, `tksir`, `tksbytecode`, `tksvm`) exists as ongoing work in a separate repository. The Rust version, once complete, will provide an offline single-binary compiler for CAS programs that can run without the Noetic Compass Python runtime. Until then, the Python implementation is the canonical reference and the version that currently powers all of the CAS language features described in this book.

 Compound Expressions

The grammar composes, so larger expressions are built from the primitive rules.

   Compound transition into a fractal: `(CO-2^C → CO-3^O) ∘ CO-0^P`. Plain English: "At every scale, the transition from cognitive abstraction to operational concretization is grounded in a stable principled identity." A disciplined craftsperson whose every act is traceable to a core ethic.
   RPM wrapping: `RPM(CO-6^O_{F5})`. Plain English: "Operational Critique driven by Agency, wrapped by the Routine/Prerequisite/Module structure." The Critique cannot execute unless its Desire and Wisdom prerequisites are already satisfied — the section-retraction guarantees the gate is one-directional.
   Involution pair: `CO-8^C ↔ CO-9^O`. Plain English: "Cognitive Expansion and Operational Contraction stand in involutional tension." Brainstorming many possibilities while executing one precise act — a healthy pair when balanced, a pathology when either side collapses.
   Dual cancellation as a law: `(CO-8 ∘ CO-9) ↔ CO-0`. Plain English: "Expansion composed with its involutional opposite Contraction returns to Identity." The antidote equation.

---

