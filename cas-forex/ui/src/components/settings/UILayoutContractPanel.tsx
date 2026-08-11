/* Extracted from pages/SettingsPage.tsx (settings decomposition, slice 1). */

import { GlassPanel } from "../../components/GlassPanel";
import { StatusChip } from "../../components/StatusChip";
import { UILayoutContractReport, fetchUILayoutContract } from "../../data/api";
import { ControlField } from "./ControlField";
import { useEffect, useState } from "react";

export function UILayoutContractPanel() {
  const [report, setReport] = useState<UILayoutContractReport | null>(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    setStatus("");
    const next = await fetchUILayoutContract();
    if (next) {
      setReport(next);
    } else {
      setStatus("UI layout contract unavailable - is the API reachable?");
    }
  }

  const checks = report?.checks ?? [];
  const attentionChecks = checks.filter((check) => check.status !== "OK");
  const displayChecks = [...attentionChecks, ...checks.filter((check) => check.status === "OK")];

  return (
    <GlassPanel title="UI Layout Contract" subtitle="Static checks for nav, dropdown, mobile, and browser-zoom regressions">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <StatusChip
          label={report?.status ?? "SYNCING"}
          variant={report?.status === "OK" ? "success" : report?.status === "ATTENTION" ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip label={`${report?.ok_count ?? 0} OK`} variant="success" size="sm" />
        <StatusChip
          label={`${report?.attention_count ?? 0} ATTENTION`}
          variant={(report?.attention_count ?? 0) ? "warning" : "success"}
          size="sm"
        />
        <StatusChip label={`${report?.route_count ?? 0} ROUTES`} variant="muted" size="sm" />
      </div>
      <div className="control-grid">
        <ControlField
          label="Zoom-Sensitive CSS"
          value={(report?.css_zoom_violations?.length ?? 0) ? `${report?.css_zoom_violations?.length} issue(s)` : "None detected"}
          danger={Boolean(report?.css_zoom_violations?.length)}
          description="Flags viewport-scaled text and negative letter spacing."
        />
        <ControlField
          label="Missing Page Routes"
          value={(report?.missing_page_routes?.length ?? 0) ? report?.missing_page_routes?.join(", ") ?? "" : "None"}
          danger={Boolean(report?.missing_page_routes?.length)}
          description="Every nav item must be reachable through App routing."
        />
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
            {displayChecks.map((check) => (
              <tr key={check.check_id ?? check.detail ?? "layout-check"}>
                <td className="mono">{check.check_id ?? "layout_check"}</td>
                <td>
                  <StatusChip
                    label={check.status ?? "UNKNOWN"}
                    variant={check.status === "OK" ? "success" : check.status === "ATTENTION" ? "warning" : "muted"}
                    size="sm"
                  />
                </td>
                <td>{check.detail ?? ""}</td>
                <td className="mono">{(check.evidence ?? []).slice(0, 3).join(", ") || "none"}</td>
                <td>{check.next_action || "Keep covered."}</td>
              </tr>
            ))}
            {displayChecks.length === 0 && (
              <tr>
                <td colSpan={5}>UI layout contract is warming.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="mobile-api-row" style={{ marginTop: 10 }}>
        <button className="mobile-api-button ghost" type="button" onClick={() => void refresh()}>Refresh layout contract</button>
      </div>
      {status && <div className="control-field-desc" style={{ color: "var(--danger)", marginTop: 8 }}>{status}</div>}
      <div className="control-field-desc" style={{ marginTop: 10 }}>
        {report?.claim_boundary ?? "UI layout contract is read-only and does not authorize trading or money movement."}
      </div>
    </GlassPanel>
  );
}

