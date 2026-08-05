# Pythia-160M V4 receipt-gated execution preparation

Status: `EXECUTOR_AUDITOR_MODEL_FREE_PASS / RUN_NOT_AUTHORIZED`.

This directory adds the real-model executor, isolated bootstrap, independent
artifact auditor, environment inventory, compute manifest, and successor
execution lock for the already-frozen V4 all-12-layer diagnostic.

The executor is disabled by default. It validates the exact lock and every
frozen model/split/control/code binding, validates a fresh receipt and absent
output, consumes the nonce, and installs the zero-network guard before any
framework import. The tokenizer and model load after those gates, and the
output root is created only after a successful exact local CPU model load.

No receipt or nonce exists, no framework/model/tokenizer was loaded, and no
model experiment or output was created by this preparation.
