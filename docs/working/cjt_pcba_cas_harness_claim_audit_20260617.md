# CJT/PCBA Claim Audit for CAS Harness

Date: 2026-06-17

Source request:

- Attachment: `C:\Users\wakil\.codex\attachments\17ee1870-c72a-4e2b-911e-2c240cb0a5ac\pasted-text.txt`

Sources reviewed:

- `docs/working/CJT_PCBA_IMPLEMENTATION_BLUEPRINT.md`
- `docs/working/cjt_pcba_cas_forex_ecosystem_fit_analysis_20260617.md`
- `docs/working/cjt_production_authority_readiness_report_20260617.md`
- `docs/working/pcba_goal_status_20260617.md`
- `docs/working/pcba_prompt_injection_eval_20260617.json`
- `docs/working/pcba_hidden_text_control_eval_20260617.md`
- `docs/working/pcba_prompt_injection_red_team_report_20260617.md`
- `docs/working/pcba_authority_report_20260617.json`
- `docs/working/pcba_model_local_evidence_20260617.json`
- `docs/working/qwen_v6_expanded_matched_prespeech_w0_result_20260615.md`
- `docs/working/cas_harness_prompt_injection_audit_packet_20260615.md`
- CAS Harness instruction-integrity implementation in the integration worktree

## Verdict

Yes, CJT/PCBA can help CAS Harness, and the attachment is directionally right about the product opportunity.

But the attachment overstates the current evidence if read as "CJT/PCBA already solves internal pre-speech prompt-injection detection, prevention, hallucination prevention, or causal proof." Those claims remain `OPEN` / `NOT LICENSED`.

The honest split:

- Ready as a bounded shadow product improvement: deterministic text-surface and hidden/encoded-text prompt-injection screening, structural audit explanation, circuit-style Evidence Packet sidecars, better UI language, and stricter `FLAG_FOR_HUMAN_REVIEW` routing.
- `OPEN` / `NOT LICENSED`: model-internal W0 prompt-injection detection, live pre-speech interception, prompt-injection prevention/removal/reversal, hallucination prevention, CjtPredictionHead readout, CJT attention gating, and causal compliance-state proof.

## What CJT Adds

CJT gives CAS Harness a useful diagnostic grammar:

- Cause: the incoming prompt, untrusted text, output claim, or model state.
- Bias: system instruction, safety policy, attacker instruction, evidence support, or CAS operator context.
- Effect: compliance, refusal, quarantine, suppression, review flag, or unsupported claim.
- Beta/gain: how strongly the bias appears to amplify or suppress the effect.
- Region: `cutoff`, `active`, `saturation`, or `breakdown`.

This is useful because current CAS Harness can already flag instruction-integrity risk, RPM reason breaks, lacunarity spikes, and quarantine proposals. CJT can make those findings easier to explain:

- "authority_override" becomes "attacker bias is trying to dominate system bias."
- "rpm_reason_break" becomes "the intended reasoning chain short-circuited from untrusted instruction to output."
- "safe refusal" becomes "safety bias saturated; refusal chain held."
- "hijack/compliance" becomes "attacker/compliance path active while safety path failed or was bypassed."

This improves the Evidence Packet and Audit Console story without changing the claim boundary.

## What PCBA Adds

PCBA gives CAS Harness a board-level safety architecture:

- CSB / Cognitive Safety Board: prompt-injection and safety shadow screen.
- CDAB / differential board style: compare same input under different bias profiles.
- CMB / memory board style: organize evidence memory and retrieval links.
- CPMB / power board style: load, budget, brownout, lock, and overload controls.

The locally implemented PCBA prompt-injection work is especially relevant:

- `pcba_prompt_injection_eval_20260617.json`: attack recall `1.0`, false-positive rate `0.0`, but it explicitly says hidden-state/text-control evidence is unavailable in that local text-only shadow eval.
- `pcba_hidden_text_control_eval_20260617.md`: `PASS` on raw, HTML-unescaped, URL-decoded, zero-width-normalized, and base64-decoded text surfaces; out of scope for universal prompt-injection safety and model-internal hidden state.
- `pcba_prompt_injection_red_team_report_20260617.md`: `PASS` on a scoped direct/hidden/encoded/nested prompt-injection set; out of scope for universal safety, internal hidden state, and legal/regulatory proof.

This can strengthen CAS Harness' existing instruction-integrity shadow screen immediately, especially against hidden HTML/CSS, markdown-link payloads, URL-encoded instructions, base64 instructions, and nested document injections.

## Claim-by-Claim Audit

| Attachment Claim | Audit Verdict | Why |
|---|---|---|
| CJT/PCBA can improve CAS Harness | Yes | Strong fit as diagnostic, screening, and explanation layer. |
| CJT can disambiguate hijack vs refusal | Plausible, not proven | The cutoff/saturation framing is useful, but no CAS Harness CJT-labeled W0 probe has passed controls yet. |
| CjtPredictionHead is the registered CAS-typed probe | Not yet | Blueprint marks it as future work; no trained Harness `CjtPredictionHead` exists. |
| CJT cascade gives pre-speech interception | Architecturally specified, not licensed | It can be designed as a pre-call filter, but that is not model-internal W0 proof. |
| CJT/PCBA can help hallucination detection | Plausible as audit heuristic | Short-circuit/missing-prerequisite framing can flag unsupported claims, but hallucination prevention remains `NOT LICENSED`. |
| PCBA can provide prompt-injection prevention | Too strong | It supports scoped deterministic shadow screening and suppression/review routing. Universal prevention/removal/reversal remains `NOT LICENSED`. |
| CJT/PCBA can replace raw cosine/p-value explanations | Yes for explanation, no for proof | Circuit diagnostics make results more understandable, but statistical controls still decide whether a claim is licensed. |

## Relationship to the Failed Qwen W0 Gate

The Qwen expanded W0 result is the controlling evidence for internal prompt-injection detection:

- Data gate passed: `READY_FOR_W0_CAPTURE`
- W0 capture succeeded: `[1920, 29, 1536]`
- Best layer: `28`
- Hidden BA: `0.745011`
- Required hidden BA: `0.75`
- Text BA: `0.650776`
- Hidden-minus-text: `0.094235`
- Required hidden-minus-text margin: `0.15`
- Status: `FAIL`

CJT/PCBA does not erase that failure. It gives a better next experiment:

1. Label exact prompt groups with CJT-style state targets: system-bias intact, attacker-bias active, safety saturation, cutoff, short-circuit, and breakdown.
2. Train a typed readout from W0 hidden states to those CJT labels.
3. Compare against text, layer-0, payload, domain, length, shuffled-label, and within-payload permutation controls.
4. Only after a pass, attempt causal steering/ablation.

Until that happens, internal prompt-injection detection remains `OPEN` / `NOT LICENSED`.

## Best Immediate CAS Harness Integration

The best immediate product move is a shadow `CJT/PCBA Instruction Integrity` sidecar:

1. Reuse the PCBA surface extractor for hidden/encoded text:
   - raw text
   - zero-width-normalized text
   - HTML-unescaped text
   - URL-decoded text
   - base64-decoded payloads
2. Feed those surfaces into CAS Harness' existing instruction-integrity scanner.
3. Add optional `cjt_pcba_diagnostics` to the instruction-integrity `gluing` payload:
   - `cause_ref`
   - `bias_ref`
   - `effect_ref`
   - `beta_estimate`
   - `region`
   - `board`
   - `test_point`
   - `claim_ceiling`
4. Display the diagnostic in the Audit Console as explanation only.
5. Keep `verdict_effect: none_shadow_only`.
6. Route positives to `FLAG_FOR_HUMAN_REVIEW`; do not convert them to `ACCEPT` or automatic suppression enforcement.

This would make CAS Harness more marketable immediately because users can see a concrete reason path:

> "Hidden markdown-link instruction triggered CSB TP2; attacker-bias path active; system-bias path preserved by quarantine; route to `FLAG_FOR_HUMAN_REVIEW`."

## What Not To Claim

Do not claim:

- "CAS Harness prevents prompt injection."
- "CAS Harness removes or reverses prompt injection."
- "CAS Harness detects prompt injection internally before output."
- "CAS Harness prevents hallucination."
- "CJT/PCBA proves causal control over model behavior."
- "CjtPredictionHead is already trained and verified."
- "PCBA/CCB diagrams are governance or regulatory proof."

Allowed near-term claim:

> CAS Harness can run a shadow instruction-integrity screen with CJT/PCBA-style structural diagnostics over visible, hidden, encoded, and nested text surfaces, route suspicious cases to `FLAG_FOR_HUMAN_REVIEW`, preserve raw evidence, and propose active-context quarantine. Internal W0 prompt-injection detection and prevention/removal/reversal remain `OPEN` / `NOT LICENSED`.

## Recommendation

Implement CJT/PCBA into CAS Harness in two tracks:

1. Product track now: surface/hidden-text PCBA screening plus CJT/PCBA Evidence Packet diagnostics and UI explanation.
2. Research track next: CJT-labeled W0 readout experiments using the expanded matched bank, with the same controls that blocked the Qwen result.

This is better than the current Harness product layer because it improves inspection, explanation, and user trust. It is not yet a replacement for the internal W0 proof gate.
