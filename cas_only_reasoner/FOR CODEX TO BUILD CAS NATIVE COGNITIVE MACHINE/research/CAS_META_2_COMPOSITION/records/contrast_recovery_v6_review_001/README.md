# Independent recovery review

Preparation only until a complete, externally pinned recovery packet passes
`review.py`. The original failed training/evaluation packet remains failed.
This checker never loads a checkpoint, imports a neural framework, calls AWS,
generates a task, selects a checkpoint, edits an action, or reseals predictions.

## Inputs and command

Run from the `research/CAS_META_2_COMPOSITION` directory. Every path may instead
be supplied as a full absolute path. The source ZIP is an extensionless file.
Supply the actual recovery packet SHA and actual recovery job; placeholders are
deliberately not usable trust defaults.

```text
C:/Python314/python.exe -B records/contrast_recovery_v6_review_001/review.py
  --packet <actual recovery packet ZIP>
  --packet-sha256 <external actual recovery packet SHA256>
  --source-archive records/aws_recovery_v6_source_002
  --source-archive-sha256 54101904990bf3945dc1242e80982f05a47853a4fce56f2d9c88e9c9bb6f3bb7
  --job <actual new recovery job>
  --old-packet records/aws_contrast_v6_001/cloud_artifacts.zip
  --old-extracted records/aws_contrast_v6_001_failure_extracted
  --extracted records/contrast_recovery_v6_review_001/recovery_extracted_001
  --create-extraction
  --output records/contrast_recovery_v6_review_001/run_001
```

Join the lines into one command. Omit `--create-extraction` only when the supplied
extraction already exists and matches every byte of the supplied ZIP. A new
extraction or output must be inside this review directory and must not exist.
Failures produce `review_failure.json`; only a completed review produces
`recovery_stored_review.json` with `RECOVERY_STORED_REVIEW_PASSED`.

## Fixed trust boundary

- Recovery source: `cbf13795202094865744f7c0b5efa234451f9208`.
- Runtime eight-file manifest: `897c6a72c7411676c4ad80ac9734b3dbe7a7ac169951f58d2ab2fd6d387ecb37`.
- Original packet: `db52b01670c9864da7eeecac25c36446986c6b0b625f6d1b6310bbfdcad55def`.
- Failure admission: `d479c90f711d417f2f585b87a0b746e250db8db12029df1586a4fbabf3b82420`.

The reviewer binds 557 source files to both the source ZIP and that Git commit,
including 316 protected files. It verifies the original 879-member packet and
the failure admission before using saved tasks or actions. It independently
binds the two recovery GPU test identities, commands, raw outputs, process
receipts, source maps, worker parents, and before/after baseline records. The
original four-test execution-contract GPU gate must also be present and pass.

All 72 references and 360 arm outcomes must be present. Complete runs use the
unchanged stored verifier and source replay. Rejections must fail the unchanged
admission check and must have no native writes. The one permitted post-start
error must retain its original failure file and a closed SQLite database. Its
committed prefix gets a separate schema/document/artifact/program-prefix check;
the absent failed tick remains unverified and its compute remains unknown.
The reviewer never invokes a success-only verifier on a failed prefix.

Initial, selected, and final checkpoint files are checked as opaque bytes against
the previously admitted training receipt. No checkpoint is loaded as a model.
All native model identities must match the original packet's independently
stored-checked case-0 reference. That anchors identity; it does not rerun neural
arithmetic or prove that a forged self-consistent output was produced by a GPU.

## Diagnostic limits

Per-depth and per-condition summaries retain every attempted case. Unknown
procedure/binding/dependency scores on post-start failures stay unknown.
Literal observation bindings, named input sites, and child names are separate
diagnostics and can penalize equivalent renaming. Complete event comparisons use
the source-bound old first-difference helper. A failed prefix has only recorded
RUNs, not a full CALL/RETURN trajectory; a missing later row is not treated as a
known early return. The first recorded difference is not proof of the earliest
causal neural token. The 72 cases are 24 related triplets, not 72 independent
structures. No fresh-test, accepted-learning, CAS-specific advantage, or
automatic promotion claim follows.

## Retained pure checks

```text
C:/Python314/python.exe -B records/contrast_recovery_v6_review_001/run_checks.py --output records/contrast_recovery_v6_review_001/checks_001 --source-archive records/aws_recovery_v6_source_002 --source-archive-sha256 54101904990bf3945dc1242e80982f05a47853a4fce56f2d9c88e9c9bb6f3bb7
```

`test_review.py` and `test_report.py` use clearly synthetic placeholders only.
`check_old_prefix.py` checks the pinned original case 9, then tests corruptions
on temporary copies inside this directory. Those copies are deliberately
rehash-indexed to reach semantic checks. Original evidence is never edited.
`run_checks.py` records exact commands, raw outputs, hashes, and unchanged source
checks. It does not claim that the forthcoming recovery packet has passed.
