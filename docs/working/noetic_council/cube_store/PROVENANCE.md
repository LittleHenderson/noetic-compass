# Provenance Manifest: `cube_store`

Created 2026-10-18. Implements `SPEC_CUBE_STORE_UNIFIED_20261018.md` extending `Cube_Node_Schema_v0.1.md`.

## File Digests (SHA-256)

| File | SHA-256 Digest | Status |
| :--- | :--- | :--- |
| `cube.py` | `f8133f83afbd55727ed42549ef0b83f637d9bbe9608f32cdc9646cd9c70ad23a` | Complete (Logical record contract & validation: assertion & valence split, polarity deprecated) |
| `operations.py` | `75a210eadfd1180f987107ec9a4afd25f3b0d7a834596addb3f35e099d496a9d` | Complete (`LIST_PARTS`, `FIND_SHARED_PART`, `REACHED_VIA`) |
| `store.py` | `9fcb9027a494f84c4b52762e728c5b80926d1ffd87c90c7e227b6c41dd3d2245` | Complete (Persistence, source gating, visibility filtering) |
| `turn.py` | `1fe686dc3b28df98b71eae5634761dfa935ff66e3995b5bee46a5dd6255c81f4` | Complete (Pipeline, kinds, assertion, valence, pantry READ, polarity deprecated, receipts) |
| `test_all.py` | `91ec14d8a170e016e24bcfa80029f006cd94ac2cc7044afc4ee4200bb23b2540` | Complete (19 acceptance & bite-check cases) |
| `RESULTS_20261018.md` | `60bb9ec7c38e5313f39e1e43a4e56560b96001bee80412c34940484566e14bec` | Complete (Execution summary & live probe results) |
| `README.md` | `115de7109263125ae858780a0e3ba1326e670ba87ccbb476a19bc85c17a35475` | Complete (Claim ceiling verbatim & honest lexical claim) |

## Vendored / Referenced Packages
- `language_v3/cce.py`: Parser, valence polarity reference, and exact render twin.
- `Cube_Node_Schema_v0.1.md`: Underlying node schema, core and six face definitions, visibility separation (`LearnerView` / `TeacherTarget`).
