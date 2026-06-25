/* ── CAS Forex — Strategy Dev Queue Page ──
 *
 * Lists strategy-dev work items and lets the operator manually
 * promote / demote / reject / archive / review each item.
 * Instrument panel only — no advisory language.
 */

import { useEffect, useMemo, useState } from "react";
import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import {
  applyStrategyDevAction,
  fetchStrategyDevQueue,
  type ApiPostError,
  type StrategyActionResponse,
  type StrategyDevAction,
} from "../data/api";
import type {
  DashboardState,
  StrategyDevQueueReport,
  StrategyDevWorkItem,
} from "../types/evidence";

interface StrategyDevPageProps {
  state: DashboardState;
}

type ChipVariant = "success" | "warning" | "danger" | "info" | "muted" | "paper";

interface RowResult {
  kind: "ok" | "err";
  ok?: StrategyActionResponse;
  err?: ApiPostError;
}

const ACTION_ORDER: StrategyDevAction[] = ["promote", "demote", "reject", "archive", "review"];

const ACTION_LABEL: Record<StrategyDevAction, string> = {
  promote: "Promote",
  demote: "Demote",
  reject: "Reject",
  archive: "Archive",
  review: "Review",
};

function stageVariant(stage: string): ChipVariant {
  const upper = (stage || "").toUpperCase();
  if (upper.includes("PROMOTE") || upper.includes("READY") || upper.includes("ACTIVE")) return "info";
  if (upper.includes("REVIEW") || upper.includes("PENDING") || upper.includes("QUEUED")) return "warning";
  if (upper.includes("REJECT") || upper.includes("BLOCK") || upper.includes("FAIL")) return "danger";
  if (upper.includes("ARCHIVE") || upper.includes("CLOSED")) return "muted";
  if (upper.includes("DEMOTE")) return "warning";
  return "muted";
}

export function StrategyDevPage({ state }: StrategyDevPageProps) {
  const initialReport = state.strategyDevQueue ?? null;
  const [report, setReport] = useState<StrategyDevQueueReport | null>(initialReport);
  const [loading, setLoading] = useState(true);
  const [stageFilter, setStageFilter] = useState<string>("__ALL__");
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [pending, setPending] = useState<Record<string, StrategyDevAction | null>>({});
  const [results, setResults] = useState<Record<string, RowResult>>({});

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchStrategyDevQueue()
      .then((data) => {
        if (!cancelled && data) setReport(data);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const items = report?.work_items ?? [];

  const stageOptions = useMemo(() => {
    const set = new Set<string>();
    for (const it of items) {
      if (it.status) set.add(it.status);
    }
    return Array.from(set).sort();
  }, [items]);

  const filtered = useMemo(() => {
    if (stageFilter === "__ALL__") return items;
    return items.filter((it) => it.status === stageFilter);
  }, [items, stageFilter]);

  async function handleAction(item: StrategyDevWorkItem, action: StrategyDevAction) {
    const id = item.item_id;
    const note = notes[id] ?? "";
    setPending((prev) => ({ ...prev, [id]: action }));
    const result = await applyStrategyDevAction(id, action, note);
    setPending((prev) => ({ ...prev, [id]: null }));
    if (result.ok) {
      setResults((prev) => ({ ...prev, [id]: { kind: "ok", ok: result.data } }));
    } else {
      setResults((prev) => ({ ...prev, [id]: { kind: "err", err: result.error } }));
    }
  }

  return (
    <div className="dashboard-page">
      <GlassPanel
        title="Strategy Dev Queue"
        subtitle={
          report
            ? `${report.summary.item_count} items · ${report.summary.queued_item_count} queued · ${report.summary.blocked_item_count} blocked`
            : loading
              ? "Loading strategy dev queue..."
              : "No strategy-dev queue report available"
        }
      >
        <div className="strategy-dev-filter-row">
          <label className="field-label" htmlFor="strategy-stage-filter">Filter by stage</label>
          <select
            id="strategy-stage-filter"
            className="strategy-dev-filter-select"
            value={stageFilter}
            onChange={(e) => setStageFilter(e.target.value)}
          >
            <option value="__ALL__">show all ({items.length})</option>
            {stageOptions.map((stage) => (
              <option key={stage} value={stage}>{stage}</option>
            ))}
          </select>
        </div>

        {filtered.length === 0 ? (
          <div className="no-data-message">
            <p>No strategy work items match the current filter.</p>
          </div>
        ) : (
          <ul className="strategy-dev-list">
            {filtered.map((item) => {
              const id = item.item_id;
              const result = results[id];
              const noteValue = notes[id] ?? "";
              const currentPending = pending[id] ?? null;
              return (
                <li key={id} className="strategy-dev-row">
                  <div className="strategy-dev-row-header">
                    <div className="strategy-dev-row-id">
                      <span className="mono cell-symbol">{id}</span>
                      <StatusChip
                        label={item.status || "UNKNOWN"}
                        variant={stageVariant(item.status)}
                        size="sm"
                      />
                    </div>
                    <div className="strategy-dev-row-meta mono">
                      created: {item.created_at}
                    </div>
                  </div>

                  <div className="strategy-dev-row-body">
                    {item.plain_english_goal && (
                      <div className="strategy-dev-row-desc">{item.plain_english_goal}</div>
                    )}
                    {item.proposed_change && (
                      <div className="strategy-dev-row-sub">
                        <span className="field-label">Proposed:</span> {item.proposed_change}
                      </div>
                    )}
                    {(item.symbols.length > 0 || item.timeframes.length > 0 || item.families.length > 0) && (
                      <div className="strategy-dev-row-sub mono">
                        {item.symbols.length > 0 && <span>symbols: {item.symbols.join(", ")} · </span>}
                        {item.timeframes.length > 0 && <span>tf: {item.timeframes.join(", ")} · </span>}
                        {item.families.length > 0 && <span>family: {item.families.join(", ")}</span>}
                      </div>
                    )}
                  </div>

                  <div className="strategy-dev-row-controls">
                    <input
                      type="text"
                      className="strategy-dev-note-input"
                      placeholder="Note (optional)"
                      value={noteValue}
                      onChange={(e) => setNotes((prev) => ({ ...prev, [id]: e.target.value }))}
                    />
                    <div className="strategy-dev-action-buttons">
                      {ACTION_ORDER.map((action) => (
                        <button
                          key={action}
                          type="button"
                          className="strategy-action-button"
                          onClick={() => handleAction(item, action)}
                          disabled={currentPending !== null}
                        >
                          {currentPending === action ? "..." : ACTION_LABEL[action]}
                        </button>
                      ))}
                    </div>
                  </div>

                  {result?.kind === "ok" && (
                    <div className="action-result-toast action-result-ok">
                      {result.ok?.action ?? "action"} applied
                      {result.ok?.current_stage ? ` · stage: ${result.ok.current_stage}` : ""}
                      {result.ok?.message ? ` · ${result.ok.message}` : ""}
                    </div>
                  )}
                  {result?.kind === "err" && (
                    <div className="action-result-toast action-result-err">
                      {formatStrategyError(result.err)}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </GlassPanel>
    </div>
  );
}

function formatStrategyError(err?: ApiPostError): string {
  if (!err) return "Request failed";
  const payload = err.payload as
    | { detail?: unknown; message?: string; current_stage?: string }
    | null;
  if (payload && typeof payload === "object") {
    const detail = payload.detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail === "object") {
      const d = detail as { message?: string; current_stage?: string };
      const parts: string[] = [];
      if (d.current_stage) parts.push(`stage: ${d.current_stage}`);
      if (d.message) parts.push(d.message);
      if (parts.length > 0) return parts.join(" · ");
    }
    const parts: string[] = [];
    if (payload.current_stage) parts.push(`stage: ${payload.current_stage}`);
    if (payload.message) parts.push(payload.message);
    if (parts.length > 0) return parts.join(" · ");
  }
  return err.message;
}
