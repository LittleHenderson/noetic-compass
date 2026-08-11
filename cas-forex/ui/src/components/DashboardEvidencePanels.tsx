import { lazy, Suspense } from "react";
import { GlassPanel } from "./GlassPanel";
import { StatusChip } from "./StatusChip";
import { CONVICTION_SCORE_TITLE, formatConvictionScore } from "../util/conviction";
import {
  describeReconciliationMovementTruth,
  summarizeMovementSource,
} from "../util/movementSource";
import type {
  AccountReconciliationReport,
  DashboardState,
  MovementStreamState,
  StrategyLead,
} from "../types/evidence";

const SparkChart = lazy(() => import("./charts/SparkChart").then((m) => ({
  default: m.SparkChart,
})));

type ChipVariant = "success" | "warning" | "danger" | "info" | "muted" | "paper";

interface DashboardEvidencePanelsProps {
  state: DashboardState;
  movement: MovementStreamState | null;
  strategyLeads: StrategyLead[] | null;
  recon: AccountReconciliationReport | null;
}

export function DashboardEvidencePanels({ state, movement, strategyLeads, recon }: DashboardEvidencePanelsProps) {
  const { uiReadiness: r, dailySchedule: s } = state;
  const b = state.dailyBundle;
  const decision = b.latest_decision.latest_decision;
  const risk = b.latest_risk.latest_review;
  const account = state.accountLedger?.summary;
  const movementTruth = movement?.movement_source_truth ?? movement ?? null;
  const movementSource = summarizeMovementSource(movementTruth);
  const reconMovementTruth = describeReconciliationMovementTruth(recon);

  return (
    <>
      <GlassPanel title={movementSource.panelTitle} subtitle={movementSource.panelSubtitle}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
          <StatusChip
            label={movementSource.statusLabel}
            variant={movementSource.statusTone}
            size="sm"
          />
          <StatusChip
            label={`${movementSource.providerBackedCount} PROVIDER`}
            variant={movementSource.providerBackedCount ? "success" : "muted"}
            size="sm"
          />
          <StatusChip
            label={`${movementSource.staticFallbackCount} STATIC`}
            variant={movementSource.staticFallbackCount ? "warning" : "success"}
            size="sm"
          />
          {movementSource.mt5FallbackCount > 0 && (
            <StatusChip
              label={`${movementSource.mt5FallbackCount} MT5 FALLBACK`}
              variant="info"
              size="sm"
            />
          )}
          <StatusChip label="PAPER / DEMO" variant="paper" size="sm" />
        </div>
        <div className="dashboard-grid-3col">
          <div className="metric-stack" style={{ padding: 0 }}>
            <Metric label="Stream Mode" value={movement?.mode ?? "PAPER_DEMO_REALTIME_SCAFFOLD"} mono />
            <Metric label="Symbols" value={movement?.symbols?.join(", ") ?? "-"} mono />
            <Metric label="Updated" value={movement?.timestamp ?? "-"} mono />
          </div>
          <div className="metric-stack" style={{ padding: 0 }}>
            <Metric label="Balance" value={`$${(movement?.account.balance_usd ?? account?.balance_usd ?? risk.account_equity).toFixed(2)}`} mono />
            <Metric label="Equity" value={`$${(movement?.account.equity_usd ?? account?.equity_usd ?? risk.account_equity).toFixed(2)}`} mono />
            <Metric
              label="Floating P/L"
              value={`$${(movement?.account.floating_pnl_usd ?? 0).toFixed(2)}`}
              mono
              warning={(movement?.account.floating_pnl_usd ?? 0) === 0}
              danger={(movement?.account.floating_pnl_usd ?? 0) < 0}
            />
          </div>
          <div className="metric-stack" style={{ padding: 0 }}>
            <Metric label="Margin / Free" value={`$${(movement?.account.margin_used_usd ?? 0).toFixed(2)} / $${(movement?.account.free_margin_usd ?? 0).toFixed(2)}`} mono />
            <Metric label="Drawdown" value={`$${(movement?.account.drawdown_usd ?? 0).toFixed(2)} (${(movement?.account.drawdown_pct ?? 0).toFixed(3)}%)`} mono />
            <Metric label="Boundary" value="PAPER / DEMO" warning />
          </div>
        </div>
        {movementSource.warningText && (
          <div className="control-field-desc" style={{ marginTop: 10, color: "var(--warning)" }}>
            {movementSource.warningText}
          </div>
        )}
        {movement && movement.quotes.length > 0 && (
          <div className="positions-table-wrap" style={{ marginTop: 12 }}>
            <table className="data-table">
              <thead>
                <tr><th>Symbol</th><th>Bid</th><th>Ask</th><th>Spread</th><th>ATR</th><th>Session</th><th>Freshness</th><th>Source</th></tr>
              </thead>
              <tbody>
                {movement.quotes.map((q) => (
                  <tr key={q.symbol}>
                    <td className="mono cell-symbol">{q.symbol}</td>
                    <td className="mono">{q.bid.toFixed(2)}</td>
                    <td className="mono">{q.ask.toFixed(2)}</td>
                    <td className="mono">{q.spread_units.toFixed(1)} {q.price_unit_name}</td>
                    <td className="mono">{q.atr_units.toFixed(2)}</td>
                    <td><StatusChip label={q.session} variant="muted" size="sm" /></td>
                    <td>
                      <StatusChip
                        label={q.stale ? "STATIC" : "LIVE QUOTE"}
                        variant={q.stale ? "warning" : "success"}
                        size="sm"
                      />
                    </td>
                    <td className="mono" style={{ fontSize: "0.66rem" }}>{q.source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassPanel>

      <GlassPanel title="Paper Route Candidates" subtitle={decision.date}>
        <div className="positions-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Symbol</th><th>Dir</th><th>Entry</th><th>SL</th><th>TP</th>
                <th>Conviction</th><th>Pulse</th><th>Lots</th><th>Risk</th><th>Status</th>
              </tr>
            </thead>
            <tbody>
              {decision.symbol_decisions.map((d) => {
                const sizing = risk.sizing.find((sz) => sz.symbol === d.symbol);
                return (
                  <tr key={d.proposal.proposal_id}>
                    <td className="mono cell-symbol">{d.symbol}</td>
                    <td><StatusChip label={d.direction} variant={d.direction === "LONG" ? "info" : "danger"} size="sm" /></td>
                    <td className="mono">{d.proposal.entry_price.toFixed(2)}</td>
                    <td className="mono" style={{ color: "var(--danger)" }}>{d.proposal.stop_loss.toFixed(2)}</td>
                    <td className="mono" style={{ color: "var(--success)" }}>{d.proposal.take_profit.toFixed(2)}</td>
                    <td className="mono" title={CONVICTION_SCORE_TITLE}>{formatConvictionScore(d.confidence)}</td>
                    <td>
                      <Suspense fallback={<span className="mono">...</span>}>
                        <SparkChart data={[0.35, Math.max(0.2, d.confidence - 0.08), d.confidence]} width={72} height={24} />
                      </Suspense>
                    </td>
                    <td className="mono">{sizing?.sized_lots ?? "-"}</td>
                    <td className="mono">{sizing != null ? `$${sizing.planned_risk_usd.toFixed(2)}` : "-"}</td>
                    <td><StatusChip label={d.action} variant="paper" size="sm" /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </GlassPanel>

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

      <GlassPanel title="Strategy Leads" subtitle="Source: strategy_leads.json">
        <div className="leads-table-wrap">
          <table className="data-table">
            <thead>
              <tr><th>#</th><th>Lead</th><th>Status</th><th>Family</th><th>Symbols</th><th>Top Result</th><th>Open Gates</th></tr>
            </thead>
            <tbody>
              {strategyLeads?.map((lead) => (
                <tr key={lead.lead_id}>
                  <td className="mono">{lead.priority}</td>
                  <td className={`mono ${lead.priority === 2 ? "cell-active" : ""}`}>{lead.lead_id}</td>
                  <td>
                    <StatusChip
                      label={lead.status === "ACTIVE_RESEARCH_LEAD" ? "ACTIVE" : lead.status}
                      variant={lead.status === "WATCHLIST_ONLY" ? "muted" : lead.priority <= 2 ? "info" : "paper"}
                      size="sm"
                    />
                  </td>
                  <td className="mono">{lead.family}</td>
                  <td className="mono" style={{ fontSize: "0.68rem" }}>{(lead.symbols_promoted_for_next_tests ?? []).join(", ") || "-"}</td>
                  <td style={{ color: "var(--text-muted)", fontSize: "0.68rem", maxWidth: 240, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{lead.headline_results?.[0] ?? "-"}</td>
                  <td className="mono" style={{ fontSize: "0.66rem", color: "var(--warning)" }}>{(lead.open_gates ?? []).length} gates</td>
                </tr>
              )) ?? (
                <tr><td colSpan={7} className="text-muted">Loading strategy leads from strategy_leads.json...</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </GlassPanel>

      <GlassPanel title="Broker/Demo Account Reconciliation" subtitle={recon ? `${recon.overall_status} - ${recon.checks_ok}/${recon.checks_total} OK, ${recon.checks_mismatch} mismatch, ${recon.checks_unverifiable} unverifiable` : "No reconciliation report"}>
        {recon ? (
          <>
            <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
              <div className="metric-stack" style={{ padding: 0 }}>
                <Metric label="Overall" value={recon.overall_status} mono danger={recon.overall_status === "RECONCILIATION_FAILED"} warning={recon.overall_status === "RECONCILED_WITH_WARNINGS"} />
                <Metric label="Broker Mode" value={recon.broker_mode} mono />
                <Metric label="Chain Verified" value={recon.broker_chain_verified ? "YES" : "NO"} mono danger={!recon.broker_chain_verified} />
              </div>
              <div className="metric-stack" style={{ padding: 0 }}>
                <Metric label="Checks OK" value={`${recon.checks_ok}/${recon.checks_total}`} mono />
                <Metric label="Mismatches" value={`${recon.checks_mismatch}`} mono danger={recon.checks_mismatch > 0} />
                <Metric label="Unverifiable" value={`${recon.checks_unverifiable}`} mono warning={recon.checks_unverifiable > 0} />
              </div>
              <div className="metric-stack" style={{ padding: 0 }}>
                <Metric label="Receipt" value={recon.broker_receipt_validation_status ?? "-"} mono />
                <Metric label="Broker Sync" value={recon.sync_to_broker_snapshot ? "PREVIEW" : "OFF"} mono warning={!!recon.sync_to_broker_snapshot} />
                <Metric label="Edge" value={recon.trading_edge_status} warning />
              </div>
            </div>
            {reconMovementTruth.hasTruth && (
              <div style={{ marginBottom: 10 }}>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
                  <StatusChip label={reconMovementTruth.feedLabel} variant={reconMovementTruth.feedTone} size="sm" />
                  <StatusChip label={reconMovementTruth.statusLabel} variant={reconMovementTruth.statusTone} size="sm" />
                </div>
                {reconMovementTruth.detail && (
                  <div className="control-field-desc" style={{ color: reconMovementTruth.statusTone === "warning" ? "var(--warning)" : "var(--text-muted)" }}>
                    {reconMovementTruth.detail}
                  </div>
                )}
              </div>
            )}
            <div className="positions-table-wrap">
              <table className="data-table">
                <thead>
                  <tr><th>Check</th><th>Status</th><th>Detail</th></tr>
                </thead>
                <tbody>
                  {recon.checks.map((c) => (
                    <tr key={c.check_id}>
                      <td className="mono" style={{ fontSize: "0.68rem" }}>{c.check_id}</td>
                      <td><StatusChip label={c.status} variant={c.status === "OK" ? "success" : c.status === "MISMATCH" ? "danger" : "warning"} size="sm" /></td>
                      <td style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>{c.detail}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ marginTop: 8, fontSize: "0.68rem", color: "var(--warning)" }}>
              {recon.claim_boundary} Broker-synced reconciliation preview is available at /api/forex/reconciliation/account?sync_to_broker=true and remains paper/demo accounting only.
            </div>
          </>
        ) : (
          <div className="no-data-message"><p>No broker/demo reconciliation report is available yet.</p></div>
        )}
      </GlassPanel>

      <GlassPanel title="Evidence Chain Health">
        <div className="evidence-health-grid">
          <EvidenceHealth label="Paper Proof Chain" verified={r.chains_verified.paper_proof} detail={`${r.completed_trading_days} days recorded`} />
          <EvidenceHealth label="Paper Decision Chain" verified={r.chains_verified.paper_decision} detail={`${b.latest_decision.decision_count} decisions`} />
          <EvidenceHealth label="Paper Risk Chain" verified={r.chains_verified.paper_risk} detail={`${b.latest_risk.review_count} reviews`} />
          <EvidenceHealth label="WORM Anchoring" verified={false} detail="UNAVAILABLE - local hash chain only" />
        </div>
      </GlassPanel>
    </>
  );
}

function Metric({
  label,
  value,
  mono,
  danger,
  warning,
}: {
  label: string;
  value: string;
  mono?: boolean;
  danger?: boolean;
  warning?: boolean;
}) {
  return (
    <div className="dashboard-metric">
      <span className="field-label">{label}</span>
      <span className={`field-value ${mono ? "mono" : ""}`} style={{ color: danger ? "var(--danger)" : warning ? "var(--warning)" : undefined }}>{value}</span>
    </div>
  );
}

function SummaryRow({ label, value, chip, mono }: { label: string; value: string; chip?: ChipVariant; mono?: boolean }) {
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
