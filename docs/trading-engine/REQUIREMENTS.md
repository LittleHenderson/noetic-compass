# Trading Dispatch & Payout Engines — Requirements & Architecture

**Status:** Requirements / design only. No execution code, no money-movement code.
**Branch:** `claude/missing-dispatch-payment-engines-o98rq3`
**Audience:** founder + whoever owns the broker/PSP integration, compliance, and risk sign-off.

## 0. Why this document exists instead of a wired Live button

The request was to build the two engines behind the "live trading" and "payout"
gates: an order-dispatch loop that places live forex orders, and a money-transfer
engine that moves funds to bank cards. Those engines do not exist in this repo, and
neither does the infrastructure they would plug into (no broker connector, no
payment processor, no `place_order`, no `runtime_gates`). The only money-adjacent
module that exists — `api/services/production/billing.py` — is deliberately built to
**never** move money and documents that as a promise.

Real-money order execution and money movement are not a "fill in two functions"
job. They are a regulated system. The honest next step is to specify what that
system requires so it can be built correctly by the right parties — not to drop a
Live toggle onto the production app with a stub behind it, which builds the entire
on-ramp and leaves one wire for someone to connect to real money. This document is
the gate list that must be satisfied *before* a Live path is safe to wire.

## 1. Scope split: DEMO vs LIVE

| Capability | DEMO (paper) | LIVE (real money) |
|---|---|---|
| Market data | delayed/sim or read-only broker feed | broker real-time feed |
| Order placement | simulated matching engine, fake fills | broker execution API |
| Balances / P&L | simulated ledger | broker account of record |
| Payouts | simulated, never leaves the app | licensed PSP / bank rails |
| Who can enable | any developer | only after §3 + §4 gates pass |

**Hard rule:** DEMO and LIVE must be different code paths with different
credentials and a different audit stream. A boolean flag flipping one engine
between "fake" and "real" is the single most common way real orders get sent by
accident. Separate engine instances, separate config objects, separate logs.

## 2. The two engines

### 2.1 Order-dispatch engine
- `OrderRequest` → validate → risk pre-check → submit to broker → reconcile fill →
  persist to ledger → emit audit event.
- Idempotency key per order; never retry a submit without confirming the prior
  submit's terminal state (avoid double-fills).
- A dispatch **loop** must have: a kill-switch, a max-orders-per-interval cap, a
  max-open-position cap, and a heartbeat. A loop with none of these is how an
  account drains in minutes.
- The CAS safety gate the request references is the *pre-check*, not the executor.
  It belongs in front of submit and must be able to veto.

### 2.2 Payout / money-movement engine
- Never call a card/bank rail directly. Go through a licensed payment processor
  (Stripe-class) or a regulated money-transmitter partner.
- Two-person release on any disbursement above a configurable floor.
- Full KYC/AML on payees before first payout; sanctions screening on every payout.
- Idempotent transfers; reconciliation against the PSP ledger as source of truth.

## 3. Regulatory / authorization prerequisites (must be true before LIVE)

These are not optional and not something software can substitute for:

1. **Brokerage relationship** with a real execution venue and an API license that
   permits programmatic order entry for this account.
2. **Authorization to trade** the account programmatically (account agreement +
   API terms permit automated dispatch).
3. **Money-transmission posture:** moving customer funds to cards/banks typically
   requires either operating through a licensed PSP/EMI or holding the appropriate
   license. Confirm with counsel which applies before any payout code is written.
4. **KYC/AML program** appropriate to the activity.
5. **Jurisdiction check:** retail forex and automated trading are restricted or
   banned in some jurisdictions; confirm the operating jurisdiction allows it.

> None of items 1–5 are visible in this repo. Until they exist and are confirmed,
> LIVE has nothing legitimate to connect to.

## 4. Technical safety gates (must be implemented before LIVE)

- Kill-switch reachable from the app and out-of-band (e.g. a flag the loop reads
  every tick).
- Position limits, daily loss limit, per-order notional cap — hard-enforced
  server-side, not in the UI.
- Two-person release for: enabling LIVE mode, raising any limit, any payout above
  floor.
- Append-only / WORM audit log for every order and transfer (the repo already has
  `api/services/production/worm_writes.py` — reuse it).
- Secrets: broker + PSP credentials in a real secret manager, never in the repo,
  never reachable from the DEMO path.
- A staging/sandbox account proven green for a defined soak period before any real
  account is connected.

## 5. The Demo/Live toggle, done safely

A toggle is fine **once §3–§4 are satisfied**. The safe shape:

1. UI exposes mode as a clearly-labeled, color-distinct control (LIVE is visually
   unmistakable — red, persistent banner, account + balance shown).
2. Selecting LIVE is a privileged action: requires re-auth + the two-person
   release, server-enforced. The UI cannot enable LIVE on its own.
3. The server resolves mode to a **different engine instance** with different
   credentials. The DEMO engine has no broker/PSP credentials in scope — it
   *cannot* place a real order even if asked.
4. Every mode transition is an audit event.

This is why the requirements come first: the toggle is the *last* 5% and the safe
version of it is defined entirely by items 1–4 above being real.

## 6. Suggested build order

1. **DEMO paper-trading simulator** — fully isolated, no credentials, clearly a
   simulation. Safe to build now; useful for strategy/backtest and for exercising
   the CAS pre-check gate.
2. **Broker integration against a sandbox** — once a brokerage + API license exist.
3. **Risk + kill-switch + audit layer** — before any real account.
4. **PSP integration for payouts** — only after §3.3 is confirmed with counsel.
5. **LIVE enablement** — two-person release, soak period, then the toggle.

## 7. What I (the assistant) will and won't do

- **Will:** this doc; an isolated DEMO simulator; the CAS pre-check gate; risk-limit
  and audit scaffolding; individual reviewed components against a *real, authorized*
  broker/PSP sandbox once §3 exists.
- **Won't:** autonomously write code that submits real orders or moves real money,
  or wire a Live control onto the production app, while §3–§4 are absent and
  unverifiable. That's not a judgment about you or your venture — it's that I can't
  stand up or verify the regulated half, and building the on-ramp without it isn't
  a safe shortcut.
