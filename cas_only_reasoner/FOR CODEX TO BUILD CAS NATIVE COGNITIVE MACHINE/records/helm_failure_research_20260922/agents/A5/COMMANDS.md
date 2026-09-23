# A5 command record

Every shell invocation used `C:/Program Files/PowerShell/7/pwsh.exe`, `login: false`, explicit workdir:
`C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/helm-failure-a5`.
Initial verified HEAD: 59b1dd57e57648ab68c1cc26fbae95a957c20cd3; branch codex/helm-failure-a5-20260922; git status clean before writes. All writes stayed in agents/A5/.

Substantive execution (tool chunk 8874ba, exit 0):
```powershell
$a5dir = 'cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/helm_failure_research_20260922/agents/A5'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONIOENCODING='utf-8'
& C:/Python314/python.exe -B "$a5dir/probe.py"
```
The tool command first wrote the exact checked-in script from a literal PowerShell here-string. probe.py has a 110-second internal deadline checked during processing; the actual complete probe took 0.7492723000032129 seconds and consumed one CPU slot. It printed the saved SUMMARY.json. No timeout occurred.

Provenance execution (tool chunk e7f96e, exit 0):
```powershell
& C:/Python314/python.exe -B "$a5dir/provenance.py"
```
Output: `{"six_runs_config_source_and_loaded_module_hashes": "MATCH", "modules_per_run": 7, "source_excerpts": 14}`. No failed assertion.

Preregistration commit (tool chunk 46f9fc, exit 0):
```powershell
git add -- 'cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/helm_failure_research_20260922/agents/A5/PREREGISTRATION.md' 'cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/helm_failure_research_20260922/agents/A5/PREREGISTRATION_TIMESTAMP.txt'
git commit -m 'research(A5): preregister answer selection comparisons'
git rev-parse HEAD
```
Result: 32b7acc603765730a4df596de62cc1fbc4f93a53.

Discovery consisted of Get-Content on own CLAUDE.md, CNCM AGENTS.md, common directive/handoff/boundaries/workspace/manifest, `rg --files`, and `rg -n` over source members copied byte-for-byte from the two hashed ZIPs into own tmp/. Python stdlib schema reads and ZIP reads printed bounded excerpts, sample schemas and filenames; these were not model execution or comparison runs. Source inventory reads used json, pathlib, zipfile and hashlib only. Source excerpts, member hashes and all consequential input hashes are saved in SOURCE_PROVENANCE.json/CONSUMED_FILES.json.

Discovery failures/limits: chunk c53952 queried nonexistent manifest `studies` and `jobs` fields, causing two nonterminating null-method PowerShell errors (process exit 0); corrected to `subjects` and `source_packages`. Chunks 1d92e6, 901396, a91965 had verbose output truncation; subsequent selected reads recovered relevant sections. Chunk 630593 misspelled PYTHONIOENCODINGENCODING while reading metadata only; later commands set the proper variable. No assertion, source hash, saved-answer reconstruction or independent correctness check failed. No historical file was edited.

Temporary copied source files in tmp/ remain unstaged scratch evidence; immutable source ZIP member paths and hashes are the authoritative references. No general pytest/cargo suite was run because this task adds research records and pure stdlib probes only, with no implementation change and no permitted dependency install or neural execution.
