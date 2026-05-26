import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import Mode7Timeline, {
  type Mode7Frame,
  type Token,
} from './Mode7Timeline';

const tokens: Token[] = [
  { token_index: 0, token: 'The' },
  { token_index: 1, token: ' patient' },
  { token_index: 2, token: ' triage' },
  { token_index: 3, token: ' nurse' },
];

const frames: Mode7Frame[] = [
  {
    token_index: 0,
    mode7_attribution: [
      { to_token_index: 0, from_token_index: null, weight: 1.0 },
    ],
  },
  {
    token_index: 1,
    mode7_attribution: [
      { to_token_index: 1, from_token_index: 0, weight: 0.82 },
    ],
  },
  {
    token_index: 2,
    mode7_attribution: [
      { to_token_index: 2, from_token_index: 1, weight: 0.55 },
      { to_token_index: 2, from_token_index: 0, weight: 0.32 },
    ],
  },
  {
    token_index: 3,
    mode7_attribution: [
      { to_token_index: 3, from_token_index: 2, weight: 0.48 },
    ],
  },
];

describe('Mode7Timeline', () => {
  it('renders one cell per token', () => {
    render(
      <Mode7Timeline
        tokens={tokens}
        frames={frames}
        currentTokenIndex={0}
      />,
    );
    const cells = screen.getAllByRole('button');
    expect(cells).toHaveLength(tokens.length);
  });

  it('highlights the current cell via data-current attribute', () => {
    render(
      <Mode7Timeline
        tokens={tokens}
        frames={frames}
        currentTokenIndex={2}
      />,
    );
    const current = screen.getByTestId('mode7-timeline-cell-2');
    expect(current.getAttribute('data-current')).toBe('true');
    expect(current.getAttribute('aria-current')).toBe('true');
    const other = screen.getByTestId('mode7-timeline-cell-0');
    expect(other.getAttribute('data-current')).toBe('false');
  });

  it('exposes slider ARIA semantics with valuemin/max/now', () => {
    render(
      <Mode7Timeline
        tokens={tokens}
        frames={frames}
        currentTokenIndex={1}
      />,
    );
    const slider = screen.getByRole('slider');
    expect(slider.getAttribute('aria-valuemin')).toBe('0');
    expect(slider.getAttribute('aria-valuemax')).toBe(String(tokens.length - 1));
    expect(slider.getAttribute('aria-valuenow')).toBe('1');
  });

  it('fires onTokenSelect with the clicked cell index', () => {
    const onSelect = vi.fn();
    render(
      <Mode7Timeline
        tokens={tokens}
        frames={frames}
        currentTokenIndex={0}
        onTokenSelect={onSelect}
      />,
    );
    fireEvent.click(screen.getByTestId('mode7-timeline-cell-2'));
    expect(onSelect).toHaveBeenCalledWith(2);
  });

  it('ArrowRight increments current via onTokenSelect', () => {
    const onSelect = vi.fn();
    render(
      <Mode7Timeline
        tokens={tokens}
        frames={frames}
        currentTokenIndex={1}
        onTokenSelect={onSelect}
      />,
    );
    fireEvent.keyDown(screen.getByRole('slider'), { key: 'ArrowRight' });
    expect(onSelect).toHaveBeenCalledWith(2);
  });

  it('ArrowLeft decrements current via onTokenSelect', () => {
    const onSelect = vi.fn();
    render(
      <Mode7Timeline
        tokens={tokens}
        frames={frames}
        currentTokenIndex={2}
        onTokenSelect={onSelect}
      />,
    );
    fireEvent.keyDown(screen.getByRole('slider'), { key: 'ArrowLeft' });
    expect(onSelect).toHaveBeenCalledWith(1);
  });

  it('ArrowLeft at index 0 clamps to 0', () => {
    const onSelect = vi.fn();
    render(
      <Mode7Timeline
        tokens={tokens}
        frames={frames}
        currentTokenIndex={0}
        onTokenSelect={onSelect}
      />,
    );
    fireEvent.keyDown(screen.getByRole('slider'), { key: 'ArrowLeft' });
    expect(onSelect).toHaveBeenCalledWith(0);
  });

  it('ArrowRight at last index clamps to last', () => {
    const onSelect = vi.fn();
    const last = tokens.length - 1;
    render(
      <Mode7Timeline
        tokens={tokens}
        frames={frames}
        currentTokenIndex={last}
        onTokenSelect={onSelect}
      />,
    );
    fireEvent.keyDown(screen.getByRole('slider'), { key: 'ArrowRight' });
    expect(onSelect).toHaveBeenCalledWith(last);
  });

  it('Home jumps to index 0', () => {
    const onSelect = vi.fn();
    render(
      <Mode7Timeline
        tokens={tokens}
        frames={frames}
        currentTokenIndex={3}
        onTokenSelect={onSelect}
      />,
    );
    fireEvent.keyDown(screen.getByRole('slider'), { key: 'Home' });
    expect(onSelect).toHaveBeenCalledWith(0);
  });

  it('End jumps to last index', () => {
    const onSelect = vi.fn();
    render(
      <Mode7Timeline
        tokens={tokens}
        frames={frames}
        currentTokenIndex={0}
        onTokenSelect={onSelect}
      />,
    );
    fireEvent.keyDown(screen.getByRole('slider'), { key: 'End' });
    expect(onSelect).toHaveBeenCalledWith(tokens.length - 1);
  });

  it('showAttributionEdges=false hides the SVG edge layer', () => {
    render(
      <Mode7Timeline
        tokens={tokens}
        frames={frames}
        currentTokenIndex={2}
        showAttributionEdges={false}
      />,
    );
    expect(screen.queryByTestId('mode7-timeline-edges')).toBeNull();
  });

  it('showAttributionEdges=true renders one edge path per non-null from_token_index for the current frame', () => {
    render(
      <Mode7Timeline
        tokens={tokens}
        frames={frames}
        currentTokenIndex={2}
        showAttributionEdges={true}
      />,
    );
    const svg = screen.getByTestId('mode7-timeline-edges');
    const paths = svg.querySelectorAll('path');
    expect(paths.length).toBe(2);
    expect(screen.getByTestId('mode7-timeline-edge-1-2')).toBeTruthy();
    expect(screen.getByTestId('mode7-timeline-edge-0-2')).toBeTruthy();
  });

  it('omits edges whose from_token_index is null (initial token)', () => {
    render(
      <Mode7Timeline
        tokens={tokens}
        frames={frames}
        currentTokenIndex={0}
        showAttributionEdges={true}
      />,
    );
    const svg = screen.getByTestId('mode7-timeline-edges');
    const paths = svg.querySelectorAll('path');
    expect(paths.length).toBe(0);
  });

  it('truncates long token strings with an ellipsis', () => {
    const longTokens: Token[] = [
      { token_index: 0, token: 'extraordinarily' },
      { token_index: 1, token: 'short' },
    ];
    render(
      <Mode7Timeline
        tokens={longTokens}
        frames={[]}
        currentTokenIndex={0}
      />,
    );
    const cell0 = screen.getByTestId('mode7-timeline-cell-0');
    expect(cell0.textContent).toContain('…');
    expect(cell0).not.toHaveAttribute('title');
    fireEvent.mouseEnter(cell0);
    expect(screen.getByRole('tooltip')).toHaveTextContent('extraordinarily');
  });
});
