# Corrected retrospective comparison source

Source commit: `9f562c761c7cb84c767673b2fab735cdd031b499`.
Archive SHA-256: `3230d805b665b91f1191d423342bb591cfb1fd69cd677fbe49206cf50b8729bd`.
Archive size: 11,616,824 bytes; 495 source/input files plus the launch manifest.

The change explicitly selects the two AWS decoder tests. It does not change
model checkpoints, either decoder, the accepted executor, dataset, evaluator,
budget limits or evidence collection rules. The source also includes the
first failed job's byte-only inspector, which remains pinned to that old job.
It is not an inspector for this new source/job.

Guarded local validation: 1,214 test functions and 178 subtests passed, zero
failures, eight GPU modules skipped. All 316 protected baseline files stayed
unchanged. See `../local_ablation_gpu_selection_fix_v4_001/receipt.json`.
This does not prove GPU execution or improved model outcomes.

`cold_check.py` checks source, archive, launcher identity and budget without
provider or neural execution. Its receipt is the evidence of whether that
check completed; this note alone does not certify the package.

The comparison remains retrospective and inference-only. It cannot claim a
fresh held-out result, new training, accepted learned memory or a CAS-specific
advantage. Preserve both failed and subsequent results.
