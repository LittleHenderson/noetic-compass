# Reproduction policy for option C — revision 1, fixed before running

Status: PROPOSED_FOR_FINAL_PLAN; no reproduction run or new result has been read by this preparation. This policy replaces the proposed raw-file-only admission rule prospectively. It does not relabel any historical file comparison or change OFF-preservation requirements.

The original unchanged model is source 20208c923d41c24614504d4ecc2b289ecb66eda8, seed 20260917. Freeze the policy, reader source, environment, reference artifacts and output-panel manifest in the final launch manifest before any comparison run. If any relevant result has already been inspected before that freeze, disclose it and require a new prospective registration; do not present this revision as a rule fixed before that result.

| Dimension | Exact requirement | Meaning |
|---|---|---|
| Checkpoint file | Preserve original bytes and SHA-256 for both files; compare them directly. | FILE_IDENTICAL or FILE_DIFFERENT. A difference is never erased or reported as byte reproduction. |
| Learned state | Independently recompute equality of all model state_dict keys, tensor shapes, dtypes, layouts and logical value bytes, including persistent buffers, plus encoder/vocabulary state and prediction-affecting configuration. No tolerance, rounding, missing-key allowance or dtype conversion. | LEARNED_STATE_IDENTICAL or LEARNED_STATE_DIFFERENT. File-container layout and elapsed time are not model parameters. |
| Output panel | Same pinned public historical course/held-back panel, exact record IDs/order, full decoded answers, explicit refusal/error status and historical grader flags. Compare every record, not aggregate accuracy. | OUTPUT_REPRODUCED or OUTPUT_DIFFERENT. This establishes behavior only on that panel; it does not establish identical weights or arbitrary unseen outputs. |
| Training continuation | Separately compare optimizer tensors/scalars, every saved RNG stream, cursor/model revision and training counters, together with compatible numerical environment. | CONTINUATION_IDENTICAL or CONTINUATION_DIFFERENT. No trajectory or restart-equivalence claim unless all required state and environment match. |

The final manifest must pin the complete output-panel inputs and historical reference answers before execution. No HSET-2 TEST question, salt, answer or digest that reveals a small-space answer is used for this panel. Missing panel pins are a launch blocker. A panel cannot be reduced after a mismatch. Failed/refused records remain records; only explicitly registered expected refusals compare as equal.

Current code independently supports these separate identities: the historical export_checkpoint procedure writes elapsed_seconds, run identity/context, device/root, counters and model/optimizer/encoder/RNG states into final.pt, and exposes state identity fields. Do not trust those fields without recomputing them from the checked checkpoint bytes on AWS. Hashes identify artifacts; they do not alone prove a trustworthy producer. Inspection/loading must use the pinned historical loader and a reviewed evidence reader. Never execute an untrusted checkpoint on the laptop.

Exclude only declared non-predictive envelope fields from learned-state equality: file path, root, elapsed time, storage/container layout, run identifier and administrative limits. Retain and report all their differences. Architecture, switch state, number of rounds, encoder/vocabulary mapping, normalization settings and inference mode are predictive configuration and must match. Training-configuration or software differences are disclosed and fail the environment-admission check unless equivalence was explicitly registered before any reading; this revision grants no such exception.

**Admission decision fixed now:**

1. Validate all immutable artifact/input/source pins, checkpoint schema/integrity, full state inventory and numerical environment. Any missing evidence or invalid reference yields ADMISSION_INVALID, stops the study and authorizes no fallback job.
2. If learned state and the complete output panel both match, admit C as STATE_AND_PANEL_REPRODUCED_FOR_ONE_SEED. Report FILE_IDENTICAL/FILE_DIFFERENT and continuation status separately. No optimizer/RNG mismatch is hidden; C makes no trajectory-reproduction claim.
3. If evidence is valid but learned state or any required output differs, label DOES_NOT_REPRODUCE_UNDER_REGISTERED_STATE_POLICY. Preserve exact differences. C's two unreplicated historical controls cannot be admitted under this policy; the proposed fallback is two additional fresh unchanged seeds, only if the final approved job count, pre-job headroom and stop rules allow them. Otherwise stop with COMPARISON_INCOMPLETE.
4. Output agreement never overrides a learned-state mismatch. A learned-state match never overrides an output mismatch. No tolerance may be introduced after results are read. An investigation may explain a mismatch but does not change the registered outcome.

B is the stronger fresh-control comparison: three fresh unchanged seeds versus three repaired seeds. C contains one fresh/reproduced historical-control seed and two reused historical controls. One successful reproduction supports only that seed and setup. Neither outcome establishes that every earlier receipt is true or false.

The actual reader and its public equal-state/different-envelope, changed-value, changed-buffer, missing-key, dtype-change, altered-output and corrupt-reference checks must be implemented, reviewed and run on AWS before the main comparison. They are NOT_RUN in this preparation; this document supplies the policy, not a fabricated reader acceptance.
