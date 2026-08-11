param(
  [switch]$AlreadyElevated
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$evidenceDir = Join-Path $repoRoot "evidence_runs\docker_desktop_install\latest"
$evidencePath = Join-Path $evidenceDir "docker_desktop_install_attempt.json"
$wingetArgs = @(
  "install",
  "--id",
  "Docker.DockerDesktop",
  "-e",
  "--accept-package-agreements",
  "--accept-source-agreements",
  "--silent",
  "--disable-interactivity"
)

function Test-IsAdministrator {
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($identity)
  return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Write-DockerInstallReport {
  param(
    [string]$Status,
    [bool]$Success,
    [string]$Detail,
    [Nullable[int]]$ReturnCode,
    [string]$WingetPath,
    [bool]$AdminElevationRequired
  )

  New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null
  $report = [ordered]@{
    report_kind = "cas_forex_docker_desktop_install_attempt"
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    status = $Status
    success = $Success
    detail = $Detail
    install_command = "winget $($wingetArgs -join ' ')"
    elevated_install_command = "npm --prefix ui run mobile:docker-install-elevated"
    winget_path = $WingetPath
    winget_id = "Docker.DockerDesktop"
    returncode = $ReturnCode
    elapsed_ms = 0
    stdout = ""
    stderr = ""
    admin_elevation_required = $AdminElevationRequired
    written_path = $evidencePath
  }
  $report | ConvertTo-Json -Depth 5 | Set-Content -Path $evidencePath -Encoding UTF8
}

$winget = Get-Command winget.exe -ErrorAction SilentlyContinue
if (-not $winget) {
  Write-DockerInstallReport `
    -Status "winget_unavailable" `
    -Success $false `
    -Detail "winget is not available, so Docker Desktop cannot be installed by this elevated helper." `
    -ReturnCode $null `
    -WingetPath "" `
    -AdminElevationRequired $false
  exit 1
}

if (-not (Test-IsAdministrator)) {
  $argsForElevatedPowerShell = @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    "`"$PSCommandPath`"",
    "-AlreadyElevated"
  )
  Start-Process -FilePath "powershell.exe" -ArgumentList $argsForElevatedPowerShell -Verb RunAs -WindowStyle Normal
  Write-DockerInstallReport `
    -Status "elevation_prompt_started" `
    -Success $false `
    -Detail "Windows UAC elevation prompt was launched for Docker Desktop install. Approve the prompt, then rerun Docker diagnosis after Docker Desktop starts." `
    -ReturnCode $null `
    -WingetPath $winget.Source `
    -AdminElevationRequired $true
  Write-Host "Docker Desktop elevated installer prompt launched. Approve UAC, then run npm --prefix ui run mobile:docker-check."
  exit 0
}

$process = Start-Process -FilePath $winget.Source -ArgumentList $wingetArgs -Wait -PassThru -WindowStyle Normal
$exitCode = $process.ExitCode
$success = $exitCode -eq 0
$status = if ($success) { "installed_or_started" } else { "install_failed" }
$detail = if ($success) {
  "Docker Desktop elevated install command completed. Start Docker Desktop if the engine is still unavailable, then rerun Docker diagnosis."
} else {
  "Docker Desktop elevated install command failed with exit code $exitCode."
}

Write-DockerInstallReport `
  -Status $status `
  -Success $success `
  -Detail $detail `
  -ReturnCode $exitCode `
  -WingetPath $winget.Source `
  -AdminElevationRequired $false

exit $exitCode
