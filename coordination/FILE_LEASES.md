# Q1 file leases issued before implementation

Issuer: Q1-Codex. Actual Codex thread: 01a0e385-db6e-7a71-beca-f6ef3a6c5e04.
Workspace: C:/Users/wakil/HELM-Q1/q1-offline-20260927.
Namespace: HELM-Q1. Branch: codex/helm-q1-offline-20260927.

| Owner | Exclusive writable paths | Acceptance |
| --- | --- | --- |
| Q1-Codex | helm_quantum/ except compiler/; tests/test_contracts.py, tests/test_classical.py, tests/test_cli.py, tests/test_backend.py; schemas/; fixtures/public/; config/; evidence/; SOURCE_INVENTORY.json; README.md; AGENTS.md; .gitignore; .gitattributes; coordination/codex/; coordination/FILE_LEASES.md | Accepted by this thread; START recorded |
| Q1-Claude | helm_quantum/compiler/; tests/compiler/; semantics/; coordination/claude/ | Issued, ACK and START not observed |
| Q1-DeepSeek | review/; coordination/deepseek/ | Lead-authored local ACK/START read; session ID not exposed; remote access not yet confirmed |
| New ChatGPT-Q1 manager | coordination/manager/ | Lead-authored local ACK/START read; session ID not exposed; remote access not yet confirmed |
| Nobody | input_package/; incumbent source, jobs, sessions, worktrees | Read-only evidence / outside Q1 scope |

Each lead uses an isolated working copy of this exact branch. Do not patch another
lead's files. Report findings to the owner, who fixes their source. Do not write
another lead's ACK. A Git publication does not wake or dispatch a model.

Compiler imports may use contracts, admission and fixtures/public only. They must
not import classical.py, vendor/, verifier.py or evaluator receipts to construct
the predicate or tune its schedule. Tests may compare independent behavior.

No host runtime slices are admitted in packet 1. No hidden/protected tests,
checkpoints or upstream history are dependencies. Host changes stay with their
incumbent owner. Job-store and budget implementation remain Codex-owned later work.
