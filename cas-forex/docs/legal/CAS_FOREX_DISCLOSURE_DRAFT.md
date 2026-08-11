# CAS Forex Disclosure Draft

This draft is product copy for owner review and legal review before public
release. It is not legal advice and does not replace jurisdiction-specific
terms, privacy, regulatory, broker, tax, or investment adviser review.

## No Profit Guarantee

There is no guarantee of profit.

CAS Forex does not guarantee profit, income, returns, win rate, or loss
avoidance. Trading results can be positive, flat, or negative. Past backtests,
paper results, demo results, live results, AI analysis, strategy scores, and
operator explanations do not guarantee future results.

## Automated Trading Risk

Automated trading can open, modify, or close positions quickly and can lose
money. Owner-defined limits, risk controls, broker-side stops, alerts, and audit
logs reduce some operational risk, but they do not eliminate market risk,
execution risk, broker risk, connectivity risk, platform risk, data risk, model
risk, or human configuration risk.

## Owner-Armed Autonomous Execution

CAS Forex is intended to support owner-armed autonomous execution.

Once the owner enables the relevant live or money controls, CAS Forex may
autonomously:

- place market, limit, stop, and stop-limit orders;
- modify or cancel pending orders;
- set, modify, trail, or execute take-profit and stop-loss logic;
- partially close, fully close, scale into, scale out of, hedge, or flatten
  positions; and
- initiate configured deposits, withdrawals, payouts, or internal transfers
  through approved provider rails and destination allowlists.

This does not mean CAS Forex acts without boundaries. Autonomous side effects
should still remain inside owner-delegated authority and runtime gates such as
fresh broker truth, broker/provider connectivity, risk caps, margin checks,
destination allowlists, receipts, audit logging, and master kill / emergency
controls.

## No Per-Action Approval Guarantee

CAS Forex should not be described as requiring per-order or per-transfer human
confirmation when the owner has already armed standing authority for those
actions. At the same time, CAS Forex should not be described as guaranteeing
that every eligible autonomous action will execute. Runtime gates may still
block or stand down a trade or transfer because of market, broker, provider,
risk, recovery, compliance, or emergency conditions.

## AI Limitations

AI limitations must remain visible anywhere CAS Forex describes the Operator,
assistant, strategy engine, or automated decisioning. AI analysis is
probabilistic and can be wrong, stale, incomplete, overconfident, unavailable,
or blocked by market, broker, data, account, margin, spread, slippage, news, or
terminal conditions. AI confidence is not a win probability unless a specific
audited metric defines it.

## Broker Execution Boundary

Broker execution, pricing, spreads, commissions, swaps, margin rules, fills,
rejections, slippage, stop distance rules, symbol names, deposits, withdrawals,
account restrictions, and account terms are controlled by the broker and trading
platform. CAS Forex can route, inspect, reconcile, and log requests, but it
cannot guarantee broker execution quality or broker account outcomes.

## Money Movement Boundary

Configured money movement remains subject to provider-side rules, destination
controls, verification requirements, fraud or anomaly checks, provider health,
and runtime receipts. CAS Forex should not imply guaranteed deposits,
withdrawals, payout timing, payout success, custody, or transfer reversibility.

## Paper, Demo, And Live Separation

Paper, demo, and live results are separate operating modes and must not be
presented as equivalent proof. Paper fills are simulated, demo fills are broker
demo conditions, and live fills use real account conditions. Performance pages,
trade history, screenshots, and assistant answers should label each result as
paper, demo, or live.

## No Financial Advice

CAS Forex is not financial advice.

CAS Forex is user-configured automation software and does not provide personal
financial advice, tax advice, legal advice, or a recommendation that any person
trade forex, CFDs, indices, metals, crypto, or any other market. The owner is
responsible for account selection, broker selection, risk settings, tax/legal
review, trading permissions, and deciding whether automation is appropriate.

## Owner Review Before Public Use

Before public release, CAS Forex should have reviewed Terms of Service, Privacy
Policy, Risk Disclosure, Automated Trading Disclosure, Broker Connectivity
Disclosure, AI Limitations Disclosure, data retention/deletion language,
support/contact language, and jurisdiction-specific compliance requirements.
