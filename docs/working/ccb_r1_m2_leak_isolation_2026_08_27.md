# CCB-R1 M2 leak-isolation finding

**Date:** 2026-08-27

**Status:** engineering instrumentation complete; diagnostic live rerun **NOT RUN**.

**Historical disposition:** M2 operational invariance **FAIL**; causal source
**OPEN**.

## What the first live artifact can and cannot show

The first Stage 5 artifact recorded 20/100 wrapped decision flips and movement
above the registered ceiling. It did not preserve pair IDs, raw replies, the
bare-arm report, or the exact outbound prompt hashes. It therefore establishes
an operational invariance failure but cannot localize the divergence or support
the claim that identity reached the model.

For all 100 registered pairs at seed `20260831`, the wrapped base and variant
prompts are byte-identical after exact-field redaction: **0/100 outbound prompt
mismatches**. The registered wrapped arm is therefore an A/A repeatability probe
at the model boundary. A later reply difference can be model/provider/transport
variability or downstream parsing behavior; it is not evidence of identity
leakage when the outbound bytes are identical.

The bare arm remains useful as a diagnostic control because its narrative keeps
the identity perturbation. M2 itself remains an absolute wrapped-arm ceiling,
not a post-hoc wrapped-minus-bare margin.

## Instrumentation added

Future result files now preserve, separately for wrapped and bare:

- flip counts plus `flipped_ids`;
- movement counts plus `over_ceiling_ids`;
- invalid/unreadable IDs and transport-failure IDs;
- complete-coverage status.

The wrapped arm additionally records, per pair and side:

- source-prompt and exact outbound-prompt SHA-256;
- exact identity fields removed and any exact residual fields;
- raw reply, parsed terminal, and parsed value;
- outbound equality, raw equality, parsed equality, and the first observable
  divergence class.

Unreadable or transport-hole coverage cannot pass M2 and cannot receive a
rule-of-three zero-flip bound. Diagnostics explicitly assign no causal
interpretation.

## Honest boundary

The live M2 path is currently:

`narrative render -> exact-span redaction -> model call -> numeric parse`

It does not run the RPM gate, dial adjustment, operator scoring, domain
coherence, or inversion scan. Exact-span checks also cannot detect semantic or
paraphrased identity cues. A test with a deliberately unregistered differential
cue proves that such a cue survives, produces different outbound hashes, and is
localized as `OUTBOUND_PROMPT_DIVERGENCE`.

## Verification and next action

The combined M1/M2/B4 integration branch passes `281/281` CCB-R1 tests,
`py_compile`, `git diff --check`, and the comparison-runner dry run.

The next M2 provider run must create a new result artifact with the new schema.
Do not reinterpret the historical 20/100 artifact after the fact. Until a new
run records the boundary evidence, the causal source remains **OPEN** and no
identity-leak claim is supported.
