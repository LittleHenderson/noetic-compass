# OWNER AUTHORIZATION RECORD -- CJT-MECH-0 BUILD AND RUN (2026-09-03)

```
directive (verbatim, owner /goal)     "Build and run everything"
preceded by (owner /goal)             "approved, resume the ledger verification then design CJT-MECH-0"
issued by                             Little Henderson (owner), in the Claude Code session, 2026-09-03 (America/Los_Angeles)
recorded by                           the clean-room successor (Claude)
form                                  chat directive; no cryptographic signature (the owner's phase-approval schema
                                      exists in cjt_gate1a_static_neural_v1/OWNER_PHASE_APPROVAL.schema.json; this
                                      record is the executable stand-in and names its own limits)
```

## What is authorized

1. Build the FRW-1 world family, the mechanism-free baselines, the zero-cost kill gates K1-K11, the
   exact-search ceiling M8, the absorption test K8, the controller arms M0-M7 and M9, the training
   and evaluation harness, and the status program, as specified in
   `cas_only_reasoner/CJT_OHM_CLEANROOM/CJT_MECH_0_DESIGN_v0_2.md`, amended by the adversarial
   design review findings as they land.
2. Run the zero-cost gates on local CPU (dataset generation, enumeration, tiny numpy checks -- control-plane work).
3. If every kill gate passes: run the neural arms on AWS GPU (us-west-2) under a hard cost ceiling of
   **USD 15.00** for the development sweep and the single protected evaluation together, with
   auto-termination on every exit path, raw-result flush, and a receipt.
4. Dispatch a different-model-family audit of the result via AWS Bedrock (language-only).

## What stays forbidden (unchanged owner law)

- No neural training or inference on local CPU. Local GPU is smoke only.
- The protected split is opened once, by the frozen status program; no prose status.
- A failed kill gate returns `DO_NOT_BUILD` for the neural phase and this record does not override it.
- No status word stronger than `SUPPORTED_NARROWLY` enters the record without the independent audit.
- No merge to `master`; no rewriting of receipts; no deletion of negatives.

## Spend ledger for this authorization

| item | ceiling | actual |
|---|---|---|
| local CPU gates | $0 | $0 |
| AWS GPU dev sweep + protected eval | USD 15.00 | to be filled from the receipt |
| Bedrock audit | USD 1.00 | to be filled from the receipt |
