# A3 commands and execution record

All shell calls used workdir `C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/helm-failure-a3`, shell `C:/Program Files/PowerShell/7/pwsh.exe`, `login:false`. Each Python invocation used `C:/Python314/python.exe -B` and environment `PYTHONDONTWRITEBYTECODE=1`, `PYTHONIOENCODING=utf-8`. All recorded calls exited 0. No read or probe exceeded 120 seconds; the saved probe enforces its own 115-second stop.

## Reproduce the decisive probe

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONIOENCODING='utf-8'
& 'C:/Python314/python.exe' -B 'cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/helm_failure_research_20260922/agents/A3/audit_teaching_transfer.py'
```

The exact diagnostic source is saved as `audit_teaching_transfer.py`. The source reads the manifest, validates frozen input hashes, reads ZIP members without importing them, reconstructs graph and label facts, and saves only A3 output. `PROBE_RESULTS.initial.json` preserves execution one. `PROBE_RESULTS.json` and `PROBE_STDOUT.json` preserve execution two. `EXECUTION_RECEIPT.json` binds the final script/output hashes and exit 0.

## Actual tool-call chronology

| Tool chunk | Commands / purpose | Exit and limitation |
| --- | --- | --- |
| `7511f6` | `Get-Location`; `rg --files` for controlling files; `git status --short`; `Get-Content` for plain-English skills | 0; initial worktree clean |
| `3c5a92` | `Get-Content` CLAUDE.md, CNCM AGENTS.md, common directive/handoff/boundaries/workspace | 0; combined output truncated |
| `870d7e` | Read AGENTS.md and directive separately; read CLAUDE.md from line 301 onward | 0; recovered controlling research instructions |
| `dfa063` | PowerShell `ConvertFrom-Json` manifest summary; owner authorization read | 0; summary was overbroad/truncated; replaced by selected fields |
| `6fe532` | Python stdin: manifest identifiers, source-package keys, course schema/count samples | 0 |
| `75237f` | Python stdin: ZIP selected source copies into A3/tmp only; course/bank/record fields | 0 |
| `8940e6` | `rg -n` in copied development.py, face_corpus.py, pointer_inputs.py | 0 |
| `518a93` | Python stdin: ZIP artifact names, source locator lines, compact development schema | 0 |
| `76297b` | Python stdin: numbered source excerpts for split, reader, checker | 0; combined display truncated |
| `b50a19` | Python stdin: smaller numbered source excerpts and exact active config fields | 0 |
| `0087c3` | Python stdin: locate batch artifacts and inspect world graph sample | 0; broad artifact display truncated |
| `873317` | Python stdin: inspect saved batch/protocol schema and model source locators | 0 |
| `0cbad7` | Python stdin: numbered graph/readout source excerpts | 0 |
| `bd3052` | Write saved probe via PowerShell literal here-string; run exact command above | 0; 1.129152 s program time; metadata case-count error described below |
| `7de59d` | Preserve initial result; correct only `development_packet_cases` from constant 60 to actual count; rerun command and capture stdout/receipt; `git branch --show-current`; `git rev-parse HEAD` | 0; 1.305959 s program time |
| `18b361` | `rg -n '_graph_blocks\('` on both pinned source copies; print final hashes/source ranges/one graph witness | 0 |

The initial program's computed development results were already 59 packets, 53 reach and 6 parts. Its separately handwritten counting-boundary field incorrectly said 60. Execution two fixes that metadata field only. No scientific result changed. Outputs preserved rather than silently hiding the error.

No source package, original receipt, grader, production source, or other worktree was edited. Temporary copied source stays under A3/tmp and is not staged. Only A3 report/probe/receipts are committed.

## Git verification

Staging was explicit for seven report/probe/receipt files. The plain staged `git diff --cached --check` reports Windows CRLF as trailing whitespace (exit 2); `git -c core.whitespace=cr-at-eol diff --cached --check` passes (exit 0). CRLF output was retained to preserve receipt byte hashes. Exact exits are in GIT_VERIFICATION.json; the large ordinary diagnostic remains only in A3/tmp. This formatting check does not change the research result.
