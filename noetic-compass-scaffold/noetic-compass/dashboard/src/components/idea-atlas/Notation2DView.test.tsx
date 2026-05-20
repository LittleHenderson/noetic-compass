/**
 * Tests for `Notation2DView` — the direct end-to-end validation that the
 * canonical 169-primitive notation map feeds the dashboard UI.
 *
 * Count-agnostic by design: assertions about how many circles render
 * compare against `allPositions().length`, never a hardcoded number.
 */

import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render } from '@testing-library/react';

import canonicalLayout from '../../../../research/cas_probe/stage23_a_notation_2d_layout.json';
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

// ── Stage 23.A.1.2 polish: showLabels + filterKind ────────────────────

describe('Notation2DView — showLabels', () => {
  it('renders no <text> labels by default', () => {
    const { container } = render(<Notation2DView />);
    // The footer is a div; the SVG should contain no <text> elements.
    const svg = container.querySelector('svg');
    expect(svg).not.toBeNull();
    expect(svg!.querySelectorAll('text').length).toBe(0);
  });

  it('renders labels for Noetics and Domains only when showLabels=true', () => {
    const { container } = render(<Notation2DView showLabels />);
    const noeticCount = allPositions().filter((p) => p.kind === 'noetic').length;
    const domainCount = allPositions().filter((p) => p.kind === 'domain').length;
    const expectedLabelCount = noeticCount + domainCount;
    const svg = container.querySelector('svg');
    const labels = svg!.querySelectorAll('text');
    expect(labels.length).toBe(expectedLabelCount);
    // Every label text matches its primitive id.
    for (const p of allPositions().filter((q) =>
      ['noetic', 'domain'].includes(q.kind),
    )) {
      const label = container.querySelector(
        `[data-testid="notation-label-${CSS.escape(p.primitive)}"]`,
      );
      expect(label).not.toBeNull();
      expect(label?.textContent).toBe(p.primitive);
    }
  });

  it('labels respect filterKind: filtering to "drive" hides Noetic+Domain labels', () => {
    const { container } = render(<Notation2DView showLabels filterKind="drive" />);
    const svg = container.querySelector('svg');
    // Drive is neither Noetic nor Domain — auto-labels do not apply.
    expect(svg!.querySelectorAll('text').length).toBe(0);
  });
});

describe('Notation2DView — filterKind', () => {
  it('renders only primitives of the filtered kind', () => {
    const { container } = render(<Notation2DView filterKind="foundation" />);
    const foundationCount = allPositions().filter(
      (p) => p.kind === 'foundation',
    ).length;
    const circles = container.querySelectorAll('circle');
    expect(circles.length).toBe(foundationCount);
    for (const c of Array.from(circles)) {
      expect(c.getAttribute('data-kind')).toBe('foundation');
    }
  });

  it('footer shows "N of M primitives" when filtered', () => {
    const { getByTestId } = render(<Notation2DView filterKind="emergent_omega" />);
    const omegaCount = allPositions().filter((p) => p.kind === 'emergent_omega').length;
    const footer = getByTestId('notation-2d-footer');
    expect(footer.textContent).toContain(
      `${omegaCount} of ${allPositions().length} primitives`,
    );
    expect(footer.textContent).toContain('emergent_omega');
  });

  it('rendering with filterKind=rpm_pathway isolates the 22 RPM nodes', () => {
    const { container } = render(<Notation2DView filterKind="rpm_pathway" />);
    const circles = container.querySelectorAll('circle');
    const rpmCount = allPositions().filter((p) => p.kind === 'rpm_pathway').length;
    expect(circles.length).toBe(rpmCount);
    // And nothing else.
    for (const c of Array.from(circles)) {
      expect(c.getAttribute('data-kind')).toBe('rpm_pathway');
    }
  });
});
