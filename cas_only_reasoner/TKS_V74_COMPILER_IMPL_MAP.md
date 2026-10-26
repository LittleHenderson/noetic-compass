# TKS v7.4 Compiler/VM Implementation Map (Draft)

Scope:
- Canonical authority: v7.4 track files (CoreCalculus, Semantics).
- Concrete language/VM spec: v7.3 Compiler track (syntax/AST/IR/bytecode/VM).
- v6.1 manual used for notation compatibility (noetic ^, fractal << >>, Unicode fractal).

Goals:
- Implement full v7.4 compiler/VM in Rust.
- Static types + effect rows/handlers (no dynamic typing).
- ASCII output defaults; accept ASCII and Unicode tokens.

## Canonical Sources
- TKS_v7.4_CoreCalculus.tex: core calculus, RPM monad, fractals, noetics, foundations, core operational rules.
- TKS_v7.4_Semantics.tex: domain-theoretic semantics (dcpo, Scott continuity, Kleene fixpoints).
- TKS_v7.3_Compiler.tex: concrete syntax, AST, type/effect system, IR, bytecode, VM, modules, FFI.
- TKS_FORMAL_MANUAL_v6.1_CLEAN_DEFINITIONS.md: notation alignment (noetic superscripts, fractal Unicode/ASCII).

## Lexical Tokens (v7.2 + v7.3)
- v7.2 core tokens: ELEMENT, NOETIC, FOUNDATION, INT, BOOL, IDENT, LAMBDA, LET, IN, IF, THEN, ELSE,
  RETURN, BIND, CHECK, ACQUIRE, ACBE, FRAC_OPEN/CLOSE, COLON, LPAREN/RPAREN, ARROW, EQUALS,
  PLUS, MINUS, TIMES, DIVIDE, LANGLE, RANGLE, COMMA, EOF.
- v7.3 additions: OMEGA, ORD, LIMIT, SUCC, TRANSFINITE, LOOP, EFFECT, HANDLE, WITH, RESUME, PERFORM,
  HANDLER, OP, MEASURE, SUPERPOSE, ENTANGLE, QSTATE, AMPLITUDE, BASIS, ORDINAL_LIT(alpha),
  LBRACE, RBRACE, PIPE, BANG, UNDERSCORE_OMEGA.
- Ordinal literals: omega, omega + n, omega * n, omega ^ n are lexed as ORDINAL_LIT or desugared.
  epsilon_n and aleph_n forms are supported by ordinal atom parsing.
- Foundation literals: numeric subfoundation (e.g., 3d) and prefixed F3d are both accepted.
- Unicode mapping (canonical): lambda, arrow, double arrow, bind, omega, epsilon, aleph, nu_k,
  ket/bra, tensor; ASCII output is default with Unicode accepted as input.
- Fractal aliases: ASCII << >> and Unicode fractal open/close are accepted as FRAC_OPEN/CLOSE.

## Concrete Syntax
- v7.2 core grammar summary (compiler track).
- v7.3 extensions:
  - Effect declarations: effect Name [T...] { op name(params): type; ... }.
  - Handler declarations: handler Name : EffectName -> Type { return x -> e; op(a) k -> e; }.
  - Handle/perform expressions: handle e with { ... } or handle e with HandlerName; perform op(arg).
  - Resume expressions: resume(expr) (syntactic form for continuation resumption).
  - Transfinite fractals: <k1:k2:...>_ordinal(expr) with optional ellipsis.
  - Ordinals: omega, epsilon_n, aleph_n, succ/limit, +, *, ^ (right-associative exponent).
  - Transfinite loops: transfinite loop i < ordinal from e step (x -> e) limit (f -> e).
  - Quantum ops: measure, superpose, entangle, ket/bra and braket.
- Quantum superpose forms:
  - superpose { amp: |v>, ... } (amp:ket form).
  - superpose[(amp, |v>), ...] (tuple list form).
- Compatibility extensions (canonical notation from v6.1):
  - Support noetic application suffix: expr^k (alias for nu k (expr)).
  - Accept fractal ASCII: <<k1:k2:...>> (alias for <k1:k2:...>).
  - Accept fractal Unicode: \u{0192}Y"1:4:7\u{0192}Yc (alias).
  - ASCII output defaults to ^ and << >>.
- Precedence/associativity notes (v7.3 compiler track):
  - Handler nesting is right-associative: handle e with h1 with h2 == handle (handle e with h2) with h1.
  - The effect-row "|" is not an operator; it separates row tail variables.
  - Ordinal exponentiation is right-associative.

## AST (v7.3)
- TopDecl: LetDecl, TypeDecl, EffectDecl, HandlerDecl.
- Effect signatures: OpSig name input output.
- HandlerDef: return clause + op clauses (op(arg) k -> body).
- Expr: v7.2 forms + Handle, Perform, Resume, Ordinal forms, TransfiniteLoop, Quantum forms.
- Handler: named handler ref or inline handler definition.
- Type: v7.2 types + effectful types, handler type, ordinal type, QState type.
- EffectRow: empty, cons, or row variable (row polymorphism).
- All nodes carry source locations; post-typecheck annotations add effect rows per AST node.

## Type System
- Hindley-Milner inference + unification (v7.3 compiler track).
- Types: Int, Bool, Unit, Void, Element[W], Foundation, Domain, Frac[k], RPM[t],
  function, product, sum.
- Effectful types: tau ! epsilon, tau1 -(epsilon)-> tau2, Handler[E, tau_in, tau_out].
- Effect rows: {} | {E1, E2 | r}, with row polymorphism; rows are order-insensitive and idempotent.
- Effect row subtyping: fewer effects can flow to more effects (pure is a subtype of any).
- Ordinal-indexed types and constraints: type-level ordinals and bounded quantification.
- Quantum types: QState[t], ket/bra as values (per compiler track).
- Effect boundary safety: imported/exported signatures must respect declared effects.

## Core Semantics (v7.4)
- Noetics: 0-9 operators (monoid; 0 is identity).
- Foundations: 7 foundations, 28 subfoundations; foundation application updates acquisition state.
- RPM monad: return/bind/check/acquire semantics (state transformer with failure).
- Fractals: sequence of noetics, iteration, fixpoint (Kleene).
- Domain-theoretic basis: dcpo + Scott continuity; Kleene fixpoint for fractal convergence.
- Map semantics to VM instructions for noetic application, fractals, RPM effects.

## IR (effect-aware ANF)
- IRVal: var, literal, lambda, element, noetic, ordinal, ket.
- IRTerm: return, let, app, if, perform, handle, resume, rpm ops, ordinal ops, quantum ops.
- Handler IR carries effect name, return clause, op clauses; effect annotations preserved.
- ANF transformation per compiler track; handler clauses lowered to continuation-aware IR.

## Bytecode + VM
- Instruction set groups: core stack ops, TKS domain ops, RPM ops, effect ops,
  transfinite ops, quantum ops.
- VM state: (code, pc, stack, env, frames, handlers, heap, acquisition alpha,
  ordinal register, qreg).
- Handler stack entries: effect name, handler addr, env, return clause, op clauses.
- Continuations capture stack + frames + handler stack up to delimiter.
- Handler ordering: innermost handler (most recent) handles first; commutativity not assumed.
- Ordinal runtime: Cantor Normal Form with succ/add/mul/exp/lt/isLimit.
- Quantum runtime: QState values, superposition lists, measurement collapse.
- Heap objects: closures, ideas, fractals, handlers, continuations, qstate.

## Module System + Artifacts
- Source: .tks
- Interface: .tksi
- Object: .tkso
- Module syntax: module, export, import (qualified/aliased/selective/wildcard).
- Export items include values, types (abstract/transparent), effects, submodules.
- Separate compilation: module graph, interface loading, signature checking.
- Standard modules (canonical): TKS.Core, TKS.Noetics, TKS.RPM, TKS.Fractals, TKS.Quantum, TKS.FFI.*.

## FFI
- external "C"/"stdcall"/"fastcall"/"system" fn ...
- safe/unsafe annotations; effect annotations on externs.
- Optional attributes: link directives and explicit symbol names.

## Implementation Status (Current)
- Implemented: noetic apply (expr^k alias + IR Noetic form), quantum ops (AST/IR forms + opcode definitions),
  ordinals (parser + symbolic bytecode/VM ops), tkso (encode/decode + roundtrip tests),
  GPU compute scaffold (tksgpu crate + tks gpu subcommand).

## Open Questions / Spec Gaps
- Precedence/associativity for ^ suffix vs nu form (define in parser).
- Ordinal literal surface syntax beyond omega (epsilon/aleph) vs generic ordinal expressions.
- Resume as a syntactic form vs ordinary function (parser support + VM semantics).
- Effect row equality/normalization rules in the implementation (order, duplicates).
- Mapping of v7.4 fixpoint/fractal semantics to VM execution model.
- Full Unicode token support beyond fractals/nu (lambda, arrow, omega, bra/ket).
- Module signatures, link directives, and @symbol attributes (FFI) are not implemented yet.
- Default standard library and effect set (IO, RPM, quantum, filesystem).
