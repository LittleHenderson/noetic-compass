/* ── CAS Forex — Incentive Ledger Card ──
 *
 * The AI's performance-fee accrual: a rate (default 2.5%) per unit of
 * broker-VERIFIED profit (default $5,000), reviewed quarterly.
 *
 * Honest by construction: the fee accrues ONLY on profit the broker has
 * verified. Faking a fill earns nothing. The card shows what has accrued so
 * far and how much more verified profit reaches the next milestone — it never
 * accrues on floating, paper, or unverified P&L.
 *
 * Pure presentational — parent supplies the verified number.
 */

import { GlassPanel } from "./GlassPanel";

interface IncentiveLedgerCardProps {
  /** Broker-verified realized profit, in USD. Only this drives accrual. */
  verifiedProfit: number;
  /** Fee rate as a fraction, e.g. 0.025 for 2.5%. */
  rate: number;
  /** Profit unit the rate applies per, e.g. 5000 for "per $5K". */
  per: number;
}

const money = (v: number) => `${v < 0 ? "-" : ""}$${Math.abs(v).toLocaleString("en-US", {
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
})}`;

function Stat({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div style={{ display: "grid", gap: 2 }}>
      <span className="field-label">{label}</span>
      <span
        className="field-value mono"
        style={{ fontWeight: 600, color: accent ? "var(--success)" : undefined }}
      >
        {value}
      </span>
    </div>
  );
}

export function IncentiveLedgerCard({ verifiedProfit, rate, per }: IncentiveLedgerCardProps) {
  const ratePct = rate * 100;

  // Fee accrues only on positive verified profit. A loss accrues nothing.
  // rate is per-`per` (e.g. 2.5% per $5K), so the realized fee is simply
  // rate × verified-profit (the `per` block size cancels out of the rate).
  const accruableProfit = Math.max(0, verifiedProfit);
  const feeEarned = accruableProfit * rate;

  // Next milestone: the next whole `per`-sized block of verified profit.
  const blocksCleared = per > 0 ? Math.floor(accruableProfit / per) : 0;
  const nextMilestone = per * (blocksCleared + 1);
  const toNextMilestone = Math.max(0, nextMilestone - accruableProfit);

  return (
    <GlassPanel
      title="AI Performance Fee"
      subtitle={`${ratePct.toFixed(1)}% per ${money(per)} of broker-verified profit · quarterly review`}
    >
      <div style={{ display: "grid", gap: 14 }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
            gap: 10,
          }}
        >
          <Stat label="Verified profit" value={money(verifiedProfit)} />
          <Stat label="Fee accrued" value={money(feeEarned)} accent={feeEarned > 0} />
          <Stat label="Next milestone" value={money(nextMilestone)} />
          <Stat label="To next milestone" value={money(toNextMilestone)} />
        </div>

        {verifiedProfit <= 0 ? (
          <div className="control-field-desc">
            No fee yet — nothing accrues until the broker verifies realized profit.
          </div>
        ) : (
          <div className="control-field-desc">
            {money(toNextMilestone)} more verified profit reaches the next{" "}
            {money(per)} milestone.
          </div>
        )}

        <div className="control-field-desc">
          The fee accrues only on broker-verified profit. Floating, paper, or unverified
          P&amp;L earns nothing — faking a fill earns nothing. Reviewed quarterly.
        </div>
      </div>
    </GlassPanel>
  );
}
