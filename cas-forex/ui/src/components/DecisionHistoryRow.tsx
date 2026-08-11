/* ── CAS Forex — Decision History Row ──
 *
 * Renders a single past agent decision. Read-only telemetry.
 * Plain text only — no markdown, no emojis, no trade-advisory text.
 */

import { useState } from "react";
import { GlassPanel } from "./GlassPanel";
import { StatusChip } from "./StatusChip";
import type {
  AgentDecisionHistoryItem,
  DecisionChainStep,
} from "../data/api";
import { DecisionVersionTrace } from "./DecisionVersionTrace";
import "./DecisionCardPrimitives.css";

type ChipVariant = "success" | "warning" | "danger" | "info" | "muted" | "paper";

function overallStatusVariant(status: string): ChipVariant {
  switch (status) {
    case "executed":
      return "info";
    case "approved_not_executed":
      return "paper";
    case "blocked":
      return "warning";
    case "no_recent_decision":
    default:
      return "muted";
  }
}

function chainStepVariant(status: string): ChipVariant {
  switch (status) {
    case "found":
      return "info";
    case "missing":
      return "muted";
    case "blocked":
      return "warning";
    default:
      return "muted";
  }
}

function truncateCycleId(id: string | null): string {
  if (!id) return "—";
  if (id.length <= 24) return id;
  return `${id.slice(0, 10)}…${id.slice(-8)}`;
}

function formatRelativeTime(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const ts = Date.parse(iso);
  if (Number.isNaN(ts)) return null;
  const diffSec = Math.floor((Date.now() - ts) / 1000);
  if (diffSec < 0) return "just now";
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}

interface DecisionHistoryRowProps {
  decision: AgentDecisionHistoryItem;
}

export function DecisionHistoryRow({ decision }: DecisionHistoryRowProps) {
  const [summaryExpanded, setSummaryExpanded] = useState(false);
  const [chainExpanded, setChainExpanded] = useState(false);

  const summary = decision.plain_english_summary ?? "";
  const summaryIsLong = summary.length > 200;
  const relTime = formatRelativeTime(decision.actioned_at ?? null);

  return (
    <GlassPanel>
      <div className="decision-history-row">
        <div className="decision-status-row">
          <code className="mono decision-cycle-id">
            {truncateCycleId(decision.cycle_id)}
          </code>
          <StatusChip
            label={decision.overall_status}
            variant={overallStatusVariant(decision.overall_status)}
            size="sm"
          />
          {relTime && (
            <span className="decision-history-time">{relTime}</span>
          )}
        </div>

        <div
          className={`decision-summary ${
            summaryIsLong && !summaryExpanded ? "decision-summary-clamped" : ""
          }`}
        >
          {summary || "No summary available."}
        </div>
        {summaryIsLong && (
          <button
            type="button"
            className="decision-chain-toggle"
            onClick={() => setSummaryExpanded((v) => !v)}
            aria-expanded={summaryExpanded}
          >
            {summaryExpanded ? "show less" : "show more"}
          </button>
        )}

        <DecisionVersionTrace trace={decision.version_trace} />

        {decision.chain.length > 0 && (
          <div className="decision-chain">
            <button
              type="button"
              className="decision-chain-toggle"
              onClick={() => setChainExpanded((v) => !v)}
              aria-expanded={chainExpanded}
            >
              <span className="decision-chain-caret">
                {chainExpanded ? "▾" : "▸"}
              </span>
              <span>Decision chain ({decision.chain.length})</span>
            </button>
            {chainExpanded && (
              <ul className="decision-chain-list">
                {decision.chain.map((step: DecisionChainStep, idx: number) => (
                  <li
                    key={`${step.name}-${idx}`}
                    className="decision-chain-item"
                  >
                    <div className="decision-chain-row">
                      <code className="mono decision-chain-name">
                        {step.name}
                      </code>
                      <StatusChip
                        label={step.status}
                        variant={chainStepVariant(step.status)}
                        size="sm"
                      />
                    </div>
                    <div className="decision-chain-headline">
                      {step.headline}
                    </div>
                    {step.detail && (
                      <div className="decision-chain-detail">{step.detail}</div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {decision.next_action_hint && (
          <div className="decision-next-action">{decision.next_action_hint}</div>
        )}
      </div>
    </GlassPanel>
  );
}
