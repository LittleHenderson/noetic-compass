/* Extracted from pages/SettingsPage.tsx (settings decomposition, slice 4). */

import { GlassPanel } from "../../components/GlassPanel";
import { StatusChip } from "../../components/StatusChip";
import { ControlField } from "../../components/settings/ControlField";
import { BrokerEmergencyActionResult, EmergencyControlsReport, LegalReviewControlReport, LegalReviewReadinessReport, OperationalReadinessReport, createOperatorBackup, fetchBrokerEmergencyStatus, fetchEmergencyControls, fetchLegalReviewControl, fetchLegalReviewReadiness, fetchOperationalReadiness, resetExternalMonitoringConfig, resetLegalReviewControl, runBrokerEmergencyAction, updateExternalMonitoringConfig, updateLegalReviewControl } from "../../data/api";
import { useEffect, useState } from "react";

type EmergencyControlRow = NonNullable<EmergencyControlsReport["controls"]>[number];

export function LegalReviewReadinessPanel() {
  const [report, setReport] = useState<LegalReviewReadinessReport | null>(null);
  const [control, setControl] = useState<LegalReviewControlReport | null>(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState({
    reviewed_by: "",
    review_date: "",
    scope: "Terms, risk disclosure, privacy, automated trading, AI limitations, broker connectivity, retail forex, public launch",
    review_artifact_path: "",
    review_artifact_sha256: "",
    matter_reference: "",
    jurisdictions: "",
    notes: "",
    qualified_counsel_confirmed: false,
    confirm_phrase: "",
  });

  useEffect(() => {
    void refresh();
  }, []);

  function syncDraftFromControl(nextControl: LegalReviewControlReport | null) {
    const record = nextControl?.current_record;
    if (!record) return;
    setDraft({
      reviewed_by: record.reviewed_by ?? "",
      review_date: record.review_date ?? "",
      scope: record.scope ?? "Terms, risk disclosure, privacy, automated trading, AI limitations, broker connectivity, retail forex, public launch",
      review_artifact_path: record.review_artifact_path ?? "",
      review_artifact_sha256: record.review_artifact_sha256 ?? "",
      matter_reference: record.matter_reference ?? "",
      jurisdictions: record.jurisdictions ?? "",
      notes: record.notes ?? "",
      qualified_counsel_confirmed: Boolean(record.qualified_counsel_confirmed),
      confirm_phrase: "",
    });
  }

  async function refresh() {
    setStatus("");
    const [nextReadiness, nextControl] = await Promise.all([
      fetchLegalReviewReadiness(),
      fetchLegalReviewControl(),
    ]);
    if (nextReadiness) setReport(nextReadiness);
    if (nextControl) {
      setControl(nextControl);
      syncDraftFromControl(nextControl);
    }
    if (!nextReadiness && !nextControl) {
      setStatus("Legal review control/readiness unavailable - is the API reachable?");
    }
  }

  async function saveCounselReviewRecord() {
    setBusy(true);
    setStatus("");
    try {
      const result = await updateLegalReviewControl({
        reviewed_by: draft.reviewed_by,
        review_date: draft.review_date,
        scope: draft.scope,
        review_artifact_path: draft.review_artifact_path,
        review_artifact_sha256: draft.review_artifact_sha256,
        matter_reference: draft.matter_reference,
        jurisdictions: draft.jurisdictions,
        notes: draft.notes,
        qualified_counsel_confirmed: draft.qualified_counsel_confirmed,
        confirm_phrase: draft.confirm_phrase,
        counsel_review_status: "accepted",
      });
      if (result.legal_review_readiness) setReport(result.legal_review_readiness);
      if (result.legal_review_control) {
        setControl(result.legal_review_control);
        syncDraftFromControl(result.legal_review_control);
      } else {
        await refresh();
      }
      setStatus("Counsel review metadata recorded. Public launch still depends on a real qualified counsel review and all other launch gates.");
    } catch (error) {
      const detail = error instanceof Error ? error.message : "";
      setStatus(detail || "Counsel review record save failed - check the typed confirmation, evidence hash, and owner access.");
    } finally {
      setBusy(false);
    }
  }

  async function resetCounselReviewRecord() {
    setBusy(true);
    setStatus("");
    try {
      const result = await resetLegalReviewControl();
      if (result.legal_review_readiness) setReport(result.legal_review_readiness);
      if (result.legal_review_control) {
        setControl(result.legal_review_control);
        syncDraftFromControl(result.legal_review_control);
      } else {
        await refresh();
      }
      setStatus("Local counsel review metadata reset. Public launch legal readiness is now blocked until a new accepted record is provided.");
    } catch (error) {
      const detail = error instanceof Error ? error.message : "";
      setStatus(detail || "Counsel review reset failed - check owner access and API reachability.");
    } finally {
      setBusy(false);
    }
  }

  const checks = report?.checks ?? [];
  const attentionChecks = checks.filter((check) => check.status !== "OK");
  const displayChecks = [...attentionChecks, ...checks.filter((check) => check.status === "OK")];
  const attentionCount = report?.attention_count ?? attentionChecks.length;
  const recordPath = report?.counsel_review_record_path ?? report?.required_documents?.counsel_review_record ?? "docs/legal/CAS_FOREX_COUNSEL_REVIEW_RECORD.md";
  const controlRecord = control?.current_record ?? null;
  const confirmPhrase = control?.required_confirm_phrase ?? "RECORD QUALIFIED COUNSEL REVIEW";
  const counselHandoff = report?.counsel_review_handoff;
  const handoffDocs = counselHandoff?.package_documents ?? [];
  const handoffSteps = counselHandoff?.setup_steps ?? [];
  const handoffTemplate = counselHandoff?.record_template ?? [];
  const handoffDocsPresent = handoffDocs.filter((doc) => doc.present).length;
  const handoffRequiredFields = counselHandoff?.required_record_fields ?? [];

  return (
    <GlassPanel title="Legal Review Readiness" subtitle="Draft disclosures versus counsel-reviewed launch approval">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <StatusChip
          label={report?.status ?? "SYNCING"}
          variant={report?.status === "OK" ? "success" : report?.status === "ATTENTION" ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip
          label={report?.launch_legal_status ?? "WARMING"}
          variant={report?.launch_legal_status === "READY_FOR_PUBLIC_LAUNCH_LEGAL" ? "success" : report?.launch_legal_status === "BLOCK_PUBLIC_LAUNCH" ? "danger" : "muted"}
          size="sm"
        />
        <StatusChip label={`${report?.ok_count ?? 0} OK`} variant="success" size="sm" />
        <StatusChip
          label={`${attentionCount} ATTENTION`}
          variant={attentionCount ? "warning" : "success"}
          size="sm"
        />
        <StatusChip
          label={report?.counsel_review_accepted ? "COUNSEL ACCEPTED" : "COUNSEL RECORD MISSING"}
          variant={report?.counsel_review_accepted ? "success" : "danger"}
          size="sm"
        />
      </div>
      <div className="control-grid">
        <ControlField
          label="Counsel Record"
          value={recordPath}
          mono
          danger={!report?.counsel_review_accepted}
          description="Draft docs do not count as public-launch legal approval."
        />
        <ControlField
          label="Next Action"
          value={report?.next_action ?? "Legal review readiness report is warming."}
          danger={!report?.counsel_review_accepted}
        />
        <ControlField
          label="Checklist"
          value={report?.required_documents?.checklist ?? "docs/legal/CAS_FOREX_LEGAL_REVIEW_CHECKLIST.md"}
          mono
          description="Review intake only; not counsel approval."
        />
        <ControlField
          label="Boundary"
          value="READ ONLY"
          description="This panel does not provide legal advice or authorize public launch."
        />
        <ControlField
          label="Counsel Handoff"
          value={counselHandoff?.status ?? "SYNCING"}
          danger={counselHandoff?.status === "COUNSEL_REVIEW_REQUIRED"}
          description={counselHandoff?.claim_boundary ?? "Read-only package checklist for external counsel review."}
        />
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>Counsel Handoff</th>
              <th>Value</th>
              <th>Purpose</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Launch Status</td>
              <td className="mono">{counselHandoff?.launch_legal_status ?? report?.launch_legal_status ?? "WARMING"}</td>
              <td>Legal launch gate state from the counsel-review handoff.</td>
            </tr>
            <tr>
              <td>Package Docs</td>
              <td className="mono">{handoffDocs.length ? `${handoffDocsPresent}/${handoffDocs.length} present` : "warming"}</td>
              <td>{handoffDocs.slice(0, 3).map((doc) => doc.path).filter(Boolean).join(", ") || "Draft disclosure package and review record inventory."}</td>
            </tr>
            <tr>
              <td>Required Fields</td>
              <td className="mono">{handoffRequiredFields.slice(0, 4).join("; ") || "warming"}</td>
              <td>Minimum accepted-record fields for the external counsel review file.</td>
            </tr>
            <tr>
              <td>First Step</td>
              <td>{handoffSteps[0] ?? "Legal review handoff is warming."}</td>
              <td>Owner-facing next action before public launch can be called legally ready.</td>
            </tr>
            <tr>
              <td>Record Template</td>
              <td className="mono">{handoffTemplate.slice(0, 3).join("; ") || "warming"}</td>
              <td>Starter fields for `docs/legal/CAS_FOREX_COUNSEL_REVIEW_RECORD.md`.</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12, padding: 12 }}>
        <div className="field-label" style={{ marginBottom: 8 }}>Counsel Record Control</div>
        <div className="control-grid">
          <div className="control-field">
            <div className="field-label">Reviewed By</div>
            <input
              className="mobile-api-input"
              value={draft.reviewed_by}
              placeholder="Qualified counsel or firm"
              onChange={(event) => setDraft({ ...draft, reviewed_by: event.target.value })}
            />
          </div>
          <div className="control-field">
            <div className="field-label">Review Date</div>
            <input
              className="mobile-api-input"
              value={draft.review_date}
              placeholder="YYYY-MM-DD"
              onChange={(event) => setDraft({ ...draft, review_date: event.target.value })}
            />
          </div>
          <div className="control-field">
            <div className="field-label">Review Artifact Path</div>
            <input
              className="mobile-api-input"
              value={draft.review_artifact_path}
              placeholder="Local file path or external record path"
              onChange={(event) => setDraft({ ...draft, review_artifact_path: event.target.value })}
            />
          </div>
          <div className="control-field">
            <div className="field-label">Artifact SHA-256</div>
            <input
              className="mobile-api-input"
              value={draft.review_artifact_sha256}
              placeholder="Auto-computed if the local artifact file exists"
              onChange={(event) => setDraft({ ...draft, review_artifact_sha256: event.target.value })}
            />
            <div className="control-field-desc" style={{ marginTop: 6 }}>
              {controlRecord?.artifact_path_exists_locally
                ? "Current artifact path resolves locally."
                : "If the artifact is not a readable local file, paste the external artifact hash explicitly."}
            </div>
          </div>
          <div className="control-field">
            <div className="field-label">Matter Reference</div>
            <input
              className="mobile-api-input"
              value={draft.matter_reference}
              placeholder="Optional internal/legal matter id"
              onChange={(event) => setDraft({ ...draft, matter_reference: event.target.value })}
            />
          </div>
          <div className="control-field">
            <div className="field-label">Jurisdictions</div>
            <input
              className="mobile-api-input"
              value={draft.jurisdictions}
              placeholder="Optional jurisdiction list"
              onChange={(event) => setDraft({ ...draft, jurisdictions: event.target.value })}
            />
          </div>
        </div>
        <div className="control-field" style={{ marginTop: 12 }}>
          <div className="field-label">Scope</div>
          <textarea
            className="mobile-api-input broker-reality-textarea"
            value={draft.scope}
            onChange={(event) => setDraft({ ...draft, scope: event.target.value })}
          />
        </div>
        <div className="control-field" style={{ marginTop: 12 }}>
          <div className="field-label">Notes</div>
          <textarea
            className="mobile-api-input broker-reality-textarea"
            value={draft.notes}
            onChange={(event) => setDraft({ ...draft, notes: event.target.value })}
          />
        </div>
        <label className="control-field-desc" style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 10 }}>
          <input
            type="checkbox"
            checked={draft.qualified_counsel_confirmed}
            onChange={(event) => setDraft({ ...draft, qualified_counsel_confirmed: event.target.checked })}
          />
          Qualified counsel has actually reviewed this scope outside the app.
        </label>
        <div className="control-field" style={{ marginTop: 10 }}>
          <div className="field-label">Typed Confirmation</div>
          <input
            className="mobile-api-input"
            value={draft.confirm_phrase}
            placeholder={confirmPhrase}
            onChange={(event) => setDraft({ ...draft, confirm_phrase: event.target.value })}
          />
        </div>
        <div className="mobile-api-row" style={{ marginTop: 10 }}>
          <button className="mobile-api-button" type="button" disabled={busy} onClick={() => void saveCounselReviewRecord()}>
            {busy ? "Saving..." : "Record counsel review"}
          </button>
          <button className="mobile-api-button ghost" type="button" disabled={busy} onClick={() => void resetCounselReviewRecord()}>
            Reset record
          </button>
          <button className="mobile-api-button ghost" type="button" disabled={busy} onClick={() => void refresh()}>
            Refresh legal readiness
          </button>
        </div>
        <div className="control-field-desc" style={{ marginTop: 8 }}>
          This stores metadata about an external review artifact. It does not turn draft disclosures into legal advice or self-create launch approval.
        </div>
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>Check</th>
              <th>Status</th>
              <th>Detail</th>
              <th>Evidence</th>
              <th>Next</th>
            </tr>
          </thead>
          <tbody>
            {displayChecks.map((check) => {
              const evidence = (check.evidence ?? [])
                .slice(0, 4)
                .map((item) => {
                  const label = item.path ?? item.term ?? item.label ?? item.key ?? "evidence";
                  const present = item.present === true ? "ok" : item.present === false ? "missing" : "seen";
                  return `${String(label)}:${present}`;
                })
                .join(", ");
              const missing = [
                ...(check.missing_paths ?? []),
                ...(check.missing_terms ?? []),
              ].slice(0, 4).join(", ");
              return (
                <tr key={check.key ?? check.label ?? "legal-check"}>
                  <td>{check.label ?? check.key ?? "Legal check"}</td>
                  <td>
                    <StatusChip
                      label={check.status ?? "UNKNOWN"}
                      variant={check.status === "OK" ? "success" : check.status === "MISSING" ? "danger" : "warning"}
                      size="sm"
                    />
                  </td>
                  <td>{check.detail ?? ""}</td>
                  <td className="mono">{evidence || "none"}</td>
                  <td>{missing || check.next_action || "Keep covered."}</td>
                </tr>
              );
            })}
            {displayChecks.length === 0 && (
              <tr>
                <td colSpan={5}>Legal review readiness is warming.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="mobile-api-row" style={{ marginTop: 10 }}>
        <button className="mobile-api-button ghost" type="button" onClick={() => void refresh()}>Refresh legal readiness</button>
      </div>
      {status && (
        <div
          className="control-field-desc"
          style={{
            color:
              status.toLowerCase().includes("failed")
              || status.toLowerCase().includes("required")
              || status.toLowerCase().includes("unavailable")
                ? "var(--danger)"
                : "var(--warning)",
            marginTop: 8,
          }}
        >
          {status}
        </div>
      )}
      <div className="control-field-desc" style={{ marginTop: 10 }}>
        {report?.claim_boundary ?? "Legal review readiness is read-only and does not authorize trading, public launch, or money movement."}
      </div>
    </GlassPanel>
  );
}


export function OperationalReadinessPanel() {
  const [report, setReport] = useState<OperationalReadinessReport | null>(null);
  const [backupBusy, setBackupBusy] = useState(false);
  const [backupStatus, setBackupStatus] = useState("");
  const [monitoringBusy, setMonitoringBusy] = useState(false);
  const [monitoringStatus, setMonitoringStatus] = useState("");
  const [uptimeMonitorUrl, setUptimeMonitorUrl] = useState("");
  const [errorTrackingDsn, setErrorTrackingDsn] = useState("");
  const [alertWebhookUrl, setAlertWebhookUrl] = useState("");

  useEffect(() => {
    void refreshReadiness();
  }, []);

  async function refreshReadiness() {
    const next = await fetchOperationalReadiness();
    if (next) setReport(next);
  }

  async function createBackup() {
    setBackupBusy(true);
    setBackupStatus("");
    try {
      const result = await createOperatorBackup();
      if (result.operational_readiness) {
        setReport(result.operational_readiness);
      } else {
        await refreshReadiness();
      }
      const manifest = result.manifest ?? {};
      const snapshotId = typeof manifest.snapshot_id === "string" ? manifest.snapshot_id : "snapshot";
      setBackupStatus(result.status === "CREATED" ? `Backup created: ${snapshotId}.` : "Backup finished without a usable snapshot.");
    } catch {
      setBackupStatus("Backup request failed - check API reachability and runtime/backups permissions.");
    } finally {
      setBackupBusy(false);
    }
  }

  const checks = report?.checks ?? [];
  const backupInventory = report?.backup_inventory;
  const latestBackup = backupInventory?.latest_snapshot ?? null;
  const latestBackupAt = typeof latestBackup?.created_at_iso === "string" ? latestBackup.created_at_iso : "none";
  const latestBackupFiles = typeof latestBackup?.file_count === "number" ? String(latestBackup.file_count) : "0";
  const attention = report?.attention_items ?? [];
  const externalMonitoring = report?.external_monitoring;
  const externalChecks = externalMonitoring?.checks ?? [];
  const uptimeCheck = externalChecks.find((check) => check.key === "external_uptime_monitor");
  const errorCheck = externalChecks.find((check) => check.key === "error_tracking_dsn");
  const alertCheck = externalChecks.find((check) => check.key === "offscreen_alert_destination");
  const monitoringHandoff = externalMonitoring?.deployment_handoff;
  const handoffEndpoints = monitoringHandoff?.health_endpoints ?? externalMonitoring?.health_endpoints ?? [];
  const handoffCommands = monitoringHandoff?.verification_commands ?? [];
  const handoffSteps = monitoringHandoff?.setup_steps ?? [];

  async function saveExternalMonitoring() {
    const patch: { uptime_monitor_url?: string; error_tracking_dsn?: string; alert_webhook_url?: string } = {};
    if (uptimeMonitorUrl.trim()) patch.uptime_monitor_url = uptimeMonitorUrl.trim();
    if (errorTrackingDsn.trim()) patch.error_tracking_dsn = errorTrackingDsn.trim();
    if (alertWebhookUrl.trim()) patch.alert_webhook_url = alertWebhookUrl.trim();
    if (!patch.uptime_monitor_url && !patch.error_tracking_dsn && !patch.alert_webhook_url) {
      setMonitoringStatus("Paste at least one uptime, error-tracking, or off-screen alert value before saving.");
      return;
    }
    setMonitoringBusy(true);
    setMonitoringStatus("");
    try {
      const result = await updateExternalMonitoringConfig(patch);
      if (result.operational_readiness) {
        setReport(result.operational_readiness);
      } else {
        await refreshReadiness();
      }
      setUptimeMonitorUrl("");
      setErrorTrackingDsn("");
      setAlertWebhookUrl("");
      setMonitoringStatus(
        result.status === "UPDATED"
          ? `Saved external hooks: ${(result.applied_keys ?? []).join(", ") || "updated"}.`
          : "No external monitoring change was applied.",
      );
    } catch {
      setMonitoringStatus("External monitoring save failed - check owner access and API reachability.");
    } finally {
      setMonitoringBusy(false);
    }
  }

  async function resetExternalMonitoring() {
    setMonitoringBusy(true);
    setMonitoringStatus("");
    try {
      const result = await resetExternalMonitoringConfig();
      if (result.operational_readiness) {
        setReport(result.operational_readiness);
      } else {
        await refreshReadiness();
      }
      setUptimeMonitorUrl("");
      setErrorTrackingDsn("");
      setAlertWebhookUrl("");
      setMonitoringStatus(
        `Reset local external monitoring hooks: ${(result.applied_keys ?? []).join(", ") || "no runtime overrides were set"}.`,
      );
    } catch {
      setMonitoringStatus("External monitoring reset failed - check owner access and API reachability.");
    } finally {
      setMonitoringBusy(false);
    }
  }

  return (
    <GlassPanel title="Operational Readiness" subtitle="Health, logs, backups, runbooks, build, rollback, and external monitoring evidence">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <StatusChip
          label={report?.status ?? "SYNCING"}
          variant={report?.status === "OK" ? "success" : report?.status === "ATTENTION" ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip
          label={`${report?.ok_count ?? 0} OK`}
          variant="success"
          size="sm"
        />
        <StatusChip
          label={`${report?.attention_count ?? 0} ATTENTION`}
          variant={(report?.attention_count ?? 0) ? "warning" : "success"}
          size="sm"
        />
        <StatusChip
          label={`${backupInventory?.snapshot_count ?? 0} BACKUPS`}
          variant={(backupInventory?.snapshot_count ?? 0) ? "success" : "warning"}
          size="sm"
        />
        <StatusChip
          label={`EXT MON ${externalMonitoring?.status ?? "SYNCING"}`}
          variant={externalMonitoring?.status === "OK" ? "success" : externalMonitoring?.status === "ATTENTION" ? "warning" : "muted"}
          size="sm"
        />
      </div>
      <div className="control-grid">
        <ControlField label="Runbook" value={report?.runbook_path ?? "docs/operations/CAS_FOREX_OPERATIONS_RUNBOOK.md"} mono description="Local operating procedure for health, logs, backup, restore, rollback, and build preview." />
        <ControlField label="Latest Backup" value={latestBackupAt} mono danger={!latestBackup} description={`${latestBackupFiles} file(s) captured in latest operator-state snapshot.`} />
        <ControlField
          label="External Monitoring"
          value={externalMonitoring?.status ?? "SYNCING"}
          danger={externalMonitoring?.status === "ATTENTION"}
          description={externalMonitoring?.next_action ?? "Configure uptime monitor, error tracking, and off-screen alerts before hosted production."}
        />
        <ControlField label="Boundary" value="READ ONLY" description="This panel reports operations evidence; it does not restart processes or touch trades." />
        <ControlField
          label="Deployment Handoff"
          value={monitoringHandoff?.status ?? "SYNCING"}
          danger={monitoringHandoff?.status === "ACTION_REQUIRED"}
          description={monitoringHandoff?.claim_boundary ?? "Read-only hosted-monitoring checklist for uptime, error tracking, and alert delivery."}
        />
      </div>
      <div className="mobile-api-row" style={{ marginTop: 12 }}>
        <button className="mobile-api-button" type="button" disabled={backupBusy} onClick={() => void createBackup()}>
          {backupBusy ? "Creating backup..." : "Create operator backup"}
        </button>
        <button className="mobile-api-button ghost" type="button" disabled={backupBusy} onClick={() => void refreshReadiness()}>
          Refresh readiness
        </button>
      </div>
      {backupStatus && (
        <div className="control-field-desc" style={{ marginTop: 8, color: backupStatus.includes("failed") ? "var(--danger)" : "var(--success)" }}>
          {backupStatus}
        </div>
      )}
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>Check</th>
              <th>Status</th>
              <th>Detail</th>
              <th>Missing</th>
            </tr>
          </thead>
          <tbody>
            {checks.map((check) => (
              <tr key={check.key ?? check.label}>
                <td>{check.label ?? check.key}</td>
                <td>
                  <StatusChip
                    label={check.status ?? "UNKNOWN"}
                    variant={check.status === "OK" ? "success" : "warning"}
                    size="sm"
                  />
                </td>
                <td>{check.detail ?? ""}</td>
                <td className="mono">{[...(check.missing_paths ?? []), ...(check.missing_terms ?? [])].join(", ") || "none"}</td>
              </tr>
            ))}
            {checks.length === 0 && (
              <tr>
                <td colSpan={4}>Operational readiness is warming.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {attention.length > 0 && (
        <div className="control-field-desc" style={{ marginTop: 8, color: "var(--warning)" }}>
          {attention.slice(0, 3).join(" ")}
        </div>
      )}
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>Hosted Handoff</th>
              <th>Value</th>
              <th>Purpose</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Owner UI</td>
              <td className="mono">{monitoringHandoff?.owner_ui_path ?? "?page=settings"}</td>
              <td>Configure runtime hooks without editing environment files.</td>
            </tr>
            <tr>
              <td>Public Base</td>
              <td className="mono">{monitoringHandoff?.public_base_url_placeholder ?? "https://your-cas-forex-host"}</td>
              <td>Replace this placeholder with the hosted HTTPS origin.</td>
            </tr>
            <tr>
              <td>Health Endpoints</td>
              <td className="mono">{handoffEndpoints.join(", ") || "loading"}</td>
              <td>Point uptime monitors at one of these read-only routes.</td>
            </tr>
            <tr>
              <td>Verify</td>
              <td className="mono">{handoffCommands.slice(0, 2).join(" | ") || "loading"}</td>
              <td>Commands to confirm hosted health endpoints answer.</td>
            </tr>
            <tr>
              <td>Next Step</td>
              <td>{handoffSteps[0] ?? externalMonitoring?.next_action ?? "Refresh readiness."}</td>
              <td>First deployment action for the current state.</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>External Hook</th>
              <th>Status</th>
              <th>Configured</th>
              <th>Detail</th>
            </tr>
          </thead>
          <tbody>
            {externalChecks.map((check) => (
              <tr key={check.key ?? check.label ?? "external-monitoring"}>
                <td>{check.label ?? check.key}</td>
                <td>
                  <StatusChip
                    label={check.status ?? "UNKNOWN"}
                    variant={check.status === "OK" ? "success" : check.status === "MISSING" ? "danger" : "warning"}
                    size="sm"
                  />
                </td>
                <td className="mono">{check.configured_key ? `${check.configured_key} ${check.masked_value ?? ""}` : "not configured"}</td>
                <td>{check.detail ?? ""}</td>
              </tr>
            ))}
            {externalChecks.length === 0 && (
              <tr>
                <td colSpan={4}>External monitoring readiness is warming.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="control-grid" style={{ marginTop: 12 }}>
        <ControlField
          label="Uptime Hook Source"
          value={uptimeCheck?.configured_key ?? "not configured"}
          mono
          description={uptimeCheck?.masked_value ?? uptimeCheck?.detail ?? "No hosted heartbeat URL is configured yet."}
          danger={uptimeCheck?.status !== "OK"}
        />
        <ControlField
          label="Error Tracking Source"
          value={errorCheck?.configured_key ?? "not configured"}
          mono
          description={errorCheck?.masked_value ?? errorCheck?.detail ?? "No external error-tracking DSN is configured yet."}
          danger={errorCheck?.status !== "OK"}
        />
        <ControlField
          label="Alert Destinations"
          value={
            alertCheck?.configured_key ?? "not configured"
          }
          mono
          description={alertCheck?.masked_value ?? "Webhook destinations can be registered below; env-based alert URLs also count."}
          danger={alertCheck?.status !== "OK"}
        />
        <ControlField
          label="Update Scope"
          value="OWNER RUNTIME"
          description="These writes update local uptime, error-tracking, and alert hooks only. They do not ping external services or affect trades."
        />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 10, marginTop: 12 }}>
        <input
          type="text"
          className="mobile-api-input"
          placeholder="Hosted uptime heartbeat URL"
          value={uptimeMonitorUrl}
          onChange={(e) => setUptimeMonitorUrl(e.target.value)}
          spellCheck={false}
        />
        <input
          type="text"
          className="mobile-api-input"
          placeholder="External error-tracking DSN"
          value={errorTrackingDsn}
          onChange={(e) => setErrorTrackingDsn(e.target.value)}
          spellCheck={false}
        />
        <input
          type="text"
          className="mobile-api-input"
          placeholder="Off-screen alert webhook URL"
          value={alertWebhookUrl}
          onChange={(e) => setAlertWebhookUrl(e.target.value)}
          spellCheck={false}
        />
      </div>
      <div className="mobile-api-row" style={{ marginTop: 12 }}>
        <button className="mobile-api-button" type="button" disabled={monitoringBusy} onClick={() => void saveExternalMonitoring()}>
          {monitoringBusy ? "Saving hooks..." : "Save external hooks"}
        </button>
        <button className="mobile-api-button ghost" type="button" disabled={monitoringBusy} onClick={() => void resetExternalMonitoring()}>
          Reset runtime hooks
        </button>
      </div>
      {monitoringStatus && (
        <div className="control-field-desc" style={{ marginTop: 8, color: monitoringStatus.includes("failed") ? "var(--danger)" : "var(--muted-text)" }}>
          {monitoringStatus}
        </div>
      )}
      <div className="control-field-desc" style={{ marginTop: 10 }}>
        {report?.claim_boundary ?? "Operational readiness is read-only and does not authorize trading or money movement."}
      </div>
    </GlassPanel>
  );
}


export function EmergencyControlsPanel() {
  const [report, setReport] = useState<EmergencyControlsReport | null>(null);
  const [brokerEmergency, setBrokerEmergency] = useState<BrokerEmergencyActionResult | null>(null);
  const [ownerConfirmBrokerEmergency, setOwnerConfirmBrokerEmergency] = useState(false);
  const [brokerEmergencyBusy, setBrokerEmergencyBusy] = useState("");
  const [brokerEmergencyMessage, setBrokerEmergencyMessage] = useState("");

  useEffect(() => {
    void fetchEmergencyControls().then((s) => { if (s) setReport(s); });
    void fetchBrokerEmergencyStatus().then((s) => { if (s) setBrokerEmergency(s); });
  }, []);

  async function runBrokerEmergency(
    endpoint: "close-all" | "close-profitable" | "close-losing" | "cancel-pending",
    dryRun: boolean,
  ) {
    let confirmPhrase = "";
    if (!dryRun) {
      if (!ownerConfirmBrokerEmergency) {
        setBrokerEmergencyMessage("OWNER_BROKER_EMERGENCY_CONFIRM_REQUIRED");
        return;
      }
      const typed = window.prompt('Type exactly "CONFIRM BROKER EMERGENCY" to execute this broker emergency action.', "");
      if (typed === null) {
        setBrokerEmergencyMessage("Broker emergency confirmation canceled.");
        return;
      }
      confirmPhrase = typed;
    }
    const busyKey = `${endpoint}:${dryRun ? "dry" : "confirm"}`;
    setBrokerEmergencyBusy(busyKey);
    setBrokerEmergencyMessage("");
    try {
      const result = await runBrokerEmergencyAction(endpoint, {
        reason: dryRun ? "OWNER_DRY_RUN_BROKER_EMERGENCY" : "OWNER_CONFIRMED_BROKER_EMERGENCY",
        dryRun,
        confirmOwnerAction: !dryRun && ownerConfirmBrokerEmergency,
        confirmPhrase,
      });
      setBrokerEmergency(result);
      setBrokerEmergencyMessage(
        result.status === "CONFIRM_REQUIRED"
          ? `Type exactly "${result.need_confirmation ?? "CONFIRM BROKER EMERGENCY"}" to execute this broker emergency action.`
          : `${result.status ?? "UNKNOWN"}: ${result.next_action ?? "Broker emergency action returned."}`,
      );
    } catch {
      setBrokerEmergencyMessage(
        "Broker emergency request failed before execution confirmation. No broker emergency action was confirmed through this app; check API reachability and MT5 terminal state.",
      );
    } finally {
      setBrokerEmergencyBusy("");
    }
  }

  const controls = report?.controls ?? [];
  const brokerControls = controls.filter((control) => control.category === "broker_exposure");
  const missingBrokerControls = brokerControls.filter((control) => control.status !== "OK");
  const attention = report?.attention_items ?? [];
  const terminalActions = report?.recommended_terminal_actions ?? [];

  return (
    <GlassPanel title="Emergency Controls Coverage" subtitle="What the app stops, and what still requires broker-terminal action">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <StatusChip
          label={report?.status ?? "SYNCING"}
          variant={report?.status === "OK" ? "success" : report?.status === "ATTENTION" ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip
          label={report?.automation_stop_ok ? "AUTOMATION STOP WIRED" : "AUTOMATION STOP CHECKING"}
          variant={report?.automation_stop_ok ? "success" : "warning"}
          size="sm"
        />
        <StatusChip
          label={report?.broker_exposure_gap ? "BROKER FLATTEN GAP" : "BROKER FLATTEN WIRED"}
          variant={report?.broker_exposure_gap ? "warning" : "success"}
          size="sm"
        />
        <StatusChip
          label={`${report?.attention_count ?? 0} ATTENTION`}
          variant={(report?.attention_count ?? 0) ? "warning" : "success"}
          size="sm"
        />
      </div>
      <div className="control-grid">
        <ControlField
          label="Stop Scope"
          value={report?.automation_stop_ok ? "NEW AUTOMATION" : "CHECKING"}
          danger={!report?.automation_stop_ok}
          description={report?.automation_stop_scope ?? "Loading emergency-stop scope."}
        />
        <ControlField
          label="Broker Exposure"
          value={missingBrokerControls.length ? "TERMINAL REQUIRED" : "APP ROUTED"}
          danger={missingBrokerControls.length > 0}
          description={missingBrokerControls.length ? "Existing open positions and pending orders need MT4/MT5 terminal action until a tested app route exists." : "Broker exposure controls are wired in-app."}
        />
        <ControlField
          label="Missing Broker Controls"
          value={String(missingBrokerControls.length)}
          mono
          danger={missingBrokerControls.length > 0}
          description="Close-all, cancel-pending, and selective close controls must be explicit and audited."
        />
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>Control</th>
              <th>Status</th>
              <th>Route / Surface</th>
              <th>Effect</th>
              <th>Money Impact</th>
            </tr>
          </thead>
          <tbody>
            {controls.map((control: EmergencyControlRow) => (
              <tr key={control.key ?? control.label}>
                <td>{control.label ?? control.key}</td>
                <td>
                  <StatusChip
                    label={control.status ?? "UNKNOWN"}
                    variant={emergencyControlVariant(control.status)}
                    size="sm"
                  />
                </td>
                <td>
                  <div className="mono">{control.route ?? "manual terminal"}</div>
                  <div className="control-field-desc">{control.surface ?? ""}</div>
                </td>
                <td>{control.status === "OK" ? control.effect : (control.missing_detail || control.effect || "")}</td>
                <td>{control.money_impact ?? ""}</td>
              </tr>
            ))}
            {controls.length === 0 && (
              <tr>
                <td colSpan={5}>Emergency controls coverage is warming.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {terminalActions.length > 0 && (
        <div className="control-field-desc" style={{ marginTop: 8 }}>
          {terminalActions.slice(0, 3).join(" ")}
        </div>
      )}
      <div className="control-section" style={{ marginTop: 12 }}>
        <h4 className="control-section-title">Broker Emergency Actions</h4>
        <div className="control-grid">
          <ControlField label="MT5 Connected" value={brokerEmergency?.mt5_connected ? "YES" : "NO"} danger={!brokerEmergency?.mt5_connected} />
          <ControlField label="Open Positions" value={String(brokerEmergency?.open_position_count ?? 0)} mono />
          <ControlField label="Pending Orders" value={String(brokerEmergency?.pending_order_count ?? 0)} mono />
          <ControlField label="Last Action" value={brokerEmergency?.status ?? "NOT RUN"} description={brokerEmergency?.next_action ?? "Dry-run before any confirmed broker emergency action."} danger={brokerEmergency?.status === "PARTIAL" || brokerEmergency?.status === "MT5_NOT_CONNECTED"} />
        </div>
        <div className="mobile-api-row" style={{ marginTop: 10 }}>
          <button className="mobile-api-button ghost" type="button" disabled={Boolean(brokerEmergencyBusy)} onClick={() => void runBrokerEmergency("close-all", true)}>
            {brokerEmergencyBusy === "close-all:dry" ? "Checking..." : "Dry-run close all"}
          </button>
          <button className="mobile-api-button ghost" type="button" disabled={Boolean(brokerEmergencyBusy)} onClick={() => void runBrokerEmergency("close-profitable", true)}>
            {brokerEmergencyBusy === "close-profitable:dry" ? "Checking..." : "Dry-run close profitable"}
          </button>
          <button className="mobile-api-button ghost" type="button" disabled={Boolean(brokerEmergencyBusy)} onClick={() => void runBrokerEmergency("close-losing", true)}>
            {brokerEmergencyBusy === "close-losing:dry" ? "Checking..." : "Dry-run close losing"}
          </button>
          <button className="mobile-api-button ghost" type="button" disabled={Boolean(brokerEmergencyBusy)} onClick={() => void runBrokerEmergency("cancel-pending", true)}>
            {brokerEmergencyBusy === "cancel-pending:dry" ? "Checking..." : "Dry-run cancel pending"}
          </button>
          <label className="sweep-confirm-check">
            <input
              type="checkbox"
              checked={ownerConfirmBrokerEmergency}
              onChange={(event) => setOwnerConfirmBrokerEmergency(event.target.checked)}
            />
            <span>Owner Confirm Broker Action</span>
          </label>
          <button
            className="mobile-api-button"
            type="button"
            disabled={Boolean(brokerEmergencyBusy) || !ownerConfirmBrokerEmergency}
            onClick={() => void runBrokerEmergency("close-all", false)}
            title="Submits MT5 close orders for selected open positions after owner confirmation"
          >
            {brokerEmergencyBusy === "close-all:confirm" ? "Closing..." : "Close all positions"}
          </button>
          <button
            className="mobile-api-button"
            type="button"
            disabled={Boolean(brokerEmergencyBusy) || !ownerConfirmBrokerEmergency}
            onClick={() => void runBrokerEmergency("close-profitable", false)}
            title="Submits MT5 close orders only for currently profitable open positions after owner confirmation"
          >
            {brokerEmergencyBusy === "close-profitable:confirm" ? "Closing..." : "Close profitable positions"}
          </button>
          <button
            className="mobile-api-button"
            type="button"
            disabled={Boolean(brokerEmergencyBusy) || !ownerConfirmBrokerEmergency}
            onClick={() => void runBrokerEmergency("close-losing", false)}
            title="Submits MT5 close orders only for currently losing open positions after owner confirmation"
          >
            {brokerEmergencyBusy === "close-losing:confirm" ? "Closing..." : "Close losing positions"}
          </button>
          <button
            className="mobile-api-button"
            type="button"
            disabled={Boolean(brokerEmergencyBusy) || !ownerConfirmBrokerEmergency}
            onClick={() => void runBrokerEmergency("cancel-pending", false)}
            title="Submits MT5 pending-order cancel requests after owner confirmation"
          >
            {brokerEmergencyBusy === "cancel-pending:confirm" ? "Cancelling..." : "Cancel pending orders"}
          </button>
        </div>
        {brokerEmergencyMessage && (
          <div className="control-field-desc" style={{ marginTop: 8, color: brokerEmergencyMessage.includes("failed") ? "var(--danger)" : "var(--text-secondary)" }}>
            {brokerEmergencyMessage}
          </div>
        )}
      </div>
      {attention.length > 0 && (
        <div className="control-field-desc" style={{ marginTop: 8, color: "var(--warning)" }}>
          {attention.slice(0, 3).join(" ")}
        </div>
      )}
      <div className="control-field-desc" style={{ marginTop: 10 }}>
        {report?.claim_boundary ?? "Emergency controls coverage is read-only and does not touch trades or money."}
      </div>
    </GlassPanel>
  );
}



export function emergencyControlVariant(status?: string) {
  if (status === "OK") return "success" as const;
  if (status === "WARMING" || status === "SYNCING") return "muted" as const;
  return "warning" as const;
}


export function LegalGate({ label, met, detail }: { label: string; met: boolean; detail: string }) {
  return (
    <div className="legal-gate-item">
      <div className="legal-gate-header">
        <span className="check-icon" style={{ color: met ? "var(--success)" : "var(--danger)" }}>{met ? "✓" : "✗"}</span>
        <span className="field-label">{label}</span>
        <StatusChip label={met ? "MET" : "NOT MET"} variant={met ? "success" : "danger"} size="sm" />
      </div>
      <div className="legal-gate-detail">{detail}</div>
    </div>
  );
}
