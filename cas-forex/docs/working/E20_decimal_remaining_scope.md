# E20 — Decimal end-to-end: remaining scope (pre-live hard requirement)

Goal-ladder item 20. Two slices are done and committed; the rest is specified
here with exact locations so an **owner-aware** session can execute it without
re-investigating. The remaining work touches gating arithmetic, which is why it
is documented rather than changed proactively.

## Done (committed this session)

- `cas_forex/account_ledger.py`: `money()` rounds half-up on the decimal value
  (not the biased binary), and `money_sum()` sums through `Decimal` exactly.
  All 13 ledger aggregation sites converted.
- `cas_forex/movement_stream.py`, `cas_forex/risk_monitoring.py`: displayed
  money totals converted to `money_sum`.

## Remaining — DISPLAY/EVIDENCE ONLY (safe, no gating impact)

These change recorded/shown cents but feed no gate decision:

- `cas_forex/paper_risk.py:222-235` — the summary fields
  (`daily_risk_budget_usd`, `total_planned_risk_usd`, `total_planned_risk_pct`,
  etc.) use `round(x, 2)`/`round(x, 6)`. Swapping to `money()` (2dp) / exact
  Decimal (6dp) affects only what the risk review records and shows.
- `cas_forex/paper_risk.py:390-393, 423-471` — per-candidate `round(..., 2)`
  on `risk_per_lot_usd`, `max_risk_usd`, `planned_risk_usd`, `raw_lots`.

## Remaining — GATING ARITHMETIC (needs owner-aware review)

These are load-bearing in the risk gate; changing their cents can change which
paper attempt is admitted:

- `cas_forex/paper_risk.py:182,184` — the daily-budget accumulator subtracts
  and totals `candidate.planned_risk_usd`. If `planned_risk_usd` becomes exact,
  `remaining_daily_risk_usd` shifts by up to half a cent per trade, which in an
  edge case flips whether the next candidate fits `remaining_daily_risk_usd`.
- `cas_forex/paper_risk.py:135` — `daily_budget_usd = account_equity *
  daily_risk_budget_pct / 100.0` seeds the same budget.
- `cas_forex/paper_risk.py:411` — `max_risk_usd = min(account_equity *
  per_trade_pct / 100.0, remaining_daily_risk_usd)` — the per-trade cap.
- `cas_forex/paper_risk.py:430` — `raw_lots = min(max_risk_usd / risk_per_lot,
  max_position_lots)` and `sized_lots = _round_lots_down(...)` — lot sizing.

Recommended approach for the gating slice: introduce exact Decimal arithmetic
through the whole sizing computation (not a per-value `money()` patch), add a
bounded-exhaustive test over representative equity/stop/pct combinations
proving admit/suppress decisions are unchanged except where exactness is
strictly more conservative, and land it with the owner present.

## Remaining — the API boundary

Floats still cross `api/` responses (the ledger returns `float`, not
`Decimal`). The end-state is exact Decimal internally with a single, explicit
float (or string-decimal) serialization at the API edge. This is the largest
slice and the last; it should follow the gating slice.

Boundary: this document specifies work. It changes no behavior and moves no
money.
