# Historical Qwen W0 Prompt-Injection Correction

Status: **CONTROLLING CORRECTION / OLD 14/14 PASS SUPERSEDED / SCOPED
LICENSE WITHDRAWN / FAIL / OPEN / NOT LICENSED**

## Corrected record

An older historical entry described the Qwen-1.5B hidden/encoded W0 result as
`PASS`, stated that all `14 / 14` gates passed, and treated a narrow internal
W0 claim as licensed. That statement is superseded.

The later exact re-audit added the previously missing character-level surface
baseline. The character model outperformed the hidden-state readout, so the
surface-margin control failed and the scoped license was explicitly withdrawn.

The controlling report is:

`noetic-compass-scaffold/noetic-compass/docs/working/hidden_prompt_injection_w0_large_v1_qwen_20260617/hidden_prompt_injection_prespeech_eval_large_v1_qwen_layer_18_parallel_20260617.json`

Source binding:

| Field | Exact identity |
|---|---|
| Correction commit | `25336f2c2b46c8b59a0fca6f06bb84ea0e190918` |
| Commit subject | `Withdraw scoped hidden prompt-injection W0 license (char-level control)` |
| Git blob | `eb5c5f99c08075aaad64a44dc183d51e1f485605` |
| Canonical Git-blob SHA-256 | `E297C9E0D35A54C5A4BE66F1668F17E55276D553987FD10696366A13EA910741` |
| Canonical Git-blob length | `4429` bytes |
| Observed Windows checkout SHA-256 | `FF395EE7DE2693262A582B6DD7A4A12D6ACDA69BB481A9B91428393FF98AD104` |
| Observed Windows checkout length | `4541` bytes |
| Checkout relation | `git diff --quiet` PASS; length/hash difference is checkout line-ending representation |
| Report schema | `cas_harness_hidden_prompt_injection_prespeech_eval.v1` |
| Report created_at | `2026-06-18T01:55:27.927556+00:00` |

The exact corrected findings are:

- report status: `FAIL`;
- report claim: `OPEN / NOT LICENSED for internal W0 prompt-injection detection`;
- hidden balanced accuracy: `0.896875`;
- character-text balanced accuracy: `0.925`;
- hidden minus character-text balanced accuracy: `-0.028125`;
- `char_text_margin_pass: false`;
- effective independent prompt count: `320`, despite `2560` replicated rows.

The report's own correction note states that the scoped license is withdrawn
because the character-level surface baseline equals or exceeds the hidden
readout. Other recorded metrics do not repair that failed mandatory control.

## Effect on Stage C

The superseded PASS must not be used as:

- positive evidence that a hidden prompt-injection detector exists;
- evidence that layer 18 is effective on the Stage C Qwen-0.5B candidate;
- a power or expected-effect assumption;
- a detector, threshold, direction, calibration, or steering artifact;
- authority to omit character-level, word-level, length, payload, taxonomy,
  carrier, or wrong-layer controls;
- support for prevention, blocking, removal, live interception, steering,
  product, licensing, public-release, or Gate 5 closure claims.

Its only permitted prospective use is as a **negative methodological prior**:

> A hidden-state claim is invalid unless it beats a strong character-level
> surface baseline on a surface-screened, group-disjoint design.

The Stage C candidate target at Qwen-0.5B layer 18 is therefore an unvalidated
prospective choice, not a transferred result. Stage C must fit its detector on
new disjoint calibration data and evaluate it prospectively with the mandatory
surface and wrong-layer controls.

This note does not rewrite the historical source report or retroactively alter
any prior receipt. The current Gate 5 manifest, verifier, review matrix, and
canonical production tracker may bind this correction prospectively while
preserving those historical bytes and their original status.
