# CAS Gate 5 — Step 4 capsule upload map (turnkey, collision-safe)

Step 4 streams the 14-file sealed surface into CloudShell one file at a time
(CloudShell `$HOME` is 1 GB; the surface is ~1.05 GB, so it can never all sit there
at once). **Eight of the transfer files are all named `part-0000.bin`** — they only
differ by their chunk directory — so uploading the wrong one for a given
`NEXT_RELATIVE` silently corrupts the run. This map pairs each **exact local source
file** to its **`NEXT_RELATIVE`**, in the exact order `03`'s `jq` list prints them, so
there is no guesswork.

Local source root (verified present, sizes match the sealed manifest):
`D:\tksCAS-archive\project_coherence_gate5_cloud_windows_source_capsule_20260815\`
Verifier wrapper (Step 4c) source:
`D:\tksCAS-archive\project_coherence_gate5_aws_full_verifier_20260815\invoke_gate5_aws_full_verifier.ps1`

Surface accounting (matches the runbook exactly): 12 transfer files = 1,049,723,574 B;
+ manifest 18,311 B + seal 88 B = **1,049,741,973 B across 14 files**.

## 4a — `03 init` (manifest + seal)

Upload `manifest\capsule_manifest.json` (18,311 B) and `manifest\capsule_manifest.sha256`
(88 B) to `$HOME`, then run the Step-4a block from the runbook. (These two have unique
names — no collision.) The positional manifest hash is
`61F8182BE31830ED4A897DE0B2564085AD7BE05E826AFC65E9B6A0EBF3D15097`; `init` also enforces
manifest bytes = 18311, seal bytes = 88, seal sha256
`A3D38D6E36417530BBFBDE7791E9BEE4BF16FF65306686AC45D97B12964E5D55`.

## 4b — the 12 transfer files, in order

For each row: (1) in the CloudShell **Upload file** UI, upload **only** the one local
file in column "Upload this local file" — it lands as `$HOME/<basename>`; (2) run the
Step-4b block with `NEXT_RELATIVE` set to the value in that row; (3) it moves → uploads
to S3 → deletes locally; (4) then upload the next row. **One at a time — never two
`part-0000.bin` in `$HOME` together.**

| # | Upload this local file (under the capsule root) | Lands as `$HOME/…` | Set `NEXT_RELATIVE` to | Bytes |
|--:|---|---|---|--:|
| 1 | `metadata\GATE5_LOCAL_WINDOWS_TEST_RUNNER_LOCK_v0.1.json` | `GATE5_LOCAL_WINDOWS_TEST_RUNNER_LOCK_v0.1.json` | `metadata/GATE5_LOCAL_WINDOWS_TEST_RUNNER_LOCK_v0.1.json` | 121,525 |
| 2 | `scripts\materialize_unarmed.ps1` | `materialize_unarmed.ps1` | `scripts/materialize_unarmed.ps1` | 40,485 |
| 3 | `scripts\verify_capsule.ps1` | `verify_capsule.ps1` | `scripts/verify_capsule.ps1` | 13,972 |
| 4 | `chunks\gate4-live-sources\part-0000.bin` | `part-0000.bin` | `chunks/gate4-live-sources/part-0000.bin` | 3,741,068 |
| 5 | `chunks\git-runtime\part-0000.bin` | `part-0000.bin` | `chunks/git-runtime/part-0000.bin` | 175,506,159 |
| 6 | `chunks\powershell-runtime\part-0000.bin` | `part-0000.bin` | `chunks/powershell-runtime/part-0000.bin` | 120,794,759 |
| 7 | `chunks\python-site\part-0000.bin` | `part-0000.bin` | `chunks/python-site/part-0000.bin` | 2,107,422 |
| 8 | `chunks\python-runtime\part-0000.bin` | `part-0000.bin` | `chunks/python-runtime/part-0000.bin` | 40,184,260 |
| 9 | `chunks\exact-six\part-0000.bin` | `part-0000.bin` | `chunks/exact-six/part-0000.bin` | 85,005 |
| 10 | `chunks\tracked-overlay\part-0000.bin` | `part-0000.bin` | `chunks/tracked-overlay/part-0000.bin` | 4,844,383 |
| 11 | `chunks\source-bundle\part-0000.bin` | `part-0000.bin` | `chunks/source-bundle/part-0000.bin` | 536,870,912 |
| 12 | `chunks\source-bundle\part-0001.bin` | `part-0001.bin` | `chunks/source-bundle/part-0001.bin` | 165,413,624 |

Notes:
- Rows 4–12 all land as `part-0000.bin` (except row 12 = `part-0001.bin`). The `03 object`
  block derives `UPLOADED_BASENAME` from `NEXT_RELATIVE`, so what matters is that the file
  physically in `$HOME` is the correct one for the row you are running.
- Row 11 is the biggest single file (512 MiB) — it fits under the 1 GB home, but upload it
  alone with nothing else staged.
- After all 12, run `03 verify` (re-downloads all 14 by immutable version id and re-hashes).
  On success `capsule.status=UPLOADED_HASH_VERIFIED_UNMATERIALIZED`.

## 4c — successor wrapper

Upload `invoke_gate5_aws_full_verifier.ps1` (141,548 B) to `$HOME`, then run the Step-4c
block. Positional hash `2501FF2487995670C45101AE1480E083B64338549859E97DF3445FF8A34D837A`;
bytes must equal 141548. This is the last step before any compute.

---

**Session note:** these pre-compute uploads run inside the Step-1 provisioner child. If the
one-hour session runs low mid-loop, exit → re-export `CAS_BILLING_ATTESTATION` → rerun `00`
→ resume at the next un-uploaded row (re-running `03 object` on an already-present matching
object is safe; `uploaded-objects.json` records what is already verified).
