/* ── CAS Forex — Condition Lab ── */

import { useState } from "react";
import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import type { DashboardState, ConditionTallyBucket } from "../types/evidence";

interface ConditionLabPageProps {
  state: DashboardState;
}

export function ConditionLabPage({ state }: ConditionLabPageProps) {
  const tally = state.conditionTally ?? [];
  const [selectedBucket, setSelectedBucket] = useState<ConditionTallyBucket | null>(null);

  // Gap analysis data
  const gapCells = [
    { strategy: "tsmom_126_250_2_10", tf: "D1", covered: true },
    { strategy: "tsmom_126_250_2_10", tf: "H1", covered: true },
    { strategy: "tsmom_126_250_2_10", tf: "H4", covered: false },
    { strategy: "tsmom_126_250_2_10", tf: "M15", covered: false },
    { strategy: "range_scalper_24_120", tf: "D1", covered: true },
    { strategy: "range_scalper_24_120", tf: "H1", covered: false },
    { strategy: "range_scalper_24_120", tf: "H4", covered: false },
    { strategy: "range_scalper_24_120", tf: "M15", covered: false },
  ];
  const gaps = gapCells.filter((c) => !c.covered).length;
  const gapFraction = gaps / gapCells.length;

  return (
    <div className="condition-lab-page">
      {/* Section 1: Condition Explorer */}
      <GlassPanel
        title="Condition Lab"
        subtitle="Interactive condition-axis explorer — drill into walk-forward evidence by timeframe, strategy, and route action"
      >
        <div className="control-section">
          <h4 className="control-section-title">Timeframe</h4>
          <div className="selector-chips">
            {["ALL", "D1", "H1", "H4", "M15"].map((tf) => (
              <button key={tf} className={`selector-chip ${tf === "D1" ? "active" : ""}`} disabled>
                {tf}
              </button>
            ))}
          </div>
        </div>
        <div className="control-section" style={{ marginTop: 12 }}>
          <h4 className="control-section-title">Strategy Setting</h4>
          <div className="selector-chips">
            {["ALL", "tsmom_126_250_2_10", "range_scalper_24_120"].map((s) => (
              <button
                key={s}
                className={`selector-chip ${s === "tsmom_126_250_2_10" ? "active" : ""}`}
                disabled
              >
                {s.length > 20 ? s.slice(0, 20) + "\u2026" : s}
              </button>
            ))}
          </div>
        </div>
        <div className="control-section" style={{ marginTop: 12 }}>
          <h4 className="control-section-title">Route Action</h4>
          <div className="selector-chips">
            {["ALL", "ROUTE", "NO_TRADE"].map((r) => (
              <button key={r} className={`selector-chip ${r === "ROUTE" ? "active" : ""}`} disabled>
                {r}
              </button>
            ))}
          </div>
        </div>
      </GlassPanel>

      {/* Section 2: Condition Buckets */}
      <GlassPanel
        title="Condition Buckets"
        subtitle={tally.length > 0 ? `${tally.length} buckets from walk-forward evidence` : "No condition tally data"}
      >
        {tally.length > 0 ? (
          <div className="tally-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Bucket Key</th>
                  <th>TF</th>
                  <th>Strategy</th>
                  <th>Windows</th>
                  <th>Active</th>
                  <th>+Rate</th>
                  <th>Mean Return</th>
                  <th>Max DD</th>
                  <th>Trades</th>
                </tr>
              </thead>
              <tbody>
                {tally.map((b) => {
                  const isSelected = selectedBucket?.key === b.key;
                  return (
                    <tr
                      key={b.key}
                      onClick={() => setSelectedBucket(b)}
                      style={{ cursor: "pointer", background: isSelected ? "var(--bg-card)" : undefined }}
                    >
                      <td className="mono" style={{ fontSize: "0.6rem" }}>
                        {b.key}
                      </td>
                      <td className="mono">{b.axes.timeframe ?? "—"}</td>
                      <td className="mono" style={{ fontSize: "0.6rem" }}>
                        {(b.axes.setting ?? "").length > 18
                          ? (b.axes.setting ?? "").slice(0, 18) + "\u2026"
                          : b.axes.setting}
                      </td>
                      <td className="mono">{b.windows}</td>
                      <td className="mono">{b.active_windows}</td>
                      <td
                        className="mono"
                        style={{ color: b.positive_window_rate >= 0.5 ? "var(--success)" : "var(--warning)" }}
                      >
                        {(b.positive_window_rate * 100).toFixed(0)}%
                      </td>
                      <td
                        className="mono"
                        style={{ color: b.mean_return_pct >= 0 ? "var(--success)" : "var(--danger)" }}
                      >
                        {b.mean_return_pct.toFixed(2)}%
                      </td>
                      <td className="mono" style={{ color: "var(--warning)" }}>
                        {b.max_drawdown_pct.toFixed(2)}%
                      </td>
                      <td className="mono">{b.trades}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="no-data-message">
            <p>No condition tally data available.</p>
          </div>
        )}
      </GlassPanel>

      {/* Section 3: Bucket Detail */}
      <GlassPanel
        title="Bucket Detail"
        subtitle={selectedBucket ? `Selected: ${selectedBucket.key}` : "Click a bucket row to see detail"}
      >
        {selectedBucket ? (
          <div>
            <div className="sizing-row">
              <span className="field-label">Key</span>
              <span className="field-value mono" style={{ fontSize: "0.68rem" }}>
                {selectedBucket.key}
              </span>
            </div>
            <div className="sizing-row">
              <span className="field-label">Timeframe</span>
              <span className="field-value mono">{selectedBucket.axes.timeframe}</span>
            </div>
            <div className="sizing-row">
              <span className="field-label">Strategy Setting</span>
              <span className="field-value mono">{selectedBucket.axes.setting}</span>
            </div>
            <div className="sizing-row">
              <span className="field-label">Route Action</span>
              <span className="field-value mono">{selectedBucket.axes.route_action}</span>
            </div>
            <div className="sizing-row">
              <span className="field-label">Total Windows</span>
              <span className="field-value mono">{selectedBucket.windows}</span>
            </div>
            <div className="sizing-row">
              <span className="field-label">Routed Windows</span>
              <span className="field-value mono">{selectedBucket.routed_windows}</span>
            </div>
            <div className="sizing-row">
              <span className="field-label">Active Windows</span>
              <span className="field-value mono">{selectedBucket.active_windows}</span>
            </div>
            <div className="sizing-row">
              <span className="field-label">Positive Windows</span>
              <span className="field-value mono">{selectedBucket.positive_windows}</span>
            </div>
            <div className="sizing-row">
              <span className="field-label">Positive Rate</span>
              <span className="field-value mono">
                {(selectedBucket.positive_window_rate * 100).toFixed(1)}%
              </span>
            </div>
            <div className="sizing-row">
              <span className="field-label">Total Return</span>
              <span
                className="field-value mono"
                style={{
                  color: selectedBucket.total_return_pct >= 0 ? "var(--success)" : "var(--danger)",
                }}
              >
                {selectedBucket.total_return_pct.toFixed(2)}%
              </span>
            </div>
            <div className="sizing-row">
              <span className="field-label">Mean Return</span>
              <span
                className="field-value mono"
                style={{
                  color: selectedBucket.mean_return_pct >= 0 ? "var(--success)" : "var(--danger)",
                }}
              >
                {selectedBucket.mean_return_pct.toFixed(2)}%
              </span>
            </div>
            <div className="sizing-row">
              <span className="field-label">Max Drawdown</span>
              <span className="field-value mono" style={{ color: "var(--warning)" }}>
                {selectedBucket.max_drawdown_pct.toFixed(2)}%
              </span>
            </div>
            <div className="sizing-row">
              <span className="field-label">Trades</span>
              <span className="field-value mono">{selectedBucket.trades}</span>
            </div>
          </div>
        ) : (
          <div className="no-data-message">
            <p>Click a bucket row above to see detailed metrics.</p>
          </div>
        )}
      </GlassPanel>

      {/* Section 4: Gap Analysis */}
      <GlassPanel title="S1-Y1 Gap Map" subtitle="Strategy-to-Year condition coverage gaps">
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {gapCells.map((c) => (
            <div
              key={`${c.strategy}-${c.tf}`}
              style={{
                padding: "4px 10px",
                background: c.covered ? "var(--success-dim)" : "var(--warning-dim)",
                borderRadius: "var(--radius-sm)",
                fontSize: "0.68rem",
                display: "flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              <span className="mono" style={{ color: c.covered ? "var(--success)" : "var(--warning)" }}>
                {c.tf}
              </span>
              <span style={{ color: "var(--text-muted)", fontSize: "0.6rem" }}>×</span>
              <span
                className="mono"
                style={{ fontSize: "0.58rem", color: "var(--text-secondary)" }}
              >
                {c.strategy.length > 16 ? c.strategy.slice(0, 16) + "\u2026" : c.strategy}
              </span>
              <StatusChip
                label={c.covered ? "COVERED" : "GAP"}
                variant={c.covered ? "success" : "warning"}
                size="sm"
              />
            </div>
          ))}
        </div>
        <div style={{ marginTop: 8, fontSize: "0.72rem", color: "var(--text-muted)" }}>
          {gaps} gaps / {gapCells.length} cells — {(gapFraction * 100).toFixed(1)}% gap fraction (target: &lt;25%)
        </div>
      </GlassPanel>

      {/* Section 5: Pipeline Status */}
      <GlassPanel title="Pipeline Status">
        <div className="sizing-row">
          <span className="field-label">Condition Tally Pipeline</span>
          <span className="field-value">
            <StatusChip label="ACTIVE" variant="info" size="sm" />
          </span>
        </div>
        <div className="sizing-row">
          <span className="field-label">Last Run</span>
          <span className="field-value mono">2026-06-22</span>
        </div>
        <div className="sizing-row">
          <span className="field-label">Gap Fraction</span>
          <span className="field-value mono">{(gapFraction * 100).toFixed(1)}%</span>
        </div>
        <div className="sizing-row">
          <span className="field-label">Missing Axes</span>
          <span className="field-value mono">H4, M15 (both strategies)</span>
        </div>
        <div className="sizing-row">
          <span className="field-label">Next Run</span>
          <span className="field-value">On next walk-forward update</span>
        </div>
        <code className="next-command-text" style={{ marginTop: 8, display: "inline-block" }}>
          python scripts/run_condition_tally.py --output-dir evidence_runs/
        </code>
      </GlassPanel>
    </div>
  );
}
