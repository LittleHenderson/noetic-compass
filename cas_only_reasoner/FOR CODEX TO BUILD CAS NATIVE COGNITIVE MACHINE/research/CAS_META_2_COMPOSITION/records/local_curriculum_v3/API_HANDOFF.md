# Curriculum v3 handoff

The pure curriculum is ready for integration. This is not a trained-model result.
No registered seed 20260919 targets were generated locally.

## Registered calls

```python
from cas_meta2.curriculum_v3 import (
    DEFAULT_COUNTS, DEFAULT_SEED, registered_development_exclusions,
    write_dataset, validate_manifest, validate_dataset, dataset_identity,
)

extra = registered_development_exclusions()  # frozenset: 177 exposed graphs
manifest = write_dataset(
    new_output_directory,
    seed=DEFAULT_SEED,
    counts=DEFAULT_COUNTS,
    excluded_graph_signatures=extra,
)
validate_manifest(
    manifest, expected_counts=DEFAULT_COUNTS, expected_seed=DEFAULT_SEED,
    excluded_graph_signatures=extra,
)
```

Explicitly pass the same `extra` set to every identity, generation, and audit
call. Registered seed 20260919 fails before target construction when the
combined exclusions omit any development graph. The asset loader does not
silently alter small development fixtures.
The base set has 4,312 graphs; the development set has 177, including one
already in the base. The registered union is 4,488 unique graphs.

The default counts are train 3,072, validation 96, and test 72. Training has
1,024 tasks at each call depth 1, 2, and 3. Validation has 32 at each depth.
Testing has 24 matched triplets: `same_depth` at depth 3, `wording_shift`
with the same formal target and input, and `deeper_calls` at depth 4 with
nonempty extra nesting. Every procedure uses the explicit ABC scope because
the existing public sentence language cannot state scope variations. The
separate general grammar still supports its full published scope language.

## Files and withholding

`write_dataset` creates only a new destination, writes `train.json`,
`validation.json`, `test_public.json`, `test_private.json`, and
`dataset_manifest.json`, then rechecks the actual cold-loaded partitions.
The public test partition contains only `problem` and `observations`; it does
not include task IDs, targets, or provenance.
The public manifest does not report held-out target-token or binding counts.
`validate_manifest` does not open partition targets.

After predictions are sealed, the stored auditor can reconstruct:

```python
dataset = {
    'schema': 'cas-meta2-curriculum/3',
    'seed': manifest['seed'],
    'dataset_id': manifest['dataset_id'],
    'splits': {
        'train': train_rows,
        'validation': validation_rows,
        'test': test_private_rows,
    },
}
checked = validate_dataset(dataset, excluded_graph_signatures=extra)
```

Use the manifest's four exact partition-byte hashes as well. Full validation
rechecks source identity, all exclusions, split separation, the permitted
matched-triplet overlaps, each public problem's independently parsed meaning,
explicit public definition order, real call depths, positive training-token
coverage, and float32 input uniqueness. It checks construction and target
contracts, not actual native outputs. The native evaluator remains required.

## Portable source assets

`dependency_receipt()` byte-checks the four frozen helper modules, the two
exclusion assets, and binds this new module's own hash. It does not claim Git
or runtime identity. The development asset separately binds the original
local exposure-record hash; runtime loading needs only the two source assets.

- Base asset SHA256: `2e11f0e0e5a8cb8bc32907f81cc4c8a02c59f8623ce8f9b5937c59d421050f48`
- Development asset SHA256: `4642f5c1c5a9fc078343cdc5fb99c042ec6ee3c7e2e2c971ee5965776ab71913`
- Curriculum source SHA256: `75ad59cd42a57eb88c5680b26cf07255c24d36132658ffd91926ccafdf5e987c`

## Local evidence boundary

62 tests passed with neural and provider imports blocked. Only the three
existing tiny diagnostic seeds were reused: 914701, 914702, and 914703.
The final rerun exposed exactly the same 177 graph signatures as the original
record; that record was not overwritten. See `registration_guard_receipt.json`
and `tests_registration_guard.xml` for the exact source and result hashes.
The earlier local receipts remain preserved.

No neural execution, native execution, AWS actions, commits, or training
integration were performed by this subtask.
