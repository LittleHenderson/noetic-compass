/* ── CAS Forex — Webhook Notification Subscription Panel ──
 *
 * Operator-facing surface for outbound webhook delivery (Slack
 * incoming hook, Discord webhook, Teams workflow URL, custom
 * endpoint). Lists subscriptions, lets the operator add or remove,
 * and fires a test dispatch. Observational system events only —
 * no advisory payloads.
 */

import { useCallback, useEffect, useState } from "react";
import { GlassPanel } from "./GlassPanel";
import { StatusChip } from "./StatusChip";
import {
  fetchWebhookSubscriptions,
  subscribeWebhook,
  testWebhookAll,
  unsubscribeWebhook,
  type WebhookSubscriptionItem,
  type WebhookTestResult,
} from "../data/api";
import "./LiveTelemetryTable.css";
import "./SubscriptionPanels.css";

function truncateUrl(url: string, max = 56): string {
  if (url.length <= max) return url;
  return `${url.slice(0, max)}…`;
}

export function WebhookSubscriptionPanel() {
  const [subscriptions, setSubscriptions] = useState<WebhookSubscriptionItem[]>([]);
  const [busy, setBusy] = useState<boolean>(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [newUrl, setNewUrl] = useState<string>("");
  const [newLabel, setNewLabel] = useState<string>("");
  const [testResults, setTestResults] = useState<WebhookTestResult[]>([]);

  const refresh = useCallback(async () => {
    const data = await fetchWebhookSubscriptions();
    if (data) {
      setSubscriptions(data.subscriptions);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleAdd = useCallback(async () => {
    const url = newUrl.trim();
    if (!url) {
      setError("Webhook URL required.");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await subscribeWebhook(url, newLabel.trim());
      if (!result.ok) {
        setError(`Add failed: ${result.error.message}`);
        return;
      }
      setMessage("Webhook added.");
      setNewUrl("");
      setNewLabel("");
      await refresh();
    } finally {
      setBusy(false);
    }
  }, [newUrl, newLabel, refresh]);

  const handleRemove = useCallback(
    async (url: string) => {
      setBusy(true);
      setError(null);
      setMessage(null);
      try {
        const result = await unsubscribeWebhook(url);
        if (!result.ok) {
          setError(`Remove failed: ${result.error.message}`);
          return;
        }
        setMessage("Webhook removed.");
        await refresh();
      } finally {
        setBusy(false);
      }
    },
    [refresh],
  );

  const handleTest = useCallback(async () => {
    if (subscriptions.length === 0) {
      setError(null);
      setTestResults([]);
      setMessage("No webhook subscriptions on server yet. Add a webhook URL first, then send a test.");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    setTestResults([]);
    try {
      const result = await testWebhookAll(
        undefined,
        "CAS Forex",
        "Test webhook from the cockpit (observational).",
      );
      if (!result.ok) {
        setError(`Test dispatch failed: ${result.error.message}`);
        return;
      }
      setTestResults(result.data.results);
      if (result.data.results.length === 0) {
        setMessage("No webhook subscriptions to dispatch to.");
      }
    } finally {
      setBusy(false);
    }
  }, [subscriptions.length]);

  return (
    <GlassPanel
      title="Webhook Notifications"
      subtitle="Operator-controlled outbound webhooks (Slack / Discord / Teams / custom) — observational events only"
    >
      <div className="webhook-subscription-panel">
        <div className="notification-status-row">
          <StatusChip
            label={`subscriptions on server: ${subscriptions.length}`}
            variant="info"
            size="sm"
          />
          <button
            type="button"
            className="notification-button"
            disabled={busy}
            onClick={() => void handleTest()}
            title={subscriptions.length === 0 ? "No webhook subscriptions on server yet." : undefined}
          >
            Send test webhook
          </button>
        </div>

        <div className="webhook-add-form">
          <input
            type="text"
            className="mobile-api-input"
            placeholder="https://hooks.slack.com/services/... or other webhook URL"
            value={newUrl}
            onChange={(e) => setNewUrl(e.target.value)}
            spellCheck={false}
          />
          <input
            type="text"
            className="mobile-api-input"
            placeholder="Label (optional, e.g. ops-channel)"
            value={newLabel}
            onChange={(e) => setNewLabel(e.target.value)}
            spellCheck={false}
          />
          <button
            type="button"
            className="notification-button"
            disabled={busy}
            onClick={() => void handleAdd()}
          >
            Add
          </button>
        </div>

        {message && (
          <div
            className="control-field-desc"
            style={{ color: "var(--success)" }}
          >
            {message}
          </div>
        )}
        {error && (
          <div
            className="control-field-desc"
            style={{ color: "var(--danger)" }}
          >
            {error}
          </div>
        )}

        {subscriptions.length === 0 ? (
          <div className="live-telemetry-empty">No webhook subscriptions registered</div>
        ) : (
          <div className="live-telemetry-table-wrap">
            <table className="live-telemetry-table">
              <thead>
                <tr>
                  <th>Label</th>
                  <th>URL</th>
                  <th>Created</th>
                  <th>Last Used</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {subscriptions.map((s) => (
                  <tr key={s.webhook_url} className="webhook-row">
                    <td>{s.label || "—"}</td>
                    <td className="mono" title={s.webhook_url}>
                      {truncateUrl(s.webhook_url)}
                    </td>
                    <td className="mono">{s.created_at_iso || "—"}</td>
                    <td className="mono">{s.last_used_at_iso ?? "—"}</td>
                    <td>
                      <button
                        type="button"
                        className="notification-button ghost"
                        disabled={busy}
                        onClick={() => void handleRemove(s.webhook_url)}
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {testResults.length > 0 && (
          <div className="live-telemetry-table-wrap">
            <table className="live-telemetry-table">
              <thead>
                <tr>
                  <th>Webhook URL</th>
                  <th>Success</th>
                  <th className="num">Status</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody>
                {testResults.map((row, i) => (
                  <tr key={i}>
                    <td className="mono">{truncateUrl(row.webhook_url)}</td>
                    <td>
                      <StatusChip
                        label={row.success ? "yes" : "no"}
                        variant={row.success ? "success" : "danger"}
                        size="sm"
                      />
                    </td>
                    <td className="num mono">{row.status_code ?? "—"}</td>
                    <td>{row.error_message ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </GlassPanel>
  );
}
