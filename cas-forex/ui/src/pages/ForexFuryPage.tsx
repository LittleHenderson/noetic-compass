/* ── CAS Forex — Forex Fury Candidates Page ──
 *
 * Lists Forex Fury replay candidates and lets the operator manually
 * move a candidate to PAPER_LANE via the promote endpoint.
 * Instrument panel only — no advisory language.
 */

import { useEffect, useState } from "react";
import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import {
  fetchForexFuryReplayCandidates,
  promoteForexFuryCandidate,
  type ApiPostError,
  type ForexFuryPromoteResponse,
} from "../data/api";
import type {
  DashboardState,
  ForexFuryReplayCandidate,
  ForexFuryReplayCandidateReport,
} from "../types/evidence";
import "../components/StrategyActionControls.css";
import "./ForexFuryPage.css";

interface ForexFuryPageProps {
  state: DashboardState;
}

type ChipVariant = "success" | "warning" | "danger" | "info" | "muted" | "paper";

interface RowResult {
  kind: "ok" | "err";
  ok?: ForexFuryPromoteResponse;
  err?: ApiPostError;
}

function readinessVariant(readiness: string): ChipVariant {
  const lower = (readiness || "").toLowerCase();
  if (lower.includes("ready")) return "info";
  if (lower.includes("wait") || lower.includes("pending")) return "warning";
  if (lower.includes("block") || lower.includes("fail")) return "danger";
  return "muted";
}

function truncateId(id: string): string {
  if (!id) return "—";
  if (id.length <= 16) return id;
  return `${id.slice(0, 6)}…${id.slice(-6)}`;
}

function topSymbol(summary: ForexFuryReplayCandidateReport["summary"] | null): string {
  if (!summary) return "—";
  if (!summary.symbols || summary.symbols.length === 0) return "—";
  return summary.symbols[0];
}

function topFamily(summary: ForexFuryReplayCandidateReport["summary"] | null): string {
  if (!summary) return "—";
  const families = summary.families ?? {};
  let best: string | null = null;
  let bestCount = -1;
  for (const [family, count] of Object.entries(families)) {
    if (count > bestCount) {
      bestCount = count;
      best = family;
    }
  }
  return best ?? "—";
}

export function ForexFuryPage({ state }: ForexFuryPageProps) {
  const initialReport = state.forexFuryReplayCandidates ?? null;
  const [report, setReport] = useState<ForexFuryReplayCandidateReport | null>(initialReport);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState<Record<string, boolean>>({});
  const [results, setResults] = useState<Record<string, RowResult>>({});

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchForexFuryReplayCandidates()
      .then((data) => {
        if (!cancelled && data) setReport(data);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handlePromote(
    candidate: ForexFuryReplayCandidate,
    allowUnverified = false,
  ) {
    const id = candidate.candidate_id;
    setPending((prev) => ({ ...prev, [id]: true }));
    const result = await promoteForexFuryCandidate(id, allowUnverified);
    setPending((prev) => ({ ...prev, [id]: false }));
    if (result.ok) {
      setResults((prev) => ({ ...prev, [id]: { kind: "ok", ok: result.data } }));
    } else {
      setResults((prev) => ({ ...prev, [id]: { kind: "err", err: result.error } }));
    }
  }

  const candidates = report?.candidates ?? [];
  const summary = report?.summary ?? null;
  const totalCandidates = summary?.candidate_count ?? candidates.length;

  return (
    <div className="dashboard-page">
      <GlassPanel
        title="Forex Fury Candidates"
        subtitle={
          report
            ? `Source: ${report.source_report_path ?? "forex-fury replay report"}`
            : loading
              ? "Loading replay candidates..."
              : "No replay report available"
        }
      >
        <div className="dashboard-grid-3col" style={{ marginBottom: 12 }}>
          <div className="metric-stack" style={{ padding: 0 }}>
            <div className="dashboard-metric">
              <span className="field-label">Total Candidates</span>
              <span className="field-value mono">{totalCandidates}</span>
            </div>
          </div>
          <div className="metric-stack" style={{ padding: 0 }}>
            <div className="dashboard-metric">
              <span className="field-label">Top Symbol</span>
              <span className="field-value mono">{topSymbol(summary)}</span>
            </div>
          </div>
          <div className="metric-stack" style={{ padding: 0 }}>
            <div className="dashboard-metric">
              <span className="field-label">Top Family</span>
              <span className="field-value mono">{topFamily(summary)}</span>
            </div>
          </div>
        </div>

        {candidates.length === 0 ? (
          <div className="no-data-message">
            <p>No replay candidates available yet. Run a Forex Fury import + replay first.</p>
          </div>
        ) : (
          <div className="positions-table-wrap fury-candidates-table">
            <table className="data-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Candidate</th>
                  <th>Symbol</th>
                  <th>TF</th>
                  <th>Family</th>
                  <th>PF</th>
                  <th>DD %</th>
                  <th>Score</th>
                  <th>Readiness</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {candidates.map((c) => {
                  const id = c.candidate_id;
                  const isPending = pending[id] === true;
                  const result = results[id];
                  const pf = c.evidence.profit_factor;
                  const dd = c.evidence.equity_drawdown_relative_pct;
                  return (
                    <tr key={id} className="fury-candidate-row">
                      <td className="mono">{c.rank}</td>
                      <td className="mono" title={id}>{truncateId(id)}</td>
                      <td className="mono cell-symbol">{c.cas_symbol}</td>
                      <td className="mono">{c.timeframe}</td>
                      <td className="mono">{c.family}</td>
                      <td className="mono">{pf != null ? pf.toFixed(2) : "—"}</td>
                      <td className="mono">{dd != null ? dd.toFixed(2) : "—"}</td>
                      <td className="mono">{c.score.toFixed(2)}</td>
                      <td>
                        <StatusChip
                          label={c.readiness}
                          variant={readinessVariant(c.readiness)}
                          size="sm"
                        />
                      </td>
                      <td>
                        <div className="fury-row-action">
                          <button
                            type="button"
                            className="strategy-action-button"
                            onClick={() => handlePromote(c)}
                            disabled={isPending || result?.kind === "ok"}
                          >
                            {isPending
                              ? "Promoting..."
                              : result?.kind === "ok"
                                ? "Promoted"
                                : "Promote to paper lane"}
                          </button>
                          {result?.kind === "ok" && (
                            <div className="action-result-toast action-result-ok">
                              {result.ok?.lead_id
                                ? `Lead created: ${result.ok.lead_id}`
                                : result.ok?.message ?? "Promotion accepted"}
                            </div>
                          )}
                          {result?.kind === "err" && (
                            <div className="action-result-toast action-result-err">
                              {extractErrorMessage(result.err)}
                              <button
                                type="button"
                                className="strategy-action-button"
                                style={{ marginTop: 6 }}
                                disabled={isPending}
                                onClick={() => handlePromote(c, true)}
                                title="Promote without the verified .set file. The lead is flagged integrity_verified: false."
                              >
                                {isPending ? "Promoting..." : "Promote anyway (unverified)"}
                              </button>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </GlassPanel>
    </div>
  );
}

function extractErrorMessage(err?: ApiPostError): string {
  if (!err) return "Request failed";
  const payload = err.payload as { detail?: unknown; message?: string } | null;
  if (payload && typeof payload === "object") {
    const detail = payload.detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail === "object") {
      const d = detail as { message?: string; current_stage?: string };
      if (d.message) return d.current_stage ? `${d.current_stage}: ${d.message}` : d.message;
    }
    if (typeof payload.message === "string") return payload.message;
  }
  return err.message;
}
