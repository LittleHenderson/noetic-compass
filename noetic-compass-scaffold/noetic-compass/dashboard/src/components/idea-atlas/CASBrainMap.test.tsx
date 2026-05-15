/**
 * Tests for CASBrainMap — Evidence Packet button wiring.
 *
 * Focus: the "Open Example Evidence" vs "Open Evidence" button label/title
 * toggles based on whether a real Mode 7 finalTraceId is supplied via the
 * `selectedTraceId` prop. The 3D Three.js scene is mocked just enough that
 * the React render commits without exploding in jsdom — we only assert on
 * the button surface.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import type {
  AtlasTraceThoughtTree,
  ThoughtTreeNode,
  ThoughtTreeRootNode,
} from '../../lib/trace';

// ── Three.js mocks ──────────────────────────────────────────────────────
// CASBrainMap calls `new WebGLRenderer({...})` directly inside a useEffect.
// jsdom has no WebGL context, so the real constructor throws. We replace it
// with a stub that exposes the surface CASBrainMap touches. OrbitControls is
// also stubbed since it attaches to renderer.domElement.

vi.mock('three', async () => {
  const actual = await vi.importActual<typeof import('three')>('three');
  class StubWebGLRenderer {
    domElement: HTMLCanvasElement;
    constructor() {
      this.domElement = document.createElement('canvas');
      this.domElement.width = 600;
      this.domElement.height = 400;
    }
    setPixelRatio() {}
    setSize() {}
    setClearColor() {}
    render() {}
    dispose() {}
  }
  return {
    ...actual,
    WebGLRenderer: StubWebGLRenderer,
  };
});

vi.mock('three/examples/jsm/controls/OrbitControls.js', () => {
  class StubOrbitControls {
    enableDamping = false;
    dampingFactor = 0;
    screenSpacePanning = false;
    minDistance = 0;
    maxDistance = 0;
    target = { x: 0, y: 0, z: 0, set: () => {} };
    update() {}
    dispose() {}
    addEventListener() {}
    removeEventListener() {}
  }
  return { OrbitControls: StubOrbitControls };
});

// ResizeObserver isn't in jsdom; the scene mount uses it.
beforeEach(() => {
  if (!('ResizeObserver' in globalThis)) {
    (globalThis as unknown as { ResizeObserver: typeof ResizeObserver }).ResizeObserver =
      class {
        observe() {}
        unobserve() {}
        disconnect() {}
      } as unknown as typeof ResizeObserver;
  }
});

import { CASBrainMap } from './CASBrainMap';

// ── Test data ───────────────────────────────────────────────────────────

function makeTree(): AtlasTraceThoughtTree {
  const root: ThoughtTreeRootNode = {
    id: 'n0',
    node_key: 'user_prompt|input|hello|',
    kind: 'user_prompt',
    role: 'input',
    label: 'hello',
    normalized_label: 'hello',
    children: [],
  };
  const flat: ThoughtTreeNode[] = [
    {
      id: 'n0',
      node_key: 'user_prompt|input|hello|',
      kind: 'user_prompt',
      role: 'input',
      label: 'hello',
      normalized_label: 'hello',
    },
  ];
  return {
    root,
    nodes: flat,
    edges: [],
    node_count: 1,
    edge_count: 0,
  };
}

// ── Tests ───────────────────────────────────────────────────────────────

describe('CASBrainMap — Open Evidence button wiring', () => {
  it('renders "Open Example Evidence" when selectedTraceId is absent', () => {
    render(<CASBrainMap tree={makeTree()} commits={[]} />);
    const btn = screen.getByTestId('cas-brain-open-evidence');
    expect(btn.textContent).toContain('Open Example Evidence');
    expect(btn.getAttribute('title')).toMatch(/EXAMPLE Evidence Packet/);
  });

  it('renders "Open Evidence" (without "Example") when selectedTraceId is set', () => {
    render(
      <CASBrainMap tree={makeTree()} commits={[]} selectedTraceId="abc123" />,
    );
    const btn = screen.getByTestId('cas-brain-open-evidence');
    const text = btn.textContent ?? '';
    expect(text).toContain('Open Evidence');
    expect(text).not.toContain('Example');
    expect(btn.getAttribute('title')).toMatch(/live trace_id from Mode 7 stream/);
  });
});
