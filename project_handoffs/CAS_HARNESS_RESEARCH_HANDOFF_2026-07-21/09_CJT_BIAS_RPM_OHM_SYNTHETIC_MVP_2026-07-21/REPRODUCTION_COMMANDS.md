# Reproduce Without an LLM (Windows PowerShell)

## 1. Set paths

```powershell
$Handoff = "C:\Users\wakil\OneDrive\Desktop\tksCAS\project_handoffs\CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21\09_CJT_BIAS_RPM_OHM_SYNTHETIC_MVP_2026-07-21"
$Checkout = "C:\tmp\cas_cjt_ohm_repro_25053461"
$Venv = "C:\tmp\cas_cjt_ohm_venv_20260721"
```

## 2. Verify bundle

```powershell
Get-FileHash -Algorithm SHA256 "$Handoff\CAS_HARNESS_CJT_OHM_SYNTHETIC_25053461.bundle"
Test-Path $Checkout
```

Expected SHA-256:
`28CB29B80E27DD1E13E86E9C889B13A6963CE48DE40C65703A75BB23E0CCF8BF`.
Continue only if `Test-Path $Checkout` prints `False`, then extract the exact
commit from the complete bundle:

```powershell
git clone --branch codex/jspace-ohm-synthetic-20260721 "$Handoff\CAS_HARNESS_CJT_OHM_SYNTHETIC_25053461.bundle" $Checkout
Set-Location $Checkout
git bundle verify "$Handoff\CAS_HARNESS_CJT_OHM_SYNTHETIC_25053461.bundle"
git checkout --detach 25053461c94de23850da7f9c853c420aab1bae62
git rev-parse HEAD
$Worker = "$Checkout\noetic-compass-scaffold\noetic-compass\live-trace-worker"
```

`git rev-parse HEAD` must print
`25053461c94de23850da7f9c853c420aab1bae62`.

## 3. Create isolated environment

Use a new directory if `$Venv` already exists and is not trusted.

```powershell
python -m venv $Venv
& "$Venv\Scripts\python.exe" -m pip install --requirement "$Worker\research_requirements\CJT_BIAS_RPM_OHM_SYNTHETIC_V0.lock.txt"
& "$Venv\Scripts\python.exe" -I -c "import sys; print(sys.version)"
```

The version must begin with `3.14.0`.

## 4. Choose unused output

```powershell
$Output = "$Handoff\CJT_BIAS_RPM_OHM_SYNTHETIC_RECEIPT_REPRO_01.json"
Test-Path $Output
```

Continue only if it prints `False`. The runner never overwrites.

## 5. Run

```powershell
Set-Location $Worker
& "$Venv\Scripts\python.exe" -I scripts\run_cjt_ohm_synthetic_recovery.py `
  --code-revision 25053461c94de23850da7f9c853c420aab1bae62 `
  --code-bundle "$Handoff\CAS_HARNESS_CJT_OHM_SYNTHETIC_25053461.bundle" `
  --expected-code-bundle-sha256 28CB29B80E27DD1E13E86E9C889B13A6963CE48DE40C65703A75BB23E0CCF8BF `
  --output $Output `
  --seed 20260721 `
  --bootstrap-replicates 1000 `
  --enable-shadow
```

## 6. Inspect authority fields

```powershell
$Receipt = Get-Content -Raw $Output | ConvertFrom-Json
$Receipt.report.harness_status
$Receipt.execution_mode
$Receipt.verdict_influence
$Receipt.claim_status
$Receipt.claim_eligible
$Receipt.report.model_execution
Get-FileHash -Algorithm SHA256 $Output
```

Expected: `SYNTHETIC_HARNESS_MVP_PASS`, `SHADOW`, `NONE`,
`NOT_LICENSED`, `False`, `NONE_SYNTHETIC_ONLY`.

Do not call this a real-model, prompt-injection, output-control, universal,
cross-architecture, or 300B result.
