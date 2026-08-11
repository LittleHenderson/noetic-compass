/* Extracted from pages/SettingsPage.tsx (settings decomposition, slice 1). */

import { GlassPanel } from "../../components/GlassPanel";
import { StatusChip } from "../../components/StatusChip";
import { BypassLaunchGateReport, PublicLaunchGateReport, fetchBypassLaunchGate, fetchPublicLaunchGate } from "../../data/api";
import { ControlField } from "./ControlField";
import { useEffect, useState } from "react";

export function PublicLaunchGatePanel() {
  const [report, setReport] = useState<PublicLaunchGateReport | null>(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    setStatus("");
    const next = await fetchPublicLaunchGate();
    if (next) {
      setReport(next);
    } else {
      setStatus("Public launch gate unavailable - is the API reachable?");
    }
  }

  const gates = report?.gates ?? [];
  const blockedGates = gates.filter((gate) => gate.status !== "PASS");
  const displayGates = [...blockedGates, ...gates.filter((gate) => gate.status === "PASS")];
  const blockCount = report?.hard_blocker_count ?? report?.block_count ?? blockedGates.length;

  return (
    <GlassPanel title="Public Launch Gate" subtitle="One aggregate pass/block decision for public, hosted, paid, multi-user, and live-production use">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <StatusChip
          label={report?.launch_gate_status ?? "SYNCING"}
          variant={report?.launch_gate_status === "PASS" ? "success" : report?.launch_gate_status === "BLOCK_PUBLIC_LAUNCH" ? "danger" : "muted"}
          size="sm"
        />
        <StatusChip
          label={`PUBLIC ${report?.public_launch_status ?? "WARMING"}`}
          variant={report?.public_launch_status === "READY" ? "success" : report?.public_launch_status === "BLOCKED" ? "danger" : "muted"}
          size="sm"
        />
        <StatusChip
          label={`LIVE PROD ${report?.live_money_production_status ?? "WARMING"}`}
          variant={report?.live_money_production_status === "READY" ? "success" : report?.live_money_production_status === "BLOCKED" ? "danger" : "muted"}
          size="sm"
        />
        <StatusChip label={`${report?.pass_count ?? 0} PASS`} variant="success" size="sm" />
        <StatusChip label={`${blockCount} BLOCK`} variant={blockCount ? "danger" : "success"} size="sm" />
      </div>
      <div className="control-grid">
        <ControlField
          label="Release Policy"
          value={report?.release_policy ?? "Treat warming or blocked gates as not ready for public/live production."}
          danger={blockCount > 0}
          description="Local paper/demo development can continue under normal owner-controlled gates."
        />
        <ControlField
          label="Next Action"
          value={report?.next_action ?? "Public launch gate is warming."}
          danger={blockCount > 0}
        />
        <ControlField
          label="Top Blocker"
          value={report?.hard_blockers?.[0] ?? "No aggregate blocker loaded."}
          danger={blockCount > 0}
        />
        <ControlField
          label="Boundary"
          value="READ ONLY"
          description="This aggregate does not authorize launch, live trading, or money movement."
        />
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>Gate</th>
              <th>Status</th>
              <th>Source</th>
              <th>Detail</th>
              <th>Evidence</th>
              <th>Next</th>
            </tr>
          </thead>
          <tbody>
            {displayGates.map((gate) => (
              <tr key={gate.key ?? gate.label ?? "launch-gate"}>
                <td>{gate.label ?? gate.key ?? "Launch gate"}</td>
                <td>
                  <StatusChip
                    label={gate.status ?? "UNKNOWN"}
                    variant={gate.status === "PASS" ? "success" : "danger"}
                    size="sm"
                  />
                </td>
                <td className="mono">{gate.source_report_kind ?? gate.source_status ?? "unknown"}</td>
                <td>{gate.detail ?? ""}</td>
                <td className="mono">{formatPublicLaunchGateEvidence(gate.evidence)}</td>
                <td>{gate.next_action ?? ""}</td>
              </tr>
            ))}
            {displayGates.length === 0 && (
              <tr>
                <td colSpan={6}>Public launch gate is warming.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="mobile-api-row" style={{ marginTop: 10 }}>
        <button className="mobile-api-button ghost" type="button" onClick={() => void refresh()}>Refresh launch gate</button>
      </div>
      {status && <div className="control-field-desc" style={{ color: "var(--danger)", marginTop: 8 }}>{status}</div>}
      <div className="control-field-desc" style={{ marginTop: 10 }}>
        {report?.claim_boundary ?? "Public launch gate is read-only and fails closed until all hard gates pass."}
      </div>
    </GlassPanel>
  );
}


export function formatPublicLaunchGateEvidence(evidence: Record<string, unknown> | undefined): string {
  const entries = Object.entries(evidence ?? {}).slice(0, 4);
  if (!entries.length) return "none";
  return entries.map(([key, value]) => `${key}: ${formatEvidenceValue(value)}`).join(", ");
}


export function formatEvidenceValue(value: unknown): string {
  if (Array.isArray(value)) return `${value.length} item(s)`;
  if (value && typeof value === "object") return `${Object.keys(value as Record<string, unknown>).length} field(s)`;
  if (value === null || value === undefined || value === "") return "none";
  return String(value);
}


export function BypassLaunchGatePanel() {
  const [report, setReport] = useState<BypassLaunchGateReport | null>(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    setStatus("");
    const next = await fetchBypassLaunchGate();
    if (next) {
      setReport(next);
    } else {
      setStatus("Bypass launch gate unavailable - is the API reachable?");
    }
  }

  const checks = report?.checks ?? [];
  const attentionChecks = checks.filter((check) => check.status !== "OK");
  const displayChecks = [...attentionChecks, ...checks.filter((check) => check.status === "OK")];
  const attentionCount = report?.attention_count ?? attentionChecks.length;

  return (
    <GlassPanel title="Bypass Launch Gate" subtitle="No-bypass invariants for dispatch, live authority, and money movement">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <StatusChip
          label={report?.status ?? "SYNCING"}
          variant={report?.status === "OK" ? "success" : report?.status === "ATTENTION" ? "danger" : "muted"}
          size="sm"
        />
        <StatusChip
          label={report?.launch_gate_status ?? "WARMING"}
          variant={report?.launch_gate_status === "PASS" ? "success" : report?.launch_gate_status === "BLOCK_RELEASE" ? "danger" : "muted"}
          size="sm"
        />
        <StatusChip label={`${report?.ok_count ?? 0} OK`} variant="success" size="sm" />
        <StatusChip
          label={`${attentionCount} ATTENTION`}
          variant={attentionCount ? "danger" : "success"}
          size="sm"
        />
        <StatusChip label={`${report?.check_count ?? 0} CHECKS`} variant="muted" size="sm" />
      </div>
      <div className="control-grid">
        <ControlField
          label="Release Policy"
          value={report?.release_policy ?? "Treat no-bypass attention as a release blocker."}
          danger={attentionCount > 0}
          description="This gate is static evidence; it does not execute test commands from the browser."
        />
        <ControlField
          label="Top Attention"
          value={report?.top_attention_items?.[0] ?? "No no-bypass attention items loaded."}
          danger={attentionCount > 0}
        />
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>Check</th>
              <th>Status</th>
              <th>Invariant</th>
              <th>Evidence</th>
              <th>Attention</th>
            </tr>
          </thead>
          <tbody>
            {displayChecks.map((check) => {
              const missing = check.missing_evidence_refs?.length
                ? `missing: ${check.missing_evidence_refs.join(", ")}`
                : "";
              const missingTerms = check.missing_required_terms?.length
                ? `terms: ${check.missing_required_terms.length}`
                : "";
              const forbidden = check.forbidden_term_hits?.length
                ? `forbidden: ${check.forbidden_term_hits.length}`
                : "";
              const attention = [missing, missingTerms, forbidden].filter(Boolean).join(" | ");
              return (
                <tr key={check.check_id ?? check.invariant ?? "bypass-check"}>
                  <td className="mono">{check.check_id ?? "bypass_check"}</td>
                  <td>
                    <StatusChip
                      label={check.status ?? "UNKNOWN"}
                      variant={check.status === "OK" ? "success" : check.status === "ATTENTION" ? "danger" : "muted"}
                      size="sm"
                    />
                  </td>
                  <td>{check.invariant ?? ""}</td>
                  <td className="mono">{(check.present_evidence_refs ?? check.evidence_refs ?? []).slice(0, 3).join(", ") || "none"}</td>
                  <td>{attention || check.next_action || "Keep covered."}</td>
                </tr>
              );
            })}
            {displayChecks.length === 0 && (
              <tr>
                <td colSpan={5}>Bypass launch gate is warming.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="mobile-api-row" style={{ marginTop: 10 }}>
        <button className="mobile-api-button ghost" type="button" onClick={() => void refresh()}>Refresh bypass gate</button>
      </div>
      {status && <div className="control-field-desc" style={{ color: "var(--danger)", marginTop: 8 }}>{status}</div>}
      <div className="control-field-desc" style={{ marginTop: 10 }}>
        {report?.claim_boundary ?? "Bypass launch gate is read-only and does not authorize trading or money movement."}
      </div>
    </GlassPanel>
  );
}

