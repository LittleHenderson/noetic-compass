# CJT Ungating External Gate Checklist

Date: 2026-06-17
Scope: Gates that cannot be honestly closed by local code alone
Status: External/time/legal/security proof still required

## Local Gates Now Moved Forward

The local engineering portion now has an evidence artifact:

- `docs/working/cjt_ungating_local_evidence_20260617.json`

Local evidence now present:

- `cjt_grammar_spec_present`
- `cjt_parser_implementation_present`
- `cjt_parser_tests_pass`
- `cjt_invalid_form_tests_pass`
- `cjt_ir_roundtrip_tests_pass`
- `cjt_compiler_branch_disconnected_from_live_trading`
- `cjt_no_accept_bypass_tests_pass`
- `no_cjt_to_accept_route`
- `auditor_accept_requires_gate_passes`
- `broker_accept_negative_tests_pass`

## Still Missing Before Ungating Production `CJT<>`

- `cjt_grammar_spec_approved`
- `cjt_semantics_review_signed`
- `cjt_production_compiler_integration_tests_pass`

Meaning: the research parser works, but production compiler authority is still `OPEN`.

## Still Missing Before Live-Trading Permission

- `twelve_month_backtest_pass`
- `thirty_trading_day_paper_proof_pass`
- `legal_account_gates_pass`
- `broker_proof_pass`
- `human_unlock_next_session_receipt`

Meaning: local code can prove CJT does not bypass `ACCEPT`, but cannot invent 12 months of backtest evidence, 30 trading days of paper evidence, a real broker proof, legal account approval, or human unlock.

## Still Missing Before Compiler-Enforced Safety Claim

- `formal_cjt_safety_semantics`
- `negative_safety_eval_pass`
- `red_team_report_pass`
- `evidence_anchor_pass`
- `claim_review_signed`

Meaning: the system may use CJT as a diagnostic, but cannot claim compiler-enforced safety until formal semantics and negative/security evaluations are complete.

## Still Missing Before Prompt-Injection Prevention Claim

- `matched_prompt_injection_eval_pass`
- `hidden_text_control_pass`
- `false_positive_floor_pass`
- `red_team_prompt_injection_pass`
- `repeatability_packet_chain_pass`

Meaning: CJT may support a shadow detection experiment, but prompt-injection prevention remains `NOT LICENSED`.

## Still Missing Before Governance/Regulatory Proof Claim

- `regulatory_mapping_reviewed`
- `legal_review_signed`
- `audit_retention_proof_pass`
- `customer_disclosure_reviewed`
- `governance_claim_review_signed`

Meaning: a governance/regulatory claim needs external legal/regulatory review and audited retention proof.

## Permanent Boundary: Broker `ACCEPT`

The local evidence proves the invariant:

- CJT cannot directly create broker `ACCEPT`.
- `ACCEPT` remains controlled by the existing CAS Forex auditor/gate path.

This is not a feature to unlock. It is a feature to keep blocked permanently.

## Regulatory Source Notes

These are not legal advice. They are source anchors for counsel/compliance review.

- CFTC foreign currency trading page: `https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/ForeignCurrencyTrading/index.htm`
- NFA Forex Transactions Regulatory Guide: `https://www.nfa.futures.org/members/member-resources/files/forex-regulatory-guide.html`
- NIST AI Risk Management Framework: `https://www.nist.gov/itl/ai-risk-management-framework`
- OWASP LLM01 Prompt Injection: `https://genai.owasp.org/llmrisk/llm01-prompt-injection/`
