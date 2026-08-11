import { useCallback, useEffect, useState } from "react";
import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import {
  fetchProfessionalClaims,
  type ProfessionalClaimHit,
  type ProfessionalClaimsReport,
  type ProfessionalDisclosureStatus,
} from "../data/api";
import "./RiskDisclosurePage.css";

type ChipVariant = "success" | "warning" | "danger" | "info" | "muted";

function statusVariant(status?: string): ChipVariant {
  const normalized = (status ?? "").toUpperCase();
  if (normalized === "OK" || normalized === "COVERED") return "success";
  if (normalized === "ATTENTION" || normalized === "WARNING" || normalized === "WARMING") return "warning";
  if (normalized === "MISSING" || normalized === "MISSING_DRAFT_COPY" || normalized === "FAIL") return "danger";
  if (!normalized || normalized === "UNKNOWN") return "muted";
  return "info";
}

function joinList(items?: string[]): string {
  return items?.filter(Boolean).join(", ") || "Not specified";
}

function formatForbiddenClaim(row: Record<string, unknown>): string {
  const label = row.label ?? row.claim_type ?? row.type ?? row.name;
  const detail = row.detail ?? row.description ?? row.example ?? row.reason;
  return [label, detail].filter((value) => typeof value === "string" && value.trim()).join(": ");
}

function DisclosureTable({ rows }: { rows: ProfessionalDisclosureStatus[] }) {
  return (
    <div className="risk-disclosure-table-wrap">
      <table className="risk-disclosure-table">
        <thead>
          <tr>
            <th>Disclosure</th>
            <th>Status</th>
            <th>Minimum copy</th>
            <th>Recommended surfaces</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={4} className="risk-disclosure-muted">
                Disclosure report is warming.
              </td>
            </tr>
          )}
          {rows.map((row) => (
            <tr key={row.key ?? row.label}>
              <td>{row.label ?? row.key ?? "Disclosure"}</td>
              <td>
                <StatusChip
                  label={row.status ?? "UNKNOWN"}
                  variant={statusVariant(row.status)}
                  size="sm"
                />
              </td>
              <td>{row.minimum_copy ?? "No minimum copy provided."}</td>
              <td>{joinList(row.recommended_surfaces)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ClaimHitsTable({ hits }: { hits: ProfessionalClaimHit[] }) {
  return (
    <div className="risk-disclosure-table-wrap">
      <table className="risk-disclosure-table">
        <thead>
          <tr>
            <th>Location</th>
            <th>Claim type</th>
            <th>Severity</th>
            <th>Excerpt</th>
          </tr>
        </thead>
        <tbody>
          {hits.length === 0 && (
            <tr>
              <td colSpan={4} className="risk-disclosure-muted">
                No risky claim phrases were found in scanned app copy.
              </td>
            </tr>
          )}
          {hits.slice(0, 12).map((hit) => (
            <tr key={`${hit.path ?? "path"}-${hit.line ?? 0}-${hit.claim_type ?? "claim"}`}>
              <td className="mono">{hit.path ?? "unknown"}:{hit.line ?? "?"}</td>
              <td>{hit.label ?? hit.claim_type ?? "claim"}</td>
              <td>
                <StatusChip
                  label={hit.severity ?? "UNKNOWN"}
                  variant={hit.severity === "needs_review" ? "warning" : "muted"}
                  size="sm"
                />
              </td>
              <td>{hit.excerpt ?? ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function RiskDisclosurePage() {
  const [report, setReport] = useState<ProfessionalClaimsReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshedAt, setRefreshedAt] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    const data = await fetchProfessionalClaims();
    if (data) {
      setReport(data);
      setError(null);
      setRefreshedAt(new Date().toISOString());
    } else {
      setError("Professional claims and disclosure endpoint unreachable.");
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const disclosures = report?.required_disclosures ?? [];
  const missing = report?.missing_disclosures ?? [];
  const hits = report?.claim_hits ?? [];
  const needsReview = hits.filter((hit) => hit.severity === "needs_review");
  const doc = report?.disclosure_document;
  const forbiddenClaimTypes = report?.copy_policy?.forbidden_claim_types ?? [];
  const preferredLanguage = report?.copy_policy?.preferred_language ?? [];

  return (
    <div className="risk-disclosure-page">
      <GlassPanel
        title="Risk Disclosure"
        subtitle="Read-only trading, AI, broker, and copy-claim boundaries"
      >
        <div className="risk-disclosure-status-grid">
          <div className="risk-disclosure-status-cell">
            <span className="field-label">Report status</span>
            <StatusChip
              label={report?.status ?? (loading ? "LOADING" : "UNAVAILABLE")}
              variant={statusVariant(report?.status)}
            />
          </div>
          <div className="risk-disclosure-status-cell">
            <span className="field-label">Risky claims</span>
            <StatusChip
              label={`${report?.risky_claim_count ?? needsReview.length} TO REVIEW`}
              variant={(report?.risky_claim_count ?? needsReview.length) > 0 ? "warning" : "success"}
            />
          </div>
          <div className="risk-disclosure-status-cell">
            <span className="field-label">Disclosure draft</span>
            <StatusChip
              label={doc?.present ? "PRESENT" : "MISSING"}
              variant={doc?.present ? "success" : "warning"}
            />
          </div>
          <div className="risk-disclosure-status-cell">
            <span className="field-label">Last fetched</span>
            <span className="field-value mono">{refreshedAt ?? "not fetched"}</span>
          </div>
        </div>
        {error && <div className="api-status-strip">{error}</div>}
        <div className="risk-disclosure-boundary">
          {report?.claim_boundary
            ?? "This page is disclosure visibility only. It does not authorize live trading, provide investment advice, or promise returns."}
        </div>
      </GlassPanel>

      <GlassPanel title="Plain-Language Boundaries" subtitle="The wording CAS Forex should consistently surface">
        <div className="risk-disclosure-copy-grid">
          <section>
            <h4>No Profit Guarantee</h4>
            <p>
              Automated trading can lose money. The system can control process, limits, and auditability,
              but it does not remove trading risk or assure future results.
            </p>
          </section>
          <section>
            <h4>AI Limitations</h4>
            <p>
              AI decisions must stay inside deterministic risk controls, broker permissions, symbol rules,
              spread limits, and margin checks. AI confidence is not a win probability.
            </p>
          </section>
          <section>
            <h4>Broker Execution</h4>
            <p>
              Pricing, spreads, slippage, swaps, withdrawals, leverage, and final fills are controlled by
              the broker or terminal. CAS Forex should reconcile against broker state as the source of truth.
            </p>
          </section>
          <section>
            <h4>Paper, Demo, and Live</h4>
            <p>
              Paper, demo, and live results are separate operating modes. Simulated or demo performance
              should never be shown as live money performance.
            </p>
          </section>
        </div>
      </GlassPanel>

      <GlassPanel title="Required Disclosure Coverage" subtitle="Minimum copy expected on product surfaces">
        <DisclosureTable rows={disclosures} />
      </GlassPanel>

      <GlassPanel title="Missing Disclosure Items" subtitle="Items the report says still need draft copy or coverage">
        <DisclosureTable rows={missing} />
      </GlassPanel>

      <GlassPanel title="Copy Policy" subtitle="Forbidden claims and preferred professional wording">
        <div className="risk-disclosure-policy-grid">
          <div>
            <h4>Forbidden claim types</h4>
            <ul className="risk-disclosure-list">
              {forbiddenClaimTypes.length === 0 && <li>No forbidden claim types returned by report.</li>}
              {forbiddenClaimTypes.map((row, index) => (
                <li key={index}>{formatForbiddenClaim(row) || "Unlabeled forbidden claim type"}</li>
              ))}
            </ul>
          </div>
          <div>
            <h4>Preferred language</h4>
            <ul className="risk-disclosure-list">
              {preferredLanguage.length === 0 && <li>No preferred wording returned by report.</li>}
              {preferredLanguage.map((phrase) => (
                <li key={phrase}>{phrase}</li>
              ))}
            </ul>
          </div>
        </div>
      </GlassPanel>

      <GlassPanel title="Risky Claim Hits" subtitle="Scanned wording that may need legal or product review">
        <ClaimHitsTable hits={hits} />
      </GlassPanel>

      <GlassPanel title="Disclosure Draft" subtitle="Local source document status">
        <div className="risk-disclosure-doc-grid">
          <div>
            <span className="field-label">Path</span>
            <span className="field-value mono">{doc?.path ?? "docs/legal/CAS_FOREX_DISCLOSURE_DRAFT.md"}</span>
          </div>
          <div>
            <span className="field-label">Lines</span>
            <span className="field-value mono">{doc?.line_count ?? 0}</span>
          </div>
          <div>
            <span className="field-label">Summary</span>
            <span className="field-value">{doc?.summary ?? "Disclosure document status is loading."}</span>
          </div>
        </div>
      </GlassPanel>
    </div>
  );
}
