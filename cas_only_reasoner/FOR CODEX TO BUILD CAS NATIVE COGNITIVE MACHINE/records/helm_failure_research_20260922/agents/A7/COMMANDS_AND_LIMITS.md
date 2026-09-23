# A7 commands, failures and scope

All shell calls used the explicit workdir below, PowerShell `C:/Program Files/PowerShell/7/pwsh.exe`, and `login:false`. No command used the unrelated app default directory. No command wrote outside A7's allowed subtree except Git's normal index/commit metadata for this role branch.

Workdir:
`C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/helm-failure-a7`

Role output relative to that workdir:
`cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/helm_failure_research_20260922/agents/A7`

Initial `git status --short` was empty. `git rev-parse HEAD` returned `59b1dd57e57648ab68c1cc26fbae95a957c20cd3`. The supplied research package HEAD was independently read as `3f7ac2967c4bc38313a003e2817a3dcab58451d1` before reading the reports. Original evidence paths came from `SOURCE_AND_EVIDENCE_MANIFEST.json`; originals were never replaced by peer outputs.

## Executed record probe

Exact substantive command, repeated after the three documented corrections:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONIOENCODING='utf-8'
& C:/Python314/python.exe -B 'cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/helm_failure_research_20260922/agents/A7/verify_original_records.py' 2>&1 | Tee-Object -FilePath 'cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/helm_failure_research_20260922/agents/A7/CHECK_STDOUT.txt'
exit $LASTEXITCODE
```

| Attempt | Tool chunk | Exit | Actual result |
|---|---|---:|---|
| 1 | ecdd55 | 1 | `StopIteration` during source preparation. The manifest has two representative source-member inventories, not six per-seed inventories. Corrected lookup to version while retaining every seed's full-ZIP hash check. |
| 2 | 749a83 | 1 | Failed schema assertion on `void_paths_taken`: the original field is an empty list, not integer zero. Corrected the type expectation; no original changed. |
| 3 | a3b71f | 1 | The substantive gate/loss/analogy/overlap checks completed, and all 708 development comparisons completed. The final peer metadata check expected zero but F2 stores an empty disagreement list. Corrected only that schema expectation. |
| 4 | a81eda | 0 | Completed all five functions and wrote ORIGINAL_RECORD_CHECKS.json. Internal time `0.6102173999970546` seconds. |

Before retries, each failed stdout file was retained with `Rename-Item -LiteralPath .../CHECK_STDOUT.txt -NewName CHECK_FAILED_0N.txt`. Every rename stayed inside A7's subtree. The successful program uses a 115-second watchdog. No attempts approached the 120-second limit. Probes ran sequentially in one CPU slot. There were four attempts, three partial failures and one completed suite. Successful JSON counters describe that invocation only, not the attempt history. The final attempt repeats computations already reached by attempt 3; do not count those as new independent cases.

The five named check functions are `check_gate`, `check_lost_reach`, `check_analogy`, `check_graph_overlap`, and `check_development`. No pytest or cargo test was run; broader repository tests and model execution would exceed this report-only scope.

- Gate: six version/seed subjects; 108 paired primary question cases. All-family reporting regroups 50 held questions per subject using saved scores. These overlap the primary cases; semantic correctness for the whole held panel was not independently rederived by A7. A1 used the historical checker for that separate semantic check.
- Lost reach: two unique questions, five input records, ten endpoint predictions and sixty scores. Exact targets were independently derived from original graphs. Complete original prediction objects were also compared with F1's raw objects.
- Analogy: two original witness records, the full 64-world bank, eighteen complete accepted candidates across two disjoint sets, and one original H2 seed18 final prediction file. All 62 candidate columns that remain non-focus are equal for the pair. This is a selected repetition of existing evidence, not new model predictions or a second follow-up round.
- Overlap: 147 actual first-pass batches for H2 seed19; 358 trained record IDs, nineteen trained focus worlds and five held worlds. All five flagged-graph witnesses independently recovered. Other runs/order claims are attributed to A3/A4.
- Development: 59 shared inputs × six subjects × two endpoints = 708 exact-answer comparisons, including 636 reach and 72 parts. These are repeated observations of one dataset, not 708 independent examples.
- Custody in the successful probe: 56 unique original files, 22 ZIP-member observations, and two historical grader Git blobs. Full identities are in the result. No checkpoint bytes were deserialized or interpreted as model weights.

The probe independently implements graph matching, reach/parts target derivation, deterministic max selection and exact binomial arithmetic. It does not import or execute the historical project code. The frozen population and most held-score correctness flags are reused. This is not an independent experiment or complete integrity recertification.

## Document checks

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONIOENCODING='utf-8'
& C:/Python314/python.exe -B 'cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/helm_failure_research_20260922/agents/A7/verify_report_tables.py' 2>&1 | Tee-Object -FilePath 'cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/helm_failure_research_20260922/agents/A7/REVIEW_STDOUT.txt'
exit $LASTEXITCODE
```

First attempt d89266 exited 1 because the live integration FOLLOWUP_PLAN.md had changed after the supplied review commit. Read-only `git -C <integration> diff 3f7ac2967c4bc38313a003e2817a3dcab58451d1 -- <record-path>/FOLLOWUP_PLAN.md` showed cosmetic spacing edits, including A1 becoming A 1. A0 acknowledged that its regex was too broad and said it would restore affected coordinator files. No investigator output was altered.

The corrected helper binds the originally reviewed versions to exact Git blobs at 3f7ac296, records live hashes separately, preserves changed baseline coordinator files under A7/tmp/at_review_pin, and still requires every selected investigator report/raw file to match byte-for-byte. Second attempt 2ed4df exited 0: twelve document result-table rows matched A7 calculations and 26 selected reviewed files were bound to the supplied commit. `REVIEW_FAILED_01.txt`, `REVIEW_STDOUT.txt` and `REVIEW_RECEIPT.json` preserve the distinction. This helper has zero formal test functions and supplies document/custody checks, not behavioral evidence. Two attempts, one completed execution; no substantive record probe rerun.

## Read-only inspection record

Instructions read: own CLAUDE.md and CNCM AGENTS.md; common directive, boundaries, workspace report and manifest; plain-English skills. BRAIN_LINEAGE's opening section and AUDIT_PACK's opening section were read from the original project as historical narrative exposure. Their broader edit/audit instructions were not used to override the current narrower writing and compute limits.

Exact read-command forms were `Get-Content -LiteralPath <listed file>`, `Get-ChildItem -LiteralPath <record directory> -File -Name`, `rg --files -g <instruction/evidence name>`, and bounded Python stdin scripts using `json`, `pathlib`, and `zipfile` to inspect keys, original records and specified source-line intervals. The original raw file comparisons and their source locators are reproducible with the committed main probe.

| Tool chunks | Reads / exit and recovery |
|---|---|
| c8e583, 77e032 | Clean initial Git status/HEAD, CLAUDE.md, evidence-file discovery and two plain-English skills; exit 0. First large CLAUDE display was truncated. |
| 8a14bc | CNCM AGENTS, boundaries, workspace, directory list. Final `Get-Content -LiteralPath CHANGELOG.md -TotalCount 85` failed because the sparse root has no such file; exit 1. No changelog or other out-of-scope file was created. |
| 7aa527 | Full research directive and manifest size; final `rg --files` for absent sparse-checkout names returned exit 1. Original-project BRAIN_LINEAGE/AUDIT_PACK were located through the manifest workspace later. |
| 24b10d | Verified integration HEAD, report inventory, manifest top-level schema, original BRAIN_LINEAGE opening; exit 0. |
| dcdfd7, 535511, 7d9340 | All six FIRST_REPORT and CONFERENCE_RESPONSE files; exit 0. The A2 conference tail in the combined output was truncated, then reread in full in de8605. |
| de8605 | A2 conference again; A1/A5/A6 addenda; F1/F2 reports; actual-session ledger and conference record; exit 0. |
| 626878, 2a0cb8 | Matrix, plan, accounting and manifest/report schemas; exit 0 with oversized schema displays truncated. Subsequent bounded JSON reads selected exact fields. |
| 522586, 3207fb | Original gate, prediction/scoring/course/dev schemas and precise witness queries/worlds; exit 0. No source code executed. |
| 5c50c5 | Original checker and slot-source ranges read directly from source.zip; exit 1 because an inspection range requested slot lines beyond EOF (348). No inference or calculation failed. |
| 937552 | Recovered original pointer-source ranges and remaining dev/batch schema reads; exit 0. |
| cce24d | F1 raw first prediction/scores/target, F2 shape, A2 witness shape, original AUDIT_PACK opening; exit 0. |
| 9ea890, 2ae8fc | Exact source-inventory and F2 metadata schemas during probe recovery; exit 0. |
| 21d3b1 | Inspected A7 complete analogy sets, eighteen candidate score pairs, both focus graphs, all five final lost records, original trained-record IDs/mapping, and original pointer graph/query/pooling/declaration path; exit 0. |
| 0822c3 | Own Git status and record .gitattributes; only A7 untracked files, `* -text`; exit 0. |
| bec9ac | Live integration status and exact diff of later coordinator changes; exit 0. No integration file written by A7. |

Inspection truncation is a display limit, not evidence absence. Decisive results use complete files and hash checks. Later cosmetic coordinator changes are a custody issue recorded above, not a new result or reason to reopen experiments.

## Resource and environment limits

Python 3.14.0 is the investigation runtime only. Historical training runtime/dependency reproduction remains incomplete. Saved source/config/loaded-module identities do not by themselves recreate an executable historical environment.

No Torch, neural model initialization, checkpoint deserialization, inference, training, GPU, provider/cloud action, paid API, install, allowance reset or allowance expansion occurred. No external message was sent. Existing native-agent allowance was used; monetary cost is unavailable. Only this A7 subtree was written. The compiler, model implementation, original source packages, grader, books, atlas and all original outputs were read-only.

## Git verification

`git add -- <role-output>` intentionally staged only the A7 subtree (tool chunk 6ff06e, exit 0). The first CRLF-aware staged check, `git -c core.whitespace=cr-at-eol diff --cached --check`, returned exit 2 (33fdb2): the exact pinned copy of coordinator/TEAM_EXECUTION_LEDGER.md has blank lines at EOF. `GIT_WHITESPACE_CHECK.txt` preserves the finding. That historical copy remains byte-exact; it was not silently reformatted. A subsequent check excludes only A7/tmp/at_review_pin and checks all A7-authored report/probe/receipt files separately. This is a selected formatting check, not a claim that every staged historical byte passes whitespace rules.

A0 later reported its coordinator-format correction at integration `2c4f89ed`, restoring affected documents and comparing all 103 investigator files to the baseline. This is attributed to A0; A7 did not rerun that expanded preservation check. The pinned review receipt and temporary baseline copies are preserved.

No passing document or formatting check should be mistaken for model readiness or a broader repository test pass. The final role commit and report SHA256 values are returned to A0 through the native session; the coordinator integrates the final two reports verbatim.
