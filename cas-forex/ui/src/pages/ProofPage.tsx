/* ── CAS Forex — Proof Cockpit Page ── */

import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import { LockReasonList } from "../components/LockReasonList";
import { EvidenceHashRow } from "../components/EvidenceHashRow";
import type { DashboardState } from "../types/evidence";

interface ProofPageProps {
  state: DashboardState;
}

export function ProofPage({ state }: ProofPageProps) {
  const { uiReadiness: r, dailySchedule: s, dailyBundle: b } = state;

  return (
    <div className="proof-page">
      {/* ── Active Lead ── */}
      <GlassPanel title="Active Lead" subtitle="Paper-proof candidate">
        <div className="lead-grid">
          <div className="lead-field">
            <span className="field-label">Lead ID</span>
            <span className="field-value mono">{r.lead_id}</span>
          </div>
          <div className="lead-field">
            <span className="field-label">Strategy</span>
            <span className="field-value mono">{r.strategy_setting}</span>
          </div>
          <div className="lead-field">
            <span className="field-label">Timeframe</span>
            <span className="field-value">{r.timeframe}</span>
          </div>
          <div className="lead-field">
            <span className="field-label">Status</span>
            <StatusChip
              label="ACTIVE_RESEARCH_LEAD"
              variant="paper"
              size="sm"
            />
          </div>
        </div>
      </GlassPanel>

      {/* ── Paper Proof Progress ── */}
      <div className="proof-grid-2col">
        <GlassPanel title="Paper Proof Progress">
          <div className="progress-stack">
            <div className="progress-row">
              <span className="progress-label">Paper Days</span>
              <div className="progress-bar-track">
                <div
                  className="progress-bar-fill warning"
                  style={{
                    width: `${(r.completed_trading_days / 30) * 100}%`,
                  }}
                />
              </div>
              <span className="progress-value mono">
                {r.completed_trading_days} / 30
              </span>
            </div>
            <div className="progress-row">
              <span className="progress-label">Multi-Day Bundles</span>
              <div className="progress-bar-track">
                <div
                  className="progress-bar-fill warning"
                  style={{
                    width: `${(r.complete_bundle_days / r.min_daily_bundles_for_ui) * 100}%`,
                  }}
                />
              </div>
              <span className="progress-value mono">
                {r.complete_bundle_days} / {r.min_daily_bundles_for_ui}
              </span>
            </div>
            <div className="progress-row">
              <span className="progress-label">Proof Gate</span>
              <StatusChip
                label={b.latest_proof.passed ? "PASSED" : "NOT PASSED"}
                variant={b.latest_proof.passed ? "success" : "warning"}
                size="sm"
              />
              <span className="progress-detail">
                {b.latest_proof.failure_reasons.join("; ")}
              </span>
            </div>
          </div>
        </GlassPanel>

        <GlassPanel title="Evidence Chain">
          <div className="hash-stack">
            <EvidenceHashRow
              label="Paper Proof Chain"
              value={r.chains_verified.paper_proof ? "VERIFIED" : "FAILED"}
              verified={r.chains_verified.paper_proof}
            />
            <EvidenceHashRow
              label="Paper Decision Chain"
              value={r.chains_verified.paper_decision ? "VERIFIED" : "FAILED"}
              verified={r.chains_verified.paper_decision}
            />
            <EvidenceHashRow
              label="Paper Risk Chain"
              value={r.chains_verified.paper_risk ? "VERIFIED" : "FAILED"}
              verified={r.chains_verified.paper_risk}
            />
            <div
              className="hash-row"
              style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: 8, marginTop: 4 }}
            >
              <span className="hash-row-label">WORM Anchoring</span>
              <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                UNAVAILABLE — local hash chain only
              </span>
            </div>
          </div>
        </GlassPanel>
      </div>

      {/* ── Live Eligibility Checklist ── */}
      <GlassPanel title="Live Eligibility Checklist" variant="danger">
        <div className="checklist-grid">
          <CheckItem
            label="12-month multi-symbol evidence"
            met={false}
            detail="OPEN — not yet accumulated"
          />
          <CheckItem
            label="30 real trading days paper evidence"
            met={false}
            detail={`${r.completed_trading_days} / 30 days complete`}
          />
          <CheckItem
            label="Broker terminal proof"
            met={false}
            detail="MT5 demo receipt only; no live broker proof"
          />
          <CheckItem
            label="Legal / account acknowledgments"
            met={false}
            detail="NOT LICENSED"
          />
          <CheckItem
            label="No pooled / managed account"
            met={false}
            detail="Account type not verified"
          />
          <CheckItem
            label="No active LIVE_LOCKED"
            met={false}
            detail="LIVE_LOCKED active"
          />
          <CheckItem
            label="WORM evidence anchoring"
            met={false}
            detail="UNAVAILABLE"
          />
        </div>
      </GlassPanel>

      {/* ── Day-1 Route Decisions ── */}
      <GlassPanel title="Latest Paper Route Decisions" subtitle={b.latest_decision.latest_decision.date}>
        <div className="route-list">
          {b.latest_decision.latest_decision.symbol_decisions.map((d) => (
            <div key={d.proposal.proposal_id} className="route-card">
              <div className="route-card-header">
                <span className="route-symbol">{d.symbol}</span>
                <StatusChip label={d.direction} variant="info" size="sm" />
                <StatusChip label={d.action} variant="paper" size="sm" />
                <span className="route-confidence mono">
                  conf: {(d.confidence * 100).toFixed(1)}%
                </span>
              </div>
              <div className="route-card-body">
                <div className="route-price-row">
                  <span className="field-label">Entry</span>
                  <span className="field-value mono">
                    {d.proposal.entry_price.toFixed(2)}
                  </span>
                  <span className="field-label">SL</span>
                  <span className="field-value mono" style={{ color: "var(--danger)" }}>
                    {d.proposal.stop_loss.toFixed(2)}
                  </span>
                  <span className="field-label">TP</span>
                  <span className="field-value mono" style={{ color: "var(--success)" }}>
                    {d.proposal.take_profit.toFixed(2)}
                  </span>
                </div>
                <div className="route-rationale">{d.proposal.rationale}</div>
              </div>
            </div>
          ))}
        </div>
      </GlassPanel>

      {/* ── Risk Sizing ── */}
      <GlassPanel title="Paper Risk Sizing" subtitle={`Equity: $${b.latest_risk.latest_review.account_equity.toLocaleString()}`}>
        <div className="sizing-grid">
          {b.latest_risk.latest_review.sizing.map((sz) => (
            <div key={sz.proposal_id} className="sizing-card">
              <div className="sizing-header">
                <span className="route-symbol">{sz.symbol}</span>
                <StatusChip
                  label={sz.attempt_status}
                  variant={sz.attempt_status === "PAPER_ATTEMPT_ALLOWED" ? "info" : "warning"}
                  size="sm"
                />
              </div>
              <div className="sizing-body">
                <div className="sizing-row">
                  <span className="field-label">Lots</span>
                  <span className="field-value mono">{sz.sized_lots}</span>
                </div>
                <div className="sizing-row">
                  <span className="field-label">Risk/Trade</span>
                  <span className="field-value mono">
                    ${sz.planned_risk_usd.toFixed(2)} ({sz.planned_risk_pct.toFixed(2)}%)
                  </span>
                </div>
                <div className="sizing-row">
                  <span className="field-label">Max Risk</span>
                  <span className="field-value mono">${sz.max_risk_usd.toFixed(2)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
        <div className="risk-summary">
          <span className="field-label">
            Attempts: {b.latest_risk.latest_review.proposed_attempts} proposed /{" "}
            {b.latest_risk.latest_review.max_paper_attempts} max
          </span>
          <span className="field-label" style={{ marginLeft: 16 }}>
            Daily Budget: ${b.latest_risk.latest_review.daily_risk_budget_usd.toFixed(2)} (
            {b.latest_risk.latest_review.daily_risk_budget_pct}%)
          </span>
        </div>
      </GlassPanel>

      {/* ── Next Action ── */}
      <GlassPanel title="Next Action" variant="info">
        <div className="next-action">
          <div className="next-action-meta">
            <span className="field-label">Next Due Date</span>
            <span className="field-value mono">{s.next_due_date}</span>
            <StatusChip
              label={s.next_due_status}
              variant="warning"
              size="sm"
            />
          </div>
          <div className="next-action-command mono">
            {s.recommended_command}
          </div>
          <LockReasonList
            title="Missing Tracks for Next Due Date"
            items={s.missing_tracks_for_next_due}
            variant="warning"
          />
        </div>
      </GlassPanel>

      {/* ── Capital / Backsolve Summary ── */}
      {state.backsolve && (
        <GlassPanel title="Capital & Backsolve" subtitle={`${state.backsolve.total_scenarios.toLocaleString()} scenarios — ${state.backsolve.ai_autonomy_mode}`} variant="warning">
          <div className="backsolve-summary">
            <div className="dashboard-grid-3col">
              <div className="metric-stack">
                <Metric label="Seed Capital" value="$5,000" mono />
                <Metric label="Target Income" value="$5K-$12K/month" />
                <Metric label="Required Return" value={`${state.backsolve.required_return_math.target_5k_on_5k_pct}%-${state.backsolve.required_return_math.target_12k_on_5k_pct}%`} mono />
              </div>
              <div className="metric-stack">
                <Metric label="Total Scenarios" value={state.backsolve.total_scenarios.toLocaleString()} mono />
                <Metric label="Viable" value={`${state.backsolve.viable_scenarios}`} mono danger={state.backsolve.viable_scenarios === 0} />
                <Metric label="AI Selection" value={state.backsolve.ai_selection ?? "NONE"} mono />
              </div>
              <div className="metric-stack">
                <Metric label="Target Not Reached" value={state.backsolve.verdict_counts.TARGET_NOT_REACHED?.toLocaleString() ?? "—"} mono />
                <Metric label="Drawdown Fail" value={state.backsolve.verdict_counts.TARGET_REACHED_BUT_DRAWDOWN_FAIL?.toLocaleString() ?? "—"} mono />
                <Metric label="Margin Fail" value={state.backsolve.verdict_counts.TARGET_REACHED_BUT_MARGIN_FAIL?.toLocaleString() ?? "—"} mono />
              </div>
            </div>
            <div style={{ marginTop: 8, padding: "6px 10px", background: "var(--danger-dim)", borderRadius: "var(--radius-sm)", fontSize: "0.72rem", color: "var(--danger)" }}>
              {state.backsolve.capital_label}: $5K-$12K/month from $5K seed requires 100%-240% monthly return. Current D1 evidence baseline is $32.93/month. Leverage changes margin; it does not create edge.
            </div>
          </div>
        </GlassPanel>
      )}

      {/* ── MT5 Demo Receipt ── */}
      {state.mt5Receipt && (
        <GlassPanel title="MT5 Demo Receipt" subtitle={`${state.mt5Receipt.server} — ${state.mt5Receipt.trading_date}`} variant="info">
          <div className="receipt-detail">
            <div className="receipt-grid">
              <div className="receipt-field">
                <span className="field-label">Status</span>
                <StatusChip label={state.mt5Receipt.receipt_validation_status} variant="success" size="sm" />
              </div>
              <div className="receipt-field">
                <span className="field-label">Broker API</span>
                <StatusChip label={state.mt5Receipt.broker_api_authenticated ? "AUTHENTICATED" : "NOT AUTH"} variant={state.mt5Receipt.broker_api_authenticated ? "success" : "danger"} size="sm" />
              </div>
              <div className="receipt-field">
                <span className="field-label">Chain</span>
                <StatusChip label={state.mt5Receipt.chain_verified ? "VERIFIED" : "FAILED"} variant={state.mt5Receipt.chain_verified ? "success" : "danger"} size="sm" />
              </div>
              <div className="receipt-field">
                <span className="field-label">WORM</span>
                <span style={{ color: "var(--text-muted)", fontSize: "0.72rem" }}>{state.mt5Receipt.worm_retained ? "RETAINED" : "UNAVAILABLE"}</span>
              </div>
              <div className="receipt-field">
                <span className="field-label">Live Mode</span>
                <span className="field-value mono" style={{ color: "var(--danger)" }}>{String(state.mt5Receipt.live_mode)}</span>
              </div>
              <div className="receipt-field">
                <span className="field-label">Positions Reconciled</span>
                <span className="field-value mono">{String(state.mt5Receipt.open_positions_reconciled)}</span>
              </div>
            </div>
            <div className="receipt-hashes">
              <div className="hash-row"><span className="field-label">Receipt Hash</span><code className="hash-row-value" style={{ fontSize: "0.62rem" }}>{state.mt5Receipt.receipt_hash_sha256.slice(0, 24)}...</code></div>
              <div className="hash-row"><span className="field-label">Broker Export</span><code className="hash-row-value" style={{ fontSize: "0.62rem" }}>{state.mt5Receipt.broker_export_sha256.slice(0, 24)}...</code></div>
              <div className="hash-row"><span className="field-label">Packet Hash</span><code className="hash-row-value" style={{ fontSize: "0.62rem" }}>{state.mt5Receipt.packet_hash.slice(0, 24)}...</code></div>
            </div>
          </div>
        </GlassPanel>
      )}

      {/* ── Walk-Forward Summary ── */}
      {state.walkForward && (
        <GlassPanel title="Walk-Forward Evidence" subtitle={`${state.walkForward.run_id} — ${state.walkForward.research_grade}`} variant="info">
          <div className="wf-summary">
            <div className="dashboard-grid-3col">
              <div className="metric-stack">
                <Metric label="Total Windows" value={`${state.walkForward.total_windows}`} mono />
                <Metric label="Routed" value={`${state.walkForward.routed_windows}`} mono />
                <Metric label="Active Routed" value={`${state.walkForward.active_routed_windows}`} mono />
              </div>
              <div className="metric-stack">
                <Metric label="Positive Active" value={`${state.walkForward.positive_active_routed_windows} / ${state.walkForward.active_routed_windows}`} mono />
                <Metric label="Mean Return" value={`${state.walkForward.active_routed_mean_return_pct.toFixed(2)}%`} mono />
                <Metric label="Max DD" value={`${state.walkForward.routed_max_drawdown_pct.toFixed(2)}%`} mono />
              </div>
              <div className="metric-stack">
                <Metric label="Routed Return" value={`${state.walkForward.routed_total_return_pct.toFixed(2)}%`} mono />
                <Metric label="Total Trades" value={`${state.walkForward.total_routed_trades}`} mono />
                <Metric label="Symbols" value={state.walkForward.symbols.join(", ")} />
              </div>
            </div>
            <div className="wf-grade">
              <StatusChip label={`Grade: ${state.walkForward.research_grade}`} variant="warning" size="sm" />
              <span className="text-muted-italic" style={{ marginLeft: 8 }}>{state.walkForward.claim_boundary}</span>
            </div>
          </div>
        </GlassPanel>
      )}

      {/* ── NOT LICENSED Controls ── */}
      <GlassPanel title="Live & Payment Controls" variant="danger">
        <div className="not-licensed-grid">
          <DisabledControl
            label="Deployment"
            reason="NOT LICENSED — paper proof incomplete"
          />
          <DisabledControl
            label="Broker ACCEPT"
            reason="NOT LICENSED — no live broker connection authorized"
          />
          <DisabledControl
            label="Auto-Deposit"
            reason="NOT LICENSED — payment movement not authorized"
          />
          <DisabledControl
            label="Debit / Card / Bank"
            reason="NOT LICENSED — transfer not authorized"
          />
          <DisabledControl
            label="Payout Automation"
            reason="NOT LICENSED — sweep/payout not authorized"
          />
          <DisabledControl
            label="Live Trading"
            reason="NOT LICENSED — 1/30 paper days, edge OPEN"
          />
        </div>
      </GlassPanel>
    </div>
  );
}

/* ── Helpers ── */

function Metric({ label, value, mono, danger }: { label: string; value: string; mono?: boolean; danger?: boolean }) {
  return (
    <div className="dashboard-metric">
      <span className="field-label">{label}</span>
      <span className={`field-value ${mono ? "mono" : ""}`} style={{ color: danger ? "var(--danger)" : undefined }}>{value}</span>
    </div>
  );
}

function CheckItem({
  label,
  met,
  detail,
}: {
  label: string;
  met: boolean;
  detail: string;
}) {
  return (
    <div className="check-item">
      <span
        className="check-icon"
        style={{ color: met ? "var(--success)" : "var(--danger)" }}
      >
        {met ? "✓" : "✗"}
      </span>
      <div>
        <div className="check-label">{label}</div>
        <div className="check-detail">{detail}</div>
      </div>
    </div>
  );
}

function DisabledControl({
  label,
  reason,
}: {
  label: string;
  reason: string;
}) {
  return (
    <div className="disabled-control">
      <div className="disabled-control-header">
        <span className="disabled-control-label">{label}</span>
        <StatusChip label="DISABLED" variant="danger" size="sm" />
      </div>
      <div className="disabled-control-reason">{reason}</div>
    </div>
  );
}
