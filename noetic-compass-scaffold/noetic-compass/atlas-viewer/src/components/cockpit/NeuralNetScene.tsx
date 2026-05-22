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

export interface NeuralNetSceneProps {
  architecture: ModelArchitecture;
  currentFrame?: PerTokenFrame;
  selectedNeuron?: { layer: number; index: number };
  blindspotCoords?: NeuronCoord[];
  activeTraceCoords?: NeuronCoord[];
  onNeuronHover?: (coord: NeuronCoord | null) => void;
  onNeuronClick?: (coord: NeuronCoord) => void;
  className?: string;
  rendererFactory?: () => MinimalWebGLRenderer;
  raycasterFactory?: () => MinimalRaycaster;
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
    controls.minDistance = 4;
    controls.maxDistance = 120;
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

    return () => {
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
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
