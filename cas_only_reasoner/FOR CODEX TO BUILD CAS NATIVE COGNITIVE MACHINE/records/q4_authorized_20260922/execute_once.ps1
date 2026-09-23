$ErrorActionPreference = 'Stop'
$q4Record = $PSScriptRoot
$q4Project = Split-Path (Split-Path $q4Record -Parent) -Parent
$q4Dependency = 'C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_runtime\q4_auth_20260922'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:HELM_Q4_AUTH_DEPENDENCY_DIR = $q4Dependency
$env:PYTHONPATH = $q4Dependency
$q4Log = Join-Path $q4Record 'execute.log'
if (Test-Path -LiteralPath $q4Log) { throw 'Existing launch log: this command is single-use.' }
Set-Location -LiteralPath $q4Project
& 'C:\Users\wakil\venvs\cas-gpu\Scripts\python.exe' -B 'research/helm_cas_expression_lab/q4_smoke_job.py' execute --plan "$q4Record/plan.json" --conversation-authorization "$q4Record/conversation_authorization.json" --conversation-sha256 'b0570c68e092e3b94e4075660cb84bb35bfd9bc1a8d294970a0075cd3baaa029' 2>&1 | Tee-Object -FilePath $q4Log
exit $LASTEXITCODE
