/* ── CAS Forex — Objective Pace Card ──
 *
 * The mission scoreboard: $250/day · $5,000/month across 20 trading days,
 * and where today / this month sit against that pace.
 *
 * Honest by construction. Pace is the *linear* expectation (target × days
 * elapsed); being "behind" is a fact, not a prompt to force trades. When
 * nothing has been realized yet it says so plainly rather than implying
 * progress. A no-trade day that protects capital is a correct outcome, and
 * this card never frames $0 as failure.
 *
 * Pure presentational — parent supplies the numbers.
 */

import { GlassPanel } from "./GlassPanel";

interface ObjectivePaceCardProps {
  dailyTarget: number;
  monthlyTarget: number;
  realizedToday: number;
  realizedMonth: number;
  /** 1-based index of the current trading day within the 20-day month (0 = not started). */
  tradingDayIndex: number;
}

const money = (v: number) => `${v < 0 ? "-" : ""}$${Math.abs(v).toLocaleString("en-US", {
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
})}`;

type Pace = { label: string; tone: "good" | "bad" | "neutral" };

function paceFor(realized: number, expected: number): Pace {
  // Small tolerance so a few dollars either way reads as "on pace".
  const tol = Math.max(1, expected * 0.02);
  if (realized >= expected + tol) return { label: "Ahead of pace", tone: "good" };
  if (realized <= expected - tol) return { label: "Behind pace", tone: "bad" };
  return { label: "On pace", tone: "neutral" };
}

function toneColor(tone?: Pace["tone"]): string | undefined {
  if (tone === "good") return "var(--success)";
  if (tone === "bad") return "var(--warning)";
  return undefined;
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: Pace["tone"] }) {
  return (
    <div style={{ display: "grid", gap: 2 }}>
      <span className="field-label">{label}</span>
      <span className="field-value mono" style={{ fontWeight: 600, color: toneColor(tone) }}>
        {value}
      </span>
    </div>
  );
}

export function ObjectivePaceCard({
  dailyTarget,
  monthlyTarget,
  realizedToday,
  realizedMonth,
  tradingDayIndex,
}: ObjectivePaceCardProps) {
  const started = tradingDayIndex > 0;

  // Linear month pace expectation given how many trading days have elapsed.
  const expectedMonth = started ? dailyTarget * tradingDayIndex : 0;
  const monthPace = paceFor(realizedMonth, expectedMonth);
  const dayPace = paceFor(realizedToday, dailyTarget);

  // What's still needed today to hit the daily target (never negative).
  const neededToday = Math.max(0, dailyTarget - realizedToday);

  const nothingYet = !started && realizedToday === 0 && realizedMonth === 0;

  return (
    <GlassPanel
      title="Objective — Pace"
      subtitle={`${money(dailyTarget)}/day · ${money(monthlyTarget)}/month over 20 trading days`}
    >
      <div style={{ display: "grid", gap: 14 }}>
        {nothingYet ? (
          <div className="control-field-desc">
            Nothing realized yet. The objective is {money(dailyTarget)}/day toward{" "}
            {money(monthlyTarget)}/month — but the AI only earns it by pressing real,
            tested edges. A day with no edge is a $0 day with capital intact, not a miss.
          </div>
        ) : (
          <>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
                gap: 10,
              }}
            >
              <Stat label="Trading day" value={started ? `${tradingDayIndex} / 20` : "not started"} />
              <Stat label="Realized today" value={money(realizedToday)} tone={dayPace.tone} />
              <Stat label="Realized month" value={money(realizedMonth)} tone={monthPace.tone} />
              <Stat label="Month pace target" value={money(expectedMonth)} />
            </div>

            <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "baseline" }}>
              <span className="field-value" style={{ color: toneColor(monthPace.tone), fontWeight: 600 }}>
                {monthPace.label} for the month
              </span>
              <span className="control-field-desc">
                {neededToday > 0
                  ? `${money(neededToday)} more would meet today's ${money(dailyTarget)} target.`
                  : `Today's ${money(dailyTarget)} target met.`}
              </span>
            </div>

            <div className="control-field-desc">
              Pace is the straight-line expectation only. Being behind is never a reason to
              force a trade — no-edge days protect capital and stay at $0.
            </div>
          </>
        )}
      </div>
    </GlassPanel>
  );
}
