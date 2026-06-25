/* ── CAS Forex — Operator Briefing Card ──
 *
 * One-call operator snapshot. Polls GET /api/forex/operator-briefing
 * every 60 seconds. Read-only instrument panel — renders the backend's
 * plain_english_briefing verbatim.
 */

import { useEffect, useState } from "react";
import { GlassPanel } from "./GlassPanel";
import { StatusChip } from "./StatusChip";
import {
  fetchOperatorBriefing,
  type OperatorBriefingResponse,
} from "../data/api";

const POLL_INTERVAL_MS = 60_000;

type ChipVariant = "success" | "warning" | "danger" | "info" | "muted" | "paper";

function loopHealthVariant(status: string): ChipVariant {
  const lower = (status || "").toLowerCase();
  if (lower === "running" || lower === "healthy" || lower === "ok") return "success";
  if (lower === "stalled" || lower === "warning") return "warning";
  if (lower === "failed" || lower === "error") return "danger";
  if (lower === "never_started" || lower === "unknown") return "muted";
  return "info";
}

export function OperatorBriefingCard() {
  const [data, setData] = useState<OperatorBriefingResponse | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      const result = await fetchOperatorBriefing();
      if (!cancelled) {
        setData(result);
        setLoaded(true);
      }
    };
    load();
    const handle = setInterval(load, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(handle);
    };
  }, []);

  if (!loaded) {
    return (
      <GlassPanel title="Operator Briefing">
        <div className="operator-briefing-card">
          <div className="decision-empty">Loading operator briefing...</div>
        </div>
      </GlassPanel>
    );
  }

  if (!data) {
    return (
      <GlassPanel title="Operator Briefing">
        <div className="operator-briefing-card">
          <div className="decision-empty">
            Operator briefing unavailable — /api/forex/operator-briefing did not respond.
          </div>
        </div>
      </GlassPanel>
    );
  }

  return (
    <GlassPanel title="Operator Briefing">
      <div className="operator-briefing-card">
        <div className="decision-status-row">
          <StatusChip
            label={data.loop_health_status || "unknown"}
            variant={loopHealthVariant(data.loop_health_status)}
            size="sm"
          />
        </div>

        <div className="loop-stats mono">
          cycles today: {data.cycles_today} · decisions: {data.decisions_today} · executions: {data.executions_today} · blocked: {data.blocked_today}
        </div>

        <div className="decision-summary">{data.plain_english_briefing}</div>

        {data.diagnostic_hints && data.diagnostic_hints.length > 0 && (
          <div className="loop-diagnostic">
            <div className="loop-diagnostic-header">Diagnostic hints</div>
            <ul className="loop-diagnostic-list">
              {data.diagnostic_hints.map((hint, idx) => (
                <li key={idx} className="loop-diagnostic-item">{hint}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </GlassPanel>
  );
}
