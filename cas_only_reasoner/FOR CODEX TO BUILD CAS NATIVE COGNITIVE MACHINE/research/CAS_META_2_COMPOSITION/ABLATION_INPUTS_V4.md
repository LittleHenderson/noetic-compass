# Restricted prediction inputs for the retrospective comparison

`cas_meta2/ablation_inputs_v4.py` reads the exact preserved input ZIP, pinned by
byte length and SHA-256. It returns only requested checkpoint bytes, tokenizer,
checkpoint/training metadata, or public problems. Requests for private answers,
previous predictions, unknown names, or duplicates are rejected before opening
the artifact. It performs no extraction, model loading, training, or provider call.

The complete compressed artifact is hashed, but private targets and earlier
predictions are not decompressed or parsed. Tests instrument ZIP reads to check
that boundary against the real input artifact. This API is not an OS sandbox:
the eventual prediction process must receive only the allowed staged files.
It does not defend against a separate concurrent writer changing an open file.

## Evaluator integration finding

The unchanged `campaign_v3.evaluate_sealed` validates train, validation, and test
partitions before native execution. The retained partial packet includes
validation data but omits `dataset/train.json`; the small input ZIP intentionally
does not contain the full dataset. Therefore that ZIP alone cannot run the frozen
evaluator. Do not bypass its dataset validation.

Reconstruct the full dataset with the unchanged `curriculum_v3.write_dataset`,
seed `20260919`, and `registered_development_exclusions()`. Require exact matches
to all original partition hashes and the dataset manifest before evaluation.
In particular, the original training JSON hash is
`579a1bfdda64702b4357f57b75c9c9b6e0710a9262c1da41d5aeec1ca1404359`.
The reconstruction was executed successfully in
`records/decoder_dataset_reconstruction_v4_001/`: all four partition files and
the manifest match their original SHA-256 hashes exactly. The guarded child
completed in a parent-measured 27.55 seconds; all 461 frozen source files matched
before and after. No neural execution or provider call occurred. The rebuilt
data remains retrospective and is not a new held-out split.

The eventual AWS predictor must reuse the frozen checkpoint loader's model,
tokenizer, source, epoch, and configuration checks with an explicitly recorded
path relocation. Seal both sets of predictions before the separate evaluator
opens private targets. No comparison has run yet. This is retrospective decoding
diagnosis, not new training, fresh held-out evidence, or release acceptance.
