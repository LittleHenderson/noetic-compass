/* ── CAS Forex — Autonomous Loop Card ──
 *
 * Pulse view of the autonomous trading loop. Surfaces overall status,
 * today's cycle/decision/execution counts, time since last cycle, and
 * any diagnostic hints when the loop is stalled.
 *
 * Polls /api/forex/autonomous-loop/health every 30 seconds while mounted.
 * Read-only — instrument panel for the operator, not advisory.
 */

import { useEffect, useState } from "react";
import { GlassPanel } from "./GlassPanel";
import { StatusChip } from "./StatusChip";
import {
  fetchAutonomousLoopHealth,
  type AutonomousLoopHealthResponse,
} from "../data/api";
import "./DecisionCardPrimitives.css";

const POLL_INTERVAL_MS = 30_000;
const RETRY_INTERVAL_MS = 5_000;

type ChipVariant = "success" | "warning" | "danger" | "info" | "muted" | "paper";

function overallStatusVariant(status: string): ChipVariant {
  switch (status) {
    case "running":
      return "info";
    case "stalled":
      return "warning";
    case "never_started":
    case "unknown":
    default:
      return "muted";
  }
}

function formatElapsed(seconds: number | null): string | null {
  if (seconds == null || !Number.isFinite(seconds) || seconds < 0) return null;
  const whole = Math.floor(seconds);
  if (whole < 3600) {
    const m = Math.floor(whole / 60);
    const s = whole % 60;
    return `${m}m ${s}s`;
  }
  const h = Math.floor(whole / 3600);
  const m = Math.floor((whole % 3600) / 60);
  return `${h}h ${m}m`;
}

function formatLocalTime(iso: string | null): string | null {
  if (!iso) return null;
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return iso;
  return parsed.toLocaleTimeString([], { hour12: false });
}

function formatNextDue(iso: string | null): string | null {
  if (!iso) return null;
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return iso;
  const hh = String(parsed.getHours()).padStart(2, "0");
  const mm = String(parsed.getMinutes()).padStart(2, "0");
  return `${hh}:${mm}`;
}

export function AutonomousLoopCard() {
  const [data, setData] = useState<AutonomousLoopHealthResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    let retryId: number | undefined;
    const load = async () => {
      const result = await fetchAutonomousLoopHealth();
      if (cancelled) return;
      if (result) setData(result);
      retryId = window.setTimeout(load, result ? POLL_INTERVAL_MS : RETRY_INTERVAL_MS);
    };
    void load();
    return () => {
      cancelled = true;
      if (retryId !== undefined) window.clearTimeout(retryId);
    };
  }, []);

  if (!data) {
    return (
      <GlassPanel title="Autonomous Loop">
        <div className="autonomous-loop-card">
          <div className="decision-empty">
            Autonomous loop status is warming. The app is retrying the live loop route.
          </div>
        </div>
      </GlassPanel>
    );
  }

  const elapsed = formatElapsed(data.seconds_since_last_cycle);
  const lastCycleLocal = formatLocalTime(data.last_cycle_at_iso);
  const nextDue = formatNextDue(data.autowake_next_due_iso);

  return (
    <GlassPanel title="Autonomous Loop">
      <div className="autonomous-loop-card">
        <div className="decision-status-row">
          <StatusChip
            label={data.overall_status}
            variant={overallStatusVariant(data.overall_status)}
            size="sm"
          />
        </div>

        <div className="loop-stats mono">
          cycles today: {data.cycles_today} · decisions: {data.decisions_today} · executions: {data.executions_today} · blocked: {data.blocked_today}
        </div>

        <div className="decision-summary">{data.plain_english_summary}</div>

        {elapsed && (
          <div className="loop-last-cycle">
            <div>Last cycle: {elapsed} ago</div>
            {lastCycleLocal && (
              <code className="mono loop-last-cycle-iso">{lastCycleLocal}</code>
            )}
          </div>
        )}

        {nextDue && (
          <div className="loop-next-due">Next due: <span className="mono">{nextDue}</span></div>
        )}

        {data.diagnostic_hints.length > 0 && (
          <div className="loop-diagnostic">
            <div className="loop-diagnostic-header">What's blocking it</div>
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
