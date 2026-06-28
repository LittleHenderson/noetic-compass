# CAS Forex Daily Paper Schedule

Date: 2026-06-22
Status: next-action schedule started
Claim boundary: daily schedule is an operator prompt only; it does not place trades, create broker `ACCEPT`, or authorize live money

## Purpose

The daily paper bundle exists, but the system also needs to say what is due
next. This schedule layer reads the paper ledgers and answers:

- Is today's bundle already complete?
- What is the next due trading date?
- Which tracks are missing for that date?
- What command should be run next?

It is read-only. It does not call MT5, append evidence, place orders, or move
money.

## Built

- `cas-forex/cas_forex/paper_daily_schedule.py`
- `cas-forex/scripts/run_paper_daily_schedule.py`
- `cas-forex/tests/test_paper_daily_schedule.py`

## First Real Schedule Check

Command:

```powershell
python scripts/run_paper_daily_schedule.py --date 2026-06-22 --account-equity 5000 --max-risk-pct 0.5 --daily-risk-pct 1.0 --output-dir evidence_runs/index_tsmom_126_paper_proof
```

Result:

- status:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-daily-schedule-status.json`
- as-of date: `2026-06-22`
- latest complete bundle date: `2026-06-22`
- next due date: `2026-06-23`
- next due status: `WAIT_NEXT_TRADING_DAY`
- complete daily bundles: `1`
- multi-day proof maturity bundles remaining: `4`
- full paper-proof days remaining: `29`
- missing tracks for next due date:
  - `broker_verified_receipt`
  - `paper_route_decision`
  - `paper_risk_review`

Recommended next command:

```powershell
python scripts/run_daily_paper_bundle.py --date 2026-06-23 --account-equity 5000 --max-risk-pct 0.5 --daily-risk-pct 1 --output-dir evidence_runs/index_tsmom_126_paper_proof
```

## Meaning

Day 1 is done. CAS should wait for the next real trading day, then run the daily
bundle. The proof cockpit UI can start now as a read-only paper/research
surface; it still needs `4` more complete daily bundles before claiming
multi-day proof maturity. The full paper proof still needs `29` more verified
paper days.

Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank transfer, and
payout automation remain `NOT LICENSED`.
