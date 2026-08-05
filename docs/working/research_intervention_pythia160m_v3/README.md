# Pythia-160M research intervention V3 startup successor

V3 corrects only the V2 isolated-interpreter package-path failure. The V2
lock, consumed receipt, consumed nonce marker, and terminal failure packet
remain byte-exact, quarantined, non-reusable, and bound into the V3 successor.
The model, tokenizer revision, prompt split, intervention map, seeds, compute
cap, controls, endpoints, thresholds, harm floors, and audit rules are
unchanged.

The exact startup contract uses:

`C:\Python314\python.exe -I -B`

Python isolated mode intentionally ignores user-site discovery and
`PYTHONPATH`. After the standard-library bootstrap validates the exact
interpreter hash, flags, bootstrap, lock, package root, package entrypoints,
executor/auditor, and preserved V2 evidence, it explicitly inserts:

`C:\Users\wakil\AppData\Roaming\Python\Python314\site-packages`

The preauthorization fixture then installs the compatible zero-network guard
and imports only `torch` and `transformers`. It cannot load a tokenizer or
model, create a receipt, query or use a GPU, or create research output.

The future execution branch remains disabled and fail closed. It requires a
separately authorized, fresh V3 one-use receipt and new nonce. Receipt,
current-commit, output-absence, and stale-nonce validation plus create-once
nonce consumption still occur before any framework import. No V3 receipt
exists and no V3 run is authorized.

Current status:

`V3_SUCCESSOR_LOCK_LOCAL_PASS / RUN_NOT_AUTHORIZED / RESEARCH_ONLY / OPEN / NOT_LICENSED / NO ACCEPT / NO PRODUCTION EFFECT`

Claim boundary: startup compatibility only. No live steering, safety or
prompt-injection defense, Gate 2, `ACCEPT`, `LICENSED`, production readiness,
or production-result claim is enabled.
