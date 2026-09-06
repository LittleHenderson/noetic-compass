param()
$ErrorActionPreference = 'Stop'
$diagRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$diagFinal = Get-Content -Raw -LiteralPath (Join-Path $diagRoot 'FINAL_RECEIPT.json') | ConvertFrom-Json
$diagChecked = 0
foreach ($diagItem in $diagFinal.files) {
    $diagPath = [System.IO.Path]::GetFullPath((Join-Path $diagRoot $diagItem.path))
    if (-not $diagPath.StartsWith($diagRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) { throw 'FILE_OUTSIDE_RECEIPT_DIRECTORY' }
    $diagFile = Get-Item -LiteralPath $diagPath
    if ($diagFile.LinkType -or $diagFile.Length -ne $diagItem.bytes) { throw ('FILE_TYPE_OR_SIZE_MISMATCH: ' + $diagItem.path) }
    $diagHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $diagPath).Hash.ToLowerInvariant()
    if ($diagHash -ne $diagItem.sha256) { throw ('FILE_HASH_MISMATCH: ' + $diagItem.path) }
    $diagChecked += 1
}
$diagLaunch = Get-Content -Raw -LiteralPath (Join-Path $diagRoot 'execution_001/launch_receipt.json') | ConvertFrom-Json
if ($diagLaunch.status -ne 'AWS_DIAGNOSTIC_FINISHED' -or -not $diagLaunch.termination_confirmed -or -not $diagLaunch.artifact_verified -or $diagLaunch.cleanup_errors.Count -ne 0 -or $diagLaunch.remaining_job_volumes.Count -ne 0) { throw 'LAUNCH_OR_CLEANUP_NOT_COMPLETE' }
if ($diagLaunch.job -ne $diagFinal.job -or $diagLaunch.result.sha256 -ne $diagFinal.cloud_archive_sha256 -or $diagLaunch.source_sha -ne $diagFinal.worker_source_sha) { throw 'LAUNCH_IDENTITY_MISMATCH' }
[ordered]@{
    status = 'SAVED_DIAGNOSTIC_EVIDENCE_VERIFIED'
    checked_files = $diagChecked
    final_receipt_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $diagRoot 'FINAL_RECEIPT.json')).Hash.ToLowerInvariant()
    job = $diagFinal.job
    provider_calls = $false
    neural_execution = $false
    native_execution = $false
    boundary = 'Saved-byte and recorded-result verification; not a new GPU run or current AWS query.'
} | ConvertTo-Json -Depth 5
