# Push preflight — NOT_PUSHED

The existing remote is `https://github.com/LittleHenderson/noetic-compass.git`.
`git push --dry-run origin HEAD:refs/heads/codex/cas-meta-2-composition`
returned exit 0 and advertised creation of the branch. A subsequent live
`git ls-remote` still found no such branch. A dry-run uploads no commits and is
not a completed push or a server-side large-file validation.

Before the new handoff commit, 399 commits were unreachable from locally known
origin refs. Their 5,652 unpublished blobs total 829,393,814 uncompressed bytes.
One blob exceeds the ordinary GitHub limit:

- Path: `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/aws_ablation_v4_002/cloud_artifacts.zip`
- Git blob: `a61aca911fdd5a7ef1dc0e3db8d46d5e864b0a89`
- Size: **136,120,962 bytes** (greater than 100 MiB = 104,857,600 bytes).

[GitHub's current documentation](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)
states that regular Git uploads block files larger than 100 MiB. This is a
documented preflight blocker; no real push was attempted or reported rejected.

A later deletion commit cannot remove the large blob from the history being
uploaded. Publishing needs a deliberate archival/LFS and history-migration
plan that retains original evidence and the old commit identities used by
receipts. No history rewrite, evidence deletion, LFS purchase, or migration was
performed. The current source/evidence branch and original archive remain intact.
