/* ── CAS Forex — Decision History Page ──
 *
 * Scrollable list of the agent's recent explained decisions.
 * Polls /api/forex/agent-decision/history every 60s while mounted.
 * Read-only instrument panel — never volunteers trade advisory text.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { DecisionHistoryRow } from "../components/DecisionHistoryRow";
import {
  fetchAgentDecisionHistory,
  type AgentDecisionHistoryItem,
  type AgentDecisionHistoryResponse,
} from "../data/api";
import "./DecisionHistoryPage.css";

const POLL_INTERVAL_MS = 60_000;
const LIMIT_OPTIONS = [10, 25, 50] as const;

interface StatusBreakdown {
  executed: number;
  blocked: number;
  approved_not_executed: number;
  no_recent_decision: number;
  other: number;
}

function tallyStatuses(decisions: AgentDecisionHistoryItem[]): StatusBreakdown {
  const out: StatusBreakdown = {
    executed: 0,
    blocked: 0,
    approved_not_executed: 0,
    no_recent_decision: 0,
    other: 0,
  };
  for (const d of decisions) {
    const s = d.overall_status;
    if (s === "executed") out.executed += 1;
    else if (s === "blocked") out.blocked += 1;
    else if (s === "approved_not_executed") out.approved_not_executed += 1;
    else if (s === "no_recent_decision") out.no_recent_decision += 1;
    else out.other += 1;
  }
  return out;
}

export function DecisionHistoryPage() {
  const [limit, setLimit] = useState<number>(25);
  const [response, setResponse] = useState<AgentDecisionHistoryResponse | null>(
    null,
  );
  const [loading, setLoading] = useState<boolean>(true);
  const [errored, setErrored] = useState<boolean>(false);

  const load = useCallback(async () => {
    const result = await fetchAgentDecisionHistory(limit);
    if (result) {
      setResponse(result);
      setErrored(false);
    } else {
      setErrored(true);
    }
    setLoading(false);
  }, [limit]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const runOnce = async () => {
      const result = await fetchAgentDecisionHistory(limit);
      if (cancelled) return;
      if (result) {
        setResponse(result);
        setErrored(false);
      } else {
        setErrored(true);
      }
      setLoading(false);
    };
    runOnce();
    const handle = setInterval(() => {
      void load();
    }, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(handle);
    };
  }, [limit, load]);

  const decisions = response?.decisions ?? [];
  const breakdown = useMemo(() => tallyStatuses(decisions), [decisions]);
  const total = decisions.length;

  return (
    <div className="decision-history-page">
      <div className="decision-history-header">
        <div>
          <h2 className="decision-history-title">Agent Decision History</h2>
          <div className="decision-history-sub">
            Recent autonomous-cycle decisions, most recent first. Read-only.
          </div>
        </div>
        <div className="decision-history-controls">
          <label className="decision-history-limit-label">
            Show
            <select
              className="decision-history-limit-select"
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
            >
              {LIMIT_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </label>
          <div className="decision-history-stats">
            <span className="decision-history-stat-total">total: {total}</span>
            <span>executed: {breakdown.executed}</span>
            <span>·</span>
            <span>blocked: {breakdown.blocked}</span>
            <span>·</span>
            <span>
              approved_not_executed: {breakdown.approved_not_executed}
            </span>
            <span>·</span>
            <span>no_recent_decision: {breakdown.no_recent_decision}</span>
            {breakdown.other > 0 && (
              <>
                <span>·</span>
                <span>other: {breakdown.other}</span>
              </>
            )}
          </div>
        </div>
      </div>

      {loading && !response && (
        <div className="decision-history-empty">Loading decision history…</div>
      )}

      {!loading && errored && !response && (
        <div className="decision-history-empty">
          Decision history unavailable — restart uvicorn so
          /api/forex/agent-decision/history is registered.
        </div>
      )}

      {!loading && response && decisions.length === 0 && (
        <div className="decision-history-empty">
          No decisions recorded yet — the agent has not yet produced a cycle.
        </div>
      )}

      {decisions.length > 0 && (
        <div className="decision-history-list">
          {decisions.map((decision, idx) => (
            <DecisionHistoryRow
              key={`${decision.cycle_id ?? "no-cycle"}-${idx}`}
              decision={decision}
            />
          ))}
        </div>
      )}
    </div>
  );
}
