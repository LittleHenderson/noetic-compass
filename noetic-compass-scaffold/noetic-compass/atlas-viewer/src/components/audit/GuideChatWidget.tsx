import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type CSSProperties,
  type KeyboardEvent,
} from 'react';
import { AnimatePresence, motion } from 'framer-motion';

import { askExplainer } from '../../lib/explainerApi';
import {
  ACCENT_CYAN,
  ACCENT_TEAL,
  COLORS,
  FONT_FAMILY,
} from '../../lib/designTokens';

const LAUNCHER_Z = 1200;
const PANEL_Z = 1200;
const PANEL_TRANSITION = { duration: 0.12, ease: 'easeOut' } as const;

export const GUIDE_HONESTY_LINE =
  'Answers come only from the public CAS Harness guide - not internal scoring, probes, or source.';

const GREETING =
  'Ask me how CAS Harness works or how to run an audit. I only read the public guide.';

type ChatRole = 'user' | 'assistant' | 'error';

interface ChatMessage {
  role: ChatRole;
  text: string;
  sources?: string[];
}

const launcherStyle: CSSProperties = {
  position: 'fixed',
  right: 20,
  bottom: 20,
  zIndex: LAUNCHER_Z,
  width: 52,
  height: 52,
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  borderRadius: 16,
  border: `1px solid ${ACCENT_TEAL}6b`,
  background:
    'linear-gradient(145deg, rgba(15, 23, 42, 0.82), rgba(8, 13, 27, 0.66))',
  boxShadow:
    '0 14px 36px rgba(0, 0, 0, 0.42), inset 0 1px 0 rgba(255, 255, 255, 0.12), 0 0 0 1px rgba(45, 212, 191, 0.12)',
  backdropFilter: 'blur(14px) saturate(1.3)',
  WebkitBackdropFilter: 'blur(14px) saturate(1.3)',
  color: COLORS.textPrimary,
  cursor: 'pointer',
  fontFamily: FONT_FAMILY,
  padding: 0,
};

const launcherGlyphStyle: CSSProperties = {
  width: 28,
  height: 28,
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  borderRadius: 10,
  border: '1px solid rgba(45, 212, 191, 0.34)',
  color: '#ccfbf1',
  fontSize: 18,
  fontWeight: 850,
  lineHeight: 1,
};

const panelStyle: CSSProperties = {
  position: 'fixed',
  right: 20,
  bottom: 82,
  zIndex: PANEL_Z,
  width: 'min(380px, calc(100vw - 32px))',
  maxHeight: '70vh',
  display: 'flex',
  flexDirection: 'column',
  overflow: 'hidden',
  borderRadius: 16,
  border: '1px solid rgba(255, 255, 255, 0.22)',
  background:
    'linear-gradient(160deg, rgba(15, 23, 42, 0.86), rgba(8, 13, 27, 0.72))',
  boxShadow:
    '0 24px 80px rgba(0, 0, 0, 0.48), inset 0 1px 0 rgba(255, 255, 255, 0.14), 0 0 0 1px rgba(45, 212, 191, 0.12)',
  backdropFilter: 'blur(24px) saturate(1.35)',
  WebkitBackdropFilter: 'blur(24px) saturate(1.35)',
  color: COLORS.textPrimary,
  fontFamily: FONT_FAMILY,
};

const headerStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'flex-start',
  gap: 10,
  padding: '12px 12px 10px 14px',
  borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
};

const headerEyebrowStyle: CSSProperties = {
  display: 'block',
  marginBottom: 3,
  color: ACCENT_CYAN,
  fontSize: 9,
  fontWeight: 900,
  letterSpacing: 0.9,
  textTransform: 'uppercase',
};

const headerTitleStyle: CSSProperties = {
  margin: 0,
  fontSize: 13,
  fontWeight: 850,
  letterSpacing: 0.2,
  color: COLORS.textPrimary,
};

const headerSublineStyle: CSSProperties = {
  margin: '3px 0 0',
  fontSize: 10.5,
  lineHeight: 1.35,
  fontWeight: 600,
  color: COLORS.textSecondary,
};

const closeButtonStyle: CSSProperties = {
  flex: '0 0 auto',
  width: 26,
  height: 26,
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  borderRadius: 8,
  border: '1px solid rgba(255, 255, 255, 0.12)',
  background: 'rgba(255, 255, 255, 0.04)',
  color: COLORS.textSecondary,
  cursor: 'pointer',
  fontSize: 14,
  lineHeight: 1,
  fontFamily: FONT_FAMILY,
  padding: 0,
};

const listStyle: CSSProperties = {
  flex: '1 1 auto',
  overflowY: 'auto',
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
  padding: '12px 14px',
};

const footerStyle: CSSProperties = {
  flex: '0 0 auto',
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
  padding: '10px 12px 12px',
  borderTop: '1px solid rgba(255, 255, 255, 0.08)',
};

const inputRowStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'flex-end',
  gap: 8,
};

const textareaStyle: CSSProperties = {
  flex: '1 1 auto',
  minHeight: 38,
  maxHeight: 96,
  resize: 'none',
  borderRadius: 10,
  border: '1px solid rgba(255, 255, 255, 0.12)',
  background: 'rgba(2, 6, 23, 0.45)',
  color: COLORS.textPrimary,
  fontFamily: FONT_FAMILY,
  fontSize: 13,
  lineHeight: 1.4,
  padding: '8px 10px',
  outline: 'none',
};

const sendButtonStyle: CSSProperties = {
  flex: '0 0 auto',
  minHeight: 38,
  padding: '0 14px',
  borderRadius: 10,
  border: '1px solid rgba(45, 212, 191, 0.42)',
  background: 'rgba(45, 212, 191, 0.12)',
  color: '#ccfbf1',
  cursor: 'pointer',
  fontFamily: FONT_FAMILY,
  fontSize: 12.5,
  fontWeight: 750,
};

const footerHonestyStyle: CSSProperties = {
  margin: 0,
  fontSize: 10,
  lineHeight: 1.35,
  fontWeight: 600,
  color: COLORS.textMuted,
};

function bubbleStyle(role: ChatRole): CSSProperties {
  if (role === 'user') {
    return {
      alignSelf: 'flex-end',
      maxWidth: '85%',
      borderRadius: '12px 12px 4px 12px',
      border: '1px solid rgba(45, 212, 191, 0.36)',
      background: 'rgba(45, 212, 191, 0.12)',
      color: '#e5f9f7',
      fontSize: 13,
      lineHeight: 1.45,
      padding: '8px 11px',
      whiteSpace: 'pre-wrap',
      wordBreak: 'break-word',
    };
  }
  if (role === 'error') {
    return {
      alignSelf: 'flex-start',
      maxWidth: '90%',
      borderRadius: '12px 12px 12px 4px',
      border: '1px solid rgba(251, 113, 133, 0.42)',
      background: 'rgba(251, 113, 133, 0.10)',
      color: '#ffe4e6',
      fontSize: 12.5,
      lineHeight: 1.45,
      padding: '8px 11px',
      whiteSpace: 'pre-wrap',
      wordBreak: 'break-word',
    };
  }
  return {
    alignSelf: 'flex-start',
    maxWidth: '90%',
    borderRadius: '12px 12px 12px 4px',
    border: '1px solid rgba(255, 255, 255, 0.10)',
    background: 'rgba(255, 255, 255, 0.04)',
    color: COLORS.textPrimary,
    fontSize: 13,
    lineHeight: 1.45,
    padding: '8px 11px',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  };
}

const sourcesRowStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 6,
  marginTop: 7,
};

const sourceChipStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  borderRadius: 999,
  border: '1px solid rgba(255, 255, 255, 0.10)',
  background: 'rgba(2, 6, 23, 0.4)',
  color: COLORS.textMuted,
  fontSize: 9.5,
  fontWeight: 600,
  letterSpacing: 0.2,
  padding: '2px 7px',
  wordBreak: 'break-all',
};

const typingStyle: CSSProperties = {
  ...bubbleStyle('assistant'),
  color: COLORS.textSecondary,
  fontStyle: 'italic',
};

export function GuideChatWidget(): JSX.Element {
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const [draft, setDraft] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'assistant', text: GREETING },
  ]);

  const panelId = useId();
  const listRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  const close = useCallback(() => setOpen(false), []);
  const toggle = useCallback(() => setOpen((prev) => !prev), []);

  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.stopPropagation();
        setOpen(false);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const list = listRef.current;
    if (list) list.scrollTop = list.scrollHeight;
    inputRef.current?.focus();
  }, [open, messages, pending]);

  const submit = useCallback(async () => {
    const question = draft.trim();
    if (!question || pending) return;

    setMessages((prev) => [...prev, { role: 'user', text: question }]);
    setDraft('');
    setPending(true);
    try {
      const response = await askExplainer(question);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: response.answer,
          sources: response.sources,
        },
      ]);
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err);
      setMessages((prev) => [
        ...prev,
        {
          role: 'error',
          text: `The Guide is unavailable right now. Try again.\n${detail}`,
        },
      ]);
    } finally {
      setPending(false);
    }
  }, [draft, pending]);

  const onTextareaKeyDown = useCallback(
    (event: KeyboardEvent<HTMLTextAreaElement>) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        void submit();
      }
    },
    [submit],
  );

  return (
    <>
      <motion.button
        type="button"
        aria-label={open ? 'Close CAS Harness Guide' : 'Open CAS Harness Guide'}
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        onClick={toggle}
        style={launcherStyle}
        title="CAS Harness Guide"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.94 }}
        transition={PANEL_TRANSITION}
        data-testid="guide-chat-launcher"
      >
        <span style={launcherGlyphStyle} aria-hidden="true">
          ?
        </span>
      </motion.button>

      <AnimatePresence>
        {open ? (
          <motion.section
            key="guide-panel"
            id={panelId}
            role="dialog"
            aria-label="CAS Harness Guide"
            style={panelStyle}
            initial={{ opacity: 0, y: 12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.98 }}
            transition={PANEL_TRANSITION}
            data-testid="guide-chat-panel"
          >
            <header style={headerStyle}>
              <div style={{ flex: '1 1 auto', minWidth: 0 }}>
                <span style={headerEyebrowStyle}>Guide</span>
                <p style={headerTitleStyle}>CAS Harness Guide</p>
                <p style={headerSublineStyle}>{GUIDE_HONESTY_LINE}</p>
              </div>
              <button
                type="button"
                aria-label="Close CAS Harness Guide"
                onClick={close}
                style={closeButtonStyle}
                data-testid="guide-chat-close"
              >
                x
              </button>
            </header>

            <div
              ref={listRef}
              style={listStyle}
              role="log"
              aria-live="polite"
              aria-label="CAS Harness Guide conversation"
              data-testid="guide-chat-messages"
            >
              {messages.map((message, index) => (
                <div key={`${message.role}-${index}`} style={bubbleStyle(message.role)}>
                  <span>{message.text}</span>
                  {message.role === 'assistant' &&
                  message.sources &&
                  message.sources.length > 0 ? (
                    <div style={sourcesRowStyle}>
                      {message.sources.map((source) => (
                        <span
                          key={source}
                          style={sourceChipStyle}
                          data-testid="guide-chat-source"
                        >
                          Source: {source}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>
              ))}
              {pending ? (
                <div style={typingStyle} data-testid="guide-chat-typing">
                  Thinking...
                </div>
              ) : null}
            </div>

            <footer style={footerStyle}>
              <div style={inputRowStyle}>
                <textarea
                  ref={inputRef}
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  onKeyDown={onTextareaKeyDown}
                  placeholder="Ask about CAS Harness..."
                  rows={1}
                  style={textareaStyle}
                  aria-label="Ask the CAS Harness Guide"
                  data-testid="guide-chat-input"
                />
                <button
                  type="button"
                  onClick={() => void submit()}
                  disabled={pending || draft.trim().length === 0}
                  style={{
                    ...sendButtonStyle,
                    opacity: pending || draft.trim().length === 0 ? 0.55 : 1,
                    cursor:
                      pending || draft.trim().length === 0 ? 'not-allowed' : 'pointer',
                  }}
                  data-testid="guide-chat-send"
                >
                  Send
                </button>
              </div>
              <p style={footerHonestyStyle}>{GUIDE_HONESTY_LINE}</p>
            </footer>
          </motion.section>
        ) : null}
      </AnimatePresence>
    </>
  );
}

export default GuideChatWidget;
