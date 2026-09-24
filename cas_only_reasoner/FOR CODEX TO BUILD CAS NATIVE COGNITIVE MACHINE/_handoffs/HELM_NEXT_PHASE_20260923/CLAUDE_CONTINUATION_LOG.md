# Claude continuation log (temporary takeover while Codex is unavailable)

Kept by the Claude coordinator. **For Codex on return:** review the bounded change set listed here. Do not repeat
completed acceptance, and do not merge automatically.

## Sources and commits

| What | Commit | Branch |
|---|---|---|
| Codex's newest source at takeover (parent) | `96644503` (full: `966445034a...`) | `codex/helm-stage2-checker-20260923` (unchanged) |
| Analogy repair | `60e382b042d54eab68394393b1d8fe4540a1ac06` | contained in the parent |
| Checker v2, ACCEPTED | `7f85af1eb9eb0ed991d5a8c82fa7ec4db43e539d` | contained in the parent |
| Original Helm 2.0 source | `20208c923d41c24614504d4ecc2b289ecb66eda8` | — |
| Claude's evaluation and custody records | `c995e09d` | `research/helm-integration-20260923` |
| This takeover's work | see Commits below | `claude/helm-builder-continuation-20260923` |

## Pointer: D-1 is ACCEPTED

Older notes say checker-v2 acceptance is "pending", "open" or "remains open". They are history, not current
status. Among them:
- `CODEX_D1_STATUS.md`;
- `CODEX_PEER_EVIDENCE_STATUS.md`;
- `records/helm_peer_handoff_20260923/README.md` ("Five- and six-node v2 acceptance remains open").

The current record is `research/helm-integration-20260923` at
`records/helm_eval_design_20260923/d1_acceptance/D1_ACCEPTANCE_RESULT.md`: **ACCEPTED**, A1-A6 plus X, for source
`7f85af1e`, from the complete run on `i-0681fa3905a7bb0eb`. It is a checker result, not a learned-model result.

## Task status

| # | Task | Status |
|---|---|---|
| A | Preserve accepted D-1; reconcile outstanding items | D-1 is preserved, and the pointer is above. Claude's review of Codex's rescorer is not yet recorded (see Open review items) |
| B | Read-only comparison setting | **Built** at `ceab6c49` (builder), two fresh reviews `APPROVE_FOR_T4_RUN`. Its tests passed on the T4 (38 passed, attempt 1 stage 0) |
| C | Historical OFF control and ON-effect checks on a T4 | Attempt 1 **INCOMPLETE** (the probes lacked their preregistration file). Preservation measured: control==reference 9/9, OFF==control 9/9. Attempt 2 running (`i-030e5665bcad36f69`). ON training (owner-approved, $60) waits on attempt 2's program verdict and on a fresh review of the ON prep `2cd6aed9` |
| D | Public evaluation design; larger-question path through the actual learner | HSET-1A built: no 5-node reach cell can carry a claim. The owner chose 6- and 7-node cells (HSET-1B): builder, spec and AWS job committed (`b5a4d525`, `5773b7ad`), not launched; it runs after the T4 job. The learner-path subclass is not started |
| E | Q4-SDG-1 (owner directive `8eb798a5`) | Separate line, own working copy `D:/tksCAS-worktrees/q4-sdg`, branch `claude/q4-sdg-feedback-20260923`, ownership record `0687e20a`. Builder sub-agent working (lesson adapter, error-panel module). Diagnostic job ($1.00 ceiling) after review. A-versus-B training needs an owner dollar ceiling |

## Commits made during the takeover

| Commit | Branch | Who | What |
|---|---|---|---|
| `d27e2ec2`, `a19eb735` | builder branch | coordinator | takeover instruction copy, coordination amendment, this log (and removal of stray text) |
| `37af9b8f`, `6a607f06` | `research/helm-integration-20260923` | coordinator | prereg amendment A4 (verdict names, read-only check, fresh-ON label), frozen before any repaired-source result; the T4 job files (not launched) |
| `0d8e8316` | `research/helm-integration-20260923` | coordinator | review of Codex's rescorer: program-emitted `RULE_REPAIR_REPRODUCES_HISTORY` |
| `098a3bdcc81ef3d31cb02f01299506d342cb2b6e` | builder branch | builder | read-only switch: `pointer_learner.py` (+30/-2, LF-only inserted lines; raw `a94084f7...`) and new `tests/test_helm_analogy_switch_read_only.py` (10 functions, 25 cases) |
| `08b305ec` | builder branch | builder | `BUILDER_REPORT_READ_ONLY_SWITCH.md` |
| `ceab6c49f611303f39addfaa3553d81d6f902811` | builder branch | builder | Revision 1: guards read a closure tuple, not `self._READ_ONLY_SWITCH`. `pointer_learner.py` raw `0f424d86...`, LF `2ebb1b08...`. New test `test_planted_attributes_cannot_disable_the_guards` (11 functions, 27 cases) |
| `8a150198` | `research/helm-integration-20260923` | coordinator | the owner's decisions, verbatim (keep the g6e; train switch ON; 6- and 7-node reach; fail-closed rescorer anchors) |
| `b5a4d525` | `research/helm-integration-20260923` | coordinator | the HSET-1B builder, spec (salt sha `b3cf84e2...` committed before the build) and AWS job. Not launched |
| `8aba0c62` | `research/helm-integration-20260923` | coordinator | launch record of the T4 item-1 job, R = `ceab6c49` |
| `5773b7ad` | `research/helm-integration-20260923` | coordinator | HSET-1B pre-launch review fixes: the launcher refuses a salt whose sha256 differs from the committed one (MAJOR); success rule pinned |
| `8eb798a5`, `e1728a59` | `research/helm-integration-20260923` | coordinator | the owner's Q4 directive (byte copy) and pasted rationale |
| `d6c9faa9` | `research/helm-integration-20260923` | coordinator | owner approves up to $60 for switch-ON training (verbatim question and answer) |
| `d7023288` | `research/helm-integration-20260923` | coordinator | prereg amendment A5 (reading rules for trained ON checkpoints), frozen before any ON training |
| `2cd6aed9` | builder branch | builder | ON-training prep: the ablation "heads" row owns `analogy_head`; ON admission writer. Fresh review pending |
| `0687e20a` | `claude/q4-sdg-feedback-20260923` | coordinator | Q4-SDG-1 temporary ownership record, before any Q4 code |
| `5e1d1373`, `e5106ad8` | `research/helm-integration-20260923` | coordinator | T4 attempt 1 filed (INCOMPLETE) + launcher fix; attempt 2 launched |

## Checks run, and results

Written test functions, input-specific cases and repeated runs are counted separately.

- **Builder, static only** (no torch on the laptop):
  - byte comparison: only the intended region changed, and the CRLF count is unchanged at 2,241;
  - `py_compile`;
  - a bytecode check that `__init__` still branches on the function argument.
  - **No test has run yet.** 10 new test functions (25 cases, 1 of them CUDA-only) and the existing 11 cases wait
    for the T4 job.
- **Fresh reviewer (a separate Claude sub-agent), static only.**
  - First review of `098a3bdc`: no blocker and no major; one MINOR (the guard could be disabled through an instance
    attribute); `APPROVE_FOR_T4_RUN`.
  - Delta review of `ceab6c49`: MINOR closed, nothing new, `APPROVE_FOR_T4_RUN`.
  - It reproduced the byte and sha256 figures independently.
  - It recorded one pre-existing defect, not fixed because fixing it would break the match with `20208c92`: at
    `pointer_learner.py:811`, `torch.nn.init.zeros_(self.declaration_table[padding, :])` zeroes a copy.
- **Rescorer review (coordinator, read-only, $0).** `RULE_REPAIR_REPRODUCES_HISTORY`: 6 of 6 decisions agree, and
  the rule is declared with no zero-loss veto. The full 564-record reading and the slow tests are NOT_RUN.
- **T4 launcher dry run against `098a3bdc`.**
  - The bundle is 2,326 files and 29.77 MB.
  - The only existing file that differs from `20208c92` is `pointer_learner.py`.
  - The pinned reference image is still offered.
  - The worst case is $2.05.
  - Nothing was uploaded or launched.

## Resource use

- 2026-09-23, T4 item-1 job, ceiling $3.00 for both attempts together:
  - attempt 1: `i-0b2a1761317398ba4`, g4dn.2xlarge, pinned image `ami-07d69ce07bfe5628f`; 43.7 minutes; upper bound
    $0.5596; terminated, no volume left. Outcome INCOMPLETE (the 4 probes crashed on a missing file; see
    `analogy_repair_t4_job/RUN_LOG.md`);
  - attempt 2: `i-030e5665bcad36f69`, same machine type and image; worst case $2.05. Running.

- 2026-09-23: read-only AWS inventory; $0.
  - No Helm instance, volume or SageMaker job is live.
  - One unrelated stopped `g6e.xlarge` `i-0c3028734c8885542` with a 300 GB volume, left untouched.

## Exposure to final tests

- **The coordinator** built and holds the sealed TEST_NEW_5, and has seen its totals only.
- **The builder and the reviewer** receive public contracts only. They are instructed not to open
  `D:/tksCAS-archive/`, any `*SEALED*` file, the S3 `helm-integration/hset1a-build-*` objects, or the coordinator's
  session logs. That is by instruction, not by permission. Their reports must list every file outside their
  working copy that they opened.
- **Exposure the builder disclosed** (not in its brief): the tool that runs sub-agents pre-loads the owner's global
  `CLAUDE.md`, the project `CLAUDE.md` and **the auto-memory index**. That index names the sealed-test archive folder
  and states sealed-build totals, such as "W=2 on TEST". It holds no TEST world, record id or answer.
- **Other files the builder opened.** torch's installed source, read and never imported, and a `git grep` of
  committed files. Nothing sealed.

## Open review items for Codex

- The read-only change (task B), once committed: its diff and test file.
- Rescorer:
  - Codex's `trusted_rescore.py` 0.3 (LF `50295072...`) reproduces the six historical decisions in its targeted
    recheck.
  - Its full 564-record reading and its 9 slow tests are **NOT_RUN** (the laptop timed out).
  - The anchor policy: the owner chose "whichever makes for a better model"; applied as **fail-closed** (refuse any
    anchor whose recorded rule is wrong; write new 0.3 anchors; keep the 0.2 ones as history). Builder task, not
    started.
- `preflight_dry_run.py` lists 48 container names, but the default container has 53 since `60e382b0`. This drift
  is recorded, not fixed.
