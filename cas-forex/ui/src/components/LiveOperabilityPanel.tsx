import { GlassPanel } from "./GlassPanel";
import { StatusChip } from "./StatusChip";
import type { BrokerSyncedRiskPreview, LiveReadinessCheck, LiveReadinessReport } from "../types/evidence";
import { detailEvidenceForLiveReadinessCheck } from "../util/movementSource";

type ChipVariant = "success" | "warning" | "danger" | "info" | "muted" | "paper";
type LiveReadinessMode = "default" | "broker-sync";

interface LiveOperabilityPanelProps {
  activeLiveReadiness: LiveReadinessReport | null | undefined;
  readinessMode: LiveReadinessMode;
  onReadinessModeChange: (mode: LiveReadinessMode) => void;
  brokerSyncBusy: boolean;
  brokerSyncUnavailable: boolean;
  activeBrokerRiskPreview: BrokerSyncedRiskPreview | null | undefined;
  brokerRiskApplying: boolean;
  brokerRiskApplyResult: BrokerSyncedRiskPreview | null;
  onApplyBrokerRiskReview: () => void;
}

export function LiveOperabilityPanel({
  activeLiveReadiness,
  readinessMode,
  onReadinessModeChange,
  brokerSyncBusy,
  brokerSyncUnavailable,
  activeBrokerRiskPreview,
  brokerRiskApplying,
  brokerRiskApplyResult,
  onApplyBrokerRiskReview,
}: LiveOperabilityPanelProps) {
  return (
    <GlassPanel
      title="Live Operability Checklist"
      subtitle={activeLiveReadiness ? activeLiveReadiness.plain_english_summary : "Computed gate report unavailable"}
      variant={activeLiveReadiness?.overall_status === "READY_FOR_LIVE_EXECUTION" ? "info" : "warning"}
    >
      {activeLiveReadiness ? (
        <>
          <div className="readiness-mode-row">
            <div className="readiness-mode-switch" role="tablist" aria-label="Live readiness mode">
              <button
                className={`readiness-mode-button ${readinessMode === "default" ? "active" : ""}`}
                type="button"
                role="tab"
                aria-selected={readinessMode === "default"}
                onClick={() => onReadinessModeChange("default")}
              >
                Default
              </button>
              <button
                className={`readiness-mode-button ${readinessMode === "broker-sync" ? "active" : ""}`}
                type="button"
                role="tab"
                aria-selected={readinessMode === "broker-sync"}
                onClick={() => onReadinessModeChange("broker-sync")}
              >
                Broker Sync
              </button>
            </div>
            {brokerSyncBusy && <span className="readiness-mode-note">Refreshing broker snapshot...</span>}
            {brokerSyncUnavailable && (
              <span className="readiness-mode-note">
                Broker sync preview unavailable; using the default readiness report only.
              </span>
            )}
          </div>
          <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
            <div className="metric-stack" style={{ padding: 0 }}>
              <Metric
                label="Overall"
                value={displayLiveCapabilityStatus(activeLiveReadiness.overall_status)}
                mono
                warning={activeLiveReadiness.overall_status !== "READY_FOR_LIVE_EXECUTION"}
              />
              <Metric label="Passed" value={`${activeLiveReadiness.checks_passed}/${activeLiveReadiness.checks_total}`} mono />
              <Metric label="Trading Edge" value={activeLiveReadiness.trading_edge_status} warning />
            </div>
            <div className="metric-stack" style={{ padding: 0 }}>
              <Metric label="Open" value={`${activeLiveReadiness.checks_open}`} mono warning={activeLiveReadiness.checks_open > 0} />
              <Metric label="Mismatch" value={`${activeLiveReadiness.checks_mismatch}`} mono danger={activeLiveReadiness.checks_mismatch > 0} />
              <Metric label="Unverifiable" value={`${activeLiveReadiness.checks_unverifiable}`} mono warning={activeLiveReadiness.checks_unverifiable > 0} />
            </div>
            <div className="metric-stack" style={{ padding: 0 }}>
              <Metric
                label="Live Trading"
                value={displayLiveCapabilityStatus(activeLiveReadiness.live_trading_status)}
                mono
                warning={activeLiveReadiness.live_trading_status !== "AUTHORIZED"}
              />
              <Metric
                label="Broker ACCEPT"
                value={displayLiveCapabilityStatus(activeLiveReadiness.broker_accept_status)}
                mono
                warning={activeLiveReadiness.broker_accept_status !== "AUTHORIZED"}
              />
              <Metric
                label="Broker Seed"
                value={activeLiveReadiness.sync_to_broker_snapshot ? `$${(activeLiveReadiness.broker_snapshot_initial_investment_usd ?? 0).toLocaleString()}` : "OFF"}
                mono
                warning={!!activeLiveReadiness.sync_to_broker_snapshot}
              />
              <Metric
                label="Payment Movement"
                value={activeLiveReadiness.payment_movement_authorized ? "AUTHORIZED" : "PAYMENT SETUP PENDING"}
                mono
                warning={!activeLiveReadiness.payment_movement_authorized}
              />
            </div>
          </div>
          {readinessMode === "broker-sync" && activeBrokerRiskPreview && (
            <div className="broker-risk-preview">
              <div className="broker-risk-preview-header">
                <span>Broker-Synced Paper Risk Preview</span>
                <div className="broker-risk-preview-actions">
                  <StatusChip label={activeBrokerRiskPreview.risk_status} variant="paper" size="sm" />
                  <button
                    className="broker-risk-apply-button"
                    type="button"
                    onClick={onApplyBrokerRiskReview}
                    disabled={brokerRiskApplying || activeBrokerRiskPreview.already_applied === true}
                  >
                    {brokerRiskApplying ? "Applying..." : activeBrokerRiskPreview.already_applied ? "Applied" : "Apply"}
                  </button>
                </div>
              </div>
              <div className="dashboard-grid-3col">
                <div className="metric-stack" style={{ padding: 0 }}>
                  <Metric label="Broker Seed" value={`$${activeBrokerRiskPreview.broker_snapshot_initial_investment_usd.toLocaleString()}`} mono warning />
                  <Metric label="Default Seed" value={`$${activeBrokerRiskPreview.default_risk_review_account_equity_usd.toLocaleString()}`} mono />
                </div>
                <div className="metric-stack" style={{ padding: 0 }}>
                  <Metric label="Preview Lots" value={`${activeBrokerRiskPreview.total_planned_lots.toFixed(2)} lots`} mono />
                  <Metric label="Default Lots" value={`${activeBrokerRiskPreview.default_total_planned_lots.toFixed(2)} lots`} mono />
                </div>
                <div className="metric-stack" style={{ padding: 0 }}>
                  <Metric label="Preview Risk" value={`$${activeBrokerRiskPreview.total_planned_risk_usd.toFixed(2)}`} mono />
                  <Metric label="Risk Delta" value={`$${activeBrokerRiskPreview.delta_vs_default.total_planned_risk_usd.toFixed(2)}`} mono warning />
                </div>
              </div>
              <div className="broker-risk-preview-note">{activeBrokerRiskPreview.next_action}</div>
              {brokerRiskApplyResult && (
                <div className="broker-risk-apply-result">
                  {brokerRiskApplyResult.evidence_appended
                    ? `Evidence appended to ${brokerRiskApplyResult.paper_risk_status_path ?? "paper-risk-status.json"}`
                    : brokerRiskApplyResult.already_applied
                      ? "Broker-synced paper risk is already the latest active review."
                      : "Apply request did not append evidence."}
                </div>
              )}
            </div>
          )}
          <div className="gate-grid">
            {activeLiveReadiness.checks.map((check) => (
              <GateItem key={check.gate_id} check={check} />
            ))}
          </div>
          {activeLiveReadiness.next_actions.length > 0 && (
            <div className="next-command" style={{ marginTop: 12 }}>
              <code className="next-command-text">{activeLiveReadiness.next_actions[0]}</code>
            </div>
          )}
        </>
      ) : (
        <div className="no-data-message"><p>Live operability checklist is not available in the dashboard payload.</p></div>
      )}
    </GlassPanel>
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
    <div className="dashboard-metric">
      <span className="field-label">{label}</span>
      <span className={`field-value ${mono ? "mono" : ""}`} style={{ color: danger ? "var(--danger)" : warning ? "var(--warning)" : undefined }}>{value}</span>
    </div>
  );
}

function GateItem({ check }: { check: LiveReadinessCheck }) {
  const evidenceDetail = detailEvidenceForLiveReadinessCheck(check);
  const followup = evidenceDetail || check.next_action;
  return (
    <div className="gate-item">
      <div className="gate-item-header">
        <span className="gate-item-label">{check.label}</span>
        <StatusChip label={displayLiveCapabilityStatus(check.status)} variant={gateVariant(check.status)} size="sm" />
      </div>
      <div className="gate-item-detail">{check.plain_english}</div>
      {followup && followup !== check.plain_english && <div className="gate-item-next">{followup}</div>}
    </div>
  );
}

function gateVariant(status: string): ChipVariant {
  if (status === "PASSED" || status === "AUTHORIZED") return "success";
  if (status === "OPEN" || status === "UNVERIFIABLE" || isOwnerPendingStatus(status)) return "warning";
  if (status === "MISMATCH") return "danger";
  return "muted";
}

function displayLiveCapabilityStatus(status: string | null | undefined): string {
  const normalized = String(status ?? "").toUpperCase();
  if (normalized.includes("PAYMENT") && isOwnerPendingStatus(normalized)) return "PAYMENT SETUP PENDING";
  if (normalized === "NOT AUTHORIZED") return "OWNER PENDING";
  if (isOwnerPendingStatus(normalized)) return "OWNER PENDING";
  return status || "UNKNOWN";
}

function isOwnerPendingStatus(status: string | null | undefined): boolean {
  const normalized = String(status ?? "").toUpperCase();
  return normalized.includes("NOT LICENSED") || normalized.includes("CURRENTLY NOT LICENSED");
}
