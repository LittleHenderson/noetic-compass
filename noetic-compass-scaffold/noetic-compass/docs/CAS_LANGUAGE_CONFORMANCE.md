# CAS Language Conformance Notes

This document records what the current repository implementation can honestly
claim about the CAS language surface.

## Implemented

- A published BNF grammar in `docs/CAS_LANGUAGE_GRAMMAR.bnf`
- Lexing and parsing to an explicit AST
- Static type checking for:
  - state, drive, string, function, fractal, rpm, relation, program, any
  - typed `let` bindings
  - typed function parameters
  - optional typed function returns
  - builtin arity and argument contracts
- Bytecode lowering
- Execution on a stack VM
- Module imports with explicit exports
- CLI, REPL, and API access
- Automated tests covering:
  - valid and invalid relations
  - typed contract enforcement
  - RPM and fractal execution
  - module import cycles
  - export-controlled module surfaces
  - cached module re-imports
  - end-to-end showcase program execution

## Honest Limits

- This is an executable DSL and compiler/interpreter surface inside the current
  repository. It is not yet a standalone language ecosystem with its own package
  manager, optimizer, or Rust-native frontend/backend pipeline.
- The runtime is Python-based, with selected semantic hooks delegated to the
  Rust `cas_engine` bindings when available.
- The language is strongly specified relative to the current implementation, but
  not yet backed by a separate formal metatheory proof.

## Reproduction

From the repository root:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m api.notation --mode run --file docs\CAS_SHOWCASE_APP.cas
.venv\Scripts\python.exe -m api.notation --grammar
```
