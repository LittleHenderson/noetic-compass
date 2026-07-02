/* ── CAS Forex — MT4 Bridge Panel ──
   Enable the stable file-based MT4 EA mailbox route, point it at the terminal's
   mailbox folder, and see the EA heartbeat — all in-app. */

import { useEffect, useState } from "react";
import { GlassPanel } from "./GlassPanel";
import { StatusChip } from "./StatusChip";
import {
  fetchMt4Control,
  updateMt4Control,
  resetMt4Control,
  setDispatchPlatform,
  type MT4ControlState,
} from "../data/api";

const LINK_VARIANT: Record<string, "success" | "warning" | "danger"> = {
  LIVE: "success",
  STALE: "warning",
  NO_HEARTBEAT: "danger",
};

const LINK_LABEL: Record<string, string> = {
  LIVE: "EA LINK LIVE",
  STALE: "EA HEARTBEAT STALE",
  NO_HEARTBEAT: "NO EA HEARTBEAT",
};

export function Mt4BridgePanel() {
  const [mc, setMc] = useState<MT4ControlState | null>(null);
  const [dir, setDir] = useState<string>("");
  const [busy, setBusy] = useState<string>("");
  const [status, setStatus] = useState<string>("");

  function apply(s: MT4ControlState) {
    setMc(s);
    setDir(s.mailbox_dir);
  }

  useEffect(() => {
    void fetchMt4Control().then((s) => {
      if (s) apply(s);
    });
    const id = setInterval(() => {
      void fetchMt4Control().then((s) => {
        if (s) setMc(s); // refresh heartbeat without clobbering the dir draft
      });
    }, 10_000);
    return () => clearInterval(id);
  }, []);

  async function save() {
    setBusy("save");
    try {
      const s = await updateMt4Control({ mailbox_dir: dir.trim() || undefined });
      apply(s);
      setStatus(s.error ? `Couldn't save: ${s.error}` : "Saved the mailbox folder.");
    } catch {
      setStatus("Couldn't save — is the API reachable? Check the address above.");
    } finally {
      setBusy("");
    }
  }

  async function toggleEnabled() {
    if (!mc) return;
    setBusy("enable");
    try {
      const s = await updateMt4Control({ enabled: !mc.enabled, mailbox_dir: dir.trim() || undefined });
      apply(s);
      setStatus(
        s.enabled
          ? s.link_status === "LIVE"
            ? "MT4 route ON and EA heartbeat live."
            : "MT4 route ON, waiting for the EA heartbeat before demo fills can run."
          : "MT4 route OFF."
      );
    } catch {
      setStatus("Couldn't change the MT4 route.");
    } finally {
      setBusy("");
    }
  }

  async function reset() {
    setBusy("reset");
    try {
      apply(await resetMt4Control());
      setStatus("Reset to defaults.");
    } catch {
      setStatus("Couldn't reset.");
    } finally {
      setBusy("");
    }
  }

  async function useForDispatch() {
    setBusy("platform");
    try {
      await setDispatchPlatform("mt4");
      setStatus(
        mc?.link_status === "LIVE"
          ? "MT4 is selected for dispatch and the EA heartbeat is live."
          : "MT4 is selected for dispatch, but no demo fills can run until the EA heartbeat is live."
      );
    } catch {
      setStatus("Couldn't switch the dispatch platform.");
    } finally {
      setBusy("");
    }
  }

  if (!mc) {
    return (
      <GlassPanel title="MT4 Bridge — Stable File Route" subtitle="The reliable real-order path (not the flaky MT5 link)">
        <div className="control-field-desc">Loading MT4 route status…</div>
      </GlassPanel>
    );
  }

  const hb = mc.heartbeat;
  const age = hb.age_seconds == null ? "—" : `${hb.age_seconds}s ago`;

  return (
    <GlassPanel title="MT4 Bridge — Stable File Route" subtitle="The reliable real-order path (not the flaky MT5 link)">
      <div style={{ display: "grid", gap: 14 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <StatusChip label={mc.enabled ? "ROUTE ON" : "ROUTE OFF"} variant={mc.enabled ? "success" : "paper"} size="sm" />
          <StatusChip label={LINK_LABEL[mc.link_status] ?? mc.link_status} variant={LINK_VARIANT[mc.link_status] ?? "warning"} size="sm" />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <button
            type="button"
            className="go-live-switch"
            data-on={mc.enabled}
            disabled={busy === "enable"}
            aria-pressed={mc.enabled}
            aria-label={`MT4 route — ${mc.enabled ? "on" : "off"}`}
            onClick={() => void toggleEnabled()}
          >
            <span className="knob" />
          </button>
          <span className="control-field-desc">Turn the MT4 mailbox route {mc.enabled ? "OFF" : "ON"}</span>
        </div>

        <div className="control-field">
          <span className="field-label">Mailbox folder (MT4 MQL4\Files\CASForexMailbox)</span>
          <input
            className="mobile-api-input"
            type="text"
            value={dir}
            placeholder="C:\\Users\\you\\AppData\\Roaming\\MetaQuotes\\Terminal\\<id>\\MQL4\\Files\\CASForexMailbox"
            onChange={(e) => { setDir(e.target.value); setStatus(""); }}
          />
          <div className="control-field-desc">
            Point this at the same folder the EA's MailboxRoot uses, so commands and receipts meet.
          </div>
        </div>

        <div className="control-field">
          <span className="field-label">EA heartbeat</span>
          <div className="control-field-desc">
            {hb.present
              ? `Last seen ${age} · state ${hb.state ?? "—"} · server ${hb.server ?? "—"}${hb.live_trading_allowed != null ? ` · live-allowed ${hb.live_trading_allowed}` : ""}`
              : "No heartbeat.json yet — attach CASForexBridgeEA in MT4 and point MailboxRoot at the folder above."}
          </div>
        </div>

        <div className="mobile-api-row">
          <button className="mobile-api-button" type="button" disabled={busy === "save"} onClick={() => void save()}>
            Save folder
          </button>
          <button className="mobile-api-button" type="button" disabled={busy === "platform"} onClick={() => void useForDispatch()}>
            Use MT4 for dispatch
          </button>
          <button className="mobile-api-button ghost" type="button" disabled={busy === "reset"} onClick={() => void reset()}>
            Reset
          </button>
        </div>

        {status && (
          <div
            className="control-field-desc"
            style={{ color: status.toLowerCase().includes("heartbeat") && mc.link_status !== "LIVE" ? "var(--warning)" : "var(--success)" }}
          >
            {status}
          </div>
        )}
        <div className="control-field-desc">
          MT4 demo trading needs a fresh EA heartbeat plus receipts from this mailbox. Route ON only selects the path; it
          is not an active MT4 demo fill by itself. Live MT4 additionally needs the EA's own LiveTradingAllowed input.
        </div>
      </div>
    </GlassPanel>
  );
}
