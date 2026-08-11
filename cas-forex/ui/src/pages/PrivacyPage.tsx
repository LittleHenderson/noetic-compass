import { GlassPanel } from "../components/GlassPanel";
import { StatusChip } from "../components/StatusChip";
import "./RiskDisclosurePage.css";

export function PrivacyPage() {
  return (
    <div className="risk-disclosure-page">
      <GlassPanel title="Privacy Policy" subtitle="Draft data handling summary for CAS Forex">
        <div className="risk-disclosure-status-grid">
          <div className="risk-disclosure-status-cell">
            <span className="field-label">Document status</span>
            <StatusChip label="DRAFT" variant="warning" />
          </div>
          <div className="risk-disclosure-status-cell">
            <span className="field-label">Primary storage</span>
            <span className="field-value">Local files and runtime stores</span>
          </div>
          <div className="risk-disclosure-status-cell">
            <span className="field-label">Legal review</span>
            <StatusChip label="REQUIRED BEFORE PUBLIC USE" variant="warning" />
          </div>
        </div>
        <div className="risk-disclosure-boundary">
          This privacy policy is a draft for local development. Hosted, paid, cloud, mobile-store, or
          multi-user deployment requires final privacy review and jurisdiction-specific updates.
        </div>
      </GlassPanel>

      <GlassPanel title="Data CAS Forex May Store" subtitle="Local operational evidence">
        <div className="risk-disclosure-copy-grid">
          <section>
            <h4>Trading Evidence</h4>
            <p>
              The app may store orders, attempted dispatches, broker receipts, account snapshots, positions,
              strategy decisions, risk checks, blocked-trade reasons, and performance reports.
            </p>
          </section>
          <section>
            <h4>Owner Settings</h4>
            <p>
              The app may store owner authorization switches, risk caps, AI dial settings, manual-order
              journal reasons, notification preferences, and local device pairing state.
            </p>
          </section>
          <section>
            <h4>Secrets</h4>
            <p>
              Broker/API secrets should remain server-side or in encrypted runtime stores. Secrets should not
              be exposed to browser JavaScript, committed to source control, or pasted into public logs.
            </p>
          </section>
          <section>
            <h4>Notifications</h4>
            <p>
              Web push and webhook destinations may receive observational system events such as risk changes,
              blocked trades, live switch changes, and unprotected-position alerts.
            </p>
          </section>
        </div>
      </GlassPanel>

      <GlassPanel title="Data Handling Boundaries" subtitle="What this local app should and should not do">
        <ul className="risk-disclosure-list">
          <li>CAS Forex should not store raw bank-card numbers or raw bank login credentials.</li>
          <li>Payment, deposit, withdrawal, KYC, and broker custody details belong with the broker or payment provider.</li>
          <li>Local logs may include trading and diagnostic evidence; protect backups and shared folders accordingly.</li>
          <li>Before public launch, add account deletion, data export, retention, and support processes.</li>
        </ul>
      </GlassPanel>
    </div>
  );
}
