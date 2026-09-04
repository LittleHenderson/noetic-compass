param(
    [Parameter(Mandatory = $true)]
    [string]$RepositoryRoot,
    [string]$Python = "C:\Python314\python.exe",
    [string]$SourceSha = "dec08c81644f1c47b4b94c29a406a9432df7c7bd"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$minimumPowerShell = [version]"7.3"
if ($PSVersionTable.PSVersion -lt $minimumPowerShell) {
    throw "PowerShell 7.3 or newer is required so native-command failures stop the run"
}
$PSNativeCommandUseErrorActionPreference = $true
$env:PYTHONDONTWRITEBYTECODE = "1"
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue

$expectedSourceSha = "dec08c81644f1c47b4b94c29a406a9432df7c7bd"
$resolvedSourceSha = (git -C $RepositoryRoot rev-parse --verify "$SourceSha^{commit}").Trim()
if ($resolvedSourceSha -ne $expectedSourceSha) {
    throw "SourceSha must resolve to the frozen v0.2 commit $expectedSourceSha"
}
$SourceSha = $resolvedSourceSha

$token = $SourceSha.Substring(0, 8) + "-" + [guid]::NewGuid().ToString("N")
$scratchRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("casformer-v02-repro-" + $token)
$sourceCheckout = Join-Path $scratchRoot "source"
$buildCheckout = Join-Path $scratchRoot "build"
$runRoot = Join-Path $scratchRoot "run"
$stateRoot = Join-Path $runRoot "state"
$demoRoot = Join-Path $runRoot "demo"
$v1Dist = Join-Path $runRoot "v1-dist"
$v2Dist = Join-Path $runRoot "v2-dist"
$venv = Join-Path $runRoot "venv"
$venvPython = Join-Path $venv "Scripts\python.exe"
$relativeCncm = "cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
$evidenceRoot = Split-Path -Parent $PSScriptRoot
$computeProbe = Join-Path $evidenceRoot "probes\compute_plan_mismatch_probe.py"
$artifactProbe = Join-Path $evidenceRoot "probes\inspect_release_artifacts.py"
$buildConstraints = Join-Path $PSScriptRoot "build-constraints.txt"

function Assert-FileSha256 {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Expected
    )
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
    if ($actual -ne $Expected) {
        throw "SHA-256 mismatch for ${Path}: expected $Expected, got $actual"
    }
}

function Assert-OutputMatch {
    param(
        [Parameter(Mandatory = $true)][object[]]$Output,
        [Parameter(Mandatory = $true)][string]$Pattern,
        [Parameter(Mandatory = $true)][string]$Label
    )
    $text = $Output -join "`n"
    if ($text -notmatch $Pattern) {
        throw "$Label did not report the required exact count"
    }
}

Assert-FileSha256 $computeProbe "5a45dd0b1c3bf530e31a2562a76ce8ddfcbaa72b9eef127b6cff8b99cdb954d5"
Assert-FileSha256 $artifactProbe "5bcb0707bfb751891b2c3969ca887a218a7cd978486908e38a9e2bf197d8d5e3"
Assert-FileSha256 $buildConstraints "5b96a1b3ab68ccbd56cda1f7d56e804b7ac05194b86762b3763c84c13a92cfeb"

New-Item -ItemType Directory -Path $scratchRoot, $runRoot, $stateRoot, $demoRoot, $v1Dist, $v2Dist | Out-Null

git -C $RepositoryRoot worktree add --detach $sourceCheckout $SourceSha
git -C $RepositoryRoot worktree add --detach $buildCheckout $SourceSha

if (git -C $sourceCheckout status --porcelain=v1 --untracked-files=all) {
    throw "verification source worktree is not clean"
}
if (git -C $buildCheckout status --porcelain=v1 --untracked-files=all) {
    throw "build source worktree is not clean"
}
if ((git -C $sourceCheckout rev-parse HEAD) -ne $SourceSha) {
    throw "verification worktree is not pinned to the source freeze"
}
if ((git -C $buildCheckout rev-parse HEAD) -ne $SourceSha) {
    throw "build worktree is not pinned to the source freeze"
}

$cncmSource = Join-Path $sourceCheckout $relativeCncm
$cncmBuild = Join-Path $buildCheckout $relativeCncm
$v1Source = Join-Path $cncmSource "research\CASFORMER_v0_1"
$v2Source = Join-Path $cncmSource "research\CAS_CJT_TRANSFORMER_v0_2"
$v1Build = Join-Path $cncmBuild "research\CASFORMER_v0_1"
$v2Build = Join-Path $cncmBuild "research\CAS_CJT_TRANSFORMER_v0_2"

uv build --clear --wheel --build-constraints $buildConstraints --python $Python --out-dir $v1Dist $v1Build
uv build --clear --build-constraints $buildConstraints --python $Python --out-dir $v2Dist $v2Build

& $Python -m venv $venv
uv pip install --python $venvPython --require-hashes --torch-backend cpu -r (Join-Path $v2Source "requirements.lock")
$v1Wheel = (Get-ChildItem -LiteralPath $v1Dist -Filter "*.whl" -File -ErrorAction Stop).FullName
$v2Wheel = (Get-ChildItem -LiteralPath $v2Dist -Filter "*.whl" -File -ErrorAction Stop).FullName
$v2Sdist = (Get-ChildItem -LiteralPath $v2Dist -Filter "*.tar.gz" -File -ErrorAction Stop).FullName
uv pip install --python $venvPython --no-deps $v1Wheel $v2Wheel
uv pip check --python $venvPython

$artifactOutput = @(
    & $venvPython -I $artifactProbe `
        --v01-wheel $v1Wheel `
        --v02-wheel $v2Wheel `
        --v02-sdist $v2Sdist `
        --source-manifest (Join-Path $v2Source "SOURCE_MANIFEST.json") `
        --requirements-lock (Join-Path $v2Source "requirements.lock")
)
$artifactOutput | ForEach-Object { Write-Output $_ }
$artifactResult = $artifactOutput -join "`n" | ConvertFrom-Json -Depth 100
if ($artifactResult.status -ne "PASS") {
    throw "built artifact inspection failed"
}
if ($artifactResult.source_manifest.file_count -ne 50) {
    throw "built artifacts do not bind the 50-file v0.2 manifest"
}
if ($artifactResult.source_manifest.sha256 -ne "f68b9ba78bb5b6bc184c4b014a799756c1b714f05d05b515dcd464a54c76e634") {
    throw "built artifacts contain the wrong v0.2 source manifest"
}

$importProbe = @'
import importlib.metadata as metadata
import json
from pathlib import Path
import sys
import cas_cjt
import casformer

prefix = Path(sys.prefix).resolve()
cas_cjt_path = Path(cas_cjt.__file__).resolve()
casformer_path = Path(casformer.__file__).resolve()
assert prefix in cas_cjt_path.parents
assert prefix in casformer_path.parents
assert metadata.version("cas-neural-cjt") == "0.2.0"
assert metadata.version("casformer-reference") == "0.1.0"
print(json.dumps({
    "cas_cjt_file": str(cas_cjt_path),
    "casformer_file": str(casformer_path),
    "cas_neural_cjt_version": metadata.version("cas-neural-cjt"),
    "casformer_reference_version": metadata.version("casformer-reference"),
    "python": sys.version,
}, indent=2, sort_keys=True))
'@
Push-Location $stateRoot
try {
    & $venvPython -I -c $importProbe
} finally {
    Pop-Location
}

$demo = Join-Path $venv "share\cas-neural-cjt\examples\complete_reasoning_transistor.py"
$demoDatabase = Join-Path $demoRoot "complete_reasoning_transistor.sqlite3"
Push-Location $stateRoot
try {
    $demoOutput = @(& $venvPython -I $demo --database $demoDatabase)
    $demoOutput | ForEach-Object { Write-Output $_ }
    $demoResult = $demoOutput -join "`n" | ConvertFrom-Json -Depth 100
    if (
        $demoResult.trace_count -ne 6 -or
        $demoResult.accepted_effects -ne 5 -or
        $demoResult.integrity -ne $true -or
        $demoResult.repair_closed -ne $true -or
        $demoResult.same_input_output_changed -ne $true -or
        $demoResult.invalid_update_reason -ne "CHECKPOINT_PARAMETER_SCOPE_ESCAPE"
    ) {
        throw "installed demo did not reproduce the accepted v0.2 result"
    }
} finally {
    Pop-Location
}

$traceProbe = @'
import json
import sys
from cas_cjt.contracts import validate_contract
from cas_cjt.persistence import SQLiteAtomicStore

store = SQLiteAtomicStore(sys.argv[1])
traces = store.trace_events()
results = [
    {
        "trace_id": trace["trace_id"],
        "tick": trace["tick"],
        "schema_valid": validate_contract(trace) == trace,
    }
    for trace in traces
]
integrity = store.verify_integrity()
output = {
    "trace_count": len(traces),
    "schema_validated": sum(1 for item in results if item["schema_valid"]),
    "integrity": integrity,
    "status": "PASS",
    "traces": results,
}
store.close()
assert output["trace_count"] == 6
assert output["schema_validated"] == 6
assert output["integrity"] is True
print(json.dumps(output, indent=2, sort_keys=True))
'@
Push-Location $stateRoot
try {
    & $venvPython -I -c $traceProbe $demoDatabase
} finally {
    Pop-Location
}

Push-Location $stateRoot
try {
    $v02Output = @(& $venvPython -I -m pytest -q -p no:cacheprovider -o addopts= --import-mode=prepend --rootdir $v2Source -c (Join-Path $v2Source "pytest.ini") (Join-Path $v2Source "tests"))
    $v02Output | ForEach-Object { Write-Output $_ }
    Assert-OutputMatch $v02Output '(?m)^250 passed in [0-9.]+s$' "v0.2 suite"

    $manifestOutput = @(& $venvPython -I -m pytest -q -p no:cacheprovider -o addopts= --import-mode=prepend --rootdir $v2Source -c (Join-Path $v2Source "pytest.ini") (Join-Path $v2Source "tests\test_source_manifest.py"))
    $manifestOutput | ForEach-Object { Write-Output $_ }
    Assert-OutputMatch $manifestOutput '(?m)^5 passed in [0-9.]+s$' "v0.2 manifest suite"
} finally {
    Pop-Location
}

Push-Location $v1Source
try {
    $v01Output = @(& $venvPython -I -m pytest -q -p no:cacheprovider -o addopts=)
    $v01Output | ForEach-Object { Write-Output $_ }
    Assert-OutputMatch $v01Output '(?m)^89 passed in [0-9.]+s$' "frozen v0.1 suite"
} finally {
    Pop-Location
}

Push-Location $cncmSource
try {
    $cncmOutput = @(& $venvPython -I -m pytest -q -p no:cacheprovider -o addopts=)
    $cncmOutput | ForEach-Object { Write-Output $_ }
    Assert-OutputMatch $cncmOutput '(?m)^181 passed, 403 subtests passed in [0-9.]+s$' "CNCM regression suite"
} finally {
    Pop-Location
}

$focused = @(
    "tests/test_network_coordinator.py::test_requested_but_unretained_memory_record_is_rejected_atomically",
    "tests/test_network_coordinator.py::test_unrequested_memory_read_claim_is_rejected_without_moving_head",
    "tests/test_network_coordinator.py::test_poisoned_mixed_memory_batch_writes_nothing_authoritative",
    "tests/test_network_coordinator.py::test_huge_observation_under_zero_compute_ceiling_is_rejected_atomically",
    "tests/test_network_coordinator.py::test_checkpoint_scope_escape_rejects_cross_cjt_bytes_and_keeps_head",
    "tests/test_persistence_coordinator_trace.py::test_selected_reconstruction_binds_trace_payload_to_trace_row",
    "tests/test_persistence_coordinator_trace.py::test_trace_tamper_and_chain_discontinuity_are_detected",
    "tests/test_integrated_runtime.py::test_complete_four_cjt_reasoning_transistor"
)
Push-Location $v2Source
try {
    $focusedOutput = @(& $venvPython -I -m pytest -vv -p no:cacheprovider -o addopts= --import-mode=prepend --rootdir $v2Source -c (Join-Path $v2Source "pytest.ini") @focused)
    $focusedOutput | ForEach-Object { Write-Output $_ }
    Assert-OutputMatch $focusedOutput '(?m)^=+ 8 passed in [0-9.]+s =+$' "required blocker tests"
} finally {
    Pop-Location
}

Push-Location $stateRoot
try {
    & $venvPython -I $computeProbe $v2Source
} finally {
    Pop-Location
}

if (git -C $sourceCheckout status --porcelain=v1 --untracked-files=all) {
    throw "verification source worktree changed during reproduction"
}
git -C $sourceCheckout diff --exit-code
git -C $buildCheckout diff --exit-code
if ((git -C $sourceCheckout rev-parse HEAD).Trim() -ne $expectedSourceSha) {
    throw "verification source worktree moved away from the source freeze"
}
if ((git -C $buildCheckout rev-parse HEAD).Trim() -ne $expectedSourceSha) {
    throw "build worktree moved away from the source freeze"
}

Write-Output ("powershell=" + $PSVersionTable.PSVersion)
git --version
uv --version
& $venvPython -I -c 'import json, platform, sys; import importlib.metadata as m; import torch; print(json.dumps({"python": sys.version, "platform": platform.platform(), "torch_cuda_available": torch.cuda.is_available(), "packages": {name: m.version(name) for name in ["cas-neural-cjt", "casformer-reference", "jsonschema", "numpy", "pytest", "setuptools", "torch"]}}, indent=2, sort_keys=True))'

Write-Output "source_checkout=$sourceCheckout"
Write-Output "build_checkout=$buildCheckout"
Write-Output "run_root=$runRoot"
Write-Output "CASFORMER_V0_2_RELEASE_REPRODUCED"
