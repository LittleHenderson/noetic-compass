# V7 exclusions from the failed v6 experiment

This is an exposure inventory, not an evaluation result. The v6 experiment generated training, validation and test tasks before native evaluation failed. All those graph signatures must be treated as known when constructing future fresh tasks.

This separate tool leaves the completed-success inventory builder unchanged. It reuses only that builder's pure combine function after checking its exact bytes against commit 80e44f20a3f2c66a62754212729ce6e11ff9c8fe. It never calls the success-only build entry point.

## Fixed inputs

- Failed review: records/contrast_failure_review_v6_001/run_002/failure_review_receipt.json
- Failed review SHA-256: d479c90f711d417f2f585b87a0b746e250db8db12029df1586a4fbabf3b82420
- Original failed packet SHA-256: db52b01670c9864da7eeecac25c36446986c6b0b625f6d1b6310bbfdcad55def
- Prior 8,053-signature inventory SHA-256: 1a8f7f39bee35f14ef002dfe90f2c6760cbe5c70436c7606fad32ee03f4c1256
- Frozen source: acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0
- Frozen source archive SHA-256: 3153318664641ea3affdbef306929c3113bb937cd04113bce41d02f736e0f1f1
- Literal original 256-task file SHA-256: ed6bb0978d34b549917e1ea1b846091f103577936f846bc01db152b19ddbac46

The fixed failure receipt, packet and source archive are checked before dataset reads. All 538 frozen source inputs and 316 protected files are checked before program-helper imports. Every extracted packet member is checked against the bound inventory. Dataset file hashes are also bound to the manifest and completed training gate. Program depth and graph signatures are independently recounted from saved targets; no tasks are generated.

Each prior origin remains unchanged. All actual v6 train, validation and private-test graph signatures are added, with per-split task counts, depth counts, unique graphs, unique graphs by depth and source-file hashes. All 256 literal prototype graphs are explicitly recomputed and checked against both the old and new inventory.

## Use

From CAS_META_2_COMPOSITION:

    C:/Python314/python.exe -B records/contrast_v7_exclusions_from_failed_v6_001/run_checks.py
    C:/Python314/python.exe -B records/contrast_v7_exclusions_from_failed_v6_001/build.py

Both commands require new output files. The tests use synthetic, in-memory records and do not read the actual failed-run dataset.

The build writes inventory.json with schema cas-meta2-known-exposures/7 and receipt.json with input pins, actual counts, source identity and output hash. The receipt captures program argv; execution_command.json also preserves the exact executed command including the Python -B flag. Future fresh curriculum generation must receive this new inventory with its actual SHA-256.

The completed build contains 8,837 unique graph signatures: all 8,053 prior signatures plus 784 additional signatures from 640 training tasks, 96 validation tasks and 72 test variants (48 unique test graphs). Every prior origin and all original 256 prototype signatures are preserved.

Inventory SHA-256: 9f579ea2d593671dfddf16db39aa22563d6b98f7388758d2a2b99539e66ed623

Build receipt SHA-256: a965297027e5ba1c1a2340bb9f9c40d52297debd91af5c4e4fab57065a5d6267

All 16 pure test methods passed. Their exact subprocess command and raw outputs are retained under checks_001/.

The entire union is excluded from fresh training, validation and test construction. The original 256 tasks may enter training only through the separate exact-byte training-only append. Their signatures must never be subtracted from fresh exclusions.

No graph generation, neural import, checkpoint loading, provider execution, native-success claim or automatic learning acceptance is performed. The recovery admission receipt and extracted packet are read-only and unchanged.
