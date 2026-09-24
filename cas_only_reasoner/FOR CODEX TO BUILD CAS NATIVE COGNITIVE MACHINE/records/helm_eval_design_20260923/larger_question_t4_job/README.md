# Larger-question path: the AWS T4 check job

**Label: CLAUDE_BUILT_CLAUDE_CHECKED.** Built by the temporary Claude builder on 2026-09-23/24. **Dry-run only. Not
launched. Not reviewed.** Limits and authority: `JOB_LIMITS.md`.

## What it is for

In plain words: the larger-question path lets Helm take 5- and 6-node questions. Its checks need torch and a GPU,
so they run on one AWS T4 machine. This folder is the job that would run them.

- It runs `research/CAS_META_2_COMPOSITION/eval_paths/t4_larger_question_checks.py` from
  `claude/helm-builder-continuation-20260923` at `e05889ee` (builder revision 2).
- It checks plumbing only. Nothing here measures Helm's accuracy. Any accuracy statement is NOT LICENSED by it.

## Files

| File | What it does |
|---|---|
| `launch.py` | Builds the bundle from git objects at the pinned commit, checks it, and (for the runner only) uploads it and starts ONE machine. `--dry-run` does everything except upload and launch |
| `job.sh.template` | The machine's script: three kill switches, stage 0 smoke, then the script (stage 1 preflight, stage 2 checks d, c, b, a), then upload and shut down |
| `watch.py` | Watches the machine, terminates it at the client deadline, downloads results, confirms "terminated" and no leftover volume |
| `read_results.py` | Restates the script's own verdict after checking the files are whole and belong to the launched bundle: the machine's own `identity.json`, bundle sha256 and wheel hashes must equal the launch record, and the cleanup record must name the same instance and launch time (codex-0007). Strict exit: 0 only for `ROUTE_ACCEPTED`; 3 when the job passed but the route is not accepted; 1 otherwise |
| `test_read_results.py` | 20 small synthetic tests, with a mismatch-negative case for every binding: `python -B test_read_results.py` |
| `JOB_LIMITS.md` | Authority, machine, time and money limits, with the arithmetic |
| `dry_run_machine_script.sh`, `dry_run_record.json` | The output of the dry run below (links are `https://DRY-RUN/...` placeholders) |

## Lessons carried over from the analogy T4 job

- Attempt 1 there lost its verdicts: a file the probe read beside itself was not bundled. Here the file list comes
  from the pinned script's own `--list-inputs`, and the launcher refuses if:
  - any listed input is missing or differs from its bytes and sha256;
  - a bundled tool reads a file beside itself (`HERE / "..."`) that is not bundled;
  - any project import in any bundled file does not resolve inside the bundle;
  - the script's import closure reaches a module that is not bundled (only the standard library, torch, numpy and
    the two wheels' modules may be outside).
- One machine, no automatic retry, a launch record that blocks a second launch, a watcher that confirms
  termination and lists leftover volumes.

## The dry run (2026-09-24, on the laptop)

Command: `python -B launch.py --dry-run` (default machine `g4dn.2xlarge`). Exit 0. Output, in short:

- **Bundle: 259 files, 10,230,760 bytes, sha256 `2410f269a46d0a80...`**
  (`2410f269a46d0a8024c7709976557aa1734b7e577cc6cfdb9e9909c53393bd36`). The bundle depends only on the pinned
  source commit, so the same command gives the same sha256.
- 12 inputs checked against `--list-inputs`; 241 `.py` files in the two source trees (77 in `cncm`, 164 in
  `cas_meta2`); 5 `eval_paths` files; `identity.json`.
- 1,518 project imports resolved. The script's import closure has 96 modules; outside the bundle it reaches only
  `cas_cjt`, `casformer` and `torch`.
- One sibling read found and bundled: the fixture file.
- **Worst case: $1.6639** (g4dn.2xlarge: 0.767959 USD/hour x 130/60 hours), ceiling $3.00.
- Image `ami-07d69ce07bfe5628f` is available ("Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 24.04)
  20260922").
- The one AWS call was `ec2.describe_images` (read-only). Nothing was uploaded; no link was made; nothing launched.

## How the runner would use it (not done by the builder)

```text
python -B launch.py --dry-run          # check again; the bundle sha256 should be 2410f269...
python -B launch.py                    # upload and start ONE machine; writes launch_record.json
python -B watch.py                     # until the machine is gone; writes watch_record.json and results/
python -B read_results.py              # writes RESULTS_READING.json; exit 0 only for ROUTE_ACCEPTED
```

The runner writes a `RUN_LOG.md` after the run, as the analogy job did.

## Open questions (for the coordinator; not decided by the builder)

1. **Review.** This folder needs its own review before launch (the verification's note V5).
2. **Machine size.** `g4dn.2xlarge` is the default because check a compares bits with history recorded on that
   machine type. `g4dn.xlarge` would fit (one process, 16 GiB) and cost less (worst case $1.1742). Which one?
3. **Budget.** Does this job's spend count toward the $60 comparison ceiling?
4. **Setup downloads.** Like the analogy job, the machine installs `uv` from `https://astral.sh/uv/install.sh`
   and torch from the PyTorch cu128 index. The versions are pinned; the installer script itself is not.

## EXPOSURE (builder of this folder)

- Read in the research-branch working copy: the analogy job's `launch.py`, `job.sh.template`, `watch.py`,
  `read_results.py`, `JOB_LIMITS.md`, `RUN_LOG.md` (whole files) and `launch_record.json` (image, limits and the
  six checkpoint sha256 values only); `OWNER_STANDING_AUTHORIZATION_CLAUDE_20260924.md`; the start of
  `docs/OWNER_RUN_AUTHORIZATION_20260922.md`; the file lists of two commits.
- Read through git objects at `e05889ee` by `launch.py`: the bundled files listed above (hashed and parsed for
  imports; not interpreted otherwise). File names only: the two source trees and `eval_paths` (no name contains
  "sealed", none is an `*_eval.jsonl`).
- Not opened: any `results/` or `attempt1/` folder, any `*sealed*` file, any `*_eval.jsonl`, `D:/tksCAS-archive/`,
  any salt, the meta1 ledger, Claude transcripts. No torch, no GPU, no training. The only AWS call was one
  `describe_images`.
