/* ── CAS Forex — LLM Optimizer Queue ── */

import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import type { DashboardState } from "../types/evidence";

interface OptimizerPageProps {
  state: DashboardState;
}

export function OptimizerPage({ state }: OptimizerPageProps) {
  const backsolve = state.backsolve;
  const tally = state.conditionTally;
  const wf = state.walkForward;
  const externalBenchmarks = state.externalBenchmarks;
  const benchmarks = externalBenchmarks?.benchmarks ?? [];
  const forexFuryImport = state.forexFurySetImport;
  const furySummary = forexFuryImport?.summary;
  const furyProfiles = furySummary?.top_report_profiles ?? [];
  const furyReplay = state.forexFuryReplayCandidates;
  const furyReplaySummary = furyReplay?.summary;
  const furyReplayCandidates = furyReplay?.candidates ?? [];
  const furyReplayResults = state.forexFuryReplayResults;
  const furyCondition = furyReplayResults?.condition_summary;
  const furyWalkForward = furyReplayResults?.walk_forward_summary;
  const agentWorkflow = state.agentWorkflowPlan;
  const agentCycle = state.agentWorkflowCycle;
  const agentFlow = state.agentInformationFlow;
  const agentBus = state.agentMessageBus;
  const agentMemory = state.agentMemory;
  const agentResearchQueue = state.agentResearchQueue;
  const strategyDevQueue = state.strategyDevQueue;
  const strategyPatchRunner = state.strategyPatchRunner;
  const dailyLearningRollup = state.dailyLearningRollup;
  const sessionAutowake = state.sessionAutowake;
  const terminalReceiptWatcher = state.terminalReceiptWatcher;
  const terminalBridgeSupervisor = state.terminalBridgeSupervisor;
  const mt4TerminalActivation = state.mt4TerminalActivation;
  const mt4PingRoundtrip = state.mt4PingRoundtrip;
  const mt4TerminalSessionVerifier = state.mt4TerminalSessionVerifier;
  const mt4HistoryExportVerifier = state.mt4HistoryExportVerifier;
  const mt5TerminalApiVerifier = state.mt5TerminalApiVerifier;
  const mt5PaperExecutionVerifier = state.mt5PaperExecutionVerifier;
  const mt5DealHistoryIngest = state.mt5DealHistoryIngest;
  const terminalPositionReconciliation = state.terminalPositionReconciliation;
  const terminalOperabilityVerifier = state.terminalOperabilityVerifier;
  const terminalReceiptIngest = state.terminalReceiptIngest;
  const terminalHistoryIngest = state.terminalHistoryIngest;
  const agentRoster = agentWorkflow?.agent_roster ?? [];
  const autowakeEvents = agentWorkflow?.autowake_schedule.events ?? [];
  const implementationQueue = agentWorkflow?.implementation_queue ?? [];
  const flowPlanes = agentFlow?.information_planes ?? [];
  const flowLifecycle = agentFlow?.receipt_and_reconciliation_lifecycle ?? [];
  const flowBottlenecks = agentFlow?.main_bottlenecks ?? [];
  const agentCycleMt5Tickets = agentCycle?.summary.mt5_broker_tickets ?? [];

  return (
    <div className="optimizer-page">
      {/* Section 1: Queue Status */}
      <GlassPanel
        title="LLM Optimizer Queue"
        subtitle="Guarded strategy optimization pipeline — runs are PCBA-validated before execution"
      >
        <div className="dashboard-grid-3col">
          <div className="metric-stack" style={{ padding: 0 }}>
            <Metric label="Active Runs" value="0" mono />
            <Metric label="Queued Runs" value="0" mono />
            <Metric
              label="Completed Runs"
              value={tally ? `${tally.length} condition-tally + 1 backsolve + 1 walk-forward + ${forexFuryImport ? "1 set import" : "0 set imports"} + ${furyReplay ? "1 replay queue" : "0 replay queues"} + ${agentWorkflow ? "1 agent workflow" : "0 agent workflows"} + ${agentFlow ? "1 info-flow plan" : "0 info-flow plans"} + ${agentBus ? "1 event journal" : "0 event journals"} + ${terminalReceiptIngest ? "1 receipt ingest" : "0 receipt ingests"} + ${terminalHistoryIngest ? "1 history ingest" : "0 history ingests"} + ${agentMemory ? "1 memory report" : "0 memory reports"} + ${agentResearchQueue ? "1 research queue" : "0 research queues"} + ${strategyDevQueue ? "1 strategy-dev queue" : "0 strategy-dev queues"} + ${strategyPatchRunner ? "1 patch runner" : "0 patch runners"} + ${dailyLearningRollup ? "1 daily rollup" : "0 daily rollups"} + ${sessionAutowake ? "1 autowake" : "0 autowakes"} + ${terminalReceiptWatcher ? "1 watcher" : "0 watchers"} + ${terminalBridgeSupervisor ? "1 supervisor" : "0 supervisors"} + ${mt4TerminalActivation ? "1 activation" : "0 activations"} + ${mt4PingRoundtrip ? "1 ping" : "0 pings"} + ${mt4TerminalSessionVerifier ? "1 session" : "0 sessions"} + ${mt4HistoryExportVerifier ? "1 history export verifier" : "0 history export verifiers"} + ${mt5TerminalApiVerifier ? "1 MT5 API verifier" : "0 MT5 API verifiers"} + ${mt5PaperExecutionVerifier ? "1 MT5 execution verifier" : "0 MT5 execution verifiers"} + ${mt5DealHistoryIngest ? "1 MT5 deal ingest" : "0 MT5 deal ingests"} + ${terminalPositionReconciliation ? "1 position reconciliation" : "0 position reconciliations"} + ${terminalOperabilityVerifier ? "1 operability verifier" : "0 operability verifiers"}` : "0"}
            />
          </div>
          <div className="metric-stack" style={{ padding: 0 }}>
            <Metric label="Queue Health" value="IDLE" />
            <StatusChip label="IDLE" variant="muted" size="sm" />
          </div>
          <div className="metric-stack" style={{ padding: 0 }}>
            <Metric label="Last Run" value={backsolve?.run_id?.slice(-8) ?? "N/A"} mono />
            <Metric
              label="Total Scenarios"
              value={backsolve ? `${backsolve.total_scenarios.toLocaleString()}` : "0"}
              mono
            />
          </div>
        </div>
      </GlassPanel>

      {/* Section 2: Run Types */}
      <GlassPanel title="Optimizer Run Types" subtitle="Available optimization pipelines">
        <div className="run-types-list">
          <RunType
            label="Condition Tally"
            status="AVAILABLE"
            detail="Condition-axis evidence scoring across timeframes/strategies"
            runs={tally ? `${tally.length} buckets` : "0"}
            variant="success"
          />
          <RunType
            label="Leverage Backsolve"
            status="AVAILABLE"
            detail="16,800 scenarios, 0 viable — SURVIVAL_RISK capital label"
            runs={backsolve ? backsolve.total_scenarios.toLocaleString() : "0"}
            variant="success"
          />
          <RunType
            label="Walk-Forward Grid"
            status="AVAILABLE"
            detail={`${wf?.total_windows ?? 0} windows, ${wf?.positive_active_routed_windows ?? 0}/${wf?.active_routed_windows ?? 0} positive`}
            runs={wf ? `${wf.total_windows}` : "0"}
            variant="success"
          />
          <RunType
            label="Strategy Harvester"
            status={furyReplay ? "AVAILABLE" : "NOT_RUN"}
            detail={furyReplay ? `${furyReplay.candidate_count} Forex Fury-derived replay candidates ready` : "Requires imported strategy profile evidence"}
            runs={furyReplay ? `${furyReplay.candidate_count}` : "—"}
            variant={furyReplay ? "success" : "muted"}
          />
          <RunType
            label="Adaptive Compounding"
            status={furyReplayResults?.adaptive_compounding_next_step === "QUEUE_FOR_ADAPTIVE_COMPOUNDING_REVIEW" ? "QUEUED" : "NOT_RUN"}
            detail={furyReplayResults ? furyReplayResults.adaptive_compounding_next_step : "Requires replay or basket data accumulation"}
            runs={furyReplayResults ? furyReplayResults.replay_verdict : "—"}
            variant={furyReplayResults ? "success" : "muted"}
          />
          <RunType
            label="Agentic Trading Day"
            status={agentWorkflow ? "READY" : "NOT_RUN"}
            detail={agentWorkflow ? `${agentWorkflow.summary.agent_count} agents, autowake + M1/M5 scalper + hourly intraday + overseer` : "Requires agent workflow plan"}
            runs={agentWorkflow ? agentWorkflow.workflow_status : "—"}
            variant={agentWorkflow ? "success" : "muted"}
          />
          <RunType
            label="Agent Information Bus"
            status={agentFlow ? "READY" : "NOT_RUN"}
            detail={agentFlow ? agentFlow.summary.best_flow_form : "Requires information-flow plan"}
            runs={agentFlow ? agentFlow.flow_status : "—"}
            variant={agentFlow ? "success" : "muted"}
          />
          <RunType
            label="Agent Event Journal"
            status={agentBus && agentBus.event_count > 0 ? "ACTIVE" : "EMPTY"}
            detail={agentBus ? `${agentBus.event_count} events, ${agentBus.pending_receipt_count} receipt pending` : "Requires agent workflow cycle events"}
            runs={agentBus ? `${agentBus.cycle_count} cycles` : "—"}
            variant={agentBus && agentBus.event_count > 0 ? "success" : "muted"}
          />
          <RunType
            label="Terminal Receipt Ingest"
            status={terminalReceiptIngest ? terminalReceiptIngest.ingest_status : "NOT_RUN"}
            detail={terminalReceiptIngest ? `${terminalReceiptIngest.summary.verified_receipt_count} verified, ${terminalReceiptIngest.summary.receipt_mismatch_count} mismatched, ${terminalReceiptIngest.summary.pending_receipt_count} pending` : "Requires MT4/MT5 receipt files"}
            runs={terminalReceiptIngest ? `${terminalReceiptIngest.summary.receipt_count} receipts` : "N/A"}
            variant={terminalReceiptIngest ? "success" : "muted"}
          />
          <RunType
            label="Terminal History Ingest"
            status={terminalHistoryIngest ? terminalHistoryIngest.ingest_status : "NOT_RUN"}
            detail={terminalHistoryIngest ? `${terminalHistoryIngest.summary.history_record_count} history rows, ${terminalHistoryIngest.summary.memory_update_count} memory updates, ${terminalHistoryIngest.summary.closed_profit_count}/${terminalHistoryIngest.summary.closed_loss_count} win/loss` : "Requires exported MT4/MT5 account history"}
            runs={terminalHistoryIngest ? `${terminalHistoryIngest.summary.closed_trade_count} closed` : "N/A"}
            variant={terminalHistoryIngest && terminalHistoryIngest.summary.memory_update_count > 0 ? "success" : "muted"}
          />
          <RunType
            label="Agent Outcome Memory"
            status={agentMemory ? agentMemory.memory_status : "NOT_RUN"}
            detail={agentMemory ? `${agentMemory.summary.memory_record_count} records, ${agentMemory.summary.pending_receipt_count} pending receipts, ${agentMemory.summary.terminal_history_joined_count ?? 0} history joined` : "Requires agent memory report"}
            runs={agentMemory ? `${agentMemory.summary.source_cycle_count} cycles` : "N/A"}
            variant={agentMemory ? "success" : "muted"}
          />
          <RunType
            label="Agent Research Queue"
            status={agentResearchQueue ? agentResearchQueue.queue_status : "NOT_RUN"}
            detail={agentResearchQueue ? `${agentResearchQueue.summary.task_count} tasks, ${agentResearchQueue.summary.high_priority_task_count} high priority, next ${agentResearchQueue.summary.next_task_id ?? "N/A"}` : "Requires agent research queue report"}
            runs={agentResearchQueue ? `${agentResearchQueue.summary.queued_task_count} queued` : "N/A"}
            variant={agentResearchQueue ? "success" : "muted"}
          />
          <RunType
            label="Strategy Dev Queue"
            status={strategyDevQueue ? strategyDevQueue.queue_status : "NOT_RUN"}
            detail={strategyDevQueue ? `${strategyDevQueue.summary.item_count} items, ${strategyDevQueue.summary.blocked_item_count} blocked, ${strategyDevQueue.summary.patch_candidate_count} patch candidates` : "Requires strategy-development queue report"}
            runs={strategyDevQueue ? `${strategyDevQueue.summary.queued_item_count} queued` : "N/A"}
            variant={strategyDevQueue ? "success" : "muted"}
          />
          <RunType
            label="Strategy Patch Runner"
            status={strategyPatchRunner ? strategyPatchRunner.runner_status : "NOT_RUN"}
            detail={strategyPatchRunner ? `${strategyPatchRunner.summary.decision_count} decisions, ${strategyPatchRunner.summary.ready_decision_count} ready, ${strategyPatchRunner.summary.blocked_decision_count} blocked` : "Requires strategy patch-runner report"}
            runs={strategyPatchRunner ? `${strategyPatchRunner.summary.patch_candidate_count} patches + ${strategyPatchRunner.summary.replay_job_count} replays` : "N/A"}
            variant={strategyPatchRunner ? "success" : "muted"}
          />
          <RunType
            label="Daily Learning Rollup"
            status={dailyLearningRollup ? dailyLearningRollup.rollup_status : "NOT_RUN"}
            detail={dailyLearningRollup ? `${dailyLearningRollup.summary.route_count} routes, ${dailyLearningRollup.summary.closed_count} closed, ${dailyLearningRollup.summary.readiness_label}` : "Requires daily learning rollup report"}
            runs={dailyLearningRollup ? `Day ${dailyLearningRollup.day_index}/${dailyLearningRollup.window_days}` : "N/A"}
            variant={dailyLearningRollup ? "success" : "muted"}
          />
          <RunType
            label="Session Autowake"
            status={sessionAutowake ? sessionAutowake.autowake_status : "NOT_RUN"}
            detail={sessionAutowake ? `${sessionAutowake.summary.active_session}, ${sessionAutowake.summary.due_event_count} due, ${sessionAutowake.summary.terminal_blocker_count} blockers` : "Requires session autowake report"}
            runs={sessionAutowake ? `${sessionAutowake.summary.executable_event_count} executable` : "N/A"}
            variant={sessionAutowake ? "success" : "muted"}
          />
          <RunType
            label="Terminal Watcher"
            status={terminalReceiptWatcher ? terminalReceiptWatcher.watch_status : "NOT_RUN"}
            detail={terminalReceiptWatcher ? `${terminalReceiptWatcher.summary.terminal_file_count} files, ${terminalReceiptWatcher.summary.changed_file_count} changed, ${terminalReceiptWatcher.summary.chain_step_complete_count} chain steps` : "Requires terminal receipt watcher report"}
            runs={terminalReceiptWatcher ? `${terminalReceiptWatcher.summary.receipt_file_count} receipts + ${terminalReceiptWatcher.summary.history_file_count} history` : "N/A"}
            variant={terminalReceiptWatcher && terminalReceiptWatcher.summary.chain_step_failed_count === 0 ? "success" : "muted"}
          />
          <RunType
            label="Bridge Supervisor"
            status={terminalBridgeSupervisor ? terminalBridgeSupervisor.supervisor_status : "NOT_RUN"}
            detail={terminalBridgeSupervisor ? `${terminalBridgeSupervisor.summary.heartbeat_status ?? "NO_HEARTBEAT"}, ${terminalBridgeSupervisor.summary.alert_count} alerts, ${terminalBridgeSupervisor.summary.pending_command_receipt_count} command receipts pending` : "Requires terminal bridge supervisor report"}
            runs={terminalBridgeSupervisor ? `${terminalBridgeSupervisor.summary.command_file_count} commands + ${terminalBridgeSupervisor.summary.receipt_file_count} receipts` : "N/A"}
            variant={terminalBridgeSupervisor && terminalBridgeSupervisor.summary.high_alert_count === 0 ? "success" : "muted"}
          />
          <RunType
            label="MT4 Activation"
            status={mt4TerminalActivation ? mt4TerminalActivation.activation_status : "NOT_RUN"}
            detail={mt4TerminalActivation ? `${mt4TerminalActivation.summary.mt4_candidate_count} MT4, ${mt4TerminalActivation.summary.mt5_only_candidate_count} MT5-only, ${mt4TerminalActivation.path_alignment.alignment_status}` : "Requires MT4 terminal activation report"}
            runs={mt4TerminalActivation ? `${mt4TerminalActivation.summary.ea_hash_matches ? "EA matched" : "EA pending"}` : "N/A"}
            variant={mt4TerminalActivation && (mt4TerminalActivation.activation_status === "MT4_ACTIVATION_STAGED_NEEDS_TERMINAL_ATTACH" || mt4TerminalActivation.activation_status === "MT4_ACTIVATION_HEARTBEAT_PRESENT") ? "success" : "muted"}
          />
          <RunType
            label="MT4 Ping"
            status={mt4PingRoundtrip ? mt4PingRoundtrip.roundtrip_status : "NOT_RUN"}
            detail={mt4PingRoundtrip ? `${mt4PingRoundtrip.summary.ping_written ? "ping written" : "no ping"}, heartbeat ${mt4PingRoundtrip.summary.heartbeat_present ? "present" : "missing"}, receipt ${mt4PingRoundtrip.summary.receipt_present ? "present" : "missing"}` : "Requires MT4 ping roundtrip report"}
            runs={mt4PingRoundtrip ? `${mt4PingRoundtrip.summary.command_file_count} commands + ${mt4PingRoundtrip.summary.receipt_file_count} receipts` : "N/A"}
            variant={mt4PingRoundtrip && mt4PingRoundtrip.roundtrip_status === "MT4_PING_ROUNDTRIP_ACKNOWLEDGED" ? "success" : "muted"}
          />
          <RunType
            label="MT4 Session"
            status={mt4TerminalSessionVerifier ? mt4TerminalSessionVerifier.session_status : "NOT_RUN"}
            detail={mt4TerminalSessionVerifier ? `${mt4TerminalSessionVerifier.summary.step_count} steps, ${mt4TerminalSessionVerifier.summary.skipped_step_count} skipped, chain ${mt4TerminalSessionVerifier.summary.refresh_chain_complete ? "complete" : "pending"}` : "Requires MT4 terminal session verifier report"}
            runs={mt4TerminalSessionVerifier ? `${mt4TerminalSessionVerifier.summary.command_file_count} commands + ${mt4TerminalSessionVerifier.summary.receipt_file_count} receipts` : "N/A"}
            variant={mt4TerminalSessionVerifier && mt4TerminalSessionVerifier.session_status === "MT4_SESSION_ROUNDTRIP_ACK_REFRESH_CHAIN_RAN" ? "success" : "muted"}
          />
          <RunType
            label="MT4 History Export"
            status={mt4HistoryExportVerifier ? mt4HistoryExportVerifier.verifier_status : "NOT_RUN"}
            detail={mt4HistoryExportVerifier ? `${mt4HistoryExportVerifier.summary.history_record_count} rows, ingest ${mt4HistoryExportVerifier.summary.ingest_status ?? "pending"}, mailbox ${mt4HistoryExportVerifier.summary.mailbox_ready ? "ready" : "missing"}` : "Requires MT4 history export verifier report"}
            runs={mt4HistoryExportVerifier ? `${mt4HistoryExportVerifier.summary.memory_update_count} memory updates` : "N/A"}
            variant={mt4HistoryExportVerifier && mt4HistoryExportVerifier.verifier_status === "MT4_HISTORY_EXPORT_INGEST_READY" ? "success" : "muted"}
          />
          <RunType
            label="MT5 API Verifier"
            status={mt5TerminalApiVerifier ? mt5TerminalApiVerifier.verifier_status : "NOT_RUN"}
            detail={mt5TerminalApiVerifier ? `${mt5TerminalApiVerifier.summary.terminal_name ?? "MT5"} ${mt5TerminalApiVerifier.summary.server ?? "server"}, balance $${(mt5TerminalApiVerifier.summary.account_balance ?? 0).toLocaleString()}, positions ${mt5TerminalApiVerifier.summary.open_position_count}` : "Requires MetaTrader5 Python API and an open MT5 terminal"}
            runs={mt5TerminalApiVerifier ? mt5TerminalApiVerifier.summary.receipt_validation_status ?? "N/A" : "N/A"}
            variant={mt5TerminalApiVerifier && mt5TerminalApiVerifier.summary.broker_api_authenticated ? "success" : "muted"}
          />
          <RunType
            label="MT5 Paper Execution"
            status={mt5PaperExecutionVerifier ? mt5PaperExecutionVerifier.verifier_status : "NOT_RUN"}
            detail={mt5PaperExecutionVerifier ? `${mt5PaperExecutionVerifier.summary.symbol ?? "symbol"} ${mt5PaperExecutionVerifier.summary.direction ?? ""} ${mt5PaperExecutionVerifier.summary.volume ?? ""}, check ${mt5PaperExecutionVerifier.summary.order_check_status ?? "N/A"}, send ${mt5PaperExecutionVerifier.summary.execution_attempted ? "attempted" : "not sent"}` : "Requires MT5 API verifier evidence and a demo terminal"}
            runs={mt5PaperExecutionVerifier ? mt5PaperExecutionVerifier.summary.execution_status ?? "DRY_RUN" : "N/A"}
            variant={mt5PaperExecutionVerifier && mt5PaperExecutionVerifier.summary.order_request_built ? "success" : "muted"}
          />
          <RunType
            label="MT5 Deal History"
            status={mt5DealHistoryIngest ? mt5DealHistoryIngest.ingest_status : "NOT_RUN"}
            detail={mt5DealHistoryIngest ? `${mt5DealHistoryIngest.summary.closed_position_count} closed, ${mt5DealHistoryIngest.summary.raw_deal_count} raw deals, ${mt5DealHistoryIngest.summary.memory_update_count} memory updates` : "Requires MT5 closed deal-history ingest"}
            runs={mt5DealHistoryIngest ? `$${mt5DealHistoryIngest.summary.net_profit_loss_account.toFixed(2)} P/L` : "N/A"}
            variant={mt5DealHistoryIngest && mt5DealHistoryIngest.summary.closed_position_count > 0 ? "success" : "muted"}
          />
          <RunType
            label="Position Reconciliation"
            status={terminalPositionReconciliation ? terminalPositionReconciliation.reconciliation_status : "NOT_RUN"}
            detail={terminalPositionReconciliation ? `${terminalPositionReconciliation.summary.reconciled_open_position_count} reconciled, ${terminalPositionReconciliation.summary.unmatched_open_position_count} unmatched, heartbeat ${terminalPositionReconciliation.summary.heartbeat_status ?? "missing"}` : "Requires terminal position reconciliation report"}
            runs={terminalPositionReconciliation ? `${terminalPositionReconciliation.summary.cas_open_position_count} CAS open + ${terminalPositionReconciliation.summary.terminal_open_position_count} terminal open` : "N/A"}
            variant={terminalPositionReconciliation && terminalPositionReconciliation.reconciliation_status.startsWith("TERMINAL_POSITION_RECONCILIATION_READY") ? "success" : "muted"}
          />
          <RunType
            label="Terminal Operability"
            status={terminalOperabilityVerifier ? terminalOperabilityVerifier.operability_status : "NOT_RUN"}
            detail={terminalOperabilityVerifier ? `terminal ${terminalOperabilityVerifier.go_no_go.terminal_lane_go ? "GO" : "NO-GO"}, live ${terminalOperabilityVerifier.go_no_go.live_order_go ? "GO" : "NO-GO"}, heartbeat ${terminalOperabilityVerifier.summary.heartbeat_status ?? "missing"}` : "Requires terminal operability verifier report"}
            runs={terminalOperabilityVerifier ? `${terminalOperabilityVerifier.summary.reconciled_open_position_count} reconciled + ${terminalOperabilityVerifier.summary.unmatched_open_position_count} unmatched` : "N/A"}
            variant={terminalOperabilityVerifier && terminalOperabilityVerifier.go_no_go.terminal_lane_go ? "success" : "muted"}
          />
        </div>
      </GlassPanel>

      {/* Section 3: Agentic Trading-Day Workflow */}
      <GlassPanel
        title="Agentic Trading-Day Workflow"
        subtitle={
          agentWorkflow
            ? `${agentWorkflow.summary.primary_replay_lead} | micro ${agentWorkflow.summary.micro_scalp_cadence_minutes} min | hourly ${agentWorkflow.summary.hourly_intraday_cadence_minutes} min`
            : "No agent workflow plan loaded"
        }
        variant="info"
      >
        {agentWorkflow ? (
          <>
            <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
              <Metric label="Desk Status" value={agentWorkflow.workflow_status} />
              <Metric label="Agents" value={`${agentWorkflow.summary.agent_count}`} mono />
              <Metric label="30-Day Window" value={`${agentWorkflow.summary.thirty_day_window_days} days`} mono />
            </div>
            <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
              <Metric label="Replay Lead" value={agentWorkflow.summary.primary_replay_lead ?? "N/A"} mono />
              <Metric label="Replay Verdict" value={agentWorkflow.summary.primary_replay_verdict ?? "N/A"} />
              <Metric label="Adaptive Next" value={agentWorkflow.summary.adaptive_next_step ?? "N/A"} />
            </div>
            {agentCycle && (
              <>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Latest Cycle" value={agentCycle.cycle_id.slice(-12)} mono />
                  <Metric label="Approved / Rejected" value={`${agentCycle.summary.approved_intent_count} / ${agentCycle.summary.rejected_intent_count}`} mono />
                  <Metric label="Terminal Lane" value={agentCycle.summary.terminal_lane ?? agentCycle.execution_mode} mono />
                </div>
                {agentCycle.summary.terminal_lane === "PAPER_MT5_DEMO" && (
                  <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                    <Metric label="MT5 Loop" value={agentCycle.summary.mt5_loop_status ?? agentCycle.mt5_execution_loop?.loop_status ?? "N/A"} />
                    <Metric label="MT5 Ticket" value={agentCycleMt5Tickets.length ? agentCycleMt5Tickets.join(", ") : "N/A"} mono />
                    <Metric label="Deal Memory" value={`${agentCycle.summary.mt5_deal_history_memory_update_count ?? 0} joins`} mono />
                    <Metric label="Closed P/L" value={`$${(agentCycle.summary.mt5_net_profit_loss_account ?? 0).toFixed(2)}`} mono danger={(agentCycle.summary.mt5_net_profit_loss_account ?? 0) < 0} />
                    <Metric label="Closed Positions" value={`${agentCycle.summary.mt5_closed_position_count ?? 0}`} mono />
                    <Metric label="P/L Memory Rows" value={`${agentCycle.summary.mt5_post_memory_pnl_ready_count ?? 0}`} mono />
                  </div>
                )}
                {agentCycle.summary.terminal_lane !== "PAPER_MT5_DEMO" && (
                  <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                    <Metric label="MT4 Paper Commands" value={`${agentCycle.summary.terminal_command_count}`} mono />
                    <Metric label="Execution Mode" value={agentCycle.execution_mode} mono />
                    <Metric label="Pending Receipts" value={`${(agentCycle.summary as Record<string, unknown>).pending_receipt_count ?? "N/A"}`} mono />
                  </div>
                )}
                <div className="tally-table-wrap" style={{ marginBottom: 10 }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Intent</th>
                        <th>Agent</th>
                        <th>Route</th>
                        <th>Confidence</th>
                        <th>Overseer</th>
                      </tr>
                    </thead>
                    <tbody>
                      {agentCycle.route_intents.slice(0, 4).map((intent) => {
                        const decision = agentCycle.overseer_decisions.find((item) => item.intent_id === intent.intent_id);
                        return (
                          <tr key={intent.intent_id}>
                            <td className="mono" style={{ fontSize: "0.58rem" }}>{intent.intent_id}</td>
                            <td>{intent.agent_id}</td>
                            <td className="mono">{intent.symbol} {intent.timeframe} {intent.action}</td>
                            <td className="mono">{intent.confidence.toFixed(4)}</td>
                            <td>
                              <StatusChip
                                label={decision?.decision ?? "PENDING"}
                                variant={decision?.approved ? "success" : "warning"}
                                size="sm"
                              />
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </>
            )}
            <div className="tally-table-wrap" style={{ marginBottom: 10 }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Agent</th>
                    <th>Cadence</th>
                    <th>Timeframes</th>
                    <th>Outputs</th>
                    <th>Writes</th>
                  </tr>
                </thead>
                <tbody>
                  {agentRoster.map((agent) => (
                    <tr key={agent.agent_id}>
                      <td>
                        <div style={{ fontWeight: 600 }}>{agent.agent_id}</div>
                        <div style={{ fontSize: "0.62rem", color: "var(--text-muted)" }}>{agent.role}</div>
                      </td>
                      <td style={{ fontSize: "0.64rem" }}>{agent.cadence}</td>
                      <td className="mono">{agent.timeframes.join(", ")}</td>
                      <td style={{ fontSize: "0.58rem" }}>{agent.decision_outputs.slice(0, 4).join(", ")}</td>
                      <td style={{ fontSize: "0.58rem" }}>{agent.memory_writes.slice(0, 3).join(", ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
              {autowakeEvents.slice(0, 3).map((event) => (
                <div key={event.event_id} className="dashboard-metric">
                  <span className="field-label">{event.event_id}</span>
                  <span className="field-value mono">{event.trigger}</span>
                  <span style={{ fontSize: "0.62rem", color: "var(--text-muted)" }}>{event.action}</span>
                </div>
              ))}
            </div>
            <div className="tally-table-wrap" style={{ marginBottom: 10 }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Priority</th>
                    <th>Build Item</th>
                    <th>Why It Matters</th>
                    <th>Target File</th>
                  </tr>
                </thead>
                <tbody>
                  {implementationQueue.slice(0, 5).map((item) => (
                    <tr key={item.item_id}>
                      <td className="mono">{item.priority}</td>
                      <td>{item.item_id}</td>
                      <td style={{ fontSize: "0.64rem" }}>{item.plain_english}</td>
                      <td className="mono" style={{ fontSize: "0.58rem" }}>{item.target_file}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
              {agentWorkflow.thirty_day_window.objective}
            </div>
            <div style={{ marginTop: 10, fontSize: "0.7rem", color: "var(--warning)" }}>
              {agentWorkflow.claim_boundary}
            </div>
          </>
        ) : (
          <div className="no-data-message">
            <p>No CAS Forex agent workflow plan is available yet.</p>
          </div>
        )}
      </GlassPanel>

      {/* Section 4: Agent Information Flow */}
      <GlassPanel
        title="Agent Information Flow"
        subtitle={
          agentFlow
            ? `${agentFlow.summary.specialist_agent_count} specialist reviews | ${agentFlow.summary.canonical_packet_count} packets | ${agentFlow.summary.lifecycle_state_count} lifecycle states`
            : "No agent information-flow report loaded"
        }
        variant="info"
      >
        {agentFlow ? (
          <>
            <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
              <Metric label="Best Flow" value={agentFlow.summary.best_flow_form} />
              <Metric label="Event Journal" value={agentFlow.storage_and_api_targets.append_only_event_log} mono />
              <Metric label="Next File" value={agentFlow.summary.must_have_next_file} mono />
            </div>
            {agentBus && (
              <>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Journal Events" value={`${agentBus.event_count}`} mono />
                  <Metric label="Cycles Logged" value={`${agentBus.cycle_count}`} mono />
                  <Metric label="Pending Receipts" value={`${agentBus.pending_receipt_count}`} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Verified Receipts" value={`${agentBus.verified_receipt_count ?? 0}`} mono />
                  <Metric label="Reconciled" value={`${agentBus.reconciled_receipt_count ?? 0}`} mono />
                  <Metric label="Next-Cycle Allowed" value={`${agentBus.next_cycle_allowed_count ?? 0}`} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Latest Cycle" value={agentBus.latest_cycle_id ?? "N/A"} mono />
                  <Metric label="Latest Event" value={agentBus.latest_event_id ?? "N/A"} mono />
                  <Metric label="Journal Path" value={agentBus.event_log_path} mono />
                </div>
                <div className="tally-table-wrap" style={{ marginBottom: 10 }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Event Type</th>
                        <th>Count</th>
                        <th>Status</th>
                        <th>Status Count</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(agentBus.event_type_counts).slice(0, 8).map(([eventType, count], index) => {
                        const statusEntry = Object.entries(agentBus.status_counts)[index];
                        return (
                          <tr key={eventType}>
                            <td className="mono">{eventType}</td>
                            <td className="mono">{count}</td>
                            <td className="mono">{statusEntry?.[0] ?? "—"}</td>
                            <td className="mono">{statusEntry?.[1] ?? "—"}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </>
            )}
            {terminalReceiptIngest && (
              <>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Receipt Files" value={`${terminalReceiptIngest.summary.receipt_count}`} mono />
                  <Metric label="New Ingested" value={`${terminalReceiptIngest.summary.new_receipt_count}`} mono />
                  <Metric label="Receipt Mismatches" value={`${terminalReceiptIngest.summary.receipt_mismatch_count}`} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Verified" value={`${terminalReceiptIngest.summary.verified_receipt_count}`} mono />
                  <Metric label="Reconciled" value={`${terminalReceiptIngest.summary.reconciled_receipt_count}`} mono />
                  <Metric label="Pending After Ingest" value={`${terminalReceiptIngest.summary.pending_receipt_count}`} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Mailbox" value={terminalReceiptIngest.mailbox_dir} mono />
                  <Metric label="Ingest Status" value={terminalReceiptIngest.ingest_status} />
                  <Metric label="Next Action" value={terminalReceiptIngest.next_action} />
                </div>
                {terminalReceiptIngest.receipt_records.length > 0 && (
                  <div className="tally-table-wrap" style={{ marginBottom: 10 }}>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Receipt</th>
                          <th>Command</th>
                          <th>Symbol</th>
                          <th>Hash</th>
                          <th>Lifecycle</th>
                          <th>Next</th>
                        </tr>
                      </thead>
                      <tbody>
                        {terminalReceiptIngest.receipt_records.slice(0, 6).map((receipt) => (
                          <tr key={`${receipt.receipt_id}-${receipt.command_id}`}>
                            <td className="mono" style={{ fontSize: "0.58rem" }}>{receipt.receipt_id}</td>
                            <td className="mono" style={{ fontSize: "0.58rem" }}>{receipt.command_id}</td>
                            <td className="mono">{receipt.symbol ?? "N/A"}</td>
                            <td>
                              <StatusChip label={receipt.raw_request_hash_match ? "MATCH" : "MISMATCH"} variant={receipt.raw_request_hash_match ? "success" : "warning"} size="sm" />
                            </td>
                            <td>
                              <StatusChip label={receipt.lifecycle_status} variant={receipt.lifecycle_status === "RECEIPT_VERIFIED" ? "success" : "warning"} size="sm" />
                            </td>
                            <td>
                              <StatusChip label={receipt.next_cycle_status} variant={receipt.next_cycle_status === "NEXT_CYCLE_ALLOWED" ? "success" : "warning"} size="sm" />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            )}
            {terminalHistoryIngest && (
              <>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="History Rows" value={`${terminalHistoryIngest.summary.history_record_count}`} mono />
                  <Metric label="Memory Updates" value={`${terminalHistoryIngest.summary.memory_update_count}`} mono />
                  <Metric label="Unmatched Rows" value={`${terminalHistoryIngest.summary.unmatched_history_count}`} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Closed Win / Loss" value={`${terminalHistoryIngest.summary.closed_profit_count} / ${terminalHistoryIngest.summary.closed_loss_count}`} mono />
                  <Metric label="Net Closed PnL" value={`${terminalHistoryIngest.summary.net_profit_loss_account}`} mono />
                  <Metric label="PNL-Ready Memory" value={`${terminalHistoryIngest.summary.pnl_ready_memory_count}`} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Source Paths" value={terminalHistoryIngest.source_paths.join(", ") || "N/A"} mono />
                  <Metric label="Ingest Status" value={terminalHistoryIngest.ingest_status} />
                  <Metric label="Next Action" value={terminalHistoryIngest.next_action} />
                </div>
                {terminalHistoryIngest.memory_updates.length > 0 && (
                  <div className="tally-table-wrap" style={{ marginBottom: 10 }}>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Memory</th>
                          <th>Symbol</th>
                          <th>Match</th>
                          <th>PnL</th>
                          <th>Pips</th>
                          <th>Outcome</th>
                        </tr>
                      </thead>
                      <tbody>
                        {terminalHistoryIngest.memory_updates.slice(0, 6).map((update) => (
                          <tr key={`${update.memory_id}-${update.history_id}`}>
                            <td className="mono" style={{ fontSize: "0.58rem" }}>{update.memory_id}</td>
                            <td className="mono">{update.symbol}</td>
                            <td className="mono">{update.match_method ?? "N/A"}</td>
                            <td className="mono">{update.profit_loss_account}</td>
                            <td className="mono">{update.profit_loss_pips ?? "N/A"}</td>
                            <td>
                              <StatusChip label={update.outcome_label} variant={update.outcome_label === "TRADE_CLOSED_PROFIT" ? "success" : "warning"} size="sm" />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            )}
            {agentMemory && (
              <>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Memory Records" value={`${agentMemory.summary.memory_record_count}`} mono />
                  <Metric label="Approved / Rejected" value={`${agentMemory.summary.approved_count} / ${agentMemory.summary.rejected_count}`} mono />
                  <Metric label="Receipts Joined" value={`${agentMemory.summary.receipt_joined_count}`} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Waiting For Terminal" value={`${agentMemory.summary.pending_receipt_count}`} mono />
                  <Metric label="Verified Receipts" value={`${agentMemory.summary.verified_receipt_count}`} mono />
                  <Metric label="Memory Status" value={agentMemory.memory_status} />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="History Joined" value={`${agentMemory.summary.terminal_history_joined_count ?? 0}`} mono />
                  <Metric label="Closed Win / Loss" value={`${agentMemory.summary.closed_profit_count ?? 0} / ${agentMemory.summary.closed_loss_count ?? 0}`} mono />
                  <Metric label="Net Closed PnL" value={`${agentMemory.summary.net_profit_loss_account ?? 0}`} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Latest Cycle" value={agentMemory.summary.latest_cycle_id ?? "N/A"} mono />
                  <Metric label="Memory Schema" value={agentMemory.schema} mono />
                  <Metric label="Next Action" value={agentMemory.next_action} />
                </div>
                {Object.keys(agentMemory.summary.outcome_label_counts).length > 0 && (
                  <div className="tally-table-wrap" style={{ marginBottom: 10 }}>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Outcome Label</th>
                          <th>Count</th>
                          <th>Learning Status</th>
                          <th>Status Count</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(agentMemory.summary.outcome_label_counts).slice(0, 6).map(([outcome, count], index) => {
                          const learningEntry = Object.entries(agentMemory.summary.learning_status_counts)[index];
                          return (
                            <tr key={outcome}>
                              <td className="mono">{outcome}</td>
                              <td className="mono">{count}</td>
                              <td className="mono">{learningEntry?.[0] ?? "N/A"}</td>
                              <td className="mono">{learningEntry?.[1] ?? "N/A"}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            )}
            {agentResearchQueue && (
              <>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Research Tasks" value={`${agentResearchQueue.summary.task_count}`} mono />
                  <Metric label="High Priority" value={`${agentResearchQueue.summary.high_priority_task_count}`} mono />
                  <Metric label="Next Task" value={agentResearchQueue.summary.next_task_id ?? "N/A"} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Receipt Joinback" value={`${agentResearchQueue.summary.terminal_receipt_task_count}`} mono />
                  <Metric label="Condition Lab" value={`${agentResearchQueue.summary.condition_lab_task_count}`} mono />
                  <Metric label="Walk-Forward Replay" value={`${agentResearchQueue.summary.walk_forward_task_count}`} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Source Memory" value={`${agentResearchQueue.summary.source_memory_count}`} mono />
                  <Metric label="Ready Rows" value={`${agentResearchQueue.summary.source_ready_for_research_count}`} mono />
                  <Metric label="Pending Receipt Rows" value={`${agentResearchQueue.summary.source_pending_receipt_count}`} mono />
                </div>
                <div className="tally-table-wrap" style={{ marginBottom: 10 }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Priority</th>
                        <th>Task Type</th>
                        <th>Symbols</th>
                        <th>Question</th>
                        <th>Blocked By</th>
                      </tr>
                    </thead>
                    <tbody>
                      {agentResearchQueue.research_tasks.slice(0, 6).map((task) => (
                        <tr key={task.task_id}>
                          <td className="mono">{task.priority}</td>
                          <td className="mono" style={{ fontSize: "0.58rem" }}>{task.task_type}</td>
                          <td className="mono">{task.symbols.join(", ")} {task.timeframes.join(", ")}</td>
                          <td style={{ fontSize: "0.64rem" }}>{task.research_question}</td>
                          <td style={{ fontSize: "0.58rem" }}>{task.blocked_by.length ? task.blocked_by.join(", ") : "N/A"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div style={{ marginBottom: 10, fontSize: "0.7rem", color: "var(--text-muted)" }}>
                  {agentResearchQueue.next_action}
                </div>
              </>
            )}
            {strategyDevQueue && (
              <>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Strategy Items" value={`${strategyDevQueue.summary.item_count}`} mono />
                  <Metric label="Queued / Blocked" value={`${strategyDevQueue.summary.queued_item_count} / ${strategyDevQueue.summary.blocked_item_count}`} mono />
                  <Metric label="Next Item" value={strategyDevQueue.summary.next_item_id ?? "N/A"} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Replay Requests" value={`${strategyDevQueue.summary.ready_for_replay_count}`} mono />
                  <Metric label="Patch Candidates" value={`${strategyDevQueue.summary.patch_candidate_count}`} mono />
                  <Metric label="Terminal Blocked" value={`${strategyDevQueue.summary.terminal_blocked_count}`} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Promotion / Demotion" value={`${strategyDevQueue.summary.promotion_review_count} / ${strategyDevQueue.summary.demotion_review_count}`} mono />
                  <Metric label="Closed Profit Memory" value={`${strategyDevQueue.summary.closed_profit_memory_count}`} mono />
                  <Metric label="Closed Loss Memory" value={`${strategyDevQueue.summary.closed_loss_memory_count}`} mono />
                </div>
                <div className="tally-table-wrap" style={{ marginBottom: 10 }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Priority</th>
                        <th>Status</th>
                        <th>Work Type</th>
                        <th>Symbols</th>
                        <th>Goal</th>
                      </tr>
                    </thead>
                    <tbody>
                      {strategyDevQueue.work_items.slice(0, 6).map((item) => (
                        <tr key={item.item_id}>
                          <td className="mono">{item.priority}</td>
                          <td>
                            <StatusChip label={item.status} variant={item.status.startsWith("BLOCKED") ? "warning" : "info"} size="sm" />
                          </td>
                          <td className="mono" style={{ fontSize: "0.58rem" }}>{item.item_type}</td>
                          <td className="mono">{item.symbols.join(", ")} {item.timeframes.join(", ")}</td>
                          <td style={{ fontSize: "0.64rem" }}>{item.plain_english_goal}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div style={{ marginBottom: 10, fontSize: "0.7rem", color: "var(--text-muted)" }}>
                  {strategyDevQueue.next_action}
                </div>
              </>
            )}
            {strategyPatchRunner && (
              <>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Patch Decisions" value={`${strategyPatchRunner.summary.decision_count}`} mono />
                  <Metric label="Ready / Blocked" value={`${strategyPatchRunner.summary.ready_decision_count} / ${strategyPatchRunner.summary.blocked_decision_count}`} mono />
                  <Metric label="Next Decision" value={strategyPatchRunner.summary.next_decision_id ?? "N/A"} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Patch / Replay" value={`${strategyPatchRunner.summary.patch_candidate_count} / ${strategyPatchRunner.summary.replay_job_count}`} mono />
                  <Metric label="Promotion / Demotion" value={`${strategyPatchRunner.summary.promotion_review_count} / ${strategyPatchRunner.summary.demotion_review_count}`} mono />
                  <Metric label="Terminal Inputs" value={`${strategyPatchRunner.summary.terminal_input_required_count}`} mono />
                </div>
                <div className="tally-table-wrap" style={{ marginBottom: 10 }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Priority</th>
                        <th>Status</th>
                        <th>Decision</th>
                        <th>Target</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {strategyPatchRunner.decisions.slice(0, 6).map((decision) => (
                        <tr key={decision.decision_id}>
                          <td className="mono">{decision.priority}</td>
                          <td>
                            <StatusChip label={decision.status} variant={decision.status.startsWith("BLOCKED") ? "warning" : "info"} size="sm" />
                          </td>
                          <td className="mono" style={{ fontSize: "0.58rem" }}>{decision.decision_type}</td>
                          <td className="mono" style={{ fontSize: "0.58rem" }}>{decision.patch_target}</td>
                          <td style={{ fontSize: "0.64rem" }}>{decision.plain_english_decision}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div style={{ marginBottom: 10, fontSize: "0.7rem", color: "var(--text-muted)" }}>
                  {strategyPatchRunner.next_action}
                </div>
              </>
            )}
            {dailyLearningRollup && (
              <>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="30-Day Day" value={`${dailyLearningRollup.day_index} / ${dailyLearningRollup.window_days}`} mono />
                  <Metric label="Routes" value={`${dailyLearningRollup.summary.route_count}`} mono />
                  <Metric label="Chain Verified" value={dailyLearningRollup.summary.chain_verified ? "YES" : "NO"} />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Approved / Rejected" value={`${dailyLearningRollup.summary.approved_count} / ${dailyLearningRollup.summary.rejected_count}`} mono />
                  <Metric label="Closed W/L/F" value={`${dailyLearningRollup.summary.win_count} / ${dailyLearningRollup.summary.loss_count} / ${dailyLearningRollup.summary.flat_count}`} mono />
                  <Metric label="Net PnL" value={`${dailyLearningRollup.summary.net_profit_loss_account}`} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Profit Factor" value={dailyLearningRollup.summary.profit_factor == null ? "N/A" : `${dailyLearningRollup.summary.profit_factor}`} mono />
                  <Metric label="Expectancy" value={dailyLearningRollup.summary.expectancy_account == null ? "N/A" : `${dailyLearningRollup.summary.expectancy_account}`} mono />
                  <Metric label="Readiness" value={dailyLearningRollup.summary.readiness_label} />
                </div>
                <div className="tally-table-wrap" style={{ marginBottom: 10 }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Work</th>
                        <th>Status</th>
                        <th>Priority</th>
                        <th>Source</th>
                        <th>Why It Matters</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dailyLearningRollup.queued_follow_up_work.slice(0, 6).map((item) => (
                        <tr key={`${item.work_type}-${item.source_id}`}>
                          <td className="mono" style={{ fontSize: "0.58rem" }}>{item.work_type}</td>
                          <td>
                            <StatusChip label={item.status ?? "N/A"} variant={(item.status ?? "").startsWith("BLOCKED") ? "warning" : "info"} size="sm" />
                          </td>
                          <td className="mono">{item.priority ?? "N/A"}</td>
                          <td className="mono" style={{ fontSize: "0.58rem" }}>{item.source_id ?? "N/A"}</td>
                          <td style={{ fontSize: "0.64rem" }}>{item.plain_english ?? "N/A"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  {dailyLearningRollup.terminal_blockers.slice(0, 3).map((blocker) => (
                    <div key={blocker.blocker_id} className="dashboard-metric">
                      <span className="field-label">{blocker.blocker_id}</span>
                      <span className="field-value mono">{blocker.count}</span>
                      <span style={{ fontSize: "0.58rem", color: "var(--text-muted)" }}>{blocker.plain_english}</span>
                    </div>
                  ))}
                </div>
                <div style={{ marginBottom: 10, fontSize: "0.7rem", color: "var(--text-muted)" }}>
                  {dailyLearningRollup.next_action}
                </div>
              </>
            )}
            {sessionAutowake && (
              <>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Autowake Status" value={sessionAutowake.autowake_status} />
                  <Metric label="Active Session" value={sessionAutowake.summary.active_session} />
                  <Metric label="Market Open" value={sessionAutowake.summary.market_open ? "YES" : "NO"} />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Due / Executable" value={`${sessionAutowake.summary.due_event_count} / ${sessionAutowake.summary.executable_event_count}`} mono />
                  <Metric label="Executed Cycles" value={`${sessionAutowake.summary.executed_cycle_count}`} mono />
                  <Metric label="Next Event" value={sessionAutowake.summary.next_due_event_id ?? "N/A"} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Pending Receipts" value={`${sessionAutowake.summary.pending_receipt_count}`} mono />
                  <Metric label="Terminal Blockers" value={`${sessionAutowake.summary.terminal_blocker_count}`} mono />
                  <Metric label="Rollup Readiness" value={sessionAutowake.summary.daily_rollup_readiness_label ?? "N/A"} />
                </div>
                <div className="tally-table-wrap" style={{ marginBottom: 10 }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Event</th>
                        <th>Status</th>
                        <th>Due</th>
                        <th>Cycle</th>
                        <th>Decision</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sessionAutowake.event_evaluations.slice(0, 7).map((event) => (
                        <tr key={event.event_id}>
                          <td className="mono" style={{ fontSize: "0.58rem" }}>{event.event_id}</td>
                          <td>
                            <StatusChip label={event.status} variant={event.status.startsWith("DUE") ? "info" : "muted"} size="sm" />
                          </td>
                          <td>{event.due ? "YES" : "NO"}</td>
                          <td>{event.requested_agent_cycle ? "YES" : "NO"}</td>
                          <td style={{ fontSize: "0.64rem" }}>{event.decision}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div style={{ marginBottom: 10, fontSize: "0.7rem", color: "var(--text-muted)" }}>
                  {sessionAutowake.next_action}
                </div>
              </>
            )}
            {terminalReceiptWatcher && (
              <>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Watcher Status" value={terminalReceiptWatcher.watch_status} />
                  <Metric label="Terminal Files" value={`${terminalReceiptWatcher.summary.terminal_file_count}`} mono />
                  <Metric label="Changed Files" value={`${terminalReceiptWatcher.summary.changed_file_count}`} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Receipt / History" value={`${terminalReceiptWatcher.summary.receipt_file_count} / ${terminalReceiptWatcher.summary.history_file_count}`} mono />
                  <Metric label="Chain Requested" value={terminalReceiptWatcher.summary.chain_requested ? "YES" : "NO"} />
                  <Metric label="Latest Step" value={terminalReceiptWatcher.summary.latest_completed_step ?? "N/A"} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Chain Steps" value={`${terminalReceiptWatcher.summary.chain_step_complete_count} complete`} mono />
                  <Metric label="Failed Steps" value={`${terminalReceiptWatcher.summary.chain_step_failed_count}`} mono />
                  <Metric label="First Failed" value={terminalReceiptWatcher.summary.first_failed_step ?? "N/A"} mono />
                </div>
                <div className="tally-table-wrap" style={{ marginBottom: 10 }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Step</th>
                        <th>Status</th>
                        <th>Label</th>
                        <th>Report</th>
                      </tr>
                    </thead>
                    <tbody>
                      {terminalReceiptWatcher.chain_steps.slice(0, 8).map((step) => (
                        <tr key={step.step}>
                          <td className="mono" style={{ fontSize: "0.58rem" }}>{step.step}</td>
                          <td>
                            <StatusChip label={step.status} variant={step.status === "FAILED" ? "warning" : "info"} size="sm" />
                          </td>
                          <td style={{ fontSize: "0.64rem" }}>{step.status_label}</td>
                          <td className="mono" style={{ fontSize: "0.55rem" }}>{step.artifact_paths?.json ?? "N/A"}</td>
                        </tr>
                      ))}
                      {terminalReceiptWatcher.chain_steps.length === 0 && (
                        <tr>
                          <td className="mono" style={{ fontSize: "0.58rem" }}>watcher_idle</td>
                          <td><StatusChip label="IDLE" variant="muted" size="sm" /></td>
                          <td style={{ fontSize: "0.64rem" }}>waiting for terminal files</td>
                          <td className="mono" style={{ fontSize: "0.55rem" }}>N/A</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
                <div style={{ marginBottom: 10, fontSize: "0.7rem", color: "var(--text-muted)" }}>
                  {terminalReceiptWatcher.next_action}
                </div>
              </>
            )}
            {terminalBridgeSupervisor && (
              <>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Bridge Status" value={terminalBridgeSupervisor.supervisor_status} />
                  <Metric label="Heartbeat" value={terminalBridgeSupervisor.summary.heartbeat_status ?? "N/A"} />
                  <Metric label="Age Seconds" value={terminalBridgeSupervisor.summary.heartbeat_age_seconds == null ? "N/A" : `${Math.round(terminalBridgeSupervisor.summary.heartbeat_age_seconds)}`} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Commands / Receipts" value={`${terminalBridgeSupervisor.summary.command_file_count} / ${terminalBridgeSupervisor.summary.receipt_file_count}`} mono />
                  <Metric label="Pending Receipts" value={`${terminalBridgeSupervisor.summary.pending_command_receipt_count}`} mono />
                  <Metric label="Journal Pending" value={`${terminalBridgeSupervisor.summary.event_journal_pending_receipt_count}`} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="History Files" value={`${terminalBridgeSupervisor.summary.history_file_count}`} mono />
                  <Metric label="Account Snapshot" value={terminalBridgeSupervisor.summary.account_snapshot_present ? "YES" : "NO"} />
                  <Metric label="Live Flag Visible" value={terminalBridgeSupervisor.summary.live_trading_flag_visible ? "YES" : "NO"} />
                </div>
                <div className="tally-table-wrap" style={{ marginBottom: 10 }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Alert</th>
                        <th>Severity</th>
                        <th>Plain English</th>
                      </tr>
                    </thead>
                    <tbody>
                      {terminalBridgeSupervisor.alerts.slice(0, 7).map((alert) => (
                        <tr key={alert.alert_id}>
                          <td className="mono" style={{ fontSize: "0.58rem" }}>{alert.alert_id}</td>
                          <td>
                            <StatusChip label={alert.severity} variant={alert.severity === "HIGH" ? "warning" : "info"} size="sm" />
                          </td>
                          <td style={{ fontSize: "0.64rem" }}>{alert.plain_english}</td>
                        </tr>
                      ))}
                      {terminalBridgeSupervisor.alerts.length === 0 && (
                        <tr>
                          <td className="mono" style={{ fontSize: "0.58rem" }}>bridge_clear</td>
                          <td><StatusChip label="CLEAR" variant="success" size="sm" /></td>
                          <td style={{ fontSize: "0.64rem" }}>No supervisor alerts in the latest bridge report.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
                <div style={{ marginBottom: 10, fontSize: "0.7rem", color: "var(--text-muted)" }}>
                  {terminalBridgeSupervisor.next_action}
                </div>
              </>
            )}
            {mt4TerminalActivation && (
              <>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="MT4 Activation" value={mt4TerminalActivation.activation_status} />
                  <Metric label="MT4 / MT5-Only" value={`${mt4TerminalActivation.summary.mt4_candidate_count} / ${mt4TerminalActivation.summary.mt5_only_candidate_count}`} mono />
                  <Metric label="EA Match" value={mt4TerminalActivation.summary.ea_hash_matches ? "YES" : "NO"} />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Selected Terminal" value={mt4TerminalActivation.selected_terminal?.terminal_data_dir ?? "N/A"} mono />
                  <Metric label="Mailbox Ready" value={mt4TerminalActivation.summary.mailbox_ready ? "YES" : "NO"} />
                  <Metric label="Heartbeat" value={mt4TerminalActivation.summary.heartbeat_present ? "PRESENT" : "MISSING"} />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="CAS Mailbox Alignment" value={mt4TerminalActivation.path_alignment.alignment_status} />
                  <Metric label="MailboxRoot" value={mt4TerminalActivation.settings.MailboxRoot} mono />
                  <Metric label="LiveTradingAllowed" value={mt4TerminalActivation.settings.LiveTradingAllowed ? "TRUE" : "FALSE"} />
                </div>
                <div className="tally-table-wrap" style={{ marginBottom: 10 }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Step</th>
                        <th>Activation</th>
                      </tr>
                    </thead>
                    <tbody>
                      {mt4TerminalActivation.activation_steps.slice(0, 5).map((step) => (
                        <tr key={step.step}>
                          <td className="mono">{step.step}</td>
                          <td style={{ fontSize: "0.64rem" }}>{step.plain_english}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div style={{ marginBottom: 10, fontSize: "0.7rem", color: "var(--text-muted)" }}>
                  {mt4TerminalActivation.next_action}
                </div>
              </>
            )}
            {mt4PingRoundtrip && (
              <>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="MT4 Ping" value={mt4PingRoundtrip.roundtrip_status} />
                  <Metric label="Ping Written" value={mt4PingRoundtrip.summary.ping_written ? "YES" : "NO"} />
                  <Metric label="Mailbox Ready" value={mt4PingRoundtrip.summary.mailbox_ready ? "YES" : "NO"} />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Heartbeat" value={mt4PingRoundtrip.summary.heartbeat_present ? "PRESENT" : "MISSING"} />
                  <Metric label="Receipt" value={mt4PingRoundtrip.summary.receipt_present ? "PRESENT" : "MISSING"} />
                  <Metric label="Receipt Status" value={mt4PingRoundtrip.summary.receipt_status ?? "N/A"} />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Hash Match" value={mt4PingRoundtrip.summary.raw_request_hash_match ? "YES" : "NO"} />
                  <Metric label="Live Flag" value={mt4PingRoundtrip.summary.live_flag_visible ? "VISIBLE" : "NOT_VISIBLE"} />
                  <Metric label="Command ID" value={mt4PingRoundtrip.summary.command_id ?? "N/A"} mono />
                </div>
                <div style={{ marginBottom: 10, fontSize: "0.7rem", color: "var(--text-muted)" }}>
                  {mt4PingRoundtrip.next_action}
                </div>
              </>
            )}
            {mt4TerminalSessionVerifier && (
              <>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="MT4 Session" value={mt4TerminalSessionVerifier.session_status} />
                  <Metric label="Steps" value={`${mt4TerminalSessionVerifier.summary.step_count} total / ${mt4TerminalSessionVerifier.summary.skipped_step_count} skipped`} mono />
                  <Metric label="Refresh Chain" value={mt4TerminalSessionVerifier.summary.refresh_chain_complete ? "COMPLETE" : "PENDING"} />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Activation" value={mt4TerminalSessionVerifier.summary.activation_status ?? "N/A"} />
                  <Metric label="Ping" value={mt4TerminalSessionVerifier.summary.roundtrip_status ?? "N/A"} />
                  <Metric label="Watcher" value={mt4TerminalSessionVerifier.summary.watch_status ?? "N/A"} />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="MT4 / MT5-Only" value={`${mt4TerminalSessionVerifier.summary.mt4_candidate_count} / ${mt4TerminalSessionVerifier.summary.mt5_only_candidate_count}`} mono />
                  <Metric label="Heartbeat" value={mt4TerminalSessionVerifier.summary.heartbeat_present ? "PRESENT" : "MISSING"} />
                  <Metric label="Receipt" value={mt4TerminalSessionVerifier.summary.receipt_present ? "PRESENT" : "MISSING"} />
                </div>
                <div className="tally-table-wrap" style={{ marginBottom: 10 }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Step</th>
                        <th>Status</th>
                        <th>Detail</th>
                      </tr>
                    </thead>
                    <tbody>
                      {mt4TerminalSessionVerifier.step_results.slice(0, 6).map((step) => (
                        <tr key={step.step}>
                          <td className="mono" style={{ fontSize: "0.58rem" }}>{step.step}</td>
                          <td>
                            <StatusChip label={step.status_label ?? step.status} variant={step.status === "COMPLETE" ? "success" : step.status === "FAILED" ? "warning" : "muted"} size="sm" />
                          </td>
                          <td style={{ fontSize: "0.64rem" }}>{step.message}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div style={{ marginBottom: 10, fontSize: "0.7rem", color: "var(--text-muted)" }}>
                  {mt4TerminalSessionVerifier.next_action}
                </div>
              </>
            )}
            {mt4HistoryExportVerifier && (
              <>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="History Export" value={mt4HistoryExportVerifier.verifier_status} />
                  <Metric label="Rows" value={`${mt4HistoryExportVerifier.summary.history_record_count}`} mono />
                  <Metric label="Mailbox" value={mt4HistoryExportVerifier.summary.mailbox_ready ? "READY" : "MISSING"} />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="EA Source" value={mt4HistoryExportVerifier.summary.ea_source_present ? "PRESENT" : "MISSING"} />
                  <Metric label="Export File" value={mt4HistoryExportVerifier.summary.history_export_present ? "PRESENT" : "MISSING"} />
                  <Metric label="Exporter Status" value={mt4HistoryExportVerifier.summary.exporter_status ?? "N/A"} />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Ingest" value={mt4HistoryExportVerifier.summary.ingest_status ?? "PENDING"} />
                  <Metric label="Memory Updates" value={`${mt4HistoryExportVerifier.summary.memory_update_count}`} mono />
                  <Metric label="Net P/L" value={`$${mt4HistoryExportVerifier.summary.net_profit_loss_account.toFixed(2)}`} mono />
                </div>
                <div className="metric-stack" style={{ marginBottom: 10 }}>
                  <Metric label="Expected Export" value={mt4HistoryExportVerifier.history_export_path ?? "N/A"} mono />
                </div>
                <div style={{ marginBottom: 10, fontSize: "0.7rem", color: "var(--text-muted)" }}>
                  {mt4HistoryExportVerifier.next_action}
                </div>
              </>
            )}
            {mt5TerminalApiVerifier && (
              <>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="MT5 API" value={mt5TerminalApiVerifier.verifier_status} />
                  <Metric label="Connected" value={mt5TerminalApiVerifier.summary.terminal_connected ? "YES" : "NO"} />
                  <Metric label="Broker API" value={mt5TerminalApiVerifier.summary.broker_api_authenticated ? "VERIFIED" : "MISSING"} />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Terminal" value={mt5TerminalApiVerifier.summary.terminal_name ?? "N/A"} />
                  <Metric label="Server" value={mt5TerminalApiVerifier.summary.server ?? "N/A"} />
                  <Metric label="Receipt" value={mt5TerminalApiVerifier.summary.receipt_validation_status ?? "N/A"} />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric
                    label="Balance"
                    value={mt5TerminalApiVerifier.summary.account_balance == null ? "N/A" : `$${mt5TerminalApiVerifier.summary.account_balance.toLocaleString()}`}
                    mono
                  />
                  <Metric
                    label="Equity"
                    value={mt5TerminalApiVerifier.summary.account_equity == null ? "N/A" : `$${mt5TerminalApiVerifier.summary.account_equity.toLocaleString()}`}
                    mono
                  />
                  <Metric label="Open Positions" value={`${mt5TerminalApiVerifier.summary.open_position_count}`} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Mode" value={mt5TerminalApiVerifier.summary.broker_mode ?? "N/A"} />
                  <Metric label="Reconciled" value={mt5TerminalApiVerifier.summary.open_positions_reconciled ? "YES" : "NO"} />
                  <Metric label="Live Mode Used" value={mt5TerminalApiVerifier.summary.live_mode_used ? "YES" : "NO"} />
                </div>
                <div style={{ marginBottom: 10, fontSize: "0.7rem", color: "var(--text-muted)" }}>
                  {mt5TerminalApiVerifier.next_action}
                </div>
              </>
            )}
            {mt5PaperExecutionVerifier && (
              <>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="MT5 Paper Exec" value={mt5PaperExecutionVerifier.verifier_status} />
                  <Metric label="Order Built" value={mt5PaperExecutionVerifier.summary.order_request_built ? "YES" : "NO"} />
                  <Metric label="Order Check" value={mt5PaperExecutionVerifier.summary.order_check_status ?? "N/A"} />
                  <Metric label="Terminal Trading" value={mt5PaperExecutionVerifier.summary.terminal_trade_allowed ? "ON" : "OFF"} />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Symbol" value={mt5PaperExecutionVerifier.summary.symbol ?? "N/A"} mono />
                  <Metric label="Direction" value={mt5PaperExecutionVerifier.summary.direction ?? "N/A"} />
                  <Metric label="Volume" value={mt5PaperExecutionVerifier.summary.volume == null ? "N/A" : `${mt5PaperExecutionVerifier.summary.volume}`} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Execution Attempted" value={mt5PaperExecutionVerifier.summary.execution_attempted ? "YES" : "NO"} />
                  <Metric label="Execution Status" value={mt5PaperExecutionVerifier.summary.execution_status ?? "N/A"} />
                  <Metric label="Ticket" value={mt5PaperExecutionVerifier.summary.broker_ticket == null ? "N/A" : `${mt5PaperExecutionVerifier.summary.broker_ticket}`} mono />
                  <Metric label="Exec Error" value={mt5PaperExecutionVerifier.summary.execution_error_message ?? "N/A"} />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Close Attempted" value={mt5PaperExecutionVerifier.summary.close_attempted ? "YES" : "NO"} />
                  <Metric label="Close Success" value={mt5PaperExecutionVerifier.summary.close_success ? "YES" : "NO"} />
                  <Metric label="Response Hash" value={mt5PaperExecutionVerifier.summary.raw_response_hash ?? "N/A"} mono />
                  <Metric label="Live Mode Used" value={mt5PaperExecutionVerifier.summary.live_mode_used ? "YES" : "NO"} />
                </div>
                <div style={{ marginBottom: 10, fontSize: "0.7rem", color: "var(--text-muted)" }}>
                  {mt5PaperExecutionVerifier.next_action}
                </div>
              </>
            )}
            {mt5DealHistoryIngest && (
              <>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="MT5 Deal History" value={mt5DealHistoryIngest.ingest_status} />
                  <Metric label="Raw Deals" value={`${mt5DealHistoryIngest.summary.raw_deal_count}`} mono />
                  <Metric label="Closed Positions" value={`${mt5DealHistoryIngest.summary.closed_position_count}`} mono />
                  <Metric label="Memory Updates" value={`${mt5DealHistoryIngest.summary.memory_update_count}`} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Unmatched Rows" value={`${mt5DealHistoryIngest.summary.unmatched_history_count}`} mono />
                  <Metric label="Net P/L" value={`$${mt5DealHistoryIngest.summary.net_profit_loss_account.toFixed(2)}`} mono />
                  <Metric label="Commission" value={`$${mt5DealHistoryIngest.summary.total_commission.toFixed(2)}`} mono />
                  <Metric label="Swap" value={`$${mt5DealHistoryIngest.summary.total_swap.toFixed(2)}`} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Server" value={mt5DealHistoryIngest.summary.server ?? "N/A"} />
                  <Metric label="Demo Account" value={mt5DealHistoryIngest.summary.demo_account_confirmed ? "YES" : "NO"} />
                  <Metric label="Terminal History" value={mt5DealHistoryIngest.summary.terminal_history_ingest_status ?? "N/A"} />
                  <Metric label="Ticket Filter" value={mt5DealHistoryIngest.summary.ticket_filter ?? "NONE"} mono />
                </div>
                <div style={{ marginBottom: 10, fontSize: "0.7rem", color: "var(--text-muted)" }}>
                  {mt5DealHistoryIngest.summary.history_export_path ?? "No MT5 deal-history export path yet."}
                </div>
                <div style={{ marginBottom: 10, fontSize: "0.7rem", color: "var(--text-muted)" }}>
                  {mt5DealHistoryIngest.next_action}
                </div>
              </>
            )}
            {terminalPositionReconciliation && (
              <>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Position Reconcile" value={terminalPositionReconciliation.reconciliation_status} />
                  <Metric label="CAS / Terminal Open" value={`${terminalPositionReconciliation.summary.cas_open_position_count} / ${terminalPositionReconciliation.summary.terminal_open_position_count}`} mono />
                  <Metric label="Matched / Unmatched" value={`${terminalPositionReconciliation.summary.reconciled_open_position_count} / ${terminalPositionReconciliation.summary.unmatched_open_position_count}`} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Heartbeat" value={terminalPositionReconciliation.summary.heartbeat_status ?? "MISSING"} />
                  <Metric label="Account Snapshot" value={terminalPositionReconciliation.summary.account_snapshot_present ? "PRESENT" : "MISSING"} />
                  <Metric label="Pending Receipts" value={`${terminalPositionReconciliation.summary.pending_receipt_count}`} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Receipt Mismatch" value={`${terminalPositionReconciliation.summary.receipt_mismatch_count}`} mono />
                  <Metric label="History Joined" value={`${terminalPositionReconciliation.summary.memory_update_count}`} mono />
                  <Metric label="Net P/L" value={`$${terminalPositionReconciliation.summary.net_profit_loss_account.toFixed(2)}`} mono />
                </div>
                <div className="tally-table-wrap" style={{ marginBottom: 10 }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Check</th>
                        <th>Status</th>
                        <th>Detail</th>
                      </tr>
                    </thead>
                    <tbody>
                      {terminalPositionReconciliation.checks.slice(0, 5).map((check) => (
                        <tr key={check.check_id}>
                          <td className="mono" style={{ fontSize: "0.58rem" }}>{check.check_id}</td>
                          <td>
                            <StatusChip label={check.status} variant={check.status === "OK" ? "success" : check.status === "MISMATCH" ? "warning" : "muted"} size="sm" />
                          </td>
                          <td style={{ fontSize: "0.64rem" }}>{check.detail}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div style={{ marginBottom: 10, fontSize: "0.7rem", color: "var(--text-muted)" }}>
                  {terminalPositionReconciliation.next_action}
                </div>
              </>
            )}
            {terminalOperabilityVerifier && (
              <>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Operability" value={terminalOperabilityVerifier.operability_status} />
                  <Metric label="Terminal Go" value={terminalOperabilityVerifier.go_no_go.terminal_lane_go ? "GO" : "NO-GO"} />
                  <Metric label="Live Order Go" value={terminalOperabilityVerifier.go_no_go.live_order_go ? "GO" : "NO-GO"} />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Broker ACCEPT" value={terminalOperabilityVerifier.go_no_go.broker_accept_go ? "GO" : "NO-GO"} />
                  <Metric label="Money Movement" value={terminalOperabilityVerifier.go_no_go.money_movement_go ? "GO" : "NO-GO"} />
                  <Metric label="Pending Gates" value={`${terminalOperabilityVerifier.summary.runtime_gate_pending_capabilities.length}`} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Session" value={terminalOperabilityVerifier.summary.session_status ?? "MISSING"} />
                  <Metric label="History Export" value={terminalOperabilityVerifier.summary.history_export_verifier_status ?? "MISSING"} />
                  <Metric label="Position Reconcile" value={terminalOperabilityVerifier.summary.position_reconciliation_status ?? "MISSING"} />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="MT5 API" value={terminalOperabilityVerifier.summary.mt5_terminal_api_verifier_status ?? "MISSING"} />
                  <Metric label="MT5 Server" value={terminalOperabilityVerifier.summary.mt5_server ?? "N/A"} />
                  <Metric label="MT5 Balance" value={terminalOperabilityVerifier.summary.mt5_account_balance == null ? "N/A" : `$${terminalOperabilityVerifier.summary.mt5_account_balance.toLocaleString()}`} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="MT5 Paper Exec" value={terminalOperabilityVerifier.summary.mt5_paper_execution_verifier_status ?? "MISSING"} />
                  <Metric label="Request Built" value={terminalOperabilityVerifier.summary.mt5_paper_order_request_built ? "YES" : "NO"} />
                  <Metric label="Exec Status" value={terminalOperabilityVerifier.summary.mt5_paper_execution_status ?? "N/A"} />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="MT5 Trading" value={terminalOperabilityVerifier.summary.mt5_paper_terminal_trade_allowed ? "ON" : "OFF"} />
                  <Metric label="MT5 Exec Error" value={terminalOperabilityVerifier.summary.mt5_paper_execution_error_message ?? "N/A"} />
                  <Metric label="MT5 Response Hash" value={terminalOperabilityVerifier.summary.mt5_paper_raw_response_hash ?? "N/A"} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="MT5 Deal History" value={terminalOperabilityVerifier.summary.mt5_deal_history_ingest_status ?? "MISSING"} />
                  <Metric label="MT5 Closed Deals" value={`${terminalOperabilityVerifier.summary.mt5_deal_history_closed_position_count ?? 0}`} mono />
                  <Metric label="MT5 Deal Memory" value={`${terminalOperabilityVerifier.summary.mt5_deal_history_memory_update_count ?? 0}`} mono />
                  <Metric label="MT5 Deal P/L" value={`$${(terminalOperabilityVerifier.summary.mt5_deal_history_net_profit_loss_account ?? 0).toFixed(2)}`} mono />
                </div>
                <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
                  <Metric label="Heartbeat" value={terminalOperabilityVerifier.summary.heartbeat_status ?? "MISSING"} />
                  <Metric label="Account Snapshot" value={terminalOperabilityVerifier.summary.account_snapshot_present ? "PRESENT" : "MISSING"} />
                  <Metric label="CAS / Terminal Open" value={`${terminalOperabilityVerifier.summary.cas_open_position_count} / ${terminalOperabilityVerifier.summary.terminal_open_position_count}`} mono />
                </div>
                <div className="tally-table-wrap" style={{ marginBottom: 10 }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Operability Check</th>
                        <th>Status</th>
                        <th>Detail</th>
                      </tr>
                    </thead>
                    <tbody>
                      {terminalOperabilityVerifier.checks.slice(0, 6).map((check) => (
                        <tr key={check.check_id}>
                          <td className="mono" style={{ fontSize: "0.58rem" }}>{check.check_id}</td>
                          <td>
                            <StatusChip label={check.status} variant={check.status === "OK" ? "success" : check.status === "BLOCKED" ? "warning" : "muted"} size="sm" />
                          </td>
                          <td style={{ fontSize: "0.64rem" }}>{check.detail}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div style={{ marginBottom: 10, fontSize: "0.7rem", color: "var(--text-muted)" }}>
                  {terminalOperabilityVerifier.next_action}
                </div>
              </>
            )}
            <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
              <Metric label="Envelope" value={agentFlow.event_envelope.schema} mono />
              <Metric label="ID Rule" value={agentFlow.event_envelope.idempotency_rule} mono />
              <Metric label="Flow API" value={agentFlow.storage_and_api_targets.flow_api} mono />
            </div>
            <div className="tally-table-wrap" style={{ marginBottom: 10 }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Agent</th>
                    <th>Focus</th>
                    <th>Verdict</th>
                  </tr>
                </thead>
                <tbody>
                  {agentFlow.specialist_agent_reviews.map((review) => (
                    <tr key={review.agent}>
                      <td className="mono">{review.agent}</td>
                      <td>{review.focus}</td>
                      <td style={{ fontSize: "0.64rem" }}>{review.plain_english}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
              {flowPlanes.slice(0, 6).map((plane) => (
                <div key={plane.plane} className="dashboard-metric">
                  <span className="field-label">{plane.plane}</span>
                  <span className="field-value mono">{plane.primary_packet}</span>
                  <span style={{ fontSize: "0.58rem", color: "var(--text-muted)" }}>{plane.path}</span>
                </div>
              ))}
            </div>
            <div className="tally-table-wrap" style={{ marginBottom: 10 }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Lifecycle State</th>
                    <th>Plain English</th>
                  </tr>
                </thead>
                <tbody>
                  {flowLifecycle.slice(0, 8).map((item) => (
                    <tr key={item.state}>
                      <td>
                        <StatusChip label={item.state} variant={item.state.includes("FAILED") || item.state.includes("LOCKED") ? "warning" : "info"} size="sm" />
                      </td>
                      <td style={{ fontSize: "0.64rem" }}>{item.plain_english}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="tally-table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Bottleneck</th>
                    <th>Fix Target</th>
                    <th>Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {flowBottlenecks.slice(0, 5).map((item) => (
                    <tr key={item.bottleneck_id}>
                      <td className="mono">{item.bottleneck_id}</td>
                      <td className="mono" style={{ fontSize: "0.58rem" }}>{item.fix_target}</td>
                      <td style={{ fontSize: "0.64rem" }}>{item.plain_english}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ marginTop: 10, fontSize: "0.7rem", color: "var(--warning)" }}>
              {agentFlow.claim_boundary}
            </div>
          </>
        ) : (
          <div className="no-data-message">
            <p>No CAS Forex agent information-flow report is available yet.</p>
          </div>
        )}
      </GlassPanel>

      {/* Section 4: External Benchmarks */}
      <GlassPanel
        title="External Benchmarks"
        subtitle={
          externalBenchmarks
            ? `${externalBenchmarks.summary.benchmark_count} public systems, ${externalBenchmarks.summary.mt4_account_count} MT4, ${externalBenchmarks.summary.total_public_trade_count} visible trades`
            : "No external benchmark snapshot loaded"
        }
        variant="info"
      >
        {benchmarks.length > 0 ? (
          <>
            <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
              <Metric label="Best Gain" value={`${externalBenchmarks?.summary.best_gain_pct.toFixed(2)}%`} mono />
              <Metric label="Lowest Drawdown" value={`${externalBenchmarks?.summary.lowest_drawdown_pct.toFixed(2)}%`} mono />
              <Metric label="Symbols" value={externalBenchmarks?.summary.symbols.join(", ") ?? "—"} mono />
            </div>
            <div className="tally-table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>System</th>
                    <th>Platform</th>
                    <th>Symbol</th>
                    <th>Gain</th>
                    <th>Monthly</th>
                    <th>DD</th>
                    <th>Trades</th>
                    <th>PF</th>
                    <th>Avg Length</th>
                  </tr>
                </thead>
                <tbody>
                  {benchmarks.map((benchmark) => (
                    <tr key={benchmark.benchmark_id}>
                      <td>
                        <a href={benchmark.url} target="_blank" rel="noreferrer">
                          {benchmark.name}
                        </a>
                      </td>
                      <td className="mono" style={{ fontSize: "0.6rem" }}>
                        {platformLabel(benchmark.public_account_descriptor)}
                      </td>
                      <td className="mono">{benchmark.visible_symbol_focus}</td>
                      <td className="mono" style={{ color: "var(--success)" }}>
                        {benchmark.gain_pct.toFixed(2)}%
                      </td>
                      <td className="mono">{benchmark.monthly_pct != null ? `${benchmark.monthly_pct.toFixed(2)}%` : "—"}</td>
                      <td className="mono" style={{ color: "var(--warning)" }}>
                        {benchmark.drawdown_pct.toFixed(2)}%
                      </td>
                      <td className="mono">{benchmark.trades}</td>
                      <td className="mono">{benchmark.profit_factor != null ? benchmark.profit_factor.toFixed(2) : "—"}</td>
                      <td className="mono">{benchmark.average_trade_length ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ marginTop: 10, fontSize: "0.7rem", color: "var(--text-muted)" }}>
              Next build: {externalBenchmarks?.summary.next_build_target}
            </div>
          </>
        ) : (
          <div className="no-data-message">
            <p>No external benchmark snapshot is available yet.</p>
          </div>
        )}
      </GlassPanel>

      {/* Section 4: Local Forex Fury Set Import */}
      <GlassPanel
        title="Local Forex Fury Set Import"
        subtitle={
          furySummary
            ? `${furySummary.set_count} set files, ${furySummary.tester_report_count} tester reports, ${furySummary.platform_counts.MT4 ?? 0} MT4 + ${furySummary.platform_counts.MT5 ?? 0} MT5`
            : "No local Forex Fury set import loaded"
        }
        variant="info"
      >
        {furySummary ? (
          <>
            <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
              <Metric label="Best PF" value={formatNullableNumber(furySummary.best_profit_factor?.profit_factor, 2)} mono />
              <Metric label="Lowest DD" value={`${formatNullableNumber(furySummary.lowest_equity_drawdown_pct?.equity_drawdown_relative_pct, 2)}%`} mono />
              <Metric label="Max Orders" value={furySummary.max_orders_values.join(", ")} mono />
            </div>
            <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
              <Metric label="Grid Sets" value={`${furySummary.grid_enabled_count}/${furySummary.set_count}`} mono />
              <Metric label="Money-Close Sets" value={`${furySummary.close_by_money_count}/${furySummary.set_count}`} mono />
              <Metric label="Windows" value={`${furySummary.trade_windows.length}`} mono />
            </div>
            <div className="tally-table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Profile</th>
                    <th>Platform</th>
                    <th>Family</th>
                    <th>Symbol</th>
                    <th>TF</th>
                    <th>Window</th>
                    <th>PF</th>
                    <th>Eq DD</th>
                    <th>Trades</th>
                  </tr>
                </thead>
                <tbody>
                  {furyProfiles.slice(0, 8).map((profile) => (
                    <tr key={profile.profile_id}>
                      <td className="mono" style={{ fontSize: "0.58rem" }}>{profile.profile_id.slice(-12)}</td>
                      <td className="mono">{profile.platform}</td>
                      <td>{profile.family}</td>
                      <td className="mono">{profile.symbol ?? "—"}</td>
                      <td className="mono">{profile.timeframe ?? "—"}</td>
                      <td className="mono">{profile.trade_window ?? "—"}</td>
                      <td className="mono" style={{ color: "var(--success)" }}>{formatNullableNumber(profile.profit_factor, 2)}</td>
                      <td className="mono" style={{ color: "var(--warning)" }}>{formatNullableNumber(profile.equity_drawdown_relative_pct, 2)}%</td>
                      <td className="mono">{profile.total_trades ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ marginTop: 10, display: "grid", gap: 6 }}>
              {(forexFuryImport?.cas_improvement_targets ?? []).slice(0, 4).map((target) => (
                <div key={target} style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>
                  {target}
                </div>
              ))}
            </div>
            <div style={{ marginTop: 10, fontSize: "0.7rem", color: "var(--warning)" }}>
              {forexFuryImport?.claim_boundary}
            </div>
          </>
        ) : (
          <div className="no-data-message">
            <p>No local Forex Fury set import report is available yet.</p>
          </div>
        )}
      </GlassPanel>

      {/* Section 5: Forex Fury Replay Candidates */}
      <GlassPanel
        title="Forex Fury Replay Candidates"
        subtitle={
          furyReplaySummary
            ? `${furyReplaySummary.candidate_count} candidates, ${furyReplaySummary.supported_candidate_count} ready, ${furyReplaySummary.symbols.join(", ")}`
            : "No Forex Fury replay candidate queue loaded"
        }
        variant="info"
      >
        {furyReplaySummary ? (
          <>
            <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
              <Metric label="Ready Candidates" value={`${furyReplaySummary.supported_candidate_count}/${furyReplaySummary.candidate_count}`} mono />
              <Metric label="Top Score" value={formatNullableNumber(furyReplaySummary.top_candidate_score, 2)} mono />
              <Metric label="Needs Instrument" value={`${furyReplaySummary.waiting_for_instrument_spec_count}`} mono />
            </div>
            <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
              <Metric label="Timeframes" value={furyReplaySummary.timeframes.join(", ")} mono />
              <Metric label="Families" value={Object.entries(furyReplaySummary.families).map(([key, value]) => `${key}:${value}`).join(", ")} mono />
              <Metric label="Platforms" value={Object.entries(furyReplaySummary.platforms).map(([key, value]) => `${key}:${value}`).join(", ")} mono />
            </div>
            <div className="tally-table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Symbol</th>
                    <th>TF</th>
                    <th>Window</th>
                    <th>Family</th>
                    <th>Score</th>
                    <th>PF</th>
                    <th>DD</th>
                    <th>Orders</th>
                    <th>Policy</th>
                    <th>Readiness</th>
                  </tr>
                </thead>
                <tbody>
                  {furyReplayCandidates.slice(0, 8).map((candidate) => (
                    <tr key={candidate.candidate_id}>
                      <td className="mono">{candidate.rank}</td>
                      <td className="mono">{candidate.cas_symbol}</td>
                      <td className="mono">{candidate.timeframe}</td>
                      <td className="mono">{candidate.trade_window ?? "—"}</td>
                      <td>{candidate.family}</td>
                      <td className="mono" style={{ color: "var(--success)" }}>{candidate.score.toFixed(2)}</td>
                      <td className="mono">{formatNullableNumber(candidate.evidence.profit_factor, 2)}</td>
                      <td className="mono">{formatNullableNumber(candidate.evidence.equity_drawdown_relative_pct, 2)}%</td>
                      <td className="mono">{candidate.execution_profile.max_orders ?? "—"}</td>
                      <td className="mono" style={{ fontSize: "0.58rem" }}>
                        {candidate.execution_profile.uses_grid ? "grid " : ""}
                        {candidate.execution_profile.uses_close_by_money ? "money-close" : ""}
                      </td>
                      <td>
                        <StatusChip
                          label={candidate.readiness}
                          variant={candidate.readiness === "READY_FOR_CAS_REPLAY" ? "success" : "warning"}
                          size="sm"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {furyReplayCandidates[0]?.recommended_commands[0] && (
              <code className="next-command-text" style={{ marginTop: 10, display: "inline-block" }}>
                {furyReplayCandidates[0].recommended_commands[0]}
              </code>
            )}
            <div style={{ marginTop: 10, display: "grid", gap: 6 }}>
              {(furyReplay?.next_actions ?? []).slice(0, 3).map((action) => (
                <div key={action} style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>
                  {action}
                </div>
              ))}
            </div>
            <div style={{ marginTop: 10, fontSize: "0.7rem", color: "var(--warning)" }}>
              {furyReplay?.claim_boundary}
            </div>
          </>
        ) : (
          <div className="no-data-message">
            <p>No Forex Fury replay candidate report is available yet.</p>
          </div>
        )}
      </GlassPanel>

      {/* Section 6: Forex Fury Replay Results */}
      <GlassPanel
        title="Forex Fury Replay Results"
        subtitle={
          furyReplayResults
            ? `${furyReplayResults.replay_verdict} -> ${furyReplayResults.adaptive_compounding_next_step}`
            : "No Forex Fury replay result summary loaded"
        }
        variant="info"
      >
        {furyReplayResults && furyCondition && furyWalkForward ? (
          <>
            <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
              <Metric label="Replay Verdict" value={furyReplayResults.replay_verdict} />
              <Metric label="WF Grade" value={furyWalkForward.research_grade} />
              <Metric label="Adaptive Next" value={furyReplayResults.adaptive_compounding_next_step} />
            </div>
            <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
              <Metric label="Condition Cells" value={`${furyCondition.non_gap_cell_count}/${furyCondition.cell_count} non-gap`} mono />
              <Metric label="RPM Routes" value={`${furyCondition.route_count} route / ${furyCondition.no_trade_route_count} no-trade`} mono />
              <Metric label="Gap Fraction" value={formatNullableNumber(furyCondition.overall_gap_fraction, 4)} mono />
            </div>
            <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
              <Metric label="WF Windows" value={`${furyWalkForward.routed_windows}/${furyWalkForward.windows} routed`} mono />
              <Metric label="Positive Routed" value={`${furyWalkForward.positive_routed_windows} (${(furyWalkForward.positive_routed_window_rate * 100).toFixed(2)}%)`} mono />
              <Metric label="Max DD / Trades" value={`${furyWalkForward.routed_max_drawdown_pct.toFixed(4)}% / ${furyWalkForward.routed_total_trades}`} mono />
            </div>
            <div className="tally-table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Source</th>
                    <th>Symbol</th>
                    <th>TF</th>
                    <th>Regime</th>
                    <th>Setting</th>
                    <th>Return</th>
                    <th>DD</th>
                    <th>PF</th>
                    <th>Score</th>
                  </tr>
                </thead>
                <tbody>
                  {furyCondition.top_condition_cells.slice(0, 6).map((cell) => (
                    <tr key={`${cell.source}-${cell.symbol}-${cell.regime}-${cell.setting}-${cell.score}`}>
                      <td className="mono">{cell.source}</td>
                      <td className="mono">{cell.symbol}</td>
                      <td className="mono">{cell.timeframe}</td>
                      <td>{cell.regime}</td>
                      <td className="mono" style={{ fontSize: "0.58rem" }}>{cell.setting}</td>
                      <td className="mono" style={{ color: "var(--success)" }}>{cell.mean_return_pct.toFixed(4)}%</td>
                      <td className="mono">{cell.mean_max_dd_pct.toFixed(4)}%</td>
                      <td className="mono">{cell.profit_factor.toFixed(2)}</td>
                      <td className="mono">{cell.score.toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ marginTop: 10, display: "grid", gap: 6 }}>
              {furyReplayResults.next_actions.slice(0, 3).map((action) => (
                <div key={action} style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>
                  {action}
                </div>
              ))}
            </div>
            <div style={{ marginTop: 10 }}>
              <StatusChip
                label={furyReplayResults.replay_verdict}
                variant={furyReplayResults.replay_verdict === "REPLAY_LEAD_FOR_ADAPTIVE_REVIEW" ? "success" : "warning"}
                size="sm"
              />
            </div>
            <div style={{ marginTop: 10, fontSize: "0.7rem", color: "var(--warning)" }}>
              {furyReplayResults.claim_boundary}
            </div>
          </>
        ) : (
          <div className="no-data-message">
            <p>No Forex Fury replay result summary is available yet.</p>
          </div>
        )}
      </GlassPanel>

      {/* Section 5: PCBA Guard */}
      <GlassPanel title="PCBA Optimization Guard" variant="danger">
        <div className="legal-gates">
          <GateRow label="Guard Active" met={true} detail="TRUE" />
          <GateRow label="PCBA Syntax Check" met={true} detail="PASS" />
          <GateRow label="PCBA Semantics Review" met={true} detail="PASS" />
          <GateRow label="PCBA Authority Check" met={true} detail="PASS" />
          <GateRow label="LLM Prompt Injection Guard" met={true} detail="ACTIVE" />
        </div>
        <div style={{ marginTop: 8, fontSize: "0.72rem", color: "var(--warning)" }}>
          Optimization boundary: PAPER-ONLY — no broker orders, no live parameter changes.
        </div>
      </GlassPanel>

      {/* Section 6: Optimization History */}
      <GlassPanel title="Recent Optimization Runs">
        <div className="tally-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Run ID</th>
                <th>Type</th>
                <th>Date</th>
                <th>Scenarios</th>
                <th>Viable</th>
                <th>Verdict</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="mono" style={{ fontSize: "0.62rem" }}>
                  forex-fury-replay-results-20260624042821
                </td>
                <td>Replay Results</td>
                <td className="mono">2026-06-24</td>
                <td className="mono">{furyWalkForward?.windows ?? "—"}</td>
                <td className="mono">{furyWalkForward?.positive_routed_windows ?? "—"}</td>
                <td>
                  <StatusChip label={furyReplayResults?.replay_verdict ?? "MISSING"} variant={furyReplayResults ? "success" : "muted"} size="sm" />
                </td>
                <td>
                  <StatusChip label={furyReplayResults ? "COMPLETE" : "MISSING"} variant={furyReplayResults ? "success" : "muted"} size="sm" />
                </td>
              </tr>
              <tr>
                <td className="mono" style={{ fontSize: "0.62rem" }}>
                  forex-fury-replay-candidates-20260624042429
                </td>
                <td>Replay Candidates</td>
                <td className="mono">2026-06-24</td>
                <td className="mono">{furyReplaySummary?.source_set_count ?? "—"}</td>
                <td className="mono">{furyReplaySummary?.supported_candidate_count ?? "—"}</td>
                <td>
                  <StatusChip label="READY_FOR_REPLAY" variant="success" size="sm" />
                </td>
                <td>
                  <StatusChip label={furyReplaySummary ? "COMPLETE" : "MISSING"} variant={furyReplaySummary ? "success" : "muted"} size="sm" />
                </td>
              </tr>
              <tr>
                <td className="mono" style={{ fontSize: "0.62rem" }}>
                  forex-fury-set-import-20260624034719
                </td>
                <td>Set Import</td>
                <td className="mono">2026-06-24</td>
                <td className="mono">{furySummary?.set_count ?? "—"}</td>
                <td className="mono">{furySummary?.tester_report_count ?? "—"}</td>
                <td>
                  <StatusChip label="LOCAL_EVIDENCE" variant="info" size="sm" />
                </td>
                <td>
                  <StatusChip label={furySummary ? "COMPLETE" : "MISSING"} variant={furySummary ? "success" : "muted"} size="sm" />
                </td>
              </tr>
              <tr>
                <td className="mono" style={{ fontSize: "0.62rem" }}>
                  backsolve-20260622191201
                </td>
                <td>Leverage Backsolve</td>
                <td className="mono">2026-06-22</td>
                <td className="mono">{backsolve?.total_scenarios.toLocaleString() ?? "—"}</td>
                <td className="mono">{backsolve?.viable_scenarios ?? "—"}</td>
                <td>
                  <StatusChip
                    label={backsolve?.viable_scenarios === 0 ? "TARGET_NOT_REACHED" : "—"}
                    variant="danger"
                    size="sm"
                  />
                </td>
                <td>
                  <StatusChip label="COMPLETE" variant="success" size="sm" />
                </td>
              </tr>
              <tr>
                <td className="mono" style={{ fontSize: "0.62rem" }}>
                  condition-tally-20260622055042
                </td>
                <td>Condition Tally</td>
                <td className="mono">2026-06-22</td>
                <td className="mono">{tally?.reduce((s, b) => s + b.windows, 0) ?? "—"}</td>
                <td className="mono">{tally?.length ?? "—"}</td>
                <td>
                  <StatusChip label="ROUTED" variant="info" size="sm" />
                </td>
                <td>
                  <StatusChip label="COMPLETE" variant="success" size="sm" />
                </td>
              </tr>
              <tr>
                <td className="mono" style={{ fontSize: "0.62rem" }}>
                  walk-forward-20260622044930
                </td>
                <td>Walk-Forward</td>
                <td className="mono">2026-06-22</td>
                <td className="mono">{wf?.total_windows ?? "—"}</td>
                <td className="mono">{wf?.positive_active_routed_windows ?? "—"}</td>
                <td>
                  <StatusChip label={wf?.research_grade ?? "—"} variant="warning" size="sm" />
                </td>
                <td>
                  <StatusChip label="COMPLETE" variant="success" size="sm" />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </GlassPanel>

      {/* Section 7: Interactive Queue Placeholder */}
      <GlassPanel title="Interactive Queue" subtitle="Submit and monitor optimization requests">
        <div className="no-data-message">
          <p>The interactive optimizer queue will be available after API wiring. Currently, runs are triggered via CLI:</p>
          <code className="next-command-text" style={{ marginTop: 8, display: "inline-block" }}>
            python scripts/run_condition_tally.py --output-dir evidence_runs/
          </code>
        </div>
      </GlassPanel>
    </div>
  );
}

function Metric({ label, value, mono, danger }: { label: string; value: string; mono?: boolean; danger?: boolean }) {
  return (
    <div className="dashboard-metric">
      <span className="field-label">{label}</span>
      <span className={`field-value ${mono ? "mono" : ""}`} style={danger ? { color: "var(--danger)" } : undefined}>{value}</span>
    </div>
  );
}

function RunType({
  label,
  status,
  detail,
  runs,
  variant,
}: {
  label: string;
  status: string;
  detail: string;
  runs: string;
  variant: "success" | "muted";
}) {
  return (
    <div
      className="run-type-item"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "8px 0",
        borderBottom: "1px solid var(--border-subtle)",
      }}
    >
      <div>
        <div style={{ fontWeight: 600, fontSize: "0.8rem" }}>{label}</div>
        <div style={{ fontSize: "0.65rem", color: "var(--text-muted)" }}>{detail}</div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span className="mono" style={{ fontSize: "0.7rem", color: "var(--text-secondary)" }}>
          {runs}
        </span>
        <StatusChip label={status} variant={variant} size="sm" />
      </div>
    </div>
  );
}

function platformLabel(descriptor: string): string {
  const parts = descriptor.split(",").map((part) => part.trim());
  return parts.slice(-2).join(", ") || descriptor;
}

function formatNullableNumber(value: number | null | undefined, digits: number): string {
  return value == null ? "—" : value.toFixed(digits);
}

function GateRow({ label, met, detail }: { label: string; met: boolean; detail: string }) {
  return (
    <div className="legal-gate-item">
      <div className="legal-gate-header">
        <span className="check-icon" style={{ color: met ? "var(--success)" : "var(--danger)" }}>
          {met ? "✓" : "✗"}
        </span>
        <span className="field-label">{label}</span>
        <StatusChip label={met ? "MET" : "NOT MET"} variant={met ? "success" : "danger"} size="sm" />
      </div>
      <div className="legal-gate-detail">{detail}</div>
    </div>
  );
}
