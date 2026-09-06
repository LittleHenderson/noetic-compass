# Recorded training-input export check

The parent constructed the already exposed seed-926603 diagnostic fixture,
checked its full private dataset, and exported a separate trainer-input folder.
A fresh Python process loaded that folder with a file-open trap that refuses
`test_private.json`, and with symbolic parsing and dataset generation disabled.
It completed successfully without model, tensor, or provider execution.

Command from CAS_META_2_COMPOSITION:
`C:/Python314/python.exe -B records/contrast_v6_bundle_probe_001/run.py`

The script refuses existing outputs. `receipt.json` binds the command, source
hashes, manifest, stdout, and stderr. `stdout.txt` records the child file reads.
Manifest SHA-256:
`36e57983fd43ac9650e5946d5fd04ca0888e9013131fc450f8d9f8f3c84131a1`

The example has 96 training tasks, 24 validation tasks, and 9 diagnostic test
tasks. All their graph signatures were checked against the earlier 8,053-graph
inventory: zero uncatalogued graphs. None of these tasks is fresh evaluation.
The trainer-input directory has no private test file; its manifest retains only
that file's digest for a later evaluator. This check does not establish an
OS-level sandbox or training capability.
