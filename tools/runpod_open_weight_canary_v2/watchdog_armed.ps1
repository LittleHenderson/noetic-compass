[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidatePattern('^[a-z0-9]{6,32}$')][string]$PodId,
    [Parameter(Mandatory)][ValidatePattern('^cas-open-weight-canary-v2-[a-z0-9-]+$')][string]$PodName,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$RunStartedAtUtc,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$HardStopDeadlineUtc,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{40,64}$')][string]$SourceCommitSha256,
    [Parameter(Mandatory)][ValidatePattern('^sha256:[0-9a-f]{64}$')][string]$OciImageDigest,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$ExpectedImageName,
    [Parameter(Mandatory)][ValidateRange(0.01, 0.50)][decimal]$ObservedHourlyRate,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$ReceiptDirectory,
    [Parameter()][ValidateNotNullOrEmpty()][string]$ProviderLaunchReceiptPath,
    [Parameter()][ValidatePattern('^[0-9A-F]{64}$')][string]$ProviderLaunchReceiptSha256,
    [Parameter()][ValidateNotNullOrEmpty()][string]$ConfigPath = 'C:\Users\wakil\.runpod\config.toml',
    [Parameter()][ValidateNotNullOrEmpty()][string]$ExpectedPublicKeyPath = 'C:\Users\wakil\.ssh\runpod_cas.pub',
    [Parameter()][switch]$ValidateProviderLaunchReceiptOnly,
    [Parameter()][switch]$EmergencyStopOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RestBase = 'https://rest.runpod.io/v1'
$ExcludedPodIds = @('q2oqlooejhin7s', 'hilj2rzs54gi06')
$MaximumHourlyRate = [decimal]'0.50'
$MaximumWallSeconds = 1800
$PollSeconds = 15
$LocalStopLeadSeconds = 90
$ReceiptClaim = 'Self-reported external watchdog receipt; provider stop action and billing settlement require separate verification.'

function Get-OptionalProperty {
    param([AllowNull()][object]$InputObject, [Parameter(Mandatory)][string]$Name)
    if ($null -eq $InputObject) { return $null }
    $property = $InputObject.PSObject.Properties[$Name]
    if ($null -eq $property) { return $null }
    # Preserve a JSON array as one pipeline object; PowerShell otherwise
    # enumerates a one-element array into a scalar at the function boundary.
    return ,$property.Value
}

function Test-IsJsonInteger {
    param([AllowNull()][object]$Value)
    return $Value -is [sbyte] -or $Value -is [byte] -or
        $Value -is [int16] -or $Value -is [uint16] -or
        $Value -is [int32] -or $Value -is [uint32] -or
        $Value -is [int64] -or $Value -is [uint64]
}

function Test-IsJsonNumber {
    param([AllowNull()][object]$Value)
    return (Test-IsJsonInteger $Value) -or $Value -is [single] -or
        $Value -is [double] -or $Value -is [decimal]
}

function Get-Utf8Sha256Hex {
    param([Parameter(Mandatory)][string]$Value)
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try {
        $digest = $algorithm.ComputeHash([Text.UTF8Encoding]::new($false).GetBytes($Value))
        return ([BitConverter]::ToString($digest)).Replace('-', '')
    }
    finally {
        $algorithm.Dispose()
    }
}

function Get-ByteSha256Hex {
    param([Parameter(Mandatory)][byte[]]$Value)
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try {
        $digest = $algorithm.ComputeHash($Value)
        return ([BitConverter]::ToString($digest)).Replace('-', '')
    }
    finally {
        $algorithm.Dispose()
    }
}

function Get-CanonicalJsonBytes {
    param([Parameter(Mandatory)][object]$Value)
    $json = (ConvertTo-CanonicalJsonValue $Value) | ConvertTo-Json -Depth 20 -Compress
    return [Text.UTF8Encoding]::new($false).GetBytes($json + "`n")
}

function ConvertTo-CanonicalJsonValue {
    param([AllowNull()][object]$Value)
    if ($null -eq $Value) { return $null }
    if ($Value -is [Collections.IDictionary]) {
        $result = [ordered]@{}
        foreach ($key in @($Value.Keys | ForEach-Object { [string]$_ } | Sort-Object)) {
            $result[$key] = ConvertTo-CanonicalJsonValue $Value[$key]
        }
        return $result
    }
    if ($Value -is [pscustomobject]) {
        $result = [ordered]@{}
        foreach ($property in @($Value.PSObject.Properties | Sort-Object Name)) {
            $result[$property.Name] = ConvertTo-CanonicalJsonValue $property.Value
        }
        return $result
    }
    if ($Value -is [Collections.IEnumerable] -and $Value -isnot [string]) {
        $items = @()
        foreach ($item in $Value) { $items += ,(ConvertTo-CanonicalJsonValue $item) }
        return ,$items
    }
    return $Value
}

function Skip-StrictJsonWhitespace {
    param([Parameter(Mandatory)][hashtable]$State)
    while ($State.Index -lt $State.Text.Length -and
        " `t`r`n".IndexOf([char]$State.Text[$State.Index]) -ge 0) {
        $State.Index++
    }
}

function Read-StrictJsonStringToken {
    param([Parameter(Mandatory)][hashtable]$State)
    if ($State.Index -ge $State.Text.Length -or $State.Text[$State.Index] -cne '"') {
        throw 'WATCHDOG_PROVIDER_LAUNCH_RESPONSE_RAW_JSON_INVALID'
    }
    $State.Index++
    $builder = [Text.StringBuilder]::new()
    while ($State.Index -lt $State.Text.Length) {
        $character = [char]$State.Text[$State.Index]
        $State.Index++
        if ($character -ceq '"') { return $builder.ToString() }
        if ([int]$character -lt 0x20) {
            throw 'WATCHDOG_PROVIDER_LAUNCH_RESPONSE_RAW_JSON_INVALID'
        }
        if ($character -cne '\') {
            [void]$builder.Append($character)
            continue
        }
        if ($State.Index -ge $State.Text.Length) {
            throw 'WATCHDOG_PROVIDER_LAUNCH_RESPONSE_RAW_JSON_INVALID'
        }
        $escape = [char]$State.Text[$State.Index]
        $State.Index++
        switch -CaseSensitive ($escape) {
            '"' { [void]$builder.Append('"') }
            '\' { [void]$builder.Append('\') }
            '/' { [void]$builder.Append('/') }
            'b' { [void]$builder.Append([char]8) }
            'f' { [void]$builder.Append([char]12) }
            'n' { [void]$builder.Append([char]10) }
            'r' { [void]$builder.Append([char]13) }
            't' { [void]$builder.Append([char]9) }
            'u' {
                if ($State.Index + 4 -gt $State.Text.Length) {
                    throw 'WATCHDOG_PROVIDER_LAUNCH_RESPONSE_RAW_JSON_INVALID'
                }
                $hex = $State.Text.Substring($State.Index, 4)
                if ($hex -cnotmatch '^[0-9A-Fa-f]{4}$') {
                    throw 'WATCHDOG_PROVIDER_LAUNCH_RESPONSE_RAW_JSON_INVALID'
                }
                [void]$builder.Append([char][Convert]::ToInt32($hex, 16))
                $State.Index += 4
            }
            default { throw 'WATCHDOG_PROVIDER_LAUNCH_RESPONSE_RAW_JSON_INVALID' }
        }
    }
    throw 'WATCHDOG_PROVIDER_LAUNCH_RESPONSE_RAW_JSON_INVALID'
}

function Read-StrictJsonNumberToken {
    param([Parameter(Mandatory)][hashtable]$State)
    $remaining = $State.Text.Substring($State.Index)
    $match = [regex]::Match($remaining, '^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?')
    if (-not $match.Success) {
        throw 'WATCHDOG_PROVIDER_LAUNCH_RESPONSE_RAW_JSON_INVALID'
    }
    $State.Index += $match.Length
}

function Read-StrictJsonValueToken {
    param(
        [Parameter(Mandatory)][hashtable]$State,
        [Parameter(Mandatory)][int]$Depth
    )
    if ($Depth -gt 64) { throw 'WATCHDOG_PROVIDER_LAUNCH_RESPONSE_RAW_JSON_INVALID' }
    Skip-StrictJsonWhitespace $State
    if ($State.Index -ge $State.Text.Length) {
        throw 'WATCHDOG_PROVIDER_LAUNCH_RESPONSE_RAW_JSON_INVALID'
    }
    $character = [char]$State.Text[$State.Index]
    if ($character -ceq '"') {
        $null = Read-StrictJsonStringToken $State
        return
    }
    if ($character -ceq '{') {
        $State.Index++
        $keys = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        Skip-StrictJsonWhitespace $State
        if ($State.Index -lt $State.Text.Length -and $State.Text[$State.Index] -ceq '}') {
            $State.Index++
            return
        }
        while ($true) {
            Skip-StrictJsonWhitespace $State
            $key = Read-StrictJsonStringToken $State
            if (-not $keys.Add($key)) {
                throw 'WATCHDOG_PROVIDER_LAUNCH_RESPONSE_RAW_DUPLICATE_KEY'
            }
            Skip-StrictJsonWhitespace $State
            if ($State.Index -ge $State.Text.Length -or $State.Text[$State.Index] -cne ':') {
                throw 'WATCHDOG_PROVIDER_LAUNCH_RESPONSE_RAW_JSON_INVALID'
            }
            $State.Index++
            Read-StrictJsonValueToken -State $State -Depth ($Depth + 1)
            Skip-StrictJsonWhitespace $State
            if ($State.Index -ge $State.Text.Length) {
                throw 'WATCHDOG_PROVIDER_LAUNCH_RESPONSE_RAW_JSON_INVALID'
            }
            $separator = [char]$State.Text[$State.Index]
            $State.Index++
            if ($separator -ceq '}') { return }
            if ($separator -cne ',') {
                throw 'WATCHDOG_PROVIDER_LAUNCH_RESPONSE_RAW_JSON_INVALID'
            }
        }
    }
    if ($character -ceq '[') {
        $State.Index++
        Skip-StrictJsonWhitespace $State
        if ($State.Index -lt $State.Text.Length -and $State.Text[$State.Index] -ceq ']') {
            $State.Index++
            return
        }
        while ($true) {
            Read-StrictJsonValueToken -State $State -Depth ($Depth + 1)
            Skip-StrictJsonWhitespace $State
            if ($State.Index -ge $State.Text.Length) {
                throw 'WATCHDOG_PROVIDER_LAUNCH_RESPONSE_RAW_JSON_INVALID'
            }
            $separator = [char]$State.Text[$State.Index]
            $State.Index++
            if ($separator -ceq ']') { return }
            if ($separator -cne ',') {
                throw 'WATCHDOG_PROVIDER_LAUNCH_RESPONSE_RAW_JSON_INVALID'
            }
        }
    }
    foreach ($literal in @('true', 'false', 'null')) {
        if ($State.Text.Substring($State.Index).StartsWith(
            $literal, [StringComparison]::Ordinal
        )) {
            $State.Index += $literal.Length
            return
        }
    }
    Read-StrictJsonNumberToken $State
}

function Assert-StrictJsonText {
    param([Parameter(Mandatory)][string]$Text)
    $state = @{ Text = $Text; Index = 0 }
    Read-StrictJsonValueToken -State $state -Depth 0
    Skip-StrictJsonWhitespace $state
    if ($state.Index -ne $state.Text.Length) {
        throw 'WATCHDOG_PROVIDER_LAUNCH_RESPONSE_RAW_JSON_INVALID'
    }
}

function ConvertFrom-JsonPreserveStrings {
    param([Parameter(Mandatory)][string]$Text)
    $command = Get-Command ConvertFrom-Json -CommandType Cmdlet
    if ($command.Parameters.ContainsKey('DateKind')) {
        # PowerShell 7.5 otherwise coerces ISO strings to DateTime and changes
        # their lexical form on reserialization, breaking exact canonical bytes.
        return ,($Text | ConvertFrom-Json -DateKind String)
    }
    return ,($Text | ConvertFrom-Json)
}

function Assert-ExactPropertyKeyset {
    param(
        [Parameter(Mandatory)][object]$Value,
        [Parameter(Mandatory)][string[]]$Expected,
        [Parameter(Mandatory)][string]$ErrorCode
    )
    $observed = @($Value.PSObject.Properties | ForEach-Object { $_.Name } | Sort-Object)
    $wanted = @($Expected | Sort-Object)
    if ($observed.Count -ne $wanted.Count -or
        (($observed -join "`n") -cne ($wanted -join "`n"))) {
        throw $ErrorCode
    }
}

function Get-RequiredProperty {
    param([Parameter(Mandatory)][object]$Value, [Parameter(Mandatory)][string]$Name)
    $property = $Value.PSObject.Properties[$Name]
    if ($null -eq $property) { throw "WATCHDOG_PROVIDER_LAUNCH_REQUIRED_FIELD_MISSING_$Name" }
    # Preserve a JSON array as one pipeline object; PowerShell otherwise
    # enumerates a one-element array into a scalar at the function boundary.
    return ,$property.Value
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

function Read-ExpectedPublicKey {
    param([Parameter(Mandatory)][string]$Path)
    $item = Get-Item -LiteralPath $Path
    if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw 'WATCHDOG_PUBLIC_KEY_MUST_BE_A_PLAIN_FILE'
    }
    if ($item.Length -gt 16384) { throw 'WATCHDOG_PUBLIC_KEY_FILE_TOO_LARGE' }
    $raw = [IO.File]::ReadAllText($item.FullName, [Text.Encoding]::UTF8)
    $value = $raw -replace '(?:\r\n|\n|\r)$', ''
    if ($value.Contains("`r") -or $value.Contains("`n")) {
        throw 'WATCHDOG_PUBLIC_KEY_MUST_BE_ONE_LINE'
    }
    if ($value -notmatch '^ssh-ed25519 [A-Za-z0-9+/]+={0,2}(?: [^\r\n]+)?$') {
        throw 'WATCHDOG_PUBLIC_KEY_FORMAT_INVALID'
    }
    return $value
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

function Convert-ProviderUtcTimestamp {
    param([Parameter(Mandatory)][string]$Value)
    $legacy = [regex]::Match(
        $Value,
        '^(?<date>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) (?<offset>[+-]\d{4}) UTC$'
    )
    if ($legacy.Success) {
        $offset = $legacy.Groups['offset'].Value
        $normalized = $legacy.Groups['date'].Value + ' ' +
            $offset.Substring(0, 3) + ':' + $offset.Substring(3, 2)
        return [DateTimeOffset]::ParseExact(
            $normalized,
            'yyyy-MM-dd HH:mm:ss.fff zzz',
            [Globalization.CultureInfo]::InvariantCulture
        ).UtcDateTime
    }
    try {
        return [DateTimeOffset]::Parse(
            $Value,
            [Globalization.CultureInfo]::InvariantCulture,
            [Globalization.DateTimeStyles]::AssumeUniversal
        ).UtcDateTime
    }
    catch {
        throw 'WATCHDOG_PROVIDER_START_TIME_INVALID'
    }
}

function Assert-ProviderTransaction {
    param(
        [Parameter(Mandatory)][object]$Value,
        [Parameter(Mandatory)][string]$Label,
        [Parameter(Mandatory)][string]$ExpectedPath,
        [Parameter(Mandatory)][int[]]$AcceptedHttpStatuses
    )
    Assert-ExactPropertyKeyset -Value $Value -Expected @(
        'effective_url',
        'elapsed_milliseconds',
        'request_body',
        'request_body_base64',
        'request_body_byte_count',
        'request_body_sha256',
        'request_accept_encoding',
        'request_content_type',
        'request_method',
        'request_observed_at_utc',
        'request_path',
        'response_body',
        'response_body_base64',
        'response_body_byte_count',
        'response_body_sha256',
        'response_content_encoding',
        'response_content_type',
        'response_http_status',
        'response_observed_at_utc',
        'response_request_id'
    ) -ErrorCode "WATCHDOG_PROVIDER_LAUNCH_${Label}_TRANSACTION_KEYSET_MISMATCH"
    if ((Get-RequiredProperty $Value 'request_method') -cne 'POST') {
        throw "WATCHDOG_PROVIDER_LAUNCH_${Label}_METHOD_MISMATCH"
    }
    if ((Get-RequiredProperty $Value 'request_path') -cne $ExpectedPath) {
        throw "WATCHDOG_PROVIDER_LAUNCH_${Label}_PATH_MISMATCH"
    }
    if ((Get-RequiredProperty $Value 'effective_url') -cne "https://rest.runpod.io$ExpectedPath" -or
        (Get-RequiredProperty $Value 'request_accept_encoding') -cne 'identity' -or
        (Get-RequiredProperty $Value 'request_content_type') -cne 'application/json') {
        throw "WATCHDOG_PROVIDER_LAUNCH_${Label}_HTTP_BINDING_MISMATCH"
    }
    $requestBody = Get-RequiredProperty $Value 'request_body'
    $responseBody = Get-RequiredProperty $Value 'response_body'
    if ($null -eq $requestBody -or $null -eq $responseBody) {
        throw "WATCHDOG_PROVIDER_LAUNCH_${Label}_BODY_MISSING"
    }
    try {
        $requestRaw = [Convert]::FromBase64String(
            [string](Get-RequiredProperty $Value 'request_body_base64')
        )
        $responseRaw = [Convert]::FromBase64String(
            [string](Get-RequiredProperty $Value 'response_body_base64')
        )
    }
    catch {
        throw "WATCHDOG_PROVIDER_LAUNCH_${Label}_RAW_BASE64_INVALID"
    }
    if ([Convert]::ToBase64String($requestRaw) -cne
            [string](Get-RequiredProperty $Value 'request_body_base64') -or
        [Convert]::ToBase64String($responseRaw) -cne
            [string](Get-RequiredProperty $Value 'response_body_base64')) {
        throw "WATCHDOG_PROVIDER_LAUNCH_${Label}_RAW_BASE64_NONCANONICAL"
    }
    if (-not (Test-IsJsonInteger (Get-RequiredProperty $Value 'request_body_byte_count')) -or
        [int64](Get-RequiredProperty $Value 'request_body_byte_count') -ne $requestRaw.Length -or
        -not (Test-IsJsonInteger (Get-RequiredProperty $Value 'response_body_byte_count')) -or
        [int64](Get-RequiredProperty $Value 'response_body_byte_count') -ne $responseRaw.Length) {
        throw "WATCHDOG_PROVIDER_LAUNCH_${Label}_RAW_BYTE_COUNT_MISMATCH"
    }
    $canonicalRequestRaw = Get-CanonicalJsonBytes $requestBody
    if ($requestRaw.Length -ne $canonicalRequestRaw.Length) {
        throw "WATCHDOG_PROVIDER_LAUNCH_${Label}_REQUEST_RAW_OBJECT_MISMATCH"
    }
    for ($index = 0; $index -lt $requestRaw.Length; $index++) {
        if ($requestRaw[$index] -ne $canonicalRequestRaw[$index]) {
            throw "WATCHDOG_PROVIDER_LAUNCH_${Label}_REQUEST_RAW_OBJECT_MISMATCH"
        }
    }
    try {
        $responseText = [Text.UTF8Encoding]::new($false, $true).GetString($responseRaw)
        Assert-StrictJsonText $responseText
        $responseRawObject = ConvertFrom-JsonPreserveStrings $responseText
    }
    catch {
        if ($_.Exception.Message -ceq 'WATCHDOG_PROVIDER_LAUNCH_RESPONSE_RAW_DUPLICATE_KEY') {
            throw 'WATCHDOG_PROVIDER_LAUNCH_RESPONSE_RAW_DUPLICATE_KEY'
        }
        throw "WATCHDOG_PROVIDER_LAUNCH_${Label}_RESPONSE_RAW_JSON_INVALID"
    }
    if ((Get-ByteSha256Hex (Get-CanonicalJsonBytes $responseRawObject)) -cne
        (Get-ByteSha256Hex (Get-CanonicalJsonBytes $responseBody))) {
        throw "WATCHDOG_PROVIDER_LAUNCH_${Label}_RESPONSE_RAW_OBJECT_MISMATCH"
    }
    $requestHash = Get-RequiredProperty $Value 'request_body_sha256'
    $responseHash = Get-RequiredProperty $Value 'response_body_sha256'
    if ($requestHash -isnot [string] -or $requestHash -notmatch '^[0-9A-F]{64}$' -or
        (Get-ByteSha256Hex $requestRaw) -cne $requestHash) {
        throw "WATCHDOG_PROVIDER_LAUNCH_${Label}_REQUEST_HASH_MISMATCH"
    }
    if ($responseHash -isnot [string] -or $responseHash -notmatch '^[0-9A-F]{64}$' -or
        (Get-ByteSha256Hex $responseRaw) -cne $responseHash) {
        throw "WATCHDOG_PROVIDER_LAUNCH_${Label}_RESPONSE_HASH_MISMATCH"
    }
    $responseContentType = Get-RequiredProperty $Value 'response_content_type'
    $responseContentEncoding = Get-RequiredProperty $Value 'response_content_encoding'
    $responseRequestId = Get-RequiredProperty $Value 'response_request_id'
    if ($responseContentType -isnot [string] -or
        $responseContentType.Length -gt 256 -or
        $responseContentType.Split(';')[0].Trim().ToLowerInvariant() -cne 'application/json' -or
        ($null -ne $responseContentEncoding -and
            ($responseContentEncoding -isnot [string] -or
             $responseContentEncoding.Trim().ToLowerInvariant() -cne 'identity')) -or
        ($null -ne $responseRequestId -and
            ($responseRequestId -isnot [string] -or
             $responseRequestId.Length -lt 1 -or $responseRequestId.Length -gt 256))) {
        throw "WATCHDOG_PROVIDER_LAUNCH_${Label}_RESPONSE_HEADER_MISMATCH"
    }
    $httpStatus = Get-RequiredProperty $Value 'response_http_status'
    if (-not (Test-IsJsonInteger $httpStatus) -or
        $AcceptedHttpStatuses -cnotcontains [int]$httpStatus) {
        throw "WATCHDOG_PROVIDER_LAUNCH_${Label}_HTTP_STATUS_MISMATCH"
    }
    $requestedUtc = Convert-ProviderUtcTimestamp ([string](Get-RequiredProperty $Value 'request_observed_at_utc'))
    $respondedUtc = Convert-ProviderUtcTimestamp ([string](Get-RequiredProperty $Value 'response_observed_at_utc'))
    if ($respondedUtc -lt $requestedUtc) {
        throw "WATCHDOG_PROVIDER_LAUNCH_${Label}_CHRONOLOGY_MISMATCH"
    }
    $elapsedMilliseconds = Get-RequiredProperty $Value 'elapsed_milliseconds'
    if (-not (Test-IsJsonInteger $elapsedMilliseconds) -or
        [int64]$elapsedMilliseconds -lt 0 -or [int64]$elapsedMilliseconds -gt 120000) {
        throw "WATCHDOG_PROVIDER_LAUNCH_${Label}_ELAPSED_MISMATCH"
    }
    $wallElapsedMilliseconds = [int64][math]::Round(
        ($respondedUtc - $requestedUtc).TotalMilliseconds
    )
    if ($wallElapsedMilliseconds -gt 120000 -or
        [math]::Abs($wallElapsedMilliseconds - [int64]$elapsedMilliseconds) -gt 5000) {
        throw "WATCHDOG_PROVIDER_LAUNCH_${Label}_WALL_MONOTONIC_MISMATCH"
    }
    return [ordered]@{
        request_body = $requestBody
        response_body = $responseBody
        requested_utc = $requestedUtc
        responded_utc = $respondedUtc
    }
}

function Read-ProviderLaunchReceipt {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][datetime]$ExpectedStartedUtc,
        [Parameter(Mandatory)][datetime]$ExpectedDeadlineUtc,
        [Parameter(Mandatory)][string]$ExpectedPublicKey
    )
    $item = Get-Item -LiteralPath $Path
    if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw 'WATCHDOG_PROVIDER_LAUNCH_RECEIPT_MUST_BE_A_PLAIN_FILE'
    }
    if ($item.Length -gt 262144) { throw 'WATCHDOG_PROVIDER_LAUNCH_RECEIPT_TOO_LARGE' }
    $rawBytes = [IO.File]::ReadAllBytes($item.FullName)
    try {
        $rawText = [Text.UTF8Encoding]::new($false, $true).GetString($rawBytes)
        $value = ConvertFrom-JsonPreserveStrings $rawText
    }
    catch {
        throw 'WATCHDOG_PROVIDER_LAUNCH_RECEIPT_JSON_INVALID'
    }
    $canonicalBytes = Get-CanonicalJsonBytes $value
    if ($rawBytes.Length -ne $canonicalBytes.Length) {
        throw 'WATCHDOG_PROVIDER_LAUNCH_RECEIPT_NOT_CANONICAL'
    }
    for ($index = 0; $index -lt $rawBytes.Length; $index++) {
        if ($rawBytes[$index] -ne $canonicalBytes[$index]) {
            throw 'WATCHDOG_PROVIDER_LAUNCH_RECEIPT_NOT_CANONICAL'
        }
    }
    Assert-ExactPropertyKeyset -Value $value -Expected @(
        'authorization_id',
        'authorization_sha256',
        'claim_boundary',
        'create_intent_sha256',
        'create_send_marker_sha256',
        'create_send_reserved_at_utc',
        'create_transaction',
        'dedicated_public_key_sha256',
        'hard_stop_deadline_utc',
        'image_name',
        'launch_mode',
        'oci_image_digest',
        'pod_id',
        'pod_name',
        'provider',
        'provider_started_at_utc',
        'precreate_guardian_receipt_sha256',
        'precreate_maximum_hard_stop_deadline_utc',
        'receipt_sha256',
        'schema_version',
        'source_commit_sha256',
        'status'
    ) -ErrorCode 'WATCHDOG_PROVIDER_LAUNCH_RECEIPT_KEYSET_MISMATCH'
    $expectedClaim = 'Locally captured exact RunPod request bytes, exact HTTP 201 response bytes, selected response metadata, and client timestamps. The receipt is not a RunPod signature, trusted timestamp, or billing settlement; it proves on-demand/unlocked only when the retained raw response strictly parses to the full retained object containing those false values, RUNNING, and lastStartedAt.'
    if ((Get-RequiredProperty $value 'schema_version') -cne 'cas_runpod_provider_launch_receipt.v2' -or
        (Get-RequiredProperty $value 'status') -cne 'EXACT_CREATE_RESPONSE_STARTED_POD_OBSERVED' -or
        (Get-RequiredProperty $value 'launch_mode') -cne 'CREATE_RESPONSE_STARTED_POD' -or
        (Get-RequiredProperty $value 'provider') -cne 'RUNPOD' -or
        (Get-RequiredProperty $value 'source_commit_sha256') -cne $SourceCommitSha256 -or
        (Get-RequiredProperty $value 'oci_image_digest') -cne $OciImageDigest -or
        (Get-RequiredProperty $value 'image_name') -cne $ExpectedImageName -or
        (Get-RequiredProperty $value 'pod_id') -cne $PodId -or
        (Get-RequiredProperty $value 'pod_name') -cne $PodName -or
        (Get-RequiredProperty $value 'claim_boundary') -cne $expectedClaim) {
        throw 'WATCHDOG_PROVIDER_LAUNCH_RECEIPT_BINDING_MISMATCH'
    }
    $publicKeySha256 = Get-RequiredProperty $value 'dedicated_public_key_sha256'
    if ($publicKeySha256 -isnot [string] -or $publicKeySha256 -notmatch '^[0-9A-F]{64}$' -or
        $publicKeySha256 -cne (Get-Utf8Sha256Hex $ExpectedPublicKey)) {
        throw 'WATCHDOG_PROVIDER_LAUNCH_PUBLIC_KEY_HASH_MISMATCH'
    }
    $authorizationId = Get-RequiredProperty $value 'authorization_id'
    $authorizationSha256 = Get-RequiredProperty $value 'authorization_sha256'
    $createIntentSha256 = Get-RequiredProperty $value 'create_intent_sha256'
    $createSendMarkerSha256 = Get-RequiredProperty $value 'create_send_marker_sha256'
    $guardianReceiptSha256 = Get-RequiredProperty $value 'precreate_guardian_receipt_sha256'
    if ($authorizationId -isnot [string] -or
        $authorizationId -cnotmatch '^[a-z0-9][a-z0-9-]{15,63}$' -or
        $authorizationSha256 -isnot [string] -or
        $authorizationSha256 -cnotmatch '^[0-9A-F]{64}$' -or
        $createIntentSha256 -isnot [string] -or
        $createIntentSha256 -cnotmatch '^[0-9A-F]{64}$' -or
        $createSendMarkerSha256 -isnot [string] -or
        $createSendMarkerSha256 -cnotmatch '^[0-9A-F]{64}$' -or
        $guardianReceiptSha256 -isnot [string] -or
        $guardianReceiptSha256 -cnotmatch '^[0-9A-F]{64}$') {
        throw 'WATCHDOG_PROVIDER_LAUNCH_AUTHORIZATION_BINDING_INVALID'
    }
    $unsigned = [ordered]@{
        authorization_id = $authorizationId
        authorization_sha256 = $authorizationSha256
        claim_boundary = Get-RequiredProperty $value 'claim_boundary'
        create_intent_sha256 = $createIntentSha256
        create_send_marker_sha256 = $createSendMarkerSha256
        create_send_reserved_at_utc = Get-RequiredProperty $value 'create_send_reserved_at_utc'
        create_transaction = Get-RequiredProperty $value 'create_transaction'
        dedicated_public_key_sha256 = $publicKeySha256
        hard_stop_deadline_utc = Get-RequiredProperty $value 'hard_stop_deadline_utc'
        image_name = Get-RequiredProperty $value 'image_name'
        launch_mode = Get-RequiredProperty $value 'launch_mode'
        oci_image_digest = Get-RequiredProperty $value 'oci_image_digest'
        pod_id = Get-RequiredProperty $value 'pod_id'
        pod_name = Get-RequiredProperty $value 'pod_name'
        provider = Get-RequiredProperty $value 'provider'
        provider_started_at_utc = Get-RequiredProperty $value 'provider_started_at_utc'
        precreate_guardian_receipt_sha256 = $guardianReceiptSha256
        precreate_maximum_hard_stop_deadline_utc = Get-RequiredProperty $value 'precreate_maximum_hard_stop_deadline_utc'
        schema_version = Get-RequiredProperty $value 'schema_version'
        source_commit_sha256 = Get-RequiredProperty $value 'source_commit_sha256'
        status = Get-RequiredProperty $value 'status'
    }
    $receiptSelfHash = Get-RequiredProperty $value 'receipt_sha256'
    if ($receiptSelfHash -isnot [string] -or $receiptSelfHash -notmatch '^[0-9A-F]{64}$' -or
        (Get-ByteSha256Hex (Get-CanonicalJsonBytes $unsigned)) -cne $receiptSelfHash) {
        throw 'WATCHDOG_PROVIDER_LAUNCH_RECEIPT_SELF_HASH_MISMATCH'
    }

    $create = Assert-ProviderTransaction `
        -Value (Get-RequiredProperty $value 'create_transaction') `
        -Label 'CREATE' `
        -ExpectedPath '/v1/pods' `
        -AcceptedHttpStatuses @(201)
    $createRequest = $create.request_body
    Assert-ExactPropertyKeyset -Value $createRequest -Expected @(
        'cloudType', 'containerDiskInGb', 'env', 'gpuCount', 'gpuTypeIds',
        'imageName', 'interruptible', 'locked', 'name', 'networkVolumeId',
        'ports', 'volumeEncrypted', 'volumeInGb', 'volumeMountPath'
    ) -ErrorCode 'WATCHDOG_PROVIDER_LAUNCH_CREATE_REQUEST_KEYSET_MISMATCH'
    $interruptibleRequest = Get-RequiredProperty $createRequest 'interruptible'
    $lockedRequest = Get-RequiredProperty $createRequest 'locked'
    $volumeEncryptedRequest = Get-RequiredProperty $createRequest 'volumeEncrypted'
    if ((Get-RequiredProperty $createRequest 'cloudType') -cne 'SECURE' -or
        -not (Test-IsJsonInteger (Get-RequiredProperty $createRequest 'containerDiskInGb')) -or
        [int64](Get-RequiredProperty $createRequest 'containerDiskInGb') -ne 50 -or
        -not (Test-IsJsonInteger (Get-RequiredProperty $createRequest 'gpuCount')) -or
        [int64](Get-RequiredProperty $createRequest 'gpuCount') -ne 1 -or
        (Get-RequiredProperty $createRequest 'imageName') -cne $ExpectedImageName -or
        $interruptibleRequest -isnot [bool] -or $interruptibleRequest -or
        $lockedRequest -isnot [bool] -or $lockedRequest -or
        (Get-RequiredProperty $createRequest 'name') -cne $PodName -or
        $null -ne (Get-RequiredProperty $createRequest 'networkVolumeId') -or
        $volumeEncryptedRequest -isnot [bool] -or -not $volumeEncryptedRequest -or
        -not (Test-IsJsonInteger (Get-RequiredProperty $createRequest 'volumeInGb')) -or
        [int64](Get-RequiredProperty $createRequest 'volumeInGb') -ne 20 -or
        (Get-RequiredProperty $createRequest 'volumeMountPath') -cne '/workspace') {
        throw 'WATCHDOG_PROVIDER_LAUNCH_CREATE_REQUEST_BOUNDARY_MISMATCH'
    }
    $gpuTypeIds = Get-RequiredProperty $createRequest 'gpuTypeIds'
    $ports = Get-RequiredProperty $createRequest 'ports'
    if ($gpuTypeIds -isnot [array] -or @($gpuTypeIds).Count -ne 1 -or
        [string]@($gpuTypeIds)[0] -cne 'NVIDIA A40' -or
        $ports -isnot [array] -or @($ports).Count -ne 1 -or
        [string]@($ports)[0] -cne '22/tcp') {
        throw 'WATCHDOG_PROVIDER_LAUNCH_CREATE_REQUEST_ARRAY_MISMATCH'
    }
    $environment = Get-RequiredProperty $createRequest 'env'
    Assert-ExactPropertyKeyset -Value $environment -Expected @('PUBLIC_KEY') `
        -ErrorCode 'WATCHDOG_PROVIDER_LAUNCH_CREATE_REQUEST_ENVIRONMENT_MISMATCH'
    $receiptPublicKey = Get-RequiredProperty $environment 'PUBLIC_KEY'
    if ($receiptPublicKey -isnot [string] -or $receiptPublicKey -cne $ExpectedPublicKey) {
        throw 'WATCHDOG_PROVIDER_LAUNCH_CREATE_REQUEST_PUBLIC_KEY_MISMATCH'
    }
    $createResponse = $create.response_body
    $createInterruptible = Get-RequiredProperty $createResponse 'interruptible'
    $createLocked = Get-RequiredProperty $createResponse 'locked'
    $createVolumeEncrypted = Get-RequiredProperty $createResponse 'volumeEncrypted'
    if ((Get-RequiredProperty $createResponse 'id') -cne $PodId -or
        (Get-RequiredProperty $createResponse 'name') -cne $PodName -or
        (Get-RequiredProperty $createResponse 'desiredStatus') -cne 'RUNNING' -or
        $createInterruptible -isnot [bool] -or $createInterruptible -or
        $createLocked -isnot [bool] -or $createLocked -or
        $createVolumeEncrypted -isnot [bool] -or -not $createVolumeEncrypted) {
        throw 'WATCHDOG_PROVIDER_LAUNCH_CREATE_RESPONSE_PROOF_MISMATCH'
    }
    $responseStartedUtc = Convert-ProviderUtcTimestamp ([string](Get-RequiredProperty $createResponse 'lastStartedAt'))
    $receiptStartedUtc = Convert-ProviderUtcTimestamp ([string](Get-RequiredProperty $value 'provider_started_at_utc'))
    $receiptDeadlineUtc = Convert-ProviderUtcTimestamp ([string](Get-RequiredProperty $value 'hard_stop_deadline_utc'))
    $sendReservedUtc = Convert-ProviderUtcTimestamp ([string](Get-RequiredProperty $value 'create_send_reserved_at_utc'))
    $precreateMaximumDeadlineUtc = Convert-ProviderUtcTimestamp ([string](Get-RequiredProperty $value 'precreate_maximum_hard_stop_deadline_utc'))
    $boundedDeadlineUtc = $receiptStartedUtc.AddSeconds($MaximumWallSeconds)
    if ($precreateMaximumDeadlineUtc -lt $boundedDeadlineUtc) {
        $boundedDeadlineUtc = $precreateMaximumDeadlineUtc
    }
    if ($responseStartedUtc -ne $receiptStartedUtc -or
        $receiptStartedUtc -ne $ExpectedStartedUtc -or
        $receiptDeadlineUtc -ne $ExpectedDeadlineUtc -or
        $receiptDeadlineUtc -ne $boundedDeadlineUtc -or
        $receiptDeadlineUtc -le $receiptStartedUtc -or
        $receiptDeadlineUtc -gt $receiptStartedUtc.AddSeconds($MaximumWallSeconds) -or
        $sendReservedUtc -gt $create.requested_utc -or
        ($create.requested_utc - $sendReservedUtc).TotalSeconds -gt 30 -or
        $precreateMaximumDeadlineUtc -le $sendReservedUtc -or
        $precreateMaximumDeadlineUtc -gt $sendReservedUtc.AddSeconds($MaximumWallSeconds)) {
        throw 'WATCHDOG_PROVIDER_LAUNCH_TIME_BINDING_MISMATCH'
    }
    if ($receiptStartedUtc -lt $create.requested_utc.AddSeconds(-30) -or
        $receiptStartedUtc -gt $create.responded_utc.AddSeconds(30)) {
        throw 'WATCHDOG_PROVIDER_LAUNCH_START_TIME_OUTSIDE_CREATE_EXCHANGE'
    }
    return [ordered]@{
        receipt_sha256 = Get-ByteSha256Hex $rawBytes
        provider_started_at_utc = $receiptStartedUtc.ToString('o')
        hard_stop_deadline_utc = $receiptDeadlineUtc.ToString('o')
    }
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

function Assert-StopTargetIdentity {
    param([Parameter(Mandatory)][object]$Pod)
    $id = Get-OptionalProperty $Pod 'id'
    $name = Get-OptionalProperty $Pod 'name'
    # The exact name is required by Assert-ExactTarget at arm time.  After arm,
    # containment is keyed only by the provider's immutable Pod ID so mutable
    # configuration drift cannot prevent an emergency STOP.
    if ($id -ne $PodId) {
        throw 'WATCHDOG_STOP_TARGET_IDENTITY_MISMATCH'
    }
    if ($ExcludedPodIds -contains $id) {
        throw 'WATCHDOG_STOP_TARGET_IS_EXPLICITLY_EXCLUDED'
    }
    return [ordered]@{
        id = $id
        name = $name
        desired_status = Get-OptionalProperty $Pod 'desiredStatus'
    }
}

function Assert-PreArmTargetIdentity {
    param([Parameter(Mandatory)][object]$Pod)
    $id = Get-OptionalProperty $Pod 'id'
    $name = Get-OptionalProperty $Pod 'name'
    if ($id -ne $PodId -or $name -ne $PodName) {
        throw 'WATCHDOG_PREARM_TARGET_IDENTITY_MISMATCH'
    }
    if ($ExcludedPodIds -contains $id) {
        throw 'WATCHDOG_PREARM_TARGET_IS_EXPLICITLY_EXCLUDED'
    }
}

function Wait-ForExitedByIdentity {
    param([Parameter(Mandatory)][datetime]$DeadlineUtc)
    do {
        $observed = Assert-StopTargetIdentity (Invoke-PodGet)
        Add-Event -Name 'POST_STOP_IDENTITY_STATUS' -Details $observed.desired_status
        if ($observed.desired_status -eq 'EXITED') { return $observed }
        Start-Sleep -Seconds $PollSeconds
    } while ((Get-Date).ToUniversalTime() -lt $DeadlineUtc)
    throw 'WATCHDOG_IDENTITY_STOP_DID_NOT_REACH_EXITED'
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
    $machine = Get-OptionalProperty $Pod 'machine'
    $machineGpuTypeId = Get-OptionalProperty $machine 'gpuTypeId'
    $secureCloud = Get-OptionalProperty $machine 'secureCloud'
    $networkVolume = Get-OptionalProperty $Pod 'networkVolume'
    $podVolumeInGb = Get-OptionalProperty $Pod 'volumeInGb'
    $containerDiskInGb = Get-OptionalProperty $Pod 'containerDiskInGb'
    $volumeMountPath = Get-OptionalProperty $Pod 'volumeMountPath'
    $volumeEncrypted = Get-OptionalProperty $Pod 'volumeEncrypted'
    $interruptible = Get-OptionalProperty $Pod 'interruptible'
    $locked = Get-OptionalProperty $Pod 'locked'
    $podEnvironment = Get-OptionalProperty $Pod 'env'
    $ports = @(Get-OptionalProperty $Pod 'ports')
    $portMappings = Get-OptionalProperty $Pod 'portMappings'
    $providerStartedAtRaw = Get-OptionalProperty $Pod 'lastStartedAt'
    if ($providerStartedAtRaw -isnot [string]) { throw 'WATCHDOG_PROVIDER_START_TIME_MISSING' }
    $providerStartedUtc = Convert-ProviderUtcTimestamp $providerStartedAtRaw
    $cost = Get-OptionalProperty $Pod 'costPerHr'
    $adjustedCost = Get-OptionalProperty $Pod 'adjustedCostPerHr'
    if ($id -ne $PodId -or $name -ne $PodName) { throw 'WATCHDOG_TARGET_IDENTITY_MISMATCH' }
    if ($ExcludedPodIds -contains $id) { throw 'WATCHDOG_TARGET_IS_EXPLICITLY_EXCLUDED' }
    if ($image -ne $ExpectedImageName) { throw 'WATCHDOG_TARGET_IMAGE_NAME_MISMATCH' }
    if (-not (Test-IsJsonInteger $gpuCount) -or [int64]$gpuCount -ne 1) {
        throw 'WATCHDOG_TARGET_GPU_COUNT_MISMATCH'
    }
    if ($machineGpuTypeId -cne 'NVIDIA A40') {
        throw 'WATCHDOG_TARGET_GPU_TYPE_MISMATCH'
    }
    if ($null -ne $gpuId -and $gpuId -cne 'NVIDIA A40') {
        throw 'WATCHDOG_TARGET_CONFLICTING_GPU_ID'
    }
    if ($null -ne $gpuDisplay -and @('NVIDIA A40', 'A40') -cnotcontains $gpuDisplay) {
        throw 'WATCHDOG_TARGET_CONFLICTING_GPU_DISPLAY_NAME'
    }
    if ($secureCloud -isnot [bool] -or -not $secureCloud) {
        throw 'WATCHDOG_TARGET_NOT_SECURE_CLOUD'
    }
    if ($null -ne $networkVolume) { throw 'WATCHDOG_TARGET_HAS_FORBIDDEN_NETWORK_VOLUME' }
    if (-not (Test-IsJsonInteger $podVolumeInGb) -or [int64]$podVolumeInGb -ne 20) {
        throw 'WATCHDOG_TARGET_POD_VOLUME_MISMATCH'
    }
    if (-not (Test-IsJsonInteger $containerDiskInGb) -or [int64]$containerDiskInGb -ne 50) {
        throw 'WATCHDOG_TARGET_CONTAINER_DISK_MISMATCH'
    }
    if ($volumeMountPath -cne '/workspace') { throw 'WATCHDOG_TARGET_VOLUME_MOUNT_MISMATCH' }
    if ($volumeEncrypted -isnot [bool] -or -not $volumeEncrypted) {
        throw 'WATCHDOG_TARGET_VOLUME_NOT_ENCRYPTED'
    }
    if ($null -ne $interruptible) {
        if ($interruptible -isnot [bool]) { throw 'WATCHDOG_TARGET_INTERRUPTIBLE_TYPE_MISMATCH' }
        if ($interruptible) { throw 'WATCHDOG_TARGET_IS_INTERRUPTIBLE' }
    }
    if ($null -ne $locked) {
        if ($locked -isnot [bool]) { throw 'WATCHDOG_TARGET_LOCKED_TYPE_MISMATCH' }
        if ($locked) { throw 'WATCHDOG_TARGET_IS_LOCKED' }
    }
    if ($null -eq $podEnvironment) { throw 'WATCHDOG_TARGET_ENVIRONMENT_MISSING' }
    $environmentProperties = @($podEnvironment.PSObject.Properties)
    if ($environmentProperties.Count -ne 1 -or
        $environmentProperties[0].Name -cne 'PUBLIC_KEY') {
        throw 'WATCHDOG_TARGET_ENVIRONMENT_KEYSET_MISMATCH'
    }
    $providerPublicKey = $environmentProperties[0].Value
    if ($providerPublicKey -isnot [string] -or $providerPublicKey -cne $script:ExpectedPublicKey) {
        throw 'WATCHDOG_TARGET_PUBLIC_KEY_MISMATCH'
    }
    if ($ports.Count -ne 1 -or [string]$ports[0] -cne '22/tcp') {
        throw 'WATCHDOG_TARGET_PORTS_MISMATCH'
    }
    if ($null -eq $portMappings) { throw 'WATCHDOG_TARGET_PORT_MAPPING_MISSING' }
    $portMappingProperties = @($portMappings.PSObject.Properties)
    if ($portMappingProperties.Count -ne 1 -or $portMappingProperties[0].Name -cne '22') {
        throw 'WATCHDOG_TARGET_PORT_MAPPING_MISMATCH'
    }
    $externalSshPort = $portMappingProperties[0].Value
    if (-not (Test-IsJsonInteger $externalSshPort) -or
        [int64]$externalSshPort -lt 1 -or [int64]$externalSshPort -gt 65535) {
        throw 'WATCHDOG_TARGET_EXTERNAL_SSH_PORT_INVALID'
    }
    if ([math]::Abs(($providerStartedUtc - $startedUtc).TotalSeconds) -gt 2) {
        throw 'WATCHDOG_PROVIDER_START_TIME_MISMATCH'
    }
    $observedRates = @($cost, $adjustedCost) | Where-Object { $null -ne $_ }
    if ($observedRates.Count -eq 0) { throw 'WATCHDOG_TARGET_RATE_MISSING' }
    foreach ($rate in $observedRates) {
        if (-not (Test-IsJsonNumber $rate) -or [decimal]$rate -lt 0 -or
            [decimal]$rate -gt $MaximumHourlyRate) {
            throw 'WATCHDOG_TARGET_RATE_EXCEEDS_CEILING'
        }
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
        machine_gpu_type_id = $machineGpuTypeId
        secure_cloud = $true
        cost_per_hour = if ($null -eq $cost) { $null } else { [decimal]$cost }
        adjusted_cost_per_hour = if ($null -eq $adjustedCost) { $null } else { [decimal]$adjustedCost }
        interruptible_provider_field = $interruptible
        interruptible_claim = if ($null -eq $interruptible) {
            'NOT_EXPOSED_BY_PROVIDER_GET_PROVIDER_CREATE_RESPONSE_FALSE'
        } else {
            'PROVIDER_GET_FALSE'
        }
        locked_provider_field = $locked
        locked_claim = if ($null -eq $locked) {
            'NOT_EXPOSED_BY_PROVIDER_GET_PROVIDER_CREATE_RESPONSE_FALSE'
        } else {
            'PROVIDER_GET_FALSE'
        }
        network_volume_absent = $true
        pod_volume_gb = [int]$podVolumeInGb
        container_disk_gb = [int]$containerDiskInGb
        volume_mount_path = $volumeMountPath
        volume_encrypted = $true
        ports = @($ports)
        external_ssh_port = [int]$externalSshPort
        public_key_sha256 = Get-Utf8Sha256Hex $script:ExpectedPublicKey
        provider_started_at_utc = $providerStartedUtc.ToString('o')
    }
}

function Remove-OwnedFallbackTask {
    param([Parameter(Mandatory)][string]$Name)
    $existing = Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
    if ($null -eq $existing) { return 'ALREADY_ABSENT' }
    Unregister-ScheduledTask -TaskName $Name -Confirm:$false
    if (Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue) {
        throw 'WATCHDOG_FALLBACK_TASK_RETIREMENT_FAILED'
    }
    return 'RETIRED'
}

function Assert-FallbackTaskRegistration {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$ExpectedExecute,
        [Parameter(Mandatory)][string]$ExpectedArguments,
        [Parameter(Mandatory)][datetime]$ExpectedDeadlineUtc,
        [Parameter(Mandatory)][string]$ExpectedUserId
    )
    $registeredTask = Get-ScheduledTask -TaskName $Name -ErrorAction Stop
    $actions = @($registeredTask.Actions)
    $triggers = @($registeredTask.Triggers)
    if ($registeredTask.TaskName -cne $Name -or $registeredTask.TaskPath -cne '\') {
        throw 'WATCHDOG_FALLBACK_TASK_IDENTITY_REVALIDATION_FAILED'
    }
    if ([string]$registeredTask.State -cne 'Ready') {
        throw 'WATCHDOG_FALLBACK_TASK_STATE_REVALIDATION_FAILED'
    }
    if ($actions.Count -ne 1 -or
        [string]$actions[0].Execute -cne $ExpectedExecute -or
        [string]$actions[0].Arguments -cne $ExpectedArguments) {
        throw 'WATCHDOG_FALLBACK_TASK_ACTION_REVALIDATION_FAILED'
    }
    if ($triggers.Count -ne 1 -or $triggers[0].Enabled -isnot [bool] -or
        -not $triggers[0].Enabled) {
        throw 'WATCHDOG_FALLBACK_TASK_TRIGGER_REVALIDATION_FAILED'
    }
    $triggerStartUtc = Convert-ProviderUtcTimestamp ([string]$triggers[0].StartBoundary)
    if ([math]::Abs(($triggerStartUtc - $ExpectedDeadlineUtc).TotalSeconds) -gt 2) {
        throw 'WATCHDOG_FALLBACK_TASK_TRIGGER_TIME_REVALIDATION_FAILED'
    }
    if ($registeredTask.Principal.UserId -cne $ExpectedUserId -or
        [string]$registeredTask.Principal.LogonType -cne 'Interactive' -or
        [string]$registeredTask.Principal.RunLevel -cne 'Limited') {
        throw 'WATCHDOG_FALLBACK_TASK_PRINCIPAL_REVALIDATION_FAILED'
    }
    if ($registeredTask.Settings.Enabled -isnot [bool] -or
        -not $registeredTask.Settings.Enabled -or
        $registeredTask.Settings.StartWhenAvailable -isnot [bool] -or
        -not $registeredTask.Settings.StartWhenAvailable -or
        $registeredTask.Settings.WakeToRun -isnot [bool] -or
        -not $registeredTask.Settings.WakeToRun -or
        $registeredTask.Settings.DisallowStartIfOnBatteries -isnot [bool] -or
        $registeredTask.Settings.DisallowStartIfOnBatteries -or
        $registeredTask.Settings.StopIfGoingOnBatteries -isnot [bool] -or
        $registeredTask.Settings.StopIfGoingOnBatteries -or
        [string]$registeredTask.Settings.MultipleInstances -cne 'IgnoreNew' -or
        [int]$registeredTask.Settings.RestartCount -ne 3 -or
        [string]$registeredTask.Settings.RestartInterval -cne 'PT1M' -or
        [string]$registeredTask.Settings.ExecutionTimeLimit -cne 'PT15M') {
        throw 'WATCHDOG_FALLBACK_TASK_SETTINGS_REVALIDATION_FAILED'
    }
    $taskInfo = Get-ScheduledTaskInfo -TaskName $Name -ErrorAction Stop
    if ($null -eq $taskInfo.NextRunTime -or
        [math]::Abs(($taskInfo.NextRunTime.ToUniversalTime() - $ExpectedDeadlineUtc).TotalSeconds) -gt 2) {
        throw 'WATCHDOG_FALLBACK_TASK_NEXT_RUN_REVALIDATION_FAILED'
    }
}

if ($ValidateProviderLaunchReceiptOnly) {
    if ($EmergencyStopOnly) { throw 'WATCHDOG_RECEIPT_VALIDATION_MODE_CONFLICT' }
    if ($ExcludedPodIds -contains $PodId) { throw 'WATCHDOG_TARGET_IS_EXPLICITLY_EXCLUDED' }
    if ([string]::IsNullOrWhiteSpace($ProviderLaunchReceiptPath)) {
        throw 'WATCHDOG_PROVIDER_LAUNCH_RECEIPT_PATH_MISSING'
    }
    $validationStartedUtc = Convert-ProviderUtcTimestamp $RunStartedAtUtc
    $validationDeadlineUtc = Convert-ProviderUtcTimestamp $HardStopDeadlineUtc
    if ($validationDeadlineUtc -le $validationStartedUtc -or
        $validationDeadlineUtc -gt $validationStartedUtc.AddSeconds($MaximumWallSeconds)) {
        throw 'WATCHDOG_PROVIDER_LAUNCH_DEADLINE_BOUND_INVALID'
    }
    $validationPublicKey = Read-ExpectedPublicKey -Path $ExpectedPublicKeyPath
    $validatedProviderLaunch = Read-ProviderLaunchReceipt `
        -Path $ProviderLaunchReceiptPath `
        -ExpectedStartedUtc $validationStartedUtc `
        -ExpectedDeadlineUtc $validationDeadlineUtc `
        -ExpectedPublicKey $validationPublicKey
    Write-Output ('PROVIDER_LAUNCH_RECEIPT_VALIDATION_PASS_NO_PROVIDER_CALL ' +
        $validatedProviderLaunch.receipt_sha256)
    exit 0
}

if ($ExcludedPodIds -contains $PodId) { throw 'WATCHDOG_TARGET_IS_EXPLICITLY_EXCLUDED' }
$startedUtc = $null
$deadlineUtc = $null
$receiptRoot = $null
$script:EventPath = $null
$armedReceiptPath = $null
$terminalReceiptPath = $null
$emergencyTerminalPath = $null
$taskName = "CAS-OpenWeight-Canary-Stop-$PodId"

if ($EmergencyStopOnly) {
    try {
        $startedUtc = Convert-ProviderUtcTimestamp $RunStartedAtUtc
        $deadlineUtc = Convert-ProviderUtcTimestamp $HardStopDeadlineUtc
        if ($deadlineUtc -le $startedUtc -or
            $deadlineUtc -gt $startedUtc.AddSeconds($MaximumWallSeconds)) {
            throw 'WATCHDOG_EMERGENCY_DEADLINE_BOUND_INVALID'
        }
        $receiptRoot = [IO.Path]::GetFullPath($ReceiptDirectory)
        $script:EventPath = Join-Path $receiptRoot 'watchdog.events.jsonl'
        $armedReceiptPath = Join-Path $receiptRoot 'external-watchdog.receipt.json'
        $emergencyTerminalPath = Join-Path $receiptRoot 'watchdog.emergency.terminal.json'
    }
    catch {
        throw 'WATCHDOG_EMERGENCY_START_TIME_INVALID'
    }
    if (-not (Test-Path -LiteralPath $receiptRoot -PathType Container)) {
        throw 'WATCHDOG_EMERGENCY_RECEIPT_DIRECTORY_MISSING'
    }
    if (-not (Test-Path -LiteralPath $armedReceiptPath -PathType Leaf)) {
        throw 'WATCHDOG_EMERGENCY_ARMED_RECEIPT_MISSING'
    }
    if ([string]::IsNullOrWhiteSpace($ProviderLaunchReceiptSha256)) {
        throw 'WATCHDOG_EMERGENCY_PROVIDER_LAUNCH_RECEIPT_SHA256_MISSING'
    }
    $armedItem = Get-Item -LiteralPath $armedReceiptPath
    if ($armedItem.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw 'WATCHDOG_EMERGENCY_ARMED_RECEIPT_REPARSE_FORBIDDEN'
    }
    if ($armedItem.Length -gt 65536) {
        throw 'WATCHDOG_EMERGENCY_ARMED_RECEIPT_TOO_LARGE'
    }
    $watchdogScriptSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $PSCommandPath).Hash
    $expectedArmedReceipt = [ordered]@{
        claim_boundary = $ReceiptClaim
        emergency_fallback_status = 'REGISTERED_AND_REVALIDATED'
        emergency_task_name = $taskName
        hard_stop_deadline_utc = $deadlineUtc.ToString('o')
        maximum_spend_usd = '0.50'
        maximum_wall_seconds = $MaximumWallSeconds
        oci_image_digest = $OciImageDigest
        provider = 'RUNPOD'
        provider_launch_receipt_sha256 = $ProviderLaunchReceiptSha256
        provider_started_at_utc = $startedUtc.ToString('o')
        schema_version = 'cas_external_stop_watchdog_receipt.v2'
        source_commit_sha256 = $SourceCommitSha256
        status = 'ARMED'
        watchdog_script_sha256 = $watchdogScriptSha256
        workload_id = $PodId
        workload_name = $PodName
    }
    $expectedArmedBytes = [Text.UTF8Encoding]::new($false).GetBytes(
        (($expectedArmedReceipt | ConvertTo-Json -Depth 12 -Compress) + "`n")
    )
    $observedArmedBytes = [IO.File]::ReadAllBytes($armedItem.FullName)
    if ($observedArmedBytes.Length -ne $expectedArmedBytes.Length) {
        throw 'WATCHDOG_EMERGENCY_ARMED_RECEIPT_BYTES_MISMATCH'
    }
    for ($index = 0; $index -lt $expectedArmedBytes.Length; $index++) {
        if ($observedArmedBytes[$index] -ne $expectedArmedBytes[$index]) {
            throw 'WATCHDOG_EMERGENCY_ARMED_RECEIPT_BYTES_MISMATCH'
        }
    }
    $apiKey = $null
    $script:Headers = $null
    $emergencyStaleRestartDetected = $false
    $emergencyTaskCleanupStatus = $null
    try {
        $apiKey = Read-RunPodApiKey -Path $ConfigPath
        $script:Headers = @{ Authorization = 'Bearer ' + $apiKey }
        $emergencyPod = Invoke-PodGet
        $target = Assert-StopTargetIdentity $emergencyPod
        $emergencyProviderStartedAtRaw = Get-OptionalProperty $emergencyPod 'lastStartedAt'
        if ($emergencyProviderStartedAtRaw -isnot [string]) {
            throw 'WATCHDOG_EMERGENCY_PROVIDER_START_TIME_MISSING'
        }
        $emergencyProviderStartedUtc = Convert-ProviderUtcTimestamp $emergencyProviderStartedAtRaw
        if ([math]::Abs(($emergencyProviderStartedUtc - $startedUtc).TotalSeconds) -gt 2) {
            $emergencyStaleRestartDetected = $true
            throw 'WATCHDOG_EMERGENCY_STALE_RESTART_MISMATCH'
        }
        if ($target.desired_status -eq 'RUNNING') {
            $status = Invoke-PodStop
            Add-Event -Name 'EMERGENCY_STOP_ACCEPTED_HTTP_200' -Details $target
            $target = Wait-ForExitedByIdentity -DeadlineUtc ((Get-Date).ToUniversalTime().AddMinutes(10))
            $terminalStatus = 'EMERGENCY_STOPPED_BEFORE_HARD_DEADLINE_EXITED_CONFIRMED'
        }
        elseif ($target.desired_status -eq 'EXITED') {
            $status = $null
            $terminalStatus = 'EMERGENCY_OBSERVED_ALREADY_EXITED'
        }
        else {
            throw 'WATCHDOG_EMERGENCY_TARGET_STATE_UNEXPECTED'
        }
        $taskCleanupStatus = Remove-OwnedFallbackTask -Name $taskName
        $emergencyTaskCleanupStatus = $taskCleanupStatus
        Write-CreateNewUtf8Json -Path $emergencyTerminalPath -Value ([ordered]@{
            schema_version = 'cas_runpod_watchdog_emergency_terminal.v1'
            status = $terminalStatus
            pod_id = $PodId
            observed_at_utc = (Get-Date).ToUniversalTime().ToString('o')
            stop_http_status = $status
            fallback_task_cleanup_status = $taskCleanupStatus
            delete_attempted = $false
        })
        exit 0
    }
    catch {
        $emergencyTaskDisposition = if ($null -ne $emergencyTaskCleanupStatus) {
            'TERMINAL_RECEIPT_FAILED_AFTER_TASK_' + $emergencyTaskCleanupStatus
        } else {
            'RETAINED_FOR_SCHEDULED_RETRY'
        }
        if ($emergencyStaleRestartDetected -and $null -eq $emergencyTaskCleanupStatus) {
            try {
                $emergencyTaskDisposition = Remove-OwnedFallbackTask -Name $taskName
            }
            catch {
                $emergencyTaskDisposition = 'STALE_TASK_RETIREMENT_FAILED_OPERATOR_INTERVENTION_REQUIRED'
            }
        }
        Add-Event -Name 'EMERGENCY_STOP_FAILED_CLOSED' -Details ([ordered]@{
            error_type = $_.Exception.GetType().FullName
            error_line = $_.InvocationInfo.ScriptLineNumber
            fallback_task_disposition = $emergencyTaskDisposition
        })
        exit 2
    }
    finally {
        if ($null -ne $script:Headers) { $script:Headers.Clear() }
        $script:Headers = $null
        $apiKey = $null
    }
}

$apiKey = $null
$script:Headers = $null
$armIdentityProven = $false
$eventLoggingAllowed = $false
$fallbackTaskRegistered = $false
$armedReceiptWritten = $false
try {
    $apiKey = Read-RunPodApiKey -Path $ConfigPath
    $script:Headers = @{ Authorization = 'Bearer ' + $apiKey }
    $initialPod = Invoke-PodGet
    Assert-PreArmTargetIdentity $initialPod
    $armIdentityProven = $true
    $startedUtc = Convert-ProviderUtcTimestamp $RunStartedAtUtc
    $receiptRoot = [IO.Path]::GetFullPath($ReceiptDirectory)
    $script:EventPath = Join-Path $receiptRoot 'watchdog.events.jsonl'
    $armedReceiptPath = Join-Path $receiptRoot 'external-watchdog.receipt.json'
    $terminalReceiptPath = Join-Path $receiptRoot 'watchdog.terminal.json'
    $nowUtc = (Get-Date).ToUniversalTime()
    $deadlineUtc = Convert-ProviderUtcTimestamp $HardStopDeadlineUtc
    if ($deadlineUtc -le $startedUtc -or
        $deadlineUtc -gt $startedUtc.AddSeconds($MaximumWallSeconds)) {
        throw 'WATCHDOG_DEADLINE_BOUND_INVALID'
    }
    if ($startedUtc -gt $nowUtc.AddMinutes(2) -or $startedUtc -lt $nowUtc.AddMinutes(-5)) {
        throw 'WATCHDOG_START_TIME_OUTSIDE_ARM_WINDOW'
    }
    if ($deadlineUtc -le $nowUtc.AddMinutes(10)) { throw 'WATCHDOG_DEADLINE_TOO_NEAR' }
    if (Test-Path -LiteralPath $receiptRoot) { throw 'WATCHDOG_RECEIPT_DIRECTORY_MUST_BE_NEW' }
    [IO.Directory]::CreateDirectory($receiptRoot) | Out-Null
    $eventLoggingAllowed = $true
    $script:ExpectedPublicKey = Read-ExpectedPublicKey -Path $ExpectedPublicKeyPath
    if ([string]::IsNullOrWhiteSpace($ProviderLaunchReceiptPath)) {
        throw 'WATCHDOG_PROVIDER_LAUNCH_RECEIPT_PATH_MISSING'
    }
    $providerLaunch = Read-ProviderLaunchReceipt `
        -Path $ProviderLaunchReceiptPath `
        -ExpectedStartedUtc $startedUtc `
        -ExpectedDeadlineUtc $deadlineUtc `
        -ExpectedPublicKey $script:ExpectedPublicKey
    $target = Assert-ExactTarget $initialPod
    if ($target.desired_status -ne 'RUNNING') { throw 'WATCHDOG_TARGET_NOT_RUNNING_AT_ARM' }

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
        '-RunStartedAtUtc', ('"' + $startedUtc.ToString('o') + '"'),
        '-HardStopDeadlineUtc', ('"' + $deadlineUtc.ToString('o') + '"'),
        '-SourceCommitSha256', $SourceCommitSha256,
        '-OciImageDigest', $OciImageDigest,
        '-ExpectedImageName', $ExpectedImageName,
        '-ObservedHourlyRate', $ObservedHourlyRate.ToString([Globalization.CultureInfo]::InvariantCulture),
        '-ReceiptDirectory', ('"' + $receiptRoot + '"'),
        '-ProviderLaunchReceiptSha256', $providerLaunch.receipt_sha256,
        '-ConfigPath', ('"' + ([IO.Path]::GetFullPath($ConfigPath)) + '"')
    ) -join ' '
    $fallbackTriggerUtc = $deadlineUtc.AddSeconds(-$LocalStopLeadSeconds)
    $taskAction = New-ScheduledTaskAction -Execute $powerShellPath -Argument $taskArguments
    $taskTrigger = New-ScheduledTaskTrigger -Once -At $fallbackTriggerUtc.ToLocalTime()
    $taskSettings = New-ScheduledTaskSettingsSet `
        -StartWhenAvailable `
        -WakeToRun `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -MultipleInstances IgnoreNew `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 15)
    $currentUserId = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    $taskPrincipal = New-ScheduledTaskPrincipal `
        -UserId $currentUserId `
        -LogonType Interactive `
        -RunLevel Limited
    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $taskAction `
        -Trigger $taskTrigger `
        -Settings $taskSettings `
        -Principal $taskPrincipal | Out-Null
    $fallbackTaskRegistered = $true
    Assert-FallbackTaskRegistration `
        -Name $taskName `
        -ExpectedExecute $powerShellPath `
        -ExpectedArguments $taskArguments `
        -ExpectedDeadlineUtc $fallbackTriggerUtc `
        -ExpectedUserId $currentUserId
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
        provider_launch_receipt_sha256 = $providerLaunch.receipt_sha256
        provider_started_at_utc = $providerLaunch.provider_started_at_utc
        schema_version = 'cas_external_stop_watchdog_receipt.v2'
        source_commit_sha256 = $SourceCommitSha256
        status = 'ARMED'
        watchdog_script_sha256 = $watchdogScriptSha256
        workload_id = $PodId
        workload_name = $PodName
    }
    Write-CreateNewUtf8Json -Path $armedReceiptPath -Value $armedReceipt
    $armedReceiptWritten = $true
    Add-Event -Name 'WATCHDOG_ARMED' -Details $target

    $localStopInitiationUtc = $fallbackTriggerUtc
    while ($true) {
        $remainingSeconds = ($localStopInitiationUtc - (Get-Date).ToUniversalTime()).TotalSeconds
        if ($remainingSeconds -le 0) { break }
        $sleepSeconds = [int][math]::Max(1, [math]::Min($PollSeconds, [math]::Floor($remainingSeconds)))
        Start-Sleep -Seconds $sleepSeconds
        if ((Get-Date).ToUniversalTime() -ge $localStopInitiationUtc) { break }
        $observed = Assert-ExactTarget (Invoke-PodGet)
        if ($observed.desired_status -eq 'EXITED') {
            Add-Event -Name 'TARGET_EXITED_BEFORE_DEADLINE' -Details $observed
            $taskCleanupStatus = Remove-OwnedFallbackTask -Name $taskName
            $fallbackTaskRegistered = $false
            Write-CreateNewUtf8Json -Path $terminalReceiptPath -Value ([ordered]@{
                schema_version = 'cas_runpod_watchdog_terminal.v1'
                status = 'EXITED_BEFORE_DEADLINE_NO_STOP_REQUIRED'
                pod_id = $PodId
                observed_at_utc = (Get-Date).ToUniversalTime().ToString('o')
                hard_stop_deadline_utc = $deadlineUtc.ToString('o')
                fallback_task_cleanup_status = $taskCleanupStatus
                delete_attempted = $false
            })
            exit 0
        }
        if ($observed.desired_status -ne 'RUNNING') {
            throw 'WATCHDOG_TARGET_ENTERED_UNEXPECTED_STATE'
        }
    }

    $finalTarget = Assert-StopTargetIdentity (Invoke-PodGet)
    if ($finalTarget.desired_status -eq 'RUNNING') {
        $stopHttpStatus = Invoke-PodStop
        Add-Event -Name 'STOP_ACCEPTED_HTTP_200' -Details $finalTarget
        $observed = Wait-ForExitedByIdentity -DeadlineUtc ((Get-Date).ToUniversalTime().AddMinutes(10))
        $terminalStatus = 'STOPPED_BEFORE_HARD_DEADLINE_EXITED_CONFIRMED'
    }
    elseif ($finalTarget.desired_status -eq 'EXITED') {
        $stopHttpStatus = $null
        $observed = $finalTarget
        $terminalStatus = 'OBSERVED_EXITED_AT_LOCAL_STOP_BOUNDARY'
    }
    else {
        throw 'WATCHDOG_TARGET_STATE_UNEXPECTED_AT_LOCAL_STOP_BOUNDARY'
    }
    $taskCleanupStatus = Remove-OwnedFallbackTask -Name $taskName
    $fallbackTaskRegistered = $false

    Write-CreateNewUtf8Json -Path $terminalReceiptPath -Value ([ordered]@{
        schema_version = 'cas_runpod_watchdog_terminal.v1'
        status = $terminalStatus
        pod_id = $PodId
        stopped_at_utc = (Get-Date).ToUniversalTime().ToString('o')
        hard_stop_deadline_utc = $deadlineUtc.ToString('o')
        local_stop_lead_seconds = $LocalStopLeadSeconds
        stop_http_status = $stopHttpStatus
        fallback_task_cleanup_status = $taskCleanupStatus
        delete_attempted = $false
        evidence_export_required_before_delete = $true
    })
    exit 0
}
catch {
    $primaryError = $_
    $failStopStatus = 'NOT_ATTEMPTED_NO_PROVIDER_SESSION'
    $failStopHttpStatus = $null
    $failStopTerminalStatus = $null
    $failStopErrorType = $null
    $taskCleanupStatus = if ($fallbackTaskRegistered) { 'NOT_YET_ATTEMPTED' } else { 'NOT_OWNED_BY_THIS_INVOCATION' }
    if ($armIdentityProven -and $null -ne $script:Headers) {
        try {
            $failTarget = Assert-StopTargetIdentity (Invoke-PodGet)
            if ($failTarget.desired_status -eq 'RUNNING') {
                $failStopHttpStatus = Invoke-PodStop
                $failTerminal = Wait-ForExitedByIdentity -DeadlineUtc ((Get-Date).ToUniversalTime().AddMinutes(10))
                $failStopTerminalStatus = $failTerminal.desired_status
                $failStopStatus = 'STOPPED_AFTER_WATCHDOG_FAILURE_EXITED_CONFIRMED'
            }
            elseif ($failTarget.desired_status -eq 'EXITED') {
                $failStopTerminalStatus = $failTarget.desired_status
                $failStopStatus = 'ALREADY_EXITED_AFTER_WATCHDOG_FAILURE'
            }
            else {
                $failStopStatus = 'UNEXPECTED_STATE_OPERATOR_INTERVENTION_REQUIRED'
            }
        }
        catch {
            $failStopErrorType = $_.Exception.GetType().FullName
            $failStopStatus = 'FAIL_STOP_ATTEMPT_FAILED_OPERATOR_INTERVENTION_REQUIRED'
        }
    }
    $containmentConfirmed = $failStopStatus -in @(
        'STOPPED_AFTER_WATCHDOG_FAILURE_EXITED_CONFIRMED',
        'ALREADY_EXITED_AFTER_WATCHDOG_FAILURE'
    )
    if ($fallbackTaskRegistered) {
        if ($containmentConfirmed) {
            try {
                $taskCleanupStatus = Remove-OwnedFallbackTask -Name $taskName
                $fallbackTaskRegistered = $false
            }
            catch {
                $taskCleanupStatus = 'RETIREMENT_FAILED_OPERATOR_INTERVENTION_REQUIRED'
            }
        }
        elseif ($armedReceiptWritten) {
            $taskCleanupStatus = 'RETAINED_FOR_PENDING_FALLBACK'
        }
        else {
            try {
                $removedStatus = Remove-OwnedFallbackTask -Name $taskName
                $taskCleanupStatus = 'RETIRED_UNUSABLE_NO_ARM_RECEIPT_' + $removedStatus
                $fallbackTaskRegistered = $false
            }
            catch {
                $taskCleanupStatus = 'UNUSABLE_TASK_RETIREMENT_FAILED_OPERATOR_INTERVENTION_REQUIRED'
            }
        }
    }
    $taskCleanupComplete = $taskCleanupStatus -in @(
        'RETIRED',
        'ALREADY_ABSENT',
        'NOT_OWNED_BY_THIS_INVOCATION'
    )
    $terminalFailureStatus = if ($containmentConfirmed -and $taskCleanupComplete) {
        'WATCHDOG_FAILED_CLOSED_CONTAINMENT_CONFIRMED'
    } else {
        'WATCHDOG_FAILED_CLOSED_OPERATOR_INTERVENTION_REQUIRED'
    }
    if ($eventLoggingAllowed) {
        try {
            Add-Event -Name 'WATCHDOG_FAILED_CLOSED' -Details ([ordered]@{
                error_type = $primaryError.Exception.GetType().FullName
                error_line = $primaryError.InvocationInfo.ScriptLineNumber
                fail_stop_status = $failStopStatus
                fail_stop_http_status = $failStopHttpStatus
                fail_stop_terminal_status = $failStopTerminalStatus
                fail_stop_error_type = $failStopErrorType
                fallback_task_cleanup_status = $taskCleanupStatus
            })
        }
        catch {}
        if (-not (Test-Path -LiteralPath $terminalReceiptPath)) {
            try {
                Write-CreateNewUtf8Json -Path $terminalReceiptPath -Value ([ordered]@{
                    schema_version = 'cas_runpod_watchdog_terminal.v1'
                    status = $terminalFailureStatus
                    pod_id = $PodId
                    observed_at_utc = (Get-Date).ToUniversalTime().ToString('o')
                    fail_stop_status = $failStopStatus
                    fail_stop_http_status = $failStopHttpStatus
                    fail_stop_terminal_status = $failStopTerminalStatus
                    fail_stop_error_type = $failStopErrorType
                    fallback_task_cleanup_status = $taskCleanupStatus
                    primary_error_type = $primaryError.Exception.GetType().FullName
                    primary_error_line = $primaryError.InvocationInfo.ScriptLineNumber
                    delete_attempted = $false
                })
            }
            catch {}
        }
    }
    exit 1
}
finally {
    if ($null -ne $script:Headers) { $script:Headers.Clear() }
    $script:Headers = $null
    $apiKey = $null
}
