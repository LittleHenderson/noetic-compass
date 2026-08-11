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
  const [pairingUrls, setPairingUrls] = useState<string[]>([]);
  const [nativePairingUrls, setNativePairingUrls] = useState<string[]>([]);
  const [pairingApiBases, setPairingApiBases] = useState<string[]>([]);
  const [directApiBases, setDirectApiBases] = useState<string[]>([]);
  const [tokenInput, setTokenInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [manualCopyValue, setManualCopyValue] = useState<string | null>(null);
  const loopback = isLoopbackHost();
  const paired = Boolean(getOwnerToken());
  const apkInstallPairCommand = "npm --prefix ui run mobile:apk:wait-install-pair";

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
    if (pairing?.owner_token) {
      setToken(pairing.owner_token);
      setPairingUrls(pairing.pairing_urls ?? []);
      setNativePairingUrls(pairing.native_pairing_urls ?? []);
      setPairingApiBases(pairing.pairing_api_bases ?? []);
      setDirectApiBases(pairing.direct_api_bases ?? []);
    }
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
      setPairingUrls([]);
      setNativePairingUrls([]);
      setPairingApiBases([]);
      setDirectApiBases([]);
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
    setManualCopyValue(null);
    setMsg(tokenInput.trim() ? "Token saved on this device." : "Token cleared.");
  }, [tokenInput]);

  const copyValue = useCallback(async (label: string, value: string) => {
    try {
      await writeClipboardText(value);
      setManualCopyValue(null);
      setMsg(`${label} copied.`);
    } catch {
      setManualCopyValue(value);
      setMsg("Copy unavailable; use the text below.");
    }
  }, []);

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
            position: "fixed",
            right: 12,
            top: "calc(env(safe-area-inset-top, 0px) + 88px)",
            zIndex: 60,
            width: "min(320px, calc(100vw - 24px))",
            maxHeight: "calc(100vh - env(safe-area-inset-top, 0px) - 104px)",
            overflowY: "auto",
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
                      onClick={() => { void copyValue("Token", token); }}
                    >
                      Copy
                    </button>
                    {pairingUrls.length > 0 ? (
                      <div style={{ marginTop: 8 }}>
                        <div style={{ opacity: 0.8, marginBottom: 4 }}>
                          Phone pairing link (token and API base stay in the URL fragment):
                        </div>
                        <PairingQrCode
                          label="Scan to pair phone PWA"
                          url={pairingUrls[0]}
                        />
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
                          {pairingUrls[0]}
                        </code>
                        <button
                          className="shell-nav-link"
                          style={{ marginTop: 6 }}
                          onClick={() => { void copyValue("Pairing link", pairingUrls[0]); }}
                        >
                          Copy pairing link
                        </button>
                      </div>
                    ) : null}
                    {pairingApiBases.length > 0 ? (
                      <div style={{ marginTop: 8 }}>
                        <div style={{ opacity: 0.8, marginBottom: 4 }}>
                          Phone PWA API base:
                        </div>
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
                          {pairingApiBases[0]}
                        </code>
                        <button
                          className="shell-nav-link"
                          style={{ marginTop: 6 }}
                          onClick={() => { void copyValue("Phone API base", pairingApiBases[0]); }}
                        >
                          Copy API base
                        </button>
                      </div>
                    ) : null}
                    {directApiBases.length > 0 ? (
                      <div style={{ marginTop: 8 }}>
                        <div style={{ opacity: 0.8, marginBottom: 4 }}>
                          APK/dev-server direct API base:
                        </div>
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
                          {directApiBases[0]}
                        </code>
                        <button
                          className="shell-nav-link"
                          style={{ marginTop: 6 }}
                          onClick={() => { void copyValue("APK API base", directApiBases[0]); }}
                        >
                          Copy APK API base
                        </button>
                      </div>
                    ) : null}
                    {nativePairingUrls.length > 0 ? (
                      <div style={{ marginTop: 8 }}>
                        <div style={{ opacity: 0.8, marginBottom: 4 }}>
                          Android app pairing link:
                        </div>
                        <PairingQrCode
                          label="Scan after APK install"
                          url={nativePairingUrls[0]}
                        />
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
                          {nativePairingUrls[0]}
                        </code>
                        <button
                          className="shell-nav-link"
                          style={{ marginTop: 6 }}
                          onClick={() => { void copyValue("Android app pairing link", nativePairingUrls[0]); }}
                        >
                          Copy Android app link
                        </button>
                      </div>
                    ) : null}
                    <div style={{ marginTop: 8 }}>
                      <div style={{ opacity: 0.8, marginBottom: 4 }}>
                        Android wait/install-pair command:
                      </div>
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
                        {apkInstallPairCommand}
                      </code>
                      <button
                        className="shell-nav-link"
                        style={{ marginTop: 6 }}
                        onClick={() => { void copyValue("APK install-pair command", apkInstallPairCommand); }}
                      >
                        Copy install-pair
                      </button>
                    </div>
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
                  <button className="shell-nav-link" onClick={() => { setOwnerToken(null); setManualCopyValue(null); setMsg("Token cleared."); }}>
                    Forget
                  </button>
                ) : null}
              </div>
            </>
          )}

          {msg ? <div style={{ marginTop: 10, opacity: 0.85 }}>{msg}</div> : null}
          {manualCopyValue ? (
            <code
              style={{
                display: "block",
                marginTop: 8,
                wordBreak: "break-all",
                background: "#0b0d12",
                border: "1px solid #3b3540",
                borderRadius: 6,
                padding: 8,
              }}
            >
              {manualCopyValue}
            </code>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

async function writeClipboardText(value: string): Promise<void> {
  try {
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(value);
      return;
    }
  } catch {
    // Fall through to the textarea path for HTTP/LAN browsers.
  }
  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "true");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  textarea.style.top = "0";
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  const copied = document.execCommand("copy");
  document.body.removeChild(textarea);
  if (!copied) throw new Error("clipboard unavailable");
}

function PairingQrCode({ label, url }: { label: string; url: string }) {
  const [dataUrl, setDataUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setDataUrl(null);
    setFailed(false);
    void (async () => {
      try {
        const { default: QRCode } = await import("qrcode");
        const next = await QRCode.toDataURL(url, {
          errorCorrectionLevel: "M",
          margin: 1,
          width: 188,
          color: {
            dark: "#020617",
            light: "#f8fafc",
          },
        });
        if (!cancelled) setDataUrl(next);
      } catch {
        if (!cancelled) setFailed(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [url]);

  if (failed) {
    return (
      <div style={{ opacity: 0.75, marginBottom: 6 }}>
        QR unavailable; copy the link below.
      </div>
    );
  }

  return (
    <div
      style={{
        display: "grid",
        justifyItems: "center",
        gap: 6,
        marginBottom: 8,
        padding: 10,
        background: "#f8fafc",
        borderRadius: 8,
      }}
    >
      {dataUrl ? (
        <img
          alt={label}
          src={dataUrl}
          width={188}
          height={188}
          style={{ display: "block", width: 188, height: 188 }}
        />
      ) : (
        <div style={{ width: 188, height: 188, display: "grid", placeItems: "center", color: "#020617" }}>
          Generating QR...
        </div>
      )}
      <div style={{ color: "#020617", fontSize: 12, fontWeight: 700 }}>
        {label}
      </div>
    </div>
  );
}
