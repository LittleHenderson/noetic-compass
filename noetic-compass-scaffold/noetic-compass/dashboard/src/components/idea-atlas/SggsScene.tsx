/**
 * SggsScene — Three.js 3D viewer for the Atlas Thought Tree.
 *
 * Mirrors `ThoughtTreeView.tsx`'s functional contract (render every
 * node + edge, call `onNodeClick`, highlight `selectedNodeId`) and adds
 * orbit camera + mouse zoom + smooth Apple-style transitions. v0 layout
 * is the same hierarchical dendrogram as ThoughtTreeView, extruded into
 * 3D space with depth-staggered Z. Real force-directed graph is Phase 1
 * week 2-3 work; this scene ships first. The `LazySggsScene` export at
 * the bottom lets the integration step `React.lazy` the three.js bundle.
 */
import {
  lazy,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from 'react';
import {
  AdditiveBlending,
  AmbientLight,
  BoxGeometry,
  BufferGeometry,
  CanvasTexture,
  Color,
  DirectionalLight,
  DoubleSide,
  EdgesGeometry,
  Group,
  Line,
  LineBasicMaterial,
  LineSegments,
  Mesh,
  MeshBasicMaterial,
  PerspectiveCamera,
  PlaneGeometry,
  Raycaster,
  Scene,
  Vector2,
  Vector3,
  WebGLRenderer,
} from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import type {
  AtlasTraceThoughtTree,
  ThoughtTreeNode,
  ThoughtTreeRootNode,
} from '../../lib/trace';
import {
  SCENE_BACKGROUND_THREE,
  SELECTED_STROKE_THREE,
  paletteThreeFor,
  kindLabel,
} from '../../lib/sggs_palette';

// ── Public component contract ─────────────────────────────────────────────

export interface SggsSceneProps {
  tree: AtlasTraceThoughtTree;
  onNodeClick?: (node: ThoughtTreeNode) => void;
  selectedNodeId?: string | null;
  className?: string;
  fillParent?: boolean;
  /**
   * Override factory for the WebGLRenderer. Tests pass a JSDOM-safe stub
   * because jsdom has no WebGL. Production callers ignore this prop.
   */
  rendererFactory?: () => MinimalWebGLRenderer;
  /**
   * Override factory for the Raycaster — tests inject a deterministic
   * stub that "hits" a specific node id. Production uses the real
   * Three.js raycaster.
   */
  raycasterFactory?: () => MinimalRaycaster;
}

/**
 * The slice of `THREE.WebGLRenderer` the SGGS scene actually calls. Tests
 * supply a stub that satisfies this shape without touching WebGL.
 */
export interface MinimalWebGLRenderer {
  domElement: HTMLCanvasElement;
  setPixelRatio: (ratio: number) => void;
  setSize: (w: number, h: number) => void;
  setClearColor: (color: Color, alpha?: number) => void;
  render: (scene: Scene, camera: PerspectiveCamera) => void;
  dispose: () => void;
}

/** Slice of `THREE.Raycaster` we use — `setFromCamera` + `intersectObjects`. */
export interface MinimalRaycaster {
  setFromCamera: (coords: Vector2, camera: PerspectiveCamera) => void;
  intersectObjects: (
    objects: Mesh[],
    recursive?: boolean,
  ) => Array<{ object: Mesh; distance: number }>;
}

// ── Layout — mirrors ThoughtTreeView.buildLayout ──────────────────────────

// Cube geometry. The first cube pass reused wide card proportions, which
// made the side panels overhang and hid the top/bottom. Keep every face
// square so the block reads as a real inspectable object in the tree.
const CUBE_SIZE = 1.42;
const NODE_W = CUBE_SIZE;
const NODE_H = CUBE_SIZE;
const NODE_D = CUBE_SIZE;
const FACE_SIZE = CUBE_SIZE * 0.92;
const H_GAP = 0.84;
const V_GAP = 2.08;

/** Depth-staggered Z so adjacent levels don't render co-planar. */
const Z_STAGGER = 0.18;

function leafCount(node: ThoughtTreeRootNode): number {
  const children = node.children ?? [];
  if (children.length === 0) return 1;
  return children.reduce((acc, c) => acc + leafCount(c), 0);
}

interface NodePos3D {
  x: number;
  y: number;
  z: number;
  depth: number;
}

function buildLayout3D(root: ThoughtTreeRootNode): Record<string, NodePos3D> {
  const positions: Record<string, NodePos3D> = {};
  const slotWidth = NODE_W + H_GAP;

  function place(node: ThoughtTreeRootNode, depth: number, leftSlot: number): number {
    const myLeaves = leafCount(node);
    const centerSlot = leftSlot + myLeaves / 2;
    const x = centerSlot * slotWidth;
    const y = -depth * V_GAP;
    // Z stagger: 0 for root, alternating ±Z_STAGGER for descendant rows
    // so the eye can read depth even when the camera looks straight on.
    const z = (depth % 3 === 0 ? 0 : depth % 3 === 1 ? Z_STAGGER : -Z_STAGGER);
    const id = node.id;
    if (id) positions[id] = { x, y, z, depth };

    let cursorSlot = leftSlot;
    for (const child of node.children ?? []) {
      const childLeaves = leafCount(child);
      place(child, depth + 1, cursorSlot);
      cursorSlot += childLeaves;
    }
    return myLeaves;
  }
  place(root, 0, 0);
  return positions;
}

/**
 * Center the tree by shifting every (x, y) by -mean. Keeps the camera's
 * default look-at-origin pose framing the whole tree without needing the
 * caller to compute bounds.
 */
function recenterLayout(positions: Record<string, NodePos3D>): void {
  const ps = Object.values(positions);
  if (ps.length === 0) return;
  let sumX = 0;
  let sumY = 0;
  for (const p of ps) {
    sumX += p.x;
    sumY += p.y;
  }
  const meanX = sumX / ps.length;
  const meanY = sumY / ps.length;
  for (const p of ps) {
    p.x -= meanX;
    p.y -= meanY;
  }
}

// ── Cube faces — canvas texture rendering for inspectable sides ───────────

interface CubeFaceSpec {
  side: 'front' | 'right' | 'back' | 'left' | 'top' | 'bottom';
  title: string;
  lines: string[];
}

function trimLine(value: string, max = 30): string {
  const s = (value || '').replace(/\s+/g, ' ').trim();
  if (s.length <= max) return s;
  return `${s.slice(0, Math.max(1, max - 3))}...`;
}

function looksLikeCas(value: string): boolean {
  return /(\^\d|CO-\d|stage[A-Z]\d|Phi|NoeticCluster|export|let\s+)/.test(value);
}

function primaryNodeText(node: ThoughtTreeNode): string {
  return (node.text || node.label || kindLabel(node.kind) || '').trim();
}

function faceSpecsForNode(
  node: ThoughtTreeNode,
  pos: NodePos3D,
  childCount: number,
): CubeFaceSpec[] {
  const main = primaryNodeText(node);
  const casSurface = looksLikeCas(main) ? main : node.label || node.node_key || node.id;
  const status =
    node.role === 'copied' || node.role === 'missed' || node.role === 'partial'
      ? node.role
      : node.kind === 'confidence_marker'
        ? node.label
        : node.kind === 'identifier_attempt'
          ? node.role || 'identifier'
          : 'available';
  const evidenceLines =
    node.kind === 'slot_pattern'
      ? ['slot trace node', trimLine(node.label), 'source: trace_v0']
      : node.kind === 'identifier_attempt'
        ? [`copy status: ${status}`, 'source span tracked', 'network: pending']
        : node.kind === 'confidence_marker'
          ? [`quality: ${trimLine(node.label)}`, 'warning-ready face', 'network: pending']
          : ['trace node present', `kind: ${kindLabel(node.kind)}`, 'network: pending'];

  return [
    {
      side: 'front',
      title: 'Human Meaning',
      lines: [trimLine(main || 'CAS thought'), trimLine(kindLabel(node.kind), 26)],
    },
    {
      side: 'right',
      title: 'CAS Syntax',
      lines: [trimLine(casSurface), `role: ${trimLine(node.role || 'node', 20)}`],
    },
    {
      side: 'back',
      title: 'Trace Source',
      lines: [`id: ${trimLine(node.id, 22)}`, `key: ${trimLine(node.node_key, 24)}`],
    },
    {
      side: 'left',
      title: 'Model Evidence',
      lines: evidenceLines.map((line) => trimLine(line, 30)),
    },
    {
      side: 'top',
      title: 'Confidence',
      lines: [
        `status: ${trimLine(String(status), 22)}`,
        `warnings: ${node.kind === 'confidence_marker' ? 'check' : 'none'}`,
      ],
    },
    {
      side: 'bottom',
      title: 'Timeline',
      lines: [`replay step: ${pos.depth}`, `children: ${childCount}`],
    },
  ];
}

function makeFacePanel(
  spec: CubeFaceSpec,
  strokeHex: string,
  fillHex: string,
): Mesh | null {
  if (typeof document === 'undefined') return null;
  const canvas = document.createElement('canvas');
  const W = 512;
  const H = 512;
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext('2d');
  if (ctx) {
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = fillHex;
    ctx.fillRect(12, 12, W - 24, H - 24);
    ctx.fillStyle = 'rgba(2, 6, 23, 0.34)';
    ctx.fillRect(20, 20, W - 40, H - 40);
    ctx.strokeStyle = strokeHex;
    ctx.lineWidth = 8;
    ctx.strokeRect(12, 12, W - 24, H - 24);
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = strokeHex;
    ctx.font = 'bold 30px ui-monospace, SFMono-Regular, monospace';
    ctx.fillText(spec.title.toUpperCase(), W / 2, 92);
    ctx.fillStyle = '#f1f5f9';
    ctx.shadowColor = 'rgba(0, 0, 0, 0.72)';
    ctx.shadowBlur = 10;
    ctx.shadowOffsetY = 3;
    ctx.font = 'bold 34px ui-sans-serif, system-ui, sans-serif';
    for (let i = 0; i < spec.lines.slice(0, 3).length; i++) {
      ctx.fillText(spec.lines[i], W / 2, 198 + i * 58);
    }
  }
  const tex = new CanvasTexture(canvas);
  tex.needsUpdate = true;
  const mat = new MeshBasicMaterial({
    map: tex,
    transparent: true,
    opacity: 1,
    side: DoubleSide,
  });
  const mesh = new Mesh(new PlaneGeometry(FACE_SIZE, FACE_SIZE), mat);
  mesh.renderOrder = 2;
  return mesh;
}

function makeFaceGlow(strokeHex: string): Mesh | null {
  if (typeof document === 'undefined') return null;
  const canvas = document.createElement('canvas');
  const W = 512;
  const H = 512;
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext('2d');
  if (ctx) {
    ctx.clearRect(0, 0, W, H);
    const gradient = ctx.createRadialGradient(W / 2, H / 2, W * 0.12, W / 2, H / 2, W * 0.5);
    gradient.addColorStop(0, `${strokeHex}ee`);
    gradient.addColorStop(0.46, `${strokeHex}8c`);
    gradient.addColorStop(0.74, `${strokeHex}34`);
    gradient.addColorStop(1, `${strokeHex}00`);
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, W, H);
  }
  const tex = new CanvasTexture(canvas);
  tex.needsUpdate = true;
  const mat = new MeshBasicMaterial({
    map: tex,
    transparent: true,
    opacity: BASE_CUBE_GLOW_OPACITY,
    blending: AdditiveBlending,
    depthWrite: false,
    side: DoubleSide,
  });
  const mesh = new Mesh(new PlaneGeometry(FACE_SIZE * 1.42, FACE_SIZE * 1.42), mat);
  mesh.renderOrder = 1;
  return mesh;
}

function placeFacePanel(panel: Mesh, side: CubeFaceSpec['side']): void {
  const z = NODE_D / 2 + 0.014;
  const x = NODE_W / 2 + 0.014;
  const y = NODE_H / 2 + 0.014;
  if (side === 'front') {
    panel.position.set(0, 0, z);
  } else if (side === 'back') {
    panel.position.set(0, 0, -z);
    panel.rotation.y = Math.PI;
  } else if (side === 'right') {
    panel.position.set(x, 0, 0);
    panel.rotation.y = Math.PI / 2;
  } else if (side === 'left') {
    panel.position.set(-x, 0, 0);
    panel.rotation.y = -Math.PI / 2;
  } else if (side === 'top') {
    panel.position.set(0, y, 0);
    panel.rotation.x = -Math.PI / 2;
  } else {
    panel.position.set(0, -y, 0);
    panel.rotation.x = Math.PI / 2;
  }
}

function placeFaceGlow(panel: Mesh, side: CubeFaceSpec['side']): void {
  const z = NODE_D / 2 + 0.008;
  const x = NODE_W / 2 + 0.008;
  const y = NODE_H / 2 + 0.008;
  if (side === 'front') {
    panel.position.set(0, 0, z);
  } else if (side === 'back') {
    panel.position.set(0, 0, -z);
    panel.rotation.y = Math.PI;
  } else if (side === 'right') {
    panel.position.set(x, 0, 0);
    panel.rotation.y = Math.PI / 2;
  } else if (side === 'left') {
    panel.position.set(-x, 0, 0);
    panel.rotation.y = -Math.PI / 2;
  } else if (side === 'top') {
    panel.position.set(0, y, 0);
    panel.rotation.x = -Math.PI / 2;
  } else {
    panel.position.set(0, -y, 0);
    panel.rotation.x = Math.PI / 2;
  }
}

// ── Node mesh — glowing inspectable cube + side panels ────────────────────

interface NodeMeshBundle {
  group: Group;
  body: Mesh;
  ribbon: Mesh;
  /** Wireframe outline used to mark selection. Visible only when selected. */
  outline: LineSegments;
  /** Six face-aligned radiant glow planes. These sit behind the face
   *  text panels so the whole cube glows without bleaching the words. */
  faceGlows: Mesh[];
  facePanels: Mesh[];
  position: NodePos3D;
  node: ThoughtTreeNode;
  /** Original fill color — kept so selection never washes out face text. */
  baseFill: Color;
  /** Stable per-card index. Used as a phase offset in the ambient float
   *  so neighbouring cards don't bob in lockstep. */
  floatPhaseOffset: number;
  /** performance.now() when the last bounce was triggered; null when not
   *  bouncing. User feedback 2026-05-13: "structure should float
   *  slightly in space and bounce when hit or touched." */
  bounceStartedAt: number | null;
  /** User-controlled per-cube rotation. Once a user drags a cube,
   *  the idle animation stops owning that cube's orientation. */
  userRotationX: number;
  userRotationY: number;
  hasUserRotation: boolean;
}

function buildNodeMesh(
  node: ThoughtTreeNode,
  pos: NodePos3D,
  childCount: number,
): NodeMeshBundle {
  const palette = paletteThreeFor(node.kind);
  const group = new Group();
  group.position.set(pos.x, pos.y, pos.z);
  group.rotation.x = CUBE_READING_TILT_X;
  group.rotation.y = CUBE_READING_TILT_Y;
  group.userData = { 'data-node-id': node.id, kind: node.kind };

  // Cube body: solid palette fill behind the readable face panels.
  const bodyMat = new MeshBasicMaterial({
    color: palette.fill.clone(),
    transparent: true,
    opacity: 0.62,
  });
  const body = new Mesh(new BoxGeometry(NODE_W, NODE_H, NODE_D), bodyMat);
  body.userData = { 'data-node-id': node.id, role: 'body' };
  group.add(body);

  // Ribbon — thin tall plane on the left edge, brighter stroke color.
  // Mirrors the SVG card's kind-colored ribbon.
  const ribbonMat = new MeshBasicMaterial({
    color: palette.stroke.clone(),
    transparent: true,
    opacity: 0.98,
    side: DoubleSide,
  });
  const ribbon = new Mesh(new PlaneGeometry(0.08, NODE_H), ribbonMat);
  ribbon.position.set(-NODE_W / 2 + 0.05, 0, NODE_D / 2 + 0.018);
  ribbon.userData = { 'data-node-id': node.id, role: 'ribbon' };
  group.add(ribbon);

  // Selection outline — wireframe of a box slightly bigger than the card.
  // Hidden by default; flipped visible when `selectedNodeId` matches.
  const outlineGeom = new EdgesGeometry(
    new BoxGeometry(NODE_W + 0.12, NODE_H + 0.12, NODE_D + 0.12),
  );
  const outlineMat = new LineBasicMaterial({
    color: SELECTED_STROKE_THREE.clone(),
    transparent: true,
    opacity: 0,
  });
  const outline = new LineSegments(outlineGeom, outlineMat);
  outline.visible = false;
  outline.userData = { 'data-node-id': node.id, role: 'outline' };
  group.add(outline);

  // Six cube faces + six radiant glow layers.
  const faceGlows: Mesh[] = [];
  const facePanels: Mesh[] = [];
  const strokeHex = `#${palette.stroke.getHexString()}`;
  const fillHex = `#${palette.fill.getHexString()}`;
  for (const spec of faceSpecsForNode(node, pos, childCount)) {
    const glow = makeFaceGlow(strokeHex);
    if (glow) {
      placeFaceGlow(glow, spec.side);
      glow.userData = {
        'data-node-id': node.id,
        role: 'face-glow',
        face: spec.side,
      };
      faceGlows.push(glow);
      group.add(glow);
    }
    const panel = makeFacePanel(spec, strokeHex, fillHex);
    if (!panel) continue;
    placeFacePanel(panel, spec.side);
    panel.userData = {
      'data-node-id': node.id,
      role: 'cube-face',
      face: spec.side,
      title: spec.title,
    };
    facePanels.push(panel);
    group.add(panel);
  }

  return {
    group,
    body,
    ribbon,
    outline,
    faceGlows,
    facePanels,
    position: pos,
    node,
    baseFill: palette.fill.clone(),
    floatPhaseOffset: 0, // overwritten by the caller with a per-index offset
    bounceStartedAt: null,
    userRotationX: group.rotation.x,
    userRotationY: group.rotation.y,
    hasUserRotation: false,
  };
}

// ── Component ─────────────────────────────────────────────────────────────

const APPLE_EASE = 'cubic-bezier(0.4, 0, 0.2, 1)';
// Selection color-lerp duration. ~200ms per the smoothness brief.
const SELECT_LERP_MS = 200;
// Camera fly-to duration when selection changes.
const CAMERA_FLY_MS = 320;

// Cube glow parameters. The first glow pass used a single plane behind
// the card, which lit only one side and washed out text. The current
// version has six face-aligned radiant gradients behind the face text.
const BASE_CUBE_GLOW_OPACITY = 0.08;
const HOVER_CUBE_GLOW_OPACITY = 0.2;
const SELECTED_CUBE_GLOW_OPACITY_MIN = 0.24;
const SELECTED_CUBE_GLOW_OPACITY_MAX = 0.42;
const SELECTED_CUBE_GLOW_SCALE_MIN = 1.0;
const SELECTED_CUBE_GLOW_SCALE_MAX = 1.14;
const PULSE_PERIOD_MS = 1500;

// Ambient float — every card subtly bobs up/down so the structure
// feels alive. Amplitude in world units; period in ms.
// (User feedback 2026-05-13: "structure should float slightly in space".)
const FLOAT_AMPLITUDE = 0.07;
const FLOAT_PERIOD_MS = 3200;

// Bounce — when a card is touched (selected), it does a damped spring
// scale animation. Amplitude is the peak overshoot scale; duration is
// total animation length; damping controls how quickly it settles.
// (User feedback 2026-05-13: "bounce when hit or touched".)
const BOUNCE_AMPLITUDE = 0.18;
const BOUNCE_DURATION_MS = 520;
const BOUNCE_DAMPING = 3.4;

// Inspectable cube idle turn. It is intentionally subtle: enough to
// reveal that each block has multiple faces, not enough to detach it
// from its place in the tree. A small X tilt exposes top/bottom faces
// while the cube remains anchored to its node position.
const CUBE_IDLE_SPIN_PERIOD_MS = 9000;
const CUBE_READING_TILT_X = -0.34;
const CUBE_READING_TILT_Y = 0.26;
const CUBE_IDLE_SPIN_AMPLITUDE = 0.34;
const CUBE_SELECTED_SPIN_AMPLITUDE = 0.48;
const CUBE_IDLE_TILT_AMPLITUDE = 0.28;
const CUBE_SELECTED_TILT_AMPLITUDE = 0.38;
const CUBE_DRAG_ROTATION_SENSITIVITY = 0.012;
const CUBE_DRAG_THRESHOLD_PX = 3;

interface CubeDragState {
  nodeId: string;
  pointerId: number;
  startX: number;
  startY: number;
  startRotX: number;
  startRotY: number;
  moved: boolean;
}

export function SggsScene({
  tree,
  onNodeClick,
  selectedNodeId,
  className,
  fillParent = false,
  rendererFactory,
  raycasterFactory,
}: SggsSceneProps) {
  const wrapperRef = useRef<HTMLDivElement>(null);
  // Live refs into the Three.js graph — they outlive React renders.
  const sceneRef = useRef<Scene | null>(null);
  const cameraRef = useRef<PerspectiveCamera | null>(null);
  const rendererRef = useRef<MinimalWebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const meshesRef = useRef<NodeMeshBundle[]>([]);
  const edgesRef = useRef<Line[]>([]);
  const rafRef = useRef<number | null>(null);
  const raycasterRef = useRef<MinimalRaycaster | null>(null);
  const onNodeClickRef = useRef<SggsSceneProps['onNodeClick']>(onNodeClick);
  const selectedIdRef = useRef<string | null | undefined>(selectedNodeId);
  const hoveredIdRef = useRef<string | null>(null);
  const cubeDragRef = useRef<CubeDragState | null>(null);
  const selectAnimRef = useRef<{
    startedAt: number;
    fromColors: Map<string, Color>;
  } | null>(null);
  const cameraAnimRef = useRef<{
    startedAt: number;
    fromTarget: Vector3;
    toTarget: Vector3;
    fromPos: Vector3;
    toPos: Vector3;
  } | null>(null);

  // Track mount lifecycle for tests that observe canvas presence.
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    onNodeClickRef.current = onNodeClick;
  }, [onNodeClick]);
  useEffect(() => {
    selectedIdRef.current = selectedNodeId;
  }, [selectedNodeId]);

  // ── Layout computed up front. Used to seed the meshes + camera. ─────────
  const layout = useMemo(() => {
    if (!tree?.root || (tree.node_count ?? 0) === 0) return null;
    const positions = buildLayout3D(tree.root);
    recenterLayout(positions);
    return positions;
  }, [tree]);

  // ── Scene construction (mount-only). ─────────────────────────────────────
  useEffect(() => {
    const wrapper = wrapperRef.current;
    if (!wrapper) return;
    if (!layout) return;

    const width = Math.max(wrapper.clientWidth, 1);
    const height = Math.max(wrapper.clientHeight, 1);

    // Scene + camera.
    const scene = new Scene();
    scene.background = SCENE_BACKGROUND_THREE.clone();

    const camera = new PerspectiveCamera(45, width / height, 0.1, 200);
    // Sensible default: pulled back along +Z, slightly above center,
    // looking at origin.
    camera.position.set(0, 0, 9);
    camera.lookAt(0, 0, 0);

    // Renderer (real or test-injected).
    const renderer: MinimalWebGLRenderer = rendererFactory
      ? rendererFactory()
      : new WebGLRenderer({ antialias: true, alpha: false });
    renderer.setPixelRatio(typeof window === 'undefined' ? 1 : window.devicePixelRatio || 1);
    renderer.setSize(width, height);
    renderer.setClearColor(SCENE_BACKGROUND_THREE.clone(), 1);

    // Attach canvas to wrapper.
    wrapper.appendChild(renderer.domElement);
    renderer.domElement.setAttribute('data-testid', 'sggs-canvas');

    // Lights — ambient fill + directional from the camera direction.
    const ambient = new AmbientLight(0xffffff, 0.6);
    scene.add(ambient);
    const dir = new DirectionalLight(0xffffff, 0.4);
    dir.position.set(2, 3, 5);
    scene.add(dir);

    // Controls — only attach when we have a real WebGL canvas. Tests pass
    // a stub `HTMLCanvasElement` from JSDOM; OrbitControls works against
    // it but emits no events, which is what we want for unit tests.
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.screenSpacePanning = true;
    controls.minDistance = 2;
    controls.maxDistance = 60;
    controls.target.set(0, 0, 0);

    // Build meshes + edges from the layout. Each card gets a unique
    // phase offset so the ambient float doesn't bob the whole tree in
    // lockstep.
    const meshes: NodeMeshBundle[] = [];
    const childCountById = new Map<string, number>();
    for (const edge of tree.edges ?? []) {
      childCountById.set(edge.source, (childCountById.get(edge.source) ?? 0) + 1);
    }
    let idx = 0;
    for (const node of tree.nodes ?? []) {
      const pos = layout[node.id];
      if (!pos) continue;
      const bundle = buildNodeMesh(node, pos, childCountById.get(node.id) ?? 0);
      bundle.floatPhaseOffset = (idx * 0.62) % (Math.PI * 2);
      meshes.push(bundle);
      scene.add(bundle.group);
      idx++;
    }

    const edges: Line[] = [];
    // Index meshes by id so edge endpoints find their positions.
    const meshById = new Map(meshes.map((m) => [m.node.id, m]));
    for (const edge of tree.edges ?? []) {
      const a = meshById.get(edge.source);
      const b = meshById.get(edge.target);
      if (!a || !b) continue;
      const palette = paletteThreeFor(b.node.kind);
      const geom = new BufferGeometry().setFromPoints([
        new Vector3(a.position.x, a.position.y - NODE_H / 2, a.position.z),
        new Vector3(b.position.x, b.position.y + NODE_H / 2, b.position.z),
      ]);
      const mat = new LineBasicMaterial({
        color: palette.stroke.clone(),
        transparent: true,
        opacity: 0.85,
        linewidth: 2,
      });
      const line = new Line(geom, mat);
      line.userData = { 'data-edge-id': edge.id };
      edges.push(line);
      scene.add(line);
    }

    // Raycaster — real or test-injected.
    const raycaster: MinimalRaycaster = raycasterFactory
      ? raycasterFactory()
      : new Raycaster();

    function hitBundleFromPointer(ev: PointerEvent): NodeMeshBundle | null {
      if (!cameraRef.current) return null;
      const rect = renderer.domElement.getBoundingClientRect();
      const nx = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
      const ny = -((ev.clientY - rect.top) / rect.height) * 2 + 1;
      const ndc = new Vector2(nx, ny);
      raycaster.setFromCamera(ndc, cameraRef.current);
      const targets = meshesRef.current.flatMap((m) => [
        m.body,
        m.ribbon,
        ...m.facePanels,
      ]);
      const hits = raycaster.intersectObjects(targets, false);
      if (hits.length === 0) return null;
      // Every clickable face/body/ribbon carries the node id.
      const hit = hits[0].object;
      const id = (hit.userData as { 'data-node-id'?: string })['data-node-id'];
      if (!id) return null;
      const bundle = meshesRef.current.find((m) => m.node.id === id);
      return bundle ?? null;
    }

    function stopCubePointerEvent(ev: PointerEvent): void {
      ev.preventDefault();
      ev.stopPropagation();
      ev.stopImmediatePropagation();
    }

    // Cube interaction handler. Dragging a cube rotates only that cube;
    // dragging empty space still belongs to OrbitControls and moves the
    // whole SGGS structure.
    function onPointerDown(ev: PointerEvent) {
      // Only handle primary-button clicks; orbit controls own right/middle.
      if (ev.button !== 0) return;
      const bundle = hitBundleFromPointer(ev);
      if (!bundle) return;
      stopCubePointerEvent(ev);
      renderer.domElement.setPointerCapture?.(ev.pointerId);
      if (controlsRef.current) controlsRef.current.enabled = false;
      hoveredIdRef.current = bundle.node.id;
      const startRotX = bundle.group.rotation.x;
      const startRotY = bundle.group.rotation.y;
      cubeDragRef.current = {
        nodeId: bundle.node.id,
        pointerId: ev.pointerId,
        startX: ev.clientX,
        startY: ev.clientY,
        startRotX,
        startRotY,
        moved: false,
      };
      // Bounce on EVERY click, not just selection changes. Per Codex
      // audit 8939e62 blocker 4: if the user clicks the already-selected
      // card, the React selection-change effect doesn't fire (same id),
      // but the user still expects the card to bounce. Setting
      // bounceStartedAt here makes "touch the card" the bounce trigger,
      // not "select a different card".
      bundle.bounceStartedAt = performance.now();
      // Stop propagation so an orbit drag doesn't simultaneously trigger
      // a click; the OrbitControls implementation is tolerant of this.
      onNodeClickRef.current?.(bundle.node);
    }
    function onPointerMove(ev: PointerEvent) {
      const drag = cubeDragRef.current;
      if (drag) {
        stopCubePointerEvent(ev);
        const bundle = meshesRef.current.find((m) => m.node.id === drag.nodeId);
        if (!bundle) return;
        const dx = ev.clientX - drag.startX;
        const dy = ev.clientY - drag.startY;
        if (
          Math.abs(dx) >= CUBE_DRAG_THRESHOLD_PX ||
          Math.abs(dy) >= CUBE_DRAG_THRESHOLD_PX
        ) {
          drag.moved = true;
          bundle.hasUserRotation = true;
          bundle.userRotationY = drag.startRotY + dx * CUBE_DRAG_ROTATION_SENSITIVITY;
          bundle.userRotationX = drag.startRotX + dy * CUBE_DRAG_ROTATION_SENSITIVITY;
          bundle.group.rotation.x = bundle.userRotationX;
          bundle.group.rotation.y = bundle.userRotationY;
        }
        return;
      }
      hoveredIdRef.current = hitBundleFromPointer(ev)?.node.id ?? null;
    }
    function endCubeDrag(ev: PointerEvent) {
      const drag = cubeDragRef.current;
      if (!drag) return;
      stopCubePointerEvent(ev);
      renderer.domElement.releasePointerCapture?.(drag.pointerId);
      if (controlsRef.current) controlsRef.current.enabled = true;
      cubeDragRef.current = null;
    }
    function onPointerLeave() {
      if (cubeDragRef.current) return;
      hoveredIdRef.current = null;
    }
    renderer.domElement.addEventListener('pointerdown', onPointerDown, true);
    renderer.domElement.addEventListener('pointermove', onPointerMove, true);
    renderer.domElement.addEventListener('pointerup', endCubeDrag, true);
    renderer.domElement.addEventListener('pointercancel', endCubeDrag, true);
    renderer.domElement.addEventListener('pointerleave', onPointerLeave, true);

    // Resize observer — keeps renderer + camera matched to the wrapper.
    const ro = new ResizeObserver(() => {
      const w = Math.max(wrapper.clientWidth, 1);
      const h = Math.max(wrapper.clientHeight, 1);
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    });
    ro.observe(wrapper);

    // Animation loop. requestAnimationFrame so the scene matches the
    // display's native refresh rate; `damping: true` on controls makes
    // camera movement glide for the Apple-feel smoothness target.
    function tick() {
      rafRef.current = requestAnimationFrame(tick);
      const now = performance.now();
      // Selection-state — body color stays at baseFill so white text on
      // cube faces remains readable. Selection is signaled by face-glow
      // intensity + outline ring (no body washout). User feedback
      // 2026-05-13: "highlighted box turns grayish and hides white
      // lettering — fix this."
      const sa = selectAnimRef.current;
      if (sa) {
        const t = Math.min(1, (now - sa.startedAt) / SELECT_LERP_MS);
        const eased = easeInOutQuad(t);
        for (const bundle of meshesRef.current) {
          // Snap body color back to baseFill (no more washout).
          const mat = bundle.body.material as MeshBasicMaterial;
          mat.color.copy(bundle.baseFill);
          // Outline opacity fade — wireframe ring around the selected card.
          const outlineMat = bundle.outline.material as LineBasicMaterial;
          if (bundle.node.id === selectedIdRef.current) {
            bundle.outline.visible = true;
            outlineMat.opacity = eased;
          } else if (outlineMat.opacity > 0) {
            outlineMat.opacity = 1 - eased;
            if (eased >= 1) bundle.outline.visible = false;
          }
        }
        if (t >= 1) selectAnimRef.current = null;
      }

      // Cube glow — every cube has six low-opacity radiant face glows;
      // the hovered/selected cube brightens as a whole. Glows sit
      // behind the readable face panels so they do not bleach text.
      const pulsePhase = (now % PULSE_PERIOD_MS) / PULSE_PERIOD_MS;
      // Sine wave 0..1 (smooth ease at the endpoints).
      const pulseT = (Math.sin(pulsePhase * Math.PI * 2 - Math.PI / 2) + 1) / 2;
      for (const bundle of meshesRef.current) {
        const isSelected = bundle.node.id === selectedIdRef.current;
        const isHovered = bundle.node.id === hoveredIdRef.current;
        const glowOpacity = isSelected
          ? SELECTED_CUBE_GLOW_OPACITY_MIN +
            (SELECTED_CUBE_GLOW_OPACITY_MAX - SELECTED_CUBE_GLOW_OPACITY_MIN) *
              pulseT
          : isHovered
            ? HOVER_CUBE_GLOW_OPACITY
            : BASE_CUBE_GLOW_OPACITY;
        const glowScale = isSelected
          ? SELECTED_CUBE_GLOW_SCALE_MIN +
            (SELECTED_CUBE_GLOW_SCALE_MAX - SELECTED_CUBE_GLOW_SCALE_MIN) *
              pulseT
          : isHovered
            ? 1.08
            : 1;
        for (const glow of bundle.faceGlows) {
          const mat = glow.material as MeshBasicMaterial;
          mat.opacity = glowOpacity;
          glow.scale.set(glowScale, glowScale, 1);
        }
      }

      // Ambient float + per-card bounce. Each card subtly bobs up/down
      // around its layout-baseline Y; per-card phase offsets keep
      // neighbours out of sync. When a card is touched (selectedIdRef
      // changes), a damped sine bounce overlays the float for ~520ms.
      const floatPhaseBase = (now / FLOAT_PERIOD_MS) * Math.PI * 2;
      for (const bundle of meshesRef.current) {
        const phase = floatPhaseBase + bundle.floatPhaseOffset;
        const floatY = Math.sin(phase) * FLOAT_AMPLITUDE;
        bundle.group.position.y = bundle.position.y + floatY;

        const isHovered = bundle.node.id === hoveredIdRef.current;
        const spinAmp =
          bundle.node.id === selectedIdRef.current
            ? CUBE_SELECTED_SPIN_AMPLITUDE
            : CUBE_IDLE_SPIN_AMPLITUDE;
        const tiltAmp =
          bundle.node.id === selectedIdRef.current
            ? CUBE_SELECTED_TILT_AMPLITUDE
            : CUBE_IDLE_TILT_AMPLITUDE;
        if (bundle.hasUserRotation) {
          bundle.group.rotation.x = bundle.userRotationX;
          bundle.group.rotation.y = bundle.userRotationY;
        } else if (!isHovered) {
          const spinPhase =
            (now / CUBE_IDLE_SPIN_PERIOD_MS) * Math.PI * 2 +
            bundle.floatPhaseOffset;
          bundle.group.rotation.y = Math.sin(spinPhase) * spinAmp;
          bundle.group.rotation.x =
            CUBE_READING_TILT_X + Math.sin(spinPhase * 0.73 + 0.8) * tiltAmp;
        } else {
          bundle.group.rotation.x +=
            (CUBE_READING_TILT_X - bundle.group.rotation.x) * 0.18;
          bundle.group.rotation.y +=
            (CUBE_READING_TILT_Y - bundle.group.rotation.y) * 0.18;
        }

        // Damped bounce scale (whole group). Affects body/ribbon/faces/
        // glows/outline together so the cube pops then settles.
        let bounceScale = 1.0;
        if (bundle.bounceStartedAt !== null) {
          const t = (now - bundle.bounceStartedAt) / BOUNCE_DURATION_MS;
          if (t >= 1) {
            bundle.bounceStartedAt = null;
          } else {
            bounceScale =
              1 +
              BOUNCE_AMPLITUDE *
                Math.sin(t * Math.PI * 1.6) *
                Math.exp(-t * BOUNCE_DAMPING);
          }
        }
        bundle.group.scale.set(bounceScale, bounceScale, bounceScale);
      }
      // Camera fly-to-selection.
      const ca = cameraAnimRef.current;
      if (ca && cameraRef.current && controlsRef.current) {
        const t = Math.min(1, (now - ca.startedAt) / CAMERA_FLY_MS);
        const eased = easeInOutQuad(t);
        controlsRef.current.target.lerpVectors(ca.fromTarget, ca.toTarget, eased);
        cameraRef.current.position.lerpVectors(ca.fromPos, ca.toPos, eased);
        if (t >= 1) cameraAnimRef.current = null;
      }
      controls.update();
      renderer.render(scene, camera);
    }

    // Save refs.
    sceneRef.current = scene;
    cameraRef.current = camera;
    rendererRef.current = renderer;
    controlsRef.current = controls;
    meshesRef.current = meshes;
    edgesRef.current = edges;
    raycasterRef.current = raycaster;

    setMounted(true);
    // Test escape hatch — exposes the Three.js scene + camera on the
    // wrapper so unit tests can `scene.traverse` + count meshes per the
    // task brief. Only attached in test-mode (rendererFactory present)
    // so production builds carry no debug surface.
    if (rendererFactory) {
      type TestSurface = {
        __sggs_scene?: Scene;
        __sggs_camera?: PerspectiveCamera;
        __sggs_step?: () => void;
        __sggs_meshes?: NodeMeshBundle[];
      };
      const testWrapper = wrapper as HTMLDivElement & TestSurface;
      testWrapper.__sggs_scene = scene;
      testWrapper.__sggs_camera = camera;
      testWrapper.__sggs_step = () => {
        // Force animation completion so tests can assert final state
        // deterministically. Body color stays at baseFill (no washout);
        // selection is signaled by face glows +
        // outline ring fully visible. Mirrors the steady-state of the
        // rAF loop's selected branch.
        for (const bundle of meshesRef.current) {
          const isSelected = bundle.node.id === selectedIdRef.current;
          const mat = bundle.body.material as MeshBasicMaterial;
          mat.color.copy(bundle.baseFill);
          const glowOpacity = isSelected
            ? SELECTED_CUBE_GLOW_OPACITY_MAX
            : BASE_CUBE_GLOW_OPACITY;
          const glowScale = isSelected ? SELECTED_CUBE_GLOW_SCALE_MAX : 1;
          for (const glow of bundle.faceGlows) {
            const glowMat = glow.material as MeshBasicMaterial;
            glowMat.opacity = glowOpacity;
            glow.scale.set(glowScale, glowScale, 1);
          }
          const outlineMat = bundle.outline.material as LineBasicMaterial;
          if (isSelected) {
            bundle.outline.visible = true;
            outlineMat.opacity = 1;
          } else {
            outlineMat.opacity = 0;
            bundle.outline.visible = false;
          }
        }
        selectAnimRef.current = null;
        cameraAnimRef.current = null;
        renderer.render(scene, camera);
      };
      testWrapper.__sggs_meshes = meshes;
    }
    // Kick the loop only in non-test environments. Tests assert on
    // post-mount state; running rAF can leak across vitest test
    // boundaries. Tests can call `wrapper.__sggs_step()` to advance
    // deterministically.
    if (typeof window !== 'undefined' && !rendererFactory) {
      tick();
    } else {
      // Run a single render so the canvas has output even in tests.
      renderer.render(scene, camera);
    }

    return () => {
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
      ro.disconnect();
      renderer.domElement.removeEventListener('pointerdown', onPointerDown, true);
      renderer.domElement.removeEventListener('pointermove', onPointerMove, true);
      renderer.domElement.removeEventListener('pointerup', endCubeDrag, true);
      renderer.domElement.removeEventListener('pointercancel', endCubeDrag, true);
      renderer.domElement.removeEventListener('pointerleave', onPointerLeave, true);
      // Dispose materials, geometries, textures. The scene rebuilds
      // when the tree prop changes, so every cube-owned texture must go.
      for (const bundle of meshes) {
        bundle.body.geometry.dispose();
        (bundle.body.material as MeshBasicMaterial).dispose();
        bundle.ribbon.geometry.dispose();
        (bundle.ribbon.material as MeshBasicMaterial).dispose();
        bundle.outline.geometry.dispose();
        (bundle.outline.material as LineBasicMaterial).dispose();
        for (const glow of bundle.faceGlows) {
          glow.geometry.dispose();
          const mat = glow.material as MeshBasicMaterial;
          if (mat.map) mat.map.dispose();
          mat.dispose();
        }
        for (const panel of bundle.facePanels) {
          panel.geometry.dispose();
          const mat = panel.material as MeshBasicMaterial;
          if (mat.map) mat.map.dispose();
          mat.dispose();
        }
        scene.remove(bundle.group);
      }
      for (const edge of edges) {
        edge.geometry.dispose();
        (edge.material as LineBasicMaterial).dispose();
        scene.remove(edge);
      }
      controls.dispose();
      renderer.dispose();
      if (renderer.domElement.parentElement === wrapper) {
        wrapper.removeChild(renderer.domElement);
      }
      sceneRef.current = null;
      cameraRef.current = null;
      rendererRef.current = null;
      controlsRef.current = null;
      meshesRef.current = [];
      edgesRef.current = [];
      raycasterRef.current = null;
      setMounted(false);
    };
    // Layout + tree changes rebuild the scene. rendererFactory /
    // raycasterFactory are test-only and stable across renders.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layout, tree.nodes, tree.edges]);

  // ── Selection change → kick the color-lerp + camera fly + bounce. ───────
  useEffect(() => {
    if (!mounted) return;
    const fromColors = new Map<string, Color>();
    for (const bundle of meshesRef.current) {
      const mat = bundle.body.material as MeshBasicMaterial;
      fromColors.set(bundle.node.id, mat.color.clone());
    }
    selectAnimRef.current = { startedAt: performance.now(), fromColors };

    // Bounce the newly-selected card. User feedback 2026-05-13:
    // "bounce when hit or touched". The tick loop applies a damped
    // spring scale to bundle.group while bounceStartedAt is set.
    if (selectedNodeId) {
      const bundle = meshesRef.current.find(
        (m) => m.node.id === selectedNodeId,
      );
      if (bundle) {
        bundle.bounceStartedAt = performance.now();
      }
    }

    // Camera fly-to the selected node (if any).
    if (
      selectedNodeId &&
      cameraRef.current &&
      controlsRef.current
    ) {
      const bundle = meshesRef.current.find((m) => m.node.id === selectedNodeId);
      if (bundle) {
        const target = new Vector3(
          bundle.position.x,
          bundle.position.y,
          bundle.position.z,
        );
        // Sit the camera a few units back along its current view direction.
        const dir = new Vector3()
          .subVectors(cameraRef.current.position, controlsRef.current.target)
          .normalize();
        const desiredDistance = Math.max(
          4,
          cameraRef.current.position.distanceTo(controlsRef.current.target),
        );
        const toPos = new Vector3().copy(target).add(dir.multiplyScalar(desiredDistance));
        cameraAnimRef.current = {
          startedAt: performance.now(),
          fromTarget: controlsRef.current.target.clone(),
          toTarget: target,
          fromPos: cameraRef.current.position.clone(),
          toPos,
        };
      }
    }
  }, [mounted, selectedNodeId]);

  // ── Test hook: deterministic click simulation. ────────────────────────────
  //
  // The unit tests can't drive WebGL hit-testing through real mouse
  // events; instead they call custom simulation helpers below. Production
  // callers don't touch these events.
  useEffect(() => {
    if (!mounted) return;
    const wrapper = wrapperRef.current;
    if (!wrapper) return;
    function clickHandler(ev: Event) {
      const id = (ev as CustomEvent<{ id: string }>).detail?.id;
      if (!id) return;
      const bundle = meshesRef.current.find((m) => m.node.id === id);
      if (!bundle) return;
      onNodeClickRef.current?.(bundle.node);
    }
    function rotateHandler(ev: Event) {
      const detail = (ev as CustomEvent<{ id: string; dx: number; dy: number }>).detail;
      if (!detail?.id) return;
      const bundle = meshesRef.current.find((m) => m.node.id === detail.id);
      if (!bundle) return;
      bundle.hasUserRotation = true;
      bundle.userRotationY += detail.dx * CUBE_DRAG_ROTATION_SENSITIVITY;
      bundle.userRotationX += detail.dy * CUBE_DRAG_ROTATION_SENSITIVITY;
      bundle.group.rotation.x = bundle.userRotationX;
      bundle.group.rotation.y = bundle.userRotationY;
    }
    wrapper.addEventListener('sggs-simulate-click', clickHandler);
    wrapper.addEventListener('sggs-simulate-cube-drag', rotateHandler);
    return () => {
      wrapper.removeEventListener('sggs-simulate-click', clickHandler);
      wrapper.removeEventListener('sggs-simulate-cube-drag', rotateHandler);
    };
  }, [mounted]);

  // ── Render — wrapper div + canvas appended via three. ────────────────────

  const containerStyle: CSSProperties = {
    width: '100%',
    height: '100%',
    minHeight: fillParent ? 0 : 280,
    position: fillParent ? 'absolute' : 'relative',
    top: fillParent ? 0 : undefined,
    right: fillParent ? 0 : undefined,
    bottom: fillParent ? 0 : undefined,
    left: fillParent ? 0 : undefined,
    transition: `background-color 240ms ${APPLE_EASE}`,
  };

  return (
    <div
      ref={wrapperRef}
      data-testid="sggs-scene"
      data-mounted={mounted ? 'true' : 'false'}
      data-node-count={tree?.node_count ?? 0}
      className={[
        'rounded-lg border border-white/[0.06] bg-black/30',
        'dark:border-white/[0.08] dark:bg-black/40',
        'overflow-hidden',
        className ?? '',
      ]
        .filter(Boolean)
        .join(' ')}
      style={containerStyle}
    />
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────

function easeInOutQuad(t: number): number {
  return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
}

/**
 * Deterministic click helper for tests. Dispatches the simulated-click
 * event on the SggsScene wrapper. Production callers should NOT use
 * this; real users click in the canvas.
 */
export function simulateNodeClick(wrapper: HTMLElement, nodeId: string): void {
  const ev = new CustomEvent('sggs-simulate-click', { detail: { id: nodeId } });
  wrapper.dispatchEvent(ev);
}

/**
 * Test helper mirroring a user dragging one cube, not the entire scene.
 * Positive dx rotates around Y; positive dy rotates around X.
 */
export function simulateCubeDrag(
  wrapper: HTMLElement,
  nodeId: string,
  dx: number,
  dy: number,
): void {
  const ev = new CustomEvent('sggs-simulate-cube-drag', {
    detail: { id: nodeId, dx, dy },
  });
  wrapper.dispatchEvent(ev);
}

/** Lazy entry-point for the integration step. */
export const LazySggsScene = lazy(() =>
  import('./SggsScene').then((m) => ({ default: m.SggsScene })),
);

export default SggsScene;
