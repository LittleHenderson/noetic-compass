# CAS Forex Winning Strategy Ledger

Date: 2026-06-22
Status: active research memory
Claim boundary: research leads only; live trading remains `NOT LICENSED`

This file keeps the current winning or near-winning strategies at the front of
CAS Forex work. New experiments should not bury these leads. A strategy can be
added here as a lead, watchlist item, or retired item, but no entry creates
broker `ACCEPT` or live permission.

Machine-readable ledger:

- `cas-forex/strategy_leads.json`
- loader: `cas-forex/cas_forex/strategy_ledger.py`
- guard test: `cas-forex/tests/test_strategy_ledger.py`
- optimizer guard: `cas-forex/cas_forex/llm_optimizer.py`
- condition tally: `cas-forex/cas_forex/condition_tally.py`
- tally runner: `cas-forex/scripts/run_condition_tally.py`
- owner control: `cas-forex/cas_forex/owner_control.py`
- owner promotion review runner: `cas-forex/scripts/run_owner_promotion_review.py`
- paper-proof module: `cas-forex/cas_forex/paper_proof.py`
- paper-proof runner: `cas-forex/scripts/run_paper_proof_plan.py`
- paper broker receipt contract:
  `docs/working/cas_forex_paper_broker_receipt_contract_20260622.md`
- paper decision loop:
  `docs/working/cas_forex_daily_paper_decision_loop_20260622.md`
- paper risk-budget loop:
  `docs/working/cas_forex_paper_risk_budget_loop_20260622.md`
- daily paper bundle:
  `docs/working/cas_forex_daily_paper_bundle_20260622.md`
- UI readiness gate:
  `docs/working/cas_forex_ui_readiness_gate_20260622.md`
- daily schedule / next action:
  `docs/working/cas_forex_daily_schedule_20260622.md`
- optimizer plan: `docs/working/cas_forex_llm_optimizer_plan_20260622.md`
- current tally report:
  `cas-forex/evidence_runs/condition_tally/condition-tally-20260622052757-report.json`
- current owner promotion review:
  `cas-forex/evidence_runs/owner_promotion_review/owner-promotion-review-20260622055433-report.json`
- current paper-proof status:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-status.json`
- current paper receipt template:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-receipt-template-20260622.json`
- current MT5 demo probe:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-mt5-demo-probe-20260622153728.json`
- current paper decision status:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-paper-decision-status.json`
- current paper risk status:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-paper-risk-status.json`
- current daily bundle status:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-daily-bundle-status.json`
- current UI readiness status:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-ui-readiness-status.json`
- current daily schedule status:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-daily-schedule-status.json`

LLM optimizer boundary:

- The LLM may propose research tests against the active leads.
- Each proposal must cite evidence refs and condition contexts.
- `CASPCBAOptimizerGuard` can send proposals to `RESEARCH_QUEUE`,
  `FLAG_FOR_HUMAN_REVIEW`, or `REJECT`.
- It rejects live trading, broker `ACCEPT`, bank/debit/card movement, and
  guaranteed-income language.
- Hallucination prevention remains `OPEN`; the current guard is an evidence and
  authority boundary, not proof that a model cannot hallucinate.
- The current tally preserves the active walk-forward pocket: `EUR/USD` `D1`
  `normal` `range_scalper_24_120` has mean return `1.1483%` across `3` routed
  windows with `31` trades; GBP/USD also routed but has weaker mean return and
  only `1` trade in this tally.
- Owner-control modes are now explicit: `DENY`, `NOTIFY_ONLY`, `LIMITED_PAPER`,
  `PAPER_AUTO`, and `LIVE_AUTO`. `LIVE_AUTO` is blocked as
  `LIVE_BLOCKED_NOT_LICENSED`; `LIMITED_PAPER` / `PAPER_AUTO` are paper-only.
- Latest GO sprint shifted the strongest next paper-proof candidate to
  `index_tsmom_126_d1`: the D1 index TSMOM bucket cleared simulator and
  walk-forward thresholds in owner review, with only 30-day paper proof still
  blocking limited-paper authorization.

## Active Lead 1 - Range Scalper On Filtered FX

- lead id: `range_scalper_filtered_fx_d1`
- current setting: `range_scalper_24_120`
- current symbols: `EUR/USD`, `GBP/USD`
- watchlist symbol: `AUD/USD`
- excluded until condition-specific proof: `USD/JPY`, `USD/CAD`
- best current mode: D1 proxy range fade; expand next to `H1` and `M15`
- preferred condition: range, low-to-normal volatility, controlled spread
- avoid: macro blackout, shock, high spread, unvalidated symbol

Evidence:

- `cas-forex/evidence_runs/range_scalper_research/real-range_scalper-20260622043152-report.json`
- `cas-forex/evidence_runs/range_scalper_research/real-range_scalper-20260622043231-report.json`
- `cas-forex/evidence_runs/walk_forward_condition_lab/walk-forward-20260622044930-report.json`

Headline:

- 5 FX majors, 5y D1 Yahoo proxy, cost-included: `+$1,572.25`; chain verified; CAS improved P&L/drawdown.
- Filtered `EUR/USD GBP/USD AUD/USD`, 5y D1 Yahoo proxy, cost-included: `+$2,686.37`; avg max DD `2.38%`; chain verified.
- Corrected D1 walk-forward: `3 / 3` active routed windows positive; active routed mean return `1.2827%`; routed max DD `2.298%`; `32` routed trades; grade `NOT_PROMOTED` due sparse coverage.

Next gates:

- broker-grade bid/ask and spread/slippage by session
- `M15` / `H1` walk-forward grid
- macro/event-aware condition axis
- 30-trading-day paper proof before live funds

Deployment status: `NOT LICENSED`

## Active Lead 2 - Index TSMOM 126

- lead id: `index_tsmom_126_d1`
- current setting: `tsmom_126_250_2_10`
- current symbols: `US30`, `NAS100`
- watchlist symbol: `XAU/USD`
- best current mode: D1 index trend following
- preferred condition: trend-up or high-vol trend, not range/chop
- avoid: range, thin liquidity, unvalidated event context

Evidence:

- `cas-forex/evidence_runs/index_tsmom_h1_d1_go/walk-forward-20260622054921-report.json`
- `cas-forex/evidence_runs/condition_tally/condition-tally-20260622055042-report.json`
- `cas-forex/evidence_runs/index_tsmom_sdg_owner_go/condition-lab-20260622055024-report.json`
- `cas-forex/evidence_runs/owner_promotion_review/owner-promotion-review-20260622055433-report.json`

Headline:

- D1 walk-forward subreport returned `WALK_FORWARD_LEAD`: `8` D1 windows,
  `5` routed, `3` positive, positive routed window rate `0.6`, routed mean
  return `1.8932%`, max drawdown `7.0764%`, `76` trades.
- Custom D1 family tally for `tsmom_126_250_2_10`: `5` routed windows,
  positive rate `0.6`, mean return `1.8932%`, max DD `7.0764%`, `76` trades.
- CAS-SDG focused index sweep found top D1 trend-up/high-vol TSMOM routes on
  US30/NAS100, with `16` RPM routes.
- Owner review in `LIMITED_PAPER` mode cleared simulator and walk-forward
  thresholds for the D1 bucket; paper proof remains the promotion blocker.
- Paper-proof ledger started 2026-06-22 and now has a day-1 MT5 demo receipt:
  `1 / 30` completed days, `1 / 30` broker-verified days, local evidence chain
  verified, `passed=false`, blockers `paper_days 1 < required 30` and
  `broker_verified_days 1 < required 30`.
- Broker/demo receipt ingestion is now available. Hash-bound local exports are
  recorded as `BROKER_EXPORT_HASHED`; only a broker/demo adapter can mark
  a day `BROKER_API_VERIFIED` for the verified-source paper gate.
- MT5 demo adapter probe for 2026-06-22 returned `BROKER_API_VERIFIED` from
  `Hugosway-Demo`, with no orders executed and open positions reconciled.
- Daily paper route decision for 2026-06-22 returned `ROUTE_PAPER_SIGNAL`:
  US30 `LONG` confidence `0.4612`, NAS100 `LONG` confidence `0.7539`, macro
  `PASS`, event context `normal`, evidence packet `SUPPRESSED`, no broker order
  placed.
- Paper risk review for 2026-06-22 returned `PAPER_ATTEMPTS_ALLOWED`: `2 / 2`
  paper attempts allowed, `0.01` lots each, total planned paper risk `$25.30`
  / `0.506%` on `$5,000` paper equity, evidence packet `SUPPRESSED`, no broker
  order placed.
- Daily paper bundle for 2026-06-22 completed with all three tracks present:
  MT5 demo receipt, route/no-trade decision, and risk-budget review. The bundle
  skipped existing same-date records and did not duplicate proof packets.
- UI readiness gate currently says `NOT_READY_FOR_UI_UX`: complete daily
  bundles `1 / 5`, with paper proof, paper decision, and paper risk chains all
  verified.
- Daily schedule points to next due date `2026-06-23`, status
  `WAIT_NEXT_TRADING_DAY`, with broker receipt, route decision, and risk review
  still missing for that next date.

Next gates:

- 29 more real verified paper-trading days on NAS100/US30 D1 after the
  2026-06-22 MT5 demo-verified day.
- 4 more complete daily bundles before proof-cockpit UI/UX starts under the
  current `5`-bundle threshold.
- Run the next due daily bundle on `2026-06-23` or the next available real
  trading day.
- Run the daily paper bundle for each verified paper day and preserve receipt,
  route/no-trade, and risk-budget status.
- Broker-grade index/CFD spread and slippage validation.
- Event-context validation for NFP/FOMC/conflict shocks.
- Owner approval for any limited paper attempts; live remains `NOT LICENSED`.

Deployment status: `NOT LICENSED`

UI/UX checkpoint: not yet. The readiness gate is now explicit:
`NOT_READY_FOR_UI_UX` until at least `5` complete daily bundles exist. Current
state is `1 / 5`.

## Active Lead 3 - Index TSMOM 252

- lead id: `index_tsmom_252_d1`
- current setting: `tsmom_252_500_2_8`
- current symbols: `NAS100`, `US30`
- watchlist symbol: `XAU/USD`
- best current mode: swing/position trend following; expand next to `H4` and `H1`
- preferred condition: trend up/down, normal-to-high volatility, not shock
- avoid: range, shock, unvalidated trend detector

Evidence:

- `cas-forex/evidence_runs/strategy_edge_sprint_tsmom_252/real-tsmom-20260622041452-report.json`
- `cas-forex/evidence_runs/condition_lab_focus/condition-lab-20260622042733-report.json`
- `cas-forex/evidence_runs/temporal_lacunarity_focus/condition-lab-20260622044212-report.json`
- `cas-forex/evidence_runs/walk_forward_condition_lab/walk-forward-20260622044930-report.json`

Headline:

- Controlled NAS100/US30 TSMOM 252 research lead: approximately `+31.6%` portfolio with roughly `6.8%` avg DD in the strategy-edge sprint.
- Real-slice Condition Lab favored `tsmom_252_500_2_8` and `tsmom_126_250_2_10` for strongest index routes.
- D1 walk-forward stayed `NO_TRADE` on NAS100/US30 because recent future windows were labeled range. This is a condition-detection blocker, not a promotion.

Next gates:

- improve index trend/range detector so trend windows are not flattened into range
- `H1` / `H4` broker-grade walk-forward testing
- owner 2020 NAS30/NAS100 discretionary rule encoding
- drawdown cap plus trailing/time exits

Deployment status: `NOT LICENSED`

## Watchlist - Mean Reversion With Trend Filter

- lead id: `meanrev_trend_filter_fx_d1`
- setting: `meanrev_20_z2_tf`
- current status: `WATCHLIST_ONLY`

Reason:

- Thin in-sample positive on FX majors, but edge was close to zero and cost-sensitive.
- Keep it as a baseline/watchlist strategy, not as a deployment candidate.

Deployment status: `NOT LICENSED`

## Analyze, Simulate, Switch-Up Status

CAS Forex has tried the analyze/simulate/switch loop in five generations:

1. Synthetic CAS-SDG regime simulator:
   - tested strategy behavior across trend, range, high/low volatility, cluster, and shock
   - found high lacunarity, meaning no strategy wins everywhere
   - produced the first RPM route seed

2. Real-data hard regime switching:
   - daily switching did not beat the best single FX-major strategy
   - H1 switching also lost
   - lesson: switching machinery worked, but FX majors/daily bars were too homogeneous and cost drag dominated

3. Condition Lab:
   - added named settings, real-data slices, CJT operating regions, nested lacunarity, and RPM route/no-trade maps
   - real-slice run found strongest routes favoring index TSMOM variants

4. Temporal nested lacunarity:
   - added `S1`, `M1`, `H1`, `D1`, `MN1`, `Y1` time axes
   - proved architecture can map strategy gaps by timeframe/mode
   - first compact run was mostly a warning map, not a promotion

5. Walk-forward RPM:
   - trained route maps on one window and tested untouched future windows
   - range scalper survived active future windows, but route coverage was too sparse for promotion

Current answer: the strategy-switching idea is real and implemented as research
machinery, but not yet a final deployable strategy. The next correct build is a
multi-timeframe/mode router that chooses both `setting` and `timeframe/mode`
from a walk-forward-tested route map.

## Event / News Factoring Status

Already present:

- `MacroGate` exists in `cas-forex/cas_forex/verifier/macro_gate.py`.
- It includes static 2026 seed events for `NFP`, `CPI`, `FOMC`, `GDP`,
  `UNEMPLOYMENT`, `CENTRAL_BANK_SPEECH`, and `RATE_DECISION`.
- CJT macro-shock diagnostics exist and route to `LIVE_LOCKED`.
- `cas-forex/cas_forex/event_context.py` now makes event context a first-class
  route-map label for `normal`, macro pre/post windows, `conflict_shock`,
  `weekend_gap`, and `liquidity_thin`.
- Condition Lab and Walk-Forward RPM route keys now include `event_context`.

Not complete yet:

- Real-data backtests currently note that macro blackout is effectively inert
  because the backtest evaluates the macro gate at wall-clock time, not each
  historical candle's real release schedule.
- Conflict/geopolitical risk is now representable as `conflict_shock`, but
  actual conflict windows still need curated/provider-backed data.
- The static 2026 macro calendar is only a seed; historical NFP/CPI/FOMC
  release windows are not yet complete for 5y backtests.

Required next build:

- Add historical event calendars for NFP/CPI/FOMC/rate decisions.
- Add manually curated or provider-backed geopolitical/conflict shock windows.
- Teach RPM to route to `NO_TRADE`, reduce risk, or switch timeframe/mode when
  event context changes.
- Feed CAS-SDG / Condition Lab simulator wins into owner-control promotion
  reviews before any paper-mode automation.

Live trading remains `NOT LICENSED`.
