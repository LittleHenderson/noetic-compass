/* Extracted from pages/SettingsPage.tsx (settings decomposition, slice 2). */

import { GlassPanel } from "../../components/GlassPanel";
import { StatusChip } from "../../components/StatusChip";
import { ControlField } from "../../components/settings/ControlField";
import { ProfessionalReadinessMatrix, fetchProfessionalReadiness } from "../../data/api";
import { useEffect, useState } from "react";

export function ProfessionalReadinessPanel() {
  const [matrix, setMatrix] = useState<ProfessionalReadinessMatrix | null>(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    setStatus("");
    const next = await fetchProfessionalReadiness();
    if (next) {
      setMatrix(next);
    } else {
      setStatus("Professional readiness matrix unavailable - is the API reachable?");
    }
  }

  const rows = matrix?.rows ?? [];
  const attentionRows = rows.filter((row) => row.status === "GAP" || row.status === "PARTIAL");
  const displayRows = [
    ...attentionRows.filter((row) => row.completion_state === "MISSING"),
    ...attentionRows.filter((row) => row.blocked_by_external_dependency),
    ...attentionRows.filter((row) => row.completion_state === "PARTIAL"),
    ...rows.filter((row) => row.status !== "GAP" && row.status !== "PARTIAL"),
  ];

  return (
    <GlassPanel title="Professional Readiness Matrix" subtitle="37-item audit against serious trading-app standards">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <StatusChip
          label={matrix?.status ?? "SYNCING"}
          variant={matrix?.status === "OK" ? "success" : matrix?.status === "ATTENTION" ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip label={`${matrix?.ok_count ?? 0} OK`} variant="success" size="sm" />
        <StatusChip
          label={`${matrix?.partial_count ?? 0} PARTIAL`}
          variant={(matrix?.partial_count ?? 0) ? "warning" : "success"}
          size="sm"
        />
        <StatusChip
          label={`${matrix?.gap_count ?? 0} GAP`}
          variant={(matrix?.gap_count ?? 0) ? "danger" : "success"}
          size="sm"
        />
        <StatusChip
          label={`${matrix?.external_blocked_count ?? 0} EXTERNAL`}
          variant={(matrix?.external_blocked_count ?? 0) ? "warning" : "success"}
          size="sm"
        />
        <StatusChip label={`${matrix?.item_count ?? 0} CHECKS`} variant="muted" size="sm" />
      </div>
      <div className="control-grid">
        <ControlField
          label="Primary Gap"
          value={matrix?.top_attention_items?.[0] ?? "No high-priority gap loaded."}
          danger={Boolean(matrix?.gap_count)}
          description="Attention rows are sorted first in the table."
        />
        <ControlField
          label="Matrix Scope"
          value="READ ONLY"
          description="This report audits evidence and gaps; it does not change trading authority."
        />
        <ControlField
          label="External Blockers"
          value={`${matrix?.external_blocked_count ?? 0}`}
          description="Rows blocked by real-world counsel, hosted monitoring, or deployment configuration stay visible without being called code gaps."
        />
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Category</th>
              <th>Standard</th>
              <th>Status</th>
              <th>Evidence</th>
              <th>Next</th>
            </tr>
          </thead>
          <tbody>
            {displayRows.map((row) => (
              <tr key={`${row.item_number ?? "n"}-${row.key ?? "row"}`}>
                <td className="mono">{row.item_number ?? ""}</td>
                <td>{row.category ?? row.key ?? "readiness"}</td>
                <td>{row.professional_standard ?? ""}</td>
                <td>
                  <StatusChip
                    label={(row.completion_state ?? row.status ?? "UNKNOWN").replace(/_/g, " ")}
                    variant={
                      row.completion_state === "SATISFIED"
                        ? "success"
                        : row.completion_state === "MISSING"
                          ? "danger"
                          : "warning"
                    }
                    size="sm"
                  />
                </td>
                <td className="mono">{(row.present_evidence_refs ?? row.evidence_refs ?? []).slice(0, 3).join(", ") || "none"}</td>
                <td>{row.external_dependency || row.remaining_gap || row.next_action || "Keep covered."}</td>
              </tr>
            ))}
            {displayRows.length === 0 && (
              <tr>
                <td colSpan={6}>Professional readiness matrix is warming.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="mobile-api-row" style={{ marginTop: 10 }}>
        <button className="mobile-api-button ghost" type="button" onClick={() => void refresh()}>Refresh matrix</button>
      </div>
      {status && <div className="control-field-desc" style={{ color: "var(--danger)", marginTop: 8 }}>{status}</div>}
      <div className="control-field-desc" style={{ marginTop: 10 }}>
        {matrix?.claim_boundary ?? "Professional readiness matrix is read-only and does not authorize trading or money movement."}
      </div>
    </GlassPanel>
  );
}

