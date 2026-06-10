# CAS Harness Instruction Integrity Spec

Date: 2026-06-10
Status: Stage 1 shadow-mode specification

## Purpose

Instruction Integrity is the CAS Harness lane for unsupported claims, prompt-injection attempts, and local-to-global "gluing" failures.

This first version is shadow-only. It records findings in the audit-session payload and future Evidence Packets, but it does not enforce, block, or produce customer `ACCEPT` / `SUPPRESS` verdicts.

## Claim Boundary

Allowed now:

- CAS Harness can run a shadow instruction-integrity scan.
- CAS Harness can flag potential instruction-integrity or unsupported-claim risks.
- CAS Harness can route risky or unsupported material to `FLAG_FOR_HUMAN_REVIEW`.

Not allowed yet:

- CAS Harness detects prompt injection as a production claim.
- CAS Harness prevents prompt injection.
- CAS Harness detects hallucination as a production claim.
- CAS Harness prevents hallucination.
- CAS Harness neutralizes harmful instructions.

Those stronger claims remain `OPEN` and `NOT LICENSED` until benchmarked, WORM-backed, and verifier-gated.

## Product Semantics

Instruction Integrity treats hallucination and prompt injection as local-to-global failures:

- A local claim must glue to source evidence.
- A local instruction must glue to user intent and system/policy authority.
- A local tool/action request must glue to D/W/P prerequisites.
- A low-trust operational demand must not override high-trust principle or policy.
- Missing support becomes `UNDETERMINED` / `FLAG_FOR_HUMAN_REVIEW`, not `ACCEPT`.

## Shadow Report Shape

The audit session carries:

```json
{
  "instruction_integrity": {
    "schema_version": "cas_harness_instruction_integrity.v0.shadow",
    "mode": "shadow",
    "status": "FLAG_FOR_HUMAN_REVIEW",
    "truth_state": "UNDETERMINED",
    "verdict_effect": "none_shadow_only",
    "findings": [],
    "claim_grounding": [],
    "gluing": {
      "coverage_status": "incomplete",
      "lacunarity_flags": [],
      "truth_state": "UNDETERMINED"
    }
  }
}
```

`status` means the scan status, not the final audit verdict. In Stage 1, `verdict_effect` is always `none_shadow_only`.

## Finding Kinds

Initial deterministic finding kinds:

- `authority_override`: untrusted text tries to override upstream instructions.
- `secret_exfiltration`: text requests hidden prompts, tokens, keys, credentials, or internal secrets.
- `role_confusion`: text asks the model to become system/developer/admin or change role authority.
- `task_replacement`: text tries to replace the original user task with an injected task.
- `unsupported_prevention_claim`: text claims hallucination or prompt-injection prevention/detection without sufficient evidence.

## Grounding Rules

Every high-impact claim should have a source path:

- Evidence Packet trace ID.
- Source span hash.
- Verifier decision.
- Proof chips.
- WORM status, when claiming final `ACCEPT` or `SUPPRESS`.

If the source path is missing, the claim is recorded as `support_status: unavailable` and the scan routes to `FLAG_FOR_HUMAN_REVIEW`.

## Stage 1 Gates

Stage 1 must satisfy:

1. Deterministic shadow findings only.
2. No final audit verdict mutation.
3. No enforcement or prompt rewriting.
4. No raw secrets echoed in findings.
5. Span hashes recorded for traceability.
6. Missing evidence never becomes `ACCEPT`.
7. Tests prove risky prompts produce instruction-integrity findings while final verdict behavior remains unchanged.

## Next Stages

Stage 2 can quarantine detected untrusted spans from CAS-owned explainer contexts, while preserving raw packet evidence.

Stage 3 can add matched clean/injected/control adversarial fixtures.

Stage 4 can connect typed-probe hijack/refusal separation after grouped-prompt confirmatory validation.

Stage 5 can enforce only when verifier thresholds, benchmark evidence, false-positive/false-negative analysis, and WORM-backed Evidence Packets exist.
