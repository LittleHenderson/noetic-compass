[CmdletBinding()]
param(
    [string]$OutputDirectory = "",
    [switch]$VerifyOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$candidateRoot = $PSScriptRoot
$repoRoot = Split-Path -Parent (Split-Path -Parent $candidateRoot)
$corePath = Join-Path $repoRoot "tools\runpod_open_weight_canary_v2\aws_production_guardian_core.py"
$runtimePath = Join-Path $candidateRoot "src\guardian_runtime.py"
$lockPath = Join-Path $candidateRoot "core-lock.json"
$aslPath = Join-Path $candidateRoot "state_machine.asl.json"
$templatePath = Join-Path $candidateRoot "template.yaml"
$bindingToolPath = Join-Path $candidateRoot "create_deployment_binding.py"
$testsPath = Join-Path $candidateRoot "tests\test_guardian_runtime.py"
$coreTestsPath = Join-Path $repoRoot "tools\runpod_open_weight_canary_v2\test_aws_production_guardian_core.py"
$precreateTestsPath = Join-Path $repoRoot "tools\runpod_open_weight_canary_v2\test_precreate_guardian_offline.py"
$buildScriptPath = $PSCommandPath

foreach ($path in @(
    $corePath,
    $runtimePath,
    $lockPath,
    $aslPath,
    $templatePath,
    $bindingToolPath,
    $testsPath,
    $coreTestsPath,
    $precreateTestsPath,
    $buildScriptPath
)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "BUILD_INPUT_ABSENT"
    }
}

$lock = Get-Content -LiteralPath $lockPath -Raw | ConvertFrom-Json
if ($lock.schema_version -ne "cas_aws_runpod_guardian_core_lock.v1") {
    throw "CORE_LOCK_SCHEMA_MISMATCH"
}

function Get-LowerSha256([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

$actual = [ordered]@{
    core_sha256 = Get-LowerSha256 $corePath
    runtime_sha256 = Get-LowerSha256 $runtimePath
    state_machine_sha256 = Get-LowerSha256 $aslPath
    template_sha256 = Get-LowerSha256 $templatePath
    build_script_sha256 = Get-LowerSha256 $buildScriptPath
    binding_tool_sha256 = Get-LowerSha256 $bindingToolPath
    tests_sha256 = Get-LowerSha256 $testsPath
    core_tests_sha256 = Get-LowerSha256 $coreTestsPath
    precreate_tests_sha256 = Get-LowerSha256 $precreateTestsPath
}
foreach ($name in $actual.Keys) {
    if ($lock.$name -ne $actual[$name]) {
        throw "HASH_LOCK_MISMATCH_$($name.ToUpperInvariant())"
    }
}
$coreLockDocumentSha256 = Get-LowerSha256 $lockPath

if ($VerifyOnly) {
    [ordered]@{
        schema_version = "cas_aws_runpod_guardian_build_verification.v1"
        status = "PASS"
        core_lock_sha256 = $coreLockDocumentSha256
        hashes = $actual
    } | ConvertTo-Json -Depth 5
    exit 0
}

if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $candidateRoot "dist"
}
$resolvedCandidate = [IO.Path]::GetFullPath($candidateRoot)
$resolvedOutput = [IO.Path]::GetFullPath($OutputDirectory)
$candidatePrefix = $resolvedCandidate + [IO.Path]::DirectorySeparatorChar
if (
    $resolvedOutput -ne $resolvedCandidate -and
    -not $resolvedOutput.StartsWith($candidatePrefix, [StringComparison]::OrdinalIgnoreCase)
) {
    throw "OUTPUT_MUST_REMAIN_INSIDE_CANDIDATE_DIRECTORY"
}
New-Item -ItemType Directory -Path $resolvedOutput -Force | Out-Null
$zipPath = Join-Path $resolvedOutput "guardian-runtime.zip"

$temporaryRoot = Join-Path ([IO.Path]::GetTempPath()) ("cas-guardian-build-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $temporaryRoot | Out-Null
try {
    $packageInputs = [ordered]@{
        "aws_production_guardian_core.py" = $corePath
        "guardian_build_identity.py" = Join-Path $temporaryRoot "guardian_build_identity.py"
        "guardian_runtime.py" = $runtimePath
    }
    $identityLines = @(
        '"""Generated immutable build identity; do not edit."""',
        "CORE_LOCK_DOCUMENT_SHA256 = `"$coreLockDocumentSha256`"",
        "LOCKED_HASHES = {"
    )
    foreach ($name in $actual.Keys) {
        $identityLines += "    `"$name`": `"$($actual[$name])`","
    }
    $identityLines += "}"
    $identityText = $identityLines -join "`n"
    [IO.File]::WriteAllText(
        $packageInputs["guardian_build_identity.py"],
        $identityText + "`n",
        [Text.UTF8Encoding]::new($false)
    )
    Add-Type -AssemblyName System.IO.Compression
    $stream = [IO.File]::Open($zipPath, [IO.FileMode]::Create, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    try {
        $archive = [IO.Compression.ZipArchive]::new($stream, [IO.Compression.ZipArchiveMode]::Create, $false)
        try {
            foreach ($entryName in ($packageInputs.Keys | Sort-Object)) {
                $entry = $archive.CreateEntry($entryName, [IO.Compression.CompressionLevel]::Optimal)
                $entry.LastWriteTime = [datetimeoffset]::new(2026, 8, 20, 0, 0, 0, [timespan]::Zero)
                $entryStream = $entry.Open()
                try {
                    $sourceStream = [IO.File]::OpenRead($packageInputs[$entryName])
                    try {
                        $sourceStream.CopyTo($entryStream)
                    }
                    finally {
                        $sourceStream.Dispose()
                    }
                }
                finally {
                    $entryStream.Dispose()
                }
            }
        }
        finally {
            $archive.Dispose()
        }
    }
    finally {
        $stream.Dispose()
    }
}
finally {
    if (Test-Path -LiteralPath $temporaryRoot) {
        Remove-Item -LiteralPath $temporaryRoot -Recurse -Force
    }
}

$manifest = [ordered]@{
    schema_version = "cas_aws_runpod_guardian_build_manifest.v1"
    status = "BUILT_OFFLINE_NOT_DEPLOYED"
    core_sha256 = $actual.core_sha256
    core_lock_sha256 = $coreLockDocumentSha256
    runtime_sha256 = $actual.runtime_sha256
    state_machine_sha256 = $actual.state_machine_sha256
    template_sha256 = $actual.template_sha256
    build_script_sha256 = $actual.build_script_sha256
    binding_tool_sha256 = $actual.binding_tool_sha256
    tests_sha256 = $actual.tests_sha256
    core_tests_sha256 = $actual.core_tests_sha256
    precreate_tests_sha256 = $actual.precreate_tests_sha256
    zip_sha256 = Get-LowerSha256 $zipPath
    zip_bytes = (Get-Item -LiteralPath $zipPath).Length
    zip_entries = @(
        "aws_production_guardian_core.py",
        "guardian_build_identity.py",
        "guardian_runtime.py"
    )
}
$manifestPath = Join-Path $resolvedOutput "build-manifest.json"
$manifestJson = $manifest | ConvertTo-Json -Depth 5
[IO.File]::WriteAllText($manifestPath, $manifestJson + "`n", [Text.UTF8Encoding]::new($false))
$manifestJson
