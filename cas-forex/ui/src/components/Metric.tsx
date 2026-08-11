/* ── Metric — the canonical provenance-carrying value row ──
 *
 * Every number or status this cockpit displays must say where it came from.
 * `provenance` is REQUIRED: omitting it is a TypeScript compile error, which
 * is the structural refusal — there is no code path that renders a bare value.
 *
 *   live     — fetched from the running API during this session; no marker.
 *   cached   — real data from an earlier session/packet; amber "CACHED" tag
 *              (pass `asOf` to show its age).
 *   unproven — placeholder, fallback, or synthetic content that has NOT been
 *              proven against live state; dimmed with an "UNPROVEN" tag. A
 *              fallback that renders "OWNER GATED" styled like a fact was this
 *              cockpit's most dangerous habit — this tag is its tombstone.
 *
 * This file must remain the ONLY Metric definition. The per-file copies that
 * predate it are being retired page-by-page during the nav rebuild; a ratchet
 * test (tests/test_metric_provenance.py) fails the suite if a new local copy
 * appears or the count of legacy copies rises.
 */

export type MetricProvenance = "live" | "cached" | "unproven";

export interface MetricProps {
  label: string;
  value: string;
  provenance: MetricProvenance;
  /** ISO timestamp of when a `cached` value was captured; renders its age. */
  asOf?: string;
  mono?: boolean;
  danger?: boolean;
  warning?: boolean;
}

function cachedAge(asOf: string | undefined): string | null {
  if (!asOf) return null;
  const captured = Date.parse(asOf);
  if (!Number.isFinite(captured)) return null;
  const seconds = Math.max(0, Math.round((Date.now() - captured) / 1000));
  if (seconds < 90) return `${seconds}s old`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 90) return `${minutes}m old`;
  const hours = Math.round(minutes / 60);
  if (hours < 36) return `${hours}h old`;
  return `${Math.round(hours / 24)}d old`;
}

export function Metric({ label, value, provenance, asOf, mono, danger, warning }: MetricProps) {
  const age = provenance === "cached" ? cachedAge(asOf) : null;
  return (
    <div className={`summary-row metric-${provenance}`}>
      <span className="field-label">{label}</span>
      <span className="metric-value-group">
        <span
          className={`field-value ${mono ? "mono" : ""}`}
          style={{ color: danger ? "var(--danger)" : warning ? "var(--warning)" : undefined }}
        >
          {value}
        </span>
        {provenance === "cached" && (
          <span className="metric-provenance-tag metric-tag-cached" title={asOf ? `Captured ${asOf}` : "From a previous session"}>
            CACHED{age ? ` · ${age}` : ""}
          </span>
        )}
        {provenance === "unproven" && (
          <span
            className="metric-provenance-tag metric-tag-unproven"
            title="Placeholder or fallback content — not proven against live state"
          >
            UNPROVEN
          </span>
        )}
      </span>
    </div>
  );
}
