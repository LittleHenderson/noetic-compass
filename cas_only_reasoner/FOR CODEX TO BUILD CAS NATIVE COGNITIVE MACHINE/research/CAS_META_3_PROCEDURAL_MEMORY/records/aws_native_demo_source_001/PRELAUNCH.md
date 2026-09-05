# Native memory candidate: prelaunch record, not AWS execution

Source SHA: `8b5d8ac9e4f469b4cd89bbe917560678d2f52cb7`.
Separate memory branch: `codex/cas-meta-3-procedural-memory`, fast-forwarded
from `997815e63b6124d33b33ec88b930065ba41ec799` to that source commit.
No merge was performed.

Archive SHA256:
`f79e40602b9b0d3729d0f2b49dcf654bd4d0bd738107c8af7e6b9096b846aa5c`.
Archive bytes: 4,038,632. Manifest source files: 447. Protected files: 316.
The ZIP and builder receipt here are exact copies of the generated files in
META3 `runs`; the original receipt keeps its original absolute archive path.

The frozen source contains the complete `local_native_demo_002` receipt:
364 tests passed, zero failures/errors/skips. The only warning is an intentional
duplicate-ZIP fixture. All source hashes and protected bytes were unchanged.

Build command, executed from the META3 root:

```powershell
C:/Python314/python.exe -B tools/build_launch_bundle.py --output runs/cas-meta3-8b5d8ac9-native-demo.zip
```

Plan-only archive validation command (exit 0; captured stdout text in
`plan_stdout.txt`). Its Windows CRLF line endings were normalized to LF by the
artifact editor; the text was then compared with the captured output with only
that explicit normalization. It is not claimed to preserve original stream bytes.

```powershell
C:/Python314/python.exe -B aws/launch.py --archive runs/cas-meta3-8b5d8ac9-native-demo.zip --sha256 f79e40602b9b0d3729d0f2b49dcf654bd4d0bd738107c8af7e6b9096b846aa5c --source-sha 8b5d8ac9e4f469b4cd89bbe917560678d2f52cb7
```

Additional read-only checks called `source_checks(source_identity(), source_sha)`
and the outer inspector's `_trusted_launcher(launch_manifest, source_sha)`.
Both exited successfully against actual Git objects, with neural/provider
imports blocked. The source check covered 341 source/protected hashes including
all 316 protected baseline files. This paragraph records the observed tool
result; it is not a cloud execution receipt.

No new budget reservation or AWS write occurred in this prelaunch step. The
previous learning-v2 job remained active. A memory launch must wait for that
job's final evidence and cleanup, use the same ledger/$400 total cap, and retain
the source SHA above even if later evidence commits advance HEAD.
