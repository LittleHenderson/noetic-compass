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
} from "../data/operatorBriefingApi";
import {
  formatMovementSourceStatus,
  movementSourceStatusTone,
} from "../util/movementSource";
import "./DecisionCardPrimitives.css";

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

function launchGateVariant(status: string | undefined): ChipVariant {
  const upper = (status || "").toUpperCase();
  if (upper === "PASS" || upper === "READY") return "success";
  if (upper.includes("BLOCK")) return "danger";
  if (upper === "UNKNOWN" || upper === "WARMING" || !upper) return "muted";
  return "warning";
}

function positionFeedVariant(label: string | undefined): ChipVariant {
  const upper = (label || "").toUpperCase();
  if (upper === "LIVE MT5" || upper === "MT5 LIVE" || upper === "MT5 DEMO") return "success";
  if (upper === "SIM PROOF") return "warning";
  if (upper === "NONE" || upper === "UNKNOWN" || !upper) return "muted";
  return "info";
}

function brokerTruthVariant(status: string | undefined, readyForLive: boolean | undefined): ChipVariant {
  const upper = (status || "").toUpperCase();
  if (readyForLive) return "success";
  if (upper.includes("FAILED") || upper.includes("MISMATCH")) return "danger";
  if (upper === "UNAVAILABLE" || !upper) return "muted";
  return "warning";
}

function positionProtectionVariant(label: string | undefined, unprotectedCount: number | undefined): ChipVariant {
  const upper = (label || "").toUpperCase();
  if ((unprotectedCount ?? 0) > 0 || upper.includes("UNPROTECTED")) return "danger";
  if (upper.includes("CLEAR") || upper.includes("PROTECTED")) return "success";
  if (upper.includes("UNAVAILABLE") || !upper) return "warning";
  return "muted";
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

  const movementTruth = data.live_movement_source_truth ?? null;
  const livePositionFeedLabel = movementTruth?.position_feed_label?.trim()
    || data.live_position_feed_label
    || "NONE";
  const livePriceSourceStatus = movementTruth?.price_source_status?.trim()
    || data.live_price_source_status
    || null;
  const livePositionFeedDetail = movementTruth?.position_feed_detail?.trim()
    || movementTruth?.detail?.trim()
    || data.live_position_feed_detail
    || "";
  const liveTelemetrySource = movementTruth?.telemetry_source?.trim()
    || data.live_telemetry_source
    || "unknown";
  const liveTelemetryStale = movementTruth?.telemetry_stale ?? data.live_telemetry_stale ?? true;
  const liveTelemetryLastUpdateIso = movementTruth?.telemetry_last_update_iso?.trim()
    || data.live_telemetry_last_update_iso
    || "unknown";

  return (
    <GlassPanel title="Operator Briefing">
      <div className="operator-briefing-card">
        <div className="decision-status-row">
          <StatusChip
            label={data.loop_health_status || "unknown"}
            variant={loopHealthVariant(data.loop_health_status)}
            size="sm"
          />
          <StatusChip
            label={`Launch ${data.public_launch_gate_status || "unknown"}`}
            variant={launchGateVariant(data.public_launch_gate_status)}
            size="sm"
          />
          <StatusChip
            label={`Live prod ${data.live_money_production_status || "unknown"}`}
            variant={launchGateVariant(data.live_money_production_status)}
            size="sm"
          />
          <StatusChip
            label={livePositionFeedLabel}
            variant={positionFeedVariant(livePositionFeedLabel)}
            size="sm"
          />
          {livePriceSourceStatus && (
            <StatusChip
              label={formatMovementSourceStatus(livePriceSourceStatus, "SOURCE")}
              variant={movementSourceStatusTone(livePriceSourceStatus)}
              size="sm"
            />
          )}
          {liveTelemetryStale && <StatusChip label="STALE" variant="warning" size="sm" />}
          <StatusChip
            label={`Broker truth ${data.broker_truth_monitor_status || "unavailable"}`}
            variant={brokerTruthVariant(data.broker_truth_monitor_status, data.broker_truth_ready_for_live)}
            size="sm"
          />
          {data.broker_truth_paper_force_latched && (
            <StatusChip label="PAPER FORCE" variant="danger" size="sm" />
          )}
          <StatusChip
            label={data.broker_truth_position_protection_label || "PROTECTION UNAVAILABLE"}
            variant={positionProtectionVariant(
              data.broker_truth_position_protection_label,
              data.broker_truth_unprotected_position_count,
            )}
            size="sm"
          />
        </div>

        <div className="loop-stats mono">
          cycles today: {data.cycles_today} · decisions: {data.decisions_today} · executions: {data.executions_today} · blocked: {data.blocked_today}
        </div>

        <div className="loop-stats mono">
          public launch: {data.public_launch_status || "unknown"} | live production: {data.live_money_production_status || "unknown"} | launch blockers: {data.public_launch_gate_block_count ?? 0}
        </div>

        <div className="loop-stats mono">
          position feed: {livePositionFeedLabel} | telemetry source: {liveTelemetrySource} | last update: {liveTelemetryLastUpdateIso}
        </div>

        <div className="loop-stats mono">
          broker truth: {data.broker_truth_monitor_status || "unavailable"} | ready for live: {String(Boolean(data.broker_truth_ready_for_live))} | halt reasons: {data.broker_truth_halt_reason_summary || "none"} | unprotected: {data.broker_truth_unprotected_position_count ?? 0}
        </div>

        <div className="decision-summary">{data.plain_english_briefing}</div>

        {livePositionFeedDetail && (
          <div className="loop-diagnostic">
            <div className="loop-diagnostic-header">Position feed boundary</div>
            <div className="loop-diagnostic-item">{livePositionFeedDetail}</div>
          </div>
        )}

        {(data.broker_truth_paper_force_latched || (data.broker_truth_unprotected_position_count ?? 0) > 0 || data.broker_truth_position_protection_detail) && (
          <div className="loop-diagnostic">
            <div className="loop-diagnostic-header">Broker truth enforcement</div>
            {data.broker_truth_paper_force_latched && (
              <div className="loop-diagnostic-item">
                Paper-force is latched by broker truth: {data.broker_truth_halt_reason_summary || "none"}.
              </div>
            )}
            <div className="loop-diagnostic-item">
              Position protection: {data.broker_truth_position_protection_label || "PROTECTION UNAVAILABLE"}; unprotected broker-visible positions: {data.broker_truth_unprotected_position_count ?? 0}.
            </div>
            {data.broker_truth_position_protection_detail && (
              <div className="loop-diagnostic-item">{data.broker_truth_position_protection_detail}</div>
            )}
          </div>
        )}

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
