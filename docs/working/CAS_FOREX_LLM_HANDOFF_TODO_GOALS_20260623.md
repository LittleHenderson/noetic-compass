# CAS Forex LLM Handoff, TODO, And Goal List

Date: 2026-06-24 (updated, original: 2026-06-23)
Workspace: `C:\Users\wakil\OneDrive\Desktop\tksCAS`
CAS Forex root: `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex`

## Copy-Paste Brief For The Next LLM

You are taking over CAS Forex. Read this file first, then read:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\cas_harness_production_todo.md
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\CHANGELOG.md
C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\CAS_FOREX_THIRD_PARTY_AUDIT_PACKET_20260622.md
C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\CAS_FOREX_HANDOFF_20260621.md
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\strategy_leads.json
```

CAS Forex is intended to become a real owner-controlled live-money trading and income system for forex, indices, and gold. The current research/backtest/paper/demo layers are not the final purpose; they are the proving, evidence, UI, and safety buildout path needed to get to owner-authorized live execution without fake claims, hidden math gaps, or broken broker/payment plumbing.

Current stage: live-money product buildout in paper/demo proof mode. The destination is real live-money owner trading. Live trading is not active yet because the evidence, broker, account, payment, and runtime requirements have not all been completed.

Current hard truth:

- Trading edge status: `OPEN`.
- Live trading: `NOT LICENSED`.
- Broker `ACCEPT`: `NOT LICENSED`.
- Auto-deposit: `NOT LICENSED`.
- Debit/card/bank movement: `NOT LICENSED`.
- Payout automation: `NOT LICENSED`.
- Current owner-control mode in the cockpit: `AI_FULL_AUTO_PAPER`.
- The read-only UI/API cockpit is allowed to exist now.
- Paper/demo evidence is not a live-income claim.
- The removed hard scope switch must not be reintroduced. Do not add back `personal_utilization_only`, `PERSONAL_ONLY`, `PERSONAL_UTILIZATION_ONLY`, `account_scope`, or `disallowed_scopes` as active owner-control fields.

Latest implementation update (2026-06-24 phase 2):

- MT5 process guard (subprocess watchdog) implemented and tested.
  - `cas_forex/mt5_process_guard.py` wraps MT5 calls in a timeout-guarded
    subprocess so a hung MT5 terminal cannot block the agent loop.
  - Five worker operations: `execute_demo_order`, `get_deal_history`,
    `get_account_snapshot`, `get_open_positions`, `close_position`.
  - Integrated into `agent_state.py` via `mt5_use_process_guard` and
    `mt5_guard_timeout_seconds` params. Guard activates only when all three
    conditions are met: flag on + MT5 path set + execution flags true.
    Falls through to existing direct MT5 path otherwise.
  - CLI flags added to `run_agent_workflow_queue.py`:
    `--mt5-use-process-guard`, `--mt5-guard-timeout-seconds`.
  - 14 new tests in `test_mt5_process_guard.py`.
- CAS Forex Bot implemented (`cas_forex/cas_forex_bot.py`).
  - Structured conversational agent: 31 capabilities across 7 action groups.
  - Menu-driven: groups + commands, max 6 options per level.
  - Confirmation gates for MT5 demo orders. Shows underlying CLI commands.
  - Entry point: `py -3.12 scripts/run_cas_forex_bot.py`.
- Verification:
  - Full suite: `494 passed` (480 existing + 14 new).
  - Bot smoke: 31 capabilities, 7 groups, all lookups + renders verified.

Next operator action: rerun scheduled MT5 demo cycle against real Hugosway
terminal with guard enabled:
```
py -3.12 scripts/run_agent_workflow_queue.py --terminal-lane PAPER_MT5_DEMO --mt5-path "C:\Program Files\Hugosway\Hugosway PRO5 Terminal\terminal64.exe" --execute-mt5-demo-order --confirm-mt5-demo-order --mt5-use-process-guard --summary-only
```

Previous implementation update:

- Scheduled/autowake agent MT5 demo loop is now implemented and
  regression-verified, but not yet real-terminal verified through the
  scheduled path.
- Implemented:
  - `cas_forex/agent_state.py`
    - explicit terminal lanes: `PAPER_MT4_MAILBOX` and `PAPER_MT5_DEMO`
    - scheduled approved `RouteIntent.order_request` can feed MT5 demo
      execution instead of only MT4 mailbox commands
    - MT5 execution receipts carry `cycle_id`, `intent_id`, `command_id`,
      `broker_ticket`, hashes, execution status, close status, and account
      snapshot facts
    - MT5 deal-history ingest runs by ticket and refreshes memory
    - successful MT5 closed-history memory join appends `NEXT_CYCLE_ALLOWED`
    - MT5 cycles use `agent-events-mt5-demo.jsonl` so stale MT4 mailbox rows
      do not jam the MT5 lane
  - `cas_forex/mt5_paper_execution_verifier.py`
    - accepts an existing `BrokerOrderRequest` from an agent route intent
    - remaps market-order SL/TP geometry onto the current MT5 tick
  - `cas_forex/agent_message_bus.py`
    - emits real MT5 receipt events instead of only `RECEIPT_PENDING`
  - `cas_forex/session_autowake_runner.py`
    - autowake can pass MT5 lane and demo execution flags into due cycles
  - `scripts/run_agent_workflow_queue.py`
    - added `--terminal-lane PAPER_MT5_DEMO`, `--mt5-path`,
      `--execute-mt5-demo-order`, `--confirm-mt5-demo-order`,
      `--no-mt5-deal-history`, and `--mt5-future-minutes`
  - `scripts/run_session_autowake_runner.py`
    - added the same MT5 lane controls
  - `api/data.py`
    - dashboard message-bus summary follows the latest cycle's event log
  - Optimizer UI/types/fixtures show cycle-level MT5 loop status, broker
    ticket, deal-history status, memory joins, closed positions, and closed P/L
- Regression proof:
  - `tests/test_agent_workflow_cycle.py` proves a fake MT5 terminal executes
    and closes a scheduled route, returns two deal-history rows, joins memory
    by `broker_ticket`, reports net P/L `-0.13`, and emits
    `NEXT_CYCLE_ALLOWED`.
- Verification:
  - `py -3.12 -m pytest tests/test_agent_workflow_cycle.py tests/test_mt5_paper_execution_verifier.py tests/test_mt5_deal_history_ingest.py tests/test_session_autowake_runner.py -q`
    -> `19 passed`
  - `py -3.12 -m pytest tests -q` -> `480 passed`
  - `cd ui && npm run build` -> passed, `51` modules, `532.25 KB` JS /
    `129.48 KB` gzip
- Real-terminal note:
  - Scheduled MT5 attempt
    `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_workflow_queue\agent-workflow-cycle-20260624165947-report.json`
    did not send an MT5 order because the old shared event journal had `28`
    stale pending MT4 receipt rows.
  - After the MT5-specific event-journal split, a real scheduled MT5 run was
    attempted against
    `C:\Program Files\Hugosway\Hugosway PRO5 Terminal\terminal64.exe`, but the
    MT5/Python call did not finish within `120` seconds. The exact
    `run_agent_workflow_queue.py` processes were stopped. Do not claim a
    successful real scheduled-agent MT5 order from that timed-out attempt.
  - Fresh non-executing MT5-lane cockpit report after the event-journal split:
    `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_workflow_queue\agent-workflow-cycle-20260624171015-report.json`.
    It uses `agent-events-mt5-demo.jsonl`, has `approved_intent_count=1`,
    `terminal_command_count=0`, and `pending_receipt_count=0`.
- Next target:
  - Add a process-level MT5 watchdog/worker wrapper so real
    scheduled/autowake MT5 cycles cannot hang the agent loop.
  - Then rerun the scheduled MT5 demo cycle against Hugosway-Demo and refresh
    terminal operability from that scheduled-cycle evidence.

Previous implementation update:

- MT5 closed-deal history ingest is now implemented, surfaced, and verified
  against the real local Hugosway-Demo MT5 account for the explicitly
  confirmed demo verifier trade.
- Implemented:
  - `cas_forex/mt5_deal_history_ingest.py`
  - `scripts/run_mt5_deal_history_ingest.py`
  - `tests/test_mt5_deal_history_ingest.py`
  - `/api/forex/strategy/mt5-deal-history-ingest/latest`
  - Optimizer UI MT5 Deal History run card/detail panel
  - terminal operability MT5 deal-history summary fields
  - default-project MT5 paper-execution seed rows in `agent_memory.py`
  - `MT5DealHistoryIngestPacket` in the agent information-flow map
- Latest real evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\mt5_deal_history_ingest\mt5-deal-history-ingest-20260624162919-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\mt5_deal_history_ingest\mt5-deal-history-ingest-20260624162919-report.md`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\terminal_history_exports\mt5-deal-history-ticket-45938644-20260624162919.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\terminal_history_ingest\terminal-history-ingest-20260624162919-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_memory\agent-memory-20260624162936-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\strategy_dev_queue\strategy-dev-queue-20260624162945-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\daily_learning_rollup\daily-learning-rollup-20260624162946-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\terminal_operability_verifier\terminal-operability-verifier-20260624162936-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624163510-report.json`
- Current MT5 closed-deal facts:
  - ticket / position id `45938644`
  - symbol `EUR/USD`, volume `0.01`
  - raw MT5 history deals `2`
  - closed positions exported `1`
  - memory updates `1`
  - unmatched history rows `0`
  - open / close `1.13489 -> 1.13481`
  - gross trade P/L `-0.08`
  - commission `-0.05`
  - swap `0.0`
  - net account P/L `-0.13`
  - pips `-0.8`
  - R multiple `-0.04`
  - close reason `MT5_HISTORY_CLOSE:CAS_CLOSE`
- Current learning state:
  - agent memory has `terminal_history_joined_count=1`,
    `closed_loss_count=1`, `net_profit_loss_account=-0.13`
  - strategy-dev queue has `closed_loss_memory_count=1`,
    `demotion_review_count=1`
  - daily rollup status is `DAILY_LEARNING_HAS_CLOSED_PNL`
  - terminal operability remains
    `TERMINAL_OPERABILITY_MT5_DEMO_EXECUTION_VERIFIED`
  - terminal lane go `true`
  - live order go `false`
  - broker `ACCEPT` go `false`
  - money movement go `false`
  - blocking reason `live_trading CURRENTLY NOT LICENSED`
- Current next software target:
  - route normal scheduled paper/demo agent workflow commands through the
    proven MT5 execution and deal-history learning loop, instead of relying
    only on the standalone verifier trade.
- Verification:

```text
py -3.12 -m pytest tests -q
# 479 passed

cd ui && npm run build
# 51 modules, 528.95 KB JS, 128.63 KB gzip
```

- Boundary:
  - MT5 demo API, demo execution, closed deal history, memory join, strategy
    queue, daily rollup, and operability are verified for one Hugosway-Demo
    test trade.
  - Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and
    payout automation remain `NOT LICENSED` / `CURRENTLY NOT LICENSED`.

Previous implementation update:

- MT5 demo execution lane is now verified for one explicitly confirmed
  Hugosway demo order and close cycle.
- Operator/runtime action completed:
  - Open MT5 window:
    `1000694 - Hugosway-Demo: Demo Account - Hedge - Hugosway`.
  - Turned on MT5 `Algo Trading` / `AutoTrading`.
  - Reran the MT5 paper execution verifier with:
    `--execute-demo-order --confirm-demo-order`.
- Result:
  - `order_check_status=ORDER_CHECK_OK`
  - `terminal_trade_allowed=true`
  - `execution_status=ORDER_EXECUTED`
  - `broker_ticket=45938644`
  - `filled_price=1.13489`
  - `close_attempted=true`
  - `close_success=true`
  - `open_position_count=0` after close
  - post-close account balance/equity: `99999.87 / 99999.87`
- Current evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\mt5_paper_execution_verifier\mt5-paper-execution-verifier-20260624160137-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\mt5_paper_execution_verifier\mt5-paper-execution-verifier-20260624160137-report.md`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\mt5_terminal_api_verifier\mt5-terminal-api-verifier-20260624160153-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\mt5_terminal_api_verifier\mt5-terminal-api-verifier-20260624160153-report.md`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\terminal_operability_verifier\terminal-operability-verifier-20260624160208-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\terminal_operability_verifier\terminal-operability-verifier-20260624160208-report.md`
- Current terminal operability summary:
  - `operability_status=TERMINAL_OPERABILITY_MT5_DEMO_EXECUTION_VERIFIED`
  - `terminal_lane_go=true`
  - `live_order_go=false`
  - `broker_accept_go=false`
  - `money_movement_go=false`
  - `blocking_reasons=["live_trading CURRENTLY NOT LICENSED"]`
- Current next software/evidence target:
  - build MT5 closed-history/deal ingestion so this executed/closed demo order
    contributes P/L, commission, swap, close reason, and deal facts into CAS
    memory, daily learning rollup, and strategy evaluation.
- Verification:

```text
py -3.12 -m pytest tests -q
# 475 passed

cd ui && npm run build
# 51 modules, 520.06 KB JS, 126.96 KB gzip
```

- Boundary:
  - The MT5 demo execution lane is verified for one demo order and close
    cycle.
  - Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and
    payout automation remain `NOT LICENSED` / `CURRENTLY NOT LICENSED`.

Previous implementation update:

- The explicitly confirmed MT5 demo-order proof has now been attempted
  against the real local Hugosway MT5 demo terminal.
- Result:
  - CAS Forex built the request.
  - Broker-side `order_check` returned `ORDER_CHECK_OK`.
  - CAS Forex attempted the demo send.
  - MT5 rejected the send with retcode `10027`.
  - Exact error: `AutoTrading disabled by client: AutoTrading disabled by client`.
  - Terminal trade permission currently reads `terminal_trade_allowed=false`.
- This means the next blocker is the MT5 terminal AutoTrading / Algo Trading
  permission, not request-shape, filling-mode, margin, or symbol validation.
- Updated code/files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\broker\mt5_bridge.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\mt5_paper_execution_verifier.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\terminal_operability_verifier.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_mt5_paper_execution_verifier.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_terminal_operability_verifier.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\types\evidence.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\OptimizerPage.tsx`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
- Current evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\mt5_paper_execution_verifier\mt5-paper-execution-verifier-20260624155515-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\mt5_paper_execution_verifier\mt5-paper-execution-verifier-20260624155515-report.md`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\terminal_operability_verifier\terminal-operability-verifier-20260624155528-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\terminal_operability_verifier\terminal-operability-verifier-20260624155528-report.md`
- Current MT5 paper execution summary:
  - `verifier_status=MT5_PAPER_EXECUTION_DEMO_ORDER_REJECTED`
  - `terminal_connected=true`
  - `server=Hugosway-Demo`
  - `account_balance=100000.0`
  - `account_equity=100000.0`
  - `symbol=EUR/USD`
  - `volume=0.01`
  - `order_request_built=true`
  - `order_check_status=ORDER_CHECK_OK`
  - `execution_attempted=true`
  - `execution_status=ORDER_REJECTED`
  - `execution_error_message=AutoTrading disabled by client: AutoTrading disabled by client`
  - `terminal_trade_allowed=false`
  - `raw_response_hash=e6682c1c10d49596d71bb26a4ff08d9d886610d6feae671be707ffd7da6132a9`
  - `live_mode_used=false`
- Current terminal operability summary:
  - `operability_status=TERMINAL_OPERABILITY_MT5_AUTOTRADING_DISABLED`
  - `terminal_lane_go=false`
  - `live_order_go=false`
  - `broker_accept_go=false`
  - `money_movement_go=false`
- Next operator action:
  - Turn on Algo Trading / AutoTrading in the Hugosway MT5 terminal.
  - Confirm the terminal allows trading.
  - Rerun:

```text
cd C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex
py -3.12 scripts/run_mt5_paper_execution_verifier.py --mt5-path "C:\Program Files\Hugosway\Hugosway PRO5 Terminal\terminal64.exe" --symbol EUR/USD --volume 0.01 --execute-demo-order --confirm-demo-order --summary-only
py -3.12 scripts/run_terminal_operability_verifier.py --summary-only
```

- Verification:

```text
py -3.12 -m pytest tests/test_mt5_paper_execution_verifier.py tests/test_terminal_operability_verifier.py tests/test_pip_math_regressions.py -q
# 26 passed

py -3.12 -m pytest tests -q
# 475 passed

cd ui && npm run build
# 51 modules, 520.43 KB JS, 126.99 KB gzip
```

- Boundary:
  - This proves the confirmed demo-send attempt reached MT5 and captured the
    terminal rejection.
  - It does not yet prove an executed demo-order receipt.
  - It does not create live trading permission, broker `ACCEPT`, deposit,
    withdrawal, bank/card movement, or payout automation.

Previous implementation update:

- MT5 paper execution verifier is now implemented, surfaced, and dry-run
  verified against the real local Hugosway MT5 demo terminal.
- CAS Forex can now build the exact MT5 order request from a
  `BrokerOrderRequest` and get a broker-side `order_check` pass without
  sending an order.
- Important broker finding:
  - Hugosway `EUR/USD` rejected IOC with `Unsupported filling mode`.
  - The bridge now reads the symbol filling mode and uses FOK
    (`type_filling: 0`) for this symbol, which passed `order_check`.
- New code/files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\mt5_paper_execution_verifier.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_mt5_paper_execution_verifier.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_mt5_paper_execution_verifier.py`
- Updated code/files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\broker\mt5_bridge.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\data.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\strategy.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\terminal_operability_verifier.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_information_flow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_agent_information_flow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_terminal_operability_verifier.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_pip_math_regressions.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\types\evidence.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\api.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\App.tsx`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\OptimizerPage.tsx`
- Current evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\mt5_paper_execution_verifier\mt5-paper-execution-verifier-20260624154210-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\mt5_paper_execution_verifier\mt5-paper-execution-verifier-20260624154210-report.md`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\terminal_operability_verifier\terminal-operability-verifier-20260624154222-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\terminal_operability_verifier\terminal-operability-verifier-20260624154222-report.md`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624154148-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624154148-report.md`
- Current MT5 paper execution summary:
  - `verifier_status=MT5_PAPER_EXECUTION_DRY_RUN_READY`
  - `terminal_connected=true`
  - `server=Hugosway-Demo`
  - `account_balance=100000.0`
  - `account_equity=100000.0`
  - `symbol=EUR/USD`
  - `volume=0.01`
  - `order_request_built=true`
  - `order_check_status=ORDER_CHECK_OK`
  - `execution_attempted=false`
  - `execution_status=DRY_RUN_NO_ORDER_SENT`
  - `live_mode_used=false`
- Current terminal operability summary:
  - `operability_status=TERMINAL_OPERABILITY_MT5_DRY_RUN_READY_DEMO_SEND_REQUIRED`
  - `terminal_lane_go=false`
  - `live_order_go=false`
  - `broker_accept_go=false`
  - `money_movement_go=false`
- Next proof target:
  - run one explicitly confirmed MT5 demo-order pass, then refresh terminal
    operability

```text
cd C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex
py -3.12 scripts/run_mt5_paper_execution_verifier.py --mt5-path "C:\Program Files\Hugosway\Hugosway PRO5 Terminal\terminal64.exe" --symbol EUR/USD --volume 0.01 --execute-demo-order --confirm-demo-order --summary-only
py -3.12 scripts/run_terminal_operability_verifier.py --summary-only
```

- Verification:

```text
py -3.12 -m pytest tests/test_mt5_paper_execution_verifier.py tests/test_terminal_operability_verifier.py tests/test_agent_information_flow.py tests/test_pip_math_regressions.py -q
# 29 passed

py -3.12 -m pytest tests -q
# 473 passed

cd ui && npm run build
# 51 modules, 518.87 KB JS, 126.78 KB gzip
```

- Boundary:
  - This proves MT5 demo request build plus broker `order_check`.
  - It does not yet prove a submitted demo-order receipt.
  - It does not create live trading permission, broker `ACCEPT`, deposit,
    withdrawal, bank/card movement, or payout automation.

Previous implementation update:

- MT5 terminal API verifier is now implemented, verified, and surfaced.
- CAS Forex now sees the local running Hugosway MT5 terminal through the
  `MetaTrader5` Python API, reads demo broker account state, and feeds that
  evidence into the terminal operability report.
- New code/files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\mt5_terminal_api_verifier.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_mt5_terminal_api_verifier.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_mt5_terminal_api_verifier.py`
- Updated code/files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\broker\mt5_bridge.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\data.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\strategy.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\terminal_operability_verifier.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_information_flow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_agent_information_flow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_terminal_operability_verifier.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_pip_math_regressions.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\types\evidence.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\api.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\App.tsx`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\OptimizerPage.tsx`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\.gitignore`
- Real local terminal facts:
  - MT5 executable:
    `C:\Program Files\Hugosway\Hugosway PRO5 Terminal\terminal64.exe`
  - MT5 terminal: connected
  - terminal name: `MetaTrader 5`
  - server: `Hugosway-Demo`
  - broker mode: `PAPER_MT5`
  - account balance/equity: `100000.0 / 100000.0`
  - open positions: `0`
  - open positions reconciled: `true`
  - live mode used: `false`
  - MT4 candidate folders: `0`
  - MT5-only terminal folders: `2`
- Current evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\mt5_terminal_api_verifier\mt5-terminal-api-verifier-20260624150739-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\mt5_terminal_api_verifier\mt5-terminal-api-verifier-20260624150739-report.md`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\terminal_operability_verifier\terminal-operability-verifier-20260624150902-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\terminal_operability_verifier\terminal-operability-verifier-20260624150902-report.md`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\index_tsmom_126_paper_proof\index-tsmom-126-d1-paper-proof-mt5-demo-probe-20260624150120.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624152031-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624152031-report.md`
- Current operability summary:
  - `operability_status=TERMINAL_OPERABILITY_MT5_API_VERIFIED_MT4_BRIDGE_MISSING`
  - `terminal_lane_go=false`
  - `live_order_go=false`
  - `broker_accept_go=false`
  - `money_movement_go=false`
  - `mt5_terminal_api_verifier_status=MT5_API_VERIFIER_BROKER_API_VERIFIED`
  - `mt5_terminal_connected=true`
  - `mt5_account_snapshot_present=true`
  - `mt5_open_position_count=0`
  - `mt5_open_positions_reconciled=true`
  - `mt5_server=Hugosway-Demo`
- Current UI/proof maturity:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\index_tsmom_126_paper_proof\index-tsmom-126-d1-paper-proof-ui-readiness-status.json`
  - `complete_bundle_days=3`
  - `broker_verified_days=3`
  - required for the current UI maturity gate: `5`
  - complete dates: `2026-06-22`, `2026-06-23`, `2026-06-24`
  - 30-day proof is still incomplete
- Agent information-flow update:
  - includes `MT5TerminalApiVerifierPacket`
  - includes `/api/forex/strategy/mt5-terminal-api-verifier/latest`
  - marks `cas_forex/mt5_terminal_api_verifier.py` as `COMPLETE_INITIAL`
  - changes `must_have_next_file` to
    `cas_forex/mt5_paper_execution_verifier.py`
- Next implementation target:
  - build `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\mt5_paper_execution_verifier.py`
  - goal: prove a gated MT5 paper/demo order lifecycle through `MT5Bridge`
    including submit, receipt, reconcile, close/history join, memory update,
    and daily rollup
  - alternate lane: install/attach MT4 if the EA mailbox path is still
    preferred
- Verification:

```text
py -3.12 -m pytest tests/test_agent_information_flow.py tests/test_mt5_terminal_api_verifier.py tests/test_terminal_operability_verifier.py tests/test_pip_math_regressions.py -q
# 26 passed

py -3.12 -m pytest tests -q
# 467 passed

cd ui && npm run build
# 51 modules, 509.94 KB JS, 125.11 KB gzip
```

Previous implementation update:

- Terminal operability verifier is now implemented and surfaced.
- This completes the concrete source-code step after terminal position
  reconciliation: CAS Forex now has one top-level go/no-go report that bundles
  MT4 terminal session, bridge heartbeat, receipt ingest, MT4 history export
  verifier, terminal history ingest, terminal position reconciliation, and
  runtime gate evidence.
- New code/files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\terminal_operability_verifier.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_terminal_operability_verifier.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_terminal_operability_verifier.py`
- Updated API/UI/roadmap files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\data.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\strategy.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_information_flow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_agent_information_flow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\types\evidence.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\api.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\App.tsx`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\OptimizerPage.tsx`
- Operability behavior:
  - loads latest MT4 terminal session, terminal bridge supervisor, terminal
    receipt ingest, MT4 history export verifier, terminal history ingest,
    terminal position reconciliation, and runtime-gate reports
  - reports terminal-lane go/no-go separately from live-order go/no-go,
    broker `ACCEPT` go/no-go, and money-movement go/no-go
  - reports clear states including
    `TERMINAL_OPERABILITY_NEEDS_MT4_TERMINAL`,
    `TERMINAL_OPERABILITY_NEEDS_HEARTBEAT`,
    `TERMINAL_OPERABILITY_WAITING_FOR_RECEIPTS`,
    `TERMINAL_OPERABILITY_POSITION_MISMATCH`,
    `TERMINAL_OPERABILITY_READY_OPEN_POSITIONS`, and
    `TERMINAL_OPERABILITY_READY_FLAT`
- Current terminal operability evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\terminal_operability_verifier\terminal-operability-verifier-20260624145246-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\terminal_operability_verifier\terminal-operability-verifier-20260624145246-report.md`
- Refreshed information-flow report:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624145333-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624145333-report.md`
  - `must_have_next_file=MQL4/Files/CASForexMailbox/heartbeat.json`
  - `cas_forex/terminal_operability_verifier.py` status is
    `COMPLETE_INITIAL`
- Current operability summary:
  - `operability_status=TERMINAL_OPERABILITY_NEEDS_MT4_TERMINAL`
  - `terminal_lane_go=false`
  - `live_order_go=false`
  - `broker_accept_go=false`
  - `money_movement_go=false`
  - `session_status=MT4_SESSION_NEEDS_MT4_TERMINAL`
  - `bridge_status=TERMINAL_BRIDGE_HEARTBEAT_MISSING`
  - `heartbeat_status=MISSING`
  - `history_export_verifier_status=MT4_HISTORY_EXPORT_NEEDS_MT4_TERMINAL`
  - `position_reconciliation_status=TERMINAL_POSITION_RECONCILIATION_NEEDS_MT4_TERMINAL`
  - `account_snapshot_present=false`
  - `pending_receipt_count=28`
  - `cas_open_position_count=28`
  - `terminal_open_position_count=0`
  - `reconciled_open_position_count=0`
  - `unmatched_open_position_count=28`
  - runtime-gate pending capabilities: `live_trading`, `broker_accept`,
    `auto_deposit`, `bank_card_movement`, `payout_automation`
- Important operational fact:
  - The operability verifier source exists and is API/UI-visible, but it proves
    the current machine still lacks attached MT4 terminal evidence. The next
    proof is not another abstract code file; it is actual terminal mailbox
    output: heartbeat, receipts with account snapshots, open-position evidence,
    and closed-history export.
- Commands for the next real MT4 pass:

```text
cd C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex
py -3.12 scripts/run_mt4_terminal_session_verifier.py --terminal-data-dir "<MT4_DATA_DIR>" --install --wait-seconds 10
py -3.12 scripts/run_mt4_history_export_verifier.py --mailbox-dir "<MT4_DATA_DIR>\MQL4\Files\CASForexMailbox" --summary-only
py -3.12 scripts/run_terminal_position_reconciliation.py --summary-only
py -3.12 scripts/run_terminal_operability_verifier.py --summary-only
```

- MT4 attach sequence after activation:
  - attach `CASForexBridgeEA.mq4` with `MailboxRoot=CASForexMailbox`
  - attach `CASForexHistoryExporterEA.mq4` with `MailboxRoot=CASForexMailbox`
  - expected heartbeat:
    `<MT4_DATA_DIR>\MQL4\Files\CASForexMailbox\heartbeat.json`
  - expected receipts:
    `<MT4_DATA_DIR>\MQL4\Files\CASForexMailbox\receipts\*.json`
  - expected history export:
    `<MT4_DATA_DIR>\MQL4\Files\CASForexMailbox\history\cas_forex_closed_history.json`
- Verification:

```text
py -3.12 -m pytest tests/test_terminal_operability_verifier.py tests/test_agent_information_flow.py -q
# 9 passed

py -3.12 -m pytest tests -q
# 461 passed

cd ui && npm run build
# 51 modules, 501.28 KB JS, 123.38 KB gzip
```

- Next implementation/evidence target:
  - attach a real MT4 terminal and produce
    `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\MQL4\Files\CASForexMailbox\heartbeat.json`
    equivalent evidence under the actual MT4 data folder. Then rerun the
    session/history/reconciliation/operability commands above.

Previous implementation update:

- Terminal position reconciliation is now implemented and surfaced.
- This completes the concrete source-code step after the MT4 history export
  verifier: CAS Forex can now compare CAS agent memory with terminal bridge
  supervisor evidence, terminal receipt ingest, terminal history ingest, MT4
  history export verifier output, account snapshots, open-position rows, and
  closed-history memory updates.
- New code/files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\terminal_position_reconciliation.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_terminal_position_reconciliation.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_terminal_position_reconciliation.py`
- Updated API/UI/roadmap files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\data.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\strategy.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_information_flow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_agent_information_flow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\types\evidence.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\api.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\App.tsx`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\OptimizerPage.tsx`
- Reconciliation behavior:
  - loads the latest terminal bridge supervisor, terminal receipt ingest,
    terminal history ingest, agent memory, and MT4 history export verifier
    reports
  - extracts terminal account snapshots and open-position rows when present
  - derives CAS open positions from approved command memory rows
  - removes positions that have already joined closed-history rows
  - matches CAS and terminal positions by `command_id`, `receipt_id`,
    `broker_ticket`, or symbol/direction/lots fallback
  - reports clear states including
    `TERMINAL_POSITION_RECONCILIATION_NEEDS_MT4_TERMINAL`,
    `TERMINAL_POSITION_RECONCILIATION_WAITING_FOR_RECEIPTS`,
    `TERMINAL_POSITION_RECONCILIATION_MISMATCH`,
    `TERMINAL_POSITION_RECONCILIATION_READY_OPEN_POSITIONS`, and
    `TERMINAL_POSITION_RECONCILIATION_READY_FLAT`
- Current terminal position reconciliation evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\terminal_position_reconciliation\terminal-position-reconciliation-20260624143531-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\terminal_position_reconciliation\terminal-position-reconciliation-20260624143531-report.md`
- Refreshed information-flow report:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624143602-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624143602-report.md`
  - `must_have_next_file=cas_forex/terminal_operability_verifier.py`
  - `cas_forex/terminal_position_reconciliation.py` status is
    `COMPLETE_INITIAL`
- Current reconciliation summary:
  - `reconciliation_status=TERMINAL_POSITION_RECONCILIATION_NEEDS_MT4_TERMINAL`
  - `bridge_status=TERMINAL_BRIDGE_HEARTBEAT_MISSING`
  - `heartbeat_status=MISSING`
  - `account_snapshot_present=false`
  - `pending_receipt_count=28`
  - `cas_open_position_count=28`
  - `terminal_open_position_count=0`
  - `reconciled_open_position_count=0`
  - `unmatched_open_position_count=28`
  - `history_record_count=0`
  - `memory_update_count=0`
  - `net_profit_loss_account=0.0`
- Important operational fact:
  - The reconciliation source exists and is API/UI-visible, but it proves the
    current machine still lacks live terminal facts: no fresh MT4 heartbeat, no
    terminal account snapshot, no terminal open-position rows, and no closed
    history rows.
- Commands for the next real MT4 pass:

```text
cd C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex
py -3.12 scripts/run_mt4_terminal_session_verifier.py --terminal-data-dir "<MT4_DATA_DIR>" --install --wait-seconds 10
py -3.12 scripts/run_mt4_history_export_verifier.py --mailbox-dir "<MT4_DATA_DIR>\MQL4\Files\CASForexMailbox" --summary-only
py -3.12 scripts/run_terminal_position_reconciliation.py --summary-only
```

- MT4 attach sequence after activation:
  - attach `CASForexBridgeEA.mq4` with `MailboxRoot=CASForexMailbox`
  - attach `CASForexHistoryExporterEA.mq4` with `MailboxRoot=CASForexMailbox`
  - expected heartbeat:
    `<MT4_DATA_DIR>\MQL4\Files\CASForexMailbox\heartbeat.json`
  - expected receipts:
    `<MT4_DATA_DIR>\MQL4\Files\CASForexMailbox\receipts\*.json`
  - expected history export:
    `<MT4_DATA_DIR>\MQL4\Files\CASForexMailbox\history\cas_forex_closed_history.json`
- Verification:

```text
py -3.12 -m pytest tests/test_terminal_position_reconciliation.py tests/test_agent_information_flow.py tests/test_mt4_history_export_verifier.py -q
# 13 passed

py -3.12 -m pytest tests -q
# 457 passed

cd ui && npm run build
# 51 modules, 491.38 KB JS, 122.03 KB gzip
```

- Next implementation target completed in the latest update above:
  - build `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\terminal_operability_verifier.py`
    so CAS Forex has one top-level go/no-go report bundling MT4 session,
    heartbeat, receipts, history export, position reconciliation, runtime
    gates, and operator next actions.

Earlier implementation update:

- MT4 history export verifier is now implemented and surfaced.
- This completes the concrete source-code step after the MT4 closed-history
  exporter EA source: CAS Forex can now verify whether an attached MT4 terminal
  has produced closed-history JSON, validate the export schema, optionally feed
  it through `terminal_history_ingest`, and surface that proof in the API and
  Optimizer UI.
- New code/files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\mt4_history_export_verifier.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_mt4_history_export_verifier.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_mt4_history_export_verifier.py`
- Updated API/UI/roadmap files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\data.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\strategy.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_information_flow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\types\evidence.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\api.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\App.tsx`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\OptimizerPage.tsx`
- Verifier behavior:
  - verifies `CASForexHistoryExporterEA.mq4` source presence
  - resolves the MT4 mailbox from explicit paths or the latest MT4 session
    verifier report
  - checks expected history export
    `<MT4_DATA_DIR>\MQL4\Files\CASForexMailbox\history\cas_forex_closed_history.json`
  - checks exporter status under
    `<MT4_DATA_DIR>\MQL4\Files\CASForexMailbox\status`
  - validates schema `cas_forex_mt4_closed_history_export.v1`
  - can run `terminal_history_ingest` and report memory update counts
  - reports clear states including `MT4_HISTORY_EXPORT_NEEDS_MT4_TERMINAL`,
    `MT4_HISTORY_EXPORT_FILE_MISSING`, `MT4_HISTORY_EXPORT_EMPTY`, and
    `MT4_HISTORY_EXPORT_INGEST_READY`
- Current MT4 history export verifier evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\mt4_history_export_verifier\mt4-history-export-verifier-20260624141540-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\mt4_history_export_verifier\mt4-history-export-verifier-20260624141540-report.md`
- Refreshed information-flow report:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624141555-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624141555-report.md`
  - `must_have_next_file=cas_forex/terminal_position_reconciliation.py`
  - `cas_forex/mt4_history_export_verifier.py` status is `COMPLETE_INITIAL`
- Current verifier summary:
  - `verifier_status=MT4_HISTORY_EXPORT_NEEDS_MT4_TERMINAL`
  - `ea_source_present=true`
  - `mailbox_ready=false`
  - `history_export_present=false`
  - `history_export_parse_status=NO_MAILBOX`
  - `history_record_count=0`
  - `memory_update_count=0`
  - `net_profit_loss_account=0.0`
- Important operational fact:
  - The verifier source exists and is API/UI-visible, but there is still no
    real MT4 terminal folder/export on this machine. The next proof requires
    MT4 itself to run both EAs and produce heartbeat, receipt, and
    closed-history files in the mailbox.
- Command for the next real MT4 pass:

```text
cd C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex
py -3.12 scripts/run_mt4_terminal_session_verifier.py --terminal-data-dir "<MT4_DATA_DIR>" --install --wait-seconds 10
py -3.12 scripts/run_mt4_history_export_verifier.py --mailbox-dir "<MT4_DATA_DIR>\MQL4\Files\CASForexMailbox" --summary-only
```

- MT4 attach sequence after activation:
  - attach `CASForexBridgeEA.mq4` with `MailboxRoot=CASForexMailbox`
  - attach `CASForexHistoryExporterEA.mq4` with `MailboxRoot=CASForexMailbox`
  - expected history export:
    `<MT4_DATA_DIR>\MQL4\Files\CASForexMailbox\history\cas_forex_closed_history.json`
- Verification:

```text
py -3.12 -m pytest tests/test_mt4_history_export_verifier.py tests/test_mt4_history_exporter_ea.py tests/test_mt4_terminal_session_verifier.py tests/test_agent_information_flow.py -q
# 15 passed

py -3.12 -m pytest tests -q
# 453 passed

cd ui && npm run build
# 51 modules, 482.70 KB JS, 120.66 KB gzip
```

- Next implementation target completed in the latest update above:
  `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\terminal_position_reconciliation.py`.

Earlier implementation update:

- MT4 closed-history exporter EA source is now implemented.
- This completes the concrete source-code step after the MT4 terminal session
  verifier: CAS Forex now has an MT4-side EA that reads closed Account History
  rows and writes CAS-shaped close-history JSON for `terminal_history_ingest`,
  memory, daily rollup, and strategy improvement.
- New code/files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\mt4\Experts\CASForexHistoryExporterEA.mq4`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_mt4_history_exporter_ea.py`
- Updated roadmap/verifier/UI fixture files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\mt4_terminal_session_verifier.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_information_flow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_mt4_terminal_session_verifier.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_agent_information_flow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
- Exporter behavior:
  - reads closed MT4 history with `OrdersHistoryTotal()` and
    `OrderSelect(..., MODE_HISTORY)`
  - writes ingestable JSON to
    `MQL4\Files\CASForexMailbox\history\cas_forex_closed_history.json`
  - writes exporter status separately to
    `MQL4\Files\CASForexMailbox\status\cas_forex_closed_history_status.json`
  - includes broker ticket, symbol, direction, lots, open/close times,
    open/close prices, SL/TP, net P/L, commission, swap, magic number,
    comment, account hash, server, and broker mode
  - contains no `OrderSend`, `OrderClose`, `OrderModify`, or `OrderDelete`
    calls
- Current MT4 session evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\mt4_terminal_session_verifier\mt4-terminal-session-verifier-20260624140047-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\mt4_terminal_session_verifier\mt4-terminal-session-verifier-20260624140047-report.md`
- Refreshed information-flow report:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624140031-report.json`
  - `must_have_next_file=cas_forex/mt4_history_export_verifier.py`
  - `mt4/Experts/CASForexHistoryExporterEA.mq4` status is
    `SOURCE_READY_NEEDS_TERMINAL_ATTACH`
- Current MT4 session summary:
  - `session_status=MT4_SESSION_NEEDS_MT4_TERMINAL`
  - `activation_status=MT4_ACTIVATION_NEEDS_MT4_TERMINAL`
  - `roundtrip_status=MT4_PING_NEEDS_ACTIVATED_MAILBOX`
  - `mt4_candidate_count=0`
  - `mt5_only_candidate_count=2`
- Important operational fact:
  - The exporter source exists, but no real MT4 terminal folder is present yet.
    The next proof requires MT4 itself to run both EAs and produce heartbeat,
    receipt, and closed-history files in the mailbox.
- Command for the next real MT4 pass:

```text
cd C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex
py -3.12 scripts/run_mt4_terminal_session_verifier.py --terminal-data-dir "<MT4_DATA_DIR>" --install --wait-seconds 10
```

- MT4 attach sequence after activation:
  - attach `CASForexBridgeEA.mq4` with `MailboxRoot=CASForexMailbox`
  - attach `CASForexHistoryExporterEA.mq4` with `MailboxRoot=CASForexMailbox`
  - expected history export:
    `<MT4_DATA_DIR>\MQL4\Files\CASForexMailbox\history\cas_forex_closed_history.json`
- Verification:

```text
py -3.12 -m pytest tests/test_mt4_history_exporter_ea.py tests/test_terminal_history_ingest.py tests/test_mt4_terminal_session_verifier.py tests/test_agent_information_flow.py -q
# 13 passed

py -3.12 -m pytest tests -q
# 449 passed

cd ui && npm run build
# 51 modules, 477.07 KB JS, 119.57 KB gzip
```

Earlier implementation update:

- MT4 terminal session verifier is now implemented and surfaced.
- This completes the concrete source-code step after the MT4 ping roundtrip:
  CAS Forex can now run activation, ping, bridge supervisor, terminal watcher,
  receipt ingest, history ingest, memory, daily rollup, and session autowake
  refresh as one operator-level verification report.
- New code/files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\mt4_terminal_session_verifier.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_mt4_terminal_session_verifier.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_mt4_terminal_session_verifier.py`
- Updated API/UI/roadmap files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\data.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\strategy.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_information_flow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\types\evidence.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\api.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\App.tsx`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\OptimizerPage.tsx`
- Current MT4 session evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\mt4_terminal_session_verifier\mt4-terminal-session-verifier-20260624134013-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\mt4_terminal_session_verifier\mt4-terminal-session-verifier-20260624134013-report.md`
- MT4 session summary:
  - `session_status=MT4_SESSION_NEEDS_MT4_TERMINAL`
  - `activation_status=MT4_ACTIVATION_NEEDS_MT4_TERMINAL`
  - `roundtrip_status=MT4_PING_NEEDS_ACTIVATED_MAILBOX`
  - `mt4_candidate_count=0`
  - `mt5_only_candidate_count=2`
  - `mailbox_ready=false`
  - `ping_written=false`
  - `heartbeat_present=false`
  - `receipt_present=false`
  - `skipped_step_count=2`
- Refreshed information-flow report:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624134619-report.json`
  - `must_have_next_file=mt4/Experts/CASForexHistoryExporterEA.mq4`
  - `cas_forex/mt4_terminal_session_verifier.py` status is `COMPLETE_INITIAL`
- Important operational fact:
  - The session verifier exists and proves the current blocker cleanly: this
    machine still needs an actual MT4 terminal data folder with `MQL4\Experts`.
    Once MT4 exists, run the verifier with `--terminal-data-dir` and
    `--install`, attach the bridge EA, and rerun it with a wait window.
- Command for the next real MT4 session pass:

```text
cd C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex
py -3.12 scripts/run_mt4_terminal_session_verifier.py --terminal-data-dir "<MT4_DATA_DIR>" --install --wait-seconds 10
```

- Verification:

```text
py -3.12 -m pytest tests/test_mt4_terminal_session_verifier.py tests/test_agent_information_flow.py -q
# 9 passed

cd ui && npm run build
# 51 modules, 475.27 KB JS, 119.21 KB gzip
```

- Next implementation target:
  - build `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\mt4\Experts\CASForexHistoryExporterEA.mq4`
    so completed MT4 account-history rows can be exported into CAS Forex
    history files and fed into `terminal_history_ingest`, memory, daily rollup,
    and strategy improvement.

Previous implementation update:

- MT4 ping roundtrip is now implemented and surfaced.
- This completes the concrete source-code step after MT4 terminal activation:
  CAS Forex can now resolve the activated MT4 mailbox, write one `PING`
  command through the existing MT4 mailbox bridge, wait for `heartbeat.json`
  and the matching `receipt-<command_id>.json`, verify request-hash match and
  visible live flags, and report whether the MT4 EA is actually answering.
- New code/files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\mt4_ping_roundtrip.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_mt4_ping_roundtrip.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_mt4_ping_roundtrip.py`
- Updated API/UI/roadmap files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\data.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\strategy.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_information_flow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\types\evidence.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\api.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\App.tsx`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\OptimizerPage.tsx`
- Current MT4 ping evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\mt4_ping_roundtrip\mt4-ping-roundtrip-20260624122729-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\mt4_ping_roundtrip\mt4-ping-roundtrip-20260624122729-report.md`
- MT4 ping summary:
  - `roundtrip_status=MT4_PING_NEEDS_ACTIVATED_MAILBOX`
  - `activation_status=MT4_ACTIVATION_NEEDS_MT4_TERMINAL`
  - `mailbox_ready=false`
  - `ping_written=false`
  - `heartbeat_present=false`
  - `receipt_present=false`
  - `receipt_status=null`
  - `live_flag_visible=false`
- Refreshed information-flow report:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624123345-report.json`
  - `must_have_next_file=cas_forex/mt4_terminal_session_verifier.py`
  - `cas_forex/mt4_ping_roundtrip.py` status is `COMPLETE_INITIAL`
- Important operational fact:
  - The ping verifier exists, but it cannot write a meaningful terminal ping
    until there is an activated MT4 mailbox. This machine still shows no MT4
    data folder from CAS Forex's point of view. Install/open MT4, activate the
    real MT4 data folder, attach `CASForexBridgeEA.mq4`, then rerun the ping
    verifier.
- Commands for the next real MT4 pass:

```text
cd C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex
py -3.12 scripts/run_mt4_terminal_activation.py --terminal-data-dir "<MT4_DATA_DIR>" --install
py -3.12 scripts/run_mt4_ping_roundtrip.py --mailbox-dir "<MT4_DATA_DIR>\MQL4\Files\CASForexMailbox" --wait-seconds 10
```

- Verification:

```text
py -3.12 -m pytest tests/test_mt4_ping_roundtrip.py tests/test_agent_information_flow.py -q
# 9 passed

py -3.12 -m pytest tests -q
# 443 passed

$env:VITE_CAS_FOREX_API_BASE='http://127.0.0.1:8810/api/forex'; npm run build
# 51 modules, 467.70 KB JS, 118.10 KB gzip
```

- Fresh local smoke:
  - API health: `http://127.0.0.1:8810/api/forex/health`
  - MT4 ping API:
    `http://127.0.0.1:8810/api/forex/strategy/mt4-ping-roundtrip/latest`
  - dashboard API: `http://127.0.0.1:8810/api/forex/dashboard`
  - UI preview: `http://127.0.0.1:5220/?page=optimizer`
- Startup note:
  - Run the local API with `py -3.12` and `PYTHONPATH=.pydeps-win312;.` on
    this machine. The default `python` is Python 3.14, but `.pydeps-win312`
    contains Python 3.12 native wheels.
- Next implementation target:
  - build `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\mt4_terminal_session_verifier.py`
    so one operator command can run activation, ping, supervisor, watcher,
    receipt ingest, history ingest, memory, daily rollup, and session autowake
    refresh together after MT4 is installed/opened.

Previous implementation update:

- MT4 terminal activation is now implemented and surfaced.
- This completes the concrete source-code step after the terminal bridge
  supervisor: CAS Forex can now discover MetaQuotes terminal data folders,
  classify folders as MT4 vs MT5-only, verify the real EA source, stage/copy
  `CASForexBridgeEA.mq4` into `MQL4\Experts`, create the MT4 file-sandbox
  mailbox, report the exact MT4 attach settings, and tell CAS command writers
  which mailbox path must be used after activation.
- New code/files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\mt4_terminal_activation.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_mt4_terminal_activation.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_mt4_terminal_activation.py`
- Updated API/UI/roadmap files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\data.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\strategy.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_information_flow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\types\evidence.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\api.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\App.tsx`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\OptimizerPage.tsx`
- Current MT4 activation evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\mt4_terminal_activation\mt4-terminal-activation-20260624121406-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\mt4_terminal_activation\mt4-terminal-activation-20260624121406-report.md`
- MT4 activation summary:
  - `activation_status=MT4_ACTIVATION_NEEDS_MT4_TERMINAL`
  - `ea_source_present=true`
  - `mt4_candidate_count=0`
  - `mt5_only_candidate_count=2`
  - `selected_terminal=null`
  - `ea_installed=false`
  - `mailbox_ready=false`
  - `heartbeat_present=false`
  - `alignment_status=NO_ACTIVATED_MAILBOX`
  - `LiveTradingAllowed=false`
- Refreshed information-flow report:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624121041-report.json`
  - `must_have_next_file=cas_forex/mt4_ping_roundtrip.py`
  - `cas_forex/mt4_terminal_activation.py` status is `COMPLETE_INITIAL`
- Important operational fact:
  - This machine currently shows two MT5-only terminal folders and zero MT4
    data folders. The next real move is not more UI polish; it is to install
    or open MT4, identify the MT4 data folder containing `MQL4\Experts`, run
    activation with `--install`, attach the EA inside MT4, and then prove a
    heartbeat/receipt roundtrip.
- Command for the next real MT4 activation pass:

```text
cd C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex
py -3.12 scripts/run_mt4_terminal_activation.py --terminal-data-dir "<MT4_DATA_DIR>" --install
```

- MT4 EA attach settings:
  - `MailboxRoot=CASForexMailbox`
  - `UseCommonFiles=false`
  - `LiveTradingAllowed=false`
  - `TimerSeconds=2`
  - `MaxCommandsPerTimer=10`
- Verification:

```text
py -3.12 -m pytest tests/test_mt4_terminal_activation.py tests/test_agent_information_flow.py -q
# 10 passed

py -3.12 -m pytest tests -q
# 439 passed

cd ui && npm run build
# 51 modules, 462.34 KB JS, 117.06 KB gzip
```

- Fresh local smoke:
  - API health: `http://127.0.0.1:8809/api/forex/health`
  - MT4 activation API:
    `http://127.0.0.1:8809/api/forex/strategy/mt4-terminal-activation/latest`
  - dashboard API: `http://127.0.0.1:8809/api/forex/dashboard`
  - UI preview: `http://127.0.0.1:5219/?page=optimizer`
- Startup note:
  - Run the local API with `py -3.12` and `PYTHONPATH=.pydeps-win312;.` on
    this machine. The default `python` is Python 3.14, but `.pydeps-win312`
    contains Python 3.12 native wheels.
- Next implementation target:
  - build `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\mt4_ping_roundtrip.py`
    so CAS Forex can write a ping command into the activated MT4 mailbox, wait
    for terminal heartbeat and receipt JSON, then refresh supervisor, watcher,
    receipt ingest, memory, research queue, strategy-dev queue, patch runner,
    daily rollup, and session autowake evidence.

Previous implementation update:

- Terminal bridge supervisor is now implemented and surfaced.
- This completes the concrete source-code step after the terminal receipt
  watcher: CAS Forex can now observe the MT4/MT5 bridge heartbeat, mailbox
  folders, command files, receipt files, close-history exports, account
  snapshot presence, visible live flag state, event-journal pending receipts,
  and terminal-run alerts.
- New code/files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\terminal_bridge_supervisor.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_terminal_bridge_supervisor.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_terminal_bridge_supervisor.py`
- Updated API/UI/roadmap files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\data.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\strategy.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_information_flow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\types\evidence.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\api.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\App.tsx`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\OptimizerPage.tsx`
- Current terminal bridge supervisor evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\terminal_bridge_supervisor\terminal-bridge-supervisor-20260624115153-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\terminal_bridge_supervisor\terminal-bridge-supervisor-20260624115153-report.md`
- Terminal bridge supervisor summary:
  - `supervisor_status=TERMINAL_BRIDGE_HEARTBEAT_MISSING`
  - `as_of=2026-06-24T13:15:00+00:00`
  - `heartbeat_status=MISSING`
  - `mailbox_ready=true`
  - `command_file_count=39`
  - `receipt_file_count=0`
  - `pending_command_receipt_count=39`
  - `event_journal_pending_receipt_count=28`
  - `history_file_count=0`
  - `account_snapshot_present=false`
  - `live_trading_flag_visible=false`
  - `alert_count=5`
- Refreshed information-flow report:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624115151-report.json`
  - historical next file: `cas_forex/mt4_terminal_activation.py`
  - superseded by the MT4 terminal activation implementation above:
    `must_have_next_file=cas_forex/mt4_ping_roundtrip.py`
  - `cas_forex/terminal_bridge_supervisor.py` status is `COMPLETE_INITIAL`
- Important operational fact:
  - The supervisor proves the mailbox folders exist and contain command files,
    but the real terminal is not yet awake from CAS Forex's point of view:
    `heartbeat.json` is missing, receipt files are still `0`, closed-history
    exports are `0`, and no receipt account snapshot is present. The real
    operational move remains MT4 terminal activation: discover/stage the MT4
    terminal data folder, copy/verify `CASForexBridgeEA.mq4` under
    `MQL4\Experts`, attach it inside MT4, point `MailboxRoot` at the shared
    mailbox, then rerun the watcher/supervisor chain.
- Verification:

```text
python -m pytest tests/test_terminal_bridge_supervisor.py -q
# 4 passed

python -m pytest tests/test_terminal_bridge_supervisor.py tests/test_agent_information_flow.py -q
# 9 passed

python -m pytest tests -q
# 434 passed

cd ui && npm run build
# 51 modules, 456.43 KB JS, 115.59 KB gzip
```

- Fresh local smoke:
  - API health: `http://127.0.0.1:8807/api/forex/health`
  - terminal bridge supervisor API:
    `http://127.0.0.1:8807/api/forex/strategy/terminal-bridge-supervisor/latest`
  - dashboard API: `http://127.0.0.1:8807/api/forex/dashboard`
  - UI preview: `http://127.0.0.1:5218/?page=optimizer`
  - browser render check: Optimizer page shows `Bridge Supervisor`,
    `TERMINAL_BRIDGE_HEARTBEAT_MISSING`,
    `cas_forex/mt4_terminal_activation.py`, and the
    `Attach and run CASForexBridgeEA.mq4` next action with zero console errors
- Startup note:
  - Run the local API with `py -3.12` and `PYTHONPATH=.pydeps-win312;.` on
    this machine. The default `python` is Python 3.14, but `.pydeps-win312`
    contains Python 3.12 native wheels.
- Completed by latest update:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\mt4_terminal_activation.py`
    now exists and stages/discovers MT4 activation.
- Current active next implementation target:
  - build `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\mt4_ping_roundtrip.py`
    after a real MT4 data folder exists, so CAS Forex can prove heartbeat,
    receipt, and close-history evidence against the attached terminal.

- Previous update: Terminal receipt watcher is now implemented and surfaced.
- This completes the concrete source-code step after the session autowake
  runner: CAS Forex can now watch MT4/MT5 receipt/history folders, detect
  changed terminal files, and rerun the existing ingest, memory, queue, patch,
  rollup, and autowake evidence chain when those files appear.
- New code/files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\terminal_receipt_watcher.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_terminal_receipt_watcher.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_terminal_receipt_watcher.py`
- Updated API/UI/roadmap files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\data.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\strategy.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_information_flow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\types\evidence.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\api.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\App.tsx`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\OptimizerPage.tsx`
- Current terminal watcher evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\terminal_receipt_watcher\terminal-receipt-watcher-20260624113653-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\terminal_receipt_watcher\terminal-receipt-watcher-20260624113653-report.md`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\terminal_receipt_watcher\terminal-receipt-watcher-20260624113653.jsonl`
- Terminal watcher summary:
  - `watch_status=WATCHER_IDLE_NO_TERMINAL_FILES`
  - `as_of=2026-06-24T13:10:00+00:00`
  - `terminal_file_count=0`
  - `receipt_file_count=0`
  - `history_file_count=0`
  - `changed_file_count=0`
  - `chain_step_count=0`
  - `chain_step_complete_count=0`
  - `chain_step_failed_count=0`
- Refreshed information-flow report:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624113652-report.json`
  - historical next file: `cas_forex/terminal_bridge_supervisor.py`
  - superseded by the terminal bridge supervisor implementation above:
    `must_have_next_file=cas_forex/mt4_terminal_activation.py`
  - `cas_forex/terminal_receipt_watcher.py` status is `COMPLETE_INITIAL`
- Important operational fact:
  - The watcher is ready, but the real terminal has not produced receipt JSON
    or closed-history exports in the watched folders. The real operational
    move remains MT4 terminal work: compile/attach/run `CASForexBridgeEA.mq4`
    against the shared mailbox, then export or ingest closed account history
    and rerun the watcher.
- Verification:

```text
python -m pytest tests/test_terminal_receipt_watcher.py -q
# 3 passed

python -m pytest tests/test_terminal_receipt_watcher.py tests/test_agent_information_flow.py -q
# 8 passed

python -m pytest tests -q
# 430 passed

cd ui && npm run build
# 51 modules, 449.52 KB JS, 114.36 KB gzip
```

- Fresh local smoke:
  - API health: `http://127.0.0.1:8806/api/forex/health`
  - terminal watcher API:
    `http://127.0.0.1:8806/api/forex/strategy/terminal-receipt-watcher/latest`
  - dashboard API: `http://127.0.0.1:8806/api/forex/dashboard`
  - UI preview: `http://127.0.0.1:5217/?page=optimizer`
  - browser render check: Optimizer page shows `Terminal Watcher`,
    `WATCHER_IDLE_NO_TERMINAL_FILES`, `cas_forex/terminal_bridge_supervisor.py`,
    and the MT4/MT5 bridge next action with zero console errors
- Startup note:
  - Run the local API with `py -3.12` and `PYTHONPATH=.pydeps-win312;.` on
    this machine. The default `python` is Python 3.14, but `.pydeps-win312`
    contains Python 3.12 native wheels.
- Next implementation target:
  - superseded by the terminal bridge supervisor implementation above; current
    next target is `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\mt4_terminal_activation.py`
  - separately, compile/attach/run `CASForexBridgeEA.mq4` inside MT4 so
    terminal receipts and closed-history data can be produced for the `28`
    pending command rows

- Previous update: Session autowake runner is now implemented and surfaced.
- This completes the concrete source-code step after the daily learning
  rollup: CAS Forex can now evaluate market/session wake windows, determine
  due micro-scalp/hourly/preopen/rollup events, see terminal blockers, and
  optionally request one paper/demo agent workflow cycle when told to execute.
- New code/files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\session_autowake_runner.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_session_autowake_runner.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_session_autowake_runner.py`
- Updated API/UI/roadmap files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\data.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\strategy.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_information_flow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\types\evidence.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\api.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\App.tsx`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\OptimizerPage.tsx`
- Current session autowake evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\session_autowake_runner\session-autowake-20260624111809-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\session_autowake_runner\session-autowake-20260624111809-report.md`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\session_autowake_runner\session-autowake-20260624111809.jsonl`
- Session autowake summary:
  - `autowake_status=SESSION_AUTOWAKE_READY`
  - `as_of=2026-06-24T13:00:00+00:00`
  - `market_open=true`
  - `active_session=LONDON_NEW_YORK_OVERLAP`
  - `event_count=7`
  - `due_event_count=2`
  - `executable_event_count=2`
  - `executed_cycle_count=0`
  - `pending_receipt_count=28`
  - `terminal_blocker_count=5`
  - `next_due_event_id=MICRO_SCALP_LOOP`
  - `daily_rollup_readiness_label=WAITING_FOR_TERMINAL_CLOSE_HISTORY`
- Refreshed information-flow report:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624111808-report.json`
  - historical next file: `cas_forex/terminal_receipt_watcher.py`
  - superseded by the terminal watcher implementation above:
    historical next file became `cas_forex/terminal_bridge_supervisor.py`;
    current next file is `cas_forex/mt4_terminal_activation.py`
  - `cas_forex/session_autowake_runner.py` status is `COMPLETE_INITIAL`
- Important operational fact:
  - Session autowake can wake/evaluate the CAS Forex agent cadence and can
    optionally request one paper/demo workflow cycle. It is not a substitute
    for the terminal producing receipt JSON and closed-history rows. The real
    operational move remains MT4 terminal work: compile/attach/run
    `CASForexBridgeEA.mq4` against the shared mailbox, then export or ingest
    closed account history and rerun the full chain.
- Verification:

```text
python -m pytest tests/test_session_autowake_runner.py -q
# 4 passed

python -m pytest tests -q
# 427 passed

cd ui && npm run build
# 51 modules, 443.73 KB JS, 113.27 KB gzip
```

- Fresh local smoke:
  - API health: `http://127.0.0.1:8805/api/forex/health`
  - session autowake API:
    `http://127.0.0.1:8805/api/forex/strategy/session-autowake/latest`
  - dashboard API: `http://127.0.0.1:8805/api/forex/dashboard`
  - UI preview: `http://127.0.0.1:5216/?page=optimizer`
  - browser render check: Optimizer page shows `Session Autowake`,
    `SESSION_AUTOWAKE_READY`, `LONDON_NEW_YORK_OVERLAP`, and
    `cas_forex/terminal_receipt_watcher.py` with zero console errors
- Startup note:
  - Run the local API with `py -3.12` and `PYTHONPATH=.pydeps-win312;.` on
    this machine. The default `python` is Python 3.14, but `.pydeps-win312`
    contains Python 3.12 native wheels.
- Next implementation target:
  - superseded by the terminal watcher implementation above; current next
    target is `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\terminal_bridge_supervisor.py`
  - separately, compile/attach/run `CASForexBridgeEA.mq4` inside MT4 so
    terminal receipts and closed-history data can be produced for the `28`
    pending command rows

- Previous update: Daily learning rollup is now implemented and surfaced.
- This completes the concrete source-code step after the strategy patch
  runner: CAS Forex can now turn the day into a 30-day improvement record by
  agent, symbol, strategy, condition, PnL, queued follow-up work, and terminal
  blockers.
- New code/files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\daily_learning_rollup.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_daily_learning_rollup.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_daily_learning_rollup.py`
- Updated API/UI/roadmap files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\data.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\strategy.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_information_flow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\types\evidence.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\api.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\App.tsx`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\OptimizerPage.tsx`
- Current daily rollup evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\daily_learning_rollup\daily-learning-rollup-20260624110228-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\daily_learning_rollup\daily-learning-rollup-20260624110228-report.md`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\daily_learning_rollup\daily-learning-rollup-20260624110228.jsonl`
- Daily rollup summary:
  - `rollup_status=DAILY_LEARNING_ROLLUP_BUILT_WAITING_FOR_CLOSED_PNL`
  - `trading_date=2026-06-24`
  - `day_index=1`
  - `window_days=30`
  - `route_count=62`
  - `approved_count=28`
  - `rejected_count=34`
  - `executed_count=28`
  - `pending_receipt_count=28`
  - `closed_count=0`
  - `net_profit_loss_account=0`
  - `patch_decision_count=6`
  - `patch_candidate_count=1`
  - `replay_job_count=3`
  - `readiness_label=WAITING_FOR_TERMINAL_CLOSE_HISTORY`
- Refreshed information-flow report:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624110229-report.json`
  - historical next file: `cas_forex/session_autowake_runner.py`
  - superseded by the session autowake implementation above:
    historical next file became `cas_forex/terminal_receipt_watcher.py`;
    current next file is `cas_forex/terminal_bridge_supervisor.py`
  - `cas_forex/daily_learning_rollup.py` status is `COMPLETE_INITIAL`
- Important operational fact:
  - The rollup shows the daily learning chain is wired, but closed-trade PnL is
    still zero because the terminal has not generated receipt JSON or
    closed-history rows. The real operational move remains MT4 terminal work:
    compile/attach/run `CASForexBridgeEA.mq4` against the shared mailbox, then
    export or ingest closed account history and rerun the full chain.
- Verification:

```text
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

- Fresh local smoke:
  - API health: `http://127.0.0.1:8804/api/forex/health`
  - daily learning rollup API:
    `http://127.0.0.1:8804/api/forex/strategy/daily-learning-rollup/latest`
  - dashboard API: `http://127.0.0.1:8804/api/forex/dashboard`
  - UI preview: `http://127.0.0.1:5215/?page=optimizer`
- Next implementation target:
  - superseded by the session autowake implementation above; current next
    target is `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\terminal_receipt_watcher.py`
  - separately, compile/attach/run `CASForexBridgeEA.mq4` inside MT4 so
    terminal receipts and closed-history data can be produced for the `28`
    pending command rows

- Previous update: strategy patch runner is now implemented and surfaced.
- Strategy patch runner is now implemented and surfaced.
- This completes the concrete source-code step after the strategy-development
  queue: CAS Forex can now turn strategy-dev work items into patch candidates,
  replay jobs, promotion/demotion reviews, and terminal-input blockers.
- New code/files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\strategy_patch_runner.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_strategy_patch_runner.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_strategy_patch_runner.py`
- Updated API/UI/roadmap files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\data.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\strategy.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_information_flow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\types\evidence.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\api.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\App.tsx`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\OptimizerPage.tsx`
- Current patch-runner evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\strategy_patch_runner\strategy-patch-runner-20260624104622-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\strategy_patch_runner\strategy-patch-runner-20260624104622-report.md`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\strategy_patch_runner\strategy-patch-runner-20260624104622.jsonl`
- Strategy patch-runner summary:
  - `runner_status=STRATEGY_PATCH_RUNNER_READY`
  - `decision_count=6`
  - `ready_decision_count=3`
  - `blocked_decision_count=3`
  - `patch_candidate_count=1`
  - `replay_job_count=3`
  - `promotion_review_count=0`
  - `demotion_review_count=0`
  - `terminal_input_required_count=2`
  - `next_decision_id=strategy-patch-terminal_joinback_blocker-b734b40a97a7028d`
- Refreshed information-flow report:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624104623-report.json`
  - historical next file: `cas_forex/daily_learning_rollup.py`
  - superseded by the daily-rollup implementation above:
    historical next file became `cas_forex/session_autowake_runner.py`;
    current next file is `cas_forex/terminal_receipt_watcher.py`
  - `cas_forex/strategy_patch_runner.py` status is `COMPLETE_INITIAL`
- Important operational fact:
  - The patch runner organizes concrete patch/replay decisions; it does not
    silently edit live strategy code or execute terminal orders. The real
    operational move remains MT4 terminal work: compile/attach/run
    `CASForexBridgeEA.mq4` against the shared mailbox, then export or ingest
    closed account history and rerun the ingest/memory/queue/patch chain.
- Verification:

```text
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

- Fresh local smoke:
  - API health: `http://127.0.0.1:8803/api/forex/health`
  - strategy patch-runner API:
    `http://127.0.0.1:8803/api/forex/strategy/strategy-patch-runner/latest`
  - dashboard API: `http://127.0.0.1:8803/api/forex/dashboard`
  - UI preview: `http://127.0.0.1:5214/?page=optimizer`
- Next implementation target:
  - build `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\daily_learning_rollup.py`
    so each trading day becomes a 30-day improvement record by agent, symbol,
    strategy, condition, PnL, and queued follow-up work
  - separately, compile/attach/run `CASForexBridgeEA.mq4` inside MT4 so
    terminal receipts and closed-history data can be produced for the `28`
    pending command rows

- Previous update: strategy-development queue is now implemented and surfaced.
- Strategy-development queue is now implemented and surfaced.
- This completes the concrete source-code step after terminal close/history
  ingest: CAS Forex can now turn research tasks and future closed-trade memory
  rows into specific strategy-development work items.
- New code/files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\strategy_dev_queue.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_strategy_dev_queue.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_strategy_dev_queue.py`
- Updated API/UI/roadmap files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\data.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\strategy.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_information_flow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\types\evidence.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\api.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\App.tsx`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\OptimizerPage.tsx`
- Current strategy-dev evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\strategy_dev_queue\strategy-dev-queue-20260624102900-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\strategy_dev_queue\strategy-dev-queue-20260624102900-report.md`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\strategy_dev_queue\strategy-dev-queue-20260624102900.jsonl`
- Strategy-dev summary:
  - `queue_status=STRATEGY_DEV_QUEUE_BUILT`
  - `item_count=6`
  - `queued_item_count=3`
  - `blocked_item_count=3`
  - `ready_for_replay_count=3`
  - `patch_candidate_count=1`
  - `promotion_review_count=0`
  - `demotion_review_count=0`
  - `terminal_blocked_count=3`
  - `next_item_id=strategy-dev-terminal-joinback-7c441e3221a2bdce`
- Refreshed information-flow report:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624102906-report.json`
  - historical next file: `cas_forex/strategy_patch_runner.py`
  - superseded by the patch-runner and daily-rollup implementations above:
    historical next file became `cas_forex/session_autowake_runner.py`;
    current next file is `cas_forex/terminal_receipt_watcher.py`
  - `cas_forex/strategy_dev_queue.py` status is `COMPLETE_INITIAL`
- Important operational fact:
  - The queue now organizes concrete patch/replay/promotion/demotion work, but
    the terminal still has not generated receipt JSON or closed-history rows.
    The real operational move remains MT4 terminal work: compile/attach/run
    `CASForexBridgeEA.mq4` against the shared mailbox, then export or ingest
    closed account history and rerun the ingest/memory/queue chain.
- Verification:

```text
python -m pytest tests/test_strategy_dev_queue.py tests/test_agent_information_flow.py -q
# 8 passed

python -m pytest tests/test_strategy_dev_queue.py tests/test_agent_research_queue.py tests/test_agent_memory.py tests/test_terminal_history_ingest.py tests/test_agent_information_flow.py -q
# 14 passed

python -m pytest tests -q
# 417 passed

cd ui && npm run build
# 51 modules, 419.23 KB JS, 109.29 KB gzip
```

- Fresh local smoke:
  - API health: `http://127.0.0.1:8802/api/forex/health`
  - strategy-dev queue API:
    `http://127.0.0.1:8802/api/forex/strategy/strategy-dev-queue/latest`
  - dashboard API: `http://127.0.0.1:8802/api/forex/dashboard`
- Next implementation target:
  - build `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\strategy_patch_runner.py`
    so queued patch and replay requests can become candidate strategy edits,
    replay jobs, and scored promotion/demotion decisions
  - separately, compile/attach/run `CASForexBridgeEA.mq4` inside MT4 so
    terminal receipts and closed-history data can be produced for the `28`
    pending command rows

- Previous update: terminal close/history ingest is now implemented and surfaced.
- Terminal close/history ingest is now implemented and surfaced.
- This completes the concrete source-code step after the agent research queue:
  CAS Forex can now normalize MT4/MT5 close-history exports and join realized
  closed-trade outcome facts back into agent memory.
- New code/files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\terminal_history_ingest.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_terminal_history_ingest.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_terminal_history_ingest.py`
- Updated API/UI/roadmap files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\data.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\strategy.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_memory.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_information_flow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_agent_memory.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\types\evidence.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\api.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\App.tsx`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\OptimizerPage.tsx`
- Current terminal-history evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\terminal_history_ingest\terminal-history-ingest-20260624101300-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\terminal_history_ingest\terminal-history-ingest-20260624101300-report.md`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\terminal_history_ingest\terminal-history-ingest-20260624101300.jsonl`
- Terminal-history summary:
  - `ingest_status=TERMINAL_HISTORY_EMPTY`
  - `history_record_count=0`
  - `memory_update_count=0`
  - `closed_trade_count=0`
  - `net_profit_loss_account=0`
  - reason: no MT4/MT5 closed-history export is present yet under
    `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\terminal_history_exports`
- Current memory evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_memory\agent-memory-20260624101307-report.json`
  - `memory_record_count=62`
  - `pending_receipt_count=28`
  - `receipt_joined_count=0`
  - `terminal_history_joined_count=0`
- Current research queue evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_research_queue\agent-research-queue-20260624101315-report.json`
  - `task_count=6`
  - `high_priority_task_count=4`
  - `next_task_id=research-terminal-receipt-joinback-7f4619f0b837f4e4`
- Refreshed information-flow report:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624101117-report.json`
  - historical value: `must_have_next_file=cas_forex/strategy_dev_queue.py`
  - superseded by the strategy-dev, patch-runner, and daily-rollup
    implementations above: historical next file became
    `cas_forex/session_autowake_runner.py`; current next file is
    `cas_forex/terminal_receipt_watcher.py`
  - `cas_forex/terminal_history_ingest.py` status is
    `SOURCE_READY_NEEDS_HISTORY_EXPORT`
  - `cas_forex/agent_memory.py` status is
    `CLOSE_HISTORY_READY_NEEDS_EXPORT`
- Important operational fact:
  - The source code is ready for closed-history files, but the terminal has
    not yet exported or generated closed-history rows. The real operational
    move is still MT4 terminal work: compile/attach/run `CASForexBridgeEA.mq4`
    against the shared mailbox, then export or ingest closed account history.
- Verification:

```text
python -m pytest tests/test_terminal_history_ingest.py tests/test_agent_memory.py tests/test_agent_research_queue.py tests/test_agent_information_flow.py -q
# 11 passed

python -m pytest tests -q
# 414 passed

cd ui && npm run build
# 51 modules, 411.40 KB JS, 107.92 KB gzip
```

- Fresh local smoke:
  - API health: `http://127.0.0.1:8801/api/forex/health`
  - terminal history API:
    `http://127.0.0.1:8801/api/forex/strategy/terminal-history-ingest/latest`
  - dashboard API: `http://127.0.0.1:8801/api/forex/dashboard`
  - UI preview: `http://127.0.0.1:5212/?page=optimizer`
- Next implementation target:
  - build `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\strategy_dev_queue.py`
    so completed research tasks and future closed PnL memory rows can become
    patch candidates, replay requests, and promotion/demotion reviews
  - separately, compile/attach/run `CASForexBridgeEA.mq4` inside MT4 so
    terminal receipts and closed-history data can be produced for the `28`
    pending command rows

- Previous update: agent research queue is now implemented and surfaced.
- Agent research queue is now implemented and surfaced.
- This completes the next concrete source-code step after agent outcome
  memory: CAS Forex now turns memory rows into queued work for terminal
  receipt joinback, overseer conflict-key refinement, condition-lab rejection
  analysis, walk-forward receipt replay, and terminal history/PnL schema work.
- New code/files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_research_queue.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_agent_research_queue.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_agent_research_queue.py`
- Updated API/UI/roadmap files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\data.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\strategy.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_information_flow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\types\evidence.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\api.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\App.tsx`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\OptimizerPage.tsx`
- Current research queue evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_research_queue\agent-research-queue-20260624095304-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_research_queue\agent-research-queue-20260624095304-report.md`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_research_queue\agent-research-queue-20260624095304.jsonl`
- Queue summary:
  - `task_count=6`
  - `high_priority_task_count=4`
  - `terminal_receipt_task_count=1`
  - `condition_lab_task_count=2`
  - `walk_forward_task_count=1`
  - `strategy_dev_task_count=0`
  - `next_task_id=research-terminal-receipt-joinback-7f4619f0b837f4e4`
- Refreshed information-flow report:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624095004-report.json`
  - historical value: `must_have_next_file=cas_forex/terminal_history_ingest.py`
  - superseded by the terminal-history, strategy-dev, patch-runner, and
    daily-rollup implementations above:
    historical next file became `cas_forex/session_autowake_runner.py`;
    current next file is `cas_forex/terminal_receipt_watcher.py`
  - `cas_forex/agent_research_queue.py` status is `COMPLETE`
- Important operational fact:
  - The queue organizes work; it does not execute broker orders. The first
    queued task is terminal receipt joinback because `28` approved commands are
    still waiting for MT4 terminal receipts.
- Verification:

```text
python -m pytest tests/test_agent_research_queue.py tests/test_agent_memory.py tests/test_agent_information_flow.py -q
# 9 passed

python -m pytest tests -q
# 412 passed

cd ui && npm run build
# 51 modules, 407.19 KB JS, 107.15 KB gzip
```

- Fresh local smoke:
  - API health: `http://127.0.0.1:8800/api/forex/health`
  - research queue API:
    `http://127.0.0.1:8800/api/forex/strategy/agent-research-queue/latest`
  - dashboard API: `http://127.0.0.1:8800/api/forex/dashboard`
  - UI preview: `http://127.0.0.1:5211/?page=optimizer`
- Next implementation target:
  - superseded: `terminal_history_ingest.py` is now built; current next code
    target is `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\strategy_dev_queue.py`
  - separately, compile/attach/run `CASForexBridgeEA.mq4` inside MT4 so terminal receipts can be generated for the 28 pending command rows

- Previous update: agent outcome memory is now implemented and surfaced.
- This completes the next concrete source-code step after the MT4 EA
  receipt-writer source: CAS Forex now turns agent route/decision/command
  facts into durable learning rows and exposes them through API/dashboard/UI.
- New code/files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_memory.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_agent_memory.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_agent_memory.py`
- Updated API/UI files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\data.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\strategy.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\types\evidence.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\api.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\App.tsx`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\OptimizerPage.tsx`
- Current memory evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_memory\agent-memory-20260624093213-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_memory\agent-memory-20260624093213-report.md`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_memory\agent-memory-20260624093213.jsonl`
- Memory summary:
  - `memory_record_count=62`
  - `approved_count=28`
  - `rejected_count=34`
  - `command_joined_count=28`
  - `receipt_joined_count=0`
  - `pending_receipt_count=28`
  - `latest_cycle_id=agent-cycle-44848f2d3efc4669`
- Refreshed information-flow report:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624093253-report.json`
  - `must_have_next_file=cas_forex/agent_research_queue.py`
  - `cas_forex/agent_memory.py` status is `INITIAL_READY_NEEDS_CLOSE_DATA`
  - This has since been superseded by the research-queue, terminal-history,
    strategy-dev, patch-runner, and daily-rollup updates above:
    historical next file became `cas_forex/session_autowake_runner.py`;
    current next file is `cas_forex/terminal_receipt_watcher.py`
- Important operational fact:
  - The memory layer currently learns from proposal/approval/rejection/command
    facts and any available receipt facts. It does not yet have closed-trade
    PnL, MAE/MFE, or full lesson scoring because the actual MT4 terminal has
    not yet produced close/history data for these command rows.
- Verification:

```text
python -m pytest tests/test_agent_memory.py tests/test_terminal_receipt_ingest.py tests/test_mt4_mailbox_bridge.py tests/test_agent_information_flow.py -q
# 16 passed

python -m pytest tests -q
# 410 passed

cd ui && npm run build
# 51 modules, 398.13 KB JS, 105.33 KB gzip
```

- Fresh local smoke:
  - API health: `http://127.0.0.1:8799/api/forex/health`
  - agent memory API:
    `http://127.0.0.1:8799/api/forex/strategy/agent-memory/latest`
  - dashboard API: `http://127.0.0.1:8799/api/forex/dashboard`
  - UI preview: `http://127.0.0.1:5209/?page=optimizer`
- Next target from this older step has now advanced:
  - `cas_forex\agent_research_queue.py` exists and is surfaced
  - build `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\terminal_history_ingest.py` so terminal close/history data can fill real PnL fields
  - separately, compile/attach/run `CASForexBridgeEA.mq4` inside MT4 so terminal receipt and history data can join into memory

- Previous update: MT4 EA receipt-writer source is now implemented and surfaced.
- This completes the next concrete source-code step after receipt-aware overseer:
  the MQL4 EA source can read CAS command JSON from the MT4 mailbox and write
  terminal receipt JSON in the exact shape CAS Forex receipt ingest expects.
- Updated code/files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\mt4\Experts\CASForexBridgeEA.mq4`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\broker\mt4_mailbox_bridge.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_information_flow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_mt4_mailbox_bridge.py`
- EA behavior now implemented in source:
  - creates mailbox folders
  - writes heartbeat JSON
  - enumerates `<MailboxRoot>\commands\*.json`
  - parses `cas_forex_mt4_mailbox_command.v1`
  - skips commands that already have receipt files
  - acknowledges `PING`
  - acknowledges `PAPER_MT4` `PLACE_ORDER` commands by writing `cas_forex_mt4_mailbox_receipt.v1`
  - includes `raw_request_hash`, `raw_response_hash`, terminal identity, account snapshot, fill fields, slippage, ticket, and error fields
  - keeps `LIVE_MT4` behind both the EA `LiveTradingAllowed` input and the command `live_money_authorized` flag
- Information-flow state at that MT4 source-ready step:
  - latest information-flow report:
    `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624091707-report.json`
  - `mt4/Experts/CASForexBridgeEA.mq4` status: `SOURCE_READY_NEEDS_TERMINAL_VERIFY`
  - `must_have_next_file=cas_forex/agent_memory.py`
  - This has since been superseded by the memory update above:
    `must_have_next_file=cas_forex/agent_research_queue.py`
  - latest MT4 mailbox smoke status:
    `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\mt4_mailbox_smoke\mt4-mailbox-smoke-status.json`
- Important operational fact:
  - The EA source is implemented and contract-tested, but not yet compiled/attached/run inside a real MT4 terminal in this session. The next terminal-side action is to install/compile the EA in MT4, point `MailboxRoot` at the shared mailbox, then run receipt ingest after receipt files appear.
- Verification:

```text
python -m pytest tests/test_mt4_mailbox_bridge.py tests/test_terminal_receipt_ingest.py tests/test_agent_information_flow.py -q
# 14 passed

python -m pytest tests -q
# 408 passed

cd ui && npm run build
# 51 modules, 394.10 KB JS, 104.63 KB gzip
```

- Next target from this older step has now advanced:
  - `cas_forex\agent_memory.py` exists as an initial route/receipt memory layer
  - build `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_research_queue.py` so memory patterns become condition-lab/walk-forward tasks
  - separately, perform the MT4 terminal compile/attach/run verification for `CASForexBridgeEA.mq4`

- Previous update: receipt-aware overseer routing is implemented and surfaced.
- This completes the next concrete build step after terminal receipt ingest:
  CAS Forex now refuses to write more same-symbol MT4 command files while
  earlier commands are still waiting for terminal receipts/reconciliation.
- Updated backend/code files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_overseer.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_state.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_message_bus.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_information_flow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
- Added/updated tests:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_agent_overseer.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_terminal_receipt_ingest.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_agent_message_bus.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_agent_workflow_cycle.py`
  - important: API-surface tests now use temp evidence/route monkeypatches and should not write throwaway `MANUAL_CLI` cycles into real `evidence_runs`
- Behavior now proven:
  - a pending same-symbol terminal command rejects new same-symbol route intents as `QUEUED_AWAITING_RECEIPT`
  - a valid verified/reconciled receipt with `NEXT_CYCLE_ALLOWED` lets the same symbol route again
  - a receipt mismatch locks the affected symbol as `TERMINAL_LOCKED_FOR_SYMBOL`
  - the default live project event journal now blocks duplicate AUD/CAD command spam while `28` receipts are pending
- Current event/receipt state:
  - agent event log:
    `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_workflow_queue\agent-events.jsonl`
  - `event_count=459`
  - `cycle_count=31`
  - `latest_cycle_id=agent-cycle-44848f2d3efc4669`
  - `terminal_command_count=28`
  - `pending_receipt_count=28`
  - latest cycle approved intent count: `0`
  - latest cycle rejected intent count: `2`
  - latest cycle terminal command count: `0`
  - latest workflow cycle report:
    `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_workflow_queue\agent-workflow-cycle-20260624090733-report.json`
  - latest terminal receipt ingest report:
    `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\terminal_receipt_ingest\terminal-receipt-ingest-20260624090739-report.json`
  - latest information-flow report:
    `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624085546-report.json`
- Important operational fact:
  - This receipt-aware update has since been followed by the MT4 EA source-ready update above.
  - `.pydeps` currently contains WSL/Linux binary wheels. On Windows, use
    `.pydeps-win312` with Python 3.12 for the FastAPI server:
    `set PYTHONPATH=.pydeps-win312;.` or
    `$env:PYTHONPATH='.pydeps-win312;.'`, then
    `py -3.12 -m uvicorn api.server:app --host 127.0.0.1 --port 8797`.
- Verification:

```text
python -m pytest tests/test_agent_overseer.py tests/test_terminal_receipt_ingest.py tests/test_agent_workflow_cycle.py tests/test_agent_message_bus.py -q
# 14 passed

python -m pytest tests -q
# 407 passed

cd ui && npm run build
# 51 modules, 393.97 KB JS, 104.58 KB gzip

py -3.12 -c "import sys; sys.path.insert(0, r'.pydeps-win312'); import pydantic_core, fastapi, uvicorn; print('windows_api_deps_ok', pydantic_core.__version__)"
# windows_api_deps_ok 2.46.4
```

- Next implementation target:
  - build `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_memory.py` for real win/loss outcome memory
  - then build `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_research_queue.py` so memory patterns become condition-lab/walk-forward tasks

- Previous update: terminal receipt ingest joinback is implemented and surfaced.
- This completes the next concrete build step after the agent event journal:
  CAS Forex can now read MT4/MT5 receipt JSON from the mailbox, validate it
  against command events, append receipt lifecycle events, and expose the
  result in the API/UI.
- New backend/code files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\terminal_receipt_ingest.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_terminal_receipt_ingest.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_terminal_receipt_ingest.py`
- Updated backend/API/UI files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_message_bus.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_information_flow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\data.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\strategy.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\types\evidence.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\api.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\App.tsx`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\OptimizerPage.tsx`
- New API endpoint:
  - `/api/forex/strategy/terminal-receipt-ingest/latest`
- Dashboard/UI:
  - `/api/forex/dashboard` now includes `terminalReceiptIngest`
  - Optimizer page shows receipt files, new ingested receipts, verified count,
    reconciled count, mismatches, pending count, mailbox path, and receipt rows
- Current event/receipt state:
  - agent event log:
    `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_workflow_queue\agent-events.jsonl`
  - `event_count=270`
  - `cycle_count=18`
  - `latest_cycle_id=agent-cycle-5885cba41e8f5a38`
  - `terminal_command_count=18`
  - `pending_receipt_count=18`
  - `verified_receipt_count=0`
  - `reconciled_receipt_count=0`
  - `next_cycle_allowed_count=0`
  - latest terminal receipt ingest report:
    `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\terminal_receipt_ingest\terminal-receipt-ingest-20260624083745-report.json`
  - latest information-flow report:
    `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624083721-report.json`
- Important operational fact:
  - No actual MT4/MT5 terminal receipt files are present in the default mailbox yet, so the default ingest report appended `0` receipt events. The ingest software path is ready; the EA/terminal still has to write receipt JSON files into `evidence_runs\agent_workflow_mt4_mailbox\receipts`.
- Verification:

```text
python -m pytest tests -q
# 403 passed

python -m pytest tests/test_agent_information_flow.py tests/test_terminal_receipt_ingest.py tests/test_agent_message_bus.py -q
# 11 passed

cd ui && npm run build
# 51 modules, 393.21 KB JS, 104.34 KB gzip
```

- Next implementation target:
  - extend `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_overseer.py` so same-symbol routes consume `NEXT_CYCLE_ALLOWED` / `TERMINAL_LOCKED_FOR_SYMBOL` from the event journal instead of only same-cycle in-memory conflict
  - connect/finish the MT4 EA side so it writes real receipt JSON into `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_workflow_mt4_mailbox\receipts`
  - then build `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_memory.py` for real win/loss outcome memory

- Previous update: Agent message bus event journal is now implemented and surfaced.
- This completes the first concrete build step after the three-agent
  information-flow review: CAS Forex now has a real append-only event journal,
  not just a blueprint.
- New backend/code files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_message_bus.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_agent_message_bus.py`
- Updated backend/API/UI files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_state.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\data.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\strategy.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\types\evidence.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\api.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\App.tsx`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\OptimizerPage.tsx`
- New API endpoints:
  - `/api/forex/strategy/agent-workflow-events/summary`
  - `/api/forex/strategy/agent-workflow-events`
  - `/api/forex/strategy/agent-workflow-context/latest`
  - `/api/forex/strategy/agent-workflow-intents/open`
  - `/api/forex/strategy/agent-workflow-receipts/latest`
- Dashboard/UI:
  - `/api/forex/dashboard` now includes `agentMessageBus`
  - Optimizer page shows event-journal counts, cycle count, pending receipt count, latest cycle/event, event type counts, and status counts
- Current event journal:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_workflow_queue\agent-events.jsonl`
  - current counts are superseded by the terminal receipt ingest update above
  - latest cycle report:
    superseded by the terminal receipt ingest update above
- Live local smoke:
  - API health: `http://127.0.0.1:8790/api/forex/health`
  - Event summary: `http://127.0.0.1:8790/api/forex/strategy/agent-workflow-events/summary`
  - Dashboard: `http://127.0.0.1:8790/api/forex/dashboard`
  - UI: `http://127.0.0.1:5200/?page=optimizer`
- Verification:

```text
python -m pytest tests/test_agent_message_bus.py tests/test_agent_workflow_cycle.py tests/test_agent_information_flow.py tests/test_settings_api_surface.py -q
# 23 passed

python -m pytest tests -q
# 400 passed

cd ui && npm run build
# 51 modules, 389.02 KB JS, 103.45 KB gzip
```

- Terminal receipt ingest is complete; the next implementation target is
  overseer consumption of receipt lifecycle events, then full win/loss outcome
  memory.

- Agent information-flow team review is now implemented and surfaced in the
  Optimizer UI/dashboard API.
- Three specialist agents reviewed the inter-agent information architecture:
  `Sagan` for coordination channels, `Mill` for execution/receipt lifecycle,
  and `Leibniz` for research-memory learning loop.
- The selected architecture is:
  - append-only event journal as the agent desk log
  - evidence artifacts as durable binders
  - API/dashboard as read-only projections
  - MT4/MT5 mailbox files only as terminal command outbox and receipt inbox
  - outcome memory as the learning source for future route decisions
- New backend/code files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_information_flow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_agent_information_flow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_agent_information_flow.py`
- New/updated API/UI surface:
  - `/api/forex/strategy/agent-information-flow`
  - `/api/forex/dashboard` now includes `agentInformationFlow`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\data.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\strategy.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\types\evidence.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\api.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\App.tsx`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\OptimizerPage.tsx`
- Generated evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624083721-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624083721-report.md`
- Current flow summary:
  - `flow_status=FLOW_BLUEPRINT_READY`
  - `best_flow_form=append-only event journal plus read-only API projections`
  - `specialist_agent_count=3`
  - `canonical_packet_count=7`
  - `flow_stage_count=8`
  - `lifecycle_state_count=10`
  - next file: `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_overseer.py`
- Required next implementation sequence:
  - `cas_forex\agent_message_bus.py` is complete
  - `cas_forex\terminal_receipt_ingest.py` is complete
  - create `cas_forex\agent_context.py`
  - extend `cas_forex\agent_overseer.py` so duplicate same-symbol open routes wait for `NEXT_CYCLE_ALLOWED` and lock on `TERMINAL_LOCKED_FOR_SYMBOL`
  - create `cas_forex\agent_memory.py` for true win/loss outcome memory with open/close condition snapshots
  - create `cas_forex\agent_research_queue.py`
- Live local smoke from this information-flow pass:
  - API health: `http://127.0.0.1:8786/api/forex/health`
  - Information-flow API: `http://127.0.0.1:8786/api/forex/strategy/agent-information-flow`
  - Dashboard: `http://127.0.0.1:8786/api/forex/dashboard`
  - UI: `http://127.0.0.1:5196/?page=optimizer`
- Verification from this information-flow pass:

```text
python -m pytest tests/test_agent_information_flow.py tests/test_agent_workflow_cycle.py tests/test_agent_workflow.py -q
# 12 passed

python -m pytest tests -q
# 397 passed

cd ui && npm run build
# 51 modules, 386.47 KB JS, 102.97 KB gzip
```

- Agent workflow execution-cycle scaffold is also now implemented.
- New backend/code files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_state.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\micro_scalp_policy.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\hourly_intraday_policy.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_overseer.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_agent_workflow_queue.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_agent_workflow_cycle.py`
- New/updated API/UI surface:
  - `/api/forex/strategy/agent-workflow-cycle/latest`
  - `/api/forex/dashboard` now includes `agentWorkflowCycle`
  - Optimizer page latest-cycle readout
- Latest cycle evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_workflow_queue\agent-workflow-cycle-20260624050225-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_workflow_queue\agent-workflow-cycle-20260624050225-report.md`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_workflow_queue\agent-workflow-state.jsonl`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_workflow_mt4_mailbox\commands`
- Latest cycle summary:
  - `execution_mode=PAPER_MT4_COMMAND_INTENT`
  - `agent_heartbeat_count=6`
  - `route_intent_count=2`
  - `approved_intent_count=1`
  - `rejected_intent_count=1`
  - `terminal_command_count=1`
  - `memory_snapshot_count=2`
  - symbols/timeframes: `AUD/CAD`, `M5`, `H1`
- Boundary: these workflow and information-flow artifacts build the owner
  agent desk and terminal-command evidence path. They do not by themselves
  execute live broker orders, create broker `ACCEPT`, deposit, withdraw, move
  bank/card funds, or automate payouts.

- Agentic trading-day workflow plan is now implemented and surfaced in the
  Optimizer UI/dashboard API.
- This encodes the owner-requested structure: CAS Forex should autowake when
  forex trading begins, run a micro-scalping agent for small accumulated
  profits, run a separate hourly intraday agent, have both overseen by an
  overseer agent, and keep research/strategy agents mining better conditions
  and shorter-timeframe profit routes during the 30-day window.
- New backend/code files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_workflow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_agent_workflow_plan.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_agent_workflow.py`
- New/updated API/UI surface:
  - `/api/forex/strategy/agent-workflow-plan`
  - `/api/forex/dashboard` now includes `agentWorkflowPlan`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\data.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\strategy.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\types\evidence.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\api.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\App.tsx`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\OptimizerPage.tsx`
- Generated evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_workflow\agent-workflow-plan-20260624044500-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_workflow\agent-workflow-plan-20260624044500-report.md`
- Current workflow summary:
  - `workflow_status=AGENT_DESK_PLAN_READY`
  - `agent_count=8`
  - agents: `session_autowake_agent`, `micro_scalp_agent`,
    `hourly_intraday_agent`, `overseer_agent`, `research_condition_agent`,
    `strategy_dev_agent`, `terminal_bridge_agent`, `audit_memory_agent`
  - micro-scalp cadence: `1-5` minutes while a session is approved
  - hourly intraday cadence: `60` minutes
  - primary short-timeframe lead: `AUD/CAD M5 range_scalper_12_80`
  - primary replay verdict: `REPLAY_LEAD_FOR_ADAPTIVE_REVIEW`
  - adaptive next step: `QUEUE_FOR_ADAPTIVE_COMPOUNDING_REVIEW`
- Live local smoke from this workflow pass:
  - API health: `http://127.0.0.1:8782/api/forex/health`
  - Workflow API: `http://127.0.0.1:8782/api/forex/strategy/agent-workflow-plan`
  - Dashboard: `http://127.0.0.1:8782/api/forex/dashboard`
  - UI: `http://127.0.0.1:5192/?page=optimizer`
- Verification from this workflow pass:

```text
python -m pytest tests/test_agent_workflow.py tests/test_forex_fury_replay_results.py -q
# 5 passed

python -m pytest tests -q
# 388 passed

cd ui && npm run build
# 51 modules, 364.08 KB JS, 97.89 KB gzip
```

- Remaining next implementation lane: build
  `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_state.py`,
  `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_agent_workflow_queue.py`,
  `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\micro_scalp_policy.py`,
  `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\hourly_intraday_policy.py`,
  and `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_overseer.py`,
  then attach approved route packets to MT4/MT5 paper/demo receipts.
- Boundary: the workflow plan coordinates autowake, scalp, intraday, overseer,
  research, terminal-bridge, and memory agents. It creates schedules, route
  intents, research tasks, and evidence requirements; it does not by itself
  execute live broker orders, create broker `ACCEPT`, deposit, withdraw, move
  bank/card funds, or automate payouts.

- Forex Fury replay-candidate queue is now implemented and surfaced in the
  Optimizer UI/dashboard API.
- New backend/code files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\forex_fury_candidates.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_forex_fury_replay_candidates.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_forex_fury_candidates.py`
- Expanded instrument support:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\instruments.py`
  - Added `AUD/CAD`, `GBP/AUD`, and `SPX500` so all top imported Forex Fury
    replay candidates can run through CAS instrument mapping.
- New/updated API surface:
  - `/api/forex/strategy/forex-fury-replay-candidates`
  - `/api/forex/dashboard` now includes `forexFuryReplayCandidates`
- Updated UI/API files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\data.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\strategy.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\types\evidence.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\api.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\App.tsx`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\OptimizerPage.tsx`
- Generated evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\forex_fury_replay_candidates\forex-fury-replay-candidates-20260624040820-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\forex_fury_replay_candidates\forex-fury-replay-candidates-20260624040820-report.md`
- Replay queue summary:
  - `candidate_count=24`
  - `supported_candidate_count=24`
  - `waiting_for_instrument_spec_count=0`
  - symbols: `AUD/CAD`, `AUD/USD`, `GBP/AUD`, `GBP/USD`, `SPX500`, `USD/JPY`
  - timeframes: `H1`, `M1`, `M5`
  - top candidate: `ff-replay-aud-cad-m5-swing-d7be2c38ca`
  - top score: `320.9726`
- Live local smoke from this replay-candidate pass:
  - API: `http://127.0.0.1:8776/api/forex/strategy/forex-fury-replay-candidates`
  - Dashboard: `http://127.0.0.1:8776/api/forex/dashboard`
  - UI: `http://127.0.0.1:5186/?page=optimizer`
- Browser verification confirmed the Optimizer page renders:
  - `Forex Fury Replay Candidates`
  - `AUD/CAD`
  - `READY_FOR_CAS_REPLAY`
  - generated `run_condition_lab.py` command
- Verification from this replay-candidate pass:

```text
python -m pytest tests/test_forex_fury_candidates.py tests/test_forex_fury_sets.py tests/test_external_benchmark.py tests/test_pip_math_regressions.py -q
# 18 passed

python -m pytest tests -q
# 383 passed

cd ui && npm run build
# 51 modules, 341.36 KB JS, 91.97 KB gzip
```

- Boundary: replay candidates are CAS research/backtest queue inputs. They do
  not execute EA binaries, place orders, create broker `ACCEPT`, deposit,
  withdraw, move bank/card money, or automate payouts.
- Remaining next implementation lane: run the generated `run_condition_lab.py`
  and `run_walk_forward_condition_lab.py` commands for the top candidates, save
  the replay outputs under `evidence_runs\forex_fury_condition_replay` and
  `evidence_runs\forex_fury_walk_forward_replay`, then wire those results into
  adaptive compounding policy and MT4 paper/demo receipt evidence.

- Local Forex Fury package import is now surfaced in the Optimizer UI and
  dashboard API.
- Updated API/UI files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\data.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\types\evidence.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\api.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\App.tsx`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\OptimizerPage.tsx`
- New/updated API surface:
  - `/api/forex/strategy/forex-fury-set-import`
  - `/api/forex/dashboard` now includes `forexFurySetImport`
- Optimizer page now shows a Local Forex Fury Set Import panel with imported
  set/report counts, MT4/MT5 counts, best profit factor, lowest drawdown, max
  orders, grid/money-close counts, top tester-report profiles, and improvement
  targets.
- Live local smoke from this UI surfacing pass:
  - API: `http://127.0.0.1:8774/api/forex/strategy/forex-fury-set-import`
  - Dashboard: `http://127.0.0.1:8774/api/forex/dashboard`
  - UI: `http://127.0.0.1:5184/?page=optimizer`
- Verified live payload:
  - `set_count=36`
  - `tester_report_count=30`
  - `best_profit_factor=15.12`
  - `best_symbol=AUDCAD`
  - `best_timeframe=M5`
- Verification from this UI surfacing pass:

```text
python -m pytest tests/test_forex_fury_sets.py tests/test_external_benchmark.py -q
# 4 passed

python -m pytest tests -q
# 379 passed

cd ui && npm run build
# 51 modules, 333.31 KB JS, 90.09 KB gzip
```

- Boundary: the Optimizer panel is comparison, mining, and owner-cockpit
  intelligence only. It does not execute EA binaries, place orders, create
  broker `ACCEPT`, deposit, withdraw, move bank/card money, or automate
  payouts.
- Previous next implementation lane to feed imported Forex Fury windows,
  symbols, timeframes, max-order settings, grid settings, and close-by-money
  settings into CAS replay candidates is now complete. The remaining lane is
  to run those generated replay jobs, then route winners into compounding
  policy and the MT4 paper/demo receipt path.

- Local Forex Fury package import is now implemented.
- Source inspected:
  - `C:\Users\wakil\Downloads\Forex-Fury-CORE-1.4NEW-SETS (1)`
- New backend/code files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\forex_fury_sets.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_forex_fury_set_import.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_forex_fury_sets.py`
- New API surface:
  - `/api/forex/strategy/forex-fury-set-import`
- Generated evidence:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\forex_fury_set_import\forex-fury-set-import-20260624034719-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\forex_fury_set_import\forex-fury-set-import-20260624034719-report.md`
- Real package summary:
  - `set_count=36`
  - `tester_report_count=30`
  - `platform_counts={MT4: 18, MT5: 18}`
  - `family_counts={classic_m15: 6, scalping: 14, swing: 16}`
  - `symbol_counts={AUDCAD: 8, AUDUSD: 6, EURUSD: 4, GBPAUD: 2, GBPUSD: 6, SPX500: 2, USDJPY: 2}`
  - `timeframe_counts={H1: 12, M1: 14, M15: 6, M5: 4}`
  - `grid_enabled_count=30`
  - `close_by_money_count=30`
  - `max_orders_values=[1, 7]`
  - best supplied tester-report signal: `AUDCAD` `M5`, `04:00:00-05:00:00`, `profit_factor=15.12`, `equity_drawdown_relative_pct=2.25`, `total_trades=294`
- Verification from this import pass:

```text
python -m pytest tests/test_forex_fury_sets.py tests/test_external_benchmark.py -q
# 4 passed

python scripts/run_forex_fury_set_import.py --source-dir "C:\Users\wakil\Downloads\Forex-Fury-CORE-1.4NEW-SETS (1)" --summary-only
# set_count=36, tester_report_count=30, best_profit_factor=15.12
```

- Boundary: the importer reads `.set`/tester-report files and fingerprints
  `.ex4`/`.ex5` binaries only. It does not execute EA binaries, place orders,
  create broker `ACCEPT`, deposit, withdraw, move bank/card money, or automate
  payouts.
- Previous next implementation lane to surface this import in the Optimizer UI
  and generate CAS backtest/replay candidates is now complete. The remaining
  lane is replay execution plus MT4 paper/demo receipt work.

- MT4 mailbox bridge scaffold is now implemented.
- New MT4 files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\broker\mt4_mailbox_bridge.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_mt4_mailbox_smoke.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_mt4_mailbox_bridge.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\mt4\Experts\CASForexBridgeEA.mq4`
- Updated export:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\broker\__init__.py`
- Smoke artifact:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\mt4_mailbox_smoke\mt4-mailbox-smoke-status.json`
- What the bridge does now:
  - creates MT4 mailbox `commands`, `receipts`, and `archive` directories
  - writes hashed `PING` command JSON
  - writes hashed `PLACE_ORDER` command JSON from a `BrokerOrderRequest`
  - validates `cas_forex_mt4_mailbox_receipt.v1` receipt files
  - blocks `LIVE_MT4` intents unless the caller passes `live_authorized=True`
  - keeps `PAPER_MT4` as the default bridge mode
- Verification from this MT4 bridge pass:

```text
python scripts/run_mt4_mailbox_smoke.py --mailbox-dir evidence_runs/mt4_mailbox_smoke
# status=MAILBOX_READY, broker_mode=PAPER_MT4, receipt_count=0

python -m pytest tests/test_mt4_mailbox_bridge.py -q
# 4 passed

python -m pytest tests -q
# 377 passed

cd ui && npm run build
# 51 modules, 324.90 KB JS, 87.71 KB gzip
```

- Remaining MT4 work: finish/compile/attach the MQL4 EA side so MT4 writes a
  real heartbeat and receipt JSON, then add an MT4 receipt/probe API panel next
  to the current MT5 probe.
- Boundary: the mailbox bridge writes and reads files. It does not place live
  orders, create broker `ACCEPT`, deposit, withdraw, move bank/card money, or
  automate payouts by itself.

- External benchmark API/UI wiring is now implemented.
- New backend/code files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\external_benchmark.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_external_benchmark_snapshot.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_external_benchmark.py`
- New/updated API surface:
  - `/api/forex/strategy/external-benchmarks`
  - `/api/forex/dashboard` now includes `externalBenchmarks`
- Updated UI/API files:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\types\evidence.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\api.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\App.tsx`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\OptimizerPage.tsx`
- Optimizer page now shows the external benchmark table with public Forex Fury
  systems, platform, symbol, gain, monthly return, drawdown, trades, profit
  factor, and average trade length.
- Normalized summary:
  - `benchmark_count=3`
  - `mt4_account_count=3`
  - `real_account_count=3`
  - `symbols=[AUDUSD, GBPUSD, USDCAD]`
  - `total_public_trade_count=646`
  - `best_gain_pct=554.1`
  - `lowest_drawdown_pct=8.6`
- Verification from this wiring pass:

```text
python scripts/run_external_benchmark_snapshot.py --summary-only
# benchmark_count=3, mt4_account_count=3, total_public_trade_count=646

python -m pytest tests/test_external_benchmark.py tests/test_settings_api_surface.py -q
# 13 passed

python -m pytest tests -q
# 373 passed

cd ui && npm run build
# 51 modules, 324.90 KB JS, 87.71 KB gzip
```

- Remaining next implementation lane: finish/attach the MT4 EA side and build
  `scripts\run_mt4_paper_receipt.py` plus the MT4 receipt/probe API/UI panel.
- Boundary: benchmark API/UI is comparison/intelligence only. It does not place
  live orders, create broker `ACCEPT`, deposit, withdraw, move bank/card money,
  or automate payouts.

- External Forex Fury / MT4 / agentic workflow first pass is now recorded.
- New local implementation note:
  `C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\CAS_FOREX_FOREX_FURY_MT4_AGENTIC_WORKFLOW_20260624.md`.
- New machine-readable benchmark snapshot:
  `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\external_benchmark\forex-fury-mt4-benchmark-20260624-report.json`.
- Reviewed public Myfxbook pages:
  - Forex FURY AU:
    `https://www.myfxbook.com/members/forexfuryreal/forex-fury-au/11171494`
  - Forex Fury USDCAD 50K:
    `https://www.myfxbook.com/members/forexfuryreal/forex-fury-usdcad-50k/9421542`
  - Forex FURY 26/39:
    `https://www.myfxbook.com/members/forexfuryreal/forex-fury-26amp39/11975493`
- Public-page finding: all three are visible as real USD automated MetaTrader 4
  systems, but full trade detail/open trades are private. Treat them as
  external benchmark targets unless full Myfxbook API, CSV, PDF, HTML, or
  broker-terminal exports are provided.
- MT4 fit verdict: likely worth adding because the owner benchmark examples are
  MT4 and CAS Forex already has MT4 config/schema hooks (`mt4_enabled`,
  `mt4_mailbox_dir`, `PAPER_MT4`, `LIVE_MT4`). Missing implementation is the
  actual bridge.
- Next MT4 files to build:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\broker\mt4_mailbox_bridge.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\mt4\Experts\CASForexBridgeEA.mq4`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_mt4_paper_receipt.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_mt4_mailbox_smoke.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_mt4_mailbox_bridge.py`
- External benchmark files built in the API/UI wiring pass above:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\external_benchmark.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_external_benchmark_snapshot.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_external_benchmark.py`
- Long-horizon agentic workflow verdict: yes, add it to CAS Harness/CAS Forex so
  multiple LLM agents can run evidence harvesting, strategy mining, backtesting,
  risk/margin solving, terminal bridge work, UI work, and audit verification
  over long jobs while writing structured handoffs.
- Agentic workflow files to build:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_workflow.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_agent_workflow_queue.py`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_agent_workflow.py`
- Boundary: this first pass creates project memory and implementation targets.
  It does not place live orders, create broker `ACCEPT`, deposit, withdraw,
  move bank/card money, or automate payouts.

- Trading-edge gate has been separated from the paper-maturity blocker.
- Refreshed owner-promotion review:
  `evidence_runs/owner_promotion_review/owner-promotion-review-20260624030818-report.json`.
- D1 `tsmom_126_250_2_10` now clears strategy-edge thresholds in live readiness:
  - `simulator_wins=18`
  - `walk_forward_windows=5`
  - `positive_routed_window_rate=0.6`
  - `mean_return_pct=1.8932`
  - `max_drawdown_pct=7.0764`
  - `trades=76`
- Remaining owner-promotion blockers are paper proof only:
  - `paper_days 3 < required 30`
  - `paper_passed is false`
- `trading_edge` now reports `PASSED`.
- `paper_proof_maturity` remains `OPEN`.
- Default live readiness is now `NOT_READY_FOR_LIVE`, `10 / 16`,
  `checks_open=1`, `checks_mismatch=0`.
- `strategy_leads.json` was updated for `index_tsmom_126_d1` to reflect 3
  complete bundles, 27 paper days remaining, 2 UI-maturity bundles remaining,
  broker-synced `$100,000` risk review, and next due date `2026-06-25`.
- Verification from this trading-edge pass:

```text
python -m pytest tests/test_live_readiness.py tests/test_settings_api_surface.py -q
# 14 passed

python -m pytest tests -q
# 371 passed

cd ui && npm run build
# 51 modules, 318.07 KB JS, 85.57 KB gzip
```

- Owner future-study inputs handled in first benchmark pass above:
  - Forex Fury AU Myfxbook:
    `https://www.myfxbook.com/members/forexfuryreal/forex-fury-au/11171494`
  - Forex Fury USDCAD 50K Myfxbook:
    `https://www.myfxbook.com/members/forexfuryreal/forex-fury-usdcad-50k/9421542`
  - Forex Fury 26/39 Myfxbook:
    `https://www.myfxbook.com/members/forexfuryreal/forex-fury-26amp39/11975493`
  - Evaluate whether MT4 is a better terminal/integration fit than MT5 for CAS
    Forex execution/history ingestion.
  - Assess long-horizon agentic workflow support for spawning/attaching
    multiple LLM agents inside CAS Harness.
- These owner inputs are now studied enough to become concrete implementation
  targets, but they are not completed runtime features yet.

- Paper proof maturity was advanced with two additional completed daily bundles.
- Ran:

```text
python scripts/run_daily_paper_bundle.py --date 2026-06-23 --account-equity 100000 --max-risk-pct 0.5 --daily-risk-pct 1 --output-dir evidence_runs/index_tsmom_126_paper_proof
python scripts/run_daily_paper_bundle.py --date 2026-06-24 --account-equity 100000 --max-risk-pct 0.5 --daily-risk-pct 1 --output-dir evidence_runs/index_tsmom_126_paper_proof
python scripts/run_paper_ui_readiness.py --output-dir evidence_runs/index_tsmom_126_paper_proof --min-daily-bundles 5
python scripts/run_paper_daily_schedule.py --date 2026-06-24 --account-equity 100000 --output-dir evidence_runs/index_tsmom_126_paper_proof
```

- Current paper proof maturity:
  - `complete_bundle_days=3`
  - complete dates: `2026-06-22`, `2026-06-23`, `2026-06-24`
  - `broker_verified_days=3`
  - `decision_days=3`
  - `risk_review_days=3`
  - all paper proof / paper decision / paper risk chains verify
  - latest bundle date: `2026-06-24`
  - latest risk review account equity: `$100,000`
  - latest risk status: `PAPER_ATTEMPTS_ALLOWED`
  - latest total planned lots: `0.2`
- Current proof UI threshold remains `NOT_READY_FOR_UI_UX` because `3 / 5`
  complete daily bundles exist.
- Next due bundle is `2026-06-25`.
- Next command:

```text
python scripts/run_daily_paper_bundle.py --date 2026-06-25 --account-equity 100000 --max-risk-pct 0.5 --daily-risk-pct 1 --output-dir evidence_runs/index_tsmom_126_paper_proof
```

- Full 30-day paper proof gate still needs `27` more paper trading days.
- Verification from this proof-window pass:

```text
python -m pytest tests/test_paper_daily_bundle.py tests/test_paper_daily_schedule.py tests/test_paper_ui_readiness.py tests/test_live_readiness.py tests/test_settings_api_surface.py -q
# 23 passed

python -m pytest tests -q
# 370 passed

cd ui && npm run build
# 51 modules, 318.07 KB JS, 85.57 KB gzip
```

- Broker-synced paper risk evidence has now been applied to the real local
  paper-risk evidence chain.
- Command path used: `apply_broker_synced_risk_review(confirm_apply=True)`.
- Active `paper-risk-status.json` now has `review_count=2`,
  `chain_verified=true`, and latest `account_equity=100000.0`.
- The dashboard/daily-bundle overlay now treats the broker-synced paper-risk
  review as the active default risk review.
- Default account ledger now starts from `$100,000` and no longer requires a
  new risk review for the selected investment.
- Default account reconciliation is now `RECONCILED` with `checks_mismatch=0`.
- Default live readiness is still `NOT_READY_FOR_LIVE`, but it improved from
  `8 / 16` to `9 / 16`; `checks_mismatch=0`.
- Broker-synced preview now reports `already_applied=true` when the active
  review already matches the broker snapshot.
- Verification from this applied-state pass:

```text
python -m pytest tests/test_broker_synced_risk_apply.py tests/test_settings_api_surface.py tests/test_account_reconciliation.py tests/test_live_readiness.py -q
# 21 passed

python -m pytest tests -q
# 370 passed

cd ui && npm run build
# 51 modules, 318.07 KB JS, 85.57 KB gzip
```

- Boundary: this is still paper/demo evidence-chain work. It does not place
  orders, create broker `ACCEPT`, deposit, withdraw, move bank/card money, or
  automate payouts. Remaining live operability blockers are now proof-window
  maturity, trading-edge promotion, and the real-money/payment authorization
  gates.

- Added explicit broker-synced paper risk apply endpoint:
  `/api/forex/account/apply-broker-sync-risk-review?confirm_apply=true`.
- The apply path appends a broker-synced paper-risk review into the local
  paper-risk evidence chain using the existing `append_paper_risk_review(...)`
  and `write_paper_risk_status(...)` path.
- The endpoint refuses to write without `confirm_apply=true`.
- The apply helper is idempotent: if the latest paper-risk review already
  matches the verified broker demo snapshot balance and source decision, it
  returns `already_applied=true` and does not append a duplicate.
- Dashboard Broker Sync mode now has an `Apply` button for this action and
  displays whether evidence was appended or already present.
- API `daily_bundle()` overlays the latest `paper-risk-status.json` when it
  exists, so applied broker-synced paper risk becomes visible as the active
  risk review instead of staying hidden behind stale daily-bundle status.
- Verification from this pass:

```text
python -m pytest tests/test_broker_synced_risk_apply.py tests/test_settings_api_surface.py tests/test_paper_risk.py tests/test_live_readiness.py -q
# 20 passed

python -m pytest tests -q
# 370 passed

cd ui && npm run build
# 51 modules, 318.07 KB JS, 85.57 KB gzip
```

- Smoke from this pass:

```text
broker-synced preview: PAPER_ATTEMPTS_ALLOWED, broker_snapshot_initial_investment_usd=100000.0, total_planned_lots=0.2
default live readiness: NOT_READY_FOR_LIVE, 8 / 16 checks passed, account_reconciliation=MISMATCH
```

- Boundary: this is still paper/demo evidence-chain work. It does not place
  orders, create broker `ACCEPT`, deposit, withdraw, move bank/card money, or
  automate payouts. Trading edge remains `OPEN`; live trading, broker `ACCEPT`,
  auto-deposit, debit/card/bank movement, and payout automation remain
  `NOT LICENSED`.

- Added broker-synced paper risk sizing preview at `/api/forex/account/broker-sync-risk-preview`.
- Added dashboard payload key `brokerSyncedRiskPreview`.
- Dashboard Broker Sync mode now shows broker-seeded risk sizing: broker seed, default seed, preview lots, default lots, preview risk, and risk delta.
- The preview reuses `paper_risk.review_paper_risk_budget(...)` with the verified MT5 demo account snapshot balance, so it is the real paper risk sizing path, not a separate calculator.
- Current smoke: `PAPER_ATTEMPTS_ALLOWED`, account equity `$100,000`, total planned lots `0.20`, total planned risk `$253.02`, delta vs default `+$95,000` account equity, `+$227.72` planned risk, `+0.18` lots.
- This remains preview-only: `would_append_evidence=false`, `live_money_authorized=false`, `payment_movement_authorized=false`.
- Dashboard now has a segmented `Default` / `Broker Sync` control in the "Live Operability Checklist" panel.
- `Default` shows the owner/risk-review paper ledger seed and keeps `account_reconciliation=MISMATCH` when the internal `$5,000` ledger does not match the verified `$100,000` MT5 demo snapshot.
- `Broker Sync` explicitly fetches `/api/forex/readiness/live?sync_to_broker=true`, displays the broker snapshot seed, and shows the reconciliation row as `PASSED` when broker balance/equity are used.
- Broker-sync preview is a UI/API preview only; it does not silently change the default owner seed or authorize live money.
- Added the plain-English live operability checklist at `cas-forex\cas_forex\live_readiness.py`.
- Added API route `/api/forex/readiness/live`.
- Added explicit broker-synced preview `/api/forex/readiness/live?sync_to_broker=true`.
- Added dashboard payload key `liveReadiness`.
- Replaced the generic Dashboard "Live & Payment Gates" card with a computed "Live Operability Checklist" panel.
- The checklist covers: owner initial investment, investment movement tracking, market movement tracking, broker/demo receipt, broker account snapshot, CAS-vs-broker reconciliation, latest MT5 probe health, evidence chain, paper/demo proof window, trading edge, AI compounding memory, live order execution, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and payout automation.
- Movement-stream metadata now explicitly lists swap, commission, broker fees, open-position count, floating P/L, margin estimate, market-open/session/source fields.
- Verification from this pass:

```text
python -m pytest tests/test_live_readiness.py tests/test_movement_stream.py tests/test_account_reconciliation.py tests/test_settings_api_surface.py -q
# 21 passed

python -m pytest tests/test_live_readiness.py tests/test_settings_api_surface.py -q
# 11 passed

python -m pytest tests/test_paper_risk.py tests/test_live_readiness.py tests/test_settings_api_surface.py -q
# 18 passed

python -m pytest tests -q
# 368 passed

cd ui && npm run build
# 51 modules, 317.01 KB JS, 85.25 KB gzip
```

Smoke from this pass:

```text
default live readiness: NOT_READY_FOR_LIVE, 8 / 16 checks passed, account_reconciliation=MISMATCH
sync_to_broker=true: NOT_READY_FOR_LIVE, 8 / 16 checks passed, account_reconciliation=PASSED, broker_snapshot_initial_investment_usd=100000.0
```

## Plain-English Product Goal

CAS Forex should become an owner cockpit that can make real money through live broker execution once the system has proved the edge, broker route, account setup, and runtime authority path. The paper/demo phase exists to build and prove that path, not to stop there.

The finished system should:

1. Pull market data and broker/demo receipts.
2. Generate strategy proposals.
3. Test proposals across real data, synthetic regimes, and condition buckets.
4. Route evidence-backed paper/demo actions now, then evidence-backed live actions after live gates are complete.
5. Let AI manage paper/demo decisions now, including compounding, stop/take-profit review, and future strategy memory; later let AI operate live only after owner authorization and runtime gates are complete.
6. Save every important decision into evidence artifacts.
7. Display the whole state in a usable UI/PWA.
8. Let the owner enter/deposit any initial investment amount, then track that capital through deposits, live balance, equity, open P/L, closed P/L, fees, swaps, commission, margin, withdrawals, and payouts.
9. Track both investment movement and market movement in real time.
10. Turn real-money actions on when the owner explicitly enables them and all runtime/broker/account/payment/evidence gates pass.

Important: do not tell the owner this is "just research." The correct framing is:

```text
Ultimate goal: real live-money owner trading/income.
Current phase: paper/demo proof, UI, broker, evidence, and runtime buildout.
Reason live is not active yet: gates are incomplete, not because the product is meant to stay research-only.
```

## What "Paper" Means Here

Paper means simulated or demo/research trading. It can include MT5 demo receipts and paper positions, but it is not real-money live broker execution. Paper can test:

- entries
- exits
- stop loss
- take profit
- compounding / adding to winners
- risk settings
- strategy routing
- evidence logging

Paper does not mean:

- live order placement
- broker `ACCEPT`
- deposits
- withdrawals
- bank/card movement
- payout automation
- guaranteed income

## Screenshot-Derived UI And Backend Requirements

The owner provided mobile trading-history and MT4/MT5 strategy-report screenshots as product references. Future agents should treat these as required UI/backend behavior targets for CAS Forex, not decoration.

What the screenshots show:

1. A mobile History screen with top-level account summary:
   - `Profit`
   - `Deposit`
   - `Balance`
   - per-trade rows
   - symbol
   - buy/sell direction
   - lot size
   - entry price -> exit price
   - timestamp
   - profit/loss amount
   - blue positive values
   - red negative values

2. A dark mobile terminal History screen with:
   - tabs for `Positions`, `Orders`, and `Deals`
   - bottom navigation for `Quotes`, `Chart`, `Trade`, `History`, and `Settings`
   - account cashflow summary: `Deposit`, `Profit`, `Swap`, `Commission`, `Balance`
   - closed trade list with order side, lot size, price movement, timestamp, and result

3. A time-filtered history view with:
   - `Seconds`, `Minutes`, `Hour`, `Day`, `Week`, `Month`, and `Custom` filters
   - many symbols at once: EURCHF, AUDUSD, XAUUSD, CHFJPY, GBPJPY, EURGBP, GBPUSD, USDJPY, EURNZD, NZDJPY
   - running daily profit, credit, deposit, withdrawal, and balance totals

4. An MT4/MT5 Strategy Tester report with:
   - initial deposit
   - total net profit
   - gross profit / gross loss
   - profit factor
   - expected payoff
   - absolute/maximal/relative drawdown
   - total trades
   - short/long positions
   - profit/loss trade counts and percentages
   - largest/average profit and loss trades
   - consecutive wins/losses
   - balance/equity curve
   - detailed order table
   - lot sizes, order IDs, open/close times, spread, modeling quality, and broker/server metadata

Required CAS Forex UI features from these screenshots:

- Account summary header: current balance, equity, deposit/invested capital, realized profit, floating profit, drawdown, margin, free margin, swap, commission, and fees.
- History screen with `Positions`, `Orders`, and `Deals` tabs.
- Time filters: `Seconds`, `Minutes`, `Hour`, `Day`, `Week`, `Month`, and `Custom` for scalping through swing views.
- Multi-symbol history with searchable/filterable rows.
- Color-coded P/L: positive, negative, flat.
- Row-level trade details: symbol, side, lot size, open price, close/current price, SL, TP, timestamp, broker ticket/order ID, strategy ID, AI action, evidence packet ID, and net P/L.
- Deposit/investment ledger: every owner deposit, withdrawal, transfer, payout, fee, and balance adjustment should be visible.
- Strategy tester/report view: profit factor, expected payoff, drawdown, win/loss stats, balance/equity curve, and full trade table.
- Mobile/PWA layout should feel like a serious trading terminal: dense, fast, scrollable, readable, and optimized for repeated use.

Required backend features from these screenshots:

- Owner can set or deposit any positive initial investment amount, not a fixed `$5,000` assumption.
- Account ledger model must store:
  - initial investment
  - deposits
  - withdrawals
  - realized P/L
  - floating P/L
  - swap
  - commission
  - broker fees
  - balance
  - equity
  - margin used
  - free margin
  - payout records
- Real-time investment movement tracking:
  - account balance/equity stream
  - open position P/L stream
  - closed deal stream
  - deposit/withdrawal/payout stream
  - margin and drawdown stream
  - broker reconciliation snapshots
- Real-time market movement tracking:
  - bid/ask quotes
  - spread
  - candles/ticks
  - symbol session state
  - volatility/ATR
  - market movement against active SL/TP
  - event/macro condition overlays where available
- Evidence requirements:
  - every deposit/investment event must have a ledger ID
  - every trade/order/deal must have a broker/demo ticket or simulator ticket
  - every AI decision must link to evidence refs and current condition state
  - every balance/equity update should be reconcilable to broker/demo/account data

Important implementation framing:

```text
The owner must be able to choose any initial investment amount.
The system must track how that investment moves in real time.
The system must track how the market moves in real time.
Paper/demo mode should emulate this now; live mode should use broker/payment/provider integrations once gates are complete.
```

## Current Verified Operating State

Last verified in this handoff pass:

```bash
python -m pytest tests/test_settings_api_surface.py tests/test_runtime_gates.py tests/test_authority_boundary.py -q
# 14 passed

python -m pytest tests -q
# 344 passed

cd ui
npm run build
# 51 modules, 275.87 KB JS, 76.45 KB gzip
```

Local API was restarted and verified:

```text
http://127.0.0.1:8765/api/forex/health -> healthy
http://127.0.0.1:8765/api/forex/settings/owner-control
http://127.0.0.1:8765/api/forex/dashboard
```

The live owner-control payload no longer exposes:

```text
personal_utilization_only
account_scope
disallowed_scopes
```

Runtime gates still report real-money capabilities as not authorized unless the owner provides the required enable flags, credentials/provider config, and gate clearance. This is a completion checklist, not a permanent "no."

## Current Evidence Snapshot

Known evidence and status:

- Leveraged income backsolve: `16,800` scenarios, `0` viable scenarios.
- AI mode for backsolve: `AI_FULL_AUTO_PAPER`.
- Backsolve verdict counts from latest known report:
  - `TARGET_NOT_REACHED=14532`
  - `TARGET_REACHED_BUT_DRAWDOWN_FAIL=2168`
  - `TARGET_REACHED_BUT_MARGIN_FAIL=100`
- MT5 demo receipt: `BROKER_API_VERIFIED`, Hugosway-Demo, MetaTrader 5.
- Active adaptive cockpit status: `READ_ONLY_PAPER_RESEARCH`.
- Adaptive actions include `OPEN_INITIAL=2` in latest known cockpit.
- UI readiness: read-only shell may run, but multi-day proof maturity is still pending.
- Paper proof maturity remains below deployment/live promotion threshold.

The `$5k-$12k/month` target from a small seed is currently labeled `SURVIVAL_RISK`, not a projection.

## Current UI And API Surface

UI root:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui
```

Current pages:

```text
ProofPage.tsx
AuditPage.tsx
DashboardPage.tsx
TradePage.tsx
AdaptivePage.tsx
HistoryPage.tsx
SettingsPage.tsx
PcbaPage.tsx
LedgerPage.tsx
OptimizerPage.tsx
ConditionLabPage.tsx
```

API root:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api
```

API entry:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\server.py
```

API routers:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\proof.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\bundle.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\strategy.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\adaptive.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\settings.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\pcba.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\routes\mt.py
```

Shared API evidence loader:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\data.py
```

## What PCBA Does In This App

PCBA is not the trading engine. PCBA is the diagnostic and guard layer around AI/optimizer output, CAS/CJT/CCB diagnostics, prompt-injection surfaces, and claim boundaries.

In guarded paths, PCBA does reject blocked inputs/proposals:

- `CASPCBAOptimizerGuard.review(...)` returns `REJECT` when a proposal tries to cross live/payment/broker authority, uses guaranteed-profit language, or contains prompt-injection surfaces.
- `AIModelClient.generate(...)` returns `ok=False` when the prompt or model output trips the PCBA prompt-injection guard.

PCBA also prevents authority escalation:

- PCBA diagnostics cannot unlock live trading.
- PCBA diagnostics cannot create broker `ACCEPT`.
- PCBA/CJT/CCB may support `OPEN`, `FLAG_FOR_HUMAN_REVIEW`, `LIVE_LOCKED`, or `NOT LICENSED` style diagnostic claims, not live authority.

Important files:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\ai_model.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\llm_optimizer.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\pcba_prompt_injection.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\pcba_readiness.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\schemas\pcba.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\PcbaPage.tsx
```

## Core Source Map

Backtest and economics:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\backtest\engine.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\instruments.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\schemas\forecast.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\schemas\order.py
```

Strategies and forecast harness:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\forecast\strategies.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\forecast\chronos_signal.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\forecast\cas_ensemble.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\forecast\harness.py
```

Broker and market data:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\market_data\connector.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\broker\mt5_bridge.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\paper_broker_adapter.py
```

Runtime gates and authority:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\runtime_gates.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\authority_boundary.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\owner_control.py
```

CAS verifier gates:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\verifier\auditor.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\verifier\risk_gate.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\verifier\macro_gate.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\verifier\market_gate.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\verifier\execution_gate.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\verifier\live_lock.py
```

Evidence and proof:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\evidence_store.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\paper_proof.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\paper_daily_bundle.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\paper_daily_schedule.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\paper_ui_readiness.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs
```

Condition Lab, SDG, walk-forward:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\sdg.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\regime_sim.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\condition_lab.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\event_context.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\walk_forward.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\condition_tally.py
```

Adaptive compounding and imported MT history:

```text
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\adaptive_compounding.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\adaptive_cockpit.py
C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\mt_history_import.py
```








## 2026-06-23 Windows MT5 Demo Probe Succeeded And Broker-Synced Reconciliation Preview

Implemented after surfacing latest MT5 probe status:

- Verified WSL Python lacks `MetaTrader5`, but Windows Python has `MetaTrader5` installed.
- Ran `python.exe scripts/run_mt5_paper_receipt.py --date 2026-06-23 --output-dir evidence_runs/index_tsmom_126_paper_proof` without `--append-if-verified`.
- New probe artifact: `cas-forex\evidence_runs\index_tsmom_126_paper_proof\index-tsmom-126-d1-paper-proof-mt5-demo-probe-20260623212602.json`.
- Probe status: `BROKER_API_VERIFIED` on Hugosway-Demo, `live_mode=false`.
- Captured redacted `account_snapshot`: balance `$100,000`, equity `$100,000`, margin `$0`, free margin `$100,000`, currency `USD`, leverage `500`, account hash only.
- Proof ledger was not appended because the run did not use `--append-if-verified`.
- Default account reconciliation now correctly reports `RECONCILIATION_FAILED` because the internal owner/risk-review paper ledger is `$5,000` while broker demo account balance/equity is `$100,000`.
- Added explicit opt-in broker-synced reconciliation preview: `/api/forex/reconciliation/account?sync_to_broker=true`.
- Broker-synced preview seeds paper/demo accounting from verified broker balance and proves `balance_equity_reconciliation=OK` without silently changing the default owner/risk seed and without authorizing live money.
- Dashboard copy now notes that broker-synced reconciliation preview is available but remains paper/demo accounting only.

Verification from this pass:

```text
python3 -m pytest tests/test_account_reconciliation.py tests/test_paper_broker_adapter.py tests/test_account_ledger.py tests/test_movement_stream.py -q
# 19 passed

python.exe -m pytest tests/test_settings_api_surface.py tests/test_account_reconciliation.py tests/test_paper_broker_adapter.py -q
# 19 passed

python.exe -m pytest tests -q
# 364 passed

cd ui && npm run build
# 51 modules, 302.23 KB JS, 82.13 KB gzip
```

Boundary preserved: broker-synced reconciliation is an explicit paper/demo accounting preview. It does not place orders, create broker `ACCEPT`, deposit, withdraw, move bank/card money, or automate payouts. Trading edge remains `OPEN`; live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and payout automation remain `NOT LICENSED`.

## 2026-06-23 Latest MT5 Probe Status Endpoint And Current Blocker

Implemented after MT5 account snapshot support:

- Ran `python3 scripts/run_mt5_paper_receipt.py --date 2026-06-23 --output-dir evidence_runs/index_tsmom_126_paper_proof` without `--append-if-verified`.
- New probe artifact: `cas-forex\evidence_runs\index_tsmom_126_paper_proof\index-tsmom-126-d1-paper-proof-mt5-demo-probe-20260623211448.json`.
- Probe result: `UNAVAILABLE` with reason `MetaTrader5 Python package is unavailable.`
- The proof ledger was not appended or mutated by this unavailable probe.
- `/api/forex/mt/receipt/latest` now returns the latest probe that actually contains a verified broker receipt, instead of being overwritten by the newest unavailable attempt.
- Added `/api/forex/mt/probe/latest` and dashboard `mt5ProbeStatus` for the newest probe attempt and blocker.
- Proof UI now shows Latest MT5 Probe Attempt separately from the last verified MT5 receipt.
- Current blocker to getting `account_snapshot` from real demo broker evidence: install/configure the MetaTrader5 Python package and connected MT5 demo terminal in the runtime environment, then rerun the MT5 paper receipt probe.

Verification from this pass:

```text
python3 -m pytest tests/test_paper_broker_adapter.py tests/test_account_reconciliation.py tests/test_account_ledger.py tests/test_movement_stream.py -q
# 18 passed

python.exe -m pytest tests/test_settings_api_surface.py tests/test_paper_broker_adapter.py tests/test_account_reconciliation.py -q
# 17 passed

python.exe -m pytest tests -q
# 362 passed

cd ui && npm run build
# 51 modules, 301.83 KB JS, 81.98 KB gzip
```

Boundary preserved: MT5 probe status is evidence/operations reporting only. It does not place orders, create broker `ACCEPT`, deposit, withdraw, move bank/card money, or automate payouts. Trading edge remains `OPEN`; live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and payout automation remain `NOT LICENSED`.

## 2026-06-23 MT5 Demo Account Snapshot In Broker Receipts

Implemented after broker/demo account reconciliation:

- `MT5DemoPaperReceiptAdapter` now includes a redacted `account_snapshot` in API-verified MT5 demo receipts.
- `account_snapshot` can carry `balance`, `equity`, `margin`, `margin_free`, `currency`, `leverage`, `server`, and `account_id_hash`.
- Raw login/account identifiers are still excluded from the receipt payload.
- `paper_proof.validate_paper_broker_receipt(...)` preserves normalized account snapshots into proof-day summaries.
- `/api/forex/mt/receipt/latest` now exposes `account_snapshot` and top-level `balance`, `equity`, `margin`, `margin_free`, `account_currency`, and `account_leverage` aliases when broker evidence contains them.
- `account_reconciliation.py` now reads either top-level or nested broker account snapshots, allowing `balance_equity_reconciliation` to become `OK` once new MT5 demo receipts include matching balance/equity truth.
- Existing saved MT5 receipt artifacts still lack account balance/equity/margin, so current dashboard evidence may remain `UNVERIFIABLE` until the next MT5 demo probe captures an account snapshot.

Verification from this pass:

```text
python3 -m pytest tests/test_paper_broker_adapter.py tests/test_account_reconciliation.py tests/test_account_ledger.py tests/test_movement_stream.py -q
# 18 passed

python.exe -m pytest tests/test_settings_api_surface.py tests/test_paper_broker_adapter.py tests/test_account_reconciliation.py -q
# 16 passed

python.exe -m pytest tests -q
# 361 passed

cd ui && npm run build
# 51 modules, 299.85 KB JS, 81.56 KB gzip
```

Boundary preserved: broker account snapshots are receipt/accounting evidence only. They do not place orders, create broker `ACCEPT`, deposit, withdraw, move bank/card money, or automate payouts. Trading edge remains `OPEN`; live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and payout automation remain `NOT LICENSED`.

## 2026-06-23 Broker/Demo Account Reconciliation Snapshot

Implemented after the provider-backed movement snapshot path:

- Added `cas-forex\cas_forex\account_reconciliation.py`.
- Added `/api/forex/reconciliation/account`.
- Added `accountReconciliation` to `/api/forex/dashboard`.
- Reconciliation cross-checks the internal owner investment ledger and movement stream against broker/demo receipt evidence.
- Checks include receipt validation, hash-chain verification, live-mode consistency, symbol coverage, open-position reconciliation, balance/equity reconcilability, and movement-vs-ledger consistency.
- Missing broker balance/equity is reported as `UNVERIFIABLE`, not silently accepted, so the broker/account proof gap stays visible.
- Dashboard now shows a broker/demo reconciliation panel with OK, mismatch, and unverifiable checks.
- Added `tests/test_account_reconciliation.py` and API surface checks for `/reconciliation/account` and dashboard shape.

Verification from this pass:

```text
python3 -m pytest tests/test_account_reconciliation.py tests/test_movement_stream.py tests/test_account_ledger.py -q
# 13 passed

python.exe -m pytest tests/test_settings_api_surface.py tests/test_account_reconciliation.py -q
# 11 passed

python.exe -m pytest tests -q
# 360 passed

cd ui && npm run build
# 51 modules, 299.73 KB JS, 81.52 KB gzip
```

Boundary preserved: reconciliation is read-only verification only. It does not place orders, create broker `ACCEPT`, deposit, withdraw, move bank/card money, or automate payouts. Trading edge remains `OPEN`; live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and payout automation remain `NOT LICENSED`.

## 2026-06-23 Provider-Backed Movement Snapshot Path

Implemented after the movement-stream first pass:

- `cas-forex\cas_forex\movement_stream.py` now accepts provider `MarketSnapshot` inputs in addition to deterministic paper-route fallback prices.
- `/api/forex/movement/snapshot` now accepts `?use_provider=true`.
- When provider mode is requested, `api/data.py` fetches one configured `MarketDataConnector` snapshot per active paper symbol and fails soft per symbol.
- Provider snapshots update active position current price, floating P/L, bid/ask/spread, candle high/low/close, session, and market-open state.
- `ui/src/data/api.ts` exposes `fetchMovementStream(useProvider)` for explicit provider-backed refreshes.
- Dashboard remains deterministic by default; provider mode is opt-in so the cockpit does not hang or fail when external market data is unavailable.

Verification from this pass:

```text
python3 -m pytest tests/test_movement_stream.py tests/test_account_ledger.py -q
# 8 passed

python.exe -m pytest tests/test_settings_api_surface.py -q
# 5 passed

python.exe -m pytest tests -q
# 354 passed

cd ui && npm run build
# 51 modules, 294.08 KB JS, 80.27 KB gzip
```

Boundary preserved: provider-backed movement snapshots are telemetry only. They do not place live orders, create broker `ACCEPT`, deposit, withdraw, move bank/card money, or automate payouts. Trading edge remains `OPEN`; live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and payout automation remain `NOT LICENSED`.

## 2026-06-23 Paper/Demo Movement Stream First Pass

Implemented this pass after the owner investment ledger work:

- Added `cas-forex\cas_forex\movement_stream.py`.
- Added `/api/forex/movement/snapshot`.
- Added `movementStream` to `/api/forex/dashboard`.
- Movement stream recomputes paper/demo account movement from the owner investment ledger and active paper rows.
- Account movement fields include balance, equity, realized P/L, floating P/L, swap, commission, broker fees, margin used, free margin, drawdown, deposit, withdrawal, payout, and open-position count.
- Market movement fields include bid, ask, mid, spread, synthetic candle, ATR units, SL/TP distance, floating P/L units/USD, and estimated margin.
- Dashboard and Trade UI now surface the paper/demo movement stream.
- Added `tests/test_movement_stream.py` and API surface checks for dashboard `/movement/snapshot` shape.

Verification from this pass:

```text
python3 -m pytest tests/test_movement_stream.py tests/test_account_ledger.py -q
# 7 passed

python.exe -m pytest tests/test_settings_api_surface.py -q
# 5 passed

python.exe -m pytest tests -q
# 353 passed

cd ui && npm run build
# 51 modules, 294.08 KB JS, 80.27 KB gzip
```

Boundary preserved: movement streams are paper/demo telemetry only. They do not place live orders, create broker `ACCEPT`, deposit, withdraw, move bank/card money, or automate payouts. Trading edge remains `OPEN`; live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and payout automation remain `NOT LICENSED`.

## 2026-06-23 Owner Investment / Account Ledger First Pass

Implemented this pass after the original handoff was written:

- Added `cas-forex\cas_forex\account_ledger.py`.
- Added `/api/forex/account/ledger` with optional positive `initial_investment` query parameter.
- Added `accountLedger` to `/api/forex/dashboard`.
- Ledger accepts any positive owner-selected paper/demo initial investment amount.
- Ledger summarizes deposit, balance, equity, realized P/L, floating P/L, swap, commission, broker fees, margin used, free margin, drawdown, planned risk, withdrawals, and payouts.
- Ledger emits internal `ledger_id` values and simulator tickets for paper/demo rows.
- Ledger exposes `Positions`, `Orders`, and `Deals` rows plus `Seconds`, `Minutes`, `Hour`, `Day`, `Week`, `Month`, and `Custom` filter metadata.
- Dashboard, Ledger, and History UI now surface the account/investment and terminal-history shape.
- Added `tests/test_account_ledger.py` and API surface checks for dashboard/account ledger shape.

Verification from this pass:

```text
python.exe -m pytest tests/test_account_ledger.py tests/test_settings_api_surface.py -q
# 9 passed

python.exe -m pytest tests -q
# 350 passed

python3 -m pytest tests/test_account_ledger.py -q
# 5 passed

cd ui && npm run build
# 51 modules, 286.46 KB JS, 78.67 KB gzip
```

Boundary preserved: the account ledger is internal paper/demo accounting only. It does not deposit, withdraw, move bank/card money, place live orders, create broker `ACCEPT`, or automate payouts. Trading edge remains `OPEN`; live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and payout automation remain `NOT LICENSED`.

## Priority Goal List

### P0 - Preserve Current Truth And Prevent Regressions

- Keep `OPEN`, `NOT LICENSED`, `FLAG_FOR_HUMAN_REVIEW`, `LICENSED`, `ACCEPT`, `present`, and `unavailable` wording exact.
- Do not reintroduce the removed hard personal-only scope switch.
- Keep runtime gates as owner-controlled gates.
- Keep PCBA authority bounded: diagnostic/guard only, no broker `ACCEPT`, no live unlock.
- Keep the UI honest: paper/demo/research labels must be visible wherever trade/profit/live controls appear.
- Add or preserve tests for every authority boundary.

### P1 - Close The Paper-Proof Gap

- Continue generating real daily paper bundles until minimum UI maturity and longer paper-proof thresholds are met.
- Keep MT5 demo receipt verification tied to real demo broker evidence.
- Make the daily proof ledger easy to inspect in the UI.
- Store paper decisions, paper risk reviews, adaptive decisions, and imported MT4/MT5 history as evidence.
- Make failures visible instead of hiding missing days or missing evidence.

### P2 - Improve Trading Evidence

- Prioritize broker-grade data for `US30`, `NAS100`, `XAU/USD`, and owner-relevant symbols.
- Improve instrument economics: point value, contract size, spread, commission, swap, slippage, margin.
- Replace Yahoo proxy assumptions where possible.
- Add broker tick/M1 data import paths.
- Fix historical macro gate behavior so backtests use candle-time macro context, not wall-clock now.
- Run walk-forward and out-of-sample tests before promoting any strategy.
- Treat `$5k-$12k/month` targets as stress/backsolve goals, not expected returns, until evidence supports them.

### P3 - Strengthen Adaptive AI Paper Autonomy

- Make adaptive compounding learn from winning and losing basket outcomes.
- Persist conditions that led to good adds, bad adds, stop-outs, partial take-profits, and closes.
- Let AI recommend stop loss and take profit changes from past conditions, current conditions, strategy family, and live paper evidence.
- Keep all of this in paper/demo mode until live gates are cleared.
- Any new AI path must call PCBA guard before accepting optimizer proposals or model output.

### P4 - UI/UX Buildout

- Keep first screen as the actual cockpit, not a marketing landing page.
- Prioritize dense operational views:
  - Proof
  - Dashboard
  - Trade/Paper Desk
  - Adaptive
  - History
  - Settings
  - PCBA
  - Ledger
  - Optimizer
  - Condition Lab
- Add terminal-style History with `Positions`, `Orders`, and `Deals`.
- Add account/investment summary visible from mobile: deposit, profit, balance, equity, swap, commission, drawdown, and margin.
- Add `Seconds`, `Minutes`, `Hour`, `Day`, `Week`, `Month`, and `Custom` filters for history.
- Add MT4/MT5-style strategy report view with equity curve, profit factor, drawdown, trade counts, and full order table.
- Add a deposit/investment ledger screen where the owner can enter any initial investment amount for paper/demo now and live funding later.
- UI must surface:
  - evidence source
  - stale/missing artifact states
  - current mode
  - `OPEN` trading edge
  - `NOT LICENSED` real-money boundary
  - PCBA optimizer verdicts
  - daily proof progress
  - adaptive basket state
  - condition bucket performance
- Phone/PWA must use the desktop/server LAN/VPN/tunnel API URL, not `127.0.0.1` from the phone.

### P5 - Live-Readiness Path

The live-readiness path is the critical path, not an optional side quest. Move as directly as possible toward real owner-authorized live trading while closing the requirements in order:

1. Owner-selectable initial investment/deposit model implemented.
2. Real-time account/investment movement tracking implemented in paper/demo.
3. Real-time market movement tracking implemented for active symbols.
4. Broker-grade data and fill/cost model audited.
5. Strategy has walk-forward and paper-proof evidence.
6. Paper proof threshold satisfied.
7. Broker demo receipts verified across the required window.
8. Runtime gates pass.
9. Owner enable flags are explicit.
10. Broker credentials/provider config are present.
11. Legal/account/payment gates are reviewed.
12. Negative tests confirm no bypass.
13. Only then can live capability status move toward `AUTHORIZED`.

## Known Audit Hotspots

- `api\data.py` is the API truth source. Do not let it drift from UI types and tests.
- `tests\test_settings_api_surface.py` should catch stale API shape regressions.
- Backtest fill order and intrabar stop/target behavior need outside audit.
- Index and gold economics must not use FX-only pip assumptions.
- Macro gate in older backtests may use current wall-clock instead of historical candle time.
- Evidence chain is local hash-chain, not WORM/object-lock retained.
- Paper proof is still immature.
- PCBA prompt-injection is a text/surface guard, not a universal hidden-state prevention proof.

## Commands For The Next LLM

From:

```powershell
cd C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex
```

Run:

```powershell
python -m pytest tests -q
```

Run targeted authority/API checks:

```powershell
python -m pytest tests/test_settings_api_surface.py tests/test_runtime_gates.py tests/test_authority_boundary.py -q
```

Run UI build:

```powershell
cd C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui
npm run build
```

Start API:

```powershell
cd C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex
$env:PYTHONPATH='.'
python -m uvicorn api.server:app --host 127.0.0.1 --port 8765
```

Start UI preview:

```powershell
cd C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui
.\node_modules\.bin\vite preview --host 127.0.0.1 --port 5174
```

Check live API:

```text
http://127.0.0.1:8765/api/forex/health
http://127.0.0.1:8765/api/forex/dashboard
http://127.0.0.1:8765/api/forex/readiness/live
http://127.0.0.1:8765/api/forex/readiness/live?sync_to_broker=true
http://127.0.0.1:8765/api/forex/account/broker-sync-risk-preview
http://127.0.0.1:8765/api/forex/settings/owner-control
http://127.0.0.1:8765/api/forex/settings/runtime-gates
```

## Rules For Future Agents

- Read `cas_harness_production_todo.md` before changing code.
- Update `cas_harness_production_todo.md` before final response if project status changes.
- Do not say `ACCEPT` unless the gate actually says `ACCEPT`.
- Do not say `LICENSED` unless the gate actually says `LICENSED`.
- Do not convert paper/demo evidence into live-income claims.
- Do not hide blockers or missing evidence.
- Do not remove owner control.
- Do not let PCBA become fake authority.
- Do not add real-money movement without explicit owner enable flags plus credentials/provider config plus passing runtime gates.
- Do not rely only on GitHub if local untracked CAS Forex files exist; audit the local workspace.

## Clean Next Moves

1. Commit or snapshot the current local `cas-forex` folder so future LLMs/auditors do not miss untracked sprint work.
2. Use `/api/forex/readiness/live` and the Dashboard "Live Operability Checklist" as the current live-readiness map.
3. Add an explicit owner apply/run action that can append a new paper-risk review from the broker snapshot seed after the owner chooses to use it; current broker-sync risk sizing is preview-only.
4. Keep running daily paper bundles and MT5 demo receipt checks until proof maturity closes.
5. Replace fallback paper quotes with broker-grade tick/M1 data for indices/gold and owner-priority symbols.
6. Improve index/gold instrument economics: contract size, point value, spread, commission, swap, slippage, and margin.
7. Add execution dry-run coverage for order create/modify/close shapes before any live authorization path.
8. Build adaptive memory views for winning/losing condition patterns, add-to-winner decisions, stop-outs, partial take-profits, and closes.
9. Add explicit tests that every new AI optimizer route goes through PCBA guard.
10. Add provider/payment configuration surfaces only after owner enable flags and runtime-gate tests are in place.
11. Move directly toward live-readiness by closing the listed requirements rather than treating paper/demo as the endpoint.

