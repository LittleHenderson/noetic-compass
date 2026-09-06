# Exact reconstruction of the omitted dataset

The guarded reconstruction completed successfully. All five generated files
match the hashes from the original v3 dataset manifest and preserved input ZIP.
The missing training file is recovered without altering the frozen generator.

- Train: 3,072 tasks; validation: 96; test: 72.
- All 461 source-package files checked before and after, unchanged.
- Local child blocked neural and provider imports; no model was loaded.
- Exact command, timing, hashes, stdout, stderr and builder hash: `receipt.json`.
- Existing dataset constructor also checked its cold JSON reload.

These are the original exposed tasks. This does not restore the missing native
execution databases from the failed v3 run, accept that run, demonstrate model
learning, or establish fresh held-out performance. It supplies the exact dataset
needed by the unchanged evaluator for the planned retrospective comparison.

The script refuses to overwrite its dataset or receipt. To independently repeat
the reconstruction, use a separate record directory and preserve the relative
placement under this project's records directory.
