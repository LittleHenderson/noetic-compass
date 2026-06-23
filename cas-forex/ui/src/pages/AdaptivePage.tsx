/* ── CAS Forex — Adaptive Cockpit Page ── */

import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import type { DashboardState, BasketState, AdaptiveTradeDecision, AdaptiveMemorySnapshot } from "../types/evidence";

interface AdaptivePageProps {
  state: DashboardState;
}

export function AdaptivePage({ state }: AdaptivePageProps) {
  const adaptive = state.adaptive;
  if (!adaptive) {
    return (
      <div className="placeholder-page">
        <div className="placeholder-card">
          <h2>Adaptive Compounding Cockpit</h2>
          <p>No adaptive compounding review has been recorded yet. Run the adaptive compounding review script to populate this view.</p>
          <span className="placeholder-badge">PENDING DATA</span>
        </div>
      </div>
    );
  }

  const review = adaptive.adaptive_compounding.latest_review;
  const actionCounts = adaptive.adaptive_action_counts;

  return (
    <div className="adaptive-page">
      {/* ── Adaptive Status Overview ── */}
      <div className="dashboard-grid-3col">
        <GlassPanel title="Adaptive Status" variant="info">
          <div className="metric-stack">
            <Metric label="Status" value={adaptive.cockpit_status} />
            <Metric label="Reviews" value={`${adaptive.adaptive_compounding.review_count}`} mono />
            <Metric label="Chain" value={adaptive.adaptive_compounding.chain_verified ? "VERIFIED" : "NOT VERIFIED"} mono />
            <Metric label="Deployment" value={adaptive.deployment_status} danger />
          </div>
        </GlassPanel>

        <GlassPanel title="Action Summary">
          <div className="action-chips">
            {Object.entries(actionCounts).length > 0 ? (
              Object.entries(actionCounts).map(([action, count]) => (
                <ActionChip key={action} action={action} count={count} />
              ))
            ) : (
              <span className="text-muted">No adaptive actions recorded</span>
            )}
          </div>
        </GlassPanel>

        <GlassPanel title="Config" variant="info">
          {review ? (
            <div className="metric-stack">
              <Metric label="Max Basket" value={`${review.config.max_basket_positions}`} mono />
              <Metric label="Base Lot" value={`${review.config.base_lot}`} mono />
              <Metric label="Compound Mult" value={`${review.config.compound_lot_multiplier}x`} mono />
              <Metric label="Min Compound R" value={`${review.config.min_compound_profit_r}R`} mono />
              <Metric label="Partial TP R" value={`${review.config.partial_take_profit_r}R`} mono />
              <Metric label="Evidence Threshold" value={`${review.config.min_evidence_score}`} mono />
            </div>
          ) : (
            <span className="text-muted">No review config available</span>
          )}
        </GlassPanel>
      </div>

      {/* ── Basket State ── */}
      {review && review.baskets.length > 0 && (
        <GlassPanel title="Basket State" subtitle={`${review.baskets.length} baskets`}>
          <div className="basket-grid">
            {review.baskets.map((basket) => (
              <BasketCard key={basket.basket_id} basket={basket} />
            ))}
          </div>
        </GlassPanel>
      )}

      {/* ── Adaptive Decisions ── */}
      <GlassPanel title="Adaptive Decisions" subtitle={review ? review.date : "No review"}>
        {review && review.decisions.length > 0 ? (
          <div className="adaptive-decisions-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Symbol</th><th>Action</th><th>Dir</th><th>Lots</th>
                  <th>Entry</th><th>SL</th><th>TP</th>
                  <th>Conf</th><th>Evidence</th><th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {review.decisions.map((d, i) => (
                  <DecisionRow key={`${d.symbol}-${i}`} decision={d} />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <span className="text-muted">No adaptive decisions recorded</span>
        )}
      </GlassPanel>

      {/* ── Memory Snapshots ── */}
      {review && review.memory_snapshots.length > 0 && (
        <GlassPanel title="Adaptive Memory Snapshots" subtitle={`${review.memory_snapshots.length} snapshots`}>
          <div className="memory-grid">
            {review.memory_snapshots.map((snap) => (
              <MemoryCard key={snap.snapshot_id} snapshot={snap} />
            ))}
          </div>
        </GlassPanel>
      )}

      {/* ── NOT LICENSED ── */}
      <GlassPanel title="Live & Payment Gates" variant="danger">
        <div className="gate-grid">
          <GateItem label="Deployment" detail="NOT LICENSED — adaptive compounding is paper/research only" />
          <GateItem label="Broker ACCEPT" detail="NOT LICENSED — no broker orders from adaptive engine" />
          <GateItem label="Auto-Deposit" detail="NOT LICENSED" />
          <GateItem label="Debit / Card / Bank" detail="NOT LICENSED" />
          <GateItem label="Payout Automation" detail="NOT LICENSED" />
          <GateItem label="Live Trading" detail="NOT LICENSED" />
        </div>
      </GlassPanel>
    </div>
  );
}

/* ── Sub-components ── */

function Metric({ label, value, mono, danger }: { label: string; value: string; mono?: boolean; danger?: boolean }) {
  return (
    <div className="dashboard-metric">
      <span className="field-label">{label}</span>
      <span className={`field-value ${mono ? "mono" : ""}`} style={{ color: danger ? "var(--danger)" : undefined }}>{value}</span>
    </div>
  );
}

const ACTION_COLORS: Record<string, { bg: string; fg: string }> = {
  OPEN_INITIAL: { bg: "var(--success-dim)", fg: "var(--success)" },
  ADD_TO_WINNER: { bg: "#1e3a5f", fg: "#60a5fa" },
  HOLD: { bg: "var(--warning-dim)", fg: "var(--warning)" },
  TIGHTEN_STOP: { bg: "#3b1f6e", fg: "var(--paper)" },
  PARTIAL_TAKE_PROFIT: { bg: "var(--accent-teal-dim)", fg: "var(--accent-teal)" },
  CLOSE_BASKET: { bg: "var(--danger-dim)", fg: "var(--danger)" },
  NO_TRADE: { bg: "var(--border-subtle)", fg: "var(--text-muted)" },
};

function ActionChip({ action, count }: { action: string; count: number }) {
  const colors = ACTION_COLORS[action] ?? { bg: "var(--border-subtle)", fg: "var(--text-muted)" };
  return (
    <span className="adaptive-action-chip" style={{ background: colors.bg, color: colors.fg, borderColor: colors.fg }}>
      {action}: {count}
    </span>
  );
}

function BasketCard({ basket }: { basket: BasketState }) {
  const isWinning = basket.floating_profit_r > 0;
  return (
    <div className="basket-card" style={{ borderColor: isWinning ? "var(--success-dim)" : "var(--danger-dim)" }}>
      <div className="basket-card-header">
        <span className="route-symbol">{basket.symbol}</span>
        <StatusChip label={basket.direction} variant="info" size="sm" />
        <StatusChip label={isWinning ? `+${basket.floating_profit_r.toFixed(2)}R` : `${basket.floating_profit_r.toFixed(2)}R`} variant={isWinning ? "success" : "danger"} size="sm" />
      </div>
      <div className="basket-card-body">
        <div className="sizing-row"><span className="field-label">Positions</span><span className="field-value mono">{basket.open_positions}</span></div>
        <div className="sizing-row"><span className="field-label">Total Lots</span><span className="field-value mono">{basket.total_lots.toFixed(2)}</span></div>
        <div className="sizing-row"><span className="field-label">Avg Entry</span><span className="field-value mono">{basket.average_entry?.toFixed(2) ?? "—"}</span></div>
        <div className="sizing-row"><span className="field-label">Current</span><span className="field-value mono">{basket.current_price?.toFixed(2) ?? "—"}</span></div>
        <div className="sizing-row"><span className="field-label">Floating P/L</span><span className="field-value mono" style={{ color: isWinning ? "var(--success)" : "var(--danger)" }}>${basket.floating_profit_usd.toFixed(2)}</span></div>
      </div>
    </div>
  );
}

function DecisionRow({ decision }: { decision: AdaptiveTradeDecision }) {
  return (
    <tr>
      <td className="mono cell-symbol">{decision.symbol}</td>
      <td><StatusChip label={decision.action} variant={decision.action === "ADD_TO_WINNER" ? "info" : decision.action === "CLOSE_BASKET" ? "danger" : decision.action === "NO_TRADE" ? "muted" : "paper"} size="sm" /></td>
      <td>{decision.direction ?? "—"}</td>
      <td className="mono">{decision.lot_size > 0 ? decision.lot_size.toFixed(2) : "—"}</td>
      <td className="mono">{decision.entry_price?.toFixed(2) ?? "—"}</td>
      <td className="mono" style={{ color: "var(--danger)" }}>{decision.stop_loss?.toFixed(2) ?? "—"}</td>
      <td className="mono" style={{ color: "var(--success)" }}>{decision.take_profit?.toFixed(2) ?? "—"}</td>
      <td className="mono">{decision.confidence != null ? `${(decision.confidence * 100).toFixed(0)}%` : "—"}</td>
      <td><StatusChip label={decision.evidence_status} variant={decision.evidence_score >= 0.6 ? "success" : decision.evidence_score >= 0.4 ? "warning" : "muted"} size="sm" /></td>
      <td style={{ color: "var(--text-muted)", fontSize: "0.7rem", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis" }}>{decision.reason}</td>
    </tr>
  );
}

function MemoryCard({ snapshot }: { snapshot: AdaptiveMemorySnapshot }) {
  return (
    <div className="memory-card">
      <div className="memory-card-header">
        <span className="route-symbol">{snapshot.symbol}</span>
        <StatusChip label={snapshot.action} variant="paper" size="sm" />
      </div>
      <div className="memory-card-body">
        <div className="sizing-row"><span className="field-label">Type</span><span className="field-value">{snapshot.snapshot_type}</span></div>
        <div className="sizing-row"><span className="field-label">Regime</span><span className="field-value">{snapshot.regime}</span></div>
        <div className="sizing-row"><span className="field-label">Evidence</span><span className="field-value mono">{snapshot.evidence_score.toFixed(2)}</span></div>
        <div className="sizing-row"><span className="field-label">Basket R</span><span className="field-value mono">{snapshot.basket_profit_r.toFixed(2)}R</span></div>
      </div>
    </div>
  );
}

function GateItem({ label, detail }: { label: string; detail: string }) {
  return (
    <div className="gate-item">
      <div className="gate-item-header">
        <span className="gate-item-label">{label}</span>
        <StatusChip label="NOT LICENSED" variant="danger" size="sm" />
      </div>
      <div className="gate-item-detail">{detail}</div>
    </div>
  );
}
