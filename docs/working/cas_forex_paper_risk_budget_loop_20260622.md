# CAS Forex Paper Risk Budget Loop

Date: 2026-06-22
Status: backend paper-risk review started
Claim boundary: paper risk reviews size paper attempts only; they do not place trades, create broker `ACCEPT`, or authorize live money

## Purpose

The paper proof now has three separate daily evidence tracks:

1. Broker/demo receipt track:
   proves whether a demo/paper broker source was checked for the day.
2. Paper route-decision track:
   records whether CAS would route, no-trade, macro-lock, or mark unavailable.
3. Paper risk-budget track:
   sizes any routed paper candidates against account equity, per-trade risk,
   daily risk, lot step, and daily attempt caps.

Keeping these separate matters. A route signal says "CAS sees a candidate."
The risk review says "this is the paper size that fits the risk budget."
Neither creates live trading permission.

## Built

- `cas-forex/cas_forex/paper_risk.py`
- `cas-forex/scripts/run_paper_risk_review.py`
- `cas-forex/tests/test_paper_risk.py`

## Active Lead

- lead id: `index_tsmom_126_d1`
- setting: `tsmom_126_250_2_10`
- symbols: `US30`, `NAS100`
- timeframe: `D1`

## First Daily Risk Review

Command:

```powershell
python scripts/run_paper_risk_review.py --account-equity 5000 --max-risk-pct 0.5 --daily-risk-pct 1.0 --append-review --output-dir evidence_runs/index_tsmom_126_paper_proof
```

Result:

- status:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-paper-risk-status.json`
- risk chain:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-paper-risk.jsonl`
- risk status: `PAPER_ATTEMPTS_ALLOWED`
- account equity used: `$5,000`
- max risk per routed paper attempt: `0.5%` / `$25`
- daily paper risk cap: `1.0%` / `$50`
- daily attempt cap: `3`
- proposed attempts: `2`
- allowed attempts: `2`
- suppressed attempts: `0`
- total planned lots: `0.02`
- total planned paper risk: `$25.30`
- total planned risk percent: `0.506%`
- evidence packet status: `SUPPRESSED`
- broker order placed: no

Per-symbol sizing:

| Symbol | Direction | Entry | Stop | Risk/lot | Paper lots | Planned risk |
|---|---|---:|---:|---:|---:|---:|
| `US30` | `LONG` | `51745.87` | `50485.56` | `$1,260.31` | `0.01` | `$12.60` |
| `NAS100` | `LONG` | `30241.62` | `28971.74` | `$1,269.88` | `0.01` | `$12.70` |

## What This Means

This is the first daily answer to "how big would the paper attempt be?" For a
`$5,000` paper equity, both day-1 index signals fit the paper risk budget only
at the smallest tested size, `0.01` lots each. That is useful and honest: it
keeps risk small while the 30-day proof is still incomplete.

## UI/UX Trigger

Daily bundle status is now available in
`docs/working/cas_forex_daily_paper_bundle_20260622.md`.

Closer, but not yet. The proof cockpit should start after this backend loop has
several daily records:

- MT5 demo receipt status per day
- paper route/no-trade decision per day
- macro/event context
- risk-budget sizing per routed candidate
- attempt count and suppressed-attempt reasons
- paper proof progress toward `30 / 30`
- explicit `NOT LICENSED` live-money boundary

Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank transfer, and
payout automation remain `NOT LICENSED`.
