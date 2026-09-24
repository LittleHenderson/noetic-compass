# Unchanged-arm reproduction admission: builder report

**Label:** `CLAUDE_BUILT_CLAUDE_CHECKED`. Built by Claude as the temporary builder while Codex is away.
It is not an owner signature. It is not reviewed yet.

**Status:** built and committed. **Not launched.** No AWS call. No money spent.

## 1. What this is

The owner approved plan HELM-REPAIR-CONTROLLED-1 (commit `197caa32`). Its option C says:
re-run Helm 2.0 seed 20260917, then compare the new `final.pt` with the old one.

This folder holds the tools for that one job:

| File | What it does |
|---|---|
| `prepare_unchanged_repro.py` | Freezes the one job (owner, request and authority records). Launches nothing. |
| `read_reproduction.py` | After the run, prints `REPRODUCES`, `DOES_NOT_REPRODUCE` or `INCOMPLETE`. |
| `repro_common.py` | Shared pins and checks. Imports nothing from the launcher. |
| `test_unchanged_repro.py` | 30 pure-Python tests. |

The job: seed 20260917, source `20208c923d41c24614504d4ecc2b289ecb66eda8`, the full 10-pass schedule,
the committed package `package_20208c92`, the same launcher, g7.2xlarge, $15.00 booking, no automatic retry.

## 2. Decide this before launch: the plan's test cannot pass

**The finding (checked in the code, not guessed):**

- `final.pt` is one `torch.save` file. It holds the weights **and** a `metadata` block
  (`pointer_learner.py`, `export_checkpoint`, lines 2045-2082 at `20208c92`).
- That block stores the **job name** (`run_identity.context.run_id`, set at `cncm/typed_pointer_worker.py` line 872).
- It also stores **`elapsed_seconds`**, a stopwatch reading (`pointer_learner.py` lines 1837-1838).
- A re-run must have a new job name, because the job name is also the AWS bucket name.
- A re-run cannot take the exact same number of seconds.
- So the new `final.pt` file bytes differ, and so its sha256 differs, **even if every weight is identical**.

**What this means.** Under the plan's rule as written, this $15 job will read `DOES_NOT_REPRODUCE`.
That answer is known before the run. The plan then triggers option B: two more jobs, $30 more in bookings.

**What I did.** I built the reader exactly to the plan's rule. I did not change the rule; only the owner can.
The reader also prints, as **non-deciding** information, whether the weight-only fingerprints match.
These are `model_state_identity`, `optimizer_state_identity`, `encoder_state_identity` and `rng_state_identity`.
They are stored in `final_checkpoint.json` and do not include the job name or the time.
The training code does switch on deterministic GPU maths (`use_deterministic_algorithms(True)`, TF32 off,
a fixed torch and GPU check), so equal weights are possible. They are not proven.

**The owner's choice (plain words):**
- keep the rule: then this job's answer is already known, so skipping it and going straight to B saves $15; or
- change the rule to "the weight fingerprints are equal": this is a change to the signed plan, so it needs
  the owner's written approval before the job runs.

## 3. The exact hash it compares against

| Item | Value |
|---|---|
| Helm 2.0 seed-17 `final.pt` sha256 | `c6c49e982c408ced7cae47935f34708e14794d2fcc9789b1bce7900db5bd4ffb` |
| Size | 3,670,007 bytes |
| Helm 2.0 job | `cas-meta2-tpntr-20260920210258-20208c92-m-20260917` |
| Commit | `c8d5c430eec23a8fadd98bbcd045fecf03d86239` (the commit that added the Helm 2.0 receipts) |
| Folder | `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/typed_pointer_001/receipt_20260917/` |

Three committed records state that hash, and the reader requires all three to agree:

| Record in that folder | Blob |
|---|---|
| `collected/results/artifacts/manifest.json` (the worker's artifact list, row `final.pt`) | `d98b25aa6b8022da9ad7f1b2c90c8799ea5b5827` |
| `collected_inventory.json` (the launcher's inventory, row `results/artifacts/final.pt`) | `25a2277b00c84613b33414de1c70c4cb96ee1ba7` |
| `collected/results/artifacts/final_checkpoint.json` (the worker's checkpoint pin) | `123f14c8ce64b99268702a64f3d9ef20235fa196` |

The same blobs are at the tips of `claude/helm-builder-continuation-20260923` (`cc68d8b3`) and
`research/helm-integration-20260923` (`197caa32`).
The Helm 2.0 run shipped the same package: its `collected/input/source.zip` is blob `50201036`, the package's blob.

## 4. How to run it

Run every command from the **worktree root**. From a deeper folder, Windows refuses to start Python because
the folder path is longer than 260 characters.

```bash
cd "C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/helm-unchanged-repro-20260924"
D="cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/typed_pointer_001/admission_unchanged_repro_001"

# 0. the tests (pure Python, about 3 seconds)
python -B "$D/test_unchanged_repro.py" -v

# 1. dry run: builds and checks everything with the launcher's own functions; writes nothing
python -B "$D/prepare_unchanged_repro.py" --dry-run

# 2. write: the same checks, then writes frozen/ (via frozen.partial/, then a rename)
python -B "$D/prepare_unchanged_repro.py" --write

# 3. commit the frozen records by explicit path, then push
git add --sparse -- "$D/frozen"
git commit -m "Freeze the unchanged-arm reproduction job (seed 20260917 of 20208c92)" -- "$D/frozen"
git push origin claude/helm-unchanged-repro-20260924
```

**4. Launch** (only after section 5 is all yes). Run the exact argv that `--write` prints and stores in
`frozen/study.json` under `jobs[0].launch_argv`. Its shape:

```
python -B <this checkout>/research/CAS_META_2_COMPOSITION/aws/typed_pointer_launch.py --execute
  --request <frozen/20260917/request.json> --request-sha256 <sha256>
  --authority <frozen/20260917/authority.json> --authority-sha256 <sha256>
  --owner-authorization <frozen/20260917/owner.json>
  --receipt-dir <this checkout>/records/typed_pointer_001/receipt_unchanged_repro_20260917
  --ledger-path <the canonical meta1 ledger>
```

There is no `--reduced-schedule`, so the launcher runs the full registered schedule.

**5. Read.** Commit the receipt folder, then:

```bash
python -B "$D/read_reproduction.py" --receipt-commit <40-hex commit that carries the receipt>
python -B "$D/read_reproduction.py" --receipt-commit <commit> --write   # also writes reproduction_reading.json
```

## 5. Before launch (none of these is checked by the writer)

- The plan says this writer must be **reviewed** first (job order item 3).
- The plan's order: the switch-ON smoke, then the three repaired seeds, then this job.
- Measured spend so far + $15.00 must be at most $60.00.
- If spend passed $30 before the third training job, stop and report.
- The owner has ruled on section 2.

## 6. Checks

**Run, and passed (real):**
- 30 of 30 tests pass (`python -B test_unchanged_repro.py -v`, 2.7 s). They cover:
  - every quote matches its pin and occurs exactly once in the plan blob `67163714` at `197caa32`;
  - edited plan text is refused;
  - the tree rule and the untracked rule, on synthetic git output;
  - the create-only `.partial` writer and its refusals;
  - the verdict reader on synthetic receipts: all three verdicts and every stop;
  - the reference hash, read from the real commit `c8d5c430` (small JSON blobs only);
  - every one of the 40 launcher names the writer uses exists in the launcher sources (read as text, not imported).
- The writer's launcher-free steps, run on this real checkout at `0aef7a18`: existing-folder refusal PASS,
  tree rule PASS, untracked rule PASS, plan blob and quotes PASS, Helm 2.0 records PASS. The launcher was not imported.
- A stray untracked file in this folder was refused by the real untracked check (probe file then removed).
- The package files on this branch are blob-identical to `3da10d84` (`597e9a2f`, `50201036`).
- All 18 practice checkpoint files the launcher's input list pins are present in this checkout.

**Not run (open):**
- `--dry-run` and `--write`. The laptop rule forbids launcher execution here. So the launcher-side steps
  (package verification, the three validators, the Helm 2.0 comparison) are **written but not yet run**.
  The first `--dry-run` is their first real test.
- No package build, no rehearsal, no AWS call, no launch.

## 7. Open questions

1. **Section 2.** The owner must choose before this job runs.
2. **Where the launcher finds the package.** The committed package receipt names the path it was built at, in
   `_worktrees/vision-next/`. The launcher follows that path, and that file exists there today (5,977,155 bytes).
   The launcher hashes it before use, so it ships the same bytes. If `vision-next` is deleted, the launch
   refuses before any booking. The writer records the path the launcher finds.
3. **Ledger room.** I did not open the budget ledger. Whether it has room for another $15.00 booking is unknown.
   The launcher refuses before spending if it has not.
4. **Spend checks are manual.** No runner script enforces section 5 for this job. `run_on_study.py` covers the
   switch-ON jobs only.
5. **Memory.** The dry run reads about 290 git blobs and holds the launcher's input list in memory (the contract
   caps that list at 96 MiB). The launch does the same reads. With little free memory, close large apps first.
6. **My choice, for the reviewer.** If the new run's own three records disagree on the hash, the reader says
   `INCOMPLETE` (a person looks), not `DOES_NOT_REPRODUCE`. This avoids triggering $30 of option B on a
   broken record. The plan's words are "Anything else reads DOES_NOT_REPRODUCE". The reviewer may want that instead.
7. **The owner's second instruction.** The access-restriction commands were not run. I do not have them. The plan
   (section 0) records that changing folder permissions is a security setting that Claude does not change,
   and that the owner holds the exact commands.

## 8. EXPOSURE

Files outside this working copy that I opened or touched:

- `C:/Users/wakil/AppData/Local/Temp/claude/.../scratchpad/plan.md`, `quotes.py`, `insp.py`: my own scratch
  files (a `git show` copy of the plan, and two small helper scripts).
- `.../_worktrees/meta1/.../records/budget/campaign_ledger.json`: existence and size only (`ls`). **Not opened.**
- `.../_worktrees/vision-next/.../research/CAS_META_2_COMPOSITION/records/typed_pointer_001/package_20208c92/`:
  folder listing only (`ls`). **The files were not opened.**
- Git objects read with `git show` / `git ls-tree` from the shared repository: commits `3da10d84`, `c8d5c430`,
  `197caa32`, and the builder branch tip `cc68d8b3` (`admission_analogy_on_001/on_study_common.py`,
  `prepare_on_study.py`). Receipt folder listings were names only, with sealed and `_eval.jsonl` names filtered out.
- `git fetch` from `origin` (GitHub) for the two named branches, with explicit refspecs.
- The tool harness saved three long command outputs under `C:/Users/wakil/.claude/projects/.../tool-results/`.
  I did not open them.

Not opened: any `*_eval.jsonl`, anything named sealed, `D:/tksCAS-archive/`, any salt, S3 or AWS, Claude transcripts.
No sealed or `_eval.jsonl` file exists in this checkout (name check over the whole checkout).
