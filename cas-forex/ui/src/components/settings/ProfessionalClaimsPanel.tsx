/* Extracted from pages/SettingsPage.tsx (settings decomposition, slice 1). */

import { GlassPanel } from "../../components/GlassPanel";
import { StatusChip } from "../../components/StatusChip";
import { ProfessionalClaimsReport, fetchProfessionalClaims } from "../../data/api";
import { ControlField } from "./ControlField";
import { useEffect, useState } from "react";

export function ProfessionalClaimsPanel() {
  const [report, setReport] = useState<ProfessionalClaimsReport | null>(null);

  useEffect(() => {
    void fetchProfessionalClaims().then((s) => { if (s) setReport(s); });
  }, []);

  const hits = report?.claim_hits ?? [];
  const needsReview = hits.filter((hit) => hit.severity === "needs_review");
  const disclosures = report?.required_disclosures ?? [];
  const missing = report?.missing_disclosures ?? [];
  const doc = report?.disclosure_document;
  const preferredLanguage = report?.copy_policy?.preferred_language ?? [];

  return (
    <GlassPanel title="Professional Claims & Disclosures" subtitle="Copy audit, disclosure draft, and AI/trading claim boundaries">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <StatusChip
          label={report?.status ?? "SYNCING"}
          variant={report?.status === "OK" ? "success" : report?.status === "ATTENTION" ? "warning" : "muted"}
          size="sm"
        />
        <StatusChip
          label={`${report?.risky_claim_count ?? needsReview.length} CLAIMS TO REVIEW`}
          variant={(report?.risky_claim_count ?? needsReview.length) ? "warning" : "success"}
          size="sm"
        />
        <StatusChip
          label={doc?.present ? "DISCLOSURE DRAFT PRESENT" : "DISCLOSURE DRAFT MISSING"}
          variant={doc?.present ? "success" : "warning"}
          size="sm"
        />
        <StatusChip
          label={`${missing.length} DISCLOSURES MISSING`}
          variant={missing.length ? "warning" : "success"}
          size="sm"
        />
      </div>
      <div className="control-grid">
        <ControlField label="Disclosure Draft" value={doc?.path ?? "docs/legal/CAS_FOREX_DISCLOSURE_DRAFT.md"} mono description={doc?.summary ?? "Loading disclosure document status."} danger={doc?.present === false} />
        <ControlField label="Boundary References" value={`${report?.boundary_reference_count ?? 0}`} mono description="Allowed guardrail references such as no-guarantee wording and disclosure copy." />
        <ControlField label="Preferred Language" value={preferredLanguage.slice(0, 3).join(", ") || "risk-managed trading"} description="Use bounded language instead of profit promises or fake AI certainty." />
      </div>
      <div className="control-section" style={{ marginTop: 12 }}>
        <h4 className="control-section-title">Required Disclosure Coverage</h4>
        <div className="positions-table-wrap ai-dial-table-wrap">
          <table className="data-table ai-dial-table">
            <thead>
              <tr>
                <th>Disclosure</th>
                <th>Status</th>
                <th>Minimum Copy</th>
                <th>Surfaces</th>
              </tr>
            </thead>
            <tbody>
              {disclosures.map((row) => (
                <tr key={row.key ?? row.label}>
                  <td>{row.label ?? row.key}</td>
                  <td>
                    <StatusChip
                      label={row.status ?? "UNKNOWN"}
                      variant={row.status === "COVERED" ? "success" : "warning"}
                      size="sm"
                    />
                  </td>
                  <td>{row.minimum_copy ?? "No minimum copy provided."}</td>
                  <td>{(row.recommended_surfaces ?? []).join(", ")}</td>
                </tr>
              ))}
              {disclosures.length === 0 && (
                <tr>
                  <td colSpan={4}>Disclosure coverage is warming.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      <div className="control-section" style={{ marginTop: 12 }}>
        <h4 className="control-section-title">Risky Claim Hits</h4>
        <div className="positions-table-wrap ai-dial-table-wrap">
          <table className="data-table ai-dial-table">
            <thead>
              <tr>
                <th>Location</th>
                <th>Claim Type</th>
                <th>Severity</th>
                <th>Excerpt</th>
              </tr>
            </thead>
            <tbody>
              {hits.slice(0, 8).map((hit) => (
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
              {hits.length === 0 && (
                <tr>
                  <td colSpan={4}>No risky claim phrases found in scanned app copy.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      <div className="control-field-desc" style={{ marginTop: 10 }}>
        {report?.claim_boundary ?? "Professional claims posture is read-only and does not authorize trading or promise returns."}
      </div>
    </GlassPanel>
  );
}

