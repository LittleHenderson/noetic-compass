# CAS FOREX — Pre-Live Safety Audit

**Date:** 2026-06-25
**Scope:** Read-only review of the safety/authorization machinery before any real-money use. No code was changed; no live mode, credentials, or money-movement was enabled.
**Verification:** 67/67 safety-critical tests pass (runtime gates, authority boundary, permission validator, pre-execution risk gate, paper risk, live readiness).

---

## Headline

The architecture is genuinely **fail-closed and well-built**. But the message that kicked this off — *"fully licensed, wired, and ready for payout automation, bank/card movement, broker accept, live orders placed"* — **does not match the actual state of the code.** Right now nothing is licensed or wired for live money, and there is no real money-movement integration anywhere in the repo. That's the most important thing to understand before you act on any belief that it's "ready."

---

## Reality vs. the claim

Current `.env` and config resolve to:

| Capability | Actual runtime status |
|---|---|
| Live order placement | **CURRENTLY NOT LICENSED** |
| Broker ACCEPT | **CURRENTLY NOT LICENSED** |
| Auto-deposit | **CURRENTLY NOT LICENSED** |
| Bank/card movement | **CURRENTLY NOT LICENSED** |
| Payout automation | **CURRENTLY NOT LICENSED** |

Why: `LIVE_MODE=false`, `PAPER_TRADING=true`, and **none** of the `OWNER_ENABLE_*` flags, `LIVE_TRADING_LICENSED`, the account acknowledgments, or any `PAYMENT_PROVIDER` are set. Every gate in `runtime_gates.py` therefore evaluates to not-authorized. The system is running as a **paper/research simulator** — which is the safe and correct default.

**There is no money pipeline behind the money-movement gates.** Even if you flipped every flag on, `sweeper.execute_sweep()` (the "payout / bank/card movement" path) just writes a `SweepTransaction` ledger record. There is **no external payment integration** — no Stripe/Wise/Plaid/bank rails, no HTTP calls. "Payout automation" and "bank/card movement" are bookkeeping abstractions, not a working transfer system. Likewise, **no bot capability is marked `dangerous`** — there is no menu path that places a live order or moves money.

So: the system can't currently move a cent of real money, and "ready for payout automation / live orders placed" is aspirational, not a description of what exists.

---

## Findings (prioritized)

### 1. The portfolio-level pre-execution risk gate is dead code — wire it before live
`pre_execution_risk_gate.evaluate_proposed_intent()` enforces total-exposure, concentration, margin-utilization, positions-per-symbol, drawdown-from-peak, and floating-loss caps. It is **never called anywhere** in the codebase (confirmed by grep; its own docstring says wiring is "OUT OF SCOPE for this slice"). Today those portfolio caps gate nothing.

Note for fairness: **per-trade** sizing risk *does* exist and is separate (`paper_risk.py` enforces `max_risk_per_trade_pct` and `max_position_lots`, with position sizing at line ~430). The gap is specifically the **portfolio-level** gate. Before any live order path is enabled, call `evaluate_proposed_intent` on every proposed intent and reject on `accepted=False`.

### 2. Live-trading authorization is enforced at the factory, not the order method (defense-in-depth gap)
`require_authorized("live_trading")` runs in `get_bridge()` via `_enforce_live_legal_gates()`. But `MT5Bridge()` is also constructed **directly** in `mt5_paper_execution_verifier.py` (3 sites), bypassing the factory, and `MT5Bridge.place_order` does **not** independently re-check authorization. Today this is inert because `live_mode=false`. But it means the gate is not defense-in-depth. **Recommendation:** also call `require_authorized("live_trading")` inside `MT5Bridge.connect()` / `place_order` so no construction path can place a live order without passing the gate.

### 3. Real MT5 credentials are present while `live_mode=false` — confirm it's a DEMO account
`mt5_login` / `mt5_password` / `mt5_server` are set. With `paper_trading=true` + `mt5_login>0`, `get_bridge()` connects a **real `MT5Bridge`** for "paper" (lines ~696–699). The only thing separating that from live order placement is the `live_mode` flag plus the gate. If those credentials point at a **funded live account**, the safety margin is thinner than it looks. Verify the configured MT5 account is a demo/practice account.

### 4. "Fully licensed" is a legal question a code audit can't answer
Automating payouts and bank/card movement is regulated activity (money transmission; and if any third party's funds are ever involved, broker/fund licensing). The code can't verify this — a lawyer must. Good signal: the live-trading gate explicitly **refuses** `account_type` in {family, friend, client, pooled, fee_based}, so the author intended personal-account-only use. Keep it that way unless counsel says otherwise.

---

## What's genuinely good

- **Fail-closed by construction.** A capability is authorized only when owner flag **AND** credentials **AND** provider config all hold (`runtime_gates.py`). Missing anything → `PERMISSION ERROR` with the exact remaining steps.
- **Degraded-state safety.** `cas_permission_validator.py` rejects `dangerous` capabilities when gate state is unavailable, and treats unknown danger levels as conservative.
- **Consistency invariant.** `authority_boundary.assert_authority_boundary()` raises if a report ever claims a capability is active that the gates deny.
- **Sweeper is correctly gated** (unlike the risk gate): it calls `evaluate_payout_automation()` and blocks fail-closed with the missing requirements.
- **Honest readiness reporting.** `live_readiness.py` separates `NOT_READY_FOR_LIVE` from `READY_FOR_LIVE_EXECUTION` and requires all real-money gates authorized.

---

## If you intend to go live later

These are yours to do by hand — I won't enable live mode, wire payments, or place orders. In rough order:

1. Wire Finding 1 (portfolio risk gate) into the order path and add a test that a cap breach blocks dispatch.
2. Close Finding 2 (gate inside the bridge, not just the factory).
3. Confirm Finding 3 (demo vs. funded account).
4. Get legal sign-off on Finding 4 before any payout/movement flags exist.
5. Build and independently audit an **actual** payment integration — none exists today.
6. Only then, with eyes open, change config yourself.

---

*Audit method: static review of `runtime_gates`, `authority_boundary`, `cas_permission_validator`, `pre_execution_risk_gate`, `owner_control`, `config`, `broker/mt5_bridge`, `sweep/sweeper`, `paper_risk`, `live_readiness`, plus call-graph grep and the project's own safety test suite (67 passing). Code targets Python 3.11+ (`datetime.UTC`); ran on 3.10 with a one-line shim.*
