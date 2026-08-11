/* Extracted from pages/SettingsPage.tsx (settings decomposition, slice 4). */

import { GlassPanel } from "../../components/GlassPanel";
import { StatusChip } from "../../components/StatusChip";
import { BrokerRealityReview, fetchAccountReconciliation } from "../../data/api";
import { AccountReconciliationReport } from "../../types/evidence";
import { brokerPortalInfo } from "../../util/brokerPortal";
import { describeReconciliationMovementTruth } from "../../util/movementSource";
import { useState } from "react";

export function BrokerFundingHandoffPanel({ brokerReality }: { brokerReality?: BrokerRealityReview }) {
  const [reconciliation, setReconciliation] = useState<AccountReconciliationReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const brokerPortal = brokerPortalInfo(
    brokerReality?.broker_id,
    brokerReality?.broker_display_name,
    brokerReality?.broker_website,
  );

  async function syncBrokerSnapshot() {
    setBusy(true);
    setStatus("");
    try {
      const report = await fetchAccountReconciliation(true);
      setReconciliation(report);
      setStatus(
        report
          ? "Broker snapshot sync completed. CAS can now compare account balance/equity against broker evidence."
          : "Broker snapshot sync returned no report.",
      );
    } catch {
      setStatus("Couldn't sync broker snapshot - confirm the API and terminal/broker receipt path are reachable.");
    } finally {
      setBusy(false);
    }
  }

  const snapshot = reconciliation?.broker_snapshot_initial_investment_usd;
  const blockerCount = reconciliation?.blockers?.length ?? 0;
  const syncStatus = reconciliation?.overall_status ?? "READY";
  const statusVariant = syncStatus === "RECONCILIATION_FAILED"
    ? "danger"
    : syncStatus === "RECONCILED_WITH_WARNINGS"
      ? "warning"
      : "info";
  const movementTruth = describeReconciliationMovementTruth(reconciliation);

  return (
    <GlassPanel title="Broker Funding Handoff" subtitle="Fund at the broker portal; CAS verifies the broker snapshot after funding">
      <div className="control-grid">
        <div className="control-field">
          <div className="control-field-header">
            <span className="field-label">Funding Route</span>
            <StatusChip label="BROKER PORTAL" variant="info" size="sm" />
          </div>
          <div className="control-field-desc">{brokerPortal.label} client portal: KYC, deposits, withdrawals, and account funding.</div>
        </div>
        <div className="control-field">
          <div className="control-field-header">
            <span className="field-label">CAS Custody</span>
            <StatusChip label="NO RAW BANK/CARD STORAGE" variant="success" size="sm" />
          </div>
          <div className="control-field-desc">CAS reads broker/terminal evidence after funding; the broker/provider handles payment details.</div>
        </div>
        <div className="control-field">
          <div className="control-field-header">
            <span className="field-label">Broker Snapshot</span>
            <StatusChip label={syncStatus} variant={statusVariant} size="sm" />
          </div>
          <div className="control-field-desc">
            {snapshot != null
              ? `Broker snapshot balance/equity seed: $${snapshot.toFixed(2)}.`
              : "Run sync after broker funding and terminal receipt/account snapshot are visible."}
          </div>
        </div>
        <div className="control-field">
          <div className="control-field-header">
            <span className="field-label">Movement Feed</span>
            <StatusChip label={movementTruth.feedLabel} variant={movementTruth.feedTone} size="sm" />
          </div>
          <div className="control-field-desc">
            {movementTruth.detail
              ? `Price source: ${movementTruth.statusLabel}. ${movementTruth.detail}`
              : "Broker snapshot sync has not reported canonical movement-source truth yet."}
          </div>
        </div>
        <div className="control-field">
          <div className="control-field-header">
            <span className="field-label">Blockers</span>
            <StatusChip label={`${blockerCount}`} variant={blockerCount ? "warning" : "success"} size="sm" />
          </div>
          <div className="control-field-desc">
            {blockerCount ? reconciliation?.blockers.slice(0, 2).join("; ") : "No broker-sync blockers loaded in this panel."}
          </div>
        </div>
      </div>
      <div className="mobile-api-row" style={{ marginTop: 12 }}>
        <a className="mobile-api-button" href={brokerPortal.url} target="_blank" rel="noreferrer">
          Open Broker Portal
        </a>
        <button className="mobile-api-button ghost" type="button" disabled={busy} onClick={() => void syncBrokerSnapshot()}>
          {busy ? "Syncing..." : "Sync Broker Snapshot"}
        </button>
      </div>
      {status && (
        <div
          className="control-field-desc"
          style={{ marginTop: 8, color: status.startsWith("Couldn't") ? "var(--danger)" : "var(--success)" }}
        >
          {status}
        </div>
      )}
      <div className="control-field-desc" style={{ marginTop: 8 }}>
        Funding is external custody; CAS uses the verified broker snapshot for account reconciliation, risk sizing, and readiness checks.
      </div>
    </GlassPanel>
  );
}

