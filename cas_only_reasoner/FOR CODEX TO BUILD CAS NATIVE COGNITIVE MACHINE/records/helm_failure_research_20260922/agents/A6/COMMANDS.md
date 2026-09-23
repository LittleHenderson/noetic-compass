# A6 command and execution receipt

All shell calls used workdir `C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/helm-failure-a6`, shell `C:/Program Files/PowerShell/7/pwsh.exe`, login false. Every returned shell process exit code was 0. Interpreter: Python 3.14.0. No dependency installation or historical Python import occurred.

## Decisive commands (exact relative arguments)

```powershell
$out = 'cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/helm_failure_research_20260922/agents/A6'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONIOENCODING='utf-8'
& 'C:/Python314/python.exe' -B ($out + '/reconstruct.py')
& 'C:/Python314/python.exe' -B ($out + '/verify_lost_reach.py')
& 'C:/Python314/python.exe' -B --version
```

Each diagnostic ran once. The first printed:

```text
{"gains": 10, "losses": 0, "p": "1/1024", "passed": true, "record_cases": 55, "seed": 20260917, "version": "Helm 1.0"}
{"gains": 12, "losses": 0, "p": "1/4096", "passed": true, "record_cases": 55, "seed": 20260918, "version": "Helm 1.0"}
{"gains": 11, "losses": 0, "p": "1/2048", "passed": true, "record_cases": 55, "seed": 20260919, "version": "Helm 1.0"}
{"gains": 11, "losses": 1, "p": "13/4096", "passed": true, "record_cases": 55, "seed": 20260917, "version": "Helm 2.0-experimental"}
{"gains": 12, "losses": 0, "p": "1/4096", "passed": true, "record_cases": 55, "seed": 20260918, "version": "Helm 2.0-experimental"}
{"gains": 7, "losses": 1, "p": "9/256", "passed": false, "record_cases": 55, "seed": 20260919, "version": "Helm 2.0-experimental"}
lost_record_rows=5
```

The second printed `{"all_checks_match_saved_score": true, "lost_question_cases": 2, "lost_record_cases": 5}` and the two unique directed paths (one repeated four times for the four raw records). Both exact paths and every raw comparison are in `reach_verification.json`.

## Read-only discovery and verification

`git status --short`, `git rev-parse --show-toplevel`, `git branch --show-current`, `git rev-parse HEAD`, `rg --files -g CLAUDE.md -g AGENTS.md -g '*Helm*' -g '*helm*'` verified the checkout. `Get-Content -LiteralPath` read CLAUDE.md, CNCM AGENTS.md, the five common handoff/manifest documents and plain-English skills. `ConvertFrom-Json` and `Select-Object` inspected only manifest fields, original gate objects, source rows and own generated output. `rg -n` located grader arithmetic, checkpoint aggregation and decision functions. No peer report was opened.

Three broad exploratory displays exceeded output limits, with exit 0. They were not counted as tests or evidence of complete inspection; smaller subsequent field and numbered-line reads recovered the decisive content. No unavailable source or failed probe was encountered. Writes were confined to A6's assigned subtree.
