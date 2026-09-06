# Exact 256-task train-only preparation

This separate adapter appends the original 256 prototype records to an externally
hash-bound v6 training partition. It does not regenerate, rewrite, filter,
deduplicate, or split those records.

The original public problem, observations, target, task ID, provenance, and
contrast-pair metadata remain unchanged. A separate import map records original
and appended indexes, pair IDs, sides, and record digests. The base training
prefix is unchanged as data; validation and both test files remain byte-identical.

Known prototype tasks are permitted training data, never fresh held-out evidence.
All 128 original pairs remain in training. Graph, observation-payload, or task-ID
overlap with any base partition is rejected, not silently removed.

## Trust and schema

Original task-file SHA-256:

    ed6bb0978d34b549917e1ea1b846091f103577936f846bc01db152b19ddbac46

Before importing checkers, Context() compares 16 frozen helper/input files with
binary Git objects at:

    acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0

The frozen parser, program validator, topology checks, original pair checker,
independent leaf comparison, and tokenizer establish structure and public meaning.
They do not establish numerical native outcomes.

The new schema is cas-meta2-prototype-training-integration/7, not a v6 manifest.
Parent bundle files are train.json, validation.json, test_public.json,
test_private.json, base_train.json, base_manifest.json, training_imports.json,
tokenizer.json, and manifest.json.

The manifest binds adapter bytes, frozen source files, original prototype file
and receipt, external base-manifest hash, data-file hashes, actual split counts
and depths, import counts, overlap checks, and train-only tokenizer. Original
gold targets are appended only to training, never to validation or test files.

## API

    merge(source, output, *, expected_sha256, seed, config, excluded, ctx=None)
    validate_bundle(path, *, expected_sha256, seed, config, excluded, ctx=None)

The merge reads a five-file v6 parent dataset and writes a new v7 parent bundle.
It refuses existing output and the live registered seed 2026092601 before reading
source data. Cold validation reconstructs the expected exact append; resealing
modified files does not bypass original-record or held-out-byte checks.

Both APIs are PARENT-ONLY and read the existing private test file. They must not
be called by a neural trainer. The companion public-only interface is documented
separately in README_PUBLIC.md when that work is complete.

The tokenizer fits only merged training problems and observation tags.
Parent checks enforce 1,024 input tokens, 256 action tokens, text round trips,
and positive action-token coverage across the existing partitions. Test-side
checks belong to the parent, not the model.

## Diagnostic use only

Local tests use only the exposed seed-926603 fixture at
records/contrast_v6_bundle_probe_001/dataset. Its expected manifest SHA-256 is:

    36e57983fd43ac9650e5946d5fd04ca0888e9013131fc450f8d9f8f3c84131a1

The intended diagnostic append is 96 + 256 = 352 training examples:
depth 1 = 32, depth 2 = 160, depth 3 = 160. Existing validation has 24 examples
and test has 9. Actual successful-run receipts establish what was produced.

A later base containing 640 training examples would become 896. This preparation
does not register that later dataset, seed, timing, or GPU launch.

## Remaining runtime integration

1. Context() requires local Git objects. A future cloud package needs
   build-verified literal pins and runtime byte checks without a Git dependency.
2. The audit context rejects preloaded neural/provider modules and installs a
   permanent import blocker. The pinned prototype builder and verifier also
   install blockers. The training process needs a separate portable context
   that retains source trust without blocking legitimate CUDA imports.
3. Output is restricted to this preparation directory. A runtime adapter needs
   explicit caller-owned output roots, no links, fresh outputs, and
   source/output separation.
4. Parent admission and the public-only trainer loader must stay separate.
   Training, validation checkpoint selection, pre-seal reload, and parent recount
   must use the correct new interface. Private test data must stay outside
   the trainer.
5. The training file has exact v6 prefix records plus exact prototype records.
   Do not simply loosen the v6 loader's strict fields and ID rules. Admit each
   source through an explicit exact rule.
6. Future source packages must include the pinned original prototype files:
   tasks.json, receipt.json, build.py, and verify.py. The v6 extra-input list
   alone does not include them.
7. Trainer, checker, evaluator, manifest, and launcher need source-bound v7
   dispatch and exact count/step registration. Accepted model/executor bytes and
   the frozen v6 experiment must remain unchanged.

No model, inference, provider, or paid launch runs here. A valid data bundle is
not a learning result. The previous CAS 0/72 held-out result and the separate
24/24 familiar-program result remain unchanged.

## Verified local result

checks_002 passed **41 tests**, with no failures, errors, or skips.
Pytest took 19.29 seconds; the full guarded wrapper took 20.274417399999948
seconds. The 16 frozen helpers/assets and adapter bytes were unchanged.
No generator, model, tensor, provider client, or paid launch was used.

The actual saved bundle is under:

    checks_002/positive_merge/bundle

| Partition | Tasks | Depth 1 | Depth 2 | Depth 3 | Depth 4 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Training | 352 | 32 | 160 | 160 | 0 |
| Validation | 24 | 8 | 8 | 8 | 0 |
| Test | 9 | 0 | 0 | 6 | 3 |

Its training list contains the unchanged 96-record base prefix followed by every
original prototype record, in original order. All original public problems,
targets, observations, IDs, provenance, and contrast fields compare exactly.
All three held-out files compare byte-for-byte with the original base files.

Manifest SHA-256:

    19162857679b3eb2e698c58ee8e0ac5dc3c7ffe7265e11e8ae1c726834067f29

Dataset ID:

    737f37d91a262a4603f02950defbfb8f9360fdc7b72615ff0ad945461e4d530b

Test receipt SHA-256:

    452c95cd78faf5a9df4a0213f84e6edcff444a7edba39abdfacfebc2c4daf0fe

The train-only tokenizer fitted exactly 352 training public inputs.
Maximum input lengths were 469 training, 457 validation, and 409 test tokens.
Maximum target length was 107 action tokens in each split. No input was
truncated. Tokenizer SHA-256:

    90e46b1640e532e6da9c126b30bd31a3bdc6d7b4c644b384ad4705df4d42615e

Tests include dropped, changed, reordered, duplicated, or split prototype
records; changed base-prefix data; wrong observation bindings; pair identity
changes; validation/test leaks; graph, observation, and ID overlap with every
base partition; altered tokenizer claims; wrong external manifest hashes;
existing-output refusal; forbidden neural/provider imports; generator traps;
and the live-seed refusal. Resealed malformed outputs still fail semantic
reconciliation.

## Retained unsuccessful attempt

checks_001 reached its declared 600-second timeout. Its child was observed
using CPU, but no JUnit or pytest scratch output appeared. The exact expensive
function was not observed. The first wrapper lacked timeout-output capture;
its missing raw child output is recorded explicitly, not replaced by invented
empty logs. Original runner/test bytes and a timeout observation are retained.

The retry changed only the test harness: a verified short retained homebase
scratch directory, early progress markers, timed stack dumps, timeout capture,
and test-output placement. Adapter semantics and bytes were unchanged. The retry
passed in about 20 seconds. This shows that the revised test setup works; it does
not identify the old expensive function or prove a unique root cause.

The short scratch path is recorded in checks_002/receipt.json. It was explicitly
approved under the homebase _tmp directory; source and durable outputs remain
under this preparation record.

## Reproduce the bounded checks

From the META2 package, invoke the absolute run_checks.py path with a new name:

    C:/Python314/python.exe -B <this-record-directory>/run_checks.py --run-name checks_new

The wrapper uses only the saved seed-926603 fixture and records commands, raw
outputs, source identities, and the retained scratch path. Existing results are
not overwritten. The adapter's standalone command interface also supports
merge and validate with explicit --source, --manifest-sha256, --seed,
--config-json, and --exclusions-json arguments; merge additionally requires
--output. The 41-test receipt verifies the merge and cold-validation Python APIs,
not a separate standalone adapter CLI invocation.

For portable parent integration, check the externally bound base manifest and
its internal seed before opening its task payloads. The present preparation
rejects an explicit seed-2026092601 request before reads, but otherwise gathers
the base files before its full manifest admission. The recorded use reads only
the known seed-926603 fixture.

