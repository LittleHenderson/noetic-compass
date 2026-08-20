[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidatePattern('^[a-z0-9]{6,32}$')][string]$PodId,
    [Parameter(Mandatory)][ValidatePattern('^cas-open-weight-canary-v2-[a-z0-9-]+$')][string]$PodName,
    [Parameter(Mandatory)][datetime]$RunCreatedAtUtc,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{40,64}$')][string]$SourceCommitSha256,
    [Parameter(Mandatory)][ValidatePattern('^sha256:[0-9a-f]{64}$')][string]$OciImageDigest,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$ExpectedImageName,
    [Parameter(Mandatory)][ValidateRange(0.01, 0.50)][decimal]$ObservedHourlyRate,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$ReceiptDirectory,
    [Parameter()][ValidateNotNullOrEmpty()][string]$ConfigPath = 'C:\Users\wakil\.runpod\config.toml',
    [Parameter()][switch]$EmergencyStopOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RestBase = 'https://rest.runpod.io/v1'
$ExcludedPodIds = @('q2oqlooejhin7s', 'hilj2rzs54gi06')
$MaximumHourlyRate = [decimal]'0.50'
$MaximumWallSeconds = 1800
$PollSeconds = 15
$ReceiptClaim = 'Self-reported external watchdog receipt; provider stop action and billing settlement require separate verification.'

function Get-OptionalProperty {
    param([AllowNull()][object]$InputObject, [Parameter(Mandatory)][string]$Name)
    if ($null -eq $InputObject) { return $null }
    $property = $InputObject.PSObject.Properties[$Name]
    if ($null -eq $property) { return $null }
    return $property.Value
}

function Read-RunPodApiKey {
    param([Parameter(Mandatory)][string]$Path)
    $item = Get-Item -LiteralPath $Path
    if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw 'RUNPOD_CONFIG_MUST_BE_A_PLAIN_FILE'
    }
    $raw = [IO.File]::ReadAllText($item.FullName, [Text.Encoding]::UTF8)
    $match = [regex]::Match($raw, '(?m)^\s*apikey\s*=\s*"(?<value>[^"\r\n]+)"\s*$')
    if (-not $match.Success) { throw 'RUNPOD_API_KEY_MISSING' }
    return $match.Groups['value'].Value
}

function Write-CreateNewUtf8Json {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][object]$Value
    )
    $json = $Value | ConvertTo-Json -Depth 12 -Compress
    $bytes = [Text.UTF8Encoding]::new($false).GetBytes($json + "`n")
    $stream = [IO.FileStream]::new(
        $Path,
        [IO.FileMode]::CreateNew,
        [IO.FileAccess]::Write,
        [IO.FileShare]::None
    )
    try {
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Flush($true)
    }
    finally {
        $stream.Dispose()
    }
}

function Add-Event {
    param([Parameter(Mandatory)][string]$Name, [Parameter()][object]$Details)
    $row = [ordered]@{
        observed_at_utc = (Get-Date).ToUniversalTime().ToString('o')
        event = $Name
        details = $Details
    }
    $json = ($row | ConvertTo-Json -Depth 10 -Compress) + "`n"
    [IO.File]::AppendAllText($script:EventPath, $json, [Text.UTF8Encoding]::new($false))
}

function Invoke-PodGet {
    $escaped = [Uri]::EscapeDataString($PodId)
    return Invoke-RestMethod -Method Get `
        -Uri "$RestBase/pods/$escaped`?includeMachine=true&includeNetworkVolume=true" `
        -Headers $script:Headers `
        -UserAgent 'cas-open-weight-canary-v2-watchdog/1.0' `
        -TimeoutSec 20
}

function Invoke-PodStop {
    $escaped = [Uri]::EscapeDataString($PodId)
    $response = Invoke-WebRequest -UseBasicParsing -Method Post `
        -Uri "$RestBase/pods/$escaped/stop" `
        -Headers $script:Headers `
        -UserAgent 'cas-open-weight-canary-v2-watchdog/1.0' `
        -TimeoutSec 20
    if ([int]$response.StatusCode -ne 200) { throw 'WATCHDOG_STOP_HTTP_STATUS_MISMATCH' }
    return [int]$response.StatusCode
}

function Wait-ForExited {
    param([Parameter(Mandatory)][datetime]$DeadlineUtc)
    do {
        Start-Sleep -Seconds $PollSeconds
        $observed = Assert-ExactTarget (Invoke-PodGet)
        Add-Event -Name 'POST_STOP_STATUS' -Details $observed.desired_status
        if ($observed.desired_status -eq 'EXITED') { return $observed }
    } while ((Get-Date).ToUniversalTime() -lt $DeadlineUtc)
    throw 'WATCHDOG_STOP_DID_NOT_REACH_EXITED'
}

function Assert-ExactTarget {
    param([Parameter(Mandatory)][object]$Pod)
    $id = Get-OptionalProperty $Pod 'id'
    $name = Get-OptionalProperty $Pod 'name'
    $image = Get-OptionalProperty $Pod 'image'
    if ($null -eq $image) { $image = Get-OptionalProperty $Pod 'imageName' }
    $gpuCount = Get-OptionalProperty $Pod 'gpuCount'
    $gpu = Get-OptionalProperty $Pod 'gpu'
    $gpuId = Get-OptionalProperty $gpu 'id'
    $gpuDisplay = Get-OptionalProperty $gpu 'displayName'
    $networkVolume = Get-OptionalProperty $Pod 'networkVolume'
    $podVolumeInGb = Get-OptionalProperty $Pod 'volumeInGb'
    $cost = Get-OptionalProperty $Pod 'costPerHr'
    if ($null -eq $cost) { $cost = Get-OptionalProperty $Pod 'adjustedCostPerHr' }
    if ($id -ne $PodId -or $name -ne $PodName) { throw 'WATCHDOG_TARGET_IDENTITY_MISMATCH' }
    if ($ExcludedPodIds -contains $id) { throw 'WATCHDOG_TARGET_IS_EXPLICITLY_EXCLUDED' }
    if ($image -ne $ExpectedImageName) { throw 'WATCHDOG_TARGET_IMAGE_NAME_MISMATCH' }
    if ([int]$gpuCount -ne 1) { throw 'WATCHDOG_TARGET_GPU_COUNT_MISMATCH' }
    if ($gpuId -ne 'NVIDIA A40' -and $gpuDisplay -ne 'NVIDIA A40') {
        throw 'WATCHDOG_TARGET_GPU_TYPE_MISMATCH'
    }
    if ($null -ne $networkVolume) { throw 'WATCHDOG_TARGET_HAS_FORBIDDEN_NETWORK_VOLUME' }
    if ($null -eq $podVolumeInGb -or [int]$podVolumeInGb -le 0) {
        throw 'WATCHDOG_TARGET_HAS_NO_POSITIVE_POD_VOLUME'
    }
    if ($null -eq $cost -or [decimal]$cost -gt $MaximumHourlyRate) {
        throw 'WATCHDOG_TARGET_RATE_EXCEEDS_CEILING'
    }
    if ($ObservedHourlyRate -gt $MaximumHourlyRate) {
        throw 'WATCHDOG_CREATE_RATE_EXCEEDS_CEILING'
    }
    return [ordered]@{
        id = $id
        name = $name
        desired_status = Get-OptionalProperty $Pod 'desiredStatus'
        image = $image
        gpu_count = [int]$gpuCount
        gpu_id = $gpuId
        gpu_display_name = $gpuDisplay
        cost_per_hour = [decimal]$cost
        network_volume_absent = $true
        pod_volume_gb = [int]$podVolumeInGb
    }
}

if ($ExcludedPodIds -contains $PodId) { throw 'WATCHDOG_TARGET_IS_EXPLICITLY_EXCLUDED' }
$createdUtc = $RunCreatedAtUtc.ToUniversalTime()
$nowUtc = (Get-Date).ToUniversalTime()
$deadlineUtc = $createdUtc.AddSeconds($MaximumWallSeconds)
$receiptRoot = [IO.Path]::GetFullPath($ReceiptDirectory)
$script:EventPath = Join-Path $receiptRoot 'watchdog.events.jsonl'
$armedReceiptPath = Join-Path $receiptRoot 'external-watchdog.receipt.json'
$terminalReceiptPath = Join-Path $receiptRoot 'watchdog.terminal.json'
$emergencyTerminalPath = Join-Path $receiptRoot 'watchdog.emergency.terminal.json'

if ($EmergencyStopOnly) {
    if (-not (Test-Path -LiteralPath $receiptRoot -PathType Container)) {
        throw 'WATCHDOG_EMERGENCY_RECEIPT_DIRECTORY_MISSING'
    }
    $apiKey = $null
    $script:Headers = $null
    try {
        $apiKey = Read-RunPodApiKey -Path $ConfigPath
        $script:Headers = @{ Authorization = 'Bearer ' + $apiKey }
        $target = Assert-ExactTarget (Invoke-PodGet)
        if ($target.desired_status -eq 'RUNNING') {
            $status = Invoke-PodStop
            Add-Event -Name 'EMERGENCY_STOP_ACCEPTED_HTTP_200' -Details $target
            $target = Wait-ForExited -DeadlineUtc ((Get-Date).ToUniversalTime().AddMinutes(10))
            $terminalStatus = 'EMERGENCY_STOPPED_AT_DEADLINE_EXITED_CONFIRMED'
        }
        elseif ($target.desired_status -eq 'EXITED') {
            $status = $null
            $terminalStatus = 'EMERGENCY_OBSERVED_ALREADY_EXITED'
        }
        else {
            throw 'WATCHDOG_EMERGENCY_TARGET_STATE_UNEXPECTED'
        }
        if (-not (Test-Path -LiteralPath $emergencyTerminalPath)) {
            Write-CreateNewUtf8Json -Path $emergencyTerminalPath -Value ([ordered]@{
                schema_version = 'cas_runpod_watchdog_emergency_terminal.v1'
                status = $terminalStatus
                pod_id = $PodId
                observed_at_utc = (Get-Date).ToUniversalTime().ToString('o')
                stop_http_status = $status
                delete_attempted = $false
            })
        }
        exit 0
    }
    catch {
        Add-Event -Name 'EMERGENCY_STOP_FAILED_CLOSED' -Details ([ordered]@{
            error_type = $_.Exception.GetType().FullName
            error_line = $_.InvocationInfo.ScriptLineNumber
        })
        exit 2
    }
    finally {
        if ($null -ne $script:Headers) { $script:Headers.Clear() }
        $script:Headers = $null
        $apiKey = $null
    }
}

if ($createdUtc -gt $nowUtc.AddMinutes(2) -or $createdUtc -lt $nowUtc.AddMinutes(-5)) {
    throw 'WATCHDOG_CREATE_TIME_OUTSIDE_ARM_WINDOW'
}
if ($deadlineUtc -le $nowUtc.AddMinutes(10)) { throw 'WATCHDOG_DEADLINE_TOO_NEAR' }
if (Test-Path -LiteralPath $receiptRoot) { throw 'WATCHDOG_RECEIPT_DIRECTORY_MUST_BE_NEW' }
[IO.Directory]::CreateDirectory($receiptRoot) | Out-Null

$apiKey = $null
$script:Headers = $null
try {
    $apiKey = Read-RunPodApiKey -Path $ConfigPath
    $script:Headers = @{ Authorization = 'Bearer ' + $apiKey }
    $initialPod = Invoke-PodGet
    $target = Assert-ExactTarget $initialPod
    if ($target.desired_status -ne 'RUNNING') { throw 'WATCHDOG_TARGET_NOT_RUNNING_AT_ARM' }

    $taskName = "CAS-OpenWeight-Canary-Stop-$PodId"
    if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
        throw 'WATCHDOG_FALLBACK_TASK_ALREADY_EXISTS'
    }
    foreach ($value in @($PSCommandPath, $ReceiptDirectory, $ConfigPath, $ExpectedImageName)) {
        if ($value.Contains('"')) { throw 'WATCHDOG_TASK_ARGUMENT_CONTAINS_QUOTE' }
    }
    $powerShellPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
    $taskArguments = @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $PSCommandPath + '"'),
        '-EmergencyStopOnly', '-PodId', $PodId, '-PodName', $PodName,
        '-RunCreatedAtUtc', ('"' + $createdUtc.ToString('o') + '"'),
        '-SourceCommitSha256', $SourceCommitSha256,
        '-OciImageDigest', $OciImageDigest,
        '-ExpectedImageName', $ExpectedImageName,
        '-ObservedHourlyRate', $ObservedHourlyRate.ToString([Globalization.CultureInfo]::InvariantCulture),
        '-ReceiptDirectory', ('"' + $receiptRoot + '"'),
        '-ConfigPath', ('"' + ([IO.Path]::GetFullPath($ConfigPath)) + '"')
    ) -join ' '
    $taskAction = New-ScheduledTaskAction -Execute $powerShellPath -Argument $taskArguments
    $taskTrigger = New-ScheduledTaskTrigger -Once -At $deadlineUtc.ToLocalTime()
    $taskSettings = New-ScheduledTaskSettingsSet `
        -StartWhenAvailable `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 15)
    $taskPrincipal = New-ScheduledTaskPrincipal `
        -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) `
        -LogonType Interactive `
        -RunLevel Limited
    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $taskAction `
        -Trigger $taskTrigger `
        -Settings $taskSettings `
        -Principal $taskPrincipal | Out-Null
    $registeredTask = Get-ScheduledTask -TaskName $taskName
    if ($registeredTask.TaskName -ne $taskName -or @($registeredTask.Triggers).Count -ne 1) {
        throw 'WATCHDOG_FALLBACK_TASK_REVALIDATION_FAILED'
    }
    $watchdogScriptSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $PSCommandPath).Hash

    # Alphabetical key insertion order is required to match the runner's
    # Python sort_keys=True canonical JSON encoding byte-for-byte.
    $armedReceipt = [ordered]@{
        claim_boundary = $ReceiptClaim
        emergency_fallback_status = 'REGISTERED_AND_REVALIDATED'
        emergency_task_name = $taskName
        hard_stop_deadline_utc = $deadlineUtc.ToString('o')
        maximum_spend_usd = '0.50'
        maximum_wall_seconds = $MaximumWallSeconds
        oci_image_digest = $OciImageDigest
        provider = 'RUNPOD'
        schema_version = 'cas_external_stop_watchdog_receipt.v1'
        source_commit_sha256 = $SourceCommitSha256
        status = 'ARMED'
        watchdog_script_sha256 = $watchdogScriptSha256
        workload_id = $PodId
    }
    Write-CreateNewUtf8Json -Path $armedReceiptPath -Value $armedReceipt
    Add-Event -Name 'WATCHDOG_ARMED' -Details $target

    while ((Get-Date).ToUniversalTime() -lt $deadlineUtc) {
        Start-Sleep -Seconds $PollSeconds
        $observed = Assert-ExactTarget (Invoke-PodGet)
        if ($observed.desired_status -eq 'EXITED') {
            Add-Event -Name 'TARGET_EXITED_BEFORE_DEADLINE' -Details $observed
            Write-CreateNewUtf8Json -Path $terminalReceiptPath -Value ([ordered]@{
                schema_version = 'cas_runpod_watchdog_terminal.v1'
                status = 'EXITED_BEFORE_DEADLINE_NO_STOP_REQUIRED'
                pod_id = $PodId
                observed_at_utc = (Get-Date).ToUniversalTime().ToString('o')
                delete_attempted = $false
            })
            exit 0
        }
        if ($observed.desired_status -ne 'RUNNING') {
            throw 'WATCHDOG_TARGET_ENTERED_UNEXPECTED_STATE'
        }
    }

    $finalTarget = Assert-ExactTarget (Invoke-PodGet)
    $stopHttpStatus = Invoke-PodStop
    Add-Event -Name 'STOP_ACCEPTED_HTTP_200' -Details $finalTarget

    $observed = Wait-ForExited -DeadlineUtc ((Get-Date).ToUniversalTime().AddMinutes(10))

    Write-CreateNewUtf8Json -Path $terminalReceiptPath -Value ([ordered]@{
        schema_version = 'cas_runpod_watchdog_terminal.v1'
        status = 'STOPPED_AT_DEADLINE_EXITED_CONFIRMED'
        pod_id = $PodId
        stopped_at_utc = (Get-Date).ToUniversalTime().ToString('o')
        stop_http_status = $stopHttpStatus
        delete_attempted = $false
        evidence_export_required_before_delete = $true
    })
    exit 0
}
catch {
    $failStopStatus = 'NOT_ATTEMPTED_NO_PROVIDER_SESSION'
    if ($null -ne $script:Headers) {
        try {
            $failTarget = Assert-ExactTarget (Invoke-PodGet)
            if ($failTarget.desired_status -eq 'RUNNING') {
                [void](Invoke-PodStop)
                $failStopStatus = 'STOP_ACCEPTED_AFTER_WATCHDOG_FAILURE'
            }
            elseif ($failTarget.desired_status -eq 'EXITED') {
                $failStopStatus = 'ALREADY_EXITED_AFTER_WATCHDOG_FAILURE'
            }
            else {
                $failStopStatus = 'UNEXPECTED_STATE_OPERATOR_INTERVENTION_REQUIRED'
            }
        }
        catch {
            $failStopStatus = 'FAIL_STOP_ATTEMPT_FAILED_OPERATOR_INTERVENTION_REQUIRED'
        }
    }
    Add-Event -Name 'WATCHDOG_FAILED_CLOSED' -Details ([ordered]@{
        error_type = $_.Exception.GetType().FullName
        error_line = $_.InvocationInfo.ScriptLineNumber
        fail_stop_status = $failStopStatus
    })
    if (-not (Test-Path -LiteralPath $terminalReceiptPath)) {
        Write-CreateNewUtf8Json -Path $terminalReceiptPath -Value ([ordered]@{
            schema_version = 'cas_runpod_watchdog_terminal.v1'
            status = 'WATCHDOG_FAILED_CLOSED_OPERATOR_INTERVENTION_REQUIRED'
            pod_id = $PodId
            observed_at_utc = (Get-Date).ToUniversalTime().ToString('o')
            delete_attempted = $false
        })
    }
    exit 1
}
finally {
    if ($null -ne $script:Headers) { $script:Headers.Clear() }
    $script:Headers = $null
    $apiKey = $null
}
