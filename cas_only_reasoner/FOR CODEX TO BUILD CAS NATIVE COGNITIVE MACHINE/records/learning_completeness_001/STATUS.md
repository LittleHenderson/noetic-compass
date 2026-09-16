# Complete inventory in learner input

Status: PURE_DISCLOSURE_REGRESSION_CHECKS_COMPLETE.

The user's analogy-package review identified a remaining assumption gap. The
current adapter had already replaced old Facts prose with structural node/rel
lines, but its learner input still omitted the source's complete-inventory
declaration. Input contract 0.2 now carries that declaration in every question.

See docs/CNCM_LEARNING_INGESTION_v0.2.md for the contract. The generated example
checks_002/analogy_cloth_public.json shows precisely what the learner receives;
checks_002/analogy_cloth_teacher.json keeps the empty teacher answer separate.
The constant statement is preserved by the lossless tokenizer and becomes an
ordered framing line. Opening six faces still creates no extra lessons or
neural updates. Formal, contextual and analogy views preserve authored structure.

The initial guarded broad run had 260 passes and one failure in a synthetic test
fixture. The fixture asserted complete face inventories within an incomplete
context, so the existing source validator refused it before the intended adapter
check. Its correction marks those faces partial, then verifies refusal before
teacher compilation. The agent edited that fixture while the broad run was
active; checks_001 correctly records failure and source drift and is not final
acceptance. Its exact original test bytes are retained in fixture_fix_001.

The final focused run passed all 34 cases with stable inputs and no forbidden
imports. verification.json confirms the same production inputs across both
runs, only the fixture/helper changes, and all 205 final input pins. The final
run checks all 306 exposed view/operation/assistance combinations, the Cloth
empty answer, statement tampering, old-schema refusal, public/private separation
and the actual smoke fixture's training-only tokenizer limits. These are exposed
engineering fixtures and test doubles, not held-out learning measurements. Test
counts overlap and are not summed as independent evidence.

The v0.1 CUDA run remains tied to source 6ef614bf and published baseline 9504f93c.
It cannot certify this new input version. Historical viewer and smoke artifacts
are unchanged; the adapter source intentionally advances to 0.2. Rebuild the
training-only tokenizer and model-origin binding for future 0.2 execution.
No new model, tensor, provider run or budget reservation occurred here.

The benefit established here is explicit and consistent input assumptions.
Learning speed, delayed retention, unseen transfer and CAS-specific advantage
remain unproven. Both matched experiment arms must receive this assumption and
account for its input work equally. The full goal remains active.
