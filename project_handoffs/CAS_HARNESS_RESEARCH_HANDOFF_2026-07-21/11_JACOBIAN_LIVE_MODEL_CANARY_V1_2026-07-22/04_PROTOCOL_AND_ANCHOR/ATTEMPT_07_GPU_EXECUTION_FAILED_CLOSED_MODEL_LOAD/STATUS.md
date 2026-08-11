# Attempt 7 guarded shadow canary — GPU execution, FAILED CLOSED at model load

Controlling status:

`OFFICIAL_SHADOW_ATTEMPT_FAILED_CLOSED_AT_MODEL_LOAD / PHASE_TWO_TSYNC_FIX_VALIDATED_IN_OFFICIAL_RUN / POST_GUARD_CUDA_PROOF_COMPLETED / MODEL_LOAD_CONFIG_ERROR_DIAGNOSED_AND_FIX_CONFIRMED / NO_AUTOGRAD_MEASUREMENT / ZERO_ARTIFACTS / SHADOW / NONE / NOT_LICENSED`

## What this run proves

Attempt 7 ran the guarded shadow canary on the repaired implementation
`88b59de9` (the `/proc/net/unix` churn fix) on research pod `zp2s9pscgncn0b`.
Run ID `jlcv1-rfc3161-09995d91...`. The one-shot DigiCert transmission
(query `8a323e83...`, 105 bytes; response `5641d58e...`; anchor receipt
`8a9443b6...`, verified, ts `Jul 24 03:08:29 2026 GMT`) and the guarded
canary executed under the owner's standing pre-authorization of 2026-07-23.

Crucially, the Attempt 6 blocker is now cleared IN THE OFFICIAL RUN:
`phase_two_full_tsync_installed_before_uvm_close_proven=true` and
`post_guard_cuda_proof_completed=true`. The `/proc/net/unix`
retry-until-stable fix works live, not only in the 13/13 pod validation.
Attempt 7 therefore advanced one full stage beyond Attempt 6 (which died at
phase two), which itself advanced beyond Attempts 4-5.

## Where it failed and why

Wrapper exit `0`, producer status `FAILED_CLOSED`, execution receipt
`f531be4fd0166a1fc0f94409b7d6ecf4ec2bfa7811f149a9c7f7d51df1f4c03e`, failure
stage `MODEL_LOAD` (`MODEL_LOAD_FAILURE`), zero artifacts, zero of 1,248
autograd calls. This is not a technical-canary pass, scientific result, or
`LICENSED` capability; claim status `SHADOW / NONE / NOT_LICENSED`, score
`0.33`.

Root cause (bounded non-official diagnostics, retained in `diagnostic/`):
`load_exact_pythia_runtime` calls `inventory_exact_model_snapshot`, whose
`_validate_model_snapshot_root` REQUIRES the model path to be the pinned
Hugging Face cache layout — `<...>/models--EleutherAI--pythia-160m/
snapshots/50f5173d932e8e61f858120bcb800b97af589f46` with a sibling
`blobs/`. The launch target-path mapping's `model_snapshot_root` instead
pointed at a FLAT convenience copy, `/workspace/cas-model-a8969eb7`, which
can never satisfy that name/layout check. It raised
`model snapshot path does not match the pinned Hugging Face cache identity`.

This is a CONFIGURATION error in the operator-built target-path mapping, not
a code defect, not a torch/transformers drift, and not a model-integrity
problem. It was latent in the mapping since the Attempt 4/5 design and was
never exercised because no prior attempt reached MODEL_LOAD. The frozen
implementation `88b59de9`, the anchored protocol, and the RFC3161 anchor are
all unaffected (the model path lives only in the post-anchor launch mapping).

## Confirmed fix

Set `model_snapshot_root` in the target-path mapping to the HF cache
snapshot path
`/workspace/cas-hf-cache/models--EleutherAI--pythia-160m/snapshots/50f5173d932e8e61f858120bcb800b97af589f46`.
Confirmed on the pod: `inventory_exact_model_snapshot` on that path returns
the exact 5 files, matches the frozen model manifest `files` AND
`files_sha256`, and `AutoModelForCausalLM.from_pretrained` loads
`GPTNeoXForCausalLM`. The isolated model-load + jlens-wrap +
`_validate_exact_model_and_lens` + `validate_deterministic_runtime` path all
pass; only the snapshot-root path was wrong.

## Next executable action

Because the guarded launch is create-once per official root and this root
holds the failed run's evidence, a corrected run is a fresh Attempt 8
identity on commit `88b59de9` with the corrected `model_snapshot_root`. The
frozen implementation and the guard fix carry forward unchanged; only the
operator target-path mapping value changes. Attempt 8 then proceeds through
model load into the canary execution stage (the 1,248 autograd calls and 213
artifacts), which has not yet been exercised and may surface further
torch 2.12 / transformers 5.9 interactions. A clean official canary PASS
earns Gate 1 (`0.38`). Attempt 1-7 identities are never reused.
