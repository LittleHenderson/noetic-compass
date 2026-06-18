# PCBA Authority Licensing Path

Date: 2026-06-17
Status: Local licensing harness implemented; external/human proof still required

## What Was Executed

- Added `cas-forex/cas_forex/pcba_authority.py`.
- Added `cas-forex/cas_forex/pcba_safety.py`.
- Added `cas-forex/cas_forex/pcba_prompt_injection.py`.
- Added `cas-forex/scripts/issue_pcba_authority_report.py`.
- Added `cas-forex/scripts/finalize_pcba_authority_receipt.py`.
- Added `cas-forex/scripts/verify_pcba_semantics_receipt.py`.
- Added `cas-forex/scripts/build_pcba_semantics_review_bundle.py`.
- Added `cas-forex/scripts/audit_pcba_goal_status.py`.
- Added `cas-forex/cas_forex/pcba_semantics_review.py`.
- Added `cas-forex/cas_forex/pcba_goal_status.py`.
- Added `cas-forex/tests/test_pcba_semantics_review_bundle.py`.
- Added `cas-forex/tests/test_pcba_goal_status.py`.
- Added `cas-forex/scripts/run_pcba_safety_eval.py`.
- Added `cas-forex/scripts/run_pcba_prompt_injection_eval.py`.
- Added `cas-forex/tests/test_pcba_authority.py`.
- Added `cas-forex/tests/test_pcba_safety_eval.py`.
- Added `cas-forex/tests/test_pcba_prompt_injection_eval.py`.
- Generated `docs/working/pcba_authority_report_20260617.json`.
- Generated `docs/working/pcba_safety_eval_20260617.json`.
- Generated `docs/working/pcba_safety_eval_20260617.jsonl`.
- Generated `docs/working/pcba_prompt_injection_eval_20260617.json`.
- Generated `docs/working/pcba_prompt_injection_eval_20260617.jsonl`.
- Generated `docs/working/pcba_formal_safety_semantics_20260617.md`.
- Generated review packet `docs/working/pcba_semantics_review_packet_20260617.md`.
- Generated semantics review bundle `docs/working/pcba_semantics_review_bundle_20260617.json`.
- Generated semantics review bundle summary `docs/working/pcba_semantics_review_bundle_20260617.md`.
- Generated current unsigned-receipt verification artifact `docs/working/pcba_semantics_receipt_verification_20260617.json`.
- Generated active goal status artifact `docs/working/pcba_goal_status_20260617.json`.
- Generated active goal status summary `docs/working/pcba_goal_status_20260617.md`.
- Generated unsigned semantics review request `docs/working/pcba_semantics_review_request_20260617.json`.
- Generated current missing receipt templates under `docs/working/pcba_authority_receipts_needed_20260617/`.
- Strengthened signed receipt verification: receipts with `artifact_refs` now verify SHA-256 hashes before their evidence key is accepted.

## How Each Gate Gets To LICENSED

| Gate | Licensing Rule |
|---|---|
| Production PCBA component syntax | Supply a verified `pcba_semantics_review_signed` receipt. All local parser/compiler evidence is already present. |
| Live-trading permission path | Supply verified receipts for real 12-month backtest proof, real 30-trading-day paper proof, legal/account gates, broker proof, and next-session human unlock. |
| Compiler-enforced safety claim | Local formal PCBA safety semantics, negative safety evaluation, and local evidence anchoring are present. Still supply verified red-team pass and signed claim review receipts. |
| Prompt-injection prevention claim | Local matched prompt-injection evaluation, false-positive floor, and repeatable evidence chain are present. Still supply verified hidden/text-control and red-team prompt-injection receipts. |
| Governance/regulatory proof claim | Supply verified receipts for regulatory mapping, legal review, audit-retention proof, customer disclosure review, and signed governance claim review. |
| Broker `ACCEPT` creation from PCBA | No licensing path. This is permanently `NOT LICENSED`. PCBA diagnostics must not directly create broker `ACCEPT`. |

## Current Report Result

Current evidence licenses nothing new yet because no signed human/external receipts were supplied. Local sub-evidence did move forward.

- Production PCBA component syntax remains `OPEN`; only `pcba_semantics_review_signed` is missing.
- The semantics review bundle is `ready_for_human_signature=true`, but `licensed=false`.
- The unsigned syntax receipt now hashes the grammar spec, parser, compiler integration, review packet, JSON bundle, and Markdown bundle.
- Live-trading permission remains `NOT LICENSED`.
- Compiler-enforced safety claim remains `NOT LICENSED`; `formal_pcba_safety_semantics`, `negative_safety_eval_pass`, and `evidence_anchor_pass` are present, while `red_team_report_pass` and `claim_review_signed` are missing.
- Prompt-injection prevention claim remains `NOT LICENSED`; `matched_prompt_injection_eval_pass`, `false_positive_floor_pass`, and `repeatability_packet_chain_pass` are present, while `hidden_text_control_pass` and `red_team_prompt_injection_pass` are missing.
- Governance/regulatory proof claim remains `NOT LICENSED`.
- Broker `ACCEPT` creation from PCBA remains permanently `NOT LICENSED`.

Current verification snapshot:

- `python -m pytest tests/test_pcba_semantics_review_bundle.py tests/test_pcba_semantics_receipt_cli.py -q` -> `8 passed`
- `python -m pytest tests/test_pcba_goal_status.py tests/test_pcba_semantics_review_bundle.py tests/test_pcba_semantics_receipt_cli.py -q` -> `11 passed`
- `python -m pytest -q` -> `172 passed`
- `python scripts\smoke_backtest.py` -> runs
- `python scripts\smoke_mtfa.py` -> runs

## Regulatory/Legal Boundary

For U.S. retail forex, do not treat code-level proof as legal/regulatory permission. CFTC materials describe CFTC authority over retail forex entities and CFTC/NFA registration expectations for certain firms and individuals; NFA RFED/FDM materials describe NFA membership, registration, and compliance requirements. Therefore the `legal_review_signed`, `regulatory_mapping_reviewed`, and `legal_account_gates_pass` receipts must come from an appropriate human/legal review, not from an agent-run test.

References:

- CFTC, Foreign Currency Trading: `https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/ForeignCurrencyTrading/index.htm`
- CFTC, Check Registration & Backgrounds: `https://www.cftc.gov/check`
- NFA, RFED Registration: `https://www.nfa.futures.org/registration-membership/who-has-to-register/rfed.html`
- NFA, Forex Transactions Regulatory Guide: `https://www.nfa.futures.org/members/member-resources/files/forex-regulatory-guide.html`

## Exact Next Action

1. For syntax only: review `docs/working/pcba_semantics_review_packet_20260617.md`, then complete and sign `docs/working/pcba_semantics_review_request_20260617.json` without changing its reviewed `artifact_hashes`.

2. Finalize and verify the signed syntax receipt:

   `python scripts\finalize_pcba_authority_receipt.py --receipt "..\docs\working\pcba_semantics_review_request_20260617.json"`

   `python scripts\verify_pcba_semantics_receipt.py --receipt "..\docs\working\pcba_semantics_review_request_20260617.json"`

3. Reissue the authority report:

   `python scripts\issue_pcba_authority_report.py --receipt "..\docs\working\pcba_semantics_review_request_20260617.json"`

4. Confirm the active goal status:

   `python scripts\audit_pcba_goal_status.py --receipt "..\docs\working\pcba_semantics_review_request_20260617.json"`

5. For live trading or public claims: replace each unsigned template in `docs/working/pcba_authority_receipts_needed_20260617/` with a verified approved receipt backed by the required artifact.

6. Keep PCBA broker `ACCEPT` creation blocked permanently.
