# Post-run audit correction: file ordering, not changed experiment data

The first full packet-inspection attempt rejected the packet with
`ORIGINAL_INDEX_PREFIX_MISMATCH`. It did not create a successful inspection
receipt or change the original ZIP. The source-run identity remains
`b5f1718e63a2b5cf72b4b606d513d0524b9226ac`.

The frozen AWS collector in `aws/launch.py` uses `sorted(Path(...))` on Linux.
That orders path components. The original inspector sorted complete strings.
For the full run, `cloud_job/campaign/…` and `cloud_job/campaign.log` expose the
difference. The first mismatch was index position zero. The earlier failed
smoke packet did not contain this file/directory-prefix case.

All 2,475 collected files were independently read from the unchanged ZIP and
hashed. They total 604,953,583 uncompressed bytes. The collection receipt is an
additional ZIP member, so the complete packet has 2,476 members.

- Whole-string reconstruction: prefix mismatch; index SHA256
  `8a4b73198523b2667029e166ca235b3b0bec01d450f67693ac5e87cbb241464a`.
- Linux path-component reconstruction: every retained prefix entry matches;
  full index SHA256 matches the original recorded value
  `18023d6e2fec6f7a11dbb18631db50784e3d0e7da684f6a3f72ac531378935f5`.
- Unchanged packet SHA256:
  `e22412583114e50cbf9e60d8b22864bfb4ca76e6ccecedee7a0f72976ec37ae0`.

The local inspector now explicitly uses `PurePosixPath` ordering to reproduce
the frozen Linux collector on Windows. It still checks every included byte,
the complete index hash, omissions, source identity and all original gates.
There is no fallback that ignores an index mismatch.

`tests/test_packet.py` now builds fixtures in the actual collector order. Two
new tests cover this prefix conflict and reject a substituted whole-string
index. The focused run passed **38 tests**. Its one warning is the intentional
duplicate ZIP-member rejection fixture.

The corrected full inspection then passed with no issues:
`records/aws_full_002_inspection/inspection_receipt.json`. Its independently
written full member inventory has SHA256
`8320c5983bd9db722b5e8be38ff08988fea24710fdfaa83f0e0092c010276fcd`.

This is a post-run audit-tool correction. No cloud training source, learned
checkpoint, recorded prediction, native execution, ZIP member, or original
collection receipt was changed. Native stored-record verification remains a
separate gate; file-integrity success alone is not task correctness.
