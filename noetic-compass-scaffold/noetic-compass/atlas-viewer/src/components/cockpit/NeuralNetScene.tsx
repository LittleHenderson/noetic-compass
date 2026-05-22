import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
} from 'react';
import {
  AmbientLight,
  Color,
  DirectionalLight,
  DoubleSide,
  InstancedMesh,
  Mesh,
  MeshBasicMaterial,
  Object3D,
  PerspectiveCamera,
  PlaneGeometry,
  Raycaster,
  Scene,
  SphereGeometry,
  Vector2,
  WebGLRenderer,
} from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import type { ModelArchitecture } from '../../lib/modelArchitecture';
import {
  ATLAS_STATUS_COLORS,
  foundationColorForActivation,
  type DriveIndex,
} from '../../lib/atlasPalette';

export interface PerTokenFrameActivation {
  layer: number;
  index: number;
  activation: number;
}

export interface PerTokenFrame {
  token_index: number;
  token: string;
  top_activated_neurons: PerTokenFrameActivation[];
  foundation_probe?: number[];
}

export interface NeuronCoord {
  layer: number;
  index: number;
  label: string;
}

export interface MinimalWebGLRenderer {
  domElement: HTMLCanvasElement;
  setPixelRatio: (ratio: number) => void;
  setSize: (w: number, h: number) => void;
  setClearColor: (color: Color, alpha?: number) => void;
  render: (scene: Scene, camera: PerspectiveCamera) => void;
  dispose: () => void;
}

export interface MinimalRaycaster {
  setFromCamera: (coords: Vector2, camera: PerspectiveCamera) => void;
  intersectObject: (
    object: Object3D,
    recursive?: boolean,
  ) => Array<{ object: Object3D; instanceId?: number; distance: number }>;
}

export type ZoomLevelValue = 0 | 1 | 2 | 3 | 4 | 5;

export interface NeuralNetSceneProps {
  architecture: ModelArchitecture;
  currentFrame?: PerTokenFrame;
  selectedNeuron?: { layer: number; index: number };
  blindspotCoords?: NeuronCoord[];
  activeTraceCoords?: NeuronCoord[];
  /**
   * Camera zoom preset Z0..Z5. Mapped to (distance, target) via
   * ZOOM_DISTANCE_PRESETS per design doc §6. Default Z0 (whole-model wide view).
   */
  zoomLevel?: ZoomLevelValue;
  onNeuronHover?: (coord: NeuronCoord | null) => void;
  onNeuronClick?: (coord: NeuronCoord) => void;
  className?: string;
  rendererFactory?: () => MinimalWebGLRenderer;
  raycasterFactory?: () => MinimalRaycaster;
}

/**
 * Camera distance + orbit target per zoom preset, per atlas_viewer_neuralnet_scene_design §6.
 * Distance is the camera's distance from the origin along the line through (0, targetY, distance);
 * targetY is the OrbitControls target y (so look-at lines up with the layer plane centerline at y=5).
 */
export const ZOOM_DISTANCE_PRESETS: ReadonlyArray<{
  level: ZoomLevelValue;
  distance: number;
  targetY: number;
}> = [
  { level: 0, distance: 30, targetY: 5 }, // Z0 Whole model
  { level: 1, distance: 18, targetY: 5 }, // Z1 Layer
  { level: 2, distance: 12, targetY: 5 }, // Z2 Attention block
  { level: 3, distance: 8, targetY: 5 }, // Z3 Component group
  { level: 4, distance: 5, targetY: 5 }, // Z4 Sparse cover cluster
  { level: 5, distance: 3, targetY: 5 }, // Z5 Individual neuron
];

const ZOOM_TWEEN_DURATION_MS = 250;

function easeOutCubic(t: number): number {
  const u = 1 - t;
  return 1 - u * u * u;
}

const GRID_COLS = 64;
const GRID_ROWS = 48;
const NEURONS_PER_LAYER = GRID_COLS * GRID_ROWS;
const NEURON_SPACING = 0.18;
const NEURON_RADIUS = 0.06;
const LAYER_Z_SPACING = 2;
const PLANE_PADDING = 0.5;
const PYTHIA_N_LAYERS = 12;

const DIM_COLOR = new Color('#2a2a3a');
const PLANE_COLOR = new Color('#0f172a');
const SCENE_BG = new Color('#05070d');

function dominantDrive(probe: number[] | undefined): DriveIndex {
  if (!probe || probe.length === 0) return 1;
  let best = 0;
  let bestVal = -Infinity;
  for (let i = 0; i < Math.min(probe.length, 7); i++) {
    if (probe[i] > bestVal) {
      bestVal = probe[i];
      best = i;
    }
  }
  return (best + 1) as DriveIndex;
}

function neuronLocalPosition(index: number): { x: number; y: number } {
  const col = index % GRID_COLS;
  const row = Math.floor(index / GRID_COLS);
  const x = (col - (GRID_COLS - 1) / 2) * NEURON_SPACING;
  const y = ((GRID_ROWS - 1) / 2 - row) * NEURON_SPACING;
  return { x, y };
}

function buildLabel(layer: number, index: number): string {
  return `L${layer}N${index}`;
}

export function NeuralNetScene({
  architecture,
  currentFrame,
  selectedNeuron,
  blindspotCoords,
  activeTraceCoords,
  zoomLevel = 0,
  onNeuronHover,
  onNeuronClick,
  className,
  rendererFactory,
  raycasterFactory,
}: NeuralNetSceneProps) {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<Scene | null>(null);
  const cameraRef = useRef<PerspectiveCamera | null>(null);
  const rendererRef = useRef<MinimalWebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const layerMeshesRef = useRef<InstancedMesh[]>([]);
  const planeMeshesRef = useRef<Mesh[]>([]);
  const rafRef = useRef<number | null>(null);
  const zoomTweenRafRef = useRef<number | null>(null);
  const raycasterRef = useRef<MinimalRaycaster | null>(null);
  const onHoverRef = useRef(onNeuronHover);
  const onClickRef = useRef(onNeuronClick);
  const hoveredRef = useRef<NeuronCoord | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    onHoverRef.current = onNeuronHover;
  }, [onNeuronHover]);
  useEffect(() => {
    onClickRef.current = onNeuronClick;
  }, [onNeuronClick]);

  const archMismatch =
    architecture.family !== 'pythia' ||
    architecture.n_layers !== PYTHIA_N_LAYERS ||
    architecture.mlp_intermediate_dim !== NEURONS_PER_LAYER;

  if (archMismatch && typeof console !== 'undefined') {
    console.warn(
      `NeuralNetScene v0.0 is hardcoded to Pythia-160M (12 layers x 3072 neurons). ` +
        `Got family=${architecture.family} layers=${architecture.n_layers} ` +
        `mlp=${architecture.mlp_intermediate_dim}. Rendering with hardcoded grid anyway.`,
    );
  }

  useEffect(() => {
    const wrapper = wrapperRef.current;
    if (!wrapper) return;

    const width = Math.max(wrapper.clientWidth, 1);
    const height = Math.max(wrapper.clientHeight, 1);

    const scene = new Scene();
    scene.background = SCENE_BG.clone();

    const camera = new PerspectiveCamera(50, width / height, 0.1, 200);
    camera.position.set(0, 5, 30);
    camera.lookAt(0, 0, 0);

    const renderer: MinimalWebGLRenderer = rendererFactory
      ? rendererFactory()
      : new WebGLRenderer({ antialias: true, alpha: false });
    renderer.setPixelRatio(typeof window === 'undefined' ? 1 : window.devicePixelRatio || 1);
    renderer.setSize(width, height);
    renderer.setClearColor(SCENE_BG.clone(), 1);

    wrapper.appendChild(renderer.domElement);
    renderer.domElement.setAttribute('data-testid', 'neuralnet-canvas');

    const ambient = new AmbientLight(0xffffff, 0.7);
    scene.add(ambient);
    const dir = new DirectionalLight(0xffffff, 0.5);
    dir.position.set(2, 3, 8);
    scene.add(dir);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    // minDistance must be <= Z5 preset distance (3) so OrbitControls does not
    // silently clamp the camera back toward 4 after controls.update().
    controls.minDistance = 3;
    controls.maxDistance = 50;
    controls.target.set(0, 0, 0);

    const planeWidth = GRID_COLS * NEURON_SPACING + PLANE_PADDING;
    const planeHeight = GRID_ROWS * NEURON_SPACING + PLANE_PADDING;
    const zStart = ((PYTHIA_N_LAYERS - 1) / 2) * LAYER_Z_SPACING;

    const sphereGeom = new SphereGeometry(NEURON_RADIUS, 6, 6);
    const dummy = new Object3D();

    const layerMeshes: InstancedMesh[] = [];
    const planeMeshes: Mesh[] = [];

    for (let layer = 0; layer < PYTHIA_N_LAYERS; layer++) {
      const z = zStart - layer * LAYER_Z_SPACING;

      const planeGeom = new PlaneGeometry(planeWidth, planeHeight);
      const planeMat = new MeshBasicMaterial({
        color: PLANE_COLOR.clone(),
        transparent: true,
        opacity: 0.18,
        side: DoubleSide,
      });
      const planeMesh = new Mesh(planeGeom, planeMat);
      planeMesh.position.set(0, 0, z);
      planeMesh.userData = { kind: 'layer-plane', layer };
      scene.add(planeMesh);
      planeMeshes.push(planeMesh);

      const instMat = new MeshBasicMaterial();
      const inst = new InstancedMesh(sphereGeom, instMat, NEURONS_PER_LAYER);
      inst.userData = { kind: 'layer-neurons', layer };
      for (let i = 0; i < NEURONS_PER_LAYER; i++) {
        const { x, y } = neuronLocalPosition(i);
        dummy.position.set(x, y, z);
        dummy.updateMatrix();
        inst.setMatrixAt(i, dummy.matrix);
        inst.setColorAt(i, DIM_COLOR);
      }
      inst.instanceMatrix.needsUpdate = true;
      if (inst.instanceColor) inst.instanceColor.needsUpdate = true;
      scene.add(inst);
      layerMeshes.push(inst);
    }

    const raycaster: MinimalRaycaster = raycasterFactory
      ? raycasterFactory()
      : (new Raycaster() as unknown as MinimalRaycaster);

    function pickNeuron(clientX: number, clientY: number): NeuronCoord | null {
      const cam = cameraRef.current;
      if (!cam) return null;
      const rect = renderer.domElement.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return null;
      const nx = ((clientX - rect.left) / rect.width) * 2 - 1;
      const ny = -((clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(new Vector2(nx, ny), cam);
      for (let layer = 0; layer < layerMeshesRef.current.length; layer++) {
        const inst = layerMeshesRef.current[layer];
        const hits = raycaster.intersectObject(inst, false);
        if (hits.length > 0) {
          const top = hits[0];
          if (top.instanceId !== undefined) {
            return {
              layer,
              index: top.instanceId,
              label: buildLabel(layer, top.instanceId),
            };
          }
        }
      }
      return null;
    }

    function onPointerMove(ev: PointerEvent) {
      const coord = pickNeuron(ev.clientX, ev.clientY);
      const prev = hoveredRef.current;
      const changed = (coord?.label ?? null) !== (prev?.label ?? null);
      if (changed) {
        hoveredRef.current = coord;
        onHoverRef.current?.(coord);
      }
    }
    function onPointerLeave() {
      if (hoveredRef.current !== null) {
        hoveredRef.current = null;
        onHoverRef.current?.(null);
      }
    }
    function onClick(ev: MouseEvent) {
      const coord = pickNeuron(ev.clientX, ev.clientY);
      if (coord) onClickRef.current?.(coord);
    }
    renderer.domElement.addEventListener('pointermove', onPointerMove);
    renderer.domElement.addEventListener('pointerleave', onPointerLeave);
    renderer.domElement.addEventListener('click', onClick);

    const ro = new ResizeObserver(() => {
      const w = Math.max(wrapper.clientWidth, 1);
      const h = Math.max(wrapper.clientHeight, 1);
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    });
    ro.observe(wrapper);

    function tick() {
      rafRef.current = requestAnimationFrame(tick);
      controls.update();
      renderer.render(scene, camera);
    }

    sceneRef.current = scene;
    cameraRef.current = camera;
    rendererRef.current = renderer;
    controlsRef.current = controls;
    layerMeshesRef.current = layerMeshes;
    planeMeshesRef.current = planeMeshes;
    raycasterRef.current = raycaster;
    setMounted(true);

    if (rendererFactory) {
      type TestSurface = {
        __nn_scene?: Scene;
        __nn_camera?: PerspectiveCamera;
        __nn_layers?: InstancedMesh[];
        __nn_pick?: (x: number, y: number) => NeuronCoord | null;
        __nn_simulate_hover?: (x: number, y: number) => void;
        __nn_simulate_leave?: () => void;
        __nn_simulate_click?: (x: number, y: number) => void;
      };
      const w = wrapper as HTMLDivElement & TestSurface;
      w.__nn_scene = scene;
      w.__nn_camera = camera;
      w.__nn_layers = layerMeshes;
      w.__nn_pick = pickNeuron;
      w.__nn_simulate_hover = (x, y) => {
        const coord = pickNeuron(x, y);
        const prev = hoveredRef.current;
        const changed = (coord?.label ?? null) !== (prev?.label ?? null);
        if (changed) {
          hoveredRef.current = coord;
          onHoverRef.current?.(coord);
        }
      };
      w.__nn_simulate_leave = () => {
        if (hoveredRef.current !== null) {
          hoveredRef.current = null;
          onHoverRef.current?.(null);
        }
      };
      w.__nn_simulate_click = (x, y) => {
        const coord = pickNeuron(x, y);
        if (coord) onClickRef.current?.(coord);
      };
      renderer.render(scene, camera);
    } else if (typeof window !== 'undefined') {
      tick();
    }

    /**
     * E2E click hook — Playwright-driven smoke contract.
     *
     * Contract: `window.__nn_e2e_click(layer: number, index: number): void`
     * Behavior: synthesizes a `NeuronCoord` `{ layer, index, label: 'L<layer>N<index>' }`
     * and invokes the `onNeuronClick` prop callback (same path the real raycaster
     * would take on a click hit). Detached on unmount.
     *
     * Security: gated by `window.location.search` containing `e2e=1`. Production
     * builds without the flag never expose this surface — no privilege escalation,
     * no input is taken from the global beyond two numeric coordinates, and the
     * synthesized coord cannot bypass any consumer-side validation of the
     * `NeuronCoord` payload because it uses the exact same shape as a real hit.
     */
    let e2eClickAttached = false;
    // Strict gate: parse the search string and match `e2e` exactly to '1'.
    // `.includes('e2e=1')` would also match `?e2eopen=1` or `?xe2e=12`.
    const e2eFlag =
      typeof window !== 'undefined'
        ? new URLSearchParams(window.location?.search ?? '').get('e2e')
        : null;
    if (e2eFlag === '1') {
      (window as unknown as {
        __nn_e2e_click?: (layer: number, index: number) => void;
      }).__nn_e2e_click = (layer: number, index: number) => {
        const coord: NeuronCoord = {
          layer,
          index,
          label: buildLabel(layer, index),
        };
        onClickRef.current?.(coord);
      };
      e2eClickAttached = true;
    }

    return () => {
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
      if (zoomTweenRafRef.current != null) {
        cancelAnimationFrame(zoomTweenRafRef.current);
        zoomTweenRafRef.current = null;
      }
      if (e2eClickAttached && typeof window !== 'undefined') {
        delete (window as unknown as { __nn_e2e_click?: unknown }).__nn_e2e_click;
      }
      ro.disconnect();
      renderer.domElement.removeEventListener('pointermove', onPointerMove);
      renderer.domElement.removeEventListener('pointerleave', onPointerLeave);
      renderer.domElement.removeEventListener('click', onClick);
      // Three.js requires explicit disposal of geometries, materials, and the
      // renderer itself — React unmount doesn't reach into GPU resources.
      for (const inst of layerMeshes) {
        (inst.material as MeshBasicMaterial).dispose();
        scene.remove(inst);
      }
      for (const plane of planeMeshes) {
        plane.geometry.dispose();
        (plane.material as MeshBasicMaterial).dispose();
        scene.remove(plane);
      }
      sphereGeom.dispose();
      controls.dispose();
      renderer.dispose();
      if (renderer.domElement.parentElement === wrapper) {
        wrapper.removeChild(renderer.domElement);
      }
      sceneRef.current = null;
      cameraRef.current = null;
      rendererRef.current = null;
      controlsRef.current = null;
      layerMeshesRef.current = [];
      planeMeshesRef.current = [];
      raycasterRef.current = null;
      setMounted(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!mounted) return;
    const layers = layerMeshesRef.current;
    if (layers.length === 0) return;

    const drive = dominantDrive(currentFrame?.foundation_probe);
    const activeMap = new Map<string, number>();
    for (const a of currentFrame?.top_activated_neurons ?? []) {
      activeMap.set(buildLabel(a.layer, a.index), a.activation);
    }
    const blindspotSet = new Set(
      (blindspotCoords ?? []).map((c) => buildLabel(c.layer, c.index)),
    );
    const traceSet = new Set(
      (activeTraceCoords ?? []).map((c) => buildLabel(c.layer, c.index)),
    );

    const tmpColor = new Color();
    const blindspotColor = new Color(ATLAS_STATUS_COLORS.suppress);
    const traceColor = new Color(ATLAS_STATUS_COLORS.activeTrace);
    const selectedColor = new Color(ATLAS_STATUS_COLORS.intervention);

    for (let layer = 0; layer < layers.length; layer++) {
      const inst = layers[layer];
      for (let i = 0; i < NEURONS_PER_LAYER; i++) {
        const label = buildLabel(layer, i);
        if (
          selectedNeuron &&
          selectedNeuron.layer === layer &&
          selectedNeuron.index === i
        ) {
          inst.setColorAt(i, selectedColor);
          continue;
        }
        if (blindspotSet.has(label)) {
          inst.setColorAt(i, blindspotColor);
          continue;
        }
        if (traceSet.has(label)) {
          inst.setColorAt(i, traceColor);
          continue;
        }
        const act = activeMap.get(label);
        if (act !== undefined) {
          const css = foundationColorForActivation(drive, act);
          tmpColor.set(css);
          inst.setColorAt(i, tmpColor);
          continue;
        }
        inst.setColorAt(i, DIM_COLOR);
      }
      if (inst.instanceColor) inst.instanceColor.needsUpdate = true;
    }

    const renderer = rendererRef.current;
    const scene = sceneRef.current;
    const camera = cameraRef.current;
    if (renderer && scene && camera) renderer.render(scene, camera);
  }, [mounted, currentFrame, selectedNeuron, blindspotCoords, activeTraceCoords]);

  // Apply the zoom preset by tweening camera position + OrbitControls target
  // from the current camera state to the preset's (0, targetY, distance) over
  // ~250ms (ease-out cubic). Any in-flight tween is cancelled when a new
  // zoomLevel arrives, so successive preset changes never compound or overlap.
  // Existing raycaster, hover, click, blindspot, and active-trace overlays are
  // preserved — zoom is additive.
  useEffect(() => {
    if (!mounted) return;
    const camera = cameraRef.current;
    const controls = controlsRef.current;
    if (!camera) return;
    const preset =
      ZOOM_DISTANCE_PRESETS.find((p) => p.level === zoomLevel) ??
      ZOOM_DISTANCE_PRESETS[0];

    const startPosX = camera.position.x;
    const startPosY = camera.position.y;
    const startPosZ = camera.position.z;
    const startTargetX = controls?.target.x ?? 0;
    const startTargetY = controls?.target.y ?? 0;
    const startTargetZ = controls?.target.z ?? 0;
    const endPosX = 0;
    const endPosY = preset.targetY;
    const endPosZ = preset.distance;
    const endTargetX = 0;
    const endTargetY = preset.targetY;
    const endTargetZ = 0;

    const wrapper = wrapperRef.current;
    type ZoomTestSurface = {
      __nn_camera_distance?: number;
      __nn_target_camera_distance?: number;
    };
    if (wrapper) {
      (wrapper as HTMLDivElement & ZoomTestSurface).__nn_target_camera_distance =
        preset.distance;
    }
    if (typeof window !== 'undefined') {
      (window as unknown as ZoomTestSurface).__nn_target_camera_distance =
        preset.distance;
    }

    // Cancel any in-flight zoom tween before starting a new one; prevents
    // overlapping rAF loops from fighting over camera.position each frame.
    if (zoomTweenRafRef.current != null) {
      cancelAnimationFrame(zoomTweenRafRef.current);
      zoomTweenRafRef.current = null;
    }

    const hasRaf =
      typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function';

    const writeLiveDistance = () => {
      // True orbit distance from the camera to the controls target, NOT
      // distance from world origin. With OrbitControls target (0, 5, 0)
      // and Z5 camera at (0, 5, 3), position.length() = √(5²+3²) ≈ 5.83
      // but distanceTo(target) = 3 — the latter is what the zoom presets
      // intend to mean.
      // Fall back to position.length() (distance from world origin) only if
      // controls is unexpectedly null — keeps the test surface populated even
      // when OrbitControls failed to construct. distanceTo(target) is the
      // truth otherwise.
      const dist = controls
        ? camera.position.distanceTo(controls.target)
        : camera.position.length();
      if (wrapper) {
        (wrapper as HTMLDivElement & ZoomTestSurface).__nn_camera_distance = dist;
      }
      if (typeof window !== 'undefined') {
        (window as unknown as ZoomTestSurface).__nn_camera_distance = dist;
      }
    };

    if (!hasRaf) {
      camera.position.set(endPosX, endPosY, endPosZ);
      camera.lookAt(endTargetX, endTargetY, endTargetZ);
      if (controls) {
        controls.target.set(endTargetX, endTargetY, endTargetZ);
        controls.update();
      }
      writeLiveDistance();
      const renderer = rendererRef.current;
      const scene = sceneRef.current;
      if (renderer && scene) renderer.render(scene, camera);
      return;
    }

    const startTime =
      typeof performance !== 'undefined' && typeof performance.now === 'function'
        ? performance.now()
        : Date.now();

    const step = (nowArg?: number) => {
      const now =
        typeof nowArg === 'number'
          ? nowArg
          : typeof performance !== 'undefined' && typeof performance.now === 'function'
            ? performance.now()
            : Date.now();
      const elapsed = now - startTime;
      const tRaw = Math.min(1, Math.max(0, elapsed / ZOOM_TWEEN_DURATION_MS));
      const t = easeOutCubic(tRaw);
      camera.position.set(
        startPosX + (endPosX - startPosX) * t,
        startPosY + (endPosY - startPosY) * t,
        startPosZ + (endPosZ - startPosZ) * t,
      );
      if (controls) {
        controls.target.set(
          startTargetX + (endTargetX - startTargetX) * t,
          startTargetY + (endTargetY - startTargetY) * t,
          startTargetZ + (endTargetZ - startTargetZ) * t,
        );
        controls.update();
      } else {
        camera.lookAt(
          startTargetX + (endTargetX - startTargetX) * t,
          startTargetY + (endTargetY - startTargetY) * t,
          startTargetZ + (endTargetZ - startTargetZ) * t,
        );
      }
      writeLiveDistance();
      const renderer = rendererRef.current;
      const scene = sceneRef.current;
      if (renderer && scene) renderer.render(scene, camera);
      if (tRaw < 1) {
        zoomTweenRafRef.current = window.requestAnimationFrame(step);
      } else {
        zoomTweenRafRef.current = null;
      }
    };

    zoomTweenRafRef.current = window.requestAnimationFrame(step);
  }, [mounted, zoomLevel]);

  const containerStyle: CSSProperties = {
    width: '100%',
    height: '100%',
    minHeight: 280,
    position: 'relative',
  };

  return (
    <div
      ref={wrapperRef}
      data-testid="neuralnet-scene"
      data-mounted={mounted ? 'true' : 'false'}
      data-arch-family={architecture.family}
      data-arch-layers={architecture.n_layers}
      data-arch-mlp={architecture.mlp_intermediate_dim}
      className={className ?? ''}
      style={containerStyle}
    />
  );
}

export default NeuralNetScene;
