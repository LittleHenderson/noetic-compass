import { useCallback, useEffect, useMemo, useState } from 'react';
import type { CSSProperties } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ControlBar, {
  type Speed,
  type LiveStatus,
  type RuntimeMode,
  type VerificationMode,
  type ZoomLevel,
} from './ControlBar';
import {
  NeuralNetScene,
  type NeuronCoord,
  type PerTokenFrame,
} from './NeuralNetScene';
import Mode7Timeline, {
  type Mode7Frame,
  type Token,
} from './Mode7Timeline';
import MethodKnobsPanel, { type KnobValue } from './MethodKnobsPanel';
import SpatialEvidencePanel from './SpatialEvidencePanel';
import VisualPrimitiveCanvas from './VisualPrimitiveCanvas';
import EvidenceDrawer, { type EvidenceDrawerPayload } from './EvidenceDrawer';
import HelpOverlay from './HelpOverlay';
import { useReplayController } from '../../hooks/useReplayController';
import type { ReplayTrace } from '../../lib/replayController';
import type { ModelArchitecture } from '../../lib/modelArchitecture';
import {
  LIVE_WORKER_METHODS,
  type TestingMethod,
} from '../../lib/testingMethods';
import type {
  LiveMethodControls,
  LiveMethodId,
} from '../../lib/liveMethodControls';
import {
  primitivesForStep,
  type EvidenceRef,
  type SpatialEvidenceArtifact,
  type VisualPrimitive,
} from '../../lib/visualPrimitives';
import { ATLAS_STATUS_COLORS } from '../../lib/atlasPalette';
import { parseCoord } from '../../lib/neuronCover';
import { GlassPanel } from '../ui/GlassPanel';
import { ACCENT_TEAL, COLORS, SPRING_GENTLE, SPRING_SNAPPY, THEME } from '../../lib/designTokens';

interface TraceNeuronCovers {
  per_class_neuron_covers?: Record<string, string[]>;
}
interface TraceWithCovers {
  neuron_covers?: TraceNeuronCovers;
  model_id?: string;
}

const LIVE_METHOD_IDS: readonly LiveMethodId[] = [
  'foundation_probe',
  'rpm_gate_check',
  'inversion_scan',
  'sparse_neuron_cover',
  'drive_local_eraser',
  'blindspot_detection',
  'verification_stack',
];
const LIVE_METHOD_ID_SET = new Set<string>(LIVE_METHOD_IDS);

export interface AtlasViewerShellProps {
  trace: ReplayTrace;
  spatialEvidence: SpatialEvidenceArtifact;
  architecture: ModelArchitecture;
  methods?: readonly TestingMethod[];
  runtimeMode?: RuntimeMode;
  liveStatus?: LiveStatus;
  liveError?: string | null;
  onStartLive?: (controls: LiveMethodControls) => void;
  onLiveControlsChange?: (controls: LiveMethodControls) => void;
  onUseReplay?: () => void;
  className?: string;
}

type LeftTab = 'spatial' | 'notation';

const shellStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  width: '100%',
  height: '100%',
  minHeight: 0,
  background: '#020617',
  color: COLORS.textPrimary,
  fontFamily: THEME.fontFamily,
  position: 'relative',
};

const controlBarFloatStyle: CSSProperties = {
  position: 'relative',
  zIndex: 10,
  margin: 8,
};

const columnStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  minWidth: 0,
  minHeight: 0,
  overflow: 'hidden',
};

const floatingCardStyle: CSSProperties = {
  margin: 8,
  flex: 1,
  display: 'flex',
  flexDirection: 'column',
  minHeight: 0,
  overflow: 'hidden',
};

const tabBarStyle: CSSProperties = {
  display: 'flex',
  position: 'relative',
  borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
};

const tabBaseStyle: CSSProperties = {
  flex: 1,
  padding: '8px 12px',
  position: 'relative',
  background: 'transparent',
  color: COLORS.textMuted,
  border: 'none',
  cursor: 'pointer',
  fontSize: 11.5,
  fontWeight: 500,
  letterSpacing: 0.4,
  textTransform: 'uppercase',
};

const tabActiveStyle: CSSProperties = {
  ...tabBaseStyle,
  color: ACCENT_TEAL,
  fontWeight: 600,
};

const tabUnderlineStyle: CSSProperties = {
  position: 'absolute',
  left: 0,
  right: 0,
  bottom: -1,
  height: 1,
  background: ACCENT_TEAL,
  borderRadius: 0,
};

const tabPanelStyle: CSSProperties = {
  flex: 1,
  overflowY: 'auto',
  padding: 12,
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
  minHeight: 0,
};

const centerSceneWrapperStyle: CSSProperties = {
  flex: 1,
  minHeight: 0,
  position: 'relative',
};

const rightCardInnerStyle: CSSProperties = {
  flex: 1,
  minHeight: 0,
  overflowY: 'auto',
};

const bottomTimelineFloatStyle: CSSProperties = {
  position: 'relative',
  zIndex: 10,
  margin: '0 8px 8px 8px',
};

const placeholderCardStyle: CSSProperties = {
  padding: 16,
  borderRadius: 6,
  background: 'rgba(255, 255, 255, 0.02)',
  border: '1px dashed rgba(255, 255, 255, 0.08)',
  color: COLORS.textMuted,
  fontSize: 12.5,
  lineHeight: 1.55,
};

// Wave 5.3 fullscreen: NN scene sits at viewport inset 0, hiding all
// surrounding chrome (control bar, narration, timeline, side panels).
// A small floating exit-fullscreen button overlays the top-right.
const fullscreenOverlayStyle: CSSProperties = {
  position: 'absolute',
  inset: 0,
  zIndex: 40,
  background: '#020617',
};

const fullscreenExitButtonStyle: CSSProperties = {
  position: 'absolute',
  top: 12,
  right: 12,
  zIndex: 41,
  padding: '6px 12px',
  borderRadius: 6,
  border: '1px solid rgba(45, 212, 191, 0.45)',
  background: 'rgba(45, 212, 191, 0.10)',
  color: ACCENT_TEAL,
  fontSize: 11.5,
  fontWeight: 600,
  letterSpacing: 0.3,
  fontFamily: THEME.fontFamily,
  cursor: 'pointer',
};

// Provenance badge — surfaces real-vs-demo split in the cockpit header so
// the user never thinks they're looking at a mock. Trace is real Pythia-160M
// activations replayed from disk; spatial primitives are demo fixtures
// until the live wire-up lands.
const provenanceBadgeStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 6,
  padding: '3px 8px',
  borderRadius: 4,
  border: '1px solid rgba(45, 212, 191, 0.35)',
  background: 'rgba(45, 212, 191, 0.08)',
  color: ACCENT_TEAL,
  fontSize: 10.5,
  fontWeight: 600,
  letterSpacing: 0.8,
  textTransform: 'uppercase',
  fontFamily: THEME.fontFamily,
};

const provenanceDotStyle: CSSProperties = {
  width: 6,
  height: 6,
  borderRadius: '50%',
  background: ACCENT_TEAL,
};

const demoBadgeStyle: CSSProperties = {
  ...provenanceBadgeStyle,
  border: '1px solid rgba(234, 179, 8, 0.40)',
  background: 'rgba(234, 179, 8, 0.08)',
  color: '#fbbf24',
};

const demoDotStyle: CSSProperties = {
  ...provenanceDotStyle,
  background: '#fbbf24',
};

function defaultValueForKnob(knob: { type: string; default: unknown }): KnobValue {
  if (knob.type === 'multiselect') {
    return Array.isArray(knob.default) ? [...(knob.default as string[])] : [];
  }
  if (knob.type === 'boolean') return Boolean(knob.default);
  if (knob.type === 'number') {
    return typeof knob.default === 'number' ? knob.default : 0;
  }
  return String(knob.default ?? '');
}

function initialKnobValues(
  methods: readonly TestingMethod[],
): Record<string, Record<string, KnobValue>> {
  const out: Record<string, Record<string, KnobValue>> = {};
  for (const method of methods) {
    const knobMap: Record<string, KnobValue> = {};
    for (const knob of method.knobs) {
      knobMap[knob.id] = defaultValueForKnob(knob);
    }
    out[method.id] = knobMap;
  }
  return out;
}

function frameToToken(frame: unknown): Token | null {
  if (typeof frame !== 'object' || frame === null) return null;
  const f = frame as { token_index?: unknown; token?: unknown };
  if (typeof f.token_index !== 'number' || typeof f.token !== 'string') return null;
  return { token_index: f.token_index, token: f.token };
}

function frameToMode7Frame(frame: unknown): Mode7Frame | null {
  if (typeof frame !== 'object' || frame === null) return null;
  const f = frame as {
    token_index?: unknown;
    mode7_attribution?: unknown;
  };
  if (typeof f.token_index !== 'number') return null;
  const attr = Array.isArray(f.mode7_attribution) ? f.mode7_attribution : undefined;
  return {
    token_index: f.token_index,
    mode7_attribution: attr as Mode7Frame['mode7_attribution'],
  };
}

function frameAtIndex(frames: unknown[], index: number): PerTokenFrame | undefined {
  const candidate = frames[index];
  if (typeof candidate !== 'object' || candidate === null) return undefined;
  return candidate as PerTokenFrame;
}

export function AtlasViewerShell(props: AtlasViewerShellProps): JSX.Element {
  const {
    trace,
    spatialEvidence,
    architecture,
    methods = LIVE_WORKER_METHODS,
    runtimeMode = 'replay',
    liveStatus = 'idle',
    liveError = null,
    onStartLive,
    onLiveControlsChange,
    onUseReplay,
    className,
  } = props;

  const {
    state,
    toggle,
    seek,
    setSpeed,
  } = useReplayController(trace);

  const [leftTab, setLeftTab] = useState<LeftTab>('spatial');
  const [selectedNeuron, setSelectedNeuron] = useState<NeuronCoord | undefined>(
    undefined,
  );
  const [activePrimitiveId, setActivePrimitiveId] = useState<string | undefined>(
    undefined,
  );
  const [enabledMethodIds, setEnabledMethodIds] = useState<Set<string>>(
    () => new Set(methods.map((m) => m.id)),
  );
  const [knobValues, setKnobValues] = useState<
    Record<string, Record<string, KnobValue>>
  >(() => initialKnobValues(methods));
  const [zoomLevel, setZoomLevel] = useState<ZoomLevel>(0);
  const [showBlindspots, setShowBlindspots] = useState<boolean>(true);
  const [showActiveTrace, setShowActiveTrace] = useState<boolean>(true);
  const [verificationMode, setVerificationMode] =
    useState<VerificationMode>('BALANCED');
  const [evidenceDrawerOpen, setEvidenceDrawerOpen] = useState<boolean>(false);
  const [evidencePayload, setEvidencePayload] = useState<
    EvidenceDrawerPayload | undefined
  >(undefined);

  const [leftPanelOpen, setLeftPanelOpen] = useState<boolean>(true);
  const [rightPanelOpen, setRightPanelOpen] = useState<boolean>(true);
  const [fullscreen, setFullscreen] = useState<boolean>(false);
  const [helpOpen, setHelpOpen] = useState<boolean>(false);

  const tokens = useMemo<Token[]>(() => {
    if (trace.tokens && trace.tokens.length > 0) return trace.tokens;
    return trace.per_token_frames
      .map(frameToToken)
      .filter((t): t is Token => t !== null);
  }, [trace.tokens, trace.per_token_frames]);

  const mode7Frames = useMemo<Mode7Frame[]>(() => {
    return trace.per_token_frames
      .map(frameToMode7Frame)
      .filter((f): f is Mode7Frame => f !== null);
  }, [trace.per_token_frames]);

  const isLiveTraceVisible =
    runtimeMode === 'live' &&
    liveStatus !== 'idle' &&
    liveStatus !== 'error' &&
    tokens.length > 0;
  const currentTokenIndex = isLiveTraceVisible
    ? Math.max(0, tokens.length - 1)
    : state.currentTokenIndex;
  const currentFrame = useMemo<PerTokenFrame | undefined>(
    () => frameAtIndex(trace.per_token_frames, currentTokenIndex),
    [trace.per_token_frames, currentTokenIndex],
  );

  const activeStep = useMemo(() => {
    return spatialEvidence.grounded_steps.find(
      (s) => s.token_index === currentTokenIndex,
    );
  }, [spatialEvidence.grounded_steps, currentTokenIndex]);

  const activePrimitives = useMemo<VisualPrimitive[]>(() => {
    if (!activeStep) return [];
    return primitivesForStep(spatialEvidence, activeStep.step_id);
  }, [spatialEvidence, activeStep]);

  const activePrimitiveIds = useMemo<string[]>(
    () => activePrimitives.map((p) => p.id),
    [activePrimitives],
  );

  const activeTraceCoords = useMemo<NeuronCoord[] | undefined>(() => {
    if (!showActiveTrace || !currentFrame) return undefined;
    return currentFrame.top_activated_neurons
      .filter((n) => n.activation >= 0.3)
      .map((n) => ({
        layer: n.layer,
        index: n.index,
        label: `L${n.layer}N${n.index}`,
      }));
  }, [showActiveTrace, currentFrame]);

  const blindspotCoords = useMemo<NeuronCoord[] | undefined>(() => {
    if (!showBlindspots) return undefined;
    const covers = (trace as unknown as TraceWithCovers).neuron_covers?.per_class_neuron_covers;
    if (!covers) return undefined;
    const seen = new Set<string>();
    const out: NeuronCoord[] = [];
    for (const labels of Object.values(covers)) {
      for (const label of labels) {
        if (seen.has(label)) continue;
        seen.add(label);
        try {
          out.push(parseCoord(label));
        } catch {
          // Skip malformed cover entries; don't crash the scene.
        }
      }
    }
    return out;
  }, [showBlindspots, trace]);

  const liveControls = useMemo<LiveMethodControls>(() => {
    const enabled = [...enabledMethodIds].filter((id): id is LiveMethodId =>
      LIVE_METHOD_ID_SET.has(id),
    );
    const liveKnobs: LiveMethodControls['knobValues'] = {};
    for (const methodId of enabled) {
      liveKnobs[methodId] = knobValues[methodId] ?? {};
    }
    return {
      enabledMethodIds: enabled,
      knobValues: liveKnobs,
      verificationMode,
      showBlindspots,
      showActiveTrace,
    };
  }, [
    enabledMethodIds,
    knobValues,
    verificationMode,
    showBlindspots,
    showActiveTrace,
  ]);

  useEffect(() => {
    onLiveControlsChange?.(liveControls);
  }, [liveControls, onLiveControlsChange]);

  useEffect(() => {
    setActivePrimitiveId(undefined);
  }, [activeStep?.step_id]);

  // Wave 5.3: Esc exits fullscreen so the user always has a keyboard
  // escape hatch even if they can't see the exit button.
  useEffect(() => {
    if (!fullscreen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setFullscreen(false);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [fullscreen]);

  const handlePlayToggle = useCallback(() => {
    toggle();
  }, [toggle]);

  const handleSpeedChange = useCallback(
    (s: Speed) => {
      setSpeed(s);
    },
    [setSpeed],
  );

  const handleTokenSeek = useCallback(
    (idx: number) => {
      seek(idx);
    },
    [seek],
  );

  const handleRewind = useCallback(() => {
    seek(0);
  }, [seek]);

  const handleToggleLeftPanel = useCallback(() => {
    setLeftPanelOpen((v) => !v);
  }, []);

  const handleToggleRightPanel = useCallback(() => {
    setRightPanelOpen((v) => !v);
  }, []);

  const handleToggleFullscreen = useCallback(() => {
    setFullscreen((v) => !v);
  }, []);

  const handleToggleHelp = useCallback(() => {
    setHelpOpen((v) => !v);
  }, []);

  const handleToggleMethod = useCallback(
    (methodId: string, enabled: boolean) => {
      setEnabledMethodIds((prev) => {
        const next = new Set(prev);
        if (enabled) next.add(methodId);
        else next.delete(methodId);
        return next;
      });
    },
    [],
  );

  const handleKnobChange = useCallback(
    (methodId: string, knobId: string, value: KnobValue) => {
      setKnobValues((prev) => ({
        ...prev,
        [methodId]: {
          ...(prev[methodId] ?? {}),
          [knobId]: value,
        },
      }));
    },
    [],
  );

  const openDrawer = useCallback((payload: EvidenceDrawerPayload) => {
    setEvidencePayload(payload);
    setEvidenceDrawerOpen(true);
  }, []);

  const closeDrawer = useCallback(() => {
    setEvidenceDrawerOpen(false);
  }, []);

  const handleNeuronClick = useCallback(
    (coord: NeuronCoord) => {
      setSelectedNeuron(coord);
      openDrawer({
        source: 'neuron',
        title: coord.label,
        evidence_ref: {
          neuron_coordinate: coord.label,
          layer: coord.layer,
          neuron_index: coord.index,
          token_index: currentTokenIndex,
        },
        detail: {
          token: tokens[currentTokenIndex]?.token,
          architecture: architecture.family,
        },
      });
    },
    [openDrawer, currentTokenIndex, tokens, architecture.family],
  );

  const handlePrimitiveSelect = useCallback((p: VisualPrimitive) => {
    setActivePrimitiveId(p.id);
  }, []);

  const handlePrimitiveOpenEvidence = useCallback(
    (ref: EvidenceRef) => {
      openDrawer({
        source: 'primitive',
        title: 'Spatial primitive',
        evidence_ref: ref,
      });
    },
    [openDrawer],
  );

  const handlePrimitiveCanvasClick = useCallback(
    (p: VisualPrimitive, ref?: EvidenceRef) => {
      setActivePrimitiveId(p.id);
      if (ref) {
        openDrawer({
          source: 'primitive',
          title: p.label ?? p.id,
          evidence_ref: ref,
          detail: {
            cas_label: p.cas_label,
            cas_axis: p.cas_axis,
            confidence: p.confidence,
          },
        });
      }
    },
    [openDrawer],
  );

  const controlsDensity = leftPanelOpen ? 'compact' : 'comfortable';

  // Wave 5.3: flex layout — each side column gets a motion.aside with an
  // animated flex value. flex=0 collapses the column smoothly to 0 width
  // (framer-motion interpolates the numeric flex basis). Production tools
  // expect a continuous slide, not a CSS-grid snap.
  const leftFlex = leftPanelOpen ? 38 : 0;
  const rightFlex = rightPanelOpen ? 20 : 0;
  const centerFlex = 100 - leftFlex - rightFlex;

  const mainRowStyle: CSSProperties = {
    flex: 1,
    display: 'flex',
    flexDirection: 'row',
    minHeight: 0,
    overflow: 'hidden',
    position: 'relative',
  };

  const modelId = (trace as unknown as TraceWithCovers).model_id ?? architecture.family;
  const liveLabel =
    liveStatus === 'connecting'
      ? 'Live · connecting'
      : liveStatus === 'streaming'
        ? `Live · streaming · ${modelId} · actual weights`
        : liveStatus === 'complete'
          ? `Live · complete · ${modelId} · actual weights`
          : liveStatus === 'error'
            ? 'Live unavailable'
            : `Replay · ${modelId} · recorded trace`;
  const tokenTextNow = tokens[currentTokenIndex]?.token ?? '';
  const narrationStyle: CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: 12,
    padding: '6px 12px',
    fontSize: 11.5,
    color: COLORS.textSecondary,
    letterSpacing: 0.3,
    margin: '0 8px',
  };
  const narrationKeyStyle: CSSProperties = {
    color: COLORS.textMuted,
    fontSize: 10.5,
    fontWeight: 600,
    letterSpacing: 1,
    textTransform: 'uppercase',
  };
  const narrationValueStyle: CSSProperties = {
    color: COLORS.textPrimary,
    fontFamily: THEME.fontMono,
  };

  // Fullscreen mode renders only the NN scene + a floating exit button.
  // All other chrome is hidden so the network truly fills the viewport.
  if (fullscreen) {
    return (
      <div
        className={className}
        data-testid="atlas-viewer-shell"
        data-fullscreen="true"
        style={shellStyle}
      >
        <div style={fullscreenOverlayStyle}>
          <NeuralNetScene
            architecture={architecture}
            currentFrame={currentFrame}
            selectedNeuron={selectedNeuron}
            blindspotCoords={blindspotCoords}
            activeTraceCoords={activeTraceCoords}
            zoomLevel={zoomLevel}
            onNeuronClick={handleNeuronClick}
          />
          <button
            type="button"
            style={fullscreenExitButtonStyle}
            onClick={handleToggleFullscreen}
            data-testid="exit-fullscreen"
            aria-label="Exit fullscreen"
          >
            Exit fullscreen · Esc
          </button>
        </div>

        <EvidenceDrawer
          open={evidenceDrawerOpen}
          payload={evidencePayload}
          onClose={closeDrawer}
        />
        <HelpOverlay open={helpOpen} onClose={() => setHelpOpen(false)} />
      </div>
    );
  }

  return (
    <div
      className={className}
      data-testid="atlas-viewer-shell"
      data-fullscreen="false"
      style={shellStyle}
    >
      <div style={controlBarFloatStyle}>
        <ControlBar
          playbackMode={state.playbackMode}
          speed={state.speed as Speed}
          zoomLevel={zoomLevel}
          currentTokenIndex={currentTokenIndex}
          tokenCount={tokens.length || state.tokenCount}
          verificationMode={verificationMode}
          showBlindspots={showBlindspots}
          showActiveTrace={showActiveTrace}
          runtimeMode={runtimeMode}
          liveStatus={liveStatus}
          onPlayToggle={handlePlayToggle}
          onStartLive={onStartLive ? () => onStartLive(liveControls) : undefined}
          onUseReplay={onUseReplay}
          onSpeedChange={handleSpeedChange}
          onZoomLevelChange={setZoomLevel}
          onTokenSeek={handleTokenSeek}
          onVerificationModeChange={setVerificationMode}
          onToggleBlindspots={() => setShowBlindspots((v) => !v)}
          onToggleActiveTrace={() => setShowActiveTrace((v) => !v)}
          onRewind={handleRewind}
          onToggleFullscreen={handleToggleFullscreen}
          onToggleLeftPanel={handleToggleLeftPanel}
          onToggleRightPanel={handleToggleRightPanel}
          onToggleHelp={handleToggleHelp}
          fullscreen={fullscreen}
          leftPanelOpen={leftPanelOpen}
          rightPanelOpen={rightPanelOpen}
        />
      </div>

      <div style={narrationStyle} data-testid="narration-strip">
        <span style={provenanceBadgeStyle} title={runtimeMode === 'live' ? 'Trace events are streaming through the API proxy from the live Pythia-160M worker.' : 'Trace is real activations from Pythia-160M, recorded offline and replayed here.'}>
          <span style={provenanceDotStyle} />
          {liveLabel}
        </span>
        {liveError ? (
          <span style={{ color: '#fb7185', fontWeight: 600 }}>
            {liveError}
          </span>
        ) : null}
        <span style={demoBadgeStyle} title="Spatial primitives below are demo fixtures until the live vision-grounding wire-up lands (roadmap item #6 + #8)">
          <span style={demoDotStyle} />
          Picture · demo fixture
        </span>
        <span style={narrationKeyStyle}>Now</span>
        <span style={narrationValueStyle}>token {currentTokenIndex + 1}</span>
        {tokenTextNow ? (
          <>
            <span style={narrationKeyStyle}>·</span>
            <span style={narrationValueStyle}>"{tokenTextNow}"</span>
          </>
        ) : null}
        {activeStep ? (
          <>
            <span style={narrationKeyStyle}>·</span>
            <span style={{ color: ACCENT_TEAL }}>
              grounded step {activeStep.step_id}
              {activePrimitives.length > 0
                ? ` · ${activePrimitives.length} spatial primitive${activePrimitives.length === 1 ? '' : 's'}`
                : ''}
            </span>
          </>
        ) : (
          <>
            <span style={narrationKeyStyle}>·</span>
            <span style={{ color: COLORS.textMuted, fontStyle: 'italic' }}>
              scrub forward to reach a grounded step
            </span>
          </>
        )}
      </div>

      <div style={mainRowStyle} data-testid="atlas-viewer-main">
        <motion.aside
          animate={{ flexGrow: leftFlex, opacity: leftPanelOpen ? 1 : 0 }}
          transition={SPRING_GENTLE}
          style={{ ...columnStyle, flexBasis: 0, flexShrink: 1, pointerEvents: leftPanelOpen ? 'auto' : 'none' }}
          data-testid="atlas-viewer-left"
          aria-hidden={!leftPanelOpen}
        >
          <GlassPanel intensity="regular" padding={0} style={floatingCardStyle}>
            <div role="tablist" aria-label="Evidence views" style={tabBarStyle}>
              <button
                type="button"
                role="tab"
                aria-selected={leftTab === 'spatial'}
                data-testid="left-tab-spatial"
                onClick={() => setLeftTab('spatial')}
                style={leftTab === 'spatial' ? tabActiveStyle : tabBaseStyle}
              >
                Spatial Evidence
                {leftTab === 'spatial' && (
                  <motion.div
                    layoutId="left-tab-underline"
                    style={tabUnderlineStyle}
                    transition={SPRING_SNAPPY}
                  />
                )}
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={leftTab === 'notation'}
                data-testid="left-tab-notation"
                onClick={() => setLeftTab('notation')}
                style={leftTab === 'notation' ? tabActiveStyle : tabBaseStyle}
              >
                2D Notation
                {leftTab === 'notation' && (
                  <motion.div
                    layoutId="left-tab-underline"
                    style={tabUnderlineStyle}
                    transition={SPRING_SNAPPY}
                  />
                )}
              </button>
            </div>
            <div
              role="tabpanel"
              data-testid="left-tab-panel"
              style={tabPanelStyle}
            >
              {leftTab === 'spatial' ? (
                <>
                  <VisualPrimitiveCanvas
                    imageUrl={spatialEvidence.image_url}
                    imageWidth={spatialEvidence.image_width}
                    imageHeight={spatialEvidence.image_height}
                    primitives={spatialEvidence.primitives}
                    activeStepPrimitiveIds={activePrimitiveIds}
                    onPrimitiveClick={handlePrimitiveCanvasClick}
                  />
                  <SpatialEvidencePanel
                    primitives={activePrimitives}
                    selectedPrimitiveId={activePrimitiveId}
                    onPrimitiveSelect={handlePrimitiveSelect}
                    onOpenEvidence={handlePrimitiveOpenEvidence}
                    emptyStateLabel={
                      activeStep
                        ? 'No spatial evidence for this step'
                        : 'Scrub forward to reach a grounded step'
                    }
                  />
                </>
              ) : (
                <div
                  style={placeholderCardStyle}
                  data-testid="notation-placeholder"
                >
                  <strong>2D Notation — pending wave 3.</strong>
                  <p style={{ margin: '8px 0 0 0' }}>
                    This slot will render the 169-primitive CAS notation
                    map (wrapping <code>dashboard/src/lib/notation2DMap</code>).
                    Not yet wired in v0.0.
                  </p>
                </div>
              )}
            </div>
          </GlassPanel>
        </motion.aside>

        <motion.div
          animate={{ flexGrow: centerFlex }}
          transition={SPRING_GENTLE}
          style={{ ...columnStyle, flexBasis: 0, flexShrink: 1 }}
          data-testid="atlas-viewer-center"
        >
          <div style={centerSceneWrapperStyle}>
            <NeuralNetScene
              architecture={architecture}
              currentFrame={currentFrame}
              selectedNeuron={selectedNeuron}
              blindspotCoords={blindspotCoords}
              activeTraceCoords={activeTraceCoords}
              zoomLevel={zoomLevel}
              onNeuronClick={handleNeuronClick}
            />
          </div>
        </motion.div>

        <motion.aside
          animate={{ flexGrow: rightFlex, opacity: rightPanelOpen ? 1 : 0 }}
          transition={SPRING_GENTLE}
          style={{ ...columnStyle, flexBasis: 0, flexShrink: 1, pointerEvents: rightPanelOpen ? 'auto' : 'none' }}
          data-testid="atlas-viewer-right"
          aria-hidden={!rightPanelOpen}
        >
          <GlassPanel intensity="regular" padding={0} style={floatingCardStyle}>
            <div style={rightCardInnerStyle}>
              <MethodKnobsPanel
                methods={[...methods]}
                enabledMethodIds={enabledMethodIds}
                knobValues={knobValues}
                onToggleMethod={handleToggleMethod}
                onKnobChange={handleKnobChange}
                density={controlsDensity}
              />
            </div>
          </GlassPanel>
        </motion.aside>
      </div>

      <div style={bottomTimelineFloatStyle} data-testid="atlas-viewer-bottom">
        <GlassPanel intensity="thin" padding="8px 12px">
          <Mode7Timeline
            tokens={tokens}
            frames={mode7Frames}
            currentTokenIndex={currentTokenIndex}
            onTokenSelect={handleTokenSeek}
          />
        </GlassPanel>
      </div>

      <EvidenceDrawer
        open={evidenceDrawerOpen}
        payload={evidencePayload}
        onClose={closeDrawer}
      />

      <HelpOverlay open={helpOpen} onClose={() => setHelpOpen(false)} />

      <span style={{ display: 'none' }} aria-hidden="true">{ATLAS_STATUS_COLORS.activeTrace}</span>

      {/* Keep AnimatePresence import non-dead so any future child can use
          exit animations without re-importing. */}
      <AnimatePresence />
    </div>
  );
}

export default AtlasViewerShell;
