# CAS Forex Third-Party Audit Packet

Date: 2026-06-22
Purpose: pre-UI/UX third-party audit handoff
Claim boundary: CAS Forex is research/paper infrastructure only. Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and payout automation remain `NOT LICENSED`.

## Copy-Paste Auditor Brief

We need an independent audit of CAS Forex before building the UI/UX proof cockpit.

CAS Forex is a Python research/backtesting and paper-proof system for FX, indices, and gold. It contains market-data ingestion, instrument metadata, strategy signal generation, a backtest engine, risk/macro/market/execution gates, local hash-chain evidence packets, CAS-SDG synthetic simulations, Condition Lab route maps, nested lacunarity, CJT/RPM-style condition classification, walk-forward testing, a strategy-lead ledger, guarded LLM optimizer scaffolding, owner-controlled promotion policy, MT5 demo receipt verification, daily paper route/no-trade records, paper risk-budget records, and a daily paper bundle/schedule.

The audit goal is not to rubber-stamp live trading. The audit goal is to identify whether the code, math, data assumptions, evidence chain, strategy validation, risk controls, and `NOT LICENSED` live-money boundaries are strong enough to justify building a read-only CAS Forex proof cockpit UI.

We need findings with file/line references, severity labels, and concrete fixes. Please prioritize:

- trading/backtest correctness
- transaction-cost, spread, slippage, fill, stop/target, and position-value assumptions
- lookahead/leakage/overfitting risks
- broker-grade data gaps versus Yahoo proxy data
- strategy promotion logic and paper-proof gates
- live-trading/payment-transfer lockouts
- MT5 demo receipt safety
- evidence-chain integrity
- UI/UX readiness and what the UI may truthfully display
- compliance/legal risk wording, especially around income claims and live automation

Important current status:

- The project is not live-money ready.
- The trading edge remains `OPEN`.
- The strongest current candidate is `index_tsmom_126_d1`, still paper-only.
- The paper ledger has only `1 / 30` verified paper days.
- The read-only UI shell may start after audit, but live controls must remain disabled.
- The user target of `$5k-$12k/month` from `$2k-$5k` seed is labeled `SURVIVAL_RISK`, not a promise or expected return.

## Local Workspace Addresses

Workspace root:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS
```

CAS Forex root:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex
```

Current Git info captured 2026-06-22:

```text
repo root: C:\Users\wakil\OneDrive\Desktop\tksCAS
branch: codex/cascompass-legal-live-source
HEAD: 125079d9
remote: https://github.com/LittleHenderson/noetic-compass.git
```

Critical audit note: the working tree currently contains local uncommitted and untracked CAS Forex work from the sprint. Audit the local folder above, not just the remote branch, unless a fresh commit/push is made before handoff.

## Project Spec Sheet

Project name:

```text
CAS Forex
```

Primary goal:

```text
Find, verify, and preserve cost-surviving trading strategy leads, then display proof state in a read-only UI before any live-money path is considered.
```

Current product stage:

```text
Research + backtesting + paper-proof infrastructure. Not a live trading platform.
```

Current deployment status:

```text
NOT LICENSED
```

Main instruments:

```text
FX majors: EUR/USD, GBP/USD, AUD/USD, USD/JPY, USD/CAD
Index/gold research: NAS100, US30, XAU/USD
```

Main strategy families:

```text
sma, chronos, meanrev, breakout, tsmom, pullback, range_scalper
```

Current front-of-mind leads:

```text
1. range_scalper_filtered_fx_d1 - ACTIVE_RESEARCH_LEAD, strongest on EUR/USD and GBP/USD, not promoted.
2. index_tsmom_126_d1 - ACTIVE_RESEARCH_LEAD, strongest current paper-proof candidate on NAS100/US30 D1.
3. index_tsmom_252_d1 - ACTIVE_RESEARCH_LEAD, older index trend lead, secondary to 126 variant.
4. meanrev_trend_filter_fx_d1 - WATCHLIST_ONLY, thin/cost-sensitive.
```

Core architecture:

```text
market data -> strategy signal -> backtest/risk math -> CAS gates -> evidence chain -> Condition Lab / walk-forward -> strategy ledger -> paper proof -> UI proof cockpit
```

CAS methodology layer:

```text
CAS-SDG synthetic regimes
CJT operating-region classification
nested lacunarity gap mapping
RPM route/no-trade selection
event-context axes for macro/conflict/shock conditions
owner-control promotion policy
guarded LLM optimizer scaffold
```

Live-money boundary:

```text
No live orders.
No broker ACCEPT.
No auto-deposit.
No debit/card/bank transfer.
No payout automation.
No guaranteed income claims.
All live/payment controls must stay disabled in UI.
```

UI/UX audit rule:

```text
UI/UX may start as a read-only paper/research proof cockpit after audit.
The 5-bundle threshold is only multi-day proof maturity.
The 30/30 paper-day threshold is live-money/deployment promotion gating.
```

## Start-Here Documents

Primary handoff:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\CAS_FOREX_HANDOFF_20260621.md
```

Priority synthesis:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\cas_forex_priority_synthesis_20260622.md
```

Human-readable winning strategy ledger:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\cas_forex_winning_strategy_ledger_20260622.md
```

Machine-readable strategy ledger:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\strategy_leads.json
```

CAS Forex changelog:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\CHANGELOG.md
```

Fiverr/nontechnical one-pager:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\CAS_FOREX_FIVERR_BRIEF_ONEPAGE.md
```

Current project dashboard:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\cas_harness_production_todo.md
```

## Core Source Files To Audit

Backtest engine and instrument economics:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\backtest\engine.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\instruments.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\schemas\forecast.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\schemas\order.py
```

Strategies and forecasts:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\forecast\strategies.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\forecast\chronos_signal.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\forecast\cas_ensemble.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\forecast\harness.py
```

Market data and broker/demo bridges:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\market_data\connector.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\broker\mt5_bridge.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\paper_broker_adapter.py
```

CAS gates and live locks:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\verifier\auditor.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\verifier\risk_gate.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\verifier\macro_gate.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\verifier\market_gate.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\verifier\execution_gate.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\verifier\live_lock.py
```

Evidence chain:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\evidence_store.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\schemas\evidence.py
```

CAS-SDG, Condition Lab, lacunarity, event contexts, walk-forward:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\sdg.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\regime_sim.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\condition_lab.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\event_context.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\walk_forward.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\condition_tally.py
```

Strategy preservation and promotion:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\strategy_ledger.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\owner_control.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\harvester.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\llm_optimizer.py
```

Capital/risk/payout planning:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\capital_plan.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\sweep\sweeper.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\schemas\sweep.py
```

Paper proof and daily bundle:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\paper_proof.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\paper_decision.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\paper_risk.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\paper_daily_bundle.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\paper_daily_schedule.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\paper_ui_readiness.py
```

PCBA/CJT safety and diagnostics:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\cjt_diagnostics.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\cjt_circuit_view.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\cjt_compiler.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\pcba_safety.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\pcba_prompt_injection.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\pcba_authority.py
```

## Scripts To Reproduce Or Inspect

Real backtests:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_real_backtest.py
```

Condition Lab:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_condition_lab.py
```

Walk-forward Condition Lab:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_walk_forward_condition_lab.py
```

Condition tally:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_condition_tally.py
```

Owner promotion review:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_owner_promotion_review.py
```

MT5 demo receipt:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_mt5_paper_receipt.py
```

Daily paper bundle:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_daily_paper_bundle.py
```

Paper UI evidence maturity:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_paper_ui_readiness.py
```

## Key Evidence Reports

Range-scalper research:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\range_scalper_research\real-range_scalper-20260622043152-report.json
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\range_scalper_research\real-range_scalper-20260622043231-report.json
```

Index TSMOM current lead:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\index_tsmom_h1_d1_go\walk-forward-20260622054921-report.json
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\condition_tally\condition-tally-20260622055042-report.json
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\index_tsmom_sdg_owner_go\condition-lab-20260622055024-report.json
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\owner_promotion_review\owner-promotion-review-20260622055433-report.json
```

Paper-proof day 1:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\index_tsmom_126_paper_proof\index-tsmom-126-d1-paper-proof-status.json
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\index_tsmom_126_paper_proof\index-tsmom-126-d1-paper-proof-mt5-demo-probe-20260622153728.json
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\index_tsmom_126_paper_proof\index-tsmom-126-d1-paper-proof-paper-decision-status.json
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\index_tsmom_126_paper_proof\index-tsmom-126-d1-paper-proof-paper-risk-status.json
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\index_tsmom_126_paper_proof\index-tsmom-126-d1-paper-proof-daily-bundle-status.json
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\index_tsmom_126_paper_proof\index-tsmom-126-d1-paper-proof-daily-schedule-status.json
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\index_tsmom_126_paper_proof\index-tsmom-126-d1-paper-proof-ui-readiness-status.json
```

Condition switching and lacunarity:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\condition_lab_focus\condition-lab-20260622042700-report.json
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\condition_lab_focus\condition-lab-20260622042733-report.json
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\temporal_lacunarity_focus\condition-lab-20260622044212-report.json
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\walk_forward_condition_lab\walk-forward-20260622044930-report.json
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\event_context_focus\condition-lab-20260622050947-report.json
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\event_context_walk_forward_smoke\walk-forward-20260622051001-report.json
```

Earlier FX-major negative/baseline work:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\real_backtest\real-20260621234945-report.json
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\real_backtest\real-chronos-20260622003352-report.json
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\meanrev\real-meanrev-20260622010926-report.json
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\meanrev_tf\real-meanrev-20260622011201-report.json
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\cost_sweep\real-meanrev-20260622012815-report.json
```

Charts:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\cas_forex_findings_chart_20260622.png
C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\cas_forex_strategy_edge_sprint_chart_20260622.png
C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\cas_forex_temporal_lacunarity_chart_20260622.png
C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\cas_forex_walk_forward_rpm_chart_20260622.png
```

## Supporting CAS Ecosystem References

CAS_PCBA_Engineer:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\book\CAS_PCBA_Engineer\CAS_PCBA_Engineer.pdf
C:\Users\wakil\OneDrive\Desktop\tksCAS\book\CAS_PCBA_Engineer\Chapter_09_CJT_Deep_Dive.md
C:\Users\wakil\OneDrive\Desktop\tksCAS\book\CAS_PCBA_Engineer\Chapter_18_CSB_Cognitive_Safety_Board.md
C:\Users\wakil\OneDrive\Desktop\tksCAS\book\CAS_PCBA_Engineer\Chapter_20_CDAB_Differential_Amplifier_Board.md
C:\Users\wakil\OneDrive\Desktop\tksCAS\book\CAS_PCBA_Engineer\Chapter_21_CMB_Cognitive_Memory_Board.md
C:\Users\wakil\OneDrive\Desktop\tksCAS\book\CAS_PCBA_Engineer\Chapter_22_CPMB_Power_Management_Board.md
C:\Users\wakil\OneDrive\Desktop\tksCAS\book\CAS_PCBA_Engineer\Chapter_23_Testing_Cognitive_Circuits.md
C:\Users\wakil\OneDrive\Desktop\tksCAS\book\CAS_PCBA_Engineer\Chapter_25_Production_Deployment.md
C:\Users\wakil\OneDrive\Desktop\tksCAS\book\CAS_PCBA_Engineer\Appendix_C_CCDL_Language_Reference.md
C:\Users\wakil\OneDrive\Desktop\tksCAS\book\CAS_PCBA_Engineer\Appendix_D_CCB_Reference_Designs.md
```

TKS / RPM / fractal formal references:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\_tmp_TKS_FORMAL_MATHEMATICAL_MANUAL_v6_1_COMPLETE.txt
C:\Users\wakil\OneDrive\Desktop\tksCAS\pdf_review\TKS_FORMAL_MATHEMATICAL_MANUAL_v6.1_COMPLETE_FIXED.pdf
C:\Users\wakil\OneDrive\Desktop\tksCAS\pdf_review\TKS_FORMAL_MATHEMATICAL_MANUAL_v6.1_COMPLETE_FIXED.txt
C:\Users\wakil\OneDrive\Desktop\tksCAS\book\manuscript\Chapter_27_RPM_Structure.md
C:\Users\wakil\OneDrive\Desktop\tksCAS\book\manuscript\Chapter_10_Cognitive_Fractals.md
```

CAS Harness forex execution plan:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\cas_harness_forex_trading_execution_plan.md
C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\cas_harness_forex_trading_execution_plan.pdf
```

PCBA/CAS Forex fit docs:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\cas_forex_pcba_engineer_book_fit_20260620.md
C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\cjt_pcba_cas_forex_ecosystem_fit_analysis_20260617.md
```

UI plan to audit before implementation:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\cas_forex_pwa_ui_ux_plan_revised_20260617.md
C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\cas_forex_ui_readiness_gate_20260622.md
C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\cas_forex_daily_schedule_20260622.md
```

## Verification Commands

Run from:

```powershell
cd C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex
```

Install:

```powershell
python -m pip install -r requirements.txt
```

Test suite:

```powershell
python -m pytest tests -q
```

Targeted paper/UI maturity tests:

```powershell
python -m pytest tests/test_paper_proof.py tests/test_paper_broker_adapter.py tests/test_paper_decision.py tests/test_paper_risk.py tests/test_paper_daily_bundle.py tests/test_paper_daily_schedule.py tests/test_paper_ui_readiness.py -q
```

Targeted strategy/switching tests:

```powershell
python -m pytest tests/test_condition_lab.py tests/test_walk_forward.py tests/test_condition_tally.py tests/test_owner_control.py tests/test_strategy_ledger.py tests/test_strategy_signals.py -q
```

Representative range-scalper reproduction:

```powershell
python scripts/run_real_backtest.py --model range_scalper --symbols EUR/USD GBP/USD AUD/USD --period 5y --interval 1d --position-lots 0.05 --spread-pips 1.0 --extra-cost-pips 1.0 --output-dir evidence_runs/audit_range_scalper_repro
```

Representative index TSMOM reproduction:

```powershell
python scripts/run_real_backtest.py --model tsmom --symbols NAS100 US30 --period 5y --interval 1d --position-lots 0.1 --spread-pips 1.0 --extra-cost-pips 1.0 --ts-lookback 126 --ts-skip-recent 2 --ts-min-return-bps 10 --ts-sl-mult 2 --ts-tp-mult 10 --output-dir evidence_runs/audit_index_tsmom_repro
```

Representative Condition Lab:

```powershell
python scripts/run_condition_lab.py --source both --symbols NAS100 US30 --settings tsmom_126_250_2_10 tsmom_252_500_2_8 --timeframes D1 --regimes trend_up trend_down range high_vol shock --vol-mults 0.7 1.0 1.5 --seeds 2 --output-dir evidence_runs/audit_condition_lab_repro
```

Representative walk-forward:

```powershell
python scripts/run_walk_forward_condition_lab.py --symbols NAS100 US30 EUR/USD GBP/USD AUD/USD --settings tsmom_126_250_2_10 range_scalper_24_120 --timeframes D1 --period 5y --interval 1d --output-dir evidence_runs/audit_walk_forward_repro
```

Read-only paper status:

```powershell
python scripts/run_paper_ui_readiness.py --min-daily-bundles 5 --output-dir evidence_runs/index_tsmom_126_paper_proof
```

Daily paper bundle dry/read-only style:

```powershell
python scripts/run_daily_paper_bundle.py --date 2026-06-23 --account-equity 5000 --max-risk-pct 0.5 --daily-risk-pct 1 --no-append --no-mt5 --output-dir evidence_runs/index_tsmom_126_paper_proof
```

Latest local verification before this packet was handed off:

```text
2026-06-22: python -m pytest tests -q -> 296 passed in 16.27s
2026-06-22: python -m pytest tests/test_paper_ui_readiness.py -q -> 3 passed
2026-06-22: python scripts/run_paper_ui_readiness.py --help -> --min-daily-bundles now says multi-day proof maturity
2026-06-22: git diff --check on CAS Forex/docs audit paths -> no whitespace errors; only LF-to-CRLF warnings
```

## Known Issues And Audit Hotspots

Working-tree hygiene:

```text
The local repo is dirty and includes many untracked CAS Forex files from the current sprint. A clean audit handoff should either commit/push the relevant CAS Forex files or provide the entire local folder snapshot.
```

Data quality:

```text
Most strategy evidence uses Yahoo proxy mid/close data, not broker-grade bid/ask tick or M1 data.
```

Cost/fill realism:

```text
The current cost model is spread-pips plus extra-cost-pips. The auditor should verify units for FX, index CFDs, and XAU/USD, plus stop/target intrabar assumptions and close-based fills.
```

Lookahead/leakage:

```text
Walk-forward logic was added to reduce leakage, but the auditor should inspect windowing, lookback context, training route maps, and test scoring.
```

Strategy evidence:

```text
Positive findings are research leads, not deployable live systems. Index TSMOM and FX range-scalper need broker-grade confirmation and paper proof.
```

Event context:

```text
NFP/CPI/FOMC/conflict labels exist as machinery, but historical event-conditioned backtests are still shallow. Conflict/geopolitical data is not provider-grade yet.
```

UI readiness naming:

```text
Some legacy status labels still use "UI readiness" language. The corrected project rule is: UI shell can start now as read-only after audit; 5 complete daily bundles only gates multi-day proof maturity.
```

Live and payment controls:

```text
ProfitSweeper/capital planning must remain DRY_RUN / INTERNAL_LEDGER_ONLY. Provider/bank/debit/card transfer automation remains NOT LICENSED.
```

Regulatory/compliance:

```text
The project must avoid acting as a money manager, trading adviser, pooled-funds system, guaranteed-income product, or live automation product until proper legal/broker gates are closed.
```

## Questions The Auditor Must Answer

1. Is the P&L math correct for FX, NAS100, US30, and XAU/USD across lot sizes, point values, spreads, stops, targets, and drawdowns?
2. Are any strategies accidentally using future data through signal generation, route selection, or Condition Lab/walk-forward windows?
3. Are transaction costs and fill assumptions too optimistic, too pessimistic, or unit-inconsistent?
4. Are the current positive leads still positive under broker-grade bid/ask data and realistic slippage?
5. Does the evidence-chain format actually protect against accidental result drift and tampering?
6. Is the MT5 demo adapter read-only and safely blocked from live accounts/orders?
7. Are the paper-proof gates sufficient before UI, paper automation, or live-money discussions?
8. Does the owner-control policy correctly separate owner approval from broker `ACCEPT` and legal permission?
9. Are the LLM optimizer guards strong enough to prevent hallucinated strategy promotion, unsafe live unlocks, or prompt-injection driven actions?
10. What exact UI labels are allowed now without misleading the owner or future users?
11. What must be fixed before the UI/UX proof cockpit starts?
12. What must be fixed before any paper automation expands?
13. What must be fixed before any live-money path is even reconsidered?

## Requested Auditor Deliverables

Written methodology review:

```text
Data, strategy logic, transaction costs, fills, risk controls, validation, leakage, and evidence-chain assessment.
```

Code review:

```text
Findings ordered by severity, with file paths, line numbers, impact, and recommended fixes.
```

Reproduction log:

```text
Commands run, environment notes, pass/fail status, and any results that differ from saved evidence.
```

Risk and compliance memo:

```text
What the system can truthfully claim now, what remains OPEN, and what remains NOT LICENSED.
```

UI/UX prebuild signoff:

```text
Whether the read-only proof cockpit can begin, what it may show, and what controls must be disabled.
```

## Plain-English Glossary For Auditor

CAS-SDG:

```text
Synthetic data generator that creates market-like regimes so strategies can be stress-tested beyond one historical sample.
```

CJT operating region:

```text
Condition label describing whether a strategy is inactive, usable, overextended, or broken under a market condition.
```

Nested lacunarity:

```text
Gap map showing where evidence is missing across nested axes such as symbol, timeframe, event, regime, volatility, and strategy family.
```

RPM route:

```text
Prerequisite-based selector. If enough evidence exists, route to a setting; otherwise return NO_TRADE.
```

Paper proof:

```text
Daily evidence that the system would have acted safely in demo/paper mode. It is not live permission.
```

`ACCEPT`:

```text
CAS Harness-style proof status. It must never be used to imply broker/legal permission.
```

`NOT LICENSED`:

```text
Hard boundary meaning the system is not authorized for live trading, payment movement, or broker execution.
```
