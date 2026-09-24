# Builder report: rescorer historical-compatibility mode (trusted_rescore 0.4)

- Builder: Claude (temporary builder while Codex is away until 2026-09-28).
- Branch: `claude/helm-rescorer-compat-20260924`, worktree `D:/tksCAS-worktrees/helm-rescorer`.
- Based on: `ec80730c`.
- Cost: $0. No AWS. No torch. No full rescore on the laptop.
- Custody: `EVALUATION_NOT_INDEPENDENT`. Claude built this. Claude also wrote the review it relies on
  (`0d8e8316`). An independent review of 0.4 is still needed.

## 1. What the owner asked for, and where each part is

Owner direction 2026-09-24, item 2 (RESCORER):

| Owner's words | Where it is in 0.4 |
|---|---|
| "explicit historical-compatibility mode for the recognized old grading-description mistake only" | The flag `--historical-compatibility`. Every output records it in `mode`. It accepts one frozen mistake (`RECOGNISED_MISTAKE`) on one frozen list (`HISTORICAL_EXCEPTION`). |
| "Require verified original evidence" | Every hash the anchor names, plus frozen digests for the frozen grader reading and each run manifest. Also the four label-deciding files per seed and the checkpoint digests as recorded. |
| "apply the preserved historical rule" | `HISTORICAL_RULE` (b > c, exact one-sided p <= 1/100, at least 2 kinds and 2 worlds, no zero-loss veto). The recorded description is never applied. |
| "Show the warning and both rule descriptions" | `WARNING` text and a side-by-side table. Both are printed and both are stored in the output. |
| "Never rewrite the original record" | Anchors are create-only. Any output path that is an original record is refused. Originals are hashed byte for byte before and after every run. |
| "Reject unknown, altered, incomplete, or incompatible evidence for trusted acceptance" | Named reasons, in both modes (section 4). |
| "New runs do not receive the historical exception" | Only the two frozen anchors and the two frozen readings qualify, matched by content hash. Anything else is `HISTORICAL_EXCEPTION_UNKNOWN_ANCHOR` / `_READING`, even with the flag. |

## 2. A finding you should know first

The 0.2 tool did not only **describe** the wrong rule. It also **applied** it:
`passed = len(gained) >= 7 and len(lost) == 0 and ...` (git `8b2bb942`, line 437).

- Effect on the committed 0.2 reading of Helm 2.0 experimental:
  - seed `20260917` had 11 gains and 1 loss;
  - the 0.2 reading records it as `passed: false`;
  - the frozen grader decided `passed: true` (p = 13/4096).
- The label is not affected: `NO_TRANSFER_TO_NEW_WORLDS` either way. Seed `20260919` (7 gains, 1 loss, p = 9/256) fails under both rules.
- The 0.2 comparison did not catch this. It compared counts only, not decisions.
- The other five recorded decisions match history.
- The compatibility mode re-derives the historical decision (`true`). It also shows the recorded one (`false`) and
  flags it as `recorded_decision_differs_from_history`.
- It confirms the recorded `false` is exactly what the recognised wrong description gives. A record that disagreed
  with the recognised mistake would be refused as `HISTORICAL_EXCEPTION_INCOMPATIBLE`.

## 3. Design

### Trusted mode (the default, no flag)

- The anchor is read strictly. Duplicate keys or non-finite numbers → `ANCHOR_MALFORMED`. So a second, hidden
  `pass_rule` key cannot slip through.
- Unknown schema → `ANCHOR_SCHEMA_UNKNOWN`. A missing field → `ANCHOR_INCOMPLETE`.
- The recorded `pass_rule` is compared by the sha256 of its canonical JSON bytes with the preserved rule.
  - Any difference → `RULE_DESCRIPTION_MISMATCH`. The detail says whether it is the recognised mistake or an unrecognised description.
  - For the two historical anchors it also says they can be read only with `--historical-compatibility`.
- A 0.2-schema anchor → also `ANCHOR_SCHEMA_OUTDATED`.
- A refused anchor stops everything behind it. The checker code is never imported.
- New anchors use schema `cncm.trusted-rescore-anchor/0.3`. They carry `pass_rule` = the preserved rule,
  `pass_rule_sha256` and `tool_version`.
- `--write-anchor` is create-only. It refuses an existing file. It refuses any original path on the frozen list,
  even after that file is deleted. It refuses the historical flag.

### Historical-compatibility mode (`--historical-compatibility`)

1. The anchor's sha256_lf must be on the frozen list. Otherwise `HISTORICAL_EXCEPTION_UNKNOWN_ANCHOR`, plus
   `RULE_DESCRIPTION_MISMATCH` if its rule is wrong. Nothing behind it is read.
2. Its recorded rule must be exactly the recognised mistake (canonical sha256 `8e74f079...`). Its schema must be 0.2.
   Its writing tool must be 0.2 (`8e9a751a...`).
3. Original evidence, all by hash (`HISTORICAL_EVIDENCE`):
   - the frozen grader reading (frozen digest);
   - each seed's run manifest `artifact_manifest.json` (frozen digest);
   - the four label-deciding files per seed (`course_p00/p10_predictions/scoring.json`), against the run's own manifest;
   - the anchor's prediction pins must equal the manifest's digests;
   - checkpoint digests "as recorded": every `.pt` row must carry a well-formed digest. A checkpoint that is present
     must match. One that is absent here is reported as `RECORDED_DIGESTS_ONLY`, not refused. See open question 1.
   - Then the usual checks: the study, the grader, all 18 checker sources, the predictions (ids, duplicates, finite numbers).
4. Refused in this mode:
   - receipt overrides → `HISTORICAL_EXCEPTION_REQUIRES_ORIGINAL_EVIDENCE`;
   - a substitute `--frozen-reading` → the same reason;
   - `--no-frozen-reading` → `HISTORICAL_EXCEPTION_REQUIRES_FROZEN_READING`;
   - receipts found outside the package → `HISTORICAL_EVIDENCE_INCOMPLETE`.
5. The full rescore (cloud only) applies the preserved rule. It must reproduce:
   - the frozen grader reading (`FROZEN_GRADER_AGREEMENT`);
   - the six frozen decisions and the label (`HISTORICAL_DECISIONS`).
6. The verdict is `HISTORICAL_COMPATIBILITY_OK` with exit code **4**, never 0. A script that expects 0 cannot
   mistake the exception for plain trusted acceptance.

### Fast path: `--check-reading` (no checker import, about 1 to 2 seconds)

- It verifies a committed reading without rescoring.
- In historical mode:
  - the reading must be on the frozen list;
  - its anchor and all evidence verify as above;
  - each seed decision is re-derived from the **recorded counts** with the preserved rule;
  - three sources must agree: the replay, the frozen grader reading, and the frozen list.
- In trusted mode:
  - a 0.2 or 0.3 reading → `RULE_DESCRIPTION_MISMATCH` and/or `READING_SCHEMA_OUTDATED`;
  - a clean 0.4 trusted reading → `READING_VERIFIED` (exit 0).

### Around both modes

- `TOOL_CONSTANTS`: the rule, the recognised mistake and the frozen list are re-hashed on every run. The list cannot grow silently.
- `ORIGINALS_UNCHANGED`: the raw bytes of the originals are hashed before and after each run.
- An `--out` that is any original record → `OUTPUT_WOULD_OVERWRITE_ORIGINAL`, and nothing is written.

### 0.3 kept as history

- Byte-identical copy: `records/typed_pointer_001/history/trusted_rescore_0_3.py` (sha256 `50295072...`, the digest the review names).
- Also in git at `60e382b0`.
- It cannot run from `history/`, because its paths resolve wrongly. It is a record, not a tool.

## 4. Named refusal reasons (new in 0.4)

| Kind | Reasons |
|---|---|
| unknown | `HISTORICAL_EXCEPTION_UNKNOWN_ANCHOR`, `HISTORICAL_EXCEPTION_UNKNOWN_READING`, `ANCHOR_SCHEMA_UNKNOWN`, `READING_SCHEMA_UNKNOWN` |
| altered | `HISTORICAL_EVIDENCE_ALTERED`, `READING_EVIDENCE_ALTERED`, `ORIGINAL_CHANGED_DURING_RUN`, `TOOL_CONSTANTS_ALTERED`, plus the existing `PREDICTIONS_IDENTITY`, `STUDY_IDENTITY`, `EVALUATOR_IDENTITY`, `CHECKER_CODE_IDENTITY` |
| incomplete | `ANCHOR_INCOMPLETE`, `READING_INCOMPLETE`, `HISTORICAL_EVIDENCE_INCOMPLETE`, `READING_EVIDENCE_INCOMPLETE` |
| incompatible | `RULE_DESCRIPTION_MISMATCH`, `RULE_DESCRIPTION_UNRECOGNISED`, `ANCHOR_SCHEMA_OUTDATED`, `READING_SCHEMA_OUTDATED`, `HISTORICAL_EXCEPTION_INCOMPATIBLE`, `HISTORICAL_EXCEPTION_REQUIRES_ORIGINAL_EVIDENCE`, `HISTORICAL_EXCEPTION_REQUIRES_FROZEN_READING`, `READING_NOT_TRUSTED`, `READING_NOT_CLEAN`, `HISTORICAL_READING_NOT_CLEAN`, `READING_INCONSISTENT` |
| malformed | `ANCHOR_MALFORMED`, `READING_MALFORMED`, `READING_UNREADABLE` |
| decisions | `HISTORICAL_DECISION_MISMATCH`, `READING_DECISION_MISMATCH` |
| originals | `OUTPUT_WOULD_OVERWRITE_ORIGINAL` |

## 5. Frozen constants (in `trusted_rescore.py`)

| Constant | Value |
|---|---|
| `HISTORICAL_RULE_SHA256` (canonical JSON of the preserved rule) | `986c66b067ac276bdfcc09e9fdabbc621b34671d65d454ad682683664195c7b2` |
| recognised wrong description | `{"all_seeds_must_pass":true,"broken_must_be":0,"min_improved_kinds":2,"min_improved_worlds":2,"min_passing_b":7}` |
| its canonical sha256 | `8e74f0793d18fa1ccc0290ca1871b113c96a74f156d6767f15e13166b2d60ff6` |
| tool that wrote it (0.2) | sha256_lf `8e9a751a15358043b8d1bbc7428fd0e475325174e58fe9e00ec5297cbdd5953a`, commit `8b2bb942` |
| `HISTORICAL_EXCEPTION_SHA256` (the whole frozen list) | `f2ea2b187a9a34cba1af3e08ed3a6e49a8f90c8468ead012f1c5b82c8e4a99b9` |

The frozen list. Paths are under `records/typed_pointer_001/`. All digests are sha256_lf.

| Record | helm1_certified | helm2_experimental |
|---|---|---|
| anchor | `trust_anchor_helm1_certified.json` `b1798323f6f7f9c9656b1c30eef724e94104715e180eb6724ad11c6c3b2b49ef` | `trust_anchor_helm2_experimental_20208c92.json` `f71fa001209eb0bb8a7ab980cae24c1dab394ca3f12ce333a84e985a76a1f834` |
| 0.2 reading | `trusted_rescore_reading_helm1_certified.json` `18265eab046b4604b9bb9fe9c00698260b00d0127dec210f6eea2be990cdd061` | `trusted_rescore_reading_helm2_experimental.json` `f0b470da443866b4e8e35a204a0383369d1caa2bd570c238af4eae33b9625602` |
| frozen grader reading | `admission_helm1_certified/gate_reading.json` `475379d2f9d47387a821c79e03a239f9a1f1277a0bbb25b298417557f9b058a9` | `admission_001/gate_reading.json` `52877c1670132c70dfd82e5e133e4e6ef90d8595a4b49387a6b0bace9f9d10d6` |
| manifest 20260917 | `454ebea561b057b639162b1ebb4680847c6f0c4e95914b4cc4679a81fd927f13` | `437e57e504f27979acfc85e56b87e8b52d4586c69576ad9a9a1da84618f77e46` |
| manifest 20260918 | `da9d0f5c188aacbe7942b8e123668b4f744a4483d175aeff391683a80ff9f2e1` | `2f8e3ac87c23c0592e2b48ebb121020018c3fc0fb3d1ff38da85a131c2309a7d` |
| manifest 20260919 | `44109895b4d412086f36f01f5f94be71c9f541ab3a89331bc3c1e88674825b6f` | `b9b65c668c8752294cb47df9edd5f4f13c63313b074effda3001dec3294a355f` |
| label | `LEARNS_NEW_WORLDS` | `NO_TRANSFER_TO_NEW_WORLDS` |
| decisions (b, c, p, passed) | 10/0 1/1024 T; 12/0 1/4096 T; 11/0 1/2048 T | 11/1 13/4096 T; 12/0 1/4096 T; 7/1 9/256 F |

Where these digests come from:

- The anchors were last changed at `64bf94a0` (the owner-approved AWS re-check). The AWS `job.log` in this repo
  records `b1798323...` and `f71fa001...` independently. Codex's test file pins them too.
- The readings were last changed at `64bf94a0`. The `aws_rescore_job/results/` copies are byte-identical.
- The frozen grader readings and manifests were last changed at `df20eb46` / `27fd5698`. `475379d2...` is the
  certificate digest named in `verify_evidence_hashes.py`.
- The six decisions equal the frozen grader readings and the review `0d8e8316`.

## 6. Files (all LF, so raw sha256 = sha256_lf)

| File | sha256 | Change |
|---|---|---|
| `records/typed_pointer_001/trusted_rescore.py` | `2f10feac675f39c3c60250ff01670ee56ac0928f386a2e665674c45411d96490` | 0.3 → 0.4 |
| `records/typed_pointer_001/test_historical_compatibility.py` | `e9027873ca31c080f6763e2a89b5c1f8bf75e4aaf8d23eb4803dcaabc559f7dc` | new |
| `records/typed_pointer_001/test_trusted_rescore.py` | `154706e87bb2edb065f92e7404d00e7d4f325bbe080f44faf66e02c539c44f09` | 4 expectations updated for 0.4 |
| `records/typed_pointer_001/history/trusted_rescore_0_3.py` | `50295072dd662fac1bf51021e8abd8395621ebafc8d35e8f8e4949120e35f8cc` | new, byte copy of 0.3 |
| `records/typed_pointer_001/test_historical_rescore_rule.py` | `58d95cf01d3eb01da18db7fefa6d087cc3ce82a2e9c621110cd8da8464d6458e` | unchanged, still passes |

Not changed: every anchor, reading, receipt, manifest, frozen grader reading, `evaluate_gates.py`, and the checker
and slot files. `git status` after every test run showed only the files above.

Edits to `test_trusted_rescore.py`. Each is a deliberate 0.4 behaviour change:

1. The trusted safe-only run now shows `HISTORICAL_EVIDENCE = NOT_REQUESTED`.
2. The committed 0.2 anchor in trusted mode is refused as `["RULE_DESCRIPTION_MISMATCH", "ANCHOR_SCHEMA_OUTDATED"]`.
   Before, it was `["ANCHOR_SCHEMA_OUTDATED"]`.
3. The committed anchors' "every pinned file is on disk" test now runs in historical mode. Trusted mode refuses them.
4. A slow test's all-PASS assertion now allows the two `NOT_REQUESTED` historical checks.

## 7. Tests, and what each covers

`test_historical_compatibility.py` holds 45 tests: 43 fast and 2 slow.

- **Frozen constants:**
  - the digests recompute;
  - the rule equals the review's declared rule;
  - both anchors record exactly the recognised mistake;
  - the list is exactly two studies and six decisions;
  - every frozen pin matches the file on disk;
  - the decisions equal the frozen grader readings;
  - the list cannot grow silently (`TOOL_CONSTANTS_ALTERED`);
  - the 0.3 history copy is byte-identical.
- **Trusted-mode refusals:**
  - both historical anchors are refused by name before any import, in process and through the command line;
  - all four historical readings are refused (the two originals and the two `aws_rescore_job/results/` copies);
  - a different wrong description is refused;
  - malformed, unknown-schema and incomplete anchors and readings are refused;
  - `--write-anchor` is create-only and never touches an original.
- **New runs:**
  - a new-run anchor built to look as much like a 0.2 anchor as possible (0.2 schema, the exact wrong rule, the 0.2 tool pin) is refused **with the flag**;
  - so is a new-run reading with the old description;
  - a clean hand-built 0.4 reading is `READING_VERIFIED`;
  - each defect in it is refused: a flipped decision, a historical mode, a wrong rule, an unclean verdict, a wrong receipt.
- **Historical acceptance:**
  - the six decisions are reproduced from the four committed readings (originals and AWS copies);
  - all checks PASS, exit 4, and the mode is recorded;
  - the warning and both descriptions appear, side by side;
  - the originals are byte-unchanged, checked independently by the test;
  - the one seed where the recorded decision differs (section 2);
  - the command line prints the warning and both column headers, and a plain run prints no warning;
  - safe-only verifies all 19 evidence items per study without importing the checker.
- **Historical refusals, in a sandbox copy (no original can be touched):**
  - altered predictions;
  - an altered scoring file;
  - the scoring forgery with a rewritten manifest (the one that fooled the frozen grader);
  - an altered frozen grader reading;
  - an altered checkpoint;
  - a missing scoring file, manifest, frozen grader reading or checker source;
  - an altered anchor or reading (it becomes unknown);
  - a deleted anchor;
  - overrides, substitute readings and `--no-frozen-reading`;
  - an `--out` that is an original (nothing is written).
- **The speed-up:** a number that overflows to infinity (`1e999`, no NaN token) is still caught.
- **Guard:** every fast test that must not run the checker replaces the checker loader with one that raises at
  once. A bug cannot turn a fast test into a 30-minute laptop run.
- **Slow (cloud):** the full 564-record historical rescore of both studies must give exit 4, all PASS, 564 re-checked
  per phase, 0 disagreements, the six decisions, and unchanged originals.

## 8. What I ran on the laptop, and the results

- Baseline before any change: 4 failed, 789 passed, 9 skipped (7.65 s).
  - All 4 failures had one cause. `records/typed_practice_001/evaluate_gates.py` (one of the 18 pinned checker files)
    was missing from the sparse checkout.
  - I added that one tracked file to this worktree's sparse checkout. Then: 793 passed, 9 skipped.
- `py_compile` on all four Python files: pass.
- Final fast run of all three files: **836 passed, 11 skipped, 54.92 s** (the 11 are the slow/AWS tests).
  - `test_historical_compatibility.py`: 43 fast.
  - `test_trusted_rescore.py`: 19 fast.
  - `test_historical_rescore_rule.py`: 774.
  - The longest single test took 3.94 s.
- Command-line smoke runs:

| Run | Exit | Result |
|---|---|---|
| historical `--check-reading`, helm1 | 4 | `HISTORICAL_COMPATIBILITY_OK`, `LEARNS_NEW_WORLDS` |
| historical `--check-reading`, helm2 | 4 | `HISTORICAL_COMPATIBILITY_OK`, `NO_TRANSFER_TO_NEW_WORLDS` |
| trusted `--check-reading`, helm1 AWS copy | 2 | `RULE_DESCRIPTION_MISMATCH`, `READING_SCHEMA_OUTDATED` |
| trusted rescore, helm1 anchor | 2 | same two reasons; the checker was not imported |
| historical `--safe-only`, helm2 anchor | 3 | `RESCORE_INCOMPLETE`; every file check PASS |

- The two historical checks each took about 2 s.

Claim status:

- **Ran here:** the fast tests and the smoke runs above.
- **Not run:** the full 564-record historical reading, the 11 slow tests, and a real `--write-anchor` (it loads the course).

## 9. What must run on AWS (coordinator)

1. Bundle `test_historical_compatibility.py` too. The old `launch.py` list does not name it.
   `records/typed_practice_001/evaluate_gates.py` must stay in the bundle.
2. **Do not reuse `job.sh.template` unchanged.** 0.4 will refuse two of its steps, on purpose:
   - it re-writes the anchors at their original paths (`--write-anchor` refuses original paths even after `rm -f`);
   - it writes readings over the original reading paths (`OUTPUT_WOULD_OVERWRITE_ORIGINAL`).
3. The full historical reading. Expect exit 4 and `HISTORICAL_COMPATIBILITY_OK`, about 14 min each (the earlier runs took 820 s and 830 s):
   ```
   python records/typed_pointer_001/trusted_rescore.py --historical-compatibility \
     --study records/typed_pointer_001/study_helm1_certified.json \
     --anchor records/typed_pointer_001/trust_anchor_helm1_certified.json \
     --out records/typed_pointer_001/historical_compat_reading_helm1_certified_0_4.json
   python records/typed_pointer_001/trusted_rescore.py --historical-compatibility \
     --study records/typed_pointer_001/admission_001/study.json \
     --anchor records/typed_pointer_001/trust_anchor_helm2_experimental_20208c92.json \
     --out records/typed_pointer_001/historical_compat_reading_helm2_experimental_0_4.json
   ```
4. The slow tests. The two new slow tests repeat step 3, so skip one or the other to save about 28 min:
   ```
   HELM_RUN_SLOW_TESTS=1 python -m pytest records/typed_pointer_001/test_trusted_rescore.py \
     records/typed_pointer_001/test_historical_compatibility.py -q -p no:cacheprovider -rs
   ```
5. Optional, and the owner's or coordinator's call: fresh **trusted** anchors for the two historical studies. Use new
   names (create-only), then a trusted rescore. Expect exit 0 and `RESCORE_OK`:
   ```
   python records/typed_pointer_001/trusted_rescore.py --study records/typed_pointer_001/study_helm1_certified.json \
     --anchor records/typed_pointer_001/trust_anchor_helm1_certified_v0_3.json --write-anchor
   python records/typed_pointer_001/trusted_rescore.py --study records/typed_pointer_001/study_helm1_certified.json \
     --anchor records/typed_pointer_001/trust_anchor_helm1_certified_v0_3.json \
     --frozen-reading records/typed_pointer_001/admission_helm1_certified/gate_reading.json \
     --out records/typed_pointer_001/trusted_rescore_reading_helm1_certified_0_4.json
   ```
   Do the same for helm2, with `admission_001/study.json` and `admission_001/gate_reading.json`.

## 10. Open questions

1. **Checkpoint weights.**
   - The `.pt` files are not in this checkout. I check that each recorded checkpoint digest is present and well-formed.
   - A present weight file must match. An absent one is reported, not refused.
   - If the owner means that weights must be byte-checked, change "absent" to "incomplete" and bundle the weights on AWS.
2. **Exit code 4** for `HISTORICAL_COMPATIBILITY_OK` instead of 0. Is that wanted?
3. **Fresh trusted anchors** for the historical studies (section 9, step 5). Should they be made?
4. **The study's nested pins** are not re-verified. These are the authority, owner and request files, whose absolute
   paths point into another worktree.
   - The study file itself is verified by its hash, so the recorded nested digests cannot change.
   - Re-checking the files is ambiguous: `admission_001/` held Helm 1.0 first and Helm 2.0 later.
5. **The 0.2 recorded decision for helm2 seed 20260917 (`false`)** differs from history (`true`). I did not check
   whether any other record quotes that per-seed value (BRAIN_LINEAGE, AUDIT_PACK, the ledger). It was outside my brief.
6. **The review file** (`RESCORER_REVIEW.json`) exists only on `research/helm-integration-20260923`. My tests
   hard-code its rule and its six rows and cite `0d8e8316`.
7. **CHANGELOG and spec sheet.** `CHANGELOG.md` and `docs/CAS_HARNESS_SPEC_SHEET.md` are outside this sparse checkout.
   They are not updated. The coordinator should decide.
8. **Independent review.** An independent review of 0.4 is needed, by Codex on return or another family.

## 11. Things I did beyond the literal brief

- **Sparse checkout.** I added one tracked file, `records/typed_practice_001/evaluate_gates.py`.
  - My first attempt went through Git Bash, which rewrote the leading `/` into `C:/Program Files/Git/...`. That wrote
    one wrong pattern, which matched nothing.
  - I restored the exact original list plus the one line, with path conversion off.
  - The final list is the original 13 lines plus that one line.
- **Speed-up**, so the fast suite fits in a minute. Same verdicts and reasons as before.
  - The JSON reader now flags numbers that overflow to infinity.
  - The per-record non-finite scan runs only when something was flagged.
  - The before/after hash covers the small records of both studies plus the large files of the study in use. The
    overwrite guard still covers every original.
- **Trusted `--check-reading`** accepts a clean 0.4 reading (`READING_VERIFIED`), so the default mode is not refusal-only.

## 12. EXPOSURE: every file outside the worktree that I opened or that reached me

- **Pre-loaded into my context by the tool that runs me.** I did not open these:
  - `C:\Users\wakil\.claude\CLAUDE.md`;
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\CLAUDE.md`;
  - the auto-memory index `C:\Users\wakil\.claude\projects\C--Users-wakil-OneDrive-Desktop-tksCAS\memory\MEMORY.md`.
    It names the sealed-test archive folder and some sealed-build facts (for example "HSET-1A reach W=2"). It holds
    no TEST world, record id or answer.
- **The shared git object store**, through git commands only:
  `C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/vision-next/.git`.
  Through it:
  - `git show 0d8e8316:.../rescorer_review/RESCORER_REVIEW.json` (read in full);
  - `git show` of `trusted_rescore.py` at `8b2bb942`, `2ef0921d` and `60e382b0` (hashed, and `8b2bb942` grepped for its pass rule);
  - `git log` of the historical records;
  - `git grep` for digest prefixes in `typed_pointer_001` `*.py`/`*.md`, `aws_rescore_job/`, and this handoff folder;
  - `git ls-tree --name-only` over up to 60 branch refs, filtered to anchor and reading **names**. The filter printed nothing.
- **This worktree's sparse-checkout file** in that store, `.../worktrees/helm-rescorer/info/sparse-checkout`. Changed as in section 11.
- **Not project files:** the Python install (`C:\Python314`, standard library and pytest).
- **My scratchpad:** `C:/Users/wakil/AppData/Local/Temp/claude/.../scratchpad`, which holds `check_helm2.json`.
- **Temporary test folders** under the system temp directory. They held copies of files from this worktree only, and were removed.
- **Not opened:** `D:/tksCAS-archive/`, any `*SEALED*`/`*sealed*` file, any `*_eval.jsonl`, any hset1a/hset1b path,
  S3/AWS, the meta1 ledger, other worktrees' files, and Claude transcripts.
  - None of the sealed, eval or hset1 paths is checked out here. I checked this by file name only, with `git ls-files`.
  - I started a recursive grep over this worktree's own files, then stopped it. It printed nothing.

---

## Revision 1 (2026-09-23): the review's BLOCKER 1, MAJOR 2 and MAJOR 3, plus MINOR 4 and MINOR 5

- Label: **CLAUDE_BUILT_CLAUDE_CHECKED** (temporary takeover while Codex is away).
- Builder: Claude, temporary builder. It answers the review `REVIEW_RESCORER_0_4_6e7f62a1.md` (commit `4c89e737`).
- Cost: $0. No AWS. No torch. No checker import. No course load. Small pure-Python checks only, one at a time.
- Custody: `EVALUATION_NOT_INDEPENDENT`. The same model family built 0.4, reviewed it, and built this revision.
  An independent (non-Claude) review is still owed.
- The tool is still version `0.4`. Its outputs now also carry `tool_revision: 1`.
- Sections 1 to 12 above describe 0.4 before this revision. Where they disagree with this section, this section wins.
  The main points they get wrong now: section 3 "a clean 0.4 trusted reading → `READING_VERIFIED` (exit 0)";
  section 3 "an absent [checkpoint] is reported as `RECORDED_DIGESTS_ONLY`, not refused"; section 9 (replaced by R1.7).

### R1.1 What changed, finding by finding

| Finding | What the tool does now |
|---|---|
| **BLOCKER 1**: trusted `--check-reading` gave exit 0 to hand-edited counts | A trusted `--check-reading` is **never** trusted acceptance. Its best verdict is `READING_CONSISTENT_NOT_RESCORED`, exit **5**, label `NOT_DERIVED`. The record says `trusted_acceptance: false` and `rescored: false`. Only a full rescore (`RESCORE_OK`, exit 0) is trusted acceptance. `READING_VERIFIED` is gone. |
| | The recorded counts must be possible, in both modes: `p_one_sided` present (0.4 readings); kinds distinct and taken from the anchor's `kind_of`; world ids distinct, taken from its `world_of`, and as many as `worlds_improved`; `gained + broken` at most the population (18); no more kinds or worlds than gains; `frozen_18_after = frozen_18_before + gained - broken`; every phase re-checked in full (564) with 0 disagreements. |
| | A clean trusted reading must record exactly this tool's checks: every one `PASS`, except `HISTORICAL_EVIDENCE` and `HISTORICAL_DECISIONS` (`NOT_REQUESTED` in trusted mode). It must record that the tool itself loaded and ran the checker. So a reading made with `--no-frozen-reading` is `READING_NOT_CLEAN` here. |
| | The reading must pin the frozen grader reading it was compared with (new field `frozen_reading_pin`). The check verifies that pin, then compares counts, p, decision, kinds, worlds and label with it (`FROZEN_GRADER_DISAGREES`). |
| | **The limit, stated plainly.** A forger who writes the reading AND a matching frozen grader reading gets exit 5. Never 0. The test `test_forged_counts_for_a_run_that_truly_fails_never_exit_0` shows this on purpose. |
| **MAJOR 2**: absent checkpoint weights passed in both modes | Coordinator decision (1) is in the code. An absent or unverifiable weight file is **incomplete evidence**, refused by name: `HISTORICAL_EVIDENCE_INCOMPLETE` in historical mode, `RUN_EVIDENCE_INCOMPLETE` in trusted mode. Never `PASS`, never exit 4, never exit 0. "Unverifiable" means no well-formed recorded digest, or a name that is not a plain file name. |
| | A seed with some weights present and some absent is `INCOMPLETE`, never `MATCH`. `RECORDED_DIGESTS_ONLY` is gone. |
| | New anchors use schema `cncm.trusted-rescore-anchor/0.4`. Each seed pins `run_evidence`: the run manifest (path and sha256) and every checkpoint digest it records (name, sha256, bytes). A `0.3` anchor is now `ANCHOR_SCHEMA_OUTDATED` ("pins no run manifest and no checkpoint digest"). No 0.3 anchor exists in this repository. |
| | New safe check `RUN_EVIDENCE` (trusted mode, part of the gate): the manifest must be the one the anchor pinned (`RUN_EVIDENCE_ALTERED` otherwise), it must agree with the anchor's prediction pins, and every weight file it records must be present and byte-identical. In historical mode it is `NOT_REQUESTED`, because `HISTORICAL_EVIDENCE` already covers the frozen manifests and their weights. |
| | `--write-anchor` byte-checks every weight file **before** it loads anything, and refuses (`ANCHOR_REFUSED`) if one is absent or altered. So a fresh anchor pins only weights that were checked. |
| | `HISTORICAL_EVIDENCE`'s detail now says how many files were byte-checked, not only how many items were listed. Example: "19 evidence items; 31 files byte-checked, including 15 of 15 recorded checkpoint weight files". |
| **MAJOR 3**: `--out` could overwrite unlisted originals | `--out` is **create-only**. It is checked **before any work**: an existing path is `OUTPUT_EXISTS`; an original on the historical list (even a deleted one) or a file named on the same command line is `OUTPUT_WOULD_OVERWRITE_ORIGINAL`. Nothing is read, nothing is written, exit 2. The file is opened with mode `"x"`, which also stops a hard link and a file that appears during the run (then exit 2, nothing written). |
| **MINOR 4**: thresholds outside the hashed rule | `historical_decision` reads every threshold from `HISTORICAL_RULE` (alpha, b > c, the veto flag, kinds, worlds). The label comes from `historical_label`, which honours `all_seeds_must_pass`. The module constants `MIN_IMPROVED_KINDS` / `MIN_IMPROVED_WORLDS` are removed, so there is no second copy. The whole `RECOGNISED_MISTAKE` is hashed: `RECOGNISED_MISTAKE_SHA256` = `fddc692ee219b0d6efe18675aa169bca693edd4e2b69918bd7ad818778c27a40`. |
| **MINOR 5**: overloaded exit codes; crashes | Usage errors exit **64** (including `--receipt` without `=`, which crashed before). A reading or anchor field of the wrong JSON type is `READING_MALFORMED` / `ANCHOR_MALFORMED` by name, never a traceback. A safety net turns any other unexpected structure in a reading into `READING_MALFORMED`. `--write-anchor` still exits 0 when it writes an anchor (see R1.8, item 2). |
| **NOTE 6** | Stated in R1.7, step 4. |
| **NOTE 7** | Partly: `--check-reading` now requires the frozen grader comparison. A trusted **rescore** with `--no-frozen-reading` can still give `RESCORE_OK`. Open for the coordinator (R1.8, item 1). |
| **NOTE 8** | Decisions (4) and (5) are restated as open items for Codex (R1.8, items 3 and 4). |
| **NOTE 9** | Decision (3), fresh anchors, can now go ahead on AWS after a re-review, with the weights bundled (R1.7, step 6). |

One more change, found while building: `_rel` returned a relative path unchanged when it was outside the package, and
later readers took it as package-relative. It now returns the resolved absolute path.

### R1.2 Exit codes now

| Exit | Meaning |
|---|---|
| 0 | `RESCORE_OK`: trusted mode, full rescore. The **only** trusted acceptance. (Also: `--write-anchor` wrote the anchor.) |
| 2 | `REJECT`: at least one named reason. Also every `--out` refusal and `ANCHOR_REFUSED`. |
| 3 | `RESCORE_INCOMPLETE` / `CHECK_INCOMPLETE`: nothing failed, but a check that should run did not. |
| 4 | `HISTORICAL_COMPATIBILITY_OK`: historical mode only, all evidence present and verified, weights included. |
| 5 | `READING_CONSISTENT_NOT_RESCORED`: trusted `--check-reading` only. Consistent counts, not a rescore. |
| 64 | Usage error. |

### R1.3 Files (all LF and ASCII, so raw sha256 = sha256_lf)

| File | sha256 | Change |
|---|---|---|
| `records/typed_pointer_001/trusted_rescore.py` | `c3d6bdd08f9f9f613fb77e1d590b557fd0e28df2d78b26f6ffd5b91661d5cdb1` | 0.4 → 0.4 revision 1 (was `2f10feac...`) |
| `records/typed_pointer_001/test_historical_compatibility.py` | `d5eb5c22ea1fbd06630b4ecb7bceb49555574ae365475d37f4fe9605be6e5a1d` | rewritten for revision 1 (was `e9027873...`) |
| `records/typed_pointer_001/test_trusted_rescore.py` | `edefa58bead6a47cb47510dd3014d113f3af67c2cb9c910f4c3302633a52ec56` | sandbox and new tests (was `154706e8...`) |
| `records/typed_pointer_001/test_historical_rescore_rule.py` | `58d95cf01d3eb01da18db7fefa6d087cc3ce82a2e9c621110cd8da8464d6458e` | unchanged, still passes |
| `records/typed_pointer_001/history/trusted_rescore_0_3.py` | `50295072dd662fac1bf51021e8abd8395621ebafc8d35e8f8e4949120e35f8cc` | unchanged |

Not changed: every anchor, reading, receipt, run manifest, frozen grader reading, `evaluate_gates.py`, every checker
and slot file, `aws_rescore_job/`, and `BRAIN_LINEAGE.md`.

### R1.4 How the tests changed

**The weights are not in this checkout.** All 30 historical checkpoint weight files are absent here (98,903,652 bytes
in total). So under decision (1) the historical mode must refuse them on this laptop. The tests now say so:

- **Without the weights (this checkout).** Each of the four committed historical readings (the originals and the AWS
  copies) gives exit **2**, 15 reasons, each one `HISTORICAL_EVIDENCE_INCOMPLETE` naming one weight file. The replay
  still runs, and all six decisions still agree with the frozen grader and the frozen list. Before this revision the
  same run gave exit 4. These tests skip themselves when the weights are present (on AWS).
- **With every weight file (SIMULATED here).** A sandbox copy of each study gets a placeholder file for every weight,
  and the test swaps the tool's file-hash function for a stand-in. The stand-in reports the recorded digest for
  exactly those placeholder bytes at exactly those paths, and hashes everything else for real. This reaches the
  acceptance path: exit 4, every check PASS, 15 of 15 weights `MATCH`, the six decisions, the warning, and both
  descriptions. **This is simulated. It proves the acceptance logic, not the real weights.**
- **With the real weights (AWS only).** New `test_with_the_real_weights_the_historical_check_reading_gives_exit_4`
  (4 cases, seconds each, no course load) and the existing full-rescore test. Both **fail** (they do not skip) if a
  weight file is missing, so an unbundled job cannot look like a pass.
- **Trusted-mode sandbox.** It is a new run, so it now has its own run manifest and two small placeholder weight files
  whose true digests that manifest records. The tool byte-checks them for real (no stand-in).

Tests that assumed the old behaviour, and what happened to each (the review named them):

| Test | Now |
|---|---|
| `test_historical_compatibility.py:378` (six decisions, exit 4) | Split: without the weights (exit 2, named) and with simulated weights (exit 4). Real weights: AWS test. |
| `test_historical_compatibility.py:435` (accepted `RECORDED_DIGESTS_ONLY`) | Uses simulated weights; every item must be `MATCH`, 15 byte-checked. |
| `test_historical_compatibility.py:441` (sandbox accepted) | Now asserts both: refused for the weights only, then accepted with simulated weights. |
| `test_trusted_rescore.py` committed-anchors test | Expects exactly the 15 named weight refusals here; expects none on AWS. It also fails on a partial bundle. |
| slow `test_clean_copy_through_the_command_line...` | Its sandbox now has byte-checked placeholder weights; it also asserts `RUN_EVIDENCE = PASS`. |
| slow `test_altered_scores_...rewritten_manifest` | The rewritten manifest is now refused at the gate, `RUN_EVIDENCE_ALTERED`, before any import. |
| `check()` / `safe()` / `run()` helpers | A new output name every call (create-only). |

New fast tests, one or more per failure scenario in the review:

- BLOCKER 1: the reviewer's own scenario (Helm 2.0 seed `20260919`'s four label files as a new run; truth 7/1, p =
  9/256, FAIL). The honest reading gives exit 5. The hand-written 12/0 reading gives exit 2, `FROZEN_GRADER_DISAGREES`.
  With a forged frozen grader reading as well, exit 5, never 0. Plus 21 defect cases, each refused by exactly one
  expected code. I also ran them one by one in a scratch script and printed the codes:

| Defect | Exit | Codes |
|---|---|---|
| 99 gains in an 18-question population | 2 | `READING_INCONSISTENT` |
| one kind counted twice (`reach`, `reach`) | 2 | `READING_INCONSISTENT` |
| no `p_one_sided` | 2 | `READING_INCOMPLETE` |
| a kind outside the population | 2 | `READING_INCONSISTENT` |
| more worlds than gains | 2 | `READING_INCONSISTENT` |
| before and after do not add up | 2 | `READING_INCONSISTENT` |
| a phase not fully re-checked (500 of 564) | 2 | `READING_INCONSISTENT` |
| a wrong p | 2 | `READING_DECISION_MISMATCH` |
| a flipped decision | 2 | `READING_DECISION_MISMATCH` |
| a receipt that is not the anchor's | 2 | `READING_INCONSISTENT` |
| no checks at all (`{}`) | 2 | `READING_NOT_CLEAN` |
| a check `NOT_RUN` | 2 | `READING_NOT_CLEAN` |
| no frozen grader comparison | 2 | `READING_NOT_CLEAN` |
| no `RUN_EVIDENCE` check | 2 | `READING_NOT_CLEAN` |
| the checker never ran | 2 | `READING_NOT_CLEAN` |
| an unclean verdict | 2 | `READING_NOT_CLEAN` |
| a historical mode | 2 | `READING_NOT_TRUSTED` |
| a wrong rule | 2 | `RULE_DESCRIPTION_MISMATCH` |
| written before revision 1 (no `tool_revision`) | 2 | `READING_INCOMPLETE` |
| no pinned frozen grader reading | 2 | `READING_INCOMPLETE` |
| `anchor.path` is a JSON object | 2 | `READING_MALFORMED` |

- Also for BLOCKER 1: the frozen grader reading changed after the pin (`READING_EVIDENCE_ALTERED`); a weight file gone
  after the reading (`RUN_EVIDENCE_INCOMPLETE`); the command line gives exit 5 and prints "NOT A RESCORE".
- MAJOR 2: absent, altered and rewritten-manifest cases in trusted mode (refused before any import); an anchor without
  run evidence (`ANCHOR_INCOMPLETE`); a 0.3 anchor (`ANCHOR_SCHEMA_OUTDATED`); `--write-anchor` refuses absent or
  altered weights before loading anything, for a sandbox run and for the real Helm 1.0 study; a partly present seed is
  `INCOMPLETE`, not `MATCH`; unit tests of the weight check (unverifiable digest, not a plain name, none recorded).
- MAJOR 3: every path the review listed (the AWS copy of the reading, the study, `evaluate_gates.py`, a checker source,
  a copy of the tool) and a plain existing file, in both modes, for `--check-reading` and for a rescore. Each is refused
  before any work: the test replaces `snapshot`, `_safe_checks` and `_check_reading_body` with functions that fail if
  called. The bytes are unchanged. Also a deleted original, a hard link, a file that appears during the run, and the
  command line.
- MINOR 4: a changed threshold changes the decision **and** shows as `TOOL_CONSTANTS_ALTERED`; an edited
  `written_by_tool_sha256_lf` shows too. MINOR 5: usage errors exit 64; a malformed field is refused, not a crash.

### R1.5 What I ran on the laptop, and the results

Free memory at the start: 745 MB of 16,085 MB. Every run: `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`, one at a time.

| Run | Result | Time |
|---|---|---|
| baseline, `test_historical_compatibility.py` before any change | 43 passed, 2 skipped | 28.70 s |
| `test_trusted_rescore.py` | **27 passed, 9 skipped** (slow) | 6.52 s |
| `test_historical_compatibility.py` | **60 passed, 6 skipped** (AWS) | 23.61 s |
| `test_historical_rescore_rule.py` | **774 passed** | 0.55 s |
| **Total** | **861 passed, 15 skipped, 0 failed** | |

Command-line smoke runs (no `--out`, so nothing was written):

| Run | Exit | Result |
|---|---|---|
| historical `--check-reading`, helm1 | 2 | `REJECT`; 15 × `HISTORICAL_EVIDENCE_INCOMPLETE` (the weights) |
| historical `--check-reading`, helm2 | 2 | the same; the three decisions still replayed and agree |
| trusted `--check-reading`, helm1 AWS copy | 2 | `RULE_DESCRIPTION_MISMATCH`, `READING_SCHEMA_OUTDATED` |
| trusted rescore, helm1 anchor | 2 | `RULE_DESCRIPTION_MISMATCH`, `ANCHOR_SCHEMA_OUTDATED`; checker not imported |
| historical `--safe-only`, helm2 anchor | 2 | 15 × `HISTORICAL_EVIDENCE_INCOMPLETE`; every other file check `PASS`; `RUN_EVIDENCE = NOT_REQUESTED` |
| historical `--check-reading --out <existing file>` | 2 | `OUTPUT_EXISTS`; the file's sha256 unchanged (`a8f875c5...` before and after) |
| `--check-reading x --study y` | 64 | `USAGE_ERROR` |
| `--receipt nosign` | 64 | `USAGE_ERROR` (was a crash) |

Claim status:

- **Ran here:** the fast tests and smoke runs above; my scratch probe of the 21 defect cases.
- **Simulated here:** "every weight file present and matching", in the historical acceptance tests (see R1.4).
- **Not run:** the full 564-record historical readings, the 15 slow/AWS tests, a real `--write-anchor` (it loads the
  course), and any check of the real weight files. All need AWS with the weights bundled.

### R1.6 Anchor and reading format changes

- Anchor schema `0.4` adds `tool_revision` and, per seed, `run_evidence`:
  `{"manifest": {"path", "pin"}, "checkpoints": {"<name>.pt": {"sha256", "bytes"}}}`.
- Reading schema stays `cncm.trusted-rescore-reading/0.4`. It adds `tool_revision`, `run_evidence` and
  `comparison_with_frozen_grader.frozen_reading_pin`. A 0.4 reading without `tool_revision` (made before this
  revision) is `READING_INCOMPLETE`. None was ever committed.
- Check record schema `cncm.trusted-rescore-reading-check/0.2` adds `trusted_acceptance` (always false), `rescored`
  (always false), `label_replayed_from_recorded_counts`, `frozen_grader` and `reading.written_by_this_tool_file`.

### R1.7 What must run on AWS (replaces section 9)

Do these only **after a re-review of this revision**.

1. **Bundle** the tool, the three test files, `evaluate_gates.py`, `records/typed_practice_001/evaluate_gates.py`, and
   **the 30 real checkpoint weight files** (98,903,652 bytes). Each goes at
   `records/typed_pointer_001/<receipt>/collected/results/artifacts/<name>`, where `<name>` is `final.pt`, `initial.pt`,
   `pass_01.pt`, `prelast.pt` and `retained.pt`, and `<receipt>` is each of `receipt_helm1_certified_20260917`,
   `_20260918`, `_20260919`, `receipt_20260917`, `receipt_20260918`, `receipt_20260919`.
   - I do not know where the weights are kept. I did not look: S3 and the archive are off-limits to me.
   - The old `aws_rescore_job/launch.py` bundle list names neither the new test file nor the weights. I did not
     change it.
   - The tool byte-checks every weight file against the frozen manifests. A wrong or missing file is refused by name.
2. **Do not reuse `job.sh.template` unchanged.** It writes over original paths; 0.4 refuses that on purpose.
3. **The quick historical check** (seconds each, no course load). Expect exit 4:
   `python records/typed_pointer_001/trusted_rescore.py --historical-compatibility --check-reading records/typed_pointer_001/trusted_rescore_reading_helm1_certified.json --out records/typed_pointer_001/historical_check_helm1_certified_r1.json`
   and the same for `trusted_rescore_reading_helm2_experimental.json` with its own new `--out` name.
4. **The full historical readings** (about 14 min each). Expect exit 4. Every `--out` must be a NEW path:
   ```
   python records/typed_pointer_001/trusted_rescore.py --historical-compatibility \
     --study records/typed_pointer_001/study_helm1_certified.json \
     --anchor records/typed_pointer_001/trust_anchor_helm1_certified.json \
     --out records/typed_pointer_001/historical_compat_reading_helm1_certified_0_4r1.json
   python records/typed_pointer_001/trusted_rescore.py --historical-compatibility \
     --study records/typed_pointer_001/admission_001/study.json \
     --anchor records/typed_pointer_001/trust_anchor_helm2_experimental_20208c92.json \
     --out records/typed_pointer_001/historical_compat_reading_helm2_experimental_0_4r1.json
   ```
   Review NOTE 6: `--check-reading` will refuse these two new files in both modes (`HISTORICAL_EXCEPTION_UNKNOWN_READING`
   in historical mode, `RULE_DESCRIPTION_MISMATCH` in trusted mode). That is by design: the frozen list pins only the
   original 0.2 readings. The only way to verify them again is to run step 4 again.
5. **The slow tests.** The historical full-rescore test repeats step 4; skip one or the other to save about 28 min:
   ```
   HELM_RUN_SLOW_TESTS=1 python -m pytest records/typed_pointer_001/test_trusted_rescore.py \
     records/typed_pointer_001/test_historical_compatibility.py records/typed_pointer_001/test_historical_rescore_rule.py \
     -q -p no:cacheprovider -rs
   ```
   With the weights bundled, the "without the weights" tests skip themselves and the AWS tests run.
6. **Decision (3), fresh trusted anchors**, if the owner or coordinator wants them. Schema 0.4 now pins the weights,
   so these anchors will not be out of date on arrival. Use new names (create-only):
   ```
   python records/typed_pointer_001/trusted_rescore.py --study records/typed_pointer_001/study_helm1_certified.json \
     --anchor records/typed_pointer_001/trust_anchor_helm1_certified_v0_4.json --write-anchor
   python records/typed_pointer_001/trusted_rescore.py --study records/typed_pointer_001/study_helm1_certified.json \
     --anchor records/typed_pointer_001/trust_anchor_helm1_certified_v0_4.json \
     --frozen-reading records/typed_pointer_001/admission_helm1_certified/gate_reading.json \
     --out records/typed_pointer_001/trusted_rescore_reading_helm1_certified_0_4r1.json
   ```
   Expect exit 0 and `RESCORE_OK`. Do the same for helm2 with `admission_001/study.json` and
   `admission_001/gate_reading.json`. A later `--check-reading` of such a reading gives exit **5**, not 0, by design.

### R1.8 Open items

1. **NOTE 7, coordinator's call.** A trusted rescore with `--no-frozen-reading` can still give `RESCORE_OK` (exit 0).
   Should that count as incomplete evidence? `--check-reading` already requires the comparison.
2. **`--write-anchor` exits 0** when it writes an anchor. It is a different command from a rescore, and 0 keeps
   `&&` chains working. The review (MINOR 5) suggested a code of its own. Coordinator's call.
3. **For Codex, decision (4):** the study's nested pins (authority, owner and request files) are still not re-verified.
4. **For Codex, decision (5):** `BRAIN_LINEAGE.md` still states the wrong seed-`20260917` decision at lines 300 and
   302-304 (the review's line numbers at `4c89e737`). Lines 17-27 already hold a dated correction that takes precedence.
5. **The weight files.** Where they are kept, and who bundles them (R1.7, step 1).
6. **CHANGELOG and spec sheet.** Still outside this sparse checkout; not updated.
7. **Independent review.** Still owed, by Codex on return or another model family.

### R1.9 EXPOSURE: every file outside this working copy that I opened, for this revision

- **Pre-loaded into my context by the tool that runs me. I did not open these:**
  `C:\Users\wakil\.claude\CLAUDE.md`; `C:\Users\wakil\OneDrive\Desktop\tksCAS\CLAUDE.md`; the auto-memory index
  `C:\Users\wakil\.claude\projects\C--Users-wakil-OneDrive-Desktop-tksCAS\memory\MEMORY.md`. It names the sealed-test
  archive folder and some sealed-build facts (for example "HSET-1A reach W=2"). It holds no TEST world, record id or answer.
- **Not project files:** the Python install and pytest; PowerShell's memory query (`Win32_OperatingSystem`).
- **My scratchpad** (`C:/Users/wakil/AppData/Local/Temp/claude/C--Users-wakil-OneDrive-Desktop-tksCAS-cas-only-reasoner/5e8709f4-3151-444f-939b-317c01bc3568/scratchpad`):
  `probe_defects.py`, and `r1_h2.json` (a check record; deleted).
- **Git Bash's `/tmp`:** `o1.txt`, the smoke runs' console text. Deleted.
- **Temporary test folders** under the system temp directory, made by the tests and my probe. They held copies of
  files from this worktree only, and were removed.
- **The shared git object store, through git commands only** (`git status`, `git diff`, `git log`, `git ls-files`,
  `git rev-parse`, then `git add`, `git commit` and `git push` for this commit):
  `C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/vision-next/.git`.
  No `git show` of any other branch or file. `git push` talks to GitHub, not AWS.
- **Not opened:** `D:/tksCAS-archive/`, any `*SEALED*`/`*sealed*` file, any `*_eval.jsonl`, any hset1a/hset1b path,
  S3/AWS, the meta1 ledger, other worktrees' files, and Claude transcripts.
