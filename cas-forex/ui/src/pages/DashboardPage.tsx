/* ── CAS Forex — Operations Dashboard ── */

import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import { SparkChart } from "../components/charts/SparkChart";
import type { DashboardState } from "../types/evidence";

interface DashboardPageProps {
  state: DashboardState;
}

export function DashboardPage({ state }: DashboardPageProps) {
  const { uiReadiness: r, dailySchedule: s, dailyBundle: b } = state;
  const risk = b.latest_risk.latest_review;
  const decision = b.latest_decision.latest_decision;

  return (
    <div className="dashboard-page">
      {/* ── Account Snapshot ── */}
      <div className="dashboard-grid-3col">
        <GlassPanel title="Account" variant="info">
          <div className="metric-stack">
            <Metric label="Equity" value={`$${risk.account_equity.toLocaleString()}`} />
            <Metric label="Mode" value="PAPER_MT5" mono />
            <Metric label="Broker" value="Demo Only" />
            <Metric label="Live" value="NOT LICENSED" danger />
          </div>
        </GlassPanel>

        <GlassPanel title="Risk Budget">
          <div className="metric-stack">
            <Metric label="Per Trade" value={`${risk.max_risk_per_trade_pct}%`} />
            <Metric label="Daily Budget" value={`$${risk.daily_risk_budget_usd.toFixed(0)} (${risk.daily_risk_budget_pct}%)`} />
            <Metric label="Max Lots" value={`${risk.max_position_lots}`} mono />
            <Metric label="Attempts" value={`${risk.proposed_attempts} / ${risk.max_paper_attempts}`} mono />
          </div>
        </GlassPanel>

        <GlassPanel title="Proof Progress">
          <div className="metric-stack">
            <Metric label="Paper Days" value={`${r.completed_trading_days} / 30`} mono />
            <Metric label="Multi-Day Bundles" value={`${r.complete_bundle_days} / ${r.min_daily_bundles_for_ui}`} mono />
            <Metric label="Chains Verified" value={r.chains_verified.paper_proof && r.chains_verified.paper_decision && r.chains_verified.paper_risk ? "3/3" : "INCOMPLETE"} mono />
            <Metric label="Edge" value="OPEN" warning />
          </div>
        </GlassPanel>
      </div>

      {/* ── Paper Route Candidates ── */}
      <GlassPanel title="Paper Route Candidates" subtitle={decision.date}>
        <div className="positions-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Symbol</th><th>Dir</th><th>Entry</th><th>SL</th><th>TP</th>
                <th>Conf</th><th>Pulse</th><th>Lots</th><th>Risk</th><th>Status</th>
              </tr>
            </thead>
            <tbody>
              {decision.symbol_decisions.map((d) => {
                const sizing = b.latest_risk.latest_review.sizing.find((sz) => sz.symbol === d.symbol);
                return (
                  <tr key={d.proposal.proposal_id}>
                    <td className="mono cell-symbol">{d.symbol}</td>
                    <td><StatusChip label={d.direction} variant={d.direction === "LONG" ? "info" : "danger"} size="sm" /></td>
                    <td className="mono">{d.proposal.entry_price.toFixed(2)}</td>
                    <td className="mono" style={{ color: "var(--danger)" }}>{d.proposal.stop_loss.toFixed(2)}</td>
                    <td className="mono" style={{ color: "var(--success)" }}>{d.proposal.take_profit.toFixed(2)}</td>
                    <td className="mono">{(d.confidence * 100).toFixed(0)}%</td>
                    <td><SparkChart data={[0.35, Math.max(0.2, d.confidence - 0.08), d.confidence]} width={72} height={24} /></td>
                    <td className="mono">{sizing?.sized_lots ?? "—"}</td>
                    <td className="mono">{sizing != null ? `$${sizing.planned_risk_usd.toFixed(2)}` : "—"}</td>
                    <td><StatusChip label={d.action} variant="paper" size="sm" /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </GlassPanel>

      {/* ── Daily Summary + Next Action ── */}
      <div className="dashboard-grid-2col">
        <GlassPanel title="Today's Summary" subtitle={b.date}>
          <div className="summary-list">
            <SummaryRow label="Route Action" value={decision.route_action} chip="paper" />
            <SummaryRow label="Macro Gate" value={decision.macro_status} chip={decision.macro_status === "PASS" ? "success" : "warning"} />
            <SummaryRow label="Event Context" value={decision.event_context} />
            <SummaryRow label="Bundle Steps" value={`${b.completed_steps} / ${b.total_steps}`} mono />
            <SummaryRow label="Overall" value={b.overall_status} chip={b.completed ? "success" : "warning"} />
          </div>
        </GlassPanel>

        <GlassPanel title="Next Action" variant="info">
          <div className="summary-list">
            <SummaryRow label="Next Due" value={s.next_due_date} mono />
            <SummaryRow label="Status" value={s.next_due_status} chip="warning" />
            <SummaryRow label="Bundles Remaining" value={`${s.ui_bundles_remaining}`} mono />
            <SummaryRow label="Paper Days Left" value={`${s.paper_days_remaining}`} mono />
          </div>
          <div className="next-command">
            <code className="next-command-text">{s.recommended_command}</code>
          </div>
        </GlassPanel>
      </div>

      {/* ── Strategy Leads (from strategy_leads.json) ── */}
      <GlassPanel title="Strategy Leads" subtitle="Source: strategy_leads.json">
        <div className="leads-table-wrap">
          <table className="data-table">
            <thead>
              <tr><th>#</th><th>Lead</th><th>Status</th><th>Family</th><th>Symbols</th><th>Top Result</th><th>Open Gates</th></tr>
            </thead>
            <tbody>
              {state.strategyLeads?.map((lead) => (
                <tr key={lead.lead_id}>
                  <td className="mono">{lead.priority}</td>
                  <td className={`mono ${lead.priority === 2 ? "cell-active" : ""}`}>{lead.lead_id}</td>
                  <td><StatusChip label={lead.status === "ACTIVE_RESEARCH_LEAD" ? "ACTIVE" : lead.status} variant={lead.status === "WATCHLIST_ONLY" ? "muted" : lead.priority <= 2 ? "info" : "paper"} size="sm" /></td>
                  <td className="mono">{lead.family}</td>
                  <td className="mono" style={{ fontSize: "0.68rem" }}>{lead.symbols_promoted_for_next_tests.join(", ")}</td>
                  <td style={{ color: "var(--text-muted)", fontSize: "0.68rem", maxWidth: 240, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{lead.headline_results[0]}</td>
                  <td className="mono" style={{ fontSize: "0.66rem", color: "var(--warning)" }}>{lead.open_gates.length} gates</td>
                </tr>
              )) ?? (
                <tr><td colSpan={7} className="text-muted">Loading strategy leads from strategy_leads.json...</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </GlassPanel>

      {/* ── Evidence Chain Health ── */}
      <GlassPanel title="Evidence Chain Health">
        <div className="evidence-health-grid">
          <EvidenceHealth label="Paper Proof Chain" verified={r.chains_verified.paper_proof} detail={`${r.completed_trading_days} days recorded`} />
          <EvidenceHealth label="Paper Decision Chain" verified={r.chains_verified.paper_decision} detail={`${b.latest_decision.decision_count} decisions`} />
          <EvidenceHealth label="Paper Risk Chain" verified={r.chains_verified.paper_risk} detail={`${b.latest_risk.review_count} reviews`} />
          <EvidenceHealth label="WORM Anchoring" verified={false} detail="UNAVAILABLE — local hash chain only" />
        </div>
      </GlassPanel>

      {/* ── NOT LICENSED ── */}
      <GlassPanel title="Live & Payment Gates" variant="danger">
        <div className="gate-grid">
          <GateItem label="Deployment" detail="Paper proof incomplete (1/30)" />
          <GateItem label="Broker ACCEPT" detail="No live broker connection authorized" />
          <GateItem label="Auto-Deposit" detail="Payment movement not authorized" />
          <GateItem label="Debit / Card / Bank" detail="Transfer not authorized" />
          <GateItem label="Payout Automation" detail="Sweep/payout not authorized" />
          <GateItem label="Live Trading" detail="1/30 paper days, edge OPEN" />
        </div>
      </GlassPanel>
    </div>
  );
}

/* ── Sub-components ── */

function Metric({ label, value, mono, danger, warning }: { label: string; value: string; mono?: boolean; danger?: boolean; warning?: boolean }) {
  return (
    <div className="dashboard-metric">
      <span className="field-label">{label}</span>
      <span className={`field-value ${mono ? "mono" : ""}`} style={{ color: danger ? "var(--danger)" : warning ? "var(--warning)" : undefined }}>{value}</span>
    </div>
  );
}

function SummaryRow({ label, value, chip, mono }: { label: string; value: string; chip?: "success" | "warning" | "danger" | "info" | "muted" | "paper"; mono?: boolean }) {
  return (
    <div className="summary-row">
      <span className="field-label">{label}</span>
      {chip ? <StatusChip label={value} variant={chip} size="sm" /> : <span className={`field-value ${mono ? "mono" : ""}`}>{value}</span>}
    </div>
  );
}

function EvidenceHealth({ label, verified, detail }: { label: string; verified: boolean; detail: string }) {
  return (
    <div className="evidence-health-item">
      <div className="evidence-health-header">
        <span className="evidence-health-dot" style={{ background: verified ? "var(--success)" : "var(--danger)" }} />
        <span className="evidence-health-label">{label}</span>
        <StatusChip label={verified ? "VERIFIED" : "FAILED"} variant={verified ? "success" : "danger"} size="sm" />
      </div>
      <div className="evidence-health-detail">{detail}</div>
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
