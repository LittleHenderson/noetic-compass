# Day 1 of 30 — Owner Runbook

Three actions start the 30-day paper proof on a chain that can actually pass.
Everything here is owner-gated on purpose: no step can be performed by the AI,
and no volume of self-generated evidence substitutes for any of it.

State when this runbook was written (2026-08-11): $5,000 paper equity, $0 P/L,
0 executed deals, live NOT LICENSED, proof chain broken at record 11
(diagnosed, not repaired), 3 complete bundle days from June that do NOT count
once the chain restarts.

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
It has been idle since 2026-06-24; demo accounts often expire after weeks of
inactivity — if login fails, register a fresh demo account at the broker and
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

```bash
python scripts/run_daily_paper_bundle.py --account-equity 5000 --max-risk-pct 0.5 --daily-risk-pct 1
```

A complete day = broker/demo receipt + route decision + risk review. The
schedule tracker shows which tracks are missing for the next due date. Days
only count when the MT5 terminal was reachable for the receipt.

Use `--no-append` first if you want to see what would happen without writing
evidence.

## What "done" looks like

- 30 complete bundle days on the restarted chain, `chain_verified: true`
- Broker-verified receipts for every day
- Then the D-section items (acknowledgments, counsel review, live account)
  become the frontier — each requires an external authority; none can be
  self-attested. See `cas_forex/eligibility_attestation.py` for exactly what
  must be wired, and by whom.

Boundary: this runbook orchestrates paper/demo evidence collection only. No
step places live orders, moves money, or changes any authority gate.
