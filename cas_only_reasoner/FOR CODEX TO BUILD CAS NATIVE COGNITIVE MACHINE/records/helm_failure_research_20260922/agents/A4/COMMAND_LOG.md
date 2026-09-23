# A4 command and failure log

Every shell invocation set these exact tool arguments:

```text
workdir = C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/helm-failure-a4
shell = C:/Program Files/PowerShell/7/pwsh.exe
login = false
```

Python invocations used `C:/Python314/python.exe -B`, preceded by:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONIOENCODING='utf-8'
```

## Decisive saved-record probe

Exact executed command (tool output chunk `1bdde9`, completed in `e86d1e`):

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONIOENCODING='utf-8'
& 'C:/Python314/python.exe' -B 'cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/helm_failure_research_20260922/agents/A4/probe_saved_training.py'
```

Exit 0. One execution, elapsed 19.572126699989894 seconds. Output:

```text
Helm 1.0 20260917 updates=1470+16 held_lost 0 retention 93 93
Helm 1.0 20260918 updates=1470+16 held_lost 0 retention 93 93
Helm 1.0 20260919 updates=1470+16 held_lost 1 retention 87 87
Helm 2.0-experimental 20260917 updates=1470+16 held_lost 1 retention 86 78
Helm 2.0-experimental 20260918 updates=1470+16 held_lost 0 retention 93 93
Helm 2.0-experimental 20260919 updates=1470+16 held_lost 5 retention 84 82
```

`PROBE_RUN.json` contains exact environment and case counts. `SAVED_RECORD_ANALYSIS.json` contains the outputs; `READ_FINGERPRINTS.json` binds the 300 original inputs. A row is an input record, not a separate test function.

A second execution used the identical command after adding explicit per-batch eight-kind and saved-total consistency assertions. Tool chunk `b97907` completed in `f96fba`, exit 0, elapsed 21.335677700000815 seconds. It produced the same six summary rows above and again matched all 300 fingerprints. There are 18 distinct subject/function cases and 36 case executions across both runs. PROBE_RUN.json retains the first execution summary. The additional final inspection (`dae12e`, exit 0) re-read the mandatory plain-English CLAUDE section, listed only A4 artifact sizes, and ran `git diff --check`.

## Source-identity inspection

Output chunk `7c3dea`, exit 0, 2.161937 seconds. Actual inline Python used json/pathlib/zipfile/hashlib only. For each of the six manifest subjects it:

```python
r = pathlib.Path(s['receipt_root'])
p = r / 'source.zip'
raw = p.read_bytes()
pin = next(a for a in s['artifacts'] if pathlib.Path(a['path']).name == 'source.zip')
assert hashlib.sha256(raw).hexdigest() == pin['sha256_raw']
loaded = json.loads((r / 'checkpoints/loaded_sources.json').read_text())
mods = {x['path']: x for x in loaded['after']['modules']}
with zipfile.ZipFile(p) as z:
    for n in selected:
        data = z.read(n)
        h = hashlib.sha256(data).hexdigest()
        assert h == mods[n]['sha256']
```

`selected` was exactly:

```text
cncm/typed_pointer_worker.py
research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/pointer_learner.py
research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/pointer_contract.py
research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/learner.py
```

The same inline command wrote `SOURCE_FINGERPRINTS.json` and line-numbered original source excerpts to `SOURCE_EXCERPTS.md`. Output: `PASS six ZIP SHA256 checks and 24 original loaded-source member checks`. This was one inspection, not a neural source import or a pytest execution.

## Exploratory command record

These calls established schema and source locations. The tool transcript contains their complete inline commands. No result depends on text that was truncated from the model-visible output.

| Output chunk | Actual command/query | Exit and result |
|---|---|---|
| 479fed | Get-Content plain-English skills; Get-Location; git status --short; Get-ChildItem -Force -Name; Get-Content CLAUDE.md | 0; initial status clean. Long master-instructions output truncated. |
| 95df5a | git status --short; rg --files -g AGENTS.md -g CLAUDE.md -g CHANGELOG.md -g CODEX_HELM_FAILURE_RESEARCH_TEAM_20260922.md -g COORDINATOR_HANDOFF.md -g RESOURCE_AND_WRITE_BOUNDARIES.md -g WORKSPACE_REPORT.md -g SOURCE_AND_EVIDENCE_MANIFEST.json | 0; sparse checkout contains controlling documents and manifest; no CHANGELOG file visible. |
| 1f4035 | Get-Content CNCM AGENTS.md and five common research documents | 0; current research limits and independent-first-report rule read. |
| 17ea67 | Inline Python reads manifest keys and subjects | 0; full subjects accidentally printed, causing output truncation; superseded by narrow reads. |
| ea435d | Inline Python reads config excluding top-level inputs; worker/checkpoint keys; ZIP member names | 0; nested design ID lists still caused output truncation; superseded by narrow reads. |
| 6da20b | Inline Python recursively summarizes metadata and copies selected source bytes into own tmp/ | 0; verbose summary partly truncated. Initial basename-only source copy could overwrite cncm worker with root bootstrap; corrected in 1bb8e4 and never used as final source evidence. |
| 19f3c5 | rg -n 'clip\|freeze\|requires_grad\|AdamW\|learning_rate\|rehears\|distill\|retention\|restore\|gradient\|manual_seed\|loss\|MAX_PASSES\|early\|warmup\|scheduler' own Helm 2 pointer_learner.py copy | 0; active/dormant setting locations and historical comments found. |
| 1bb8e4 | Inline Python copies cncm/typed_pointer_worker.py under distinct cncm_ prefix, learner.py and loss_plan.py; prints selected learner lines; rg worker phases | 0; original source code read without import. |
| 6f9127 | Inline schema inspection of update/batch rows then guessed heldback_p00_scoring.json | **1**; FileNotFoundError on guessed name. This is an inspection error, not missing historical evidence. |
| d69294 | Inline Python lists actual held filenames and reads retention/model/checkpoint/protocol schemas | 0; p00,p01,p10 are course snapshots; p02,p04,p06,p08 are heldback snapshots. |
| 0c3bed | Inline Python inspects actual course and replay schemas; rg loss reduction and scheduling | 0; correct filenames/schema resolved. |
| a5de80 | Inline Python prints selected original worker, shared loss and contract lines | 0; fixed endpoint, rate limits, loss reduction, order and retention sequence read. |
| 0ba406 | Inline Python summarizes completed SAVED_RECORD_ANALYSIS.json | 0; chronology, per-kind losses and raw answer changes inspected. |
| 2c1580 | Inline Python checks six model identity flags and reads aggregate rates/gradients/replays; git branch --show-current; git rev-parse HEAD; git status --short | 0; branch codex/helm-failure-a4-20260922, HEAD 59b1dd57e57648ab68c1cc26fbae95a957c20cd3, only A4 output untracked. |

All source copies and exploratory metadata are confined to this role's ignored `tmp/`. They are not staged. Original receipts, packages and checkpoints were read-only. No filesystem delete, process termination, Git worktree metadata operation, push or cherry-pick was run by A4.

## Not run

No whole-repository pytest/cargo suite: this is an isolated evidence report and stdlib probe, and project imports could cross the no-model boundary. The relevant saved-record integrity checks above ran and passed. No new semantic grader run, neural execution or causal intervention. The proposed follow-up in FIRST_REPORT.md is explicitly NOT RUN.

## Staging correction

The first explicit nine-file stage (`cdd1e9`) exposed a formatting problem: Python's generated CRLF lines were treated as trailing whitespace by this repository's Git settings. The shell ended 0 because later listing commands succeeded, but a separately captured repeat (`448ea8`) confirmed `git diff --cached --check` exit 2 with 39,968 diagnostic lines. Only this role's generated JSON/Markdown line endings and trailing spaces were normalized; original evidence was untouched. Source excerpts retain original member line numbers and source hashes, with display-only trailing spaces removed. The probe's JSON writes were then changed to explicit LF for future reuse; its record-check logic was unchanged and was not rerun for that formatting-only edit. The final staged whitespace check was rerun before commit.
