# CAS Forex UI Readiness Gate

Date: 2026-06-22
Status: proof-cockpit readiness gate started
Claim boundary: UI readiness does not create broker `ACCEPT`, live trading permission, or payment-transfer permission

## Purpose

This gate answers one question:

> Do we have enough truthful daily paper-bundle records for the CAS Forex proof
> cockpit to claim multi-day proof maturity?

It is intentionally not a live trading gate. It only decides whether the backend
has enough real paper evidence for the UI to display multi-day proof without
becoming a placeholder shell.

Correction after owner pushback: this gate must not block starting UI/UX. The
read-only CAS Forex proof cockpit/platform shell can start now using the current
day-1 real evidence, with missing future days shown as blocked or pending. The
`5` complete-bundle threshold is a maturity threshold for truthful multi-day
proof views, not a reason to wait before building the product surface.

## Built

- `cas-forex/cas_forex/paper_ui_readiness.py`
- `cas-forex/scripts/run_paper_ui_readiness.py`
- `cas-forex/tests/test_paper_ui_readiness.py`

## Current Rule

Minimum before the UI can claim multi-day proof maturity:

- `5` complete daily paper bundles
- each complete day must have:
  - broker/demo verified paper receipt
  - paper route/no-trade decision
  - paper risk-budget review
- all three local evidence chains must verify
- live mode must not appear in the paper-proof status
- open positions must reconcile

This is a UI evidence-maturity threshold, not the final live gate and not a UI
start blocker. The final paper-proof gate remains `30 / 30` verified trading
days.

## First Real Readiness Check

Command:

```powershell
python scripts/run_paper_ui_readiness.py --min-daily-bundles 5 --output-dir evidence_runs/index_tsmom_126_paper_proof
```

Result:

- status:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-ui-readiness-status.json`
- readiness status: `NOT_READY_FOR_UI_UX`
- complete daily bundles: `1 / 5`
- completed paper days: `1`
- broker verified days: `1`
- decision days: `1`
- risk review days: `1`
- complete bundle date: `2026-06-22`
- paper proof chain verified: `true`
- paper decision chain verified: `true`
- paper risk chain verified: `true`

Blockers:

- `complete_bundle_days 1 < required 5`
- `broker_verified_days 1 < required 5`
- `decision_days 1 < required 5`
- `risk_review_days 1 < required 5`

## Meaning

The UI/UX point is now: start the proof cockpit now, but keep it honest. The
backend architecture has enough real day-1 evidence to power a read-only shell;
the data history is not yet mature enough for multi-day proof claims. Run the
daily bundle for each real trading day until at least `5` complete daily bundles
exist, and have the UI show:

- proof progress toward `30 / 30`
- broker/demo verification
- route/no-trade/macro-lock state
- risk sizing and attempt caps
- blockers
- explicit `NOT LICENSED` live-money boundary

Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank transfer, and
payout automation remain `NOT LICENSED`.
