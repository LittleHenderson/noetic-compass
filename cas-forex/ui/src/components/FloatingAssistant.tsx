/* ── CAS Forex — Floating AI Assistant ──
 * A persistent chat bubble that follows the owner on every page. Tap to open a
 * chat panel that talks to the AI via POST /api/forex/assistant/chat.
 * Self-contained (inline styles) so it floats above all pages on phone + desktop.
 */

import { useEffect, useRef, useState } from "react";
import {
  postAssistantChat,
  type AssistantReply,
  type AssistantTurn,
} from "../data/assistantApi";
import {
  executeCommand,
  type CommandPreview,
  type ProposedCommand,
} from "../data/ownerCommandApi";

interface Msg {
  role: "user" | "assistant";
  content: string;
  pending?: boolean;
  responder?: string;
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
  const [proposed, setProposed] = useState<ProposedCommand | null>(null);
  const [preview, setPreview] = useState<CommandPreview | null>(null);
  const [confirmInput, setConfirmInput] = useState("");
  const [journalInput, setJournalInput] = useState("");
  const [receiptMsg, setReceiptMsg] = useState("");
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
    setProposed(null);
    setPreview(null);
    setConfirmInput("");
    setJournalInput("");
    setReceiptMsg("");
    setMsgs((prev) => [...prev, { role: "user", content: text }, { role: "assistant", content: "…", pending: true }]);
    setInput("");
    setBusy(true);
    try {
      const res = await postAssistantChat(text, history);
      setMsgs((prev) => {
        const next = prev.slice(0, -1); // drop the pending placeholder
        return [
          ...next,
          {
            role: "assistant",
            content: res.reply,
            responder: assistantResponderLabel(res),
          },
        ];
      });
      if (res.proposed_command && res.command_preview) {
        setProposed(res.proposed_command);
        setPreview(res.command_preview);
        setConfirmInput(res.command_preview.confirm_phrase || "CONFIRM");
        setJournalInput(extractPreviewReason(res.proposed_command.params));
      }
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
            responder: "Request failed",
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

  async function runProposed() {
    if (!proposed) return;
    setBusy(true);
    setReceiptMsg("");
    try {
      const res = await executeCommand(
        proposed.command,
        {
          ...proposed.params,
          ...(journalInput.trim() ? { journal_reason: journalInput.trim() } : {}),
        },
        confirmInput.trim(),
      );
      if (res.ok && res.applied) {
        setReceiptMsg(`Done: ${JSON.stringify(res.result || {})}`);
        setProposed(null);
        setPreview(null);
        setConfirmInput("");
        setJournalInput("");
      } else if (res.need_confirmation) {
        setReceiptMsg(`Type exactly: "${res.need_confirmation}"`);
      } else {
        const blockers = res.preview?.blockers?.length ? ` - ${res.preview.blockers.join("; ")}` : "";
        setReceiptMsg(`Not applied: ${res.reason ?? "blocked"}${blockers}`);
      }
    } catch {
      setReceiptMsg("Command failed to run.");
    } finally {
      setBusy(false);
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
                <div style={{ ...S.messageStack, alignItems: m.role === "user" ? "flex-end" : "flex-start" }}>
                  <div style={{ ...S.bubble, ...(m.role === "user" ? S.bubbleUser : S.bubbleAi) }}>
                    {m.pending ? <TypingDots /> : m.content}
                  </div>
                  {m.role === "assistant" && m.responder ? (
                    <div style={S.responder}>Answered by: {m.responder}</div>
                  ) : null}
                </div>
              </div>
            ))}
            {preview ? (
              <div style={S.commandCard}>
                <div style={S.commandTitle}>Proposed: {preview.title}</div>
                <div style={S.commandSmall}>
                  {String(JSON.stringify(preview.current))} → <strong>{String(JSON.stringify(preview.proposed))}</strong>
                </div>
                {preview.binding?.operational_effect ? (
                  <div style={S.commandSmall}>{preview.binding.operational_effect}</div>
                ) : null}
                {(preview.contract_rows || []).map((row, i) => (
                  <div key={`${row.field || "contract"}-${i}`} style={S.commandContract}>
                    <div style={S.commandSmall}>
                      <strong>{row.label || row.field || "Dial"}</strong>: {formatContractValue(row.before, row.value_kind)}
                      {" "}to <strong>{formatContractValue(row.after, row.value_kind)}</strong>
                      {row.units ? ` ${row.units}` : ""}
                    </div>
                    {row.value_kind === "subset" ? (
                      <>
                        {row.added?.length ? <div style={S.commandSmall}>Added: {row.added.join(", ")}</div> : null}
                        {row.removed?.length ? <div style={S.commandSmall}>Removed: {row.removed.join(", ")}</div> : null}
                      </>
                    ) : null}
                    {row.enforced_by ? <div style={S.commandSmall}>Enforced by {row.enforced_by}.</div> : null}
                    {row.owner_bound ? <div style={S.commandSmall}>Owner bound: {formatOwnerBound(row.owner_bound)}</div> : null}
                  </div>
                ))}
                {(preview.effects || []).map((effect, i) => (
                  <div key={i} style={S.commandSmall}>{effect}</div>
                ))}
                {preview.blockers && preview.blockers.length > 0 ? (
                  <div style={{ ...S.commandSmall, color: "#fca5a5" }}>
                    Can't run yet: {preview.blockers.join("; ")}
                  </div>
                ) : null}
                <>
                  {preview.journal_required ? (
                    <>
                      <div style={S.commandSmall}>
                        {preview.journal_prompt || "Record why this widening is not revenge, FOMO, or chasing losses."}
                      </div>
                      <textarea
                        value={journalInput}
                        onChange={(e) => setJournalInput(e.target.value)}
                        aria-label="Anti-impulse journal reason"
                        rows={3}
                        style={{ ...S.confirmInput, minHeight: 84, resize: "vertical" }}
                      />
                      <div style={S.commandSmall}>
                        Minimum {preview.journal_minimum_length ?? 20} characters.
                      </div>
                    </>
                  ) : null}
                  <div style={S.commandSmall}>
                    To run, this must say exactly: <code>{preview.confirm_phrase}</code>
                  </div>
                  <input
                    value={confirmInput}
                    onChange={(e) => setConfirmInput(e.target.value)}
                    aria-label="Type the confirmation phrase to run the command"
                    style={S.confirmInput}
                  />
                  <div style={S.commandButtons}>
                    <button disabled={busy} onClick={() => void runProposed()} style={S.commandButton}>
                      Confirm & run
                    </button>
                    <button
                      disabled={busy}
                      onClick={() => { setProposed(null); setPreview(null); setConfirmInput(""); setJournalInput(""); setReceiptMsg(""); }}
                      style={S.commandButtonGhost}
                    >
                      Cancel
                    </button>
                  </div>
                </>
                {receiptMsg ? <div style={S.receiptMsg}>{receiptMsg}</div> : null}
              </div>
            ) : receiptMsg ? (
              <div style={S.receiptMsg}>{receiptMsg}</div>
            ) : null}
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

function extractPreviewReason(params: Record<string, unknown> | null | undefined): string {
  const value = params?.journal_reason ?? params?.reason;
  return typeof value === "string" ? value : "";
}

function assistantResponderLabel(reply: AssistantReply): string {
  const model = reply.model?.trim();
  if (reply.source === "ai-local") return model ? `Local AI · ${model}` : "Local AI";
  if (reply.source === "ai") return model ? `Claude · ${model}` : "Claude";
  if (reply.source === "local") return "CAS runtime truth";
  if (reply.source === "unconfigured") return "Configuration check";
  if (reply.source === "error") return "Model fallback status";
  return model || reply.source || "CAS Assistant";
}

function formatContractValue(value: unknown, valueKind?: string): string {
  if (valueKind === "toggle") return value ? "ON" : "OFF";
  if (Array.isArray(value)) return value.join(", ");
  if (value == null) return "n/a";
  return String(value);
}

function formatOwnerBound(bound: unknown): string {
  if (!bound || typeof bound !== "object" || Array.isArray(bound)) return String(bound ?? "n/a");
  const record = bound as Record<string, unknown>;
  if ("min" in record || "max" in record) {
    return `${String(record.min ?? "n/a")} to ${String(record.max ?? "n/a")}`;
  }
  if (Array.isArray(record.allowed)) {
    return record.allowed.join(", ");
  }
  return JSON.stringify(record);
}

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
  messageStack: { display: "flex", flexDirection: "column", maxWidth: "85%", minWidth: 0 },
  bubble: { maxWidth: "100%", padding: "9px 12px", borderRadius: 12, fontSize: 14, lineHeight: 1.45, whiteSpace: "pre-wrap", wordBreak: "break-word" },
  bubbleUser: { background: ACCENT, color: "#fff", borderBottomRightRadius: 4 },
  bubbleAi: { background: "#1b2740", color: "#e5e7eb", borderBottomLeftRadius: 4 },
  responder: { marginTop: 4, padding: "0 4px", color: "#8bd5c6", fontSize: 10, fontWeight: 600 },
  pending: { opacity: 0.6 },
  commandCard: {
    alignSelf: "stretch",
    border: "1px solid #2a3650",
    borderRadius: 10,
    padding: 10,
    background: "#111c33",
    fontSize: 13,
    display: "grid",
    gap: 6,
  },
  commandTitle: { fontWeight: 700, color: "#f8fafc" },
  commandSmall: { color: "#cbd5e1", fontSize: 12, lineHeight: 1.35, wordBreak: "break-word" },
  commandContract: {
    marginTop: 6,
    padding: "8px 10px",
    borderRadius: 8,
    border: "1px solid #243049",
    background: "#0d1526",
  },
  confirmInput: {
    width: "100%",
    boxSizing: "border-box",
    background: "#0f1729",
    color: "#e5e7eb",
    border: "1px solid #243049",
    borderRadius: 8,
    padding: "8px 10px",
    fontSize: 13,
  },
  commandButtons: { display: "flex", gap: 8, flexWrap: "wrap" },
  commandButton: {
    background: ACCENT,
    color: "#fff",
    border: "none",
    borderRadius: 8,
    padding: "7px 10px",
    fontWeight: 600,
    cursor: "pointer",
  },
  commandButtonGhost: {
    background: "transparent",
    color: "#cbd5e1",
    border: "1px solid #334155",
    borderRadius: 8,
    padding: "7px 10px",
    fontWeight: 600,
    cursor: "pointer",
  },
  receiptMsg: {
    color: "#bbf7d0",
    background: "#102318",
    border: "1px solid #22543d",
    borderRadius: 8,
    padding: "7px 9px",
    fontSize: 12,
    wordBreak: "break-word",
  },
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
