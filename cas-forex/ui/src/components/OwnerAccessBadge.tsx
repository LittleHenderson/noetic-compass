/* ── CAS Forex — Owner Access ──
   Pair a phone, turn LAN mode on/off, rotate the token. On the owner's own PC
   (loopback) everything works with no token; this panel is how the owner ARMS
   network access and pairs another device. Live money is the point — this makes
   reaching the cockpit from a phone safe, it does not disable anything. */

import { useCallback, useEffect, useState } from "react";
import {
  fetchOwnerAuthState,
  fetchOwnerPairing,
  getOwnerToken,
  isLoopbackHost,
  rotateOwnerToken,
  setLanMode,
  setOwnerToken,
  type OwnerAuthState,
} from "../data/ownerAuthApi";

export function OwnerAccessBadge() {
  const [open, setOpen] = useState(false);
  const [state, setState] = useState<OwnerAuthState | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [tokenInput, setTokenInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const loopback = isLoopbackHost();
  const paired = Boolean(getOwnerToken());

  const refresh = useCallback(async () => {
    setState(await fetchOwnerAuthState());
  }, []);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(refresh, 30_000);
    return () => window.clearInterval(id);
  }, [refresh]);

  const revealToken = useCallback(async () => {
    setBusy(true);
    setMsg("");
    const pairing = await fetchOwnerPairing();
    setBusy(false);
    if (pairing?.owner_token) setToken(pairing.owner_token);
    else setMsg("Token is only visible on the PC running CAS Forex.");
  }, []);

  const toggleLan = useCallback(async () => {
    setBusy(true);
    setMsg("");
    try {
      await setLanMode(!(state?.lan_mode_enabled ?? false));
      await refresh();
    } catch {
      setMsg("Could not change LAN mode (do this on the PC).");
    } finally {
      setBusy(false);
    }
  }, [state, refresh]);

  const rotate = useCallback(async () => {
    setBusy(true);
    setMsg("");
    try {
      await rotateOwnerToken();
      setToken(null);
      await refresh();
      setMsg("Token rotated. Every paired device must pair again.");
    } catch {
      setMsg("Rotate must be done on the PC.");
    } finally {
      setBusy(false);
    }
  }, [refresh]);

  const savePhoneToken = useCallback(() => {
    setOwnerToken(tokenInput.trim() || null);
    setTokenInput("");
    setMsg(tokenInput.trim() ? "Token saved on this device." : "Token cleared.");
  }, [tokenInput]);

  const lanOn = state?.lan_mode_enabled ?? false;
  const dot = loopback ? "#39d98a" : paired ? "#39d98a" : "#e0574a";

  return (
    <div className="owner-access-badge" style={{ position: "relative" }}>
      <button
        className="shell-nav-link"
        onClick={() => setOpen((v) => !v)}
        title="Owner Access — pair a device, LAN mode"
        style={{ display: "inline-flex", alignItems: "center", gap: 6 }}
      >
        <span aria-hidden style={{ width: 8, height: 8, borderRadius: 8, background: dot, display: "inline-block" }} />
        🔒 Owner Access
      </button>

      {open ? (
        <div
          style={{
            position: "absolute",
            right: 0,
            top: "110%",
            zIndex: 60,
            width: 320,
            maxWidth: "90vw",
            background: "#12151c",
            border: "1px solid #2a2f3a",
            borderRadius: 10,
            padding: 14,
            boxShadow: "0 10px 30px rgba(0,0,0,.45)",
            fontSize: 13,
            lineHeight: 1.4,
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Owner Access</div>

          {loopback ? (
            <>
              <div style={{ opacity: 0.85, marginBottom: 10 }}>
                You're on this PC — always allowed, no token needed. Use this to let your
                phone in.
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <span>LAN access (phone): <strong>{lanOn ? "ON" : "OFF"}</strong></span>
                <button className="shell-nav-link" disabled={busy} onClick={toggleLan}>
                  {lanOn ? "Turn OFF" : "Turn ON"}
                </button>
              </div>

              <div style={{ marginBottom: 8 }}>
                {token ? (
                  <div>
                    <div style={{ opacity: 0.8, marginBottom: 4 }}>Pairing token (type this on the phone):</div>
                    <code
                      style={{
                        display: "block",
                        wordBreak: "break-all",
                        background: "#0b0d12",
                        border: "1px solid #2a2f3a",
                        borderRadius: 6,
                        padding: 8,
                      }}
                    >
                      {token}
                    </code>
                    <button
                      className="shell-nav-link"
                      style={{ marginTop: 6 }}
                      onClick={() => { void navigator.clipboard?.writeText(token); setMsg("Copied."); }}
                    >
                      Copy
                    </button>
                  </div>
                ) : (
                  <button className="shell-nav-link" disabled={busy} onClick={revealToken}>
                    Show pairing token
                  </button>
                )}
              </div>

              <button className="shell-nav-link" disabled={busy} onClick={rotate} style={{ color: "#e0574a" }}>
                Rotate token (unpairs all devices)
              </button>
            </>
          ) : (
            <>
              <div style={{ opacity: 0.85, marginBottom: 10 }}>
                Reaching from another device. Paste the token shown in the cockpit on the
                PC (Owner Access → Show pairing token), and make sure LAN mode is ON there.
              </div>
              <div style={{ marginBottom: 8 }}>
                Status: <strong>{paired ? "paired on this device" : "not paired"}</strong>
                {state?.token_hint ? ` · server token ${state.token_hint}` : ""}
              </div>
              <input
                type="password"
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                placeholder="Paste owner token"
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  background: "#0b0d12",
                  border: "1px solid #2a2f3a",
                  borderRadius: 6,
                  padding: 8,
                  color: "inherit",
                  marginBottom: 6,
                }}
              />
              <div style={{ display: "flex", gap: 8 }}>
                <button className="shell-nav-link" onClick={savePhoneToken}>Save</button>
                {paired ? (
                  <button className="shell-nav-link" onClick={() => { setOwnerToken(null); setMsg("Token cleared."); }}>
                    Forget
                  </button>
                ) : null}
              </div>
            </>
          )}

          {msg ? <div style={{ marginTop: 10, opacity: 0.85 }}>{msg}</div> : null}
        </div>
      ) : null}
    </div>
  );
}
