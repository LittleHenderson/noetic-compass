[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidatePattern('^[a-z0-9]{6,32}$')]
    [string]$PodId,

    [Parameter(Mandatory)]
    [ValidatePattern('^cas-open-weight-canary-v2-[a-z0-9-]+$')]
    [string]$PodName,

    [Parameter(Mandatory)]
    [datetime]$RunCreatedAtUtc,

    [Parameter()]
    [ValidateRange(1, 30)]
    [int]$StopAfterMinutes = 30,

    [Parameter()]
    [switch]$EvidenceExportVerified
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ExcludedPodIds = @(
    'q2oqlooejhin7s',
    'hilj2rzs54gi06'
)

if ($ExcludedPodIds -contains $PodId) {
    throw 'WATCHDOG_TARGET_IS_EXPLICITLY_EXCLUDED'
}
if ($StopAfterMinutes -ne 30) {
    throw 'WATCHDOG_DEADLINE_MUST_REMAIN_EXACTLY_30_MINUTES'
}

$createdUtc = $RunCreatedAtUtc.ToUniversalTime()
$deadlineUtc = $createdUtc.AddMinutes(30)
$encodedPodId = [Uri]::EscapeDataString($PodId)

# Deliberately no config read, credential read, HTTP client, wait loop, POST,
# DELETE, or provider call exists in this file. It emits the exact future state
# machine for review and exits UNARMED.
$plan = [ordered]@{
    schemaVersion = 'cas_runpod_open_weight_canary_watchdog_plan.v1'
    status = 'UNARMED_PLAN_ONLY'
    armed = $false
    providerCallsAttempted = 0
    target = [ordered]@{
        podId = $PodId
        podName = $PodName
        createdAtUtc = $createdUtc.ToString('o')
        stopDeadlineUtc = $deadlineUtc.ToString('o')
        excludedIds = $ExcludedPodIds
    }
    mandatoryArmPreconditions = @(
        'Target pod ID was returned by the future create call for this exact run and was absent from the pre-create inventory.',
        'Target name equals the bound cas-open-weight-canary-v2 run name.',
        'Target image is an exact OCI digest, not a tag.',
        'Target GPU type is NVIDIA A40, count is 1, interruptible is false, and observed price is within the frozen cap.',
        'Target has no network volume because Runpod documents network-volume Pods as terminate-only.',
        'Target has a bounded Pod volume for /workspace so STOP preserves evidence.',
        'The external watchdog process is running before model execution begins.',
        'Neither excluded pod ID can ever pass target validation.'
    )
    futureReadOperations = @(
        [ordered]@{
            method = 'GET'
            uriTemplate = "https://rest.runpod.io/v1/pods/$encodedPodId`?includeMachine=true&includeNetworkVolume=true"
            purpose = 'Revalidate exact ID, name, status, image digest, GPU, rate, and absence of a network volume.'
        }
    )
    futureDeadlineAction = [ordered]@{
        method = 'POST'
        uriTemplate = "https://rest.runpod.io/v1/pods/$encodedPodId/stop"
        requestBody = $null
        executeAtUtc = $deadlineUtc.ToString('o')
        successHttpStatus = 200
        nextState = 'POLL_GET_UNTIL_DESIRED_STATUS_EXITED'
    }
    futureTerminationAction = [ordered]@{
        method = 'DELETE'
        uriTemplate = "https://rest.runpod.io/v1/pods/$encodedPodId"
        requestBody = $null
        successHttpStatus = 204
        allowedNow = [bool]$EvidenceExportVerified
        requiredBeforeDelete = @(
            'Provider reports desiredStatus EXITED.',
            'Off-pod archive byte count and SHA-256 match the pod export sidecar.',
            'Independent bundle verification completed or a retained failure receipt explicitly records why it could not.',
            'A final target identity re-read still matches this exact new pod and neither excluded ID.'
        )
    }
    failClosedRules = @(
        'Any identity mismatch means make no mutation and escalate.',
        'At 30 minutes STOP is attempted even if the experiment is incomplete.',
        'If STOP fails, preserve the error, re-read only, and escalate; never redirect the action to another pod.',
        'If evidence export is not verified, do not DELETE automatically; retain the EXITED pod volume for bounded recovery.',
        'A network volume on the target is a pre-run NO-GO because STOP is not supported for that topology.',
        'No retry may broaden the target from one exact pod ID.'
    )
    claimBoundary = 'THIS FILE IS UNARMED. IT PERFORMS ZERO PROVIDER CALLS AND CANNOT STOP OR DELETE A POD.'
}

$plan | ConvertTo-Json -Depth 10
exit 3
