# CAS Harness Automated Forex Trading System Plan

## Summary

Build a fully automated CAS-gated forex trading system where forecasting models propose trades, specialized CAS Harnesses verify market, macro, risk, and execution conditions, MetaTrader sends approved orders to the broker, and realized profits can be swept into savings automatically.

Locked defaults:

- Live mode target: automatic trading with no approval by default.
- Human role: exception-only intervention.
- Risk posture: moderate.
- Broker path: Hugo's Way via MetaTrader 5 if available; MetaTrader 4 fallback.
- Profit transfer: support both manual approval and auto-sweep modes.
- Use case: personal, family, and friends, with legal/account-boundary warnings included.

Important boundary: this document is a planning artifact only. Do not build trading code, connect broker accounts, move money, or execute trades until CAS Harness AI Auditor is finished, the system has passed backtests and paper-trading gates, and legal/account-boundary review is complete.

## Key Architecture

```text
Market Data
  -> Forecast Model Ensemble
  -> CAS Intelligence Harness Stack
  -> CAS Verification Stack
  -> Risk Manager
  -> MetaTrader 5 / MetaTrader 4 Bridge
  -> Broker
  -> Trade Outcome Monitor
  -> Profit Sweep Module
  -> Evidence Packet Archive
```

Model stack:

- Primary: Chronos / Chronos-Bolt / Chronos-2
- Secondary: TimesFM
- Optional hosted challenger: TimeGPT
- Baselines: naive last-price, moving average, breakout, volatility filter, no-trade baseline

CAS does not replace the forecasting model. CAS verifies whether the proposed trade is safe, coherent, better than baseline, and allowed under risk rules.

## Harness Modules

Implement the forex system as a series of specialized CAS Harnesses:

- Market Data Harness
  - Tracks price, spread, volatility, liquidity, session, and slippage.
  - Suppresses trades during abnormal spread or volatility.

- Macro Intelligence Harness
  - Tracks NFP, CPI, FOMC, unemployment, GDP, central-bank speeches, and rate decisions.
  - Converts events into risk states: normal, caution, blackout, or shock.

- Calendar Risk Harness
  - Enforces trade blackouts around high-impact events.
  - Default: suppress new trades 15 minutes before and after NFP, FOMC, and CPI unless later backtests justify a different window.

- Forecast Harness
  - Compares Chronos, TimesFM, optional TimeGPT, and baselines.
  - Flags disagreement, weak confidence, unstable forecast intervals, and model drift.

- CAS Verification Harness
  - Produces ACCEPT, SUPPRESS, or HUMAN_REVIEW.
  - In live-auto mode, HUMAN_REVIEW behaves as suppress unless the user later enables manual override.

- Risk Harness
  - Moderate defaults:
    - max risk per trade: 0.5%
    - max daily drawdown: 2%
    - max weekly drawdown: 5%
    - max simultaneous correlated exposure: configurable, default conservative
  - Breach forces LIVE_LOCKED.

- Execution Harness
  - Validates exact MetaTrader order before submission.
  - Checks pair, side, lot size, stop loss, take profit, margin, spread, and duplicate-order risk.

- Post-Trade Harness
  - Compares actual trade behavior against forecast and CAS verdict.
  - Feeds outcome back into drift, suppression, and risk scoring.

- Savings Sweep Harness
  - Calculates realized distributable profit.
  - Supports manual approval sweep, automatic threshold sweep, tax reserve first, reinvest-only, and hybrid split.

## Public Interfaces And Types

Add forex-specific schemas:

- ForexMarketSnapshot
  - pair, timestamp, bid, ask, spread, candles, volatility, session, news flags

- MacroEventState
  - event name, currency, expected, actual, surprise, impact level, blackout status

- ForecastSignal
  - model, pair, horizon, direction, confidence, expected move, interval, baseline comparison

- TradeProposal
  - pair, side, entry, stop loss, take profit, lot size, max loss, expected reward/risk

- CASForexVerdict
  - verdict: ACCEPT, SUPPRESS, or HUMAN_REVIEW
  - reason codes: spread, volatility, news, drawdown, disagreement, inversion risk, weak edge, broker error

- BrokerOrderRequest
  - MetaTrader-ready order object after CAS and risk approval

- ProfitSweepPolicy
  - mode, threshold, tax reserve, reinvest percentage, savings percentage, minimum trading balance

- ForexEvidencePacket
  - full audit trail from market snapshot through forecast, CAS decision, order, outcome, and savings sweep

## Execution Phases

1. Research and legal boundary
   - Document that this is experimental trading automation, not guaranteed profit.
   - For family/friends, default to separate user-owned accounts.
   - No pooled capital, no performance fees, no public signal service until legal review.

2. Backtesting
   - Use at least 12 months of forex history.
   - Test EUR/USD, GBP/USD, USD/JPY, AUD/USD, and USD/CAD.
   - Compare raw model vs CAS-gated model vs baselines.
   - Promotion requires CAS-gated strategy to reduce drawdown, false accepts, or improve risk-adjusted return.

3. Paper trading
   - Run at least 30 trading days.
   - All trades fully automated in demo mode.
   - Generate Evidence Packet for every proposed, accepted, suppressed, and closed trade.

4. MetaTrader bridge
   - Prefer MT5 Python bridge if Hugo's Way account supports MT5.
   - Use MT4 Expert Advisor bridge only if MT5 is unavailable.
   - MetaTrader only executes approved orders; it does not decide trades.

5. Limited live auto
   - Start with tiny lot size and moderate risk limits.
   - No human approval required for ordinary accepted trades.
   - Human only intervenes if a hard lock triggers.

6. Profit sweep
   - Track realized closed-trade profit only.
   - Block sweeps during drawdown recovery or open-risk overload.
   - Auto-sweep mode transfers only after threshold, reserve, and minimum-balance checks pass.

## Failure Modes And Locks

The system must immediately lock live trading on:

- daily drawdown over 2%
- weekly drawdown over 5%
- broker disconnect during open trade
- duplicate order detection
- abnormal slippage
- margin error
- MetaTrader execution mismatch
- model drift breach
- news shock outside expected bounds
- Evidence Packet write failure
- savings transfer failure

LIVE_LOCKED requires human unlock.

## Test Plan

- Unit tests for all schema validators.
- Forecast ensemble disagreement tests.
- Macro blackout tests for NFP, CPI, and FOMC.
- Risk-limit breach tests.
- MetaTrader order validation tests.
- Duplicate order suppression tests.
- Broker disconnect simulation.
- Slippage stress tests.
- Backtest raw model vs CAS-gated model.
- 30-day paper trading simulation.
- Profit sweep dry-run and auto-sweep tests.
- Evidence Packet completeness tests.
- Live lock/unlock tests.

## Assumptions And Defaults

- CAS Harness AI Auditor is completed first; this forex project starts afterward.
- Fully automated trading is the goal, but only after backtest and paper-trading gates pass.
- Hugo's Way is included as requested, but jurisdiction/legal risk must be explicitly documented.
- MT5 is preferred; MT4 is fallback.
- Human intervention is exception-only.
- Moderate risk defaults are used unless user changes them.
- HUMAN_REVIEW in unattended mode defaults to no trade.
- Savings sweep starts as dry-run, then manual, then optional auto-sweep after validation.

## Reference Links To Re-Check Before Build

- Hugo's Way: https://hugosway.com/
- CFTC registration check guidance: https://www.cftc.gov/check
- NFA forex regulatory guide: https://www.nfa.futures.org/members/member-resources/files/forex-regulatory-guide.html
- Nixtla TimeGPT API: https://www.nixtla.io/docs/api-reference/foundational-time-series-model-multi-series
- Amazon Chronos: https://github.com/amazon-science/chronos-forecasting
- OANDA REST API reference: https://help.oanda.com/us/en/faqs/rest-v20-api-troubleshooting-guide.htm
