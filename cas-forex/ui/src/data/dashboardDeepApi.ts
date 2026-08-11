import type {
  AccountLedgerState,
  AccountReconciliationReport,
  BrokerSyncedRiskPreview,
  BrokerTruthMonitorStatus,
  BrokerTruthMonitorSupervisorStatus,
  LiveOrderDryRunLatest,
  LiveOrderDryRunReport,
  LiveOrderDryRunReview,
  LiveReadinessReport,
  LiveRecoveryReport,
  MovementStreamState,
  MT5MarketDataDiagnostic,
  PayoutRecoveryStatus,
  StrategyLead,
  WasteEntryDispatchHandoffStatus,
  WasteEntryPilotPromotionStatus,
  WasteRealCandleProbe,
} from "../types/evidence";
import { apiGet, apiPost, apiPostJson } from "./apiCore";
import type {
  AutonomousMoneyMovementStatus,
  AutoHaltReport,
  DispatchLoopState,
  LoopSupervisorStatus,
  VerifiedProfitSweepPolicy,
  VerifiedProfitSweepPolicyUpdate,
  VerifiedProfitSweepPreview,
  VerifiedProfitSweepRequestResult,
  WasteLoopState,
  WasteRealCandleProbeDryRunRequest,
} from "./api";

export type {
  AutonomousMoneyMovementStatus,
  AutoHaltReport,
  DispatchLoopState,
  LoopSupervisorStatus,
  VerifiedProfitSweepPolicy,
  VerifiedProfitSweepPolicyUpdate,
  VerifiedProfitSweepPreview,
  VerifiedProfitSweepRequestResult,
  WasteLoopCandidate,
  WasteLoopState,
  WasteRealCandleProbeDryRunRequest,
} from "./api";

export type {
  BrokerTruthMonitorStatus,
  BrokerTruthMonitorSupervisorStatus,
  LiveOrderDryRunLatest,
  LiveOrderDryRunReport,
  LiveOrderDryRunReview,
  LiveRecoveryReport,
  MT5MarketDataDiagnostic,
  PayoutRecoveryStatus,
  WasteEntryDispatchHandoffStatus,
  WasteEntryPilotPromotionStatus,
  WasteRealCandleProbe,
};

export interface DashboardDeepCacheSnapshot {
  report_kind: "cas_forex_dashboard_deep_cache_snapshot";
  generated_at_iso: string;
  status: string;
  packet_count: number;
  warm_packet_count: number;
  packets: {
    accountReconciliation?: AccountReconciliationReport;
    liveReadiness?: LiveReadinessReport;
    autoHalt?: AutoHaltReport;
    brokerTruthMonitor?: BrokerTruthMonitorStatus;
    wasteLoop?: WasteLoopState;
    verifiedProfitSweepPolicy?: VerifiedProfitSweepPolicy;
    verifiedProfitSweepState?: VerifiedProfitSweepPreview;
    payoutRecovery?: PayoutRecoveryStatus;
    liveRecovery?: LiveRecoveryReport;
    mt5MarketDataDiagnostic?: MT5MarketDataDiagnostic;
    wasteRealCandleProbe?: WasteRealCandleProbe;
    liveOrderDryRun?: LiveOrderDryRunLatest;
    liveOrderDryRunReview?: LiveOrderDryRunReview;
    wasteEntryDispatchHandoff?: WasteEntryDispatchHandoffStatus;
    wasteEntryPilotPromotion?: WasteEntryPilotPromotionStatus;
  };
  claim_boundary: string;
}

export async function fetchDashboardDeepCacheSnapshot(): Promise<DashboardDeepCacheSnapshot | null> {
  try {
    return await apiGet<DashboardDeepCacheSnapshot>("/dashboard/deep-cache");
  } catch {
    return null;
  }
}

export async function fetchVerifiedProfitSweepPolicy(): Promise<VerifiedProfitSweepPolicy | null> {
  try {
    return await apiGet<VerifiedProfitSweepPolicy>("/money-movement/verified-profit-sweep/policy");
  } catch {
    return null;
  }
}

export async function updateVerifiedProfitSweepPolicy(
  patch: VerifiedProfitSweepPolicyUpdate,
  confirmPhrase = "",
): Promise<VerifiedProfitSweepPolicy> {
  const q = confirmPhrase.trim()
    ? `?confirm_phrase=${encodeURIComponent(confirmPhrase.trim())}`
    : "";
  return apiPostJson<VerifiedProfitSweepPolicy, VerifiedProfitSweepPolicyUpdate>(
    `/money-movement/verified-profit-sweep/policy${q}`,
    patch,
  );
}

export async function fetchAutonomousMoneyMovementStatus(): Promise<AutonomousMoneyMovementStatus | null> {
  try {
    return await apiGet<AutonomousMoneyMovementStatus>(
      "/money-movement/verified-profit-sweep/autonomy",
    );
  } catch {
    return null;
  }
}

export async function runAutonomousMoneyMovementOnce(): Promise<AutonomousMoneyMovementStatus> {
  return apiPost<AutonomousMoneyMovementStatus>(
    "/money-movement/verified-profit-sweep/autonomy/run-once",
  );
}

export async function fetchVerifiedProfitSweepState(): Promise<VerifiedProfitSweepPreview | null> {
  try {
    return await apiGet<VerifiedProfitSweepPreview>("/money-movement/verified-profit-sweep/state");
  } catch {
    return null;
  }
}

export async function requestVerifiedProfitSweepCurrent(
  settings?: VerifiedProfitSweepPolicyUpdate,
  confirm = false,
  confirmPhrase = "",
): Promise<VerifiedProfitSweepRequestResult> {
  const params = new URLSearchParams();
  if (confirm) params.set("confirm", "true");
  if (confirmPhrase.trim()) params.set("confirm_phrase", confirmPhrase.trim());
  const q = params.toString() ? `?${params.toString()}` : "";
  return apiPostJson<VerifiedProfitSweepRequestResult, VerifiedProfitSweepPolicyUpdate>(
    `/money-movement/verified-profit-sweep/request-current${q}`,
    settings ?? {},
  );
}

export async function fetchPayoutRecoveryStatus(): Promise<PayoutRecoveryStatus | null> {
  try {
    return await apiGet<PayoutRecoveryStatus>("/money-movement/verified-profit-sweep/payout-recovery");
  } catch {
    return null;
  }
}

export async function fetchLatestLiveOrderDryRun(): Promise<LiveOrderDryRunLatest | null> {
  try {
    return await apiGet<LiveOrderDryRunLatest>("/live-order-dry-run/latest");
  } catch {
    return null;
  }
}

export async function fetchWasteEntryDispatchHandoffStatus(): Promise<WasteEntryDispatchHandoffStatus | null> {
  try {
    return await apiGet<WasteEntryDispatchHandoffStatus>("/live-order-dry-run/waste-entry-order/dispatch-handoff");
  } catch {
    return null;
  }
}

export async function fetchWasteEntryPilotPromotionStatus(): Promise<WasteEntryPilotPromotionStatus | null> {
  try {
    return await apiGet<WasteEntryPilotPromotionStatus>("/live-order-dry-run/waste-entry-order/pilot-promotion");
  } catch {
    return null;
  }
}

export async function dispatchWasteEntryDispatchHandoff(
  notes = "",
  confirmOwnerDispatch = false,
  confirmLiveDispatch = false,
  confirmPhrase = "",
): Promise<WasteEntryDispatchHandoffStatus> {
  const params = new URLSearchParams();
  if (confirmLiveDispatch) params.set("confirm", "true");
  if (confirmPhrase.trim()) params.set("confirm_phrase", confirmPhrase.trim());
  const q = params.toString() ? `?${params.toString()}` : "";
  return apiPostJson<WasteEntryDispatchHandoffStatus, { confirm_owner_dispatch: boolean; notes: string }>(
    `/live-order-dry-run/waste-entry-order/dispatch-handoff/dispatch${q}`,
    { confirm_owner_dispatch: confirmOwnerDispatch, notes },
  );
}

export async function fetchLiveOrderDryRunReview(): Promise<LiveOrderDryRunReview | null> {
  try {
    return await apiGet<LiveOrderDryRunReview>("/live-order-dry-run/review");
  } catch {
    return null;
  }
}

export async function acceptLiveOrderDryRunReview(
  notes = "",
  confirmOwnerAccept = false,
): Promise<LiveOrderDryRunReview> {
  const q = confirmOwnerAccept ? "?confirm_owner_accept=true" : "";
  return apiPostJson<LiveOrderDryRunReview, { notes: string }>(
    `/live-order-dry-run/review/accept${q}`,
    { notes },
  );
}

export async function fetchAutoHaltStatus(): Promise<AutoHaltReport | null> {
  try {
    return await apiGet<AutoHaltReport>("/auto-halt/status");
  } catch {
    return null;
  }
}

export async function clearAutoHalt(reason: string, confirmClear = false): Promise<AutoHaltReport> {
  const q = confirmClear ? "?confirm_clear=true" : "";
  return apiPostJson<AutoHaltReport, { reason: string }>(
    `/auto-halt/clear${q}`,
    { reason: reason.trim() || "OWNER_CLEAR" },
  );
}

export async function triggerAutoHaltEmergencyStop(reason = "OWNER_EMERGENCY_STOP"): Promise<AutoHaltReport> {
  return apiPostJson<AutoHaltReport, { reason: string }>(
    "/auto-halt/emergency-stop",
    { reason: reason.trim() || "OWNER_EMERGENCY_STOP" },
  );
}

export async function fetchBrokerTruthMonitorStatus(): Promise<BrokerTruthMonitorStatus | null> {
  try {
    return await apiGet<BrokerTruthMonitorStatus>("/broker-truth-monitor/status/fast");
  } catch {
    return null;
  }
}

export async function startBrokerTruthMonitor(intervalSeconds = 30): Promise<BrokerTruthMonitorStatus> {
  return apiPostJson<BrokerTruthMonitorStatus, { interval_seconds: number }>(
    "/broker-truth-monitor/start",
    { interval_seconds: intervalSeconds },
  );
}

export async function stopBrokerTruthMonitor(): Promise<BrokerTruthMonitorStatus> {
  return apiPost<BrokerTruthMonitorStatus>("/broker-truth-monitor/stop");
}

export async function runBrokerTruthMonitorOnce(): Promise<BrokerTruthMonitorStatus> {
  return apiPost<BrokerTruthMonitorStatus>("/broker-truth-monitor/run-once");
}

export async function recoverBrokerTruthMonitorSupervisor(confirm = true): Promise<BrokerTruthMonitorSupervisorStatus> {
  const q = confirm ? "?confirm=true" : "";
  return apiPost<BrokerTruthMonitorSupervisorStatus>(`/broker-truth-monitor/supervisor/recover${q}`);
}

export async function fetchLiveRecoveryStatus(): Promise<LiveRecoveryReport | null> {
  try {
    return await apiGet<LiveRecoveryReport>("/live-recovery/status");
  } catch {
    return null;
  }
}

export async function stopDispatchLoop(): Promise<DispatchLoopState> {
  return apiPost<DispatchLoopState>("/dispatch-loop/stop");
}

export async function fetchWasteLoopStatus(): Promise<WasteLoopState | null> {
  try {
    return await apiGet<WasteLoopState>("/waste-loop-control/status/fast");
  } catch {
    return null;
  }
}

export async function fetchWasteRealCandleProbe(): Promise<WasteRealCandleProbe | null> {
  try {
    return await apiGet<WasteRealCandleProbe>("/waste-loop-control/real-candle-probe/latest");
  } catch {
    return null;
  }
}

export async function runWasteRealCandleProbe(
  body: { symbol?: string | null; timeframe?: string; bars?: number; max_pairs?: number } = {},
): Promise<WasteRealCandleProbe> {
  return apiPostJson<WasteRealCandleProbe, typeof body>("/waste-loop-control/real-candle-probe/run", body);
}

export async function runWasteRealCandleProbeDryRun(
  body: WasteRealCandleProbeDryRunRequest,
): Promise<LiveOrderDryRunReport> {
  return apiPostJson<LiveOrderDryRunReport, WasteRealCandleProbeDryRunRequest>(
    "/waste-loop-control/real-candle-probe/dry-run",
    body,
  );
}

export async function fetchMT5MarketDataDiagnostic(): Promise<MT5MarketDataDiagnostic | null> {
  try {
    return await apiGet<MT5MarketDataDiagnostic>("/waste-loop-control/mt5-market-data-diagnostic/latest");
  } catch {
    return null;
  }
}

export async function runMT5MarketDataDiagnostic(
  body: { symbols?: string[] | null; timeframe?: string; bars?: number } = {},
): Promise<MT5MarketDataDiagnostic> {
  return apiPostJson<MT5MarketDataDiagnostic, typeof body>(
    "/waste-loop-control/mt5-market-data-diagnostic/run",
    body,
  );
}

export async function stopWasteLoop(): Promise<WasteLoopState> {
  return apiPost<WasteLoopState>("/waste-loop-control/stop");
}

export async function recoverWasteLoopSupervisor(confirm = true): Promise<LoopSupervisorStatus> {
  const q = confirm ? "?confirm=true" : "";
  return apiPost<LoopSupervisorStatus>(`/waste-loop-control/supervisor/recover${q}`);
}

export async function fetchStrategyLeads(): Promise<StrategyLead[] | null> {
  try {
    return await apiGet<StrategyLead[]>("/strategy/leads/summary");
  } catch {
    return null;
  }
}

export async function fetchAccountLedger(initialInvestment?: number): Promise<AccountLedgerState | null> {
  const suffix = initialInvestment != null ? `?initial_investment=${encodeURIComponent(initialInvestment)}` : "";
  try {
    return await apiGet<AccountLedgerState>(`/account/ledger${suffix}`);
  } catch {
    return null;
  }
}

export async function fetchBrokerSyncedRiskPreview(): Promise<BrokerSyncedRiskPreview | null> {
  try {
    return await apiGet<BrokerSyncedRiskPreview>("/account/broker-sync-risk-preview");
  } catch {
    return null;
  }
}

export async function applyBrokerSyncedRiskReview(): Promise<BrokerSyncedRiskPreview | null> {
  try {
    return await apiPost<BrokerSyncedRiskPreview>("/account/apply-broker-sync-risk-review?confirm_apply=true");
  } catch {
    return null;
  }
}

export async function fetchMovementStream(useProvider = true): Promise<MovementStreamState | null> {
  const suffix = useProvider ? "" : "?use_provider=false";
  try {
    return await apiGet<MovementStreamState>(`/movement/snapshot${suffix}`);
  } catch {
    return null;
  }
}

export async function fetchAccountReconciliation(syncToBroker = false): Promise<AccountReconciliationReport | null> {
  const suffix = syncToBroker ? "?sync_to_broker=true" : "";
  try {
    return await apiGet<AccountReconciliationReport>(`/reconciliation/account${suffix}`);
  } catch {
    return null;
  }
}

export async function fetchLiveReadiness(syncToBroker = false): Promise<LiveReadinessReport | null> {
  const suffix = syncToBroker ? "?sync_to_broker=true" : "";
  try {
    return await apiGet<LiveReadinessReport>(`/readiness/live${suffix}`);
  } catch {
    return null;
  }
}
