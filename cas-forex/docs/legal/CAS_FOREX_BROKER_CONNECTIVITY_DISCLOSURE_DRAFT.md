# CAS Forex Broker Connectivity Disclosure Draft

Status: draft for owner review and qualified legal/compliance review before any
public, hosted, paid, or multi-user use.

This draft is not legal advice and is not approval for launch or live-money
use.

## Broker And Provider Boundary

CAS Forex may connect to brokers, trading terminals, and payment or payout
providers, but those third parties control pricing, spreads, swaps, leverage,
margin rules, symbol mapping, fills, rejections, custody, deposits,
withdrawals, payout timing, account restrictions, KYC, and account terms.

## Source Of Truth

CAS Forex should treat broker/provider state as the source of truth for live
orders, positions, receipts, and funds movement, even when local caches or UI
panels show mirrored state.

## No Broker Safety Or Withdrawal Guarantee

CAS Forex should not imply that broker compatibility means broker safety, fair
pricing, successful withdrawals, or regulatory approval. The owner remains
responsible for independently reviewing broker/provider terms and legal status.

## Connectivity And Execution Risk

Live automation may be blocked or degraded by terminal disconnects, stale
broker truth, provider outages, permissions issues, or missing runtime health.
CAS Forex may fail closed and refuse execution under those conditions.
