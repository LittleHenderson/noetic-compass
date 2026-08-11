import { StatusChip } from "./StatusChip";
import type { AgentDecisionVersionTrace } from "../data/api";

type ChipVariant = "success" | "warning" | "danger" | "info" | "muted" | "paper";

interface DecisionVersionTraceProps {
  trace?: AgentDecisionVersionTrace | null;
}

function statusVariant(status: string): ChipVariant {
  const normalized = status.toUpperCase();
  if (normalized === "COMPLETE") return "success";
  if (normalized === "PARTIAL") return "warning";
  if (normalized === "NO_AGENT_CYCLE") return "muted";
  return "info";
}

function text(value: unknown, fallback = "not attached"): string {
  if (value === null || value === undefined) return fallback;
  const out = String(value).trim();
  return out || fallback;
}

function compactHash(value: unknown): string {
  const out = text(value);
  if (out === "not attached") return out;
  if (out.length <= 18) return out;
  return `${out.slice(0, 8)}...${out.slice(-6)}`;
}

function joinFirst(values: Array<unknown>): string {
  for (const value of values) {
    const out = text(value, "");
    if (out) return out;
  }
  return "not attached";
}

export function DecisionVersionTrace({ trace }: DecisionVersionTraceProps) {
  if (!trace) return null;
  const status = text(trace.trace_status, "UNKNOWN");
  const gaps = Array.isArray(trace.gaps) ? trace.gaps.filter(Boolean) : [];
  const marketRefs = Array.isArray(trace.market_data_refs)
    ? trace.market_data_refs.filter(Boolean)
    : [];

  return (
    <div className="decision-version-trace">
      <div className="decision-version-head">
        <span className="decision-version-title">Version trace</span>
        <StatusChip label={status} variant={statusVariant(status)} size="sm" />
        <span className="decision-version-source">{text(trace.trace_source)}</span>
      </div>
      <div className="decision-version-grid">
        <TraceItem label="Strategy" value={joinFirst([trace.strategy_ref, trace.strategy_version])} />
        <TraceItem label="Model" value={joinFirst([trace.model_ref, trace.agent_ref])} />
        <TraceItem label="Prompt" value={text(trace.prompt_version)} />
        <TraceItem label="Risk" value={text(trace.risk_engine_version)} />
        <TraceItem
          label="Execution"
          value={joinFirst([trace.dispatch_engine_version, trace.execution_router_version, trace.broker_mode])}
        />
        <TraceItem label="Market data" value={joinFirst([trace.market_data_source, trace.broker_symbol])} />
        <TraceItem label="Config" value={compactHash(trace.config_hash)} mono />
      </div>
      {marketRefs.length > 0 && (
        <div className="decision-version-refs" title={marketRefs.join("\n")}>
          refs: {marketRefs.slice(0, 2).join(", ")}
        </div>
      )}
      {gaps.length > 0 && (
        <div className="decision-version-gaps" title={gaps.join("\n")}>
          gaps: {gaps.slice(0, 4).join(", ")}
          {gaps.length > 4 ? ` +${gaps.length - 4}` : ""}
        </div>
      )}
    </div>
  );
}

function TraceItem({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="decision-version-item">
      <span className="decision-version-label">{label}</span>
      <span className={`decision-version-value${mono ? " mono" : ""}`} title={value}>
        {value}
      </span>
    </div>
  );
}
