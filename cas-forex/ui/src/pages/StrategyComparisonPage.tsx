/* ── CAS Forex — Strategy Comparison Page ── */

import { useCallback, useEffect, useMemo, useState } from "react";
import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import {
  fetchPerformanceDiscipline,
  fetchRankedStrategies,
  fetchStrategyDiff,
} from "../data/api";
import type {
  PerformanceDisciplineReport,
  StrategyComparisonRecord,
  StrategyDiff,
  StrategyRankingReport,
} from "../data/api";
import "./StrategyComparisonPage.css";

type Mode = "ranked" | "diff";

const LIMIT_OPTIONS = [10, 25, 50];

type SourceVariant = "success" | "warning" | "danger" | "info" | "muted" | "paper";

function sourceVariant(source: string): SourceVariant {
  const s = (source || "").toLowerCase();
  if (s.includes("fury")) return "info";
  if (s.includes("lead")) return "paper";
  if (s.includes("dev")) return "warning";
  return "muted";
}

function truncate(id: string, width = 14): string {
  if (!id) return "—";
  if (id.length <= width) return id;
  return `${id.slice(0, width - 1)}…`;
}

function fmtNum(n: number | null | undefined, digits = 2): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toFixed(digits);
}

function scoreClass(score: number | null | undefined): string {
  if (score === null || score === undefined || Number.isNaN(score)) return "score-muted";
  if (score >= 75) return "score-teal";
  if (score >= 50) return "score-yellow";
  return "score-muted";
}

interface DiffPanelProps {
  diff: StrategyDiff | null;
  loading: boolean;
  error: string | null;
}

function DiffPanel({ diff, loading, error }: DiffPanelProps) {
  if (loading) {
    return <div className="muted-cell">Loading diff…</div>;
  }
  if (error) {
    return <div className="api-status-strip">{error}</div>;
  }
  if (!diff) {
    return <div className="muted-cell">Pick strategies A and B to view the diff.</div>;
  }
  return (
    <div className="diff-panel">
      <table className="comparison-table">
        <thead>
          <tr>
            <th>Field</th>
            <th>A — {truncate(diff.strategy_id_a, 18)}</th>
            <th>B — {truncate(diff.strategy_id_b, 18)}</th>
          </tr>
        </thead>
        <tbody>
          {diff.field_diffs.map((f) => (
            <tr key={f.field}>
              <td className="mono">{f.field}</td>
              <td>{String(f.a_value ?? "—")}</td>
              <td>{String(f.b_value ?? "—")}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {diff.plain_english_diff && (
        <p className="plain-english-block">{diff.plain_english_diff}</p>
      )}
    </div>
  );
}

export function StrategyComparisonPage() {
  const [mode, setMode] = useState<Mode>("ranked");
  const [limit, setLimit] = useState<number>(25);
  const [report, setReport] = useState<StrategyRankingReport | null>(null);
  const [discipline, setDiscipline] = useState<PerformanceDisciplineReport | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [idA, setIdA] = useState<string>("");
  const [idB, setIdB] = useState<string>("");
  const [diff, setDiff] = useState<StrategyDiff | null>(null);
  const [loadingDiff, setLoadingDiff] = useState(false);
  const [diffError, setDiffError] = useState<string | null>(null);

  const loadRanked = useCallback(async () => {
    setLoadingList(true);
    const [data, disciplineData] = await Promise.all([
      fetchRankedStrategies(limit),
      fetchPerformanceDiscipline(limit),
    ]);
    if (data) {
      setReport(data);
      setListError(null);
    } else {
      setListError("Ranked strategies endpoint unreachable.");
    }
    if (disciplineData) {
      setDiscipline(disciplineData);
    }
    setLoadingList(false);
  }, [limit]);

  useEffect(() => {
    loadRanked();
  }, [loadRanked]);

  const rows: StrategyComparisonRecord[] = useMemo(
    () => report?.records ?? [],
    [report],
  );

  const loadDiff = useCallback(async (a: string, b: string) => {
    if (!a || !b || a === b) {
      setDiff(null);
      return;
    }
    setLoadingDiff(true);
    setDiffError(null);
    const data = await fetchStrategyDiff(a, b);
    if (data) {
      setDiff(data);
    } else {
      setDiff(null);
      setDiffError("Diff endpoint unreachable or returned no payload.");
    }
    setLoadingDiff(false);
  }, []);

  useEffect(() => {
    if (mode === "diff") {
      loadDiff(idA, idB);
    }
  }, [mode, idA, idB, loadDiff]);

  const openDiffWith = (id: string) => {
    setIdA(id);
    if (idB && idB !== id) {
      // keep existing B
    } else {
      // pick first non-equal as B
      const other = rows.find((r) => r.strategy_id !== id);
      setIdB(other?.strategy_id ?? "");
    }
    setMode("diff");
  };

  return (
    <div className="strategy-comparison-page">
      <GlassPanel
        title="Strategy Comparison"
        subtitle="Observational ranking and diff — not trade advisory"
      >
        <div className="comparison-mode-toggle">
          <button
            className={`mode-btn ${mode === "ranked" ? "active" : ""}`}
            onClick={() => setMode("ranked")}
          >
            Ranked
          </button>
          <button
            className={`mode-btn ${mode === "diff" ? "active" : ""}`}
            onClick={() => setMode("diff")}
          >
            Diff
          </button>
          {mode === "ranked" && (
            <label className="limit-selector">
              <span className="field-label">Limit</span>
              <select
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
              >
                {LIMIT_OPTIONS.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
        {report?.plain_english_summary && (
          <p className="plain-english-block">{report.plain_english_summary}</p>
        )}
      </GlassPanel>

      <GlassPanel
        title="Performance Discipline"
        subtitle={discipline?.plain_english_summary ?? "Checking cost, drawdown, OOS, robustness, and mode-separation coverage"}
        variant={discipline?.status === "OK" ? "default" : "warning"}
      >
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
          <StatusChip
            label={discipline?.status ?? "SYNCING"}
            variant={discipline?.status === "OK" ? "success" : discipline?.status === "ATTENTION" ? "warning" : "muted"}
            size="sm"
          />
          <StatusChip
            label={`${discipline?.record_count ?? 0} RECORDS`}
            variant="info"
            size="sm"
          />
          <StatusChip
            label={`${discipline?.attention_count ?? 0} NEED REVIEW`}
            variant={(discipline?.attention_count ?? 0) ? "warning" : "success"}
            size="sm"
          />
        </div>
        <table className="comparison-table">
          <thead>
            <tr>
              <th>Strategy</th>
              <th>Mode</th>
              <th>Coverage</th>
              <th>Costs</th>
              <th>OOS / WF</th>
              <th>Mode Sep</th>
              <th>Missing Critical</th>
            </tr>
          </thead>
          <tbody>
            {(discipline?.records ?? []).slice(0, 6).map((row) => (
              <tr key={`${row.source}-${row.strategy_id}`}>
                <td className="mono" title={row.strategy_id}>{truncate(row.strategy_id, 20)}</td>
                <td className="mono">{row.mode_label}</td>
                <td className="mono">{fmtNum(row.coverage_pct, 1)}%</td>
                <td>
                  <StatusChip label={row.cost_model_present ? "COVERED" : "MISSING"} variant={row.cost_model_present ? "success" : "warning"} size="sm" />
                </td>
                <td>
                  <StatusChip label={row.out_of_sample_present ? "COVERED" : "MISSING"} variant={row.out_of_sample_present ? "success" : "warning"} size="sm" />
                </td>
                <td>
                  <StatusChip label={row.mode_separation_present ? "COVERED" : "MISSING"} variant={row.mode_separation_present ? "success" : "warning"} size="sm" />
                </td>
                <td>{row.critical_missing.length ? row.critical_missing.join(", ") : "none"}</td>
              </tr>
            ))}
            {(!discipline || discipline.records.length === 0) && (
              <tr>
                <td colSpan={7} className="muted-cell">No strategy performance discipline records loaded.</td>
              </tr>
            )}
          </tbody>
        </table>
        {discipline?.diagnostic_hints?.length ? (
          <p className="plain-english-block">{discipline.diagnostic_hints.slice(0, 3).join(" ")}</p>
        ) : null}
        <p className="muted-cell">{discipline?.claim_boundary ?? "Read-only performance coverage check; no strategy recommendation or trading authority."}</p>
      </GlassPanel>

      {mode === "ranked" && (
        <GlassPanel title="Ranked strategies">
          {listError && <div className="api-status-strip">{listError}</div>}
          <table className="comparison-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Strategy</th>
                <th>Source</th>
                <th>Symbol</th>
                <th>TF</th>
                <th>Family</th>
                <th>PF</th>
                <th>DD %</th>
                <th>WF grade</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr>
                  <td colSpan={10} className="muted-cell">
                    {loadingList ? "Loading…" : "No strategies returned."}
                  </td>
                </tr>
              )}
              {rows.map((r) => (
                <tr
                  key={r.strategy_id}
                  className="comparison-row"
                  onClick={() => openDiffWith(r.strategy_id)}
                >
                  <td className="mono">{r.rank}</td>
                  <td className="mono" title={r.strategy_id}>
                    {truncate(r.strategy_id, 18)}
                  </td>
                  <td>
                    <StatusChip
                      label={r.source || "—"}
                      variant={sourceVariant(r.source)}
                      size="sm"
                    />
                  </td>
                  <td className="mono">{r.symbol ?? "—"}</td>
                  <td className="mono">{r.timeframe ?? "—"}</td>
                  <td>{r.family ?? "—"}</td>
                  <td className="mono">{fmtNum(r.profit_factor)}</td>
                  <td className="mono">{fmtNum(r.max_drawdown_pct)}</td>
                  <td>{r.walk_forward_grade ?? "—"}</td>
                  <td className={`mono ${scoreClass(r.composite_score)}`}>
                    {fmtNum(r.composite_score, 1)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </GlassPanel>
      )}

      {mode === "diff" && (
        <GlassPanel title="Diff" subtitle="Field-by-field comparison">
          <div className="diff-controls">
            <label className="limit-selector">
              <span className="field-label">A</span>
              <select value={idA} onChange={(e) => setIdA(e.target.value)}>
                <option value="">— pick strategy —</option>
                {rows.map((r) => (
                  <option key={r.strategy_id} value={r.strategy_id}>
                    {truncate(r.strategy_id, 22)} ({r.symbol ?? "—"} {r.timeframe ?? ""})
                  </option>
                ))}
              </select>
            </label>
            <label className="limit-selector">
              <span className="field-label">B</span>
              <select value={idB} onChange={(e) => setIdB(e.target.value)}>
                <option value="">— pick strategy —</option>
                {rows.map((r) => (
                  <option key={r.strategy_id} value={r.strategy_id}>
                    {truncate(r.strategy_id, 22)} ({r.symbol ?? "—"} {r.timeframe ?? ""})
                  </option>
                ))}
              </select>
            </label>
          </div>
          <DiffPanel diff={diff} loading={loadingDiff} error={diffError} />
        </GlassPanel>
      )}
    </div>
  );
}
