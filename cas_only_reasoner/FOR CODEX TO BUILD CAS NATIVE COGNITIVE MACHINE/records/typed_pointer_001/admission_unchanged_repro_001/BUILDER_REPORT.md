# Unchanged-arm reproduction admission: builder report

**Label:** `CLAUDE_BUILT_CLAUDE_CHECKED`. Built by Claude as the temporary builder while Codex is away.
It is not an owner signature.

**Status:** revision 2, conformed to Codex's reproduction policy (commit `bc46b36e`). **Not ready to freeze or
launch.** **Not launched.** No AWS call. No torch run. No money spent. Needs a fresh review.

> **Revision 2 (2026-09-24). Read section 9 first.** It supersedes sections 2, 4, 5 and 7 where they disagree.
> - The file-hash rule is gone. The reader now follows Codex's policy: valid evidence AND identical learned state AND
>   an identical 564-record public panel reads `STATE_AND_PANEL_REPRODUCED_FOR_ONE_SEED`. Valid evidence with any
>   difference reads `DOES_NOT_REPRODUCE_UNDER_REGISTERED_STATE_POLICY`. Any bad evidence reads `ADMISSION_INVALID_STOP`.
> - A new AWS-only module, `recompute_reproduction_evidence.py`, recomputes the evidence. It is written, not run.
> - The prose status parser (review finding V1) is gone. Two machine-readable states replace it:
>   `owner_authorization` and `execution_admission`.
>
> **Revision 1 (2026-09-23, after the review).** A fresh reviewer said NOT READY TO FREEZE OR LAUNCH.
> The review and my answer to each finding are in `REVIEW.md`. In short:
> - The plan was put **on hold** at `7b6e25f8` (`LAUNCH_HELD_PENDING_AMENDMENTS`), 4 minutes after this report was
>   first written. A new **plan gate** now stops the writer until the pinned plan is again the current, approved plan.
> - The plan's file-hash test **cannot pass** for a real re-run (section 2 below). A new **policy gate** stops the
>   writer and the reader until the amended plan fixes the reproduction rule. I did not choose the rule.
> - The reader now ties every record to the new job, needs all three records, and stops on a contradiction.
> - A new `--check` mode re-checks everything just before launch, including the $60 spend arithmetic.
> Today both gates stop. That is intended.

## 1. What this is

The owner approved plan HELM-REPAIR-CONTROLLED-1 (commit `197caa32`). Its option C says:
re-run Helm 2.0 seed 20260917, then compare the new `final.pt` with the old one.

This folder holds the tools for that one job:

| File | What it does |
|---|---|
| `prepare_unchanged_repro.py` | Freezes the one job (owner, request and authority records). Launches nothing. |
| `read_reproduction.py` | After the run, prints one of the three policy verdicts (revision 2; section 9). |
| `recompute_reproduction_evidence.py` | Revision 2. AWS only. Recomputes the evidence the reader reads. Written, not run. |
| `repro_common.py` | Shared pins, labels, the policy gate and the two states. Imports no launcher and no torch. |
| `public_panel_manifest.json` | Revision 2. The pinned public panel: 564 course records and the historical answers. |
| `build_panel_manifest.py` | Revision 2. Rebuilds that manifest from committed JSON (git only). |
| `EXECUTION_ADMISSION.json` | Revision 2. The technical-readiness record. Today `NOT_READY`. |
| `test_unchanged_repro.py` | 74 pure-Python tests (48 in revision 1). |
| `REVIEW.md` | The review, and my disposition of each finding (revisions 0 and 1). |

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

**Revision 1.** The fresh reviewer confirmed this finding independently. The owner's own review (item 2) now asks
for the same thing: tell file identity, learned-state identity and output reproduction apart, and fix the rule before
running. Codex is working that amendment. Until it lands, the writer and the reader stop at the policy gate
(`REPRODUCTION_POLICY_NOT_FIXED_BY_AN_AMENDED_PLAN`). Under the rule as written, the reader now also stops if a new
run's records show Helm 2.0's file hash under the new job name. That is a contradiction, not a pass.

## 3. The exact hash it compares against

| Item | Value |
|---|---|
| Helm 2.0 seed-17 `final.pt` sha256 | `c6c49e982c408ced7cae47935f34708e14794d2fcc9789b1bce7900db5bd4ffb` |
| Size | 3,670,007 bytes |
| Helm 2.0 job | `cas-meta2-tpntr-20260920210258-20208c92-m-20260917` |
| Commit | `c8d5c430eec23a8fadd98bbcd045fecf03d86239` (the commit that added the Helm 2.0 receipts) |
| Folder | `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/typed_pointer_001/receipt_20260917/` |

Three committed records state that hash, and the reader requires all three to agree (on the new side too, since
revision 1, and each record must belong to the job it reads):

| Record in that folder | Blob |
|---|---|
| `collected/results/artifacts/manifest.json` (the worker's artifact list, row `final.pt`) | `d98b25aa6b8022da9ad7f1b2c90c8799ea5b5827` |
| `collected_inventory.json` (the launcher's inventory, row `results/artifacts/final.pt`) | `25a2277b00c84613b33414de1c70c4cb96ee1ba7` |
| `collected/results/artifacts/final_checkpoint.json` (the worker's checkpoint pin) | `123f14c8ce64b99268702a64f3d9ef20235fa196` |

The same blobs are at the tips of `claude/helm-builder-continuation-20260923` (`cc68d8b3`) and
`research/helm-integration-20260923` (`197caa32`).
The Helm 2.0 run shipped the same package: its `collected/input/source.zip` is blob `50201036`, the package's blob.

## 4. How to run it

**Today steps 1 to 4 stop at the plan gate (`PLAN_MOVED_OR_HELD`) and the policy gate. That is intended.** They
work only after the re-pin described in section 5.

Run every command from the **worktree root**. From a deeper folder, Windows refuses to start Python because
the folder path is longer than 260 characters.

```bash
cd "C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/helm-unchanged-repro-20260924"
D="cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/typed_pointer_001/admission_unchanged_repro_001"

# 0. the tests (pure Python, about 4 seconds)
python -B "$D/test_unchanged_repro.py" -v

# 1. dry run: the two gates, then every check with the launcher's own functions; writes nothing
python -B "$D/prepare_unchanged_repro.py" --dry-run

# 2. write: the same checks, then writes frozen/ (via frozen.partial/, then a rename). Pause OneDrive sync first.
python -B "$D/prepare_unchanged_repro.py" --write

# 3. commit the frozen records by explicit path, then push
git add --sparse -- "$D/frozen"
git commit -m "Freeze the unchanged-arm reproduction job (seed 20260917 of 20208c92)" -- "$D/frozen"
git push origin claude/helm-unchanged-repro-20260924

# 4. immediately before launch: re-check everything (launcher-free); prints the exact launch argv
python -B "$D/prepare_unchanged_repro.py" --check --study-sha256 <study_json_sha256 printed by step 2> \
    --spend-so-far-usd <measured spend so far, e.g. 23.18> --spend-source "<where that figure was read>"
```

**5. Launch** (only after section 5 is all yes, and only right after step 4 passes). Run the exact argv that
`--check` prints (the same argv `--write` stored in `frozen/study.json` under `jobs[0].launch_argv`). Its shape:

```
python -B <this checkout>/research/CAS_META_2_COMPOSITION/aws/typed_pointer_launch.py --execute
  --request <frozen/20260917/request.json> --request-sha256 <sha256>
  --authority <frozen/20260917/authority.json> --authority-sha256 <sha256>
  --owner-authorization <frozen/20260917/owner.json>
  --receipt-dir <this checkout>/records/typed_pointer_001/receipt_unchanged_repro_20260917
  --ledger-path <the canonical meta1 ledger>
```

There is no `--reduced-schedule`, so the launcher runs the full registered schedule.

**6. Read.** Commit the receipt folder, then (the reader also stops at the policy gate until the rule is fixed):

```bash
python -B "$D/read_reproduction.py" --receipt-commit <40-hex commit that carries the receipt>
python -B "$D/read_reproduction.py" --receipt-commit <commit> --write   # also writes reproduction_reading.json
```

## 5. Before launch

**Superseded (revision 1).** The first version of this list was committed at 21:00 (2026-09-23, local time, -0700).
At 21:04 commit `7b6e25f8` put the plan on hold (the plan dates its status 2026-09-24): the owner's launch yes "is held, not used", and the owner's pasted review says
"This review does not authorize a launch." So the list is now:

Blocked today (checked by a program: the writer and `--check` stop):
- **The plan is on hold.** Codex finishes the six amendments. The owner approves one complete, amended launch request.
- **The re-pin.** A builder re-pins `PLAN_COMMIT`, `PLAN_BLOB` and `PLAN_SHA256` in `repro_common.py` to the amended
  plan and re-checks every quote. Until then: `PLAN_MOVED_OR_HELD`.
- **The reproduction rule.** The amended plan fixes it (owner review item 2). A builder conforms
  `read_reproduction.py`, sets `READER_RULE`, and records the amended plan in `REPRODUCTION_POLICY`. Until then:
  `REPRODUCTION_POLICY_NOT_FIXED_BY_AN_AMENDED_PLAN`.
- **Measured spend so far + $15.00 must be at most $60.00.** `--check` enforces the arithmetic on the figure the
  operator states.

Still checked by the operator, not by a program:
- A fresh review of the re-pinned, conformed writer and reader.
- The plan's order: the switch-ON smoke, then the three repaired seeds, then this job. (The smoke, attempt 2,
  PASSED per the coordinator's state note at `6816b52e`.)
- If spend passed $30 before the third training job, stop and report.
- If B is chosen or kept as the fallback, its two admissions exist (review finding 6).

## 6. Checks

**Revision 1 (real):** 48 of 48 tests pass, none skipped. On the live repository, the plan gate (with a real fetch)
stopped with `PLAN_MOVED_OR_HELD` and the policy gate stopped with `REPRODUCTION_POLICY_NOT_FIXED_BY_AN_AMENDED_PLAN`.
Both are the intended results. Details in `REVIEW.md` section 5.

**First version, run and passed (real):**
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

(Revision 1: questions 1, 4 and 6 are now handled as described in `REVIEW.md`: 1 by the policy gate, 4 partly by
`--check`, 6 kept and flagged for the policy amendment.)

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

Revision 1's exposure is listed in `REVIEW.md` section 8.

Files outside this working copy that I opened or touched (first version):

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

## 9. Conformance to policy bc46b36e (revision 2, 2026-09-24)

**Label:** `CLAUDE_BUILT_CLAUDE_CHECKED`. Built by Claude as the temporary builder. Not an owner signature. Not yet
reviewed.

### 9.1 In plain words

- **The old rule is gone.** It compared the `final.pt` file hash. A real re-run can never match that hash, because
  the file stores the job name and the elapsed time. So the old rule could never pass.
- **The new rule is Codex's policy, exactly.** Commit `bc46b36e`, `REPRODUCTION_POLICY.json` and `.md`. There are three
  answers only:
  - `STATE_AND_PANEL_REPRODUCED_FOR_ONE_SEED`: the evidence is valid, the learned state is identical, and all 564
    panel records are identical.
  - `DOES_NOT_REPRODUCE_UNDER_REGISTERED_STATE_POLICY`: the evidence is valid, but the learned state or any panel
    record differs. Only this answer may lead to fallback B.
  - `ADMISSION_INVALID_STOP`: any evidence is missing, broken or tied to the wrong job. The study stops. No fallback.
- **Four levels, two decide.** The reader works out four things from the evidence: file, learned state, panel output,
  and continuation (optimizer and random-number state). Only learned state and panel output decide. File and
  continuation are printed for the record and never change the answer.
- **Zero tolerance.** Every tensor is compared by the sha256 of its exact bytes. No rounding. No missing key allowed.
  No dtype conversion.
- **The evidence is made on AWS only.** `recompute_reproduction_evidence.py` loads both checkpoints on a GPU, hashes
  every tensor itself, and runs the 564 public records through the historical model. It is written. It has never run.
- **No prose approval.** The old code searched a plan's status line for approval words (finding V1). That is gone.
  Two machine-readable states replace it. Owner authorization: granted, read from blob-bound owner records.
  Execution admission: `NOT_READY` today, in a JSON record bound to exact hashes.

### 9.2 Policy clause to code

Line numbers are in this revision. `rr` = `read_reproduction.py`, `rc` = `repro_common.py`,
`re` = `recompute_reproduction_evidence.py`, `pu` = `prepare_unchanged_repro.py`.

| Policy clause (where) | What the code does | Code |
|---|---|---|
| `required_for_C`: valid admission AND complete learned state identical AND complete panel identical (JSON) | `decide()` returns REPRODUCED only when all three hold | `rr:104` `decide` |
| `missing_or_invalid_evidence: ADMISSION_INVALID_STOP` (JSON); "authorizes no fallback job" (md step 1) | every evidence problem is a named reason; any reason gives ADMISSION_INVALID_STOP; next step says no fallback | `rr:104`, `rr:529` `reading`, `rr:73` `NEXT_STEP` |
| `valid_state_or_output_mismatch: DOES_NOT_REPRODUCE_UNDER_REGISTERED_STATE_POLICY` (JSON); fallback only if job count, authority, headroom and stop rules allow, else COMPARISON_INCOMPLETE (md step 3) | the verdict for valid evidence with any difference; the next-step text names the fallback conditions and COMPARISON_INCOMPLETE | `rr:104`, `rr:73`, `rc:143` |
| `file_hash_preserved: true`, `file_mismatch_alone_triggers_fallback: false` (JSON) | FILE_IDENTICAL / FILE_DIFFERENT is computed and printed; `decide()` takes it and never reads it | `rr:496`, `rr:104` |
| `continuation_identity_reported_separately: true` (JSON); optimizer, RNG, cursor, revision, counters (md table) | CONTINUATION_IDENTICAL / _DIFFERENT from optimizer and RNG rows plus cursor, revision, counters, training mode, starting state; printed separately; never decides | `rr:507`, `rc:221`, `rc:245` |
| `learned_state_tolerance: 0`; "no tolerance, rounding, missing-key allowance or dtype conversion" (md table) | per tensor: key path, dtype, shape, layout, sha256 of the logical value bytes; any difference, missing or extra key counts | `rc:255`, `rr:337` `deciding`, `rr:367` `compare_rows`, `rr:503` |
| "all model state_dict keys ... including persistent buffers, plus encoder/vocabulary state and prediction-affecting configuration" (md table) | learned state = every model_state row + every encoder_state row (incl. the tokenizer/vocabulary) + predictive configuration + inference mode | `rc:220`, `rc:234`, `rc:187`, `re:410` `load_side`, `re:454` buffers |
| "Architecture, switch state, number of rounds, encoder/vocabulary mapping, normalization settings and inference mode are predictive configuration" (md) | `PREDICTIVE_RUN_IDENTITY`: learner profile (file hashes of the architecture), encoder identity, core rounds, readout, heads, normalisation, prediction depth, learnable names | `rc:234`, `rr:305` `split_metadata` |
| "Exclude only ... file path, root, elapsed time, storage/container layout, run identifier and administrative limits. Retain and report all their differences." (md) | stride, storage offset, device, run id, root, elapsed seconds, limits and the run-identity digest are envelope: reported under `envelope_differences_reported_only`, never compared | `rc:250`, `rr:305`, `rr:337` |
| "Training-configuration or software differences ... fail the environment-admission check" (md) | a training-configuration difference between the two checkpoints is INVALID; both training receipts must show the pinned torch, CUDA and GPU | `rr:490`, `rr:224`, `rr:282` |
| "Validate ... numerical environment" (md step 1); manifest `dependencies` | the evidence environment must equal `NUMERICAL_ENVIRONMENT` exactly, else INVALID | `rc:196`, `rr:426` |
| "Same pinned public historical course/held-back panel, exact record IDs/order, full decoded answers, explicit refusal/error status and historical grader flags. Compare every record" (md table) | 564 records in the historical order; the reader hashes each full answer and its slot decisions itself; status; grader `correct` and the sha256 of the full grader row | `public_panel_manifest.json`, `rc:175`, `rr:390` `panel_view`, `rr:483`, `rr:517` |
| "The final manifest must pin the complete output-panel inputs and historical reference answers" (md) | the manifest pins the course file and the Helm 2.0 `course_p10` predictions and scoring by blob and sha256; the recomputed reference panel must equal them, else INVALID | `build_panel_manifest.py`, `rr:486` |
| "Failed/refused records remain records; only explicitly registered expected refusals compare as equal" (md) | `registered_expected_refusals` is empty; a refusal or error stays a record and compares as different | `build_panel_manifest.py`, `rr:390` |
| "A panel cannot be reduced after a mismatch"; "No HSET-2 TEST question ... is used" (md) | the panel is pinned by file sha256 and record-id digest; order is checked; `hset2_material_used: false` | `rc:446`, `rr:479` |
| "Do not trust those fields without recomputing them from the checked checkpoint bytes on AWS" (md) | the AWS module hashes every tensor itself; the four stored identities are only checked for integrity (mismatch = INVALID) | `re:366` `tensor_row`, `re:410`, `rr:456` |
| "Inspection/loading must use the pinned historical loader ... Never execute an untrusted checkpoint on the laptop" (md) | loads through `PointerCourseLearner.restore_checkpoint` from the byte-verified historical package; stops with GPU_REQUIRED before torch is imported off Linux | `re:443`, `re:321` `verify_package`, `re:282` `require_gpu` |
| "Output agreement never overrides a learned-state mismatch. A learned-state match never overrides an output mismatch." (md step 4) | `decide()`; tested both ways | `rr:104`, tests |
| "equal-state/different-envelope, changed-value, changed-buffer, missing-key, dtype-change, altered-output and corrupt-reference checks must be implemented, reviewed and run on AWS" (md) | `--mode acceptance` builds each variant from the public reference checkpoint and checks its registered verdict | `re:522` `acceptance_specs`, `re:585` `acceptance_mode` |
| "Missing/corrupt/misbound evidence maps to ADMISSION_INVALID_STOP ... align the existing reader's INCOMPLETE/named-stop vocabulary" (md) | `INCOMPLETE` is gone; the old mix-up stops are now named invalid reasons (V2's `CHECKPOINT_RUN_ID_MISSING` included) | `rr:173` `bound_records`, `rr:260` `new_reading` |
| "Record standing owner authorization separately from a machine-readable technical-admission state bound to exact plan/policy/manifest hashes. A prose line containing `APPROVED_FOR_LAUNCH` is insufficient" (md) | `owner_authorization_state` reads machine fields of blob-bound records; `execution_admission_state` reads `EXECUTION_ADMISSION.json`, bound to every pinned hash; no status line is parsed anywhere | `rc:631`, `rc:694`, `rc:678`, `EXECUTION_ADMISSION.json` |
| "A preparation-only path must not require inventing launch approval" (amendments item 2) | `--dry-run` and `--print-admission-bindings` need neither state; `--write` and `--check` need both; `--write` takes the job name from the ADMITTED record | `pu:147` `gates`, `pu:358`, `pu:364`, `pu:497` |
| "pin the complete public panel, numerical environment and independent reader" (amendments item 2) | panel sha256; environment dict and its digest; one reader-source digest over the three reader files | `rc:175`, `rc:196`, `rc:430` |
| policy JSON `output_panel_manifest_sha256`, `reader_source_sha256`, `reader_acceptance_receipt_sha256` (all null today) | the admission cannot be ADMITTED until they equal this panel, this reader and the P1 receipt; nor until the manifest and launch request say `launch_enabled: true` | `rc:583` `policy_freeze_violations` |
| "keep the plan immutable ... A changed plan invalidates affected technical admission evidence, not the standing owner authority" (md) | each pinned file must be unchanged at the fetched branch tip: `--write`/`--check` stop, `--dry-run` reports | `rc:560` `check_policy`, `rc:530` |

### 9.3 What runs on AWS in the P1 slot

Nothing here has run. This is the plan the code implements.

- **Machine.** The pinned numerical environment: g7.2xlarge (NVIDIA RTX PRO 4500 Blackwell Server Edition),
  torch `2.11.0+cu128`, CUDA `12.8`, numpy `2.2.6`, deterministic algorithms on, TF32 off,
  `CUBLAS_WORKSPACE_CONFIG=:4096:8`. See open question 1 about T4.
- **Inputs, each named by sha256:**
  - the historical package `source.zip` (`c42370c4...`, 5,977,155 bytes), unpacked at `/opt/cas-graph6curr/package`
    (the root both checkpoints record). The module checks all 270 members byte for byte and refuses any extra `.py`;
  - the reference `final.pt` (`c6c49e98...`, 3,670,007 bytes; committed at `c8d5c430`) and its
    `final_checkpoint.json` (`2f4bfbd1...`);
  - `public_panel_manifest.json` (`a27b3839...`, 442,201 bytes);
  - the three reader sources, in a folder outside the package root.
- **Command (P1):** `CAS_META2_RUN_TEACHING_CYCLE=1 python -B recompute_reproduction_evidence.py --mode acceptance
  --package-root /opt/cas-graph6curr/package --package-archive <source.zip> --reference-checkpoint <final.pt>
  --reference-record <final_checkpoint.json> --panel-manifest <public_panel_manifest.json> --work-dir <new dir>
  --out <acceptance_receipt.json>`.
- **What it checks (10 cases).** Self identity (REPRODUCED). Equal state with a new envelope (REPRODUCED,
  FILE_DIFFERENT). Continuation-only difference (REPRODUCED, CONTINUATION_DIFFERENT). Changed value, changed encoder
  state, altered output (all DOES_NOT_REPRODUCE). Equal state with one answer tampered (DOES_NOT_REPRODUCE). Missing
  key, dtype change, corrupt reference (all ADMISSION_INVALID_STOP). The receipt says `READER_ACCEPTANCE_PASS` only if
  all 10 give their registered answer.
- **Work estimate, not measured.** Six panel runs of 564 records (3,384 forward passes) plus about ten checkpoint
  loads. For scale only: the Helm 2.0 worker made 13,750 predictions and 1,470 training updates in 7,817 s.
- **After P1.** The receipt sha256 goes into `EXECUTION_ADMISSION.json` and, by Codex, into
  `REPRODUCTION_POLICY.json` `reader_acceptance_receipt_sha256`.
- **After the main job.** The same module runs `--mode reading` on the same machine type. The evidence file is
  committed at `records/typed_pointer_001/evidence_unchanged_repro_20260917/reproduction_evidence.json`. Then
  `read_reproduction.py --receipt-commit <commit>` gives the verdict. It reads JSON only and may run anywhere.
- **Not built yet.** No launcher ships this module to AWS. The pointer launcher only runs the training worker.

### 9.4 How to run it now (supersedes section 4)

From the worktree root, with the full folder path `D` as in section 4:

```bash
python -B "$D/test_unchanged_repro.py" -v                              # 74 pure-Python tests
python -B "$D/prepare_unchanged_repro.py" --print-admission-bindings   # read-only; no approval needed
python -B "$D/build_panel_manifest.py" --verify                        # rebuilds the panel manifest from git
# Not on the laptop (imports the launcher): --dry-run (preparation only), --write (needs ADMITTED).
python -B "$D/prepare_unchanged_repro.py" --check --study-sha256 <hex> --spend-so-far-usd <d.dd> --spend-source "<where>"
python -B "$D/read_reproduction.py" --receipt-commit <commit>          # exit 0 valid verdict, 2 INVALID_STOP, 1 tool stop
```

To admit the job later: run P1, collect every prerequisite receipt, then write a new `EXECUTION_ADMISSION.json`
with `state: ADMITTED`, the job name, every receipt sha256 and the bindings printed by `--print-admission-bindings`.
Commit it as is. Only then does `--write` proceed.

### 9.5 Checks (real, this revision)

- **Tests.** 74 of 74 pass, none skipped (`python -B test_unchanged_repro.py -v`). They cover all 32 combinations of
  `decide()`, non-boolean inputs, the label spellings in the real policy files, every policy pin, the panel manifest
  rebuilt from git byte for byte, both states (including prose-only approval and approval words in a state field),
  the preparation-only path, and the reader over synthetic evidence.
- **Mutation check (scratch script).** I broke the rule three ways in memory: output alone decides, file identity
  decides, invalid evidence reads as a mismatch. The tests caught each one (6, 6 and 7 failures). Ignoring the tensor
  value bytes was caught too (2 failures). The clean run then had 0 failures.
- **Live gates, real repository, real fetch.** Owner authorization: `STANDING_PROJECT_AUTHORIZATION`, no reasons (the
  three recorded owner files at `bc46b36e` and `ca68690b`, blobs `10069e00`, `e6cfe5b9`, `f707ce45`). Execution
  admission: `NOT_READY`, 16 named reasons: the state itself, no job name, all six prerequisites not passed, seven
  policy/manifest/launch-request freeze fields not set, and the record not yet committed. The launcher and torch were
  not imported.
- **The write path stops today** with `POLICY_OR_PLAN_MOVED`. Codex's branch moved after `bc46b36e` (commits
  `510dd0d2`, `4489cc62`, agent-bus coordination). `LAUNCH_REQUEST.json` and `CODEX_AMENDMENTS_20260924.md` changed.
  No deciding file changed. See open question 2.
- `--check` stops with `NOTHING_FROZEN_RUN_WRITE_FIRST` (exit 1). `read_reproduction.py --receipt-commit 000...0`
  passes the policy check, then stops on the missing commit (exit 1, no verdict).
- **Not run:** anything in `recompute_reproduction_evidence.py` that imports torch; `--dry-run` and `--write` (they
  import the launcher; not on the laptop). No AWS call. No money spent.

### 9.6 Open questions and conflicts (not chosen silently)

1. **P1 machine type.** The cost envelope names a T4 for P1. The historical code refuses a T4 (`gpu_adapter._cuda`,
   `T4_NOT_ADMITTED`), and the pinned environment is the RTX PRO 4500. The historical answers are only expected to
   reproduce bit for bit on the pinned GPU. On a T4 the acceptance would read ADMISSION_INVALID_STOP. Which machine?
2. **Codex's branch moved after `bc46b36e`.** Only coordination notes changed. I kept all eight pinned files under
   the currency check, so `--write` and `--check` stop until a reviewed re-pin. Should the currency check cover only
   the deciding files (policy, manifest, plan, protocol, statistical policy)?
3. **Missing key and dtype change.** The policy table counts them as learned-state differences (a valid mismatch).
   The pinned historical loader refuses such a checkpoint, so no panel evidence can exist, and the reading is
   ADMISSION_INVALID_STOP. Policy step 1 ("full state inventory ... any missing evidence") supports the stop. The
   reader, given complete evidence, would read DOES_NOT_REPRODUCE. Which is intended?
4. **Unregistered refusals.** The reproduction policy keeps them as differing records (DOES_NOT_REPRODUCE). The plan
   (section 3) says unexpected route errors invalidate the reading. I followed the reproduction policy. Confirm.
5. **Route.** The plan names the common `predict_packet` adapter (builder snapshot `cc68d8b3`) for both study arms.
   For this reproduction panel I used the historical learner route, which produced the pinned historical answers.
   Route check 1 requires the two to agree on course packets. Confirm this is acceptable.
6. **Panel scope.** The panel is the 564-record public course, including its 127 held-back records. I did not add the
   59-record public development panel. Should it be added?
7. **Slot decisions.** I counted the decoded slot decisions as part of the "full decoded answer" (stricter than the
   answer alone). Confirm.
8. **Environment lock.** Driver, cuDNN, Python and AMI are recorded, not pinned. The manifest itself says
   `NOT_READY_FULL_ENVIRONMENT_NOT_FROZEN`. The Helm 2.0 run recorded AMI `ami-0fbbd0facbc9e3cff`.
9. **P1 packaging.** No launcher exists for this module yet.
10. **Which plan file is "the plan".** The amended plan (blob `2462d158`) exists only on Codex's branch. The
    integration branch still carries the held plan (blob `3172a221`). The pins name Codex's copy.
11. **Spend.** `--check` still takes an operator-stated figure. The `budget_headroom_verified` prerequisite asks for a
    figure read from a record, but no runner reads one yet. The $30 stop before the third training job is still not
    enforced by code (Codex item 6).
12. **Fallback B admissions** still do not exist (review finding 6).

### 9.7 EXPOSURE (revision 2)

- **Git objects read** with `git show`, `ls-tree`, `diff`, `log`, `rev-parse`:
  - Codex's branch at `bc46b36e`: `REPRODUCTION_POLICY.json/.md`, `EXECUTION_MANIFEST.json`, `LAUNCH_REQUEST.json`,
    `STATISTICAL_POLICY.json`, `ROUTE_AND_CHECKPOINT_PROTOCOL.md`, `OWNER_STANDING_AUTHORIZATION_20260924.json/.md`,
    `PREPARATION_AUTHORITY.md`, the amended plan (head only), `CODEX_AMENDMENTS_20260924.md`, and the sha256 of
    `COST_*`, `CURRENT_COORDINATION_STATE.json`, `LEDGER_RECONCILIATION.json`, `SMOKE_*`, `EVALUATION_DESIGN_v0_4.md`
    and `AGENTS.md` (hashes only, to check the launch request's pins). The diff to `4489cc62` for two files.
  - The integration branch: `ca68690b` (Claude's owner record), and the plan blob ids at `197caa32`, `7b6e25f8`,
    `ca68690b` and its tip `51917b06`.
  - The Helm 2.0 receipt at `c8d5c430`: `final_checkpoint.json`, `course_p10_predictions.json`,
    `course_p10_scoring.json`, `worker_report.json`; the top-level `result.json` (key names and the preflight AMI id
    only; it embeds ledger snapshots, and I printed none of their content); file listings (names, sizes, blob ids;
    sealed and `_eval.jsonl` names filtered out).
- **Files read in this worktree** (source `20208c92`, not edited): `pointer_learner.py`, `learner.py`,
  `pointer_contract.py`, `encoder.py`, `gpu_adapter.py`, `cncm/typed_pointer_worker.py`, `typed_matched_worker.py`,
  `typed_course_worker.py`, `typed_practice_worker.py`, `typed_pointer_launch.py` (`validate_owner` only),
  `requirements-gpu.txt`, `public_course.json`, and the package `source.zip` member names.
- **Network:** `git fetch origin` with explicit refspecs for `codex/helm-controlled-prelaunch-20260924` (the gate moved
  its tracking ref to `4489cc62`) and `research/helm-integration-20260923` (to `51917b06`); the `git push` of this
  commit.
- **Written outside this worktree:** three scratch scripts in the session scratchpad (`write_admission.py`,
  `mutants.py`, `live_gates.py`).
- The tool harness saved one long listing under `C:/Users/wakil/.claude/projects/.../tool-results/`. I did not open it.
- **Not opened:** any `*_eval.jsonl`, anything named sealed, `D:/tksCAS-archive/`, any salt, the meta1 ledger (not
  even an existence check), S3 or AWS, Claude transcripts, Codex's working copy.

## 10. Revision 3 (2026-09-24): review of 303c281b fixed

**Label:** `CLAUDE_BUILT_CLAUDE_CHECKED`. Built by Claude as the temporary builder. Not an owner signature. Not yet
reviewed. The review and the disposition of all 14 findings are in `REVIEW.md`, section "Review of 303c281b".

### 10.1 In plain words

- **The reader can now be admitted.** Before, the policy had to hold the reader's digest while the reader held the
  policy's hash. That can never match. Now the policy hashes live in `policy_pins.json`, which the reader digest does
  not cover. Codex can freeze the policy with the digest, and a re-pin does not change it.
- **Nothing passes on its own say-so.** Each of the six prerequisites must name a committed receipt. The code opens
  it and checks what is inside. The money gate reads the spend from a committed spend record, not from typed text.
- **A broken machine is not a wrong answer.** A CUDA fault or out-of-memory error during the panel now stops the
  study (`ADMISSION_INVALID_STOP`). Only the historical model's own coded refusals count as answers.
- **The reader re-checks instead of trusting.** It re-reads the admission at the receipt commit, checks that the
  freeze came before the result, checks the training machine (AMI) and the shipped package, and requires the READING
  mode.

### 10.2 Clause map corrections (supersede the matching rows of 9.2)

| Policy clause | What the code does now | Code |
|---|---|---|
| "equal-state/different-envelope, changed-value, **changed-buffer**, missing-key, dtype-change, altered-output and corrupt-reference checks" | changed-buffer is **VACUOUS** for this architecture: no file in `cas_meta2/typed_teaching/` at `20208c92` calls `register_buffer` (I checked); the reviewer also found all 48 state entries at `c8d5c430` are learnable names. The AWS acceptance records `changed_buffer` as VACUOUS with the reference's buffer list and passes it only while that list is empty. A SYNTHETIC pure test shows a changed buffer reads DOES_NOT_REPRODUCE. Not "built" in the sense of a real variant | `re` `acceptance_mode`, test `test_a_changed_buffer_is_a_valid_mismatch_SYNTHETIC` |
| `file_mismatch_alone_triggers_fallback: false`; file identity "never decides" | still true for decide(). BUT a **binding rule** also exists: a candidate file hash equal to Helm 2.0's own is misbound evidence (final.pt embeds the run id) and reads INVALID. So FILE_IDENTICAL cannot occur in a valid full reading | `rr` `new_reading` (the CONTRADICTION check) |
| envelope "root ... reported only" | reported, AND a **binding rule**: the root must be the recorded historical root, because the historical loader rebuilds its role tagger from `init_args.root` | `rr` `evaluate_evidence` |
| continuation = "optimizer tensors/scalars, every saved RNG stream, cursor/model revision and training counters" | the starting-state identity is no longer here. It is training configuration: a difference is INVALID (route protocol: checked "before its first optimizer update"). Open question 10.6-D | `rc` `TRAINING_RUN_IDENTITY` |
| `frozen_before_reproduction_result_required: true` | in `READER_RULE`; the reader enforces it over git history (one freeze commit before and without the result; one version of the evidence and of the receipt result; admission unchanged after the freeze) | `rr` `history_violations`, `collect_history` |
| "A preparation-only path must not require inventing launch approval"; "bind ... exact final packet/policy/source hashes; require all technical and budget admissions" | unchanged for the dry run. For ADMITTED, every prerequisite receipt is opened from a committed blob and checked by content | `rc` `read_prerequisite_receipts`, `prerequisite_violations` |
| "Failed/refused records remain records" | only a historical coded refusal (`POINTER_`/`TYPED_`) is a record. Any other fault invalidates the evidence (open question 10.6-B) | `re` `classify_prediction_error`, `rr` `panel_row_faults` |

### 10.3 P1 on AWS: what changed

- Ship `policy_pins.json` next to the three reader sources. `repro_common.py` reads it at import and stops if it is
  missing or malformed.
- The acceptance now has 11 registered cases (`repro_common.ACCEPTANCE_CASES`), in this order: self identity, equal
  state with a new envelope, continuation-only difference, changed value, changed encoder state, missing key, dtype
  change, altered output, changed buffer (VACUOUS), state equal with one answer tampered, corrupt reference.
  `READER_ACCEPTANCE_PASS` needs all 11, in order, passed.
- The receipt also records `policy_pins_sha256`. It is taken before Codex's freeze, so after a re-pin its pins differ
  from the admitted ones. That is expected. The admission checks the receipt's reader digest, panel and environment,
  not its pins.
- The P1 slot has been split by Codex into P1a (route only; launched) and P1b (reader, probe, admission). This
  acceptance belongs to P1b.

### 10.4 How to run it now (supersedes 9.4)

```bash
python -B "$D/test_unchanged_repro.py" -v                              # 99 pure-Python tests
python -B "$D/prepare_unchanged_repro.py" --print-admission-bindings   # read-only; bindings, receipt kinds, pins sha
# Not on the laptop (imports the launcher): --dry-run (preparation only), --write (needs ADMITTED).
python -B "$D/prepare_unchanged_repro.py" --check --study-sha256 <hex>  # spend read from the admitted spend record
python -B "$D/read_reproduction.py" --receipt-commit <commit>          # exit 0 valid verdict, 2 INVALID_STOP, 1 tool stop
```

To admit the job later, each prerequisite entry in `EXECUTION_ADMISSION.json` needs `status: PASS`,
`receipt_commit`, `receipt_path` (relative to the CNCM folder) and `receipt_sha256`. The receipt must be committed in
this branch's history, or be the pinned policy file at the pinned commit. `--print-admission-bindings` lists the
receipt schemas.

### 10.5 Checks

See `REVIEW.md`, "R3.5 Checks". In short: 99 of 99 tests pass, none skipped; every mutant in the mutation check was
caught; the live gates give owner authorization granted and execution admission `NOT_READY` with 16 named reasons;
`--check` and the reader stop with named tool stops. Nothing imported torch or the launcher. No AWS call. No money
spent.

### 10.6 Open questions (new or changed; earlier ones in 9.6 stay open unless named here)

- **A (new).** The frozen launch packet must not contain `policy_pins.json` or `EXECUTION_ADMISSION.json`, or a new
  hash cycle appears. What does the packet contain?
- **B (extends 9.6 question 4).** Only a historical coded refusal is a panel record; every other fault invalidates the
  evidence. Confirm.
- **C.** Accept changed-buffer as VACUOUS for this architecture.
- **D.** Confirm the starting-state identity as training configuration (INVALID), not continuation.
- **E (replaces 9.6 question 2).** Codex's branch moved to `42ad8367`: plan, manifest, launch request and amendments
  changed; the reproduction policy did not. Re-pin after review? It is now a data-only change.
- **F (replaces 9.6 question 11).** Who writes the spend record, from which sources, and how fresh must it be at
  `--check`? No age limit is enforced. The $30 stop before the third training job is still not enforced by code.
- **G.** A separate, unpushed history could hold a different single evidence version. Should the reader also require
  the receipt commit to be in the fetched tip of this branch?
- **H.** The review-receipt verdict word `NO_BLOCKER_OR_MAJOR_FINDING_OPEN` is mine; rename if Codex prefers.
- **I.** The environment-lock receipt is checked only by the manifest's sha256 and `dependencies.status`.
- Still open from 9.6: 1 (P1 machine type: T4 vs RTX PRO 4500), 3 (missing key / dtype change; now aligned in the
  tests, ruling still needed), 5 (route), 6 (panel scope), 7 (slot decisions), 8 (environment lock; now partly checked
  through the preflight AMI), 9 (P1 packaging), 10 (which plan file), 12 (fallback B admissions).

### 10.7 EXPOSURE (revision 3)

See `REVIEW.md`, "R3.8 EXPOSURE". Same session, same reads.
