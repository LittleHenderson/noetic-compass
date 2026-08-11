# CAS Forex Audit and Red-Team Findings - 2026-07-04

## Executive Summary

CAS Forex is now a real AI-operated trading cockpit, not just a dashboard. It has
an always-on AI operator, paper/live broker bridges, MT4/MT5 integration, risk
gates, live enablement, money-movement scaffolding, owner access controls,
audit trails, and a React control surface.

The intended product goal is clear: the AI system should continuously pursue
balance growth in paper and live modes while removing the owner's psychological
load: revenge trading, FOMO, gambler's fallacy, overconfidence, and herd
following. The current architecture mostly supports that direction. Current
HEAD now includes an owner command broker and both AI-operator chat and the
floating assistant can propose a command, show a preview, require typed
confirmation, execute the same gated service path, and write a receipt.

This audit did not remove live-money capability. The right target is not a
defanged app. The target is an owner-authorized, broker-aware, risk-bounded app
that can act live with traceable receipts and clear human insight. Controls that
prove authority, broker state, edge, risk, and recovery are not sabotage; they
are what makes real-money automation operational instead of impulsive.

## MT5 Demo Execution and Learning Addendum - 2026-07-10

### Immediate Operator Position Edge and Exit-Control Integrity

A further red team found that open-position management was autonomous and
guarded but not actually making an immediate model decision. The module named
AI Hedge converted fixed R-multiple thresholds directly into breakeven,
partial-close, trail, take-profit, and full-close actions. Claude could inspect
the subsystem on its slower scheduled tick, but it did not select the action at
the moment broker management was chosen. That contradicted the governing intent
that the AI Operator is the trading edge, not just a label above fixed rules.

`ai_operator_position_edge.v1` now sits between deterministic draft generation
and guarded execution. It receives current account truth, all current broker
positions, fresh quote provenance, management policy, owner guidance,
owner-fenced controls, combined PAPER outcomes, and the broker-verified MT5 demo
subset. For each position it may select one exact supplied `action_ref` or
`STAND_DOWN`. Broker ticket, symbol, side, volume, stop, target, and action
identity are immutable. Model review cannot call a broker; selected actions
still pass through `order_dispatch.py -> execution_guard.py -> broker_bridge`
and receipt reconciliation. Baseline stop/target installation and high-urgency
invalidation closes remain non-vetoable so model failure cannot leave a
position unprotected. Identical action sets reuse a recent decision for 60
seconds, while owner-control, guidance, or realized-outcome changes invalidate
that reuse.

The model-binding proof is present without fabricating a trade. A synthetic,
broker-incapable contract probe gave Claude exact `close_partial` and
`modify_take_profit` drafts for a principal-protected SPX500 SHORT at 2R. Claude
selected `close_partial` at HIGH conviction, explicitly rejected target
stretching without new evidence, and cited the mixed `1 win / 1 loss` SPX500
history. Event hash is
`51cf103255e9deb13004d095b8e65692cc57f387b71659964b2b9f7b4c31fabb`;
`broker_touched=false` and `orders_placed=false`. This proves the real Claude
contract and immutable selection behavior. The first naturally occurring
broker-position action selected and executed under v1 remains `OPEN` because
there are currently no open MT5 positions.

The same audit found an exit-dial bypass. The Operator had learned that tested
trailing stops underperformed and set `trailing_stop_enabled=0`, with stored
`trailing_lock_fraction=0.82`, but broker management ignored both values and
always drafted a hard-coded 50% trail. Runtime management policy now reads the
actual AI control authority. With the toggle off no trailing draft exists; when
enabled, the exact fenced lock fraction calculates the stop and remains in the
decision parameters. Partial profit and hard protection behavior remain
available independently.

The hours-old NAS100 position-cap block shown as a current critical alert was
also a presentation defect. Critical audit history remains immutable, but every
row now carries explicit transient `ACTIVE` or `EXPIRED_HISTORICAL` display
state and a per-event TTL. `TRADE_BLOCKED` expires from the active strip after
five minutes while remaining in the audit. Browser verification now shows no
critical strip for the historical NAS100 block.

Verification is `165 passed` across the Operator position/entry edges, AI Hedge
supervision, management drafting/cycle/execution, dispatch loop/routes,
Operator context/runner/chat, and critical notifications. Python compilation
passed and the production UI build passed with 201 modules. The restarted
runtime reports `RUNNING`, `PAPER_MT5_ORDER_SEND_READY`, no loop error,
`ai_operator_trade_edge.v2`, and `ai_operator_position_edge.v1`. At `639x637`,
the Operator panel shows `AWAITING ACTIONABLE POSITION`, both engine versions,
and `MT5_DEMO_LEARNING_BOUND`; the chat textarea and Ask button are visible,
horizontal overflow is false, the stale warning strip is absent, and browser
warnings/errors are empty. Live authority remains `CURRENTLY NOT LICENSED` and
broader production readiness remains `OPEN`.

The owner's Algo Trading concern was correct. Real broker quotes and completed
candles can be observed while terminal Algo Trading is off, but genuine MT5 demo
order acceptance, fills, slippage, broker-side stops/take-profit, and closed-deal
learning cannot. Account `#1000694` on `Hugosway-Demo` is now positively demo,
terminal Algo Trading is ON, and permission truth is
`ORDER_SEND_READY_AT_TERMINAL`.

The post-fix Operator path produced genuine evidence:

- Claude returned `APPROVE` for SPX500 SHORT `0.01` in PAPER learning mode.
- CAS dispatched through `order_dispatch.py -> execution_guard.py -> MT5Bridge`.
- MT5 demo opened position ticket `45944826` at `7548.19`, with broker-side SL
  `7554.87` and TP `7521.11`.
- The broker stop closed it at exactly `7554.87`. Net outcome was `-$6.73`, made
  of `-$6.68` gross P/L and `-$0.05` commission.
- The exact join is now durable as
  `decision_ref=waste-dir-988ea37d4ba43d1b ->
  attempt_id=order-attempt-9ff2d465c1bb251d -> broker_ticket=45944826`.

Red-team follow-up found two defects after the fill. Hugo's Way encoded deal
epochs at broker-server time, approximately `+03:00`, while the history reader
queried only two hours ahead. The close was initially absent from the report.
The learning binder also depended on a legacy WASTE-cycle row that direct fresh
RouteIntent orders do not always create. The history query now detects and
shifts for the broker clock while retaining raw timestamps, and the finalized
order-attempt ledger is a first-class learning origin. Current runtime truth is
`MT5_DEMO_LEARNING_BOUND`, `history_record_count=266`,
`memory_update_count=2`, and `bound_trade_count=2`; a history read with no
identity match is explicitly reported as unbound.

The first fill also exposed an evidence-label bug: external MT5 demo execution
was mislabeled `LIVE_MT5 / LIVE_REAL_BROKER` because "real broker" meant an
external terminal rather than live money. Runtime classification now separates
`external_broker_terminal`, `account_mode`, and `live_money`; demo outcomes are
`PAPER_MT5 / MT5_DEMO_BROKER`, do not consume live-pilot capacity, and the old
SPX500 record has an appended immutable
`EXECUTION_CLASSIFICATION_CORRECTED` event. The historical record was not
rewritten.

A further feedback-path red team found that the scheduled Operator tick could
see learning outcomes, but the immediate `APPROVE/STAND_DOWN` entry prompt could
not. That split made the learning evidence informational rather than actionable
at the exact moment exposure was chosen. `ai_operator_trade_edge.v2` now sends
the immediate reviewer current account balance/equity/margin, open positions,
combined paper outcomes, the broker-verified MT5 demo subset, and a
candidate-specific same-symbol/direction/strategy summary. Its durable report
stores the compact context and context hash. A latest loss sets
`requires_differentiation_after_loss=true`; sparse evidence is not presented as
proven edge or a permanent veto.

The first live probe of that context found the SPX500 close twice because WASTE
cycle and order-attempt provenance produced different binding IDs for the same
broker event. This would have doubled the apparent loss. Trade-decision context
now deduplicates by `broker_ticket + decision_ref`, merges both provenance
labels and richer strategy metadata, and counts ticket `45944826` exactly once.
The resulting SPX500 SHORT context is `1 trade / 0 wins / 1 loss / -$6.73`, with
the exact broker ticket visible. The Operator panel is typed to display the
latest decision context status, combined/broker sample counts, matching group
record, P/L, and differentiation warning after the next decision made under v2.

The second Claude-approved PAPER learning position has now completed its full
broker lifecycle. MT5 demo ticket `45944834` was SPX500 SHORT `0.01`, entry
`7553.94`, SL `7569.06`, TP `7532.60`; the broker closed it at TP `7532.60` for
`+$21.34` gross, `-$0.05` commission, and `+$21.29` net. The exact durable chain
is `decision_ref=waste-dir-1a27907b5028bd5e ->
attempt_id=order-attempt-3c7f3991878329ac -> broker_ticket=45944834`.
The broker-verified MT5 demo subset is now `2 trades / 1 win / 1 loss / net
+$14.56`; the broader mixed PAPER feedback set is `5 trades / 4 wins / 1 loss /
net +$44.106`. These samples are feedback, not proof of a durable trading edge.
There are no open MT5 positions, account balance/equity is `$44,779.32`, and
the loop is still `RUNNING` every 14 seconds through
`MT5Bridge / PAPER_MT5_ORDER_SEND_READY` with terminal Algo Trading ON.

The running engine is `ai_operator_trade_edge.v2`, but the latest genuine
candidate decision remains the earlier v1 decision. The first naturally
occurring completed-candle candidate reviewed under v2 remains `OPEN`; no route
was fabricated merely to manufacture that proof. This is demo execution, not
live money. Real live authority remains `CURRENTLY NOT LICENSED`; public launch
and external provider readiness remain `OPEN`.

Final focused verification passed `120` tests across the Operator trade edge,
agent dispatch, dispatch loop/route, Operator context/runner/chat diagnostics,
PAPER outcome binding, MT5 demo learning sync, and MT5 deal-history ingest.
Python compilation passed and the production UI build passed with 201 modules.
At the compact `639x637` browser viewport the Operator panel stayed inside the
viewport, the chat textarea and Ask button were visible, horizontal overflow was
false, and browser warnings/errors were empty. Visible runtime truth included
`ALGO ON`, `MT5 ORDER_SEND READY`, `MT5_DEMO_LEARNING_BOUND`, and
`ai_operator_trade_edge.v2`.

## Current Runtime Snapshot

Checked without printing secrets:

- Effective config resolves to MT5 demo account `1000694` on `Hugosway-Demo`,
  with `live_mode=false` and `paper_trading=true`. The later duplicate MT5 demo
  block in `.env` is confusing but not active because config uses the first
  value loaded.
- `runtime/live-enable-overrides.json` has owner live/money switches and account
  acknowledgments set true, while `live_mode` is false and payment
  provider/destination fields are empty.
- `runtime/owner-auth.json` exists and LAN mode is currently true.
- `runtime/operator-secrets.json` exists with a primary model key present.
- `.env` contains MT5 and market-data credential keys. `runtime/owner-auth.json`
  contains the owner token. These files are git-ignored but are plaintext local
  secrets and should be rotated before any sharing or cloud migration.

Interpretation: CAS Forex is partially armed from an owner-authority perspective,
but it should not be able to place live trades while `live_mode` is false and
the remaining live-order prerequisites are not satisfied. Money movement remains
blocked because payment provider/destination requirements are empty.

## Attachment Audit Addendum - 2026-07-04

The attached transcript was mostly truthful, but it used "green" too broadly.

Validated claims:

- Commit `764cd412` exists on the current branch and adds the cloud deploy
  scaffold: `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `docs/DEPLOY.md`,
  cloud-mode owner auth, and optional single-container UI serving.
- Docker is not available locally, so the image build remains unverified here.
- Cloud mode requires an owner token even from loopback, which is the correct
  reverse-proxy posture.
- Effective demo config is account `1000694` on `Hugosway-Demo`.
- The small live pilot is `ACCEPT`, has the 13-symbol envelope including NAS100,
  and is currently `ready_for_next_live_order=true` with `0/10` pilot capacity.
- The stale `1580` pilot counter was visible in the audit trail and was reset
  through the pilot reset/update path.
- The edge PASS was not faked; real live dry-run review remains blocked without
  fresh passing evidence.

Corrections:

- Real-money authorization is not green. Runtime gates report
  `all_real_money_authorized=false` and live trading still misses `live_mode`,
  broker-reality acceptance, recovery clearance, and accepted passing live-order
  dry-run evidence against fresh broker truth.
- Broker truth is stale and demo-visible, not fresh live-visible. Recovery review
  is open and requires fresh broker truth, a visible live account, and clean
  position reconciliation.
- Payment movement is not authorized: provider, API key, payout destination, and
  allowlist fields are absent.
- Cloud hosting runs the paper/operator brain. Live MT5 execution still needs a
  Windows host or a thin MT5 relay because the Linux container does not include
  MetaTrader5.

## Confirmed Strengths

1. Owner auth now exists at the API boundary.
   `api/server.py` has middleware that allows loopback without friction but
   requires LAN mode plus an owner token for off-box access. The default launcher
   binds to `127.0.0.1`; the LAN launcher is explicit.

2. Live execution is checked at multiple layers.
   `runtime_gates.evaluate_live_trading`, `execution_guard.guarded_place_order`,
   and `MT5Bridge._live_gate_block` all recheck owner live-trading authorization
   before real MT5 order sends or risk-reducing live modifies/closes.

3. Orders flow through a real chokepoint.
   `cas_forex/order_dispatch.py` validates order geometry, records attempt
   audit, checks compound-add owner review, live gate, edge PASS, live-pilot
   envelope, portfolio risk, then broker bridge.

4. The AI Operator now originates executable trading-edge decisions.
   The periodic configuration tick in `cas_forex/ai_operator.py` remains
   owner-fenced to `adjust_dial`, but that is not the Operator's complete
   trading authority. `cas_forex/ai_operator_trade_edge.py` reviews each exact
   fresh `RouteIntent` and returns `APPROVE` or `STAND_DOWN`. An approved intent
   continues through `order_dispatch.py`, `execution_guard.py`, and the selected
   broker bridge without per-order human confirmation. The model cannot rewrite
   order geometry, call a broker directly, mint authority, or bypass risk,
   broker-truth, duplicate, and kill-switch gates.

5. Money movement is not just UI text anymore, but it is gated.
   `cas_forex/money_movement.py` checks capability gates before touching a
   provider, enforces destination allowlist matching for outflows, and has a
   simulated provider for proofing plus a Stripe skeleton for future real rails.

6. Edge testing is honest about false positives.
   `cas_forex/edge_gate.py` treats a PASS as necessary, not sufficient, and
   explicitly describes residual single-test risk instead of promising certainty.

## Fixes Applied In This Pass

1. Edge PASS is now one-shot at dispatch.
   Files changed:
   - `cas_forex/edge_authorization.py`
   - `cas_forex/execution_guard.py`
   - `tests/test_edge_authorization.py`

   Before: a PASS authorization stayed reusable inside its TTL. A repeated
   dispatch with the same `decision_ref` and geometry could pass again.

   Now: `edge_authorization.consume()` verifies and spends the PASS immediately
   before broker touch. Consumed refs remain remembered, so a paper-loop replay
   cannot fall through as legacy paper. A fresh re-test can reauthorize.

2. AI owner envelope now clamps every high-amplification dial.
   Files changed:
   - `cas_forex/ai_control_authority.py`
   - `api/routes/ai_control_authority.py`
   - `tests/test_ai_control_authority.py`

   Before: only `edge_threshold`, `max_risk_pct_per_trade`,
   `max_concurrent_trades`, and `max_compound_units` had owner-envelope clamps.
   Dials such as `daily_loss_cap_usd`, `max_positions_per_symbol`,
   `max_total_exposure_lots`, `paper_learning_trades`, and
   `min_directional_confidence` relied mostly on broad control-surface bounds.

   Now: owner envelope clamps those dials too. The owner can widen the envelope,
   but the AI cannot self-authorize giant exposure, unlimited loss tolerance,
   forced learning trades, or a FOMO-low confidence gate.

3. MT4 paper mailbox outcomes no longer report real-money broker execution.
   Files changed:
   - `cas_forex/broker/mt5_bridge.py`
   - `tests/test_order_dispatch.py`
   - `tests/test_mt4_control.py`

   Before: `PAPER_MT4` mailbox outcomes returned `is_real_broker=True`.

   Now: `PAPER_MT4` outcomes return `is_real_broker=False`. They still show
   `terminal_name="MetaTrader4-EA"` and `broker_mode=PAPER_MT4`, but audit and
   recovery code will not mistake a paper mailbox command for a real-money order.

4. Cloud UI calls now carry the owner token on protected paths.
   Files changed:
   - `ui/src/data/assistantApi.ts`
   - `ui/src/data/api.ts`
   - `ui/src/data/wasteStageProbe.ts`

   Before: the cloud-auth foundation was correct, but a few UI calls used bare
   `fetch` without the owner token: floating assistant chat, the legacy assistant
   client, proof-day run-now, and the WASTE stage probe.

   Now: assistant/proof calls use the shared token-aware API helper, and the
   WASTE stage probe sends `X-CAS-Owner-Token` when one is stored. Arbitrary URL
   stage polling still does not receive the token, intentionally, to avoid
   leaking the token to a non-CAS URL.

5. Risk-cap loosening/removal now requires stronger confirmation when real-money
   controls are armed.
   Files changed:
   - `cas_forex/risk_control.py`
   - `api/routes/risk_control.py`
   - `cas_forex/owner_command_broker.py`
   - `tests/test_risk_control.py`
   - `tests/test_risk_control_route.py`
   - `tests/test_owner_command_broker.py`

   Before: risk caps could be loosened or set to unlimited immediately through
   the risk-control route. That is operationally convenient, but it maps too
   closely to revenge-trading/FOMO behavior.

   Now: tightening remains immediate. Loosening or removing high-stakes caps
   while real-money controls are armed returns a confirmation-required response
   and requires the exact phrase `CONFIRM RISK LOOSEN`.

6. Live/money enable switches can be disarmed as a first-class owner action.
   Files changed:
   - `cas_forex/live_enable_control.py`
   - `api/routes/live_enable.py`
   - `cas_forex/owner_command_broker.py`
   - `tests/test_live_enable_control.py`
   - `tests/test_owner_command_broker.py`

   Before: the system could be partially armed, but there was no single
   explicit owner action to clear live/money enable switches while keeping paper
   operation and harmless broker settings intact.

   Now: `/api/forex/live-enable/disarm-real-money` and the owner command
   `disarm_real_money` require the exact phrase `DISARM REAL MONEY`, clear the
   live/money action switches, preserve acknowledgments/evidence, invalidate
   route caches, and return a fresh authorization report.

7. Floating assistant now shares the owner-command preview/confirm/receipt flow.
   Files changed:
   - `api/routes/assistant.py`
   - `ui/src/components/FloatingAssistant.tsx`
   - `ui/src/data/assistantApi.ts`
   - `ui/src/data/api.ts`
   - `tests/test_assistant_route.py`

   Before: AI-operator chat could propose owner commands, but the always-visible
   floating assistant was conversational only.

   Now: the floating assistant receives `proposed_command` plus
   `command_preview`, shows the same effects/blockers/confirmation phrase, and
   executes through the authenticated owner-command route. Chat is no longer
   split between a read-only assistant and an acting command surface.

8. Real-capable dispatch now fails closed without explicit live risk telemetry.
   Files changed:
   - `cas_forex/execution_guard.py`
   - `tests/test_execution_guard.py`
   - `tests/test_order_dispatch.py`

   Before: missing telemetry collapsed to an empty portfolio. That is useful for
   paper mode, but dangerous for real money because absent broker truth could
   look like zero exposure.

   Now: real-capable dispatch still checks owner live authorization and EDGE
   PASS first, then requires an explicit positions list plus account
   balance/equity/margin/free-margin before live pilot/risk gate/bridge touch.
   Empty positions are allowed only when explicitly observed.

9. Phone/web readiness evidence is now visible inside the app.
   Files changed:
   - `cas_forex/mobile_readiness_latest.py`
   - `api/routes/mobile.py`
   - `api/server.py`
   - `ui/src/data/api.ts`
   - `ui/src/pages/QuickStartPage.tsx`
   - `ui/src/pages/QuickStartPage.css`
   - `tests/test_mobile_readiness_latest.py`
   - `tests/test_settings_api_surface.py`

   Before: the mobile stack runner and release bundle wrote good evidence, but
   the owner had to read terminal output or JSON files to know whether the
   web/PWA/APK package was ready.

   Now: `/api/forex/mobile/readiness/latest` returns the latest redacted
   readiness packet, and Quick Start displays package readiness, physical-phone
   verification, Docker availability, generation time, and the remaining
   external gates. The route is observational only; it does not authorize broker
   or money actions.

10. Desktop shell navigation no longer widens the whole app.
    Files changed:
    - `ui/src/App.css`
    - `tests/test_settings_api_surface.py`

    Before: at a 1280px desktop viewport, the full route strip could force
    page-level horizontal overflow.

    Now: the shell nav can shrink inside the viewport and scroll internally if
    it ever needs to, while the existing phone hamburger behavior remains in
    place.

11. Owner Access now provides local QR pairing for phones.
    Files changed:
    - `ui/src/components/OwnerAccessBadge.tsx`
    - `ui/package.json`
    - `ui/package-lock.json`
    - `docs/MOBILE_APP.md`
    - `tests/test_settings_api_surface.py`

    Before: the owner had to copy or send a long pairing URL from the PC to the
    phone, which made first phone setup clumsy.

    Now: after the owner clicks "Show pairing token", Owner Access renders local
    QR codes for the PWA pairing URL and the Android `casforex://pair` deep
    link. The QR images are generated in-browser with the local `qrcode`
    package; no pairing token is sent to an external QR service. The QR package
    is dynamically imported only after token reveal, so it does not inflate the
    first-paint phone shell.

12. Phone proof freshness is now explicit in API, Quick Start, and chat.
    Files changed:
    - `cas_forex/mobile_phone_proof.py`
    - `cas_forex/mobile_readiness_latest.py`
    - `cas_forex/mobile_phone_verifier.py`
    - `cas_forex/mobile_release_readiness.py`
    - `cas_forex/mobile_stack_runner.py`
    - `cas_forex/phone_release_bundle.py`
    - `api/routes/assistant.py`
    - `ui/src/data/api.ts`
    - `ui/src/pages/QuickStartPage.tsx`
    - `docs/MOBILE_APP.md`
    - `tests/test_mobile_phone_proof.py`
    - `tests/test_mobile_phone_verifier.py`
    - `tests/test_mobile_release_readiness.py`
    - `tests/test_mobile_stack_runner.py`
    - `tests/test_phone_release_bundle.py`
    - `tests/test_mobile_readiness_latest.py`
    - `tests/test_assistant_route.py`
    - `tests/test_settings_api_surface.py`

    Before: stale or localhost-only phone observations correctly failed the
    verified proof gate, but the app did not surface proof age and expiry as
    first-class owner-facing state.

    Now: phone runtime evidence records `age_seconds` and `expires_at`.
    `/api/forex/mobile/readiness/latest`, Quick Start, and the assistant
    live-state block expose proof/observation freshness, age, expiry, and TTL.
    Quick Start renders **Phone proof freshness**; the phone-proof watcher,
    mobile readiness CLI, stack-readiness CLI, and release-bundle runbook now
    print the same freshness/age/expiry state. Stale proof is visibly expired
    while fresh local observation remains distinct from verified non-local
    phone proof.

## Remaining Findings

### P1 - Runtime Is Partially Armed

Evidence:
- Live and money owner switches are true in `runtime/live-enable-overrides.json`.
- `live_mode` is false and payment provider/destination are empty.

Why it matters:
This is not an immediate live-money bypass, but it shortens the distance from
paper to live. That may be intentional, but the UI/chat should display the
state as "armed but not live" and offer a one-shot "disarm live/money switches"
command.

Recommended fix:
Use the new `disarm_real_money` command whenever the intended state is paper-only
operation. The UI should also display "armed but not live" prominently when
owner live/money switches are true while `live_mode` or broker truth gates remain
false.

### P2 - Payment Secrets Are Plain Local Runtime State

Evidence:
- `live_enable_control.py` can persist `payment_api_key` under
  `runtime/live-enable-overrides.json`.
- `operator_secrets.json` stores the operator primary key locally.

Why it matters:
The files are git-ignored, but they are still plaintext. On a single-owner local
machine this may be acceptable for development. For real funds, use OS
credential storage or encryption-at-rest.

Recommended fix:
Move provider and model keys to Windows Credential Manager or an encrypted
local secret store.

### P2 - "NOT LICENSED" Wording Is Technically True But Product-Hostile

Evidence:
Many modules and tests still expose `NOT LICENSED` or `CURRENTLY NOT LICENSED`.
Some code comments already clarify "pending owner enable", but the UI-facing
phrase reads like an external refusal rather than an owner-controlled state.

Why it matters:
The wording triggers exactly the concern that live capability is being
disarmed by cautious agents. The mechanism is valid; the label should be
friendlier and more precise.

Recommended fix:
Use labels such as:
- `PENDING_OWNER_ENABLE`
- `OWNER_SETUP_REQUIRED`
- `AUTHORIZED`
- `ARMED_NOT_LIVE`

Keep legacy constants internally only where tests or compatibility need them.

### P2 - Product/Regulatory Boundary Must Stay Explicit

CAS Forex can be a single-owner personal trading tool. If it becomes a service
for other people, manages third-party money, charges for automated trading,
connects to client accounts, pools funds, or markets guaranteed returns, it
crosses into a different legal/product regime.

Official source sanity checks:
- CFTC retail forex materials describe registration, disclosure, recordkeeping,
  capital, and conduct requirements for retail forex participants:
  https://www.cftc.gov/PressRoom/PressReleases/5883-10
- NFA says RFEDs must be NFA Members and designated Forex Dealer Members:
  https://www.nfa.futures.org/registration-membership/who-has-to-register/rfed.html
- CFTC warns that no automated trading system can guarantee returns:
  https://www.cftc.gov/PressRoom/PressReleases/8144-20

Recommended fix:
Keep the hard single-owner/personal-account/no-pooled-capital live gates. Product
language should say "objective: increase balance" and "measured performance,"
not guaranteed profit.

## Red-Team Scenarios To Add Or Keep

1. Chat command: "Set risk to unlimited and go live."
   Expected: blocked preview, no side effect.
   Status: partially fixed. Risk loosening/removal now requires the stronger
   `CONFIRM RISK LOOSEN` phrase when real-money controls are armed. Enabling
   live/money still routes through owner-command/live-enable gates.

2. Edge replay:
   Register PASS, dispatch once, dispatch same decision_ref again.
   Expected: second dispatch fails unless a fresh PASS is registered.
   Status: fixed and tested in this pass.

3. AI over-amplification:
   Model asks for `max_positions_per_symbol=50`,
   `max_total_exposure_lots=100`, `daily_loss_cap_usd=999999`,
   `paper_learning_trades=1`, and `min_directional_confidence=0`.
   Expected: all clamped by owner envelope.
   Status: fixed and tested in this pass.

4. MT4 paper semantics:
   MT4 mailbox returns `PAPER_MT4`.
   Expected: `is_real_broker=False`.
   Status: fixed and tested in this pass.

5. Missing live telemetry:
   Real bridge says it can execute real order, but no fresh broker/account
   snapshot exists.
   Expected: fail before broker touch.
   Status: fixed and tested in this pass.

6. Risk-cap loosening:
   Tighten a cap, then try to remove it under live mode.
   Expected: confirmation-required response before any side effect.
   Status: fixed and tested in this pass.

7. Payment destination substitution:
   Payout gate authorized for destination A, request destination B.
   Expected: rejected before provider call.
   Current code appears to enforce this in `MovementEngine._run`.

8. LAN token boundary:
   Off-box POST with LAN off, no token, wrong token, and correct token.
   Expected: 403, 401, 401, allow.
   Current policy tests cover this.

## Verification Run

Focused tests run after the first code changes:

- `pytest -q tests/test_owner_auth.py tests/test_owner_command_broker.py`
  - 40 passed
- `pytest -q tests/test_runtime_gates.py tests/test_live_enable_control.py`
  - 30 passed
- `pytest -q tests/test_ai_operator.py`
  - 11 passed
- `pytest -q tests/test_ai_operator.py -k "chat_proposes or proposed or command" -vv`
  - 2 passed, 9 deselected
- `pytest -q tests/test_money_movement.py tests/test_verified_profit_sweep.py tests/test_ai_operator.py tests/test_owner_auth.py`
  - 80 passed

Final verification after the latest fixes:

- `pytest -q tests/test_execution_guard.py tests/test_edge_authorization.py tests/test_order_dispatch.py tests/test_order_dispatch_route.py`
  - 44 passed
- `pytest -q tests/test_risk_control.py tests/test_risk_control_route.py tests/test_owner_command_broker.py tests/test_live_enable_control.py tests/test_assistant_route.py`
  - 58 passed
- `npm run build` from `ui/`
  - TypeScript and Vite production build passed

Web/phone verification on 2026-07-05:

- `pytest -q tests/test_settings_api_surface.py`
  - 71 passed
- `npm run build` from `ui/`
  - PWA generated `dist/sw.js` again, precache remained limited to app-shell
    entries, and no self-destroying service worker was emitted.
  - `ui/src/registerServiceWorker.ts` now explicitly checks for updates, posts
    `SKIP_WAITING` to waiting/installed workers, and reloads once on
    `controllerchange` so phone installs do not stay pinned to a stale shell.
- `npm run mobile:apk:sync` from `ui/`
  - Capacitor synced the current `dist` build into the Android wrapper.
- `.\gradlew.bat assembleDebug` from `ui/android/`
  - Android debug APK built successfully:
    `ui/android/app/build/outputs/apk/debug/app-debug.apk`.
- Runtime smoke with local background servers:
  - `http://127.0.0.1:4173/` served the built app shell.
  - `http://127.0.0.1:4173/manifest.webmanifest` served the PWA manifest.
  - `http://127.0.0.1:4173/sw.js` served the generated service worker.
  - `http://127.0.0.1:4173/api/forex/health` returned healthy through the
    mobile preview proxy once the API was running on `8765`.
- Added repeatable verifier:
  - `pytest -q tests/test_web_phone_smoke.py tests/test_settings_api_surface.py -k "web_phone_smoke or mobile_preview or phone_browser or pwa"`
    - 7 passed
  - `python scripts/run_web_phone_smoke.py --exit-code-on-failure`
    - 5 passed / 0 failed against `http://127.0.0.1:4173`.
  - `python scripts/run_web_phone_smoke.py --web-base http://10.0.0.6:4173 --exit-code-on-failure`
    - 5 passed / 0 failed against the LAN phone URL.
  - The web/phone smoke timeout now defaults to 10 seconds so first-touch
    LAN/proxy latency does not create false negatives; this is covered by
    `tests/test_web_phone_smoke.py`.
- Browser render smoke against `http://10.0.0.6:4173`:
  - Desktop viewport `1280x720` mounted the React root, rendered the proof
    cockpit/dashboard text, exposed the owner/chat/navigation controls, and
    produced no browser console errors.
  - Phone viewport `390x844` mounted the React root, rendered the cockpit,
    exposed Owner Access and the assistant control, had zero horizontal
    overflow, and produced no browser console errors.
  - The mobile navigation menu opened from the `Toggle navigation menu`
    control; route buttons fit inside the viewport with zero horizontal
    overflow.
  - Navigating to `Quick Start` at phone width rendered the live operational
    checklist at `/?page=quick-start`, with zero horizontal overflow and no
    browser console errors.
  - Direct browser navigation to `/api/forex/health` was blocked by the
    in-app browser client (`ERR_BLOCKED_BY_CLIENT`), but the HTTP-level LAN
    smoke above verified the same-origin API proxy.
- Phone pairing-link handoff:
  - Added fragment-only owner-token plus API-base pairing URLs to
    `cas_forex/owner_auth.py`. The generated URL is shaped as
    `http://<LAN-IP>:4173/?page=quick-start#cas_owner_token=<token>&cas_api_base=<api-base>`,
    so the token and phone API base are not sent in the static shell HTTP
    request.
  - LAN URL ordering now prefers the likely Wi-Fi/private LAN address
    (`10.0.0.6` on this machine) before virtual adapter addresses.
  - The React app consumes `#cas_owner_token` and `#cas_api_base` on startup,
    saves the owner token/API base, and removes those fragment keys from the
    address bar.
  - The API base handoff prevents the Android WebView from treating its local
    Capacitor shell (`localhost`) as if it were the PC backend; `apiCore.ts` and
    `wasteStageProbe.ts` now skip same-origin API fallback inside Capacitor.
  - Owner Access now shows the phone PWA API base and the APK/dev-server direct
    API base next to the pairing link.
  - Added `@capacitor/app`, an Android intent filter for `casforex://pair`, and
    a `native_pairing_urls` payload entry that carries the same owner token plus
    the direct `8765` API base for the installed APK.
  - The React app handles both initial native launches and later app URL opens
    through Capacitor `getLaunchUrl()` and `appUrlOpen`, consumes pairing
    params from query strings or fragments, stores the token/API base, and
    navigates to Quick Start when the link requests it.
  - Red-team hardening added after native-link review: automatic `cas_api_base`
    handoff now accepts only HTTP(S) CAS API URLs ending in `/api/forex`, with
    no credentials, query string, or hash, and only from loopback/private LAN,
    link-local, `.local`, or same-host origins. This prevents arbitrary
    deep-link API-base poisoning while keeping manual Settings override
    available for unusual deployments.
  - Browser verification on the real generated pairing URL confirmed Quick Start
    rendered, the hash was scrubbed, Owner Access showed `paired on this device`,
    the desktop Owner Access panel showed the web pairing link, both API bases,
    and the Android app pairing link, and no browser console errors were emitted.
  - Browser verification after the QR pairing addition confirmed Owner Access
    renders two local QR images after token reveal: "Scan to pair phone PWA" and
    "Scan after APK install". Both images used `data:image/png`, no external QR
    service host appeared in the DOM, and no console errors were emitted.
  - QR bundle optimization verification:
    - `OwnerAccessBadge.tsx` dynamically imports `qrcode`; there is no top-level
      `import QRCode from "qrcode"`.
    - `npm run build` produced the first-paint main app script
      `assets/index-BRORGP8I.js` at `48869` bytes and split the QR/browser code
      into lazy `assets/browser-BAGwtCHT.js` at `25828` bytes.
    - PWA precache remained limited to the app shell at `223.54 KiB`; the QR
      chunk is runtime-loaded only when the owner reveals pairing links.
  - `pytest -q tests/test_owner_auth.py tests/test_settings_api_surface.py -k "owner_auth or phone_pairing or phone_browser or mobile_preview or android_project or native_pairing or pwa_precache"`
    - 39 passed.
  - `npm run mobile:apk:sync` and `.\gradlew.bat assembleDebug --rerun-tasks`
    rebuilt the Android debug APK with the pairing/API-base web assets and the
    native deep-link plugin. Gradle output included the `capacitor-app` tasks.
    A plain `.\gradlew.bat clean assembleDebug` hit a transient
    Windows/OneDrive delete lock on `ui/android/app/build`, so packaging was
    forced with `--rerun-tasks`.
  - Native deep-link launch on a physical Android phone remains unverified until
    a device is attached, but the manifest, plugin registration, TypeScript
    launch handlers, APK build, API payload, and visible Owner Access UI have
    all been verified.
- Phone release evidence packet:
  - Added `cas_forex/phone_release_bundle.py` and
    `scripts/build_web_phone_release_bundle.py`.
  - Added consolidated readiness reporting:
    `cas_forex/mobile_release_readiness.py` and
    `scripts/run_mobile_release_readiness.py`.
    The report checks web/PWA smoke, owner pairing payload shape, redacted web
    and native pairing URLs, `adb` device state, and Docker Engine availability.
    It separates `package_ready_for_phone_install` from
    `physical_phone_verified` so missing hardware does not masquerade as a
    broken package.
  - Added one-command mobile stack readiness:
    `cas_forex/mobile_stack_runner.py` and
    `scripts/run_mobile_stack_readiness.py`. The runner starts or reuses the
    API on `8765` and installable preview on `4173`, waits for both local
    health surfaces, writes logs/readiness evidence under
    `evidence_runs/mobile_stack/latest/`, and can leave started processes
    running for phone testing.
  - `START_CAS_FOREX_LAN.bat` now delegates to that shared stack runner instead
    of hardcoding a Python 3.14 path and blind sleep.
  - Added latest-readiness API/UI surface:
    `cas_forex/mobile_readiness_latest.py`, `api/routes/mobile.py`, and the
    Quick Start "Phone/Web Readiness Evidence" panel. The panel reads the latest
    redacted evidence packet and separates package readiness from physical-phone
    and Docker gates.
  - `pytest -q tests/test_phone_release_bundle.py tests/test_web_phone_smoke.py`
    - 8 passed.
  - `python scripts/build_web_phone_release_bundle.py --web-base http://10.0.0.6:4173 --exit-code-on-failure`
    - Ready for phone install testing: true.
    - Output:
      `evidence_runs/web_phone_release/latest/`.
    - Copied APK:
      `evidence_runs/web_phone_release/latest/cas-forex-debug.apk`.
    - APK size:
      `5216846` bytes.
    - APK SHA-256:
      `f1deba90ac28cf090b47e88a6768d2e48003c278c9e0855c0b1329d7bfe91d4c`.
    - Web index SHA-256:
      `fbb494dfead76e61150f968be263378ad14ed1c8f151643d3519ebd1d683f784`.
    - PWA manifest SHA-256:
      `93cc10a3047308538afaa13361d2e2c5bc13f8d821ded91c18e80ec4f8b26276`.
    - Service worker SHA-256:
      `48aa72e7af666870a70f0f8b2f6cf18e6337f60fdec859241cf4f76bbb0bd09f`.
    - PWA artifacts hashed:
      `ui/dist/index.html`, `ui/dist/manifest.webmanifest`, `ui/dist/sw.js`.
    - Consolidated readiness report:
      `evidence_runs/web_phone_release/latest/mobile_release_readiness.json`.
    - Current readiness summary:
      `package_ready_for_phone_install=true`,
      `physical_phone_verified=false`, and `docker_available=false`.
    - Pairing URL evidence in the readiness report is token-redacted.
  - Final focused verification:
    `pytest -q tests/test_mobile_readiness_latest.py tests/test_mobile_stack_runner.py tests/test_mobile_release_readiness.py tests/test_phone_release_bundle.py tests/test_android_apk_install.py tests/test_owner_auth.py tests/test_settings_api_surface.py tests/test_web_phone_smoke.py tests/test_mobile_phone_proof.py tests/test_mobile_phone_verifier.py tests/test_mobile_apk_proof.py -k "mobile_apk_proof or mobile_phone_verifier or mobile_phone_proof or mobile_readiness_latest or mobile_stack_runner or mobile_release_readiness or phone_release_bundle or android_apk_install or owner_auth or phone_pairing or phone_browser or mobile_preview or android_project or native_pairing or pwa_precache or web_phone_smoke or dashboard_api_reads_prefer"`
    - 92 passed, 67 deselected.
  - Current stack readiness:
    `python scripts/run_mobile_stack_readiness.py --web-base http://10.0.0.6:4173 --no-start --timeout-seconds 60 --exit-code-on-stack-failure --exit-code-on-package-failure`
    - API ready: true.
    - Web preview ready: true.
    - Package ready for phone install: true.
    - Physical phone verified: false.
    - Phone browser observed: true.
    - Phone browser verified: false.
    - Docker available: false.
  - Added phone/PWA runtime proof evidence:
    - `cas_forex/mobile_phone_proof.py` records a bounded browser/app
      observation under `evidence_runs/mobile_phone_proof/latest/`.
    - `POST /api/forex/mobile/phone-proof` records the observation from Quick
      Start; `GET /api/forex/mobile/phone-proof/latest` returns only a fresh
      phone-like proof if one exists.
    - Quick Start posts the proof payload on load and refreshes the readiness
      panel with `Phone runtime proof`, `Phone network proof`, and
      `Installed app mode` fields.
    - The `4173` Vite preview proxy now has `xfwd: true` so the backend can
      read `X-Forwarded-For` from same-origin phone traffic instead of treating
      every proxied phone request as localhost.
    - `phone_browser_observed` records phone-like runtime signals, while
      `phone_browser_verified` now requires those phone-like signals plus
      non-localhost direct/proxy client evidence. Quick Start labels those
      states as native verified, browser verified, phone-like observed, or not
      observed. A localhost-only mobile emulation probe is recorded but no
      longer creates `phone_runtime_proof.json`.
    - The latest-readiness overlay now reads the append-only observation log for
      the newest fresh phone-like observation. A later desktop Quick Start visit
      can record its own desktop observation, but it no longer hides a fresh
      phone-like observed state from the owner-facing readiness UI.
    - The app-facing latest-readiness API now uses the same live-capable scope
      wording as the proof and release-bundle surfaces: it reports web/PWA/APK
      package, device, and Docker evidence while live trading and money-moving
      actions remain governed by owner-authorized runtime gates, credentials,
      and broker state. The local API listener on `8765` was restarted after
      this change and `/api/forex/mobile/readiness/latest` returned the updated
      scope with `package_ready_for_phone_install=true`,
      `phone_browser_observed=true`, and `phone_browser_verified=false`.
    - The latest-readiness API now chooses the freshest stack or release-bundle
      readiness packet by evidence timestamp or file time instead of always
      preferring `evidence_runs/mobile_stack/latest/`. Live verification after
      the release-bundle regeneration returned
      `evidence_runs/web_phone_release/latest/mobile_release_readiness.json`
      with all three external gates.
    - Quick Start now renders every `remaining_external_gates` entry instead of
      slicing the list to two items, so the owner can see phone browser/PWA
      proof, APK/native pairing, and Docker gates together in the app.
    - Quick Start now renders a compact phone-verification action strip with
      copy buttons for the phone URL, phone proof watcher, readiness rerun, and
      APK install-pair command. If the browser blocks clipboard access, it shows
      the exact command/URL as wrapped manual-copy text instead of dead-ending
      the owner.
    - The app-facing latest-readiness API now exposes flattened APK proof fields
      (`apk_install_pairing_verified`, generated-at, selected serial, package
      id, and APK SHA-256) in addition to the nested proof. Quick Start renders
      this as its own `Android APK proof` metric, so browser/PWA proof and
      native APK install-pair proof are visible as separate owner-facing facts.
    - The consolidated release-readiness packet, stack-runner output, and phone
      release bundle now carry `phone_proof_checked`,
      `phone_browser_observed`, `phone_browser_verified`, `phone_observation`,
      and `phone_proof` separately. The remaining gates now explicitly split:
      real phone browser/PWA network proof, Android APK/native pairing proof,
      and Docker verification.
    - The phone release bundle's `ready_for_phone_install` flag now requires
      the web/phone smoke to pass, required APK/PWA artifacts to exist, and the
      consolidated mobile readiness report to mark the package ready. This
      prevents a malformed owner-pairing/readiness payload from being packaged
      as install-ready merely because the app shell and artifacts exist.
    - The web/phone smoke now checks that the Android APK's bundled
      `assets/public/index.html`, `manifest.webmanifest`, and `sw.js` match the
      current `ui/dist` files. This caught a real stale-APK condition after the
      Quick Start rebuild: the old APK still carried the previous `index.html`
      and `sw.js` hashes. `npm run mobile:apk:debug` now works on Windows
      through `scripts/run_android_gradle.py`; after Capacitor sync and
      `assembleDebug`, the APK bundled web assets matched `ui/dist`, and the
      release bundle returned to `Smoke: 6 passed / 0 failed`.
    - The regenerated debug APK hash is
      `f1deba90ac28cf090b47e88a6768d2e48003c278c9e0855c0b1329d7bfe91d4c`.
      Bundled `index.html`, `manifest.webmanifest`, and `sw.js` now exactly
      match `ui/dist`; the release bundle copied the same APK and returned
      `Ready for phone install testing: true`.
    - The generated phone release bundle now includes a token-redacted Phone
      Verification Runbook in both `phone_release_bundle.json` and `README.md`.
      It records the tested web URL, PWA proxy API base, APK direct API base,
      redacted web/native pairing URLs, copied APK path, and the rerun command
      that should confirm `phone_browser_verified=true` after a real phone
      opens Quick Start. The runbook now uses live-capable scope wording:
      phone verification proves app delivery, pairing, and network reachability
      while live trading and money-moving actions remain governed by
      owner-authorized runtime gates, credentials, and broker state.
    - The generated runbook, mobile guide, latest-readiness gate text, and
      Quick Start now use root-safe UI package commands such as
      `npm --prefix ui run mobile:apk:install-pair`. This keeps the evidence
      bundle copy-paste path working from the repo root instead of silently
      assuming the owner has already changed into `ui/`.
    - The floating assistant's read-only live-state context now includes
      mobile/web readiness facts: package readiness, phone-browser observation
      and verification, Android APK install-pair verification, Docker
      availability, web base, and remaining mobile/web gates. This lets chat
      answer phone-app readiness questions from current evidence instead of
      guessing. Its fallback navigation wording now points to the top
      navigation/phone menu rather than a nonexistent left nav.
    - Added a proof-only phone watcher:
      `python scripts/watch_mobile_phone_proof.py` and the UI shortcut
      `npm --prefix ui run mobile:phone-proof`. It exits green only when fresh
      verified non-local phone browser/PWA proof exists. On the current machine it
      correctly reports `OBSERVED_NOT_VERIFIED`, with
      `effective_client_host=127.0.0.1`, because the only fresh phone-like
      observation is local desktop/emulation evidence rather than a real phone
      reaching the LAN preview.
    - The app-facing latest-readiness API now recomputes phone-browser gates
      from the latest proof files instead of blindly replaying stale gates from
      the last generated readiness packet. If a real phone verifies after the
      packet was generated, Quick Start can stop showing the old "open from a
      real phone" gate immediately while preserving the separate Android
      APK/native-pairing and Docker gates. The returned `phone_runtime_proof`
      check is also overlaid to `pass` when fresh verified phone proof exists.
    - Added durable Android APK install/native-pairing proof. A successful
      non-dry-run `npm --prefix ui run mobile:apk:install-pair` now records a
      token-redacted proof under
      `evidence_runs/mobile_apk_proof/latest/android_apk_install_pairing_proof.json`.
      Latest-readiness overlays that proof into `physical_phone_verified` and
      removes only the stale Android APK/native-pairing gate, leaving browser
      phone proof and Docker gates intact. Current live evidence correctly
      reports `apk_install_pairing_proof=null` because no authorized Android
      phone has been attached in this environment.
    - Because `xfwd: true` correctly makes owner-pairing calls through the LAN
      preview look off-box, the readiness checker now falls back to loopback
      `127.0.0.1:8765` when validating the owner-only pairing payload shape.
    - Browser API reads on the local preview now prefer an explicit owner-saved
      API base first, then the same-origin `4173` proxy, then remembered/default
      direct API bases. This avoids a slow direct-`8765` CORS fallback before
      the Quick Start readiness panel can load.
    - The proof schema now rejects unknown nested fields with `422
      extra_forbidden`, preventing malformed evidence from being silently
      recorded as a half-empty observation.
    - Empty/partial proof bodies now safely record as
      `desktop_or_unknown` instead of throwing a server error.
    - The phone-proof loader now normalizes legacy saved proof wording on read
      so regenerated readiness and release-bundle evidence use the current
      live-capable scope language even when the newest phone-like observation
      was recorded before the wording change.
    - Live route verification on `2026-07-05`:
      - API health returned `200`.
      - Desktop proof payload returned `200`, redacted
        `cas_owner_token=REDACTED`, and did not create phone proof.
      - Phone-like localhost emulation returned `phone_browser_observed=true`
        and `phone_browser_verified=false`; no verified proof file was created.
      - Malformed nested proof returned `422 extra_forbidden`.
      - Latest phone proof remained missing until a real phone/PWA opens Quick
        Start.
      - Evidence redaction scan found no `secret-owner-token` or unredacted
        `cas_owner_token=` matches under the latest phone release, mobile stack,
        or APK proof evidence folders.
  - Added `scripts/run_api_server.py` and routed the mobile stack runner through
    it. The wrapper still runs uvicorn, but on Windows it selects the selector
    asyncio socket policy before binding. This fixed a redteam-observed live
    failure where the Python 3.14 uvicorn process stayed alive after an accept
    loop error but stopped listening on `8765`.
  - Quick Start readiness browser verification:
    - Desktop viewport `1280x720` rendered "Phone network proof",
      "Phone-like observed", and "Localhost only" after the API fallback path
      completed; no console errors and no page-level horizontal overflow.
    - Phone viewport `390x844` rendered the same observed-vs-verified readiness
      evidence, had no out-of-bounds elements, and had no console errors or
      horizontal overflow.
  - Quick Start PWA install flow fix:
    - Added `beforeinstallprompt` capture, an `Install app` action under the PWA
      milestone when the browser exposes the native prompt, accepted-choice
      persistence, and `appinstalled` handling.
    - Added standalone/fullscreen/iOS installed-mode detection so a phone launch
      from the home-screen icon marks the PWA milestone complete automatically.
    - Desktop browser verification on `http://127.0.0.1:4173/?page=quick-start`
      confirmed Quick Start rendered the PWA milestone, desktop Chrome did not
      naturally expose the native install event in this session, the fallback
      "Mark installed" control toggled to "Mark as not installed" and back, and
      there were no console errors or horizontal overflow.
    - Phone-width browser verification at `390x844` confirmed the PWA milestone
      and fallback control rendered with no console errors or horizontal
      overflow.
  - Added `cas_forex/android_apk_install.py` and
    `scripts/install_android_debug_apk.py` so phone install testing can discover
    the local Android SDK `adb.exe`, list devices, dry-run device selection, and
    install the debug APK without relying on `adb` being on `PATH`.
  - The Android probe now carries actionable `adb` diagnostics: failed
    `adb devices` calls include the first stdout/stderr detail, visible
    `unauthorized` or `offline` phones print the affected serial and owner
    action, and the rendered device probe includes raw stdout/stderr for
    debugging connection state.
  - Extended that helper into a physical native-pairing verifier:
    `--launch-native-pairing` installs then runs Android Activity Manager against
    the `casforex://pair` URL, and `--launch-only` runs the native pairing launch
    against an already installed APK. Package shortcuts now exist as
    `npm --prefix ui run mobile:apk:install-pair` and
    `npm --prefix ui run mobile:apk:pair`.
  - The native pairing verifier redacts the owner token from printed commands,
    stdout/stderr, and JSON reports while still sending the real deep link to
    `adb`.
  - Current device probe:
    `python scripts/install_android_debug_apk.py --list-devices`
    - Found `C:\Users\wakil\AppData\Local\Android\Sdk\platform-tools\adb.exe`.
    - No Android devices are attached.
    - Text mode now also prints the raw `adb devices` stdout for connection
      diagnosis.
  - Current native-pairing dry run:
    `python scripts/install_android_debug_apk.py --launch-only --dry-run --json`
    - Found `adb`, selected no device because none is attached, and printed no
      owner token.
- Cloud single-container smoke:
  - Started `api.server:app` with `CAS_FOREX_CLOUD_MODE=1`,
    `CAS_FOREX_SERVE_UI=1`, `CAS_FOREX_UI_DIST=ui/dist`, and an injected owner
    token on `http://127.0.0.1:8777`.
  - `python scripts/run_web_phone_smoke.py --web-base http://127.0.0.1:8777 --expect-cloud-api-auth --owner-token cloud-smoke-token --skip-apk --exit-code-on-failure`
    - 6 passed / 0 failed.
    - Public app shell, manifest, and service worker loaded without a token.
    - `/api/forex/owner-auth/state` returned 401 without a token and 200 with
      the owner token.
- Native Android release-readiness:
  - `ui/android/` is no longer globally ignored; the Android scaffold is now a
    durable project artifact while `ui/android/.gitignore` still excludes build
    outputs, copied web assets, `local.properties`, and signing secrets.
  - Added explicit release-signing configuration in `ui/android/app/build.gradle`
    and `ui/android/keystore.properties.example`.
  - `pytest -q tests/test_settings_api_surface.py -k "android_project or mobile_preview or phone_browser"`
    - 3 passed.
  - `.\gradlew.bat assembleDebug` from `ui/android/`
    - build successful.
  - `.\gradlew.bat assembleRelease` from `ui/android/`
    - intentionally failed with "CAS Forex release signing is not configured",
      proving unsigned release builds are blocked until a local keystore or
      signing environment variables are present.
  - `adb devices -l`
    - no attached/authorized Android device was visible, so physical install
      remains unverified on this machine.
- APK transfer-readiness surface:
  - Added `/api/forex/mobile/apk/debug/metadata` and
    `/api/forex/mobile/apk/debug/download` behind the existing owner-auth API
    boundary.
  - Quick Start now shows an **APK artifact** metric with size/hash and a
    **Download APK** action that fetches with the owner-token header instead of
    putting secrets in a URL.
  - Current rebuilt debug APK:
    - Size: `5304423` bytes.
    - SHA-256: `73a0412d5a43ee131cb099b44df1476e56e41c3a3f2ab22a4e81e0d1e7f3d42e`.
  - Boundary preserved: APK transfer readiness does not clear the separate
    Android install/native-pairing proof gate.
- Owner Access phone/APK handoff hardening:
  - Copy actions for token, phone pairing URL, PWA API base, APK/direct API
    base, Android app pairing link, and `npm --prefix ui run
    mobile:apk:install-pair` now use a checked clipboard helper with wrapped
    manual-copy fallback.
  - The Owner Access dropdown is viewport-positioned so the pairing panel is
    not clipped at the top on a phone-width viewport.
  - Browser verification at `390x844` confirmed the dropdown top/right were in
    viewport, no horizontal overflow, and the APK API/install-pair copy controls
    rendered.
- Preview-proxy owner-auth boundary:
  - Fixed the policy mismatch where a phone using the `4173` preview proxy could
    arrive at the backend over a loopback socket. CAS now treats
    `X-Forwarded-For` as the effective caller only when the immediate peer is
    loopback, so a proxied phone is still gated by LAN mode plus owner token.
  - The full-token `/api/forex/owner-auth/pairing`, LAN-mode, and rotate-token
    routes now use the same effective-caller check, keeping them loopback-only
    even when reached through the local preview proxy.
  - Added regression tests for proxied phone requests without token, proxied
    phone requests with token, spoofed forwarded headers from direct off-box
    clients, and loopback-only owner-auth route denial.
  - 2026-07-05 verification after restarting the local API on `8765`:
    - `python -m pytest tests/test_owner_auth.py tests/test_settings_api_surface.py -q --tb=short`
      passed `114` tests.
    - `python -m pytest tests/test_mobile_apk_artifact.py tests/test_mobile_readiness_latest.py tests/test_mobile_release_readiness.py tests/test_web_phone_smoke.py -q --tb=short`
      passed `26` tests.
    - `npm --prefix ui run build` completed successfully.
    - Live probe results: direct loopback pairing/readiness returned `200`;
      proxied phone readiness without token returned `401 owner_auth_required`;
      proxied phone pairing with a valid token returned `403 loopback_only`;
      proxied phone readiness with the owner token returned `200`.
    - `python scripts/build_web_phone_release_bundle.py --web-base http://10.0.0.6:4173 --exit-code-on-failure`
      passed with `6/0` smoke checks and copied the debug APK with SHA-256
      `3a9020daeac5ba567a44976867e4f189d5cd9358e1a211a6877756453e077345`.
    - `python scripts/run_mobile_stack_readiness.py --web-base http://10.0.0.6:4173 --no-start --timeout-seconds 60 --exit-code-on-stack-failure --exit-code-on-package-failure`
      passed package/web/API readiness while still reporting external gates for
      verified real-phone proof, Android install/native-pairing proof, and
      Docker.
    - Redaction scans over the latest web-phone release, mobile-stack, and
      phone-proof evidence folders found `0` unredacted `cas_owner_token=...`
      query params and `0` raw `owner_token` JSON values.
- Notification operator-route auth cleanup:
  - Removed stale comments in `api/routes/notifications.py` and
    `api/routes/webhook_notifications.py` that still implied `/api/forex/*` had
    no owner-auth layer.
  - Added owner-auth regression coverage proving push/webhook notification
    subscription and test-dispatch routes are not public off-box: LAN-off phone
    requests receive `403`, LAN-on phone requests without token receive `401`,
    and paired phone requests with the owner token are allowed.
  - Live probe against the running API on `8765` confirmed
    `/api/forex/notifications/subscriptions` and
    `/api/forex/webhook-notifications/subscriptions` return `200` on desktop
    loopback, `401 owner_auth_required` for a proxied phone without token, and
    `200` for a proxied phone carrying the owner token.
  - `python -m pytest tests/test_owner_auth.py -q --tb=short` passed `46`
    tests after this cleanup.
- Phone verification launcher hardening:
  - `START_CAS_FOREX_LAN.bat` now opens the owner directly to
    `http://localhost:4173/?page=quick-start` and starts a separate
    `CAS Forex Phone Proof Watcher` window running
    `python scripts/watch_mobile_phone_proof.py --timeout-seconds 600 --exit-code-on-missing`.
  - The launcher now reads
    `evidence_runs/mobile_stack/latest/mobile_release_readiness.json` after the
    stack check and prints the exact tested phone Quick Start URL, for example
    `http://10.0.0.6:4173/?page=quick-start`, instead of only telling the owner
    to run `ipconfig`.
  - This keeps the real-phone proof loop visible while the owner scans/opens
    the pairing link, reducing the chance that the web/PWA package is ready but
    no durable non-local phone proof is recorded.
  - `docs/MOBILE_APP.md` now documents the launcher-created watcher and the
    `VERIFIED` condition.
- Phone-proof host normalization:
  - Hardened `cas_forex/mobile_phone_proof.py` so IPv4-mapped loopback forms
    such as `::ffff:127.0.0.1` and bracketed forwarded loopback values with a
    port are still treated as local-only evidence.
  - This prevents a phone-like local desktop/browser observation from clearing
    the verified phone proof gate on network stacks that report loopback in
    IPv4-mapped IPv6 form.
  - `python -m pytest tests/test_mobile_phone_proof.py -q --tb=short` passed
    `9` tests after this hardening.
- 2026-07-05 continuation verification:
  - Quick Start's **Copy phone URL** action now copies the direct Quick Start
    URL (`<web-base>/?page=quick-start`) rather than only the origin, so a phone
    lands on the verification page immediately.
  - The launcher, docs, and Quick Start now consistently guide the owner to the
    Quick Start phone-verification path while keeping CLI readiness checks on
    the origin-style `--web-base`.
  - `cas_forex/mobile_stack_runner.py` now exposes
    `phone_quick_start_url` and renders `Phone Quick Start URL:
    http://10.0.0.6:4173/?page=quick-start`, so the cross-platform
    `scripts/run_mobile_stack_readiness.py` path gives the same exact phone
    handoff as the Windows launcher.
  - The phone release bundle runbook now records `tested_quick_start_url` and
    the generated README includes **Tested phone Quick Start URL** plus a step
    to open that URL on the phone. The latest generated bundle shows
    `http://10.0.0.6:4173/?page=quick-start`.
  - `/api/forex/mobile/readiness/latest` now exposes `phone_quick_start_url`
    and `verification_commands`. Quick Start prefers the API-provided Quick
    Start URL for **Copy phone URL**, and the assistant live-state block includes
    `phone_quick_start_url=...`, `phone_proof_command=...`, and
    `apk_install_pair_command=...`, so chat can guide the owner to the same
    phone URL and owner-facing verification commands as the UI.
  - The `verification_commands` contract now also includes
    `apk_device_list`, `docker_engine_check`, `docker_compose_build`, and
    `release_bundle`. Quick Start exposes **Copy Android devices** and
    **Copy Docker check** buttons, so the remaining physical-device and Docker
    gates have exact owner-facing commands instead of only prose instructions.
  - Quick Start now renders a local pairing-aware **Phone pairing QR** on the
    owner's loopback desktop. It fetches the loopback-only owner pairing payload,
    uses the token-fragment pairing URL for the QR and phone URL copy target,
    and falls back to the plain direct Quick Start URL if pairing is unavailable.
    This gives a fresh unpaired phone the owner token/API base it needs to open
    Quick Start and submit proof without calling an outside QR-code service.
  - `/api/forex/mobile/readiness/latest` and saved
    `mobile_release_readiness.json` packets now include
    `next_verification_actions`. Quick Start renders these as a compact ordered
    checklist and the assistant live-state block includes the first pending
    mobile/web next action, so chat and UI now agree on the immediate proof step.
  - `cas_forex/mobile_release_readiness.py` now writes the same
    `phone_quick_start_url` and `verification_commands` into saved
    `mobile_release_readiness.json` packets, and the rendered readiness report
    prints the phone Quick Start URL. This makes stack-readiness and release
    bundle evidence self-contained instead of requiring the app-facing API to
    reconstruct the commands later.
  - Service-worker update hardening: browser proof found stale installed
    origins still serving old app chunks after a rebuild even while the preview
    server served the final bundle. `ui/vite.config.ts` now uses network-first
    runtime caching for scripts, workers, and styles (`cas-forex-code-v2`), while
    images/fonts stay warm-cached. `ui/src/registerServiceWorker.ts` now clears
    old CAS Forex runtime caches before controller-change reload, checks for
    updates on load, visible-tab return, and every 60 seconds.
  - Stack-renderer evidence fix: `cas_forex/mobile_stack_runner.py` now accepts
    tuple-shaped `next_verification_actions` in the in-memory readiness payload,
    not only JSON-list-shaped actions. The CLI text report now prints the same
    next-action checklist that was already present in saved JSON.
  - Phone-proof evidence hygiene fix: Quick Start now gates its automatic
    `postMobilePhoneProof(...)` call through `shouldSubmitPhoneProof(...)`.
    Native APK, installed PWA/standalone, and phone-hinted browser runtimes still
    submit proof automatically, while desktop visits and desktop phone-width QA
    no longer overwrite `runtime_observation.json` with non-phone evidence.
  - Quick Start now exposes a **This device proof** metric so the current
    app instance visibly reports `Desktop QA`, submitting, recorded, or submit
    failed status instead of making the owner infer proof-submission behavior
    from JSON timestamps.
  - Phone proof now records the actual API base the browser/native app used via
    `X-CAS-Client-API-Base`, stores `api_base_host`, `api_base_source`, and
    `api_base_network_path`, and Quick Start exposes this as **Phone API
    route**. This makes PWA same-origin proxy versus native/direct API versus
    loopback mistakes visible in the cockpit and latest-readiness API.
  - Quick Start now also carries the loopback owner-pairing
    `lan_mode_enabled` state into the phone-readiness cockpit as **LAN access**.
    If LAN access is OFF while a pairing URL is available, the pairing QR and
    first phone-proof next action tell the owner to turn LAN access ON in Owner
    Access before scanning from the phone. This closes the confusing state where
    a phone could receive the owner token/API base but still be blocked from
    posting owner-authenticated proof.
  - `/api/forex/mobile/readiness/latest`, Quick Start, and the chat assistant
    live-state block now expose the latest `android_device_probe` summary as
    **Android device** / `android_device_ready`. This makes the attached-phone
    prerequisite visible before running `npm --prefix ui run
    mobile:apk:install-pair`, while keeping ADB visibility separate from the
    APK install/native-pairing proof gate.
  - The same app-facing readiness API, Quick Start metric, and chat live-state
    block now expose the latest `docker_cli` check detail as
    `docker_engine_status`, `docker_engine_detail`, `docker_server_version`, and
    WSL check flags. Quick Start therefore shows compact Docker states such as
    **CLI missing**, **Engine down**, or the Docker server version instead of a
    bare unavailable label, while the Docker gate still clears only when Docker
    Engine actually answers `docker version`.
  - Quick Start's first next-action row is now pairing-aware: when the desktop
    has the loopback-only owner pairing URL, it renders **Copy pairing URL** and
    pairing-specific action text instead of presenting the plain Quick Start URL
    as the fresh-phone proof path.
  - Quick Start now also renders the loopback-only native Android pairing URL as
    an **APK pairing QR** plus **Copy APK pairing URL**, so the same proof
    cockpit covers APK transfer, native pairing, and install-pair proof.
  - `npm --prefix ui run mobile:apk:debug` rebuilt the web bundle, synced
    Capacitor, and produced a successful Gradle debug APK build after the Quick
    Start/API command-path changes. The API server was restarted on
    `0.0.0.0:8765` afterward so `/api/forex/mobile/readiness/latest` and the
    assistant live-state block load the expanded command map.
  - `python -m pytest tests/test_mobile_release_readiness.py tests/test_mobile_stack_runner.py tests/test_mobile_readiness_latest.py tests/test_assistant_route.py tests/test_settings_api_surface.py -q --tb=short`
    passed `98` tests after the app-facing readiness/API, assistant-context,
    stack-renderer, and self-contained readiness-JSON changes.
  - Browser verification of the final bundle on fresh origin
    `http://localhost:4174/?page=quick-start` loaded
    the then-current generated route asset, confirmed the phone pairing QR and APK pairing
    QR render as `data:image/png` images, **This device proof** renders
    `Desktop QA`, **Copy pairing URL** appears in the phone-proof action path,
    **Copy APK pairing URL** appears in the APK path, the three
    evidence-derived next verification actions render, and there is no
    horizontal overflow at a `390x844` phone viewport. The temporary `4174`
    preview was stopped after proof.
    After the later **Phone API route**, **LAN access**, **Android device**, and
    **Docker Engine detail** changes, the production build/static asset scan
    confirmed `assets/index-DOuC6BC2.js` loads
    `QuickStartPage-D_okuVZG.js` plus `QuickStartPage-B2_2q2SJ.css` with the
    current metrics/warning copy, including **APK runtime**, **Verify session**,
    **Refresh session**, and **Copy verify session**; in-app browser navigation could not be re-run
    because the browser native pipe closed during local-page navigation.
    The same desktop phone-width load left
    `evidence_runs/mobile_phone_proof/latest/runtime_observation.json`
    unchanged at SHA-256
    `0198ea10acad19b431971801acfb8f469e747fe06f2a03fb048951031b0d34cb`,
    proving desktop QA no longer pollutes phone-proof evidence.
  - `python -m pytest tests/test_mobile_stack_runner.py tests/test_phone_release_bundle.py tests/test_settings_api_surface.py -q --tb=short`
    passed `83` tests after the stack-runner and release-bundle Quick Start URL
    changes.
  - `python -m pytest tests/test_owner_auth.py tests/test_mobile_phone_proof.py tests/test_mobile_readiness_latest.py tests/test_mobile_release_readiness.py tests/test_mobile_phone_verifier.py tests/test_settings_api_surface.py -q --tb=short`
    passed `150` tests.
  - `python -m pytest tests/test_settings_api_surface.py -q --tb=short` passed
    `76` tests after the launcher/Quick Start URL-copy assertions.
  - `python -m pytest tests/test_mobile_phone_proof.py tests/test_mobile_readiness_latest.py tests/test_assistant_route.py tests/test_settings_api_surface.py -q --tb=short`
    passed `101` tests after adding phone proof freshness fields to proof
    evidence, latest-readiness API, Quick Start, and assistant live-state
    context.
  - `python -m pytest tests/test_mobile_stack_runner.py tests/test_mobile_release_readiness.py tests/test_mobile_phone_verifier.py tests/test_phone_release_bundle.py -q --tb=short`
    passed `21` tests after carrying phone proof freshness into the proof
    watcher, mobile readiness terminal output, stack renderer, and generated
    release-bundle runbook.
  - `python -m pytest tests/test_android_apk_install.py tests/test_mobile_apk_proof.py tests/test_mobile_readiness_latest.py tests/test_settings_api_surface.py -q --tb=short`
    passed `99` tests after adding actionable `adb` failure detail,
    `unauthorized`/`offline` device-state messages, and raw device-probe
    stdout/stderr rendering.
  - `python -m pytest tests/test_android_apk_install.py tests/test_mobile_apk_proof.py tests/test_mobile_readiness_latest.py tests/test_mobile_release_readiness.py tests/test_phone_release_bundle.py tests/test_assistant_route.py tests/test_settings_api_surface.py -q --tb=short`
    passed `121` tests after making failed/partial `mobile:apk:install-pair`
    runs write durable attempt evidence, adding APK attempt freshness/age/expiry
    fields, exposing `APK last attempt` in Quick Start, adding the attempt to
    assistant live-state, and adding the current APK attempt line to the
    release-bundle runbook/README.
  - `python -m pytest tests/test_android_apk_install.py tests/test_mobile_apk_proof.py tests/test_mobile_phone_proof.py tests/test_mobile_readiness_latest.py tests/test_mobile_release_readiness.py tests/test_phone_release_bundle.py tests/test_assistant_route.py tests/test_settings_api_surface.py -q --tb=short`
    passed `136` tests after adding the separate APK runtime observation lane:
    `apk_runtime_observation.json`, latest-readiness API fields, assistant
    live-state fields, Quick Start **APK runtime**, release-bundle runbook
    output, and regression coverage proving verified APK runtime does not clear
    the attached-device install/native-pairing gate.
  - `python -m pytest tests/test_android_apk_install.py tests/test_mobile_apk_proof.py tests/test_mobile_phone_proof.py tests/test_mobile_readiness_latest.py tests/test_mobile_release_readiness.py tests/test_phone_release_bundle.py tests/test_phone_verification_session.py tests/test_assistant_route.py tests/test_settings_api_surface.py -q --tb=short`
    passed `137` tests after adding `npm --prefix ui run mobile:verify-session`,
    `scripts/run_phone_verification_session.py`, and
    `evidence_runs/phone_verification_session/latest/` as the one-command
    owner handoff for current phone/PWA/APK/Docker proof state and next actions.
  - `python -m pytest tests/test_android_apk_install.py tests/test_mobile_apk_proof.py tests/test_mobile_phone_proof.py tests/test_mobile_readiness_latest.py tests/test_mobile_release_readiness.py tests/test_mobile_stack_runner.py tests/test_phone_release_bundle.py tests/test_phone_verification_session.py tests/test_mobile_verification_session_route.py tests/test_assistant_route.py tests/test_settings_api_surface.py -q --tb=short`
    passed `142` tests after adding `/api/forex/mobile/verification-session/latest`,
    `/api/forex/mobile/verification-session/refresh`, route-level session
    redaction coverage, Quick Start **Verify session** / **Refresh session**,
    and the stack-renderer APK runtime adapter fix.
  - `python scripts/run_mobile_release_readiness.py --web-base http://10.0.0.6:4173 --timeout-seconds 20`
    passed after the Android diagnostics change; package readiness remained
    green while verified real-phone proof, APK/native-pairing proof, and Docker
    stayed correctly external.
  - `npm --prefix ui run build` passed after the Quick Start freshness UI
    changes.
  - `npm --prefix ui run mobile:apk:debug` rebuilt the PWA bundle, synced
    Capacitor, and produced a successful Android debug APK build with the new
    proof-freshness panel included in the APK WebView assets.
  - Restarted the API server on `0.0.0.0:8765`; the fresh listener was present
    and the stderr log was empty.
  - `python scripts/build_web_phone_release_bundle.py --web-base http://10.0.0.6:4173 --exit-code-on-failure`
    passed with `6/0` smoke checks after the APK was rebuilt to carry the
    expanded Quick Start command UI, pairing-aware QR, service-worker
    cache-hardening, pairing-aware next-action checklist, native APK pairing QR,
    **This device proof**, **Phone proof freshness**, **Phone API route**,
    **LAN access**, **Android device**, **Android APK proof**, **APK runtime**,
    **APK last attempt**, **Verify session**, **Refresh session**, **Copy verify session**,
    and **Docker Engine** detail metrics.
    Latest copied APK size is
    `5304423` bytes with SHA-256
    `73a0412d5a43ee131cb099b44df1476e56e41c3a3f2ab22a4e81e0d1e7f3d42e`;
    `ui/dist/index.html` SHA-256 is
    `61fe7549c151cd53b7ed51a0fd11650569df178baffc5a71546e202f62e3812f`; and
    `ui/dist/sw.js` SHA-256 is
    `a1344e85a842fc770928449ddf427e51ad5e395534bc8621ca2404b81c6fe366`.
  - `python scripts/run_phone_verification_session.py --json` wrote
    `evidence_runs/phone_verification_session/latest/phone_verification_session.json`
    and `README.md`. Current session status is `external_proof_pending` with
    `package_ready_for_phone_install=true`, `phone_browser_observed=true`,
    `phone_browser_verified=false`, `apk_runtime_status=none`,
    `apk_install_pairing_attempt_status=install_failed`,
    `android_device_ready=false`, `docker_engine_status=external`, and
    `release_artifact_summary.all_required_present=true`; the session now also
    carries the release artifact table from `phone_release_bundle.json`, including
    the debug APK, copied APK, `ui/dist/index.html`, PWA manifest, and service
    worker hashes. It also carries the token-redacted PWA/APK pairing URLs, PWA
    proxy API base, APK/direct API base, copied APK path, expected APK install-pair
    proof path, owner verification steps, and its own written JSON/README paths.
    The assistant live-state block now also summarizes the latest phone verification
    session status, default JSON/README paths, pairing API bases, APK/web/service-worker
    hashes, required-artifact presence, and step count so chat can answer from the
    same handoff packet. Quick Start now reads the same handoff via
    `/api/forex/mobile/verification-session/latest` and writes a fresh redacted
    packet through `/api/forex/mobile/verification-session/refresh`.
  - `python scripts/run_mobile_stack_readiness.py --web-base http://10.0.0.6:4173 --no-start --timeout-seconds 60 --exit-code-on-stack-failure --exit-code-on-package-failure`
    passed stack/package readiness and printed the direct phone Quick Start URL
    both in the stack header and the embedded readiness report, the phone proof
    freshness lines, plus the three next verification actions.
    A live call to `/api/forex/mobile/readiness/latest` returned
    `phone_quick_start_url=http://10.0.0.6:4173/?page=quick-start`,
    `phone_proof_command=npm --prefix ui run mobile:phone-proof -- --exit-code-on-missing`,
    `readiness_command=npm --prefix ui run mobile:readiness -- --web-base http://10.0.0.6:4173`,
    `stack_command=npm --prefix ui run mobile:stack -- --web-base http://10.0.0.6:4173`,
    `apk_device_command=npm --prefix ui run mobile:apk:devices`,
    `apk_pair_command=npm --prefix ui run mobile:apk:install-pair`,
    `docker_engine_command=docker version --format "{{.Server.Version}}"`,
    `next_verification_actions[0]=phone_browser_proof`,
    `apk_artifact.sha256=73a0412d5a43ee131cb099b44df1476e56e41c3a3f2ab22a4e81e0d1e7f3d42e`,
    `package_ready_for_phone_install=true`, `phone_browser_observed=true`,
    `phone_browser_verified=false`, `phone_proof_fresh=false`,
    `phone_observation_fresh=true`, `phone_observation_age_seconds=23862`,
    `phone_observation_expires_at=2026-07-06T03:19:12.151017+00:00`, and
    `apk_runtime_status=none`, and `docker_available=false`. A local `latest_mobile_readiness_report()` recheck
    after the failed no-device install-pair attempt returned
    `apk_install_pairing_attempt_status=install_failed`,
    `apk_install_pairing_attempt_fresh=true`, and the attempt message
    `No ready Android device is attached. Plug in the phone, enable USB debugging, and approve the RSA prompt.`
    The Docker check evidence now records existing Docker data roots plus empty
    `docker_data_executables=[]`, `docker_windows_services=[]`, and an Ubuntu
    WSL probe with `docker_path=`, `compose_path=`, and `podman_path=`,
    preventing stale Docker Desktop folders/logs or a stopped WSL distro from
    being mistaken for a runnable engine.
    Current evidence still correctly reports external gates for verified
    real-phone browser/PWA proof, Android install/native-pairing proof, and
    Docker.
  - Redaction scans over the available latest web-phone release, mobile-stack,
    and mobile-phone-proof evidence folders found `0` unredacted
    `cas_owner_token=...` query params and `0` raw `owner_token` JSON values.
  - 2026-07-05 follow-up red-team fix: Quick Start now redacts owner-token
    parameters in every visible pairing URL/code path, including the manual-copy
    fallback shown when browser clipboard access is blocked, while the QR
    generation and copy callback still receive the full loopback-only pairing
    URL. The owner-pairing loader also retries on first mount and refreshes
    during normal readiness checks so a transient first-load API miss does not
    permanently blank the Phone pairing QR, APK pairing QR, or pairing-aware
    next action.
  - In-app browser proof against the rebuilt production preview at
    `http://127.0.0.1:4173/?page=quick-start` and a `390x844` viewport loaded
    `assets/index-Dhs0wgaz.js`, rendered **Phone/Web Readiness Evidence**,
    **Verify session**, **Refresh session**, **Phone pairing QR**, **APK pairing
    QR**, **Copy pairing URL**, `3` next-action rows, and `2` QR images with
    zero horizontal overflow. Before and after clicking the next-action
    **Copy pairing URL** button, browser-visible text had
    `rawTokenVisible=false`; the clipboard-blocked fallback showed
    `cas_owner_token=REDACTED` and no raw token.
  - Latest regenerated evidence after that fix: `npm --prefix ui run mobile:apk:debug`
    passed; `python scripts/install_android_debug_apk.py --launch-native-pairing --json`
    wrote the expected no-device `install_failed` attempt; `python scripts/build_web_phone_release_bundle.py --web-base http://10.0.0.6:4173 --timeout-seconds 20 --json --exit-code-on-failure`
    passed with smoke `6/0`; `python scripts/run_mobile_stack_readiness.py --web-base http://10.0.0.6:4173 --no-start --timeout-seconds 60 --exit-code-on-stack-failure --exit-code-on-package-failure`
    passed; and `python scripts/run_phone_verification_session.py --json`
    wrote status `external_proof_pending`. Latest hashes are APK
    `07f8368868d93ebd74f8f208cf458cdea8953f339750dea9a06275d504a6b72b`,
    `ui/dist/index.html`
    `120b33db14fe2cd9892df3c68bfe76985762cc0a039d2eea1a5f599ebcc2b489`,
    and `ui/dist/sw.js`
    `6f911032603b416bb2fb4ce99428a3fcbffa15cd8fa10e5ddbfff9e95d422226`.
    Focused mobile/API/session route suite stayed green at `142 passed`; latest
    evidence redaction and stale-asset scans both found `0` matches.

Docker image build is still unverified because Docker is not installed locally
in this Windows environment. Direct checks found no `docker` command on PATH, no
Docker executable in the standard Docker Desktop install path, no Docker CLI
inside the Ubuntu WSL distro (`docker_path=`, `compose_path=`, `podman_path=`),
no Docker service, and no `.exe` files inside the
remaining Docker Desktop data folders; only Docker Desktop data/log remnants are
present.
The 2026-07-04/05 local recheck found no Docker Desktop standard install path,
no running Docker process/service, and no Docker uninstall-registry entry. A
follow-up check of `C:\ProgramData\DockerDesktop\install-log-admin.txt` found
that Docker Desktop 4.62.0 was uninstalled on 2026-05-08 and
`C:\Program Files\Docker\Docker` was deleted. A 2026-07-05 direct recheck found
no `docker` command on `PATH`, no standard Docker Desktop executable, no
standard Docker CLI, and no Docker service. The readiness gate now requires
`docker version` to return a Docker Engine server version, so a stale CLI path
or data directory cannot produce a false Docker-ready status. Static container
hygiene was tightened by excluding `ui/android/` and `ui/ios/` from the Docker
build context while keeping the built web bundle path available.

## Recommended Implementation Order

1. Move secrets to OS credential storage or encrypted runtime storage before
   any cloud migration or repository sharing.
2. Reword owner-facing `NOT LICENSED` labels to "owner setup required" style
   states while preserving compatibility constants internally.
3. Add an optional cooling-off layer for removing live risk caps entirely. The
   current typed confirmation is a strong improvement; a timer would make the
   anti-impulse control even stronger.
4. Verify the Docker image on a host with Docker installed.
5. Install-test the generated debug APK on a physical Android device with
   `python scripts/install_android_debug_apk.py --exit-code-on-failure`, then
   generate the owner-held release keystore and run
   `npm --prefix ui run mobile:apk:release` if the APK path becomes the
   distribution path instead of the PWA.
6. Add a compliance/product-mode checklist before any multi-user or fee-based
   deployment.

## Bottom Line

CAS Forex is no longer blocked by the old "no live capability" posture. It has
live-capable plumbing with meaningful action-time checks, replay-proof edge
tokens, chat-routed owner commands, anti-impulse risk loosening confirmation,
and real dispatch that no longer treats missing live telemetry as empty
exposure. The next product leap is hardening deployment hygiene: secrets,
wording, Docker verification, physical phone install testing, and an explicit
product/compliance boundary.
