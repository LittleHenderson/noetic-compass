# Learned candidate writer — fresh GPU reader still pending

`cas_meta3/learned_writer.py` runs a fixed, data-only child process to save a
candidate and records its actual process ID, exit code, request digest, source
identity, output digests and saved database digest. It does not launch a GPU
reader, promote a skill or train a model.

The request supplies the package, external trust anchors and all five raw
learning-evidence files. Inputs and outputs must be beneath this META3 directory's
`records` or `runs` directories; links and replacement outputs are refused.
The existing handoff and store recheck the evidence before saving. A failed
child keeps stdout, stderr and an unsuccessful process receipt; there is no
automatic retry. The child blocks neural and provider imports.

Python entrypoint:

```python
run_writer(request_path, request_sha256, process_output, timeout_seconds=120)
```

This is only the writer half of the process boundary. A later AWS launcher must
check its exit receipt and saved bytes before starting a distinct GPU reader,
then bind the actual reader process, source identity and execution outcome.
That integration and real learned-candidate reuse remain unverified.

Tests in `tests/test_learned_writer.py` use synthetic learning evidence, including
a real successful child and a real rejected child. Their process results are
real; the supplied learning records are fixtures, not model learning evidence.
Generated test input and process files are retained under
`records/writer_test_inputs/`. The first validation record caught a test fixture
using a Python set where the request requires a JSON list; it is retained.

The active META2 training package, accepted executor and baseline weights are
unchanged. No new AWS instance is launched by this module.

## Verification

`records/local_learned_writer_002/receipt.json` records 624 passed tests,
zero failures/errors/skips, 55.95 pytest seconds and 57.4348314 runner seconds.
All tested source files and 316 protected baseline files remained unchanged.
All 461 files in the separate live META2 source package were also rehashed and
unchanged. The earlier failed run is retained in `local_learned_writer_001`.

Rerun from META3, selecting a new output directory:

```powershell
C:/Python314/python.exe -B tools/validate_local.py --output records/local_learned_writer_003
```
