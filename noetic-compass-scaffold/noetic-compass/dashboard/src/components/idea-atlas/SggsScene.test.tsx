/**
 * Tests for SggsScene — Three.js 3D viewer for the Atlas Thought Tree.
 *
 * jsdom has no WebGL, so a `MinimalWebGLRenderer` stub is injected via
 * the `rendererFactory` prop. The stub satisfies the surface SggsScene
 * actually calls (`setSize`, `setClearColor`, `setPixelRatio`, `render`,
 * `dispose`, `domElement`) without touching a GPU.
 *
 * Tests cover:
 * - Mount: component creates a canvas without throwing.
 * - Mesh count: scene contains N node meshes by `userData['data-node-id']`.
 * - Click: `simulateNodeClick(wrapper, id)` fires `onNodeClick` with the
 *   expected node (verifies the test-hook event path the scene exposes).
 * - Selection: changing `selectedNodeId` lerps the body material color to
 *   the selection accent and toggles the outline visibility.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/react';
import { Color } from 'three';
import type { Scene } from 'three';
import {
  SggsScene,
  simulateCubeDrag,
  simulateNodeClick,
  type MinimalWebGLRenderer,
} from './SggsScene';
import type {
  AtlasTraceThoughtTree,
  ThoughtTreeNode,
  ThoughtTreeEdge,
  ThoughtTreeRootNode,
} from '../../lib/trace';
import { SELECTED_STROKE_HEX } from '../../lib/sggs_palette';

// ── Test data builders ──────────────────────────────────────────────────

function node(
  id: string,
  kind: string,
  label: string,
  role: string = '',
  children?: ThoughtTreeRootNode[],
): ThoughtTreeRootNode {
  return {
    id,
    node_key: `${kind}|${role}|${label.toLowerCase()}|`,
    kind,
    role,
    label,
    normalized_label: label.toLowerCase(),
    children,
  };
}

function edge(id: string, source: string, target: string): ThoughtTreeEdge {
  return {
    id,
    edge_key: `${source}->${target}`,
    source,
    target,
    source_key: source,
    target_key: target,
    kind: 'parent_child',
  };
}

function makeSampleTree(): AtlasTraceThoughtTree {
  const ident1 = node('n2', 'identifier_attempt', 'stageA0_4_857', 'copied');
  const ident2 = node('n3', 'identifier_attempt', 'stageD3_4_857', 'missed');
  const slot = node('n4', 'slot_pattern', 'recognized 1 position', 'summary');
  const conf = node('n5', 'confidence_marker', 'coverage: weak', 'weak');
  const gen = node('n1', 'model_generation', 'stub answer', 'output', [
    ident1,
    ident2,
    slot,
    conf,
  ]);
  const root = node('n0', 'user_prompt', '^7^P_{F5}', 'input', [gen]);
  // Flat array drops `children` to match traceability_v0 shape.
  const flat: ThoughtTreeNode[] = [root, gen, ident1, ident2, slot, conf].map(
    (n) => ({
      id: n.id!,
      node_key: n.node_key!,
      kind: n.kind,
      role: n.role,
      label: n.label,
      normalized_label: n.normalized_label,
    }),
  );
  const edges: ThoughtTreeEdge[] = [
    edge('e0', 'n0', 'n1'),
    edge('e1', 'n1', 'n2'),
    edge('e2', 'n1', 'n3'),
    edge('e3', 'n1', 'n4'),
    edge('e4', 'n1', 'n5'),
  ];
  return {
    root,
    nodes: flat,
    edges,
    node_count: flat.length,
    edge_count: edges.length,
  };
}

// ── Renderer stub — JSDOM-safe ──────────────────────────────────────────

function makeRendererStub(): MinimalWebGLRenderer {
  const canvas = document.createElement('canvas');
  // Sized so tests that read `boundingClientRect` get a non-zero box.
  canvas.width = 600;
  canvas.height = 400;
  return {
    domElement: canvas,
    setPixelRatio: vi.fn(),
    setSize: vi.fn(),
    setClearColor: vi.fn(),
    render: vi.fn(),
    dispose: vi.fn(),
  };
}

// Test surface exposed by SggsScene when `rendererFactory` is provided.
interface TestSurface {
  __sggs_scene?: Scene;
  __sggs_step?: () => void;
  __sggs_meshes?: Array<{
    group: { rotation: { x: number; y: number } };
    body: {
      geometry: {
        type?: string;
        parameters?: { width?: number; height?: number; depth?: number };
      };
    };
    hasUserRotation: boolean;
    faceGlows: Array<{
      scale: { x: number };
      material: { opacity: number };
      userData: Record<string, unknown>;
    }>;
    facePanels: Array<{
      material: { opacity?: number };
      geometry: { parameters?: { width?: number; height?: number } };
      userData: Record<string, unknown>;
    }>;
  }>;
}

beforeEach(() => {
  // ResizeObserver isn't in jsdom; SggsScene observes its wrapper.
  if (!('ResizeObserver' in globalThis)) {
    (globalThis as unknown as { ResizeObserver: typeof ResizeObserver }).ResizeObserver =
      class {
        observe() {}
        unobserve() {}
        disconnect() {}
      } as unknown as typeof ResizeObserver;
  }
});

// ── Tests ───────────────────────────────────────────────────────────────

describe('SggsScene — mount', () => {
  it('mounts without throwing and creates a canvas in the wrapper', () => {
    const tree = makeSampleTree();
    const { container } = render(
      <SggsScene tree={tree} rendererFactory={makeRendererStub} />,
    );
    const wrapper = container.querySelector('[data-testid="sggs-scene"]');
    expect(wrapper).not.toBeNull();
    const canvas = wrapper!.querySelector('[data-testid="sggs-canvas"]');
    expect(canvas).not.toBeNull();
    expect((canvas as HTMLElement).tagName.toLowerCase()).toBe('canvas');
  });

  it('marks mount complete and surfaces node_count on the wrapper', () => {
    const tree = makeSampleTree();
    const { container } = render(
      <SggsScene tree={tree} rendererFactory={makeRendererStub} />,
    );
    const wrapper = container.querySelector('[data-testid="sggs-scene"]')!;
    expect(wrapper.getAttribute('data-mounted')).toBe('true');
    expect(wrapper.getAttribute('data-node-count')).toBe(String(tree.node_count));
  });
});

describe('SggsScene — scene composition', () => {
  it('scene contains N node meshes — counted by userData[data-node-id]', () => {
    const tree = makeSampleTree();
    const { container } = render(
      <SggsScene tree={tree} rendererFactory={makeRendererStub} />,
    );
    const wrapper = container.querySelector('[data-testid="sggs-scene"]') as
      | (HTMLElement & TestSurface)
      | null;
    expect(wrapper).not.toBeNull();
    const scene = wrapper!.__sggs_scene;
    expect(scene).toBeDefined();
    const seen = new Set<string>();
    scene!.traverse((obj) => {
      const id = (obj.userData as { 'data-node-id'?: string })?.['data-node-id'];
      // Only count `Group`-level entries (each card has one group), not
      // the per-mesh body/ribbon/outline that also carry data-node-id.
      if (id && (obj as { isGroup?: boolean }).isGroup) {
        seen.add(id);
      }
    });
    expect(seen.size).toBe(tree.node_count);
    for (const n of tree.nodes) {
      expect(seen.has(n.id)).toBe(true);
    }
  });

  it('scene contains one Line per edge', () => {
    const tree = makeSampleTree();
    const { container } = render(
      <SggsScene tree={tree} rendererFactory={makeRendererStub} />,
    );
    const wrapper = container.querySelector('[data-testid="sggs-scene"]') as
      | (HTMLElement & TestSurface)
      | null;
    const scene = wrapper!.__sggs_scene!;
    let lineCount = 0;
    scene.traverse((obj) => {
      // `Line` is the parent class of `LineSegments` (used for outlines).
      // We want only edge lines, which carry `data-edge-id`.
      const eid = (obj.userData as { 'data-edge-id'?: string })?.['data-edge-id'];
      if (eid) lineCount += 1;
    });
    expect(lineCount).toBe(tree.edge_count);
  });

  it('renders each node as an inspectable square cube body', () => {
    const tree = makeSampleTree();
    const { container } = render(
      <SggsScene tree={tree} rendererFactory={makeRendererStub} />,
    );
    const wrapper = container.querySelector('[data-testid="sggs-scene"]') as
      | (HTMLElement & TestSurface)
      | null;
    expect(wrapper!.__sggs_meshes).toBeDefined();
    for (const bundle of wrapper!.__sggs_meshes!) {
      expect(bundle.body.geometry.type).toBe('BoxGeometry');
      const params = bundle.body.geometry.parameters!;
      expect(params.width).toBeCloseTo(params.height!);
      expect(params.width).toBeCloseTo(params.depth!);
    }
  });

  it('adds six information faces to every cube', () => {
    const tree = makeSampleTree();
    const { container } = render(
      <SggsScene tree={tree} rendererFactory={makeRendererStub} />,
    );
    const wrapper = container.querySelector('[data-testid="sggs-scene"]') as
      | (HTMLElement & TestSurface)
      | null;
    const expectedFaces = ['front', 'right', 'back', 'left', 'top', 'bottom'];
    for (const bundle of wrapper!.__sggs_meshes!) {
      expect(bundle.facePanels).toHaveLength(6);
      const faces = bundle.facePanels.map((panel) => panel.userData.face);
      expect(faces).toEqual(expectedFaces);
      for (const panel of bundle.facePanels) {
        const params = panel.geometry.parameters!;
        expect(params.width).toBeCloseTo(params.height!);
      }
    }
  });

  it('adds six radiant glow layers behind every cube face', () => {
    const tree = makeSampleTree();
    const { container } = render(
      <SggsScene tree={tree} rendererFactory={makeRendererStub} />,
    );
    const wrapper = container.querySelector('[data-testid="sggs-scene"]') as
      | (HTMLElement & TestSurface)
      | null;
    const expectedFaces = ['front', 'right', 'back', 'left', 'top', 'bottom'];
    for (const bundle of wrapper!.__sggs_meshes!) {
      expect(bundle.faceGlows).toHaveLength(6);
      expect(bundle.faceGlows.map((glow) => glow.userData.face)).toEqual(
        expectedFaces,
      );
      for (const panel of bundle.facePanels) {
        expect(panel.material.opacity).toBe(1);
      }
    }
  });
});

describe('SggsScene — click → onNodeClick', () => {
  it('simulateNodeClick(wrapper, id) calls onNodeClick with the matching node', () => {
    const tree = makeSampleTree();
    const onNodeClick = vi.fn();
    const { container } = render(
      <SggsScene
        tree={tree}
        onNodeClick={onNodeClick}
        rendererFactory={makeRendererStub}
      />,
    );
    const wrapper = container.querySelector(
      '[data-testid="sggs-scene"]',
    ) as HTMLElement;
    // n2 = first identifier_attempt; matches ThoughtTreeView's click test.
    simulateNodeClick(wrapper, 'n2');
    expect(onNodeClick).toHaveBeenCalledTimes(1);
    const arg = onNodeClick.mock.calls[0][0] as ThoughtTreeNode;
    expect(arg.id).toBe('n2');
    expect(arg.kind).toBe('identifier_attempt');
  });

  it('simulateNodeClick with an unknown id is a no-op', () => {
    const tree = makeSampleTree();
    const onNodeClick = vi.fn();
    const { container } = render(
      <SggsScene
        tree={tree}
        onNodeClick={onNodeClick}
        rendererFactory={makeRendererStub}
      />,
    );
    const wrapper = container.querySelector(
      '[data-testid="sggs-scene"]',
    ) as HTMLElement;
    simulateNodeClick(wrapper, 'does-not-exist');
    expect(onNodeClick).not.toHaveBeenCalled();
  });
});

describe('SggsScene — per-cube rotation', () => {
  it('dragging a cube rotates that cube without rotating its siblings', () => {
    const tree = makeSampleTree();
    const { container } = render(
      <SggsScene tree={tree} rendererFactory={makeRendererStub} />,
    );
    const wrapper = container.querySelector('[data-testid="sggs-scene"]') as
      | (HTMLElement & TestSurface)
      | null;
    const meshes = wrapper!.__sggs_meshes!;
    const target = meshes[0];
    const sibling = meshes[1];
    const beforeTargetX = target.group.rotation.x;
    const beforeTargetY = target.group.rotation.y;
    const beforeSiblingX = sibling.group.rotation.x;
    const beforeSiblingY = sibling.group.rotation.y;

    simulateCubeDrag(wrapper!, target.facePanels[0].userData['data-node-id'] as string, 120, -80);

    expect(target.hasUserRotation).toBe(true);
    expect(target.group.rotation.x).not.toBeCloseTo(beforeTargetX);
    expect(target.group.rotation.y).not.toBeCloseTo(beforeTargetY);
    expect(sibling.group.rotation.x).toBeCloseTo(beforeSiblingX);
    expect(sibling.group.rotation.y).toBeCloseTo(beforeSiblingY);
  });
});

describe('SggsScene — selectedNodeId visual state', () => {
  it('selected node body color stays at its baseFill (no washout)', () => {
    // REGRESSION PIN (user feedback 2026-05-13): "when the box is
    // highlighted it turns grayish and the grayishness hides the
    // white lettering." Fix is to leave body color at the palette
    // baseFill and signal selection via face glow + outline instead.
    const tree = makeSampleTree();
    const { container, rerender } = render(
      <SggsScene
        tree={tree}
        selectedNodeId={null}
        rendererFactory={makeRendererStub}
      />,
    );
    const wrapper = container.querySelector('[data-testid="sggs-scene"]') as
      | (HTMLElement & TestSurface)
      | null;
    rerender(
      <SggsScene
        tree={tree}
        selectedNodeId="n3"
        rendererFactory={makeRendererStub}
      />,
    );
    wrapper!.__sggs_step!();
    const scene = wrapper!.__sggs_scene!;
    const accent = new Color(SELECTED_STROKE_HEX);
    let bodyColorMatchesAccent = false;
    scene.traverse((obj) => {
      const role = (obj.userData as { role?: string })?.role;
      const id = (obj.userData as { 'data-node-id'?: string })?.[
        'data-node-id'
      ];
      if (role === 'body' && id === 'n3') {
        const mat = (obj as unknown as { material: { color: Color } }).material;
        const dr = Math.abs(mat.color.r - accent.r);
        const dg = Math.abs(mat.color.g - accent.g);
        const db = Math.abs(mat.color.b - accent.b);
        bodyColorMatchesAccent = dr < 1e-3 && dg < 1e-3 && db < 1e-3;
      }
    });
    // Body should NOT have lerp'd to the accent — that was the
    // grayish-washout bug. White card text must stay readable.
    expect(bodyColorMatchesAccent).toBe(false);
  });

  it('selected node glows on all six sides without washing out faces', () => {
    // REGRESSION PIN (user feedback 2026-05-13): "the highlighted one
    // should glow and pulsate." The glow should wrap all six sides,
    // while the face panels remain opaque enough to keep text readable.
    const tree = makeSampleTree();
    const { container, rerender } = render(
      <SggsScene
        tree={tree}
        selectedNodeId={null}
        rendererFactory={makeRendererStub}
      />,
    );
    const wrapper = container.querySelector('[data-testid="sggs-scene"]') as
      | (HTMLElement & TestSurface)
      | null;
    rerender(
      <SggsScene
        tree={tree}
        selectedNodeId="n3"
        rendererFactory={makeRendererStub}
      />,
    );
    wrapper!.__sggs_step!();
    const selected = wrapper!.__sggs_meshes!.find(
      (m) => m.faceGlows[0].userData['data-node-id'] === 'n3',
    )!;
    expect(selected.faceGlows).toHaveLength(6);
    for (const glow of selected.faceGlows) {
      expect(glow.material.opacity).toBeGreaterThan(0.2);
      expect(glow.scale.x).toBeGreaterThan(1.0);
    }
    for (const panel of selected.facePanels) {
      expect(panel.material.opacity).toBe(1);
    }
  });

  it('shows the outline only on the selected mesh', () => {
    const tree = makeSampleTree();
    const { container, rerender } = render(
      <SggsScene
        tree={tree}
        selectedNodeId={null}
        rendererFactory={makeRendererStub}
      />,
    );
    const wrapper = container.querySelector('[data-testid="sggs-scene"]') as
      | (HTMLElement & TestSurface)
      | null;
    rerender(
      <SggsScene
        tree={tree}
        selectedNodeId="n4"
        rendererFactory={makeRendererStub}
      />,
    );
    wrapper!.__sggs_step!();
    const scene = wrapper!.__sggs_scene!;
    let visibleOutlineIds: string[] = [];
    scene.traverse((obj) => {
      const role = (obj.userData as { role?: string })?.role;
      const id = (obj.userData as { 'data-node-id'?: string })?.[
        'data-node-id'
      ];
      if (role === 'outline' && (obj as { visible: boolean }).visible && id) {
        visibleOutlineIds.push(id);
      }
    });
    expect(visibleOutlineIds).toEqual(['n4']);
  });
});

describe('SggsScene — empty tree', () => {
  it('does not crash when given an empty thought tree', () => {
    const empty: AtlasTraceThoughtTree = {
      root: {} as ThoughtTreeRootNode,
      nodes: [],
      edges: [],
      node_count: 0,
      edge_count: 0,
    };
    const { container } = render(
      <SggsScene tree={empty} rendererFactory={makeRendererStub} />,
    );
    const wrapper = container.querySelector('[data-testid="sggs-scene"]');
    expect(wrapper).not.toBeNull();
    expect(wrapper!.getAttribute('data-node-count')).toBe('0');
  });
});
