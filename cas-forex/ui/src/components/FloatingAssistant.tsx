/* ── CAS Forex — Floating AI Assistant ──
 * A persistent chat bubble that follows the owner on every page. Tap to open a
 * chat panel that talks to the AI via POST /api/forex/assistant/chat.
 * Self-contained (inline styles) so it floats above all pages on phone + desktop.
 */

import { useEffect, useRef, useState } from "react";
import { postAssistantChat, type AssistantTurn } from "../data/api";

interface Msg {
  role: "user" | "assistant";
  content: string;
  pending?: boolean;
}

const GREETING: Msg = {
  role: "assistant",
  content:
    "Hey — I'm your CAS Forex assistant. Ask me anything about the cockpit: " +
    "how to go live, link a broker/card, set up scalping timeframes, change risk " +
    "caps, or what any screen does.",
};

// Keyframes for the "thinking" cues (injected once; inline styles can't do @keyframes).
const KEYFRAMES = `
@keyframes casTyping { 0%,80%,100% { opacity:.25; transform:translateY(0) } 40% { opacity:1; transform:translateY(-3px) } }
@keyframes casPulse { 0%,100% { box-shadow:0 0 0 0 rgba(34,197,94,.55) } 70% { box-shadow:0 0 0 6px rgba(34,197,94,0) } }
.cas-typing-dot { width:6px; height:6px; border-radius:3px; background:#9aa4b2; display:inline-block; animation:casTyping 1s infinite }
.cas-pulse { animation:casPulse 1.2s infinite }
`;

function TypingDots() {
  return (
    <span style={{ display: "inline-flex", gap: 4, alignItems: "center", padding: "3px 0" }} aria-label="Assistant is thinking">
      <span className="cas-typing-dot" style={{ animationDelay: "0s" }} />
      <span className="cas-typing-dot" style={{ animationDelay: "0.15s" }} />
      <span className="cas-typing-dot" style={{ animationDelay: "0.3s" }} />
    </span>
  );
}

export function FloatingAssistant() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([GREETING]);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    if (open) scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [msgs, open, busy]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    const history: AssistantTurn[] = msgs
      .filter((m) => !m.pending)
      .map((m) => ({ role: m.role, content: m.content }));
    setMsgs((prev) => [...prev, { role: "user", content: text }, { role: "assistant", content: "…", pending: true }]);
    setInput("");
    setBusy(true);
    try {
      const res = await postAssistantChat(text, history);
      setMsgs((prev) => {
        const next = prev.slice(0, -1); // drop the pending placeholder
        return [...next, { role: "assistant", content: res.reply }];
      });
    } catch {
      setMsgs((prev) => {
        const next = prev.slice(0, -1);
        return [
          ...next,
          {
            role: "assistant",
            content:
              "Couldn't reach the assistant — is the API server running and is the " +
              "API address set correctly in Settings?",
          },
        ];
      });
    } finally {
      setBusy(false);
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send();
    }
  }

  return (
    <>
      <style>{KEYFRAMES}</style>
      {/* Floating button — always visible, bottom-right, above everything.
          Pulses while a reply is in flight even if collapsed. */}
      {!open && (
        <button
          aria-label="Open assistant"
          onClick={() => setOpen(true)}
          style={S.fab}
          className={busy ? "cas-pulse" : undefined}
        >
          <span style={S.fabIcon}>{busy ? "…" : "💬"}</span>
        </button>
      )}

      {open && (
        <div style={S.panel} role="dialog" aria-label="CAS Forex assistant">
          <div style={S.header}>
            <span style={S.headerTitle}>
              <span style={S.dot} className={busy ? "cas-pulse" : undefined} />{" "}
              {busy ? "Thinking…" : "CAS Forex Assistant"}
            </span>
            <button aria-label="Close assistant" onClick={() => setOpen(false)} style={S.iconBtn}>
              ✕
            </button>
          </div>

          <div ref={scrollRef} style={S.scroll}>
            {msgs.map((m, i) => (
              <div key={i} style={{ ...S.row, justifyContent: m.role === "user" ? "flex-end" : "flex-start" }}>
                <div style={{ ...S.bubble, ...(m.role === "user" ? S.bubbleUser : S.bubbleAi) }}>
                  {m.pending ? <TypingDots /> : m.content}
                </div>
              </div>
            ))}
          </div>

          <div style={S.inputRow}>
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Ask the assistant…"
              rows={1}
              style={S.textarea}
            />
            <button onClick={() => void send()} disabled={busy || !input.trim()} style={S.send}>
              {busy ? "…" : "Send"}
            </button>
          </div>
        </div>
      )}
    </>
  );
}

const ACCENT = "#3b82f6";
const S: Record<string, React.CSSProperties> = {
  fab: {
    position: "fixed",
    right: "max(16px, env(safe-area-inset-right))",
    bottom: "max(16px, env(safe-area-inset-bottom))",
    width: 56,
    height: 56,
    borderRadius: 28,
    border: "none",
    background: ACCENT,
    color: "#fff",
    boxShadow: "0 6px 20px rgba(0,0,0,0.35)",
    cursor: "pointer",
    zIndex: 2147483000,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  fabIcon: { fontSize: 24, lineHeight: 1 },
  panel: {
    position: "fixed",
    right: "max(12px, env(safe-area-inset-right))",
    bottom: "max(12px, env(safe-area-inset-bottom))",
    width: "min(380px, calc(100vw - 24px))",
    height: "min(560px, calc(100vh - 24px))",
    background: "#0f1729",
    color: "#e5e7eb",
    border: "1px solid #1f2a44",
    borderRadius: 16,
    boxShadow: "0 16px 48px rgba(0,0,0,0.5)",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
    zIndex: 2147483000,
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "12px 14px",
    background: "#111c33",
    borderBottom: "1px solid #1f2a44",
  },
  headerTitle: { display: "flex", alignItems: "center", gap: 8, fontWeight: 600, fontSize: 14 },
  dot: { width: 8, height: 8, borderRadius: 4, background: "#22c55e", display: "inline-block" },
  iconBtn: { background: "transparent", border: "none", color: "#9aa4b2", fontSize: 16, cursor: "pointer" },
  scroll: { flex: 1, overflowY: "auto", padding: 12, display: "flex", flexDirection: "column", gap: 8 },
  row: { display: "flex" },
  bubble: { maxWidth: "85%", padding: "9px 12px", borderRadius: 12, fontSize: 14, lineHeight: 1.45, whiteSpace: "pre-wrap", wordBreak: "break-word" },
  bubbleUser: { background: ACCENT, color: "#fff", borderBottomRightRadius: 4 },
  bubbleAi: { background: "#1b2740", color: "#e5e7eb", borderBottomLeftRadius: 4 },
  pending: { opacity: 0.6 },
  inputRow: { display: "flex", gap: 8, padding: 10, borderTop: "1px solid #1f2a44", background: "#0c1424" },
  textarea: {
    flex: 1,
    resize: "none",
    maxHeight: 96,
    background: "#0f1729",
    color: "#e5e7eb",
    border: "1px solid #243049",
    borderRadius: 10,
    padding: "10px 12px",
    fontSize: 14,
    fontFamily: "inherit",
    outline: "none",
  },
  send: {
    background: ACCENT,
    color: "#fff",
    border: "none",
    borderRadius: 10,
    padding: "0 16px",
    fontWeight: 600,
    fontSize: 14,
    cursor: "pointer",
  },
};
