import { useEffect, useState } from "react";
import type {
  AccountReconciliationReport,
  BrokerTruthMonitorStatus,
  LiveReadinessCheck,
  LiveReadinessReport,
} from "../types/evidence";
import { apiGet } from "../data/apiCore";
import { GlassPanel } from "./GlassPanel";
import { StatusChip } from "./StatusChip";
import { detailEvidenceForLiveReadinessCheck } from "../util/movementSource";

type ChipVariant = "success" | "warning" | "danger" | "info" | "muted" | "paper";

interface LiveReadinessSummaryPanelProps {
  initialLiveReadiness?: LiveReadinessReport | null;
  initialAccountReconciliation?: AccountReconciliationReport | null;
  initialBrokerTruthMonitor?: BrokerTruthMonitorStatus | null;
  refreshIntervalMs?: number;
}

export function LiveReadinessSummaryPanel({
  initialLiveReadiness = null,
  initialAccountReconciliation = null,
  initialBrokerTruthMonitor = null,
  refreshIntervalMs = 30_000,
}: LiveReadinessSummaryPanelProps) {
  const [liveReadiness, setLiveReadiness] = useState<LiveReadinessReport | null>(initialLiveReadiness);
  const [accountReconciliation, setAccountReconciliation] = useState<AccountReconciliationReport | null>(initialAccountReconciliation);
  const [brokerTruthMonitor, setBrokerTruthMonitor] = useState<BrokerTruthMonitorStatus | null>(initialBrokerTruthMonitor);

  useEffect(() => {
    if (initialLiveReadiness) setLiveReadiness(initialLiveReadiness);
  }, [initialLiveReadiness]);

  useEffect(() => {
    if (initialAccountReconciliation) setAccountReconciliation(initialAccountReconciliation);
  }, [initialAccountReconciliation]);

  useEffect(() => {
    if (initialBrokerTruthMonitor) setBrokerTruthMonitor(initialBrokerTruthMonitor);
  }, [initialBrokerTruthMonitor]);

  useEffect(() => {
    let cancelled = false;

    async function refresh() {
      const [nextReadiness, nextReconciliation, nextBrokerTruth] = await Promise.all([
        fetchLiveReadinessSummary(),
        fetchAccountReconciliationSummary(),
        fetchBrokerTruthSummary(),
      ]);
      if (cancelled) return;
      if (nextReadiness) setLiveReadiness(nextReadiness);
      if (nextReconciliation) setAccountReconciliation(nextReconciliation);
      if (nextBrokerTruth) setBrokerTruthMonitor(nextBrokerTruth);
    }

    void refresh();
    const intervalId = window.setInterval(() => void refresh(), refreshIntervalMs);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [refreshIntervalMs]);

  if (!liveReadiness) {
    return (
      <GlassPanel title="Live Gate Summary" subtitle="Current live blockers, broker truth, and next actions">
        <div className="control-field-desc">Live readiness summary is syncing.</div>
      </GlassPanel>
    );
  }

  const blockingChecks = liveReadiness.checks.filter((check) => check.blocks_live && check.status !== "PASSED").slice(0, 4);
  const brokerTruthReport = brokerTruthMonitor?.latest_report ?? null;
  const notReady = liveReadiness.overall_status !== "READY_FOR_LIVE_EXECUTION";
  const brokerTruthBlocked = !brokerTruthMonitor?.ready_for_live;
  const reconciliationStatus = accountReconciliation?.overall_status ?? "SYNCING";
  const mt5Connected = brokerTruthReport?.mt5_connected;
  const mt5IdentityMatch = brokerTruthReport?.mt5_account_identity_matches_config;
  const mt5ActualIdentity = formatMt5Identity(
    brokerTruthReport?.mt5_account,
    brokerTruthReport?.mt5_account_server,
  );
  const mt5ExpectedIdentity = formatMt5Identity(
    brokerTruthReport?.mt5_expected_account,
    brokerTruthReport?.mt5_expected_server,
  );
  const brokerTruthProtectionStatus = String(brokerTruthReport?.position_protection_status ?? "POSITION_PROTECTION_UNAVAILABLE");
  const brokerTruthUnprotectedCount = Number(brokerTruthReport?.position_protection_unprotected_position_count ?? 0);
  const brokerTruthProtectionDetail = String(brokerTruthReport?.position_protection_detail ?? "").trim();
  const brokerTruthAutoHaltReasonIds = Array.isArray(brokerTruthReport?.monitor_auto_halt_reason_ids)
    ? brokerTruthReport.monitor_auto_halt_reason_ids.filter((value: unknown): value is string => typeof value === "string" && value.trim().length > 0)
    : [];
  const brokerTruthAutoHaltLatched = Boolean(brokerTruthReport?.auto_halt_latched_from_monitor) || brokerTruthAutoHaltReasonIds.length > 0;
  const brokerTruthReasonSummary = formatBrokerTruthReasonList(brokerTruthAutoHaltReasonIds);
  const blockingCount =
    liveReadiness.checks_open
    + liveReadiness.checks_mismatch
    + liveReadiness.checks_unverifiable
    + liveReadiness.checks_currently_not_licensed;

  return (
    <GlassPanel
      title="Live Gate Summary"
      subtitle={liveReadiness.plain_english_summary || "Current live blockers, broker truth, and next actions"}
      variant={notReady ? "warning" : "info"}
    >
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <StatusChip
          label={displayLiveCapabilityStatus(liveReadiness.overall_status)}
          variant={notReady ? "warning" : "success"}
          size="sm"
        />
        <StatusChip
          label={brokerTruthMonitor?.ready_for_live ? "BROKER TRUTH READY" : "BROKER TRUTH BLOCKED"}
          variant={brokerTruthBlocked ? "warning" : "success"}
          size="sm"
        />
        <StatusChip
          label={brokerTruthAutoHaltLatched ? "BROKER TRUTH PAPER FORCE" : "BROKER TRUTH WATCHING"}
          variant={brokerTruthAutoHaltLatched ? "danger" : "success"}
          size="sm"
        />
        <StatusChip
          label={shortPositionProtectionStatus(brokerTruthProtectionStatus)}
          variant={positionProtectionVariant(brokerTruthProtectionStatus, brokerTruthUnprotectedCount)}
          size="sm"
        />
        <StatusChip
          label={reconciliationStatus.replace(/_/g, " ")}
          variant={reconciliationVariant(reconciliationStatus)}
          size="sm"
        />
        <StatusChip
          label={mt5Connected === true ? "MT5 CONNECTED" : mt5Connected === false ? "MT5 OFFLINE" : "MT5 SYNCING"}
          variant={mt5Connected === true ? "success" : mt5Connected === false ? "danger" : "muted"}
          size="sm"
        />
        <StatusChip
          label={mt5IdentityMatch === true ? "ACCOUNT MATCH" : mt5IdentityMatch === false ? "WRONG ACCOUNT" : "ACCOUNT UNVERIFIED"}
          variant={mt5IdentityMatch === true ? "success" : mt5IdentityMatch === false ? "danger" : "warning"}
          size="sm"
        />
      </div>

      <div className="dashboard-grid-3col">
        <Metric label="Passed" value={`${liveReadiness.checks_passed}/${liveReadiness.checks_total}`} mono />
        <Metric label="Blocking Checks" value={String(blockingCount)} mono warning={blockingCount > 0} />
        <Metric label="Broker Truth" value={shortBrokerTruthStatus(brokerTruthMonitor?.monitor_status)} mono warning={brokerTruthBlocked} />
        <Metric label="Connected Account" value={mt5ActualIdentity} mono danger={mt5IdentityMatch === false} warning={mt5IdentityMatch == null} />
        <Metric label="Configured Account" value={mt5ExpectedIdentity} mono warning={mt5ExpectedIdentity === "UNSET"} />
        <Metric
          label="Truth Halt Reasons"
          value={brokerTruthReasonSummary}
          mono
          danger={brokerTruthAutoHaltLatched}
          warning={!brokerTruthAutoHaltLatched && brokerTruthReasonSummary !== "NONE"}
        />
        <Metric
          label="Position Protection"
          value={shortPositionProtectionStatus(brokerTruthProtectionStatus)}
          mono
          danger={brokerTruthUnprotectedCount > 0}
          warning={brokerTruthProtectionStatus === "POSITION_PROTECTION_UNAVAILABLE"}
        />
        <Metric
          label="Unprotected Positions"
          value={String(brokerTruthUnprotectedCount)}
          mono
          danger={brokerTruthUnprotectedCount > 0}
        />
        <Metric
          label="Live Trading"
          value={displayLiveCapabilityStatus(liveReadiness.live_trading_status)}
          mono
          warning={liveReadiness.live_trading_status !== "AUTHORIZED"}
        />
        <Metric
          label="Broker ACCEPT"
          value={displayLiveCapabilityStatus(liveReadiness.broker_accept_status)}
          mono
          warning={liveReadiness.broker_accept_status !== "AUTHORIZED"}
        />
        <Metric
          label="Payment Movement"
          value={liveReadiness.payment_movement_authorized ? "AUTHORIZED" : "PENDING"}
          mono
          warning={!liveReadiness.payment_movement_authorized}
        />
      </div>

      {(brokerTruthAutoHaltLatched || brokerTruthProtectionDetail || brokerTruthUnprotectedCount > 0 || mt5IdentityMatch !== true) && (
        <div style={{ marginTop: 12 }}>
          <div className="field-label" style={{ marginBottom: 6 }}>Broker Truth Enforcement</div>
          <div className="summary-list">
            {brokerTruthAutoHaltLatched && (
              <div className="summary-row" style={{ justifyContent: "flex-start", gap: 8, alignItems: "flex-start" }}>
                <StatusChip label="PAPER FORCE" variant="danger" size="sm" />
                <span style={{ color: "var(--text-secondary)", fontSize: "0.74rem", lineHeight: 1.4 }}>
                  Broker-truth monitor latched fail-closed because of: {brokerTruthReasonSummary}.
                </span>
              </div>
            )}
            {(brokerTruthProtectionDetail || brokerTruthUnprotectedCount > 0) && (
              <div className="summary-row" style={{ justifyContent: "flex-start", gap: 8, alignItems: "flex-start" }}>
                <StatusChip
                  label={shortPositionProtectionStatus(brokerTruthProtectionStatus)}
                  variant={positionProtectionVariant(brokerTruthProtectionStatus, brokerTruthUnprotectedCount)}
                  size="sm"
                />
                <span style={{ color: "var(--text-secondary)", fontSize: "0.74rem", lineHeight: 1.4 }}>
                  {brokerTruthProtectionDetail || `${brokerTruthUnprotectedCount} broker-visible position(s) have no stop-loss protection.`}
                </span>
              </div>
            )}
            {mt5IdentityMatch !== true && (
              <div className="summary-row" style={{ justifyContent: "flex-start", gap: 8, alignItems: "flex-start" }}>
                <StatusChip label={mt5IdentityMatch === false ? "WRONG ACCOUNT" : "ACCOUNT UNVERIFIED"} variant={mt5IdentityMatch === false ? "danger" : "warning"} size="sm" />
                <span style={{ color: "var(--text-secondary)", fontSize: "0.74rem", lineHeight: 1.4 }}>
                  Connected: {mt5ActualIdentity}. Configured owner account: {mt5ExpectedIdentity}. Live execution remains blocked until these match exactly.
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {blockingChecks.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <div className="field-label" style={{ marginBottom: 6 }}>Top Blocking Checks</div>
          <div className="summary-list">
            {blockingChecks.map((check) => (
              <BlockingCheckRow key={check.gate_id} check={check} />
            ))}
          </div>
        </div>
      )}

      {liveReadiness.next_actions.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <div className="field-label" style={{ marginBottom: 6 }}>Next Actions</div>
          <div className="summary-list">
            {liveReadiness.next_actions.slice(0, 3).map((action) => (
              <div key={action} className="summary-row" style={{ justifyContent: "flex-start", gap: 8, alignItems: "flex-start" }}>
                <span style={{ color: "var(--warning)", lineHeight: 1.2 }}>!</span>
                <span style={{ color: "var(--text-secondary)", fontSize: "0.74rem", lineHeight: 1.4 }}>{action}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="control-field-desc" style={{ marginTop: 10 }}>
        {liveReadiness.claim_boundary || "Live readiness is observational only. It summarizes blockers and next actions; it does not authorize live trading, place orders, or move money."}
      </div>
    </GlassPanel>
  );
}

function BlockingCheckRow({ check }: { check: LiveReadinessCheck }) {
  const evidenceDetail = detailEvidenceForLiveReadinessCheck(check);
  const followup = evidenceDetail || check.next_action;
  return (
    <div className="summary-row" style={{ justifyContent: "flex-start", gap: 8, alignItems: "flex-start" }}>
      <StatusChip label={displayLiveCapabilityStatus(check.status)} variant={gateVariant(check.status)} size="sm" />
      <div style={{ minWidth: 0 }}>
        <div style={{ color: "var(--text-primary)", fontSize: "0.74rem", fontWeight: 600 }}>{check.label}</div>
        <div style={{ color: "var(--text-secondary)", fontSize: "0.72rem", lineHeight: 1.35 }}>
          {check.plain_english}
        </div>
        {followup && followup !== check.plain_english && (
          <div style={{ color: "var(--text-muted)", fontSize: "0.7rem", lineHeight: 1.35, marginTop: 4 }}>
            {followup}
          </div>
        )}
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  mono,
  danger,
  warning,
}: {
  label: string;
  value: string;
  mono?: boolean;
  danger?: boolean;
  warning?: boolean;
}) {
  return (
    <div className="control-field">
      <div className="field-label">{label}</div>
      <div className={`field-value ${mono ? "mono" : ""}`} style={{ marginTop: 4, color: danger ? "var(--danger)" : warning ? "var(--warning)" : undefined }}>
        {value}
      </div>
    </div>
  );
}

function gateVariant(status: string): ChipVariant {
  if (status === "PASSED" || status === "AUTHORIZED") return "success";
  if (status === "MISMATCH") return "danger";
  if (status === "OPEN" || status === "UNVERIFIABLE" || isOwnerPendingStatus(status)) return "warning";
  return "muted";
}

function displayLiveCapabilityStatus(status: string | null | undefined): string {
  const normalized = String(status ?? "").toUpperCase();
  if (normalized.includes("PAYMENT") && isOwnerPendingStatus(normalized)) return "PAYMENT SETUP PENDING";
  if (normalized === "NOT AUTHORIZED") return "OWNER PENDING";
  if (isOwnerPendingStatus(normalized)) return "OWNER PENDING";
  return String(status || "UNKNOWN").replace(/_/g, " ");
}

function isOwnerPendingStatus(status: string | null | undefined): boolean {
  const normalized = String(status ?? "").toUpperCase();
  return normalized.includes("NOT LICENSED") || normalized.includes("CURRENTLY NOT LICENSED");
}

function reconciliationVariant(status: string): ChipVariant {
  if (status === "RECONCILED") return "success";
  if (status === "RECONCILIATION_FAILED") return "danger";
  if (status === "RECONCILED_WITH_WARNINGS") return "warning";
  return "muted";
}

function shortBrokerTruthStatus(status: string | null | undefined): string {
  return String(status ?? "SYNCING")
    .replace(/^BROKER_TRUTH_/, "")
    .replace(/^MONITOR_/, "")
    .replace(/_/g, " ");
}

function formatBrokerTruthReasonList(values: string[] | null | undefined): string {
  if (!Array.isArray(values) || values.length === 0) return "NONE";
  return values.map(formatBrokerTruthReasonLabel).join(", ");
}

function formatBrokerTruthReasonLabel(value: string): string {
  const labels: Record<string, string> = {
    broker_truth_reconciliation: "Broker Truth",
    terminal_position_reconciliation: "Terminal Reconciliation",
    live_open_positions_crosscheck: "Open Position Crosscheck",
    live_position_stop_loss_protection: "Stop-Loss Protection",
    mt5_account_identity_matches_config: "MT5 Account Identity",
  };
  return labels[value] ?? value.replace(/_/g, " ");
}

function formatMt5Identity(login: number | null | undefined, server: string | null | undefined): string {
  const normalizedServer = String(server ?? "").trim();
  if (login == null && !normalizedServer) return "UNSET";
  return `${login == null ? "?" : `#${login}`} @ ${normalizedServer || "UNKNOWN"}`;
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

async function fetchLiveReadinessSummary(): Promise<LiveReadinessReport | null> {
  try {
    return await apiGet<LiveReadinessReport>("/readiness/live");
  } catch {
    return null;
  }
}

async function fetchAccountReconciliationSummary(): Promise<AccountReconciliationReport | null> {
  try {
    return await apiGet<AccountReconciliationReport>("/reconciliation/account");
  } catch {
    return null;
  }
}

async function fetchBrokerTruthSummary(): Promise<BrokerTruthMonitorStatus | null> {
  try {
    return await apiGet<BrokerTruthMonitorStatus>("/broker-truth-monitor/status/fast");
  } catch {
    return null;
  }
}
