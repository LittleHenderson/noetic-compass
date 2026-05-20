/**
 * Tests for `Notation2DView` — the direct end-to-end validation that the
 * canonical 169-primitive notation map feeds the dashboard UI.
 *
 * Count-agnostic by design: assertions about how many circles render
 * compare against `allPositions().length`, never a hardcoded number.
 */

import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render } from '@testing-library/react';

import canonicalLayout from '../../../../research/cas_probe/stage23_a_notation_2d_layout_20260519.json';
import {
  allPositions,
  KIND_COLOR,
  type CanonicalLayoutPayload,
  type Position2D,
} from '../../lib/notation2DMap';
import { Notation2DView } from './Notation2DView';

const payload = canonicalLayout as CanonicalLayoutPayload;

describe('Notation2DView — canonical map renders end-to-end', () => {
  it('renders one circle per canonical primitive (count-agnostic)', () => {
    const { container } = render(<Notation2DView />);
    const circles = container.querySelectorAll('circle');
    expect(circles.length).toBe(payload.primitives.length);
  });

  it('every rendered primitive has the canonical color for its kind', () => {
    const { container } = render(<Notation2DView />);
    for (const p of allPositions()) {
      const circle = container.querySelector(
        `[data-testid="notation-primitive-${CSS.escape(p.primitive)}"]`,
      );
      expect(circle, `circle missing for primitive ${p.primitive}`).not.toBeNull();
      expect(circle?.getAttribute('fill')).toBe(KIND_COLOR[p.kind]);
      expect(circle?.getAttribute('data-kind')).toBe(p.kind);
    }
  });

  it('renders the layout_version in the footer', () => {
    const { getByTestId } = render(<Notation2DView />);
    const footer = getByTestId('notation-2d-footer');
    expect(footer.textContent).toContain(payload.layout_version);
    expect(footer.textContent).toContain(String(payload.primitives.length));
  });

  it('hovering a primitive shows the tooltip with primitive, kind, coords', () => {
    const { container, queryByTestId, getByTestId } = render(<Notation2DView />);
    expect(queryByTestId('notation-2d-tooltip')).toBeNull();
    const target = allPositions()[0];
    const circle = container.querySelector(
      `[data-testid="notation-primitive-${CSS.escape(target.primitive)}"]`,
    );
    fireEvent.mouseEnter(circle!);
    const tooltip = getByTestId('notation-2d-tooltip');
    expect(tooltip.textContent).toContain(target.primitive);
    expect(tooltip.textContent).toContain(target.kind);
    expect(tooltip.textContent).toContain(target.x.toFixed(3));
    expect(tooltip.textContent).toContain(target.y.toFixed(3));
  });

  it('mouse leave clears the tooltip', () => {
    const { container, queryByTestId } = render(<Notation2DView />);
    const target = allPositions()[0];
    const circle = container.querySelector(
      `[data-testid="notation-primitive-${CSS.escape(target.primitive)}"]`,
    );
    fireEvent.mouseEnter(circle!);
    expect(queryByTestId('notation-2d-tooltip')).not.toBeNull();
    fireEvent.mouseLeave(circle!);
    expect(queryByTestId('notation-2d-tooltip')).toBeNull();
  });

  it('clicking a primitive invokes onSelectPrimitive with the right Position2D', () => {
    const onSelect = vi.fn();
    const { container } = render(<Notation2DView onSelectPrimitive={onSelect} />);
    const target: Position2D = allPositions().find((p) => p.primitive === '^3^P')!;
    expect(target).toBeDefined();
    const circle = container.querySelector(
      `[data-testid="notation-primitive-${CSS.escape(target.primitive)}"]`,
    );
    fireEvent.click(circle!);
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({
        primitive: '^3^P',
        kind: 'cognitive_state',
        x: target.x,
        y: target.y,
      }),
    );
  });

  it('emergent_omega primitives (Stage 23.A.3) render with the canonical purple', () => {
    const { container } = render(<Notation2DView />);
    const omegas = allPositions().filter((p) => p.kind === 'emergent_omega');
    expect(omegas.length).toBeGreaterThan(0);
    for (const omega of omegas) {
      const circle = container.querySelector(
        `[data-testid="notation-primitive-${CSS.escape(omega.primitive)}"]`,
      );
      expect(circle?.getAttribute('fill')).toBe(KIND_COLOR.emergent_omega);
    }
  });

  it('accepts custom width and height and respects them on the SVG', () => {
    const { getByTestId } = render(<Notation2DView width={400} height={300} />);
    const svg = getByTestId('notation-2d-view-svg');
    expect(svg.getAttribute('width')).toBe('400');
    expect(svg.getAttribute('height')).toBe('300');
  });
});
