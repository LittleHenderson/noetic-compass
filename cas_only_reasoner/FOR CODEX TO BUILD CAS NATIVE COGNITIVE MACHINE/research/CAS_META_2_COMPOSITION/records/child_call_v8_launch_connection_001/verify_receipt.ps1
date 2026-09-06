# Read-only audit of this preparation record. No provider or neural imports.
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$receiptPath = Join-Path $PSScriptRoot 'FINAL_RECEIPT.json'
$record = Get-Content -Raw -LiteralPath $receiptPath | ConvertFrom-Json
$checked = 0
foreach ($item in @($record.evidence_files) + @($record.source_files) + @($record.external_inputs)) {
    $target = if ($item.absolute_path) { $item.absolute_path } else { Join-Path $taskRoot $item.path }
    $actual = Get-Item -LiteralPath $target
    if (-not $actual.PSIsContainer -and $actual.Length -eq $item.bytes -and
        (Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash.ToLower() -eq $item.sha256) {
        $checked += 1
    } else { throw "Artifact identity mismatch: $target" }
}
$requestPath = Join-Path $PSScriptRoot 'launch_request.json'
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $requestPath).Hash.ToLower() -ne $record.launch_request_sha256) {
    throw 'Launch request identity mismatch'
}
$request = Get-Content -Raw -LiteralPath $requestPath | ConvertFrom-Json
if ($request.job -ne $record.job -or $request.parent_source_sha -ne $record.parent_source_sha -or
    $request.worker_source_sha -ne $record.worker_source_sha -or $request.launch_authorized -ne $false) {
    throw 'Launch request binding mismatch'
}
$prefix = git -C $taskRoot rev-parse --show-prefix
if ($LASTEXITCODE -ne 0) { throw 'Git repository unavailable' }
foreach ($item in $record.source_files) {
    $target = Join-Path $taskRoot $item.path
    $blob = git -C $taskRoot hash-object --no-filters -- $target
    if ($LASTEXITCODE -ne 0) { throw "Cannot hash source: $target" }
    $committed = git -C $taskRoot rev-parse ($record.parent_source_sha + ':' + $prefix + $item.path)
    if ($LASTEXITCODE -ne 0 -or $blob -ne $committed) { throw "Committed source mismatch: $target" }
}
foreach ($check in $record.test_runs) {
    $testReceipt = Get-Content -Raw -LiteralPath (Join-Path $taskRoot $check.receipt) | ConvertFrom-Json
    $stdout = Get-Content -Raw -LiteralPath (Join-Path $taskRoot $check.stdout)
    if ($testReceipt.exit_code -ne 0 -or $testReceipt.source_unchanged -ne $true -or
        -not $stdout.Contains($check.exact_summary)) { throw "Test evidence mismatch: $($check.receipt)" }
}
@{
    status = 'PREPARATION_EVIDENCE_IDENTITIES_VERIFIED'
    files_checked = $checked
    source_files_checked_against_commit = @($record.source_files).Count
    parent_source_sha = $record.parent_source_sha
    launch_request_sha256 = $record.launch_request_sha256
    final_receipt_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $receiptPath).Hash.ToLower()
    observed_utc = [DateTime]::UtcNow.ToString('o')
    provider_calls = $false
    paid_launch = $false
    boundary = 'Hashes and existing receipts only. Does not rerun tests or execute the model.'
} | ConvertTo-Json -Depth 4
