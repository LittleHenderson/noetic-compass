/* ── CAS Forex — Proof Control Panel ──
   Profit-measured proof summary + in-app advance (record-today / auto-runner) +
   owner-adjustable pass thresholds. Self-fetching; paper-only. */

import { useEffect, useState } from "react";
import { GlassPanel } from "./GlassPanel";
import { StatusChip } from "./StatusChip";
import {
  fetchProofControl,
  runProofDayNow,
  startProofAutoRunner,
  stopProofAutoRunner,
  updateProofThresholds,
  resetProofThresholds,
  type ProofControlState,
  type ProofThresholdPatch,
} from "../data/api";

type Draft = {
  require_net_positive: boolean;
  min_net_pnl_usd: string;
  max_drawdown_pct: string;
  min_trade_days_fraction: string;
  seed_capital_usd: string;
};

function toDraft(s: ProofControlState): Draft {
  const t = s.thresholds;
  return {
    require_net_positive: t.require_net_positive,
    min_net_pnl_usd: String(t.min_net_pnl_usd),
    max_drawdown_pct: String(t.max_drawdown_pct),
    min_trade_days_fraction: String(t.min_trade_days_fraction),
    seed_capital_usd: String(t.seed_capital_usd),
  };
}

const money = (v: number) => `${v < 0 ? "-" : ""}$${Math.abs(v).toFixed(2)}`;

export function ProofControlPanel() {
  const [pc, setPc] = useState<ProofControlState | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [busy, setBusy] = useState<string>("");
  const [status, setStatus] = useState<string>("");

  function apply(s: ProofControlState) {
    setPc(s);
    setDraft(toDraft(s));
  }

  useEffect(() => {
    void fetchProofControl().then((s) => {
      if (s) apply(s);
    });
  }, []);

  async function recordToday() {
    setBusy("run");
    setStatus("Recording today's proof day — reading the demo broker…");
    try {
      const s = await runProofDayNow();
      apply(s);
      const rr = s.run_result;
      setStatus(rr ? `Run result: ${rr.status}${rr.detail ? " — " + rr.detail : ""}` : "Done.");
    } catch {
      setStatus("Couldn't record the day — is the API reachable? Check the address in Settings.");
    } finally {
      setBusy("");
    }
  }

  async function toggleAuto() {
    if (!pc) return;
    setBusy("auto");
    try {
      const s = pc.auto_runner.running ? await stopProofAutoRunner() : await startProofAutoRunner(1800);
      apply(s);
      setStatus(s.auto_runner.running ? "Auto-runner ON — records each trading day for you." : "Auto-runner OFF.");
    } catch {
      setStatus("Couldn't change the auto-runner.");
    } finally {
      setBusy("");
    }
  }

  async function saveThresholds() {
    if (!draft) return;
    setBusy("thresholds");
    const patch: ProofThresholdPatch = {
      require_net_positive: draft.require_net_positive,
      min_net_pnl_usd: draft.min_net_pnl_usd.trim() === "" ? undefined : Number(draft.min_net_pnl_usd),
      max_drawdown_pct: draft.max_drawdown_pct.trim() === "" ? undefined : Number(draft.max_drawdown_pct),
      min_trade_days_fraction:
        draft.min_trade_days_fraction.trim() === "" ? undefined : Number(draft.min_trade_days_fraction),
      seed_capital_usd: draft.seed_capital_usd.trim() === "" ? undefined : Number(draft.seed_capital_usd),
    };
    try {
      const s = await updateProofThresholds(patch);
      apply(s);
      setStatus(s.error ? `Couldn't save: ${s.error}` : "Saved — applies to the proof immediately.");
    } catch {
      setStatus("Couldn't save the thresholds.");
    } finally {
      setBusy("");
    }
  }

  async function resetThresholds() {
    setBusy("thresholds");
    try {
      apply(await resetProofThresholds());
      setStatus("Thresholds reset to plan defaults.");
    } catch {
      setStatus("Couldn't reset.");
    } finally {
      setBusy("");
    }
  }

  if (!pc || !draft) {
    return (
      <GlassPanel title="Proof Control" subtitle="Advance the 30-day proof + set what 'passed' means">
        <div className="control-field-desc">Loading proof status…</div>
      </GlassPanel>
    );
  }

  const p = pc.proof;
  const auto = pc.auto_runner;
  const ddOver = p.max_drawdown_pct > pc.thresholds.max_drawdown_pct;

  return (
    <GlassPanel
      title="Proof Control — You Drive"
      subtitle="Advance the 30-day proof from here, and set what counts as a profitable pass"
    >
      <div style={{ display: "grid", gap: 14 }}>
        {/* Headline pass state */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <StatusChip
            label={p.passed ? "PROOF PASSED" : "NOT YET"}
            variant={p.passed ? "success" : "paper"}
            size="sm"
          />
          <span className="control-field-desc">
            A pass needs all 30 broker-verified days, net-positive P&L, drawdown within the limit, and real
            trades on most days.
          </span>
        </div>

        {/* Profit metrics */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 10 }}>
          <Metric label="Verified days" value={`${p.broker_verified_days} / ${p.required_trading_days}`} />
          <Metric
            label="Net P&L"
            value={money(p.net_pnl_usd)}
            tone={p.net_pnl_usd > 0 ? "good" : p.net_pnl_usd < 0 ? "bad" : "neutral"}
          />
          <Metric
            label="Max drawdown"
            value={`${p.max_drawdown_pct.toFixed(2)}%`}
            tone={ddOver ? "bad" : "neutral"}
          />
          <Metric label="Days with trades" value={`${p.days_with_trades} / ${p.min_trade_days_required}`} />
          <Metric label="Profit check" value={p.profit_passed ? "PASS" : "NOT YET"} tone={p.profit_passed ? "good" : "neutral"} />
        </div>

        {p.failure_reasons.length > 0 && (
          <div className="control-field-desc" style={{ color: "var(--warning)" }}>
            What's left: {p.failure_reasons.join(" · ")}
          </div>
        )}

        {/* Advance the proof */}
        <div style={{ borderTop: "1px solid var(--border, rgba(255,255,255,0.08))", paddingTop: 12 }}>
          <div className="field-label" style={{ marginBottom: 8 }}>Advance the proof</div>
          <div className="mobile-api-row">
            <button
              className="mobile-api-button"
              type="button"
              disabled={busy === "run"}
              onClick={() => void recordToday()}
            >
              {busy === "run" ? "Recording…" : "Record today's proof day"}
            </button>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <button
                type="button"
                className="go-live-switch"
                data-on={auto.running}
                disabled={busy === "auto"}
                aria-pressed={auto.running}
                aria-label={`Daily auto-runner — ${auto.running ? "on" : "off"}`}
                onClick={() => void toggleAuto()}
              >
                <span className="knob" />
              </button>
              <span className="control-field-desc">Daily auto-runner {auto.running ? "ON" : "OFF"}</span>
            </div>
          </div>
          <div className="control-field-desc" style={{ marginTop: 6 }}>
            {auto.running
              ? `Records each trading day automatically. Last: ${auto.last_recorded_date ?? "—"} (${auto.last_status ?? "—"}).`
              : "Turn this on to record each broker-verified trading day for you — no command line."}
          </div>
        </div>

        {/* Thresholds — owner-tunable */}
        <div style={{ borderTop: "1px solid var(--border, rgba(255,255,255,0.08))", paddingTop: 12 }}>
          <div className="field-label" style={{ marginBottom: 8 }}>What counts as "passed" (your bar)</div>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.875rem", marginBottom: 10 }}>
            <input
              type="checkbox"
              checked={draft.require_net_positive}
              onChange={(e) => { setDraft({ ...draft, require_net_positive: e.target.checked }); setStatus(""); }}
            />
            Require the proof to be net-positive (made money)
          </label>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 10 }}>
            <ThresholdInput
              label="Min net P&L ($)"
              value={draft.min_net_pnl_usd}
              onChange={(v) => { setDraft({ ...draft, min_net_pnl_usd: v }); setStatus(""); }}
            />
            <ThresholdInput
              label="Max drawdown (%)"
              value={draft.max_drawdown_pct}
              onChange={(v) => { setDraft({ ...draft, max_drawdown_pct: v }); setStatus(""); }}
            />
            <ThresholdInput
              label="Trade-days fraction (0–1)"
              value={draft.min_trade_days_fraction}
              hint="0.5 = most days"
              onChange={(v) => { setDraft({ ...draft, min_trade_days_fraction: v }); setStatus(""); }}
            />
            <ThresholdInput
              label="Seed capital ($)"
              value={draft.seed_capital_usd}
              hint="drawdown base"
              onChange={(v) => { setDraft({ ...draft, seed_capital_usd: v }); setStatus(""); }}
            />
          </div>
          <div className="mobile-api-row" style={{ marginTop: 10 }}>
            <button className="mobile-api-button" type="button" disabled={busy === "thresholds"} onClick={() => void saveThresholds()}>
              Save bar
            </button>
            <button className="mobile-api-button ghost" type="button" disabled={busy === "thresholds"} onClick={() => void resetThresholds()}>
              Reset to plan defaults
            </button>
          </div>
        </div>

        {status && <div className="control-field-desc" style={{ color: "var(--success)" }}>{status}</div>}
      </div>
    </GlassPanel>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: "good" | "bad" | "neutral" }) {
  const color = tone === "good" ? "var(--success)" : tone === "bad" ? "var(--danger)" : undefined;
  return (
    <div style={{ display: "grid", gap: 2 }}>
      <span className="field-label">{label}</span>
      <span className="field-value mono" style={{ color, fontWeight: 600 }}>{value}</span>
    </div>
  );
}

function ThresholdInput({
  label,
  value,
  hint,
  onChange,
}: {
  label: string;
  value: string;
  hint?: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="control-field">
      <span className="field-label">{label}</span>
      <input
        className="mobile-api-input"
        type="number"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      {hint && <div className="control-field-desc">{hint}</div>}
    </div>
  );
}
