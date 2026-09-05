# Frozen-source workspace alignment for the native memory demo

The first local launch command for source `8b5d8ac9e4f469b4cd89bbe917560678d2f52cb7`
stopped before provider calls or budget reservation with:
`LAUNCH_REFUSED:LOCAL_SOURCE_ARCHIVE_IDENTITY_MISMATCH:research/CAS_META_2_COMPOSITION/README.md`.
No job receipt directory was created. The command was the documented launch
command in `aws_native_demo_source_001/PRELAUNCH.md`, with `--execute`, the $400
cap, default profile, subnet `subnet-0eb3ca4bf5ca98f24`, and receipt directory
`records/aws_native_demo_001`. This was not an AWS job or a paid retry.

The source check was correct: the root agent had just updated the status README
in evidence commit `d5978613`. All other 446 source-manifest files still matched
the original bundle. The latest status text has SHA256
`bb2529cf8d89b96df1681f735ffc82ebf9f7d433ad9e9e9471103f8283fd6cb5`.
It remains preserved in that commit and the current learning result remains
documented in META2 `records/aws_learning_v2_001/RESULT.md`.

Only that agent-authored README change was temporarily reverted in the working
tree, using a patch. Its resulting bytes match source 8b5d8ac9 exactly:
`53c07976cadc8a381298097f569ad643993d50caa90b29593abb38e2877e42ec`.
`git diff 8b5d8ac9e4f469b4cd89bbe917560678d2f52cb7 -- README.md` was empty.

The frozen README bytes were retained through the source-bound packet inspection
and stored-result audit. The latest status text was then restored exactly to
HEAD `d5978613aff5d4d6fdc803e9b6360c774c28b441`, with SHA256
`bb2529cf8d89b96df1681f735ffc82ebf9f7d433ad9e9e9471103f8283fd6cb5`.
The restored file's last-write UTC is `2026-09-05T23:11:00.0293234Z`; its hash and
empty Git diff were independently checked at `2026-09-05T23:11:36.4835567Z`.
The temporary source alignment was not staged as a rollback.
No code, frozen check, published archive, baseline, or budget path was changed.
New future-learning source files are not in the frozen archive or demo imports.
The original $400 campaign ledger remains the sole budget authority.

## Isolated stored audit

The unchanged auditor's active-checkout attempt encountered new untracked
learning-v3 modules through its source glob and rejected that source environment.
A sparse detached checkout of the actual source commit was therefore used at:

`C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta3_audit_8b5d8ac9`

It contains no budget ledger. Its first two audit attempts correctly rejected
three metadata files converted to CRLF by the Windows checkout configuration:

- `CAS_CJT_TRANSFORMER_v0_2/artifacts/.gitattributes`.
- `CASFORMER_v0_3_META_LOGIC_WIP/.gitignore`.
- `CASFORMER_v0_3_META_LOGIC_WIP/records/.gitattributes`.

For each file, the Git source blob, pinned source ZIP, original active checkout,
and protected manifest agreed on LF bytes. Only those three isolated-checkout
files were mechanically normalized to LF. This corrected checkout bytes, not
source content or manifest authority. All 316 protected hashes then matched
before and after the unchanged audit. Git reports no content diff; system
`core.autocrlf=true` can convert these metadata files again if Git rewrites them.

The fresh `aws_native_demo_001_stored_audit_clean_003` run passed at
`2026-09-05T23:09:56.286338+00:00`. Its receipt and exact command were copied
byte-for-byte to [the active-checkout evidence directory](../aws_native_demo_001_stored_audit_clean/README.md).
The original active-checkout rejection and both earlier isolated-checkout
rejections remain unchanged, with preserved copies alongside the passing receipt.
No source code, old receipts, extracted inputs, or cloud packet was changed;
the retry performed no provider calls or neural work.
