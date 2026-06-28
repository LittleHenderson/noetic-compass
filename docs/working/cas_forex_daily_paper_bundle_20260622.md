# CAS Forex Daily Paper Bundle

Date: 2026-06-22
Status: backend daily bundle started
Claim boundary: daily paper bundles orchestrate paper proof only; they do not place trades, create broker `ACCEPT`, or authorize live money

## Purpose

The daily bundle runs or summarizes the three proof tracks needed before UI/UX:

1. MT5 demo receipt status
2. paper route/no-trade decision
3. paper risk-budget review

It defaults to `skip_existing`, so rerunning it for the same date does not
duplicate already-written proof records.

## Built

- `cas-forex/cas_forex/paper_daily_bundle.py`
- `cas-forex/scripts/run_daily_paper_bundle.py`
- `cas-forex/tests/test_paper_daily_bundle.py`

## Active Lead

- lead id: `index_tsmom_126_d1`
- setting: `tsmom_126_250_2_10`
- symbols: `US30`, `NAS100`
- timeframe: `D1`

## First Bundle Run

Command:

```powershell
python scripts/run_daily_paper_bundle.py --date 2026-06-22 --account-equity 5000 --max-risk-pct 0.5 --daily-risk-pct 1.0 --output-dir evidence_runs/index_tsmom_126_paper_proof
```

Result:

- status:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-daily-bundle-status.json`
- bundle id:
  `index-tsmom-126-d1-paper-proof-2026-06-22-daily-bundle`
- completed: `true`
- MT5 demo receipt step: `SKIPPED_EXISTING`
- paper route decision step: `SKIPPED_EXISTING`
- paper risk review step: `SKIPPED_EXISTING`
- reason: all three day-1 records already existed, so the bundle did not duplicate them

Current combined status:

- paper proof: `1 / 30` completed, `1 / 30` broker verified, chain verified,
  `passed=false`
- route decision: `ROUTE_PAPER_SIGNAL` for US30 and NAS100, macro `PASS`,
  event context `normal`
- risk review: `PAPER_ATTEMPTS_ALLOWED`, `2 / 2` paper attempts allowed,
  total planned paper risk `$25.30` / `0.506%` on `$5,000` paper equity

## Next Daily Command

For the next trading day, run the same command with the new date:

```powershell
python scripts/run_daily_paper_bundle.py --date YYYY-MM-DD --account-equity 5000 --max-risk-pct 0.5 --daily-risk-pct 1.0 --output-dir evidence_runs/index_tsmom_126_paper_proof
```

If MT5 is unavailable, the bundle will report that step as `UNAVAILABLE` or
`BLOCKED` instead of pretending proof exists. If a macro/event lock suppresses
the route, risk review should show no paper attempt.

## UI/UX Trigger

The UI readiness gate is now recorded in
`docs/working/cas_forex_ui_readiness_gate_20260622.md`.

Not yet. The backend now has the right daily bundle, but the proof cockpit should
wait until the readiness gate reaches `READY_FOR_PROOF_COCKPIT_UI_UX`. Current
state is `NOT_READY_FOR_UI_UX` with complete daily bundles `1 / 5`. Then the UI
can truthfully show:

- proof progress toward `30 / 30`
- broker/demo verification
- route/no-trade/macro-lock status
- risk sizing and attempt caps
- blockers
- `NOT LICENSED` live-money boundary

Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank transfer, and
payout automation remain `NOT LICENSED`.
