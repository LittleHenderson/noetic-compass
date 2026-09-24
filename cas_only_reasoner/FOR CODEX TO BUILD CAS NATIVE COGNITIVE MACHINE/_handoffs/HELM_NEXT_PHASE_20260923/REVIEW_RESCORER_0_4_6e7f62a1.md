# Review: trusted_rescore 0.4, historical-compatibility mode (commit 6e7f62a1)

- Label: **CLAUDE_BUILT_CLAUDE_CHECKED** (temporary takeover while Codex is away).
- Reviewer: a fresh Claude session, adversarial brief, 2026-09-23. Same model family as the builder.
  So this is **not** the independent review the builder asks for in section 10, item 8.
- Branch `claude/helm-rescorer-compat-20260924`, worktree `D:/tksCAS-worktrees/helm-rescorer`, commit `6e7f62a1`.
- Cost: $0. No AWS. No torch. No checker import. Only small pure-Python checks, one at a time, each under 2 minutes.
- File hashes match the builder's report: `trusted_rescore.py` `2f10feac...`, `test_historical_compatibility.py`
  `e9027873...`, `test_trusted_rescore.py` `154706e8...`, `history/trusted_rescore_0_3.py` `50295072...`,
  `test_historical_rescore_rule.py` `58d95cf0...`.

## Verdict: CHANGES_REQUIRED

- **1 BLOCKER, 2 MAJOR, 2 MINOR, 4 NOTE.**
- The historical mode itself is sound. It is narrow, and it is pinned by content hash to the two named studies.
  I could not get a new run, an altered record or a substitute file through it.
- The six historical decisions are right. I re-derived them myself from the frozen grader readings, without
  importing the tool.
- But three things break the owner's words:
  - **BLOCKER 1.** In the default (trusted) mode, `--check-reading` accepts a hand-edited reading. It gives exit 0
    and `READING_VERIFIED` for counts that no rescore produced. That includes a run that truly fails.
  - **MAJOR 2.** Coordinator decision (1) is not in the code. Missing checkpoint weights still pass, in both modes.
  - **MAJOR 3.** `--out` can overwrite original records that are not on the frozen list. It still reports success,
    and the warning still says "never rewritten".

## What I checked, and what held

| Question in my brief | Result | How |
|---|---|---|
| Are the six historical decisions reproduced? | **Yes** (from the recorded counts; the full 564-record rescore is NOT_RUN, it needs AWS) | My own script recomputed every p and decision from `admission_helm1_certified/gate_reading.json` and `admission_001/gate_reading.json`. It matched the frozen list, all six. The CLI check of the Helm 2.0 reading gave exit 4 and printed all three seeds. |
| Is the builder's finding true (0.2 applied the veto)? | **Yes** | `git show 8b2bb942` line 437: `len(gained) >= MIN_PASSING_B and len(lost) == 0 ...`. The 0.2 Helm 2.0 reading records seed `20260917` (11/1) as `passed: false`. The frozen grader says `true`, p = 13/4096. The label `NO_TRANSFER_TO_NEW_WORLDS` does not change: seed `20260919` (7/1, p = 9/256) fails under both rules. |
| Do the frozen digests pin the named records? | **Yes** | All three constant digests recompute. All 12 pinned files match the disk. Both anchors record exactly the recognised mistake. The 0.2 tool digest `8e9a751a...` matches git `8b2bb942`. The 0.3 copy `50295072...` matches git `60e382b0` and `ec80730c`. |
| Is the rule the owner's rule? | **Yes** | `HISTORICAL_RULE` = b > c, exact one-sided p <= 1/100, at least 2 kinds and 2 worlds, no zero-loss veto. It matches `evaluate_gates.py` (`d3e0ea97...`) lines 283-321. |
| Can a new run get the exception? | **No** | Only anchor and reading content hashes on the frozen list qualify. An off-list anchor or reading is `HISTORICAL_EXCEPTION_UNKNOWN_*`, even with the flag. The study, the predictions and the receipts are all pinned behind the listed anchor. Overrides and substitute frozen readings are refused. |
| Can a listed original be rewritten? | **No** | The guard covers every listed original. Sandbox tests pass. (Unlisted originals: see MAJOR 3.) |
| Are the warning and both rule descriptions shown? | **Yes** | Printed on the command line as a side-by-side table, and stored in the output. |
| Are the exit codes unambiguous? | **Partly** | 4 is only ever a historical pass (decision (2) kept). But 0 and 2 each mean several things (BLOCKER 1, MINOR 5). |

Targeted tests I ran (fast only, one command at a time, no bytecode written):

- `test_historical_compatibility.py`, 43 of 43 fast tests, in four runs: 6 + 13 + 23 + 1 passed.
- `test_trusted_rescore.py`, the 3 fast tests the builder edited: 3 passed.
- Total: 46 passed, 0 failed. The 2 slow tests in the new file are NOT_RUN (AWS).
- `git status` after all runs: clean.

## Findings, most severe first

### BLOCKER 1: trusted `--check-reading` accepts a reading with forged counts, and returns exit 0

- **Where.** `trusted_rescore.py:1219-1258` (the trusted branch of `_check_reading_body`), `:1251`, `:1366`.
- **What it does.** In trusted mode, `--check-reading` re-derives each decision from the counts the reading
  **records**. It never checks those counts against anything. It does not rescore. It does not compare with the frozen
  grader's reading. It does not check that the counts are even possible.
- **Failure scenario (I ran this, in a temp folder, on copies).**
  - I made a new run from copies of Helm 2.0 seed `20260919`'s four label files. The truth for these predictions is
    7 gains, 1 loss, p = 9/256, **FAIL**.
  - I wrote a fresh 0.3 anchor for it. The file checks all pass.
  - I hand-wrote a 0.4 reading that says 12 gains, 0 losses.
  - Results of `check_reading(..., historical_compatibility=False)`:

| Hand-written reading | Exit | Verdict | Label |
|---|---|---|---|
| 12 gains / 0 losses (the truth is 7 / 1, FAIL) | **0** | `READING_VERIFIED` | `LEARNS_NEW_WORLDS` |
| 99 gains, in an 18-question population | **0** | `READING_VERIFIED` | `LEARNS_NEW_WORLDS` |
| `kinds_improved: ["reach", "reach"]` (one kind, counted as two) | **0** | `READING_VERIFIED` | `LEARNS_NEW_WORLDS` |
| no `p_one_sided` field at all | **0** | `READING_VERIFIED` | `LEARNS_NEW_WORLDS` |

- **Why it matters.**
  - This is the same class of forgery that the 2026-09-20 audit found in the frozen grader: an edited result file
    produces a pass label. The tool exists to stop exactly that.
  - It breaks the owner's words: "Reject unknown, altered, incomplete, or incompatible evidence for trusted
    acceptance." A reading whose counts no rescore produced is unknown evidence. A missing `p_one_sided` is incomplete.
  - Exit 0 is also what a full `RESCORE_OK` returns. A script cannot tell "every prediction was re-checked" from
    "the counts in a file were believed".
  - The builder's report (section 1, section 11) presents this path as trusted acceptance.
- **Why the historical branch does not have this problem.** There, the reading must be on the frozen list by hash, and
  its counts must agree three ways: with the frozen grader reading, with the frozen list, and with the replay.
- **Suggested fix.**
  - A trusted `--check-reading` must never give trusted acceptance or exit 0. Give it its own verdict and exit code, for
    example `READING_CONSISTENT_NOT_RESCORED`, exit 5. Trusted acceptance must come only from a full rescore.
  - Also add plain sanity checks, in both modes: `p_one_sided` required; `kinds_improved` without duplicates and
    drawn from the anchor's `kind_of`; `gained + broken` at most the population size; `worlds_improved` at most
    `gained`; every recorded check `PASS`.
  - Where the reading names a frozen grader reading, compare counts, decisions and breadth with it, as the
    historical branch does. This narrows the gap but cannot close it alone: the frozen grader reading is itself
    built from scoring files, and those were the ones forged on 2026-09-20.
  - Add a fast test with forged counts. The current test (`test_trusted_check_reading_accepts_a_clean_0_4_reading...`)
    flips only `passed`, so it cannot see this.

### MAJOR 2: coordinator decision (1) is not implemented; missing checkpoint weights pass in both modes

- **The decision.** An absent or unverifiable checkpoint weight file is INCOMPLETE evidence. It is refused for
  trusted acceptance in both modes. Tests that need the real weights become AWS/slow tests.
- **Historical mode, where.** `trusted_rescore.py:567-591`. An absent `.pt` file only increments `absent_here`, and
  the status becomes `RECORDED_DIGESTS_ONLY`.
  - **I ran this.** `--historical-compatibility --check-reading` on the Helm 2.0 reading: all **15 of 15** checkpoint
    files are absent here. Yet `HISTORICAL_EVIDENCE = PASS`, the detail says "19 original evidence items verified",
    and the exit is **4**.
  - Also, a seed with some checkpoints present and some absent gets the status `MATCH` (`:589-590`). That overstates it.
- **Trusted mode, where.** `safe_anchor_part` (`:634-650`) and `_safe_checks` (`:809-889`). Trusted mode never reads
  the run's `artifact_manifest.json` and never looks at a checkpoint.
  - **I ran this.** My new-run folder had no manifest and no weights at all. Every file check was `PASS`.
  - The 0.3 anchor schema has no field that pins checkpoints or the run manifest. So trusted mode cannot implement
    decision (1) without a schema change.
- **Tests that assume the old behaviour.** `test_historical_compatibility.py:435` accepts `RECORDED_DIGESTS_ONLY`.
  `:378` (six decisions, exit 4) and `:441` (sandbox accepted) pass only because absent weights are allowed. The slow
  `test_clean_copy_through_the_command_line...` in `test_trusted_rescore.py` expects a trusted pass on a sandbox with
  no weights. Under decision (1), each must either assert the refusal locally, or move to AWS/slow with the real weights.
- **Ordering risk with decision (3).** The coordinator plans to write fresh correct-rule anchors on AWS. If that
  happens before the 0.3 schema gains checkpoint (or manifest) pins, those anchors will be out of date on arrival.
  Anchors are create-only, so each redo needs yet another file name. **Fix MAJOR 2 before decision (3) runs.**
- **Suggested fix.**
  - Historical mode: an absent or unverifiable checkpoint adds `HISTORICAL_EVIDENCE_INCOMPLETE` (named, never PASS,
    never exit 4). A partial seed must not be `MATCH`.
  - Trusted mode: pin the run manifest digest and every checkpoint digest in the new anchor. Verify them in
    `_safe_checks`. Refuse an absent or altered one by name.
  - Say in `HISTORICAL_EVIDENCE`'s detail how many items were byte-checked, not only how many were listed.

### MAJOR 3: `--out` is not create-only, so unlisted original records can be overwritten, with a success exit

- **Where.** `trusted_rescore.py:489-494` (`open(out_path, "w", ...)`) and the guard `protected_paths` (`:431-446`).
- **What it does.** The guard refuses an `--out` only if it is a record on the frozen list, or a file named on the same
  command line. Anything else is silently overwritten.
- **Not covered by the guard (I checked each path; nothing was written):**
  - `aws_rescore_job/results/trusted_rescore_reading_helm1_certified.json` and `..._helm2_experimental.json`. These are
    the owner-approved AWS copies of the two historical readings. The builder's own tests treat them as historical readings.
  - `study_helm1_certified.json` (when Helm 2.0 is the study in use) and `admission_001/study.json` (when Helm 1.0 is).
  - `evaluate_gates.py`, every checker source, `trusted_rescore.py` itself, and `history/trusted_rescore_0_3.py`.
  - Every record of every new run: its predictions, scoring files, manifest, anchor and earlier readings.
- **Failure scenario (I ran this in a sandbox copy only).**
  - `check_reading(<Helm 2.0 reading>, out=<sandbox copy of the AWS reading copy>, historical_compatibility=True)`:
    exit **4**, and the AWS copy was replaced by the check record.
  - The same with `out=<sandbox copy of study_helm1_certified.json>`: exit **4**, and the study file was replaced.
  - In both cases `ORIGINALS_UNCHANGED = PASS`. The printed warning still says "The original records were read,
    never rewritten" (`:193`).
- **Why it matters.** The owner said: "Never rewrite the original record." The builder's report says "Any output path
  that is an original record is refused". That is true only for the frozen list. A realistic trigger: an adapted
  `job.sh.template` that writes new readings into `aws_rescore_job/results/`.
- **Suggested fix.**
  - Open `--out` with mode `"x"` (create-only), exactly like `write_anchor` already does. That also defeats hard links.
  - Refuse an existing `--out` by name, before any work, not after.
  - Adjust the test helpers that reuse one output name (`check()` and `safe()` write `check.json` / `reading.json`
    again and again), and the AWS commands in the builder's section 9.

### MINOR 4: the "frozen constants" check does not cover everything the tool applies

- **Where.** `trusted_rescore.py:106`, `:346-357`, `:387-396`, `:121-133`.
- **What it does.** `TOOL_CONSTANTS` hashes the rule **description** (`HISTORICAL_RULE`), the wrong description, and
  the frozen list. But the decision itself uses the module constants `MIN_IMPROVED_KINDS` and `MIN_IMPROVED_WORLDS`,
  a hard-coded `b > c`, a hard-coded absence of the veto, and a hard-coded all-seeds label. Only `alpha` is read from
  the hashed dict. In `RECOGNISED_MISTAKE`, only `recorded_description` is hashed; `written_by_tool_sha256_lf`,
  `anchor_schema` and `reading_schema` are not.
- **I ran this (in memory only).** Setting `MIN_IMPROVED_KINDS = 1` leaves `constants_problems() == []`, and 12/0 with
  **one** kind then passes. Editing `written_by_tool_sha256_lf` also leaves it `[]`.
- **Limits.** In historical mode, a changed rule would still be caught if it changed one of the six decisions. The
  774 tests in `test_historical_rescore_rule.py` also cover the decision function. Any self-hash is only a tripwire:
  whoever edits the file can edit the digest too. The real pin is the tool's own file digest, `2f10feac...`.
- **Suggested fix.** Read every threshold from `HISTORICAL_RULE` in `historical_decision`. Hash the whole
  `RECOGNISED_MISTAKE`. Record the 0.4 tool digest wherever the coordinator records accepted tools.

### MINOR 5: exit codes 0 and 2 each carry several meanings, and one malformed reading crashes

- **Exit 2** means `REJECT`, but also an argparse usage error (`:1385`, `:1388`) and `ANCHOR_REFUSED`.
  - **I ran this.** `--check-reading x.json --study y.json` exits 2 with only a usage message and no record.
- **Exit 0** means `RESCORE_OK`, but also `READING_VERIFIED` (BLOCKER 1) and "anchor written" (`:685`).
- **Exit 1 (a crash).** A reading whose `anchor.path` is a JSON object crashes at `:1196`
  (`TypeError`), with a traceback and no record. A `--receipt` value without `=` crashes at `:1391`
  (found by reading the code; not run).
  - **I ran this.** A 0.4-schema reading with `"anchor": {"path": {"x": 1}, ...}` exits 1.
  - Every one of these fails closed. None is a pass. But the owner asked for refusals by name.
- **Suggested fix.** Give usage errors their own code (for example 64). Catch malformed fields and refuse them as
  `READING_MALFORMED` or `ANCHOR_MALFORMED`. Give "anchor written" and the check-only verdict codes of their own.

### NOTE 6: the 0.4 historical readings that AWS will write can never pass `--check-reading`

- The builder's section 9, step 3, writes `historical_compat_reading_*_0_4.json` on AWS.
- `--check-reading` will refuse those files in both modes. In historical mode they are `HISTORICAL_EXCEPTION_UNKNOWN_READING`
  (only the two 0.2 readings are listed). In trusted mode they are `RULE_DESCRIPTION_MISMATCH`.
- That may be the right design, because the frozen list pins only the originals. But then the only way to verify them
  again is a new 14-minute run. Section 9 should say so.

### NOTE 7: trusted acceptance is reachable without the frozen grader comparison and without a run manifest

- `--no-frozen-reading` makes `FROZEN_GRADER_AGREEMENT = NOT_REQUESTED`, and `RESCORE_OK` (exit 0) is still possible.
- No run manifest is needed either (MAJOR 2).
- The coordinator should decide whether a trusted pass without these counts as "incomplete evidence". Once MAJOR 2
  is fixed, the manifest will be required anyway.

### NOTE 8: coordinator decisions (2), (4) and (5)

- **(2) Exit code 4 kept.** The code does this. 4 is returned only for `HISTORICAL_COMPATIBILITY_OK`, in both
  `rescore` and `check_reading`, and only in historical mode. No gap.
- **(4) Nested study pins stay open for Codex.** The code does not re-verify them (consistent). The builder's report
  still lists this as a question (section 10, item 4). It should be restated as an open item for Codex.
- **(5) BRAIN_LINEAGE.md is not rewritten.** Confirmed: commit `6e7f62a1` touches only the five files in its report.
  Two details for the Codex list:
  - At this commit, the wrong seed-`20260917` decision is at `BRAIN_LINEAGE.md` **lines 300 and 302-304**
    ("per seed: 20260917 False ..." and "the gate requires zero broken on every seed"). Line 265 is about the one-hop
    adjacency rule. The ":265" may come from another branch's numbering.
  - Lines 17-27 already hold a dated correction that "takes precedence" (PASS, PASS, FAIL; no zero-loss veto).
  - The builder's report (section 10, item 5) does not list it for Codex yet.

### NOTE 9: decision (3) can go ahead only after MAJOR 2

- The builder's section 9, step 5, gives the right commands for fresh correct-rule anchors under new names.
- But see MAJOR 2: the anchor schema must first gain checkpoint (or manifest) pins. Otherwise the fresh anchors would
  pass trusted mode without any weight check.

## What must happen next

1. The builder fixes BLOCKER 1, MAJOR 2 and MAJOR 3, and adds a fast test for each failure scenario above.
2. MINOR 4 and MINOR 5 in the same revision, if cheap.
3. Only then does the coordinator run the AWS steps: the full historical readings, the slow tests, and the fresh anchors.
4. A re-review of the revision. An independent (non-Claude) review is still owed.

## Claim status

- **Ran here:** my independent recomputation script; the Helm 2.0 historical `--check-reading` (exit 4); the four
  forged-reading probes (BLOCKER 1); the guard membership and sandbox overwrite probes (MAJOR 3); the in-memory
  constant probes (MINOR 4); the two exit-code probes (MINOR 5); 46 targeted fast tests.
- **Not run:** the full 564-record historical rescore, all slow tests, and `--write-anchor` (each loads the course;
  AWS only).
- **Not checked:** the nested study pins (decision (4)); whether the ledger or the audit pack quote the wrong
  per-seed value.

## EXPOSURE: every file outside my working copy that I opened or that reached me

- **Pre-loaded into my context by the tool that runs me. I did not open these:**
  - `C:\Users\wakil\.claude\CLAUDE.md`;
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\CLAUDE.md`;
  - the auto-memory index `C:\Users\wakil\.claude\projects\C--Users-wakil-OneDrive-Desktop-tksCAS\memory\MEMORY.md`.
    It names the sealed-test archive folder and some sealed-build facts (for example "HSET-1A reach W=2"). It holds
    no TEST world, record id or answer.
- **The shared git object store, through git commands only:**
  `C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/vision-next/.git`.
  - `git show` of `records/typed_pointer_001/trusted_rescore.py` at `8b2bb942`, `60e382b0` and `ec80730c` (hashed;
    lines 430-440 of `8b2bb942` read);
  - `git show HEAD:.../BRAIN_LINEAGE.md` (not in the sparse checkout): lines 17-28, 263-266 and 296-306 read, plus one grep;
  - `git diff` of `test_trusted_rescore.py` between `ec80730c` and `6e7f62a1`;
  - this worktree's sparse-checkout list, `.../.git/worktrees/helm-rescorer/info/sparse-checkout` (read only, not changed);
  - `git ls-remote origin` for this branch (GitHub, not AWS).
- **Not project files:** the Python install (`C:\Python314`, standard library and pytest).
- **My scratchpad** (`C:/Users/wakil/AppData/Local/Temp/claude/C--Users-wakil-OneDrive-Desktop-tksCAS-cas-only-reasoner/5e8709f4-3151-444f-939b-317c01bc3568/scratchpad`):
  `indep_check.py`, `probe_forged_reading.py`, `probe_out_and_constants.py`, `h2_check.json`. The probe sandboxes held
  copies of files from this worktree only, and were removed.
- **Temporary test folders** under the system temp directory, made by the builder's tests. They held copies of files
  from this worktree only. `test_the_committed_anchors_are_the_pinned_ones...` uses `tempfile.mkdtemp()` without
  cleanup, so a few small `safe.json` folders remain there.
- **Not opened:** `D:/tksCAS-archive/`, any `*SEALED*`/`*sealed*` file, any `*_eval.jsonl`, any hset1a/hset1b path,
  S3/AWS, the meta1 ledger, other worktrees' files, and Claude transcripts.
