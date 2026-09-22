# Q4 preparation — 2026-09-22

The current Q4 plan passes deterministic preparation and the real signature-library check. **A18 / real Q4 remains NOT_RUN.** No model was loaded, Torch was not imported, CUDA execution was not probed, and no training output directory was created. No applicable signed Q4 resource authorization was found in the reviewed records. The GPU process query also reported existing compute processes; this is not a ready-to-launch receipt.

This document records preparation, not an owner approval, run certificate, or result. The separate recorded Helm viewer uses retained Helm 2 development predictions. Those are not Q4 outcomes.

## Exact retained evidence

- `plan.json`: canonical plan SHA-256 `af81383702c9695ae00ba831eac2ae9f28891d40eaa8075b90d3857723d0aa87`. This is the digest of canonical JSON used by the authorization verifier, not the hash of pretty-printed file bytes.
- `preparation_verification.json`: observed `2026-09-22T15:41:06.163424+00:00`; metadata revalidation PASS, actual cryptography import PASS, public RFC8032 test-vector verification PASS, neural execution NOT_RUN, CUDA NOT_PROBED, GPU NOT_IDLE_OR_UNKNOWN, proposed output absent.
- `dependency_manifest.json`: full 166-file inventory, 11,233,284 bytes, manifest SHA-256 `1b59d30cabc5635cc5c7344b722b2a4f8de76abfd724d1fc3b72f3837e12fa74`.
- `deterministic_tests_short_path.txt`: **107 passed in 2.20 seconds**. Earlier 92- and 105-test receipts are preserved under their original names; the 107-test receipt is current.
- `requirements-auth.txt`, the two dependency-install logs, and `verify_preparation.py` preserve dependency setup and verification. Runtime packages are ignored by Git; they are not vendored source.

The signature test uses only the public key, public signature, and empty message from [RFC 8032 section 7.1, TEST 1](https://www.rfc-editor.org/rfc/rfc8032.txt). It generates no key or signature and supplies no owner identity or authorization.

## Proposed local job, still unauthorized

| Field | Prepared value |
| --- | --- |
| Purpose | `T14_R1_G_ENGINEERING_SMOKE`; not a claim-bearing study |
| Interpreter | `C:\Users\wakil\venvs\cas-gpu\Scripts\python.exe`, Python 3.14.0 |
| Static Torch metadata | `2.11.0+cu128`, CUDA build 12.8; runtime not exercised |
| Observed device | CUDA index 0; NVIDIA GeForce RTX 4070 Laptop GPU; 8188 MiB |
| Observed UUID | `GPU-7cfee18b-e83d-b6fb-a946-ae444b329fdd` |
| Data | Pinned `q3_v0_7`, family G, train and development only |
| Seed / width | 20260921 / 64 |
| Maximum rows | 2048 train, 16 development |
| Maximum optimizer updates | 128 |
| Maximum wall time | 1800 seconds |
| Concurrency / repeats | One job; no automatic retry, resume, extra seed, or sweep |
| Output | This record directory's `q4_smoke_output`; currently absent |
| Numerical policy | CUDA float32 deterministic or fail; no CPU fallback |
| Cloud / paid API | No launcher or new permission; no spend authorized by this preparation |
| Evaluation custody | `EVALUATION_NOT_INDEPENDENT` |

The signed plan binds absolute interpreter/data/output paths, source/data/dependency hashes, `cuda:0`, and limits. The hardware UUID above is an observation in the separate receipt, not a signed plan field. No monetary ceiling or cloud machine is encoded in this local-only plan. Local computation is not described as resource-free. GPU process IDs were nonempty at verification; nothing was stopped or taken over.

The existing R1 code is a real CUDA GRU encoder/decoder implementation with a numeric bottleneck, but it has not been run here. Its output codec covers G `StateLiteral` and PLUS/TIMES `BinaryExpr` trees. It does **not** implement T15 learned operation prediction. R2 has interfaces rather than a trained implementation. Q4 held-out neural results, fresh-process neural checkpoint reload, operation/benefit claims, and independent final-evaluation custody remain open. No protected final targets were opened for this preparation.

## Permission findings and exact remaining owner action

The bounded review covered the current `codex-helm-data` baseline (`5b3d713c`), the new `codex-rpa-recorded-run` checkout, the original `helm3-lab` branch at `86ba3d75431c56147f229f24794805a3d8504f76`, their Q4 records, and relevant tracked main-repository references. This is not a claim that every file on the computer was searched.

`research/helm_cas_expression_lab/EXECUTION_AUTHORIZATION.working.json` remains `PREPARED_PENDING_OWNER_WORD`: local neural work is `PENDING_OWNER_WORD`; cloud is `NOT_NEWLY_AUTHORIZED`. Its suggested RTX 4070 caps came from an owner-side draft explicitly awaiting adoption. They are not an independent grant.

`OWNER_DECISIONS_20260921.json` records the owner's AWS preference because the laptop overheats/stalls. Its specifically named authorization covers a different CPU rescoring job: one c7i.2xlarge in us-west-2, 90 minutes, a $2 ceiling, and that job only. The file's historical price and OD-7 budget context are not reused as current Q4 permission or current provider pricing. The owner's instruction to continue only on actually authorized resources does not grant a new machine or new spend.

**The owner must personally supply the applicable job authorization and its pre-established trust anchor.** For this proposed local job, that means adopting the exact plan and scope above, providing the existing owner public-key file and independently established SHA-256 fingerprint, and supplying an unexpired Ed25519-signed job record for this plan digest. Neither an agent-generated key nor a newly invented approval can establish that identity. If AWS is intended, this local plan must be replaced by a separately prepared, owner-authorized cloud machine/job/time/cost/retry plan; there is no Q4 cloud launcher in the current preparation.

The existing verifier expects exactly `schema`, `plan_sha256`, `expires_utc`, and `signature_base64`. The schema is `helm-cas-expression-lab.q4-signed-job/0.1`. It verifies the signature over canonical JSON of the first three fields, including an unexpired timezone-aware deadline. The raw Ed25519 public-key file must be 32 bytes and outside the job's source/data/output trees. Its SHA-256 must match the fingerprint independently established by the owner. The code verifies scope and cryptography; it cannot establish human ownership of an arbitrary key.

## Reproduction and conditional execution

These PowerShell variables name the actual checkout and short dependency directory:

```powershell
$base = 'C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE'
$cn = Join-Path $base '_worktrees\codex-rpa-recorded-run\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE'
$lab = Join-Path $cn 'research\helm_cas_expression_lab'
$record = Join-Path $cn 'records\rpa_recorded_helm_20260922\q4_preparation'
$deps = Join-Path $base '_runtime\q4_auth_20260922'
$gpuPython = 'C:\Users\wakil\venvs\cas-gpu\Scripts\python.exe'
```

The exact current deterministic test command is:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
Remove-Item Env:\HELM_Q4_AUTH_DEPENDENCY_DIR -ErrorAction SilentlyContinue
Remove-Item Env:\PYTHONPATH -ErrorAction SilentlyContinue
Set-Location -LiteralPath $lab
& 'C:\Python314\python.exe' -m pytest -q -p no:cacheprovider --noconftest test_learner_q4.py test_q4_followup.py test_q4_preparation.py --basetemp (Join-Path $base '_test_runs\q4_preparation_short_path_20260922')
```

These tests use symbolic records, fake model/checkpoint objects, and test-only signatures. They do not prove CUDA training readiness. The new cases bind dependency path, contents, extra files, package origin and homebase containment; reject invalid paths/budgets; show changed dependencies invalidate a prepared plan; and distinguish CPU versus CUDA builds through bounded literal version-file reads.

To rebuild missing dependencies into an **absent** short directory, use the pinned requirements below. Do not install over a signed dependency tree. A fresh installation may change file bytes; compare the entire manifest and prepare a new versioned plan if any identity changes.

```powershell
if (Test-Path -LiteralPath $deps) { throw 'Preserve the existing bound dependency directory.' }
& 'C:\Python314\python.exe' -m pip install --target $deps --only-binary=:all: --no-compile --no-cache-dir --disable-pip-version-check --retries 0 -r (Join-Path $record 'requirements-auth.txt')
```

The successful metadata verification used the following environment and command. The script creates its three output files exclusively; rerunning against this completed record will refuse to overwrite them. Preserve these receipts and use a new versioned record for a fresh preparation.

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONPATH = $deps
$env:HELM_Q4_AUTH_DEPENDENCY_DIR = $deps
& $gpuPython (Join-Path $record 'verify_preparation.py')
```

Only after the owner-supplied authorization, key, fingerprint, machine scope and availability are established, the existing gated execution command is below. The three `$owner...` variables are intentionally not assigned here. This command was **not** run. The supervisor checks the plan, authorization and GPU availability, reserves one output, and enforces the wall limit; it does not stop another process or retry a failed job.

```powershell
& $gpuPython (Join-Path $lab 'q4_smoke_job.py') execute --plan (Join-Path $record 'plan.json') --authorization $ownerSignedJob --trusted-public-key $ownerPublicKey --trusted-key-sha256 $ownerPinnedFingerprint
```

## Failures preserved and corrected

1. The historical `records/continuation_20260921/Q4_PREPARED_PLAN.json` was stale: its normalized `q3_behaviour_records.py` pin was `c377f130b5ab4b4d03a80934f617b6f0e0c2e4bd444acac2e0312295ce5496e4`, while current bytes hash to `5b3e03cd3b8bc1eac044e30b99781c0e1229e1039f5775b52848582055473787`. It also selected `C:\Python314\python.exe`; static inspection found that interpreter's Torch build was `2.11.0+cpu`. Distribution version alone was inadequate. The historical plan remains preserved.
2. The selected GPU environment had the CUDA Torch build but no cryptography package. The initial local dependency download failed with socket `WinError 10013`; `dependency_install.txt` retains that failure. The permitted network retry succeeded and is retained in `dependency_install_network_retry.txt`. No existing GPU environment packages were changed.
3. An intermediate metadata-only plan with missing cryptography is preserved as `plan_before_dependency_setup.json` and `prepare_before_dependency_setup.json`; it is superseded and must not be authorized. The child agent's old restricted context subsequently could not read the installed files. Root could read them; no ACLs were changed.
4. Root's actual cryptography import from the deeply nested checkout failed with `ImportError: DLL load failed while importing _cffi_backend: The filename or extension is too long.` The dependency copy was preserved and copied to the shorter `$deps` directory inside the outer CNCM homebase. The runtime binding now permits that homebase-contained location while preserving exact path/byte/package-origin checks. This fixed the import.
5. A verification-script public-signature literal had an extra hex digit, causing `ValueError` in `bytes.fromhex` before any plan was written. The literal was corrected against RFC 8032's four exact lines, verified separately with the GPU interpreter, and then passed in the final receipt. This was our transcription error, not an owner-authorization failure.
6. A steering-message interruption left one attempted command running from the wrong working directory; it did not run a model or create a Q4 result. Final commands use explicit paths and retained outputs.

File identity and a successful signature-library import do not establish CUDA capability, idle capacity, owner identity, or protection against every possible same-size concurrent file modification. Source pins and dependency revalidation narrow those risks; no broader readiness claim is made.
