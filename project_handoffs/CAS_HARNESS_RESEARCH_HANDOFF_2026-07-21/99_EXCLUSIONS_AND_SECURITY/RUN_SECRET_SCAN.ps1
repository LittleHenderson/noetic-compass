param()

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$textExtensions = @('.md', '.txt', '.json', '.py', '.ps1', '.sh', '.tex', '.gitattributes', '.yaml', '.yml', '.toml', '.ini', '.cfg')
$patterns = [ordered]@{
    private_key = '-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'
    aws_access_key = '\b(?:AKIA|ASIA)[0-9A-Z]{16}\b'
    github_token = '\bgh[pousr]_[A-Za-z0-9]{20,}\b'
    huggingface_token = '\bhf_[A-Za-z0-9]{30,}\b'
    openai_style_secret = '\bsk-[A-Za-z0-9][A-Za-z0-9_-]{19,}\b'
    bearer_credential = '(?i)\bBearer\s+[A-Za-z0-9._~-]{20,}'
    credential_url = 'https?://[^/\s:@]+:[^@\s/]+@'
    named_secret_assignment = '(?im)^\s*(?:RUNPOD_API_KEY|HF_TOKEN|HUGGING_FACE_HUB_TOKEN|OPENAI_API_KEY|AWS_SECRET_ACCESS_KEY|DATABASE_URL|POSTGRES_PASSWORD|STRIPE_SECRET_KEY)\s*[:=]\s*(?!<|CHANGEME|YOUR_|example|placeholder|REDACTED|\$\{)[^\s#]{8,}'
}

$findings = @()
$filesScanned = 0
foreach ($file in Get-ChildItem -LiteralPath $root -Recurse -File -Force) {
    if ($textExtensions -notcontains $file.Extension.ToLowerInvariant() -and $file.Name -ne '.gitattributes') { continue }
    $filesScanned++
    $content = Get-Content -Raw -LiteralPath $file.FullName -ErrorAction Stop
    foreach ($entry in $patterns.GetEnumerator()) {
        $count = [regex]::Matches($content, $entry.Value).Count
        if ($count -gt 0) {
            $findings += [pscustomobject]@{
                relative_path = $file.FullName.Substring($root.Length).TrimStart('\').Replace('\', '/')
                category = $entry.Key
                match_count = $count
            }
        }
    }
}

$suspiciousNames = @(Get-ChildItem -LiteralPath $root -Recurse -File -Force | Where-Object {
    $_.Name -match '(^\.env$|^\.env\.(?!example$)|id_rsa|id_ed25519|\.pfx$|\.p12$|\.pem$|\.key$|credentials\.json$)'
} | ForEach-Object { $_.FullName.Substring($root.Length).TrimStart('\').Replace('\', '/') })

$suspiciousArchiveMembers = @()
Add-Type -AssemblyName System.IO.Compression.FileSystem
foreach ($archive in Get-ChildItem -LiteralPath $root -Recurse -File -Filter '*.zip') {
    $zip = [System.IO.Compression.ZipFile]::OpenRead($archive.FullName)
    try {
        foreach ($entry in $zip.Entries) {
            if ($entry.FullName -match '(^|/)(\.env($|\.)|id_rsa|id_ed25519|[^/]+\.(?:pfx|p12|pem|key)$|credentials\.json$)') {
                $suspiciousArchiveMembers += [pscustomobject]@{
                    archive = $archive.FullName.Substring($root.Length).TrimStart('\').Replace('\', '/')
                    member = $entry.FullName
                }
            }
        }
    } finally {
        $zip.Dispose()
    }
}

$status = if ($findings.Count -eq 0 -and $suspiciousNames.Count -eq 0 -and $suspiciousArchiveMembers.Count -eq 0) { 'SECRET_SCAN_PASS' } else { 'SECRET_SCAN_REVIEW_REQUIRED' }
[pscustomobject]@{
    status = $status
    text_files_scanned = $filesScanned
    high_confidence_pattern_findings = $findings
    suspicious_file_names = $suspiciousNames
    suspicious_archive_members = $suspiciousArchiveMembers
    note = 'Match values are deliberately never printed.'
} | ConvertTo-Json -Depth 8

if ($status -ne 'SECRET_SCAN_PASS') { exit 2 }
