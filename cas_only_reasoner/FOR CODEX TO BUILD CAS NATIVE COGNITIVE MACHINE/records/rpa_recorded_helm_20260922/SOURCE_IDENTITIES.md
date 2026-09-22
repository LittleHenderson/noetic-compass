# Saved Helm source identities

Final source check, 2026-09-22: the selected original records and pins match. No concrete backend/source mismatch was found. This check did not run a model.

## Saved run

- Model: **Helm 2.0-experimental**, uncertified; no upgrade claim.
- Job: `cas-meta2-tpntr-20260920210258-20208c92-m-20260917`.
- Original worker source commit: `20208c923d41c24614504d4ecc2b289ecb66eda8`.
- Retained repository snapshot: `5b3d713c5e7f2b2fc2959aaf776d0d80ca09d256`.
- Validated document SHA-256: `088b1d4f83d5533003860d028c6247ed88a03b620021ff64421a61a6fa166271`.

Original paths below are relative to repository directory `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/`. They identify Git blobs; sparse checkout files need not be materialized. Exact extraction locations and selected-file pins are in `source_selection.json`.

## Original file pins

Each raw byte length/hash was checked against its original Git blob and the separately retained original artifact manifest.

| Original path | Bytes | Raw SHA-256 |
|---|---:|---|
| `records/typed_pointer_001/receipt_20260917/checkpoints/development_p10_predictions.json` | 115,188 | `9cdf1825f155a12f38cd07828da7a5cc94823a6950313840f0c6796f9e57d638` |
| `records/typed_pointer_001/receipt_20260917/checkpoints/development_p10_scoring.json` | 62,488 | `1594c9f1a42cda34fc4645476e65ca839e1d22f548888347c9ead19ff5b4730d` |
| `records/typed_pointer_001/receipt_20260917/checkpoints/final_checkpoint.json` | 30,879 | `2f4bfbd1c61f5814fc91a17430ce9d89447c603654c7bc48754f928b82fc1c89` |
| `records/typed_pointer_001/receipt_20260917/checkpoints/loaded_sources.json` | 24,849 | `9709df9e7e763bd26d24968d7f03866baee9a3e12633752d5f7f82614c71bffa` |
| `records/typed_pointer_001/receipt_20260917/checkpoints/model_identity.json` | 4,234 | `7438a2b0110e190f932a182e7820820337fe37fe3588d2e94a4ce2ee752f43d4` |
| `records/typed_pointer_001/receipt_20260917/checkpoints/protocol_material.json` | 16,182,588 | `cfa3e9d13cf1a234b1b617f205aa132ad79d9e1816cf23de316f0366c4b8dfed` |
| `records/typed_pointer_001/receipt_20260917/checkpoints/worker_report.json` | 89,492 | `f41544105902ad874a1f71dfd9dae98f93996ffd7755581d3386637a09c70d0a` |
| `records/typed_pointer_001/receipt_20260917/collected/results/artifacts/manifest.json` | 12,679 | `437e57e504f27979acfc85e56b87e8b52d4586c69576ad9a9a1da84618f77e46` |

## Selected development examples

Only the original development packets/admissions and matching development-p10 predictions/checks are exported. The development disclosure declares `split=development`, `final_questions_constructed=0`, and `main_targets_constructed=0`. Each original public input includes 64 training-bank worlds and one development focus world. The complete packet and a separate readable focus-graph projection remain accessible.

The full protocol file is retained by hash, not copied into the viewer. Protected main/final target files were not opened or exported for this work. Historical nonexposure claims remain limited to the retained inventory.

The first correct and first wrong saved examples were selected after scoring, for illustration. The pair is not a new benchmark or a 50% performance claim: the complete original development-p10 receipt reports **2 correct out of 59**.

### Correct example

How is Dev1Node1 reached from Dev1Node7? Original answer: **VIA via Dev1Node2**; original checker `correct=true`. Separate replay answer: **VIA via Dev1Node2**.

- Record: `typed-input-4da592b0a8f7e97ed48493432a4735913acf77e1cd99d1116db4882b287499b8`.
- Query: `typed-query-f007ca4fb949f128299efe6bad948593acbf589cc005c183a3d7ee79f934c9ed`.
- Prediction: `typed-prediction-d3f26f9c1bb8a5331eadd5f76299a6d50757b63ae0adf5ae243948fedfbbb855`.
- Packet digest: `ae873fb8041d0afaad1b69385d189367127e78819499766a093227f5fa1d0de1`.
- Saved check digest: `19d8f5d9676c8b327a3f74f23f19ffd9fe2d6e0990eab4633e4412591def391f`.
- Saved target digest: `72dbd45e1da5ce20738bd9bb59b2cbfa04cd7c57cbfc0b8bb04189943aacc411`.

### Wrong example

Which nodes does Dev1Node7 directly contain? Original answer: **(no nodes)**; original checker `correct=false`. Separate replay answer: **Dev1Node2**.

- Record: `typed-input-0cd5786cbec5560790abdf15217d9e0f28a7af62109171832a7d816670dea864`.
- Query: `typed-query-8ba3957637452c9145ed9e3f2bd31b2ff0128e685069b59b447a645d9b96c797`.
- Prediction: `typed-prediction-bcbc0aa4c1a4dc6fc1f5f3490ddb18a0aee6fc24d848b9109496be8e6483ec8f`.
- Packet digest: `48574790c67423fe05363fcc21079d8ce73ef5d9ee50f0b6043b0fb162cff7e1`.
- Saved check digest: `cd01fbc744b210e528b75a718bf38b74e3fd04aa96c05fc725d4aa876477334d`.
- Saved target digest: `437f682230c80527d055148264fd6a01ad29c567b4d60e27618de4d082d000fd`.

The wrong prediction remains the original empty node list. The checker-derived `Dev1Node2` does not replace it. Both use focus world `world-684620458740010349dd5179b29ff9b6f814313df6787ddd535f5cc335d1763e`.

## Checkpoint and model join

Both predictions have model revision `1470` and run-context digest `bfee0e7c0a36ed6b7e46b6b32f7d4bd0637fef07464737f403659e601dcb881d`, matching the saved final-checkpoint metadata and original job. The original packet/admission digests and prediction/checker IDs also match.

- Checkpoint: `records/typed_pointer_001/receipt_20260917/checkpoints/final.pt`; `3,670,007` bytes.
- Raw SHA-256: `c6c49e982c408ced7cae47935f34708e14794d2fcc9789b1bce7900db5bd4ffb`.
- Recorded model-state identity: `c6d0f95d68740834199684cd706ad385ccb040dd91eb13781e60d14ba3cd1ed6`.
- Recorded encoder-state identity: `15d3ba3557aa8fb6142e0497d7978de798fef775dffb41080fc87798e139eae4`.

The retained Git checkpoint bytes were hashed at selection and during the final check; both matched the original metadata and artifact manifest. The checkpoint was not decoded, unpickled, loaded, or executed, and is not included in the export. Internal state identities above are preserved metadata, not independently recomputed tensor hashes. The viewer displays original saved inference records; it does not reproduce inference or establish current runtime availability.

## Checker source and replay

These original source-commit bytes match their historical `loaded_sources.json` receipts (`COMPILED_FROM_VERIFIED_SOURCE_BYTES`) and local `pinned_checker/` copies.

| Original path | Bytes | Raw SHA-256 |
|---|---:|---|
| `research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/source.py` | 20,601 | `13c265e576dd027362611ca0956ac9f1e6285945cb7e626cef9270c2d08a9337` |
| `research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/answers.py` | 13,894 | `4d4cf21b65914c5b6878b58a52ab3cfe2f8864b319a3bb5ad1b95c6780686e5c` |
| `research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/focal.py` | 15,105 | `cd2761b5c5dced4af5e4acc0a6b55a384555b2cb9bb3b90442f8673d1754e70a` |
| `research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/checker.py` | 13,934 | `57ac0a9f78c46999fac444fc974d3c1b718435b583cbc48701be74c56efa971e` |

The adapter executes only these four verified pure checker modules. It replays `check_answer(public, query, answer)`, compares the complete original saved check after adding the original record/prediction IDs, and separately derives/checks the target digest. This deterministic development check is displayed separately from original inference and original checker results. It produces no learned prediction.

## Validation and limits

- External selection anchor: `source_selection.json`, SHA-256 `d181782419e3480a7f8b39e2bc3bce7eaa28cde21c44bb9abcd0c021bfcd7daf`. Its exact selected-file pins bind `selected_records.json`, `saved_identity.json`, and the original `artifact_manifest.json`.
- The trusted adapter reconstructs the entire document from those anchored sources. Changing a record and recomputing the outer digest cannot replace the baseline. Cached checker reuse still verifies source bytes. Wire decoding bounds size, structure, number tokens, duplicates, and nonfinite values.
- Hashes provide retained local integrity, not external authentication or independent proof that historical inference occurred. Replacing trusted code and its source anchors can establish another baseline.
- The fixed present is an archived run record. Navigation changes focus/reference, not that record. Links represent saved-record associations; the shared checkpoint keeps one identity. They are not an internal thought trace or execution graph.
- All ten nodes have `profile40=null` and `profile_basis=null`; the validated payload has `profiles={}` and `calculations={}`. No CAS profile, coordinate measurement, or CAS-Ohm quantity was assigned or inferred. Internal thought traces were not recorded.
- Correctness is relative to the original supplied-graph checker semantics. No new model, training, cloud job, live Helm control, certification, or Q4 neural acceptance is claimed.

## Performed source check

The final read-only check compared the seven original JSON files and manifest with their raw pins; joined both selected packet/admission/prediction/checker objects to the originals by record ID; compared selected identity metadata with originals; hashed checkpoint bytes without decoding; compared the four checker files to original source-commit bytes/loader receipts; and loaded/revalidated generated `workbench/helm.json`, including absence of profiles/Ohm calculations.

Outcome: `ORIGINAL_RECORD_EXTRACTION_AND_PINS_MATCH`. Tests and browser evidence are recorded separately. This report is not a fresh neural run or external audit.
