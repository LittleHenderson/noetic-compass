import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { GlassPanel } from './GlassPanel';
import { GLASS_RADIUS } from '../../lib/designTokens';

// Note: jsdom strips `backdrop-filter` from inline style attributes (treats
// it as an unknown property), so we verify intensity via the data-intensity
// marker instead of the literal CSS value. Real blur rendering is covered
// by the Playwright E2E suite (visible canvas + screenshot diff).
describe('GlassPanel', () => {
  it('renders children', () => {
    render(<GlassPanel>Hello Atlas</GlassPanel>);
    expect(screen.getByText('Hello Atlas')).toBeInTheDocument();
  });

  it('applies regular blur by default', () => {
    render(<GlassPanel ariaLabel="default-panel">content</GlassPanel>);
    const panel = screen.getByLabelText('default-panel');
    expect(panel.getAttribute('data-intensity')).toBe('regular');
  });

  it('applies thin blur when intensity=thin', () => {
    render(
      <GlassPanel intensity="thin" ariaLabel="thin-panel">
        content
      </GlassPanel>,
    );
    const panel = screen.getByLabelText('thin-panel');
    expect(panel.getAttribute('data-intensity')).toBe('thin');
  });

  it('applies thick blur when intensity=thick', () => {
    render(
      <GlassPanel intensity="thick" ariaLabel="thick-panel">
        content
      </GlassPanel>,
    );
    const panel = screen.getByLabelText('thick-panel');
    expect(panel.getAttribute('data-intensity')).toBe('thick');
  });

  it('uses the design-token border radius', () => {
    render(<GlassPanel ariaLabel="radius-panel">content</GlassPanel>);
    const panel = screen.getByLabelText('radius-panel');
    const style = panel.getAttribute('style') ?? '';
    expect(style).toContain(`border-radius: ${GLASS_RADIUS}px`);
  });

  it('wires onClick and marks interactive when interactive=true', () => {
    const handler = vi.fn();
    render(
      <GlassPanel interactive onClick={handler} ariaLabel="click-panel">
        click me
      </GlassPanel>,
    );
    const panel = screen.getByLabelText('click-panel');
    expect(panel.getAttribute('data-interactive')).toBe('true');
    fireEvent.click(panel);
    expect(handler).toHaveBeenCalledTimes(1);
  });

  it('propagates the ARIA label', () => {
    render(<GlassPanel ariaLabel="status-panel">x</GlassPanel>);
    expect(screen.getByLabelText('status-panel')).toBeInTheDocument();
  });

  it('renders as a different element when `as` is provided', () => {
    render(
      <GlassPanel as="section" ariaLabel="section-panel">
        section content
      </GlassPanel>,
    );
    const panel = screen.getByLabelText('section-panel');
    expect(panel.tagName.toLowerCase()).toBe('section');
  });

  it('accepts custom padding', () => {
    render(
      <GlassPanel padding={32} ariaLabel="padded-panel">
        padded
      </GlassPanel>,
    );
    const panel = screen.getByLabelText('padded-panel');
    const style = panel.getAttribute('style') ?? '';
    expect(style).toContain('padding: 32px');
  });
});
