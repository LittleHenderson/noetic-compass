/**
 * Tests for NeuralNetScene — Three.js viewer for Pythia-160M.
 *
 * jsdom has no WebGL, so a `MinimalWebGLRenderer` stub is injected via
 * `rendererFactory`. A `MinimalRaycaster` stub is injected via
 * `raycasterFactory` so we can deterministically simulate hits without
 * a working camera projection inside jsdom.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/react';
import type { InstancedMesh, Object3D, Scene } from 'three';
import {
  NeuralNetScene,
  type MinimalRaycaster,
  type MinimalWebGLRenderer,
  type NeuronCoord,
  type PerTokenFrame,
} from './NeuralNetScene';
import { PYTHIA_160M_PRESET } from '../../lib/modelArchitecture';

function makeRendererStub(): MinimalWebGLRenderer {
  const canvas = document.createElement('canvas');
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

function makeRaycasterStub(
  hits: Array<{ object: Object3D; instanceId?: number; distance: number }> = [],
): MinimalRaycaster {
  return {
    setFromCamera: vi.fn(),
    intersectObject: vi.fn(() => hits),
  };
}

interface TestSurface {
  __nn_scene?: Scene;
  __nn_layers?: InstancedMesh[];
  __nn_simulate_hover?: (x: number, y: number) => void;
  __nn_simulate_leave?: () => void;
  __nn_simulate_click?: (x: number, y: number) => void;
}

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

describe('NeuralNetScene — mount', () => {
  it('mounts without throwing given PYTHIA_160M_PRESET and no frame', () => {
    const { container } = render(
      <NeuralNetScene
        architecture={PYTHIA_160M_PRESET}
        rendererFactory={makeRendererStub}
        raycasterFactory={() => makeRaycasterStub()}
      />,
    );
    const wrapper = container.querySelector('[data-testid="neuralnet-scene"]');
    expect(wrapper).not.toBeNull();
    expect(wrapper!.getAttribute('data-mounted')).toBe('true');
    const canvas = wrapper!.querySelector('[data-testid="neuralnet-canvas"]');
    expect(canvas).not.toBeNull();
    expect((canvas as HTMLElement).tagName.toLowerCase()).toBe('canvas');
  });

  it('builds 12 instanced layers each carrying Pythia mlp dim', () => {
    const { container } = render(
      <NeuralNetScene
        architecture={PYTHIA_160M_PRESET}
        rendererFactory={makeRendererStub}
        raycasterFactory={() => makeRaycasterStub()}
      />,
    );
    const wrapper = container.querySelector(
      '[data-testid="neuralnet-scene"]',
    ) as (HTMLElement & TestSurface) | null;
    expect(wrapper!.__nn_layers).toHaveLength(12);
    for (const inst of wrapper!.__nn_layers!) {
      expect(inst.count).toBe(3072);
    }
  });

  it('emits a console warning when given a non-Pythia arch but still mounts', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const { container } = render(
      <NeuralNetScene
        architecture={{
          family: 'llama',
          n_layers: 32,
          hidden_size: 4096,
          mlp_intermediate_dim: 14336,
          n_heads: 32,
          total_params: 8_000_000_000,
          validated: false,
        }}
        rendererFactory={makeRendererStub}
        raycasterFactory={() => makeRaycasterStub()}
      />,
    );
    expect(warn).toHaveBeenCalled();
    const wrapper = container.querySelector('[data-testid="neuralnet-scene"]');
    expect(wrapper!.getAttribute('data-mounted')).toBe('true');
    warn.mockRestore();
  });
});

describe('NeuralNetScene — cleanup', () => {
  it('calls renderer.dispose on unmount', () => {
    const stub = makeRendererStub();
    const { unmount } = render(
      <NeuralNetScene
        architecture={PYTHIA_160M_PRESET}
        rendererFactory={() => stub}
        raycasterFactory={() => makeRaycasterStub()}
      />,
    );
    expect(stub.dispose).not.toHaveBeenCalled();
    unmount();
    expect(stub.dispose).toHaveBeenCalledTimes(1);
  });

  it('removes the canvas from the DOM on unmount', () => {
    const { container, unmount } = render(
      <NeuralNetScene
        architecture={PYTHIA_160M_PRESET}
        rendererFactory={makeRendererStub}
        raycasterFactory={() => makeRaycasterStub()}
      />,
    );
    expect(container.querySelector('[data-testid="neuralnet-canvas"]')).not.toBeNull();
    unmount();
    expect(container.querySelector('[data-testid="neuralnet-canvas"]')).toBeNull();
  });
});

describe('NeuralNetScene — hover & click', () => {
  it('fires onNeuronHover with a NeuronCoord when raycast hits an instance', () => {
    const onHover = vi.fn();
    // Stub raycaster that "hits" the first layer's instance #42.
    const raycaster = makeRaycasterStub();
    const { container } = render(
      <NeuralNetScene
        architecture={PYTHIA_160M_PRESET}
        onNeuronHover={onHover}
        rendererFactory={makeRendererStub}
        raycasterFactory={() => raycaster}
      />,
    );
    const wrapper = container.querySelector(
      '[data-testid="neuralnet-scene"]',
    ) as (HTMLElement & TestSurface) | null;
    const firstLayer = wrapper!.__nn_layers![0];
    (raycaster.intersectObject as ReturnType<typeof vi.fn>).mockImplementation(
      (obj: Object3D) => {
        if (obj === firstLayer) {
          return [{ object: firstLayer, instanceId: 42, distance: 1 }];
        }
        return [];
      },
    );
    wrapper!.__nn_simulate_hover!(100, 100);
    expect(onHover).toHaveBeenCalledTimes(1);
    const coord = onHover.mock.calls[0][0] as NeuronCoord;
    expect(coord.layer).toBe(0);
    expect(coord.index).toBe(42);
    expect(coord.label).toBe('L0N42');
  });

  it('fires onNeuronHover(null) on pointer leave when previously hovered', () => {
    const onHover = vi.fn();
    const raycaster = makeRaycasterStub();
    const { container } = render(
      <NeuralNetScene
        architecture={PYTHIA_160M_PRESET}
        onNeuronHover={onHover}
        rendererFactory={makeRendererStub}
        raycasterFactory={() => raycaster}
      />,
    );
    const wrapper = container.querySelector(
      '[data-testid="neuralnet-scene"]',
    ) as (HTMLElement & TestSurface) | null;
    const firstLayer = wrapper!.__nn_layers![0];
    (raycaster.intersectObject as ReturnType<typeof vi.fn>).mockImplementation(
      (obj: Object3D) =>
        obj === firstLayer
          ? [{ object: firstLayer, instanceId: 7, distance: 1 }]
          : [],
    );
    wrapper!.__nn_simulate_hover!(50, 50);
    expect(onHover).toHaveBeenLastCalledWith(
      expect.objectContaining({ layer: 0, index: 7 }),
    );
    wrapper!.__nn_simulate_leave!();
    expect(onHover).toHaveBeenLastCalledWith(null);
  });

  it('fires onNeuronClick with the hit NeuronCoord', () => {
    const onClick = vi.fn();
    const raycaster = makeRaycasterStub();
    const { container } = render(
      <NeuralNetScene
        architecture={PYTHIA_160M_PRESET}
        onNeuronClick={onClick}
        rendererFactory={makeRendererStub}
        raycasterFactory={() => raycaster}
      />,
    );
    const wrapper = container.querySelector(
      '[data-testid="neuralnet-scene"]',
    ) as (HTMLElement & TestSurface) | null;
    const layers = wrapper!.__nn_layers!;
    // Hit on layer index 3, neuron 1234.
    (raycaster.intersectObject as ReturnType<typeof vi.fn>).mockImplementation(
      (obj: Object3D) =>
        obj === layers[3]
          ? [{ object: layers[3], instanceId: 1234, distance: 1 }]
          : [],
    );
    wrapper!.__nn_simulate_click!(120, 120);
    expect(onClick).toHaveBeenCalledTimes(1);
    expect(onClick).toHaveBeenCalledWith({
      layer: 3,
      index: 1234,
      label: 'L3N1234',
    });
  });
});

describe('NeuralNetScene — frame updates', () => {
  it('accepts a currentFrame prop update without throwing', () => {
    const frame: PerTokenFrame = {
      token_index: 0,
      token: 'The',
      top_activated_neurons: [
        { layer: 0, index: 142, activation: 0.81 },
        { layer: 5, index: 2648, activation: 0.71 },
      ],
      foundation_probe: [0.3, 0.18, 0.22, 0.4, 0.12, 0.5, 0.2],
    };
    const { container, rerender } = render(
      <NeuralNetScene
        architecture={PYTHIA_160M_PRESET}
        rendererFactory={makeRendererStub}
        raycasterFactory={() => makeRaycasterStub()}
      />,
    );
    rerender(
      <NeuralNetScene
        architecture={PYTHIA_160M_PRESET}
        currentFrame={frame}
        blindspotCoords={[{ layer: 5, index: 230, label: 'L5N230' }]}
        activeTraceCoords={[{ layer: 1, index: 142, label: 'L1N142' }]}
        selectedNeuron={{ layer: 5, index: 2648 }}
        rendererFactory={makeRendererStub}
        raycasterFactory={() => makeRaycasterStub()}
      />,
    );
    const wrapper = container.querySelector('[data-testid="neuralnet-scene"]');
    expect(wrapper!.getAttribute('data-mounted')).toBe('true');
  });
});

// TODO: full WebGL render assertions (per-instance color buffer values, plane
// stacking pixel-perfect spacing, OrbitControls drag) are out of scope for
// jsdom. Re-enable as integration tests under a real-browser harness when
// Playwright lands in the atlas-viewer test stack.
describe.skip('NeuralNetScene — WebGL render assertions (TODO playwright)', () => {
  it.skip('renders 36864 colored sphere instances in the canvas', () => {});
  it.skip('orbit controls drag rotates the camera', () => {});
});
