# Pythia-160M research intervention V2

V2 is the preparation-only successor to the immutable V1 prospective lock.
It adds a disabled Pythia-specific executor, an independent standard-library
auditor, exact environment/compute manifests, and a numerically complete
wrong-axis control. It does not create a receipt or authorize a run.

The executor imports only the Python standard library at module import time.
Its sole `torch`/`transformers` import path is ordered after:

1. explicit research feature enablement with the live flag false;
2. exact successor-lock and frozen-file validation;
3. a future fresh one-use owner receipt;
4. current source-commit, expiry, output-absence, and stale-nonce validation;
5. create-once nonce consumption; and
6. installation of the compatible zero-network guard.

Model and tokenizer loading is local-only from
`EleutherAI/pythia-160m@50f5173d932e8e61f858120bcb800b97af589f46`.
Output creation occurs only after those gates and successful model load.

The independent auditor does not import the executor or any framework. It
reconstructs the exact request matrix, raw hashes, no-op equivalence, signed
dose response, random/wrong-layer/wrong-token/wrong-axis controls, wrong-sign
reversal, utility/fluency/collateral-safety floors, patch-back, compute cap,
and claim boundary.

Current status:
`EXECUTOR_AUDITOR_MODEL_FREE_PASS / RUN_NOT_AUTHORIZED`.

GPT-2 remains outside this lock as a later separately authorized comparison.
No live worker, product-decision, Evidence Packet `ACCEPT`, safety steering,
prompt-injection prevention, Gate 2, `LICENSED`, production-readiness, or
production-result claim is enabled.
