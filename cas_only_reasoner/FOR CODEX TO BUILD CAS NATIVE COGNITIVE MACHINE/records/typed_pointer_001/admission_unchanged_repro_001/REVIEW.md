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
- After commit `ccf1d86a`, on this clean checkout:
  - `prepare_unchanged_repro.py --dry-run` **stopped** with `PLAN_MOVED_OR_HELD` (same tips as above), exit 1. It ran
    under `python -X importtime`; the import log names neither `typed_pointer_launch` nor `torch`. So the gate
    stopped it before the launcher was imported. Intended.
  - `prepare_unchanged_repro.py --check` **stopped** with `NOTHING_FROZEN_RUN_WRITE_FIRST`, exit 1. Intended: no
    `frozen/` exists.

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
- Two temporary files I wrote by mistake under the shell's `/tmp`: a `git show` copy of Helm 2.0's
  `collected_inventory.json` (from `c8d5c430`) and the import-time log of the dry run. Both deleted.
- The `__pycache__/` folder my compile check created in this folder (git-ignored). Deleted before the commit.
- The tool harness saved one long command output under `C:/Users/wakil/.claude/projects/.../tool-results/`. I did not
  open it.

Not opened: any `*_eval.jsonl`, anything named sealed, `D:/tksCAS-archive/`, any salt, S3 or AWS, the budget ledger,
Claude transcripts.

## Verification of cb2df78aa3e6a3c52db3b284e8fe86c431e7ad82

**Label:** `CLAUDE_BUILT_CLAUDE_CHECKED`. A fresh Claude verifier. Not an owner signature.

**Checked:** the diff from `2c464d2fad88922b4f44c3677265bde303258e4b` to
`cb2df78aa3e6a3c52db3b284e8fe86c431e7ad82`, against the two blockers and two majors of the first review.

**Verdict: `CHANGES_REQUIRED`.**

In plain words: the code changes are correct. The two majors are fixed. The two blockers are now gated correctly,
but they are not closed. The plan is still on hold, and the reproduction rule is still not fixed. So the writer must
not run `--write`, and nothing may launch. That is the builder's own position too.

### V.1 Each finding

| # | Finding | Result of this check |
|---|---|---|
| 1 | BLOCKER: pinned to a plan that is now held | **Gate FIXED and correct. Blocker still OPEN.** |
| 2 | BLOCKER: the file-hash test cannot pass | **Gate correct. Rule not chosen by the builder (right). Blocker still OPEN.** |
| 3 | MAJOR: copied records read `REPRODUCES` | **FIXED, complete.** |
| 4 | MAJOR: partial record sets give a verdict | **FIXED, complete.** |

**Finding 1.** The gate fetches the plan branch with an explicit refspec. It reads the fetched tip and the local
tip. Each must carry blob `67163714`, and the pinned commit must be in the branch. It runs before the launcher is
imported, in every mode, and again (without a fetch) just before the rename in `--write`. Real result today: both tips
are `6816b52e`, blob `3172a221`, status `LAUNCH_HELD_PENDING_AMENDMENTS`. The gate stops with `PLAN_MOVED_OR_HELD`.
That is correct. The finding stays open until the amended plan is approved and re-pinned. `BUILDER_REPORT.md`
section 5 is updated; its times match git (`2c464d2f` at 21:00:14, `7b6e25f8` at 21:04:56, both -0700).

**Finding 2.** `REPRODUCTION_POLICY` ships as `NOT_FIXED_PENDING_CODEX_AMENDMENT_ITEM_2`. The writer and the reader
both stop on it first. The builder did not pick a new rule. That is right: the rule is the owner's, via Codex. Under
the rule as written, `REPRODUCES` is now unreachable (an equal hash under the new run id is a stop). The underlying
fact holds: `pointer_learner.py` at `20208c92` lists `run_identity` and `elapsed_seconds` in `METADATA_FIELDS`
(lines 186-187) and puts them in the saved `metadata` (line 2056).

**Finding 3.** Every part of the reviewer's fix is in `read_reproduction.bound_records` and `new_reading`:
- the inventory `job` must be the frozen job;
- both checkpoint run ids must be the frozen job (a missing one also stops);
- the manifest and checkpoint-pin bytes must be the ones the job's own inventory collected (beyond the fix asked);
- Helm 2.0's file hash under the new run id is a stop, not `REPRODUCES`.

The reviewer's exact probe now stops. The real Helm 2.0 records, read as if they were a new run, stop. The old
impossible positive test is gone. The same binding runs on the reference side and passes on the real records at
`c8d5c430`.

**Finding 4.** All three records are required. Each needs exactly one well-formed `final.pt` row (64-hex sha256,
positive whole-number bytes). All three must agree on sha256 and bytes. Otherwise `INCOMPLETE`. The weights file is a
cross-check only. The four reviewer probes each read `INCOMPLETE`. My own extra probes (synthetic, pure Python):

| Probe | Result |
|---|---|
| inventory has two `final.pt` rows | `INCOMPLETE` |
| inventory `files` is not a list | `INCOMPLETE` |
| all three records absent | `INCOMPLETE` |
| bytes as a float, or as `true` | `INCOMPLETE` |
| only the inventory states Helm 2.0's hash | `INCOMPLETE` (records disagree) |
| checkpoint pin without `metadata` | stop (`CHECKPOINT_IS_FOR_ANOTHER_JOB:(None, None)`) |
| not delivered, Helm 2.0 inventory copied in | `INCOMPLETE` |

None reads `REPRODUCES` or `DOES_NOT_REPRODUCE`.

### V.2 New findings from this verification

**V1 - MINOR - the status-line check is a deny-list and ignores order** (`repro_common.py`, lines 119-122 and
342-345). `plan_status_approved` accepts any status line that has `APPROVED_FOR_LAUNCH` somewhere and no backticked
word containing HELD, HOLD, PENDING, WITHDRAWN, REVOKED, SUSPENDED or SUPERSEDED. Real probes of the function:

- "Was `APPROVED_FOR_LAUNCH`; now `DRAFT` again." -> accepted.
- "Was `APPROVED_FOR_LAUNCH`; now `PAUSED`." -> accepted.
- "`APPROVED_FOR_LAUNCH` is cancelled; see `CANCELLED`." -> accepted.
- "`APPROVED_FOR_LAUNCH` (launch held by the owner, see the note)." -> accepted (the word "held" is not backticked).

Today this does no harm: the blob pin stops any edit to the plan. It matters at the re-pin, which is the very next
step. Then the status check is the only program check that the new blob is approved.
**Fix:** use an allow-list. For example: the last backticked word on the status line must be `APPROVED_FOR_LAUNCH`;
any other backticked word must be in a short known list (today only `DRAFT`, in the "Was ... now" form); any prose
word such as held, hold, paused, cancel, withdraw, revoke, suspend or supersede, in any case, is a refusal. Better,
following the owner's rule that approval be executable: gate on an owner-signed phase-approval record, not on plan
prose.

**V2 - NOTE - a misleading stop name.** A checkpoint pin with no `metadata` stops as
`CHECKPOINT_IS_FOR_ANOTHER_JOB:(None, None)`. It fails closed, and section 3 says a missing run id stops. A name such
as `CHECKPOINT_RUN_ID_MISSING` would be clearer.

**V3 - NOTE - any later edit to the plan file stops `--check`.** The gate compares the whole plan blob. If the
amended plan is later edited for any reason (for example a results note), `--check` stops until a reviewed re-pin.
That fails closed and is intended. The amendment should keep later notes out of the plan file.

**V4 - NOTE - conforming the reader means more than `READER_RULE`.** The contradiction stop (`new_reading`, line 256)
and `decide()` both assume file identity. When the policy is fixed, the builder must revisit both, not only the
constant.

**V5 - NOTE - where the first `--dry-run` runs.** `--dry-run` and `--write` import the launcher, read about 290 git
blobs and hash 18 checkpoints. The owner's rules forbid launcher execution on this laptop. Where that first real run
happens should be settled before the re-pinned revision is reviewed.

### V.3 Checks run (real)

- Tests, once: `python -B test_unchanged_repro.py -v` from the worktree root. **48 of 48 pass**, none skipped,
  5.383 s.
- A live probe from a scratch script, with `load_launcher` replaced by a stub that stops:
  - `--dry-run` stopped with `PLAN_MOVED_OR_HELD` (both tips `6816b52e`, blob `3172a221`,
    `LAUNCH_HELD_PENDING_AMENDMENTS`);
  - `--check` stopped with `NOTHING_FROZEN_RUN_WRITE_FIRST`;
  - `read_reproduction.py --receipt-commit 000...0` stopped with
    `REPRODUCTION_POLICY_NOT_FIXED_BY_AN_AMENDED_PLAN`;
  - neither the launcher nor torch was imported.
- `git ls-remote origin`: the plan branch is at `6816b52e`; this branch was at `cb2df78a` before this commit.
- `git diff --name-status 20208c92 cb2df78a`: 8 files, all added. No file that exists at `20208c92` was edited.
- Reference hash: commit `c8d5c430` added the three records (status `A`) under
  `records/typed_pointer_001/receipt_20260917/`. It is an ancestor of `claude/helm-builder-continuation-20260923`
  (`cc68d8b3`). The real-record test reads `c6c49e982c408ced7cae47935f34708e14794d2fcc9789b1bce7900db5bd4ffb`,
  3,670,007 bytes, from all 3 records, bound to Helm 2.0's job.
- Launcher `validate_owner` (lines 481-492) reads only schema, candidate, quote, job and bounds. The new owner-record
  keys (`reproduction_policy`, `sixty_dollar_readings`) do not break it. Read statically; not run.

**Not run:** `--write`, the launcher, any package build, any AWS call. Nothing launched. No money spent.

**The owner's second instruction** ("Run the access-restriction commands..."): not run. It is not in this task.
Changing folder permissions is a security setting that Claude does not change. The owner holds the commands.

### V.4 What must happen before `APPROVE_FOR_WRITE_AND_LAUNCH`

1. Codex's amended plan, approved by the owner in an executable form.
2. Re-pin `PLAN_COMMIT`, `PLAN_BLOB` and `PLAN_SHA256`; re-check every quote.
3. The reproduction rule fixed by that plan. The reader conformed (`READER_RULE`, `decide()`, the contradiction stop),
   and `REPRODUCTION_POLICY` recorded.
4. V1 fixed, or explicitly accepted by the owner.
5. Fallback B admissions, if B is kept (finding 6).
6. A fresh review of that revision. Then `--dry-run` where the owner's compute rules allow.

### V.5 EXPOSURE (this verification)

- Two scratch scripts I wrote in the session scratchpad (`verify_probe.py`, `verify_reader_probe.py`), and this
  section's draft there (`verification_section.md`).
- Git objects read from the shared repository: the plan file at `197caa32` and `6816b52e` (blob ids and status
  lines); the log `197caa32..6816b52e`; the names added by `c8d5c430`; through the tests, the three Helm 2.0
  `final.pt` JSON records at `c8d5c430` and the package and admission blobs at `3da10d84`.
- Network: `git ls-remote origin` for two branch names; one `git fetch` of the plan branch with the explicit refspec,
  made by the gate during the probe (the tracking ref stayed at `6816b52e`); the `git push` of this commit.
- The tool harness may save long outputs under `C:/Users/wakil/.claude/projects/.../tool-results/`. I did not open
  them.

Not opened: any `*_eval.jsonl`, anything named sealed, `D:/tksCAS-archive/`, any salt, S3 or AWS, the meta1 ledger
(not even checked for existence: both probes stopped before that step), the `vision-next` worktree, Claude transcripts.

## Review of 303c281b (revision 2) and builder disposition (revision 3)

**Label:** `CLAUDE_BUILT_CLAUDE_CHECKED`. The reviewer was a fresh Claude reviewer. The builder is Claude, the
temporary builder while Codex is away. Neither is an owner signature.

**Reviewed commit:** `303c281b84bdecb0613f9a7f412b4fc7916ca23d` (revision 2, conformed to Codex policy `bc46b36e`).

**Review verdict:** `CHANGES_REQUIRED`. 1 BLOCKER, 2 MAJOR, 5 MINOR, 6 NOTE.

**Status after this revision:** still `NOT_READY`, on purpose. The execution admission cannot become `ADMITTED` until
real receipts exist: the P1 acceptance on AWS, Codex's policy freeze, the environment lock, the launch packet, a spend
record and a fresh review. Nothing was launched. No AWS call was made. No money was spent.

### R3.1 The review, in short

- **The blocker.** The reader could never be admitted. The policy must hold the reader's own digest. But the reader's
  source held the policy's hash. Each re-pin changed the digest. So no pair could ever match.
- **The two majors.** (a) A prerequisite "passed" on its own say-so: the word `PASS` and any 64-hex string. No
  receipt was opened. (b) A CUDA fault or out-of-memory error during the candidate panel was counted as the model's
  answer. That reads `DOES_NOT_REPRODUCE`, which allows the fallback. It should stop the study instead.
- **The minors and notes.** Smaller gaps in the same spirit: things trusted instead of re-checked.

### R3.2 Disposition at a glance

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | BLOCKER | Hash cycle between the policy file and the reader digest | **FIXED.** Pins moved to `policy_pins.json`, outside the digest |
| 2 | MAJOR | Prerequisites are self-asserted; no receipt is opened | **FIXED.** Each receipt is opened from git and its content checked |
| 3 | MAJOR | Infrastructure faults read as a valid output mismatch | **FIXED.** Faults make the evidence invalid. Split to be confirmed by Codex |
| 4 | MINOR | Reader trusts the admission copy inside `frozen/study.json` | **FIXED.** The committed admission is re-read and re-checked |
| 5 | MINOR | "Frozen before the result" is not enforced | **FIXED.** Rule field added; git-history rule enforced |
| 6 | MINOR | Changed-buffer check missing | **FIXED as VACUOUS** plus a SYNTHETIC test. Codex to accept |
| 7 | MINOR | Software environment only partly checked | **FIXED.** AMI, instance, region, shipped package, requirements |
| 8 | MINOR | Starting-state identity counted as continuation | **CHANGED to training configuration (INVALID).** Codex to confirm |
| 9 | NOTE | Missing key / dtype change: tests and AWS disagree | **ALIGNED.** Loader-refused case now tested as INVALID. Codex to rule |
| 10 | NOTE | File identity affects the verdict one way | **DOCUMENTED** as a binding rule |
| 11 | NOTE | Production reading accepts ACCEPTANCE-mode evidence | **FIXED.** Mode must be READING |
| 12 | NOTE | Owner records read only at pinned commits | **FIXED.** Owner records added to the tip check |
| 13 | NOTE | `--write`/`--check` stop with `POLICY_OR_PLAN_MOVED` | **KEPT (fail closed).** Re-pin is now a data-only change. Not re-pinned |
| 14 | NOTE | Package root used as a validity condition | **DOCUMENTED** as a binding rule |

### R3.3 Each finding, and what I did

**Finding 1 - BLOCKER - the hash cycle.** The reviewer was right. `repro_common.py` held the sha256 of
`REPRODUCTION_POLICY.json`, and `repro_common.py` is one of the three files the reader digest covers.
- **Fix.** Every policy and owner-record pin now lives in a new data file, `policy_pins.json`. The three reader
  sources hold no pinned policy hash at all. I also removed five prose mentions of the commit `bc46b36e` from their
  docstrings, so a re-pin leaves nothing stale inside the digest.
- **How it is bound instead.** The pins file's own sha256 is bound in `EXECUTION_ADMISSION.json`
  (`bindings.policy_pins_sha256`), in `frozen/study.json`, in every evidence file (`policy.policy_pins_sha256`) and in
  the review receipt. At reading time the reader stops (no verdict) unless the pins at the receipt commit are the very
  bytes it loaded.
- **The order now works.** (1) Claude fixes the reader; digest D. (2) P1 runs on AWS and records D. (3) Codex freezes
  the policy with D and the P1 receipt's sha256. (4) Claude re-pins: only `policy_pins.json` changes, so D is
  unchanged. P1 does not need to be paid for twice.
- **The P1 receipt is now opened** and must show `READER_ACCEPTANCE_PASS`, all 11 registered cases in order and
  passed, the admitted reader digest and sources, and the pinned panel and environment digests.
- **Tests.** `test_no_reader_source_carries_a_pinned_policy_hash` (full and 8-character forms) and
  `test_a_policy_freeze_and_re_pin_leave_the_reader_digest_unchanged` (a simulated freeze and re-pin in a temporary
  folder).
- **One new risk to settle with Codex** (open question R3-A): the frozen launch packet must not contain
  `policy_pins.json` or `EXECUTION_ADMISSION.json`. The pins hold the manifest's hash, and the manifest holds the
  packet's hash. A packet that held the pins would be a new cycle.

**Finding 2 - MAJOR - self-asserted prerequisites.**
- **Fix.** Each prerequisite entry must now name its receipt by `receipt_commit`, `receipt_path` and
  `receipt_sha256`. `read_prerequisite_receipts` opens the receipt with `git show <commit>:<path>`, and only when that
  commit is in HEAD's history (or the receipt commit's, for the reader) or the pinned policy commit's. A wrong path
  form (`..`, leading slash) or a missing blob is refused. Then `prerequisite_violations` checks the bytes and the
  content, per receipt:
  - P1 acceptance: as above (a `READER_ACCEPTANCE_FAIL` receipt whose hash is written is now refused; tested);
  - frozen policy: the receipt IS the pinned `REPRODUCTION_POLICY.json` at the pinned commit;
  - environment lock and launch packet: the files whose sha256 the manifest's `final_freeze` names, and the manifest's
    `dependencies.status` no longer `NOT_READY`;
  - budget: a committed spend record for THIS job, with named sources. The code reads the figure from it and does the
    `+ $15.00 <= $60.00` arithmetic;
  - fresh review: a machine verdict (`NO_BLOCKER_OR_MAJOR_FINDING_OPEN`) on this reader digest and these pins, by a
    reviewer other than the builder. Prose is never read.
- **`--check` no longer takes a typed spend figure.** `--spend-so-far-usd` and `--spend-source` are gone. It uses the
  spend read from the admitted spend record. It still cannot see spend incurred after that record was measured (open
  question R3-F).

**Finding 3 - MAJOR - infrastructure faults read as a mismatch.**
- **Fix, producer side.** `classify_prediction_error` counts ONLY a plain `ValueError` carrying a historical `require`
  code as a refusal. The codes start `POINTER_` or `TYPED_` (from `source.require` and `matched_contract.require` at
  `20208c92`). Every other exception, a prediction for the wrong record, and a grader crash become an `ERROR` row AND a
  producer invalid reason.
- **Fix, reader side (independent of the producer).** Any `ERROR` row, or any refusal without a historical code, on
  either side, reads `ADMISSION_INVALID_STOP`.
- **Tests.** The reviewer's scenario (reference panel fine, then a device fault partway through the candidate panel)
  now reads `ADMISSION_INVALID_STOP`, with and without the producer reporting it.
- **To confirm with Codex** (open question R3-B, extends builder question 4): only coded refusals are records.

**Finding 4 - MINOR - the frozen copy was trusted.** The reader now reads `EXECUTION_ADMISSION.json` at the receipt
commit and evaluates it in full: owner records, bindings, every prerequisite receipt opened. It must be `ADMITTED`,
for this job, with the same record sha256 that `frozen/study.json` names. A hand-written `frozen/` folder no longer
passes.

**Finding 5 - MINOR - "frozen before the result".**
- `frozen_before_reproduction_result_required: true` is now part of `READER_RULE`, so a policy change to `false` stops
  every tool.
- The reader now reads git history at the receipt commit. `frozen/` must be in exactly one non-merge commit. That
  commit must hold neither the receipt result nor the evidence, and must be an ancestor of both. The evidence file and
  the receipt `result.json` must each have exactly one committed version. `EXECUTION_ADMISSION.json` must not change
  after the freeze. The reading records the receipt, freeze, evidence and receipt-result commits.
- **Residual** (open question R3-G): someone could build a separate, unpushed history with one different evidence
  version. The protection is procedural (read only pushed commits of this branch; no force-push), not code.

**Finding 6 - MINOR - changed-buffer.** The reviewer checked it: the architecture at `20208c92` registers no buffer.
I confirmed there is no `register_buffer` call anywhere in `cas_meta2/typed_teaching/` at `20208c92`.
The check is therefore **VACUOUS** for this architecture. What I did: (a) the AWS acceptance records a `changed_buffer`
case with status `VACUOUS` and the reference's buffer list, and it PASSES only while that list is empty (if a buffer
ever appears, the acceptance fails until a real variant is built); (b) a pure test with a SYNTHETIC buffer shows a
changed buffer reads `DOES_NOT_REPRODUCE`; (c) the old test case named "changed buffer" (really an extra key) is
renamed "extra key". Codex should accept the VACUOUS label (open question R3-C).

**Finding 7 - MINOR - environment.** Both receipts' `preflight.json` must show AMI `ami-0fbbd0facbc9e3cff`,
`g7.2xlarge` and `us-west-2` (the real reference receipt at `c8d5c430` does; checked). The new receipt's shipped
`collected/input/source.zip` must be the pinned archive blob, and its `requirements-gpu.txt` member must have sha256
`9d0be781...` (the committed package has exactly that; checked). The evidence must record driver, cuDNN, Python and
kernel versions (recorded, not pinned; printed in the reading). `HISTORICAL_AMI`, `REQUIREMENTS_GPU_SHA256` and
`ENVIRONMENT_RECORDED_NOT_PINNED` are now all used.

**Finding 8 - MINOR - the starting state.** I moved `initial_model_identity` from continuation to training
configuration. Reason: the route protocol makes the starting state a check that must pass "before its first optimizer
update", and the policy's continuation row lists only optimizer, RNG, cursor/revision and counters. A different start
now reads `ADMISSION_INVALID_STOP`. This is a choice made in the open, fail-closed (no fallback). Codex should confirm
it (open question R3-D).

**Finding 9 - NOTE - missing key and dtype change.** The reviewer confirmed the pinned loader refuses both. A new
test builds both as the loader treats them (restore refused) and gets `ADMISSION_INVALID_STOP`, the same answer as the
AWS acceptance table. The older reader-level test (complete evidence from a loader that accepted the checkpoint) is
kept and labelled as such. Builder question 3 stays open for Codex's ruling.

**Finding 10 - NOTE - file identity one way.** Documented in the reader docstring, in `new_reading`, and in the
builder report clause map: a candidate hash equal to Helm 2.0's own is misbound evidence (final.pt embeds the run id),
a binding rule. It never turns a valid mismatch into a pass.

**Finding 11 - NOTE - evidence mode.** `evaluate_evidence` now takes `required_mode`. The production reading
requires `READING`. The P1 acceptance requires `ACCEPTANCE`.

**Finding 12 - NOTE - owner records at the tips.** The tip check now watches every pinned file on its own branch:
the policy files and both Codex owner records on `codex/helm-controlled-prelaunch-20260924`, and Claude's owner record
on `research/helm-integration-20260923` (fetched with an explicit refspec). A later owner record there stops `--write`
and `--check` until a reviewed re-pin.

**Finding 13 - NOTE - `POLICY_OR_PLAN_MOVED`.** Kept. It is correct fail-closed behaviour. I did NOT re-pin. The task
names `bc46b36e`, and Codex's branch has moved again, to `42ad8367`. Four pinned files changed there: the plan, the
execution manifest, the launch request and the amendments. `REPRODUCTION_POLICY.json` and `.md` did not change, and the
tip launch request still pins their same sha256 values. The plan change is process and accounting (P1 split into a
route-only P1a and a reader/probe/admission P1b; job counts; costs). A re-pin needs a review of those changes (open
question R3-E). It is now a data-only edit of `policy_pins.json` and does not change the reader digest.

**Finding 14 - NOTE - package root.** Documented as a binding rule: the historical loader rebuilds its role tagger
from `init_args.root`, so the root must be the recorded one.

### R3.4 What changed

- New file: `policy_pins.json` (the policy and owner-record pins; sha256 `d57d32dd...`).
- `repro_common.py`: pins loaded from that file (strict form check at import); `READER_RULE` gains
  `frozen_before_reproduction_result_required`; the tip check watches both branches; receipts are opened and checked
  (`read_prerequisite_receipts`, `prerequisite_violations` and one checker per receipt kind); the spend is read from a
  spend record; the historical refusal form; preflight, shipped-package and recorded-environment helpers; the
  starting state moved to training configuration; `spend_gate` removed.
- `read_reproduction.py`: the admission re-read at the receipt commit; the history rule; READING mode; ERROR rows and
  uncoded refusals invalid; preflight and shipped-package checks; pins checked at the receipt commit.
- `recompute_reproduction_evidence.py`: the refusal/fault split; faults reported; the pins sha256 in the evidence;
  the `changed_buffer` VACUOUS case; the acceptance passes only with all 11 registered cases in order.
- `prepare_unchanged_repro.py`: `gates()` opens the receipts; `--check` reads the spend from the admitted record.
- `EXECUTION_ADMISSION.json`: regenerated. Still `NOT_READY`. New binding `policy_pins_sha256`; each prerequisite gains
  `receipt_commit`; the reader digest is now `f35cd2ae...`.
- `test_unchanged_repro.py`: 99 tests (was 74).
- `BUILDER_REPORT.md`: new section 10.

### R3.5 Checks (real, this revision)

- **Tests.** `python -B test_unchanged_repro.py -v` from the worktree root: **99 of 99 pass, none skipped**, 14.0 s.
- **Mutation check** (scratch script, in memory). I broke each new rule once and ran the relevant test classes:
  receipts not opened (6 failures); reader ignores ERROR rows (1); any ValueError counts as a refusal (1); reader
  trusts the frozen admission copy (1); history rule off (3); pins file counted as a reader source (2); starting state
  back in continuation (1); preflight not checked (2); owner records not watched (2). Every mutant was caught.
- **Live gates, real repository, real fetch** (both branches fetched with explicit refspecs). Owner authorization:
  `STANDING_PROJECT_AUTHORIZATION`, no reasons. Both owner records unchanged at their tips (`42ad8367` and
  `b0fd06ff`). Four policy files moved at `42ad8367` (above). Execution admission: `NOT_READY`, 16 named reasons (state,
  no job, six prerequisites not passed, seven policy/manifest/launch-request freeze fields, not yet committed as is).
  Neither torch nor the launcher was imported.
- `--print-admission-bindings`: exit 0. Pins sha256 `d57d32dd...`; reader digest `f35cd2ae...`; 11 acceptance cases.
- `--check --study-sha256 000...0`: exit 1, `NOTHING_FROZEN_RUN_WRITE_FIRST`.
- `read_reproduction.py --receipt-commit 000...0`: exit 1 (no such commit). At `303c281b`: exit 1,
  `POLICY_PINS_ON_DISK_ARE_NOT_THE_PINS_AT_THE_RECEIPT_COMMIT` (that commit has no pins file). Correct tool stops.
- **Not run:** anything in `recompute_reproduction_evidence.py` that imports torch; `--dry-run` and `--write` (they
  import the launcher); any AWS call. No money spent.

### R3.6 What must happen before this job can run

1. Codex answers open questions R3-A to R3-E (and builder questions 1-12 in `BUILDER_REPORT.md` sections 9.6 and 10.6).
2. A reviewed re-pin of `policy_pins.json` to Codex's current records, if Codex wants the moved tip.
3. P1 (the reader acceptance) on AWS, in its authorized slot; its receipt committed.
4. Codex freezes `REPRODUCTION_POLICY.json` with this panel, reader digest `f35cd2ae...` (or the digest of the reviewed
   revision) and the P1 receipt's sha256; the manifest's environment lock and launch packet frozen; launch enabled.
5. A committed spend record for the named job, and a committed fresh-review receipt on this revision.
6. An `ADMITTED` admission naming all six receipts, committed. Then `--write`, commit, `--check`, launch.

### R3.7 Open questions (new or changed in this revision)

- **R3-A (new).** The frozen launch packet must not contain `policy_pins.json` or `EXECUTION_ADMISSION.json`, or a
  new hash cycle appears (pins -> manifest -> packet -> pins). What does Codex's packet contain?
- **R3-B (extends question 4).** Only a `ValueError` with a historical `POINTER_`/`TYPED_` code is a panel record.
  Every other fault invalidates the evidence. Confirm.
- **R3-C.** Accept `changed_buffer` as `VACUOUS` for this architecture (the acceptance fails if a buffer appears).
- **R3-D.** Confirm the starting-state identity as training configuration (a difference is INVALID, not a mismatch).
- **R3-E.** Re-pin to `42ad8367` (or later)? The reproduction policy itself is unchanged there.
- **R3-F.** The spend record is a point-in-time figure. Who writes it, from which sources, and how fresh must it be at
  `--check`? No age limit is enforced. Codex asked for per-slot spending admission (`codex-0007`).
- **R3-G.** A separate, unpushed history could hold one different evidence version. Read only pushed commits of this
  branch. Should the reader require the receipt commit to be in the fetched branch tip?
- **R3-H.** The review-receipt verdict word `NO_BLOCKER_OR_MAJOR_FINDING_OPEN` is mine. The code can check only that
  the reviewer is not the builder's runner string, not who the reviewer really is.
- **R3-I.** The environment-lock receipt is checked only against the manifest's sha256 and `dependencies.status`; its
  content format is Codex's.

### R3.8 EXPOSURE

- **Git objects read** (with `git show`, `ls-tree`, `diff`, `log`, `rev-parse`, `merge-base`):
  - Codex's branch at `bc46b36e`: `REPRODUCTION_POLICY.json` and `.md`, `LAUNCH_REQUEST.json`, the manifest's
    `final_freeze`, `dependencies` and `launch_enabled` fields, part of `ROUTE_AND_CHECKPOINT_PROTOCOL.md` (the
    starting-state section and matching lines); at the tip `42ad8367`: the diff stat since `bc46b36e`, the diff of the
    plan and of `CODEX_AMENDMENTS_20260924.md`, the field names of `COST_STATE.json`, and the two policy pins in the tip
    `LAUNCH_REQUEST.json`.
  - The Helm 2.0 receipt at `c8d5c430`: file names (sealed and `_eval` names filtered out); from `preflight.json` only
    its top-level key names and the `ami`, `instance_type` and `region` values; the runtime key names of
    `worker_report.json`; the blob id of `collected/input/source.zip`. The tests also read, as before, the three
    `final.pt` JSON records and the panel inputs.
  - This worktree (source `20208c92`, not edited): `pointer_learner.py` (`predict` and nearby `require` lines),
    `require` definitions in `source.py`, `matched_contract.py`, `worker_contract.py`; a search of
    `cas_meta2/typed_teaching/` for `register_buffer` (none); the member list and the `requirements-gpu.txt` member of
    the committed package `source.zip`.
- **Network:** `git fetch origin` with explicit refspecs for `codex/helm-controlled-prelaunch-20260924` (tracking ref
  moved `4489cc62` -> `42ad8367`) and, through the live gate, `research/helm-integration-20260923` (tip `b0fd06ff`);
  `git pull --ff-only` of this branch (already up to date); the `git push` of this commit.
- **Written outside this worktree:** scratch scripts in the session scratchpad (`write_pins.py`,
  `write_admission_r3.py`, `mutants_r3.py`, `live_gates_r3.py`).
- **Not opened:** any `*_eval.jsonl`, anything named sealed, `D:/tksCAS-archive/`, any salt, the meta1 ledger (not
  even an existence check), S3 or AWS, Claude transcripts, Codex's working copy. Nothing that exists at `20208c92` was
  edited. `CHANGELOG.md` and the harness spec sheet exist at `20208c92`, so they were not edited (standing rule).
