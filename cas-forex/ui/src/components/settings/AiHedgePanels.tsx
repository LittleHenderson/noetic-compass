/* Extracted from pages/SettingsPage.tsx (settings decomposition, slice 2). */

import { GlassPanel } from "../../components/GlassPanel";
import { StatusChip } from "../../components/StatusChip";
import { ControlField } from "../../components/settings/ControlField";
import { AiHedgeManagementExecutionResult, AiHedgeManagementHandoffReport, AiHedgeSupervisionReport, fetchAiHedgeManagementHandoff, fetchAiHedgeSupervision, runAiHedgeManagementAction } from "../../data/api";
import { formatUsd, recordOrNull } from "./formatters";
import { useEffect, useState } from "react";

export function AiHedgeSupervisionPanel() {
  const [report, setReport] = useState<AiHedgeSupervisionReport | null>(null);
  const [status, setStatus] = useState("");

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    setStatus("");
    const next = await fetchAiHedgeSupervision();
    if (next) {
      setReport(next);
    } else {
      setStatus("AI Hedge supervision unavailable - is the API reachable?");
    }
  }

  const recommendations = report?.recommendations ?? [];
  const actionRecommendations = recommendations.filter((row) => row.intent !== "skip");
  const positions = report?.positions ?? [];
  const topRecommendation = actionRecommendations[0] ?? recommendations[0];
  const sourceHealth = recordOrNull(report?.source_health);
  const positionFeedLabel = report?.position_feed_label
    ?? (typeof sourceHealth?.position_feed_label === "string" ? sourceHealth.position_feed_label : undefined)
    ?? "warming";
  const positionFeedDetail = report?.position_feed_detail
    ?? (typeof sourceHealth?.position_feed_detail === "string" ? sourceHealth.position_feed_detail : undefined)
    ?? (typeof sourceHealth?.detail === "string" ? sourceHealth.detail : undefined)
    ?? report?.price_source_summary
    ?? "Movement source truth is warming.";

  return (
    <GlassPanel title="AI Operator Edge / Hedge Supervision" subtitle="Runtime edge and trade-management recommendations; dispatch gates remain authoritative">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <StatusChip
          label={report?.status ?? "SYNCING"}
          variant={report?.status === "ATTENTION" ? "danger" : report?.status === "ACTIVE_RECOMMENDATIONS" ? "warning" : report?.status === "WATCHING" ? "success" : "muted"}
          size="sm"
        />
        <StatusChip
          label={report?.price_source_status ?? "SOURCE WARMING"}
          variant={report?.static_simulation_active ? "warning" : report?.price_source_status === "PROVIDER_ACTIVE" ? "success" : "muted"}
          size="sm"
        />
        <StatusChip label={`${report?.position_count ?? 0} POSITIONS`} variant="muted" size="sm" />
        <StatusChip
          label={`${report?.action_recommendation_count ?? 0} ACTION INTENTS`}
          variant={(report?.action_recommendation_count ?? 0) ? "warning" : "success"}
          size="sm"
        />
        <StatusChip
          label={`${report?.high_urgency_count ?? 0} HIGH`}
          variant={(report?.high_urgency_count ?? 0) ? "danger" : "success"}
          size="sm"
        />
      </div>
      <div className="control-grid">
        <ControlField
          label="Top Intent"
          value={topRecommendation ? `${topRecommendation.intent ?? "unknown"} ${topRecommendation.symbol ?? ""}` : "No recommendation loaded."}
          danger={topRecommendation?.urgency === "HIGH"}
          description={topRecommendation?.reason ?? report?.next_action ?? "AI Hedge supervision is warming."}
        />
        <ControlField
          label="Gate Path"
          value={topRecommendation?.gate_path ?? "No broker-bound action authorized here."}
          mono
          description="Any action still needs the protected dispatch path."
        />
        <ControlField
          label="Price Source"
          value={report?.price_source_label ?? "warming"}
          danger={Boolean(report?.static_simulation_active)}
          description={report?.price_source_summary ?? "Movement source truth is warming."}
        />
        <ControlField
          label="Position Feed"
          value={positionFeedLabel}
          danger={Boolean(report?.static_simulation_active)}
          description={positionFeedDetail}
        />
        <ControlField
          label="Execution Boundary"
          value={report?.broker_bound_action_authorized ? "AUTHORIZED" : "READ ONLY"}
          danger={Boolean(report?.broker_bound_action_authorized)}
          description="This report does not place orders, close positions, or move money."
        />
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>Intent</th>
              <th>Scope</th>
              <th>Urgency</th>
              <th>Reason</th>
              <th>Gate</th>
            </tr>
          </thead>
          <tbody>
            {recommendations.slice(0, 8).map((row, index) => (
              <tr key={`${row.intent ?? "intent"}-${row.symbol ?? "symbol"}-${index}`}>
                <td className="mono">{row.intent ?? "unknown"}</td>
                <td>{row.scope ?? "runtime"} {row.symbol ? `- ${row.symbol}` : ""}</td>
                <td>
                  <StatusChip
                    label={row.urgency ?? "LOW"}
                    variant={row.urgency === "HIGH" ? "danger" : row.urgency === "MEDIUM" ? "warning" : "muted"}
                    size="sm"
                  />
                </td>
                <td>{row.reason ?? ""}</td>
                <td className="mono">{row.gate_path ?? "read-only"}</td>
              </tr>
            ))}
            {recommendations.length === 0 && (
              <tr>
                <td colSpan={5}>AI Hedge supervision is warming.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>Position</th>
              <th>Side</th>
              <th>R</th>
              <th>P&amp;L</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {positions.slice(0, 8).map((row, index) => (
              <tr key={`${row.position_id ?? row.symbol ?? "position"}-${index}`}>
                <td>{row.symbol ?? "UNKNOWN"}</td>
                <td className="mono">{row.side ?? ""}</td>
                <td className="mono">{row.r_multiple == null ? "n/a" : Number(row.r_multiple).toFixed(2)}</td>
                <td className="mono">{formatUsd(row.floating_pnl_usd)}</td>
                <td>{row.position_source_label ?? row.price_source ?? "unknown"}{row.price_stale ? " - stale" : ""}</td>
              </tr>
            ))}
            {positions.length === 0 && (
              <tr>
                <td colSpan={5}>No open movement-stream positions.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="mobile-api-row" style={{ marginTop: 10 }}>
        <button className="mobile-api-button ghost" type="button" onClick={() => void refresh()}>Refresh AI Hedge supervision</button>
      </div>
      {status && <div className="control-field-desc" style={{ color: "var(--danger)", marginTop: 8 }}>{status}</div>}
      <div className="control-field-desc" style={{ marginTop: 10 }}>
        {report?.claim_boundary ?? "AI Hedge supervision is read-only and does not authorize trading."}
      </div>
    </GlassPanel>
  );
}


export function AiHedgeManagementHandoffPanel() {
  const [report, setReport] = useState<AiHedgeManagementHandoffReport | null>(null);
  const [status, setStatus] = useState("");
  const [execution, setExecution] = useState<AiHedgeManagementExecutionResult | null>(null);
  const [busyAction, setBusyAction] = useState("");

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    setStatus("");
    const next = await fetchAiHedgeManagementHandoff();
    if (next) {
      setReport(next);
    } else {
      setStatus("AI Hedge management handoff unavailable - is the API reachable?");
    }
  }

  async function runManagement(dryRun: boolean) {
    if (!topAction?.action_id) {
      setStatus("No current AI Edge/Hedge management draft is selected.");
      return;
    }
    setStatus("");
    setBusyAction(dryRun ? "dry-run" : "execute");
    try {
      const result = await runAiHedgeManagementAction({
        action_id: topAction.action_id,
        reason: "AI_OPERATOR_EDGE_MANAGEMENT",
        dry_run: dryRun,
        confirm_owner_action: false,
        confirm_phrase: "",
      });
      setExecution(result);
      if (!dryRun) {
        await refresh();
      }
    } catch {
      setStatus("AI Edge/Hedge management execution route failed - is the API reachable?");
    } finally {
      setBusyAction("");
    }
  }

  const actions = report?.management_actions ?? [];
  const blocked = report?.blocked_actions ?? [];
  const topAction = actions[0];
  const topBlocked = blocked[0];
  const formatNum = (value: unknown) => (
    value == null || value === "" || Number.isNaN(Number(value))
      ? "n/a"
      : Number(value).toFixed(2)
  );
  const executedAndProven = execution?.status === "EXECUTED_RECONCILED";
  const executedButUnproven = String(execution?.status ?? "").startsWith("EXECUTED_") && !executedAndProven;
  const postExecutionRefresh = (
    execution?.post_execution_refresh && typeof execution.post_execution_refresh === "object"
      ? execution.post_execution_refresh
      : null
  );
  const postExecutionRefreshStatus = String(
    execution?.post_execution_refresh_status
      ?? postExecutionRefresh?.status
      ?? "NOT RUN",
  );
  const postExecutionRefreshErrorCount = Number(postExecutionRefresh?.error_count ?? 0);

  return (
    <GlassPanel title="AI Operator Edge / Hedge Management Handoff" subtitle="Guarded broker-action drafts for breakeven, trailing, and partial-close execution">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <StatusChip
          label={report?.status ?? "SYNCING"}
          variant={report?.status === "READY_FOR_GUARDED_EXECUTION" || report?.status === "READY_FOR_OWNER_REVIEW" ? "warning" : report?.status === "BLOCKED" ? "danger" : report?.status === "NO_ACTIONABLE_MANAGEMENT" ? "success" : "muted"}
          size="sm"
        />
        <StatusChip
          label={`${report?.management_action_count ?? 0} DRAFTS`}
          variant={(report?.management_action_count ?? 0) ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip
          label={`${report?.blocked_action_count ?? 0} BLOCKED`}
          variant={(report?.blocked_action_count ?? 0) ? "danger" : "success"}
          size="sm"
        />
        <StatusChip
          label={report?.dry_run_only ? "DRY RUN ONLY" : "CHECK MODE"}
          variant="muted"
          size="sm"
        />
      </div>
      <div className="control-grid">
        <ControlField
          label="Top Draft"
          value={topAction ? `${topAction.broker_method ?? "action"} ${topAction.symbol ?? ""}` : "No broker-action draft."}
          description={topAction?.reason ?? topBlocked?.reason ?? report?.next_action ?? "AI Hedge management handoff is warming."}
        />
        <ControlField
          label="Ticket / Method"
          value={topAction ? `${topAction.broker_ticket ?? "n/a"} / ${topAction.broker_method ?? "n/a"}` : topBlocked ? `${topBlocked.broker_ticket ?? "n/a"} / ${topBlocked.block_code ?? "blocked"}` : "n/a"}
          mono
          danger={Boolean(topBlocked) && !topAction}
          description="A broker ticket is required before any close or modify proposal can target a real position."
        />
        <ControlField
          label="Draft Change"
          value={topAction ? `SL ${formatNum(topAction.stop_loss)} / volume ${formatNum(topAction.volume)}` : "No change drafted."}
          mono
          description="This is a proposed bridge call, not an executed command."
        />
        <ControlField
          label="Execution Boundary"
          value={report?.broker_bound_action_authorized ? "AUTHORIZED" : "GUARDED"}
          danger={Boolean(report?.broker_bound_action_authorized)}
          description="Per-action owner confirmation is not required inside delegated authority; fresh broker truth and execution guard approval still are."
        />
      </div>
      <div className="control-grid" style={{ marginTop: 12 }}>
        <ControlField
          label="Execution Result"
          value={execution?.status ?? "NOT RUN"}
          danger={Boolean(execution?.status && !["DRY_RUN", "EXECUTED_RECONCILED"].includes(String(execution.status)))}
          description={execution?.next_action ?? execution?.detail ?? "Run a dry-run first, then execute only if the selected draft should pass through the guard and bridge."}
        />
        <ControlField
          label="Broker Touch"
          value={execution?.broker_touched ? "BRIDGE CALLED" : "NO BROKER TOUCH"}
          mono
          danger={Boolean(execution?.broker_touched && executedButUnproven)}
          description={execution?.audit_id ? `audit ${execution.audit_id}` : "No execution audit row yet."}
        />
        <ControlField
          label="Receipt Reconciliation"
          value={execution?.terminal_receipt_status ?? "NOT CHECKED"}
          mono
          danger={Boolean(execution?.terminal_receipt_status && execution.terminal_receipt_status !== "RECONCILED" && execution.terminal_receipt_status !== "NOT_REQUESTED")}
          description={execution?.terminal_receipt && typeof execution.terminal_receipt.reason === "string" ? execution.terminal_receipt.reason : "After confirmed execution, bridge position state must prove the ticket/SL/volume outcome."}
        />
        <ControlField
          label="Post-Execution Refresh"
          value={postExecutionRefreshStatus}
          mono
          danger={Boolean(execution?.broker_touched && !["REFRESH_RAN", "NOT_REQUESTED"].includes(postExecutionRefreshStatus))}
          description={
            postExecutionRefresh
              ? `${postExecutionRefreshErrorCount} refresh errors; broker/account truth packets rebuilt after execution.`
              : "After broker execution, live telemetry and reconciliation should refresh from current terminal/account truth."
          }
        />
      </div>
      <div className="mobile-api-row" style={{ marginTop: 10 }}>
        <button
          className="mobile-api-button ghost"
          type="button"
          disabled={!topAction || busyAction !== ""}
          onClick={() => void runManagement(true)}
        >
          {busyAction === "dry-run" ? "Dry-running..." : "Dry run selected draft"}
        </button>
        <button
          className="mobile-api-button danger"
          type="button"
          disabled={!topAction || busyAction !== ""}
          onClick={() => void runManagement(false)}
        >
          {busyAction === "execute" ? "Executing..." : "Execute guarded draft"}
        </button>
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>Draft</th>
              <th>Ticket</th>
              <th>Method</th>
              <th>Change</th>
              <th>Gate</th>
            </tr>
          </thead>
          <tbody>
            {actions.slice(0, 8).map((row, index) => (
              <tr key={`${row.action_id ?? "action"}-${index}`}>
                <td>{row.intent ?? "unknown"} {row.symbol ? `- ${row.symbol}` : ""}</td>
                <td className="mono">{row.broker_ticket ?? "n/a"}</td>
                <td className="mono">{row.broker_method ?? "n/a"}</td>
                <td className="mono">SL {formatNum(row.stop_loss)} / volume {formatNum(row.volume)}</td>
                <td>{row.gate_path ?? "owner review required"}</td>
              </tr>
            ))}
            {actions.length === 0 && (
              <tr>
                <td colSpan={5}>No AI Hedge broker-action drafts are ready.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="positions-table-wrap ai-dial-table-wrap" style={{ marginTop: 12 }}>
        <table className="data-table ai-dial-table">
          <thead>
            <tr>
              <th>Blocked Intent</th>
              <th>Symbol</th>
              <th>Code</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody>
            {blocked.slice(0, 8).map((row, index) => (
              <tr key={`${row.intent ?? "blocked"}-${row.symbol ?? "symbol"}-${index}`}>
                <td className="mono">{row.intent ?? "unknown"}</td>
                <td>{row.symbol ?? "UNKNOWN"}</td>
                <td className="mono">{row.block_code ?? "BLOCKED"}</td>
                <td>{row.reason ?? ""}</td>
              </tr>
            ))}
            {blocked.length === 0 && (
              <tr>
                <td colSpan={4}>No blocked AI Hedge management drafts.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="mobile-api-row" style={{ marginTop: 10 }}>
        <button className="mobile-api-button ghost" type="button" onClick={() => void refresh()}>Refresh management handoff</button>
      </div>
      {status && <div className="control-field-desc" style={{ color: "var(--danger)", marginTop: 8 }}>{status}</div>}
      <div className="control-field-desc" style={{ marginTop: 10 }}>
        {report?.claim_boundary ?? "AI Hedge management handoff is proposal-only and does not call the broker."}
      </div>
    </GlassPanel>
  );
}

