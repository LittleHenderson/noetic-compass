# Decoder comparison preparation — not launched

`cas_meta2/predict_viability_v4.py` is a separately versioned AWS-only predictor
for the existing v3 CAS and generic checkpoints. It accepts an explicit `v3` or
`viability_v4` grammar mode. Both use the same greedy decoding loop, input
features, learned scores, token vocabulary and action bounds. No weights are
trained or changed, and no parser, answer-based repair or fallback supplies a
program. The frozen v3 predictor remains unchanged.

The new entrypoint is pure on import and refuses missing job flags, CPU devices,
unregistered modes, invalid batches and unbounded execution before importing
neural modules. Actual inference still requires CUDA and refuses T4. A call is
limited to 96 public problems and 900 seconds. These are per-call bounds, not an
AWS spending cap; a future launcher must supply the independent job deadline,
budget reservation and real provider binding.

## Required comparison

Keep the initial and selected checkpoints from each family unchanged. Compare
both grammar modes on exactly the same permitted observations and model state.
First demonstrate that the `v3` mode matches the frozen predictor on actual
CUDA; then test the candidate mask. Report task correctness through the accepted
executor, program and binding correctness, grammar rejections, and compute.
Count every requested task, including rejected outputs.

A mask-only improvement is a decoding improvement, not evidence of additional
training. Compare trained against untrained under the same mask before making
a learning claim. The previous exposed test set may be used for a labelled
retrospective diagnostic, never presented as fresh held-out evidence. Fresh
evaluation needs separately registered, checked tasks and excluded prior graphs.

## Gates still open

- Actual CUDA parity of the new `v3` loop with the frozen predictor.
- Source-bound loading and byte preservation of all checkpoint candidates.
- GPU tests of both mask modes, including explicit rejections and time limits.
- A complete bounded launcher and evidence collector that does not generate
  pytest directory aliases inside its published payload. Keep link rejection.
- Budget reservation and current provider/quota checks before paid launch.
- Completed execution, stored semantic checks and cleanup evidence afterward.

Local tests only cover pure import/refusal paths and static absence of training
or semantic-parser calls. They do not prove CUDA parity, useful model behavior,
the full process-pair memory path, or release acceptance.

## Local verification record

`records/local_decoder_ablation_v4_001/receipt.json` reports 1,159 passed test
functions and 178 passed subtests, zero failures/errors, seven skipped GPU
modules and 216.0796434 seconds. All 101 source/config files and 316 protected
baseline files remained unchanged. A separate check confirmed all 461 files
from the frozen v3 launch package still match their hashes.

Rerun from META2, using a new output directory:

```powershell
C:/Python314/python.exe -B tools/validate_local_v3.py --output records/local_decoder_ablation_v4_002
```
