# How to Verify This Handoff

These instructions are written for a Windows PowerShell novice.

## One-command verification

1. Open PowerShell.
2. Copy and paste this command exactly:

```powershell
Set-Location "C:\Users\wakil\OneDrive\Desktop\tksCAS\project_handoffs\CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21"
```

3. Then run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\06_REPRODUCTION_GUIDES\BUILD_AND_VERIFY_MANIFEST.ps1" -VerifyOnly
```

The final line must say `HANDOFF_VERIFICATION_PASS`.

If it reports a mismatch, stop. Do not repair, rename, or overwrite the mismatched evidence. Record the exact error and compare the file with its original source.

## What the files mean

- `SHA256SUMS.txt` is the fingerprint list for every payload file.
- `MANIFEST.json` is the machine-readable inventory and source map.
- `MANIFEST.sha256` is the fingerprint for `MANIFEST.json` itself.

A SHA-256 match means the bytes are the same as when the handoff was sealed. It does not mean the scientific claim is true or production-ready.

## Critical manual spot checks

```powershell
Get-FileHash -Algorithm SHA256 ".\01_FROZEN_SOURCE\cas-tks-anchor-diagnostic-20260721-da00bd94.zip"
Get-FileHash -Algorithm SHA256 ".\02_RESEARCH_EVIDENCE\full_recovery\artifacts\full\tks_definition_anchor_raw_diagnostic_vectors.npz"
Get-FileHash -Algorithm SHA256 ".\02_RESEARCH_EVIDENCE\full_recovery\OFF_POD_VERIFICATION.json"
```

Expected hashes:

- Frozen ZIP: `CAEB3171D8F461E81AEB164888A41A7C33E105D2813A253DF25A833CC58A2E20`
- Raw NPZ: `454A4F017D56ED393E50D7E88D29486B3379E96AE930A1123698C6275298EAD6`
- Off-pod verification: `DB115601DF8F2984D56F6C9F5CDE09F598B77308ACD6CF978109583F375C2E9C`

## Rebuilding the manifest

Normally, do not rebuild it. Verification is read-only. Rebuild only after intentionally adding or refreshing handoff files:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\06_REPRODUCTION_GUIDES\BUILD_AND_VERIFY_MANIFEST.ps1"
```

After rebuilding, immediately run the `-VerifyOnly` command and document why the bundle changed.

