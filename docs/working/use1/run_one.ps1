param([Parameter(ValueFromRemainingArguments=$true)][string[]]$PyArgs)
# One python worker at a time; wait (never kill) if another builder's worker.py is running.
$waited = 0
while ($true) {
  $others = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match 'worker\.py' }
  if (-not $others) { break }
  if ($waited -ge 600) { "WAITED 600 s for another worker.py; giving up this call"; exit 3 }
  Start-Sleep -Seconds 10; $waited += 10
}
$use1 = "C:\Users\wakil\Documents\Codex\2026-10-19\use1"
$p = Start-Process -FilePath "python" -ArgumentList (@("-B","-I","-X","utf8") + $PyArgs) -WorkingDirectory $use1 -PassThru -NoNewWindow
$peak = 0; $sw = [Diagnostics.Stopwatch]::StartNew(); $killed = ""
while (-not $p.HasExited) {
  try { $p.Refresh(); if ($p.PeakWorkingSet64 -gt $peak) { $peak = $p.PeakWorkingSet64 } } catch {}
  if ($sw.Elapsed.TotalSeconds -gt 295) { $p.Kill(); $killed = "KILLED_300S" }
  if ($peak -gt 300MB) { $p.Kill(); $killed = "KILLED_300MIB" }
  Start-Sleep -Milliseconds 250
}
$p.WaitForExit()
"RUN exit=$($p.ExitCode) seconds=$([math]::Round($sw.Elapsed.TotalSeconds,1)) peakMiB=$([int]($peak/1MB)) waited=$waited $killed"
