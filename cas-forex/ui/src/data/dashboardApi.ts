import { apiGet } from "./apiCore";
import type { DashboardState } from "../types/evidence";
import type { DashboardPacket } from "./dashboardStartupCache";

type DashboardStateUpdater = (current: DashboardState | null) => DashboardState;

interface DashboardLoadHandlers {
  setState: (updater: DashboardStateUpdater) => void;
  setLoading?: (loading: boolean) => void;
  setError?: (error: string | null) => void;
  isCancelled?: () => boolean;
}

interface DashboardLoadOptions {
  fastFetchDeferMs?: number;
}

const DASHBOARD_FAST_FETCH_DEFER_MS = 350;
const DASHBOARD_FULL_AUTHORITY_BOUNDARY_DEFER_MS = 900;
const DASHBOARD_FULL_UI_READINESS_DEFER_MS = 1_500;
const DASHBOARD_FULL_DAILY_SCHEDULE_DEFER_MS = 2_100;
const DASHBOARD_FULL_DAILY_BUNDLE_DEFER_MS = 2_800;
const DASHBOARD_FULL_WASTE_SAMPLE_SCHEDULER_DEFER_MS = 6_500;
const DASHBOARD_FAST_RETRY_BASE_DELAY_MS = 1_500;
const DASHBOARD_STALE_CACHE_WRITE_IDLE_TIMEOUT_MS = 4_000;

type IdleCallbackHandle = number;
type DashboardHydrationWindow = Window & {
  requestIdleCallback?: (callback: () => void, options?: { timeout?: number }) => IdleCallbackHandle;
};
type DashboardCacheWriterModule = typeof import("./dashboardStartupCacheWriter");

let dashboardCacheWriterPromise: Promise<DashboardCacheWriterModule> | null = null;

function scheduleDashboardHydrationWork(callback: () => void, timeoutMs: number): void {
  const hydrationWindow = window as DashboardHydrationWindow;
  if (hydrationWindow.requestIdleCallback) {
    hydrationWindow.requestIdleCallback(callback, { timeout: timeoutMs });
    return;
  }
  window.setTimeout(callback, timeoutMs);
}

function scheduleDashboardRetryWork(callback: () => void, delayMs: number): void {
  window.setTimeout(() => {
    scheduleDashboardHydrationWork(callback, delayMs);
  }, delayMs);
}

function writeStaleDashboardPacketLater(packet: DashboardPacket | null): void {
  if (typeof window === "undefined" || !packet) return;
  scheduleDashboardHydrationWork(() => {
    dashboardCacheWriterPromise ??= import("./dashboardStartupCacheWriter");
    void dashboardCacheWriterPromise
      .then((module) => module.writeStaleDashboardPacket(packet))
      .catch(() => undefined);
  }, DASHBOARD_STALE_CACHE_WRITE_IDLE_TIMEOUT_MS);
}

export async function fetchDashboardShell(): Promise<DashboardPacket | null> {
  try {
    return await apiGet<DashboardPacket>("/dashboard/shell", 5_000);
  } catch {
    return null;
  }
}

export async function fetchDashboardFast(): Promise<DashboardPacket | null> {
  try {
    return await apiGet<DashboardPacket>("/dashboard/fast", 15_000);
  } catch {
    return null;
  }
}

export async function fetchDailyBundle(): Promise<DashboardState["dailyBundle"] | null> {
  try {
    return await apiGet<DashboardState["dailyBundle"]>("/bundle/daily", 15_000);
  } catch {
    return null;
  }
}

export async function fetchAuthorityBoundary(): Promise<DashboardState["authorityBoundary"] | null> {
  try {
    return await apiGet<DashboardState["authorityBoundary"]>("/settings/authority-boundary", 10_000);
  } catch {
    return null;
  }
}

export async function fetchUiReadiness(): Promise<DashboardState["uiReadiness"] | null> {
  try {
    return await apiGet<DashboardState["uiReadiness"]>("/proof/readiness", 10_000);
  } catch {
    return null;
  }
}

export async function fetchDailySchedule(): Promise<DashboardState["dailySchedule"] | null> {
  try {
    return await apiGet<DashboardState["dailySchedule"]>("/proof/schedule", 10_000);
  } catch {
    return null;
  }
}

export async function fetchWastePaperSampleCollectorScheduler(): Promise<DashboardState["wastePaperSampleCollectorScheduler"] | null> {
  try {
    return await apiGet<DashboardState["wastePaperSampleCollectorScheduler"]>(
      "/waste-loop-control/paper-sample-collector/scheduler",
      10_000,
    );
  } catch {
    return null;
  }
}

function mergeDashboardState(fallback: DashboardState, live: Partial<DashboardState>): DashboardState {
  const hasLiveKey = (key: keyof DashboardState) => Object.prototype.hasOwnProperty.call(live, key);
  const liveOrFallback = <K extends keyof DashboardState>(key: K): DashboardState[K] =>
    hasLiveKey(key) ? (live[key] as DashboardState[K]) : fallback[key];

  return {
    ...fallback,
    ...live,
    adaptive: live.adaptive ?? fallback.adaptive,
    riskBudget: live.riskBudget ?? fallback.riskBudget,
    proofProgress: live.proofProgress ?? fallback.proofProgress,
    ownerControl: live.ownerControl ?? fallback.ownerControl,
    accountLedger: live.accountLedger ?? fallback.accountLedger,
    movementStream: live.movementStream ?? fallback.movementStream,
    accountReconciliation: live.accountReconciliation ?? fallback.accountReconciliation,
    liveReadiness: live.liveReadiness ?? fallback.liveReadiness,
    brokerSyncedRiskPreview: live.brokerSyncedRiskPreview ?? fallback.brokerSyncedRiskPreview,
    mtHistory: live.mtHistory ?? fallback.mtHistory,
    strategyLeads: live.strategyLeads ?? fallback.strategyLeads,
    backsolve: live.backsolve ?? fallback.backsolve,
    conditionTally: live.conditionTally ?? fallback.conditionTally,
    walkForward: live.walkForward ?? fallback.walkForward,
    externalBenchmarks: live.externalBenchmarks ?? fallback.externalBenchmarks,
    forexFurySetImport: liveOrFallback("forexFurySetImport"),
    forexFuryReplayCandidates: liveOrFallback("forexFuryReplayCandidates"),
    forexFuryReplayResults: liveOrFallback("forexFuryReplayResults"),
    agentWorkflowPlan: liveOrFallback("agentWorkflowPlan"),
    agentWorkflowCycle: liveOrFallback("agentWorkflowCycle"),
    agentInformationFlow: liveOrFallback("agentInformationFlow"),
    agentMessageBus: liveOrFallback("agentMessageBus"),
    agentMemory: liveOrFallback("agentMemory"),
    agentResearchQueue: liveOrFallback("agentResearchQueue"),
    strategyDevQueue: liveOrFallback("strategyDevQueue"),
    strategyPatchRunner: liveOrFallback("strategyPatchRunner"),
    dailyLearningRollup: liveOrFallback("dailyLearningRollup"),
    sessionAutowake: liveOrFallback("sessionAutowake"),
    terminalReceiptWatcher: liveOrFallback("terminalReceiptWatcher"),
    terminalBridgeSupervisor: liveOrFallback("terminalBridgeSupervisor"),
    mt4TerminalActivation: liveOrFallback("mt4TerminalActivation"),
    mt4PingRoundtrip: liveOrFallback("mt4PingRoundtrip"),
    mt4TerminalSessionVerifier: liveOrFallback("mt4TerminalSessionVerifier"),
    mt4HistoryExportVerifier: liveOrFallback("mt4HistoryExportVerifier"),
    mt5TerminalApiVerifier: liveOrFallback("mt5TerminalApiVerifier"),
    mt5PaperExecutionVerifier: liveOrFallback("mt5PaperExecutionVerifier"),
    mt5DealHistoryIngest: liveOrFallback("mt5DealHistoryIngest"),
    terminalPositionReconciliation: liveOrFallback("terminalPositionReconciliation"),
    terminalReceiptRecoveryPacket: liveOrFallback("terminalReceiptRecoveryPacket"),
    terminalOperabilityVerifier: liveOrFallback("terminalOperabilityVerifier"),
    terminalReceiptIngest: liveOrFallback("terminalReceiptIngest"),
    terminalHistoryIngest: liveOrFallback("terminalHistoryIngest"),
    mt5Receipt: live.mt5Receipt ?? fallback.mt5Receipt,
    mt5ProbeStatus: live.mt5ProbeStatus ?? fallback.mt5ProbeStatus,
    authorityBoundary: live.authorityBoundary ?? fallback.authorityBoundary,
    runtimeGates: live.runtimeGates ?? fallback.runtimeGates,
    autoHalt: live.autoHalt ?? fallback.autoHalt,
    brokerTruthMonitor: live.brokerTruthMonitor ?? fallback.brokerTruthMonitor,
    wasteLoop: live.wasteLoop ?? fallback.wasteLoop,
    orderAttemptAudit: live.orderAttemptAudit ?? fallback.orderAttemptAudit,
    payoutRecovery: live.payoutRecovery ?? fallback.payoutRecovery,
    aiModel: live.aiModel ?? fallback.aiModel,
    brokerCandidates: live.brokerCandidates ?? fallback.brokerCandidates,
    brokerReality: live.brokerReality ?? fallback.brokerReality,
    livePilot: live.livePilot ?? fallback.livePilot,
    liveOrderDryRun: live.liveOrderDryRun ?? fallback.liveOrderDryRun,
    liveOrderDryRunReview: live.liveOrderDryRunReview ?? fallback.liveOrderDryRunReview,
    compoundAddOrderDryRun: live.compoundAddOrderDryRun ?? fallback.compoundAddOrderDryRun,
    compoundAddOrderDryRunReview: live.compoundAddOrderDryRunReview ?? fallback.compoundAddOrderDryRunReview,
    compoundAddDispatchHandoff: live.compoundAddDispatchHandoff ?? fallback.compoundAddDispatchHandoff,
    wasteDirectionReview: live.wasteDirectionReview ?? fallback.wasteDirectionReview,
    wasteDirectionLearning: liveOrFallback("wasteDirectionLearning"),
    wasteDirectionOutcomeBinding: liveOrFallback("wasteDirectionOutcomeBinding"),
    wastePaperSampleCollector: liveOrFallback("wastePaperSampleCollector"),
    wastePaperSampleCollectorScheduler: live.wastePaperSampleCollectorScheduler ?? fallback.wastePaperSampleCollectorScheduler,
    wasteAdaptationPromotionRule: liveOrFallback("wasteAdaptationPromotionRule"),
    wasteAdaptationPlan: liveOrFallback("wasteAdaptationPlan"),
    wasteAdaptationApplyPreview: liveOrFallback("wasteAdaptationApplyPreview"),
    wasteAdaptationOwnerReview: liveOrFallback("wasteAdaptationOwnerReview"),
    wasteAdaptationPaperApply: liveOrFallback("wasteAdaptationPaperApply"),
    liveRecovery: live.liveRecovery ?? fallback.liveRecovery,
    liveMoneyProgression: live.liveMoneyProgression ?? fallback.liveMoneyProgression,
    orderAttemptRecoveryPacket: live.orderAttemptRecoveryPacket ?? fallback.orderAttemptRecoveryPacket,
    mt5MarketDataDiagnostic: live.mt5MarketDataDiagnostic ?? fallback.mt5MarketDataDiagnostic,
    wasteRealCandleProbe: live.wasteRealCandleProbe ?? fallback.wasteRealCandleProbe,
    pcba: liveOrFallback("pcba"),
  };
}

export async function loadDashboardState(
  initialState: DashboardState,
  handlers: DashboardLoadHandlers,
  options: DashboardLoadOptions = {},
): Promise<void> {
  const isCancelled = handlers.isCancelled ?? (() => false);
  const setLoading = handlers.setLoading ?? (() => undefined);
  const setError = handlers.setError ?? (() => undefined);
  const fastFetchDeferMs = Math.max(0, options.fastFetchDeferMs ?? DASHBOARD_FAST_FETCH_DEFER_MS);

  setLoading(true);
  setError(null);

  const needsFullRetry = (packet: DashboardPacket | null): boolean => (
    packet?.dashboardMeta?.kind !== "shell"
    && (
      packet?.dashboardMeta?.full_cache_status === "warming"
      || packet?.dashboardMeta?.full_cache_status === "refreshing"
    )
  );

  const applyPacket = (packet: DashboardPacket | null): boolean => {
    if (!packet || isCancelled()) return false;
    handlers.setState((current) => mergeDashboardState(current ?? initialState, packet));
    setLoading(false);
    setError(null);
    return true;
  };

  let hasLivePacket = false;

  const fetchAndApplyDashboardShell = async () => {
    const shell = await fetchDashboardShell();
    if (shell && applyPacket(shell)) {
      hasLivePacket = true;
      writeStaleDashboardPacketLater(shell);
    }
  };

  const applyDailyBundle = (dailyBundle: DashboardState["dailyBundle"] | null): boolean => {
    if (!dailyBundle || isCancelled()) return false;
    handlers.setState((current) => mergeDashboardState(current ?? initialState, { dailyBundle }));
    setError(null);
    return true;
  };

  const applyAuthorityBoundary = (authorityBoundary: DashboardState["authorityBoundary"] | null): boolean => {
    if (!authorityBoundary || isCancelled()) return false;
    handlers.setState((current) => mergeDashboardState(current ?? initialState, { authorityBoundary }));
    setError(null);
    return true;
  };

  const applyUiReadiness = (uiReadiness: DashboardState["uiReadiness"] | null): boolean => {
    if (!uiReadiness || isCancelled()) return false;
    handlers.setState((current) => mergeDashboardState(current ?? initialState, { uiReadiness }));
    setError(null);
    return true;
  };

  const applyDailySchedule = (dailySchedule: DashboardState["dailySchedule"] | null): boolean => {
    if (!dailySchedule || isCancelled()) return false;
    handlers.setState((current) => mergeDashboardState(current ?? initialState, { dailySchedule }));
    setError(null);
    return true;
  };

  const applyWastePaperSampleCollectorScheduler = (
    wastePaperSampleCollectorScheduler: DashboardState["wastePaperSampleCollectorScheduler"] | null,
  ): boolean => {
    if (!wastePaperSampleCollectorScheduler || isCancelled()) return false;
    handlers.setState((current) => mergeDashboardState(
      current ?? initialState,
      { wastePaperSampleCollectorScheduler },
    ));
    setError(null);
    return true;
  };

  const fetchAndApplyDailyBundle = async () => {
    applyDailyBundle(await fetchDailyBundle());
  };

  const fetchAndApplyAuthorityBoundary = async () => {
    applyAuthorityBoundary(await fetchAuthorityBoundary());
  };

  const fetchAndApplyUiReadiness = async () => {
    applyUiReadiness(await fetchUiReadiness());
  };

  const fetchAndApplyDailySchedule = async () => {
    applyDailySchedule(await fetchDailySchedule());
  };

  const fetchAndApplyWastePaperSampleCollectorScheduler = async () => {
    applyWastePaperSampleCollectorScheduler(await fetchWastePaperSampleCollectorScheduler());
  };

  let fullAuthorityBoundaryHydrationScheduled = false;
  const scheduleFullAuthorityBoundaryHydration = () => {
    if (fullAuthorityBoundaryHydrationScheduled || typeof window === "undefined" || isCancelled()) return;
    fullAuthorityBoundaryHydrationScheduled = true;
    scheduleDashboardHydrationWork(() => {
      if (isCancelled()) return;
      void fetchAndApplyAuthorityBoundary();
    }, DASHBOARD_FULL_AUTHORITY_BOUNDARY_DEFER_MS);
  };

  let fullUiReadinessHydrationScheduled = false;
  const scheduleFullUiReadinessHydration = () => {
    if (fullUiReadinessHydrationScheduled || typeof window === "undefined" || isCancelled()) return;
    fullUiReadinessHydrationScheduled = true;
    scheduleDashboardHydrationWork(() => {
      if (isCancelled()) return;
      void fetchAndApplyUiReadiness();
    }, DASHBOARD_FULL_UI_READINESS_DEFER_MS);
  };

  let fullDailyScheduleHydrationScheduled = false;
  const scheduleFullDailyScheduleHydration = () => {
    if (fullDailyScheduleHydrationScheduled || typeof window === "undefined" || isCancelled()) return;
    fullDailyScheduleHydrationScheduled = true;
    scheduleDashboardHydrationWork(() => {
      if (isCancelled()) return;
      void fetchAndApplyDailySchedule();
    }, DASHBOARD_FULL_DAILY_SCHEDULE_DEFER_MS);
  };

  let fullWastePaperSampleCollectorSchedulerHydrationScheduled = false;
  const scheduleFullWastePaperSampleCollectorSchedulerHydration = () => {
    if (fullWastePaperSampleCollectorSchedulerHydrationScheduled || typeof window === "undefined" || isCancelled()) return;
    fullWastePaperSampleCollectorSchedulerHydrationScheduled = true;
    scheduleDashboardHydrationWork(() => {
      if (isCancelled()) return;
      void fetchAndApplyWastePaperSampleCollectorScheduler();
    }, DASHBOARD_FULL_WASTE_SAMPLE_SCHEDULER_DEFER_MS);
  };

  let fullDailyBundleHydrationScheduled = false;
  const scheduleFullDailyBundleHydration = () => {
    if (fullDailyBundleHydrationScheduled || typeof window === "undefined" || isCancelled()) return;
    fullDailyBundleHydrationScheduled = true;
    scheduleDashboardHydrationWork(() => {
      if (isCancelled()) return;
      void fetchAndApplyDailyBundle();
    }, DASHBOARD_FULL_DAILY_BUNDLE_DEFER_MS);
  };

  const failIfNoLivePacket = (hasLivePacket: boolean) => {
    if (hasLivePacket || isCancelled()) return;
    handlers.setState(() => initialState);
    setError("Live API shell/fast dashboard unavailable - using local startup state");
    setLoading(false);
  };

  const retryFastDashboard = (attempt = 1) => {
    if (typeof window === "undefined" || attempt > 5 || isCancelled()) return;
    scheduleDashboardRetryWork(() => {
      if (isCancelled()) return;
      void fetchDashboardFast().then((warmed) => {
        if (!applyPacket(warmed)) return;
        writeStaleDashboardPacketLater(warmed);
        if (needsFullRetry(warmed)) retryFastDashboard(attempt + 1);
      });
    }, DASHBOARD_FAST_RETRY_BASE_DELAY_MS * attempt);
  };

  const fetchAndApplyFastDashboard = async (scheduleFullDailyBundle = true) => {
    const fast = await fetchDashboardFast();
    if (fast && applyPacket(fast)) {
      hasLivePacket = true;
      writeStaleDashboardPacketLater(fast);
      if (needsFullRetry(fast)) retryFastDashboard();
      if (scheduleFullDailyBundle) {
        scheduleFullAuthorityBoundaryHydration();
        scheduleFullUiReadinessHydration();
        scheduleFullDailyScheduleHydration();
        scheduleFullWastePaperSampleCollectorSchedulerHydration();
        scheduleFullDailyBundleHydration();
      }
    }
    failIfNoLivePacket(hasLivePacket);
  };

  if (typeof window === "undefined") {
    await fetchAndApplyDashboardShell();
    await fetchAndApplyFastDashboard(false);
    await fetchAndApplyAuthorityBoundary();
    await fetchAndApplyUiReadiness();
    await fetchAndApplyDailySchedule();
    await fetchAndApplyWastePaperSampleCollectorScheduler();
    await fetchAndApplyDailyBundle();
    return;
  }

  void fetchAndApplyDashboardShell();

  window.setTimeout(() => {
    if (isCancelled()) return;
    void fetchAndApplyFastDashboard();
  }, fastFetchDeferMs);
}
