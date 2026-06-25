/* ── CAS Forex — Operations Dashboard ── */

import { useEffect, useState } from "react";
import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import { SparkChart } from "../components/charts/SparkChart";
import { OperatorBriefingCard } from "../components/OperatorBriefingCard";
import { applyBrokerSyncedRiskReview, fetchBrokerSyncedRiskPreview, fetchLiveReadiness } from "../data/api";
import type { BrokerSyncedRiskPreview, DashboardState, LiveReadinessCheck, LiveReadinessReport } from "../types/evidence";

interface DashboardPageProps {
  state: DashboardState;
}

export function DashboardPage({ state }: DashboardPageProps) {
  const { uiReadiness: r, dailySchedule: s, dailyBundle: b } = state;
  const risk = b.latest_risk.latest_review;
  const decision = b.latest_decision.latest_decision;
  const account = state.accountLedger?.summary;
  const movement = state.movementStream;
  const recon = state.accountReconciliation;
  const liveReadiness = state.liveReadiness;
  const [readinessMode, setReadinessMode] = useState<"default" | "broker-sync">("default");
  const [brokerSyncedReadiness, setBrokerSyncedReadiness] = useState<LiveReadinessReport | null>(null);
  const [brokerSyncedRiskPreview, setBrokerSyncedRiskPreview] = useState<BrokerSyncedRiskPreview | null>(null);
  const [brokerRiskApplyResult, setBrokerRiskApplyResult] = useState<BrokerSyncedRiskPreview | null>(null);
  const [brokerRiskApplying, setBrokerRiskApplying] = useState(false);
  const [brokerSyncLoading, setBrokerSyncLoading] = useState(false);
  const dashboardBrokerSyncedRiskPreview = state.brokerSyncedRiskPreview ?? null;

  useEffect(() => {
    if (readinessMode !== "broker-sync" || brokerSyncedReadiness) return;
    let cancelled = false;
    setBrokerSyncLoading(true);
    fetchLiveReadiness(true)
      .then((payload) => {
        if (!cancelled && payload) setBrokerSyncedReadiness(payload);
      })
      .finally(() => {
        if (!cancelled) setBrokerSyncLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [brokerSyncedReadiness, readinessMode]);

  useEffect(() => {
    if (readinessMode !== "broker-sync" || brokerSyncedRiskPreview || dashboardBrokerSyncedRiskPreview) return;
    let cancelled = false;
    fetchBrokerSyncedRiskPreview().then((payload) => {
      if (!cancelled && payload) setBrokerSyncedRiskPreview(payload);
    });
    return () => {
      cancelled = true;
    };
  }, [brokerSyncedRiskPreview, dashboardBrokerSyncedRiskPreview, readinessMode]);

  const activeLiveReadiness =
    readinessMode === "broker-sync" ? brokerSyncedReadiness ?? liveReadiness : liveReadiness;
  const activeBrokerRiskPreview = brokerSyncedRiskPreview ?? dashboardBrokerSyncedRiskPreview;
  const brokerSyncUnavailable =
    readinessMode === "broker-sync" && !brokerSyncLoading && brokerSyncedReadiness == null;

  async function handleApplyBrokerRiskReview() {
    if (brokerRiskApplying) return;
    setBrokerRiskApplying(true);
    const result = await applyBrokerSyncedRiskReview();
    if (result) {
      setBrokerRiskApplyResult(result);
      setBrokerSyncedRiskPreview(result);
      const refreshed = await fetchLiveReadiness(true);
      if (refreshed) setBrokerSyncedReadiness(refreshed);
    }
    setBrokerRiskApplying(false);
  }

  return (
    <div className="dashboard-page">
      {/* ── Operator Briefing (live one-call snapshot) ── */}
      <OperatorBriefingCard />

      {/* ── Account Snapshot ── */}
      <div className="dashboard-grid-3col">
        <GlassPanel title="Account" variant="info">
          <div className="metric-stack">
            <Metric label="Deposit" value={`$${(account?.deposit_usd ?? risk.account_equity).toLocaleString()}`} />
            <Metric label="Balance" value={`$${(account?.balance_usd ?? risk.account_equity).toLocaleString()}`} />
            <Metric label="Equity" value={`$${(account?.equity_usd ?? risk.account_equity).toLocaleString()}`} />
            <Metric label="Live" value="NOT LICENSED" danger />
          </div>
        </GlassPanel>

        <GlassPanel title="Risk Budget">
          <div className="metric-stack">
            <Metric label="Realized P/L" value={`$${(account?.realized_pnl_usd ?? 0).toFixed(2)}`} />
            <Metric label="Floating P/L" value={`$${(account?.floating_pnl_usd ?? 0).toFixed(2)}`} />
            <Metric label="Margin / Free" value={`$${(account?.margin_used_usd ?? 0).toFixed(0)} / $${(account?.free_margin_usd ?? risk.account_equity).toFixed(0)}`} mono />
            <Metric label="Planned Risk" value={`$${(account?.planned_risk_usd ?? risk.sizing.reduce((sum, row) => sum + row.planned_risk_usd, 0)).toFixed(2)}`} mono />
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



      <GlassPanel title="Real-Time Movement Scaffold" subtitle="paper/demo account + market movement now; live providers later after gates">
        <div className="dashboard-grid-3col">
          <div className="metric-stack" style={{ padding: 0 }}>
            <Metric label="Stream Mode" value={movement?.mode ?? "PAPER_DEMO_REALTIME_SCAFFOLD"} mono />
            <Metric label="Symbols" value={movement?.symbols.join(", ") ?? "—"} mono />
            <Metric label="Updated" value={movement?.timestamp ?? "—"} mono />
          </div>
          <div className="metric-stack" style={{ padding: 0 }}>
            <Metric label="Balance" value={`$${(movement?.account.balance_usd ?? account?.balance_usd ?? risk.account_equity).toFixed(2)}`} mono />
            <Metric label="Equity" value={`$${(movement?.account.equity_usd ?? account?.equity_usd ?? risk.account_equity).toFixed(2)}`} mono />
            <Metric label="Floating P/L" value={`$${(movement?.account.floating_pnl_usd ?? 0).toFixed(2)}`} mono warning={(movement?.account.floating_pnl_usd ?? 0) === 0} danger={(movement?.account.floating_pnl_usd ?? 0) < 0} />
          </div>
          <div className="metric-stack" style={{ padding: 0 }}>
            <Metric label="Margin / Free" value={`$${(movement?.account.margin_used_usd ?? 0).toFixed(2)} / $${(movement?.account.free_margin_usd ?? 0).toFixed(2)}`} mono />
            <Metric label="Drawdown" value={`$${(movement?.account.drawdown_usd ?? 0).toFixed(2)} (${(movement?.account.drawdown_pct ?? 0).toFixed(3)}%)`} mono />
            <Metric label="Boundary" value="NOT LICENSED" danger />
          </div>
        </div>
        {movement && movement.quotes.length > 0 && (
          <div className="positions-table-wrap" style={{ marginTop: 12 }}>
            <table className="data-table">
              <thead>
                <tr><th>Symbol</th><th>Bid</th><th>Ask</th><th>Spread</th><th>ATR</th><th>Session</th><th>Source</th></tr>
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
                    <td className="mono" style={{ fontSize: "0.66rem" }}>{q.source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassPanel>

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



      {/* ── Broker/Demo Reconciliation ── */}
      <GlassPanel title="Broker/Demo Account Reconciliation" subtitle={recon ? `${recon.overall_status} — ${recon.checks_ok}/${recon.checks_total} OK, ${recon.checks_mismatch} mismatch, ${recon.checks_unverifiable} unverifiable` : "No reconciliation report"}>
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
                <Metric label="Receipt" value={recon.broker_receipt_validation_status ?? "—"} mono />
                <Metric label="Broker Sync" value={recon.sync_to_broker_snapshot ? "PREVIEW" : "OFF"} mono warning={!!recon.sync_to_broker_snapshot} />
                <Metric label="Edge" value={recon.trading_edge_status} warning />
              </div>
            </div>
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
      <GlassPanel
        title="Live Operability Checklist"
        subtitle={activeLiveReadiness ? activeLiveReadiness.plain_english_summary : "Computed gate report unavailable"}
        variant={activeLiveReadiness?.overall_status === "READY_FOR_LIVE_EXECUTION" ? "info" : "danger"}
      >
        {activeLiveReadiness ? (
          <>
            <div className="readiness-mode-row">
              <div className="readiness-mode-switch" role="tablist" aria-label="Live readiness mode">
                <button
                  className={`readiness-mode-button ${readinessMode === "default" ? "active" : ""}`}
                  type="button"
                  role="tab"
                  aria-selected={readinessMode === "default"}
                  onClick={() => setReadinessMode("default")}
                >
                  Default
                </button>
                <button
                  className={`readiness-mode-button ${readinessMode === "broker-sync" ? "active" : ""}`}
                  type="button"
                  role="tab"
                  aria-selected={readinessMode === "broker-sync"}
                  onClick={() => setReadinessMode("broker-sync")}
                >
                  Broker Sync
                </button>
              </div>
              {brokerSyncLoading && <span className="readiness-mode-note">Loading broker snapshot...</span>}
              {brokerSyncUnavailable && <span className="readiness-mode-note">Broker sync preview unavailable</span>}
            </div>
            <div className="dashboard-grid-3col" style={{ marginBottom: 10 }}>
              <div className="metric-stack" style={{ padding: 0 }}>
                <Metric label="Overall" value={activeLiveReadiness.overall_status} mono danger={activeLiveReadiness.overall_status !== "READY_FOR_LIVE_EXECUTION"} />
                <Metric label="Passed" value={`${activeLiveReadiness.checks_passed}/${activeLiveReadiness.checks_total}`} mono />
                <Metric label="Trading Edge" value={activeLiveReadiness.trading_edge_status} warning />
              </div>
              <div className="metric-stack" style={{ padding: 0 }}>
                <Metric label="Open" value={`${activeLiveReadiness.checks_open}`} mono warning={activeLiveReadiness.checks_open > 0} />
                <Metric label="Mismatch" value={`${activeLiveReadiness.checks_mismatch}`} mono danger={activeLiveReadiness.checks_mismatch > 0} />
                <Metric label="Unverifiable" value={`${activeLiveReadiness.checks_unverifiable}`} mono warning={activeLiveReadiness.checks_unverifiable > 0} />
              </div>
              <div className="metric-stack" style={{ padding: 0 }}>
                <Metric label="Live Trading" value={activeLiveReadiness.live_trading_status} mono danger={activeLiveReadiness.live_trading_status !== "AUTHORIZED"} />
                <Metric label="Broker ACCEPT" value={activeLiveReadiness.broker_accept_status} mono danger={activeLiveReadiness.broker_accept_status !== "AUTHORIZED"} />
                <Metric label="Broker Seed" value={activeLiveReadiness.sync_to_broker_snapshot ? `$${(activeLiveReadiness.broker_snapshot_initial_investment_usd ?? 0).toLocaleString()}` : "OFF"} mono warning={!!activeLiveReadiness.sync_to_broker_snapshot} />
                <Metric label="Payment Movement" value={activeLiveReadiness.payment_movement_authorized ? "AUTHORIZED" : "CURRENTLY NOT LICENSED"} mono danger={!activeLiveReadiness.payment_movement_authorized} />
              </div>
            </div>
            {readinessMode === "broker-sync" && activeBrokerRiskPreview && (
              <div className="broker-risk-preview">
                <div className="broker-risk-preview-header">
                  <span>Broker-Synced Paper Risk Preview</span>
                  <div className="broker-risk-preview-actions">
                    <StatusChip label={activeBrokerRiskPreview.risk_status} variant="paper" size="sm" />
                    <button
                      className="broker-risk-apply-button"
                      type="button"
                      onClick={handleApplyBrokerRiskReview}
                      disabled={brokerRiskApplying || activeBrokerRiskPreview.already_applied === true}
                    >
                      {brokerRiskApplying ? "Applying..." : activeBrokerRiskPreview.already_applied ? "Applied" : "Apply"}
                    </button>
                  </div>
                </div>
                <div className="dashboard-grid-3col">
                  <div className="metric-stack" style={{ padding: 0 }}>
                    <Metric label="Broker Seed" value={`$${activeBrokerRiskPreview.broker_snapshot_initial_investment_usd.toLocaleString()}`} mono warning />
                    <Metric label="Default Seed" value={`$${activeBrokerRiskPreview.default_risk_review_account_equity_usd.toLocaleString()}`} mono />
                  </div>
                  <div className="metric-stack" style={{ padding: 0 }}>
                    <Metric label="Preview Lots" value={`${activeBrokerRiskPreview.total_planned_lots.toFixed(2)} lots`} mono />
                    <Metric label="Default Lots" value={`${activeBrokerRiskPreview.default_total_planned_lots.toFixed(2)} lots`} mono />
                  </div>
                  <div className="metric-stack" style={{ padding: 0 }}>
                    <Metric label="Preview Risk" value={`$${activeBrokerRiskPreview.total_planned_risk_usd.toFixed(2)}`} mono />
                    <Metric label="Risk Delta" value={`$${activeBrokerRiskPreview.delta_vs_default.total_planned_risk_usd.toFixed(2)}`} mono warning />
                  </div>
                </div>
                <div className="broker-risk-preview-note">{activeBrokerRiskPreview.next_action}</div>
                {brokerRiskApplyResult && (
                  <div className="broker-risk-apply-result">
                    {brokerRiskApplyResult.evidence_appended
                      ? `Evidence appended to ${brokerRiskApplyResult.paper_risk_status_path ?? "paper-risk-status.json"}`
                      : brokerRiskApplyResult.already_applied
                        ? "Broker-synced paper risk is already the latest active review."
                        : "Apply request did not append evidence."}
                  </div>
                )}
              </div>
            )}
            <div className="gate-grid">
              {activeLiveReadiness.checks.map((check) => (
                <GateItem key={check.gate_id} check={check} />
              ))}
            </div>
            {activeLiveReadiness.next_actions.length > 0 && (
              <div className="next-command" style={{ marginTop: 12 }}>
                <code className="next-command-text">{activeLiveReadiness.next_actions[0]}</code>
              </div>
            )}
          </>
        ) : (
          <div className="no-data-message"><p>Live operability checklist is not available in the dashboard payload.</p></div>
        )}
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

function GateItem({ check }: { check: LiveReadinessCheck }) {
  return (
    <div className="gate-item">
      <div className="gate-item-header">
        <span className="gate-item-label">{check.label}</span>
        <StatusChip label={displayGateStatus(check.status)} variant={gateVariant(check.status)} size="sm" />
      </div>
      <div className="gate-item-detail">{check.plain_english}</div>
      {check.next_action && <div className="gate-item-next">{check.next_action}</div>}
    </div>
  );
}

function displayGateStatus(status: string): string {
  return status === "CURRENTLY NOT LICENSED" ? "NOT LICENSED" : status;
}

function gateVariant(status: string): "success" | "warning" | "danger" | "info" | "muted" | "paper" {
  if (status === "PASSED" || status === "AUTHORIZED") return "success";
  if (status === "OPEN" || status === "UNVERIFIABLE") return "warning";
  if (status === "CURRENTLY NOT LICENSED" || status === "MISMATCH") return "danger";
  return "muted";
}
