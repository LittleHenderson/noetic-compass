import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import "./RiskDisclosurePage.css";

export function TermsPage() {
  return (
    <div className="risk-disclosure-page">
      <GlassPanel title="Terms of Service" subtitle="Draft owner-facing terms for CAS Forex">
        <div className="risk-disclosure-status-grid">
          <div className="risk-disclosure-status-cell">
            <span className="field-label">Document status</span>
            <StatusChip label="DRAFT" variant="warning" />
          </div>
          <div className="risk-disclosure-status-cell">
            <span className="field-label">Scope</span>
            <span className="field-value">Local owner-operated trading cockpit</span>
          </div>
          <div className="risk-disclosure-status-cell">
            <span className="field-label">Legal review</span>
            <StatusChip label="REQUIRED BEFORE PUBLIC USE" variant="warning" />
          </div>
        </div>
        <div className="risk-disclosure-boundary">
          These terms are draft product copy for local development. They are not legal advice and are not a
          substitute for review by qualified counsel before public, hosted, paid, or multi-user use.
        </div>
      </GlassPanel>

      <GlassPanel title="Use of CAS Forex" subtitle="Operational boundaries">
        <div className="risk-disclosure-copy-grid">
          <section>
            <h4>Owner Responsibility</h4>
            <p>
              The owner is responsible for broker account setup, credentials, funding decisions, strategy
              configuration, risk limits, live authorization switches, and any decision to use live money.
            </p>
          </section>
          <section>
            <h4>No Profit Guarantee</h4>
            <p>
              CAS Forex provides automation, risk controls, monitoring, and audit evidence. It does not
              promise profitable results, account growth, fill quality, broker behavior, or future outcomes.
            </p>
          </section>
          <section>
            <h4>Automated Trading</h4>
            <p>
              Automated and AI-assisted trading can open, manage, or block trades only through configured
              gates. Those gates can reduce some process risks but cannot remove market risk.
            </p>
          </section>
          <section>
            <h4>Broker Boundary</h4>
            <p>
              Broker pricing, spreads, swaps, leverage, margin, order acceptance, withdrawals, and final
              account records are controlled by the broker or terminal, not by CAS Forex.
            </p>
          </section>
        </div>
      </GlassPanel>

      <GlassPanel title="Owner Controls" subtitle="Authority and audit commitments">
        <ul className="risk-disclosure-list">
          <li>Live trading requires explicit owner authorization and action-time gate checks.</li>
          <li>Risk-cap loosening, AI-dial loosening, and manual orders require anti-impulse journal evidence.</li>
          <li>Emergency controls are intended to pause automation or reduce broker exposure, subject to broker connectivity.</li>
          <li>Audit records are diagnostic evidence and do not prove profitability or regulatory compliance.</li>
        </ul>
      </GlassPanel>
    </div>
  );
}
