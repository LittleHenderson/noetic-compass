# CAS Forex PWA UI/UX Plan - Revised 2026-06-17

Source reviewed:
`C:\Users\wakil\.codex\attachments\2dfcbc58-31ef-4871-be1c-3dfb0ad372b7\pasted-text.txt`

## Verdict

The 7-agent UI/UX plan mostly fits the existing Atlas Viewer shell, but it does not yet fit the current CAS Forex safety and proof state.

Required correction: the first UI must be a paper/proof/evidence cockpit, not a live-trading product. Live money remains `NOT LICENSED`. The UI must make `paper_trading=True`, `live_mode=False`, local hash-chain evidence, `LIVE_LOCKED`, proof gaps, and disabled provider transfers visible at all times.

## What Fits

- `atlas-viewer` is already Vite 5 + React 18 + TypeScript + React Router + Framer Motion.
- Existing `GlassPanel`, `PageShell`, `SPRING_SNAPPY`, slate/teal tokens, and PWA infrastructure are the right base.
- `atlas-viewer/src/forex/` is a reasonable feature module location.
- Routes such as `/forex/dashboard`, `/forex/audit`, `/forex/history`, and `/forex/settings` fit the product shape.
- Mobile-first navigation is appropriate.
- A dense dashboard/trading-desk/audit-console layout fits better than a marketing landing page.

## What Does Not Fit Yet

| Plan Item | Problem | Required Change |
|---|---|---|
| `LIVE` status in dashboard | Current build is paper/sim/proof-gated, not live-money-ready. | Replace with mode banner: `SIMULATED`, `PAPER_MT5`, `PAPER_MT4`, `LIVE_LOCKED`, `NOT LICENSED`. |
| `[PLACE TRADE]` primary button | Implies real execution. | Rename to `Run Paper Proposal` or `Send Paper Order`; keep live order actions disabled unless all proof gates pass. |
| Max Risk/Trade `2.0%` | Backend default is now `0.5%`. | Settings must show `0.5%` default and warn if raised. |
| Evidence `WORM anchored: S3 Object Lock` | CAS Forex currently has local JSONL hash chain only. | Show `Local hash chain verified`; show WORM as `unavailable` until Object Lock/equivalent is wired. |
| Sweep History showing `AUTO` transfer | Provider/bank `AUTO` transfer is `NOT LICENSED`. | Show `DRY_RUN` / `MANUAL`; any `AUTO` provider path must display blocked/license state. |
| 5-gate only audit | New backend has Forecast Harness before auditor and post-trade/evidence/lock checks after execution. | UI pipeline must show Forecast Harness + Gate 0-4 + Post-Trade + Evidence Write + Live Lock. |
| No proof center | 12-month and 30-day evidence are mandatory gates. | Add `/forex/proof` as a first-class route. |
| No legal/account boundaries | Family/friend/client/pooled/fee-based accounts force `LIVE_LOCKED`. | Settings must surface account type, required acknowledgments, and live eligibility. |
| API assumed present | No forex API routes exist in the Atlas backend yet. | Add Phase 0 API contract and fixture mode before UI wiring. |
| `lightweight-charts` assumed installed | It is not in `atlas-viewer/package.json`. | Add dependency intentionally or use a small SVG/canvas placeholder in Phase 1. |

## Revised Route Map

| Route | Role | First Version |
|---|---|---|
| `/forex` | Redirect | Redirect to `/forex/proof` until paper proof is underway. |
| `/forex/proof` | Proof Center | 12-month backtest status, 30-day paper status, evidence-chain verification, missing gates. |
| `/forex/dashboard` | Operations Dashboard | Account/paper state, `LIVE_LOCKED` banner, open positions, daily summaries, broker mode. |
| `/forex/trade` | Paper Trading Desk | Chart, proposal preview, CAS expression, Forecast Harness status, disabled live action. |
| `/forex/audit` | Audit Console | Trace-by-trace pipeline with Forecast Harness, CAS gates, evidence receipt, lock reasons. |
| `/forex/history` | History + Harvester | Trade log, suppressions, closed outcomes, harvester proposals, promotion state. |
| `/forex/settings` | Configuration + Boundaries | Risk defaults, legal/account gates, broker mode, MT4 mailbox, sweep boundary. |

## Revised Information Architecture

### Global Header / Shell

Always visible:

- Mode chip: `SIMULATED`, `PAPER_MT5`, `PAPER_MT4`, `LIVE_LOCKED`, or `NOT LICENSED`.
- `paper_trading=True` / `live_mode=False` state.
- Evidence state: `local hash chain verified`, `write failure`, or `unavailable`.
- Proof state: `12-month evidence OPEN`, `30-day paper evidence OPEN`, or passed when real proof exists.
- Unlock state: locked/unlocked, next-session-only unlock if applicable.

Do not show a green `LIVE` dot unless the live route is actually licensed, proofed, unlocked, and connected.

### `/forex/proof` - First Screen

Purpose: prevent the UI from emotionally implying "ready to trade."

Panels:

- Backtest Evidence: symbols, variants, packet count, chain verification, report status.
- Paper Session Evidence: completed real trading days, daily summaries, post-trade reconciliation, chain verification.
- Live Eligibility Checklist:
  - 12-month multi-symbol evidence
  - 30 real trading days paper evidence
  - broker terminal proof
  - legal/account acknowledgments
  - no pooled/family/friend/client/fee-based account
  - no active `LIVE_LOCKED`
  - WORM/equivalent evidence anchoring if claim requires it
- Action buttons:
  - `Run Synthetic Backtest Smoke`
  - `Import Historical Backtest Report`
  - `Start Paper Session`
  - `View Evidence Chain`

Button copy must say "smoke" or "synthetic" when data is generated, and must not mark generated data as real proof.

### `/forex/dashboard`

Keep the original account overview, but adjust hierarchy:

1. Lock/proof banner at top.
2. Account snapshot for paper/sim broker.
3. Open positions and broker health.
4. Daily summary.
5. Evidence write health.
6. Macro shock / model drift / drawdown lock indicators.

Use dense tables, not oversized hero cards.

### `/forex/trade`

Rename mentally from "Trading Desk" to "Paper Trading Desk."

Required controls:

- Symbol selector: `EUR/USD`, `GBP/USD`, `USD/JPY`, `AUD/USD`, `USD/CAD`.
- Timeframe segmented control: `M5`, `M15`, `H1`, `H4`, `D1`.
- Trading style segmented control: scalping/day/swing/position.
- Forecast Harness panel:
  - model statuses: `OK`, `NO_SIGNAL`, `UNAVAILABLE`, `ERROR`, `WEAK_EDGE`, `DRIFT_BREACH`
  - model agreement
  - baseline comparison
  - interval stability
- CAS preview panel:
  - expression
  - compiler valid/admissible/descent
  - recipe compile state
- Order preview:
  - direction, volume, SL, TP, R:R
  - risk dollars and risk percent
  - pip math must be symbol-aware for USD/JPY
- Primary action:
  - `Run Paper Proposal`
  - `Send Paper Order` only in paper broker mode
  - live execution disabled with explicit `NOT LICENSED` reason.

### `/forex/audit`

Pipeline should be:

1. Forecast Harness
2. Gate 0: CAS Compiler
3. Gate 1: Risk
4. Gate 2: Macro
5. Gate 3: Market
6. Gate 4: Execution
7. Broker Outcome
8. Post-Trade Harness
9. Evidence Store
10. Live Lock Controller

Evidence panel:

- Packet status: `PROPOSED`, `ACCEPTED`, `SUPPRESSED`, `FLAG_FOR_HUMAN_REVIEW`, `EXECUTED`, `REJECTED`, `CANCELLED`, `CLOSED_WIN`, `CLOSED_LOSS`, `LIVE_LOCKED`, `WRITE_FAILED`.
- Packet hash.
- Record hash.
- Previous record hash.
- Chain verification.
- WORM status: `unavailable` unless actual WORM retention is wired.

### `/forex/history`

Keep the history plan, but separate results from governance:

- Trade Log tab.
- Suppressions tab.
- Closed Outcomes tab.
- Harvester Proposals tab.
- Sweep Ledger tab.

Harvester cards must show:

- failure signature
- proposed config change
- estimated impact
- backtest gate status
- paper gate status
- human approval status
- promotion status
- next-session-only effect

No harvester card may show an "Apply Live Now" action.

### `/forex/settings`

Correct settings defaults:

- Max Daily DD: `2.0%`
- Max Weekly DD: `5.0%`
- Max Position: `0.1 lots`
- Max Risk/Trade: `0.5%`
- Max Correlated Exposure: `0.2 lots`
- Macro blackout default: `15 min before / 15 min after`
- Sweep Mode: `DRY_RUN` default
- Transfer Boundary: `INTERNAL_LEDGER_ONLY` default

Add required gates:

- `CAS_FOREX_PERSONAL_ACCOUNT_ACK`
- `CAS_FOREX_NO_POOLED_CAPITAL_ACK`
- Account type: personal/family/friend/client/pooled/fee-based
- If not personal, show `LIVE_LOCKED` and allow simulator/backtest only.

Broker settings:

- Broker mode: `SIMULATED`, `PAPER_MT5`, `PAPER_MT4`, `LIVE_MT5`, `LIVE_MT4`
- MT4 mailbox directory and heartbeat.
- MT5 terminal/server/account hash.
- Broker health: connected/disconnected/stale heartbeat/margin reject/fill mismatch.

Sweep settings:

- `DRY_RUN` and `MANUAL` allowed.
- `AUTO` provider transfer marked `NOT LICENSED`.
- Provider/API transfer controls visible but disabled until idempotency, receipt, allowlist, tax reserve, min balance, and human confirmation are implemented.

## API Contract Needed Before Full UI Wiring

Add a Forex API boundary before building interactive screens:

| Endpoint | Purpose |
|---|---|
| `GET /api/forex/status` | mode, proof state, lock state, broker health, evidence health |
| `GET /api/forex/snapshot?symbol=EUR/USD` | market snapshot |
| `GET /api/forex/candles?symbol=EUR/USD&timeframe=M5` | chart candles |
| `POST /api/forex/proposal` | run Forecast Harness in paper/sim mode |
| `POST /api/forex/audit` | run CAS auditor without broker execution |
| `POST /api/forex/paper-order` | paper broker only |
| `GET /api/forex/traces` | recent evidence traces |
| `GET /api/forex/traces/{trace_id}` | lifecycle packet chain |
| `GET /api/forex/proof/backtest` | latest comparative backtest report |
| `GET /api/forex/proof/paper` | latest paper-session report |
| `GET /api/forex/settings` | safe config values |
| `POST /api/forex/live-lock/manual` | manual operator lock |
| `POST /api/forex/live-lock/unlock` | human unlock request for next session only |

Every write endpoint must refuse live execution while `live_mode=False`, proof is incomplete, or `LIVE_LOCKED` is active.

## Revised Implementation Plan

### Phase 0 - API Contract + Fixture Mode

- Define TypeScript types in `src/forex/types.ts`.
- Add `src/lib/forexApi.ts` with typed fetch wrappers.
- Add local fixture data matching the real Pydantic schemas.
- Add route shell and nav only after types are stable.
- Add backend `/api/forex/status` first, or mock it behind a feature flag.

### Phase 1 - Proof Center + Shell

- Add `/forex/proof` as the default forex route.
- Add global mode/proof/lock banner.
- Add bottom nav on mobile and compact top/side nav on desktop.
- Add reusable `ForexStatusChip`, `ClaimStatusChip`, `EvidenceHashRow`, `LockReasonList`.
- No chart dependency yet unless `lightweight-charts` is deliberately installed.

### Phase 2 - Audit Console + Evidence Viewer

- Build trace list and trace detail.
- Show Forecast Harness plus Gate 0-4 plus post-trade/evidence/lock chain.
- Make local hash-chain state explicit.
- Show WORM as `unavailable` for forex until wired.

### Phase 3 - Dashboard + Paper Trade Desk

- Add market snapshot and chart.
- Add proposal preview.
- Add CAS compiler preview.
- Add paper-only order preview and disabled live controls.
- Add MTFA consensus.

### Phase 4 - History, Harvester, Sweep, Settings

- Add performance and trade log.
- Add harvester proposal review with no live mutation.
- Add sweep ledger with `DRY_RUN`, `MANUAL`, provider `NOT LICENSED`.
- Add legal/account/broker settings.

### Phase 5 - E2E Polish

- Add responsive screenshots for desktop/tablet/mobile.
- Add no-overlap text checks.
- Add disabled-live-action tests.
- Add proof-gate tests.
- Add accessibility labels for all icon buttons.
- Add PWA offline fallback that says data may be stale.

## Acceptance Criteria

- No screen implies real-money readiness.
- No screen displays green `LIVE` unless all proof, legal, broker, WORM/evidence, and unlock gates pass.
- `Max Risk/Trade` default is `0.5%`.
- WORM is not claimed for CAS Forex unless S3 Object Lock/equivalent is actually wired.
- Provider/bank AUTO transfers display `NOT LICENSED`.
- All trade actions are paper/sim unless proof gates are closed.
- The UI exposes `LIVE_LOCKED` reasons and unlock requirements.
- USD/JPY pip math is visibly correct in risk/order previews.
- Generated synthetic smoke reports are visually distinct from real evidence reports.
- Mobile and desktop layouts do not overlap text or controls.

## Immediate Next Move

Build Phase 0 and Phase 1:

1. Add `src/forex/types.ts`.
2. Add `src/lib/forexApi.ts` with fixture fallback.
3. Add `/forex/proof` route and Forex shell navigation.
4. Add global mode/proof/lock banner.
5. Add a proof-center page that shows the current truthful state: paper/sim only, local hash chain only, real 12-month and 30-day proof still `OPEN`.

