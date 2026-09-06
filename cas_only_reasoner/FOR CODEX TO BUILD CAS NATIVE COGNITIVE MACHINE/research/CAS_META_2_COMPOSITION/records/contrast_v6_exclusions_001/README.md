# Known development exposures for the contrast curriculum

`inventory.json` records 8,053 distinct program graph signatures. It combines
the frozen exclusion lists, all three reconstructed v3 partitions, the 256-task
contrast prototype, and all partitions of the seed-926603 unit-test fixture.
Some origins overlap; their individual counts must not be added as if disjoint.

Inventory SHA-256:
`1a8f7f39bee35f14ef002dfe90f2c6760cbe5c70436c7606fad32ee03f4c1256`

Reproduction: run `C:/Python314/python.exe -B records/contrast_v6_exclusions_001/build.py`
from the CAS_META_2_COMPOSITION package in a source copy without the generated
inventory. Existing output is refused. The script installs the local validator's
neural/provider import guard before importing curriculum code. It checks pinned
historical input hashes and records current candidate source hashes.

A separate PowerShell read checked every recorded source digest and rebuilt the
union of origin signatures: 0 source mismatches, 0 graph differences, and 8,053
unique graphs. No neural model or provider was called.

Use the entire graph-signature union as explicit exclusions for a future
registered dataset. The unit-test partition named `test` is development exposure,
not an unseen evaluation. Record any additional development generations in a
new inventory version. This is an inventory of the recorded inputs above, not a
claim to discover every possible unrecorded exposure automatically.

The curriculum candidate is not yet wired into GPU training or native evaluation.
Its structural checks do not prove numerical task correctness, learned nested
composition, retention, or CAS-specific advantage. The previous composition
result remains CAS 0/72, generic 12/72, rule 72/72.
