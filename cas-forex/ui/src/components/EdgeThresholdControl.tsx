/* ── CAS Forex — Edge Threshold Control ──
 *
 * The owner's bar for trading. A slider from 50% to 95% setting the minimum
 * measured win-probability the AI must prove (out-of-sample, AND beating the
 * shuffled null) before it is allowed to place a trade.
 *
 * This is the integrity dial: raise it and the AI trades less but only on
 * stronger evidence; it can never trade below this bar, and a setup must also
 * beat the null regardless of where this sits.
 *
 * Pure controlled component — owns no fetch. The parent holds the value and
 * decides where it is persisted / wired into the test gate.
 */

import { GlassPanel } from "./GlassPanel";

interface EdgeThresholdControlProps {
  value: number;
  onChange: (v: number) => void;
}

const MIN = 50;
const MAX = 95;

export function EdgeThresholdControl({ value, onChange }: EdgeThresholdControlProps) {
  // Keep the displayed value inside the legal band even if a stale prop slips in.
  const clamped = Math.max(MIN, Math.min(MAX, Math.round(value)));

  return (
    <GlassPanel
      title="Min edge to trade"
      subtitle="AI only trades setups it measures above this AND that beat the null"
    >
      <div className="edge-threshold-control" style={{ display: "grid", gap: 10 }}>
        <div
          style={{
            display: "flex",
            alignItems: "baseline",
            justifyContent: "space-between",
            gap: 8,
          }}
        >
          <span className="field-label">Min measured win-probability</span>
          <span className="field-value mono" style={{ fontWeight: 600, fontSize: "1.125rem" }}>
            {clamped}%
          </span>
        </div>

        <input
          type="range"
          className="edge-threshold-slider"
          min={MIN}
          max={MAX}
          step={1}
          value={clamped}
          onChange={(e) => onChange(Number(e.target.value))}
          aria-label="Minimum edge to trade (percent)"
          aria-valuemin={MIN}
          aria-valuemax={MAX}
          aria-valuenow={clamped}
          style={{ width: "100%" }}
        />

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: "0.8125rem",
            color: "var(--text-muted)",
          }}
        >
          <span>{MIN}%</span>
          <span>{MAX}%</span>
        </div>

        <div className="control-field-desc">
          The AI only trades setups it measures above this AND that beat the null.
          Below this bar, or on a failed null test, it stands down and sends no new order.
        </div>
      </div>
    </GlassPanel>
  );
}
