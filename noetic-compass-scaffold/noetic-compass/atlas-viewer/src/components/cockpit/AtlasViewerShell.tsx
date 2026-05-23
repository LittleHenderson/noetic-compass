import { useCallback, useEffect, useMemo, useState } from 'react';
import type { CSSProperties } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ControlBar, {
  type Speed,
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
  TESTING_METHODS,
  type TestingMethod,
} from '../../lib/testingMethods';
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
}

const BLINDSPOT_DEMO_CLASSES = ['F1A', 'F1T', 'F1f', 'F1E'];

export interface AtlasViewerShellProps {
  trace: ReplayTrace;
  spatialEvidence: SpatialEvidenceArtifact;
  architecture: ModelArchitecture;
  methods?: readonly TestingMethod[];
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

const centerColumnStyle: CSSProperties = {
  ...columnStyle,
};

const centerSceneWrapperStyle: CSSProperties = {
  flex: 1,
  minHeight: 0,
  position: 'relative',
};

const rightColumnStyle: CSSProperties = {
  ...columnStyle,
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

const fullscreenSceneStyle: CSSProperties = {
  position: 'absolute',
  inset: 8,
  bottom: 64, // leave room for the floating timeline
  zIndex: 5,
  border: '1px solid rgba(255, 255, 255, 0.06)',
  borderRadius: 8,
  overflow: 'hidden',
  background: '#020617',
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

// Build the grid template based on which side panels are open. Each panel
// gets a fluid track when open and zero width when collapsed. The center
// column always exists; in fullscreen mode the grid collapses to one
// 100% column and the panels render off-screen.
function gridTemplate(leftOpen: boolean, rightOpen: boolean, fullscreen: boolean): string {
  if (fullscreen) return '100%';
  if (leftOpen && rightOpen) return '38% 42% 20%';
  if (leftOpen && !rightOpen) return '40% 60%';
  if (!leftOpen && rightOpen) return '75% 25%';
  return '100%';
}

export function AtlasViewerShell(props: AtlasViewerShellProps): JSX.Element {
  const {
    trace,
    spatialEvidence,
    architecture,
    methods = TESTING_METHODS,
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

  // Wave 5.2: panel collapse + fullscreen + help state.
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

  const currentTokenIndex = state.currentTokenIndex;
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
    for (const cls of BLINDSPOT_DEMO_CLASSES) {
      const labels = covers[cls];
      if (!labels) continue;
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

  useEffect(() => {
    setActivePrimitiveId(undefined);
  }, [activeStep?.step_id]);

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

  // Wave 5.2: rewind to t=0
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

  // Wave 5.2: when the picture panel is collapsed, the controls panel
  // typography scales up. User's explicit ask: "when picture panel is
  // retracted the checks and control panel words and letters will get
  // bigger and become more legible."
  const controlsDensity = leftPanelOpen ? 'compact' : 'comfortable';

  const mainGridStyle: CSSProperties = {
    flex: 1,
    display: 'grid',
    gridTemplateColumns: gridTemplate(leftPanelOpen, rightPanelOpen, fullscreen),
    columnGap: 8,
    minHeight: 0,
    overflow: 'hidden',
    position: 'relative',
  };

  // Caption strip beside the timeline: tells the user what's happening at
  // the current token. Pulls the active grounded step (if any) plus the
  // raw token string. Renders "—" when there's no grounded step at this
  // moment, so the user knows scrubbing further forward will land one.
  const tokenTextNow = tokens[currentTokenIndex]?.token ?? '';
  const narrationStyle: CSSProperties = {
    display: 'flex',
    alignItems: 'center',
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

  return (
    <div
      className={className}
      data-testid="atlas-viewer-shell"
      style={shellStyle}
    >
      <div style={controlBarFloatStyle}>
        <ControlBar
          playbackMode={state.playbackMode}
          speed={state.speed as Speed}
          zoomLevel={zoomLevel}
          currentTokenIndex={currentTokenIndex}
          tokenCount={state.tokenCount}
          verificationMode={verificationMode}
          showBlindspots={showBlindspots}
          showActiveTrace={showActiveTrace}
          onPlayToggle={handlePlayToggle}
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

      {/* Narration strip — tells user what they're seeing right now */}
      <div style={narrationStyle} data-testid="narration-strip">
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

      <div style={mainGridStyle} data-testid="atlas-viewer-main">
        <AnimatePresence initial={false}>
          {leftPanelOpen && !fullscreen ? (
            <motion.div
              key="left"
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -8 }}
              transition={SPRING_GENTLE}
              style={columnStyle}
              data-testid="atlas-viewer-left"
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
            </motion.div>
          ) : null}
        </AnimatePresence>

        <div
          style={fullscreen ? fullscreenSceneStyle : centerColumnStyle}
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
        </div>

        <AnimatePresence initial={false}>
          {rightPanelOpen && !fullscreen ? (
            <motion.div
              key="right"
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 8 }}
              transition={SPRING_GENTLE}
              style={rightColumnStyle}
              data-testid="atlas-viewer-right"
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
            </motion.div>
          ) : null}
        </AnimatePresence>
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

      {/* Touch the imported palette so it isn't dead-code-eliminated; we
          still rely on activeTrace color via its consumers above. */}
      <span style={{ display: 'none' }} aria-hidden="true">{ATLAS_STATUS_COLORS.activeTrace}</span>
    </div>
  );
}

export default AtlasViewerShell;
