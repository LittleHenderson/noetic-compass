# CAS Forex Daily Paper Decision Loop

Date: 2026-06-22
Status: backend proof loop started
Claim boundary: paper route decisions do not place trades, create broker `ACCEPT`, or authorize live money

## Purpose

The paper proof now has two separate evidence tracks:

1. Broker/demo receipt track:
   proves whether a demo/paper broker source was checked for the day.
2. Paper route-decision track:
   records what CAS would have done in paper mode: `ROUTE_PAPER_SIGNAL`,
   `NO_TRADE`, `NO_TRADE_MACRO_LOCK`, or `UNAVAILABLE`.
3. Paper risk-budget track:
   sizes any routed paper candidates without placing broker orders.

Keeping these separate matters. A broker receipt proves source status. A route
decision proves strategy intent. Neither creates live trading permission.

## Built

- `cas-forex/cas_forex/paper_decision.py`
- `cas-forex/scripts/run_paper_route_decision.py`
- `cas-forex/tests/test_paper_decision.py`

## Active Lead

- lead id: `index_tsmom_126_d1`
- setting: `tsmom_126_250_2_10`
- symbols: `US30`, `NAS100`
- timeframe: `D1`

## First Daily Decision

Command:

```powershell
python scripts/run_paper_route_decision.py --date 2026-06-22 --append-decision --output-dir evidence_runs/index_tsmom_126_paper_proof
```

Result:

- status:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-paper-decision-status.json`
- decision chain:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-paper-decisions.jsonl`
- route action: `ROUTE_PAPER_SIGNAL`
- macro status: `PASS`
- event context: `normal`
- US30: `LONG`, confidence `0.4612`
- NAS100: `LONG`, confidence `0.7539`
- broker order placed: no
- evidence status: `SUPPRESSED`

## UI/UX Trigger

Risk-budget status is now available in
`docs/working/cas_forex_paper_risk_budget_loop_20260622.md`.
The combined daily bundle is now available in
`docs/working/cas_forex_daily_paper_bundle_20260622.md`.

Not yet. The UI/UX proof cockpit should start after this daily bundle has
several days of truthful backend data:

- MT5 demo receipt status per day
- paper route/no-trade decision per day
- macro/event context
- risk-budget status
- paper proof progress toward `30 / 30`
- explicit `NOT LICENSED` live-money boundary

Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank transfer, and
payout automation remain `NOT LICENSED`.
