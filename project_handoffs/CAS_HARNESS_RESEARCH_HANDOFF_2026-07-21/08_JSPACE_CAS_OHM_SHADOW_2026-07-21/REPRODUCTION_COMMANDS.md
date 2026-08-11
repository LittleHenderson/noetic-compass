# Reproduction commands

Run these commands in PowerShell. They verify the saved source bundle and
receipt; they do not require a GPU.

## 1. Verify file hashes

    Set-Location "C:\Users\wakil\OneDrive\Desktop\tksCAS\project_handoffs\CAS_HARNESS_RESEARCH_HANDOFF_2026-07-21\08_JSPACE_CAS_OHM_SHADOW_2026-07-21"
    Get-FileHash -Algorithm SHA256 ".\cas-jspace-ohm-shadow-de1a117d.bundle"
    Get-FileHash -Algorithm SHA256 ".\research_shadow_baseline_final.json"

Expected:

- bundle:
  13034E27046C689AA1FE8AEC12959D2D94C58A601AB9C49014AE4335B70C68CD
- receipt file:
  308673144C7A373EEE3666B3D95DD70559A843D23FE6069741020FB7C29EB99D

## 2. Verify and inspect the Git bundle

    git bundle verify ".\cas-jspace-ohm-shadow-de1a117d.bundle"
    git bundle list-heads ".\cas-jspace-ohm-shadow-de1a117d.bundle"

The bundle must report complete history and head:

    de1a117d028e655840931e9702911c1967a3d6a4 refs/heads/codex/jspace-ohm-shadow-20260721

## 3. Inspect the result without running code

    $receipt = Get-Content -Raw ".\research_shadow_baseline_final.json" |
        ConvertFrom-Json
    $receipt |
        Select-Object schema_version, execution_mode, verdict_influence,
            claim_status, claim_eligible, receipt_content_sha256 |
        Format-List
    $receipt.method_assessments |
        Select-Object method, status |
        Format-Table -AutoSize

Expected method statuses:

- JSPACE_CORRESPONDENCE_V0 — BASELINE_ONLY
- JACOBIAN_LENS_V0 — NOT_COMPUTABLE_FROM_ACTIVATION_ONLY
- CAS_OHM_RESPONSE_PROFILE_V0 — BASELINE_ONLY

## 4. Re-run the final baseline

Clone the bundle into a separate verification directory, install the worker
requirements in a clean Python environment, and run this one-line command from
the live-trace-worker directory:

    python scripts\run_research_shadow_baseline.py --input-artifact "PATH_TO\tks_definition_anchor_raw_diagnostic_vectors.npz" --expected-sha256 454a4f017d56ed393e50d7e88d29486b3379e96ae930a1123698c6275298ead6 --code-revision de1a117d028e655840931e9702911c1967a3d6a4 --code-bundle "PATH_TO\cas-jspace-ohm-shadow-de1a117d.bundle" --expected-code-bundle-sha256 13034e27046c689aa1fe8aec12959d2d94c58a601ab9c49014ae4335b70c68cd --output ".\research_shadow_baseline_reproduced.json" --enable-shadow

The created_at timestamp will differ, so the whole receipt file hash and
content hash will differ on a new run. The fixed model/artifact/code identity,
method statuses, and claim boundaries must agree.
