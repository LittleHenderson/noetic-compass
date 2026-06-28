# CAS Forex Forex Fury / MT4 / Agentic Workflow Implementation Note

Date: 2026-06-24
Workspace: `C:\Users\wakil\OneDrive\Desktop\tksCAS`
CAS Forex root: `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex`

## Plain-English Bottom Line

The Forex Fury links are useful as outside benchmark examples, especially
because all three public pages are real-money, automated, MetaTrader 4 systems.
They do not give enough public trade-by-trade detail to copy a strategy. They
do give enough public metrics to build a CAS Forex benchmark target and to add
an MT4 ingestion/execution path next to the existing MT5 path.

MT4 is a serious candidate for CAS Forex because the examples the owner sent
are MT4 systems, MT4 has broad EA support, and CAS Forex already has config and
schemas that mention MT4. The missing piece is a real MT4 bridge.

Long-horizon multi-agent workflow should be added to CAS Harness. It should let
multiple LLM agents work on long-running trading goals: evidence harvesting,
strategy mining, backtesting, terminal bridge work, UI work, risk/margin review,
and audit verification. Their output should feed the optimizer/research queue,
not silently bypass the owner/runtime execution path.

2026-06-24 status update: the long-horizon agentic workflow is now a first-class
CAS Forex plan artifact and Optimizer UI panel. The implementation does not yet
run the autonomous loop, but it defines the agent roster, wake cadence, evidence
pack, proposal flow, rejection rules, memory writes, and next code files needed
to execute that loop.

2026-06-24 follow-up status update: the first execution-cycle scaffold and
information-flow blueprint are now also first-class CAS Forex surfaces. The
cycle runner creates `PAPER_MT4_COMMAND_INTENT` evidence with heartbeats,
micro-scalp/hourly route intents, overseer decisions, an MT4 paper mailbox
command, and memory snapshots. A three-agent review then selected the durable
information architecture: append-only event journal for agent coordination,
evidence reports for durable artifacts, API/dashboard as read-only projections,
MT4/MT5 mailbox as terminal outbox/inbox, and outcome memory as the learning
loop. The next build target is `cas_forex\agent_message_bus.py`, followed by
terminal receipt ingest, reconciliation-gated same-symbol routing, and
trade-outcome memory.

2026-06-24 second follow-up status update: `cas_forex\agent_message_bus.py` is
now implemented. Each workflow cycle writes `cas_forex_agent_event.v1` rows to
`cas-forex\evidence_runs\agent_workflow_queue\agent-events.jsonl`, including
context, heartbeats, route intents, overseer decisions, MT4 command-written
events, terminal-receipt-pending events, and memory writes.

2026-06-24 third follow-up status update: `cas_forex\terminal_receipt_ingest.py`
is now implemented. The journal now has `270` events across `18` cycles after
verification, with `18` terminal commands still waiting for receipt files. The
latest ingest report is
`cas-forex\evidence_runs\terminal_receipt_ingest\terminal-receipt-ingest-20260624083745-report.json`.
Current mailbox receipt state is `0` receipt files, `0` verified, `0`
reconciled, `0` next-cycle allowed, and `0` mismatched. The next MT4/agentic
workflow lane is no longer receipt ingest; it is `cas_forex\agent_overseer.py`
consuming `NEXT_CYCLE_ALLOWED` / `TERMINAL_LOCKED_FOR_SYMBOL`, plus the actual
MT4 EA/terminal writing receipt JSON into the mailbox.

2026-06-24 fourth follow-up status update: receipt-aware overseer routing is
now implemented. The latest default workflow cycle
`agent-cycle-44848f2d3efc4669` rejected `2` AUD/CAD route intents and wrote `0`
new terminal commands because `28` prior AUD/CAD terminal commands are still
waiting for receipts/reconciliation. The event journal now has `459` events
across `31` cycles, with `28` terminal commands written and `28` pending
receipts. Latest cycle report:
`cas-forex\evidence_runs\agent_workflow_queue\agent-workflow-cycle-20260624090733-report.json`.
Latest terminal receipt ingest report:
`cas-forex\evidence_runs\terminal_receipt_ingest\terminal-receipt-ingest-20260624090739-report.json`.
Latest information-flow report:
`cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624085546-report.json`.
The next MT4/agentic workflow lane is now the actual MT4 EA bridge:
`mt4\Experts\CASForexBridgeEA.mq4` must read mailbox command JSON and write
real terminal receipt JSON from terminal state. After that, build
`cas_forex\agent_memory.py` so wins/losses, open/close conditions, MAE/MFE, and
lessons feed future strategy decisions.

2026-06-24 fifth follow-up status update: `mt4\Experts\CASForexBridgeEA.mq4`
source is now implemented as a mailbox worker. It creates mailbox folders,
writes heartbeat JSON, reads command JSON, parses `PING` and `PLACE_ORDER`,
acknowledges `PAPER_MT4` by writing `cas_forex_mt4_mailbox_receipt.v1`
receipts, includes request/response hashes and account snapshot fields, skips
already-receipted commands, and keeps `LIVE_MT4` behind both the EA
`LiveTradingAllowed` input and command-level `live_money_authorized`.
Verification in this session is source/contract/API level, not a terminal
compile: targeted MT4/receipt/info-flow tests passed as `14 passed`, full CAS
Forex suite passed as `408 passed`, and UI build passed. Latest information
flow report:
`cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624091707-report.json`.
The next code lane is now `cas_forex\agent_memory.py`; the remaining terminal
 lane is to compile/attach/run the EA inside a real MT4 terminal against the
shared mailbox and then ingest the generated receipt JSON.

2026-06-24 sixth follow-up status update: `cas_forex\agent_memory.py` is now
implemented and surfaced in the API/UI. It writes
`cas_forex_agent_outcome_memory.v1` rows by joining route intents, overseer
decisions, terminal commands, and any available terminal receipts. Latest memory
report:
`cas-forex\evidence_runs\agent_memory\agent-memory-20260624093213-report.json`.
Current memory summary is `62` records: `28` approved command rows waiting for
terminal receipts, `34` rejected-route rows ready for research, `28` commands
joined, and `0` receipts joined because the actual MT4 terminal has not yet
produced receipt files for those commands. Latest information-flow report:
`cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624093253-report.json`.
The next code lane is now `cas_forex\agent_research_queue.py`; the remaining
terminal lane is still compile/attach/run `CASForexBridgeEA.mq4` in MT4 and
then rerun receipt ingest plus memory so terminal receipts and close/history
data become learning rows.

2026-06-24 seventh follow-up status update:
`cas_forex\agent_research_queue.py` is now implemented and surfaced in the
API/UI. It converts the latest `62` memory rows into `6` queued research tasks:
`1` terminal receipt joinback task, `1` overseer conflict-key refinement task,
`2` condition-lab rejection analysis tasks, `1` walk-forward receipt replay
task, and `1` terminal history/PnL schema task. Latest queue report:
`cas-forex\evidence_runs\agent_research_queue\agent-research-queue-20260624095304-report.json`.
Latest information-flow report:
`cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624095004-report.json`.
The next code lane is now `cas_forex\terminal_history_ingest.py`; the remaining
 terminal lane is still compile/attach/run `CASForexBridgeEA.mq4` in MT4 and
then rerun receipt ingest, memory, and research queue.

2026-06-24 eighth follow-up status update:
`cas_forex\terminal_history_ingest.py` is now implemented and surfaced in the
API/UI. It normalizes MT4/MT5 closed-history exports, joins rows back to agent
memory by `command_id`, `receipt_id`, broker ticket, or symbol/direction/lot
fallback, and can enrich memory with closed PnL, pips, R multiple, MAE/MFE,
close reason, commission, swap, close time, and exit price. Latest terminal
history report:
`cas-forex\evidence_runs\terminal_history_ingest\terminal-history-ingest-20260624101300-report.json`.
Current status is `TERMINAL_HISTORY_EMPTY`: `0` history rows, `0` memory
updates, `0` closed trades, and `0` net PnL because no MT4/MT5 closed-history
export has been placed under `cas-forex\evidence_runs\terminal_history_exports`
yet. Latest memory report:
`cas-forex\evidence_runs\agent_memory\agent-memory-20260624101307-report.json`
with `62` memory rows, `28` pending terminal receipts, `0` receipts joined, and
`0` terminal-history rows joined. Latest information-flow report:
`cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624101117-report.json`.
The next code lane is now `cas_forex\strategy_dev_queue.py`; the remaining
terminal lane is still compile/attach/run `CASForexBridgeEA.mq4` in MT4,
generate receipt JSON, export or ingest closed account history, then rerun
receipt ingest, terminal-history ingest, memory, and research queue.

2026-06-24 ninth follow-up status update:
`cas_forex\strategy_dev_queue.py` is now implemented and surfaced in the
API/UI. It converts the latest research queue and available agent memory into
`6` strategy-development work items: terminal joinback, terminal history
contract work, condition-lab replay requests, walk-forward terminal replay, and
one overseer rule patch candidate. Latest strategy-dev queue report:
`cas-forex\evidence_runs\strategy_dev_queue\strategy-dev-queue-20260624102900-report.json`.
Current status is `STRATEGY_DEV_QUEUE_BUILT`: `3` queued items, `3` blocked
items, `3` ready-for-replay items, `1` patch candidate, and next item
`strategy-dev-terminal-joinback-7c441e3221a2bdce`. Latest information-flow
report:
`cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624102906-report.json`.
The next code lane is now `cas_forex\strategy_patch_runner.py`; the remaining
terminal lane is still compile/attach/run `CASForexBridgeEA.mq4` in MT4,
generate receipt JSON, export or ingest closed account history, then rerun
receipt ingest, terminal-history ingest, memory, research queue, and
strategy-dev queue.

2026-06-24 tenth follow-up status update:
`cas_forex\strategy_patch_runner.py` is now implemented and surfaced in the
API/UI. It converts `6` strategy-development work items into `6`
patch/replay decisions: `1` patch candidate, `3` replay jobs, and `2`
terminal-input-required blockers. Latest strategy patch-runner report:
`cas-forex\evidence_runs\strategy_patch_runner\strategy-patch-runner-20260624104622-report.json`.
Current status is `STRATEGY_PATCH_RUNNER_READY`: `3` ready decisions, `3`
blocked decisions, and next decision
`strategy-patch-terminal_joinback_blocker-b734b40a97a7028d`. Latest
information-flow report:
`cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624104623-report.json`.
The next code lane is now `cas_forex\daily_learning_rollup.py`; the remaining
terminal lane is still compile/attach/run `CASForexBridgeEA.mq4` in MT4,
generate receipt JSON, export or ingest closed account history, then rerun
receipt ingest, terminal-history ingest, memory, research queue,
strategy-dev queue, and patch runner.

2026-06-24 eleventh follow-up status update:
`cas_forex\daily_learning_rollup.py` is now implemented and surfaced in the
API/UI. It summarizes the 30-day improvement day by route, agent, symbol,
strategy, condition cell, PnL, queued follow-up work, patch decisions, and
terminal blockers. Latest daily rollup report:
`cas-forex\evidence_runs\daily_learning_rollup\daily-learning-rollup-20260624110228-report.json`.
Current status is `DAILY_LEARNING_ROLLUP_BUILT_WAITING_FOR_CLOSED_PNL`: `62`
routes, `28` approved, `34` rejected, `28` pending receipts, `0` closed trades,
`0` net PnL, `1` patch candidate, and `3` replay jobs. Latest information-flow
report:
`cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624110229-report.json`.
At that point, the next code lane became `cas_forex\session_autowake_runner.py`.
That lane is now completed by the twelfth update below. The remaining terminal
lane is still compile/attach/run `CASForexBridgeEA.mq4` in MT4, generate
receipt JSON, export or ingest closed account history, then rerun receipt
ingest, terminal-history ingest, memory, research queue, strategy-dev queue,
patch runner, daily rollup, and session autowake.

2026-06-24 twelfth follow-up status update:
`cas_forex\session_autowake_runner.py` is now implemented and surfaced in the
API/UI. It evaluates market-open state, active forex session, due wake events,
daily rollup readiness, pending terminal receipts, and terminal blockers before
requesting any agent-loop cycle. Latest session autowake report:
`cas-forex\evidence_runs\session_autowake_runner\session-autowake-20260624111809-report.json`.
Current deterministic status at `2026-06-24T13:00:00+00:00` is
`SESSION_AUTOWAKE_READY`: active session `LONDON_NEW_YORK_OVERLAP`, `7` wake
events evaluated, `2` due, `2` executable, `0` executed cycles, `28` pending
receipts, `5` terminal blockers, and next due event `MICRO_SCALP_LOOP`. Latest
information-flow report:
`cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624111808-report.json`.
At that point, the next code lane became `cas_forex\terminal_receipt_watcher.py`.
That lane is now completed by the thirteenth update below. The remaining
terminal lane is still compile/attach/run `CASForexBridgeEA.mq4` in MT4,
generate receipt JSON, export or ingest closed account history, then rerun
receipt ingest, terminal-history ingest, memory, research queue, strategy-dev
queue, patch runner, daily rollup, and session autowake.

2026-06-24 thirteenth follow-up status update:
`cas_forex\terminal_receipt_watcher.py` is now implemented and surfaced in the
API/UI. It fingerprints MT4/MT5 receipt and history folders, detects terminal
file changes, and can rerun receipt ingest, history ingest, memory, research
queue, strategy-dev queue, patch runner, daily rollup, and session autowake
when terminal files arrive. Latest watcher report:
`cas-forex\evidence_runs\terminal_receipt_watcher\terminal-receipt-watcher-20260624113653-report.json`.
Current status is `WATCHER_IDLE_NO_TERMINAL_FILES`: `0` terminal files, `0`
receipt files, `0` history files, `0` changed files, and `0` chain steps
because the actual MT4/MT5 terminal has not yet written receipt JSON or
closed-history exports into the watched folders. Latest information-flow
report:
`cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624113652-report.json`.
At that point, the next code lane became `cas_forex\terminal_bridge_supervisor.py`.
That lane is now completed by the fourteenth update below. The remaining
terminal lane is still compile/attach/run `CASForexBridgeEA.mq4` in MT4,
generate receipt JSON, export or ingest closed account history, then rerun the
watcher and the ingest-memory-queue-rollup-autowake chain.

2026-06-24 fourteenth follow-up status update:
`cas_forex\terminal_bridge_supervisor.py` is now implemented and surfaced in
the API/UI. It observes heartbeat, mailbox folders, command files, receipt
files, close-history exports, account snapshot presence, visible live flag
state, event-journal pending receipts, and terminal-run alerts. Latest
supervisor report:
`cas-forex\evidence_runs\terminal_bridge_supervisor\terminal-bridge-supervisor-20260624115153-report.json`.
Current status is `TERMINAL_BRIDGE_HEARTBEAT_MISSING`: mailbox folders are
present and `39` command files exist, but `heartbeat.json` is missing, receipt
files are `0`, pending command receipts are `39`, event-journal pending
receipts are `28`, history exports are `0`, account snapshot present is
`false`, visible live flag is `false`, and alert count is `5`. Latest
information-flow report:
`cas-forex\evidence_runs\agent_information_flow\agent-information-flow-20260624115151-report.json`.
The next code lane is now `cas_forex\mt4_terminal_activation.py`; the
remaining terminal lane is to discover/stage the real MT4 terminal data folder,
copy or verify `CASForexBridgeEA.mq4` under `MQL4\Experts`, attach it inside
MT4 with `MailboxRoot` pointed at the shared mailbox, then rerun the watcher,
supervisor, and ingest-memory-queue-rollup-autowake chain.

## Public Benchmark Snapshot

Source pages reviewed:

- `https://www.myfxbook.com/members/forexfuryreal/forex-fury-au/11171494`
- `https://www.myfxbook.com/members/forexfuryreal/forex-fury-usdcad-50k/9421542`
- `https://www.myfxbook.com/members/forexfuryreal/forex-fury-26amp39/11975493`
- `https://www.myfxbook.com/api`

Important public-page limitation: the public pages expose summary statistics,
period stats, and advanced-stat summary rows. They show that deeper data is
private and open trades are private. Use the pages as benchmark evidence, not
as a full trade-history source.

### Forex FURY AU

- Public Myfxbook id: `11171494`
- Public page type: Real USD, Fyntura, Technical, Automated, 1:500, MetaTrader 4
- Visible symbol filter: `AUDUSD`
- Gain: `+214.03%`
- Abs gain: `+214.03%`
- Daily: `0.18%`
- Monthly: `5.79%`
- Drawdown: `35.77%`
- Balance/equity: `$31,402.50`
- Deposits: `$10,000.00`
- Profit: `$21,402.50`
- Trades: `43`
- Pips: `227.4`
- Average win: `5.29 pips / $497.73`
- Average loss: `0 pips / $0.00`
- Lots: `430.00`
- Commissions: `-$860.00`
- Longs won: `23/23`, `100%`
- Shorts won: `20/20`, `100%`
- Average trade length: `13h 30m`
- Expectancy: `5.3 pips / $497.73`

### Forex Fury USDCAD 50K

- Public Myfxbook id: `9421542`
- Public page type: Real USD, AdroFx, Technical, Automated, 1:200, MetaTrader 4
- Visible symbol filter: `USDCAD`
- Gain: `+154.62%`
- Abs gain: `+154.61%`
- Daily: `0.06%`
- Monthly: `2.46%`
- Drawdown: `8.60%`
- Balance/equity: `$129,040.09`
- Deposits: `$50,681.13`
- Profit: `$78,358.96`
- Trades: `541`
- Pips: `2,912.6`
- Average win: `6.12 pips / $169.78`
- Average loss: `-11.28 pips / -$416.80`
- Longs won: `301/316`, `95%`
- Shorts won: `217/225`, `96%`
- Average trade length: `23h 23m`
- Profit factor: `9.17`
- Expectancy: `5.4 pips / $144.84`

### Forex FURY 26'

- Public Myfxbook id: `11975493`
- Public page type: Real USD, Fyntura, Technical, Automated, 1:500, MetaTrader 4
- Visible symbol filter: `GBPUSD`
- Gain: `+554.10%`
- Abs gain: `+554.13%`
- Daily: `0.54%`
- Monthly: `18.19%`
- Drawdown: `37.00%`
- Balance/equity: `$19,623.84`
- Deposits: `$3,000.00`
- Profit: `$16,623.84`
- Trades: `62`
- Pips: `860.1`
- Average win: `14.19 pips / $277.67`
- Average loss: `4.45 pips / -$18.10` as displayed publicly
- Lots: `124.00`
- Longs won: `30/32`, `93%`
- Shorts won: `30/30`, `100%`
- Average trade length: `1d`
- Profit factor: `460.22`
- Expectancy: `13.9 pips / $268.13`

## What This Should Add To CAS Forex

## Implementation Status

2026-06-24 first build slice complete:

- Added `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\external_benchmark.py`
- Added `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_external_benchmark_snapshot.py`
- Added `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_external_benchmark.py`
- Added API route `/api/forex/strategy/external-benchmarks`
- Added dashboard payload key `externalBenchmarks`
- Added TypeScript types/API client/fixture fallback
- Added Optimizer page external benchmark table

Verification:

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

Still not implemented:

- MQL4 EA command parser/order-send implementation
- MT4 receipt/probe runner
- MT4 terminal-health selector
- Persistent agent state store
- Autowake runner
- Micro-scalp and hourly intraday policies
- Overseer router
- Long-horizon multi-agent execution loop

2026-06-24 second build slice complete:

- Added `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\broker\mt4_mailbox_bridge.py`
- Added `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_mt4_mailbox_smoke.py`
- Added `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_mt4_mailbox_bridge.py`
- Added `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\mt4\Experts\CASForexBridgeEA.mq4`
- Updated `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\broker\__init__.py`
- Smoke wrote `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\mt4_mailbox_smoke\mt4-mailbox-smoke-status.json`

Verification:

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

2026-06-24 third build slice complete:

- Inspected local owner-supplied package
  `C:\Users\wakil\Downloads\Forex-Fury-CORE-1.4NEW-SETS (1)` without executing
  compiled EA binaries.
- Added `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\forex_fury_sets.py`
- Added `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_forex_fury_set_import.py`
- Added `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_forex_fury_sets.py`
- Added API route `/api/forex/strategy/forex-fury-set-import`
- Generated:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\forex_fury_set_import\forex-fury-set-import-20260624034719-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\forex_fury_set_import\forex-fury-set-import-20260624034719-report.md`

Local package extraction summary:

- `36` set files
- `30` tester reports
- `18` MT4 sets and `18` MT5 sets
- families: `14` scalping, `16` swing, `6` classic M15
- symbols: `AUDCAD`, `AUDUSD`, `EURUSD`, `GBPAUD`, `GBPUSD`, `SPX500`, `USDJPY`
- timeframes: `M1`, `M5`, `M15`, `H1`
- `30` grid-enabled sets
- `30` close-all-by-money sets
- max orders observed: `1` and `7`
- best supplied tester-report signal: `AUDCAD` `M5`, `04:00:00-05:00:00`,
  `profit_factor=15.12`, `equity_drawdown_relative_pct=2.25`,
  `total_net_profit=21982.6`, `total_trades=294`

Verification:

```text
python -m pytest tests/test_forex_fury_sets.py tests/test_external_benchmark.py -q
# 4 passed

python scripts/run_forex_fury_set_import.py --source-dir "C:\Users\wakil\Downloads\Forex-Fury-CORE-1.4NEW-SETS (1)" --summary-only
# set_count=36, tester_report_count=30, best_profit_factor=15.12
```

Boundary: this local import reads `.set` and tester-report files and
fingerprints `.ex4`/`.ex5` binaries only. It does not execute EA binaries,
place orders, create broker `ACCEPT`, deposit, withdraw, move bank/card money,
or automate payouts.

2026-06-24 fourth build slice complete:

- Surfaced the local Forex Fury set/report import inside the Optimizer UI and
  dashboard API.
- Updated `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\api\data.py`
  so `/api/forex/dashboard` includes `forexFurySetImport`.
- Updated `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\types\evidence.ts`
  with Forex Fury import/report TypeScript types.
- Updated `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\api.ts`
  with the `/strategy/forex-fury-set-import` client and dashboard merge
  fallback.
- Updated `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\data\fixtures.ts`
  and `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\App.tsx`
  with fixture fallback data.
- Updated `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\OptimizerPage.tsx`
  with the Local Forex Fury Set Import panel.

Live local smoke:

```text
http://127.0.0.1:8774/api/forex/strategy/forex-fury-set-import
# set_count=36, tester_report_count=30, best_profit_factor=15.12

http://127.0.0.1:8774/api/forex/dashboard
# forexFurySetImport present, best_profit_factor=15.12

http://127.0.0.1:5184/?page=optimizer
# HTTP 200
```

Verification:

```text
python -m pytest tests/test_forex_fury_sets.py tests/test_external_benchmark.py -q
# 4 passed

python -m pytest tests -q
# 379 passed

cd ui && npm run build
# 51 modules, 333.31 KB JS, 90.09 KB gzip
```

Previous next lane to convert imported Forex Fury set parameters into CAS
backtest/replay candidates is now complete. The remaining lane is to run the
generated replay jobs and compare their outputs against CAS condition buckets,
compounding rules, and MT4 paper/demo receipt evidence.

2026-06-24 fifth build slice complete:

- Converted the imported Forex Fury set/report evidence into CAS replay and
  backtest candidate jobs.
- Added `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\forex_fury_candidates.py`
- Added `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_forex_fury_replay_candidates.py`
- Added `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_forex_fury_candidates.py`
- Expanded `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\instruments.py`
  with `AUD/CAD`, `GBP/AUD`, and `SPX500`.
- Added API route `/api/forex/strategy/forex-fury-replay-candidates`
- Added dashboard payload key `forexFuryReplayCandidates`
- Added the Optimizer page `Forex Fury Replay Candidates` panel.
- Generated:
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\forex_fury_replay_candidates\forex-fury-replay-candidates-20260624040820-report.json`
  - `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\forex_fury_replay_candidates\forex-fury-replay-candidates-20260624040820-report.md`

Replay queue summary:

- `candidate_count=24`
- `supported_candidate_count=24`
- `waiting_for_instrument_spec_count=0`
- symbols: `AUD/CAD`, `AUD/USD`, `GBP/AUD`, `GBP/USD`, `SPX500`, `USD/JPY`
- timeframes: `H1`, `M1`, `M5`
- top candidate: `ff-replay-aud-cad-m5-swing-d7be2c38ca`
- top score: `320.9726`

Live local smoke:

```text
http://127.0.0.1:8776/api/forex/strategy/forex-fury-replay-candidates
# candidate_count=24, supported_candidate_count=24

http://127.0.0.1:8776/api/forex/dashboard
# forexFuryReplayCandidates present

http://127.0.0.1:5186/?page=optimizer
# HTTP 200; browser DOM confirms Forex Fury Replay Candidates panel
```

Verification:

```text
python -m pytest tests/test_forex_fury_candidates.py tests/test_forex_fury_sets.py tests/test_external_benchmark.py tests/test_pip_math_regressions.py -q
# 18 passed

python -m pytest tests -q
# 383 passed

cd ui && npm run build
# 51 modules, 341.36 KB JS, 91.97 KB gzip
```

Next implementation lane: run the generated condition-lab and walk-forward
replay commands for top-ranked candidates, starting with
`ff-replay-aud-cad-m5-swing-d7be2c38ca`, and then feed replay winners into
adaptive compounding policy plus MT4 paper/demo receipt evidence.

### 1. External Benchmark Ingestion

Goal: let CAS Forex store outside reference systems and compare CAS candidates
against them.

Files to add or modify:

- Add `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\external_benchmark.py`
- Add `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_external_benchmark_snapshot.py`
- Add `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_external_benchmark.py`
- Optionally add `/api/forex/strategy/external-benchmarks`
- Optionally surface on Dashboard, Optimizer, and Condition Lab pages

Needed data model:

- Benchmark id
- Source URL
- Source kind: `PUBLIC_PAGE_SNAPSHOT`, `MYFXBOOK_API`, `CSV_EXPORT`, `MT4_HTML_REPORT`, `MT5_HTML_REPORT`
- Broker/platform: MT4/MT5, broker name, leverage
- Account kind: real/demo if visible
- Symbol focus
- Gain, monthly return, drawdown, deposit, balance, profit
- Trade count, pips, average win/loss, long/short win rates
- Average trade length
- Public-data limitations
- CAS candidate comparison fields

CAS use:

- Compare CAS strategy leads to outside benchmark profiles.
- Mine useful shape targets: single-symbol specialization, high win rate,
  small average pip capture, long/short symmetry, session timing, average trade
  length, and drawdown-return ratio.
- Feed optimizer proposals into `CASPCBAOptimizerGuard` as research requests.

### 2. MT4 Bridge Buildout

Current code already has MT4 hints:

- `ForexConfig.mt4_enabled`
- `ForexConfig.mt4_mailbox_dir`
- `BrokerMode.PAPER_MT4`
- `BrokerMode.LIVE_MT4`

Missing implementation:

- No real `cas_forex/broker/mt4_mailbox_bridge.py`
- No MQL4 bridge EA template
- No MT4 receipt/probe equivalent to the MT5 receipt path
- No UI/API terminal selector that compares MT4 and MT5 current health

Recommended bridge shape:

- CAS writes signed order intents into an MT4 mailbox directory.
- An MQL4 Expert Advisor reads the mailbox from MetaTrader 4.
- The EA writes account snapshots, open positions, order outcomes, and history
  receipts back to an outbox directory.
- CAS hashes every request/receipt pair and appends evidence.
- Paper/demo mode should be implemented first.
- Live mode should use the same order schema after owner runtime flags,
  broker credentials, proof maturity, and broker/account checks are satisfied.

Suggested paths:

- `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\broker\mt4_mailbox_bridge.py`
- `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\mt4\Experts\CASForexBridgeEA.mq4`
- `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_mt4_paper_receipt.py`
- `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_mt4_mailbox_smoke.py`
- `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_mt4_mailbox_bridge.py`

### 3. Myfxbook/API/Export Ingestion

Official Myfxbook API notes that matter:

- The API can access account data programmatically.
- It has methods for my accounts, watched accounts, open trades, open orders,
  history, daily gain, gain between dates, and daily data.
- Official docs say API access is for personal information.
- Official docs say `get-history` is limited to the last 50 transactions.

Therefore:

- Use public pages as public benchmark snapshots.
- Use Myfxbook API only for accounts available through the owner's own login or
  watched-account permissions.
- For full historical strategy study, prefer exported CSV/PDF/HTML files when
  available, or direct MT4/MT5 broker terminal history exports.

### 4. Long-Horizon Multi-Agent Workflow

This should be added to CAS Harness because CAS Forex needs long-running,
parallel work that a single short LLM turn will not carry well.

Recommended agent roles:

- Evidence Harvester: pulls broker exports, MT4/MT5 receipts, Myfxbook snapshots,
  daily proof bundles, and market condition data.
- Strategy Miner: proposes symbol/session/condition families to test.
- Backtest Runner: executes simulator, walk-forward, and condition-tally jobs.
- Risk/Margin Solver: tests lot sizing, leverage, concurrent trades, drawdown,
  margin, and compounding plans.
- Terminal Bridge Engineer: builds and verifies MT4/MT5 bridge paths.
- UI Cockpit Engineer: surfaces owner controls, live movement, market movement,
  history, benchmark comparison, and agent queue state.
- Audit Verifier: checks claims, evidence hashes, chain continuity, and exact
  readiness state.

Needed workflow rules:

- Every spawned agent needs a goal id, owner objective, evidence refs, allowed
  files, max runtime, output schema, and handoff summary.
- Agents can generate code, tests, reports, and research proposals.
- Order placement still flows through CAS Forex runtime execution. The agent
  workflow should speed buildout and analysis, not create hidden execution paths.
- Store agent outputs as evidence packets or handoff notes so future agents do
  not lose context.

Suggested paths:

- `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_workflow.py`
- `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_agent_workflow_queue.py`
- `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_agent_workflow.py`
- `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\ui\src\pages\OptimizerPage.tsx`

2026-06-24 agent workflow plan slice complete:

- Added `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\cas_forex\agent_workflow.py`
- Added `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\scripts\run_agent_workflow_plan.py`
- Added `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\tests\test_agent_workflow.py`
- Added API route `/api/forex/strategy/agent-workflow-plan`
- Added dashboard payload key `agentWorkflowPlan`
- Added Optimizer page `Agentic Trading-Day Workflow` panel
- Generated `C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex\evidence_runs\agent_workflow\agent-workflow-plan-20260624044500-report.json`

Current workflow status:

- `workflow_status=AGENT_DESK_PLAN_READY`
- `agent_count=8`
- `micro_scalp_cadence_minutes=1-5`
- `hourly_intraday_cadence_minutes=60`
- primary replay lead: `AUD/CAD M5 range_scalper_12_80`
- next build target: persistent agent state, autowake runner, micro-scalp
  policy, hourly intraday policy, overseer router, and terminal receipt
  attachment.

Verification:

```text
python -m pytest tests/test_agent_workflow.py tests/test_forex_fury_replay_results.py -q
# 5 passed

python -m pytest tests -q
# 388 passed

cd ui && npm run build
# 51 modules, 364.08 KB JS, 97.89 KB gzip
```

## Priority Order

1. Add external benchmark snapshot model and report runner.
2. Add MT4 mailbox bridge in paper/demo mode.
3. Add MT4 receipt/probe to the existing proof cockpit.
4. Add benchmark comparison panel to Optimizer/Condition Lab.
5. Add persistent agent state and the autowake execution runner.
6. Add micro-scalp, hourly intraday, and overseer policies.
7. Connect agents to run benchmark-driven strategy experiments.
8. Continue the daily paper/demo proof window until the 30-day gate is complete.

## Plain-English Metaphor Map

- External benchmark: a scoreboard from another team.
- MT4 bridge: a courier between CAS Forex and MetaTrader 4.
- Mailbox directory: the drop box where CAS leaves instructions and MT4 leaves receipts.
- Myfxbook API/export: a bank-style statement feed for trading statistics.
- Agent workflow: a crew assignment board where each LLM worker has one job and must leave receipts.
- Evidence chain: the paper trail proving what happened and when.

## Current Claim Boundary

This note does not make CAS Forex live-ready by itself. It adds implementation
targets for benchmark study, MT4 support, and long-horizon agent workflow.
Live trading, broker `ACCEPT`, auto-deposit, debit/card/bank movement, and
payout automation remain `NOT LICENSED` / `CURRENTLY NOT LICENSED` until the
actual runtime, broker, account, proof, and payment requirements are completed.
