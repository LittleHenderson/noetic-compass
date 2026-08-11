/* Extracted from pages/SettingsPage.tsx (settings decomposition, slice 1). */

import { GlassPanel } from "../../components/GlassPanel";
import { StatusChip } from "../../components/StatusChip";
import { SpecContextStatusReport, fetchSpecContextStatus } from "../../data/api";
import { ControlField } from "./ControlField";
import { useEffect, useState } from "react";

export function SpecContextPanel() {
  const [report, setReport] = useState<SpecContextStatusReport | null>(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    setStatus("");
    const next = await fetchSpecContextStatus();
    if (next) {
      setReport(next);
    } else {
      setStatus("Spec context status unavailable - is the API reachable?");
    }
  }

  const source = report?.source ?? null;
  const promptReady = Boolean(report?.assistant_prompt_available && report?.operator_prompt_available);
  const stale = Boolean(report?.snapshot_stale);
  const sourceLabel = source?.path_or_url ?? "No spec workbook source found.";
  const aiHedge = report?.ai_hedge_intelligence_layer;
  const autonomousCorrection = report?.autonomous_execution_correction;
  const hedgeLayers = aiHedge?.layers ?? [];
  const hedgeIntents = aiHedge?.allowed_trade_intents ?? [];
  const hedgeEdgeDecisions = aiHedge?.allowed_operator_edge_decisions ?? [];
  const hedgeBoundaries = aiHedge?.hard_boundaries ?? [];
  const autonomousActions = autonomousCorrection?.autonomous_trading_authority?.allowed_actions ?? [];
  const moneyActions = autonomousCorrection?.autonomous_money_movement_authority?.allowed_actions ?? [];

  return (
    <GlassPanel title="Spec Context" subtitle="Spec-sheet authority memory used by Assistant and Operator">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <StatusChip
          label={report?.status ?? "SYNCING"}
          variant={report?.status === "OK" ? "success" : report?.status === "ATTENTION" ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip
          label={report?.available ? "SNAPSHOT AVAILABLE" : "SNAPSHOT MISSING"}
          variant={report?.available ? "success" : "warning"}
          size="sm"
        />
        <StatusChip
          label={promptReady ? "CHAT CONTEXT READY" : "CHAT CONTEXT INCOMPLETE"}
          variant={promptReady ? "success" : "warning"}
          size="sm"
        />
        <StatusChip
          label={stale ? "SOURCE NEWER THAN SNAPSHOT" : "SOURCE CURRENT"}
          variant={stale ? "warning" : "success"}
          size="sm"
        />
        <StatusChip
          label={aiHedge?.status ?? "HEDGE SPEC WARMING"}
          variant={aiHedge?.status === "SPECIFIED_GOVERNED_LAYER" ? "success" : "muted"}
          size="sm"
        />
        <StatusChip
          label={autonomousCorrection?.status ?? "AUTONOMY SPEC WARMING"}
          variant={autonomousCorrection?.status === "GOVERNING_REPLACEMENT_LANGUAGE" ? "success" : "muted"}
          size="sm"
        />
        <StatusChip label={`${report?.sheet_count ?? 0} SHEETS`} variant="muted" size="sm" />
      </div>
      <div className="control-grid">
        <ControlField label="Version" value={report?.version ?? "warming"} mono />
        <ControlField label="Generated" value={report?.generated_at ?? "warming"} mono />
        <ControlField label="Source" value={sourceLabel} mono danger={!report?.source_found} />
        <ControlField
          label="Next Action"
          value={report?.next_action ?? "Spec context status is warming."}
          danger={report?.status === "ATTENTION" || stale}
        />
        <ControlField
          label="Assistant Context"
          value={`${report?.assistant_context_chars ?? 0} chars`}
          mono
          description="Injected into the floating CAS Forex assistant prompt."
        />
        <ControlField
          label="Operator Constitution"
          value={`${report?.operator_constitution_chars ?? 0} chars`}
          mono
          description="Injected into Operator full tick and fast chat context."
        />
        <ControlField
          label="AI Operator Edge"
          value={aiHedge?.thesis ?? "Adaptive AI Operator edge spec is warming."}
          description={aiHedge?.claim_boundary ?? "Architecture memory; side effects still require backend dispatch/provider gates."}
        />
        <ControlField
          label="Autonomous Correction"
          value={autonomousCorrection?.version ?? "warming"}
          mono
          description={autonomousCorrection?.replacement_autonomy_clause ?? "Autonomous execution correction is warming."}
        />
        <ControlField
          label="Edge Role"
          value={aiHedge?.edge_role ?? "Operator edge role is warming."}
          description="This is architecture memory; dispatch, guard, broker truth, and risk gates still decide action authority."
        />
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>AI Operator Edge Surface</th>
              <th>Value</th>
              <th>Boundary</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Layers</td>
              <td>{hedgeLayers.map((layer) => layer.label).filter(Boolean).join(", ") || "warming"}</td>
              <td>Regime, strategy, trade management, account, and psychology supervision.</td>
            </tr>
            <tr>
              <td>Edge Decisions</td>
              <td className="mono">{hedgeEdgeDecisions.join(", ") || "warming"}</td>
              <td>Decision vocabulary only; no broker order is created from this panel.</td>
            </tr>
            <tr>
              <td>Allowed Intents</td>
              <td className="mono">{hedgeIntents.join(", ") || "warming"}</td>
              <td>Intent vocabulary only; execution remains gated elsewhere.</td>
            </tr>
            <tr>
              <td>Autonomous Trading</td>
              <td className="mono">{autonomousActions.join(", ") || "warming"}</td>
              <td>No per-order human approval inside armed owner limits; broker dispatch gates still apply.</td>
            </tr>
            <tr>
              <td>Autonomous Money Movement</td>
              <td className="mono">{moneyActions.join(", ") || "warming"}</td>
              <td>No per-configured-transfer human approval inside caps, provider rails, allowlists, and receipt gates.</td>
            </tr>
            <tr>
              <td>Hard Boundaries</td>
              <td>{(autonomousCorrection?.hard_blocks ?? hedgeBoundaries).slice(0, 5).join(", ") || "warming"}</td>
              <td>Dispatch, execution guard, edge PASS when required, broker truth, risk, provider, receipt, and kill-switch gates stay authoritative.</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>Artifact</th>
              <th>Path / Value</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>JSON snapshot</td>
              <td className="mono">{report?.json_path ?? "runtime/spec_context/spec_context.json"}</td>
            </tr>
            <tr>
              <td>Assistant markdown</td>
              <td className="mono">{report?.markdown_path ?? "runtime/spec_context/spec_context.md"}</td>
            </tr>
            <tr>
              <td>Operator constitution</td>
              <td className="mono">{report?.operator_constitution_path ?? "runtime/spec_context/operator_constitution.md"}</td>
            </tr>
            <tr>
              <td>Refresh command</td>
              <td className="mono">{report?.refresh_command ?? "python scripts/refresh_spec_context.py"}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div className="mobile-api-row" style={{ marginTop: 10 }}>
        <button className="mobile-api-button ghost" type="button" onClick={() => void refresh()}>Refresh spec context</button>
      </div>
      {status && <div className="control-field-desc" style={{ color: "var(--danger)", marginTop: 8 }}>{status}</div>}
      <div className="control-field-desc" style={{ marginTop: 10 }}>
        {report?.claim_boundary ?? "Spec context is product authority memory; actual side effects still require backend dispatch/provider gates."}
      </div>
    </GlassPanel>
  );
}

