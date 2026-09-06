# Public-only v7 training inputs — preparation only

`public_data.py` exports and loads the exact-256 training extension. It does not
train a model, run the executor, approve a GPU job, or complete the v7 pipeline.
The accepted v6 code and original 256 records are unchanged.

## Boundary

The parent bundle has nine files, including `test_private.json`. The exporter
first calls the parent validator, which checks private test targets. It then
copies only these eight files into a new trainer-input directory:

- `manifest.json`
- `train.json`
- `validation.json`
- `test_public.json`
- `base_train.json`
- `base_manifest.json`
- `training_imports.json`
- `tokenizer.json`

The loader refuses any extra file. It never constructs a private-test file path,
opens or hashes private-test bytes, derives test programs, or calls the parent
validator. This also applies on reload and checker paths. It compares the private
file digest only as opaque, externally pinned manifest metadata. Private test
depths and graph separation remain parent-checked facts, not checks replayed by
the public loader. The returned receipt says so explicitly.

Training and validation targets are allowed inputs. They are checked as programs.
The test input remains public observations only. The tokenizer is rebuilt from
the merged training examples only and must exactly match the saved tokenizer.

## Exact data admission

Two record formats are allowed: the frozen v6 base format and the exact original
prototype format. This is not a general relaxation of the v6 loader. Training
must be exactly the retained base-training prefix followed by all original 256
records in their original order. The loader checks the complete import map,
record identities, original provenance, actual train/validation depths, and
retained base manifest. No records are filtered, rewritten, or regenerated.

The original records have SHA-256
`ed6bb0978d34b549917e1ea1b846091f103577936f846bc01db152b19ddbac46`.
They are old, exposed training examples, not fresh evaluation evidence. The
loader rejects their graph overlap with base training or validation and their
observation overlap with every public split. Private-test graph exclusion is
admitted through the pinned parent validation, without parsing public tests into
gold programs. There is no graph-wide exclusion exemption.

Only two count configurations are admitted:

| Configuration | Merged training | Training depths 1 / 2 / 3 | Validation | Public test |
| --- | ---: | --- | ---: | ---: |
| Saved diagnostic seed `926603` | 352 | 32 / 160 / 160 | 24 | 9 |
| Proposed full-size shape, with a different seed | 896 | 128 / 384 / 384 | 96 | 72 |

Seed `2026092601` is explicitly refused. Accepting the proposed count shape does
not register its seed, approve execution, or prove its data exists. At batch size
16 and 200 epochs, 896 examples mean 56 batches per epoch and 11,200 optimizer
steps per policy family. The job budget and timing must be checked separately.

## API and external trust

```python
export_training_bundle(
    source, output,
    expected_sha256=merged_manifest_sha256,
    seed=seed,
    config=config,
    excluded=excluded,
    expected_loader_sha256=registered_loader_sha256,
    parent_ctx=None,
    root=source_root,
)

bundle = load_training_bundle(
    output,
    expected_sha256=merged_manifest_sha256,
    seed=seed,
    config=config,
    excluded=excluded,
    expected_loader_sha256=registered_loader_sha256,
    root=source_root,
)
```

Both SHA-256 arguments are required external pins. The runtime wrapper must check
the loader's registered hash before importing it; checking a file against a hash
read from that same mutable file is not an external trust check. The merged
manifest pin binds the source map, retained v6 base, file hashes, and import map.

The loader returns exactly `train`, `validation`, `test_public`, `tokenizer`,
`manifest`, and `receipt`. The receipt includes:

```text
private_labels_read_by_loader = false
test_programs_parsed_by_loader = false
parent_validation_replayed_by_loader = false
private_test_depths_recounted = false
private_test_graph_separation_replayed = false
neural_execution = false
```

The exporter returns that receipt plus the parent validation result, export
directory, and `training_performed = false`. Its default parent context is
local-only: it needs the parent's Git objects and validation dependencies. It
restores import hooks and search paths added by its own invocation. A caller can
supply an independently checked parent context. This module does not implement
or prove a portable parent context.

## Source packaging still required

The public loader directly hashes the frozen helper bytes before import and
again before return. It does not run Git, instantiate `adapter.Context`, install
import blockers, or import a neural or provider library. It can coexist with an
already imported neural library; this was checked with a placeholder, not CUDA.

The source package must include `public_data.py`, `adapter.py`, and every exact
file named by `FROZEN_FILES` in `public_data.py`. That closure contains the pure
v6 curriculum/data helpers, their dependencies, and all four original prototype
assets under `records/contrast_curriculum_v6_probe_001/`:

- `tasks.json`
- `receipt.json`
- `build.py`
- `verify.py`

These raw files are bound to frozen source commit
`acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0` through the externally pinned parent
manifest's source map. The prototype builder and verifier are hashed but never
executed by the public loader. The versioned trainer, checker, launcher, source
archive, experiment specification, and exclusion inventory need their own
complete source binding. This helper alone does not supply those gates.

## Checks run

From the `CAS_META_2_COMPOSITION` directory:

```powershell
C:/Python314/python.exe -B records/prototype_training_integration_v7_001/test_public_data.py
```

Result: **18 test methods passed**, 28.429 seconds, exit code 0. These tests use
temporary copies of the existing saved seed `926603` fixture and exact original
256 records. No new graphs, current campaign results, registered-seed data,
models, tensors, GPU work, or provider calls were used.

Coverage includes the real parent merge/export, exact records and counts,
train-only tokenizer reconstruction, changed-byte and changed-import rejection,
external pins, strict JSON, source changes, and repeat loading. A fresh Python
process blocks private-file access, program parsing, parent validation, Git, task
generation, and neural/provider imports while loading the public bundle. Import
and reload also check that search paths and import hooks remain unchanged.

These are local, pure-data checks. They do not prove model learning, CUDA
execution, a complete portable release, or successful cloud training.
