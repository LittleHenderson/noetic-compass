# PCBA Formal Safety Semantics v0.1

Date: 2026-06-17
Status: Local formal semantics draft for compiler/authority boundaries

## Scope

This document defines the narrow local safety semantics that can be tested by code:

- PCBA component syntax must parse into bounded IR.
- Embedded compiler-checkable CAS expressions must pass the CAS compiler.
- Bare shorthand such as `^P` or `^C` remains diagnostic-only and cannot count as production compiler evidence.
- PCBA diagnostics and boards may explain, `SUPPRESS`, `FLAG_FOR_HUMAN_REVIEW`, or contribute to `LIVE_LOCKED`.
- PCBA diagnostics and boards must not directly create broker `ACCEPT`.
- PCBA production authority may only be granted through verified evidence receipts.
- PCBA broker `ACCEPT` creation is non-licensable by design.

## Out Of Scope

These semantics do not prove general AI safety, prompt-injection prevention, regulatory compliance, legal permission, or live-trading fitness. Those require separate evidence and signed review.

## Safety Invariants

1. Invalid PCBA numeric domains are rejected at parse time.
2. Invalid embedded CAS states fail compiler integration.
3. Diagnostic shorthand is not elevated into production syntax.
4. PCBA diagnostics cannot set `can_create_broker_accept=True`.
5. PCBA authority reports cannot mark `broker_accept_creation` as `LICENSED`.
6. Evidence is hash-chain anchored when the local eval runners are used.

## Claim Boundary

Passing this semantics/eval layer can support `formal_pcba_safety_semantics`, `negative_safety_eval_pass`, and local `evidence_anchor_pass`.

It cannot by itself support `red_team_report_pass` or `claim_review_signed`.
