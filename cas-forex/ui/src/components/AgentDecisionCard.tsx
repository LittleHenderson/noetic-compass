/* ── CAS Forex — Agent Decision Card ──
 *
 * Surfaces the latest autonomous agent decision so the operator can SEE
 * the agent's reasoning rather than having to type `ax` to inspect it.
 * Read-only telemetry — never advisory, never trade-pick guidance.
 *
 * Polls /api/forex/agent-decision/latest every 30 seconds while mounted.
 */

import { useEffect, useState } from "react";
import { GlassPanel } from "./GlassPanel";
import { StatusChip } from "./StatusChip";
import {
  fetchAgentDecisionLatest,
  type AgentDecisionResponse,
  type DecisionChainStep,
} from "../data/api";
import { DecisionVersionTrace } from "./DecisionVersionTrace";
import { DecisionMovementTruth } from "./DecisionMovementTruth";
import "./DecisionCardPrimitives.css";

const POLL_INTERVAL_MS = 30_000;
const RETRY_INTERVAL_MS = 5_000;

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

export function AgentDecisionCard() {
  const [data, setData] = useState<AgentDecisionResponse | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let retryId: number | undefined;
    const load = async () => {
      const result = await fetchAgentDecisionLatest();
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
      <GlassPanel title="Latest Agent Decision">
        <div className="agent-decision-card">
          <div className="decision-empty">
            Agent decision is warming. The app is retrying the live decision route.
          </div>
        </div>
      </GlassPanel>
    );
  }

  return (
    <GlassPanel title="Latest Agent Decision">
      <div className="agent-decision-card">
        <div className="decision-status-row">
          <code className="mono decision-cycle-id">{truncateCycleId(data.cycle_id)}</code>
          <StatusChip
            label={data.overall_status}
            variant={overallStatusVariant(data.overall_status)}
            size="sm"
          />
        </div>

        <div className="decision-summary">{data.plain_english_summary}</div>

        <DecisionMovementTruth truth={data.movement_source_truth} />

        <DecisionVersionTrace trace={data.version_trace} />

        {data.chain.length > 0 && (
          <div className="decision-chain">
            <button
              type="button"
              className="decision-chain-toggle"
              onClick={() => setExpanded((v) => !v)}
              aria-expanded={expanded}
            >
              <span className="decision-chain-caret">{expanded ? "▾" : "▸"}</span>
              <span>Decision chain ({data.chain.length})</span>
            </button>
            {expanded && (
              <ul className="decision-chain-list">
                {data.chain.map((step: DecisionChainStep, idx: number) => (
                  <li key={`${step.name}-${idx}`} className="decision-chain-item">
                    <div className="decision-chain-row">
                      <code className="mono decision-chain-name">{step.name}</code>
                      <StatusChip
                        label={step.status}
                        variant={chainStepVariant(step.status)}
                        size="sm"
                      />
                    </div>
                    <div className="decision-chain-headline">{step.headline}</div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {data.next_action_hint && (
          <div className="decision-next-action">{data.next_action_hint}</div>
        )}
      </div>
    </GlassPanel>
  );
}
