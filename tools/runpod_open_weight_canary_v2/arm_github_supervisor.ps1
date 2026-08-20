[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidatePattern('^[a-z0-9]{6,32}$')][string]$PodId,
    [Parameter(Mandatory)][ValidatePattern('^cas-open-weight-canary-v2-[a-z0-9-]+$')][string]$PodName,
    [Parameter(Mandatory)][datetime]$HardStopDeadlineUtc,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$ProviderStartedAtUtc,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{40}$')][string]$SourceCommit,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$RefName,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$ReceiptDirectory,
    [Parameter()][ValidateNotNullOrEmpty()][string]$Repository = 'LittleHenderson/noetic-compass',
    [Parameter()][ValidateNotNullOrEmpty()][string]$ConfigPath = 'C:\Users\wakil\.runpod\config.toml',
    [Parameter()][switch]$Apply,
    [Parameter()][string]$Confirmation
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Workflow = 'runpod-canary-stop-supervisor.yml'
$SecretName = 'RUNPOD_CANARY_V2_API_KEY'
$ExcludedPodIds = @('q2oqlooejhin7s', 'hilj2rzs54gi06')

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

function Invoke-GhText {
    param([Parameter(Mandatory)][string[]]$Arguments)
    $output = & gh @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) { throw "GH_COMMAND_FAILED: $($Arguments[0])" }
    return ($output -join "`n")
}

if ($ExcludedPodIds -contains $PodId) { throw 'PROTECTED_POD_ID_IS_FORBIDDEN' }
$deadline = $HardStopDeadlineUtc.ToUniversalTime()
try {
    $providerStarted = [DateTimeOffset]::Parse(
        $ProviderStartedAtUtc,
        [Globalization.CultureInfo]::InvariantCulture,
        [Globalization.DateTimeStyles]::AssumeUniversal
    ).UtcDateTime
}
catch {
    throw 'PROVIDER_STARTED_AT_UTC_INVALID'
}
if ($deadline -le $providerStarted -or $deadline -gt $providerStarted.AddSeconds(1800)) {
    throw 'HARD_STOP_DEADLINE_MUST_BE_AFTER_START_AND_AT_MOST_1800_SECONDS'
}
$remaining = ($deadline - (Get-Date).ToUniversalTime()).TotalSeconds
if ($remaining -lt 600 -or $remaining -gt 2100) {
    throw 'HARD_STOP_DEADLINE_MUST_BE_10_TO_35_MINUTES_AHEAD'
}
$receiptRoot = [IO.Path]::GetFullPath($ReceiptDirectory)
if (Test-Path -LiteralPath $receiptRoot) { throw 'RECEIPT_DIRECTORY_MUST_BE_NEW' }

$auth = Invoke-GhText -Arguments @('auth', 'status', '--hostname', 'github.com')
$remoteHead = (Invoke-GhText -Arguments @(
    'api', "repos/$Repository/git/ref/heads/$RefName", '--jq', '.object.sha'
)).Trim()
if ($remoteHead -ne $SourceCommit) { throw 'REMOTE_REF_DOES_NOT_MATCH_SOURCE_COMMIT' }
Invoke-GhText -Arguments @(
    'workflow', 'view', $Workflow, '--repo', $Repository, '--ref', $RefName, '--yaml'
) | Out-Null

if (-not $Apply) {
    [ordered]@{
        status = 'DRY_RUN_PASS_NO_PROVIDER_OR_GITHUB_MUTATION'
        pod_id = $PodId
        pod_name = $PodName
        hard_stop_deadline_utc = $deadline.ToString('o')
        provider_started_at_utc = $ProviderStartedAtUtc
        source_commit = $SourceCommit
        repository = $Repository
        ref_name = $RefName
        github_auth_observed = [bool]$auth
    } | ConvertTo-Json -Compress
    exit 0
}

$expectedConfirmation = "I CONFIRM GITHUB WATCHDOG FOR $PodId"
if ($Confirmation -cne $expectedConfirmation) {
    throw 'EXACT_GITHUB_WATCHDOG_CONFIRMATION_MISSING'
}

[IO.Directory]::CreateDirectory($receiptRoot) | Out-Null
$apiKey = $null
try {
    $apiKey = Read-RunPodApiKey -Path $ConfigPath
    $apiKey | & gh secret set $SecretName --repo $Repository
    if ($LASTEXITCODE -ne 0) { throw 'GITHUB_SECRET_SET_FAILED' }

    $dispatchStarted = (Get-Date).ToUniversalTime()
    Invoke-GhText -Arguments @(
        'workflow', 'run', $Workflow,
        '--repo', $Repository,
        '--ref', $RefName,
        '-f', "pod_id=$PodId",
        '-f', "pod_name=$PodName",
        '-f', "hard_stop_deadline_utc=$($deadline.ToString('o'))",
        '-f', "provider_started_at_utc=$ProviderStartedAtUtc",
        '-f', "source_commit=$SourceCommit"
    ) | Out-Null

    $run = $null
    $runDeadline = (Get-Date).ToUniversalTime().AddMinutes(3)
    do {
        Start-Sleep -Seconds 5
        $rows = Invoke-GhText -Arguments @(
            'run', 'list', '--repo', $Repository,
            '--workflow', $Workflow,
            '--branch', $RefName,
            '--event', 'workflow_dispatch',
            '--limit', '20',
            '--json', 'databaseId,headSha,status,createdAt,url'
        ) | ConvertFrom-Json
        $run = @($rows) | Where-Object {
            $_.headSha -eq $SourceCommit -and
            ([datetime]$_.createdAt).ToUniversalTime() -ge $dispatchStarted.AddMinutes(-1)
        } | Sort-Object { [datetime]$_.createdAt } -Descending | Select-Object -First 1
    } while ($null -eq $run -and (Get-Date).ToUniversalTime() -lt $runDeadline)
    if ($null -eq $run) { throw 'GITHUB_WATCHDOG_RUN_NOT_FOUND' }

    $artifactName = "runpod-stop-supervisor-armed-$PodId"
    $artifactDeadline = (Get-Date).ToUniversalTime().AddMinutes(5)
    $artifact = $null
    do {
        Start-Sleep -Seconds 10
        $artifactPayload = Invoke-GhText -Arguments @(
            'api', "repos/$Repository/actions/runs/$($run.databaseId)/artifacts"
        ) | ConvertFrom-Json
        $artifact = @($artifactPayload.artifacts) | Where-Object {
            $_.name -eq $artifactName -and -not $_.expired
        } | Select-Object -First 1
    } while ($null -eq $artifact -and (Get-Date).ToUniversalTime() -lt $artifactDeadline)
    if ($null -eq $artifact) { throw 'GITHUB_WATCHDOG_ARM_ARTIFACT_NOT_FOUND' }

    Invoke-GhText -Arguments @(
        'run', 'download', [string]$run.databaseId,
        '--repo', $Repository,
        '--name', $artifactName,
        '--dir', $receiptRoot
    ) | Out-Null
    $receiptPath = Join-Path $receiptRoot 'runpod-stop-supervisor-armed.json'
    if (-not (Test-Path -LiteralPath $receiptPath -PathType Leaf)) {
        throw 'GITHUB_WATCHDOG_ARM_RECEIPT_MISSING_AFTER_DOWNLOAD'
    }
    $receiptSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $receiptPath).Hash
    [ordered]@{
        schema_version = 'cas_github_watchdog_arm_handoff.v2'
        status = 'ARM_ARTIFACT_DOWNLOADED'
        github_run_id = [string]$run.databaseId
        github_run_url = [string]$run.url
        source_commit = $SourceCommit
        pod_id = $PodId
        hard_stop_deadline_utc = $deadline.ToString('o')
        provider_started_at_utc = $ProviderStartedAtUtc
        armed_receipt_path = $receiptPath
        armed_receipt_sha256 = $receiptSha
        claim_boundary = 'Local download observation; the runner independently validates the canonical GitHub arm receipt.'
    } | ConvertTo-Json -Compress
    exit 0
}
finally {
    $apiKey = $null
}
