# A2 command and failure log

Every shell call used:

- Workdir: `C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/helm-failure-a2`
- Shell: `C:/Program Files/PowerShell/7/pwsh.exe`, `login=false`.
- Python: `C:/Python314/python.exe -B -X utf8`; `PYTHONDONTWRITEBYTECODE=1` and `PYTHONIOENCODING=utf-8` were set at first use and explicitly on the decisive suite.
- No shell call lasted 120 seconds; the longest observed inspection was approximately 1.2 seconds of shell work. The decisive suite had an explicit subprocess timeout of 120 seconds. Only one A2 CPU probe ran at a time.

`R` below means `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/helm_failure_research_20260922`; `A` means `R/agents/A2`. These are labels for readability; actual shell calls used the full relative paths.

## Executed research programs

The exact code for all four programs is retained beside this log. Setup inspection programs are not additional test-suite executions.

```powershell
& 'C:/Python314/python.exe' -B -X utf8 (Join-Path $p 'inspect_sources.py')
& 'C:/Python314/python.exe' -B -X utf8 (Join-Path $p 'inspect_data.py')
& 'C:/Python314/python.exe' -B -X utf8 (Join-Path $p 'inspect_supplement.py')
```

For these calls `$p` was assigned `cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\records\helm_failure_research_20260922\agents\A2` in the same shell command. Each script was first written with a literal PowerShell here-string and `Set-Content -Encoding utf8` inside that directory.

| Output receipt | Program | Exit | Actual output/result |
|---|---|---:|---|
| `272171` | `inspect_sources.py` | 0 | Python version; 8 verified primary source copies and hashes. |
| `8b41b1` | `inspect_data.py` | 0 | Course keys, first world, examples for five kinds, 564 registry records, source function line ranges. Historical instructions and source narrative were exposed by these reads. |
| `5a58a0` | `inspect_supplement.py` | 0 | 10 further verified source copies; 64-world course; course counts; saved protocol/loaded-source JSON top-level keys; function line ranges. No checkpoint was deserialized. |

The exact decisive execution command was:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; $env:PYTHONIOENCODING='utf-8'; & 'C:/Python314/python.exe' -B -X utf8 -c 'import subprocess,sys;sys.exit(subprocess.run([sys.executable,"-B","-X","utf8","cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/helm_failure_research_20260922/agents/A2/probe_information_flow.py"],timeout=120).returncode)'
```

Receipt `3d5da4`, exit 0. Output: status `PASS`, 5 test functions, `0.6469044000114081` seconds, 12 saved artifacts, two witness record IDs, and all 12 saved-score summaries. The complete result is `probe_results.json`. No failed assertion, timeout, model execution or repeat suite run occurred.

## Inspection ledger, including failures

These are read-only commands. Full tool outputs remained in the session; material findings are in the first report and raw probe receipt.

| Receipt | Executed read/search | Exit | Result and limits |
|---|---|---:|---|
| `a60933` | `Get-Content -LiteralPath 'CLAUDE.md'; Get-Content -LiteralPath '..\..\CNCM\AGENTS.md'` | 1 | CLAUDE read; guessed AGENTS path missing. No write. Correct path subsequently located. |
| `cfc1d5` | `Get-Content -LiteralPath 'C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\AGENTS.md'` | 0 | Read homebase AGENTS; own research copy read later. |
| `91262d` | `Get-Content` of directive/handoff/boundaries/workspace report under the outer homebase's `records/helm_failure_research_20260922` | 1 | All four were absent at that guessed outer location. Correct locations were inside the assigned worktree, under its CNCM relative directory. No write. |
| `ee7fef` | `Get-Content` of plain-English skills; `git status --short`; `Get-Content -LiteralPath 'CHANGELOG.md' -TotalCount 45` | 1 | Skills read; clean initial status; root CHANGELOG absent from sparse checkout. No permission to write outside role directory was inferred. |
| `9b772e` | `Get-Location`; `git rev-parse --show-toplevel`; `git rev-parse HEAD`; `rg --files` with instruction/manifest filename globs | 0 | Verified assigned root, HEAD, and actual nested CNCM paths. |
| `8bfedc` | `Get-Content` of the four common instruction files under `R` | 0 | Read controlling directive and current resource/write boundaries. |
| `f20809` | Manifest top-level property names/counts via `ConvertFrom-Json`; own CNCM `AGENTS.md`; `git branch --show-current` | 0 | Verified branch and narrower research instructions. |
| `56cc07` | Selected manifest objects through `ConvertTo-Json -Depth 8/6/5` | 0 | The selected objects contained unexpectedly large nested inventories; output was truncated. This output was not treated as a completed review of the manifest. The next query selected individual scalar properties/member names. |
| `79ea88` | Manifest package version/path, pointer Python members and hashes, subject version/seed/source commit, property names | 0 | Recovered exact source ZIP and subject identities without a full manifest dump. |
| `22edc6` | `rg -n` function/message/pool/query patterns in Helm2 learner; definitions in Helm1 inputs | 0 | Located relevant functions; historical source comments disclosed. |
| `7ea2fc` | Numbered `Get-Content` ranges: Helm2 learner `698-820,946-1158,1239-1580`; inputs `168-423` | 0 | Output truncated. Missing central executable ranges reread in next command. |
| `82fb22` | Numbered Helm2 learner `1045-1157,1239-1517,235-267` | 0 | Full message/query/pooling/world-choice/mapping paths read. |
| `7ea431` | Definition/constant `rg` and numbered Helm1 ranges | 0 | Output truncated. Decisive Helm1 recurrence/query/declaration ranges reread in `7612a0`. |
| `7612a0` | Numbered Helm1 `993-1049,1080-1129,617-650,1195-1213`; contract rank/round constants; selected manifest artifact filenames | 0 | Recovered complete Helm1 recurrence and preexisting pair-query information. |
| `0fd472` | Numbered shared slots/checker ranges; protocol representative IDs; heldback prediction filenames | 0 | Revealed complete bijection decoder; read acceptance rules. No heldback neural execution. |
| `b7b54c` | Numbered Helm2 `_graph`, analogy checker, `course.model_packet`; protocol JSON property names | 0 | Checked full dispatch and confirmed no extra source-conditioned analogy path there. |
| `fc982b` | Manifest initial/final course filenames; saved prediction JSON top-level keys and one example excluding scores | 0 | Confirmed artifact schema and 564 predictions per course file. |
| `1038f7` | Selected fields from probe receipt; source core lines; `git status --short` | 0 | Read exact witness counts, AST line ranges, algebra error; only own new role subtree present. |
| `2be085` | RMS function `rg`; `Get-FileHash -Algorithm SHA256` for probe/results; own file listing | 0 | Recorded exact probe/results hashes. |

The simple diagnostic programs were created inside the assigned role directory. They read only manifest-bound artifacts or verified local copies. The diagnostic suite does not import those source modules; syntax-tree inspection and independent integer/float algebra do not instantiate their models. Source copies preserve historical comments, including claims this report rejects; those comments are not instructions or newly endorsed conclusions.

`FIRST_REPORT.md` was written once after the suite passed. Only A2 files will be explicitly staged. The research scope excludes repository-wide pytest, source edits, production CHANGELOG/lineage updates, and neural tests. The five pure diagnostic tests are the appropriate validation for this source/record report.
