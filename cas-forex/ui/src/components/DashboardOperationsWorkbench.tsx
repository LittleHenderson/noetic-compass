import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { GlassPanel } from "./GlassPanel";
import type {
  AutoHaltReport,
  BrokerTruthMonitorStatus,
  LiveOrderDryRunLatest,
  LiveOrderDryRunReport,
  LiveOrderDryRunReview,
  LiveRecoveryReport,
  MT5MarketDataDiagnostic,
  PayoutRecoveryStatus,
  VerifiedProfitSweepPolicy,
  VerifiedProfitSweepPreview,
  VerifiedProfitSweepRequestResult,
  WasteLoopCandidate,
  WasteLoopState,
  WasteEntryDispatchHandoffStatus,
  WasteEntryPilotPromotionStatus,
  WasteRealCandleProbe,
} from "../data/dashboardDeepApi";
import type {
  AccountLedgerState,
  AccountReconciliationReport,
  BrokerSyncedRiskPreview,
  DashboardState,
  LiveReadinessReport,
  MovementStreamState,
  StrategyLead,
} from "../types/evidence";

type DashboardDeepApiModule = typeof import("../data/dashboardDeepApi");
type DeepApiArgs<K extends keyof DashboardDeepApiModule> =
  DashboardDeepApiModule[K] extends (...args: infer Args) => unknown ? Args : never;
type DeepApiReturn<K extends keyof DashboardDeepApiModule> =
  DashboardDeepApiModule[K] extends (...args: any[]) => infer Result ? Result : never;

let dashboardDeepApiPromise: Promise<DashboardDeepApiModule> | null = null;

function loadDashboardDeepApi(): Promise<DashboardDeepApiModule> {
  dashboardDeepApiPromise ??= import("../data/dashboardDeepApi");
  return dashboardDeepApiPromise;
}

async function callDashboardDeepApi<K extends keyof DashboardDeepApiModule>(
  key: K,
  ...args: DeepApiArgs<K>
): Promise<Awaited<DeepApiReturn<K>>> {
  const api = await loadDashboardDeepApi();
  const fn = api[key] as (...callArgs: DeepApiArgs<K>) => DeepApiReturn<K>;
  return await fn(...args);
}

const acceptLiveOrderDryRunReview = (...args: DeepApiArgs<"acceptLiveOrderDryRunReview">) =>
  callDashboardDeepApi("acceptLiveOrderDryRunReview", ...args);
const applyBrokerSyncedRiskReview = (...args: DeepApiArgs<"applyBrokerSyncedRiskReview">) =>
  callDashboardDeepApi("applyBrokerSyncedRiskReview", ...args);
const clearAutoHalt = (...args: DeepApiArgs<"clearAutoHalt">) =>
  callDashboardDeepApi("clearAutoHalt", ...args);
const dispatchWasteEntryDispatchHandoff = (...args: DeepApiArgs<"dispatchWasteEntryDispatchHandoff">) =>
  callDashboardDeepApi("dispatchWasteEntryDispatchHandoff", ...args);
const fetchAccountLedger = (...args: DeepApiArgs<"fetchAccountLedger">) =>
  callDashboardDeepApi("fetchAccountLedger", ...args);
const fetchAccountReconciliation = (...args: DeepApiArgs<"fetchAccountReconciliation">) =>
  callDashboardDeepApi("fetchAccountReconciliation", ...args);
const fetchAutoHaltStatus = (...args: DeepApiArgs<"fetchAutoHaltStatus">) =>
  callDashboardDeepApi("fetchAutoHaltStatus", ...args);
const fetchBrokerSyncedRiskPreview = (...args: DeepApiArgs<"fetchBrokerSyncedRiskPreview">) =>
  callDashboardDeepApi("fetchBrokerSyncedRiskPreview", ...args);
const fetchBrokerTruthMonitorStatus = (...args: DeepApiArgs<"fetchBrokerTruthMonitorStatus">) =>
  callDashboardDeepApi("fetchBrokerTruthMonitorStatus", ...args);
const fetchDashboardDeepCacheSnapshot = (...args: DeepApiArgs<"fetchDashboardDeepCacheSnapshot">) =>
  callDashboardDeepApi("fetchDashboardDeepCacheSnapshot", ...args);
const fetchLatestLiveOrderDryRun = (...args: DeepApiArgs<"fetchLatestLiveOrderDryRun">) =>
  callDashboardDeepApi("fetchLatestLiveOrderDryRun", ...args);
const fetchLiveOrderDryRunReview = (...args: DeepApiArgs<"fetchLiveOrderDryRunReview">) =>
  callDashboardDeepApi("fetchLiveOrderDryRunReview", ...args);
const fetchLiveReadiness = (...args: DeepApiArgs<"fetchLiveReadiness">) =>
  callDashboardDeepApi("fetchLiveReadiness", ...args);
const fetchLiveRecoveryStatus = (...args: DeepApiArgs<"fetchLiveRecoveryStatus">) =>
  callDashboardDeepApi("fetchLiveRecoveryStatus", ...args);
const fetchMovementStream = (...args: DeepApiArgs<"fetchMovementStream">) =>
  callDashboardDeepApi("fetchMovementStream", ...args);
const fetchMT5MarketDataDiagnostic = (...args: DeepApiArgs<"fetchMT5MarketDataDiagnostic">) =>
  callDashboardDeepApi("fetchMT5MarketDataDiagnostic", ...args);
const fetchPayoutRecoveryStatus = (...args: DeepApiArgs<"fetchPayoutRecoveryStatus">) =>
  callDashboardDeepApi("fetchPayoutRecoveryStatus", ...args);
const fetchStrategyLeads = (...args: DeepApiArgs<"fetchStrategyLeads">) =>
  callDashboardDeepApi("fetchStrategyLeads", ...args);
const fetchVerifiedProfitSweepPolicy = (...args: DeepApiArgs<"fetchVerifiedProfitSweepPolicy">) =>
  callDashboardDeepApi("fetchVerifiedProfitSweepPolicy", ...args);
const fetchVerifiedProfitSweepState = (...args: DeepApiArgs<"fetchVerifiedProfitSweepState">) =>
  callDashboardDeepApi("fetchVerifiedProfitSweepState", ...args);
const fetchWasteEntryDispatchHandoffStatus = (...args: DeepApiArgs<"fetchWasteEntryDispatchHandoffStatus">) =>
  callDashboardDeepApi("fetchWasteEntryDispatchHandoffStatus", ...args);
const fetchWasteEntryPilotPromotionStatus = (...args: DeepApiArgs<"fetchWasteEntryPilotPromotionStatus">) =>
  callDashboardDeepApi("fetchWasteEntryPilotPromotionStatus", ...args);
const fetchWasteLoopStatus = (...args: DeepApiArgs<"fetchWasteLoopStatus">) =>
  callDashboardDeepApi("fetchWasteLoopStatus", ...args);
const fetchWasteRealCandleProbe = (...args: DeepApiArgs<"fetchWasteRealCandleProbe">) =>
  callDashboardDeepApi("fetchWasteRealCandleProbe", ...args);
const recoverBrokerTruthMonitorSupervisor = (...args: DeepApiArgs<"recoverBrokerTruthMonitorSupervisor">) =>
  callDashboardDeepApi("recoverBrokerTruthMonitorSupervisor", ...args);
const recoverWasteLoopSupervisor = (...args: DeepApiArgs<"recoverWasteLoopSupervisor">) =>
  callDashboardDeepApi("recoverWasteLoopSupervisor", ...args);
const requestVerifiedProfitSweepCurrent = (...args: DeepApiArgs<"requestVerifiedProfitSweepCurrent">) =>
  callDashboardDeepApi("requestVerifiedProfitSweepCurrent", ...args);
const runBrokerTruthMonitorOnce = (...args: DeepApiArgs<"runBrokerTruthMonitorOnce">) =>
  callDashboardDeepApi("runBrokerTruthMonitorOnce", ...args);
const runMT5MarketDataDiagnostic = (...args: DeepApiArgs<"runMT5MarketDataDiagnostic">) =>
  callDashboardDeepApi("runMT5MarketDataDiagnostic", ...args);
const runWasteRealCandleProbe = (...args: DeepApiArgs<"runWasteRealCandleProbe">) =>
  callDashboardDeepApi("runWasteRealCandleProbe", ...args);
const runWasteRealCandleProbeDryRun = (...args: DeepApiArgs<"runWasteRealCandleProbeDryRun">) =>
  callDashboardDeepApi("runWasteRealCandleProbeDryRun", ...args);
const startBrokerTruthMonitor = (...args: DeepApiArgs<"startBrokerTruthMonitor">) =>
  callDashboardDeepApi("startBrokerTruthMonitor", ...args);
const stopBrokerTruthMonitor = (...args: DeepApiArgs<"stopBrokerTruthMonitor">) =>
  callDashboardDeepApi("stopBrokerTruthMonitor", ...args);
const stopDispatchLoop = (...args: DeepApiArgs<"stopDispatchLoop">) =>
  callDashboardDeepApi("stopDispatchLoop", ...args);
const stopWasteLoop = (...args: DeepApiArgs<"stopWasteLoop">) =>
  callDashboardDeepApi("stopWasteLoop", ...args);
const updateVerifiedProfitSweepPolicy = (...args: DeepApiArgs<"updateVerifiedProfitSweepPolicy">) =>
  callDashboardDeepApi("updateVerifiedProfitSweepPolicy", ...args);

const DashboardEvidencePanels = lazy(() => import("./DashboardEvidencePanels").then((m) => ({
  default: m.DashboardEvidencePanels,
})));
const DashboardSweepOpsPanel = lazy(() => import("./DashboardSweepOpsPanel").then((m) => ({
  default: m.DashboardSweepOpsPanel,
})));
const LiveOperabilityPanel = lazy(() => import("./LiveOperabilityPanel").then((m) => ({
  default: m.LiveOperabilityPanel,
})));

const DASHBOARD_LEADS_FIRST_LOAD_MS = 1_200;
const DASHBOARD_ACCOUNT_LEDGER_FIRST_LOAD_MS = 1_600;
const DASHBOARD_MOVEMENT_FIRST_LOAD_MS = 2_100;
const DASHBOARD_RECONCILIATION_FIRST_LOAD_MS = 2_600;
const DASHBOARD_LIVE_READINESS_FIRST_LOAD_MS = 3_100;
const DASHBOARD_CORE_POLL_MS = 30_000;
const DASHBOARD_LOOP_CORE_FIRST_LOAD_MS = 900;
const DASHBOARD_LOOP_CORE_POLL_MS = 15_000;
const DASHBOARD_DEEP_CACHE_SNAPSHOT_IDLE_TIMEOUT_MS = 700;
const DASHBOARD_SWEEP_FIRST_LOAD_MS = 3_000;
const DASHBOARD_SWEEP_WORKBENCH_IDLE_TIMEOUT_MS = 3_200;
const DASHBOARD_AUTO_HALT_FIRST_LOAD_MS = 3_500;
const DASHBOARD_MARKET_EVIDENCE_FIRST_LOAD_MS = 6_000;
const DASHBOARD_DRY_RUN_EVIDENCE_FIRST_LOAD_MS = 9_000;
const DASHBOARD_HANDOFF_EVIDENCE_FIRST_LOAD_MS = 12_000;
const DASHBOARD_DEEP_EVIDENCE_POLL_MS = 45_000;
const DASHBOARD_EVIDENCE_PANELS_IDLE_TIMEOUT_MS = 2_400;
const DASHBOARD_LIVE_OPERABILITY_IDLE_TIMEOUT_MS = 3_600;
const DASHBOARD_COMPOUND_ADD_IDLE_TIMEOUT_MS = 4_000;
const DASHBOARD_COMPOUND_ADD_FIRST_LOAD_MS = 15_000;

type IdleCallbackHandle = number;
type IdleSchedulerWindow = Window & {
  requestIdleCallback?: (callback: () => void, options?: { timeout?: number }) => IdleCallbackHandle;
  cancelIdleCallback?: (handle: IdleCallbackHandle) => void;
};

type SupervisorStatusLike = {
  desired_running?: boolean;
  active_lease?: Record<string, unknown> | null;
  active_lease_is_fresh?: boolean;
  owned_by_this_process?: boolean;
  local_owner_id?: string;
  local_running?: boolean;
  stop_requested_at?: string | null;
  stop_requested_by?: string | null;
  next_action?: string;
};

interface DashboardOperationsWorkbenchProps {
  state: DashboardState;
}

export function DashboardOperationsWorkbench({ state }: DashboardOperationsWorkbenchProps) {
  const [liveAccountLedger, setLiveAccountLedger] = useState<AccountLedgerState | null>(state.accountLedger ?? null);
  const [liveMovement, setLiveMovement] = useState<MovementStreamState | null>(state.movementStream ?? null);
  const [liveReconciliation, setLiveReconciliation] = useState<AccountReconciliationReport | null>(
    state.accountReconciliation ?? null,
  );
  const [liveReadinessState, setLiveReadinessState] = useState<LiveReadinessReport | null>(state.liveReadiness ?? null);
  const accountLedger = liveAccountLedger ?? state.accountLedger ?? null;
  const movement = liveMovement ?? state.movementStream ?? null;
  const liveReadiness = liveReadinessState ?? state.liveReadiness ?? null;
  const [readinessMode, setReadinessMode] = useState<"default" | "broker-sync">("default");
  const [brokerSyncedReconciliation, setBrokerSyncedReconciliation] = useState<AccountReconciliationReport | null>(null);
  const [brokerSyncedReadiness, setBrokerSyncedReadiness] = useState<LiveReadinessReport | null>(null);
  const [brokerSyncedRiskPreview, setBrokerSyncedRiskPreview] = useState<BrokerSyncedRiskPreview | null>(null);
  const [brokerRiskApplyResult, setBrokerRiskApplyResult] = useState<BrokerSyncedRiskPreview | null>(null);
  const [brokerRiskApplying, setBrokerRiskApplying] = useState(false);
  const [brokerSyncLoading, setBrokerSyncLoading] = useState(false);
  const [brokerSyncReconLoading, setBrokerSyncReconLoading] = useState(false);
  const [strategyLeads, setStrategyLeads] = useState<StrategyLead[] | null>(state.strategyLeads ?? null);
  const [sweepPolicy, setSweepPolicy] = useState<VerifiedProfitSweepPolicy | null>(null);
  const [sweepState, setSweepState] = useState<VerifiedProfitSweepPreview | null>(null);
  const [sweepRequest, setSweepRequest] = useState<VerifiedProfitSweepRequestResult | null>(null);
  const [payoutRecovery, setPayoutRecovery] = useState<PayoutRecoveryStatus | null>(state.payoutRecovery ?? null);
  const [liveRecovery, setLiveRecovery] = useState<LiveRecoveryReport | null>(state.liveRecovery ?? null);
  const [sweepActionMessage, setSweepActionMessage] = useState<string | null>(null);
  const [sweepLoading, setSweepLoading] = useState(false);
  const [sweepSaving, setSweepSaving] = useState(false);
  const [sweepRequesting, setSweepRequesting] = useState(false);
  const [ownerConfirmSweep, setOwnerConfirmSweep] = useState(false);
  const [emergencyStopping, setEmergencyStopping] = useState(false);
  const [emergencyStatus, setEmergencyStatus] = useState<string | null>(null);
  const [autoHalt, setAutoHalt] = useState<AutoHaltReport | null>(state.autoHalt ?? null);
  const [autoHaltLoading, setAutoHaltLoading] = useState(false);
  const [autoHaltClearing, setAutoHaltClearing] = useState(false);
  const [ownerConfirmAutoHaltClear, setOwnerConfirmAutoHaltClear] = useState(false);
  const [autoHaltClearReason, setAutoHaltClearReason] = useState("OWNER_CLEAR");
  const [autoHaltMessage, setAutoHaltMessage] = useState<string | null>(null);
  const [brokerTruthMonitor, setBrokerTruthMonitor] = useState<BrokerTruthMonitorStatus | null>(state.brokerTruthMonitor ?? null);
  const [wasteLoop, setWasteLoop] = useState<WasteLoopState | null>((state.wasteLoop as unknown as WasteLoopState | undefined) ?? null);
  const [mt5MarketDataDiagnostic, setMt5MarketDataDiagnostic] = useState<MT5MarketDataDiagnostic | null>(
    state.mt5MarketDataDiagnostic ?? null,
  );
  const [mt5MarketDataBusy, setMt5MarketDataBusy] = useState(false);
  const [mt5MarketDataMessage, setMt5MarketDataMessage] = useState<string | null>(null);
  const [wasteRealCandleProbe, setWasteRealCandleProbe] = useState<WasteRealCandleProbe | null>(state.wasteRealCandleProbe ?? null);
  const [wasteProbeBusy, setWasteProbeBusy] = useState(false);
  const [wasteProbeMessage, setWasteProbeMessage] = useState<string | null>(null);
  const [liveOrderDryRun, setLiveOrderDryRun] = useState<LiveOrderDryRunLatest | null>(state.liveOrderDryRun ?? null);
  const [liveOrderDryRunReport, setLiveOrderDryRunReport] = useState<LiveOrderDryRunReport | null>(
    liveDryRunReportFromLatest(state.liveOrderDryRun ?? null),
  );
  const [liveOrderDryRunReview, setLiveOrderDryRunReview] = useState<LiveOrderDryRunReview | null>(state.liveOrderDryRunReview ?? null);
  const [wasteEntryHandoff, setWasteEntryHandoff] = useState<WasteEntryDispatchHandoffStatus | null>(null);
  const [wastePilotPromotion, setWastePilotPromotion] = useState<WasteEntryPilotPromotionStatus | null>(state.wasteEntryPilotPromotion ?? null);
  const [liveOrderDryRunBusy, setLiveOrderDryRunBusy] = useState(false);
  const [liveOrderDryRunMessage, setLiveOrderDryRunMessage] = useState<string | null>(null);
  const [ownerConfirmDryRunAccept, setOwnerConfirmDryRunAccept] = useState(false);
  const [dryRunReviewNotes, setDryRunReviewNotes] = useState("Owner reviewed passing dry-run evidence.");
  const [wasteEntryHandoffBusy, setWasteEntryHandoffBusy] = useState(false);
  const [wastePilotPromotionBusy, setWastePilotPromotionBusy] = useState(false);
  const [ownerConfirmWasteEntryDispatch, setOwnerConfirmWasteEntryDispatch] = useState(false);
  const [wasteEntryDispatchNotes, setWasteEntryDispatchNotes] = useState("Owner requested WASTE entry dispatch handoff.");
  const [wasteEntryHandoffMessage, setWasteEntryHandoffMessage] = useState<string | null>(null);
  const [wastePilotPromotionMessage, setWastePilotPromotionMessage] = useState<string | null>(null);
  const [brokerTruthBusy, setBrokerTruthBusy] = useState(false);
  const [brokerTruthMessage, setBrokerTruthMessage] = useState<string | null>(null);
  const [sweepOpsPanelReady, setSweepOpsPanelReady] = useState(false);
  const [evidencePanelsReady, setEvidencePanelsReady] = useState(false);
  const [liveOperabilityPanelReady, setLiveOperabilityPanelReady] = useState(false);
  const [compoundAddPanelReady, setCompoundAddPanelReady] = useState(false);
  const [supervisorRecoveryBusy, setSupervisorRecoveryBusy] = useState(false);
  const [supervisorRecoveryMessage, setSupervisorRecoveryMessage] = useState<string | null>(null);
  const [sweepDraft, setSweepDraft] = useState({
    sweep_pct: 30,
    tax_reserve_pct: 20,
    min_sweep_usd: 25,
  });
  const deepCacheWarmFieldsRef = useRef<Set<string>>(new Set());

  function rememberDeepCachePacket<T>(field: string, packet: T | null | undefined): T | null {
    const ready = readyPacket(packet);
    if (ready) deepCacheWarmFieldsRef.current.add(field);
    return ready;
  }

  function consumeDeepCacheWarmField(field: string): boolean {
    if (!deepCacheWarmFieldsRef.current.has(field)) return false;
    deepCacheWarmFieldsRef.current.delete(field);
    return true;
  }

  function consumeAllDeepCacheWarmFields(fields: string[]): boolean {
    if (!fields.every((field) => deepCacheWarmFieldsRef.current.has(field))) return false;
    fields.forEach((field) => deepCacheWarmFieldsRef.current.delete(field));
    return true;
  }

  const defaultReconciliation = liveReconciliation ?? state.accountReconciliation ?? null;
  const recon = readinessMode === "broker-sync"
    ? brokerSyncedReconciliation ?? defaultReconciliation
    : defaultReconciliation;
  const dashboardBrokerSyncedRiskPreview = state.brokerSyncedRiskPreview ?? null;

  useEffect(() => {
    if (state.wasteLoop) setWasteLoop(state.wasteLoop as unknown as WasteLoopState);
  }, [state.wasteLoop]);

  useEffect(() => {
    if (state.strategyLeads) setStrategyLeads(state.strategyLeads);
  }, [state.strategyLeads]);

  useEffect(() => {
    if (state.accountLedger) setLiveAccountLedger(state.accountLedger);
  }, [state.accountLedger]);

  useEffect(() => {
    if (state.movementStream) setLiveMovement(state.movementStream);
  }, [state.movementStream]);

  useEffect(() => {
    if (state.accountReconciliation) setLiveReconciliation(state.accountReconciliation);
  }, [state.accountReconciliation]);

  useEffect(() => {
    if (state.liveReadiness) setLiveReadinessState(state.liveReadiness);
  }, [state.liveReadiness]);

  useEffect(() => {
    let cancelled = false;
    const cancelDeepCacheSnapshot = scheduleDashboardIdleWork(() => {
      fetchDashboardDeepCacheSnapshot().then((snapshot) => {
        if (cancelled || !snapshot) return;
        const packets = snapshot.packets ?? {};

        const accountReconciliation = rememberDeepCachePacket("accountReconciliation", packets.accountReconciliation);
        if (accountReconciliation) setLiveReconciliation(accountReconciliation);

        const liveReadiness = rememberDeepCachePacket("liveReadiness", packets.liveReadiness);
        if (liveReadiness) setLiveReadinessState(liveReadiness);

        const autoHaltStatus = rememberDeepCachePacket("autoHalt", packets.autoHalt);
        if (autoHaltStatus) setAutoHalt(autoHaltStatus);

        const brokerTruthStatus = rememberDeepCachePacket("brokerTruthMonitor", packets.brokerTruthMonitor);
        if (brokerTruthStatus) setBrokerTruthMonitor(brokerTruthStatus);

        const wasteStatus = rememberDeepCachePacket("wasteLoop", packets.wasteLoop);
        if (wasteStatus) setWasteLoop(wasteStatus);

        const sweepPolicyPacket = rememberDeepCachePacket("verifiedProfitSweepPolicy", packets.verifiedProfitSweepPolicy);
        if (sweepPolicyPacket?.settings) {
          setSweepPolicy(sweepPolicyPacket);
          setSweepDraft({
            sweep_pct: sweepPolicyPacket.settings.sweep_pct,
            tax_reserve_pct: sweepPolicyPacket.settings.tax_reserve_pct,
            min_sweep_usd: sweepPolicyPacket.settings.min_sweep_usd,
          });
        }

        const sweepStatePacket = rememberDeepCachePacket("verifiedProfitSweepState", packets.verifiedProfitSweepState);
        if (sweepStatePacket?.settings) {
          setSweepState(sweepStatePacket);
          if (!sweepPolicyPacket?.settings) {
            setSweepDraft({
              sweep_pct: sweepStatePacket.settings.sweep_pct,
              tax_reserve_pct: sweepStatePacket.settings.tax_reserve_pct,
              min_sweep_usd: sweepStatePacket.settings.min_sweep_usd,
            });
          }
        }

        const payoutRecoveryStatus = rememberDeepCachePacket("payoutRecovery", packets.payoutRecovery);
        if (payoutRecoveryStatus) setPayoutRecovery(payoutRecoveryStatus);

        const liveRecoveryStatus = rememberDeepCachePacket("liveRecovery", packets.liveRecovery);
        if (liveRecoveryStatus) setLiveRecovery(liveRecoveryStatus);

        const mt5Diagnostic = rememberDeepCachePacket("mt5MarketDataDiagnostic", packets.mt5MarketDataDiagnostic);
        if (mt5Diagnostic) setMt5MarketDataDiagnostic(mt5Diagnostic);

        const realCandleProbe = rememberDeepCachePacket("wasteRealCandleProbe", packets.wasteRealCandleProbe);
        if (realCandleProbe) setWasteRealCandleProbe(realCandleProbe);

        const liveDryRun = rememberDeepCachePacket("liveOrderDryRun", packets.liveOrderDryRun);
        if (liveDryRun) {
          setLiveOrderDryRun(liveDryRun);
          setLiveOrderDryRunReport(liveDryRunReportFromLatest(liveDryRun));
        }

        const liveDryRunReview = rememberDeepCachePacket("liveOrderDryRunReview", packets.liveOrderDryRunReview);
        if (liveDryRunReview) setLiveOrderDryRunReview(liveDryRunReview);

        const wasteHandoff = rememberDeepCachePacket("wasteEntryDispatchHandoff", packets.wasteEntryDispatchHandoff);
        if (wasteHandoff) setWasteEntryHandoff(wasteHandoff);

        const wastePilot = rememberDeepCachePacket("wasteEntryPilotPromotion", packets.wasteEntryPilotPromotion);
        if (wastePilot) setWastePilotPromotion(wastePilot);
      });
    }, DASHBOARD_DEEP_CACHE_SNAPSHOT_IDLE_TIMEOUT_MS);
    return () => {
      cancelled = true;
      cancelDeepCacheSnapshot();
    };
  }, []);

  useEffect(() => {
    return scheduleDashboardIdleWork(
      () => setSweepOpsPanelReady(true),
      DASHBOARD_SWEEP_WORKBENCH_IDLE_TIMEOUT_MS,
    );
  }, []);

  useEffect(() => {
    return scheduleDashboardIdleWork(
      () => setCompoundAddPanelReady(true),
      DASHBOARD_COMPOUND_ADD_IDLE_TIMEOUT_MS,
    );
  }, []);

  useEffect(() => {
    return scheduleDashboardIdleWork(
      () => setEvidencePanelsReady(true),
      DASHBOARD_EVIDENCE_PANELS_IDLE_TIMEOUT_MS,
    );
  }, []);

  useEffect(() => {
    return scheduleDashboardIdleWork(
      () => setLiveOperabilityPanelReady(true),
      DASHBOARD_LIVE_OPERABILITY_IDLE_TIMEOUT_MS,
    );
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadStrategyLeads() {
      const leads = await fetchStrategyLeads();
      if (!cancelled && leads) setStrategyLeads(leads);
    }

    const cancelStrategyLeadsPoll = scheduleDashboardRecurringWork(
      () => void loadStrategyLeads(),
      DASHBOARD_LEADS_FIRST_LOAD_MS,
      DASHBOARD_CORE_POLL_MS,
    );
    return () => {
      cancelled = true;
      cancelStrategyLeadsPoll();
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const cancelCorePolls: Array<() => void> = [];

    const scheduleCorePoll = (firstDelayMs: number, load: () => void) => {
      cancelCorePolls.push(scheduleDashboardRecurringWork(load, firstDelayMs, DASHBOARD_CORE_POLL_MS));
    };

    scheduleCorePoll(DASHBOARD_ACCOUNT_LEDGER_FIRST_LOAD_MS, () => {
      void fetchAccountLedger().then((ledger) => {
        if (!cancelled && ledger) setLiveAccountLedger(ledger);
      });
    });

    scheduleCorePoll(DASHBOARD_MOVEMENT_FIRST_LOAD_MS, () => {
      void fetchMovementStream().then((movementState) => {
        if (!cancelled && movementState) setLiveMovement(movementState);
      });
    });

    scheduleCorePoll(DASHBOARD_RECONCILIATION_FIRST_LOAD_MS, () => {
      if (consumeDeepCacheWarmField("accountReconciliation")) return;
      void fetchAccountReconciliation().then((reconciliation) => {
        if (!cancelled && reconciliation) setLiveReconciliation(reconciliation);
      });
    });

    scheduleCorePoll(DASHBOARD_LIVE_READINESS_FIRST_LOAD_MS, () => {
      if (consumeDeepCacheWarmField("liveReadiness")) return;
      void fetchLiveReadiness(false).then((readiness) => {
        if (!cancelled && readiness) setLiveReadinessState(readiness);
      });
    });

    return () => {
      cancelled = true;
      cancelCorePolls.forEach((cancelPoll) => cancelPoll());
    };
  }, []);

  useEffect(() => {
    if (readinessMode !== "broker-sync" || brokerSyncedReadiness) return;
    let cancelled = false;
    let retry: number | undefined;
    setBrokerSyncLoading(true);
    const loadBrokerSyncReadiness = () => {
      fetchLiveReadiness(true)
        .then((payload) => {
          if (cancelled || !payload) return;
          if (isWarmingLiveReadiness(payload)) {
            retry = window.setTimeout(loadBrokerSyncReadiness, 1200);
            return;
          }
          setBrokerSyncedReadiness(payload);
        })
        .finally(() => {
          if (!cancelled) setBrokerSyncLoading(false);
        });
    };
    loadBrokerSyncReadiness();
    return () => {
      cancelled = true;
      if (retry !== undefined) window.clearTimeout(retry);
    };
  }, [brokerSyncedReadiness, readinessMode]);

  useEffect(() => {
    if (readinessMode !== "broker-sync" || brokerSyncedReconciliation) return;
    let cancelled = false;
    let retry: number | undefined;
    setBrokerSyncReconLoading(true);
    const loadBrokerSyncReconciliation = () => {
      fetchAccountReconciliation(true)
        .then((payload) => {
          if (cancelled || !payload) return;
          if (isWarmingAccountReconciliation(payload)) {
            retry = window.setTimeout(loadBrokerSyncReconciliation, 1200);
            return;
          }
          setBrokerSyncedReconciliation(payload);
        })
        .finally(() => {
          if (!cancelled) setBrokerSyncReconLoading(false);
        });
    };
    loadBrokerSyncReconciliation();
    return () => {
      cancelled = true;
      if (retry !== undefined) window.clearTimeout(retry);
    };
  }, [brokerSyncedReconciliation, readinessMode]);

  useEffect(() => {
    if (readinessMode !== "broker-sync" || brokerSyncedRiskPreview || dashboardBrokerSyncedRiskPreview) return;
    let cancelled = false;
    fetchBrokerSyncedRiskPreview().then((payload) => {
      if (!cancelled && payload) setBrokerSyncedRiskPreview(payload);
    });
    return () => {
      cancelled = true;
    };
  }, [brokerSyncedRiskPreview, dashboardBrokerSyncedRiskPreview, readinessMode]);

  useEffect(() => {
    let cancelled = false;

    function loadSweep() {
      if (consumeAllDeepCacheWarmFields([
        "verifiedProfitSweepPolicy",
        "verifiedProfitSweepState",
        "payoutRecovery",
        "liveRecovery",
      ])) {
        if (!cancelled) setSweepLoading(false);
        return;
      }
      if (!cancelled) setSweepLoading(true);
      let pending = 4;
      let sweepPolicyApplied = false;
      const finishSweepRead = () => {
        pending -= 1;
        if (!cancelled && pending <= 0) setSweepLoading(false);
      };
      void fetchVerifiedProfitSweepPolicy()
        .then((policy) => {
          if (cancelled || !policy) return;
          sweepPolicyApplied = true;
          setSweepPolicy(policy);
          setSweepDraft({
            sweep_pct: policy.settings.sweep_pct,
            tax_reserve_pct: policy.settings.tax_reserve_pct,
            min_sweep_usd: policy.settings.min_sweep_usd,
          });
        })
        .finally(finishSweepRead);
      void fetchVerifiedProfitSweepState()
        .then((preview) => {
          if (cancelled || !preview) return;
          setSweepState(preview);
          if (!sweepPolicyApplied) setSweepDraft({
            sweep_pct: preview.settings.sweep_pct,
            tax_reserve_pct: preview.settings.tax_reserve_pct,
            min_sweep_usd: preview.settings.min_sweep_usd,
          });
        })
        .finally(finishSweepRead);
      void fetchPayoutRecoveryStatus()
        .then((recovery) => {
          if (!cancelled && recovery) setPayoutRecovery(recovery);
        })
        .finally(finishSweepRead);
      void fetchLiveRecoveryStatus()
        .then((recoveryGate) => {
          if (!cancelled && recoveryGate) setLiveRecovery(recoveryGate);
        })
        .finally(finishSweepRead);
    }

    const cancelSweepPoll = scheduleDashboardRecurringWork(
      loadSweep,
      DASHBOARD_SWEEP_FIRST_LOAD_MS,
      DASHBOARD_CORE_POLL_MS,
    );
    return () => {
      cancelled = true;
      cancelSweepPoll();
    };
  }, []);

  useEffect(() => {
    if (state.autoHalt) setAutoHalt(state.autoHalt);
  }, [state.autoHalt]);

  useEffect(() => {
    if (state.brokerTruthMonitor) setBrokerTruthMonitor(state.brokerTruthMonitor);
  }, [state.brokerTruthMonitor]);

  useEffect(() => {
    if (state.payoutRecovery) setPayoutRecovery(state.payoutRecovery);
  }, [state.payoutRecovery]);

  useEffect(() => {
    if (state.liveRecovery) setLiveRecovery(state.liveRecovery);
  }, [state.liveRecovery]);

  useEffect(() => {
    if (!state.liveOrderDryRun) return;
    setLiveOrderDryRun(state.liveOrderDryRun);
    setLiveOrderDryRunReport(liveDryRunReportFromLatest(state.liveOrderDryRun));
  }, [state.liveOrderDryRun]);

  useEffect(() => {
    if (state.liveOrderDryRunReview) setLiveOrderDryRunReview(state.liveOrderDryRunReview);
  }, [state.liveOrderDryRunReview]);

  useEffect(() => {
    if (state.wasteRealCandleProbe) setWasteRealCandleProbe(state.wasteRealCandleProbe);
  }, [state.wasteRealCandleProbe]);

  useEffect(() => {
    if (state.mt5MarketDataDiagnostic) setMt5MarketDataDiagnostic(state.mt5MarketDataDiagnostic);
  }, [state.mt5MarketDataDiagnostic]);

  useEffect(() => {
    let cancelled = false;

    async function loadAutoHalt() {
      if (consumeDeepCacheWarmField("autoHalt")) return;
      if (!cancelled) setAutoHaltLoading(true);
      const report = await fetchAutoHaltStatus();
      if (cancelled) return;
      if (report) {
        setAutoHalt(report);
        setAutoHaltMessage(null);
      }
      setAutoHaltLoading(false);
    }

    const cancelAutoHaltPoll = scheduleDashboardRecurringWork(
      () => void loadAutoHalt(),
      DASHBOARD_AUTO_HALT_FIRST_LOAD_MS,
      DASHBOARD_CORE_POLL_MS,
    );
    return () => {
      cancelled = true;
      cancelAutoHaltPoll();
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const cancelLoopPolls: Array<() => void> = [];

    function loadLoopCore() {
      if (!consumeDeepCacheWarmField("wasteLoop")) {
        void fetchWasteLoopStatus().then((wasteStatus) => {
          if (!cancelled && wasteStatus) setWasteLoop(wasteStatus);
        });
      }
      if (!consumeDeepCacheWarmField("brokerTruthMonitor")) {
        void fetchBrokerTruthMonitorStatus().then((status) => {
          if (cancelled || !status) return;
          setBrokerTruthMonitor(status);
          setBrokerTruthMessage(null);
        });
      }
    }

    function loadMarketEvidence() {
      if (!consumeDeepCacheWarmField("mt5MarketDataDiagnostic")) {
        void fetchMT5MarketDataDiagnostic().then((mt5DataStatus) => {
          if (!cancelled && mt5DataStatus) setMt5MarketDataDiagnostic(mt5DataStatus);
        });
      }
      if (!consumeDeepCacheWarmField("wasteRealCandleProbe")) {
        void fetchWasteRealCandleProbe().then((wasteProbeStatus) => {
          if (!cancelled && wasteProbeStatus) setWasteRealCandleProbe(wasteProbeStatus);
        });
      }
    }

    function loadDryRunEvidence() {
      if (!consumeDeepCacheWarmField("liveOrderDryRun")) {
        void fetchLatestLiveOrderDryRun().then((dryRunStatus) => {
          if (cancelled || !dryRunStatus) return;
          setLiveOrderDryRun(dryRunStatus);
          setLiveOrderDryRunReport(liveDryRunReportFromLatest(dryRunStatus));
        });
      }
      if (!consumeDeepCacheWarmField("liveOrderDryRunReview")) {
        void fetchLiveOrderDryRunReview().then((dryRunReview) => {
          if (!cancelled && dryRunReview) setLiveOrderDryRunReview(dryRunReview);
        });
      }
    }

    function loadHandoffEvidence() {
      if (!consumeDeepCacheWarmField("wasteEntryDispatchHandoff")) {
        void fetchWasteEntryDispatchHandoffStatus().then((wasteHandoffStatus) => {
          if (!cancelled && wasteHandoffStatus) setWasteEntryHandoff(wasteHandoffStatus);
        });
      }
      if (!consumeDeepCacheWarmField("wasteEntryPilotPromotion")) {
        void fetchWasteEntryPilotPromotionStatus().then((wastePilotStatus) => {
          if (!cancelled && wastePilotStatus) setWastePilotPromotion(wastePilotStatus);
        });
      }
    }

    cancelLoopPolls.push(
      scheduleDashboardRecurringWork(loadLoopCore, DASHBOARD_LOOP_CORE_FIRST_LOAD_MS, DASHBOARD_LOOP_CORE_POLL_MS),
      scheduleDashboardRecurringWork(loadMarketEvidence, DASHBOARD_MARKET_EVIDENCE_FIRST_LOAD_MS, DASHBOARD_DEEP_EVIDENCE_POLL_MS),
      scheduleDashboardRecurringWork(loadDryRunEvidence, DASHBOARD_DRY_RUN_EVIDENCE_FIRST_LOAD_MS, DASHBOARD_DEEP_EVIDENCE_POLL_MS),
      scheduleDashboardRecurringWork(loadHandoffEvidence, DASHBOARD_HANDOFF_EVIDENCE_FIRST_LOAD_MS, DASHBOARD_DEEP_EVIDENCE_POLL_MS),
    );
    return () => {
      cancelled = true;
      cancelLoopPolls.forEach((cancelPoll) => cancelPoll());
    };
  }, []);

  const activeLiveReadiness =
    readinessMode === "broker-sync" ? brokerSyncedReadiness ?? liveReadiness : liveReadiness;
  const activeBrokerRiskPreview = brokerSyncedRiskPreview ?? dashboardBrokerSyncedRiskPreview;
  const brokerSyncBusy = brokerSyncLoading || brokerSyncReconLoading;
  const brokerSyncUnavailable =
    readinessMode === "broker-sync" && !brokerSyncBusy && brokerSyncedReadiness == null;
  const currentSweep = sweepRequest?.preview ?? sweepState;
  const latestSweepAudit = sweepRequest?.audit ?? sweepPolicy?.latest_audit ?? sweepPolicy?.audit ?? null;
  const isLiveLedger = currentSweep?.winnings.live_money_authorized ?? accountLedger?.live_money_authorized ?? false;
  const liveTradingStatus = activeLiveReadiness?.live_trading_status ?? accountLedger?.live_trading_status ?? "NOT AUTHORIZED";
  const payoutStatus =
    currentSweep?.payout_gate.status ??
    accountLedger?.payout_automation_status ??
    "NOT AUTHORIZED";
  const payoutGateAuthorized = currentSweep?.payout_gate.authorized ?? false;
  const currentLiveRecovery = liveRecovery ?? state.liveRecovery ?? null;
  const liveRecoveryClear = currentLiveRecovery?.recovery_clear_for_live === true;
  const liveRecoveryStatus = currentLiveRecovery?.recovery_status ?? "UNKNOWN";
  const liveRecoveryMissingCount = currentLiveRecovery?.missing_requirements?.length ?? 0;
  const sweepReady = currentSweep?.status === "READY";
  const sweepPayoutReady = sweepReady && liveRecoveryClear;
  const currentAutoHalt = autoHalt ?? state.autoHalt ?? null;
  const autoHaltActive = currentAutoHalt?.halt_active ?? false;
  const autoHaltForcedPaper = currentAutoHalt?.force_paper_mode ?? false;
  const autoHaltChecks = currentAutoHalt?.checks ?? [];
  const autoHaltTriggeredChecks = currentAutoHalt?.triggered_checks ?? [];
  const autoHaltWarming =
    currentAutoHalt?.status === "WARMING" || (currentAutoHalt as { cache_status?: string } | null)?.cache_status === "warming";
  const autoHaltVariant = autoHaltActive ? "danger" : autoHaltWarming ? "warning" : currentAutoHalt ? "success" : "warning";
  const currentBrokerTruth = brokerTruthMonitor ?? state.brokerTruthMonitor ?? null;
  const wasteSupervisor = wasteLoop?.supervisor ?? null;
  const brokerTruthSupervisor = currentBrokerTruth?.supervisor ?? null;
  const brokerTruthReport = currentBrokerTruth?.latest_report ?? null;
  const brokerTruthStatus = currentBrokerTruth?.monitor_status ?? brokerTruthReport?.monitor_status ?? "BROKER_TRUTH_MONITOR_UNKNOWN";
  const brokerTruthRunning = currentBrokerTruth?.running ?? false;
  const brokerTruthReady = currentBrokerTruth?.ready_for_live ?? false;
  const currentPayoutRecovery = payoutRecovery ?? state.payoutRecovery ?? null;
  const latestPayoutAttempt = sweepRequest?.payout_attempt ?? currentPayoutRecovery?.latest_attempt ?? null;
  const payoutAttemptStatus = latestPayoutAttempt?.status ?? "NONE";
  const payoutRecoveryOpen = Boolean(currentPayoutRecovery?.has_pending_recovery);
  const payoutRecoveryLabel = payoutRecoveryOpen ? "RECOVERY OPEN" : latestPayoutAttempt ? shortPayoutAttemptStatus(payoutAttemptStatus) : "NO ATTEMPT";
  const currentLiveDryRunLatest = liveOrderDryRun ?? state.liveOrderDryRun ?? null;
  const currentLiveDryRunReview = liveOrderDryRunReview ?? state.liveOrderDryRunReview ?? null;
  const currentLiveDryRunReport = liveOrderDryRunReport ?? liveDryRunReportFromLatest(currentLiveDryRunLatest);
  const currentMT5MarketDataDiagnostic = mt5MarketDataDiagnostic ?? state.mt5MarketDataDiagnostic ?? null;
  const mt5MarketDataStatus = currentMT5MarketDataDiagnostic?.status ?? "NO_MT5_MARKET_DATA_DIAGNOSTIC";
  const mt5MarketDataReady = mt5MarketDataStatus === "MT5_MARKET_DATA_READY";
  const mt5MarketDataReadyCount = Number(currentMT5MarketDataDiagnostic?.ready_symbol_count ?? 0);
  const mt5MarketDataCheckedCount = Number(currentMT5MarketDataDiagnostic?.checked_symbol_count ?? 0);
  const mt5FirstSymbol = Array.isArray(currentMT5MarketDataDiagnostic?.symbols)
    ? currentMT5MarketDataDiagnostic?.symbols[0] ?? null
    : null;
  const mt5TerminalLocator = (currentMT5MarketDataDiagnostic?.terminal_locator ?? {}) as Record<string, unknown>;
  const mt5TerminalProcessCount = Number(mt5TerminalLocator["running_process_count"] ?? 0);
  const mt5TerminalPath = String(
    mt5TerminalLocator["preferred_path"] ?? mt5TerminalLocator["configured_path"] ?? "UNSET",
  );
  const mt5TerminalNextAction =
    typeof mt5TerminalLocator["next_action"] === "string" && mt5TerminalLocator["next_action"]
      ? String(mt5TerminalLocator["next_action"])
      : null;
  const mt5MarketDataPanelMessage =
    mt5MarketDataMessage ??
    mt5FirstSymbol?.detail ??
    mt5TerminalNextAction ??
    currentMT5MarketDataDiagnostic?.next_action ??
    "No MT5 market-data diagnostic has reported yet.";
  const wasteRunnerCycle = wasteLoop?.durable_cycle ?? null;
  const wasteRunnerWatch = isRecord(wasteRunnerCycle?.watch_state) ? wasteRunnerCycle.watch_state : {};
  const wasteRunnerAnalysis = isRecord(wasteRunnerCycle?.analysis) ? wasteRunnerCycle.analysis : {};
  const wasteRunnerCandidateMeta = isRecord(wasteRunnerCycle?.candidate?.market_state_meta)
    ? wasteRunnerCycle.candidate.market_state_meta
    : {};
  const wasteRunnerBrokerGrade = Boolean(wasteRunnerWatch["broker_grade_market_truth"] ?? wasteRunnerCandidateMeta["broker_grade_market_truth"]);
  const wasteRunnerFallback = Boolean(wasteRunnerWatch["fallback_used"]);
  const wasteRunnerSource = String(wasteRunnerWatch["source"] ?? wasteRunnerCandidateMeta["source"] ?? "NA");
  const wasteRunnerPairCount = Number(wasteRunnerWatch["entry_pair_count"] ?? wasteRunnerCycle?.candidate?.entry_pair_count ?? 0);
  const wasteRunnerCandleCount = Number(wasteRunnerWatch["candles_count"] ?? 0);
  const wasteRunnerProfile = String(wasteRunnerWatch["selected_directional_profile"] ?? wasteRunnerCandidateMeta["selected_directional_profile"] ?? "NA");
  const currentWasteProbe = wasteRealCandleProbe ?? state.wasteRealCandleProbe ?? null;
  const wasteProbeStatus = currentWasteProbe?.status ?? "NO_PROBE_RECORDED";
  const wasteProbeCandidate = currentWasteProbe?.candidate ?? null;
  const wasteProbeEdge = currentWasteProbe?.edge ?? null;
  const wasteProbeMarketState = currentWasteProbe?.market_state ?? {};
  const wasteProbeBrokerGrade = Boolean(currentWasteProbe?.broker_grade_market_truth ?? wasteProbeMarketState["broker_grade_market_truth"]);
  const wasteProbeCosts = (wasteProbeMarketState["execution_costs"] as Record<string, unknown> | undefined) ?? null;
  const liveDryRunStatus = currentLiveDryRunReport?.status ?? currentLiveDryRunLatest?.status ?? "NO_DRY_RUN_AUDIT_YET";
  const liveDryRunBlockingCount = currentLiveDryRunReport?.blocking_reasons?.length ?? 0;
  const liveDryRunReviewClear = Boolean(currentLiveDryRunReview?.dry_run_review_clear_for_live);
  const liveDryRunReviewReady = Boolean(currentLiveDryRunReview?.evidence_ready_for_owner_accept);
  const wasteEntryHandoffStatus = wasteEntryHandoff?.status ?? "NO_WASTE_ENTRY_HANDOFF";
  const wasteEntryHandoffReady = Boolean(wasteEntryHandoff?.would_call_dispatch_if_owner_attempted);
  const currentWastePilotPromotion = wastePilotPromotion ?? state.wasteEntryPilotPromotion ?? null;
  const wastePilotPromotionStatus = currentWastePilotPromotion?.status ?? "NO_WASTE_PILOT_PROMOTION";
  const wastePilotPromotionReady = Boolean(currentWastePilotPromotion?.ready_for_pilot_sequence);
  const wastePilotBlockingCount = currentWastePilotPromotion?.missing_requirements?.length ?? 0;
  const latestWasteCandidate = wasteCandidateForDryRun(currentWasteProbe);
  const canRunWasteDryRun = Boolean(latestWasteCandidate);
  const wasteDryRunBlocker = canRunWasteDryRun
    ? ""
    : "NO_WASTE_CANDIDATE_FOR_DRY_RUN: run Real Candle Probe until a candidate is available.";
  const wasteDispatchBlocker = !ownerConfirmWasteEntryDispatch
    ? "OWNER_DISPATCH_CONFIRM_REQUIRED"
    : !wasteEntryHandoffReady
      ? wasteEntryHandoff?.next_action ?? wasteEntryHandoff?.reason ?? "WASTE_ENTRY_HANDOFF_NOT_READY"
      : "";
  const liveDryRunAcceptBlocker = !ownerConfirmDryRunAccept
    ? "OWNER_ACCEPT_CONFIRM_REQUIRED"
    : !liveDryRunReviewReady
      ? currentLiveDryRunReview?.next_action ??
        currentLiveDryRunReview?.missing_requirements?.join(", ") ??
        "LIVE_DRY_RUN_EVIDENCE_NOT_READY"
      : "";
  const autoHaltClearBlocker = !ownerConfirmAutoHaltClear
    ? "OWNER_CLEAR_CONFIRM_REQUIRED"
    : !autoHaltActive
      ? "AUTO_HALT_NOT_ACTIVE"
      : "";
  const payoutConfirmBlocker = !ownerConfirmSweep
    ? "OWNER_PAYOUT_CONFIRM_REQUIRED"
    : !sweepReady
      ? currentSweep?.reason ?? "NO_VERIFIED_LIVE_PROFIT_READY"
      : !liveRecoveryClear
        ? currentLiveRecovery?.next_action ?? "LIVE_RECOVERY_NOT_CLEAR_FOR_PAYOUT"
        : "";

  async function handleApplyBrokerRiskReview() {
    if (brokerRiskApplying) return;
    setBrokerRiskApplying(true);
    const result = await applyBrokerSyncedRiskReview();
    if (result) {
      setBrokerRiskApplyResult(result);
      setBrokerSyncedRiskPreview(result);
      const refreshed = await fetchLiveReadiness(true);
      if (refreshed) setBrokerSyncedReadiness(refreshed);
    }
    setBrokerRiskApplying(false);
  }

  async function refreshSweepState(nextPolicy?: VerifiedProfitSweepPolicy) {
    const [policy, preview, recovery] = await Promise.all([
      nextPolicy ? Promise.resolve(nextPolicy) : fetchVerifiedProfitSweepPolicy(),
      fetchVerifiedProfitSweepState(),
      fetchPayoutRecoveryStatus(),
    ]);
    if (policy) setSweepPolicy(policy);
    if (preview) setSweepState(preview);
    if (recovery) setPayoutRecovery(recovery);
  }

  async function handleSaveSweepPolicy() {
    if (sweepSaving) return;
    setSweepSaving(true);
    setSweepActionMessage(null);
    const saved = await updateVerifiedProfitSweepPolicy({
      sweep_pct: clamp(sweepDraft.sweep_pct, 0, 100),
      tax_reserve_pct: clamp(sweepDraft.tax_reserve_pct, 0, 100),
      min_sweep_usd: Math.max(0, sweepDraft.min_sweep_usd),
    });
    await refreshSweepState(saved);
    setSweepSaving(false);
  }

  async function handleSweepRequest(confirm: boolean) {
    if (sweepRequesting) return;
    if (confirm && payoutConfirmBlocker) {
      setSweepActionMessage(payoutConfirmBlocker);
      return;
    }
    setSweepActionMessage(null);
    setSweepRequesting(true);
    const result = await requestVerifiedProfitSweepCurrent({
      sweep_pct: clamp(sweepDraft.sweep_pct, 0, 100),
      tax_reserve_pct: clamp(sweepDraft.tax_reserve_pct, 0, 100),
      min_sweep_usd: Math.max(0, sweepDraft.min_sweep_usd),
    }, confirm);
    setSweepRequest(result);
    setSweepState(result.preview);
    await refreshSweepState();
    setOwnerConfirmSweep(false);
    setSweepRequesting(false);
  }

  async function handleEmergencyStop() {
    if (emergencyStopping) return;
    setEmergencyStopping(true);
    const results = await Promise.allSettled([stopWasteLoop(), stopDispatchLoop()]);
    const wasteResult = results[0];
    if (wasteResult.status === "fulfilled") setWasteLoop(wasteResult.value);
    const failed = results.filter((result) => result.status === "rejected").length;
    setEmergencyStatus(failed === 0 ? "STOP_SENT" : `STOP_PARTIAL_${failed}`);
    setEmergencyStopping(false);
  }

  async function handleRefreshAutoHalt() {
    if (autoHaltLoading) return;
    setAutoHaltLoading(true);
    const report = await fetchAutoHaltStatus();
    if (report) {
      setAutoHalt(report);
      setAutoHaltMessage("AUTO_HALT_REFRESHED");
    } else {
      setAutoHaltMessage("AUTO_HALT_UNAVAILABLE");
    }
    setAutoHaltLoading(false);
  }

  async function handleClearAutoHalt() {
    if (autoHaltClearing) return;
    if (autoHaltClearBlocker) {
      setAutoHaltMessage(autoHaltClearBlocker);
      return;
    }
    setAutoHaltClearing(true);
    setAutoHaltMessage(null);
    try {
      const report = await clearAutoHalt(autoHaltClearReason, true);
      setAutoHalt(report);
      setOwnerConfirmAutoHaltClear(false);
      setAutoHaltMessage("AUTO_HALT_CLEAR_SENT");
    } catch (error) {
      setAutoHaltMessage(error instanceof Error ? error.message : "AUTO_HALT_CLEAR_FAILED");
    } finally {
      setAutoHaltClearing(false);
    }
  }

  async function handleRefreshBrokerTruthMonitor() {
    if (brokerTruthBusy) return;
    setBrokerTruthBusy(true);
    const status = await fetchBrokerTruthMonitorStatus();
    if (status) {
      setBrokerTruthMonitor(status);
      setBrokerTruthMessage("BROKER_TRUTH_REFRESHED");
    } else {
      setBrokerTruthMessage("BROKER_TRUTH_UNAVAILABLE");
    }
    setBrokerTruthBusy(false);
  }

  async function handleRunBrokerTruthOnce() {
    if (brokerTruthBusy) return;
    setBrokerTruthBusy(true);
    try {
      const status = await runBrokerTruthMonitorOnce();
      setBrokerTruthMonitor(status);
      setBrokerTruthMessage("BROKER_TRUTH_CHECK_RECORDED");
    } catch (error) {
      setBrokerTruthMessage(error instanceof Error ? error.message : "BROKER_TRUTH_CHECK_FAILED");
    } finally {
      setBrokerTruthBusy(false);
    }
  }

  async function handleToggleBrokerTruthMonitor() {
    if (brokerTruthBusy) return;
    setBrokerTruthBusy(true);
    try {
      const status = brokerTruthRunning
        ? await stopBrokerTruthMonitor()
        : await startBrokerTruthMonitor(currentBrokerTruth?.interval_seconds ?? 120);
      setBrokerTruthMonitor(status);
      setBrokerTruthMessage(brokerTruthRunning ? "BROKER_TRUTH_MONITOR_STOPPED" : "BROKER_TRUTH_MONITOR_STARTED");
    } catch (error) {
      setBrokerTruthMessage(error instanceof Error ? error.message : "BROKER_TRUTH_MONITOR_ACTION_FAILED");
    } finally {
      setBrokerTruthBusy(false);
    }
  }

  async function handleRecoverWasteSupervisor() {
    if (supervisorRecoveryBusy) return;
    if (!supervisorRecoveryAllowed(wasteSupervisor)) {
      setSupervisorRecoveryMessage("WASTE_LEASE_HEALTHY_NO_RECOVERY_NEEDED");
      return;
    }
    setSupervisorRecoveryBusy(true);
    try {
      const recovery = await recoverWasteLoopSupervisor(true);
      const refreshed = await fetchWasteLoopStatus();
      if (refreshed) setWasteLoop(refreshed);
      setSupervisorRecoveryMessage(`WASTE_${recovery.status ?? "RECOVERY_SENT"}`);
    } catch (error) {
      setSupervisorRecoveryMessage(error instanceof Error ? error.message : "WASTE_RECOVERY_FAILED");
    } finally {
      setSupervisorRecoveryBusy(false);
    }
  }

  async function handleRecoverBrokerTruthSupervisor() {
    if (supervisorRecoveryBusy) return;
    if (!supervisorRecoveryAllowed(brokerTruthSupervisor)) {
      setSupervisorRecoveryMessage("BROKER_TRUTH_LEASE_HEALTHY_NO_RECOVERY_NEEDED");
      return;
    }
    setSupervisorRecoveryBusy(true);
    try {
      const recovery = await recoverBrokerTruthMonitorSupervisor(true);
      const refreshed = await fetchBrokerTruthMonitorStatus();
      if (refreshed) setBrokerTruthMonitor(refreshed);
      setSupervisorRecoveryMessage(`BROKER_TRUTH_${recovery.status ?? "RECOVERY_SENT"}`);
    } catch (error) {
      setSupervisorRecoveryMessage(error instanceof Error ? error.message : "BROKER_TRUTH_RECOVERY_FAILED");
    } finally {
      setSupervisorRecoveryBusy(false);
    }
  }

  async function handleRefreshMT5MarketDataDiagnostic() {
    if (mt5MarketDataBusy) return;
    setMt5MarketDataBusy(true);
    try {
      const report = await fetchMT5MarketDataDiagnostic();
      if (report) {
        setMt5MarketDataDiagnostic(report);
        setMt5MarketDataMessage("MT5_MARKET_DATA_DIAGNOSTIC_REFRESHED");
      } else {
        setMt5MarketDataMessage("MT5_MARKET_DATA_DIAGNOSTIC_UNAVAILABLE");
      }
    } catch (error) {
      setMt5MarketDataMessage(error instanceof Error ? error.message : "MT5_MARKET_DATA_DIAGNOSTIC_REFRESH_FAILED");
    } finally {
      setMt5MarketDataBusy(false);
    }
  }

  async function handleRunMT5MarketDataDiagnostic() {
    if (mt5MarketDataBusy) return;
    setMt5MarketDataBusy(true);
    try {
      const report = await runMT5MarketDataDiagnostic({ symbols: ["NAS100", "US30"], timeframe: "D1", bars: 180 });
      setMt5MarketDataDiagnostic(report);
      setMt5MarketDataMessage(report.status);
    } catch (error) {
      setMt5MarketDataMessage(error instanceof Error ? error.message : "MT5_MARKET_DATA_DIAGNOSTIC_FAILED");
    } finally {
      setMt5MarketDataBusy(false);
    }
  }

  async function handleRefreshWasteRealCandleProbe() {
    if (wasteProbeBusy) return;
    setWasteProbeBusy(true);
    try {
      const report = await fetchWasteRealCandleProbe();
      if (report) {
        setWasteRealCandleProbe(report);
        setWasteProbeMessage("WASTE_PROBE_REFRESHED");
      } else {
        setWasteProbeMessage("WASTE_PROBE_UNAVAILABLE");
      }
    } catch (error) {
      setWasteProbeMessage(error instanceof Error ? error.message : "WASTE_PROBE_REFRESH_FAILED");
    } finally {
      setWasteProbeBusy(false);
    }
  }

  async function handleRunWasteRealCandleProbe() {
    if (wasteProbeBusy) return;
    setWasteProbeBusy(true);
    try {
      const report = await runWasteRealCandleProbe({ timeframe: "D1", bars: 180, max_pairs: 80 });
      setWasteRealCandleProbe(report);
      setWasteProbeMessage(report.status);
    } catch (error) {
      setWasteProbeMessage(error instanceof Error ? error.message : "WASTE_PROBE_FAILED");
    } finally {
      setWasteProbeBusy(false);
    }
  }

  async function handleRefreshLiveOrderDryRun() {
    if (liveOrderDryRunBusy) return;
    setLiveOrderDryRunBusy(true);
    try {
      const latest = await fetchLatestLiveOrderDryRun();
      if (latest) {
        setLiveOrderDryRun(latest);
        setLiveOrderDryRunReport(liveDryRunReportFromLatest(latest));
        const review = await fetchLiveOrderDryRunReview();
        if (review) setLiveOrderDryRunReview(review);
        const pilotPromotion = await fetchWasteEntryPilotPromotionStatus();
        if (pilotPromotion) setWastePilotPromotion(pilotPromotion);
        setLiveOrderDryRunMessage("LIVE_DRY_RUN_REFRESHED");
      } else {
        setLiveOrderDryRunMessage("LIVE_DRY_RUN_UNAVAILABLE");
      }
    } catch (error) {
      setLiveOrderDryRunMessage(error instanceof Error ? error.message : "LIVE_DRY_RUN_REFRESH_FAILED");
    } finally {
      setLiveOrderDryRunBusy(false);
    }
  }

  async function handleRunWasteCandidateDryRun() {
    if (liveOrderDryRunBusy) return;
    const candidate = wasteCandidateForDryRun(currentWasteProbe);
    if (!candidate) {
      setLiveOrderDryRunMessage("NO_WASTE_CANDIDATE_FOR_DRY_RUN");
      return;
    }
    setLiveOrderDryRunBusy(true);
    try {
      const report = await runWasteRealCandleProbeDryRun({
        volume: Math.max(0.001, Number(state.livePilot?.max_trade_lots ?? 0.01)),
      });
      setLiveOrderDryRunReport(report);
      setLiveOrderDryRun({
        report_kind: "cas_forex_live_order_dry_run_latest",
        status: report.status,
        broker_touched: false,
        latest_audit: report.audit ?? {
          action: "LIVE_ORDER_DRY_RUN",
          timestamp: report.generated_at,
          status: report.status,
          order_id: report.order_id,
          decision_ref: report.decision_ref,
          payload: report,
        },
      });
      const review = await fetchLiveOrderDryRunReview();
      if (review) setLiveOrderDryRunReview(review);
      const pilotPromotion = await fetchWasteEntryPilotPromotionStatus();
      if (pilotPromotion) setWastePilotPromotion(pilotPromotion);
      setLiveOrderDryRunMessage(report.status);
    } catch (error) {
      setLiveOrderDryRunMessage(error instanceof Error ? error.message : "LIVE_DRY_RUN_FAILED");
    } finally {
      setLiveOrderDryRunBusy(false);
    }
  }

  async function handleRefreshWasteEntryHandoff() {
    if (wasteEntryHandoffBusy) return;
    setWasteEntryHandoffBusy(true);
    try {
      const report = await fetchWasteEntryDispatchHandoffStatus();
      if (report) {
        setWasteEntryHandoff(report);
        setWasteEntryHandoffMessage(report.status);
        const pilotPromotion = await fetchWasteEntryPilotPromotionStatus();
        if (pilotPromotion) setWastePilotPromotion(pilotPromotion);
      } else {
        setWasteEntryHandoffMessage("WASTE_ENTRY_HANDOFF_UNAVAILABLE");
      }
    } catch (error) {
      setWasteEntryHandoffMessage(error instanceof Error ? error.message : "WASTE_ENTRY_HANDOFF_REFRESH_FAILED");
    } finally {
      setWasteEntryHandoffBusy(false);
    }
  }

  async function handleRefreshWastePilotPromotion() {
    if (wastePilotPromotionBusy) return;
    setWastePilotPromotionBusy(true);
    try {
      const report = await fetchWasteEntryPilotPromotionStatus();
      if (report) {
        setWastePilotPromotion(report);
        setWastePilotPromotionMessage(report.status);
      } else {
        setWastePilotPromotionMessage("WASTE_PILOT_PROMOTION_UNAVAILABLE");
      }
    } catch (error) {
      setWastePilotPromotionMessage(error instanceof Error ? error.message : "WASTE_PILOT_PROMOTION_REFRESH_FAILED");
    } finally {
      setWastePilotPromotionBusy(false);
    }
  }

  async function handleDispatchWasteEntryHandoff() {
    if (wasteEntryHandoffBusy) return;
    if (wasteDispatchBlocker) {
      setWasteEntryHandoffMessage(wasteDispatchBlocker);
      return;
    }
    setWasteEntryHandoffBusy(true);
    try {
      const report = await dispatchWasteEntryDispatchHandoff(wasteEntryDispatchNotes, true, false);
      setWasteEntryHandoff(report.handoff_status ?? report);
      setWasteEntryHandoffMessage(report.status);
      const latest = await fetchLatestLiveOrderDryRun();
      if (latest) {
        setLiveOrderDryRun(latest);
        setLiveOrderDryRunReport(liveDryRunReportFromLatest(latest));
      }
      const pilotPromotion = await fetchWasteEntryPilotPromotionStatus();
      if (pilotPromotion) setWastePilotPromotion(pilotPromotion);
    } catch (error) {
      setWasteEntryHandoffMessage(error instanceof Error ? error.message : "WASTE_ENTRY_HANDOFF_DISPATCH_FAILED");
    } finally {
      setWasteEntryHandoffBusy(false);
    }
  }

  async function handleAcceptLiveOrderDryRunReview() {
    if (liveOrderDryRunBusy) return;
    if (liveDryRunAcceptBlocker) {
      setLiveOrderDryRunMessage(liveDryRunAcceptBlocker);
      return;
    }
    setLiveOrderDryRunBusy(true);
    try {
      const review = await acceptLiveOrderDryRunReview(dryRunReviewNotes, true);
      setLiveOrderDryRunReview(review);
      setOwnerConfirmDryRunAccept(false);
      const pilotPromotion = await fetchWasteEntryPilotPromotionStatus();
      if (pilotPromotion) setWastePilotPromotion(pilotPromotion);
      setLiveOrderDryRunMessage(review.review_status);
    } catch (error) {
      setLiveOrderDryRunMessage(error instanceof Error ? error.message : "LIVE_DRY_RUN_ACCEPT_FAILED");
    } finally {
      setLiveOrderDryRunBusy(false);
    }
  }

  return (
    <>
      {sweepOpsPanelReady ? (
        <Suspense fallback={<DashboardSweepOpsPanelFallback />}>
          <DashboardSweepOpsPanel
            ops={{
            activeLiveReadiness,
            autoHaltActive,
            autoHaltCheckVariant,
            autoHaltChecks,
            autoHaltClearBlocker,
            autoHaltClearReason,
            autoHaltClearing,
            autoHaltForcedPaper,
            autoHaltLoading,
            autoHaltMessage,
            autoHaltTriggeredChecks,
            autoHaltVariant,
            autoHaltWarming,
            brokerTruthOps: {
              canRunWasteDryRun,
              compoundAddFirstLoadMs: DASHBOARD_COMPOUND_ADD_FIRST_LOAD_MS,
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
            },
            currentAutoHalt,
            currentLiveRecovery,
            currentPayoutRecovery,
            currentSweep,
            emergencyStatus,
            emergencyStopping,
            formatAutoHaltValue,
            handleClearAutoHalt,
            handleEmergencyStop,
            handleRefreshAutoHalt,
            handleSaveSweepPolicy,
            handleSweepRequest,
            isLiveLedger,
            latestPayoutAttempt,
            latestSweepAudit,
            liveRecoveryClear,
            liveRecoveryMissingCount,
            liveRecoveryStatus,
            liveTradingStatus,
            ownerConfirmAutoHaltClear,
            ownerConfirmSweep,
            payoutAttemptStatus,
            payoutConfirmBlocker,
            payoutGateAuthorized,
            payoutRecoveryLabel,
            payoutRecoveryOpen,
            payoutStatus,
            setAutoHaltClearReason,
            setOwnerConfirmAutoHaltClear,
            setOwnerConfirmSweep,
            setSweepDraft,
            sweepActionMessage,
            sweepDraft,
            sweepLoading,
            sweepPayoutReady,
            sweepReady,
            sweepRequest,
            sweepRequesting,
            sweepSaving,
            }}
          />
        </Suspense>
      ) : (
        <DashboardSweepOpsPanelFallback />
      )}

      {evidencePanelsReady ? (
        <Suspense fallback={<DashboardEvidencePanelsFallback />}>
          <DashboardEvidencePanels
            state={state}
            movement={movement}
            strategyLeads={strategyLeads}
            recon={recon}
          />
        </Suspense>
      ) : (
        <DashboardEvidencePanelsFallback />
      )}

      {liveOperabilityPanelReady ? (
        <Suspense fallback={<LiveOperabilityPanelFallback />}>
          <LiveOperabilityPanel
            activeLiveReadiness={activeLiveReadiness}
            readinessMode={readinessMode}
            onReadinessModeChange={setReadinessMode}
            brokerSyncBusy={brokerSyncBusy}
            brokerSyncUnavailable={brokerSyncUnavailable}
            activeBrokerRiskPreview={activeBrokerRiskPreview}
            brokerRiskApplying={brokerRiskApplying}
            brokerRiskApplyResult={brokerRiskApplyResult}
            onApplyBrokerRiskReview={handleApplyBrokerRiskReview}
          />
        </Suspense>
      ) : (
        <LiveOperabilityPanelFallback />
      )}
    </>
  );
}

function DashboardEvidencePanelsFallback() {
  return (
    <GlassPanel title="Evidence + Route Panels" subtitle="Syncing below-fold tables" variant="info">
      <div className="dashboard-grid-3col">
        <div className="metric-stack" style={{ padding: 0 }}>
          <Metric label="Movement" value="SYNCING" mono />
          <Metric label="Routes" value="QUEUED" mono />
        </div>
        <div className="metric-stack" style={{ padding: 0 }}>
          <Metric label="Daily Summary" value="SYNCING" mono />
          <Metric label="Strategy Leads" value="QUEUED" mono />
        </div>
        <div className="metric-stack" style={{ padding: 0 }}>
          <Metric label="Reconciliation" value="SYNCING" mono warning />
          <Metric label="Evidence Chain" value="READ ONLY" mono />
        </div>
      </div>
    </GlassPanel>
  );
}

function DashboardSweepOpsPanelFallback() {
  return (
    <GlassPanel title="Verified Profit Sweep" subtitle="Syncing payout and live-protection controls" variant="warning">
      <div className="dashboard-grid-3col">
        <div className="metric-stack" style={{ padding: 0 }}>
          <Metric label="Payment" value="PAYMENT SETUP PENDING" warning />
          <Metric label="Sweep" value="SYNCING" mono />
        </div>
        <div className="metric-stack" style={{ padding: 0 }}>
          <Metric label="Auto-Halt" value="SYNCING" mono warning />
          <Metric label="Broker Truth" value="QUEUED" mono />
        </div>
        <div className="metric-stack" style={{ padding: 0 }}>
          <Metric label="Live Orders" value="OWNER GATED" mono warning />
          <Metric label="Payout" value="NOT MOVING MONEY" mono />
        </div>
      </div>
    </GlassPanel>
  );
}

function LiveOperabilityPanelFallback() {
  return (
    <GlassPanel title="Live Operability Checklist" subtitle="Syncing owner-gated review surface" variant="warning">
      <div className="dashboard-grid-3col">
        <div className="metric-stack" style={{ padding: 0 }}>
          <Metric label="Live Gate" value="OWNER GATED" mono warning />
          <Metric label="Broker Sync" value="SYNCING" mono />
        </div>
        <div className="metric-stack" style={{ padding: 0 }}>
          <Metric label="Risk Review" value="PENDING" mono warning />
          <Metric label="Evidence" value="READ ONLY" mono />
        </div>
        <div className="metric-stack" style={{ padding: 0 }}>
          <Metric label="Orders" value="NO LIVE DISPATCH" mono warning />
          <Metric label="Status" value="WAITING" mono />
        </div>
      </div>
    </GlassPanel>
  );
}

function scheduleDashboardIdleWork(callback: () => void, timeoutMs: number): () => void {
  const idleWindow = window as IdleSchedulerWindow;
  if (idleWindow.requestIdleCallback) {
    const id = idleWindow.requestIdleCallback(callback, { timeout: timeoutMs });
    return () => idleWindow.cancelIdleCallback?.(id);
  }

  const id = window.setTimeout(callback, timeoutMs);
  return () => window.clearTimeout(id);
}

function scheduleDashboardRecurringWork(callback: () => void, firstDelayMs: number, intervalMs: number): () => void {
  let interval: number | undefined;
  const cancelFirstLoad = scheduleDashboardIdleWork(() => {
    callback();
    interval = window.setInterval(callback, intervalMs);
  }, firstDelayMs);

  return () => {
    cancelFirstLoad();
    if (interval !== undefined) window.clearInterval(interval);
  };
}

function clamp(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min;
  return Math.min(max, Math.max(min, value));
}

function formatAutoHaltValue(value: unknown): string {
  if (value == null) return "NA";
  if (typeof value === "number") return Number.isFinite(value) ? value.toFixed(Math.abs(value) >= 100 ? 0 : 2) : "NA";
  if (typeof value === "boolean") return value ? "YES" : "NO";
  return String(value);
}

function liveDryRunReportFromLatest(latest: LiveOrderDryRunLatest | null | undefined): LiveOrderDryRunReport | null {
  if (!latest) return null;
  const auditPayload = latest.latest_audit?.payload;
  if (auditPayload && isRecord(auditPayload) && auditPayload["report_kind"] === "cas_forex_live_order_dry_run") {
    return auditPayload as unknown as LiveOrderDryRunReport;
  }
  return null;
}

function wasteCandidateForDryRun(realCandleProbe: WasteRealCandleProbe | null | undefined): WasteLoopCandidate | null {
  return marketBackedWasteCandidate(realCandleProbe?.candidate);
}

function marketBackedWasteCandidate(candidate: WasteLoopCandidate | Record<string, unknown> | null | undefined): WasteLoopCandidate | null {
  if (!candidate || !isRecord(candidate)) return null;
  const marketStateMeta = isRecord(candidate["market_state_meta"]) ? candidate["market_state_meta"] : {};
  const pairCount = Number(candidate["entry_pair_count"] ?? marketStateMeta["entry_pair_count"] ?? 0);
  const source = String(marketStateMeta["source"] ?? "");
  const brokerGrade = Boolean(marketStateMeta["broker_grade_market_truth"]);
  const hasRealData = brokerGrade || pairCount > 0 || source.toUpperCase().includes("MT5") || source.toUpperCase().includes("CANDLE");
  return hasRealData ? candidate as WasteLoopCandidate : null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function readyPacket<T>(packet: T | null | undefined): T | null {
  if (!packet || !isRecord(packet)) return null;
  const record = packet as Record<string, unknown>;
  return record["cache_status"] === "warming" ? null : packet;
}

function isWarmingLiveReadiness(report: LiveReadinessReport): boolean {
  const cacheStatus = (report as { cache_status?: string }).cache_status;
  const total = Number(report.checks_total ?? 0);
  return cacheStatus === "warming" || total <= 0;
}

function isWarmingAccountReconciliation(report: AccountReconciliationReport): boolean {
  const cacheStatus = (report as { cache_status?: string }).cache_status;
  const checkCount = Array.isArray(report.checks) ? report.checks.length : 0;
  return cacheStatus === "warming" || checkCount <= 0;
}

function autoHaltCheckVariant(status: string): "success" | "warning" | "danger" | "info" | "muted" | "paper" {
  if (status === "OK") return "success";
  if (status === "TRIGGERED" || status === "BLOCKED") return "danger";
  if (status === "UNKNOWN" || status === "UNAVAILABLE") return "warning";
  return "info";
}

function shortPayoutAttemptStatus(status: string): string {
  return status.replace(/^PAYOUT_/, "").replace(/_/g, " ");
}

function supervisorRecoveryAllowed(status: SupervisorStatusLike | null | undefined): boolean {
  if (!status) return false;
  if (status.desired_running !== true) return false;
  if (status.active_lease && status.active_lease_is_fresh && status.owned_by_this_process) return false;
  if (status.local_running && !status.stop_requested_at) return false;
  return true;
}

function Metric({ label, value, mono, danger, warning }: { label: string; value: string; mono?: boolean; danger?: boolean; warning?: boolean }) {
  return (
    <div className="summary-row">
      <span className="field-label">{label}</span>
      <span className={`field-value ${mono ? "mono" : ""}`} style={{ color: danger ? "var(--danger)" : warning ? "var(--warning)" : undefined }}>
        {value}
      </span>
    </div>
  );
}
