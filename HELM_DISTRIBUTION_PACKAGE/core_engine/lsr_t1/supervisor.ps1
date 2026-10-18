# lsr_t1 LOCAL_CPU_ONCE supervisor (copied pattern: fair_data_experiment_v2_sdg/supervisor.ps1).
# Runs only with the exact sign line. Refuses if free RAM < 150 MB. One worker process per part, hard wall 300 s
# (preflight included), worker killed above 300 MiB working set, no network
# (sockets blocked inside the worker), no spend. Single-use run folder per part.
param(
    [Parameter(Mandatory=$true)][string]$ReviewedManifestSha256,
    [Parameter(Mandatory=$true)][string]$OwnerSignLine
)
$ErrorActionPreference = 'Stop'
$timer = [Diagnostics.Stopwatch]::StartNew()
$startedUtc = [DateTimeOffset]::UtcNow
$hardWallSeconds = 300
$memoryCapBytes = 300MB
$stageDir = Split-Path -Parent $PSCommandPath
$projectRoot = Split-Path -Parent $stageDir
$pythonPath = 'C:\Python314\python.exe'
$workerPath = Join-Path $stageDir 'worker.py'
$manifestPath = Join-Path $stageDir 'SOURCE_MANIFEST.json'
$evidenceTemplate = Join-Path $stageDir 'OWNER_APPROVAL_EVIDENCE.template.md'
$runId = 'LSR_T1_MSI_RUN2'
$Part = 'ALL'
$runDir = Join-Path $stageDir "runs\$runId"
$status = 'NOT_STARTED'
$exitCode = $null
$peakBytes = $null
$cpuSeconds = $null
$errorText = $null
$proc = $null
$runDirOwned = $false

function Write-JsonFile([string]$Path, $Value) {
    $Value | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Path -Encoding UTF8
}

try {
    if ($env:COMPUTERNAME -ne 'MSI') { throw 'LOCAL_CPU_ONCE is MSI-only' }
    if (-not (Test-Path -LiteralPath $pythonPath)) { throw "python not found: $pythonPath" }
    $freeKB = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory
    if ($freeKB -lt 153600) { throw "free RAM $freeKB KB is under 150 MB; not running locally" }
    $actual = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $ReviewedManifestSha256.ToLowerInvariant()) { throw 'manifest differs from the reviewed sha256' }
    $expectedLine = "APPROVE lsr_t1, source $($actual.Substring(0,8)), LOCAL_CPU_ONCE on MSI, 300 s cap, no spend."
    if ($OwnerSignLine.Trim() -cne $expectedLine) { throw "sign line mismatch; expected exactly: $expectedLine" }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    foreach ($row in $manifest.files) {
        $h = (Get-FileHash -LiteralPath $row.path -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($h -ne $row.sha256) { throw "source drift: $($row.path)" }
    }
    if (Test-Path -LiteralPath $runDir) { throw 'single-use run folder already exists; a new run needs a new approval and run id' }
    New-Item -ItemType Directory -Path $runDir | Out-Null
    $runDirOwned = $true
    $evidence = (Get-Content -LiteralPath $evidenceTemplate -Raw).Replace('{RUN_ID}', $runId).Replace('{SIGN_LINE}', $OwnerSignLine.Trim()).Replace('{MANIFEST}', $actual).Replace('{LAUNCH_UTC}', $startedUtc.ToString('o'))
    Set-Content -LiteralPath (Join-Path $runDir 'OWNER_APPROVAL_EVIDENCE.md') -Value $evidence -Encoding UTF8
    $remaining = $hardWallSeconds - $timer.Elapsed.TotalSeconds - 2
    if ($remaining -le 10) { throw 'preflight used the time budget' }
    $deadlineEpoch = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() / 1000.0 + $remaining
    Write-JsonFile (Join-Path $runDir 'CLAIM.json') ([ordered]@{status='STARTED'; run_id=$runId; part=$Part; source_manifest_sha256=$actual; start_utc=$startedUtc.ToString('o')})
    $authPath = Join-Path $runDir 'AUTHORIZATION.json'
    Write-JsonFile $authPath ([ordered]@{
        authorized=$true; scope='LSR_T1'; part=$Part; run_id=$runId; environment='LOCAL_CPU_ONCE';
        hostname='MSI'; source_manifest_sha256=$actual; owner_sign_line=$OwnerSignLine.Trim();
        owner_words='Run it locally as long as it Quick if long use aws. / Run both / Yes on parallel prod';
        new_spend=0; network_allowed=$false; cpu_only=$true; max_wall_seconds=$hardWallSeconds;
        deadline_epoch=$deadlineEpoch; created_utc=[DateTimeOffset]::UtcNow.ToString('o')})
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $env:PYTHONNOUSERSITE = '1'
    $env:OMP_NUM_THREADS = '1'
    $env:OPENBLAS_NUM_THREADS = '1'
    $env:MKL_NUM_THREADS = '1'
    $env:CUDA_VISIBLE_DEVICES = '-1'
    $arguments = @('-I', '-B', '-u', "`"$workerPath`"", '--authorization', "`"$authPath`"", '--output', "`"$runDir`"")
    $proc = Start-Process -FilePath $pythonPath -ArgumentList $arguments -WorkingDirectory $projectRoot -NoNewWindow -PassThru `
        -RedirectStandardOutput (Join-Path $runDir 'stdout.log') -RedirectStandardError (Join-Path $runDir 'stderr.log')
    $null = $proc.Handle
    $status = 'RUNNING'
    while (-not $proc.HasExited) {
        if ($timer.Elapsed.TotalSeconds -ge ($hardWallSeconds - 1)) { $status = 'TIMEOUT_KILLED'; break }
        try {
            $proc.Refresh()
            if ($null -eq $peakBytes -or $proc.PeakWorkingSet64 -gt $peakBytes) { $peakBytes = $proc.PeakWorkingSet64 }
            $cpuSeconds = $proc.TotalProcessorTime.TotalSeconds
            if ($peakBytes -gt $memoryCapBytes) { $status = 'MEMORY_CAP_KILLED'; break }
        } catch { }
        Start-Sleep -Milliseconds 200
    }
    if (-not $proc.HasExited) {
        $proc.Kill()
        $null = $proc.WaitForExit(5000)
    } else {
        $proc.WaitForExit()
        $exitCode = $proc.ExitCode
        try { $cpuSeconds = $proc.TotalProcessorTime.TotalSeconds } catch { }
        if ($exitCode -eq 0) { $status = 'COMPLETED' } else { $status = 'WORKER_FAILED' }
    }
} catch {
    $errorText = $_.Exception.Message
    if ($status -eq 'RUNNING' -and $null -ne $proc -and -not $proc.HasExited) { $proc.Kill() }
    $status = 'SUPERVISOR_ERROR'
} finally {
    $end = [ordered]@{
        status=$status; run_id=$runId; part=$Part; start_utc=$startedUtc.ToString('o'); end_utc=[DateTimeOffset]::UtcNow.ToString('o');
        elapsed_wall_seconds=$timer.Elapsed.TotalSeconds; hard_wall_seconds=$hardWallSeconds;
        memory_cap_bytes=$memoryCapBytes; worker_exit_code=$exitCode; worker_cpu_seconds=$cpuSeconds;
        worker_peak_working_set_bytes=$peakBytes; peak_status='PARTIAL_OBSERVED_PEAK_200MS_POLL';
        supervisor_error=$errorText; network='BLOCKED_IN_WORKER'; new_spend=0}
    if ($runDirOwned) {
        Write-JsonFile (Join-Path $runDir 'END.json') $end
        Write-JsonFile (Join-Path $runDir 'CLAIM.json') ([ordered]@{status='CLOSED'; run_id=$runId; end_status=$status})
    }
    $end | ConvertTo-Json -Depth 4
}
