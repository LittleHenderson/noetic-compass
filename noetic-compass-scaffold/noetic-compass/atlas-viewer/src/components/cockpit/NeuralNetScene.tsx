import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
} from 'react';
import {
  AmbientLight,
  BufferGeometry,
  Color,
  DirectionalLight,
  DoubleSide,
  InstancedMesh,
  Line,
  LineBasicMaterial,
  Mesh,
  MeshLambertMaterial,
  MeshBasicMaterial,
  Object3D,
  PerspectiveCamera,
  PlaneGeometry,
  Raycaster,
  Scene,
  SphereGeometry,
  Vector2,
  Vector3,
  WebGLRenderer,
} from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { AnimatePresence, motion, type PanInfo } from 'framer-motion';
import type { ModelArchitecture } from '../../lib/modelArchitecture';
import {
  ATLAS_STATUS_COLORS,
  foundationColorForActivation,
  type DriveIndex,
} from '../../lib/atlasPalette';
import { GlassPanel } from '../ui/GlassPanel';
import { ACCENT_BLUE, SPRING_SNAPPY } from '../../lib/designTokens';

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
  inversion_risk?: number | null;
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
  focusedBlindspotCoords?: NeuronCoord[];
  focusedBlindspotLabel?: string;
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
const MINI_STACK_SCALE = 0.18;
const DETACHED_ACTIVE_SCALE = 1.16;
const DETACHED_TRAY_SCALE = 0.44;
const MINI_STACK_X = -8.4;
const MINI_STACK_Y = 4.4;
const DETACHED_TRAY_START_X = -4.8;
const DETACHED_TRAY_START_Y = -4.1;
const DETACHED_TRAY_COL_GAP = 2.7;
const DETACHED_TRAY_ROW_GAP = 1.25;

const DIM_COLOR = new Color('#2a2a3a');
const PLANE_COLOR = new Color('#0f172a');
// Cockpit ambient tint — subtle dark-blue base to complement the floating
// glass UI overhead. Wave 5 darkened the previous '#05070d' to '#03060f'
// so the glass panels read more cleanly against the 3D scene. Spec allowed
// a gradient (top '#050818' / bottom '#02030a') but a solid is cheaper and
// indistinguishable on the rendered canvas at typical FOV.
const SCENE_BG = new Color('#03060f');
// Planes pick up ACCENT_BLUE at very low intensity to give a sense of depth
// without colouring the neurons themselves. Lambert material reacts to the
// existing AmbientLight + DirectionalLight; emissive carries the tint when
// the lights aren't striking the plane directly.
const PLANE_EMISSIVE = new Color(ACCENT_BLUE);
const PLANE_EMISSIVE_INTENSITY = 0.05;

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

function layerHomeZ(layer: number): number {
  const zStart = ((PYTHIA_N_LAYERS - 1) / 2) * LAYER_Z_SPACING;
  return zStart - layer * LAYER_Z_SPACING;
}

function neuronWorldPosition(coord: { layer: number; index: number }): Vector3 {
  const { x, y } = neuronLocalPosition(coord.index);
  return new Vector3(x, y, layerHomeZ(coord.layer));
}

function buildLabel(layer: number, index: number): string {
  return `L${layer}N${index}`;
}

function layerTitle(layer: number): string {
  return `Layer ${layer}`;
}

function stackPlace(layer: number): string {
  return `${layer + 1} of ${PYTHIA_N_LAYERS}`;
}

export function NeuralNetScene({
  architecture,
  currentFrame,
  selectedNeuron,
  blindspotCoords,
  focusedBlindspotCoords,
  focusedBlindspotLabel,
  activeTraceCoords,
  zoomLevel = 0,
  onNeuronHover,
  onNeuronClick,
  className,
  rendererFactory,
  raycasterFactory,
}: NeuralNetSceneProps) {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const stackDockRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<Scene | null>(null);
  const cameraRef = useRef<PerspectiveCamera | null>(null);
  const rendererRef = useRef<MinimalWebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const layerMeshesRef = useRef<InstancedMesh[]>([]);
  const planeMeshesRef = useRef<Mesh[]>([]);
  const focusLineRefs = useRef<Line[]>([]);
  const rafRef = useRef<number | null>(null);
  const zoomTweenRafRef = useRef<number | null>(null);
  const focusPulseRafRef = useRef<number | null>(null);
  const layerSpinRafRef = useRef<number | null>(null);
  const raycasterRef = useRef<MinimalRaycaster | null>(null);
  const onHoverRef = useRef(onNeuronHover);
  const onClickRef = useRef(onNeuronClick);
  const detachLayerRef = useRef<(layer: number) => void>(() => {});
  const hoveredRef = useRef<NeuronCoord | null>(null);
  const [mounted, setMounted] = useState(false);
  const [focusPulse, setFocusPulse] = useState(0);
  const [detachedLayers, setDetachedLayers] = useState<number[]>([]);
  const [activeDetachedLayer, setActiveDetachedLayer] = useState<number | null>(null);
  const [spinningLayers, setSpinningLayers] = useState<number[]>([]);
  const [selectedDockLayer, setSelectedDockLayer] = useState(0);
  // DOM tooltip state — Wave 5. The 3D scene reports hovers via the
  // onNeuronHover prop callback (preserved); a parallel local state powers a
  // GlassPanel tooltip that floats above the canvas at the cursor. Position
  // is in wrapper-local coordinates so it survives canvas scrolling.
  const [tooltip, setTooltip] = useState<
    { coord: NeuronCoord; x: number; y: number } | null
  >(null);

  useEffect(() => {
    onHoverRef.current = onNeuronHover;
  }, [onNeuronHover]);
  useEffect(() => {
    onClickRef.current = onNeuronClick;
  }, [onNeuronClick]);

  const detachLayer = (layer: number) => {
    setDetachedLayers((prev) => {
      if (prev.includes(layer)) return prev;
      return [...prev, layer];
    });
    setActiveDetachedLayer(layer);
  };

  const snapLayerHome = (layer: number) => {
    setDetachedLayers((prev) => prev.filter((item) => item !== layer));
    setSpinningLayers((prev) => prev.filter((item) => item !== layer));
    setActiveDetachedLayer((current) => {
      if (current !== layer) return current;
      const remaining = detachedLayers.filter((item) => item !== layer);
      return remaining.length > 0 ? remaining[remaining.length - 1] : null;
    });
  };

  const snapAllLayersHome = () => {
    setDetachedLayers([]);
    setSpinningLayers([]);
    setActiveDetachedLayer(null);
  };

  const toggleLayerSpin = (layer: number) => {
    setSpinningLayers((prev) =>
      prev.includes(layer)
        ? prev.filter((item) => item !== layer)
        : [...prev, layer],
    );
    setActiveDetachedLayer(layer);
  };

  const toggleLayerDetach = (layer: number) => {
    if (detachedLayers.includes(layer)) {
      snapLayerHome(layer);
      return;
    }
    detachLayer(layer);
  };

  detachLayerRef.current = (layer: number) => {
    toggleLayerDetach(layer);
  };

  useEffect(() => {
    if (activeDetachedLayer !== null && !detachedLayers.includes(activeDetachedLayer)) {
      setActiveDetachedLayer(
        detachedLayers.length > 0 ? detachedLayers[detachedLayers.length - 1] : null,
      );
    }
  }, [activeDetachedLayer, detachedLayers]);

  useEffect(() => {
    const docked = Array.from({ length: PYTHIA_N_LAYERS }, (_, layer) => layer).filter(
      (layer) => !detachedLayers.includes(layer),
    );
    if (docked.length > 0 && !docked.includes(selectedDockLayer)) {
      setSelectedDockLayer(docked[0]);
    }
  }, [detachedLayers, selectedDockLayer]);

  function neuronScenePosition(coord: { layer: number; index: number }): Vector3 {
    const layerMesh = layerMeshesRef.current[coord.layer];
    if (!layerMesh) return neuronWorldPosition(coord);
    const { x, y } = neuronLocalPosition(coord.index);
    return layerMesh.localToWorld(new Vector3(x, y, 0));
  }

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
      // Lambert (not Basic) so the plane can carry a low-intensity emissive
      // tint while still responding to scene lights. Base colour stays
      // grey/dim; emissive contributes ACCENT_BLUE at 5% — barely perceptible
      // but enough to suggest depth and tie the 3D zone to the glass UI palette.
      const planeMat = new MeshLambertMaterial({
        color: PLANE_COLOR.clone(),
        emissive: PLANE_EMISSIVE.clone(),
        emissiveIntensity: PLANE_EMISSIVE_INTENSITY,
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
      inst.position.set(0, 0, z);
      for (let i = 0; i < NEURONS_PER_LAYER; i++) {
        const { x, y } = neuronLocalPosition(i);
        dummy.position.set(x, y, 0);
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

    function pickLayer(clientX: number, clientY: number): number | null {
      const neuron = pickNeuron(clientX, clientY);
      if (neuron) return neuron.layer;

      const cam = cameraRef.current;
      if (!cam) return null;
      const rect = renderer.domElement.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return null;
      const nx = ((clientX - rect.left) / rect.width) * 2 - 1;
      const ny = -((clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(new Vector2(nx, ny), cam);
      for (let layer = 0; layer < planeMeshesRef.current.length; layer++) {
        const plane = planeMeshesRef.current[layer];
        const hits = raycaster.intersectObject(plane, false);
        if (hits.length > 0) return layer;
      }
      return null;
    }

    function wrapperLocalPosition(clientX: number, clientY: number) {
      if (!wrapper) return { x: 0, y: 0 };
      const rect = wrapper.getBoundingClientRect();
      return { x: clientX - rect.left, y: clientY - rect.top };
    }

    function onPointerMove(ev: PointerEvent) {
      const coord = pickNeuron(ev.clientX, ev.clientY);
      const prev = hoveredRef.current;
      const changed = (coord?.label ?? null) !== (prev?.label ?? null);
      if (changed) {
        hoveredRef.current = coord;
        onHoverRef.current?.(coord);
      }
      // Tooltip tracks the cursor regardless of hit-change so the GlassPanel
      // glides smoothly even while still hovering the same neuron.
      if (coord) {
        const pos = wrapperLocalPosition(ev.clientX, ev.clientY);
        setTooltip({ coord, x: pos.x, y: pos.y });
      } else if (changed) {
        setTooltip(null);
      }
    }
    function onPointerLeave() {
      if (hoveredRef.current !== null) {
        hoveredRef.current = null;
        onHoverRef.current?.(null);
      }
      setTooltip(null);
    }
    function onClick(ev: MouseEvent) {
      const coord = pickNeuron(ev.clientX, ev.clientY);
      if (coord) onClickRef.current?.(coord);
    }
    function onDoubleClick(ev: MouseEvent) {
      const layer = pickLayer(ev.clientX, ev.clientY);
      if (layer !== null) {
        detachLayerRef.current(layer);
      }
    }
    renderer.domElement.addEventListener('pointermove', onPointerMove);
    renderer.domElement.addEventListener('pointerleave', onPointerLeave);
    renderer.domElement.addEventListener('click', onClick);
    renderer.domElement.addEventListener('dblclick', onDoubleClick);

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
        __nn_planes?: Mesh[];
        __nn_pick?: (x: number, y: number) => NeuronCoord | null;
        __nn_pick_layer?: (x: number, y: number) => number | null;
        __nn_simulate_hover?: (x: number, y: number) => void;
        __nn_simulate_leave?: () => void;
        __nn_simulate_click?: (x: number, y: number) => void;
        __nn_simulate_double_click?: (x: number, y: number) => void;
        __nn_layer_layout?: () => Array<{
          layer: number;
          x: number;
          y: number;
          z: number;
          scale: number;
        }>;
      };
      const w = wrapper as HTMLDivElement & TestSurface;
      w.__nn_scene = scene;
      w.__nn_camera = camera;
      w.__nn_layers = layerMeshes;
      w.__nn_planes = planeMeshes;
      w.__nn_pick = pickNeuron;
      w.__nn_pick_layer = pickLayer;
      w.__nn_simulate_hover = (x, y) => {
        const coord = pickNeuron(x, y);
        const prev = hoveredRef.current;
        const changed = (coord?.label ?? null) !== (prev?.label ?? null);
        if (changed) {
          hoveredRef.current = coord;
          onHoverRef.current?.(coord);
        }
        if (coord) {
          const pos = wrapperLocalPosition(x, y);
          setTooltip({ coord, x: pos.x, y: pos.y });
        } else if (changed) {
          setTooltip(null);
        }
      };
      w.__nn_simulate_leave = () => {
        if (hoveredRef.current !== null) {
          hoveredRef.current = null;
          onHoverRef.current?.(null);
        }
        setTooltip(null);
      };
      w.__nn_simulate_click = (x, y) => {
        const coord = pickNeuron(x, y);
        if (coord) onClickRef.current?.(coord);
      };
      w.__nn_simulate_double_click = (x, y) => {
        const layer = pickLayer(x, y);
        if (layer !== null) detachLayerRef.current(layer);
      };
      w.__nn_layer_layout = () =>
        layerMeshes.map((mesh, layer) => ({
          layer,
          x: mesh.position.x,
          y: mesh.position.y,
          z: mesh.position.z,
          scale: mesh.scale.x,
        }));
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
    // Two-layer gate:
    //   (a) The build must opt in — DEV mode OR a build done with
    //       VITE_ENABLE_E2E_HOOK=true (e.g. vite build --mode e2e). Production
    //       builds without that flag never ship the hook into the bundle path.
    //   (b) The URL must include the strict ?e2e=1 query (exact match via
    //       URLSearchParams — not .includes(), which would also match
    //       ?e2eopen=1, ?xe2e=12, etc.).
    // Belt + suspenders: a leaked preview URL can't activate the hook on a
    // production build, and a production URL can't activate the hook even if
    // the build opted in.
    const e2eHookAllowedByBuild =
      import.meta.env.DEV ||
      import.meta.env.VITE_ENABLE_E2E_HOOK === 'true';
    const e2eFlag =
      typeof window !== 'undefined'
        ? new URLSearchParams(window.location?.search ?? '').get('e2e')
        : null;
    if (e2eHookAllowedByBuild && e2eFlag === '1') {
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
      if (layerSpinRafRef.current != null) {
        cancelAnimationFrame(layerSpinRafRef.current);
        layerSpinRafRef.current = null;
      }
      if (e2eClickAttached && typeof window !== 'undefined') {
        delete (window as unknown as { __nn_e2e_click?: unknown }).__nn_e2e_click;
      }
      ro.disconnect();
      renderer.domElement.removeEventListener('pointermove', onPointerMove);
      renderer.domElement.removeEventListener('pointerleave', onPointerLeave);
      renderer.domElement.removeEventListener('click', onClick);
      renderer.domElement.removeEventListener('dblclick', onDoubleClick);
      // Three.js requires explicit disposal of geometries, materials, and the
      // renderer itself — React unmount doesn't reach into GPU resources.
      for (const inst of layerMeshes) {
        (inst.material as MeshBasicMaterial).dispose();
        scene.remove(inst);
      }
      for (const plane of planeMeshes) {
        plane.geometry.dispose();
        (plane.material as MeshLambertMaterial).dispose();
        scene.remove(plane);
      }
      for (const line of focusLineRefs.current) {
        line.geometry.dispose();
        (line.material as LineBasicMaterial).dispose();
        scene.remove(line);
      }
      focusLineRefs.current = [];
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
    if (!focusedBlindspotCoords?.length || typeof window === 'undefined') {
      setFocusPulse(0);
      if (focusPulseRafRef.current !== null && typeof window !== 'undefined') {
        window.cancelAnimationFrame(focusPulseRafRef.current);
        focusPulseRafRef.current = null;
      }
      return;
    }

    let active = true;
    const step = (ts: number) => {
      if (!active) return;
      setFocusPulse(ts);
      focusPulseRafRef.current = window.requestAnimationFrame(step);
    };
    focusPulseRafRef.current = window.requestAnimationFrame(step);
    return () => {
      active = false;
      if (focusPulseRafRef.current !== null) {
        window.cancelAnimationFrame(focusPulseRafRef.current);
        focusPulseRafRef.current = null;
      }
    };
  }, [focusedBlindspotCoords]);

  useEffect(() => {
    if (!mounted) return;
    const layers = layerMeshesRef.current;
    const planes = planeMeshesRef.current;
    if (layers.length === 0 || planes.length === 0) return;

    const detachedSet = new Set(detachedLayers);
    const activeLayer =
      activeDetachedLayer !== null && detachedSet.has(activeDetachedLayer)
        ? activeDetachedLayer
        : detachedLayers[detachedLayers.length - 1] ?? null;
    const dockedLayers = Array.from({ length: PYTHIA_N_LAYERS }, (_, layer) => layer).filter(
      (layer) => !detachedSet.has(layer),
    );

    for (let layer = 0; layer < PYTHIA_N_LAYERS; layer++) {
      const inst = layers[layer];
      const plane = planes[layer];
      if (!inst || !plane) continue;

      const isDetached = detachedSet.has(layer);
      const isActive = isDetached && layer === activeLayer;
      const detachIndex = Math.max(0, detachedLayers.indexOf(layer));
      const dockIndex = Math.max(0, dockedLayers.indexOf(layer));
      const trayLayers = detachedLayers.filter((item) => item !== activeLayer);
      const trayIndex = Math.max(0, trayLayers.indexOf(layer));
      const trayCol = trayIndex % 4;
      const trayRow = Math.floor(trayIndex / 4);

      let x = 0;
      let y = 0;
      let z = layerHomeZ(layer);
      let scale = 1;
      let planeOpacity = 0.18;

      if (isDetached) {
        if (isActive) {
          x = 0;
          y = 0;
          z = 0;
          scale = DETACHED_ACTIVE_SCALE;
          planeOpacity = 0.3;
        } else {
          x = DETACHED_TRAY_START_X + trayCol * DETACHED_TRAY_COL_GAP;
          y = DETACHED_TRAY_START_Y - trayRow * DETACHED_TRAY_ROW_GAP;
          z = 1.2 - trayRow * 0.22 - detachIndex * 0.04;
          scale = DETACHED_TRAY_SCALE;
          planeOpacity = 0.22;
        }
      } else if (detachedLayers.length > 0) {
        x = MINI_STACK_X;
        y = MINI_STACK_Y - dockIndex * 0.24;
        z = 4.2 - dockIndex * 0.1;
        scale = MINI_STACK_SCALE;
        planeOpacity = 0.14;
      }

      inst.position.set(x, y, z);
      plane.position.set(x, y, z);
      inst.scale.setScalar(scale);
      plane.scale.setScalar(scale);
      if (!spinningLayers.includes(layer)) {
        inst.rotation.set(0, 0, 0);
        plane.rotation.set(0, 0, 0);
      }
      const planeMat = plane.material as MeshLambertMaterial;
      planeMat.opacity = planeOpacity;
      planeMat.emissiveIntensity = isActive
        ? PLANE_EMISSIVE_INTENSITY * 2.4
        : PLANE_EMISSIVE_INTENSITY;
    }

    const renderer = rendererRef.current;
    const scene = sceneRef.current;
    const camera = cameraRef.current;
    if (renderer && scene && camera) renderer.render(scene, camera);
  }, [mounted, detachedLayers, activeDetachedLayer, spinningLayers]);

  useEffect(() => {
    if (!mounted || typeof window === 'undefined') return;
    if (spinningLayers.length === 0) {
      if (layerSpinRafRef.current !== null) {
        window.cancelAnimationFrame(layerSpinRafRef.current);
        layerSpinRafRef.current = null;
      }
      return;
    }

    let active = true;
    const step = (ts: number) => {
      if (!active) return;
      for (const layer of spinningLayers) {
        if (!detachedLayers.includes(layer)) continue;
        const inst = layerMeshesRef.current[layer];
        const plane = planeMeshesRef.current[layer];
        const angle = ts / 900;
        inst?.rotation.set(0, 0, angle);
        plane?.rotation.set(0, 0, angle);
      }
      const renderer = rendererRef.current;
      const scene = sceneRef.current;
      const camera = cameraRef.current;
      if (renderer && scene && camera) renderer.render(scene, camera);
      layerSpinRafRef.current = window.requestAnimationFrame(step);
    };
    layerSpinRafRef.current = window.requestAnimationFrame(step);
    return () => {
      active = false;
      if (layerSpinRafRef.current !== null) {
        window.cancelAnimationFrame(layerSpinRafRef.current);
        layerSpinRafRef.current = null;
      }
    };
  }, [mounted, detachedLayers, spinningLayers]);

  useEffect(() => {
    if (!mounted) return;
    const scene = sceneRef.current;
    const renderer = rendererRef.current;
    const camera = cameraRef.current;
    if (!scene || !renderer || !camera) return;

    for (const line of focusLineRefs.current) {
      line.geometry.dispose();
      (line.material as LineBasicMaterial).dispose();
      scene.remove(line);
    }
    focusLineRefs.current = [];

    const coords = focusedBlindspotCoords ?? [];
    const stringOpacity =
      zoomLevel >= 5 ? 0.9 : zoomLevel === 4 ? 0.58 : zoomLevel === 3 ? 0.24 : 0;
    if (coords.length >= 2 && stringOpacity > 0) {
      const sorted = [...coords].sort((a, b) => {
        if (a.layer !== b.layer) return a.layer - b.layer;
        return a.index - b.index;
      });
      for (let i = 0; i < sorted.length - 1; i++) {
        const points = [
          neuronScenePosition(sorted[i]),
          neuronScenePosition(sorted[i + 1]),
        ];
        const geometry = new BufferGeometry().setFromPoints(points);
        const material = new LineBasicMaterial({
          color: '#2dd4bf',
          transparent: true,
          opacity: stringOpacity,
        });
        const line = new Line(geometry, material);
        line.userData = {
          kind: 'focused-blindspot-string',
          label: focusedBlindspotLabel,
        };
        scene.add(line);
        focusLineRefs.current.push(line);
      }
    }

    renderer.render(scene, camera);
  }, [
    mounted,
    focusedBlindspotCoords,
    focusedBlindspotLabel,
    zoomLevel,
    detachedLayers,
    activeDetachedLayer,
  ]);

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
    const focusedBlindspotSet = new Set(
      (focusedBlindspotCoords ?? []).map((c) => buildLabel(c.layer, c.index)),
    );
    const traceSet = new Set(
      (activeTraceCoords ?? []).map((c) => buildLabel(c.layer, c.index)),
    );

    const tmpColor = new Color();
    const blindspotColor = new Color(ATLAS_STATUS_COLORS.suppress);
    const traceColor = new Color(ATLAS_STATUS_COLORS.activeTrace);
    const selectedColor = new Color(ATLAS_STATUS_COLORS.intervention);
    const focusedBaseColor = new Color('#2dd4bf');
    const focusedPulseColor = new Color('#facc15');
    const pulseAmount =
      focusedBlindspotSet.size > 0 ? (Math.sin(focusPulse / 150) + 1) / 2 : 0;
    const focusedColor = focusedBaseColor.clone().lerp(focusedPulseColor, pulseAmount);

    for (let layer = 0; layer < layers.length; layer++) {
      const inst = layers[layer];
      for (let i = 0; i < NEURONS_PER_LAYER; i++) {
        const label = buildLabel(layer, i);
        if (focusedBlindspotSet.has(label)) {
          inst.setColorAt(i, focusedColor);
          continue;
        }
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
  }, [
    mounted,
    currentFrame,
    selectedNeuron,
    blindspotCoords,
    focusedBlindspotCoords,
    focusPulse,
    activeTraceCoords,
  ]);

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

  const layerHintStyle: CSSProperties = {
    position: 'absolute',
    left: 14,
    bottom: 14,
    zIndex: 4,
    maxWidth: 320,
    pointerEvents: 'none',
  };

  const stackDockStyle: CSSProperties = {
    position: 'absolute',
    right: 14,
    top: 14,
    zIndex: 10,
    width: 258,
  };

  const layerCardRailStyle: CSSProperties = {
    position: 'absolute',
    right: 14,
    top: detachedLayers.length > 0 ? 146 : 14,
    zIndex: 11,
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    width: 238,
    maxHeight: 'calc(100% - 124px)',
    overflowY: 'auto',
    pointerEvents: 'auto',
  };

  const layerActionButtonStyle: CSSProperties = {
    minHeight: 25,
    padding: '4px 8px',
    borderRadius: 6,
    border: '1px solid rgba(45, 212, 191, 0.32)',
    background: 'rgba(15, 23, 42, 0.72)',
    color: '#ccfbf1',
    cursor: 'pointer',
    fontSize: 11,
    fontWeight: 700,
  };

  const dockSelectRowStyle: CSSProperties = {
    display: 'grid',
    gridTemplateColumns: '1fr auto',
    gap: 6,
    marginTop: 8,
  };

  const dockLayerSelectStyle: CSSProperties = {
    minHeight: 30,
    borderRadius: 6,
    border: '1px solid rgba(148, 163, 184, 0.24)',
    background: 'rgba(15, 23, 42, 0.68)',
    color: '#cbd5e1',
    fontSize: 12,
    fontFamily: 'inherit',
    padding: '4px 8px',
  };

  const dockLayerButtonStyle: CSSProperties = {
    minHeight: 30,
    borderRadius: 6,
    border: '1px solid rgba(45, 212, 191, 0.42)',
    background: 'rgba(20, 184, 166, 0.16)',
    color: '#ccfbf1',
    cursor: 'pointer',
    fontSize: 11,
    fontWeight: 800,
    fontFamily: 'inherit',
    padding: '4px 10px',
  };

  const activeDetached =
    activeDetachedLayer !== null && detachedLayers.includes(activeDetachedLayer)
      ? activeDetachedLayer
      : detachedLayers[detachedLayers.length - 1] ?? null;

  const dockedLayerControls = Array.from(
    { length: PYTHIA_N_LAYERS },
    (_, layer) => layer,
  ).filter((layer) => !detachedLayers.includes(layer));

  const layerActivityCount = (layer: number) =>
    currentFrame?.top_activated_neurons.filter((item) => item.layer === layer).length ?? 0;
  const layerBlindspotCount = (layer: number) =>
    (blindspotCoords ?? []).filter((item) => item.layer === layer).length;
  const layerTraceCount = (layer: number) =>
    (activeTraceCoords ?? []).filter((item) => item.layer === layer).length;

  const isPointInsideStackDock = (point: { x: number; y: number }) => {
    const dock = stackDockRef.current;
    if (!dock) return false;
    const rect = dock.getBoundingClientRect();
    const margin = 18;
    return (
      point.x >= rect.left - margin &&
      point.x <= rect.right + margin &&
      point.y >= rect.top - margin &&
      point.y <= rect.bottom + margin
    );
  };

  const handleLayerCardDragEnd = (layer: number, info: PanInfo) => {
    if (isPointInsideStackDock(info.point)) {
      snapLayerHome(layer);
    }
  };

  // Tooltip offset from cursor so the GlassPanel doesn't sit under the
  // pointer (which would block subsequent hover picks on adjacent neurons).
  const TOOLTIP_OFFSET_X = 14;
  const TOOLTIP_OFFSET_Y = 14;

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
    >
      <AnimatePresence>
        {focusedBlindspotCoords?.length ? (
          <motion.div
            key="focused-blindspot-badge"
            data-testid="focused-blindspot-badge"
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={SPRING_SNAPPY}
            style={{
              position: 'absolute',
              left: 14,
              top: 14,
              zIndex: 4,
              pointerEvents: 'none',
            }}
          >
            <GlassPanel intensity="regular" padding="7px 10px">
              <span
                style={{
                  display: 'block',
                  color: '#ccfbf1',
                  fontSize: 12,
                  fontWeight: 800,
                }}
              >
                {focusedBlindspotLabel ?? 'Cover'} neurons pulsing
              </span>
              <span
                style={{
                  display: 'block',
                  color: '#94a3b8',
                  fontSize: 11,
                  marginTop: 2,
                }}
              >
                {focusedBlindspotCoords.length} neurons highlighted
                {zoomLevel >= 3 ? ' · cover string visible' : ' · zoom in for cover string'}
              </span>
            </GlassPanel>
          </motion.div>
        ) : null}
      </AnimatePresence>
      <AnimatePresence>
        {detachedLayers.length === 0 ? (
          <motion.div
            key="layer-detach-hint"
            data-testid="layer-detach-hint"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 6 }}
            transition={SPRING_SNAPPY}
            style={layerHintStyle}
          >
            <GlassPanel intensity="thin" padding="7px 10px">
              <span
                style={{
                  display: 'block',
                  color: '#ccfbf1',
                  fontSize: 12,
                  fontWeight: 800,
                }}
              >
                Double-click a layer to inspect it
              </span>
              <span
                style={{
                  display: 'block',
                  color: '#94a3b8',
                  fontSize: 11,
                  marginTop: 2,
                  lineHeight: 1.35,
                }}
              >
                The layer detaches; the remaining stack docks in the corner.
                Double-click a detached layer again to snap it back.
              </span>
            </GlassPanel>
          </motion.div>
        ) : null}
      </AnimatePresence>
      <AnimatePresence>
        {detachedLayers.length > 0 ? (
          <motion.div
            key="layer-stack-dock"
            ref={stackDockRef}
            data-testid="layer-stack-dock"
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 10 }}
            transition={SPRING_SNAPPY}
            style={stackDockStyle}
          >
            <GlassPanel intensity="regular" padding="8px 10px">
              <span
                style={{
                  display: 'block',
                  color: '#e2e8f0',
                  fontSize: 12,
                  fontWeight: 800,
                }}
              >
                Mini stack dock
              </span>
              <span
                style={{
                  display: 'block',
                  color: '#94a3b8',
                  fontSize: 11,
                  lineHeight: 1.35,
                  marginTop: 3,
                }}
              >
                {PYTHIA_N_LAYERS - detachedLayers.length} layers docked · drag a
                layer card here to snap home · click a layer number to detach it
              </span>
              {dockedLayerControls.length > 0 ? (
                <div data-testid="layer-dock-controls" style={{ marginTop: 8 }}>
                  <label
                    htmlFor="layer-dock-select"
                    style={{
                      display: 'block',
                      color: '#cbd5e1',
                      fontSize: 11,
                      fontWeight: 800,
                      marginBottom: 4,
                    }}
                  >
                    Detach another layer
                  </label>
                  <div style={dockSelectRowStyle}>
                    <select
                      id="layer-dock-select"
                      data-testid="layer-dock-select"
                      value={selectedDockLayer}
                      onChange={(event) => setSelectedDockLayer(Number(event.target.value))}
                      style={dockLayerSelectStyle}
                      aria-label="Choose another layer to detach"
                    >
                      {dockedLayerControls.map((layer) => (
                        <option key={layer} value={layer}>
                          {layerTitle(layer)} · {stackPlace(layer)}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      data-testid="layer-dock-detach-selected"
                      onClick={() => detachLayer(selectedDockLayer)}
                      style={dockLayerButtonStyle}
                    >
                      Detach
                    </button>
                  </div>
                </div>
              ) : null}
              <button
                type="button"
                data-testid="layer-snap-all"
                onClick={snapAllLayersHome}
                style={{
                  ...layerActionButtonStyle,
                  width: '100%',
                  marginTop: 8,
                }}
              >
                Snap all back
              </button>
            </GlassPanel>
          </motion.div>
        ) : null}
      </AnimatePresence>
      <AnimatePresence>
        {detachedLayers.length > 0 ? (
          <div style={layerCardRailStyle} data-testid="layer-card-rail">
            {detachedLayers.map((layer) => {
              const isActive = layer === activeDetached;
              const isSpinning = spinningLayers.includes(layer);
              return (
                <motion.div
                  key={layer}
                  drag
                  dragMomentum={false}
                  dragElastic={0.08}
                  onDragStart={() => setActiveDetachedLayer(layer)}
                  onDragEnd={(_, info) => handleLayerCardDragEnd(layer, info)}
                  initial={{ opacity: 0, x: 18 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 18 }}
                  whileDrag={{ scale: 1.02 }}
                  transition={SPRING_SNAPPY}
                  data-testid={`detached-layer-card-${layer}`}
                  style={{ cursor: 'grab' }}
                >
                  <GlassPanel
                    intensity={isActive ? 'thick' : 'regular'}
                    padding="9px 10px"
                    style={{
                      borderColor: isActive
                        ? 'rgba(45, 212, 191, 0.58)'
                        : 'rgba(255, 255, 255, 0.08)',
                      background: isActive
                        ? 'rgba(20, 184, 166, 0.10)'
                        : 'rgba(15, 23, 42, 0.56)',
                    }}
                  >
                    <span
                      style={{
                        display: 'block',
                        color: isActive ? '#ccfbf1' : '#e2e8f0',
                        fontSize: 12,
                        fontWeight: 900,
                      }}
                    >
                      {layerTitle(layer)} · stack place {stackPlace(layer)}
                    </span>
                    <span
                      style={{
                        display: 'block',
                        color: '#94a3b8',
                        fontSize: 11,
                        marginTop: 3,
                        lineHeight: 1.35,
                      }}
                    >
                      3,072 MLP neurons · active {layerActivityCount(layer)} ·
                      covers {layerBlindspotCount(layer)} · trace {layerTraceCount(layer)}
                    </span>
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: '1fr 1fr 1fr',
                        gap: 6,
                        marginTop: 8,
                      }}
                    >
                      <button
                        type="button"
                        data-testid={`layer-focus-${layer}`}
                        onClick={() => setActiveDetachedLayer(layer)}
                        style={layerActionButtonStyle}
                      >
                        Focus
                      </button>
                      <button
                        type="button"
                        data-testid={`layer-spin-${layer}`}
                        onClick={() => toggleLayerSpin(layer)}
                        style={layerActionButtonStyle}
                      >
                        {isSpinning ? 'Stop' : 'Spin'}
                      </button>
                      <button
                        type="button"
                        data-testid={`layer-snap-${layer}`}
                        onClick={() => snapLayerHome(layer)}
                        style={layerActionButtonStyle}
                      >
                        Snap
                      </button>
                    </div>
                  </GlassPanel>
                </motion.div>
              );
            })}
          </div>
        ) : null}
      </AnimatePresence>
      <AnimatePresence>
        {tooltip && (
          <motion.div
            key="neuralnet-tooltip"
            data-testid="neuralnet-tooltip"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={SPRING_SNAPPY}
            style={{
              position: 'absolute',
              left: `min(${tooltip.x + TOOLTIP_OFFSET_X}px, calc(100% - 130px))`,
              top: `min(${tooltip.y + TOOLTIP_OFFSET_Y}px, calc(100% - 44px))`,
              pointerEvents: 'none',
              zIndex: 3,
            }}
          >
            <GlassPanel intensity="thick" padding="6px 10px">
              <span
                style={{
                  fontFamily:
                    'ui-monospace, SFMono-Regular, "JetBrains Mono", monospace',
                  fontSize: 12,
                  letterSpacing: 0.2,
                  color: '#e2e8f0',
                }}
              >
                {tooltip.coord.label}
              </span>
            </GlassPanel>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default NeuralNetScene;
