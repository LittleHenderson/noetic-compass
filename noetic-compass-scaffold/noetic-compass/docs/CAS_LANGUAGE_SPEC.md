# CAS Language Specification

This repository contains an executable CAS language surface implemented in
`api/notation/compiler.py`.

## Scope

The implementation is a typed domain-specific language for Cognitive
Architecture System notation. It currently supports:

- Singular states: `CO-2^C_{F2}`, `CO-5^E`, `P3`, `C7`
- Typed bindings: `let thesis: state[C] = CO-2^C_{F2}`
- Expression-bodied functions with typed parameters and returns:
  `fn bridge(x: state[C], y: state[E]): relation = x -> y`
- Explicit module exports: `export let base = ...`, `export fn bridge(...) = ...`
- Imports: `use "shared.cas"`
- Binary state operators: `+`, `-`, `*`, `×`, `/`, `÷`
- Relations: `->`, `←`, `<-`, `<->`, `↔`
- Fractal composition: `∘`
- RPM wrapping: `RPM(F5)`, `RPM(CO-6^O_{F5})`
- Phi literals: `Phi<2:5:8:3:9>`, `Φ⟨2:5:8:3:9⟩`
- Programs: multiple statements separated by semicolons or newlines

## Pipeline

1. Lexing
2. Parsing into an AST
3. Static type and admissibility checking
4. Lowering to stack bytecode
5. Execution on a small VM

## Static Semantics

- `let` may declare an expected type. The compiler rejects incompatible
  expressions before execution.
- `fn` parameters may declare types. Calls are checked against those contracts.
- Functions may declare a return type. The compiler checks the body against the
  declared return, and the VM revalidates the runtime result.
- `use` imports another `.cas` file. If the imported module declares explicit
  exports, only that exported surface is brought into scope. Otherwise the
  module behaves permissively and exports all bindings/functions.
- Builtins are statically checked:
  - `dominant_state(state) -> string`
  - `dominant_domain(state) -> string`
  - `dominant_operator(state) -> string`
  - `compose(state, state) -> state`
  - `rpm_of(state|drive) -> rpm`
  - `fractal(state|fractal, state|fractal, ...) -> fractal`

## Execution Semantics

- `*` and `×` compose singular states in the same domain using operator
  composition. When the Rust `cas_engine` is available, composition uses the
  engine bindings directly.
- `/` and `÷` perform a modular difference on operators within a shared domain.
- `->`, `<-`, and `<->` construct typed relations and validate domain-descent
  constraints.
- `∘` builds cognitive-fractal operator sequences.
- `RPM(...)` evaluates whether a drive-tagged state or explicit drive reference
  has enough information to produce a prerequisite-chain result.

## Tooling

- API route: `POST /notation/compile`
- Grammar route: `GET /notation/grammar`
- CLI: `python -m api.notation.cli`
- REPL: `python -m api.notation.cli --repl`
- File execution: `python -m api.notation.cli --file docs/CAS_LANGUAGE_EXAMPLES.cas`

## Honest Limit

This implementation is a real executable DSL with grammar, parsing, static
checking, bytecode lowering, a VM, a CLI, and an API surface. It is not yet a
separate standalone Rust-first compiler ecosystem, nor a full formalization of
every CAS manuscript claim. It is the repository's working language
implementation surface today.
