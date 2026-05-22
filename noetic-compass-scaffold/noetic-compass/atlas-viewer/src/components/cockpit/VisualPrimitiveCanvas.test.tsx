import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import {
  VisualPrimitiveCanvas,
  type VisualPrimitive,
} from './VisualPrimitiveCanvas';

let host: HTMLDivElement;
let root: Root;

beforeEach(() => {
  host = document.createElement('div');
  document.body.appendChild(host);
  root = createRoot(host);
});

afterEach(() => {
  act(() => {
    root.unmount();
  });
  host.remove();
});

const samplePrimitives: VisualPrimitive[] = [
  {
    id: 'p1',
    kind: 'point',
    coords_norm: [0.5, 0.5],
    cas_axis: 'Noetic',
    cas_label: '^1^C',
    label: 'Mind cluster',
    explanation: 'Attention spike at center.',
    evidence_ref: { trace_id: 'tr-1' },
  },
  {
    id: 'b1',
    kind: 'box',
    coords_norm: [0.1, 0.1, 0.2, 0.2],
    cas_axis: 'Drive',
    label: 'Drive box',
    evidence_ref: { trace_id: 'tr-2' },
  },
  {
    id: 'l1',
    kind: 'polyline',
    coords_norm: [0.2, 0.8, 0.4, 0.6, 0.6, 0.7],
    cas_axis: 'Register',
    label: 'Trace path',
  },
  {
    id: 'r1',
    kind: 'region',
    coords_norm: [0.7, 0.7, 0.9, 0.7, 0.9, 0.9, 0.7, 0.9],
    cas_axis: 'Domain',
    label: 'Inversion region',
  },
];

function render(node: React.ReactNode): void {
  act(() => {
    root.render(node);
  });
}

describe('VisualPrimitiveCanvas — image rendering', () => {
  it('renders the image with src and aria-label as alt', () => {
    render(
      <VisualPrimitiveCanvas
        imageUrl="/fixtures/spatial.png"
        imageWidth={400}
        imageHeight={200}
        primitives={[]}
        ariaLabel="Spatial Evidence Layer demo"
      />,
    );
    const img = host.querySelector('img');
    expect(img).not.toBeNull();
    expect(img?.getAttribute('src')).toBe('/fixtures/spatial.png');
    expect(img?.getAttribute('alt')).toBe('Spatial Evidence Layer demo');
  });

  it('renders one primitive of each kind without crashing', () => {
    render(
      <VisualPrimitiveCanvas
        imageUrl="/x.png"
        imageWidth={400}
        imageHeight={200}
        primitives={samplePrimitives}
      />,
    );
    expect(host.querySelector('[data-kind="point"]')).not.toBeNull();
    expect(host.querySelector('[data-kind="box"]')).not.toBeNull();
    expect(host.querySelector('[data-kind="polyline"]')).not.toBeNull();
    expect(host.querySelector('[data-kind="region"]')).not.toBeNull();
  });
});

describe('VisualPrimitiveCanvas — interaction', () => {
  // React's synthetic event system delegates at the root and listens for
  // native `mouseover` / `mouseout` (which DO bubble in jsdom), then
  // synthesizes `onMouseEnter` / `onMouseLeave` from them. Native
  // `mouseenter` / `mouseleave` do not bubble and React's delegation never
  // picks them up in jsdom — so the tests below dispatch `mouseover` /
  // `mouseout` instead. Coordinate math also needs a non-zero container
  // rect, hence the getBoundingClientRect mock.
  it('calls onPrimitiveHover with the primitive on mouse enter', () => {
    const onHover = vi.fn();
    render(
      <VisualPrimitiveCanvas
        imageUrl="/x.png"
        imageWidth={400}
        imageHeight={200}
        primitives={samplePrimitives}
        onPrimitiveHover={onHover}
      />,
    );
    const node = host.querySelector('[data-primitive-id="p1"]') as SVGElement;
    expect(node).not.toBeNull();
    act(() => {
      node.dispatchEvent(
        new MouseEvent('mouseover', { bubbles: true, clientX: 10, clientY: 10 }),
      );
    });
    expect(onHover).toHaveBeenCalled();
    expect(onHover.mock.calls[0][0]).toMatchObject({ id: 'p1' });
  });

  it('shows tooltip text including the colloquialism on hover', () => {
    render(
      <VisualPrimitiveCanvas
        imageUrl="/x.png"
        imageWidth={400}
        imageHeight={200}
        primitives={samplePrimitives}
      />,
    );
    const container = host.querySelector(
      '[data-testid="visual-primitive-canvas"]',
    ) as HTMLElement;
    // Realistic rect so tooltip coord math (evt.clientX - rect.left) is sane.
    container.getBoundingClientRect = () =>
      ({ left: 0, top: 0, right: 400, bottom: 200, width: 400, height: 200, x: 0, y: 0, toJSON: () => ({}) }) as DOMRect;
    const node = host.querySelector('[data-primitive-id="p1"]') as SVGElement;
    act(() => {
      node.dispatchEvent(
        new MouseEvent('mouseover', { bubbles: true, clientX: 10, clientY: 10 }),
      );
    });
    const tooltip = host.querySelector('[data-testid="vpc-tooltip"]');
    expect(tooltip).not.toBeNull();
    const text = tooltip?.textContent ?? '';
    expect(text).toContain('Mind cluster');
    expect(text).toContain('Paying attention.');
  });

  it('clears tooltip and fires hover(null) on mouse leave', () => {
    const onHover = vi.fn();
    render(
      <VisualPrimitiveCanvas
        imageUrl="/x.png"
        imageWidth={400}
        imageHeight={200}
        primitives={samplePrimitives}
        onPrimitiveHover={onHover}
      />,
    );
    const node = host.querySelector('[data-primitive-id="p1"]') as SVGElement;
    act(() => {
      node.dispatchEvent(
        new MouseEvent('mouseover', { bubbles: true, clientX: 10, clientY: 10 }),
      );
    });
    // React's synthetic onMouseLeave is driven by native `mouseout` whose
    // relatedTarget is outside the bound element. Setting relatedTarget to
    // an outside node (host) makes React fire onMouseLeave.
    act(() => {
      const evt = new MouseEvent('mouseout', { bubbles: true });
      Object.defineProperty(evt, 'relatedTarget', { value: document.body });
      node.dispatchEvent(evt);
    });
    expect(host.querySelector('[data-testid="vpc-tooltip"]')).toBeNull();
    expect(onHover).toHaveBeenLastCalledWith(null);
  });

  it('calls onPrimitiveClick with primitive and its evidence_ref', () => {
    const onClick = vi.fn();
    render(
      <VisualPrimitiveCanvas
        imageUrl="/x.png"
        imageWidth={400}
        imageHeight={200}
        primitives={samplePrimitives}
        onPrimitiveClick={onClick}
      />,
    );
    const node = host.querySelector('[data-primitive-id="b1"]') as SVGElement;
    act(() => {
      node.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    expect(onClick).toHaveBeenCalledTimes(1);
    expect(onClick.mock.calls[0][0]).toMatchObject({ id: 'b1' });
    expect(onClick.mock.calls[0][1]).toEqual({ trace_id: 'tr-2' });
  });
});

describe('VisualPrimitiveCanvas — highlight', () => {
  it('applies active highlight styling to primitives in activeStepPrimitiveIds', () => {
    render(
      <VisualPrimitiveCanvas
        imageUrl="/x.png"
        imageWidth={400}
        imageHeight={200}
        primitives={samplePrimitives}
        activeStepPrimitiveIds={['p1', 'l1']}
      />,
    );
    const active1 = host.querySelector('[data-primitive-id="p1"]');
    const active2 = host.querySelector('[data-primitive-id="l1"]');
    const inactive = host.querySelector('[data-primitive-id="b1"]');
    expect(active1?.getAttribute('data-active')).toBe('true');
    expect(active2?.getAttribute('data-active')).toBe('true');
    expect(inactive?.getAttribute('data-active')).toBe('false');
    expect(active1?.getAttribute('filter')).toBe('url(#vpc-halo)');
    expect(active1?.getAttribute('stroke-width')).toBe('4');
    expect(inactive?.getAttribute('stroke-width')).toBe('2');
  });
});

describe('VisualPrimitiveCanvas — accessibility', () => {
  it('exposes per-primitive aria-label and is keyboard focusable', () => {
    render(
      <VisualPrimitiveCanvas
        imageUrl="/x.png"
        imageWidth={400}
        imageHeight={200}
        primitives={samplePrimitives}
      />,
    );
    const node = host.querySelector('[data-primitive-id="p1"]');
    expect(node?.getAttribute('aria-label')).toBe('Mind cluster');
    expect(node?.getAttribute('tabindex')).toBe('0');
    expect(node?.getAttribute('role')).toBe('button');
  });

  it('triggers click handler via Enter key', () => {
    const onClick = vi.fn();
    render(
      <VisualPrimitiveCanvas
        imageUrl="/x.png"
        imageWidth={400}
        imageHeight={200}
        primitives={samplePrimitives}
        onPrimitiveClick={onClick}
      />,
    );
    const node = host.querySelector('[data-primitive-id="p1"]') as SVGElement;
    act(() => {
      node.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }),
      );
    });
    expect(onClick).toHaveBeenCalledTimes(1);
    expect(onClick.mock.calls[0][0]).toMatchObject({ id: 'p1' });
  });
});
