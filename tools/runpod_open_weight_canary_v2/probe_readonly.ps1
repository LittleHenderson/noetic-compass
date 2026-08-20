[CmdletBinding()]
param(
    [Parameter()]
    [ValidateNotNullOrEmpty()]
    [string]$ConfigPath = 'C:\Users\wakil\.runpod\config.toml'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RestBase = 'https://rest.runpod.io/v1'
$ExpectedGraphQlHost = 'api.runpod.io'
$ExpectedGraphQlPath = '/graphql'
$ExcludedPodIds = @(
    'q2oqlooejhin7s',
    'hilj2rzs54gi06'
)

function Read-RunPodConfig {
    param([Parameter(Mandatory)][string]$Path)

    $item = Get-Item -LiteralPath $Path
    if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw 'RUNPOD_CONFIG_MUST_BE_A_PLAIN_FILE'
    }
    $raw = [IO.File]::ReadAllText($item.FullName, [Text.Encoding]::UTF8)
    $keyMatch = [regex]::Match(
        $raw,
        '(?m)^\s*apikey\s*=\s*"(?<value>[^"\r\n]+)"\s*$'
    )
    $urlMatch = [regex]::Match(
        $raw,
        '(?m)^\s*apiurl\s*=\s*"(?<value>[^"\r\n]+)"\s*$'
    )
    if (-not $keyMatch.Success -or -not $urlMatch.Success) {
        throw 'RUNPOD_CONFIG_REQUIRED_KEYS_MISSING'
    }
    $uri = [Uri]$urlMatch.Groups['value'].Value
    if (
        $uri.Scheme -ne 'https' -or
        $uri.Host -ne $ExpectedGraphQlHost -or
        $uri.AbsolutePath -ne $ExpectedGraphQlPath -or
        -not [string]::IsNullOrEmpty($uri.Query)
    ) {
        throw 'RUNPOD_GRAPHQL_URL_NOT_ALLOWLISTED'
    }
    return [pscustomobject]@{
        ApiKey = $keyMatch.Groups['value'].Value
        GraphQlUri = $uri.AbsoluteUri
    }
}

function Invoke-RunPodRestGet {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][hashtable]$Headers
    )
    if (-not $Path.StartsWith('/')) {
        throw 'REST_PATH_MUST_BE_ABSOLUTE'
    }
    return Invoke-RestMethod `
        -Method Get `
        -Uri ($RestBase + $Path) `
        -Headers $Headers `
        -UserAgent 'cas-open-weight-canary-v2-readonly-probe/1.0' `
        -TimeoutSec 20
}

function Get-OptionalProperty {
    param(
        [Parameter()][AllowNull()][object]$InputObject,
        [Parameter(Mandatory)][string]$Name
    )
    if ($null -eq $InputObject) { return $null }
    $property = $InputObject.PSObject.Properties[$Name]
    if ($null -eq $property) { return $null }
    return $property.Value
}

function Expand-JsonArray {
    param([Parameter()][AllowNull()][object]$Value)
    if ($null -eq $Value) { return }
    if ($Value -is [Array]) {
        foreach ($item in $Value) { Expand-JsonArray -Value $item }
        return
    }
    Write-Output $Value
}

$config = $null
$headers = $null
try {
    $config = Read-RunPodConfig -Path $ConfigPath
    $headers = @{ Authorization = 'Bearer ' + $config.ApiKey }

    # These are the only provider operations in this program. They are all
    # authenticated GETs or a named GraphQL query; there are no mutations.
    $podResponse = Invoke-RunPodRestGet `
            -Path '/pods?includeMachine=true&includeNetworkVolume=true' `
            -Headers $headers
    $pods = @(Expand-JsonArray -Value $podResponse)
    $volumeResponse = Invoke-RunPodRestGet -Path '/networkvolumes' -Headers $headers
    $volumes = @(Expand-JsonArray -Value $volumeResponse)

    $graphQlBody = @{
        query = @'
query ReadOnlyAccountState {
  myself {
    clientBalance
    currentSpendPerHr
  }
}
'@
    } | ConvertTo-Json -Compress
    $graph = Invoke-RestMethod `
        -Method Post `
        -Uri $config.GraphQlUri `
        -Headers $headers `
        -ContentType 'application/json' `
        -UserAgent 'cas-open-weight-canary-v2-readonly-probe/1.0' `
        -Body $graphQlBody `
        -TimeoutSec 20
    if ($null -ne (Get-OptionalProperty -InputObject $graph -Name 'errors')) {
        throw 'RUNPOD_ACCOUNT_GRAPHQL_QUERY_RETURNED_ERRORS'
    }

    # GPU discovery is a public read-only GraphQL surface and intentionally
    # receives no account credential.
    $gpuGraphQlBody = @{
        query = @'
query ReadOnlyA40State {
  gpuTypes(input: { id: "NVIDIA A40" }) {
    id
    displayName
    memoryInGb
    secureCloud
    communityCloud
    lowestPrice(input: { gpuCount: 1 }) {
      stockStatus
      uninterruptablePrice
      availableGpuCounts
    }
  }
}
'@
    } | ConvertTo-Json -Compress
    $gpuGraph = Invoke-RestMethod `
        -Method Post `
        -Uri $config.GraphQlUri `
        -ContentType 'application/json' `
        -UserAgent 'cas-open-weight-canary-v2-readonly-probe/1.0' `
        -Body $gpuGraphQlBody `
        -TimeoutSec 20
    if ($null -ne (Get-OptionalProperty -InputObject $gpuGraph -Name 'errors')) {
        throw 'RUNPOD_GPU_GRAPHQL_QUERY_RETURNED_ERRORS'
    }

    $podRows = foreach ($pod in $pods) {
        $gpu = Get-OptionalProperty -InputObject $pod -Name 'gpu'
        $machine = Get-OptionalProperty -InputObject $pod -Name 'machine'
        $networkVolume = Get-OptionalProperty -InputObject $pod -Name 'networkVolume'
        $podId = Get-OptionalProperty -InputObject $pod -Name 'id'
        $image = Get-OptionalProperty -InputObject $pod -Name 'image'
        if ($null -eq $image) {
            # The current REST schema returns imageName. Keep the legacy field
            # fallback so the sanitized observation remains schema-tolerant.
            $image = Get-OptionalProperty -InputObject $pod -Name 'imageName'
        }
        [pscustomobject]@{
            id = $podId
            name = Get-OptionalProperty -InputObject $pod -Name 'name'
            desiredStatus = Get-OptionalProperty -InputObject $pod -Name 'desiredStatus'
            doNotTouch = $ExcludedPodIds -contains $podId
            costPerHr = Get-OptionalProperty -InputObject $pod -Name 'costPerHr'
            adjustedCostPerHr = Get-OptionalProperty -InputObject $pod -Name 'adjustedCostPerHr'
            image = $image
            gpuCount = Get-OptionalProperty -InputObject $pod -Name 'gpuCount'
            gpu = if ($null -eq $gpu) { $null } else {
                [pscustomobject]@{
                    id = Get-OptionalProperty -InputObject $gpu -Name 'id'
                    displayName = Get-OptionalProperty -InputObject $gpu -Name 'displayName'
                    count = Get-OptionalProperty -InputObject $gpu -Name 'count'
                }
            }
            memoryInGb = Get-OptionalProperty -InputObject $pod -Name 'memoryInGb'
            vcpuCount = Get-OptionalProperty -InputObject $pod -Name 'vcpuCount'
            containerDiskInGb = Get-OptionalProperty -InputObject $pod -Name 'containerDiskInGb'
            volumeInGb = Get-OptionalProperty -InputObject $pod -Name 'volumeInGb'
            machine = if ($null -eq $machine) { $null } else {
                [pscustomobject]@{
                    dataCenterId = Get-OptionalProperty -InputObject $machine -Name 'dataCenterId'
                    secureCloud = Get-OptionalProperty -InputObject $machine -Name 'secureCloud'
                }
            }
            networkVolume = if ($null -eq $networkVolume) { $null } else {
                [pscustomobject]@{
                    id = Get-OptionalProperty -InputObject $networkVolume -Name 'id'
                    name = Get-OptionalProperty -InputObject $networkVolume -Name 'name'
                    size = Get-OptionalProperty -InputObject $networkVolume -Name 'size'
                    dataCenterId = Get-OptionalProperty -InputObject $networkVolume -Name 'dataCenterId'
                }
            }
        }
    }

    $volumeRows = foreach ($volume in $volumes) {
        [pscustomobject]@{
            id = Get-OptionalProperty -InputObject $volume -Name 'id'
            name = Get-OptionalProperty -InputObject $volume -Name 'name'
            size = Get-OptionalProperty -InputObject $volume -Name 'size'
            dataCenterId = Get-OptionalProperty -InputObject $volume -Name 'dataCenterId'
        }
    }

    $account = $graph.data.myself
    $a40 = @($gpuGraph.data.gpuTypes)
    $a40DiscoveryStatus = if ($a40.Count -eq 0) {
        'GPU_TYPE_NOT_RETURNED_FAIL_CLOSED'
    }
    elseif ($a40.Count -ne 1) {
        'GPU_TYPE_RESPONSE_AMBIGUOUS_FAIL_CLOSED'
    }
    else {
        $lowestPrice = Get-OptionalProperty -InputObject $a40[0] -Name 'lowestPrice'
        $stockStatus = Get-OptionalProperty -InputObject $lowestPrice -Name 'stockStatus'
        $uninterruptablePrice = Get-OptionalProperty -InputObject $lowestPrice -Name 'uninterruptablePrice'
        if ($null -eq $stockStatus -or $null -eq $uninterruptablePrice) {
            'PRICE_OR_STOCK_UNAVAILABLE_FAIL_CLOSED'
        }
        else {
            'PRICE_AND_STOCK_OBSERVED_RECHECK_REQUIRED'
        }
    }
    $result = [ordered]@{
        schemaVersion = 'cas_runpod_readonly_provider_probe.v1'
        observedAtUtc = (Get-Date).ToUniversalTime().ToString('o')
        status = 'READ_ONLY_PROVIDER_STATE_OBSERVED'
        mutationsAttempted = 0
        account = [ordered]@{
            clientBalance = $account.clientBalance
            currentSpendPerHr = $account.currentSpendPerHr
        }
        podCounts = [ordered]@{
            total = @($podRows).Count
            running = @($podRows | Where-Object desiredStatus -eq 'RUNNING').Count
            exited = @($podRows | Where-Object desiredStatus -eq 'EXITED').Count
            terminated = @($podRows | Where-Object desiredStatus -eq 'TERMINATED').Count
        }
        pods = @($podRows)
        networkVolumes = @($volumeRows)
        requestedGpuType = 'NVIDIA A40'
        gpuDiscoveryStatus = $a40DiscoveryStatus
        gpuAvailability = @($a40)
        exclusions = $ExcludedPodIds
        claimBoundary = 'READ-ONLY PROVIDER OBSERVATION. NO POD OR VOLUME WAS CREATED, STARTED, STOPPED, UPDATED, OR DELETED.'
    }
    $result | ConvertTo-Json -Depth 12
}
catch {
    [ordered]@{
        schemaVersion = 'cas_runpod_readonly_provider_probe.v1'
        observedAtUtc = (Get-Date).ToUniversalTime().ToString('o')
        status = 'READ_ONLY_PROVIDER_PROBE_FAILED_CLOSED'
        mutationsAttempted = 0
        errorType = $_.Exception.GetType().FullName
        errorLine = $_.InvocationInfo.ScriptLineNumber
        claimBoundary = 'NO PROVIDER MUTATION WAS ATTEMPTED. ERROR DETAILS ARE REDACTED TO AVOID CREDENTIAL DISCLOSURE.'
    } | ConvertTo-Json -Depth 4
    exit 1
}
finally {
    if ($null -ne $headers) { $headers.Clear() }
    $headers = $null
    $config = $null
    $graphQlBody = $null
    $gpuGraphQlBody = $null
}
