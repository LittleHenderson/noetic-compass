import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import WordTokenStream, { type WordSpan } from './WordTokenStream';

const tokens = [
  { token_index: 0, token: 'hello' },
  { token_index: 1, token: ' world' },
];

const spans: WordSpan[] = [
  { word: 'hello', token_indices: [0], char_start: 0, char_end: 5 },
  { word: 'world', token_indices: [1], char_start: 6, char_end: 11 },
];

describe('WordTokenStream', () => {
  it('renders each span as a clickable element', () => {
    render(<WordTokenStream tokens={tokens} spans={spans} />);
    expect(screen.getByTestId('word-token-stream')).toBeInTheDocument();
    expect(screen.getByTestId('word-stream-word-0')).toHaveAttribute(
      'data-word',
      'hello',
    );
    expect(screen.getByTestId('word-stream-word-6')).toHaveAttribute(
      'data-word',
      'world',
    );
  });

  it('dispatches onWordClick with the full span on click', () => {
    const handler = vi.fn();
    render(
      <WordTokenStream tokens={tokens} spans={spans} onWordClick={handler} />,
    );

    fireEvent.click(screen.getByTestId('word-stream-word-6'));
    expect(handler).toHaveBeenCalledTimes(1);
    expect(handler).toHaveBeenCalledWith(spans[1]);
  });

  it('renders the inter-word gap text between spans', () => {
    render(<WordTokenStream tokens={tokens} spans={spans} />);
    // The space between 'hello' and 'world' is a literal gap span.
    expect(screen.getByTestId('word-stream-gap-1').textContent).toBe(' ');
  });

  it('shows a passive placeholder when spans is undefined', () => {
    render(<WordTokenStream tokens={tokens} spans={undefined} />);
    expect(screen.getByTestId('word-token-stream-placeholder')).toBeInTheDocument();
    expect(screen.queryByTestId('word-token-stream')).toBeNull();
  });

  it('shows a friendly placeholder when no tokens have arrived yet', () => {
    render(<WordTokenStream tokens={[]} spans={undefined} />);
    expect(
      screen.getByTestId('word-token-stream-placeholder').textContent,
    ).toContain('Generated text will appear here');
  });

  it('renders a tooltip for multi-token words', () => {
    const multi: WordSpan[] = [
      { word: 'wound.', token_indices: [5, 6], char_start: 0, char_end: 6 },
    ];
    render(<WordTokenStream tokens={[]} spans={multi} />);
    const el = screen.getByTestId('word-stream-word-0');
    expect(el.getAttribute('title')).toContain('tokens 5-6');
  });

  it('highlights the word that contains the current token', () => {
    render(
      <WordTokenStream
        tokens={tokens}
        spans={spans}
        currentTokenIndex={1}
      />,
    );
    const helloEl = screen.getByTestId('word-stream-word-0');
    const worldEl = screen.getByTestId('word-stream-word-6');
    // Active span gets a teal outline; inactive does not.
    expect(worldEl.style.outline).not.toBe('none');
    expect(helloEl.style.outline).toBe('none');
  });
});
