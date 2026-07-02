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
  fetchPushSubscriptions,
  subscribeWebPush,
  testPushAll,
  unsubscribeWebPush,
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
  const [currentEndpoint, setCurrentEndpoint] = useState<string | null>(null);
  const [busy, setBusy] = useState<boolean>(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<PushTestResult[]>([]);

  const apiAvailable = isPushApiAvailable();

  const refreshServer = useCallback(async () => {
    const data = await fetchPushSubscriptions();
    if (data) {
      setServerSubscriptions(data.subscriptions);
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
        if (!VAPID_PUBLIC_KEY) {
          setError(
            "VAPID public key not configured (VITE_CAS_FOREX_VAPID_PUBLIC_KEY). Subscription cannot be created.",
          );
          return;
        }
        sub = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY),
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
  }, [apiAvailable, refreshServer]);

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

            {!VAPID_PUBLIC_KEY && (
              <div
                className="control-field-desc"
                style={{ color: "var(--warning)" }}
              >
                VAPID public key not configured. Set
                <code> VITE_CAS_FOREX_VAPID_PUBLIC_KEY </code>
                in the UI environment to allow new subscription creation.
              </div>
            )}

            <div
              className="control-field-desc"
              style={{ color: "var(--warning)" }}
            >
              Backend dispatch backend (pywebpush) not yet installed —
              subscriptions register but pushes will fail until installed.
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
                      <tr key={i}>
                        <td className="mono">
                          {row.endpoint.length > 48
                            ? `${row.endpoint.slice(0, 48)}…`
                            : row.endpoint}
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
                      <tr key={s.endpoint}>
                        <td className="mono">
                          {s.endpoint.length > 48
                            ? `${s.endpoint.slice(0, 48)}…`
                            : s.endpoint}
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
