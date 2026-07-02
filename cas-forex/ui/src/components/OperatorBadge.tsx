/* ── CAS Forex — AI Operator badge ──
   Always-visible header indicator for the AI strategy desk: which model is
   driving (Claude vs free local fallback), whether the operator loop is on, the
   token budget, and every model switch. Click to expand controls (start/stop,
   run now, top up Claude tokens) and see recent operator actions. */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  fetchOperatorState,
  startOperator,
  stopOperator,
  runOperatorNow,
  addOperatorTokens,
  setOperatorKey,
  chatWithOperator,
  fetchGuidance,
  addGuidance,
  removeGuidance,
  type GuidanceNote,
  type OperatorState,
} from "../data/operatorApi";
import "./OperatorBadge.css";

const POLL_MS = 10_000;
const DEFAULT_INTERVAL_SECONDS = 1800;

type Driver = "claude" | "local" | "off" | "stalled" | "warming" | "unknown";

function classifyDriver(state: OperatorState | null): { driver: Driver; label: string; note: string } {
  if (!state) return { driver: "unknown", label: "OPERATOR ?", note: "API unreachable" };
  if (!state.running) return { driver: "off", label: "OPERATOR OFF", note: "strategy desk paused" };

  // Prefer the ACTUAL last-tick outcome over "which provider would be tried" —
  // a configured Claude that fails every call must NOT read as a healthy CLAUDE.
  const lastOk = state.last_ok;
  const lastProvider = state.last_provider ?? null;
  if (lastOk === false) {
    return { driver: "stalled", label: "NO MODEL", note: "no AI model reachable — set a Claude key or install the local model" };
  }
  if (lastOk === true && lastProvider) {
    const paid = lastProvider === "claude";
    return paid
      ? { driver: "claude", label: "CLAUDE", note: "paid primary is answering" }
      : { driver: "local", label: "LOCAL (free)", note: "free fallback is answering" };
  }
  // Running but no tick has completed yet.
  return { driver: "warming", label: "OPERATOR ON", note: "starting — first check pending" };
}

export function OperatorBadge() {
  const [state, setState] = useState<OperatorState | null>(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [topUp, setTopUp] = useState("500000");
  const [keyInput, setKeyInput] = useState("");
  const [keyMsg, setKeyMsg] = useState("");
  const [chatInput, setChatInput] = useState("");
  const [chatReply, setChatReply] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const [guidance, setGuidance] = useState<GuidanceNote[]>([]);
  const timer = useRef<number | null>(null);

  const refresh = useCallback(async () => {
    const next = await fetchOperatorState();
    setState(next);
  }, []);

  useEffect(() => {
    refresh();
    timer.current = window.setInterval(refresh, POLL_MS);
    return () => {
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [refresh]);

  useEffect(() => {
    if (open) fetchGuidance().then(setGuidance);
  }, [open]);

  const ask = useCallback(async () => {
    const q = chatInput.trim();
    if (!q) return;
    setChatBusy(true);
    setChatReply("…thinking…");
    try {
      const res = await chatWithOperator(q);
      setChatReply(res.ok ? res.reply || "(no reply)" : `Unavailable: ${res.error ?? "no model reachable"}`);
    } catch {
      setChatReply("Unavailable: request failed.");
    } finally {
      setChatBusy(false);
    }
  }, [chatInput]);

  const saveGuidance = useCallback(async () => {
    const q = chatInput.trim();
    if (!q) return;
    setChatBusy(true);
    try {
      setGuidance(await addGuidance(q));
      setChatInput("");
      setChatReply("Saved as standing guidance — the operator weighs it on every check from now on.");
    } catch {
      setChatReply("Could not save guidance.");
    } finally {
      setChatBusy(false);
    }
  }, [chatInput]);

  const { driver, label, note } = classifyDriver(state);
  const mp = state?.model_provider;
  const running = Boolean(state?.running);

  const act = useCallback(
    async (fn: () => Promise<unknown>) => {
      setBusy(true);
      try {
        await fn();
        await refresh();
      } catch {
        /* leave the badge showing last-known state; poll will recover */
      } finally {
        setBusy(false);
      }
    },
    [refresh],
  );

  return (
    <div className={`operator-badge operator-badge--${driver}`}>
      <button
        className="operator-badge-chip"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        title="AI operator / model status — click for controls"
      >
        <span className="operator-badge-dot" />
        <span className="operator-badge-label">{label}</span>
        {mp?.budget_capped && driver === "claude" ? (
          <span className="operator-badge-budget">{formatTokens(mp?.budget_remaining ?? 0)} left</span>
        ) : null}
      </button>

      {open ? (
        <div className="operator-badge-panel">
          <div className="operator-badge-row operator-badge-title">
            <span>AI Operator (strategy desk)</span>
            <span className={`operator-badge-state operator-badge-state--${running ? "on" : "off"}`}>
              {running ? "RUNNING" : "OFF"}
            </span>
          </div>

          <div className="operator-badge-line">
            Driving now: <strong>{label}</strong> <span className="operator-badge-muted">— {note}</span>
          </div>

          {mp?.primary_configured ? (
            <div className="operator-badge-line operator-badge-muted">
              Claude budget: {formatTokens(mp?.spent_tokens ?? 0)} used
              {mp?.budget_capped ? ` of ${formatTokens(mp?.budget_tokens ?? 0)}` : " (no cap)"}
              {mp?.primary_in_cooldown
                ? ` · primary cooling down ${mp?.primary_cooldown_seconds_left ?? 0}s`
                : ""}
            </div>
          ) : (
            <div className="operator-badge-line operator-badge-muted">
              No Claude key set — running on the free local model. Set a key to use Claude as primary.
            </div>
          )}

          {mp?.last_switch?.to ? (
            <div className="operator-badge-line operator-badge-switch">
              ↻ switched to <strong>{mp.last_switch.to}</strong>
              {mp.last_switch.reason ? ` — ${mp.last_switch.reason}` : ""}
            </div>
          ) : null}

          {state?.last_summary ? (
            <div className="operator-badge-line operator-badge-summary">“{state.last_summary}”</div>
          ) : null}

          <div className="operator-badge-controls">
            {running ? (
              <button disabled={busy} onClick={() => act(stopOperator)}>
                Pause operator
              </button>
            ) : (
              <button disabled={busy} onClick={() => act(() => startOperator(DEFAULT_INTERVAL_SECONDS))}>
                Start operator
              </button>
            )}
            <button disabled={busy} onClick={() => act(runOperatorNow)}>
              Run once now
            </button>
          </div>

          <div className="operator-badge-keyrow">
            <div className="operator-badge-keylabel">
              Claude API key{" "}
              {mp?.primary_key_present ? (
                <span className="operator-badge-keyok">set {mp?.primary_key_hint ?? ""} ✓</span>
              ) : (
                <span className="operator-badge-keymissing">not set</span>
              )}
            </div>
            <div className="operator-badge-keyinput">
              <input
                type="password"
                placeholder="paste sk-ant-api03-…"
                value={keyInput}
                autoComplete="off"
                onChange={(e) => setKeyInput(e.target.value)}
                aria-label="Claude API key"
              />
              <button
                disabled={busy || !keyInput.trim()}
                onClick={() =>
                  act(async () => {
                    await setOperatorKey(keyInput.trim());
                    setKeyInput("");
                    setKeyMsg("Key saved locally — Claude will be tried on the next check.");
                  })
                }
              >
                Save key
              </button>
            </div>
            {keyMsg ? <div className="operator-badge-muted operator-badge-keymsg">{keyMsg}</div> : null}
          </div>

          <div className="operator-badge-topup">
            <input
              type="number"
              min={0}
              step={10000}
              value={topUp}
              onChange={(e) => setTopUp(e.target.value)}
              aria-label="Claude tokens to add"
            />
            <button
              disabled={busy}
              onClick={() => act(() => addOperatorTokens(Math.max(0, Number(topUp) || 0)))}
            >
              Add Claude tokens
            </button>
          </div>

          <div className="operator-badge-chat">
            <div className="operator-badge-actions-title">Talk to the operator</div>
            <textarea
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Ask a question, or write a consideration (e.g. bank big winners early, then restart the cycle)…"
              rows={2}
              aria-label="Message to the AI operator"
            />
            <div className="operator-badge-chat-buttons">
              <button disabled={chatBusy || !chatInput.trim()} onClick={ask}>
                Ask
              </button>
              <button disabled={chatBusy || !chatInput.trim()} onClick={saveGuidance}>
                Save as standing guidance
              </button>
            </div>
            {chatReply ? <div className="operator-badge-chat-reply">{chatReply}</div> : null}
            {guidance.length > 0 ? (
              <div className="operator-badge-guidance">
                <div className="operator-badge-actions-title">Standing guidance (weighed every check)</div>
                {guidance.slice(0, 6).map((note) => (
                  <div className="operator-badge-guidance-note" key={note.note_id}>
                    <span>{note.text.length > 90 ? note.text.slice(0, 90) + "…" : note.text}</span>
                    <button
                      aria-label="Remove guidance"
                      title="Remove"
                      onClick={() => removeGuidance(note.note_id).then(setGuidance)}
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
            ) : null}
          </div>

          {state?.recent_actions && state.recent_actions.length > 0 ? (
            <div className="operator-badge-actions">
              <div className="operator-badge-actions-title">Recent operator actions</div>
              {state.recent_actions.slice(0, 5).map((a, i) => (
                <div className="operator-badge-action" key={i}>
                  <span className="operator-badge-muted">{String((a as Record<string, unknown>).provider ?? "")}</span>{" "}
                  {String((a as Record<string, unknown>).summary ?? (a as Record<string, unknown>).error ?? "—")}
                </div>
              ))}
            </div>
          ) : null}

          <div className="operator-badge-boundary">
            Adjusts only owner-fenced AI dials. Never trades, moves money, or authorizes live trading.
          </div>
        </div>
      ) : null}
    </div>
  );
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${Math.round(n / 1_000)}k`;
  return String(n);
}
