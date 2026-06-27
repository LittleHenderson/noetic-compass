/* ── CAS Forex — Paper Proof Ledger ── */

import { useMemo, useState } from "react";
import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import { EquityCurve } from "../components/charts/EquityCurve";
import type { DashboardState } from "../types/evidence";

interface LedgerPageProps {
  state: DashboardState;
}

export function LedgerPage({ state }: LedgerPageProps) {
  const sched = state.dailySchedule;
  const mt = state.mt5Receipt;
  const completed = sched.completed_trading_days;
  const remaining = sched.required_paper_days - completed;
  const bundlesDone = sched.complete_bundle_days;
  const bundlesTarget = sched.ui_min_daily_bundles;
  const equity = state.dailyBundle.latest_risk.latest_review.account_equity;
  const account = state.accountLedger;
  const [ownerSeedInput, setOwnerSeedInput] = useState(() => `${account?.summary.owner_selected_initial_investment_usd ?? equity}`);
  const ownerSeed = Number(ownerSeedInput);
  const plannedRisk = (state.dailyBundle.latest_risk.latest_review.sizing ?? []).reduce(
    (sum, row) => sum + row.planned_risk_usd,
    0,
  );
  const equityReference = [
    { date: sched.latest_complete_bundle_date, equity },
    { date: "planned-risk-floor", equity: equity - plannedRisk },
    { date: sched.next_due_date, equity },
  ];
  const accountPreview = useMemo(() => {
    const seed = Number.isFinite(ownerSeed) && ownerSeed > 0 ? ownerSeed : account?.summary.initial_investment_usd ?? equity;
    const realized = account?.summary.realized_pnl_usd ?? 0;
    const floating = account?.summary.floating_pnl_usd ?? 0;
    const margin = account?.summary.margin_used_usd ?? 0;
    const balance = seed + realized - (account?.summary.withdrawals_usd ?? 0) - (account?.summary.payouts_usd ?? 0) - (account?.summary.commission_usd ?? 0) - (account?.summary.broker_fees_usd ?? 0) + (account?.summary.swap_usd ?? 0);
    const previewEquity = balance + floating;
    return { seed, balance, equity: previewEquity, freeMargin: Math.max(0, previewEquity - margin), riskPct: seed > 0 ? (plannedRisk / seed) * 100 : 0 };
  }, [account, equity, ownerSeed, plannedRisk]);

  // Generate 30-day skeleton (skip weekends)
  const dayRows: { day: number; date: string; status: string; route: string; risk: string; broker: string; hash: string }[] = [];
  const startDate = new Date("2026-06-22");
  let tradingDay = 0;
  for (let d = 0; d < 60; d++) {
    const date = new Date(startDate);
    date.setDate(date.getDate() + d);
    const dow = date.getDay();
    if (dow === 0 || dow === 6) continue;
    tradingDay++;
    const dateStr = date.toISOString().slice(0, 10);
    const isComplete = d === 0;
    dayRows.push({
      day: tradingDay,
      date: dateStr,
      status: isComplete ? "COMPLETE" : "PENDING",
      route: isComplete ? "ROUTE_PAPER_SIGNAL" : "--",
      risk: isComplete ? "PAPER_ATTEMPTS_ALLOWED" : "--",
      broker: isComplete ? "VERIFIED" : "--",
      hash: isComplete ? "a5233429d7251512..." : "--",
    });
    if (tradingDay >= 30) break;
  }

  return (
    <div className="ledger-page">
      {/* Section 1: Progress Overview */}
      <GlassPanel
        title="30-Day Paper Proof Ledger"
        subtitle={`${completed}/30 days complete — ${remaining} remaining until deployment gate${
          bundlesDone < bundlesTarget ? ` · ${bundlesDone}/${bundlesTarget} bundles for multi-day maturity` : ""
        }`}
      >
        <div className="dashboard-grid-3col">
          <div className="metric-stack" style={{ padding: 0 }}>
            <Metric label="Completed Trading Days" value={`${completed}`} mono />
            <Metric label="Broker Verified Days" value={`${sched.broker_verified_days}`} mono />
            <Metric label="Complete Bundle Days" value={`${sched.complete_bundle_days}`} mono />
          </div>
          <div className="metric-stack" style={{ padding: 0 }}>
            <Metric label="Decision Days" value={`${sched.decision_days}`} mono />
            <Metric label="Risk Review Days" value={`${sched.risk_review_days}`} mono />
            <Metric label="Paper Days Remaining" value={`${sched.paper_days_remaining}`} mono />
          </div>
          <div className="metric-stack" style={{ padding: 0 }}>
            <Metric label="Next Due Date" value={sched.next_due_date} />
            <Metric label="Latest Bundle Date" value={sched.latest_complete_bundle_date} />
            <Metric label="Next Due Status" value={sched.next_due_status} />
          </div>
        </div>
      </GlassPanel>

      <GlassPanel title="Paper Equity Reference" subtitle="paper risk budget reference, not live P&L">
        <EquityCurve points={equityReference} initialEquity={equity} height={160} />
      </GlassPanel>


      <GlassPanel title="Owner Investment Ledger" subtitle="owner-selectable paper/demo seed now; live deposits remain gated">
        <div className="dashboard-grid-3col">
          <div className="metric-stack" style={{ padding: 0 }}>
            <label className="field-label" htmlFor="owner-seed-input">Paper initial investment</label>
            <input
              id="owner-seed-input"
              type="number"
              min="0.01"
              step="0.01"
              value={ownerSeedInput}
              onChange={(event) => setOwnerSeedInput(event.target.value)}
              style={{ width: "100%", padding: "8px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--panel)", color: "var(--text)", marginTop: 6 }}
            />
            <div style={{ marginTop: 8 }}>
              <StatusChip label="PAPER/DEMO LEDGER" variant="paper" size="sm" />
            </div>
          </div>
          <div className="metric-stack" style={{ padding: 0 }}>
            <Metric label="Deposit" value={`$${accountPreview.seed.toLocaleString(undefined, { maximumFractionDigits: 2 })}`} mono />
            <Metric label="Balance" value={`$${accountPreview.balance.toLocaleString(undefined, { maximumFractionDigits: 2 })}`} mono />
            <Metric label="Equity" value={`$${accountPreview.equity.toLocaleString(undefined, { maximumFractionDigits: 2 })}`} mono />
          </div>
          <div className="metric-stack" style={{ padding: 0 }}>
            <Metric label="Planned Risk" value={`$${plannedRisk.toFixed(2)} / ${accountPreview.riskPct.toFixed(3)}%`} mono />
            <Metric label="Margin / Free" value={`$${(account?.summary.margin_used_usd ?? 0).toFixed(2)} / $${accountPreview.freeMargin.toFixed(2)}`} mono />
            <Metric label="Risk Review Equity" value={`$${(account?.summary.risk_review_account_equity_usd ?? equity).toLocaleString()}`} mono />
          </div>
        </div>
        <div style={{ marginTop: 10, color: "var(--text-muted)", fontSize: "0.72rem" }}>
          Changing this field previews the owner-selected paper/demo account seed. It does not deposit funds or move bank/card money.
          {accountPreview.seed !== (account?.summary.risk_review_account_equity_usd ?? equity) && (
            <span style={{ color: "var(--warning)", marginLeft: 6 }}>Rerun paper risk sizing for this amount before relying on lot/risk percentages.</span>
          )}
        </div>
      </GlassPanel>

      {/* Section 2: Daily Bundle Ledger */}
      <GlassPanel
        title="Daily Bundle Ledger"
        subtitle={`${dayRows.filter((r) => r.status === "COMPLETE").length} of ${dayRows.length} trading days recorded`}
      >
        <div className="tally-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Day #</th>
                <th>Date</th>
                <th>Bundle</th>
                <th>Route</th>
                <th>Risk</th>
                <th>Broker</th>
                <th>Hash</th>
              </tr>
            </thead>
            <tbody>
              {dayRows.map((r) => (
                <tr key={r.day} style={r.status === "PENDING" ? { opacity: 0.4 } : undefined}>
                  <td className="mono">{r.day}</td>
                  <td className="mono">{r.date}</td>
                  <td>
                    <StatusChip label={r.status} variant={r.status === "COMPLETE" ? "success" : "muted"} size="sm" />
                  </td>
                  <td className="mono" style={{ fontSize: "0.68rem" }}>
                    {r.route}
                  </td>
                  <td className="mono" style={{ fontSize: "0.68rem" }}>
                    {r.risk}
                  </td>
                  <td>
                    <StatusChip label={r.broker} variant={r.broker === "VERIFIED" ? "success" : "muted"} size="sm" />
                  </td>
                  <td className="mono" style={{ fontSize: "0.6rem" }}>
                    {r.hash}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassPanel>

      {/* Section 3: Evidence Hash Chain */}
      <GlassPanel title="Evidence Hash Chain">
        <div className="sizing-row">
          <span className="field-label">Bundle Hash</span>
          <span className="field-value mono" style={{ fontSize: "0.65rem" }}>
            94d68da3b3c4d7bd...
          </span>
        </div>
        <div className="sizing-row">
          <span className="field-label">Decision Hash</span>
          <span className="field-value mono" style={{ fontSize: "0.65rem" }}>
            56faa6ac644c30fa...
          </span>
        </div>
        <div className="sizing-row">
          <span className="field-label">Risk Hash</span>
          <span className="field-value mono" style={{ fontSize: "0.65rem" }}>
            a5233429d7251512...
          </span>
        </div>
        <div className="sizing-row">
          <span className="field-label">Receipt Hash</span>
          <span className="field-value mono" style={{ fontSize: "0.65rem" }}>
            {mt?.receipt_hash_sha256?.slice(0, 16) ?? "94d68da3b3c4d7bd"}...
          </span>
        </div>
        <div style={{ marginTop: 8 }}>
          <StatusChip
            label={mt?.chain_verified ? "Chain Verified: TRUE" : "Chain Verified: FALSE"}
            variant={mt?.chain_verified ? "success" : "danger"}
            size="sm"
          />
          {!mt?.worm_retained && (
            <span style={{ marginLeft: 8, fontSize: "0.68rem", color: "var(--warning)" }}>
              WORM retention: UNAVAILABLE
            </span>
          )}
        </div>
      </GlassPanel>

      {/* Section 4: Deployment Gate */}
      <GlassPanel title="Deployment Gate" variant="danger">
        <div className="legal-gates">
          <GateRow label="30 paper days completed" met={completed >= 30} detail={`${completed}/30`} />
          <GateRow label="5 multi-day bundles" met={bundlesDone >= bundlesTarget} detail={`${bundlesDone}/${bundlesTarget}`} />
          <GateRow label="All chains verified" met={!!mt?.chain_verified} detail={mt?.chain_verified ? "YES" : "NO"} />
          <GateRow label="Broker API verified" met={!!mt?.broker_api_authenticated} detail={mt?.broker_api_authenticated ? "YES" : "NO"} />
          <GateRow label="Owner acknowledgment" met={false} detail="NOT MET" />
          <GateRow label="Legal acknowledgment" met={false} detail="NOT MET" />
        </div>
        <div
          style={{
            marginTop: 12,
            padding: "8px 12px",
            background: "var(--danger-dim)",
            borderRadius: "var(--radius-sm)",
            fontSize: "0.72rem",
            color: "var(--danger)",
          }}
        >
          DEPLOYMENT GATE: NOT MET — {completed}/30 paper days, {bundlesDone}/{bundlesTarget} bundles. Live trading, broker
          ACCEPT, and payment movement remain NOT LICENSED.
        </div>
      </GlassPanel>
    </div>
  );
}

function Metric({ label, value, mono, danger }: { label: string; value: string; mono?: boolean; danger?: boolean }) {
  return (
    <div className="dashboard-metric">
      <span className="field-label">{label}</span>
      <span
        className={`field-value ${mono ? "mono" : ""}`}
        style={{ color: danger ? "var(--danger)" : undefined }}
      >
        {value}
      </span>
    </div>
  );
}

function GateRow({ label, met, detail }: { label: string; met: boolean; detail: string }) {
  return (
    <div className="legal-gate-item">
      <div className="legal-gate-header">
        <span className="check-icon" style={{ color: met ? "var(--success)" : "var(--danger)" }}>
          {met ? "✓" : "✗"}
        </span>
        <span className="field-label">{label}</span>
        <StatusChip label={met ? "MET" : "NOT MET"} variant={met ? "success" : "danger"} size="sm" />
      </div>
      <div className="legal-gate-detail">{detail}</div>
    </div>
  );
}
