/* ── CAS Forex — History & MT Import ── */

import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import type { DashboardState } from "../types/evidence";

interface HistoryPageProps {
  state: DashboardState;
}

export function HistoryPage({ state }: HistoryPageProps) {
  const mt = state.mtHistory;
  const account = state.accountLedger;

  return (
    <div className="history-page">
      {/* ── MT4/MT5 Import Summary ── */}
      <GlassPanel title="MT4/MT5 Account History" subtitle={mt ? `Imported: ${mt.import_date} — ${mt.source}` : "No import data"}>
        {mt ? (
          <div className="mt-import-summary">
            <div className="dashboard-grid-3col">
              <div className="metric-stack" style={{ padding: "0" }}>
                <Metric label="Total Trades" value={`${mt.total_trades}`} mono />
                <Metric label="Win Rate" value={`${(mt.win_rate * 100).toFixed(1)}%`} mono />
                <Metric label="Profit Factor" value={mt.profit_factor.toFixed(2)} mono />
              </div>
              <div className="metric-stack" style={{ padding: "0" }}>
                <Metric label="Total Profit" value={`$${mt.total_profit.toFixed(2)}`} mono />
                <Metric label="Total Loss" value={`$${Math.abs(mt.total_loss).toFixed(2)}`} mono />
                <Metric label="Net P&L" value={`$${mt.net_pnl.toFixed(2)}`} mono danger={mt.net_pnl < 0} />
              </div>
              <div className="metric-stack" style={{ padding: "0" }}>
                <Metric label="Multi-Trade Bursts" value={`${mt.multi_trade_bursts}`} mono />
                <Metric label="Source" value={mt.source} />
                <Metric label="Import Date" value={mt.import_date} />
              </div>
            </div>

            {/* Symbol Performance */}
            {Object.keys(mt.symbol_performance).length > 0 && (
              <div style={{ marginTop: 12 }}>
                <h4 className="control-section-title" style={{ marginBottom: 8 }}>Symbol Performance</h4>
                <div className="symbol-perf-grid">
                  {Object.entries(mt.symbol_performance).map(([symbol, perf]) => (
                    <div key={symbol} className="symbol-perf-card">
                      <div className="symbol-perf-header">
                        <span className="route-symbol">{symbol}</span>
                        <StatusChip label={`${perf.trades} trades`} variant="muted" size="sm" />
                      </div>
                      <div className="symbol-perf-body">
                        <div className="sizing-row"><span className="field-label">Win Rate</span><span className="field-value mono">{(perf.win_rate * 100).toFixed(0)}%</span></div>
                        <div className="sizing-row"><span className="field-label">Profit Factor</span><span className="field-value mono">{perf.profit_factor.toFixed(2)}</span></div>
                        <div className="sizing-row"><span className="field-label">Net P&L</span><span className="field-value mono" style={{ color: perf.net_pnl >= 0 ? "var(--success)" : "var(--danger)" }}>${perf.net_pnl.toFixed(2)}</span></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="no-data-message">
            <p>No MT4/MT5 account history has been imported yet.</p>
            <code className="next-command-text" style={{ marginTop: 8, display: "inline-block" }}>
              python scripts/run_mt_history_import.py --source path/to/history.csv --output-dir evidence_runs/
            </code>
          </div>
        )}
      </GlassPanel>


      <GlassPanel title="Terminal History" subtitle="Positions / Orders / Deals · Day / Week / Month / Custom filters">
        <div className="dashboard-grid-3col" style={{ marginBottom: 12 }}>
          <div className="metric-stack" style={{ padding: 0 }}>
            <Metric label="Deposit" value={`$${(account?.summary.deposit_usd ?? 0).toFixed(2)}`} mono />
            <Metric label="Profit" value={`$${(account?.summary.realized_pnl_usd ?? 0).toFixed(2)}`} mono danger={(account?.summary.realized_pnl_usd ?? 0) < 0} />
            <Metric label="Balance" value={`$${(account?.summary.balance_usd ?? 0).toFixed(2)}`} mono />
          </div>
          <div className="metric-stack" style={{ padding: 0 }}>
            <Metric label="Equity" value={`$${(account?.summary.equity_usd ?? 0).toFixed(2)}`} mono />
            <Metric label="Swap" value={`$${(account?.summary.swap_usd ?? 0).toFixed(2)}`} mono />
            <Metric label="Commission" value={`$${(account?.summary.commission_usd ?? 0).toFixed(2)}`} mono />
          </div>
          <div className="metric-stack" style={{ padding: 0 }}>
            <Metric label="Positions" value={`${account?.summary.open_position_count ?? 0}`} mono />
            <Metric label="Orders" value={`${account?.summary.order_count ?? 0}`} mono />
            <Metric label="Deals" value={`${account?.summary.deal_count ?? 0}`} mono />
          </div>
        </div>
        <div className="sweep-status" style={{ marginBottom: 8 }}>
          {(account?.supported_history_tabs ?? ["Positions", "Orders", "Deals"]).map((tab) => (
            <StatusChip key={tab} label={tab} variant={tab === "Positions" ? "info" : "muted"} size="sm" />
          ))}
          <span style={{ color: "var(--text-muted)", fontSize: "0.72rem", marginLeft: 8 }}>
            Filters: {(account?.supported_time_filters ?? ["Seconds", "Minutes", "Hour", "Day", "Week", "Month", "Custom"]).join(" / ")}
          </span>
        </div>
        {account && account.positions.length > 0 ? (
          <div className="tally-table-wrap">
            <table className="data-table">
              <thead>
                <tr><th>Symbol</th><th>Side</th><th>Lot</th><th>Open → Current</th><th>SL</th><th>TP</th><th>Ticket</th><th>AI / Evidence</th><th>Net P/L</th></tr>
              </thead>
              <tbody>
                {account.positions.map((row) => (
                  <tr key={row.row_id}>
                    <td className="mono cell-symbol">{row.symbol}</td>
                    <td><StatusChip label={row.side} variant={row.side === "LONG" ? "info" : "danger"} size="sm" /></td>
                    <td className="mono">{row.lot_size.toFixed(2)}</td>
                    <td className="mono">{row.open_price.toFixed(2)} → {(row.close_or_current_price ?? row.open_price).toFixed(2)}</td>
                    <td className="mono" style={{ color: "var(--danger)" }}>{row.stop_loss?.toFixed(2) ?? "—"}</td>
                    <td className="mono" style={{ color: "var(--success)" }}>{row.take_profit?.toFixed(2) ?? "—"}</td>
                    <td className="mono" style={{ fontSize: "0.66rem" }}>{row.broker_ticket ?? row.simulator_ticket}</td>
                    <td className="mono" style={{ fontSize: "0.66rem" }}>{row.ai_action} / {row.evidence_packet_id}</td>
                    <td className="mono" style={{ color: row.net_pnl_usd > 0 ? "var(--success)" : row.net_pnl_usd < 0 ? "var(--danger)" : "var(--text-muted)" }}>${row.net_pnl_usd.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="no-data-message"><p>No paper/demo terminal rows are available yet.</p></div>
        )}
        <div style={{ marginTop: 8, color: "var(--warning)", fontSize: "0.7rem" }}>
          {account?.claim_boundary ?? "Paper/demo history only. Live trading and payment movement remain NOT LICENSED."}
        </div>
      </GlassPanel>

      {/* ── Condition Tally ── */}
      <GlassPanel title="Condition Tally" subtitle={state.conditionTally && state.conditionTally.length > 0 ? `${state.conditionTally.length} buckets from walk-forward evidence` : "Evidence score breakdown across condition axes"}>
        {state.conditionTally && state.conditionTally.length > 0 ? (
          <div className="tally-table-wrap">
            <table className="data-table">
              <thead>
                <tr><th>Bucket</th><th>Windows</th><th>Active</th><th>+Rate</th><th>Mean Return</th><th>Max DD</th><th>Trades</th></tr>
              </thead>
              <tbody>
                {state.conditionTally.map((b) => (
                  <tr key={b.key}>
                    <td className="mono" style={{ fontSize: "0.68rem" }}>{b.key}</td>
                    <td className="mono">{b.windows}</td>
                    <td className="mono">{b.active_windows}</td>
                    <td className="mono" style={{ color: b.positive_window_rate >= 0.5 ? "var(--success)" : "var(--warning)" }}>{(b.positive_window_rate * 100).toFixed(0)}%</td>
                    <td className="mono" style={{ color: b.mean_return_pct >= 0 ? "var(--success)" : "var(--danger)" }}>{b.mean_return_pct.toFixed(2)}%</td>
                    <td className="mono" style={{ color: "var(--warning)" }}>{b.max_drawdown_pct.toFixed(2)}%</td>
                    <td className="mono">{b.trades}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div style={{ marginTop: 8, color: "var(--text-muted)", fontSize: "0.68rem" }}>
              Source: latest walk-forward condition-tally evidence — {state.conditionTally.length} condition buckets
            </div>
          </div>
        ) : (
          <div className="no-data-message">
            <p>Condition tally data is generated by the guarded LLM optimizer pipeline.</p>
            <code className="next-command-text" style={{ marginTop: 8, display: "inline-block" }}>
              python scripts/run_condition_tally.py --output-dir evidence_runs/
            </code>
          </div>
        )}
      </GlassPanel>

      {/* ── Trade Log (Placeholder) ── */}
      <GlassPanel title="Paper Trade Log">
        <div className="no-data-message">
          <p>The paper trade log will populate as paper proof days accumulate. Currently 1/30 days complete.</p>
        </div>
      </GlassPanel>

      {/* ── Harvester Proposals (Placeholder) ── */}
      <GlassPanel title="Harvester Proposals">
        <div className="no-data-message">
          <p>Strategy harvester proposals appear after sufficient backtest and paper evidence accumulates.</p>
        </div>
      </GlassPanel>

      {/* ── Sweep Ledger ── */}
      <GlassPanel title="Sweep Ledger" variant="danger">
        <div className="sweep-ledger">
          <div className="sweep-status">
            <StatusChip label="DRY_RUN" variant="warning" size="sm" />
            <span style={{ color: "var(--text-muted)", fontSize: "0.75rem", marginLeft: 8 }}>Sweep/payout automation is NOT LICENSED</span>
          </div>
          <div style={{ marginTop: 8 }}>
            <div className="sizing-row"><span className="field-label">Mode</span><span className="field-value">DRY_RUN</span></div>
            <div className="sizing-row"><span className="field-label">Transfer Boundary</span><span className="field-value">INTERNAL_LEDGER_ONLY</span></div>
            <div className="sizing-row"><span className="field-label">Provider Transfer</span><span className="field-value mono" style={{ color: "var(--danger)" }}>NOT LICENSED</span></div>
            <div className="sizing-row"><span className="field-label">Bank / Debit / Card</span><span className="field-value mono" style={{ color: "var(--danger)" }}>NOT LICENSED</span></div>
          </div>
        </div>
      </GlassPanel>
    </div>
  );
}

function Metric({ label, value, mono, danger }: { label: string; value: string; mono?: boolean; danger?: boolean }) {
  return (
    <div className="dashboard-metric">
      <span className="field-label">{label}</span>
      <span className={`field-value ${mono ? "mono" : ""}`} style={{ color: danger ? "var(--danger)" : undefined }}>{value}</span>
    </div>
  );
}
