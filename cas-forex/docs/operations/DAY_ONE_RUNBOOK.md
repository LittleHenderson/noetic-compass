# Day 1 of 30 — Owner Runbook

Three actions start the 30-day paper proof on a chain that can actually pass.
Everything here is owner-gated on purpose: no step can be performed by the AI,
and no volume of self-generated evidence substitutes for any of it.

State when this runbook was written (2026-08-11), CORRECTED after audit -
there are TWO account records and they are very different:

- INTERNAL LEDGER (the app's risk-review model, seeded at $5,000): $0 P/L,
  0 executed deals. This is a model, not the broker.
- BROKER DEMO ACCOUNT (Hugosway-Demo, runtime/mt5-account-growth.json,
  reconciled 2026-07-15): $100,000 deposited, 1,723 closed positions,
  net realized -$55,069.22, balance $44,930.73. The June-July loop traded
  this account down 55%.

Any screen or report showing "$5,000, no trades" is describing the internal
model. The broker demo account is NOT untouched. Live remains NOT LICENSED;
the proof chain is broken at record 11 (diagnosed, not repaired); the 3 June
bundle days do not count once the chain restarts.

## 1. Restart the proof chain (~1 minute)

The June chain is permanently unverifiable (concurrent-writer break at record
11 — see `evidence_runs/index_tsmom_126_paper_proof/` and the diagnosis in
CHANGELOG 2026-08-11). The proof gate requires a chain that verifies
end-to-end, so days appended to the broken chain can never pass.

```bash
python scripts/restart_paper_proof_chain.py --confirm "RESTART PAPER PROOF CHAIN"
```

- Refuses if the chain verifies (nothing to remediate).
- Moves the broken store + sidecar into `archive/broken-chain-<stamp>/` with a
  defect record. Nothing is deleted or rehashed.
- **Consequence, stated plainly: the 30-day counter restarts at 0.**

## 2. Start the MT5 demo terminal (~5 minutes, maybe longer once)

Broker receipts require the Hugosway MT5 demo terminal running and logged in.
Its last recorded broker contact was 2026-07-15 (~4 weeks idle at time of
writing); demo accounts often expire after weeks of inactivity — if login fails, register a fresh demo account at the broker and
update `CAS_FOREX_MT5_LOGIN` / `_PASSWORD` / `_SERVER` in `.env`.

Verify from the repo root:

```bash
python -c "from cas_forex.broker.mt5_bridge import MT5Bridge; b=MT5Bridge(); print('connected:', b.connect(force=True))"
```

`connected: True` means receipts can be collected. (The `force=True` bypasses
the 30-second failure cooldown if you just started the terminal.)

## 3. Run the stack so the loop outlives dev sessions

```bash
START_CAS_FOREX.bat
```

This runs the API server + execution loop under the production launcher. The
loop trades the PAPER lane only: live dispatch is blocked by NOT LICENSED,
the owner switches, and the authenticated-eligibility axis (constant false
until external verifiers are wired by code change).

## Daily cadence (each trading day, ~2 minutes)

The recommended command comes from the dashboard's Next Action panel, or:

DECISION REQUIRED FIRST - equity basis. The internal ledger is seeded at
$5,000, but the broker demo account the receipts come from holds ~$44,930
(after -$55,069 of June-July losses on a $100,000 deposit), and the on-disk
Next Action recommendation still says `--account-equity 100000`. These size
risk 20x apart. Pick ONE basis for the restarted proof - the honest choice is
the broker account's real equity at restart time - and use it every day:

```bash
python scripts/run_daily_paper_bundle.py --account-equity <chosen-basis> --max-risk-pct 0.5 --daily-risk-pct 1
```

A complete day = broker/demo receipt + route decision + risk review. The
schedule tracker shows which tracks are missing for the next due date. Days
only count when the MT5 terminal was reachable for the receipt.

Use `--no-append` first if you want to see what would happen without writing
evidence.

## What "done" looks like (the FULL gate, per cas_forex/paper_proof.py)

- 30 complete bundle days on the restarted chain, `chain_verified: true`
- Broker-verified receipts for every day
- **At least 15 days with real executed paper trades** - receipts + decisions
  + risk reviews alone produce zero executed attempts (the June days show
  `orders_paper_executed: 0`); the execution loop must actually be trading
- **Open positions reconciled every day**
- **Net P&L above zero across the proof** - the gate is net-positive by
  design and cannot be relaxed to hit the number
- Then the D-section items (acknowledgments, counsel review, live account)
  become the frontier — each requires an external authority; none can be
  self-attested. See `cas_forex/eligibility_attestation.py` for exactly what
  must be wired, and by whom.

Boundary: this runbook orchestrates paper/demo evidence collection only. No
step places live orders, moves money, or changes any authority gate.
