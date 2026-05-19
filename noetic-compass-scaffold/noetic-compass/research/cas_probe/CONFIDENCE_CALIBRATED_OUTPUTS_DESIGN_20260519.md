---
title: Confidence-Calibrated User-Facing Outputs — Design Spec
subtitle: Path D — Verification Stack tiers exposed as user-facing reply confidence
version: 0.1 (design only, no code)
date: 2026-05-19
status: Internal design draft — gated on Wrap Pipeline integration of VerificationGate (Path C)
authors: Little Henderson (Founder), Claude Opus 4.7
classification: Confidential
---

# Confidence-Calibrated User-Facing Outputs — Design Spec

**Version 0.1 — 2026-05-19**
**Status: design only, no code.** Implementation depends on Path C (CAS Native Wrap Pipeline integration of the VerificationGate module landed at `cas-native/inference/verification_gate.py`).

---

## 1. Purpose

CAS Native's outputs today are uniform — one reply per prompt, no built-in indication of how confident the model is in its own answer. The Stage 19A Verification Stack methodology gives us a runtime-safe, gold-label-free way to grade each prediction as `high` / `medium` / `suppress` / `uncertain`. Path D exposes that grade to the end user, making CAS Native produce **confidence-calibrated** replies instead of uniform replies.

This is the user-facing endpoint of the Stage 19A capability. Section 5.14 of the v1.3 spec sheet documents the underlying mechanism. This document specifies how that mechanism becomes a customer-visible product behavior.

## 2. The four tiers and their user-facing mappings

| Stack verdict | User-facing label | Example reply phrasing | Mode 7 trace fields |
|---|---|---|---|
| **ACCEPT — high** | (no visible label; clean reply) | "The answer is X." | `decision_tier=high`, `ensemble_agreement=true`, `trace_stability ≥ 0.8`, `confidence ≥ 0.85` |
| **ACCEPT — medium** | "with moderate confidence" | "My best understanding is X, though I'd flag moderate confidence on this one." | `decision_tier=medium`, `ensemble_agreement=true`, `trace_stability ∈ [0.6, 0.8)`, `confidence ∈ [0.6, 0.85)` |
| **SUPPRESS** | "not confident — could you clarify?" | "I'd rather not answer this one — my internal readouts disagree about what you're asking. Could you clarify? [details available in trace]" | `decision_tier=suppress`, list of `suppression_reasons[]`, dominant_reason highlighted |
| **UNCERTAIN** | "uncertain — answering tentatively" | "Tentatively: X. My internal trace was unstable on this one — please double-check." | `decision_tier=uncertain`, `trace_stability < 0.6`, `ensemble_agreement=true` (the unusual case where positions agree but layers drift) |

These mappings are **deliberate and reserved-language disciplined**. The phrases use "confidence", "I'd rather not", "double-check" — never "I refuse", "rejected", "failed", or any framing that implies the model crashed.

## 3. Plain English — why this matters

**Plain English metaphor:** A confident doctor who tells you "your test came back inconclusive — let's run another one" is more useful than a doctor who guesses confidently every time. The honest "I'm not sure" output is itself a useful answer when it comes with auditable reasoning attached.

Today CAS Native produces a single answer per prompt. With Path D it produces:
- A clean answer when internally consistent (most cases)
- A flagged answer with explicit caveat when partially uncertain (some cases)
- A request for clarification or a tentative-flagged answer when internally inconsistent (rare cases)

The honest "I don't know" output is the same property that makes CAS Harness regulator-grade for auditing third-party models. Path D propagates that property into CAS Native's own user-facing outputs.

## 4. Wrap Pipeline integration points

CAS Native's 8-stage Wrap Pipeline currently ends in an Output Gate. Path D adds two integration points:

### 4.1 Pre-emission (decision)

After the model generates a candidate reply but BEFORE emission, the `VerificationGate.check(...)` method (from Path C) consumes:

- Per-position CAS classifications at three readout points (focus_token, final_token, mean_over_sequence_length)
- Per-layer trace of the dominant CAS class across all transformer layers
- The candidate reply's CAS expression (if any), for compiler validation

It returns a `VerificationResult` containing the decision_tier, suppression_reasons, ensemble_agreement, trace_stability, compiler_valid, and aggregated confidence.

### 4.2 Reply rendering (presentation)

The reply renderer consumes the `VerificationResult` and produces one of four reply shapes per Section 2:

```python
# Pseudocode for reply renderer
def render_reply(candidate_reply: str, verification: VerificationResult) -> RenderedReply:
    if verification.decision == 'ACCEPT' and verification.decision_tier == 'high':
        return RenderedReply(text=candidate_reply, label=None, trace=verification)
    elif verification.decision == 'ACCEPT' and verification.decision_tier == 'medium':
        return RenderedReply(
            text=candidate_reply,
            label="with moderate confidence",
            trace=verification,
        )
    elif verification.decision_tier == 'uncertain':
        return RenderedReply(
            text=f"Tentatively: {candidate_reply}",
            label="uncertain — internal trace was unstable",
            trace=verification,
        )
    elif verification.decision == 'SUPPRESS':
        return RenderedReply(
            text=clarification_request_for(verification.suppression_reasons),
            label="not confident — could you clarify?",
            trace=verification,
        )
```

The `clarification_request_for(...)` helper maps suppression_reasons to natural-language clarification requests. For example, `ensemble_all_disagree` might map to "Different parts of my internal trace are reaching different conclusions about what you're asking. Could you rephrase?"; `trace_unstable` might map to "My reasoning drifted between layers — let me re-read the question.".

## 5. Mode 7 trace surface

Every reply (regardless of tier) emits a Mode 7 trace record containing the full `VerificationResult`:

```json
{
  "trace_id": "uuid4-here",
  "reply_text": "...",
  "rendered_reply_label": "with moderate confidence",
  "verification": {
    "decision": "ACCEPT",
    "decision_tier": "medium",
    "ensemble_agreement": true,
    "trace_stability": 0.71,
    "compiler_valid": true,
    "confidence": 0.78,
    "suppression_reasons": []
  },
  "internal_state": {
    "per_position_classifications": {"focus_token": "^3^P|f", "final_token": "^3^P|f", "mean_over_seq_len": "^3^P|f"},
    "per_position_confidences": {"focus_token": 0.84, "final_token": 0.79, "mean_over_seq_len": 0.71},
    "per_layer_trace": ["^3^P|f", "^3^P|f", "^3^P|f", "^3^P|f", "^2^P|f", "^3^P|f", "^3^P|f", "^3^P|f"]
  }
}
```

This trace is the same shape as the Stage 19A Evidence Packet schema, ensuring the CAS Harness (third-party model audit) and CAS Native (own-model audit) speak the same language. A regulator using the Mode 7 trace surface sees the same evidence shape whether they're auditing a customer's model via Harness or auditing CAS Native's own output.

## 6. Bounds (reserved language)

What this design DOES specify:

- Mapping of Stack verdicts to user-facing labels
- Reply-rendering pseudocode
- Mode 7 trace shape
- Integration points with the existing Wrap Pipeline

What this design does NOT specify and SHOULD NOT be inferred:

- The natural-language phrasing is illustrative, not contractual. Final phrasings need UX review.
- The suppression_reason → clarification_request mapping is a stub. Each reason needs a curated natural-language equivalent. This is a copy-writing task plus UX review.
- This design does not modify any existing reply behavior until Path C (VerificationGate wired into Wrap Pipeline) is complete. Path D is downstream of Path C.
- This design does NOT claim user-study validation. Users may find the "moderate confidence" label confusing, useful, or annoying — that's an empirical UX question to test after the basic mechanism ships.

## 7. Implementation phases

| Phase | Deliverable | Depends on |
|---|---|---|
| Phase 1 | VerificationGate module (Path C precursor) | Done — landed at `cas-native/inference/verification_gate.py` with 14 passing tests |
| Phase 2 | Wrap Pipeline integration: VerificationGate.check() called before emission | Pending |
| Phase 3 | Reply renderer: implement four-tier presentation per Section 4.2 | Phase 2 |
| Phase 4 | Mode 7 trace surface: emit full verification record per Section 5 | Phase 2 |
| Phase 5 | Suppression_reason → clarification_request mapping (UX copy work) | Phases 2–4 |
| Phase 6 | UX user study on the four-tier phrasings | Phase 5 |

This document specifies Phases 2–5. Phase 1 is complete. Phase 6 is post-ship validation.

## 8. The one-line product summary

**CAS Native's user-facing replies stop being uniform. Each reply carries an honest confidence tier, derived at runtime from the same Verification Stack methodology that makes CAS Harness regulator-grade. The user gets a clean answer when the model is internally consistent, a flagged answer when it's marginally consistent, and a clarification request when it's not. Every reply emits a full Mode 7 trace with the verification evidence available for inspection.**

---

## Appendix A — Why this design preserves CAS Native's "transparent by construction" property

Per the founder's standing rules: *"CAS Native is 'our model, transparent by construction.'"* Path D extends that transparency to the moment of emission. The traditional LLM emission contract is "model produces text; user trusts the text." The CAS Native emission contract is "model produces text PLUS the runtime verification evidence; user can see both and decide."

The transparency promise was always architectural (CAS as the substrate). Path D makes it operational (verification evidence as part of every output). Same property, different layer.

---

*End of Document — Path D Confidence-Calibrated Outputs Design v0.1 — 2026-05-19*
