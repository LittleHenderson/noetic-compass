# Protected test copies: inventory, authority, backup and access, and a cleanup proposal (2026-09-24)

**Owner direction 3** (`OWNER_DIRECTION_20260924.md`): "Keep the protected copies for now. Inventory them without
exposing the answers to the builder. Identify the authoritative archive and verify its backup and access
restrictions. Prepare a specific cleanup proposal for unnecessary duplicates. Do not delete any copies under this
instruction."

**Who and how.**
- Made by the Claude coordinator (custodian). **Nothing was deleted, moved or changed.**
- Files were found by name only: `*sealed*`, `*_eval.jsonl`, `salt.hex`. They were read only to compute sha256
  and git blob ids. No content was printed or stored.
- The full per-file list (paths, sizes, hashes, matches) is **not** in the repository and is not given to
  builders. It is at `D:/tksCAS-archive/protected_copy_inventory_20260924/inventory_full.json`, sha256
  `860c52265acef92cdf70445e8dda70974e7db2d34ae9a310e14627153ca7e86e`.

**What was searched:** `D:/tksCAS-archive`, `D:/tksCAS-worktrees`, and the whole main checkout on C: (including
`_worktrees/`), skipping `.git`, `node_modules` and virtual environments.
- The count holds only for these places and these name patterns. A renamed copy, or any other disk, would not be
  found.
- Git objects and remote branches were counted separately, below.

## 1. What the protected sets are, and where their authoritative copy lives

| Set | What it protects | Authoritative copy | Other copies |
|---|---|---|---|
| **Q3 v0.1 to v0.7 held-back files** (`sealed_view/`, `visible_*_eval.jsonl`). v0.7 family G depths 4-5 is the **Q4 protected examination** | Q4's only transfer claim | **Git history.** Committed `04547c55` (2026-09-21, LittleHenderson) and present on every Helm and Q4 branch; 125 matching tracked paths per branch; 58 distinct protected blobs on `research/helm-integration-20260923` | 20 working copies (below) and 5 test-run folders |
| **HSET-1A sealed TEST** (`HSET1A_SEALED_TEST_NEW_5.json`, sha256 prefix `ae0c28a494f861ff`, 3,789,623 bytes) and its salt | Stage 1 test at 5 nodes | `D:/tksCAS-archive/hset1a_sealed_20260923/` | S3: `helm-integration/hset1a-build-20260923T154946Z/sealed.tar.gz` (439,201 bytes); a local copy of that tarball |
| **HSET-1B salt** (`salt.hex`, file sha256 prefix `82ac5c0f1fe6928b`) | the 6/7-node test, now replaced by HSET-2 (never built) | `D:/tksCAS-archive/hset1b_sealed_20260923/` | **none** |

## 2. How many copies, and where

**Totals.** 5,125 files were found by name. 3,200 of them are byte-identical to a committed Q3 protected file (43
distinct contents, 1,465.7 MB in total). 5 are the HSET archive files. 21 match another committed file with a
protected name. 1,899 match nothing protected (generated test data and older project packets).

| Where | Q3 protected copies | Note |
|---|---|---|
| 5 test-run folders on C: (`CNCM/_test_runs/peer_audit_lab_20260922`, `..._final_20260922`, `..._full_20260922`, `CNCM/_test_runs_fable_check/lab`, `CNCM/_test_runs_merge/lab`) | 292 each | leftovers from the 2026-09-22 peer audits; not authoritative |
| 18 working copies under `C:/.../CNCM/_worktrees/` | 108 each in 14 of them; 60 in `codex-helm-q3-errors` and `codex-helm-q4`; 0 in `meta1` and `vision-next` | full checkouts of branches that carry the data |
| `D:/tksCAS-worktrees/helm-builder` (**the temporary builders' working copy**) | 108 | builders are kept away by instruction only |
| `D:/tksCAS-worktrees/helm-integration` (the coordinator's) | 108 | custodian's copy |
| `D:/tksCAS-worktrees/q4-sdg` and `helm-rescorer` | 0 | partial checkouts exclude them |

**Also:**
- The main repository's git directory for these branches is on C: under OneDrive
  (`C:/.../CNCM/_worktrees/vision-next/.git`), so OneDrive syncs it.
- The branches are pushed to `github.com/LittleHenderson/noetic-compass`, which GitHub reports as **PRIVATE**.

## 3. Backup and access, as checked (read-only)

| Store | Backup | Access, as found |
|---|---|---|
| Git (Q3 sets) | many copies: GitHub (private), the OneDrive-synced git directory, every checkout | **anyone with access to the private repository, the OneDrive account, or this laptop's user accounts can read the Q4 protected examination.** Builders are kept away by instruction and by partial checkouts only |
| `D:/tksCAS-archive` (HSET sets) | D: is a fixed internal NVMe SSD (NTFS, label "Data"), not synced. The HSET-1A TEST also sits in S3 inside a tarball. **The HSET-1B salt has no second copy** | NTFS permissions inherited by every sealed folder: Administrators and SYSTEM full control; **Authenticated Users modify**; Users read and execute. Any local account can read or change it |
| S3 `cas-harness-runpod-92754088` | versioning **Enabled**, so a deletion leaves older versions | public access fully blocked (all four settings true); server-side encryption AES256; readable by any identity in AWS account `807562639912` with S3 read rights |

## 4. Cleanup proposal (NOT carried out; each line needs the owner's yes)

1. **Test-run leftovers.** Delete the Q3 protected copies under the 5 test-run folders (1,460 files). The rest of
   those folders can go too, if the peer-audit records do not cite them; check before deleting. Git holds the
   authoritative copy. These are the largest pile of unneeded duplicates.
2. **Builder working copy.** Change `D:/tksCAS-worktrees/helm-builder` to a partial checkout that excludes
   `*sealed*` and `*_eval.jsonl`, as `q4-sdg` and `helm-rescorer` already do. This removes the 108 files from the
   builders' disk without touching git.
3. **Idle C: working copies.** For each of the 14 `_worktrees` checkouts that hold 108 copies and have no running
   work, either:
   - remove the working copy with `git worktree remove`, after confirming it is clean and pushed; or
   - apply the same exclusion as item 2.
   Codex's own working copies wait for Codex's return (2026-09-28).
4. **The failed first HSET-1A tarball** (115 bytes, run `20260923T154310Z`, local and S3). It holds no test.
   Deleting it is optional. In S3, deletion only adds a delete marker, because versioning is on.
5. **Backups to ADD (not deletions).**
   - A second copy of `D:/tksCAS-archive/hset1*_sealed_20260923/`, including the HSET-1B salt, to a private,
     versioned place. For example, a separate S3 prefix readable only by the owner.
   - The same for the HSET-2 salt when it is made.
6. **Access (the owner's own setting; Claude does not change security settings).**
   - Restrict the sealed archive folders to the owner's own account: remove "Authenticated Users: modify" and
     "Users: read".
   - Optionally, keep sealed sets in an S3 prefix whose policy denies read to every role except the owner's.
7. **Future rule.** New protected sets (HSET-2 TEST, any new Q4 examination) are never committed to git. Only
   their digests are committed; the files live in the archive. The Q3 sets already in git stay there: removing
   them would mean rewriting published history, which is not proposed.
