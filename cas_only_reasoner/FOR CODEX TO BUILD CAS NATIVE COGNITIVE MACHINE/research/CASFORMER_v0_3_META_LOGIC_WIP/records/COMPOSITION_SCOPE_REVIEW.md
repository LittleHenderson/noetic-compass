# Internal composition review, 2026-09-05

This is a development review, not a new GLM audit or release acceptance.
The tested source checkpoint is
`fda27bcff9c38af5941a15433db6ae7d59bf0d9a` on
`research/casformer-v0.3-meta-logic-wip`.

## Owner input

The latest supplied specification is
`C:\Users\wakil\.codex\attachments\e707bf14-75fa-4590-9fc3-b775d48ad575\pasted-text.txt`.
Its SHA-256 is
`23440a19c8ee10611112e8d9e61e4a7e9c7f7222e8093bed54abf27a3cfb0ed5`.

The build interprets this as authorization for one small callable procedure,
not for all Noetics, Foundation semantics, training, or pulsating memory.

## Resolved findings

- The original fifth demo tick performs learning. The new comparison uses an
  explicitly documented inference-only adaptation; it does not claim learning
  equivalence or the original changed-output demonstration.
- Extra initial-input artifacts changed later native receipt identities.
  Only not-yet-durable artifacts are now supplied to each native call.
- Completed executors now recheck model and native-head bindings before
  reporting their saved result again.
- Checkpoint writes enforce the same size limit as checkpoint reads, before
  replacing an existing checkpoint.
- The schema now includes a unique run ID in every call-instance ID; the old
  format without that identity is rejected.
- Source hashes and Git HEAD must remain unchanged throughout the evidence
  run. Installed package bytes are checked against the preserved wheels.
- Stale-checkpoint restart is explicitly tested after later native progress.
  The older checkpoint must not erase or replay the already committed B step.

## Deliberate limits

Only fixed-weight, authored-oracle execution is covered. Native persistent
Bias is per CJT, while call-frame bookkeeping is per invocation. Accepted
native steps remain durable when later work fails. The shared ledger measures
reserved native policy units, not measured FLOPs or wall time.

Restart is supported at clean checkpoints. Atomic recovery between the native
database and the separate checkpoint file, concurrent owners, arbitrary
self-recursion, procedure retrieval, learning isolation, and matched generic
recursive controls remain open.

The prior v0.2 full-release evidence is preserved and checked for integrity.
Its 250/89/181+403 regression counts are not represented as newly rerun here.
The final new-run commands, counts, hashes, environment, and demo result are in
`validation/receipt.json` and its companion records.
