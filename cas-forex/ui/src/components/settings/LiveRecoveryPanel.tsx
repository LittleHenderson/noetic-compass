/* Extracted from pages/SettingsPage.tsx (settings decomposition, slice 4). */

import { GlassPanel } from "../../components/GlassPanel";
import { StatusChip } from "../../components/StatusChip";
import { ControlField } from "../../components/settings/ControlField";
import { formatBrokerTruthReasonList, formatUnknownValue, recordOrNull } from "../../components/settings/formatters";
import { LIVE_MONEY_PROGRESS_REFRESH_EVENT, isLiveMoneyProgressionWarming } from "../../components/settings/liveMoneyProgression";
import { BrokerTruthMonitorStatus, BrokerTruthRecoveryPacket, LiveMoneyProgressionPacket, LiveRecoveryReport, OrderAttemptAuditAttempt, OrderAttemptAuditStatus, OrderAttemptRecoveryPacket, TerminalReceiptArchiveAction, TerminalReceiptRecoveryPacket, TerminalReceiptRecoveryRefreshAction, WasteAdaptationApplyPreview, WasteAdaptationOwnerReview, WasteAdaptationPaperApply, WasteAdaptationPlan, WasteAdaptationPromotionRule, WasteDirectionLearningLedger, WasteDirectionOutcomeBinding, WasteDirectionReviewPacket, WastePaperSampleCollector, WastePaperSampleCollectorScheduler, acceptLiveRecovery, fetchBrokerTruthMonitorStatus, fetchBrokerTruthRecoveryPacket, fetchLiveMoneyProgressionPacket, fetchLiveRecoveryStatus, fetchOrderAttemptAudit, fetchOrderAttemptRecoveryPacket, fetchTerminalReceiptRecoveryPacket, fetchWasteAdaptationApplyPreview, fetchWasteAdaptationOwnerReview, fetchWasteAdaptationPaperApply, fetchWasteAdaptationPlan, fetchWasteAdaptationPromotionRule, fetchWasteDirectionLearningLedger, fetchWasteDirectionOutcomeBinding, fetchWasteDirectionReviewPacket, fetchWastePaperSampleCollector, fetchWastePaperSampleCollectorScheduler, reconcileUnresolvedOrderAttempt, recordWasteAdaptationOwnerReview, recordWasteAdaptationPaperApply, resetLiveRecovery, resetWasteAdaptationOwnerReview, resetWasteAdaptationPaperApply, runBrokerTruthMonitorOnce, runTerminalReceiptArchiveAction, runTerminalReceiptRecoveryRefreshAction, runWastePaperSampleCollectorSchedulerOnce, startBrokerTruthMonitor, startWastePaperSampleCollectorScheduler, stopBrokerTruthMonitor, stopWastePaperSampleCollectorScheduler } from "../../data/api";
import { useEffect, useState } from "react";

const LIVE_MONEY_POST_WRITE_RETRY_DELAYS_MS = [1_500, 4_000, 8_000] as const;

export function LiveRecoveryPanel({
  initialReport,
  initialAudit,
  initialRecoveryPacket,
  initialTerminalReceiptPacket,
  initialBrokerTruth,
  initialLiveMoneyProgression,
  initialWasteDirectionReview,
  initialWasteDirectionLearning,
  initialWasteDirectionOutcomeBinding,
  initialWastePaperSampleCollector,
  initialWastePaperSampleCollectorScheduler,
  initialWasteAdaptationPromotionRule,
  initialWasteAdaptationPlan,
  initialWasteAdaptationApplyPreview,
  initialWasteAdaptationOwnerReview,
  initialWasteAdaptationPaperApply,
}: {
  initialReport?: LiveRecoveryReport;
  initialAudit?: OrderAttemptAuditStatus;
  initialRecoveryPacket?: OrderAttemptRecoveryPacket;
  initialTerminalReceiptPacket?: TerminalReceiptRecoveryPacket | null;
  initialBrokerTruth?: BrokerTruthMonitorStatus | null;
  initialLiveMoneyProgression?: LiveMoneyProgressionPacket | null;
  initialWasteDirectionReview?: WasteDirectionReviewPacket | null;
  initialWasteDirectionLearning?: WasteDirectionLearningLedger | null;
  initialWasteDirectionOutcomeBinding?: WasteDirectionOutcomeBinding | null;
  initialWastePaperSampleCollector?: WastePaperSampleCollector | null;
  initialWastePaperSampleCollectorScheduler?: WastePaperSampleCollectorScheduler | null;
  initialWasteAdaptationPromotionRule?: WasteAdaptationPromotionRule | null;
  initialWasteAdaptationPlan?: WasteAdaptationPlan | null;
  initialWasteAdaptationApplyPreview?: WasteAdaptationApplyPreview | null;
  initialWasteAdaptationOwnerReview?: WasteAdaptationOwnerReview | null;
  initialWasteAdaptationPaperApply?: WasteAdaptationPaperApply | null;
}) {
  const [report, setReport] = useState<LiveRecoveryReport | null>(initialReport ?? null);
  const [brokerTruthMonitor, setBrokerTruthMonitor] = useState<BrokerTruthMonitorStatus | null>(initialBrokerTruth ?? null);
  const [brokerTruthRecoveryPacket, setBrokerTruthRecoveryPacket] = useState<BrokerTruthRecoveryPacket | null>(null);
  const [liveMoneyProgression, setLiveMoneyProgression] = useState<LiveMoneyProgressionPacket | null>(initialLiveMoneyProgression ?? null);
  const [wasteDirectionReview, setWasteDirectionReview] = useState<WasteDirectionReviewPacket | null>(initialWasteDirectionReview ?? null);
  const [wasteDirectionLearning, setWasteDirectionLearning] = useState<WasteDirectionLearningLedger | null>(initialWasteDirectionLearning ?? null);
  const [wasteDirectionOutcomeBinding, setWasteDirectionOutcomeBinding] = useState<WasteDirectionOutcomeBinding | null>(initialWasteDirectionOutcomeBinding ?? null);
  const [wastePaperSampleCollector, setWastePaperSampleCollector] = useState<WastePaperSampleCollector | null>(initialWastePaperSampleCollector ?? null);
  const [wastePaperSampleCollectorScheduler, setWastePaperSampleCollectorScheduler] = useState<WastePaperSampleCollectorScheduler | null>(initialWastePaperSampleCollectorScheduler ?? null);
  const [wasteAdaptationPromotionRule, setWasteAdaptationPromotionRule] = useState<WasteAdaptationPromotionRule | null>(initialWasteAdaptationPromotionRule ?? null);
  const [wasteAdaptationPlan, setWasteAdaptationPlan] = useState<WasteAdaptationPlan | null>(initialWasteAdaptationPlan ?? null);
  const [wasteAdaptationApplyPreview, setWasteAdaptationApplyPreview] = useState<WasteAdaptationApplyPreview | null>(initialWasteAdaptationApplyPreview ?? null);
  const [wasteAdaptationOwnerReview, setWasteAdaptationOwnerReview] = useState<WasteAdaptationOwnerReview | null>(initialWasteAdaptationOwnerReview ?? null);
  const [wasteAdaptationPaperApply, setWasteAdaptationPaperApply] = useState<WasteAdaptationPaperApply | null>(initialWasteAdaptationPaperApply ?? null);
  const [attemptAudit, setAttemptAudit] = useState<OrderAttemptAuditStatus | null>(initialAudit ?? null);
  const [recoveryPacket, setRecoveryPacket] = useState<OrderAttemptRecoveryPacket | null>(initialRecoveryPacket ?? null);
  const [terminalReceiptPacket, setTerminalReceiptPacket] = useState<TerminalReceiptRecoveryPacket | null>(initialTerminalReceiptPacket ?? null);
  const [terminalArchiveAction, setTerminalArchiveAction] = useState<TerminalReceiptArchiveAction | null>(null);
  const [terminalRefreshAction, setTerminalRefreshAction] = useState<TerminalReceiptRecoveryRefreshAction | null>(null);
  const [selectedAttemptId, setSelectedAttemptId] = useState("");
  const [notes, setNotes] = useState("");
  const [ownerConfirm, setOwnerConfirm] = useState(false);
  const [ownerConfirmReconcile, setOwnerConfirmReconcile] = useState(false);
  const [ownerConfirmArchive, setOwnerConfirmArchive] = useState(false);
  const [ownerConfirmRefresh, setOwnerConfirmRefresh] = useState(false);
  const [ownerConfirmAdaptationReview, setOwnerConfirmAdaptationReview] = useState(false);
  const [ownerConfirmAdaptationApply, setOwnerConfirmAdaptationApply] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");

  async function refreshLiveMoneyProgression(refreshPacket = false): Promise<LiveMoneyProgressionPacket | null> {
    const progression = await fetchLiveMoneyProgressionPacket(refreshPacket);
    if (progression) setLiveMoneyProgression(progression);
    return progression;
  }

  function scheduleLiveMoneyProgressionRetries() {
    LIVE_MONEY_POST_WRITE_RETRY_DELAYS_MS.forEach((delayMs) => {
      window.setTimeout(() => {
        void refreshLiveMoneyProgression(false);
      }, delayMs);
    });
  }

  async function refreshLiveMoneyProgressionAfterWrite() {
    const progression = await refreshLiveMoneyProgression(true);
    if (isLiveMoneyProgressionWarming(progression)) scheduleLiveMoneyProgressionRetries();
  }

  useEffect(() => {
    if (initialReport) setReport(initialReport);
  }, [initialReport]);

  useEffect(() => {
    if (initialBrokerTruth) setBrokerTruthMonitor(initialBrokerTruth);
  }, [initialBrokerTruth]);

  useEffect(() => {
    if (initialLiveMoneyProgression) setLiveMoneyProgression(initialLiveMoneyProgression);
  }, [initialLiveMoneyProgression]);

  useEffect(() => {
    if (initialWasteDirectionReview) setWasteDirectionReview(initialWasteDirectionReview);
  }, [initialWasteDirectionReview]);

  useEffect(() => {
    if (initialWasteDirectionLearning) setWasteDirectionLearning(initialWasteDirectionLearning);
  }, [initialWasteDirectionLearning]);

  useEffect(() => {
    if (initialWasteDirectionOutcomeBinding) setWasteDirectionOutcomeBinding(initialWasteDirectionOutcomeBinding);
  }, [initialWasteDirectionOutcomeBinding]);

  useEffect(() => {
    if (initialWastePaperSampleCollector) setWastePaperSampleCollector(initialWastePaperSampleCollector);
  }, [initialWastePaperSampleCollector]);

  useEffect(() => {
    if (initialWastePaperSampleCollectorScheduler) setWastePaperSampleCollectorScheduler(initialWastePaperSampleCollectorScheduler);
  }, [initialWastePaperSampleCollectorScheduler]);

  useEffect(() => {
    if (initialWasteAdaptationPromotionRule) setWasteAdaptationPromotionRule(initialWasteAdaptationPromotionRule);
  }, [initialWasteAdaptationPromotionRule]);

  useEffect(() => {
    if (initialWasteAdaptationPlan) setWasteAdaptationPlan(initialWasteAdaptationPlan);
  }, [initialWasteAdaptationPlan]);

  useEffect(() => {
    if (initialWasteAdaptationApplyPreview) setWasteAdaptationApplyPreview(initialWasteAdaptationApplyPreview);
  }, [initialWasteAdaptationApplyPreview]);

  useEffect(() => {
    if (initialWasteAdaptationOwnerReview) setWasteAdaptationOwnerReview(initialWasteAdaptationOwnerReview);
  }, [initialWasteAdaptationOwnerReview]);

  useEffect(() => {
    if (initialWasteAdaptationPaperApply) setWasteAdaptationPaperApply(initialWasteAdaptationPaperApply);
  }, [initialWasteAdaptationPaperApply]);

  useEffect(() => {
    if (initialAudit) setAttemptAudit(initialAudit);
  }, [initialAudit]);

  useEffect(() => {
    if (initialRecoveryPacket) setRecoveryPacket(initialRecoveryPacket);
  }, [initialRecoveryPacket]);

  useEffect(() => {
    if (initialTerminalReceiptPacket) setTerminalReceiptPacket(initialTerminalReceiptPacket);
  }, [initialTerminalReceiptPacket]);

  useEffect(() => {
    const refreshHandler = () => {
      void refreshLiveMoneyProgressionAfterWrite();
    };
    window.addEventListener(LIVE_MONEY_PROGRESS_REFRESH_EVENT, refreshHandler);
    return () => window.removeEventListener(LIVE_MONEY_PROGRESS_REFRESH_EVENT, refreshHandler);
  }, []);

  useEffect(() => {
    void Promise.all([
      fetchLiveRecoveryStatus(),
      fetchBrokerTruthMonitorStatus(),
      fetchBrokerTruthRecoveryPacket(),
      fetchOrderAttemptAudit(),
      fetchOrderAttemptRecoveryPacket(),
      fetchTerminalReceiptRecoveryPacket(),
      fetchLiveMoneyProgressionPacket(),
      fetchWasteDirectionReviewPacket(),
      fetchWasteDirectionLearningLedger(),
      fetchWasteDirectionOutcomeBinding(),
      fetchWastePaperSampleCollector(),
      fetchWastePaperSampleCollectorScheduler(),
      fetchWasteAdaptationPromotionRule(),
      fetchWasteAdaptationPlan(),
      fetchWasteAdaptationApplyPreview(),
      fetchWasteAdaptationOwnerReview(),
      fetchWasteAdaptationPaperApply(),
    ]).then(([payload, brokerTruth, brokerTruthPacket, audit, packet, terminalPacket, progression, directionReview, directionLearning, directionOutcomeBinding, paperSampleCollector, paperSampleScheduler, adaptationPromotionRule, adaptationPlan, adaptationApplyPreview, adaptationOwnerReview, adaptationPaperApply]) => {
      if (payload) setReport(payload);
      if (brokerTruth) setBrokerTruthMonitor(brokerTruth);
      if (brokerTruthPacket) setBrokerTruthRecoveryPacket(brokerTruthPacket);
      if (audit) setAttemptAudit(audit);
      if (packet) setRecoveryPacket(packet);
      if (terminalPacket) setTerminalReceiptPacket(terminalPacket);
      if (progression) setLiveMoneyProgression(progression);
      if (directionReview) setWasteDirectionReview(directionReview);
      if (directionLearning) setWasteDirectionLearning(directionLearning);
      if (directionOutcomeBinding) setWasteDirectionOutcomeBinding(directionOutcomeBinding);
      if (paperSampleCollector) setWastePaperSampleCollector(paperSampleCollector);
      if (paperSampleScheduler) setWastePaperSampleCollectorScheduler(paperSampleScheduler);
      if (adaptationPromotionRule) setWasteAdaptationPromotionRule(adaptationPromotionRule);
      if (adaptationPlan) setWasteAdaptationPlan(adaptationPlan);
      if (adaptationApplyPreview) setWasteAdaptationApplyPreview(adaptationApplyPreview);
      if (adaptationOwnerReview) setWasteAdaptationOwnerReview(adaptationOwnerReview);
      if (adaptationPaperApply) setWasteAdaptationPaperApply(adaptationPaperApply);
    });
  }, []);

  const unresolvedAttempts = recoveryPacket?.unresolved_real_attempts?.length
    ? recoveryPacket.unresolved_real_attempts
    : attemptAudit?.unresolved_real_attempts?.length
      ? attemptAudit.unresolved_real_attempts
      : unresolvedAttemptsFromRecovery(report);

  useEffect(() => {
    if (!unresolvedAttempts.length) {
      if (selectedAttemptId) setSelectedAttemptId("");
      return;
    }
    if (!selectedAttemptId || !unresolvedAttempts.some((attempt) => attempt.attempt_id === selectedAttemptId)) {
      setSelectedAttemptId(unresolvedAttempts[0]?.attempt_id ?? "");
    }
  }, [selectedAttemptId, unresolvedAttempts]);

  const selectedAttempt = unresolvedAttempts.find((attempt) => attempt.attempt_id === selectedAttemptId) ?? null;
  const selectedAttemptProvenance = recordOrNull(selectedAttempt?.execution_provenance);
  const selectedAttemptInitiator = recordOrNull(selectedAttemptProvenance?.initiator);
  const selectedAttemptRuntimeLane = recordOrNull(selectedAttemptProvenance?.runtime_lane);
  const selectedAttemptDispatchPath = recordOrNull(selectedAttemptProvenance?.dispatch_path);
  const selectedAttemptAudit = recordOrNull(selectedAttemptProvenance?.attempt_audit);

  async function refresh() {
    if (busy) return;
    setBusy(true);
    setStatus("");
    try {
      const [next, brokerTruthPacket, audit, packet, terminalPacket, progression, directionReview, directionLearning, directionOutcomeBinding, paperSampleCollector, paperSampleScheduler, adaptationPromotionRule, adaptationPlan, adaptationApplyPreview, adaptationOwnerReview, adaptationPaperApply] = await Promise.all([
        fetchLiveRecoveryStatus(),
        fetchBrokerTruthRecoveryPacket(),
        fetchOrderAttemptAudit(),
        fetchOrderAttemptRecoveryPacket(),
        fetchTerminalReceiptRecoveryPacket(),
        fetchLiveMoneyProgressionPacket(),
        fetchWasteDirectionReviewPacket(),
        fetchWasteDirectionLearningLedger(),
        fetchWasteDirectionOutcomeBinding(),
        fetchWastePaperSampleCollector(),
        fetchWastePaperSampleCollectorScheduler(),
        fetchWasteAdaptationPromotionRule(),
        fetchWasteAdaptationPlan(),
        fetchWasteAdaptationApplyPreview(),
        fetchWasteAdaptationOwnerReview(),
        fetchWasteAdaptationPaperApply(),
      ]);
      if (next) setReport(next);
      if (brokerTruthPacket) setBrokerTruthRecoveryPacket(brokerTruthPacket);
      if (audit) setAttemptAudit(audit);
      if (packet) setRecoveryPacket(packet);
      if (terminalPacket) setTerminalReceiptPacket(terminalPacket);
      if (progression) setLiveMoneyProgression(progression);
      if (directionReview) setWasteDirectionReview(directionReview);
      if (directionLearning) setWasteDirectionLearning(directionLearning);
      if (directionOutcomeBinding) setWasteDirectionOutcomeBinding(directionOutcomeBinding);
      if (paperSampleCollector) setWastePaperSampleCollector(paperSampleCollector);
      if (paperSampleScheduler) setWastePaperSampleCollectorScheduler(paperSampleScheduler);
      if (adaptationPromotionRule) setWasteAdaptationPromotionRule(adaptationPromotionRule);
      if (adaptationPlan) setWasteAdaptationPlan(adaptationPlan);
      if (adaptationApplyPreview) setWasteAdaptationApplyPreview(adaptationApplyPreview);
      if (adaptationOwnerReview) setWasteAdaptationOwnerReview(adaptationOwnerReview);
      if (adaptationPaperApply) setWasteAdaptationPaperApply(adaptationPaperApply);
      setStatus("Live recovery refreshed.");
    } finally {
      setBusy(false);
    }
  }

  async function accept() {
    if (busy) return;
    if (!ownerConfirm) {
      setStatus("Cannot record Owner ACCEPT until Owner Confirm is checked.");
      return;
    }
    if (!ready) {
      setStatus(`Cannot record Owner ACCEPT: ${(report?.missing_requirements ?? ["live recovery evidence is not ready"]).join("; ")}`);
      return;
    }
    setBusy(true);
    setStatus("");
    try {
      const next = await acceptLiveRecovery(notes, ownerConfirm);
      setReport(next);
      await refreshLiveMoneyProgressionAfterWrite();
      setOwnerConfirm(false);
      setStatus("Live recovery review recorded as ACCEPT.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Couldn't ACCEPT live recovery review.");
    } finally {
      setBusy(false);
    }
  }

  async function reset() {
    if (busy) return;
    setBusy(true);
    setStatus("");
    try {
      const next = await resetLiveRecovery("OWNER_RESET_FROM_SETTINGS");
      setReport(next);
      await refreshLiveMoneyProgressionAfterWrite();
      setOwnerConfirm(false);
      setOwnerConfirmReconcile(false);
      setOwnerConfirmArchive(false);
      setOwnerConfirmRefresh(false);
      setOwnerConfirmAdaptationReview(false);
      setOwnerConfirmAdaptationApply(false);
      setStatus("Live recovery review reset to OPEN.");
    } catch {
      setStatus("Couldn't reset live recovery review.");
    } finally {
      setBusy(false);
    }
  }

  async function reconcileAttempt() {
    if (busy) return;
    if (!selectedAttemptId) {
      setStatus("Cannot reconcile: no unresolved attempt is selected.");
      return;
    }
    if (!ownerConfirmReconcile) {
      setStatus("Cannot reconcile until Owner Reconcile is checked.");
      return;
    }
    setBusy(true);
    setStatus("");
    try {
      const audit = await reconcileUnresolvedOrderAttempt(selectedAttemptId, notes, ownerConfirmReconcile);
      setAttemptAudit(audit);
      const [next, packet, progression] = await Promise.all([
        fetchLiveRecoveryStatus(),
        fetchOrderAttemptRecoveryPacket(),
        fetchLiveMoneyProgressionPacket(),
      ]);
      if (next) setReport(next);
      if (packet) setRecoveryPacket(packet);
      if (progression) setLiveMoneyProgression(progression);
      setOwnerConfirmReconcile(false);
      setStatus("Unresolved real attempt recorded as RECOVERY_RECONCILED.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Couldn't reconcile unresolved real attempt.");
    } finally {
      setBusy(false);
    }
  }

  async function archiveTerminalReceipts(execute: boolean) {
    if (busy) return;
    if (execute && !ownerConfirmArchive) {
      setStatus("Cannot archive stale rows until Owner Archive is checked.");
      return;
    }
    if (execute && !canExecuteTerminalArchive) {
      setStatus("Cannot archive stale rows: no archive-ready terminal receipt rows are present.");
      return;
    }
    setBusy(true);
    setStatus("");
    try {
      const action = await runTerminalReceiptArchiveAction({
        execute,
        confirm_owner_archive: execute ? ownerConfirmArchive : false,
        age_threshold_hours: 24,
        notes,
      });
      setTerminalArchiveAction(action);
      const [next, terminalPacket, progression] = await Promise.all([
        fetchLiveRecoveryStatus(),
        fetchTerminalReceiptRecoveryPacket(),
        fetchLiveMoneyProgressionPacket(),
      ]);
      if (next) setReport(next);
      if (terminalPacket) setTerminalReceiptPacket(terminalPacket);
      if (progression) setLiveMoneyProgression(progression);
      if (execute) setOwnerConfirmArchive(false);
      setStatus(`Terminal receipt archive action: ${action.status}.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Couldn't run terminal receipt archive action.");
    } finally {
      setBusy(false);
    }
  }

  async function refreshTerminalRecoveryChain(execute: boolean) {
    if (busy) return;
    if (execute && !ownerConfirmRefresh) {
      setStatus("Cannot run refresh chain until Owner Refresh is checked.");
      return;
    }
    setBusy(true);
    setStatus("");
    try {
      const action = await runTerminalReceiptRecoveryRefreshAction({
        execute,
        confirm_owner_refresh: execute ? ownerConfirmRefresh : false,
        notes,
      });
      setTerminalRefreshAction(action);
      const [next, packet, terminalPacket, progression] = await Promise.all([
        fetchLiveRecoveryStatus(),
        fetchOrderAttemptRecoveryPacket(),
        fetchTerminalReceiptRecoveryPacket(),
        fetchLiveMoneyProgressionPacket(),
      ]);
      if (next) setReport(next);
      if (packet) setRecoveryPacket(packet);
      if (terminalPacket) setTerminalReceiptPacket(terminalPacket);
      if (progression) setLiveMoneyProgression(progression);
      if (execute) setOwnerConfirmRefresh(false);
      setStatus(`Terminal recovery refresh: ${action.status}.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Couldn't run terminal recovery refresh.");
    } finally {
      setBusy(false);
    }
  }

  async function recordAdaptationOwnerReview(decision: string) {
    if (busy) return;
    if (!ownerConfirmAdaptationReview) {
      setStatus("Cannot record adaptation review until Owner Adapt is checked.");
      return;
    }
    if (decision === "ACCEPT_PAPER_ONLY" && !adaptationOwnerEvidenceReady) {
      setStatus(`Cannot accept paper adaptation: ${(wasteAdaptationOwnerReview?.missing_requirements ?? ["adaptation evidence is not ready"]).join("; ")}`);
      return;
    }
    setBusy(true);
    setStatus("");
    try {
      const ownerReview = await recordWasteAdaptationOwnerReview(
        { decision, notes },
        ownerConfirmAdaptationReview,
        decision === "ACCEPT_PAPER_ONLY",
      );
      setWasteAdaptationOwnerReview(ownerReview);
      const [progression, preview] = await Promise.all([
        fetchLiveMoneyProgressionPacket(),
        fetchWasteAdaptationApplyPreview(),
      ]);
      if (progression) setLiveMoneyProgression(progression);
      if (preview) setWasteAdaptationApplyPreview(preview);
      setOwnerConfirmAdaptationReview(false);
      setStatus(`WASTE adaptation owner review recorded: ${ownerReview.owner_review_decision || ownerReview.owner_review_status}.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Couldn't record WASTE adaptation owner review.");
    } finally {
      setBusy(false);
    }
  }

  async function resetAdaptationOwnerReview() {
    if (busy) return;
    setBusy(true);
    setStatus("");
    try {
      const ownerReview = await resetWasteAdaptationOwnerReview("OWNER_RESET_FROM_SETTINGS");
      setWasteAdaptationOwnerReview(ownerReview);
      const progression = await fetchLiveMoneyProgressionPacket();
      if (progression) setLiveMoneyProgression(progression);
      setOwnerConfirmAdaptationReview(false);
      setStatus("WASTE adaptation owner review reset to OPEN.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Couldn't reset WASTE adaptation owner review.");
    } finally {
      setBusy(false);
    }
  }

  async function recordAdaptationPaperApply() {
    if (busy) return;
    if (!ownerConfirmAdaptationApply) {
      setStatus("Cannot record paper apply until Owner Paper Apply is checked.");
      return;
    }
    if (!adaptationPaperApplyReady) {
      setStatus(`Cannot record paper apply: ${(wasteAdaptationPaperApply?.missing_requirements ?? ["paper adaptation apply is not ready"]).join("; ")}`);
      return;
    }
    setBusy(true);
    setStatus("");
    try {
      const paperApply = await recordWasteAdaptationPaperApply(
        { notes },
        ownerConfirmAdaptationApply,
      );
      setWasteAdaptationPaperApply(paperApply);
      const [progression, ownerReview] = await Promise.all([
        fetchLiveMoneyProgressionPacket(),
        fetchWasteAdaptationOwnerReview(),
      ]);
      if (progression) setLiveMoneyProgression(progression);
      if (ownerReview) setWasteAdaptationOwnerReview(ownerReview);
      setOwnerConfirmAdaptationApply(false);
      setStatus(`WASTE adaptation paper apply: ${paperApply.status}.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Couldn't record WASTE adaptation paper apply.");
    } finally {
      setBusy(false);
    }
  }

  async function resetAdaptationPaperApply() {
    if (busy) return;
    setBusy(true);
    setStatus("");
    try {
      const paperApply = await resetWasteAdaptationPaperApply("OWNER_RESET_FROM_SETTINGS");
      setWasteAdaptationPaperApply(paperApply);
      const progression = await fetchLiveMoneyProgressionPacket();
      if (progression) setLiveMoneyProgression(progression);
      setOwnerConfirmAdaptationApply(false);
      setStatus("WASTE adaptation paper apply reset.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Couldn't reset WASTE adaptation paper apply.");
    } finally {
      setBusy(false);
    }
  }

  async function runBrokerTruthNow() {
    if (busy) return;
    setBusy(true);
    setStatus("");
    try {
      const brokerTruth = await runBrokerTruthMonitorOnce();
      setBrokerTruthMonitor(brokerTruth);
      const [next, brokerTruthPacket, packet, progression] = await Promise.all([
        fetchLiveRecoveryStatus(),
        fetchBrokerTruthRecoveryPacket(),
        fetchOrderAttemptRecoveryPacket(),
        fetchLiveMoneyProgressionPacket(),
      ]);
      if (next) setReport(next);
      if (brokerTruthPacket) setBrokerTruthRecoveryPacket(brokerTruthPacket);
      if (packet) setRecoveryPacket(packet);
      if (progression) setLiveMoneyProgression(progression);
      setStatus(`Broker truth check recorded: ${brokerTruth.monitor_status}.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Couldn't run broker truth check.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleBrokerTruthMonitor() {
    if (busy) return;
    setBusy(true);
    setStatus("");
    try {
      const next = brokerTruthMonitor?.running
        ? await stopBrokerTruthMonitor()
        : await startBrokerTruthMonitor(brokerTruthMonitor?.interval_seconds ?? 120);
      setBrokerTruthMonitor(next);
      const [brokerTruthPacket, progression] = await Promise.all([
        fetchBrokerTruthRecoveryPacket(),
        fetchLiveMoneyProgressionPacket(),
      ]);
      if (brokerTruthPacket) setBrokerTruthRecoveryPacket(brokerTruthPacket);
      if (progression) setLiveMoneyProgression(progression);
      setStatus(next.running ? "Broker truth monitor started." : "Broker truth monitor stopped.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Couldn't change broker truth monitor.");
    } finally {
      setBusy(false);
    }
  }

  async function runPaperSampleCollectorNow() {
    if (busy) return;
    setBusy(true);
    setStatus("");
    try {
      const scheduler = await runWastePaperSampleCollectorSchedulerOnce({
        run_market_diagnostic: true,
        run_real_candle_probe: true,
        run_deal_history_ingest: true,
        timeframe: wastePaperSampleCollectorScheduler?.config?.timeframe ?? "D1",
        bars: wastePaperSampleCollectorScheduler?.config?.bars ?? 180,
        max_pairs: wastePaperSampleCollectorScheduler?.config?.max_pairs ?? 80,
        scan_candidates: true,
        max_scan_candidates: 8,
      });
      setWastePaperSampleCollectorScheduler(scheduler);
      const [collector, progression] = await Promise.all([
        fetchWastePaperSampleCollector(),
        fetchLiveMoneyProgressionPacket(),
      ]);
      if (collector) setWastePaperSampleCollector(collector);
      if (progression) setLiveMoneyProgression(progression);
      setStatus(`Paper sample collector run: ${scheduler.latest_collector_status ?? scheduler.status}.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Couldn't run paper sample collector.");
    } finally {
      setBusy(false);
    }
  }

  async function togglePaperSampleCollectorScheduler() {
    if (busy) return;
    setBusy(true);
    setStatus("");
    try {
      const next = wastePaperSampleCollectorScheduler?.running
        ? await stopWastePaperSampleCollectorScheduler()
        : await startWastePaperSampleCollectorScheduler({
            interval_seconds: wastePaperSampleCollectorScheduler?.interval_seconds ?? 300,
            run_market_diagnostic: true,
            run_real_candle_probe: true,
            run_deal_history_ingest: true,
            timeframe: wastePaperSampleCollectorScheduler?.config?.timeframe ?? "D1",
            bars: wastePaperSampleCollectorScheduler?.config?.bars ?? 180,
            max_pairs: wastePaperSampleCollectorScheduler?.config?.max_pairs ?? 80,
            scan_candidates: true,
            max_scan_candidates: 8,
          });
      setWastePaperSampleCollectorScheduler(next);
      const collector = await fetchWastePaperSampleCollector();
      if (collector) setWastePaperSampleCollector(collector);
      setStatus(next.running ? "Paper sample collector scheduler started." : "Paper sample collector scheduler stopped.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Couldn't change paper sample collector scheduler.");
    } finally {
      setBusy(false);
    }
  }

  const clear = report?.recovery_clear_for_live ?? false;
  const ready = report?.evidence_ready_for_owner_accept ?? false;
  const requires = report?.requires_recovery_review ?? false;
  const liveRecoveryAttemptSummary = (report?.order_attempt_summary ?? {}) as Record<string, unknown>;
  const unresolvedCount = Number(
    liveRecoveryAttemptSummary.unresolved_real_attempt_count
      ?? recoveryPacket?.unresolved_real_attempt_count
      ?? attemptAudit?.unresolved_real_attempt_count
      ?? 0,
  );
  const canReconcileNow = Boolean(recoveryPacket?.can_reconcile_unresolved_attempts);
  const syntheticLikeCount = Number(
    liveRecoveryAttemptSummary.synthetic_test_like_unresolved_attempt_count
      ?? recoveryPacket?.synthetic_test_like_count
      ?? 0,
  );
  const brokerReviewCount = Number(
    liveRecoveryAttemptSummary.broker_review_required_unresolved_attempt_count
      ?? recoveryPacket?.broker_review_required_count
      ?? 0,
  );
  const unknownUnresolvedCount = Number(liveRecoveryAttemptSummary.unknown_unresolved_attempt_count ?? 0);
  const brokerBlockingAttemptCount = brokerReviewCount;
  const idempotencyPolicy = attemptAudit?.idempotency_policy;
  const duplicateSuppressedCount = Number(attemptAudit?.duplicate_suppressed_count ?? 0);
  const nearDuplicateSuppressedCount = Number(attemptAudit?.near_duplicate_suppressed_count ?? 0);
  const idempotencyWindowSeconds = Number(idempotencyPolicy?.near_duplicate_window_seconds ?? 600);
  const latestAttemptShapeKey = attemptAudit?.latest_attempt?.order_shape_key ?? "none";
  const terminalPendingReceiptCount = Number(terminalReceiptPacket?.pending_receipt_count ?? 0);
  const terminalArchivePreviewCount = Number(terminalReceiptPacket?.legacy_archive_preview?.pending_receipt_rows_archived ?? 0);
  const canExecuteTerminalArchive = terminalArchivePreviewCount > 0;
  const brokerTruthReport = brokerTruthMonitor?.latest_report ?? null;
  const brokerTruthReady = brokerTruthMonitor?.ready_for_live ?? false;
  const brokerTruthRunning = brokerTruthMonitor?.running ?? false;
  const brokerTruthStatus = brokerTruthMonitor?.monitor_status ?? brokerTruthReport?.monitor_status ?? "BROKER_TRUTH_UNKNOWN";
  const brokerTruthProtectionStatus = String(brokerTruthReport?.position_protection_status ?? "unavailable");
  const brokerTruthUnprotectedCount = Number(brokerTruthReport?.position_protection_unprotected_position_count ?? 0);
  const brokerTruthProtectionDetail = typeof brokerTruthReport?.position_protection_detail === "string"
    ? brokerTruthReport.position_protection_detail
    : "";
  const brokerTruthAutoHaltLatched = Boolean(brokerTruthReport?.auto_halt_latched_from_monitor);
  const brokerTruthReasonList = formatBrokerTruthReasonList(brokerTruthReport?.monitor_auto_halt_reason_ids);
  const brokerTruthBlockerCount = brokerTruthRecoveryPacket?.blockers?.length ?? 0;
  const liveMoneyBlockerCount = liveMoneyProgression?.blocker_count ?? liveMoneyProgression?.blockers?.length ?? 0;
  const liveMoneyIntent = liveMoneyProgression?.active_waste_intent ?? {};
  const liveMoneyIntentLabel = liveMoneyIntent.symbol || liveMoneyIntent.direction
    ? `${liveMoneyIntent.symbol ?? "NA"} ${liveMoneyIntent.direction ?? "NA"}`
    : "NO ACTIVE INTENT";
  const liveMoneyCacheLabel = formatCacheAge(liveMoneyProgression);
  const liveMoneyCacheStale = Boolean(liveMoneyProgression?.cache_stale);
  const wasteDirection = wasteDirectionReview?.direction_summary ?? {};
  const wasteEdge = wasteDirectionReview?.edge_gate_summary ?? {};
  const wasteProfitBox = wasteDirectionReview?.profit_box ?? {};
  const wasteDirectionLabel = wasteDirection.symbol || wasteDirection.direction
    ? `${wasteDirection.symbol ?? "NA"} ${wasteDirection.direction ?? "NA"}`
    : "NO DIRECTION";
  const wasteDirectionBlockerCount = wasteDirectionReview?.blocker_count ?? wasteDirectionReview?.blockers?.length ?? 0;
  const learningRecommendation = wasteDirectionLearning?.profile_recommendation ?? {};
  const learningGroup = (
    (learningRecommendation.recommended_group ?? learningRecommendation.dominant_observed_group ?? {}) as Record<string, unknown>
  );
  const learningGroupLabel = learningGroup.symbol || learningGroup.direction
    ? `${String(learningGroup.symbol ?? "NA")} ${String(learningGroup.timeframe ?? "NA")} ${String(learningGroup.profile ?? "NA")} ${String(learningGroup.direction ?? "NA")}`
    : "NO LEARNING GROUP";
  const outcomeReady = wasteDirectionOutcomeBinding?.outcome_ready_for_promotion ?? false;
  const outcomeBoundCount = wasteDirectionOutcomeBinding?.bound_outcome_count ?? 0;
  const outcomeBoundNeeded = wasteDirectionOutcomeBinding?.bound_outcomes_needed ?? 0;
  const paperSampleComplete = wastePaperSampleCollector?.sample_collection_complete ?? false;
  const paperSampleActionCount = wastePaperSampleCollector?.required_actions?.length ?? 0;
  const paperSampleMarketReady = wastePaperSampleCollector?.market_data_ready ?? false;
  const paperSampleLabel = wastePaperSampleCollector?.probe_symbol || wastePaperSampleCollector?.probe_direction
    ? `${wastePaperSampleCollector?.probe_symbol ?? "NA"} ${wastePaperSampleCollector?.probe_timeframe ?? "NA"} ${wastePaperSampleCollector?.probe_direction ?? "NA"}`
    : "NO PAPER SAMPLE";
  const paperSampleSchedulerRunning = wastePaperSampleCollectorScheduler?.running ?? false;
  const paperSampleSchedulerStatus = wastePaperSampleCollectorScheduler?.latest_collector_status ?? wastePaperSampleCollectorScheduler?.status ?? "unavailable";
  const paperSampleSchedulerCycles = wastePaperSampleCollectorScheduler?.cycles_run ?? 0;
  const promotionGroup = (
    (wasteAdaptationPromotionRule?.recommended_group ?? wasteAdaptationPromotionRule?.dominant_group ?? {}) as Record<string, unknown>
  );
  const promotionGroupLabel = promotionGroup.symbol || promotionGroup.direction
    ? `${String(promotionGroup.symbol ?? "NA")} ${String(promotionGroup.timeframe ?? "NA")} ${String(promotionGroup.profile ?? "NA")} ${String(promotionGroup.direction ?? "NA")}`
    : "NO PROMOTION GROUP";
  const promotionSamplesNeeded = wasteAdaptationPromotionRule?.confirmed_samples_needed ?? 0;
  const promotionReady = wasteAdaptationPromotionRule?.promotion_ready_for_owner_review ?? false;
  const adaptationProposalCount = wasteAdaptationPlan?.proposal_count ?? wasteAdaptationPlan?.proposals?.length ?? 0;
  const adaptationApplyPreviewBlockerCount = wasteAdaptationApplyPreview?.blocker_count ?? wasteAdaptationApplyPreview?.blockers?.length ?? 0;
  const adaptationSimulatedChangeCount = wasteAdaptationApplyPreview?.simulated_change_count ?? wasteAdaptationApplyPreview?.simulated_changes?.length ?? 0;
  const adaptationControls = wasteAdaptationApplyPreview?.current_controls ?? {};
  const adaptationOwnerReviewMissingCount = wasteAdaptationOwnerReview?.missing_requirements?.length ?? 0;
  const adaptationOwnerReviewCurrent = wasteAdaptationOwnerReview?.paper_only_review_current ?? false;
  const adaptationOwnerAcceptCurrent = wasteAdaptationOwnerReview?.paper_only_accept_current ?? false;
  const adaptationOwnerEvidenceReady = wasteAdaptationOwnerReview?.evidence_ready_for_owner_accept ?? false;
  const adaptationPaperApplyMissingCount = wasteAdaptationPaperApply?.missing_requirements?.length ?? 0;
  const adaptationPaperApplyReady = wasteAdaptationPaperApply?.paper_apply_ready ?? false;
  const adaptationPaperApplyCurrent = wasteAdaptationPaperApply?.paper_apply_current ?? false;
  const adaptationPaperApplyRecorded = wasteAdaptationPaperApply?.paper_apply_recorded ?? false;

  return (
    <GlassPanel
      title="Live Recovery"
      subtitle="Crash, disconnect, and restart review before more live orders"
      variant={clear ? "default" : "danger"}
    >
      <div className="sweep-status-row" style={{ marginBottom: 10 }}>
        <StatusChip label={report?.recovery_status ?? "OPEN"} variant={clear ? "success" : "danger"} size="sm" />
        <StatusChip label={requires ? "REVIEW REQUIRED" : "NO LIVE RECOVERY NEEDED"} variant={requires ? "warning" : "success"} size="sm" />
        <StatusChip label={ready ? "EVIDENCE READY" : "EVIDENCE NOT READY"} variant={ready ? "success" : "warning"} size="sm" />
        <StatusChip label={canReconcileNow ? "RECONCILE READY" : "RECONCILE BLOCKED"} variant={canReconcileNow ? "success" : "warning"} size="sm" />
        <StatusChip
          label={terminalReceiptPacket?.terminal_reconciliation_clean_for_live ? "RECEIPTS CLEAN" : "RECEIPTS BLOCKED"}
          variant={terminalReceiptPacket?.terminal_reconciliation_clean_for_live ? "success" : "warning"}
          size="sm"
        />
        <StatusChip
          label={canExecuteTerminalArchive ? "ARCHIVE READY" : "ARCHIVE IDLE"}
          variant={canExecuteTerminalArchive ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip
          label={`DUPLICATES ${duplicateSuppressedCount}`}
          variant={duplicateSuppressedCount > 0 ? "warning" : "success"}
          size="sm"
        />
        <StatusChip
          label={brokerTruthReady ? "BROKER TRUTH READY" : "BROKER TRUTH BLOCKED"}
          variant={brokerTruthReady ? "success" : "warning"}
          size="sm"
        />
        <StatusChip
          label={`TRUTH BLOCKERS ${brokerTruthBlockerCount}`}
          variant={brokerTruthBlockerCount === 0 ? "success" : "warning"}
          size="sm"
        />
        <StatusChip
          label={liveMoneyProgression?.full_progression_clear ? "LIVE MONEY CLEAR" : `LIVE MONEY BLOCKED ${liveMoneyBlockerCount}`}
          variant={liveMoneyProgression?.full_progression_clear ? "success" : "danger"}
          size="sm"
        />
        <StatusChip
          label={wasteDirectionReview?.direction_edge_confirmed ? "DIRECTION EDGE PASS" : `DIRECTION BLOCKED ${wasteDirectionBlockerCount}`}
          variant={wasteDirectionReview?.direction_edge_confirmed ? "success" : "warning"}
          size="sm"
        />
        <StatusChip
          label={wasteDirectionLearning?.learning_ready_for_adaptation ? "LEARNING READY" : "LEARNING COLLECTING"}
          variant={wasteDirectionLearning?.learning_ready_for_adaptation ? "success" : "muted"}
          size="sm"
        />
        <StatusChip
          label={outcomeReady ? "OUTCOMES BOUND" : `OUTCOMES NEED ${outcomeBoundNeeded}`}
          variant={outcomeReady ? "success" : "muted"}
          size="sm"
        />
        <StatusChip
          label={paperSampleComplete ? "PAPER SAMPLES READY" : `PAPER SAMPLE ACTIONS ${paperSampleActionCount}`}
          variant={paperSampleComplete ? "success" : paperSampleMarketReady ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip
          label={paperSampleSchedulerRunning ? "SAMPLE SCHEDULER ON" : "SAMPLE SCHEDULER OFF"}
          variant={paperSampleSchedulerRunning ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip
          label={promotionReady ? "PROMOTION READY" : `PROMOTION NEEDS ${promotionSamplesNeeded}`}
          variant={promotionReady ? "success" : "muted"}
          size="sm"
        />
        <StatusChip
          label={wasteAdaptationPlan?.adaptation_ready_for_owner_review ? "ADAPT PLAN READY" : "ADAPT PLAN DRY RUN"}
          variant={wasteAdaptationPlan?.adaptation_ready_for_owner_review ? "success" : "muted"}
          size="sm"
        />
        <StatusChip
          label={wasteAdaptationApplyPreview?.preview_ready_for_owner_review ? "ADAPT PREVIEW READY" : `ADAPT PREVIEW BLOCKED ${adaptationApplyPreviewBlockerCount}`}
          variant={wasteAdaptationApplyPreview?.preview_ready_for_owner_review ? "success" : "muted"}
          size="sm"
        />
        <StatusChip
          label={adaptationOwnerAcceptCurrent ? "ADAPT OWNER ACCEPT" : adaptationOwnerReviewCurrent ? "ADAPT OWNER REVIEWED" : "ADAPT OWNER OPEN"}
          variant={adaptationOwnerAcceptCurrent ? "success" : adaptationOwnerReviewCurrent ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip
          label={adaptationPaperApplyCurrent ? "PAPER ADAPT CURRENT" : adaptationPaperApplyReady ? "PAPER ADAPT READY" : "PAPER ADAPT BLOCKED"}
          variant={adaptationPaperApplyCurrent ? "success" : adaptationPaperApplyReady ? "warning" : "muted"}
          size="sm"
        />
      </div>

      <div className="control-grid">
        <ControlField
          label="Live Money Packet"
          value={liveMoneyProgression?.status ?? "unavailable"}
          danger={!liveMoneyProgression?.full_progression_clear}
        />
        <ControlField
          label="Packet Cache"
          value={liveMoneyCacheLabel}
          danger={liveMoneyCacheStale}
          mono
        />
        <ControlField label="Live Dispatch" value={String(liveMoneyProgression?.live_dispatch_clear ?? false)} danger={!liveMoneyProgression?.live_dispatch_clear} mono />
        <ControlField label="WASTE Pilot" value={String(liveMoneyProgression?.waste_pilot_clear ?? false)} danger={!liveMoneyProgression?.waste_pilot_clear} mono />
        <ControlField label="Verified Payout" value={String(liveMoneyProgression?.verified_payout_clear ?? false)} danger={!liveMoneyProgression?.verified_payout_clear} mono />
        <ControlField label="Progress Blockers" value={String(liveMoneyBlockerCount)} danger={liveMoneyBlockerCount > 0} mono />
        <ControlField label="WASTE Intent" value={liveMoneyIntentLabel} mono />
        <ControlField label="Direction Review" value={wasteDirectionReview?.status ?? "unavailable"} danger={!wasteDirectionReview?.direction_edge_confirmed} />
        <ControlField label="Chosen Side" value={wasteDirectionLabel} mono />
        <ControlField label="Opposite Score" value={String(wasteDirection.opposite_score ?? "NA")} mono />
        <ControlField label="Score Margin" value={String(wasteDirection.score_margin ?? "NA")} mono />
        <ControlField label="Edge Status" value={String(wasteEdge.status ?? "NA")} danger={wasteEdge.status !== "PASS"} mono />
        <ControlField label="Reward R" value={String(wasteProfitBox.reward_r ?? "NA")} danger={!wasteProfitBox.valid} mono />
        <ControlField label="Direction Samples" value={String(wasteDirectionLearning?.direction_rows ?? 0)} mono />
        <ControlField label="Confirmed Directions" value={String(wasteDirectionLearning?.confirmed_direction_count ?? 0)} danger={(wasteDirectionLearning?.confirmed_direction_count ?? 0) <= 0} mono />
        <ControlField label="Blocked Directions" value={String(wasteDirectionLearning?.blocked_direction_count ?? 0)} danger={(wasteDirectionLearning?.blocked_direction_count ?? 0) > 0} mono />
        <ControlField label="Learned Group" value={learningGroupLabel} mono />
        <ControlField label="Learning Ready" value={String(wasteDirectionLearning?.learning_ready_for_adaptation ?? false)} danger={!wasteDirectionLearning?.learning_ready_for_adaptation} mono />
        <ControlField label="Outcome Binding" value={wasteDirectionOutcomeBinding?.status ?? "unavailable"} danger={Boolean(wasteDirectionOutcomeBinding?.runtime_changed)} />
        <ControlField label="Outcomes Ready" value={String(outcomeReady)} danger={!outcomeReady} mono />
        <ControlField label="Bound Outcomes" value={String(outcomeBoundCount)} danger={outcomeBoundCount <= 0} mono />
        <ControlField label="Outcomes Needed" value={String(outcomeBoundNeeded)} danger={outcomeBoundNeeded > 0} mono />
        <ControlField label="Net Paper P/L" value={String(wasteDirectionOutcomeBinding?.net_paper_pnl ?? "NA")} danger={(wasteDirectionOutcomeBinding?.net_paper_pnl ?? 0) <= 0} mono />
        <ControlField label="Outcome Money Moved" value={String(wasteDirectionOutcomeBinding?.money_moved ?? false)} danger={Boolean(wasteDirectionOutcomeBinding?.money_moved)} mono />
        <ControlField label="Paper Sample Collector" value={wastePaperSampleCollector?.status ?? "unavailable"} danger={Boolean(wastePaperSampleCollector?.runtime_changed)} />
        <ControlField label="Sample Intent" value={paperSampleLabel} mono />
        <ControlField label="Market Ready" value={String(paperSampleMarketReady)} danger={!paperSampleMarketReady} mono />
        <ControlField label="Probe Edge" value={String(wastePaperSampleCollector?.probe_edge_status ?? "NA")} danger={wastePaperSampleCollector?.probe_edge_status !== "PASS"} mono />
        <ControlField label="Sample Actions" value={String(paperSampleActionCount)} danger={paperSampleActionCount > 0} mono />
        <ControlField label="Collector Money Moved" value={String(wastePaperSampleCollector?.money_moved ?? false)} danger={Boolean(wastePaperSampleCollector?.money_moved)} mono />
        <ControlField label="Sample Scheduler" value={paperSampleSchedulerStatus} danger={Boolean(wastePaperSampleCollectorScheduler?.last_error)} />
        <ControlField label="Scheduler Running" value={String(paperSampleSchedulerRunning)} mono />
        <ControlField label="Scheduler Cycles" value={String(paperSampleSchedulerCycles)} mono />
        <ControlField label="Scheduler Interval" value={`${String(wastePaperSampleCollectorScheduler?.interval_seconds ?? 300)}s`} mono />
        <ControlField label="Scheduler Last Run" value={String(wastePaperSampleCollectorScheduler?.last_run_iso ?? "never")} mono />
        <ControlField label="Scheduler Broker Touch" value={String(wastePaperSampleCollectorScheduler?.broker_execution_touched ?? false)} danger={Boolean(wastePaperSampleCollectorScheduler?.broker_execution_touched)} mono />
        <ControlField label="Scheduler Money Moved" value={String(wastePaperSampleCollectorScheduler?.money_moved ?? false)} danger={Boolean(wastePaperSampleCollectorScheduler?.money_moved)} mono />
        <ControlField label="Promotion Rule" value={wasteAdaptationPromotionRule?.status ?? "unavailable"} danger={Boolean(wasteAdaptationPromotionRule?.runtime_changed)} />
        <ControlField label="Promotion Ready" value={String(promotionReady)} danger={!promotionReady} mono />
        <ControlField label="Min Confirmed" value={String(wasteAdaptationPromotionRule?.min_confirmed_for_adaptation ?? "NA")} mono />
        <ControlField label="Confirmed Needed" value={String(promotionSamplesNeeded)} danger={promotionSamplesNeeded > 0} mono />
        <ControlField label="Promotion Group" value={promotionGroupLabel} mono />
        <ControlField label="Promotion Money Moved" value={String(wasteAdaptationPromotionRule?.money_moved ?? false)} danger={Boolean(wasteAdaptationPromotionRule?.money_moved)} mono />
        <ControlField label="Promotion Runtime Changed" value={String(wasteAdaptationPromotionRule?.runtime_changed ?? false)} danger={Boolean(wasteAdaptationPromotionRule?.runtime_changed)} mono />
        <ControlField label="Promotion Enables Live" value={String(wasteAdaptationPromotionRule?.would_enable_live_trading ?? false)} danger={Boolean(wasteAdaptationPromotionRule?.would_enable_live_trading)} mono />
        <ControlField label="Adaptation Plan" value={wasteAdaptationPlan?.status ?? "unavailable"} danger={!wasteAdaptationPlan?.dry_run} />
        <ControlField label="Adapt Proposals" value={String(adaptationProposalCount)} mono />
        <ControlField label="Adapt Ready" value={String(wasteAdaptationPlan?.adaptation_ready_for_owner_review ?? false)} danger={!wasteAdaptationPlan?.adaptation_ready_for_owner_review} mono />
        <ControlField label="Runtime Changed" value={String(wasteAdaptationPlan?.runtime_changed ?? false)} danger={Boolean(wasteAdaptationPlan?.runtime_changed)} mono />
        <ControlField label="Apply Preview" value={wasteAdaptationApplyPreview?.status ?? "unavailable"} danger={!wasteAdaptationApplyPreview?.dry_run} />
        <ControlField label="Preview Changes" value={String(adaptationSimulatedChangeCount)} mono />
        <ControlField label="Preview Blockers" value={String(adaptationApplyPreviewBlockerCount)} danger={adaptationApplyPreviewBlockerCount > 0} mono />
        <ControlField label="Apply Allowed" value={String(wasteAdaptationApplyPreview?.apply_allowed_now ?? false)} danger={Boolean(wasteAdaptationApplyPreview?.apply_allowed_now)} mono />
        <ControlField label="Would Lower Edge" value={String(wasteAdaptationApplyPreview?.would_lower_edge_threshold ?? false)} danger={Boolean(wasteAdaptationApplyPreview?.would_lower_edge_threshold)} mono />
        <ControlField label="Would Enable Live" value={String(wasteAdaptationApplyPreview?.would_enable_live_trading ?? false)} danger={Boolean(wasteAdaptationApplyPreview?.would_enable_live_trading)} mono />
        <ControlField label="Would Change Runtime" value={String(wasteAdaptationApplyPreview?.would_apply_runtime_change ?? false)} danger={Boolean(wasteAdaptationApplyPreview?.would_apply_runtime_change)} mono />
        <ControlField label="Current Edge Gate" value={String(adaptationControls["edge_threshold"] ?? "NA")} mono />
        <ControlField label="Owner Adapt Review" value={wasteAdaptationOwnerReview?.owner_review_status ?? "unavailable"} danger={Boolean(wasteAdaptationOwnerReview?.runtime_changed)} />
        <ControlField label="Adapt Decision" value={wasteAdaptationOwnerReview?.owner_review_decision || "OPEN"} mono />
        <ControlField label="Review Current" value={String(adaptationOwnerReviewCurrent)} danger={!adaptationOwnerReviewCurrent} mono />
        <ControlField label="Accept Current" value={String(adaptationOwnerAcceptCurrent)} danger={Boolean(adaptationOwnerAcceptCurrent && !adaptationOwnerEvidenceReady)} mono />
        <ControlField label="Accept Evidence Ready" value={String(adaptationOwnerEvidenceReady)} danger={!adaptationOwnerEvidenceReady} mono />
        <ControlField label="Review Missing" value={String(adaptationOwnerReviewMissingCount)} danger={adaptationOwnerReviewMissingCount > 0} mono />
        <ControlField label="Review Money Moved" value={String(wasteAdaptationOwnerReview?.money_moved ?? false)} danger={Boolean(wasteAdaptationOwnerReview?.money_moved)} mono />
        <ControlField label="Paper Apply" value={wasteAdaptationPaperApply?.status ?? "unavailable"} danger={Boolean(wasteAdaptationPaperApply?.runtime_changed)} />
        <ControlField label="Apply Ready" value={String(adaptationPaperApplyReady)} danger={!adaptationPaperApplyReady} mono />
        <ControlField label="Apply Current" value={String(adaptationPaperApplyCurrent)} danger={Boolean(adaptationPaperApplyCurrent && !adaptationPaperApplyRecorded)} mono />
        <ControlField label="Apply Recorded" value={String(adaptationPaperApplyRecorded)} mono />
        <ControlField label="Apply Missing" value={String(adaptationPaperApplyMissingCount)} danger={adaptationPaperApplyMissingCount > 0} mono />
        <ControlField label="Apply Runtime Changed" value={String(wasteAdaptationPaperApply?.runtime_changed ?? false)} danger={Boolean(wasteAdaptationPaperApply?.runtime_changed)} mono />
        <ControlField label="Apply Money Moved" value={String(wasteAdaptationPaperApply?.money_moved ?? false)} danger={Boolean(wasteAdaptationPaperApply?.money_moved)} mono />
        <ControlField label="Broker Truth" value={String(report?.broker_truth_summary?.overall_status ?? "unavailable")} danger={!clear} />
        <ControlField label="Truth Monitor" value={brokerTruthStatus} danger={!brokerTruthReady} />
        <ControlField label="Truth Running" value={String(brokerTruthRunning)} mono />
        <ControlField label="Truth Live Ready" value={String(brokerTruthReady)} danger={!brokerTruthReady} mono />
        <ControlField
          label="Truth Auto-Halt"
          value={String(brokerTruthAutoHaltLatched)}
          danger={brokerTruthAutoHaltLatched}
          description={brokerTruthAutoHaltLatched ? "The continuous broker-truth worker latched paper-force from a live mismatch." : undefined}
          mono
        />
        <ControlField
          label="Truth Halt Reasons"
          value={brokerTruthReasonList}
          danger={brokerTruthReasonList !== "NONE"}
          description={brokerTruthReasonList !== "NONE" ? "Mismatch checks that forced the monitor fail-closed path." : undefined}
          mono
        />
        <ControlField label="Truth Blockers" value={String(brokerTruthBlockerCount)} danger={brokerTruthBlockerCount > 0} mono />
        <ControlField label="MT5 Connected" value={String(report?.broker_truth_summary?.mt5_connected ?? false)} danger={!report?.broker_truth_summary?.mt5_connected} />
        <ControlField label="MT5 Open Positions" value={String(report?.broker_truth_summary?.mt5_open_position_count ?? 0)} mono />
        <ControlField
          label="Position Protection"
          value={brokerTruthProtectionStatus}
          danger={brokerTruthProtectionStatus === "UNPROTECTED_POSITIONS"}
          description={brokerTruthProtectionDetail || undefined}
        />
        <ControlField
          label="Unprotected Positions"
          value={String(brokerTruthUnprotectedCount)}
          danger={brokerTruthUnprotectedCount > 0}
          description={brokerTruthUnprotectedCount > 0 ? "Broker-visible open positions without stop-loss protection." : undefined}
          mono
        />
        <ControlField label="Unmatched Positions" value={String(report?.broker_truth_summary?.terminal_unmatched_open_position_count ?? 0)} danger={Number(report?.broker_truth_summary?.terminal_unmatched_open_position_count ?? 0) > 0} />
        <ControlField
          label="Unresolved Attempt Rows"
          value={String(unresolvedCount)}
          danger={brokerBlockingAttemptCount > 0}
          description={
            unresolvedCount > 0 && brokerBlockingAttemptCount === 0
              ? "Classified separately; not blocking live recovery by itself."
              : undefined
          }
          mono
        />
        <ControlField
          label="Test-like Attempts"
          value={String(syntheticLikeCount)}
          description={syntheticLikeCount > 0 ? "Synthetic/test-like audit rows; not a broker-review blocker." : undefined}
          mono
        />
        <ControlField label="Broker Review Attempts" value={String(brokerReviewCount)} danger={brokerReviewCount > 0} mono />
        <ControlField label="Unknown Attempt Rows" value={String(unknownUnresolvedCount)} danger={unknownUnresolvedCount > 0} mono />
        <ControlField label="Duplicate Suppressed" value={String(duplicateSuppressedCount)} danger={duplicateSuppressedCount > 0} mono />
        <ControlField label="Shape Duplicates" value={String(nearDuplicateSuppressedCount)} danger={nearDuplicateSuppressedCount > 0} mono />
        <ControlField label="Idempotency Window" value={`${idempotencyWindowSeconds}s`} mono />
        <ControlField label="Exact Retry Key" value={idempotencyPolicy?.exact_retry_key ?? "decision_ref|order_id"} mono />
        <ControlField label="Near Duplicate Key" value={idempotencyPolicy?.near_duplicate_key ?? "automation order shape"} mono />
        <ControlField label="Latest Shape Key" value={String(latestAttemptShapeKey)} mono />
        <ControlField label="Pending Receipts" value={String(terminalPendingReceiptCount)} danger={terminalPendingReceiptCount > 0} mono />
        <ControlField
          label="Archive Preview"
          value={String(terminalArchivePreviewCount)}
          description={terminalArchivePreviewCount > 0 ? "Dry-run only; owner execution required to archive." : undefined}
          mono
        />
        <ControlField label="Live Pilot Trades" value={String(report?.live_pilot_summary?.live_trade_count ?? 0)} mono />
        <ControlField label="Fingerprint" value={String(report?.current_fingerprint ?? "pending")} mono />
      </div>

      {report && report.missing_requirements.length > 0 && (
        <div className="control-field-desc" style={{ color: "var(--danger)", marginTop: 8 }}>
          Missing: {report.missing_requirements.join("; ")}
        </div>
      )}

      {liveMoneyProgression && (
        <div className="control-field-desc" style={{ marginTop: 8, color: liveMoneyProgression.full_progression_clear ? "var(--success)" : "var(--warning)" }}>
          Live-money packet: {liveMoneyProgression.status}; cache {liveMoneyCacheLabel}. {liveMoneyProgression.next_action}
        </div>
      )}

      {wasteDirectionReview && (
        <div className="control-field-desc" style={{ marginTop: 8, color: wasteDirectionReview.direction_edge_confirmed ? "var(--success)" : "var(--warning)" }}>
          WASTE direction: {wasteDirectionReview.status}. {wasteDirectionReview.next_action}
        </div>
      )}

      {wasteDirectionLearning && (
        <div className="control-field-desc" style={{ marginTop: 8, color: wasteDirectionLearning.learning_ready_for_adaptation ? "var(--success)" : "var(--text-secondary)" }}>
          Direction learning: {wasteDirectionLearning.status}. {wasteDirectionLearning.next_action}
        </div>
      )}

      {wasteDirectionOutcomeBinding && (
        <div className="control-field-desc" style={{ marginTop: 8, color: outcomeReady ? "var(--success)" : "var(--text-secondary)" }}>
          Direction outcomes: {wasteDirectionOutcomeBinding.status}. {wasteDirectionOutcomeBinding.next_action}
        </div>
      )}

      {wastePaperSampleCollector && (
        <div className="control-field-desc" style={{ marginTop: 8, color: paperSampleComplete ? "var(--success)" : paperSampleMarketReady ? "var(--warning)" : "var(--text-secondary)" }}>
          Paper sample collection: {wastePaperSampleCollector.status}. {wastePaperSampleCollector.next_action}
        </div>
      )}

      {wastePaperSampleCollectorScheduler && (
        <div className="control-field-desc" style={{ marginTop: 8, color: paperSampleSchedulerRunning ? "var(--warning)" : "var(--text-secondary)" }}>
          Paper sample scheduler: {wastePaperSampleCollectorScheduler.status}. {wastePaperSampleCollectorScheduler.next_action}
        </div>
      )}

      {wasteAdaptationPromotionRule && (
        <div className="control-field-desc" style={{ marginTop: 8, color: promotionReady ? "var(--success)" : "var(--text-secondary)" }}>
          Adaptation promotion: {wasteAdaptationPromotionRule.status}. {wasteAdaptationPromotionRule.next_action}
        </div>
      )}

      {wasteAdaptationPlan && (
        <div className="control-field-desc" style={{ marginTop: 8, color: wasteAdaptationPlan.adaptation_ready_for_owner_review ? "var(--success)" : "var(--text-secondary)" }}>
          WASTE adaptation: {wasteAdaptationPlan.status}. {wasteAdaptationPlan.next_action}
        </div>
      )}

      {wasteAdaptationApplyPreview && (
        <div className="control-field-desc" style={{ marginTop: 8, color: wasteAdaptationApplyPreview.preview_ready_for_owner_review ? "var(--success)" : "var(--text-secondary)" }}>
          Apply preview: {wasteAdaptationApplyPreview.status}. {wasteAdaptationApplyPreview.next_action}
        </div>
      )}

      {wasteAdaptationOwnerReview && (
        <div className="control-field-desc" style={{ marginTop: 8, color: adaptationOwnerAcceptCurrent ? "var(--success)" : adaptationOwnerReviewCurrent ? "var(--warning)" : "var(--text-secondary)" }}>
          Owner adaptation review: {wasteAdaptationOwnerReview.owner_review_status}. {wasteAdaptationOwnerReview.next_action}
        </div>
      )}

      {wasteAdaptationPaperApply && (
        <div className="control-field-desc" style={{ marginTop: 8, color: adaptationPaperApplyCurrent ? "var(--success)" : adaptationPaperApplyReady ? "var(--warning)" : "var(--text-secondary)" }}>
          Paper adaptation apply: {wasteAdaptationPaperApply.status}. {wasteAdaptationPaperApply.next_action}
        </div>
      )}

      {recoveryPacket && (
        <div className="control-field-desc" style={{ marginTop: 8, color: recoveryPacket.can_reconcile_unresolved_attempts ? "var(--success)" : "var(--warning)" }}>
          Recovery packet: {recoveryPacket.status}. {recoveryPacket.next_action}
        </div>
      )}

      {idempotencyPolicy && (
        <div className="control-field-desc" style={{ marginTop: 8, color: duplicateSuppressedCount > 0 ? "var(--warning)" : "var(--text-secondary)" }}>
          Idempotency: exact retries use {idempotencyPolicy.exact_retry_key}; automation near-duplicates use {idempotencyPolicy.near_duplicate_key} for {idempotencyWindowSeconds}s. Manual and compound/pyramid adds are excluded from the near-duplicate block.
        </div>
      )}

      {terminalReceiptPacket && (
        <div className="control-field-desc" style={{ marginTop: 8, color: terminalReceiptPacket.terminal_reconciliation_clean_for_live ? "var(--success)" : "var(--warning)" }}>
          Terminal receipt packet: {terminalReceiptPacket.status}. {terminalReceiptPacket.next_action}
        </div>
      )}

      {terminalArchiveAction && (
        <div className="control-field-desc" style={{ marginTop: 8, color: terminalArchiveAction.journal_rewritten ? "var(--success)" : "var(--warning)" }}>
          Archive action: {terminalArchiveAction.status}. {terminalArchiveAction.next_action}
        </div>
      )}

      {terminalRefreshAction && (
        <div className="control-field-desc" style={{ marginTop: 8, color: terminalRefreshAction.status.includes("FAILED") ? "var(--danger)" : "var(--warning)" }}>
          Recovery refresh: {terminalRefreshAction.status}. {terminalRefreshAction.next_action}
        </div>
      )}

      {brokerTruthRecoveryPacket && (
        <div className="control-field-desc" style={{ marginTop: 8, color: brokerTruthRecoveryPacket.broker_truth_clear_for_live_recovery ? "var(--success)" : "var(--warning)" }}>
          Broker truth packet: {brokerTruthRecoveryPacket.status}. {brokerTruthRecoveryPacket.next_action}
        </div>
      )}

      <label className="control-field" style={{ marginTop: 12 }}>
        <span className="field-label">Owner recovery notes</span>
        <textarea className="mobile-api-input broker-reality-textarea" value={notes} onChange={(event) => setNotes(event.target.value)} />
      </label>

      {unresolvedAttempts.length > 0 && (
        <div className="control-grid" style={{ marginTop: 12 }}>
          <label className="control-field">
            <span className="field-label">Unresolved attempt</span>
            <select
              className="mobile-api-input"
              value={selectedAttemptId}
              onChange={(event) => setSelectedAttemptId(event.target.value)}
            >
              {unresolvedAttempts.map((attempt) => (
                <option key={attempt.attempt_id ?? ""} value={attempt.attempt_id ?? ""}>
                  {formatAttemptOption(attempt)}
                </option>
              ))}
            </select>
          </label>
          <ControlField
            label="Selected Attempt"
            value={selectedAttemptId || "NONE"}
            danger={Boolean(selectedAttemptId)}
            mono
          />
        </div>
      )}

      {selectedAttempt && (
        <div className="control-grid" style={{ marginTop: 12 }}>
          <ControlField label="Attempt Status" value={selectedAttempt.status ?? "UNKNOWN"} danger={!selectedAttempt.result_finalized} mono />
          <ControlField label="Result Status" value={selectedAttempt.result_status ?? "UNKNOWN"} danger={Boolean(selectedAttempt.bridge_touch_unknown)} mono />
          <ControlField label="Initiator" value={formatUnknownValue(selectedAttemptInitiator?.kind ?? selectedAttempt.source ?? "UNKNOWN")} mono />
          <ControlField label="Runtime Lane" value={formatUnknownValue(selectedAttemptRuntimeLane?.effective_lane ?? selectedAttempt.mode ?? "UNKNOWN")} mono />
          <ControlField label="Final Gate" value={formatUnknownValue(selectedAttemptDispatchPath?.terminal_stage ?? "UNKNOWN")} mono />
          <ControlField label="Bridge Touch" value={formatUnknownValue(selectedAttemptDispatchPath?.bridge_touch_state ?? (selectedAttempt.bridge_touch_unknown ? "TOUCH_UNKNOWN" : "NOT_ATTACHED"))} danger={Boolean(selectedAttempt.bridge_touch_unknown)} mono />
          <ControlField label="Audit Snapshot" value={formatUnknownValue(selectedAttemptAudit?.status ?? selectedAttempt.status ?? "UNKNOWN")} mono />
          <ControlField label="Provenance Hash" value={formatUnknownValue(selectedAttemptProvenance?.provenance_hash ?? "NOT_ATTACHED")} mono />
          <ControlField label="Config Hash" value={formatUnknownValue(selectedAttemptProvenance?.config_hash ?? "NOT_ATTACHED")} mono />
        </div>
      )}

      <div className="sweep-action-row" style={{ marginTop: 12 }}>
        <button className="broker-risk-apply-button" type="button" disabled={busy} onClick={() => void refresh()}>Refresh</button>
        <button className="mobile-api-button ghost" type="button" disabled={busy} onClick={() => void runPaperSampleCollectorNow()}>Run Sample Collector</button>
        <button className="mobile-api-button ghost" type="button" disabled={busy} onClick={() => void togglePaperSampleCollectorScheduler()}>
          {paperSampleSchedulerRunning ? "Stop Sample Scheduler" : "Start Sample Scheduler"}
        </button>
        <button className="mobile-api-button ghost" type="button" disabled={busy} onClick={() => void runBrokerTruthNow()}>Run Broker Truth</button>
        <button className="mobile-api-button ghost" type="button" disabled={busy} onClick={() => void toggleBrokerTruthMonitor()}>
          {brokerTruthRunning ? "Stop Truth Monitor" : "Start Truth Monitor"}
        </button>
        <button className="mobile-api-button ghost" type="button" disabled={busy} onClick={() => void archiveTerminalReceipts(false)}>Preview Archive</button>
        <button className="mobile-api-button ghost" type="button" disabled={busy} onClick={() => void refreshTerminalRecoveryChain(false)}>Plan Refresh</button>
        <label className="sweep-confirm-check">
          <input type="checkbox" checked={ownerConfirmAdaptationReview} onChange={(event) => setOwnerConfirmAdaptationReview(event.target.checked)} />
          <span>Owner Adapt</span>
        </label>
        <button
          className="mobile-api-button ghost"
          type="button"
          disabled={busy}
          onClick={() => void recordAdaptationOwnerReview("HOLD_PAPER_ONLY")}
        >
          Hold Adapt
        </button>
        <button
          className="mobile-api-button ghost"
          type="button"
          disabled={busy}
          onClick={() => void recordAdaptationOwnerReview("REQUEST_MORE_EVIDENCE")}
        >
          More Evidence
        </button>
        <button
          className="sweep-action-button danger"
          type="button"
          disabled={busy}
          onClick={() => void recordAdaptationOwnerReview("ACCEPT_PAPER_ONLY")}
        >
          Accept Paper Adapt
        </button>
        <button
          className="mobile-api-button ghost"
          type="button"
          disabled={busy}
          onClick={() => void resetAdaptationOwnerReview()}
        >
          Reset Adapt Review
        </button>
        <label className="sweep-confirm-check">
          <input type="checkbox" checked={ownerConfirmAdaptationApply} onChange={(event) => setOwnerConfirmAdaptationApply(event.target.checked)} />
          <span>Owner Paper Apply</span>
        </label>
        <button
          className="sweep-action-button danger"
          type="button"
          disabled={busy}
          onClick={() => void recordAdaptationPaperApply()}
        >
          Record Paper Apply
        </button>
        <button
          className="mobile-api-button ghost"
          type="button"
          disabled={busy}
          onClick={() => void resetAdaptationPaperApply()}
        >
          Reset Paper Apply
        </button>
        <label className="sweep-confirm-check">
          <input type="checkbox" checked={ownerConfirmArchive} onChange={(event) => setOwnerConfirmArchive(event.target.checked)} />
          <span>Owner Archive</span>
        </label>
        <button
          className="sweep-action-button danger"
          type="button"
          disabled={busy}
          onClick={() => void archiveTerminalReceipts(true)}
        >
          Archive Stale Rows
        </button>
        <label className="sweep-confirm-check">
          <input type="checkbox" checked={ownerConfirmRefresh} onChange={(event) => setOwnerConfirmRefresh(event.target.checked)} />
          <span>Owner Refresh</span>
        </label>
        <button
          className="sweep-action-button danger"
          type="button"
          disabled={busy}
          onClick={() => void refreshTerminalRecoveryChain(true)}
        >
          Run Refresh Chain
        </button>
        <label className="sweep-confirm-check">
          <input type="checkbox" checked={ownerConfirm} onChange={(event) => setOwnerConfirm(event.target.checked)} />
          <span>Owner Confirm</span>
        </label>
        <button className="sweep-action-button danger" type="button" disabled={busy} onClick={() => void accept()}>Owner ACCEPT</button>
        <label className="sweep-confirm-check">
          <input type="checkbox" checked={ownerConfirmReconcile} onChange={(event) => setOwnerConfirmReconcile(event.target.checked)} />
          <span>Owner Reconcile</span>
        </label>
        <button
          className="sweep-action-button danger"
          type="button"
          disabled={busy}
          onClick={() => void reconcileAttempt()}
        >
          Reconcile Attempt
        </button>
        <button className="mobile-api-button ghost" type="button" disabled={busy} onClick={() => void reset()}>Reset</button>
      </div>

      {status && <div className="control-field-desc" style={{ marginTop: 8, color: status.includes("Couldn't") || status.includes("Cannot") || status.includes("API") ? "var(--danger)" : "var(--success)" }}>{status}</div>}
      <div className="control-field-desc" style={{ marginTop: 8 }}>
        {report?.claim_boundary ?? "Live recovery review does not place orders or move money; it gates more live orders after interruption evidence."}
      </div>
    </GlassPanel>
  );
}


export function unresolvedAttemptsFromRecovery(report: LiveRecoveryReport | null): OrderAttemptAuditAttempt[] {
  const attempts = report?.order_attempt_summary?.unresolved_real_attempts;
  if (!Array.isArray(attempts)) return [];
  return attempts.filter((attempt): attempt is OrderAttemptAuditAttempt => Boolean(attempt) && typeof attempt === "object");
}


export function formatAttemptOption(attempt: OrderAttemptAuditAttempt): string {
  const id = attempt.attempt_id ?? "unknown-attempt";
  const symbol = attempt.symbol ?? "NA";
  const direction = attempt.direction ?? "NA";
  const source = attempt.source ?? "unknown";
  const classification = "classification_status" in attempt && attempt.classification_status
    ? ` | ${String(attempt.classification_status)}`
    : "";
  const bridgeUnknown = attempt.bridge_touch_unknown ? " | BRIDGE_TOUCH_UNKNOWN" : "";
  return `${id} | ${symbol} ${direction} | ${source}${classification}${bridgeUnknown}`;
}


export function formatCacheAge(packet?: { cache_status?: string; cache_age_seconds?: number | null } | null): string {
  if (!packet) return "unavailable";
  const status = packet.cache_status ?? "direct";
  if (packet.cache_age_seconds == null) return status;
  return `${status} ${formatDuration(packet.cache_age_seconds)} old`;
}


export function formatDuration(seconds: number): string {
  const safeSeconds = Math.max(0, Math.floor(seconds));
  if (safeSeconds < 60) return `${safeSeconds}s`;
  const minutes = Math.floor(safeSeconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const extraMinutes = minutes % 60;
  return extraMinutes ? `${hours}h ${extraMinutes}m` : `${hours}h`;
}

