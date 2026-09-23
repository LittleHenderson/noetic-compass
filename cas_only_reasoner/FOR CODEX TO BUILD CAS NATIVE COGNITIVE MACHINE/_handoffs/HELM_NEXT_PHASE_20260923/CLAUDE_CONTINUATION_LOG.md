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
| B | Read-only comparison setting | **OPEN at `96644503`.** `pointer_learner.py:731-732` are plain changeable attributes (blob `caaff9dc`, unchanged since `60e382b0`). Assigned to the temporary builder |
| C | Historical OFF control and ON-effect checks on a T4 | Not run. The specification is recovered (A3 rule, 9 models). It waits on B and on prereg amendment A4 |
| D | Public evaluation design; larger-question path through the actual learner | Not started. The learner imports only the original `slots`, so 5- and 6-node correspondence is refused at the slot compiler. The proposal is a separate opt-in, inference-only subclass. The Stage 1 cut awaits the owner |

## Commits made during the takeover

| Commit | Branch | Who | What |
|---|---|---|---|
| `d27e2ec2`, `a19eb735` | builder branch | coordinator | takeover instruction copy, coordination amendment, this log (and removal of stray text) |
| `37af9b8f`, `6a607f06` | `research/helm-integration-20260923` | coordinator | prereg amendment A4 (verdict names, read-only check, fresh-ON label), frozen before any repaired-source result; the T4 job files (not launched) |
| `0d8e8316` | `research/helm-integration-20260923` | coordinator | review of Codex's rescorer: program-emitted `RULE_REPAIR_REPRODUCES_HISTORY` |
| `098a3bdcc81ef3d31cb02f01299506d342cb2b6e` | builder branch | builder | read-only switch: `pointer_learner.py` (+30/-2, LF-only inserted lines; raw `a94084f7...`) and new `tests/test_helm_analogy_switch_read_only.py` (10 functions, 25 cases) |
| `08b305ec` | builder branch | builder | `BUILDER_REPORT_READ_ONLY_SWITCH.md` |

## Checks run, and results

Written test functions, input-specific cases and repeated runs are counted separately.

- **Builder, static only** (no torch on the laptop):
  - byte comparison: only the intended region changed, and the CRLF count is unchanged at 2,241;
  - `py_compile`;
  - a bytecode check that `__init__` still branches on the function argument.
  - **No test has run yet.** 10 new test functions (25 cases, 1 of them CUDA-only) and the existing 11 cases wait
    for the T4 job.
- **Rescorer review (coordinator, read-only, $0).** `RULE_REPAIR_REPRODUCES_HISTORY`: 6 of 6 decisions agree, and
  the rule is declared with no zero-loss veto. The full 564-record reading and the slow tests are NOT_RUN.
- **T4 launcher dry run against `098a3bdc`.**
  - The bundle is 2,326 files and 29.77 MB.
  - The only existing file that differs from `20208c92` is `pointer_learner.py`.
  - The pinned reference image is still offered.
  - The worst case is $2.05.
  - Nothing was uploaded or launched.

## Resource use

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
  - The anchor policy (keep the 0.2 anchors and report their zero-loss metadata, or refuse them) is **unresolved**,
    and is the owner's decision.
- `preflight_dry_run.py` lists 48 container names, but the default container has 53 since `60e382b0`. This drift
  is recorded, not fixed.
