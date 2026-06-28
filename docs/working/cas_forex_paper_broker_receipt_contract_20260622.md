# CAS Forex Paper Broker Receipt Contract

Date: 2026-06-22
Status: proof-ingestion contract
Claim boundary: broker/demo paper receipts do not create broker `ACCEPT`; live trading remains `NOT LICENSED`

## Purpose

This contract defines the receipt shape CAS Forex can ingest for the
`index_tsmom_126_d1` paper-proof ledger.

The receipt gate has three evidence levels:

1. `PLAN_ONLY`: CAS recorded a daily heartbeat, but no broker/demo source is
   attached.
2. `BROKER_EXPORT_HASHED`: CAS validated and hash-bound a paper/demo broker
   export supplied as JSON, but the export is not API-authenticated by CAS.
3. `BROKER_API_VERIFIED`: a broker/demo adapter verified the receipt directly
   through a paper broker source. Only this level can satisfy the broker-source
   paper-proof gate.

The generic command-line runner intentionally does not mark user-supplied JSON
as `BROKER_API_VERIFIED`. That authority is reserved for a broker/demo adapter.

## Active Lead

- lead id: `index_tsmom_126_d1`
- strategy setting: `tsmom_126_250_2_10`
- symbols: `US30`, `NAS100`
- timeframe: `D1`
- proof ledger:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-status.json`
- receipt template:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-receipt-template-20260622.json`
- MT5 demo probe:
  `cas-forex/evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-mt5-demo-probe-20260622153728.json`

## Required Receipt Fields

```json
{
  "receipt_id": "index-tsmom-126-d1-paper-proof-2026-06-22-broker-demo-receipt",
  "source_attestation": "BROKER_EXPORT_HASHED",
  "broker_mode": "PAPER_MT5",
  "trading_date": "2026-06-22",
  "lead_id": "index_tsmom_126_d1",
  "strategy_setting": "tsmom_126_250_2_10",
  "symbols": ["US30", "NAS100"],
  "timeframe": "D1",
  "orders_attempted": 0,
  "orders_paper_executed": 0,
  "open_positions_reconciled": true,
  "live_mode": false,
  "broker_export_sha256": "64-character SHA-256 of the broker export",
  "account_id_hash": "hash of demo account id, never the raw account number",
  "server": "demo server name",
  "terminal_name": "terminal name",
  "provider_receipt_id": "broker/demo export id",
  "order_ids": []
}
```

## Validation Rules

- `live_mode` must be `false`.
- `broker_mode` must be `PAPER_MT5`, `PAPER_MT4`, or `PAPER_BROKER_DEMO`.
- `lead_id`, `strategy_setting`, `symbols`, and `timeframe` must match the
  proof plan exactly.
- `trading_date` must match the appended proof date.
- `orders_paper_executed` cannot exceed `orders_attempted`.
- `broker_export_sha256` must be a 64-character SHA-256 hex digest.
- `account_id_hash` must be hash-like and must not expose a raw account label.
- Duplicate dates do not inflate the day count; CAS keeps the strongest
  evidence for that trading date.

## Current Status

Current paper-proof status remains:

- completed days: `1 / 30`
- broker verified days: `1 / 30`
- chain verified: `true`
- passed: `false`
- broker source: `BROKER_API_VERIFIED` for 2026-06-22 via `Hugosway-Demo`

First verified receipt:

- receipt id:
  `index-tsmom-126-d1-paper-proof-2026-06-22-mt5-demo-api`
- receipt hash:
  `94d68da3b3c4d7bd13e29f69df60e1ff1d7938757e0e8e3d9aec613976704c0c`
- server: `Hugosway-Demo`
- terminal: `MetaTrader 5`
- orders attempted/executed: `0 / 0`
- open positions reconciled: `true`

Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank transfer, and
payout automation remain `NOT LICENSED`.
