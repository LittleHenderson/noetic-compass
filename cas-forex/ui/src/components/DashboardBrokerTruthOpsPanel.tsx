import { lazy, Suspense } from "react";
import { StatusChip } from "./StatusChip";

type ChipVariant = "success" | "warning" | "danger" | "info" | "muted" | "paper";

type SupervisorStatusLike = {
  desired_running?: boolean;
  active_lease?: Record<string, unknown> | null;
  active_lease_is_fresh?: boolean;
  owned_by_this_process?: boolean;
  local_owner_id?: string;
  stop_requested_at?: string | null;
};

const CompoundAddReviewPanel = lazy(() => import("./CompoundAddReviewPanel").then((m) => ({
  default: m.CompoundAddReviewPanel,
})));

export function DashboardBrokerTruthOpsPanel({ ops }: { ops: any }) {
  const {
    canRunWasteDryRun,
    compoundAddFirstLoadMs,
    compoundAddPanelReady,
    brokerTruthBusy,
    brokerTruthMessage,
    brokerTruthReady,
    brokerTruthReport,
    brokerTruthRunning,
    brokerTruthStatus,
    brokerTruthSupervisor,
    currentBrokerTruth,
    currentLiveDryRunLatest,
    currentLiveDryRunReport,
    currentLiveDryRunReview,
    currentMT5MarketDataDiagnostic,
    currentWastePilotPromotion,
    currentWasteProbe,
    dryRunReviewNotes,
    handleAcceptLiveOrderDryRunReview,
    handleDispatchWasteEntryHandoff,
    handleRecoverBrokerTruthSupervisor,
    handleRecoverWasteSupervisor,
    handleRefreshBrokerTruthMonitor,
    handleRefreshLiveOrderDryRun,
    handleRefreshMT5MarketDataDiagnostic,
    handleRefreshWasteEntryHandoff,
    handleRefreshWastePilotPromotion,
    handleRefreshWasteRealCandleProbe,
    handleRunBrokerTruthOnce,
    handleRunMT5MarketDataDiagnostic,
    handleRunWasteCandidateDryRun,
    handleRunWasteRealCandleProbe,
    handleToggleBrokerTruthMonitor,
    latestWasteCandidate,
    liveDryRunAcceptBlocker,
    liveDryRunBlockingCount,
    liveDryRunReviewClear,
    liveDryRunReviewReady,
    liveDryRunStatus,
    liveOrderDryRunBusy,
    liveOrderDryRunMessage,
    mt5FirstSymbol,
    mt5MarketDataBusy,
    mt5MarketDataCheckedCount,
    mt5MarketDataPanelMessage,
    mt5MarketDataReady,
    mt5MarketDataReadyCount,
    mt5MarketDataStatus,
    mt5TerminalPath,
    mt5TerminalProcessCount,
    ownerConfirmDryRunAccept,
    ownerConfirmWasteEntryDispatch,
    setDryRunReviewNotes,
    setOwnerConfirmDryRunAccept,
    setOwnerConfirmWasteEntryDispatch,
    setWasteEntryDispatchNotes,
    state,
    supervisorRecoveryBusy,
    supervisorRecoveryMessage,
    wasteDispatchBlocker,
    wasteDryRunBlocker,
    wasteEntryDispatchNotes,
    wasteEntryHandoff,
    wasteEntryHandoffBusy,
    wasteEntryHandoffMessage,
    wasteEntryHandoffReady,
    wasteEntryHandoffStatus,
    wasteLoop,
    wastePilotBlockingCount,
    wastePilotPromotionBusy,
    wastePilotPromotionMessage,
    wastePilotPromotionReady,
    wastePilotPromotionStatus,
    wasteProbeBrokerGrade,
    wasteProbeBusy,
    wasteProbeCandidate,
    wasteProbeCosts,
    wasteProbeEdge,
    wasteProbeMessage,
    wasteProbeStatus,
    wasteRunnerAnalysis,
    wasteRunnerBrokerGrade,
    wasteRunnerCandleCount,
    wasteRunnerFallback,
    wasteRunnerPairCount,
    wasteRunnerProfile,
    wasteRunnerSource,
    wasteSupervisor,
  } = ops;
  const brokerTruthProtectionStatus = String(brokerTruthReport?.position_protection_status ?? "POSITION_PROTECTION_UNAVAILABLE");
  const brokerTruthUnprotectedCount = Number(brokerTruthReport?.position_protection_unprotected_position_count ?? 0);
  const brokerTruthProtectionDetail = String(brokerTruthReport?.position_protection_detail ?? "").trim();
  const brokerTruthAutoHaltReasonIds = Array.isArray(brokerTruthReport?.monitor_auto_halt_reason_ids)
    ? brokerTruthReport.monitor_auto_halt_reason_ids.filter((value: unknown): value is string => typeof value === "string" && value.trim().length > 0)
    : [];
  const brokerTruthAutoHaltLatched = Boolean(brokerTruthReport?.auto_halt_latched_from_monitor) || brokerTruthAutoHaltReasonIds.length > 0;
  const brokerTruthProtectionPreview = Array.isArray(brokerTruthReport?.position_protection_unprotected_preview)
    ? brokerTruthReport.position_protection_unprotected_preview.filter((value: unknown): value is Record<string, unknown> => isRecord(value))
    : [];
  const brokerTruthIdentityMatch = brokerTruthReport?.mt5_account_identity_matches_config;
  const brokerTruthActualIdentity = formatMt5Identity(brokerTruthReport?.mt5_account, brokerTruthReport?.mt5_account_server);
  const brokerTruthExpectedIdentity = formatMt5Identity(brokerTruthReport?.mt5_expected_account, brokerTruthReport?.mt5_expected_server);

  return (
    <>
      <div className="broker-truth-monitor-strip">
        <div className="broker-truth-monitor-header">
          <div className="auto-halt-title">
            <StatusChip
              label={shortMT5MarketDataStatus(mt5MarketDataStatus)}
              variant={mt5MarketDataVariant(mt5MarketDataStatus)}
              size="sm"
            />
            <StatusChip
              label={mt5MarketDataReady ? "BROKER DATA READY" : "BROKER DATA BLOCKED"}
              variant={mt5MarketDataReady ? "success" : "warning"}
              size="sm"
            />
            <StatusChip
              label={`${mt5MarketDataReadyCount}/${mt5MarketDataCheckedCount} SYMBOLS READY`}
              variant={mt5MarketDataReady ? "success" : "muted"}
              size="sm"
            />
            <StatusChip
              label={currentMT5MarketDataDiagnostic?.broker_touched ? "BROKER TOUCHED" : "READ ONLY"}
              variant={currentMT5MarketDataDiagnostic?.broker_touched ? "danger" : "success"}
              size="sm"
            />
          </div>
          <div className="broker-truth-monitor-actions">
            <button
              className="sweep-action-button"
              type="button"
              onClick={handleRefreshMT5MarketDataDiagnostic}
              disabled={mt5MarketDataBusy}
            >
              Refresh
            </button>
            <button
              className="sweep-action-button"
              type="button"
              onClick={handleRunMT5MarketDataDiagnostic}
              disabled={mt5MarketDataBusy}
            >
              {mt5MarketDataBusy ? "Checking..." : "Check MT5 Data"}
            </button>
          </div>
        </div>
        <div className="broker-truth-monitor-meta">
          <span className="mono">symbol {String(mt5FirstSymbol?.symbol ?? "NAS100/US30")}</span>
          <span className="mono">broker {String(mt5FirstSymbol?.selected_broker_symbol ?? "UNRESOLVED")}</span>
          <span className="mono">tf {String(currentMT5MarketDataDiagnostic?.timeframe ?? "D1")}</span>
          <span className="mono">candles {Number(mt5FirstSymbol?.candle_count ?? 0)}</span>
          <span className="mono">spread {String(mt5FirstSymbol?.spread_pips ?? "NA")}</span>
          <span className="mono">proc {mt5TerminalProcessCount}</span>
          <span className="mono">path {shortLocalPath(mt5TerminalPath)}</span>
          <span className="mono">last {mt5MarketDataTimestampLabel(currentMT5MarketDataDiagnostic)}</span>
          <span>{mt5MarketDataPanelMessage}</span>
        </div>
      </div>

      <div className="broker-truth-monitor-strip">
        <div className="broker-truth-monitor-header">
          <div className="auto-halt-title">
            <StatusChip
              label={wasteLoop?.running ? `WASTE LOOP LIVE: ${wasteLoopStageLabel(wasteLoop)}` : "WASTE LOOP OFFLINE"}
              variant={wasteLoop?.running ? "info" : "warning"}
              size="sm"
            />
            <StatusChip
              label={supervisorOwnershipLabel(wasteSupervisor, wasteLoop?.running ?? false)}
              variant={supervisorOwnershipVariant(wasteSupervisor, wasteLoop?.running ?? false)}
              size="sm"
            />
            <StatusChip
              label={String(wasteLoop?.mode ?? "MODE UNKNOWN")}
              variant={wasteLoop?.mode === "LIVE" ? "danger" : "paper"}
              size="sm"
            />
            <StatusChip
              label={wasteRunnerBrokerGrade ? "RUNNER BROKER TRUTH" : wasteRunnerFallback ? "RUNNER FALLBACK" : "RUNNER SOURCE OPEN"}
              variant={wasteRunnerBrokerGrade ? "success" : wasteRunnerFallback ? "warning" : "muted"}
              size="sm"
            />
          </div>
          <div className="broker-truth-monitor-actions">
            <button
              className="sweep-action-button"
              type="button"
              onClick={handleRecoverWasteSupervisor}
              disabled={supervisorRecoveryBusy}
              title={!supervisorRecoveryAllowed(wasteSupervisor) ? "WASTE lease is healthy; recovery is not needed." : undefined}
            >
              {supervisorRecoveryBusy ? "Recovering..." : "Recover Lease"}
            </button>
          </div>
        </div>
        <div className="broker-truth-monitor-meta">
          <span className="mono">cycles {wasteLoop?.cycles_run ?? 0}</span>
          <span className="mono">stage {String(wasteLoop?.current_stage ?? wasteLoop?.stage ?? wasteLoop?.status ?? "UNKNOWN")}</span>
          <span className="mono">source {wasteRunnerSource}</span>
          <span className="mono">candles {wasteRunnerCandleCount}</span>
          <span className="mono">pairs {wasteRunnerPairCount}</span>
          <span className="mono">profile {wasteRunnerProfile}</span>
          <span className="mono">hyp {String((wasteRunnerAnalysis["hypothesis"] as Record<string, unknown> | undefined)?.["direction"] ?? "NA")}</span>
          <span className="mono">owner {supervisorOwnerLabel(wasteSupervisor)}</span>
          <span className="mono">beat {supervisorHeartbeatLabel(wasteSupervisor)}</span>
          <span>{wasteSupervisor?.next_action ?? wasteLoop?.last_reason ?? "WASTE supervisor has not reported yet."}</span>
        </div>
      </div>

      <div className="broker-truth-monitor-strip">
        <div className="broker-truth-monitor-header">
          <div className="auto-halt-title">
            <StatusChip
              label={shortWasteProbeStatus(wasteProbeStatus)}
              variant={wasteProbeVariant(wasteProbeStatus)}
              size="sm"
            />
            <StatusChip
              label={currentWasteProbe?.broker_touched ? "BROKER TOUCHED" : "BROKER NOT TOUCHED"}
              variant={currentWasteProbe?.broker_touched ? "danger" : "success"}
              size="sm"
            />
            <StatusChip
              label={wasteProbeCandidate ? "REAL CANDLE CANDIDATE" : "NO REAL CANDLE CANDIDATE"}
              variant={wasteProbeCandidate ? "info" : "muted"}
              size="sm"
            />
            <StatusChip
              label={String(wasteProbeEdge?.status ?? "EDGE NA").replace(/_/g, " ")}
              variant={String(wasteProbeEdge?.status ?? "") === "PASS" ? "success" : wasteProbeEdge ? "warning" : "muted"}
              size="sm"
            />
            <StatusChip
              label={wasteProbeBrokerGrade ? "BROKER TRUTH" : currentWasteProbe?.fallback_used ? "FALLBACK DATA" : "CONNECTOR DATA"}
              variant={wasteProbeBrokerGrade ? "success" : currentWasteProbe?.fallback_used ? "warning" : "muted"}
              size="sm"
            />
          </div>
          <div className="broker-truth-monitor-actions">
            <button className="sweep-action-button" type="button" onClick={handleRefreshWasteRealCandleProbe} disabled={wasteProbeBusy}>
              Refresh
            </button>
            <button className="sweep-action-button" type="button" onClick={handleRunWasteRealCandleProbe} disabled={wasteProbeBusy}>
              {wasteProbeBusy ? "Watching..." : "Run Real Candle Probe"}
            </button>
          </div>
        </div>
        <div className="broker-truth-monitor-meta">
          <span className="mono">symbol {String(currentWasteProbe?.symbol ?? wasteProbeCandidate?.symbol ?? "NA")}</span>
          <span className="mono">side {String(wasteProbeCandidate?.direction ?? "NA")}</span>
          <span className="mono">source {String(currentWasteProbe?.source ?? "NA")}</span>
          <span className="mono">cost {String(wasteProbeCosts?.edge_cost_pips ?? "NA")}</span>
          <span className="mono">candles {Number(currentWasteProbe?.candles_count ?? 0)}</span>
          <span className="mono">pairs {Number(currentWasteProbe?.entry_pair_count ?? 0)}</span>
          <span className="mono">last {wasteProbeTimestampLabel(currentWasteProbe)}</span>
          <span>{wasteProbeMessage ?? currentWasteProbe?.next_action ?? currentWasteProbe?.detail ?? "No WASTE real-candle probe has reported yet."}</span>
        </div>
      </div>

      <div className="broker-truth-monitor-strip">
        <div className="broker-truth-monitor-header">
          <div className="auto-halt-title">
            <StatusChip
              label={brokerTruthRunning ? "MONITOR RUNNING" : "MONITOR STOPPED"}
              variant={brokerTruthRunning ? "info" : "warning"}
              size="sm"
            />
            <StatusChip
              label={brokerTruthReady ? "LIVE TRUTH FRESH" : "LIVE TRUTH NOT READY"}
              variant={brokerTruthReady ? "success" : "warning"}
              size="sm"
            />
            <StatusChip
              label={shortBrokerTruthStatus(brokerTruthStatus)}
              variant={brokerTruthVariant(brokerTruthStatus)}
              size="sm"
            />
            <StatusChip
              label={shortPositionProtectionStatus(brokerTruthProtectionStatus)}
              variant={positionProtectionVariant(brokerTruthProtectionStatus, brokerTruthUnprotectedCount)}
              size="sm"
            />
            <StatusChip
              label={brokerTruthAutoHaltLatched ? "MONITOR PAPER FORCE" : "MONITOR WATCHING"}
              variant={brokerTruthAutoHaltLatched ? "danger" : "muted"}
              size="sm"
            />
            <StatusChip
              label={brokerTruthIdentityMatch === true ? "ACCOUNT MATCH" : brokerTruthIdentityMatch === false ? "WRONG ACCOUNT" : "ACCOUNT UNVERIFIED"}
              variant={brokerTruthIdentityMatch === true ? "success" : brokerTruthIdentityMatch === false ? "danger" : "warning"}
              size="sm"
            />
            <StatusChip
              label={supervisorOwnershipLabel(brokerTruthSupervisor, brokerTruthRunning)}
              variant={supervisorOwnershipVariant(brokerTruthSupervisor, brokerTruthRunning)}
              size="sm"
            />
          </div>
          <div className="broker-truth-monitor-actions">
            <button className="sweep-action-button" type="button" onClick={handleRefreshBrokerTruthMonitor} disabled={brokerTruthBusy}>
              Refresh
            </button>
            <button className="sweep-action-button" type="button" onClick={handleRunBrokerTruthOnce} disabled={brokerTruthBusy}>
              Run Check
            </button>
            <button className="sweep-action-button" type="button" onClick={handleToggleBrokerTruthMonitor} disabled={brokerTruthBusy}>
              {brokerTruthRunning ? "Stop Monitor" : "Start Monitor"}
            </button>
            <button
              className="sweep-action-button"
              type="button"
              onClick={handleRecoverBrokerTruthSupervisor}
              disabled={supervisorRecoveryBusy}
              title={!supervisorRecoveryAllowed(brokerTruthSupervisor) ? "Broker-truth lease is healthy; recovery is not needed." : undefined}
            >
              {supervisorRecoveryBusy ? "Recovering..." : "Recover Lease"}
            </button>
          </div>
        </div>
        <div className="broker-truth-monitor-meta">
          <span className="mono">cycles {currentBrokerTruth?.cycles_run ?? 0}</span>
          <span className="mono">mt5 {brokerTruthReport?.mt5_connected ? (brokerTruthReport.mt5_is_demo ? "DEMO" : "LIVE") : "UNAVAILABLE"}</span>
          <span className="mono">actual {brokerTruthActualIdentity}</span>
          <span className="mono">expected {brokerTruthExpectedIdentity}</span>
          <span className="mono">unmatched {brokerTruthReport?.terminal_unmatched_open_position_count ?? "NA"}</span>
          <span className="mono">unprotected {brokerTruthUnprotectedCount}</span>
          <span className="mono">owner {supervisorOwnerLabel(brokerTruthSupervisor)}</span>
          <span className="mono">beat {supervisorHeartbeatLabel(brokerTruthSupervisor)}</span>
          <span>{brokerTruthMessage ?? brokerTruthReport?.next_action ?? "Broker-truth monitor has not reported yet."}</span>
        </div>
        {(brokerTruthAutoHaltReasonIds.length > 0 || brokerTruthProtectionDetail) && (
          <div className="broker-truth-monitor-meta">
            {brokerTruthAutoHaltReasonIds.length > 0 && (
              <span className="mono">
                halt {brokerTruthAutoHaltReasonIds.map(formatAutoHaltCheckId).join(", ")}
              </span>
            )}
            {brokerTruthProtectionDetail && <span>{brokerTruthProtectionDetail}</span>}
          </div>
        )}
        {brokerTruthProtectionPreview.length > 0 && (
          <div className="broker-truth-monitor-meta">
            <span className="mono">tickets {formatUnprotectedPreview(brokerTruthProtectionPreview)}</span>
            <span>Latest broker-visible unprotected positions need owner review before more automated exposure.</span>
          </div>
        )}
        {supervisorRecoveryMessage && (
          <div className="broker-truth-monitor-meta">
            <span>{supervisorRecoveryMessage}</span>
          </div>
        )}
      </div>

      <div className="broker-truth-monitor-strip">
        <div className="broker-truth-monitor-header">
          <div className="auto-halt-title">
            <StatusChip
              label={shortDryRunStatus(liveDryRunStatus)}
              variant={liveDryRunVariant(liveDryRunStatus)}
              size="sm"
            />
            <StatusChip
              label={currentLiveDryRunReport?.broker_touched ? "BROKER TOUCHED" : "BROKER NOT TOUCHED"}
              variant={currentLiveDryRunReport?.broker_touched ? "danger" : "success"}
              size="sm"
            />
            <StatusChip
              label={canRunWasteDryRun ? "MARKET WASTE CANDIDATE" : "NO MARKET CANDIDATE"}
              variant={canRunWasteDryRun ? "info" : "muted"}
              size="sm"
            />
            <StatusChip
              label={shortWasteEntryHandoffStatus(wasteEntryHandoffStatus)}
              variant={wasteEntryHandoffVariant(wasteEntryHandoffStatus, wasteEntryHandoffReady)}
              size="sm"
            />
            <StatusChip
              label={shortWastePilotPromotionStatus(wastePilotPromotionStatus)}
              variant={wastePilotPromotionVariant(wastePilotPromotionStatus, wastePilotPromotionReady)}
              size="sm"
            />
            {wastePilotBlockingCount > 0 && (
              <StatusChip label={`${wastePilotBlockingCount} PILOT BLOCKERS`} variant="warning" size="sm" />
            )}
            {liveDryRunBlockingCount > 0 && (
              <StatusChip label={`${liveDryRunBlockingCount} BLOCKERS`} variant="warning" size="sm" />
            )}
          </div>
          <div className="broker-truth-monitor-actions">
            <button className="sweep-action-button" type="button" onClick={handleRefreshLiveOrderDryRun} disabled={liveOrderDryRunBusy}>
              Refresh
            </button>
            <button
              className="sweep-action-button"
              type="button"
              onClick={handleRunWasteCandidateDryRun}
              disabled={liveOrderDryRunBusy}
              title={wasteDryRunBlocker || undefined}
            >
              {liveOrderDryRunBusy ? "Rehearsing..." : "Run WASTE Dry Run"}
            </button>
            <button className="sweep-action-button" type="button" onClick={handleRefreshWasteEntryHandoff} disabled={wasteEntryHandoffBusy}>
              Check Handoff
            </button>
            <button className="sweep-action-button" type="button" onClick={handleRefreshWastePilotPromotion} disabled={wastePilotPromotionBusy}>
              Check Pilot
            </button>
          </div>
        </div>
        <div className="broker-truth-monitor-meta">
          <span className="mono">order {currentLiveDryRunReport?.order_id ?? currentLiveDryRunLatest?.latest_audit?.order_id ?? "NONE"}</span>
          <span className="mono">side {String(currentLiveDryRunReport?.proposed_intent?.direction ?? latestWasteCandidate?.direction ?? "NA")}</span>
          <span className="mono">symbol {String(currentLiveDryRunReport?.proposed_intent?.symbol ?? latestWasteCandidate?.symbol ?? "NA")}</span>
          <span className="mono">last {dryRunTimestampLabel(currentLiveDryRunReport, currentLiveDryRunLatest)}</span>
          <span>{liveOrderDryRunMessage ?? currentLiveDryRunReport?.next_action ?? currentLiveDryRunLatest?.detail ?? "No live-order dry-run audit has reported yet."}</span>
        </div>
        <div className="auto-halt-clear-row">
          <label className="sweep-confirm">
            <input
              type="checkbox"
              checked={ownerConfirmWasteEntryDispatch}
              onChange={(event) => setOwnerConfirmWasteEntryDispatch(event.target.checked)}
            />
            <span>Owner dispatch</span>
          </label>
          <input
            className="sweep-input"
            value={wasteEntryDispatchNotes}
            onChange={(event) => setWasteEntryDispatchNotes(event.target.value)}
          />
          <button
            className="sweep-action-button"
            type="button"
            onClick={handleDispatchWasteEntryHandoff}
            disabled={wasteEntryHandoffBusy}
            title={wasteDispatchBlocker || undefined}
          >
            Dispatch WASTE
          </button>
        </div>
        <div className="broker-truth-monitor-meta">
          <span className="mono">handoff {wasteEntryHandoff?.status ?? "NONE"}</span>
          <span className="mono">ready {wasteEntryHandoffReady ? "YES" : "NO"}</span>
          <span>{wasteEntryHandoffMessage ?? wasteEntryHandoff?.next_action ?? wasteEntryHandoff?.reason ?? "No WASTE entry handoff status has reported yet."}</span>
        </div>
        <div className="broker-truth-monitor-meta">
          <span className="mono">pilot {currentWastePilotPromotion?.status ?? "NONE"}</span>
          <span className="mono">sequence {wastePilotPromotionReady ? "READY" : "BLOCKED"}</span>
          <span className="mono">pairs {currentWastePilotPromotion?.entry_pair_count ?? "NA"}</span>
          <span>
            {wastePilotPromotionMessage ??
              currentWastePilotPromotion?.next_action ??
              "No WASTE pilot promotion status has reported yet."}
          </span>
        </div>
        <div className="auto-halt-clear-row">
          <StatusChip
            label={liveDryRunReviewClear ? "OWNER ACCEPT CURRENT" : currentLiveDryRunReview?.owner_review_status ?? "OWNER REVIEW OPEN"}
            variant={liveDryRunReviewClear ? "success" : "warning"}
            size="sm"
          />
          <StatusChip
            label={liveDryRunReviewReady ? "EVIDENCE READY" : `${currentLiveDryRunReview?.missing_requirements?.length ?? 0} REVIEW BLOCKERS`}
            variant={liveDryRunReviewReady ? "info" : "warning"}
            size="sm"
          />
          <input
            className="auto-halt-reason-input"
            type="text"
            value={dryRunReviewNotes}
            onChange={(event) => setDryRunReviewNotes(event.target.value)}
            aria-label="Live order dry-run review notes"
          />
          <label className="sweep-confirm-check">
            <input
              type="checkbox"
              checked={ownerConfirmDryRunAccept}
              onChange={(event) => setOwnerConfirmDryRunAccept(event.target.checked)}
            />
            <span>Owner ACCEPT</span>
          </label>
          <button
            className="sweep-action-button"
            type="button"
            onClick={handleAcceptLiveOrderDryRunReview}
            disabled={liveOrderDryRunBusy}
            title={liveDryRunAcceptBlocker || undefined}
          >
            Accept Dry Run
          </button>
        </div>
        {currentLiveDryRunReview?.missing_requirements?.length ? (
          <div className="broker-truth-monitor-meta">
            <span className="mono">missing {currentLiveDryRunReview.missing_requirements.join(", ")}</span>
            <span>{currentLiveDryRunReview.next_action}</span>
          </div>
        ) : null}
        {currentLiveDryRunReport?.checks?.length ? (
          <div className="auto-halt-check-grid">
            {currentLiveDryRunReport.checks.map((check: any) => (
              <div className={`auto-halt-check ${check.passed ? "ok" : "tripped"}`} key={check.check_id}>
                <div className="auto-halt-check-title">
                  <span>{formatAutoHaltCheckId(check.check_id)}</span>
                  <StatusChip label={check.status} variant={check.passed ? "success" : "danger"} size="sm" />
                </div>
                <div className="auto-halt-check-detail">{check.detail}</div>
              </div>
            ))}
          </div>
        ) : null}
      </div>

      {compoundAddPanelReady ? (
        <Suspense fallback={<div className="no-data-message"><p>Compound-add review syncing...</p></div>}>
          <CompoundAddReviewPanel state={state} autoHydrateDelayMs={compoundAddFirstLoadMs} />
        </Suspense>
      ) : (
        <div className="no-data-message"><p>Compound-add review queued...</p></div>
      )}
    </>
  );
}

function formatShortTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatAutoHaltCheckId(value: string): string {
  const labels: Record<string, string> = {
    max_account_drawdown_pct: "Max Drawdown",
    max_consecutive_losses: "Loss Streak",
    live_vs_paper_divergence_pct: "Live vs Paper",
    broker_truth_reconciliation: "Broker Truth",
    terminal_position_reconciliation: "Terminal Reconciliation",
    live_open_positions_crosscheck: "Open Position Crosscheck",
    live_position_stop_loss_protection: "Stop-Loss Protection",
    mt5_account_identity_matches_config: "MT5 Account Identity",
  };
  return labels[value] ?? value.replace(/_/g, " ");
}

function shortPositionProtectionStatus(status: string): string {
  if (status === "ALL_POSITIONS_PROTECTED") return "PROTECTION CLEAR";
  if (status === "UNPROTECTED_POSITIONS") return "UNPROTECTED POSITIONS";
  if (status === "POSITION_PROTECTION_UNAVAILABLE") return "PROTECTION UNAVAILABLE";
  return status.replace(/_/g, " ");
}

function positionProtectionVariant(status: string, unprotectedCount: number): ChipVariant {
  if (status === "UNPROTECTED_POSITIONS" || unprotectedCount > 0) return "danger";
  if (status === "ALL_POSITIONS_PROTECTED") return "success";
  if (status === "POSITION_PROTECTION_UNAVAILABLE") return "warning";
  return "muted";
}

function shortDryRunStatus(status: string): string {
  return status
    .replace(/^DRY_RUN_/, "")
    .replace(/^NO_DRY_RUN_/, "NO ")
    .replace(/_/g, " ");
}

function liveDryRunVariant(status: string): ChipVariant {
  if (status === "DRY_RUN_PASS") return "success";
  if (status === "DRY_RUN_BLOCKED") return "warning";
  if (status === "NO_DRY_RUN_AUDIT_YET") return "warning";
  return "muted";
}

function shortWasteEntryHandoffStatus(status: string): string {
  return status
    .replace(/^WASTE_ENTRY_/, "")
    .replace(/^BLOCKED_WASTE_ENTRY_/, "BLOCKED ")
    .replace(/_DISPATCH_HANDOFF$/, "")
    .replace(/_/g, " ");
}

function wasteEntryHandoffVariant(status: string, ready: boolean): ChipVariant {
  if (ready || status === "WASTE_ENTRY_HANDOFF_REVIEW_READY") return "success";
  if (status === "WASTE_ENTRY_HANDOFF_REVIEW_BLOCKED") return "warning";
  if (status === "BLOCKED_WASTE_ENTRY_DISPATCH_HANDOFF") return "warning";
  return "muted";
}

function shortWastePilotPromotionStatus(status: string): string {
  return status
    .replace(/^WASTE_PILOT_/, "PILOT ")
    .replace(/^NO_WASTE_PILOT_/, "NO PILOT ")
    .replace(/_/g, " ");
}

function wastePilotPromotionVariant(status: string, ready: boolean): ChipVariant {
  if (ready || status === "WASTE_PILOT_READY") return "success";
  if (status === "WASTE_PILOT_BLOCKED") return "warning";
  if (status === "NO_WASTE_PILOT_PROMOTION") return "warning";
  return "muted";
}

function wasteLoopStageLabel(wasteLoop: unknown): string {
  const record = isRecord(wasteLoop) ? wasteLoop : {};
  const raw = String(record.current_stage ?? record.stage ?? record.status ?? "UNKNOWN").toUpperCase();
  if (raw === "NO_TRADE" || raw === "NO TRADE") return "NO TRADE";
  return raw.replace(/_/g, " ");
}

function dryRunTimestampLabel(report: any, latest: any): string {
  const value = report?.generated_at ?? latest?.latest_audit?.timestamp;
  return value ? formatShortTime(value) : "NONE";
}

function shortMT5MarketDataStatus(status: string): string {
  return status
    .replace(/^MT5_MARKET_DATA_/, "")
    .replace(/^NO_MT5_MARKET_DATA_/, "NO ")
    .replace(/_/g, " ");
}

function mt5MarketDataVariant(status: string): ChipVariant {
  if (status === "MT5_MARKET_DATA_READY") return "success";
  if (status === "MT5_MARKET_DATA_NOT_READY") return "warning";
  if (status === "MT5_MARKET_DATA_DIAGNOSTIC_ERROR") return "danger";
  if (status === "NO_MT5_MARKET_DATA_DIAGNOSTIC") return "muted";
  return "info";
}

function mt5MarketDataTimestampLabel(report: any): string {
  const value = report?.generated_at ?? (typeof report?.audit?.timestamp === "string" ? report.audit.timestamp : "");
  return value ? formatShortTime(value) : "NONE";
}

function shortLocalPath(value: string): string {
  if (!value || value === "UNSET") return "UNSET";
  const parts = value.split(/[\\/]+/).filter(Boolean);
  if (parts.length <= 3) return value;
  return `${parts[0]}\\...\\${parts.slice(-2).join("\\")}`;
}

function shortWasteProbeStatus(status: string): string {
  return status
    .replace(/_UNREGISTERED$/, "")
    .replace(/_/g, " ");
}

function wasteProbeVariant(status: string): ChipVariant {
  if (status === "EDGE_PASS_UNREGISTERED") return "success";
  if (status === "EDGE_BLOCKED" || status === "NO_CANDIDATE") return "warning";
  if (status === "PROBE_ERROR" || status === "NO_USABLE_CANDLES") return "danger";
  if (status === "NO_PROBE_RECORDED") return "muted";
  return "info";
}

function wasteProbeTimestampLabel(report: any): string {
  const value = report?.generated_at ?? (typeof report?.audit?.timestamp === "string" ? report.audit.timestamp : "");
  return value ? formatShortTime(value) : "NONE";
}

function formatMt5Identity(login: unknown, server: unknown): string {
  const normalizedServer = String(server ?? "").trim();
  const normalizedLogin = login == null || String(login).trim() === "" ? "?" : `#${String(login).trim()}`;
  if (normalizedLogin === "?" && !normalizedServer) return "UNSET";
  return `${normalizedLogin}@${normalizedServer || "UNKNOWN"}`;
}

function shortBrokerTruthStatus(status: string): string {
  return status
    .replace(/^BROKER_TRUTH_/, "")
    .replace(/^MONITOR_/, "")
    .replace(/_/g, " ");
}

function brokerTruthVariant(status: string): ChipVariant {
  if (status.includes("FAILED")) return "danger";
  if (status.includes("RECONCILED") && !status.includes("WARNINGS")) return "success";
  if (status.includes("WARNINGS") || status.includes("UNAVAILABLE") || status.includes("UNKNOWN")) return "warning";
  return "muted";
}

function supervisorOwnershipLabel(status: SupervisorStatusLike | null | undefined, localRunning: boolean): string {
  if (!status) return "OWNERSHIP UNKNOWN";
  if (status.stop_requested_at || (!status.desired_running && status.active_lease && status.active_lease_is_fresh)) {
    return "STOP REQUESTED";
  }
  if (localRunning && status.owned_by_this_process) return "LOCAL OWNER";
  if (status.active_lease_is_fresh && !status.owned_by_this_process) return "REMOTE OWNER";
  if (status.active_lease && !status.active_lease_is_fresh) return "STALE LEASE";
  if (status.desired_running) return "DESIRED RUNNING";
  return "NO OWNER";
}

function supervisorOwnershipVariant(status: SupervisorStatusLike | null | undefined, localRunning: boolean): ChipVariant {
  const label = supervisorOwnershipLabel(status, localRunning);
  if (label === "LOCAL OWNER") return "success";
  if (label === "REMOTE OWNER" || label === "DESIRED RUNNING") return "info";
  if (label === "STALE LEASE" || label === "STOP REQUESTED") return "warning";
  if (label === "OWNERSHIP UNKNOWN") return "danger";
  return "muted";
}

function supervisorRecoveryAllowed(status: SupervisorStatusLike | null | undefined): boolean {
  if (!status) return false;
  if (status.stop_requested_at) return true;
  if (status.active_lease && status.active_lease_is_fresh === false) return true;
  if (status.active_lease && status.desired_running === false) return true;
  return false;
}

function supervisorOwnerLabel(status: SupervisorStatusLike | null | undefined): string {
  const owner = status?.active_lease?.owner_id ?? status?.local_owner_id;
  if (!owner) return "NONE";
  const text = String(owner);
  return text.length <= 22 ? text : `${text.slice(0, 10)}...${text.slice(-8)}`;
}

function supervisorHeartbeatLabel(status: SupervisorStatusLike | null | undefined): string {
  const heartbeat = status?.active_lease?.last_heartbeat_at;
  return typeof heartbeat === "string" && heartbeat ? formatShortTime(heartbeat) : "NONE";
}

function formatUnprotectedPreview(rows: Array<Record<string, unknown>>): string {
  const items = rows
    .slice(0, 3)
    .map((row) => {
      const symbol = String(row.symbol ?? "NA");
      const ticket = String(row.ticket ?? "NA");
      const side = String(row.side ?? "NA");
      return `${symbol} ${side} #${ticket}`;
    })
    .filter((value) => value.trim().length > 0);
  return items.length > 0 ? items.join(", ") : "NONE";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
