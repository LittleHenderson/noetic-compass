import { useState, type CSSProperties, type FormEvent } from 'react';
import { motion } from 'framer-motion';
import { GlassPanel } from '../components/ui/GlassPanel';
import { PageShell } from '../components/ui/PageShell';
import { askExplainer, type ExplainerChatResponse } from '../lib/explainerApi';
import {
  ACCENT_AMBER,
  ACCENT_TEAL,
  COLORS,
  SPRING_SNAPPY,
  THEME,
} from '../lib/designTokens';

const STARTERS = [
  'Walk me through my first CAS Harness audit.',
  'What does CAS Harness do in plain English?',
  'How should I read a verdict and evidence packet?',
  'What should I do if a proof gate is unavailable?',
];

const headingStyle: CSSProperties = {
  margin: 0,
  fontSize: 24,
  fontWeight: 700,
  color: COLORS.textPrimary,
};

const introStyle: CSSProperties = {
  margin: '8px 0 18px 0',
  fontSize: 13.5,
  lineHeight: 1.55,
  color: COLORS.textSecondary,
};

const layoutStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'minmax(0, 1fr)',
  gap: 14,
};

const starterGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))',
  gap: 8,
};

const starterButtonStyle: CSSProperties = {
  minHeight: 48,
  padding: '10px 12px',
  borderRadius: 6,
  border: '1px solid rgba(255, 255, 255, 0.08)',
  background: 'rgba(255, 255, 255, 0.03)',
  color: COLORS.textSecondary,
  fontSize: 12.5,
  lineHeight: 1.4,
  fontFamily: THEME.fontFamily,
  textAlign: 'left',
  cursor: 'pointer',
};

const formStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
};

const textareaStyle: CSSProperties = {
  minHeight: 96,
  resize: 'vertical',
  padding: '12px 14px',
  borderRadius: 6,
  border: '1px solid rgba(255, 255, 255, 0.08)',
  background: 'rgba(255, 255, 255, 0.025)',
  color: COLORS.textPrimary,
  fontSize: 14,
  lineHeight: 1.55,
  fontFamily: THEME.fontFamily,
  outline: 'none',
};

const buttonStyle: CSSProperties = {
  alignSelf: 'flex-start',
  padding: '9px 14px',
  borderRadius: 6,
  border: `1px solid ${ACCENT_TEAL}`,
  background: 'rgba(45, 212, 191, 0.08)',
  color: ACCENT_TEAL,
  fontSize: 13,
  fontWeight: 600,
  fontFamily: THEME.fontFamily,
  cursor: 'pointer',
};

const answerStyle: CSSProperties = {
  margin: 0,
  whiteSpace: 'pre-wrap',
  fontSize: 13.5,
  lineHeight: 1.65,
  color: COLORS.textPrimary,
};

const metaStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 8,
  marginTop: 14,
  paddingTop: 12,
  borderTop: '1px solid rgba(255, 255, 255, 0.06)',
  fontSize: 11,
  color: COLORS.textMuted,
  fontFamily: THEME.fontMono,
};

const statusStyle = (kind: 'idle' | 'error'): CSSProperties => ({
  margin: 0,
  fontSize: 12.5,
  lineHeight: 1.55,
  color: kind === 'error' ? ACCENT_AMBER : COLORS.textMuted,
});

function ResponsePanel({ response }: { response: ExplainerChatResponse | null }) {
  if (!response) {
    return (
      <GlassPanel intensity="thin" padding={16} ariaLabel="Explainer response">
        <p style={statusStyle('idle')}>
          Ask for product guidance, verdict interpretation, or help moving through the audit flow.
          The explainer only uses the public-safe knowledge base.
        </p>
      </GlassPanel>
    );
  }

  return (
    <GlassPanel intensity="thin" padding={16} ariaLabel="Explainer answer">
      <p style={answerStyle}>{response.answer}</p>
      <div style={metaStyle}>
        <span>{response.used_gemini ? response.model : 'local guardrail'}</span>
        <span>{response.safety_mode}</span>
        {response.sources.slice(0, 2).map((source) => (
          <span key={source}>{source}</span>
        ))}
      </div>
    </GlassPanel>
  );
}

export default function ExplainerPage() {
  const [question, setQuestion] = useState(STARTERS[0]);
  const [response, setResponse] = useState<ExplainerChatResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event?: FormEvent<HTMLFormElement>) => {
    event?.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || loading) return;
    setLoading(true);
    setError(null);
    try {
      const next = await askExplainer(trimmed);
      setResponse(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageShell cardMaxWidth={780} contentAlign="start">
      <GlassPanel intensity="regular" padding={24} ariaLabel="CAS Harness explainer">
        <h1 style={headingStyle}>CAS Harness guide</h1>
        <p style={introStyle}>
          Ask how to use the app, what an audit step means, or how to read a verdict. The guide is
          intentionally limited to public-safe product knowledge.
        </p>

        <div style={layoutStyle}>
          <div style={starterGridStyle} aria-label="Starter questions">
            {STARTERS.map((starter) => (
              <button
                key={starter}
                type="button"
                style={starterButtonStyle}
                onClick={() => setQuestion(starter)}
              >
                {starter}
              </button>
            ))}
          </div>

          <form style={formStyle} onSubmit={submit}>
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              style={textareaStyle}
              maxLength={1200}
              aria-label="Ask the CAS Harness guide"
            />
            <motion.button
              type="submit"
              style={{
                ...buttonStyle,
                opacity: loading ? 0.65 : 1,
                cursor: loading ? 'wait' : 'pointer',
              }}
              whileHover={loading ? undefined : { background: 'rgba(45, 212, 191, 0.16)' }}
              whileTap={loading ? undefined : { scale: 0.99 }}
              transition={SPRING_SNAPPY}
              disabled={loading}
            >
              {loading ? 'Asking...' : 'Ask guide'}
            </motion.button>
          </form>

          {error ? (
            <GlassPanel intensity="thin" padding={16} ariaLabel="Explainer error">
              <p style={statusStyle('error')}>{error}</p>
            </GlassPanel>
          ) : (
            <ResponsePanel response={response} />
          )}
        </div>
      </GlassPanel>
    </PageShell>
  );
}
