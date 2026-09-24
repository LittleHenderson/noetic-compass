# Unchanged-arm reproduction admission: review and builder disposition

**Label:** `CLAUDE_BUILT_CLAUDE_CHECKED`. The reviewer was a fresh Claude reviewer. The builder is Claude, the
temporary builder while Codex is away. Neither is an owner signature.

**Reviewed commit:** `2c464d2fad88922b4f44c3677265bde303258e4b` (branch `claude/helm-unchanged-repro-20260924`).

**Review verdict:** `NOT READY TO FREEZE OR LAUNCH`.

**Status after this revision:** still **not ready to freeze or launch**, on purpose. Two new gates now stop the
writer and the reader until two things happen. The launch plan must be amended and approved again. The reproduction
rule must be fixed by that amended plan. Nothing was launched. No AWS call was made. No money was spent.

## 1. The review, in short

The reviewer found the launcher-side admission built carefully. It binds seed 20260917 of `20208c92` to the full
schedule. Two things block it:

- **(a)** The plan it is pinned to has since been put on hold.
- **(b)** The plan's reproduction test cannot pass for a real re-run.

The reviewer also found two ways the verdict reader could print `REPRODUCES` wrongly.

## 2. Disposition at a glance

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | BLOCKER | Pinned to a plan revision that is now held | **FIXED (gate added).** Re-pin waits for the amended plan |
| 2 | BLOCKER | The plan's file-hash test cannot pass for a real re-run | **GATED, NOT DECIDED.** The rule is the owner's (via Codex). Both tools stop until it is fixed |
| 3 | MAJOR | Records copied from Helm 2.0's receipt read `REPRODUCES` | **FIXED** |
| 4 | MAJOR | Partial record sets still give a verdict | **FIXED** |
| 5 | MINOR | The $60 ceiling and stop rules are only quoted text | **PARTLY FIXED.** `--check` enforces the $60 arithmetic; the full runner is deferred |
| 6 | MINOR | Fallback B jobs have no admission | **DEFERRED.** Depends on the B-versus-C choice (review item 1) |
| 7 | MINOR | Tree and untracked rules run only at `--write` | **FIXED.** New `--check` mode |
| 8 | NOTE | Disagreeing records read `INCOMPLETE`, not `DOES_NOT_REPRODUCE` | **KEPT, FLAGGED** for the policy amendment |
| 9 | NOTE | The package ships from the `vision-next` worktree | **FIXED (optional part).** `--check` re-hashes the located archive |
| 10 | NOTE | OneDrive may lock the rename | **FIXED (cheap part).** A failed rename is now a named stop |
| 11 | NOTE | The plan reads the $60 two ways | **DISCLOSED.** Both readings carried in the records; reconciliation left to the amendment |

## 3. Each finding, and what I did

### Finding 1 - BLOCKER - the plan is on hold

**Reviewer (file `repro_common.py`, lines 89-92 and 245-257):** The admission is pinned to plan commit `197caa32`,
blob `67163714`, status `APPROVED_FOR_LAUNCH`. Commit `7b6e25f8` changed the plan to blob `3172a221`. Its status line
now reads `LAUNCH_HELD_PENDING_AMENDMENTS`: the owner's launch yes "is held, not used". The owner's pasted review says
"This review does not authorize a launch." `read_plan()` only reads the fixed commit, so `--write` would still pass.
All 15 pinned quotes still occur exactly once in the held plan, so no quote check could catch it.
**Reviewer's fix:** do not run `--write`; do not launch. Add a stop that fetches the plan branch with an explicit
refspec and requires the tip blob to equal `PLAN_BLOB` and the status line to read `APPROVED_FOR_LAUNCH`, else
`PLAN_MOVED_OR_HELD`. Re-pin after Codex's amendments. Update `BUILDER_REPORT.md` section 5.

**Disposition: FIXED (the gate). The re-pin waits.**
- New gate `repro_common.check_plan_is_current`. It runs `git fetch origin
  research/helm-integration-20260923:refs/remotes/origin/research/helm-integration-20260923`. Then it reads the
  fetched tip, and the local branch tip if one exists. Each must carry blob `67163714`. Each status line must hold
  `APPROVED_FOR_LAUNCH` and no word containing HELD, HOLD, PENDING, WITHDRAWN, REVOKED, SUSPENDED or SUPERSEDED.
  The pinned commit must be in the branch history. Otherwise it stops with `PLAN_MOVED_OR_HELD`. A failed fetch
  also stops.
- The writer runs this gate in every mode (`--dry-run`, `--write`, `--check`), **before the launcher is imported**.
  `--write` re-checks the refs (without a second fetch) just before the rename.
- **Real run on the live repository (2026-09-23, after the fetch):** it stopped. Both tips are at `6816b52e`, blob
  `3172a221`, status `LAUNCH_HELD_PENDING_AMENDMENTS`. So the gate sees the hold today.
- Tests use the real commits: the approval commit `197caa32` passes, and the hold commit `7b6e25f8` is refused on
  both blob and status. The test also shows every pinned quote still occurs once in the held plan. So the quote check
  alone could not have caught the hold, exactly as the reviewer said.
- **Not done, on purpose:** the re-pin. The amended plan does not exist yet. `PLAN_COMMIT`, `PLAN_BLOB` and
  `PLAN_SHA256` stay at `197caa32`, so the gate keeps stopping until a builder re-pins them to the amended, approved
  plan.
- `BUILDER_REPORT.md` updated: a revision note at the top, and sections 4, 5, 6 and 7.

### Finding 2 - BLOCKER - the plan's test cannot pass

**Reviewer (file `prepare_unchanged_repro.py`, `FINAL_PT_FINDING`):** Confirmed independently. `final.pt` is one
`torch.save` payload. It includes `run_identity` (whose `context.run_id` is the job name), `elapsed_seconds`, and
`init_args.root` (`pointer_learner.py` lines 2056-2068 at `20208c92`). A new run needs a new job name (the job name is
also the bucket name), and cannot repeat the elapsed time. So its file hash must differ, even with equal weights. The
$15 job buys an answer known in advance, and that answer triggers option B automatically. This is item 2 of the
owner's review (file identity versus learned-state identity versus output reproduction).
**Reviewer's fix:** the owner, through Codex's amendment, fixes the policy before any run. The reader then follows it.
The builder correctly did not change the rule.

**Disposition: GATED, NOT DECIDED.** I did not choose a new rule. That choice is the owner's, through Codex.
- I re-checked the fact in the source at `20208c92`. `export_checkpoint` builds `metadata` with `run_identity`,
  `elapsed_seconds` and `init_args.run_context.run_id`, and saves it inside `final.pt`. The worker sets `run_id` to
  the job name (`cncm/typed_pointer_worker.py` line 872). Neither file changed since `20208c92`.
- New gate `repro_common.check_policy_fixed`. `REPRODUCTION_POLICY` ships with status
  `NOT_FIXED_PENDING_CODEX_AMENDMENT_ITEM_2`. The gate passes only when the policy names the amended plan's commit and
  blob (equal to the re-pinned plan) **and** names the rule the reader implements (`read_reproduction.READER_RULE`,
  today `CHECKPOINT_FILE_IDENTITY`). So re-pinning the plan without conforming the reader also stops.
- The writer checks it before the launcher import. The reader checks it first, before reading any record.
  **Real run:** `read_reproduction.py` stopped with `REPRODUCTION_POLICY_NOT_FIXED_BY_AN_AMENDED_PLAN`, exit 1.
- The frozen `study.json` and owner record now carry the policy. The reader refuses a frozen admission made under a
  different policy.
- Under the rule as written, the reader can no longer print `REPRODUCES` for a real run (see finding 3). That makes
  the finding executable: the file-hash rule cannot give a pass.

### Finding 3 - MAJOR - copied records read `REPRODUCES`

**Reviewer (file `read_reproduction.py`, `new_reading`, lines 119-172):** The reader never checks that the three
`final.pt` records belong to the new job. With the new run's own result files, plus Helm 2.0's
`collected_inventory.json` and `final_checkpoint.json`, it printed `REPRODUCES` from 3 sources. A real re-run embeds
its own job name in `final.pt`, so a matching hash is evidence of a mix-up. The old positive unit test built exactly
this impossible receipt.
**Reviewer's fix:** require the inventory `job` and the checkpoint `run_id` to equal the frozen job, else stop. Treat
a matching file hash with a different `run_id` as a contradiction (stop), not `REPRODUCES`.

**Disposition: FIXED.**
- `collected_inventory.json` `job` must equal the frozen job, or it stops (`INVENTORY_IS_FOR_ANOTHER_JOB`).
- `final_checkpoint.json` must name the frozen job in **both** `metadata.run_identity.context.run_id` and
  `metadata.init_args.run_context.run_id`, or it stops (`CHECKPOINT_IS_FOR_ANOTHER_JOB`). A missing run id also stops.
- New, beyond the reviewer's fix: the manifest has no job field. So the committed manifest and checkpoint-pin bytes
  must equal the sha256 and size that the job's own inventory lists for them. Otherwise it stops
  (`RECORD_IS_NOT_THE_ONE_THIS_JOB_COLLECTED`). I checked this binding holds on the real Helm 2.0 receipt at
  `c8d5c430`.
- Helm 2.0's hash under the new job's run id stops as `CONTRADICTION_HELM2_FILE_HASH_UNDER_THE_NEW_RUN_ID`.
- The same binding runs on the reference side, with Helm 2.0's job.
- The old positive test is gone. New tests: the reviewer's exact probe; each swapped record alone; mixed run ids;
  a missing run id; and the real Helm 2.0 records read as if they were a new run (they stop).

### Finding 4 - MAJOR - partial record sets give a verdict

**Reviewer (file `read_reproduction.py`, lines 61-74 and 153-172):** Four probes read `REPRODUCES`: only the
inventory states a hash; only the checkpoint pin states it; the records agree on sha256 but not on bytes; the manifest
has two `final.pt` rows (so that record was silently dropped). Partial runs must read `INCOMPLETE`.
**Reviewer's fix:** require all three records, each with exactly one `final.pt` row, equal sha256 and equal bytes,
else `INCOMPLETE`. Hash the weights file only as a cross-check.

**Disposition: FIXED.**
- All three records are required. Each must have exactly one well-formed `final.pt` row: a 64-hex sha256 and a
  positive whole-number byte count. All three must state the same sha256 **and** the same bytes. Otherwise
  `INCOMPLETE`, with the reason named.
- An inventory with no single row for the manifest or the checkpoint pin also reads `INCOMPLETE`.
- The weights file is now a cross-check only. If the receipt commit carries `final.pt`, its hash and size must equal
  the three records, or the reader stops. The weights file alone never gives a verdict.
- Tests: all four reviewer probes, plus the missing inventory row and a text byte count. Each reads `INCOMPLETE`.

### Finding 5 - MINOR - the $60 ceiling and stop rules are only text

**Reviewer (file `repro_common.py`, `owner_record`):** Only an operator stands between `--write` and a $15 booking.
`run_on_study.py` covers the switch-ON jobs only. The owner's rule says gates must be executable. The section 6 line
"If spend passes the owner's stated stop before the last job, stop and report" is not quoted.
**Reviewer's fix:** a small runner that checks the four earlier jobs were delivered, reads measured spend, refuses
unless spend + $15.00 <= $60.00, applies the $30 stop, and only then launches.

**Disposition: PARTLY FIXED.**
- Done: `--check` requires `--spend-so-far-usd` and `--spend-source`. It refuses unless the figure + $15.00 is at
  most $60.00 (`SPEND_SO_FAR_PLUS_PER_JOB_BOUND_EXCEEDS_CEILING`). The figure must be plain dollars with at most two
  decimals. The output says plainly that the figure was **stated by the operator, not read from a record**.
- Deferred: the runner that reads delivery and spend from the switch-ON run's own records, and the $30 check. The
  amended launch request (review item 6) will set the real job count, bookings and maximum charges. A runner built
  now would be built against numbers that are about to change. `--check` lists both unchecked items in its output.
- Not done: I did not add a pinned quote for the section 6 line. The plan is to be re-pinned anyway.

### Finding 6 - MINOR - fallback B has no admission

**Reviewer (file `repro_common.py`, `MODEL_SEED`):** The writer is hard-coded to seed 20260917. Under the current rule
the fallback to B is certain, and seeds 20260918 and 20260919 have no admission.
**Reviewer's fix:** settle the policy first. If B is chosen or kept as the fallback, parameterise the writer or build
B's admissions up front.

**Disposition: DEFERRED.** The reviewer's own fix depends on the policy and on the B-versus-C choice (review items 1
and 2). Building B's admissions now would pre-empt Codex's amendment. When it lands, a builder parameterises
`MODEL_SEED`, the Helm 2.0 admission pins and the receipt folder over the three registered seeds.

### Finding 7 - MINOR - nothing re-checks the checkout at launch

**Reviewer (file `prepare_unchanged_repro.py`, lines 84-105 and 309-350):** The tree and untracked rules run only at
`--write`. The lifecycle, provider and budget code are not re-protected at launch.
**Reviewer's fix:** a `--check` mode that re-runs the existing-folder refusals (except `frozen/`), the repository
check and the frozen-file pins, just before `launch_argv`.

**Disposition: FIXED.** New `--check` mode, launcher-free. It re-runs:
- the refusals for `frozen.partial/` and the receipt folder; `frozen/` must exist;
- the tree rule and the untracked rule; then `frozen/` must be committed at HEAD with exactly its current bytes;
- the plan gate (fresh fetch) and the policy gate;
- `frozen/study.json` against the sha256 that `--write` printed;
- every frozen-file pin, the exact launch argv (rebuilt and compared), the three records' job names, the request
  identity, the authority bindings and the owner record;
- the archive the launcher located at freeze time: still there, same sha256 and size;
- the canonical ledger path: existence only, never opened;
- the spend gate (finding 5).

### Finding 8 - NOTE - disagreeing records read `INCOMPLETE`

**Reviewer:** This deviates from "Anything else reads DOES_NOT_REPRODUCE", in the safe direction. The policy should
not be set by the builder.
**Disposition: KEPT, FLAGGED.** The reader still says `INCOMPLETE`, and its docstring says why. It is listed for the
policy amendment. Once the rule is fixed, the reader is made to match the amended text exactly.

### Finding 9 - NOTE - the package ships from another worktree

**Reviewer:** `_locate_archive` follows the receipt's recorded path into `_worktrees/vision-next/`. It hashes the file
first, so the bytes are identical. If `vision-next` is removed, the launch refuses before any booking.
**Disposition: FIXED (the optional part).** `--check` re-hashes the archive at the path recorded at freeze time,
just before launch.

### Finding 10 - NOTE - OneDrive may lock the rename

**Reviewer:** If `os.rename` of `frozen.partial` fails, the error is not caught. It fails closed.
**Disposition: FIXED (the cheap part).** A failed rename is now a named stop,
`RENAME_FAILED_PARTIAL_LEFT_INSPECT_BY_HAND`, with a hint to pause OneDrive sync during `--write`. The `.partial`
folder is still left for a person. Tested with a simulated lock.

### Finding 11 - NOTE - the plan reads the $60 two ways

**Reviewer (plan at `197caa32`, section 4 "Cost basis"):** Section 4 says the $60 covers the smoke plus 3 jobs, and
options C and B need more. Section 0 says the $60 is actual spend and approves C with the fallback to B. The owner
record carried only section 0's reading.
**Disposition: DISCLOSED, not reconciled.** The section 4 sentence is now a pinned quote (`plan_cost_basis_bookings`,
sha256 `0f97696f...`). It occurs exactly once in the plan. The owner record and `study.json` now carry
`sixty_dollar_readings`, which states both readings. Reconciling them is the amended plan's job.

## 4. What changed

All in `records/typed_pointer_001/admission_unchanged_repro_001/`. No file that exists at `20208c92` was edited.

| File | Change |
|---|---|
| `repro_common.py` | plan gate; policy gate; spend gate; record-binding constants; new quote; `stamp_of`; named rename stop |
| `read_reproduction.py` | policy gate first; job binding; all three records; contradiction stop; weights cross-check only |
| `prepare_unchanged_repro.py` | both gates before the launcher; `--check` mode; policy and plan tips in the records |
| `test_unchanged_repro.py` | 30 tests became 48 |
| `BUILDER_REPORT.md` | revision note; sections 4-7 brought up to date |
| `REVIEW.md` | this file |

## 5. Checks

**Run, and passed (real):**
- 48 of 48 tests pass, none skipped (`python -B test_unchanged_repro.py -v`, about 4 s).
- The plan gate on the live repository, with a real fetch: **stopped** with `PLAN_MOVED_OR_HELD` (tips `6816b52e`,
  blob `3172a221`, `LAUNCH_HELD_PENDING_AMENDMENTS`). This is the intended result.
- The policy gate: **stopped** with `REPRODUCTION_POLICY_NOT_FIXED_BY_AN_AMENDED_PLAN`. Intended.
- `read_reproduction.py --receipt-commit 000...0`: **stopped** on the policy gate first, exit 1. Intended.
- After the commit, the writer's `--dry-run` and `--check` on this checkout (results in the commit report). Both are
  expected to stop before any launcher import.

**Not run (open):**
- The launcher-side steps (`verify_package`, the three validators, the Helm 2.0 comparison). The laptop rule forbids
  launcher execution here, and the gates now stop before them anyway. Their first real run will be the first
  `--dry-run` after the re-pin.
- No package build, no AWS call, no launch.

## 6. What must happen before this job can run

1. Codex finishes the six amendments. The owner approves one complete, amended launch request.
2. A builder re-pins `PLAN_COMMIT`, `PLAN_BLOB` and `PLAN_SHA256` to the amended plan, and re-checks every quote.
3. The builder conforms the reader to the fixed reproduction rule, sets `READER_RULE`, and records the amended plan in
   `REPRODUCTION_POLICY`.
4. If B is chosen or kept as the fallback, the builder builds B's admissions (finding 6).
5. A fresh review. Then `--dry-run`, `--write`, commit, and `--check` just before launch.

## 7. Open questions

1. **The owner's second instruction.** "Run the access-restriction commands Claude handed to lock down the secret
   test files." I did not run them. They are not in this task, and I do not have them. The plan (section 0) records
   that changing folder permissions is a security setting that Claude does not change, and that the owner holds the
   exact commands.
2. **The owner's launch yes.** It is held, not used, by the owner's own later review ("This review does not authorize
   a launch"). Nothing here launches.
3. **The spend figure for `--check`.** It is typed in by the operator. Should the amended launch request name the
   record it must come from (for example the switch-ON run log's last spend line)? Then a runner can read it.

## 8. EXPOSURE

Files and objects outside this working copy that I opened or touched in this revision:

- Git objects read from the shared repository with `git show`, `git diff`, `git log` and `git ls-tree`: the plan and
  the two hold notes at `197caa32`, `7b6e25f8`, `91968e5d` and `6816b52e`; the three Helm 2.0 `final.pt` records and
  the receipt file listing at `c8d5c430` (names only; sealed and `_eval.jsonl` names filtered out);
  `admission_analogy_on_001/run_on_study.py` at `cc68d8b3`.
- `git fetch` from `origin` (GitHub) of `research/helm-integration-20260923`, with an explicit refspec, twice (once by
  hand, once by the gate). It moved `refs/remotes/origin/research/helm-integration-20260923` to `6816b52e`.
- My scratch copy of `run_on_study.py` (from `git show`) in the session scratchpad folder.
- The tool harness saved one long command output under `C:/Users/wakil/.claude/projects/.../tool-results/`. I did not
  open it.

Not opened: any `*_eval.jsonl`, anything named sealed, `D:/tksCAS-archive/`, any salt, S3 or AWS, the budget ledger,
Claude transcripts.
