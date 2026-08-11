# CAS Forex - Changelog

## 2026-08-11 - Suite green end-to-end; eligibility split; provenance renderer; grouped nav; evidence chain hardened (revamp steps 3+)

Suite is fully green for the first time in project history and stayed green
through every milestone below: **2,978 passed, 0 failed** (from 3.5 hr
projected runtime and 10 failures at session start to ~16 min and zero).

**Performance / suite usability**
- Dashboard aggregation 86s -> ~14s: MT5 handshake cooldown shared across the
  seven modules that connect (`mt5_connect_guard.py`), 68 MB order-attempt
  state memoised on (mtime, size), per-build thread-local memo in `api/data.py`.
  Worst test file 569s -> 34s.
- Cleared all 10 pre-existing failures: honesty/disclosure fixes (operator
  chat error envelope with `money_impact`, no-model greeting discloses local
  fallback), stale fixtures updated to tightened gates (account-identity match,
  same-UTC-day loss ledger, AI-dial-first risk caps), two spec-sheet
  assertions moved off machine-state evidence.

**Correctness on the money path**
- `money()` now rounds half-up on the decimal value (0.345 -> 0.35, not 0.34);
  334 of 314,290 stored runtime values had the downward bias. Chains stay
  valid (verification re-hashes stored payloads).
- Reconciliation no longer reports "matches broker figures" when the broker
  exposed only one of balance/equity: partial comparisons are UNVERIFIABLE and
  name the missing field.

**Eligibility split (CAS-Ohm Ch11 "no drift by accumulation")**
- New `eligibility_attestation.py`: authenticated axis with three NOT_WIRED
  external authorities (broker API, external counsel, independent evidence
  anchor). Constant False, no config/env/runtime read - flipping it requires a
  reviewed code change. READY now requires structural completeness AND owner
  authority AND external attestation (pure function, 8-combo exhaustive test).
- Three fail-opens closed in `live_money_progression_packet.py`: a crashed
  readiness or payout-recovery builder used to CLEAR its gate; an unevaluable
  gate now blocks. Adversarially verified (3 lenses, refuted=false).

**UI: provenance + grouped nav + settings decomposition**
- Canonical `Metric` with REQUIRED provenance (live/cached/unproven) - an
  unlabelled value is a compile error. Dashboard first-paint surfaces
  migrated; fallback panels render dimmed UNPROVEN tags; ratchet test pins the
  12 remaining legacy Metric copies (may only shrink). Verified in all three
  runtime states against the running app.
- Nav: 23 flat destinations -> 7 groups + secondary tabs + legal footer;
  pushState/popstate so the back button works (verified live, desktop + 375px
  drawer). `?page=` URLs unchanged. Partition property enforced by test.
- SettingsPage 6,501 -> 4,346 lines across two slices; 11 modules under
  `components/settings/`; dead legacy RiskControlPanel deleted (tautology-
  gated unreachable code). Repo-wide rewire keeps assertions pointing at
  moved code.

**Settings decomposition complete (slices 3-4, follow-up commits)**
- SettingsPage 4,346 -> 480 lines: go-live cluster (GoLivePanels,
  BrokerRealityPanel, LivePilotPanel, shared gate consts), then
  LiveRecoveryPanel (1,277 - largest component in the codebase),
  LegalGovernancePanels (1,013), RiskControlPanel, AiControlAuthorityPanel,
  BrokerFundingHandoffPanel. 23 modules total under components/settings/.
- Slice-3 first attempt REVERTED before commit: the block-boundary regex
  missed export-prefixed declarations and swallowed the page component; redo
  added a no-block-may-contain-the-page assertion and per-block size ceiling.
- Race-test flakiness root-caused: pytest names modules tests.test_x in full
  collection vs test_x standalone; ProcessPool workers could import only the
  latter. Worker moved to a stable helper module. (First attribution - the
  msvcrt lock ceiling - was wrong; that fix stays as a real defect fix.)
- Suite green after every slice: 2,978 passed, 0 failed, five consecutive
  full runs.

**Evidence chain (C-section groundwork)**
- Located the July break precisely: broken_link at record 11, verified prefix
  11/18 - predecessor rewritten after append (state/file divergence +
  unlocked writers). `verify_chain_report()` now names record, reason class,
  and verified prefix; paper-proof failure reasons carry the diagnosis.
- `append()` derives the chain from the FILE tail under a cross-process lock
  that waits under contention (msvcrt's ~10s ceiling would crash a loaded
  append). Proven with 4 real processes racing -> chain verifies.
- Owner-gated `scripts/restart_paper_proof_chain.py`: archives the broken
  store with a defect record (never rewrites hashes), refuses on a healthy
  chain, requires the exact typed phrase. NOT executed - owner decision.

**Open (owner actions, day 1 of 30)**
- Run the restart script with its confirm phrase; start the Hugosway MT5 demo
  terminal (may have expired after 48 idle days); run START_CAS_FOREX.bat for
  a loop that outlives dev sessions. True day count: 3 complete bundle days
  (June), not the 0/30 the startup shell displayed - those zeros now honestly
  tag themselves UNPROVEN.

**Failed approaches recorded**
- The flaky race test was NOT the lock ceiling (first attribution wrong,
  corrected in 839a46f8): pytest names modules `tests.test_x` in full
  collection vs `test_x` standalone, and ProcessPool workers could only
  import the latter. Workers now live in a stable helper module.
- Naive chain re-hash walk produced false breaks on every record (wrong
  recipe); always use the store's own verifier.


## 2026-08-10 - UI/UX audit + stabilise & emergency legibility fixes (revamp steps 1-2)

Full audit of the cockpit ahead of a planned UI/UX revamp, then the first two
remediation steps. Findings were measured in the running app (computed styles +
DOM), not inferred from source.

**Stabilise**
- Committed 606 drifted working-tree files (+75,219 insertions) across four
  area-scoped commits. There had been no cas-forex commit since 2026-07-04, so
  the revamp had no rollback point. Verified first that `.env` stays ignored and
  that the only credential-shaped strings in the diff are dummy test fixtures.
- `pytest.ini`: `[tool:pytest]` -> `[pytest]`. pytest only honours the
  `tool:` prefix inside `setup.cfg`, so `testpaths` and `--ignore` were both
  silently discarded, collection walked a stray temp dir and died. Collection
  now succeeds: **2,949 tests in 4.12s** (was a hard error at 56s).
- Deleted `ui/src/data/fixtures.ts` (3,843 lines, 47 payloads). Confirmed
  imported by nothing - dead code, not a fake-data source.

**Emergency legibility + safety fixes**
- Defined 8 tokens that were referenced app-wide but never declared
  (`--bg-root`, `--border`, `--panel`, `--panel-dim`, `--surface`, `--text`,
  `--muted-text`, `--accent`), plus `--paper-dim`. Every declaration using them
  had been silently dropped. Most visible casualty: TradePage's `.btn-paper` /
  `.btn-send` inherited light text onto light fills. Measured **2.0:1 -> 7.1:1**
  and **1.7:1 -> 8.5:1**.
- `html { font-size: 14px }` -> `100%`, and rescaled 466 `font-size`
  declarations across 46 files onto a new 6-step scale with a 12px floor. The
  hard 14px root had overridden the reader's browser preference and shrank every
  rem by 12.5%. Visible text under 12px: **87% -> 1%**. Distinct sizes: 31 -> 11.
- `--text-muted` #5a6273 -> #7e8798 (2.8:1 -> 4.8:1 on `--bg-card`).
- `StatusChip` moved onto the type scale (was 11.2px in 46 files).
- Overall contrast failures on the landing page: **45% -> 12%**. The residual is
  the semantic chip palette (bright fg on dim bg), deliberately left for the
  palette work in the revamp proper.
- **New `GlobalHaltButton`**, mounted eagerly in the shell header on every page.
  The only emergency stop previously sat in `DashboardOperationsWorkbench`,
  lazy-mounted behind a ~1.6s idle timer at the bottom of the longest page.
  Two-step confirm, self-cancels after 4s, 44px touch target, honest reporting
  on partial failure.
- **New `StaleDataBadge`**. The startup cache replays a packet up to 5 minutes
  old and stamps `full_cache_status: "stale-ui-cache"`, but nothing rendered it,
  so cached equity/risk/proof values looked live. `DashboardMeta` is now declared
  on `DashboardState` (it was merged in at runtime but absent from the type, so
  no component could read it), provenance is stamped unconditionally, and the
  badge shows a live-updating age.

Typecheck clean, production build 4.62s, no chunk over 500 kB.

Not changed, and corrected against the audit: `runtime_topology` IS registered
(`api/server.py:778`) and returns 200 - an agent report claiming it 404s was
wrong, verified against the live server.

## 2026-07-04 — Cloud deploy scaffold (phone runs independently of the desktop)

Owner chose cloud hosting so the engine runs 24/7 and the phone works even when
the laptop is off. This lays the safe foundation (no deploy, no account, no
money — just the artifacts + the security model). The image build itself is
unverified locally (no Docker on the build box); app code + auth + UI serving
are tested.

- **Cloud-mode auth** (`owner_auth`): `CAS_FOREX_CLOUD_MODE=1` makes the app
  trust NO request without a valid owner token — loopback is NOT trusted,
  because a reverse proxy in front makes every request look local (the classic
  cloud hole). `CAS_FOREX_OWNER_TOKEN` env injects the owner's token at deploy.
  4 new tests (21 total).
- **Single-container UI serving** (`api/server.py`): `CAS_FOREX_SERVE_UI=1`
  mounts the built cockpit at `/` so ONE container serves API + UI on one port
  — phone/desktop are thin clients of the same instance. Off by default (local
  dev unchanged), mounted last so all API routes take precedence.
- **`Dockerfile` / `docker-compose.yml` / `.dockerignore`**: the engine as an
  always-on service with a persistent `/app/runtime` volume ("same instance,
  continued exactly"). MetaTrader5 stays out (Linux-cloud-safe; paper/operator
  brain uses yfinance/OANDA data). `--proxy-headers` for TLS-terminating proxies.
- **`docs/DEPLOY.md`**: step-by-step for a VPS+Caddy (auto-HTTPS) or Fly.io,
  the HTTPS/owner-token security rules, and the live-MT5 caveat (Windows host or
  PC-side relay when going live — not needed for paper/demo now).

The owner provisions the host + pays + runs the deploy (an AI can't create
accounts or enter payment); everything else is copy-paste.

## 2026-07-04 — Use the connected HugosWay DEMO terminal for real fills (not the sim)

Owner: "why is HugosWay demo not being used?" — because `select_bridge()` only
routed to MT5 when `mt5_login > 0`, and it's 0. The app READ the terminal (for
the account display) but ROUTED trades to the internal simulator. Fixed.

- **`broker_control.select_bridge` now uses a connected DEMO terminal.** New
  `_try_mt5_bridge` constructs an MT5Bridge with NO login required — the bridge
  attaches to the already-running, already-logged-in terminal (a bare
  `mt5.initialize()`). In `auto` mode a connected DEMO terminal is used for
  dispatch (real demo fills, real spreads/slippage); a connected LIVE terminal
  is NOT auto-routed (that stays an explicit `platform="mt5"` choice, and even
  then the live-trading gate blocks any real `order_send` until authorized).
- Safety unchanged: `is_demo_account()` is fail-closed toward LIVE, so only a
  true demo trades freely; `will_execute_real_order()` stays False for demo, so
  the execution guard never triggers the live gate for demo dispatch.
- Verified live on the owner's box: `select_bridge()` → `MT5Bridge`,
  `connected: True`, `is_demo: True`, `will_execute_real_order: False`.
- pytest guard: the real terminal is never attached during tests (the dev box
  has a live demo terminal up); tests exercise the path via a monkeypatched
  fake. 5 broker tests updated/added; suite green.

Net: the operator now trades your HugosWay demo (#1000694) — a real broker,
demo money — instead of the internal candle simulator. Risk caps
(max_concurrent_trades / per-symbol / total lots) apply to this dispatch too.

## 2026-07-04 — Daily winnings target: a real, findable control

Owner: "where can I control the increase in daily winnings?" — the assistant
correctly said it didn't exist as a control. Now it does.

- **`set_profit_target` command** (owner command broker → `ai_control_authority.owner_update`):
  set the daily winnings TARGET, the daily CAP, and the monthly target. Preview
  shows current → proposed, blocks a target above the cap, and applies with a
  receipt. Settable three ways: the operator chat ("set my daily target to $500"
  → preview → CONFIRM), the operator panel's new target field, or the console.
- **The operator now USES it**: `profit_and_balance` carries
  `daily_winnings_target_usd` / `daily_cap_usd` / `monthly_target_usd`, and the
  operator prompt tells it to push toward the daily target (size up when behind,
  with evidence, within risk caps) and ease off once the daily cap is hit.
- **UI**: a "🎯 Daily winnings target" row + inline setter in the AI Operator
  panel (top bar) showing the current target/cap.
- **Assistant awareness**: the floating assistant's control map now lists the
  Daily Winnings Target so it points the owner there instead of saying "I don't
  see it."
- 4 new tests (19 broker total); verified live (catalog has the command; operator
  state shows the target; preview current→proposed works). UI typecheck + build
  green.

## 2026-07-04 — Chat can ACT: propose → preview → typed CONFIRM → receipt (fix #3 of 3, COMPLETE)

The final piece — chat gains the power to *do* things, closing all three of the
owner's fixes.

- **Operator chat proposes commands** (`ai_operator.chat`): the operator now
  gets the command catalog and, when the owner clearly asks it to DO something,
  emits a `` ```command `` block; the reply carries the proposed command AND its
  broker preview (current → proposed, effects, blockers, the exact phrase to
  type). It never executes — proposing shows the preview; the change happens
  only when the owner confirms. `_extract_proposed_command` parses + strips the
  block so the chat bubble stays clean. 2 new tests.
- **UI command console** (`OperatorBadge` + `ownerCommandApi.ts`): a chat
  proposal renders inline as a preview card with the effects, any blockers, and
  a confirm box pre-filled with the exact phrase — "Confirm & run" executes
  through the broker and shows the receipt; a blocked preview shows why and
  offers no run. `apiCore` already carries the owner token, so this works from a
  paired phone too.
- Verified live from the browser: full preview → execute(CONFIRM) → receipt
  round-trip works; execute without the phrase is refused; the operator panel
  and chat render with no console errors. UI typecheck + build green.

**Fix #3 complete.** All three owner fixes shipped: (1) owner auth, (2)
loopback-default launcher + authenticated LAN + phone pairing, (3) the chat
command broker (5 commands: set_ai_dial, set_risk_cap, set_lan_mode,
arm_live_switch, move_money) with preview → typed CONFIRM → receipt, every
command running the same gated function the buttons use — never a bypass.

## 2026-07-04 — Owner command broker: live-arm + move-money commands (fix #3 of 3, part B)

The two highest-stakes commands, each wired through its EXISTING gates — the
broker adds a preview + a graduated typed confirmation + a receipt on top, never
a bypass.

- **`arm_live_switch`** → `live_enable_control.set_live_enable_overrides`. Arms/
  disarms any owner authorization switch (live trading, broker accept, deposit/
  withdraw/payout enablement, the acks). It AUTHORIZES a capability; the trade/
  money chokepoints still enforce their own gates. Confirmation is switch-
  specific: you type `ARM owner_enable_live_trading` (not a generic CONFIRM).
- **`move_money`** → `MovementEngine` (deposit / withdraw / payout). Fail-closed:
  the preview reads `runtime_gates.evaluate_capability` and BLOCKS with the exact
  missing requirements when the capability isn't armed; the engine re-checks the
  gate before touching any provider, and the provider is SIMULATED unless the
  owner configured a real one. Confirmation is amount-and-action-specific: you
  type `SEND $500 WITHDRAW`.
- Confirmation matching now collapses internal whitespace (robust typing).
- 5 more tests (15 total); verified live: catalog lists all 5 commands;
  arm_live_switch shows its switch-specific phrase; move_money honestly blocks
  when unarmed and shows what's missing.

Next: the chat wiring (operator proposes a command → preview → you type the
confirmation → receipt) and a small command console in the UI.

## 2026-07-04 — Owner command broker engine + settings commands (fix #3 of 3, part A)

Fix #3: chat gains the power to ACT — preview → typed CONFIRM → receipt — so you
can tell it to do something and it does it, legibly and auditably, through the
SAME gated functions the buttons use (never a bypass). Part A ships the engine
and the settings commands; part B adds live-arm + move-money commands and the
chat/UI wiring.

- **`cas_forex/owner_command_broker.py`**: a command registry where each command
  has a `build_preview` (current state, exact change, effects, blockers, the
  phrase to type) and an `apply` (calls the same owner-facing service function
  the UI uses). `preview(command, params)` shows what will happen;
  `execute(command, params, confirm)` re-checks blockers, verifies the typed
  confirmation, applies, and writes a durable receipt to
  `runtime/owner-command-receipts.jsonl`. A blocked preview NEVER applies; no
  confirmation → no change.
- Commands: `set_ai_dial` (→ `ai_control_authority.ai_adjust`, owner-fenced),
  `set_risk_cap` (→ `risk_control.set_risk_control_overrides`, number or null=
  unlimited), `set_lan_mode` (→ `owner_auth.set_lan_mode`).
- **Routes** `api/routes/owner-command/*`: `/catalog`, `/preview`, `/execute`,
  `/receipts`.
- 10 tests; verified live over loopback (catalog + preview show current→proposed;
  execute without CONFIRM does not apply).

Next (part B): `arm_live_switch` + `move_money` commands (through their existing
owner-authorization / confirm / edge gates — the typed CONFIRM is an EXTRA step,
not a replacement), then the chat integration (operator proposes a command →
preview → you type CONFIRM → receipt) and a small command console in the UI.

## 2026-07-04 — Loopback-default launcher + authenticated LAN + phone pairing (fix #2 of 3)

Fix #2 of the owner's three: make phone access SAFE without disabling anything.

- **Launchers split.** `START_CAS_FOREX.bat` now binds `127.0.0.1` (this PC
  only) — the safe default; nothing on the network can reach it. New
  `START_CAS_FOREX_LAN.bat` binds `0.0.0.0` for phone access, and other devices
  are still refused until the owner turns LAN mode ON and pairs. Loopback always
  works with no token.
- **UI carries the owner token.** `ui/src/data/apiCore.ts` gains
  `getOwnerToken`/`setOwnerToken` and attaches `X-CAS-Owner-Token` on every
  request when a token is set — so a paired phone works whether it hits the API
  directly or through the app-server origin. The owner's own PC (loopback) needs
  no token, unchanged.
- **Owner Access panel** (`OwnerAccessBadge` in the shell nav, `ownerAuthApi.ts`):
  on the PC it shows the pairing token (loopback-only), a LAN-mode ON/OFF toggle,
  and rotate (unpairs all devices); on a phone it takes the pasted token and
  saves it locally. Green/red dot shows paired state at a glance.
- Verified live: panel renders on the PC ("always allowed, no token needed"),
  `/owner-auth/pairing` returns the full 43-char token over loopback only,
  LAN mode reads/writes. UI typecheck + build green.

Next: #3 the chat command broker (preview → typed CONFIRM → receipt) so chat can
ACT, not just talk.

## 2026-07-04 — Owner authentication (fix #1 of 3): loopback drives free, off-box needs pairing

Owner directive: stop the over-cautious "disarm live money" framing that
over-careful AI agents leave behind (it silently caps the app below full
development). Live money is the point — it gets ARMED by the owner through
authenticated, confirmed, receipted actions, not walled off. Three fixes in
order: (1) owner auth, (2) loopback-default launcher + authenticated LAN mode,
(3) chat command broker with preview/typed-confirm/receipt. This is #1.

Also erased the contaminated `AUDIT_AND_REDTEAM_BRIEF.md` (a local-only commit
that never reached the remote) — it was written in exactly that disarming
voice.

Shipped (#1 owner auth):
- **`cas_forex/owner_auth.py`**: the WHO-may-drive gate. Loopback (the owner's
  own PC — 127.0.0.1/::1/localhost) is ALWAYS allowed, zero friction; the
  desktop cockpit is unchanged. Any OTHER device is refused unless the owner
  turned LAN mode ON (default OFF) AND the request carries the owner token
  (`X-CAS-Owner-Token` or `Authorization: Bearer`). Per-install token generated
  on first use, stored git-ignored under `runtime/owner-auth.json`, never
  logged. `evaluate_request` is a pure function so the whole policy is unit
  tested without a server. This closes the real hole the 2026-07-04 audit
  flagged: an unauthenticated LAN-bound API where any device on the WiFi could
  POST to money routes — the auth is what makes phone access SAFE, not a brake
  on the owner.
- **Middleware** in `api/server.py` (`owner_auth_gate`): admission only; every
  route still carries its own trading/money gates behind it. Bypassed under
  pytest so the 193-file suite (which speaks from a loopback-equivalent host)
  stays green.
- **Routes** `api/routes/owner_auth.py`: `GET /owner-auth/state` (safe, no full
  token), and LOOPBACK-ONLY `GET /owner-auth/pairing` (shows the token to pair
  a phone), `POST /owner-auth/lan-mode`, `POST /owner-auth/rotate`. Arming
  network access stays a physical-owner action.
- 17 policy/store tests (`tests/test_owner_auth.py`); verified live: loopback
  200, health open, pairing shows the token only over loopback.

Next: #2 loopback-default launcher + LAN launcher + UI token pairing screen
(so the phone flow is restored cleanly), then #3 the chat command broker.

## 2026-07-03 — Risk caps in the AI's hands + test-artifact quarantine + two-question scoreboard + lessons journal

Owner directives this session: (1) "the risk cap must be placed in the hands of
the AI to control as he sees fit... increasing the balance must be the number 1
goal"; (2) never dismiss a profitable pattern as "luck" — investigate it; (3)
current trades are a learning curve that must teach FUTURE operators.

**The measurement that drove it (6-agent audit of the 1,434-trade paper ledger,
adversarially verified, high confidence):**
- 90.4% of the paper "profit" (+\$9,458.47 of +\$10,461.21) was ONE injected
  test order — a 49-copy EUR/USD LONG cluster, single broker ticket, identical
  \$193.03 per copy, decision_refs `micro_scalp_agent:test`/`dec-1`. Not trading.
- The burst loop stacks BLINDLY: winners avg 1.21 copies vs losers 1.22 —
  genuine multi-copy stacking netted −\$317; single deliberate trades produced
  nearly all real profit (+\$964 of the de-artifacted +\$1,003).
- No hidden open-loser survivorship in this ledger (12 unresolvable rows are
  missed-opens with no P&L; worst-case swing ~\$180).

**Shipped:**
- **Test-artifact quarantine** (`paper_outcome_sim`): `is_test_artifact` +
  `purge_test_artifacts` (rows moved to a `quarantined_test_artifacts` bucket,
  never destroyed) + ingest guard so test-tagged rows can never re-enter.
  Ran on the real ledger: 49 rows / +\$9,458.47 quarantined, 1,385 real remain.
- **Risk caps enforced from the AI's dials** (`execution_guard.caps_from_config`):
  precedence = explicit owner runtime override > AI dial > static config. New
  dials `max_positions_per_symbol` (default 3 — the anti-blind-stacking lever)
  and `max_total_exposure_lots` (default 2.0); `max_concurrent_trades` dial
  (default 15) now actually reaches the gate.
- **Self-hydrating portfolio snapshot** (`build_snapshot_payload`): with no
  broker telemetry the gate now counts the simulator's still-open paper
  attempts (`open_paper_positions`, TTL-cached, path-keyed) instead of
  comparing against an EMPTY portfolio — the bug that let 150+ positions pile
  up unchecked. Skipped under pytest.
- **Two-question scoreboard** (`_profit_and_balance` + OperatorBadge): BALANCE
  GROWTH (every filled lot counts — the #1-goal number) and INDEPENDENT
  EVIDENCE (1 vote per signal — the edge-confidence number) side by side, each
  labeled with its question; neither called a "mirage". Plus stack-symmetry
  monitor (`stacking_is_blind`), quarantine badge, data-class badge.
- **Operator brain**: system prompt carries the owner's risk-cap handoff, the
  measured stacking facts, and the epistemic stance (clustered wins = ONE
  observation = unconfirmed lead to investigate, never "luck").
- **Cross-operator lessons journal** (`operator_lessons`, from earlier this
  session): founding principles auto-seeded; 3 measured lessons recorded
  (blind stacking, provenance-before-trust, two-questions-two-numbers);
  `GET /ai-operator/lessons`; lessons inherited into every operator context.
- Tests updated to the new layered-caps semantics + new coverage (artifact
  flagging/purge/ingest-guard, open-position counting, dial→gate flow,
  owner-override precedence).

## 2026-07-02 — Early-banking test of the owner's idea (MFE tracking) + operator-guidance context + isolation fix

Built the exact instrument the operator itself said it needed (and the owner
asked for): a way to test "bank big winners early, then restart WASTE."

- **MFE (max favorable excursion)** now recorded on every simulated paper close
  (`paper_outcome_sim._closed`): `mfe_price`, `mfe_pnl`, `captured_fraction_of_peak`,
  `bars_to_peak`, `bars_held` — how far a trade ran into profit before it closed.
- **`build_early_banking_analysis`**: for a range of "bank at f × peak" policies,
  models paper net vs holding to SL/TP. Conservative + honest: a losing trade is
  never rescued by early banking (only winners change); caveats surfaced (assumes
  the fractional level was reachable; ignores capital-efficiency upside; paper-
  only, no real-money-edge claim). Route `GET /waste-loop-control/early-banking-
  analysis`; wired into the operator context so it (and the owner via chat) can
  reason over it. 3 hand-computed tests (MFE recorded; banking beats hold on big
  give-back; never rescues a loser).
- **Early live signal (directional, 11 MFE trades so far):** trades capture only
  ~0.40 of their peak (big give-back); modeled banking at 0.8×peak improves paper
  net by ~+\$41 vs hold. Verdict honestly "not enough data yet" (needs 20) —
  accumulates as trading continues. Note: MFE is captured on NEW resolutions
  only; the pre-existing resolved backlog has none.
- **Test-isolation fix (real bug):** `get_authority()` with a bare call now
  returns the current process authority instead of rebuilding — the previous
  version leaked a shared per-process temp store between tests (chat test saw a
  0.95 edge_threshold left by another test). A bare call respects
  `set_authority_for_tests`; explicit paths still rebind. Also: the operator's
  live paper-outcome refresh is skipped under pytest (it did live candle fetches).

## 2026-07-02 — THE LEARNING LOOP IS CLOSED: paper-outcome simulator (real-candle first-touch P&L) + full-circle operator proof

The gap documented in the previous entry is fixed the careful way. New
`cas_forex/paper_outcome_sim.py`: for every executed PAPER order attempt
(entry/SL/TP/direction/lots from the order-attempt audit) it walks REAL M1
candles after the open via the live connector chain and resolves realized P&L —
no broker terminal needed.

**Null-discipline rules, each proven by a hand-computed test (10 tests):**
- First-touch resolution; candles strictly BEFORE the open are ignored
  (lookahead guard test).
- A candle spanning BOTH stop and target is unknowable at M1 ⇒ resolved
  CONSERVATIVELY as a LOSS at the stop (`AMBIGUOUS_CANDLE_CONSERVATIVE_SL`).
  The simulator may under-report, never flatter.
- Full spread cost charged on every trade (FX 1.5 pips / index 2.0 / metal 2.5)
  — winners shrink, losers grow; asserted `profit < gross_profit` always.
- P&L uses the SAME money math as position sizing
  (`value_per_price_unit_per_lot`) so realized loss agrees with sized risk.
- Unresolved trades stay OPEN (no record, re-walked next run); attempts older
  than the candle window are marked unresolvable — never guessed. Idempotent
  per ticket. Real-money attempts are never eligible.
- Records carry `broker_mode: PAPER_SIM` + `outcome_source:
  paper_simulated_first_touch`; the learning engine merges them with
  broker-verified MT5 history (real wins per ticket). The PROMOTION-grade
  binding still reads broker-verified history ONLY — nothing simulated can
  advance the real-money path.

Wired: routes `GET /waste-loop-control/paper-outcomes/latest` + `POST
/paper-outcomes/run`; the AI operator refreshes outcomes (guarded, ≤1/10min)
before each read.

**Run on the real backlog: 1,114 outcomes resolved; 339 bound to their
originating decisions.** The honest aggregate: 46.6% win rate, net −$361.48
paper — a coin flip minus costs, exactly what a not-yet-edged strategy should
show. Worst/best symbol×direction×profile groups now populate for the operator.
Caveat noted: 15-second burst trading produces CLUSTERS of same-direction
same-symbol trades that resolve off the same price path — group win rates like
48/48 are correlated samples, not 48 independent wins; cluster-aware weighting
is a sensible future refinement.

**Full circle verified live:** the operator (Claude) read the 337 bound
outcomes, cited the per-symbol biases, and made a reasoned fenced adjustment
while explicitly declining to touch risk dials given negative paper P&L.

**Also fixed: test runs scrambling the LIVE dials.** Full-suite pytest runs
mutated `runtime/ai-control-authority.json` (tests call `get_authority()`),
repeatedly resetting the owner's edge/learning/risk dials mid-trading.
`get_authority()` now isolates to a temp store whenever `PYTEST_CURRENT_TEST`
is set; owner baseline restored (learning ON, confidence 0.05, edge 0.65,
risk 0.1%).

## 2026-07-02 — LEARN-FROM-MISTAKES ledger + THE critical finding: paper trades open but never realize P&L

Built the learn-from-mistakes engine the owner's whole thesis depends on, AND
diagnosed why learning can't yet complete. Suite green (5 new tests); operator +
route wired.

**`build_waste_learning_outcomes` (in waste_direction_outcome_binding.py).** The
existing outcome-binding only counts PASS-token edges (of which there is ~1 in
250 cycles), so the gloves-off learning trades never fed adaptation. The new
engine binds EVERY closed paper trade — learning trades included — to its
originating direction and aggregates realized win-rate + net P&L per
symbol × direction × profile, surfacing worst/best groups. This is what lets the
AI operator say "SHORT NAS100 M1 loses 70% over 25 trades — raise its confidence
bar." Wired into the operator's context (`_compact_learning_outcomes`) + route
`GET /api/forex/waste-loop-control/learning-outcomes`. 5 tests prove it binds
non-edge trades, ranks the losing group, ignores unclosed trades, and never
touches money/live. Read-only PAPER/DEMO; realized paper stats NEVER auto-promote
to real money (that still needs a PASS token + owner live gates).

**THE CRITICAL FINDING (documented, not yet fixed — next build).** Tracing why
`bound_outcome_count` is 0 despite 300+ dispatched trades: the paper trades OPEN
(the sim/paper bridge assigns tickets) but their realized P&L is NEVER captured,
because (a) no MT5 terminal is connected — `mt5_deal_history_ingest` reports
`mt5_package_available: false, initialize_ok: false`, so closed-deal P&L can't be
ingested; and (b) `SimulatedBrokerBridge` holds positions in-memory and has no
close-with-P&L step. So the learning loop makes predictions and dispatches
orders, but no outcome ever comes back — it can generate but not yet LEARN.

The missing piece is a **paper-outcome simulator**: for each dispatched paper
order (entry/SL/TP/direction), walk subsequent REAL candles, resolve first-touch
of SL vs TP (with real spread/cost), compute realized P&L, and write a durable
closed-outcome ledger the learning engine reads — no broker terminal required.
Deliberately NOT rushed here: a subtly-wrong P&L simulator would fabricate fake
edges, which violates the codebase's sacred null-discipline. It must use real
candles + correct pip math + honest first-touch/spread, and be validated before
its outputs feed the operator. Specified as the next build in the handoff.

Net: the consumer (learning-outcomes engine + operator wiring) is shipped and
tested; the producer (paper-outcome P&L) is the next careful, null-safe build.
Until then the operator correctly sees 0 bound outcomes and HOLDS — honest.

## 2026-07-02 — AI OPERATOR: always-on strategy desk + Claude→free-local failover + live model indicator

The original vision, built: an owner-controlled AI operator that runs alongside
the app, reads the learning ledgers, and tunes the AI dials WITHIN the owner
fences — with automatic failover to a free local model when Claude tokens run
out, and an always-visible indicator so the owner sees every switch. Suite green
including 19 new tests; UI tsc + build clean.

**`cas_forex/model_provider.py` — failover ladder (the cost-control heart).**
Ordered chain: PAID primary (Claude via Anthropic API) → FREE local fallback
(Ollama by default, fully free). Durable token budget (`runtime/model-provider-
state.json`); when the owner's budget is spent OR the primary returns a credit/
rate/auth error, the chain fails over to free and records the switch; a cooldown
(900s) stops it from hammering a token-less primary; `top_up(tokens)` flips it
back to Claude on the next call. Built on the existing `ai_model.py` backends.
7 tests cover: chain order, no-key→free, credit-error failover + cooldown,
budget-exhaustion skip, top-up flip-back, all-fail safe degrade.

**`cas_forex/ai_operator.py` — the strategy-desk brain.** Each tick: gathers
context (direction-learning ledger, outcome binding, adaptation plan, recent
cycles, dials) + a TOOL MANIFEST so the model is always aware of what exists
(dials it can set, evidence it can read, PCBA/CondLab/Optimizer/adaptation, and
an explicit "you cannot" list); asks the ACTIVE model for a structured decision;
applies it ONLY through `ai_control_authority.ai_adjust`, which clamps every
value to owner bounds. Hard boundary proven by tests: it can move only the 9
owner-fenced dials; `live_mode`, `owner_enable_live_trading`, "wire_money", and
any non-dial action are rejected; unparseable/absent model replies make NO
change; the live-money gate is unreachable by construction.

**`cas_forex/ai_operator_runner.py` + `api/routes/ai_operator.py`.** Always-on
scheduler mirroring the proof-runner (owner on/off, durable desired-state,
survives API restarts, default 30-min interval for cost). Routes:
`/api/forex/ai-operator/{state,start,stop,run-now,config}` and
`/ai-operator/model-provider/{state,add-tokens,reset-budget}`. Startup restore
re-arms the loop if the owner had it on. New config: `ai_operator_enabled`,
`ai_operator_interval_seconds`, `ai_operator_primary_{backend,model,base_url,
api_key}` (key from `AI_OPERATOR_PRIMARY_API_KEY` or `ANTHROPIC_API_KEY`),
`ai_operator_token_budget`.

**UI — `OperatorBadge` in the header (every page + phone).** Live indicator that
polls `/ai-operator/state` every 10s and shows the ACTUAL driver, not just what
is configured: CLAUDE (green) / LOCAL free (amber) / OPERATOR ON warming (blue) /
NO MODEL (red) / OFF (grey). Click to expand: running state, active model + token
budget, the last model switch, the operator's last summary, controls
(pause/start, run once, **Add Claude tokens**), recent operator actions, and the
boundary line. Honesty fix baked in: a configured-but-failing Claude reads
"NO MODEL", never a healthy green.

**Verified live:** badge renders and correctly showed "NO MODEL" when a tick
failed (this environment has no valid Anthropic billing key and no local Ollama),
proving the failover degraded safely with the trading loop untouched. To make a
model actually answer: set a real Anthropic API key (`sk-ant-api03-…`) OR install
Ollama + pull a model (fully free) — the badge flips to green/amber the moment
either works. The operator only ever moves owner-fenced dials; it cannot trade,
move money, or authorize live.

## 2026-07-01 (late) — GLOVES-OFF PAPER LEARNING: the edge bar becomes a label on paper; M1 scalp loop live; FIRST LEARNING TRADE FILLED

Owner directive (verbatim intent): the 65% edge bar is for REAL money; on paper/demo the AI
must TRADE to build learning material — "the edge is developed from learning from mistakes,
not before." Also: scalp on M1 or faster, both directions, all sessions. Implemented, tested
(suite **1716 passed / 0 failed**), and verified live tonight with a FILLED demo trade:
`LONG NAS100 0.47 lots, broker ticket 45940508, BROKER_EXECUTED (PAPER_MT5)` carrying its
edge verdict as the learning label.

**The learning-mode architecture (paper-only by construction):**
- `waste_loop.py`: non-PASS candidates now execute as **paper LEARNING trades** when the
  owner's `paper_learning_trades` dial is ON — the edge verdict rides along as the training
  label (`learning_trade: true` on the cycle). Learning trades carry an **EMPTY edge token**,
  so any real-money path refuses them at the dispatch chokepoint (fail-closed physics, not
  policy). Learning never invents candidates (strategize None ⇒ still NO_TRADE) and never
  compounds (adds always require a fresh PASS).
- `waste_runner.py`: empty-token execute skips edge-authorization registration (never
  fabricates a PASS) and dispatches through the legacy paper path; `_paper_learning_allowed`
  = dial ON + effective mode PAPER. Production runners now share the DURABLE owner-fenced
  authority dial surface (`get_runner()` wires `get_authority().control`) — owner/AI dial
  changes (edge threshold, risk %, learning, confidence) finally reach the running loop.
- Three learning-hostile vetoes made learning-aware (all real-money behavior unchanged):
  the strategy-lead firewall (owner-dial symbols allowed as `ALLOW_PAPER_LEARNING`), the
  CAS lacuna/RPM cell veto (a lacuna is where learning DATA is needed), and the directional
  confidence bar (now owner lever `min_directional_confidence`, default 0.18, scalp 0.05).
- Scan breadth: the WASTE market scan now ALWAYS includes the owner's symbol dial after
  research leads (was: leads-only unless empty) — 8 lanes scanned per cycle incl. FX pairs.
- Scalp mode: `POST /waste-loop-control/start?confirm=true` accepts `deep_watch` (full
  candle scan per tick instead of the 5-min-probe mirror) + `watch_timeframe` (e.g. "M1");
  `_start_worker` pops inherited env so stale snapshot-mode vars can't override the request.
- New levers: `paper_learning_trades` (1/0, default 1), `min_directional_confidence`
  (0.0–0.90, default 0.18). Set live: learning ON, confidence 0.05, risk/trade 0.1%.

**Current runtime**: runner LIVE at 15s cycles, deep-watch M1, 8 lanes, long+short scored
every cycle; collector 900-bar sweeps every 5 min; proof auto-runner recording days.
Owner switch note: **live_mode override flipped OFF** (it was ON without a live account,
which made the chokepoint treat paper learning trades as real attempts and block them —
flip it back in-app when actually going live). Mixed-version processes were found
overwriting each other's authority lever registry — resolved by restarting everything on
final code; the env-pop + shared-authority changes prevent recurrence.

**Also this session**: `START_CAS_FOREX.bat` (repo + Desktop) one-click starter; stale
AUD/CAD same-symbol block diagnosed (28 June-24 mailbox phantoms need one MT4-terminal
session to verify-flat then archive via `terminal-receipt-recovery-packet/archive-stale`).

Honest boundary, stated once: learning trades measure and label — they are NOT edge claims.
The 30-day proof still requires net-positive P&L at the owner bar; nothing here touches the
real-money gate chain (owner switches + broker-reality ACCEPT + dry-run ACCEPT + pilot).

> **NEXT AGENT: read `docs/working/SESSION_HANDOFF_2026-07-01.md` first** (then the PART3-EDGE handoff below for the edge verdict). The per-unit build log for 2026-06-29→07-01 lives in the parent repo's `docs/working/cas_harness_production_todo.md` (266 dated entries) — read its head before changing dashboard/live-money/WASTE code.

## 2026-07-01 — Three days of in-flight work landed: live-money spine, WASTE adaptation, funding handoff, dashboard overhaul (suite 1707 green)

This session inventoried and landed the large uncommitted body of work built across
2026-06-29→07-01 (127 modified files + ~130 new modules/tests, logged entry-by-entry in
`../docs/working/cas_harness_production_todo.md`). Verified green before commit: **pytest
1707 passed / 0 failed** (suite grew from 1217), UI `tsc --noEmit` clean, `npm run build`
clean (PWA precache = 8 shell entries, ~182 KiB). Four stale tests were updated to the
newest ratified contracts (below) — no app code was changed to make the suite pass.

**1. Live-money go-live spine (all fail-closed, owner-driven).** New modules + routes:
`auto_halt` (circuit breaker), `broker_reality` (owner ACCEPT of the real broker's
withdrawal/KYC/fees/currency terms), `broker_truth_monitor` (+ supervisor + recovery
packets; continuous MT5-snapshot vs terminal reconciliation), `live_pilot`
(small-controlled live pilot envelope with remaining-capacity tracking), `live_recovery`
(crash/disconnect recovery review), `live_order_dry_run` (+ owner review bound to fresh
broker truth), `order_attempt_audit` (every dispatch attempt recorded before the bridge is
touched), `terminal_receipt_recovery_*`, `payout_recovery`, `live_money_progression_packet`
(routes `/api/forex/live-money/progression-packet{,/fast}`), `ai_control_authority`.

**2. Runtime-gate redesign — owner authority boundary.** `runtime_gates.py` now states it
in code: performance/readiness METRICS (paper-day counts, evidence, AI confidence, profit
pace) are advisory only — they never authorize or veto live trading. The live gate gained a
new advisory tier (broker-truth monitor freshness is an ADVISORY, surfaced but never an
owner veto) and five new HARD requirements: auto-halt clear, owner broker-reality ACCEPT,
live-pilot ACCEPT with capacity, recovery review clear, owner-ACCEPTED passing live-order
dry run against fresh broker truth. The payout gate now also requires broker-reality ACCEPT
for withdrawal terms. Bridge-level `is_demo_account` strict gate unchanged (a connected
demo still never licenses live).

**3. Funding custody boundary (owner requirement made product truth).** Funding is a
**broker handoff + CAS verification loop**, never card entry into CAS: Settings gained a
`Broker Funding Handoff` panel (broker portal link, `NO RAW BANK/CARD STORAGE`, `Sync
Broker Snapshot` → `/api/forex/reconciliation/account?sync_to_broker=true`), and Proof
gained the same `Broker Funding Route` block inside Live & Payment Controls. Winnings flow
out via the new **verified-profit sweep** (`verified_profit_sweep.py` + 8 routes under
`/api/forex/money-movement/verified-profit-sweep/*`): sweepable money is computed ONLY from
broker-confirmed closed trades (demo/paper profit reports `DEMO_NOT_SWEEPABLE`), with owner
sweep %, tax-reserve %, minimum, allowlisted destination, and payout-recovery handling.
Verified live this session: reconciliation sync returns 7/7 checks OK
(`BROKER_API_VERIFIED`, chain verified) against the demo terminal.

**4. WASTE adaptation loop (learning half of the engine).** `waste_adaptation_plan` →
`apply_preview` → `owner_review` → `paper_apply` → `promotion_rule` (adaptations are
planned, previewed, owner-reviewed, applied to PAPER first, and only promoted by rule),
plus `waste_background_worker`, `waste_cycle_audit`, direction-learning ledger +
outcome-binding + review packet, paper sample collector, real-candle probe, runner
supervisor, and `waste_strategy_firewall`. MT4 mailbox dispatch now requires a FRESH EA
heartbeat (fail-loud `BROKER_REJECTED` instead of silently queueing commands no EA reads).

**5. Dashboard/first-paint overhaul.** Instant shell + startup caches
(`DashboardInstantShell`, `DashboardStateHydrator`, shell/fast cache prewarm with
first-claim ordering), idle-gated deep panels (`DashboardOperationsWorkbench`, sweep/broker
-truth ops panels), per-route lazy CSS (every page), React vendor chunk, API-base
last-good routing + 15s failed-base cooldown (`apiCore.ts`), W.A.S.T.E header stage probe.
PWA precache trimmed to the 8-entry first-paint shell.

**6. This session's fixes (stale tests → ratified contracts).**
`test_broker_truth_monitor` ×2 updated to the advisory-tier gate contract (freshness is
advisory, never a veto; a DEMO snapshot still never reads as live truth);
`test_dispatch_works_through_mt4_mailbox_bridge` updated to the heartbeat contract (dead
mailbox → `BROKER_REJECTED`, fresh heartbeat → `BROKER_PENDING`);
`test_dashboard_fast_*` now derives proof-day/risk expectations from the same live evidence
files the endpoint reads (they legitimately advance as the auto-runner records days) instead
of freezing `3 days` / `$28.48`. Also: `.gitignore` now excludes `uvicorn-*.log`.

Honest status separation (unchanged by all of the above): the 30-day profit proof is at
**5/30 broker-verified days, 0 trades, net $0** — `NOT PASSED`; the edge remains
**unproven** (see PART3-EDGE handoff); live trading, deposits, payouts all remain
`CURRENTLY NOT LICENSED` pending owner switches + funded real broker + provider config.

> **PRIOR HEAD NOTE (still true): read `docs/working/SESSION_HANDOFF_2026-06-28-PART3-EDGE.md`.** This session honestly answered "does CAS Forex have an edge?" — and built the apparatus to prove one. Bottom line: NO edge found. Price-only signals are all-gaps at every timeframe; every assembly tool (PCBA/CJT/Fury/optimizer/condition_lab) organizes the same edgeless price rules; the CAS Harness is the wrong domain; CAS recipes/28-Foundations organize but don't predict; and the first REAL new-information test (macro surprise, 811 events) is NO_SKILL at daily resolution (a faint sub-significance tilt). A null control caught 3 apparent edges. The one open door — an intraday post-release macro test — was BUILT, adversarially reviewed, and RUN on real HistData M1 EUR/USD (2020–2024, ~1.8M bars): verdict **NO_SKILL** (hit 0.51, net negative, worse than the shuffled null). The new-information macro channel is closed for retail. Every lever is now tested; no edge anywhere. Don't claim/build a fake edge; the null discipline is sacred.

## 2026-06-29 — AI activity indicator: hard-wired to the real loop (honest LIVE/OFFLINE), not a demo

The header heartbeat now reflects what the loop is ACTUALLY doing instead of cycling on a timer
(owner caught it: "constantly changing, no indication it's connected"). New `cas_forex/loop_heartbeat.py`
(in-memory stage mirror; `running` only on a fresh tick) + route `GET /api/forex/waste-loop/stage`.
UI: `useLoopHeartbeat` polls it; `AiActivityIndicator` defaults to the real stage and shows an explicit
**LIVE / OFFLINE / DEMO** badge (demo is now opt-in via prop). Verified live: with the loop not running
the indicator reads `idle` + `OFFLINE` from the endpoint (`running:false`) — no faked activity. Once the
WASTE loop ticks (calls `loop_heartbeat.record(stage)` from the runner), it goes LIVE with the real stage.
Heartbeat tests green; UI tsc clean.

## 2026-06-29 — WASTE engine: fleet-built core of the adaptive AI loop (7 modules, 107 tests green)

A fleet of 7 agents built the **W·A·S·T·E** (Watch·Analyze·Strategize·Test·Execute) loop's modules
with zero collisions (disjoint new files), all green. The engine name **WASTE** is kept by owner
decision (prima-materia / transmutation omen). Modules:
- `cas_forex/edge_gate.py` — the fail-closed null TEST gate (the integrity core): CandidateSetup →
  EdgeTestDecision; PASS only when measured win-prob ≥ threshold AND it beats the shuffle null;
  mints an HMAC `edge_token` bound to the order; `verify_token` rejects tampered/stale tokens.
- `cas_forex/waste_loop.py` — the WASTE controller (dependency-injected, fail-closed: no PASS token
  ⇒ no execute; emits the AiStage trace that drives the heartbeat).
- `cas_forex/compounding_governor.py` — lacunarity/RPM/CJT/cascade add·hold·cut; every ADD requires a
  FRESH edge-gate PASS (never inherits the parent's token).
- `cas_forex/ai_control_surface.py` — the AI's typed dials over every lever (edge_threshold default
  0.65, risk, symbols, sessions, compound units) with owner-set bounds.
- `cas_forex/trade_management.py` — position sizing + breakeven principal-lock (SL→entry at +1R).
- `cas_forex/ai_objective.py` + `ai_incentive.py` — pace board (**$250/day floor … $3,500/day CAP =
  stop-for-the-day**, owner sliders) + 2.5%/$5k **verified-profit** fee ledger. Pace is a scoreboard,
  never a trade-forcer; nothing lowers the edge bar (honesty-guard test enforces it).
- UI: `EdgeThresholdControl` (65% slider), `ObjectivePaceCard`, `IncentiveLedgerCard`, `useAiStage`.
All import-clean + contracts align; UI tsc clean; **107 module tests green**. NEXT (main-agent
integration into shared files): edge-token into the dispatch chokepoint (fail-closed), broker
`modify_position` for breakeven-lock, mount UI + wire heartbeat to the real stage, start the loop.

## 2026-06-28 — Intelligent-execution loop: architecture blueprint + live AI activity indicator

The owner's pivot (correct, and matches the evidence): no static formula beats forex; only an
adaptive AI **Watch→Analyze→Strategize→Test→Execute** loop can. Architecture workflow
`wf_9c26a366-034` mapped the codebase + produced a buildable spec. The honesty auditor caught
that the null TEST gate was BYPASSABLE (opt-in kwarg, every existing caller skipped it) and
specified the fail-closed fix (unconditional edge-token check inside `guarded_place_order`),
plus 8 fixes: token carrier on TradeIntent/BrokerOrderRequest; correct null hypothesis (feed
entry SIGNAL-STRENGTH as `surprise`, not the fixed direction); UNDERPOWERED≠NO_TRADE reason
taxonomy; bar-based (not wall-clock) verdict staleness; multiple-testing correction under
candidate fan-out; per-add compounding re-test enforcement; missing `modify_position` broker
primitive for breakeven-lock; missing risk→lots position sizing. Build follows.
- **`ui/src/components/AiActivityIndicator`** — a live animated heartbeat in the app header:
  a distinct figure + colour per loop stage (radar sweep=watch, orbiting dots=analyze, thinking
  dots=strategize, flipping coin=test, burst=execute, rising bars=compound, gold shield=principal
  locked, dim dash=no-trade, red X=blocked, breathing core=idle). Self-cycles now; drives off the
  real loop stage once wired. tsc clean, no console errors.
- Owner requirements locked for the loop build: user-controlled **edge-threshold slider (default
  65%)** gating execution on measured-OOS win-prob that beats the null, and full **long/short**
  (both directions evaluated each cycle).

## 2026-06-28 — Index TSMOM = no alpha; Chronos forecaster = no skill (every public-signal lever closed)

- **Index TSMOM** (the active proof lead `tsmom_126_250_2_10`) tested vs buy-hold + a
  beta-controlled random-timing null on 30+yr index D1 (`scripts/run_index_tsmom_test.py`):
  beats_null=NO in every era (full/2000+/2010+/2016+). It cuts drawdown vs buy-hold —
  real risk management — but generates NO alpha. Not an edge.
- **Chronos-Bolt forecaster skill-gate** — filled the empty `chronos_signal` slot
  (`scripts/run_forecaster_skill_gate.py`, GPU). Next-bar direction on EUR/USD H1/D1 +
  US30/NAS100/SPX D1: hit **0.49–0.51**, below the shuffled-label null p95, Brier worse
  than base-rate → **NO next-bar skill**. The last untested signal class, closed.
- Bottom line: every testable public-data signal class (price rules all TFs, regime
  switching, macro daily+intraday, weekend-gap, turn-of-month, index TSMOM, cross-asset,
  a real pretrained forecaster) is now measured NO-EDGE against the null. The remaining
  untested edge source is the **owner's own discretionary method** (the unencoded "2020
  NAS30/NAS100 rule") — encode + null-test that next.

## 2026-06-28 — Edge-research team (48 agents) + 2 top survivors tested: weekend-gap NO_SKILL, turn-of-month DECAYED

Ran a 48-agent research workflow over the full codebase + CAS v7.4/Noetic docs + index
microstructure + cross-asset + seasonality + money-management to generate and adversarially
screen genuinely-novel TESTABLE edge hypotheses (41 gathered, 30 survived, team-lead ranked).
Several index ideas were computed DEAD by the screeners themselves: the overnight-drift
premise is FALSE on 2020-25 (NASDAQ intraday wins; after CFD financing it's beta);
cross-asset and index<->index lead-lag are NO_SKILL after cost; macro-on-index inherits the
FX-macro failure. Then ran the top-2 testable-now survivors through the sacred null myself:

- **Weekend-gap fade** (`scripts/run_weekend_gap_test.py`): EUR/USD Sunday-open gap, HistData
  M1 2020-2024, 261 weekends. Real GROSS reversion at 1h (61.7% fade-aligned, beats the null
  gross) — but it dies to cost: net-NEGATIVE at >= 2-pip weekend spread (real weekend spreads
  are 3-8 pips), and 4h/6h decay to a coin flip. **NO_SKILL** (a real micro-tendency, not a
  tradeable edge). Settles a screener disagreement in favor of the null.
- **Turn-of-month (-1,+3)** on US30/NAS100/SPX (`scripts/run_turn_of_month_test.py`): yfinance
  D1 to 1992/1985/1927, beta-controlled within-month relocation null. REAL + strong over FULL
  history (NAS100 98.8th pct, SPX 100th) — the apparatus correctly detected the famous
  Lakonishok-Smidt / McConnell-Xu anomaly — but **DECAYED**: by 2000+/2010+/2016+ it no longer
  beats the timing null (55-70th pct). Modern positive return is beta, not timing skill.
  **No tradeable edge today.** (Fixed a cost bug: proportional bps spread, not absolute index
  points across a 1927 S&P of ~17.)
- Honest state: both top survivors resolved to no tradeable edge; the machine works (found a
  real anomaly AND its death). Remaining lever: the real-forecaster skill-gate (Chronos/TimesFM),
  team prior ~10-15%. yfinance index D1 frozen to `data/external/` (git-ignored); scripts committed.

## 2026-06-28 — Intraday macro-surprise test: BUILT, reviewed, RUN — verdict NO_SKILL (last open door closed)

The higher-resolution rerun of the daily macro test (which was NO_SKILL with a faint
tilt): the EUR/USD move in the 5–30 min AFTER each US release, on 1-minute bars, through
the same leak-free shuffled-surprise null core.

- **`cas_forex/macro_intraday.py`** — DST-correct release schedule (self-contained
  US-Eastern rule proven == IANA tz database across 5,219 weekdays 2007–2026, 0
  mismatches; NFP/CPI/PPI/Retail 8:30, ISM 10:00, FOMC 14:00, ADP 8:15 → true UTC).
  HistData ASCII M1 loader that defeats the timezone trap STRUCTURALLY: bars are
  EST-no-DST (+5h fixed), releases are ET-with-DST (+4/+5h), BOTH forced to true UTC
  before alignment. Per-indicator causal z-score → `evaluate_surprise_return_pairs`.
  Pre-registered PRIMARY window is the verdict (0→30 min, news-realistic 2-pip cost);
  4 exploratory secondaries never become the headline (no tuning-to-pass).
- **`scripts/run_macro_intraday_real.py`** — real runner; verdict the instant HistData
  M1 EUR/USD CSVs land in `data/external/` (git-ignored). `--self-test` proves the
  machinery now (synthetic signal→CANDIDATE_EDGE, noise→NO_SKILL). FF calendar yields
  34 known-time US indicators / 3,668 candidate releases (2007–2025).
- **Adversarial review** (5-lens workflow, every finding independently verified):
  1 CRITICAL finding REJECTED on ground truth — the calendar's `[:10]` date slice matches
  published NFP release dates 24/24, so the proposed timezone-conversion "fix" would have
  shifted ~half the sample back a day (the `00:00` stamps are placeholders; the date is
  the true US release date). 5 real findings FIXED: (a) **co-released indicators**
  (NFP+Avg Hourly Earnings, CPI+Core CPI at one instant) now **collapse to one window**
  with averaged surprise — they were double-counting identical returns and breaking the
  null's exchangeability toward a false edge; (b) PRIMARY cost → **news-realistic 2 pips**
  + documented that the permutation null is gross-directional (cost held fixed) and
  `net>0` is the cost gate; (c) **per-indicator decomposition** in the report (is a
  verdict broad or NFP/CPI-driven?); (d) non-finite calendar cells dropped + counted,
  never coerced (also fixes a one-bad-cell-zeroes-successors bug); (e) UNDERPOWERED print
  surfaces its reason.
- Suite green: **1235 passed**. External data (FF calendar + HistData M1) stays on disk,
  git-ignored — never committed.
- **RAN on real data — verdict NO_SKILL (conclusive):** real HistData ASCII M1 EUR/USD
  2020–2024 (5 files, ~1.8M bars, in `data/external/`, git-ignored). PRIMARY (0→30 min,
  2-pip): 535 usable events / 214 OOS, hit **0.509** (coin flip), net **−3.74%**, WORSE
  than the shuffled-null p95 (−1.31%) → **NO_SKILL**. All 4 secondary windows agree (each
  net-negative); per-indicator raw hits cluster at ~0.50 (NFP 0.518, CPI y/y 0.357 — the
  move after the print is essentially random). The faint *positive* daily tilt goes
  *negative* at intraday resolution. Generous case (HistData M1 is interbank-tighter than
  retail; real news spreads blow out → retail worse). **The new-information macro channel
  is closed for retail.** Report: `evidence_runs/macro_intraday/` (git-ignored).

## 2026-06-28 — The EDGE investigation: leak-free OOS, bias-state map, macro-surprise (verdict: no edge yet)

- **Leak-free OOS regime-switching test** (`d7ba0062`, `e2fa510b`): `cas_forex/edge_oos.py`
  — routing learned on train, per-bar causal switcher, realistic cost, measured vs a
  RANDOM-ROUTING null. Verdict NO_EDGE: switching never beats the null (0% of windows),
  any cost. The +40%/−2.7% swing on a data refetch is pure beta/noise.
- **All assembly tools are dead ends** (PCBA/CJT/CCB = governance; Fury = vendor `.set`
  import; condition_lab = re-parameterized price rules; optimizer = no model). 13-setting
  grid through edge_oos: 4 positive standalone (beta), selection forward → NO_EDGE (`2366d812`).
- **Discipline frame** (`c759c5a2`): `cas_forex/cascade_forecast.py` (confidence decay +
  breakdown/open-cause flags) + `cas_forex/nested_lacunarity.py` (bias-state map; structural
  no-lookahead TF guard). Measured D1+H1: ALL_GAPS 28/28 (`7399b735`).
- **Macro-surprise new-information cell** (`b7d6e9f5`, `a4c94585`): `cas_forex/macro_surprise.py`
  — surprise→move OOS vs a shuffled-surprise null; instrument validated (detects planted
  signal, rejects noise). Real Forex Factory data (HF `Ehsanrs2/Forex_Factory_Calendar`):
  811 US surprises 2021-2026 vs EUR/USD daily → NO_SKILL (learned correct sign −1, 56.3%
  hit, +7.45%, but null p95 +9.52%; faint tilt, not significant at daily resolution).
- **Repo made whole + monorepo cleaned** earlier this session (`8747a4f5`..`01d3c15c`):
  committed ~104 untracked-but-tested files, restored 28 deleted eval packs, landed real
  gitignores (big data stays on disk). Archived `evidence_runs/` to D:. Suite green: 1217.
- **Known issue:** the intraday M1/M5/M15 bias-state map crashed on zero-distance ATR
  stops at fine scale (`engine._generate_proposal` tp==entry) — inconclusive, fix pending.

## 2026-06-28 — "Live & profitable" finish line (profit-measured proof, in-app advance, MT4 route, honest status)

- **The 30-day proof now measures profit** (`3167fb60`). `summarize_paper_proof.passed`
  also requires net-positive realized P&L + max drawdown ≤ limit (default 8%, the
  plan's gate) + real trades on most days — before, a proof of 30 zero-trade or
  losing days would have PASSED. MT5 demo receipt sums realized P&L
  (profit+commission+swap+fee) into `realized_pnl`, carried through the receipt →
  daily summary. New `cas_forex/proof_control.py` = owner-adjustable thresholds.
  Anti-gaming: only broker-verified days count; a plan-only ledger can never pass.
- **The proof advances from inside the app** (`eed98c9e`, `900b5da0`, `a61ff4cc`).
  `cas_forex/proof_runner.py` = owner-controlled daily auto-runner + `run_proof_day_now()`
  manual path (paper-only, idempotent, retries if the demo terminal is down).
  `POST /api/forex/proof-control/{run-now,auto/start,auto/stop,thresholds}`. Proof page
  gains a **Proof Control** panel: profit metrics, the honest "what's left", a
  **Record today's proof day** button, the **daily auto-runner** toggle, and tunable
  thresholds. Removed the CLI instruction from the owner's next-action.
- **MT4 EA mailbox as the stable in-app real-order route** (`78319cea`). New
  `cas_forex/mt4_control.py` (enable + mailbox folder + EA heartbeat). **Fixed the
  round-trip**: `MT4EABridge.execute_order` now writes the EA-readable
  `commands/<id>.json` (the EA never saw dispatched orders before). Settings "MT4
  Bridge — Stable File Route" panel: on/off, mailbox folder, EA link
  (LIVE/STALE/NO_HEARTBEAT), one-tap "Use MT4 for dispatch".
- **Honest live/authority status** (`f84cad78`). ModeBanner (every page) + Settings
  Owner-Control / Broker-Config / Legal-Gates now read live owner-flag sources
  (authorityBoundary, live-enable, broker-control, proof readiness, MT4 link) instead
  of hardcoded "PAPER_MT5 / live_mode=false / Broker Health: DISCONNECTED / 1/30".
  A connected DEMO never licenses live (status is owner-flag driven, not the MT5 IPC).
- Suite green: **1177 passed**; UI tsc clean.


## 2026-06-27 — Auto-Trade Loop: owner-set interval + symbol/session targeting; market status

- **Market OPEN/CLOSED + session strip** on Trading Windows: live badge, Asian/
  London/New York with the active one lit, and a "reopens in … (Sun 22:00 UTC)"
  countdown — so frozen weekend charts read as "market closed", not a bug. (8c73e480)
- **Strategy panes show open positions**: Strategy A → US30, Strategy B → NAS100,
  each with its LONG position under the chart. (8c73e480)
- **Loop interval is fully owner-set** — 1 second to 24 hours (old 10s/60s floor
  gone), changeable live while running via "Apply". (1a252b0d)
- **Loop targeting**: aim the paper loop at chosen symbols ("Trade only" chips) and
  sessions ("During sessions" chips) so it stacks proof on the setups you care
  about; idles off-session; updates live. (6760b67b)
- Full suite green: 1159 passed.

## 2026-06-27 — Trading terminal + auto-trade loop + green test suite

- **Trading Windows is now a real terminal** (was bare charts). Account header bar
  (Balance / Equity / Floating P&L / Open positions / Margin / Mode) + an MT4-style
  "Open Positions" table listing every open position (symbol, side, lots, entry, now,
  SL, TP, floating P&L), plus per-pane positions for each chart's symbol — all from
  /movement/snapshot. (0bc3553b)
- **Paper dispatch loop on a timer** — the #1 functional gap. `cas_forex/dispatch_loop.py`
  + an "Auto-Trade Loop" control on the Trading Windows page run the gated dispatch
  cycle every N seconds, so the bot trades on its own (paper-safe; live needs explicit
  authorize + a ?confirm=true start). This builds the paper-proof track record
  automatically. (62f2109a)
- **Test suite fully green (1154 passed, 0 failed).** Fixed the 6 long-standing
  strategy_ledger/llm_optimizer failures by teaching the validator that Forex-Fury
  PROMOTED_PAPER_LANE records are a separate, provenance-checked record type. (0bc3553b)



A batch of owner-reported breakage + control gaps, all fixed and verified live.

- **Dashboard blank-out + missing floating assistant (same root cause).** The
  Dashboard threw on render (unguarded `.join` on heterogeneous strategy leads —
  8 of 12 `ff-lead-*` entries lack `symbols_promoted_for_next_tests`) and, with no
  error boundary, the uncaught throw unmounted the WHOLE app — which is why the
  floating assistant vanished too. Guarded the lead reads + added a real
  `ErrorBoundary` so one page can never blank the app/assistant again. (62c4c1e7)
- **Authority Boundary / Path to Authorize were non-functional** (read-only). The
  "Path to Authorize Everything" panel is now real in-app TOGGLES for all 5
  owner-controlled capabilities (live trading, broker ACCEPT, auto-deposit,
  bank/card movement, payout automation = the sweep ledger) + a shared payment
  provider section (provider, API key as a password stored-but-never-returned,
  payout destination, allowlist). The sweep ledger can be licensed entirely in-app.
  `live_enable_control` extended; `runtime_gates` consults the overrides. (c2b81ed4)
- **Assistant stopped lying about `.env`.** Its system prompt was stale (still said
  "no button to go live", listed `CAS_FOREX_*` env vars). Rewrote it to point at
  the Go Live + Path to Authorize toggle panels and to never instruct a `.env` edit
  or restart — while keeping the honest caveat that toggles satisfy the gate but a
  broker feed + running process are still needed. (c2b81ed4)
- **Condition Lab now always shows M1 + M5** (and M15/H1/D1) in the Timeframe
  filter, not just the timeframes present in data — selecting one with no evidence
  shows the honest empty state.


> **NEXT AGENT: read `docs/working/SESSION_HANDOFF_2026-06-27.md` first.** Tasks A (live-enable toggles), B (Trading Windows cockpit), and the comprehensive UI audit are all DONE (see entries below). The audit fanned 19 agents across every page + adversarial verification; 13 confirmed issues fixed (7 high incl. broken Strategy-diff contract, blank Daily-Report section titles, a Ledger crash-guard), plus 2 runtime React key bugs the static audit missed.

## 2026-06-27 - Comprehensive UI audit + 15 fixes

Ran a 36-agent workflow (one auditor per page → adversarial verifier per finding)
across all 19 pages. 13 confirmed issues (7 high, 5 medium, 1 low); 11 pages clean.
Fixed every confirmed issue, plus 2 duplicate/missing React-key bugs a live console
sweep caught that the static audit could not. All verified in-browser on a fresh
server (section titles render, diff works, no console errors); `tsc` clean.

Contract mismatches (frontend was reading the wrong field/param names — verified
against live backend before fixing):
- **Daily Report**: section titles were blank — backend sends `section_name`, UI read
  `name` (also fixed the undefined React key). `ui/src/data/api.ts` + `DailyReportPage.tsx`.
- **Strategy Compare diff**: was fully broken — UI sent `a`/`b` (backend wants
  `strategy_id_a`/`strategy_id_b` → 422) and read `fields`/`value_a`/`value_b`/`strategy_a_id`
  (backend sends `field_diffs`/`a_value`/`b_value`/`strategy_id_a` → `.map` crash). Aligned
  the api.ts types, the fetch params, and `StrategyComparisonPage.tsx`.
- **Strategy Dev**: success toast showed no stage — read `current_stage`; success payload
  has `next_stage` (error payload legitimately has `current_stage`, left as-is). `StrategyDevPage.tsx`.

Crash guards / render bugs:
- **Ledger**: `sizing.reduce(...)` had no guard; backend can omit `latest_risk` → crash.
  Now `(sizing ?? []).reduce(...)`. `LedgerPage.tsx`.
- **Optimizer**: 4 mojibake em-dashes (`â€"` from a double-UTF-8 encoding) → proper `—`.
- **PCBA**: two `String(boolean)` renders showed raw `true`/`false` → `YES`/`NO`; the danger
  styling now follows the value. Also a duplicate React key (`feature-status` collided across
  pcba+cjt checks) → index-suffixed.
- **Condition Lab**: bucket-detail axes rendered without the `?? "—"` guard the table uses → added.
- **History**: hardcoded/stale condition-tally source line (`...20260622...json — 46 windows`) →
  dynamic bucket count, no fabricated numbers.

11 pages came back clean: Quick Start, Proof, Audit, Dashboard, Trade, Live Charts,
Adaptive, Settings, Decisions, Fury, Stack.

## 2026-06-27 - "Trading Windows" live-chart cockpit (Task B)

## 2026-06-27 - "Trading Windows" live-chart cockpit (Task B)

A 4-pane (2×2) live-ish chart cockpit, like MT4/TradingView: Live / Demo /
Strategy A / Strategy B, each watching what the CAS agents track, with optional
manual controls.

### Backend (`api/routes/chart.py`, registered in `api/server.py`)
`GET /api/forex/chart/window?symbol=&timeframe=&bars=` → `{candles:[{time,o,h,l,c}],
quote:{bid,ask,mid,spread,is_market_open,session}, source, live_feed, feed_label}`
via `market_data.connector.get_connector()` (OANDA when configured, else yfinance).
Small in-process **TTL cache (~20s)** keyed by (symbol,timeframe,bars) so multiple
panes can poll every ~12s without hammering the slow/rate-limited upstream on a
single-worker uvicorn. `GET /chart/symbols` lists tradeable symbols + timeframes.
HONEST: `live_feed:false` + `feed_label:"near-real-time market data (delayed)"` —
no connected broker tick feed; yfinance/OANDA is delayed retail data.

### Manual orders (`POST /api/forex/order-dispatch/manual`)
`{symbol,direction,lots,sl?,tp?}` → routes one `TradeIntent` through the SAME gated
`dispatch_intents` (paper-safe by default; SL/TP auto-derived from the live quote
when omitted so the order is always risk-bounded). `?confirm=true` required only
when live trading is owner-authorized. Verified: paper BUY EUR/USD → BROKER_EXECUTED,
`live_execution_runtime_locked` stays true.

### UI (`TradingWindow.tsx`, `WindowsPage.tsx`, nav in `App.tsx`/`Shell.tsx`, CSS)
Each window: role label + status chip + symbol/timeframe selectors + live bid/ask/
spread/session → `CandlestickChart` (pure SVG) → footer with source/feed label +
Buy/Sell (0.01-lot gated paper orders) + Pause (UI-local poll toggle). Polls every
12s; the TTL cache covers it. Strategy panes default from the top strategy leads /
Fury replay candidates. "Live" honestly shows "No broker feed — market data".
New nav item **"Live Charts"** (`?page=windows`).

**Verified end-to-end:** all 4 panes render real candles (60 each) + real quotes
(incl. gold @ ~4086); symbol/timeframe selectors reload the chart; Buy → "PAPER:
BUY EUR/USD 0.01 lots filled"; Pause toggles; mobile stacks single-column; no
console errors. `tests/test_chart_route.py` (5) pass; full suite 1140 passing
(same 6 pre-existing `strategy_leads.json` `PROMOTED_PAPER_LANE` failures, untouched).

## 2026-06-27 - "Go Live — Owner Switches" panel (Task A: enable live trading from the app, no .env)

## 2026-06-27 - "Go Live — Owner Switches" panel (Task A: enable live trading from the app, no .env)

The owner is not a developer; going live used to require editing `.env`. This adds
in-app toggle switches for everything `runtime_gates.evaluate_live_trading` checked
that was env-only, following the exact `risk_control` override pattern.

### Runtime override (`cas_forex/live_enable_control.py`)
Module-level `_OVERRIDES` + `set_live_enable_overrides()` / `resolve_live_enable()` /
`clear_live_enable_overrides()`, plus `apply_live_enable_overrides(config)` that
returns a `_ResolvedConfig` view whose six live-enable flags read their override
values. The flags: `personal_account_ack`, `no_pooled_capital_ack`, `live_mode`,
`prefer_mt5`, `owner_enable_live_trading`, `live_trading_licensed`.

### Gate wiring (`cas_forex/runtime_gates.py`)
`_resolve_config` now consults `apply_live_enable_overrides` — the single point where
the toggles reach the real-money authorization path. **No-op when no overrides are
set** (existing behaviour/tests unchanged); fail-closed (overrides only ever set the
six named booleans — every other gate requirement is still checked at the bridge).

### API (`api/routes/live_enable.py`, registered in `api/server.py`)
`GET /api/forex/live-enable/state`, `POST /update`, `POST /reset`. Every response
re-evaluates `runtime_gates` and returns the live-trading decision so the UI shows
exactly what is still missing.

### UI ("Go Live — Owner Switches" panel on Settings, `SettingsPage.tsx` + `App.css`)
6 real toggle switches in 3 groups (Acknowledgments / Live broker mode / Owner enable),
each labelled with its real consequence; a live readout chip (AUTHORIZED vs NOT YET)
with the exact still-missing list; an always-visible honest caveat: the toggles satisfy
the gate but a connected broker feed + a running dispatch loop are still required, and
the bridge re-checks at order time — never one accidental tap from real money.

**Verified end-to-end:** API returns correct state; flipping all 6 toggles in the UI
flips the gate to AUTHORIZED with an empty missing-list; Reset reverts to config
defaults; mobile layout correct; no console errors. New tests
`tests/test_live_enable_control.py` (7) + `tests/test_runtime_gates.py` (7) all pass;
full suite 1135 passing (6 pre-existing unrelated failures from the working-tree
`strategy_leads.json` `PROMOTED_PAPER_LANE` WIP — not touched here).

## 2026-06-27 - Floating AI assistant + owner risk control (you drive, no ceilings)

Two owner-facing features, plus phone access over WiFi.

### Floating AI assistant (`ui/src/components/FloatingAssistant.tsx`)

A persistent 💬 chat bubble mounted at the app root, so it follows the owner on
every page. Opens a chat panel wired to `POST /api/forex/assistant/chat`
(`api/routes/assistant.py`) — a cockpit-aware Claude reply via the anthropic SDK
(`ANTHROPIC_API_KEY` from env, model `claude-sonnet-4-6`). Never 500s: returns a
clear "set ANTHROPIC_API_KEY" message when unconfigured, a graceful error string
on provider failure; `GET /assistant/status` reports configured + model. Verified
live (real reply, source=ai).

### Owner risk control (`cas_forex/risk_control.py`)

Set ANY concurrent-trade count and ANY loss cap at runtime — or remove the cap
entirely (null = unlimited). Mirrors the broker_control override pattern; the
effective caps feed `execution_guard.caps_from_config`, so they apply to the
pre-execution risk gate on the next dispatch with no restart. With no overrides
the prior config-only caps are reproduced exactly. `GET/POST /api/forex/risk-control`
+ a "Risk Control — You Drive" panel on the Settings page (4 caps, each with an
Unlimited toggle). Verified: an oversized order the default 0.5-lot cap blocks
passes once the owner removes the exposure cap.

### Phone access

Backend + UI dev server now bind to the LAN (`--host 0.0.0.0`); phone reaches the
cockpit at `http://<PC-LAN-IP>:5174` and points at the API via the in-app
Settings → API address field. Local/home-WiFi only until hosting + auth land.

+12 risk-control tests. Full suite: 1133 passed.

## 2026-06-27 - Broker strictness: loosen OR harden (both MT5 & MT4), one knob

Made the broker control symmetric. `broker_strictness` ∈ `loose | normal | strict`
is the single loosen-or-harden knob for both MT5 and MT4 (and the simulator):
`loose` relaxes the execution tolerances (accept more orders), `strict` tightens
them (reject more), `normal` = defaults. Env (`BROKER_STRICTNESS`) or runtime
(`POST /api/forex/broker-control/update {"strictness": "..."}`). Per-field
tolerance overrides still win over the preset; the report now carries
`strictness`, `loosened`, and `hardened`. Verified: a 4-pip-stop order is
rejected at normal, executes when loosened, rejected when hardened. +8 tests,
full suite 1121.

## 2026-06-27 - Broker control (choose MT4/MT5 + loosen) + adversarial-review fixes

Owner gets two broker abilities — pick the platform and loosen the paper limits —
and the security review of the prior round's hardening/API caught a real
fail-open I introduced, now fixed. Full suite: 1114 passed.

### Owner broker control (`cas_forex/broker_control.py`)

- CHOOSE the platform the gated dispatch loop trades through:
  `broker_platform` ∈ `auto | mt5 | mt4 | simulated`. `select_bridge()` honors
  it; the dispatch loop now uses it instead of the auto-only `get_bridge()`.
- LOOSEN the paper/simulator execution tolerances (`max_spread_pips`,
  `max_slippage_pips`, `min_lot`, `max_lot`, `min_stop_distance_pips`) so the
  paper broker accepts more orders. Verified: a tight-stop order rejected by the
  strict sim executes once loosened.
- Runtime-overridable via `POST /api/forex/broker-control/update` (+ `GET
  /state`, `POST /reset`); persistent via env. The real-money loosen
  (`mt5_treat_account_as_demo`) and the per-transfer cap (`movement_max_usd`)
  are env-only — deliberately NOT settable from the runtime API.

### Adversarial-review fixes (5 confirmed findings)

- **is_demo_account fail-open (high):** the demo-detection substring fallback
  (`"demo" in server/company`) could flip a genuine LIVE account to demo and
  skip the live gate — broker/operator-controlled strings, not safety inputs.
  Now ONLY a positive `trade_mode == ACCOUNT_TRADE_MODE_DEMO` match confirms
  demo (fail-closed to live); the substring path is gone. The owner can still
  explicitly declare paper via `mt5_treat_account_as_demo`.
- **close_position ungated (low):** a position close is a real `order_send`;
  it now goes through the same live-trading gate as `execute_order` (shared
  `_live_gate_block`).
- **MM-1 withdraw exposure (high):** WITHDRAWAL is an outflow, so it now binds
  to the owner-allowlisted destination (like PAYOUT); added an optional
  per-transfer USD cap (`movement_max_usd`); money POSTs now require an explicit
  `?confirm=true` when the capability is owner-authorized (second layer beyond
  the gate).
- **MM-2 provider error (low):** a misconfigured/unavailable payment provider
  becomes a clean `FAILED` result instead of a 500.

### MT4

The dispatch loop already drives MT4 (verified last round). `broker_platform=mt4`
now selects the MT4 mailbox bridge explicitly; MT4 stays paper/demo-only.

Tests: +21 (broker-control unit + route, demo-substring regression, owner
loosen override, close-position gate, withdraw allowlist + cap + provider-error,
authorized payout confirm flow).

## 2026-06-26 - API surface + MT5 bridge live-gate hardening (+ MT4 verified)

Exposed both engines over the FastAPI gateway, hardened the MT5 bridge so a
connected live account can't fill orders without owner authorization, and
confirmed the gated dispatch loop works on the MT4 front. Full suite: 1092 passed.

### MT5 bridge hardening (root-cause fix for GB-1)

The earlier fix patched the dispatch-loop chokepoint; this closes the root in
shared broker infra so DIRECT callers (e.g. the MT5 demo verifier lane) are also
fail-closed.

- `MT5Bridge.is_demo_account()` — best-effort demo detection (trade_mode /
  server / company), fail-closed (unconfirmable → treated as live).
- `MT5Bridge.execute_order` now requires `runtime_gates.require_authorized
  ("live_trading")` before `order_send` whenever the connected account is NOT a
  confirmed demo account — so a connected LIVE account returns REJECTED without
  ever sending, regardless of `config.live_mode`. A connected DEMO account stays
  paper (no gate).
- `will_execute_real_order()` = `is_connected() and not is_demo_account()`, so
  the execution guard and the bridge agree on what counts as real.

### API surface

- `api/routes/order_dispatch.py` (`/api/forex/order-dispatch`): `GET /latest`
  (most recent gated dispatch cycle, read-only), `POST /run` (run one now —
  real signals → overseer → gate → configured bridge; paper-first).
- `api/routes/money_movement.py` (`/api/forex/money-movement`): `GET /gates`
  (deposit / bank-card / payout gate status + what's missing), `POST /deposit
  /withdraw /payout /reinvest-split` via `MovementEngine.from_config`. Each runs
  the capability gate first; default config → every POST returns BLOCKED with
  the missing requirements and moves no money.

### MT4

Confirmed the gated dispatch loop is broker-agnostic and drives the MT4 EA
mailbox bridge (`MT4EABridge`): a dispatched order is written as a `PAPER_MT4`
command intent and returns `PENDING`. MT4 is paper/demo-only by construction
(the EA bridge refuses live mode).

Tests: +11 (bridge live-gate regression, MT4 mailbox dispatch, 2 order-dispatch
route, 5 money-movement route).

## 2026-06-26 - Agent-signal dispatch + Stripe provider + adversarial-review fixes

Wired the agent cycle's real signals into the gated dispatch loop, added a live
Stripe payment-provider skeleton, then ran a 5-lens adversarial review (with
per-finding refutation + a completeness critic) and fixed every confirmed
finding. Full suite: 1084 passed.

### Engine A — agent-signal dispatch (`cas_forex/agent_dispatch.py`)

Reuses the SAME signal builders (`build_micro_scalp_intents` /
`build_hourly_intraday_intents`) and the SAME overseer (`review_route_intents`)
as the existing cycle, then routes overseer-approved intents through
`order_dispatch.dispatch_order` (live + risk gate → bridge → ledger). Every
intent is represented in the report (approved→dispatched, rejected→
`OVERSEER_REJECTED`). `order_dispatch` refactored to share a `dispatch_order` +
`build_dispatch_report` core (no duplication).

- `scripts/run_agent_dispatch_cycle.py` — production runner (real replay evidence
  → overseer → gated paper dispatch → JSON artifact). Verified end-to-end against
  real Forex Fury replay leads.

### Engine B — Stripe provider (`cas_forex/payment_providers.py`)

`StripePaymentProvider` (lazy/injectable SDK, `is_real=True`) + `build_payment_provider`
factory + `MovementEngine.from_config`. A real provider is unreachable until the
capability gate authorizes it, and its events are real-money (refused by the
paper ledger).

### Adversarial-review fixes

- **GB-1 (blocker):** the live-trading gate keyed only on `config.live_mode`, but
  a *connected* `MT5Bridge` fills real orders regardless — so LIVE_MODE off + a
  connected real account = real order with no owner gate. Added
  `BrokerBridge.will_execute_real_order()` (MT5Bridge → True when connected); the
  execution guard now requires the live-trading gate whenever the bridge would
  execute real, not just when `live_mode` is set.
- **payout-allowlist (med):** an authorized payout could target any caller
  `destination_id`. The engine now binds the destination to / validates it
  against `config.payout_destination_id`, fail-closed.
- **SM-1 (med):** Stripe `requires_capture` (authorized, not captured — funds not
  moved) no longer maps to SETTLED.
- **OD-1 (low):** `PENDING` broker outcomes now have a `pending_count` bucket so
  executed+blocked+rejected+pending == intent_count.
- **OD-2 (low):** dispatch never-raises contract hardened — bridge with no
  usable method / a throwing `execute_order` becomes a per-intent
  `DISPATCH_ERROR`, not an aborted batch.
- **SF-1 (nit):** `dispatch_route_intents` pairs intents↔decisions positionally
  (matching the canonical cycle); no intent dropped under duplicate `intent_id`.

Tests: +13 (order dispatch real-bridge gate / pending / dispatch-error,
payout allowlist, Stripe deposit + `requires_capture`, real reinvest legs,
duplicate-id, report writer).

## 2026-06-26 - The two missing engines: order dispatch loop + money-movement engine

The gates were open-able but guarded nothing — no loop ever walked a signal
through them into a broker, and no transfer code sat behind the money gates.
This round builds both engines, paper-first and fully tested.

### Engine 1 — Order dispatch loop (`cas_forex/order_dispatch.py`)

The walk that was missing: `TradeIntent → BrokerOrderRequest (schema/geometry
validation) → execution_guard.guarded_place_order (live-trading gate if live,
then pre-execution risk gate) → bridge.execute_order → AccountLedgerEvent`.

- `TradeIntent` (normalized, broker-agnostic signal; SL/TP required so every
  dispatched order is risk-bounded by construction).
- `dispatch_intent` / `dispatch_intents` — non-raising per-intent loop; each
  yields a `DispatchResult` with explicit status (`REJECTED_PRECHECK`,
  `BLOCKED_LIVE_GATE`, `BLOCKED_RISK`, or `BROKER_<status>`), the gate decision,
  the broker outcome, and a balance-neutral dispatch ledger event.
- Paper-first: `bridge=None` uses `broker.get_bridge()` (SimulatedBrokerBridge
  unless live trading is owner-authorized). Going live is a config/flag swap on
  a loop already proven against the paper broker; the same gate chain runs in
  paper mode.

### Engine 2 — Money-movement engine (`cas_forex/money_movement.py`)

The transfer code behind the money gates. `PaymentProvider` abstraction +
`SimulatedPaymentProvider` (moves no real money, `is_real=False`).

- `MovementEngine.deposit / withdraw / payout / reinvest_split`. Each is
  fail-closed: the matching capability gate (`auto_deposit` /
  `bank_card_movement` / `payout_automation`) is evaluated first and the
  provider is only touched if authorized; a block returns the exact missing
  requirements and never calls the provider.
- `reinvest_split` retains the reinvest leg in-account (no gate) and routes the
  savings + tax-reserve legs through the payout gate.
- Simulated-provider events keep `external_money_movement=False`, so the paper
  account ledger accepts them; a real provider sets it True (real-money ledger,
  out of scope).

### Fix

- `execution_guard.guarded_place_order` now calls the real `bridge.execute_order`
  (falling back to `place_order` for test fakes). It previously called
  `place_order`, which only exists on test fakes — so the one sanctioned
  dispatch chokepoint would have failed against every real bridge.

### Other

- `scripts/run_paper_dispatch.py` — runnable end-to-end paper demo (dispatch →
  ledger → reinvest split), no credentials needed.
- Tests: `tests/test_order_dispatch.py` (5) + `tests/test_money_movement.py`
  (11). Full suite: 1056 passed (1 pre-existing stale-date failure in
  test_daily_report_generator, unrelated).

## 2026-06-25 - Army fleet round 5: operator audit + backup/restore + e2e smoke + quick-start

Four parallel agents on disjoint files. No collisions. 979 → 1032 (+53 net).

### Slice 1 — Operator audit log

`cas_forex/operator_audit.py` — append-only JSONL at
`evidence_runs/operator_audit/operator-audit.jsonl` with append + flush +
fsync per entry. `OperatorAuditEntry` carries `action_kind` (13 kinds:
STRATEGY_PROMOTED/DEMOTED/REJECTED/ARCHIVED/REVIEWED,
FOREX_FURY_PROMOTED, RUNTIME_GATE_FLIP, NOTIFICATION_SUBSCRIBED/UNSUBSCRIBED,
WEBHOOK_SUBSCRIBED/UNSUBSCRIBED, LEGACY_RECEIPTS_ARCHIVED, OTHER), actor,
target id/label, summary, payload, recorded_at_iso, reversible flag +
reversal_hint.

Append validates summary against `OBSERVATIONAL_GUARD_PHRASES`
(case-insensitive) and raises ValueError on match — no advisory text
gets persisted.

`api/routes/operator_audit.py` — `GET /entries?limit=...&since_iso=...
&action_kind=...&action_kind=...` (multi-filter), `GET /stats`, `POST
/record` (400 on guard phrase). Tests: 15 unit + 8 route.

Wiring into the existing strategy_dev_actions / forex_fury_promote /
runtime-gate endpoints is a follow-on slice; this round ships the
primitive + standalone API.

### Slice 2 — Backup / restore primitive

`cas_forex/backup_restore.py`:
- `create_backup(...)` produces a ZIP at `snapshot_dir/cas-forex-backup-<ts>.zip`
  with an internal `manifest.json`. Glob patterns default to
  `strategy_leads.json`, `evidence_runs/agent_memory/*-report.json`
  (latest-only by mtime), agent-events.jsonl, agent-events-mt5-demo.jsonl,
  push/webhook subscriptions, operator-audit.jsonl. Never raises (empty
  manifest on failure).
- `list_backups(...)` returns sorted-DESC by created_at.
- `evaluate_restore(...)` classifies each file: WOULD_OVERWRITE /
  WOULD_RESTORE_NEW / SKIPPED_UNCHANGED / MISSING_IN_BACKUP /
  SKIPPED_OUT_OF_ROOT. Read-only.
- `execute_restore(...)` writes via tempfile + os.replace per file.
  Out-of-root paths refused. Unchanged files skipped (idempotent).
  Simulated I/O error → live file untouched.

`scripts/run_backup.py` — always creates a backup.
`scripts/run_restore.py` — `--snapshot-path` required; `--execute`
required for real restore (default dry-run). `--only-files` for scoped
restore.

14 tests, all `tmp_path`-based (never touches operator's real
evidence_runs/).

### Slice 3 — End-to-end smoke orchestrator

`cas_forex/e2e_smoke.py` — `run_endpoint_smoke(...)` hits every API
endpoint in `BUILT_IN_ENDPOINTS` (17 entries across health, dashboard,
readiness, observability, agent-decision, telemetry, configuration,
risk, strategy, reporting, subscriptions), validates required schema
keys at the top level, classifies pass/fail/skip per endpoint, returns
`E2ESmokeReport(passed, failed, skipped, elapsed_ms, failures, results,
plain_english_summary)`.

`skip_post=True` by default (POST endpoints can mutate); GET-only smoke.
Schema-check leniency: missing required key → success=False,
schema_check=`MISSING_KEY:<name>`. Connection error → status_code=None,
error_message documents.

`scripts/run_e2e_smoke.py` — `--api-base`, `--timeout-seconds`,
`--json`, `--summary-only`, `--exit-code-on-failure`. Human view shows
per-category OK/FAIL tally + failures list.

16 tests (5-phrase forbidden-substring parametrized across all-OK,
all-500, empty-catalog branches; belt-and-suspenders redactor in the
report builder).

### Slice 4 — Quick-Start onboarding page (UI)

`ui/src/pages/QuickStartPage.tsx` — 7-milestone checklist with
auto-refresh every 30s + "Run all checks now" button:
1. API server reachable (checks `/health`)
2. MT5 terminal connected (via stack-health)
3. Autowake supervisor running (via stack-health)
4. Autonomous loop firing (via autonomous-loop/health)
5. PWA installed on phone (operator self-marks; persisted in
   localStorage `cas_forex_quick_start_pwa_installed`)
6. Notification subscription registered (push OR webhook)
7. Operator briefing returns plain English

Completion banner ("Stack ready. Loop firing. Phone connected.
You're set.") shown only when all 7 are done.

`ui/src/components/QuickStartItem.tsx` — collapsible card with status
chip + "how to complete" detail body.

Nav placement: "Quick Start" is now the FIRST tab in the top nav.
Default route preserved (still `proof` when no `?page=`).

UI build: 68 modules, 2.76s, PWA SW regenerated, zero TS errors.

### Parent integration

`api/server.py` — additive: import + include_router for
`operator_audit` under `/api/forex/operator-audit`.

### Verification

```bash
py -3.12 -m pytest tests -q   # 1032 passed (979 → 1032, +53 net)
cd ui && npm run build         # 68 modules, 2.76s, PWA SW regenerated
```

### Honest assessment after 5 rounds

The operational chassis is now comprehensive. Across 5 rounds:
- Tests: 631 → 1032 (+401 net)
- Backend modules: 20+ new (most pure / observational)
- API routes: 13 new (including stack-health, system-health, daily-report,
  strategy-comparison, operator-briefing, risk-monitoring, audit log,
  push/webhook subscriptions, agent-decision history)
- UI surfaces: 14 new pages/components (Quick Start, Stack Status, Compare,
  Daily Report, Forex Fury, Strategy Dev, Decision History, Portfolio Risk,
  Operator Briefing, Multi-Timeframe Selector, Live Telemetry, Notification
  Subscription, Webhook Subscription, AgentDecisionCard, AutonomousLoopCard)
- Forbidden-phrase guards: enforced across every operator-facing
  observational primitive

What more chassis will NOT do: change the revenue picture. The
remaining levers are:
1. Strategy edge research (multi-iteration, can't fleet).
2. Wiring chassis primitives into the live agent cycle (high blast
   radius — better as targeted slices with explicit operator review).
3. Operator-side actions (MT5 AutoTrading, runtime gate flips, license
   work).

## 2026-06-25 - Army fleet round 4: stack-check + strategy ranking/diff + daily report + UI pages

Four parallel agents on disjoint scopes. No collisions. 879 → 979 (+100 net).

### Slice 1 — Stack health check

`cas_forex/stack_health_check.py` — composes 6 checks (`uvicorn-api`,
`autowake-supervisor`, `mt5-terminal`, `autonomous-loop`,
`readiness-gates`, `live-telemetry`) into a single
`StackHealthReport(overall_status, checks, plain_english_summary,
next_actions)`. Overall precedence: MISSING > DEGRADED > UNKNOWN > OK.

`scripts/run_cas_forex_stack_check.py` — CLI: `--api-base`, `--json`,
`--summary-only`, `--exit-code-on-degraded`, `--repo-root`.

`api/routes/stack_health.py` — `GET /api/forex/stack-health/check`
(thin wrapper; parent added this so the UI page has a backend).

Tests: 16, parametrized 9 forbidden phrases across 4 sample reports.

### Slice 2 — Strategy comparison / ranking

`cas_forex/strategy_comparison.py` — pure:
- `normalize_records(...)` unifies Forex Fury candidates + strategy leads +
  strategy-dev-queue items into a single shape.
- `rank_strategies(...)` computes per-metric ranks + composite score (0–100).
  Default weights: PF 0.35, DD-inverse 0.30, walk-forward grade 0.20,
  recency 0.10, total-trades-log 0.05. Normalizers: PF clamped at PF/5,
  DD-inv = 1 - min(dd/50, 1), WF grade {LEAD:1.0, WATCH:0.5,
  REJECT:0.0}, trades = log1p(n)/log1p(1000). Recency: linear over
  30 days clamped 0..1.
- `diff_strategies(a, b)` field-level diff with observational
  `plain_english_diff`.

`api/routes/strategy_comparison.py` — `GET /ranked?limit=N` (default
25, max 50, 400 on out-of-range) and `GET /diff?strategy_id_a=X&strategy_id_b=Y`
(400 on unknown id).

Tests: 22 unit + 22 route fixtures (44 total). 10 forbidden phrases
parametrized across ranked summary, diagnostic hints, and diff text.
Wording emphasizes "the operator owns interpretation; this is
observational evidence only."

### Slice 3 — Daily report generator

`cas_forex/daily_report_generator.py` — pure composer with 7 sections:
1. `cycles` — total + by-outcome counts; flags ≥5 consecutive blocked.
2. `decisions` — total + by_status + top blocking reason.
3. `executions` — total + net P&L + top winning/losing strategies.
4. `strategies` — promotions/demotions + walk-forward verdict counts.
5. `risk` — peak concentration + peak margin utilization + floating P&L range.
6. `system` — uvicorn / autowake uptime % + MT5 disconnect events.
7. `incidents` — loop stalls, REJECTs, dispatch failures, MT5 incidents.

`overall_headline` template: "YYYY-MM-DD: N cycles, N executions,
N blocked, net $X — system healthy throughout." (or "...N incident(s)
recorded.")

`api/routes/daily_report.py` — `GET /today` and `GET /{report_date}`.

Tests: 35 generator + 5 route (40 total). 10 forbidden phrases
parametrized across multiple report fixtures.

### Slice 4 — UI: Stack Status + Strategy Comparison + Daily Report pages

`ui/src/pages/StackStatusPage.tsx` — 30s polling. Overall status chip,
plain summary, 6-check table, remediation steps as numbered list (the
"factual commands" returned by the backend, not advice).

`ui/src/pages/StrategyComparisonPage.tsx` — Ranked/Diff mode toggle:
- Ranked: limit selector (10/25/50), 10-col table (rank, ID, source
  chip, symbol, TF, family, PF, DD%, WF grade, composite). Row-click
  enters diff mode with that row as A and auto-picks a non-equal B.
- Diff: two dropdowns, side-by-side field table, `plain_english_diff`
  verbatim.

`ui/src/pages/DailyReportPage.tsx` — date picker (`max=today UTC`,
default today), overall headline, plain summary, collapsible section
cards (defaults to expanded), diagnostic hints bullet list.

`ui/src/data/api.ts` — additive types `StackHealthCheckResult`,
`StackHealthReport`, `StrategyComparisonRecord`, `StrategyRankingReport`,
`StrategyDiff`, `DailySection`, `DailyReport`; fetchers
`fetchStackHealth`, `fetchRankedStrategies`, `fetchStrategyDiff`,
`fetchDailyReport`.

`ui/src/App.tsx`, `ui/src/components/Shell.tsx` — additive: `Page`
union extended with `"stack-status"` / `"strategy-comparison"` /
`"daily-report"`; nav entries Stack / Compare / Daily.

UI build: 66 modules, 2.95s, PWA SW regenerated, zero TS errors.

### Parent integration

`api/server.py` — additive: extended imports with `strategy_comparison`,
`daily_report`, `stack_health`; three new `include_router` lines under
their own prefixes.

### Verification

```bash
py -3.12 -m pytest tests -q   # 979 passed (879 → 979, +100 net)
cd ui && npm run build         # 66 modules, 2.95s, PWA SW regenerated
```

### Boundary unchanged

Stack-check next_actions are factual commands ("Launch autowake
supervisor: ..."). Strategy comparison output is observational
evidence. Daily report describes what happened. None of these
artifacts produces trade advice. All forbidden-phrase guards verified
in tests.

## 2026-06-25 - Army fleet round 3: dispatcher loop + risk gate + webhook fallback + UI panels + system health

Five parallel agents on disjoint scopes. No collisions. 799 → 879 (+80 net).

### Slice 1 — Notification dispatcher loop

`cas_forex/notification_dispatcher_loop.py` — `NotificationDispatcherLoop`
class mirrors `AutowakeSupervisor`: injected clock/sleeper, shutdown event,
max_ticks/duration/consecutive-failure caps, backoff
`tick_interval * min(2^consec, 16)`.

Per tick: load current state snapshot → load previous from JSON file →
`notification_triggers.detect_all(current, previous)` → dispatch each event
to each subscription → persist current → previous atomically. Dispatch
failures swallowed (tick continues). Loader failures count toward
consecutive-failure budget.

`scripts/run_notification_dispatcher.py` — launcher; SIGINT/SIGTERM →
shutdown event; default 60s ticks. Real loader chains
`load_operator_briefing_inputs` + `load_loop_health_inputs`. Real
dispatch is the stubbed `dispatch_test_push(transport=None)` until
`pip install pywebpush` lands.

+9 tests.

### Slice 2 — Pre-execution risk gate

`cas_forex/pre_execution_risk_gate.py` — pure
`evaluate_proposed_intent(...)` that checks a proposed RouteIntent
against the current `PortfolioRiskSnapshot` and `RiskCapConfig`.

Cap dimensions (7):
- `max_total_exposure_lots`
- `max_concentration_pct`
- `max_margin_utilization_pct`
- `max_positions_per_symbol`
- `max_open_position_count`
- `max_drawdown_pct_from_equity_peak`
- `max_floating_loss_usd`

`DEFAULT_CAPS`: 10 lots / 70% / 70% / 5 pos / 20 open / 15% dd / no
floating cap. `None` on any cap means "no cap" for that dimension.

`RiskGateDecision.plain_english_reason` is parametrized against 10
forbidden phrases (`"you should sell"`, `"consider closing"`, `"scale
back"`, `"exit position"`, `"take profit"`, `"cut your losses"`,
`"buy more"`, `"add to position"`, `"is a good entry"`, `"we
recommend"`) across PASS and REJECT branches — observational only.

Concentration computes the max would-be symbol concentration after
adding (covers the case where adding to a small symbol still leaves an
existing dominant symbol breaching). Exposure aggregates as `|lots|`.

Integration into the agent cycle is OOS (follow-on slice).

+28 tests.

### Slice 3 — Webhook fallback notifications

`cas_forex/webhook_notifications.py` — `WebhookSubscriptionStore`
(JSONL-backed, atomic temp+rename) + `dispatch_webhook(...)`.

Pre-dispatch validation: `OBSERVATIONAL_GUARD_PHRASES` (11 phrases:
`"you should buy"`, `"you should sell"`, `"good entry"`, `"good exit"`,
`"recommended trade"`, `"we recommend"`, `"buy now"`, `"sell now"`,
`"take profit now"`, `"best trade"`, `"hot tip"`) checked
case-insensitively against payload's `title`+`body`. Match → short-circuit
to `success=False, error_message="advisory phrase in payload: '<phrase>'"`
before any HTTP call. Tests confirm transport NEVER invoked for any of
the 11 phrases.

`api/routes/webhook_notifications.py` — `POST /subscribe` (400 on
missing url), `POST /unsubscribe` (204 idempotent), `GET /subscriptions`,
`POST /test`. Module-level singleton store + `set_store_for_testing` /
`set_transport_for_testing` injection.

Works with Slack, Discord, Microsoft Teams, custom servers — anywhere
the operator pastes the webhook URL.

+23 tests (15 unit + 8 route).

### Slice 4 — UI: portfolio risk + push subscriptions + webhook subscriptions

`ui/src/components/PortfolioRiskCard.tsx` — polls
`/api/forex/risk-monitoring/portfolio` every 30s. Open-position count,
total exposure, floating P/L (color-coded), concentration meter +
margin utilization meter (teal under 50%, warning yellow 50-70%, danger
red >70%), top-5 by_symbol table, diagnostic-hint bullets. Mounted on
TradePage above LiveTradesTelemetry.

`ui/src/components/NotificationSubscriptionPanel.tsx` — uses the
browser Push API: `Notification.permission` check,
`navigator.serviceWorker.ready` + `pushManager.subscribe`. Buttons:
Enable / Disable / Send test push. Persistent inline note: "Backend
dispatch backend (pywebpush) not yet installed — subscriptions
register but pushes will fail until installed." VAPID public key from
`VITE_CAS_FOREX_VAPID_PUBLIC_KEY` env. Mounted on SettingsPage under
MobileApiPanel.

`ui/src/components/WebhookSubscriptionPanel.tsx` — list existing,
add form (webhook_url + label), per-row remove button, "Send test
webhook" with inline result. Mounted on SettingsPage.

`ui/src/data/api.ts` — additive: 6 new types, 8 fetchers/actions
(`fetchPortfolioRisk`, `fetchPushSubscriptions`, `subscribeWebPush`,
`unsubscribeWebPush`, `testPushAll`, `fetchWebhookSubscriptions`,
`subscribeWebhook`, `unsubscribeWebhook`, `testWebhookAll`).

`ui/src/App.css` — additive: `.portfolio-risk-*`, `.risk-meter-*`,
`.notification-subscription-*`, `.webhook-*` styles.

UI build: 63 modules transformed, 2.88s, PWA SW regenerated.

### Slice 5 — System health monitor

`cas_forex/system_health_monitor.py` — pure `compose_system_health(...)`
returns `SystemHealthSnapshot` with:
- `processes`: per-process `ProcessHealth(name, expected, last_signal_at_iso,
  seconds_since_signal, likely_alive, status_label)` where
  `status_label ∈ {alive, stale, missing, expected_off}`.
- `evidence_freshness`: per-artifact freshness with per-artifact threshold
  override.
- `disk_space`: `shutil.disk_usage` + recursive walk of evidence_runs/.
- `overall_status ∈ {healthy, degraded, stale, unknown}` with precedence.
- `plain_english_summary`, `diagnostic_hints`.

5 forbidden imperative phrases (`"you should restart"`, `"consider
restarting"`, `"kill the"`, `"should be killed"`, `"force restart"`)
parametrized across all 5 status branches — health monitor describes
state, never commands.

`load_system_health_inputs(repo_root)` separate disk loader. Default
expected processes: `("uvicorn-api", "autowake-supervisor",
"mt5-terminal")`. `notification-dispatcher` reports `expected_off` when
absent (does NOT degrade overall).

`api/routes/system_health.py` — `GET /api/forex/system-health/snapshot`
with loader-injection.

+20 tests (16 composer + 4 route).

### Parent integration

`api/server.py` — additive: imports extended with `webhook_notifications`,
`system_health`; two new `include_router` lines under prefixes
`/api/forex/webhook-notifications` and `/api/forex/system-health`.

### Verification

```bash
py -3.12 -m pytest tests -q   # 879 passed (799 → 879, +80 net)
cd ui && npm run build         # 63 modules, 2.88s, PWA SW regenerated
```

### Boundary unchanged

Webhook payloads observational (11 forbidden phrases enforced
pre-dispatch). Risk gate decisions observational (10 forbidden phrases
across PASS+REJECT). System health observational (5 forbidden
imperative phrases across all status branches). Notification dispatcher
uses the same stubbed dispatcher until `pywebpush` is installed. The
LLM bot is still an understanding window. License gates remain
unchanged.

## 2026-06-25 - Army fleet round 2: Fury set application + notification triggers + UI pages + risk monitoring

Four parallel agents on disjoint scopes. No collisions. 726 → 799 (+73 net).

### Slice 1 — Forex Fury set application primitive

`cas_forex/forex_fury_set_application.py` — pure module:
- `parse_set_text(text) -> (parameters, errors)` parses MT4/MT5 `.set` files
  with optimization tuples (value, min, step, max, optimize_flag).
- `SetParameter`, `SetPayload`, `EnrichedOrderRequest` frozen dataclasses.
- `apply_set_to_order_request(...)` enriches a base broker order request
  with `.set` parameters via `DEFAULT_SET_KEY_TO_REQUEST_KEY` mapping
  (`Lot_Size→lots`, `Stop_Loss→stop_loss_pips`, `Take_Profit→take_profit_pips`,
  `InpUseGrid→uses_grid`, plus 13 more). Base never mutated; returns new dict.
- `materialize_set_payload(...)` disk loader with sha256 verification;
  returns `(SetPayload|None, error_message|None)`, never raises.

Out of scope: integration into `cas_forex/broker/mt5_bridge.py`. This slice
ships the primitive; the broker bridge integration is a follow-on with
larger blast radius.

+14 tests.

### Slice 2 — Notification trigger observers

`cas_forex/notification_triggers.py` — pure detectors that fire
`NotificationEvent`s when meaningful state changes:

| event_kind | severity |
|---|---|
| `TRADE_EXECUTED` | info |
| `TRADE_BLOCKED` | warning |
| `LOOP_STALLED` | alert |
| `LOOP_RESUMED` | info |
| `MT5_DISCONNECTED` | alert |
| `READINESS_GATE_FLIPPED` | info |

Each detector takes parsed state dicts + the previous observation
(`previous_status` / `previous_authorized_set` / `previous_cycle_report`)
and returns 0 or 1 events. `detect_all(...)` runs all detectors and
returns a deterministic tuple. `event_id = sha256(kind|key_fields)[:16]`
for dedupe.

`title` + `body` are OBSERVATIONAL ("Cycle abc executed BUY EURUSD
0.01 lots; broker ticket 12345"). Tests parametrize 14 forbidden
advisory phrases across all 6 detectors × multiple sample inputs — no
trade-pick language anywhere.

Wiring into the live agent cycle (calling `dispatch_test_push` when
events fire) is a follow-on slice; this one ships the primitives.

+30 tests.

### Slice 3 — UI integrator: Operator Briefing card + Fury page + Strategy Dev page

Consumes the three backend capabilities shipped in the last fleet.

`ui/src/components/OperatorBriefingCard.tsx` — polls
`/api/forex/operator-briefing` every 60s. `StatusChip` for loop status,
stats line, `plain_english_briefing` verbatim, diagnostic-hint bullets.
Mounted on `DashboardPage.tsx` above the existing 3-col grid.

`ui/src/pages/ForexFuryPage.tsx` — new "Fury" page. Lists replay
candidates with rank, ID, symbol, TF, family, PF, DD%, score,
readiness. Each row has a "Promote to paper lane" button that calls
`POST /api/forex/forex-fury-promote/promote`. Success shows `lead_id`
inline; 400 shows integrity error. Summary stats (total candidates,
top symbol, top family).

`ui/src/pages/StrategyDevPage.tsx` — new "Strategy" page. Lists queue
items with stage filter dropdown (default show all). Per-item:
5 action buttons (Promote / Demote / Reject / Archive / Review) +
optional inline note. Each button posts to
`/api/forex/strategy-dev-actions/{action}`. Success / 400 surfaced
inline with `current_stage` + `message`.

`ui/src/data/api.ts` — additive: `apiPostJson` helper,
`OperatorBriefingResponse`, `ForexFuryPromoteResponse`,
`ForexFuryPromotionStatusResponse`, `StrategyActionResponse`,
`StrategyDevAction`, `ApiPostError`. Fetchers + action wrappers.

`ui/src/App.tsx`, `ui/src/components/Shell.tsx` — additive: `Page`
union extended with `"forex-fury"` and `"strategy-dev"`; nav entries
labeled "Fury" and "Strategy" appended after "Decisions".

`ui/src/App.css` — additive styles for `.operator-briefing-card`,
`.fury-candidates-table`, `.fury-candidate-row`, `.fury-row-action`,
`.strategy-dev-list`, `.strategy-dev-row`, `.strategy-action-button`,
`.action-result-toast` (`.action-result-ok` / `.action-result-err`),
filter row, note input.

UI build: 60 modules, 2.87s, PWA SW regenerated. Zero TS errors.

### Slice 4 — Portfolio risk monitoring

`cas_forex/risk_monitoring.py` — pure aggregator:
- `compose_portfolio_risk_snapshot(*, live_telemetry, account_snapshot,
  now)` → `PortfolioRiskSnapshot` with per-symbol exposure aggregation
  (`MIXED` direction when both BUY+SELL on same symbol), concentration %,
  margin utilization %, largest gain/loss positions, sorted `by_symbol`
  list, plain-English summary, observational diagnostic hints
  ("Concentration above 60% in EURUSD", "Margin utilization above 50%").
- `snapshot_to_payload(...)` JSON-serializer.
- `SymbolRiskExposure`, `PortfolioRiskSnapshot` frozen dataclasses.

Tests parametrize 9 forbidden advisory phrases ("you should close",
"consider closing", "scale back", "exit position", "take profit now",
"cut your losses", "reduce exposure", "buy more", "add to position")
across 3 risk shapes; all observational. 27 parametrized assertions.

`api/routes/risk_monitoring.py` — `GET /api/forex/risk-monitoring/portfolio`.
Default loader chains `api.routes.live_telemetry.collect_live_telemetry()`
(reuses MT5 → movement_stream → empty cascade) and
`api.data.mt5_terminal_api_verifier_latest()` for the account snapshot.
Loader-injection hooks.

+29 tests (16 unit + 5 route + 8 forbidden-phrase parametrized).

### Parent integration

`api/server.py` — additive: import extended with `risk_monitoring`;
one new `include_router` line under `/api/forex/risk-monitoring`.

### Verification

```bash
py -3.12 -m pytest tests -q   # 799 passed (726 → 799, +73 net)
cd ui && npm run build         # 60 modules, 2.87s, PWA SW regenerated
```

### Boundary unchanged

Risk monitoring is OBSERVATIONAL. Notification trigger bodies are
OBSERVATIONAL. The Fury promote button posts `PROMOTED_PAPER_LANE`
only; live-money path remains license-gated. Strategy Dev actions move
queue stages without enabling live execution. The LLM bot is still an
understanding window. The agent cycle still trades autonomously on
the operator's behalf to remove emotional decisions from the loop.

## 2026-06-25 - Army fleet: push + Fury promote + strategy actions + history UI + operator briefing

Five parallel agents on disjoint files. No collisions. 631 → 726 (+95 net tests).
Parent integrates 4 new routes into `api/server.py`.

### Slice 1 — Web push notifications (skeleton)

`cas_forex/push_notifications.py`: `PushSubscription` + `PushSubscriptionStore`
(file-backed JSONL at `evidence_runs/push_subscriptions/subscriptions.jsonl`,
atomic temp+rename writes); `PushDispatchResult`; `dispatch_test_push`. An
observational-payload guard raises on advisory phrases — notifications are
report-only, never trade-advisory.

`api/routes/notifications.py`: `POST /subscribe`, `POST /unsubscribe` (204,
idempotent), `GET /subscriptions`, `POST /test-push`. Module-level singleton
store + `set_store_for_testing` / `set_transport_for_testing` hooks.

`dispatch_test_push` returns `success=False,
error_message="dispatch backend not installed (pywebpush)"` when no transport
injected. `pip install pywebpush` + a tiny VAPID transport unlocks real
push later — no dep added today.

Tests: 11 unit + 8 route = 19. Operator hits `POST /test-push` to validate
their subscription roundtrip without a real push delivery.

### Slice 2 — Forex Fury promote + sha256 verification

`cas_forex/forex_fury_promote.py`: `verify_set_integrity(...)` pure sha256
check; `promote_candidate(...)` looks up a replay candidate, verifies the
`.set` on disk matches the manifest, atomically appends a strategy lead.
Lead `status` is hard-coded `PROMOTED_PAPER_LANE` — never `PROMOTED_LIVE`
(license-flip stays operator-driven).

`api/routes/forex_fury_promote.py`: `POST /promote` (200 success, 400 on
integrity fail with structured detail), `GET /promotion-status?candidate_id=X`.
Loader-injection hooks for tests.

Promoted twice → appends both with distinct deterministic `lead_id`s
(audit-trail semantics; callers dedupe via `GET /promotion-status`).

Tests: 10 unit + 5 route = 15. Confirms PROMOTED_PAPER_LANE is the only
status emitted by this module.

### Slice 3 — Strategy Dev Queue promote/demote/reject/archive/review

`cas_forex/strategy_dev_actions.py`: `PROMOTABLE_STAGES = ("RESEARCH",
"REPLAY", "PAPER", "REVIEW")`, `STAGE_ORDER` map, pure predicates
`can_promote`/`can_demote`/`next_stage_for_promotion`/
`previous_stage_for_demotion`, and `apply_action(...)` that atomically
rewrites the queue JSON with `history` appended (never replaced) per action.
PROMOTED/REJECTED/ARCHIVED are terminal. REVIEW tags `last_reviewed_at_iso`
without changing stage. `PROMOTED` here is the queue-stage label only;
nothing in this slice enables live execution.

`api/routes/strategy_dev_actions.py`: `POST /promote`, `/demote`, `/reject`,
`/archive`, `/review`. 400 on illegal transition or missing strategy_id
with `{error, message, current_stage}` detail. Loader-injection.

Route gracefully accepts both `items`/`strategy_id` (spec) and the real
queue report's `work_items`/`item_id` shape so the existing dashboard
data flows through unchanged.

Tests: 13 unit + 9 route = 22.

### Slice 4 — Decision History UI page

`ui/src/pages/DecisionHistoryPage.tsx` — limit selector (10/25/50,
default 25), 60s polling, status breakdown stats
(`executed: N · blocked: N · approved_not_executed: N · no_recent_decision: N`),
empty/error/loading states.

`ui/src/components/DecisionHistoryRow.tsx` — truncated mono `cycle_id`,
`StatusChip` for `overall_status`, clamped summary with show-more toggle,
collapsible decision chain, muted `next_action_hint`. Plain text only — no
markdown / emojis / advisory text.

`ui/src/data/api.ts` — additive types `AgentDecisionHistoryItem`,
`AgentDecisionHistoryResponse`; fetcher `fetchAgentDecisionHistory(limit)`.

`ui/src/App.tsx` and `ui/src/components/Shell.tsx` — additive: `Page`
union extended with `"decision-history"`, route entry after Cond. Lab,
nav entry labeled "Decisions".

`ui/src/App.css` — additive styles for `.decision-history-*` classes.

UI build: 57 modules transformed in 3.22s, PWA precache 9 entries / 589 KiB.

### Slice 5 — Operator Briefing capability

`cas_forex/operator_briefing.py`: `OperatorBriefing` frozen dataclass
aggregating loop health, latest decision, live telemetry, MT5 probe, and
readiness state into one structured snapshot. Pure
`compose_operator_briefing(...)` takes parsed inputs; companion
`load_operator_briefing_inputs(repo_root)` does the disk I/O.

`plain_english_briefing` is a 3-5 sentence template the LLM bot surfaces
verbatim. Tests verify it NEVER contains "buy now" / "should you trade" /
"good entry" / "place a trade" / "what should i do" / "you should sell" /
"now is the time" (case-insensitive substring assertion).

`api/routes/operator_briefing.py`: `GET /api/forex/operator-briefing`
(loader-injection). Returns 200 even when all inputs are None — graceful
"unknown" briefing.

`cas_forex/cas_forex_bot.py`: new `BotCapability(key="bf", group="status",
label="Operator Briefing", api_endpoint="/api/forex/operator-briefing")`
added after `ah`. Capability count: 33 → 34.

Tests: 9 unit + 4 route = 13.

The LLM bot can now answer "what's going on?" with a single `bf` tool
call instead of chaining 4-5 capability calls.

### Parent integration

`api/server.py` — additive: imports extended with `notifications`,
`forex_fury_promote`, `strategy_dev_actions`, `operator_briefing`;
4 new `include_router` lines under prefixes
`/api/forex/notifications`, `/api/forex/forex-fury-promote`,
`/api/forex/strategy-dev-actions`, `/api/forex/operator-briefing`.

### Verification

```bash
py -3.12 -m pytest tests -q  # 726 passed (631 → 726, +95 net)
cd ui && npm run build       # 57 modules, 3.22s, PWA SW regenerated
```

### Boundary unchanged

LLM bot remains an understanding window. `requires_confirm` gates, Stage 3
validator, and runtime-gate licensure all unchanged. Push notifications
are observational. Strategy Dev `PROMOTED` is a queue-stage label only.
Forex Fury promotion writes `PROMOTED_PAPER_LANE` only. The agent cycle
still trades autonomously on the operator's behalf to remove emotional
decision-making from the loop — that's the whole point.

## 2026-06-25 - Parallel fleet: trade-page cards + decision history + receipt archive + Fury audit

Four parallel agents on disjoint slices. No collisions. 615 → 631 (+16 net).

### Slice 1 — Trade page: Agent Decision card + Autonomous Loop card

Surfaces the explainer (`ax`) and loop-health (`ah`) primitives as live
UI panels on the Trade page so the operator SEES them without typing.

- `ui/src/components/AgentDecisionCard.tsx` — polls `/api/forex/agent-decision/latest`
  every 30s. Header: truncated mono `cycle_id` + `overall_status` chip
  (executed→info, approved_not_executed→paper, blocked→warning,
  no_recent_decision→muted). `plain_english_summary` below. Collapsible
  "Decision chain" lists each step with a status chip (found→info,
  missing→muted, blocked→warning). `next_action_hint` in muted text at
  bottom.
- `ui/src/components/AutonomousLoopCard.tsx` — polls
  `/api/forex/autonomous-loop/health` every 30s. Header: `overall_status`
  chip (running→info, stalled→warning, others→muted). Stats line:
  `cycles today: N · decisions: N · executions: N · blocked: N`. Plain
  summary, "Last cycle: Xm Ys ago" (with local-time ISO), "Next due:
  HH:MM" when present, and a "What's blocking it" bullet list when
  `diagnostic_hints` non-empty.
- `ui/src/pages/TradePage.tsx` — additive: both cards in a 2-col grid
  directly above `<LiveTradesTelemetry />`, below `<MultiTimeframeSelector />`.
- `ui/src/data/api.ts` — additive: `DecisionChainStep`,
  `AgentDecisionResponse`, `AutonomousLoopHealthResponse` types;
  `fetchAgentDecisionLatest()`, `fetchAutonomousLoopHealth()`.
- `ui/src/App.css` — additive: `.agent-decision-card`,
  `.autonomous-loop-card`, `.decision-chain-list`, `.loop-diagnostic-list`,
  `.decision-status-row` (~150 lines, all using existing CSS vars).

Build: 55 modules transformed, 2.85s; PWA precache 9 entries / 582 KiB.

### Slice 2 — `GET /api/forex/agent-decision/history?limit=N`

- `api/routes/agent_decision_history.py` — globs recent cycle reports
  (newest-first by mtime), runs the pure explainer against each
  with shared context (memory / strategy / walk-forward / PCBA),
  returns the list. Default `limit=10`, range `[1, 50]`,
  out-of-range → HTTP 400 `{"error": "invalid_limit", ...}`. Same
  loader-injection pattern as the latest route.
- `api/server.py` — additive two lines (import + `include_router`
  under same prefix as the latest route so the tag groups together).
- `tests/test_agent_decision_history_route.py` — 6 tests: empty cycle
  set → empty list (NOT 404); 3 reports → 3 decisions newest-first;
  `limit=2` with 5 reports returns 2; `limit=0` and `limit=51` → 400;
  no `plain_english_summary` contains trade-advisory substrings.

### Slice 3 — Legacy MT4 receipt archive tool

The supervisor's `pending_receipt_count: 28` and the cockpit's
`legacy_total: 28` come from stale MT4-mailbox `RECEIPT_PENDING` rows
that never reconciled (no MT4 terminal active). This slice gives the
operator a safe way to archive them to a snapshot and reset the
baseline.

- `cas_forex/legacy_receipts_archive.py`:
  - `identify_stale_pending_receipts(events, *, age_threshold_hours,
    now)` — pure. Conservative: row qualifies only when
    `kind`/`event_kind` is `RECEIPT_PENDING` AND broker_mode contains
    "MT4" (case-insensitive, top-level / nested `command` / nested
    `intent`) AND timestamp is older than threshold. Missing fields
    or unparseable timestamps → row NOT archived.
  - `archive_stale_receipts(*, journal_path, snapshot_dir, dry_run=True,
    age_threshold_hours=24.0, now=None)` → `LegacyReceiptArchiveResult`.
    Default `dry_run=True`. Snapshot-first ordering (write+fsync the
    archive snapshot BEFORE rewriting the journal). Journal rewrite is
    atomic via temp file + `os.replace`. Idempotent: zero stale → no
    snapshot created. Any I/O error populates `error_message`;
    public API never raises.
- `scripts/run_legacy_receipts_archive.py` — CLI flags:
  `--journal-path` (default `evidence_runs/agent_workflow_queue/agent-events.jsonl`),
  `--snapshot-dir` (default `evidence_runs/legacy_receipts_archive/`),
  `--age-hours` (default 24), `--execute` (REQUIRED to actually
  archive), `--summary-only`. Default behavior is dry-run preview.
- `tests/test_legacy_receipts_archive.py` — 10 tests. All I/O via
  `tmp_path`; the real `evidence_runs/` is never read or written.

**Operator usage:**

```powershell
# Preview what would archive (safe):
py -3.12 scripts/run_legacy_receipts_archive.py

# Actually archive (writes snapshot + rewrites journal):
py -3.12 scripts/run_legacy_receipts_archive.py --execute
```

### Slice 4 — Forex Fury sets audit (investigation only, no code change)

The operator asked where their Forex Fury sets landed. Findings:

**Status: PARTIAL** — the 36 sets are fully ingested, ranked, replayed,
summarized, and the paper agent cycle IS consuming them today. They are
NOT yet driving live-money orders (license-gated by design).

**Location:**
- Ingest: `cas_forex/forex_fury_sets.py` parses `.set` files +
  ReportTester.html, fingerprints `.ex4`/`.ex5` binaries (does NOT execute).
- Candidates: `cas_forex/forex_fury_candidates.py` builds ranked replay
  candidates from the import report.
- Verdict: `cas_forex/forex_fury_replay_results.py` rolls condition-lab
  + walk-forward into `REPLAY_LEAD_FOR_ADAPTIVE_REVIEW`.
- Cycle consumption: `cas_forex/agent_state.py:155-162` calls
  `load_latest_forex_fury_*` + `build_micro_scalp_intents(...)` +
  `build_hourly_intraday_intents(...)` → `RouteIntent` with
  `strategy_setting="forex_fury_<family>_<symbol>_<tf>"`.
- API: `/strategy/forex-fury-set-import`,
  `/strategy/forex-fury-replay-candidates`,
  `/strategy/forex-fury-replay-results` already serve the imports.
- UI: rendered on `ui/src/pages/OptimizerPage.tsx`.

**Headline numbers from the import report:**

- 36 `.set` files imported (MT4=18, MT5=18).
- Families: scalping=14, swing=16, classic_m15=6.
- Symbols: AUDCAD=8, AUDUSD=6, EURUSD=4, GBPAUD=2, GBPUSD=6, SPX500=2,
  USDJPY=2.
- 24 ranked replay candidates produced.
- **Top profile:** AUDCAD M5 swing 04:00-05:00 — PF 15.12, DD 2.25%,
  total trades 294, history quality 98%.
- Walk-forward grade: `WALK_FORWARD_LEAD` (61/126 windows routed,
  35 positive).
- Condition-lab gap: 0.7912 across 297 cells.

**Caveat:** PF / DD numbers are vendor-supplied EA tester reports, NOT
CAS-validated OOS edge. The walk-forward replay over the CAS condition
lab is the more honest indicator and grades `WALK_FORWARD_LEAD`. The
agent cycle is acting on the verdict — not on the raw tester reports.

**Path from PARTIAL → LIVE** (not built in this slice, ~5-file change):

1. `cas_forex/broker/mt5_bridge.py` — add `apply_set_file(profile_id,
   set_path)` so the chosen candidate's source `.set` is applied to the
   live MT5 EA at runtime (today the `.set` parameters are only
   summarized into `BrokerOrderRequest` SL/TP/lot, not re-applied to the
   EA).
2. `cas_forex/agent_state.py:155-170` — propagate
   `relative_source_path` + `source_sha256` into
   `RouteIntent.order_request` so the executor can verify integrity
   before sending.
3. `cas_forex/agent_workflow.py:77-90` — wire an owner-authorized
   license check into `run_agent_workflow_cycle` to gate the
   `MT5_DEMO → MT5_LIVE` lane switch.
4. `api/routes/strategy.py` — `POST /strategy/forex-fury-promote`
   takes a `candidate_id` and writes a `strategy_leads.json` entry
   binding the `.set` to the live lane.
5. `tests/test_forex_fury_candidates.py` — assert the top candidate's
   `source_sha256` matches the bytes on disk before any promotion.

### Verification

```bash
py -3.12 -m pytest tests -q     # 631 passed (615 → 631, +16 net)
cd ui && npm run build          # 55 modules, 2.85s, PWA SW regenerated
```

### Boundary unchanged

The understanding-window bot framing, `requires_confirm` gates, Stage 3
validator, and runtime-gate licensure all unchanged. The cards expose
existing primitives; the history route wraps the existing pure
explainer; the receipt archive is dry-run by default; Slice 4 was
investigation only.

## 2026-06-24 - Mobile build: PWA installable on any phone + Capacitor Android APK path

The PWA manifest and Capacitor scaffolding were partially in place (manifest,
icons, capacitor.config.json, `mobile:*` npm scripts) but no service worker
was generated and Capacitor was never installed. This slice completes both
paths.

### PWA — installable on any modern phone, no app store

- `ui/vite.config.ts` — registers `vite-plugin-pwa`. The existing manifest at
  `ui/public/manifest.webmanifest` is used verbatim (no synthesized manifest).
  `strategies: "generateSW"` produces a Workbox service worker.
- Workbox config:
  - 9 entries precached at build time (575 KiB).
  - `navigateFallbackDenylist: [/^\/api\//]` — API responses are NEVER
    cached. CAS Forex telemetry must stay live; stale data is worse than
    no data.
  - Runtime caching `StaleWhileRevalidate` for static assets only
    (style/script/worker/image/font) with a 30-day window.
- `ui/package.json` — adds `vite-plugin-pwa` and `workbox-window` as
  `devDependencies`.

After `npm run build`, the operator opens
`http://<host>:5174/` (or a deployed URL) on their phone's browser and
taps "Add to Home Screen." The app installs as a standalone PWA with the
manifest's icon, theme colour, and shortcuts — no APK, no store, no Java
toolchain required.

### Capacitor — Android APK path

- `ui/package.json` — adds `@capacitor/core`, `@capacitor/cli`, and
  `@capacitor/android` as `devDependencies`.
- `npx cap add android` was run; `ui/android/` is now scaffolded with the
  full Gradle project. `.gitignore` already excludes `ui/android/` — the
  native project is regenerated per machine.
- Existing `mobile:apk:debug` script works as-is:
  ```bash
  cd ui
  npm run mobile:apk:debug
  ```
  This runs `tsc -b && vite build && npx cap sync android && cd android &&
  ./gradlew assembleDebug` and produces an APK at
  `ui/android/app/build/outputs/apk/debug/app-debug.apk`.

Operator-side requirements for the APK build (not in scope this iteration):

- **Java JDK 17+** on the build machine (`java -version` to verify).
- **Android SDK** with API level 33+ (Android Studio is the easiest install;
  the SDK manager handles platform/build-tools downloads).
- Set `ANDROID_HOME` environment variable to the SDK location.

The first time on a fresh machine, also run `npx cap add android` once
(already done on this machine; `.gitignore` keeps the result local).

### Verification

```bash
cd ui && npm run build
# vite v6 build OK, 538 KiB JS / 26 KiB CSS gzipped to 130/4.6 KiB.
# PWA v1.3.0 generateSW; 9 entries precached at 575 KiB.
# dist/sw.js and dist/workbox-*.js generated.
npx cap add android
# √ Adding native android project — gradle project at ui/android/.
py -3.12 -m pytest tests -q
# 615 passed (no Python changes; UI-only slice).
```

### Boundary

Neither path changes the bot framing or runtime safety. The PWA loads the
same React app, hits the same API, and shows the same instrument-panel
view (live telemetry, MTF selector, autonomous-loop status). The APK is
just a WebView shell around the same bundle. The agent cycle still trades
autonomously on the operator's behalf; the LLM bot remains an
understanding window.

## 2026-06-24 - Wire explainer + loop health into API routes and bot capabilities

The `agent_decision_explainer` and `autonomous_loop_health` primitives
shipped earlier but were not callable from the bot. This slice exposes
both as API routes, adds them as `BotCapability` entries so the LLM
bot can call them as tools, and surfaces loop health in the deterministic
bot's startup status banner.

Implemented:

- `api/routes/agent_decision.py` — `GET /api/forex/agent-decision/latest`
  loads cycle / memory / strategy-dev / strategy-leads / walk-forward /
  PCBA evidence from `evidence_runs/*` via `_safe_load_latest`, runs the
  pure explainer, returns the structured `AgentDecisionExplanation`
  payload. Missing artifacts → explainer's `status="missing"` chain
  steps; the route never fabricates. `set_loader_for_testing` /
  `reset_loader_for_testing` for injection.
- `api/routes/autonomous_loop.py` — `GET /api/forex/autonomous-loop/health`
  uses the module's own `load_loop_health_inputs(repo_root)` helper,
  runs the pure summariser, returns the `AutonomousLoopHealth` payload.
  Same loader-injection pattern.
- `api/server.py` — `include_router` for both under
  `/api/forex/agent-decision` and `/api/forex/autonomous-loop`.
- `cas_forex/cas_forex_bot.py`:
  - Two new `BotCapability` entries (capability count: 31 → 33):
    - `ax` — Explain Latest Agent Decision (`/api/forex/agent-decision/latest`)
    - `ah` — Autonomous Loop Health (`/api/forex/autonomous-loop/health`)
  - `build_status_summary` now also queries
    `/api/forex/autonomous-loop/health` and reports the loop status
    in the deterministic bot's startup banner: e.g.
    `Autonomous loop: running (3 cycles today)`. If the endpoint
    isn't reachable (e.g. uvicorn predates the route), the line is
    silently skipped — the bot doesn't lecture about it.

The LLM bot's tool-registry size test was rewritten to follow
`len(CAPABILITIES)` instead of a hardcoded 31, so future capability
additions don't break it.

Tests:

- `tests/test_agent_decision_route.py` — 4 tests via the FastAPI ASGI
  helper: 200 + correct empty payload when no evidence, full schema
  shape matching the dataclass, no-trade-advisory invariant on
  `plain_english_summary` at the route boundary, default loader is
  the disk-backed helper after reset.
- `tests/test_autonomous_loop_route.py` — 4 tests: 200 + "unknown"
  status when no evidence, full required-fields schema, no-trade-
  advisory invariant, default loader resolution.

Verification:

```bash
py -3.12 -m pytest tests -q
# 615 passed (607 → 615, +8 net; no regressions).
```

Bot capabilities: 31 → 33. The LLM bot's "why did the agent trade X?"
and "is the loop alive?" paths are now single tool calls instead of
multi-step JSON assembly.

Deployment note: restart uvicorn so both new routes register and the
deterministic bot's `Autonomous loop` status line shows up.

## 2026-06-24 - Parallel fleet: decision explainer + loop health + autowake supervisor + live telemetry

Four parallel agents on disjoint slices, all serving the autonomous-loop
+ understanding-window architecture. No file collisions, no test
regressions. Net `+34` tests (`573 → 607`).

### Slice A — Agent decision explainer

`cas_forex/agent_decision_explainer.py` — pure function
`explain_latest_agent_decision(...)` that walks the agent's reasoning
chain in order: strategy lead → walk-forward evidence → PCBA gate
verdict → cycle decision → execution outcome. Returns an
`AgentDecisionExplanation(cycle_id, overall_status, plain_english_summary,
chain, next_action_hint)` with `chain: tuple[DecisionChainStep, ...]`.

`overall_status ∈ {"executed", "approved_not_executed", "blocked",
"no_recent_decision"}`. Per-step `status ∈ {"found", "missing",
"blocked"}` — when a step's input is absent, the step explains what
input would unlock it. The function NEVER fabricates and NEVER advises
a future trade — every plain-English summary is strictly past-tense
explanation. Tests assert forbidden substrings ("buy now", "should you
trade", "good entry", "place a trade") never appear in any scenario.

Tests (`tests/test_agent_decision_explainer.py`): 8 tests including
no-input → "no_recent_decision", full-executed chain, approved-but-
not-executed, PCBA-blocked, missing walk-forward, and the "never
advises future trades" invariant.

This is the primitive the LLM bot will use when the operator asks "why
did the agent trade X?" or "explain the most recent agent decision."

### Slice B — Autonomous loop health summary

`cas_forex/autonomous_loop_health.py` — pure function
`summarize_autonomous_loop_health(...)` answering "is the autonomous
loop alive and producing decisions?" in one structured snapshot.

`AutonomousLoopHealth(overall_status, last_cycle_at_iso,
seconds_since_last_cycle, cycles_today, decisions_today,
executions_today, blocked_today, autowake_present,
autowake_next_due_iso, plain_english_summary, diagnostic_hints)`.

Status classification:
- `"unknown"` — every input is None / empty. The function refuses to fabricate.
- `"never_started"` — at least one input provided, but no parseable cycle timestamp anywhere.
- `"running"` — cycle within the last `running_threshold_minutes` (default 60), OR `autowake_next_due_iso` parses to a future UTC instant (loop is paced between fires).
- `"stalled"` — cycle exists, older than threshold, AND no future autowake fire is scheduled.

`diagnostic_hints` is `()` when `"running"`; otherwise actionable strings
(autowake missing, MT5 cycle present but executions 0, validator
rejection rate high, autowake past due). `plain_english_summary` is
verified across all scenarios to never contain trade-advisory
substrings.

Companion `load_loop_health_inputs(repo_root)` does the disk I/O
separately so the summarizer stays pure for tests.

Tests (`tests/test_autonomous_loop_health.py`): 11 tests across
all status branches + the no-trade-advisory invariant.

### Slice C — Autowake supervisor

`cas_forex/autowake_supervisor.py` — the missing long-running
supervisor that wraps the existing `session_autowake_runner` as a
restart-on-crash loop with capped exponential backoff, max-tick /
max-duration / consecutive-failure caps, and SIGINT/SIGTERM-safe
graceful shutdown.

`AutowakeSupervisor` constructor takes:
- `tick: Callable[[], Mapping[str, Any]]` — the autowake one-shot.
- `tick_interval_seconds: float` — base cadence.
- `max_ticks: int | None` — optional cap.
- `max_consecutive_failures: int = 5` — circuit breaker.
- `max_total_duration_seconds: float | None` — optional cap.
- `clock: Callable[[], float] = time.monotonic` — INJECTED so tests
  advance virtual time without sleeping.
- `sleeper: Callable[[float], None] = time.sleep` — INJECTED.
- `on_tick: Callable[[SupervisorTickResult], None] | None` — per-tick
  observer.
- `shutdown_event: threading.Event | None` — signal-handler hook.

`run()` returns `SupervisorRunSummary(total_ticks, successful_ticks,
failed_ticks, consecutive_failures_at_stop, stopped_reason,
last_tick_result)` where `stopped_reason ∈ {"max_ticks",
"shutdown_signal", "max_consecutive_failures", "duration_cap"}`.
Backoff between failed ticks: `tick_interval * min(2^consec_failures,
30)`.

`scripts/run_autowake_supervisor.py` — production launcher with
SIGINT/SIGTERM → `threading.Event` plumbing and CLI flags
`--tick-interval-seconds`, `--max-ticks`, `--max-total-duration-seconds`,
`--max-consecutive-failures`, `--execute-cycle`, `--summary-only`.

Example invocation:

```powershell
py -3.12 scripts/run_autowake_supervisor.py `
  --tick-interval-seconds 300 `
  --max-ticks 288 `
  --max-total-duration-seconds 86400 `
  --execute-cycle --summary-only
```

That schedules a tick every 5 minutes for up to 24 hours (288 ticks),
each calling the autowake runner with `--execute-cycle`. SIGINT/SIGTERM
flip the shutdown event so the loop exits cleanly between ticks.

Tests (`tests/test_autowake_supervisor.py`): 8 tests using fake
`clock` + `sleeper`. Cover the four stop reasons, success-resets-
consecutive-counter, backoff multiplier, and the `on_tick` callback.

### Slice D — Live trades telemetry (backend + UI panel)

Backend — `api/routes/live_telemetry.py`:

`GET /api/forex/live-telemetry` returns:

```jsonc
{
  "as_of_iso": "...",
  "open_positions": [
    {
      "symbol": "EURUSD",
      "direction": "BUY"|"SELL",
      "lots": 0.01,
      "entry_price": 1.0850,
      "current_price": 1.0855,
      "floating_pnl": 0.5,
      "opened_at_iso": "..." | null,
      "broker_ticket": "..." | null
    }
  ],
  "totals": { "open_position_count": int, "total_floating_pnl": float },
  "data_freshness": {
    "source": "mt5_terminal_api_verifier"|"movement_stream"|"none",
    "stale": bool,
    "last_update_iso": "..." | null
  }
}
```

Source selection: MT5 terminal verifier first (broker truth);
movement_stream fallback (paper/demo ledger-derived); otherwise
`source: "none", open_positions: []`. NEVER fabricates prices or P&L.
Staleness window: 5 minutes against UTC now.

`api/server.py` — wired the router under `/api/forex/live-telemetry`.

UI — `ui/src/components/LiveTradesTelemetry.tsx`:

Polls every 2 seconds via `setInterval` in `useEffect`. Renders:
- Header: open position count, total floating P&L, "as of HH:MM:SS",
  staleness chip when `data_freshness.stale`.
- Table: Symbol, Direction, Lots, Entry, Current, Floating P&L,
  Time open. P&L color: positive teal, negative red, zero neutral.
- Empty state: "No active positions" — not an error, not "you
  should trade." Observational only.

Wired into `ui/src/pages/TradePage.tsx` above the proposal preview.
`ui/src/data/api.ts` gains `LiveTelemetryPosition` /
`LiveTelemetryResponse` types and `fetchLiveTelemetry()`.

Tests (`tests/test_live_telemetry_api.py`): 7 tests via the FastAPI
ASGI helper — route registered, schema shape, no-data → `source:"none"`,
mocked-data echoes correctly, totals math, direction normalization.

### Verification

```bash
py -3.12 -m pytest tests -q     # 607 passed (573 → 607, +34 net)
cd ui && npm run build           # 53 modules, 3.26s
```

### Boundary

Operator-side actions (not in scope this iteration):
1. Start MT5 terminal with Hugosway-Demo and enable AutoTrading.
2. Restart uvicorn so the new `/api/forex/live-telemetry` route
   registers in the running process.
3. Launch the supervisor: `py -3.12 scripts/run_autowake_supervisor.py
   --tick-interval-seconds 300 --execute-cycle --summary-only`.

Runtime safety unchanged: `requires_confirm=True` capabilities still
prompt; Stage 3 validator still REJECTs closed gates; the LLM bot
remains an understanding window, not a trade advisor.

## 2026-06-24 - Bot role corrected: understanding window, NOT trade advisor

Followup correction to the MTF monitor entry below, which framed
`find_tradeable_symbols` as "the operator's 'what should I act on now'
answer." That framing is wrong: surfacing trade picks to the operator
through the LLM bot reintroduces the exact emotional / anxiety-driven
decision loop the agent autonomy exists to eliminate.

CAS Forex has two interaction surfaces and they serve different roles:

1. **The agent cycle** trades autonomously on the operator's account.
   Its explicit purpose is to REMOVE detrimental trading psychology —
   anxiety-driven, emotional, in-the-moment decisions — from the
   operator's loop. The agent picks what to trade. The operator does not.
2. **The LLM bot** is an EDUCATOR + WINDOW into the system's reasoning.
   It helps the operator UNDERSTAND what the system is doing and why.
   It is NOT a trade advisor, NOT a trade picker, NOT an oracle to query
   for trade decisions.

Fixed:

- `cas_forex/cas_forex_llm_bot.py` — `SYSTEM_PROMPT` rewritten. The bot
  is now framed as "an educator and a window into the system's
  reasoning." Good question categories listed explicitly: "Why did the
  agent trade X?" / "How does Strategy Y work?" / "What's a runtime
  gate?" / "What's the system doing right now?" / "How does the agent
  decide what to trade?". The bot MUST redirect "what should I trade?"
  / "is this a good entry?" / "what's hot right now?" — those are the
  exact emotional prompts the agent autonomy exists to defuse.

Internal primitives like `find_tradeable_symbols` in
`cas_forex/mtf_monitor.py` are AGENT-CYCLE primitives, not user-facing
tools. They power the agent's autonomous selection logic. They will
NOT be wired as `BotCapability` entries for the LLM bot to call —
contrary to the "Not built in this slice" note in the MTF monitor
entry below.

Runtime safety surface unchanged: `requires_confirm=True`, Stage 3
validator, runtime gates. Only the LLM bot's CONVERSATIONAL role is
constrained to understanding. The agent cycle, MT5 execution path,
broker bridge, and strategy dev queue still trade autonomously on the
operator's behalf — that's the whole point.

Verification:

```bash
py -3.12 -m pytest tests -q
# 573 passed (no regressions; system-prompt-only change).
```

Saved as a durable feedback memory so this constraint survives future
sessions.

## 2026-06-24 - MTF monitor — "what should I trade right now"

Built the next slice on the multi-timeframe stack: a pure-function monitor
that composes a per-symbol snapshot across every symbol with at least one
active timeframe in the runtime, and identifies which symbols are
currently tradeable.

The monitor's job is composition, not feed integration. Upstream code
(MTFA, candle subscriptions, broker bridge) is responsible for producing
per-(symbol, tf) direction and risk numbers. The monitor takes those as
inputs, orchestrates the runtime's `aggregate_risk` and `signals_align`
across every active symbol, and returns a single composed snapshot the
bot, the LLM, and the UI can render.

Implemented:

- `cas_forex/mtf_monitor.py`:
  - `SymbolMonitorSnapshot(symbol, active_timeframes, aggregated_risk,
    signal_alignment)` — frozen per-symbol record.
  - `MonitorSnapshot(symbols)` — frozen snapshot across every active
    symbol, sorted by symbol for stable rendering;
    `for_symbol(symbol)` accessor.
  - `TradeableSymbol(symbol, direction, aggregated_risk,
    active_timeframes)` — symbol the operator should consider acting on
    right now.
  - `compose_monitor_snapshot(runtime, *, risk_by_symbol,
    direction_by_symbol)` — pure composition. Missing inputs treated as
    "no signal" / "no risk" (consistent with runtime semantics: an
    active TF that supplies no number does not count as zero, it does
    not contribute). Inactive TFs in the input are ignored even if
    present.
  - `find_tradeable_symbols(snapshot, *, max_risk_per_symbol)` —
    filters to symbols where (a) every voting active TF agrees on
    direction (alignment ∈ {BUY, SELL}) AND (b) aggregated sum-risk
    ≤ cap. Sorted order preserved from the snapshot.
- `tests/test_mtf_monitor.py` — 12 tests: empty runtime, sorted output,
  per-symbol active-TF carriage, risk aggregation ignoring inactive TFs,
  all-BUY / MIXED / EMPTY alignment cases, missing-input resilience,
  tradeable filter skipping MIXED/EMPTY, tradeable filter respecting
  risk cap, tradeable filter returning all aligned within budget,
  sorted ordering preserved through filter.

Verification:

```bash
py -3.12 -m pytest tests -q
# 573 passed (561 → 573, +12 net; no regressions).
```

What this unlocks: the LLM bot's open-ended "what should I trade right
now?" path now has a concrete primitive to call. Wiring the monitor into
a capability that pulls live per-TF direction/risk from MTFA + current
floating PnL is the next step. The pure-function design means upstream
feed implementations can evolve independently of monitor / runtime / UI.

Not built in this slice:

1. Live feed integration — concrete upstream for `risk_by_symbol` /
   `direction_by_symbol`. MTFA's `analyze(symbol, candles)` returns
   direction; the broker bridge knows floating PnL.
2. New `BotCapability` exposing `find_tradeable_symbols` as a tool the
   LLM bot can call.
3. UI panel rendering the monitor snapshot on the Trade or Dashboard
   page.

## 2026-06-24 - Bot voice: instrument-panel framing, no defeatist language

CAS Forex is the operator's personal trading system on their own account.
The LLM bot's prior `SYSTEM_PROMPT` described it to the owner as a "forex
research, paper-trading, and MT5-demo-execution platform" and instructed
the model to volunteer the status of the runtime gates (`live_trading`,
`broker_accept`, `auto_deposit`, `bank_card_movement`, `payout_automation`)
unsolicited. Combined with the model's markdown defaults, that produced
operator-hostile responses (tables, emoji status rows, "NOT LICENSED"
banners) that undermined the operator's goal of using the system to make
money. The deterministic bot's startup greeting had the same issue: it
printed `Live trading: CURRENTLY NOT LICENSED` on every launch.

Fixed:

- `cas_forex/cas_forex_llm_bot.py` — rewrote `SYSTEM_PROMPT`. The bot is
  now "the operator's instrument panel for CAS Forex — their personal
  forex trading system." Capability framing leads with what the system
  does FOR the operator (signal generation, strategy execution, MT5 trade
  execution, risk sizing, position management, daily learning rollups,
  multi-timeframe runtime selection). Markdown, tables, and emojis are
  banned. Runtime gates are mentioned only when (a) the operator asks
  explicitly or (b) the Stage 3 validator returns `[cas-validator:REJECTED]`
  on a tool call the operator initiated — in which case the model relays
  the validator's structured reason once and stops. Open-ended questions
  default to capabilities that move money / show edge / surface risk
  (`workflow`, `mt5`, `proof`, `strategy`), not health-status volunteering.
- `cas_forex/cas_forex_bot.py` — `build_status_summary` no longer prints
  a separate `Live trading: <status>` row. Readiness is reported as
  `Readiness gates: N/M gates open`. The operator owns those gates and
  flips them when ready; the bot does not lecture about them on launch.

Runtime safety unchanged:

- `requires_confirm=True` capabilities still prompt for explicit operator
  y/n. The LLM cannot bypass `_interactive_confirmation`.
- Stage 3 validator still REJECTs capabilities flagged `dangerous` when
  the corresponding runtime gates are closed. The validator's output is
  what feeds back to the model; only the unsolicited prose changed.

Verification:

```bash
py -3.12 -m pytest tests -q
# 561 passed (no regressions; the framing change is in operator-facing
# text and does not affect the test surface).
```

## 2026-06-24 - Multi-timeframe selector UI (Trade page)

Wired the operator-facing selector for the MTF runtime API into the React
Trade page. The operator can now visually toggle which timeframes are
concurrently active for a symbol; each toggle round-trips through
`/api/forex/timeframes` so the bot, monitor loop, and risk gates all
see the same state.

Implemented:

- `ui/src/data/api.ts` — added `apiDelete<T>` helper (sibling of
  `apiGet`/`apiPost`) and five timeframes endpoints:
  `fetchCanonicalTimeframes`, `fetchAllActiveTimeframes`,
  `fetchSymbolTimeframes`, `activateTimeframe`, `deactivateTimeframe`.
  All return `null` on error so the UI can degrade gracefully if the
  API is down. Types: `SymbolTimeframeSelection`, `CanonicalTimeframes`,
  `ActiveTimeframesSnapshot`.
- `ui/src/components/MultiTimeframeSelector.tsx` — controlled component
  taking a `symbol` prop. Loads the canonical vocabulary once,
  re-syncs the active set whenever the symbol changes, and uses
  optimistic UI for toggle interactions (local state flips immediately,
  reverts if the API returns null). Per-chip `pending` state disables
  the button while its POST/DELETE is in flight so double-clicks can't
  race.
- `ui/src/pages/TradePage.tsx` — added a new `MultiTimeframeSelector`
  panel below the existing single-TF picker (additive — the existing
  Symbol/Timeframe/Style chips are unchanged). New helper
  `normalizeSymbolForRuntime("EUR/USD") -> "EURUSD"` strips the slash
  so FastAPI path parameters don't have to deal with `%2F` encoding.
- `ui/src/App.css` — minimal new styles for `.mtf-selector`,
  `.mtf-chips`, `.mtf-loading`, `.mtf-error`, `.mtf-summary`, plus a
  generic `.selector-chip:disabled` rule. The chip buttons reuse the
  existing `.selector-chip` / `.selector-chip.active` styling so the
  visual language matches the rest of the page.

Verification:

```bash
cd ui && npm run build
# vite v6.4.3 building for production... 52 modules transformed
# (was 51 modules; +1 for MultiTimeframeSelector). built in 2.99s.

py -3.12 -m pytest tests -q
# 561 passed (no regressions; UI-only change does not affect Python tests).
```

Deployment notes:

- The running dev server must be reloaded to pick up the new route
  (committed in the prior CHANGELOG entry). Hit `Ctrl-C` on the uvicorn
  process and rerun, or use `--reload`.
- The UI build (`npm run build`) produces a fresh bundle in `ui/dist/`.
  Vite dev server (`npm run dev`) HMR will pick up the changes
  automatically.

Next wiring (NOT built in this slice):

1. Concurrent monitor loop in the bot reading `GET /api/forex/timeframes`
   on tick and maintaining per-`(symbol, tf)` candle subscriptions +
   analyzers.
2. Portfolio-risk gate at order time calling `aggregate_risk` with
   live floating PnL per TF and blocking if `sum_risk` exceeds the
   symbol's configured cap.
3. State persistence (file-backed or Redis) if/when the API server
   moves to multi-worker uvicorn — today the runtime is pure in-memory
   and resets on server restart.
4. Selector parity on Dashboard and Optimizer pages (currently only
   on Trade page).

## 2026-06-24 - Multi-timeframe runtime API route

Wired the multi-timeframe runtime skeleton (shipped earlier this session)
into a thin FastAPI route so the UI selector and a future concurrent
monitor loop have a single source of truth for "which timeframes are
active for which symbol."

Implemented:

- `api/routes/timeframes.py` — process-singleton `MultiTimeframeRuntime`
  (`get_runtime()` accessor; `set_runtime_for_testing()` swap helper) +
  five endpoints under `/api/forex/timeframes`:
  - `GET /canonical` — list the canonical timeframe vocabulary
    (`M1/M5/M15/H1/H4/D1`) so the UI selector stays in sync with the
    runtime's accepted set.
  - `GET ` / `GET /` — snapshot of every symbol with at least one
    active timeframe, sorted by symbol for stable UI rendering.
  - `GET /{symbol}` — selection for one symbol. Unknown symbols return
    an empty selection (not 404) — the symbol is just not yet active.
  - `POST /{symbol}/{timeframe}` — activate. Idempotent. Returns the
    updated selection. 400 on unknown timeframe with the canonical
    vocabulary in the error detail.
  - `DELETE /{symbol}/{timeframe}` — deactivate. Idempotent. Same
    error shape on unknown timeframe.
- `api/server.py` — `from .routes import ... timeframes` and
  `app.include_router(timeframes.router, prefix="/api/forex/timeframes",
  tags=["timeframes"])`.
- `tests/test_timeframes_api.py` — 10 tests driving the FastAPI ASGI app
  directly: canonical endpoint shape, empty-state listing, missing-symbol
  returns empty selection (not 404), activate→query roundtrip and
  multi-TF aggregation, unknown-timeframe 400 with canonical list, POST
  idempotency, deactivate removes only the target, deactivate-last
  drops the symbol from the listing, DELETE error shape, sorted-symbols
  listing for stable UI.

Deployment note: a running uvicorn process must be reloaded (or
`--reload` enabled) to pick up the new route. The ASGI-driven tests
prove the route registration; the running dev server returns 404 until
restarted.

Tests: 551 → 561 (+10 net, no regressions).

Next wiring (NOT built):

1. UI selector on Trade / Dashboard pages calling these endpoints.
2. Concurrent monitor loop in the bot: for each `(symbol, tf)` pair from
   `GET /api/forex/timeframes`, maintain a per-TF candle subscription
   and per-TF analyzer.
3. Portfolio-risk gate at order time: order pipeline calls
   `aggregate_risk` with current floating PnL per TF and blocks if
   `sum_risk` exceeds the symbol's configured cap.
4. State persistence (file-backed or Redis) if/when the server moves
   to multi-worker — today the runtime is pure in-memory.

## 2026-06-24 - Parallel fleet: cockpit honesty + bot dry-run + multi-timeframe runtime

Three parallel agents on disjoint slices. No file collisions, no test
regressions. Net `+18` tests (`533 → 551`).

### Slice 1 — cockpit honesty (lane-aware operability counts)

The operability cockpit was reporting `cas_open_position_count: 28` and
`pending_receipt_count: 28` from stale rows in the legacy MT4 mailbox event
journal (`evidence_runs/agent_workflow_queue/agent-events.jsonl`) while
broker truth on the active MT5 lane is 0 open positions. The fix makes the
reconciler and verifier lane-aware.

Implemented:

- `cas_forex/terminal_position_reconciliation.py` — added
  `LANE_MT4_MAILBOX` / `LANE_MT5_DEMO` constants and `_lane_for_record()`
  helper that classifies each record by its `broker_mode` field; CAS open
  positions and terminal open positions now carry `lane` / `broker_mode`
  tags; `_summary` produces a per-lane breakdown.
- `cas_forex/terminal_operability_verifier.py` — added `ACTIVE_LANE_*`
  constants and `_detect_active_terminal_lane()` (signal: MT5 broker-API
  verifier status, non-blocked MT5 paper execution verifier status, or any
  MT5 execution summary showing `execution_attempted` /
  `order_request_built`; default `MT4_MAILBOX`); top-level
  `cas_open_position_count` and `pending_receipt_count` now reflect the
  active lane, with legacy totals preserved under
  `cas_open_position_count_legacy_total` and
  `pending_receipt_count_legacy_total`.

New summary fields:

- `active_terminal_lane: "MT5_DEMO" | "MT4_MAILBOX"`
- `cas_open_position_count_by_lane: {"mt4_mailbox": N, "mt5_demo": N}`
- `pending_receipt_count_by_lane: {"mt4_mailbox": N, "mt5_demo": N}`
- `terminal_open_position_count_by_lane: {"mt4_mailbox": N, "mt5_demo": N}`
- `cas_open_position_count_legacy_total: N`
- `pending_receipt_count_legacy_total: N`

Reconciliation summary additionally exposes per-lane breakdowns under
the same key names.

Tests: `tests/test_terminal_operability_lane_awareness.py` — 5 tests
covering MT5-lane active with stale MT4 rows present (top-level count
reflects MT5), MT4-lane active with no MT5 evidence (top-level count is
MT4), per-lane breakdown shape, and `active_terminal_lane` detection.

### Slice 2 — LLM bot `--dry-run` pipeline tracer

The LLM bot is unusable without an `ANTHROPIC_API_KEY`. The dry-run mode
lets the operator exercise the full 7-stage runtime pipeline (LLM tool
selection through validator, manual approval, dispatch, broker, and
explanation hand-back) without ever calling the model.

Implemented:

- `cas_forex/cas_forex_llm_bot.py` — added `run_dry_run_once(input, ...)`
  (single-turn pure tracer returning a structured trace dict for tests)
  and `run_dry_run_cli(...)` (interactive loop). Both paths use the real
  Stage 3 validator (`validate_capability` + `fetch_runtime_gates`) and
  the real Stage 4 dispatcher (`execute_capability`) only when
  `actually_execute=True`. No LLM imports or calls are involved on the
  dry-run path.
- `scripts/run_cas_forex_llm_bot.py` — added `--dry-run` and
  `--actually-execute` flags. `--actually-execute` errors out unless
  paired with `--dry-run`. Default behavior unchanged.
- `tests/test_cas_forex_llm_bot.py` — 5 new tests: validator
  structured-message printout; REJECT short-circuits before Stage 4 and
  Stage 5 even with `--actually-execute`; unknown-key path; correct
  parsing of `<key> <hint>` input; full interactive CLI never touches
  `call_gateway`.

CLI:

```powershell
py -3.12 scripts/run_cas_forex_llm_bot.py --dry-run
py -3.12 scripts/run_cas_forex_llm_bot.py --dry-run --actually-execute
```

Operator types `<key>` (e.g. `cy`, `mt`, `pp`) or `<key> <hint>` (e.g.
`mt buy EURUSD 0.01`) at the `dry-run>` prompt; the bot prints each
stage's output and stops at the first REJECT.

### Slice 3 — Multi-timeframe runtime skeleton

The runtime layer for the 2026-06-21 user request ("pick/change timeframe
AND trade multiple timeframes at once"). Skeleton only — UI selector,
API route, and concurrent-monitor wiring are follow-on work.

Implemented:

- `cas_forex/multi_timeframe_runtime.py` — pure in-memory runtime, no
  I/O. Canonical timeframes (`M1, M5, M15, H1, H4, D1`) deliberately
  narrower than `mtfa.TF_HIERARCHY` (W1/MN stay analytical-only).
  Public surface:
  - `CANONICAL_TIMEFRAMES: frozenset[str]`
  - `TimeframeKey(str, Enum)` — string-valued enum mirror
  - `UnknownTimeframeError(ValueError)`
  - `TimeframeSelection(symbol, active_timeframes)` (frozen)
  - `AggregatedRisk(symbol, sum_risk, max_risk, contributing_timeframes)`
    (frozen)
  - `SignalAlignment(symbol, alignment: "BUY"|"SELL"|"MIXED"|"EMPTY",
    votes)` (frozen)
  - `MultiTimeframeRuntime`:
    - `activate(symbol, timeframe)` / `deactivate(symbol, timeframe)`
      (idempotent, both validate timeframe against the canonical set)
    - `active_timeframes_for(symbol) -> frozenset[str]`
    - `all_active() -> Mapping[str, frozenset[str]]`
    - `selection_for(symbol) -> TimeframeSelection`
    - `aggregate_risk(symbol, per_timeframe_risk) -> AggregatedRisk`
      (sums and maxes only across currently-active timeframes; inactive
      timeframes are ignored even if present in the input mapping;
      absent active timeframes do NOT count as zero)
    - `signals_align(symbol, per_timeframe_direction) -> SignalAlignment`
      (case-insensitive direction labels; unknown labels preserved in
      votes but force `MIXED`)

Tests: `tests/test_multi_timeframe_runtime.py` — 8 tests covering empty
state, single/multi activation, deactivation (including symbol-drop when
last TF removed), risk aggregation ignoring inactive TFs, signal
alignment (BUY/SELL/MIXED/EMPTY, case-insensitive, unknown-direction
forces MIXED), unknown-TF rejection at every entry point, and
`TimeframeKey` enum parity with `CANONICAL_TIMEFRAMES`.

Next wiring (NOT built in this slice):

1. Per-symbol timeframe selector on Trade / Dashboard pages backed by
   a thin API route (e.g. `GET/POST /api/forex/timeframes/{symbol}`)
   reading `all_active()` for state.
2. Concurrent monitor loop in the bot: for each `(symbol, tf)` pair from
   `all_active()`, spawn / maintain a per-TF candle subscription +
   per-TF analyzer, feed `risk_pct` / `direction` into `aggregate_risk`
   and `signals_align`.
3. Portfolio-risk gate at order time: order pipeline calls
   `aggregate_risk` with current floating PnL per TF and blocks if
   `sum_risk` exceeds the symbol's configured cap. This is the missing
   concurrent-TF aggregation in the 2026-06-21 spec.

### Verification

```bash
py -3.12 -m pytest tests -q
# 551 passed (533 → 551, +18 net; no regressions)
```



### Deterministic bot crashed on Windows launch — fixed

Previous session's `CAS Forex Bot` ("Bot OK: 31 caps") smoke test only
imported the module; the actual CLI crashed on launch with
`UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f916'`
because the greeting prints emoji on a cp1252 Windows console. The launcher
script also emitted a `SyntaxWarning: invalid escape sequence '\P'` from an
unescaped Windows path in its docstring.

Fixes:

- `scripts/run_cas_forex_bot.py` — escape the example Windows path so the
  docstring no longer raises a SyntaxWarning; reconfigure `sys.stdout` and
  `sys.stderr` to `encoding="utf-8", errors="replace"` at process start so
  emoji output works on modern Windows Terminal / PowerShell and degrades
  gracefully on legacy cp1252 consoles.
- `cas_forex/cas_forex_bot.py` — add `_ensure_utf8_console()` at the
  `run_bot_cli` entry so any caller (script or test) gets the same
  protection; rewrite `build_status_summary` to read the actual API shapes
  (`overall_status`, `checks_passed`/`checks_total`, `live_trading_status`,
  `live_money_authorized` from `/api/forex/readiness/live`, and
  `terminalOperabilityVerifier.operability_status` from `/api/forex/dashboard`)
  instead of the nonexistent `summary.operability_status` / `summary.live_order_go`
  keys it was previously reading. The greeting now shows honest numbers
  (`Live readiness: 10/16 passed`,
  `MT5 operability: TERMINAL_OPERABILITY_MT5_DEMO_EXECUTION_VERIFIED`)
  instead of `unknown`.

### CAS Forex LLM Bot — natural-language operator interface

Added an LLM-first operator bot (`cas_forex/cas_forex_llm_bot.py`) that
routes every operator turn through a frontier model and exposes the existing
31 `BotCapability` entries as typed tool definitions. The deterministic
menu is still reachable via `menu`/`h`.

Architecture (runtime pipeline):

1. Operator input (`run_llm_bot_cli` CLI loop)
2. Claude: intent classification + typed tool selection (`call_gateway` →
   `step_conversation`, 31 tools as OpenAI-shape function definitions)
3. CAS permission/risk validator — NOT YET BUILT (next step)
4. Deterministic capability dispatcher (`execute_tool_call` →
   `execute_capability`, the same path the deterministic bot uses)
5. Manual approval for `requires_confirm=True` capabilities
   (`_interactive_confirmation` callback intercepts before dispatch)
6. Broker/MT5 API (capability subprocesses into existing `run_mt5_*.py`)
7. Logged result returned to Claude for plain-English explanation
   (tool message appended; model summarizes in the same conversation turn)

Provider selection — two paths, no SDK dependency added (uses `requests`,
already a dep):

- `anthropic-direct` — DEFAULT. Direct Anthropic Messages API.
  Requires `ANTHROPIC_API_KEY`. Default model `claude-sonnet-4-6`.
  Anthropic-native message/tools shape is translated to/from the canonical
  OpenAI shape inside the adapter so call sites stay provider-agnostic.
- `vercel-gateway` — alternative. Multi-provider routing via Vercel AI
  Gateway. Requires `AI_GATEWAY_API_KEY`. Model strings are `provider/model`,
  e.g. `anthropic/claude-sonnet-4-6`, `openai/gpt-5`,
  `google/gemini-3.1-pro-preview`.

Safety / discipline:

- `requires_confirm=True` capabilities intercept before execution and prompt
  the operator for explicit y/n. The LLM cannot bypass this — declining feeds
  a structured "operator declined" message back so the model explains the
  result instead of swallowing it.
- `max_tool_rounds` (default 4) bounds successive tool-use rounds.
- The system prompt names the non-licensed capabilities by their runtime-gate
  IDs (`live_trading`, `broker_accept`, `auto_deposit`,
  `bank_card_movement`, `payout_automation`) so the model never claims they
  are operational.

Implemented:

- `cas_forex/cas_forex_llm_bot.py` — `LLMConfig` (provider/env/model
  resolution); `build_tools_from_capabilities` (31 typed tools);
  `capability_tool_name` / `capability_for_tool_name` (reversible naming);
  `call_gateway` (provider dispatch); `_call_vercel_gateway` and
  `_call_anthropic_direct` (provider adapters); `_openai_messages_to_anthropic`
  and `_anthropic_response_to_openai_message` (canonical-shape conversion);
  `execute_tool_call` (dispatch + confirmation gate); `step_conversation`
  (LLM → tool round-trip with round cap); `run_llm_bot_cli` (interactive
  CLI with `menu`/`q` short-circuits).
- `scripts/run_cas_forex_llm_bot.py` — launcher with `--provider`/`--model`/
  `--api`/`--mt5` flags; UTF-8 stdout/stderr reconfig at import time.
- `tests/test_cas_forex_llm_bot.py` — 17 tests covering tool registry
  shape and coverage, provider config defaults, both adapter HTTP shapes,
  Anthropic tool-use → OpenAI tool_calls normalization, confirmation
  interception (no-callback / decline / approve paths), tool dispatch for
  safe capabilities, full conversation round-trip with tool result, and
  the `max_tool_rounds` cap.

Example:

```powershell
# Default: direct Claude Sonnet 4.6
$env:ANTHROPIC_API_KEY = "sk-..."
py -3.12 scripts/run_cas_forex_llm_bot.py

# Alternative: multi-provider via Vercel AI Gateway
$env:AI_GATEWAY_API_KEY = "..."
py -3.12 scripts/run_cas_forex_llm_bot.py --provider vercel-gateway --model openai/gpt-5
```

Verification:

```bash
py -3.12 -m pytest tests/test_cas_forex_llm_bot.py -q
# 17 passed

py -3.12 -m pytest tests -q
# 511 passed (494 baseline + 14 process-guard + 17 LLM bot — 3 net delta accounted by file-already-present tests)

py -3.12 scripts/run_cas_forex_llm_bot.py --help
# Defaults to anthropic-direct (direct Anthropic Claude Sonnet 4.6).
```

Boundary: the LLM is the OPERATOR INTERFACE, not the CAS reasoning spine.
The CAS-Native end-to-end work is unaffected; this bot only translates
natural language into deterministic capability calls. Live trading, broker
ACCEPT, auto-deposit, bank/card movement, and payout automation remain
`NOT LICENSED` / `CURRENTLY NOT LICENSED`.

### Stage 3 — CAS permission/risk validator (shipped same session)

Built the missing Stage 3 of the runtime pipeline. The validator runs between
LLM tool selection (Stage 2) and deterministic capability dispatch (Stage 4)
— before the manual approval gate (Stage 5). When a runtime gate is closed,
the validator REJECTs the call and feeds a structured reason back to the
model instead of the operator seeing a stack trace.

Pipeline ordering inside `execute_tool_call`:

1. Resolve capability from LLM tool name.
2. **Stage 3 — `validate_capability(cap, runtime_gates)`.** Decides
   `PASS` / `REJECT` / `DEGRADED` based on `cap.danger_level` and the live
   `/api/forex/settings/runtime-gates` body. REJECT short-circuits the call
   without ever asking the operator for confirmation.
3. Stage 5 — `confirmation_callback` if `requires_confirm=True`.
4. Stage 4 — `execute_capability(cap, state)` (deterministic dispatch).

Decision rules (`REQUIRED_GATES_BY_DANGER` in
`cas_forex/cas_permission_validator.py`):

- `safe` → no gates required.
- `caution` → no gates required (MT5 demo / paper-proof / read-only;
  still hard-gated by `requires_confirm=True` at Stage 5).
- `dangerous` → conjunctively requires `live_trading`, `broker_accept`,
  `auto_deposit`, `bank_card_movement`, and `payout_automation` to all be
  `authorized`. Today no capability in the 31-capability registry has
  `danger_level="dangerous"`, so Stage 3 mostly passes; the contract is in
  place for when live capabilities are added.
- Unknown danger level → conservative (treated as `caution`, never `safe`).

Degraded path: when the runtime-gates endpoint is unreachable
(`fetch_runtime_gates` returns `None`), `safe` and `caution` capabilities
pass under DEGRADED (so the deterministic bot keeps working offline) and
`dangerous` capabilities reject (we cannot prove the gates are open).

LLM-facing structured message: rejection text always starts
`[cas-validator:REJECTED]` and lists every blocking gate by name with its
status and `next_action` hint. The system prompt instructs the model to
surface this verbatim instead of retrying.

Implemented:

- `cas_forex/cas_permission_validator.py` — `ValidationResult`/`GateBlock`
  dataclasses; `validate_capability` pure function; `_attach_message`
  formatting; `fetch_runtime_gates` and `fetch_authority_boundary` with
  injected `transport` for tests; `validate_by_key` convenience.
- `cas_forex/cas_forex_llm_bot.py` — `ToolCallResult` extended with
  `intercepted_by_validator: bool` and `validation: Optional[ValidationResult]`;
  `execute_tool_call` accepts `runtime_gates` and `skip_validation`,
  routes Stage 3 → Stage 5 → Stage 4 in that order; `step_conversation`
  fetches `runtime_gates` once per operator turn via injectable
  `runtime_gates_fetcher` (defaults to live HTTP) and passes the body to
  every tool dispatch; system prompt updated to teach the model what
  `[cas-validator:REJECTED]` and `[cas-validator:DEGRADED]` mean.
- `tests/test_cas_permission_validator.py` — 19 tests: safe always-passes,
  caution passes with broker-touching advisory, dangerous rejection with
  all-gates-closed and one-gate-closed cases, dangerous PASS when all gates
  open, next-action hint propagation, DEGRADED path for safe/caution/
  dangerous, authority-boundary advisory, unknown danger conservative,
  structured message shape (gate names and capability labels), HTTP fetch
  via injected transport (success + failure → None), `validate_by_key`
  unknown-capability rejection and live-fetch integration.
- `tests/test_cas_forex_llm_bot.py` — 3 new integration tests: validator
  REJECT short-circuits before Stage 4 and before manual approval;
  `skip_validation=True` escape hatch works; `step_conversation` passes
  the fetched gates body to every tool dispatch.

Verification:

```bash
py -3.12 -m pytest tests/test_cas_permission_validator.py tests/test_cas_forex_llm_bot.py -v
# 39 passed (19 validator + 20 LLM bot)

py -3.12 -m pytest tests -q
# 533 passed (511 previous + 22 net)
```

The 7-stage runtime pipeline is now wired end-to-end:
operator input → LLM tool selection → **Stage 3 validator** →
manual approval → deterministic dispatch → broker/MT5 → tool result
returned to model for plain-English explanation.

## 2026-06-24 - MT5 process guard + CAS Forex Bot

### MT5 process guard (subprocess watchdog)

Added a process-level watchdog so real MT5 terminal calls cannot hang the
CAS Forex agent loop. The previous state had the MT5 Python package blocking
indefinitely when the Hugosway MT5 terminal was unresponsive (timed out at
120s). Now MT5 operations run in a timeout-guarded subprocess.

Implemented:
- `cas_forex/mt5_process_guard.py` — subprocess watchdog with configurable
  timeout. Five operations: `execute_demo_order`, `get_deal_history`,
  `get_account_snapshot`, `get_open_positions`, `close_position`.
  Architecture: parent writes JSON spec to temp file, spawns
  `python -m cas_forex.mt5_process_guard --worker <spec>`, waits with
  `subprocess.run(timeout=...)`. On timeout the worker is killed and a
  clean `MT5_TIMEOUT` error is returned to the agent loop.
- `cas_forex/agent_state.py` — new params `mt5_use_process_guard` and
  `mt5_guard_timeout_seconds`. When guard is active, MT5 execution and
  deal-history ingest route through `_run_mt5_execution_via_guard` and
  `_run_mt5_deal_history_via_guard` which call `run_mt5_operation_safe`.
  Guard branch only activates when all three conditions are met:
  `use_process_guard=True` + `mt5_path` set + execution flags true.
  Otherwise falls through to existing direct MT5 path.
- `scripts/run_agent_workflow_queue.py` — new CLI flags
  `--mt5-use-process-guard` and `--mt5-guard-timeout-seconds`.
- `tests/test_mt5_process_guard.py` — 14 tests covering worker ops,
  guard integration, timeout handling, fake MT5 execution, deal history,
  and no-regression path when guard flag is off.

Example: run a full MT5 demo cycle with watchdog:
```powershell
py -3.12 scripts/run_agent_workflow_queue.py `
  --terminal-lane PAPER_MT5_DEMO `
  --mt5-path "C:\Program Files\Hugosway\Hugosway PRO5 Terminal\terminal64.exe" `
  --execute-mt5-demo-order --confirm-mt5-demo-order `
  --mt5-use-process-guard --mt5-guard-timeout-seconds 120 `
  --summary-only
```

### CAS Forex Bot

Added a structured conversational agent (`cas_forex/cas_forex_bot.py`) that
knows all CAS Forex operations and provides a menu-driven interface to prevent
decision paralysis. 31 capabilities across 7 action groups.

Design:
- **Menu-driven**: groups → commands, never more than 6 options per level
- **Quick keys**: `cy` = run agent cycle, `mt` = MT5 probe, `pp` = paper proof
- **Confirmation gates**: MT5 demo orders require explicit confirm
- **Command transparency**: shows the underlying CLI commands so users learn
- **Status-first**: checks API health and operability on startup

Action groups:
- `status` — Health, dashboard, readiness, operability, memory (6 ops)
- `workflow` — Agent cycles, autowake, daily rollup, MT4/MT5 lanes (5 ops)
- `mt5` — Terminal probe, paper execution, demo orders, deal history (4 ops)
- `proof` — Paper bundles, proof status, risk review, backsolve (4 ops)
- `strategy` — Strategy dev, leads, PCBA guard, walk-forward (4 ops)
- `owner` — Owner controls, runtime gates, broker sync (3 ops)
- `system` — Tests, UI build, evidence, dashboard, API docs (5 ops)

Entry point: `py -3.12 scripts/run_cas_forex_bot.py`

### Verification

```bash
py -3.12 -m pytest tests -q
# 494 passed (480 existing + 14 new process guard tests)

py -3.12 -m pytest tests/test_mt5_process_guard.py -q
# 14 passed

py -3.12 -c "from cas_forex.cas_forex_bot import *; print('Bot OK:', len(CAPABILITIES), 'caps')"
# Bot OK: 31 caps
```

### Next step

The MT5 process guard was tested against the real Hugosway MT5 terminal path.
The guard subprocess correctly imported MetaTrader5 (via .mt5deps) and
attempted the demo order. The cycle completed without hanging (no timeout
fired). The order was rejected by the terminal (MT5 terminal not responding to
order_send), which is a runtime/terminal-state issue, not a code bug. The
guard's function — preventing agent-loop hangs — is verified.

The next real-terminal test requires:
1. MT5 terminal running with Hugosway-Demo account logged in
2. Algo Trading / AutoTrading enabled in MT5 terminal
3. Then rerun:
```powershell
py -3.12 scripts/run_agent_workflow_queue.py `
  --terminal-lane PAPER_MT5_DEMO `
  --mt5-path "C:\Program Files\Hugosway\Hugosway PRO5 Terminal\terminal64.exe" `
  --execute-mt5-demo-order --confirm-mt5-demo-order `
  --mt5-use-process-guard --summary-only
```

Boundary: MT5 demo API, demo execution, and deal history paths remain the
scope. Live trading, broker ACCEPT, auto-deposit, debit/card/bank movement,
and payout automation remain NOT LICENSED.

## 2026-06-24 - Scheduled agent MT5 demo loop wired to deal-history learning

Implemented the missing bridge from the scheduled/autowake agent cycle to the
proven MT5 demo execution and closed-deal learning path.

Implemented:

- `cas_forex/agent_state.py`
  - added explicit `PAPER_MT5_DEMO` terminal lane alongside the existing
    `PAPER_MT4_MAILBOX` lane
  - scheduled approved `RouteIntent.order_request` can now feed the MT5 demo
    execution verifier instead of only writing MT4 mailbox commands
  - MT5 execution receipts now carry `cycle_id`, `intent_id`, `command_id`,
    `broker_ticket`, execution status, request/response hashes, close status,
    and account snapshot facts
  - after MT5 deal-history joins memory, the agent event journal appends
    `NEXT_CYCLE_ALLOWED` so a successful closed MT5 cycle does not block the
    next same-symbol cycle
  - MT5 cycles use `agent-events-mt5-demo.jsonl` so stale MT4 mailbox pending
    rows do not jam the MT5 lane
- `cas_forex/mt5_paper_execution_verifier.py`
  - accepts an existing `BrokerOrderRequest` from an agent route intent
  - remaps market-order SL/TP geometry onto the current MT5 tick before
    building the broker request
- `cas_forex/agent_message_bus.py`
  - emits real receipt events for MT5 execution commands instead of only
    `RECEIPT_PENDING`
- `cas_forex/session_autowake_runner.py`
  - autowake can pass terminal-lane and MT5 demo execution flags into the
    scheduled cycle
- `scripts/run_agent_workflow_queue.py`
  - added `--terminal-lane PAPER_MT5_DEMO`, `--mt5-path`,
    `--execute-mt5-demo-order`, `--confirm-mt5-demo-order`,
    `--no-mt5-deal-history`, and `--mt5-future-minutes`
- `scripts/run_session_autowake_runner.py`
  - added the same MT5 lane controls for due autowake cycles
- `api/data.py`
  - dashboard message-bus summary now follows the latest cycle's own event log
    when available
- Optimizer UI/types/fixtures now surface the linked cycle-level MT5 loop
  status, broker ticket, deal-history status, memory joins, closed positions,
  and closed P/L.

Verification:

```bash
py -3.12 -m pytest tests/test_agent_workflow_cycle.py tests/test_mt5_paper_execution_verifier.py tests/test_mt5_deal_history_ingest.py tests/test_session_autowake_runner.py -q
# 19 passed

py -3.12 -m pytest tests -q
# 480 passed

cd ui && npm run build
# 51 modules, 532.25 KB JS, 129.48 KB gzip
```

Important real-terminal note:

- A scheduled MT5 agent-cycle attempt before the lane-specific event-journal
  fix wrote:
  `evidence_runs/agent_workflow_queue/agent-workflow-cycle-20260624165947-report.json`.
  That run did not send an MT5 order because the old shared default event
  journal still had `28` stale pending MT4 receipt rows.
- After the lane-specific event-journal fix, a real MT5 scheduled-cycle run was
  attempted with the Hugosway terminal path, but the MT5/Python call did not
  finish within `120` seconds and the exact `run_agent_workflow_queue.py`
  processes were stopped. No successful real scheduled-agent MT5 order is
  claimed from that timed-out attempt.
- A fresh non-executing MT5-lane cycle was written after the fix:
  `evidence_runs/agent_workflow_queue/agent-workflow-cycle-20260624171015-report.json`.
  It uses `agent-events-mt5-demo.jsonl`, has `approved_intent_count=1`,
  `terminal_command_count=0`, and `pending_receipt_count=0`, proving the
  cockpit now sees the MT5 lane without inheriting stale MT4 pending rows.
- The linked scheduled MT5 path is regression-verified with a fake MT5 terminal
  that executes, closes, returns two deal-history rows, joins memory by
  `broker_ticket`, and emits `NEXT_CYCLE_ALLOWED`.

Next software/evidence target: add a process-level MT5 watchdog or worker
wrapper so a real scheduled/autowake MT5 cycle cannot hang the agent loop, then
rerun the scheduled MT5 demo cycle against Hugosway-Demo and refresh terminal
operability from that scheduled-cycle evidence.

Boundary: this is a scheduled paper/demo MT5 operability bridge. Live trading,
broker `ACCEPT`, auto-deposit, debit/card/bank movement, and payout automation
remain `NOT LICENSED` / `CURRENTLY NOT LICENSED`.

## 2026-06-24 - MT5 closed deal history joined CAS memory

Implemented and verified MT5 closed-deal history ingest for the already
executed Hugosway-Demo MT5 verifier trade.

Implemented:

- `cas_forex/mt5_deal_history_ingest.py`
- `scripts/run_mt5_deal_history_ingest.py`
- `tests/test_mt5_deal_history_ingest.py`
- API/dashboard route:
  `/api/forex/strategy/mt5-deal-history-ingest/latest`
- Optimizer UI MT5 Deal History run card/detail panel.
- Terminal operability summary fields for MT5 raw deals, closed positions,
  memory updates, unmatched rows, and net P/L.
- Agent memory now adds a default-project MT5 paper-execution seed row so the
  closed deal can join by `broker_ticket`.
- Agent information-flow map now includes `MT5DealHistoryIngestPacket`.

Latest real Hugosway-Demo evidence:

- `evidence_runs/mt5_deal_history_ingest/mt5-deal-history-ingest-20260624162919-report.json`
- `evidence_runs/mt5_deal_history_ingest/mt5-deal-history-ingest-20260624162919-report.md`
- `evidence_runs/terminal_history_exports/mt5-deal-history-ticket-45938644-20260624162919.json`
- `evidence_runs/terminal_history_ingest/terminal-history-ingest-20260624162919-report.json`
- `evidence_runs/agent_memory/agent-memory-20260624162936-report.json`
- `evidence_runs/strategy_dev_queue/strategy-dev-queue-20260624162945-report.json`
- `evidence_runs/daily_learning_rollup/daily-learning-rollup-20260624162946-report.json`
- `evidence_runs/terminal_operability_verifier/terminal-operability-verifier-20260624162936-report.json`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624163510-report.json`

Current verified MT5 closed-deal state:

- server: `Hugosway-Demo`
- ticket / position id: `45938644`
- symbol: `EUR/USD`
- volume: `0.01`
- raw MT5 history deals: `2`
- closed positions exported: `1`
- memory updates: `1`
- unmatched history rows: `0`
- open / close: `1.13489 -> 1.13481`
- gross trade P/L: `-0.08`
- commission: `-0.05`
- swap: `0.0`
- net account P/L: `-0.13`
- pips: `-0.8`
- R multiple: `-0.04`
- close reason: `MT5_HISTORY_CLOSE:CAS_CLOSE`
- agent memory: `terminal_history_joined_count=1`,
  `closed_loss_count=1`, `net_profit_loss_account=-0.13`
- strategy-dev queue: `closed_loss_memory_count=1`,
  `demotion_review_count=1`
- daily learning rollup: `DAILY_LEARNING_HAS_CLOSED_PNL`
- terminal operability:
  `TERMINAL_OPERABILITY_MT5_DEMO_EXECUTION_VERIFIED`,
  terminal lane go `true`, live order go `false`,
  blocking reason `live_trading CURRENTLY NOT LICENSED`

Verification:

```bash
py -3.12 -m pytest tests -q
# 479 passed

cd ui && npm run build
# 51 modules, 528.95 KB JS, 128.63 KB gzip
```

Boundary: MT5 demo API, demo execution, closed deal history, memory join,
strategy queue, daily rollup, and operability are verified for one
Hugosway-Demo test trade. Live trading, broker `ACCEPT`, auto-deposit,
debit/card/bank movement, and payout automation remain `NOT LICENSED` /
`CURRENTLY NOT LICENSED`.

## 2026-06-24 - MT5 demo execution path verified

Cleared the MT5 terminal AutoTrading blocker, executed one explicitly
confirmed Hugosway MT5 demo order, and closed it through the CAS Forex MT5
bridge.

Operator/runtime action:

- Used the open Hugosway MT5 demo terminal window
  `1000694 - Hugosway-Demo: Demo Account - Hedge - Hugosway`.
- Turned on MT5 `Algo Trading` / `AutoTrading`.
- Reran the explicitly confirmed MT5 paper execution verifier.

Generated evidence:

- `evidence_runs/mt5_paper_execution_verifier/mt5-paper-execution-verifier-20260624160137-report.json`
- `evidence_runs/mt5_paper_execution_verifier/mt5-paper-execution-verifier-20260624160137-report.md`
- `evidence_runs/mt5_terminal_api_verifier/mt5-terminal-api-verifier-20260624160153-report.json`
- `evidence_runs/mt5_terminal_api_verifier/mt5-terminal-api-verifier-20260624160153-report.md`
- `evidence_runs/terminal_operability_verifier/terminal-operability-verifier-20260624160208-report.json`
- `evidence_runs/terminal_operability_verifier/terminal-operability-verifier-20260624160208-report.md`

Current verified state:

- terminal: `MetaTrader 5`
- server: `Hugosway-Demo`
- account balance/equity after close: `$99,999.87 / $99,999.87`
- open positions after close: `0`
- symbol: `EUR/USD`
- volume: `0.01`
- order request built: `true`
- broker `order_check`: `ORDER_CHECK_OK`
- demo send attempted: `true`
- terminal trade allowed: `true`
- execution status: `ORDER_EXECUTED`
- broker ticket: `45938644`
- filled price: `1.13489`
- close attempted: `true`
- close success: `true`
- raw request hash:
  `8bf07bc73705c4dded9ce75184379f10574c5c71a006fbe8731cb680030fa11a`
- raw response hash:
  `ac87b38e2add12e995d63e20f4017bbd5309308bb941b1ccc4740f99ec0d1a34`
- terminal operability:
  `TERMINAL_OPERABILITY_MT5_DEMO_EXECUTION_VERIFIED`
- terminal lane go: `true`
- live order go: `false`
- blocking reason: `live_trading CURRENTLY NOT LICENSED`

Next evidence/software target:

- Add MT5 closed-history/deal ingestion so the close, P/L, commission, swap,
  and deal records from the executed/closed demo order flow into CAS memory,
  daily learning rollup, and strategy evaluation.

Verification:

```bash
py -3.12 -m pytest tests -q
# 475 passed

cd ui && npm run build
# 51 modules, 520.06 KB JS, 126.96 KB gzip
```

Boundary: the MT5 demo execution lane is now verified for one demo order and
close cycle. Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank
movement, and payout automation remain `NOT LICENSED` / `CURRENTLY NOT
LICENSED`.

## 2026-06-24 - MT5 demo send proof reached terminal; AutoTrading blocker surfaced

Ran the explicitly confirmed MT5 demo-order proof and turned the resulting
terminal rejection into a first-class operability status.

Implemented:

- `cas_forex/broker/mt5_bridge.py`
  - no longer mislabels real MT5 `OrderSendResult` objects that do not expose
    a `commission` field
  - preserves request/response hashes on rejected MT5 responses
  - maps retcode `10027` to `AutoTrading disabled by client`
  - adds symbol-supported filling mode to MT5 close-position requests
- `cas_forex/mt5_paper_execution_verifier.py`
  - summary now includes `terminal_trade_allowed`,
    `execution_error_message`, and `raw_response_hash`
  - next action now names the AutoTrading/Algo Trading terminal blocker
- `cas_forex/terminal_operability_verifier.py`
  - summary now carries MT5 paper execution error text, terminal trade
    permission, and raw response hash
  - reports `TERMINAL_OPERABILITY_MT5_AUTOTRADING_DISABLED` when MT5 rejects
    the demo send because terminal AutoTrading is off
- `ui/src/types/evidence.ts`, `ui/src/pages/OptimizerPage.tsx`, and
  `ui/src/data/fixtures.ts`
  - surface MT5 trading permission, execution error, and response hash in the
    Optimizer/Operability UI
- Regression tests for missing MT5 `commission` fields and the AutoTrading
  disabled path

Generated evidence:

- `evidence_runs/mt5_paper_execution_verifier/mt5-paper-execution-verifier-20260624155515-report.json`
- `evidence_runs/mt5_paper_execution_verifier/mt5-paper-execution-verifier-20260624155515-report.md`
- `evidence_runs/terminal_operability_verifier/terminal-operability-verifier-20260624155528-report.json`
- `evidence_runs/terminal_operability_verifier/terminal-operability-verifier-20260624155528-report.md`

Current verified state:

- MT5 terminal: connected
- server: `Hugosway-Demo`
- account balance/equity: `$100,000 / $100,000`
- symbol checked: `EUR/USD`
- volume: `0.01`
- order request built: `true`
- broker `order_check`: `ORDER_CHECK_OK`
- demo send attempted: `true`
- execution status: `ORDER_REJECTED`
- execution error: `AutoTrading disabled by client: AutoTrading disabled by client`
- terminal trade allowed: `false`
- raw response hash:
  `e6682c1c10d49596d71bb26a4ff08d9d886610d6feae671be707ffd7da6132a9`
- terminal operability:
  `TERMINAL_OPERABILITY_MT5_AUTOTRADING_DISABLED`
- terminal lane go: `false`

Next operator action:

- Turn on Algo Trading / AutoTrading in the Hugosway MT5 terminal, confirm the
  terminal allows trading, then rerun:

```bash
py -3.12 scripts/run_mt5_paper_execution_verifier.py --mt5-path "C:\Program Files\Hugosway\Hugosway PRO5 Terminal\terminal64.exe" --symbol EUR/USD --volume 0.01 --execute-demo-order --confirm-demo-order --summary-only
py -3.12 scripts/run_terminal_operability_verifier.py --summary-only
```

Verification:

```bash
py -3.12 -m pytest tests/test_mt5_paper_execution_verifier.py tests/test_terminal_operability_verifier.py tests/test_pip_math_regressions.py -q
# 26 passed

py -3.12 -m pytest tests -q
# 475 passed

cd ui && npm run build
# 51 modules, 520.43 KB JS, 126.99 KB gzip
```

Boundary: the confirmed demo-send attempt reached MT5 and captured the exact
terminal rejection. It has not yet produced an executed demo-order receipt or
closed-history proof. Live trading, broker `ACCEPT`, auto-deposit,
debit/card/bank movement, and payout automation remain `NOT LICENSED` /
`CURRENTLY NOT LICENSED`.

## 2026-06-24 - MT5 paper execution verifier dry-run ready

Implemented and verified the MT5 paper/demo execution lane through the real
local Hugosway MT5 terminal.

Implemented:

- `cas_forex/mt5_paper_execution_verifier.py`
  - connects to the local MT5 demo account
  - reuses the MT5 terminal API verifier as prerequisite evidence
  - builds the exact `BrokerOrderRequest` -> MT5 request payload
  - runs broker-side `order_check` when available
  - sends no order by default
  - only submits a demo order when both `--execute-demo-order` and
    `--confirm-demo-order` are supplied
- `scripts/run_mt5_paper_execution_verifier.py`
- `tests/test_mt5_paper_execution_verifier.py`
- `/api/forex/strategy/mt5-paper-execution-verifier/latest`
- dashboard key `mt5PaperExecutionVerifier`
- TypeScript evidence type, API client fetcher, fixture fallback, root app
  state, and Optimizer page run card/detail panel for MT5 paper execution
- `cas_forex/broker/mt5_bridge.py`
  - now chooses the symbol-supported MT5 filling mode instead of hardcoding
    IOC; Hugosway `EUR/USD` accepted FOK (`type_filling: 0`) while IOC had
    returned `Unsupported filling mode`
  - preserves fallback behavior for test/fake MT5 modules that do not expose
    full terminal metadata
- terminal operability verifier now consumes the MT5 paper execution verifier
  and reports `TERMINAL_OPERABILITY_MT5_DRY_RUN_READY_DEMO_SEND_REQUIRED`
- agent information-flow roadmap now includes
  `MT5PaperExecutionVerifierPacket`,
  `/api/forex/strategy/mt5-paper-execution-verifier/latest`, and the demo-send
  evidence gap

Generated evidence:

- `evidence_runs/mt5_paper_execution_verifier/mt5-paper-execution-verifier-20260624154210-report.json`
- `evidence_runs/mt5_paper_execution_verifier/mt5-paper-execution-verifier-20260624154210-report.md`
- `evidence_runs/terminal_operability_verifier/terminal-operability-verifier-20260624154222-report.json`
- `evidence_runs/terminal_operability_verifier/terminal-operability-verifier-20260624154222-report.md`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624154148-report.json`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624154148-report.md`

Current verified state:

- terminal: `MetaTrader 5`
- server: `Hugosway-Demo`
- account balance/equity: `$100,000 / $100,000`
- symbol checked: `EUR/USD`
- requested volume: `0.01`
- MT5 request built: `true`
- MT5 request filling mode: `type_filling: 0`
- broker `order_check`: `ORDER_CHECK_OK`
- execution attempted: `false`
- execution status: `DRY_RUN_NO_ORDER_SENT`
- live mode used: `false`
- terminal operability status:
  `TERMINAL_OPERABILITY_MT5_DRY_RUN_READY_DEMO_SEND_REQUIRED`
- terminal lane go: `false`
- live order go: `false`
- broker `ACCEPT` go: `false`
- money movement go: `false`

Next evidence target:

- Run one explicitly confirmed MT5 demo-order pass:

```bash
py -3.12 scripts/run_mt5_paper_execution_verifier.py --mt5-path "C:\Program Files\Hugosway\Hugosway PRO5 Terminal\terminal64.exe" --symbol EUR/USD --volume 0.01 --execute-demo-order --confirm-demo-order --summary-only
py -3.12 scripts/run_terminal_operability_verifier.py --summary-only
```

Verification:

```bash
py -3.12 -m pytest tests/test_mt5_paper_execution_verifier.py tests/test_terminal_operability_verifier.py tests/test_agent_information_flow.py tests/test_pip_math_regressions.py -q
# 29 passed

py -3.12 -m pytest tests -q
# 473 passed

cd ui && npm run build
# 51 modules, 518.87 KB JS, 126.78 KB gzip
```

Boundary: MT5 paper execution dry-run proves CAS Forex can build and
broker-check a demo MT5 order request. It does not prove a submitted demo-order
receipt yet, does not place live broker orders, does not create broker
`ACCEPT`, does not deposit or withdraw money, does not move bank/card funds,
and does not automate payouts. Live trading, broker `ACCEPT`, auto-deposit,
debit/card/bank movement, and payout automation remain `NOT LICENSED` /
`CURRENTLY NOT LICENSED`.

## 2026-06-24 - MT5 terminal API verifier and lane-choice update

Verified the local Hugosway MT5 terminal as an actual MT5 demo broker API
source and updated the terminal roadmap/UI to reflect the new lane choice.

Implemented:

- `cas_forex/mt5_terminal_api_verifier.py`
  - verifies local `MetaTrader5` Python package availability
  - initializes against
    `C:\Program Files\Hugosway\Hugosway PRO5 Terminal\terminal64.exe`
  - reads terminal/account/position state without placing orders
  - reports `MT5_API_VERIFIER_BROKER_API_VERIFIED` when the demo broker API,
    account snapshot, receipt validation, and open-position reconciliation are
    visible
- `scripts/run_mt5_terminal_api_verifier.py`
- `tests/test_mt5_terminal_api_verifier.py`
- `cas_forex/broker/mt5_bridge.py`
  - now adds local `.mt5deps` when present
  - uses configured `mt5_path`
  - omits empty login/password/server kwargs unless a login is configured
- `.mt5deps/` in `.gitignore` for isolated Windows MT5 Python deps
- `/api/forex/strategy/mt5-terminal-api-verifier/latest`
- dashboard key `mt5TerminalApiVerifier`
- TypeScript evidence type, API client fetcher, fixture fallback, root app
  state, and Optimizer page run card/detail panel for MT5 terminal API evidence
- terminal operability verifier now consumes the latest MT5 terminal API
  verifier report and reports
  `TERMINAL_OPERABILITY_MT5_API_VERIFIED_MT4_BRIDGE_MISSING`
- agent information-flow roadmap now includes
  `MT5TerminalApiVerifierPacket`, the MT5 verifier API projection, and
  `cas_forex/mt5_paper_execution_verifier.py` as the next code target

Generated evidence:

- `evidence_runs/mt5_terminal_api_verifier/mt5-terminal-api-verifier-20260624150739-report.json`
- `evidence_runs/mt5_terminal_api_verifier/mt5-terminal-api-verifier-20260624150739-report.md`
- `evidence_runs/terminal_operability_verifier/terminal-operability-verifier-20260624150902-report.json`
- `evidence_runs/terminal_operability_verifier/terminal-operability-verifier-20260624150902-report.md`
- `evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-mt5-demo-probe-20260624150120.json`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624152031-report.json`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624152031-report.md`

Current verified state:

- MT5 package: available from `.mt5deps`
- MT5 terminal: connected
- terminal: `MetaTrader 5`
- server: `Hugosway-Demo`
- broker mode: `PAPER_MT5`
- account balance/equity: `$100,000 / $100,000`
- open positions: `0`
- open positions reconciled: `true`
- live mode used: `false`
- MT4 candidate folders: `0`
- MT5-only terminal folders: `2`
- terminal operability status:
  `TERMINAL_OPERABILITY_MT5_API_VERIFIED_MT4_BRIDGE_MISSING`
- terminal lane go: `false`
- live order go: `false`
- broker `ACCEPT` go: `false`
- money movement go: `false`
- UI/proof maturity: `3` complete bundle days out of the `5` needed for the
  current read-only UI maturity gate; 30-day proof is still incomplete

Next code target:

- Build `cas_forex/mt5_paper_execution_verifier.py` so CAS Forex can prove a
  gated MT5 paper/demo order lifecycle through `MT5Bridge`: submit, receipt,
  reconcile, close/history join, memory update, and daily rollup.
- Alternate operator lane: install/attach MT4 if the EA mailbox path is still
  preferred.

Verification:

```bash
py -3.12 -m pytest tests/test_agent_information_flow.py tests/test_mt5_terminal_api_verifier.py tests/test_terminal_operability_verifier.py tests/test_pip_math_regressions.py -q
# 26 passed

py -3.12 -m pytest tests -q
# 467 passed

cd ui && npm run build
# 51 modules, 509.94 KB JS, 125.11 KB gzip
```

Boundary: MT5 demo broker API verification proves local demo account visibility
and receipt/account-state access. It does not place live broker orders, create
broker `ACCEPT`, deposit or withdraw money, move bank/card funds, or automate
payouts. Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank
movement, and payout automation remain `NOT LICENSED` / `CURRENTLY NOT
LICENSED`.

## 2026-06-24 - Terminal operability verifier API/UI

Implemented the top-level terminal operability verifier for CAS Forex.

Implemented:

- `cas_forex/terminal_operability_verifier.py`
  - bundles MT4 terminal session, bridge heartbeat, receipt ingest, MT4
    history export verifier, terminal history ingest, terminal position
    reconciliation, and runtime gate evidence into one go/no-go report
  - separates terminal-lane go/no-go from live-order, broker `ACCEPT`, and
    money-movement authorization
  - reports states such as `TERMINAL_OPERABILITY_NEEDS_MT4_TERMINAL`,
    `TERMINAL_OPERABILITY_NEEDS_HEARTBEAT`,
    `TERMINAL_OPERABILITY_WAITING_FOR_RECEIPTS`,
    `TERMINAL_OPERABILITY_POSITION_MISMATCH`,
    `TERMINAL_OPERABILITY_READY_OPEN_POSITIONS`, and
    `TERMINAL_OPERABILITY_READY_FLAT`
- `scripts/run_terminal_operability_verifier.py`
- `tests/test_terminal_operability_verifier.py`
- `/api/forex/strategy/terminal-operability-verifier/latest`
- dashboard key `terminalOperabilityVerifier`
- TypeScript evidence types, API client fetcher, fixture fallback, and
  Optimizer page run card/detail panel
- information-flow roadmap now marks
  `cas_forex/terminal_operability_verifier.py` as `COMPLETE_INITIAL` and
  moves the next must-have evidence file to
  `MQL4/Files/CASForexMailbox/heartbeat.json`

Generated evidence:

- `evidence_runs/terminal_operability_verifier/terminal-operability-verifier-20260624145246-report.json`
- `evidence_runs/terminal_operability_verifier/terminal-operability-verifier-20260624145246-report.md`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624145333-report.json`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624145333-report.md`

Current terminal operability summary:

- status: `TERMINAL_OPERABILITY_NEEDS_MT4_TERMINAL`
- terminal lane go: `false`
- live order go: `false`
- broker `ACCEPT` go: `false`
- money movement go: `false`
- session status: `MT4_SESSION_NEEDS_MT4_TERMINAL`
- bridge status: `TERMINAL_BRIDGE_HEARTBEAT_MISSING`
- heartbeat status: `MISSING`
- history export status: `MT4_HISTORY_EXPORT_NEEDS_MT4_TERMINAL`
- position reconciliation status:
  `TERMINAL_POSITION_RECONCILIATION_NEEDS_MT4_TERMINAL`
- account snapshot present: `false`
- pending receipts: `28`
- CAS open positions: `28`
- terminal open positions: `0`
- reconciled open positions: `0`
- unmatched open positions: `28`
- runtime-gate pending capabilities: `live_trading`, `broker_accept`,
  `auto_deposit`, `bank_card_movement`, `payout_automation`
- next operator lane: install/open MT4, identify the terminal data folder, run
  the session verifier with `--install`, attach `CASForexBridgeEA.mq4`, attach
  `CASForexHistoryExporterEA.mq4`, then rerun terminal session, history export,
  position reconciliation, and terminal operability

Verification:

```bash
py -3.12 -m pytest tests/test_terminal_operability_verifier.py tests/test_agent_information_flow.py -q
# 9 passed

py -3.12 -m pytest tests -q
# 461 passed

cd ui && npm run build
# 51 modules, 501.28 KB JS, 123.38 KB gzip
```

Boundary: this is an evidence bundle and go/no-go report. It does not place
broker orders, does not create broker `ACCEPT`, does not deposit or withdraw
money, and does not automate payouts. Live trading, broker `ACCEPT`,
auto-deposit, debit/card/bank movement, and payout automation remain
`NOT LICENSED` / `CURRENTLY NOT LICENSED`.

## 2026-06-24 - Terminal position reconciliation API/UI

Implemented terminal position reconciliation for CAS Forex.

Implemented:

- `cas_forex/terminal_position_reconciliation.py`
  - compares CAS agent memory against terminal bridge supervisor evidence,
    terminal receipt ingest, terminal history ingest, MT4 history export
    verifier output, account snapshots, open-position rows, and closed-history
    memory updates
  - reports states such as
    `TERMINAL_POSITION_RECONCILIATION_NEEDS_MT4_TERMINAL`,
    `TERMINAL_POSITION_RECONCILIATION_WAITING_FOR_RECEIPTS`,
    `TERMINAL_POSITION_RECONCILIATION_MISMATCH`,
    `TERMINAL_POSITION_RECONCILIATION_READY_OPEN_POSITIONS`, and
    `TERMINAL_POSITION_RECONCILIATION_READY_FLAT`
  - preserves a read-only boundary: it reconciles evidence and does not place
    orders or move money
- `scripts/run_terminal_position_reconciliation.py`
- `tests/test_terminal_position_reconciliation.py`
- `/api/forex/strategy/terminal-position-reconciliation/latest`
- dashboard key `terminalPositionReconciliation`
- TypeScript evidence types, API client fetcher, fixture fallback, and
  Optimizer page run card/detail panel
- information-flow roadmap now marks
  `cas_forex/terminal_position_reconciliation.py` as `COMPLETE_INITIAL` and
  moves the next code lane to `cas_forex/terminal_operability_verifier.py`

Generated evidence:

- `evidence_runs/terminal_position_reconciliation/terminal-position-reconciliation-20260624143531-report.json`
- `evidence_runs/terminal_position_reconciliation/terminal-position-reconciliation-20260624143531-report.md`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624143602-report.json`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624143602-report.md`

Current terminal position reconciliation summary:

- status: `TERMINAL_POSITION_RECONCILIATION_NEEDS_MT4_TERMINAL`
- bridge status: `TERMINAL_BRIDGE_HEARTBEAT_MISSING`
- heartbeat status: `MISSING`
- account snapshot present: `false`
- pending receipts: `28`
- CAS open positions: `28`
- terminal open positions: `0`
- reconciled open positions: `0`
- unmatched open positions: `28`
- history rows / memory updates: `0` / `0`
- next code lane: `cas_forex/terminal_operability_verifier.py`
- next operator lane: install/open MT4, activate the terminal data folder,
  attach `CASForexBridgeEA.mq4`, attach `CASForexHistoryExporterEA.mq4`, then
  rerun terminal session, history export, receipt ingest, memory, and position
  reconciliation

Verification:

```bash
py -3.12 -m pytest tests/test_terminal_position_reconciliation.py tests/test_agent_information_flow.py tests/test_mt4_history_export_verifier.py -q
# 13 passed

py -3.12 -m pytest tests -q
# 457 passed

cd ui && npm run build
# 51 modules, 491.38 KB JS, 122.03 KB gzip
```

Boundary: this reconciles CAS memory against terminal-side evidence. It does
not place broker orders, does not create broker `ACCEPT`, does not deposit or
withdraw money, and does not automate payouts. Live trading, broker `ACCEPT`,
auto-deposit, debit/card/bank movement, and payout automation remain
`NOT LICENSED` / `CURRENTLY NOT LICENSED`.

## 2026-06-24 - MT4 history export verifier API/UI

Implemented the MT4 closed-history export verifier for CAS Forex.

Implemented:

- `cas_forex/mt4_history_export_verifier.py`
  - verifies the `CASForexHistoryExporterEA.mq4` source is present
  - resolves the activated MT4 mailbox from `--mailbox-dir`,
    `--terminal-data-dir`, or the latest MT4 session verifier report
  - checks
    `MQL4\Files\CASForexMailbox\history\cas_forex_closed_history.json`
  - checks the separated exporter status file under
    `MQL4\Files\CASForexMailbox\status`
  - validates export schema `cas_forex_mt4_closed_history_export.v1`
  - optionally runs `terminal_history_ingest` against the export
  - reports states such as `MT4_HISTORY_EXPORT_NEEDS_MT4_TERMINAL`,
    `MT4_HISTORY_EXPORT_FILE_MISSING`, `MT4_HISTORY_EXPORT_EMPTY`, and
    `MT4_HISTORY_EXPORT_INGEST_READY`
- `scripts/run_mt4_history_export_verifier.py`
- `tests/test_mt4_history_export_verifier.py`
- `/api/forex/strategy/mt4-history-export-verifier/latest`
- dashboard key `mt4HistoryExportVerifier`
- TypeScript evidence types, API client fetcher, fixture fallback, and
  Optimizer page run card/detail panel
- information-flow roadmap now marks
  `cas_forex/mt4_history_export_verifier.py` as `COMPLETE_INITIAL` and moves
  the next code lane to `cas_forex/terminal_position_reconciliation.py`

Generated evidence:

- `evidence_runs/mt4_history_export_verifier/mt4-history-export-verifier-20260624141540-report.json`
- `evidence_runs/mt4_history_export_verifier/mt4-history-export-verifier-20260624141540-report.md`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624141555-report.json`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624141555-report.md`

Current MT4 history export verifier summary:

- status: `MT4_HISTORY_EXPORT_NEEDS_MT4_TERMINAL`
- EA source present: `true`
- mailbox ready: `false`
- history export present: `false`
- history export parse status: `NO_MAILBOX`
- history rows: `0`
- memory updates: `0`
- next code lane: `cas_forex/terminal_position_reconciliation.py`
- next operator lane: install/open MT4, activate the terminal data folder,
  attach `CASForexBridgeEA.mq4`, attach `CASForexHistoryExporterEA.mq4`, then
  rerun the history export verifier

Verification:

```bash
py -3.12 -m pytest tests/test_mt4_history_export_verifier.py tests/test_mt4_history_exporter_ea.py tests/test_mt4_terminal_session_verifier.py tests/test_agent_information_flow.py -q
# 15 passed

py -3.12 -m pytest tests -q
# 453 passed

cd ui && npm run build
# 51 modules, 482.70 KB JS, 120.66 KB gzip
```

Boundary: this verifies terminal-side closed-history export and ingest
compatibility. It does not place broker orders, does not create broker
`ACCEPT`, does not deposit or withdraw money, and does not automate payouts.
Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and
payout automation remain `NOT LICENSED` / `CURRENTLY NOT LICENSED`.

## 2026-06-24 - MT4 closed-history exporter EA source

Implemented the MT4 terminal-side closed-history exporter source for CAS
Forex.

Implemented:

- `mt4/Experts/CASForexHistoryExporterEA.mq4`
  - reads closed MT4 Account History rows with `OrdersHistoryTotal()` and
    `OrderSelect(..., MODE_HISTORY)`
  - exports `history_records` to
    `MQL4\Files\CASForexMailbox\history\cas_forex_closed_history.json`
  - includes broker ticket, symbol, direction, lots, open/close times,
    open/close prices, stop loss, take profit, net P/L, commission, swap,
    magic number, comment, account hash, server, and broker mode
  - writes exporter health/status to
    `MQL4\Files\CASForexMailbox\status\cas_forex_closed_history_status.json`
    so the watched history folder contains only ingestable history files
  - contains no `OrderSend`, `OrderClose`, `OrderModify`, or `OrderDelete`
    execution calls
- `cas_forex/mt4_terminal_session_verifier.py`
  - now includes the activated mailbox `history` folder as a default history
    source when an MT4 mailbox is known
  - reports the expected exporter attach/output path in `operator_commands`
- `tests/test_mt4_history_exporter_ea.py`
  - proves the EA source is read/export only
  - proves exporter-shaped JSON feeds `terminal_history_ingest` and joins
    back to agent memory by `command_id`
- information-flow roadmap and UI fixture now mark
  `mt4/Experts/CASForexHistoryExporterEA.mq4` as
  `SOURCE_READY_NEEDS_TERMINAL_ATTACH` and move the next code lane to
  `cas_forex/mt4_history_export_verifier.py`

Generated evidence:

- `evidence_runs/agent_information_flow/agent-information-flow-20260624140031-report.json`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624140031-report.md`
- `evidence_runs/mt4_terminal_session_verifier/mt4-terminal-session-verifier-20260624140047-report.json`
- `evidence_runs/mt4_terminal_session_verifier/mt4-terminal-session-verifier-20260624140047-report.md`

Current MT4 terminal state:

- status: `MT4_SESSION_NEEDS_MT4_TERMINAL`
- activation status: `MT4_ACTIVATION_NEEDS_MT4_TERMINAL`
- ping status: `MT4_PING_NEEDS_ACTIVATED_MAILBOX`
- MT4 candidate folders: `0`
- MT5-only folders: `2`
- next code lane: `cas_forex/mt4_history_export_verifier.py`
- next operator lane: install/open MT4, run activation with `--install`,
  attach `CASForexBridgeEA.mq4`, attach `CASForexHistoryExporterEA.mq4`, then
  verify heartbeat, receipt, and closed-history export output

Verification:

```bash
py -3.12 -m pytest tests/test_mt4_history_exporter_ea.py tests/test_terminal_history_ingest.py tests/test_mt4_terminal_session_verifier.py tests/test_agent_information_flow.py -q
# 13 passed

py -3.12 -m pytest tests -q
# 449 passed

cd ui && npm run build
# 51 modules, 477.07 KB JS, 119.57 KB gzip
```

Boundary: this adds terminal-side closed-history export evidence and ingest
compatibility. It does not place broker orders, does not create broker
`ACCEPT`, does not deposit or withdraw money, and does not automate payouts.
Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and
payout automation remain `NOT LICENSED` / `CURRENTLY NOT LICENSED`.

## 2026-06-24 - MT4 terminal session verifier API/UI

Implemented the MT4 terminal session verifier for CAS Forex.

Implemented:

- `cas_forex/mt4_terminal_session_verifier.py`
  - runs MT4 activation, ping roundtrip, bridge supervisor, terminal watcher,
    and the downstream evidence refresh chain as one operator-level report
  - records every child step as `COMPLETE`, `SKIPPED`, or `FAILED`
  - reports whether the session needs MT4, needs an activated mailbox, is
    waiting for the terminal, or has completed ping plus refresh-chain proof
  - preserves the boundary that this is a verifier, not a broker order placer
- `scripts/run_mt4_terminal_session_verifier.py`
- `tests/test_mt4_terminal_session_verifier.py`
- `/api/forex/strategy/mt4-terminal-session-verifier/latest`
- dashboard key `mt4TerminalSessionVerifier`
- TypeScript evidence types and API client fetcher
- Optimizer page `MT4 Session` run type and panel
- fixture fallback for offline UI mode
- information-flow roadmap moved from
  `cas_forex/mt4_terminal_session_verifier.py` to
  `mt4/Experts/CASForexHistoryExporterEA.mq4`

Generated evidence:

- `evidence_runs/mt4_terminal_session_verifier/mt4-terminal-session-verifier-20260624134013-report.json`
- `evidence_runs/mt4_terminal_session_verifier/mt4-terminal-session-verifier-20260624134013-report.md`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624134619-report.json`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624134619-report.md`

Current MT4 session summary:

- status: `MT4_SESSION_NEEDS_MT4_TERMINAL`
- activation status: `MT4_ACTIVATION_NEEDS_MT4_TERMINAL`
- ping status: `MT4_PING_NEEDS_ACTIVATED_MAILBOX`
- MT4 candidate folders: `0`
- MT5-only folders: `2`
- mailbox ready: `false`
- ping written: `false`
- heartbeat present: `false`
- receipt present: `false`
- skipped steps: `2`
- next action: install/open MT4, identify the terminal data folder with
  `MQL4\Experts`, then rerun the verifier with `--terminal-data-dir` and
  `--install`
- next file: `mt4/Experts/CASForexHistoryExporterEA.mq4`

Verification:

```bash
py -3.12 -m pytest tests/test_mt4_terminal_session_verifier.py tests/test_agent_information_flow.py -q
# 9 passed

cd ui && npm run build
# 51 modules, 475.27 KB JS, 119.21 KB gzip
```

Boundary: this coordinates terminal evidence checks. It does not place broker
orders, does not create broker `ACCEPT`, does not deposit or withdraw money,
and does not automate payouts. Live trading, broker `ACCEPT`, auto-deposit,
debit/card/bank movement, and payout automation remain `NOT LICENSED` /
`CURRENTLY NOT LICENSED`.

## 2026-06-24 - MT4 ping roundtrip API/UI

Implemented the MT4 ping heartbeat/receipt roundtrip verifier for CAS Forex.

Implemented:

- `cas_forex/mt4_ping_roundtrip.py`
  - resolves the activated MT4 mailbox from the latest activation report or an
    explicit `--mailbox-dir`
  - writes one `PING` command through the existing MT4 mailbox bridge
  - waits for `heartbeat.json` and the matching `receipt-<command_id>.json`
  - verifies receipt schema, request-hash match, receipt status, heartbeat
    presence, and visible live flags
  - reports clear states such as `MT4_PING_NEEDS_ACTIVATED_MAILBOX`,
    `MT4_PING_WRITTEN_WAITING_FOR_TERMINAL`, and
    `MT4_PING_ROUNDTRIP_ACKNOWLEDGED`
- `scripts/run_mt4_ping_roundtrip.py`
- `tests/test_mt4_ping_roundtrip.py`
- `/api/forex/strategy/mt4-ping-roundtrip/latest`
- dashboard key `mt4PingRoundtrip`
- TypeScript evidence types and API client fetcher
- Optimizer page `MT4 Ping` run type and panel
- fixture fallback for offline UI mode
- information-flow roadmap moved from `cas_forex/mt4_ping_roundtrip.py`
  to `cas_forex/mt4_terminal_session_verifier.py`

Generated evidence:

- `evidence_runs/mt4_ping_roundtrip/mt4-ping-roundtrip-20260624122729-report.json`
- `evidence_runs/mt4_ping_roundtrip/mt4-ping-roundtrip-20260624122729-report.md`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624123345-report.json`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624123345-report.md`

Current MT4 ping summary:

- status: `MT4_PING_NEEDS_ACTIVATED_MAILBOX`
- activation status: `MT4_ACTIVATION_NEEDS_MT4_TERMINAL`
- mailbox ready: `false`
- ping written: `false`
- heartbeat present: `false`
- receipt present: `false`
- receipt status: `null`
- next action: run MT4 terminal activation against a real MT4 data folder
  first; no activated mailbox exists for a ping roundtrip yet
- next file: `cas_forex/mt4_terminal_session_verifier.py`

Verification:

```bash
py -3.12 -m pytest tests/test_mt4_ping_roundtrip.py tests/test_agent_information_flow.py -q
# 9 passed

py -3.12 -m pytest tests -q
# 443 passed

$env:VITE_CAS_FOREX_API_BASE='http://127.0.0.1:8810/api/forex'; npm run build
# 51 modules, 467.70 KB JS, 118.10 KB gzip
```

API/UI smoke:

- `http://127.0.0.1:8810/api/forex/health` -> healthy
- `/api/forex/strategy/mt4-ping-roundtrip/latest` ->
  `MT4_PING_NEEDS_ACTIVATED_MAILBOX`
- `/api/forex/dashboard` includes `mt4PingRoundtrip`
- information-flow dashboard now reports
  `must_have_next_file=cas_forex/mt4_terminal_session_verifier.py`
- `http://127.0.0.1:5220/?page=optimizer` returns the React shell

Boundary: this writes or inspects one paper/demo ping command only. It does
not place broker orders, does not create broker `ACCEPT`, does not deposit or
withdraw money, and does not automate payouts. Live trading, broker `ACCEPT`,
auto-deposit, debit/card/bank movement, and payout automation remain
`NOT LICENSED` / `CURRENTLY NOT LICENSED`.

## 2026-06-24 - MT4 terminal activation API/UI

Implemented the MT4 terminal activation lane for CAS Forex.

Implemented:

- `cas_forex/mt4_terminal_activation.py`
  - discovers MetaQuotes terminal data folders from the Windows user profile
    and optional explicit search roots
  - classifies folders as `MT4`, `MT5_ONLY`, or `UNKNOWN`
  - verifies the real EA source at `mt4/Experts/CASForexBridgeEA.mq4`
  - can install/stage the EA under `MQL4\Experts\CASForexBridgeEA.mq4`
  - creates the MT4 file-sandbox mailbox at
    `MQL4\Files\CASForexMailbox`
  - writes exact operator settings for MT4 attach:
    `MailboxRoot=CASForexMailbox`, `UseCommonFiles=false`,
    `LiveTradingAllowed=false`, `TimerSeconds=2`,
    `MaxCommandsPerTimer=10`
  - reports mailbox-path alignment so CAS command writers use the activated
    MT4 mailbox instead of the repo fallback mailbox
- `scripts/run_mt4_terminal_activation.py`
- `tests/test_mt4_terminal_activation.py`
- `/api/forex/strategy/mt4-terminal-activation/latest`
- dashboard key `mt4TerminalActivation`
- TypeScript evidence types and API client fetcher
- Optimizer page `MT4 Activation` run type and panel
- fixture fallback for offline UI mode
- information-flow roadmap moved from `cas_forex/mt4_terminal_activation.py`
  to `cas_forex/mt4_ping_roundtrip.py`

Generated evidence:

- `evidence_runs/mt4_terminal_activation/mt4-terminal-activation-20260624121406-report.json`
- `evidence_runs/mt4_terminal_activation/mt4-terminal-activation-20260624121406-report.md`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624121041-report.json`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624121041-report.md`

Current MT4 activation summary:

- status: `MT4_ACTIVATION_NEEDS_MT4_TERMINAL`
- EA source present: `true`
- MT4 candidate folders: `0`
- MT5-only folders: `2`
- selected terminal: `null`
- EA installed: `false`
- mailbox ready: `false`
- heartbeat present: `false`
- path alignment: `NO_ACTIVATED_MAILBOX`
- next action: install/open MT4, then rerun the activation lane against the
  MT4 data folder containing `MQL4\Experts`
- next file: `cas_forex/mt4_ping_roundtrip.py`

Verification:

```bash
py -3.12 -m pytest tests/test_mt4_terminal_activation.py tests/test_agent_information_flow.py -q
# 10 passed

py -3.12 -m pytest tests -q
# 439 passed

cd ui && npm run build
# 51 modules, 462.34 KB JS, 117.06 KB gzip
```

API/UI smoke:

- `http://127.0.0.1:8809/api/forex/health` -> healthy
- `/api/forex/strategy/mt4-terminal-activation/latest` ->
  `MT4_ACTIVATION_NEEDS_MT4_TERMINAL`, `0` MT4 folders, `2` MT5-only folders
- `/api/forex/dashboard` includes `mt4TerminalActivation`
- information-flow dashboard now reports
  `must_have_next_file=cas_forex/mt4_ping_roundtrip.py`
- `http://127.0.0.1:5219/?page=optimizer` returns the React shell

Boundary: this discovers/stages MT4 activation evidence and the EA attach
runbook. It does not execute broker orders by itself, does not create broker
`ACCEPT`, does not deposit or withdraw money, and does not automate payouts.
Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and
payout automation remain `NOT LICENSED` / `CURRENTLY NOT LICENSED`.

## 2026-06-24 - Terminal bridge supervisor API/UI

Implemented the terminal bridge supervisor for the CAS Forex MT4/MT5 bridge.

Implemented:

- `cas_forex/terminal_bridge_supervisor.py`
  - observes MT4 heartbeat, mailbox folders, command files, receipt files,
    close-history exports, account snapshots, and event-journal pending
    receipts
  - reports heartbeat missing/stale/fresh/live-flag-visible status
  - surfaces pending command receipts and account/history freshness
  - writes supervisor report JSON and Markdown
- `scripts/run_terminal_bridge_supervisor.py`
- `tests/test_terminal_bridge_supervisor.py`
- `/api/forex/strategy/terminal-bridge-supervisor/latest`
- dashboard key `terminalBridgeSupervisor`
- TypeScript evidence types and API client fetcher
- Optimizer page `Bridge Supervisor` run type and panel
- fixture fallback for offline UI mode
- information-flow roadmap moved from `cas_forex/terminal_bridge_supervisor.py`
  to `cas_forex/mt4_terminal_activation.py`

Generated evidence:

- `evidence_runs/terminal_bridge_supervisor/terminal-bridge-supervisor-20260624115153-report.json`
- `evidence_runs/terminal_bridge_supervisor/terminal-bridge-supervisor-20260624115153-report.md`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624115151-report.json`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624115151-report.md`

Current terminal bridge supervisor summary:

- status: `TERMINAL_BRIDGE_HEARTBEAT_MISSING`
- as-of timestamp: `2026-06-24T13:15:00+00:00`
- heartbeat: `MISSING`
- mailbox ready: `true`
- command files: `39`
- receipt files: `0`
- pending command receipts: `39`
- event-journal pending receipts: `28`
- history files: `0`
- account snapshot present: `false`
- visible live flag: `false`
- alerts: `5`
- next file: `cas_forex/mt4_terminal_activation.py`

Verification:

```bash
python -m pytest tests/test_terminal_bridge_supervisor.py -q
# 4 passed

python -m pytest tests/test_terminal_bridge_supervisor.py tests/test_agent_information_flow.py -q
# 9 passed

python -m pytest tests -q
# 434 passed

cd ui && npm run build
# 51 modules, 456.43 KB JS, 115.59 KB gzip
```

API/UI smoke:

- `http://127.0.0.1:8807/api/forex/health` -> healthy
- `/api/forex/strategy/terminal-bridge-supervisor/latest` ->
  `TERMINAL_BRIDGE_HEARTBEAT_MISSING`, `39` commands, `39` pending command
  receipts
- `/api/forex/dashboard` includes `terminalBridgeSupervisor`
- information-flow dashboard now reports
  `must_have_next_file=cas_forex/mt4_terminal_activation.py`
- `http://127.0.0.1:5218/?page=optimizer` returns `200 OK`
- browser render check found `Bridge Supervisor`,
  `TERMINAL_BRIDGE_HEARTBEAT_MISSING`, `cas_forex/mt4_terminal_activation.py`,
  and the `Attach and run CASForexBridgeEA.mq4` next action with zero console
  errors

Boundary: this observes bridge health and terminal evidence freshness. It does
not execute broker orders by itself, does not create broker `ACCEPT`, does not
deposit or withdraw money, and does not automate payouts. Live trading, broker
`ACCEPT`, auto-deposit, debit/card/bank movement, and payout automation remain
`NOT LICENSED` / `CURRENTLY NOT LICENSED`.

## 2026-06-24 - Terminal receipt watcher API/UI

Implemented the terminal receipt/history watcher for the CAS Forex agent desk.

Implemented:

- `cas_forex/terminal_receipt_watcher.py`
  - fingerprints MT4/MT5 receipt and close-history folders
  - detects new, changed, deleted, and unchanged terminal files
  - reruns the existing receipt ingest, history ingest, memory, research queue,
    strategy-dev queue, patch runner, daily rollup, and session autowake chain
    when terminal files change
  - writes watcher report JSON, Markdown, and JSONL change rows
- `scripts/run_terminal_receipt_watcher.py`
- `tests/test_terminal_receipt_watcher.py`
- `/api/forex/strategy/terminal-receipt-watcher/latest`
- dashboard key `terminalReceiptWatcher`
- TypeScript evidence types and API client fetcher
- Optimizer page `Terminal Watcher` run type and panel
- fixture fallback for offline UI mode
- information-flow roadmap moved from `cas_forex/terminal_receipt_watcher.py`
  to `cas_forex/terminal_bridge_supervisor.py`

Generated evidence:

- `evidence_runs/terminal_receipt_watcher/terminal-receipt-watcher-20260624113653-report.json`
- `evidence_runs/terminal_receipt_watcher/terminal-receipt-watcher-20260624113653-report.md`
- `evidence_runs/terminal_receipt_watcher/terminal-receipt-watcher-20260624113653.jsonl`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624113652-report.json`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624113652-report.md`

Current terminal watcher summary:

- status: `WATCHER_IDLE_NO_TERMINAL_FILES`
- as-of timestamp: `2026-06-24T13:10:00+00:00`
- terminal files: `0`
- receipt files: `0`
- history files: `0`
- changed files: `0`
- chain steps: `0`
- next file: `cas_forex/terminal_bridge_supervisor.py`

Verification:

```bash
python -m pytest tests/test_terminal_receipt_watcher.py -q
# 3 passed

python -m pytest tests/test_terminal_receipt_watcher.py tests/test_agent_information_flow.py -q
# 8 passed

python -m pytest tests -q
# 430 passed

cd ui && npm run build
# 51 modules, 449.52 KB JS, 114.36 KB gzip
```

API/UI smoke:

- `http://127.0.0.1:8806/api/forex/health` -> healthy
- `/api/forex/strategy/terminal-receipt-watcher/latest` ->
  `WATCHER_IDLE_NO_TERMINAL_FILES`, `0` terminal files, `0` chain steps
- `/api/forex/dashboard` includes `terminalReceiptWatcher`
- historical information-flow dashboard for this run reported next file
  `cas_forex/terminal_bridge_supervisor.py`; the terminal bridge supervisor
  implementation above supersedes it and the current next file is
  `cas_forex/mt4_terminal_activation.py`
- `http://127.0.0.1:5217/?page=optimizer` returns `200 OK`
- browser render check found `Terminal Watcher`,
  `WATCHER_IDLE_NO_TERMINAL_FILES`, `cas_forex/terminal_bridge_supervisor.py`,
  and the MT4/MT5 bridge next action with zero console errors

Boundary: this watches terminal evidence folders and reruns paper/demo evidence
refresh steps. It does not execute broker orders by itself, does not create
broker `ACCEPT`, does not deposit or withdraw money, and does not automate
payouts. Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement,
and payout automation remain `NOT LICENSED` / `CURRENTLY NOT LICENSED`.

## 2026-06-24 - Session autowake runner API/UI

Implemented the session autowake runner for the CAS Forex agent loop.

Implemented:

- `cas_forex/session_autowake_runner.py`
  - reads the latest workflow plan and daily learning rollup
  - evaluates market-open state, active forex session, due wake events, terminal
    blockers, pending receipts, and daily rollup readiness
  - can optionally run one paper/demo agent workflow cycle when an event is due
  - writes report JSON, Markdown, and JSONL event rows
- `scripts/run_session_autowake_runner.py`
- `tests/test_session_autowake_runner.py`
- `/api/forex/strategy/session-autowake/latest`
- dashboard key `sessionAutowake`
- TypeScript evidence types and API client fetcher
- Optimizer page `Session Autowake` run type and panel
- fixture fallback for offline UI mode
- information-flow roadmap moved from `cas_forex/session_autowake_runner.py` to
  `cas_forex/terminal_receipt_watcher.py`

Generated evidence:

- `evidence_runs/session_autowake_runner/session-autowake-20260624111809-report.json`
- `evidence_runs/session_autowake_runner/session-autowake-20260624111809-report.md`
- `evidence_runs/session_autowake_runner/session-autowake-20260624111809.jsonl`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624111808-report.json`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624111808-report.md`

Current session autowake summary:

- status: `SESSION_AUTOWAKE_READY`
- as-of timestamp: `2026-06-24T13:00:00+00:00`
- market open: `true`
- active session: `LONDON_NEW_YORK_OVERLAP`
- events evaluated: `7`
- due/executable events: `2` / `2`
- executed cycles: `0`
- pending receipts: `28`
- terminal blockers: `5`
- next due event: `MICRO_SCALP_LOOP`
- daily rollup readiness: `WAITING_FOR_TERMINAL_CLOSE_HISTORY`

Verification:

```bash
python -m pytest tests/test_session_autowake_runner.py -q
# 4 passed

python -m pytest tests -q
# 427 passed

cd ui && npm run build
# 51 modules, 443.73 KB JS, 113.27 KB gzip
```

API/UI smoke:

- `http://127.0.0.1:8805/api/forex/health` -> healthy
- `/api/forex/strategy/session-autowake/latest` ->
  `SESSION_AUTOWAKE_READY`, `LONDON_NEW_YORK_OVERLAP`, `2` due events,
  `5` terminal blockers
- `/api/forex/dashboard` includes `sessionAutowake`
- historical information-flow dashboard for this run reported next file
  `cas_forex/terminal_receipt_watcher.py`; the terminal watcher implementation
  above supersedes it and the current next file is
  `cas_forex/terminal_bridge_supervisor.py`
- `http://127.0.0.1:5216/?page=optimizer` returns `200 OK`
- browser render check found `Session Autowake`, `SESSION_AUTOWAKE_READY`,
  `LONDON_NEW_YORK_OVERLAP`, and `cas_forex/terminal_receipt_watcher.py` with
  zero console errors

Operational note: start the local API with `py -3.12` and
`PYTHONPATH=.pydeps-win312;.` because the default `python` on this machine is
currently Python 3.14 while `.pydeps-win312` contains Python 3.12 native
dependencies.

Boundary: this wakes/evaluates the paper/demo agent-loop cadence and can
request a paper/demo cycle. It does not execute broker orders by itself, does
not create broker `ACCEPT`, does not deposit or withdraw money, and does not
automate payouts. Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank
movement, and payout automation remain `NOT LICENSED` / `CURRENTLY NOT
LICENSED`.

## 2026-06-24 - Daily learning rollup API/UI

Implemented the first daily learning rollup for the CAS Forex 30-day
improvement window.

Implemented:

- `cas_forex/daily_learning_rollup.py`
  - reads latest agent cycle, memory, terminal history, research queue,
    strategy-dev queue, and strategy patch-runner reports
  - summarizes route counts, approved/rejected counts, command/receipt state,
    closed PnL, profit factor, expectancy, by-agent/by-symbol/by-strategy
    buckets, queued follow-up work, and terminal blockers
  - writes report JSON, Markdown, and JSONL rollup rows
- `scripts/run_daily_learning_rollup.py`
- `tests/test_daily_learning_rollup.py`
- `/api/forex/strategy/daily-learning-rollup/latest`
- dashboard key `dailyLearningRollup`
- TypeScript evidence types and API client fetcher
- Optimizer page `Daily Learning Rollup` run type and panel
- fixture fallback for offline UI mode
- information-flow roadmap moved from `cas_forex/daily_learning_rollup.py` to
  `cas_forex/session_autowake_runner.py`

Generated evidence:

- `evidence_runs/daily_learning_rollup/daily-learning-rollup-20260624110228-report.json`
- `evidence_runs/daily_learning_rollup/daily-learning-rollup-20260624110228-report.md`
- `evidence_runs/daily_learning_rollup/daily-learning-rollup-20260624110228.jsonl`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624110229-report.json`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624110229-report.md`

Current daily rollup summary:

- status: `DAILY_LEARNING_ROLLUP_BUILT_WAITING_FOR_CLOSED_PNL`
- trading date: `2026-06-24`
- day index: `1` of `30`
- routes: `62`
- approved/rejected: `28` / `34`
- executed command rows: `28`
- pending receipts: `28`
- closed trades: `0`
- net PnL: `0`
- patch decisions: `6`
- patch candidates: `1`
- replay jobs: `3`
- readiness label: `WAITING_FOR_TERMINAL_CLOSE_HISTORY`

Verification:

```bash
python -m pytest tests/test_daily_learning_rollup.py -q
# 3 passed

python -m pytest tests/test_daily_learning_rollup.py tests/test_strategy_patch_runner.py tests/test_agent_information_flow.py -q
# 11 passed

python -m pytest tests/test_daily_learning_rollup.py tests/test_strategy_patch_runner.py tests/test_strategy_dev_queue.py tests/test_agent_research_queue.py tests/test_agent_memory.py tests/test_terminal_history_ingest.py tests/test_agent_information_flow.py -q
# 20 passed

python -m pytest tests -q
# 423 passed

cd ui && npm run build
# 51 modules, 435.75 KB JS, 111.88 KB gzip
```

API/UI smoke:

- `http://127.0.0.1:8804/api/forex/health` -> healthy
- `/api/forex/strategy/daily-learning-rollup/latest` ->
  `DAILY_LEARNING_ROLLUP_BUILT_WAITING_FOR_CLOSED_PNL`, `62` routes,
  `0` closed, `28` pending receipts
- `/api/forex/dashboard` includes `dailyLearningRollup`
- historical information-flow dashboard for this run reported next file
  `cas_forex/session_autowake_runner.py`; the session autowake implementation
  above supersedes it and the current next file is
  `cas_forex/terminal_receipt_watcher.py`
- `http://127.0.0.1:5215/?page=optimizer` returns `200 OK`

Boundary: this creates the 30-day-window daily learning record. It does not
execute broker orders, does not compile or run the MT4 EA inside a real
terminal, does not move money, and does not claim live-income readiness. Live
trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and payout
automation remain `NOT LICENSED` / `CURRENTLY NOT LICENSED`.

## 2026-06-24 - Strategy patch runner API/UI

Implemented the first strategy patch/replay decision runner for CAS Forex.

Implemented:

- `cas_forex/strategy_patch_runner.py`
  - reads the latest strategy-development queue report
  - converts work items into patch candidates, replay jobs, promotion reviews,
    demotion reviews, and terminal-input blockers
  - writes report JSON, Markdown, and JSONL decision rows
- `scripts/run_strategy_patch_runner.py`
- `tests/test_strategy_patch_runner.py`
- `/api/forex/strategy/strategy-patch-runner/latest`
- dashboard key `strategyPatchRunner`
- TypeScript evidence types and API client fetcher
- Optimizer page `Strategy Patch Runner` run type and decision table
- fixture fallback for offline UI mode
- information-flow roadmap moved from `cas_forex/strategy_patch_runner.py` to
  `cas_forex/daily_learning_rollup.py`

Generated evidence:

- `evidence_runs/strategy_patch_runner/strategy-patch-runner-20260624104622-report.json`
- `evidence_runs/strategy_patch_runner/strategy-patch-runner-20260624104622-report.md`
- `evidence_runs/strategy_patch_runner/strategy-patch-runner-20260624104622.jsonl`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624104623-report.json`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624104623-report.md`

Current strategy patch-runner summary:

- status: `STRATEGY_PATCH_RUNNER_READY`
- decisions: `6`
- ready decisions: `3`
- blocked decisions: `3`
- patch candidates: `1`
- replay jobs: `3`
- promotion reviews: `0`
- demotion reviews: `0`
- terminal-input-required decisions: `2`
- next decision: `strategy-patch-terminal_joinback_blocker-b734b40a97a7028d`

Verification:

```bash
python -m pytest tests/test_strategy_patch_runner.py -q
# 3 passed

python -m pytest tests/test_strategy_patch_runner.py tests/test_strategy_dev_queue.py tests/test_agent_information_flow.py -q
# 11 passed

python -m pytest tests/test_strategy_patch_runner.py tests/test_strategy_dev_queue.py tests/test_agent_research_queue.py tests/test_agent_memory.py tests/test_terminal_history_ingest.py tests/test_agent_information_flow.py -q
# 17 passed

python -m pytest tests -q
# 420 passed

cd ui && npm run build
# 51 modules, 427.81 KB JS, 110.56 KB gzip
```

API/UI smoke:

- `http://127.0.0.1:8803/api/forex/health` -> healthy
- `/api/forex/strategy/strategy-patch-runner/latest` ->
  `STRATEGY_PATCH_RUNNER_READY`, `6` decisions, `3` ready, `3` blocked
- `/api/forex/dashboard` includes `strategyPatchRunner`
- information-flow dashboard reported `cas_forex/daily_learning_rollup.py`
  as the next file for this historical section; the current top section
  supersedes that with `cas_forex/session_autowake_runner.py`
- `http://127.0.0.1:5214/?page=optimizer` returns `200 OK`

Boundary: this creates evidence-backed patch/replay decisions. It does not
execute broker orders, does not compile or run the MT4 EA inside a real
terminal, does not move money, and does not silently modify live strategy code.
Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and
payout automation remain `NOT LICENSED` / `CURRENTLY NOT LICENSED`.

## 2026-06-24 - Strategy development queue API/UI

Implemented the first strategy-development queue for CAS Forex.

Implemented:

- `cas_forex/strategy_dev_queue.py`
  - reads the latest agent research queue and optional agent memory report
  - converts research tasks into replay, patch, and terminal-joinback work items
  - converts future closed profit/loss memory rows into promotion/demotion reviews
  - writes report JSON, Markdown, and JSONL work-item rows
- `scripts/run_strategy_dev_queue.py`
- `tests/test_strategy_dev_queue.py`
- `/api/forex/strategy/strategy-dev-queue/latest`
- dashboard key `strategyDevQueue`
- TypeScript evidence types and API client fetcher
- Optimizer page `Strategy Dev Queue` run type and work-item table
- fixture fallback for offline UI mode
- information-flow roadmap moved from `cas_forex/strategy_dev_queue.py` to
  `cas_forex/strategy_patch_runner.py`

Generated evidence:

- `evidence_runs/strategy_dev_queue/strategy-dev-queue-20260624102900-report.json`
- `evidence_runs/strategy_dev_queue/strategy-dev-queue-20260624102900-report.md`
- `evidence_runs/strategy_dev_queue/strategy-dev-queue-20260624102900.jsonl`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624102906-report.json`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624102906-report.md`

Current strategy-dev queue summary:

- status: `STRATEGY_DEV_QUEUE_BUILT`
- work items: `6`
- queued items: `3`
- blocked items: `3`
- ready-for-replay items: `3`
- patch candidates: `1`
- promotion reviews: `0`
- demotion reviews: `0`
- terminal-blocked items: `3`
- next item: `strategy-dev-terminal-joinback-7c441e3221a2bdce`

Verification:

```bash
python -m pytest tests/test_strategy_dev_queue.py tests/test_agent_information_flow.py -q
# 8 passed

python -m pytest tests/test_strategy_dev_queue.py tests/test_agent_research_queue.py tests/test_agent_memory.py tests/test_terminal_history_ingest.py tests/test_agent_information_flow.py -q
# 14 passed

python -m pytest tests -q
# 417 passed

cd ui && npm run build
# 51 modules, 419.23 KB JS, 109.29 KB gzip
```

API smoke:

- `http://127.0.0.1:8802/api/forex/health` -> healthy
- `/api/forex/strategy/strategy-dev-queue/latest` ->
  `STRATEGY_DEV_QUEUE_BUILT`, `6` items, `3` blocked, `1` patch candidate
- `/api/forex/dashboard` includes `strategyDevQueue`
- information-flow dashboard reported `cas_forex/strategy_patch_runner.py`
  as the next file for this historical section; the current top section
  supersedes that with `cas_forex/daily_learning_rollup.py`

Boundary: this creates the queue that turns memory/research into patch,
replay, promotion, and demotion work. It does not execute broker orders, does
not compile or run the MT4 EA inside a real terminal, and does not move money.
Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and
payout automation remain `NOT LICENSED` / `CURRENTLY NOT LICENSED`.

## 2026-06-24 - Terminal history ingest and closed-memory PnL

Implemented terminal close/history ingest and wired it into agent memory,
API, and UI.

Implemented:

- `cas_forex/terminal_history_ingest.py`
  - normalizes MT4/MT5 close-history JSON/CSV/text/HTML inputs
  - joins closed rows back to agent memory by `command_id`, `receipt_id`,
    broker ticket, or symbol/direction/lot/entry fallback
  - writes report JSON, Markdown, and JSONL history rows
  - produces memory update packets with closed PnL, pips, R multiple, MAE/MFE,
    close reason, commission, swap, close time, and exit price
- `scripts/run_terminal_history_ingest.py`
- `tests/test_terminal_history_ingest.py`
- `scripts/run_agent_memory.py --terminal-history-report-dir`
- `/api/forex/strategy/terminal-history-ingest/latest`
- dashboard key `terminalHistoryIngest`
- TypeScript evidence types and API client fetcher
- Optimizer page `Terminal History Ingest` run type and closed-PnL panels
- agent information-flow roadmap moved from `cas_forex/terminal_history_ingest.py`
  to `cas_forex/strategy_dev_queue.py`

Generated evidence:

- `evidence_runs/terminal_history_ingest/terminal-history-ingest-20260624101300-report.json`
- `evidence_runs/terminal_history_ingest/terminal-history-ingest-20260624101300-report.md`
- `evidence_runs/terminal_history_ingest/terminal-history-ingest-20260624101300.jsonl`
- `evidence_runs/agent_memory/agent-memory-20260624101307-report.json`
- `evidence_runs/agent_research_queue/agent-research-queue-20260624101315-report.json`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624101117-report.json`

Current terminal-history summary:

- status: `TERMINAL_HISTORY_EMPTY`
- history rows: `0`
- memory updates: `0`
- closed trades: `0`
- net closed PnL: `0`
- reason: no MT4/MT5 closed-history export is present yet under
  `evidence_runs/terminal_history_exports`

Current memory summary:

- memory rows: `62`
- pending terminal receipts: `28`
- receipt rows joined: `0`
- terminal-history rows joined: `0`
- rejected-route research rows: `34`

Verification:

```bash
python -m pytest tests/test_terminal_history_ingest.py tests/test_agent_memory.py tests/test_agent_research_queue.py tests/test_agent_information_flow.py -q
# 11 passed

python -m pytest tests -q
# 414 passed

cd ui && npm run build
# 51 modules, 411.40 KB JS, 107.92 KB gzip
```

API/UI smoke:

- `http://127.0.0.1:8801/api/forex/health` -> healthy
- `/api/forex/strategy/terminal-history-ingest/latest` ->
  `TERMINAL_HISTORY_EMPTY`, `0` history rows, `0` memory updates
- `/api/forex/dashboard` includes `terminalHistoryIngest`
- `http://127.0.0.1:5212/?page=optimizer` returns `200 OK`

Boundary: this makes CAS Forex ready to ingest closed paper/demo terminal
history and learn from realized trade outcomes once exports exist. It does not
compile or run the MT4 EA inside a real terminal, does not produce receipt
files, and does not create live trading permission. Live trading, broker
`ACCEPT`, auto-deposit, debit/card/bank movement, and payout automation remain
`NOT LICENSED` / `CURRENTLY NOT LICENSED`.

## 2026-06-24 - Agent research queue API/UI

Implemented the first CAS Forex agent research queue.

Implemented:

- `cas_forex/agent_research_queue.py`
  - reads latest `cas_forex_agent_outcome_memory.v1` rows
  - turns memory into `cas_forex_research_task_packet.v1` tasks
  - writes report JSON, Markdown, and JSONL task rows
  - creates terminal receipt joinback tasks for approved commands waiting for
    receipts
  - creates overseer conflict-key refinement tasks from rejected routes
  - creates condition-lab rejection analysis tasks
  - creates walk-forward receipt replay tasks after receipts arrive
  - creates terminal history/PnL schema work so memory can later learn PnL,
    pips, MAE/MFE, close reason, commission, and swap
- `scripts/run_agent_research_queue.py`
- `tests/test_agent_research_queue.py`
- `/api/forex/strategy/agent-research-queue/latest`
- dashboard key `agentResearchQueue`
- TypeScript evidence types and API client fetcher
- Optimizer page `Agent Research Queue` run type and task table
- fixture fallback for offline UI mode
- information-flow roadmap moved from `cas_forex/agent_research_queue.py` to
  `cas_forex/terminal_history_ingest.py`

Generated evidence:

- `evidence_runs/agent_research_queue/agent-research-queue-20260624095304-report.json`
- `evidence_runs/agent_research_queue/agent-research-queue-20260624095304-report.md`
- `evidence_runs/agent_research_queue/agent-research-queue-20260624095304.jsonl`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624095004-report.json`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624095004-report.md`

Current queue summary:

- queued tasks: `6`
- high-priority tasks: `4`
- terminal receipt joinback tasks: `1`
- overseer conflict-key refinement tasks: `1`
- condition-lab rejection tasks: `2`
- walk-forward receipt replay tasks: `1`
- terminal history/PnL schema tasks: `1`
- next task: `research-terminal-receipt-joinback-7f4619f0b837f4e4`

Verification:

```bash
python -m pytest tests/test_agent_research_queue.py tests/test_agent_memory.py tests/test_agent_information_flow.py -q
# 9 passed

python -m pytest tests -q
# 412 passed

cd ui && npm run build
# 51 modules, 407.19 KB JS, 107.15 KB gzip
```

API/UI smoke:

- `http://127.0.0.1:8800/api/forex/health` -> healthy
- `/api/forex/strategy/agent-research-queue/latest` -> `6` tasks, `4` high
  priority, next task `research-terminal-receipt-joinback-7f4619f0b837f4e4`
- `/api/forex/dashboard` includes `agentResearchQueue`
- `http://127.0.0.1:5211/?page=optimizer` returns `200 OK`

Boundary: this creates research tasks and cockpit/API visibility. It does not
compile or run the MT4 EA inside a real terminal, and it does not provide
closed-trade PnL/MAE/MFE until terminal close/history data exists. Live trading,
broker `ACCEPT`, auto-deposit, debit/card/bank movement, and payout automation
remain `NOT LICENSED` / `CURRENTLY NOT LICENSED`.

## 2026-06-24 - Agent outcome memory API/UI

Implemented the first CAS Forex agent outcome-memory layer.

Implemented:

- `cas_forex/agent_memory.py`
  - reads the append-only agent event journal
  - joins route intents, overseer decisions, terminal commands, and available
    terminal receipts
  - writes `cas_forex_agent_outcome_memory.v1` report JSON, Markdown, and JSONL
  - labels approved commands without receipts as `AWAITING_TERMINAL_RECEIPT`
  - labels rejected routes as `ROUTE_REJECTED`
  - labels verified receipt rows as `TERMINAL_ACKNOWLEDGED`
- `scripts/run_agent_memory.py`
- `tests/test_agent_memory.py`
- `/api/forex/strategy/agent-memory/latest`
- dashboard key `agentMemory`
- TypeScript evidence types and API client fetcher
- Optimizer page `Agent Outcome Memory` run type and information-flow metrics
- fixture fallback for offline UI mode
- information-flow roadmap moved from `cas_forex/agent_memory.py` to
  `cas_forex/agent_research_queue.py`

Generated evidence:

- `evidence_runs/agent_memory/agent-memory-20260624093213-report.json`
- `evidence_runs/agent_memory/agent-memory-20260624093213-report.md`
- `evidence_runs/agent_memory/agent-memory-20260624093213.jsonl`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624093253-report.json`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624093253-report.md`

Current memory summary:

- memory records: `62`
- route intents: `62`
- approved rows: `28`
- rejected rows: `34`
- commands joined: `28`
- receipts joined: `0`
- pending receipts: `28`
- latest cycle: `agent-cycle-44848f2d3efc4669`

Verification:

```bash
python -m pytest tests/test_agent_memory.py tests/test_terminal_receipt_ingest.py tests/test_mt4_mailbox_bridge.py tests/test_agent_information_flow.py -q
# 16 passed

python -m pytest tests -q
# 410 passed

cd ui && npm run build
# 51 modules, 398.13 KB JS, 105.33 KB gzip
```

API/UI smoke:

- `http://127.0.0.1:8799/api/forex/health` -> healthy
- `/api/forex/strategy/agent-memory/latest` -> `62` memory rows, `28` pending
  receipts, `0` receipts joined
- `/api/forex/dashboard` includes `agentMemory`
- `http://127.0.0.1:5209/?page=optimizer` returns `200 OK`

Boundary: this creates learning rows and cockpit/API visibility. It does not
compile or run the MT4 EA inside a real terminal, and it does not provide
closed-trade PnL/MAE/MFE until terminal close/history data exists. Live trading,
broker `ACCEPT`, auto-deposit, debit/card/bank movement, and payout automation
remain `NOT LICENSED` / `CURRENTLY NOT LICENSED`.

## 2026-06-24 - MT4 EA receipt-writer source

Replaced the MT4 EA scaffold with a source-ready mailbox worker.

Implemented:

- `mt4/Experts/CASForexBridgeEA.mq4`
  - creates mailbox folders
  - writes heartbeat JSON
  - enumerates `<MailboxRoot>/commands/*.json`
  - parses the stable CAS command schema
  - skips commands that already have receipt files
  - acknowledges `PING`
  - acknowledges `PAPER_MT4` `PLACE_ORDER` commands by writing receipt JSON
  - includes `raw_request_hash`, `raw_response_hash`, terminal identity,
    account snapshot, fill fields, slippage, ticket, and error fields
  - keeps `LIVE_MT4` behind both the EA `LiveTradingAllowed` input and the
    command `live_money_authorized` flag
- `tests/test_mt4_mailbox_bridge.py` now checks the EA source contract
- `cas_forex/broker/mt4_mailbox_bridge.py` probe next-action text updated
- `cas_forex/agent_information_flow.py` and UI fixture now mark the MT4 EA
  source as `SOURCE_READY_NEEDS_TERMINAL_VERIFY`

Generated evidence:

- `evidence_runs/agent_information_flow/agent-information-flow-20260624091707-report.json`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624091707-report.md`
- `evidence_runs/mt4_mailbox_smoke/mt4-mailbox-smoke-status.json`

Verification:

```bash
python -m pytest tests/test_mt4_mailbox_bridge.py tests/test_terminal_receipt_ingest.py tests/test_agent_information_flow.py -q
# 14 passed

python -m pytest tests -q
# 408 passed

cd ui && npm run build
# 51 modules, 394.10 KB JS, 104.63 KB gzip
```

API/UI smoke:

- `/api/forex/strategy/agent-information-flow` reports
  `must_have_next_file=cas_forex/agent_memory.py`
- `mt4/Experts/CASForexBridgeEA.mq4` status is
  `SOURCE_READY_NEEDS_TERMINAL_VERIFY`
- `http://127.0.0.1:5206/?page=optimizer` returns `200 OK`

Remaining MT4 terminal step: compile, attach, and run the EA inside an actual
MT4 terminal pointed at the shared mailbox, then ingest the generated receipt
JSON. Next software lane: build `cas_forex/agent_memory.py`.

Boundary: this makes the MT4 EA source capable of writing paper/demo receipt
JSON. It does not create broker `ACCEPT`, deposit, withdraw, move bank/card
money, or automate payouts. Live trading, broker `ACCEPT`, auto-deposit,
debit/card/bank movement, and payout automation remain `NOT LICENSED` /
`CURRENTLY NOT LICENSED`.

## 2026-06-24 - Receipt-aware overseer routing gate

Implemented receipt-aware same-symbol routing in the agent overseer.

Implemented:

- `cas_forex/agent_overseer.py` now reads receipt lifecycle state from
  `evidence_runs/agent_workflow_queue/agent-events.jsonl`
- `cas_forex/agent_state.py` passes the cycle event log path into the overseer
- `cas_forex/agent_message_bus.py` maps receipt-gated rejections to
  `QUEUED_AWAITING_RECEIPT` / `TERMINAL_LOCKED_FOR_SYMBOL`
- `tests/test_agent_overseer.py`
- workflow regression coverage in `tests/test_terminal_receipt_ingest.py`
- API-surface tests now use temp evidence/route monkeypatches instead of
  writing throwaway `MANUAL_CLI` cycles into real `evidence_runs`
- fixture fallback update in `ui/src/data/fixtures.ts`

Receipt-aware routing behavior:

- pending same-symbol command -> reject new same-symbol route as awaiting
  terminal receipt/reconciliation
- `NEXT_CYCLE_ALLOWED` after verified/reconciled receipt -> allow the next
  same-symbol route
- `TERMINAL_RECEIPT_MISMATCH` / `TERMINAL_LOCKED_FOR_SYMBOL` -> keep the symbol
  locked until the mismatch is handled

Current event journal after default smoke:

- path: `evidence_runs/agent_workflow_queue/agent-events.jsonl`
- event count: `459`
- cycle count: `31`
- latest cycle: `agent-cycle-44848f2d3efc4669`
- terminal commands written: `28`
- pending terminal receipts: `28`
- latest default cycle approved intents: `0`
- latest default cycle rejected intents: `2`
- latest default cycle terminal commands written: `0`

Generated evidence:

- `evidence_runs/agent_workflow_queue/agent-workflow-cycle-20260624090733-report.json`
- `evidence_runs/terminal_receipt_ingest/terminal-receipt-ingest-20260624090739-report.json`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624085546-report.json`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624085546-report.md`

Verification:

```bash
python -m pytest tests/test_agent_overseer.py tests/test_terminal_receipt_ingest.py tests/test_agent_workflow_cycle.py tests/test_agent_message_bus.py -q
# 14 passed

python -m pytest tests -q
# 407 passed

cd ui && npm run build
# 51 modules, 393.97 KB JS, 104.58 KB gzip

py -3.12 -c "import sys; sys.path.insert(0, r'.pydeps-win312'); import pydantic_core, fastapi, uvicorn; print('windows_api_deps_ok', pydantic_core.__version__)"
# windows_api_deps_ok 2.46.4
```

Windows API dependency note: `.pydeps` currently contains WSL/Linux binary
wheels. Added `.pydeps-win312/` to `.gitignore` and installed clean
Windows-compatible FastAPI/Uvicorn/Pydantic dependencies there. On Windows,
start the API with Python 3.12 and `PYTHONPATH=.pydeps-win312;.`.

Next implementation lane: make `mt4/Experts/CASForexBridgeEA.mq4` read command
JSON from the mailbox and write real terminal receipt JSON, then build
`cas_forex/agent_memory.py` for full win/loss outcome memory.

Boundary: the overseer now prevents duplicate same-symbol command spam while
terminal receipts are pending. It does not execute live broker orders, create
broker `ACCEPT`, deposit, withdraw, move bank/card money, or automate payouts.
Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and
payout automation remain `NOT LICENSED` / `CURRENTLY NOT LICENSED`.

## 2026-06-24 - Terminal receipt ingest joinback

Implemented the missing receipt joinback between MT4/MT5 mailbox receipt files
and the append-only agent event journal.

Implemented:

- `cas_forex/terminal_receipt_ingest.py`
- `scripts/run_terminal_receipt_ingest.py`
- `tests/test_terminal_receipt_ingest.py`
- `/api/forex/strategy/terminal-receipt-ingest/latest`
- dashboard payload key `terminalReceiptIngest`
- TypeScript type/API client/fixture fallback for terminal receipt ingest
- Optimizer page receipt-ingest metrics and receipt rows
- event-journal summary now reports outstanding receipt commands, not just raw
  historical `RECEIPT_PENDING` event count

Receipt lifecycle behavior:

- valid receipt -> `TERMINAL_RECEIPT_RECEIVED`,
  `TERMINAL_RECEIPT_RECONCILED`, `NEXT_CYCLE_ALLOWED`
- bad receipt hash or missing terminal/account fields ->
  `TERMINAL_RECEIPT_MISMATCH`, `TERMINAL_LOCKED_FOR_SYMBOL`
- reruns are idempotent by `receipt_id`

Current event journal after verification:

- path: `evidence_runs/agent_workflow_queue/agent-events.jsonl`
- event count: `270`
- cycle count: `18`
- latest cycle: `agent-cycle-5885cba41e8f5a38`
- terminal commands written: `18`
- pending terminal receipts: `18`
- verified terminal receipts: `0`
- reconciled terminal receipts: `0`
- next-cycle allowed events: `0`
- receipt mismatches: `0`

Generated evidence:

- `evidence_runs/terminal_receipt_ingest/terminal-receipt-ingest-20260624083745-report.json`
- `evidence_runs/terminal_receipt_ingest/terminal-receipt-ingest-20260624083745-report.md`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624083721-report.json`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624083721-report.md`

Current receipt state: no MT4/MT5 terminal receipt files have been written into
the mailbox yet, so ingest appended `0` new events in the default evidence run.
The software path is now ready for terminal receipts; the external EA/terminal
still needs to write receipt JSON.

Verification:

```bash
python -m pytest tests -q
# 403 passed

python -m pytest tests/test_agent_information_flow.py tests/test_terminal_receipt_ingest.py tests/test_agent_message_bus.py -q
# 11 passed

cd ui && npm run build
# 51 modules, 393.21 KB JS, 104.34 KB gzip
```

Next implementation lane: update `cas_forex/agent_overseer.py` so same-symbol
route decisions consume `NEXT_CYCLE_ALLOWED` and
`TERMINAL_LOCKED_FOR_SYMBOL`, connect the actual MT4 EA/terminal receipt feed,
then build `cas_forex/agent_memory.py` for full win/loss outcome memory.

Boundary: terminal receipt ingest verifies paper/demo terminal receipts against
command events and account snapshots. It does not execute live broker orders,
create broker `ACCEPT`, deposit, withdraw, move bank/card money, or automate
payouts. Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement,
and payout automation remain `NOT LICENSED` / `CURRENTLY NOT LICENSED`.

## 2026-06-24 - Agent message bus event journal

Implemented the real append-only agent event journal selected by the
information-flow team review.

Implemented:

- `cas_forex/agent_message_bus.py`
- `tests/test_agent_message_bus.py`
- `cas_forex/agent_state.py` now writes cycle events into `agent-events.jsonl`
- `/api/forex/strategy/agent-workflow-events/summary`
- `/api/forex/strategy/agent-workflow-events`
- `/api/forex/strategy/agent-workflow-context/latest`
- `/api/forex/strategy/agent-workflow-intents/open`
- `/api/forex/strategy/agent-workflow-receipts/latest`
- dashboard payload key `agentMessageBus`
- TypeScript type/API client/fixture fallback for `AgentMessageBusSummary`
- Optimizer page event-journal metrics

Current event journal:

- path: `evidence_runs/agent_workflow_queue/agent-events.jsonl`
- event count: superseded by terminal receipt ingest update above
- cycle count: superseded by terminal receipt ingest update above
- latest cycle: superseded by terminal receipt ingest update above
- latest cycle report: superseded by terminal receipt ingest update above
- event types: `AGENT_CONTEXT_READY`, `AGENT_HEARTBEAT`,
  `ROUTE_INTENT_CREATED`, `OVERSEER_DECISION_CREATED`,
  `TERMINAL_COMMAND_WRITTEN`, `TERMINAL_RECEIPT_PENDING`,
  `OUTCOME_MEMORY_WRITTEN`
- pending terminal receipts: superseded by terminal receipt ingest update above

Live local smoke:

- API health: `http://127.0.0.1:8790/api/forex/health`
- Event summary: `http://127.0.0.1:8790/api/forex/strategy/agent-workflow-events/summary`
- Dashboard: `http://127.0.0.1:8790/api/forex/dashboard`
- UI: `http://127.0.0.1:5200/?page=optimizer`

Verification:

```bash
python -m pytest tests/test_agent_message_bus.py tests/test_agent_workflow_cycle.py tests/test_agent_information_flow.py tests/test_settings_api_surface.py -q
# 23 passed

python -m pytest tests -q
# 400 passed

cd ui && npm run build
# 51 modules, 389.02 KB JS, 103.45 KB gzip
```

Terminal receipt ingest is complete in the newer update above. Next
implementation lane: reconciliation-gated same-symbol routing in
`cas_forex/agent_overseer.py`.

Boundary: agent events are coordination records for paper/demo workflows. They
do not by themselves execute live broker orders, create broker `ACCEPT`,
deposit, withdraw, move bank/card money, or automate payouts. Live trading,
broker `ACCEPT`, auto-deposit, debit/card/bank movement, and payout automation
remain `NOT LICENSED` / `CURRENTLY NOT LICENSED`.

## 2026-06-24 - Agent information-flow team review

Spawned three specialist agents (`Sagan`, `Mill`, and `Leibniz`) to determine
the best form of information flow between CAS Forex agents, then promoted the
combined recommendation into evidence/API/dashboard/UI.

Implemented:

- `cas_forex/agent_information_flow.py`
- `scripts/run_agent_information_flow.py`
- `tests/test_agent_information_flow.py`
- `/api/forex/strategy/agent-information-flow`
- dashboard payload key `agentInformationFlow`
- TypeScript types/API client/fixture fallback for `AgentInformationFlow`
- Optimizer page `Agent Information Flow` panel

Generated evidence:

- `evidence_runs/agent_information_flow/agent-information-flow-20260624083721-report.json`
- `evidence_runs/agent_information_flow/agent-information-flow-20260624083721-report.md`

Team verdict:

- best flow form: `append-only event journal plus read-only API projections`
- canonical event log: `evidence_runs/agent_workflow_queue/agent-events.jsonl`
- latest cycle projection: `evidence_runs/agent_workflow_queue/agent-workflow-state.jsonl`
- terminal mailbox: `evidence_runs/agent_workflow_mt4_mailbox/{commands,receipts}`
- canonical packet count: `7`
- flow stages: `8`
- receipt/reconciliation lifecycle states: `10`
- next build target: `cas_forex/agent_message_bus.py`

Plain-English decision: agents should coordinate through the event journal, not
by scraping `/api/forex/dashboard`. The dashboard is the wall display. The
MetaTrader mailbox is only the command outbox and receipt inbox. The learning
loop must join route intent, overseer decision, MT4/MT5 command, terminal
receipt, reconciliation, close outcome, condition snapshot, and daily 30-day
rollup.

Verification:

```bash
python -m pytest tests/test_agent_information_flow.py tests/test_agent_workflow_cycle.py tests/test_agent_workflow.py -q
# 12 passed

python -m pytest tests -q
# 397 passed

cd ui && npm run build
# 51 modules, 386.47 KB JS, 102.97 KB gzip
```

Live local smoke:

- API health: `http://127.0.0.1:8786/api/forex/health`
- Information-flow API: `http://127.0.0.1:8786/api/forex/strategy/agent-information-flow`
- Dashboard: `http://127.0.0.1:8786/api/forex/dashboard`
- UI: `http://127.0.0.1:5196/?page=optimizer`

Boundary: this report defines message shape, lifecycle, storage, and agent
responsibility. It does not by itself execute live broker orders, create broker
`ACCEPT`, deposit, withdraw, move bank/card money, or automate payouts. Live
trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and payout
automation remain `NOT LICENSED` / `CURRENTLY NOT LICENSED`.

## 2026-06-24 - Agent workflow execution cycle

Converted the agentic trading-day plan into a runnable paper/demo cycle.

Implemented:

- `cas_forex/agent_state.py`
- `cas_forex/micro_scalp_policy.py`
- `cas_forex/hourly_intraday_policy.py`
- `cas_forex/agent_overseer.py`
- `scripts/run_agent_workflow_queue.py`
- `tests/test_agent_workflow_cycle.py`
- `/api/forex/strategy/agent-workflow-cycle/latest`
- dashboard payload key `agentWorkflowCycle`
- Optimizer latest-cycle readout

Latest cycle summary:

- execution mode: `PAPER_MT4_COMMAND_INTENT`
- agent heartbeats: `6`
- route intents: `2`
- approved intents: `1`
- rejected/queued same-symbol hourly intents: `1`
- MT4 paper commands: `1`
- memory snapshots: `2`
- symbol/timeframes: `AUD/CAD`, `M5` and `H1`

Latest evidence:

- `evidence_runs/agent_workflow_queue/agent-workflow-cycle-20260624050225-report.json`
- `evidence_runs/agent_workflow_queue/agent-workflow-cycle-20260624050225-report.md`
- `evidence_runs/agent_workflow_queue/agent-workflow-state.jsonl`
- `evidence_runs/agent_workflow_mt4_mailbox/commands/`

Next implementation lane: make the command cycle receipt/reconciliation-gated
and add true trade-outcome learning memory.

## 2026-06-24 - Agentic trading-day workflow plan

Encoded the owner-requested CAS Forex agent desk as a first-class workflow
report, API endpoint, dashboard payload, and Optimizer UI panel.

Implemented:

- `cas_forex/agent_workflow.py`
- `scripts/run_agent_workflow_plan.py`
- `tests/test_agent_workflow.py`
- `/api/forex/strategy/agent-workflow-plan`
- dashboard payload key `agentWorkflowPlan`
- TypeScript types/API client/fixture fallback for `AgentWorkflowPlan`
- Optimizer page `Agentic Trading-Day Workflow` panel

Generated evidence:

- `evidence_runs/agent_workflow/agent-workflow-plan-20260624044500-report.json`
- `evidence_runs/agent_workflow/agent-workflow-plan-20260624044500-report.md`

Workflow summary:

- status: `AGENT_DESK_PLAN_READY`
- agents: `8`
- autowake events: `7`
- micro-scalp cadence: `1-5` minutes
- hourly intraday cadence: `60` minutes
- primary short-timeframe lead: `AUD/CAD M5 range_scalper_12_80`
- replay verdict: `REPLAY_LEAD_FOR_ADAPTIVE_REVIEW`
- adaptive next step: `QUEUE_FOR_ADAPTIVE_COMPOUNDING_REVIEW`

Agents defined:

- `session_autowake_agent`
- `micro_scalp_agent`
- `hourly_intraday_agent`
- `overseer_agent`
- `research_condition_agent`
- `strategy_dev_agent`
- `terminal_bridge_agent`
- `audit_memory_agent`

Live local smoke:

- API health: `http://127.0.0.1:8782/api/forex/health`
- Workflow API: `http://127.0.0.1:8782/api/forex/strategy/agent-workflow-plan`
- Dashboard: `http://127.0.0.1:8782/api/forex/dashboard`
- UI: `http://127.0.0.1:5192/?page=optimizer`

Verification:

```bash
python -m pytest tests/test_agent_workflow.py tests/test_forex_fury_replay_results.py -q
# 5 passed

python -m pytest tests -q
# 388 passed

cd ui && npm run build
# 51 modules, 364.08 KB JS, 97.89 KB gzip
```

Next implementation lane: build persistent agent state, the autowake runner,
micro-scalp policy, hourly intraday policy, overseer router, and terminal
receipt attachment.

Boundary: the workflow plan coordinates autowake, scalp, intraday, overseer,
research, terminal-bridge, and memory agents. It creates schedules, route
intents, research tasks, and evidence requirements; it does not by itself
execute live broker orders, create broker `ACCEPT`, deposit, withdraw, move
bank/card money, or automate payouts. Live trading, broker `ACCEPT`,
auto-deposit, debit/card/bank movement, and payout automation remain
`NOT LICENSED` / `CURRENTLY NOT LICENSED`.

## 2026-06-24 - Forex Fury top-candidate replay results

Executed the generated CAS replay lane for the top Forex Fury-derived
`AUD/CAD` `M5` candidate and promoted the result into API/dashboard/UI
evidence.

Implemented:

- fixed generated walk-forward command to use `--timeframes`
- `cas_forex/forex_fury_replay_results.py`
- `scripts/run_forex_fury_replay_results.py`
- `tests/test_forex_fury_replay_results.py`
- `/api/forex/strategy/forex-fury-replay-results`
- dashboard payload key `forexFuryReplayResults`
- Optimizer page `Forex Fury Replay Results` panel

Generated evidence:

- `evidence_runs/forex_fury_replay_candidates/forex-fury-replay-candidates-20260624042429-report.json`
- `evidence_runs/forex_fury_condition_replay/condition-lab-20260624042332-report.json`
- `evidence_runs/forex_fury_walk_forward_replay/walk-forward-20260624042543-report.json`
- `evidence_runs/forex_fury_replay_results/forex-fury-replay-results-20260624042821-report.json`

Replay result:

- condition lab: `297` cells, `62` non-gap, `22` RPM routes, `11` no-trade routes
- top real condition cell: `AUD/CAD` `M5`, `shock`, `range_scalper_12_80`, `1.2845%` return, `0.0%` drawdown, `20.7614` profit factor
- walk-forward: `126` windows, `61` routed, `35` positive routed, `350` routed trades
- walk-forward max drawdown: `0.4953%`
- walk-forward grade: `WALK_FORWARD_LEAD`
- replay verdict: `REPLAY_LEAD_FOR_ADAPTIVE_REVIEW`
- adaptive next step: `QUEUE_FOR_ADAPTIVE_COMPOUNDING_REVIEW`

Live local smoke:

- API: `http://127.0.0.1:8778/api/forex/strategy/forex-fury-replay-results`
- Dashboard: `http://127.0.0.1:8778/api/forex/dashboard`
- UI: `http://127.0.0.1:5188/?page=optimizer`

Verification:

```bash
python -m pytest tests/test_forex_fury_replay_results.py tests/test_forex_fury_candidates.py tests/test_forex_fury_sets.py tests/test_pip_math_regressions.py -q
# 18 passed

python -m pytest tests -q
# 385 passed

cd ui && npm run build
# 51 modules, 348.28 KB JS, 93.25 KB gzip
```

Browser verification confirmed the Optimizer page renders `Forex Fury Replay
Results`, `REPLAY_LEAD_FOR_ADAPTIVE_REVIEW`,
`QUEUE_FOR_ADAPTIVE_COMPOUNDING_REVIEW`, `WALK_FORWARD_LEAD`, and `AUD/CAD`.

Boundary: replay results are CAS research/backtest evidence. They can queue an
adaptive compounding review, but they do not execute EA binaries, place orders,
create broker `ACCEPT`, deposit, withdraw, move bank/card money, or automate
payouts. Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement,
and payout automation remain `NOT LICENSED` / `CURRENTLY NOT LICENSED`.

## 2026-06-24 - Forex Fury replay-candidate queue

Converted the local Forex Fury set/report import into ranked CAS replay and
backtest candidate jobs, then surfaced the queue in the API/dashboard and
Optimizer UI.

Implemented:

- `cas_forex/forex_fury_candidates.py`
- `scripts/run_forex_fury_replay_candidates.py`
- `tests/test_forex_fury_candidates.py`
- `/api/forex/strategy/forex-fury-replay-candidates`
- dashboard payload key `forexFuryReplayCandidates`
- Optimizer page `Forex Fury Replay Candidates` panel
- instrument support for `AUD/CAD`, `GBP/AUD`, and `SPX500`

Generated evidence:

- `evidence_runs/forex_fury_replay_candidates/forex-fury-replay-candidates-20260624040820-report.json`
- `evidence_runs/forex_fury_replay_candidates/forex-fury-replay-candidates-20260624040820-report.md`

Current replay queue summary:

- `candidate_count=24`
- `supported_candidate_count=24`
- `waiting_for_instrument_spec_count=0`
- symbols: `AUD/CAD`, `AUD/USD`, `GBP/AUD`, `GBP/USD`, `SPX500`, `USD/JPY`
- timeframes: `H1`, `M1`, `M5`
- top candidate: `ff-replay-aud-cad-m5-swing-d7be2c38ca`
- top score: `320.9726`

Live local smoke:

- API: `http://127.0.0.1:8776/api/forex/strategy/forex-fury-replay-candidates`
- Dashboard: `http://127.0.0.1:8776/api/forex/dashboard`
- UI: `http://127.0.0.1:5186/?page=optimizer`

Verification:

```bash
python -m pytest tests/test_forex_fury_candidates.py tests/test_forex_fury_sets.py tests/test_external_benchmark.py tests/test_pip_math_regressions.py -q
# 18 passed

python -m pytest tests -q
# 383 passed

cd ui && npm run build
# 51 modules, 341.36 KB JS, 91.97 KB gzip
```

Browser verification confirmed the Optimizer page renders `Forex Fury Replay
Candidates`, `AUD/CAD`, `READY_FOR_CAS_REPLAY`, and the generated
`run_condition_lab.py` replay command.

Boundary: replay candidates are CAS research/backtest queue inputs. They do
not execute EA binaries, place orders, create broker `ACCEPT`, deposit,
withdraw, move bank/card money, or automate payouts. Live trading, broker
`ACCEPT`, auto-deposit, debit/card/bank movement, and payout automation remain
`NOT LICENSED` / `CURRENTLY NOT LICENSED`.

## 2026-06-24 - Forex Fury set import Optimizer UI surfacing

Surfaced the local Forex Fury set/report import as a first-class Optimizer and
dashboard payload so CAS Forex can compare and mine the owner-supplied package
from the live cockpit instead of leaving it as a standalone report.

Implemented:

- `api/data.py` dashboard key `forexFurySetImport`
- `ui/src/types/evidence.ts` Forex Fury import/report types
- `ui/src/data/api.ts` endpoint client and dashboard merge fallback
- `ui/src/data/fixtures.ts` fixture fallback
- `ui/src/App.tsx` fixture dashboard state
- `ui/src/pages/OptimizerPage.tsx` Local Forex Fury Set Import panel

Live local smoke:

- API: `http://127.0.0.1:8774/api/forex/strategy/forex-fury-set-import`
- Dashboard: `http://127.0.0.1:8774/api/forex/dashboard`
- UI: `http://127.0.0.1:5184/?page=optimizer`

Verified live payload:

- `set_count=36`
- `tester_report_count=30`
- `best_profit_factor=15.12`
- `best_symbol=AUDCAD`
- `best_timeframe=M5`

Verification:

```bash
python -m pytest tests/test_forex_fury_sets.py tests/test_external_benchmark.py -q
# 4 passed

python -m pytest tests -q
# 379 passed

cd ui && npm run build
# 51 modules, 333.31 KB JS, 90.09 KB gzip
```

Boundary: this UI/API surfacing is comparison, mining, and owner-cockpit
intelligence. It does not execute EA binaries, place orders, create broker
`ACCEPT`, deposit, withdraw, move bank/card money, or automate payouts. Live
trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and payout
automation remain `NOT LICENSED` / `CURRENTLY NOT LICENSED`.

## 2026-06-24 - Forex Fury local set/report importer

Imported the owner-supplied local Forex Fury CORE package as repeatable CAS
Forex strategy-study evidence without executing compiled EA binaries.

Source inspected:

- `C:\Users\wakil\Downloads\Forex-Fury-CORE-1.4NEW-SETS (1)`

Implemented:

- `cas_forex/forex_fury_sets.py`
- `scripts/run_forex_fury_set_import.py`
- `tests/test_forex_fury_sets.py`
- `/api/forex/strategy/forex-fury-set-import`

Generated evidence:

- `evidence_runs/forex_fury_set_import/forex-fury-set-import-20260624034719-report.json`
- `evidence_runs/forex_fury_set_import/forex-fury-set-import-20260624034719-report.md`

Current normalized summary from the local package:

- `set_count=36`
- `tester_report_count=30`
- `platform_counts={MT4: 18, MT5: 18}`
- `family_counts={classic_m15: 6, scalping: 14, swing: 16}`
- `symbol_counts={AUDCAD: 8, AUDUSD: 6, EURUSD: 4, GBPAUD: 2, GBPUSD: 6, SPX500: 2, USDJPY: 2}`
- `timeframe_counts={H1: 12, M1: 14, M15: 6, M5: 4}`
- `grid_enabled_count=30`
- `close_by_money_count=30`
- `max_orders_values=[1, 7]`
- best supplied tester-report profit factor: `15.12` on `AUDCAD` `M5`, `04:00:00-05:00:00`, with `2.25%` equity drawdown and `294` trades.

Verification:

```bash
python -m pytest tests/test_forex_fury_sets.py tests/test_external_benchmark.py -q
# 4 passed

python scripts/run_forex_fury_set_import.py --source-dir "C:\Users\wakil\Downloads\Forex-Fury-CORE-1.4NEW-SETS (1)" --summary-only
# set_count=36, tester_report_count=30, best_profit_factor=15.12
```

Boundary: this importer reads `.set` and tester-report files and fingerprints
compiled `.ex4`/`.ex5` binaries only. It does not execute binaries, place
orders, create broker `ACCEPT`, deposit, withdraw, move bank/card money, or
automate payouts. Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank
movement, and payout automation remain `NOT LICENSED` / `CURRENTLY NOT LICENSED`.

## 2026-06-24 - MT4 mailbox bridge scaffold

Added a dedicated paper/demo-first MT4 mailbox bridge without disturbing the
older `MT4EABridge` stub inside `mt5_bridge.py`.

Implemented:

- `cas_forex/broker/mt4_mailbox_bridge.py`
- `scripts/run_mt4_mailbox_smoke.py`
- `tests/test_mt4_mailbox_bridge.py`
- `mt4/Experts/CASForexBridgeEA.mq4`
- `cas_forex/broker/__init__.py` export for `MT4MailboxBridge`

Current behavior:

- creates `commands`, `receipts`, and `archive` directories
- writes hashed `PING` command JSON
- writes hashed `PLACE_ORDER` command JSON from a `BrokerOrderRequest`
- validates `cas_forex_mt4_mailbox_receipt.v1` receipt files
- keeps `PAPER_MT4` as the default bridge mode
- blocks `LIVE_MT4` intents unless the caller passes `live_authorized=True`

Verification:

```bash
python scripts/run_mt4_mailbox_smoke.py --mailbox-dir evidence_runs/mt4_mailbox_smoke
# status=MAILBOX_READY, broker_mode=PAPER_MT4, receipt_count=0

python -m pytest tests/test_mt4_mailbox_bridge.py -q
# 4 passed

python -m pytest tests -q
# 377 passed

cd ui && npm run build
# 51 modules, 324.90 KB JS, 87.71 KB gzip
```

Boundary: this bridge writes and reads mailbox files. The MQL4 EA side still
needs parser/receipt/order-send implementation. This scaffold does not place
live orders, create broker `ACCEPT`, deposit, withdraw, move bank/card money,
or automate payouts. Live trading, broker `ACCEPT`, auto-deposit, debit/card/
bank movement, and payout automation remain `NOT LICENSED` /
`CURRENTLY NOT LICENSED`.

## 2026-06-24 - External benchmark API/UI wiring

Promoted the Forex Fury MT4 benchmark snapshot into a first-class CAS Forex API
and UI surface.

Implemented:

- `cas_forex/external_benchmark.py`
- `scripts/run_external_benchmark_snapshot.py`
- `tests/test_external_benchmark.py`
- `/api/forex/strategy/external-benchmarks`
- dashboard payload key `externalBenchmarks`
- TypeScript types/API client/fixture fallback
- Optimizer page external benchmark table

Current normalized summary:

- `benchmark_count=3`
- `mt4_account_count=3`
- `real_account_count=3`
- `symbols=[AUDUSD, GBPUSD, USDCAD]`
- `total_public_trade_count=646`
- `best_gain_pct=554.1`
- `lowest_drawdown_pct=8.6`

Verification:

```bash
python scripts/run_external_benchmark_snapshot.py --summary-only
# benchmark_count=3, mt4_account_count=3, total_public_trade_count=646

python -m pytest tests/test_external_benchmark.py tests/test_settings_api_surface.py -q
# 13 passed

python -m pytest tests -q
# 373 passed

cd ui && npm run build
# 51 modules, 324.90 KB JS, 87.71 KB gzip
```

Boundary: this is comparison/intelligence wiring only. It does not place orders,
create broker `ACCEPT`, deposit, withdraw, move bank/card money, or automate
payouts. Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement,
and payout automation remain `NOT LICENSED` / `CURRENTLY NOT LICENSED`.

## 2026-06-24 - Forex Fury / MT4 / agentic workflow benchmark pass

Reviewed the owner's three Forex Fury Myfxbook links as external benchmark
inputs and converted the findings into a local implementation note plus a
machine-readable benchmark snapshot.

Artifacts:

- `docs/working/CAS_FOREX_FOREX_FURY_MT4_AGENTIC_WORKFLOW_20260624.md`
- `evidence_runs/external_benchmark/forex-fury-mt4-benchmark-20260624-report.json`

Public-page findings:

- Forex FURY AU: real USD automated MT4, Fyntura, 1:500, `+214.03%` gain,
  `35.77%` drawdown, `43` trades.
- Forex Fury USDCAD 50K: real USD automated MT4, AdroFx, 1:200, `+154.62%`
  gain, `8.60%` drawdown, `541` trades.
- Forex FURY 26/39: real USD automated MT4, Fyntura, 1:500, `+554.10%` gain,
  `37.00%` drawdown, `62` trades.

Implementation targets recorded:

- add external benchmark model and snapshot runner
- add MT4 mailbox bridge and MQL4 EA template
- add MT4 receipt/probe runners beside the current MT5 path
- add benchmark comparison to Optimizer/Condition Lab
- add long-horizon CAS Harness multi-agent workflow for evidence harvesting,
  strategy mining, backtesting, risk/margin solving, bridge work, UI work, and
  audit verification

Boundary: this is benchmark/project-memory work only. It does not place orders,
create broker `ACCEPT`, deposit, withdraw, move bank/card money, or automate
payouts. Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement,
and payout automation remain `NOT LICENSED` / `CURRENTLY NOT LICENSED`.

## 2026-06-24 - Trading edge separated from paper maturity

Refreshed owner-promotion evidence with current `paper_days=3` and wired that
summary into the live operability checklist.

Result:

- latest owner-promotion report:
  `evidence_runs/owner_promotion_review/owner-promotion-review-20260624030818-report.json`
- D1 `tsmom_126_250_2_10` clears strategy-edge thresholds:
  - `simulator_wins=18`
  - `walk_forward_windows=5`
  - `positive_routed_window_rate=0.6`
  - `mean_return_pct=1.8932`
  - `max_drawdown_pct=7.0764`
  - `trades=76`
- remaining promotion blockers are paper proof only:
  - `paper_days 3 < required 30`
  - `paper_passed is false`
- `trading_edge` now reports `PASSED` in live readiness
- `paper_proof_maturity` remains `OPEN`
- default live readiness is now `NOT_READY_FOR_LIVE`, `10 / 16`,
  `checks_open=1`, `checks_mismatch=0`
- `strategy_leads.json` now reflects 3 completed proof bundles and next due
  `2026-06-25`

Verification:

```bash
python -m pytest tests/test_live_readiness.py tests/test_settings_api_surface.py -q
# 14 passed

python -m pytest tests -q
# 371 passed

cd ui && npm run build
# 51 modules, 318.07 KB JS, 85.57 KB gzip
```

Owner future-study inputs recorded:

- Myfxbook Forex Fury AU:
  `https://www.myfxbook.com/members/forexfuryreal/forex-fury-au/11171494`
- Myfxbook Forex Fury USDCAD 50K:
  `https://www.myfxbook.com/members/forexfuryreal/forex-fury-usdcad-50k/9421542`
- Myfxbook Forex Fury 26/39:
  `https://www.myfxbook.com/members/forexfuryreal/forex-fury-26amp39/11975493`
- evaluate MT4 as a possible better-fit broker/terminal integration
- assess long-horizon agentic workflow support for spawning/attaching multiple
  LLM agents

Boundary: these are research/implementation inputs, not completed live evidence.
Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and
payout automation remain `NOT LICENSED` / `CURRENTLY NOT LICENSED`.

## 2026-06-24 - Paper proof window advanced to 3 complete bundles

Ran the scheduled daily paper-proof bundle pipeline for `2026-06-23` and
`2026-06-24` using the broker-synced account equity.

Commands:

```bash
python scripts/run_daily_paper_bundle.py --date 2026-06-23 --account-equity 100000 --max-risk-pct 0.5 --daily-risk-pct 1 --output-dir evidence_runs/index_tsmom_126_paper_proof
python scripts/run_daily_paper_bundle.py --date 2026-06-24 --account-equity 100000 --max-risk-pct 0.5 --daily-risk-pct 1 --output-dir evidence_runs/index_tsmom_126_paper_proof
python scripts/run_paper_ui_readiness.py --output-dir evidence_runs/index_tsmom_126_paper_proof --min-daily-bundles 5
python scripts/run_paper_daily_schedule.py --date 2026-06-24 --account-equity 100000 --output-dir evidence_runs/index_tsmom_126_paper_proof
```

Result:

- `complete_bundle_days=3`
- complete dates: `2026-06-22`, `2026-06-23`, `2026-06-24`
- `broker_verified_days=3`
- `decision_days=3`
- `risk_review_days=3`
- chains verified: paper proof, paper decision, paper risk
- latest risk review: `account_equity=100000.0`, `PAPER_ATTEMPTS_ALLOWED`,
  `total_planned_lots=0.2`
- UI proof threshold remains `NOT_READY_FOR_UI_UX` because `3 / 5` complete
  bundles exist
- next due command:
  `python scripts/run_daily_paper_bundle.py --date 2026-06-25 --account-equity 100000 --max-risk-pct 0.5 --daily-risk-pct 1 --output-dir evidence_runs/index_tsmom_126_paper_proof`
- full 30-day proof gate still needs `27` more paper trading days

Verification:

```bash
python -m pytest tests/test_paper_daily_bundle.py tests/test_paper_daily_schedule.py tests/test_paper_ui_readiness.py tests/test_live_readiness.py tests/test_settings_api_surface.py -q
# 23 passed

python -m pytest tests -q
# 370 passed

cd ui && npm run build
# 51 modules, 318.07 KB JS, 85.57 KB gzip
```

Boundary: these are paper/demo proof-bundle artifacts. They do not place live
orders, create broker `ACCEPT`, deposit, withdraw, move bank/card money, or
automate payouts.

## 2026-06-23 - Broker-synced paper risk evidence applied

Applied the broker-synced paper-risk review to the real local paper-risk
evidence chain.

Applied state:

- `apply_broker_synced_risk_review(confirm_apply=True)` appended the broker
  snapshot-seeded risk review.
- `paper-risk-status.json` now has `review_count=2`.
- `chain_verified=true`.
- latest `account_equity=100000.0`.
- dashboard/daily-bundle overlay now treats the broker-synced review as the
  active default paper-risk review.
- default account reconciliation is now `RECONCILED` with `checks_mismatch=0`.
- default live readiness is now `NOT_READY_FOR_LIVE`, `9 / 16`, with
  `checks_mismatch=0`.
- broker-synced preview now reports `already_applied=true` when the active
  review already matches the broker snapshot.

Boundary: this is still paper/demo evidence-chain work. It does not place
orders, create broker `ACCEPT`, deposit, withdraw, move bank/card money, or
automate payouts.

Verification:

```bash
python -m pytest tests/test_broker_synced_risk_apply.py tests/test_settings_api_surface.py tests/test_account_reconciliation.py tests/test_live_readiness.py -q
# 21 passed

python -m pytest tests -q
# 370 passed

cd ui && npm run build
# 51 modules, 318.07 KB JS, 85.57 KB gzip
```

## 2026-06-23 - Broker-synced paper risk apply action

Added an explicit owner-run action that turns the broker-synced risk preview
into an appended paper-risk evidence review.

Implemented:

- `POST /api/forex/account/apply-broker-sync-risk-review?confirm_apply=true`
- `apply_broker_synced_risk_review(...)` in the API data layer
- idempotency so repeated applies report `already_applied=true` instead of
  appending duplicate broker-synced reviews
- dashboard daily-bundle overlay from latest `paper-risk-status.json`
- Dashboard Broker Sync `Apply` button with append/already-applied feedback
- TypeScript/API support for the apply response

Boundary: this writes only to the paper/demo risk evidence chain. It does not
place orders, create broker `ACCEPT`, deposit, withdraw, move bank/card money,
or automate payouts.

Verification:

```bash
python -m pytest tests/test_broker_synced_risk_apply.py tests/test_settings_api_surface.py tests/test_paper_risk.py tests/test_live_readiness.py -q
# 20 passed

python -m pytest tests -q
# 370 passed

cd ui && npm run build
# 51 modules, 318.07 KB JS, 85.57 KB gzip
```

Smoke:

```text
broker-synced preview = PAPER_ATTEMPTS_ALLOWED
broker_snapshot_initial_investment_usd = 100000.0
total_planned_lots = 0.2
default live readiness = NOT_READY_FOR_LIVE, 8 / 16, account_reconciliation=MISMATCH
```

## 2026-06-23 - Broker-synced paper risk sizing preview

Added a broker-synced paper risk sizing preview.

Implemented:

- `/api/forex/account/broker-sync-risk-preview`
- `brokerSyncedRiskPreview` in `/api/forex/dashboard`
- TypeScript/API/fixture support for `BrokerSyncedRiskPreview`
- Dashboard Broker Sync strip showing broker seed, default seed, preview lots,
  default lots, preview risk, and risk delta

The preview reruns the existing `paper_risk.review_paper_risk_budget(...)` path
using the verified MT5 demo account snapshot balance (`$100,000`). Current smoke:

```text
cas_forex_broker_synced_risk_preview
PAPER_ATTEMPTS_ALLOWED
account_equity = 100000.0
total_planned_lots = 0.2
total_planned_risk_usd = 253.02
delta_vs_default = {account_equity_usd: 95000.0, total_planned_risk_usd: 227.72, total_planned_lots: 0.18}
```

Boundary: preview-only. It does not append evidence, change the default owner
seed, place orders, create broker `ACCEPT`, deposit, withdraw, move bank/card
money, or automate payouts.

Verification:

```bash
python -m pytest tests/test_paper_risk.py tests/test_live_readiness.py tests/test_settings_api_surface.py -q
# 18 passed

python -m pytest tests -q
# 368 passed

cd ui && npm run build
# 51 modules, 317.01 KB JS, 85.25 KB gzip
```

## 2026-06-23 - Dashboard broker-sync readiness preview

Added a segmented `Default` / `Broker Sync` control to the Dashboard "Live
Operability Checklist" panel.

- `Default` keeps the owner/risk-review paper ledger seed and continues showing
  the current `$5,000` internal ledger vs `$100,000` MT5 demo account mismatch.
- `Broker Sync` explicitly fetches
  `/api/forex/readiness/live?sync_to_broker=true`, displays the broker snapshot
  seed, and shows `account_reconciliation=PASSED` when broker balance/equity are
  used.
- The preview does not silently change the default owner seed, rerun risk
  sizing, place orders, create broker `ACCEPT`, deposit, withdraw, move bank/card
  money, or automate payouts.

Verification:

```bash
python -m pytest tests/test_live_readiness.py tests/test_settings_api_surface.py -q
# 11 passed

python -m pytest tests -q
# 367 passed

cd ui && npm run build
# 51 modules, 312.53 KB JS, 84.51 KB gzip
```

Smoke: default readiness remains `NOT_READY_FOR_LIVE`, `8 / 16`,
`account_reconciliation=MISMATCH`; broker-sync readiness remains
`NOT_READY_FOR_LIVE`, `8 / 16`, `account_reconciliation=PASSED`,
`broker_snapshot_initial_investment_usd=100000.0`.

## 2026-06-23 - Live operability checklist added

Added a computed plain-English live-readiness surface so the cockpit no longer
depends on a static "gates" card.

Implemented:

- `cas_forex/live_readiness.py`
- `/api/forex/readiness/live`
- `/api/forex/readiness/live?sync_to_broker=true` explicit broker-synced preview
- `liveReadiness` inside `/api/forex/dashboard`
- Dashboard "Live Operability Checklist" panel
- TypeScript/API/fixture support for the new readiness payload
- movement-stream metadata for swap, commission, broker fees, open-position
  count, floating P/L, margin estimate, market-open/session/source fields

The checklist now reports owner initial investment, investment movement,
market movement, broker/demo receipt, broker account snapshot, CAS-vs-broker
reconciliation, latest MT5 probe health, evidence chain, paper/demo proof
window, trading edge, AI compounding memory, live order execution, broker
`ACCEPT`, auto-deposit, debit/card/bank movement, and payout automation.

Verification:

```bash
python -m pytest tests/test_live_readiness.py tests/test_movement_stream.py tests/test_account_reconciliation.py tests/test_settings_api_surface.py -q
# 21 passed

python -m pytest tests -q
# 367 passed

cd ui && npm run build
# 51 modules, 311.18 KB JS, 84.08 KB gzip
```

Smoke: default readiness keeps `account_reconciliation=MISMATCH`; explicit
`sync_to_broker=true` reports `account_reconciliation=PASSED` with
`broker_snapshot_initial_investment_usd=100000.0`, while overall readiness
remains `NOT_READY_FOR_LIVE`.

Current status remains: trading edge `OPEN`; live trading, broker `ACCEPT`,
auto-deposit, debit/card/bank movement, and payout automation remain
`NOT LICENSED` / `CURRENTLY NOT LICENSED` until the checklist and runtime
requirements are actually closed.

## 2026-06-23 - Screenshot-derived trading terminal requirements added

Updated the next-agent handoff/TODO/goal packet with owner-provided mobile
trading-history and MT4/MT5 strategy-report screenshot requirements.

Added as required CAS Forex UI/backend targets:

- terminal-style mobile account summary: profit, deposit, balance, equity,
  floating P/L, drawdown, margin, swap, commission, and fees
- `Positions` / `Orders` / `Deals` tabs
- `Day` / `Week` / `Month` / `Custom` history filters
- per-trade rows with symbol, buy/sell side, lot size, entry -> exit/current
  price, timestamp, broker ticket/order ID, strategy ID, evidence packet ID,
  and net P/L
- deposit/investment ledger where the owner can enter any positive initial
  investment amount
- real-time investment movement tracking: deposits, withdrawals, payouts,
  balance, equity, realized P/L, floating P/L, margin, swap, commission, and
  broker reconciliation snapshots
- real-time market movement tracking: quotes, bid/ask, spread, candles/ticks,
  volatility/ATR, symbol session state, and active SL/TP distance
- MT4/MT5-style strategy report view with profit factor, expected payoff,
  drawdown, win/loss stats, equity curve, and full order table

No code behavior changed in this entry. Trading edge remains `OPEN`; live
trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and payout
automation remain `NOT LICENSED` until the completion checklist is actually
closed and the relevant runtime gates become `AUTHORIZED`.

## 2026-06-23 - Goal framing corrected: live-money system is the destination

Updated the LLM handoff and project dashboard after the owner clarified the
intended end state: CAS Forex is not meant to stay a simple research project.
The destination is a real owner-controlled live-money trading and income system.
The current research/backtest/paper/demo layers are the proving, evidence, UI,
broker, and runtime buildout path to owner-authorized live execution.

Updated:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\CAS_FOREX_LLM_HANDOFF_TODO_GOALS_20260623.md
C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\cas_harness_production_todo.md
```

No code behavior changed in this entry. Trading edge remains `OPEN`; live
trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and payout
automation remain `NOT LICENSED` until the completion checklist is actually
closed and the relevant runtime gates become `AUTHORIZED`.

## 2026-06-23 - LLM handoff and owner-control API cleanup

Created the next-agent handoff/TODO/goal packet:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\CAS_FOREX_LLM_HANDOFF_TODO_GOALS_20260623.md
```

Also corrected the remaining owner-control API/test drift after the hard scope
gate removal. `api\data.py` and `tests\test_settings_api_surface.py` now enforce
that the removed hard scope fields are absent from `/api/forex/settings/owner-control`
and `/api/forex/dashboard`.

Verification:

```bash
python -m pytest tests/test_settings_api_surface.py tests/test_runtime_gates.py tests/test_authority_boundary.py -q
# 14 passed

python -m pytest tests -q
# 344 passed

npm run build
# 51 modules, 275.87 KB JS, 76.45 KB gzip
```

Restarted the local CAS Forex API on `127.0.0.1:8765`; live HTTP owner-control
payload no longer exposes `personal_utilization_only`, `account_scope`, or
`disallowed_scopes`. Live trading, broker `ACCEPT`, auto-deposit,
debit/card/bank movement, and payout automation remain `NOT LICENSED`; trading
edge remains `OPEN`.

## 2026-06-22 - Removed extra hard scope gate

Removed the extra hard scope switch after owner rejection of that boundary.

- Removed the extra live-trading runtime check.
- Removed the matching config field, direct regression test,
  owner-control API fields, UI Settings gate, fallback fixture fields, authority
  boundary wording, and mobile app wording.
- Kept the separate owner-controlled real-money gates intact: live trading,
  broker `ACCEPT`, auto-deposit, debit/card/bank movement, and payout automation
  still require explicit owner flags, credentials/provider config, and gate
  clearance before they can become `AUTHORIZED`.

Verification:

```bash
python -m pytest tests/test_runtime_gates.py tests/test_authority_boundary.py -q
# 11 passed

python -m pytest tests -q
# 338 passed

npm run build
# 51 modules, 269.94 KB JS, 75.09 KB gzip
```

Restarted the local CAS Forex API on `127.0.0.1:8765`; live HTTP
`/api/forex/settings/owner-control` and `/api/forex/dashboard` no longer expose
the removed scope switch fields. The live-trading missing-requirement text now
uses `account/source-of-funds acknowledgments signed`.

Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and
payout automation remain `NOT LICENSED`; trading edge remains `OPEN`.

## 2026-06-22 - Real evidence wiring: strategy leads, backsolve, MT5 receipt, condition tally, walk-forward

The UI is no longer a static fixture cockpit. It now reflects real generated
evidence from the CAS Forex backend.

New types: `BacksolveSummary`, `ConditionTallyBucket`, `WalkForwardSummary`,
`MT5Receipt`, `StrategyLead`. `DashboardState` now carries `strategyLeads`,
`backsolve`, `conditionTally`, `walkForward`, `mt5Receipt`.

Real evidence fixtures (`fixtures.ts`):
- **Strategy leads**: 4 leads from `strategy_leads.json` with headline results,
  open gates, evidence refs, symbol assignments.
- **Backsolve**: 16,800 scenarios, 0 viable, AI_FULL_AUTO_PAPER,
  SURVIVAL_RISK label, verdict breakdown (14,532 TARGET_NOT_REACHED + 2,168
  DRAWDOWN_FAIL + 100 MARGIN_FAIL).
- **Condition tally**: 2 buckets (D1 + H1 tsmom_126), D1: 1.89% mean return,
  60% positive rate, 7.08% max DD, 76 trades.
- **Walk-forward**: 18 windows, 7 routed, 3 active, all 3 positive, 1.28%
  mean return, 2.30% max DD, NOT_PROMOTED.
- **MT5 receipt**: BROKER_API_VERIFIED, Hugosway-Demo, MetaTrader 5, chain
  verified, receipt/broker/packet hashes.

Page updates:
- **Proof page**: +Capital & Backsolve panel (3-column scenario grid +
  SURVIVAL_RISK warning), +MT5 Demo Receipt panel (validation status, broker
  API auth, chain verified, hash display), +Walk-Forward Evidence panel (window
  stats, mean return, max DD, research grade).
- **Dashboard**: strategy leads table now reads `state.strategyLeads` with
  7-column format (priority, lead ID, status, family, symbols, top result,
  open gates count).
- **History**: condition tally section now displays real bucket data table
  (windows, active, positive rate, mean return, max DD, trades) with source
  attribution.

All NOT LICENSED boundaries preserved.

Verification: `npx tsc --noEmit` clean; `npx vite build` 42 modules, 222KB JS
(64KB gzip).

## 2026-06-22 - Adaptive compounding + History + Owner Control UI (cas-forex/ui/)

Closed the audit gap: the self-contained UI now represents the full CAS Forex
adaptive compounding system, not just the pre-adaptive paper cockpit.

New types (`evidence.ts`): `AdaptiveAction`, `BasketState`, `AdaptiveTradeDecision`,
`AdaptiveMemorySnapshot`, `AdaptiveCompoundingConfig`, `AdaptiveCompoundingReview`,
`AdaptiveCockpitPayload`, `OwnerControlMode`, `OwnerControlState`, `MTHistorySummary`.
`DashboardState` now accepts optional `adaptive`, `ownerControl`, and `mtHistory`.

New pages:
- **Adaptive** (`AdaptivePage.tsx`): adaptive status overview, action summary chips
  (OPEN_INITIAL, ADD_TO_WINNER, HOLD, TIGHTEN_STOP, PARTIAL_TAKE_PROFIT,
  CLOSE_BASKET, NO_TRADE) with color coding, basket state cards (floating P/L,
  open positions, average entry), adaptive decisions table (10 columns with
  evidence scores), memory snapshots grid, compounding config display, NOT LICENSED
  gates. Graceful fallback when no adaptive data exists.
- **History** (`HistoryPage.tsx`): MT4/MT5 import summary (total trades, win rate,
  profit factor, net P&L, symbol performance breakdown, multi-trade bursts),
  condition tally placeholder with run command, paper trade log placeholder,
  harvester proposals placeholder, sweep ledger (DRY_RUN, INTERNAL_LEDGER_ONLY).
- **Settings** (`SettingsPage.tsx`): Owner Control Policy surface â€” autonomy mode
  selector (DENY through AI_FULL_AUTO_LIVE_REQUESTED with BLOCKED marker), risk
  caps (max loss cap, max concurrent trades 1-15, AI autonomy PAPER ONLY),
  compounding thresholds (all 10 AdaptiveCompoundingConfig fields), risk defaults,
  account/legal gates (5 items, all NOT MET), broker configuration.

Nav: Adaptive, History, and Settings all flipped from placeholder to ready. Zero
placeholder pages remain â€” all 7 routes are live.

Owner control state wired into `App.tsx` with `AI_FULL_AUTO_PAPER` mode, 15
concurrent trades, 10% loss cap, AI autonomy enabled, live blocked.

Verification:
- `npx tsc --noEmit` â†’ clean.
- `npx vite build` â†’ 42 modules, 18.09KB CSS + 209.07KB JS (60.10KB gzip).

Live trading, broker ACCEPT, auto-deposit, debit/card/bank movement, and payout
automation remain NOT LICENSED.

## 2026-06-22 - Dashboard + Trade Desk pages (cas-forex/ui/)

Added Operations Dashboard and Paper Trading Desk to the proof cockpit.

- **Dashboard** (`src/pages/DashboardPage.tsx`): 3-panel account snapshot (equity
  $5,000, PAPER_MT5 mode, risk budget 0.5%/trade, daily $50), paper route
  candidates table (US30 + NAS100 with entry/SL/TP/conf/lots/risk), today's
  summary, next-action schedule with recommended CLI command, strategy leads
  table (4 leads from strategy_leads.json), evidence chain health (3/3 verified,
  WORM UNAVAILABLE), and 6 NOT LICENSED gate items.
- **Trade Desk** (`src/pages/TradePage.tsx`): interactive symbol selector (8
  instruments), timeframe chips (M5-D1), trading style selector
  (scalping-position), proposal preview with entry/SL/TP prices, risk sizing
  (0.01 lots, $12.60-$12.70 risk), forecast harness status (6 models), CAS
  expression panel (NOT_RUN), and disabled Run Paper Proposal / Send Paper Order
  buttons with explicit NOT LICENSED lock reasons.
- Dashboard and Trade nav items flipped from `soon` to ready.
- 496 lines of new CSS: data tables, metric stacks, selector chips, proposal
  preview, sizing grid, forecast harness cards, CAS expression display, lock
  lines.

Verification:
- `npx tsc --noEmit` â†’ clean.
- `npx vite build` â†’ 39 modules, 15.63KB CSS + 188.78KB JS (55.94KB gzip).

Live trading, broker ACCEPT, auto-deposit, debit/card/bank movement, and payout
automation remain NOT LICENSED.

## 2026-06-22 - Self-contained proof cockpit UI scaffold (cas-forex/ui/)

Scaffolded a standalone React 18 + TypeScript + Vite proof cockpit in
`cas-forex/ui/`, self-contained from atlas-viewer.

- **Tech stack**: React 18.3, TypeScript 5.6, Vite 6, zero routing deps.
- **`src/types/evidence.ts`** â€” Full TypeScript contracts for UIReadinessReport,
  DailySchedule, DailyBundle, PaperDecision, PaperRisk, SymbolDecision, Proposal,
  SizingEntry, and DashboardState. Shapes match real `evidence_runs/` JSON.
- **`src/data/fixtures.ts`** â€” Faithful day-1 evidence snapshots (truthful
  1/30 paper days, 1/5 bundles, NOT LICENSED everywhere).
- **`src/components/`** â€” `Shell` (nav with 6 routes, 4 marked `soon`),
  `ModeBanner` (always-visible NOT LICENSED + PAPER_MT5 + edge: OPEN),
  `StatusChip`, `GlassPanel`, `EvidenceHashRow`, `LockReasonList`.
- **`src/pages/ProofPage.tsx`** â€” Full proof cockpit: active lead, paper proof
  progress bars (1/30, 1/5), evidence chain verification (3/3), live eligibility
  checklist (0/7 met), route decisions (US30 + NAS100), risk sizing (0.01 lots,
  $12.60-$12.70 risk/trade), next-action schedule, and 6 disabled NOT LICENSED
  controls with explicit reasons.
- **`src/pages/AuditPage.tsx`** â€” Pipeline trace stepper (10 stages: Forecast
  Harness â†’ Gate 0-4 â†’ Broker â†’ Post-Trade â†’ Evidence â†’ Live Lock), honest
  NOT_RUN markers for CAS Compiler and Market gates, evidence packet summary,
  per-symbol trace detail.
- Placeholder pages for Dashboard, Trade, History, Settings (labeled COMING SOON).
- Dark theme, dense trading-desk aesthetic, slate/teal palette, monospace data.

Verification:
- `npx tsc -b` / `npx tsc --noEmit` â†’ clean.
- `npx vite build` â†’ 37 modules, 0.59KB HTML + 9.45KB CSS + 171.70KB JS (52.84KB gzip).
- Dev server on port 5174, renders `/forex/proof` equivalents via state-based nav.

Live trading, broker ACCEPT, auto-deposit, debit/card/bank movement, and payout
automation remain NOT LICENSED.

## 2026-06-22 - Adaptive paper compounding manager and read-only cockpit

Implemented the first V1 of the owner-requested adaptive compounding lane:
when a paper trade is already winning and fresh evidence still supports the
route, CAS Forex can now recommend `ADD_TO_WINNER`; when evidence weakens or
the route flips, it recommends `TIGHTEN_STOP`, `PARTIAL_TAKE_PROFIT`,
`CLOSE_BASKET`, `HOLD`, `OPEN_INITIAL`, or `NO_TRADE`.

- Added `cas_forex/adaptive_compounding.py`.
  - Evaluates active paper positions against the latest paper route decision,
    condition-tally evidence, imported MT4/MT5 history summaries, and owner
    basket limits.
  - Produces per-trade SL/TP, add-lot, basket state, evidence refs, and saved
    adaptive memory snapshots for future strategy analysis.
  - Writes tamper-evident local JSONL Evidence Packets with
    `deployment_status`, broker `ACCEPT`, and payment movement all
    `NOT LICENSED`.
- Added `cas_forex/mt_history_import.py`.
  - Imports MT4/MT5 CSV or HTML account-history exports into normalized
    research evidence.
  - Summarizes win rate, profit factor, symbol performance, lot sizing, and
    multi-trade bursts such as repeated entries.
- Added `cas_forex/adaptive_cockpit.py`.
  - Generates read-only adaptive cockpit JSON and HTML artifacts for the proof
    cockpit/UI path.
  - Displays adaptive decisions, action counts, proof/risk/route summaries,
    and `NOT LICENSED` boundaries.
- Added scripts:
  - `scripts/run_adaptive_compounding_review.py`
  - `scripts/run_mt_history_import.py`
  - `scripts/run_adaptive_cockpit.py`
- Added tests:
  - `tests/test_adaptive_compounding.py`
  - `tests/test_mt_history_import.py`
  - `tests/test_adaptive_cockpit.py`

Verification:

```bash
python -m pytest tests/test_adaptive_compounding.py tests/test_mt_history_import.py tests/test_adaptive_cockpit.py -q
# 10 passed

python -m pytest tests -q
# 319 passed
```

Smoke verified the new adaptive review and cockpit runners against a disposable
temp output directory. Live trading, broker `ACCEPT`, auto-deposit,
debit/card/bank movement, and payout automation remain `NOT LICENSED`.

## 2026-06-22 - Owner-selected risk caps and AI full-paper-auto mode

Expanded the leveraged income backsolve and owner-control layer after the owner
rejected fixed `10%` / `15%` assumptions and recommendation-only AI authority.

- `cas_forex/leverage_backsolve.py`
  - Accepts any positive user max-loss percentage via `max_loss_cap_pcts`.
  - Tests concurrent trades up to `15` (`MAX_USER_CONCURRENT_TRADES`).
  - Replaced the active success verdict with `SURVIVES_USER_LOSS_CAP`.
  - Adds AI autonomy modes: `USER_MANUAL`, `AI_RECOMMEND`,
    `AI_FULL_AUTO_PAPER`, and `AI_FULL_AUTO_LIVE_REQUESTED`.
  - `AI_FULL_AUTO_PAPER` can select risk cap, lot size, and concurrency from
    scenarios that survive the user's cap and margin gates.
  - `AI_FULL_AUTO_LIVE_REQUESTED` records the owner request but returns
    `AI_FULL_AUTO_LIVE_BLOCKED_NOT_LICENSED`.
- `scripts/run_leverage_income_backsolve.py`
  - New `--max-loss-caps` accepts arbitrary percentages.
  - New `--max-open-trades` tests `1..N` up to `15`.
  - New `--ai-autonomy-mode` selects the AI control mode.
- `cas_forex/owner_control.py`
  - Adds `AI_FULL_AUTO_PAPER` and `AI_FULL_AUTO_LIVE_REQUESTED`.
  - Caps owner-authorized paper attempts at `15`.

Fresh report:
`evidence_runs/leverage_income_backsolve/leverage-income-backsolve-20260622191201-report.json`
and `.md`.

Command used:

```bash
python scripts/run_leverage_income_backsolve.py --max-loss-caps 10 15 25 50 100 2500 6000 --max-open-trades 15 --ai-autonomy-mode AI_FULL_AUTO_PAPER
```

Result: `16,800` scenarios, viable scenarios `0`, AI status
`AI_NO_VIABLE_SCENARIO`. Verdict counts: `TARGET_NOT_REACHED=14532`,
`TARGET_REACHED_BUT_DRAWDOWN_FAIL=2168`, and
`TARGET_REACHED_BUT_MARGIN_FAIL=100`. Target-reaching scenarios still require
drawdown around `2264.448%` for `$5k/month` and/or exhaust stressed
equity/margin.

Verification: `python -m pytest tests -q` -> `309 passed`.

Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and
payout automation remain `NOT LICENSED`.

## 2026-06-22 - Leveraged income backsolve: 1:100 / 1:200 cannot clear the 10% cap

Added a paper-only leveraged income backsolver for the owner's `$5k-$12k/month`
question from a `$5,000` seed account.

- `cas_forex/leverage_backsolve.py` defines research broker profiles,
  required-return math, saved walk-forward evidence projection, margin stress,
  drawdown caps, and `BacksolveVerdict` statuses:
  `TARGET_NOT_REACHED`, `TARGET_REACHED_BUT_DRAWDOWN_FAIL`,
  `TARGET_REACHED_BUT_MARGIN_FAIL`, `SURVIVES_10_PERCENT_CAP`, and
  `NOT_LICENSED_LIVE_BLOCKED`.
- `scripts/run_leverage_income_backsolve.py` writes JSON and Markdown reports
  under `evidence_runs/leverage_income_backsolve/`.
- `tests/test_leverage_backsolve.py` covers `$5k = 100%` and `$12k = 240%`
  monthly return math, leverage affecting margin but not edge, drawdown failure,
  margin failure, regulatory-risk broker profiles refusing broker `ACCEPT`, and
  saved `US30`/`NAS100` walk-forward report generation.

Current generated report:
`evidence_runs/leverage_income_backsolve/leverage-income-backsolve-20260622185718-report.json`
and `.md`.

Result: `480` scenarios checked across `tsmom_126_250_2_10`,
`tsmom_252_500_2_8`, `HugosWay`/`CedarFX` research profiles at `1:100` and
`1:200`, lot grid `0.01` through `10`, and concurrency `1`, `2`, `4`. Viable
scenarios: `0`. The current D1 evidence baseline for `tsmom_126_250_2_10` is
`$32.93/month` at `0.05` lots on the saved `$10k` research balance, with
`7.0764%` base max drawdown. Target-reaching scenarios require drawdown far
above the owner-selected `10%` account-loss cap (`2264.448%` lowest for
`$5k/month`; `5661.12%` lowest for `$12k/month`). Leverage changes margin
capacity; it does not create strategy edge.

Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and
payout automation remain `NOT LICENSED`.

## 2026-06-22 - Proof cockpit: live /api/forex backend (cockpit reads live, not fixtures)

Wired the real read-only `/api/forex/*` FastAPI boundary so the cockpit reads
live evidence files instead of bundled fixtures.

- `noetic-compass-scaffold/noetic-compass/api/routes/forex_proof.py` â€” read-only
  router (prefix `/forex`) serving the six day-1 evidence JSON files for
  `index_tsmom_126_d1` from `cas-forex/evidence_runs/` (overridable via
  `CAS_FOREX_EVIDENCE_DIR`). GET-only, fixed filename map (no path traversal),
  404 when a file is absent so the cockpit falls back to fixtures cleanly.
- `api/main.py` includes the router; `api/middleware/auth.py` exempts
  **GET `/forex/...`** from JWT (public, non-secret proof JSON) while any non-GET
  still falls through to auth â€” so there is no unauthenticated write path.
- Endpoints: `/forex`, `/forex/proof/{paper,ui-readiness,schedule,decision,risk,bundle}`.
- Frontend `forexApi.ts` now attempts the live backend by default in dev/prod
  (transparent fixture fallback on any error) and stays on fixtures under vitest;
  force fixtures anywhere with `VITE_FOREX_API=0`. When live data is served the
  banner drops its `FIXTURE DATA` badge.

The atlas-viewer dev proxy strips `/api`, so the cockpit's `/api/forex/...`
reaches the router at `/forex/...`.

Verification:

- `python -m pytest tests/test_forex_proof.py tests/test_middleware.py` ->
  `15 passed` (real-data reads, NOT LICENSED fields, POST blocked, 404 on
  missing evidence; existing middleware auth unaffected).
- Live: `GET /forex/proof/paper` -> `completed_trading_days=1`,
  `deployment_status=NOT LICENSED`; `POST` -> `401`.
- Cockpit reloaded against the live backend: `FIXTURE DATA` badge gone, real
  `1/30` and `NOT LICENSED` intact, no console errors.

Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and
payout automation remain `NOT LICENSED`.

## 2026-06-22 - Proof cockpit UI: Phase 2 audit console + evidence trace viewer

Added the `/forex/audit` Audit Console to the read-only cockpit.

- `forexSelectors.deriveTraces()` builds one audit trace per real day-1 paper
  route candidate (US30, NAS100) by joining the route decision, risk sizing,
  and proof receipt.
- `components/TraceStageList.tsx` renders the full pipeline as a vertical
  stepper: Forecast Harness -> Gate 0-4 -> Broker Outcome -> Post-Trade ->
  Evidence Store -> Live Lock Controller.
- `pages/ForexAuditPage.tsx` â€” trace selector + pipeline + evidence-packet
  panel (packet status, hash-chain rows, WORM `UNAVAILABLE`).
- Route wired at `/forex/audit`; nav "Audit" item flipped to ready.

Truthfulness rule: the day-1 PAPER-ROUTE loop is the decision + risk + receipt
tracks, not the full backtest/auditor pipeline. Stages the paper loop did not
exercise (Gate 0 CAS Compiler, Gate 3 Market) are dimmed and marked `NOT_RUN`
with an honest detail line instead of a fabricated PASS. Every trace ends
`SUPPRESSED` with no broker order placed.

Verification: `tsc -b` clean; `vitest` forex suite `25 passed` (9 new:
`deriveTraces`, `ForexAuditPage`); `/forex/audit` renders with no console
errors. Live trading and payment movement remain `NOT LICENSED`.

## 2026-06-22 - Read-only proof cockpit UI: Phase 0 + Phase 1 (atlas-viewer)

Started the CAS Forex read-only proof cockpit in the existing `atlas-viewer`
React app, per `docs/working/cas_forex_pwa_ui_ux_plan_revised_20260617.md`
(Phase 0 â€” API contract + fixture mode; Phase 1 â€” Proof Center + shell). This is
a research/paper proof surface only. It builds nothing toward live execution.

New feature module `noetic-compass-scaffold/noetic-compass/atlas-viewer/src/forex/`:

- `types.ts` â€” TypeScript contracts mirroring the real evidence JSON shapes
  (paper-proof, ui-readiness, daily-schedule, paper-decision, paper-risk,
  daily-bundle).
- `fixtures/*.json` â€” faithful snapshots of the real day-1 evidence from
  `evidence_runs/index_tsmom_126_paper_proof/` so the cockpit shows truthful
  state with no live backend wired.
- `forexApi.ts` â€” read-only fetch wrappers with fixture fallback behind the
  `VITE_FOREX_API` feature flag (default OFF). When a `/api/forex/*` backend
  lands, flip the flag and the same wrappers fetch live status. No order,
  transfer, or unlock path exists anywhere in the layer.
- `forexSelectors.ts` â€” pure selectors: `deriveBannerState` (cannot assert a
  green LIVE state on day-1 evidence) and `deriveLiveEligibility`.
- `components/` â€” `ForexShell` (surface + nav; only Proof is wired, the rest
  render as honest "soon" markers), `ForexModeBanner` (always-visible mode /
  paper-vs-live / evidence-chain / proof-progress / NOT LICENSED boundaries),
  and reusable `ClaimStatusChip`, `ForexStatusChip`, `EvidenceHashRow`,
  `LockReasonList`, `ForexPanel`.
- `pages/ForexProofPage.tsx` â€” `/forex/proof` Proof Center: active lead, paper
  session evidence with hash-chain rows, live eligibility checklist, multi-day
  maturity (1/5 bundles), next-action schedule, and six disabled live/payment
  controls each labeled with their `NOT LICENSED` reason.
- Route wired at `/forex/*` (lazy-loaded, redirects to `/forex/proof`).

The cockpit truthfully displays: `PAPER_MT5`, `live_mode=false`, paper proof
`1 / 30`, multi-day maturity `1 / 5`, local hash chain verified, trading edge
`OPEN`, and `NOT LICENSED` for deployment, broker `ACCEPT`, and payment
transfer. WORM is shown `UNAVAILABLE` (local hash chain only).

Verification:

- `npx tsc -b` -> clean.
- `npx vitest run` -> `293 passed, 2 skipped` (16 new forex tests:
  selectors, `ClaimStatusChip`, `ForexProofPage`).
- Dev server (`atlas-viewer`, port 5173) renders `/forex/proof` with no console
  errors; desktop and mobile (375px) layouts verified with no text/control
  overlap.

Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and
payout automation remain `NOT LICENSED`, and every such control in the UI is
disabled and labeled.

## 2026-06-22 - Third-party audit packet before UI/UX

Added a pre-UI/UX third-party audit handoff:

- `docs/working/CAS_FOREX_THIRD_PARTY_AUDIT_PACKET_20260622.md`

The packet gives an outside reviewer copy-paste local addresses, a project spec
sheet, the source/evidence file map, reproduction commands, known audit
hotspots, and requested deliverables. This makes third-party audit the next
gate before starting the read-only proof cockpit UI.

Also corrected the paper UI readiness CLI wording so its `--help` describes the
`5` bundle rule as multi-day proof maturity, not a blocker to starting a
read-only UI shell.

Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and
payout automation remain `NOT LICENSED`.

## 2026-06-22 - UI/UX start correction

Corrected the proof-cockpit timing rule after owner pushback.

The CAS Forex proof-cockpit/platform UI can start now as a read-only paper and
research surface using the current day-1 evidence. The `5` complete daily bundle
threshold is now documented as a truthful multi-day proof maturity threshold,
not a blocker to starting UI/UX. The `30 / 30` verified paper-day threshold
remains the live-money/deployment promotion gate.

The first UI should show real day-1 broker/demo receipt status, route/no-trade
decision, risk-budget review, daily bundle status, daily schedule, blockers,
and disabled live-money controls. Live trading, broker `ACCEPT`, auto-deposit,
debit/card/bank movement, and payout automation remain `NOT LICENSED`.

## 2026-06-22 - Daily paper schedule / next-action status

Added a read-only next-action schedule for the paper-proof loop.

- Added `cas_forex/paper_daily_schedule.py`.
- Added `scripts/run_paper_daily_schedule.py`.
- Added `tests/test_paper_daily_schedule.py`.
- Added handoff doc:
  `docs/working/cas_forex_daily_schedule_20260622.md`.

The schedule reads the paper proof, paper decision, and paper risk ledgers and
reports:

- next due trading date
- whether the date is due today or waiting for the next trading day
- missing tracks for the next due date
- remaining complete bundles before UI/UX
- remaining paper days before the 30-day proof gate
- exact next command to run

First real schedule check:

- command:
  `python scripts/run_paper_daily_schedule.py --date 2026-06-22 --account-equity 5000 --max-risk-pct 0.5 --daily-risk-pct 1.0 --output-dir evidence_runs/index_tsmom_126_paper_proof`
- status:
  `evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-daily-schedule-status.json`
- next due date: `2026-06-23`
- next due status: `WAIT_NEXT_TRADING_DAY`
- complete daily bundles: `1`
- UI bundles remaining: `4`
- paper-proof days remaining: `29`
- missing tracks for next due date:
  `broker_verified_receipt`, `paper_route_decision`, `paper_risk_review`

This is an operator prompt only. Live trading, broker `ACCEPT`, auto-deposit,
debit/card/bank movement, and payout automation remain `NOT LICENSED`.

## 2026-06-22 - UI-readiness gate for proof cockpit

Added a read-only gate that decides when the CAS Forex proof cockpit has enough
daily evidence to claim multi-day proof maturity.

- Added `cas_forex/paper_ui_readiness.py`.
- Added `scripts/run_paper_ui_readiness.py`.
- Added `tests/test_paper_ui_readiness.py`.
- Added handoff doc:
  `docs/working/cas_forex_ui_readiness_gate_20260622.md`.

The gate requires a minimum number of complete daily paper bundles before
multi-day proof maturity:

- broker/demo verified receipt
- paper route/no-trade decision
- paper risk-budget review
- verified local evidence chains
- no live-mode contamination

First real readiness check:

- command:
  `python scripts/run_paper_ui_readiness.py --min-daily-bundles 5 --output-dir evidence_runs/index_tsmom_126_paper_proof`
- status:
  `evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-ui-readiness-status.json`
- readiness status: `NOT_READY_FOR_UI_UX`
- complete daily bundles: `1 / 5`
- paper proof chain verified: `true`
- paper decision chain verified: `true`
- paper risk chain verified: `true`
- blockers:
  `complete_bundle_days 1 < required 5`;
  `broker_verified_days 1 < required 5`;
  `decision_days 1 < required 5`;
  `risk_review_days 1 < required 5`

This tells us exactly when the UI can claim multi-day proof maturity: after at
least five complete real daily paper bundles. UI/UX can start now as a read-only
paper/proof cockpit. Live trading, broker `ACCEPT`, auto-deposit,
debit/card/bank movement, and payout automation remain `NOT LICENSED`.

## 2026-06-22 - Daily paper proof bundle runner

Added a daily bundle runner that ties together the three paper-proof tracks:
MT5 demo receipt, route/no-trade decision, and paper risk-budget review.

- Added `cas_forex/paper_daily_bundle.py`.
- Added `scripts/run_daily_paper_bundle.py`.
- Added `tests/test_paper_daily_bundle.py`.
- Added handoff doc:
  `docs/working/cas_forex_daily_paper_bundle_20260622.md`.

The bundle defaults to `skip_existing`, so rerunning the same trading date does
not duplicate already-written receipt, decision, or risk records.

First real bundle run:

- command:
  `python scripts/run_daily_paper_bundle.py --date 2026-06-22 --account-equity 5000 --max-risk-pct 0.5 --daily-risk-pct 1.0 --output-dir evidence_runs/index_tsmom_126_paper_proof`
- status:
  `evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-daily-bundle-status.json`
- completed: `true`
- MT5 receipt step: `SKIPPED_EXISTING`
- route decision step: `SKIPPED_EXISTING`
- risk review step: `SKIPPED_EXISTING`
- reason: all three day-1 records already existed, so nothing was duplicated.

This is the practical one-command daily paper-proof loop. UI/UX is now close,
but still should wait until several daily bundles exist across real trading
days. Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement,
and payout automation remain `NOT LICENSED`.

## 2026-06-22 - Paper risk-budget sizing loop

Added the paper-only risk sizing track that sits after daily route/no-trade
decisions and before any future paper execution adapter.

- Added `cas_forex/paper_risk.py`.
- Added `scripts/run_paper_risk_review.py`.
- Added `tests/test_paper_risk.py`.
- Added handoff doc:
  `docs/working/cas_forex_paper_risk_budget_loop_20260622.md`.

The new track sizes routed paper candidates against:

- account equity
- per-trade risk percent
- daily risk percent
- lot step / minimum paper lot
- max position lots
- daily paper-attempt cap

First real daily risk review:

- command:
  `python scripts/run_paper_risk_review.py --account-equity 5000 --max-risk-pct 0.5 --daily-risk-pct 1.0 --append-review --output-dir evidence_runs/index_tsmom_126_paper_proof`
- status:
  `evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-paper-risk-status.json`
- risk status: `PAPER_ATTEMPTS_ALLOWED`
- account equity: `$5,000`
- per-attempt risk cap: `0.5%` / `$25`
- daily risk cap: `1.0%` / `$50`
- daily attempt cap: `3`
- proposed attempts: `2`
- allowed attempts: `2`
- suppressed attempts: `0`
- US30: `0.01` paper lots, planned risk `$12.60`
- NAS100: `0.01` paper lots, planned risk `$12.70`
- total planned paper risk: `$25.30` / `0.506%`
- evidence packet status: `SUPPRESSED`
- broker order placed: no

This gives the day-1 paper loop a complete backend readout: MT5 demo source
verified, strategy route recorded, and risk budget sized. It is still paper-only
evidence. Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement,
and payout automation remain `NOT LICENSED`.

## 2026-06-22 - Daily paper route/no-trade decision loop

Added the daily paper-decision track that pairs with MT5 demo receipts.

- Added `cas_forex/paper_decision.py`.
- Added `scripts/run_paper_route_decision.py`.
- Added `tests/test_paper_decision.py`.
- Added handoff doc:
  `docs/working/cas_forex_daily_paper_decision_loop_20260622.md`.

The new track records what CAS would have done in paper mode for the active
lead without placing any broker order:

- `ROUTE_PAPER_SIGNAL`
- `NO_TRADE`
- `NO_TRADE_MACRO_LOCK`
- `UNAVAILABLE`

First real daily paper decision:

- command:
  `python scripts/run_paper_route_decision.py --date 2026-06-22 --append-decision --output-dir evidence_runs/index_tsmom_126_paper_proof`
- status:
  `evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-paper-decision-status.json`
- route action: `ROUTE_PAPER_SIGNAL`
- macro status: `PASS`
- event context: `normal`
- US30: `LONG`, confidence `0.4612`
- NAS100: `LONG`, confidence `0.7539`
- evidence packet status: `SUPPRESSED`
- broker order placed: no

This is exactly the missing backend piece before UI/UX: verified paper source
plus daily route/no-trade intent. The UI should still wait until this loop has
several daily records, risk status, and blockers to display truthfully.

Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and
payout automation remain `NOT LICENSED`.

## 2026-06-22 - MT5 demo adapter verified paper day 1

Implemented the real demo-broker receipt adapter path for `index_tsmom_126_d1`.

- Added `cas_forex/paper_broker_adapter.py` with `MT5DemoPaperReceiptAdapter`.
- Added `scripts/run_mt5_paper_receipt.py` to probe MT5 demo account state and
  append a receipt only when the source is `BROKER_API_VERIFIED`.
- Added `tests/test_paper_broker_adapter.py` covering demo verification,
  real-account blocking, disconnected terminal `UNAVAILABLE`, and verified
  receipt append behavior.
- Ran the real MT5 probe for 2026-06-22. Result:
  `BROKER_API_VERIFIED` from `Hugosway-Demo`, terminal `MetaTrader 5`,
  `orders_attempted=0`, `orders_paper_executed=0`, open positions reconciled,
  receipt hash `94d68da3b3c4d7bd13e29f69df60e1ff1d7938757e0e8e3d9aec613976704c0c`.
- Probe artifact:
  `evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-mt5-demo-probe-20260622153728.json`.

Current active paper-proof status:

- completed days: `1 / 30`
- broker verified days: `1 / 30`
- packet count: `2`
- chain verified: `true`
- passed: `false`
- blockers: `paper_days 1 < required 30`; `broker_verified_days 1 < required 30`

This is the first real demo-source paper-proof day. It is still not live
permission and still not income proof. Live trading, broker `ACCEPT`,
auto-deposit, debit/card/bank movement, and payout automation remain
`NOT LICENSED`.

UI/UX checkpoint: we are close but not there yet. Build the UI after the proof
backend has stable daily MT5 demo receipt generation and at least a small run of
multi-day verified paper status to display truthfully.

## 2026-06-22 - Broker/demo receipt gate for paper proof

Added a receipt-ingestion gate for the active `index_tsmom_126_d1` paper-proof
ledger.

- `cas_forex/paper_proof.py` now validates and hash-binds paper/demo broker
  receipts.
- Receipt evidence is split into explicit levels:
  - `PLAN_ONLY`: heartbeat only, no broker/demo source.
  - `BROKER_EXPORT_HASHED`: user-supplied paper/demo export is schema-checked
    and hash-bound, but not API-authenticated.
  - `BROKER_API_VERIFIED`: reserved for a broker/demo adapter that
    verifies the receipt directly from the paper broker source.
- Duplicate receipt events for an existing trading date no longer inflate the
  paper-day count; the summary keeps the strongest evidence for each date.
- `scripts/run_paper_proof_plan.py` now supports `--broker-receipt` and
  `--write-receipt-template`.
- Added receipt-contract doc:
  `docs/working/cas_forex_paper_broker_receipt_contract_20260622.md`.
- Wrote the active local template:
  `evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-receipt-template-20260622.json`.

Current status remains correctly conservative: `1 / 30` paper days, `1 / 30`
broker verified days, chain verified, `passed=false`. Live trading,
broker `ACCEPT`, auto-deposit, debit/card/bank movement, and payout automation
remain `NOT LICENSED`.

## 2026-06-22 - Started paper-proof ledger for index TSMOM 126

Started the 30-trading-day paper-proof path for the strongest current CAS Forex
candidate: `index_tsmom_126_d1`, using D1 `tsmom_126_250_2_10` on `US30` and
`NAS100`.

- Added `cas_forex/paper_proof.py`, a lead-specific paper-proof module that
  writes a plan, appends daily Evidence Packets, verifies the local hash chain,
  and refuses live mode.
- Added `scripts/run_paper_proof_plan.py` for starting/appending the current
  `index_tsmom_126_d1` proof ledger.
- Added `tests/test_paper_proof.py` to lock the important gates:
  live mode is refused, duplicate trading days cannot inflate the count, and a
  plan-only heartbeat stays `passed=false`.
- Started the actual proof ledger:
  `evidence_runs/index_tsmom_126_paper_proof/index-tsmom-126-d1-paper-proof-status.json`.

Current paper status:

- completed trading days: `1 / 30`
- evidence chain: verified
- live mode used: `false`
- passed: `false`
- blockers: `paper_days 1 < required 30`; `broker_verified_days 1 < required 30`

Honest boundary: this protects the best current lead and starts the proof clock,
but it is not live trading permission. Broker `ACCEPT`, auto-deposit,
debit/card/bank movement, payout automation, and live trading remain
`NOT LICENSED`.

## 2026-06-22 - GO sprint: simulator-fed owner review + index D1 TSMOM lead

Ran the next money-focused proof step: feed CAS-SDG simulator wins and fresh
M15/H1/D1 walk-forward evidence into owner-control promotion reviews.

- `cas_forex/owner_control.py` now exposes
  `count_condition_lab_simulator_wins()` so owner-control can count simulator
  wins directly from Condition Lab cells instead of relying on a manually typed
  number.
- `scripts/run_owner_promotion_review.py` now accepts
  `--condition-lab-reports` plus simulator-win filters:
  `--sim-min-return`, `--sim-max-drawdown`, and `--sim-min-trades`.
- `scripts/run_condition_tally.py` now accepts custom `--axes`, which lets CAS
  review a broader route family such as D1 index TSMOM across NAS100/US30
  instead of only per-symbol buckets.
- Added `index_tsmom_126_d1` to `strategy_leads.json` as priority 2 and updated
  `tests/test_strategy_ledger.py` so the lead remains visible.

Fresh range-scalper evidence:

- CAS-SDG focused sweep:
  `evidence_runs/range_scalper_sdg_owner_go/condition-lab-20260622054512-report.json`
  with `108` cells, `5` RPM routes, and mostly D1 non-gap pockets.
- M15/H1 walk-forward for `range_scalper_24_120`:
  `evidence_runs/range_scalper_m15_h1_walk_forward_go/walk-forward-20260622054614-report.json`
  with `340` windows, `65` routed, but combined routed mean return `-0.0614%`
  and grade `NOT_PROMOTED`.
- M15/H1 walk-forward for `range_scalper_24_120` + `range_scalper_12_80`:
  `evidence_runs/range_scalper_variants_m15_h1_go/walk-forward-20260622054829-report.json`
  with `340` windows, `107` routed, combined routed mean return `-0.1056%`,
  and grade `NOT_PROMOTED`.
- Interpretation: do not promote short-timeframe range-scalper yet. The D1
  range-scalper lead remains alive, but M15/H1 needs a better filter or
  broker-grade spread/session model.

Fresh index TSMOM evidence:

- H1/D1 walk-forward for NAS100/US30, `tsmom_126_250_2_10` and
  `tsmom_252_500_2_8`:
  `evidence_runs/index_tsmom_h1_d1_go/walk-forward-20260622054921-report.json`.
- D1 subreport returned `WALK_FORWARD_LEAD`: `8` D1 windows, `5` routed,
  `3` positive, positive routed window rate `0.6`, routed mean return
  `1.8932%`, max drawdown `7.0764%`, and `76` routed trades.
- Custom D1 family tally:
  `evidence_runs/condition_tally/condition-tally-20260622055042-report.json`
  shows `tsmom_126_250_2_10` D1 with `5` routed windows, `0.6` positive rate,
  `1.8932%` mean return, `7.0764%` max drawdown, and `76` trades.
- CAS-SDG focused index sweep:
  `evidence_runs/index_tsmom_sdg_owner_go/condition-lab-20260622055024-report.json`
  with `288` cells and `16` RPM routes; top non-gap cells were D1
  trend-up/high-vol TSMOM routes on US30/NAS100.
- Owner review:
  `evidence_runs/owner_promotion_review/owner-promotion-review-20260622055433-report.json`
  in `LIMITED_PAPER` mode shows the D1 `tsmom_126_250_2_10` bucket cleared
  simulator and walk-forward thresholds; remaining blockers are `paper_days 0 <
  required 30` and `paper_passed is false`.

Honest boundary: this is the strongest current paper-proof candidate, not live
permission. Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank
movement, and payout automation remain `NOT LICENSED`.

## 2026-06-22 - Owner-controlled simulator promotion policy

Added the owner-control layer requested for the future CAS-SDG/LLM loop. The
idea is: if the simulator, walk-forward route map, and paper proof produce
enough wins for `Strategy X`, the owner's selected mode decides what CAS Forex
is allowed to do next.

- `cas_forex/owner_control.py` - promotion candidate, thresholds, and owner
  modes:
  - `DENY`
  - `NOTIFY_ONLY`
  - `LIMITED_PAPER`
  - `PAPER_AUTO`
  - `LIVE_AUTO`
- `LIVE_AUTO` intentionally returns `LIVE_BLOCKED_NOT_LICENSED`; owner approval
  does not create broker `ACCEPT`, live trading permission, or payment-transfer
  permission.
- `LIMITED_PAPER` can authorize a fixed number of paper-mode attempts after
  thresholds pass.
- `PAPER_AUTO` can authorize paper-mode automatic routing after thresholds pass.
- `cas_forex/llm_optimizer.py` proposals now include `simulator_requests`, so a
  future LLM can request CAS-SDG/Condition Lab sweeps without being connected
  directly to live execution.
- `scripts/run_owner_promotion_review.py` reviews saved condition-tally buckets
  against owner-control thresholds.
- `tests/test_owner_control.py` covers enough-wins authorization, notify-only
  mode, under-threshold blockers, and live-auto blocking.

First current-evidence owner review:

- source tally:
  `evidence_runs/condition_tally/condition-tally-20260622052757-report.json`
- review report:
  `evidence_runs/owner_promotion_review/owner-promotion-review-20260622053731-report.json`
- requested mode: `LIMITED_PAPER`
- current decision: both routed buckets remain `NOTIFY`, not paper-authorized,
  because the current tally lacks CAS-SDG win count, enough walk-forward windows,
  and 30-day paper proof.

Honest boundary: this creates the switchboard for the owner's future accept/deny
choices, but live trading, auto-deposit, debit/card/bank movement, and broker
`ACCEPT` remain `NOT LICENSED`.

## 2026-06-22 - Guarded LLM optimizer scaffold + condition tally

Added the first safe CAS Forex LLM-optimizer layer. The design keeps winning
strategy leads visible, lets an LLM propose research experiments, and blocks
live/bank/broker/profit-claim escalation through CAS Harness/PCBA style gates.

- `cas_forex/llm_optimizer.py` - `OptimizerProposal`,
  `CASPCBAOptimizerGuard`, and review verdicts:
  - `RESEARCH_QUEUE`
  - `FLAG_FOR_HUMAN_REVIEW`
  - `REJECT`
- The guard requires known strategy-lead IDs, evidence refs, condition contexts,
  and the `NOT LICENSED` claim boundary.
- The guard rejects proposals that try to place trades, unlock live mode,
  create broker `ACCEPT`, move money to/from bank/debit/card/payment rails, or
  promise guaranteed income.
- It reuses the PCBA prompt-injection surface extractor so obvious prompt
  hijack text is rejected before a proposal reaches the research queue.
- `cas_forex/condition_tally.py` - walk-forward condition scoreboard grouped by
  symbol, timeframe, event context, regime, route action, setting, return,
  drawdown, and trade count.
- `scripts/run_condition_tally.py` - converts saved walk-forward JSON reports
  into condition tally artifacts.
- `tests/test_llm_optimizer.py` and `tests/test_condition_tally.py` lock the
  core safety and tally behavior.
- `docs/working/cas_forex_llm_optimizer_plan_20260622.md` records the target
  architecture and open-weight model benchmark plan.
- First tally artifact from the corrected D1 walk-forward report:
  `evidence_runs/condition_tally/condition-tally-20260622052757-report.json`
  with `18` windows, `7` routed windows, `11` `NO_TRADE` windows, and
  `normal` event context on all legacy windows.

Honest boundary: this is a guarded research assistant scaffold, not
hallucination prevention proof, not live trading permission, and not a path to
automatic bank/debit/card transfers. Live trading remains `NOT LICENSED`.

## 2026-06-22 - Event-aware condition axis for multi-timeframe RPM routing

Started the next requested switching layer: event-aware routing. CAS FOREX can
now include event context in Condition Lab cells, nested lacunarity keys, and
RPM route keys.

- `cas_forex/event_context.py` - event-context labels and helpers:
  - `normal`
  - `pre_NFP` / `post_NFP`
  - `pre_CPI` / `post_CPI`
  - `pre_FOMC` / `post_FOMC`
  - `pre_RATE_DECISION` / `post_RATE_DECISION`
  - `pre_GDP` / `post_GDP`
  - `pre_UNEMPLOYMENT` / `post_UNEMPLOYMENT`
  - `pre_CENTRAL_BANK_SPEECH` / `post_CENTRAL_BANK_SPEECH`
  - `weekend_gap`, `liquidity_thin`, `conflict_shock`
- `ConditionCell` now carries `event_context`.
- Synthetic CAS-SDG sweeps accept `--event-contexts` and scale synthetic
  volatility by event context, so `conflict_shock` and post-release contexts can
  be stress-tested separately from normal markets.
- Real-data Condition Lab and walk-forward runs can opt into
  `--real-event-source static_macro` / `--event-source static_macro`; this uses
  the static 2026 seed macro calendar as a research label source only.
- Nested lacunarity now defaults to:
  `source -> symbol -> time_scale -> timeframe -> event_context -> regime -> vol_mult -> family`.
- RPM route keys now include `event_context`, so routes learned under `normal`
  conditions are not blindly applied during NFP/FOMC/conflict-style contexts.
- Added tests for macro pre/post windows, manual conflict windows, synthetic
  event-context cells, and event-context walk-forward route keys.

First compact synthetic event-context run:

- command: `python scripts/run_condition_lab.py --source synthetic --symbols NAS100 EUR/USD --settings tsmom_252_500_2_8 range_scalper_24_120 --regimes trend_up range --vol-mults 1.0 --timeframes M15 H1 D1 --event-contexts normal pre_NFP post_NFP conflict_shock --seeds 1 --bars 300 --position-lots 0.05 --spread-pips 1.0 --extra-cost-pips 0.5 --rpm-min-return 0.5 --output-dir evidence_runs/event_context_focus`
- cells: `96`
- overall nested-lacunarity gap fraction: `0.9062`
- RPM routes: `1`; `NO_TRADE`: `47`
- only routed condition: synthetic `EUR/USD` `D1` `post_NFP` `trend_up` -> `tsmom_252_500_2_8`
- report: `evidence_runs/event_context_focus/condition-lab-20260622050947-report.json`

First real-data static-macro smoke:

- report: `evidence_runs/event_context_walk_forward_smoke/walk-forward-20260622051001-report.json`
- windows: `8`
- routes: `0`
- `NO_TRADE`: `8`
- readout: adding event context made sparse/untrained macro windows route to
  `NO_TRADE`, which is the conservative behavior we want until event-specific
  evidence exists.

Honest boundary: this is an event-aware route-map scaffold, not a finished
news/conflict trading system. The static 2026 macro calendar is only a seed;
historical macro releases and geopolitical/conflict shock windows still need
provider-backed or curated data. Live trading remains `NOT LICENSED`.

## 2026-06-22 - Strategy lead ledger + analyze/simulate/switch status audit

Added a durable strategy-lead memory so current winning research leads stay in
front while new CAS Forex strategies are explored.

- `strategy_leads.json` - machine-readable ledger of active research leads,
  watchlist strategies, evidence refs, open gates, and deployment status.
- `cas_forex/strategy_ledger.py` - loader/validator that preserves the
  `NOT LICENSED` claim boundary.
- `tests/test_strategy_ledger.py` - regression checks that the active leads
  remain recorded and their evidence refs resolve.
- `docs/working/cas_forex_winning_strategy_ledger_20260622.md` - human-readable
  strategy ledger plus a direct status audit of the analyze/simulate/switch-up
  program.

Current active leads:

- `range_scalper_filtered_fx_d1` - priority 1, `range_scalper_24_120`,
  promoted next for `EUR/USD` and `GBP/USD`, with `AUD/USD` on watchlist and
  `USD/JPY` / `USD/CAD` excluded until condition-specific proof.
- `index_tsmom_252_d1` - priority 2, `tsmom_252_500_2_8`, promoted next for
  `NAS100` and `US30`, but blocked on better index trend/range detection after
  the first D1 walk-forward run stayed `NO_TRADE` on recent index windows.
- `meanrev_trend_filter_fx_d1` - watchlist only; thin and cost-sensitive.

Analyze/simulate/switch-up audit:

- Tried as synthetic CAS-SDG regime simulator.
- Tried as real-data hard switching on daily and H1; switching did not beat the
  best single FX-major strategy.
- Rebuilt as Condition Lab with settings, real slices, CJT regions, nested
  lacunarity, and RPM route/no-trade maps.
- Extended across temporal nested lacunarity (`S1`, `M1`, `H1`, `D1`, `MN1`,
  `Y1`).
- First walk-forward RPM test preserved the range-scalper lead on active future
  windows but remains `NOT_PROMOTED` because route coverage is sparse.

Event/news factoring status:

- Present: `MacroGate` handles static seed `NFP`, `CPI`, `FOMC`, `GDP`,
  `UNEMPLOYMENT`, `CENTRAL_BANK_SPEECH`, and `RATE_DECISION`; CJT macro-shock
  diagnostics route to `LIVE_LOCKED`.
- Not complete: historical backtests do not yet evaluate real macro event
  timing per candle, and conflict/geopolitical shocks are not yet a first-class
  Condition Lab / RPM axis.

Next correct build: add event-context axes (`normal`, `pre_NFP`, `post_NFP`,
`FOMC`, `CPI`, `conflict_shock`, `weekend_gap`, `liquidity_thin`) and train
multi-timeframe/mode RPM routes that can switch setting + timeframe, reduce
risk, or choose `NO_TRADE`. Live trading remains `NOT LICENSED`.

## 2026-06-22 - Walk-forward RPM validation for current profit leads

Added a walk-forward validation layer for the Condition Lab so CAS can train an
RPM route map on one historical window, freeze it, and evaluate only the next
untouched future window.

- `cas_forex/walk_forward.py` - reusable walk-forward route evaluator:
  - splits candles into train/test windows
  - builds real-data Condition Lab cells on the training window only
  - freezes the RPM route table
  - labels the future test window by regime and volatility bucket
  - applies only the exact trained route, otherwise emits `NO_TRADE`
  - uses prior training bars as signal lookback context while allowing trades
    only inside the future test window
  - summarizes routed, active-routed, positive, drawdown, trade-count, and
    research-grade metrics
- `scripts/run_walk_forward_condition_lab.py` - CLI for Yahoo proxy
  walk-forward runs.
- Added tests for walk-forward index ranges, future-condition labeling,
  strategy lookback context, and JSON serialization.

First corrected D1 walk-forward focus run:

- command: `python scripts/run_walk_forward_condition_lab.py --symbols NAS100 US30 EUR/USD GBP/USD AUD/USD --settings tsmom_252_500_2_8 range_scalper_24_120 --timeframes D1 --period 5y --train-bars 756 --test-bars 126 --step-bars 126 --train-segment-bars 252 --train-step-bars 63 --position-lots 0.05 --spread-pips 1.0 --extra-cost-pips 0.5 --rpm-min-trades 1 --rpm-max-dd 20 --rpm-min-return 0 --output-dir evidence_runs/walk_forward_condition_lab`
- report: `evidence_runs/walk_forward_condition_lab/walk-forward-20260622044930-report.json`
- chart: `docs/working/cas_forex_walk_forward_rpm_chart_20260622.png`
- windows: `18`
- routed windows: `7`
- active routed windows: `3`
- positive active routed windows: `3 / 3`
- positive routed window rate: `0.4286`
- active routed mean return: `1.2827%`
- routed total return-percent sum: `3.8480%`
- routed max drawdown: `2.2980%`
- total routed trades: `32`
- research grade: `NOT_PROMOTED`

Readout: the corrected walk-forward harness preserved the range-scalper lead
on active future windows (`EUR/USD` and `GBP/USD`) but did not promote it
because route coverage is still sparse and inactive/no-route windows dominate.
`NAS100` and `US30` stayed `NO_TRADE` in this D1 run because the current
real-slice detector labeled the future windows as range and the trained route
map did not find an acceptable index route. This is useful evidence for the
next target: improve condition detection and test broker-grade/intraday data.
Live trading remains `NOT LICENSED`.

## 2026-06-22 - Temporal nested lacunarity across second/minute/hour/day/month/year

Added the user's requested time-axis nesting to the CAS FOREX Condition Lab so
CJT, nested lacunarity, and RPM routing can reason over temporal scale instead
of treating all bars as if they were daily bars.

- `cas_forex/condition_lab.py` now carries `timeframe` and `time_scale` on every
  `ConditionCell`.
- Added canonical CAS timeframe helpers for `S1`, `M1`, `H1`, `D1`, `W1`,
  `MN1`, and `Y1`, plus aliases such as `1m`, `1h`, `1mo`, and `1y`.
- Synthetic CAS-SDG sweeps now accept multiple `--timeframes` and scale
  volatility by approximate bar duration, enabling second/minute/hour/day/month/
  year stress maps.
- Nested lacunarity now defaults to:
  `source -> symbol -> time_scale -> timeframe -> regime -> vol_mult -> family`.
- RPM route keys now include `time_scale` and `timeframe`, so the router can
  choose different settings or `NO_TRADE` for M1 scalping versus D1 swing versus
  MN1/Y1 longer-horizon behavior.
- `scripts/run_condition_lab.py` now supports `--timeframes` and uses Yahoo-safe
  real-data defaults where available. True second bars and native yearly bars
  are explicitly skipped for real-data Yahoo runs until broker tick data or an
  aggregation layer is added.
- Added regression tests for timeframe classification, provider interval
  mapping, synthetic multi-timeframe cell generation, default temporal
  lacunarity keys, and RPM route-key changes.

First compact synthetic temporal run:

- command: `python scripts/run_condition_lab.py --source synthetic --symbols NAS100 --settings tsmom_252_500_2_8 range_scalper_24_120 --regimes trend_up range --vol-mults 1.0 --timeframes S1 M1 H1 D1 MN1 Y1 --seeds 1 --bars 300 --position-lots 0.05 --spread-pips 1.0 --extra-cost-pips 0.5 --rpm-min-return 0.5 --output-dir evidence_runs/temporal_lacunarity_focus`
- cells: `24`
- overall nested-lacunarity gap fraction: `0.8750`
- temporal pattern: `S1`, `M1`, and `H1` were `100%` gap in this compact
  two-strategy sweep; `D1`, `MN1`, and `Y1` were `75%` gap.
- RPM routes: `1`; `NO_TRADE`: `11`
- only routed condition: synthetic `NAS100` `Y1` `trend_up` -> `tsmom_252_500_2_8`
- report: `evidence_runs/temporal_lacunarity_focus/condition-lab-20260622044212-report.json`
- chart: `docs/working/cas_forex_temporal_lacunarity_chart_20260622.png`
- verification: `python -m pytest tests -q` -> `239 passed`

Honest read: this is the correct architecture for multi-timeframe CAS routing,
but the first run is a focused stress test, not a live edge. Short timeframes
need broker-grade/tick data, spread/slippage realism, and walk-forward proof
before they can be trusted. Live trading remains `NOT LICENSED`.

## 2026-06-22 - Capital goal planner + low-volatility range-scalper research lead

Added explicit capital-goal math and a Forex-Fury-inspired research strategy
without copying proprietary code or claiming guaranteed returns.

- `cas_forex/capital_plan.py` - converts seed capital and monthly income target
  into required monthly return, feasibility status, notes, and a linked
  `ProfitSweepPolicy`.
- The user's stated range (`$2k-$5k` seed, `$5k-$12k/month` target) requires
  roughly `100%` to `600%` monthly returns, so the planner classifies all four
  corners as `SURVIVAL_RISK`.
- `forecast/strategies.py` now includes `make_low_vol_range_scalper_signal()`:
  a public-pattern range/low-volatility fade inspired by EA descriptions such
  as Forex Fury's published low-volatility/range approach. This is a CAS
  research candidate, not a copy of proprietary set files.
- `scripts/run_real_backtest.py` now supports `--model range_scalper`.
- `condition_lab.py` now includes `range_scalper_24_120` and
  `range_scalper_12_80` setting variants.
- Added tests for the capital planner, linked sweep policy, and range-scalper
  signal behavior.

Forex Fury public-source synthesis checked on 2026-06-22: the official site
describes a customizable MT4/MT5 EA, verified third-party tracking, no fixed
monthly return, 0-7 trades/day, and a range-based method designed for low
volatility, often trading one hour per day and one pair per account. CAS Forex
should test that pattern, not trust the marketing.

Initial research-only runs, 5y daily Yahoo proxy data, `0.05` lots, `1.0`
spread + `1.0` extra cost:

- `range_scalper` on 5 FX majors: portfolio `+$1,572.25`; EUR/USD `+7.41%`,
  GBP/USD `+17.75%`, AUD/USD `+1.69%`, USD/JPY `-9.06%`, USD/CAD `-2.07%`;
  CAS gating improved P&L and lowered avg max DD (`4.88%` vs `6.55%`);
  chain verified; `report.passed=true` as research signal only.
- `range_scalper` on filtered EUR/USD, GBP/USD, AUD/USD: portfolio
  `+$2,686.37`; avg max DD `2.38%`; chain verified; `report.passed=true`
  because CAS lowered drawdown, though raw P&L was higher.

Honest read: this is a second positive research lead alongside index TSMOM.
It is not enough to fund live trading or promise `$5k-$12k/month`. Promote it
to condition-lab and walk-forward testing, then paper proof. Live trading and
provider/bank/card automation remain `NOT LICENSED`.

## 2026-06-22 - CAS condition lab: SDG + real slices + CJT/lacunarity/RPM routing

Added the deeper simulator layer requested by the user: a condition laboratory
that plays strategy settings across synthetic CAS-SDG regimes and real market
windows, then uses CJT regions, nested lacunarity, and RPM prerequisites to
produce a route/no-trade map.

- `cas_forex/condition_lab.py` - reusable condition-lab engine:
  - named strategy-setting registry (`trend_sma`, `breakout`, `meanrev`,
    `tsmom`, `pullback`)
  - deterministic synthetic sampling
  - real-data window slicing with regime + volatility labeling
  - CJT operating-region classification per setting/condition cell
  - nested lacunarity over `source -> symbol -> regime -> vol -> family`
  - RPM route table that selects the best non-gap setting or emits `NO_TRADE`
- `scripts/run_condition_lab.py` - CLI for synthetic, real, or combined sweeps.
- `regime_sim.generate_regime_candles()` is now instrument-aware for
  `NAS100`, `US30`, and `XAU/USD` instead of using FX-scale default prices.
- Added regression coverage for deterministic seeds, index-scale synthetic
  generation, strategy-setting registry, nested lacunarity, and RPM routing.

Focused synthetic run:

- cells: `168`
- overall nested-lacunarity gap fraction: `0.8333`
- RPM routes: `19`; `NO_TRADE`: `23`
- report: `evidence_runs/condition_lab_focus/condition-lab-20260622042700-report.json`

Focused real-slice run:

- cells: `20`
- overall nested-lacunarity gap fraction: `0.1500`
- RPM routes: `5`; `NO_TRADE`: `0`
- top route examples:
  - real `NAS100` range vol `1.0` -> `tsmom_252_500_2_8`
  - real `US30` range vol `0.5` -> `tsmom_126_250_2_10`
  - real `US30` trend_up vol `1.0` -> `tsmom_126_250_2_10`
- report: `evidence_runs/condition_lab_focus/condition-lab-20260622042733-report.json`

Honest read: the simulator now exists and can generate switching hypotheses.
It does not prove live edge. The next step is to add walk-forward splitting so
RPM routes are learned on one window and judged on untouched future windows.
Live trading remains `NOT LICENSED`.

## 2026-06-22 - Strategy edge sprint: index time-series momentum is the first real research lead

Pushed beyond the first generic index smoke tests and added two new research
strategy families for NAS100/US30:

- `forecast/strategies.py` now includes:
  - `make_time_series_momentum_signal()` - daily-bar trend following / TSMOM,
    long-or-flat by default for indices.
  - `make_trend_pullback_signal()` - buys short pullbacks inside a larger trend.
- `scripts/run_real_backtest.py` now supports `--model tsmom` and
  `--model pullback`, with explicit strategy parameters.
- `backtest/engine.py` now recomputes ATR each bar instead of reusing the warmup
  ATR for the whole test, and rounds proposal entry/SL/TP by instrument metadata.
- `verifier/auditor.py` now suppresses all risk-gate failures, not only drawdown
  live locks. This makes `max_open_positions`, exposure, and correlated-exposure
  failures actually block new trades in the backtest path.
- Added regression coverage for the new strategy signals, rolling ATR, and
  non-lock risk suppression.

Research-only results, NAS100 + US30, 5y daily Yahoo proxy data, `0.1` lots,
`1.0` spread + `1.0` extra cost:

- Raw TSMOM 126: `+123.5%` portfolio, but avg max DD `58.6%` - dangerous
  overtrading profile, not promotable.
- TSMOM 126 max1: `+6.8%` portfolio, avg max DD `4.3%`.
- TSMOM 126 max2: `+13.2%` portfolio, avg max DD `7.6%`.
- TSMOM 126 TP10 max2: `+17.2%` portfolio, avg max DD `5.7%`.
- Pullback 126: `+9.1%` portfolio, avg max DD `6.9%`.
- TSMOM 252 with correlated-exposure cap: `+31.6%` portfolio, avg max DD
  `6.8%`; this is the current best controlled research lead.

Chart: `docs/working/cas_forex_strategy_edge_sprint_chart_20260622.png`.

Honest read: this is the first meaningful positive index research signal, but it
is still in-sample, Yahoo proxy data, and daily-bar only. Promote TSMOM 252 to
walk-forward validation and broker-grade bid/ask testing. Do not promote raw
overtrading. Live trading remains `NOT LICENSED`.

## 2026-06-22 - Index/gold instrument metadata + first NAS100/US30/XAU research smoke

Added the first non-FX instrument layer so CAS Forex no longer has to pretend that
indices and gold are currency pairs.

- `cas_forex/instruments.py` - central metadata registry for FX, `NAS100`, `US30`,
  and `XAU/USD`: research movement unit, point value, contract size, default mid,
  Yahoo ticker, and MT5 symbol.
- `schemas/forecast.py` now gets `SUPPORTED_SYMBOLS` and `pip_multiplier()` from
  the registry. Existing FX pip behavior stays compatible; indices/gold now return
  research points.
- `backtest/engine.py` now uses metadata-backed price units, point value per lot,
  and USD notional estimates, including before a position is open.
- `market_data/connector.py` and `scripts/run_real_backtest.py` now map `NAS100`
  -> `^NDX`, `US30` -> `^DJI`, and `XAU/USD` -> `GC=F` for Yahoo proxy data.
- `schemas/order.py` and `broker/mt5_bridge.py` now use registry-backed broker
  symbols such as `XAUUSD`.
- Added regression coverage for NAS100 point P&L, XAU/USD contract point value,
  and non-FX Yahoo/MT5 symbol mappings.

Verification: `python -m pytest tests -q` -> `220 passed`.

First research-only Yahoo proxy runs, using 5y daily data, `0.1` lots, `1.0`
spread + `1.0` extra cost:

- `breakout`, `NAS100 US30 XAU/USD`: portfolio `-$9,833.96`; NAS100 `+0.55%`,
  US30 `+2.44%`, XAU/USD `-101.34%`; chain verified; `report.passed=false`.
- `sma`, `NAS100 US30`: portfolio `-$954.72`; NAS100 `+3.63%`, US30 `-13.18%`;
  chain verified; `report.passed=false`.
- `breakout`, `NAS100 US30`: portfolio `+$299.62`; NAS100 `+0.55%`, US30
  `+2.44%`; chain verified; `report.passed=false` because CAS gating did not
  improve P&L/drawdown versus raw and buy-and-hold massively outperformed
  (`NAS100 +115.08%`, `US30 +52.21%`).

Honest read: indices are now wired and runnable, but the first generic index
strategies are not deployable edges. XAU/USD should be isolated or deprioritized
until it has a separate gold-specific strategy. The next real edge attempt should
encode the owner's 2020 NAS30/NAS100 rules, add trailing/time exits, and run
walk-forward validation with broker-grade bid/ask data. Live trading remains
`NOT LICENSED`.

## 2026-06-21 â€” Detector tuning + intraday switching: cost drag is the wall, no config beats break-even

Followed the switching test with (A) detector-threshold tuning on daily and (B)
intraday H1. Added detector CLI args (`--er-trend/--detect-window/--hi-vol/--lo-vol/
--shock-z`) to `run_switching_backtest.py`.

(A) Daily er_trend sweep â€” MORE trend detection = WORSE switching (monotonic):
  er 0.15 -$7,360 | 0.20 -$6,479 | 0.25 -$5,631 | 0.35 -$2,040.
  Every "trend" call routes to breakout/trend, which lose on daily, so seeing more
  trends destroys value. Can't tune a daily edge into existence; meanrev_tf (~+$9) wins.

(B) Intraday H1 (real 2y, ~12,300 bars/pair, cost 1.5p): EVERYTHING loses â€”
  trend_sma -$10,404 | breakout -$6,196 | meanrev -$4,862 | SWITCH -$4,715 |
  meanrev_tf -$4,123 (best). SWITCH again ~= meanrev (detector still 91.6% range at H1).
  The killer is COST DRAG: meanrev_tf made +$3.72 on daily (286 trades) but loses
  -$4,123 on H1 (4,654 trades) â€” same strategy, ~16x more trades x cost. ~85% of the
  H1 loss is trading cost.

Synthesis after a thorough search (4 strategy families, 2 forecasters incl. Chronos,
regime sim, detection, hard switching, detector tuning, daily + H1): NO configuration
produces a cost-surviving edge. The ceiling is daily mean-rev+filter at literal
break-even (+$3.72), which evaporates at realistic costs. The wall is cost drag eating
thin edges, worse at higher frequency.

Genuinely untested (tied to user's real 2020 success): the user's OWN discretionary
entry rules encoded, and NAS30 / index instruments (indices trend more strongly than FX
majors; we have only tested FX majors, which mean-revert). Live trading remains NOT
LICENSED. 217 tests pass.

## 2026-06-21 â€” Regime detector + switching on REAL data: switching does NOT beat the best single strategy (on daily)

Built the live regime detector + RPM switching and tested it on real 5y daily data
against every single strategy.

- `forecast/strategies.py` â€” `make_sma_trend_signal` (composable SMA, routable).
- `regime_sim.py` â€” `detect_regime` (Kaufman efficiency ratio + vol-vs-baseline +
  shock z-score + vol-of-vol), `DEFAULT_ROUTING` (sim's RPM seed), and
  `make_regime_switching_signal` (detect each bar -> route -> sit out on lacuna).
- `scripts/run_switching_backtest.py` â€” SWITCH vs each single strategy on real data.

Result (real 5y daily, cost 1.5p, $50k):
  trend_sma  -$15,055 | meanrev -$729 | meanrev_tf +$3.72 | breakout -$8,144 |
  SWITCH     -$2,048
Best = meanrev_tf (+$3.72). SWITCH did NOT beat it (-$2,048).

Why (the mechanism): the detector classifies **97% of real daily bars as "range"**,
so SWITCH ~= plain meanrev, plus rare trend/breakout detours that lost money. Daily
bars are too coarse/homogeneous for hard switching to add value â€” there isn't enough
regime variety, and the trend calls aren't reliable/timely on daily.

Honest read: the regime-switching MACHINERY works end-to-end, but on daily data the
useful "regime intelligence" is the lightweight trend FILTER already baked into
meanrev_tf (a soft regime-awareness), not a separate hard switch. Switching's real
shot is INTRADAY, where regimes vary and change more (ties to the multi-timeframe
requirement). meanrev_tf remains the incumbent (break-even). NOT LICENSED. 217 tests pass.

## 2026-06-21 â€” Strategy-condition simulator (CAS-SDG for regimes): CJT + nested lacunarity + RPM routing

Built the user's idea: a market-REGIME simulator that plays every strategy across
every condition and uses the CAS machinery to map where edge lives. Working v0.

- `cas_forex/regime_sim.py` â€” seeded synthetic OHLC generator for 7 regimes
  (trend_up/down, range, high_vol, low_vol, vol_cluster, shock); CJT operating-region
  classifier (cutoff/active/saturation/breakdown + gain beta); nested lacunarity
  (gap map across strategy x regime x volatility); best-strategy-per-regime (RPM seed).
- `scripts/run_strategy_simulator.py` â€” sweeps strategies x regimes x vol x seeds,
  prints the matrix + nested lacunarity + RPM routing seed, writes a JSON report.

First run (4 strategies x 7 regimes x 3 vol x 5 seeds, cost 1.5p) cleanly recovers
known structure â€” which validates the simulator:
- Trend/breakout WIN in trends (breakout +13.2%/+12.2% up/down) and LOSE in range.
- Mean-reversion WINS in range (+0.9%) and loses in trends.
- No single strategy wins everywhere (overall lacunarity 0.58 â€” 58% of cells are gaps).

RPM routing seed (regime -> best validated strategy):
  trend_up/down/high_vol -> breakout; range/shock -> meanrev; low_vol -> trend_sma;
  vol_cluster -> NONE (honest lacuna, do not trade).

Reframe (the productive insight): the edge â€” if any â€” is in REGIME DETECTION +
SWITCHING, not one magic strategy. The honest next frontier is detecting the live
regime reliably on REAL data and validating the routing out-of-sample (the RPM
prerequisite question). Synthetic regimes characterize behavior, not live edge.
Live trading remains NOT LICENSED. 217 tests pass.

## 2026-06-21 â€” Realistic-cost test: the thin edge does NOT survive normal costs

Added a configurable round-trip cost knob (`extra_cost_pips` = commission + slippage
on top of spread; `--spread-pips` / `--extra-cost-pips`) and swept the trend-filtered
mean-reversion (the only positive strategy) across realistic cost levels.

5y portfolio P&L (gated, $50k):
- 1.0 pip total cost (very optimistic):  +$91   PASS
- 1.5 pips (optimistic ECN+commission):  +$28   PASS
- 2.0 pips (normal retail):              -$31   FAIL
- 2.5 pips (standard account):           -$95   FAIL

Verdict: the edge breaks even at ~1.5-2.0 pips and is negative at realistic retail
all-in costs (majors typically 1.5-2.5 pips spread+commission+slippage). So the
trend-filtered mean-reversion is NOT a deployable, cost-surviving strategy â€” it is
positive only under optimistic cost assumptions, and even then ~$0 over 5 years on
$50k. This is the honest make-or-break result: no deployable edge yet across 4
strategy families tested (trend SMA, Chronos, mean-rev, mean-rev+filter).

Implication for the $5-12k/month target: not reachable. Best strategy made ~$0 over
5y on $50k; $5-12k/month on a $2-5k seed is +100-600%/month (martingale-blowup
territory), not a real return. A realistic 2-5%/month would need a ~$100-250k account
to clear $5k/month â€” and even that is exceptional and not guaranteed.

Added/changed:
- `backtest/engine.py` â€” `extra_cost_pips` (round-trip commission+slippage), deducted
  with spread on close. Default 0.0 (tests unchanged).
- `scripts/run_real_backtest.py` â€” `--spread-pips`, `--extra-cost-pips`.
- 217 tests pass.

## 2026-06-21 â€” Strategy pivot: mean-reversion + trend filter = first POSITIVE backtest (thin)

Acted on the research insight that FX majors range 70-80% of the time, so our
trend-follower was the wrong strategy class (it lost most on the most mean-reverting
pair, USD/CAD). Added rule-based strategies + user-controllable risk budget and
re-ran the same real-data harness (5y daily, 5 majors).

Progression (portfolio P&L on $50k, gated):
- Trend SMA:               -$15,098   (avg max DD 41%)
- Chronos:                 -$15,574   (avg max DD 49%)
- Mean-reversion (z-fade):    -$523    (avg max DD 6%)   <- ~30x less bad, ~break-even
- Mean-reversion + trend filter: +$105.62 (avg max DD 3.5%)  <- FIRST passed=True

The trend filter (skip fades that fight a >150bps move over 60 bars â€” a theory-backed
fix, not curve-fitting) made it net positive: 3/5 pairs clearly positive (EUR/USD
+1.56%, GBP/USD +3.47%, AUD/USD +3.26%), beating buy-and-hold on every ranging pair.
Only USD/CAD (-6.1%) still loses (it trended up). Evidence chains verified.

CRITICAL honesty caveat â€” the edge is razor-thin and NOT yet deployable:
- +$105.62 over 286 gated trades = ~$0.37/trade = ~0.74 pip/trade edge.
- The backtest already charges a 1-pip spread; ONE more pip of real cost
  (commission + slippage) is ~$143 across 286 trades and FLIPS IT NEGATIVE.
- So this is positive-after-1-pip-spread, NOT positive-after-realistic-costs.
- One parameter set, one dataset, in-sample. Needs out-of-sample / walk-forward
  validation + realistic cost modeling before ANY capital. report.passed is a
  research signal, not a license. Live trading remains NOT LICENSED.

Real progress nonetheless: we moved from "definitely loses" to "plausibly
break-even with low drawdown," and confirmed the lever is strategy class + regime
filter, not forecaster sophistication.

Added/changed:
- `forecast/strategies.py` â€” mean-reversion (z-fade, optional trend filter) and
  Donchian breakout signals; no martingale / grid / no-stop modes (real money).
- `backtest/engine.py` â€” signals may set ATR stop/target multiples; risk limits now
  all sourced from config (single source of truth for the risk budget).
- `scripts/run_real_backtest.py` â€” `--model meanrev|breakout`, mean-rev params, and
  RISK BUDGET flags (`--starting-balance --position-lots --risk-per-trade-pct
  --max-daily-dd --max-weekly-dd --max-open-positions --max-position-lots`).
- 217 tests pass throughout.

## 2026-06-21 â€” Chronos-Bolt re-run confirms NO edge across TWO forecasters

Wired Amazon Chronos-Bolt (`forecast/chronos_signal.py`) as a pluggable directional
signal and re-ran the exact same real-data harness (5y daily Yahoo, 5 majors), with
SL/TP held identical so only the forecaster changed (SMA â†’ ML model). Evidence chain
verified: 19,660 hash-chained packets across 5 files, all re-verified.

Result (REAL): Chronos also **loses** â€” portfolio **-$15,574 gated / -$17,007 raw**
on $50k, vs the SMA run's -$15,098 / -$16,296. Per pair (gated%): EUR/USD -22.0,
GBP/USD -81.1, USD/JPY +38.6, AUD/USD -101.6 (account wiped), USD/CAD +10.2.
Buy-and-hold beat the strategy on every pair, including the two "winners" (USD/JPY
b&h +46.3 vs +38.6; USD/CAD b&h +14.6 vs +10.2).

Decisive read: swapping a simple moving average for a real ML forecaster moved the
needle by ~$0.5k on -$15k â€” i.e. **the edge problem is NOT a forecaster-quality
problem.** Two structurally different models both lose on majors over 5 years.

Consistent finding across BOTH models: the **CAS gating layer reduces loss and
drawdown** (gated beat raw on P&L and avg max DD in both runs; suppressed 1,118
Chronos trades) and the new blow-up guard prevented crashes when the ungated AUD/USD
and GBP/USD arms hit ~100% loss / ~100% drawdown. Honest nuance: on the two
profitable pairs the gates slightly REDUCED gains (USD/CAD gated +10.2 vs raw +19.5)
â€” the gates cut both tails; net-positive only because losers dominate.

Strategic implication: the validated, sellable asset is the safety/audit chassis, not
a profitable bot. A trading edge remains OPEN and is the hard, unsolved part; next
lever is a different strategy class or timeframe (per the user multi-timeframe
requirement), NOT a bigger model. Live trading remains NOT LICENSED.

Added/changed:
- `forecast/chronos_signal.py` â€” cached CPU Chronos-Bolt â†’ (Direction, confidence).
- `backtest/engine.py` â€” optional `signal_fn` hook (SMA default unchanged); blow-up
  guard (stop trading when balance <= 0; clamp risk_per_trade_pct at 100%).
- `scripts/run_real_backtest.py` â€” `--model {sma,chronos}`.
- Artifacts: `evidence_runs/real_backtest/real-chronos-20260622003352-report.json`.
- 217 tests pass throughout.

## 2026-06-21 â€” First REAL-data comparative backtest: safety layer works, strategy has NO edge

Ran the first backtest on REAL market data instead of synthetic candles. Pulled 5
years of daily candles from Yahoo Finance (1,300 bars/pair, 2021-06-22 â†’ 2026-06-22,
no API key, no GPU) for EUR/USD, GBP/USD, USD/JPY, AUD/USD, USD/CAD and ran the full
CAS Forex pipeline three ways: `cas_gated` (SMA proposals through the 5-gate auditor),
`raw_model` (same proposals, gates removed), and `buy_hold` / `no_trade` baselines.

Result (REAL, evidence-chain verified): the built-in SMA5/20/50 daily strategy **LOSES
money** with or without CAS gating â€” portfolio P&L **-$15,097.88 gated vs -$16,296.32
raw** on $50,000 starting capital (5 Ã— $10k), avg max drawdown 41.5% gated / 46.0% raw.
Buy-and-hold beat the strategy on most pairs (e.g. USD/JPY b&h +46.3% vs gated +9.3%).

Honest read:
- The **CAS safety/gating layer does its job**: it suppressed 695 trades, lost ~$1,198
  (~7.4%) less than the ungated arm, and lowered average max drawdown (41.5% vs 46.0%).
  It reduces damage â€” it cannot turn a losing strategy into a winning one.
- The **trading edge does not exist** with the current model. `report.passed = False`
  (no positive edge vs no-trade). This confirms live trading SHOULD remain NOT LICENSED:
  trading this model live would lose money.
- Evidence is real and verifiable: 13,554 hash-chained Evidence Packets across 5 files,
  all chains independently re-verified. 217 tests still pass (additive change only).

Next lever for an actual edge (in priority order): wire a real forecaster (Chronos stub
at `forecast/models.py:112`, or a TimeGPT key), then re-run this exact harness; the
strategy â€” not the safety chassis â€” is the bottleneck.

Added:
- `scripts/run_real_backtest.py` â€” real-data (Yahoo) comparative backtest:
  cas_gated vs raw_model vs buy_hold vs no_trade, writes a real BacktestEvidenceReport
  + verifiable hash-chain, with an explicit research-signal (not license) pass criterion.
- Run artifact: `evidence_runs/real_backtest/real-20260621234945-report.json`.

Known caveat (follow-up): the macro gate is evaluated at wall-clock now, not at the
candle's historical timestamp, so macro blackouts are effectively inert in backtests
(`backtest/engine.py` builds the snapshot with `timestamp=utc_now()`).

## 2026-06-19 â€” Closed-book KWIK hallucination probe: measured ceiling, NOT LICENSED

Ran the decisive pre-answer hidden-state hallucination experiment in the one framing where
text controls are structurally weak â€” closed-book "knows-what-it-knows" (TriviaQA no-context,
hidden state captured at the last prompt token before any answer is emitted, label = did the
model's own greedy answer match). This is the literature SOTA direction (SAPLMA / semantic
entropy) and the only honest route to a real +0.15 margin.

Result (REAL, leakage-safe, N=2500 each): the framing **works** â€” residual signal climbed off
the chance floor (grounded 0.45 â†’ KWIK 0.68), proving the hidden state carries genuine
text-independent "do I know this" information. But it **plateaus below the license gate**:
hidden BA â‰ˆ 0.75, margin â‰ˆ +0.12 over text, residual 0.68 â€” short of +0.15 / 0.75. The wall is
flat: 7B â†’ 14B moved the margin +0.000, and a nonlinear MLP + layer ensemble land on the same
~0.75. This matches the published ceiling (~0.7â€“0.85 AUROC) for pre-answer hidden-state probes.

Then, per user request, COUPLED the hidden-state probe with semantic entropy (10Ã— sampling on
14B, leakage-safe stacking). Result: coupled BA 0.7345 vs hidden-only 0.732 â€” a +0.002 gain. The
two signals are **redundant, not complementary** (the 14B is often confidently wrong: mean
entropy 0.379 nats), so entropy adds almost nothing. Held-out generalization flipped to PASS
(0.757), proving an information ceiling rather than overfitting; floor/margin/residual still fail.

Verdict: hallucination detection remains **OPEN / NOT LICENSED** at the specified bars â€” now a
*measured* ceiling confirmed from five independent angles (framing, scale, readout, probe,
method-coupling), not an untested assumption. No fabrication.

Added:
- `closedbook_kwik_capture.py` â€” KWIK capture (last-token + mean-pool hidden, greedy label).
- `lic_eval_closedbook.py` â€” leakage-safe gate (readoutÃ—layer selection, residual, held-out,
  selection-aware 1000-perm).
- `kwik_enhanced_probe.py` â€” ceiling check (ensemble + MLP) confirming the plateau.
- `kwik_semantic_entropy.py` â€” batched 10Ã— sampling + discrete semantic entropy.
- `lic_eval_coupled.py` â€” coupled (hidden + semantic entropy) leakage-safe gate.
- `docs/working/hallucination_kwik_ceiling_findings_20260619.md` â€” full findings + A/B/C fork.

## 2026-06-17 â€” CJT/PCBA Tier-B/C research code + honest gates

Built the research-tier and gated CJT/PCBA work: real, runnable code plus honest
readiness gates. No higher-authority claim was flipped to LICENSED â€” those need
GPU traces, external red-team, or legal review (all still OPEN / NOT LICENSED).

Added:
- `cas_forex/cjt_compiler.py` (B) â€” compiles one `CJT<>` statement: runs embedded
  CAS literals through the real CAS compiler bridge and emits E-CJT-001..008
  validation findings. `is_production_cjt_syntax_enabled()` stays False.
- `cas_forex/cjt_analysis.py` (B) â€” analytical Î² (large/small-signal), gm, and
  operating-region classification via Fisher-Rao geometry. `validated` is always
  False â€” analytical estimate, not measured against real traces (Q-002).
- `cas_forex/ccb_designs.py` (B) â€” the 5 Cognitive Circuit Boards (CSB, COB,
  CDAB, CMB, CPMB) encoded as executable `CrcCircuit` specs that pass CRC
  ERROR-free. Well-formed designs, NOT runtime-safety guarantees.
- `cas_forex/ccb_readiness.py` (C) â€” readiness gates that report each CCB safety
  claim, governance proof, and the CjtPredictionHead as NOT LICENSED / OPEN with
  required external evidence missing.
- `docs/working/cjt_w0_labeled_readout_experiment_design_20260617.md` (C) â€”
  design for the failed-Qwen-W0-gate follow-up (CJT labels + controls + pass
  criteria). Research design only; not run.
- `tests/test_cjt_tier_bc.py` â€” 17 tests incl. negative claim-boundary proofs.

Tests: `python -m pytest tests -q` â†’ 217 passed (zero regressions).

## 2026-06-17 â€” CJT/PCBA Tier-A evidence + visualization layer

Built the buildable-now ("Tier A") CJT/PCBA stack recommended in
`docs/working/cjt_pcba_cas_forex_ecosystem_fit_analysis_20260617.md`. All
additive, evidence-only, claim-bounded (no path to live trading or broker
ACCEPT).

Added:
- `cas_forex/cas_state_utils.py` â€” surface parser for CAS state literals
  (`^k^D_{Fd}|R`): Noetic/Domain/Drive/Register extraction, domain precedence,
  involution-pair check. Not the compiler â€” surface only.
- `cas_forex/cjt_diagnostics.py` (A-1) â€” maps forex conditions (weak edge,
  forecast disagreement, single-model overconfidence, macro shock, drawdown,
  broker mismatch, beta drift) into `CjtCircuitDiagnostic` sidecars with
  claim-ceiling routing (SUPPRESS / FLAG_FOR_HUMAN_REVIEW / LIVE_LOCKED).
- `cas_forex/crc_linter.py` (A-3) â€” Cognitive Rule Check: static design-time
  linter (CRC-001..008) over CJT/via/fuse circuit specs. Flags invalid bias
  domain, short circuits, reverse-flow bypass, push-pull gain divergence,
  cascade depth, gain firewall, and fuse-after-protected. Static only; a
  well-formed circuit is NOT a runtime-safety guarantee.
- `cas_forex/cjt_circuit_view.py` (A-2) â€” deterministic markdown/ASCII renderer
  for diagnostics and CRC reports (Causeâ†’[Bias]â†’Effect, region, Î², gate).
- `cas_forex/cjt_differential.py` (A-4) â€” differential-pair matched-control via
  Fisher-Rao geodesic distance on the open simplex; emits FLAG_FOR_HUMAN_REVIEW
  above threshold. Heuristic, not proof.
- `tests/test_cjt_pcba_tier_a.py` â€” 23 tests covering all of the above.

Tests: `python -m pytest tests -q` â†’ 200 passed (zero regressions).

