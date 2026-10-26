# Excluded bulk tree — `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE`

Status: **kept on disk, deliberately not committed.** GitHub rejected the push twice, and both rejections were about
size, not content.

## Why it is excluded

1. First push: the tree contains a Git-LFS object and the repository's LFS budget is exhausted.
2. Second push: the tree contains files larger than GitHub's hard per-file limit of 100 MB. The largest are four
   ~695.7 MB objects (two git bundles, one LFS cache object, one pack) plus a 272.7 MB `artifacts.zip`.

GitHub cannot accept this tree. Committing it again would break every future push.

## What is kept where

- The full tree remains at
  `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/` in the working tree, unmodified.
- It is excluded from tracking through `.git/info/exclude` (a local, non-committed exclusion), so `git status` stays
  clean and no future commit re-adds it by accident.
- The tree's small text records that matter for the project narrative are also summarised in the spec sheet's
  §7.20–§7.43 entries, which are committed.

## What is therefore not in the repository

The research artifact tree itself: source archives, publication clones, worktrees, pytest scratch runs, and the
LFS-cache objects. Anything in it that is cited as evidence by a committed document is cited by path; the path is
valid on this machine but not in the remote repository.

## Options if the owner wants it versioned

1. Raise the repository's Git-LFS budget and remove the >100 MB files, then push the remainder.
2. Archive the tree to the S3 bucket already used for run evidence (`cas-harness-runpod-92754088`) and commit a manifest
   with object hashes.
3. Keep it local and treat it as workstation evidence, as with the CTT checkpoints.

None of these was done in this commit; this note exists so the exclusion is a recorded decision rather than a silent
loss.

## Update 2026-10-25 23:27 PDT — archived to S3

The deduplicated documentary tree was uploaded to `s3://cas-harness-runpod-92754088/bridge-control-20260822/for-codex-tree-20261025/`: **6,112 unique files, 2.55 GiB, 0 failures, 485.7 s**. The manifest with every path, size and SHA-256 is committed at `docs/working/FOR_CODEX_TREE_S3_MANIFEST_20261025.json` and stored beside the objects as `_MANIFEST.json`. Excluded from both repo and archive: `_worktrees`, `_tmp`, `_test_runs`, `github-lfs-cache`, `node_modules`, `__pycache__` and nested `.git` (the bulk of the 56.66 GiB), which remain on disk only.
