# CAS Forex Priority Synthesis

Date: 2026-06-22
Status: working synthesis for urgent CAS Forex focus
Claim boundary: CAS Forex live trading remains `NOT LICENSED`

## Third-Party Audit Before UI/UX - 2026-06-22

Before building the read-only CAS Forex proof cockpit UI, the owner requested an
independent third-party audit of the entire project. The audit packet is saved at
`docs/working/CAS_FOREX_THIRD_PARTY_AUDIT_PACKET_20260622.md` and includes local
file addresses, project spec sheet, evidence maps, reproduction commands, known
hotspots, and requested auditor deliverables. The corrected path is now:
third-party audit first, then read-only UI shell, while live trading, broker
`ACCEPT`, auto-deposit, debit/card/bank movement, and payout automation remain
`NOT LICENSED`.

## Executive Read

CAS Forex is a real, tested research/backtest chassis. It has market data ingestion,
forecast strategies, a 5-gate CAS auditor, risk controls, broker bridges, local
hash-chain Evidence Packets, CJT/PCBA diagnostic sidecars, a harvester/promotion
state machine, and handoff docs for an outside quant reviewer.

The current trading edge is still `OPEN`. The system proved something useful but
painful: simple strategies on FX majors do not survive realistic costs. The fastest
honest path is not to turn on live money. The fastest path is:

1. Extend the instrument model beyond FX majors to indices and gold.
2. Bring in broker-grade data/cost assumptions.
3. Run NAS100/US30/XAU trend/breakout and the owner's 2020 discretionary rules.
4. Add walk-forward/out-of-sample validation.
5. Only after a real edge exists, run actual 30-trading-day paper proof.

Plain English: the engine is built; the edge is not yet proven. The next dollar of
effort should test the market where the owner actually had a historical edge:
indices, especially NAS100/US30/NAS30 style instruments.

## Temporal Nested Lacunarity Update - 2026-06-22

CAS Forex now treats timeframe as a first-class condition axis in the Condition
Lab. Synthetic CAS-SDG sweeps can nest lacunarity across `S1`, `M1`, `H1`, `D1`,
`MN1`, and `Y1`, with the default gap map now ordered as:

`source -> symbol -> time_scale -> timeframe -> regime -> vol_mult -> family`

RPM route keys also include `time_scale` and `timeframe`, which means CAS can
eventually choose different strategy settings for scalping, day, swing, and
position modes instead of assuming one route fits every bar duration.

First compact NAS100 synthetic focus run, using `tsmom_252_500_2_8` and
`range_scalper_24_120` across `trend_up` and `range`:

- report: `cas-forex/evidence_runs/temporal_lacunarity_focus/condition-lab-20260622044212-report.json`
- chart: `docs/working/cas_forex_temporal_lacunarity_chart_20260622.png`
- cells: `24`
- overall gap fraction: `0.8750`
- `S1`, `M1`, `H1`: `100%` gap in this compact run
- `D1`, `MN1`, `Y1`: `75%` gap in this compact run
- RPM routes: `1`; `NO_TRADE`: `11`
- only route: synthetic `NAS100` `Y1` `trend_up` -> `tsmom_252_500_2_8`

Interpretation: the architecture now matches the owner's multi-timeframe idea,
but the first result is mostly a warning map. Short-timeframe profitability
cannot be inferred from daily Yahoo proxy data or synthetic scaling alone. The
next proof step is broker-grade M1/tick data, realistic spread/slippage by
session, and walk-forward RPM training/testing. Live trading remains
`NOT LICENSED`.

## Walk-Forward RPM Update - 2026-06-22

CAS Forex now has a walk-forward Condition Lab evaluator. It trains RPM routes
on a historical window, freezes the route map, then evaluates only the next
untouched future window. The evaluator uses prior training bars as lookback-only
context, so long-lookback settings such as `tsmom_252_500_2_8` can fire in the
test window without leaking training P&L into the score.

First corrected D1 Yahoo-proxy run:

- report: `cas-forex/evidence_runs/walk_forward_condition_lab/walk-forward-20260622044930-report.json`
- chart: `docs/working/cas_forex_walk_forward_rpm_chart_20260622.png`
- symbols: `NAS100`, `US30`, `EUR/USD`, `GBP/USD`, `AUD/USD`
- settings: `tsmom_252_500_2_8`, `range_scalper_24_120`
- windows: `18`
- routed windows: `7`
- active routed windows: `3`
- positive active routed windows: `3 / 3`
- routed total return-percent sum: `3.8480%`
- active routed mean return: `1.2827%`
- routed max drawdown: `2.2980%`
- total routed trades: `32`
- research grade: `NOT_PROMOTED`

Interpretation: the range-scalper survived the first out-of-sample check on the
active future windows, especially EUR/USD and one GBP/USD window. That is a
real lead worth protecting. It is still too sparse for promotion: many windows
were `NO_TRADE` or route-with-no-entry, and the D1 index route map did not
activate because the current detector labeled recent NAS100/US30 windows as
range. Next proof step: broker-grade M1/H1 data, better index condition
detection, and a larger walk-forward grid before paper proof. Live trading
remains `NOT LICENSED`.

## Winning Strategy Ledger - 2026-06-22

The current profitable leads are now preserved in both a machine-readable and a
human-readable ledger:

- machine ledger: `cas-forex/strategy_leads.json`
- loader/validator: `cas-forex/cas_forex/strategy_ledger.py`
- guard test: `cas-forex/tests/test_strategy_ledger.py`
- human ledger: `docs/working/cas_forex_winning_strategy_ledger_20260622.md`

Current front-of-mind leads:

| Priority | Lead | Current status | Next gate |
|---:|---|---|---|
| 1 | `range_scalper_filtered_fx_d1` | `ACTIVE_RESEARCH_LEAD`; strongest on EUR/USD and GBP/USD | Broker-grade M15/H1 walk-forward + event-aware filters |
| 2 | `index_tsmom_126_d1` | `ACTIVE_RESEARCH_LEAD`; strongest current index paper-proof candidate | 30-day paper proof on NAS100/US30 D1 |
| 3 | `index_tsmom_252_d1` | `ACTIVE_RESEARCH_LEAD`; older index trend lead, now secondary to 126 variant | Better trend detector + compare against 126 |
| 4 | `meanrev_trend_filter_fx_d1` | `WATCHLIST_ONLY`; thin/cost-sensitive | Only revive if broker-grade costs preserve edge |

Analyze/simulate/switch-up has been tried in multiple forms: synthetic CAS-SDG
regime simulation, hard real-data switching on D1/H1, Condition Lab RPM route
maps, temporal nested lacunarity, and walk-forward RPM. The machinery works, but
the current promoted direction is not "always switch"; it is "route only when
the condition has evidence, otherwise `NO_TRADE`." The missing next axis is
event context: NFP/CPI/FOMC and geopolitical/conflict shock states need to
become first-class Condition Lab and walk-forward keys.

## Event-Aware RPM Update - 2026-06-22

CAS Forex now has an event-context condition axis. This is the first version of
the user's requested "switch timeframe/mode as conditions require" layer for
macro/news/conflict states.

Added:

- `cas-forex/cas_forex/event_context.py`
- `event_context` on every Condition Lab cell
- synthetic `--event-contexts`
- optional real-data `--real-event-source static_macro`
- optional walk-forward `--event-source static_macro`
- default nested lacunarity/RPM axes now include `event_context`

Event labels currently supported:

- `normal`
- `pre_NFP`, `post_NFP`
- `pre_CPI`, `post_CPI`
- `pre_FOMC`, `post_FOMC`
- `pre_RATE_DECISION`, `post_RATE_DECISION`
- `pre_GDP`, `post_GDP`
- `pre_UNEMPLOYMENT`, `post_UNEMPLOYMENT`
- `pre_CENTRAL_BANK_SPEECH`, `post_CENTRAL_BANK_SPEECH`
- `conflict_shock`
- `weekend_gap`
- `liquidity_thin`

First compact synthetic event-context run:

- report: `cas-forex/evidence_runs/event_context_focus/condition-lab-20260622050947-report.json`
- cells: `96`
- gap fraction: `0.9062`
- RPM routes: `1`; `NO_TRADE`: `47`
- only route: synthetic `EUR/USD` `D1` `post_NFP` `trend_up` -> `tsmom_252_500_2_8`

First real static-macro walk-forward smoke:

- report: `cas-forex/evidence_runs/event_context_walk_forward_smoke/walk-forward-20260622051001-report.json`
- windows: `8`
- routes: `0`
- `NO_TRADE`: `8`

Interpretation: event context is now part of the switching machinery, and the
first behavior is appropriately conservative: untrained event windows do not
borrow normal-market routes. The missing piece is data quality. The static 2026
macro calendar is only a seed, and conflict/geopolitical windows need curated
or provider-backed event data before any event-conditioned route can be trusted.
Live trading remains `NOT LICENSED`.

## Guarded LLM Optimizer Update - 2026-06-22

CAS Forex now has the first scaffold for an LLM research optimizer attached to
CAS Harness / CAS PCBA style safety boundaries.

Added:

- `cas-forex/cas_forex/llm_optimizer.py`
- `cas-forex/cas_forex/condition_tally.py`
- `cas-forex/scripts/run_condition_tally.py`
- `cas-forex/tests/test_llm_optimizer.py`
- `cas-forex/tests/test_condition_tally.py`
- `docs/working/cas_forex_llm_optimizer_plan_20260622.md`

The intended loop is:

`strategy ledger -> evidence runs -> condition/event tally -> LLM proposal -> CASPCBAOptimizerGuard -> RESEARCH_QUEUE / FLAG_FOR_HUMAN_REVIEW / REJECT`

The LLM optimizer can summarize winning leads, compare condition tallies, and
propose research tests. It cannot place trades, unlock live trading, create
broker `ACCEPT`, move money through bank/debit/card rails, or promise income.
Proposals must cite a known strategy lead, evidence refs, condition contexts,
and the `NOT LICENSED` boundary.

Open-weight model planning is now a benchmark lane, not a hand-picked default.
Candidates include Qwen, Llama, Mistral, Gemma, and DeepSeek families, but any
model must pass evidence-grounding, JSON-contract, no-live-authority,
negative-control, drift, and cost checks before it becomes the CAS Forex
research assistant. Hallucination prevention remains `OPEN`; this pass adds a
guarded research proposal gate, not proof of hallucination prevention. Live
trading remains `NOT LICENSED`.

First saved condition tally:

- report: `cas-forex/evidence_runs/condition_tally/condition-tally-20260622052757-report.json`
- source: `cas-forex/evidence_runs/walk_forward_condition_lab/walk-forward-20260622044930-report.json`
- windows: `18`
- routed windows: `7`
- `NO_TRADE` windows: `11`
- positive routed windows: `3`
- event contexts: all legacy windows default to `normal`
- strongest current bucket: `EUR/USD` `D1` `normal` `range_scalper_24_120`,
  mean return `1.1483%`, `31` trades

## Owner-Controlled Simulator Promotion Update - 2026-06-22

The future LLM add-on is now explicitly allowed to use CAS-SDG / Condition Lab
through structured simulator requests, but the actual LLM remains a later build.
The immediate build added the owner-control policy that decides what happens
after enough wins exist.

Added:

- `cas-forex/cas_forex/owner_control.py`
- `cas-forex/scripts/run_owner_promotion_review.py`
- `cas-forex/tests/test_owner_control.py`

Owner modes:

- `DENY`: do nothing.
- `NOTIFY_ONLY`: notify only.
- `LIMITED_PAPER`: allow a fixed number of paper-mode attempts.
- `PAPER_AUTO`: allow automatic paper-mode routing.
- `LIVE_AUTO`: currently returns `LIVE_BLOCKED_NOT_LICENSED`.

This implements the owner's desired accept/deny idea without confusing owner
approval with broker `ACCEPT`. Current CAS Forex can review a strategy bucket
against thresholds, but it cannot use owner approval to bypass live gates.

First owner promotion review:

- source tally: `cas-forex/evidence_runs/condition_tally/condition-tally-20260622052757-report.json`
- report: `cas-forex/evidence_runs/owner_promotion_review/owner-promotion-review-20260622053731-report.json`
- requested mode: `LIMITED_PAPER`
- result: both routed buckets remain `NOTIFY`, not paper-authorized
- main blockers: no CAS-SDG win count attached yet, too few walk-forward windows,
  no 30-day paper proof, and no paper pass

This is the correct shape for the money goal: do not forget the urgent
`$5k-$12k/month` target, but force every "enough wins" claim through simulator,
walk-forward, paper proof, drawdown, and owner-control thresholds before any
automation. Profit sweep/deposit/debit/card movement remains `NOT LICENSED`.

## GO Sprint Evidence Update - 2026-06-22

CAS Forex now feeds CAS-SDG simulator wins into owner-control reviews.

Code updates:

- `cas-forex/cas_forex/owner_control.py` now counts Condition Lab simulator
  wins via `count_condition_lab_simulator_wins()`.
- `cas-forex/scripts/run_owner_promotion_review.py` accepts
  `--condition-lab-reports` and simulator filters.
- `cas-forex/scripts/run_condition_tally.py` accepts custom `--axes` so route
  families can be reviewed across symbols.
- `cas-forex/strategy_leads.json` now records `index_tsmom_126_d1` as priority
  2.

Range-scalper result:

- CAS-SDG focused report:
  `cas-forex/evidence_runs/range_scalper_sdg_owner_go/condition-lab-20260622054512-report.json`
- M15/H1 `range_scalper_24_120` walk-forward:
  `cas-forex/evidence_runs/range_scalper_m15_h1_walk_forward_go/walk-forward-20260622054614-report.json`
- M15/H1 variant walk-forward:
  `cas-forex/evidence_runs/range_scalper_variants_m15_h1_go/walk-forward-20260622054829-report.json`

Interpretation: the D1 range-scalper lead remains alive, but M15/H1 is not
ready. The `12_80` variant made short-timeframe results worse; do not promote it.

Index TSMOM result:

- walk-forward:
  `cas-forex/evidence_runs/index_tsmom_h1_d1_go/walk-forward-20260622054921-report.json`
- custom D1 tally:
  `cas-forex/evidence_runs/condition_tally/condition-tally-20260622055042-report.json`
- CAS-SDG:
  `cas-forex/evidence_runs/index_tsmom_sdg_owner_go/condition-lab-20260622055024-report.json`
- owner review:
  `cas-forex/evidence_runs/owner_promotion_review/owner-promotion-review-20260622055433-report.json`

The D1 `tsmom_126_250_2_10` bucket is now the strongest candidate:

- D1 subreport grade: `WALK_FORWARD_LEAD`
- D1 routed windows: `5`
- positive routed window rate: `0.6`
- routed mean return: `1.8932%`
- max drawdown: `7.0764%`
- trades: `76`
- owner review: simulator and walk-forward thresholds cleared; only paper proof
  remains

Next valid move: start or simulate the 30-trading-day paper-proof path for
`index_tsmom_126_d1` on NAS100/US30 D1, still with live trading `NOT LICENSED`.

## Paper-Proof Ledger Started - 2026-06-22

CAS Forex now has a lead-specific paper-proof path for `index_tsmom_126_d1`.

Added:

- `cas-forex/cas_forex/paper_proof.py`
- `cas-forex/scripts/run_paper_proof_plan.py`
- `cas-forex/tests/test_paper_proof.py`

Started ledger:

- plan:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-plan.json`
- status:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-status.json`
- evidence chain:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof.jsonl`
- receipt contract:
  `docs/working/cas_forex_paper_broker_receipt_contract_20260622.md`
- receipt template:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-receipt-template-20260622.json`

Current status:

- lead: `index_tsmom_126_d1`
- setting: `tsmom_126_250_2_10`
- symbols: `US30`, `NAS100`
- timeframe: `D1`
- completed trading days: `1 / 30`
- broker verified days: `1 / 30`
- chain verified: `true`
- passed: `false`
- blockers: `paper_days 1 < required 30`; `broker_verified_days 1 < required
  30`

Interpretation: the best current index lead is no longer just a research note;
it has a persistent proof ledger. This still does not authorize live trading.
The next valid move is to attach a real broker/demo paper source, append one
verified trading day at a time, and require the full 30-day proof before any
paper automation expands. Live trading, broker `ACCEPT`, auto-deposit,
debit/card/bank movement, and payout automation remain `NOT LICENSED`.

## Paper Broker Receipt Gate - 2026-06-22

CAS Forex now has the receipt-ingestion layer needed before a real demo/paper
broker source can feed the 30-day proof ledger.

The proof gate separates evidence levels:

- `PLAN_ONLY`: daily heartbeat only.
- `BROKER_EXPORT_HASHED`: local broker/demo export was schema-checked and
  hash-bound, but not API-authenticated.
- `BROKER_API_VERIFIED`: reserved for a broker/demo adapter that verifies the
  receipt directly from the paper source.

Code updates:

- `cas-forex/cas_forex/paper_proof.py` validates paper receipts, hashes them,
  rejects live-mode receipts, and keeps duplicate-date receipt events from
  inflating the day count.
- `cas-forex/scripts/run_paper_proof_plan.py` now supports
  `--broker-receipt` and `--write-receipt-template`.
- `cas-forex/tests/test_paper_proof.py` verifies receipt validation, duplicate
  date handling, live receipt rejection, and the future API-verified path.

Current status remains deliberately conservative: the active status report is
still `1 / 30`, chain verified, `passed=false`. The MT5 demo adapter has now
verified the first broker-source day, but the 30-day paper gate remains open.
The next valid move is to run the MT5 demo receipt probe each trading day,
record route/no-trade decisions, and preserve the `NOT LICENSED` live boundary.

## MT5 Demo Receipt Adapter - 2026-06-22

CAS Forex now has an MT5 demo adapter for paper-proof receipts.

Added:

- `cas-forex/cas_forex/paper_broker_adapter.py`
- `cas-forex/scripts/run_mt5_paper_receipt.py`
- `cas-forex/tests/test_paper_broker_adapter.py`

Real probe result:

- command:
  `python scripts/run_mt5_paper_receipt.py --date 2026-06-22 --append-if-verified --output-dir evidence_runs/index_tsmom_126_paper_proof`
- probe:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-mt5-demo-probe-20260622153728.json`
- status: `BROKER_API_VERIFIED`
- server: `Hugosway-Demo`
- terminal: `MetaTrader 5`
- receipt hash:
  `94d68da3b3c4d7bd13e29f69df60e1ff1d7938757e0e8e3d9aec613976704c0c`
- orders attempted/executed: `0 / 0`
- open positions reconciled: `true`

Updated active proof status:

- completed days: `1 / 30`
- broker verified days: `1 / 30`
- packet count: `2`
- chain verified: `true`
- passed: `false`

UI/UX correction after owner pushback: do not wait a month, and do not wait for
five complete daily bundles, to start the platform UI/UX. Start the read-only
proof cockpit now using the current day-1 MT5 demo receipt, daily route/no-trade
decision, risk review, bundle status, and schedule. The `5` complete-bundle
threshold only gates truthful multi-day proof maturity inside the UI. The
`30 / 30` paper-proof threshold only gates live-money/deployment promotion.
Any live-order, broker `ACCEPT`, auto-deposit, debit/card/bank, or payout
automation control must remain disabled and labeled `NOT LICENSED`.

## Daily Paper Route Decision Loop - 2026-06-22

CAS Forex now records daily paper route/no-trade intent separately from broker
receipt proof.

Added:

- `cas-forex/cas_forex/paper_decision.py`
- `cas-forex/scripts/run_paper_route_decision.py`
- `cas-forex/tests/test_paper_decision.py`
- `docs/working/cas_forex_daily_paper_decision_loop_20260622.md`

First daily decision:

- command:
  `python scripts/run_paper_route_decision.py --date 2026-06-22 --append-decision --output-dir evidence_runs/index_tsmom_126_paper_proof`
- status:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-paper-decision-status.json`
- decision chain:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-paper-decisions.jsonl`
- route action: `ROUTE_PAPER_SIGNAL`
- macro status: `PASS`
- event context: `normal`
- US30: `LONG`, confidence `0.4612`
- NAS100: `LONG`, confidence `0.7539`
- evidence status: `SUPPRESSED`
- broker order placed: no

Interpretation: CAS now has both sides of the daily paper loop for the active
lead: MT5 demo source proof plus strategy route/no-trade intent. This is still
paper-only evidence, not live permission. The risk-budget sizing layer below
completes the current day-1 backend bundle.

## Paper Risk-Budget Loop - 2026-06-22

CAS Forex now records paper risk-budget sizing separately from route decisions.

Added:

- `cas-forex/cas_forex/paper_risk.py`
- `cas-forex/scripts/run_paper_risk_review.py`
- `cas-forex/tests/test_paper_risk.py`
- `docs/working/cas_forex_paper_risk_budget_loop_20260622.md`

First daily risk review:

- command:
  `python scripts/run_paper_risk_review.py --account-equity 5000 --max-risk-pct 0.5 --daily-risk-pct 1.0 --append-review --output-dir evidence_runs/index_tsmom_126_paper_proof`
- status:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-paper-risk-status.json`
- risk status: `PAPER_ATTEMPTS_ALLOWED`
- account equity used: `$5,000`
- proposed attempts: `2`
- allowed attempts: `2`
- suppressed attempts: `0`
- US30: `0.01` lots, planned paper risk `$12.60`
- NAS100: `0.01` lots, planned paper risk `$12.70`
- total planned paper risk: `$25.30` / `0.506%`
- evidence packet: `SUPPRESSED`
- broker order placed: no

Interpretation: the day-1 paper loop now has MT5 demo source proof, strategy
route/no-trade intent, and risk-budget sizing. The next backend step is a
repeatable daily runner/scheduler that produces all three records per trading
day and handles no-trade/macro-lock days cleanly. UI/UX should start after that
daily bundle is stable across several days.

## Daily Paper Bundle - 2026-06-22

CAS Forex now has the repeatable daily backend bundle for the active paper-proof
lead.

Added:

- `cas-forex/cas_forex/paper_daily_bundle.py`
- `cas-forex/scripts/run_daily_paper_bundle.py`
- `cas-forex/tests/test_paper_daily_bundle.py`
- `docs/working/cas_forex_daily_paper_bundle_20260622.md`

First bundle run:

- command:
  `python scripts/run_daily_paper_bundle.py --date 2026-06-22 --account-equity 5000 --max-risk-pct 0.5 --daily-risk-pct 1.0 --output-dir evidence_runs/index_tsmom_126_paper_proof`
- status:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-daily-bundle-status.json`
- completed: `true`
- MT5 demo receipt: `SKIPPED_EXISTING`
- paper route decision: `SKIPPED_EXISTING`
- paper risk review: `SKIPPED_EXISTING`
- reason: all three day-1 records already existed, so no duplicate proof
  packets were appended

Interpretation: there is now a practical one-command daily paper loop. The next
move is to run it for each real trading day until there are enough daily bundles
to build a truthful proof cockpit. UI/UX is close, but still should wait for
several real daily bundle records.

## UI Readiness Gate - 2026-06-22

CAS Forex now has an explicit proof-cockpit readiness gate.

Added:

- `cas-forex/cas_forex/paper_ui_readiness.py`
- `cas-forex/scripts/run_paper_ui_readiness.py`
- `cas-forex/tests/test_paper_ui_readiness.py`
- `docs/working/cas_forex_ui_readiness_gate_20260622.md`

First real readiness check:

- command:
  `python scripts/run_paper_ui_readiness.py --min-daily-bundles 5 --output-dir evidence_runs/index_tsmom_126_paper_proof`
- status:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-ui-readiness-status.json`
- readiness status: `NOT_READY_FOR_UI_UX`
- complete daily bundles: `1 / 5`
- broker verified days: `1 / 5`
- decision days: `1 / 5`
- risk review days: `1 / 5`
- all three local paper chains verified: `true`

Interpretation: this is now the concrete UI/UX trigger. Start the proof cockpit
after `5` complete daily paper bundles. Current state is `1 / 5`, so the next
move remains running the daily bundle each real trading day.

## Daily Schedule / Next Action - 2026-06-22

CAS Forex now has a read-only next-action schedule for the paper-proof loop.

Added:

- `cas-forex/cas_forex/paper_daily_schedule.py`
- `cas-forex/scripts/run_paper_daily_schedule.py`
- `cas-forex/tests/test_paper_daily_schedule.py`
- `docs/working/cas_forex_daily_schedule_20260622.md`

First real schedule check:

- command:
  `python scripts/run_paper_daily_schedule.py --date 2026-06-22 --account-equity 5000 --max-risk-pct 0.5 --daily-risk-pct 1.0 --output-dir evidence_runs/index_tsmom_126_paper_proof`
- status:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-daily-schedule-status.json`
- latest complete bundle date: `2026-06-22`
- next due date: `2026-06-23`
- next due status: `WAIT_NEXT_TRADING_DAY`
- UI bundles remaining: `4`
- full paper-proof days remaining: `29`
- missing tracks for next due date:
  `broker_verified_receipt`, `paper_route_decision`, `paper_risk_review`

Recommended next command:

`python scripts/run_daily_paper_bundle.py --date 2026-06-23 --account-equity 5000 --max-risk-pct 0.5 --daily-risk-pct 1 --output-dir evidence_runs/index_tsmom_126_paper_proof`

## Sources Reviewed

- `docs/working/CAS_FOREX_HANDOFF_20260621.md`
- `docs/working/CAS_FOREX_FIVERR_BRIEF_ONEPAGE.md`
- `cas-forex/CHANGELOG.md`
- `cas-forex/cas_forex/`
- `cas-forex/evidence_runs/`
- `docs/working/cas_forex_pcba_engineer_book_fit_20260620.md`
- `docs/working/cjt_pcba_cas_forex_ecosystem_fit_analysis_20260617.md`
- `docs/working/cas_harness_forex_trading_execution_plan.md`
- `docs/working/cas_forex_pwa_ui_ux_plan_revised_20260617.md`
- `docs/working/cas_harness_production_todo.md`
- `book/CAS_PCBA_Engineer/`
- `_tmp_TKS_FORMAL_MATHEMATICAL_MANUAL_v6_1_COMPLETE.txt`
- Official CFTC/NFA guidance checked 2026-06-22:
  - https://www.cftc.gov/check
  - https://www.cftc.gov/LearnAndProtect/Resources/Check/redlist.htm
  - https://www.nfa.futures.org/members/member-resources/files/forex-regulatory-guide.html
  - https://www.nfa.futures.org/registration-membership/who-has-to-register/rfed.html

## What We Know CAS Forex Already Has

### Built code

- Backtest engine: `cas-forex/cas_forex/backtest/engine.py`
- Auditor/gates: `cas-forex/cas_forex/verifier/`
- Forecast strategies: `cas-forex/cas_forex/forecast/strategies.py`
- Chronos signal integration: `cas-forex/cas_forex/forecast/chronos_signal.py`
- Yahoo/OANDA market-data connector: `cas-forex/cas_forex/market_data/connector.py`
- MT5, MT4 mailbox, and simulated broker bridges: `cas-forex/cas_forex/broker/mt5_bridge.py`
- Local append-only evidence chain: `cas-forex/cas_forex/evidence_store.py`
- Evidence packet schemas: `cas-forex/cas_forex/schemas/evidence.py`
- CJT/PCBA diagnostics and circuit views: `cas-forex/cas_forex/cjt_diagnostics.py`, `cjt_circuit_view.py`, `crc_linter.py`
- Regime simulator/switching: `cas-forex/cas_forex/regime_sim.py`
- Harvester/promotion controller: `cas-forex/cas_forex/harvester.py`
- Paper proof scaffold: `cas-forex/scripts/run_paper_trading_session.py`
- Repro runners: `cas-forex/scripts/run_real_backtest.py`, `run_strategy_simulator.py`, `run_switching_backtest.py`

### Built docs

- External technical handoff: `docs/working/CAS_FOREX_HANDOFF_20260621.md`
- Fiverr one-pager: `docs/working/CAS_FOREX_FIVERR_BRIEF_ONEPAGE.md`
- PCBA fit audit: `docs/working/cas_forex_pcba_engineer_book_fit_20260620.md`
- CJT/PCBA ecosystem fit: `docs/working/cjt_pcba_cas_forex_ecosystem_fit_analysis_20260617.md`
- UI/proof cockpit plan: `docs/working/cas_forex_pwa_ui_ux_plan_revised_20260617.md`
- Original Harness forex execution plan: `docs/working/cas_harness_forex_trading_execution_plan.md`

## Evidence Results

### Real FX-major strategy tests

All of these used real Yahoo data over five FX majors unless noted:

| Run | Result | Meaning |
|---|---:|---|
| SMA trend, 5y daily | `-$15,097.88` gated, `13,554` packets, chain verified | Trend-following loses on FX majors |
| Chronos, 5y daily | `-$15,574.25` gated, `19,660` packets, chain verified | Bigger ML forecaster did not solve the edge |
| Mean-reversion | `-$523.45` gated, `2,824` packets, chain verified | Correcter regime, near break-even |
| Mean-reversion + trend filter | `+$105.62` gated, `1,156` packets, chain verified | First thin positive in-sample result |
| Cost sweep | `+$91.47`, `+$28.39`, `-$31.48`, `-$94.80` | Thin result flips negative around normal retail all-in cost |

The break-even conclusion is the core survival fact. A strategy that makes roughly
zero over five years on a simulated `$50,000` portfolio cannot rationally fund CAS
projects or living expenses from a small account.

### CAS methodology/regime results

The simulator works as a strategy-behavior map:

- Regimes tested: `trend_up`, `trend_down`, `range`, `high_vol`, `low_vol`, `vol_cluster`, `shock`.
- Overall lacunarity: `0.5833333333333334`, meaning most strategy x regime x volatility cells are unvalidated gaps.
- RPM routing seed:
  - `trend_up`, `trend_down`, `high_vol` -> `breakout`
  - `range`, `shock` -> `meanrev`
  - `low_vol` -> `trend_sma`
  - `vol_cluster` -> `None` / no trade

The live regime switcher did not beat the best single FX-major strategy:

- Daily switching report: `SWITCH -$2,040.26`, while `meanrev_tf` was `+$9.90` in that run.
- H1 switching report: every variant lost; `SWITCH -$4,715.23`, best single `meanrev_tf -$4,123.09`.
- Detector read daily majors as mostly `range`, so switching had little genuine work to do.

Conclusion: the CAS methodology layer is useful, but it needs a market with real
regime variety and multiple strategies that each own a regime. Indices are the
obvious next market.

### First index/gold wiring pass, completed 2026-06-22

After this synthesis started, CAS Forex gained the first non-FX instrument layer:

- `cas-forex/cas_forex/instruments.py`
- metadata-backed `NAS100`, `US30`, and `XAU/USD` support
- Yahoo mappings: `NAS100 -> ^NDX`, `US30 -> ^DJI`, `XAU/USD -> GC=F`
- MT5 mappings through the same registry, including `XAU/USD -> XAUUSD`
- metadata-backed point value / notional math in the backtest engine
- regression tests for NAS100 point P&L, XAU/USD contract point value, and non-FX mappings

Verification: `python -m pytest tests -q` in `cas-forex` now reports `220 passed`.

First research-only Yahoo proxy runs:

| Run | Result | Meaning |
|---|---:|---|
| `breakout`, `NAS100 US30 XAU/USD`, 5y daily | `-$9,833.96` portfolio | XAU/USD wiped out the portfolio; isolate gold from index tests |
| `sma`, `NAS100 US30`, 5y daily | `-$954.72` portfolio | NAS100 positive, US30 negative; not enough |
| `breakout`, `NAS100 US30`, 5y daily | `+$299.62` portfolio | Positive but tiny; no CAS improvement over raw; buy-and-hold dominated |

This proves indices/gold are now runnable through the harness. It does not prove a
deployable edge. The next edge attempt should encode the owner's actual 2020
NAS30/NAS100 rules, add trailing/time exits, and run walk-forward validation on
broker-grade bid/ask data.

## What Went Wrong

Nothing appears broken in the chassis. The negative result is consistent across
multiple strategies and model classes. The problem is scope.

- The tests focused on FX majors, a highly efficient and mostly ranging retail market.
- The strategies were textbook-simple: SMA trend, Donchian breakout, z-score mean reversion, naive Chronos direction.
- The system did not test NAS100/US30/NAS30, the market tied to the owner's actual 2020 wins.
- The system did not encode the owner's discretionary rules.
- Data was Yahoo mid-price, not broker bid/ask tick or M1 data.
- Fill/cost modeling is still simplified.
- There is no walk-forward/out-of-sample harness yet.
- The paper proof runner is a scaffold with synthetic daily heartbeats, not real 30-day paper evidence.

## How CAS_PCBA_Engineer Strengthens CAS Forex

The PCBA book helps most as an engineering and evidence layer, not as trading
authority.

Best additions:

1. CCDL Forex pipeline board spec:
   `ForecastHarness -> CASCompilerGate -> RiskGate -> MacroGate -> MarketGate -> ExecutionGate -> BrokerBridge -> PostTradeHarness`
2. Fixed trade test points:
   - `TP1_forecast`
   - `TP2_cas`
   - `TP3_risk_macro_market`
   - `TP4_execution`
   - `TP5_post_trade`
3. CSB for safety/lock explanations.
4. CDAB for model/baseline disagreement.
5. CMB for evidence memory and lacunarity by symbol/session/timeframe/regime.
6. CPMB for risk-budget ledgers.
7. COB for session rhythm, volatility rhythm, and repeated failure cycles.
8. Chapter 23-style fault injection proving missing safety components fail closed.
9. Chapter 25-style circuit registry and rollback discipline.

Hard boundary:

- CCDL/CJT/PCBA/CCB must not create broker `ACCEPT`.
- They may explain, `SUPPRESS`, `FLAG_FOR_HUMAN_REVIEW`, or contribute to `LIVE_LOCKED`.
- CAS Forex live trading remains `NOT LICENSED`.

## How CAS Harness Strengthens CAS Forex

CAS Harness gives CAS Forex a product/proof spine:

- Evidence Packet discipline.
- Local hash-chain now; WORM/Object Lock later if a claim requires it.
- `/verify` style thinking for evidence replay.
- UI proof center instead of a fake "live trading cockpit."
- Worker/token/auth/account-boundary discipline.
- Claim-status discipline: do not call research evidence a live feature.

Useful transfer:

- Add a CAS Forex proof route and evidence viewer to the Atlas/CAS Harness UI.
- Treat every trade proposal as an Evidence Packet lifecycle.
- Add proof gates for 12-month backtest, 30 real paper trading days, broker account proof, legal/account acknowledgments, and no active `LIVE_LOCKED`.
- Keep public/product wording in research mode until those gates close.

## How TKS_FORMAL_MANUAL_v6.1_CLEAN Strengthens CAS Forex

The TKS manual contributes formal discipline:

- RPM monad: every trade must satisfy prerequisites before action. In trading terms: desire to profit is not enough; the chain needs market evidence, strategy proof, risk budget, cost realism, broker proof, and legal/account permission.
- Failure propagation: one failed prerequisite stops the computation. A failed cost model or missing broker-data proof should suppress the trade, not get waved through.
- Fractal calculus: useful as a lens for repeated market/strategy patterns, stability, and convergence. In product terms, use it to study recurring loss signatures and stable strategy regimes, not to assert mystical predictive power.
- Type/effect system: useful for preventing status confusion. Research result, paper proof, live permission, and broker execution are different types.

Plain-English map:

- RPM = checklist that stops the line when one required box is missing.
- Fractal/stability = repeated pattern behavior across time and scale.
- Effect typing = label that prevents a research result from being mistaken for live authorization.

## Legal And Broker Boundary

This is not legal advice. For a U.S.-located retail user, official CFTC/NFA materials
make broker registration and status checks non-optional before live activity.

Current official checks to keep in the workflow:

- CFTC registration/background check: https://www.cftc.gov/check
- CFTC RED List: https://www.cftc.gov/LearnAndProtect/Resources/Check/redlist.htm
- NFA forex regulatory guide: https://www.nfa.futures.org/members/member-resources/files/forex-regulatory-guide.html
- NFA RFED registration page: https://www.nfa.futures.org/registration-membership/who-has-to-register/rfed.html

CAS Forex should continue to enforce:

- personal-account only for any future live path
- no pooled capital
- no family/friend/client/fee-based account automation
- no auto bank/card transfer
- no martingale/grid/no-stop-loss systems
- `paper_trading=True`, `live_mode=False` until licensed gates close

## Immediate Build Plan

### Phase 1: Index/gold instrument model

Goal: make the engine understand non-FX point/tick economics.

Add an instrument metadata layer:

- symbol
- asset class: `FX`, `INDEX_CFD`, `METAL_CFD`
- price precision
- tick size
- tick value
- point value
- contract size
- min/max lot
- margin/leverage assumptions
- spread units
- slippage units

Then extend:

- `SUPPORTED_SYMBOLS`
- `pip_multiplier` replacement or wrapper
- P&L calculation
- stop-distance/risk calculation
- tests for `NAS100`, `US30`, `XAU/USD`, and `USD/JPY`

### Phase 2: Data and cost realism

Goal: stop relying only on Yahoo mid-price for deployability decisions.

Add either:

- broker MT5/MT4 historical export import, or
- OANDA/Dukascopy/broker CSV adapter, or
- a fixture format for bid/ask M1/tick data.

Record:

- bid/ask spread by timestamp
- commission
- slippage model
- session
- rollover/swap if relevant
- unavailable/holiday gaps

### Phase 3: NAS100/US30/XAU research runs

Run:

- trend SMA
- Donchian breakout
- ATR breakout/trailing stop
- mean-reversion only as a control
- owner 2020 rule encoding, once described

Acceptance:

- cost-included positive result
- drawdown tolerable
- enough trades to matter
- beats no-trade and naive buy/hold or exposure baseline
- clear chain verification

### Phase 4: Walk-forward harness

Add train/validate/test splits:

- expanding window
- rolling window
- per-symbol and portfolio aggregation
- parameter selection only on training/validation
- final test kept untouched

No strategy should move toward paper proof without this.

### Phase 5: Actual paper proof

Replace synthetic paper heartbeat with real paper-mode proposal/order lifecycle:

- live market snapshot
- forecast proposal
- CAS audit
- simulated/MT5 demo order
- broker outcome
- post-trade reconciliation
- evidence packet
- daily summary

The current paper runner is useful scaffolding only. It explicitly does not satisfy
actual 30-trading-day proof.

### Phase 6: Proof UI

Build the PWA proof center first:

- `NOT LICENSED` / paper/sim banner
- backtest proof state
- paper proof state
- evidence-chain verification
- disabled live actions with reasons
- missing-gates list

Do not build a glossy live-trading cockpit before proof exists.

## Fastest Honest Next Move

Implement Phase 1 and Phase 3 together:

1. Add non-FX instrument metadata and point-value math.
2. Add tests that prove NAS100/US30/XAU P&L and risk math.
3. Run the existing trend/breakout harness on index/gold data, even if the first data source is Yahoo proxy data.
4. Immediately mark the result as research-only until broker-grade bid/ask data confirms it.

This is the first path that might discover a real edge quickly without violating
the `NOT LICENSED` boundary.

## Strategy Edge Sprint Update - 2026-06-22

We found the first positive index research lead after adding adaptive ATR,
explicit index/gold metadata, and new strategy candidates.

Test setup:

- `NAS100` + `US30`
- 5y daily Yahoo proxy data
- `0.1` lots per trade
- `1.0` spread + `1.0` extra cost
- research-only backtest, not broker-grade bid/ask data

Results:

- Raw TSMOM 126: `+123.5%` portfolio, avg max DD `58.6%`. This is a dangerous
  overtrading profile, not a promotable system.
- TSMOM 126 max1: `+6.8%` portfolio, avg max DD `4.3%`.
- TSMOM 126 max2: `+13.2%` portfolio, avg max DD `7.6%`.
- TSMOM 126 TP10 max2: `+17.2%` portfolio, avg max DD `5.7%`.
- Pullback 126: `+9.1%` portfolio, avg max DD `6.9%`.
- TSMOM 252 with correlated-exposure cap: `+31.6%` portfolio, avg max DD
  `6.8%`. This is the current best controlled research lead.

Decision:

- Promote TSMOM 252 to walk-forward validation.
- Keep raw overtrading out of the promotion path.
- Add trailing/time exits before any paper-proof claim.
- Confirm with broker-grade bid/ask data.
- Keep live trading `NOT LICENSED`.

Chart:

- `docs/working/cas_forex_strategy_edge_sprint_chart_20260622.png`

## Condition Lab Update - 2026-06-22

We now have the simulator layer needed to test the idea directly: play strategy
settings across synthetic CAS-SDG regimes and real market windows, classify each
cell with CJT, mark lacunae with nested lacunarity, and emit RPM route/no-trade
recommendations.

New files:

- `cas-forex/cas_forex/condition_lab.py`
- `cas-forex/scripts/run_condition_lab.py`
- `cas-forex/tests/test_condition_lab.py`

What it does:

- sweeps named strategy settings, not just strategy families
- supports synthetic CAS-SDG regimes and real Yahoo proxy windows
- labels cells by `source`, `symbol`, `regime`, `vol_mult`, and `family`
- classifies each cell as CJT `active`, `cutoff`, `saturation`, or `breakdown`
- computes nested lacunarity across condition axes
- routes by RPM prerequisites to either a setting or `NO_TRADE`

First focused synthetic run:

- `NAS100` + `US30`
- 4 settings: `tsmom_252_500_2_8`, `tsmom_126_250_2_10`,
  `pullback_126_5`, `breakout_55_2_6`
- 7 regimes x 3 volatility levels x 1 seed
- cells: `168`
- overall nested-lacunarity gap fraction: `0.8333`
- RPM routes: `19`
- `NO_TRADE`: `23`

First focused real-slice run:

- 5y daily Yahoo proxy data
- 420-bar windows, 120-bar step
- cells: `20`
- overall nested-lacunarity gap fraction: `0.1500`
- RPM routes: `5`
- `NO_TRADE`: `0`
- strongest real routes favored `tsmom_252_500_2_8` and
  `tsmom_126_250_2_10`

Interpretation:

- This is the right architecture for condition-aware switching.
- Synthetic coverage is deliberately harsh and exposes many lacunae.
- Real daily index slices currently favor time-series momentum settings.
- The next required step is walk-forward routing: learn the RPM map on one
  period, freeze it, then judge it on a future untouched period.
- Live trading remains `NOT LICENSED`.

## Capital Goal And Sweep Update - 2026-06-22

User target:

- seed account: `$2k-$5k`
- desired monthly income: `$5k-$12k+`
- user-controlled split between reinvestment and payout
- user-controlled risk budget
- eventual option for bank/debit/pre-funded-account flows

Math boundary:

- `$5k/month` from `$5k` seed requires `100%` monthly return.
- `$12k/month` from `$2k` seed requires `600%` monthly return.
- The new capital planner classifies the stated target range as
  `SURVIVAL_RISK`, not as a normal expected return.

New support:

- `cas-forex/cas_forex/capital_plan.py` converts seed, target, risk budget, and
  reinvest/payout/reserve split into an explicit plan.
- The linked sweep policy defaults to `DRY_RUN` and
  `INTERNAL_LEDGER_ONLY`.
- Provider/bank/debit/card automation remains `NOT LICENSED` until broker,
  payment-provider, allowlist, receipt, idempotency, tax, and legal gates close.

## Low-Volatility Range-Scalper Update - 2026-06-22

Checked the public Forex Fury pattern and translated the safe part into a CAS
research candidate: low-volatility range fading with small targets and strict
filters. This is not a copy of proprietary strategy files and not an endorsement.

New support:

- `make_low_vol_range_scalper_signal()` in `forecast/strategies.py`
- `--model range_scalper` in `scripts/run_real_backtest.py`
- `range_scalper_24_120` and `range_scalper_12_80` in the condition lab

Initial research-only FX-major results, 5y daily Yahoo proxy data, `0.05` lots,
`1.0` spread + `1.0` extra cost:

- all 5 majors: portfolio `+$1,572.25`; chain verified; CAS gating improved P&L
  and drawdown; USD/JPY and USD/CAD were negative.
- filtered EUR/USD, GBP/USD, AUD/USD: portfolio `+$2,686.37`; avg max DD
  `2.38%`; chain verified; CAS lowered drawdown.

Decision:

- Promote range-scalper to condition-lab and walk-forward testing.
- Do not promote USD/JPY or USD/CAD without a condition-specific reason.
- Treat this as a second research lead alongside index TSMOM.
- Live trading remains `NOT LICENSED`.

## Survival Note

CAS Forex should be prioritized, but not because it is ready to generate income
today. It should be prioritized because the engine is already built and the next
experiment is sharply defined. The survival-safe move is to use CAS discipline to
avoid desperation trading:

- no live money until edge and paper proof exist
- no high leverage to "catch up"
- no martingale/grid/no-stop systems
- no family/friend/client/pooled money
- spend effort only on tests that can change the decision

The strongest immediate business asset may be the audited trading research/proof
chassis itself, while the trading edge remains `OPEN`.
