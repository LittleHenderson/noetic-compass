/* ── CAS Forex — Web Push Notification Subscription Panel ──
 *
 * Operator-facing surface for the browser Push API. Lets the
 * operator grant permission, register a subscription with the
 * backend, send a test push, and unsubscribe. All actions are
 * operator-initiated. Plain text. No advisory language.
 *
 * Push API requires a secure context (HTTPS or localhost). If the
 * environment isn't secure or the browser lacks ServiceWorker /
 * PushManager, an explanatory note replaces the controls.
 */

import { useCallback, useEffect, useState } from "react";
import { GlassPanel } from "./GlassPanel";
import { StatusChip } from "./StatusChip";
import {
  fetchPushBackendStatus,
  fetchPushSubscriptions,
  subscribeWebPush,
  testPushAll,
  unsubscribeWebPush,
  type PushBackendStatus,
  type PushSubscriptionItem,
  type PushTestResult,
} from "../data/api";
import "./LiveTelemetryTable.css";
import "./SubscriptionPanels.css";

type PermissionState = "default" | "granted" | "denied" | "unknown";

const VAPID_PUBLIC_KEY: string =
  (import.meta.env.VITE_CAS_FOREX_VAPID_PUBLIC_KEY as string | undefined) ?? "";

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  const output = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i += 1) {
    output[i] = rawData.charCodeAt(i);
  }
  return output;
}

function arrayBufferToBase64(buffer: ArrayBuffer | null): string {
  if (!buffer) return "";
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.byteLength; i += 1) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary);
}

function isPushApiAvailable(): boolean {
  if (typeof window === "undefined") return false;
  if (!("serviceWorker" in navigator)) return false;
  if (!("PushManager" in window)) return false;
  if (!("Notification" in window)) return false;
  return Boolean(window.isSecureContext);
}

export function NotificationSubscriptionPanel() {
  const [permission, setPermission] = useState<PermissionState>("unknown");
  const [registered, setRegistered] = useState<boolean>(false);
  const [serverSubscriptions, setServerSubscriptions] = useState<PushSubscriptionItem[]>([]);
  const [backendStatus, setBackendStatus] = useState<PushBackendStatus | null>(null);
  const [currentEndpoint, setCurrentEndpoint] = useState<string | null>(null);
  const [busy, setBusy] = useState<boolean>(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<PushTestResult[]>([]);

  const apiAvailable = isPushApiAvailable();
  const effectiveVapidPublicKey = backendStatus
    ? backendStatus.vapid_public_key || ""
    : VAPID_PUBLIC_KEY;

  const refreshServer = useCallback(async () => {
    const [subscriptions, backend] = await Promise.all([
      fetchPushSubscriptions(),
      fetchPushBackendStatus(),
    ]);
    if (subscriptions) {
      setServerSubscriptions(subscriptions.subscriptions);
    }
    if (backend) {
      setBackendStatus(backend);
    }
  }, []);

  const refreshLocal = useCallback(async () => {
    if (!apiAvailable) return;
    setPermission((Notification.permission as PermissionState) ?? "unknown");
    try {
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.getSubscription();
      setRegistered(Boolean(sub));
      setCurrentEndpoint(sub?.endpoint ?? null);
    } catch {
      setRegistered(false);
      setCurrentEndpoint(null);
    }
  }, [apiAvailable]);

  useEffect(() => {
    void refreshServer();
    void refreshLocal();
  }, [refreshServer, refreshLocal]);

  const handleEnable = useCallback(async () => {
    if (!apiAvailable) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const perm = await Notification.requestPermission();
      setPermission(perm as PermissionState);
      if (perm !== "granted") {
        setError("Browser permission not granted.");
        return;
      }
      const reg = await navigator.serviceWorker.ready;
      let sub = await reg.pushManager.getSubscription();
      if (!sub) {
        if (!effectiveVapidPublicKey) {
          setError(
            "VAPID public key is not configured on the API side. Browser subscription cannot be created yet.",
          );
          return;
        }
        sub = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(effectiveVapidPublicKey),
        });
      }
      const p256dh = arrayBufferToBase64(sub.getKey("p256dh"));
      const auth = arrayBufferToBase64(sub.getKey("auth"));
      const result = await subscribeWebPush({
        endpoint: sub.endpoint,
        keys: { p256dh, auth },
        label: "cockpit",
      });
      if (!result.ok) {
        setError(`Backend rejected subscription: ${result.error.message}`);
        return;
      }
      setMessage("Subscribed.");
      setRegistered(true);
      setCurrentEndpoint(sub.endpoint);
      await refreshServer();
    } catch (err) {
      setError(`Subscription failed: ${(err as Error).message ?? String(err)}`);
    } finally {
      setBusy(false);
    }
  }, [apiAvailable, effectiveVapidPublicKey, refreshServer]);

  const handleDisable = useCallback(async () => {
    if (!apiAvailable) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.getSubscription();
      if (sub) {
        const endpoint = sub.endpoint;
        await sub.unsubscribe();
        const result = await unsubscribeWebPush(endpoint);
        if (!result.ok) {
          setError(`Backend unsubscribe failed: ${result.error.message}`);
        } else {
          setMessage("Unsubscribed.");
        }
      } else if (currentEndpoint) {
        const result = await unsubscribeWebPush(currentEndpoint);
        if (!result.ok) {
          setError(`Backend unsubscribe failed: ${result.error.message}`);
        } else {
          setMessage("Unsubscribed.");
        }
      }
      setRegistered(false);
      setCurrentEndpoint(null);
      await refreshServer();
    } catch (err) {
      setError(`Unsubscribe failed: ${(err as Error).message ?? String(err)}`);
    } finally {
      setBusy(false);
    }
  }, [apiAvailable, currentEndpoint, refreshServer]);

  const handleTest = useCallback(async () => {
    if (serverSubscriptions.length === 0) {
      setError(null);
      setTestResults([]);
      setMessage("No push subscriptions on server yet. Enable/register push notifications first, then send a test.");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    setTestResults([]);
    try {
      const result = await testPushAll();
      if (!result.ok) {
        setError(`Test dispatch failed: ${result.error.message}`);
        return;
      }
      setTestResults(result.data.results);
      if (result.data.results.length === 0) {
        setMessage("No subscriptions on server to dispatch to.");
      }
    } catch (err) {
      setError(`Test dispatch failed: ${(err as Error).message ?? String(err)}`);
    } finally {
      setBusy(false);
    }
  }, [serverSubscriptions.length]);

  const permissionVariant: "success" | "warning" | "danger" | "muted" =
    permission === "granted"
      ? "success"
      : permission === "denied"
        ? "danger"
        : permission === "default"
          ? "warning"
          : "muted";

  return (
    <GlassPanel
      title="Push Notifications"
      subtitle="Operator-controlled browser push subscriptions — observational system events only"
    >
      <div className="notification-subscription-panel">
        {!apiAvailable ? (
          <div className="control-field-desc">
            Push API is unavailable in this context. The Web Push API requires a
            secure context (HTTPS or localhost) and a browser with ServiceWorker +
            PushManager support. Open the cockpit over HTTPS or on localhost to
            enable push notifications.
          </div>
        ) : (
          <>
            <div className="notification-status-row">
              <StatusChip
                label={`permission: ${permission}`}
                variant={permissionVariant}
                size="sm"
              />
              <StatusChip
                label={`registered: ${registered ? "yes" : "no"}`}
                variant={registered ? "success" : "muted"}
                size="sm"
              />
              <StatusChip
                label={`subscriptions on server: ${serverSubscriptions.length}`}
                variant="info"
                size="sm"
              />
              <StatusChip
                label={`dispatch: ${backendStatus?.dispatch_ready ? "ready" : "not ready"}`}
                variant={backendStatus?.dispatch_ready ? "success" : "warning"}
                size="sm"
              />
            </div>

            <div className="notification-button-row">
              {permission !== "granted" && (
                <button
                  type="button"
                  className="notification-button"
                  disabled={busy}
                  onClick={() => void handleEnable()}
                >
                  Enable push notifications
                </button>
              )}
              {permission === "granted" && !registered && (
                <button
                  type="button"
                  className="notification-button"
                  disabled={busy}
                  onClick={() => void handleEnable()}
                >
                  Register subscription
                </button>
              )}
              {registered && (
                <button
                  type="button"
                  className="notification-button ghost"
                  disabled={busy}
                  onClick={() => void handleDisable()}
                >
                  Disable
                </button>
              )}
              <button
                type="button"
                className="notification-button"
                disabled={busy}
                onClick={() => void handleTest()}
                title={serverSubscriptions.length === 0 ? "No push subscriptions on server yet." : undefined}
              >
                Send test push
              </button>
            </div>

            {!effectiveVapidPublicKey && (
              <div
                className="control-field-desc"
                style={{ color: "var(--warning)" }}
              >
                VAPID public key is not configured on the API side, so this
                browser cannot create a new push subscription yet.
              </div>
            )}

            {backendStatus && (
              <>
                <div className="control-field-desc">
                  Backend status: <strong>{backendStatus.status}</strong>.{" "}
                  {backendStatus.next_action}
                </div>

                {!backendStatus.dispatch_backend_available && (
                  <div
                    className="control-field-desc"
                    style={{ color: "var(--warning)" }}
                  >
                    Server dispatch backend is missing. Install{" "}
                    <code>pywebpush</code> in the API environment before
                    expecting off-screen push delivery to work.
                  </div>
                )}

                {!backendStatus.subscription_registration_ready && (
                  <div
                    className="control-field-desc"
                    style={{ color: "var(--warning)" }}
                  >
                    Browser subscription creation is blocked until a VAPID
                    public key is configured on the API side.
                  </div>
                )}

                {!backendStatus.dispatch_ready && (
                  <div
                    className="control-field-desc"
                    style={{ color: "var(--warning)" }}
                  >
                    Off-screen push delivery is blocked until the server has
                    both a VAPID private key and VAPID subject configured.
                  </div>
                )}

                <div className="control-field-desc">
                  Public key source: {backendStatus.vapid_public_key_source || "unknown"}.
                  Subject: {backendStatus.vapid_subject.value || "unset"}.
                  Private key: {backendStatus.vapid_private_key.masked_value || "unset"}.
                </div>
              </>
            )}

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

            {testResults.length > 0 && (
              <div className="live-telemetry-table-wrap">
                <table className="live-telemetry-table">
                  <thead>
                    <tr>
                      <th>Endpoint</th>
                      <th>Success</th>
                      <th className="num">Status</th>
                      <th>Error</th>
                    </tr>
                  </thead>
                  <tbody>
                    {testResults.map((row, i) => (
                      <tr key={row.subscription_id || i}>
                        <td className="mono">
                          {row.endpoint_masked.length > 48
                            ? `${row.endpoint_masked.slice(0, 48)}…`
                            : row.endpoint_masked}
                        </td>
                        <td>
                          <StatusChip
                            label={row.success ? "yes" : "no"}
                            variant={row.success ? "success" : "danger"}
                            size="sm"
                          />
                        </td>
                        <td className="num mono">
                          {row.status_code ?? "—"}
                        </td>
                        <td>{row.error_message ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {serverSubscriptions.length > 0 && (
              <div className="live-telemetry-table-wrap">
                <table className="live-telemetry-table">
                  <thead>
                    <tr>
                      <th>Server-side subscriptions</th>
                      <th>Label</th>
                      <th>Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {serverSubscriptions.map((s) => (
                      <tr key={s.subscription_id}>
                        <td className="mono">
                          {s.endpoint_masked.length > 48
                            ? `${s.endpoint_masked.slice(0, 48)}…`
                            : s.endpoint_masked}
                        </td>
                        <td>{s.label || "—"}</td>
                        <td className="mono">{s.created_at_iso}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </GlassPanel>
  );
}
