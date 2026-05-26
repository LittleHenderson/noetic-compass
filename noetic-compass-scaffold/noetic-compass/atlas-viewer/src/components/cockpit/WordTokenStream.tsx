import { useMemo } from 'react';
import type { CSSProperties } from 'react';
import { ATLAS_STATUS_COLORS } from '../../lib/atlasPalette';
import { THEME, COLORS } from '../../lib/designTokens';
import LiquidGlassTooltip from '../ui/LiquidGlassTooltip';

export interface WordSpan {
  word: string;
  token_indices: number[];
  char_start: number;
  char_end: number;
}

export interface WordTokenStreamProps {
  /** Token strings in emission order. Used to reconstruct the displayed text. */
  tokens: { token_index: number; token: string }[];
  /** Word spans emitted by the worker (one-shot, post-stream). */
  spans?: WordSpan[];
  /** Currently-active token index — used to highlight the surrounding word. */
  currentTokenIndex?: number;
  /** Click handler — dispatched once per word click. */
  onWordClick?: (span: WordSpan) => void;
  className?: string;
}

const wrapperStyle: CSSProperties = {
  width: '100%',
  padding: '10px 14px',
  borderRadius: 6,
  background: 'rgba(2, 6, 23, 0.45)',
  border: '1px solid rgba(255, 255, 255, 0.06)',
  fontFamily: THEME.fontMono,
  fontSize: 12.5,
  lineHeight: 1.6,
  color: COLORS.textPrimary,
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
  // Disable text selection so word clicks don't fight selection.
  userSelect: 'none',
};

const wordBaseStyle: CSSProperties = {
  display: 'inline',
  padding: '0 1px',
  borderRadius: 3,
  cursor: 'pointer',
  transition: 'background 0.12s ease, color 0.12s ease',
};

const placeholderStyle: CSSProperties = {
  ...wrapperStyle,
  color: COLORS.textMuted,
  fontStyle: 'italic',
};

function tokenIndexToSpanLookup(spans: WordSpan[]): Map<number, WordSpan> {
  const map = new Map<number, WordSpan>();
  for (const span of spans) {
    for (const ti of span.token_indices) {
      map.set(ti, span);
    }
  }
  return map;
}

function tooltipFor(span: WordSpan): string {
  if (span.token_indices.length === 1) {
    return `Inspect this word (token ${span.token_indices[0]})`;
  }
  const first = span.token_indices[0];
  const last = span.token_indices[span.token_indices.length - 1];
  return `Inspect this word (tokens ${first}-${last})`;
}

/**
 * Renders the generated continuation as clickable word spans.
 *
 * When the worker has emitted ``word_spans`` (one-shot, end of stream), each
 * word is rendered as a separate span. Clicking dispatches ``onWordClick``
 * with the full WordSpan — caller is responsible for seeking playback and
 * opening the Evidence Drawer.
 *
 * If ``spans`` is undefined (live stream still in progress, or offline
 * replay trace), the component shows a passive placeholder line listing the
 * concatenated token text without click handlers.
 */
export function WordTokenStream(props: WordTokenStreamProps): JSX.Element {
  const { tokens, spans, currentTokenIndex, onWordClick, className } = props;

  const fullText = useMemo(
    () => tokens.map((t) => t.token).join(''),
    [tokens],
  );

  const activeSpan = useMemo<WordSpan | undefined>(() => {
    if (!spans || currentTokenIndex === undefined) return undefined;
    return tokenIndexToSpanLookup(spans).get(currentTokenIndex);
  }, [spans, currentTokenIndex]);

  if (!spans || spans.length === 0) {
    const placeholderText = fullText.length > 0
      ? fullText
      : 'Generated text will appear here as the model emits tokens.';
    return (
      <div
        className={className}
        data-testid="word-token-stream-placeholder"
        style={placeholderStyle}
      >
        {placeholderText}
      </div>
    );
  }

  // Walk through the full text, emitting either an inter-word gap (plain
  // text) or a clickable word span. We rely on the spans being sorted by
  // char_start (worker guarantees this).
  const sortedSpans = [...spans].sort((a, b) => a.char_start - b.char_start);
  const pieces: JSX.Element[] = [];
  let cursor = 0;

  for (let i = 0; i < sortedSpans.length; i += 1) {
    const span = sortedSpans[i];
    if (span.char_start > cursor) {
      pieces.push(
        <span key={`gap-${i}`} data-testid={`word-stream-gap-${i}`}>
          {fullText.slice(cursor, span.char_start)}
        </span>,
      );
    }
    const isActive = activeSpan === span;
    const wordStyle: CSSProperties = {
      ...wordBaseStyle,
      background: isActive
        ? 'rgba(45, 212, 191, 0.18)'
        : 'transparent',
      color: isActive ? ATLAS_STATUS_COLORS.activeTrace : COLORS.textPrimary,
      outline: isActive
        ? `1px solid ${ATLAS_STATUS_COLORS.activeTrace}`
        : 'none',
    };
    pieces.push(
      <LiquidGlassTooltip
        key={`word-${span.char_start}-${span.char_end}`}
        briefing={tooltipFor(span)}
        focusable={false}
      >
        <span
          role="button"
          tabIndex={0}
          data-testid={`word-stream-word-${span.char_start}`}
          data-word={span.word}
          aria-label={`Inspect word "${span.word}"`}
          style={wordStyle}
          onClick={() => onWordClick?.(span)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              onWordClick?.(span);
            }
          }}
          onMouseEnter={(e) => {
            if (!isActive) {
              (e.currentTarget as HTMLSpanElement).style.background =
                'rgba(45, 212, 191, 0.08)';
            }
          }}
          onMouseLeave={(e) => {
            if (!isActive) {
              (e.currentTarget as HTMLSpanElement).style.background = 'transparent';
            }
          }}
        >
          {span.word}
        </span>
      </LiquidGlassTooltip>,
    );
    cursor = span.char_end;
  }

  if (cursor < fullText.length) {
    pieces.push(
      <span key="gap-trailing" data-testid="word-stream-gap-trailing">
        {fullText.slice(cursor)}
      </span>,
    );
  }

  return (
    <div
      className={className}
      data-testid="word-token-stream"
      style={wrapperStyle}
    >
      {pieces}
    </div>
  );
}

export default WordTokenStream;
